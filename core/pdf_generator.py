# ============================================================
# pdf_generator.py — Pure Python PDF Executive Tear-Sheet Generator
# Investment Risk BI Platform
# (Zero external binary dependency for maximum portability)
# ============================================================

from datetime import datetime
import pandas as pd


def generate_executive_pdf_report(portfolio_name: str, risk_data: dict, base_currency: str = "EUR") -> bytes:
    """
    Genera un report PDF di sintesi (Executive Tear-Sheet) in puro Python senza dipendenze esterne.
    Restituisce i byte completi del file PDF valido.
    """
    positions = risk_data.get("positions", pd.DataFrame())
    metrics = risk_data.get("metrics", {})
    market_risk = metrics.get("market_risk", {})
    returns = metrics.get("returns", {})
    concentration = metrics.get("concentration", {})
    opt = risk_data.get("optimization", {})
    stress = risk_data.get("stress_tests", {})

    tot_val = positions["current_value"].sum() if not positions.empty else 0.0
    tot_pnl = positions["unrealized_pnl"].sum() if not positions.empty else 0.0
    tot_divs = positions["dividends_total"].sum() if not positions.empty else 0.0
    cagr = returns.get("cagr_pct", 0.0)
    sharpe = market_risk.get("sharpe_ratio", 0.0)
    vol = market_risk.get("volatility_pct", 0.0)
    max_dd = market_risk.get("max_drawdown_pct", 0.0)
    var_95 = market_risk.get("var_95_pct", 0.0)
    dr = concentration.get("diversification_ratio", 1.0)
    hhi = concentration.get("hhi_index", 0.0)
    ulcer = market_risk.get("ulcer_index", 0.0)
    ff_alpha = market_risk.get("ff_alpha_pct", 0.0)
    ff_beta = market_risk.get("ff_beta_mkt", 1.0)
    smb_tilt = market_risk.get("smb_tilt", 0.0)
    hml_tilt = market_risk.get("hml_tilt", 0.0)

    max_s = opt.get("max_sharpe", {})
    min_v = opt.get("min_vol", {})
    cov_type = opt.get("cov_type", "Ledoit-Wolf Shrinkage")

    st_dotcom = stress.get("Dot-Com Crash (Mar 2000 - Ott 2002)", {}).get("portfolio_loss_pct", 0.0)
    st_lehman = stress.get("Lehman Brothers (Sep-Nov 2008)", {}).get("portfolio_loss_pct", 0.0)
    st_downgrade = stress.get("US Downgrade Crisis (Ago 2011)", {}).get("portfolio_loss_pct", 0.0)
    st_covid = stress.get("COVID-19 Crash (Feb-Mar 2020)", {}).get("portfolio_loss_pct", 0.0)
    st_rates = stress.get("Tech & Rate Shock (Gen-Ott 2022)", {}).get("portfolio_loss_pct", 0.0)

    # Costruzione del testo formattato
    lines = [
        "ARGUS — EXECUTIVE RISK & PERFORMANCE TEAR-SHEET",
        f"Portafoglio: {portfolio_name} | Data: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Valuta Base: {base_currency}",
        "=" * 70,
        "",
        "1. INDICATORI CORE DI PORTAFOGLIO",
        f"   • Valore Totale: {tot_val:,.2f} {base_currency}",
        f"   • PnL Non Realizzato: {tot_pnl:,.2f} {base_currency}",
        f"   • Dividendi Totali Incassati: {tot_divs:,.2f} {base_currency}",
        f"   • CAGR (Tasso Annuo Composto): {cagr:.2f}%",
        f"   • Sharpe Ratio: {sharpe:.2f}",
        f"   • Volatilita Annualizzata: {vol:.2f}%",
        f"   • Max Drawdown: {max_dd:.2f}%",
        f"   • Ulcer Index (UI): {ulcer:.2f}",
        f"   • VaR 95% Parametrico (1g): {var_95:.2f}%",
        f"   • Diversification Ratio (DR): {dr:.2f}",
        f"   • Herfindahl Index (HHI): {hhi:.4f}",
        "",
        "2. STYLE ANALYSIS (FAMA-FRENCH 3-FACTOR MODEL)",
        f"   • Alpha Fama-French: {ff_alpha:+.2f}%",
        f"   • Market Beta (FF): {ff_beta:.2f}",
        f"   • SMB Tilt (Size): {smb_tilt:+.2f} (Small vs Large Cap)",
        f"   • HML Tilt (Value): {hml_tilt:+.2f} (Value vs Growth)",
        "",
        "3. OTTIMIZZAZIONE E FRONTIERA EFFICIENTE (MARKOWITZ & LEDOIT-WOLF)",
        f"   Stima Covarianza: {cov_type}",
        f"   • Max Sharpe: Rend. {max_s.get('return', 0)*100:.2f}% | Rischio {max_s.get('risk', 0)*100:.2f}% | Sharpe {max_s.get('sharpe', 0):.2f}",
        f"   • Min Volatility: Rend. {min_v.get('return', 0)*100:.2f}% | Rischio {min_v.get('risk', 0)*100:.2f}% | Sharpe {min_v.get('sharpe', 0):.2f}",
        "",
        "4. SINTESI STRESS TEST (CRISI STORICHE REALI)",
        f"   • Dot-Com Crash (2000-2002): {st_dotcom:.2f}%",
        f"   • Lehman Brothers (2008): {st_lehman:.2f}%",
        f"   • US Downgrade Crisis (2011): {st_downgrade:.2f}%",
        f"   • COVID-19 Crash (2020): {st_covid:.2f}%",
        f"   • Tech & Rate Shock (2022): {st_rates:.2f}%",
        "",
        "5. DETTAGLIO POSIZIONI E RISCHIO LIQUIDITA (ADV)",
        f"   {'Ticker':<9} | {'Valore':>11} | {'Peso':>7} | {'YoC %':>7} | {'Liquidaz. (ADV)':>16}",
        "   " + "-" * 66
    ]

    if not positions.empty:
        for _, row in positions.iterrows():
            t = str(row.get("ticker", ""))[:8]
            v = f"{row.get('current_value', 0):,.2f}"
            w = f"{row.get('weight_pct', 0):.1f}%"
            yoc = f"{row.get('yield_on_cost_pct', 0):.1f}%"
            dtl_v = row.get("days_to_liquidate")
            dtl = f"{dtl_v:.1f} gg" if dtl_v is not None else "N/A"
            lines.append(f"   {t:<9} | {v:>11} | {w:>7} | {yoc:>7} | {dtl:>16}")

    lines.append("")
    lines.append("Generato da ARGUS Risk Analytics Platform")

    # Pure PDF Stream Writer
    return _build_pdf_from_text("\n".join(lines))


def _build_pdf_from_text(text_content: str) -> bytes:
    """
    Costruisce un PDF valido (spec standard PDF 1.4) contenente il testo formattato.
    """
    text_lines = text_content.split("\n")
    
    # Costruzione comandi PDF stream
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

    objects = []
    # Obj 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # Obj 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # Obj 3: Page
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n")
    # Obj 4: Resources
    objects.append(b"4 0 obj\n<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Courier >> >> >>\nendobj\n")
    # Obj 5: Stream
    stream_obj = f"5 0 obj\n<< /Length {len(stream_data)} >>\nstream\n".encode("ascii") + stream_data + b"\nendstream\nendobj\n"
    objects.append(stream_obj)

    # Building PDF binary layout
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


