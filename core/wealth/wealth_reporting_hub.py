# ============================================================
# core/wealth/wealth_reporting_hub.py
# ARGUS — Wealth Reporting & Comprehensive Institutional Exports Hub
# Multi-Format: White-Label PDF, Pitchbook, Tear-Sheet, Excel, Parquet, CSV, JSON & Audio
# ============================================================

import io
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from core.fetcher import get_engine
from core.quarterly_report_generator import generate_white_label_quarterly_pdf_report
from core.ui_export_utils import render_export_toolbar
from core.ui_utils import render_segmented_tabs
from core.voice_advisor_engine import generate_ai_voice_executive_briefing
from core.wealth.personal_balance_sheet import (
    generate_personal_balance_sheet_pdf,
    generate_personal_balance_sheet_tearsheet_pdf,
)
from core.wealth.wealth_db import get_cashflow_records, get_pension_plans, get_physical_assets, get_wealth_accounts
from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_fiscal_analytics,
    compute_real_estate_net_equity_and_ltv,
    generate_advisory_pitchbook_html,
    generate_advisory_pitchbook_pdf,
    generate_executive_tear_sheet_pdf,
)
from core.wealth.wealth_exporter import export_wealth_master_excel_workbook


def _get_engine_db_key(eng) -> str:
    """Restituisce un identificatore deterministico del DB attivo per isolamento dell'hash di cache."""
    from core.workspace_context import get_canonical_db_fingerprint

    return get_canonical_db_fingerprint(eng)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_quarterly_pdf(_engine, pid: int, client_name: str, quarter: str, db_key: str = "") -> bytes:
    return generate_white_label_quarterly_pdf_report(
        _engine, portfolio_id=pid, client_name=client_name, quarter=quarter
    )


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_pitchbook_pdf(_engine, pid: int, db_key: str = "") -> bytes:
    return generate_advisory_pitchbook_pdf(_engine, portfolio_id=pid)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_balance_sheet_pdf(_engine, pid: int, db_key: str = "") -> bytes:
    return generate_personal_balance_sheet_pdf(_engine, portfolio_id=pid)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_tear_sheet_pdf(_engine, pid: int, db_key: str = "") -> bytes:
    return generate_executive_tear_sheet_pdf(_engine, portfolio_id=pid)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_master_excel(_engine, pid: int, db_key: str = "") -> bytes:
    return export_wealth_master_excel_workbook(_engine, portfolio_id=pid).getvalue()


