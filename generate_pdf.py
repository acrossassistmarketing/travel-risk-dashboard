"""
generate_pdf.py
Generates a colour-coded PDF travel risk report using reportlab.
"""

import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)

# Risk level colours
LEVEL_COLORS = {
    1: colors.HexColor("#2E7D32"),   # Green
    2: colors.HexColor("#F57F17"),   # Amber
    3: colors.HexColor("#E65100"),   # Deep Orange
    4: colors.HexColor("#B71C1C"),   # Dark Red
}

LEVEL_BG_COLORS = {
    1: colors.HexColor("#E8F5E9"),
    2: colors.HexColor("#FFF8E1"),
    3: colors.HexColor("#FBE9E7"),
    4: colors.HexColor("#FFEBEE"),
}

LEVEL_TEXT = {
    1: "LEVEL 1",
    2: "LEVEL 2",
    3: "LEVEL 3",
    4: "LEVEL 4",
}

RISK_TEXT = {
    1: "Low Risk",
    2: "Moderate Risk",
    3: "High Risk",
    4: "Extreme Risk",
}


def build_styles():
    styles = getSampleStyleSheet()
    custom = {
        "title": ParagraphStyle("title", parent=styles["Normal"],
            fontSize=22, fontName="Helvetica-Bold", textColor=colors.HexColor("#1a1a2e"),
            alignment=TA_CENTER, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=styles["Normal"],
            fontSize=11, fontName="Helvetica", textColor=colors.HexColor("#555555"),
            alignment=TA_CENTER, spaceAfter=2),
        "updated": ParagraphStyle("updated", parent=styles["Normal"],
            fontSize=9, fontName="Helvetica", textColor=colors.HexColor("#888888"),
            alignment=TA_CENTER, spaceAfter=16),
        "region_header": ParagraphStyle("region_header", parent=styles["Normal"],
            fontSize=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#1a1a2e"),
            spaceBefore=14, spaceAfter=6),
        "country_name": ParagraphStyle("country_name", parent=styles["Normal"],
            fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#1a1a2e")),
        "body_small": ParagraphStyle("body_small", parent=styles["Normal"],
            fontSize=9, fontName="Helvetica", textColor=colors.HexColor("#333333"),
            leading=13),
        "label": ParagraphStyle("label", parent=styles["Normal"],
            fontSize=8, fontName="Helvetica-Bold", textColor=colors.HexColor("#666666")),
        "legend_item": ParagraphStyle("legend_item", parent=styles["Normal"],
            fontSize=9, fontName="Helvetica", textColor=colors.HexColor("#333333")),
        "footer": ParagraphStyle("footer", parent=styles["Normal"],
            fontSize=8, fontName="Helvetica", textColor=colors.HexColor("#999999"),
            alignment=TA_CENTER),
    }
    return custom


def level_badge_table(level):
    """Returns a small table acting as a coloured badge."""
    lvl_color = LEVEL_COLORS.get(level, colors.grey)
    lvl_bg = LEVEL_BG_COLORS.get(level, colors.white)
    lvl_text = LEVEL_TEXT.get(level, "N/A")
    risk_text = RISK_TEXT.get(level, "Unknown")

    badge = Table(
        [[Paragraph(f'<font size="9" color="{lvl_color.hexval()}"><b>{lvl_text}</b></font>',
                    ParagraphStyle("b", fontName="Helvetica-Bold", fontSize=9, alignment=TA_CENTER)),
          Paragraph(f'<font size="9" color="{lvl_color.hexval()}">{risk_text}</font>',
                    ParagraphStyle("b", fontName="Helvetica", fontSize=9, alignment=TA_CENTER))]],
        colWidths=[22*mm, 28*mm]
    )
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), lvl_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, lvl_color),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return badge


