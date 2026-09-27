"""CSRD board readiness pack (PDF).

A one-document briefing for the board/audit committee: coverage hero,
readiness by standard, DMA methodology status, material IROs, top gaps,
and the generated methodology paragraph. Built from the same numbers as
the workspace (gap report + DMA coverage + methodology), so the pack can
never disagree with the screen.
"""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLUE = colors.HexColor("#2563EB")
SLATE = colors.HexColor("#334155")
LIGHT = colors.HexColor("#EEF3FF")


def _styles():
    base = getSampleStyleSheet()
    title = ParagraphStyle("pack_title", parent=base["Title"], fontSize=20, textColor=SLATE, spaceAfter=2)
    h2 = ParagraphStyle("pack_h2", parent=base["Heading2"], fontSize=13, textColor=BLUE,
                        borderPadding=(0, 0, 4, 0), spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("pack_body", parent=base["Normal"], fontSize=9, leading=13, textColor=SLATE)
    small = ParagraphStyle("pack_small", parent=base["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#64748B"))
    cell = ParagraphStyle("pack_cell", parent=base["Normal"], fontSize=8, leading=10, textColor=SLATE)
    return title, h2, body, small, cell


def _std_table(standards: list[dict[str, Any]], cell) -> Table:
    rows = [[Paragraph("<b>Standard</b>", cell), Paragraph("<b>Handled</b>", cell),
             Paragraph("<b>Remaining</b>", cell), Paragraph("<b>Coverage</b>", cell)]]
    for s in standards:
        total = s.get("datapoints", 0) or 0
        handled = s.get("handled", 0) or 0
        pct = f"{round(100.0 * handled / total, 1)}%" if total else "—"
        rows.append([
            Paragraph(f"{s.get('code', '')} — {s.get('name', '')}", cell),
            Paragraph(str(handled), cell),
            Paragraph(str(s.get("remaining", 0)), cell),
            Paragraph(pct, cell),
        ])
    t = Table(rows, colWidths=[9 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DEE9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    return t


def build_board_pack(
    *,
    org_name: str,
    financial_year: str,
    gap: dict[str, Any],
    dma_coverage: dict[str, Any],
    methodology_paragraph: str,
    material_iros: list[dict[str, Any]],
) -> bytes:
    """Render the board pack PDF. All inputs are plain dicts (test-friendly)."""
    title, h2, body, small, cell = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    story: list[Any] = [
        Paragraph("CSRD Board Readiness Pack", title),
        Paragraph(f"{org_name} · {financial_year}", small),
        Spacer(1, 0.4 * cm),
        Paragraph(
            f"Coverage <b>{gap.get('coverage_pct', 0)}%</b> — "
            f"{gap.get('handled', 0)} of {gap.get('total_datapoints', 0)} in-scope datapoints handled, "
            f"{gap.get('effective_gap', 0)} remaining.",
            body,
        ),
        Paragraph("Readiness by standard", h2),
        _std_table(gap.get("standards", []), cell),
        Paragraph("Double materiality status", h2),
        Paragraph(
            f"Material IROs: <b>{dma_coverage.get('material_iros', 0)}</b> "
            f"({dma_coverage.get('covered_iros', 0)} traced to disclosure requirements). "
            f"Methodology: <b>{dma_coverage.get('methodology_status', 'draft')}</b>"
            + (f" (approved by {dma_coverage.get('methodology_approved_by')})."
               if dma_coverage.get("methodology_approved_by") else ".")
            + f" Stakeholder records: <b>{dma_coverage.get('stakeholder_records', 0)}</b>. "
            + ("<b>Audit-ready.</b>" if dma_coverage.get("audit_ready") else "<b>Not yet audit-ready.</b>"),
            body,
        ),
    ]
    orphans = dma_coverage.get("orphan_iro_ids") or []
    if orphans:
        story.append(Paragraph(f"Orphan IROs lacking DR linkage: {', '.join(orphans[:10])}", body))
    if material_iros:
        story.append(Paragraph("Material IROs", h2))
        iro_rows = [[Paragraph("<b>Title</b>", cell), Paragraph("<b>Type</b>", cell), Paragraph("<b>Std</b>", cell)]]
        for r in material_iros[:25]:
            iro_rows.append([
                Paragraph(str(r.get("title", ""))[:120], cell),
                Paragraph(str(r.get("iro_type", "")), cell),
                Paragraph(str(r.get("standard", "")), cell),
            ])
        it = Table(iro_rows, colWidths=[10 * cm, 3 * cm, 3.5 * cm])
        it.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DEE9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(it)
    if methodology_paragraph:
        story.append(Paragraph("Methodology (IRO-1)", h2))
        story.append(Paragraph(methodology_paragraph, body))
    story += [Spacer(1, 0.6 * cm),
              Paragraph("Generated by FileBRSR CSRD workspace from live workspace data.", small)]
    doc.build(story)
    return buf.getvalue()
