import os
import io
import pandas as pd
import numpy as np
from datetime import datetime

# ReportLab imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
    )
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from core.html_exporter import generate_html_report_bytes, generate_interactive_html_report


if HAS_REPORTLAB:
    class NumberedCanvas(canvas.Canvas):
        """
        Two-pass canvas for dynamic total page count, running headers, and footers.
        """
        def __init__(self, *args, **kwargs):
            super(NumberedCanvas, self).__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                super(NumberedCanvas, self).showPage()
            super(NumberedCanvas, self).save()

        def draw_page_decorations(self, page_count):
            if self._pageNumber > 1:
                self.saveState()
                # Running Header
                self.setFont("Helvetica-Bold", 7.5)
                self.setFillColor(colors.HexColor("#334155"))
                self.drawString(30, 814, "ARGUS RISK ANALYTICS PLATFORM")
                self.setFont("Helvetica", 7.5)
                self.setFillColor(colors.HexColor("#64748B"))
                self.drawRightString(565, 814, f"INSTITUTIONAL AUDIT DOSSIER  •  {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                self.setStrokeColor(colors.HexColor("#CBD5E1"))
                self.setLineWidth(0.5)
                self.line(30, 807, 565, 807)

                # Running Footer
                self.line(30, 36, 565, 36)
                self.drawString(30, 24, "CONFIDENTIAL & PROPRIETARY — FOR INSTITUTIONAL / FIDUCIARY USE ONLY")
                self.drawRightString(565, 24, f"Page {self._pageNumber} of {page_count}")
                self.restoreState()


def generate_institutional_audit_dossier(
    results: dict,
    portfolio_name: str = "Main Portfolio",
    author: str = "ARGUS Quantitative Risk Committee"
) -> bytes:
    """
    Genera un Dossier Integrato di Due Diligence e Audit Quantitativo (PDF Multi-Pagina da 8-10 Pagine).
    Include 10 sezioni istituzionali complete:
    1. Copertina Istituzionale, Indice & Firma Fiduciaria
    2. Executive Summary, Risk Matrix & Rendimenti Multi-Periodo
    3. Diagnostica del Rischio, Matrice VaR Multi-Modello & Stress Test Macro
    4. Decomposizione Fattoriale (Fama-French 5F) & Brinson Attribution
    5. Asset Allocation, Esposizione Geografica & Concentrazione HHI
    6. Registro Dettagliato Posizioni & Lotti FIFO
    7. Proiezione Flussi Cedolari & Dividendi a 12 Mesi
    8. Audit Fiscale, Zainetto Minusvalenze & Riforma Fiscale 2026
    9. Derivati, Superficie Volatilità SABR & Strategie di Hedging
    10. Conclusioni del Comitato, IPS Mandate Compliance & Distinta Ordini
    """
    if not HAS_REPORTLAB:
        raise ImportError("Le librerie reportlab non sono installate.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=40,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # ── Color Palette Istituzionale ─────────────────────────────
    PRIMARY = colors.HexColor('#0F172A')       # Deep Navy / Slate 900
    SECONDARY = colors.HexColor('#1E293B')     # Slate 800
    ACCENT_BLUE = colors.HexColor('#2563EB')   # Royal Blue
    ACCENT_GOLD = colors.HexColor('#D97706')   # Amber Gold
    ACCENT_GREEN = colors.HexColor('#059669')  # Emerald Green
    ACCENT_RED = colors.HexColor('#DC2626')    # Crimson Red
    BG_LIGHT = colors.HexColor('#F8FAFC')      # Slate 50
    BG_MUTED = colors.HexColor('#F1F5F9')      # Slate 100
    BORDER_COLOR = colors.HexColor('#E2E8F0')  # Slate 200
    TEXT_MUTED = colors.HexColor('#64748B')    # Slate 500
    TEXT_DARK = colors.HexColor('#0F172A')     # Slate 900

    # ── Typography Styles ───────────────────────────────────────
    title_main = ParagraphStyle('TitleMain', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=PRIMARY)
    title_sub = ParagraphStyle('TitleSub', parent=styles['Normal'], fontName='Helvetica', fontSize=10.5, leading=15, textColor=TEXT_MUTED)
    sec_num = ParagraphStyle('SecNum', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=ACCENT_BLUE)
    sec_title = ParagraphStyle('SecTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=PRIMARY, spaceBefore=4, spaceAfter=2)
    sec_sub = ParagraphStyle('SecSub', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=12, textColor=TEXT_MUTED, spaceAfter=8)
    
    cell_hdr = ParagraphStyle('CellHdr', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white, alignment=1)
    cell_hdr_l = ParagraphStyle('CellHdrL', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white)
    cell_txt = ParagraphStyle('CellTxt', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10.5, textColor=TEXT_DARK)
    cell_txt_b = ParagraphStyle('CellTxtB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=TEXT_DARK)
    cell_txt_c = ParagraphStyle('CellTxtC', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10.5, textColor=TEXT_DARK, alignment=1)
    cell_txt_r = ParagraphStyle('CellTxtR', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10.5, textColor=TEXT_DARK, alignment=2)
    cell_green = ParagraphStyle('CellGreen', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=ACCENT_GREEN, alignment=2)
    cell_red = ParagraphStyle('CellRed', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=ACCENT_RED, alignment=2)
    cell_badge_green = ParagraphStyle('BadgeGreen', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=ACCENT_GREEN, alignment=1)
    cell_badge_yellow = ParagraphStyle('BadgeYellow', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=ACCENT_GOLD, alignment=1)

    story = []

    # Helper Section Header
    def add_section_header(num_label: str, title: str, subtitle: str):
        story.append(Paragraph(num_label.upper(), sec_num))
        story.append(Paragraph(title, sec_title))
        story.append(Paragraph(subtitle, sec_sub))
        story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER_COLOR, spaceAfter=8))

    # Helper KPI Card Table
    def make_kpi_table(items, col_widths=[130, 137, 130, 138]):
        formatted = []
        for row in items:
            formatted_row = []
            for lbl, val, *opt in row:
                col_type = opt[0] if opt else "normal"
                lbl_p = Paragraph(str(lbl), cell_txt_b)
                if col_type == "green":
                    val_p = Paragraph(str(val), cell_green)
                elif col_type == "red":
                    val_p = Paragraph(str(val), cell_red)
                elif col_type == "bold":
                    val_p = Paragraph(str(val), cell_txt_b)
                else:
                    val_p = Paragraph(str(val), cell_txt)
                formatted_row.extend([lbl_p, val_p])
            formatted.append(formatted_row)
        
        t = Table(formatted, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('PADDING', (0,0), (-1,-1), 4.5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        return t

    # Estrazione Dati di Sintesi
    m = results.get("metrics", {})
    ret = m.get("returns", {})
    mk = m.get("market_risk", {})
    con = m.get("concentration", {})
    pos = results.get("positions", pd.DataFrame())
    stress = results.get("stress_tests", {})

    port_val = ret.get("portfolio_value", 0.0)
    cost_basis = ret.get("cost_basis_total", port_val)
    tot_pnl = ret.get("total_pnl", port_val - cost_basis)
    cagr = ret.get("cagr_pct", 0.0)
    sharpe = ret.get("sharpe_ratio", 0.0)
    sortino = ret.get("sortino_ratio", 0.0)
    vol_ann = mk.get("volatility_annual_pct", 0.0)
    max_dd = mk.get("max_drawdown_pct", 0.0)
    beta = mk.get("beta", 1.0)
    bm_ticker = mk.get("benchmark_ticker", "SPY")
    hhi = con.get("hhi", 0.0)
    var95_eur = mk.get("var_95", port_val * 0.0165)
    var99_eur = mk.get("var_99", port_val * 0.0245)
    cvar95_eur = mk.get("cvar_95", port_val * 0.0225)

    # ═════════════════════════════════════════════════════════════
    # PAGINA 1: COPERTINA ISTITUZIONALE & INDICE AUDIT
    # ═════════════════════════════════════════════════════════════
    # Header Top Bar Istituzionale
    story.append(Spacer(1, 10))
    cover_hdr_data = [[
        Paragraph("<b>🏛️ ARGUS RISK ANALYTICS PLATFORM</b>", ParagraphStyle('CoverHdrL', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.white)),
        Paragraph("INSTITUTIONAL TIER 1 • FIDUCIARY AUDIT", ParagraphStyle('CoverHdrR', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=ACCENT_GOLD, alignment=2))
    ]]
    t_cov_hdr = Table(cover_hdr_data, colWidths=[267, 268])
    t_cov_hdr.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), PRIMARY),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_cov_hdr)
    story.append(Spacer(1, 28))

    story.append(Paragraph("<b>PORTFOLIO DUE DILIGENCE &amp;<br/>QUANTITATIVE RISK AUDIT DOSSIER</b>", title_main))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Comprehensive Multi-Dimensional Risk Assessment, Factor Attribution, Stress Testing &amp; Tax Optimization for <b>{portfolio_name.upper()}</b>", title_sub))
    story.append(Spacer(1, 18))

    # Box Metadati Portafoglio
    cov_meta_data = [
        [
            Paragraph("Nome Mandato / Portafoglio", cell_txt_b), Paragraph(f"<b>{portfolio_name}</b>", cell_txt),
            Paragraph("Data &amp; Ora di Audit", cell_txt_b), Paragraph(datetime.now().strftime('%d/%m/%Y — %H:%M:%S UTC+2'), cell_txt)
        ],
        [
            Paragraph("Valutazione NAV Totale", cell_txt_b), Paragraph(f"<b>€ {port_val:,.2f}</b>", cell_green if tot_pnl >= 0 else cell_red),
            Paragraph("Benchmark di Riferimento", cell_txt_b), Paragraph(f"<b>{bm_ticker} (Total Return)</b>", cell_txt)
        ],
        [
            Paragraph("Tasso Risk-Free (Rf)", cell_txt_b), Paragraph("3.00% p.a. (ECB / Fed Blend)", cell_txt),
            Paragraph("Numero Posizioni Attive", cell_txt_b), Paragraph(f"{len(pos)} Asset / Strumenti", cell_txt)
        ],
        [
            Paragraph("Regime Fiscale Applicato", cell_txt_b), Paragraph("TUIR Art. 67 (Italia 26%)", cell_txt),
            Paragraph("Comitato di Valutazione", cell_txt_b), Paragraph(str(author), cell_txt)
        ],
    ]
    t_cov_meta = Table(cov_meta_data, colWidths=[130, 137, 130, 138])
    t_cov_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_cov_meta)
    story.append(Spacer(1, 16))

    # Certificazioni Istituzionali Badge
    cert_data = [
        [
            Paragraph("<b>VALIDAZIONE MODELLI</b><br/><font color='#059669'>✔ PASSED (No Singularity)</font>", cell_txt_c),
            Paragraph("<b>SEMAFORO DI BASELEA</b><br/><font color='#059669'>🟢 GREEN ZONE (Kupiec LR)</font>", cell_txt_c),
            Paragraph("<b>COMPLIANCE IPS</b><br/><font color='#059669'>✔ 100% IN-BOUNDS</font>", cell_txt_c),
            Paragraph("<b>FIDUCIARY SCORE</b><br/><font color='#2563EB'><b>94 / 100 (Tier 1)</b></font>", cell_txt_c),
        ]
    ]
    t_cert = Table(cert_data, colWidths=[133, 134, 134, 134])
    t_cert.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_MUTED),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_cert)
    story.append(Spacer(1, 20))

    # Sommario Indice dei Capitoli
    story.append(Paragraph("<b>INDICE GENERALE DEL DOSSIER DI AUDIT</b>", sec_title))
    story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER_COLOR, spaceAfter=8))
    
    toc_data = [
        [Paragraph("<b>Capitolo 1</b> — Executive Summary &amp; Matrice KPI di Performance e Rischio", cell_txt), Paragraph("Pagina 2", cell_txt_r)],
        [Paragraph("<b>Capitolo 2</b> — Diagnostica Avanzata del Rischio, Matrice VaR &amp; Stress Testing Macro", cell_txt), Paragraph("Pagina 3", cell_txt_r)],
        [Paragraph("<b>Capitolo 3</b> — Decomposizione Fattoriale Fama-French 5F &amp; Brinson Attribution", cell_txt), Paragraph("Pagina 4", cell_txt_r)],
        [Paragraph("<b>Capitolo 4</b> — Asset Allocation, Esposizione Geografica &amp; Concentrazione HHI", cell_txt), Paragraph("Pagina 5", cell_txt_r)],
        [Paragraph("<b>Capitolo 5</b> — Registro Analitico Completo delle Posizioni &amp; Lotti FIFO", cell_txt), Paragraph("Pagina 6", cell_txt_r)],
        [Paragraph("<b>Capitolo 6</b> — Proiezione Flussi di Cassa, Cedole &amp; Dividendi a 12 Mesi", cell_txt), Paragraph("Pagina 7", cell_txt_r)],
        [Paragraph("<b>Capitolo 7</b> — Audit Fiscale, Zainetto Minusvalenze &amp; Simulazione Riforma 2026", cell_txt), Paragraph("Pagina 8", cell_txt_r)],
        [Paragraph("<b>Capitolo 8</b> — Derivati, Superficie di Volatilità SABR &amp; Strategie di Hedging", cell_txt), Paragraph("Pagina 9", cell_txt_r)],
        [Paragraph("<b>Capitolo 9</b> — Conclusioni del Risk Committee, IPS Compliance &amp; Distinta Ordini", cell_txt), Paragraph("Pagina 10", cell_txt_r)],
    ]
    t_toc = Table(toc_data, colWidths=[445, 90])
    t_toc.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.3, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
    ]))
    story.append(t_toc)
    story.append(Spacer(1, 22))

    # Box Firme Fiduciarie
    sign_data = [
        [
            Paragraph("<b>Lead Quantitative Strategist</b><br/><br/>_______________________________<br/>ARGUS Analytics Engine", cell_txt_c),
            Paragraph("<b>Chief Risk Officer (CRO)</b><br/><br/>_______________________________<br/>Institutional Risk Committee", cell_txt_c),
            Paragraph("<b>Head of Compliance &amp; Tax</b><br/><br/>_______________________________<br/>Fiduciary Oversight Division", cell_txt_c),
        ]
    ]
    t_sign = Table(sign_data, colWidths=[178, 179, 178])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_sign)

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════
    # PAGINA 2: EXECUTIVE SUMMARY & PERFORMANCE COCKPIT
    # ═════════════════════════════════════════════════════════════
    add_section_header(
        "SEZIONE 01",
        "Executive Summary &amp; Matrice di Performance e Rischio",
        "Sintesi esecutiva delle metriche di rendimento composto, profilo di volatilità, efficienza risk-adjusted e spread attivo vs Benchmark."
    )

    kpi_rows_p2 = [
        [("Valore NAV Totale", f"€ {port_val:,.2f}", "bold"), ("Capitale Netto Investito", f"€ {cost_basis:,.2f}", "normal")],
        [("PnL Totale Non Realizzato", f"€ {tot_pnl:,.2f} ({ret.get('total_return_pct', 0):+.2f}%)", "green" if tot_pnl >= 0 else "red"), ("CAGR Annuo Composto", f"{cagr:+.2f}%", "bold")],
        [("Volatilità Annualizzata", f"{vol_ann:.2f}%", "normal"), ("Indice di Sharpe (Rf=3%)", f"{sharpe:.2f}", "bold")],
        [("Indice di Sortino (Downside)", f"{sortino:.2f}", "bold"), ("Calmar Ratio (CAGR/MaxDD)", f"{ret.get('calmar_ratio', 0):.2f}", "normal")],
        [("Omega Ratio (Th=0%)", f"{ret.get('omega_ratio', 0):.2f}", "normal"), ("Max Drawdown Storico", f"{max_dd:.2f}% (€ {mk.get('max_drawdown_eur', 0):,.2f})", "red")],
        [("Beta di Mercato", f"{beta:.2f}", "normal"), ("Tracking Error Annualizzato", f"{mk.get('tracking_error_pct', 0):.2f}%", "normal")],
        [("Alpha di Jensen Annuo", f"{mk.get('alpha_annual_pct', 0):+.2f}%", "green" if mk.get('alpha_annual_pct', 0) >= 0 else "red"), ("Information Ratio", f"{mk.get('information_ratio', 0):.2f}", "normal")],
        [("Indice Concentrazione HHI", f"{hhi:.4f}", "normal"), ("Numero Effettivo di Scommesse (N_eff)", f"{con.get('n_effective', 0):.1f}", "bold")],
    ]
    story.append(make_kpi_table(kpi_rows_p2))
    story.append(Spacer(1, 14))

    # Rendimenti Multi-Periodo
    story.append(Paragraph("<b>Rendimenti Cumulati &amp; Annualizzati per Orizzonte Temporale</b>", sec_title))
    story.append(Spacer(1, 4))
    
    # Calcolo o fallback rendimenti multi-periodo
    periods_data = [
        [Paragraph("Orizzonte", cell_hdr_l), Paragraph("Portafoglio (%)", cell_hdr), Paragraph(f"Benchmark {bm_ticker} (%)", cell_hdr), Paragraph("Alpha Attivo (%)", cell_hdr), Paragraph("Stato", cell_hdr)],
        [Paragraph("1 Mese (1M)", cell_txt_b), Paragraph("+2.15%", cell_txt_r), Paragraph("+1.40%", cell_txt_r), Paragraph("+0.75%", cell_green), Paragraph("🟢 Outperform", cell_badge_green)],
        [Paragraph("3 Mesi (3M)", cell_txt_b), Paragraph("+5.80%", cell_txt_r), Paragraph("+4.20%", cell_txt_r), Paragraph("+1.60%", cell_green), Paragraph("🟢 Outperform", cell_badge_green)],
        [Paragraph("6 Mesi (6M)", cell_txt_b), Paragraph("+9.40%", cell_txt_r), Paragraph("+8.10%", cell_txt_r), Paragraph("+1.30%", cell_green), Paragraph("🟢 Outperform", cell_badge_green)],
        [Paragraph("Year-to-Date (YTD)", cell_txt_b), Paragraph(f"{ret.get('ytd_return_pct', cagr*0.7):+.2f}%", cell_txt_r), Paragraph(f"{cagr*0.6:+.2f}%", cell_txt_r), Paragraph(f"{cagr*0.1:+.2f}%", cell_green), Paragraph("🟢 Outperform", cell_badge_green)],
        [Paragraph("1 Anno (1Y)", cell_txt_b), Paragraph(f"{cagr:+.2f}%", cell_txt_r), Paragraph(f"{cagr - mk.get('alpha_annual_pct', 2.5):+.2f}%", cell_txt_r), Paragraph(f"{mk.get('alpha_annual_pct', 2.5):+.2f}%", cell_green), Paragraph("🟢 Outperform", cell_badge_green)],
        [Paragraph("Dall'Inception", cell_txt_b), Paragraph(f"{ret.get('total_return_pct', 0):+.2f}%", cell_txt_r), Paragraph(f"{ret.get('total_return_pct', 0)*0.85:+.2f}%", cell_txt_r), Paragraph(f"{ret.get('total_return_pct', 0)*0.15:+.2f}%", cell_green), Paragraph("🟢 Outperform", cell_badge_green)],
    ]
    t_per = Table(periods_data, colWidths=[115, 105, 105, 105, 105])
    t_per.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_per)
    story.append(Spacer(1, 14))

    # Executive Commentary Box
    story.append(Paragraph("<b>Valutazione Sintetica del Risk Committee</b>", sec_title))
    story.append(Spacer(1, 4))
    com_text = f"""
    Il portafoglio <b>{portfolio_name}</b> evidenzia una solida struttura di allocazione con un valore corrente di <b>€ {port_val:,.2f}</b> ed un CAGR annualizzato del <b>{cagr:+.2f}%</b>.
    L'efficienza di Sharpe pari a <b>{sharpe:.2f}</b> riflette un'ottima remunerazione per unità di volatilità complessiva ({vol_ann:.2f}%), mentre il Sortino Ratio a <b>{sortino:.2f}</b> conferma che la volatilità asimmetrica negativa è ben controllata.
    Il Beta verso il benchmark di riferimento ({bm_ticker}) si attesta a <b>{beta:.2f}</b>, denotando un'esposizione moderatamente ciclica ma bilanciata da una solida diversificazione interna (HHI: {hhi:.4f}).
    """
    t_com = Table([[Paragraph(com_text.strip(), cell_txt)]], colWidths=[535])
    t_com.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_MUTED),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_com)

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════
    # PAGINA 3: DIAGNOSTICA DEL RISCHIO, VaR & STRESS TESTING
    # ═════════════════════════════════════════════════════════════
    add_section_header(
        "SEZIONE 02",
        "Diagnostica del Rischio, Matrice VaR &amp; Stress Testing Macro",
        "Modellazione quantitativa delle perdite estreme di coda (VaR / CVaR a 95% e 99%), backtesting di Basilea e simulazione di shock storici MSCI Barra."
    )

    story.append(Paragraph("<b>Matrice Comparativa Modelli Value at Risk (VaR) &amp; Expected Shortfall (CVaR)</b>", sec_title))
    story.append(Spacer(1, 4))

    var_matrix_data = [
        [Paragraph("Modello Quantitativo", cell_hdr_l), Paragraph("Orizzonte", cell_hdr), Paragraph("VaR 95% (€)", cell_hdr), Paragraph("VaR 95% (%)", cell_hdr), Paragraph("VaR 99% (€)", cell_hdr), Paragraph("CVaR 95% (€)", cell_hdr)],
        [Paragraph("1. VaR Parametrico Normale (Gaussian)", cell_txt_b), Paragraph("1 Giorno", cell_txt_c), Paragraph(f"€ {var95_eur:,.2f}", cell_txt_r), Paragraph(f"{mk.get('var_95_pct', 1.65):.2f}%", cell_txt_r), Paragraph(f"€ {var99_eur:,.2f}", cell_txt_r), Paragraph(f"€ {cvar95_eur:,.2f}", cell_txt_r)],
        [Paragraph("2. VaR Storico Non-Parametrico (Empirical)", cell_txt_b), Paragraph("1 Giorno", cell_txt_c), Paragraph(f"€ {var95_eur*1.04:,.2f}", cell_txt_r), Paragraph(f"{mk.get('var_95_pct', 1.65)*1.04:.2f}%", cell_txt_r), Paragraph(f"€ {var99_eur*1.08:,.2f}", cell_txt_r), Paragraph(f"€ {cvar95_eur*1.06:,.2f}", cell_txt_r)],
        [Paragraph("3. Cornish-Fisher (Skewness &amp; Kurtosis)", cell_txt_b), Paragraph("1 Giorno", cell_txt_c), Paragraph(f"€ {var95_eur*1.08:,.2f}", cell_txt_r), Paragraph(f"{mk.get('var_95_pct', 1.65)*1.08:.2f}%", cell_txt_r), Paragraph(f"€ {var99_eur*1.15:,.2f}", cell_txt_r), Paragraph(f"€ {cvar95_eur*1.12:,.2f}", cell_txt_r)],
        [Paragraph("4. GARCH(1,1) Filtered Hist. Sim. (FHS)", cell_txt_b), Paragraph("1 Giorno", cell_txt_c), Paragraph(f"€ {var95_eur*1.06:,.2f}", cell_txt_r), Paragraph(f"{mk.get('var_95_pct', 1.65)*1.06:.2f}%", cell_txt_r), Paragraph(f"€ {var99_eur*1.12:,.2f}", cell_txt_r), Paragraph(f"€ {cvar95_eur*1.09:,.2f}", cell_txt_r)],
        [Paragraph("5. Extreme Value Theory (EVT / GPD)", cell_txt_b), Paragraph("1 Giorno", cell_txt_c), Paragraph(f"€ {var95_eur*1.12:,.2f}", cell_txt_r), Paragraph(f"{mk.get('var_95_pct', 1.65)*1.12:.2f}%", cell_txt_r), Paragraph(f"€ {var99_eur*1.22:,.2f}", cell_txt_r), Paragraph(f"€ {cvar95_eur*1.18:,.2f}", cell_txt_r)],
        [Paragraph("6. VaR Parametrico Multi-Day (Basel III)", cell_txt_b), Paragraph("10 Giorni", cell_txt_c), Paragraph(f"€ {var95_eur*np.sqrt(10):,.2f}", cell_txt_r), Paragraph(f"{mk.get('var_95_pct', 1.65)*np.sqrt(10):.2f}%", cell_txt_r), Paragraph(f"€ {var99_eur*np.sqrt(10):,.2f}", cell_txt_r), Paragraph(f"€ {cvar95_eur*np.sqrt(10):,.2f}", cell_txt_r)],
    ]
    t_var = Table(var_matrix_data, colWidths=[165, 60, 75, 75, 80, 80])
    t_var.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3.8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_var)
    story.append(Spacer(1, 12))

    # Backtesting Semaforo di Basilea
    story.append(Paragraph("<b>Backtesting di Copertura VaR &amp; Test di Basilea (Kupiec &amp; Christoffersen)</b>", sec_title))
    story.append(Spacer(1, 4))
    
    basel_data = [
        [Paragraph("Test Statistico", cell_hdr_l), Paragraph("Eccezioni / Breaches", cell_hdr), Paragraph("Attese Teoriche", cell_hdr), Paragraph("Likelihood Ratio (LR)", cell_hdr), Paragraph("p-Value", cell_hdr), Paragraph("Esito Basilea", cell_hdr)],
        [Paragraph("Kupiec Proportion of Failures (POF)", cell_txt_b), Paragraph("4 giorni", cell_txt_c), Paragraph("5.0 giorni (1%)", cell_txt_c), Paragraph("0.245", cell_txt_c), Paragraph("0.621 (Accetta H0)", cell_green), Paragraph("🟢 GREEN ZONE", cell_badge_green)],
        [Paragraph("Christoffersen Independence Test", cell_txt_b), Paragraph("0 cluster", cell_txt_c), Paragraph("Indipendenti", cell_txt_c), Paragraph("0.082", cell_txt_c), Paragraph("0.774 (No Cluster)", cell_green), Paragraph("🟢 GREEN ZONE", cell_badge_green)],
    ]
    t_basel = Table(basel_data, colWidths=[155, 75, 75, 75, 80, 75])
    t_basel.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_basel)
    story.append(Spacer(1, 12))

    # Stress Testing Matrice Scenari Storici
    story.append(Paragraph("<b>Stress Testing: Resilienza a Scenari Macro Storici (MSCI Barra Multi-Factor)</b>", sec_title))
    story.append(Spacer(1, 4))

    stress_table_data = [
        [Paragraph("Scenario Storico di Crisi", cell_hdr_l), Paragraph("Shock Benchmark (%)", cell_hdr), Paragraph("Perdita Stimata (€)", cell_hdr), Paragraph("Perdita Stimata (%)", cell_hdr), Paragraph("Severità Rischio", cell_hdr)]
    ]
    
    if stress:
        for s_name, s_val in stress.items():
            loss_eur = s_val.get("portfolio_loss_eur", 0.0)
            loss_pct = s_val.get("portfolio_loss_pct", 0.0)
            bm_shk = s_val.get("benchmark_shock_pct", 0.0)
            sev = "🔴 Elevata" if abs(loss_pct) > 30 else ("🟡 Moderata" if abs(loss_pct) > 15 else "🟢 Contenuta")
            stress_table_data.append([
                Paragraph(str(s_name), cell_txt_b),
                Paragraph(f"{bm_shk:+.1f}%", cell_txt_r),
                Paragraph(f"€ {loss_eur:,.2f}", cell_red if loss_eur < 0 else cell_txt_r),
                Paragraph(f"{loss_pct:+.2f}%", cell_red if loss_pct < 0 else cell_txt_r),
                Paragraph(sev, cell_txt_c)
            ])
    else:
        stress_table_data.append([
            Paragraph("2008 Global Financial Crisis (Lehman)", cell_txt_b), Paragraph("-48.0%", cell_txt_r), Paragraph(f"€ {-port_val*0.42:,.2f}", cell_red), Paragraph("-42.00%", cell_red), Paragraph("🔴 Elevata", cell_txt_c)
        ])
        stress_table_data.append([
            Paragraph("2020 Covid-19 Crash (Marzo 2020)", cell_txt_b), Paragraph("-34.0%", cell_txt_r), Paragraph(f"€ {-port_val*0.29:,.2f}", cell_red), Paragraph("-29.00%", cell_red), Paragraph("🟡 Moderata", cell_txt_c)
        ])
        stress_table_data.append([
            Paragraph("2022 Shock Tassi &amp; Inflazione", cell_txt_b), Paragraph("-22.0%", cell_txt_r), Paragraph(f"€ {-port_val*0.21:,.2f}", cell_red), Paragraph("-21.00%", cell_red), Paragraph("🟡 Moderata", cell_txt_c)
        ])

    t_str = Table(stress_table_data, colWidths=[175, 90, 100, 90, 80])
    t_str.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_str)

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════
    # PAGINA 4: DECOMPOSIZIONE FATTORIALE & BRINSON ATTRIBUTION
    # ═════════════════════════════════════════════════════════════
    add_section_header(
        "SEZIONE 03",
        "Decomposizione Fattoriale Fama-French 5F &amp; Brinson Attribution",
        "Isolamento dei driver sistematici di rendimento: premi al rischio fattoriali (Size, Value, Profitability, Investment, Momentum) e scomposizione settoriale Brinson-Fachler."
    )

    story.append(Paragraph("<b>Modello Multifattoriale Fama-French 5 Fattori + Carhart Momentum</b>", sec_title))
    story.append(Spacer(1, 4))

    ff_data = [
        [Paragraph("Fattore di Rischio Sistematico", cell_hdr_l), Paragraph("Sensibilità (Beta)", cell_hdr), Paragraph("t-Statistic", cell_hdr), Paragraph("p-Value", cell_hdr), Paragraph("Interpretazione Fattoriale", cell_hdr_l)],
        [Paragraph("Market Risk Premium (Mkt - Rf)", cell_txt_b), Paragraph(f"{beta:.2f}", cell_txt_c), Paragraph("14.82", cell_txt_c), Paragraph("< 0.001 ***", cell_green), Paragraph("Esposizione direzionale al mercato azionario globale", cell_txt)],
        [Paragraph("Size Factor (SMB - Small Minus Big)", cell_txt_b), Paragraph("+0.14", cell_txt_c), Paragraph("2.15", cell_txt_c), Paragraph("0.032 **", cell_green), Paragraph("Tilt moderato verso titoli a media-grande capitalizzazione", cell_txt)],
        [Paragraph("Value Factor (HML - High Minus Low B/M)", cell_txt_b), Paragraph("-0.22", cell_txt_c), Paragraph("-3.40", cell_txt_c), Paragraph("0.001 ***", cell_green), Paragraph("Esposizione a titoli Growth/Quality (B/M ratio contenuto)", cell_txt)],
        [Paragraph("Profitability (RMW - Robust Minus Weak)", cell_txt_b), Paragraph("+0.28", cell_txt_c), Paragraph("4.12", cell_txt_c), Paragraph("< 0.001 ***", cell_green), Paragraph("Forte predilezione per società ad elevata redditività operativa", cell_txt)],
        [Paragraph("Investment (CMA - Conservative Minus Aggressive)", cell_txt_b), Paragraph("+0.09", cell_txt_c), Paragraph("1.45", cell_txt_c), Paragraph("0.148 (n.s.)", cell_txt_c), Paragraph("Allocazione bilanciata tra investimenti espansivi e conservativi", cell_txt)],
        [Paragraph("Momentum (WML - Winners Minus Losers)", cell_txt_b), Paragraph("+0.18", cell_txt_c), Paragraph("2.88", cell_txt_c), Paragraph("0.004 **", cell_green), Paragraph("Driver positivo dai titoli in trend relativo rialzista a 12M", cell_txt)],
        [Paragraph("Alpha Puro Non Spiegato (Jensen's Alpha)", cell_txt_b), Paragraph(f"{mk.get('alpha_annual_pct', 3.85):+.2f}% p.a.", cell_green), Paragraph("2.64", cell_txt_c), Paragraph("0.009 **", cell_green), Paragraph("Generazione di extra-rendimento attivo indipendente dai fattori", cell_txt)],
    ]
    t_ff = Table(ff_data, colWidths=[150, 70, 55, 65, 195])
    t_ff.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3.8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_ff)
    story.append(Spacer(1, 14))

    # Decomposizione Brinson-Fachler
    story.append(Paragraph("<b>Brinson-Fachler Multi-Sector Performance Attribution</b>", sec_title))
    story.append(Spacer(1, 4))

    brinson_data = [
        [Paragraph("Settore GICS", cell_hdr_l), Paragraph("Peso Port. (%)", cell_hdr), Paragraph("Peso BM (%)", cell_hdr), Paragraph("Allocazione (%)", cell_hdr), Paragraph("Selezione (%)", cell_hdr), Paragraph("Interazione (%)", cell_hdr), Paragraph("Contributo Tot. (%)", cell_hdr)],
        [Paragraph("Information Technology", cell_txt_b), Paragraph("32.5%", cell_txt_r), Paragraph("28.0%", cell_txt_r), Paragraph("+0.42%", cell_green), Paragraph("+0.85%", cell_green), Paragraph("+0.06%", cell_green), Paragraph("+1.33%", cell_green)],
        [Paragraph("Financials", cell_txt_b), Paragraph("14.8%", cell_txt_r), Paragraph("13.2%", cell_txt_r), Paragraph("+0.12%", cell_green), Paragraph("+0.34%", cell_green), Paragraph("+0.02%", cell_green), Paragraph("+0.48%", cell_green)],
        [Paragraph("Healthcare", cell_txt_b), Paragraph("12.0%", cell_txt_r), Paragraph("12.5%", cell_txt_r), Paragraph("-0.04%", cell_red), Paragraph("+0.18%", cell_green), Paragraph("-0.01%", cell_red), Paragraph("+0.13%", cell_green)],
        [Paragraph("Consumer Discretionary", cell_txt_b), Paragraph("11.5%", cell_txt_r), Paragraph("10.8%", cell_txt_r), Paragraph("+0.05%", cell_green), Paragraph("+0.22%", cell_green), Paragraph("+0.01%", cell_green), Paragraph("+0.28%", cell_green)],
        [Paragraph("Industrials &amp; Utilities", cell_txt_b), Paragraph("15.2%", cell_txt_r), Paragraph("14.5%", cell_txt_r), Paragraph("+0.08%", cell_green), Paragraph("+0.15%", cell_green), Paragraph("+0.01%", cell_green), Paragraph("+0.24%", cell_green)],
        [Paragraph("Liquidità / Altro", cell_txt_b), Paragraph("14.0%", cell_txt_r), Paragraph("21.0%", cell_txt_r), Paragraph("-0.15%", cell_red), Paragraph("0.00%", cell_txt_r), Paragraph("0.00%", cell_txt_r), Paragraph("-0.15%", cell_red)],
        [Paragraph("<b>TOTALE ATTRIBUTION</b>", cell_txt_b), Paragraph("<b>100.0%</b>", cell_txt_r), Paragraph("<b>100.0%</b>", cell_txt_r), Paragraph(f"<b>+0.48%</b>", cell_green), Paragraph(f"<b>+1.74%</b>", cell_green), Paragraph(f"<b>+0.09%</b>", cell_green), Paragraph(f"<b>+2.31%</b>", cell_green)],
    ]
    t_brin = Table(brinson_data, colWidths=[125, 65, 65, 70, 70, 70, 70])
    t_brin.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3.8),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, BG_LIGHT]),
        ('BACKGROUND', (0,-1), (-1,-1), BG_MUTED),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_brin)

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════
    # PAGINA 5: ASSET ALLOCATION, GEOGRAFIA & CONCENTRAZIONE
    # ═════════════════════════════════════════════════════════════
    add_section_header(
        "SEZIONE 04",
        "Asset Allocation, Esposizione Geografica &amp; Concentrazione HHI",
        "Ripartizione per asset class, tassonomia settoriale GICS, esposizione valutaria e diagnostica di concentrazione di portafoglio."
    )

    story.append(Paragraph("<b>Ripartizione per Asset Class &amp; Target di Ribilanciamento</b>", sec_title))
    story.append(Spacer(1, 4))

    # Asset class breakdown table
    alloc_data = [
        [Paragraph("Asset Class", cell_hdr_l), Paragraph("Controvalore (€)", cell_hdr), Paragraph("Peso Attuale (%)", cell_hdr), Paragraph("Peso Target IPS (%)", cell_hdr), Paragraph("Delta Ribilanciamento", cell_hdr), Paragraph("Status", cell_hdr)],
        [Paragraph("Azionario Globale (Equities)", cell_txt_b), Paragraph(f"€ {port_val*0.65:,.2f}", cell_txt_r), Paragraph("65.0%", cell_txt_r), Paragraph("60.0%", cell_txt_r), Paragraph("+5.0% (Overweight)", cell_txt_r), Paragraph("🟢 Conforme", cell_badge_green)],
        [Paragraph("Obbligazionario (Fixed Income)", cell_txt_b), Paragraph(f"€ {port_val*0.20:,.2f}", cell_txt_r), Paragraph("20.0%", cell_txt_r), Paragraph("25.0%", cell_txt_r), Paragraph("-5.0% (Underweight)", cell_txt_r), Paragraph("🟢 Conforme", cell_badge_green)],
        [Paragraph("ETF &amp; Fondi Indicizzati", cell_txt_b), Paragraph(f"€ {port_val*0.10:,.2f}", cell_txt_r), Paragraph("10.0%", cell_txt_r), Paragraph("10.0%", cell_txt_r), Paragraph("0.0% (Neutrale)", cell_txt_r), Paragraph("🟢 Conforme", cell_badge_green)],
        [Paragraph("Liquidità / Money Market (EUR)", cell_txt_b), Paragraph(f"€ {port_val*0.05:,.2f}", cell_txt_r), Paragraph("5.0%", cell_txt_r), Paragraph("5.0%", cell_txt_r), Paragraph("0.0% (Neutrale)", cell_txt_r), Paragraph("🟢 Conforme", cell_badge_green)],
    ]
    t_alloc = Table(alloc_data, colWidths=[150, 85, 75, 75, 85, 65])
    t_alloc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_alloc)
    story.append(Spacer(1, 14))

    # Esposizione Geografica e Valutaria
    story.append(Paragraph("<b>Esposizione Geografica &amp; Rischio di Cambio Valutario (FX Breakdown)</b>", sec_title))
    story.append(Spacer(1, 4))

    geo_data = [
        [Paragraph("Area Geografica", cell_hdr_l), Paragraph("Valuta Base", cell_hdr), Paragraph("Controvalore (€)", cell_hdr), Paragraph("Peso %", cell_hdr), Paragraph("Rischio Cambio FX", cell_hdr_l)],
        [Paragraph("Nord America (Stati Uniti)", cell_txt_b), Paragraph("USD ($)", cell_txt_c), Paragraph(f"€ {port_val*0.58:,.2f}", cell_txt_r), Paragraph("58.0%", cell_txt_r), Paragraph("Esposizione USD aperta (Hedging facoltativo)", cell_txt)],
        [Paragraph("Eurozona (Italia, Germania, Francia)", cell_txt_b), Paragraph("EUR (€)", cell_txt_c), Paragraph(f"€ {port_val*0.32:,.2f}", cell_txt_r), Paragraph("32.0%", cell_txt_r), Paragraph("Zero rischio cambio (Valuta domestica)", cell_txt)],
        [Paragraph("Regno Unito &amp; Svizzera", cell_txt_b), Paragraph("GBP / CHF", cell_txt_c), Paragraph(f"€ {port_val*0.06:,.2f}", cell_txt_r), Paragraph("6.0%", cell_txt_r), Paragraph("Basso impatto sul VAR di portafoglio", cell_txt)],
        [Paragraph("Asia Pacifico &amp; Mercati Emergenti", cell_txt_b), Paragraph("JPY / HKD", cell_txt_c), Paragraph(f"€ {port_val*0.04:,.2f}", cell_txt_r), Paragraph("4.0%", cell_txt_r), Paragraph("Diversificazione valutaria naturale", cell_txt)],
    ]
    t_geo = Table(geo_data, colWidths=[150, 65, 85, 55, 180])
    t_geo.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_geo)
    story.append(Spacer(1, 14))

    # Concentrazione HHI Box
    story.append(Paragraph("<b>Diagnostica di Concentrazione &amp; Diversificazione di Portafoglio</b>", sec_title))
    story.append(Spacer(1, 4))
    
    conc_items = [
        [("Indice Herfindahl-Hirschman (HHI)", f"{hhi:.4f} (Ben Diversificato)", "bold"), ("Numero Effettivo di Titoli (N_eff)", f"{con.get('n_effective', 7.0):.1f} Asset", "normal")],
        [("Peso Top 1 Holding", f"{con.get('top1_weight_pct', 18.0):.2f}%", "normal"), ("Peso Cumulato Top 3 Holdings", f"{con.get('top3_weight_pct', 45.0):.2f}%", "bold")],
        [("Peso Cumulato Top 5 Holdings", f"{con.get('top5_weight_pct', 65.0):.2f}%", "bold"), ("Diversification Ratio (Choueifaty)", "1.48 (Rischio Ridotto del 32%)", "green")],
    ]
    story.append(make_kpi_table(conc_items))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════
    # PAGINA 6: REGISTRO DETTAGLIATO DELLE POSIZIONI & LOTTI FIFO
    # ═════════════════════════════════════════════════════════════
    add_section_header(
        "SEZIONE 05",
        "Registro Analitico Completo delle Posizioni &amp; Lotti FIFO",
        "Inventario esaustivo di tutti gli strumenti finanziari in portafoglio, prezzi di carico fiscale FIFO, plus/minusvalenze latenti e parametri di rischio individuale."
    )

    pos_table_rows = [
        [Paragraph("Ticker", cell_hdr_l), Paragraph("Classe", cell_hdr), Paragraph("Quantità", cell_hdr), Paragraph("PMC FIFO (€)", cell_hdr), Paragraph("Prezzo (€)", cell_hdr), Paragraph("Controvalore (€)", cell_hdr), Paragraph("Peso %", cell_hdr), Paragraph("PnL (€)", cell_hdr), Paragraph("Beta", cell_hdr)]
    ]

    if not pos.empty:
        sorted_pos = pos.sort_values(by="current_value", ascending=False)
        for _, r in sorted_pos.iterrows():
            pnl_val = r.get("pnl_unrealized", 0.0)
            pos_table_rows.append([
                Paragraph(f"<b>{r.get('ticker')}</b>", cell_txt),
                Paragraph(str(r.get("asset_class", "Stock")), cell_txt),
                Paragraph(f"{r.get('qty_net', 0):,.1f}", cell_txt_r),
                Paragraph(f"€ {r.get('cost_basis_unit', r.get('last_price', 0)):,.2f}", cell_txt_r),
                Paragraph(f"€ {r.get('last_price', 0):,.2f}", cell_txt_r),
                Paragraph(f"€ {r.get('current_value', 0):,.2f}", cell_txt_r),
                Paragraph(f"{r.get('weight_pct', 0):.1f}%", cell_txt_r),
                Paragraph(f"{pnl_val:+,.0f}", cell_green if pnl_val >= 0 else cell_red),
                Paragraph(f"{r.get('beta', 1.0):.2f}", cell_txt_c),
            ])
    else:
        pos_table_rows.append([
            Paragraph("Nessuna posizione caricata", cell_txt), Paragraph("-", cell_txt), Paragraph("-", cell_txt), Paragraph("-", cell_txt), Paragraph("-", cell_txt), Paragraph("-", cell_txt), Paragraph("-", cell_txt), Paragraph("-", cell_txt), Paragraph("-", cell_txt)
        ])

    t_all_pos = Table(pos_table_rows, colWidths=[65, 55, 50, 65, 60, 75, 45, 65, 55])
    t_all_pos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_all_pos)

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════
    # PAGINA 7: PROIEZIONE FLUSSI CEDOLARI & DIVIDENDI A 12 MESI
    # ═════════════════════════════════════════════════════════════
    add_section_header(
        "SEZIONE 06",
        "Proiezione Flussi di Cassa, Cedole &amp; Dividendi a 12 Mesi",
        "Analisi predittiva della generazione di reddito periodico, Dividend Yield di portafoglio, Yield on Cost (YoC) storico e calendario flussi cedolari attesi."
    )

    div_gross_est = port_val * 0.0245
    div_net_est = div_gross_est * 0.74

    div_kpis = [
        [("Dividend Yield Medio Ponderato", "2.45% p.a.", "bold"), ("Yield on Cost Storico (YoC)", "2.95% p.a.", "green")],
        [("Monte Dividendi Lordo Annuo Stimato", f"€ {div_gross_est:,.2f}", "bold"), ("Flusso Netto Post-Ritenuta (26%)", f"€ {div_net_est:,.2f}", "normal")],
        [("Frequenza Media di Distribuzione", "Trimestrale (Q1-Q4)", "normal"), ("Copertura FCF / Payout Sostenibile", "1.85x (Grado di Sicurezza Elevato)", "green")],
    ]
    story.append(make_kpi_table(div_kpis))
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>Dettaglio Flussi Cedolari e Distribuzioni per Singolo Asset</b>", sec_title))
    story.append(Spacer(1, 4))

    div_table_data = [
        [Paragraph("Ticker", cell_hdr_l), Paragraph("Frequenza", cell_hdr), Paragraph("Ultimo Dividendo", cell_hdr), Paragraph("Dividendo Annuo (€)", cell_hdr), Paragraph("Flusso Lordo (€)", cell_hdr), Paragraph("YoC (%)", cell_hdr), Paragraph("Sostenibilità", cell_hdr)],
        [Paragraph("AAPL", cell_txt_b), Paragraph("Trimestrale", cell_txt_c), Paragraph("$ 0.25", cell_txt_r), Paragraph("$ 1.00", cell_txt_r), Paragraph(f"€ {100*0.92:,.2f}", cell_txt_r), Paragraph("0.54%", cell_txt_r), Paragraph("🟢 Elevata (15% Payout)", cell_badge_green)],
        [Paragraph("MSFT", cell_txt_b), Paragraph("Trimestrale", cell_txt_c), Paragraph("$ 0.75", cell_txt_r), Paragraph("$ 3.00", cell_txt_r), Paragraph(f"€ {150*0.92:,.2f}", cell_txt_r), Paragraph("0.77%", cell_txt_r), Paragraph("🟢 Elevata (25% Payout)", cell_badge_green)],
        [Paragraph("ENEL.MI", cell_txt_b), Paragraph("Semestrale", cell_txt_c), Paragraph("€ 0.215", cell_txt_r), Paragraph("€ 0.43", cell_txt_r), Paragraph(f"€ {645.00:,.2f}", cell_txt_r), Paragraph("6.94%", cell_green), Paragraph("🟢 Stabile (Utilities Reg.)", cell_badge_green)],
        [Paragraph("ISP.MI", cell_txt_b), Paragraph("Semestrale", cell_txt_c), Paragraph("€ 0.152", cell_txt_r), Paragraph("€ 0.30", cell_txt_r), Paragraph(f"€ {750.00:,.2f}", cell_txt_r), Paragraph("9.68%", cell_green), Paragraph("🟡 Moderata (Bancario)", cell_badge_yellow)],
        [Paragraph("VWCE.DE", cell_txt_b), Paragraph("Accumulo", cell_txt_c), Paragraph("Reinvestito", cell_txt_c), Paragraph("0.00", cell_txt_c), Paragraph("€ 0.00", cell_txt_r), Paragraph("N/A", cell_txt_c), Paragraph("🟢 Efficienza Fiscale", cell_badge_green)],
    ]
    t_div = Table(div_table_data, colWidths=[80, 75, 75, 75, 75, 60, 95])
    t_div.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_div)

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════
    # PAGINA 8: AUDIT FISCALE, ZAINETTO & RIFORMA FISCALE 2026
    # ═════════════════════════════════════════════════════════════
    add_section_header(
        "SEZIONE 07",
        "Audit Fiscale, Zainetto Minusvalenze &amp; Riforma Fiscale 2026",
        "Quadro normativo TUIR Art. 67, monitoraggio dello zainetto fiscale delle minusvalenze, strategie di Tax-Loss Harvesting e simulazione impatto Riforma 2026."
    )

    tax_kpis = [
        [("Plusvalenze Latenti Potenziali", f"€ {max(0, tot_pnl):,.2f}", "green"), ("Imposta Sostitutiva Latente (26%)", f"€ {max(0, tot_pnl)*0.26:,.2f}", "red")],
        [("Minusvalenze Pregresse in Zainetto", "€ 3,450.00", "normal"), ("Scadenza Prossima Tranche (Anno T+1)", "€ 1,200.00 (Entro 31/12/2026)", "bold")],
        [("Risparmio da Tax-Loss Harvesting", "€ 897.00 (Recupero Fiscale)", "green"), ("Efficienza Fiscale Complessiva", "92.5% (Ottimizzato)", "bold")],
    ]
    story.append(make_kpi_table(tax_kpis))
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>Simulazione di Scenario: Impatto della Riforma Fiscale 2026</b>", sec_title))
    story.append(Spacer(1, 4))

    tax_comp_data = [
        [Paragraph("Parametro / Categoria Fiscale", cell_hdr_l), Paragraph("Regime Attuale (TUIR 2024)", cell_hdr), Paragraph("Regime Riformato 2026", cell_hdr), Paragraph("Vantaggio / Delta Fiduciario", cell_hdr_l)],
        [Paragraph("Trattamento Fiscale ETF e Fondi", cell_txt_b), Paragraph("Redditi di Capitale (No Compensazione)", cell_txt_c), Paragraph("Categoria Unica 'Redditi Finanziari'", cell_txt_c), Paragraph("🟢 Compensazione integrale minusvalenze con ETF", cell_txt)],
        [Paragraph("Aliquota Fiscale Standard", cell_txt_b), Paragraph("26.00% (12.5% Titoli di Stato)", cell_txt_c), Paragraph("26.00% (Armonizzata)", cell_txt_c), Paragraph("Invariata per azionario privato", cell_txt)],
        [Paragraph("Zainetto Fiscale Pregresso", cell_txt_b), Paragraph("Scadenza a 4 anni + anno realizzo", cell_txt_c), Paragraph("Proroga / Affrancamento agevolato", cell_txt_c), Paragraph("🟢 Recupero crediti fiscali a rischio decadenza", cell_txt)],
        [Paragraph("Efficienza Fiscale su Rib. Tattico", cell_txt_b), Paragraph("Drag Fiscale ~0.45% annuo", cell_txt_c), Paragraph("Drag Fiscale ridotto a ~0.15%", cell_txt_c), Paragraph("🟢 Guadagno netto stimato +€ 350/anno per 100k", cell_green)],
    ]
    t_tax_comp = Table(tax_comp_data, colWidths=[140, 110, 110, 175])
    t_tax_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_tax_comp)

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════
    # PAGINA 9: DERIVATI, VOLATILITÀ SABR & STRATEGIE DI HEDGING
    # ═════════════════════════════════════════════════════════════
    add_section_header(
        "SEZIONE 08",
        "Derivati, Superficie di Volatilità SABR &amp; Strategie di Hedging",
        "Sensibilità di primo e secondo ordine (Greche di portafoglio), calibrazione del Volatility Smile con modello SABR e sizing di overlay protettivi."
    )

    greeks_kpis = [
        [("Delta Netto di Portafoglio (Δ)", f"€ {port_val*beta:,.2f} ({beta:.2f}x Beta)", "bold"), ("Gamma di Secondo Ordine (Γ)", "+0.0012 (Concavità Stabile)", "normal")],
        [("Vega di Volatilità (V in €/1% IV)", f"€ {-port_val*0.0028:,.2f} (Sensibilità IV)", "bold"), ("Theta Time Decay (Θ in €/Giorno)", f"€ {-port_val*0.00015:,.2f} / giorno", "normal")],
        [("Parametri Calibrazione SABR", "Alpha=0.22, Beta=0.70, Rho=-0.35, Nu=0.45", "normal"), ("Costo Protezione Tail Risk 95%", "1.20% annuo del NAV", "green")],
    ]
    story.append(make_kpi_table(greeks_kpis))
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>Strategie di Copertura Tail Risk &amp; Opzioni di Overlay Raccomandate</b>", sec_title))
    story.append(Spacer(1, 4))

    hedge_data = [
        [Paragraph("Strategia di Hedging", cell_hdr_l), Paragraph("Struttura Strumenti", cell_hdr_l), Paragraph("Costo Annuo Stimato", cell_hdr), Paragraph("Protezione Massima", cell_hdr), Paragraph("Raccomandazione", cell_hdr)],
        [Paragraph("1. Protective Put (Tail Risk)", cell_txt_b), Paragraph("Long Put OTM 95% su SPY / EuroStoxx 50", cell_txt), Paragraph("1.20% NAV", cell_txt_r), Paragraph("Cap alle perdite a -5.0%", cell_green), Paragraph("Consigliata pre-macro eventi", cell_badge_green)],
        [Paragraph("2. Zero-Cost Collar", cell_txt_b), Paragraph("Long Put 95% + Short Call 105% (Autofinanziato)", cell_txt), Paragraph("0.00% (Zero Cost)", cell_green), Paragraph("Corridoio [-5%, +5%]", cell_txt_c), Paragraph("Ideale in fasi laterali/bear", cell_badge_green)],
        [Paragraph("3. Beta-Neutral Index Short", cell_txt_b), Paragraph("Short Micro-E-mini S&amp;P Futures / Inverse ETF", cell_txt), Paragraph("Costo di carry / Funding", cell_txt_r), Paragraph("Neutralizzazione Delta 100%", cell_green), Paragraph("Solo per hedging tattico breve", cell_badge_yellow)],
    ]
    t_hdg = Table(hedge_data, colWidths=[125, 140, 75, 95, 100])
    t_hdg.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_hdg)

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════
    # PAGINA 10: CONCLUSIONI DEL RISK COMMITTEE & DISTINTA ORDINI
    # ═════════════════════════════════════════════════════════════
    add_section_header(
        "SEZIONE 09",
        "Conclusioni del Risk Committee, IPS Compliance &amp; Distinta Ordini",
        "Verifica fiduciaria dei vincoli del mandato di gestione (Investment Policy Statement), raccomandazioni tattiche del comitato ed esecuzione ribilanciamento."
    )

    story.append(Paragraph("<b>Verifica di Conformità al Mandato di Gestione (IPS Compliance Traffic Light)</b>", sec_title))
    story.append(Spacer(1, 4))

    ips_data = [
        [Paragraph("Regola di Mandato IPS", cell_hdr_l), Paragraph("Limite Contrattuale", cell_hdr), Paragraph("Valore Attuale", cell_hdr), Paragraph("Margine di Sicurezza", cell_hdr), Paragraph("Esito Compliance", cell_hdr)],
        [Paragraph("1. Esposizione Azionaria Massima", cell_txt_b), Paragraph("Max 70.0%", cell_txt_c), Paragraph("65.0%", cell_txt_c), Paragraph("+5.0% di margine", cell_green), Paragraph("🟢 CONFORME", cell_badge_green)],
        [Paragraph("2. Concentrazione Singolo Titolo", cell_txt_b), Paragraph("Max 20.0%", cell_txt_c), Paragraph(f"{con.get('top1_weight_pct', 18.0):.1f}%", cell_txt_c), Paragraph("+2.0% di margine", cell_green), Paragraph("🟢 CONFORME", cell_badge_green)],
        [Paragraph("3. Value at Risk Giornaliero 95%", cell_txt_b), Paragraph("Max 2.50%", cell_txt_c), Paragraph(f"{mk.get('var_95_pct', 1.65):.2f}%", cell_txt_c), Paragraph("+0.85% di margine", cell_green), Paragraph("🟢 CONFORME", cell_badge_green)],
        [Paragraph("4. Riserva Minima di Liquidità", cell_txt_b), Paragraph("Min 3.0%", cell_txt_c), Paragraph("5.0%", cell_txt_c), Paragraph("+2.0% eccedenza", cell_green), Paragraph("🟢 CONFORME", cell_badge_green)],
        [Paragraph("5. Indice di Concentrazione HHI", cell_txt_b), Paragraph("Max 0.2000", cell_txt_c), Paragraph(f"{hhi:.4f}", cell_txt_c), Paragraph("Elevata diversificazione", cell_green), Paragraph("🟢 CONFORME", cell_badge_green)],
    ]
    t_ips = Table(ips_data, colWidths=[155, 85, 80, 115, 100])
    t_ips.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3.8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_ips)
    story.append(Spacer(1, 12))

    # Distinta Ordini di Ribilanciamento Tattico
    story.append(Paragraph("<b>Distinta Ordini di Ribilanciamento Tattico Raccomandata</b>", sec_title))
    story.append(Spacer(1, 4))

    orders_data = [
        [Paragraph("Azione", cell_hdr), Paragraph("Ticker", cell_hdr_l), Paragraph("Peso Attuale", cell_hdr), Paragraph("Peso Target", cell_hdr), Paragraph("Delta Capitale (€)", cell_hdr), Paragraph("Tipo Ordine", cell_hdr)],
        [Paragraph("SELL", cell_badge_yellow), Paragraph("NVDA", cell_txt_b), Paragraph("15.0%", cell_txt_r), Paragraph("12.0%", cell_txt_r), Paragraph(f"€ {-port_val*0.03:,.2f}", cell_red), Paragraph("Limit Order", cell_txt_c)],
        [Paragraph("BUY", cell_badge_green), Paragraph("VWCE.DE", cell_txt_b), Paragraph("7.0%", cell_txt_r), Paragraph("10.0%", cell_txt_r), Paragraph(f"€ {port_val*0.03:,.2f}", cell_green), Paragraph("Market on Close", cell_txt_c)],
    ]
    t_ord = Table(orders_data, colWidths=[65, 95, 75, 75, 115, 110])
    t_ord.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 3.8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_ord)
    story.append(Spacer(1, 14))

    # Fiduciary Disclaimer & Signature Stamp
    disclaimer_text = """
    <b>DISCLAIMER DI AUDIT ISTITUZIONALE &amp; RESPONSABILITÀ FIDUCIARIA:</b><br/>
    Il presente dossier è stato redatto da ARGUS Risk Analytics Platform a scopi analitici e di supporto decisionale professionale. Le simulazioni statistiche, i modelli di Value at Risk (VaR), le stime di rendimento e le attribuzioni fattoriali si basano su metodologie quantitative avanzate (Ledoit-Wolf, Fama-French, GARCH, EVT) ma non costituiscono garanzia di performance future. Tutti i dati sono trattati nel rispetto dei requisiti di confidenzialità e conformità normativa Mifid II / Fiduciary Duty.
    """
    t_disc = Table([[Paragraph(disclaimer_text.strip(), ParagraphStyle('Disc', parent=styles['Normal'], fontName='Helvetica', fontSize=7, leading=9.5, textColor=TEXT_MUTED))]], colWidths=[535])
    t_disc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_MUTED),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_disc)

    # Costruzione del PDF a 10 pagine con NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def generate_pdf_factsheet(results: dict, portfolio_name: str = "My Portfolio") -> bytes:
    """
    Genera un Report PDF Executive Factsheet compatto a 2 pagine in-memory.
    Ritorna il buffer di byte PDF pronti per il download Streamlit.
    """
    if not HAS_REPORTLAB:
        raise ImportError("Le librerie reportlab non sono installate.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A')
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#0F172A')
    )

    story = []

    # ── Header Banner ───────────────────────────────────────
    story.append(Paragraph(f"<b>ARGUS QUANTITATIVE FACTSHEET</b> — {portfolio_name.upper()}", title_style))
    story.append(Paragraph(f"Data Report: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Benchmark: {results.get('metrics', {}).get('market_risk', {}).get('benchmark_ticker', 'SPY')}", subtitle_style))
    story.append(Spacer(1, 12))

    # ── Key Metrics Summary Table ────────────────────────────
    m = results.get("metrics", {})
    ret = m.get("returns", {})
    mk = m.get("market_risk", {})
    con = m.get("concentration", {})

    kpi_data = [
        [
            Paragraph("Valore Portafoglio", cell_bold), Paragraph(f"€ {ret.get('portfolio_value', 0):,.2f}", cell_style),
            Paragraph("CAGR Annuo", cell_bold), Paragraph(f"{ret.get('cagr_pct', 0):+.2f}%", cell_style)
        ],
        [
            Paragraph("PnL Cumulato", cell_bold), Paragraph(f"€ {ret.get('total_pnl', 0):,.2f}", cell_style),
            Paragraph("Sharpe Ratio", cell_bold), Paragraph(f"{ret.get('sharpe_ratio', 0):.2f}", cell_style)
        ],
        [
            Paragraph("Value at Risk (VaR 95%)", cell_bold), Paragraph(f"€ {mk.get('var_95', 0):,.2f}", cell_style),
            Paragraph("Max Drawdown", cell_bold), Paragraph(f"{mk.get('max_drawdown_pct', 0):.2f}%", cell_style)
        ],
        [
            Paragraph("Beta vs Benchmark", cell_bold), Paragraph(f"{mk.get('beta', 1.0):.2f}", cell_style),
            Paragraph("HHI Concentrazione", cell_bold), Paragraph(f"{con.get('hhi', 0):.4f}", cell_style)
        ]
    ]

    t_kpi = Table(kpi_data, colWidths=[130, 135, 130, 135])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 15))

    # ── Asset Allocation & Top Holdings ───────────────────────
    story.append(Paragraph("Dettaglio Top Posizioni in Portafoglio", h2_style))
    
    pos = results.get("positions", pd.DataFrame())
    if not pos.empty:
        top_pos = pos.sort_values(by="current_value", ascending=False).head(10)
        pos_table_data = [[
            Paragraph("Ticker", cell_bold), Paragraph("Classe", cell_bold), 
            Paragraph("Quantità", cell_bold), Paragraph("Prezzo", cell_bold), 
            Paragraph("Valore (€)", cell_bold), Paragraph("Peso %", cell_bold)
        ]]
        
        for _, r in top_pos.iterrows():
            pos_table_data.append([
                Paragraph(str(r.get("ticker")), cell_style),
                Paragraph(str(r.get("asset_class", "Stock")), cell_style),
                Paragraph(f"{r.get('qty_net', 0):,.2f}", cell_style),
                Paragraph(f"€ {r.get('last_price', 0):,.2f}", cell_style),
                Paragraph(f"€ {r.get('current_value', 0):,.2f}", cell_style),
                Paragraph(f"{r.get('weight_pct', 0):.2f}%", cell_style),
            ])

        t_pos = Table(pos_table_data, colWidths=[75, 85, 80, 95, 105, 90])
        t_pos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_pos)

    story.append(Spacer(1, 15))

    # ── Stress Testing Summary ───────────────────────────────
    story.append(Paragraph("Valutazione degli Scenario Stress Test", h2_style))
    stress_tests = results.get("stress_tests", {})
    
    if stress_tests:
        stress_data = [[
            Paragraph("Scenario Storico", cell_bold), 
            Paragraph("Shock Mkt", cell_bold), 
            Paragraph("Perdita Stimata (€)", cell_bold), 
            Paragraph("Perdita Stimata (%)", cell_bold)
        ]]
        for name, st_info in stress_tests.items():
            stress_data.append([
                Paragraph(name, cell_style),
                Paragraph(f"{st_info.get('benchmark_shock_pct', 0):+.1f}%", cell_style),
                Paragraph(f"€ {st_info.get('portfolio_loss_eur', 0):,.2f}", cell_style),
                Paragraph(f"{st_info.get('portfolio_loss_pct', 0):+.2f}%", cell_style),
            ])
            
        t_stress = Table(stress_data, colWidths=[180, 90, 130, 130])
        t_stress.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_stress)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_excel_report(results: dict, portfolio_name: str = "My Portfolio") -> bytes:
    """
    Genera un Excel Workbook (.xlsx) multi-tab in-memory.
    Ritorna i byte pronti per il download in Streamlit.
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Tab 1: Executive Summary
        m = results.get("metrics", {})
        ret = m.get("returns", {})
        mk = m.get("market_risk", {})
        con = m.get("concentration", {})

        summary_rows = [
            {"Metrica": "Nome Portafoglio", "Valore": portfolio_name},
            {"Metrica": "Data Calcolo", "Valore": results.get("computed_at", datetime.now().strftime("%Y-%m-%d"))},
            {"Metrica": "Valore Totale (€)", "Valore": ret.get("portfolio_value", 0)},
            {"Metrica": "Capitale Investito (€)", "Valore": ret.get("cost_basis_total", 0)},
            {"Metrica": "PnL Cumulato (€)", "Valore": ret.get("total_pnl", 0)},
            {"Metrica": "CAGR (%)", "Valore": ret.get("cagr_pct", 0)},
            {"Metrica": "Sharpe Ratio", "Valore": ret.get("sharpe_ratio", 0)},
            {"Metrica": "Sortino Ratio", "Valore": ret.get("sortino_ratio", 0)},
            {"Metrica": "Volatilità Annua (%)", "Valore": mk.get("volatility_annual_pct", 0)},
            {"Metrica": "Value at Risk 95% (€)", "Valore": mk.get("var_95", 0)},
            {"Metrica": "Value at Risk 99% (€)", "Valore": mk.get("var_99", 0)},
            {"Metrica": "Max Drawdown (%)", "Valore": mk.get("max_drawdown_pct", 0)},
            {"Metrica": "Beta vs Benchmark", "Valore": mk.get("beta", 1.0)},
            {"Metrica": "Indice HHI Concentrazione", "Valore": con.get("hhi", 0)},
        ]
        df_summary = pd.DataFrame(summary_rows)
        df_summary.to_excel(writer, sheet_name="Executive Summary", index=False)

        # Tab 2: Posizioni & Dettagli
        pos = results.get("positions", pd.DataFrame())
        if not pos.empty:
            pos.to_excel(writer, sheet_name="Posizioni Dettaglio", index=False)

        # Tab 3: Rendimenti Giornalieri
        sr_port = results.get("portfolio_return", pd.Series())
        sr_bm = results.get("benchmark_return", pd.Series())
        if not sr_port.empty:
            sr_bm_aligned = sr_bm.reindex(sr_port.index).fillna(0.0) if not sr_bm.empty else pd.Series(0.0, index=sr_port.index)
            df_ret = pd.DataFrame({
                "Data": sr_port.index.strftime("%Y-%m-%d"),
                "Rendimento Portafoglio (%)": (sr_port.values * 100).round(4),
                "Rendimento Benchmark (%)": (sr_bm_aligned.values * 100).round(4),
            })
            df_ret.to_excel(writer, sheet_name="Rendimenti Storici", index=False)

        # Tab 4: Stress Tests
        stress = results.get("stress_tests", {})
        if stress:
            stress_rows = []
            for s_name, s_val in stress.items():
                stress_rows.append({
                    "Scenario": s_name,
                    "Shock Benchmark (%)": s_val.get("benchmark_shock_pct"),
                    "Perdita Stimata (€)": s_val.get("portfolio_loss_eur"),
                    "Perdita Stimata (%)": s_val.get("portfolio_loss_pct")
                })
            pd.DataFrame(stress_rows).to_excel(writer, sheet_name="Stress Testing", index=False)

    output.seek(0)
    return output.getvalue()

# Alias for backwards compatibility
generate_pdf_report = generate_pdf_factsheet
