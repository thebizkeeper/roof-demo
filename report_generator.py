import io
import os
import requests
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

BRAND_DARK  = colors.HexColor("#0f172a")
BRAND_GREEN = colors.HexColor("#10b981")
BRAND_BLUE  = colors.HexColor("#1a56db")
BRAND_GRAY  = colors.HexColor("#64748b")
BRAND_LIGHT = colors.HexColor("#f1f5f9")


def _fmt_money(n):
    return f"${n:,}"


def _section_header(text, styles):
    return Paragraph(
        f'<font color="#10b981"><b>{text}</b></font>',
        styles["section_header"]
    )


def generate_pdf_report(data, report_id):
    """
    data keys: name, email, phone, address, material, ownership,
               sq_ft, sq_ft_low, sq_ft_high, facets, pitch, complexity,
               cost_mat_low, cost_mat_high, cost_labor_low, cost_labor_high,
               cost_total_low, cost_total_high, timeline (dict),
               satellite_image_url, confidence, notes
    Returns: bytes (PDF)
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    base_styles = getSampleStyleSheet()
    styles = {
        "normal": ParagraphStyle("normal", fontName="Helvetica", fontSize=10, leading=14),
        "bold":   ParagraphStyle("bold",   fontName="Helvetica-Bold", fontSize=10, leading=14),
        "small":  ParagraphStyle("small",  fontName="Helvetica", fontSize=8, leading=11, textColor=BRAND_GRAY),
        "section_header": ParagraphStyle(
            "section_header", fontName="Helvetica-Bold", fontSize=11,
            leading=16, textColor=BRAND_GREEN, spaceAfter=4
        ),
        "title": ParagraphStyle(
            "title", fontName="Helvetica-Bold", fontSize=20,
            leading=24, textColor=colors.white
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName="Helvetica", fontSize=10,
            leading=14, textColor=colors.HexColor("#94a3b8")
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer", fontName="Helvetica-Oblique", fontSize=8,
            leading=11, textColor=BRAND_GRAY, alignment=TA_CENTER
        ),
    }

    story = []

    # ── Header banner ─────────────────────────────────────────────────────────
    header_data = [[
        Paragraph('<font color="white"><b>RoofGrid AI</b></font>', ParagraphStyle(
            "hdr", fontName="Helvetica-Bold", fontSize=22, textColor=colors.white
        )),
        Paragraph(
            f'<font color="#94a3b8">Roof Analysis Report<br/>'
            f'Report ID: {report_id}<br/>'
            f'Generated: {datetime.now().strftime("%B %d, %Y")}</font>',
            ParagraphStyle("hdr2", fontName="Helvetica", fontSize=9,
                           textColor=colors.HexColor("#94a3b8"), alignment=TA_RIGHT)
        ),
    ]]
    header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), BRAND_DARK),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING",   (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 18),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1), [8, 8, 0, 0]),
    ]))
    story.append(header_table)

    # ── Property bar ──────────────────────────────────────────────────────────
    prop_table = Table([[
        Paragraph(
            f'<b>Property:</b>  {data.get("address", "N/A")}',
            ParagraphStyle("prop", fontName="Helvetica", fontSize=10,
                           textColor=BRAND_DARK)
        )
    ]], colWidths=[7 * inch])
    prop_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), BRAND_LIGHT),
        ("LEFTPADDING",  (0, 0), (-1, -1), 16),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
    ]))
    story.append(prop_table)
    story.append(Spacer(1, 14))

    # ── Satellite image (optional — fetch from Mapbox) ────────────────────────
    sat_url = data.get("satellite_image_url", "")
    if sat_url:
        try:
            resp = requests.get(sat_url, timeout=8)
            if resp.status_code == 200:
                img_buf = io.BytesIO(resp.content)
                img = RLImage(img_buf, width=7 * inch, height=2.5 * inch)
                img.hAlign = "CENTER"
                story.append(img)
                story.append(Spacer(1, 12))
        except Exception:
            pass  # Skip image if fetch fails

    # ── Measurements ──────────────────────────────────────────────────────────
    story.append(_section_header("MEASUREMENTS", styles))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_GREEN, spaceAfter=8))

    meas_data = [
        ["Estimated Roof Area",     f'{data.get("sq_ft", 0):,} sq ft  '
                                    f'(range: {data.get("sq_ft_low",0):,} – {data.get("sq_ft_high",0):,} sq ft)'],
        ["Roof Sections (Facets)",  str(data.get("facets", "N/A"))],
        ["Pitch / Slope",           data.get("pitch", "N/A").capitalize()],
        ["Complexity",              data.get("complexity", "N/A")],
        ["AI Confidence",           data.get("confidence", "N/A").capitalize()],
    ]
    _add_data_table(story, meas_data)
    if data.get("notes"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(f'<i>{data["notes"]}</i>', styles["small"]))
    story.append(Spacer(1, 14))

    # ── Material ──────────────────────────────────────────────────────────────
    story.append(_section_header("MATERIAL SELECTED", styles))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_GREEN, spaceAfter=8))
    _add_data_table(story, [["Material", data.get("material", "N/A")]])
    story.append(Spacer(1, 14))

    # ── Cost Estimate ─────────────────────────────────────────────────────────
    story.append(_section_header("COST ESTIMATE", styles))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_GREEN, spaceAfter=8))

    cost_data = [
        ["Materials",
         f'{_fmt_money(data.get("cost_mat_low",0))} – {_fmt_money(data.get("cost_mat_high",0))}'],
        ["Labor",
         f'{_fmt_money(data.get("cost_labor_low",0))} – {_fmt_money(data.get("cost_labor_high",0))}'],
        ["Total Estimate",
         f'{_fmt_money(data.get("cost_total_low",0))} – {_fmt_money(data.get("cost_total_high",0))}'],
    ]
    cost_table = Table(cost_data, colWidths=[2.5 * inch, 4.5 * inch])
    cost_table.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME",     (1, 0), (1, -1), "Helvetica"),
        ("FONTNAME",     (0, 2), (1, 2),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",    (0, 0), (0, -1), BRAND_GRAY),
        ("TEXTCOLOR",    (1, 2), (1, 2),  BRAND_BLUE),
        ("FONTSIZE",     (0, 2), (1, 2),  11),
        ("BACKGROUND",   (0, 2), (-1, 2), BRAND_LIGHT),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LINEBELOW",    (0, 1), (-1, 1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(cost_table)
    story.append(Spacer(1, 14))

    # ── Timeline ──────────────────────────────────────────────────────────────
    timeline = data.get("timeline", {})
    story.append(_section_header("ESTIMATED COMPLETION TIMELINE", styles))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_GREEN, spaceAfter=8))

    tl_data = [["Typical Duration", timeline.get("range", "N/A")]]
    basis = f'{data.get("sq_ft",0):,} sq ft  ·  {data.get("complexity","N/A")} complexity'
    tl_data.append(["Based on", basis])
    _add_data_table(story, tl_data)

    if timeline.get("weather_note"):
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f'<i>{timeline["weather_note"]}</i>', styles["small"]
        ))
    story.append(Spacer(1, 20))

    # ── Disclaimer + Footer ───────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "* This is an AI-generated estimate based on satellite imagery analysis. "
        "Measurements and costs are approximations. For a certified measurement, "
        "contact a licensed roofing contractor.",
        styles["disclaimer"]
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'Powered by RoofGrid AI  ·  roofgridai.com  ·  reports@roofgridai.com  ·  {report_id}',
        styles["disclaimer"]
    ))

    doc.build(story)
    return buf.getvalue()


def _add_data_table(story, rows):
    table = Table(rows, colWidths=[2.5 * inch, 4.5 * inch])
    table.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME",     (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",    (0, 0), (0, -1), BRAND_GRAY),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LINEBELOW",    (0, 0), (-1, -2), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(table)
