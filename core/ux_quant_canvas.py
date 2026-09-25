"""ARGUS Institutional Visual Quant Canvas (Release v9.18.0).

Provides interactive 3D and 2D Plotly visual storytelling charts for all Tier-1
quantitative engines:
1. Rough Bergomi + Gatheral SVI 3D Volatility Surface & Breeden-Litzenberger Density g(k)
2. ISDA SIMM v2.6 Risk-Class Waterfall, Cross-Bucket Diversification & UMR $50M Gauge
3. ALM / LDI Dual-Sided Cash-Flow Horizon (1Y-30Y) & Cumulative Surplus Trajectory
4. Single-Name CDS Survival/Hazard Term Structure & iTraxx/CDX Tranche Risk Profile
5. Avellaneda-Stoikov Reservation Price, Inventory Quote Skew & VPIN/Hawkes Toxicity
"""

from __future__ import annotations

from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.ux_institutional_hub import apply_institutional_plotly_theme


def build_svi_3d_surface_and_density_chart(
    svi_result: dict[str, Any],
    rbergomi_result: dict[str, Any] | None = None,
) -> tuple[go.Figure, go.Figure]:
    """Build 3D Arbitrage-Free Volatility Surface and 2D Smile + Butterfly Density g(k) chart."""
    params = svi_result.get("calibrated_params", {})
    a = float(params.get("a", 0.015))
    b = float(params.get("b", 0.12))
    rho = float(params.get("rho", -0.55))
    m = float(params.get("m", 0.01))
    sigma = float(params.get("sigma", 0.15))

    hurst_h = float((rbergomi_result or {}).get("hurst_h", 0.10))
    t0 = max(float(svi_result.get("maturity_years", 0.25)), 0.02)

    k_grid = np.linspace(-0.30, 0.30, 35)
    t_grid = np.linspace(0.05, 2.0, 25)
    k_mesh, t_mesh = np.meshgrid(k_grid, t_grid)

    # Blend SVI slice with rough volatility power-law term structure scaling (T / t0)^(H - 0.5)
    base_w = a + b * (rho * (k_mesh - m) + np.sqrt((k_mesh - m) ** 2 + sigma**2))
    skew_scaling = (t_mesh / t0) ** (hurst_h - 0.5)
    atm_w = a + b * ( -rho * m + np.sqrt(m**2 + sigma**2))
    w_surface = np.maximum(
        1e-5,
        (t_mesh / t0) * atm_w + (base_w - atm_w) * (t_mesh / t0) * np.clip(skew_scaling, 0.45, 2.2),
    )
    iv_surface_pct = np.sqrt(w_surface / np.maximum(t_mesh, 1e-4)) * 100.0

    fig_3d = go.Figure(
        data=[
            go.Surface(
                x=k_grid,
                y=t_grid,
                z=iv_surface_pct,
                colorscale="Viridis",
                opacity=0.92,
                colorbar={"title": "IV (%)", "len": 0.75},
                hovertemplate="Log-Strike k: %{x:.3f}<br>Maturity T: %{y:.2f}Y<br>Implied Vol: %{z:.2f}%<extra></extra>",
            )
        ]
    )
    fig_3d.update_layout(
        title=f"Rough Bergomi (H={hurst_h:.2f}) + Gatheral SVI 3D Implied Volatility Surface",
        scene={
            "xaxis_title": "Log-Moneyness k = ln(K/F)",
            "yaxis_title": "Maturity T (Years)",
            "zaxis_title": "Implied Vol (%)",
            "bgcolor": "rgba(15,23,42,0.85)",
        },
        height=440,
        margin={"l": 16, "r": 16, "t": 48, "b": 16},
        paper_bgcolor="rgba(15, 23, 42, 0.65)",
        font={"family": "Inter, JetBrains Mono, sans-serif", "color": "#e2e8f0"},
    )

    # Figure 2: 2D Smile + Durrleman / Breeden-Litzenberger Butterfly Density g(k)
    smile_rows = svi_result.get("smile_grid", [])
    if smile_rows:
        ks = [float(r["log_moneyness_k"]) for r in smile_rows]
        ivs = [float(r["svi_iv"]) * 100.0 for r in smile_rows]
        g_vals = [float(r["butterfly_g_k"]) for r in smile_rows]
        mkt_ivs = [
            float(r["market_iv"]) * 100.0 if r.get("market_iv") is not None else None
            for r in smile_rows
        ]
    else:
        ks = list(k_grid)
        w_slice = a + b * (rho * (k_grid - m) + np.sqrt((k_grid - m) ** 2 + sigma**2))
        ivs = list(np.sqrt(np.maximum(w_slice, 1e-6) / t0) * 100.0)
        g_vals = [0.25 for _ in ks]
        mkt_ivs = [None for _ in ks]

    fig_density = make_subplots(specs=[[{"secondary_y": True}]])
    fig_density.add_trace(
        go.Scatter(
            x=ks,
            y=ivs,
            mode="lines",
            name="SVI Fitted Smile (%)",
            line={"color": "#10b981", "width": 3},
        ),
        secondary_y=False,
    )
    if any(v is not None for v in mkt_ivs):
        fig_density.add_trace(
            go.Scatter(
                x=[k for k, mv in zip(ks, mkt_ivs) if mv is not None],
                y=[mv for mv in mkt_ivs if mv is not None],
                mode="markers",
                name="Market Quotes (%)",
                marker={"color": "#f59e0b", "size": 9, "symbol": "diamond"},
            ),
            secondary_y=False,
        )
    fig_density.add_trace(
        go.Scatter(
            x=ks,
            y=g_vals,
            mode="lines",
            name="Butterfly Condition g(k)",
            line={"color": "#3b82f6", "width": 2, "dash": "dot"},
            fill="tozeroy",
            fillcolor="rgba(59, 130, 246, 0.14)",
        ),
        secondary_y=True,
    )
    fig_density.add_hline(
        y=0.0,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text="No-Butterfly-Arbitrage Floor g(k) = 0",
        secondary_y=True,
    )
    fig_density.update_yaxes(title_text="Implied Volatility (%)", secondary_y=False)
    fig_density.update_yaxes(title_text="Durrleman Density g(k)", secondary_y=True)
    fig_density.update_xaxes(title_text="Log-Moneyness k = ln(K/F)")
    apply_institutional_plotly_theme(
        fig_density,
        title="SVI Implied Volatility Smile vs Breeden-Litzenberger Arbitrage-Free Density g(k)",
        height=390,
    )
    return fig_3d, fig_density


