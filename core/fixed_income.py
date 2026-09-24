# ============================================================
# core/fixed_income.py
# ARGUS — Risk Analytics Platform
# Institutional Fixed Income Analytics (Bloomberg YAS/FI Parity)
# Features:
#   - Bond Cash Flows & Analytical Pricing
#   - Yield to Maturity (YTM) Solver (Newton-Raphson + Brent)
#   - Macaulay Duration, Modified Duration, Convexity & DV01/PVBP
#   - 2nd-Order Taylor Series Price Impact: dP/P ~ -D_mod * dy + 0.5 * C * (dy)^2
#   - Z-Spread (Zero-Volatility Spread) over Nelson-Siegel-Svensson Spot Curve
#   - Credit Default Swap (CDS) Implied Hazard Rate & Default Probabilities
# ============================================================

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy.optimize import brentq, newton

# ── 1. MODELLO CASH FLOW OBBLIGAZIONARI ─────────────────────────────


def compute_bond_cash_flows(
    face_value: float = 100.0, coupon_rate: float = 0.04, maturity_years: float = 10.0, coupon_frequency: int = 2
) -> List[Tuple[float, float]]:
    """
    Genera il piano di flussi di cassa (cedole + rimborso capitale a scadenza).

    Args:
        face_value: Valore nominale (default 100.0)
        coupon_rate: Tasso cedolare annuo decimale (es. 0.04 per 4.0%)
        maturity_years: Durata residua in anni (es. 10.0)
        coupon_frequency: Frequenza annuale stacco cedola (1=annuale, 2=semestrale, 4=trimestrale)

    Returns:
        Lista di tuple (tempo_anni_t, cash_flow_t)
    """
    if maturity_years <= 0:
        return [(0.0, face_value)]

    freq = max(1, int(coupon_frequency))
    total_periods = int(round(maturity_years * freq))
    if total_periods == 0:
        total_periods = 1

    coupon_payment = (coupon_rate * face_value) / freq
    cash_flows = []

    for i in range(1, total_periods + 1):
        t = i / freq
        # All'ultimo periodo si aggiunge il rimborso del valore nominale
        amount = coupon_payment + (face_value if i == total_periods else 0.0)
        cash_flows.append((t, amount))

    return cash_flows


def compute_bond_price_from_ytm(
    face_value: float, coupon_rate: float, maturity_years: float, ytm: float, coupon_frequency: int = 2
) -> float:
    """
    Calcola il prezzo teorico del bond dato uno Yield to Maturity (YTM).
    P = sum(CF_t / (1 + ytm/m)^(m * t))
    """
    if maturity_years <= 0:
        return float(face_value)

    freq = max(1, int(coupon_frequency))
    cfs = compute_bond_cash_flows(face_value, coupon_rate, maturity_years, freq)

    price = 0.0
    for t, cf in cfs:
        discount_factor = (1.0 + ytm / freq) ** (freq * t)
        price += cf / discount_factor

    return float(price)


# ── 2. RISOLUTORE NUMERICO YTM (YIELD TO MATURITY) ─────────────────


def compute_bond_ytm(
    face_value: float, coupon_rate: float, maturity_years: float, market_price: float, coupon_frequency: int = 2
) -> float:
    """
    Risolve numericamente lo Yield to Maturity (YTM) di un bond dato il suo prezzo di mercato.
    Usa Newton-Raphson con fallback robusto a Brentq solver.
    """
    if market_price <= 0 or face_value <= 0:
        return 0.0
    if maturity_years <= 0:
        return 0.0

    # Funzione obiettivo: P(y) - P_market = 0
    def objective(y: float) -> float:
        return compute_bond_price_from_ytm(face_value, coupon_rate, maturity_years, y, coupon_frequency) - market_price

    # Derivata prima rispetto a y per Newton-Raphson: dP/dy = - sum(t * CF_t / (1 + y/m)^(m*t + 1))
    def prime(y: float) -> float:
        freq = max(1, int(coupon_frequency))
        cfs = compute_bond_cash_flows(face_value, coupon_rate, maturity_years, freq)
        dp = 0.0
        for t, cf in cfs:
            dp -= (t * cf) / ((1.0 + y / freq) ** (freq * t + 1))
        return dp

    # Stima iniziale prudenziale (formula approssimata di YTM)
    # y0 ~ (C + (F - P)/n) / ((F + P)/2)
    annual_coupon = coupon_rate * face_value
    approx_y = (annual_coupon + (face_value - market_price) / max(0.1, maturity_years)) / (
        (face_value + market_price) / 2.0
    )
    approx_y = max(-0.10, min(0.50, approx_y))

    try:
        sol = newton(objective, x0=approx_y, fprime=prime, maxiter=50, tol=1e-7)
        if -0.20 <= sol <= 2.0:
            return float(sol)
    except Exception:
        pass

    # Fallback robusto a Brent su intervallo [-15%, +100%]
    try:
        sol = brentq(objective, a=-0.15, b=1.0, maxiter=100, xtol=1e-7)
        return float(sol)
    except Exception:
        return float(approx_y)


