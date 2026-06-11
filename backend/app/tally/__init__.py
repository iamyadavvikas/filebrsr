"""
Tally Prime / Tally ERP 9 connector — Slice 0 (file ingest).

Slice 0 surface: parse a Tally voucher XML export, classify each cost-line
HSN code to a GHG scope + Scope-3 category via the static lookup table
under ``lookups/hsn_scope3_v1.json``, and (optionally) persist normalised
rows into the ``raw_records`` table (migration v13).

What's deliberately NOT in slice 0:
  * Tally HTTP-XML push endpoint, ODBC driver, Tally Cloud connector
  * Sarvam-M (Hindi narration) / GPT-4o-mini (English narration) LLM
    classifier for unmapped HSNs
  * GSTR-2A/2B reconciliation
  * e-Way Bill cross-reference
  * Cost-centre hierarchy walk
  * Signed batch export (the SHA-256 hash is captured but not signed)

Public API::

    from app.tally import ingest_tally_xml

    summary = ingest_tally_xml(
        xml_bytes=open("daybook.xml", "rb").read(),
        user_id="...uuid...",
        supabase_client=client,   # or None for a dry-run
    )
    print(summary.lines_parsed, summary.lines_unmapped)
"""

from __future__ import annotations

from app.tally.classifier import (
    Classification,
    classify_hsn,
    classify_with_llm_fallback,
    reset_cache,
)
from app.tally.ingest import IngestSummary, ingest_tally_xml
from app.tally.llm_classifier import (
    DisabledClassifier,
    LLMClassification,
    LLMClassifier,
    MockClassifier,
    OpenAIMiniClassifier,
    SarvamMClassifier,
    get_llm_classifier,
    reset_classifier_cache,
)
from app.tally.parser import TallyLineItem, fiscal_year_for, parse_tally_xml

__all__ = [
    "Classification",
    "DisabledClassifier",
    "IngestSummary",
    "LLMClassification",
    "LLMClassifier",
    "MockClassifier",
    "OpenAIMiniClassifier",
    "SarvamMClassifier",
    "TallyLineItem",
    "classify_hsn",
    "classify_with_llm_fallback",
    "fiscal_year_for",
    "get_llm_classifier",
    "ingest_tally_xml",
    "parse_tally_xml",
    "reset_cache",
    "reset_classifier_cache",
]
