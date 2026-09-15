# ==============================================================================
# components/command_palette.py
# ARGUS Risk Analytics — Bloomberg-Style Command Palette (Ctrl+K) v9.7.0
# ==============================================================================
"""
Universal Command Palette & Fast Asset/Workspace Switcher:
- Global Ctrl+K / Cmd+K hotkey interceptor via resilient multi-context JavaScript snippet.
- Fuzzy filtering across all 22 ARGUS pages, active portfolio assets/ISINs,
  and macro stress scenarios.
- Full compatibility with standard web browsers and Windows Native Desktop (.exe via WebView2).
- Direct non-blocking navigation and session state propagation.
"""

from typing import Any, Dict, List, Optional
import os
import streamlit as st
import streamlit.components.v1 as components

from core.sidebar import switch_to_page


HOTKEY_JS_SNIPPET = """
<div id="argus-cmd-palette-listener-stub" style="display:none; width:0; height:0;"></div>
<script>
(function() {
    function getRootWindow() {
        try {
            if (window.top && window.top.document) return window.top;
        } catch(e) {}
        try {
            if (window.parent && window.parent.document) return window.parent;
        } catch(e) {}
        return window;
    }

    function findTriggerButton(rootDoc) {
        if (!rootDoc) return null;

        // 1. Explicit ID or testid
        var btn = rootDoc.getElementById('argus-cmd-palette-trigger') ||
                  rootDoc.querySelector('[data-testid="argus_cmd_palette_btn"]') ||
                  rootDoc.querySelector('[data-testid="argus-cmd-palette-btn"]');
        if (btn) return btn;

        // 2. Near anchor element in main Streamlit DOM
        var anchor = rootDoc.getElementById('argus-cmd-palette-anchor') ||
                     rootDoc.querySelector('[data-argus-role="cmd-palette-anchor"]');
        if (anchor) {
            var container = anchor.closest('[data-testid="stVerticalBlock"]') ||
                            anchor.closest('.stButton') ||
                            anchor.parentElement;
            if (container) {
                var cBtn = container.querySelector('button');
                if (cBtn) return cBtn;
            }
        }

        // 3. Inspect all buttons by text content
        var allButtons = rootDoc.querySelectorAll('button');
        for (var i = 0; i < allButtons.length; i++) {
            var text = (allButtons[i].innerText || allButtons[i].textContent || '').toLowerCase();
            if (text.indexOf('quick command') !== -1 || text.indexOf('ctrl+k') !== -1 || text.indexOf('cmd+k') !== -1) {
                return allButtons[i];
            }
        }

        return null;
    }

    function triggerPalette() {
        var rootWin = getRootWindow();
        var rootDoc = rootWin.document;
        if (!rootDoc) return;

        var btn = findTriggerButton(rootDoc);
        if (btn) {
            try {
                btn.focus();
                btn.click();
                btn.dispatchEvent(new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: rootWin
                }));
            } catch(err) {
                console.error('[ARGUS Command Palette] Click dispatch error:', err);
            }
        }
    }

    function handleKeyDown(e) {
        // Detect Ctrl+K or Cmd+K across all keyboard locales & CapsLock states
        var isK = (e.key === 'k' || e.key === 'K' || e.code === 'KeyK' || e.keyCode === 75);
        var isModifier = (e.ctrlKey || e.metaKey);

        if (isModifier && isK) {
            e.preventDefault();
            e.stopPropagation();
            if (e.stopImmediatePropagation) e.stopImmediatePropagation();
            triggerPalette();
        }
    }

    function registerListeners() {
        var targets = [];
        try { if (window.top && window.top.document) targets.push(window.top.document); } catch(e) {}
        try { if (window.parent && window.parent.document && targets.indexOf(window.parent.document) === -1) targets.push(window.parent.document); } catch(e) {}
        try { if (window.document && targets.indexOf(window.document) === -1) targets.push(window.document); } catch(e) {}

        var rootWin = getRootWindow();
        if (rootWin.__argus_cmd_k_listener) {
            for (var i = 0; i < targets.length; i++) {
                try {
                    targets[i].removeEventListener('keydown', rootWin.__argus_cmd_k_listener, true);
                } catch(e) {}
            }
        }

        rootWin.__argus_cmd_k_listener = handleKeyDown;

        for (var j = 0; j < targets.length; j++) {
            try {
                targets[j].addEventListener('keydown', handleKeyDown, true);
            } catch(e) {}
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', registerListeners);
    } else {
        registerListeners();
    }
    setTimeout(registerListeners, 250);
    setTimeout(registerListeners, 1000);
})();
</script>
"""

