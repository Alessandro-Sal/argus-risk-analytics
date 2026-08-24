# ==============================================================================
# core/workspace_engine.py
# ARGUS Launchpad & Institutional Workspace Customizer
# Role-based workspace profiles, widget orchestration and layout persistence.
# ==============================================================================

import os
import json
import sqlite3
from typing import Dict, Any, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# 1. Institutional Role Profiles & Preset Configurations
# ─────────────────────────────────────────────────────────────────────────────

ROLE_PRESET_PROFILES: Dict[str, Dict[str, Any]] = {
    "trading_desk": {
        "id": "trading_desk",
        "title": "📈 Trading Desk & Execution",
        "subtitle": "Intraday Microstructure, Optimal Liquidation & Hedging",
        "badge_color": "#ff9900",
        "icon": "⚡",
        "description": "Ottimizzato per trader istituzionali, execution desk e market maker. Focus su flussi streaming ad alta frequenza, order book L2, slippage Almgren-Chriss e coperture delta rapide.",
        "primary_pages": [
            {"name": "Posizioni e Dettagli", "page": "4_📋_Posizioni_e_Dettagli", "tab": "⚡ Liquidità & Smart Order Router"},
            {"name": "Analisi Tecnica", "page": "8_📈_Analisi_Tecnica", "tab": "🧱 Volume Profile Dettaglio"},
            {"name": "Modelli Quantitativi", "page": "3_🔬_Modelli_Quantitativi", "tab": "🛡️ Hedging & Opzioni"},
            {"name": "BQuant Python", "page": "10_💻_BQuant_e_Launchpad", "tab": "🐍 ARGUS BQuant Python Sandbox"}
        ],
        "key_kpis": ["Order Flow Imbalance", "Microprice L2", "Slippage Stimato", "Execution VaR", "Delta Hedge Ratio"],
        "recommended_refresh_rate": 5 # secondi
    },

    "risk_officer": {
        "id": "risk_officer",
        "title": "🛡️ Risk Officer & Compliance",
        "subtitle": "VaR/CVaR, GARCH-FHS, Basel Backtest & Stress Testing 3D",
        "badge_color": "#f85149",
        "icon": "🛡️",
        "description": "Configurato per Chief Risk Officer e comitati di controllo. Focus su limiti di rischio Basel III/IV, volatilità dinamica GARCH(1,1), stress test macroeconomici 3D e LVaR Bangia.",
        "primary_pages": [
            {"name": "Analisi Rischio", "page": "2_🔴_Analisi_Rischio", "tab": "📉 VaR, CVaR & Backtesting Kupiec"},
            {"name": "Analisi Rischio", "page": "2_🔴_Analisi_Rischio", "tab": "📊 Profilo del Rischio & Fama-French"},
            {"name": "Stress Testing", "page": "6_🌪️_Stress_Testing", "tab": "⚡ Matrice Comparativa MSCI Barra"},
            {"name": "Analisi Rischio", "page": "2_🔴_Analisi_Rischio", "tab": "🔗 Correlazioni, Liquidità & ATR Chandelier"}
        ],
        "key_kpis": ["Parametric VaR 95%", "Expected Shortfall (CVaR)", "GARCH Term Structure", "Basel Traffic Light Zone", "LVaR 5-Days"],
        "recommended_refresh_rate": 60
    },

    "portfolio_manager": {
        "id": "portfolio_manager",
        "title": "💼 Portfolio Manager & CIO",
        "subtitle": "HRP Frontier, Brinson Attribution, Factor Backtest & Dividends",
        "badge_color": "#58a6ff",
        "icon": "💼",
        "description": "Strutturato per gestori di fondi e allocatori strategici. Focus sull'ottimizzazione Hierarchical Risk Parity, attribuzione performance Brinson / Fama-French, backtesting a quintili e flussi cedolari.",
        "primary_pages": [
            {"name": "Dashboard Generale", "page": "1_📈_Dashboard_Generale", "tab": "Dashboard Generale"},
            {"name": "Modelli Quantitativi", "page": "3_🔬_Modelli_Quantitativi", "tab": "📊 Markowitz & Rebalancing"},
            {"name": "Modelli Quantitativi", "page": "3_🔬_Modelli_Quantitativi", "tab": "🎯 Attribuzione & Fattori"},
            {"name": "Screener Opportunità", "page": "9_🔍_Screener_Opportunita", "tab": "🔍 Screener Multi-Fattoriale & Archetipi"}
        ],
        "key_kpis": ["Sharpe Ratio", "Information Ratio", "Alpha Fama-French", "Spread Long-Short Q1-Q5", "Yield on Cost"],
        "recommended_refresh_rate": 30
    },

    "quant_analyst": {
        "id": "quant_analyst",
        "title": "🔬 Quantitative Analyst & Data Scientist",
        "subtitle": "BQuant Python Sandbox, Volatility Surface & Jump-Diffusion",
        "badge_color": "#d2a8ff",
        "icon": "🔬",
        "description": "Dedicato alla ricerca quantitativa e modellistica avanzata. Include console interattiva BQuant Python, superfici di volatilità SVI/Spline, calibrazione Merton Jump-Diffusion e clustering non supervisionato K-Means.",
        "primary_pages": [
            {"name": "BQuant Python", "page": "10_💻_BQuant_e_Launchpad", "tab": "🐍 ARGUS BQuant Python Sandbox"},
            {"name": "Modelli Quantitativi", "page": "3_🔬_Modelli_Quantitativi", "tab": "🎲 Monte Carlo & Merton"},
            {"name": "Modelli Quantitativi", "page": "3_🔬_Modelli_Quantitativi", "tab": "🧬 Tail Copula & Kelly"},
            {"name": "Modelli Quantitativi", "page": "3_🔬_Modelli_Quantitativi", "tab": "🤖 AI Reinforcement Learning"}
        ],
        "key_kpis": ["Implied Volatility Smile", "Jump Intensity (λ)", "Spearman Monotonicity", "K-Means Silhouette", "Python Execution Time"],
        "recommended_refresh_rate": 0 # Manual execution
    },

    "corporate_treasurer": {
        "id": "corporate_treasurer",
        "title": "🏛️ Corporate Treasurer & Fixed Income",
        "subtitle": "Fixed Income YAS, Z-Spread, CDS Curve & Tax Optimization",
        "badge_color": "#3fb950",
        "icon": "🏛️",
        "description": "Ottimizzato per direttori finanziari, tesorieri d'impresa e desk obbligazionari. Focus su YTM, Duration, Convexity, Z-Spread Nelson-Siegel, monitoraggio CDS sovrano/corporate e compensazione fiscale minusvalenze.",
        "primary_pages": [
            {"name": "Modelli Quantitativi", "page": "3_🔬_Modelli_Quantitativi", "tab": "🏛️ Fixed Income & Z-Spread"},
            {"name": "Posizioni e Dettagli", "page": "4_📋_Posizioni_e_Dettagli", "tab": "💰 Ottimizzazione Fiscale (TUIR Art. 67)"},
            {"name": "Valutazione Aziendale", "page": "5_🏛️_Valutazione_Aziendale", "tab": "🏛️ Fair Value & Consensus Analisti"},
            {"name": "Excel Live Connector", "page": "10_💻_BQuant_e_Launchpad", "tab": "📊 Excel Live Connector & RTD"}
        ],
        "key_kpis": ["Yield to Maturity (YTM)", "Modified Duration", "DV01 Total", "Z-Spread (bps)", "Credito Fiscale Zainetto"],
        "recommended_refresh_rate": 120
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Database Persistence for Custom Workspace Layouts
# ─────────────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "argus_workspaces.db")

def _init_workspace_db():
    """Inizializza la tabella SQLite per la memorizzazione dei layout personalizzati."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_workspaces (
                user_id TEXT PRIMARY KEY,
                active_role TEXT,
                custom_widgets TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_custom_workspace_layout(user_id: str, active_role: str, custom_widgets: Optional[Dict[str, Any]] = None) -> bool:
    """Salva il layout personalizzato e il ruolo attivo dell'utente nel DB locale."""
    try:
        _init_workspace_db()
        widgets_json = json.dumps(custom_widgets or {})
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_workspaces (user_id, active_role, custom_widgets, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, active_role, widgets_json))
            conn.commit()
        return True
    except Exception:
        return False

def load_custom_workspace_layout(user_id: str) -> Dict[str, Any]:
    """Carica il layout personalizzato dell'utente dal DB locale."""
    try:
        _init_workspace_db()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT active_role, custom_widgets FROM user_workspaces WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                role, widgets_str = row
                return {
                    "active_role": role,
                    "custom_widgets": json.loads(widgets_str) if widgets_str else {},
                    "found": True
                }
    except Exception:
        pass
    return {
        "active_role": "portfolio_manager",
        "custom_widgets": {},
        "found": False
    }

def get_role_profile(role_key: str) -> Dict[str, Any]:
    """Restituisce la configurazione completa per il ruolo selezionato."""
    clean_k = str(role_key).lower().strip()
    return ROLE_PRESET_PROFILES.get(clean_k, ROLE_PRESET_PROFILES["portfolio_manager"])

def get_available_roles() -> List[Dict[str, Any]]:
    """Restituisce la lista di tutti i profili di ruolo disponibili."""
    return list(ROLE_PRESET_PROFILES.values())
