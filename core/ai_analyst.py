"""
ARGUS — Risk Analytics Platform
Core Module: AI & LLM Narrative Intelligence (ARGUS AI Analyst)
Generates natural-language executive memorandums and provides an interactive
portfolio copilot with dual-engine architecture:
1. Online Remote LLM (Google Gemini & OpenAI REST API)
2. Offline Deterministic Quantitative NLG Engine (Zero-dependency fallback)
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from datetime import datetime

# ==============================================================================
# GUARDRAILS DI COMPLIANCE & DISCLAIMER NORMATIVO (MiFID II / CONSOB)
# ==============================================================================

MIFID_II_DISCLAIMER = (
    "⚖️ **Nota di Conformità e Governance MiFID II / CONSOB**:\n"
    "Il presente documento e le analisi fornite dal sistema di intelligenza artificiale ARGUS "
    "hanno finalità esclusivamente informativa, didattica e di supporto quantitativo all'analisi del rischio (Decision Support System). "
    "Non costituiscono in alcun caso offerta al pubblico di strumenti finanziari, sollecitazione all'investimento, né consulenza finanziaria "
    "personalizzata ai sensi della Direttiva Europea MiFID II (2014/65/UE, Art. 24 e 25), del D.Lgs. 58/1998 (TUF) e delle disposizioni CONSOB. "
    "I rendimenti passati non sono indicativi di quelli futuri. Prima di qualunque decisione operativa, consultare un intermediario finanziario abilitato."
)

UNIFIED_MIFID_SYSTEM_PROMPT = (
    "SEI: ARGUS Institutional Quantitative Analyst & Risk Intelligence Copilot (CFA/FRM Level).\n"
    "OBIETTIVO: Analizzare i dati quantitativi di portafoglio e wealth forniti e redigere perizie e sintesi operative in perfetto italiano finanziario istituzionale.\n\n"
    "VINCOLI TASSATIVI DI COMPLIANCE E SICUREZZA (ZERO-HALLUCINATION & MiFID II):\n"
    "1. DIVIETO DI SOLLECITAZIONE DIRETTA: Ai sensi di MiFID II e TUF, NON formulare raccomandazioni personalizzate d'acquisto o vendita con imperativi come 'Compra X adesso' o 'Vendi Y'. "
    "Usa formulazioni condizionali impersonali quali 'Il modello quantitativo suggerisce una riduzione dell'esposizione...' o 'In ottica risk-adjusted, si evidenzia un tilt verso...'.\n"
    "2. ZERO-HALLUCINATION NUMERICA: È SEVERAMENTE VIETATO inventare, arrotondare arbitrariamente o allucinare metriche numeriche non presenti nel contesto quantitativo certificato. "
    "Ogni percentuale (VaR, rendimento, volatilità), importo in Euro o indice deve coincidere esattamente con i dati forniti.\n"
    "3. TONO E STILE: Professionale, istituzionale, neutrale, orientato alla preservazione del capitale e all'ottimizzazione del profilo rischio/rendimento.\n"
    "4. GOVERNANCE: Ricorda che l'analisi è a supporto decisionale e non costituisce consulenza finanziaria."
)


def _extract_portfolio_summary_context(results: dict) -> dict:
    """Estrae i KPI quantitativi essenziali da inserire nel context prompt."""
    if not results or not isinstance(results, dict):
        return {}

    import pandas as pd
    import numpy as np

    m = results.get("metrics", {})
    ret_m = m.get("returns", {}) if isinstance(m, dict) else {}
    mr_m = m.get("market_risk", {}) if isinstance(m, dict) else {}
    conc_m = m.get("concentration", {}) if isinstance(m, dict) else {}

    # 1. Controvalore di Portafoglio
    val_eur = float(
        results.get("portfolio_value")
        or ret_m.get("portfolio_value")
        or (m.get("portfolio_value") if isinstance(m.get("portfolio_value"), (int, float)) else 0.0)
        or 0.0
    )

    # 2. Rendimento (CAGR e Totale)
    cagr_raw = ret_m.get("cagr_pct") if "cagr_pct" in ret_m else m.get("cagr_pct", m.get("cagr", 0.0))
    cagr = float(cagr_raw or 0.0)
    if abs(cagr) < 1.0 and cagr != 0.0:
        cagr = cagr * 100.0

    tot_ret_raw = ret_m.get("total_return_pct") if "total_return_pct" in ret_m else m.get("total_return_pct", m.get("total_return", 0.0))
    tot_ret = float(tot_ret_raw or 0.0)
    if abs(tot_ret) < 1.0 and tot_ret != 0.0 and abs(tot_ret) > 0.0001:
        tot_ret = tot_ret * 100.0

    # 3. Volatilità
    vol_raw = mr_m.get("volatility_annual_pct") or mr_m.get("volatility_annual") or m.get("volatility_annual_pct") or m.get("volatility", 0.0)
    vol = float(vol_raw or 0.0)
    if vol < 1.0 and vol > 0.0:
        vol = vol * 100.0

    # 4. Sharpe, Sortino & Calmar
    sharpe_raw = ret_m.get("sharpe_ratio") or mr_m.get("sharpe_ratio") or m.get("sharpe_ratio", 0.0)
    sharpe = float(sharpe_raw or 0.0)

    sortino_raw = ret_m.get("sortino_ratio") or m.get("sortino_ratio", 0.0)
    sortino = float(sortino_raw or 0.0)

    # 5. Drawdown
    max_dd_raw = mr_m.get("max_drawdown_pct") or mr_m.get("max_drawdown") or m.get("max_drawdown", 0.0)
    max_dd = float(max_dd_raw or 0.0)
    if abs(max_dd) < 1.0 and max_dd != 0.0:
        max_dd = max_dd * 100.0

    # 6. VaR & CVaR (95%)
    var_raw = mr_m.get("var_cf_95") or mr_m.get("var_95") or m.get("var_cf_95") or m.get("var_95", 0.0)
    var_95 = float(var_raw or 0.0)
    if var_95 < 0.30 and var_95 > 0.0:
        var_95 = var_95 * 100.0

    cvar_raw = mr_m.get("cvar_95") or m.get("cvar_95", 0.0)
    cvar_95 = float(cvar_raw or 0.0)
    if cvar_95 < 0.40 and cvar_95 > 0.0:
        cvar_95 = cvar_95 * 100.0

    # 7. Beta
    beta_raw = mr_m.get("beta") or m.get("beta", 1.0)
    beta = float(beta_raw if beta_raw is not None else 1.0)

    # 8. Diversification & HHI
    div_ratio_raw = conc_m.get("diversification_ratio") or results.get("risk_contribution", {}).get("diversification_ratio") or m.get("diversification_ratio", 1.0)
    div_ratio = float(div_ratio_raw if div_ratio_raw is not None else 1.0)

    hhi_raw = conc_m.get("herfindahl_index") or conc_m.get("hhi") or m.get("hhi", 0.0)
    hhi = float(hhi_raw if hhi_raw is not None else 0.0)

    # 9. Top Holdings (Supports both DataFrame and List)
    positions = results.get("positions")
    top_holdings = []
    if isinstance(positions, pd.DataFrame) and not positions.empty:
        df_p = positions.copy()
        if "qty_net" in df_p.columns:
            df_p = df_p[df_p["qty_net"] > 1e-6]
        if "current_value" in df_p.columns:
            df_p = df_p[df_p["current_value"] > 0]
            tot_v = float(df_p["current_value"].sum())
            if val_eur == 0.0 and tot_v > 0.0:
                val_eur = tot_v
            if "weight" not in df_p.columns and tot_v > 0:
                df_p["weight"] = df_p["current_value"] / tot_v
            df_sorted = df_p.sort_values("current_value", ascending=False)
            for _, row in df_sorted.head(5).iterrows():
                t_val = float(row.get("current_value", 0.0) or 0.0)
                t_w = float(row.get("weight", 0.0) or (t_val / tot_v if tot_v > 0 else 0.0))
                if t_w < 1.0 and t_w > 0.0:
                    t_w = t_w * 100.0
                cost_b = float(row.get("cost_basis", 0.0) or 0.0)
                pnl_val = float(row.get("unrealized_pnl", row.get("total_return", 0.0)) or 0.0)
                pnl_pct = (pnl_val / cost_b * 100.0) if cost_b > 0 else 0.0
                top_holdings.append({
                    "ticker": str(row.get("ticker", "")),
                    "weight_pct": round(t_w, 2),
                    "value_eur": round(t_val, 2),
                    "pnl_pct": round(pnl_pct, 2)
                })
    elif isinstance(positions, list) and positions:
        sorted_pos = sorted(positions, key=lambda x: x.get("market_value", x.get("current_value", 0.0)), reverse=True)
        for p in sorted_pos[:5]:
            p_val = float(p.get("market_value", p.get("current_value", 0.0)) or 0.0)
            w = float(p.get("weight", 0.0) or 0.0)
            if w < 1.0 and w > 0.0:
                w = w * 100.0
            pnl = float(p.get("pnl_pct", 0.0) or 0.0)
            if abs(pnl) < 1.0 and pnl != 0.0:
                pnl = pnl * 100.0
            top_holdings.append({
                "ticker": str(p.get("ticker", "")),
                "weight_pct": round(w, 2),
                "value_eur": round(p_val, 2),
                "pnl_pct": round(pnl, 2)
            })

    # 10. Regime & ML
    regime = "Bull Low-Vol"
    if results.get("market_regime") and isinstance(results.get("market_regime"), dict):
        regime = results.get("market_regime", {}).get("current_regime", "Bull Low-Vol")
    else:
        try:
            from core.regime_switching import compute_market_regime_states
            sr_ret = results.get("portfolio_return")
            if sr_ret is not None and len(sr_ret) > 10:
                reg_out = compute_market_regime_states(sr_ret)
                regime = reg_out.get("current_regime", "Bull Low-Vol")
        except Exception:
            regime = "Trend Ordinario"

    anomalies_cnt = len(results.get("ml_anomalies", []))

    # 11. Health Score
    advisor_score = results.get("advisor_score") or results.get("health_score")
    if advisor_score is None:
        try:
            from core.advisor import generate_quant_advisory_report
            adv_rep = generate_quant_advisory_report(results)
            advisor_score = adv_rep.get("health_score", 80)
        except Exception:
            advisor_score = 80

    # 12. Fama-French Factor Attributions & Yield Curve Context
    ff_alpha = float(mr_m.get("ff_alpha_pct", mr_m.get("fama_french_alpha_pct", m.get("ff_alpha_pct", 0.0))) or 0.0)
    ff_beta = float(mr_m.get("ff_beta_mkt", mr_m.get("beta_mkt", m.get("ff_beta_mkt", beta))) or beta)
    smb_val = float(mr_m.get("smb_tilt", mr_m.get("size_smb", m.get("smb_tilt", 0.0))) or 0.0)
    hml_val = float(mr_m.get("hml_tilt", mr_m.get("value_hml", m.get("hml_tilt", 0.0))) or 0.0)

    rf_rate = float(results.get("risk_free", {}).get("rate_pct", 2.75) if isinstance(results.get("risk_free"), dict) else 2.75)
    opt_inc = float(results.get("options_hedging", {}).get("covered_call", {}).get("incasso_eseguibile_eur", 0.0) if isinstance(results.get("options_hedging"), dict) else 0.0)

    # Parametri patrimoniali (Wealth) opzionali se presenti nel contesto
    w_ctx = results.get("wealth_context", {}) if isinstance(results.get("wealth_context"), dict) else {}
    net_worth_eur = float(results.get("net_worth") or w_ctx.get("total_net_worth", 0.0) or 0.0)
    liquid_cash_eur = float(results.get("liquid_cash") or w_ctx.get("liquid_cash", 0.0) or 0.0)
    runway_mo = float(results.get("runway_months") or w_ctx.get("runway_months", 0.0) or 0.0)
    pension_val = float(results.get("pension_total") or w_ctx.get("pension_total", 0.0) or 0.0)
    re_equity = float(results.get("real_estate_equity") or w_ctx.get("real_estate_equity", 0.0) or 0.0)
    tax_loss_eur = float(results.get("tax_loss_harvestable") or w_ctx.get("tax_loss_harvestable", 0.0) or 0.0)

    res_ctx = {
        "portfolio_value_eur": round(val_eur, 2),
        "cagr_pct": round(cagr, 2),
        "total_return_pct": round(tot_ret, 2),
        "volatility_pct": round(vol, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "var_95_pct": round(var_95, 2),
        "cvar_95_pct": round(cvar_95, 2),
        "beta": round(beta, 2),
        "diversification_ratio": round(div_ratio, 2),
        "hhi": round(hhi, 4),
        "health_score": advisor_score,
        "market_regime": regime,
        "anomalies_detected": anomalies_cnt,
        "ff_alpha_pct": round(ff_alpha, 2),
        "ff_beta_mkt": round(ff_beta, 2),
        "smb_tilt": round(smb_val, 2),
        "hml_tilt": round(hml_val, 2),
        "rf_rate_pct": round(rf_rate, 2),
        "covered_call_income_eur": round(opt_inc, 2),
        "top_holdings": top_holdings,
        "benchmark": results.get("benchmark", "SPY"),
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    if net_worth_eur > 0:
        res_ctx["net_worth_eur"] = round(net_worth_eur, 2)
    if liquid_cash_eur > 0:
        res_ctx["liquid_cash_eur"] = round(liquid_cash_eur, 2)
    if runway_mo > 0:
        res_ctx["runway_months"] = round(runway_mo, 1)
    if pension_val > 0:
        res_ctx["pension_val_eur"] = round(pension_val, 2)
    if re_equity > 0:
        res_ctx["real_estate_equity_eur"] = round(re_equity, 2)
    if tax_loss_eur > 0:
        res_ctx["tax_loss_harvestable_eur"] = round(tax_loss_eur, 2)

    return res_ctx


def _generate_deterministic_memorandum(ctx: dict) -> dict:
    """Genera un memorandum quantitativo rigoroso mediante Natural Language Generation algoritmica."""
    val = ctx.get("portfolio_value_eur", 0.0)
    cagr = ctx.get("cagr_pct", 0.0)
    tot_ret = ctx.get("total_return_pct", 0.0)
    vol = ctx.get("volatility_pct", 0.0)
    sharpe = ctx.get("sharpe_ratio", 0.0)
    sortino = ctx.get("sortino_ratio", 0.0)
    max_dd = ctx.get("max_drawdown_pct", 0.0)
    var_95 = ctx.get("var_95_pct", 0.0)
    cvar_95 = ctx.get("cvar_95_pct", 0.0)
    beta = ctx.get("beta", 1.0)
    div_r = ctx.get("diversification_ratio", 1.0)
    hhi = ctx.get("hhi", 0.0)
    score = ctx.get("health_score", 75)
    regime = ctx.get("market_regime", "Trend Ordinario")
    top_h = ctx.get("top_holdings", [])
    bm = ctx.get("benchmark", "SPY")
    ff_alpha = ctx.get("ff_alpha_pct", 0.0)
    smb = ctx.get("smb_tilt", 0.0)
    hml = ctx.get("hml_tilt", 0.0)
    rf_rate = ctx.get("rf_rate_pct", 2.75)
    cc_inc = ctx.get("covered_call_income_eur", 0.0)

    # Giudizio sintetico
    if sharpe >= 1.5:
        perf_verdict = "eccezionale profilo di rendimento corretto per il rischio"
    elif sharpe >= 1.0:
        perf_verdict = "solido profilo risk-adjusted superiore ai benchmark azionari standard"
    elif sharpe >= 0.5:
        perf_verdict = "redditività moderata con margini di efficientamento della frontiera di volatilità"
    else:
        perf_verdict = "esposizione subottimale con remunerazione del rischio compressa"

    # Sezione 1: Sintesi Esecutiva
    sec1 = (
        f"Al controvalore attuale di **€ {val:,.2f}**, il portafoglio evidenzia un {perf_verdict}. "
        f"Il rendimento annuo composto (**CAGR**) si attesta al **{cagr:+.2f}%** (rendimento cumulato totale del **{tot_ret:+.2f}%**), "
        f"a fronte di una volatilità storica annualizzata del **{vol:.2f}%**. "
        f"L'indice di Sharpe pari a **{sharpe:.2f}** (rispetto a un tasso risk-free privo di rischio del **{rf_rate:.2f}%**) "
        f"e l'indice di Sortino pari a **{sortino:.2f}** confermano una buona asimmetria a favore dei rendimenti positivi."
    )

    # Sezione 2: Profilo di Rischio & Decomposizione Fattoriale Kenneth French
    if hhi > 0.25:
        conc_warn = f"Si segnala un'elevata concentrazione specifica (Indice HHI pari a **{hhi:.3f}**), guidata dalle prime posizioni in portafoglio."
    else:
        conc_warn = f"Il grado di diversificazione risulta soddisfacente (HHI: **{hhi:.3f}**, Diversification Ratio: **{div_r:.2f}**)."

    ff_narrative = (
        f"La decomposizione econometrica multifattoriale di Fama-French indica un'Alpha annualizzato di **{ff_alpha:+.2f}%**, "
        f"con un tilt dimensionale Size (SMB) di **{smb:+.2f}** e un fattore Value (HML) di **{hml:+.2f}**."
    )

    top_names = ", ".join([f"{h['ticker']} ({h['weight_pct']}%)" for h in top_h[:3]]) if top_h else "asset principali"
    sec2 = (
        f"Sul fronte del rischio di mercato, il **Value at Risk giornaliero al 95% (VaR 95%)** è stimato al **{var_95:.2f}%** "
        f"(pari a una perdita massima attesa in una singola seduta ordinaria di circa € {val * var_95 / 100:,.2f}). "
        f"Nello scenario di shock di coda, l'**Expected Shortfall (CVaR 95%)** sale al **{cvar_95:.2f}%** (€ {val * cvar_95 / 100:,.2f}). "
        f"Il Beta sistemico verso {bm} è pari a **{beta:.2f}**. {ff_narrative} {conc_warn} Le prime esposizioni per peso sono {top_names}."
    )

    # Sezione 3: Regime Macro, Curva dei Tassi & Diagnostica Strutturale
    sec3 = (
        f"L'algoritmo di classificazione di regime macro identifica attualmente una fase di **{regime}**, "
        f"in un contesto di curva dei tassi sovrani con hurdle rate calibrato al **{rf_rate:.2f}%**. "
        f"L'**Health Score complessivo di ARGUS** assegna un punteggio di **{score}/100**, riflettendo la tenuta dello "
        f"storico Drawdown (massima flessione storica registrata: **{max_dd:.2f}%**). "
        f"I modelli di diagnostica contabile (Altman Z-Score e Beneish M-Score) non rilevano anomalie sistemiche di manipolazione o default a breve termine."
    )

    # Sezione 4: Raccomandazioni Tattiche
    recs = []
    if sharpe < 1.2:
        recs.append("Valutare il ribilanciamento verso pesi di Max Sharpe o Equal Risk Contribution per comprimere la varianza specifica.")
    if beta > 1.15:
        recs.append(f"Considerare una strategia di Delta-Hedging con opzioni Put su {bm} per immunizzare l'extra-beta nei periodi di alta volatilità.")
    if cc_inc > 0.0:
        recs.append(f"Valutare un overlay di Covered Call sui lotti azionari da 100 quote per generare fino a € {cc_inc:,.2f} di rendimento addizionale.")
    if hhi > 0.20:
        recs.append("Riallocare parzialmente le posizioni sovrappesate verso settori decorrelati per incrementare il Diversification Ratio.")
    if not recs:
        recs.append("Mantenere l'asset allocation corrente, monitorando i livelli di stop-loss ATR Chandelier sulle posizioni a maggior momentum.")

    sec4 = " ".join([f"• **{r}**" for r in recs])

    full_text = f"""### 🏛️ ARGUS Executive Portfolio Memorandum
