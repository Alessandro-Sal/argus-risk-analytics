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

    q = max(0.01, min(0.20, quantile_threshold))

    # 1. Matrici indicatrici booleane e prodotto matriciale BLAS B^T @ B
    U_mat = uniforms.to_numpy(dtype=np.float64)
    B_lower = (U_mat <= q).astype(np.float64)
    B_upper = (U_mat >= (1.0 - q)).astype(np.float64)

    joint_lower = B_lower.T @ B_lower
    joint_upper = B_upper.T @ B_upper

    counts_lower = np.diag(joint_lower)[:, np.newaxis]
    counts_upper = np.diag(joint_upper)[:, np.newaxis]

    emp_lambda_l = np.divide(joint_lower, counts_lower, out=np.zeros((n, n)), where=counts_lower > 0)
    emp_lambda_u = np.divide(joint_upper, counts_upper, out=np.zeros((n, n)), where=counts_upper > 0)

    # 2. Clayton Copula: calcolo solo triangolo superiore con mirroring simmetrico
    clayton_lambda_l = np.eye(n, dtype=np.float64)
    for i in range(n):
        for j in range(i + 1, n):
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
            clayton_lambda_l[i, j] = clay_l
            clayton_lambda_l[j, i] = clay_l

    # 3. Blend robusto empirico + parametrico vettorizzato
    lambda_lower = np.clip(0.6 * emp_lambda_l + 0.4 * clayton_lambda_l, 0.0, 1.0)
    lambda_upper = np.clip(emp_lambda_u, 0.0, 1.0)
    np.fill_diagonal(lambda_lower, 1.0)
    np.fill_diagonal(lambda_upper, 1.0)

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
    risk_free_rate: float = None
) -> pd.DataFrame:
    """
    Calcola l'allocazione ottimale secondo il Criterio di Kelly (Full Kelly, Half-Kelly, Quarter-Kelly).
    
    Formula Continua: f* = max(0, (μ - Rf) / σ^2)
    Formula Bernoulli: f* = (p * (b + 1) - 1) / b
    dove p = win rate, b = rapporto medio vincita/perdita.
    """
    from core.yield_curve import get_default_risk_free_rate
    if risk_free_rate is None:
        risk_free_rate = get_default_risk_free_rate("EUR")

    if returns_df is None or returns_df.empty:
        return pd.DataFrame()

    cur_w = current_weights or {}
    raw_stats = []
    raw_f_stars = {}

    for col in returns_df.columns:
        r_series = returns_df[col].dropna()
        if len(r_series) < 15:
            continue

        mean_daily = float(r_series.mean())
        std_daily = float(r_series.std())
        
        # Annualizzazione
        ann_mu = mean_daily * 252.0
        ann_vol = std_daily * np.sqrt(252.0)
        ann_var = (ann_vol ** 2.0) if ann_vol > 1e-6 else 0.0001

        # Metriche Bernoulli su sedute attive (escludendo rendimenti flat a 0)
        active_r = r_series[r_series.abs() > 1e-6]
        if len(active_r) < 10:
            active_r = r_series
            
        pos_ret = active_r[active_r > 0]
        neg_ret = active_r[active_r < 0]
        
        win_rate = float(len(pos_ret) / len(active_r)) if len(active_r) > 0 else 0.5
        avg_win = float(pos_ret.mean()) if len(pos_ret) > 0 else 0.001
        avg_loss = float(abs(neg_ret.mean())) if len(neg_ret) > 0 else 0.001
        b_ratio = (avg_win / avg_loss) if avg_loss > 0 else 1.0

        # Kelly Continuo (Excess Return / Varianza)
        excess_ret = ann_mu - risk_free_rate
        f_continuous = (excess_ret / ann_var) if (excess_ret > 0 and ann_var > 0) else 0.0

        # Kelly Discreto (Bernoulli Edge)
        b_edge = (win_rate * (b_ratio + 1.0) - 1.0)
        f_bernoulli = (b_edge / b_ratio) if (b_edge > 0 and b_ratio > 0) else 0.0

        # Kelly robusto (se excess return <= 0, f* = 0)
        if excess_ret <= 0:
            f_star = 0.0
        elif f_bernoulli > 0 and f_continuous > 0:
            f_star = float(0.7 * f_continuous + 0.3 * f_bernoulli)
        else:
            f_star = float(f_continuous)

        raw_f_stars[col] = max(0.0, f_star)
        raw_stats.append({
            "ticker": col,
            "ann_mu": ann_mu,
            "ann_vol": ann_vol,
            "win_rate": win_rate,
            "b_ratio": b_ratio,
            "f_star": f_star,
            "act_w": float(cur_w.get(col, 0.0))
        })

    if not raw_stats:
        return pd.DataFrame()

    # Normalizzazione Multi-Asset a somma 100% per target di portafoglio
    tot_f = sum(raw_f_stars.values())
    results = []

    for item in raw_stats:
        t = item["ticker"]
        f_val = item["f_star"]
        act_w = item["act_w"]
        
        # Target Normalizzato di Portafoglio
        norm_target_w = (f_val / tot_f) if tot_f > 0 else (1.0 / len(raw_stats))
        half_kelly_w = norm_target_w
        quarter_kelly_w = norm_target_w * 0.5
        
        # Standalone Kelly (con leva)
        standalone_full = f_val
        standalone_half = f_val * 0.5
        
        # Delta & Diagnostica
        delta_w = act_w - half_kelly_w
        if f_val <= 1e-4:
            status = "⛔ Nessun Edge (Rf > Rendimento)"
        elif act_w > (half_kelly_w * 1.5):
            status = "🔴 Sovra-Allocato (Alto Rischio)"
        elif act_w < (half_kelly_w * 0.6) and half_kelly_w > 0.03:
            status = "🟢 Sotto-Allocato (Margine Espansione)"
        else:
            status = "⚪ Equilibrato (Zona Half-Kelly)"

        results.append({
            "Ticker": t,
            "Rendimento Annuo": f"{item['ann_mu'] * 100:+.2f}%",
            "Volatilità Annua": f"{item['ann_vol'] * 100:.2f}%",
            "Win Rate": f"{item['win_rate'] * 100:.1f}%",
            "Win/Loss Ratio": f"{item['b_ratio']:.2f}x",
            "Peso Attuale": f"{act_w * 100:.2f}%",
            "Half-Kelly (Target)": f"{half_kelly_w * 100:.2f}%",
            "Full Kelly": f"{standalone_full * 100:.2f}%",
            "Quarter Kelly": f"{quarter_kelly_w * 100:.2f}%",
            "Delta vs Half-Kelly": f"{delta_w * 100:+.2f}%",
            "Stato Allocazione": status
        })

    df_out = pd.DataFrame(results)
    return df_out


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