def build_isda_simm_waterfall_and_umr_chart(simm_result: dict[str, Any]) -> go.Figure:
    """Build ISDA SIMM v2.6 Risk-Class Waterfall & OTC vs CCP Cheapest-to-Clear chart."""
    breakdown = simm_result.get("risk_class_breakdown", {})
    rc_names = ["IR", "CreditQ", "CreditNonQ", "Equity", "Commodity", "FX"]
    rc_values_m = [float(breakdown.get(rc, {}).get("total_margin", 0.0)) / 1e6 for rc in rc_names]

    standalone_sum_m = float(simm_result.get("standalone_sum_eur", sum(rc_values_m) * 1e6)) / 1e6
    total_simm_m = float(simm_result.get("total_simm_im_eur", standalone_sum_m * 0.72 * 1e6)) / 1e6
    div_benefit_m = total_simm_m - standalone_sum_m  # negative number
    ccp_im_m = float(simm_result.get("ccp_cleared_im_eur", total_simm_m * 0.58 * 1e6)) / 1e6
    umr_thresh_m = float(simm_result.get("umr_threshold_eur", 50_000_000.0)) / 1e6

    fig = go.Figure(
        go.Waterfall(
            name="ISDA SIMM v2.6",
            orientation="v",
            measure=["relative"] * len(rc_names) + ["relative", "total"],
            x=rc_names + ["Cross-Bucket Div.", "Total Bilateral SIMM"],
            y=rc_values_m + [div_benefit_m, total_simm_m],
            text=[f"€{v:+.2f}M" for v in rc_values_m]
            + [f"€{div_benefit_m:+.2f}M", f"€{total_simm_m:.2f}M"],
            textposition="outside",
            increasing={"marker": {"color": "#3b82f6"}},
            decreasing={"marker": {"color": "#10b981"}},
            totals={"marker": {"color": "#f59e0b"}},
            connector={"line": {"color": "rgba(148, 163, 184, 0.4)"}},
        )
    )
    fig.add_trace(
        go.Bar(
            x=["CCP Cleared (MPOR 5d)"],
            y=[ccp_im_m],
            name="CCP Cleared IM (5d)",
            marker_color="#10b981",
            text=[f"€{ccp_im_m:.2f}M"],
            textposition="outside",
            width=[0.45],
        )
    )
    fig.add_hline(
        y=umr_thresh_m,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text=f"UMR Phase 6 Threshold (€{umr_thresh_m:.0f}M)",
        annotation_position="top left",
    )
    fig.update_yaxes(title_text="Initial Margin (€ Millions)")
    return apply_institutional_plotly_theme(
        fig,
        title="ISDA SIMM™ v2.6 Risk-Class Waterfall, Cross-Bucket Benefit & CCP Clearing Optimizer",
        height=400,
    )