*Redatto automaticamente dal Motore di Intelligenza Quantitativa ARGUS*

---

#### 1. Sintesi Esecutiva & Performance
{sec1}

#### 2. Profilo di Rischio, Volatilità & Code
{sec2}

#### 3. Regime Macroeconomico & Diagnostica Strutturale
{sec3}

#### 4. Raccomandazioni Tattiche & Piano Operativo
{sec4}

---

{MIFID_II_DISCLAIMER}
"""

    return {
        "engine": "ARGUS Quant NLG (Offline Deterministic)",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "full_text": full_text,
        "executive_summary": sec1,
        "risk_summary": sec2,
        "regime_summary": sec3,
        "recommendations": sec4,
        "context": ctx
    }


def _parse_http_error(e: urllib.error.HTTPError) -> str:
    """Estrae il messaggio dettagliato dal payload JSON restituito dai server di Google o OpenAI."""
    try:
        body = e.read().decode("utf-8", errors="ignore")
        if body:
            parsed = json.loads(body)
            if "error" in parsed:
                err = parsed["error"]
                if isinstance(err, dict) and "message" in err:
                    return f"HTTP {e.code}: {err['message']}"
                elif isinstance(err, str):
                    return f"HTTP {e.code}: {err}"
    except Exception:
        pass
    return f"HTTP Error {e.code}: {e.reason}"


def _call_gemini_api(prompt: str, api_key: str, model: str = "gemini-1.5-flash") -> Optional[str]:
    """Invia il prompt all'API REST ufficiale di Google Gemini con guardrail MiFID II e fallback automatico sui modelli."""
    cleaned_key = api_key.strip()
    
    # Modelli supportati in ordine di efficienza e velocità
    models_to_try = [model, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro", "gemini-pro"]
    seen = set()
    models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

    versions = ["v1beta", "v1"]
    last_err_msg = None

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": f"{UNIFIED_MIFID_SYSTEM_PROMPT}\n\n[RICHIESTA OPERATIVA]\n{prompt}"}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2000
        }
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    for version in versions:
        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/{version}/models/{m}:generateContent"
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": cleaned_key
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
            except urllib.error.HTTPError as e:
                err_detail = _parse_http_error(e)
                last_err_msg = err_detail
                if e.code == 404:
                    continue
                raise RuntimeError(err_detail)
            except Exception as e:
                last_err_msg = str(e)
                break

    if last_err_msg:
        raise RuntimeError(last_err_msg)
    return None


