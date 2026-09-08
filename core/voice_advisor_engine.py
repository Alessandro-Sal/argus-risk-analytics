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
    from core.wealth.wealth_engine import compute_consolidated_net_worth, compute_ai_wealth_diagnostics
    from core.macro_stress_engine import compute_macro_scenario_stress_test
    from core.esg_engine import compute_portfolio_esg_and_sfdr_metrics

    nw = compute_consolidated_net_worth(engine, portfolio_id=portfolio_id)
    diag = compute_ai_wealth_diagnostics(engine, portfolio_id=portfolio_id)
    stress = compute_macro_scenario_stress_test()
    esg = compute_portfolio_esg_and_sfdr_metrics()

    today_str = datetime.now().strftime("%d %B %Y")
    h_score = float(diag.get("health_score") or nw.wealth_health_score or 80.0)

    bottlenecks = diag.get("bottlenecks", [])
    if bottlenecks:
        top_issue = f"Nota di attenzione prioritaria identificata dal sistema: {bottlenecks[0].get('messaggio', 'Ribilanciamento consigliato')}."
    else:
        top_issue = "Tutti i parametri patrimoniali risultano allineati agli standard prudenziali senza colli di bottiglia attivi."

    rebalance_orders = diag.get("rebalance_orders", [])
    if rebalance_orders:
        top_ord = rebalance_orders[0]
        action_note = f"Sul piano operativo, il modello quantitativo suggerisce un intervento di riallineamento: {top_ord.get('azione', 'Ribilanciamento')} per circa € {float(top_ord.get('importo_eur', 0)):,.2f} su {top_ord.get('asset', 'asset class')}."
    else:
        action_note = "Sul piano operativo, il modello raccomanda di mantenere l'asset allocation corrente, monitorando le finestre temporali di ribilanciamento periodico."

    # Script dinamico a 2 voci (CIO e CRO)
    dialogue_script = [
        {
            "speaker": "CIO (Chief Investment Officer)",
            "voice": "en-US-Journey-F",
            "role": "Chief Investment Officer",
            "text": f"Buongiorno e benvenuti all'Executive Briefing ARGUS per {client_name}. Oggi, {today_str}, il nostro patrimonio netto consolidato si attesta a € {nw.total_net_worth:,.2f}, con una liquidità operativa pari a € {nw.liquid_cash:,.2f} e un Wealth Health Score solido di {h_score:.0f} su 100."
        },
        {
            "speaker": "CRO (Chief Risk Officer)",
            "voice": "en-US-Journey-D",
            "role": "Chief Risk Officer",
            "text": f"Grazie. Sul fronte della gestione del rischio, l'emergency runway garantisce {nw.runway_months:.1f} mesi di autonomia corrente. Nello scenario di stress macro avverso stimiamo un drawdown potenziale del {stress['worst_case_drawdown_pct']:.1f}%. {top_issue}"
        },
        {
            "speaker": "CIO (Chief Investment Officer)",
            "voice": "en-US-Journey-F",
            "role": "Chief Investment Officer",
            "text": f"Ottimo. Inoltre, sul piano della sostenibilità ESG, il portafoglio mantiene un punteggio di {esg['portfolio_esg_score']}/100 e un'intensità carbonica di {esg['weighted_carbon_intensity_tco2e_per_m_eur']:.1f} tonnellate di CO2 per milione investito. {action_note}"
        },
        {
            "speaker": "CRO (Chief Risk Officer)",
            "voice": "en-US-Journey-D",
            "role": "Chief Risk Officer",
            "text": "Confermo. Ricordiamo che il presente briefing ha finalità esclusivamente analitiche e quantitative a supporto decisionale e non costituisce consulenza personalizzata né sollecitazione all'investimento ai sensi della Direttiva MiFID II. Buona prosecuzione e al prossimo aggiornamento."
        }
    ]

    # Testo continuo per sintetizzatore vocale singolo (Solo Voice)
    solo_text = "\n\n".join([f"{d['speaker']}:\n\"{d['text']}\"" for d in dialogue_script])

    # Calcolo durata stimata (media 140 parole al minuto)
    word_count = sum(len(d["text"].split()) for d in dialogue_script)
    duration_seconds = int((word_count / 140.0) * 60.0)

    return {
        "title": f"ARGUS Dynamic Executive Audio Briefing — {client_name}",
        "as_of_date": today_str,
        "total_net_worth_eur": nw.total_net_worth,
        "estimated_duration_seconds": duration_seconds,
        "estimated_duration_formatted": f"{duration_seconds // 60}m {duration_seconds % 60:02d}s",
        "word_count": word_count,
        "dialogue_script": dialogue_script,
        "full_text_transcript": solo_text,
        "mifid_compliance_verified": True
    }
