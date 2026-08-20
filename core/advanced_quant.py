"""
ARGUS — Risk Analytics Platform
Core Module: Advanced Quantitative Models (Frontier Quant Engine)
Includes:
1. Asymmetric Tail Copula Models (Clayton & Gumbel Tail Dependence)
2. Kelly Criterion & Fractional Kelly Position Sizing
3. Equal Risk Contribution (ERC / Risk Parity Portfolio Optimizer)
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
from typing import Dict, Any, Optional, List


# ==============================================================================
# 1. TAIL COPULA MODELS (CLAYTON & GUMBEL ASYMMETRIC DEPENDENCE)
# ==============================================================================

def compute_tail_copula_matrix(
    returns_df: pd.DataFrame,
    quantile_threshold: float = 0.05
) -> dict:
    """
    Calcola la matrice di dipendenza di coda asimmetrica (Tail Copula Dependence)
    tra tutti gli asset in portafoglio.
    
    Permette di quantificare la probabilità di crash congiunto (Lower Tail Dependence λ_L)
    e boom congiunto (Upper Tail Dependence λ_U), superando l'assunzione di correlazione
    lineare gaussiana simmetrica.
    """
    if returns_df is None or returns_df.empty or returns_df.shape[1] < 2:
        return {
            "lambda_lower_df": pd.DataFrame(),
            "lambda_upper_df": pd.DataFrame(),
            "asymmetry_df": pd.DataFrame(),
            "contagion_pairs": [],
            "mean_tail_dependence": 0.0
        }

    clean_df = returns_df.dropna()
    if len(clean_df) < 30:
        return {
            "lambda_lower_df": pd.DataFrame(),
            "lambda_upper_df": pd.DataFrame(),
            "asymmetry_df": pd.DataFrame(),
            "contagion_pairs": [],
            "mean_tail_dependence": 0.0
        }

    tickers = list(clean_df.columns)
    n = len(tickers)
    t_len = len(clean_df)

    # 1. Trasformazione alle marginali uniformi (Rank Transformation empirical CDF)
    uniforms = clean_df.rank(axis=0) / (t_len + 1.0)

    lambda_lower = np.zeros((n, n))
    lambda_upper = np.zeros((n, n))
    clayton_lambda_l = np.zeros((n, n))

    q = max(0.01, min(0.20, quantile_threshold))

    for i in range(n):
        for j in range(n):
            if i == j:
                lambda_lower[i, j] = 1.0
                lambda_upper[i, j] = 1.0
                clayton_lambda_l[i, j] = 1.0
                continue

            u_i = uniforms.iloc[:, i].values
            u_j = uniforms.iloc[:, j].values

            # Dipendenza Empirica Coda Inferiore (Joint Crash Probability)
            # P(U_j <= q | U_i <= q) = P(U_i <= q, U_j <= q) / q
            both_lower = np.sum((u_i <= q) & (u_j <= q))
            i_lower = np.sum(u_i <= q)
            emp_lambda_l = (both_lower / i_lower) if i_lower > 0 else 0.0

            # Dipendenza Empirica Coda Superiore (Joint Boom Probability)
            both_upper = np.sum((u_i >= 1.0 - q) & (u_j >= 1.0 - q))
            i_upper = np.sum(u_i >= 1.0 - q)
            emp_lambda_u = (both_upper / i_upper) if i_upper > 0 else 0.0

            # Clayton Copula (Parametrica tramite Kendall Tau)
            try:
                tau, _ = stats.kendalltau(clean_df.iloc[:, i], clean_df.iloc[:, j])
                if np.isnan(tau):
                    tau = 0.0
                if tau > 0.01:
                    theta = (2.0 * tau) / (1.0 - tau)
                    clay_l = 2.0 ** (-1.0 / max(0.001, theta))
                else:
                    clay_l = 0.0
            except Exception:
                clay_l = 0.0

            # Blend robusto empirico + parametrico
            final_l = float(np.clip(0.6 * emp_lambda_l + 0.4 * clay_l, 0.0, 1.0))
            final_u = float(np.clip(emp_lambda_u, 0.0, 1.0))

            lambda_lower[i, j] = final_l
            lambda_upper[i, j] = final_u
            clayton_lambda_l[i, j] = clay_l

    lambda_lower_df = pd.DataFrame(lambda_lower, index=tickers, columns=tickers)
    lambda_upper_df = pd.DataFrame(lambda_upper, index=tickers, columns=tickers)
    asymmetry_df = lambda_lower_df - lambda_upper_df

    # Identificazione delle coppie ad alto rischio contagio (λ_L > 0.35)
    contagion_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            l_val = lambda_lower[i, j]
            if l_val >= 0.30:
                contagion_pairs.append({
                    "pair": f"{tickers[i]} ⇄ {tickers[j]}",
                    "lambda_lower": round(float(l_val), 3),
                    "lambda_upper": round(float(lambda_upper[i, j]), 3),
                    "asymmetry": round(float(asymmetry_df.iloc[i, j]), 3),
                    "risk_level": "🔴 Alto Contagio" if l_val >= 0.45 else "🟡 Moderato"
                })

    contagion_pairs = sorted(contagion_pairs, key=lambda x: x["lambda_lower"], reverse=True)

    # Media non-diagonale
    mask = ~np.eye(n, dtype=bool)
    mean_tail = float(np.mean(lambda_lower[mask])) if np.any(mask) else 0.0

    return {
        "lambda_lower_df": lambda_lower_df,
        "lambda_upper_df": lambda_upper_df,
        "asymmetry_df": asymmetry_df,
        "contagion_pairs": contagion_pairs,
        "mean_tail_dependence": round(mean_tail, 3)
    }


# ==============================================================================
# 2. KELLY CRITERION & FRACTIONAL KELLY SIZING
# ==============================================================================

def compute_kelly_criterion_sizing(
    returns_df: pd.DataFrame,
    current_weights: Optional[dict] = None,
    risk_free_rate: float = 0.02
) -> pd.DataFrame:
    """
    Calcola l'allocazione ottimale secondo il Criterio di Kelly (Full Kelly, Half-Kelly, Quarter-Kelly).
    
    Formula Continua: f* = (μ - Rf) / σ^2
    Formula Bernoulli: f* = (p * (b + 1) - 1) / b
    dove p = win rate, b = rapporto medio vincita/perdita.
    """
    if returns_df is None or returns_df.empty:
        return pd.DataFrame()

    clean_df = returns_df.dropna()
    if clean_df.empty:
        return pd.DataFrame()

    cur_w = current_weights or {}
    results = []

    for col in clean_df.columns:
        r_series = clean_df[col].dropna()
        if len(r_series) < 15:
            continue

        mean_daily = r_series.mean()
        std_daily = r_series.std()
        
        # Annualizzazione
        ann_mu = mean_daily * 252.0
        ann_vol = std_daily * np.sqrt(252.0)
        ann_var = (ann_vol ** 2.0) if ann_vol > 0 else 0.0001

        # Metriche Bernoulli
        pos_ret = r_series[r_series > 0]
        neg_ret = r_series[r_series < 0]
        
        win_rate = len(pos_ret) / len(r_series) if len(r_series) > 0 else 0.5
        avg_win = pos_ret.mean() if len(pos_ret) > 0 else 0.001
        avg_loss = abs(neg_ret.mean()) if len(neg_ret) > 0 else 0.001
        b_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0

        # Kelly Continuo (Gaussian / Modern Portfolio Theory)
        excess_ret = ann_mu - risk_free_rate
        f_continuous = excess_ret / ann_var if ann_var > 0 else 0.0

        # Kelly Discreto (Bernoulli)
        f_bernoulli = (win_rate * (b_ratio + 1.0) - 1.0) / b_ratio if b_ratio > 0 else 0.0

        # Robust Blend
        f_star_raw = 0.5 * f_continuous + 0.5 * f_bernoulli if f_continuous > 0 and f_bernoulli > 0 else max(0.0, f_continuous)
        
        # Vincolo a valori positivi non a leva illimitata
        full_kelly = float(np.clip(f_star_raw, 0.0, 1.5))
        half_kelly = full_kelly / 2.0
        quarter_kelly = full_kelly / 4.0

        act_w = cur_w.get(col, 0.0)

        # Delta & Diagnostica
        delta_w = act_w - half_kelly
        if act_w > full_kelly:
            status = "🔴 Sovra-Allocato (Alto Rischio Drawdown)"
        elif act_w < quarter_kelly and full_kelly > 0.15:
            status = "🟢 Sotto-Allocato (Margine di Espansione)"
        else:
            status = "⚪ Equilibrato (Zona Half-Kelly)"

        results.append({
            "Ticker": col,
            "Rendimento Annuo": f"{ann_mu * 100:+.2f}%",
            "Volatilità Annua": f"{ann_vol * 100:.2f}%",
            "Win Rate": f"{win_rate * 100:.1f}%",
            "Win/Loss Ratio": f"{b_ratio:.2f}x",
            "Peso Attuale": f"{act_w * 100:.2f}%",
            "Half-Kelly (Target)": f"{half_kelly * 100:.2f}%",
            "Full Kelly": f"{full_kelly * 100:.2f}%",
            "Quarter Kelly": f"{quarter_kelly * 100:.2f}%",
            "Delta vs Half-Kelly": f"{delta_w * 100:+.2f}%",
            "Stato Allocazione": status
        })

    return pd.DataFrame(results)


def compute_interactive_trade_kelly(
    win_rate_pct: float,
    payoff_ratio: float,
    portfolio_capital_eur: float = 100000.0,
    stop_loss_pct: float = 5.0
) -> dict:
    """
    Calcola il dimensionamento monetario e percentuale ottimale di una singola operazione (Trade Sizing)
    secondo il Criterio di Kelly, Half-Kelly e Quarter-Kelly con vincoli di stop-loss.
    """
    p = max(0.01, min(0.99, win_rate_pct / 100.0))
    b = max(0.01, payoff_ratio)
    
    # Kelly fraction: f* = p - (1-p)/b = (p*(b+1) - 1)/b
    f_star = (p * (b + 1.0) - 1.0) / b
    
    full_kelly_pct = max(0.0, min(100.0, f_star * 100.0))
    half_kelly_pct = full_kelly_pct / 2.0
    quarter_kelly_pct = full_kelly_pct / 4.0
    
    sl_dec = max(0.005, stop_loss_pct / 100.0)
    
    risk_full_eur = portfolio_capital_eur * (full_kelly_pct / 100.0)
    risk_half_eur = portfolio_capital_eur * (half_kelly_pct / 100.0)
    risk_quarter_eur = portfolio_capital_eur * (quarter_kelly_pct / 100.0)
    
    pos_size_half_eur = min(portfolio_capital_eur * 1.5, risk_half_eur / sl_dec)
    
    drawdown_risk = "🟢 Basso (< 5%)" if half_kelly_pct < 15.0 else ("🟡 Medio (5-15%)" if half_kelly_pct < 30.0 else "🔴 Elevato (> 15%)")
    
    growth_rate = (p * np.log(1 + f_star * b) + (1 - p) * np.log(max(0.001, 1 - f_star))) * 100.0 if f_star > 0 else 0.0
    
    return {
        "full_kelly_pct": round(full_kelly_pct, 2),
        "half_kelly_pct": round(half_kelly_pct, 2),
        "quarter_kelly_pct": round(quarter_kelly_pct, 2),
        "risk_full_eur": round(risk_full_eur, 2),
        "risk_half_eur": round(risk_half_eur, 2),
        "risk_quarter_eur": round(risk_quarter_eur, 2),
        "pos_size_half_eur": round(pos_size_half_eur, 2),
        "expected_growth_rate": round(growth_rate, 3),
        "drawdown_risk": drawdown_risk,
        "edge_pct": round((p * b - (1 - p)) * 100.0, 2)
    }


# ==============================================================================
# 3. EQUAL RISK CONTRIBUTION (ERC / RISK PARITY)
# ==============================================================================

def compute_equal_risk_contribution_portfolio(returns_df: pd.DataFrame) -> dict:
    """
    Risolve il problema di ottimizzazione Equal Risk Contribution (ERC / Risk Parity).
    
    Ciascun asset contribuisce esattamente per la stessa frazione (1/N) alla volatilità
    totale di portafoglio:
    RC_i = w_i * (Σ w)_i / σ_p = σ_p / N  per ogni i.
    """
    if returns_df is None or returns_df.empty or returns_df.shape[1] < 2:
        return {
            "weights": {},
            "expected_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "risk_contributions_pct": {},
            "success": False
        }

    # Sostituzione inf e clipping per evitare che anomalie o split sporchino i rendimenti
    clean_df = returns_df.replace([np.inf, -np.inf], np.nan).clip(lower=-0.95, upper=3.0)
    # Bonifica NaN multi-mercato per evitare che dropna() elimini troppi giorni di borsa
    clean_df_no_nan = clean_df.dropna(axis=0, how="any")
    if clean_df_no_nan.shape[0] >= 15:
        clean_df = clean_df_no_nan
    else:
        clean_df = clean_df.fillna(0.0)

    tickers = list(clean_df.columns)
    n = len(tickers)
    if n < 2 or clean_df.empty:
        return {
            "weights": {t: 1.0 / n for t in tickers},
            "expected_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "risk_contributions_pct": {t: 100.0 / n for t in tickers},
            "success": False
        }

    # Covarianza Ledoit-Wolf per evitare singolarità e sovrastima del rumore
    try:
        lw = LedoitWolf().fit(clean_df)
        cov_matrix = lw.covariance_ * 252.0
    except Exception:
        cov_matrix = clean_df.cov().fillna(0.0).values * 252.0

    # Garanzia simmetria e semi-definitezza positiva
    cov_matrix = (cov_matrix + cov_matrix.T) / 2.0
    try:
        min_eig = np.min(np.real(np.linalg.eigvals(cov_matrix)))
        if min_eig < 1e-6:
            cov_matrix += (1e-6 - min_eig) * np.eye(cov_matrix.shape[0])
    except Exception:
        pass

    mean_returns = clean_df.mean().values * 252.0

    # Funzione Obiettivo ERC: minimizzare la dispersione dei contributi percentuali al rischio rispetto a 1/N
    def _erc_objective(w):
        w = np.array(w)
        port_var = float(w.T @ cov_matrix @ w)
        if port_var <= 0:
            return 1e6
        # RC_pct_i = w_i * (Σ w)_i / σ_p^2
        risk_contributions_pct = (w * (cov_matrix @ w)) / port_var
        target_rc = 1.0 / n
        return np.sum((risk_contributions_pct - target_rc) ** 2)

    # Vincoli e Limiti: pesi positivi e somma a 1
    init_weights = np.ones(n) / n
    bounds = tuple((0.001, 0.99) for _ in range(n))
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})

    opt_res = minimize(
        _erc_objective,
        init_weights,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 600, 'ftol': 1e-9}
    )

    if opt_res.success:
        opt_w = opt_res.x
    else:
        # Fallback rapido con ottimizzazione L-BFGS-B o inverse volatility
        try:
            vols = np.sqrt(np.diag(cov_matrix))
            inv_vols = 1.0 / np.where(vols > 0, vols, 1.0)
            opt_w = inv_vols / np.sum(inv_vols)
        except Exception:
            opt_w = init_weights

    # Normalizzazione finale
    opt_w = np.clip(opt_w, 0.0, 1.0)
    if np.sum(opt_w) > 0:
        opt_w = opt_w / np.sum(opt_w)
    else:
        opt_w = init_weights

    port_ret = float(np.clip(opt_w @ mean_returns, -2.0, 5.0))
    port_var = float(opt_w.T @ cov_matrix @ opt_w)
    port_vol = float(np.clip(np.sqrt(max(1e-6, port_var)), 0.001, 3.0))
    sharpe = float((port_ret - 0.03) / port_vol) if port_vol > 0 else 0.0

    # Calcolo esatto dei Risk Contributions
    marginal_risk = (cov_matrix @ opt_w) / port_vol
    rc_absolute = opt_w * marginal_risk
    rc_pct = (rc_absolute / port_vol) * 100.0

    weights_dict = {t: float(round(opt_w[i], 4)) for i, t in enumerate(tickers)}
    rc_pct_dict = {t: float(round(rc_pct[i], 2)) for i, t in enumerate(tickers)}

    return {
        "weights": weights_dict,
        "expected_return": round(port_ret, 4),
        "volatility": round(port_vol, 4),
        "sharpe_ratio": round(sharpe, 2),
        "risk_contributions_pct": rc_pct_dict,
        "success": bool(opt_res.success)
    }
