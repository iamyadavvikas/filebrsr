"""Metrics for self-supervised extraction evaluation (Phase 4.2).

Scores a *candidate* extractor output against a *silver* label set
produced by :mod:`app.eval_silver`. Pure functions — no I/O.

Definitions (per ``(section, field_id)``):
    TP — candidate has the field, silver has the field, normalised values match
    FP — candidate has the field, silver has the field, values differ
    FN — silver has the field, candidate omits it
    extraneous — candidate has the field, silver does NOT have it
                 (i.e. neither regex/enhanced/ai had ≥2-agreement on it)

We split FP from "extraneous" because the latter is a weaker signal: an
extra field from the candidate may actually be correct — the legacy
extractors simply didn't find it. The CLI reports both numbers so callers
can decide which to trust.

Precision and recall are computed over the silver-covered field set only:
    precision = TP / (TP + FP)
    recall    = TP / (TP + FN)
    f1        = 2 * P * R / (P + R)

This is the standard set-based IR formulation. Extraneous fields do NOT
enter precision (would unfairly penalise extractors that find real fields
silver missed); they're tracked separately for diagnostic value.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.eval_silver import SECTION_KEYS, SilverLabel, normalise_value

# ─── Types ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FieldResult:
    """Per-field comparison outcome."""

    section: str
    field_id: str
    status: str            # "tp" | "fp" | "fn" | "extraneous"
    silver_value: Any = None
    candidate_value: Any = None


@dataclass
class SectionStats:
    """Per-section roll-up. Mutable so the aggregator can accumulate."""

    section: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    extraneous: int = 0
    silver_total: int = 0

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


@dataclass
class EvalReport:
    """Complete evaluation result for one (extractor, silver-set) pair."""

    extractor_name: str
    overall: SectionStats
    by_section: dict[str, SectionStats]
    per_field: list[FieldResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable view for the CLI ``--output`` flag."""
        return {
            "extractor": self.extractor_name,
            "overall": _stats_to_dict(self.overall),
            "by_section": {
                s: _stats_to_dict(st) for s, st in self.by_section.items()
            },
            "per_field": [
                {
                    "section": r.section,
                    "field_id": r.field_id,
                    "status": r.status,
                    "silver": _safe_jsonable(r.silver_value),
                    "candidate": _safe_jsonable(r.candidate_value),
                }
                for r in self.per_field
            ],
        }


def _stats_to_dict(s: SectionStats) -> dict[str, Any]:
    return {
        "section": s.section,
        "tp": s.tp,
        "fp": s.fp,
        "fn": s.fn,
        "extraneous": s.extraneous,
        "silver_total": s.silver_total,
        "precision": round(s.precision, 4),
        "recall": round(s.recall, 4),
        "f1": round(s.f1, 4),
    }


