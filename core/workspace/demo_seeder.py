"""ARGUS — Unified Workspace Demo Seeder & Archetype Engine.

Canonical File: core/workspace/demo_seeder.py
Unifies synthetic scenario seeding (Family Office, High Net Worth, Quant Desk)
with pedagogical multi-asset archetypes (All-Weather, Permanent Portfolio, Golden Butterfly).
"""
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

    df_returns = pd.DataFrame(
        {"VWCE.DE": ret_vwce, "AAPL": ret_aapl, "ASML.AS": ret_asml, "BTP_10Y": ret_btp}, index=dates
    )

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
    positions_df = pd.DataFrame(
        [
            {
                "ticker": "VWCE.DE",
                "asset_class": "ETF",
                "gics_sector": "Global Equity",
                "country": "DE",
                "currency": "EUR",
                "qty_net": 500.0,
                "avg_cost": 105.0,
                "last_price": 112.50,
                "current_value": 56250.0,
                "cost_basis": 52500.0,
                "unrealized_pnl": 3750.0,
                "unrealized_pnl_pct": 7.14,
                "realized_pnl": 0.0,
                "dividends_total": 0.0,
                "weight_pct": 26.17,
                "beta": 0.98,
                "days_to_liquidate": 0.2,
            },
            {
                "ticker": "AAPL",
                "asset_class": "Equity",
                "gics_sector": "Information Technology",
                "country": "US",
                "currency": "USD",
                "qty_net": 150.0,
                "avg_cost": 160.0,
                "last_price": 170.0,
                "current_value": 25500.0,
                "cost_basis": 24000.0,
                "unrealized_pnl": 1500.0,
                "unrealized_pnl_pct": 6.25,
                "realized_pnl": 450.0,
                "dividends_total": 180.0,
                "weight_pct": 11.86,
                "beta": 1.15,
                "days_to_liquidate": 0.1,
            },
            {
                "ticker": "ASML.AS",
                "asset_class": "Equity",
                "gics_sector": "Information Technology",
                "country": "NL",
                "currency": "EUR",
                "qty_net": 40.0,
                "avg_cost": 750.0,
                "last_price": 850.0,
                "current_value": 34000.0,
                "cost_basis": 30000.0,
                "unrealized_pnl": 4000.0,
                "unrealized_pnl_pct": 13.33,
                "realized_pnl": 0.0,
                "dividends_total": 240.0,
                "weight_pct": 15.82,
                "beta": 1.25,
                "days_to_liquidate": 0.3,
            },
            {
                "ticker": "BTP_10Y",
                "asset_class": "Fixed Income",
                "gics_sector": "Sovereign Debt",
                "country": "IT",
                "currency": "EUR",
                "qty_net": 1000.0,
                "avg_cost": 100.0,
                "last_price": 99.20,
                "current_value": 99200.0,
                "cost_basis": 100000.0,
                "unrealized_pnl": -800.0,
                "unrealized_pnl_pct": -0.80,
                "realized_pnl": 0.0,
                "dividends_total": 3850.0,
                "weight_pct": 46.15,
                "beta": 0.10,
                "days_to_liquidate": 0.5,
            },
        ]
    )

    # ── 4. STRESS TESTS SU CRISI STORICHE ───────────────────────
    stress_tests = {
        "Dot-Com Crash (2000-2002)": {"portfolio_loss_pct": -34.5, "portfolio_loss_eur": -74157.0},
        "Lehman Brothers (2008)": {"portfolio_loss_pct": -28.2, "portfolio_loss_eur": -60615.0},
        "US Downgrade (2011)": {"portfolio_loss_pct": -11.4, "portfolio_loss_eur": -24504.0},
        "COVID-19 Crash (2020)": {"portfolio_loss_pct": -21.6, "portfolio_loss_eur": -46429.0},
        "Tech & Rate Shock (2022)": {"portfolio_loss_pct": -16.8, "portfolio_loss_eur": -36111.0},
    }

    # ── 5. TOTAL WEALTH SNAPSHOT (5 PILASTRI) ────────────────────
    wealth_snapshot = {
        "liquid_cash": 95000.0,  # Cassa €45k + Deposito €50k
        "financial_investments": 214950.0,  # Valore titoli
        "physical_assets": 674500.0,  # Immobile €650k + Rolex €24.5k
        "pension_total": 38000.0,  # Fondo pensione
        "liabilities_total": 220000.0,  # Mutuo residuo
        "total_assets": 1022450.0,
        "total_net_worth": 802450.0,
        "wealth_health_score": 91.0,
        "debt_to_asset_pct": 21.52,
        "emergency_fund_months": 18.5,
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
        "base_currency": "EUR",
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
    curr_user = "user"
    user_id = None
    try:
        import streamlit as st
        ss = getattr(st, "session_state", None)
        if ss is not None:
            user_obj = ss.get("user")
            if user_obj:
                if isinstance(user_obj, dict):
                    curr_user = user_obj.get("username") or user_obj.get("email") or "user"
                    user_id = user_obj.get("id")
                else:
                    curr_user = getattr(user_obj, "username", None) or getattr(user_obj, "email", None) or "user"
                    user_id = getattr(user_obj, "id", None)
            if not user_id:
                user_id = ss.get("user_id")
            if not curr_user:
                curr_user = ss.get("argus_auth_user", "user")
    except Exception:
        pass

    try:
        from core.bitemporal_engine import BitemporalLedgerEngine

        b_engine = BitemporalLedgerEngine()
        b_engine.seed_demonstration_scenario(portfolio_id=target_portfolio_name)
    except Exception:
        pass

    try:
        from core.fetcher import get_engine
        from core.wealth.wealth_db import (
            create_wealth_portfolio,
            get_wealth_categories,
            init_wealth_db,
            insert_cashflow_tx,
            save_pension_plan,
            save_physical_asset,
            save_wealth_account,
        )

        # Isolamento Air-Gapped: il seeding avviene esclusivamente sul database sandbox demo_sandbox.db
        demo_db_path = "data/demo_sandbox.db"
        engine = get_engine(offline=True, sqlite_path=demo_db_path)
        init_wealth_db(engine)

        pid = create_wealth_portfolio(
            engine,
            name=target_portfolio_name,
            description="Demo Family Office Multi-Asset (5 Pilastri)",
            owner="demo_sandbox_user",
            base_currency="EUR",
        )

        try:
            import streamlit as st

            ss = getattr(st, "session_state", None)
            if ss is not None:
                ss["is_sandbox"] = True
                ss["is_demo"] = True
                ss["demo_sqlite_path"] = demo_db_path
        except Exception:
            pass

        try:
            import streamlit as st

            if hasattr(st, "session_state"):
                st.session_state["wealth_active_portfolio_id"] = pid
                st.session_state["active_portfolio_id"] = pid
                st.session_state["active_portfolio_data"] = {
                    "portfolio": {"portfolio_id": pid, "name": target_portfolio_name, "owner": curr_user},
                    "positions": positions_df,
                    "equity": float(positions_df["current_value"].sum()) if not positions_df.empty else 214950.0,
                    "results": results_bundle,
                }
                st.session_state["session_cleared"] = False
        except Exception:
            pass

        # Check existing accounts for this profile to prevent duplication
        with engine.connect() as conn:
            from sqlalchemy import text as sqlt

            res_cnt = conn.execute(
                sqlt("SELECT COUNT(*) FROM wealth_accounts WHERE portfolio_id = :pid"), {"pid": pid}
            ).scalar()

        if not res_cnt:
            acc_chk_id = save_wealth_account(
                engine,
                {
                    "name": "Conto Corrente Principale",
                    "institution": "Intesa Sanpaolo",
                    "account_type": "checking",
                    "currency": "EUR",
                    "balance": 45000.0,
                    "portfolio_id": pid,
                    "notes": "Liquidità operativa di cassa",
                },
            )
            save_wealth_account(
                engine,
                {
                    "name": "Conto Deposito Rendimento",
                    "institution": "Illimity Bank",
                    "account_type": "savings",
                    "currency": "EUR",
                    "balance": 50000.0,
                    "portfolio_id": pid,
                    "notes": "Fondo emergenza e remunerazione liquidità",
                },
            )
            save_wealth_account(
                engine,
                {
                    "name": "Mutuo Ipotecario Casa Milano",
                    "institution": "Banco BPM",
                    "account_type": "loan",
                    "currency": "EUR",
                    "balance": -220000.0,
                    "portfolio_id": pid,
                    "notes": "Debito ipotecario residuo prima casa",
                },
            )

            # Physical Assets (Immobile Milano €650k, Rolex Daytona €24.5k)
            save_physical_asset(
                engine,
                {
                    "name": "Immobile Residenziale Milano Centro",
                    "asset_category": "real_estate",
                    "brand_or_location": "Milano, Porta Nuova",
                    "model_or_specs": "Quadrilocale 140 mq con box",
                    "purchase_price": 580000.0,
                    "current_market_value": 650000.0,
                    "portfolio_id": pid,
                    "notes": "Abitazione principale",
                },
            )
            save_physical_asset(
                engine,
                {
                    "name": "Rolex Daytona Cosmograph 116500LN",
                    "asset_category": "luxury_watches",
                    "brand_or_location": "Rolex",
                    "model_or_specs": "Acciaio Oyster, Quadrante Bianco, Ghiera Cerachrom",
                    "reference_number": "116500LN",
                    "purchase_price": 18500.0,
                    "current_market_value": 24500.0,
                    "portfolio_id": pid,
                    "notes": "Collezione personale con garanzia e scatola originale",
                },
            )

            # Pension Plan (Fondo Cometa €38k)
            save_pension_plan(
                engine,
                {
                    "plan_name": "Fondo Pensione Cometa / Fonchim",
                    "provider": "Fondo Pensione Negoziale",
                    "plan_type": "fondo_pensione_aperto",
                    "accumulated_value": 38000.0,
                    "monthly_employee_contrib": 250.0,
                    "monthly_employer_contrib": 250.0,
                    "tax_deductible_annual": 5164.57,
                    "portfolio_id": pid,
                    "notes": "Comparto Crescita / Azionario Bilanciato",
                },
            )

            # Sample cash flows
            today_d = datetime.now().date()
            cats_df = get_wealth_categories(engine)
            inc_cat = 1
            exp_cat = 6
            if cats_df is not None and not cats_df.empty:
                inc_matches = cats_df[cats_df["flow_type"] == "income"]
                if not inc_matches.empty:
                    inc_cat = int(inc_matches.iloc[0]["category_id"])
                exp_matches = cats_df[cats_df["flow_type"] == "expense"]
                if not exp_matches.empty:
                    exp_cat = int(exp_matches.iloc[0]["category_id"])

            if acc_chk_id:
                try:
                    insert_cashflow_tx(
                        engine,
                        {
                            "account_id": acc_chk_id,
                            "category_id": inc_cat,
                            "tx_date": today_d.strftime("%Y-%m-%d"),
                            "amount": 6500.0,
                            "direction": "inflow",
                            "merchant": "Datore di Lavoro SpA",
                            "notes": "Stipendio Mensile Dirigente",
                            "portfolio_id": pid,
                        },
                    )
                    insert_cashflow_tx(
                        engine,
                        {
                            "account_id": acc_chk_id,
                            "category_id": exp_cat,
                            "tx_date": today_d.strftime("%Y-%m-%d"),
                            "amount": 1450.0,
                            "direction": "outflow",
                            "merchant": "Banco BPM",
                            "notes": "Rata Mensile Mutuo",
                            "portfolio_id": pid,
                        },
                    )
                    with engine.begin() as wconn:
                        wconn.execute(
                            sqlt("UPDATE wealth_accounts SET balance = 45000.0 WHERE account_id = :aid"),
                            {"aid": acc_chk_id},
                        )
                except Exception:
                    pass
    except Exception:
        pass

    return results_bundle


# ==============================================================================
# UNIFIED ARCHETYPE MANAGER CAPABILITIES (Relocated from archetype_manager.py)
# ==============================================================================
"""
core/archetype_manager.py
ARGUS Institutional — Unified Cross-Module Archetype & Scenario Manager

Permette il caricamento e la sincronizzazione 1-click di scenari didattici e archetipi
realistici simultaneamente sia per il modulo Risk Analytics che per il modulo Wealth Management.
"""

from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st


def execute_unified_archetype_load(
    arch_code: str, auto_run: bool = False, source_module: str = "risk"
) -> Dict[str, Any]:
    """
    Esegue la simulazione quantitativa realistica e inietta l'archetipo sia su SQLite
    che su MySQL (se connesso), allineando simultaneamente lo stato di Risk Analytics
    e Wealth Management.
    """
    from core.fetcher import get_engine
    from core.models import Base
    from core.wealth.wealth_db import init_wealth_db, sync_wealth_tables_between_engines
    from scripts.generate_realistic_portfolio import PortfolioSimulationEngine, populate_argus_database

    sim_eng = PortfolioSimulationEngine(offline=True, seed=42)
    res_arch = sim_eng.simulate(arch_code, years=3)

    # 1. Popolamento database SQLite isolato in sandbox (Air-Gapped: non inquina argus_local.db)
    demo_db_path = "data/demo_sandbox.db"
    db_res = populate_argus_database(res_arch, sqlite_path=demo_db_path)
    risk_pid = db_res["risk_portfolio_id"]
    wealth_pid = db_res["wealth_profile_id"]

    # 2. Flag di isolamento sandbox per prevenire sync cloud
    st.session_state["is_sandbox"] = True
    st.session_state["is_demo"] = True
    st.session_state["demo_sqlite_path"] = demo_db_path

    # 3. Aggiorna Session State per Risk Analytics
    st.session_state["df_raw_injected"] = res_arch.trading_transactions_df
    st.session_state["portfolio_name"] = f"Archetipo: {res_arch.archetype.name}"
    st.session_state["portfolio_id"] = risk_pid
    st.session_state["active_archetype_code"] = arch_code
    st.session_state["active_archetype_name"] = res_arch.archetype.name
    st.session_state["active_archetype_tx_count"] = len(res_arch.trading_transactions_df)
    st.session_state["active_archetype_db_ids"] = db_res
    st.session_state["keep_archetype_expander_open"] = True
    st.session_state["archetype_just_injected"] = True

    # 4. Aggiorna Session State per Wealth Management
    st.session_state["wealth_active_portfolio_id"] = wealth_pid
    st.session_state["wealth_active_profile_name"] = f"Patrimonio {res_arch.archetype.name}"
    st.session_state.pop("wealth_profile_selector_widget", None)
    st.session_state.pop("cf_profile_selector_widget", None)
    st.session_state.pop("wealth_active_snapshot", None)

    # 5. Pulisce cache pipeline precedenti
    st.session_state.pop("session_cleared", None)
    st.session_state.pop("pipeline_done", None)
    st.session_state.pop("results", None)
    st.session_state.pop("fetch_report", None)

    if auto_run:
        st.session_state["auto_run_pipeline_requested"] = True

    # 6. Invalidazione cache Streamlit
    try:
        st.cache_data.clear()
    except Exception:
        pass

    return db_res


def clear_unified_archetype():
    """
    Rimuove l'archetipo attivo e ripulisce le chiavi di sessione per entrambi i moduli.
    """
    keys_to_clear = [
        "df_raw_injected",
        "active_archetype_code",
        "active_archetype_name",
        "active_archetype_tx_count",
        "active_archetype_db_ids",
        "keep_archetype_expander_open",
        "archetype_just_injected",
        "auto_run_pipeline_requested",
        "pipeline_done",
        "results",
        "fetch_report",
        "wealth_active_snapshot",
        "wealth_profile_selector_widget",
        "cf_profile_selector_widget",
    ]
    for k in keys_to_clear:
        st.session_state.pop(k, None)
    st.session_state["portfolio_name"] = ""
    st.session_state["wealth_active_portfolio_id"] = None

    try:
        st.cache_data.clear()
    except Exception:
        pass

    st.rerun()


def render_unified_archetype_hud(current_module: str = "risk"):
    """
    Renderizza il banner HUD istituzionale quando uno scenario didattico è attivo in sessione,
    offrendo navigazione rapida 1-click tra il modulo Risk e il modulo Wealth.
    """
    active_code = st.session_state.get("active_archetype_code")
    if not active_code:
        return

    active_name = st.session_state.get("active_archetype_name", "Scenario")
    tx_count = st.session_state.get("active_archetype_tx_count", 0)
    db_ids = st.session_state.get("active_archetype_db_ids", {})
    r_id = db_ids.get("risk_portfolio_id", st.session_state.get("portfolio_id", 1))
    w_id = db_ids.get("wealth_profile_id", st.session_state.get("wealth_active_portfolio_id"))

    st.markdown(
        f"""
    <div style="background: rgba(46, 160, 67, 0.14); border: 1px solid rgba(46, 160, 67, 0.4); border-left: 4px solid #2ea043; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
                <div style="font-weight: 700; color: #3fb950; font-size: 14.5px;">
                    ✅ Scenario Didattico Attivo: <b>{active_name}</b> (Sincronizzato Cross-Modulo)
                </div>
                <div style="color: #c9d1d9; font-size: 12px; margin-top: 3px;">
                    • <b>{tx_count} transazioni</b> simulate | 📊 Trading Portfolio: <code>#{r_id}</code> • 🏛️ Wealth Profile: <code>#{w_id}</code><br>
                    • Portafoglio quantitativo e patrimonio multi-asset caricati contemporaneamente su <b>Risk Analytics</b> e <b>Wealth Management</b>.
                </div>
            </div>
            <span class="argus-command-pill" style="border-color: rgba(46,160,67,0.5); color: #3fb950; font-weight:700;">UNIFIED ECOSYSTEM ATTIVO</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if current_module == "risk":
        col_act1, col_act2, col_act3 = st.columns([2.2, 1.8, 1.2])
        with col_act1:
            if st.button(
                "🚀 Avvia Subito Analisi Quantitativa ARGUS",
                key="btn_hud_run_risk",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["auto_run_pipeline_requested"] = True
                st.rerun()
        with col_act2:
            if st.button(
                "🏛️ Esplora Patrimonio & Net Worth",
                key="btn_hud_goto_wealth",
                type="secondary",
                use_container_width=True,
            ):
                st.switch_page("pages/13_🏛️_Patrimonio_e_NetWorth.py")
        with col_act3:
            if st.button("🗑️ Rimuovi Scenario", key="btn_hud_clear_risk", type="secondary", use_container_width=True):
                clear_unified_archetype()
    else:
        col_act1, col_act2, col_act3 = st.columns([2.2, 1.8, 1.2])
        with col_act1:
            if st.button(
                "🏛️ Esplora Patrimonio & Net Worth", key="btn_hud_w_goto_nw", type="primary", use_container_width=True
            ):
                st.switch_page("pages/13_🏛️_Patrimonio_e_NetWorth.py")
        with col_act2:
            if st.button(
                "📊 Vai ad Analisi Rischio & Portafoglio",
                key="btn_hud_w_goto_risk",
                type="secondary",
                use_container_width=True,
            ):
                st.switch_page("0_Control_Room.py")
        with col_act3:
            if st.button("🗑️ Rimuovi Scenario", key="btn_hud_clear_wealth", type="secondary", use_container_width=True):
                clear_unified_archetype()

    st.markdown(
        "<hr style='margin: 12px 0; border: none; border-top: 1px solid rgba(255,255,255,0.08);'>",
        unsafe_allow_html=True,
    )

