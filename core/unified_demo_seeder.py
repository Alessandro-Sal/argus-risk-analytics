"""
ARGUS — Quantitative Risk & Wealth Intelligence Platform
Core Module: Unified Demo Portfolio Seeder (5 Pillars)
Seeds an institutional, multi-asset demonstration scenario spanning both
Risk Analytics and Total Wealth Management in a single atomic operation.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from core.risk_engine import compute_risk_metrics
from core.workspace_context import WorkspaceContext


def seed_unified_demo_scenario(target_portfolio_name: str = "DEMO_FAMILY_OFFICE") -> Dict[str, Any]:
    """
    Inizializza e inietta uno scenario dimostrativo multi-asset a 5 pilastri:
    1. Liquidità & Conti Deposito: €95.000
    2. Titoli Azionari & ETF: VWCE.DE (€56.250), AAPL (€25.500), ASML.AS (€34.000)
    3. Obbligazioni Governative: BTP 10Y Italia (€99.200)
    4. Real Estate & Mutuo: Immobile Milano Centro (€650.000) e Mutuo passivo (€220.000)
    5. Alternative Assets & Pensione: Rolex Daytona (€24.500) e Fondo Pensione (€38.000)

    Totale Attivo: €1.022.450 | Totale Passivo: €220.000 | Patrimonio Netto: €802.450
    """
    np.random.seed(42)

    # ── 1. GENERAZIONE DATE E RENDIMENTI SINTETICI REALISTICI ───
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=252, freq="B")

    # Rendimenti simulati con correlazioni coerenti
    # Benchmark SPY/World: mu=8%, vol=15%
    ret_bm = np.random.normal(0.08 / 252.0, 0.15 / np.sqrt(252.0), 252)
    # VWCE (World ETF): Beta ~ 0.98, vol=15.5%
    ret_vwce = 0.98 * ret_bm + np.random.normal(0.0001, 0.05 / np.sqrt(252.0), 252)
    # AAPL (Tech Mega-cap): Beta ~ 1.15, vol=24%
    ret_aapl = 1.15 * ret_bm + np.random.normal(0.0004, 0.18 / np.sqrt(252.0), 252)
    # ASML (Semiconductor Growth): Beta ~ 1.25, vol=28%
    ret_asml = 1.25 * ret_bm + np.random.normal(0.0005, 0.22 / np.sqrt(252.0), 252)
    # BTP 10Y (Gov Bond): Beta ~ 0.10 vs equity, vol=7.5%
    ret_btp = 0.10 * ret_bm + np.random.normal(0.038 / 252.0, 0.075 / np.sqrt(252.0), 252)

    df_returns = pd.DataFrame({
        "VWCE.DE": ret_vwce,
        "AAPL": ret_aapl,
        "ASML.AS": ret_asml,
        "BTP_10Y": ret_btp
    }, index=dates)

    sr_bm = pd.Series(ret_bm, index=dates, name="SPY")

    # Pesi di portafoglio mobiliare:
    # VWCE: 56.250 / 214.950 = 26.17%
    # AAPL: 25.500 / 214.950 = 11.86%
    # ASML: 34.000 / 214.950 = 15.82%
    # BTP:  99.200 / 214.950 = 46.15%
    weights = np.array([56250.0, 25500.0, 34000.0, 99200.0]) / 214950.0
    port_ret = df_returns.dot(weights)
    port_ret.name = "Portfolio"

    # ── 2. CALCOLO METRICHE QUANTITATIVE RISK ENGINE ────────────
    risk_metrics = compute_risk_metrics(port_ret, risk_free_rate=0.03)
    risk_metrics["market_risk"]["beta"] = float(np.cov(port_ret, sr_bm)[0, 1] / np.var(sr_bm))
    risk_metrics["market_risk"]["tracking_error_pct"] = float((port_ret - sr_bm).std() * np.sqrt(252.0) * 100.0)

    # ── 3. POSIZIONI MOBILIARI DETTAGLIATE ───────────────────────
    positions_df = pd.DataFrame([
        {
            "ticker": "VWCE.DE", "asset_class": "ETF", "gics_sector": "Global Equity",
            "country": "DE", "currency": "EUR", "qty_net": 500.0, "avg_cost": 105.0,
            "last_price": 112.50, "current_value": 56250.0, "cost_basis": 52500.0,
            "unrealized_pnl": 3750.0, "unrealized_pnl_pct": 7.14, "realized_pnl": 0.0,
            "dividends_total": 0.0, "weight_pct": 26.17, "beta": 0.98, "days_to_liquidate": 0.2
        },
        {
            "ticker": "AAPL", "asset_class": "Equity", "gics_sector": "Information Technology",
            "country": "US", "currency": "USD", "qty_net": 150.0, "avg_cost": 160.0,
            "last_price": 170.0, "current_value": 25500.0, "cost_basis": 24000.0,
            "unrealized_pnl": 1500.0, "unrealized_pnl_pct": 6.25, "realized_pnl": 450.0,
            "dividends_total": 180.0, "weight_pct": 11.86, "beta": 1.15, "days_to_liquidate": 0.1
        },
        {
            "ticker": "ASML.AS", "asset_class": "Equity", "gics_sector": "Information Technology",
            "country": "NL", "currency": "EUR", "qty_net": 40.0, "avg_cost": 750.0,
            "last_price": 850.0, "current_value": 34000.0, "cost_basis": 30000.0,
            "unrealized_pnl": 4000.0, "unrealized_pnl_pct": 13.33, "realized_pnl": 0.0,
            "dividends_total": 240.0, "weight_pct": 15.82, "beta": 1.25, "days_to_liquidate": 0.3
        },
        {
            "ticker": "BTP_10Y", "asset_class": "Fixed Income", "gics_sector": "Sovereign Debt",
            "country": "IT", "currency": "EUR", "qty_net": 1000.0, "avg_cost": 100.0,
            "last_price": 99.20, "current_value": 99200.0, "cost_basis": 100000.0,
            "unrealized_pnl": -800.0, "unrealized_pnl_pct": -0.80, "realized_pnl": 0.0,
            "dividends_total": 3850.0, "weight_pct": 46.15, "beta": 0.10, "days_to_liquidate": 0.5
        }
    ])

    # ── 4. STRESS TESTS SU CRISI STORICHE ───────────────────────
    stress_tests = {
        "Dot-Com Crash (2000-2002)": {"portfolio_loss_pct": -34.5, "portfolio_loss_eur": -74157.0},
        "Lehman Brothers (2008)": {"portfolio_loss_pct": -28.2, "portfolio_loss_eur": -60615.0},
        "US Downgrade (2011)": {"portfolio_loss_pct": -11.4, "portfolio_loss_eur": -24504.0},
        "COVID-19 Crash (2020)": {"portfolio_loss_pct": -21.6, "portfolio_loss_eur": -46429.0},
        "Tech & Rate Shock (2022)": {"portfolio_loss_pct": -16.8, "portfolio_loss_eur": -36111.0}
    }

    # ── 5. TOTAL WEALTH SNAPSHOT (5 PILASTRI) ────────────────────
    wealth_snapshot = {
        "liquid_cash": 95000.0,               # Cassa €45k + Deposito €50k
        "financial_investments": 214950.0,    # Valore titoli
        "physical_assets": 674500.0,          # Immobile €650k + Rolex €24.5k
        "pension_total": 38000.0,             # Fondo pensione
        "liabilities_total": 220000.0,        # Mutuo residuo
        "total_assets": 1022450.0,
        "total_net_worth": 802450.0,
        "wealth_health_score": 91.0,
        "debt_to_asset_pct": 21.52,
        "emergency_fund_months": 18.5
    }

    # ── 6. ASSEMBLAGGIO BUNDLE RISCHIO COMPLETO ─────────────────
    results_bundle = {
        "portfolio_id": 999001,
        "portfolio_name": target_portfolio_name,
        "computed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_sandbox": True,
        "sandbox_name": "Demo Family Office (5 Pilastri)",
        "portfolio_return": port_ret,
        "benchmark_return": sr_bm,
        "returns": df_returns,
        "positions": positions_df,
        "metrics": risk_metrics,
        "stress_tests": stress_tests,
        "wealth_snapshot": wealth_snapshot,
        "base_currency": "EUR"
    }

    # ── 7. SINCRONIZZAZIONE STATO SESSIONE & WORKSPACE CONTEXT ──
    ctx = WorkspaceContext.get_current()
    ctx.risk.portfolio_id = 999001
    ctx.risk.portfolio_name = target_portfolio_name
    ctx.risk.run_id = f"RUN_DEMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    ctx.risk.base_currency = "EUR"
    ctx.risk.pipeline_done = True
    ctx.risk.is_live_active = True
    ctx.risk.is_sandbox = True
    ctx.risk.results = results_bundle
    ctx.wealth.net_worth_cached = wealth_snapshot
    ctx.wealth.last_consolidated_at = datetime.now()

    try:
        import streamlit as st
        if hasattr(st, "session_state"):
            st.session_state["results"] = results_bundle
            st.session_state["pipeline_done"] = True
            st.session_state["portfolio_name"] = target_portfolio_name
            st.session_state["run_id"] = ctx.risk.run_id
            st.session_state["base_currency"] = "EUR"
            st.session_state["selected_bitemp_port"] = target_portfolio_name
            st.session_state["workspace_context"] = ctx
    except Exception:
        pass

    # ── 8. SEED OPZIONALE BITEMPORAL & WEALTH DB ─────────────────
    try:
        from core.bitemporal_engine import BitemporalLedgerEngine
        b_engine = BitemporalLedgerEngine()
        b_engine.seed_demonstration_scenario(portfolio_id=target_portfolio_name)
    except Exception:
        pass

    return results_bundle
