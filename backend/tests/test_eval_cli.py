"""Tests for app/eval_cli.py — argument parsing, leave-one-out dispatch,
and the run_eval driver with all heavy parts mocked."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app import eval_cli
from app.eval_cli import (
    _LEAVE_ONE_OUT,
    _build_silver_for,
    _candidate_output,
    _parse_args,
    _PdfExtractions,
    main,
    run_eval,
)


def _sec(**kw):
    """Helper: build a {section_a: {...}, section_b: {}, section_c: {}} dict."""
    return {"section_a": kw, "section_b": {}, "section_c": {}}


# ─── Argument parsing ────────────────────────────────────────────────────


def test_parse_args_minimal():
    ns = _parse_args(["--pdf-dir", "/tmp"])
    assert ns.pdf_dir == Path("/tmp")
    assert ns.limit is None
    assert ns.extractor == "all"
    assert ns.top_failures == 10
    assert ns.output is None
    assert ns.api_key is None


def test_parse_args_full():
    ns = _parse_args([
        "--pdf-dir", "/x", "--limit", "3", "--extractor", "retrieval",
        "--top-failures", "5", "--output", "/tmp/o.json", "--api-key", "k",
    ])
    assert ns.limit == 3
    assert ns.extractor == "retrieval"
    assert ns.top_failures == 5
    assert ns.output == Path("/tmp/o.json")
    assert ns.api_key == "k"


def test_parse_args_pdf_dir_required():
    with pytest.raises(SystemExit):
        _parse_args([])


def test_parse_args_invalid_extractor():
    with pytest.raises(SystemExit):
        _parse_args(["--pdf-dir", "/tmp", "--extractor", "magic"])


# ─── Leave-one-out wiring ────────────────────────────────────────────────


def _ex(regex=None, enhanced=None, ai=None, retrieval=None) -> _PdfExtractions:
    empty = {"section_a": {}, "section_b": {}, "section_c": {}}
    return _PdfExtractions(
        pdf_path=Path("/x/test.pdf"), report_id="test", text="",
        regex=regex or empty, enhanced=enhanced or empty,
        ai=ai or empty, retrieval=retrieval or empty,
    )


def test_leave_one_out_map_complete():
    """Every named extractor must have a silver source list, and no
    extractor must contribute to its own silver."""
    for name, sources in _LEAVE_ONE_OUT.items():
        if name == "retrieval":
            # retrieval is the candidate-under-test; it never participates
            assert "retrieval" not in sources
        else:
            assert name not in sources


def test_build_silver_for_regex_uses_enhanced_and_ai():
    """Silver for `regex` must come from enhanced+ai agreement."""
    ex = _ex(
        regex=_sec(only_regex="999"),       # should NOT appear in silver
        enhanced=_sec(shared="42"),
        ai=_sec(shared="42"),
    )
    silver = _build_silver_for("regex", ex)
    assert "section_a.shared" in silver
    assert "section_a.only_regex" not in silver  # regex contribution ignored


def test_build_silver_for_retrieval_uses_all_three_legacy():
    """Retrieval gets the full 3-extractor ensemble silver."""
    ex = _ex(
        regex=_sec(f="1"), enhanced=_sec(f="1"), ai=_sec(f="999"),
        retrieval=_sec(should_not_count="hello"),
    )
    silver = _build_silver_for("retrieval", ex)
    assert "section_a.f" in silver  # 2-of-3 agreement
    # Retrieval's own output mustn't bleed in
    assert "section_a.should_not_count" not in silver


def test_candidate_output_dispatch():
    def tagged(tag):
        return {"section_a": {"tag": tag}, "section_b": {}, "section_c": {}}
    ex = _ex(
        regex=tagged("R"), enhanced=tagged("E"),
        ai=tagged("A"), retrieval=tagged("RT"),
    )
    assert _candidate_output("regex", ex)["section_a"]["tag"] == "R"
    assert _candidate_output("enhanced", ex)["section_a"]["tag"] == "E"
    assert _candidate_output("ai", ex)["section_a"]["tag"] == "A"
    assert _candidate_output("retrieval", ex)["section_a"]["tag"] == "RT"


# ─── main() error paths ──────────────────────────────────────────────────


def test_main_returns_2_when_pdf_dir_missing(tmp_path):
    missing = tmp_path / "nope"
    rc = main(["--pdf-dir", str(missing)])
    assert rc == 2


def test_main_returns_2_when_pdf_dir_is_file(tmp_path):
    f = tmp_path / "x.pdf"
    f.write_bytes(b"")
    rc = main(["--pdf-dir", str(f)])
    assert rc == 2


# ─── run_eval driver (heavy parts mocked) ────────────────────────────────


@pytest.mark.asyncio
async def test_run_eval_no_pdfs_returns_2(tmp_path):
    rc = await run_eval(
        pdf_dir=tmp_path, extractors=["regex"], limit=None,
        api_key="", top_failures=5, output_path=None,
    )
    assert rc == 2


@pytest.mark.asyncio
async def test_run_eval_skips_unparseable_pdfs(tmp_path, capsys):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"not really a pdf")

    # _extract_all returning None simulates an unparseable PDF
    with patch.object(eval_cli, "_extract_all", new=AsyncMock(return_value=None)):
        rc = await run_eval(
            pdf_dir=tmp_path, extractors=["regex"], limit=None,
            api_key="", top_failures=5, output_path=None,
        )
    assert rc == 0
    out = capsys.readouterr().out
    assert "skipped" in out


@pytest.mark.asyncio
async def test_run_eval_aggregates_across_pdfs(tmp_path, capsys):
    # Two fake PDFs
    for name in ("a.pdf", "b.pdf"):
        (tmp_path / name).write_bytes(b"")

    # Build extractions where regex==enhanced (so silver for ai has 2 fields,
    # and ai matches one of them → TP=1, FN=1)
    extractions_a = _PdfExtractions(
        pdf_path=tmp_path / "a.pdf", report_id="a", text="x",
        regex=_sec(f1="1", f2="2"),
        enhanced=_sec(f1="1", f2="2"),
        ai=_sec(f1="1"),  # matches f1, misses f2
        retrieval=_sec(),
    )
    extractions_b = _PdfExtractions(
        pdf_path=tmp_path / "b.pdf", report_id="b", text="x",
        regex=_sec(f3="3"),
        enhanced=_sec(f3="3"),
        ai=_sec(f3="3"),
        retrieval=_sec(),
    )

    async def fake_extract(pdf_path, **_):
        return extractions_a if pdf_path.name == "a.pdf" else extractions_b

    with patch.object(eval_cli, "_extract_all", new=fake_extract):
        rc = await run_eval(
            pdf_dir=tmp_path, extractors=["ai"], limit=None,
            api_key="", top_failures=5, output_path=None,
        )

    assert rc == 0
    out = capsys.readouterr().out
    assert "AGGREGATED RESULTS" in out
    # PDF a: silver={f1,f2}, ai got f1 → TP=1 FN=1
    # PDF b: silver={f3}, ai got f3 → TP=1
    # Aggregated: TP=2 FN=1
    assert "TP / FP / FN         : 2 / 0 / 1" in out


@pytest.mark.asyncio
async def test_run_eval_limit_truncates(tmp_path):
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        (tmp_path / name).write_bytes(b"")

    calls: list[Path] = []

    async def fake_extract(pdf_path, **_):
        calls.append(pdf_path)
        return None  # skip immediately

    with patch.object(eval_cli, "_extract_all", new=fake_extract):
        await run_eval(
            pdf_dir=tmp_path, extractors=["regex"], limit=2,
            api_key="", top_failures=5, output_path=None,
        )

    assert len(calls) == 2
    assert {p.name for p in calls} == {"a.pdf", "b.pdf"}  # sorted, first 2


@pytest.mark.asyncio
async def test_run_eval_writes_output_json(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"")
    out_path = tmp_path / "out.json"

    extractions = _PdfExtractions(
        pdf_path=pdf, report_id="a", text="x",
        regex=_sec(f="1"), enhanced=_sec(f="1"), ai=_sec(f="1"),
        retrieval=_sec(f="1"),
    )

    async def fake_extract(pdf_path, **_):
        return extractions

    with patch.object(eval_cli, "_extract_all", new=fake_extract):
        rc = await run_eval(
            pdf_dir=tmp_path, extractors=["retrieval"], limit=None,
            api_key="", top_failures=5, output_path=out_path,
        )

    assert rc == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert data["pdf_count"] == 1
    assert data["extractors"] == ["retrieval"]
    assert "reports" in data
    assert data["reports"]["retrieval"]["overall"]["tp"] == 1


@pytest.mark.asyncio
async def test_run_eval_all_extractors_each_get_a_report(tmp_path, capsys):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"")

    extractions = _PdfExtractions(
        pdf_path=pdf, report_id="a", text="x",
        regex=_sec(f="1"), enhanced=_sec(f="1"), ai=_sec(f="1"),
        retrieval=_sec(f="1"),
    )

    async def fake_extract(pdf_path, **_):
        return extractions

    with patch.object(eval_cli, "_extract_all", new=fake_extract):
        await run_eval(
            pdf_dir=tmp_path,
            extractors=["regex", "enhanced", "ai", "retrieval"],
            limit=None, api_key="", top_failures=3, output_path=None,
        )

    out = capsys.readouterr().out
    # Each extractor must appear in the aggregated section header
    for name in ("regex", "enhanced", "ai", "retrieval"):
        assert f"=== Extractor: {name} ===" in out
