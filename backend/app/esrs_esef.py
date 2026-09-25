"""ESEF digital filing export for the ESRS sustainability statement.

Generates a single electronic format (ESEF) document -- an inline-XBRL XHTML
file machine-tagged against the official EFRAG ESRS Set 1 XBRL Taxonomy
(published 2024-08-30, namespace
``https://xbrl.efrag.org/taxonomy/esrs/2023-12-22``).

Design decisions (keep honest, avoid fabricated tags):

* A datapoint is tagged with a precise XBRL concept **only when the official
  taxonomy defines an element for its (disclosure requirement, paragraph)**.
  The mapping is generated offline from EFRAG's reference linkbase and shipped
  in ``app/esrs_taxonomy_map.json`` (see ``scripts/build_esrs_taxonomy_map.py``).
* Datapoints the taxonomy does not define at paragraph level are rendered
  human-readable in the XHTML body but **not** cluttered with invented element
  names. Sections with an official ``textBlockItemType`` element get that
  text-block tag instead.
* Facts are cross-linked to the taxonomy's own ``esrs_all.xsd`` entry point via
  ``link:schemaRef``; contexts/units follow the XBRL instance spec, so the file
  loads in any XBRL processor (Arelle, etc.).

The module is dependency-free: it emits well-formed XML by construction and
escapes every text node.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.esrs_datapoints import ESRS_DATAPOINTS, ESRS_STANDARDS

ESRS_NS = "https://xbrl.efrag.org/taxonomy/esrs/2023-12-22"
IX_NS = "http://www.xbrl.org/2013/inlineXBRL"
XLINK_NS = "http://www.w3.org/1999/xlink"
XBRLI_NS = "http://www.xbrl.org/2003/instance"
LINK_NS = "http://www.xbrl.org/2003/linkbase"
IXT_NS = "http://www.xbrl.org/inlineXBRL/transformation/2020-02-12"

_NUMERIC_TYPES = {
    "xbrli:monetaryItemType",
    "xbrli:decimalItemType",
    "xbrli:integerItemType",
    "xbrli:percentItemType",
    "xbrli:pureItemType",
    "ghgEmissionsItemType",
    "massItemType",
    "energyItemType",
    "volumeItemType",
    "areaItemType",
}


def concept_unit(item_type: str) -> Optional[str]:
    if item_type == "xbrli:monetaryItemType":
        return "eur"
    if item_type in ("xbrli:percentItemType", "xbrli:pureItemType"):
        return "pure"
    if item_type == "ghgEmissionsItemType":
        return "tco2e"
    if item_type == "massItemType":
        return "tonne"
    if item_type == "energyItemType":
        return "mwh"
    if item_type == "volumeItemType":
        return "m3"
    return "pure"


@lru_cache(maxsize=1)
def _taxonomy_map() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "esrs_taxonomy_map.json"
    return json.loads(path.read_text())


def _norm_paragraph(p: str) -> str:
    p = p.strip().replace("  ", " ")
    if p.upper().startswith(("AR", "IR")):
        return p
    m = re.match(r"^(\d+)([a-zA-Z]?)$", p)
    return f"{int(m.group(1)):02d}{m.group(2)}" if m else p


def _split_paragraphs(p: str) -> list[str]:
    return [c.strip() for c in re.split(r"[;,]", p or "") if c.strip()]


def concepts_for(dp: dict) -> list[dict]:
    """Precise taxonomy concepts defined for this datapoint, map order."""
    m = _taxonomy_map()
    by_para = m["by_paragraph"]
    out: list[dict] = []
    seen: set[str] = set()
    for p in _split_paragraphs(dp.get("paragraph", "")):
        for c in by_para.get(f"{dp['dr']}::{_norm_paragraph(p)}", []):
            if c["concept"] not in seen:
                seen.add(c["concept"])
                out.append(c)
    return out


def textblock_for(dp: dict) -> Optional[dict]:
    return (_taxonomy_map()["section_textblocks"].get(dp["dr"]) or [None])[0]


def _fy_year(financial_year: str) -> int:
    m = re.match(r"FY(\d{4})", financial_year or "")
    return int(m.group(1)) if m else 2025


def fy_period(financial_year: str) -> tuple[str, str]:
    year = _fy_year(financial_year)
    return f"{year}-01-01", f"{year}-12-31"


def _value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _esc(s: Any) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _pick_concept(concepts: list[dict], value: Any) -> Optional[dict]:
    if not concepts:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        for c in concepts:
            if c["type"] in _NUMERIC_TYPES:
                return c
    return concepts[0]


def _tag_cell(value: Any, tag: dict, ctx_ref: str) -> str:
    """Return an inline-XBRL tagged cell for one fact."""
    item_type = tag["type"]
    txt = _value_text(value)
    name = f'esrs:{_esc(tag["concept"])}'
    if item_type in _NUMERIC_TYPES and isinstance(value, (int, float)) and not isinstance(value, bool):
        decimals = "0" if item_type == "xbrli:integerItemType" else "-1"
        unit = concept_unit(item_type)
        return (
            f'<td class="v">'
            f'<ix:nonFraction name="{name}" contextRef="{ctx_ref}" unitRef="u_{unit}" '
            f'decimals="{decimals}" scale="0" format="ixt:numdotdecimal">{_esc(txt)}</ix:nonFraction>'
            "</td>"
        )
    if isinstance(value, bool):
        return (
            f'<td class="v">'
            f'<ix:nonNumeric name="{name}" contextRef="{ctx_ref}" escape="false">{txt}</ix:nonNumeric>'
            "</td>"
        )
    return (
        f'<td class="v">'
        f'<ix:nonNumeric name="{name}" contextRef="{ctx_ref}" escape="true">{_esc(txt)}</ix:nonNumeric>'
        "</td>"
    )


def build_esef_statement(
    *,
    financial_year: str,
    org_id: str,
    org_name: str,
    entity_identifier: str,
    entity_scheme: str = "http://xbrl.efrag.org/LEI",
    entries: list[dict],
    in_scope_ids: list[str],
    coverage_pct: float,
    value_chain_scope: Optional[list[str]] = None,
    assurance: Optional[dict] = None,
) -> bytes:
    """Return the UTF-8 inline-XBRL XHTML single file (the ESEF artifact).

    ``entries``: ``esrs_entries`` rows reduced to
    ``{datapoint_id, status, value, evidence, notes}``.
    """
    start, end = fy_period(financial_year)
    ctx_duration = f"cfy_fy{_fy_year(financial_year)}"
    by_dp = json.loads(json.dumps({e["datapoint_id"]: e for e in entries}))
    in_scope = [
        d for d in ESRS_DATAPOINTS if d["id"] in set(in_scope_ids)
    ]

    per_std_rows: dict[str, list[str]] = {}
    for dp in sorted(in_scope, key=lambda d: (d["dr"], d["id"])):
        entry = by_dp.get(dp["id"], {})
        status = entry.get("status") or "not_assessed"
        value = entry.get("value")
        evidence = entry.get("evidence") or ""
        concepts = concepts_for(dp)
        tag = _pick_concept(concepts, value)
        if tag is None:
            tag = textblock_for(dp)
        elif value is None and tag["type"] != "textBlockItemType":
            tag = None
        cells = (
            f"<td class=\"id\">{_esc(dp['id'])}</td>"
            f"<td>{_esc(dp['name'])}</td>"
            f"<td class=\"st\">{_esc(status)}</td>"
        )
        if tag and value is not None:
            cells += _tag_cell(value, tag, ctx_duration)
        else:
            cells += f"<td class=\"v\">{_esc(_value_text(value))}</td>"
        cells += f"<td>{_esc(evidence)}</td>"
        per_std_rows.setdefault(dp["standard"], []).append(f"<tr>{cells}</tr>")

    sections: list[str] = []
    for std in sorted(per_std_rows, key=lambda s: ESRS_STANDARDS.get(s, {}).get("order", 99)):
        meta = ESRS_STANDARDS.get(std, {"code": f"ESRS {std}", "name": std})
        sections.append(
            f"<h2>{_esc(meta['code'])} — {_esc(meta['name'])}</h2>"
            "<table><thead><tr><th>Datapoint</th><th>Topic</th><th>Status</th><th>Value</th><th>Evidence</th></tr></thead>"
            f"<tbody>{''.join(per_std_rows[std])}</tbody></table>"
        )

    header = _make_header(
        entity_identifier=entity_identifier,
        entity_scheme=entity_scheme,
        start=start,
        end=end,
        ctx_duration=ctx_duration,
    )
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<html lang="en" xmlns:ix="{IX_NS}" xmlns:xbrli="{XBRLI_NS}" xmlns:link="{LINK_NS}" xmlns:xlink="{XLINK_NS}" xmlns:esrs="{ESRS_NS}" xmlns:utr="http://www.xbrl.org/2009/utr" xmlns:ixt="{IXT_NS}">
<head>
<meta charset="utf-8"/>
<title>ESRS Sustainability Statement — {_esc(financial_year)}</title>
<style>body{{font-family:Georgia,serif;margin:40px;color:#1a2333}} h1{{border-bottom:2px solid #2563EB;padding-bottom:10px}} h2{{color:#2563EB;margin-top:32px;border-left:4px solid #2563EB;padding-left:10px}} table{{width:100%;border-collapse:collapse;margin-top:8px;font-size:12px}} th,td{{border:1px solid #d6dee9;padding:6px;text-align:left;vertical-align:top}} th{{background:#eef3ff}} .esc{{font-size:11px;color:#64748b}} .v ix\\:nonNumeric{{background:#fff7ed;border:1px solid #fdba74}}</style>
</head>
<body>{header}
<h1>ESRS Sustainability Statement</h1>
<p><b>Reporting period:</b> {_esc(financial_year)} ({start} to {end}) · <b>Coverage:</b> {coverage_pct:.2f}% · <b>Entity:</b> {_esc(org_name)} ({_esc(entity_identifier)})</p>
<p class="esc">ESEF single file — inline-XBRL tagged to the EFRAG ESRS Set 1 XBRL Taxonomy ({ESRS_NS}).</p>
{sections}
{_assurance_html(assurance, start, end, org_name)}
</body>
</html>"""
    return body.encode("utf-8")


