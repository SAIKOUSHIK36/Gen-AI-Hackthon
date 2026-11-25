"""Executive ReportLab PDF generator for PS 158 Workload Narrative Assistant."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_executive_pdf(
    analytics: dict[str, Any],
    narrative_result: dict[str, Any],
    pii_audit: dict[str, Any] | None = None,
) -> bytes:
    """Build a professionally formatted executive workload & accountability PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="PS 158 Executive Public Service Workload Report",
    )

    styles = getSampleStyleSheet()
    navy = colors.HexColor("#0F172A")
    slate = colors.HexColor("#334155")
    accent = colors.HexColor("#1D4ED8")
    emerald = colors.HexColor("#047857")
    emerald_bg = colors.HexColor("#ECFDF5")
    light_bg = colors.HexColor("#F8FAFC")
    border_col = colors.HexColor("#CBD5E1")

    title_style = ParagraphStyle(
        "PS158Title",
        parent=styles["Heading1"],
        fontSize=17,
        leading=21,
        textColor=navy,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "PS158Subtitle",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=slate,
        spaceAfter=10,
    )
    h2_style = ParagraphStyle(
        "PS158H2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=accent,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "PS158Body",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13.5,
        textColor=navy,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "PS158Cell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10.5,
        textColor=navy,
    )
    cell_header_style = ParagraphStyle(
        "PS158CellHeader",
        parent=styles["Normal"],
        fontSize=8,
        leading=10.5,
        textColor=colors.white,
    )

    story: list[Any] = []
    kpis = analytics.get("kpis", {})
    date_range = kpis.get("date_range", {})
    narrative = narrative_result.get("narrative", {})
    mode = narrative_result.get("mode", "deterministic_fallback")
    model = narrative_result.get("model", "N/A")

    # Header
    story.append(Paragraph("PS 158: Public Service Workload &amp; Accountability Briefing", title_style))
    gen_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(
        Paragraph(
            f"Reporting Window: <b>{escape(str(date_range.get('start', 'N/A')))}</b> to <b>{escape(str(date_range.get('end', 'N/A')))}</b>"
            f" &nbsp;|&nbsp; Generated: {escape(gen_ts)} &nbsp;|&nbsp; Engine: {escape(str(model))} ({escape(str(mode))})",
            subtitle_style,
        )
    )

    # Privacy Compliance Stamp
    dropped_cnt = len((pii_audit or {}).get("dropped_pii_columns", []))
    scrubbed_cnt = (pii_audit or {}).get("total_inline_pii_scrubbed", 0)
    stamp_table = Table(
        [
            [
                Paragraph(
                    f"<b>PRIVACY SHIELD VERIFIED (ZERO CITIZEN PII):</b> Layer 2 stripped {dropped_cnt} PII column(s) "
                    f"and scrubbed {scrubbed_cnt} inline PII pattern(s). Only anonymized municipal worker IDs appear below.",
                    ParagraphStyle("Stamp", parent=body_style, fontSize=8.5, textColor=emerald, spaceAfter=0),
                )
            ]
        ],
        colWidths=[7.3 * inch],
    )
    stamp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), emerald_bg),
                ("BOX", (0, 0), (-1, -1), 0.75, emerald),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(stamp_table)
    story.append(Spacer(1, 10))

    # Executive KPI Grid
    kpi_data = [
        [
            Paragraph("<b>Total Requests</b><br/>" + str(kpis.get("total_requests", 0)), cell_style),
            Paragraph(
                f"<b>Completed vs Remaining</b><br/>{kpis.get('completed_count', 0)} / {kpis.get('remaining_count', 0)}",
                cell_style,
            ),
            Paragraph(f"<b>Completion Rate</b><br/>{kpis.get('completion_rate_pct', 0)}%", cell_style),
            Paragraph(
                f"<b>SLA Compliance</b><br/>{kpis.get('sla_compliance_pct', 0)}% ({kpis.get('overdue_remaining_count', 0)} overdue)",
                cell_style,
            ),
            Paragraph(
                f"<b>Avg / Median Resolution</b><br/>{kpis.get('avg_resolution_hours', 0)}h / {kpis.get('median_resolution_hours', 0)}h",
                cell_style,
            ),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[1.35 * inch, 1.55 * inch, 1.2 * inch, 1.65 * inch, 1.55 * inch])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                ("GRID", (0, 0), (-1, -1), 0.5, border_col),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 6))

    # AI Narrative Sections
    story.append(Paragraph("1. Executive Administrative Summary", h2_style))
    story.append(Paragraph(escape(str(narrative.get("executive_summary", ""))), body_style))

    story.append(Paragraph("2. Time-Period Workload &amp; Backlog Trajectory", h2_style))
    story.append(Paragraph(escape(str(narrative.get("workload_and_backlog_analysis", ""))), body_style))

    story.append(Paragraph("3. Service Category Bottlenecks", h2_style))
    for item in narrative.get("category_bottlenecks", []):
        if isinstance(item, dict):
            cat = escape(str(item.get("category", "")))
            ev = escape(str(item.get("evidence", "")))
            rec = escape(str(item.get("recommended_action", "")))
            story.append(Paragraph(f"<b>• {cat}:</b> {ev} <i>Intervention:</i> {rec}", body_style))
        else:
            story.append(Paragraph(f"• {escape(str(item))}", body_style))

    story.append(Paragraph("4. Government Worker Accountability &amp; Actions Audit", h2_style))
    story.append(Paragraph(escape(str(narrative.get("worker_accountability_audit", ""))), body_style))

    # Category Breakdown Table
    story.append(Paragraph("5. Service Category Performance Breakdown", h2_style))
    cat_rows = [
        [
            Paragraph("<b>Category</b>", cell_header_style),
            Paragraph("<b>Total</b>", cell_header_style),
            Paragraph("<b>Completed</b>", cell_header_style),
            Paragraph("<b>Remaining</b>", cell_header_style),
            Paragraph("<b>Comp %</b>", cell_header_style),
            Paragraph("<b>Avg Hrs</b>", cell_header_style),
            Paragraph("<b>SLA %</b>", cell_header_style),
        ]
    ]
    for cat in analytics.get("categories", []):
        cat_rows.append(
            [
                Paragraph(escape(str(cat["service_category"])), cell_style),
                Paragraph(escape(str(cat["total_requests"])), cell_style),
                Paragraph(escape(str(cat["completed"])), cell_style),
                Paragraph(escape(str(cat["remaining"])), cell_style),
                Paragraph(f"{cat['completion_rate_pct']}%", cell_style),
                Paragraph(f"{cat['avg_resolution_hours']}h", cell_style),
                Paragraph(f"{cat['sla_compliance_pct']}%", cell_style),
            ]
        )
    cat_table = Table(
        cat_rows,
        colWidths=[2.3 * inch, 0.7 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.9 * inch],
        repeatRows=1,
    )
    cat_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("GRID", (0, 0), (-1, -1), 0.4, border_col),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(cat_table)
    story.append(Spacer(1, 8))

    # Worker Accountability Table
    story.append(Paragraph("6. Anonymized Worker Accountability Roster", h2_style))
    worker_rows = [
        [
            Paragraph("<b>Worker ID</b>", cell_header_style),
            Paragraph("<b>Department</b>", cell_header_style),
            Paragraph("<b>Assigned</b>", cell_header_style),
            Paragraph("<b>Done / Rem</b>", cell_header_style),
            Paragraph("<b>SLA %</b>", cell_header_style),
            Paragraph("<b>Primary Action Taken</b>", cell_header_style),
            Paragraph("<b>Status Flag</b>", cell_header_style),
        ]
    ]
    for w in analytics.get("worker_audit", [])[:25]:
        worker_rows.append(
            [
                Paragraph(f"<b>{escape(str(w['worker_id']))}</b>", cell_style),
                Paragraph(escape(str(w["primary_category"])), cell_style),
                Paragraph(escape(str(w["assigned_count"])), cell_style),
                Paragraph(f"{w['completed_count']} / {w['remaining_count']}", cell_style),
                Paragraph(f"{w['sla_compliance_pct']}%", cell_style),
                Paragraph(escape(str(w["primary_action"])), cell_style),
                Paragraph(escape(str(w["accountability_flag"])), cell_style),
            ]
        )
    worker_table = Table(
        worker_rows,
        colWidths=[0.8 * inch, 1.55 * inch, 0.65 * inch, 0.8 * inch, 0.6 * inch, 1.7 * inch, 1.2 * inch],
        repeatRows=1,
    )
    worker_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("GRID", (0, 0), (-1, -1), 0.4, border_col),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(worker_table)
    story.append(Spacer(1, 10))

    # Administrative Recommendations
    story.append(Paragraph("7. Recommended Administrative Interventions", h2_style))
    for rec in narrative.get("administrative_recommendations", []):
        if isinstance(rec, dict):
            story.append(
                Paragraph(
                    f"<b>[{escape(str(rec.get('priority', 'Action')))}]</b> {escape(str(rec.get('action', '')))} "
                    f"<i>(Impact: {escape(str(rec.get('expected_impact', '')))})</i>",
                    body_style,
                )
            )
        else:
            story.append(Paragraph(f"• {escape(str(rec))}", body_style))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.6, color=border_col))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            escape(str(narrative.get("privacy_attestation", "Zero citizen PII processed in report generation."))),
            ParagraphStyle("Footer", parent=subtitle_style, fontSize=8, textColor=slate),
        )
    )

    doc.build(story)
    return buffer.getvalue()