# ── 3. ANALISI ISTITUZIONALE: DURATION, CONVEXITY, DV01 ─────────────


def compute_bond_analytics(
    face_value: float = 100.0,
    coupon_rate: float = 0.04,
    maturity_years: float = 10.0,
    market_price: float = 100.0,
    coupon_frequency: int = 2,
    yield_shift_bps: float = 10.0,
) -> Dict[str, Any]:
    """
    Calcola l'insieme completo delle metriche di sensibilità istituzionale (Bloomberg YAS Style):
      - YTM (Yield to Maturity) & Current Yield
      - Macaulay Duration (anni)
      - Modified Duration (% / 100bps)
      - Convexity esatta (convessità di 2° ordine)
      - DV01 / PVBP (Price Value of a Basis Point in unità monetarie)
      - Matrice di Stress Tassi (-200bps ... +200bps) con Taylor Expansion
    """
    freq = max(1, int(coupon_frequency))
    ytm = compute_bond_ytm(face_value, coupon_rate, maturity_years, market_price, freq)
    current_yield = (coupon_rate * face_value) / market_price if market_price > 0 else 0.0

    cfs = compute_bond_cash_flows(face_value, coupon_rate, maturity_years, freq)

    # Calcolo Macaulay Duration & Convexity esatta
    weighted_time_sum = 0.0
    convexity_sum = 0.0
    actual_price = 0.0

    for t, cf in cfs:
        df = (1.0 + ytm / freq) ** (freq * t)
        pv_cf = cf / df
        actual_price += pv_cf
        weighted_time_sum += t * pv_cf
        # Formula periodica convessità
        convexity_sum += t * (t + 1.0 / freq) * pv_cf

    # Protezione divisione per zero
    ref_price = max(0.01, actual_price if actual_price > 0 else market_price)
    macaulay_duration = weighted_time_sum / ref_price
    modified_duration = macaulay_duration / (1.0 + ytm / freq)

    # Convexity: 1 / (P * (1 + y/m)^2) * sum(...)
    convexity = convexity_sum / (ref_price * ((1.0 + ytm / freq) ** 2))

    # DV01 (Dollar Value of a 01 / Price Value of a Basis Point)
    # DV01 = Modified Duration * P * 0.0001
    dv01 = modified_duration * market_price * 0.0001
    pvbp = dv01  # Sinonimo nei desk reddito fisso

    # Generazione tabella di sensibilità a shock di rendimento (-200bps .. +200bps)
    shifts_bps = [-200, -100, -50, -25, 25, 50, 100, 200]
    sensitivity_rows = []

    for s_bps in shifts_bps:
        dy = s_bps / 10000.0
        # Prezzo esatto ricalcolato
        exact_p = compute_bond_price_from_ytm(face_value, coupon_rate, maturity_years, ytm + dy, freq)
        pct_exact = ((exact_p - market_price) / market_price) * 100.0

        # Taylor 1° ordine (Solo Duration)
        pct_taylor_1 = (-modified_duration * dy) * 100.0
        # Taylor 2° ordine (Duration + Convexity)
        pct_taylor_2 = (-modified_duration * dy + 0.5 * convexity * (dy**2)) * 100.0

        sensitivity_rows.append(
            {
                "shift_bps": s_bps,
                "new_ytm_pct": (ytm + dy) * 100.0,
                "exact_price": round(exact_p, 4),
                "pct_change_exact": round(pct_exact, 3),
                "pct_change_duration_only": round(pct_taylor_1, 3),
                "pct_change_duration_plus_convexity": round(pct_taylor_2, 3),
                "convexity_gain_pct": round(pct_taylor_2 - pct_taylor_1, 3),
            }
        )

    return {
        "face_value": face_value,
        "coupon_rate_pct": coupon_rate * 100.0,
        "maturity_years": maturity_years,
        "market_price": market_price,
        "ytm_pct": round(ytm * 100.0, 4),
        "current_yield_pct": round(current_yield * 100.0, 4),
        "macaulay_duration_years": round(macaulay_duration, 4),
        "modified_duration": round(modified_duration, 4),
        "convexity": round(convexity, 4),
        "dv01": round(dv01, 5),
        "pvbp": round(pvbp, 5),
        "sensitivity_table": pd.DataFrame(sensitivity_rows),
    }


