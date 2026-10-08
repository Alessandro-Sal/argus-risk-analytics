# ============================================================
# tests/test_sidebar_subtab_sync.py
# Test suite for bidirectional subtab and segmented tabs synchronization
# ============================================================

import os
from pathlib import Path

import streamlit as st

from core.sidebar import NAV_MODULES_RISK, NAV_MODULES_WEALTH
from core.ui_utils import render_segmented_tabs, resolve_active_subtab


def test_resolve_active_subtab():
    """Verifica che resolve_active_subtab risolva correttamente stato iniziale, target sidebar e fallback."""
    key = "test_resolve_key"
    keys_to_clean = [
        key,
        f"{key}_selectbox",
        f"target_subtab_{key}",
        f"_synced_tab_val_{key}",
        "global_target_subtab",
    ]
    for k in keys_to_clean:
        st.session_state.pop(k, None)

    options = ["Tab Alpha", "Tab Beta", "Tab Gamma"]

    # 1. Default fallback to first option
    res = resolve_active_subtab(options, key=key)
    assert res == "Tab Alpha"
    assert st.session_state[key] == "Tab Alpha"

    # 2. Sidebar target priority
    st.session_state[f"target_subtab_{key}"] = "Tab Gamma"
    res = resolve_active_subtab(options, key=key)
    assert res == "Tab Gamma"
    assert st.session_state[key] == "Tab Gamma"
    assert f"target_subtab_{key}" not in st.session_state

    # 3. Invalid target fallback
    st.session_state[f"target_subtab_{key}"] = "NonExistentTab"
    res = resolve_active_subtab(options, key=key)
    assert res == "Tab Gamma"  # keeps current if target invalid


def test_render_segmented_tabs_state_sync(monkeypatch):
    """Verifica che render_segmented_tabs mantenga sincronizzati tutti i puntatori di stato."""
    keys_to_clean = [
        "test_tab_key",
        "test_tab_key_selectbox",
        "target_subtab_test_tab_key",
        "_synced_tab_val_test_tab_key",
        "_prev_rendered_tab_test_tab_key",
        "global_target_subtab",
    ]
    for k in keys_to_clean:
        st.session_state.pop(k, None)

    options = ["Tab A", "Tab B", "Tab C"]

    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(st, "rerun", lambda: None)

    active = render_segmented_tabs(options, default="Tab A", key="test_tab_key")
    assert active == "Tab A"
    assert st.session_state["test_tab_key"] == "Tab A"
    assert st.session_state["test_tab_key_selectbox"] == "Tab A"
    assert st.session_state["_synced_tab_val_test_tab_key"] == "Tab A"

    # Simula click su Succ. ▶ (stile Bloomberg Risk Engine)
    def mock_button(label, *args, **kwargs):
        return label == "Succ. ▶"

    monkeypatch.setattr(st, "button", mock_button)
    rerun_called = []
    monkeypatch.setattr(st, "rerun", lambda: rerun_called.append(True))

    render_segmented_tabs(options, key="test_tab_key")
    assert st.session_state["test_tab_key"] == "Tab B"
    assert st.session_state["test_tab_key_selectbox"] == "Tab B"
    assert st.session_state["target_subtab_test_tab_key"] == "Tab B"
    assert st.session_state["_synced_tab_val_test_tab_key"] == "Tab B"
    assert len(rerun_called) == 1


def test_render_segmented_tabs_with_catalog(monkeypatch):
    """Verifica che render_segmented_tabs supporti cataloghi dizionario e formatti il banner."""
    catalog = {
        "Mod Alpha": {
            "title": "Modulo Alpha Istituzionale",
            "badge": "ALPHA • 95%",
            "badge_color": "#10b981",
            "category": "Quant",
            "desc": "Descrizione modulo alpha.",
        },
        "Mod Beta": {
            "title": "Modulo Beta Istituzionale",
            "badge": "BETA • 99%",
            "badge_color": "#f85149",
            "category": "Risk",
            "desc": "Descrizione modulo beta.",
        },
    }
    for k in ["cat_key", "cat_key_selectbox", "target_subtab_cat_key", "_synced_tab_val_cat_key", "_prev_rendered_tab_cat_key"]:
        st.session_state.pop(k, None)

    monkeypatch.setattr(st, "button", lambda *args, **kwargs: False)
    markdown_rendered = []
    monkeypatch.setattr(st, "markdown", lambda body, *args, **kwargs: markdown_rendered.append(body))

    active = render_segmented_tabs(catalog, key="cat_key")
    assert active == "Mod Alpha"
    assert st.session_state["cat_key"] == "Mod Alpha"
    assert any("Modulo Alpha Istituzionale" in str(m) for m in markdown_rendered)
    assert any("#10b981" in str(m) for m in markdown_rendered)


def test_sidebar_subtab_bidirectional_sync_logic():
    """Verifica la logica di sincronizzazione della sidebar senza sovrascritture stantie."""
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


