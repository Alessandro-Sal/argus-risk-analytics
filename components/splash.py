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
    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.12; }
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

/* ── BARRA SUPERIORE SISTEMA (Top Header Allineato) ────────────────── */
div[data-testid="stHorizontalBlock"]:has(.splash-sys-status) {
    max-width: 1200px !important;
    width: 100% !important;
    margin: 0 auto 10px auto !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
}
.splash-sys-status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #94a3b8;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 6px 16px;
    border-radius: 20px;
    backdrop-filter: blur(12px);
    letter-spacing: 0.4px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
}
.sys-pulse-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: ledPulse 2s infinite ease-in-out;
    display: inline-block;
}
.sys-title {
    color: #e2e8f0;
    font-weight: 700;
    letter-spacing: 0.8px;
}
.sys-sep {
    color: #475569;
    font-size: 9px;
}
.sys-tag {
    color: #f59e0b;
    font-weight: 600;
}
.sys-mode {
    color: #38bdf8;
    font-weight: 600;
}

/* Switcher Lingua Segmentato IT / EN */
div.st-key-btn_splash_toggle_it button,
div.st-key-btn_splash_toggle_en button {
    height: 30px !important;
    min-height: 30px !important;
    padding: 2px 14px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.8px !important;
    border-radius: 8px !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
div.st-key-btn_splash_toggle_it button[kind="primary"],
div.st-key-btn_splash_toggle_en button[kind="primary"] {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.25) 0%, rgba(217, 119, 6, 0.35) 100%) !important;
    border: 1px solid rgba(245, 158, 11, 0.8) !important;
    color: #fbbf24 !important;
    box-shadow: 0 0 12px rgba(245, 158, 11, 0.25) !important;
}
div.st-key-btn_splash_toggle_it button[kind="secondary"],
div.st-key-btn_splash_toggle_en button[kind="secondary"] {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #94a3b8 !important;
}
div.st-key-btn_splash_toggle_it button[kind="secondary"]:hover,
div.st-key-btn_splash_toggle_en button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.25) !important;
    color: #ffffff !important;
}

/* Master Double-Bezel (Doppelrand) Architecture: Involucro Macchina Istituzionale */
.splash-master-wrapper {
    max-width: 1200px;
    width: 100%;
    margin: 0px auto 14px auto;
    padding: 4px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.8), 0 0 40px rgba(245, 158, 11, 0.03);
    backdrop-filter: blur(32px) saturate(180%);
    -webkit-backdrop-filter: blur(32px) saturate(180%);
    position: relative;
    overflow: hidden;
    animation: splashFadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.splash-inner-core {
    border-radius: 20px;
    background: radial-gradient(1200px circle at 50% -10%, rgba(20, 29, 46, 0.85) 0%, rgba(10, 15, 26, 0.96) 55%, rgba(6, 9, 16, 0.99) 100%);
    border: 1px solid rgba(255, 255, 255, 0.05);
    padding: 20px 28px 16px;
    box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1);
    text-align: center;
}

@keyframes splashFadeIn {
    0% { opacity: 0; transform: translateY(6px) scale(0.99); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}

.splash-logo-container {
    margin-bottom: 2px;
    filter: drop-shadow(0 0 20px rgba(245, 158, 11, 0.45));
    transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.splash-logo-container:hover {
    transform: scale(1.02);
}

.splash-title {
    font-size: 32px;
    font-weight: 900;
    letter-spacing: 14px;
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
    font-family: 'JetBrains Mono', monospace;
}

.splash-desc {
    font-size: 12.5px;
    color: #94a3b8;
    max-width: 860px;
    margin: 0 auto 9px auto;
    line-height: 1.5;
    font-family: 'Outfit', -apple-system, sans-serif;
}

/* Badge Ribbon Istituzionale */
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

/* Hardware Telemetry Rail Istituzionale */
@keyframes ledPulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(0.85); }
}
.telemetry-bar {
    background: rgba(4, 7, 14, 0.94);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 8px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
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

/* Workspace Selection Callout Prompt */
.splash-workspace-prompt {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 12px;
    padding: 5px 18px;
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.22);
    border-radius: 9999px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 700;
    color: #fde68a;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.prompt-pulse-icon {
    font-size: 11px;
    color: #f59e0b;
    animation: ledPulse 1.8s infinite ease-in-out;
    display: inline-block;
}

