"""CLI eval harness — score extractors against self-supervised silver labels.

Usage::

    # Score all four extractors over every PDF in a directory
    python -m app.eval_cli --pdf-dir /path/to/pdfs

    # Limit to the first 5 PDFs (faster smoke run)
    python -m app.eval_cli --pdf-dir /path/to/pdfs --limit 5

    # Score one extractor only
    python -m app.eval_cli --pdf-dir /path/to/pdfs --extractor retrieval

    # Dump per-field results to JSON for further analysis
    python -m app.eval_cli --pdf-dir /path/to/pdfs --output /tmp/eval.json

PDFs are matched by filename (no Supabase round-trip): the file stem is
used as the report_id label in the JSON output.

Silver-label algorithm — **leave-one-out**:
    When scoring extractor X, the silver set is built from the consensus
    of the OTHER extractors only. This prevents the trivial bias where
    an extractor's own outputs become part of its own ground truth.

    - regex     → silver from {enhanced, ai}      (both must agree)
    - enhanced  → silver from {regex, ai}         (both must agree)
    - ai        → silver from {regex, enhanced}   (both must agree)
    - retrieval → silver from {regex, enhanced, ai} (≥2 of 3 agree)

The retrieval extractor never participates in any silver, so its scores
are an honest measure of how it compares to the legacy ensemble. This
is what makes the deferred Phase 3.3 decision ("replace agent passes
with retrieval?") measurable rather than vibes-based.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.eval_metrics import (
    EvalReport,
    evaluate,
    merge_reports,
    most_extraneous_fields,
    worst_precision_fields,
    worst_recall_fields,
)
from app.eval_silver import SECTION_KEYS, build_silver_labels, silver_summary
from app.extraction import extract_with_regex
from app.extraction_enhanced import extract_enhanced

logger = logging.getLogger("app.eval_cli")

# Empty-shape dict returned when an extractor is unavailable or failed.
_EMPTY_SECTIONS: dict[str, dict[str, Any]] = {s: {} for s in SECTION_KEYS}


# ─── Per-PDF extraction ──────────────────────────────────────────────────


@dataclass
class _PdfExtractions:
    """All four extractor outputs for one PDF, plus metadata."""

    pdf_path: Path
    report_id: str
    text: str
    regex: dict[str, Any]
    enhanced: dict[str, Any]
    ai: dict[str, Any]
    retrieval: dict[str, Any]


async def _extract_all(
    pdf_path: Path, *, api_key: str, run_retrieval: bool,
    retrieval_max_datapoints: int = 40,
    retrieval_batch_size: int = 5,
    retrieval_top_k: int = 3,
) -> _PdfExtractions | None:
    """Parse a PDF and run all four extractors. Returns None on parse error."""
    # Local imports so the CLI can be invoked without the full backend
    # import graph at the top level (faster --help, fewer side effects).
    from app.ai_extraction import extract_with_ai
    from app.pdf_parser import parse_pdf

    try:
        content = pdf_path.read_bytes()
    except OSError as exc:
        logger.warning("cannot read %s: %s", pdf_path, exc)
        return None

    try:
        doc = parse_pdf(content)
    except Exception as exc:
        logger.warning("parse_pdf failed on %s: %s", pdf_path, exc)
        return None

    # OCR fallback for scanned pages — only if API key present
    if api_key:
        try:
            from app.ocr import ocr_document
            await ocr_document(doc, content, api_key=api_key)
        except Exception as exc:
            logger.warning("OCR failed on %s: %s", pdf_path, exc)

    text = doc.to_text()
    if not text.strip():
        logger.warning("empty text for %s, skipping", pdf_path)
        return None

    # Synchronous extractors first (no rate-limit cost)
    try:
        rx = extract_with_regex(text)
    except Exception as exc:
        logger.warning("regex extractor failed on %s: %s", pdf_path, exc)
        rx = _EMPTY_SECTIONS

    try:
        en = extract_enhanced(text)
    except Exception as exc:
        logger.warning("enhanced extractor failed on %s: %s", pdf_path, exc)
        en = _EMPTY_SECTIONS

    # AI single-shot (cheaper than the 6-pass agent for eval purposes)
    if api_key:
        try:
            ai = await extract_with_ai(text, gemini_key=api_key)
        except Exception as exc:
            logger.warning("ai extractor failed on %s: %s", pdf_path, exc)
            ai = _EMPTY_SECTIONS
    else:
        logger.warning("no GEMINI_API_KEY; ai extractor skipped")
        ai = _EMPTY_SECTIONS

    # Retrieval extractor (Phase 3) — opt-in
    if run_retrieval and api_key:
        try:
            from app.extract_retrieval import (
                extract_with_retrieval,
                select_retrievable_datapoints,
            )
            from app.retrieval import build_in_memory_index

            index = await build_in_memory_index(doc, api_key=api_key)
            datapoints = select_retrievable_datapoints(
                max_count=retrieval_max_datapoints,
            )
            ret = await extract_with_retrieval(
                index=index, datapoints=datapoints, api_key=api_key,
                batch_size=retrieval_batch_size,
                top_k=retrieval_top_k,
            )
        except Exception as exc:
            logger.warning("retrieval extractor failed on %s: %s", pdf_path, exc)
            ret = _EMPTY_SECTIONS
    else:
        ret = _EMPTY_SECTIONS

    return _PdfExtractions(
        pdf_path=pdf_path,
        report_id=pdf_path.stem,
        text=text,
        regex=rx,
        enhanced=en,
        ai=ai,
        retrieval=ret,
    )


# ─── Leave-one-out silver per candidate ──────────────────────────────────


_LEAVE_ONE_OUT: dict[str, tuple[str, ...]] = {
    "regex":     ("enhanced", "ai"),
    "enhanced":  ("regex", "ai"),
    "ai":        ("regex", "enhanced"),
    # retrieval doesn't contribute to any silver, so it gets the full
    # 3-extractor ensemble as ground truth
    "retrieval": ("regex", "enhanced", "ai"),
}


def _build_silver_for(
    extractor: str, extractions: _PdfExtractions,
):
    """Build a silver set scoped for scoring `extractor` (leave-one-out)."""
    sources = _LEAVE_ONE_OUT[extractor]
    kwargs = {}
    if "regex" in sources:
        kwargs["regex"] = extractions.regex
    if "enhanced" in sources:
        kwargs["enhanced"] = extractions.enhanced
    if "ai" in sources:
        kwargs["ai"] = extractions.ai
    # min_agreement defaults to 2 — for 2-source silver that means both
    # must agree, which is intentional (we don't want a single extractor
    # to dictate the silver).
    return build_silver_labels(**kwargs)


def _candidate_output(extractor: str, ex: _PdfExtractions) -> dict[str, Any]:
    return {
        "regex": ex.regex,
        "enhanced": ex.enhanced,
        "ai": ex.ai,
        "retrieval": ex.retrieval,
    }[extractor]


# ─── Pretty printing ─────────────────────────────────────────────────────


def _print_overall(name: str, report: EvalReport) -> None:
    o = report.overall
    print(f"\n=== Extractor: {name} ===")
    print(f"  Silver fields scored : {o.silver_total}")
    print(f"  TP / FP / FN         : {o.tp} / {o.fp} / {o.fn}")
    print(f"  Extraneous (FYI)     : {o.extraneous}")
    print(f"  Precision            : {o.precision:.3f}")
    print(f"  Recall               : {o.recall:.3f}")
    print(f"  F1                   : {o.f1:.3f}")
    print("  By section:")
    print(f"    {'section':<12} {'P':>6} {'R':>6} {'F1':>6}  silver")
    for sec in SECTION_KEYS:
        s = report.by_section.get(sec)
        if s is None:
            continue
        print(f"    {sec:<12} {s.precision:>6.3f} {s.recall:>6.3f} "
              f"{s.f1:>6.3f}  {s.silver_total}")


def _print_failures(name: str, report: EvalReport, *, top: int) -> None:
    fns = worst_recall_fields(report, limit=top)
    fps = worst_precision_fields(report, limit=top)
    extras = most_extraneous_fields(report, limit=top)
    if fns:
        print(f"\n  Top {len(fns)} missed (FN) for {name}:")
        for r in fns:
            print(f"    {r.section}.{r.field_id}  (silver={r.silver_value!r})")
    if fps:
        print(f"\n  Top {len(fps)} wrong (FP) for {name}:")
        for r in fps:
            print(f"    {r.section}.{r.field_id}  "
                  f"silver={r.silver_value!r}  got={r.candidate_value!r}")
    if extras:
        print(f"\n  Top {len(extras)} extraneous for {name}:")
        for r in extras:
            print(f"    {r.section}.{r.field_id}  got={r.candidate_value!r}")


# ─── Main driver ─────────────────────────────────────────────────────────


async def run_eval(
    *,
    pdf_dir: Path,
    extractors: list[str],
    limit: int | None,
    api_key: str,
    top_failures: int,
    output_path: Path | None,
    retrieval_max_datapoints: int = 40,
    retrieval_batch_size: int = 5,
    retrieval_top_k: int = 3,
) -> int:
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if limit is not None:
        pdfs = pdfs[:limit]
    if not pdfs:
        print(f"No PDFs found in {pdf_dir}", file=sys.stderr)
        return 2

    print(f"Found {len(pdfs)} PDF(s) in {pdf_dir}")
    print(f"Extractors under test: {', '.join(extractors)}")
    if not api_key:
        print("WARNING: GEMINI_API_KEY not set; ai + retrieval extractors "
              "will be empty.", file=sys.stderr)

    run_retrieval = "retrieval" in extractors

    # Accumulate per-extractor reports
    per_extractor_reports: dict[str, list[EvalReport]] = {
        e: [] for e in extractors
    }
    per_extractor_silver_total = {e: 0 for e in extractors}

    for i, pdf in enumerate(pdfs, 1):
        print(f"\n[{i}/{len(pdfs)}] {pdf.name}")
        ex = await _extract_all(
            pdf, api_key=api_key, run_retrieval=run_retrieval,
            retrieval_max_datapoints=retrieval_max_datapoints,
            retrieval_batch_size=retrieval_batch_size,
            retrieval_top_k=retrieval_top_k,
        )
        if ex is None:
            print("  ✗ skipped (parse/read error)")
            continue

        for name in extractors:
            silver = _build_silver_for(name, ex)
            summary = silver_summary(silver)
            per_extractor_silver_total[name] += summary["total"]
            cand = _candidate_output(name, ex)
            rep = evaluate(
                candidate=cand, silver=silver, extractor_name=name,
                keep_per_field=output_path is not None,
            )
            per_extractor_reports[name].append(rep)
            print(f"  {name:<10} silver={summary['total']:>3}  "
                  f"P={rep.overall.precision:.2f} "
                  f"R={rep.overall.recall:.2f} "
                  f"F1={rep.overall.f1:.2f}")

    # Aggregate
    merged: dict[str, EvalReport] = {}
    for name, reports in per_extractor_reports.items():
        merged[name] = merge_reports(reports)
        merged[name].extractor_name = name
        # Per-field is dropped by merge_reports; rebuild a flat list across
        # reports for the --output dump (only if user wants it)
        if output_path is not None:
            flat = [r for rep in reports for r in rep.per_field]
            merged[name].per_field = flat

    # Print aggregated summary tables
    print("\n" + "=" * 64)
    print("AGGREGATED RESULTS")
    print("=" * 64)
    for name in extractors:
        _print_overall(name, merged[name])

    for name in extractors:
        _print_failures(name, merged[name], top=top_failures)

    # Side-by-side comparison row
    print("\n" + "-" * 64)
    print(f"{'extractor':<12} {'P':>6} {'R':>6} {'F1':>6}  silver  TP   FP   FN")
    for name in extractors:
        o = merged[name].overall
        print(f"{name:<12} {o.precision:>6.3f} {o.recall:>6.3f} "
              f"{o.f1:>6.3f}  {o.silver_total:>6}  {o.tp:>3}  "
              f"{o.fp:>3}  {o.fn:>3}")

    if output_path is not None:
        out = {
            "pdf_dir": str(pdf_dir),
            "pdf_count": len(pdfs),
            "extractors": extractors,
            "reports": {n: merged[n].to_dict() for n in extractors},
        }
        output_path.write_text(json.dumps(out, indent=2))
        print(f"\nWrote {output_path}")

    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m app.eval_cli",
        description="Self-supervised extraction eval harness.",
    )
    p.add_argument("--pdf-dir", required=True, type=Path,
                   help="Directory containing *.pdf files to evaluate.")
    p.add_argument("--limit", type=int, default=None,
                   help="Only process the first N PDFs (alphabetical).")
    p.add_argument(
        "--extractor", default="all",
        choices=["all", "regex", "enhanced", "ai", "retrieval"],
        help="Which extractor(s) to score. 'all' (default) runs every one.",
    )
    p.add_argument("--top-failures", type=int, default=10,
                   help="How many worst-recall/precision fields to print "
                        "per extractor.")
    p.add_argument("--output", type=Path, default=None,
                   help="Write full per-field results as JSON to this path.")
    p.add_argument("--api-key", type=str, default=None,
                   help="Gemini API key (defaults to settings.GEMINI_API_KEY).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)
    if not args.pdf_dir.is_dir():
        print(f"--pdf-dir {args.pdf_dir} is not a directory", file=sys.stderr)
        return 2
    extractors = (
        ["regex", "enhanced", "ai", "retrieval"]
        if args.extractor == "all"
        else [args.extractor]
    )
    # Lazy-load settings only after arg parsing so --help works without env
    settings = get_settings()
    api_key = args.api_key or settings.GEMINI_API_KEY
    return asyncio.run(run_eval(
        pdf_dir=args.pdf_dir,
        extractors=extractors,
        limit=args.limit,
        api_key=api_key,
        top_failures=args.top_failures,
        output_path=args.output,
        retrieval_max_datapoints=settings.RETRIEVAL_MAX_DATAPOINTS,
        retrieval_batch_size=settings.RETRIEVAL_BATCH_SIZE,
        retrieval_top_k=settings.RETRIEVAL_TOP_K,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