# Catalogo canonico delle 22 pagine di ARGUS
CATALOG_PAGES = [
    {"label": "Control Room & Setup", "file": "0_Control_Room.py", "icon": "🎛️", "cat": "Risk Core"},
    {"label": "Dashboard Generale", "file": "pages/1_📈_Dashboard_Generale.py", "icon": "📈", "cat": "Risk Core"},
    {"label": "Live Terminal & Desk", "file": "pages/2_🖥️_Live_Terminal.py", "icon": "🖥️", "cat": "Risk Core"},
    {"label": "Analisi del Rischio", "file": "pages/3_🔴_Analisi_Rischio.py", "icon": "🔴", "cat": "Risk Analytics"},
    {"label": "Modelli Quantitativi", "file": "pages/4_🔬_Modelli_Quantitativi.py", "icon": "🔬", "cat": "Risk Analytics"},
    {"label": "Posizioni & Dettagli Fiscali", "file": "pages/5_📋_Posizioni_e_Dettagli.py", "icon": "📋", "cat": "Portfolio & Tax"},
    {"label": "Valutazione Aziendale", "file": "pages/6_🏛️_Valutazione_Aziendale.py", "icon": "🏛️", "cat": "Valuation"},
    {"label": "Stress Testing & Scenari", "file": "pages/7_🌪️_Stress_Testing.py", "icon": "🌪️", "cat": "Risk Analytics"},
    {"label": "Analisi Temporale & Stili", "file": "pages/8_📊_Analisi_Temporale.py", "icon": "📊", "cat": "Risk Analytics"},
    {"label": "Analisi Tecnica & Indicatori", "file": "pages/9_📈_Analisi_Tecnica.py", "icon": "📈", "cat": "Market"},
    {"label": "Screener Opportunità Multi-Asset", "file": "pages/10_🔍_Screener_Opportunita.py", "icon": "🔍", "cat": "Market"},
    {"label": "BQuant Sandbox & Launchpad", "file": "pages/11_💻_BQuant_e_Launchpad.py", "icon": "💻", "cat": "Quant Dev"},
    {"label": "Wealth Control Room", "file": "pages/12_🎛️_Wealth_Control_Room.py", "icon": "🎛️", "cat": "Wealth Core"},
    {"label": "Patrimonio & Net Worth Master", "file": "pages/13_🏛️_Patrimonio_e_NetWorth.py", "icon": "🏛️", "cat": "Wealth Core"},
    {"label": "Cash Flow & Spese Personali", "file": "pages/14_💳_Cash_Flow_e_Spese.py", "icon": "💳", "cat": "Wealth Core"},
    {"label": "Asset Illiquidi, Orologi & Arte", "file": "pages/15_⌚_Asset_Illiquidi_e_Orologi.py", "icon": "⌚", "cat": "Wealth Illiquid"},
    {"label": "Previdenza & Pension Planning", "file": "pages/16_🛡️_Previdenza_e_Pension_Planning.py", "icon": "🛡️", "cat": "Wealth Advisory"},
    {"label": "Indipendenza Finanziaria (FIRE)", "file": "pages/17_🔥_Indipendenza_Finanziaria_e_FIRE.py", "icon": "🔥", "cat": "Wealth Advisory"},
    {"label": "Fiscalità, Minusvalenze & Quadro RW", "file": "pages/18_📑_Fiscalita_e_Quadro_RW.py", "icon": "📑", "cat": "Tax Compliance"},
    {"label": "Immobili, Mutui & Rendite", "file": "pages/19_🏡_Immobili_e_Mutui.py", "icon": "🏡", "cat": "Wealth Real Estate"},
    {"label": "Pianificazione Successoria & Trust", "file": "pages/20_⚖️_Pianificazione_Successoria.py", "icon": "⚖️", "cat": "Wealth Estate"},
    {"label": "Tri-Agent AI Copilot & Governance", "file": "pages/21_🤖_AI_Copilot_e_Advisor.py", "icon": "🤖", "cat": "AI Governance"},
]

# Scenari macro predefiniti
CATALOG_SCENARIOS = [
    {"label": "Scenario: Crisi Mutui Subprime Lehman (2007-2009)", "code": "LEHMAN_2008", "target_page": "pages/7_🌪️_Stress_Testing.py", "icon": "📉", "cat": "Macro Stress"},
    {"label": "Scenario: Flash Crash Pandemia COVID-19 (2020)", "code": "COVID_2020", "target_page": "pages/7_🌪️_Stress_Testing.py", "icon": "🦠", "cat": "Macro Stress"},
    {"label": "Scenario: Shock Tassi & Inflazione (2022)", "code": "RATES_2022", "target_page": "pages/7_🌪️_Stress_Testing.py", "icon": "⚡", "cat": "Macro Stress"},
    {"label": "Scenario: Crisi Debito Sovrano & Spread BTP (2011)", "code": "SOVEREIGN_2011", "target_page": "pages/7_🌪️_Stress_Testing.py", "icon": "🏛️", "cat": "Macro Stress"},
    {"label": "Scenario: Bolla Dot-Com Tech Crash (2000-2002)", "code": "DOTCOM_2000", "target_page": "pages/7_🌪️_Stress_Testing.py", "icon": "💻", "cat": "Macro Stress"},
]


