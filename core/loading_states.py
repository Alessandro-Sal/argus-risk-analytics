"""
ARGUS — UI Lifecycle, Loading & Transition States Architecture
==============================================================
Institutional Shimmer Skeleton Loaders, Glassmorphic Transition Overlays,
Atomic "Clear -> Compute -> Mount" View Slots, and Concurrency Locking (Debounce & Double-Click Guard).

Author: Senior Frontend Architect & UX Engineer
Platform: ARGUS Quantitative Risk & Wealth Ecosystem
"""

from __future__ import annotations

import functools
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("argus.loading_states")

# ── 1. CSS & VISUAL DESIGN ENGINE ───────────────────────────────────

LOADING_SHIMMER_CSS = """
<style>
/* ===================================================================
   ARGUS SKELETON SHIMMER & TRANSITION OVERLAY ENGINE (60 FPS GPU)
   =================================================================== */

@keyframes argusShimmer {
    0% {
        background-position: -200% 0;
    }
    100% {
        background-position: 200% 0;
    }
}

@keyframes argusSpin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes argusPulseGlow {
    0%, 100% { opacity: 0.85; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.02); }
}

@keyframes argusFadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Base Skeleton Block */
.argus-skeleton {
    background: linear-gradient(
        90deg,
        rgba(255, 255, 255, 0.03) 20%,
        rgba(255, 255, 255, 0.11) 50%,
        rgba(255, 255, 255, 0.03) 80%
    ) !important;
    background-size: 200% 100% !important;
    animation: argusShimmer 1.8s cubic-bezier(0.4, 0, 0.2, 1) infinite !important;
    border-radius: 6px !important;
    display: inline-block;
}

/* Skeleton Card Container */
.argus-skeleton-card {
    background: rgba(15, 23, 42, 0.65) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    padding: 16px 18px !important;
    margin-bottom: 14px !important;
    backdrop-filter: blur(8px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    animation: argusFadeIn 0.2s ease-out;
}

.argus-skeleton-line {
    height: 14px;
    border-radius: 4px;
    margin-bottom: 8px;
}

.argus-skeleton-title {
    width: 48%;
    height: 12px;
    margin-bottom: 12px;
}

.argus-skeleton-value {
    width: 75%;
    height: 28px;
    margin-bottom: 10px;
}

.argus-skeleton-delta {
    width: 38%;
    height: 14px;
    border-radius: 12px;
}

/* Full-Viewport Transition Overlay */
.argus-transition-overlay {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    background: radial-gradient(circle at 50% 45%, rgba(15, 23, 42, 0.94) 0%, rgba(6, 9, 16, 0.98) 100%) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    z-index: 9999999 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    pointer-events: all !important;
    animation: argusFadeIn 0.15s ease-out;
}

.argus-overlay-panel {
    background: rgba(22, 27, 34, 0.92) !important;
    border: 1px solid rgba(245, 158, 11, 0.35) !important;
    border-radius: 14px !important;
    padding: 34px 44px !important;
    text-align: center !important;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.75), 0 0 35px rgba(245, 158, 11, 0.15) !important;
    max-width: 500px !important;
    animation: argusPulseGlow 3s ease-in-out infinite !important;
}

.argus-quantum-spinner {
    width: 46px;
    height: 46px;
    border: 3.5px solid rgba(245, 158, 11, 0.18);
    border-top: 3.5px solid #f59e0b;
    border-right: 3.5px solid rgba(16, 185, 129, 0.8);
    border-radius: 50%;
    animation: argusSpin 0.75s linear infinite;
    margin: 0 auto 18px auto;
}

.argus-overlay-title {
    font-family: 'Outfit', -apple-system, sans-serif !important;
    font-size: 19px !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    letter-spacing: 1px !important;
    margin-bottom: 6px !important;
    text-transform: uppercase !important;
}

.argus-overlay-subtitle {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    color: #94a3b8 !important;
    line-height: 1.4 !important;
}
</style>
"""


