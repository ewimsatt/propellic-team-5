"""PDF report generation using reportlab. Charts are embedded as PNG via kaleido."""

from __future__ import annotations

import io
import os
import tempfile
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph,
    Spacer, Table, TableStyle, Image, HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import plotly.io as pio

from analysis.detection import CoiledSpring
from config import CONFIDENCE_COLORS


# ── Colour palette (light / print-friendly) ──────────────────────────────────

WHITE      = colors.HexColor("#FFFFFF")
NEAR_BLACK = colors.HexColor("#111827")
SLATE      = colors.HexColor("#374151")
MUTED      = colors.HexColor("#6B7280")
ACCENT     = colors.HexColor("#2563EB")
AMBER      = colors.HexColor("#D97706")
GREEN      = colors.HexColor("#059669")
BORDER     = colors.HexColor("#E5E7EB")
LIGHT_BG   = colors.HexColor("#F9FAFB")


def _conf_color(level: str) -> colors.HexColor:
    hex_str = CONFIDENCE_COLORS.get(level, "#94a3b8")
    return colors.HexColor(hex_str)


# ── Styles ───────────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "cs_title", parent=base["Title"],
        fontSize=22, textColor=NEAR_BLACK, spaceAfter=4,
        fontName="Helvetica-Bold", alignment=TA_LEFT,
    )
    styles["subtitle"] = ParagraphStyle(
        "cs_subtitle", parent=base["Normal"],
        fontSize=11, textColor=MUTED, spaceAfter=12,
        fontName="Helvetica",
    )
    styles["h2"] = ParagraphStyle(
        "cs_h2", parent=base["Heading2"],
        fontSize=14, textColor=ACCENT, spaceBefore=18, spaceAfter=6,
        fontName="Helvetica-Bold",
    )
    styles["h3"] = ParagraphStyle(
        "cs_h3", parent=base["Heading3"],
        fontSize=11, textColor=NEAR_BLACK, spaceBefore=10, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    styles["body"] = ParagraphStyle(
        "cs_body", parent=base["Normal"],
        fontSize=10, textColor=SLATE, leading=16, spaceAfter=8,
        fontName="Helvetica",
    )
    styles["small"] = ParagraphStyle(
        "cs_small", parent=base["Normal"],
        fontSize=8.5, textColor=MUTED, leading=13,
        fontName="Helvetica",
    )
    styles["exec"] = ParagraphStyle(
        "cs_exec", parent=base["Normal"],
        fontSize=11, textColor=NEAR_BLACK, leading=18, spaceAfter=10,
        fontName="Helvetica", leftIndent=12, rightIndent=12,
    )
    return styles


# ── Header / Footer ──────────────────────────────────────────────────────────

def _header_footer(canvas, doc, title: str, report_date: str):
    canvas.saveState()
    w, h = letter

    # Header bar
    canvas.setFillColor(NEAR_BLACK)
    canvas.rect(0, h - 36, w, 36, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(40, h - 22, "🌀 Coiled Spring Opportunity Report")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(w - 40, h - 22, title)

    # Footer
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(40, 18, f"Generated {report_date} · Confidential")
    canvas.drawRightString(w - 40, 18, f"Page {doc.page}")
    canvas.setStrokeColor(BORDER)
    canvas.line(40, 28, w - 40, 28)

    canvas.restoreState()


# ── Chart → PNG bytes ─────────────────────────────────────────────────────────

def _fig_to_png(fig, width_px: int = 900, height_px: int = 320) -> bytes | None:
    try:
        fig_light = fig
        # Override to white background for print
        fig_light = fig.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="#f8fafc",
            font_color="#1e293b",
        )
        png = pio.to_image(fig_light, format="png", width=width_px, height=height_px, scale=1.5)
        return png
    except Exception:
        return None


# ── KPI table ────────────────────────────────────────────────────────────────

def _kpi_table(kpis: dict, styles: dict):
    rows = [
        ["Metric", "Value"],
        ["Active Coiled Springs",     str(kpis.get("spring_count", 0))],
        ["Avg CVR vs Baseline",        f"{kpis.get('avg_cvr_delta_pct', 0):+.1f}%"],
        ["Estimated Spend at Risk",    f"${kpis.get('total_spend_at_risk', 0):,.0f}"],
        ["Projected Recovery Uplift",  f"{kpis.get('total_projected_uplift', 0):,.0f} conv."],
    ]
    t = Table(rows, colWidths=[3.2 * inch, 3.2 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TEXTCOLOR",    (0, 1), (-1, -1), SLATE),
        ("GRID",         (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    return t


# ── Public entry point ────────────────────────────────────────────────────────

def generate_pdf(
    springs: list[CoiledSpring],
    kpis: dict,
    executive_summary: str,
    divergence_charts: dict,      # campaign_id → go.Figure
    report_title: str = "Propellic",
) -> bytes:
    buf = io.BytesIO()
    styles = _build_styles()
    report_date = date.today().strftime("%B %d, %Y")

    doc = BaseDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=52, bottomMargin=40,
    )

    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id="normal",
    )
    template = PageTemplate(
        id="main",
        frames=[frame],
        onPage=lambda c, d: _header_footer(c, d, report_title, report_date),
    )
    doc.addPageTemplates([template])

    story = []

    # ── Page 1: Cover / Executive Summary ────────────────────────────────────
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Coiled Spring Opportunity Report", styles["title"]))
    story.append(Paragraph(f"Prepared for {report_title} · {report_date}", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=12))

    story.append(Paragraph("Executive Summary", styles["h2"]))

    # Tinted box around the summary
    exec_bg = Table(
        [[Paragraph(p, styles["exec"])] for p in executive_summary.split("\n\n") if p.strip()],
        colWidths=[doc.width],
    )
    exec_bg.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(exec_bg)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("KPI Summary", styles["h2"]))
    story.append(_kpi_table(kpis, styles))
    story.append(Spacer(1, 0.3 * inch))

    # ── One page per opportunity ──────────────────────────────────────────────
    for spring in springs:
        story.append(Paragraph(
            f"Opportunity: {spring.campaign_name}", styles["h2"]
        ))

        conf_hex = CONFIDENCE_COLORS.get(spring.confidence, "#94a3b8")
        story.append(Paragraph(
            f"<font color='{conf_hex}'><b>Confidence: {spring.confidence.upper()}</b></font> "
            f"&nbsp;|&nbsp; Signals: {', '.join(spring.active_signals)} "
            f"&nbsp;|&nbsp; Active since: {spring.start_date} ({spring.duration_days} days)",
            styles["body"],
        ))

        # Metrics table
        metrics_rows = [
            ["", ""],
            ["Current CVR",   f"{spring.cvr_current*100:.2f}%"],
            ["Baseline CVR",  f"{spring.cvr_baseline*100:.2f}%"],
            ["CVR Deviation", f"{spring.cvr_z_score:.1f} SD below baseline"],
            ["Intent Trend",  spring.impression_trend.replace("_", " ").title()],
            ["Rebound Est.",  f"{spring.rebound_min_days}–{spring.rebound_max_days} days"],
            ["Spend at Risk", f"${spring.estimated_spend_at_risk:,.0f}"],
            ["Recovery Uplift", f"+{spring.projected_recovery_uplift:,.0f} conversions"],
        ]
        metrics_rows[0] = ["Metric", "Value"]
        mt = Table(metrics_rows, colWidths=[2.4 * inch, 4.0 * inch])
        mt.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR",     (0, 0), (-1, -1), SLATE),
            ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        story.append(mt)
        story.append(Spacer(1, 0.12 * inch))

        # Divergence chart
        fig = divergence_charts.get(spring.campaign_id)
        if fig is not None:
            png = _fig_to_png(fig, width_px=860, height_px=300)
            if png:
                img_buf = io.BytesIO(png)
                img = Image(img_buf, width=6.5 * inch, height=2.3 * inch)
                story.append(img)
                story.append(Spacer(1, 0.08 * inch))

        # Signal details
        if spring.signal_details:
            story.append(Paragraph("Signal Details", styles["h3"]))
            for sig, detail in spring.signal_details.items():
                story.append(Paragraph(f"<b>{sig.capitalize()}:</b> {detail}", styles["body"]))

        # Recommendation
        story.append(Paragraph("Recommended Action", styles["h3"]))
        rec_table = Table(
            [[Paragraph(spring.recommendation, styles["body"])]],
            colWidths=[doc.width],
        )
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
            ("BOX",        (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
            ("LEFTPADDING",(0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 0.4 * inch))

    doc.build(story)
    buf.seek(0)
    return buf.read()