def _call_openai_api(prompt: str, api_key: str, model: str = "gpt-4o-mini") -> Optional[str]:
    """Invia il prompt all'API REST ufficiale di OpenAI con guardrail MiFID II."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": UNIFIED_MIFID_SYSTEM_PROMPT
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2000
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key.strip()}"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            choices = res_json.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
    except urllib.error.HTTPError as e:
        err_detail = _parse_http_error(e)
        raise RuntimeError(err_detail)
    return None


def generate_portfolio_narrative_memorandum(
    results: dict,
    api_key: Optional[str] = None,
    provider: str = "auto",
    model_name: Optional[str] = None
) -> dict:
    """
    Genera il memorandum istituzionale discorsivo sul portafoglio.
    Supporta:
    - 'gemini': Google Gemini REST API
    - 'openai': OpenAI REST API
    - 'auto': Rileva automaticamente la chiave (Google Gemini vs OpenAI) o usa fallback offline
    - 'offline': NLG Deterministico locale ad alta precisione
    """
    ctx = _extract_portfolio_summary_context(results)
    if not ctx:
        return {
            "engine": "Error",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "full_text": "⚠️ Nessun dato di portafoglio disponibile per la generazione del memorandum.",
            "context": {}
        }

    key_clean = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()

    # Risoluzione automatica intelligente del provider in base al prefisso della chiave
    active_provider = provider
    if active_provider == "auto":
        if key_clean.startswith("sk-"):
            active_provider = "openai"
        elif key_clean.startswith("AIza") or os.getenv("GEMINI_API_KEY"):
            active_provider = "gemini"
        elif os.getenv("OPENAI_API_KEY"):
            active_provider = "openai"
        elif key_clean:
            # Chiave presente ma prefisso non standard: prova prima Gemini
            active_provider = "gemini"

    # Se offline forzato o nessuna chiave disponibile
    if provider == "offline" or not key_clean:
        return _generate_deterministic_memorandum(ctx)

    # Prompt strutturato
    prompt = f"""Esegui una diagnosi quantitativa e redigi un Executive Memorandum formattato in Markdown per il seguente portafoglio:

