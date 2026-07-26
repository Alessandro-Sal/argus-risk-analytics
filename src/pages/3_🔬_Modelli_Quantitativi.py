import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.ui_utils import inject_custom_css, metric_card, fmt_pct, glossary_modal, render_executive_badges, section

st.set_page_config(page_title="Modelli Quantitativi | ARGUS", page_icon="🔬", layout="wide")
inject_custom_css()

# Cache bust
from core.sidebar import render_sidebar
render_sidebar()

if "results" not in st.session_state:
    st.warning("Per favore, torna alla Home e carica un portafoglio.")
    st.stop()

results = st.session_state["results"]
m = results["metrics"]

st.title("🔬 Modelli Quantitativi & Simulazioni Stocastiche")
if "run_id" in st.session_state:
    st.caption(f"Run ID: {st.session_state['run_id']} | Portafoglio: {st.session_state.get('portfolio_name', 'N/A')} • Simulatore Monte Carlo 10.000 run, frontiera efficiente Markowitz/Ledoit-Wolf, hedging tattico e Brinson attribution.")
col_head1, col_head2 = st.columns([3.5, 1])
with col_head1:
    render_executive_badges(m)
with col_head2:
    glossary_modal("📚 Glossario dei Modelli Quantitativi", """
<ul style="margin-top:0; padding-left:20px;">
    <li style="margin-bottom:14px;"><b>Monte Carlo Multivariato:</b>
        <ul style="margin-top:4px;">
            <li>Metodo statistico che esegue 10.000 simulazioni stocastiche per proiettare i possibili valori futuri del portafoglio a 1 anno. La componente "Multivariata" preserva le reali matrici storiche di covarianza e correlazione tra gli asset (tramite Decomposizione di Cholesky).</li>
        </ul>
    </li>
    <li style="margin-bottom:14px;"><b>Frontiera Efficiente di Markowitz:</b>
        <ul style="margin-top:4px;">
            <li>Insieme dei portafogli ottimali che offrono il massimo rendimento atteso per un dato livello di rischio (o la minima volatilità per un dato rendimento target).</li>
        </ul>
    </li>
    <li style="margin-bottom:14px;"><b>Hedging Beta-Neutral:</b>
        <ul style="margin-top:4px;">
            <li>Tecnica per ridurre o azzerare la sensibilità del portafoglio ai movimenti del mercato tramite ETF Inversi senza liquidare le posizioni detentute.</li>
        </ul>
    </li>
</ul>
""", button_label="📚 Glossario Modelli Quantitativi")

st.divider()

ai = m.get("ai_insights", {})
mc = ai.get("montecarlo", {})
clusters = ai.get("asset_clusters", [])
opt = results.get("optimization", {})

# ── STRUTTURA IN TAB AD ALTA NAVIGABILITÀ ─────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Frontiera Markowitz & Rebalancing",
    "🎲 Monte Carlo & Clustering K-Means",
    "🛡️ Hedging Tattico & Tail Risk",
    "🎯 Attribuzione Brinson-Fachler"
])

