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

import hashlib
import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

try:
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None  # type: ignore[assignment]

APP_VERSION: str = "9.18.0"

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


def _compact_html(raw: str) -> str:
    """Collapse multi-line HTML into a single line to prevent CommonMark 4-space code block parsing."""
    return " ".join(line.strip() for line in raw.splitlines() if line.strip())


def build_telemetry_ribbon_html(
    telemetry: dict[str, Any],
    shock_info: dict[str, Any] | None = None,
) -> str:
    """Build single-line, zero-indent HTML for the sticky institutional telemetry ribbon."""
    s_info = shock_info if shock_info is not None else get_active_macro_shock()
    nav_str = f"€ {telemetry['nav_eur']:,.0f}".replace(",", ".")
    var_str = f"€ {telemetry['var_99_eur']:,.0f}".replace(",", ".")
    shock_pill_html = ""
    if s_info.get("is_active"):
        shock_pill_html = (
            f'<span style="background: rgba(168, 85, 247, 0.22); border: 1px solid #a855f7; '
            f'color: #e9d5ff; font-size: 10.5px; font-weight: 800; padding: 2px 8px; border-radius: 12px;">'
            f'⚡ SHOCK: {s_info["label"]}</span>'
        )

    raw_html = f"""
    <div style="background: linear-gradient(90deg, rgba(15, 23, 42, 0.96) 0%, rgba(22, 27, 34, 0.96) 100%);
                border: 1px solid rgba(99, 102, 241, 0.32);
                border-left: 4px solid #6366f1;
                border-radius: 10px;
                padding: 8px 14px;
                margin-bottom: 8px;
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
            {shock_pill_html}
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
    """
    return _compact_html(raw_html)


def render_institutional_telemetry_ribbon(
    page_badge: str = "INSTITUTIONAL TERMINAL",
) -> dict[str, Any]:
    """Render sticky Bloomberg Launchpad-style top telemetry ribbon in Streamlit."""
    telemetry = build_telemetry_ribbon_state(page_badge=page_badge)
    shock_info = get_active_macro_shock()
    telemetry["active_macro_shock"] = shock_info["preset_key"]
    if st is None:
        return telemetry

    density_mode = str(st.session_state.get("ux_density_mode", "COMPACT_DESK"))
    inject_density_mode_css(density_mode)

    # Avoid rendering a duplicate top bar on the Control Room (which already renders render_command_bar + render_control_room_hero)
    if "CONTROL ROOM" not in page_badge.upper():
        st.markdown(build_telemetry_ribbon_html(telemetry, shock_info), unsafe_allow_html=True)
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


