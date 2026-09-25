"""Arelle-backed ESEF/XBRL conformance tier for the submission gate.

Runs the official Arelle conformance suite (``arelleCmdLine``) over a
single-file inline-XBRL statement and folds its findings into the product's
own pre-flight result (:mod:`app.esrs_validate`). Arelle is strictly optional
at runtime: when the binary is missing, the run times out or falls over, the
authority is recorded as unavailable and the product gate remains decisive
(fail-closed on Arelle *errors*, advisory on its warnings).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.esrs_validate import ValidationResult

_AUTHORITY_MAX_WARNINGS = 100


def _resolve_cmdline(cmdline: str) -> Optional[str]:
    """Resolve the Arelle CLI, preferring the current interpreter's venv."""
    if Path(cmdline).is_file():
        return cmdline
    in_venv = Path(sys.prefix) / "bin" / cmdline
    if in_venv.is_file():
        return str(in_venv)
    found = shutil.which(cmdline)
    return found


def arelle_available(cmdline: str = "arelleCmdLine") -> bool:
    return _resolve_cmdline(cmdline) is not None


def run_arelle_validation(
    content: bytes,
    *,
    timeout: float = 180.0,
    cmdline: str = "arelleCmdLine",
) -> Optional[dict]:
    """Run Arelle over ``content`` and return classified findings.

    Returns ``None`` when the binary is missing, the run times out, or the
    process cannot start (the authority failed rather than validated). On a
    successful run: ``{"available": True, "errors": [...], "warnings": [...],
    "elapsed_ms": int}`` where items are ``{"severity", "code", "message",
    "source": "arelle"}`` dicts. ESRS ``message:ea_*`` formula messages fire
    at ERROR level but advise on mandatory-tag completeness that phase-in
    provisions relax; they are surfaced as advisory warnings, while genuine
    instance/XBRL structure errors gate the submission.
    """
    resolved = _resolve_cmdline(cmdline)
    if resolved is None:
        return None
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        tmp.write(content)
        path = tmp.name
    started = time.monotonic()
    try:
        try:
            proc = subprocess.run(
                [
                    resolved,
                    "-f",
                    path,
                    "--validate",
                    "--logFormat",
                    "%(levelname)s\t%(messageCode)s\t%(message)s",
                ],
                capture_output=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
        elapsed_ms = int((time.monotonic() - started) * 1000)
    finally:
        Path(path).unlink(missing_ok=True)

    errors: list[dict] = []
    warnings: list[dict] = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        level, code, message = parts[0], parts[1], parts[2].strip()
        if level == "ERROR" and code.startswith("message:ea_"):
            if len(warnings) < _AUTHORITY_MAX_WARNINGS:
                warnings.append(
                    {
                        "severity": "warning",
                        "code": code or "arelle",
                        "message": message,
                        "source": "arelle",
                    }
                )
            continue
        item = {
            "severity": "warning" if level == "WARNING" else "error",
            "code": code or "arelle",
            "message": message,
            "source": "arelle",
        }
        if level == "ERROR":
            errors.append(item)
        elif level == "WARNING" and len(warnings) < _AUTHORITY_MAX_WARNINGS:
            warnings.append(item)
    return {
        "available": True,
        "elapsed_ms": elapsed_ms,
        "errors": errors,
        "warnings": warnings,
    }


def merge_arelle_into(result: ValidationResult, arelle_out: dict) -> None:
    """Fold Arelle authority findings into a gate result.

    Arelle ``[ERROR]`` entries block submission; ``[WARNING]`` entries are
    advisory (the ESRS ``ea_*`` formula family is informational completeness
    guidance). Issues already produced by the product gate at the same
    ``(code, message)`` are not duplicated.
    """
    existing = {(i.code, i.message, i.severity) for i in result.issues}
    for item in arelle_out.get("errors", []):
        if (item["code"], item["message"], "error") not in existing:
            result.error(item["code"], item["message"])
    added = 0
    for item in arelle_out.get("warnings", []):
        if (item["code"], item["message"], "warning") not in existing and added < _AUTHORITY_MAX_WARNINGS:
            result.warn(item["code"], item["message"])
            added += 1
    errors = len(arelle_out.get("errors", []))
    warnings = len(arelle_out.get("warnings", []))
    if errors == 0 and warnings == 0:
        result.info("arelle", "Arelle XBRL conformance suite: no issues found")
    else:
        note = f"Arelle XBRL conformance suite: {errors} error(s), {warnings} warning(s)"
        elapsed_ms = arelle_out.get("elapsed_ms")
        if elapsed_ms is not None:
            note += f" ({elapsed_ms} ms)"
        result.info("arelle", note)


def apply_arelle(
    result: ValidationResult,
    content: bytes,
    *,
    enabled: bool = True,
    timeout: float = 180.0,
    cmdline: str = "arelleCmdLine",
) -> None:
    """Run Arelle when available and fold its findings into ``result``."""
    if not enabled:
        return
    out = run_arelle_validation(content, timeout=timeout, cmdline=cmdline)
    if out is None:
        result.info(
            "arelle_unavailable",
            "Arelle XBRL conformance suite unavailable; only the product gate ran",
        )
        return
    merge_arelle_into(result, out)