/* Allineamento larghezza blocco card a due colonne */
div[data-testid="stHorizontalBlock"]:has(.portal-card-risk) {
    max-width: 1200px !important;
    margin: 0 auto !important;
    gap: 16px !important;
}

/* Bento Grid: Schede Monolitiche di Design Superiore con altezza identica garantita */
.portal-card-risk {
    background: radial-gradient(circle at 0% 0%, rgba(245, 158, 11, 0.10) 0%, rgba(13, 19, 33, 0.96) 75%);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-top: 2px solid #f59e0b;
    border-radius: 20px;
    padding: 22px 24px 20px 24px;
    height: 252px;
    min-height: 252px;
    box-sizing: border-box;
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.portal-card-risk:hover {
    border-color: rgba(245, 158, 11, 0.65);
    box-shadow: 0 18px 44px rgba(245, 158, 11, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.portal-card-wealth {
    background: radial-gradient(circle at 100% 0%, rgba(16, 185, 129, 0.10) 0%, rgba(13, 19, 33, 0.96) 75%);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-top: 2px solid #10b981;
    border-radius: 20px;
    padding: 22px 24px 20px 24px;
    height: 252px;
    min-height: 252px;
    box-sizing: border-box;
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.portal-card-wealth:hover {
    border-color: rgba(16, 185, 129, 0.65);
    box-shadow: 0 18px 44px rgba(16, 185, 129, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15);
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
    gap: 7px;
}

.portal-feature-item {
    font-size: 12px;
    color: #cbd5e1;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-family: 'Outfit', -apple-system, sans-serif;
    line-height: 1.45;
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
    font-size: 9px;
    font-weight: 800;
    padding: 2px 0px;
    border-radius: 5px;
    letter-spacing: 0.5px;
    width: 62px;
    min-width: 62px;
    max-width: 62px;
    text-align: center;
    flex-shrink: 0;
    margin-top: 1.5px;
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

/* Spaziatura controllata e pulsanti CTA Obsidian Glass perfettamente livellati */
div.st-key-btn_splash_risk,
div.st-key-btn_splash_wealth {
    margin-top: 10px !important;
}

/* Pulsante CTA Risk: Obsidian Glass Istituzionale con bordo ambra illuminato */
div[data-testid="stButton"] button[key="btn_splash_risk"],
div.st-key-btn_splash_risk button {
    background: linear-gradient(180deg, rgba(245, 158, 11, 0.18) 0%, rgba(180, 83, 9, 0.32) 100%) !important;
    border: 1px solid rgba(245, 158, 11, 0.65) !important;
    border-top: 1px solid rgba(255, 255, 255, 0.22) !important;
    border-radius: 14px !important;
    color: #ffffff !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important;
    font-size: 13.5px !important;
    letter-spacing: 1px !important;
    padding: 13px 24px !important;
    height: 48px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6), 0 0 16px rgba(245, 158, 11, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    text-transform: uppercase !important;
    text-shadow: 0 0 12px rgba(245, 158, 11, 0.6) !important;
}
div[data-testid="stButton"] button[key="btn_splash_risk"]:hover,
div.st-key-btn_splash_risk button:hover {
    background: linear-gradient(180deg, rgba(245, 158, 11, 0.38) 0%, rgba(217, 119, 6, 0.58) 100%) !important;
    border-color: #f59e0b !important;
    color: #ffffff !important;
    box-shadow: 0 12px 32px rgba(245, 158, 11, 0.45), 0 0 28px rgba(245, 158, 11, 0.3) !important;
    transform: translateY(-2px) !important;
}
div[data-testid="stButton"] button[key="btn_splash_risk"]:active,
div.st-key-btn_splash_risk button:active {
    transform: translateY(0px) scale(0.99) !important;
}

/* Pulsante CTA Wealth: Obsidian Glass Istituzionale con bordo smeraldo illuminato */
div[data-testid="stButton"] button[key="btn_splash_wealth"],
div.st-key-btn_splash_wealth button {
    background: linear-gradient(180deg, rgba(16, 185, 129, 0.18) 0%, rgba(5, 150, 105, 0.32) 100%) !important;
    border: 1px solid rgba(16, 185, 129, 0.65) !important;
    border-top: 1px solid rgba(255, 255, 255, 0.22) !important;
    border-radius: 14px !important;
    color: #ffffff !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important;
    font-size: 13.5px !important;
    letter-spacing: 1px !important;
    padding: 13px 24px !important;
    height: 48px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6), 0 0 16px rgba(16, 185, 129, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    text-transform: uppercase !important;
    text-shadow: 0 0 12px rgba(16, 185, 129, 0.6) !important;
}
div[data-testid="stButton"] button[key="btn_splash_wealth"]:hover,
div.st-key-btn_splash_wealth button:hover {
    background: linear-gradient(180deg, rgba(16, 185, 129, 0.38) 0%, rgba(4, 120, 87, 0.58) 100%) !important;
    border-color: #10b981 !important;
    color: #ffffff !important;
    box-shadow: 0 12px 32px rgba(16, 185, 129, 0.45), 0 0 28px rgba(16, 185, 129, 0.3) !important;
    transform: translateY(-2px) !important;
}
div[data-testid="stButton"] button[key="btn_splash_wealth"]:active,
div.st-key-btn_splash_wealth button:active {
    transform: translateY(0px) scale(0.99) !important;
}

/* Pulsante Logout / Switch Account Inferiore */
div.st-key-btn_splash_switch_account {
    margin-top: 14px !important;
}
div.st-key-btn_splash_switch_account button {
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 9999px !important;
    color: #94a3b8 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.4px !important;
    padding: 7px 20px !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    box-shadow: none !important;
}
div.st-key-btn_splash_switch_account button:hover {
    background: rgba(255, 255, 255, 0.06) !important;
    border-color: rgba(255, 255, 255, 0.22) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
    transform: translateY(-1px) !important;
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
    version_tag: str = "v10.0.0 Institutional",
    current_status: str = "Kernel operativo. Seleziona l'Ambiente di Lavoro sottostante:",
    progress_pct: int = 100,
    accent_color: str = "#f59e0b",
    is_fading_out: bool = False,
    show_skip: bool = False,
    locale: str = "it",
) -> str:
    """Costruisce il layout completo dello splash screen con logo, badge ribbon, console telemetrica e scudo di caricamento."""
    is_it = (locale == "it")
    logo_svg = get_argus_vector_logo_svg(size=138, accent_color=accent_color)
    status_text = current_status if current_status else ("Caricamento moduli operativi..." if is_it else "Loading operative modules...")
    fade_class = " splash-fade-out" if is_fading_out else ""
    skip_msg = "⚡ Salta introduzione &bull; Premi uno dei due portali per accedere subito" if is_it else "⚡ Skip introduction &bull; Click one of the two desks to enter immediately"
    skip_html = f'<div style="margin-top: 8px; font-size: 11px; color: #64748b; text-align: center;">{skip_msg}</div>' if show_skip else ""

    shield_title = "INIZIALIZZAZIONE AMBIENTE OPERATIVO..." if is_it else "INITIALIZING OPERATIONAL RUNTIME..."
    shield_sub = "Sincronizzazione runtime DuckDB &amp; SQLite in corso..." if is_it else "Synchronizing DuckDB &amp; SQLite runtime..."

    loading_shield_html = f"""
    <div id="argus-loading-shield">
        <div style="text-align: center; display: flex; flex-direction: column; align-items: center;">
            {get_argus_vector_logo_svg(size=64, accent_color=accent_color)}
            <div class="shield-spinner"></div>
            <div class="shield-title">{shield_title}</div>
            <div class="shield-subtext">{shield_sub}</div>
        </div>
    </div>
    """

    try:
        from core.supabase_cloud import get_active_account_badge_info

        acct = get_active_account_badge_info()
        disp_user = acct["display_name"]
        badge_lbl = acct["badge_label"]
        if not is_it:
            badge_lbl = badge_lbl.replace("(LOCALE)", "(LOCAL)").replace("TITOLARE", "OWNER")
        user_pill_html = (
            f'<span class="splash-pill" style="border-color:{acct["badge_border"]}; '
            f'background:{acct["badge_bg"]}; color:#ffffff;">'
            f'👤 <b>{html.escape(disp_user)}</b> &bull; '
            f'<span style="color:{acct["badge_color"]};">{html.escape(badge_lbl)}</span></span>'
        )
    except Exception:
        zero_leak = "Zero-Cloud Leak Crittografia Locale" if is_it else "Zero-Cloud Leak Local Encryption"
        user_pill_html = f'<span class="splash-pill">🔒 <b>{zero_leak}</b></span>'

    desc_text = (
        "Terminale quantitativo unificato per l'analisi econometrica del rischio, stress testing sistemico, "
        "ottimizzazione di frontiera e intelligence patrimoniale olistica."
        if is_it else
        "Unified quantitative terminal for econometric risk analysis, systemic stress testing, "
        "frontier portfolio optimization, and holistic wealth intelligence."
    )

    mod_text = "⚡ <b>22 Moduli Attivi</b> (12 Risk + 10 Wealth)" if is_it else "⚡ <b>22 Active Modules</b> (12 Risk + 10 Wealth)"
    t_engine = "duckdb-simd@localhost"
    t_latency = "0.18 ms"
    t_engine_lbl = "RUNTIME"
    t_latency_lbl = "LATENCY"
    t_vault_lbl = "ISOLAMENTO DATI" if is_it else "DATA ISOLATION"
    t_vault_val = "Supabase AES-256"
    t_kernel_lbl = "KERNEL" if is_it else "CORE KERNEL"
    t_kernel_val = "100% OPERATIVO" if is_it else "100% OPERATIONAL"

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
                {desc_text}
            </div>
            
            <div class="splash-badge-ribbon">
                {user_pill_html}
                <span class="splash-pill">🟢 <b>{html.escape(version_tag)}</b></span>
                <span class="splash-pill">{mod_text}</span>
                <span class="splash-pill">🗄️ <b>Supabase Cloud &amp; DuckDB SIMD</b></span>
            </div>

            <div class="telemetry-bar">
                <div class="telemetry-item">
                    <span class="telemetry-dot dot-green"></span>
                    <span class="telemetry-label">{t_engine_lbl}:</span>
                    <b>{t_engine}</b>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-dot dot-cyan"></span>
                    <span class="telemetry-label">{t_latency_lbl}:</span>
                    <b>{t_latency}</b>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-dot dot-purple"></span>
                    <span class="telemetry-label">{t_vault_lbl}:</span>
                    <b>{t_vault_val}</b>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-dot dot-amber"></span>
                    <span class="telemetry-label">{t_kernel_lbl}:</span>
                    <span style="color: #10b981; font-weight: 700;">● {t_kernel_val}</span>
                </div>
            </div>

            <div class="splash-workspace-prompt">
                <span class="prompt-pulse-icon">⚡</span>
                <span>{html.escape(status_text)}</span>
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
    Se `ARGUS_REQUIRE_LOGIN=true`, mostra PRIMA il Login Gate a tutto schermo.
    
    Restituisce True se il Login Gate o lo Splash e' attivo (bloccando l'esecuzione sottostante con st.stop()).
    Restituisce False se lo splash e' completato/bypassato (permettendo il caricamento immediato della dashboard).
    """
    # ── Hardened Auth Guard (Supabase Native Auth & Session Lock) ──
    from core.auth_manager import AuthManager

    AuthManager.auth_guard(show_login_if_unauth=True)

    # Se splash_dismissed e' esplicitamente False (es. click su 'Schermata di Avvio' nella sidebar)
    if st.session_state.get("splash_dismissed") is False:
        force_show = True

    # Bypass istantaneo se gia inizializzato o dismissato e non forzato
    if (st.session_state.get("splash_dismissed", False) or st.session_state.get("_app_initialized", False)) and not force_show:
        return False

    # Controllo query parameters per bypass esplicito / skip
    query_params = getattr(st, "query_params", None)
    if query_params is not None and "skip_splash" in query_params:
        st.session_state["_app_initialized"] = True
        st.session_state["splash_dismissed"] = True
        st.session_state["splash_completed"] = True
        return False

    # Contenitore atomico per rimozione immediata dal DOM senza ghost elements
    splash_container = st.empty()

    def _on_click_enter_risk():
        st.session_state["_app_initialized"] = True
        st.session_state["splash_dismissed"] = True
        st.session_state["splash_completed"] = True
        st.session_state["argus_portal_mode"] = "📊 Risk Analytics"
        st.session_state["db_name"] = st.session_state.get("risk_db_name") or "investment_risk_bi"
        try:
            splash_container.empty()
        except Exception:
            pass
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
        st.session_state["db_name"] = st.session_state.get("wealth_db_name") or "wealth"
        try:
            splash_container.empty()
        except Exception:
            pass
        try:
            if hasattr(st, "query_params") and "splash" in st.query_params:
                del st.query_params["splash"]
        except Exception:
            pass
        try:
            from core.sidebar import switch_to_page
            switch_to_page("pages/12_🎛️_Wealth_Control_Room.py")
        except Exception:
            pass

    with splash_container.container():
        cur_lang = (st.session_state.get("locale") or st.session_state.get("argus_locale") or "it").lower()
        is_it = (cur_lang == "it")

        # Iniezione stili CSS isolati in cima per applicazione immediata su tutti gli elementi
        st.markdown(SPLASH_STYLES, unsafe_allow_html=True)

        # Assicura che all'avvio la sidebar rimanga chiusa e le freccette nascoste
        auto_collapse_sidebar()

        # Barra superiore istituzionale perfettamente allineata al container
        top_cols = st.columns([4.4, 0.6])
        top_sp_c1 = top_cols[0]
        top_sp_c2 = top_cols[1] if len(top_cols) > 1 else top_cols[0]
        with top_sp_c1:
            desk_txt = "GATEWAY AMBIENTI" if is_it else "WORKSPACE GATEWAY"
            top_bar_status = _clean_html(f"""
            <div class="splash-sys-status">
                <span class="sys-pulse-dot"></span>
                <span class="sys-title">ARGUS QUANTITATIVE TERMINAL OS</span>
                <span class="sys-sep">•</span>
                <span class="sys-tag">v{app_version} Institutional</span>
                <span class="sys-sep">•</span>
                <span class="sys-mode">{desk_txt}</span>
            </div>
            """)
            st.markdown(top_bar_status, unsafe_allow_html=True)
        with top_sp_c2:
            lang_cols = st.columns(2, gap="small")
            sp_it = lang_cols[0]
            sp_en = lang_cols[1] if len(lang_cols) > 1 else lang_cols[0]
            with sp_it:
                if st.button("IT", key="btn_splash_toggle_it", type="primary" if is_it else "secondary", use_container_width=True):
                    st.session_state["locale"] = "it"
                    st.session_state["argus_locale"] = "it"
                    from core.i18n.translator import I18nEngine
                    I18nEngine.get_instance().set_locale("it")
                    st.rerun()
            with sp_en:
                if st.button("EN", key="btn_splash_toggle_en", type="primary" if not is_it else "secondary", use_container_width=True):
                    st.session_state["locale"] = "en"
                    st.session_state["argus_locale"] = "en"
                    from core.i18n.translator import I18nEngine
                    I18nEngine.get_instance().set_locale("en")
                    st.rerun()

        # Frame HTML istituzionale completo
        status_msg = "Seleziona l'Ambiente di Lavoro sottostante:" if is_it else "Select your operational workspace below:"
        html_frame = render_splash_html(
            app_title="A R G U S",
            subtitle="QUANTITATIVE RISK ANALYTICS & WEALTH INTELLIGENCE ECOSYSTEM",
            version_tag=f"v{app_version} Institutional",
            current_status=status_msg,
            progress_pct=100,
            accent_color="#f59e0b",
            is_fading_out=False,
            show_skip=False,
            locale=cur_lang,
        )
        st.markdown(html_frame, unsafe_allow_html=True)

        # Schede Bento Grid e Pulsanti di Accesso Istituzionale Fusi Insieme
        col_risk, col_wealth = st.columns(2)
        with col_risk:
            r_badge = "12 MODULI RISK &amp; QUANT" if is_it else "12 RISK &amp; QUANT MODULES"
            r_desc = (
                "Desk quantitativo istituzionale per asset pricing, stress testing sistemico e ottimizzazione di frontiera."
                if is_it else
                "Institutional quantitative desk for asset pricing, systemic stress testing, and frontier optimization."
            )
            r_f1 = "<b>Metriche di Coda:</b> VaR Storico/Parametrico (95/99%), CVaR &amp; EWMA" if is_it else "<b>Tail Metrics:</b> Historical/Parametric VaR (95/99%), CVaR &amp; EWMA"
            r_f2 = "<b>Stress Testing:</b> Scenari Storici 2008, Shock Tassi, Crolli Tech &amp; Tariffe" if is_it else "<b>Stress Testing:</b> 2008 Crisis, Rate Shocks, Tech Crashes &amp; Tariffs"
            r_f3 = "<b>Asset Allocation:</b> Markowitz, Black-Litterman, HRP &amp; Copule Matematiche" if is_it else "<b>Asset Allocation:</b> Markowitz, Black-Litterman, HRP &amp; Mathematical Copulas"
            r_f4 = "<b>Screener &amp; BQuant:</b> Multi-Factor Screener + Sandbox Python Integrata" if is_it else "<b>Screener &amp; BQuant:</b> Multi-Factor Screener + Integrated Python Sandbox"

            risk_card_html = _clean_html(f"""
            <div class="portal-card-risk">
                <div>
                    <div class="portal-card-header">
                        <span class="portal-card-title">📊 Risk Analytics &amp; Portfolios</span>
                        <span class="portal-badge-risk">{r_badge}</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; line-height: 1.45; margin-bottom: 7px;">
                        {r_desc}
                    </div>
                    <div class="portal-feature-list">
                        <div class="portal-feature-item"><span class="portal-tag-pill tag-risk">VaR</span> <span>{r_f1}</span></div>
                        <div class="portal-feature-item"><span class="portal-tag-pill tag-risk">STRESS</span> <span>{r_f2}</span></div>
                        <div class="portal-feature-item"><span class="portal-tag-pill tag-risk">ALLOC</span> <span>{r_f3}</span></div>
                        <div class="portal-feature-item"><span class="portal-tag-pill tag-risk">QUANT</span> <span>{r_f4}</span></div>
                    </div>
                </div>
            </div>
            """)
            st.markdown(risk_card_html, unsafe_allow_html=True)
            btn_risk_txt = "⚡ ENTRA NEL DESK RISK ANALYTICS →" if is_it else "⚡ ENTER RISK ANALYTICS DESK →"
            if st.button(btn_risk_txt, key="btn_splash_risk", use_container_width=True, on_click=_on_click_enter_risk):
                _on_click_enter_risk()
                splash_container.empty()
                st.rerun()

        with col_wealth:
            w_badge = "10 MODULI WEALTH &amp; ADVISORY" if is_it else "10 WEALTH &amp; ADVISORY MODULES"
            w_desc = (
                "Piattaforma di consolidamento olistico del patrimonio netto, budget familiare, caveau beni rifugio e fiscalità."
                if is_it else
                "Holistic balance sheet consolidation platform, family budgeting, safe-haven caveau, and taxation."
            )
            w_f1 = "<b>Net Worth Olistico:</b> Conti Correnti, Broker, Immobili &amp; Caveau Orologi" if is_it else "<b>Holistic Net Worth:</b> Bank Accounts, Brokers, Real Estate &amp; Watch Caveau"
            w_f2 = "<b>Cash Flow:</b> Framework 50/30/20, Burn Rate &amp; Proiezioni FIRE" if is_it else "<b>Cash Flow:</b> 50/30/20 Framework, Burn Rate &amp; FIRE Projections"
            w_f3 = "<b>Fisco &amp; Previdenza:</b> Monitoraggio Quadro RW (IVAFE/IVIE) &amp; Fondi Pensione" if is_it else "<b>Tax &amp; Pension:</b> Italian Quadro RW (IVAFE/IVIE) &amp; Pension Funds"
            w_f4 = "<b>Advisory Copilot:</b> Audit patrimoniale avanzato con motore quantitativo locale" if is_it else "<b>Advisory Copilot:</b> Advanced wealth audit with local quantitative engine"

            wealth_card_html = _clean_html(f"""
            <div class="portal-card-wealth">
                <div>
                    <div class="portal-card-header">
                        <span class="portal-card-title">🏛️ Wealth Management &amp; Advisory</span>
                        <span class="portal-badge-wealth">{w_badge}</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; line-height: 1.45; margin-bottom: 7px;">
                        {w_desc}
                    </div>
                    <div class="portal-feature-list">
                        <div class="portal-feature-item"><span class="portal-tag-pill tag-wealth">LEDGER</span> <span>{w_f1}</span></div>
                        <div class="portal-feature-item"><span class="portal-tag-pill tag-wealth">BUDGET</span> <span>{w_f2}</span></div>
                        <div class="portal-feature-item"><span class="portal-tag-pill tag-wealth">FISCO</span> <span>{w_f3}</span></div>
                        <div class="portal-feature-item"><span class="portal-tag-pill tag-wealth">COPILOT</span> <span>{w_f4}</span></div>
                    </div>
                </div>
            </div>
            """)
            st.markdown(wealth_card_html, unsafe_allow_html=True)
            btn_wealth_txt = "🏛️ ENTRA NELLA SUITE WEALTH ADVISORY →" if is_it else "🏛️ ENTER WEALTH ADVISORY SUITE →"
            if st.button(btn_wealth_txt, key="btn_splash_wealth", use_container_width=True, on_click=_on_click_enter_wealth):
                _on_click_enter_wealth()
                splash_container.empty()
                if not st.session_state.get("wealth_active_portfolio_id"):
                    auth_pid = st.session_state.get("argus_auth_personal_profile_id")
                    st.session_state["wealth_active_portfolio_id"] = auth_pid or 1
                from core.sidebar import switch_to_page
                switch_to_page("pages/12_🎛️_Wealth_Control_Room.py")

        try:
            from core.supabase_cloud import (
                SupabaseAuthManager,
                get_active_account_badge_info,
                logout_argus_user,
            )

            acct_splash = get_active_account_badge_info()
            disp_user_name = acct_splash.get("display_name", "Utente")
            cols_logout = st.columns([1.3, 1.4, 1.3])
            col_logout_sp = cols_logout[1] if len(cols_logout) >= 2 else cols_logout[0]
            with col_logout_sp:
                btn_out_txt = f"⇄ Cambia Account / Logout ({disp_user_name})" if is_it else f"⇄ Switch Account / Sign Out ({disp_user_name})"
                btn_out_hlp = "Disconnette la sessione corrente e riapre il terminale di Login ARGUS." if is_it else "Disconnects current session and reopens the ARGUS Sign In terminal."
                if st.button(
                    btn_out_txt,
                    key="btn_splash_switch_account",
                    use_container_width=True,
                    help=btn_out_hlp,
                ):
                    from core.auth_manager import AuthManager

                    splash_container.empty()
                    SupabaseAuthManager.set_security_settings(require_login=True)
                    logout_argus_user()
                    AuthManager.logout()
                    st.session_state["splash_dismissed"] = True
                    st.session_state["auth_view"] = "LOGIN"
                    st.session_state["require_login_forced"] = True
                    st.rerun()

            footer_watermark = (
                "🔒 SESSIONE IN MEMORIA CRITTOGRAFATA AES-256 • ZERO PERSISTENZA CLOUD NON AUTORIZZATA • ENGINE IBRIDO LOCALE/CLOUD"
                if is_it else
                "🔒 AES-256 ENCRYPTED MEMORY SESSION • ZERO UNAUTHORIZED CLOUD PERSISTENCE • HYBRID LOCAL/CLOUD KERNEL"
            )
            st.markdown(
                f'<div style="margin-top:10px; margin-bottom:4px; text-align:center; font-family:\'JetBrains Mono\', monospace; font-size:9.5px; color:#475569; letter-spacing:0.8px;">{footer_watermark}</div>',
                unsafe_allow_html=True,
            )
        except Exception:
            pass

    return True


# Alias di retrocompatibilita
show_splash_screen = render_splash_screen