# ── 4. Z-SPREAD (ZERO-VOLATILITY SPREAD) SU CURVA NSS ──────────────


def compute_z_spread(
    face_value: float,
    coupon_rate: float,
    maturity_years: float,
    market_price: float,
    spot_curve_fn_or_params: Union[Callable[[float], float], Dict[str, float], None] = None,
    coupon_frequency: int = 2,
) -> float:
    """
    Calcola lo Z-Spread (in Basis Points) rispetto a una curva spot risk-free o Nelson-Siegel-Svensson.
    Risolve per z tale che:
      P_market = sum( CF_t / (1 + (r(t) + z)/m )^(m * t) )
    """
    if market_price <= 0 or maturity_years <= 0:
        return 0.0

    freq = max(1, int(coupon_frequency))
    cfs = compute_bond_cash_flows(face_value, coupon_rate, maturity_years, freq)

    # Determina la funzione del tasso spot r(t)
    if callable(spot_curve_fn_or_params):
        r_spot = spot_curve_fn_or_params
    elif isinstance(spot_curve_fn_or_params, dict) and "beta0" in spot_curve_fn_or_params:
        from core.yield_curve import evaluate_nelson_siegel_svensson_curve

        params = spot_curve_fn_or_params
        r_spot = lambda t: evaluate_nelson_siegel_svensson_curve(np.array([t]), params)[0] / 100.0
    else:
        # Tasso flat di fallback 2.50%
        r_spot = lambda t: 0.0250

    def price_with_z(z: float) -> float:
        p = 0.0
        for t, cf in cfs:
            r_t = r_spot(t)
            rate_effective = r_t + z
            df = (1.0 + rate_effective / freq) ** (freq * t)
            p += cf / df
        return p

    def objective(z: float) -> float:
        return price_with_z(z) - market_price

    try:
        z_solution = brentq(objective, a=-0.10, b=0.25, maxiter=100, xtol=1e-7)
        return float(z_solution * 10000.0)  # In Basis Points (bps)
    except Exception:
        # Approssimazione se fallisce la calibrazione esatta
        ytm = compute_bond_ytm(face_value, coupon_rate, maturity_years, market_price, freq)
        r_mat = r_spot(maturity_years)
        return float((ytm - r_mat) * 10000.0)


# ── 5. CREDIT DEFAULT SWAP (CDS) & IMPLIED DEFAULT PROBABILITY ─────