# ── TAB 1: MARKOWITZ & LEDOIT-WOLF ────────────────────────────
with tab1:
    if opt and opt.get("tickers"):
        st.markdown("#### Ottimizzazione di Portafoglio (Markowitz Efficient Frontier)")
        st.caption(f"Confronta il tuo portafoglio attuale con le allocazioni ottimali (Stima Covarianza: **{opt.get('cov_type', 'Ledoit-Wolf Shrinkage')}**)")
        
        glossary_modal("ℹ️ Guida all'Ottimizzazione Ledoit-Wolf & Ribilanciamento", """
        <p><b>1. Cos'è la Covarianza Ledoit-Wolf Shrinkage?</b><br>
        La matrice di covarianza campionaria standard soffre di rumore di stima (specialmente con molti asset o campioni brevi). L'algoritmo di <b>Ledoit-Wolf Shrinkage</b> applica una contrazione (shrinkage) verso una matrice strutturata a singolo fattore, riducendo l'errore quadratico medio e rendendo i pesi ottimali di Markowitz estremamente più stabili e realistici.</p>
        
        <p><b>2. Come funziona il Calcolatore di Ribilanciamento?</b><br>
        Confronta i pesi percentuali del tuo portafoglio attuale con i pesi ideali (Max Sharpe o Min Volatility). Calcola la differenza monetaria in Euro e stima il <b>numero esatto di azioni o quote da Acquistare (+) o Vendere (-)</b> per allineare il portafoglio all'allocazione ottimale.</p>
        """, button_label="💡 Come funziona Ledoit-Wolf & Ribilanciamento?")
        
        col_opt1, col_opt2 = st.columns([2, 1])
        
        with col_opt1:
            raw_frontier = opt.get("frontier", {})
            frontier = pd.DataFrame(raw_frontier)
            if not frontier.empty:
                v_col = "volatility" if "volatility" in frontier.columns else ("risk" if "risk" in frontier.columns else frontier.columns[0])
                r_col = "return" if "return" in frontier.columns else (frontier.columns[1] if len(frontier.columns) > 1 else frontier.columns[0])
                
                frontier["vol_pct"] = frontier[v_col] * 100.0
                frontier["ret_pct"] = frontier[r_col] * 100.0
                
                fig_f = px.scatter(
                    frontier, x="vol_pct", y="ret_pct",
                    labels={"vol_pct": "Volatilità Annua %", "ret_pct": "Rendimento Atteso %"},
                    title="Frontiera Efficiente (Markowitz & Ledoit-Wolf Shrinkage)",
                    template="plotly_dark", height=420
                )
                fig_f.update_traces(
                    hovertemplate="<b>Portafoglio Ottimo sulla Frontiera</b><br>Volatilità: %{x:.2f}%<br>Rendimento Atteso: %{y:.2f}%<extra></extra>"
                )
                
                cur = opt.get("current", {})
                cur_v = cur.get("risk", cur.get("volatility", opt.get("current_vol", 0))) * 100.0
                cur_r = cur.get("return", opt.get("current_ret", 0)) * 100.0
                fig_f.add_trace(go.Scatter(
                    x=[cur_v], y=[cur_r], mode="markers+text",
                    name="Portafoglio Attuale", text=["Attuale"], textposition="top right",
                    marker=dict(size=14, color="#00ff66", symbol="star")
                ))
                
                ms = opt.get("max_sharpe", {})
                ms_v = ms.get("volatility", ms.get("risk", 0.0)) * 100.0 if ms else 0.0
                ms_r = ms.get("return", 0.0) * 100.0 if ms else 0.0

                mv = opt.get("min_vol", {})
                mv_v = mv.get("volatility", mv.get("risk", 0.0)) * 100.0 if mv else 0.0
                mv_r = mv.get("return", 0.0) * 100.0 if mv else 0.0

                if ms:
                    fig_f.add_trace(go.Scatter(
                        x=[ms_v], y=[ms_r], mode="markers+text",
                        name="Max Sharpe Ratio", text=["Max Sharpe"], textposition="top left",
                        marker=dict(size=12, color="#ff9900", symbol="diamond")
                    ))
                    
                if mv:
                    fig_f.add_trace(go.Scatter(
                        x=[mv_v], y=[mv_r], mode="markers+text",
                        name="Min Volatility", text=["Min Vol"], textposition="bottom right",
                        marker=dict(size=12, color="#00f3ff", symbol="circle")
                    ))

                # Dynamic axis range calculation so ALL points (Current, Max Sharpe, Min Vol, Cloud) fit perfectly
                all_vols = [frontier["vol_pct"].min(), frontier["vol_pct"].max(), cur_v, ms_v, mv_v]
                all_rets = [frontier["ret_pct"].min(), frontier["ret_pct"].max(), cur_r, ms_r, mv_r]
                all_vols = [v for v in all_vols if v > 0]
                all_rets = [r for r in all_rets]

                min_x = max(0, min(all_vols) - 2.0) if all_vols else 0
                max_x = max(all_vols) + 3.0 if all_vols else 30
                min_y = min(0, min(all_rets) - 2.0) if all_rets else 0
                max_y = max(all_rets) + 5.0 if all_rets else 40

                fig_f.update_xaxes(range=[min_x, max_x])
                fig_f.update_yaxes(range=[min_y, max_y])
                    
                fig_f.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
                )
                st.plotly_chart(fig_f, use_container_width=True)

        with col_opt2:
            st.markdown("**Confronto Allocazioni Ottimali**")
            cur = opt.get("current", {})
            ms = opt.get("max_sharpe", {})
            mv = opt.get("min_vol", {})
            
            if cur:
                cur_v = cur.get("risk", 0.0) * 100.0
                cur_r = cur.get("return", 0.0) * 100.0
                cur_s = cur.get("sharpe", 0.0)
                st.warning(f"⭐ **Portafoglio Attuale**\nRendimento: **{cur_r:.2f}%** | Volatilità: **{cur_v:.2f}%** | Sharpe: **{cur_s:.2f}**")
            if ms:
                ms_v = ms.get("volatility", ms.get("risk", 0.0)) * 100.0
                ms_r = ms.get("return", 0.0) * 100.0
                st.info(f"🏆 **Max Sharpe Ratio**\nRendimento: **{ms_r:.2f}%** | Volatilità: **{ms_v:.2f}%** | Sharpe: **{ms.get('sharpe', 0.0):.2f}**")
            if mv:
                mv_v = mv.get("volatility", mv.get("risk", 0.0)) * 100.0
                mv_r = mv.get("return", 0.0) * 100.0
                st.success(f"🛡️ **Minima Volatilità**\nRendimento: **{mv_r:.2f}%** | Volatilità: **{mv_v:.2f}%** | Sharpe: **{mv.get('sharpe', 0.0):.2f}**")

        st.divider()
        st.markdown("#### 🧮 Calcolatore di Ribilanciamento Tattico (Pesi & Quote Operative)")
        st.caption("Calcola gli ordini esatti di acquisto/vendita per riallineare il tuo portafoglio ai pesi ottimi di Markowitz o ad una strategia custom.")

        from core.rebalancer import compute_rebalancing_orders

        col_reb1, col_reb2, col_reb3 = st.columns([2, 1.5, 1])
        with col_reb1:
            target_strategy = st.radio(
                "Profilo Bersaglio di Ribilanciamento:",
                ["Max Sharpe (Markowitz)", "Minima Volatilità", "Equi-peso (Equal Weight)"],
                horizontal=True
            )
        with col_reb2:
            new_cash_input = st.number_input(
                "Nuova Cassa / Iniezione Liquidità (€):",
                value=0.0, step=500.0, format="%.2f",
                help="Inserisci un valore positivo per nuovi versamenti o negativo per prelievi di cassa."
            )
        with col_reb3:
            int_shares_flag = st.checkbox("Quote Intere", value=True, help="Arrotonda le quote agli interi.")

        mode_key = "max_sharpe" if "Max Sharpe" in target_strategy else ("min_vol" if "Minima" in target_strategy else "equal_weight")

        rebal_res = compute_rebalancing_orders(
            results,
            target_mode=mode_key,
            new_cash_eur=new_cash_input,
            integer_shares=int_shares_flag
        )

        df_orders = rebal_res.get("orders", pd.DataFrame())
        summary_orders = rebal_res.get("summary", {})

        if not df_orders.empty:
            def highlight_action(val):
                if str(val).startswith("BUY"):
                    return "color: #00ff66; font-weight: bold;"
                elif str(val).startswith("SELL"):
                    return "color: #ff3333; font-weight: bold;"
                return "color: #8b949e;"

            col_om1, col_om2, col_om3 = st.columns(3)
            with col_om1:
                st.metric("Valore Portafoglio Target", f"€ {summary_orders.get('target_total_value_eur', 0):,.2f}")
            with col_om2:
                st.metric("Totale Acquisti (€)", f"€ {summary_orders.get('total_buy_eur', 0):,.2f}")
            with col_om3:
                st.metric("Totale Vendite (€)", f"€ {summary_orders.get('total_sell_eur', 0):,.2f}")

            df_disp_orders = df_orders[["ticker", "action", "current_qty", "target_qty", "qty_delta", "last_price", "order_value_eur", "current_weight_pct", "target_weight_pct"]].rename(columns={
                "ticker": "Ticker", "action": "Azione Tattica", "current_qty": "Quote Attuali", "target_qty": "Quote Target",
                "qty_delta": "Quote Operative", "last_price": "Prezzo (€)", "order_value_eur": "Controvalore Ordine (€)",
                "current_weight_pct": "Peso Attuale %", "target_weight_pct": "Peso Target %"
            })

            st.dataframe(
                df_disp_orders.style.map(highlight_action, subset=["Azione Tattica"]).format({
                    "Quote Attuali": "{:,.2f}", "Quote Target": "{:,.2f}", "Quote Operative": "{:+,.2f}",
                    "Prezzo (€)": "€ {:,.2f}", "Controvalore Ordine (€)": "€ {:+,.2f}",
                    "Peso Attuale %": "{:.2f}%", "Peso Target %": "{:.2f}%"
                }),
                use_container_width=True, hide_index=True
            )
            
        # ── BACKTESTING ESTRATTO (HRP / MARKOWITZ / EQUI-PESO) ────────
        bt_data = opt.get("backtest", {})
        if bt_data:
            st.divider()
            st.markdown("#### ⏳ Backtesting Storico: Portafoglio vs Markowitz vs HRP vs S&P 500")
            st.caption("Verifica la performance out-of-sample storicizzata dei modelli di allocazione rispetto al mercato.")
            
            glossary_modal("ℹ️ Cos'è l'Hierarchical Risk Parity (HRP)?", """
            <p>L'<b>Hierarchical Risk Parity (HRP)</b> è un algoritmo avanzato sviluppato da Marcos López de Prado che sostituisce l'inversione della matrice di covarianza di Markowitz con un <b>clustering gerarchico sugli alberi delle correlazioni</b>. Genera allocazioni di portafoglio estremamente stabili e resistenti alle crisi fuori campione.</p>
            """, button_label="💡 Cos'è l'Hierarchical Risk Parity?")
            
            df_bt = pd.DataFrame(bt_data.get("equity_curves", {}))
            if not df_bt.empty and "date" in df_bt.columns:
                df_bt["date"] = pd.to_datetime(df_bt["date"])
                
                fig_bt = px.line(
                    df_bt, x="date", y=[c for c in df_bt.columns if c != "date"],
                    labels={"value": "Valore Indiciato (Base 100)", "date": "Data", "variable": "Strategia"},
                    title="Confronto Curve di Equity Storiche (Base 100)",
                    template="plotly_dark", height=400
                )
                fig_bt.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
                )
                st.plotly_chart(fig_bt, use_container_width=True)

    else:
        st.info("Dati di ottimizzazione di Markowitz non disponibili.")