def _safe_jsonable(v: Any) -> Any:
    """Coerce a value to something json.dumps can handle."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


# ─── Comparison ──────────────────────────────────────────────────────────


def _candidate_get(
    candidate: dict[str, Any], section: str, field_id: str,
) -> Any:
    """Pull a value from the canonical ``{section: {field_id: value}}`` shape."""
    if not isinstance(candidate, dict):
        return None
    sec = candidate.get(section)
    if not isinstance(sec, dict):
        return None
    return sec.get(field_id)


def _values_match(silver_norm: Any, candidate_raw: Any) -> bool:
    """Compare a silver-normalised value to a raw candidate value.

    Re-uses ``normalise_value`` so the same Cr/Lakh/Mn/comma rules apply.
    Uses 1% numeric tolerance for floats (matches silver-side equality).
    """
    cand_norm = normalise_value(candidate_raw)
    if silver_norm is None or cand_norm is None:
        return silver_norm is cand_norm
    if isinstance(silver_norm, float) and isinstance(cand_norm, float):
        if silver_norm == 0 and cand_norm == 0:
            return True
        denom = max(abs(silver_norm), abs(cand_norm))
        return abs(silver_norm - cand_norm) / denom <= 0.01
    return silver_norm == cand_norm


def evaluate(
    *,
    candidate: dict[str, Any],
    silver: dict[str, SilverLabel],
    extractor_name: str = "candidate",
    keep_per_field: bool = True,
) -> EvalReport:
    """Score ``candidate`` against ``silver``.

    Args:
        candidate: extractor output in ``{section_a, section_b, section_c}``
            shape (same shape as silver came from).
        silver: silver labels keyed ``"<section>.<field_id>"``.
        extractor_name: label for the report (shown in CLI output).
        keep_per_field: when False, omits the ``per_field`` list to save
            memory for big runs. Aggregates are always computed.

    Returns:
        An :class:`EvalReport` with overall + per-section stats and
        (optionally) per-field results.
    """
    by_section: dict[str, SectionStats] = {
        s: SectionStats(section=s) for s in SECTION_KEYS
    }
    per_field: list[FieldResult] = []

    # Silver-covered fields → TP / FP / FN classification
    silver_by_section: dict[str, set[str]] = defaultdict(set)
    for key, label in silver.items():
        silver_by_section[label.section].add(label.field_id)
        stats = by_section.setdefault(
            label.section, SectionStats(section=label.section),
        )
        stats.silver_total += 1

        cand_raw = _candidate_get(candidate, label.section, label.field_id)
        cand_norm = normalise_value(cand_raw)
        if cand_norm is None:
            stats.fn += 1
            if keep_per_field:
                per_field.append(FieldResult(
                    section=label.section, field_id=label.field_id,
                    status="fn",
                    silver_value=label.value, candidate_value=None,
                ))
        elif _values_match(label.normalised, cand_raw):
            stats.tp += 1
            if keep_per_field:
                per_field.append(FieldResult(
                    section=label.section, field_id=label.field_id,
                    status="tp",
                    silver_value=label.value, candidate_value=cand_raw,
                ))
        else:
            stats.fp += 1
            if keep_per_field:
                per_field.append(FieldResult(
                    section=label.section, field_id=label.field_id,
                    status="fp",
                    silver_value=label.value, candidate_value=cand_raw,
                ))

    # Extraneous fields — candidate has them, silver doesn't
    if isinstance(candidate, dict):
        for section in SECTION_KEYS:
            sec_dict = candidate.get(section)
            if not isinstance(sec_dict, dict):
                continue
            stats = by_section.setdefault(
                section, SectionStats(section=section),
            )
            for field_id, raw in sec_dict.items():
                if field_id in silver_by_section[section]:
                    continue
                if normalise_value(raw) is None:
                    continue
                stats.extraneous += 1
                if keep_per_field:
                    per_field.append(FieldResult(
                        section=section, field_id=field_id,
                        status="extraneous",
                        silver_value=None, candidate_value=raw,
                    ))

    # Aggregate overall
    overall = SectionStats(section="overall")
    for s in by_section.values():
        overall.tp += s.tp
        overall.fp += s.fp
        overall.fn += s.fn
        overall.extraneous += s.extraneous
        overall.silver_total += s.silver_total

    # Stable per-field ordering
    per_field.sort(key=lambda r: (r.section, r.field_id))

    return EvalReport(
        extractor_name=extractor_name,
        overall=overall,
        by_section=by_section,
        per_field=per_field if keep_per_field else [],
    )


# ─── Diagnostic helpers (for CLI) ────────────────────────────────────────


def worst_recall_fields(
    report: EvalReport, *, limit: int = 10,
) -> list[FieldResult]:
    """Return the FN results (silver had it, candidate missed it).

    Caller typically prints these to surface "fields the candidate
    systematically fails to extract".
    """
    return [r for r in report.per_field if r.status == "fn"][:limit]


def worst_precision_fields(
    report: EvalReport, *, limit: int = 10,
) -> list[FieldResult]:
    """Return the FP results (silver and candidate disagree).

    These are the most informative for prompt/extractor debugging — they
    flag hallucinations or unit-confusion bugs.
    """
    return [r for r in report.per_field if r.status == "fp"][:limit]


def most_extraneous_fields(
    report: EvalReport, *, limit: int = 10,
) -> list[FieldResult]:
    """Fields the candidate produced that silver didn't have.

    Could be legitimate (silver missed them) or hallucination. Surfacing
    helps decide which.
    """
    return [r for r in report.per_field if r.status == "extraneous"][:limit]


# ─── Multi-report aggregation ────────────────────────────────────────────


def merge_reports(reports: list[EvalReport]) -> EvalReport:
    """Sum stats across multiple per-report evaluations.

    Returns an :class:`EvalReport` with ``extractor_name`` taken from the
    first report and ``per_field`` empty (per-field comparisons are not
    deduped across reports — call :func:`evaluate` per report and keep
    them separate if you need that detail).
    """
    if not reports:
        return EvalReport(
            extractor_name="empty",
            overall=SectionStats(section="overall"),
            by_section={s: SectionStats(section=s) for s in SECTION_KEYS},
            per_field=[],
        )
    merged_by_section: dict[str, SectionStats] = {
        s: SectionStats(section=s) for s in SECTION_KEYS
    }
    overall = SectionStats(section="overall")
    for rep in reports:
        for section, s in rep.by_section.items():
            tgt = merged_by_section.setdefault(
                section, SectionStats(section=section),
            )
            tgt.tp += s.tp
            tgt.fp += s.fp
            tgt.fn += s.fn
            tgt.extraneous += s.extraneous
            tgt.silver_total += s.silver_total
        overall.tp += rep.overall.tp
        overall.fp += rep.overall.fp
        overall.fn += rep.overall.fn
        overall.extraneous += rep.overall.extraneous
        overall.silver_total += rep.overall.silver_total
    return EvalReport(
        extractor_name=reports[0].extractor_name,
        overall=overall,
        by_section=merged_by_section,
        per_field=[],
    )