@st.dialog("⚡ ARGUS Command Palette — Quick Action & Navigator", width="large")
def render_command_palette_dialog() -> None:
    """Finestra di comando rapida stile Bloomberg Terminal / Spotlight."""
    st.caption("Cerca tra **tutte le 22 pagine**, strumenti del portafoglio, o applica scenari macro.")
    
    query = st.text_input(
        "Cerca comando, pagina o asset:",
        placeholder="es. Stress, Posizioni, Quadro RW, AAPL, BTP, Lehman...",
        key="cmd_palette_search_query",
        label_visibility="collapsed",
    )

    # Costruzione indice dinamico
    all_items: List[Dict[str, Any]] = []

    # 1. Pagine della suite
    for p in CATALOG_PAGES:
        all_items.append({
            "type": "PAGE",
            "name": p["label"],
            "code": p["file"],
            "icon": p["icon"],
            "category": p["cat"],
            "action": lambda f=p["file"]: switch_to_page(f),
        })

    # 2. Scenari di stress
    for s in CATALOG_SCENARIOS:
        def _apply_scenario(code=s["code"], page=s["target_page"]):
            st.session_state["active_stress_scenario"] = code
            st.session_state["stress_applied_from_palette"] = True
            switch_to_page(page)

        all_items.append({
            "type": "SCENARIO",
            "name": s["label"],
            "code": s["code"],
            "icon": s["icon"],
            "category": s["cat"],
            "action": _apply_scenario,
        })

    # 3. Strumenti del portafoglio attivo (se presenti in session_state)
    active_positions = st.session_state.get("positions_df")
    if active_positions is None:
        port_res = st.session_state.get("portfolio_results", {})
        if isinstance(port_res, dict):
            active_positions = port_res.get("positions")

    if active_positions is not None and hasattr(active_positions, "iterrows"):
        for _, row in active_positions.iterrows():
            ticker = str(row.get("ticker", row.get("symbol", ""))).strip().upper()
            if not ticker:
                continue
            isin = str(row.get("isin", ""))
            name = str(row.get("name", ticker))
            
            def _select_asset(sym=ticker):
                st.session_state["selected_asset"] = sym
                st.session_state["target_subtab_pos_active_tab"] = "📋 Posizioni di Portafoglio"
                switch_to_page("pages/5_📋_Posizioni_e_Dettagli.py")

            all_items.append({
                "type": "ASSET",
                "name": f"{ticker} — {name}",
                "code": isin or ticker,
                "icon": "💼",
                "category": "Portafoglio Attivo",
                "action": _select_asset,
            })

    # Filtro della query
    q_clean = query.strip().lower() if query else ""
    if q_clean:
        filtered = [
            item for item in all_items
            if q_clean in item["name"].lower() or q_clean in item["code"].lower() or q_clean in item["category"].lower()
        ]
    else:
        # Default: mostra le prime 6 pagine + 2 scenari
        filtered = [item for item in all_items if item["type"] == "PAGE"][:6] + [
            item for item in all_items if item["type"] == "SCENARIO"
        ][:2]

    st.markdown(
        f"<div style='font-size: 11px; font-weight: 700; color: #8b949e; text-transform: uppercase; margin-bottom: 8px;'>"
        f"RISULTATI DISPONIBILI ({len(filtered)})</div>",
        unsafe_allow_html=True,
    )

    for idx, item in enumerate(filtered[:10]):
        col_icon, col_info, col_btn = st.columns([1, 8, 2])
        with col_icon:
            st.markdown(f"<div style='font-size: 20px; text-align: center;'>{item['icon']}</div>", unsafe_allow_html=True)
        with col_info:
            st.markdown(f"**{item['name']}**")
            st.caption(f"{item['category']} • `{item['code']}`")
        with col_btn:
            if st.button("Apri ➔", key=f"btn_cmd_nav_{idx}", use_container_width=True, type="secondary"):
                item["action"]()
                st.rerun()

    st.divider()
    c_close, _ = st.columns([2, 8])
    with c_close:
        if st.button("Chiudi [Esc]", use_container_width=True):
            st.rerun()


def inject_command_palette_support(render_button: bool = True) -> None:
    """
    Inietta il listener JS per Ctrl+K e, se richiesto, visualizza il trigger compatto.
    Garantisce pieno supporto sia in ambiente Web standard che WebView2 / Desktop .exe.
    """
    # 1. Ancora invisibile nel DOM principale di Streamlit per geolocalizzare il pulsante
    st.markdown(
        '<div id="argus-cmd-palette-anchor" data-argus-role="cmd-palette-anchor" style="display:none; height:0; width:0;"></div>',
        unsafe_allow_html=True,
    )

    # 2. Iniezione listener JS tramite components.html (altezza 1px per prevenire throttling Chromium/WebView2)
    components.html(HOTKEY_JS_SNIPPET, height=1, width=1)

    # 3. Visualizzazione pulsante trigger se richiesto
    if render_button:
        if st.button("🔍 Quick Command (Ctrl+K)", key="argus_cmd_palette_btn", use_container_width=True):
            render_command_palette_dialog()
