import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.ui_utils import inject_custom_css, metric_card, fmt_pct, glossary_modal, render_executive_badges, section, render_formula_popover, apply_plotly_theme, render_command_bar
from core.hrp_optimizer import compute_hrp_portfolio
from core.options_hedging import black_scholes_pricing, compute_portfolio_delta_hedge, compute_covered_call_yield_enhancement

st.set_page_config(page_title="Modelli Quantitativi | ARGUS", page_icon="🔬", layout="wide")
inject_custom_css()

# Cache bust
from core.sidebar import render_sidebar
render_sidebar()
render_command_bar()

if "results" not in st.session_state:
    st.warning("Per favore, torna alla Home e carica un portafoglio.")
    st.stop()

results = st.session_state["results"]
m = results.get("metrics", {})
pos = results.get("positions", pd.DataFrame())

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
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Frontiera Markowitz & Rebalancing",
    "🎲 Simulazioni Stocastiche (Monte Carlo & Merton)",
    "🛡️ Hedging Tattico & Tail Risk",
    "🎯 Attribuzione Brinson-Fachler",
    "🏛️ Modelli Fattoriali, Black-Litterman & ML"
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
                    template="plotly_dark", height=440
                )
                # Cloud di punti Monte Carlo traslucida per non nascondere i marcatori chiave
                fig_f.update_traces(
                    marker=dict(opacity=0.35, size=5, color="#58a6ff"),
                    hovertemplate="<b>Portafoglio Simulato</b><br>Volatilità: %{x:.2f}%<br>Rendimento Atteso: %{y:.2f}%<extra></extra>"
                )
                
                cur = opt.get("current", {})
                cur_v = cur.get("risk", cur.get("volatility", opt.get("current_vol", 0))) * 100.0
                cur_r = cur.get("return", opt.get("current_ret", 0)) * 100.0
                
                ms = opt.get("max_sharpe", {})
                ms_v = ms.get("volatility", ms.get("risk", 0.0)) * 100.0 if ms else 0.0
                ms_r = ms.get("return", 0.0) * 100.0 if ms else 0.0

                mv = opt.get("min_vol", {})
                mv_v = mv.get("volatility", mv.get("risk", 0.0)) * 100.0 if mv else 0.0
                mv_r = mv.get("return", 0.0) * 100.0 if mv else 0.0

                # 1. Portafoglio Attuale (Stella Verde Smeraldo in primo piano con bordo luminoso)
                fig_f.add_trace(go.Scatter(
                    x=[cur_v], y=[cur_r], mode="markers+text",
                    name="Portafoglio Attuale", text=["⭐ Attuale"], textposition="top center",
                    marker=dict(
                        size=20,
                        color="#00e676",
                        symbol="star",
                        line=dict(width=2.5, color="#ffffff")
                    ),
                    textfont=dict(color="#00e676", size=13, family="Arial Black")
                ))

                # 2. Max Sharpe Ratio
                if ms:
                    fig_f.add_trace(go.Scatter(
                        x=[ms_v], y=[ms_r], mode="markers+text",
                        name="Max Sharpe Ratio", text=["🏆 Max Sharpe"], textposition="top left",
                        marker=dict(
                            size=16,
                            color="#ff9900",
                            symbol="diamond",
                            line=dict(width=2, color="#ffffff")
                        ),
                        textfont=dict(color="#ff9900", size=13, family="Arial Black")
                    ))
                    
                # 3. Minima Volatilità
                if mv:
                    fig_f.add_trace(go.Scatter(
                        x=[mv_v], y=[mv_r], mode="markers+text",
                        name="Min Volatility", text=["🛡️ Min Vol"], textposition="bottom right",
                        marker=dict(
                            size=18,
                            color="#00f3ff",
                            symbol="circle",
                            line=dict(width=2.5, color="#ffffff")
                        ),
                        textfont=dict(color="#00f3ff", size=13, family="Arial Black")
                    ))

                # Dynamic axis range calculation so ALL points fit perfectly
                all_vols = [frontier["vol_pct"].min(), frontier["vol_pct"].max(), cur_v, ms_v, mv_v]
                all_rets = [frontier["ret_pct"].min(), frontier["ret_pct"].max(), cur_r, ms_r, mv_r]
                all_vols = [v for v in all_vols if v > 0]
                all_rets = [r for r in all_rets]

                min_x = max(0, min(all_vols) - 2.0) if all_vols else 0
                max_x = max(all_vols) + 3.0 if all_vols else 30
                min_y = min(0, min(all_rets) - 2.0) if all_rets else 0
                max_y = max(all_rets) + 5.0 if all_rets else 40

                fig_f.update_xaxes(range=[min_x, max_x], gridcolor="rgba(255,255,255,0.06)")
                fig_f.update_yaxes(range=[min_y, max_y], gridcolor="rgba(255,255,255,0.06)")
                    
                fig_f.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
                )
                apply_plotly_theme(fig_f)
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
        st.markdown("#### 🧬 Hierarchical Risk Parity (HRP — Marcos López de Prado)")
        st.caption("Allocazione robusta basata su Machine Learning & Clustering Gerarchico ad Albero (Tree Clustering & Recursive Bisection) senza inversione di matrice.")

        glossary_modal("ℹ️ Guida all'Hierarchical Risk Parity (HRP)", """
        <p><b>1. Cos'è l'Hierarchical Risk Parity (HRP)?</b><br>
        Sviluppato da <b>Marcos López de Prado (2016)</b>, l'algoritmo HRP supera il limite principale della Frontiera di Markowitz: l'instabilità dell'inversione della matrice di covarianza ($\\Sigma^{-1}$). Quando due asset sono molto correlati, l'ottimizzazione classica amplifica il rumore statistico creando pesi estremi o irrealistici.</p>

        <p><b>2. Come funziona in 3 Fasi:</b><br>
        • <b>Tree Clustering:</b> Calcola la distanza di correlazione $D_{i,j} = \\sqrt{\\frac{1 - \\rho_{i,j}}{2}}$ e raggruppa gli asset in cluster gerarchici.<br>
        • <b>Quasi-Diagonalization:</b> Riordina la matrice di covarianza affinché gli asset più simili si trovino contigui sulla diagonale.<br>
        • <b>Recursive Bisection:</b> Distribuisce il capitale tra i sotto-rami in modo inversamente proporzionale alla loro varianza aggregata.</p>

        <p><b>3. Vantaggi Operativi:</b><br>
        Massima robustezza fuori campione (<i>Out-of-Sample</i>), assenza di vincoli rigidi e diversificazione naturale del rischio di portafoglio.</p>
        """, button_label="💡 Come funziona l'Hierarchical Risk Parity (HRP)?")

        df_returns_hrp = results.get("returns", pd.DataFrame())
        if df_returns_hrp.empty or df_returns_hrp.shape[1] < 2:
            df_pr = results.get("df_prices", pd.DataFrame())
            if not df_pr.empty and "ticker" in df_pr.columns and "close" in df_pr.columns:
                piv = df_pr.pivot(index="price_date", columns="ticker", values="close")
                df_returns_hrp = piv.pct_change().dropna(how="all")

        # Filtro per isolare solo i titoli del portafoglio ed escludere i tassi di cambio FX (es. DKKEUR=X)
        if not df_returns_hrp.empty and not pos.empty:
            port_tickers = [t for t in pos["ticker"].dropna().unique() if not str(t).endswith("=X")]
            valid_cols = [c for c in df_returns_hrp.columns if c in port_tickers]
            if len(valid_cols) >= 2:
                df_returns_hrp = df_returns_hrp[valid_cols]

        if not df_returns_hrp.empty and df_returns_hrp.shape[1] >= 2:
            hrp_res = compute_hrp_portfolio(df_returns_hrp)
            if hrp_res:
                col_hrp1, col_hrp2 = st.columns([1.5, 1])
                with col_hrp1:
                    df_hrp_w = hrp_res.get("df_weights", pd.DataFrame()).sort_values("hrp_weight_pct", ascending=False)
                    fig_hrp = px.bar(
                        df_hrp_w, x="ticker", y="hrp_weight_pct",
                        labels={"ticker": "Asset in Portafoglio", "hrp_weight_pct": "Allocazione Ottima HRP %"},
                        title="Allocazione Ottima Hierarchical Risk Parity (HRP)",
                        color="hrp_weight_pct", color_continuous_scale="Viridis",
                        template="plotly_dark", height=340
                    )
                    fig_hrp.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=10, r=10, t=40, b=10)
                    )
                    st.plotly_chart(fig_hrp, use_container_width=True)

                with col_hrp2:
                    st.markdown(f"""
                    * **Rendimento Atteso HRP**: <span style='color:#00e676; font-weight:bold;'>{hrp_res['expected_return_pct']:.2f}%</span>
                    * **Volatilità Annua HRP**: <span style='color:#ffab40; font-weight:bold;'>{hrp_res['volatility_annual_pct']:.2f}%</span>
                    * **Sharpe Ratio HRP**: <span style='color:#00f3ff; font-weight:bold;'>{hrp_res['sharpe_ratio']:.2f}</span>
                    * **Metodo di Linkage**: `scipy.cluster.hierarchy.single`
                    """, unsafe_allow_html=True)
                    
                    df_hrp_display = df_hrp_w.rename(columns={
                        "ticker": "Asset / Titolo",
                        "hrp_weight": "Peso Frazionario",
                        "hrp_weight_pct": "Allocazione Ottima HRP %"
                    })
                    st.dataframe(
                        df_hrp_display.style.format({
                            "Allocazione Ottima HRP %": "{:.2f}%",
                            "Peso Frazionario": "{:.4f}"
                        }),
                        use_container_width=True,
                        hide_index=True,
                        height=240
                    )
        else:
            st.info("Hierarchical Risk Parity richiede almeno 2 asset azionari/ETF validi con serie storiche nel portafoglio.")

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
                t_val = summary_orders.get('target_total_value_eur', summary_orders.get('target_total_value', 0.0))
                st.metric("Valore Portafoglio Target", f"€ {t_val:,.2f}")
            with col_om2:
                b_val = summary_orders.get('total_buy_eur', summary_orders.get('total_buy_value', 0.0))
                st.metric("Totale Acquisti (€)", f"€ {b_val:,.2f}")
            with col_om3:
                s_val = summary_orders.get('total_sell_eur', summary_orders.get('total_sell_value', 0.0))
                st.metric("Totale Vendite (€)", f"€ {s_val:,.2f}")

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
                    color_discrete_sequence=["#58a6ff", "#00e676", "#ff9900", "#bc8cff"],
                    template="plotly_dark", height=420
                )
                fig_bt.update_traces(
                    line=dict(width=2.2),
                    hovertemplate="<b>Data: %{x|%d %b %Y}</b><br>%{fullData.name}: %{y:.2f}<extra></extra>"
                )
                fig_bt.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.06)")
                )
                apply_plotly_theme(fig_bt)
                st.plotly_chart(fig_bt, use_container_width=True)

    else:
        st.info("Dati di ottimizzazione di Markowitz non disponibili.")