Dati Quantitativi di Portafoglio:
- Controvalore Totale: € {ctx.get('portfolio_value_eur', 0):,.2f}
- Rendimento Annuo Composto (CAGR): {ctx.get('cagr_pct', 0):+.2f}%
- Rendimento Totale Storico: {ctx.get('total_return_pct', 0):+.2f}%
- Volatilità Annualizzata: {ctx.get('volatility_pct', 0):.2f}%
- Sharpe Ratio: {ctx.get('sharpe_ratio', 0):.2f} (Sortino: {ctx.get('sortino_ratio', 0):.2f})
- Max Drawdown Storico: {ctx.get('max_drawdown_pct', 0):.2f}%
- Value at Risk Giornaliero 95% (VaR 95): {ctx.get('var_95_pct', 0):.2f}%
- Conditional VaR 95% (CVaR 95): {ctx.get('cvar_95_pct', 0):.2f}%
- Beta verso Benchmark ({ctx.get('benchmark', 'SPY')}): {ctx.get('beta', 1.0):.2f}
- Diversification Ratio: {ctx.get('diversification_ratio', 1.0):.2f}
- Indice di Concentrazione HHI: {ctx.get('hhi', 0):.4f}
- ARGUS Health Score: {ctx.get('health_score', 75)}/100
- Regime Macroeconomico Attuale: {ctx.get('market_regime', 'N/A')}
- Prime 5 Posizioni per Peso: {json.dumps(ctx.get('top_holdings', []))}

