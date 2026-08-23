# ==============================================================================
# tests/test_fase4_bquant_launchpad_excel.py
# Automated PyTest Suite for Phase 4: BQuant Sandbox, Launchpad & Excel Live Connector
# ==============================================================================

import os
import pytest
import pandas as pd
import numpy as np

from core.bquant_engine import (
    execute_bquant_script,
    BQUANT_SNIPPETS
)
from core.workspace_engine import (
    ROLE_PRESET_PROFILES,
    get_available_roles,
    get_role_profile,
    save_custom_workspace_layout,
    load_custom_workspace_layout
)
from core.excel_connector import (
    EXCEL_SUPPORTED_FIELDS,
    EXCEL_PORTFOLIO_RISK_FIELDS,
    build_bloomberg_formula,
    generate_vba_macro_code,
    generate_office_script_code,
    export_institutional_multisheet_excel
)
from core.ui_utils import parse_terminal_command


# ─────────────────────────────────────────────────────────────────────────────
# 1. BQuant Python Sandbox Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_bquant_script_execution_stdout_and_df():
    """Verifica che la sandbox BQuant catturi correttamente stdout e DataFrame di output."""
    sample_code = """
import pandas as pd
print("Hello BQuant Terminal!")
df_out = pd.DataFrame({
    'ticker': ['AAPL', 'MSFT', 'NVDA'],
    'score': [95.5, 92.0, 98.2]
})
"""
    res = execute_bquant_script(sample_code)
    assert res["success"] is True
    assert "Hello BQuant Terminal!" in res["stdout"]
    assert res["output_df"] is not None
    assert len(res["output_df"]) == 3
    assert "ticker" in res["output_df"].columns
    assert res["execution_time_sec"] >= 0.0


def test_bquant_duckdb_sql_integration():
    """Verifica l'interrogazione SQL in-memory tramite DuckDB su DataFrame di portafoglio."""
    df_pos = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "JNJ", "PG"],
        "current_value": [25000.0, 35000.0, 20000.0, 20000.0],
        "weight_pct": [25.0, 35.0, 20.0, 20.0],
        "gics_sector": ["Technology", "Technology", "Healthcare", "Consumer Defensive"]
    })
    ctx = {"df_positions": df_pos}
    
    duckdb_code = """
import duckdb
con = duckdb.connect(':memory:')
con.register('positions', df_positions)
df_out = con.execute("SELECT gics_sector, SUM(current_value) as val FROM positions GROUP BY 1 ORDER BY 2 DESC").df()
"""
    res = execute_bquant_script(duckdb_code, ctx)
    assert res["success"] is True
    assert res["output_df"] is not None
    assert len(res["output_df"]) == 3
    assert float(res["output_df"].iloc[0]["val"]) == 60000.0 # Tech total


def test_bquant_presets_execution_all():
    """Verifica che tutti i 5 snippet istituzionali preimpostati vengano eseguiti senza errori."""
    df_pos = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "GOOGL"],
        "current_value": [10000.0, 15000.0, 12000.0],
        "weight_pct": [27.0, 40.5, 32.5],
        "gics_sector": ["Technology", "Technology", "Communication"]
    })
    df_pr = pd.DataFrame({
        "price_date": pd.date_range("2024-01-01", "2024-03-01", freq="B"),
        "AAPL": np.linspace(180, 195, 45),
        "MSFT": np.linspace(380, 410, 45),
        "GOOGL": np.linspace(140, 155, 45)
    })
    df_rets = pd.DataFrame({
        "AAPL": np.random.normal(0.0005, 0.012, 100),
        "MSFT": np.random.normal(0.0006, 0.011, 100),
        "GOOGL": np.random.normal(0.0004, 0.013, 100)
    })
    ctx = {"df_positions": df_pos, "df_prices": df_pr, "df_returns": df_rets}
    
    for key, data in BQUANT_SNIPPETS.items():
        res = execute_bquant_script(data["code"], ctx)
        assert res["success"] is True, f"Snippet [{key}] fallito con errore: {res.get('error')}"
        assert res["execution_time_sec"] >= 0.0