def build_country_row(country_data, styles):
    """Build a single country block as a table row."""
    level = country_data.get("level", 2)
    name = country_data.get("country", "")
    summary = country_data.get("summary", "")
    security = country_data.get("security", "")
    health = country_data.get("health", "")
    crime = country_data.get("crime", "")

    lvl_color = LEVEL_COLORS.get(level, colors.grey)
    lvl_bg = LEVEL_BG_COLORS.get(level, colors.HexColor("#f9f9f9"))

    # Left: badge
    badge = level_badge_table(level)

    # Right: content
    content = []
    content.append(Paragraph(name, styles["country_name"]))
    content.append(Spacer(1, 3))
    if summary:
        content.append(Paragraph(summary, styles["body_small"]))
        content.append(Spacer(1, 4))

    details = []
    if security:
        details.append(Paragraph(f'<b>Security:</b> {security}', styles["body_small"]))
    if health:
        details.append(Paragraph(f'<b>Health:</b> {health}', styles["body_small"]))
    if crime:
        details.append(Paragraph(f'<b>Crime:</b> {crime}', styles["body_small"]))
    content.extend(details)

    row_table = Table(
        [[badge, content]],
        colWidths=[54*mm, 126*mm]
    )
    row_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), lvl_bg),
        ("BOX", (0, 0), (-1, -1), 0.3, lvl_color),
        ("LEFTPADDING", (0, 0), (0, 0), 4),
        ("RIGHTPADDING", (0, 0), (0, 0), 4),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
        ("RIGHTPADDING", (1, 0), (1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
    ]))
    return row_table


def build_legend(styles):
    items = []
    for level in [1, 2, 3, 4]:
        col = LEVEL_COLORS[level]
        bg = LEVEL_BG_COLORS[level]
        items.append(
            Paragraph(
                f'<font color="{col.hexval()}"><b>{LEVEL_TEXT[level]}</b></font>'
                f' — {RISK_TEXT[level]}',
                styles["legend_item"]
            )
        )

    legend_table = Table([items], colWidths=[45*mm]*4)
    legend_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
        ("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return legend_table


def generate_pdf(classified_data, output_path="travel_risk_report.pdf"):
    """Main function to generate the PDF report."""
    now = datetime.now()
    date_str = now.strftime("%d %B %Y, %I:%M %p IST")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
    )

    styles = build_styles()
    story = []

    # Header
    story.append(Paragraph("Across Assist — Travel Risk Advisory", styles["title"]))
    story.append(Paragraph("Country Risk Classification Report", styles["subtitle"]))
    story.append(Paragraph(f"Last updated: {date_str}", styles["updated"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
    story.append(Spacer(1, 8))

    # Legend
    story.append(build_legend(styles))
    story.append(Spacer(1, 12))

    # Summary stats
    total = len(classified_data)
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for c in classified_data:
        lvl = c.get("level", 2)
        counts[lvl] = counts.get(lvl, 0) + 1

    stats_data = [[
        Paragraph(f'<font size="16" color="{LEVEL_COLORS[l].hexval()}"><b>{counts[l]}</b></font><br/>'
                  f'<font size="8" color="#666666">{RISK_TEXT[l]}</font>',
                  ParagraphStyle("s", fontName="Helvetica", fontSize=9, alignment=TA_CENTER))
        for l in [1, 2, 3, 4]
    ]]
    stats_table = Table(stats_data, colWidths=[45*mm]*4)
    stats_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
        ("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e0e0e0")),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 16))

    # Group by region
    regions = {}
    for c in classified_data:
        r = c.get("region", "Other")
        regions.setdefault(r, []).append(c)

    for region, countries in regions.items():
        story.append(Paragraph(f"▸  {region}", styles["region_header"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0")))
        story.append(Spacer(1, 4))

        for country in countries:
            row = build_country_row(country, styles)
            story.append(KeepTogether([row, Spacer(1, 5)]))

        story.append(Spacer(1, 8))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Source: US State Department travel.state.gov · Generated: {date_str} · "
        "For internal use only — Across Assist Private Limited",
        styles["footer"]
    ))

    doc.build(story)
    print(f"PDF report saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    with open("classified_data.json") as f:
        data = json.load(f)
    generate_pdf(data, "travel_risk_report.pdf")
