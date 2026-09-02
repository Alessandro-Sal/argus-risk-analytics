# ============================================================
# core/voice_advisor_engine.py
# ARGUS — AI Voice Executive Briefing & Wealth Audio Podcast
# Sintesi vocale automatica, copione a due voci (CIO & CRO) ed executive audio
# ============================================================

from typing import Dict, Any, List, Optional
from datetime import datetime


def generate_ai_voice_executive_briefing(
    engine: Any,
    portfolio_id: int = 1,
    client_name: str = "Family Office Master",
    speaker_mode: str = "dialogue"
) -> Dict[str, Any]:
    """
    Genera un executive audio briefing e copione broadcast a due voci (CIO & Chief Risk Officer)
    sincronizzato sui dati reali del patrimonio.
    """
    from core.wealth.wealth_engine import compute_consolidated_net_worth
    from core.macro_stress_engine import compute_macro_scenario_stress_test
    from core.esg_engine import compute_portfolio_esg_and_sfdr_metrics

    nw = compute_consolidated_net_worth(engine, portfolio_id=portfolio_id)
    stress = compute_macro_scenario_stress_test()
    esg = compute_portfolio_esg_and_sfdr_metrics()

    today_str = datetime.now().strftime("%d %B %Y")

    # Script a 2 voci (CIO e CRO)
    dialogue_script = [
        {
            "speaker": "CIO (Chief Investment Officer)",
            "voice": "en-US-Journey-F",
            "role": "Chief Investment Officer",
            "text": f"Buongiorno e benvenuti all'Executive Briefing ARGUS per {client_name}. Oggi, {today_str}, il nostro patrimonio netto consolidato si attesta a € {nw.total_net_worth:,.2f}, con una liquidità operativa pari a € {nw.liquid_cash:,.2f} e un Wealth Health Score solido di {nw.wealth_health_score:.0f} su 100."
        },
        {
            "speaker": "CRO (Chief Risk Officer)",
            "voice": "en-US-Journey-D",
            "role": "Chief Risk Officer",
            "text": f"Grazie. Sul fronte della gestione del rischio, la nostra esposizione globale rimane sotto controllo. I test di stress macroeconomico EBA indicano un drawdown massimo stimato del {stress['worst_case_drawdown_pct']:.1f}% nello scenario più avverso, ampiamente sostenibile dal cuscinetto di liquidità che garantisce {nw.runway_months:.1f} mesi di autonomia."
        },
        {
            "speaker": "CIO (Chief Investment Officer)",
            "voice": "en-US-Journey-F",
            "role": "Chief Investment Officer",
            "text": f"Ottimo. Inoltre, sul piano della sostenibilità e dei mandati ESG, il portafoglio mantiene una qualifica eccellente con un punteggio di {esg['portfolio_esg_score']}/100 e un'intensità carbonica di soli {esg['weighted_carbon_intensity_tco2e_per_m_eur']:.1f} tonnellate di CO2 per milione investito, con una netta prevalenza di fondi Articolo 8 e 9 SFDR."
        },
        {
            "speaker": "CRO (Chief Risk Officer)",
            "voice": "en-US-Journey-D",
            "role": "Chief Risk Officer",
            "text": "Le raccomandazioni tattiche per questa settimana includono il mantenimento della copertura asimmetrica e l'esecuzione del ribilanciamento automatico per ottimizzare le plusvalenze fiscali in scadenza. Buona prosecuzione e al prossimo aggiornamento."
        }
    ]

    # Testo continuo per sintetizzatore vocale singolo (Solo Voice)
    solo_text = " ".join([d["speaker"].split()[0] + ": " + d["text"] for d in dialogue_script])

    # Calcolo durata stimata (media 140 parole al minuto)
    word_count = sum(len(d["text"].split()) for d in dialogue_script)
    duration_seconds = int((word_count / 140.0) * 60.0)

    return {
        "title": f"ARGUS Executive Audio Briefing — {client_name}",
        "as_of_date": today_str,
        "total_net_worth_eur": nw.total_net_worth,
        "estimated_duration_seconds": duration_seconds,
        "estimated_duration_formatted": f"{duration_seconds // 60}m {duration_seconds % 60}s",
        "word_count": word_count,
        "dialogue_script": dialogue_script,
        "full_text_transcript": solo_text
    }