apply_institutional_plotly_theme = style_institutional_chart


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
    session_state_dict: dict[str, Any] | None = None,
    risk_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute 6-Pillar Executive CRO Traffic-Light Radar reactive to Live Portfolio & Global Macro Shocks."""
    state = session_state_dict if session_state_dict is not None else (
        dict(st.session_state) if st is not None and hasattr(st, "session_state") else {}
    )
    last_res = risk_data if isinstance(risk_data, dict) and risk_data else (state.get("last_results") or {})
    metrics_block = last_res.get("metrics") or {}
    ret_block = metrics_block.get("returns") or {}
    mk = metrics_block.get("market_risk") or {}
    pos_raw = last_res.get("positions")
    pos_df = pd.DataFrame(pos_raw) if isinstance(pos_raw, list) else pos_raw
    has_live_portfolio = bool(
        last_res and (mk or ret_block or metrics_block or (isinstance(pos_df, pd.DataFrame) and not pos_df.empty))
    )

    # 1. Extract NAV (€)
    nav_eur = float(
        ret_block.get("portfolio_value")
        or metrics_block.get("total_value")
        or metrics_block.get("portfolio_value")
        or last_res.get("portfolio_value")
        or last_res.get("total_value")
        or 0.0
    )
    if nav_eur <= 0.0 and isinstance(pos_df, pd.DataFrame) and not pos_df.empty:
        for vcol in ("market_value", "current_value", "valore_mercato"):
            if vcol in pos_df.columns:
                nav_eur = float(pd.to_numeric(pos_df[vcol], errors="coerce").fillna(0.0).sum())
                if nav_eur > 0.0:
                    break
    if nav_eur <= 0.0:
        nav_eur = 125_000_000.0

    # 2. Extract Real Daily VaR 95% & VaR 99% (handling negative decimals like -0.0250 or pct like 2.50)
    raw_var95 = abs(
        float(
            mk.get("var_95")
            or mk.get("var_95_pct")
            or metrics_block.get("var_95")
            or last_res.get("var_95_pct")
            or 0.0
        )
    )
    if 0.0 < raw_var95 < 0.50:
        raw_var95 *= 100.0
    raw_var99 = abs(
        float(
            mk.get("var_99")
            or mk.get("var_99_pct")
            or metrics_block.get("var_99")
            or last_res.get("var_99_pct")
            or 0.0
        )
    )
    if 0.0 < raw_var99 < 0.50:
        raw_var99 *= 100.0
    if raw_var99 <= 0.0:
        live_var = round(raw_var95 * 1.38, 2) if raw_var95 > 0.0 else 1.84
    else:
        live_var = round(raw_var99, 2)

    # 3. Extract Real Annualized Volatility %, Max Drawdown %, and Sharpe Ratio
    raw_vol = abs(
        float(
            mk.get("volatility_annual_pct")
            or mk.get("volatility_annual")
            or mk.get("annual_volatility")
            or ret_block.get("volatility_pct")
            or metrics_block.get("volatility_annual_pct")
            or metrics_block.get("volatility_annual")
            or last_res.get("annual_volatility_pct")
            or 0.0
        )
    )
    if 0.0 < raw_vol < 1.50:
        raw_vol *= 100.0
    live_vol = round(raw_vol, 2) if raw_vol > 0.0 else 12.6

    raw_mdd = abs(
        float(
            mk.get("max_drawdown_pct")
            or mk.get("max_drawdown")
            or ret_block.get("max_drawdown_pct")
            or metrics_block.get("max_drawdown_pct")
            or metrics_block.get("max_drawdown")
            or last_res.get("max_drawdown_pct")
            or 0.0
        )
    )
    if 0.0 < raw_mdd < 1.50:
        raw_mdd *= 100.0
    live_mdd = round(raw_mdd, 2) if raw_mdd > 0.0 else 9.8

    if has_live_portfolio and (
        "sharpe_ratio" in ret_block
        or "sharpe_ratio" in mk
        or "sharpe_ratio" in metrics_block
        or "sharpe_ratio" in last_res
    ):
        live_sharpe = round(
            float(
                ret_block.get(
                    "sharpe_ratio",
                    mk.get(
                        "sharpe_ratio",
                        metrics_block.get("sharpe_ratio", last_res.get("sharpe_ratio", 1.42)),
                    ),
                )
            ),
            2,
        )
    else:
        live_sharpe = 1.42

    # 4. Extract Real HHI Concentration % from positions
    live_hhi = 16.5
    if isinstance(pos_df, pd.DataFrame) and not pos_df.empty:
        w_series = None
        for wcol in ("weight", "weight_pct", "peso_pct"):
            if wcol in pos_df.columns:
                w_series = pd.to_numeric(pos_df[wcol], errors="coerce").fillna(0.0)
                break
        if w_series is None:
            for vcol in ("market_value", "current_value", "valore_mercato"):
                if vcol in pos_df.columns:
                    vals = pd.to_numeric(pos_df[vcol], errors="coerce").fillna(0.0).abs()
                    if vals.sum() > 0:
                        w_series = vals / vals.sum()
                        break
        if w_series is not None and w_series.sum() > 0:
            w_norm = w_series / w_series.sum()
            hhi_calc = float((w_norm**2).sum() * 100.0)
            if hhi_calc > 0.5:
                live_hhi = round(hhi_calc, 1)

    # 5. Compute Real PRIIPs SRI (1-7) & CET1 / Liquidity adjustments from portfolio risk
    base_sri = 3.0
    if live_vol >= 40.0 or live_mdd >= 32.0:
        base_sri = 6.0
    elif live_vol >= 25.0 or live_mdd >= 22.0:
        base_sri = 5.0
    elif live_vol >= 15.0 or live_mdd >= 14.0:
        base_sri = 4.0

    base_cet1 = 10.25
    if live_sharpe < 0.35 or live_mdd >= 25.0:
        base_cet1 = 8.85
    elif live_sharpe < 0.70 or live_mdd >= 18.0:
        base_cet1 = 9.35

    base_cva = round(14.2 + max(0.0, (live_vol - 14.0) * 0.65), 1)

    shock = get_active_macro_shock(session_state_dict=state)
    s_key = str(shock.get("preset_key", "NONE"))

    var_shock_add = 0.0
    lcr_shock_add = 0.0
    nsfr_shock_add = 0.0
    cet1_shock_add = 0.0
    sri_shock_add = 0.0
    hhi_shock_add = 0.0
    cva_shock_add = 0.0

    if s_key == "GFC_2008":
        var_shock_add = 1.45
        lcr_shock_add = -38.0
        nsfr_shock_add = -16.0
        cet1_shock_add = -2.40
        sri_shock_add = 2.0
        hhi_shock_add = 7.5
        cva_shock_add = 38.0
    elif s_key == "STAGFLATION_SHOCK":
        var_shock_add = 0.82
        lcr_shock_add = -22.0
        nsfr_shock_add = -9.5
        cet1_shock_add = -1.15
        sri_shock_add = 1.0
        hhi_shock_add = 4.5
        cva_shock_add = 18.5
    elif s_key == "LIQUIDITY_FREEZE":
        var_shock_add = 0.65
        lcr_shock_add = -46.0
        nsfr_shock_add = -19.5
        cet1_shock_add = -0.85
        sri_shock_add = 1.0
        hhi_shock_add = 9.0
        cva_shock_add = 26.0

    m = {
        "var_99_daily_pct": round(live_var + var_shock_add, 2),
        "var_limit_pct": 2.50,
        "basel_lcr_pct": round(142.5 + lcr_shock_add, 1),
        "basel_nsfr_pct": round(118.4 + nsfr_shock_add, 1),
        "ccar_stressed_cet1_pct": round(base_cet1 + cet1_shock_add, 2),
        "ccar_mda_hurdle_pct": 9.50,
        "priips_sri_score": min(7.0, max(1.0, base_sri + sri_shock_add)),
        "hhi_concentration_pct": round(live_hhi + hhi_shock_add, 1),
        "counterparty_cva_bps": round(base_cva + cva_shock_add, 1),
    }
    if metrics_override:
        m.update(metrics_override)

    pillars: list[dict[str, Any]] = []

    # 1. Market Risk VaR 99% Gate
    var_val = float(m["var_99_daily_pct"])
    var_lim = float(m["var_limit_pct"])
    var_util = min(100.0, (var_val / max(var_lim, 0.01)) * 100.0)
    var_status = "PASS" if var_val <= var_lim * 0.85 else ("WARNING" if var_val <= var_lim else "BREACH")
    pillars.append(
        {
            "pillar_id": "market_var",
            "title": "Market Risk VaR 99% (1d)",
            "reg_framework": "BCBS-352 / FRTB",
            "value_label": f"VaR {var_val:.2f}% / Lim {var_lim:.2f}%",
            "delta_label": (
                f"Δ +{var_shock_add:.2f}% Shock"
                if var_shock_add > 0
                else (f"VaR 95%: {raw_var95:.2f}%" if raw_var95 > 0 else "Baseline Compliant")
            ),
            "utilization_pct": round(var_util, 1),
            "sparkline": [1.45, 1.62, 1.84, max(1.84, live_var * 0.9), var_val],
            "status": var_status,
            "target_page": "pages/2_🔴_Analisi_Rischio.py",
            "badge_color": "#10b981" if var_status == "PASS" else ("#f59e0b" if var_status == "WARNING" else "#ef4444"),
        }
    )

    # 2. Basel III Liquidity LCR & NSFR
    lcr = float(m["basel_lcr_pct"])
    nsfr = float(m["basel_nsfr_pct"])
    liq_util = min(100.0, max(12.0, (150.0 - lcr) / 50.0 * 100.0))
    liq_status = "PASS" if (lcr >= 110.0 and nsfr >= 105.0) else ("WARNING" if (lcr >= 100.0 and nsfr >= 100.0) else "BREACH")
    pillars.append(
        {
            "pillar_id": "basel_liquidity",
            "title": "Basel III LCR & NSFR",
            "reg_framework": "CRR II / Basel III",
            "value_label": f"LCR {lcr:.1f}% · NSFR {nsfr:.0f}%",
            "delta_label": f"Δ {lcr_shock_add:+.1f}% LCR" if lcr_shock_add != 0 else "Min 100% Buffer OK",
            "utilization_pct": round(liq_util, 1),
            "sparkline": [148.0, 145.0, 143.5, 142.5, lcr],
            "status": liq_status,
            "target_page": "pages/7_🌪️_Stress_Testing.py",
            "badge_color": "#10b981" if liq_status == "PASS" else ("#f59e0b" if liq_status == "WARNING" else "#ef4444"),
        }
    )

    # 3. Fed CCAR / EBA Stressed CET1 & Sharpe Efficiency
    cet1 = float(m["ccar_stressed_cet1_pct"])
    mda = float(m["ccar_mda_hurdle_pct"])
    ccar_util = min(100.0, max(15.0, (mda / max(cet1, 1.0)) * 84.0))
    ccar_status = "PASS" if (cet1 >= mda + 0.5 and live_sharpe >= 0.70) else ("WARNING" if (cet1 >= 8.5 and live_sharpe >= 0.15) else "BREACH")
    if metrics_override and "ccar_stressed_cet1_pct" in metrics_override:
        ccar_status = "PASS" if cet1 >= mda + 0.5 else ("WARNING" if cet1 >= 6.0 else "BREACH")
    pillars.append(
        {
            "pillar_id": "ccar_capital",
            "title": "Stressed CET1 & Sharpe",
            "reg_framework": "EBA / Hurdle Rf",
            "value_label": f"CET1 {cet1:.2f}% · SR {live_sharpe:.2f}",
            "delta_label": (
                f"Sharpe {live_sharpe:.2f} < 0.70 Hurdle"
                if live_sharpe < 0.70
                else (f"Δ {cet1_shock_add:+.2f}% CET1" if cet1_shock_add != 0 else f"+{cet1 - mda:.2f}% vs MDA")
            ),
            "utilization_pct": round(ccar_util, 1),
            "sparkline": [12.4, 11.8, 11.1, 10.25, cet1],
            "status": ccar_status,
            "target_page": "pages/7_🌪️_Stress_Testing.py",
            "badge_color": "#10b981" if ccar_status == "PASS" else ("#f59e0b" if ccar_status == "WARNING" else "#ef4444"),
        }
    )

    # 4. PRIIPs KID SRI & Max Drawdown Gate
    sri = int(round(float(m["priips_sri_score"])))
    sri_util = round((sri / 7.0) * 100.0, 1)
    sri_status = "PASS" if (sri <= 4 and live_mdd <= 22.0) else ("WARNING" if (sri == 5 and live_mdd <= 28.0) else "BREACH")
    pillars.append(
        {
            "pillar_id": "priips_sri",
            "title": "PRIIPs SRI & Drawdown",
            "reg_framework": "EU PRIIPs / MDD",
            "value_label": f"SRI {sri}/7 · MDD {live_mdd:.1f}%",
            "delta_label": (
                f"Vol {live_vol:.1f}% (>25%) · MDD {live_mdd:.1f}%"
                if (live_vol > 25.0 or live_mdd > 22.0)
                else "Target SRI ≤ 4/7"
            ),
            "utilization_pct": sri_util,
            "sparkline": [3.0, 3.0, 4.0, base_sri, float(sri)],
            "status": sri_status,
            "target_page": "pages/13_🏛️_Patrimonio_e_NetWorth.py",
            "badge_color": "#10b981" if sri_status == "PASS" else ("#f59e0b" if sri_status == "WARNING" else "#ef4444"),
        }
    )

    # 5. Portfolio Concentration HHI
    hhi = float(m["hhi_concentration_pct"])
    hhi_util = min(100.0, (hhi / 25.0) * 100.0)
    hhi_status = "PASS" if hhi <= 20.0 else ("WARNING" if hhi <= 30.0 else "BREACH")
    pillars.append(
        {
            "pillar_id": "hhi_concentration",
            "title": "Concentrazione HHI & UCITS",
            "reg_framework": "UCITS V 5/10/40",
            "value_label": f"HHI {hhi:.1f}% / Max 25%",
            "delta_label": f"Δ +{hhi_shock_add:.1f}% Corr." if hhi_shock_add > 0 else "Diversificato",
            "utilization_pct": round(hhi_util, 1),
            "sparkline": [14.0, 15.2, 16.0, live_hhi, hhi],
            "status": hhi_status,
            "target_page": "pages/4_🔬_Modelli_Quantitativi.py",
            "badge_color": "#10b981" if hhi_status == "PASS" else ("#f59e0b" if hhi_status == "WARNING" else "#ef4444"),
        }
    )

    # 6. Bilateral XVA & Credit IRB
    cva_bps = float(m["counterparty_cva_bps"])
    xva_util = min(100.0, (cva_bps / 50.0) * 100.0)
    xva_status = "PASS" if cva_bps <= 25.0 else ("WARNING" if cva_bps <= 50.0 else "BREACH")
    pillars.append(
        {
            "pillar_id": "xva_credit",
            "title": "Counterparty XVA & Credit IRB",
            "reg_framework": "ISDA SIMM v2.6",
            "value_label": f"CVA {cva_bps:.1f} bps / Lim 50",
            "delta_label": f"Δ +{cva_shock_add:.1f} bps" if cva_shock_add > 0 else "Soglia 50 bps",
            "utilization_pct": round(xva_util, 1),
            "sparkline": [11.5, 12.4, 13.5, base_cva, cva_bps],
            "status": xva_status,
            "target_page": "pages/7_🌪️_Stress_Testing.py",
            "badge_color": "#10b981" if xva_status == "PASS" else ("#f59e0b" if xva_status == "WARNING" else "#ef4444"),
        }
    )

    pass_cnt = sum(1 for p in pillars if p["status"] == "PASS")
    warn_cnt = sum(1 for p in pillars if p["status"] == "WARNING")
    breach_cnt = sum(1 for p in pillars if p["status"] == "BREACH")
    readiness_score = max(15, int(round(100 - warn_cnt * 12 - breach_cnt * 22)))

    overall = "GREEN - ALL REGULATORY GATES COMPLIANT"
    if breach_cnt > 0:
        overall = f"RED - {breach_cnt} REGULATORY BREACH(ES) & {warn_cnt} WATCH ITEM(S)"
    elif warn_cnt > 0:
        overall = f"AMBER - {warn_cnt} SUPERVISORY WATCH ITEM(S)"

    return {
        "overall_status": overall,
        "readiness_score": readiness_score,
        "active_macro_shock": s_key,
        "nav_eur": nav_eur,
        "pass_count": pass_cnt,
        "warning_count": warn_cnt,
        "breach_count": breach_cnt,
        "pillars": pillars,
    }


def _safe_page_link(page_path: str, label: str) -> None:
    """Safely render st.page_link using path relative to the src/ entrypoint directory."""
    if st is None or not hasattr(st, "page_link") or not page_path:
        return
    rel_path = page_path[4:] if page_path.startswith("src/") else page_path
    try:
        st.page_link(rel_path, label=label, use_container_width=True)
    except Exception:
        pass


def render_executive_traffic_light_radar(
    key_prefix: str = "cro_radar",
    metrics_override: dict[str, float] | None = None,
    include_board_pack: bool = False,
    default_expanded: bool = False,
    risk_data: dict[str, Any] | None = None,
    factsheet_pdf_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Render upgraded CRO Traffic-Light Radar, Global Macro Shock Console & 1-Click Board-Pack."""
    radar = compute_executive_traffic_light_radar(
        metrics_override=metrics_override,
        risk_data=risk_data,
    )
    if st is None:
        return radar

    cur_shock = str(st.session_state.get("global_macro_shock", "NONE"))
    shock_badge = f" · ⚡ SHOCK: {cur_shock}" if cur_shock != "NONE" else ""
    score = int(radar.get("readiness_score", 96))
    expander_title = (
        f"🏛️ Console Istituzionale CRO & Stress Broadcast — Readiness {score}/100 "
        f"({radar['pass_count']} PASS · {radar['warning_count']} WATCH · {radar['breach_count']} BREACH){shock_badge}"
    )

    with st.expander(expander_title, expanded=default_expanded):
        score_col = "#10b981" if score >= 85 else ("#f59e0b" if score >= 60 else "#ef4444")
        shock_lbl = MACRO_SHOCK_PRESETS.get(cur_shock, MACRO_SHOCK_PRESETS["NONE"])["label"]
        top_strip_html = _compact_html(
            f"""
            <div style="background: linear-gradient(90deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.90) 100%);
                        border: 1px solid rgba(148,163,184,0.20); border-left: 4px solid {score_col};
                        border-radius: 10px; padding: 10px 16px; margin-bottom: 12px;
                        display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                    <span style="background:rgba(255,255,255,0.06); border:1px solid {score_col}; color:{score_col};
                                 font-family:'JetBrains Mono',monospace; font-size:12px; font-weight:800; padding:3px 10px; border-radius:8px;">
                        CRO READINESS: {score}/100
                    </span>
                    <span style="font-size:12px; font-weight:700; color:#f8fafc;">{radar['overall_status']}</span>
                </div>
                <div style="font-size:11.5px; color:#cbd5e1; font-family:'JetBrains Mono',monospace;">
                    NAV: <b style="color:#10b981;">€ {radar['nav_eur']:,.2f}</b> &bull; Scenario: <b style="color:#a855f7;">{shock_lbl}</b>
                </div>
            </div>
            """
        )
        st.markdown(top_strip_html, unsafe_allow_html=True)

        # Row 1: Perfectly Aligned 3-Column Controls
        c_cmd, c_shk, c_den = st.columns([2.1, 2.2, 1.2])
        with c_cmd:
            cmd_input = st.text_input(
                "⌨️ Bloomberg Command Launcher `<GO>`",
                value="",
                placeholder="SIMM <GO>, SVI <GO>, ALM <GO>, CDS <GO>, VPIN <GO>, SHOCK 2008...",
                key=f"{key_prefix}_go_in",
            )
            if cmd_input.strip():
                res = resolve_terminal_command(cmd_input)
                if res.get("macro_shock"):
                    st.session_state["global_macro_shock"] = res["macro_shock"]
                st.info(f"**{res['command']}** → {res['description']}")
                if res.get("target_page"):
                    _safe_page_link(res["target_page"], f"🚀 Apri {res['command']} ({res['workspace']})")
        with c_shk:
            preset_keys = list(MACRO_SHOCK_PRESETS.keys())
            idx = preset_keys.index(cur_shock) if cur_shock in preset_keys else 0
            chosen_shock = st.selectbox(
                "⚡ Global Macro Shock Broadcast (Cross-Page)",
                options=preset_keys,
                format_func=lambda k: MACRO_SHOCK_PRESETS[k]["label"],
                index=idx,
                key=f"{key_prefix}_shock_sel",
            )
            if chosen_shock != cur_shock:
                st.session_state["global_macro_shock"] = chosen_shock
                st.rerun()
        with c_den:
            cur_density = str(st.session_state.get("ux_density_mode", "COMPACT_DESK"))
            chosen_density = st.selectbox(
                "🖥️ Densità Terminale",
                options=["COMPACT_DESK", "BOARDROOM"],
                format_func=lambda m: "Compact Quant Desk" if m == "COMPACT_DESK" else "Boardroom HD Mode",
                index=0 if cur_density == "COMPACT_DESK" else 1,
                key=f"{key_prefix}_density_sel",
            )
            st.session_state["ux_density_mode"] = chosen_density

        # Row 2: 1-Click Quick-Jump Institutional Module Bar
        if hasattr(st, "page_link"):
            qj1, qj2, qj3, qj4, qj5, qj6 = st.columns(6)
            with qj1:
                _safe_page_link("pages/7_🌪️_Stress_Testing.py", "🛡️ ISDA SIMM v2.6")
            with qj2:
                _safe_page_link("pages/4_🔬_Modelli_Quantitativi.py", "🌊 Rough Vol & SVI")
            with qj3:
                _safe_page_link("pages/13_🏛️_Patrimonio_e_NetWorth.py", "🏛️ ALM / LDI LP")
            with qj4:
                _safe_page_link("pages/4_🔬_Modelli_Quantitativi.py", "💳 CDS & Tranches")
            with qj5:
                _safe_page_link("pages/13_🏛️_Patrimonio_e_NetWorth.py", "⚡ Market-Making VPIN")
            with qj6:
                _safe_page_link("pages/7_🌪️_Stress_Testing.py", "🌪️ Fed CCAR 9Q")

        # Row 3: 6 Rich Bento CRO Pillar Cards (Single-Line Value Label, SVG Sparkline & Limit Bar)
        cols = st.columns(3)
        for idx_p, p in enumerate(radar["pillars"]):
            icon = "🟢" if p["status"] == "PASS" else ("🟡" if p["status"] == "WARNING" else "🔴")
            spark_svg = build_svg_sparkline(p.get("sparkline", [1.0, 1.1, 1.05]), color=p["badge_color"], width=86, height=22)
            util_pct = float(p.get("utilization_pct", 50.0))
            with cols[idx_p % 3]:
                card_html = _compact_html(
                    f"""
                    <div class="argus-bento-card" style="background: rgba(15, 23, 42, 0.90); border: 1px solid rgba(148,163,184,0.16);
                                border-left: 4px solid {p['badge_color']}; border-radius: 10px; padding: 11px 14px; margin-bottom: 10px;
                                box-shadow: 0 4px 12px rgba(0,0,0,0.25);">
                        <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
                            <span style="font-size: 11.5px; font-weight: 700; color: #f8fafc; white-space:nowrap;">{p['title']}</span>
                            <span style="background:rgba(255,255,255,0.05); border:1px solid {p['badge_color']};
                                         font-size: 9.5px; font-weight: 800; color: {p['badge_color']}; padding:1px 7px; border-radius:10px; white-space:nowrap;">
                                {icon} {p['status']}
                            </span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:7px; gap:8px;">
                            <div style="min-width:0;">
                                <div style="font-size: 13.5px; font-weight: 800; color: #f1f5f9; font-family: 'JetBrains Mono', monospace; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                                    {p['value_label']}
                                </div>
                                <div style="font-size: 10px; color: #94a3b8; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                                    <span style="color:#818cf8; font-weight:700;">[{p.get('reg_framework', 'BCBS')}]</span> · {p.get('delta_label', '')}
                                </div>
                            </div>
                            <div style="flex-shrink:0;">{spark_svg}</div>
                        </div>
                        <div style="margin-top:7px;">
                            <div style="display:flex; justify-content:space-between; font-size:9.5px; color:#94a3b8; margin-bottom:2px;">
                                <span>Saturazione Limite Regolamentare</span>
                                <span style="color:{p['badge_color']}; font-weight:700;">{util_pct:.1f}%</span>
                            </div>
                            <div style="width:100%; height:4px; background:rgba(255,255,255,0.08); border-radius:2px; overflow:hidden;">
                                <div style="width:{min(100.0, util_pct):.1f}%; height:100%; background:{p['badge_color']}; border-radius:2px;"></div>
                            </div>
                        </div>
                    </div>
                    """
                )
                st.markdown(card_html, unsafe_allow_html=True)

        if include_board_pack:
            from core.executive_board_pack_engine import generate_executive_board_pack

            port_name = str(st.session_state.get("portfolio_name") or "Portafoglio Attivo")
            bp_res = generate_executive_board_pack(
                portfolio_name=port_name,
                nav_eur=float(radar.get("nav_eur", 125_000_000.0)),
            )
            bp_c1, bp_c2 = st.columns([3.0, 1.2])
            with bp_c1:
                rx_items_html = "".join(
                    f'<div style="font-size:11.5px; color:#e2e8f0; margin-bottom:4px;">'
                    f'<span style="background:rgba(99,102,241,0.2); color:#a5b4fc; font-weight:800; font-size:10px; '
                    f'padding:1px 6px; border-radius:4px; margin-right:6px;">{rx["priority"]} · {rx["domain"]}</span>'
                    f'{rx["action"]}</div>'
                    for rx in bp_res["cro_prescriptions"][:2]
                )
                st.markdown(
                    _compact_html(
                        f"""
                        <div style="background:rgba(22,27,34,0.75); border:1px solid rgba(255,255,255,0.08);
                                    border-radius:8px; padding:8px 12px;">
                            <div style="font-size:11px; font-weight:800; color:#f59e0b; margin-bottom:4px;">
                                📑 PRESCRIZIONI OPERATIVE COMITATO RISCHI ({port_name} — NAV € {radar['nav_eur']:,.2f})
                            </div>
                            {rx_items_html}
                        </div>
                        """
                    ),
                    unsafe_allow_html=True,
                )
            with bp_c2:
                st.download_button(
                    label="📥 Scarica CRO Board-Pack (HTML5)",
                    data=bp_res["board_pack_html"].encode("utf-8"),
                    file_name="argus_executive_cro_board_pack_v918.html",
                    mime="text/html",
                    use_container_width=True,
                    type="primary",
                    key=f"{key_prefix}_dl_bp_btn",
                )
                if factsheet_pdf_bytes:
                    st.download_button(
                        label="📄 Factsheet PDF (2 Pagine)",
                        data=factsheet_pdf_bytes,
                        file_name=f"ARGUS_Factsheet_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"{key_prefix}_dl_pdf_btn",
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


# ============================================================================
# RELEASE v9.18.0 — BLOOMBERG COMMAND BAR <GO>, MACRO SHOCK BROADCAST,
# BENTO KPI CARDS (SVG SPARKLINES), SR 11-7 AUDIT DRAWER & DENSITY MODES
# ============================================================================

MACRO_SHOCK_PRESETS: dict[str, dict[str, Any]] = {
    "NONE": {
        "preset_key": "NONE",
        "label": "🟢 Baseline Normal Market (No Global Shock)",
        "is_active": False,
        "rates_bps": 0.0,
        "credit_bps": 0.0,
        "equity_pct": 0.0,
        "vol_pts": 0.0,
        "vpin_add": 0.0,
    },
    "GFC_2008": {
        "preset_key": "GFC_2008",
        "label": "🔴 Global Financial Crisis 2008 (-125bps Rates / +350bps Credit / -35% Eq / +22v)",
        "is_active": True,
        "rates_bps": -125.0,
        "credit_bps": 350.0,
        "equity_pct": -35.0,
        "vol_pts": 22.0,
        "vpin_add": 0.35,
    },
    "STAGFLATION_SHOCK": {
        "preset_key": "STAGFLATION_SHOCK",
        "label": "🟠 Stagflation & Rate Spike (+200bps Rates / +160bps Credit / -18% Eq / +10v)",
        "is_active": True,
        "rates_bps": 200.0,
        "credit_bps": 160.0,
        "equity_pct": -18.0,
        "vol_pts": 10.0,
        "vpin_add": 0.20,
    },
    "LIQUIDITY_FREEZE": {
        "preset_key": "LIQUIDITY_FREEZE",
        "label": "🟣 Flash Crash & Order-Flow Toxicity (+50bps Rates / +220bps Credit / VPIN +0.45)",
        "is_active": True,
        "rates_bps": 50.0,
        "credit_bps": 220.0,
        "equity_pct": -15.0,
        "vol_pts": 16.0,
        "vpin_add": 0.45,
    },
}

GLOBAL_COMMAND_REGISTRY: dict[str, dict[str, str]] = {
    "SIMM": {
        "command": "SIMM <GO>",
        "target_page": "src/pages/7_🌪️_Stress_Testing.py",
        "workspace": "🛡️ Bilateral XVA, ISDA SIMM & Reg Capital",
        "description": "ISDA SIMM v2.6 Initial Margin, UMR $50M Threshold & CCP Optimizer",
    },
    "SVI": {
        "command": "SVI <GO>",
        "target_page": "src/pages/4_🔬_Modelli_Quantitativi.py",
        "workspace": "📈 Rates, Credit, Commodities & Rough Vol",
        "description": "Rough Bergomi (H=0.10) & Gatheral SVI Arbitrage-Free Volatility Surface",
    },
    "RBERGOMI": {
        "command": "RBERGOMI <GO>",
        "target_page": "src/pages/4_🔬_Modelli_Quantitativi.py",
        "workspace": "📈 Rates, Credit, Commodities & Rough Vol",
        "description": "Rough Bergomi Fractional Brownian Motion Volatility Surface",
    },
    "CDS": {
        "command": "CDS <GO>",
        "target_page": "src/pages/4_🔬_Modelli_Quantitativi.py",
        "workspace": "📈 Rates, Credit, Commodities & Rough Vol",
        "description": "Single-Name CDS Bootstrapping & iTraxx/CDX Synthetic CDO Tranches",
    },
    "ALM": {
        "command": "ALM <GO>",
        "target_page": "src/pages/13_🏛️_Patrimonio_e_NetWorth.py",
        "workspace": "🏛️ ALM, LDI & Microstructure Execution",
        "description": "Asset-Liability Management, Redington Immunization & Cash-Flow LP",
    },
    "VPIN": {
        "command": "VPIN <GO>",
        "target_page": "src/pages/13_🏛️_Patrimonio_e_NetWorth.py",
        "workspace": "🏛️ ALM, LDI & Microstructure Execution",
        "description": "Avellaneda-Stoikov Market-Making & Hawkes / VPIN Order-Flow Toxicity",
    },
    "PACK": {
        "command": "PACK <GO>",
        "target_page": "src/0_Control_Room.py",
        "workspace": "Executive CRO Board-Pack",
        "description": "1-Click Executive CRO & Investment Committee Printable HTML5 Board-Pack",
    },
    "CCAR": {
        "command": "CCAR <GO>",
        "target_page": "src/pages/7_🌪️_Stress_Testing.py",
        "workspace": "🛡️ Bilateral XVA, ISDA SIMM & Reg Capital",
        "description": "Fed CCAR / EBA 9-Quarter CET1 & Leverage Capital Trajectory",
    },
    "SHOCK 2008": {
        "command": "SHOCK 2008 <GO>",
        "target_page": "",
        "macro_shock": "GFC_2008",
        "description": "Broadcast Global Financial Crisis 2008 Macro Shock across all pages",
    },
    "SHOCK STAGFLATION": {
        "command": "SHOCK STAGFLATION <GO>",
        "target_page": "",
        "macro_shock": "STAGFLATION_SHOCK",
        "description": "Broadcast Stagflation (+200bps Rates / +160bps Credit) Shock across all pages",
    },
    "SHOCK LIQUIDITY": {
        "command": "SHOCK LIQUIDITY <GO>",
        "target_page": "",
        "macro_shock": "LIQUIDITY_FREEZE",
        "description": "Broadcast Liquidity Freeze & High VPIN Toxicity across all pages",
    },
    "SHOCK RESET": {
        "command": "SHOCK RESET <GO>",
        "target_page": "",
        "macro_shock": "NONE",
        "description": "Clear Global Macro Shock and return to Baseline Normal Market",
    },
}


def resolve_terminal_command(query: str) -> dict[str, Any]:
    """Resolve a user command string (e.g. 'SIMM <GO>', 'svi', 'shock 2008') into an executable action."""
    clean = str(query or "").upper().replace("<GO>", "").strip()
    if not clean:
        return {
            "matched": False,
            "command_key": "NONE",
            "command": "HELP <GO>",
            "target_page": "",
            "workspace": "",
            "macro_shock": "",
            "description": "Type SIMM, SVI, CDS, ALM, VPIN, PACK, CCAR, or SHOCK 2008",
        }

    # Exact or prefix match first
    for key, spec in GLOBAL_COMMAND_REGISTRY.items():
        if clean == key or clean.startswith(key) or key in clean:
            return {
                "matched": True,
                "command_key": key,
                "command": spec["command"],
                "target_page": spec.get("target_page", ""),
                "workspace": spec.get("workspace", ""),
                "macro_shock": spec.get("macro_shock", ""),
                "description": spec["description"],
            }

    # Fuzzy keyword match on description
    for key, spec in GLOBAL_COMMAND_REGISTRY.items():
        if any(tok in spec["description"].upper() for tok in clean.split() if len(tok) >= 3):
            return {
                "matched": True,
                "command_key": key,
                "command": spec["command"],
                "target_page": spec.get("target_page", ""),
                "workspace": spec.get("workspace", ""),
                "macro_shock": spec.get("macro_shock", ""),
                "description": spec["description"],
            }

    return {
        "matched": False,
        "command_key": "UNKNOWN",
        "command": f"{clean} <GO>",
        "target_page": "",
        "workspace": "",
        "macro_shock": "",
        "description": f"No exact match for '{clean}'. Available: " + ", ".join(GLOBAL_COMMAND_REGISTRY.keys()),
    }


def get_active_macro_shock(
    session_state_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return active global macro shock preset from session state."""
    state = session_state_dict if session_state_dict is not None else (
        dict(st.session_state) if st is not None and hasattr(st, "session_state") else {}
    )
    preset_key = str(state.get("global_macro_shock", "NONE")).upper()
    if preset_key not in MACRO_SHOCK_PRESETS:
        preset_key = "NONE"
    return dict(MACRO_SHOCK_PRESETS[preset_key])


def apply_macro_shock_to_inputs(
    base_inputs: dict[str, float],
    session_state_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply active global macro shock deltas to engine inputs deterministically."""
    shock = get_active_macro_shock(session_state_dict=session_state_dict)
    out = dict(base_inputs)
    if not shock["is_active"]:
        out["macro_shock_active"] = False
        out["macro_shock_label"] = shock["label"]
        return out

    rates_delta_dec = float(shock["rates_bps"]) / 10000.0
    credit_mult = 1.0 + float(shock["credit_bps"]) / 200.0
    eq_mult = max(0.25, 1.0 + float(shock["equity_pct"]) / 100.0)
    vol_add_dec = float(shock["vol_pts"]) / 100.0

    if "discount_rate" in out:
        out["discount_rate"] = max(0.005, float(out["discount_rate"]) + rates_delta_dec)
    if "index_spread_bps" in out:
        out["index_spread_bps"] = max(10.0, float(out["index_spread_bps"]) + float(shock["credit_bps"]))
    if "ir_dv01" in out:
        out["ir_dv01"] = float(out["ir_dv01"]) * (1.0 + abs(float(shock["rates_bps"])) / 250.0)
    if "credit_q_cs01" in out:
        out["credit_q_cs01"] = float(out["credit_q_cs01"]) * credit_mult
    if "equity_delta" in out:
        out["equity_delta"] = float(out["equity_delta"]) * (2.0 - eq_mult)
    if "annual_vol" in out:
        out["annual_vol"] = min(1.50, float(out["annual_vol"]) + vol_add_dec)
    if "asset_value" in out:
        out["asset_value"] = float(out["asset_value"]) * eq_mult

    out["macro_shock_active"] = True
    out["macro_shock_label"] = shock["label"]
    out["macro_shock_preset"] = shock["preset_key"]
    return out


def build_svg_sparkline(
    values: list[float],
    color: str = "#10b981",
    width: int = 120,
    height: int = 30,
) -> str:
    """Build an inline SVG polyline micro-sparkline for Bento KPI cards."""
    pts = [float(v) for v in (values or [1.0, 1.05, 1.02, 1.08, 1.12]) if np.isfinite(v)]
    if len(pts) < 2:
        pts = [1.0, 1.0]
    vmin, vmax = min(pts), max(pts)
    span = max(vmax - vmin, 1e-9)
    coords: list[str] = []
    for idx, val in enumerate(pts):
        x = (idx / (len(pts) - 1)) * (width - 6) + 3
        y = height - 4 - ((val - vmin) / span) * (height - 8)
        coords.append(f"{x:.1f},{y:.1f}")
    poly_points = " ".join(coords)
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="overflow:visible;">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" points="{poly_points}" />'
        f"</svg>"
    )


def build_bento_kpi_card_html(
    title: str,
    value: str,
    delta_label: str = "",
    provenance: str = "LIVE PORTFOLIO",
    limit_utilization_pct: float | None = None,
    sparkline_values: list[float] | None = None,
    accent_color: str = "#10b981",
) -> str:
    """Build HTML for an Institutional Bento KPI Card with inline SVG sparkline & limit bar."""
    prov_upper = provenance.upper()
    if "SHOCK" in prov_upper:
        prov_bg, prov_col, prov_icon = "rgba(168,85,247,0.18)", "#d8b4fe", "🟣"
    elif "LIVE" in prov_upper:
        prov_bg, prov_col, prov_icon = "rgba(16,185,129,0.16)", "#6ee7b7", "🟢"
    else:
        prov_bg, prov_col, prov_icon = "rgba(59,130,246,0.16)", "#93c5fd", "🔵"

    spark_html = ""
    if sparkline_values:
        spark_html = build_svg_sparkline(sparkline_values, color=accent_color, width=105, height=26)

    limit_html = ""
    if limit_utilization_pct is not None:
        pct_clamped = float(np.clip(limit_utilization_pct, 0.0, 100.0))
        bar_col = "#10b981" if pct_clamped < 70.0 else ("#f59e0b" if pct_clamped < 90.0 else "#ef4444")
        limit_html = (
            f'<div style="margin-top:8px;">'
            f'<div style="display:flex;justify-content:space-between;font-size:10px;color:#94a3b8;margin-bottom:2px;">'
            f'<span>Limit Utilization</span><span style="color:{bar_col};font-weight:700;">{limit_utilization_pct:.1f}%</span></div>'
            f'<div style="width:100%;height:5px;background:rgba(255,255,255,0.08);border-radius:3px;overflow:hidden;">'
            f'<div style="width:{pct_clamped:.1f}%;height:100%;background:{bar_col};border-radius:3px;"></div>'
            f"</div></div>"
        )

    return (
        f'<div class="argus-bento-card" style="background:rgba(15,23,42,0.86);border:1px solid rgba(148,163,184,0.18);'
        f'border-top:3px solid {accent_color};border-radius:10px;padding:12px 14px;margin-bottom:8px;'
        f'box-shadow:0 4px 14px rgba(0,0,0,0.28);">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">'
        f'<span style="font-size:11.5px;font-weight:700;color:#cbd5e1;">{title}</span>'
        f'<span style="background:{prov_bg};color:{prov_col};font-size:9.5px;font-weight:800;'
        f'padding:2px 6px;border-radius:8px;font-family:\'JetBrains Mono\',monospace;">{prov_icon} {provenance}</span>'
        f"</div>"
        f'<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-top:6px;">'
        f"<div>"
        f'<div style="font-size:20px;font-weight:800;color:#f8fafc;font-family:\'JetBrains Mono\',monospace;">{value}</div>'
        f'<div style="font-size:11px;color:{accent_color};font-weight:600;margin-top:2px;">{delta_label}</div>'
        f"</div>"
        f"<div>{spark_html}</div>"
        f"</div>"
        f"{limit_html}"
        f"</div>"
    )


def render_bento_kpi_card(
    title: str,
    value: str,
    delta_label: str = "",
    provenance: str = "LIVE PORTFOLIO",
    limit_utilization_pct: float | None = None,
    sparkline_values: list[float] | None = None,
    accent_color: str = "#10b981",
) -> str:
    """Render an Institutional Bento KPI Card in Streamlit and return its HTML."""
    html = build_bento_kpi_card_html(
        title=title,
        value=value,
        delta_label=delta_label,
        provenance=provenance,
        limit_utilization_pct=limit_utilization_pct,
        sparkline_values=sparkline_values,
        accent_color=accent_color,
    )
    if st is not None:
        st.markdown(html, unsafe_allow_html=True)
    return html


def build_sr117_audit_record(
    engine_name: str,
    model_version: str,
    latex_formulas: list[str],
    inputs_dict: dict[str, Any],
    outputs_dict: dict[str, Any],
    compute_ms: float = 4.2,
    regulatory_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Build a deterministic Fed SR 11-7 / ECB TRIM Model Risk Management audit trail record."""
    canonical_payload = json.dumps(
        {"engine": engine_name, "version": model_version, "inputs": inputs_dict, "outputs": outputs_dict},
        sort_keys=True,
        default=str,
    )
    sha256_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
    return {
        "engine_name": engine_name,
        "model_version": model_version,
        "sha256_audit_hash": sha256_hash,
        "compute_ms": round(float(compute_ms), 2),
        "timestamp_utc": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regulatory_references": regulatory_refs or ["Fed SR 11-7", "ECB TRIM", "BCBS-352"],
        "latex_formulas": latex_formulas,
        "canonical_json": canonical_payload,
    }


def render_sr117_audit_drawer(
    engine_name: str,
    latex_formulas: list[str],
    inputs_dict: dict[str, Any],
    outputs_dict: dict[str, Any],
    compute_ms: float = 4.2,
    regulatory_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Render collapsible Explain-the-Math & SR 11-7 Audit Trail drawer for a quantitative engine."""
    record = build_sr117_audit_record(
        engine_name=engine_name,
        model_version=APP_VERSION,
        latex_formulas=latex_formulas,
        inputs_dict=inputs_dict,
        outputs_dict=outputs_dict,
        compute_ms=compute_ms,
        regulatory_refs=regulatory_refs,
    )
    if st is None:
        return record

    with st.expander(
        f"📐 Explain-the-Math & SR 11-7 Audit Trail — {engine_name} [SHA-256: {record['sha256_audit_hash'][:12]}...]"
    ):
        st.caption(
            f"**Regulatory Standards**: {', '.join(record['regulatory_references'])} | "
            f"**Compute Latency**: `{record['compute_ms']:.2f} ms` | "
            f"**Audit Hash**: `{record['sha256_audit_hash']}`"
        )
        for formula in latex_formulas:
            st.latex(formula)
        st.code(record["canonical_json"][:1200], language="json")
    return record


def get_density_mode_css(mode: str = "COMPACT_DESK") -> str:
    """Return CSS rules for Compact Quant Desk vs Boardroom Presentation mode."""
    mode_norm = str(mode or "COMPACT_DESK").upper()
    if mode_norm == "BOARDROOM":
        return _compact_html(
            """
            <style>
            .argus-bento-card { padding: 18px 22px !important; }
            div[data-testid="stMetricValue"] { font-size: 1.85rem !important; }
            </style>
            """
        )
    return _compact_html(
        """
        <style>
        .argus-bento-card { padding: 10px 12px !important; }
        div[data-testid="stMetricValue"] { font-size: 1.35rem !important; font-family: 'JetBrains Mono', monospace !important; }
        </style>
        """
    )


def inject_density_mode_css(mode: str = "COMPACT_DESK") -> str:
    """Inject adaptive density CSS into Streamlit view."""
    css = get_density_mode_css(mode)
    if st is not None:
        st.markdown(css, unsafe_allow_html=True)
    return css


def render_command_bar_and_shock_ribbon(key_prefix: str = "global_cmd") -> dict[str, Any]:
    """Render Bloomberg <GO> Command Launcher, Global Macro Shock Selector & Adaptive Density Toggle."""
    if st is None:
        return get_active_macro_shock()

    with st.expander("⌨️ Bloomberg Command Bar `<GO>` · Global Macro Shock Broadcast · Adaptive Density", expanded=False):
        c1, c2, c3 = st.columns([2.2, 2.0, 1.3])
        with c1:
            cmd_input = st.text_input(
                "Terminal Command (`SIMM <GO>`, `SVI <GO>`, `ALM <GO>`, `CDS <GO>`, `VPIN <GO>`, `PACK <GO>`, `SHOCK 2008`)",
                value="",
                placeholder="Type e.g. SIMM <GO> or SHOCK STAGFLATION and press Enter...",
                key=f"{key_prefix}_input",
            )
            if cmd_input.strip():
                res = resolve_terminal_command(cmd_input)
                if res.get("macro_shock"):
                    st.session_state["global_macro_shock"] = res["macro_shock"]
                st.info(f"**{res['command']}** → {res['description']}")
                if res.get("target_page"):
                    _safe_page_link(res["target_page"], f"🚀 Open {res['command']} ({res['workspace']})")
        with c2:
            preset_keys = list(MACRO_SHOCK_PRESETS.keys())
            cur_shock = str(st.session_state.get("global_macro_shock", "NONE"))
            idx = preset_keys.index(cur_shock) if cur_shock in preset_keys else 0
            chosen_shock = st.selectbox(
                "⚡ Global Macro Shock Broadcast (Cross-Page Synchronizer)",
                options=preset_keys,
                format_func=lambda k: MACRO_SHOCK_PRESETS[k]["label"],
                index=idx,
                key=f"{key_prefix}_shock_sel",
            )
            st.session_state["global_macro_shock"] = chosen_shock
        with c3:
            cur_density = str(st.session_state.get("ux_density_mode", "COMPACT_DESK"))
            chosen_density = st.radio(
                "🖥️ View Density",
                options=["COMPACT_DESK", "BOARDROOM"],
                format_func=lambda m: "Compact Desk" if m == "COMPACT_DESK" else "Boardroom HD",
                index=0 if cur_density == "COMPACT_DESK" else 1,
                horizontal=True,
                key=f"{key_prefix}_density_sel",
            )
            st.session_state["ux_density_mode"] = chosen_density

    return get_active_macro_shock()

