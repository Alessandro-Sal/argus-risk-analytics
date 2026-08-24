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
import core.execution_algo
importlib.reload(core.ui_utils)
importlib.reload(core.risk_engine)
importlib.reload(core.crypto_tax_engine)
importlib.reload(core.duckdb_engine)
importlib.reload(core.execution_algo)
from core.ui_utils import inject_custom_css, metric_card, fmt_eur, section, glossary_modal, render_command_bar, render_segmented_tabs, apply_plotly_theme, ensure_risk_bundle_loaded, render_sandbox_banner, render_corporate_actions_modal, render_crypto_tax_modal
from core.sidebar import render_sidebar
from core.execution_algo import compute_twap_schedule, compute_vwap_schedule, compare_execution_strategies, generate_intraday_volume_profile

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
st.markdown('<div style="margin-bottom: 8px;"></div>', unsafe_allow_html=True)

# ── STRUTTURA IN TAB CON LAZY LOADING ──────────────────────────
active_pos_tab = render_segmented_tabs([
    "📋 Posizioni Attive & Costi FIFO",
    "🪦 Posizioni Chiuse & Graveyard",
    "📅 Proiezione Dividendi",
    "💰 Ottimizzazione Fiscale (TUIR Art. 67)",
    "⚡ Liquidità & Smart Order Router"
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
        st.markdown("---")
        st.markdown("#### ⚡ Vista Analitica Aggregata DuckDB (Cubo OLAP Multi-Dimensionale)")
        st.caption("Aggregazione colonnare ad alta performance per Asset Class × Settore GICS × Valuta con scomposizione gerarchica.")
        from core.ui_utils import render_duckdb_olap_cube_widget
        render_duckdb_olap_cube_widget(df_l, key_prefix="p4_pos")

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
            col_m_sel, col_m_btn = st.columns([2.0, 1.1])
            with col_m_sel:
                selected_m = st.selectbox("Seleziona Mese da Ispezionare:", options=month_options, index=0, key="select_div_month_focus")
            
            if selected_m == "Tutti i Mesi con Incassi":
                if not df_events.empty and "month_num" in df_events.columns and "installment_payout_eur" in df_events.columns:
                    active_events = df_events.sort_values(by=["month_num", "installment_payout_eur"], ascending=[True, False])
                    df_disp_ev = active_events[["month_name", "ticker", "installment_payout_eur", "annual_payout_eur"]].rename(columns={
                        "month_name": "Mese", "ticker": "Asset", "installment_payout_eur": "Stacco", "annual_payout_eur": "Tot. Annuo"
                    })
                    with col_m_btn:
                        st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                        csv_m = df_disp_ev.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Scarica CSV", data=csv_m, file_name="dividendi_per_mese.csv", mime="text/csv", use_container_width=True, key="btn_download_div_m_all")

                    ev_cfg = {
                        "Mese": st.column_config.TextColumn("Mese", width="small"),
                        "Asset": st.column_config.TextColumn("Asset", width="small"),
                        "Stacco": st.column_config.NumberColumn("Stacco Singolo", format="€ %.2f"),
                        "Tot. Annuo": st.column_config.NumberColumn("Tot. Annuo", format="€ %.2f")
                    }
                    st.dataframe(
                        df_disp_ev,
                        column_config=ev_cfg,
                        use_container_width=True,
                        hide_index=True,
                        height=280
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
                    df_disp_ev = m_events[["ticker", "dividend_yield_pct", "installment_payout_eur", "annual_payout_eur"]].rename(columns={
                        "ticker": "Asset", "dividend_yield_pct": "Yield %", "installment_payout_eur": "Stacco", "annual_payout_eur": "Tot. Annuo"
                    })
                    with col_m_btn:
                        st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
                        csv_m = df_disp_ev.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Scarica CSV", data=csv_m, file_name=f"dividendi_{selected_m.lower()}.csv", mime="text/csv", use_container_width=True, key=f"btn_download_div_m_{m_num}")

                    st.success(f"🗓️ **{selected_m}**: Incasso Totale Stimato di **€ {tot_m:,.2f}**")
                    ev_cfg = {
                        "Asset": st.column_config.TextColumn("Asset", width="small"),
                        "Yield %": st.column_config.NumberColumn("Yield Dividendo", format="%.2f%%"),
                        "Stacco": st.column_config.NumberColumn("Stacco Singolo", format="€ %.2f"),
                        "Tot. Annuo": st.column_config.NumberColumn("Tot. Annuo", format="€ %.2f")
                    }
                    st.dataframe(
                        df_disp_ev,
                        column_config=ev_cfg,
                        use_container_width=True,
                        hide_index=True,
                        height=240
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
            col_m1, col_m2 = st.columns([3.4, 1.1])
            with col_m1:
                st.markdown('<div style="padding-top: 6px; font-size: 13.5px; color: #8b949e;">Importo monetario stimato (€) per ciascun mese dell\'anno solare:</div>', unsafe_allow_html=True)
            with col_m2:
                csv_mat = df_matrix.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica Matrice CSV", data=csv_mat, file_name="matrice_annuale_dividendi.csv", mime="text/csv", use_container_width=True, key="btn_download_div_matrix")

            matrix_config = {
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Yield %": st.column_config.NumberColumn("Yield %", format="%.2f%%"),
                "Frequenza": st.column_config.TextColumn("Frequenza", width="medium"),
                "Totale Annuo (€)": st.column_config.NumberColumn("Totale Annuo (€)", format="€ %.2f")
            }
            for m_l in ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]:
                matrix_config[m_l] = st.column_config.NumberColumn(m_l, format="€ %.2f")

            mat_height = min(480, max(220, 42 + len(df_matrix) * 38))
            st.dataframe(
                df_matrix,
                use_container_width=True,
                hide_index=True,
                column_config=matrix_config,
                height=mat_height
            )

# ── TAB 3: OTTIMIZZAZIONE FISCALE ─────────────────────────────
elif active_pos_tab == "💰 Ottimizzazione Fiscale (TUIR Art. 67)":
    section("💰 Ottimizzazione Fiscale & Tax-Loss Harvesting")
    st.caption("Analisi delle plusvalenze realizzate, della stima delle imposte (aliquote 26% / 12.5%), fiscalità Cripto (L. 197/2022) ed opportunità di Tax-Loss Harvesting.")

    import importlib
    import core.tax_engine
    import core.crypto_tax_engine
    importlib.reload(core.tax_engine)
    importlib.reload(core.crypto_tax_engine)
    from core.tax_engine import (
        compute_tax_and_harvesting,
        generate_tax_loss_harvesting_strategy,
        compute_riforma_fiscale_comparison,
        compute_modello_redditi_pf,
        compute_withholding_tax_analysis,
        simulate_fifo_lot_sale
    )
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
        tax_credit_val = tax_sum.get("tax_credit_zainetto_eur", 0.0)

        # ── 4 SUB-TABS FISCALI ISTITUZIONALI ──
        tab_tax_c1, tab_tax_c2, tab_tax_c3, tab_tax_c4 = st.tabs([
            "🏛️ Cockpit Fiscale & Riforma 2026",
            "📑 Modello Redditi PF (RT & RW)",
            "🇺🇸 Withholding Tax (Doppia Imposizione)",
            "🧮 Tax-Smart Lot Sizing (Pre-Trade FIFO)"
        ])

        # ══════════════════════════════════════════════════════════════════════
        # SUB-TAB 1: COCKPIT FISCALE, ZAINETTO & SIMULATORE RIFORMA 2026
        # ══════════════════════════════════════════════════════════════════════
        with tab_tax_c1:
            col_tx1, col_tx2, col_tx3, col_tx4 = st.columns(4)
            with col_tx1:
                sub_txt = f"Div: € {tax_sum['total_realized_gain_diversi_eur']:,.0f} | ETF: € {tax_sum['total_realized_gain_etf_eur']:,.0f}"
                metric_card(f"Plusvalenze ({selected_year})", f"€ {tax_sum['total_realized_gain_eur']:,.2f}", sub_txt, True)
            with col_tx2:
                metric_card(f"Minusvalenze ({selected_year})", f"€ {tax_sum['total_realized_loss_eur']:,.2f}", "Inviate a Zainetto Fiscale", False)
            with col_tx3:
                metric_card(f"Stima Imposte ({selected_year})", f"€ {tax_sum['estimated_tax_due_eur']:,.2f}", "Aliquote 26% / 12.5%", False)
            with col_tx4:
                metric_card("Zainetto Residuo", f"€ {tax_credit_val:,.2f}", "Compensabile in 4 Anni", True)

            # ── SIMULATORE RIFORMA FISCALE 2026 ──
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            col_rf_t1, col_rf_t2 = st.columns([3.2, 1.2])
            with col_rf_t1:
                st.markdown("##### 🔮 Simulatore Riforma Fiscale 2026 (Armonizzazione ETF & Compensazione 100%)")
                st.caption("Confronta il carico tributario tra il regime asimmetrico attuale e il nuovo regime unificato dove le plusvalenze da ETF compensano al 100% le minusvalenze.")
            with col_rf_t2:
                st.markdown('<div style="margin-top: 4px;"></div>', unsafe_allow_html=True)
                glossary_modal(
                    "💡 Come Funziona la Riforma Fiscale",
                    """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
<div style="background: rgba(255, 153, 0, 0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px;">
  <b style="color: #ff9900;">📜 Superamento dell'Asimmetria Fiscale</b><br>
  Attualmente i guadagni da ETF sono considerati <i>Redditi di Capitale</i> (tassati al 26% senza compensazione). Con la Riforma Fiscale, tutti i redditi finanziari confluiscono in un'unica categoria, consentendo di assorbire lo zainetto fiscale anche con gli ETF.
</div>
<div>ARGUS quantifica in tempo reale il <b>Tax Drag</b> risparmiato dal nuovo quadro normativo.</div>
</div>
"""
                )

            sim_regime = st.segmented_control(
                "Regime Normativo:",
                options=["🏦 TUIR Attuale (Asimmetrico)", "🔮 Riforma Fiscale Unificata (Armonizzata)"],
                default="🏦 TUIR Attuale (Asimmetrico)",
                key="seg_tax_reform_mode"
            )

            riforma_res = compute_riforma_fiscale_comparison(results, tax_year=tax_year_param)
            curr_reg = riforma_res["current_regime"]
            ref_reg = riforma_res["reformed_regime"]
            comp_reg = riforma_res["comparison"]

            if "Riforma" in (sim_regime or ""):
                st.markdown(f"""
                <div style="background: rgba(46, 160, 67, 0.12); border: 1px solid rgba(46, 160, 67, 0.35); border-left: 4px solid #3fb950; border-radius: 10px; padding: 14px 18px; margin: 10px 0 16px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 700; font-size: 15px; color: #3fb950;">✨ Vantaggio della Riforma Fiscale Unificata</div>
                            <div style="font-size: 13px; color: #c9d1d9; margin-top: 3px;">
                                Grazie alla compensazione estesa agli ETF, il tuo debito d'imposta scende da <b>€ {curr_reg['tax_due_eur']:,.2f}</b> a <b>€ {ref_reg['tax_due_eur']:,.2f}</b>.
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 11px; color: #8b949e; font-weight: 600;">RISPARMIO NETTO DIRETTO</div>
                            <div style="font-size: 22px; font-weight: 800; color: #3fb950;">€ {comp_reg['net_tax_savings_eur']:,.2f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # ── COCKPIT INTERATTIVO ZAINETTO FISCALE & HARVESTING OPTIMIZER ──
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            col_zf_h1, col_zf_h2 = st.columns([3.2, 1.2])
            with col_zf_h1:
                st.markdown("##### 💼 Simulatore Zainetto Fiscale & Generatore Ordini di Harvesting")
                st.caption("Algoritmo istituzionale di ottimizzazione fiscale: calcola il piano di realizzo minusvalenze e le strategie di Step-Up per azzerare le imposte sul capital gain.")
            with col_zf_h2:
                st.markdown('<div style="margin-top: 4px;"></div>', unsafe_allow_html=True)
                glossary_modal(
                    "📖 Guida Fiscale TUIR",
                    """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
<div style="background: rgba(255, 153, 0, 0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px;">
  <b style="color: #ff9900;">📜 Regola dei 4 Anni (TUIR Art. 67)</b><br>
  Le minusvalenze realizzate su azioni, obbligazioni e derivati possono essere compensate con future plusvalenze (Redditi Diversi) entro il 31 dicembre del 4° anno successivo a quello di realizzo.
</div>
<div><b>1. Raccolta Minusvalenze (Tax-Loss Harvesting):</b> Liquidare posizioni in perdita per accumulare credito fiscale immediato.<br>
<b>2. Step-Up a 0€ Imposte:</b> Vendere e ricomprare titoli in forte utile compensandoli con lo zainetto prima che scada.<br>
<b>3. Proxy Re-Entry:</b> Reinvestire in strumenti correlati per non perdere il trend di mercato.</div>
</div>
"""
                )

            col_z1, col_z2 = st.columns([2.0, 2.0])
            with col_z1:
                custom_zainetto = st.number_input(
                    "Saldo Zainetto Fiscale Pregresso da Compensare (€):",
                    value=float(tax_credit_val),
                    step=250.0, format="%.2f",
                    key="input_custom_zainetto_val",
                    help="Inserisci le minusvalenze pregresse accumulate presso la tua banca o broker (Directa, Fineco, Degiro, IBKR)."
                )
            with col_z2:
                tax_harvest_res = generate_tax_loss_harvesting_strategy(results, custom_zainetto_eur=custom_zainetto)
                tot_shield = tax_harvest_res.get("total_tax_shield_created_eur", 0.0)
                tot_saved = tax_harvest_res.get("total_tax_savings_eur", 0.0)
                st.markdown(f"""
                <div style="background: rgba(22, 27, 34, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 12px 18px; margin-top: 4px; display: flex; justify-content: space-around; text-align: center;">
                    <div>
                        <div style="font-size: 10.5px; color: #8b949e; font-weight: 600;">RISPARMIO STEP-UP (0€ TASSE)</div>
                        <div style="font-size: 17px; font-weight: 800; color: #3fb950;">€ {tot_saved:,.2f}</div>
                    </div>
                    <div style="border-left: 1px solid rgba(255,255,255,0.08);"></div>
                    <div>
                        <div style="font-size: 10.5px; color: #8b949e; font-weight: 600;">NUOVO CREDITO FISCALE</div>
                        <div style="font-size: 17px; font-weight: 800; color: #58a6ff;">€ {tot_shield:,.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            df_harvest_loss = tax_harvest_res.get("df_harvest_loss", pd.DataFrame())
            df_step_up = tax_harvest_res.get("df_step_up", pd.DataFrame())

            tab_harv1, tab_harv2 = st.tabs([
                f"✂️ Raccolta Minusvalenze & Proxy Re-Entry ({len(df_harvest_loss)})",
                f"🎯 Step-Up a 0€ Imposte ({len(df_step_up)})"
            ])

            with tab_harv1:
                if not df_harvest_loss.empty:
                    df_hl_disp = df_harvest_loss.rename(columns={
                        "ticker": "Ticker", "asset_class": "Classe Asset", "qty_held": "Quote Detenute",
                        "current_price_eur": "Prezzo (€)", "order_notional_eur": "Controvalore (€)",
                        "unrealized_loss_eur": "Minus Realizzabile (€)", "unrealized_loss_pct": "Loss %",
                        "tax_shield_created_eur": "Risparmio Fiscale (€)", "action": "Azione Consigliata",
                        "replacement_proxy": "Re-Entry Proxy Correlato", "rationale": "Logica Operativa"
                    })

                    col_hl1, col_hl2 = st.columns([3.5, 1.2])
                    with col_hl1:
                        st.caption("Esegui gli ordini di vendita per registrare le minusvalenze e reinvesti contestualmente nel proxy consigliato per mantenere l'esposizione al trend.")
                    with col_hl2:
                        csv_hl = df_hl_disp.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Scarica Ordini CSV", data=csv_hl, file_name="ordini_tax_loss_harvesting.csv", mime="text/csv", use_container_width=True, key="btn_download_orders_tax_harvest")

                    cfg_hl = {
                        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                        "Classe Asset": st.column_config.TextColumn("Classe", width="small"),
                        "Quote Detenute": st.column_config.NumberColumn("Quote", format="%.2f"),
                        "Prezzo (€)": st.column_config.NumberColumn("Prezzo", format="€ %.2f"),
                        "Controvalore (€)": st.column_config.NumberColumn("Controvalore", format="€ %.2f"),
                        "Minus Realizzabile (€)": st.column_config.NumberColumn("Minus (€)", format="€ %.2f"),
                        "Risparmio Fiscale (€)": st.column_config.NumberColumn("Risparmio Imposta", format="€ %.2f"),
                        "Azione Consigliata": st.column_config.TextColumn("Azione", width="medium"),
                        "Re-Entry Proxy Correlato": st.column_config.TextColumn("Proxy Re-Entry", width="medium"),
                    }

                    st.dataframe(
                        df_hl_disp[["Ticker", "Classe Asset", "Quote Detenute", "Prezzo (€)", "Controvalore (€)", "Minus Realizzabile (€)", "Risparmio Fiscale (€)", "Azione Consigliata", "Re-Entry Proxy Correlato"]],
                        column_config=cfg_hl, use_container_width=True, hide_index=True
                    )
                else:
                    st.info("Nessuna posizione in perdita latente da raccogliere.")

            with tab_harv2:
                if not df_step_up.empty:
                    df_su_disp = df_step_up.rename(columns={
                        "ticker": "Ticker", "asset_class": "Classe Asset", "qty_held": "Quote Detenute",
                        "current_price_eur": "Prezzo (€)", "unrealized_gain_eur": "Plusvalenza Latente (€)",
                        "consumable_minus_eur": "Minus Compensabile (€)", "tax_saving_eur": "Tasse Azzerate (€)",
                        "action": "Azione Consigliata", "replacement_proxy": "Re-Entry", "rationale": "Logica Operativa"
                    })

                    st.caption("Monetizza le plusvalenze compensandole al 100% con lo zainetto fiscale prima della scadenza dei 4 anni. Riacquista subito per alzare il prezzo di carico a 0€ di imposta.")
                    
                    cfg_su = {
                        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                        "Classe Asset": st.column_config.TextColumn("Classe", width="small"),
                        "Quote Detenute": st.column_config.NumberColumn("Quote", format="%.2f"),
                        "Prezzo (€)": st.column_config.NumberColumn("Prezzo", format="€ %.2f"),
                        "Plusvalenza Latente (€)": st.column_config.NumberColumn("Plusvalenza (€)", format="€ %.2f"),
                        "Minus Compensabile (€)": st.column_config.NumberColumn("Minus Compensata", format="€ %.2f"),
                        "Tasse Azzerate (€)": st.column_config.NumberColumn("Tasse Risparmiate", format="€ %.2f"),
                        "Azione Consigliata": st.column_config.TextColumn("Azione", width="medium"),
                    }

                    st.dataframe(
                        df_su_disp[["Ticker", "Classe Asset", "Quote Detenute", "Prezzo (€)", "Plusvalenza Latente (€)", "Minus Compensabile (€)", "Tasse Azzerate (€)", "Azione Consigliata"]],
                        column_config=cfg_su, use_container_width=True, hide_index=True
                    )
                else:
                    st.info("Nessun candidato per Step-Up a 0€ imposte (richiede posizioni in utile su Redditi Diversi e saldo zainetto attivo).")

            # ── TIMELINE SCADENZA ZAINETTO ──
            df_zainetto = tax_res.get("zainetto_timeline", pd.DataFrame())
            if not df_zainetto.empty:
                st.divider()
                st.markdown("##### ⏳ Timeline Zainetto Fiscale & Scadenze Quadriennali (TUIR Art. 68 c. 5)")
                st.caption("Tracciamento delle minusvalenze pregresse con scadenza quadriennale (compensabili entro il 31 dicembre del 4° anno successivo alla realizzazione).")

                df_z_plot = df_zainetto.copy()
                df_z_plot["Anno Origine (Scadenza)"] = df_z_plot.apply(lambda r: f"Origine {r['origin_year']} (Scade {r['expiry_year']})", axis=1)

                fig_z_timeline = px.bar(
                    df_z_plot, x="Anno Origine (Scadenza)", y=["residual_active_eur", "compensated_eur", "expired_eur"],
                    labels={"value": "Euro (€)", "variable": "", "Anno Origine (Scadenza)": ""},
                    color_discrete_map={"residual_active_eur": "#ff9900", "compensated_eur": "#3fb950", "expired_eur": "#f85149"},
                    barmode="stack", template="plotly_dark", height=320
                )
                legend_names = {"residual_active_eur": "Residuo Attivo", "compensated_eur": "Compensato", "expired_eur": "Scaduto"}
                fig_z_timeline.for_each_trace(lambda t: t.update(name=legend_names.get(t.name, t.name), hovertemplate="<b>%{x}</b><br>" + legend_names.get(t.name, t.name) + ": <b>€ %{y:,.2f}</b><extra></extra>"))
                fig_z_timeline.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=20, r=20, t=35, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11, color="#ffffff")))
                apply_plotly_theme(fig_z_timeline)
                st.plotly_chart(fig_z_timeline, use_container_width=True, config={"displayModeBar": False})

        # ══════════════════════════════════════════════════════════════════════
        # SUB-TAB 2: PROSPETTO PRECOMPILATO MODELLO REDDITI PF (QUADRO RT & RW)
        # ══════════════════════════════════════════════════════════════════════
        with tab_tax_c2:
            col_rt_h1, col_rt_h2 = st.columns([3.2, 1.2])
            with col_rt_h1:
                st.markdown("#### 📑 Prospetto Precompilato Modello Redditi Persone Fisiche")
                st.caption("Prospetto conforme per chi opera in **Regime Dichiarativo** (es. Interactive Brokers, Degiro, Scalable Capital, Revolut o Wallet Privati).")
            with col_rt_h2:
                st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
                glossary_modal(
                    "ℹ️ Istruzioni Modello Redditi PF",
                    """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
<div style="background: rgba(255, 153, 0, 0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px;">
  <b style="color: #ff9900;">🏛️ Come utilizzare questi prospetti</b><br>
  I dati calcolati riportano esattamente i codici rigo ministeriali per la compilazione della dichiarazione annuale dei redditi da parte del Commercialista o CAF.
</div>
<div><b>Quadro RT (Sez. II):</b> Plusvalenze su partecipazioni non qualificate assoggettate ad imposta sostitutiva del 26% (Codice tributo F24: <b>1100</b>).<br>
<b>Quadro RW:</b> Monitoraggio fiscale delle attività finanziarie detenute all'estero e liquidazione IVAFE (0,20%).</div>
</div>
"""
                )

            col_rt_in1, col_rt_in2 = st.columns([2.0, 2.0])
            with col_rt_in1:
                prior_minus_in = st.number_input(
                    "Minusvalenze Pregresse da Quadro RT Anno Precedente (€):",
                    value=float(tax_credit_val),
                    step=250.0, format="%.2f",
                    key="input_prior_minus_rt"
                )

            pf_res = compute_modello_redditi_pf(results, tax_year=tax_year_param, db_engine=engine, prior_minus_custom_eur=prior_minus_in)
            pf_sum = pf_res["summary"]
            df_rt_table = pf_res["df_quadro_rt"]
            df_rw_table = pf_res["df_quadro_rw"]

            col_pf1, col_pf2, col_pf3, col_pf4 = st.columns(4)
            with col_pf1:
                metric_card("Imposta Sostitutiva (RT)", f"€ {pf_sum['imposta_sostitutiva_rt_eur']:,.2f}", "Aliquota 26% F24 (Cod. 1100)", False)
            with col_pf2:
                metric_card("IVAFE Dovuta (RW)", f"€ {pf_sum['totale_ivafe_rw_eur']:,.2f}", "Esente se < 12€" if pf_sum["esenzione_ivafe_applicata"] else "0.20% su giacenza estera", False)
            with col_pf3:
                metric_card("Totale Debito F24", f"€ {pf_sum['totale_debito_dichiarativo_eur']:,.2f}", "RT26 + RW IVAFE", False)
            with col_pf4:
                metric_card("Minus Riportabili (RT25)", f"€ {pf_sum['minusvalenze_riportabili_eur']:,.2f}", "Valide per i prossimi 4 anni", True)

            st.markdown("##### 📋 Quadro RT — Sezione II (Plusvalenze & Minusvalenze Finanziarie)")
            col_rt_d1, col_rt_d2 = st.columns([3.5, 1.2])
            with col_rt_d2:
                csv_rt = df_rt_table.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Scarica Quadro RT CSV", data=csv_rt, file_name="quadro_rt_precompilato.csv", mime="text/csv", use_container_width=True, key="btn_download_rt_csv")

            st.dataframe(
                df_rt_table.rename(columns={"rigo": "Rigo", "descrizione": "Descrizione Ministeriale", "valore_eur": "Importo (€)"}),
                column_config={"Importo (€)": st.column_config.NumberColumn("Importo (€)", format="€ %.2f")},
                use_container_width=True, hide_index=True
            )

            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 🌍 Quadro RW — Monitoraggio Fiscale Attività Estere & Calcolo IVAFE")
            if not df_rw_table.empty:
                col_rw_d1, col_rw_d2 = st.columns([3.5, 1.2])
                with col_rw_d2:
                    csv_rw = df_rw_table.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica Quadro RW CSV", data=csv_rw, file_name="quadro_rw_precompilato.csv", mime="text/csv", use_container_width=True, key="btn_download_rw_csv")

                st.dataframe(
                    df_rw_table.rename(columns={
                        "rigo": "Rigo", "ticker": "Asset / Ticker", "asset_class": "Classe",
                        "codice_investimento": "Cod. Investimento", "codice_paese": "Cod. Paese",
                        "quota_possesso_pct": "Possesso %", "giorni_detenzione": "Giorni",
                        "valore_iniziale_eur": "Valore Iniziale (€)", "valore_finale_eur": "Valore Finale (€)",
                        "ivafe_calcolata_eur": "IVAFE (€)"
                    }),
                    column_config={
                        "Valore Iniziale (€)": st.column_config.NumberColumn("Valore Iniziale", format="€ %.2f"),
                        "Valore Finale (€)": st.column_config.NumberColumn("Valore Finale", format="€ %.2f"),
                        "IVAFE (€)": st.column_config.NumberColumn("IVAFE (0.2%)", format="€ %.2f"),
                        "Possesso %": st.column_config.NumberColumn("Possesso", format="%.0f%%")
                    },
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("Nessun asset estero rilevante ai fini del monitoraggio Quadro RW.")

        # ══════════════════════════════════════════════════════════════════════
        # SUB-TAB 3: WITHHOLDING TAX DIVIDENDI ESTERI (DOPPIA IMPOSIZIONE)
        # ══════════════════════════════════════════════════════════════════════
        with tab_tax_c3:
            col_wt_h1, col_wt_h2 = st.columns([3.2, 1.2])
            with col_wt_h1:
                st.markdown("#### 🇺🇸 Withholding Tax Dividendi Esteri & Doppia Imposizione")
                st.caption("Analisi dell'impatto fiscale sui dividendi azionari esteri (Ritenuta alla fonte W-8BEN + Ritenuta italiana al 26% sul netto frontiera).")
            with col_wt_h2:
                st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
                glossary_modal(
                    "📖 Guida Withholding Tax & Doppia Imposizione",
                    """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
<div style="background: rgba(255, 153, 0, 0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px;">
  <b style="color: #ff9900;">🇺🇸 Meccanismo della Doppia Imposizione</b><br>
  Sui dividendi azionari USA viene applicata la ritenuta alla fonte del <b>15%</b> (con W-8BEN). L'intermediario italiano applica poi il <b>26% sul netto frontiera (85%)</b>, portando l'aliquota effettiva reale al <b>37,10%</b>.
</div>
<div><b>Confronto con ETF ad Accumulazione:</b> Gli ETF UCITS trattengono internamente il 15% sul dividendo reinvestito senza subire la tassazione italiana immediata, eliminando il Tax Drag.</div>
</div>
"""
                )

            wht_res = compute_withholding_tax_analysis(results)
            wht_sum = wht_res["summary"]
            df_wht = wht_res["df_withholding"]

            col_w1, col_w2, col_w3, col_w4 = st.columns(4)
            with col_w1:
                metric_card("Dividendi Lordi Stimati", f"€ {wht_sum['total_gross_dividends_eur']:,.2f}", "Flusso Cedolare Lordo", True)
            with col_w2:
                metric_card("Ritenute Estere (WHT)", f"€ {wht_sum['total_foreign_wht_eur']:,.2f}", "Trattenute alla fonte", False)
            with col_w3:
                metric_card("Imposta Italia (26%)", f"€ {wht_sum['total_italian_tax_eur']:,.2f}", "Applicata su netto frontiera", False)
            with col_w4:
                metric_card("Aliquota Effettiva Media", f"{wht_sum['weighted_effective_tax_pct']:.2f}%", f"Tax Drag vs ETF: € {wht_sum['total_tax_drag_vs_accumulating_eur']:,.2f}", False)

            if not df_wht.empty:
                col_wd1, col_wd2 = st.columns([3.5, 1.2])
                with col_wd1:
                    st.markdown("##### 🔍 Breakdown Fiscale per Singolo Asset a Distribuzione")
                with col_wd2:
                    csv_wht = df_wht.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica Report WHT CSV", data=csv_wht, file_name="withholding_tax_report.csv", mime="text/csv", use_container_width=True, key="btn_download_wht_csv")

                st.dataframe(
                    df_wht.rename(columns={
                        "ticker": "Ticker", "asset_class": "Classe", "paese_regime": "Paese / Regime Fiscale",
                        "dividendo_lordo_eur": "Dividendo Lordo (€)", "ritenuta_estera_wht_eur": "WHT Estera (€)",
                        "aliquota_wht_pct": "Aliquota WHT %", "netto_frontiera_eur": "Netto Frontiera (€)",
                        "imposta_italiana_26_eur": "Imposta IT 26% (€)", "totale_imposte_eur": "Totale Imposte (€)",
                        "dividendo_netto_incassato_eur": "Netto Incassato (€)", "aliquota_effettiva_combinata_pct": "Aliquota Effettiva %",
                        "tax_drag_vs_accumulo_eur": "Tax Drag vs Accumulo (€)"
                    }),
                    column_config={
                        "Dividendo Lordo (€)": st.column_config.NumberColumn("Lordo (€)", format="€ %.2f"),
                        "WHT Estera (€)": st.column_config.NumberColumn("WHT Estera", format="€ %.2f"),
                        "Netto Frontiera (€)": st.column_config.NumberColumn("Netto Frontiera", format="€ %.2f"),
                        "Imposta IT 26% (€)": st.column_config.NumberColumn("Imposta IT 26%", format="€ %.2f"),
                        "Netto Incassato (€)": st.column_config.NumberColumn("Netto Reale", format="€ %.2f"),
                        "Aliquota Effettiva %": st.column_config.NumberColumn("Aliquota Effettiva", format="%.2f%%"),
                        "Tax Drag vs Accumulo (€)": st.column_config.NumberColumn("Tax Drag vs Acc.", format="€ %.2f"),
                    },
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("Nessuna posizione azionaria estera a dividendo presente in portafoglio.")

        # ══════════════════════════════════════════════════════════════════════
        # SUB-TAB 4: TAX-SMART LOT SIZING (SIMULATORE PRE-TRADE FIFO)
        # ══════════════════════════════════════════════════════════════════════
        with tab_tax_c4:
            col_ls_h1, col_ls_h2 = st.columns([3.2, 1.2])
            with col_ls_h1:
                st.markdown("#### 🧮 Tax-Smart Lot Sizing (Simulatore Pre-Trade FIFO)")
                st.caption("Simula la vendita parziale di un asset per prevedere con esattezza quali lotti storici verranno scaricati e l'imposta netta generata.")
            with col_ls_h2:
                st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
                glossary_modal(
                    "💡 Come Funziona il Lot Sizing FIFO",
                    """
<div style="font-size: 13.5px; line-height: 1.5; color: #c9d1d9;">
<div style="background: rgba(255, 153, 0, 0.08); border-left: 3px solid #ff9900; padding: 10px 14px; border-radius: 4px; margin-bottom: 12px;">
  <b style="color: #ff9900;">🎯 Principio First-In First-Out (FIFO)</b><br>
  L'Agenzia delle Entrate impone di liquidare prioritariamente le quote acquistate per prime. Quando vendi una quantità parziale, il simulatore calcola lo scorporo puntuale dei lotti per mostrarti il capital gain effettivo prima di confermare l'ordine sul broker.
</div>
</div>
"""
                )

            pos_df = results.get("positions", pd.DataFrame())
            active_pos_tickers = sorted(pos_df[pos_df["qty_net"] > 0]["ticker"].unique().tolist()) if not pos_df.empty and "qty_net" in pos_df.columns else []

            if active_pos_tickers:
                col_ls_in1, col_ls_in2, col_ls_in3 = st.columns([2.0, 1.5, 1.5])
                with col_ls_in1:
                    sel_lot_ticker = st.selectbox("Seleziona Titolo da Simulare:", options=active_pos_tickers, key="sel_lot_sizing_ticker")
                
                cur_lot_pos = pos_df[pos_df["ticker"] == sel_lot_ticker].iloc[0]
                cur_qty = float(cur_lot_pos.get("qty_net", 1.0))
                cur_price = float(cur_lot_pos.get("current_price", 100.0))

                with col_ls_in2:
                    qty_to_sell_input = st.number_input(
                        f"Quote da Vendere (Max: {cur_qty:,.2f}):",
                        min_value=0.01, max_value=float(cur_qty), value=float(min(cur_qty, max(1.0, round(cur_qty * 0.5, 2)))),
                        step=1.0 if cur_qty >= 10 else 0.1, key="input_qty_to_sell_sim"
                    )
                with col_ls_in3:
                    price_sell_input = st.number_input(
                        "Prezzo di Esecuzione Stimato (€):",
                        value=float(cur_price), step=1.0, format="%.2f", key="input_price_to_sell_sim"
                    )

                sim_res = simulate_fifo_lot_sale(results, ticker=sel_lot_ticker, qty_to_sell=qty_to_sell_input, sale_price=price_sell_input)

                col_lr1, col_lr2, col_lr3, col_lr4 = st.columns(4)
                with col_lr1:
                    metric_card("Controvalore Incassato", f"€ {sim_res['total_proceeds_eur']:,.2f}", f"Prezzo: € {sim_res['sale_price_eur']:.2f}", True)
                with col_lr2:
                    pnl_color = sim_res["total_realized_pnl_eur"] >= 0
                    metric_card("PnL Realizzato", f"€ {sim_res['total_realized_pnl_eur']:,.2f}", f"{sim_res['realized_pnl_pct']:+.2f}% vs costo FIFO", pnl_color)
                with col_lr3:
                    if sim_res["total_realized_pnl_eur"] >= 0:
                        metric_card("Imposta Stimata", f"€ {sim_res['estimated_tax_due_eur']:,.2f}", f"Aliquota: {sim_res['applicable_tax_rate_pct']:.1f}%", False)
                    else:
                        metric_card("Nuova Minusvalenza", f"€ {sim_res['minusvalenza_generata_eur']:,.2f}", "Credito zainetto fiscale", True)
                with col_lr4:
                    metric_card("Quote Residue in PTF", f"{sim_res['residual_shares']:,.2f}", f"Valore Residuo: € {sim_res['residual_value_eur']:,.2f}", True)

                st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                st.markdown(f"##### 📦 Dettaglio Lotti FIFO Scaricati per {sel_lot_ticker}")
                
                df_aff = sim_res.get("df_affected_lots", pd.DataFrame())
                if not df_aff.empty:
                    st.dataframe(
                        df_aff.rename(columns={
                            "data_lotto": "Data Acquisto", "quote_scaricate": "Quote Scaricate",
                            "prezzo_carico_lotto_eur": "Prezzo Carico (€)", "prezzo_vendita_eur": "Prezzo Vendita (€)",
                            "controvalore_lotto_eur": "Controvalore (€)", "costo_fiscale_lotto_eur": "Costo FIFO (€)",
                            "pnl_lotto_eur": "PnL Lotto (€)", "pnl_lotto_pct": "PnL %",
                            "imposta_stimata_eur": "Imposta (€)", "tipo_reddito": "Tipologia Fiscale"
                        }),
                        column_config={
                            "Quote Scaricate": st.column_config.NumberColumn("Quote", format="%.2f"),
                            "Prezzo Carico (€)": st.column_config.NumberColumn("Prezzo Carico", format="€ %.2f"),
                            "Prezzo Vendita (€)": st.column_config.NumberColumn("Prezzo Vendita", format="€ %.2f"),
                            "Controvalore (€)": st.column_config.NumberColumn("Controvalore", format="€ %.2f"),
                            "PnL Lotto (€)": st.column_config.NumberColumn("PnL Lotto", format="€ %.2f"),
                            "Imposta (€)": st.column_config.NumberColumn("Imposta Stimata", format="€ %.2f"),
                            "PnL %": st.column_config.NumberColumn("PnL %", format="%+.2f%%")
                        },
                        use_container_width=True, hide_index=True
                    )
            else:
                st.info("Nessuna posizione attiva in portafoglio disponibile per la simulazione.")

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

# ── TAB 5: RISCHIO LIQUIDITÀ & SMART ORDER ROUTER ─────────────
elif active_pos_tab == "⚡ Liquidità & Smart Order Router":
    col_head_ac1, col_head_ac2 = st.columns([3.2, 1.1])
    with col_head_ac1:
        st.markdown("#### ⚡ Impatto di Mercato, Liquidità & Smart Order Router (TWAP/VWAP)")
        st.caption("Stima dello slippage e dei costi di esecuzione imposti dal mercato durante la smobilizzazione o il ri-bilanciamento delle posizioni con algoritmi istituzionali.")
    with col_head_ac2:
        st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
        glossary_modal("ℹ️ Guida ad Almgren-Chriss & Smart Order Router", """
<div style="font-size: 13.5px; line-height: 1.45;">

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📌 Smart Order Routing Istituzionale (TWAP & VWAP)</div>
  <div>Tecniche di suddivisione temporale e volumetrica (Order Slicing) per eseguire grandi ordini minimizzando il Market Impact e l'asimmetria informativa sul book:</div>
  <div style="margin-top: 5px; color: #ffb74d;">
    • <b>TWAP (Time-Weighted Average Price):</b> Suddivide l'ordine in tranche temporali costanti con jitter stocastico per evitare rilevamenti e front-running algoritmico.<br>
    • <b>VWAP (Volume-Weighted Average Price):</b> Pesa le tranche in base alla curva di liquidità intraday a "U", concentrando gli scambi in apertura e chiusura dove la profondità del book è massima.
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">📐 Modello Almgren-Chriss (2000)</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 5px 0; color: #ffb74d; font-size: 12px; line-height: 1.45;">
    • <b>Impatto Temporaneo:</b> &eta; &middot; (v / V)<sup>0.5</sup> &middot; &sigma; (pressione immediata sul book ordini)<br>
    • <b>Impatto Permanente:</b> &gamma; &middot; (V<sub>tot</sub> / ADV) &middot; &sigma; (spostamento strutturale del Fair Value)
  </div>
</div>

<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px 14px;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">⚙️ POV Cap (Percentage of Volume)</div>
  <div>Per limitare l'impatto sul book, il router fissa un tetto massimo di partecipazione (tipicamente 10%-15% del volume dell'intervallo).</div>
</div>

</div>
""", button_label="💡 Guida Execution Router")

    from core.risk_engine import compute_almgren_chriss_market_impact, compute_almgren_chriss_optimal_execution
    df_ac = compute_almgren_chriss_market_impact(pos)
    
    if not df_ac.empty:
        # Sezione 1: Overview Tabellare
        col_t1, col_t2 = st.columns([3.0, 1.0])
        with col_t1:
            st.markdown("##### 📊 Profilo di Rischio Liquidità per Asset")
        with col_t2:
            csv_ac = df_ac.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Scarica CSV", data=csv_ac, file_name="liquidita_almgren_chriss.csv", mime="text/csv", use_container_width=True, key="btn_download_almgren_chriss")

        st.dataframe(
            df_ac,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Valore (€)": st.column_config.NumberColumn("Valore", format="€ %,.2f"),
                "ADV (€)": st.column_config.NumberColumn("Volume Medio Giornaliero (ADV)", format="€ %,.2f"),
                "Partecipazione (% ADV)": st.column_config.NumberColumn("Quota su ADV", format="%.2f%%"),
                "Giorni Liquidazione (10% ADV)": st.column_config.NumberColumn("Giorni Stimati (10% ADV)", format="%.2f gg"),
                "Impatto Permanente (€)": st.column_config.NumberColumn("Impatto Perm.", format="€ %,.2f"),
                "Impatto Temporaneo (€)": st.column_config.NumberColumn("Impatto Temp.", format="€ %,.2f"),
                "Costo Totale (€)": st.column_config.NumberColumn("Costo Stimato", format="€ %,.2f"),
                "Costo (bps)": st.column_config.NumberColumn("Slippage", format="%.1f bps"),
                "Rischio Liquidità": st.column_config.TextColumn("Livello Rischio")
            },
            hide_index=True,
            use_container_width=True
        )

        st.markdown("<hr style='border: 0; border-top: 1px solid rgba(255,255,255,0.08); margin: 24px 0;'>", unsafe_allow_html=True)

        # ── SEZIONE 2: SIMULATORE DI TRAIETTORIA OTTIMALE ALMGREN-CHRISS ───
        col_tr1, col_tr2 = st.columns([3.0, 1.2])
        with col_tr1:
            st.markdown("#### 🎯 Traiettoria Ottimale di Smobilizzo Multi-Day (Almgren-Chriss)")
            st.caption("Modellazione stocastica della velocità ottima di disinvestimento per bilanciare market impact e volatility risk.")
        with col_tr2:
            st.markdown('<div style="margin-top: 6px;"></div>', unsafe_allow_html=True)
            glossary_modal("💡 Come funziona la Traiettoria Ottimale Almgren-Chriss", """
<div style="font-size: 13.5px; line-height: 1.45;">
  <div style="font-weight: 700; color: #58a6ff; margin-bottom: 3px;">🎯 Teoria dell'Esecuzione Ottimale (Almgren &amp; Chriss, 2000)</div>
  <div>La traiettoria ottima di disinvestimento risolve l'equazione differenziale di secondo ordine:</div>
  <div style="background: rgba(255,153,0,0.08); border-left: 3px solid #ff9900; padding: 6px 10px; border-radius: 6px; margin: 6px 0; color: #ffb74d; font-family: monospace; font-size: 12px;">
    x(t) = X &middot; sinh(&kappa; (T &minus; t)) / sinh(&kappa; T)
  </div>
  <div>dove <i>&kappa;</i> rappresenta il parametro di urgenza che dipende dall'avversione al rischio (&lambda;), dalla volatilità (&sigma;) e dall'elasticità del book (&eta;).</div>
</div>
""", button_label="💡 Come funziona?")

        col_opt_ctrl1, col_opt_ctrl2, col_opt_ctrl3 = st.columns([1.5, 1.5, 1.5])
        
        # Scelta asset o totale
        all_ac_tickers = ["Intero Portafoglio (€ " + f"{pos['current_value'].sum():,.0f}".replace(",", ".") + ")"] + list(df_ac["Ticker"].unique()) if ("current_value" in pos.columns and not pos.empty) else ["Intero Portafoglio (€ 100.000)"]
        with col_opt_ctrl1:
            sel_target = st.selectbox("Seleziona Ordine da Liquidare:", all_ac_tickers, index=0, key="ac_sel_target_box")
            if "Intero Portafoglio" in sel_target:
                target_order_val = float(pos["current_value"].sum()) if ("current_value" in pos.columns and pos["current_value"].sum() > 0) else 100_000.0
                target_adv = target_order_val * 5.0 # ADV aggregato prudenziale
                target_vol = 22.0
            else:
                sel_row = pos[pos["ticker"] == sel_target] if "ticker" in pos.columns else pd.DataFrame()
                target_order_val = float(sel_row["current_value"].iloc[0]) if (not sel_row.empty and "current_value" in sel_row.columns) else 10_000.0
                target_adv = target_order_val * 8.0
                target_vol = 28.0

        with col_opt_ctrl2:
            exec_horizon = st.slider("Orizzonte di Liquidazione (Giorni T):", min_value=1, max_value=20, value=5, step=1, key="ac_exec_horizon_sl")
            spread_bps_ac = st.slider("Bid-Ask Spread Stimato (bps):", min_value=5, max_value=80, value=15, step=5, key="ac_spread_sl")

        with col_opt_ctrl3:
            lambda_choice = st.select_slider(
                "Avversione al Rischio (λ):",
                options=[0.0, 1e-7, 5e-7, 1e-6, 5e-6, 1e-5, 5e-5],
                value=1e-6,
                format_func=lambda l: "0.0 (Risk-Neutral TWAP)" if l == 0.0 else (f"{l:.1e} (Aggressivo)" if l >= 1e-5 else f"{l:.1e} (Bilanciato)"),
                key="ac_lambda_sl"
            )
            n_steps = st.slider("Intervalli di Esecuzione (N Slices):", min_value=5, max_value=30, value=15, step=5, key="ac_n_steps_sl")

        exec_res = compute_almgren_chriss_optimal_execution(
            order_value=target_order_val,
            adv_value=target_adv,
            volatility_ann_pct=target_vol,
            horizon_days=float(exec_horizon),
            n_intervals=n_steps,
            risk_aversion_lambda=lambda_choice,
            bid_ask_spread_bps=float(spread_bps_ac)
        )

        df_sched = exec_res["schedule_df"]

        # KPI Cards
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        with col_k1:
            metric_card("Costo Atteso E[x]", f"€ {exec_res['expected_cost_amount']:,.2f}", f"{exec_res['expected_cost_bps']:.1f} bps su nozionale")
        with col_k2:
            metric_card("Execution Risk (Std Dev)", f"€ {exec_res['execution_std_amount']:,.2f}", "Incertezza prezzo durante trade")
        with col_k3:
            metric_card("Execution VaR (95%)", f"€ {exec_res['execution_var_95_amount']:,.2f}", "Costo massimo al 95% conf.")
        with col_k4:
            metric_card("Half-Life di Liquidazione", f"{exec_res['half_life_days']:.2f} gg", f"Parametro Urgenza κ: {exec_res['kappa']:.3f}")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        col_f1, col_f2 = st.columns([1.6, 1.0])
        with col_f1:
            st.markdown("##### 📉 Traiettorie di Smobilizzo a Confronto")
            t_vals = [0.0] + list(df_sched["Giorno"])
            opt_vals = [exec_res["order_value"]] + list(df_sched["Posizione Residua (€)"])
            twap_vals = [exec_res["order_value"]] + list(df_sched["Traiettoria TWAP (€)"])
            agg_vals = [exec_res["order_value"]] + list(df_sched["Traiettoria Aggressiva (€)"])

            fig_traj = go.Figure()
            fig_traj.add_trace(go.Scatter(
                x=t_vals, y=opt_vals,
                mode="lines+markers", name="Traiettoria Ottimale (Almgren-Chriss)",
                line=dict(color="#ff9900", width=3.5),
                marker=dict(size=6, color="#ff9900")
            ))
            fig_traj.add_trace(go.Scatter(
                x=t_vals, y=twap_vals,
                mode="lines", name="TWAP Lineare (Risk-Neutral)",
                line=dict(color="#58a6ff", width=2, dash="dash")
            ))
            fig_traj.add_trace(go.Scatter(
                x=t_vals, y=agg_vals,
                mode="lines", name="Esecuzione Aggressiva (High Urgency)",
                line=dict(color="#f85149", width=1.8, dash="dot")
            ))
            fig_traj.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(13,17,23,0.7)",
                margin=dict(l=20, r=20, t=30, b=20),
                height=340,
                xaxis=dict(title="Tempo di Esecuzione (Giorni)", gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(title="Posizione Residua (€)", gridcolor="rgba(255,255,255,0.06)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            apply_plotly_theme(fig_traj)
            st.plotly_chart(fig_traj, use_container_width=True, config={"displayModeBar": "hover", "displaylogo": False})

        with col_f2:
            st.markdown("##### 🍩 Scomposizione Costi di Esecuzione")
            bd = exec_res["cost_breakdown"]
            fig_bd = go.Figure(data=[go.Pie(
                labels=["Impatto Temporaneo", "Impatto Permanente", "Bid-Ask Spread"],
                values=[bd["temporary_impact_amount"], bd["permanent_impact_amount"], bd["spread_cost_amount"]],
                hole=0.55,
                marker=dict(colors=["#58a6ff", "#f85149", "#ff9900"]),
                textinfo="percent",
                textposition="inside",
                hovertemplate="<b>%{label}</b><br>Costo: <b>€ %{value:,.2f}</b><br>Quota: <b>%{percent}</b><extra></extra>"
            )])
            fig_bd.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=30, b=20),
                height=340,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            apply_plotly_theme(fig_bd)
            st.plotly_chart(fig_bd, use_container_width=True, config={"displayModeBar": False})

        # Tabella Schedule di Trading
        col_sch_h1, col_sch_h2 = st.columns([3.0, 1.0])
        with col_sch_h1:
            st.markdown("##### 📋 Tabella di Esecuzione a Scaglioni (Order Slicing Schedule)")
        with col_sch_h2:
            csv_sched = df_sched.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Scarica Schedule CSV", data=csv_sched, file_name=f"execution_schedule_{exec_horizon}d.csv", mime="text/csv", use_container_width=True, key="btn_dl_exec_sched")

        st.dataframe(
            df_sched,
            column_config={
                "Intervallo": st.column_config.TextColumn("Fetta"),
                "Giorno": st.column_config.NumberColumn("Giorno", format="%.2f"),
                "Posizione Residua (€)": st.column_config.NumberColumn("Posizione Residua", format="€ %,.2f"),
                "Flusso Liquidato (€)": st.column_config.NumberColumn("Da Vendere", format="€ %,.2f"),
                "Velocità Vendita (€/giorno)": st.column_config.NumberColumn("Velocità (€/g)", format="€ %,.2f"),
                "Costo Step (€)": st.column_config.NumberColumn("Costo Fetta", format="€ %,.2f"),
                "Costo Cumulato (€)": st.column_config.NumberColumn("Costo Cumulato", format="€ %,.2f"),
                "% Liquidata": st.column_config.NumberColumn("% Eseguita", format="%.1f%%")
            },
            hide_index=True,
            use_container_width=True
        )

        st.markdown("<hr style='border: 0; border-top: 1px solid rgba(255,255,255,0.08); margin: 28px 0;'>", unsafe_allow_html=True)

        # ── SEZIONE 3: SMART ORDER ROUTER INTRADAY (TWAP & VWAP) ────────────
        st.markdown("#### 🤖 Smart Order Router Intraday (TWAP & VWAP Slicing Engine)")
        st.caption("Pianificazione operativa delle tranche di negoziazione intraday (09:00 - 17:30) per minimizzare lo slippage su ordini consistenti.")

        # Rilevamento completo e robusto dei ticker disponibili
        avail_tickers = []
        for c in ["ticker", "Ticker", "symbol", "Symbol", "Asset"]:
            if c in pos.columns:
                cands = [str(x).strip() for x in pos[c].dropna().unique() if str(x).strip() and str(x).strip().upper() not in ["UNKNOWN", "NAN", "NONE", "SAMPLE_STOCK"]]
                if cands:
                    avail_tickers = cands
                    break
        if not avail_tickers and not df_ac.empty and "Ticker" in df_ac.columns:
            avail_tickers = [str(x).strip() for x in df_ac["Ticker"].dropna().unique() if str(x).strip() and str(x).strip().upper() not in ["UNKNOWN", "NAN", "NONE", "SAMPLE_STOCK"]]
        if not avail_tickers and "tickers" in results and results["tickers"]:
            avail_tickers = [str(x).strip() for x in results["tickers"] if str(x).strip()]

        col_sor1, col_sor2, col_sor3, col_sor4 = st.columns([1.5, 1.2, 1.2, 1.1])
        with col_sor1:
            sel_asset_mode = st.selectbox(
                "Paniere Operativo",
                options=["Singolo Titolo da Smobilizzare", "Paniere Intero Portafoglio (Pro-Quota)"],
                key="sor_asset_mode"
            )
        with col_sor2:
            if sel_asset_mode == "Singolo Titolo da Smobilizzare" and avail_tickers:
                sel_ticker = st.selectbox("Seleziona Titolo", options=avail_tickers, key="sor_single_tk")
            else:
                sel_ticker = "PORTFOLIO_BASKET"
                st.markdown("<div style='padding-top: 28px; font-weight: 600; color: #58a6ff;'>Tutti gli Asset Aperti</div>", unsafe_allow_html=True)

        with col_sor3:
            sel_window = st.selectbox(
                "Orizzonte di Sessione",
                options=[
                    "Sessione Intera (09:00 - 17:30, 16 tranche da 30m)",
                    "Sessione Mattina (09:00 - 13:00, 8 tranche da 30m)",
                    "Sessione Pomeriggio (14:00 - 17:30, 7 tranche da 30m)",
                    "Esecuzione Rapida (2 Ore, 8 tranche da 15m)"
                ],
                key="sor_window_mode"
            )
        with col_sor4:
            pov_cap = st.slider("POV Participation Cap", min_value=5, max_value=30, value=15, step=5, format="%d%%", key="sor_pov_cap")

        # Map interval parameters
        if "16 tranche" in sel_window:
            n_interv = 16
            start_t = "09:00"
            interv_min = 30
        elif "Mattina" in sel_window:
            n_interv = 8
            start_t = "09:00"
            interv_min = 30
        elif "Pomeriggio" in sel_window:
            n_interv = 7
            start_t = "14:00"
            interv_min = 30
        else:
            n_interv = 8
            start_t = "10:00"
            interv_min = 15

        def _extract_order_info(row_data, fallback_tk="ASSET"):
            # Ticker
            tk = None
            for c in ["ticker", "Ticker", "symbol", "Symbol", "Asset"]:
                if c in row_data and pd.notna(row_data[c]):
                    v = str(row_data[c]).strip()
                    if v and v.upper() not in ["UNKNOWN", "NAN", "NONE"]:
                        tk = v
                        break
            if not tk:
                tk = fallback_tk

            # Controvalore
            c_val = 0.0
            for c in ["current_value", "Controvalore (€)", "value", "valore", "Valore (€)", "notional"]:
                if c in row_data and pd.notna(row_data[c]):
                    try:
                        c_val = float(str(row_data[c]).replace("€", "").replace(" ", "").replace(",", "."))
                        if c_val > 0:
                            break
                    except Exception:
                        pass

            # Prezzo
            p = 0.0
            for c in ["last_price", "current_price", "Prezzo Mkt (€)", "price", "prezzo", "close", "wacp", "Prezzo Carico (€)"]:
                if c in row_data and pd.notna(row_data[c]):
                    try:
                        p = float(str(row_data[c]).replace("€", "").replace(" ", "").replace(",", "."))
                        if p > 0:
                            break
                    except Exception:
                        pass

            # Quantità
            q = 0.0
            for c in ["qty_net", "quantity", "shares", "Quantità", "qty", "quote", "Quote"]:
                if c in row_data and pd.notna(row_data[c]):
                    try:
                        q = float(str(row_data[c]).replace(" ", "").replace(",", "."))
                        if q > 0:
                            break
                    except Exception:
                        pass

            if q <= 0 and c_val > 0 and p > 0:
                q = c_val / p
            elif q > 0 and p <= 0 and c_val > 0:
                p = c_val / q
            elif q <= 0 and c_val > 0:
                p = 100.0
                q = c_val / p
            elif q <= 0:
                q = 100.0
                p = 100.0 if p <= 0 else p

            # ADV
            adv = 0.0
            for c in ["adv", "ADV (€)", "volume", "avg_daily_volume", "Volume"]:
                if c in row_data and pd.notna(row_data[c]):
                    try:
                        adv = float(str(row_data[c]).replace("€", "").replace(" ", "").replace(",", "."))
                        if adv > 0:
                            break
                    except Exception:
                        pass
            if adv <= 0:
                adv = max(500_000.0, (q * p) * 15.0)

            return {
                "ticker": str(tk),
                "action": "SELL",
                "quantity": max(1.0, float(q)),
                "price": max(0.01, float(p)),
                "adv": max(10_000.0, float(adv))
            }

        # Build order list
        orders_for_sor = []
        if sel_asset_mode == "Singolo Titolo da Smobilizzare" and avail_tickers and sel_ticker in avail_tickers:
            # Trova riga in pos
            match_row = None
            if not pos.empty:
                for _, r in pos.iterrows():
                    for c in ["ticker", "Ticker", "symbol", "Symbol", "Asset"]:
                        if c in r and str(r[c]).strip() == str(sel_ticker).strip():
                            match_row = r
                            break
                    if match_row is not None:
                        break
            if match_row is not None:
                orders_for_sor.append(_extract_order_info(match_row, fallback_tk=sel_ticker))
            elif not df_ac.empty and "Ticker" in df_ac.columns:
                match_ac = df_ac[df_ac["Ticker"] == sel_ticker]
                if not match_ac.empty:
                    orders_for_sor.append(_extract_order_info(match_ac.iloc[0], fallback_tk=sel_ticker))
        elif not pos.empty:
            for _, r in pos.iterrows():
                ord_item = _extract_order_info(r)
                orders_for_sor.append(ord_item)
        elif not df_ac.empty:
            for _, r in df_ac.iterrows():
                ord_item = _extract_order_info(r)
                orders_for_sor.append(ord_item)

        if not orders_for_sor and avail_tickers:
            for tk in avail_tickers[:5]:
                orders_for_sor.append({
                    "ticker": tk,
                    "action": "SELL",
                    "quantity": 100.0,
                    "price": 100.0,
                    "adv": 500_000.0
                })
        elif not orders_for_sor:
            orders_for_sor.append({
                "ticker": "AAPL",
                "action": "SELL",
                "quantity": 100.0,
                "price": 150.0,
                "adv": 1_000_000.0
            })

        comp_exec = compare_execution_strategies(
            orders_for_sor,
            start_time_str=start_t,
            interval_minutes=interv_min,
            n_intervals=n_interv,
            pov_cap_pct=float(pov_cap) / 100.0
        )
        
        twap_data = comp_exec["twap"]
        vwap_data = comp_exec["vwap"]
        comp_summary = comp_exec["comparison"]

        tot_notional_val = comp_summary.get("total_notional_eur", 0.0)
        mkt_cost_val = comp_summary.get("market_order_cost_eur", 0.0)
        vwap_cost_val = comp_summary.get("vwap_cost_eur", 0.0)
        vwap_save_val = comp_summary.get("vwap_savings_vs_market_eur", 0.0)
        avg_slip = vwap_data.get("summary", {}).get("avg_slippage_bps", 0.0)

        # Scorecards Comparazione Algoritmi
        col_sc1, col_sc2, col_sc3, col_sc4 = st.columns(4)
        with col_sc1:
            metric_card("Controvalore Ordine", f"€ {tot_notional_val:,.2f}", f"{len(orders_for_sor)} ordini pianificati")
        with col_sc2:
            metric_card("Costo Esecuzione Blocco (Market)", f"€ {mkt_cost_val:,.2f}", "Slippage 25.0 bps (blocco unico)")
        with col_sc3:
            metric_card("Costo VWAP Istituzionale", f"€ {vwap_cost_val:,.2f}", f"Slippage medio: {avg_slip:.1f} bps")
        with col_sc4:
            metric_card("Risparmio Netto Stimato", f"€ {vwap_save_val:,.2f}", f"Risparmio vs Market: € {vwap_save_val:,.2f}", positive=True)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        col_algo_tab1, col_algo_tab2 = st.tabs(["📊 VWAP Execution Schedule (Liquidity-Matched)", "⏱️ TWAP Execution Schedule (Uniform Jitter)"])

        with col_algo_tab1:
            df_vwap_sched = vwap_data["schedule_df"]
            if not df_vwap_sched.empty:
                col_g1, col_g2 = st.columns([1.5, 1.0])
                unique_ts = df_vwap_sched["timestamp"].unique()
                agg_notional_t = [df_vwap_sched[df_vwap_sched["timestamp"] == t]["order_notional_eur"].sum() for t in unique_ts]
                
                # Calcolo aggregate POV rate
                agg_pov_rates = []
                for t in unique_ts:
                    df_slice_t = df_vwap_sched[df_vwap_sched["timestamp"] == t]
                    total_slice_eur = df_slice_t["order_notional_eur"].sum()
                    total_mkt_eur = (df_slice_t["interval_mkt_vol"] * df_slice_t["benchmark_price_eur"]).sum()
                    if total_mkt_eur > 0:
                        agg_pov_rates.append(round((total_slice_eur / total_mkt_eur) * 100.0, 2))
                    else:
                        agg_pov_rates.append(round(float(df_slice_t["pov_rate_pct"].mean()), 2))

                max_p = max(agg_pov_rates) if agg_pov_rates else 1.0

                with col_g1:
                    fig_vwap = go.Figure()
                    fig_vwap.add_trace(go.Bar(
                        x=unique_ts,
                        y=agg_notional_t,
                        name="Controvalore Tranche (€)",
                        marker_color="#58a6ff",
                        opacity=0.85
                    ))
                    fig_vwap.add_trace(go.Scatter(
                        x=unique_ts,
                        y=agg_pov_rates,
                        name="Participation Rate (% Mkt)",
                        yaxis="y2",
                        mode="lines+markers",
                        line=dict(color="#ff9900", width=2.5),
                        marker=dict(size=5, color="#ff9900")
                    ))
                    fig_vwap.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(13,17,23,0.7)",
                        height=310,
                        margin=dict(l=20, r=20, t=30, b=20),
                        yaxis=dict(title="Controvalore Tranche (€)", gridcolor="rgba(255,255,255,0.06)"),
                        yaxis2=dict(title="Partecipazione (% Mkt)", overlaying="y", side="right", showgrid=False, rangemode="tozero", range=[0, max(1.0, max_p * 1.5)]),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    apply_plotly_theme(fig_vwap)
                    st.plotly_chart(fig_vwap, use_container_width=True)

                with col_g2:
                    # Traiettoria unica aggregata di avanzamento
                    cum_prog_vals = []
                    tot_order_notional = df_vwap_sched["order_notional_eur"].sum()
                    running_notional = 0.0
                    for t in unique_ts:
                        running_notional += df_vwap_sched[df_vwap_sched["timestamp"] == t]["order_notional_eur"].sum()
                        cum_prog_vals.append(round((running_notional / max(1.0, tot_order_notional)) * 100.0, 1))

                    fig_cum = go.Figure()
                    fig_cum.add_trace(go.Scatter(
                        x=unique_ts,
                        y=cum_prog_vals,
                        mode="lines+markers",
                        name="Avanzamento Globale (%)",
                        line=dict(color="#58a6ff", width=3),
                        marker=dict(size=6, color="#58a6ff"),
                        fill="tozeroy",
                        fillcolor="rgba(88,166,255,0.12)"
                    ))
                    fig_cum.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(13,17,23,0.7)",
                        height=310,
                        margin=dict(l=20, r=20, t=30, b=20),
                        yaxis=dict(title="% Avanzamento", range=[0, 105], gridcolor="rgba(255,255,255,0.06)"),
                        xaxis=dict(title="Orario", gridcolor="rgba(255,255,255,0.06)"),
                        showlegend=False
                    )
                    apply_plotly_theme(fig_cum)
                    st.plotly_chart(fig_cum, use_container_width=True)

                col_vwap_h1, col_vwap_h2 = st.columns([3.0, 1.0])
                with col_vwap_h1:
                    st.markdown("##### 📋 Tabella Dettagliata Tranche VWAP")
                with col_vwap_h2:
                    csv_vwap = df_vwap_sched.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica Ordini FIX/CSV", data=csv_vwap, file_name="vwap_orders_schedule.csv", mime="text/csv", use_container_width=True, key="btn_dl_vwap_sched")

                st.dataframe(
                    df_vwap_sched[[
                        "tranche_idx", "timestamp", "ticker", "action", "slice_qty", "cum_progress_pct",
                        "order_notional_eur", "benchmark_price_eur", "est_exec_price_eur", "est_slippage_bps", "pov_rate_pct"
                    ]],
                    column_config={
                        "tranche_idx": st.column_config.NumberColumn("#", format="%d", width="small"),
                        "timestamp": st.column_config.TextColumn("Orario", width="small"),
                        "ticker": st.column_config.TextColumn("Ticker", width="small"),
                        "action": st.column_config.TextColumn("Azione", width="small"),
                        "slice_qty": st.column_config.NumberColumn("Quote Tranche", format="%,.2f"),
                        "cum_progress_pct": st.column_config.NumberColumn("% Eseguita", format="%.1f%%"),
                        "order_notional_eur": st.column_config.NumberColumn("Controvalore (€)", format="€ %,.2f"),
                        "benchmark_price_eur": st.column_config.NumberColumn("Prezzo Riferimento (€)", format="€ %,.2f"),
                        "est_exec_price_eur": st.column_config.NumberColumn("Prezzo Esecuzione Stimato (€)", format="€ %,.2f"),
                        "est_slippage_bps": st.column_config.NumberColumn("Slippage (bps)", format="%.1f bps"),
                        "pov_rate_pct": st.column_config.NumberColumn("POV Rate", format="%.2f%%")
                    },
                    hide_index=True,
                    use_container_width=True
                )

        with col_algo_tab2:
            df_twap_sched = twap_data["schedule_df"]
            if not df_twap_sched.empty:
                col_g1_tw, col_g2_tw = st.columns([1.5, 1.0])
                unique_ts_tw = df_twap_sched["timestamp"].unique()
                agg_notional_tw = [df_twap_sched[df_twap_sched["timestamp"] == t]["order_notional_eur"].sum() for t in unique_ts_tw]
                
                with col_g1_tw:
                    fig_twap = go.Figure()
                    fig_twap.add_trace(go.Bar(
                        x=unique_ts_tw,
                        y=agg_notional_tw,
                        name="Controvalore TWAP (€)",
                        marker_color="#a371f7",
                        opacity=0.85
                    ))
                    fig_twap.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(13,17,23,0.7)",
                        height=310,
                        margin=dict(l=20, r=20, t=30, b=20),
                        yaxis=dict(title="Controvalore Tranche (€)", gridcolor="rgba(255,255,255,0.06)"),
                        xaxis=dict(title="Orario", gridcolor="rgba(255,255,255,0.06)"),
                        showlegend=False
                    )
                    apply_plotly_theme(fig_twap)
                    st.plotly_chart(fig_twap, use_container_width=True)

                with col_g2_tw:
                    cum_prog_tw = []
                    tot_notional_tw = df_twap_sched["order_notional_eur"].sum()
                    running_tw = 0.0
                    for t in unique_ts_tw:
                        running_tw += df_twap_sched[df_twap_sched["timestamp"] == t]["order_notional_eur"].sum()
                        cum_prog_tw.append(round((running_tw / max(1.0, tot_notional_tw)) * 100.0, 1))

                    fig_cum_tw = go.Figure()
                    fig_cum_tw.add_trace(go.Scatter(
                        x=unique_ts_tw,
                        y=cum_prog_tw,
                        mode="lines+markers",
                        name="Avanzamento TWAP (%)",
                        line=dict(color="#a371f7", width=3),
                        marker=dict(size=6, color="#a371f7"),
                        fill="tozeroy",
                        fillcolor="rgba(163,113,247,0.12)"
                    ))
                    fig_cum_tw.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(13,17,23,0.7)",
                        height=310,
                        margin=dict(l=20, r=20, t=30, b=20),
                        yaxis=dict(title="% Avanzamento", range=[0, 105], gridcolor="rgba(255,255,255,0.06)"),
                        xaxis=dict(title="Orario", gridcolor="rgba(255,255,255,0.06)"),
                        showlegend=False
                    )
                    apply_plotly_theme(fig_cum_tw)
                    st.plotly_chart(fig_cum_tw, use_container_width=True)

                col_twap_h1, col_twap_h2 = st.columns([3.0, 1.0])
                with col_twap_h1:
                    st.markdown("##### 📋 Tabella Dettagliata Tranche TWAP (Uniform Time Jitter)")
                with col_twap_h2:
                    csv_twap = df_twap_sched.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Scarica Ordini TWAP CSV", data=csv_twap, file_name="twap_orders_schedule.csv", mime="text/csv", use_container_width=True, key="btn_dl_twap_sched")

                st.dataframe(
                    df_twap_sched[[
                        "tranche_idx", "timestamp", "ticker", "action", "slice_qty", "cum_progress_pct",
                        "order_notional_eur", "benchmark_price_eur", "est_exec_price_eur", "est_slippage_bps", "pov_rate_pct"
                    ]],
                    column_config={
                        "tranche_idx": st.column_config.NumberColumn("#", format="%d", width="small"),
                        "timestamp": st.column_config.TextColumn("Orario", width="small"),
                        "ticker": st.column_config.TextColumn("Ticker", width="small"),
                        "action": st.column_config.TextColumn("Azione", width="small"),
                        "slice_qty": st.column_config.NumberColumn("Quote Tranche", format="%,.2f"),
                        "cum_progress_pct": st.column_config.NumberColumn("% Eseguita", format="%.1f%%"),
                        "order_notional_eur": st.column_config.NumberColumn("Controvalore (€)", format="€ %,.2f"),
                        "benchmark_price_eur": st.column_config.NumberColumn("Prezzo Riferimento (€)", format="€ %,.2f"),
                        "est_exec_price_eur": st.column_config.NumberColumn("Prezzo Esecuzione Stimato (€)", format="€ %,.2f"),
                        "est_slippage_bps": st.column_config.NumberColumn("Slippage (bps)", format="%.1f bps"),
                        "pov_rate_pct": st.column_config.NumberColumn("POV Rate", format="%.2f%%")
                    },
                    hide_index=True,
                    use_container_width=True
                )

    else:
        st.info("Impossibile calcolare il modello Almgren-Chriss: posizioni attive o dati di volume non sufficienti.")
