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

/* Scudo di Caricamento Pulito e Immediato al Click */
#argus-loading-shield {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    background: radial-gradient(circle at 50% 40%, rgba(15, 23, 42, 0.98) 0%, rgba(6, 9, 16, 1) 100%) !important;
    z-index: 9999999 !important;
    display: none;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    opacity: 0;
    transition: opacity 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    pointer-events: all !important;
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
}
.shield-spinner {
    width: 44px;
    height: 44px;
    border: 3px solid rgba(245, 158, 11, 0.15);
    border-top: 3px solid #f59e0b;
    border-radius: 50%;
    animation: shieldSpin 0.75s linear infinite;
    margin: 18px auto 14px auto;
}
@keyframes shieldSpin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.shield-title {
    font-family: 'Outfit', -apple-system, sans-serif;
    font-size: 19px;
    font-weight: 850;
    letter-spacing: 2px;
    color: #ffffff;
    text-transform: uppercase;
    margin-bottom: 6px;
    text-shadow: 0 0 20px rgba(245, 158, 11, 0.4);
}
.shield-subtext {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    color: #94a3b8;
    letter-spacing: 0.5px;
}

/* Sfondo con illuminazione d'atmosfera Dual Horizon */
.splash-ambient-glow {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 0;
    background:
        radial-gradient(900px circle at 15% 45%, rgba(245, 158, 11, 0.08) 0%, transparent 65%),
        radial-gradient(900px circle at 85% 45%, rgba(16, 185, 129, 0.08) 0%, transparent 65%),
        radial-gradient(1200px circle at 50% -10%, rgba(99, 102, 241, 0.06) 0%, transparent 60%);
}

/* Centratura ottica totale nel viewport: posiziona lo splash al centro perfetto dello schermo */
.block-container,
div[data-testid="stAppViewBlockContainer"],
.main .block-container,
section.main > div {
    padding-top: 0.8rem !important;
    padding-bottom: 0.8rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 1240px !important;
    min-height: 94vh !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
}

