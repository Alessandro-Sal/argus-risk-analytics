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
    face_value: float = 100.0,
    coupon_rate: float = 0.04,
    maturity_years: float = 10.0,
    coupon_frequency: int = 2
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
    face_value: float,
    coupon_rate: float,
    maturity_years: float,
    ytm: float,
    coupon_frequency: int = 2
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
    face_value: float,
    coupon_rate: float,
    maturity_years: float,
    market_price: float,
    coupon_frequency: int = 2
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
    approx_y = (annual_coupon + (face_value - market_price) / max(0.1, maturity_years)) / ((face_value + market_price) / 2.0)
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
    yield_shift_bps: float = 10.0
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
        pct_taylor_2 = (-modified_duration * dy + 0.5 * convexity * (dy ** 2)) * 100.0
        
        sensitivity_rows.append({
            "shift_bps": s_bps,
            "new_ytm_pct": (ytm + dy) * 100.0,
            "exact_price": round(exact_p, 4),
            "pct_change_exact": round(pct_exact, 3),
            "pct_change_duration_only": round(pct_taylor_1, 3),
            "pct_change_duration_plus_convexity": round(pct_taylor_2, 3),
            "convexity_gain_pct": round(pct_taylor_2 - pct_taylor_1, 3)
        })

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
        "sensitivity_table": pd.DataFrame(sensitivity_rows)
    }


# ── 4. Z-SPREAD (ZERO-VOLATILITY SPREAD) SU CURVA NSS ──────────────

def compute_z_spread(
    face_value: float,
    coupon_rate: float,
    maturity_years: float,
    market_price: float,
    spot_curve_fn_or_params: Union[Callable[[float], float], Dict[str, float], None] = None,
    coupon_frequency: int = 2
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
    cds_spread_bps: float,
    recovery_rate: float = 0.40,
    tenors_years: Optional[List[float]] = None
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
        
        rows.append({
            "tenor_years": t,
            "tenor_label": f"{int(t)}Y" if t == int(t) else f"{t}Y",
            "survival_probability_pct": round(float(surv_prob * 100.0), 3),
            "cumulative_default_prob_pct": round(float(cum_pd * 100.0), 3),
            "marginal_default_prob_pct": round(float(marginal_pd * 100.0), 3),
            "annualized_default_rate_pct": round(float(annualized_pd * 100.0), 3)
        })
        prev_pd = cum_pd
        
    df_pd = pd.DataFrame(rows)
    
    return {
        "cds_spread_bps": cds_spread_bps,
        "recovery_rate_pct": recovery_rate * 100.0,
        "loss_given_default_pct": loss_given_default * 100.0,
        "implied_hazard_rate_pct": round(float(hazard_rate * 100.0), 4),
        "default_probability_curve": df_pd
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
        "cds_5y_bps": 88.0
    },
    "DE10Y": {
        "name": "Bund Decennale Repubblica Federale Tedesca 2.50%",
        "issuer": "Bundesrepublik Deutschland",
        "coupon_rate": 0.025,
        "maturity_years": 10.0,
        "market_price": 99.80,
        "currency": "EUR",
        "coupon_freq": 1,
        "cds_5y_bps": 12.0
    },
    "US10Y": {
        "name": "US 10-Year Treasury Note 4.25%",
        "issuer": "US Department of the Treasury",
        "coupon_rate": 0.0425,
        "maturity_years": 10.0,
        "market_price": 98.90,
        "currency": "USD",
        "coupon_freq": 2,
        "cds_5y_bps": 34.0
    },
    "CORP_ENI": {
        "name": "ENI SpA Sustainability-Linked Bond 3.875%",
        "issuer": "ENI SpA (Corporate)",
        "coupon_rate": 0.03875,
        "maturity_years": 6.0,
        "market_price": 99.20,
        "currency": "EUR",
        "coupon_freq": 1,
        "cds_5y_bps": 65.0
    }
}
