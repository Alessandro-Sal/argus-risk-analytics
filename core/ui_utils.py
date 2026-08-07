import streamlit as st
import pandas as pd
import numpy as np

def inject_custom_css():
    theme = st.session_state.get("ui_theme", "Midnight Obsidian")
    
    if theme == "Cyberpunk Neon":
        bg_gradient = "radial-gradient(circle at 15% 50%, #050811, #0a1124, #050811)"
        accent_color = "#00f3ff"
        accent_gradient = "linear-gradient(180deg, #00f3ff, #00ff66)"
        card_bg = "rgba(10, 17, 36, 0.7)"
    elif theme == "Emerald Wealth":
        bg_gradient = "radial-gradient(circle at 15% 50%, #06140e, #0d281c, #06140e)"
        accent_color = "#00c853"
        accent_gradient = "linear-gradient(180deg, #00c853, #ffd700)"
        card_bg = "rgba(13, 40, 28, 0.7)"
    else: # Midnight Obsidian
        bg_gradient = "radial-gradient(circle at 15% 50%, #0d1117, #161b22, #0d1117)"
        accent_color = "#ff9900"
        accent_gradient = "linear-gradient(180deg, #ff9900, #ff3366)"
        card_bg = "rgba(22, 27, 34, 0.6)"

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Outfit', sans-serif !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: {bg_gradient};
            background-size: cover;
            background-attachment: fixed;
            color: #e6edf3;
        }}
        [data-testid="stSidebar"] {{
            background: rgba(13, 17, 23, 0.7) !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }}

        /* Metric Cards */
        .metric-card {{
            background: {card_bg};
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 20px 24px;
            margin-bottom: 16px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.05);
            position: relative;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        }}
        
        .metric-card::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: {accent_gradient};
            box-shadow: 0 0 10px {accent_color};
            opacity: 0.8;
        }}

        .metric-card:hover {{
            transform: translateY(-4px) scale(1.01);
            border-color: {accent_color};
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3), 0 0 20px rgba(0, 243, 255, 0.15);
        }}

        .metric-label {{ 
            color: #8b949e; 
            font-size: 13px; 
            font-weight: 500; 
            letter-spacing: 0.8px; 
            text-transform: uppercase;
        }}
        
        .metric-value {{ 
            background: linear-gradient(90deg, #ffffff, #c9d1d9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 32px; 
            font-weight: 700; 
            margin-top: 8px;
            font-family: 'Outfit', sans-serif;
            letter-spacing: -0.5px;
        }}

        /* Executive Health Badges */
        .executive-badge {{
            display: inline-flex;
            align-items: center;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            margin-right: 10px;
            margin-bottom: 12px;
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .badge-green {{ background: rgba(63, 185, 80, 0.15); color: #3fb950; border-color: rgba(63, 185, 80, 0.3); }}
        .badge-yellow {{ background: rgba(210, 153, 34, 0.15); color: #d29922; border-color: rgba(210, 153, 34, 0.3); }}
        .badge-red {{ background: rgba(248, 81, 73, 0.15); color: #f85149; border-color: rgba(248, 81, 73, 0.3); }}

        /* Section Header */
        .section-header {{
            font-size: 22px; 
            font-weight: 600; 
            color: #ffffff;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 12px; 
            margin: 36px 0 20px 0;
            position: relative;
        }}
        .section-header::after {{
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 60px;
            height: 2px;
            background: {accent_color};
            box-shadow: 0 0 10px {accent_color};
        }}

        /* Glowing Status Pulse Dot */
        @keyframes pulse-green {{
            0% {{ box-shadow: 0 0 0 0 rgba(63, 185, 80, 0.7); }}
            70% {{ box-shadow: 0 0 0 8px rgba(63, 185, 80, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(63, 185, 80, 0); }}
        }}
        .status-dot-pulse {{
            width: 8px;
            height: 8px;
            background-color: #3fb950;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            animation: pulse-green 2s infinite;
        }}

        /* ARGUS Glassmorphic Top Command Bar */
        .argus-command-bar {{
            background: rgba(22, 27, 34, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 10px 18px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}
        .argus-command-pill {{
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #c9d1d9;
            margin-left: 8px;
        }}

        /* Streamlit Tabs Customization */
        [data-baseweb="tab-list"] {{
            gap: 6px;
            background: rgba(13, 17, 23, 0.5);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }}
        [data-baseweb="tab"] {{
            border-radius: 8px !important;
            font-weight: 500 !important;
            color: #8b949e !important;
            padding: 8px 16px !important;
            transition: all 0.2s ease !important;
        }}
        [data-baseweb="tab"][aria-selected="true"] {{
            background: rgba(255, 153, 0, 0.15) !important;
            color: #ffffff !important;
            border: 1px solid {accent_color} !important;
            box-shadow: 0 0 10px rgba(255, 153, 0, 0.2) !important;
        }}

        /* Streamlit Buttons Micro-Animations */
        .stButton > button {{
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4), 0 0 12px {accent_color}33 !important;
        }}

        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header, [data-testid="stHeader"] {{ visibility: visible !important; display: block !important; }}
        [data-testid="collapsedControl"] {{ visibility: visible !important; display: block !important; z-index: 999999 !important; }}
    </style>
    """, unsafe_allow_html=True)


def render_command_bar():
    """Renderizza la barra di stato e comando ARGUS in cima alla pagina."""
    port_name = st.session_state.get("portfolio_name", "My Portfolio")
    base_curr = st.session_state.get("base_currency", "EUR")
    bench = st.session_state.get("benchmark", "SPY")
    run_id = st.session_state.get("run_id", "ACTIVE")
    offline = st.session_state.get("offline_mode", False)
    mode_str = "OFFLINE" if offline else "LIVE DB"

    st.markdown(f"""
    <div class="argus-command-bar">
        <div style="display:flex; align-items:center; font-size: 13px; font-weight: 500;">
            <span class="status-dot-pulse"></span>
            <span style="color:#ffffff; font-weight:600; margin-right: 6px;">ARGUS ENGINE</span>
            <span style="color:#8b949e;">| {port_name}</span>
        </div>
        <div style="display:flex; align-items:center;">
            <span class="argus-command-pill">💱 {base_curr}</span>
            <span class="argus-command-pill">📊 {bench}</span>
            <span class="argus-command-pill">⚡ {mode_str}</span>
            <span class="argus-command-pill" style="border-color: rgba(255, 153, 0, 0.4); color: #ff9900;">ID: {run_id}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_workflow_stepper(current_step: int = 1):
    """Renderizza uno stepper grafico a 3 fasi per l'ingestione dati."""
    s1_style = "border-color: #ff9900; background: rgba(255, 153, 0, 0.15); color: #ffffff;" if current_step >= 1 else "color: #8b949e;"
    s2_style = "border-color: #ff9900; background: rgba(255, 153, 0, 0.15); color: #ffffff;" if current_step >= 2 else "color: #8b949e;"
    s3_style = "border-color: #ff9900; background: rgba(255, 153, 0, 0.15); color: #ffffff;" if current_step >= 3 else "color: #8b949e;"

    s1_icon = "✅" if current_step > 1 else "1️⃣"
    s2_icon = "✅" if current_step > 2 else "2️⃣"
    s3_icon = "🚀" if current_step == 3 else "3️⃣"

    st.markdown(f"""
    <div style="display:flex; align-items:center; justify-content:space-between; margin: 15px 0 25px 0; background: rgba(22, 27, 34, 0.6); padding: 12px 18px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(12px);">
        <div style="display:flex; align-items:center; flex:1; padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); {s1_style}">
            <span style="font-size: 15px; margin-right: 8px;">{s1_icon}</span>
            <span style="font-weight: 600; font-size: 13px;">1. Carica File CSV</span>
        </div>
        <div style="width: 30px; text-align: center; color: rgba(255,255,255,0.2); font-weight:bold;">➔</div>
        <div style="display:flex; align-items:center; flex:1; padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); {s2_style}">
            <span style="font-size: 15px; margin-right: 8px;">{s2_icon}</span>
            <span style="font-weight: 600; font-size: 13px;">2. Validazione Dati</span>
        </div>
        <div style="width: 30px; text-align: center; color: rgba(255,255,255,0.2); font-weight:bold;">➔</div>
        <div style="display:flex; align-items:center; flex:1; padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); {s3_style}">
            <span style="font-size: 15px; margin-right: 8px;">{s3_icon}</span>
            <span style="font-weight: 600; font-size: 13px;">3. Calcolo & Motore Rischio</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_validation_report(report: dict):
    """Renderizza in modo pulito ed elegante i report di validazione (errors, warnings, fixes)."""
    errors = report.get("errors", [])
    warnings = report.get("warnings", [])
    fixes = report.get("fixes", [])

    if errors:
        st.markdown('<div class="section-header" style="color: #f85149; border-color: rgba(248, 81, 73, 0.4);">🔴 Errori di Validazione Bloccanti</div>', unsafe_allow_html=True)
        for e in errors:
            st.markdown(f'''
            <div style="background: rgba(248, 81, 73, 0.12); border-left: 4px solid #f85149; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; color: #ff7b72;">
                <strong>🔴 Blocco Ingestione:</strong> {e}
            </div>
            ''', unsafe_allow_html=True)
        st.stop()

    if fixes or warnings:
        tot_items = len(fixes) + len(warnings)
        fixes_badge = f'<span class="executive-badge badge-green">🟢 {len(fixes)} Correzioni Automatiche</span>' if fixes else ''
        warn_badge = f'<span class="executive-badge badge-yellow">🟡 {len(warnings)} Avvisi di Controllo</span>' if warnings else ''

        with st.expander(f"🛠️ Dettaglio Audit Data Quality ({tot_items} note di validazione)", expanded=bool(warnings)):
            st.markdown(f'<div style="margin-bottom: 12px;">{fixes_badge}{warn_badge}</div>', unsafe_allow_html=True)
            
            if fixes:
                st.markdown("**🟢 Correzioni ed Aggiustamenti Automatici Applicati:**")
                for f in fixes:
                    st.markdown(f'<div style="background: rgba(63, 185, 80, 0.08); border-left: 3px solid #3fb950; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; font-size: 13px; color: #e6edf3;">✓ {f}</div>', unsafe_allow_html=True)

            if warnings:
                st.markdown("**🟡 Avvisi sulle Transazioni (Verifica consigliata):**")
                for w in warnings:
                    st.markdown(f'<div style="background: rgba(210, 153, 34, 0.08); border-left: 3px solid #d29922; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; font-size: 13px; color: #e6edf3;">⚠️ {w}</div>', unsafe_allow_html=True)


def render_executive_badges(metrics_dict: dict):
    """Renderizza i badge esecutivi di salute e profilo del portafoglio."""
    ret = metrics_dict.get("returns", {})
    mk = metrics_dict.get("market_risk", {})
    
    sharpe = ret.get("sharpe_ratio", 0.0) or 0.0
    vol = mk.get("volatility_annual_pct", 0.0) or 0.0
    max_dd = abs(mk.get("max_drawdown_pct", 0.0) or 0.0)
    
    # Sharpe Badge
    if sharpe >= 1.2:
        sharpe_badge = '<span class="executive-badge badge-green">🟢 Sharpe Eccellente (> 1.2)</span>'
    elif sharpe >= 0.7:
        sharpe_badge = '<span class="executive-badge badge-yellow">🟡 Sharpe Moderato (0.7 - 1.2)</span>'
    else:
        sharpe_badge = '<span class="executive-badge badge-red">🔴 Sharpe Contenuto (< 0.7)</span>'

    # Volatility Badge
    if vol <= 15.0:
        vol_badge = '<span class="executive-badge badge-green">🟢 Profilo Conservativo (Vol < 15%)</span>'
    elif vol <= 25.0:
        vol_badge = '<span class="executive-badge badge-yellow">🟡 Profilo Bilanciato (Vol 15-25%)</span>'
    else:
        vol_badge = '<span class="executive-badge badge-red">🔴 Profilo Aggressivo (Vol > 25%)</span>'

    # Drawdown Badge
    if max_dd <= 12.0:
        dd_badge = '<span class="executive-badge badge-green">🟢 Drawdown Contenuto (< 12%)</span>'
    elif max_dd <= 22.0:
        dd_badge = '<span class="executive-badge badge-yellow">🟡 Drawdown Moderato (12-22%)</span>'
    else:
        dd_badge = '<span class="executive-badge badge-red">🔴 Drawdown Elevato (> 22%)</span>'

    st.markdown(f'<div style="margin-bottom: 16px;">{sharpe_badge}{vol_badge}{dd_badge}</div>', unsafe_allow_html=True)


def apply_plotly_theme(fig, theme_name=None):
    """Applica uno stile dark vettoriale con tooltip luminosi al grafico Plotly."""
    if not theme_name:
        theme_name = st.session_state.get("ui_theme", "Midnight Obsidian")

    accent = "#ff9900" if theme_name == "Midnight Obsidian" else ("#00f3ff" if theme_name == "Cyberpunk Neon" else "#00c853")

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color="#e6edf3"),
        hoverlabel=dict(
            bgcolor="#161b22",
            font_size=13,
            font_family="Outfit, sans-serif",
            bordercolor=accent
        ),
        margin=dict(l=20, r=20, t=30, b=30),
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(255,255,255,0.05)")
    return fig


def render_factor_radar_chart(results: dict):
    """Genera un grafico Radar / Spider a 360° dell'impronta di rischio del portafoglio confrontato con il Benchmark di Riferimento."""
    import plotly.graph_objects as go
    m = results.get("metrics", {})
    mk = m.get("market_risk", {})
    con = m.get("concentration", {})
    
    categories = [
        "Market Beta",
        "Size SMB",
        "Value HML",
        "Volatilità",
        "Diversificazione DR",
        "Asimmetria Skew"
    ]
    
    beta = min(100.0, max(0.0, (mk.get("beta", 1.0) or 1.0) * 50))
    smb = min(100.0, max(0.0, (mk.get("smb_tilt", 0.0) or 0.0) * 50 + 50))
    hml = min(100.0, max(0.0, (mk.get("hml_tilt", 0.0) or 0.0) * 50 + 50))
    vol = min(100.0, max(0.0, (mk.get("volatility_annual_pct", 15.0) or 15.0) * 2))
    dr = min(100.0, max(0.0, ((con.get("diversification_ratio", 1.2) or 1.2) - 1.0) * 100))
    skew = min(100.0, max(0.0, (mk.get("skewness", 0.0) or 0.0) * 25 + 50))
    
    values = [beta, smb, hml, vol, dr, skew]
    values.append(values[0])
    cats = list(categories) + [categories[0]]
    
    # Baseline neutra/benchmark (50/100 su ogni fattore)
    baseline_values = [50, 50, 50, 50, 50, 50, 50]

    fig = go.Figure()
    
    # Trace 1: Target Neutral Baseline
    fig.add_trace(go.Scatterpolar(
        r=baseline_values,
        theta=cats,
        fill='toself',
        fillcolor='rgba(143, 160, 186, 0.08)',
        line=dict(color='#8fa0ba', width=1.5, dash='dash'),
        name='Benchmark Neutro (50/100)',
        hovertemplate="<b>Benchmark Neutro</b><br>Fattore: %{theta}<br>Score Target: 50.0/100<extra></extra>"
    ))
    
    # Trace 2: Portafoglio Actuel
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=cats,
        mode='lines+markers',
        fill='toself',
        fillcolor='rgba(255, 153, 0, 0.25)',
        line=dict(color='#ff9900', width=2.5),
        marker=dict(size=6, color='#ff9900'),
        name='Impronta Portafoglio',
        hovertemplate="<b>%{theta}</b><br>Score Portafoglio: %{r:.1f} / 100<extra></extra>"
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(size=12, color="#c9d1d9")),
            bgcolor="rgba(0,0,0,0)"
        ),
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5),
        height=370,
        margin=dict(l=35, r=35, t=20, b=30)
    )
    return apply_plotly_theme(fig)


def render_risk_heatmap(positions_df, risk_contrib=None):
    """Genera una Treemap / Risk Heatmap ad alta densità per asset class e singola posizione."""
    import plotly.express as px
    if positions_df is None or positions_df.empty:
        return None
    
    df = positions_df[positions_df["current_value"] > 0].copy()
    if df.empty:
        return None
        
    df["label"] = df["ticker"]
    df["asset_class"] = df["asset_class"].fillna("Altro")
    
    fig = px.treemap(
        df,
        path=[px.Constant("Portafoglio"), "asset_class", "ticker"],
        values="current_value",
        color="unrealized_pnl",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        labels={
            "current_value": "Controvalore (€)",
            "unrealized_pnl": "PnL Latente (€)",
            "weight_pct": "Peso (%)",
            "asset_class": "Asset Class",
            "ticker": "Asset"
        }
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Controvalore: € %{value:,.2f}<br>Peso: %{customdata[0]:.2f}%<br>PnL Latente: € %{color:+,.2f}<extra></extra>",
        customdata=df[["weight_pct"]].values
    )
    fig.update_layout(
        height=380,
        coloraxis_colorbar=dict(title="PnL Latente (€)"),
        margin=dict(l=10, r=10, t=10, b=10)
    )
    return apply_plotly_theme(fig)



def metric_card(label: str, value: str, delta: str = None, positive: bool = True, help_text: str = None):
    import re
    import random
    
    unique_id = f"{re.sub(r'[^a-zA-Z0-9]', '_', label).lower()}_{random.randint(1000, 9999)}"
    
    delta_html = ""
    if delta:
        cls = "metric-delta-pos" if positive else "metric-delta-neg"
        arrow = "↑" if positive else "↓"
        delta_html = f'<div class="{cls}">{arrow} {delta}</div>'
    
    modal_html = ""
    if help_text:
        safe_help_text = help_text.replace('\n', '<br>')
        
        modal_html = f"""<style>
#modal-toggle-{unique_id} {{ display: none; }}
.modal-overlay-{unique_id} {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(13, 17, 23, 0.85);
    z-index: 999999;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}}
#modal-toggle-{unique_id}:checked ~ .modal-overlay-{unique_id} {{
    display: flex;
}}
.modal-content-{unique_id} {{
    background: #161b22;
    border: 1px solid rgba(255, 153, 0, 0.4);
    padding: 30px;
    border-radius: 16px;
    width: 90%;
    max-width: 650px;
    max-height: 85vh;
    overflow-y: auto;
    color: #e6edf3;
    position: relative;
    box-shadow: 0 20px 40px rgba(0,0,0,0.8), 0 0 20px rgba(255, 153, 0, 0.1);
    font-family: 'Outfit', sans-serif;
    text-align: left;
    animation: modalFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}}
@keyframes modalFadeIn {{
    from {{ opacity: 0; transform: translateY(20px) scale(0.95); }}
    to {{ opacity: 1; transform: translateY(0) scale(1); }}
}}
.modal-close-{unique_id} {{
    position: absolute;
    top: 15px; right: 20px;
    cursor: pointer;
    font-size: 28px;
    color: rgba(255, 255, 255, 0.5);
    font-weight: 300;
    line-height: 1;
    transition: 0.2s;
}}
.modal-close-{unique_id}:hover {{
    color: #ff9900;
}}
.info-icon-{unique_id} {{
    cursor: pointer; 
    font-size: 13px; 
    color: #ff9900;
    background: rgba(255, 153, 0, 0.1);
    border-radius: 50%;
    width: 20px;
    height: 20px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-left: 8px;
    transition: all 0.2s;
    border: 1px solid transparent;
}}
.info-icon-{unique_id}:hover {{
    background: rgba(255, 153, 0, 0.2);
    border-color: rgba(255, 153, 0, 0.5);
    transform: scale(1.1);
}}
</style>

<input type="checkbox" id="modal-toggle-{unique_id}">
<div class="modal-overlay-{unique_id}">
    <div class="modal-content-{unique_id}">
        <label for="modal-toggle-{unique_id}" class="modal-close-{unique_id}">×</label>
        <h3 style="margin-top:0; border-bottom: 1px solid rgba(255,153,0,0.3); padding-bottom: 10px; color: #ffffff;">{label}</h3>
        <div style="font-size: 15px; line-height: 1.6; margin-top: 15px; color: #c9d1d9;">{safe_help_text}</div>
    </div>
</div>"""
        label_html = f'<div class="metric-label" style="display:flex; align-items:center;">{label} <label for="modal-toggle-{unique_id}" class="info-icon-{unique_id}" title="Clicca per approfondire">ⓘ</label></div>'
    else:
        label_html = f'<div class="metric-label">{label}</div>'

    st.markdown(f"""{modal_html}
<div class="metric-card">
    {label_html}
    <div class="metric-value">{value}</div>
    {delta_html}
</div>""", unsafe_allow_html=True)

def section(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

def fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{v:+.2f}%" if v != 0 else "0.00%"

def fmt_eur(v):
    if v is None:
        return "N/A"
    try:
        val = float(v)
    except (ValueError, TypeError):
        return "N/A"
        
    abs_v = abs(val)
    if abs_v >= 1_000_000_000:
        return f"€{val / 1_000_000_000:,.2f}B"
    elif abs_v >= 1_000_000:
        return f"€{val / 1_000_000:,.2f}M"
    else:
        return f"€{val:,.2f}"

def color_pnl(val):
    color = "#3fb950" if val >= 0 else "#f85149"
    return f"color: {color}; font-weight: 600"

def glossary_modal(title: str, content: str, button_label: str = "📖 Approfondisci"):
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    safe_content = content.replace('\n', '<br>')
    
    modal_html = f"""<style>
#modal-toggle-{unique_id} {{ display: none; }}
.modal-overlay-{unique_id} {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(13, 17, 23, 0.85);
    z-index: 999999;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}}
#modal-toggle-{unique_id}:checked ~ .modal-overlay-{unique_id} {{
    display: flex;
}}
.modal-content-{unique_id} {{
    background: #161b22;
    border: 1px solid rgba(255, 153, 0, 0.4);
    padding: 30px;
    border-radius: 16px;
    width: 90%;
    max-width: 650px;
    max-height: 85vh;
    overflow-y: auto;
    color: #e6edf3;
    position: relative;
    box-shadow: 0 20px 40px rgba(0,0,0,0.8), 0 0 20px rgba(255, 153, 0, 0.1);
    font-family: 'Outfit', sans-serif;
    text-align: left;
    animation: modalFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}}
.modal-close-{unique_id} {{
    position: absolute;
    top: 15px; right: 20px;
    cursor: pointer;
    font-size: 28px;
    color: rgba(255, 255, 255, 0.5);
    font-weight: 300;
    line-height: 1;
    transition: 0.2s;
}}
.modal-close-{unique_id}:hover {{
    color: #ff9900;
}}
.btn-glossary-{unique_id} {{
    cursor: pointer;
    background: rgba(255, 153, 0, 0.1);
    color: #ff9900;
    border: 1px solid rgba(255, 153, 0, 0.4);
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    margin-bottom: 12px;
}}
.btn-glossary-{unique_id}:hover {{
    background: rgba(255, 153, 0, 0.2);
    transform: translateY(-1px);
}}
</style>

<input type="checkbox" id="modal-toggle-{unique_id}">
<div class="modal-overlay-{unique_id}">
    <div class="modal-content-{unique_id}">
        <label for="modal-toggle-{unique_id}" class="modal-close-{unique_id}">×</label>
        <h3 style="margin-top:0; border-bottom: 1px solid rgba(255,153,0,0.3); padding-bottom: 10px; color: #ffffff;">{title}</h3>
        <div style="font-size: 15px; line-height: 1.6; margin-top: 15px; color: #c9d1d9;">{safe_content}</div>
    </div>
</div>

<label for="modal-toggle-{unique_id}" class="btn-glossary-{unique_id}">{button_label}</label>
"""
    st.markdown(modal_html, unsafe_allow_html=True)

def section(title: str):
    """Renders a section header with custom styling."""
    st.markdown(f"### {title}")


def render_db_status_badge(engine):
    """Visualizza un badge di stato del DB (MySQL DW Live vs SQLite Fallback)."""
    if engine is None:
        st.caption("🔴 **DB Connection**: Non connesso")
        return
    dialect = getattr(engine.dialect, "name", "").lower()
    if dialect == "mysql":
        st.markdown("""
        <div style="display: inline-flex; align-items: center; gap: 8px; padding: 4px 12px; background: rgba(0, 200, 83, 0.15); border: 1px solid rgba(0, 200, 83, 0.4); border-radius: 20px; font-size: 13px; color: #00e676; font-weight: 500; margin-bottom: 12px;">
            <span style="height: 8px; width: 8px; background-color: #00e676; border-radius: 50%; display: inline-block;"></span>
            MySQL Data Warehouse (Live)
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="display: inline-flex; align-items: center; gap: 8px; padding: 4px 12px; background: rgba(255, 153, 0, 0.15); border: 1px solid rgba(255, 153, 0, 0.4); border-radius: 20px; font-size: 13px; color: #ffab40; font-weight: 500; margin-bottom: 12px;">
            <span style="height: 8px; width: 8px; background-color: #ffab40; border-radius: 50%; display: inline-block;"></span>
            SQLite Local Storage (Fallback)
        </div>
        """, unsafe_allow_html=True)


def render_formula_popover(label: str, title: str, formula_latex: str, description: str):
    """Visualizza un popover interattivo con formula LaTeX e spiegazione concettuale."""
    with st.popover(label, help=f"Spiegazione dettagliata per {title}"):
        st.markdown(f"#### {title}")
        st.latex(formula_latex)
        st.markdown(description)


def load_benchmark_returns(ticker: str, df_prices, portfolio_index) -> pd.Series:
    """Carica o genera la serie dei rendimenti giornalieri per un qualsiasi benchmark specificato (SPY, QQQ, ACWI, AGG, GLD, BTC)."""
    import numpy as np
    import pandas as pd
    
    if portfolio_index is None or len(portfolio_index) == 0:
        return pd.Series(dtype=float)
        
    if df_prices is not None and isinstance(df_prices, pd.DataFrame) and not df_prices.empty and "ticker" in df_prices.columns:
        bm = df_prices[df_prices["ticker"] == ticker].copy()
        if not bm.empty:
            bm = bm.set_index("price_date")["close"].sort_index()
            bm_ret = bm.pct_change().fillna(0.0)
            bm_ret.name = ticker
            return bm_ret.reindex(portfolio_index).fillna(0.0)

    # Derivazione deterministica se non presente in DB
    spy_bm = pd.Series(0.0, index=portfolio_index, name=ticker)
    if df_prices is not None and isinstance(df_prices, pd.DataFrame) and not df_prices.empty and "ticker" in df_prices.columns:
        spy_df = df_prices[df_prices["ticker"] == "SPY"].copy()
        if not spy_df.empty:
            spy_s = spy_df.set_index("price_date")["close"].sort_index()
            spy_bm = spy_s.pct_change().fillna(0.0).reindex(portfolio_index).fillna(0.0)

    mult_map = {
        "SPY": 1.0,
        "QQQ": 1.25,
        "ACWI": 0.90,
        "AGG": 0.20,
        "GLD": 0.35,
        "BTC": 2.10,
        "BTC-USD": 2.10
    }
    m_factor = mult_map.get(ticker, 1.0)
    derived = spy_bm * m_factor
    derived.name = ticker
    return derived


