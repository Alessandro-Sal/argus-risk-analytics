import pandas as pd
import numpy as np

def generate_quant_advisory_report(results: dict) -> dict:
    """
    Motore di Diagnostica Quantitativa & ARGUS Quant Advisor.
    Scansiona il portafoglio alla ricerca di anomalie di rischio, concentrazione,
    valutazioni e opportunità di ottimizzazione dello Sharpe Ratio.
    
    Returns
    -------
    dict con 'health_score' (0-100), 'diagnostics' (list of dicts), 'summary' (dict)
    """
    if not results or not isinstance(results, dict):
        return {
            "health_score": 100,
            "diagnostics": [],
            "summary": {"hhi": 0.0, "top3_weight_pct": 0.0, "sharpe_ratio": 0.0, "beta": 1.0, "volatility_annual_pct": 15.0}
        }

    m = results.get("metrics", {}) or {}
    ret = m.get("returns", {}) or {}
    mk = m.get("market_risk", {}) or {}
    con = m.get("concentration", {}) or {}
    pos_raw = results.get("positions", pd.DataFrame())
    if isinstance(pos_raw, pd.DataFrame) and not pos_raw.empty and "qty_net" in pos_raw.columns:
        pos = pos_raw[pos_raw["qty_net"] > 0].copy()
    elif isinstance(pos_raw, pd.DataFrame):
        pos = pos_raw.copy()
    else:
        pos = pd.DataFrame()

    risk_contrib = results.get("risk_contribution", {}) or {}
    opt = results.get("optimization") or {}

    diagnostics = []
    health_score = 100

    # 1. Diagnostica Concentrazione (HHI & Top 3 Asset)
    hhi = float(con.get("hhi") or 0.0) if con.get("hhi") is not None else 0.0
    eff_n = float(con.get("effective_n_assets") or 1.0) if con.get("effective_n_assets") is not None else 1.0
    
    if not pos.empty and "weight_pct" in pos.columns:
        pos_sorted = pos.sort_values(by="weight_pct", ascending=False)
        top3_weight = float(pos_sorted.head(3)["weight_pct"].sum() or 0.0)
        top1_row = pos_sorted.iloc[0]
        top1_ticker = str(top1_row["ticker"])
        top1_weight = float(top1_row["weight_pct"] or 0.0)
    else:
        top3_weight = 0.0
        top1_ticker = "N/A"
        top1_weight = 0.0

    if hhi > 0.25 or top3_weight > 50.0:
        health_score -= 15
        diagnostics.append({
            "type": "WARNING",
            "category": "Concentrazione Asset",
            "title": f"Alta Concentrazione di Portafoglio (Top 3 = {top3_weight:.1f}%)",
            "description": f"Il portafoglio mostra un'alta concentrazione. Il titolo più pesante **{top1_ticker}** rappresenta da solo il **{top1_weight:.1f}%** del patrimonio totale. L'Indice di Herfindahl (HHI) è {hhi:.4f}.",
            "actionable_recommendation": f"Considera di prendere profitto o ridurre il peso di {top1_ticker} al di sotto del 15-20% per diversificare il rischio idiosincratico.",
            "page_target": "pages/4_📋_Posizioni_e_Dettagli.py",
            "page_label": "📋 Vai alla Gestione Posizioni & Pesi",
            "page_icon": "📋"
        })
    elif hhi < 0.10 and not pos.empty:
        diagnostics.append({
            "type": "SUCCESS",
            "category": "Concentrazione Asset",
            "title": "Diversificazione di Portafoglio Eccellente",
            "description": f"Il numero di asset effettivi è {eff_n:.1f} con un HHI di {hhi:.4f}, indicando un'ottima distribuzione del capitale.",
            "actionable_recommendation": "Mantieni l'attuale strategia di allocazione bilanciata."
        })

    # 2. Diagnostica Contributo al Rischio (Component VaR > 25%)
    comp_var = risk_contrib.get("component_var_pct", {}) if isinstance(risk_contrib, dict) else {}
    active_tickers = set(pos["ticker"].tolist()) if not pos.empty and "ticker" in pos.columns else set()
    high_risk_contributors = []
    if isinstance(comp_var, dict):
        for tk, cvar_val in comp_var.items():
            if tk in active_tickers and cvar_val is not None:
                try:
                    cvar_f = float(cvar_val)
                    if cvar_f > 25.0:
                        high_risk_contributors.append((tk, cvar_f))
                except (ValueError, TypeError):
                    pass

    if high_risk_contributors:
        health_score -= 15
        risk_str = ", ".join([f"**{tk}** ({cvar:.1f}% del VaR)" for tk, cvar in high_risk_contributors])
        diagnostics.append({
            "type": "CRITICAL",
            "category": "Contributo al Rischio (VaR)",
            "title": "Concentrazione del Rischio Estremo (Component VaR)",
            "description": f"I seguenti titoli generano una quota sproporzionata del rischio di perdita totale: {risk_str}.",
            "actionable_recommendation": "Riduci l'esposizione sui titoli a più alta volatilità marginale o inserisci una copertura (hedging).",
            "page_target": "pages/2_🔴_Analisi_Rischio.py",
            "page_label": "🔴 Analizza Component VaR & Coperture (Hedging)",
            "page_icon": "🔴"
        })

    # 3. Diagnostica Efficienza Markowitz & Sharpe Ratio
    curr_sharpe = float(ret.get("sharpe_ratio") or 0.0) if ret.get("sharpe_ratio") is not None else 0.0
    if isinstance(opt, dict) and opt.get("max_sharpe"):
        opt_sharpe = float(opt["max_sharpe"].get("sharpe") or 0.0) if opt["max_sharpe"].get("sharpe") is not None else 0.0
        sharpe_delta = opt_sharpe - curr_sharpe
        if sharpe_delta > 0.3:
            health_score -= 10
            diagnostics.append({
                "type": "INFO",
                "category": "Efficienza Quantitativa",
                "title": f"Opportunità di Ottimizzazione Sharpe (+{sharpe_delta:.2f})",
                "description": f"L'attuale Sharpe Ratio ({curr_sharpe:.2f}) può essere incrementato fino a **{opt_sharpe:.2f}** riallineando i pesi alla Frontiera Efficiente di Markowitz.",
                "actionable_recommendation": "Usa il Simulatore di Ribilanciamento per applicare la combinazione a Sharpe Massimo.",
                "page_target": "pages/3_🔬_Modelli_Quantitativi.py",
                "page_label": "🔬 Apri Ottimizzatore Markowitz & Simulatore di Ribilanciamento",
                "page_icon": "🔬"
            })

    # 4. Diagnostica Valutazioni Fondamentali (P/E Elevati o Payout Rischiosi)
    if not pos.empty and "trailing_pe" in pos.columns:
        pe_series = pd.to_numeric(pos["trailing_pe"], errors="coerce")
        expensive_stocks = pos[pe_series > 45]
        if not expensive_stocks.empty:
            exp_tickers = ", ".join([f"**{r['ticker']}** (P/E: {float(r['trailing_pe']):.1f})" for _, r in expensive_stocks.iterrows() if pd.notna(r.get('trailing_pe'))])
            if exp_tickers:
                diagnostics.append({
                    "type": "WARNING",
                    "category": "Valutazioni Fondamentali",
                    "title": "Moltiplicatori P/E su Livelli Elevati",
                    "description": f"I seguenti titoli in portafoglio scambiano a multipli P/E superiori a 45x: {exp_tickers}.",
                    "actionable_recommendation": "Verifica se la crescita degli utili attesa giustifica i multipli attuali o imposta stop-loss prudenziali.",
                    "page_target": "pages/5_🏛️_Valutazione_Aziendale.py",
                    "page_label": "🏛️ Analisi Fondamentale Fair Value & Multipli",
                    "page_icon": "🏛️"
                })

    # 5. Diagnostica Beta & Volatilità di Mercato
    beta_raw = mk.get("beta")
    try:
        beta = float(beta_raw) if beta_raw is not None else 1.0
    except (ValueError, TypeError):
        beta = 1.0

    vol_raw = mk.get("volatility_annual_pct")
    try:
        vol = float(vol_raw) if vol_raw is not None else 15.0
    except (ValueError, TypeError):
        vol = 15.0

    if beta > 1.3:
        diagnostics.append({
            "type": "WARNING",
            "category": "Rischio di Mercato",
            "title": f"Profilo Aggressivo (Beta = {beta:.2f})",
            "description": f"Il portafoglio amplia i movimenti del mercato del **{((beta - 1) * 100):.0f}%**. In caso di storno dell'indice, le perdite saranno amplificate.",
            "actionable_recommendation": "Valuta l'inserimento di asset difensivi (es. bond, gold o titoli value) per ridurre il Beta complessivo verso 1.0.",
            "page_target": "pages/6_🌪️_Stress_Testing.py",
            "page_label": "🌪️ Esegui Stress Test & Simulazione Shock Macro",
            "page_icon": "🌪️"
        })
    elif beta < 0.7:
        diagnostics.append({
            "type": "INFO",
            "category": "Rischio di Mercato",
            "title": f"Profilo Difensivo (Beta = {beta:.2f})",
            "description": f"Il portafoglio ha una bassa sensibilità alle oscillazioni del mercato principale.",
            "actionable_recommendation": "Adatto per la preservazione del capitale nelle fasi di elevata incertezza."
        })

    # Clamp health score 0-100
    health_score = max(0, min(100, health_score))

    return {
        "health_score": int(round(health_score)),
        "diagnostics": diagnostics,
        "summary": {
            "hhi": hhi,
            "top3_weight_pct": top3_weight,
            "sharpe_ratio": curr_sharpe,
            "beta": beta,
            "volatility_annual_pct": vol
        }
    }
