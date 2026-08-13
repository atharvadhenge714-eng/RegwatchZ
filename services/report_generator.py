import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_pdf_report(company_profile: dict, discovery_results: dict, compliance_results: dict, risk_results: dict, action_results: dict, output_path: str):
    """Generate a highly professional, comprehensive compliance audit PDF report using ReportLab."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1e1b4b'),
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=30
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#312e81'),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'SubSectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#4338ca'),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=8
    )
    
    bold_body_style = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    bullet_style = ParagraphStyle(
        'BulletItem',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=5
    )

    story = []
    
    # ================= PAGE 1: TITLE & EXECUTIVE SUMMARY =================
    story.append(Paragraph("🛡️ REGWATCH COMPLIANCE REPORT", title_style))
    story.append(Paragraph(f"<b>Target Company:</b> {company_profile.get('company_name')} | <b>Date:</b> {os.getenv('CURRENT_DATE', 'August 13, 2026')}", subtitle_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Executive Summary", h1_style))
    sum_text = risk_results.get("exposure", {}).get("board_summary", "Audit summary details and corporate compliance mapping.")
    story.append(Paragraph(sum_text, body_style))
    story.append(Spacer(1, 15))
    
    # Profile Grid Table
    story.append(Paragraph("Company Profile Summary", h2_style))
    profile_data = [
        [Paragraph("<b>Company Name</b>", body_style), Paragraph(company_profile.get("company_name", "N/A"), body_style)],
        [Paragraph("<b>Jurisdiction Base</b>", body_style), Paragraph(company_profile.get("primary_country", "N/A"), body_style)],
        [Paragraph("<b>Company Type</b>", body_style), Paragraph(company_profile.get("company_type", "N/A"), body_style)],
        [Paragraph("<b>Industry Focus</b>", body_style), Paragraph(company_profile.get("industry", "N/A"), body_style)],
        [Paragraph("<b>Key Services</b>", body_style), Paragraph(", ".join(company_profile.get("services", [])), body_style)],
        [Paragraph("<b>Website</b>", body_style), Paragraph(company_profile.get("website_url", "N/A"), body_style)]
    ]
    t_profile = Table(profile_data, colWidths=[150, 380])
    t_profile.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f1f5f9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_profile)
    story.append(Spacer(1, 15))
    
    # Global Compliance Standing Table
    story.append(Paragraph("Jurisdictional Exposure Overview", h2_style))
    score_rows = [[Paragraph("<b>Jurisdiction</b>", bold_body_style), Paragraph("<b>Compliance Score</b>", bold_body_style)]]
    for country, score in risk_results.get("scores", {}).items():
        score_rows.append([Paragraph(country, body_style), Paragraph(f"<b>{score}%</b>", body_style)])
    
    t_scores = Table(score_rows, colWidths=[260, 270])
    t_scores.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_scores)
    
    story.append(PageBreak())
    
    # ================= PAGE 2: DISCOVERED REGULATIONS & MATRIX =================
    story.append(Paragraph("Discovered Regulatory Ecosystem", h1_style))
    story.append(Paragraph("Authoritative regulatory sources discovered for the target business activities across jurisdictions:", body_style))
    story.append(Spacer(1, 8))
    
    reg_index = 1
    for country, eco in discovery_results.get("ecosystem", {}).items():
        story.append(Paragraph(f"<b>{country} Regulatory Framework</b>", h2_style))
        for reg in eco.get("regulations", [])[:3]:
            text = f"<b>{reg_index}. {reg.get('title')}</b> ({reg.get('domain')})<br/>{reg.get('description')}<br/><i>Source: {reg.get('source_url', 'N/A')}</i>"
            story.append(Paragraph(text, body_style))
            story.append(Spacer(1, 5))
            reg_index += 1
            
    story.append(Spacer(1, 15))
    story.append(Paragraph("Compliance Matrix Statuses", h2_style))
    
    # We will build a small visual table mapping matrix cells
    matrix_cells = compliance_results.get("matrix_cells", {})
    domains = ["Data Protection", "Cybersecurity", "Financial Rules", "Reporting", "Third-Party Risk"]
    countries = company_profile.get("operating_countries", [company_profile.get("primary_country", "India")])
    
    matrix_headers = [Paragraph("<b>Domain</b>", bold_body_style)] + [Paragraph(f"<b>{c}</b>", bold_body_style) for c in countries]
    matrix_data = [matrix_headers]
    
    for d in domains:
        row = [Paragraph(d, body_style)]
        for c in countries:
            cell_key = f"{d}|||{c}"
            cell = matrix_cells.get(cell_key, {})
            status = cell.get("status", "🟢")
            row.append(Paragraph(status, body_style))
        matrix_data.append(row)
        
    t_matrix = Table(matrix_data, colWidths=[140] + [390/len(countries)]*len(countries))
    t_matrix.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_matrix)
    
    story.append(PageBreak())
    
    # ================= PAGE 3: COMPLIANCE GAPS & RISK ANALYSIS =================
    story.append(Paragraph("Identified Compliance Gaps", h1_style))
    story.append(Paragraph("The following gaps represent discrepancies between company policies and local regulations:", body_style))
    story.append(Spacer(1, 8))
    
    gaps = compliance_results.get("gaps", [])
    if not gaps:
        story.append(Paragraph("🟢 No compliance gaps identified. Company meets all regulatory thresholds.", body_style))
    else:
        for idx, gap in enumerate(gaps):
            gap_html = f"""<b>Gap {idx+1}: {gap.get('gap_description')}</b><br/>
            • <b>Regulation:</b> {gap.get('regulation')} ({gap.get('country')})<br/>
            • <b>Domain:</b> {gap.get('domain')} | <b>Risk Severity:</b> {gap.get('severity', 'MEDIUM')}<br/>
            • <b>Regulatory Obligation:</b> {gap.get('obligation')}<br/>
            • <b>Current Company Control:</b> {gap.get('current_state')}
            """
            story.append(Paragraph(gap_html, body_style))
            story.append(Spacer(1, 10))
            
    story.append(Spacer(1, 15))
    story.append(Paragraph("High Exposure Danger Risk Factors", h2_style))
    exp_factors = risk_results.get("exposure", {}).get("risk_factors", [])
    if not exp_factors:
        story.append(Paragraph("No critical high exposure threat risks detected.", body_style))
    else:
        for f in exp_factors:
            story.append(Paragraph(f"• {f}", bullet_style))
            
    story.append(PageBreak())
    
    # ================= PAGE 4: DETAILED ACTION ROADMAP =================
    story.append(Paragraph("Remediation Action Plan & Tasks", h1_style))
    story.append(Paragraph("Action items and JIRA-style tickets prioritized by severity to close regulatory gaps:", body_style))
    story.append(Spacer(1, 8))
    
    actions = action_results.get("actions", [])
    if not actions:
        story.append(Paragraph("No pending actions required.", body_style))
    else:
        # Action Table
        action_headers = [
            Paragraph("<b>Ticket</b>", bold_body_style),
            Paragraph("<b>Task / Action Required</b>", bold_body_style),
            Paragraph("<b>Owner</b>", bold_body_style),
            Paragraph("<b>Timeline</b>", bold_body_style),
            Paragraph("<b>Priority</b>", bold_body_style)
        ]
        action_table_rows = [action_headers]
        
        for act in actions:
            action_table_rows.append([
                Paragraph(act.get("ticket_id", "COMP"), body_style),
                Paragraph(f"<b>{act.get('title')}</b><br/>{act.get('action_required')}<br/><i>Evidence: {act.get('evidence_needed')}</i>", body_style),
                Paragraph(act.get("assignee", "Compliance"), body_style),
                Paragraph(act.get("timeline", "30 days"), body_style),
                Paragraph(act.get("priority", "HIGH"), body_style)
            ])
            
        t_actions = Table(action_table_rows, colWidths=[60, 240, 80, 80, 70])
        t_actions.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(t_actions)
        
    story.append(Spacer(1, 20))
    story.append(Paragraph("Compliance Timeline Goals", h2_style))
    story.append(Paragraph("• <b>Phase 1: Control Identification</b> - immediate assessment. Action: Verify gaps (1-7 days).", bullet_style))
    story.append(Paragraph("• <b>Phase 2: Policy Update</b> - draft changes in internal handbooks. Action: Write revisions (8-21 days).", bullet_style))
    story.append(Paragraph("• <b>Phase 3: Operational Enforcement</b> - deploy technical changes. Action: Engineers build tests (22-60 days).", bullet_style))
    story.append(Paragraph("• <b>Phase 4: Independent Attestation</b> - audit evidence logs. Action: Final Board signoff.", bullet_style))
    
    # Build Document
    doc.build(story)
