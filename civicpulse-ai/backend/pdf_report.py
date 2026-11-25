"""ReportLab PDF report generator for CivicPulse AI Administrative Reports."""

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


def build_administrative_pdf(
    analytics: dict[str, Any],
    report_bundle: dict[str, Any],
    source_name: str = "CivicPulse Dataset",
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="CivicPulse AI - Public Complaint Resolution & Delay Analysis Report",
    )

    styles = getSampleStyleSheet()
    navy = colors.HexColor("#0F172A")
    blue = colors.HexColor("#1D4ED8")
    slate = colors.HexColor("#475569")
    emerald = colors.HexColor("#047857")
    emerald_bg = colors.HexColor("#ECFDF5")
    light_bg = colors.HexColor("#F8FAFC")
    border = colors.HexColor("#CBD5E1")

    title_st = ParagraphStyle("CPTitle", parent=styles["Heading1"], fontSize=16.5, leading=20, textColor=navy, spaceAfter=4)
    sub_st = ParagraphStyle("CPSub", parent=styles["Normal"], fontSize=9, leading=12.5, textColor=slate, spaceAfter=10)
    h2_st = ParagraphStyle("CPH2", parent=styles["Heading2"], fontSize=11.5, leading=14.5, textColor=blue, spaceBefore=10, spaceAfter=5)
    body_st = ParagraphStyle("CPBody", parent=styles["Normal"], fontSize=9.2, leading=13, textColor=navy, spaceAfter=5)
    cell_st = ParagraphStyle("CPCell", parent=styles["Normal"], fontSize=7.8, leading=10, textColor=navy)
    hdr_st = ParagraphStyle("CPHdr", parent=styles["Normal"], fontSize=7.8, leading=10, textColor=colors.white)

    kpis = analytics.get("kpis", {})
    report = report_bundle.get("report", {})
    mode = report_bundle.get("mode", "deterministic_fallback")
    model = report_bundle.get("model", "N/A")
    gen_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story: list[Any] = [
        Paragraph("CivicPulse AI — Public Complaint Resolution &amp; Delay Analysis Report", title_st),
        Paragraph(
            f"Source: <b>{escape(source_name)}</b> &nbsp;|&nbsp; Window: {escape(str(kpis.get('date_range', {}).get('start', 'N/A')))} to "
            f"{escape(str(kpis.get('date_range', {}).get('end', 'N/A')))} &nbsp;|&nbsp; Generated: {escape(gen_ts)} &nbsp;|&nbsp; Engine: {escape(str(model))} ({escape(str(mode))})",
            sub_st,
        ),
    ]

    # Privacy & Grounding Badge
    stamp = Table(
        [
            [
                Paragraph(
                    "<b>ZERO CITIZEN PII &amp; EVIDENCE-GROUNDED:</b> Statistics computed deterministically via Pandas/NumPy/Scikit-learn. "
                    "Recorded delay reasons are strictly separated from unconfirmed inferred patterns.",
                    ParagraphStyle("Stamp", parent=body_st, fontSize=8.3, textColor=emerald, spaceAfter=0),
                )
            ]
        ],
        colWidths=[7.4 * inch],
    )
    stamp.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), emerald_bg),
                ("BOX", (0, 0), (-1, -1), 0.75, emerald),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([stamp, Spacer(1, 8)])

    # KPI Grid
    kpi_grid = Table(
        [
            [
                Paragraph(f"<b>Total Received</b><br/>{kpis.get('total_received', 0)}", cell_st),
                Paragraph(f"<b>Resolved</b><br/>{kpis.get('resolved_count', 0)} ({kpis.get('resolution_rate_pct', 0)}%)", cell_st),
                Paragraph(f"<b>Pending Backlog</b><br/>{kpis.get('total_pending_backlog', 0)} ({kpis.get('pending_rate_pct', 0)}%)", cell_st),
                Paragraph(f"<b>Overdue</b><br/>{kpis.get('overdue_count', 0)} crossed deadline", cell_st),
                Paragraph(f"<b>Avg Resolution</b><br/>{kpis.get('avg_resolution_days', 0)} days", cell_st),
            ]
        ],
        colWidths=[1.35 * inch, 1.45 * inch, 1.6 * inch, 1.55 * inch, 1.45 * inch],
    )
    kpi_grid.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                ("GRID", (0, 0), (-1, -1), 0.5, border),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([kpi_grid, Spacer(1, 6)])

    story.append(Paragraph("1. Executive Administrative Summary", h2_st))
    story.append(Paragraph(escape(str(report.get("executive_summary", ""))), body_st))

    story.append(Paragraph("2. Department Performance Intelligence", h2_st))
    story.append(Paragraph(escape(str(report.get("department_performance_narrative", ""))), body_st))

    dept_rows = [
        [
            Paragraph("<b>Department</b>", hdr_st),
            Paragraph("<b>Received</b>", hdr_st),
            Paragraph("<b>Resolved</b>", hdr_st),
            Paragraph("<b>Pending</b>", hdr_st),
            Paragraph("<b>Overdue</b>", hdr_st),
            Paragraph("<b>Res %</b>", hdr_st),
            Paragraph("<b>Avg Days</b>", hdr_st),
            Paragraph("<b>Status</b>", hdr_st),
        ]
    ]
    for d in analytics.get("departments", []):
        dept_rows.append(
            [
                Paragraph(escape(str(d["department"])), cell_st),
                Paragraph(str(d["total_received"]), cell_st),
                Paragraph(str(d["resolved"]), cell_st),
                Paragraph(str(d["pending_backlog"]), cell_st),
                Paragraph(str(d["overdue"]), cell_st),
                Paragraph(f"{d['resolution_rate_pct']}%", cell_st),
                Paragraph(f"{d['avg_resolution_days']}d", cell_st),
                Paragraph(escape(str(d["attention_status"])), cell_st),
            ]
        )
    dept_tbl = Table(dept_rows, colWidths=[1.6 * inch, 0.65 * inch, 0.65 * inch, 0.65 * inch, 0.65 * inch, 0.65 * inch, 0.75 * inch, 1.8 * inch], repeatRows=1)
    dept_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("GRID", (0, 0), (-1, -1), 0.4, border),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([dept_tbl, Spacer(1, 6)])

    story.append(Paragraph("3. Delay Reason Analysis (Recorded vs. Inferred Patterns)", h2_st))
    for item in report.get("recorded_delay_findings", []):
        if isinstance(item, dict):
            story.append(
                Paragraph(
                    f"<b>[RECORDED] {escape(str(item.get('reason', '')))}:</b> {escape(str(item.get('evidence', '')))} "
                    f"<i>({escape(str(item.get('departments', '')))})</i>",
                    body_st,
                )
            )
    for pat in report.get("inferred_delay_patterns", []):
        if isinstance(pat, dict):
            tag = escape(str(pat.get("evidence_type", "INFERRED_PATTERN")))
            story.append(
                Paragraph(
                    f"<b>[{tag}] {escape(str(pat.get('department', '')))}:</b> {escape(str(pat.get('explanation', '')))}",
                    body_st,
                )
            )

    story.append(Paragraph("4. Top Overdue Complaints Requiring Immediate Action", h2_st))
    ovd_rows = [
        [
            Paragraph("<b>Complaint ID</b>", hdr_st),
            Paragraph("<b>Department</b>", hdr_st),
            Paragraph("<b>Category</b>", hdr_st),
            Paragraph("<b>Priority</b>", hdr_st),
            Paragraph("<b>Deadline</b>", hdr_st),
            Paragraph("<b>Overdue</b>", hdr_st),
            Paragraph("<b>Recorded Reason / Status</b>", hdr_st),
        ]
    ]
    for q in [x for x in analytics.get("pending_overdue_queue", []) if x["is_overdue"]][:15]:
        ovd_rows.append(
            [
                Paragraph(f"<b>{escape(str(q['complaint_id']))}</b>", cell_st),
                Paragraph(escape(str(q["department"])), cell_st),
                Paragraph(escape(str(q["category"])), cell_st),
                Paragraph(escape(str(q["priority"])), cell_st),
                Paragraph(escape(str(q["deadline"])), cell_st),
                Paragraph(f"{q['days_overdue']}d", cell_st),
                Paragraph(escape(str(q["delay_explanation"])), cell_st),
            ]
        )
    ovd_tbl = Table(ovd_rows, colWidths=[0.85 * inch, 1.15 * inch, 1.25 * inch, 0.65 * inch, 0.8 * inch, 0.6 * inch, 2.1 * inch], repeatRows=1)
    ovd_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
                ("GRID", (0, 0), (-1, -1), 0.4, border),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([ovd_tbl, Spacer(1, 6)])

    story.append(Paragraph("5. ML Anomaly Detection &amp; Administrative Recommendations", h2_st))
    story.append(Paragraph(escape(str(report.get("anomaly_summary", ""))), body_st))
    for rec in report.get("administrative_recommendations", []):
        if isinstance(rec, dict):
            story.append(
                Paragraph(
                    f"<b>[{escape(str(rec.get('priority', 'Action')))}]</b> {escape(str(rec.get('recommendation', '')))} "
                    f"<i>(Basis: {escape(str(rec.get('basis', '')))})</i>",
                    body_st,
                )
            )

    story.extend([Spacer(1, 8), HRFlowable(width="100%", thickness=0.6, color=border), Spacer(1, 4)])
    story.append(Paragraph(escape(str(report.get("privacy_and_grounding_note", ""))), ParagraphStyle("Ftr", parent=sub_st, fontSize=8)))

    doc.build(story)
    return buf.getvalue()

