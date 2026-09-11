"""
====================================================================
MODULO: components/splash.py
DESCRIZIONE: Master Institutional Splash Screen & Dual-Portal Gateway for Streamlit
DESIGN SYSTEM: Obsidian Dark Glass / Bento Grid Monolith / 60 FPS Hardware-Accelerated SVG
ARCHITECTURE: 22 Moduli Operativi (12 Risk & Quant + 10 Wealth & Advisory)
STREAMLIT ENGINE: Compatible with Streamlit 1.59+ (stExpandSidebarButton / stSidebarCollapseButton)
====================================================================
"""

from __future__ import annotations

import html
from typing import Callable, List, Optional, Tuple
import streamlit as st


def _clean_html(raw_html: str) -> str:
    """Rimuove l'indentazione iniziale e le righe vuote per impedire a Markdown di interpretare l'HTML come blocco di codice."""
    return "\n".join(line.strip() for line in raw_html.splitlines() if line.strip())


# ── DESIGN SYSTEM & STYLESHEET PERFEZIONATO ─────────────────────────
SPLASH_STYLES = _clean_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Outfit:wght@400;500;600;700;800;900&display=swap');

/* NASCONDI TASSATIVAMENTE HEADER, TOOLBAR E TUTTE LE FRECCETTE DELLA SIDEBAR NELLO SPLASH */
header[data-testid="stHeader"],
[data-testid="stHeader"],
header[data-testid="stHeader"] *,
[data-testid="stToolbar"],
div[data-testid="stToolbar"],
[data-testid="stExpandSidebarButton"],
button[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapseButton"],
section[data-testid="stSidebar"],
[data-testid="stSidebar"],
div[data-testid="collapsedControl"],
[data-testid="collapsedControl"],
button[data-testid="stSidebarCollapsedControl"],
[data-testid="stHeader"] [data-testid="collapsedControl"],
[data-testid="stHeader"] [data-testid="stExpandSidebarButton"],
button[aria-label*="sidebar" i],
button[aria-label*="Sidebar" i],
button[title*="sidebar" i],
button[title*="Sidebar" i] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    width: 0px !important;
    height: 0px !important;
    max-height: 0px !important;
    max-width: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
    pointer-events: none !important;
    position: absolute !important;
    top: -9999px !important;
    left: -9999px !important;
}

/* Contenitore principale a tutto schermo con padding ottico ottimizzato */
.block-container,
div[data-testid="stAppViewBlockContainer"],
.main .block-container,
section.main > div {
    padding-top: 0.1rem !important;
    padding-bottom: 0.8rem !important;
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
    max-width: 1260px !important;
}

