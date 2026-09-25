"""ESEF pre-flight validation for the CSRD filing artifact.

A pragmatic, dependency-free validator for the single-file inline-XBRL ESEF
statement produced by :mod:`app.esrs_esef`. It does **not** replace the
official ESEF/XBRL conformance suite (Arelle + EFRAG business rules) -- it is
the product's own gate that catches the structural mistakes a human reviewer
would catch before submission:

* well-formed, XML-serializable XHTML with a UTF-8 declaration;
* required ``ix:header`` present with a ``link:schemaRef`` pointing at the
  configured EFRAG ESRS taxonomy entry point (version pinned);
* every ``esrs:*`` concept actually exists in the shipped taxonomy map
  (no invented element names);
* every inline fact carries a valid ``contextRef``/``unitRef`` that resolves
  to a defined context/unit, a well-formed value, and (for ``ix:nonFraction``)
  a valid ``decimals`` token;
* no duplicate facts on the same (concept, context, unit);
* the statement carries an assurance opinion (CSRD precondition);
* in-scope datapoints with a precise concept mapping but no reported value
  are surfaced as warnings (completeness).

Severities: ``error`` blocks submission; ``warning`` / ``info`` are advisory.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.esrs_datapoints import ESRS_DATAPOINTS
from app.esrs_esef import (
    ESRS_NS,
    IX_NS,
    IXT_NS,
    LINK_NS,
    XBRLI_NS,
    XLINK_NS,
    concepts_for,
)

_XML_DECL_RE = re.compile(rb'^\s*<\?xml[^>]*encoding=["\']utf-8["\']', re.I)
_NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?$")
_DECIMALS_RE = re.compile(r"^(?:INF|-?\d{1,6})$")
_DATEPART_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_NOT_REPORTED_OUT = {"not_material", "not_applicable"}


@lru_cache(maxsize=1)
def _taxonomy_concepts() -> dict[str, str]:
    """concept local name -> item type, from the shipped taxonomy map."""
    path = Path(__file__).resolve().parent / "esrs_taxonomy_map.json"
    m = json.loads(path.read_text())
    out: dict[str, str] = {}
    for items in m["by_paragraph"].values():
        for c in items:
            out[c["concept"]] = c["type"]
    for items in m["section_textblocks"].values():
        for c in items:
            out[c["concept"]] = c["type"]
    return out


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class ValidationIssue:
    __slots__ = ("severity", "code", "message")

    def __init__(self, severity: str, code: str, message: str):
        self.severity = severity
        self.code = code
        self.message = message

    def as_dict(self) -> dict:
        return {"severity": self.severity, "code": self.code, "message": self.message}


class ValidationResult:
    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def error(self, code: str, message: str) -> None:
        self.issues.append(ValidationIssue("error", code, message))

    def warn(self, code: str, message: str) -> None:
        self.issues.append(ValidationIssue("warning", code, message))

    def info(self, code: str, message: str) -> None:
        self.issues.append(ValidationIssue("info", code, message))

    @property
    def errors(self) -> list[dict]:
        return [i.as_dict() for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[dict]:
        return [i.as_dict() for i in self.issues if i.severity == "warning"]

    @property
    def infos(self) -> list[dict]:
        return [i.as_dict() for i in self.issues if i.severity == "info"]

    @property
    def passed(self) -> bool:
        return not self.errors

    @property
    def summary(self) -> str:
        return f"{len(self.errors)} errors, {len(self.warnings)} warnings"

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "summary": self.summary,
            "errors": self.errors,
            "warnings": self.warnings,
            "infos": self.infos,
        }


def validate_esef_statement(
    content: bytes,
    *,
    financial_year: str,
    in_scope_ids: Optional[list[str]] = None,
    coverage_pct: float = 0.0,
    assurance: Optional[dict] = None,
    pinned_namespace: str = ESRS_NS,
) -> ValidationResult:
    """Run the pre-flight checks over an ESEF artifact (bytes)."""
    v = ValidationResult()
    concepts_known = _taxonomy_concepts()

    # 1. Well-formed XML + UTF-8 declaration
    if not _XML_DECL_RE.match(content[:256]):
        v.warn("encoding", "Missing UTF-8 XML declaration at the top of the file")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        v.error("well_formed", f"Document is not well-formed XML: {exc}")
        return v

    ns = _extract_prefix_map(content)

    # 2. ix:header + schemaRef (version pinning)
    header = _find(root, IX_NS, "header")
    if header is None:
        v.error("ix_header_missing", "No <ix:header> element found; the file is not valid inline XBRL")
    else:
        hidden = _first(root, IX_NS, "hidden") or _find(header, IX_NS, "hidden")
        resources = (
            _first(header, IX_NS, "resources")
            if hidden is None
            else _find(hidden, IX_NS, "resources")
        )
        schema_ref = (
            _first(resources, LINK_NS, "schemaRef")
            if resources is not None
            else _find(header, LINK_NS, "schemaRef")
        )
        href = (schema_ref.attrib.get(f"{{{XLINK_NS}}}href") or "") if schema_ref is not None else ""
        if not href:
            v.error("schema_ref_missing", "No link:schemaRef element found in the ix:header")
        elif not href.endswith("/esrs_all.xsd"):
            v.error("schema_ref_entry_point", f"schemaRef must point at the esrs_all.xsd entry point, got: {href}")
        elif pinned_namespace and ESRS_NS in href and pinned_namespace != ESRS_NS:
            v.error("taxonomy_version", f"Taxonomy version mismatch: file uses {ESRS_NS} but {pinned_namespace} is required")
        else:
            v.info("schema_ref", f"Schema reference OK: {href}")

    esrs_namespace = next((u for p, u in ns.items() if p == "esrs"), None)
    if esrs_namespace != ESRS_NS:
        v.error("esrs_namespace", f"esrs prefix must bind to {ESRS_NS}, got {esrs_namespace!r}")

    # 3. Collect contexts and units defined in the hidden resources
    defined_contexts: set[str] = set()
    defined_units: set[str] = set()
    context_period_ok: set[str] = set()
    if header is not None:
        hidden = _first(header, IX_NS, "hidden")
        if hidden is None:
            hidden = header
        for el in hidden.iter():
            if el.tag == f"{{{XBRLI_NS}}}context":
                ctx_id = el.attrib.get("id")
                if ctx_id:
                    defined_contexts.add(ctx_id)
                    period = _first(el, XBRLI_NS, "period")
                    if period is not None:
                        start = _first(period, XBRLI_NS, "startDate")
                        end = _first(period, XBRLI_NS, "endDate")
                        if (
                            start is not None
                            and end is not None
                            and _DATEPART_RE.match(start.text or "")
                            and (end.text or "") > (start.text or "")
                        ):
                            context_period_ok.add(ctx_id)
            elif el.tag == f"{{{XBRLI_NS}}}unit":
                unit_id = el.attrib.get("id")
                if unit_id:
                    defined_units.add(unit_id)

    if not defined_contexts:
        v.error("contexts_missing", "No <xbrli:context> elements defined in the header")

    # 4. Facts
    facts_seen: dict[tuple[str, str, str], str] = {}
    fact_count = 0
    for el in root.iter():
        if el.tag not in (f"{{{IX_NS}}}nonFraction", f"{{{IX_NS}}}nonNumeric"):
            continue
        fact_count += 1
        name = el.attrib.get("name", "")
        ctx_ref = el.attrib.get("contextRef", "")
        unit_ref = el.attrib.get("unitRef")
        decimals = el.attrib.get("decimals")

        if not name:
            v.error("fact_no_name", "An ix fact is missing its 'name' attribute")
        else:
            local_name = name.split(":", 1)[1] if ":" in name else name
            if name.startswith("esrs:") and local_name not in concepts_known:
                v.error("unknown_concept", f"Tagged concept {name} is not defined in the ESRS taxonomy map")

        if not ctx_ref:
            v.error("fact_no_context", f"Fact {name} is missing contextRef")
        elif ctx_ref not in defined_contexts:
            v.error("unknown_context", f"Fact {name} references undefined context '{ctx_ref}'")
        elif ctx_ref not in context_period_ok:
            v.error("context_period", f"Context '{ctx_ref}' must be a duration with valid start/end dates")

        if el.tag == f"{{{IX_NS}}}nonFraction":
            fact_count_key = (name, ctx_ref, unit_ref or "")
            if fact_count_key in facts_seen:
                v.error("duplicate_fact", f"Duplicate fact {name}@{ctx_ref} (unit {unit_ref})")
            else:
                facts_seen[fact_count_key] = unit_ref or ""
            if not unit_ref:
                v.error("fact_no_unit", f"Numeric fact {name} is missing unitRef")
            elif unit_ref not in defined_units:
                v.error("unknown_unit", f"Fact {name} references undefined unit '{unit_ref}'")
            if decimals is None:
                v.error("fact_no_decimals", f"Numeric fact {name} is missing the decimals attribute")
            elif not _DECIMALS_RE.match(decimals):
                v.error("bad_decimals", f"Fact {name} has invalid decimals '{decimals}' (expected INF or an integer)")
            else:
                item_type = concepts_known.get(name.split(":", 1)[1] if ":" in name else name, "")
                if item_type == "xbrli:integerItemType" and decimals != "0":
                    v.warn("decimals_integer", f"Fact {name} is an integerItemType but decimals='{decimals}' (expected '0')")
                if unit_ref == "u_pure" and decimals not in ("INF", "0"):
                    v.warn("decimals_pure", f"Fact {name} is a pure/percent measure with decimals='{decimals}' (consider INF)")
            raw_text = (el.text or "").strip()
            if not raw_text:
                v.error("empty_fact", f"Numeric fact {name} is empty")
            elif not _NUMERIC_RE.match(raw_text):
                v.error("bad_numeric", f"Numeric fact {name} has non-numeric value '{raw_text}'")
            if el.attrib.get("format") and not _qname_in_ns(el.attrib.get("format"), ns, IXT_NS):
                v.warn("format_namespace", f"Fact {name} format attribute is outside the ixt namespace")
        else:
            if ctx_ref and ctx_ref in defined_contexts and ctx_ref not in context_period_ok:
                v.error("context_period", f"Context '{ctx_ref}' must be a duration with valid start/end dates")

    if fact_count == 0:
        v.error("no_facts", "No tagged facts found — the statement is not digitally tagged")

    # 5. Assurance present (CSRD precondition for filing)
    status = (assurance or {}).get("status") or "none"
    if status not in ("limited", "reasonable"):
        v.error(
            "assurance_missing",
            f"Filing requires a limited/reasonable assurance opinion on the ESEF statement (current: {status})",
        )
    else:
        v.info("assurance", f"Assurance opinion present: {status}")

    # 6. Completeness: in-scope datapoints with a precise concept mapping but
#    no fact actually tagged on the document (no reported value or unmappable)
    tagged_names = set()
    for el in root.iter():
        if el.tag in (f"{{{IX_NS}}}nonFraction", f"{{{IX_NS}}}nonNumeric"):
            n = el.attrib.get("name", "")
            if n.startswith("esrs:"):
                tagged_names.add(n.split(":", 1)[1])
    in_scope = set(in_scope_ids) if in_scope_ids is not None else {d["id"] for d in ESRS_DATAPOINTS}
    untagged = sorted(
        d["id"] for d in ESRS_DATAPOINTS
        if d["id"] in in_scope
        and concepts_for(d)
        and not any(c["concept"] in tagged_names for c in concepts_for(d))
    )
    if untagged:
        sample = ", ".join(untagged[:3]) + (", …" if len(untagged) > 3 else "")
        v.warn(
            "mapped_untagged",
            f"{len(untagged)} in-scope datapoint(s) map to a precise ESRS concept but have "
            f"no tagged fact in the file (report a value to tag them): {sample}",
        )

    if coverage_pct > 0 and coverage_pct < 50:
        v.warn("low_coverage", f"Report covers only {coverage_pct:.1f}% of in-scope datapoints")

    v.info("facts", f"{fact_count} tagged fact(s), {len(defined_contexts)} context(s), {len(defined_units)} unit(s)")
    return v


def _first(parent: Optional[ET.Element], ns_uri: str, name: str) -> Optional[ET.Element]:
    if parent is None:
        return None
    tag = f"{{{ns_uri}}}{name}"
    for el in parent:
        if el.tag == tag:
            return el
    return None


def _find(parent: Optional[ET.Element], ns_uri: str, name: str) -> Optional[ET.Element]:
    if parent is None:
        return None
    tag = f"{{{ns_uri}}}{name}"
    for el in parent.iter():
        if el.tag == tag:
            return el
    return None


def _qname_in_ns(qname: str, prefix_map: dict[str, str], ns_uri: str) -> bool:
    """True when a QName attribute (e.g. ``ixt:numdotdecimal``) resolves to ``ns_uri``."""
    if ":" in qname:
        prefix, _local = qname.split(":", 1)
        return prefix_map.get(prefix) == ns_uri
    return True


def _extract_prefix_map(content: bytes) -> dict[str, str]:
    """xmlns prefix -> URI, taken from the document's own declarations.

    ElementTree drops ``xmlns`` attributes from ``Element.attrib``, so the
    prefix bindings must come from the raw document text. First occurrence
    wins (root declarations shadow later re-declarations).
    """
    out: dict[str, str] = {}
    for m in re.finditer(rb'xmlns(?::([A-Za-z_][A-Za-z0-9_.-]*))?="([^"]+)"', content):
        prefix = (m.group(1) or b"").decode() if m.group(1) else ""
        uri = m.group(2).decode()
        if prefix not in out:
            out[prefix] = uri
    return out