def compute_equal_risk_contribution_portfolio(returns_df: pd.DataFrame, risk_free_rate: float = None) -> dict:
    """
    Risolve il problema di ottimizzazione Equal Risk Contribution (ERC / Risk Parity).
    
    Ciascun asset contribuisce esattamente per la stessa frazione (1/N) alla volatilità
    totale di portafoglio:
    RC_i = w_i * (Σ w)_i / σ_p = σ_p / N  per ogni i.
    """
    from core.yield_curve import get_default_risk_free_rate
    if risk_free_rate is None:
        risk_free_rate = get_default_risk_free_rate("EUR")

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
    sharpe = float((port_ret - risk_free_rate) / port_vol) if port_vol > 0 else 0.0

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


# ==============================================================================
# 4. LIQUIDITY-ADJUSTED VALUE AT RISK (L-VaR) & ENDOGENOUS LIQUIDATION HORIZON
# ==============================================================================

def compute_liquidity_adjusted_var(
    position_values: Any,
    daily_returns: Optional[pd.DataFrame] = None,
    bid_ask_spreads: Optional[Any] = None,
    spread_volatilities: Optional[Any] = None,
    daily_volumes_eur: Optional[Any] = None,
    confidence: float = 0.95,
    max_adv_participation: float = 0.10,
    cov_matrix: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Calcola il Liquidity-Adjusted VaR (L-VaR) secondo il modello Bangia / Almgren-Chriss.
    
    Supera l'assunzione di liquidabilità immediata e gratuita integrando:
    1. Costo esogeno di allargamento dello spread bid-ask sotto stress:
       Cost_exog = 0.5 * sum(V_i * (S_bar_i + z_alpha * sigma_S_i))
    2. Orizzonte endogeno di smobilizzo ordinato per non superare max_adv_participation (default 10% ADV):
       T_eff = max(V_i / (max_adv_participation * ADV_i))
    3. Scaling del VaR di mercato su T_eff giorni (Square-Root of Time):
       VaR_scaled = VaR_1D * sqrt(T_eff)
    4. L-VaR totale = VaR_scaled + Cost_exog
    """
    pos_arr = np.array(position_values, dtype=float)
    if len(pos_arr) == 0 or np.sum(pos_arr) <= 0:
        return {
            "standard_var_eur": 0.0,
            "exogenous_spread_cost_eur": 0.0,
            "effective_liquidation_days": 1,
            "l_var_total_eur": 0.0,
            "l_var_premium_pct": 0.0,
            "liquidity_haircut_eur": 0.0
        }

    total_val = float(np.sum(pos_arr))
    weights = pos_arr / total_val
    n_assets = len(pos_arr)

    # 1. Calcolo Volatilità di Portafoglio e VaR Standard
    if cov_matrix is not None and cov_matrix.shape == (n_assets, n_assets):
        port_vol = np.sqrt(max(1e-8, float(weights.T @ cov_matrix @ weights)))
    elif daily_returns is not None and not daily_returns.empty:
        clean_ret = daily_returns.dropna()
        if len(clean_ret) >= 5 and clean_ret.shape[1] == n_assets:
            cov_est = clean_ret.cov().values
            port_vol = np.sqrt(max(1e-8, float(weights.T @ cov_est @ weights)))
        else:
            port_vol = 0.0125  # ~20% annualizzata default
    else:
        port_vol = 0.0125

    z_alpha = float(stats.norm.ppf(confidence))
    standard_var_eur = total_val * (z_alpha * port_vol)

    # 2. Costo Esogeno di Spread (Bid-Ask Expansion under Stress)
    if bid_ask_spreads is not None:
        spreads = np.array(bid_ask_spreads, dtype=float)
        if len(spreads) != n_assets:
            spreads = np.full(n_assets, 0.0015)
    else:
        spreads = np.full(n_assets, 0.0015)  # 15 bps default

    if spread_volatilities is not None:
        spread_vols = np.array(spread_volatilities, dtype=float)
        if len(spread_vols) != n_assets:
            spread_vols = spreads * 0.5
    else:
        spread_vols = spreads * 0.5  # Dev. std spread stimata pari al 50% dello spread medio

    stressed_spreads = np.maximum(0.0001, spreads + z_alpha * spread_vols)
    exogenous_spread_cost = float(0.5 * np.sum(pos_arr * stressed_spreads))

    # 3. Orizzonte Endogeno di Liquidazione Prudenziale
    if daily_volumes_eur is not None:
        vols = np.array(daily_volumes_eur, dtype=float)
        if len(vols) == n_assets:
            adv_cap = np.maximum(1000.0, vols * max_adv_participation)
            days_per_asset = np.maximum(1.0, pos_arr / adv_cap)
            effective_days = float(np.max(days_per_asset))
        else:
            effective_days = 1.0
    else:
        effective_days = 1.0

    # Limite prudenziale orizzonte (max 60 giorni lavorativi per non divergere)
    effective_days = min(60.0, max(1.0, effective_days))

    # 4. Scaling del VaR e Calcolo L-VaR
    scaled_var_eur = standard_var_eur * np.sqrt(effective_days)
    l_var_total_eur = scaled_var_eur + exogenous_spread_cost
    liquidity_haircut_eur = l_var_total_eur - standard_var_eur
    l_var_premium_pct = ((l_var_total_eur / max(0.01, standard_var_eur)) - 1.0) * 100.0

    return {
        "confidence": confidence,
        "standard_var_eur": round(standard_var_eur, 2),
        "exogenous_spread_cost_eur": round(exogenous_spread_cost, 2),
        "effective_liquidation_days": int(np.ceil(effective_days)),
        "l_var_total_eur": round(l_var_total_eur, 2),
        "liquidity_haircut_eur": round(liquidity_haircut_eur, 2),
        "l_var_premium_pct": round(l_var_premium_pct, 2)
    }

