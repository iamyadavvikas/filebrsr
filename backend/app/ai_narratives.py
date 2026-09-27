"""DR-family narrative prompts (ESRS 2 + BRSR Section B).

Numbers extract with regex; prose does not. These builders produce
family-scoped prompts that ask the model for **quote-grounded** extractions:
every returned item must carry a verbatim quote from the source text, so
:func:`groundedness` can score an output without human review and the
flywheel can reject ungrounded claims before they reach the review queue.

Families mirror the disclosure structure, not the model vendor: callers
inject their own async ``llm_call(prompt) -> str`` (Claude/Gemini/Groq
wrappers in ``app.ai_extraction`` all fit), which keeps this module
unit-testable with a stub.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

FAMILIES: dict[str, dict[str, Any]] = {
    "esrs2-gov": {
        "title": "ESRS 2 governance (GOV-1)",
        "drs": ["GOV-1"],
        "wants": "body composition/diversity, roles on IRO oversight, reporting lines, sustainability expertise",
    },
    "esrs2-sbm": {
        "title": "ESRS 2 strategy & business model (SBM-1)",
        "drs": ["SBM-1"],
        "wants": "significant sectors, revenue splits, value-chain description, key inputs/outputs",
    },
    "esrs2-mdr-p": {
        "title": "Minimum disclosure: policies (MDR-P)",
        "drs": ["MDR-P"],
        "wants": "policy scope/coverage, owner, objective, horizon, strategy linkage, gaps where no policy exists",
    },
    "esrs2-mdr-a": {
        "title": "Minimum disclosure: actions (MDR-A)",
        "drs": ["MDR-A"],
        "wants": "key actions, scope (own ops vs value chain), resources, timelines, progress status",
    },
    "esrs2-mdr-m": {
        "title": "Minimum disclosure: metrics (MDR-M)",
        "drs": ["MDR-M"],
        "wants": "metrics used, methods/assumptions, targets linkage, estimation uncertainty",
    },
    "brsr-section-b": {
        "title": "BRSR Section B management & process (P1-P9)",
        "drs": ["B"],
        "wants": "policy availability per principle, board approval, web links, grievance mechanisms",
    },
}

RESPONSE_SCHEMA = (
    'Return ONLY valid JSON: {"items": [{"dr": "<DR code>", '
    '"summary": "<one sentence>", "quote": "<verbatim span from TEXT>"}]}. '
    "Omit DRs with no support in TEXT. Never invent quotes."
)


def build_prompt(family: str, text: str) -> str:
    """Render the extraction prompt for a DR family."""
    if family not in FAMILIES:
        raise ValueError(f"unknown narrative family {family!r}; choices: {sorted(FAMILIES)}")
    fam = FAMILIES[family]
    drs = ", ".join(fam["drs"])
    return (
        f"You extract sustainability disclosure narratives for {fam['title']} "
        f"(DRs: {drs}) from an annual/sustainability report.\n"
        f"Capture: {fam['wants']}.\n"
        f"{RESPONSE_SCHEMA}\n\nTEXT:\n{text}"
    )


def parse_narrative_response(response_text: str) -> list[dict[str, Any]]:
    """Parse the model JSON into item dicts (tolerates prose wrappers)."""
    import json as _json
    import re as _re

    try:
        data = _json.loads(response_text)
    except _json.JSONDecodeError:
        m = _re.search(r"\{[\s\S]*\}", response_text)
        if not m:
            return []
        try:
            data = _json.loads(m.group())
        except _json.JSONDecodeError:
            return []
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict) and i.get("dr")]


def groundedness(items: list[dict[str, Any]], source_text: str) -> dict[str, Any]:
    """Quote-groundedness score: fraction of items whose quote is verbatim.

    The flywheel's quality signal for narrative extraction — measurable
    without human labels. Empty quotes and missing DRs count as ungrounded.
    """
    if not items:
        return {"n": 0, "grounded": 0, "score": 0.0, "ungrounded_idx": []}
    ungrounded = [
        i for i, it in enumerate(items)
        if not it.get("dr") or not it.get("quote") or str(it["quote"]) not in (source_text or "")
    ]
    n = len(items)
    g = n - len(ungrounded)
    return {"n": n, "grounded": g, "score": round(g / n, 3), "ungrounded_idx": ungrounded}


async def extract_narratives(
    text: str,
    family: str,
    llm_call: Callable[[str], Awaitable[str]],
) -> dict[str, Any]:
    """Run one family prompt through an injected LLM callable."""
    prompt = build_prompt(family, text)
    raw = await llm_call(prompt)
    items = parse_narrative_response(raw)
    score = groundedness(items, text)
    return {
        "family": family,
        "drs": FAMILIES[family]["drs"],
        "items": items,
        "groundedness": score,
    }
