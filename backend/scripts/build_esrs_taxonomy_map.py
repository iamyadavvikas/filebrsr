"""Generate the committed ESRS digital-taxonomy map (app/esrs_taxonomy_map.json).

Downloads the official EFRAG ESRS Set 1 XBRL Taxonomy (2024) reference linkbase
and core schema, then cross-references every registry datapoint against the
taxonomy's own (Disclosure Requirement, paragraph) references. Only elements
that can be tagged as XBRL facts are kept (non-abstract, xbrli:item, not an
axis/member/table). Datapoints the taxonomy does not define at paragraph level
are intentionally left unmapped -- the report builder falls back to the
section-level text block instead of fabricating element names.

Sources (official, published 2024-08-30):
  https://xbrl.efrag.org/taxonomy/esrs/2023-12-22/common/esrs_cor.xsd
  https://xbrl.efrag.org/taxonomy/esrs/2023-12-22/common/references/ref_esrs.xml

Run from backend/:  python scripts/build_esrs_taxonomy_map.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

TAXONOMY_BASE = "https://xbrl.efrag.org/taxonomy/esrs/2023-12-22"
NS_DATE = "2023-12-22"
PUBLISHED = "2024-08-30"
OUT = Path(__file__).resolve().parent.parent / "app" / "esrs_taxonomy_map.json"

XSD = "{http://www.w3.org/2001/XMLSchema}"
XLINK = "{http://www.w3.org/1999/xlink}"
XBRLI = "{http://www.xbrl.org/2003/instance}"


def _download(name: str) -> bytes:
    url = f"{TAXONOMY_BASE}/common/{name}"
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 - official HTTPS
        return resp.read()


def parse_concepts(xsd: bytes) -> dict[str, dict]:
    concepts: dict[str, dict] = {}
    for _ev, el in ET.iterparse(__import__("io").BytesIO(xsd), events=("end",)):
        if el.tag == XSD + "element" and el.attrib.get("name"):
            concepts[el.attrib["name"]] = {
                "abstract": el.attrib.get("abstract") == "true",
                "substitutionGroup": (el.attrib.get("substitutionGroup") or "").split(":")[-1],
                "periodType": el.attrib.get(XBRLI + "periodType") or "",
                "type": (el.attrib.get("type") or "").split(":")[-1],
            }
        el.clear()
    return concepts


def parse_references(ref_xml: bytes) -> dict[str, dict]:
    root = ET.fromstring(ref_xml)
    locs: dict[str, str] = {}
    refs: dict[str, dict] = {}
    arcs: list[tuple[str, str]] = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "loc":
            label = el.attrib.get(XLINK + "label")
            href = (el.attrib.get(XLINK + "href") or "").split("#")[-1]
            if href:
                locs[label] = href
        elif tag == "reference":
            parts = {}
            for child in el:
                parts[child.tag.rsplit("}", 1)[-1]] = (child.text or "").strip()
            refs[el.attrib.get(XLINK + "label")] = parts
        elif tag == "referenceArc":
            arcs.append((el.attrib.get(XLINK + "from"), el.attrib.get(XLINK + "to")))
    by_concept: dict[str, dict] = {}
    for fr, to in arcs:
        if fr in locs and to in refs:
            by_concept[locs[fr]] = refs[to]
    return by_concept


def _blank(name: str) -> bool:
    return "Axis" in name or "Member" in name or "Table" in name or "Domain" in name


def main() -> int:
    concepts = parse_concepts(_download("esrs_cor.xsd"))
    refs = parse_references(_download("references/ref_esrs.xml"))
    refs = {k[5:] if k.startswith("esrs_") else k: v for k, v in refs.items()}

    # fact-like concepts, keyed by (Section, Paragraph) as cited in the taxonomy.
    by_paragraph: dict[str, list[dict]] = {}
    textblocks: dict[str, list[dict]] = {}
    tagged = 0
    for local in sorted(set(concepts) & set(refs)):
        attrs, ref = concepts[local], refs[local]
        section, para = ref.get("Section"), ref.get("Paragraph")
        if not section or not para:
            continue
        if attrs["abstract"] or attrs["substitutionGroup"] != "item" or _blank(local):
            continue
        entry = {
            "concept": local,
            "periodType": attrs["periodType"],
            "type": attrs["type"],
            "requirement": ref.get("MandatoryDatapoint", ""),
            "datapointId": ref.get("DatapointId", ""),
        }
        key = f"{section}::{para}"
        by_paragraph.setdefault(key, []).append(entry)
        if attrs["type"] == "textBlockItemType":
            textblocks.setdefault(section, []).append(entry)
        tagged += 1

    payload = {
        "source": "EFRAG ESRS Set 1 XBRL Taxonomy",
        "namespace": TAXONOMY_BASE,
        "entry_point": f"{TAXONOMY_BASE}/esrs_all.xsd",
        "core_schema": f"{TAXONOMY_BASE}/common/esrs_cor.xsd",
        "ns_date": NS_DATE,
        "published": PUBLISHED,
        "concept_count": tagged,
        "paragraph_keys": len(by_paragraph),
        "section_textblocks": {k: v for k, v in sorted(textblocks.items())},
        "by_paragraph": dict(sorted(by_paragraph.items())),
    }
    OUT.write_text(json.dumps(payload, indent=1))
    print(f"wrote {OUT} ({OUT.stat().st_size // 1000} KB, {tagged} tagged concepts, "
          f"{len(by_paragraph)} paragraph keys, {len(textblocks)} section text-blocks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())