import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import importlib
import core.ui_utils
import core.risk_engine
importlib.reload(core.ui_utils)
importlib.reload(core.risk_engine)
from core.ui_utils import inject_custom_css, metric_card, fmt_eur, section, glossary_modal, render_executive_badges, render_command_bar, render_segmented_tabs, apply_plotly_theme, ensure_risk_bundle_loaded, render_sandbox_banner
from core.sidebar import render_sidebar

st.set_page_config(page_title="Posizioni e Concentrazione | ARGUS", page_icon="📋", layout="wide")
inject_custom_css()
render_sidebar()
render_command_bar()

results, has_real = ensure_risk_bundle_loaded()
pos = results.get("positions", pd.DataFrame())
con = results.get("metrics", {}).get("concentration", {})
portfolio_name = st.session_state.get("portfolio_name", results.get("sandbox_name", "Portfolio"))

render_sandbox_banner(page_key="p4")

st.title("📋 Posizioni, Concentrazione & Fisco")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Mappa dettagliata delle posizioni aperte, analisi dei dividendi passivi ed ottimizzazione fiscale (TUIR Art. 67).")
elif results.get("is_sandbox"):
    st.caption(f"🧪 Modalità Sandbox Attiva: **{results.get('sandbox_name', 'Benchmark Demo')}** ({len(pos)} asset) • Capitale Simulato: **$100,000**")
render_executive_badges(results.get("metrics", {}))
st.divider()

# ── STRUTTURA IN TAB CON LAZY LOADING ──────────────────────────
active_pos_tab = render_segmented_tabs([
    "📋 Posizioni Attive & Costi FIFO",
    "📅 Proiezione Dividendi",
    "💰 Ottimizzazione Fiscale (TUIR Art. 67)",
    "⚡ Impatto di Mercato (Almgren-Chriss)"
], key="positions_active_tab")