def test_sidebar_and_selectbox_subtab_interaction_no_revert():
    """
    Verifica che dopo un click su un subtab della sidebar (che imposta target_subtab e global_target_subtab),
    un successivo cambio della selectbox da parte dell'utente non venga revertito dal target globale stantio.
    """
    key = "wealth_tax_active_tab"
    options = [
        "🏛️ Storico 730 & Riconciliazione",
        "📑 Prospetto Quadro RW / RT",
        "📉 Zainetto Fiscale & Scadenze",
        "🌾 Tax-Loss Harvesting & Plusvalenze",
        "⚖️ Ripartizione Italia vs Estero",
        "💡 Strategie di Efficienza Fiscale",
        "🌍 Fiscalità Internazionale & Cross-Border",
    ]
    for k in [
        key,
        f"{key}_selectbox",
        f"target_subtab_{key}",
        f"_synced_tab_val_{key}",
        f"_prev_rendered_tab_{key}",
        "global_target_subtab",
    ]:
        st.session_state.pop(k, None)

    # 1. Simula click sidebar su 'Tax-Loss Harvesting'
    st.session_state[f"target_subtab_{key}"] = "🌾 Tax-Loss Harvesting & Plusvalenze"
    st.session_state["global_target_subtab"] = "🌾 Tax-Loss Harvesting & Plusvalenze"

    res1 = resolve_active_subtab(options, key=key)
    assert res1 == "🌾 Tax-Loss Harvesting & Plusvalenze"
    assert f"target_subtab_{key}" not in st.session_state
    # global_target_subtab deve essere stato epurato
    assert "global_target_subtab" not in st.session_state

    # 2. Utente cambia la selectbox su '🏛️ Storico 730 & Riconciliazione'
    st.session_state[f"{key}_selectbox"] = "🏛️ Storico 730 & Riconciliazione"
    res2 = resolve_active_subtab(options, key=key)
    assert res2 == "🏛️ Storico 730 & Riconciliazione"
    assert st.session_state[key] == "🏛️ Storico 730 & Riconciliazione"
    assert st.session_state[f"{key}_selectbox"] == "🏛️ Storico 730 & Riconciliazione"

    # 3. Caso limite: anche se global_target_subtab fosse inquinato da un'altra chiamata,
    # la modifica diretta della selectbox da parte dell'utente deve prevalere
    st.session_state["global_target_subtab"] = "🌾 Tax-Loss Harvesting & Plusvalenze"
    st.session_state[f"{key}_selectbox"] = "📉 Zainetto Fiscale & Scadenze"
    res3 = resolve_active_subtab(options, key=key)
    assert res3 == "📉 Zainetto Fiscale & Scadenze"
    assert "global_target_subtab" not in st.session_state



def test_all_sidebar_subtabs_exist_in_page_files():
    """
    Test di regressione: verifica che TUTTE le subtabs configurate in NAV_MODULES_RISK
    e NAV_MODULES_WEALTH abbiano un target testuale che compare nel codice sorgente della relativa pagina.
    """
    all_modules = NAV_MODULES_RISK + NAV_MODULES_WEALTH
    project_root = Path(__file__).parent.parent

    for mod in all_modules:
        if not mod.get("has_subtabs"):
            continue

        raw_page_file = mod["page_file"]
        # In this project, pages are stored in src/pages
        page_rel = raw_page_file.replace("pages/", "src/pages/")
        page_path = project_root / page_rel

        assert page_path.exists(), f"Page file does not exist: {page_path}"

        with open(page_path, encoding="utf-8") as f:
            content = f.read()

        subtabs = mod.get("subtabs", [])
        assert len(subtabs) > 0, f"Module {mod['title']} has has_subtabs=True but subtabs is empty"

        for sub in subtabs:
            target = sub["target"]
            assert target in content, (
                f"Mismatch in module '{mod['title']}': target '{target}' not found in {page_path.name}"
            )


def test_wealth_telemetry_ribbon():
    """Verifica che il ribbon di telemetria Wealth calcoli correttamente stato, metriche e HTML."""
    from core.ui_utils import (
        build_wealth_telemetry_ribbon_html,
        build_wealth_telemetry_ribbon_state,
        render_wealth_telemetry_ribbon,
    )

    class DummyNW:
        total_net_worth = 2_500_000.0
        liquid_cash = 250_000.0
        runway_months = 18.5
        financial_investments = 1_400_000.0
        real_estate_total = 950_000.0
        total_liabilities = 100_000.0

    state = build_wealth_telemetry_ribbon_state(
        nw_summary=DummyNW(),
        page_badge="TEST BADGE",
        profile_name="Family Trust Alpha",
    )

    assert state["total_net_worth"] == 2_500_000.0
    assert state["liquid_cash"] == 250_000.0
    assert state["runway_months"] == 18.5
    assert state["solvency_label"] == "🟢 EXCELLENT RUNWAY"
    assert state["profile_name"] == "Family Trust Alpha"

    html = build_wealth_telemetry_ribbon_html(state)
    assert "ARGUS WEALTH" in html
    assert "Family Trust Alpha" in html
    assert "€ 2.500.000" in html
    assert "EXCELLENT RUNWAY" in html
    assert "\n" not in html  # must be single-line compact HTML

    # Rendering test
    rendered = render_wealth_telemetry_ribbon(
        nw_summary=DummyNW(),
        page_badge="TEST BADGE",
        profile_name="Family Trust Alpha",
    )
    assert rendered["total_net_worth"] == 2_500_000.0


def test_wealth_db_composite_indexes():
    """Verifica che init_wealth_db crei gli indici compositi su wealth_cashflow."""
    from sqlalchemy import create_engine, text

    from core.wealth.wealth_db import init_wealth_db

    mem_engine = create_engine("sqlite:///:memory:")
    init_wealth_db(mem_engine)

    with mem_engine.connect() as conn:
        res = conn.execute(text("PRAGMA index_list('wealth_cashflow');")).fetchall()
        idx_names = [r[1] for r in res]

    assert "idx_cf_port_date" in idx_names
    assert "idx_cf_port_cat" in idx_names