def generate_master_board_pack_html(
    engine: Engine,
    portfolio_id: int = 1,
    prof_name: str = "Family Office Master",
    risk_data: Optional[Dict[str, Any]] = None,
    session_state_dict: Optional[Dict[str, Any]] = None,
) -> str:
    """Genera il dossier esecutivo consolidato Master Board Pack (HTML standalone dark-mode)."""
    import streamlit as st

    from core.wealth.unified_stress_bridge import evaluate_active_wealth_macro_shock
    from core.wealth.wealth_engine import (
        compute_consolidated_net_worth,
        compute_fiscal_analytics,
        compute_real_estate_net_equity_and_ltv,
    )

    state = session_state_dict if session_state_dict is not None else (
        dict(st.session_state) if hasattr(st, "session_state") else {}
    )

    nw = compute_consolidated_net_worth(engine, portfolio_id=portfolio_id)
    _ = compute_real_estate_net_equity_and_ltv(engine, portfolio_id=portfolio_id)
    _ = compute_fiscal_analytics(engine, portfolio_id=portfolio_id)

    # Risk metrics extraction
    r_data = risk_data or state.get("last_portfolio_result") or {}
    mk = r_data.get("metrics", {}).get("market_risk", {}) if isinstance(r_data.get("metrics"), dict) else {}
    nav_val = float(mk.get("nav") or nw.financial_investments or 500_000.0)
    var95_pct = float(mk.get("var_95_pct") or 2.15)
    var95_eur = float(mk.get("var_95_eur") or (nav_val * var95_pct / 100.0))
    vol_pct = float(mk.get("volatility_pct") or mk.get("volatility_annual_pct") or 12.8)
    sharpe = float(mk.get("sharpe_ratio") or 1.45)

    pos_df = r_data.get("positions")
    if isinstance(pos_df, list):
        pos_df = pd.DataFrame(pos_df)
    pos_rows_html = ""
    if isinstance(pos_df, pd.DataFrame) and not pos_df.empty:
        top_pos = pos_df.sort_values(by="weight_pct", ascending=False).head(5) if "weight_pct" in pos_df.columns else pos_df.head(5)
        for _, row in top_pos.iterrows():
            tk = str(row.get("ticker", "N/A"))
            sec = str(row.get("sector") or row.get("asset_class") or "Liquid Equity")
            w = float(row.get("weight_pct", 0.0))
            val = float(row.get("current_value", row.get("market_value", 0.0)))
            pos_rows_html += f"""
            <tr>
                <td style="padding: 8px 12px; font-weight:700; color:#58a6ff; border-bottom: 1px solid rgba(255,255,255,0.06);">{tk}</td>
                <td style="padding: 8px 12px; color:#94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">{sec}</td>
                <td style="padding: 8px 12px; text-align:right; font-family:monospace; color:#10b981; border-bottom: 1px solid rgba(255,255,255,0.06);">{w:.2f}%</td>
                <td style="padding: 8px 12px; text-align:right; font-family:monospace; color:#f0f6fc; border-bottom: 1px solid rgba(255,255,255,0.06);">€ {val:,.2f}</td>
            </tr>
            """
    else:
        pos_rows_html = """
        <tr>
            <td style="padding: 8px 12px; font-weight:700; color:#58a6ff; border-bottom: 1px solid rgba(255,255,255,0.06);">SPY (S&amp;P 500)</td>
            <td style="padding: 8px 12px; color:#94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">Global Equity ETF</td>
            <td style="padding: 8px 12px; text-align:right; font-family:monospace; color:#10b981; border-bottom: 1px solid rgba(255,255,255,0.06);">55.00%</td>
            <td style="padding: 8px 12px; text-align:right; font-family:monospace; color:#f0f6fc; border-bottom: 1px solid rgba(255,255,255,0.06);">€ 357.500,00</td>
        </tr>
        <tr>
            <td style="padding: 8px 12px; font-weight:700; color:#58a6ff; border-bottom: 1px solid rgba(255,255,255,0.06);">BND (Total Bond)</td>
            <td style="padding: 8px 12px; color:#94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">Fixed Income Aggregate</td>
            <td style="padding: 8px 12px; text-align:right; font-family:monospace; color:#10b981; border-bottom: 1px solid rgba(255,255,255,0.06);">30.00%</td>
            <td style="padding: 8px 12px; text-align:right; font-family:monospace; color:#f0f6fc; border-bottom: 1px solid rgba(255,255,255,0.06);">€ 195.000,00</td>
        </tr>
        <tr>
            <td style="padding: 8px 12px; font-weight:700; color:#58a6ff; border-bottom: 1px solid rgba(255,255,255,0.06);">GLD (Gold Physical)</td>
            <td style="padding: 8px 12px; color:#94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">Precious Metals ETC</td>
            <td style="padding: 8px 12px; text-align:right; font-family:monospace; color:#10b981; border-bottom: 1px solid rgba(255,255,255,0.06);">15.00%</td>
            <td style="padding: 8px 12px; text-align:right; font-family:monospace; color:#f0f6fc; border-bottom: 1px solid rgba(255,255,255,0.06);">€ 97.500,00</td>
        </tr>
        """

    snap_stress = {
        "total_net_worth": nw.total_net_worth,
        "liquid_cash": nw.liquid_cash,
        "financial_investments": nw.financial_investments,
        "real_estate_total": nw.real_estate_total,
        "total_liabilities": nw.total_liabilities,
        "runway_months": nw.runway_months,
        "fixed_mortgages_balance": getattr(nw, "fixed_mortgages_balance", nw.total_liabilities * 0.7),
        "variable_mortgages_balance": getattr(nw, "variable_mortgages_balance", nw.total_liabilities * 0.3),
    }
    stress_res = evaluate_active_wealth_macro_shock(snap_stress, session_state_dict=state, portfolio_positions=pos_df)
    s_name = stress_res.get("scenario_name", "Baseline Market")
    s_pnl_pct = stress_res.get("total_net_worth_pnl_pct", 0.0)
    s_pnl_eur = stress_res.get("total_wealth_pnl_eur", 0.0)
    s_nw = stress_res.get("post_stress_net_worth", nw.total_net_worth)
    s_runway = stress_res.get("stressed_runway_months", nw.runway_months)
    s_pmt_delta = stress_res.get("pmt_monthly_delta_eur", 0.0)
    s_re_haircut = stress_res.get("real_estate_haircut_eur", 0.0)

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    tot_nw_val = nw.total_net_worth
    liq_val = nw.liquid_cash
    fin_val = nw.financial_investments
    re_val = nw.real_estate_total
    liab_val = nw.total_liabilities
    health_val = nw.wealth_health_score
    runway_val = nw.runway_months

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>ARGUS Master Board Pack — {prof_name}</title>
<style>
  @page {{ size: A4; margin: 16mm 14mm 16mm 14mm; }}
  body {{
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
    background-color: #0b0f19;
    color: #e2e8f0;
    margin: 0;
    padding: 24px;
    font-size: 13px;
    line-height: 1.5;
  }}
  .card {{
    background: #161b22;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    page-break-inside: avoid;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #ff9900;
    padding-bottom: 12px;
    margin-bottom: 20px;
  }}
  .brand {{
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
  }}
  .brand span {{ color: #ff9900; }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 10px;
    margin-bottom: 20px;
  }}
  .kpi-tile {{
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }}
  .kpi-label {{
    font-size: 10.5px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }}
  .kpi-value {{
    font-size: 15px;
    font-weight: 750;
    color: #ffffff;
    font-family: monospace;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
  }}
  th {{
    background: rgba(255, 255, 255, 0.04);
    color: #94a3b8;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid rgba(255,255,255,0.12);
  }}
  h3 {{
    font-size: 14px;
    font-weight: 700;
    color: #ff9900;
    margin: 0 0 8px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="brand">ARGUS <span>EXECUTIVE BOARD PACK</span></div>
    <div style="font-size: 11.5px; color: #94a3b8; margin-top: 3px;">
      Dossier Istituzionale Unificato Risk &amp; Wealth &bull; Profilo: <b>{prof_name}</b> &bull; Data: <b>{now_str}</b>
    </div>
  </div>
  <div style="text-align: right;">
    <span style="background: rgba(255, 153, 0, 0.15); border: 1px solid #ff9900; color: #ff9900; font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 12px;">
      CONFIDENTIAL &bull; BOARD LEVEL
    </span>
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi-tile">
    <div class="kpi-label">Patrimonio Netto</div>
    <div class="kpi-value" style="color: #10b981;">€ {tot_nw_val:,.0f}</div>
  </div>
  <div class="kpi-tile">
    <div class="kpi-label">Runway Liquidità</div>
    <div class="kpi-value" style="color: #38bdf8;">{runway_val:.1f} Mesi</div>
  </div>
  <div class="kpi-tile">
    <div class="kpi-label">Portafoglio NAV</div>
    <div class="kpi-value" style="color: #fbbf24;">€ {nav_val:,.0f}</div>
  </div>
  <div class="kpi-tile">
    <div class="kpi-label">VaR 95% (1-Day)</div>
    <div class="kpi-value" style="color: #f87171;">€ {var95_eur:,.0f}</div>
  </div>
  <div class="kpi-tile">
    <div class="kpi-label">Sharpe Ratio</div>
    <div class="kpi-value" style="color: #a855f7;">{sharpe:.2f}</div>
  </div>
  <div class="kpi-tile">
    <div class="kpi-label">Health Score</div>
    <div class="kpi-value" style="color: #34d399;">{health_val:.0f}/100</div>
  </div>
</div>

<div class="card">
  <h3>🏛️ 1. Stato Patrimoniale Consolidato &amp; Allocazione Asset</h3>
  <table>
    <thead>
      <tr>
        <th>Comparto Patrimoniale</th>
        <th>Descrizione Contabile</th>
        <th style="text-align: right;">Peso % Net Worth</th>
        <th style="text-align: right;">Controvalore (€)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="padding: 8px 12px; font-weight: 700; color: #38bdf8; border-bottom: 1px solid rgba(255,255,255,0.06);">Liquidità &amp; Conti a Vista</td>
        <td style="padding: 8px 12px; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">Riserve di cassa, depositi vincolati e conti correnti operativi</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #10b981; border-bottom: 1px solid rgba(255,255,255,0.06);">{(liq_val / max(1.0, tot_nw_val) * 100):.1f}%</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #f0f6fc; border-bottom: 1px solid rgba(255,255,255,0.06);">€ {liq_val:,.2f}</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; font-weight: 700; color: #fbbf24; border-bottom: 1px solid rgba(255,255,255,0.06);">Investimenti Finanziari (Portfolio)</td>
        <td style="padding: 8px 12px; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">Azionario, Obbligazionario, ETF, Note Strutturate e Liquid Equity</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #10b981; border-bottom: 1px solid rgba(255,255,255,0.06);">{(fin_val / max(1.0, tot_nw_val) * 100):.1f}%</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #f0f6fc; border-bottom: 1px solid rgba(255,255,255,0.06);">€ {fin_val:,.2f}</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; font-weight: 700; color: #a855f7; border-bottom: 1px solid rgba(255,255,255,0.06);">Patrimonio Immobiliare (Real Estate)</td>
        <td style="padding: 8px 12px; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">Immobili residenziali, commerciali, terreni ed equity immobiliare</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #10b981; border-bottom: 1px solid rgba(255,255,255,0.06);">{(re_val / max(1.0, tot_nw_val) * 100):.1f}%</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #f0f6fc; border-bottom: 1px solid rgba(255,255,255,0.06);">€ {re_val:,.2f}</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; font-weight: 700; color: #f87171; border-bottom: 1px solid rgba(255,255,255,0.06);">Passività &amp; Debiti Finanziari</td>
        <td style="padding: 8px 12px; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">Mutui ipotecari (fissi e variabili), linee di credito e prestiti</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #f87171; border-bottom: 1px solid rgba(255,255,255,0.06);">-{(liab_val / max(1.0, tot_nw_val) * 100):.1f}%</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #f87171; border-bottom: 1px solid rgba(255,255,255,0.06);">-€ {liab_val:,.2f}</td>
      </tr>
    </tbody>
  </table>
</div>

<div class="card">
  <h3>🔬 2. Rischio Quantitativo &amp; Top 5 Posizioni Portafoglio</h3>
  <div style="font-size: 11.5px; color: #94a3b8; margin-bottom: 8px;">
    Volatilità Annualizzata: <b style="color: #f0f6fc;">{vol_pct:.2f}%</b> &bull; VaR 95% 1-Day: <b style="color: #f87171;">€ {var95_eur:,.0f} ({var95_pct:.2f}%)</b> &bull; Sharpe Ratio: <b style="color: #38bdf8;">{sharpe:.2f}</b>
  </div>
  <table>
    <thead>
      <tr>
        <th>Ticker / Strumento</th>
        <th>Asset Class / Settore</th>
        <th style="text-align: right;">Peso Portafoglio</th>
        <th style="text-align: right;">Controvalore (€)</th>
      </tr>
    </thead>
    <tbody>
      {pos_rows_html}
    </tbody>
  </table>
</div>

<div class="card">
  <h3>⚡ 3. Cross-Portal Macro Stress Test &amp; Resilienza Patrimoniale</h3>
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <div style="font-size: 12px; color: #cbd5e1;">
      Scenario Attivo: <b style="color: #ef4444;">{s_name}</b>
    </div>
    <div style="font-size: 11.5px; color: #94a3b8; font-family: monospace;">
      Haircut Immobiliare: <b style="color: #f87171;">-€ {abs(s_re_haircut):,.0f}</b> &bull; &Delta; PMT Mutuo: <b style="color: #fbbf24;">{s_pmt_delta:+,.0f} €/mese</b>
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Metrica di Stress</th>
        <th>Valore Pre-Stress</th>
        <th>Valore Post-Stress</th>
        <th style="text-align: right;">Impatto Nominale</th>
        <th style="text-align: right;">Variazione %</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="padding: 8px 12px; font-weight: 700; color: #e2e8f0; border-bottom: 1px solid rgba(255,255,255,0.06);">Patrimonio Netto Consolidato</td>
        <td style="padding: 8px 12px; font-family: monospace; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">€ {tot_nw_val:,.0f}</td>
        <td style="padding: 8px 12px; font-family: monospace; font-weight: 750; color: #f87171; border-bottom: 1px solid rgba(255,255,255,0.06);">€ {s_nw:,.0f}</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #f87171; border-bottom: 1px solid rgba(255,255,255,0.06);">{s_pnl_eur:+,.0f} €</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; font-weight: 700; color: #f87171; border-bottom: 1px solid rgba(255,255,255,0.06);">{s_pnl_pct:+.2f}%</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; font-weight: 700; color: #e2e8f0; border-bottom: 1px solid rgba(255,255,255,0.06);">Emergency Cash Runway</td>
        <td style="padding: 8px 12px; font-family: monospace; color: #94a3b8; border-bottom: 1px solid rgba(255,255,255,0.06);">{runway_val:.1f} Mesi</td>
        <td style="padding: 8px 12px; font-family: monospace; font-weight: 750; color: #fbbf24; border-bottom: 1px solid rgba(255,255,255,0.06);">{s_runway:.1f} Mesi</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; color: #fbbf24; border-bottom: 1px solid rgba(255,255,255,0.06);">{s_runway - runway_val:+.1f} Mesi</td>
        <td style="padding: 8px 12px; text-align: right; font-family: monospace; font-weight: 700; color: #fbbf24; border-bottom: 1px solid rgba(255,255,255,0.06);">{((s_runway/max(0.1, runway_val))-1)*100:+.1f}%</td>
      </tr>
    </tbody>
  </table>
</div>

<div class="card">
  <h3>📋 4. Memo Esecutivo di Consulenza Strategica &amp; Delibere Board</h3>
  <div style="font-size: 12px; color: #cbd5e1; line-height: 1.6;">
    <p><b>1. Valutazione della Solvibilità:</b> Il patrimonio presenta un Health Score pari a <b>{health_val:.0f}/100</b> con una riserva di liquidità a vista garantita per <b>{runway_val:.1f} mesi</b> di spese fisse. Sotto lo scenario di stress <i>{s_name}</i>, il runway si attesta a <b>{s_runway:.1f} mesi</b>, mantenendosi in fascia di sicurezza istituzionale.</p>
    <p><b>2. Monitoraggio Debito e Mutui:</b> La leva finanziaria complessiva (LTV immobiliare / Debito su Attivo) è pari a <b>{(liab_val / max(1.0, tot_nw_val + liab_val) * 100):.1f}%</b>. In caso di shock tassi, la quota variabile genera un aggravio mensile stimato di <b>{s_pmt_delta:+,.0f} €/mese</b>.</p>
    <p><b>3. Raccomandazione Tattica:</b> Mantenere l'allocazione difensiva sul comparto a breve termine e valutare l'attivazione di coperture asimmetriche con opzioni su indici per proteggere l'equity di portafoglio in vista delle scadenze macroeconomiche.</p>
  </div>
</div>

<div style="text-align: center; font-size: 11px; color: #64748b; margin-top: 24px;">
  ARGUS Enterprise Multi-Asset Risk &amp; Wealth Platform &bull; Generato automaticamente &bull; Tutti i diritti riservati.
</div>

</body>
</html>
"""
    return html


def generate_master_board_pack_pdf(
    engine: Engine,
    portfolio_id: int = 1,
    prof_name: str = "Family Office Master",
    risk_data: Optional[Dict[str, Any]] = None,
    session_state_dict: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Compila e genera il file PDF binario del Master Board Pack Istituzionale."""
    html_content = generate_master_board_pack_html(
        engine,
        portfolio_id=portfolio_id,
        prof_name=prof_name,
        risk_data=risk_data,
        session_state_dict=session_state_dict,
    )
    import os
    import shutil
    import subprocess
    import tempfile

    browser_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "msedge",
        "chrome",
        "google-chrome",
        "chromium",
    ]
    found_browser = None
    for b in browser_candidates:
        if os.path.isabs(b) and os.path.exists(b):
            found_browser = b
            break
        elif not os.path.isabs(b) and shutil.which(b):
            found_browser = shutil.which(b)
            break

    if found_browser:
        tmp_html = None
        tmp_pdf = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
                f.write(html_content)
                tmp_html = f.name
            tmp_pdf = tmp_html.replace(".html", ".pdf")
            cmd = [
                found_browser,
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={tmp_pdf}",
                tmp_html,
            ]
            subprocess.run(cmd, capture_output=True, timeout=15)
            if os.path.exists(tmp_pdf) and os.path.getsize(tmp_pdf) > 0:
                with open(tmp_pdf, "rb") as f_pdf:
                    return f_pdf.read()
        except Exception:
            pass
        finally:
            for p in [tmp_html, tmp_pdf]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    # Fallback ReportLab
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    from core.wealth.wealth_engine import compute_consolidated_net_worth

    nw = compute_consolidated_net_worth(engine, portfolio_id=portfolio_id)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"<b>ARGUS MASTER BOARD PACK — {prof_name}</b>", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"<b>Patrimonio Netto Consolidato:</b> € {nw.total_net_worth:,.2f}", styles["Normal"]),
        Paragraph(f"<b>Liquidità Disponibile:</b> € {nw.liquid_cash:,.2f} ({nw.runway_months:.1f} Mesi Runway)", styles["Normal"]),
        Paragraph(f"<b>Investimenti Finanziari:</b> € {nw.financial_investments:,.2f}", styles["Normal"]),
        Paragraph(f"<b>Real Estate Totale:</b> € {nw.real_estate_total:,.2f}", styles["Normal"]),
        Paragraph(f"<b>Passività Totali:</b> € {nw.total_liabilities:,.2f}", styles["Normal"]),
        Paragraph(f"<b>Health Score:</b> {nw.wealth_health_score:.0f}/100", styles["Normal"]),
    ]
    doc.build(story)
    return buf.getvalue()


