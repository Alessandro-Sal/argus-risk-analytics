# ============================================================
# tests/test_sidebar_subtab_sync.py
# Test suite for bidirectional subtab and segmented tabs synchronization
# ============================================================

import pytest
import streamlit as st


def test_render_segmented_tabs_state_sync(monkeypatch):
    """Verifica che render_segmented_tabs mantenga sincronizzati tutti i puntatori di stato."""
    from core.ui_utils import render_segmented_tabs

    # Pulisci session state per il test
    keys_to_clean = [
        "test_tab_key",
        "test_tab_key_selectbox",
        "target_subtab_test_tab_key",
        "_synced_tab_val_test_tab_key",
        "_prev_rendered_tab_test_tab_key",
        "global_target_subtab",
    ]
    for k in keys_to_clean:
        if k in st.session_state:
            del st.session_state[k]

    options = ["Tab A", "Tab B", "Tab C"]

    # Simula render iniziale
    # Monkeypatch st.button per non cliccare nulla
    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(st, "rerun", lambda: None)

    active = render_segmented_tabs(options, default="Tab A", key="test_tab_key")
    assert active == "Tab A"
    assert st.session_state["test_tab_key"] == "Tab A"
    assert st.session_state["test_tab_key_selectbox"] == "Tab A"
    assert st.session_state["_synced_tab_val_test_tab_key"] == "Tab A"

    # Simula click su Tab B
    def mock_button(label, *args, **kwargs):
        return label == "Tab B"

    monkeypatch.setattr(st, "button", mock_button)
    rerun_called = []
    monkeypatch.setattr(st, "rerun", lambda: rerun_called.append(True))

    active_after_click = render_segmented_tabs(options, key="test_tab_key")
    assert st.session_state["test_tab_key"] == "Tab B"
    assert st.session_state["test_tab_key_selectbox"] == "Tab B"
    assert st.session_state["target_subtab_test_tab_key"] == "Tab B"
    assert st.session_state["_synced_tab_val_test_tab_key"] == "Tab B"
    assert len(rerun_called) == 1


def test_sidebar_subtab_bidirectional_sync_logic():
    """Verifica la logica di sincronizzazione della sidebar senza sovrascritture stantie."""
    active_nav_modules = [
        {
            "has_subtabs": True,
            "tab_key": "sync_test_mod",
        }
    ]

    tk = "sync_test_mod"
    sb_k = f"{tk}_selectbox"
    tgt_k = f"target_subtab_{tk}"
    sync_k = f"_synced_tab_val_{tk}"

    # Scenario 1: Tab iniziale impostato a "Tab 1"
    st.session_state[tk] = "Tab 1"
    st.session_state[sb_k] = "Tab 1"
    st.session_state[sync_k] = "Tab 1"
    st.session_state.pop(tgt_k, None)

    # Simula click utente su tab button interno che cambia solo tk
    st.session_state[tk] = "Tab 2"

    # Esegui la logica del blocco 1.1 della sidebar
    prev_val = st.session_state.get(sync_k)
    if tgt_k in st.session_state and st.session_state[tgt_k]:
        val = st.session_state[tgt_k]
        st.session_state[tk] = val
        st.session_state[sb_k] = val
        st.session_state[sync_k] = val
    else:
        curr_tk = st.session_state.get(tk)
        curr_sb = st.session_state.get(sb_k)
        if curr_tk != prev_val and curr_tk is not None:
            st.session_state[sb_k] = curr_tk
            st.session_state[sync_k] = curr_tk
        elif curr_sb != prev_val and curr_sb is not None:
            st.session_state[tk] = curr_sb
            st.session_state[sync_k] = curr_sb

    # sb_k deve essere stato allineato a "Tab 2", tk NON deve essere tornato a "Tab 1"!
    assert st.session_state[tk] == "Tab 2"
    assert st.session_state[sb_k] == "Tab 2"
    assert st.session_state[sync_k] == "Tab 2"

    # Scenario 2: Utente cambia la selectbox su una pagina classica
    st.session_state[sb_k] = "Tab 3"
    prev_val = st.session_state.get(sync_k)
    curr_tk = st.session_state.get(tk)
    curr_sb = st.session_state.get(sb_k)
    if curr_tk != prev_val and curr_tk is not None:
        st.session_state[sb_k] = curr_tk
        st.session_state[sync_k] = curr_tk
    elif curr_sb != prev_val and curr_sb is not None:
        st.session_state[tk] = curr_sb
        st.session_state[sync_k] = curr_sb

    assert st.session_state[tk] == "Tab 3"
    assert st.session_state[sb_k] == "Tab 3"
    assert st.session_state[sync_k] == "Tab 3"
