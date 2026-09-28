"""DR-family narrative prompts: builders + groundedness scoring."""

from __future__ import annotations

import pytest

from app.ai_narratives import (
    FAMILIES,
    build_prompt,
    extract_narratives,
    groundedness,
    parse_narrative_response,
)


def test_all_families_build_scoped_prompts():
    assert set(FAMILIES) == {
        "esrs2-gov", "esrs2-sbm", "esrs2-mdr-p",
        "esrs2-mdr-a", "esrs2-mdr-m", "brsr-section-b",
    }
    for fam in FAMILIES:
        p = build_prompt(fam, "sample text")
        assert "verbatim" in p
        assert "ONLY valid JSON" in p
        for dr in FAMILIES[fam]["drs"]:
            assert dr in p
    with pytest.raises(ValueError):
        build_prompt("nope", "text")


def test_parse_tolerates_prose_wrappers_and_rejects_junk():
    items = parse_narrative_response('Here you go: {"items": [{"dr": "GOV-1", "summary": "s", "quote": "q"}]} done')
    assert len(items) == 1 and items[0]["dr"] == "GOV-1"
    assert parse_narrative_response("no json here") == []
    assert parse_narrative_response('{"items": "notalist"}') == []


def test_groundedness_scores_verbatim_only():
    src = "The board oversees climate risk quarterly."
    items = [
        {"dr": "GOV-1", "summary": "s", "quote": "oversees climate risk"},
        {"dr": "GOV-1", "summary": "s", "quote": "invented phrase here"},
        {"dr": "", "summary": "s", "quote": "The board"},
    ]
    out = groundedness(items, src)
    assert out == {"n": 3, "grounded": 1, "score": 0.333, "ungrounded_idx": [1, 2]}
    assert groundedness([], src) == {"n": 0, "grounded": 0, "score": 0.0, "ungrounded_idx": []}


@pytest.mark.asyncio
async def test_extract_narratives_end_to_end_with_stub_llm():
    src = "Our climate policy covers all operations through 2030."

    async def stub_llm(prompt: str) -> str:
        assert "MDR-P" in prompt
        return '{"items": [{"dr": "MDR-P", "summary": "policy scope", "quote": "covers all operations"}]}'

    out = await extract_narratives(src, "esrs2-mdr-p", stub_llm)
    assert out["family"] == "esrs2-mdr-p"
    assert len(out["items"]) == 1
    assert out["groundedness"]["score"] == 1.0
