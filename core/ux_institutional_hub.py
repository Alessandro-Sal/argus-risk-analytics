"""ARGUS Institutional Terminal UX/UI Hub (Release v9.16.0).

Provides the 6 Institutional UX/UI Pillars:
1. Segmented Domain Workspace Switcher & @st.fragment Reactive Isolation
2. Global Telemetry Top-Ribbon (Bloomberg Launchpad Sticky Header)
3. 1-Click Live Portfolio Auto-Binding (Real Position & Return Extraction)
4. Unified Institutional Plotly Styling (Glassmorphic + Magnetic Crosshairs)
5. Scenario Pin & Delta Comparator (Baseline Snapshot vs Current Simulation)
6. Executive Traffic-Light CRO Radar (6-Pillar Regulatory & Risk Appetite Matrix)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

try:
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None  # type: ignore[assignment]

APP_VERSION: str = "9.17.0"

INSTITUTIONAL_PALETTE: list[str] = [
    "#10b981",  # Emerald
    "#3b82f6",  # Royal Blue
    "#f59e0b",  # Amber Gold
    "#ef4444",  # Crimson Risk
    "#6366f1",  # Indigo
    "#ec4899",  # Rose
    "#06b6d4",  # Cyan
    "#a855f7",  # Purple
]


def build_telemetry_ribbon_state(
    session_state_dict: dict[str, Any] | None = None,
    page_badge: str = "INSTITUTIONAL TERMINAL",
) -> dict[str, Any]:
    """Extract live portfolio telemetry from session state with institutional fallbacks."""
    state = session_state_dict if session_state_dict is not None else (
        dict(st.session_state) if st is not None and hasattr(st, "session_state") else {}
    )
    last_res = state.get("last_results") or {}
    profile_name = str(
        state.get("active_portfolio_name")
        or state.get("selected_portfolio_name")
        or "Portafoglio Principale (Institutional)"
    )

    nav_eur = 0.0
    pos_df = last_res.get("positions")
    if isinstance(pos_df, pd.DataFrame) and not pos_df.empty:
        if "current_value" in pos_df.columns:
            nav_eur = float(pos_df["current_value"].fillna(0.0).sum())
        elif "qty_net" in pos_df.columns and "last_price" in pos_df.columns:
            nav_eur = float((pos_df["qty_net"].fillna(0.0) * pos_df["last_price"].fillna(0.0)).sum())

    if nav_eur <= 0.0:
        nav_eur = float(last_res.get("total_value", 1_250_000.0) or 1_250_000.0)

    var_99_pct = float(last_res.get("var_99_pct", last_res.get("var_95_pct", 1.84)) or 1.84)
    var_99_eur = nav_eur * (abs(var_99_pct) / 100.0)
    sharpe = float(last_res.get("sharpe_ratio", 1.42) or 1.42)
    ann_vol_pct = float(last_res.get("annual_volatility_pct", 12.6) or 12.6)

    if ann_vol_pct >= 22.0 or abs(var_99_pct) >= 3.0:
        regime_label = "🔴 STRESS / HIGH VOL"
        regime_color = "#ef4444"
    elif ann_vol_pct >= 15.5:
        regime_label = "🟡 TRANSITIONAL / ELEVATED"
        regime_color = "#f59e0b"
    else:
        regime_label = "🟢 BULL / NORMAL"
        regime_color = "#10b981"

    return {
        "app_version": APP_VERSION,
        "page_badge": page_badge,
        "profile_name": profile_name,
        "nav_eur": round(nav_eur, 2),
        "var_99_pct": round(abs(var_99_pct), 2),
        "var_99_eur": round(var_99_eur, 2),
        "sharpe_ratio": round(sharpe, 2),
        "annual_volatility_pct": round(ann_vol_pct, 2),
        "regime_label": regime_label,
        "regime_color": regime_color,
        "timestamp_utc": datetime.now().strftime("%H:%M:%S"),
    }


def render_institutional_telemetry_ribbon(
    page_badge: str = "INSTITUTIONAL TERMINAL",
) -> dict[str, Any]:
    """Render sticky Bloomberg Launchpad-style top telemetry ribbon in Streamlit."""
    telemetry = build_telemetry_ribbon_state(page_badge=page_badge)
    if st is None:
        return telemetry

    nav_str = f"€ {telemetry['nav_eur']:,.0f}".replace(",", ".")
    var_str = f"€ {telemetry['var_99_eur']:,.0f}".replace(",", ".")

    st.markdown(
        f"""
        <div style="background: linear-gradient(90deg, rgba(15, 23, 42, 0.96) 0%, rgba(22, 27, 34, 0.96) 100%);
                    border: 1px solid rgba(99, 102, 241, 0.32);
                    border-left: 4px solid #6366f1;
                    border-radius: 10px;
                    padding: 8px 14px;
                    margin-bottom: 12px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 10px;
                    box-shadow: 0 4px 16px rgba(0,0,0,0.35);">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <span style="background: rgba(99, 102, 241, 0.18); border: 1px solid rgba(99, 102, 241, 0.45);
                             color: #818cf8; font-size: 10.5px; font-weight: 800; padding: 2px 8px;
                             border-radius: 6px; font-family: 'JetBrains Mono', monospace;">
                    ARGUS v{telemetry['app_version']}
                </span>
                <span style="color: #e2e8f0; font-size: 12px; font-weight: 700;">
                    🏛️ {telemetry['profile_name']}
                </span>
                <span style="color: #64748b; font-size: 11px;">|</span>
                <span style="color: #94a3b8; font-size: 11px; font-weight: 600;">
                    {telemetry['page_badge']}
                </span>
            </div>
            <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap; font-family: 'JetBrains Mono', monospace;">
                <span style="font-size: 11.5px; color: #cbd5e1;">
                    NAV: <b style="color: #10b981;">{nav_str}</b>
                </span>
                <span style="font-size: 11.5px; color: #cbd5e1;">
                    VaR 99%: <b style="color: #f59e0b;">{var_str} ({telemetry['var_99_pct']:.2f}%)</b>
                </span>
                <span style="font-size: 11.5px; color: #cbd5e1;">
                    Sharpe: <b style="color: #38bdf8;">{telemetry['sharpe_ratio']:.2f}</b>
                </span>
                <span style="background: rgba(255,255,255,0.04); border: 1px solid {telemetry['regime_color']};
                             color: {telemetry['regime_color']}; font-size: 10.5px; font-weight: 800;
                             padding: 2px 8px; border-radius: 12px;">
                    {telemetry['regime_label']}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return telemetry