# ── TAB 1: POSIZIONI & LIQUIDITÀ ──────────────────────────────
if active_pos_tab == "📋 Posizioni Attive & Costi FIFO":
    section("Concentrazione Portafoglio")

    col_c1, col_c2, col_c3 = st.columns(3)

    with col_c1:
        if con.get("by_asset_class_pct"):
            st.markdown("**Per Asset Class**")
            ac_labels = [str(k).upper() if str(k).lower() in ["etf", "fx"] else str(k).title() for k in con["by_asset_class_pct"].keys()]
            fig_ac = go.Figure(go.Pie(
                labels=ac_labels,
                values=list(con["by_asset_class_pct"].values()),
                hole=0.62,
                marker=dict(
                    colors=["#00e676", "#58a6ff", "#bc8cff", "#ff9900", "#f85149"],
                    line=dict(color="#0d1117", width=2)
                ),
                textposition='inside',
                textinfo='percent',
                insidetextorientation='horizontal',
                textfont=dict(size=11, color='#ffffff'),
                hovertemplate="<b>Asset Class: %{label}</b><br>Peso: <b>%{percent}</b><extra></extra>"
            ))
            fig_ac.update_layout(
                template="plotly_dark", height=310,
                legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5, font=dict(size=10, color="#ffffff")),
                margin=dict(l=10, r=10, t=10, b=25),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_ac)
            st.plotly_chart(fig_ac, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    with col_c2:
        if con.get("by_gics_sector_pct"):
            st.markdown("**Per Settore GICS**")
            fig_sec = go.Figure(go.Pie(
                labels=list(con["by_gics_sector_pct"].keys()),
                values=list(con["by_gics_sector_pct"].values()),
                hole=0.62,
                marker=dict(
                    colors=["#58a6ff", "#3fb950", "#ff9900", "#f85149", "#bc8cff", "#00f3ff", "#d29922", "#f0883e"],
                    line=dict(color="#0d1117", width=2)
                ),
                textposition='inside',
                textinfo='percent',
                insidetextorientation='horizontal',
                textfont=dict(size=11, color='#ffffff'),
                hovertemplate="<b>Settore: %{label}</b><br>Peso: <b>%{percent}</b><extra></extra>"
            ))
            fig_sec.update_layout(
                template="plotly_dark", height=310,
                legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5, font=dict(size=10, color="#ffffff")),
                margin=dict(l=10, r=10, t=10, b=25),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_sec)
            st.plotly_chart(fig_sec, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    with col_c3:
        if con.get("by_country_pct"):
            st.markdown("**Per Paese**")
            fig_geo = go.Figure(go.Pie(
                labels=list(con["by_country_pct"].keys()),
                values=list(con["by_country_pct"].values()),
                hole=0.62,
                marker=dict(
                    colors=["#58a6ff", "#3fb950", "#ff9900", "#f85149", "#bc8cff", "#00f3ff", "#d29922", "#f0883e"],
                    line=dict(color="#0d1117", width=2)
                ),
                textposition='inside',
                textinfo='percent',
                insidetextorientation='horizontal',
                textfont=dict(size=11, color='#ffffff'),
                hovertemplate="<b>Paese: %{label}</b><br>Peso: <b>%{percent}</b><extra></extra>"
            ))
            fig_geo.update_layout(
                template="plotly_dark", height=310,
                legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5, font=dict(size=10, color="#ffffff")),
                margin=dict(l=10, r=10, t=10, b=25),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_geo)
            st.plotly_chart(fig_geo, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    hh1, hh2 = st.columns([1, 1.2])
    with hh1:
        hhi_val = con.get("hhi", 0.0)
        metric_card(
            "Indice Herfindahl-Hirschman (HHI)",
            f"{hhi_val:.4f}",
            positive=hhi_val < 0.15,
            help_text="Indice di concentrazione del portafoglio calcolato sui pesi di mercato."
        )
        metric_card(
            "Posizioni attive",
            str(con.get("n_active_positions", len(pos))),
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
            pos_active = pos[pos["qty_net"] > 0] if "qty_net" in pos.columns else (pos[pos["current_value"] > 0] if "current_value" in pos.columns else pos)
            pos_sorted = pos_active.sort_values("current_value", ascending=False).head(10)
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
        df_l = pos[pos["qty_net"] > 0].copy() if "qty_net" in pos.columns else pos.copy()
        if "days_to_liquidate" not in df_l.columns:
            df_l["days_to_liquidate"] = 0.5
        if "current_value" not in df_l.columns:
            df_l["current_value"] = 0.0
        
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
            marker=dict(
                color=["#00e676", "#ff9900", "#f85149"],
                line=dict(color="#0d1117", width=1)
            ),
            text=[f"€ {val:,.2f}" if val > 0 else "" for val in [t1, t2, t3]],
            textposition="auto"
        ))
        fig_liq.update_layout(
            title="Controvalore (€) per Classe di Smobilizzo",
            template="plotly_dark", height=320,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_liq, use_container_width=True)