def _clean_html(raw_html: str) -> str:
    """Rimuove l'indentazione iniziale e le righe vuote per impedire a Markdown di interpretare l'HTML come blocco di codice."""
    return "\n".join(line.strip() for line in raw_html.splitlines() if line.strip())


def inject_loading_css() -> None:
    """Inietta una sola volta nella sessione corrente il foglio di stile per skeleton loader e overlay."""
    try:
        import streamlit as st
        if "_argus_loading_css_injected" not in st.session_state:
            st.markdown(_clean_html(LOADING_SHIMMER_CSS), unsafe_allow_html=True)
            st.session_state["_argus_loading_css_injected"] = True
    except Exception:
        pass


# ── 2. CONCURRENCY GUARD & DEBOUNCING (DOUBLE-CLICK PREVENTION) ────

def _get_session_state() -> Optional[Any]:
    try:
        import streamlit as st
        return getattr(st, "session_state", None)
    except Exception:
        return None


def is_computing(key: Optional[str] = None) -> bool:
    """
    Restituisce True se è in corso un'elaborazione (a livello globale o per una chiave specifica).
    Utilizzato dai widget Streamlit (es. st.button(..., disabled=is_computing())) per
    disabilitare l'input durante il caricamento.
    """
    st_state = _get_session_state()
    if st_state is None:
        return False
    if key:
        return bool(st_state.get(f"_is_computing_{key}", False))
    return bool(st_state.get("_global_is_computing", False))


def set_computing_state(key: str, active: bool) -> None:
    """Imposta o rimuove il flag di computazione attiva per prevenire concorrenza e click multipli."""
    st_state = _get_session_state()
    if st_state is None:
        return
    st_state[f"_is_computing_{key}"] = active
    if active:
        st_state["_global_is_computing"] = True
    else:
        # Se nessun altro calcolo è in corso, sblocca il flag globale
        any_computing = any(
            k.startswith("_is_computing_") and st_state[k]
            for k in list(st_state.keys())
            if k != f"_is_computing_{key}"
        )
        st_state["_global_is_computing"] = any_computing


def debounce_trigger(key: str, cooldown_seconds: float = 1.0) -> bool:
    """
    Protegge da click multipli o accidentali (spam debounce).
    Restituisce True se l'azione è consentita; False se il click è avvenuto
    entro la finestra di cooldown dall'ultimo trigger.
    """
    st_state = _get_session_state()
    if st_state is None:
        return True

    now = time.time()
    ts_key = f"_last_trigger_ts_{key}"
    last_ts = float(st_state.get(ts_key, 0.0))

    if (now - last_ts) < cooldown_seconds:
        logger.debug(
            "Debounce guard suppressed rapid click for key '%s' (delta=%.3fs < %.1fs)",
            key,
            now - last_ts,
            cooldown_seconds,
        )
        return False

    st_state[ts_key] = now
    return True


# ── 3. SKELETON LOADERS (PULSING SHIMMER SIGHT-MASKS) ───────────────

def render_kpi_skeleton(count: int = 4) -> None:
    """Renderizza una riga responsive di KPI card segnaposto con gradiente shimmer pulsante."""
    inject_loading_css()
    try:
        import streamlit as st
        cols = st.columns(count)
        html_card = _clean_html("""
        <div class="argus-skeleton-card">
            <div class="argus-skeleton argus-skeleton-line argus-skeleton-title"></div>
            <div class="argus-skeleton argus-skeleton-line argus-skeleton-value"></div>
            <div class="argus-skeleton argus-skeleton-line argus-skeleton-delta"></div>
        </div>
        """)
        for col in cols:
            with col:
                st.markdown(html_card, unsafe_allow_html=True)
    except Exception:
        pass


def render_table_skeleton(rows: int = 5, cols: int = 4) -> None:
    """Renderizza una tabella istituzionale segnaposto con shimmer animato."""
    inject_loading_css()
    try:
        import streamlit as st
        header_cells = "".join("<div class='argus-skeleton' style='flex:1; height:18px; margin:4px;'></div>" for _ in range(cols))
        row_cells = "".join(
            "<div style='display:flex; gap:12px; margin-bottom:8px;'>"
            + "".join("<div class='argus-skeleton' style='flex:1; height:14px;'></div>" for _ in range(cols))
            + "</div>"
            for _ in range(rows)
        )
        table_html = _clean_html(f"""
        <div class="argus-skeleton-card" style="padding: 14px;">
            <div style="display:flex; gap:12px; margin-bottom:14px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px;">
                {header_cells}
            </div>
            {row_cells}
        </div>
        """)
        st.markdown(table_html, unsafe_allow_html=True)
    except Exception:
        pass