def _make_header(*, entity_identifier, entity_scheme, start, end, ctx_duration) -> str:
    return (
        '<ix:header><ix:hidden><ix:resources>'
        f'<link:schemaRef xlink:type="simple" xlink:href="{ESRS_NS}/esrs_all.xsd"/>'
        f'<xbrli:context id="{ctx_duration}">'
        f'<xbrli:entity><xbrli:identifier scheme="{_esc(entity_scheme)}">{_esc(entity_identifier)}</xbrli:identifier></xbrli:entity>'
        f'<xbrli:period><xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate></xbrli:period>'
        "</xbrli:context>"
        f'<xbrli:context id="{ctx_duration}-prior">'
        f'<xbrli:entity><xbrli:identifier scheme="{_esc(entity_scheme)}">{_esc(entity_identifier)}</xbrli:identifier></xbrli:entity>'
        f'<xbrli:period><xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate></xbrli:period>'
        "</xbrli:context>"
        '<xbrli:unit id="u_eur"><xbrli:measure>iso4217:EUR</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="u_tco2e"><xbrli:measure>utr:tCO2e</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="u_pure"><xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="u_tonne"><xbrli:measure>utr:tonnes</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="u_mwh"><xbrli:measure>utr:megawattHours</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="u_m3"><xbrli:measure>utr:cubicMeters</xbrli:measure></xbrli:unit>'
        "</ix:resources></ix:hidden></ix:header>"
    )


def _assurance_html(assurance: Optional[dict], start: str, end: str, org_name: str) -> str:
    if not assurance:
        return ""
    if assurance.get("status") not in ("limited", "reasonable"):
        return ""
    level = "limited assurance" if assurance["status"] == "limited" else "reasonable assurance"
    return (
        "<h2>Assurance statement</h2>"
        f"<p><b>{_esc(level.title())}</b> on the sustainability statement of {_esc(org_name)} "
        f"for the period {start} to {end}.</p>"
        f"<p>Firm: {_esc(assurance.get('firm') or '')} · Date: {_esc(assurance.get('date') or '')}</p>"
        f"<p>{_esc(assurance.get('statement') or '')}</p>"
    )
