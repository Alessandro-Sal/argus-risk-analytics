"""
====================================================================
MODULO: components/splash.py
DESCRIZIONE: Launch Screen & Bootloader Istituzionale per Streamlit
DESIGN: Dark Obsidian / Glassmorphism / SVG Vettoriale a 60 FPS
====================================================================
"""

import time
from typing import Callable, List, Tuple, Optional
import streamlit as st


def get_animated_logo_svg(size: int = 120, accent_color: str = "#f59e0b") -> str:
    """Genera un logo SVG vettoriale animato con reticoli concentrici e scanner."""
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" class="splash-logo-svg">
        <defs>
            <radialGradient id="splashIrisGrad" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#ffffff" stop-opacity="0.95"/>
                <stop offset="35%" stop-color="{accent_color}" stop-opacity="0.85"/>
                <stop offset="70%" stop-color="#b45309" stop-opacity="0.5"/>
                <stop offset="100%" stop-color="#090d16" stop-opacity="0.95"/>
            </radialGradient>
            <filter id="splashGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feComposite in="SourceGraphic" in2="blur" operator="over"/>
            </filter>
        </defs>
        <g filter="url(#splashGlow)">
            <circle cx="100" cy="100" r="90" fill="none" stroke="{accent_color}" stroke-width="1.2" stroke-opacity="0.3" stroke-dasharray="6, 8" class="svg-rot-cw"/>
            <circle cx="100" cy="10" r="3.5" fill="{accent_color}" class="svg-rot-cw"/>
            <circle cx="190" cy="100" r="3.5" fill="{accent_color}" class="svg-rot-cw"/>
            <circle cx="100" cy="190" r="3.5" fill="{accent_color}" class="svg-rot-cw"/>
            <circle cx="10" cy="100" r="3.5" fill="{accent_color}" class="svg-rot-cw"/>
            <circle cx="100" cy="100" r="72" fill="none" stroke="{accent_color}" stroke-width="1.6" stroke-opacity="0.45" stroke-dasharray="14, 8, 4, 8" class="svg-rot-ccw"/>
            <path d="M 24 100 Q 100 42 176 100 Q 100 158 24 100 Z" fill="rgba(10, 15, 26, 0.85)" stroke="{accent_color}" stroke-width="2" stroke-opacity="0.9"/>
            <circle cx="100" cy="100" r="36" fill="url(#splashIrisGrad)" stroke="{accent_color}" stroke-width="1.5"/>
            <circle cx="100" cy="100" r="16" fill="#ffffff" class="svg-core-pulse"/>
            <line x1="45" y1="65" x2="155" y2="65" stroke="{accent_color}" stroke-width="2" stroke-linecap="round" class="svg-scan-beam" opacity="0.85"/>
        </g>
    </svg>
    """


def get_splash_styles(accent_color: str = "#f59e0b") -> str:
    """Restituisce le regole CSS per l'overlay fullscreen, le animazioni a 60 FPS e il glassmorphism."""
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Outfit:wght@400;600;700;800;900&display=swap');

        section[data-testid="stSidebar"], 
        [data-testid="stSidebar"], 
        [data-testid="collapsedControl"],
        header[data-testid="stHeader"] {{
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
        }}

        #splash-screen-root {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: radial-gradient(circle at 50% 30%, #151e2e 0%, #0a0e17 55%, #05070b 100%);
            z-index: 999999;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            font-family: 'Outfit', -apple-system, sans-serif;
            overflow: hidden;
            transition: opacity 0.75s cubic-bezier(0.16, 1, 0.3, 1), 
                        transform 0.75s cubic-bezier(0.16, 1, 0.3, 1),
                        backdrop-filter 0.75s ease;
            will-change: opacity, transform;
        }}

        #splash-screen-root.splash-fade-out {{
            opacity: 0 !important;
            transform: scale(1.03) !important;
            pointer-events: none !important;
        }}

        .splash-ambient-glow {{
            position: absolute;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, {accent_color}18 0%, rgba(0,0,0,0) 70%);
            filter: blur(80px);
            z-index: -1;
            animation: pulseGlow 5s ease-in-out infinite;
        }}

        .splash-card {{
            position: relative;
            width: 90%;
            max-width: 520px;
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-top: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 24px;
            padding: 36px 32px 30px;
            box-shadow: 0 32px 64px -16px rgba(0, 0, 0, 0.85),
                        0 0 40px {accent_color}1a;
            backdrop-filter: blur(28px);
            -webkit-backdrop-filter: blur(28px);
            text-align: center;
        }}

        .splash-title {{
            font-size: 32px;
            font-weight: 900;
            letter-spacing: 8px;
            color: #ffffff;
            margin: 18px 0 4px;
            text-transform: uppercase;
            background: linear-gradient(135deg, #ffffff 40%, {accent_color} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .splash-subtitle {{
            font-size: 11px;
            font-weight: 700;
            color: {accent_color};
            letter-spacing: 3px;
            text-transform: uppercase;
            margin-bottom: 16px;
        }}

        .splash-badge-ribbon {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            margin-bottom: 22px;
        }}

        .splash-pill {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 10.5px;
            font-weight: 600;
            color: #94a3b8;
            font-family: 'JetBrains Mono', monospace;
        }}

        .splash-terminal {{
            background: rgba(8, 12, 20, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 10px 14px;
            margin-bottom: 20px;
            text-align: left;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #38bdf8;
            display: flex;
            align-items: center;
            gap: 10px;
            min-height: 42px;
            box-shadow: inset 0 2px 6px rgba(0,0,0,0.5);
        }}

        .terminal-cursor {{
            display: inline-block;
            width: 7px;
            height: 13px;
            background-color: {accent_color};
            animation: blink 0.8s infinite;
        }}

        .splash-progress-track {{
            position: relative;
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 999px;
            overflow: hidden;
            margin-bottom: 10px;
        }}

        .splash-progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #d97706 0%, {accent_color} 50%, #ffffff 100%);
            border-radius: 999px;
            box-shadow: 0 0 16px {accent_color};
            transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .splash-progress-meta {{
            display: flex;
            justify-content: space-between;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10.5px;
            color: #64748b;
            font-weight: 500;
        }}

        .svg-rot-cw {{ transform-origin: 100px 100px; animation: spinCW 18s linear infinite; }}
        .svg-rot-ccw {{ transform-origin: 100px 100px; animation: spinCCW 12s linear infinite; }}
        .svg-core-pulse {{ transform-origin: 100px 100px; animation: pulseCore 2.4s ease-in-out infinite; }}
        .svg-scan-beam {{ animation: scanVertical 2.2s ease-in-out infinite; }}

        @keyframes spinCW {{ 100% {{ transform: rotate(360deg); }} }}
        @keyframes spinCCW {{ 100% {{ transform: rotate(-360deg); }} }}
        @keyframes pulseCore {{ 0%, 100% {{ transform: scale(1); opacity: 0.9; }} 50% {{ transform: scale(1.15); opacity: 1; }} }}
        @keyframes scanVertical {{ 0%, 100% {{ transform: translateY(0); opacity: 0.2; }} 50% {{ transform: translateY(68px); opacity: 0.9; }} }}
        @keyframes pulseGlow {{ 0%, 100% {{ opacity: 0.4; transform: scale(1); }} 50% {{ opacity: 0.8; transform: scale(1.1); }} }}
        @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
    </style>
    """


def render_card_html(
    app_title: str,
    subtitle: str,
    version_tag: str,
    current_status: str,
    progress_pct: int,
    accent_color: str,
    is_fading_out: bool = False,
) -> str:
    """Costruisce la stringa HTML completa per il frame dello splash screen."""
    fade_class = "splash-fade-out" if is_fading_out else ""
    logo_svg = get_animated_logo_svg(size=115, accent_color=accent_color)

    return f"""
    <div id="splash-screen-root" class="{fade_class}">
        <div class="splash-ambient-glow"></div>
        <div class="splash-card">
            <div>{logo_svg}</div>
            <div class="splash-title">{app_title}</div>
            <div class="splash-subtitle">{subtitle}</div>
            
            <div class="splash-badge-ribbon">
                <span class="splash-pill">🟢 <b>{version_tag}</b></span>
                <span class="splash-pill">🔒 Zero-Cloud Security</span>
                <span class="splash-pill">⚡ Engine Ready</span>
            </div>

            <div class="splash-terminal">
                <span style="color: {accent_color}; font-weight: 700;">&gt;</span>
                <span style="flex-grow: 1;">{current_status}</span>
                <span class="terminal-cursor"></span>
            </div>

            <div class="splash-progress-track">
                <div class="splash-progress-fill" style="width: {progress_pct}%;"></div>
            </div>

            <div class="splash-progress-meta">
                <span>INIZIALIZZAZIONE KERNEL</span>
                <span>{progress_pct}%</span>
            </div>
        </div>
    </div>
    """


def show_splash_screen(
    app_title: str = "A R G U S",
    subtitle: str = "QUANTITATIVE RISK & WEALTH ECOSYSTEM",
    version_tag: str = "v6.0.0 Institutional",
    accent_color: str = "#f59e0b",
    boot_tasks: Optional[List[Tuple[str, Callable[[], None]]]] = None,
    min_step_duration: float = 0.35,
    force_show: bool = False,
) -> None:
    """
    Esegue lo Splash Screen di avvio una sola volta per sessione utente.
    """
    if "splash_completed" not in st.session_state:
        st.session_state.splash_completed = False

    if force_show:
        st.session_state.splash_completed = False

    if st.session_state.splash_completed:
        return

    if boot_tasks is None:
        boot_tasks = [
            ("Caricamento configurazioni di sistema & parametri quant...", lambda: time.sleep(0.35)),
            ("Verifica integrità database SQLite & DuckDB Storage...", lambda: time.sleep(0.40)),
            ("Riscaldamento Cache Shield & Connessioni API...", lambda: time.sleep(0.35)),
            ("Calcolo metriche di rischio & Portali Pronti...", lambda: time.sleep(0.30)),
        ]

    total_tasks = len(boot_tasks)
    placeholder = st.empty()

    st.markdown(get_splash_styles(accent_color=accent_color), unsafe_allow_html=True)

    for idx, (status_text, task_fn) in enumerate(boot_tasks):
        pct = int(((idx) / total_tasks) * 100)
        
        html_code = render_card_html(
            app_title=app_title,
            subtitle=subtitle,
            version_tag=version_tag,
            current_status=status_text,
            progress_pct=pct,
            accent_color=accent_color,
            is_fading_out=False,
        )
        placeholder.markdown(html_code, unsafe_allow_html=True)

        start_t = time.time()
        try:
            if callable(task_fn):
                task_fn()
        except Exception as e:
            print(f"[SPLASH WARNING] Errore task '{status_text}': {e}")
        
        elapsed = time.time() - start_t
        if elapsed < min_step_duration:
            time.sleep(min_step_duration - elapsed)

    final_html = render_card_html(
        app_title=app_title,
        subtitle=subtitle,
        version_tag=version_tag,
        current_status="Sistema pronto. Accesso alla Control Room...",
        progress_pct=100,
        accent_color="#10b981",
        is_fading_out=False,
    )
    placeholder.markdown(final_html, unsafe_allow_html=True)
    time.sleep(0.3)

    fade_html = render_card_html(
        app_title=app_title,
        subtitle=subtitle,
        version_tag=version_tag,
        current_status="Sistema pronto. Accesso alla Control Room...",
        progress_pct=100,
        accent_color="#10b981",
        is_fading_out=True,
    )
    placeholder.markdown(fade_html, unsafe_allow_html=True)
    time.sleep(0.45)

    placeholder.empty()
    st.session_state.splash_completed = True
    st.rerun()