/* Sfondo ad ambient-glow dual horizon dietro la schermata con respiro cinematico */
@keyframes ambientGlowPulse {
    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.13; }
    50% { transform: translate(-50%, -50%) scale(1.04); opacity: 0.18; }
}
.splash-ambient-glow {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 1100px;
    height: 580px;
    background: radial-gradient(circle at 22% 45%, #f59e0b 0%, transparent 55%),
                radial-gradient(circle at 78% 45%, #10b981 0%, transparent 55%);
    pointer-events: none;
    z-index: 0;
    filter: blur(65px);
    animation: ambientGlowPulse 8s ease-in-out infinite;
}

/* Master Double-Bezel (Doppelrand) Architecture: Involucro Macchina Istituzionale */
.splash-master-wrapper {
    max-width: 1200px;
    width: 100%;
    margin: 0px auto 14px auto;
    padding: 5px;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 26px;
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.8), 0 0 40px rgba(245, 158, 11, 0.04);
    backdrop-filter: blur(32px) saturate(180%);
    -webkit-backdrop-filter: blur(32px) saturate(180%);
    position: relative;
    overflow: hidden;
    animation: splashFadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.splash-inner-core {
    border-radius: 21px;
    background: radial-gradient(1200px circle at 50% -10%, rgba(26, 36, 54, 0.85) 0%, rgba(13, 19, 32, 0.95) 55%, rgba(6, 9, 16, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.06);
    padding: 20px 28px 16px;
    box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.12);
    text-align: center;
}

@keyframes splashFadeIn {
    0% { opacity: 0; transform: translateY(6px) scale(0.99); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}

.splash-logo-container {
    margin-bottom: 3px;
    filter: drop-shadow(0 0 22px rgba(245, 158, 11, 0.42));
    transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.splash-logo-container:hover {
    transform: scale(1.025);
}

.splash-title {
    font-size: 32px;
    font-weight: 900;
    letter-spacing: 12px;
    background: linear-gradient(180deg, #ffffff 25%, #fde68a 68%, #f59e0b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 2px;
    line-height: 1.15;
    text-transform: uppercase;
    font-family: 'Outfit', -apple-system, sans-serif;
    text-shadow: 0 2px 24px rgba(245, 158, 11, 0.28);
}

.splash-subtitle {
    font-size: 11px;
    font-weight: 800;
    color: #f59e0b;
    letter-spacing: 3.5px;
    text-transform: uppercase;
    margin-bottom: 7px;
    opacity: 0.95;
    font-family: 'Outfit', -apple-system, sans-serif;
}

.splash-desc {
    font-size: 12.5px;
    color: #94a3b8;
    max-width: 860px;
    margin: 0 auto 9px auto;
    line-height: 1.5;
    font-family: 'Outfit', -apple-system, sans-serif;
}

/* Badge Ribbon Istituzionale (Numeri rigorosi: 22 Moduli = 12 Risk + 10 Wealth) */
.splash-badge-ribbon {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}

.splash-pill {
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(255, 255, 255, 0.09);
    padding: 3.5px 12px;
    border-radius: 20px;
    font-size: 11px;
    color: #cbd5e1;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.3px;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}
.splash-pill:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(245, 158, 11, 0.55);
    color: #ffffff;
    box-shadow: 0 0 12px rgba(245, 158, 11, 0.2);
}

/* Hardware Telemetry Rail Istituzionale Bloomberg-Grade */
@keyframes ledPulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(0.85); }
}
.telemetry-bar {
    background: rgba(4, 7, 14, 0.94);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 7px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 4px;
    box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.7), 0 4px 16px rgba(0, 0, 0, 0.4);
}
.telemetry-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    color: #cbd5e1;
}
.telemetry-label {
    color: #64748b;
    font-weight: 500;
}
.telemetry-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    display: inline-block;
    animation: ledPulse 2.4s ease-in-out infinite;
}
.dot-green { background: #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.85); }
.dot-amber { background: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.85); }
.dot-cyan { background: #00f3ff; box-shadow: 0 0 8px rgba(0, 243, 255, 0.85); }
.dot-purple { background: #a855f7; box-shadow: 0 0 8px rgba(168, 85, 247, 0.85); }
.telemetry-status-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 800;
    color: #10b981;
    background: rgba(16, 185, 129, 0.14);
    border: 1px solid rgba(16, 185, 129, 0.4);
    padding: 2.5px 10px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 5px;
    letter-spacing: 0.5px;
}

/* Allineamento larghezza blocco card a due colonne */
div[data-testid="stHorizontalBlock"]:has(.portal-card-risk) {
    max-width: 1200px !important;
    margin: 0 auto !important;
    gap: 16px !important;
}

/* Bento Grid: Schede Monolitiche di Design Superiore */
.portal-card-risk {
    background: radial-gradient(circle at 0% 0%, rgba(245, 158, 11, 0.15) 0%, rgba(13, 19, 33, 0.95) 75%);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-top: 3px solid #f59e0b;
    border-bottom: none;
    border-top-left-radius: 22px;
    border-top-right-radius: 22px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
    padding: 20px 24px 14px 24px;
    min-height: 205px;
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.portal-card-risk:hover {
    border-color: rgba(245, 158, 11, 0.7);
    box-shadow: 0 18px 44px rgba(245, 158, 11, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.portal-card-wealth {
    background: radial-gradient(circle at 100% 0%, rgba(16, 185, 129, 0.15) 0%, rgba(13, 19, 33, 0.95) 75%);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-top: 3px solid #10b981;
    border-bottom: none;
    border-top-left-radius: 22px;
    border-top-right-radius: 22px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
    padding: 20px 24px 14px 24px;
    min-height: 205px;
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.portal-card-wealth:hover {
    border-color: rgba(16, 185, 129, 0.7);
    box-shadow: 0 18px 44px rgba(16, 185, 129, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.portal-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.portal-card-title {
    font-size: 17.5px;
    font-weight: 850;
    color: #ffffff;
    font-family: 'Outfit', -apple-system, sans-serif;
    letter-spacing: 0.3px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.portal-badge-risk {
    background: rgba(245, 158, 11, 0.16);
    border: 1px solid rgba(245, 158, 11, 0.55);
    color: #fde68a;
    font-size: 10px;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 9999px;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.8px;
    box-shadow: 0 0 10px rgba(245, 158, 11, 0.15);
}

.portal-badge-wealth {
    background: rgba(16, 185, 129, 0.16);
    border: 1px solid rgba(16, 185, 129, 0.55);
    color: #a7f3d0;
    font-size: 10px;
    font-weight: 800;
    padding: 3px 10px;
    border-radius: 9999px;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.8px;
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.15);
}

.portal-feature-list {
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.portal-feature-item {
    font-size: 12px;
    color: #cbd5e1;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Outfit', -apple-system, sans-serif;
    line-height: 1.4;
}
.portal-feature-item b {
    color: #ffffff;
    font-weight: 700;
}
.portal-tag-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5px;
    font-weight: 750;
    padding: 1.5px 6px;
    border-radius: 4px;
    letter-spacing: 0.5px;
    min-width: 44px;
    text-align: center;
}
.tag-risk {
    background: rgba(245, 158, 11, 0.15);
    color: #fde68a;
    border: 1px solid rgba(245, 158, 11, 0.35);
}
.tag-wealth {
    background: rgba(16, 185, 129, 0.15);
    color: #a7f3d0;
    border: 1px solid rgba(16, 185, 129, 0.35);
}

/* Azzeramento del gap tra card e pulsante CTA per renderli un unico blocco coeso */
div[data-testid="column"]:has(.portal-card-risk) div[data-testid="stButton"],
div[data-testid="column"]:has(.portal-card-wealth) div[data-testid="stButton"] {
    margin-top: -8px !important;
}

/* Pulsante CTA Risk: Oro Istituzionale fuso con la scheda */
div[data-testid="stButton"] button[key="btn_splash_risk"],
div.st-key-btn_splash_risk button {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.95) 0%, rgba(217, 119, 6, 0.95) 100%) !important;
    border: 1px solid rgba(245, 158, 11, 0.9) !important;
    border-top: 1px solid rgba(255, 255, 255, 0.35) !important;
    border-top-left-radius: 0px !important;
    border-top-right-radius: 0px !important;
    border-bottom-left-radius: 22px !important;
    border-bottom-right-radius: 22px !important;
    color: #070b14 !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 900 !important;
    font-size: 13.5px !important;
    letter-spacing: 1px !important;
    padding: 13px 24px !important;
    box-shadow: 0 10px 28px rgba(245, 158, 11, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    text-transform: uppercase !important;
}
div[data-testid="stButton"] button[key="btn_splash_risk"]:hover,
div.st-key-btn_splash_risk button:hover {
    background: linear-gradient(135deg, #fbbf24 0%, #ea580c 100%) !important;
    color: #000000 !important;
    box-shadow: 0 14px 38px rgba(245, 158, 11, 0.6), 0 0 28px rgba(245, 158, 11, 0.35) !important;
    transform: translateY(-2px) !important;
}
div[data-testid="stButton"] button[key="btn_splash_risk"]:active,
div.st-key-btn_splash_risk button:active {
    transform: translateY(0px) scale(0.99) !important;
}

/* Pulsante CTA Wealth: Smeraldo Istituzionale fuso con la scheda */
div[data-testid="stButton"] button[key="btn_splash_wealth"],
div.st-key-btn_splash_wealth button {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.95) 0%, rgba(5, 150, 105, 0.95) 100%) !important;
    border: 1px solid rgba(16, 185, 129, 0.9) !important;
    border-top: 1px solid rgba(255, 255, 255, 0.35) !important;
    border-top-left-radius: 0px !important;
    border-top-right-radius: 0px !important;
    border-bottom-left-radius: 22px !important;
    border-bottom-right-radius: 22px !important;
    color: #031c12 !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 900 !important;
    font-size: 13.5px !important;
    letter-spacing: 1px !important;
    padding: 13px 24px !important;
    box-shadow: 0 10px 28px rgba(16, 185, 129, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    text-transform: uppercase !important;
}
div[data-testid="stButton"] button[key="btn_splash_wealth"]:hover,
div.st-key-btn_splash_wealth button:hover {
    background: linear-gradient(135deg, #34d399 0%, #047857 100%) !important;
    color: #000000 !important;
    box-shadow: 0 14px 38px rgba(16, 185, 129, 0.6), 0 0 28px rgba(16, 185, 129, 0.35) !important;
    transform: translateY(-2px) !important;
}
div[data-testid="stButton"] button[key="btn_splash_wealth"]:active,
div.st-key-btn_splash_wealth button:active {
    transform: translateY(0px) scale(0.99) !important;
}
</style>
""")


# ── JAVASCRIPT HARDWARE OVERRIDE (COMPATIBILE STREAMLIT 1.59+) ───────
def auto_collapse_sidebar() -> None:
    """Collassa e nasconde la sidebar durante lo splash screen, disconnettendosi non appena si accede ai moduli."""
    try:
        import streamlit.components.v1 as components
        components.html("""
        <script>
        (function() {
            try {
                const doc = window.parent.document;
                
                // Disconnetti eventuale observer precedente
                if (window.parent.__argusSplashObs) {
                    window.parent.__argusSplashObs.disconnect();
                    window.parent.__argusSplashObs = null;
                }

                // 1. Collassa la sidebar se aperta nello splash
                const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                if (sidebar && sidebar.getAttribute('aria-expanded') === 'true') {
                    const collapseBtn = doc.querySelector('button[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapseButton"] button, button[aria-label*="collapse" i]');
                    if (collapseBtn) collapseBtn.click();
                }
                
                // 2. Nascondi controlli header durante lo splash screen
                const hideSplashChevrons = () => {
                    const splashRoot = doc.getElementById('argus-splash-root');
                    if (!splashRoot) {
                        if (window.parent.__argusSplashObs) {
                            window.parent.__argusSplashObs.disconnect();
                            window.parent.__argusSplashObs = null;
                        }
                        return;
                    }
                    const targets = doc.querySelectorAll('header[data-testid="stHeader"], [data-testid="stExpandSidebarButton"], button[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"], button[data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"], button[data-testid="stSidebarCollapsedControl"], button[aria-label*="sidebar" i]');
                    targets.forEach(el => {
                        el.style.setProperty('display', 'none', 'important');
                        el.style.setProperty('visibility', 'hidden', 'important');
                        el.style.setProperty('opacity', '0', 'important');
                        el.style.setProperty('pointer-events', 'none', 'important');
                    });
                };
                hideSplashChevrons();
                
                // 3. MutationObserver limitato alla durata dello splash
                const obs = new MutationObserver(hideSplashChevrons);
                obs.observe(doc.body, { childList: true, subtree: true });
                window.parent.__argusSplashObs = obs;
                setTimeout(() => {
                    if (window.parent.__argusSplashObs === obs) {
                        obs.disconnect();
                        window.parent.__argusSplashObs = null;
                    }
                }, 5000);

                // 4. Intercetta click sui pulsanti CTA per attivare immediatamente lo scudo di caricamento pulito
                const attachCtaInterceptors = () => {
                    const btnRisk = doc.querySelector('button[key="btn_splash_risk"], div.st-key-btn_splash_risk button');
                    const btnWealth = doc.querySelector('button[key="btn_splash_wealth"], div.st-key-btn_splash_wealth button');
                    const shield = doc.getElementById('argus-loading-shield');
                    const splashRoot = doc.getElementById('argus-splash-root');
                    const ctaCards = doc.querySelectorAll('.portal-card-risk, .portal-card-wealth');
                    const ctaCols = doc.querySelectorAll('div[data-testid="column"]:has(.portal-card-risk), div[data-testid="column"]:has(.portal-card-wealth), div.st-key-btn_splash_risk, div.st-key-btn_splash_wealth');
                    
                    const triggerShield = (title, sub) => {
                        if (window.parent.__argusSplashObs) {
                            window.parent.__argusSplashObs.disconnect();
                            window.parent.__argusSplashObs = null;
                        }
                        try {
                            window.parent.scrollTo({top: 0, behavior: 'instant'});
                        } catch(e) {
                            window.parent.scrollTo(0, 0);
                        }
                        if (splashRoot) splashRoot.style.setProperty('display', 'none', 'important');
                        ctaCards.forEach(c => c.style.setProperty('display', 'none', 'important'));
                        ctaCols.forEach(c => c.style.setProperty('display', 'none', 'important'));
                        if (shield) {
                            const titleEl = shield.querySelector('.shield-title');
                            const subEl = shield.querySelector('.shield-subtext');
                            if (titleEl) titleEl.innerText = title;
                            if (subEl) subEl.innerText = sub;
                            shield.style.setProperty('display', 'flex', 'important');
                            shield.style.setProperty('opacity', '1', 'important');
                        }
                    };

                    if (btnRisk && !btnRisk.dataset.argusAttached) {
                        btnRisk.dataset.argusAttached = "true";
                        btnRisk.addEventListener('click', () => triggerShield('INIZIALIZZAZIONE DESK RISK ANALYTICS...', 'Caricamento matrici di covarianza e pipeline quantitativa...'));
                    }
                    if (btnWealth && !btnWealth.dataset.argusAttached) {
                        btnWealth.dataset.argusAttached = "true";
                        btnWealth.addEventListener('click', () => triggerShield('INIZIALIZZAZIONE SUITE WEALTH ADVISORY...', 'Caricamento modulo Control Room e ledger patrimoniale...'));
                    }
                };
                attachCtaInterceptors();
                setTimeout(attachCtaInterceptors, 200);
                setTimeout(attachCtaInterceptors, 600);
                setTimeout(attachCtaInterceptors, 1200);
            } catch (e) {}
        })();
        </script>
        """, height=0, width=0)
    except Exception:
        pass


def auto_expand_sidebar() -> None:
    """Apre la sidebar al passaggio nel modulo e ripristina la piena operatività dei controlli << e >>."""
    try:
        import streamlit.components.v1 as components
        components.html("""
        <script>
        function triggerExpand() {
            try {
                const doc = window.parent.document;
                
                // 1. Disconnetti tassativamente qualsiasi observer di blocco dello splash
                if (window.parent.__argusSplashObs) {
                    window.parent.__argusSplashObs.disconnect();
                    window.parent.__argusSplashObs = null;
                }

                // 2. Rimuovi ogni stile inline residuo sui pulsanti di collasso ed espansione
                const chevrons = doc.querySelectorAll('header[data-testid="stHeader"], [data-testid="stSidebarCollapseButton"], button[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarHeader"], div[data-testid="stSidebarHeader"], [data-testid="stExpandSidebarButton"], button[data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"], button[data-testid="stSidebarCollapsedControl"], button[aria-label*="sidebar" i]');
                chevrons.forEach(el => {
                    el.style.removeProperty('display');
                    el.style.removeProperty('visibility');
                    el.style.removeProperty('opacity');
                    el.style.removeProperty('width');
                    el.style.removeProperty('height');
                    el.style.removeProperty('pointer-events');
                });

                // 3. Espandi la sidebar se e' chiusa
                const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                const isCollapsed = !sidebar || sidebar.getAttribute('aria-expanded') === 'false' || sidebar.getBoundingClientRect().width < 80;
                if (isCollapsed) {
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
def get_argus_vector_logo_svg(size: int = 138, accent_color: str = "#f59e0b") -> str:
    """Genera l'Occhio di Argus vettoriale avanzato con radar quantitativo orbitale animato, iride ad alta precisione, mirino HUD e ottica laser."""
    return _clean_html(f"""
    <svg width="{size}" height="{size}" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" class="splash-logo-svg" style="display:block;margin:auto;filter:drop-shadow(0 0 26px rgba(245, 158, 11, 0.55));">
        <defs>
            <radialGradient id="argusIrisGrad" cx="45%" cy="45%" r="55%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95"/>
                <stop offset="25%" stop-color="{accent_color}" stop-opacity="0.95"/>
                <stop offset="55%" stop-color="#b45309" stop-opacity="0.85"/>
                <stop offset="85%" stop-color="#0b0f19" stop-opacity="0.95"/>
                <stop offset="100%" stop-color="{accent_color}" stop-opacity="0.6"/>
            </radialGradient>
            <radialGradient id="argusPupilGrad" cx="40%" cy="40%" r="60%">
                <stop offset="0%" stop-color="#1e293b" stop-opacity="0.9"/>
                <stop offset="60%" stop-color="#060911" stop-opacity="0.98"/>
                <stop offset="100%" stop-color="#020408" stop-opacity="1.0"/>
            </radialGradient>
            <filter id="argusGlow" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="coreGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3.5" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <linearGradient id="orbitalGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="{accent_color}" stop-opacity="0.9"/>
                <stop offset="50%" stop-color="#38bdf8" stop-opacity="0.4"/>
                <stop offset="100%" stop-color="{accent_color}" stop-opacity="0.9"/>
            </linearGradient>
            <linearGradient id="radarSweepGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="{accent_color}" stop-opacity="0.5"/>
                <stop offset="100%" stop-color="{accent_color}" stop-opacity="0.0"/>
            </linearGradient>
            <style>
                @keyframes argusRadarSweep {{
                    from {{ transform: rotate(0deg); }}
                    to {{ transform: rotate(360deg); }}
                }}
                @keyframes argusRingCounter {{
                    from {{ transform: rotate(360deg); }}
                    to {{ transform: rotate(0deg); }}
                }}
                @keyframes argusRingPulse {{
                    0%, 100% {{ opacity: 0.65; transform: scale(1); }}
                    50% {{ opacity: 0.95; transform: scale(1.02); }}
                }}
                @keyframes argusCoreBlink {{
                    0%, 100% {{ r: 3.5; opacity: 0.95; }}
                    50% {{ r: 4.8; opacity: 1; }}
                }}
            </style>
        </defs>

        <!-- Anello Esterno HUD Radar con rotazione e coordinate polari -->
        <circle cx="100" cy="100" r="92" fill="none" stroke="url(#orbitalGrad)" stroke-width="1.2" stroke-dasharray="4 8" opacity="0.6" style="transform-origin: 100px 100px; animation: argusRingPulse 4s ease-in-out infinite;"/>
        <circle cx="100" cy="100" r="82" fill="none" stroke="{accent_color}" stroke-width="0.8" stroke-dasharray="1 5" opacity="0.45" style="transform-origin: 100px 100px; animation: argusRingCounter 30s linear infinite;"/>
        <circle cx="100" cy="100" r="72" fill="none" stroke="{accent_color}" stroke-width="0.5" opacity="0.25"/>

        <!-- Tacche di Azimut / Coordinate Caliper HUD -->
        <line x1="100" y1="5" x2="100" y2="15" stroke="{accent_color}" stroke-width="2" opacity="0.9"/>
        <line x1="100" y1="185" x2="100" y2="195" stroke="{accent_color}" stroke-width="2" opacity="0.9"/>
        <line x1="5" y1="100" x2="15" y2="100" stroke="{accent_color}" stroke-width="2" opacity="0.9"/>
        <line x1="185" y1="100" x2="195" y2="100" stroke="{accent_color}" stroke-width="2" opacity="0.9"/>

        <line x1="33" y1="33" x2="40" y2="40" stroke="{accent_color}" stroke-width="1.2" opacity="0.6"/>
        <line x1="167" y1="33" x2="160" y2="40" stroke="{accent_color}" stroke-width="1.2" opacity="0.6"/>
        <line x1="33" y1="167" x2="40" y2="160" stroke="{accent_color}" stroke-width="1.2" opacity="0.6"/>
        <line x1="167" y1="167" x2="160" y2="160" stroke="{accent_color}" stroke-width="1.2" opacity="0.6"/>

        <!-- Fascio Radar Vettoriale Rotante a 360° -->
        <g style="transform-origin: 100px 100px; animation: argusRadarSweep 4.5s linear infinite;">
            <line x1="100" y1="100" x2="100" y2="8" stroke="{accent_color}" stroke-width="2" stroke-linecap="round" opacity="0.95" filter="url(#coreGlow)"/>
            <path d="M 100 100 L 100 8 A 92 92 0 0 1 158 26 Z" fill="url(#radarSweepGrad)" opacity="0.35"/>
        </g>

        <!-- Sagoma Mandorla Esterna dell'Occhio di Argus -->
        <path d="M 18 100 Q 100 24 182 100 Q 100 176 18 100 Z" fill="rgba(12, 17, 29, 0.88)" stroke="{accent_color}" stroke-width="2.6" filter="url(#argusGlow)" />
        
        <!-- Contorno Interno Tecnico Tratteggiato -->
        <path d="M 32 100 Q 100 38 168 100 Q 100 162 32 100 Z" fill="none" stroke="rgba(255, 255, 255, 0.3)" stroke-width="1" stroke-dasharray="3 4" />
        <path d="M 44 100 Q 100 50 156 100 Q 100 150 44 100 Z" fill="none" stroke="{accent_color}" stroke-width="0.6" opacity="0.3" />

        <!-- Mirini di Coordinate HUD (+ Markers) -->
        <g stroke="{accent_color}" stroke-width="1" opacity="0.5">
            <path d="M 56 97 L 56 103 M 53 100 L 59 100" />
            <path d="M 144 97 L 144 103 M 141 100 L 147 100" />
        </g>

        <!-- Corona Circolare dell'Iride Quantitativa -->
        <circle cx="100" cy="100" r="36" fill="url(#argusIrisGrad)" stroke="{accent_color}" stroke-width="2.2" filter="url(#coreGlow)"/>
        <circle cx="100" cy="100" r="36" fill="none" stroke="rgba(255, 255, 255, 0.4)" stroke-width="0.8" stroke-dasharray="2 3"/>
        
        <!-- Ghiera Radiale Interna (Apertura Meccanica / Chrono) -->
        <circle cx="100" cy="100" r="26" fill="none" stroke="{accent_color}" stroke-width="0.8" stroke-dasharray="1 3" opacity="0.75" style="transform-origin: 100px 100px; animation: argusRingCounter 18s linear infinite;"/>

        <!-- Pupilla Centrale Profonda -->
        <circle cx="100" cy="100" r="16" fill="url(#argusPupilGrad)" stroke="#ffffff" stroke-width="1.4" opacity="0.98"/>
        
        <!-- Anello Ottico Speculare & Riflesso Curvo -->
        <path d="M 88 88 A 16 16 0 0 1 112 88" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" opacity="0.85"/>
        <circle cx="94" cy="94" r="4.2" fill="#ffffff" opacity="0.95"/>
        <circle cx="105" cy="104" r="2" fill="#ffffff" opacity="0.6"/>

        <!-- Nucleo Laser Centrale Pulsante (Focal Point) -->
        <circle cx="100" cy="100" r="4" fill="{accent_color}" filter="url(#coreGlow)" style="animation: argusCoreBlink 2.2s ease-in-out infinite;"/>

        <!-- Reticolo Assiale di Calibrazione Laser -->
        <line x1="100" y1="24" x2="100" y2="40" stroke="{accent_color}" stroke-width="2" opacity="0.9"/>
        <line x1="100" y1="160" x2="100" y2="176" stroke="{accent_color}" stroke-width="2" opacity="0.9"/>
        <line x1="24" y1="100" x2="40" y2="100" stroke="{accent_color}" stroke-width="2" opacity="0.9"/>
        <line x1="160" y1="100" x2="176" y2="100" stroke="{accent_color}" stroke-width="2" opacity="0.9"/>
    </svg>
    """)


# ── RENDERIZZAZIONE DEL CONTENUTO HTML ───────────────────────────────
def render_splash_html(
    app_title: str = "A R G U S",
    subtitle: str = "QUANTITATIVE RISK ANALYTICS & WEALTH INTELLIGENCE ECOSYSTEM",
    version_tag: str = "v9.7.0 Institutional",
    current_status: str = "Kernel operativo. Seleziona l'Ambiente di Lavoro sottostante:",
    progress_pct: int = 100,
    accent_color: str = "#f59e0b",
    is_fading_out: bool = False,
    show_skip: bool = False,
) -> str:
    """Costruisce il layout completo dello splash screen con logo, badge ribbon, console telemetrica e scudo di caricamento."""
    logo_svg = get_argus_vector_logo_svg(size=138, accent_color=accent_color)
    status_text = current_status if current_status else "Caricamento moduli operativi..."
    fade_class = " splash-fade-out" if is_fading_out else ""
    skip_html = '<div style="margin-top: 8px; font-size: 11px; color: #64748b; text-align: center;">⚡ Salta introduzione &bull; Premi uno dei due portali per accedere subito</div>' if show_skip else ""

    loading_shield_html = f"""
    <div id="argus-loading-shield">
        <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
            {get_argus_vector_logo_svg(size=64, accent_color=accent_color)}
            <div class="shield-spinner"></div>
            <div class="shield-title">INIZIALIZZAZIONE AMBIENTE OPERATIVO...</div>
            <div class="shield-subtext">Sincronizzazione runtime DuckDB &amp; SQLite in corso...</div>
        </div>
    </div>
    """

    return _clean_html(f"""
    {loading_shield_html}
    <div class="splash-ambient-glow"></div>
    <div id="argus-splash-root" class="splash-master-wrapper{fade_class}">
        <div class="splash-inner-core">
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

            <div class="telemetry-bar">
                <div class="telemetry-item">
                    <span class="telemetry-dot dot-green"></span>
                    <span class="telemetry-label">RUNTIME:</span>
                    <b>duckdb-simd@localhost</b>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-dot dot-cyan"></span>
                    <span class="telemetry-label">LATENCY:</span>
                    <b>0.18 ms</b>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-dot dot-purple"></span>
                    <span class="telemetry-label">STATUS ({progress_pct}%):</span>
                    <b>{html.escape(status_text)}</b>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-dot dot-amber"></span>
                    <span class="telemetry-label">KERNEL:</span>
                    <span style="color: #10b981; font-weight: 700;">● 100% OPERATIONAL</span>
                </div>
            </div>
            {skip_html}
        </div>
    </div>
    """)


# ── CONTROLLO CICLO DI VITA & RENDERING PRINCIPALE ─────────────────
def render_splash_screen(
    app_version: str = "9.7.0",
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

    def _on_click_enter_risk():
        st.session_state["_app_initialized"] = True
        st.session_state["splash_dismissed"] = True
        st.session_state["splash_completed"] = True
        st.session_state["argus_portal_mode"] = "📊 Risk Analytics"
        try:
            if hasattr(st, "query_params") and "splash" in st.query_params:
                del st.query_params["splash"]
        except Exception:
            pass

    def _on_click_enter_wealth():
        st.session_state["_app_initialized"] = True
        st.session_state["splash_dismissed"] = True
        st.session_state["splash_completed"] = True
        st.session_state["argus_portal_mode"] = "🏛️ Wealth Management"
        try:
            if hasattr(st, "query_params") and "splash" in st.query_params:
                del st.query_params["splash"]
        except Exception:
            pass

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
                <div style="font-size: 12px; color: #94a3b8; line-height: 1.4; margin-bottom: 7px;">
                    Desk quantitativo istituzionale per asset pricing, stress testing sistemico e ottimizzazione di frontiera.
                </div>
                <div class="portal-feature-list">
                    <div class="portal-feature-item"><span class="portal-tag-pill tag-risk">VaR</span> <span><b>Metriche di Coda:</b> VaR Storico/Parametrico (95/99%), CVaR &amp; EWMA</span></div>
                    <div class="portal-feature-item"><span class="portal-tag-pill tag-risk">SHOCK</span> <span><b>Stress Testing:</b> Scenari Crisi 2008, Shock Tassi, Crolli Tech &amp; Tariffe</span></div>
                    <div class="portal-feature-item"><span class="portal-tag-pill tag-risk">QP</span> <span><b>Asset Allocation:</b> Markowitz, Black-Litterman, HRP &amp; Copule Matematiche</span></div>
                    <div class="portal-feature-item"><span class="portal-tag-pill tag-risk">QUANT</span> <span><b>Screener &amp; BQuant:</b> Multi-Factor Screener + Sandbox Python Integrata</span></div>
                </div>
            </div>
        </div>
        """)
        st.markdown(risk_card_html, unsafe_allow_html=True)
        if st.button("🚀 ENTRA NEL DESK RISK ANALYTICS →", key="btn_splash_risk", use_container_width=True, on_click=_on_click_enter_risk):
            _on_click_enter_risk()
            st.rerun()

    with col_wealth:
        wealth_card_html = _clean_html("""
        <div class="portal-card-wealth">
            <div>
                <div class="portal-card-header">
                    <span class="portal-card-title">🏛️ Wealth Management &amp; Advisory</span>
                    <span class="portal-badge-wealth">10 MODULI WEALTH &amp; ADVISORY</span>
                </div>
                <div style="font-size: 12px; color: #94a3b8; line-height: 1.4; margin-bottom: 7px;">
                    Piattaforma di consolidamento olistico del patrimonio netto, budget familiare, caveau beni rifugio e fiscalità.
                </div>
                <div class="portal-feature-list">
                    <div class="portal-feature-item"><span class="portal-tag-pill tag-wealth">LEDGER</span> <span><b>Net Worth Olistico:</b> Conti Correnti, Broker, Immobili &amp; Caveau Orologi</span></div>
                    <div class="portal-feature-item"><span class="portal-tag-pill tag-wealth">BUDGET</span> <span><b>Cash Flow:</b> Framework 50/30/20, Burn Rate &amp; Proiezioni FIRE</span></div>
                    <div class="portal-feature-item"><span class="portal-tag-pill tag-wealth">FISCO</span> <span><b>Fisco &amp; Previdenza:</b> Monitoraggio Quadro RW (IVAFE/IVIE) &amp; Fondi Pensione</span></div>
                    <div class="portal-feature-item"><span class="portal-tag-pill tag-wealth">AI</span> <span><b>Advisory Copilot:</b> Audit patrimoniale avanzato con motore quantitativo locale</span></div>
                </div>
            </div>
        </div>
        """)
        st.markdown(wealth_card_html, unsafe_allow_html=True)
        if st.button("💎 ENTRA NELLA SUITE WEALTH ADVISORY →", key="btn_splash_wealth", use_container_width=True, on_click=_on_click_enter_wealth):
            _on_click_enter_wealth()
            st.switch_page("pages/12_🎛️_Wealth_Control_Room.py")

    return True


# Alias di retrocompatibilita
show_splash_screen = render_splash_screen
