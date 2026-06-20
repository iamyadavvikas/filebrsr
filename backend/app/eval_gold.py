"""Promote user-corrected fields to *gold* labels (Phase 4.4).

Silver labels (from :mod:`app.eval_silver`) come from extractor consensus
— they're cheap but noisy. Once a field has been corrected to the same
value by enough distinct users (default 20), that value is treated as
**gold**: high-confidence human-verified ground truth that should override
silver in the eval harness.

Source: ``extraction_corrections`` table (Supabase migration v10), which
captures user edits in the dashboard. Each row carries
``(report_id, user_id, section, field_path, corrected_value)``.

Algorithm:
    1. Group corrections by ``(section, field_path)``.
    2. Within each group, normalise every ``corrected_value`` using the
       same rules as silver (Cr/Lakh/Mn, commas, currency, lowercase).
    3. Cluster by normalised equality (1% numeric tolerance).
    4. For each cluster, count *distinct* ``user_id`` s — same user
       correcting the same field 50 times doesn't make it gold.
    5. If the largest cluster has ``>= min_users`` distinct users, emit a
       :class:`GoldLabel` for that field with that value.

This module is pure (no I/O). The CLI / Supabase loader plumbing is a
separate concern and lives wherever the rows are first fetched.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from app.eval_silver import SilverLabel, normalise_value

# Default threshold: 20 distinct users must agree on the same corrected
# value before that field is promoted to gold. Conservative for now — we
# can lower it once we observe how corrections actually cluster.
DEFAULT_MIN_USERS = 20

# Numeric tolerance for clustering, matching silver-label logic.
_NUMERIC_TOL = 0.01


# ─── Types ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GoldLabel:
    """A human-verified canonical value for one (section, field_id) pair.

    Same shape as :class:`SilverLabel` so the eval harness can mix them
    transparently. ``agreement`` is set to ``distinct_users`` so callers
    eyeballing a debug dump can tell apart 3-user from 30-user fields.
    """

    section: str
    field_id: str
    value: str                    # canonical raw value (most common corrected_value)
    normalised: Any               # normalised form (float or lowercased str)
    distinct_users: int           # how many distinct users agreed
    total_corrections: int        # total correction rows for this (sec, field)


# ─── Helpers ─────────────────────────────────────────────────────────────


def _values_equal(a: Any, b: Any) -> bool:
    """Same equality rule as eval_silver — kept local to avoid a private
    cross-module import."""
    if a is None or b is None:
        return a is b
    if isinstance(a, float) and isinstance(b, float):
        if a == 0 and b == 0:
            return True
        denom = max(abs(a), abs(b))
        return abs(a - b) / denom <= _NUMERIC_TOL
    return a == b


# ─── Public API ──────────────────────────────────────────────────────────


def build_gold_labels(
    corrections: Iterable[dict[str, Any]],
    *,
    min_users: int = DEFAULT_MIN_USERS,
) -> dict[str, GoldLabel]:
    """Cluster correction rows and promote agreed values to gold.

    Args:
        corrections: iterable of dict rows from ``extraction_corrections``
            (or any source with the same shape). Required keys per row:

            - ``section``         (str: "section_a" / "section_b" / "section_c")
            - ``field_path``      (str: e.g. "turnover")
            - ``corrected_value`` (str | number)
            - ``user_id``         (str / UUID — used for distinct-user count)

            Rows missing any required key are skipped silently (defensive
            against partial Supabase result shapes).
        min_users: minimum number of *distinct* users that must have
            corrected the field to the same normalised value. Defaults to
            :data:`DEFAULT_MIN_USERS` (20).

    Returns:
        Mapping ``"<section>.<field_id>" -> GoldLabel`` covering only the
        fields that crossed the threshold. Deterministic (key-sorted)
        output.
    """
    if min_users < 1:
        raise ValueError("min_users must be ≥ 1")

    # Group rows by (section, field_path)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in corrections:
        section = row.get("section")
        field_path = row.get("field_path")
        if not section or not field_path:
            continue
        if row.get("corrected_value") is None:
            continue
        if not row.get("user_id"):
            continue
        grouped[(section, field_path)].append(row)

    gold: dict[str, GoldLabel] = {}

    for (section, field_path), rows in grouped.items():
        # Cluster by normalised value. Small N per field; O(n*c) is fine
        # (c = number of distinct value clusters, typically 1–3).
        clusters: list[dict[str, Any]] = []  # each: {norm, raw, users:set, rows:int}
        for row in rows:
            raw = row["corrected_value"]
            norm = normalise_value(raw)
            if norm is None:
                continue
            placed = False
            for c in clusters:
                if _values_equal(norm, c["norm"]):
                    c["users"].add(row["user_id"])
                    c["rows"] += 1
                    placed = True
                    break
            if not placed:
                clusters.append({
                    "norm": norm,
                    "raw": raw,
                    "users": {row["user_id"]},
                    "rows": 1,
                })

        if not clusters:
            continue

        # Pick the cluster with the most distinct users; ties broken by
        # total-row-count then insertion order.
        best = max(
            clusters,
            key=lambda c: (len(c["users"]), c["rows"]),
        )
        if len(best["users"]) < min_users:
            continue

        gold[f"{section}.{field_path}"] = GoldLabel(
            section=section,
            field_id=field_path,
            value=best["raw"],
            normalised=best["norm"],
            distinct_users=len(best["users"]),
            total_corrections=best["rows"],
        )

    return dict(sorted(gold.items()))


def merge_gold_into_silver(
    silver: dict[str, SilverLabel],
    gold: dict[str, GoldLabel],
) -> dict[str, SilverLabel]:
    """Return a new silver-shaped dict where gold labels override silver.

    The eval harness only knows :class:`SilverLabel`, so we wrap each
    gold value in a SilverLabel with a sentinel ``agreement=999`` and a
    single source ``"gold"``. This lets downstream code distinguish
    promoted gold from extractor-consensus silver in debug dumps without
    needing a separate code path.

    Args:
        silver: existing silver labels.
        gold: gold labels from :func:`build_gold_labels`.

    Returns:
        A NEW dict (inputs are not mutated). Keys present only in gold
        are added; keys in both are overridden by gold; keys present only
        in silver pass through unchanged.
    """
    merged = dict(silver)
    for key, g in gold.items():
        merged[key] = SilverLabel(
            section=g.section,
            field_id=g.field_id,
            value=g.value,
            normalised=g.normalised,
            agreement=999,           # sentinel: "this came from gold"
            sources=("gold",),
        )
    return dict(sorted(merged.items()))


def gold_summary(gold: dict[str, GoldLabel]) -> dict[str, Any]:
    """Tiny summary for CLI banners. Pure."""
    if not gold:
        return {"total": 0, "by_section": {}, "min_users": 0, "max_users": 0}
    by_section: dict[str, int] = defaultdict(int)
    user_counts: list[int] = []
    for g in gold.values():
        by_section[g.section] += 1
        user_counts.append(g.distinct_users)
    return {
        "total": len(gold),
        "by_section": dict(by_section),
        "min_users": min(user_counts),
        "max_users": max(user_counts),
    }