def compute_cds_implied_default_probability(
    cds_spread_bps: float, recovery_rate: float = 0.40, tenors_years: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Stima la probabilità cumulativa di default e l'Hazard Rate (intensità di default)
    a partire dallo spread di mercato di un Credit Default Swap (CDS).

    Formula standard di mercato:
      Hazard Rate (lambda) ~ S_CDS / (1 - Recovery Rate)
      Sopravvivenza S(t) = exp(-lambda * t)
      Probabilità Cumulativa di Default PD(t) = 1 - exp(-lambda * t)

    Args:
        cds_spread_bps: Spread CDS a 5 anni in punti base (es. 120 bps = 1.20%)
        recovery_rate: Tasso di recupero atteso (default standard ISDA 40% = 0.40)
        tenors_years: Lista di orizzonti temporali (es. [1, 2, 3, 5, 7, 10])

    Returns:
        Dizionario con Hazard Rate, tabella term structure di default e probabilità marginali.
    """
    if tenors_years is None:
        tenors_years = [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 30.0]

    spread_dec = max(0.0, cds_spread_bps / 10000.0)
    loss_given_default = max(0.01, 1.0 - recovery_rate)

    # Stima dell'Hazard Rate (lambda costante o approssimato)
    hazard_rate = spread_dec / loss_given_default

    rows = []
    prev_pd = 0.0
    for t in tenors_years:
        surv_prob = np.exp(-hazard_rate * t)
        cum_pd = 1.0 - surv_prob
        marginal_pd = cum_pd - prev_pd
        annualized_pd = 1.0 - (surv_prob ** (1.0 / t)) if t > 0 else 0.0

        rows.append(
            {
                "tenor_years": t,
                "tenor_label": f"{int(t)}Y" if t == int(t) else f"{t}Y",
                "survival_probability_pct": round(float(surv_prob * 100.0), 3),
                "cumulative_default_prob_pct": round(float(cum_pd * 100.0), 3),
                "marginal_default_prob_pct": round(float(marginal_pd * 100.0), 3),
                "annualized_default_rate_pct": round(float(annualized_pd * 100.0), 3),
            }
        )
        prev_pd = cum_pd

    df_pd = pd.DataFrame(rows)

    return {
        "cds_spread_bps": cds_spread_bps,
        "recovery_rate_pct": recovery_rate * 100.0,
        "loss_given_default_pct": loss_given_default * 100.0,
        "implied_hazard_rate_pct": round(float(hazard_rate * 100.0), 4),
        "default_probability_curve": df_pd,
    }


# ── 6. PRESET ISTITUZIONALI TITOLI DI STATO & CORPORATE ────────────

INSTITUTIONAL_BOND_PRESETS: Dict[str, Dict[str, Any]] = {
    "IT10Y": {
        "name": "BTP Decennale Repubblica Italiana 4.00%",
        "issuer": "Ministero dell'Economia e delle Finanze (Italia)",
        "coupon_rate": 0.040,
        "maturity_years": 10.0,
        "market_price": 101.50,
        "currency": "EUR",
        "coupon_freq": 2,
        "cds_5y_bps": 88.0,
    },
    "DE10Y": {
        "name": "Bund Decennale Repubblica Federale Tedesca 2.50%",
        "issuer": "Bundesrepublik Deutschland",
        "coupon_rate": 0.025,
        "maturity_years": 10.0,
        "market_price": 99.80,
        "currency": "EUR",
        "coupon_freq": 1,
        "cds_5y_bps": 12.0,
    },
    "US10Y": {
        "name": "US 10-Year Treasury Note 4.25%",
        "issuer": "US Department of the Treasury",
        "coupon_rate": 0.0425,
        "maturity_years": 10.0,
        "market_price": 98.90,
        "currency": "USD",
        "coupon_freq": 2,
        "cds_5y_bps": 34.0,
    },
    "CORP_ENI": {
        "name": "ENI SpA Sustainability-Linked Bond 3.875%",
        "issuer": "ENI SpA (Corporate)",
        "coupon_rate": 0.03875,
        "maturity_years": 6.0,
        "market_price": 99.20,
        "currency": "EUR",
        "coupon_freq": 1,
        "cds_5y_bps": 65.0,
    },
}


# ── 6. NELSON-SIEGEL CASHFLOW PRICING & KEY RATE DURATION ─────────


def price_bond_cashflows_nelson_siegel(
    cashflows: List[Tuple[float, float]], ns_params: Dict[str, float], compounding_freq: int = 2
) -> Dict[str, Any]:
    """
    Calcola il prezzo teorico analitico, la Duration di Macaulay e la Convessità
    scontando ciascun flusso (t, CF_t) sui tassi spot della curva Nelson-Siegel o Svensson.
    """
    if not cashflows:
        return {"fair_price": 0.0, "macaulay_duration": 0.0, "modified_duration": 0.0, "convexity": 0.0}

    from core.yield_curve import evaluate_nelson_siegel_curve, evaluate_nelson_siegel_svensson_curve

    is_svensson = "beta3" in ns_params or "tau2" in ns_params
    eval_fn = evaluate_nelson_siegel_svensson_curve if is_svensson else evaluate_nelson_siegel_curve

    freq = max(1, int(compounding_freq))
    maturities = np.array([t for t, _ in cashflows], dtype=float)
    amounts = np.array([cf for _, cf in cashflows], dtype=float)

    # Tassi spot annualizzati percentuali dalla curva -> convertiti in decimali
    spot_rates_pct = eval_fn(maturities, ns_params)
    spot_rates = np.maximum(0.0001, spot_rates_pct / 100.0)

    # Fattori di sconto composti
    discount_factors = (1.0 + spot_rates / freq) ** (-freq * maturities)
    pv_cashflows = amounts * discount_factors
    fair_price = float(np.sum(pv_cashflows))

    if fair_price <= 0:
        return {"fair_price": 0.0, "macaulay_duration": 0.0, "modified_duration": 0.0, "convexity": 0.0}

    # Macaulay Duration ponderata sui flussi attualizzati
    mac_duration = float(np.sum(maturities * pv_cashflows) / fair_price)
    # Tasso medio ponderato per la modified duration
    avg_yield = float(np.sum(spot_rates * pv_cashflows) / fair_price)
    mod_duration = mac_duration / (1.0 + avg_yield / freq)

    # Convessità discreta
    convexity = float(
        np.sum(maturities * (maturities + 1.0 / freq) * pv_cashflows) / (fair_price * (1.0 + avg_yield / freq) ** 2)
    )

    return {
        "fair_price": round(fair_price, 4),
        "macaulay_duration": round(mac_duration, 3),
        "modified_duration": round(mod_duration, 3),
        "convexity": round(convexity, 3),
        "weighted_spot_yield_pct": round(avg_yield * 100.0, 3),
    }


def compute_key_rate_durations(
    face_value: float,
    coupon_rate: float,
    maturity_years: float,
    ns_params: Dict[str, float],
    key_rates: Optional[List[float]] = None,
    coupon_freq: int = 2,
    shift_bps: float = 10.0,
) -> Dict[str, float]:
    """
    Calcola le Key Rate Durations (KRD) sui nodi della curva specificati (default: 2Y, 5Y, 10Y, 30Y).
    Misura la sensibilità del prezzo a shock localizzati su singoli segmenti della curva dei tassi.
    """
    nodes = key_rates or [2.0, 5.0, 10.0, 30.0]
    freq = max(1, int(coupon_freq))
    cfs = compute_bond_cash_flows(face_value, coupon_rate, maturity_years, freq)
    base_res = price_bond_cashflows_nelson_siegel(cfs, ns_params, freq)
    p0 = base_res["fair_price"]
    if p0 <= 0:
        return {f"{int(n) if n.is_integer() else n}Y": 0.0 for n in nodes}

    h = shift_bps / 10000.0  # Shock in decimale (es. 10 bps = 0.0010)
    krd_results = {}

    from core.yield_curve import evaluate_nelson_siegel_curve, evaluate_nelson_siegel_svensson_curve

    is_svensson = "beta3" in ns_params or "tau2" in ns_params
    eval_fn = evaluate_nelson_siegel_svensson_curve if is_svensson else evaluate_nelson_siegel_curve

    maturities = np.array([t for t, _ in cfs], dtype=float)
    amounts = np.array([cf for _, cf in cfs], dtype=float)
    base_spots = np.maximum(0.0001, eval_fn(maturities, ns_params) / 100.0)

    # Interpolazione triangolare dello shock locale attorno a ciascun nodo
    extended_nodes = [0.0] + sorted(nodes) + [nodes[-1] + 10.0]

    for i in range(1, len(extended_nodes) - 1):
        node = extended_nodes[i]
        left_node = extended_nodes[i - 1]
        right_node = extended_nodes[i + 1]

        # Costruisci i pesi dello shock triangolare
        w_shock = np.zeros_like(maturities)
        # Segmento sinistro
        mask_left = (maturities >= left_node) & (maturities < node)
        if node > left_node:
            w_shock[mask_left] = (maturities[mask_left] - left_node) / (node - left_node)
        # Segmento destro
        mask_right = (maturities >= node) & (maturities <= right_node)
        if right_node > node:
            w_shock[mask_right] = (right_node - maturities[mask_right]) / (right_node - node)

        # Repricing con bump up e bump down
        spot_up = base_spots + (h * w_shock)
        df_up = (1.0 + spot_up / freq) ** (-freq * maturities)
        p_up = float(np.sum(amounts * df_up))

        spot_down = np.maximum(0.00001, base_spots - (h * w_shock))
        df_down = (1.0 + spot_down / freq) ** (-freq * maturities)
        p_down = float(np.sum(amounts * df_down))

        # Formula centrale KRD
        krd = -(p_up - p_down) / (2.0 * p0 * h)
        label = f"{int(node) if node.is_integer() else node}Y"
        krd_results[label] = round(float(krd), 3)

    return krd_results


# ── 7. PORTFOLIO FIXED INCOME & ALM ANALYTICS ENGINE ───────────────────

KNOWN_BOND_ETF_METRICS: Dict[str, Dict[str, float]] = {
    "SHY": {"duration": 1.9, "convexity": 0.05, "avg_ytm": 0.042},
    "IEI": {"duration": 4.5, "convexity": 0.25, "avg_ytm": 0.041},
    "IEF": {"duration": 7.4, "convexity": 0.65, "avg_ytm": 0.043},
    "TLT": {"duration": 16.8, "convexity": 3.70, "avg_ytm": 0.046},
    "AGG": {"duration": 6.1, "convexity": 0.45, "avg_ytm": 0.044},
    "BND": {"duration": 6.2, "convexity": 0.48, "avg_ytm": 0.044},
    "HYG": {"duration": 3.6, "convexity": 0.18, "avg_ytm": 0.068},
    "JNK": {"duration": 3.4, "convexity": 0.16, "avg_ytm": 0.070},
    "LQD": {"duration": 8.1, "convexity": 0.85, "avg_ytm": 0.052},
    "EMB": {"duration": 6.9, "convexity": 0.75, "avg_ytm": 0.062},
    "BTP": {"duration": 6.5, "convexity": 0.55, "avg_ytm": 0.036},
    "BUND": {"duration": 7.2, "convexity": 0.60, "avg_ytm": 0.024},
    "CSB.MI": {"duration": 4.8, "convexity": 0.30, "avg_ytm": 0.035},
    "EM710.MI": {"duration": 7.1, "convexity": 0.62, "avg_ytm": 0.033},
    "IEAC.MI": {"duration": 4.7, "convexity": 0.32, "avg_ytm": 0.038},
    "VGEA.MI": {"duration": 7.3, "convexity": 0.65, "avg_ytm": 0.028},
}


def _is_fixed_income_asset(row: pd.Series) -> bool:
    """Riconosce se una riga di posizioni appartiene alla classe obbligazionaria."""
    ac = str(row.get("asset_class", "")).strip().upper()
    mac = str(row.get("macro_asset_class", "")).strip().upper()
    tipo = str(row.get("tipo", "")).strip().upper()

    # Esclusione esplicita di azioni e crypto a meno che non ci siano parametri obbligazionari espliciti
    if any(eq in ac or eq in mac or eq in tipo for eq in ["EQUITY", "AZION", "STOCK", "CRYPTO", "COMMODIT"]):
        if not ("coupon_rate" in row and "maturity_years" in row and pd.notnull(row["maturity_years"]) and float(row.get("maturity_years", 0)) > 0):
            return False

    tk = str(row.get("ticker", "")).strip().upper()
    name = str(row.get("name", "")).strip().upper()
    isin = str(row.get("isin", "")).strip().upper()

    # Controllo esatto o prefisso su ticker di ETF/Bond noti
    for k in KNOWN_BOND_ETF_METRICS.keys():
        if tk == k or tk.startswith(k + ".") or tk == k + "-USD" or tk == k + "-EUR":
            return True

    fi_keywords = ["BOND", "OBBLIGAZ", "FIXED INCOME", "TREASURY", "GOV BOND", "CORP BOND", "BTP", "BOT", "CCT", "CTZ", "BUND", "GILT"]
    search_text = f"{tk} {ac} {mac} {tipo} {name} {isin}"
    return any(kw in search_text for kw in fi_keywords)



def compute_portfolio_fixed_income_analytics(
    df_positions: pd.DataFrame,
    df_prices: Optional[pd.DataFrame] = None,
    ns_params: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Calcola l'analisi aggregata del rischio tasso e reddito fisso di portafoglio (ALM / Treasury):
      - Identificazione e filtraggio automatico delle posizioni a reddito fisso (Bond diretti, ETF obbligazionari).
      - Macaulay Duration, Modified Duration e Convessità ponderata per controvalore.
      - DV01 / PVBP Totale di Portafoglio (perdita monetaria per ogni +1 bps di rialzo tassi).
      - Key Rate Durations aggregate (2Y, 5Y, 10Y, 30Y).
      - Matrice di Stress Scenari Curva Tassi:
          * Parallel Shifts (+50, -50, +100, +200 bps)
          * Bull Steepener (2Y -100bps, 10Y -25bps)
          * Bear Steepener (2Y +25bps, 10Y +100bps)
          * Bull Flattener (2Y -25bps, 10Y -100bps)
          * Bear Flattener (2Y +100bps, 10Y +25bps)
      - Tabella dettagliata per singola posizione obbligazionaria.
    """
    if df_positions is None or df_positions.empty:
        return {
            "has_fixed_income": False,
            "total_portfolio_value": 0.0,
            "fixed_income_value": 0.0,
            "fixed_income_weight_pct": 0.0,
            "weighted_mac_duration": 0.0,
            "weighted_mod_duration": 0.0,
            "weighted_convexity": 0.0,
            "portfolio_dv01": 0.0,
            "key_rate_durations": {"2Y": 0.0, "5Y": 0.0, "10Y": 0.0, "30Y": 0.0},
            "curve_stress_scenarios": {},
            "fi_positions_breakdown": [],
        }

    val_col = None
    for c in ["current_value", "controvalore", "valore", "market_value"]:
        if c in df_positions.columns:
            val_col = c
            break

    total_port_val = float(df_positions[val_col].sum()) if val_col else 0.0

    fi_rows = []
    for _, row in df_positions.iterrows():
        if _is_fixed_income_asset(row):
            fi_rows.append(row)

    if not fi_rows:
        return {
            "has_fixed_income": False,
            "total_portfolio_value": round(total_port_val, 2),
            "fixed_income_value": 0.0,
            "fixed_income_weight_pct": 0.0,
            "weighted_mac_duration": 0.0,
            "weighted_mod_duration": 0.0,
            "weighted_convexity": 0.0,
            "portfolio_dv01": 0.0,
            "key_rate_durations": {"2Y": 0.0, "5Y": 0.0, "10Y": 0.0, "30Y": 0.0},
            "curve_stress_scenarios": {},
            "fi_positions_breakdown": [],
            "message": "Nessuna posizione obbligazionaria o ETF a reddito fisso individuata nel portafoglio.",
        }

    df_fi = pd.DataFrame(fi_rows)
    total_fi_val = float(df_fi[val_col].sum()) if val_col else 1.0
    if total_fi_val <= 0:
        total_fi_val = 1.0

    detailed_positions = []
    w_mac_dur = 0.0
    w_mod_dur = 0.0
    w_convexity = 0.0
    total_dv01 = 0.0
    krd_accum = {"2Y": 0.0, "5Y": 0.0, "10Y": 0.0, "30Y": 0.0}

    for _, row in df_fi.iterrows():
        val = float(row.get(val_col, 0.0)) if val_col else 0.0
        weight_fi = val / total_fi_val if total_fi_val > 0 else 0.0
        tk = str(row.get("ticker", "")).strip().upper()

        # Determina metriche del singolo strumento
        d_mac, d_mod, conv, ytm = 5.0, 4.6, 0.35, 0.035
        matched_proxy = None
        for k_proxy, metrics in KNOWN_BOND_ETF_METRICS.items():
            if k_proxy in tk:
                d_mod = metrics["duration"]
                d_mac = d_mod * 1.04
                conv = metrics["convexity"]
                ytm = metrics["avg_ytm"]
                matched_proxy = k_proxy
                break

        # Se sono presenti parametri espliciti del bond
        if "coupon_rate" in row and "maturity_years" in row and pd.notnull(row["maturity_years"]):
            try:
                b_res = compute_bond_analytics(
                    face_value=float(row.get("face_value", 100.0)),
                    coupon_rate=float(row.get("coupon_rate", 0.03)),
                    maturity_years=float(row.get("maturity_years", 5.0)),
                    market_price=float(row.get("market_price", 100.0)),
                )
                d_mac = b_res["macaulay_duration"]
                d_mod = b_res["modified_duration"]
                conv = b_res["convexity"]
                ytm = b_res["ytm_pct"] / 100.0
            except Exception:
                pass

        dv01_pos = val * d_mod * 0.0001
        impact_plus_100bps = -d_mod * 0.01 + 0.5 * conv * (0.01**2)
        euro_impact_100bps = val * impact_plus_100bps

        w_mac_dur += weight_fi * d_mac
        w_mod_dur += weight_fi * d_mod
        w_convexity += weight_fi * conv
        total_dv01 += dv01_pos

        # Key rate allocation stocastica basata su duration
        if d_mod <= 3.0:
            krd_accum["2Y"] += weight_fi * d_mod
        elif d_mod <= 7.0:
            krd_accum["2Y"] += weight_fi * (d_mod * 0.3)
            krd_accum["5Y"] += weight_fi * (d_mod * 0.7)
        elif d_mod <= 12.0:
            krd_accum["5Y"] += weight_fi * (d_mod * 0.3)
            krd_accum["10Y"] += weight_fi * (d_mod * 0.7)
        else:
            krd_accum["10Y"] += weight_fi * (d_mod * 0.4)
            krd_accum["30Y"] += weight_fi * (d_mod * 0.6)

        detailed_positions.append(
            {
                "ticker": tk,
                "name": str(row.get("name", tk)),
                "value_eur": round(val, 2),
                "weight_fi_pct": round(weight_fi * 100.0, 2),
                "weight_portfolio_pct": round((val / total_port_val * 100.0) if total_port_val > 0 else 0.0, 2),
                "macaulay_duration": round(d_mac, 2),
                "modified_duration": round(d_mod, 2),
                "convexity": round(conv, 3),
                "ytm_pct": round(ytm * 100.0, 2),
                "dv01_eur": round(dv01_pos, 2),
                "loss_plus_100bps_eur": round(euro_impact_100bps, 2),
                "proxy": matched_proxy or "Model Inferred",
            }
        )

    # Scenari di stress curva
    scenarios = {}
    parallel_shifts = [-100.0, -50.0, 25.0, 50.0, 100.0, 200.0]
    for bps in parallel_shifts:
        dy = bps / 10000.0
        pct_chg = -w_mod_dur * dy + 0.5 * w_convexity * (dy**2)
        scenarios[f"Parallel_{int(bps):+d}bps"] = {
            "name": f"Shift Parallelo {int(bps):+d} bps",
            "rate_change_bps": bps,
            "fi_return_pct": round(pct_chg * 100.0, 2),
            "fi_pnl_eur": round(total_fi_val * pct_chg, 2),
            "portfolio_pnl_eur": round(total_fi_val * pct_chg, 2),
            "portfolio_impact_pct": round((total_fi_val * pct_chg / total_port_val * 100.0) if total_port_val > 0 else 0.0, 2),
        }

    # Twist Scenarios (Steepener / Flattener)
    twist_definitions = {
        "Bull_Steepener": {"name": "Bull Steepener (Tagli aggressivi a breve)", "dy_2y": -0.0100, "dy_10y": -0.0025},
        "Bear_Steepener": {"name": "Bear Steepener (Pressioni inflative a lungo)", "dy_2y": 0.0025, "dy_10y": 0.0100},
        "Bull_Flattener": {"name": "Bull Flattener (Rally su scadenze lunghe)", "dy_2y": -0.0025, "dy_10y": -0.0100},
        "Bear_Flattener": {"name": "Bear Flattener (Stretta tassi a breve termine)", "dy_2y": 0.0100, "dy_10y": 0.0025},
    }
    for code, tw in twist_definitions.items():
        dy2, dy10 = tw["dy_2y"], tw["dy_10y"]
        # Impatto stimato con Key Rate Durations
        pct_chg = -(krd_accum["2Y"] * dy2 + krd_accum["5Y"] * ((dy2 + dy10) / 2.0) + krd_accum["10Y"] * dy10 + krd_accum["30Y"] * dy10)
        scenarios[code] = {
            "name": tw["name"],
            "fi_return_pct": round(pct_chg * 100.0, 2),
            "fi_pnl_eur": round(total_fi_val * pct_chg, 2),
            "portfolio_pnl_eur": round(total_fi_val * pct_chg, 2),
            "portfolio_impact_pct": round((total_fi_val * pct_chg / total_port_val * 100.0) if total_port_val > 0 else 0.0, 2),
        }

    return {
        "has_fixed_income": True,
        "total_portfolio_value": round(total_port_val, 2),
        "fixed_income_value": round(total_fi_val, 2),
        "fixed_income_weight_pct": round((total_fi_val / total_port_val * 100.0) if total_port_val > 0 else 0.0, 2),
        "weighted_mac_duration": round(w_mac_dur, 2),
        "weighted_mod_duration": round(w_mod_dur, 2),
        "weighted_convexity": round(w_convexity, 3),
        "portfolio_dv01": round(total_dv01, 2),
        "key_rate_durations": {k: round(v, 2) for k, v in krd_accum.items()},
        "curve_stress_scenarios": scenarios,
        "fi_positions_breakdown": detailed_positions,
    }
