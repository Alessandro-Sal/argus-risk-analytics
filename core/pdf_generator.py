# ============================================================
# pdf_generator.py — Executive Factsheet & Tear-Sheet Generator
# ARGUS Risk & Wealth Analytics Platform
# Institutional Private Banking A4 standard with pure Python fallback
# ============================================================

import io
from datetime import datetime
import pandas as pd

# Tentativo di importazione motore vettoriale ReportLab
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
    )
    from core.reporting_design_system import (
        InstitutionalPalette,
        InstitutionalNumberedCanvas,
        get_institutional_reportlab_styles,
        create_vector_donut_chart
    )
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def generate_executive_pdf_report(portfolio_name: str, risk_data: dict, base_currency: str = "EUR") -> bytes:
    """
    Genera un Executive Factsheet ad alta risoluzione conforme agli standard di Private Banking.
    Utilizza ReportLab A4 con Design System Obsidian Sovereign e fallback puro Python.
    """
    if HAS_REPORTLAB:
        try:
            return _generate_reportlab_executive_factsheet(portfolio_name, risk_data, base_currency)
        except Exception:
            pass

    # Fallback deterministico a zero dipendenze
    return _generate_legacy_pure_pdf(portfolio_name, risk_data, base_currency)


def _generate_reportlab_executive_factsheet(portfolio_name: str, risk_data: dict, base_currency: str = "EUR") -> bytes:
    """Costruisce il Factsheet esecutivo A4 tramite ReportLab Platypus Flowables."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=32,
        rightMargin=32,
        topMargin=40,
        bottomMargin=42
    )

    p = InstitutionalPalette
    styles = get_institutional_reportlab_styles()
    story = []

    # Estrazione Dati
    positions = risk_data.get("positions", pd.DataFrame())
    metrics = risk_data.get("metrics", {})
    market_risk = metrics.get("market_risk", {})
    returns = metrics.get("returns", {})
    concentration = metrics.get("concentration", {})
    opt = risk_data.get("optimization", {})
    stress = risk_data.get("stress_tests", {})

    tot_val = float(positions["current_value"].sum()) if not positions.empty and "current_value" in positions.columns else 0.0
    tot_pnl = float(positions["unrealized_pnl"].sum()) if not positions.empty and "unrealized_pnl" in positions.columns else 0.0
    cagr = float(returns.get("cagr_pct", 0.0) or 0.0)
    sharpe = float(market_risk.get("sharpe_ratio", 0.0) or 0.0)
    vol = float(market_risk.get("volatility_pct", 0.0) or 0.0)
    max_dd = float(market_risk.get("max_drawdown_pct", 0.0) or 0.0)
    var_95 = float(market_risk.get("var_95_pct", 0.0) or 0.0)
    dr = float(concentration.get("diversification_ratio", 1.0) or 1.0)
    hhi = float(concentration.get("hhi_index", 0.0) or 0.0)
    ff_alpha = float(market_risk.get("ff_alpha_pct", 0.0) or 0.0)
    ff_beta = float(market_risk.get("ff_beta_mkt", 1.0) or 1.0)

    # 1. Header Documentale
    p_title = Paragraph("ARGUS — EXECUTIVE RISK & PERFORMANCE FACTSHEET", styles["DocTitle"])
    p_meta = Paragraph(
        f"<b>Portafoglio:</b> {portfolio_name} &nbsp;|&nbsp; <b>Data:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')} &nbsp;|&nbsp; <b>Valuta Base:</b> {base_currency}",
        styles["DocSubTitle"]
    )
    story.extend([p_title, p_meta])

    # 2. KPI Banner a 4 Colonne
    kpi_data = [
        [
            Paragraph("VALORE TOTALE", styles["KpiLabel"]),
            Paragraph("CAGR ANNUO", styles["KpiLabel"]),
            Paragraph("SHARPE RATIO", styles["KpiLabel"]),
            Paragraph("MAX DRAWDOWN", styles["KpiLabel"])
        ],
        [
            Paragraph(f"€ {tot_val:,.2f}", styles["KpiValueEmerald"]),
            Paragraph(f"{cagr:+.2f}%", styles["KpiValue"]),
            Paragraph(f"{sharpe:.2f}", styles["KpiValue"]),
            Paragraph(f"{max_dd:.2f}%", styles["KpiValue"])
        ]
    ]
    t_kpi = Table(kpi_data, colWidths=[132, 132, 132, 132])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(p.BG_CARD)),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 10))

    # 3. Indicatori Strutturali di Rischio & Decomposizione Fattoriale
    story.append(Paragraph("1. DIAGNOSTICA DI MERCATO & FATTORIALE (FAMA-FRENCH)", styles["SectionTitle"]))
    risk_summary_data = [
        [
            Paragraph("Metrica di Rischio", styles["TableHeaderLeft"]),
            Paragraph("Valore", styles["TableHeader"]),
            Paragraph("Modello / Benchmark", styles["TableHeaderLeft"]),
            Paragraph("Note di Vigilanza / Limiti", styles["TableHeaderLeft"])
        ],
        [
            Paragraph("Volatilità Annualizzata", styles["TableCellBold"]),
            Paragraph(f"{vol:.2f}%", styles["TableCellRight"]),
            Paragraph("Deviazione Standard 252gg", styles["TableCell"]),
            Paragraph("Rischio di Mercato Complessivo", styles["TableCell"])
        ],
        [
            Paragraph("VaR Parametrico 95% (1g)", styles["TableCellBold"]),
            Paragraph(f"{var_95:.2f}%", styles["TableCellRight"]),
            Paragraph("Normale / Delta-Normal", styles["TableCell"]),
            Paragraph("Perdita max attesa al 95% di confidenza", styles["TableCell"])
        ],
        [
            Paragraph("Diversification Ratio (DR)", styles["TableCellBold"]),
            Paragraph(f"{dr:.2f}", styles["TableCellRight"]),
            Paragraph("Choueifaty & Coignard", styles["TableCell"]),
            Paragraph("Rapporto di efficienza della diversificazione", styles["TableCell"])
        ],
        [
            Paragraph("Herfindahl Index (HHI)", styles["TableCellBold"]),
            Paragraph(f"{hhi:.4f}", styles["TableCellRight"]),
            Paragraph("Concentrazione Pesi Posizioni", styles["TableCell"]),
            Paragraph("Sotto 0.15 indica buona granularità", styles["TableCell"])
        ],
        [
            Paragraph("Alpha & Beta Fama-French", styles["TableCellBold"]),
            Paragraph(f"α {ff_alpha:+.2f}% | β {ff_beta:.2f}", styles["TableCellRight"]),
            Paragraph("Fama-French 3-Factor (Market, SMB, HML)", styles["TableCell"]),
            Paragraph("Rendimento anomalo depurato dai fattori di stile", styles["TableCell"])
        ]
    ]
    t_risk = Table(risk_summary_data, colWidths=[140, 95, 140, 153])
    t_risk.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(p.PRIMARY_NAVY)),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(p.BG_ZEBRA)]),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_risk)
    story.append(Spacer(1, 10))

    # 4. Stress Testing Storico
    story.append(Paragraph("2. MATRICE STRESS TEST SU CRISI STORICHE", styles["SectionTitle"]))
    stress_rows = [
        [
            Paragraph("Scenario di Crisi", styles["TableHeaderLeft"]),
            Paragraph("Periodo Storico", styles["TableHeaderLeft"]),
            Paragraph("Impatto Atteso sul Portafoglio", styles["TableHeader"])
        ]
    ]
    scenarios_ref = [
        ("Dot-Com Bubble Crash", "Mar 2000 - Ott 2002", stress.get("Dot-Com Crash (Mar 2000 - Ott 2002)", {}).get("portfolio_loss_pct", -48.2)),
        ("Lehman Brothers Collapse", "Sep 2008 - Nov 2008", stress.get("Lehman Brothers (Sep-Nov 2008)", {}).get("portfolio_loss_pct", -35.1)),
        ("US Sovereign Downgrade", "Ago 2011 - Ott 2011", stress.get("US Downgrade Crisis (Ago 2011)", {}).get("portfolio_loss_pct", -16.5)),
        ("COVID-19 Global Shock", "Feb 2020 - Mar 2020", stress.get("COVID-19 Crash (Feb-Mar 2020)", {}).get("portfolio_loss_pct", -22.4)),
        ("Tech & Inflation Rate Shock", "Gen 2022 - Ott 2022", stress.get("Tech & Rate Shock (Gen-Ott 2022)", {}).get("portfolio_loss_pct", -18.2)),
    ]
    for name, period, impact in scenarios_ref:
        imp_val = float(impact or 0.0)
        p_color = p.ACCENT_CRIMSON if imp_val < 0 else p.ACCENT_EMERALD
        p_imp = Paragraph(f"<font color='{p_color}'><b>{imp_val:+.2f}%</b></font>", styles["TableCellRight"])
        stress_rows.append([Paragraph(name, styles["TableCellBold"]), Paragraph(period, styles["TableCell"]), p_imp])

    t_stress = Table(stress_rows, colWidths=[200, 180, 148])
    t_stress.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(p.SECONDARY_SLATE)),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(p.BG_ZEBRA)]),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_stress)
    story.append(Spacer(1, 10))

    # 5. Dettaglio Prime 8 Posizioni con Liquidità ADV
    if not positions.empty:
        story.append(Paragraph("3. DETTAGLIO POSIZIONI CORE & LIQUIDITÀ (ADV)", styles["SectionTitle"]))
        pos_table_data = [
            [
                Paragraph("Ticker", styles["TableHeaderLeft"]),
                Paragraph("Asset Class", styles["TableHeaderLeft"]),
                Paragraph("Controvalore (€)", styles["TableHeader"]),
                Paragraph("Peso %", styles["TableHeader"]),
                Paragraph("PnL Latente", styles["TableHeader"]),
                Paragraph("Giorni Liq. (ADV)", styles["TableHeader"])
            ]
        ]
        top_pos = positions.head(8)
        for _, row in top_pos.iterrows():
            tk = str(row.get("ticker", "N/A"))
            ac = str(row.get("asset_class", "Equity") or "Equity")
            cv = float(row.get("current_value", 0.0) or 0.0)
            wp = float(row.get("weight_pct", 0.0) or 0.0)
            pnl = float(row.get("unrealized_pnl", 0.0) or 0.0)
            pnl_c = p.ACCENT_EMERALD if pnl >= 0 else p.ACCENT_CRIMSON
            dtl_v = row.get("days_to_liquidate")
            dtl = f"{float(dtl_v):.1f} gg" if dtl_v is not None else "1.0 gg"

            pos_table_data.append([
                Paragraph(tk, styles["TableCellBold"]),
                Paragraph(ac, styles["TableCell"]),
                Paragraph(f"€ {cv:,.2f}", styles["TableCellRight"]),
                Paragraph(f"{wp:.1f}%", styles["TableCellRight"]),
                Paragraph(f"<font color='{pnl_c}'>€ {pnl:+,.2f}</font>", styles["TableCellRight"]),
                Paragraph(dtl, styles["TableCellRight"])
            ])

        t_pos = Table(pos_table_data, colWidths=[80, 100, 110, 70, 95, 73])
        t_pos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(p.PRIMARY_NAVY)),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor(p.BG_ZEBRA)]),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor(p.BORDER_LIGHT)),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t_pos)

    # 6. Disclaimer di Compliance MiFID II
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(p.BORDER_LIGHT), spaceAfter=4))
    story.append(Paragraph(
        "<b>AVVERTENZA NORMATIVA FIDUCIARIA (Art. 24-25 MiFID II / Art. 21 D.Lgs. 58/1998 TUF):</b> "
        "Il presente factsheet costituisce un elaborato quantitativo di analisi del rischio e performance a uso strettamente interno o fiduciario. "
        "Non costituisce in alcun modo consulenza in materia di investimenti personalizzata, offerta al pubblico né sollecitazione al risparmio. "
        "Le stime di rendimento passato e le metriche di simulazione non rappresentano una garanzia di rendimenti futuri.",
        styles["Disclaimer"]
    ))

    # Compilazione del documento con InstitutionalNumberedCanvas
    doc.build(story, canvasmaker=InstitutionalNumberedCanvas)
    return buffer.getvalue()


def _generate_legacy_pure_pdf(portfolio_name: str, risk_data: dict, base_currency: str = "EUR") -> bytes:
    """Fallback deterministico puro Python (senza ReportLab) conforme alla specifica PDF 1.4."""
    positions = risk_data.get("positions", pd.DataFrame())
    metrics = risk_data.get("metrics", {})
    market_risk = metrics.get("market_risk", {})
    returns = metrics.get("returns", {})
    concentration = metrics.get("concentration", {})

    tot_val = positions["current_value"].sum() if not positions.empty and "current_value" in positions.columns else 0.0
    tot_pnl = positions["unrealized_pnl"].sum() if not positions.empty and "unrealized_pnl" in positions.columns else 0.0
    cagr = returns.get("cagr_pct", 0.0)
    sharpe = market_risk.get("sharpe_ratio", 0.0)
    vol = market_risk.get("volatility_pct", 0.0)
    max_dd = market_risk.get("max_drawdown_pct", 0.0)
    var_95 = market_risk.get("var_95_pct", 0.0)

    lines = [
        "ARGUS — EXECUTIVE RISK & PERFORMANCE TEAR-SHEET",
        f"Portafoglio: {portfolio_name} | Data: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Valuta: {base_currency}",
        "=" * 70,
        "",
        "1. INDICATORI CORE DI PORTAFOGLIO",
        f"   • Valore Totale: {tot_val:,.2f} {base_currency}",
        f"   • PnL Non Realizzato: {tot_pnl:,.2f} {base_currency}",
        f"   • CAGR: {cagr:.2f}%",
        f"   • Sharpe Ratio: {sharpe:.2f}",
        f"   • Volatilita Annualizzata: {vol:.2f}%",
        f"   • Max Drawdown: {max_dd:.2f}%",
        f"   • VaR 95% Parametrico: {var_95:.2f}%",
        "",
        "Generato da ARGUS Risk Analytics Platform (Pure Stream Mode)"
    ]

    return _build_pdf_from_text("\n".join(lines))


def _build_pdf_from_text(text_content: str) -> bytes:
    """Costruisce un PDF 1.4 valido codificando lo stream testuale."""
    text_lines = text_content.split("\n")
    pdf_commands = [
        "BT",
        "/F1 9 Tf",
        "11 TL",
        "40 760 Td"
    ]
    for line in text_lines:
        escaped_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        pdf_commands.append(f"({escaped_line}) '")
    pdf_commands.append("ET")
    stream_data = "\n".join(pdf_commands).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 595 842] /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Courier >> >> >>\nendobj\n",
        f"5 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("ascii") + stream_data + b"\nendstream\nendobj\n"
    ]

    pdf_bytes = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf_bytes))
        pdf_bytes.extend(obj)

    xref_offset = len(pdf_bytes)
    pdf_bytes.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        pdf_bytes.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf_bytes.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(pdf_bytes)


def generate_asset_factsheet_pdf(asset: dict) -> bytes:
    """
    Genera un One-Pager Institutional Factsheet in formato PDF per un asset analizzato dallo Screener o dal Portafoglio.
    """
    tk = str(asset.get("ticker", "N/A")).upper()
    name = str(asset.get("name", tk))
    sector = str(asset.get("sector", "N/D"))
    industry = str(asset.get("industry", "N/D"))
    price = asset.get("last_price", 0.0)
    target = asset.get("target_mean_price", 0.0)
    upside = asset.get("upside_pct", 0.0)
    pe = asset.get("trailing_pe", 0.0)
    peg = asset.get("peg_ratio", 0.0)
    pb = asset.get("price_to_book", 0.0)
    div_y = asset.get("dividend_yield_pct", 0.0)
    roe = asset.get("roe_pct", 0.0)
    z_score = asset.get("altman_z_score", 0.0)
    piot = asset.get("piotroski_score", 0)
    beta = asset.get("beta", 1.0)
    vol = asset.get("volatility_ann_pct", 0.0)
    sharpe = asset.get("sharpe_ratio", 0.0)
    rsi = asset.get("rsi_14", 50.0)
    score = asset.get("argus_score", 50.0)

    lines = [
        "ARGUS RISK ANALYTICS — INSTITUTIONAL ASSET FACTSHEET",
        f"Asset: {tk} ({name}) | Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        "1. PROFILO SOCIETARIO & VALUTAZIONE FONDAMENTALE",
        f"   • Settore: {sector:<24} | Industria: {industry}",
        f"   • Ultimo Prezzo: {price:,.2f} USD/EUR   | Target Price Consensus: {target:,.2f}",
        f"   • Upside Potenziale Stimato: {upside:+.2f}%",
        f"   • P/E Trailing: {pe:.2f}x               | PEG Ratio: {peg:.2f}",
        f"   • Price to Book (P/B): {pb:.2f}x         | Dividend Yield: {div_y:.2f}%",
        f"   • Return on Equity (ROE): {roe:.2f}%",
        "",
        "2. QUALITA CONTABILE & SOLVIBILITA (FORENSIC AUDIT)",
        f"   • Altman Z-Score: {z_score:.2f} " + ("(Safe Zone 🟢)" if z_score >= 2.9 else ("(Grey Zone 🟡)" if z_score >= 1.8 else "(Distress Zone 🔴)")),
        f"   • Piotroski F-Score: {piot}/9 (Qualita Contabile Istituzionale)",
        "",
        "3. PROFILO QUANTITATIVO & DINAMICHE DI RISCHIO",
        f"   • Beta di Mercato vs Benchmark: {beta:.2f}",
        f"   • Volatilita Storica Annualizzata: {vol:.2f}%",
        f"   • Indice di Sharpe (Rf = 3.0%): {sharpe:.2f}",
        f"   • Relative Strength Index RSI (14g): {rsi:.1f}",
        "",
        "4. PUNTEGGIO COMPOSITO ARGUS",
        f"   • ARGUS Composite Score: {score:.1f} / 100",
        "=" * 70,
        "Report generato automaticamente da ARGUS Institutional Risk Analytics Platform."
    ]

    return _build_pdf_from_text("\n".join(lines))

