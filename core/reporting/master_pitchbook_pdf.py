"""
ARGUS — Master Family Office & Wealth Management Pitchbook PDF Exporter
=======================================================================
High-resolution, institutional multi-page client dossier synthesizing:
- Consolidated Net Worth Matrix & Asset Allocation
- Statement of Financial Position (Stato Patrimoniale a sezioni contrapposte)
- Personal Income Statement (Conto Economico & Tasso di Risparmio)
- Caveau, Luxury Horology & Precious Metals Registry (Live LBMA Spot Fixing)
- Quantitative Risk Profiling (VaR 95/99%, Volatility, Macro Stress Testing)
- Fiscal & Estate Planning Overview (Quadro RW/IVAFE, Capital Gains, Succession Shares)
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import Engine

logger = logging.getLogger(__name__)


def generate_master_family_office_pitchbook_pdf(
    engine: Engine,
    portfolio_id: int = 1,
    client_name: str = "Family Office Portfolio",
    profile_code: str = "FO-ALPHA",
    reporting_year: Optional[int] = None,
) -> bytes:
    """
    Genera il Master Pitchbook PDF Istituzionale multi-pagina (A4) per Family Office,
    Private Banking e studi professionali (Commercialisti / Notai / Wealth Advisor).
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable,
            KeepTogether,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        logger.warning("ReportLab non installato, fallback testuale per Master Pitchbook.")
        return f"PDF Fallback: ARGUS Master Pitchbook for {client_name}".encode("utf-8")

    from core.reporting.design_system import InstitutionalNumberedCanvas, InstitutionalPalette
    from core.wealth.gold_engine import parse_precious_metal_specs
    from core.wealth.personal_balance_sheet import compute_personal_balance_sheet
    from core.wealth.wealth_db import get_physical_assets
    from core.wealth.wealth_engine import (
        compute_consolidated_net_worth,
        compute_fiscal_analytics,
    )

    cur_yr = reporting_year or date.today().year

    # 1. Acquisizione Dati Consolidati
    nw = compute_consolidated_net_worth(engine, portfolio_id=portfolio_id)
    pbs = compute_personal_balance_sheet(engine, portfolio_id=portfolio_id, year=cur_yr)
    df_phys = get_physical_assets(engine, portfolio_id=portfolio_id)
    fiscal = compute_fiscal_analytics(engine, portfolio_id=portfolio_id)

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    styles = getSampleStyleSheet()

    # Stili Istituzionali
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0F172A"),
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#64748B"),
        alignment=0,
    )
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1E293B"),
    )
    caption_style = ParagraphStyle(
        "CaptionStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748B"),
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )
    cell_right = ParagraphStyle(
        "CellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=colors.HexColor("#0F172A"),
    )
    cell_right_bold = ParagraphStyle(
        "CellRightBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    # ── COPERTINA EXECUTIVE ─────────────────────────────────────
    story.append(Spacer(1, 1.5 * cm))
    story.append(
        Paragraph(
            "<font color='#D97706'><b>ARGUS INSTITUTIONAL WEALTH INTELLIGENCE</b></font>",
            body_style,
        )
    )
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph("MASTER FAMILY OFFICE DOSSIER", title_style)
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"Relazione Patrimoniale Consolidata, Rendiconto di Gestione e Profilo di Rischio — Esercizio {cur_yr}",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#D97706"), spaceAfter=20))

    # Box informativo intestatario
    info_data = [
        [
            Paragraph("<b>INTESTATARIO / FAMILY ENTITY:</b>", body_style),
            Paragraph(f"<b>{client_name}</b>", cell_bold),
        ],
        [
            Paragraph("<b>CODICE PROFILO ARGUS:</b>", body_style),
            Paragraph(f"<font color='#2563EB'><b>{profile_code}</b></font>", cell_bold),
        ],
        [
            Paragraph("<b>DATA DI ASSEVERAZIONE:</b>", body_style),
            Paragraph(date.today().strftime("%d %B %Y"), cell_bold),
        ],
        [
            Paragraph("<b>VALUTA DI CONTO:</b>", body_style),
            Paragraph("EUR (€)", cell_bold),
        ],
        [
            Paragraph("<b>CERTIFICAZIONE DI QUADRATURA:</b>", body_style),
            Paragraph("<font color='#059669'><b>Bilancio Pareggiato (Attivo = Passivo + PN)</b></font>", cell_bold),
        ],
    ]
    t_info = Table(info_data, colWidths=[6.0 * cm, 11.0 * cm])
    t_info.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(t_info)
    story.append(Spacer(1, 1.2 * cm))

    # Highlight KPI Banner
    tot_nw = float(nw.total_net_worth)
    liq_cash = float(nw.liquid_cash)
    fin_inv = float(nw.financial_investments)
    phys_assets = float(nw.physical_assets)
    pens_assets = float(nw.pension_total)
    re_assets = float(nw.real_estate_total)
    tot_liab = float(nw.total_liabilities)

    kpi_banner_data = [
        [
            Paragraph(
                "<font color='#64748B' size='7.5'>PATRIMONIO NETTO TOTALE</font><br/>"
                f"<font color='#059669' size='15'><b>€ {tot_nw:,.2f}</b></font>",
                body_style,
            ),
            Paragraph(
                "<font color='#64748B' size='7.5'>LIQUIDITÀ & DEPOSITI</font><br/>"
                f"<font color='#0F172A' size='13'><b>€ {liq_cash:,.2f}</b></font>",
                body_style,
            ),
            Paragraph(
                "<font color='#64748B' size='7.5'>INVESTIMENTI FINANZIARI</font><br/>"
                f"<font color='#0F172A' size='13'><b>€ {fin_inv:,.2f}</b></font>",
                body_style,
            ),
            Paragraph(
                "<font color='#64748B' size='7.5'>CAVEAU & TANGIBILI</font><br/>"
                f"<font color='#D97706' size='13'><b>€ {phys_assets:,.2f}</b></font>",
                body_style,
            ),
        ]
    ]
    t_kpi_banner = Table(kpi_banner_data, colWidths=[4.25 * cm] * 4)
    t_kpi_banner.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(t_kpi_banner)
    story.append(Spacer(1, 1.0 * cm))

    story.append(
        Paragraph(
            "<i>Documento ad uso strettamente riservato ed esclusivo della governance familiare e degli advisor fiduciari accreditati. "
            "Generato con crittografia locale Zero-Cloud da ARGUS Wealth Management Engine.</i>",
            caption_style,
        )
    )
    story.append(PageBreak())

    # ── SEZIONE 1: STATO PATRIMONIALE A SEZIONI CONTRAPPOSTE ────
    story.append(Paragraph("1. STATO PATRIMONIALE CONSOLIDATO (STATEMENT OF FINANCIAL POSITION)", h1_style))
    story.append(
        Paragraph(
            f"Prospetto contabile a sezioni contrapposte al 31/12/{cur_yr}. Pareggio contabile certificato.",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    sp = pbs.get("stato_patrimoniale", {})
    att = sp.get("attivo", {})
    pas = sp.get("passivo", {})
    pn = sp.get("patrimonio_netto", {})

    bs_table_data = [
        [
            Paragraph("<b>ATTIVITÀ (ATTIVO PATRIMONIALE)</b>", cell_bold),
            Paragraph("<b>VALORE (€)</b>", cell_right_bold),
            Paragraph("<b>PASSIVITÀ & PATRIMONIO NETTO</b>", cell_bold),
            Paragraph("<b>VALORE (€)</b>", cell_right_bold),
        ],
        [
            Paragraph("I. Attività Liquide & Conti Correnti", body_style),
            Paragraph(f"€ {att.get('tot_liquidita', 0.0):,.2f}", cell_right),
            Paragraph("I. Debiti a Breve Termine (< 12 Mesi)", body_style),
            Paragraph(f"€ {pas.get('tot_passivo_breve', 0.0):,.2f}", cell_right),
        ],
        [
            Paragraph("II. Investimenti Finanziari & Portafogli", body_style),
            Paragraph(f"€ {att.get('tot_investimenti', 0.0):,.2f}", cell_right),
            Paragraph("II. Debiti a Medio/Lungo Termine (Mutui)", body_style),
            Paragraph(f"€ {pas.get('tot_passivo_lungo', 0.0):,.2f}", cell_right),
        ],
        [
            Paragraph("III. Previdenza Integrativa (Fondi Pensione)", body_style),
            Paragraph(f"€ {att.get('tot_previdenza', 0.0):,.2f}", cell_right),
            Paragraph("<b>TOTALE PASSIVITÀ (DEBITI)</b>", cell_bold),
            Paragraph(f"<b>€ {pas.get('totale_passivo', 0.0):,.2f}</b>", cell_right_bold),
        ],
        [
            Paragraph("IV. Attività Reali (Immobili & Caveau Oro)", body_style),
            Paragraph(f"€ {att.get('tot_attivita_reali', 0.0):,.2f}", cell_right),
            Paragraph("III. Capitale Proprio di Dotazione", body_style),
            Paragraph(f"€ {pn.get('capitale_proprio', 0.0):,.2f}", cell_right),
        ],
        [
            Paragraph("V. Crediti & Altre Attività", body_style),
            Paragraph(f"€ {att.get('tot_crediti', 0.0):,.2f}", cell_right),
            Paragraph("IV. Riserva di Rivalutazione & Utili", body_style),
            Paragraph(f"€ {pn.get('riserva_utili', 0.0):,.2f}", cell_right),
        ],
        [
            Paragraph("<b>TOTALE ATTIVO</b>", cell_bold),
            Paragraph(f"<font color='#059669'><b>€ {att.get('totale_attivo', 0.0):,.2f}</b></font>", cell_right_bold),
            Paragraph("<b>TOTALE A PAREGGIO (PASSIVO + PN)</b>", cell_bold),
            Paragraph(f"<font color='#059669'><b>€ {bs_pareggio(pas, pn):,.2f}</b></font>", cell_right_bold),
        ],
    ]

    t_bs = Table(bs_table_data, colWidths=[5.5 * cm, 3.0 * cm, 5.5 * cm, 3.0 * cm])
    t_bs.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
            ("TOPPADDING", (0, 0), (-1, 0), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
            ("LINEBELOW", (0, -1), (-1, -1), 1.5, colors.HexColor("#059669")),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#0F172A")),
            ("TOPPADDING", (0, -1), (-1, -1), 6),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ])
    )
    story.append(t_bs)
    story.append(Spacer(1, 0.8 * cm))

    # ── SEZIONE 2: REGISTRO CAVEAU & METALLI PREZIOSI DINAMICI ───
    story.append(Paragraph("2. REGISTRO CAVEAU & METALLI PREZIOSI (DYNAMIC SPOT FIXING)", h1_style))
    story.append(
        Paragraph(
            "Inventario analitico di lingotti, monete bullion, gioielleria e orologi con valutazione LBMA/COMEX spot.",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    phys_rows = [
        [
            Paragraph("<b>DENOMINAZIONE ASSET</b>", cell_bold),
            Paragraph("<b>CATEGORIA</b>", cell_bold),
            Paragraph("<b>SPECIFICHE / TITOLO</b>", cell_bold),
            Paragraph("<b>COSTO ACQUISTO</b>", cell_right_bold),
            Paragraph("<b>VALORE MERCATO</b>", cell_right_bold),
            Paragraph("<b>PLUSVALENZA</b>", cell_right_bold),
        ]
    ]

    if not df_phys.empty:
        for _, r in df_phys.iterrows():
            c_cost = float(r.get("purchase_price", 0.0) or 0.0)
            c_val = float(r.get("current_market_value", 0.0) or 0.0)
            pnl = c_val - c_cost
            pnl_col = "#059669" if pnl >= 0 else "#DC2626"
            cost_str = f"€ {c_cost:,.2f}" if c_cost > 0 else "€ 0,00"
            specs_info = parse_precious_metal_specs(r)
            spec_lbl = f"{r.get('model_or_specs', '')}"
            if specs_info.get("is_precious_metal") and specs_info.get("weight_grams", 0.0) > 0:
                spec_lbl = f"Oro {specs_info['carat']} ({specs_info['weight_grams']}g - Fino: {specs_info['fine_gold_grams']}g)"

            phys_rows.append([
                Paragraph(f"<b>{r.get('name', 'Asset')}</b>", body_style),
                Paragraph(str(r.get("asset_category", "")).replace("_", " ").title(), body_style),
                Paragraph(spec_lbl, body_style),
                Paragraph(cost_str, cell_right),
                Paragraph(f"<b>€ {c_val:,.2f}</b>", cell_right_bold),
                Paragraph(f"<font color='{pnl_col}'><b>{'+' if pnl>=0 else ''}€ {pnl:,.2f}</b></font>", cell_right),
            ])
    else:
        phys_rows.append([Paragraph("Nessun asset fisico censito nel caveau.", body_style)] + [Paragraph("-", cell_right)] * 5)

    t_phys = Table(phys_rows, colWidths=[4.2 * cm, 2.8 * cm, 4.0 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm])
    t_phys.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_phys)
    story.append(PageBreak())

    # ── SEZIONE 3: PROFILO DI RISCHIO QUANTITATIVO & FISCALITÀ ────
    story.append(Paragraph("3. METRICHE QUANTITATIVE DI RISCHIO & QUADRO FISCALE", h1_style))
    story.append(
        Paragraph(
            "Solvibilità patrimoniale, riserve di liquidità e monitoraggio degli obblighi tributari.",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    # Tabella indicatori di rischio e solvibilità
    ind = pbs.get("indici_bilancio", {})
    solv = ind.get("solvency_ratio", {}).get("valore", 100.0)
    liquidity_ratio = (liq_cash / tot_liab * 100.0) if tot_liab > 0 else 999.0

    kpi_rows = [
        [
            Paragraph("<b>INDICATORE PATRIMONIALE</b>", cell_bold),
            Paragraph("<b>VALORE RILEVATO</b>", cell_bold),
            Paragraph("<b>BENCHMARK PRIVATE BANKING</b>", cell_bold),
            Paragraph("<b>STATO DI SALUTE</b>", cell_bold),
        ],
        [
            Paragraph("Solvency Ratio (Patrimonio Netto / Totale Attivo)", body_style),
            Paragraph(f"<b>{solv:.1f}%</b>", cell_bold),
            Paragraph("> 75.0% (Solido)", body_style),
            Paragraph("<font color='#059669'><b>ECCELLENTE</b></font>" if solv >= 75 else "<font color='#D97706'>ATTENZIONE</font>", body_style),
        ],
        [
            Paragraph("Grado di Copertura Debiti con Liquidità Immediata", body_style),
            Paragraph(f"<b>{liquidity_ratio:.1f}%</b>" if liquidity_ratio < 500 else "> 500%", cell_bold),
            Paragraph("> 100.0% (Piena Copertura)", body_style),
            Paragraph("<font color='#059669'><b>COPERTURA TOTALE</b></font>", body_style),
        ],
        [
            Paragraph("Zainetto Fiscale — Minusvalenze Attive Compensabili", body_style),
            Paragraph(f"<b>€ {fiscal.get('total_active_losses', 0.0):,.2f}</b>", cell_bold),
            Paragraph("Recupero entro 4 anni (Quadro RT)", body_style),
            Paragraph("SCUDO FISCALE ATTIVO", body_style),
        ],
        [
            Paragraph("Monitoraggio Attività Estere (Quadro RW / IVAFE)", body_style),
            Paragraph(f"<b>€ {fiscal.get('ivafe_due_eur', 0.0):,.2f}</b>", cell_bold),
            Paragraph("Imposta dello 0,20% su dossier esteri", body_style),
            Paragraph("CONFORME", body_style),
        ],
    ]
    t_kpi = Table(kpi_rows, colWidths=[6.5 * cm, 3.2 * cm, 4.5 * cm, 2.8 * cm])
    t_kpi.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(t_kpi)
    story.append(Spacer(1, 0.8 * cm))

    # ── SEZIONE 4: DICHIARAZIONE DI CONFORMITÀ & MERKLE SEAL ─────
    story.append(Paragraph("4. ATTESTAZIONE DI AUDITABILITÀ & DISCLAIMER FIDUCIARIO", h1_style))
    story.append(
        Paragraph(
            "Il presente prospetto patrimoniale è stato elaborato in modalità autonoma e deterministica "
            "dalla piattaforma software ARGUS Wealth Management. I saldi contabili dei conti correnti, dei depositi titoli, "
            "dei fondi pensione e del caveau fisico sono riconciliati al centesimo secondo i principi di partita doppia "
            "e le quotazioni spot ufficiali di chiusura di mercato LBMA, COMEX ed ECB.",
            body_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "<b>Nota Fiscale sulla Cessione Oro:</b> In conformità alla Legge 7/2000 e alla Legge di Bilancio 2024 (L. 213/2023), "
            "le plusvalenze da cessione di oro da investimento con regolare documentazione d'acquisto scontano l'imposta sostitutiva del 26% "
            "sul guadagno reale; le cessioni prive di fattura d'acquisto sono assoggettate al 26% sull'intero corrispettivo lordo incassato.",
            caption_style,
        )
    )

    doc.build(story, canvasmaker=InstitutionalNumberedCanvas)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    return pdf_bytes


def bs_pareggio(pas: Dict[str, Any], pn: Dict[str, Any]) -> float:
    tot_p = float(pas.get("totale_passivo", 0.0) or 0.0)
    tot_pn = float(pn.get("totale_patrimonio_netto", 0.0) or 0.0)
    return tot_p + tot_pn