# ── TAB 2: MONTE CARLO & CLUSTERING K-MEANS ───────────────────
with tab2:
    mc_col1, mc_col2 = st.columns([1, 2])
    with mc_col1:
        st.markdown("#### Monte Carlo Multivariato (10.000 iterazioni)")
        glossary_modal("Cos'è il Monte Carlo Multivariato?",
    "Simulazione avanzata tramite <b>Decomposizione di Cholesky</b>. Genera percorsi storici per i singoli asset rispettando le reali matrici di covarianza tra di essi.", button_label="💡 Come funziona?")
        if mc:
            metric_card("Expected Return (1Y)", fmt_pct(mc.get("expected_return_1y_pct")), positive=mc.get("expected_return_1y_pct", 0) >= 0, help_text="Rendimento medio atteso ad 1 anno su 10.000 simulazioni.")
            metric_card("Simulated VaR 95%", fmt_pct(mc.get("var_95_simulated_pct")), positive=False, help_text="Massima perdita percentuale stimata a 1 anno con 95% di confidenza.")
            metric_card("Simulated VaR 99%", fmt_pct(mc.get("var_99_simulated_pct")), positive=False, help_text="Massima perdita percentuale in uno scenario di stress estremo (99% confidenza).")
        else:
            st.info("Simulazione Monte Carlo non disponibile.")

    with mc_col2:
        st.markdown("#### K-Means Clustering: Asset per Profilo di Rischio")
        if clusters:
            df_cl = pd.DataFrame(clusters)
            df_cl["volatility"] = df_cl["volatility"] * 100
            df_cl["cagr"] = df_cl["cagr"] * 100
            df_cl["cluster"] = df_cl["cluster"].astype(str)
            
            fig_cl = px.scatter(
                df_cl, 
                x="volatility", y="cagr", color="cluster", text="ticker",
                labels={"volatility": "Volatilità Annua %", "cagr": "CAGR %", "cluster": "Cluster"},
                template="plotly_dark", height=400
            )
            fig_cl.update_traces(
                textposition="top center", marker=dict(size=12),
                hovertemplate="<b>%{text}</b> (Cluster %{fullData.name})<br>Volatilità Annua: %{x:.2f}%<br>CAGR: %{y:.2f}%<extra></extra>"
            )
            fig_cl.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_cl, use_container_width=True)