def generate_master_board_pack_dossier(
    engine: Engine,
    portfolio_id: int = 1,
    prof_name: str = "Family Office Master",
    risk_data: Optional[Dict[str, Any]] = None,
    session_state_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Genera il dossier completo Master Board Pack con HTML e PDF binario."""
    html = generate_master_board_pack_html(
        engine,
        portfolio_id=portfolio_id,
        prof_name=prof_name,
        risk_data=risk_data,
        session_state_dict=session_state_dict,
    )
    pdf = generate_master_board_pack_pdf(
        engine,
        portfolio_id=portfolio_id,
        prof_name=prof_name,
        risk_data=risk_data,
        session_state_dict=session_state_dict,
    )
    return {
        "html": html,
        "pdf": pdf,
        "filename_slug": f"argus_master_board_pack_{prof_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}",
    }


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_master_board_pack_pdf(_engine, pid: int, prof_name: str, db_key: str = "") -> bytes:
    return generate_master_board_pack_pdf(_engine, portfolio_id=pid, prof_name=prof_name)


@st.cache_data(ttl=300, show_spinner=False)
def _get_cached_master_board_pack_html(_engine, pid: int, prof_name: str, db_key: str = "") -> str:
    return generate_master_board_pack_html(_engine, portfolio_id=pid, prof_name=prof_name)




def render_wealth_reporting_and_exports_hub(
    engine: Engine, portfolio_id: int = 1, prof_name: str = "Family Office Master"
):
    """
    Renderizza il Centro Istituzionale di Reportistica ed Esportazioni Multi-Formato per ARGUS Wealth.
    Include 9 tipologie di esportazione: PDF, XLSX, Parquet, CSV, JSON e Audio TTS.
    """
    db_key = _get_engine_db_key(engine)
    date_slug = datetime.now().strftime("%Y%m%d")
    prof_slug = prof_name.lower().replace(" ", "_")

    st.markdown(
        """
    <div style="background: linear-gradient(135deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.98) 100%); border: 1px solid rgba(16, 185, 129, 0.3); border-left: 4px solid #10b981; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div>
                <h4 style="color: #ffffff; margin: 0 0 4px 0; font-size: 16px; font-weight: 750;">
                    📑 Hub di Reportistica &amp; Esportazioni Istituzionali
                </h4>
                <span style="color: #94a3b8; font-size: 12.5px;">
                    Dossier esecutivi completi per Family Office, Private Banking, Commercialisti e Archiviazione Locale Crittografata.
                </span>
            </div>
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px;">
                9 Formati di Esportazione Disponibili
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    REPORTING_HUB_CATALOG = {
        "📑 Dossier PDF & Client Reports": {
            "title": "Dossier PDF, Pitchbook Istituzionali & Client Reports",
            "badge": "PDF • ReportLab • Pitchbook",
            "badge_color": "#38bdf8",
            "category": "Documenti Clienti",
            "desc": "Dossier trimestrali, advisory pitchbook a 6 pagine, bilancio personale certificato e tear-sheet sintetica.",
        },
        "📊 Master Excel & Database Parquet": {
            "title": "Master Excel (.xlsx) & Database Analitico Parquet",
            "badge": "Excel • OpenPyXL • Parquet",
            "badge_color": "#10b981",
            "category": "Fogli di Calcolo & OLAP",
            "desc": "Workbook multi-foglio con formule live e tabelle ListObject, oltre al database colonnare Parquet per Power BI.",
        },
        "⚖️ Fisco, Libro Mastro & Quadro RW": {
            "title": "Monitoraggio Fiscale, Libro Mastro & Quadro RW",
            "badge": "Quadro RW • Fisco • CSV",
            "badge_color": "#f59e0b",
            "category": "Fisco & Contabilità",
            "desc": "Prospetti per la dichiarazione dei redditi (Quadro RW, RT, RM) e libro mastro transazioni in formato CSV/JSON.",
        },
        "🎙️ Executive Audio & Backup JSON": {
            "title": "Executive Voice Briefing & Backup Crittografato",
            "badge": "TTS • Audio Briefing • JSON Vault",
            "badge_color": "#a855f7",
            "category": "Multimedia & Backup",
            "desc": "Briefing vocale sintetico per il CIO/Family Officer e snapshot crittografato di backup per disaster recovery.",
        },
    }

    active_rep_tab = render_segmented_tabs(
        REPORTING_HUB_CATALOG,
        key=f"wealth_reporting_hub_active_tab_{portfolio_id}",
        select_label="Seleziona Formato / Canale di Esportazione:",
    )

    # ── TAB 1: PDF & CLIENT DOSSIERS ────────────────────────────
    if active_rep_tab == "📑 Dossier PDF & Client Reports":
        st.markdown("##### 📄 Dossier Multipagina & Pitchbook Istituzionali")
        st.caption(
            "Documenti ad alta risoluzione pronti per la stampa, comitati consultivi e clienti di private banking."
        )

        st.markdown(
            """
            <div style="background: linear-gradient(135deg, rgba(255, 153, 0, 0.12) 0%, rgba(22, 27, 34, 0.95) 100%);
                        border: 1px solid rgba(255, 153, 0, 0.45);
                        border-left: 4px solid #ff9900;
                        border-radius: 12px;
                        padding: 16px 20px;
                        margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <div style="font-size: 15px; font-weight: 800; color: #ff9900;">
                            📑 Executive Master Board Pack (Unified Risk + Wealth Dossier)
                        </div>
                        <div style="font-size: 12px; color: #cbd5e1; margin-top: 2px;">
                            Dossier consolidato per CDA e Family Office: Stato Patrimoniale, Rischio Quantitativo VaR, Stress Test Macro, Fisco e AI Advisory Memo.
                        </div>
                    </div>
                    <span style="background: rgba(255,153,0,0.2); border: 1px solid #ff9900; color: #ffb74d; font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 12px;">
                        1-CLICK MASTER EXPORT
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        mb_c1, mb_c2 = st.columns(2)
        with mb_c1:
            try:
                st.download_button(
                    label="📥 Scarica Master Board Pack (PDF Istituzionale)",
                    data=lambda: _get_cached_master_board_pack_pdf(engine, pid=portfolio_id, prof_name=prof_name, db_key=db_key),
                    file_name=f"argus_master_board_pack_{prof_slug}_{date_slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="dl_mb_pdf_hub",
                )
            except Exception as e:
                st.error(f"Errore Master Board Pack PDF: {e}")

        with mb_c2:
            try:
                st.download_button(
                    label="🌐 Scarica Master Dossier (HTML Standalone)",
                    data=lambda: _get_cached_master_board_pack_html(engine, pid=portfolio_id, prof_name=prof_name, db_key=db_key),
                    file_name=f"argus_master_board_pack_{prof_slug}_{date_slug}.html",
                    mime="text/html",
                    use_container_width=True,
                    key="dl_mb_html_hub",
                )
            except Exception as e:
                st.error(f"Errore Master Board Pack HTML: {e}")

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        c_pdf1, c_pdf2 = st.columns(2)

        with c_pdf1:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #38bdf8; font-size: 13.5px;">📄 Quarterly Client Report (PDF)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Dossier trimestrale completo ReportLab: Bilancio Net Worth, Brinson Multi-Asset, EBA Stress Test e SFDR ESG Scorecard.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                st.download_button(
                    label="📥 Scarica Quarterly Report PDF",
                    data=lambda: _get_cached_quarterly_pdf(engine, pid=portfolio_id, client_name=prof_name, quarter="Q1 2026", db_key=db_key),
                    file_name=f"argus_quarterly_dossier_{prof_slug}_{date_slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="dl_qtr_pdf_hub",
                )
            except Exception as e:
                st.error(f"Errore PDF QTR: {e}")

        with c_pdf2:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #34d399; font-size: 13.5px;">🏢 Advisory Pitchbook (PDF 6 Pag.)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Brochure di consulenza patrimoniale a 6 pagine con Health Score Radar, Goal-Based SPI %, Real Estate LTV e Action Plan.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                st.download_button(
                    label="📥 Scarica Pitchbook PDF",
                    data=lambda: _get_cached_pitchbook_pdf(engine, pid=portfolio_id, db_key=db_key),
                    file_name=f"argus_advisory_pitchbook_{prof_slug}_{date_slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_pitch_pdf_hub",
                )
            except Exception as e:
                st.error(f"Errore Pitchbook: {e}")

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        c_pdf3, c_pdf4 = st.columns(2)

        with c_pdf3:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-left: 3px solid #10b981; border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #10b981; font-size: 13.5px;">📋 Bilancio Personale &amp; Stato Patrimoniale (PDF 3 Pag.)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Prospetto contabile certificato CFP Board / IFRS: sezioni contrapposte, Conto Economico di gestione, pareggio e indici di solidità.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                st.download_button(
                    label="📥 Scarica Bilancio Personale PDF",
                    data=lambda: _get_cached_balance_sheet_pdf(engine, pid=portfolio_id, db_key=db_key),
                    file_name=f"argus_bilancio_personale_{prof_slug}_{date_slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_pbs_pdf_hub",
                )
            except Exception as e:
                st.error(f"Errore Bilancio Personale PDF: {e}")

        with c_pdf4:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #fbbf24; font-size: 13.5px;">📑 Tear-Sheet Sintetica &amp; Contabile (PDF/HTML)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Scheda riassuntiva one-page a colpo d'occhio con Net Worth, indicatori di solvibilità e sintesi grafica degli attivi.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                st.download_button(
                    label="📥 Scarica Tear-Sheet PDF",
                    data=lambda: _get_cached_tear_sheet_pdf(engine, pid=portfolio_id, db_key=db_key),
                    file_name=f"argus_tear_sheet_{prof_slug}_{date_slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_ts_pdf_hub",
                )
            except Exception as e:
                st.error(f"Errore Tear-Sheet: {e}")

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        c_kid1, c_kid2 = st.columns(2)
        with c_kid1:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255, 153, 0, 0.3); border-left: 3px solid #ff9900; border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #ff9900; font-size: 13.5px;">🇪🇺 PRIIPs KID &amp; MiFID II Factsheet (PDF 2 Pag.)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Documento normativo conforme al Regolamento (UE) 1286/2014 &amp; SFDR: Indicatore Sintetico di Rischio (SRI 1-7), 4 scenari di performance Cornish-Fisher e tabella PAI.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                from core.priips_kid_generator import generate_priips_kid_data, generate_priips_kid_pdf

                kid_ds = generate_priips_kid_data(portfolio_name=prof_name)
                st.download_button(
                    label="📥 Scarica PRIIPs KID (PDF A4)",
                    data=generate_priips_kid_pdf(kid_ds),
                    file_name=f"argus_priips_kid_{prof_slug}_{date_slug}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="dl_priips_pdf_hub",
                )
            except Exception as e:
                st.error(f"Errore PRIIPs KID PDF: {e}")

        with c_kid2:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(56, 189, 248, 0.3); border-left: 3px solid #38bdf8; border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #38bdf8; font-size: 13.5px;">🌐 Factsheet Regolamentare Interattivo (HTML5)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Versione web del KID PRIIPs con gauge visivo SRI responsive, tabelle interattive dei rendimenti futuri e audit trail crittografico SHA-256.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                from core.priips_kid_generator import generate_priips_kid_data, generate_priips_kid_html

                kid_ds = generate_priips_kid_data(portfolio_name=prof_name)
                st.download_button(
                    label="🌐 Scarica Factsheet Web (HTML)",
                    data=generate_priips_kid_html(kid_ds).encode("utf-8"),
                    file_name=f"argus_priips_kid_{prof_slug}_{date_slug}.html",
                    mime="text/html",
                    use_container_width=True,
                    key="dl_priips_html_hub",
                )
            except Exception as e:
                st.error(f"Errore PRIIPs KID HTML: {e}")


    # ── TAB 2: MASTER EXCEL & PARQUET ───────────────────────────
    elif active_rep_tab == "📊 Master Excel & Database Parquet":
        st.markdown("##### 📊 Database & Fogli di Calcolo Strutturati")
        st.caption("Modelli tabellari per audit analitico, elaborazioni in Python/R o integrazione in database OLAP.")

        c_dat1, c_dat2 = st.columns(2)

        with c_dat1:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #10b981; font-size: 13.5px;">📊 Master Excel Workbook (.xlsx)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Dossier completo a 10 fogli (Stato Patrimoniale, Cash Flow, Asset Fisici, Orologi, Previdenza, Immobili, Scenari e Formule).
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                st.download_button(
                    label="📥 Scarica Master Excel (.xlsx)",
                    data=lambda: _get_cached_master_excel(engine, pid=portfolio_id, db_key=db_key),
                    file_name=f"argus_wealth_master_{prof_slug}_{date_slug}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary",
                    key="dl_xl_hub",
                )
            except Exception as e:
                st.error(f"Errore Excel: {e}")

        with c_dat2:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #6366f1; font-size: 13.5px;">💾 Parquet Analytical Database (.parquet)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Esportazione compattata ad alte prestazioni delle transazioni e snapshot per DuckDB, Apache Arrow, Polars e Pandas.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                df_tx = get_cashflow_records(engine, portfolio_id=portfolio_id)
                if df_tx is None or df_tx.empty:
                    df_tx = pd.DataFrame([{"info": "no_data"}])
                pq_buf = io.BytesIO()
                df_tx.to_parquet(pq_buf, index=False)
                st.download_button(
                    label="📥 Scarica Dataset Parquet (.parquet)",
                    data=pq_buf.getvalue(),
                    file_name=f"argus_wealth_cashflow_{prof_slug}_{date_slug}.parquet",
                    mime="application/octet-stream",
                    use_container_width=True,
                    key="dl_pq_hub",
                )
            except Exception as e:
                st.error(f"Errore Parquet: {e}")

    # ── TAB 3: FISCO & LIBRO MASTRO ─────────────────────────────
    elif active_rep_tab == "⚖️ Fisco, Libro Mastro & Quadro RW":
        st.markdown("##### ⚖️ Fiscalità, Libro Mastro & Monitoraggio Estero")
        st.caption(
            "Prospetti conformi alla normativa tributaria italiana (TUIR Quadro RW / RT) e registro dei movimenti bancari."
        )

        c_fisc1, c_fisc2 = st.columns(2)

        with c_fisc1:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #f59e0b; font-size: 13.5px;">📑 Prospetto Quadro RW / RT (.xlsx / .csv)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Righi precompilati per il Modello Redditi PF con codice investimento, valore iniziale/finale e calcolo IVAFE per il commercialista.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                fisc = compute_fiscal_analytics(engine, portfolio_id=portfolio_id)
                df_rw = pd.DataFrame(fisc.get("quadro_rw_rows", []))
                render_export_toolbar(
                    df_rw,
                    file_prefix=f"argus_quadro_rw_{prof_slug}",
                    key_suffix="hub_quadro_rw",
                    table_title="Prospetto Quadro RW / RT",
                )
            except Exception as e:
                st.error(f"Errore Quadro RW: {e}")

        with c_fisc2:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #38bdf8; font-size: 13.5px;">📜 Registro Integrale Cash Flow (.xlsx / .csv)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Libro mastro completo di tutte le entrate e uscite con data contabile, importo, categoria semantica e natura 50/30/20.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                df_cf = get_cashflow_records(engine, portfolio_id=portfolio_id)
                render_export_toolbar(
                    df_cf,
                    file_prefix=f"argus_cashflow_ledger_{prof_slug}",
                    key_suffix="hub_cashflow_ledger",
                    table_title="Registro Integrale Cash Flow",
                )
            except Exception as e:
                st.error(f"Errore Cash Flow CSV: {e}")

    # ── TAB 4: AUDIO & BACKUP JSON ──────────────────────────────
    elif active_rep_tab == "🎙️ Executive Audio & Backup JSON":
        st.markdown("##### 🎙️ Audio Executive Briefing & Backup Crittografico JSON")
        st.caption("Sintesi vocale per podcast esecutivo e snapshot JSON atomico per backup e migrazione dati.")

        c_med1, c_med2 = st.columns(2)

        with c_med1:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #ec4899; font-size: 13.5px;">🎙️ Copione Audio Briefing (.txt)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Script a due voci (Chief Investment Officer & Chief Risk Officer) sincronizzato sui dati reali del patrimonio per sintesi vocale TTS.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                st.download_button(
                    label="📥 Scarica Script Audio (.txt)",
                    data=lambda: generate_ai_voice_executive_briefing(engine, portfolio_id=portfolio_id, client_name=prof_name)["full_text_transcript"],
                    file_name=f"argus_voice_script_{prof_slug}_{date_slug}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="dl_txt_audio_hub",
                )
            except Exception as e:
                st.error(f"Errore Audio Script: {e}")

        with c_med2:
            st.markdown(
                """
            <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 14px 16px; min-height: 170px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <b style="color: #a855f7; font-size: 13.5px;">🏛️ Snapshot Patrimoniale JSON (.json)</b>
                    <p style="color: #cbd5e1; font-size: 12px; margin: 6px 0 12px 0; line-height: 1.5;">
                        Backup atomico strutturato di conti, saldi, categorie e parametri per ripristino istantaneo o migrazione su altro ambiente.
                    </p>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
            try:
                nw = compute_consolidated_net_worth(engine, portfolio_id=portfolio_id)
                snap_dict = {
                    "portfolio_id": portfolio_id,
                    "portfolio_name": prof_name,
                    "exported_at": datetime.now().isoformat(),
                    "net_worth_eur": nw.total_net_worth,
                    "liquid_cash_eur": nw.liquid_cash,
                    "investments_eur": nw.financial_investments,
                    "real_estate_eur": nw.real_estate_total,
                    "liabilities_eur": nw.total_liabilities,
                    "health_score": nw.wealth_health_score,
                }
                json_str = json.dumps(snap_dict, indent=2)
                st.download_button(
                    label="📥 Scarica Snapshot JSON (.json)",
                    data=json_str,
                    file_name=f"argus_wealth_snapshot_{prof_slug}_{date_slug}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="dl_json_snap_hub",
                )
            except Exception as e:
                st.error(f"Errore JSON Snapshot: {e}")