def render_chart_skeleton(height: int = 340, title: str = "Caricamento Grafico...") -> None:
    """Renderizza un mockup segnaposto per grafici Plotly con assi, griglia e barre pulsanti."""
    inject_loading_css()
    try:
        import streamlit as st
        chart_html = _clean_html(f"""
        <div class="argus-skeleton-card" style="height:{height}px; display:flex; flex-direction:column; justify-content:space-between;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div class="argus-skeleton" style="width:28%; height:16px;"></div>
                <div class="argus-skeleton" style="width:14%; height:14px;"></div>
            </div>
            <div style="display:flex; align-items:flex-end; gap:10px; height:{height - 90}px; padding: 12px 0;">
                <div class="argus-skeleton" style="flex:1; height:35%;"></div>
                <div class="argus-skeleton" style="flex:1; height:65%;"></div>
                <div class="argus-skeleton" style="flex:1; height:45%;"></div>
                <div class="argus-skeleton" style="flex:1; height:85%;"></div>
                <div class="argus-skeleton" style="flex:1; height:40%;"></div>
                <div class="argus-skeleton" style="flex:1; height:75%;"></div>
                <div class="argus-skeleton" style="flex:1; height:90%;"></div>
                <div class="argus-skeleton" style="flex:1; height:55%;"></div>
            </div>
            <div class="argus-skeleton" style="width:100%; height:12px;"></div>
        </div>
        """)
        st.markdown(chart_html, unsafe_allow_html=True)
    except Exception:
        pass


def render_dashboard_skeleton() -> None:
    """Renderizza l'intero mockup segnaposto di una dashboard (KPI + 2 Chart + Tabella)."""
    render_kpi_skeleton(count=4)
    try:
        import streamlit as st
        c1, c2 = st.columns(2)
        with c1:
            render_chart_skeleton(height=320)
        with c2:
            render_chart_skeleton(height=320)
        render_table_skeleton(rows=4, cols=4)
    except Exception:
        pass


# ── 4. TRANSITION OVERLAYS & PAGE MASKS ────────────────────────────

def render_transition_overlay(
    title: str = "Caricamento in corso...",
    subtitle: str = "Elaborazione modelli e metriche quantitative...",
) -> None:
    """
    Monta istantaneamente un overlay a schermo intero con glassmorphic blur,
    mascherando i pixel della schermata precedente prima che inizi il ricalcolo.
    """
    inject_loading_css()
    try:
        import streamlit as st
        overlay_html = _clean_html(f"""
        <div class="argus-transition-overlay">
            <div class="argus-overlay-panel">
                <div class="argus-quantum-spinner"></div>
                <div class="argus-overlay-title">{title}</div>
                <div class="argus-overlay-subtitle">{subtitle}</div>
            </div>
        </div>
        """)
        st.markdown(overlay_html, unsafe_allow_html=True)
    except Exception:
        pass


# ── 5. ATOMIC VIEW SLOT (SVUOTA -> CALCOLA -> MOSTRA) ──────────────