# ── TAB 2: MONTE CARLO & CLUSTERING K-MEANS ───────────────────
with tab2:
    st.markdown("### 🎲 Simulatore Stocastico Monte Carlo Multivariato & Clustering")
    st.caption("Proietta 3.000 traiettorie causali del portafoglio nel tempo tramite Decomposizione di Cholesky, con supporto per regimi di stress, distribuzioni a code grasse (Student-t) e metriche di Tail Risk (VaR & CVaR).")

    glossary_modal("📚 Guida alla Simulazione Monte Carlo Avanzata", """
    <p><b>1. Decomposizione di Cholesky ($L L^T = \\Sigma$):</b><br>
    Per preservare la complessa struttura di covarianza ed i legami storici di correlazione tra tutti gli asset del portafoglio, il simulatore scompone la matrice di covarianza $\\Sigma$ e genera shock ortogonali correlati.</p>

    <p><b>2. Distribuzione a Code Grasse (Student-t vs Gaussiana):</b><br>
    I rendimenti di mercato reali presentano curtosi elevata (eventi "Cigno Nero"). Selezionando la distribuzione <b>Student-t ($\nu=5$)</b>, il modello simula con accuratezza shock estremi di mercato spesso sottostimati dalla curva normale.</p>

    <p><b>3. Value at Risk (VaR) vs Expected Shortfall (CVaR):</b><br>
    - <b>VaR 95%:</b> La massima perdita stimata al 95° percentile di confidenza.<br>
    - <b>CVaR 95% (Expected Shortfall):</b> La <i>perdita media effettiva</i> che si verifica quando il mercato supera la soglia di VaR (ovvero nel peggiore 5% dei casi).</p>
    """, button_label="💡 Come funziona la Simulazione Monte Carlo?")

    try:
        from core.risk_engine import run_advanced_monte_carlo_simulation
    except ImportError:
        import importlib
        import core.risk_engine
        importlib.reload(core.risk_engine)
        from core.risk_engine import run_advanced_monte_carlo_simulation

    with st.expander("⚙️ Pannello di Controllo Scenario Monte Carlo & Regimi di Stress", expanded=True):
        mc_c1, mc_c2, mc_c3, mc_c4 = st.columns(4)
        with mc_c1:
            horizon_opt = st.selectbox(
                "Orizzonte Temporale Proiettato:",
                options=[63, 126, 252, 504, 756],
                index=2,
                format_func=lambda x: {63: "3 Mesi (63 gg)", 126: "6 Mesi (126 gg)", 252: "1 Anno (252 gg)", 504: "2 Anni (504 gg)", 756: "3 Anni (756 gg)"}[x]
            )
        with mc_c2:
            vol_mult = st.slider("Moltiplicatore Volatilità (Stress):", 0.50, 2.50, 1.00, 0.25, help="1.0x = Condizioni Normali; 1.5x - 2.0x = Regime di Alta Volatilità / Crisi")
        with mc_c3:
            drift_shift = st.slider("Aggiustamento Trend / Drift Anno (%):", -20.0, 20.0, 0.0, 1.0, help="Shift % sul rendimento atteso anno")
        with mc_c4:
            dist_type = st.radio("Distribuzione Shock:", ["Gaussiana (Normale)", "Student-t (Code Grasse)"], horizontal=True)
            dist_key = "student_t" if "Student-t" in dist_type else "gaussian"

    # Esecuzione della Simulazione Monte Carlo
    mc_adv = run_advanced_monte_carlo_simulation(
        results_dict=results,
        horizon_days=horizon_opt,
        volatility_multiplier=vol_mult,
        drift_shift_pct=drift_shift,
        distribution_type=dist_key,
        n_simulations=3000
    )

    if mc_adv:
        # Head KPI Cards
        mk1, mk2, mk3, mk4, mk5 = st.columns(5)
        with mk1:
            metric_card("Valore Iniziale", f"€ {mc_adv['initial_portfolio_value']:,.2f}", "Capitale Base", True)
        with mk2:
            metric_card("Mediana Attesa (1Y)", f"€ {mc_adv['expected_value_median']:,.2f}", f"Rendimento: {mc_adv['expected_return_median_pct']:+.2f}%", mc_adv['expected_return_median_pct'] >= 0)
        with mk3:
            metric_card("VaR 95% (Rischio)", f"€ {mc_adv['var_95_val_eur']:,.2f}", f"Perdita Max: -{mc_adv['var_95_pct']:.2f}%", False)
        with mk4:
            metric_card("CVaR 95% (Shortfall)", f"€ {mc_adv['cvar_95_val_eur']:,.2f}", f"Perdita Media Peggiori: -{mc_adv['cvar_95_pct']:.2f}%", False)
        with mk5:
            metric_card("Probabilità Profitto", f"{mc_adv['prob_profit_pct']:.1f}%", f"3.000 Simulazioni", mc_adv['prob_profit_pct'] >= 50.0)

        st.divider()

        # Grafico a Nastro (Ribbon & Path Generator Chart)
        st.markdown("#### 📈 Proiezione Stocastica delle Traiettorie nel Tempo (Fan / Ribbon Chart)")
        
        t_days = mc_adv["time_axis"]
        fig_fan = go.Figure()

        # 80 sample paths traslucidi per evidenziare il fascio esteso
        sample_paths = mc_adv["sample_paths"]
        for s_idx in range(sample_paths.shape[1]):
            fig_fan.add_trace(go.Scatter(
                x=t_days, y=sample_paths[:, s_idx],
                mode="lines",
                line=dict(color="rgba(72, 149, 239, 0.07)", width=1),
                showlegend=False,
                hoverinfo="skip"
            ))

        # Fasce a nastro (Ribbon Fills)
        fig_fan.add_trace(go.Scatter(
            x=t_days, y=mc_adv["p99_path"], mode="lines", name="P99 (Scenario Ultra-Ralzista)",
            line=dict(color="rgba(0, 255, 153, 0.6)", width=1.5, dash="dot")
        ))
        fig_fan.add_trace(go.Scatter(
            x=t_days, y=mc_adv["p75_path"], mode="lines", name="P75 (Scenario Positivo)",
            line=dict(color="rgba(0, 204, 255, 0.5)", width=1), fill="tonexty", fillcolor="rgba(0, 255, 153, 0.05)"
        ))
        fig_fan.add_trace(go.Scatter(
            x=t_days, y=mc_adv["p50_path"], mode="lines", name="P50 (Mediana Attesa)",
            line=dict(color="#00ff99", width=3)
        ))
        fig_fan.add_trace(go.Scatter(
            x=t_days, y=mc_adv["p25_path"], mode="lines", name="P25 (Scenario Conservativo)",
            line=dict(color="rgba(255, 204, 0, 0.5)", width=1), fill="tonexty", fillcolor="rgba(255, 204, 0, 0.05)"
        ))
        fig_fan.add_trace(go.Scatter(
            x=t_days, y=mc_adv["p05_path"], mode="lines", name="P05 (VaR 95%)",
            line=dict(color="#ff9900", width=2, dash="dash")
        ))
        fig_fan.add_trace(go.Scatter(
            x=t_days, y=mc_adv["p01_path"], mode="lines", name="P01 (Worst Case / VaR 99%)",
            line=dict(color="#ff3333", width=2.5, dash="dash")
        ))

        fig_fan.update_layout(
            title=f"Distribuzione Temporale dei Valori di Portafoglio — Orizzonte {horizon_opt} Giorni (Distribuzione {dist_type})",
            xaxis_title="Giorni di Contrattazione (Trading Days)",
            yaxis_title="Valore stimato di Portafoglio (€)",
            template="plotly_dark",
            height=460,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_fan, use_container_width=True)

        col_mc_dist, col_mc_odds = st.columns([1.6, 1])

        with col_mc_dist:
            st.markdown("#### 📊 Istogramma del Valore Finale & Soglie di Rischio (VaR / CVaR)")
            final_vals = mc_adv["final_values"]
            fig_hist_mc = go.Figure()
            
            fig_hist_mc.add_trace(go.Histogram(
                x=final_vals, nbinsx=45, name="Valore Finale",
                marker=dict(color="rgba(0, 243, 255, 0.5)", line=dict(color="#00f3ff", width=1))
            ))

            init_v = mc_adv["initial_portfolio_value"]
            med_v = mc_adv["expected_value_median"]
            var95_v = init_v - mc_adv["var_95_val_eur"]
            cvar95_v = init_v - mc_adv["cvar_95_val_eur"]

            fig_hist_mc.add_vline(
                x=cvar95_v, line_dash="dot", line_color="#ff3333", 
                annotation_text=f"CVaR 95% (€ {cvar95_v:,.0f})", 
                annotation_position="top left",
                annotation_font_color="#ff5252",
                annotation_font_size=11
            )
            fig_hist_mc.add_vline(
                x=var95_v, line_dash="dash", line_color="#ff9900", 
                annotation_text=f"VaR 95% (€ {var95_v:,.0f})", 
                annotation_position="bottom left",
                annotation_font_color="#ffab40",
                annotation_font_size=11
            )
            fig_hist_mc.add_vline(
                x=init_v, line_dash="dash", line_color="#ffffff", 
                annotation_text=f"Iniziale (€ {init_v:,.0f})", 
                annotation_position="top right",
                annotation_font_color="#ffffff",
                annotation_font_size=11
            )
            fig_hist_mc.add_vline(
                x=med_v, line_dash="solid", line_color="#00ff99", 
                annotation_text=f"Mediana (€ {med_v:,.0f})", 
                annotation_position="bottom right",
                annotation_font_color="#00e676",
                annotation_font_size=11
            )

            fig_hist_mc.update_layout(
                title="Distribuzione di Frequenza a Fine Orizzonte",
                xaxis_title="Valore Finale Portafoglio (€)",
                yaxis_title="Frequenza Simulazioni",
                template="plotly_dark", height=380,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_hist_mc, use_container_width=True)

        with col_mc_odds:
            st.markdown("#### 🎯 Matrice delle Probabilità & Risk Profile")
            df_odds = pd.DataFrame([
                {"Metrica / Scenario Stocastico": "🟢 Probabilità di Profitto (Rendimento > 0%)", "Valore Simulato": f"{mc_adv['prob_profit_pct']:.1f}%"},
                {"Metrica / Scenario Stocastico": "🚀 Probabilità di Target ≥ +10%", "Valore Simulato": f"{mc_adv['prob_gain_10_pct']:.1f}%"},
                {"Metrica / Scenario Stocastico": "🔥 Probabilità di Target ≥ +20%", "Valore Simulato": f"{mc_adv['prob_gain_20_pct']:.1f}%"},
                {"Metrica / Scenario Stocastico": "⚠️ Probabilità di Perdita ≤ -10%", "Valore Simulato": f"{mc_adv['prob_loss_10_pct']:.1f}%"},
                {"Metrica / Scenario Stocastico": "🔴 Probabilità di Perdita ≤ -20%", "Valore Simulato": f"{mc_adv['prob_loss_20_pct']:.1f}%"},
                {"Metrica / Scenario Stocastico": "📉 Max Drawdown Simulato Medio", "Valore Simulato": f"{mc_adv['avg_max_drawdown_pct']:.2f}%"},
                {"Metrica / Scenario Stocastico": "💥 Max Drawdown Simulato Worst 1%", "Valore Simulato": f"{mc_adv['p99_max_drawdown_pct']:.2f}%"}
            ])
            st.dataframe(df_odds, use_container_width=True, hide_index=True)

    else:
        st.info("Simulazione Monte Carlo non disponibile per gli asset selezionati.")

    st.divider()

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

    st.divider()
    st.markdown("#### ⚡ Simulatore Jump-Diffusion di Merton (Shock Stocastici & Tail Risk)")
    st.caption("Modellizzazione stocastica avanzata non-gaussiana che integra salti di Poisson (Crash Shock) per misurare perdite catastrofiche di coda (Fat Tails).")

    glossary_modal("⚡ Guida al Modello Merton Jump-Diffusion", """
    <p><b>1. Cos'è il Processo Jump-Diffusion di Merton?</b><br>
    I classici modelli di Black-Scholes ipotizzano una distribuzione normale continua dei rendimenti, sottostimando la frequenza dei crolli finanziari. Il modello di Merton aggiunge un <b>processo di salto Poissoniano ($N_t$)</b>:</p>
    $$dS_t = \\mu S_t dt + \\sigma S_t dW_t + (e^{Y_t} - 1) S_t dN_t$$

    <p><b>2. Parametri chiave:</b><br>
    • <b>$\\lambda$ (Frequenza Salto):</b> Il numero medio di shock catastrofici o crolli attesi in un anno (es. 1.5 salti/anno).<br>
    • <b>$\\mu_J$ (Dimensione Media Salto):</b> L'ampiezza media del crollo percentuale quando si verifica il salto (es. -8%).<br>
    • <b>$\\sigma_J$ (Volatilità del Salto):</b> La dispersione della dimensione dello shock.</p>

    <p><b>3. Perché confrontare VaR Gaussiano vs Merton Jump VaR?</b><br>
    Durante crisi di mercato, il VaR normale fallisce perché assume code sottili. Il VaR e CVaR di Merton catturano l'extra-rischio di coda (<i>Fat Tail Risk</i>).</p>
    """, button_label="💡 Come funziona il Modello Merton Jump-Diffusion?")

    with st.expander("⚙️ Configurazione Parametri Merton Jump Shocks", expanded=False):
        col_mj1, col_mj2, col_mj3 = st.columns(3)
        with col_mj1:
            lambda_in = st.slider("Frequenza Salto Poisson (salti/anno):", 0.1, 5.0, 1.5, 0.1, help="Numero medio di shock improvvisi attesi all'anno")
        with col_mj2:
            mu_j_in = st.slider("Dimensione Media Salto (%)", -30.0, 5.0, -8.0, 1.0, help="Shock medio in % (valori negativi = crolli)") / 100.0
        with col_mj3:
            sigma_j_in = st.slider("Volatilità Salto (%)", 1.0, 20.0, 5.0, 1.0) / 100.0

    from core.risk_engine import compute_merton_jump_diffusion_simulation
    sr_p_merton = results.get("portfolio_return", pd.Series(dtype=float))
    merton_res = compute_merton_jump_diffusion_simulation(
        sr_portfolio=sr_p_merton,
        n_sims=500,
        time_horizon_days=horizon_opt,
        lambda_j=lambda_in,
        mu_j=mu_j_in,
        sigma_j=sigma_j_in,
        initial_value=mc_adv['initial_portfolio_value'] if mc_adv else 100000.0
    )

    cmj1, cmj2, cmj3, cmj4 = st.columns(4)
    with cmj1:
        st.metric("VaR 99% Gaussiano Normale", f"{merton_res['var_99_gauss_pct']:.2f}%")
    with cmj2:
        st.metric("VaR 99% Merton Jump (Fat Tail)", f"{merton_res['var_99_jump_pct']:.2f}%", delta=f"{merton_res['var_99_jump_pct'] - merton_res['var_99_gauss_pct']:+.2f}%", delta_color="inverse")
    with cmj3:
        st.metric("CVaR 99% Merton Jump (Shortfall)", f"{merton_res['cvar_99_jump_pct']:.2f}%", delta_color="inverse")
    with cmj4:
        st.metric("Media Salti Poisson / Anno", f"{merton_res['mean_jumps_per_year']:.1f}")

    m_days = merton_res["days"]
    fig_merton = go.Figure()
    fig_merton.add_trace(go.Scatter(x=m_days, y=merton_res["p95"], mode="lines", name="P95 Scenario Rialzista", line=dict(color="rgba(0,255,153,0.5)", width=1)))
    fig_merton.add_trace(go.Scatter(x=m_days, y=merton_res["p75"], mode="lines", name="P75 Scenario Positivo", line=dict(color="rgba(0,204,255,0.4)", width=1), fill="tonexty", fillcolor="rgba(0,255,153,0.05)"))
    fig_merton.add_trace(go.Scatter(x=m_days, y=merton_res["p50"], mode="lines", name="P50 Mediana Jump-Diffusion", line=dict(color="#00f3ff", width=2.5)))
    fig_merton.add_trace(go.Scatter(x=m_days, y=merton_res["p25"], mode="lines", name="P25 Scenario Conservativo", line=dict(color="rgba(255,204,0,0.4)", width=1), fill="tonexty", fillcolor="rgba(255,204,0,0.05)"))
    fig_merton.add_trace(go.Scatter(x=m_days, y=merton_res["p5"], mode="lines", name="P05 Tail Crash Zone", line=dict(color="#ff3333", width=2, dash="dash")))

    fig_merton.update_layout(
        title=f"Traiettorie Stocastiche Merton Jump-Diffusion (λ={lambda_in}/anno, μ_J={mu_j_in*100:.1f}%)",
        xaxis_title="Giorni di Contrattazione", yaxis_title="Valore Portafoglio (€)",
        template="plotly_dark", height=400,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_merton, use_container_width=True)

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

    st.divider()
    st.markdown("#### 🛡️ Modello Black-Scholes (1973): Opzioni Put Hedging & Covered Call Yield")
    st.caption("Calcolo analitico dei 5 Greci ($\\Delta, \\Gamma, \\Theta, \\text{Vega}, \\rho$), copertura Delta-Hedge con opzioni Put e generazione di rendimento passivo con Covered Call.")

    glossary_modal("ℹ️ Guida al Modello Black-Scholes, Greci & Covered Call", """
    <p><b>1. Modello di Black-Scholes-Merton (1973):</b><br>
    Formula analitica fondamentale per determinare il prezzo equo (Fair Value) di opzioni Europee Call e Put in base a Prezzo Spot ($S$), Strike ($K$), Scadenza ($T$), Tasso Risk-Free ($r$) e Volatilità Implicita ($\\sigma$).</p>

    <p><b>2. I 5 Greci Analitici:</b><br>
    • <b>Delta ($\\Delta$):</b> Variazione del prezzo dell'opzione per variazione di $1$ del sottostante (usato per calcolare la copertura esatta).<br>
    • <b>Gamma ($\\Gamma$):</b> Accelerazione del Delta rispetto al sottostante.<br>
    • <b>Theta ($\\Theta$):</b> Decadimento temporale giornaliero del valore dell'opzione (<i>Time Decay</i>).<br>
    • <b>Vega:</b> Sensibilità del prezzo dell'opzione ad un aumento dell'1% della volatilità implicita.<br>
    • <b>Rho ($\\rho$):</b> Sensibilità alle variazioni dei tassi d'interesse ufficiali.</p>

    <p><b>3. Delta-Hedging con Put vs Covered Call:</b><br>
    • <b>Put Delta-Hedge:</b> Acquisto di contratti Put sul benchmark per azzerare o ridurre il Beta e proteggere il capitale dai crolli.<br>
    • <b>Covered Call Writing:</b> Vendita sistematica di opzioni Call Out-of-the-Money (+5%) sulle azioni possedute per incassare premi periodici e generare un rendimento passivo extra (<i>Yield Enhancement</i>).</p>
    """, button_label="💡 Come funziona Black-Scholes, Greci & Covered Call?")

    col_opt_in1, col_opt_in2, col_opt_in3 = st.columns(3)
    with col_opt_in1:
        bm_spot_in = st.number_input("Prezzo Sottostante Benchmark (SPY/SPX $):", value=550.0, step=10.0)
    with col_opt_in2:
        iv_in = st.slider("Volatilità Implicita Opzioni (%):", 10.0, 60.0, 18.0, 1.0) / 100.0
    with col_opt_in3:
        target_hedge_pct = st.slider("Copertura del Portafoglio (%):", 25.0, 100.0, 100.0, 25.0)

    port_val_tot = float(pos["current_value"].sum()) if not pos.empty else 100000.0
    port_b = float(results.get("metrics", {}).get("market_risk", {}).get("beta", 1.10) or 1.10)

    bs_hedge = compute_portfolio_delta_hedge(
        portfolio_value=port_val_tot,
        portfolio_beta=port_b,
        benchmark_spot=bm_spot_in,
        target_hedge_pct=target_hedge_pct,
        implied_vol=iv_in
    )

    col_bs1, col_bs2, col_bs3, col_bs4 = st.columns(4)
    with col_bs1:
        st.metric("Contratti Put Necessari", f"{bs_hedge['contracts_needed']} contratti")
    with col_bs2:
        st.metric("Prezzo Opzione Put", f"$ {bs_hedge['put_price']:.2f}")
    with col_bs3:
        st.metric("Costo Totale Copertura", f"$ {bs_hedge['total_hedge_cost']:,.2f}", delta=f"{bs_hedge['cost_pct_of_portfolio']:.2f}% portafoglio", delta_color="inverse")
    with col_bs4:
        st.metric("Delta Put (Sensibilità)", f"{bs_hedge['put_delta']:.3f}", help="Variazione del prezzo dell'opzione per variazione di $1 del sottostante")

    st.markdown("##### 💵 Covered Call Yield Enhancer per Titoli in Portafoglio")
    df_cov_call = compute_covered_call_yield_enhancement(pos, otm_pct=5.0, implied_vol=iv_in)
    if not df_cov_call.empty:
        df_cov_display = df_cov_call.rename(columns={
            "ticker": "Asset / Titolo",
            "prezzo_spot": "Prezzo Spot (€)",
            "strike_call_otm": "Strike OTM (+5%)",
            "premio_per_azione": "Premio per Azione (€)",
            "incasso_premio_totale": "Incasso Totale Premio (€)",
            "extra_rendimento_mensile_pct": "Extra Yield Mensile %",
            "extra_rendimento_annuo_pct": "Extra Yield Annuo %",
            "delta_call": "Delta Call (Δ)"
        })
        st.dataframe(
            df_cov_display.style.format({
                "Prezzo Spot (€)": "€ {:.2f}",
                "Strike OTM (+5%)": "€ {:.2f}",
                "Premio per Azione (€)": "€ {:.2f}",
                "Incasso Totale Premio (€)": "€ {:,.2f}",
                "Extra Yield Mensile %": "{:.2f}%",
                "Extra Yield Annuo %": "{:.2f}%",
                "Delta Call (Δ)": "{:.3f}"
            }),
            use_container_width=True,
            hide_index=True,
            height=240
        )

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
    if not attr_df.empty:
        st.markdown("**Scomposizione per Settore (Allocation vs Selection vs Interaction)**")
        fig_attr = px.bar(
            attr_df, x="sector", y=["allocation_effect_pct", "selection_effect_pct", "interaction_effect_pct"],
            barmode="group", title="Scomposizione Effetti per Settore GICS (%)",
            color_discrete_sequence=["#58a6ff", "#3fb950", "#bc8cff"],
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
        apply_plotly_theme(fig_attr)
        st.plotly_chart(fig_attr, use_container_width=True)

# ── TAB 5: BLACK-LITTERMAN & CARHART 4-FACTOR ────────────────
with tab5:
    st.markdown("#### Modello Black-Litterman & Regressione Fattoriale Carhart (4 Fattori)")
    st.caption("Combina le stime di equilibrio di mercato con le opinioni dell'investitore (Views) ed analizza l'esposizione ai 4 fattori di rischio (Market, Size SMB, Value HML, Momentum WML).")

    from core.risk_engine import compute_black_litterman_optimization, compute_carhart_4factor_exposures

    col_bl_ff1, col_bl_ff2 = st.columns([1, 1])

    with col_bl_ff1:
        st.markdown("##### 🏛️ Ottimizzazione Black-Litterman")
        cov_df = None
        if opt and "cov_matrix" in opt and isinstance(opt["cov_matrix"], pd.DataFrame) and not opt["cov_matrix"].empty:
            cov_df = opt["cov_matrix"]
        else:
            df_returns_all = results.get("returns", pd.DataFrame())
            if isinstance(df_returns_all, pd.DataFrame) and not df_returns_all.empty:
                active_tickers = []
                if isinstance(pos, pd.DataFrame) and not pos.empty and "qty_net" in pos.columns and "ticker" in pos.columns:
                    active_tickers = pos[pos["qty_net"] > 0]["ticker"].tolist()
                common = [t for t in active_tickers if t in df_returns_all.columns]
                if len(common) >= 1:
                    cov_df = df_returns_all[common].cov() * 252

        if cov_df is not None and not cov_df.empty:
            mkt_w = None
            if isinstance(pos, pd.DataFrame) and not pos.empty and "weight_pct" in pos.columns and "ticker" in pos.columns:
                mkt_w = pos.set_index("ticker")["weight_pct"] / 100.0
            else:
                mkt_w = pd.Series(1.0 / len(cov_df), index=cov_df.index)
            
            bl_res = compute_black_litterman_optimization(cov_df, mkt_w)
            if bl_res:
                df_bl = pd.DataFrame({
                    "Equilibrium Return %": bl_res["implied_equilibrium_returns"] * 100,
                    "BL Return %": bl_res["black_litterman_returns"] * 100,
                    "BL Weight %": bl_res["black_litterman_weights"] * 100
                })
                st.dataframe(df_bl.style.format("{:.2f}%"), use_container_width=True)
            else:
                st.info("Dati di covarianza insufficienti per Black-Litterman.")
        else:
            st.info("Matrice di covarianza non disponibile. Assicurati di aver calcolato i rendimenti per le posizioni attive.")

    with col_bl_ff2:
        st.markdown("##### 🧠 Analisi Fattoriale Carhart (4 Fattori)")
        render_formula_popover(
            "🧠 Formula & Teoria Carhart 4-Factor",
            "Modello di Carhart a 4 Fattori (1997)",
            r"R_{i,t} - R_{f,t} = \alpha + \beta_1 (R_{m,t} - R_{f,t}) + \beta_2 \text{SMB}_t + \beta_3 \text{HML}_t + \beta_4 \text{WML}_t + \epsilon_t",
            "<b>Significato dei Fattori:</b><br>"
            "• <b>Mkt-RF:</b> Rischio sistemico di mercato generale.<br>"
            "• <b>SMB (Small Minus Big):</b> Inclinazione verso titoli Small Cap.<br>"
            "• <b>HML (High Minus Low):</b> Inclinazione verso titoli Value.<br>"
            "• <b>WML (Winners Minus Losers):</b> Esposizione al fattore Momentum."
        )

        sr_p = results.get("portfolio_return", pd.Series(dtype=float))
        c4_res = compute_carhart_4factor_exposures(sr_p)

        st.metric("Alpha Annua Puro (α)", f"{c4_res['alpha']*100:+.2f}%")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.metric("Beta Mercato (Mkt)", f"{c4_res['beta_mkt']:.2f}")
            st.metric("Beta Value (HML)", f"{c4_res['beta_hml']:+.2f}")
        with col_f2:
            st.metric("Beta Size (SMB)", f"{c4_res['beta_smb']:+.2f}")
            st.metric("Beta Momentum (WML)", f"{c4_res['beta_wml']:+.2f}")
        
        st.caption(f"Bontà di Adattamento del Modello (R²): **{c4_res['r_squared']*100:.1f}%**")

    st.divider()
    st.markdown("#### 🏛️ Modello Macro-Fattoriale MSCI Barra (5 Fattori Ortogonalizzati)")
    st.caption("Decomposizione avanzata ed ortogonale delle esposizioni fattoriali del portafoglio (Market, Size SMB, Value HML, Momentum WML, Term Premium).")

    glossary_modal("ℹ️ Guida al Modello Fattoriale MSCI Barra & Forecast ML", """
    <p><b>1. Cos'è il Modello Macro-Fattoriale MSCI Barra?</b><br>
    È un modello econometrico multi-variato che scompone il rischio del portafoglio in 5 fattori di stile e macroeconomici tra loro ortogonalizzati per evitare la multicollinearità:</p>
    <ul>
        <li><b>MKT (Mercato):</b> Esposizione al rischio sistemico del mercato azionario generale.</li>
        <li><b>SMB (Small Minus Big):</b> Inclinazione verso titoli a bassa capitalizzazione (Small Caps).</li>
        <li><b>HML (High Minus Low):</b> Inclinazione verso titoli Value (alto Book-to-Market).</li>
        <li><b>WML (Winners Minus Losers):</b> Esposizione al fattore Inerzia / Momentum.</li>
        <li><b>TERM (Term Premium):</b> Sensibilità alle variazioni della pendenza della curva dei tassi di interesse.</li>
    </ul>

    <p><b>2. Come interpretare la Decomposizione della Varianza?</b><br>
    • <b>Rischio Sistemico (Fattori):</b> La percentuale di volatilità spiegata dai 5 fattori macro.<br>
    • <b>Rischio Specifico (Residuo):</b> La volatilità idiosincratica specifica dei singoli titoli.<br>
    • <b>Alpha (α):</b> Il rendimento extra puro generato oltre la spiegazione dei fattori di rischio.</p>

    <p><b>3. Cos'è il Forecast di Volatilità Machine Learning?</b><br>
    Un modello predittivo <b>Random Forest Regressor</b> che stima la volatilità annualizzata attesa nei prossimi 30 giorni basandosi sulle feature di volatilità rolling storiche (5g, 10g, 22g), Skewness e Kurtosis.</p>
    """, button_label="💡 Come funziona il Modello MSCI Barra & Forecast ML?")

    from core.risk_engine import compute_msci_barra_multifactor_model
    barra_res = compute_msci_barra_multifactor_model(sr_p)

    betas_dict = barra_res.get("factor_betas", {})
    t_dict = barra_res.get("t_stats", {})

    factor_names_map = {
        "MKT": "Mercato (Equity Systematic)",
        "SMB": "Dimensione (Small Caps)",
        "HML": "Valore (High Book-to-Market)",
        "WML": "Inerzia (12M Momentum)",
        "TERM": "Macro Curva Tassi (Term Premium)"
    }

    df_barra = pd.DataFrame({
        "Fattore": list(betas_dict.keys()),
        "Nome Esteso": [factor_names_map.get(k, k) for k in betas_dict.keys()],
        "Beta Fattoriale": [betas_dict[k] for k in betas_dict.keys()],
        "Statistica t": [t_dict.get(k, 0.0) for k in betas_dict.keys()],
        "Significatività (95%)": ["🟢 Significativo" if abs(t_dict.get(k, 0.0)) >= 1.96 else "⚪ In Linea" for k in betas_dict.keys()]
    })

    col_bar1, col_bar2 = st.columns([1.5, 1])

    with col_bar1:
        colors = ["#3fb950" if b >= 0 else "#f85149" for b in df_barra["Beta Fattoriale"]]

        fig_barra = go.Figure(go.Bar(
            x=df_barra["Fattore"],
            y=df_barra["Beta Fattoriale"],
            marker_color=colors,
            text=df_barra["Beta Fattoriale"].apply(lambda b: f"{b:+.2f}"),
            textposition="outside",
            textfont=dict(size=12, color="white")
        ))

        fig_barra.update_layout(
            template="plotly_dark",
            height=350,
            margin=dict(l=10, r=10, t=20, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="Esposizione (Beta)", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            xaxis=dict(title="Fattori Stile & Macro")
        )
        apply_plotly_theme(fig_barra)
        st.plotly_chart(fig_barra, use_container_width=True)

    with col_bar2:
        st.markdown("##### 🍩 Decomposizione Varianza Rischio")
        sys_pct = barra_res.get("systematic_risk_pct", 88.0)
        spec_pct = barra_res.get("specific_risk_pct", 12.0)

        fig_pie = go.Figure(data=[go.Pie(
            labels=["Rischio Sistemico (Fattori)", "Rischio Specifico (Residuo)"],
            values=[sys_pct, spec_pct],
            hole=0.6,
            marker=dict(colors=["#58a6ff", "#bc8cff"], line=dict(color="#0d1117", width=2))
        )])
        fig_pie.update_layout(
            template="plotly_dark",
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            legend=dict(orientation="h", y=-0.1)
        )
        apply_plotly_theme(fig_pie)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.metric("Alpha Multi-Fattoriale (α)", f"{barra_res.get('alpha_annualized', 0.0)*100:+.2f}%", help="Rendimento extra puro generato oltre la spiegazione dei 5 fattori macro")

    st.markdown("##### 📋 Tabella di Dettaglio dei Fattori MSCI Barra")
    st.dataframe(
        df_barra.style.format({
            "Beta Fattoriale": "{:+.3f}",
            "Statistica t": "{:+.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    st.markdown("##### 🤖 Forecast Volatilità a 30 Giorni (Machine Learning Ensemble)")
    from core.financial_analysis import predict_ml_distress_and_volatility
    df_p_ml = st.session_state.get("df_prices")
    ml_res = predict_ml_distress_and_volatility(df_prices=df_p_ml)

    st.metric("Volatilità Predetta 30 Giorni Futuri", f"{ml_res['predicted_volatility_30d_pct']:.2f}%", help="Stima della volatilità annualizzata a 30 giorni basata su Random Forest Regressor")
    st.caption(f"Verdetto ML: **{ml_res['verdict']}**")