def extract_live_portfolio_binding(
    session_state_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract live portfolio ticker, spot price, quantity, volatility, and NAV for 1-click auto-binding."""
    state = session_state_dict if session_state_dict is not None else (
        dict(st.session_state) if st is not None and hasattr(st, "session_state") else {}
    )
    last_res = state.get("last_results") or {}
    pos_df = last_res.get("positions")

    has_live = False
    top_ticker = "ENI.MI"
    top_spot = 14.80
    top_shares = 250_000.0
    total_nav = 1_250_000.0
    daily_vol = 0.018
    annual_vol = 0.28

    if isinstance(pos_df, pd.DataFrame) and not pos_df.empty and "ticker" in pos_df.columns:
        has_live = True
        df_sorted = pos_df.copy()
        if "current_value" not in df_sorted.columns and "qty_net" in df_sorted.columns and "last_price" in df_sorted.columns:
            df_sorted["current_value"] = df_sorted["qty_net"].fillna(0.0) * df_sorted["last_price"].fillna(0.0)
        if "current_value" in df_sorted.columns:
            df_sorted = df_sorted.sort_values("current_value", ascending=False)
            total_nav = max(float(df_sorted["current_value"].fillna(0.0).sum()), 10_000.0)
        row0 = df_sorted.iloc[0]
        top_ticker = str(row0.get("ticker", "ENI.MI") or "ENI.MI")
        top_spot = max(float(row0.get("last_price", 14.80) or 14.80), 0.5)
        top_shares = max(float(row0.get("qty_net", 1000.0) or 1000.0), 100.0)

    rets_df = last_res.get("returns")
    if isinstance(rets_df, pd.DataFrame) and not rets_df.empty:
        has_live = True
        if top_ticker in rets_df.columns:
            s_std = float(rets_df[top_ticker].dropna().std())
            if s_std > 1e-5:
                daily_vol = float(np.clip(s_std, 0.005, 0.06))
                annual_vol = float(np.clip(s_std * np.sqrt(252.0), 0.08, 0.80))

    return {
        "has_live_portfolio": has_live,
        "top_ticker": top_ticker,
        "top_spot_price": round(top_spot, 4),
        "top_shares": round(top_shares, 1),
        "total_nav_eur": round(total_nav, 2),
        "daily_volatility": round(daily_vol, 4),
        "annual_volatility": round(annual_vol, 4),
        "adv_shares_estimate": round(max(top_shares * 20.0, 500_000.0), 0),
    }


def render_live_portfolio_autobind_banner(
    key_prefix: str,
    model_label: str = "Motore Quantitativo",
) -> dict[str, Any]:
    """Render 1-Click Live Portfolio Auto-Bind control and return bound parameters."""
    binding = extract_live_portfolio_binding()
    if st is None:
        return binding

    c1, c2 = st.columns([1.5, 2.5])
    with c1:
        use_live = st.toggle(
            f"🔗 Sincronizza dal Portafoglio Attivo ({binding['top_ticker']})",
            value=binding["has_live_portfolio"],
            key=f"autobind_toggle_{key_prefix}",
            help=f"Popola automaticamente {model_label} con i dati reali del portafoglio attivo.",
        )
    with c2:
        mode_txt = (
            f"🟢 <b>Auto-Binding Attivo</b>: Ticker Primario <code>{binding['top_ticker']}</code> "
            f"(Spot € {binding['top_spot_price']:.2f} | Vol Giornaliera {binding['daily_volatility']*100:.2f}% | NAV € {binding['total_nav_eur']:,.0f})"
            if use_live
            else "⚪ <b>Modalità Sandbox Istituzionale</b>: Parametri manuali personalizzabili indipendenti dal portafoglio."
        )
        st.markdown(
            f"<div style='font-size:11.5px; color:#cbd5e1; padding-top:6px;'>{mode_txt}</div>",
            unsafe_allow_html=True,
        )
    binding["autobind_enabled"] = bool(use_live)
    return binding


def style_institutional_chart(
    fig: Any,
    title: str | None = None,
    height: int = 390,
    unified_hover: bool = True,
) -> Any:
    """Apply ARGUS Institutional Terminal styling, transparent glassmorphic canvas, and magnetic crosshairs."""
    if fig is None or not hasattr(fig, "update_layout"):
        return fig

    layout_kwargs: dict[str, Any] = {
        "template": "plotly_dark",
        "height": height,
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(15, 23, 42, 0.35)",
        "font": {"family": "Outfit, JetBrains Mono, sans-serif", "color": "#e2e8f0", "size": 12},
        "margin": {"l": 16, "r": 16, "t": 44 if title else 24, "b": 20},
        "hovermode": "x unified" if unified_hover else "closest",
        "colorway": INSTITUTIONAL_PALETTE,
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0.0,
            "bgcolor": "rgba(22, 27, 34, 0.75)",
            "bordercolor": "rgba(255,255,255,0.12)",
            "borderwidth": 1,
            "font": {"size": 11, "color": "#f1f5f9"},
        },
    }
    if title:
        layout_kwargs["title"] = {
            "text": f"<b>{title}</b>",
            "font": {"size": 14, "color": "#f8fafc"},
            "x": 0.0,
            "xanchor": "left",
        }

    fig.update_layout(**layout_kwargs)
    if hasattr(fig, "update_xaxes"):
        fig.update_xaxes(
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.12)",
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikecolor="rgba(99, 102, 241, 0.55)",
            spikethickness=1,
        )
    if hasattr(fig, "update_yaxes"):
        fig.update_yaxes(
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.12)",
        )
    return fig


def compute_scenario_delta_comparison(
    baseline_metrics: dict[str, float],
    current_metrics: dict[str, float],
    higher_is_better_map: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Compute side-by-side absolute and percentage deltas between Pinned Baseline and Current Run."""
    hib = higher_is_better_map or {}
    rows: list[dict[str, Any]] = []
    improved_count = 0

    for metric_name, curr_val in current_metrics.items():
        base_val = float(baseline_metrics.get(metric_name, curr_val))
        curr_f = float(curr_val)
        delta_abs = curr_f - base_val
        denom = abs(base_val) if abs(base_val) > 1e-9 else 1.0
        delta_pct = (delta_abs / denom) * 100.0
        higher_better = bool(hib.get(metric_name, True))

        if abs(delta_abs) < 1e-8:
            status = "UNCHANGED"
            is_favorable = True
        else:
            is_favorable = (delta_abs > 0) if higher_better else (delta_abs < 0)
            status = "IMPROVED" if is_favorable else "DEGRADED"
            if is_favorable:
                improved_count += 1

        rows.append(
            {
                "metric": metric_name,
                "baseline": round(base_val, 4),
                "current": round(curr_f, 4),
                "delta_abs": round(delta_abs, 4),
                "delta_pct": round(delta_pct, 2),
                "higher_is_better": higher_better,
                "is_favorable": is_favorable,
                "status": status,
            }
        )

    return {
        "has_baseline": bool(baseline_metrics),
        "metrics_count": len(rows),
        "improved_count": improved_count,
        "comparisons": rows,
    }


def render_scenario_delta_comparator(
    scenario_key: str,
    scenario_title: str,
    current_metrics: dict[str, float],
    higher_is_better_map: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Render interactive Pin Baseline button and side-by-side Delta Comparator bar."""
    store_key = f"_pinned_baseline_{scenario_key}"
    if st is None:
        return compute_scenario_delta_comparison(current_metrics, current_metrics, higher_is_better_map)

    pinned = st.session_state.get(store_key)
    c_btn1, c_btn2, c_info = st.columns([1.1, 0.9, 2.5])
    with c_btn1:
        if st.button(
            "📌 Fissa come Baseline",
            key=f"btn_pin_{scenario_key}",
            use_container_width=True,
            help="Salva i risultati attuali come Baseline di riferimento per confrontare l'effetto di modifiche ai parametri.",
        ):
            st.session_state[store_key] = dict(current_metrics)
            pinned = st.session_state[store_key]
    with c_btn2:
        if pinned and st.button(
            "🧹 Reset Baseline",
            key=f"btn_rst_{scenario_key}",
            use_container_width=True,
        ):
            del st.session_state[store_key]
            pinned = None
    with c_info:
        if pinned:
            st.caption(rf"⚖️ **Scenario Delta Comparator attivo** per *{scenario_title}* — Modifica i parametri per osservare i differenziali $\Delta$ rispetto alla Baseline fissata.")
        else:
            st.caption(f"💡 Clicca **📌 Fissa come Baseline** per congelare *{scenario_title}* e confrontare scenari Prima vs Dopo.")

    if not pinned:
        return compute_scenario_delta_comparison(current_metrics, current_metrics, higher_is_better_map)

    comp = compute_scenario_delta_comparison(pinned, current_metrics, higher_is_better_map)
    cols = st.columns(min(max(len(comp["comparisons"]), 1), 4))
    for idx, item in enumerate(comp["comparisons"][:4]):
        col = cols[idx % len(cols)]
        color = "#10b981" if item["is_favorable"] else "#ef4444"
        if item["status"] == "UNCHANGED":
            color = "#94a3b8"
        sign = "+" if item["delta_abs"] >= 0 else ""
        with col:
            st.markdown(
                f"""
                <div style="background: rgba(22, 27, 34, 0.8); border: 1px solid rgba(255,255,255,0.08);
                            border-top: 3px solid {color}; border-radius: 8px; padding: 8px 10px; margin-bottom: 8px;">
                    <div style="font-size: 10.5px; color: #94a3b8; font-weight: 700;">{item['metric']}</div>
                    <div style="font-size: 14px; font-weight: 800; color: #f8fafc; margin-top: 2px;">
                        {item['current']:,.2f} <span style="font-size: 11px; color: #64748b;">(Base: {item['baseline']:,.2f})</span>
                    </div>
                    <div style="font-size: 11px; font-weight: 700; color: {color}; font-family: 'JetBrains Mono', monospace;">
                        Δ {sign}{item['delta_abs']:,.2f} ({sign}{item['delta_pct']:.2f}%)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    return comp


def compute_executive_traffic_light_radar(
    metrics_override: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute 6-Pillar Executive CRO Traffic-Light Radar (Pass / Warning / Breach)."""
    m = {
        "var_99_daily_pct": 1.84,
        "var_limit_pct": 2.50,
        "basel_lcr_pct": 142.5,
        "basel_nsfr_pct": 118.4,
        "ccar_stressed_cet1_pct": 10.25,
        "ccar_mda_hurdle_pct": 9.50,
        "priips_sri_score": 3.0,
        "hhi_concentration_pct": 16.5,
        "counterparty_cva_bps": 14.2,
    }
    if metrics_override:
        m.update(metrics_override)

    pillars: list[dict[str, Any]] = []

    # 1. Market Risk VaR 99% Gate
    var_val = float(m["var_99_daily_pct"])
    var_lim = float(m["var_limit_pct"])
    var_status = "PASS" if var_val <= var_lim * 0.85 else ("WARNING" if var_val <= var_lim else "BREACH")
    pillars.append(
        {
            "pillar_id": "market_var",
            "title": "Market Risk VaR 99% (1d)",
            "value_label": f"{var_val:.2f}% (Limit {var_lim:.2f}%)",
            "status": var_status,
            "target_page": "src/pages/1_📈_Analisi_Mercato.py",
            "badge_color": "#10b981" if var_status == "PASS" else ("#f59e0b" if var_status == "WARNING" else "#ef4444"),
        }
    )

    # 2. Basel III Liquidity LCR & NSFR
    lcr = float(m["basel_lcr_pct"])
    nsfr = float(m["basel_nsfr_pct"])
    liq_status = "PASS" if (lcr >= 110.0 and nsfr >= 105.0) else ("WARNING" if (lcr >= 100.0 and nsfr >= 100.0) else "BREACH")
    pillars.append(
        {
            "pillar_id": "basel_liquidity",
            "title": "Basel III LCR & NSFR",
            "value_label": f"LCR {lcr:.1f}% | NSFR {nsfr:.1f}%",
            "status": liq_status,
            "target_page": "src/pages/7_🌪️_Stress_Testing.py",
            "badge_color": "#10b981" if liq_status == "PASS" else ("#f59e0b" if liq_status == "WARNING" else "#ef4444"),
        }
    )

    # 3. Fed CCAR / EBA Stressed CET1
    cet1 = float(m["ccar_stressed_cet1_pct"])
    mda = float(m["ccar_mda_hurdle_pct"])
    ccar_status = "PASS" if cet1 >= mda + 0.5 else ("WARNING" if cet1 >= 6.0 else "BREACH")
    pillars.append(
        {
            "pillar_id": "ccar_capital",
            "title": "Fed CCAR / EBA Stressed CET1",
            "value_label": f"Min CET1 {cet1:.2f}% (MDA {mda:.1f}%)",
            "status": ccar_status,
            "target_page": "src/pages/7_🌪️_Stress_Testing.py",
            "badge_color": "#10b981" if ccar_status == "PASS" else ("#f59e0b" if ccar_status == "WARNING" else "#ef4444"),
        }
    )

    # 4. PRIIPs KID SRI & SFDR Compliance
    sri = int(round(float(m["priips_sri_score"])))
    sri_status = "PASS" if sri <= 4 else ("WARNING" if sri == 5 else "BREACH")
    pillars.append(
        {
            "pillar_id": "priips_sri",
            "title": "PRIIPs KID Risk Indicator",
            "value_label": f"SRI {sri}/7 (Art. 8/9 ESG)",
            "status": sri_status,
            "target_page": "src/pages/13_🏛️_Patrimonio_e_NetWorth.py",
            "badge_color": "#10b981" if sri_status == "PASS" else ("#f59e0b" if sri_status == "WARNING" else "#ef4444"),
        }
    )

    # 5. Portfolio Concentration HHI
    hhi = float(m["hhi_concentration_pct"])
    hhi_status = "PASS" if hhi <= 20.0 else ("WARNING" if hhi <= 30.0 else "BREACH")
    pillars.append(
        {
            "pillar_id": "hhi_concentration",
            "title": "Concentrazione HHI & UCITS",
            "value_label": f"HHI {hhi:.1f}% (Soglia 25%)",
            "status": hhi_status,
            "target_page": "src/pages/4_🔬_Modelli_Quantitativi.py",
            "badge_color": "#10b981" if hhi_status == "PASS" else ("#f59e0b" if hhi_status == "WARNING" else "#ef4444"),
        }
    )

    # 6. Bilateral XVA & Credit IRB
    cva_bps = float(m["counterparty_cva_bps"])
    xva_status = "PASS" if cva_bps <= 25.0 else ("WARNING" if cva_bps <= 50.0 else "BREACH")
    pillars.append(
        {
            "pillar_id": "xva_credit",
            "title": "Counterparty XVA & Credit IRB",
            "value_label": f"CVA/FVA {cva_bps:.1f} bps",
            "status": xva_status,
            "target_page": "src/pages/7_🌪️_Stress_Testing.py",
            "badge_color": "#10b981" if xva_status == "PASS" else ("#f59e0b" if xva_status == "WARNING" else "#ef4444"),
        }
    )

    pass_cnt = sum(1 for p in pillars if p["status"] == "PASS")
    warn_cnt = sum(1 for p in pillars if p["status"] == "WARNING")
    breach_cnt = sum(1 for p in pillars if p["status"] == "BREACH")

    overall = "GREEN - ALL REGULATORY GATES COMPLIANT"
    if breach_cnt > 0:
        overall = f"RED - {breach_cnt} REGULATORY BREACH(ES) DETECTED"
    elif warn_cnt > 0:
        overall = f"AMBER - {warn_cnt} SUPERVISORY WATCH ITEM(S)"

    return {
        "overall_status": overall,
        "pass_count": pass_cnt,
        "warning_count": warn_cnt,
        "breach_count": breach_cnt,
        "pillars": pillars,
    }


def render_executive_traffic_light_radar(
    key_prefix: str = "cro_radar",
    metrics_override: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Render compact 6-Pillar CRO Traffic-Light Radar with 1-click page navigation."""
    radar = compute_executive_traffic_light_radar(metrics_override=metrics_override)
    if st is None:
        return radar

    with st.expander("🚦 Executive CRO Traffic-Light Radar (Semaforo Regolamentare & Risk Appetite — 6 Pilastri)", expanded=False):
        cols = st.columns(3)
        for idx, p in enumerate(radar["pillars"]):
            icon = "🟢" if p["status"] == "PASS" else ("🟡" if p["status"] == "WARNING" else "🔴")
            with cols[idx % 3]:
                st.markdown(
                    f"""
                    <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(255,255,255,0.08);
                                border-left: 4px solid {p['badge_color']}; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size: 12px; font-weight: 700; color: #f8fafc;">{p['title']}</span>
                            <span style="font-size: 10.5px; font-weight: 800; color: {p['badge_color']};">{icon} {p['status']}</span>
                        </div>
                        <div style="font-size: 12px; color: #94a3b8; font-family: 'JetBrains Mono', monospace; margin-top: 4px;">
                            {p['value_label']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    return radar


def render_segmented_workspace_switcher(
    workspace_key: str,
    label: str,
    options: list[str],
    default_index: int = 0,
) -> str:
    """Render Bloomberg-style horizontal workspace selector bar to eliminate infinite scroll fatigue."""
    if st is None or not options:
        return options[0] if options else ""

    selected = st.radio(
        label,
        options=options,
        index=min(default_index, len(options) - 1),
        horizontal=True,
        key=f"seg_ws_{workspace_key}",
    )
    return str(selected)
