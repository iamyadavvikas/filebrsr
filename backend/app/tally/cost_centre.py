"""
Cost-centre allocation utilities (Tally Slice 5).

When a Tally line is allocated across multiple cost centres (e.g. one
₹100 000 freight charge split 60 % Mumbai / 40 % Delhi), we need to emit
one ``raw_records`` row per centre so facility-level rollups work
without a post-hoc allocation join.

This module exposes a single function, :func:`split_by_cost_centre`,
that takes a :class:`app.tally.parser.TallyLineItem` and returns a list
of line items:

  * If the line has no allocations, returns ``[line]`` unchanged.
  * If the line has exactly one allocation, returns ``[line']`` with the
    ``cost_centre_name`` / ``cost_centre_category`` resolved (the dataclass
    itself doesn't carry those convenience fields; the resolved values
    are surfaced through the small :class:`AllocatedLine` wrapper).
  * If the line has multiple allocations, splits the base value and tax
    proportionally to each allocation's amount. The last split absorbs
    any rounding remainder so the sum of splits equals the original
    base value to the exact paisa.

The split function is **pure**: it does not mutate the input line.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal

from app.tally.parser import CostCentreAllocation, TallyLineItem


@dataclass(frozen=True)
class AllocatedLine:
    """A line plus the cost-centre context it was split into.

    Kept separate from :class:`TallyLineItem` so the parser-level
    dataclass stays stable across slices. The ingest path reads
    ``cost_centre_name`` / ``cost_centre_category`` off this wrapper.
    """

    line: TallyLineItem
    cost_centre_name: str | None
    cost_centre_category: str | None


# Paisa precision; matches numeric(18, 2) on raw_records.base_value.
_PAISA = Decimal("0.01")


def _quantise(value: Decimal) -> Decimal:
    return value.quantize(_PAISA, rounding=ROUND_HALF_UP)


def _scale(value: Decimal, ratio: Decimal) -> Decimal:
    return _quantise(value * ratio)


def split_by_cost_centre(line: TallyLineItem) -> list[AllocatedLine]:
    """Split a line into one entry per cost-centre allocation.

    Allocation maths uses Decimal throughout and reconciles rounding by
    crediting the residual to the largest allocation (avoids a long-tail
    of off-by-one paisa errors on a 50k-line ingest)."""
    allocs = line.cost_centre_allocations

    if not allocs:
        return [AllocatedLine(line=line, cost_centre_name=None, cost_centre_category=None)]

    if len(allocs) == 1:
        only = allocs[0]
        return [AllocatedLine(
            line=line,
            cost_centre_name=only.name,
            cost_centre_category=only.category,
        )]

    # Multi-centre: split base / cgst / sgst / igst / cess proportionally
    # by allocation amount. If amounts are zero (shouldn't happen but be
    # defensive), fall back to equal split.
    total_alloc = sum((a.amount for a in allocs), Decimal(0))
    n = len(allocs)
    if total_alloc == 0:
        ratios = [Decimal(1) / n for _ in allocs]
    else:
        ratios = [a.amount / total_alloc for a in allocs]

    splits: list[AllocatedLine] = []
    accum_base = Decimal(0)
    accum_cgst = Decimal(0)
    accum_sgst = Decimal(0)
    accum_igst = Decimal(0)
    accum_cess = Decimal(0)
    accum_qty: Decimal | None = None if line.quantity is None else Decimal(0)

    for i, (alloc, ratio) in enumerate(zip(allocs, ratios, strict=True)):
        is_last = i == n - 1

        if is_last:
            # Residual to keep totals exact.
            base = _quantise(line.base_value - accum_base)
            cgst = _quantise(line.cgst - accum_cgst)
            sgst = _quantise(line.sgst - accum_sgst)
            igst = _quantise(line.igst - accum_igst)
            cess = _quantise(line.cess - accum_cess)
            qty = None if line.quantity is None else _quantise(line.quantity - (accum_qty or Decimal(0)))
        else:
            base = _scale(line.base_value, ratio)
            cgst = _scale(line.cgst, ratio)
            sgst = _scale(line.sgst, ratio)
            igst = _scale(line.igst, ratio)
            cess = _scale(line.cess, ratio)
            qty = None if line.quantity is None else _scale(line.quantity, ratio)
            accum_base += base
            accum_cgst += cgst
            accum_sgst += sgst
            accum_igst += igst
            accum_cess += cess
            if accum_qty is not None and qty is not None:
                accum_qty += qty

        split_line = replace(
            line,
            base_value=base, cgst=cgst, sgst=sgst, igst=igst, cess=cess,
            quantity=qty,
            # Keep the original allocations on each split so audit replay
            # can reconstruct the parent allocation if needed.
        )
        splits.append(AllocatedLine(
            line=split_line,
            cost_centre_name=alloc.name,
            cost_centre_category=alloc.category,
        ))

    return splits


__all__ = ["AllocatedLine", "CostCentreAllocation", "split_by_cost_centre"]
