import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import importlib
import core.ui_utils
import core.risk_engine
import core.crypto_tax_engine
import core.duckdb_engine
importlib.reload(core.ui_utils)
importlib.reload(core.risk_engine)
importlib.reload(core.crypto_tax_engine)
importlib.reload(core.duckdb_engine)
from core.ui_utils import inject_custom_css, metric_card, fmt_eur, section, glossary_modal, render_command_bar, render_segmented_tabs, apply_plotly_theme, ensure_risk_bundle_loaded, render_sandbox_banner, render_corporate_actions_modal, render_crypto_tax_modal
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
st.divider()

# ── STRUTTURA IN TAB CON LAZY LOADING ──────────────────────────
active_pos_tab = render_segmented_tabs([
    "📋 Posizioni Attive & Costi FIFO",
    "🪦 Posizioni Chiuse & Graveyard",
    "📅 Proiezione Dividendi",
    "💰 Ottimizzazione Fiscale (TUIR Art. 67)",
    "⚡ Liquidità Almgren-Chriss"
], key="positions_active_tab")

# ── TAB 1: POSIZIONI & LIQUIDITÀ ──────────────────────────────
if active_pos_tab == "📋 Posizioni Attive & Costi FIFO":
    section("Concentrazione Portafoglio")

    col_c1, col_c2, col_c3 = st.columns(3)

    with col_c1:
        if con.get("by_asset_class_pct"):
            st.markdown("**Macro Asset Class**")
            ac_labels = [str(k).upper() if str(k).lower() in ["etf", "fx"] else str(k).title() for k in con["by_asset_class_pct"].keys()]
            ac_vals = list(con["by_asset_class_pct"].values())
            fig_ac = go.Figure(go.Pie(
                labels=ac_labels,
                values=ac_vals,
                hole=0.65,
                marker=dict(
                    colors=["#bc8cff", "#00e676", "#58a6ff", "#ff9900", "#f85149"],
                    line=dict(color="#0d1117", width=2)
                ),
                textposition='inside',
                textinfo='percent',
                insidetextorientation='horizontal',
                textfont=dict(size=11, color='#ffffff'),
                hovertemplate="<b>Asset Class: %{label}</b><br>Peso: <b>%{percent}</b><extra></extra>"
            ))
            fig_ac.update_layout(
                template="plotly_dark", height=290,
                legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5, font=dict(size=10.5, color="#ffffff")),
                margin=dict(l=10, r=10, t=10, b=25),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                annotations=[dict(text=f"<b>{len(ac_labels)}</b><br><span style='font-size:10px; color:#8b949e;'>Classi</span>", x=0.5, y=0.5, font_size=13, showarrow=False)]
            )
            apply_plotly_theme(fig_ac)
            st.plotly_chart(fig_ac, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    with col_c2:
        if con.get("by_gics_sector_pct"):
            st.markdown("**Per Settore GICS**")
            s_dict = con["by_gics_sector_pct"]
            s_df = pd.DataFrame(list(s_dict.items()), columns=["Settore", "Peso %"]).sort_values(by="Peso %", ascending=True)
            max_s = s_df["Peso %"].max() if not s_df.empty else 20.0

            fig_sec = go.Figure(go.Bar(
                y=s_df["Settore"],
                x=s_df["Peso %"],
                orientation="h",
                marker=dict(
                    color=s_df["Peso %"],
                    colorscale=[[0, "#1e3a8a"], [1, "#38bdf8"]],
                    line=dict(color="rgba(255,255,255,0.1)", width=1)
                ),
                text=s_df["Peso %"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside",
                cliponaxis=False,
                textfont=dict(size=11, color="#e6edf3", family="monospace"),
                hovertemplate="<b>%{y}</b><br>Peso: <b>%{x:.2f}%</b><extra></extra>"
            ))
            fig_sec.update_layout(
                template="plotly_dark", height=290,
                margin=dict(l=10, r=45, t=10, b=20),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", ticksuffix="%", title=None, range=[0, max(5.0, max_s * 1.25)]),
                yaxis=dict(title=None, tickfont=dict(size=10.5))
            )
            apply_plotly_theme(fig_sec)
            st.plotly_chart(fig_sec, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

    with col_c3:
        if con.get("by_country_pct"):
            st.markdown("**Per Paese**")
            g_dict = con["by_country_pct"]
            g_df = pd.DataFrame(list(g_dict.items()), columns=["Paese", "Peso %"]).sort_values(by="Peso %", ascending=True)
            max_g = g_df["Peso %"].max() if not g_df.empty else 40.0

            fig_geo = go.Figure(go.Bar(
                y=g_df["Paese"],
                x=g_df["Peso %"],
                orientation="h",
                marker=dict(
                    color=g_df["Peso %"],
                    colorscale=[[0, "#7c2d12"], [1, "#fb923c"]],
                    line=dict(color="rgba(255,255,255,0.1)", width=1)
                ),
                text=g_df["Peso %"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside",
                cliponaxis=False,
                textfont=dict(size=11, color="#e6edf3", family="monospace"),
                hovertemplate="<b>%{y}</b><br>Peso: <b>%{x:.2f}%</b><extra></extra>"
            ))
            fig_geo.update_layout(
                template="plotly_dark", height=290,
                margin=dict(l=10, r=45, t=10, b=20),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", ticksuffix="%", title=None, range=[0, max(5.0, max_g * 1.25)]),
                yaxis=dict(title=None, tickfont=dict(size=10.5))
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

        col_pos_f1, col_pos_f2, col_pos_f3 = st.columns([2.0, 1.3, 0.9])
        with col_pos_f1:
            search_pos = st.text_input("🔍 Cerca Posizione:", placeholder="Filtra per Ticker o Settore...", key="search_main_pos")
        with col_pos_f2:
            classes_available = ["Tutte le Classi"] + sorted(list(df_disp["Asset Class"].dropna().unique())) if "Asset Class" in df_disp.columns else ["Tutte"]
            filter_ac = st.selectbox("🏷️ Asset Class:", classes_available, key="filter_main_pos_ac")
        with col_pos_f3:
            st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
            csv_pos = df_disp.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Scarica CSV", data=csv_pos, file_name="posizioni_portafoglio.csv", mime="text/csv", use_container_width=True)

        df_disp_filt = df_disp.copy()
        if search_pos:
            mask = df_disp_filt["Ticker"].astype(str).str.contains(search_pos.strip(), case=False, na=False)
            if "Settore" in df_disp_filt.columns:
                mask |= df_disp_filt["Settore"].astype(str).str.contains(search_pos.strip(), case=False, na=False)
            df_disp_filt = df_disp_filt[mask]
        if filter_ac != "Tutte le Classi" and "Asset Class" in df_disp_filt.columns:
            df_disp_filt = df_disp_filt[df_disp_filt["Asset Class"] == filter_ac]

        column_config = {
            "Prezzo Carico (€)": st.column_config.NumberColumn("Prezzo Carico (€)", format="€ %.2f"),
            "Prezzo Mkt (€)": st.column_config.NumberColumn("Prezzo Mkt (€)", format="€ %.2f"),
            "Controvalore (€)": st.column_config.NumberColumn("Controvalore (€)", format="€ %.2f"),
            "PnL Realizz. (€)": st.column_config.NumberColumn("PnL Realizz. (€)", format="€ %.2f"),
            "PnL Latente (€)": st.column_config.NumberColumn("PnL Latente (€)", format="€ %.2f"),
            "Peso (%)": st.column_config.ProgressColumn("Peso (%)", format="%.2f%%", min_value=0.0, max_value=100.0),
            "Giorni Liq. (ADV 15%)": st.column_config.NumberColumn("Giorni Liq. (ADV 15%)", format="%.2f gg"),
            "Yield on Cost (%)": st.column_config.ProgressColumn("Yield on Cost (%)", format="%.2f%%", min_value=0.0, max_value=20.0)
        }

        st.dataframe(df_disp_filt, use_container_width=True, hide_index=True, column_config=column_config)

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

        # ⚡ DuckDB OLAP In-Process Accelerated Aggregations
        with st.expander("⚡ Vista Analitica Aggregata DuckDB (Cubo OLAP & Ranking Settoriale)", expanded=False):
            from core.duckdb_engine import compute_duckdb_asset_sector_currency_cube, compute_duckdb_sector_rankings
            cube_res = compute_duckdb_asset_sector_currency_cube(df_l)
            rank_res = compute_duckdb_sector_rankings(df_l, top_n=3)

            tab_cube, tab_rank = st.tabs([
                "🧊 Cubo Multi-Dimensionale (Asset Class × Settore × Valuta)",
                "🏆 Leader Settoriali (QUALIFY Rank ≤ 3)"
            ])

            with tab_cube:
                if cube_res.get("success") and not cube_res["df"].empty:
                    df_cube = cube_res["df"].copy()
                    col_cu_h1, col_cu_h2 = st.columns([3.2, 1.0])
                    with col_cu_h1:
                        st.caption(f"🚀 Esecuzione C++ SIMD Vettorizzata in **{cube_res['latency_ms']:.2f} ms** (DuckDB GROUPING SETS Rollup)")
                    with col_cu_h2:
                        csv_cube = df_cube.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Scarica Cubo CSV", data=csv_cube, file_name="duckdb_olap_cube.csv", mime="text/csv", use_container_width=True)

                    cube_cfg = {
                        "asset_class": st.column_config.TextColumn("Asset Class"),
                        "sector": st.column_config.TextColumn("Settore GICS"),
                        "currency": st.column_config.TextColumn("Valuta"),
                        "n_posizioni": st.column_config.NumberColumn("N. Posizioni", format="%d"),
                        "controvalore_eur": st.column_config.NumberColumn("Controvalore (€)", format="€ %.2f")
                    }
                    st.dataframe(
                        df_cube,
                        column_config=cube_cfg,
                        use_container_width=True,
                        hide_index=True,
                        height=300
                    )
                else:
                    st.info("Nessun dato disponibile per il cubo OLAP.")

            with tab_rank:
                if rank_res.get("success") and not rank_res["df"].empty:
                    df_rank = rank_res["df"].copy()
                    col_rk_h1, col_rk_h2 = st.columns([3.2, 1.0])
                    with col_rk_h1:
                        st.caption(f"⚡ Calcolo Window Function in **{rank_res['latency_ms']:.2f} ms** (DuckDB QUALIFY DENSE_RANK() ≤ 3)")
                    with col_rk_h2:
                        csv_rank = df_rank.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Scarica Leader CSV", data=csv_rank, file_name="duckdb_sector_leaders.csv", mime="text/csv", use_container_width=True)

                    rank_cfg = {
                        "settore": st.column_config.TextColumn("Settore GICS"),
                        "ticker": st.column_config.TextColumn("Ticker"),
                        "controvalore_eur": st.column_config.NumberColumn("Controvalore (€)", format="€ %.2f"),
                        "rank_in_settore": st.column_config.NumberColumn("Rank Settoriale", format="#%d")
                    }
                    st.dataframe(
                        df_rank,
                        column_config=rank_cfg,
                        use_container_width=True,
                        hide_index=True,
                        height=300
                    )
                else:
                    st.info("Nessun ranking disponibile.")

    # Sezione Corporate Actions & Stock Split Audit
    corp_actions = results.get("corporate_actions", [])
    st.markdown("---")
    col_ca_title, col_ca_btn = st.columns([3.2, 1.2])
    with col_ca_title:
        st.markdown("#### 🧬 Corporate Actions & Stock Split Engine (Rettifica FIFO)")
        st.caption("Rilevazione automatica e rettifica dei lotti storici per frazionamenti azionari (Stock Split) e raggruppamenti (Reverse Split), a garanzia dell'invarianza del costo fiscale.")
    with col_ca_btn:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        render_corporate_actions_modal(corporate_actions_list=corp_actions, use_popover=False)

    if corp_actions and len(corp_actions) > 0:
        df_ca = pd.DataFrame(corp_actions)
        col_ca_map = {
            "ticker": "Ticker",
            "split_date": "Data Efficacia",
            "split_type": "Tipologia",
            "split_ratio": "Rapporto Split",
            "description": "Descrizione",
            "affected_lots_count": "Lotti Rettificati",
            "shares_before": "Quote Ante-Split",
            "shares_after": "Quote Post-Split"
        }
        df_ca_disp = df_ca[[c for c in col_ca_map.keys() if c in df_ca.columns]].rename(columns=col_ca_map)
        st.dataframe(df_ca_disp, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Nessuno split azionario o operazione straordinaria rilevata sui lotti storici di questo portafoglio (le transazioni sono già sincronizzate con i prezzi correnti).")


# ── TAB 2: POSIZIONI CHIUSE & GRAVEYARD ───────────────────────
elif active_pos_tab == "🪦 Posizioni Chiuse & Graveyard":
    col_head_g1, col_head_g2 = st.columns([3.2, 1.2])
    with col_head_g1:
        st.markdown("### 🪦 Graveyard & Registro Operazioni Chiuse (FIFO)")
        st.caption("Tracciamento contabile delle posizioni interamente o parzialmente liquidate, plus/minusvalenze realizzate, tempo di detenzione (holding period) e statistiche di performance.")
    with col_head_g2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("🪦 Guida al Graveyard & PnL Realizzato (FIFO)", """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">

<!-- 1. PNL REALIZZATO -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(0,230,118,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #00e676; font-size: 15px; font-weight: 700; margin-bottom: 6px;">💰 1. PnL Realizzato (Realized Profit & Loss)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Il guadagno o la perdita monetaria effettivamente incassata a seguito della chiusura totale o parziale di uno strumento finanziario.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(0,230,118,0.08); border-left: 3px solid #00e676; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #00e676; text-align: center; font-size: 12.5px;">
      <b>PnL Realizzato</b> = Incasso Netto Vendita &minus; Costo Storico Fiscale FIFO
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Misurare la ricchezza monetizzata e consolidata, separandola dalle oscillazioni temporanee dei prezzi delle posizioni ancora aperte (PnL Latente).</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Motore contabile a code FIFO che abbina ogni ordine di vendita al lotto d'acquisto cronologicamente più vecchio con conversione FX storica.</div>
  <div><b>🔍 Come leggerlo:</b> Se positivo indica plusvalenza netta realizzata; se negativo minusvalenza fiscalmente compensabile.</div>
</div>

<!-- 2. WIN RATE & PROFIT FACTOR -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(88,166,255,0.25); border-radius: 10px; padding: 14px; margin-bottom: 12px;">
  <div style="color: #58a6ff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🎯 2. Win Rate & Profit Factor</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> Parametri quantitativi di efficienza strategica. Il <b>Win Rate</b> è la percentuale di trade chiusi in utile; il <b>Profit Factor</b> è il rapporto tra profitti lordi realizzati e perdite lorde.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(88,166,255,0.08); border-left: 3px solid #58a6ff; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #58a6ff; text-align: center; font-size: 12.5px;">
      <b>Win Rate</b> = N<sub>Trades Vincenti</sub> / N<sub>Totale</sub> &nbsp;|&nbsp; <b>Profit Factor</b> = &sum; Guadagni / &sum; |Perdite|
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Valutare la robustezza del processo decisionale e se i guadagni superano stabilmente i drawdown subiti.</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Calcolato su tutti i lotti FIFO chiusi storicamente nel portafoglio.</div>
  <div><b>🔍 Come leggerlo:</b> Un Profit Factor &gt; 1.50 e Win Rate &gt; 55% indicano un'eccellente disciplina di gestione del rischio.</div>
</div>

<!-- 3. GRAVEYARD & HOLDING PERIOD -->
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,153,0,0.25); border-radius: 10px; padding: 14px; margin-bottom: 4px;">
  <div style="color: #ff9900; font-size: 15px; font-weight: 700; margin-bottom: 6px;">🪦 3. Graveyard & Holding Period (Tempo di Detenzione)</div>
  <div style="margin-bottom: 6px;"><b>📌 Cos'è:</b> L'archivio storico ('Cimitero dei Titoli') di tutti gli strumenti dismessi e il numero medio di giorni trascorsi tra l'acquisto e la vendita definitiva.</div>
  <div style="margin-bottom: 6px;"><b>📐 Come si calcola:</b>
    <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 4px 0; color: #ffb74d; text-align: center; font-size: 12.5px;">
      <b>Holding Period (gg)</b> = Data Vendita &minus; Data Acquisto FIFO
    </div>
  </div>
  <div style="margin-bottom: 6px;"><b>🎯 A cosa serve:</b> Identificare se il portafoglio segue una strategia di lungo periodo (Buy & Hold / Compounder) o di rotazione frequente (Swing/Tactical Trading).</div>
  <div style="margin-bottom: 6px;"><b>⚙️ Calcolo in ARGUS:</b> Calcolato su ciascuna combinazione di lotto acquistato e venduto.</div>
  <div><b>🔍 Come leggerlo:</b> Mostra l'orizzonte temporale effettivo di detenzione per ciascuna idea d'investimento.</div>
</div>

</div>
""", button_label="💡 Come funziona il Graveyard?")

    from core.closed_trades import compute_closed_trades_journal
    df_tx = results.get("df_tx", pd.DataFrame())
    df_prices = results.get("df_prices", pd.DataFrame())
    is_sand = results.get("is_sandbox", False)
    closed_data = results.get("closed_trades") or compute_closed_trades_journal(df_tx=df_tx, df_prices=df_prices, df_positions=pos, is_sandbox=is_sand)

    if not closed_data.get("has_closed_trades", False) or closed_data.get("df_closed_lots", pd.DataFrame()).empty:
        st.info("ℹ️ **Nessuna vendita registrata nello storico**: tutte le posizioni acquistate sono ancora aperte a mercato. Il PnL totale attuale corrisponde interamente a PnL Latente e Dividendi percepiti.")
    else:
        # ── 1. KPI COCKPIT DELLE OPERAZIONI CHIUSE (GRID 2x3) ─────────
        c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
        
        tot_real_pnl = closed_data["total_realized_pnl_eur"]
        tot_real_pct = closed_data["total_realized_pnl_pct"]
        win_rate = closed_data["win_rate_pct"]
        prof_factor = closed_data["profit_factor"]
        avg_holding = closed_data["avg_holding_days"]
        n_closed = closed_data["total_closed_trades"]
        best_t = closed_data.get("best_trade", {})
        worst_t = closed_data.get("worst_trade", {})

        with c_kpi1:
            metric_card(
                "PnL Realizzato Netto",
                f"€ {tot_real_pnl:,.2f}",
                delta=f"{tot_real_pct:+.2f}%",
                positive=(tot_real_pnl >= 0),
                help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Somma monetaria netta consolidata derivante da tutte le operazioni di vendita concluse dall'inizio dell'operatività.</div>
<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b> Somma algebrica del differenziale tra prezzo di vendita ed il costo storico d'acquisto FIFO per ogni quota liquidata.</div>
<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Misura la redditività effettivamente monetizzata, distinta dal PnL latente (ancora soggetto alle fluttuazioni di mercato).</div>
<div style="margin-bottom: 8px;"><b>⚙️ Calcolo in ARGUS:</b> Coda FIFO con conversione dei tassi di cambio storici alla data dell'operazione.</div>
<div><b>🔍 Come leggerlo:</b> Se positivo indica che le vendite storiche hanno generato un surplus di cassa netto.</div>
</div>"""
            )
        with c_kpi2:
            metric_card(
                "Win Rate (%)",
                f"{win_rate:.1f}%",
                delta=f"{closed_data['n_winning_trades']}W / {closed_data['n_losing_trades']}L",
                positive=(win_rate >= 50.0),
                help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Percentuale di operazioni chiuse in profitto (Win) rispetto al totale dei lotti venduti.</div>
<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b> (Numero Trade Vincenti / Numero Totale Trade Chiusi) &times; 100.</div>
<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Valuta la frequenza di successo delle decisioni di disinvestimento o presa di profitto.</div>
<div style="margin-bottom: 8px;"><b>⚙️ Calcolo in ARGUS:</b> Traccia ciascun lotto FIFO chiuso con PnL > 0 come Win, PnL < 0 come Loss.</div>
<div><b>🔍 Come leggerlo:</b> Un Win Rate > 50% combinato con un buon Profit Factor indica una strategia statisticamente solida.</div>
</div>"""
            )
        with c_kpi3:
            metric_card(
                "Profit Factor",
                f"{prof_factor:.2f}" if prof_factor < 90 else "> 10.0",
                delta="Profitti / |Perdite|",
                positive=(prof_factor >= 1.30),
                help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Rapporto di efficienza tra i profitti lordi realizzati e le perdite lorde subite sulle posizioni chiuse.</div>
<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b> &sum;(Guadagni delle vendite in utile) / &sum;|Perdite delle vendite in perdita|.</div>
<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Misura la qualità asimmetrica del trading: quanti Euro si guadagnano per ogni Euro perso.</div>
<div style="margin-bottom: 8px;"><b>⚙️ Calcolo in ARGUS:</b> Rapporto tra le plusvalenze complessive e il valore assoluto delle minusvalenze storiche.</div>
<div><b>🔍 Come leggerlo:</b> Valori > 1.50 indicano eccellente gestione del rischio; < 1.0 segnala che le perdite superano i guadagni realizzati.</div>
</div>"""
            )

        c_kpi4, c_kpi5, c_kpi6 = st.columns(3)
        with c_kpi4:
            metric_card(
                "Holding Period Medio",
                f"{avg_holding} gg",
                delta=f"Su {n_closed} Trade",
                positive=True,
                help_text="""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> Numero medio di giorni di calendario trascorsi tra la data d'acquisto e la data di vendita definitiva dei lotti.</div>
<div style="margin-bottom: 8px;"><b>📐 Come si calcola:</b> Media aritmetica della differenza (Data Vendita &minus; Data Acquisto FIFO) per ciascun lotto chiuso.</div>
<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Identifica lo stile operativo effettivo (es. medio termine, swing trading, buy-and-hold pluriennale).</div>
<div style="margin-bottom: 8px;"><b>⚙️ Calcolo in ARGUS:</b> Differenza temporale esatta in giorni per ciascun matching contabile.</div>
<div><b>🔍 Come leggerlo:</b> Valori elevati (> 365 gg) riflettono un approccio d'investimento paziente e orientato al compounding.</div>
</div>"""
            )
        with c_kpi5:
            best_tk = best_t.get("ticker", "N/A")
            best_pnl = best_t.get("realized_pnl_eur", 0.0)
            best_pct = best_t.get("realized_pnl_pct", 0.0)
            metric_card(
                "Miglior Trade Realizzato",
                f"€ {best_pnl:+,.2f}",
                delta=f"{best_tk} ({best_pct:+.1f}%)",
                positive=True,
                help_text=f"""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> L'operazione chiusa che ha generato il maggior profitto monetario in assoluto (€).</div>
<div style="margin-bottom: 8px;"><b>📐 Dati Trade:</b> Ticker: <b>{best_tk}</b> | PnL: <b>€ {best_pnl:+,.2f}</b> ({best_pct:+.1f}%) | Chiusura: <b>{best_t.get('sell_date', 'N/A')}</b>.</div>
<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Evidenzia il 'fuoriclasse' storico del portafoglio e il suo contributo alla ricchezza complessiva.</div>
<div style="margin-bottom: 8px;"><b>⚙️ Calcolo in ARGUS:</b> Massimo PnL realizzato tra tutti i lotti chiusi.</div>
<div><b>🔍 Come leggerlo:</b> Mostra l'asset che ha beneficiato del miglior timing e dimensionamento della posizione.</div>
</div>"""
            )
        with c_kpi6:
            worst_tk = worst_t.get("ticker", "N/A")
            worst_pnl = worst_t.get("realized_pnl_eur", 0.0)
            worst_pct = worst_t.get("realized_pnl_pct", 0.0)
            metric_card(
                "Peggior Trade Realizzato",
                f"€ {worst_pnl:+,.2f}",
                delta=f"{worst_tk} ({worst_pct:+.1f}%)",
                positive=False,
                help_text=f"""<div style="font-size: 13.5px; line-height: 1.45;">
<div style="margin-bottom: 8px;"><b>📌 Cos'è:</b> L'operazione chiusa che ha registrato la maggior perdita monetaria in assoluto (€).</div>
<div style="margin-bottom: 8px;"><b>📐 Dati Trade:</b> Ticker: <b>{worst_tk}</b> | PnL: <b>€ {worst_pnl:+,.2f}</b> ({worst_pct:+.1f}%) | Chiusura: <b>{worst_t.get('sell_date', 'N/A')}</b>.</div>
<div style="margin-bottom: 8px;"><b>🎯 A cosa serve:</b> Fornisce trasparenza sui rischi incorsi e sulle decisioni di stop-loss o disinvestimento in perdita.</div>
<div style="margin-bottom: 8px;"><b>⚙️ Calcolo in ARGUS:</b> Minimo PnL realizzato tra tutti i lotti chiusi.</div>
<div><b>🔍 Come leggerlo:</b> Utile per analizzare gli errori di timing o le tesi d'investimento invalidate.</div>
</div>"""
            )

        st.markdown('<div style="margin-top: 15px;"></div>', unsafe_allow_html=True)

        # ── 2. SELETTORE PROSPETTIVA GRAFICA COCKPIT ──────────────────
        df_assets_closed = closed_data.get("df_closed_assets", pd.DataFrame())
        df_lots_closed = closed_data.get("df_closed_lots", pd.DataFrame())
        df_cum_curve = closed_data.get("df_cumulative_curve", pd.DataFrame())
        cal_data = closed_data.get("calendar_data", {})
        breakdown_data = closed_data.get("breakdown_data", {})

        st.markdown("#### 📊 Analisi Grafica delle Posizioni Chiuse")
        view_mode_gy = st.radio(
            "Seleziona Prospettiva Grafica:",
            [
                "📊 PnL Asset & Timeline (2 Righe)",
                "📈 Curva Cumulativa PnL Realizzato (€)",
                "📅 Trading Calendar & Heatmap Mensile",
                "🏷️ Scomposizione Settori & Asset Class"
            ],
            horizontal=True,
            key="gy_chart_view_mode_radio"
        )

        if view_mode_gy == "📊 PnL Asset & Timeline (2 Righe)":
            # RIGA 1: PnL Realizzato per Asset (Istogramma Verticale Divergente)
            if not df_assets_closed.empty:
                st.markdown("##### 📊 PnL Realizzato per Asset (€)")
                df_sorted_a = df_assets_closed.sort_values("realized_pnl_eur", ascending=False)
                bar_colors = ["#3fb950" if v >= 0 else "#f85149" for v in df_sorted_a["realized_pnl_eur"]]
                
                fig_bar_pnl = go.Figure(go.Bar(
                    x=df_sorted_a["ticker"],
                    y=df_sorted_a["realized_pnl_eur"],
                    marker=dict(color=bar_colors, line=dict(color="rgba(255,255,255,0.15)", width=1)),
                    customdata=df_sorted_a["realized_pnl_pct"],
                    hovertemplate="<b>Asset: %{x}</b><br>• PnL Realizzato: <b>€ %{y:+,.2f}</b><br>• Rendimento: <b>%{customdata:+.2f}%</b><extra></extra>"
                ))
                fig_bar_pnl.update_layout(
                    template="plotly_dark", height=300,
                    xaxis=dict(
                        title=None,
                        gridcolor="rgba(255,255,255,0.04)",
                        tickfont=dict(size=11, color="#c9d1d9"),
                        tickangle=-30
                    ),
                    yaxis=dict(
                        title="PnL Realizzato Netto (€)",
                        zeroline=True,
                        zerolinecolor="rgba(255,255,255,0.3)",
                        zerolinewidth=1.5,
                        gridcolor="rgba(255,255,255,0.06)",
                        tickprefix="€ ",
                        separatethousands=True
                    ),
                    margin=dict(l=60, r=20, t=20, b=40),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                apply_plotly_theme(fig_bar_pnl)
                st.plotly_chart(fig_bar_pnl, use_container_width=True)

            st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)

            # RIGA 2: Rendimento vs Tempo di Detenzione (Scatter Timeline)
            if not df_lots_closed.empty:
                st.markdown("##### ⏱️ Rendimento Realizzato (%) vs Tempo di Detenzione")
                fig_scat = go.Figure()
                for outcome, color in [("🟢 WIN", "#3fb950"), ("🔴 LOSS", "#f85149"), ("🟡 BREAKEVEN", "#ffd700")]:
                    df_sub = df_lots_closed[df_lots_closed["outcome"] == outcome]
                    if not df_sub.empty:
                        fig_scat.add_trace(go.Scatter(
                            x=df_sub["holding_days"],
                            y=df_sub["realized_pnl_pct"],
                            mode="markers",
                            name=outcome,
                            marker=dict(
                                color=color,
                                size=9,
                                opacity=0.88,
                                line=dict(width=1.0, color="#ffffff")
                            ),
                            customdata=np.stack((
                                df_sub["ticker"],
                                df_sub["realized_pnl_eur"],
                                df_sub["buy_date"],
                                df_sub["sell_date"]
                            ), axis=-1),
                            hovertemplate=(
                                "<b>%{customdata[0]}</b> (" + outcome + ")<br>"
                                "• Tempo Detenzione: <b>%{x} gg</b><br>"
                                "• Rendimento: <b>%{y:+.2f}%</b><br>"
                                "• PnL Realizzato: <b>€ %{customdata[1]:+,.2f}</b><br>"
                                "• Acquisto: <b>%{customdata[2]}</b> | Vendita: <b>%{customdata[3]}</b>"
                                "<extra></extra>"
                            )
                        ))
                fig_scat.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.35)", line_width=1.5)
                fig_scat.update_layout(
                    template="plotly_dark", height=320,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1.0,
                        title_text="",
                        bgcolor="rgba(22,27,34,0.75)",
                        bordercolor="rgba(255,255,255,0.12)",
                        borderwidth=1,
                        font=dict(size=10)
                    ),
                    xaxis=dict(
                        title="Giorni di Detenzione (Holding Period)",
                        gridcolor="rgba(255,255,255,0.06)",
                        zeroline=False
                    ),
                    yaxis=dict(
                        title="Rendimento Realizzato (%)",
                        ticksuffix="%",
                        gridcolor="rgba(255,255,255,0.06)",
                        zeroline=False
                    ),
                    margin=dict(l=55, r=20, t=30, b=45),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                apply_plotly_theme(fig_scat)
                st.plotly_chart(fig_scat, use_container_width=True)

        elif view_mode_gy == "📈 Curva Cumulativa PnL Realizzato (€)":
            if not df_cum_curve.empty:
                st.markdown("##### 📈 Crescita Progressiva del Capitale Chiuso & High-Water Mark")
                st.caption("Visualizza l'accumulazione monetaria progressiva del PnL realizzato e la distanza dal picco storico (Drawdown del capitale chiuso).")
                
                last_cum = float(df_cum_curve["cum_realized_pnl_eur"].iloc[-1])
                area_color = "rgba(63, 185, 80, 0.15)" if last_cum >= 0 else "rgba(248, 81, 73, 0.15)"
                line_color = "#3fb950" if last_cum >= 0 else "#f85149"
                
                fig_cum = go.Figure()
                fig_cum.add_trace(go.Scatter(
                    x=df_cum_curve["sell_date_str"],
                    y=df_cum_curve["cum_realized_pnl_eur"],
                    mode="lines+markers",
                    name="PnL Realizzato Cumulato",
                    line=dict(color=line_color, width=2.5),
                    marker=dict(size=7, color=line_color, line=dict(color="#ffffff", width=1)),
                    fill="tozeroy",
                    fillcolor=area_color,
                    customdata=np.stack((
                        df_cum_curve["ticker"],
                        df_cum_curve["realized_pnl_eur"].apply(lambda v: f"€ {v:+,.2f}"),
                        df_cum_curve["drawdown_eur"].apply(lambda v: f"€ {v:,.2f}"),
                        df_cum_curve["cum_realized_pnl_eur"].apply(lambda v: f"€ {v:+,.2f}")
                    ), axis=-1),
                    hovertemplate=(
                        "<b>Data Vendita: %{x}</b><br>"
                        "• PnL Cumulato: <b>%{customdata[3]}</b><br>"
                        "• Asset Venduti: <b>%{customdata[0]}</b> (PnL: %{customdata[1]})<br>"
                        "• Drawdown da Picco: <b>%{customdata[2]}</b>"
                        "<extra></extra>"
                    )
                ))
                fig_cum.add_trace(go.Scatter(
                    x=df_cum_curve["sell_date_str"],
                    y=df_cum_curve["high_water_mark_eur"],
                    mode="lines",
                    name="High-Water Mark (Picco)",
                    line=dict(color="#58a6ff", width=1.5, dash="dash"),
                    customdata=df_cum_curve["high_water_mark_eur"].apply(lambda v: f"€ {v:,.2f}"),
                    hovertemplate="<b>Picco Storico PnL: %{customdata}</b><extra></extra>"
                ))
                fig_cum.update_layout(
                    template="plotly_dark", height=350,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
                    xaxis=dict(title="Data di Uscita FIFO", gridcolor="rgba(255,255,255,0.06)"),
                    yaxis=dict(title="PnL Realizzato Cumulato (€)", tickprefix="€ ", separatethousands=True, gridcolor="rgba(255,255,255,0.06)"),
                    margin=dict(l=60, r=20, t=30, b=40),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                apply_plotly_theme(fig_cum)
                st.plotly_chart(fig_cum, use_container_width=True)
            else:
                st.info("Dati insufficienti per generare la curva cumulativa di PnL.")

        elif view_mode_gy == "📅 Trading Calendar & Heatmap Mensile":
            df_piv = cal_data.get("df_pivot", pd.DataFrame())
            if not df_piv.empty:
                st.markdown("##### 📅 Trading Calendar: Performance Realizzata per Mese & Anno (€)")
                st.caption("Matrice di monitoraggio temporale delle chiusure: identificazione della stagionalità e dei mesi più profittevoli.")
                
                month_cols = [c for c in df_piv.columns if c != "Totale Anno (€)"]
                z_matrix = df_piv[month_cols].values
                y_years = [str(y) for y in df_piv.index]

                fig_cal = go.Figure(data=go.Heatmap(
                    z=z_matrix,
                    x=month_cols,
                    y=y_years,
                    colorscale=[
                        [0.0, "#f85149"],
                        [0.48, "#21262d"],
                        [0.50, "#161b22"],
                        [0.52, "#21262d"],
                        [1.0, "#3fb950"]
                    ],
                    zmid=0.0,
                    text=[[f"€ {v:+,.0f}" if abs(v) > 0.01 else "—" for v in row] for row in z_matrix],
                    texttemplate="%{text}",
                    textfont=dict(size=11, color="#ffffff"),
                    hoverongaps=False,
                    hovertemplate="<b>Anno %{y} - %{x}</b><br>• PnL Realizzato: <b>%{text}</b><extra></extra>"
                ))
                fig_cal.update_layout(
                    template="plotly_dark",
                    height=200 + len(y_years) * 45,
                    xaxis=dict(title=None, side="top", gridcolor="rgba(255,255,255,0.02)"),
                    yaxis=dict(title="Anno", autorange="reversed", gridcolor="rgba(255,255,255,0.02)"),
                    margin=dict(l=55, r=20, t=40, b=20),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                apply_plotly_theme(fig_cal)
                st.plotly_chart(fig_cal, use_container_width=True)

                def _color_pnl_cell(val):
                    try:
                        v = float(val)
                        if v > 0.01:
                            return "color: #3fb950; font-weight: 600;"
                        elif v < -0.01:
                            return "color: #f85149; font-weight: 600;"
                        else:
                            return "color: #8b949e;"
                    except Exception:
                        return ""

                st.markdown("###### 📑 Riepilogo Tabellare Performance per Anno")
                st_piv = df_piv.style.format("€ {:+,.2f}")
                if hasattr(st_piv, "map"):
                    st_piv = st_piv.map(_color_pnl_cell, subset=month_cols)
                elif hasattr(st_piv, "applymap"):
                    st_piv = st_piv.applymap(_color_pnl_cell, subset=month_cols)

                st.dataframe(st_piv, use_container_width=True)
            else:
                st.info("Nessuna operazione registrata nel calendario mensile.")

        elif view_mode_gy == "🏷️ Scomposizione Settori & Asset Class":
            df_sec = breakdown_data.get("df_by_sector", pd.DataFrame())
            df_ac = breakdown_data.get("df_by_asset_class", pd.DataFrame())

            col_sec, col_ac = st.columns(2)
            with col_sec:
                st.markdown("##### 🏢 PnL Realizzato per Settore (€)")
                if not df_sec.empty:
                    df_sec_sort = df_sec.sort_values("pnl_eur", ascending=True)
                    sec_colors = ["#3fb950" if v >= 0 else "#f85149" for v in df_sec_sort["pnl_eur"]]
                    fig_sec = go.Figure(go.Bar(
                        x=df_sec_sort["pnl_eur"],
                        y=df_sec_sort["sector"],
                        orientation="h",
                        marker=dict(color=sec_colors, line=dict(color="rgba(255,255,255,0.15)", width=1)),
                        customdata=np.stack((df_sec_sort["win_rate_pct"], df_sec_sort["trades_count"]), axis=-1),
                        hovertemplate="<b>Settore: %{y}</b><br>• PnL Realizzato: <b>€ %{x:+,.2f}</b><br>• Win Rate: <b>%{customdata[0]:.1f}%</b><br>• N. Trade: <b>%{customdata[1]}</b><extra></extra>"
                    ))
                    fig_sec.update_layout(
                        template="plotly_dark",
                        height=max(320, 36 * len(df_sec_sort)),
                        xaxis=dict(title="PnL Realizzato Netto (€)", tickprefix="€ ", separatethousands=True, gridcolor="rgba(255,255,255,0.06)"),
                        yaxis=dict(title=None, tickfont=dict(size=11, color="#c9d1d9")),
                        margin=dict(l=175, r=20, t=20, b=40),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                    )
                    apply_plotly_theme(fig_sec)
                    st.plotly_chart(fig_sec, use_container_width=True)

            with col_ac:
                st.markdown("##### 🏛️ PnL Realizzato per Asset Class (€)")
                if not df_ac.empty:
                    df_ac_sort = df_ac.sort_values("pnl_eur", ascending=True)
                    ac_colors = ["#3fb950" if v >= 0 else "#f85149" for v in df_ac_sort["pnl_eur"]]
                    fig_ac = go.Figure(go.Bar(
                        x=df_ac_sort["pnl_eur"],
                        y=df_ac_sort["asset_class"],
                        orientation="h",
                        marker=dict(color=ac_colors, line=dict(color="rgba(255,255,255,0.15)", width=1)),
                        customdata=np.stack((df_ac_sort["win_rate_pct"], df_ac_sort["trades_count"]), axis=-1),
                        hovertemplate="<b>Asset Class: %{y}</b><br>• PnL Realizzato: <b>€ %{x:+,.2f}</b><br>• Win Rate: <b>%{customdata[0]:.1f}%</b><br>• N. Trade: <b>%{customdata[1]}</b><extra></extra>"
                    ))
                    fig_ac.update_layout(
                        template="plotly_dark",
                        height=max(260, 50 * len(df_ac_sort)),
                        bargap=0.55,
                        xaxis=dict(title="PnL Realizzato Netto (€)", tickprefix="€ ", separatethousands=True, gridcolor="rgba(255,255,255,0.06)"),
                        yaxis=dict(title=None, tickfont=dict(size=11, color="#c9d1d9")),
                        margin=dict(l=145, r=20, t=20, b=40),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                    )
                    apply_plotly_theme(fig_ac)
                    st.plotly_chart(fig_ac, use_container_width=True)

        st.divider()

        # ── 3. TABELLE GRAVEYARD & REGISTRO LOTTI ─────────────────────
        st.markdown("#### 📜 Registro Operazioni Chiuse & Graveyard")
        sub_view_gy = st.radio(
            "Seleziona Vista Dati:",
            ["🪦 Sintesi per Asset (Graveyard Aggregato)", "📑 Registro Analitico Lotti Chiusi (FIFO Log)"],
            horizontal=True,
            key="sub_view_gy_radio"
        )

        if sub_view_gy == "🪦 Sintesi per Asset (Graveyard Aggregato)":
            if not df_assets_closed.empty:
                df_a_disp = df_assets_closed.copy()
                df_a_disp_cols = [
                    "ticker", "asset_class", "sector", "country", "status", "qty_sold",
                    "avg_buy_price_eur", "avg_sell_price_eur", "cost_basis_eur",
                    "proceeds_eur", "realized_pnl_eur", "realized_pnl_pct",
                    "dividends_eur", "total_profit_eur", "avg_holding_days", "outcome"
                ]
                df_a_show = df_a_disp[[c for c in df_a_disp_cols if c in df_a_disp.columns]].rename(columns={
                    "ticker": "Ticker", "asset_class": "Asset Class", "sector": "Settore", "country": "Paese",
                    "status": "Stato Posizione", "qty_sold": "Q.tà Chiusa", "avg_buy_price_eur": "Prezzo Carico Medio (€)",
                    "avg_sell_price_eur": "Prezzo Vendita Medio (€)", "cost_basis_eur": "Costo Fiscale (€)",
                    "proceeds_eur": "Incasso (€)", "realized_pnl_eur": "PnL Realizzato (€)",
                    "realized_pnl_pct": "Rendimento (%)", "dividends_eur": "Dividendi (€)",
                    "total_profit_eur": "Profitto Netto (€)", "avg_holding_days": "Holding Medio (gg)",
                    "outcome": "Esito"
                })

                # Toolbar: Ricerca, Filtri e Download CSV
                col_f1, col_f2, col_f3, col_f4 = st.columns([2.0, 1.2, 1.2, 1.1])
                with col_f1:
                    search_gy_a = st.text_input("🔍 Cerca Ticker / Settore:", key="search_gy_assets", placeholder="Es. META, AAPL, Tecnologia...")
                with col_f2:
                    statuses = ["Tutti gli Stati"] + sorted(list(df_a_show["Stato Posizione"].dropna().unique())) if "Stato Posizione" in df_a_show.columns else ["Tutti"]
                    filter_status = st.selectbox("📌 Stato:", statuses, key="filter_gy_status")
                with col_f3:
                    outcomes = ["Tutti gli Esiti"] + sorted(list(df_a_show["Esito"].dropna().unique())) if "Esito" in df_a_show.columns else ["Tutti"]
                    filter_outcome = st.selectbox("🎯 Esito:", outcomes, key="filter_gy_outcome")
                with col_f4:
                    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                    csv_a = df_a_show.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica CSV", data=csv_a, file_name="graveyard_sintesi_asset.csv", mime="text/csv", use_container_width=True, key="btn_download_gy_assets")

                df_a_filt = df_a_show.copy()
                if search_gy_a:
                    mask = df_a_filt["Ticker"].astype(str).str.contains(search_gy_a.strip(), case=False, na=False)
                    if "Settore" in df_a_filt.columns:
                        mask |= df_a_filt["Settore"].astype(str).str.contains(search_gy_a.strip(), case=False, na=False)
                    if "Asset Class" in df_a_filt.columns:
                        mask |= df_a_filt["Asset Class"].astype(str).str.contains(search_gy_a.strip(), case=False, na=False)
                    df_a_filt = df_a_filt[mask]
                if filter_status != "Tutti gli Stati" and "Stato Posizione" in df_a_filt.columns:
                    df_a_filt = df_a_filt[df_a_filt["Stato Posizione"] == filter_status]
                if filter_outcome != "Tutti gli Esiti" and "Esito" in df_a_filt.columns:
                    df_a_filt = df_a_filt[df_a_filt["Esito"] == filter_outcome]

                cfg_a = {
                    "Prezzo Carico Medio (€)": st.column_config.NumberColumn("Prezzo Carico Medio (€)", format="€ %.2f"),
                    "Prezzo Vendita Medio (€)": st.column_config.NumberColumn("Prezzo Vendita Medio (€)", format="€ %.2f"),
                    "Costo Fiscale (€)": st.column_config.NumberColumn("Costo Fiscale (€)", format="€ %.2f"),
                    "Incasso (€)": st.column_config.NumberColumn("Incasso (€)", format="€ %.2f"),
                    "PnL Realizzato (€)": st.column_config.NumberColumn("PnL Realizzato (€)", format="€ %.2f"),
                    "Rendimento (%)": st.column_config.NumberColumn("Rendimento (%)", format="%.2f%%"),
                    "Dividendi (€)": st.column_config.NumberColumn("Dividendi (€)", format="€ %.2f"),
                    "Profitto Netto (€)": st.column_config.NumberColumn("Profitto Netto (€)", format="€ %.2f"),
                    "Holding Medio (gg)": st.column_config.NumberColumn("Holding Medio (gg)", format="%d gg")
                }
                st.dataframe(df_a_filt, use_container_width=True, hide_index=True, column_config=cfg_a)
            else:
                st.info("Nessuna sintesi per asset disponibile.")

        else:
            if not df_lots_closed.empty:
                df_l_disp = df_lots_closed.copy()
                df_l_cols = [
                    "ticker", "asset_class", "sector", "country", "buy_date", "sell_date", "qty",
                    "buy_price_eur", "sell_price_eur", "cost_basis_eur",
                    "proceeds_eur", "realized_pnl_eur", "realized_pnl_pct",
                    "holding_days", "outcome"
                ]
                df_l_show = df_l_disp[[c for c in df_l_cols if c in df_l_disp.columns]].rename(columns={
                    "ticker": "Ticker", "asset_class": "Asset Class", "sector": "Settore", "country": "Paese",
                    "buy_date": "Data Acquisto", "sell_date": "Data Vendita",
                    "qty": "Quantità Lotto", "buy_price_eur": "Prezzo Acquisto (€)",
                    "sell_price_eur": "Prezzo Vendita (€)", "cost_basis_eur": "Costo Lotto (€)",
                    "proceeds_eur": "Incasso (€)", "realized_pnl_eur": "PnL Realizzato (€)",
                    "realized_pnl_pct": "Rendimento (%)", "holding_days": "Holding (gg)", "outcome": "Esito"
                })

                # Toolbar: Ricerca, Filtri e Download CSV per Registro Lotti
                col_lf1, col_lf2, col_lf3 = st.columns([2.0, 1.2, 1.1])
                with col_lf1:
                    search_gy_l = st.text_input("🔍 Cerca Ticker / Data / Settore:", key="search_gy_lots", placeholder="Es. BTC, 2024, META, Tecnologia...")
                with col_lf2:
                    outcomes_l = ["Tutti gli Esiti"] + sorted(list(df_l_show["Esito"].dropna().unique())) if "Esito" in df_l_show.columns else ["Tutti"]
                    filter_outcome_l = st.selectbox("🎯 Esito:", outcomes_l, key="filter_gy_outcome_lots")
                with col_lf3:
                    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                    csv_l = df_l_show.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica CSV", data=csv_l, file_name="registro_analitico_lotti_chiusi.csv", mime="text/csv", use_container_width=True, key="btn_download_gy_lots")

                df_l_filt = df_l_show.copy()
                if search_gy_l:
                    mask = df_l_filt["Ticker"].astype(str).str.contains(search_gy_l.strip(), case=False, na=False)
                    if "Data Acquisto" in df_l_filt.columns:
                        mask |= df_l_filt["Data Acquisto"].astype(str).str.contains(search_gy_l.strip(), case=False, na=False)
                    if "Data Vendita" in df_l_filt.columns:
                        mask |= df_l_filt["Data Vendita"].astype(str).str.contains(search_gy_l.strip(), case=False, na=False)
                    if "Settore" in df_l_filt.columns:
                        mask |= df_l_filt["Settore"].astype(str).str.contains(search_gy_l.strip(), case=False, na=False)
                    df_l_filt = df_l_filt[mask]
                if filter_outcome_l != "Tutti gli Esiti" and "Esito" in df_l_filt.columns:
                    df_l_filt = df_l_filt[df_l_filt["Esito"] == filter_outcome_l]

                cfg_l = {
                    "Prezzo Acquisto (€)": st.column_config.NumberColumn("Prezzo Acquisto (€)", format="€ %.2f"),
                    "Prezzo Vendita (€)": st.column_config.NumberColumn("Prezzo Vendita (€)", format="€ %.2f"),
                    "Costo Lotto (€)": st.column_config.NumberColumn("Costo Lotto (€)", format="€ %.2f"),
                    "Incasso (€)": st.column_config.NumberColumn("Incasso (€)", format="€ %.2f"),
                    "PnL Realizzato (€)": st.column_config.NumberColumn("PnL Realizzato (€)", format="€ %.2f"),
                    "Rendimento (%)": st.column_config.NumberColumn("Rendimento (%)", format="%.2f%%"),
                    "Holding (gg)": st.column_config.NumberColumn("Holding (gg)", format="%d gg")
                }
                st.dataframe(df_l_filt, use_container_width=True, hide_index=True, column_config=cfg_l)
            else:
                st.info("Nessun lotto chiuso disponibile.")


# ── TAB 3: PROIEZIONE DIVIDENDI ───────────────────────────────
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

            # Toolbar: Ricerca, Filtro Frequenza e Download CSV
            col_df1, col_df2, col_df3 = st.columns([2.0, 1.2, 1.1])
            with col_df1:
                search_div = st.text_input("🔍 Cerca Asset / Mesi:", key="search_div_table", placeholder="Es. ISP.MI, NOVO, Maggio, Trimestrale...")
            with col_df2:
                freqs = ["Tutte le Frequenze"] + sorted(list(df_table_show["Frequenza"].dropna().unique())) if "Frequenza" in df_table_show.columns else ["Tutte"]
                filter_freq = st.selectbox("⏳ Frequenza:", freqs, key="filter_div_freq")
            with col_df3:
                st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                csv_div = df_table_show.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_div, file_name="calendario_dividendi_stimati.csv", mime="text/csv", use_container_width=True, key="btn_download_div_table")

            df_table_filt = df_table_show.copy()
            if search_div:
                mask = df_table_filt["Asset / Ticker"].astype(str).str.contains(search_div.strip(), case=False, na=False)
                if "Mesi di Stacco Stimati" in df_table_filt.columns:
                    mask |= df_table_filt["Mesi di Stacco Stimati"].astype(str).str.contains(search_div.strip(), case=False, na=False)
                if "Frequenza" in df_table_filt.columns:
                    mask |= df_table_filt["Frequenza"].astype(str).str.contains(search_div.strip(), case=False, na=False)
                df_table_filt = df_table_filt[mask]
            if filter_freq != "Tutte le Frequenze" and "Frequenza" in df_table_filt.columns:
                df_table_filt = df_table_filt[df_table_filt["Frequenza"] == filter_freq]

            div_table_config = {
                "Dividend Yield": st.column_config.NumberColumn("Dividend Yield", format="%.2f%%"),
                "Yield on Cost (YOC)": st.column_config.NumberColumn("Yield on Cost (YOC)", format="%.2f%%"),
                "Incasso per Singolo Stacco": st.column_config.NumberColumn("Incasso per Singolo Stacco", format="€ %.2f"),
                "Stima Totale Annua": st.column_config.NumberColumn("Stima Totale Annua", format="€ %.2f"),
                "Storico Incassato Reale": st.column_config.NumberColumn("Storico Incassato Reale", format="€ %.2f")
            }

            st.dataframe(df_table_filt, use_container_width=True, hide_index=True, column_config=div_table_config)
        else:
            st.info("Nessuna posizione in portafoglio genera dividendi o cedole attive.")

    # ── MATRICE MENSILE DISTRIBUZIONE DIVIDENDI ──────────────────────
    if not df_matrix.empty:
        with st.expander("🗓️ Visualizza la Matrice Annuale Completa (Incassi Titolo per Mese)", expanded=False):
            st.caption("Importo monetario stimato (€) per ciascun mese dell'anno solare:")
            
            col_m1, col_m2 = st.columns([3.0, 1.1])
            with col_m2:
                csv_mat = df_matrix.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica Matrice CSV", data=csv_mat, file_name="matrice_annuale_dividendi.csv", mime="text/csv", use_container_width=True, key="btn_download_div_matrix")

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
    st.caption("Analisi delle plusvalenze realizzate, della stima delle imposte (aliquote 26% / 12.5%), fiscalità Cripto (L. 197/2022) ed opportunità di Tax-Loss Harvesting.")

    import importlib
    import core.tax_engine
    import core.crypto_tax_engine
    importlib.reload(core.tax_engine)
    importlib.reload(core.crypto_tax_engine)
    from core.tax_engine import compute_tax_and_harvesting
    from core.crypto_tax_engine import compute_crypto_tax_report

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

    sub_tax_mode = st.radio(
        "Regime Fiscale:",
        options=["🏦 Regime Ordinario (Azioni, ETF, Obbligazioni - TUIR Art. 67)", "🪙 Fisco Cripto-Attività & Quadri RT / RW / IVAFE (L. 197/2022)"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if sub_tax_mode.startswith("🏦"):
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
            metric_card("Zainetto Residuo", f"€ {tax_credit_val:,.2f}" if (tax_credit_val := tax_sum.get("tax_credit_zainetto_eur", 0.0)) else "€ 0.00", "Compensabile in 4 Anni", True)

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("#### 💡 Candidati Tax-Loss Harvesting (Riduzione Debito Fiscale)")
        st.caption("Posizioni attualmente in perdita latente compensabile per ridurre il carico fiscale sulle plusvalenze realizzate o accumulare credito d'imposta nello zainetto fiscale.")

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
            
            # Formattazione numerica standard
            for col in ["PnL Non Realizzato (€)", "Risparmio Fiscale Potenziale (€)", "Aliquota Fiscale %"]:
                if col in df_harv_disp.columns:
                    df_harv_disp[col] = pd.to_numeric(
                        df_harv_disp[col].astype(str).str.replace("%", "").str.replace("€", "").str.strip(),
                        errors="coerce"
                    ).fillna(0.0)

            # Toolbar: Ricerca, Filtro Classe Asset e Download CSV
            col_th_f1, col_th_f2, col_th_f3 = st.columns([2.0, 1.2, 1.1])
            with col_th_f1:
                search_th = st.text_input("🔍 Cerca Asset / TUIR:", key="search_tax_loss_cands", placeholder="Es. ENPH, ADA, Stock, Crypto...")
            with col_th_f2:
                cls_list = ["Tutte le Classi"] + sorted(list(df_harv_disp["Classe Asset"].dropna().unique())) if "Classe Asset" in df_harv_disp.columns else ["Tutte"]
                filter_th_cls = st.selectbox("🏷️ Classe Asset:", cls_list, key="filter_tax_loss_cls")
            with col_th_f3:
                st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                csv_th = df_harv_disp.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_th, file_name="candidati_tax_loss_harvesting.csv", mime="text/csv", use_container_width=True, key="btn_download_tax_loss_cands")

            df_harv_filt = df_harv_disp.copy()
            if search_th:
                mask = df_harv_filt["Ticker"].astype(str).str.contains(search_th.strip(), case=False, na=False)
                if "Tipologia Reddito (TUIR)" in df_harv_filt.columns:
                    mask |= df_harv_filt["Tipologia Reddito (TUIR)"].astype(str).str.contains(search_th.strip(), case=False, na=False)
                if "Classe Asset" in df_harv_filt.columns:
                    mask |= df_harv_filt["Classe Asset"].astype(str).str.contains(search_th.strip(), case=False, na=False)
                df_harv_filt = df_harv_filt[mask]
            if filter_th_cls != "Tutte le Classi" and "Classe Asset" in df_harv_filt.columns:
                df_harv_filt = df_harv_filt[df_harv_filt["Classe Asset"] == filter_th_cls]

            th_cfg = {
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Classe Asset": st.column_config.TextColumn("Classe Asset", width="small"),
                "PnL Non Realizzato (€)": st.column_config.NumberColumn("PnL Non Realizzato (€)", format="€ %.2f"),
                "Risparmio Fiscale Potenziale (€)": st.column_config.NumberColumn("Risparmio Fiscale Potenziale (€)", format="€ %.2f"),
                "Aliquota Fiscale %": st.column_config.NumberColumn("Aliquota Fiscale", format="%.1f%%"),
                "Tipologia Reddito (TUIR)": st.column_config.TextColumn("Tipologia Reddito (TUIR)", width="medium")
            }

            st.dataframe(
                df_harv_filt,
                column_config=th_cfg,
                use_container_width=True,
                hide_index=True
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
            
            col_txy_h1, col_txy_h2 = st.columns([3.5, 0.9])
            with col_txy_h2:
                csv_txy = df_tax_show.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_txy, file_name="imposte_plusvalenze_per_anno.csv", mime="text/csv", use_container_width=True, key="btn_download_tax_year")

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

            col_z_dh1, col_z_dh2 = st.columns([3.5, 0.9])
            with col_z_dh2:
                csv_zt = df_z_table_show.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_zt, file_name="timeline_zainetto_fiscale.csv", mime="text/csv", use_container_width=True, key="btn_download_zainetto_timeline")

            st.dataframe(
                df_z_table_show.style.format({
                    "Minusvalenza Iniziale (€)": "€ {:,.2f}",
                    "Compensato (€)": "€ {:,.2f}",
                    "Credito Residuo (€)": "€ {:,.2f}"
                }),
                use_container_width=True,
                hide_index=True
            )

        # ── WIZARD GUIDATO: TAX-LOSS HARVESTING & STEP-UP FISCALE ────────
        st.divider()
        col_wiz_h1, col_wiz_h2 = st.columns([3.2, 1.1])
        with col_wiz_h1:
            st.markdown("#### 🧙‍♂️ Tax-Loss Harvesting & Step-Up Wizard (TUIR Art. 67)")
            st.caption("Assistente decisionale per l'ottimizzazione del carico fiscale: compensazione delle minusvalenze in scadenza senza imposte e monetizzazione strategica delle perdite.")
        with col_wiz_h2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("🧙‍♂️ Guida allo Step-Up & Tax-Loss Harvesting", """
<div style="font-size: 13.5px; line-height: 1.45;">
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Cos'è lo Step-Up Fiscale e il Tax-Loss Harvesting</div>
  <div>1. <b>Step-Up:</b> Vendere e ricomprare titoli in guadagno (Redditi Diversi) per assorbire minusvalenze a imposta zero.<br>
  2. <b>Tax-Loss Harvesting:</b> Vendere posizioni in perdita per generare nuove minusvalenze compensative.</div>
</div>
</div>
""", button_label="💡 Come funziona il Wizard Fiscale?")

        from core.tax_engine import compute_tax_loss_harvesting_strategy
        def_zainetto = float(df_zainetto["residual_active_eur"].sum()) if not df_zainetto.empty else 2500.0
        
        with st.expander("⚙️ Parametri di Simulazione dello Zainetto Fiscale", expanded=True):
            col_w_in1, col_w_in2 = st.columns([2, 2])
            with col_w_in1:
                target_minus = st.number_input("Minusvalenze Totali da Compensare (€):", value=float(def_zainetto), step=250.0, min_value=0.0)
            with col_w_in2:
                reinvest_same_day = st.checkbox("Simula Reinvestimento Immediato (Step-Up Carico Fiscale)", value=True)

        strat_res = compute_tax_loss_harvesting_strategy(results, custom_zainetto_eur=target_minus)
        summary_w = strat_res.get("summary", {})
        df_harv_g = strat_res.get("df_step_up", pd.DataFrame())
        df_harv_l = strat_res.get("df_harvest_loss", pd.DataFrame())

        col_ws1, col_ws2, col_ws3, col_ws4 = st.columns(4)
        with col_ws1:
            metric_card("Zainetto da Compensare", f"€ {target_minus:,.2f}", "Obiettivo Fiscale", True)
        with col_ws2:
            metric_card("Minusvalenze Assorbibili", f"€ {strat_res.get('total_minus_consumed_eur', 0.0):,.2f}", f"Disponibili: € {target_minus:,.2f}", True)
        with col_ws3:
            metric_card("Risparmio Imposte Stimato", f"€ {strat_res.get('total_tax_savings_eur', 0.0):,.2f}", "0€ imposte su plusvalenze", True)
        with col_ws4:
            metric_card("Nuovo Scudo Fiscale", f"€ {strat_res.get('total_tax_shield_created_eur', 0.0):,.2f}", "Da chiusure in perdita", False)

        tab_w_gain, tab_w_loss = st.tabs(["🚀 Strategia Step-Up (Vendita Titoli in Utile)", "✂️ Tax-Loss Harvesting (Monetizzazione Perdite)"])

        with tab_w_gain:
            if not df_harv_g.empty:
                col_sg_h1, col_sg_h2 = st.columns([3.5, 0.9])
                with col_sg_h1:
                    st.markdown("##### 📋 Piano Operativo di Vendita / Riacquisto per Step-Up Fiscale")
                    st.caption("Esegui gli ordini di vendita indicati e riacquista immediatamente i titoli per innalzare il prezzo di carico a costo fiscale zero.")
                with col_sg_h2:
                    st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
                    csv_sg = df_harv_g.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica CSV", data=csv_sg, file_name="piano_step_up_fiscale.csv", mime="text/csv", use_container_width=True, key="btn_download_step_up")
                
                df_gain_show = df_harv_g[[
                    "ticker", "asset_class", "qty_held", "current_price_eur",
                    "unrealized_gain_eur", "consumable_minus_eur", "tax_saving_eur", "action"
                ]].rename(columns={
                    "ticker": "Ticker", "asset_class": "Asset Class", "qty_held": "Q.tà Totale",
                    "current_price_eur": "Prezzo Attuale (€)", "unrealized_gain_eur": "Plusvalenza Latente (€)",
                    "consumable_minus_eur": "Minus Compensabile (€)", "tax_saving_eur": "Risparmio Fiscale (€)",
                    "action": "Azione Consigliata"
                })
                st.dataframe(
                    df_gain_show.style.format({
                        "Prezzo Attuale (€)": "€ {:,.2f}",
                        "Plusvalenza Latente (€)": "€ {:,.2f}",
                        "Minus Compensabile (€)": "€ {:,.2f}",
                        "Risparmio Fiscale (€)": "€ {:,.2f}"
                    }),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("Nessuna posizione in utile su Redditi Diversi (azioni/bond) idonea per la compensazione dello zainetto fiscale.")

        with tab_w_loss:
            if not df_harv_l.empty:
                col_sl_h1, col_sl_h2 = st.columns([3.5, 0.9])
                with col_sl_h1:
                    st.markdown("##### ✂️ Titoli in Perdita per Generazione Nuovo Credito Fiscale")
                    st.caption("Monetizzare queste perdite permette di abbattere il debito fiscale dell'anno in corso o creare nuove minusvalenze con scadenza a 4 anni.")
                with col_sl_h2:
                    st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
                    csv_sl = df_harv_l.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica CSV", data=csv_sl, file_name="piano_tax_loss_harvesting.csv", mime="text/csv", use_container_width=True, key="btn_download_tax_harvesting")
                
                df_loss_show = df_harv_l[[
                    "ticker", "asset_class", "qty_held", "current_price_eur",
                    "unrealized_loss_eur", "loss_to_harvest_eur", "tax_shield_created_eur", "action"
                ]].rename(columns={
                    "ticker": "Ticker", "asset_class": "Asset Class", "qty_held": "Q.tà in Portafoglio",
                    "current_price_eur": "Prezzo Attuale (€)", "unrealized_loss_eur": "Perdita Latente (€)",
                    "loss_to_harvest_eur": "Minusvalenza Generabile (€)", "tax_shield_created_eur": "Scudo Fiscale Stimato (€)",
                    "action": "Azione Consigliata"
                })
                st.dataframe(
                    df_loss_show.style.format({
                        "Prezzo Attuale (€)": "€ {:,.2f}", "Perdita Latente (€)": "€ {:,.2f}",
                        "Minusvalenza Generabile (€)": "€ {:,.2f}", "Scudo Fiscale Stimato (€)": "€ {:,.2f}"
                    }),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("Nessuna posizione in perdita latente significativa da raccogliere.")

    # ══════════════════════════════════════════════════════════════════════
    # SEZIONE FISCO CRIPTO-ATTIVITÀ (L. 197/2022 & CIRCOLARE AdE 30/E/2023)
    # ══════════════════════════════════════════════════════════════════════
    else:
        col_cr_h1, col_cr_h2 = st.columns([3.2, 1.2])
        with col_cr_h1:
            st.markdown("#### 🪙 Fiscalità Cripto-Attività (Legge di Bilancio 197/2022 & Circolare AdE 30/E/2023)")
            st.caption("Quadro RT (Plusvalenze 26% & Franchigia 2.000€), Quadro RW (Monitoraggio Fiscale Codice 21), IVAFE (0,20%) e Zainetto Fiscale Cripto.")
        with col_cr_h2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            render_crypto_tax_modal(button_label="ℹ️ Normativa Fiscale Cripto (L. 197/2022)", use_popover=False)

        crypto_report = compute_crypto_tax_report(results, db_engine=engine, tax_year=tax_year_param)
        c_sum = crypto_report["summary"]
        df_c_rt = crypto_report["df_rt"]
        df_c_rw = crypto_report["df_rw"]
        df_c_zainetto = crypto_report["df_crypto_zainetto"]

        col_cr1, col_cr2, col_cr3, col_cr4 = st.columns(4)
        with col_cr1:
            metric_card(f"Controvalore Cripto ({selected_year})", f"€ {c_sum['total_crypto_portfolio_val_eur']:,.2f}", "Posizioni al 31/12 (Quadro RW)", True)
        with col_cr2:
            net_cr_pnl = c_sum['total_realized_gains_eur'] - c_sum['total_realized_losses_eur']
            franchigia_txt = "Esente (< 2.000€)" if (0 < net_cr_pnl <= 2000.0) else ("Soggetta a Imposta 26%" if net_cr_pnl > 2000.0 else "Nessuna Plusvalenza")
            metric_card("Plusvalenze Nette Cripto", f"€ {net_cr_pnl:,.2f}", franchigia_txt, net_cr_pnl <= 2000.0)
        with col_cr3:
            metric_card(f"Imposta Quadro RT (26%)", f"€ {c_sum['total_tax_due_rt_eur']:,.2f}", "Imposta Sostitutiva Plusvalenze", False)
        with col_cr4:
            metric_card("Imposta Valore / IVAFE (0,20%)", f"€ {c_sum['total_ivafe_rw_eur']:,.2f}", f"Totale Carico: € {c_sum['total_crypto_tax_burden_eur']:,.2f}", False)

        # 1. Prospetto Quadro RT
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_rt_h1, col_rt_h2 = st.columns([3.5, 0.9])
        with col_rt_h1:
            st.markdown("##### 📈 Quadro RT (Sezione II-B) — Plusvalenze su Cripto-Attività (Art. 67 c. 1 lett. c-sexies TUIR)")
        with col_rt_h2:
            if not df_c_rt.empty:
                csv_rt = df_c_rt.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_rt, file_name="quadro_rt_cripto.csv", mime="text/csv", use_container_width=True, key="btn_download_quadro_rt")

        if not df_c_rt.empty:
            df_rt_show = df_c_rt.rename(columns={
                "year": "Anno Fiscale",
                "realized_gains_eur": "Plusvalenze Realizzate (€)",
                "realized_losses_eur": "Minusvalenze Realizzate (€)",
                "net_pnl_eur": "Saldo Netto (€)",
                "prior_crypto_minus_deducted_eur": "Minusv. Cripto Dedotte (€)",
                "taxable_base_rt_eur": "Base Imponibile (€)",
                "tax_due_rt_eur": "Imposta Dovuta 26% (€)",
                "threshold_exempt": "Franchigia 2.000€ Applicata",
                "crypto_zainetto_residual_eur": "Zainetto Cripto Residuo (€)"
            })
            df_rt_show["Franchigia 2.000€ Applicata"] = df_rt_show["Franchigia 2.000€ Applicata"].apply(lambda x: "✅ Sì (Esente)" if x else "❌ No (Oltre Soglia)")
            st.dataframe(
                df_rt_show.style.format({
                    "Plusvalenze Realizzate (€)": "€ {:,.2f}",
                    "Minusvalenze Realizzate (€)": "€ {:,.2f}",
                    "Saldo Netto (€)": "€ {:,.2f}",
                    "Minusv. Cripto Dedotte (€)": "€ {:,.2f}",
                    "Base Imponibile (€)": "€ {:,.2f}",
                    "Imposta Dovuta 26% (€)": "€ {:,.2f}",
                    "Zainetto Cripto Residuo (€)": "€ {:,.2f}"
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Nessuna transazione di vendita o realizzo cripto registrata per il periodo selezionato.")

        # 2. Prospetto Quadro RW
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_rw_h1, col_rw_h2 = st.columns([3.5, 0.9])
        with col_rw_h1:
            st.markdown("##### 🌐 Quadro RW — Prospetto Monitoraggio Fiscale Attività Estere & Self-Custody (Codice 21)")
        with col_rw_h2:
            if not df_c_rw.empty:
                csv_rw = df_c_rw.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_rw, file_name="quadro_rw_cripto.csv", mime="text/csv", use_container_width=True, key="btn_download_quadro_rw")

        if not df_c_rw.empty:
            df_rw_show = df_c_rw.rename(columns={
                "quadro": "Quadro",
                "codice_investimento": "Codice Bene",
                "descrizione_bene": "Descrizione Cripto-Attività",
                "valore_iniziale_eur": "Valore Iniziale 01/01 (€)",
                "valore_finale_eur": "Valore Finale 31/12 (€)",
                "valore_massimo_eur": "Valore Massimo (€)",
                "giorni_detenzione": "Giorni Possesso",
                "quota_possesso_pct": "Quota Possesso %",
                "imposta_valore_ivafe_eur": "Imposta Valore / IVAFE 0,20% (€)"
            })
            st.dataframe(
                df_rw_show.style.format({
                    "Valore Iniziale 01/01 (€)": "€ {:,.2f}",
                    "Valore Finale 31/12 (€)": "€ {:,.2f}",
                    "Valore Massimo (€)": "€ {:,.2f}",
                    "Quota Possesso %": "{:.0f}%",
                    "Imposta Valore / IVAFE 0,20% (€)": "€ {:,.2f}"
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Nessuna posizione cripto aperta attualmente in portafoglio da monitorare nel Quadro RW.")

        # 3. Zainetto Fiscale Cripto Separato
        if not df_c_zainetto.empty:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            col_cz_h1, col_cz_h2 = st.columns([3.5, 0.9])
            with col_cz_h1:
                st.markdown("##### 📦 Zainetto Fiscale Cripto Separato (Minusvalenze Riportabili in 4 Anni)")
            with col_cz_h2:
                csv_cz = df_c_zainetto.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_cz, file_name="zainetto_fiscale_cripto.csv", mime="text/csv", use_container_width=True, key="btn_download_zainetto_cripto")

            df_cz_show = df_c_zainetto.rename(columns={
                "origin_year": "Anno Origine",
                "expiry_year": "Anno Scadenza",
                "initial_minus_eur": "Minusvalenza Iniziale (€)",
                "compensated_eur": "Compensato (€)",
                "residual_active_eur": "Credito Cripto Residuo (€)",
                "status": "Stato Fiscale"
            })
            st.dataframe(
                df_cz_show.style.format({
                    "Minusvalenza Iniziale (€)": "€ {:,.2f}",
                    "Compensato (€)": "€ {:,.2f}",
                    "Credito Cripto Residuo (€)": "€ {:,.2f}"
                }),
                use_container_width=True, hide_index=True
            )

# ── TAB 4: RISCHIO LIQUIDITÀ & ALMGREN-CHRISS ─────────────────
elif active_pos_tab == "⚡ Liquidità Almgren-Chriss":
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
            col_ac_h1, col_ac_h2 = st.columns([2.5, 1.0])
            with col_ac_h1:
                st.markdown("#### 📊 Dettaglio Impatto e Slippage per Asset")
            with col_ac_h2:
                csv_ac = df_ac.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica CSV", data=csv_ac, file_name="liquidita_almgren_chriss.csv", mime="text/csv", use_container_width=True, key="btn_download_almgren_chriss")

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

