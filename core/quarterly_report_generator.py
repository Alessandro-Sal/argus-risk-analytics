# ============================================================
# core/quarterly_report_generator.py
# ARGUS — Universal White-Label Quarterly PDF Exporter
# Multi-page executive client reporting for Family Offices & HNWI
# ============================================================

from typing import Dict, Any, Optional
import io
from datetime import date
import pandas as pd


def generate_white_label_quarterly_pdf_report(
    engine: Any,
    portfolio_id: int = 1,
    client_name: str = "Family Office Portfolio",
    quarter: str = "Q1 2026",
    advisor_firm: str = "ARGUS Wealth & Family Office Advisory"
) -> bytes:
    """
    Genera un dossier trimestrale multipagina ad alta risoluzione (PDF)
    con bilancio consolidato, attribuzione di performance, risk test ed ESG.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
    except ImportError:
        # Fallback se reportlab non fosse installato
        return f"PDF Fallback: Report {quarter} for {client_name}".encode("utf-8")

    from core.wealth.wealth_engine import (
        compute_consolidated_net_worth,
        compute_total_wealth_brinson_attribution
    )
    from core.macro_stress_engine import compute_macro_scenario_stress_test
    from core.esg_engine import compute_portfolio_esg_and_sfdr_metrics

    # Calcolo dati live
    nw = compute_consolidated_net_worth(engine, portfolio_id=portfolio_id)
    br = compute_total_wealth_brinson_attribution(engine, portfolio_id=portfolio_id)
    stress = compute_macro_scenario_stress_test()
    esg = compute_portfolio_esg_and_sfdr_metrics()

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm
    )

    styles = getSampleStyleSheet()

    # Custom typography
    c_primary = colors.HexColor("#0f172a")
    c_accent = colors.HexColor("#6366f1")
    c_text = colors.HexColor("#334155")
    c_bg = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=c_primary,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=c_accent,
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=c_text
    )

    meta_style = ParagraphStyle(
        'Meta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#64748b")
    )

    story = []

    # ── HEADER & COPIRTINA ──────────────────────────────────────
    story.append(Paragraph(f"<b>{advisor_firm.upper()}</b>", meta_style))
    story.append(Paragraph(f"Relazione Patrimoniale Trimestrale — {quarter}", title_style))
    story.append(Paragraph(f"Cliente: <b>{client_name}</b> | Data di Riferimento: <b>{date.today().strftime('%d/%m/%Y')}</b>", meta_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=8, spaceAfter=14))

    # ── EXECUTIVE SUMMARY & TOP METRICS ─────────────────────────
    story.append(Paragraph("1. Quadro di Sintesi Patrimoniale & Liquidità", h2_style))

    kpi_data = [
        [
            Paragraph("<b>Patrimonio Netto Consolidato</b>", meta_style),
            Paragraph("<b>Disponibilità Liquide</b>", meta_style),
            Paragraph("<b>Investimenti Finanziari</b>", meta_style),
            Paragraph("<b>Wealth Health Score</b>", meta_style)
        ],
        [
            Paragraph(f"<font size=13 color='#0f172a'><b>€ {nw.total_net_worth:,.2f}</b></font>", body_style),
            Paragraph(f"<font size=13 color='#10b981'><b>€ {nw.liquid_cash:,.2f}</b></font>", body_style),
            Paragraph(f"<font size=13 color='#6366f1'><b>€ {nw.financial_investments:,.2f}</b></font>", body_style),
            Paragraph(f"<font size=13 color='#38bdf8'><b>{nw.wealth_health_score:.0f}/100</b></font>", body_style)
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[4.2*cm, 4.2*cm, 4.2*cm, 4.2*cm])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_bg),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 14))

    # ── ATTRIBUZIONE DI RENDIMENTO BRINSON ──────────────────────
    story.append(Paragraph("2. Attribuzione di Performance Multi-Asset (Brinson-Fachler)", h2_style))
    story.append(Paragraph(
        f"Nel trimestre di riferimento, il portafoglio ha generato un rendimento totale del <b>{br['portfolio_total_return_pct']:+.2f}%</b> "
        f"rispetto al benchmark strategico ({br['benchmark_total_return_pct']:+.2f}%), registrando un Extra-Rendimento netto (Alpha) "
        f"pari a <b>{br['excess_return_pct']:+.2f}%</b>.",
        body_style
    ))
    story.append(Spacer(1, 6))

    br_table_data = [
        [Paragraph("<b>Classe di Attivo</b>", meta_style), Paragraph("<b>Peso (%)</b>", meta_style), Paragraph("<b>Rendimento (%)</b>", meta_style), Paragraph("<b>Allocazione (%)</b>", meta_style), Paragraph("<b>Selezione (%)</b>", meta_style)]
    ]
    for row in br.get("breakdown_list", []):
        br_table_data.append([
            Paragraph(row["asset_class"], body_style),
            Paragraph(f"{row['portfolio_weight_pct']:.1f}%", body_style),
            Paragraph(f"{row['portfolio_return_pct']:+.1f}%", body_style),
            Paragraph(f"{row['allocation_effect_pct']:+.2f}%", body_style),
            Paragraph(f"{row['selection_effect_pct']:+.2f}%", body_style)
        ])
    t_br = Table(br_table_data, colWidths=[5.5*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm])
    t_br.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_br)
    story.append(Spacer(1, 14))

    # ── STRESS TESTING & ESG ────────────────────────────────────
    story.append(Paragraph("3. Resilienza a Shock Macroeconomici & Allineamento ESG (SFDR)", h2_style))
    story.append(Paragraph(
        f"Lo stress test normativo EBA Adverse indica una perdita potenziale massima del <b>{stress['worst_case_drawdown_pct']:.1f}%</b>. "
        f"Sul fronte di sostenibilità, il portafoglio vanta un punteggio ESG globale di <b>{esg['portfolio_esg_score']}/100 (Rating {esg['esg_rating_band']})</b> "
        f"con il <b>{esg['sfdr_breakdown']['art_8_esg_promoting_pct'] + esg['sfdr_breakdown']['art_9_dark_green_impact_pct']:.1f}%</b> di asset conformi agli Articoli 8 e 9 SFDR.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ── DISCLAIMER ──────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceBefore=10, spaceAfter=8))
    story.append(Paragraph(
        "<i>Documento ad uso interno e riservato. I rendimenti passati non sono indicativi di quelli futuri. "
        "Generato automaticamente dalla piattaforma ARGUS Wealth Intelligence.</i>",
        meta_style
    ))

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()