# ── TAB 3: HEDGING TATTICO & TAIL RISK ────────────────────────
with tab3:
    section("🛡️ Simulatore di Copertura & Hedging Tattico (Beta-Neutral & Tail Protection)")
    st.caption("Calcola le coperture esatte con ETF inversi o micro-futures per azzerare o ridurre la sensibilità al rischio sistemico senza vendere gli asset.")

    from core.hedging import compute_beta_neutral_hedge, HEDGE_INSTRUMENTS

    col_hd1, col_hd2 = st.columns(2)
    with col_hd1:
        target_beta_input = st.slider(
            "Target Beta Desiderato:",
            min_value=-0.50, max_value=1.50, value=0.00, step=0.10,
            help="Imposta 0.00 per renderti immune ai movimenti del mercato generale (Beta-Neutral)."
        )
    with col_hd2:
        hedge_inst_input = st.selectbox(
            "Strumento di Copertura:",
            options=list(HEDGE_INSTRUMENTS.keys()),
            format_func=lambda k: f"{k} - {HEDGE_INSTRUMENTS[k]['name']} ({HEDGE_INSTRUMENTS[k]['underlying']})"
        )

    hedge_res = compute_beta_neutral_hedge(results, target_beta=target_beta_input, hedge_ticker=hedge_inst_input)

    col_hm1, col_hm2, col_hm3, col_hm4 = st.columns(4)
    with col_hm1:
        st.metric("Beta Attuale Portafoglio", f"{hedge_res['current_beta']:.2f}")
    with col_hm2:
        st.metric("Valore Copertura Necessaria", f"€ {hedge_res['hedge_value_eur']:,.2f}")
    with col_hm3:
        st.metric(f"Quote {hedge_inst_input} da Acquistare", f"{hedge_res['hedge_shares']} quote")
    with col_hm4:
        st.metric("Protezione Tail Risk (VaR 99%)", f"€ {hedge_res['tail_risk_var99_eur']:,.2f}")

    st.info(f"""
    💡 **Indicazione Operativa di Copertura**:
    Per portare il Beta di portafoglio da **{hedge_res['current_beta']:.2f}** a **{target_beta_input:.2f}**, acquista **{hedge_res['hedge_shares']} quote** dello strumento **{hedge_res['instrument_name']} ({hedge_inst_input})** ad un prezzo indicativo di **€ {hedge_res['instrument_price']:.2f}** per un investimento protettivo di **€ {hedge_res['hedge_value_eur']:,.2f}**.
    """)

