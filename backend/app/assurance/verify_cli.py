"""Offline verifier for Carbon Assurance proof bundles.

Usage::

    python -m app.assurance.verify_cli <bundle.json> [--json]

Ported from CarbonTrace's ``carbontrace verify`` command. Verifies a proof
bundle using **only its own contents** — no server, database or network. This is
what makes the assurance claim credible: an auditor can re-check a disclosed
number independently with this single file.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from app.assurance import crypto
from app.assurance.schemas import ProofBundle

_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of verifying a proof bundle, each independent check exposed."""

    valid: bool
    leaf_hash_ok: bool
    inclusion_ok: bool
    root_signature_ok: bool
    supplier_signature_ok: bool | None
    root: str
    size: int
    leaf_index: int

    def as_dict(self) -> dict:
        return {
            "valid": self.valid,
            "checks": {
                "leaf_hash": self.leaf_hash_ok,
                "inclusion_proof": self.inclusion_ok,
                "root_signature": self.root_signature_ok,
                "supplier_signature": self.supplier_signature_ok,
            },
            "root": self.root,
            "size": self.size,
            "leaf_index": self.leaf_index,
        }


def verify_bundle(bundle: ProofBundle) -> VerificationResult:
    """Verify a proof bundle using only its own contents (no server/DB)."""
    record_json = bundle.record.model_dump(mode="json")
    sr = bundle.signed_root

    recomputed_leaf = crypto.leaf_hash(record_json, algorithm=sr.algorithm)
    leaf_ok = recomputed_leaf == bundle.leaf_hash

    inclusion_ok = crypto.verify_inclusion(
        bundle.leaf_hash,
        sr.root,
        [crypto.ProofStep(side=s.side, hash=s.hash) for s in bundle.inclusion_proof],
        algorithm=sr.algorithm,
    )

    header = crypto.canonical_bytes(crypto.root_header(sr.root, sr.size, sr.algorithm))
    root_sig_ok = crypto.verify_signature(sr.server_public_key, header, sr.signature)

    supplier_ok: bool | None = None
    if bundle.supplier_public_key and bundle.supplier_signature:
        message = crypto.canonical_bytes(record_json)
        supplier_ok = crypto.verify_signature(
            bundle.supplier_public_key, message, bundle.supplier_signature
        )

    valid = leaf_ok and inclusion_ok and root_sig_ok and (supplier_ok is not False)
    return VerificationResult(
        valid=valid,
        leaf_hash_ok=leaf_ok,
        inclusion_ok=inclusion_ok,
        root_signature_ok=root_sig_ok,
        supplier_signature_ok=supplier_ok,
        root=sr.root,
        size=sr.size,
        leaf_index=bundle.leaf_index,
    )


def _mark(ok: bool | None) -> str:
    if ok is None:
        return "—  (not present)"
    return f"{_GREEN}✓{_RESET}" if ok else f"{_RED}✗{_RESET}"


def _print_human(result: VerificationResult) -> None:
    status = f"{_GREEN}VALID{_RESET}" if result.valid else f"{_RED}INVALID{_RESET}"
    print(f"Integrity: {status}")
    print(f"  leaf hash ......... {_mark(result.leaf_hash_ok)}")
    print(f"  inclusion proof ... {_mark(result.inclusion_ok)}")
    print(f"  root signature .... {_mark(result.root_signature_ok)}")
    print(f"  supplier signature  {_mark(result.supplier_signature_ok)}")
    print(f"  leaf index {result.leaf_index} of tree size {result.size}")
    print(f"  root {result.root}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="filebrsr-verify",
        description="Offline verifier for Carbon Assurance proof bundles.",
    )
    parser.add_argument("bundle", help="Path to a proof bundle JSON file.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    path = Path(args.bundle)
    if not path.exists():
        print(f"error: bundle not found: {path}", file=sys.stderr)
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        bundle = ProofBundle.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: invalid bundle: {exc}", file=sys.stderr)
        return 2

    result = verify_bundle(bundle)
    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        _print_human(result)
    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