def build_alm_cashflow_and_surplus_chart(alm_result: dict[str, Any]) -> go.Figure:
    """Build Dual-Sided ALM Cash-Flow Horizon (1Y-30Y) and Cumulative Surplus Trajectory."""
    schedule = alm_result.get("cashflow_schedule", [])
    if schedule:
        years = [float(r.get("year", i + 1)) for i, r in enumerate(schedule)]
        asset_cfs_m = [float(r.get("asset_cf", 0.0)) / 1e6 for r in schedule]
        liab_cfs_m = [-abs(float(r.get("liability_cf", 0.0))) / 1e6 for r in schedule]
        cum_surplus_m = [float(r.get("cumulative_surplus", 0.0)) / 1e6 for r in schedule]
    else:
        years = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0]
        asset_cfs_m = [1.1, 1.3, 1.4, 2.2, 2.5, 3.8, 4.5, 5.2, 6.5]
        liab_cfs_m = [-1.0, -1.2, -1.3, -2.0, -2.4, -3.5, -4.2, -5.0, -6.0]
        cum_surplus_m = list(np.cumsum([a + l for a, l in zip(asset_cfs_m, liab_cfs_m)]))

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=years,
            y=asset_cfs_m,
            name="Asset & LDI Bond Inflows (+€M)",
            marker_color="#10b981",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=years,
            y=liab_cfs_m,
            name="Actuarial Liability Outflows (-€M)",
            marker_color="#ef4444",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=cum_surplus_m,
            mode="lines+markers",
            name="Cumulative Net Surplus (€M)",
            line={"color": "#f59e0b", "width": 3},
            marker={"size": 7},
        ),
        secondary_y=True,
    )
    fig.update_layout(barmode="relative")
    fig.update_xaxes(title_text="Actuarial Horizon (Years)")
    fig.update_yaxes(title_text="Annual Cash Flows (€M)", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative Net Surplus (€M)", secondary_y=True)
    return apply_institutional_plotly_theme(
        fig,
        title="ALM / LDI Cash-Flow Matching Schedule (Assets vs Liabilities) & Cumulative Surplus",
        height=400,
    )


def build_cds_bootstrap_and_tranche_chart(
    cds_result: dict[str, Any],
    tranche_result: dict[str, Any],
) -> tuple[go.Figure, go.Figure]:
    """Build Bootstrapped CDS Survival/Hazard curve and Synthetic CDO Tranche Loss/Spread chart."""
    curve = cds_result.get("bootstrapped_curve", [])
    if curve:
        tenors = [float(r["tenor_years"]) for r in curve]
        surv_pct = [float(r["survival_prob_q"]) * 100.0 for r in curve]
        haz_bps = [float(r["hazard_rate_lambda"]) * 10000.0 for r in curve]
    else:
        tenors = [1.0, 3.0, 5.0, 7.0, 10.0]
        surv_pct = [99.0, 96.5, 93.2, 89.5, 84.0]
        haz_bps = [105.0, 125.0, 150.0, 165.0, 180.0]

    fig_cds = make_subplots(specs=[[{"secondary_y": True}]])
    fig_cds.add_trace(
        go.Scatter(
            x=tenors,
            y=surv_pct,
            mode="lines+markers",
            name="Survival Prob Q(t) (%)",
            line={"color": "#10b981", "width": 3},
        ),
        secondary_y=False,
    )
    fig_cds.add_trace(
        go.Bar(
            x=tenors,
            y=haz_bps,
            name="Piecewise Hazard Rate λ (bps)",
            marker_color="rgba(59, 130, 246, 0.55)",
            width=0.65,
        ),
        secondary_y=True,
    )
    fig_cds.update_xaxes(title_text="Tenor (Years)")
    fig_cds.update_yaxes(title_text="Survival Probability Q(t) (%)", secondary_y=False)
    fig_cds.update_yaxes(title_text="Hazard Rate λ (bps)", secondary_y=True)
    apply_institutional_plotly_theme(
        fig_cds,
        title="Bootstrapped Single-Name CDS Survival Curve Q(t) & Piecewise Hazard Rates λ(t)",
        height=380,
    )

    tranches = tranche_result.get("tranches", [])
    if tranches:
        t_names = [f"{r['tranche_name']} [{r['attach_pct']:.0f}-{r['detach_pct']:.0f}%]" for r in tranches]
        el_pcts = [float(r["expected_loss_pct"]) for r in tranches]
        spreads_bps = [float(r["fair_running_spread_bps"]) for r in tranches]
    else:
        t_names = ["Equity [0-3%]", "Mezzanine [3-7%]", "Senior [7-15%]", "Super-Senior [15-100%]"]
        el_pcts = [42.5, 11.2, 2.8, 0.15]
        spreads_bps = [1150.0, 310.0, 75.0, 8.5]

    fig_tranche = make_subplots(specs=[[{"secondary_y": True}]])
    fig_tranche.add_trace(
        go.Bar(
            x=t_names,
            y=el_pcts,
            name="Tranche Expected Loss (%)",
            marker_color="#ef4444",
        ),
        secondary_y=False,
    )
    fig_tranche.add_trace(
        go.Scatter(
            x=t_names,
            y=spreads_bps,
            mode="lines+markers",
            name="Fair Running Spread (bps)",
            line={"color": "#f59e0b", "width": 3},
            marker={"size": 9},
        ),
        secondary_y=True,
    )
    fig_tranche.update_yaxes(title_text="Expected Tranche Loss (%)", secondary_y=False)
    fig_tranche.update_yaxes(title_text="Fair Spread (bps)", secondary_y=True)
    apply_institutional_plotly_theme(
        fig_tranche,
        title="iTraxx / CDX Synthetic CDO Tranche Expected Loss (%) vs Fair Spread (1F Gaussian Copula)",
        height=380,
    )
    return fig_cds, fig_tranche


def build_avellaneda_stoikov_microstructure_chart(mm_result: dict[str, Any]) -> go.Figure:
    """Build Avellaneda-Stoikov Reservation Price & Optimal Bid/Ask Skew across Inventory q."""
    mid = float(mm_result.get("mid_price", 100.0))
    res_p = float(mm_result.get("reservation_price", 99.85))
    bid_p = float(mm_result.get("optimal_bid", 99.65))
    ask_p = float(mm_result.get("optimal_ask", 100.05))
    half_spread = max((ask_p - bid_p) / 2.0, 0.02)
    cur_q = float(mm_result.get("inventory_units", 0.0))
    skew_per_unit = (mid - res_p) / cur_q if abs(cur_q) > 1e-6 else 0.000015

    q_grid = np.linspace(-50_000.0, 50_000.0, 41)
    r_curve = mid - q_grid * skew_per_unit
    bid_curve = r_curve - half_spread
    ask_curve = r_curve + half_spread

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=q_grid,
            y=ask_curve,
            mode="lines",
            name="Optimal Ask Quote pᵃ(q)",
            line={"color": "#ef4444", "width": 2.5},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=q_grid,
            y=r_curve,
            mode="lines",
            name="Reservation Price r(s, q, t)",
            line={"color": "#f59e0b", "width": 2.5, "dash": "dash"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=q_grid,
            y=bid_curve,
            mode="lines",
            name="Optimal Bid Quote pᵇ(q)",
            line={"color": "#10b981", "width": 2.5},
            fill="tonexty",
            fillcolor="rgba(16, 185, 129, 0.08)",
        )
    )
    fig.add_hline(
        y=mid,
        line_dash="dot",
        line_color="#94a3b8",
        annotation_text=f"Market Mid-Price ({mid:.3f})",
    )
    fig.add_vline(
        x=cur_q,
        line_dash="dash",
        line_color="#3b82f6",
        annotation_text=f"Current Inventory q={cur_q:,.0f}",
    )
    fig.update_xaxes(title_text="Dealer Inventory Position q (Units)")
    fig.update_yaxes(title_text="Quote Price Level")
    return apply_institutional_plotly_theme(
        fig,
        title="Avellaneda-Stoikov (2008) Inventory Quote Skew & VPIN-Adjusted Bid/Ask Envelope",
        height=390,
    )