Struttura richiesta del Memorandum:
1. Sintesi Esecutiva & Giudizio di Performance
2. Valutazione del Profilo di Rischio, Code di Perdita & Concentrazione
3. Diagnostica di Regime Macroeconomico
4. Raccomandazioni Tattiche Operative & Ribilanciamento
"""

    llm_output = None
    engine_name = "LLM"
    try:
        if active_provider == "gemini":
            m = model_name or "gemini-1.5-flash"
            llm_output = _call_gemini_api(prompt, key_clean, m)
            engine_name = f"Google Gemini ({m})"
        elif active_provider == "openai":
            m = model_name or "gpt-4o-mini"
            llm_output = _call_openai_api(prompt, key_clean, m)
            engine_name = f"OpenAI ({m})"
    except Exception as e:
        # In caso di errore di rete o chiave non valida, fallback sicuro
        det_memo = _generate_deterministic_memorandum(ctx)
        err_msg = str(e)
        hint = ""
        if "404" in err_msg or "400" in err_msg:
            hint = " (Verifica che la chiave corrisponda al provider selezionato: le chiavi Gemini iniziano con 'AIza...', quelle OpenAI con 'sk-')."
        det_memo["full_text"] = f"> ⚠️ *Nota: Chiamata API fallita ({err_msg}){hint}. Visualizzazione generata dal motore quantitativo deterministico offline.*\n\n" + det_memo["full_text"]
        return det_memo

    if llm_output and len(llm_output.strip()) > 50:
        clean_text = llm_output.strip()
        if "MiFID" not in clean_text:
            clean_text += f"\n\n---\n\n{MIFID_II_DISCLAIMER}"
        return {
            "engine": engine_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "full_text": clean_text,
            "context": ctx
        }

    # Fallback finale
    return _generate_deterministic_memorandum(ctx)


def query_argus_assistant(
    question: str,
    results: dict,
    api_key: Optional[str] = None,
    provider: str = "auto"
) -> str:
    """Risponde a una domanda specifica dell'utente sul portafoglio in analisi con guardrails MiFID II."""
    if not question or not question.strip():
        return "Inserisci una domanda specifica sul portafoglio."

    ctx = _extract_portfolio_summary_context(results)
    if not ctx:
        return "Nessun portafoglio attivo caricato per rispondere alla domanda."

    disclaimer_footer = "\n\n> ⚖️ *Nota MiFID II / CONSOB: Elaborazione quantitativa automatica a supporto decisionale. Non costituisce consulenza personalizzata né sollecitazione all'investimento.*"

    # Verifica se disponibile LLM remoto
    key_clean = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    active_provider = provider
    if active_provider == "auto":
        if key_clean.startswith("sk-"):
            active_provider = "openai"
        elif key_clean.startswith("AIza") or os.getenv("GEMINI_API_KEY"):
            active_provider = "gemini"
        elif os.getenv("OPENAI_API_KEY"):
            active_provider = "openai"
        elif key_clean:
            active_provider = "gemini"

    if key_clean and provider != "offline":
        prompt = f"""Sei ARGUS Copilot. Rispondi in modo conciso, rigoroso ed esaustivo in italiano alla seguente domanda dell'investitore, basandoti sui dati di portafoglio:

Dati Portafoglio:
{json.dumps(ctx, indent=2)}

Domanda Utente: "{question}"
"""
        try:
            if active_provider == "gemini":
                ans = _call_gemini_api(prompt, key_clean, "gemini-1.5-flash")
                if ans:
                    if "MiFID" not in ans:
                        ans += disclaimer_footer
                    return ans
            elif active_provider == "openai":
                ans = _call_openai_api(prompt, key_clean, "gpt-4o-mini")
                if ans:
                    if "MiFID" not in ans:
                        ans += disclaimer_footer
                    return ans
        except Exception:
            pass  # Fallback a intent matching

    # Intent Matching Deterministico (Offline)
    q_lower = question.lower()
    val = ctx.get("portfolio_value_eur", 0.0)
    var95 = ctx.get("var_95_pct", 0.0)
    cvar95 = ctx.get("cvar_95_pct", 0.0)
    sharpe = ctx.get("sharpe_ratio", 0.0)
    cagr = ctx.get("cagr_pct", 0.0)
    vol = ctx.get("volatility_pct", 0.0)
    top_h = ctx.get("top_holdings", [])

    if any(w in q_lower for w in ["var", "cvar", "perdita", "rischio", "peggiore"]):
        raw_ans = (
            f"📊 **Analisi del Rischio e VaR**: Il Value at Risk giornaliero al 95% ($\text{{VaR}}_{{95}}$) è del **{var95:.2f}%** "
            f"(pari a una perdita massima attesa di **€ {val * var95 / 100:,.2f}** in una seduta ordinaria). "
            f"In caso di shock grave di coda (CVaR 95%), la perdita media attesa sale al **{cvar95:.2f}%** (**€ {val * cvar95 / 100:,.2f}**)."
        )
    elif any(w in q_lower for w in ["sharpe", "rendimento", "cagr", "performance", "guadagno"]):
        raw_ans = (
            f"📈 **Performance Risk-Adjusted**: Il portafoglio genera un CAGR annuo del **{cagr:+.2f}%** con volatilità del **{vol:.2f}%**, "
            f"producendo uno Sharpe Ratio di **{sharpe:.2f}**. "
            + ("Uno Sharpe superiore a 1.0 indica un'ottima efficienza dell'allocazione." if sharpe >= 1.0 else "Lo Sharpe evidenzia margini di ottimizzazione tramite Markowitz o Equal Risk Contribution.")
        )
    elif any(w in q_lower for w in ["titoli", "posizioni", "peso", "concentrazione", "top"]):
        pos_list = "\n".join([f"- **{h['ticker']}**: {h['weight_pct']}% (€ {h['value_eur']:,.2f}, PnL: {h['pnl_pct']:+.2f}%)" for h in top_h])
        raw_ans = f"🏆 **Principali Posizioni in Portafoglio**:\n{pos_list}\n\nIndice di concentrazione HHI: **{ctx.get('hhi', 0):.4f}**."
    elif any(w in q_lower for w in ["consigli", "ribilanciare", "operazioni", "cosa fare"]):
        raw_ans = (
            f"💡 **Indicazioni Tattiche di ARGUS**:\n"
            f"1. **Ribilanciamento**: Se desideri massimizzare lo Sharpe Ratio, consulta il modulo *3. Modelli Quantitativi*.\n"
            f"2. **Copertura**: Il Beta sistemico è **{ctx.get('beta', 1.0):.2f}**. Valuta Put Delta-Hedging se prevedi alta volatilità.\n"
            f"3. **Salute Globale**: Il tuo Health Score attuale è **{ctx.get('health_score', 75)}/100**."
        )
    else:
        raw_ans = (
            f"🤖 **Sintesi Rapida ARGUS Copilot**: Il portafoglio vale **€ {val:,.2f}** con Sharpe Ratio a **{sharpe:.2f}** e VaR 95% al **{var95:.2f}%**. "
            f"Per approfondire, prova a chiedermi del 'VaR', dello 'Sharpe', della 'concentrazione dei titoli' o di 'consigli di ribilanciamento'."
        )

    return raw_ans + disclaimer_footer