def test_bquant_error_handling_and_sandboxing():
    """Verifica che errori di sintassi e runtime vengano intercettati in modo sicuro."""
    syntax_err_code = "for i in range(10) print(i)" # Errore due punti mancanti
    res_syn = execute_bquant_script(syntax_err_code)
    assert res_syn["success"] is False
    assert "SyntaxError" in res_syn["error"]

    runtime_err_code = "x = 10 / 0" # Zero division
    res_run = execute_bquant_script(runtime_err_code)
    assert res_run["success"] is False
    assert "ZeroDivisionError" in res_run["error"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Launchpad & Workspace Customizer Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_workspace_role_profiles_structure():
    """Verifica la completezza dei 5 profili di ruolo istituzionali."""
    roles = get_available_roles()
    assert len(roles) >= 5
    
    expected_roles = ["trading_desk", "risk_officer", "portfolio_manager", "quant_analyst", "corporate_treasurer"]
    for role_id in expected_roles:
        profile = get_role_profile(role_id)
        assert profile["id"] == role_id
        assert "title" in profile
        assert "primary_pages" in profile
        assert len(profile["primary_pages"]) >= 3
        assert "key_kpis" in profile


def test_workspace_layout_persistence(tmp_path):
    """Verifica il salvataggio e il recupero del layout utente su SQLite."""
    ok = save_custom_workspace_layout("test_user_1", "trading_desk", {"zoom": 1.1})
    assert ok is True
    
    loaded = load_custom_workspace_layout("test_user_1")
    assert loaded["found"] is True
    assert loaded["active_role"] == "trading_desk"
    assert loaded["custom_widgets"].get("zoom") == 1.1


# ─────────────────────────────────────────────────────────────────────────────
# 3. Excel Live Connector & Multi-Sheet Exporter Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_excel_bloomberg_formulas_generation():
    """Verifica la corretta formattazione delle formule Bloomberg-Style per Excel."""
    f_bdp = build_bloomberg_formula("BDP", "AAPL", "LAST_PRICE")
    assert f_bdp == '=ARGUS_BDP("AAPL", "LAST_PRICE")'
    
    f_bdh = build_bloomberg_formula("BDH", "MSFT", "CLOSE", "2024-01-01", "2026-08-01")
    assert f_bdh == '=ARGUS_BDH("MSFT", "CLOSE", "2024-01-01", "2026-08-01")'
    
    f_risk = build_bloomberg_formula("RISK", "", "PORTFOLIO_VAR_95")
    assert f_risk == '=ARGUS_RISK("PORTFOLIO_VAR_95")'


def test_excel_vba_and_office_script_generators():
    """Verifica la generazione dei moduli di integrazione VBA e Office Scripts."""
    vba_code = generate_vba_macro_code()
    assert "Public Function ARGUS_BDP" in vba_code
    assert "Public Function ARGUS_RISK" in vba_code
    
    ts_code = generate_office_script_code()
    assert "async function main" in ts_code
    assert "portfolio_snapshot" in ts_code


def test_excel_institutional_multisheet_export():
    """Verifica la generazione del file Excel multi-foglio (.xlsx)."""
    mock_bundle = {
        "positions": pd.DataFrame({
            "ticker": ["AAPL", "MSFT", "NVDA"],
            "current_value": [50000.0, 30000.0, 20000.0],
            "weight_pct": [50.0, 30.0, 20.0],
            "unrealized_pnl": [5000.0, 3000.0, 1000.0]
        }),
        "metrics": {
            "market_risk": {"sharpe_ratio": 1.45, "volatility_annualized_pct": 16.5, "var_parametric_95_eur": 1650.0},
            "returns": {"cagr_pct": 14.2}
        },
        "risk_free": {"rate_pct": 2.75}
    }
    
    xlsx_bytes = export_institutional_multisheet_excel(mock_bundle)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 2000 # File xlsx valido non vuoto


# ─────────────────────────────────────────────────────────────────────────────
# 4. Command Gateway Phase 4 Mnemonics Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_terminal_command_gateway_phase4_mnemonics():
    """Verifica il corretto parsing e routing dei nuovi comandi gateway di Fase 4."""
    cmd_bquant = parse_terminal_command("BQUANT")
    assert cmd_bquant is not None
    assert "10_💻_BQuant_e_Launchpad.py" in cmd_bquant["page"]
    assert "🐍" in cmd_bquant["target"]

    cmd_py = parse_terminal_command("PY")
    assert cmd_py is not None
    assert "10_💻_BQuant_e_Launchpad.py" in cmd_py["page"]

    cmd_launchpad = parse_terminal_command("LAUNCHPAD")
    assert cmd_launchpad is not None
    assert "10_💻_BQuant_e_Launchpad.py" in cmd_launchpad["page"]
    assert "🎛️" in cmd_launchpad["target"]

    cmd_xl = parse_terminal_command("XL")
    assert cmd_xl is not None
    assert "10_💻_BQuant_e_Launchpad.py" in cmd_xl["page"]
    assert "📊" in cmd_xl["target"]