/* Master Glassmorphic Wrapper Istituzionale */
.splash-master-wrapper {
    max-width: 1240px;
    margin: 0px auto 14px auto;
    background: radial-gradient(1300px circle at 50% -20%, rgba(245, 158, 11, 0.16) 0%, rgba(15, 23, 42, 0.96) 50%, rgba(5, 8, 15, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.11);
    border-top: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: 24px;
    padding: 22px 30px 18px;
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.88), 0 0 60px rgba(245, 158, 11, 0.10);
    backdrop-filter: blur(28px) saturate(180%);
    -webkit-backdrop-filter: blur(28px) saturate(180%);
    text-align: center;
    position: relative;
    overflow: hidden;
    animation: splashFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes splashFadeIn {
    0% { opacity: 0; transform: translateY(6px) scale(0.99); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}

.splash-logo-container {
    margin-bottom: 4px;
    filter: drop-shadow(0 0 24px rgba(245, 158, 11, 0.38));
    transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.splash-logo-container:hover {
    transform: scale(1.025);
}

.splash-title {
    font-size: 38px;
    font-weight: 900;
    letter-spacing: 12px;
    background: linear-gradient(180deg, #ffffff 20%, #fde68a 60%, #f59e0b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 2px;
    line-height: 1.1;
    text-transform: uppercase;
    font-family: 'Outfit', -apple-system, sans-serif;
    text-shadow: 0 2px 20px rgba(245, 158, 11, 0.25);
}

.splash-subtitle {
    font-size: 11.5px;
    font-weight: 800;
    color: #f59e0b;
    letter-spacing: 3.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
    opacity: 0.95;
    font-family: 'Outfit', -apple-system, sans-serif;
}

.splash-desc {
    font-size: 13.5px;
    color: #94a3b8;
    max-width: 900px;
    margin: 0 auto 12px auto;
    line-height: 1.55;
    font-family: 'Outfit', -apple-system, sans-serif;
}

/* Badge Ribbon Istituzionale (Numeri rigorosi: 22 Moduli = 12 Risk + 10 Wealth) */
.splash-badge-ribbon {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 14px;
}

.splash-pill {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.10);
    padding: 3.5px 12px;
    border-radius: 20px;
    font-size: 11px;
    color: #cbd5e1;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.2px;
    transition: all 0.2s ease;
}
.splash-pill:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: #f59e0b;
    color: #ffffff;
}

/* Bloomberg-Style Telemetry Console */
.terminal-window {
    background: rgba(6, 9, 16, 0.98);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 13px;
    padding: 0;
    text-align: left;
    margin-bottom: 12px;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.7), 0 6px 20px rgba(0,0,0,0.5);
    overflow: hidden;
}

.terminal-header {
    background: rgba(255, 255, 255, 0.035);
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    padding: 7px 15px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.terminal-dots-group {
    display: flex;
    align-items: center;
    gap: 6px;
}
.terminal-dot { width: 8.5px; height: 8.5px; border-radius: 50%; display: inline-block; }
.dot-red { background: #ef4444; box-shadow: 0 0 6px rgba(239, 68, 68, 0.6); }
.dot-yellow { background: #f59e0b; box-shadow: 0 0 6px rgba(245, 158, 11, 0.6); }
.dot-green { background: #10b981; box-shadow: 0 0 6px rgba(16, 185, 129, 0.6); }

.terminal-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    color: #64748b;
    margin-left: 8px;
    letter-spacing: 0.5px;
}

.terminal-status-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 750;
    color: #10b981;
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(16, 185, 129, 0.35);
    padding: 2px 9px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 5px;
}

.terminal-body {
    padding: 10px 18px 8px 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    line-height: 1.7;
}

/* Micro-Progress Bar a Gradiente Liquido */
.splash-progress-track {
    width: 100%;
    height: 4.5px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 999px;
    overflow: hidden;
    margin: 8px 0 2px 0;
    position: relative;
}

.splash-progress-fill {
    height: 100%;
    width: 100%;
    background: linear-gradient(90deg, #6366f1 0%, #f59e0b 50%, #10b981 100%);
    border-radius: 999px;
    box-shadow: 0 0 10px #f59e0b;
    animation: progressPulse 2.5s ease-in-out infinite alternate;
}

@keyframes progressPulse {
    0% { filter: brightness(1) drop-shadow(0 0 3px #f59e0b); }
    100% { filter: brightness(1.25) drop-shadow(0 0 8px #f59e0b); }
}

/* Bento Grid: Schede Monolitiche di Design Superiore */
.portal-card-risk {
    background: radial-gradient(circle at 0% 0%, rgba(245, 158, 11, 0.16) 0%, rgba(15, 23, 42, 0.95) 75%);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-top: 3px solid #f59e0b;
    border-bottom: none;
    border-top-left-radius: 18px;
    border-top-right-radius: 18px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
    padding: 20px 24px 16px 24px;
    min-height: 240px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.portal-card-risk:hover {
    border-color: rgba(245, 158, 11, 0.65);
    box-shadow: 0 16px 40px rgba(245, 158, 11, 0.2), inset 0 1px 0 rgba(255,255,255,0.2);
}

.portal-card-wealth {
    background: radial-gradient(circle at 100% 0%, rgba(16, 185, 129, 0.16) 0%, rgba(15, 23, 42, 0.95) 75%);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-top: 3px solid #10b981;
    border-bottom: none;
    border-top-left-radius: 18px;
    border-top-right-radius: 18px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
    padding: 20px 24px 16px 24px;
    min-height: 240px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.portal-card-wealth:hover {
    border-color: rgba(16, 185, 129, 0.65);
    box-shadow: 0 16px 40px rgba(16, 185, 129, 0.2), inset 0 1px 0 rgba(255,255,255,0.2);
}

.portal-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.portal-card-title {
    font-size: 19px;
    font-weight: 850;
    color: #ffffff;
    font-family: 'Outfit', -apple-system, sans-serif;
    letter-spacing: 0.3px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.portal-badge-risk {
    background: rgba(245, 158, 11, 0.18);
    border: 1px solid rgba(245, 158, 11, 0.45);
    color: #fde68a;
    font-size: 11px;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 8px;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.5px;
}

.portal-badge-wealth {
    background: rgba(16, 185, 129, 0.18);
    border: 1px solid rgba(16, 185, 129, 0.45);
    color: #a7f3d0;
    font-size: 11px;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 8px;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.5px;
}

.portal-feature-list {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 7px;
}

.portal-feature-item {
    font-size: 12.5px;
    color: #cbd5e1;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Outfit', -apple-system, sans-serif;
    line-height: 1.4;
}
.portal-feature-item b {
    color: #f1f5f9;
    font-weight: 700;
}

/* Azzeramento del gap tra card e pulsante CTA per renderli un unico blocco coeso */
div[data-testid="column"]:has(.portal-card-risk) div[data-testid="stButton"],
div[data-testid="column"]:has(.portal-card-wealth) div[data-testid="stButton"] {
    margin-top: -14px !important;
}

/* Pulsante CTA Risk: Oro Istituzionale fuso con la scheda */
div[data-testid="stButton"] button[key="btn_splash_risk"],
div.st-key-btn_splash_risk button {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
    border: 1px solid rgba(245, 158, 11, 0.9) !important;
    border-top: 1px solid rgba(255, 255, 255, 0.3) !important;
    border-top-left-radius: 0px !important;
    border-top-right-radius: 0px !important;
    border-bottom-left-radius: 18px !important;
    border-bottom-right-radius: 18px !important;
    color: #0b0f19 !important;
    font-weight: 900 !important;
    font-size: 14px !important;
    letter-spacing: 1px !important;
    padding: 14px 24px !important;
    box-shadow: 0 8px 24px rgba(245, 158, 11, 0.35) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    text-transform: uppercase !important;
}
div[data-testid="stButton"] button[key="btn_splash_risk"]:hover,
div.st-key-btn_splash_risk button:hover {
    background: linear-gradient(135deg, #fbbf24 0%, #ea580c 100%) !important;
    color: #000000 !important;
    transform: translateY(0px) !important;
    box-shadow: 0 12px 32px rgba(245, 158, 11, 0.55) !important;
}

/* Pulsante CTA Wealth: Smeraldo Istituzionale fuso con la scheda */
div[data-testid="stButton"] button[key="btn_splash_wealth"],
div.st-key-btn_splash_wealth button {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    border: 1px solid rgba(16, 185, 129, 0.9) !important;
    border-top: 1px solid rgba(255, 255, 255, 0.3) !important;
    border-top-left-radius: 0px !important;
    border-top-right-radius: 0px !important;
    border-bottom-left-radius: 18px !important;
    border-bottom-right-radius: 18px !important;
    color: #041f15 !important;
    font-weight: 900 !important;
    font-size: 14px !important;
    letter-spacing: 1px !important;
    padding: 14px 24px !important;
    box-shadow: 0 8px 24px rgba(16, 185, 129, 0.35) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    text-transform: uppercase !important;
}
div[data-testid="stButton"] button[key="btn_splash_wealth"]:hover,
div.st-key-btn_splash_wealth button:hover {
    background: linear-gradient(135deg, #34d399 0%, #047857 100%) !important;
    color: #000000 !important;
    transform: translateY(0px) !important;
    box-shadow: 0 12px 32px rgba(16, 185, 129, 0.55) !important;
}
</style>
""")


# ── JAVASCRIPT HARDWARE OVERRIDE (COMPATIBILE STREAMLIT 1.59+) ───────
def auto_collapse_sidebar() -> None:
    """Collassa e nasconde forzatamente la sidebar e i controlli di espansione (>>)."""
    try:
        import streamlit.components.v1 as components
        components.html("""
        <script>
        (function() {
            try {
                const doc = window.parent.document;
                
                // 1. Collassa la sidebar se aperta
                const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                if (sidebar && sidebar.getAttribute('aria-expanded') === 'true') {
                    const collapseBtn = doc.querySelector('button[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapseButton"] button, button[aria-label*="collapse" i]');
                    if (collapseBtn) collapseBtn.click();
                }
                
                // 2. Nascondi aggressivamente ogni freccetta o controllo header
                const hideAllChevrons = () => {
                    const targets = doc.querySelectorAll('header[data-testid="stHeader"], [data-testid="stExpandSidebarButton"], button[data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"], button[data-testid="stSidebarCollapsedControl"], button[aria-label*="sidebar" i]');
                    targets.forEach(el => {
                        el.style.setProperty('display', 'none', 'important');
                        el.style.setProperty('visibility', 'hidden', 'important');
                        el.style.setProperty('opacity', '0', 'important');
                        el.style.setProperty('width', '0px', 'important');
                        el.style.setProperty('height', '0px', 'important');
                        el.style.setProperty('pointer-events', 'none', 'important');
                    });
                };
                hideAllChevrons();
                
                // 3. MutationObserver per bloccare ricomparse dinamiche di React
                const obs = new MutationObserver(hideAllChevrons);
                obs.observe(doc.body, { childList: true, subtree: true });
                setTimeout(() => obs.disconnect(), 4000);
            } catch (e) {}
        })();
        </script>
        """, height=0, width=0)
    except Exception:
        pass


def auto_expand_sidebar() -> None:
    """Apre automaticamente la sidebar non appena l'utente accede a uno dei due moduli."""
    try:
        import streamlit.components.v1 as components
        components.html("""
        <script>
        function triggerExpand() {
            try {
                const doc = window.parent.document;
                const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                const isCollapsed = !sidebar || sidebar.getAttribute('aria-expanded') === 'false' || sidebar.getBoundingClientRect().width < 80;
                if (isCollapsed) {
                    // Supporto unificato per Streamlit 1.59+ (stExpandSidebarButton) e versioni precedenti (collapsedControl)
                    const btn = doc.querySelector('button[data-testid="stExpandSidebarButton"], [data-testid="stExpandSidebarButton"], button[aria-label*="expand" i], div[data-testid="collapsedControl"] button, [data-testid="stSidebarCollapsedControl"] button, button[data-testid="stSidebarCollapsedControl"]');
                    if (btn) {
                        btn.click();
                    }
                }
            } catch (e) {}
        }
        triggerExpand();
        setTimeout(triggerExpand, 30);
        setTimeout(triggerExpand, 100);
        setTimeout(triggerExpand, 250);
        setTimeout(triggerExpand, 500);
        </script>
        """, height=0, width=0)
    except Exception:
        pass


# ── LOGO VETTORIALE SVG DINAMICO ────────────────────────────────────
def get_argus_vector_logo_svg(size: int = 130, accent_color: str = "#f59e0b") -> str:
    """Genera l'Occhio di Argus vettoriale con reticoli concentrici, mirino quantitativo e fascio laser."""
    return _clean_html(f"""
    <svg width="{size}" height="{size}" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" class="splash-logo-svg" style="display:block;margin:auto;filter:drop-shadow(0 0 18px rgba(245, 158, 11, 0.45));">
        <defs>
            <radialGradient id="argusIrisGrad" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95"/>
                <stop offset="35%" stop-color="{accent_color}" stop-opacity="0.9"/>
                <stop offset="70%" stop-color="#b45309" stop-opacity="0.6"/>
                <stop offset="100%" stop-color="#070a12" stop-opacity="0.95"/>
            </radialGradient>
            <filter id="argusGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <linearGradient id="orbitalGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{accent_color}" stop-opacity="0.8"/>
                <stop offset="50%" stop-color="#38bdf8" stop-opacity="0.2"/>
                <stop offset="100%" stop-color="{accent_color}" stop-opacity="0.8"/>
            </linearGradient>
        </defs>

        <circle cx="100" cy="100" r="88" fill="none" stroke="url(#orbitalGrad)" stroke-width="1.2" stroke-dasharray="4 8" opacity="0.65"/>
        <circle cx="100" cy="100" r="74" fill="none" stroke="{accent_color}" stroke-width="0.8" opacity="0.35"/>

        <path d="M 22 100 Q 100 32 178 100 Q 100 168 22 100 Z" fill="rgba(15, 23, 42, 0.75)" stroke="{accent_color}" stroke-width="2.5" filter="url(#argusGlow)" />
        <path d="M 38 100 Q 100 48 162 100 Q 100 152 38 100 Z" fill="none" stroke="rgba(255, 255, 255, 0.25)" stroke-width="1" stroke-dasharray="2 4" />

        <circle cx="100" cy="100" r="32" fill="url(#argusIrisGrad)" stroke="{accent_color}" stroke-width="2"/>
        <circle cx="100" cy="100" r="14" fill="#070a12" stroke="#ffffff" stroke-width="1.5"/>
        <circle cx="95" cy="95" r="4.5" fill="#ffffff" opacity="0.95"/>

        <line x1="100" y1="18" x2="100" y2="34" stroke="{accent_color}" stroke-width="2" opacity="0.8"/>
        <line x1="100" y1="166" x2="100" y2="182" stroke="{accent_color}" stroke-width="2" opacity="0.8"/>
        <line x1="18" y1="100" x2="34" y2="100" stroke="{accent_color}" stroke-width="2" opacity="0.8"/>
        <line x1="166" y1="100" x2="182" y2="100" stroke="{accent_color}" stroke-width="2" opacity="0.8"/>
    </svg>
    """)


# ── RENDERIZZAZIONE DEL CONTENUTO HTML ───────────────────────────────
def render_splash_html(
    app_title: str = "A R G U S",
    subtitle: str = "QUANTITATIVE RISK ANALYTICS & WEALTH INTELLIGENCE ECOSYSTEM",
    version_tag: str = "v9.0.0 Institutional",
    current_status: str = "Kernel operativo. Seleziona l'Ambiente di Lavoro sottostante:",
    progress_pct: int = 100,
    accent_color: str = "#f59e0b",
    is_fading_out: bool = False,
    show_skip: bool = False,
) -> str:
    """Costruisce il layout completo dello splash screen con logo, badge ribbon e console telemetrica."""
    logo_svg = get_argus_vector_logo_svg(size=125, accent_color=accent_color)
    status_text = current_status if current_status else "Caricamento moduli operativi..."
    fade_class = " splash-fade-out" if is_fading_out else ""
    skip_html = '<div style="margin-top: 6px; font-size: 11px; color: #64748b;">⚡ Salta introduzione &bull; Premi uno dei due portali per accedere subito</div>' if show_skip else ""

    return _clean_html(f"""
    <div id="argus-splash-root" class="splash-master-wrapper{fade_class}">
        <div class="splash-logo-container">
            {logo_svg}
        </div>
        <div class="splash-title">{html.escape(app_title)}</div>
        <div class="splash-subtitle">{html.escape(subtitle)}</div>
        <div class="splash-desc">
            Piattaforma quantitativa multi-asset per analisi econometrica del rischio, stress testing sistemico, ottimizzazione di frontiera e consolidamento patrimoniale olistico.
        </div>
        
        <div class="splash-badge-ribbon">
            <span class="splash-pill">🟢 <b>{html.escape(version_tag)}</b></span>
            <span class="splash-pill">⚡ <b>22 Moduli Attivi</b> (12 Risk + 10 Wealth)</span>
            <span class="splash-pill">🔒 <b>Zero-Cloud Leak</b> Crittografia Locale</span>
            <span class="splash-pill">🗄️ <b>DuckDB SIMD &amp; SQLite</b> Vectorized OLAP</span>
        </div>

        <div class="terminal-window">
            <div class="terminal-header">
                <div class="terminal-dots-group">
                    <span class="terminal-dot dot-red"></span>
                    <span class="terminal-dot dot-yellow"></span>
                    <span class="terminal-dot dot-green"></span>
                    <span class="terminal-title">argus-kernel@localhost:8501 --cluster dual-pipeline --runtime production</span>
                </div>
                <div class="terminal-status-badge">
                    <span>●</span> 100% OPERATIONAL
                </div>
            </div>
            <div class="terminal-body">
                <div style="color: #34d399;"><span style="color: #64748b;">[01/03]</span> <b>RISK SUITE (12 Moduli):</b> Dual Ingestion (Stocks &amp; Crypto) &bull; VaR/CVaR, Copula, Markowitz QP &amp; BQuant IDE</div>
                <div style="color: #38bdf8;"><span style="color: #64748b;">[02/03]</span> <b>WEALTH SUITE (10 Moduli):</b> Multi-Account Ledger &bull; 50/30/20, Real Estate, Orologi, Quadro RW &amp; AI Copilot</div>
                <div style="color: #a78bfa;"><span style="color: #64748b;">[03/03]</span> <b>STORAGE FABRIC:</b> DuckDB In-Memory SIMD Columnar Engine &bull; SQLite ACID Ledger Synchronized</div>
                <div style="color: #fbbf24; font-weight: 700; margin-top: 3px;"><span style="color: #f59e0b;">[⚡]</span> <b>STATUS ({progress_pct}%):</b> {html.escape(status_text)}</div>
                
                <div class="splash-progress-track">
                    <div class="splash-progress-fill" style="width: {progress_pct}%;"></div>
                </div>
                {skip_html}
            </div>
        </div>
    </div>
    """)


# ── CONTROLLO CICLO DI VITA & RENDERING PRINCIPALE ─────────────────
def render_splash_screen(
    app_version: str = "9.0.0",
    force_show: bool = False,
    boot_tasks: Optional[List[Tuple[str, Optional[Callable[[], None]]]]] = None,
    min_step_duration: float = 0.32,
) -> bool:
    """
    Renderizza lo Splash Screen & Bootloader Istituzionale di ARGUS all'avvio.
    
    Restituisce True se lo splash e' attivo (bloccando l'esecuzione sottostante con st.stop()).
    Restituisce False se lo splash e' completato/bypassato (permettendo il caricamento immediato della dashboard).
    """
    # Se splash_dismissed e' esplicitamente False (es. click su 'Schermata di Avvio' nella sidebar)
    if st.session_state.get("splash_dismissed") is False:
        force_show = True

    # Bypass istantaneo se gia inizializzato e non forzato
    if st.session_state.get("_app_initialized", False) and not force_show:
        return False

    # Controllo query parameters per bypass esplicito / skip
    query_params = getattr(st, "query_params", None)
    if query_params is not None and "skip_splash" in query_params:
        st.session_state["_app_initialized"] = True
        st.session_state["splash_dismissed"] = True
        st.session_state["splash_completed"] = True
        return False

    # Assicura che all'avvio la sidebar rimanga chiusa e le freccette nascoste
    auto_collapse_sidebar()

    # Iniezione stili CSS isolati (inclusa la rimozione totale dell'header e delle freccette)
    st.markdown(SPLASH_STYLES, unsafe_allow_html=True)

    # Frame HTML istituzionale completo
    html_frame = render_splash_html(
        app_title="A R G U S",
        subtitle="QUANTITATIVE RISK ANALYTICS & WEALTH INTELLIGENCE ECOSYSTEM",
        version_tag=f"v{app_version} Institutional",
        current_status="Kernel operativo. Seleziona l'Ambiente di Lavoro sottostante:",
        progress_pct=100,
        accent_color="#f59e0b",
        is_fading_out=False,
        show_skip=False,
    )
    st.markdown(html_frame, unsafe_allow_html=True)

    # Schede Bento Grid e Pulsanti di Accesso Istituzionale Fusi Insieme
    col_risk, col_wealth = st.columns(2)
    with col_risk:
        risk_card_html = _clean_html("""
        <div class="portal-card-risk">
            <div>
                <div class="portal-card-header">
                    <span class="portal-card-title">📊 Risk Analytics &amp; Portfolios</span>
                    <span class="portal-badge-risk">12 MODULI RISK &amp; QUANT</span>
                </div>
                <div style="font-size: 12.5px; color: #94a3b8; line-height: 1.5; margin-bottom: 10px;">
                    Desk quantitativo istituzionale per asset pricing, stress testing sistemico e ottimizzazione di frontiera.
                </div>
                <div class="portal-feature-list">
                    <div class="portal-feature-item"><span>📉</span> <span><b>Metriche di Coda:</b> VaR Storico/Parametrico (95/99%), CVaR &amp; Deviazione EWMA</span></div>
                    <div class="portal-feature-item"><span>🌪️</span> <span><b>Stress Testing Sistemico:</b> Scenari Crisi 2008, Shock Tassi, Crolli Tech &amp; Tariffe</span></div>
                    <div class="portal-feature-item"><span>🔬</span> <span><b>Asset Allocation QP:</b> Markowitz, Black-Litterman, HRP &amp; Copule Matematiche</span></div>
                    <div class="portal-feature-item"><span>💻</span> <span><b>Screener &amp; BQuant:</b> Multi-Factor Equity Screener + Sandbox Python Integrata</span></div>
                </div>
            </div>
        </div>
        """)
        st.markdown(risk_card_html, unsafe_allow_html=True)
        if st.button("🚀 ENTRA NEL DESK RISK ANALYTICS →", key="btn_splash_risk", use_container_width=True):
            st.session_state["_app_initialized"] = True
            st.session_state["splash_dismissed"] = True
            st.session_state["splash_completed"] = True
            st.session_state["argus_portal_mode"] = "📊 Risk Analytics"
            st.rerun()

    with col_wealth:
        wealth_card_html = _clean_html("""
        <div class="portal-card-wealth">
            <div>
                <div class="portal-card-header">
                    <span class="portal-card-title">🏛️ Wealth Management &amp; Advisory</span>
                    <span class="portal-badge-wealth">10 MODULI WEALTH &amp; ADVISORY</span>
                </div>
                <div style="font-size: 12.5px; color: #94a3b8; line-height: 1.5; margin-bottom: 10px;">
                    Piattaforma di consolidamento olistico del patrimonio netto, budget familiare, caveau beni rifugio e fiscalità.
                </div>
                <div class="portal-feature-list">
                    <div class="portal-feature-item"><span>🏛️</span> <span><b>Net Worth Olistico:</b> Conti Correnti, Broker, Immobili, Mutui &amp; Caveau Orologi</span></div>
                    <div class="portal-feature-item"><span>💳</span> <span><b>Cash Flow &amp; Budgeting:</b> Framework 50/30/20, Burn Rate &amp; Proiezioni FIRE</span></div>
                    <div class="portal-feature-item"><span>📑</span> <span><b>Fisco &amp; Previdenza:</b> Monitoraggio Quadro RW (IVAFE/IVIE) &amp; Fondo Pensione</span></div>
                    <div class="portal-feature-item"><span>🤖</span> <span><b>AI Advisory Copilot:</b> Audit patrimoniale avanzato con motore quantitativo locale</span></div>
                </div>
            </div>
        </div>
        """)
        st.markdown(wealth_card_html, unsafe_allow_html=True)
        if st.button("💎 ENTRA NELLA SUITE WEALTH ADVISORY →", key="btn_splash_wealth", use_container_width=True):
            st.session_state["_app_initialized"] = True
            st.session_state["splash_dismissed"] = True
            st.session_state["splash_completed"] = True
            st.session_state["argus_portal_mode"] = "🏛️ Wealth Management"
            st.switch_page("pages/12_🎛️_Wealth_Control_Room.py")

    return True


# Alias di retrocompatibilita
show_splash_screen = render_splash_screen