# ── TAB 4: ATTRIBUZIONE BRINSON-FACHLER ───────────────────────
with tab4:
    section("🎯 Attribuzione della Performance Brinson-Fachler")
    st.caption("Scompone l'extra-rendimento di portafoglio rispetto al Benchmark nei 3 fattori: Allocazione Settoriale, Selezione dei Titoli e Interazione.")

    import importlib
    import core.attribution
    importlib.reload(core.attribution)
    from core.attribution import compute_brinson_attribution

    attr_res = compute_brinson_attribution(results)
    attr_summary = attr_res["summary"]
    attr_df = attr_res["attribution_df"]

    col_att1, col_att2, col_att3, col_att4 = st.columns(4)
    with col_att1:
        st.metric("Rendimento Portafoglio", f"{attr_summary['portfolio_return_pct']:.2f}%")
    with col_att2:
        st.metric("Rendimento Benchmark", f"{attr_summary['benchmark_return_pct']:.2f}%")
    with col_att3:
        st.metric("Extra-Rendimento (Alpha)", f"{attr_summary['excess_return_pct']:+.2f}%")
    with col_att4:
        st.metric("Effetto Allocazione Totale", f"{attr_summary['total_allocation_effect_pct']:+.2f}%")

    if not attr_df.empty:
        st.markdown("**Scomposizione per Settore (Allocation vs Selection vs Interaction)**")
        fig_attr = px.bar(
            attr_df, x="sector", y=["allocation_effect_pct", "selection_effect_pct", "interaction_effect_pct"],
            barmode="group", title="Scomposizione Effetti per Settore GICS (%)",
            labels={
                "value": "Impatto %", "sector": "Settore", "variable": "Fattore Attribuzione",
                "allocation_effect_pct": "Allocation Effect",
                "selection_effect_pct": "Selection Effect",
                "interaction_effect_pct": "Interaction Effect"
            },
            template="plotly_dark", height=420
        )
        new_names = {
            "allocation_effect_pct": "Allocation Effect",
            "selection_effect_pct": "Selection Effect",
            "interaction_effect_pct": "Interaction Effect"
        }
        fig_attr.for_each_trace(lambda t: t.update(name=new_names.get(t.name, t.name)))
        fig_attr.update_traces(
            hovertemplate="<b>Settore: %{x}</b><br>%{fullData.name}: %{y:+.2f}%<extra></extra>"
        )
        fig_attr.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_attr, use_container_width=True)
