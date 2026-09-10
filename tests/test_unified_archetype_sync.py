import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pandas as pd
from unittest.mock import MagicMock

# Mock streamlit session_state
import streamlit as st
if not hasattr(st, "session_state") or not isinstance(st.session_state, dict):
    class SessionState(dict):
        def __getattr__(self, item):
            return self.get(item)
        def __setattr__(self, key, value):
            self[key] = value
        def __delattr__(self, item):
            self.pop(item, None)
    st.session_state = SessionState()

# Mock st.spinner, st.rerun, st.cache_data
st.spinner = MagicMock()
st.rerun = MagicMock()
st.cache_data = MagicMock()
st.cache_data.clear = MagicMock()

from core.archetype_manager import execute_unified_archetype_load, clear_unified_archetype
from core.fetcher import get_engine
from core.wealth.wealth_db import get_wealth_portfolios

def test_unified_loading():
    print("--- 1. Testing execute_unified_archetype_load ---")
    st.session_state["offline_mode"] = True
    db_res = execute_unified_archetype_load("young_accumulator", auto_run=False, source_module="risk")
    
    print(f"db_res: {db_res}")
    assert "risk_portfolio_id" in db_res, "Missing risk_portfolio_id"
    assert "wealth_profile_id" in db_res, "Missing wealth_profile_id"
    
    # Check Session State for Risk
    assert st.session_state.get("portfolio_id") == db_res["risk_portfolio_id"], "Risk portfolio_id mismatch"
    assert st.session_state.get("active_archetype_code") == "young_accumulator", "Archetype code mismatch"
    assert isinstance(st.session_state.get("df_raw_injected"), pd.DataFrame), "df_raw_injected is not DataFrame"
    assert len(st.session_state["df_raw_injected"]) > 0, "Transactions DF is empty"
    
    # Check Session State for Wealth
    assert st.session_state.get("wealth_active_portfolio_id") == db_res["wealth_profile_id"], "Wealth portfolio_id mismatch"
    assert "Patrimonio" in st.session_state.get("wealth_active_profile_name", ""), "Wealth profile name missing"
    
    # Check SQLite contents
    eng = get_engine(offline=True, sqlite_path="data/argus_local.db")
    with eng.connect() as conn:
        tx_count = conn.exec_driver_sql("SELECT COUNT(*) FROM transactions WHERE portfolio_id = :pid", {"pid": db_res["risk_portfolio_id"]}).scalar()
        print(f"SQLite Risk transactions count: {tx_count}")
        assert tx_count > 0, "No transactions found in SQLite"
        
        acc_count = conn.exec_driver_sql("SELECT COUNT(*) FROM wealth_accounts WHERE portfolio_id = :pid", {"pid": db_res["wealth_profile_id"]}).scalar()
        print(f"SQLite Wealth accounts count: {acc_count}")
        assert acc_count > 0, "No wealth accounts found in SQLite"
    
    print("✅ execute_unified_archetype_load passed!")

def test_unified_clearing():
    print("--- 2. Testing clear_unified_archetype ---")
    clear_unified_archetype()
    assert st.session_state.get("df_raw_injected") is None, "df_raw_injected not cleared"
    assert st.session_state.get("active_archetype_code") is None, "active_archetype_code not cleared"
    assert st.session_state.get("portfolio_name") == "", "portfolio_name not cleared"
    assert st.session_state.get("wealth_active_portfolio_id") is None, "wealth_active_portfolio_id not cleared"
    print("✅ clear_unified_archetype passed!")

def test_db_sync_state():
    print("--- 3. Testing DB State Synchronization ---")
    # Simulate DB switch in sidebar
    target_db = "argus_custom_db"
    st.session_state["db_name"] = target_db
    st.session_state["wealth_db_name"] = target_db
    st.session_state["risk_db_name"] = target_db
    
    assert st.session_state["db_name"] == st.session_state["wealth_db_name"] == st.session_state["risk_db_name"] == target_db
    print("✅ DB state synchronization passed!")

if __name__ == "__main__":
    test_unified_loading()
    test_unified_clearing()
    test_db_sync_state()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
