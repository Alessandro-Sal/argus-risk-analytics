import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from core.ui_utils import inject_custom_css, metric_card, fmt_eur, section, glossary_modal, render_executive_badges
from core.sidebar import render_sidebar

st.set_page_config(page_title="Posizioni e Concentrazione | ARGUS", page_icon="📋", layout="wide")
inject_custom_css()
render_sidebar()

if "results" not in st.session_state:
    st.warning("Per favore, torna alla Home e carica un portafoglio.")
    st.stop()

results = st.session_state["results"]
pos = results["positions"]
con = results["metrics"]["concentration"]
portfolio_name = st.session_state.get("portfolio_name", "Portfolio")

st.title("📋 Posizioni, Concentrazione & Fisco")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Mappa dettagliata delle posizioni aperte, analisi dei dividendi passivi ed ottimizzazione fiscale (TUIR Art. 67).")
render_executive_badges(results["metrics"])
st.divider()

# ── STRUTTURA IN TAB ──────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📋 Posizioni & Liquidità ADV",
    "📅 Proiezione Dividendi",
    "💰 Ottimizzazione Fiscale (TUIR Art. 67)"
])

# ── TAB 1: POSIZIONI & LIQUIDITÀ ──────────────────────────────
with tab1:
    section("Concentrazione Portafoglio")

    col_c1, col_c2, col_c3 = st.columns(3)

    with col_c1:
        if con["by_asset_class_pct"]:
            st.markdown("**Per asset class**")
            fig_ac = go.Figure(go.Pie(
                labels=list(con["by_asset_class_pct"].keys()),
                values=list(con["by_asset_class_pct"].values()),
                hole=0.6,
                marker_colors=["#ff9900","#00ff66","#4361ee","#ff3333","#9b59b6"]
            ))
            fig_ac.update_layout(
                template="plotly_dark", height=300,
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                margin=dict(l=0, r=0, t=10, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_ac, use_container_width=True)

    with col_c2:
        if con["by_gics_sector_pct"]:
            st.markdown("**Per settore GICS**")
            fig_sec = go.Figure(go.Pie(
                labels=list(con["by_gics_sector_pct"].keys()),
                values=list(con["by_gics_sector_pct"].values()),
                hole=0.6,
            ))
            fig_sec.update_layout(
                template="plotly_dark", height=300,
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                margin=dict(l=0, r=0, t=10, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_sec, use_container_width=True)

    with col_c3:
        if con["by_country_pct"]:
            st.markdown("**Per paese**")
            fig_geo = go.Figure(go.Pie(
                labels=list(con["by_country_pct"].keys()),
                values=list(con["by_country_pct"].values()),
                hole=0.6,
            ))
            fig_geo.update_layout(
                template="plotly_dark", height=300,
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
                margin=dict(l=0, r=0, t=10, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_geo, use_container_width=True)

    hh1, hh2 = st.columns([1, 1.2])
    with hh1:
        metric_card(
            "Indice Herfindahl-Hirschman (HHI)",
            f"{con['hhi']:.4f}",
            positive=con["hhi"] < 0.15,
            help_text="Indice di concentrazione del portafoglio calcolato sui pesi di mercato."
        )
        metric_card(
            "Posizioni attive",
            str(con["n_active_positions"]),
            help_text="Conteggio del numero di strumenti finanziari posseduti in modo netto."
        )
        metric_card(
            "Diversification Ratio",
            f"{con.get('diversification_ratio', 1.0):.2f}",
            positive=con.get("diversification_ratio", 1.0) >= 1.20,
            help_text="Rapporto tra la media ponderata delle volatilità dei singoli asset e la volatilità totale."
        )

    with hh2:
        st.markdown("**Top 10 Posizioni**")
        if not pos.empty and "current_value" in pos.columns and "weight_pct" in pos.columns:
            pos_sorted = pos[pos["qty_net"] > 0].sort_values("current_value", ascending=False).head(10)
            df_top10 = pos_sorted[["ticker", "current_value", "weight_pct"]].rename(columns={
                "ticker": "Ticker",
                "current_value": "Valore",
                "weight_pct": "Peso %"
            })
            top10_col_config = {
                "Valore": st.column_config.NumberColumn("Valore", format="€ %.2f"),
                "Peso %": st.column_config.ProgressColumn(
                    "Peso %",
                    format="%.2f%%",
                    min_value=0,
                    max_value=float(df_top10["Peso %"].max()) if not df_top10.empty else 100,
                )
            }
            st.dataframe(df_top10, use_container_width=True, hide_index=True, column_config=top10_col_config)

    st.divider()
    section("Dettaglio Posizioni & Rischio Liquidità ADV")

    if not pos.empty:
        df_l = pos[pos["qty_net"] > 0].copy()
        
        display_cols = [
            "ticker", "asset_class", "sector", "country", "qty_net",
            "wacp", "last_price", "current_value", "weight_pct",
            "pnl_realized", "pnl_unrealized", "days_to_liquidate", "yield_on_cost_pct"
        ]
        valid_cols = [c for c in display_cols if c in df_l.columns]
        df_disp = df_l[valid_cols].copy()
        
        col_renames = {
            "ticker": "Ticker", "asset_class": "Asset Class", "sector": "Settore",
            "country": "Paese", "qty_net": "Quantità", "wacp": "Prezzo Carico (€)",
            "last_price": "Prezzo Mkt (€)", "current_value": "Controvalore (€)",
            "weight_pct": "Peso (%)", "pnl_realized": "PnL Realizz. (€)",
            "pnl_unrealized": "PnL Latente (€)", "days_to_liquidate": "Giorni Liq. (ADV 15%)",
            "yield_on_cost_pct": "Yield on Cost (%)"
        }
        df_disp.rename(columns=col_renames, inplace=True)

        column_config = {
            "Prezzo Carico (€)": st.column_config.NumberColumn("Prezzo Carico (€)", format="€ %.2f"),
            "Prezzo Mkt (€)": st.column_config.NumberColumn("Prezzo Mkt (€)", format="€ %.2f"),
            "Controvalore (€)": st.column_config.NumberColumn("Controvalore (€)", format="€ %.2f"),
            "PnL Realizz. (€)": st.column_config.NumberColumn("PnL Realizz. (€)", format="€ %.2f"),
            "PnL Latente (€)": st.column_config.NumberColumn("PnL Latente (€)", format="€ %.2f"),
            "Peso (%)": st.column_config.NumberColumn("Peso (%)", format="%.2f%%"),
            "Giorni Liq. (ADV 15%)": st.column_config.NumberColumn("Giorni Liq. (ADV 15%)", format="%.2f gg"),
            "Yield on Cost (%)": st.column_config.NumberColumn("Yield on Cost (%)", format="%.2f%%")
        }

        st.dataframe(df_disp, use_container_width=True, hide_index=True, column_config=column_config)

        st.markdown("#### Ripartizione Liquidità del Portafoglio (ADV Days)")
        t1 = df_l[df_l["days_to_liquidate"] <= 1.0]["current_value"].sum()
        t2 = df_l[(df_l["days_to_liquidate"] > 1.0) & (df_l["days_to_liquidate"] <= 5.0)]["current_value"].sum()
        t3 = df_l[df_l["days_to_liquidate"] > 5.0]["current_value"].sum()
        
        fig_liq = go.Figure(go.Bar(
            x=["< 1 Giorno (Ultra-Liquido)", "1 - 5 Giorni (Moderato)", "> 5 Giorni (Illiquido)"],
            y=[t1, t2, t3],
            marker_color=["#00ff66", "#ff9900", "#ff3333"]
        ))
        fig_liq.update_layout(
            title="Controvalore (€) per Classe di Smobilizzo",
            template="plotly_dark", height=320,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_liq, use_container_width=True)

# ── TAB 2: PROIEZIONE DIVIDENDI ───────────────────────────────
with tab2:
    section("💰 Proiezione Flusso di Cassa & Dividendi (12 Mesi)")
    st.caption("Stima del flusso di cassa generato dai dividendi delle posizioni in portafoglio e storico degli incassi reali.")

    from core.dividend_engine import compute_dividend_forecast
    div_data = compute_dividend_forecast(pos)

    total_div_eur = div_data.get("total_annual_dividends_eur", 0.0)
    hist_div_eur = div_data.get("historical_dividends_total_eur", 0.0)
    port_yield_pct = div_data.get("portfolio_yield_pct", 0.0)
    df_div_m = div_data.get("monthly_forecast", pd.DataFrame())
    df_div_b = div_data.get("dividend_breakdown", pd.DataFrame())

    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        st.metric("Dividendi Annui Stimati", f"€ {total_div_eur:,.2f}")
    with col_d2:
        st.metric("Dividend Yield Medio Portafoglio", f"{port_yield_pct:.2f}%")
    with col_d3:
        st.metric("Dividendi Storici Incassati", f"€ {hist_div_eur:,.2f}")

    if not df_div_m.empty:
        m_col = "month_name" if "month_name" in df_div_m.columns else ("month" if "month" in df_div_m.columns else df_div_m.columns[0])
        p_col = "projected_payout_eur" if "projected_payout_eur" in df_div_m.columns else ("estimated_payout_eur" if "estimated_payout_eur" in df_div_m.columns else df_div_m.columns[1])
        
        col_dg1, col_dg2 = st.columns([1.5, 1])
        with col_dg1:
            st.markdown("**Stagionalità Proiettata (Flusso Mensile in Euro)**")
            fig_div_m = go.Figure(go.Bar(
                x=df_div_m[m_col],
                y=df_div_m[p_col],
                marker_color="#3fb950",
                text=[f"€ {val:,.2f}" if val > 0 else "" for val in df_div_m[p_col]],
                textposition="auto"
            ))
            fig_div_m.update_layout(
                template="plotly_dark", height=320,
                xaxis_title="Mese", yaxis_title="Incasso Stimato (€)",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_div_m, use_container_width=True)

        with col_dg2:
            st.markdown("**Top Società Pagatrici**")
            if not df_div_b.empty:
                b_payout_col = "annual_payout_eur" if "annual_payout_eur" in df_div_b.columns else ("estimated_annual_dividend_eur" if "estimated_annual_dividend_eur" in df_div_b.columns else df_div_b.columns[-1])
                yoc_col = "yield_on_cost_pct" if "yield_on_cost_pct" in df_div_b.columns else df_div_b.columns[1]
                
                df_top_div = df_div_b.copy()
                df_top_div[b_payout_col] = pd.to_numeric(df_top_div[b_payout_col], errors="coerce").fillna(0.0)
                df_top_div[yoc_col] = pd.to_numeric(df_top_div[yoc_col], errors="coerce").fillna(0.0)
                
                df_top_sorted = df_top_div.sort_values(b_payout_col, ascending=False).head(5)
                df_top_disp = df_top_sorted[["ticker", yoc_col, b_payout_col]].rename(columns={
                    "ticker": "Ticker", yoc_col: "Yield on Cost %", b_payout_col: "Stima Annua (€)"
                })
                
                div_col_config = {
                    "Stima Annua (€)": st.column_config.NumberColumn("Stima Annua (€)", format="€ %.2f"),
                    "Yield on Cost %": st.column_config.NumberColumn("Yield on Cost %", format="%.2f%%")
                }
                st.dataframe(df_top_disp, use_container_width=True, hide_index=True, column_config=div_col_config)

# ── TAB 3: OTTIMIZZAZIONE FISCALE ─────────────────────────────
with tab3:
    section("💰 Ottimizzazione Fiscale & Tax-Loss Harvesting")
    st.caption("Analisi delle plusvalenze realizzate, della stima delle imposte (aliquote 26% / 12.5%) ed opportunità di Tax-Loss Harvesting per la riduzione del debito fiscale.")

    import importlib
    import core.tax_engine
    importlib.reload(core.tax_engine)
    from core.tax_engine import compute_tax_and_harvesting

    engine = st.session_state.get("db_engine", None)
    if engine is None:
        try:
            from core.fetcher import get_engine
            engine = get_engine("root", "root", "localhost", 3306, "wealth")
        except Exception:
            engine = None

    selected_year = st.selectbox(
        "📅 Seleziona Anno Fiscale da Analizzare:",
        options=["Tutti gli Anni", 2026, 2025, 2024, 2023, 2022, 2021],
        index=0,
        help="Filtra l'analisi delle plusvalenze realizzate e delle imposte stimate per un singolo anno solare."
    )

    tax_year_param = None if selected_year == "Tutti gli Anni" else int(selected_year)
    tax_res = compute_tax_and_harvesting(results, db_engine=engine, tax_year=tax_year_param)
    tax_sum = tax_res["summary"]
    tax_harv = tax_res["harvesting_candidates"]
    tax_by_year = tax_res.get("tax_by_year", pd.DataFrame())

    col_tx1, col_tx2, col_tx3, col_tx4 = st.columns(4)
    with col_tx1:
        st.metric(
            f"Plusvalenze Realizzate ({selected_year})",
            f"€ {tax_sum['total_realized_gain_eur']:,.2f}",
            delta=f"Diversi: € {tax_sum['total_realized_gain_diversi_eur']:,.2f} | ETF: € {tax_sum['total_realized_gain_etf_eur']:,.2f}"
        )
    with col_tx2:
        st.metric(
            f"Minusvalenze Realizzate ({selected_year})",
            f"€ {tax_sum['total_realized_loss_eur']:,.2f}",
            delta="Inviate a Zainetto Fiscale", delta_color="inverse"
        )
    with col_tx3:
        st.metric(
            f"Stima Imposte Dovute ({selected_year})",
            f"€ {tax_sum['estimated_tax_due_eur']:,.2f}",
            delta="Aliquote 26% / 12.5%", delta_color="inverse"
        )
    with col_tx4:
        st.metric(
            "Zainetto Fiscale Residuo",
            f"€ {tax_sum['tax_credit_zainetto_eur']:,.2f}",
            help="Minusvalenze pregresse compensabili entro 4 anni."
        )

    st.markdown("#### 💡 Candidati Tax-Loss Harvesting (Riduzione Debito Fiscale)")
    if not tax_harv.empty:
        st.dataframe(
            tax_harv.style.format({
                "pnl_unrealized": "€ {:,.2f}",
                "potential_tax_saving_eur": "€ {:,.2f}"
            }),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Nessuna posizione in perdita latente compensabile individuata.")

    if not tax_by_year.empty:
        st.markdown("#### 📊 Dettaglio Imposte & Plusvalenze per Anno Solare")
        fig_tax_y = px.bar(
            tax_by_year, x="year", y=["realized_gain_eur", "realized_loss_eur", "estimated_tax_eur"],
            barmode="group", title="Storico Fiscale Anno per Anno (€)",
            labels={"value": "Euro (€)", "year": "Anno Solare", "variable": "Voce Fiscale"},
            template="plotly_dark", height=350
        )
        fig_tax_y.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_tax_y, use_container_width=True)
