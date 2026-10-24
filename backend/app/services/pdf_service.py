import io
from typing import Dict, Any, List
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)


def generate_agreement_pdf(
    deal_title: str,
    deal_id: str,
    version_number: int,
    agreement_json: Dict[str, Any],
    agreement_text: str,
    parties: List[Dict[str, Any]],
    approvals: List[Dict[str, Any]],
    is_confirmed: bool,
    created_at: datetime,
) -> bytes:
    """
    Generates a professional, plain-language legal agreement PDF using ReportLab.
    Includes document metadata, parties table, structured clauses, participant confirmations,
    tamper-evident verification note, and statutory legal disclaimer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    navy_color = colors.HexColor("#0F233E")
    charcoal_color = colors.HexColor("#1E293B")
    border_color = colors.HexColor("#CBD5E1")
    light_bg = colors.HexColor("#F8FAFC")
    success_color = colors.HexColor("#0D9488")
    warning_color = colors.HexColor("#B45309")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=navy_color,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=12,
    )

    section_heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=navy_color,
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=charcoal_color,
        spaceAfter=6,
    )

    bold_label_style = ParagraphStyle(
        "BoldLabel",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=navy_color,
    )

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        alignment=1,  # Center
        textColor=colors.white,
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748B"),
        alignment=1,
    )

    story = []

    # 1. Header Banner & Status
    status_label = "MUTUALLY CONFIRMED AGREEMENT" if is_confirmed else "DRAFT AGREEMENT — PENDING CONFIRMATION"
    badge_bg = success_color if is_confirmed else warning_color

    status_table = Table(
        [[Paragraph(status_label, badge_style)]],
        colWidths=[532],
    )
    status_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), badge_bg),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
    )
    story.append(status_table)
    story.append(Spacer(1, 12))

    # 2. Document Title & Reference
    story.append(Paragraph(deal_title, title_style))
    ref_text = (
        f"<b>Reference ID:</b> LB-{deal_id[:8].upper()} | "
        f"<b>Version:</b> {version_number}.0 | "
        f"<b>Date:</b> {created_at.strftime('%d %B %Y')}"
    )
    story.append(Paragraph(ref_text, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceAfter=12))

    # 3. Parties Table
    story.append(Paragraph("1. PARTIES INVOLVED", section_heading_style))
    parties_data = [
        [
            Paragraph("<b>Participant Role</b>", bold_label_style),
            Paragraph("<b>Name & Details</b>", bold_label_style),
            Paragraph("<b>Confirmation Status</b>", bold_label_style),
        ]
    ]

    for p in parties:
        role_label = p.get("role", "Participant").capitalize()
        name_label = p.get("full_name") or p.get("email") or "Authorized Representative"
        status_text = "Approved" if p.get("has_approved") else "Pending Review"
        status_color = "#0D9488" if p.get("has_approved") else "#B45309"
        parties_data.append([
            Paragraph(role_label, body_style),
            Paragraph(f"{name_label} ({p.get('email', 'No email registered')})", body_style),
            Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", body_style),
        ])

    parties_table = Table(parties_data, colWidths=[120, 260, 152])
    parties_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), light_bg),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(parties_table)
    story.append(Spacer(1, 14))

    # 4. Clauses / Sections
    sections = [
        ("2. WORK SCOPE & DELIVERABLES", agreement_json.get("work_scope")),
        ("3. FINANCIAL TERMS & PAYMENT SCHEDULE", agreement_json.get("financial_terms")),
        ("4. TIMELINE & DEADLINES", agreement_json.get("timeline")),
        ("5. RESPONSIBILITIES & OBLIGATIONS", agreement_json.get("responsibilities")),
        ("6. DELIVERY & ACCEPTANCE CRITERIA", agreement_json.get("delivery_acceptance")),
        ("7. CANCELLATION, REFUNDS & DISPUTES", agreement_json.get("cancellation_refunds")),
        ("8. ADDITIONAL AGREED CONDITIONS", agreement_json.get("additional_conditions")),
    ]

    for title, content in sections:
        if content:
            story.append(Paragraph(title, section_heading_style))
            # Format lines
            if isinstance(content, str):
                story.append(Paragraph(content.replace("\n", "<br/>"), body_style))
            elif isinstance(content, dict):
                content_text = content.get("value") or content.get("content") or "None specified"
                story.append(Paragraph(str(content_text).replace("\n", "<br/>"), body_style))
            story.append(Spacer(1, 6))

    # Full custom agreement text if sections are minimal
    if agreement_text and not agreement_json.get("work_scope"):
        story.append(Paragraph("2. MUTUAL AGREEMENT TERMS", section_heading_style))
        story.append(Paragraph(agreement_text.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 10))

    # 5. Clarified or Unresolved Terms
    unresolved = agreement_json.get("unresolved_terms", [])
    if unresolved:
        story.append(Spacer(1, 8))
        story.append(Paragraph("9. UNRESOLVED / CLARIFIED MATTERS", section_heading_style))
        for item in unresolved:
            story.append(Paragraph(f"• {item}", body_style))
        story.append(Spacer(1, 6))

    # 6. Approvals & Signatures Block
    story.append(Spacer(1, 14))
    story.append(KeepTogether([
        Paragraph("10. PARTICIPANT CONFIRMATION RECORD", section_heading_style),
        HRFlowable(width="100%", thickness=0.5, color=border_color, spaceAfter=8),
    ]))

    approval_rows = [
        [
            Paragraph("<b>Participant</b>", bold_label_style),
            Paragraph("<b>Decision</b>", bold_label_style),
            Paragraph("<b>Timestamp (UTC)</b>", bold_label_style),
            Paragraph("<b>Verification Stamp</b>", bold_label_style),
        ]
    ]

    for app in approvals:
        p_name = app.get("participant_name", "Participant")
        p_role = app.get("role", "")
        status_disp = app.get("status", "pending").replace("_", " ").upper()
        conf_time = app.get("confirmed_at")
        time_str = conf_time.strftime("%Y-%m-%d %H:%M:%S UTC") if isinstance(conf_time, datetime) else str(conf_time or "—")
        color_code = "#0D9488" if app.get("status") == "approved" else "#B45309"

        stamp = f"LB-VERIFIED-{app.get('id', '')[:8].upper()}" if app.get("status") == "approved" else "PENDING"
        approval_rows.append([
            Paragraph(f"{p_name}<br/><font size=8 color='#64748B'>{p_role}</font>", body_style),
            Paragraph(f"<font color='{color_code}'><b>{status_disp}</b></font>", body_style),
            Paragraph(time_str, body_style),
            Paragraph(f"<code>{stamp}</code>", body_style),
        ])

    if len(approval_rows) > 1:
        app_table = Table(approval_rows, colWidths=[150, 100, 150, 132])
        app_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), light_bg),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(app_table)
    else:
        story.append(Paragraph("<i>No formal approval records submitted for this version yet.</i>", body_style))

    # 7. Tamper-evident Audit Seal & Legal Disclaimer
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceAfter=8))
    seal_text = (
        "<b>Legalbandu Tamper-Evident Assurance:</b> This document was generated and version-controlled "
        "via SHA-256 cryptographic hash-chaining. Any amendment to terms requires bilateral re-confirmation."
    )
    story.append(Paragraph(seal_text, disclaimer_style))
    story.append(Spacer(1, 4))
    disclaimer = (
        "<b>LEGAL DISCLAIMER:</b> Legalbandu is an AI-assisted record-keeping and agreement documentation tool. "
        "This document is drafted based on participant communications and mutual confirmations. "
        "Legalbandu does not provide formal legal advice, representation, or guarantee statutory enforceability."
    )
    story.append(Paragraph(disclaimer, disclaimer_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