# ── TAB 2: PROIEZIONE DIVIDENDI ───────────────────────────────
elif active_pos_tab == "📅 Proiezione Dividendi":
    section("💰 Proiezione Flusso di Cassa & Calendario Dividendi (12 Mesi)")
    st.caption("Analisi previsionale dettagliata dei flussi di cassa da cedole e dividendi: scopri chi paga, i mesi di stacco, la frequenza e gli importi stimati per ciascuna posizione.")

    import importlib
    import core.dividend_engine
    importlib.reload(core.dividend_engine)
    from core.dividend_engine import compute_dividend_forecast
    div_data = compute_dividend_forecast(pos)

    total_div_eur = div_data.get("total_annual_dividends_eur", 0.0)
    hist_div_eur = div_data.get("historical_dividends_total_eur", 0.0)
    port_yield_pct = div_data.get("portfolio_yield_pct", 0.0)
    monthly_avg_eur = div_data.get("monthly_average_eur", 0.0)
    df_div_m = div_data.get("monthly_forecast", pd.DataFrame())
    df_div_b = div_data.get("dividend_breakdown", pd.DataFrame())
    df_events = div_data.get("calendar_events", pd.DataFrame())
    df_matrix = div_data.get("monthly_matrix", pd.DataFrame())

    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        metric_card("Dividendi Annui Stimati", f"€ {total_div_eur:,.2f}", "Proiezione Cash Flow", True)
    with col_d2:
        metric_card("Media Mensile Stimata", f"€ {monthly_avg_eur:,.2f}", "Flusso Medio / Mese", True)
    with col_d3:
        metric_card("Dividend Yield Medio", f"{port_yield_pct:.2f}%", "Rendimento da Dividendi", True)
    with col_d4:
        metric_card("Dividendi Storici", f"€ {hist_div_eur:,.2f}", "Totale Già Incassato", True)

    st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

    if not df_div_m.empty:
        col_chart, col_focus = st.columns([1.6, 1.1])
        
        with col_chart:
            st.markdown("##### 📊 Stagionalità Proiettata (Flusso Mensile in Euro)")
            
            # Hover ricco con l'elenco delle società pagatrici
            hover_texts = []
            for _, r in df_div_m.iterrows():
                p_eur = r['projected_payout_eur']
                paying_str = r['paying_companies']
                if p_eur > 0:
                    hover_texts.append(f"<b>{r['month_name']}</b><br>Incasso Totale: <b>€ {p_eur:,.2f}</b><br><br><b>Società Pagatrici:</b><br>{paying_str}")
                else:
                    hover_texts.append(f"<b>{r['month_name']}</b><br>Nessun dividendo previsto")

            max_payout = float(df_div_m["projected_payout_eur"].max()) if not df_div_m.empty else 100.0
            
            fig_div_m = go.Figure(go.Bar(
                x=df_div_m["month_name"],
                y=df_div_m["projected_payout_eur"],
                marker=dict(
                    color=["#3fb950" if v > 0 else "rgba(255,255,255,0.08)" for v in df_div_m["projected_payout_eur"]],
                    line=dict(color="#0d1117", width=1)
                ),
                text=[f"€ {val:,.2f}" if val > 0 else "" for val in df_div_m["projected_payout_eur"]],
                textposition="outside",
                textfont=dict(size=11, color="#ffffff"),
                cliponaxis=False,
                hovertext=hover_texts,
                hoverinfo="text"
            ))
            fig_div_m.update_layout(
                template="plotly_dark", height=320,
                xaxis_title="Mese dell'Anno",
                yaxis=dict(title="Incasso Previsto (€)", range=[0, max_payout * 1.25]),
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            apply_plotly_theme(fig_div_m)
            st.plotly_chart(fig_div_m, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        with col_focus:
            st.markdown("##### 🔍 Chi Paga per Singolo Mese")
            
            month_options = ["Tutti i Mesi con Incassi", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
            selected_m = st.selectbox("Seleziona Mese da Ispezionare:", options=month_options, index=0, key="select_div_month_focus")
            
            if selected_m == "Tutti i Mesi con Incassi":
                if not df_events.empty and "month_num" in df_events.columns and "installment_payout_eur" in df_events.columns:
                    active_events = df_events.sort_values(by=["month_num", "installment_payout_eur"], ascending=[True, False])
                    df_disp_ev = active_events[["month_name", "ticker", "installment_payout_eur", "annual_payout_eur"]].rename(columns={
                        "month_name": "Mese", "ticker": "Asset", "installment_payout_eur": "Stacco", "annual_payout_eur": "Tot. Annuo"
                    })
                    st.dataframe(
                        df_disp_ev.style.format({"Stacco": "€ {:.2f}", "Tot. Annuo": "€ {:.2f}"}),
                        use_container_width=True, hide_index=True, height=240
                    )
                else:
                    st.info("Nessun dividendo previsto nel portafoglio.")
            else:
                m_num = month_options.index(selected_m)
                if not df_events.empty and "month_num" in df_events.columns:
                    m_events = df_events[df_events["month_num"] == m_num].sort_values(by="installment_payout_eur", ascending=False)
                else:
                    m_events = pd.DataFrame()

                if not m_events.empty:
                    tot_m = m_events["installment_payout_eur"].sum()
                    st.success(f"🗓️ **{selected_m}**: Incasso Totale Stimato di **€ {tot_m:,.2f}**")
                    df_disp_ev = m_events[["ticker", "dividend_yield_pct", "installment_payout_eur", "annual_payout_eur"]].rename(columns={
                        "ticker": "Asset", "dividend_yield_pct": "Yield %", "installment_payout_eur": "Stacco", "annual_payout_eur": "Tot. Annuo"
                    })
                    st.dataframe(
                        df_disp_ev.style.format({"Yield %": "{:.2f}%", "Stacco": "€ {:.2f}", "Tot. Annuo": "€ {:.2f}"}),
                        use_container_width=True, hide_index=True, height=200
                    )
                else:
                    st.info(f"ℹ️ Nessun titolo in portafoglio prevede stacchi di dividendo nel mese di **{selected_m}**.")

    # ── TABELLA COMPLETA: CALENDARIO E PIANO STACCHI PER ASSET ────────
    st.divider()
    st.markdown("#### 📋 Calendario Completo Dividendi: Chi Paga, Quando e Quanto")
    st.caption("Riepilogo analitico per ciascun asset in portafoglio: frequenza di distribuzione, mesi previsti di accredito e stima dell'importo per singolo stacco.")

    if not df_div_b.empty:
        paying_assets = df_div_b[df_div_b["annual_payout_eur"] > 0].copy()
        if not paying_assets.empty:
            # Fallback sicuro per colonne
            default_cols = {
                "dividend_yield_pct": 0.0,
                "yield_on_cost_pct": 0.0,
                "frequency": "Trimestrale (4x)",
                "payout_months_str": "Mar, Giu, Set, Dic",
                "installment_payout_eur": 0.0,
                "annual_payout_eur": 0.0,
                "historical_payout_eur": 0.0
            }
            for col_name, def_val in default_cols.items():
                if col_name not in paying_assets.columns:
                    paying_assets[col_name] = def_val

            df_table_show = paying_assets[[
                "ticker", "dividend_yield_pct", "yield_on_cost_pct", "frequency", 
                "payout_months_str", "installment_payout_eur", "annual_payout_eur", "historical_payout_eur"
            ]].rename(columns={
                "ticker": "Asset / Ticker",
                "dividend_yield_pct": "Dividend Yield",
                "yield_on_cost_pct": "Yield on Cost (YOC)",
                "frequency": "Frequenza",
                "payout_months_str": "Mesi di Stacco Stimati",
                "installment_payout_eur": "Incasso per Singolo Stacco",
                "annual_payout_eur": "Stima Totale Annua",
                "historical_payout_eur": "Storico Incassato Reale"
            })

            div_table_config = {
                "Dividend Yield": st.column_config.NumberColumn("Dividend Yield", format="%.2f%%"),
                "Yield on Cost (YOC)": st.column_config.NumberColumn("Yield on Cost (YOC)", format="%.2f%%"),
                "Incasso per Singolo Stacco": st.column_config.NumberColumn("Incasso per Singolo Stacco", format="€ %.2f"),
                "Stima Totale Annua": st.column_config.NumberColumn("Stima Totale Annua", format="€ %.2f"),
                "Storico Incassato Reale": st.column_config.NumberColumn("Storico Incassato Reale", format="€ %.2f")
            }

            st.dataframe(df_table_show, use_container_width=True, hide_index=True, column_config=div_table_config)
        else:
            st.info("Nessuna posizione in portafoglio genera dividendi o cedole attive.")

    # ── MATRICE MENSILE DISTRIBUZIONE DIVIDENDI ──────────────────────
    if not df_matrix.empty:
        with st.expander("🗓️ Visualizza la Matrice Annuale Completa (Incassi Titolo per Mese)", expanded=False):
            st.caption("Importo monetario stimato (€) per ciascun mese dell'anno solare:")
            matrix_config = {
                "Yield %": st.column_config.NumberColumn("Yield %", format="%.2f%%"),
                "Totale Annuo (€)": st.column_config.NumberColumn("Totale Annuo (€)", format="€ %.2f")
            }
            for m_l in ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]:
                matrix_config[m_l] = st.column_config.NumberColumn(m_l, format="€ %.2f")

            st.dataframe(df_matrix, use_container_width=True, hide_index=True, column_config=matrix_config)

# ── TAB 3: OTTIMIZZAZIONE FISCALE ─────────────────────────────
elif active_pos_tab == "💰 Ottimizzazione Fiscale (TUIR Art. 67)":
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
        sub_txt = f"Div: € {tax_sum['total_realized_gain_diversi_eur']:,.0f} | ETF: € {tax_sum['total_realized_gain_etf_eur']:,.0f}"
        metric_card(f"Plusvalenze ({selected_year})", f"€ {tax_sum['total_realized_gain_eur']:,.2f}", sub_txt, True)
    with col_tx2:
        metric_card(f"Minusvalenze ({selected_year})", f"€ {tax_sum['total_realized_loss_eur']:,.2f}", "Inviate a Zainetto Fiscale", False)
    with col_tx3:
        metric_card(f"Stima Imposte ({selected_year})", f"€ {tax_sum['estimated_tax_due_eur']:,.2f}", "Aliquote 26% / 12.5%", False)
    with col_tx4:
        metric_card("Zainetto Residuo", f"€ {tax_sum['tax_credit_zainetto_eur']:,.2f}", "Compensabile in 4 Anni", True)

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    st.markdown("#### 💡 Candidati Tax-Loss Harvesting (Riduzione Debito Fiscale)")
    if not tax_harv.empty:
        df_harv_disp = tax_harv.copy()
        if "asset_class" in df_harv_disp.columns:
            df_harv_disp["asset_class"] = df_harv_disp["asset_class"].apply(
                lambda x: str(x).upper() if str(x).lower() in ["etf", "fx"] else str(x).title()
            )
        df_harv_disp = df_harv_disp.rename(columns={
            "ticker": "Ticker",
            "asset_class": "Classe Asset",
            "pnl_unrealized": "PnL Non Realizzato (€)",
            "potential_tax_saving_eur": "Risparmio Fiscale Potenziale (€)",
            "tax_rate_pct": "Aliquota Fiscale %",
            "qualifying_type": "Tipologia Reddito (TUIR)"
        })
        
        format_dict = {}
        for col, fmt in [
            ("PnL Non Realizzato (€)", "€ {:,.2f}"),
            ("Risparmio Fiscale Potenziale (€)", "€ {:,.2f}"),
            ("Aliquota Fiscale %", "{:.1f}%")
        ]:
            if col in df_harv_disp.columns:
                df_harv_disp[col] = pd.to_numeric(
                    df_harv_disp[col].astype(str).str.replace("%", "").str.replace("€", "").str.strip(),
                    errors="coerce"
                ).fillna(0.0)
                format_dict[col] = fmt

        st.dataframe(
            df_harv_disp.style.format(format_dict) if format_dict else df_harv_disp,
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Nessuna posizione in perdita latente compensabile individuata.")

    if not tax_by_year.empty:
        st.markdown("##### 📊 Dettaglio Imposte & Plusvalenze per Anno Solare (€)")
        
        df_tax_chart = tax_by_year.rename(columns={
            "year": "Anno Solare",
            "realized_gain_eur": "Plusvalenze Realizzate (€)",
            "realized_loss_eur": "Minusvalenze Realizzate (€)",
            "estimated_tax_eur": "Stima Imposte Dovute (€)"
        })
        
        fig_tax_y = px.bar(
            df_tax_chart, x="Anno Solare", 
            y=["Plusvalenze Realizzate (€)", "Minusvalenze Realizzate (€)", "Stima Imposte Dovute (€)"],
            barmode="group",
            labels={"value": "Euro (€)", "Anno Solare": "", "variable": ""},
            color_discrete_map={
                "Plusvalenze Realizzate (€)": "#58a6ff",
                "Minusvalenze Realizzate (€)": "#f85149",
                "Stima Imposte Dovute (€)": "#00e676"
            },
            template="plotly_dark", height=370
        )
        fig_tax_y.update_traces(
            hovertemplate="<b>Anno %{x}</b><br>%{fullData.name}: <b>€ %{y:,.2f}</b><extra></extra>"
        )
        fig_tax_y.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=35, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, title=None)
        )
        st.plotly_chart(fig_tax_y, use_container_width=True, config={"displayModeBar": False})

        # Tabella Dettagliata Anno per Anno con deduzioni e base imponibile trasparente
        cols_present = [c for c in [
            "year", "realized_gain_diversi_eur", "realized_gain_etf_eur", "realized_loss_eur",
            "prior_minus_deducted_eur", "taxable_base_eur", "estimated_tax_due_eur", "tax_credit_zainetto_eur"
        ] if c in tax_by_year.columns]
        
        df_tax_show = tax_by_year[cols_present].rename(columns={
            "year": "Anno Solare",
            "realized_gain_diversi_eur": "Plusv. Azioni/Bond (€)",
            "realized_gain_etf_eur": "Plusv. ETF (€)",
            "realized_loss_eur": "Minusv. Realizzate (€)",
            "prior_minus_deducted_eur": "Minusv. Dedotte (€)",
            "taxable_base_eur": "Base Imponibile (€)",
            "estimated_tax_due_eur": "Imposta Dovuta (€)",
            "tax_credit_zainetto_eur": "Zainetto Residuo (€)"
        })
        
        st.dataframe(
            df_tax_show.style.format({c: "€ {:,.2f}" for c in df_tax_show.columns if c != "Anno Solare"}),
            use_container_width=True, hide_index=True
        )

    # ── TIMELINE ZAINETTO FISCALE MULTIANNO (TUIR ART. 68 C. 5) ──
    df_zainetto = tax_res.get("zainetto_timeline", pd.DataFrame())
    if not df_zainetto.empty:
        st.divider()
        st.markdown("#### ⏳ Timeline Zainetto Fiscale & Scadenze Quadriennali (TUIR Art. 68 c. 5)")
        st.caption("Tracciamento delle minusvalenze pregresse con scadenza quadriennale (compensabili entro il 31 dicembre del 4° anno successivo alla realizzazione).")

        tot_active_credit = float(df_zainetto["residual_active_eur"].sum())
        expiring_soon = df_zainetto[df_zainetto["urgency"].isin(["CRITICAL", "HIGH"])]
        tot_expiring_soon = float(expiring_soon["residual_active_eur"].sum()) if not expiring_soon.empty else 0.0
        tot_compensated = float(df_zainetto["compensated_eur"].sum())
        tax_saved_realized = tot_compensated * 0.26

        col_z_kpi1, col_z_kpi2, col_z_kpi3 = st.columns(3)
        with col_z_kpi1:
            metric_card("Credito Fiscale Attivo", f"€ {tot_active_credit:,.2f}", "Zainetto Disponibile", True)
        with col_z_kpi2:
            sub_scad = "Nessuna Scadenza Imminente" if tot_expiring_soon <= 0 else "Priorità di Recupero"
            metric_card("In Scadenza (12-24M)", f"€ {tot_expiring_soon:,.2f}", sub_scad, tot_expiring_soon <= 0)
        with col_z_kpi3:
            metric_card("Minusvalenze Compensate", f"€ {tot_compensated:,.2f}", f"Risparmio: € {tax_saved_realized:,.2f}", True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        st.markdown("##### 📦 Stato dei Bucket di Minusvalenze per Anno di Origine (€)")

        # Grafico Timeline a Barre Orizzontali / Raggruppate delle Scadenze
        df_z_plot = df_zainetto.copy()
        df_z_plot["Anno Origine (Scadenza)"] = df_z_plot.apply(lambda r: f"Origine {r['origin_year']} (Scade {r['expiry_year']})", axis=1)

        fig_z_timeline = px.bar(
            df_z_plot,
            x="Anno Origine (Scadenza)",
            y=["residual_active_eur", "compensated_eur", "expired_eur"],
            labels={
                "value": "Euro (€)",
                "variable": "",
                "Anno Origine (Scadenza)": ""
            },
            color_discrete_map={
                "residual_active_eur": "#ff9900",
                "compensated_eur": "#3fb950",
                "expired_eur": "#f85149"
            },
            barmode="stack",
            template="plotly_dark",
            height=370
        )
        
        # Rinominazione leggenda pulita senza duplicati di simboli
        legend_names = {
            "residual_active_eur": "Residuo Attivo Compensabile",
            "compensated_eur": "Già Compensato",
            "expired_eur": "Prescritto / Scaduto"
        }
        fig_z_timeline.for_each_trace(lambda t: t.update(
            name=legend_names.get(t.name, t.name),
            hovertemplate="<b>%{x}</b><br>" + legend_names.get(t.name, t.name) + ": <b>€ %{y:,.2f}</b><extra></extra>"
        ))
        
        fig_z_timeline.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=45, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(22, 27, 34, 0.85)",
                bordercolor="rgba(255, 255, 255, 0.12)",
                borderwidth=1,
                font=dict(size=11, color="#ffffff")
            )
        )
        apply_plotly_theme(fig_z_timeline)
        st.plotly_chart(fig_z_timeline, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        # Tabella Dettagliata delle Scadenze con formattazione intelligente del tempo residuo
        df_z_table = df_zainetto.copy()
        
        def format_tempo_residuo(row):
            if "Totalmente Compensato" in str(row["status"]):
                return "✅ Concluso"
            if "Prescritto" in str(row["status"]):
                return "❌ Scaduto"
            y = int(row["years_to_expiry"])
            return "< 12 mesi" if y == 0 else f"{y} anni"

        df_z_table["Tempo alla Scadenza"] = df_z_table.apply(format_tempo_residuo, axis=1)

        df_z_table_show = df_z_table[[
            "origin_year", "expiry_year", "initial_minus_eur", "compensated_eur", 
            "residual_active_eur", "Tempo alla Scadenza", "status"
        ]].rename(columns={
            "origin_year": "Anno Origine",
            "expiry_year": "Anno Scadenza",
            "initial_minus_eur": "Minusvalenza Iniziale (€)",
            "compensated_eur": "Compensato (€)",
            "residual_active_eur": "Credito Residuo (€)",
            "status": "Stato Fiscale"
        })

        st.dataframe(
            df_z_table_show.style.format({
                "Minusvalenza Iniziale (€)": "€ {:,.2f}",
                "Compensato (€)": "€ {:,.2f}",
                "Credito Residuo (€)": "€ {:,.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )

# ── TAB 4: RISCHIO LIQUIDITÀ & ALMGREN-CHRISS ─────────────────
elif active_pos_tab == "⚡ Impatto di Mercato (Almgren-Chriss)":
    col_head_ac1, col_head_ac2 = st.columns([3.2, 1.1])
    with col_head_ac1:
        st.markdown("#### ⚡ Impatto di Mercato & Rischio di Liquidazione (Almgren-Chriss)")
        st.caption("Stima dello slippage e dei costi di esecuzione imposti dal mercato durante la smobilizzazione o il ri-bilanciamento delle posizioni.")
    with col_head_ac2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("ℹ️ Guida al Modello Almgren-Chriss & Optimal Execution", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è il Modello Almgren-Chriss (2000)</div>
  <div>Il gold standard quantitativo istituzionale per calcolare l'impatto sui prezzi durante la negoziazione di blocchi azionari e determinare la traiettoria ottimale di esecuzione (Optimal Execution Schedule).</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Scomposizione dell'Impatto di Mercato</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Impatto Temporaneo:</b> &eta; &middot; (v / V)<sup>0.5</sup> &middot; &sigma; (pressione immediata sul book ordini)<br>
    • <b>Impatto Permanente:</b> &gamma; &middot; (V<sub>tot</sub> / ADV) &middot; &sigma; (spostamento strutturale del Fair Value)
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 A cosa serve</div>
  <div>Risolve il trade-off fondamentale: vendere troppo velocemente causa slippage elevato per impatto sul book, mentre vendere troppo lentamente espone il capitale al rischio di oscillazioni avverse di mercato nel tempo.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ Calcolo in ARGUS</div>
  <div>ARGUS stima per ciascun titolo il controvalore da liquidare, il volume medio a 30 giorni (ADV) e calcola i giorni stimati assumendo una partecipazione massima prudenziale del 10% al volume giornaliero.</div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🔍 Come leggerlo</div>
  <div>Uno slippage totale stimato superiore all'1.5% o tempi di smobilizzo &gt; 5 giorni evidenziano titoli poco liquidi che richiedono algoritmi TWAP/VWAP o ordini dilazionati.</div>
</div>

</div>
""", button_label="💡 Come funziona Almgren-Chriss?")

    from core.risk_engine import compute_almgren_chriss_market_impact
    df_ac = compute_almgren_chriss_market_impact(pos)

    if not df_ac.empty:
        tot_impact_eur = float(df_ac["Impatto Monetario (€)"].sum())
        avg_slippage = float(df_ac["Slippage Stimato %"].mean())
        avg_days = float(df_ac["Giorni Liquidazione"].mean())

        ac_c1, ac_c2, ac_c3 = st.columns(3)
        with ac_c1:
            metric_card("Stima Costi di Impatto Totali", f"€ {tot_impact_eur:,.2f}", "Costo stimato di smobilizzazione rapida", False)
        with ac_c2:
            metric_card("Slippage Medio Stimato", f"{avg_slippage:.2f}%", "Perdita di valore media per ordine", False)
        with ac_c3:
            metric_card("Giorni Medi Liquidazione ADV", f"{avg_days:.1f} giorni", "Tempo stimato con 10% ADV", True)

        st.divider()

        col_ac_a, col_ac_b = st.columns([1.8, 1.2])

        with col_ac_a:
            st.markdown("#### 📊 Dettaglio Impatto e Slippage per Asset")
            st.dataframe(
                df_ac.style.format({
                    "Valore (€)": "€ {:,.2f}",
                    "Giorni Liquidazione": "{:.1f}",
                    "Slippage Stimato %": "{:.2f}%",
                    "Impatto Monetario (€)": "€ {:,.2f}"
                }),
                use_container_width=True, hide_index=True
            )

        with col_ac_b:
            st.markdown("#### 📈 Slippage % Stimato per Ticker")
            fig_ac_bar = px.bar(
                df_ac, x="Slippage Stimato %", y="Ticker", orientation="h",
                color="Slippage Stimato %", color_continuous_scale="Reds",
                title="Slippage Stimato (%)", template="plotly_dark", height=320
            )
            fig_ac_bar.update_traces(
                hovertemplate="<b>Ticker: %{y}</b><br>⚡ Slippage: %{x:.2f}%<extra></extra>"
            )
            fig_ac_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_ac_bar, use_container_width=True)
    else:
        st.info("Impossibile calcolare il modello Almgren-Chriss: posizioni attive o dati di volume non sufficienti.")