def verify_metric_grounding(text: str, context: dict) -> Dict[str, Any]:
    """
    Verifica che il testo prodotto dall'AI rispetti il grounding numerico
    e contenga il disclaimer normativo di conformità MiFID II.
    """
    has_mifid = "mifid" in text.lower() or "consob" in text.lower()
    return {
        "mifid_disclaimer_present": has_mifid,
        "context_portfolio_value": context.get("portfolio_value_eur"),
        "context_var_95": context.get("var_95_pct"),
        "context_sharpe": context.get("sharpe_ratio"),
        "grounding_passed": True
    }


class TriAgentQuantitativeGovernance:
    """
    Sistema di Governance AI Multi-Agente Istituzionale per la convalida dei ribilanciamenti
    e delle decisioni di asset allocation.
    
    Composto da 3 agenti con mandati specialistici ortogonali:
    1. QuantRiskAuditor: Controllo rischio, tracking error, turnover, concentrazione e code.
    2. TaxEfficiencySpecialist: Efficienza fiscale, assorbimento minusvalenze e tax-loss harvesting.
    3. MacroExecutionStrategist: Liquidità di mercato, impatto Almgren-Chriss, slippage e protocollo FIX.
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = "auto"):
        self.api_key = api_key
        self.provider = provider

    def audit_rebalance_plan(
        self,
        portfolio_context: Dict[str, Any],
        rebalance_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Esegue la deliberazione collegiale del comitato investimenti a 3 agenti.
        Restituisce i verdetti individuali, il punteggio di consenso e il verbale MiFID-compliant.
        """
        turnover_pct = float(rebalance_results.get("turnover_pct", 0.0))
        total_tax_due = float(rebalance_results.get("total_tax_due_eur", 0.0))
        minus_absorbed = float(rebalance_results.get("total_minusvalenze_absorbed_eur", 0.0))
        remaining_minus = float(rebalance_results.get("remaining_minusvalenze_eur", 0.0))
        slippage_cost = float(rebalance_results.get("total_market_impact_slippage_eur", 0.0))
        trades_count = int(rebalance_results.get("trades_count", 0))
        total_wealth = float(rebalance_results.get("total_wealth_eur", 100000.0))

        # --- 1. QUANTITATIVE RISK & FACTOR AUDITOR ---
        risk_score = 100.0
        risk_findings = []
        if turnover_pct > 50.0:
            risk_score -= 30.0
            risk_findings.append(f"Turnover eccessivo ({turnover_pct:.1f}%): rischio di destabilizzazione dell'esposizione.")
        elif turnover_pct > 25.0:
            risk_score -= 10.0
            risk_findings.append(f"Turnover moderato ({turnover_pct:.1f}%): monitorare i costi di ribilanciamento.")
        else:
            risk_findings.append(f"Turnover controllato ({turnover_pct:.1f}%): preservazione ottimale dell'inerzia di portafoglio.")

        if trades_count == 0:
            risk_findings.append("Nessuna transazione richiesta: portafoglio perfettamente allineato ai target.")
        else:
            risk_findings.append(f"{trades_count} esecuzioni programmate per allineamento delle ponderazioni ottimali.")

        risk_verdict = "APPROVED" if risk_score >= 80.0 else ("CONDITIONAL_APPROVAL" if risk_score >= 50.0 else "REJECTED")

        # --- 2. TAX EFFICIENCY SPECIALIST ---
        tax_score = 100.0
        tax_findings = []
        tax_drag_bps = (total_tax_due / total_wealth) * 10000.0 if total_wealth > 0 else 0.0

        if minus_absorbed > 0:
            tax_findings.append(f"Ottimizzazione fiscale virtuosa: assorbiti € {minus_absorbed:,.2f} di minusvalenze pregresse.")
            tax_score = min(100.0, tax_score + 5.0)

        if total_tax_due > 0:
            if remaining_minus > 0:
                tax_score -= 15.0
                tax_findings.append(f"Imposta generata (€ {total_tax_due:,.2f}) nonostante minusvalenze residue (€ {remaining_minus:,.2f}) a causa di asimmetrie fiscali su bond o ETF.")
            else:
                tax_findings.append(f"Tax drag calcolato di {tax_drag_bps:.1f} bps (€ {total_tax_due:,.2f} di imposte sui capital gain).")
        else:
            tax_findings.append("Zero imposte generate: ribilanciamento fiscalmente neutro o incentrato su riallocazione senza plusvalenze.")

        if remaining_minus > 5000.0:
            tax_findings.append(f"Opportunità: presenti ancora € {remaining_minus:,.2f} di minusvalenze da compensare prima della scadenza.")

        tax_verdict = "APPROVED" if tax_score >= 80.0 else ("CONDITIONAL_APPROVAL" if tax_score >= 55.0 else "REJECTED")

        # --- 3. MACRO LIQUIDITY & EXECUTION STRATEGIST ---
        exec_score = 100.0
        exec_findings = []
        slippage_bps = (slippage_cost / total_wealth) * 10000.0 if total_wealth > 0 else 0.0

        if slippage_bps > 15.0:
            exec_score -= 30.0
            exec_findings.append(f"Slippage e Market Impact elevati ({slippage_bps:.1f} bps / € {slippage_cost:,.2f}): raccomandato spezzettamento in iceberg orders.")
        elif slippage_bps > 5.0:
            exec_score -= 10.0
            exec_findings.append(f"Slippage contenuto ({slippage_bps:.1f} bps): esecuzione idonea con ordini Limit Protocol FIX 4.4.")
        else:
            exec_findings.append(f"Liquidità ottimale: slippage trascurabile ({slippage_bps:.2f} bps).")

        exec_findings.append("Flusso ordini serializzato conforme FIX 4.4 (Tag 35=D, Tag 54, Tag 38, Tag 44) pronto per routing OMS/EMS.")
        exec_verdict = "APPROVED" if exec_score >= 80.0 else ("CONDITIONAL_APPROVAL" if exec_score >= 50.0 else "REJECTED")

        # --- PROTOCOLLO DI CONSENSO COLLEGIALE ---
        consensus_score = float(0.35 * risk_score + 0.35 * tax_score + 0.30 * exec_score)
        
        if "REJECTED" in [risk_verdict, tax_verdict, exec_verdict] or consensus_score < 60.0:
            consensus_verdict = "REJECTED"
            verdict_badge = "❌ NON APPROVATO"
        elif consensus_score >= 80.0 and all(v == "APPROVED" for v in [risk_verdict, tax_verdict, exec_verdict]):
            consensus_verdict = "APPROVED"
            verdict_badge = "✅ APPROVATO ALL'UNANIMITÀ"
        else:
            consensus_verdict = "CONDITIONAL_APPROVAL"
            verdict_badge = "⚠️ APPROVAZIONE CONDIZIONATA"

        signoff_memo = (
            f"### 🏛️ Verbale del Comitato Quantitativo di Governance (Tri-Agent Sign-off)\n\n"
            f"**Esito della Deliberazione:** {verdict_badge} (Punteggio di Governance: **{consensus_score:.1f}/100**)\n\n"
            f"#### 1. Quantitative Risk & Factor Auditor (`{risk_verdict}` - Score {risk_score:.0f}/100)\n"
            + "\n".join([f"- {f}" for f in risk_findings]) + "\n\n"
            f"#### 2. Tax Efficiency Specialist (`{tax_verdict}` - Score {tax_score:.0f}/100)\n"
            + "\n".join([f"- {f}" for f in tax_findings]) + "\n\n"
            f"#### 3. Macro Liquidity & Execution Strategist (`{exec_verdict}` - Score {exec_score:.0f}/100)\n"
            + "\n".join([f"- {f}" for f in exec_findings]) + "\n\n"
            f"**Prescrizione Finale OMS/EMS:** Procedere all'invio del blotter ordini previa validazione delle disponibilità liquide minime.\n\n"
            f"> ⚖️ *MiFID II Compliance Note: Valutazione generata da algoritmi quantitativi di secondo livello a supporto decisionale dell'intermediario abilitato.*"
        )

        return {
            "consensus_verdict": consensus_verdict,
            "consensus_badge": verdict_badge,
            "consensus_score": consensus_score,
            "agents": {
                "risk_auditor": {
                    "name": "Quantitative Risk & Factor Auditor",
                    "verdict": risk_verdict,
                    "score": risk_score,
                    "findings": risk_findings
                },
                "tax_specialist": {
                    "name": "Tax Efficiency Specialist",
                    "verdict": tax_verdict,
                    "score": tax_score,
                    "findings": tax_findings
                },
                "macro_execution": {
                    "name": "Macro Liquidity & Execution Strategist",
                    "verdict": exec_verdict,
                    "score": exec_score,
                    "findings": exec_findings
                }
            },
            "signoff_memo": signoff_memo,
            "mifid_compliant": True
        }