class AtomicViewSlot:
    """
    Gestore di container atomico basato su `st.empty()`.
    Separa rigorosamente il ciclo di vita in 3 fasi:
    1. Fase 1: Svuotamento esplicito del contenitore (.empty()) e montaggio immediato dello skeleton.
    2. Fase 2: Esecuzione del calcolo pesante / fetch dati (senza render parziali a video).
    3. Fase 3: Render atomico dei componenti definitivi completati nel contenitore pulito.
    """

    def __init__(self, key: str = "default_slot"):
        self.key = key
        import streamlit as st
        self._placeholder = st.empty()

    def clear(self) -> None:
        """Svuota immediatamente qualsiasi contenuto visivo renderizzato nel container."""
        self._placeholder.empty()

    def mount_skeleton(self, skeleton_type: str = "dashboard", **kwargs: Any) -> None:
        """Svuota il container e monta lo skeleton desiderato (kpi, chart, table, dashboard)."""
        self.clear()
        with self._placeholder.container():
            if skeleton_type == "kpi":
                render_kpi_skeleton(count=kwargs.get("count", 4))
            elif skeleton_type == "chart":
                render_chart_skeleton(height=kwargs.get("height", 340))
            elif skeleton_type == "table":
                render_table_skeleton(rows=kwargs.get("rows", 5), cols=kwargs.get("cols", 4))
            else:
                render_dashboard_skeleton()

    def render(self, render_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Svuota lo skeleton e renderizza atomisticamente il contenuto reale definitivo."""
        self.clear()
        with self._placeholder.container():
            return render_func(*args, **kwargs)


# ── 6. CONTEXT MANAGER & DECORATOR PER CALCOLI PESANTI ─────────────

@contextmanager
def computation_barrier(
    key: str,
    label: str = "Elaborazione in corso...",
    container: Optional[Any] = None,
    skeleton_type: Optional[str] = None,
    show_overlay: bool = False,
):
    """
    Context manager per incapsulare calcoli pesanti:
    - Imposta il flag `is_computing` per disabilitare controlli e bloccare click multipli.
    - Se specificato un container, ne esegue il flush immediato (.empty()) e vi monta uno skeleton.
    - Se show_overlay è True, monta l'overlay a schermo intero.
    - Garantisce il rilascio del lock e la pulizia dello skeleton al termine (blocco finally).

    Esempio:
        with computation_barrier("markowitz_opt", label="Ottimizzazione Frontiera...", container=main_slot, skeleton_type="chart"):
            res = heavy_opt_calc()
        main_slot.render(render_markowitz_chart, res)
    """
    set_computing_state(key, True)
    if container is not None:
        try:
            container.empty()
            if skeleton_type:
                with container.container():
                    if skeleton_type == "kpi":
                        render_kpi_skeleton()
                    elif skeleton_type == "chart":
                        render_chart_skeleton()
                    elif skeleton_type == "table":
                        render_table_skeleton()
                    else:
                        render_dashboard_skeleton()
        except Exception:
            pass

    if show_overlay:
        render_transition_overlay(title="Elaborazione Quantitativa", subtitle=label)

    try:
        import streamlit as st
        with st.spinner(label):
            yield
    finally:
        set_computing_state(key, False)
        if container is not None:
            try:
                container.empty()
            except Exception:
                pass


def atomic_computation(key: str, label: str = "Elaborazione in corso...", show_overlay: bool = False):
    """
    Decoratore per funzioni di calcolo analitico o fetch dati.
    Applica automaticamente la barriera di calcolo atomica e il blocco di concorrenza.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with computation_barrier(key=key, label=label, show_overlay=show_overlay):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# ── 7. TRANSIZIONE NAVIGAZIONE FLUIDA CON LOADING SCREEN ───────────

def switch_to_page_with_transition(
    target_page_file: str,
    title: str = "Caricamento Schermata...",
    subtitle: str = "Inizializzazione vista e modelli analitici...",
) -> None:
    """
    Esegue la transizione fluida verso una nuova schermata:
    1. Maschera immediatamente i pixel della vecchia pagina con l'overlay istituzionale.
    2. Invoca il teardown atomico preventivo dello stato precedente.
    3. Esegue lo switch effettivo tramite st.switch_page().
    """
    # 1. Overlay di transizione istantaneo
    render_transition_overlay(title=title, subtitle=subtitle)

    # 2. Teardown preventivo dello stato di vista
    try:
        from core.ui_lifecycle import teardown_view_state
        teardown_view_state(target_page=target_page_file)
    except Exception:
        pass

    # 3. Navigazione Streamlit canonica
    from core.sidebar import switch_to_page
    switch_to_page(target_page_file)
