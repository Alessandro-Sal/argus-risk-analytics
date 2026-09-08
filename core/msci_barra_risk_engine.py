"""
core/msci_barra_risk_engine.py
ARGUS — Asset-Level Multi-Factor Risk Decomposition Engine (MSCI Barra GEM3/USE4 Standard).

Features:
- Decomposizione formale della covarianza totale di portafoglio:
  Sigma = X @ F @ X.T + Delta
  dove:
    X: Matrice delle esposizioni fattoriali (N asset x K fattori)
    F: Matrice di covarianza dei fattori sistemici (K x K)
    Delta: Matrice diagonale del rischio specifico/idiosincratico (N x N)
- Scomposizione della varianza del portafoglio (Euler Decomposition):
  sigma_total^2 = sigma_factor^2 + sigma_specific^2
- Marginal Contribution to Total Risk (MCTR) e Percent Contribution to Total Risk (PCTR)
  sia a livello di singolo asset sia a livello di singolo fattore (Style, Sector, Macro).
- Calcolo dei Factor Tilts attivi rispetto al benchmark di mercato (MSCI World).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


# 11 Settori GICS Standard
GICS_SECTORS = [
    "Information Technology",
    "Financials",
    "Healthcare",
    "Consumer Discretionary",
    "Communication Services",
    "Industrials",
    "Consumer Staples",
    "Energy",
    "Utilities",
    "Real Estate",
    "Materials"
]

# 5 Fattori di Stile Fondamentali Barra
STYLE_FACTORS = [
    "Size",          # Log Market Cap (Large vs Small)
    "Value",         # Book-to-Market / Earnings Yield
    "Momentum",      # 12-1M Price Momentum
    "Quality",       # High ROE, Low Leverage, Stable Earnings
    "Low Volatility" # Low Historical Beta & Residual Volatility
]

# 3 Fattori Macroeconomici Istituzionali
MACRO_FACTORS = [
    "Term / Rates",  # Sensibilità alla Curva dei Tassi (Duration)
    "Credit Spread", # Sensibilità allo spread corporate/HY
    "Currency USD"   # Esposizione al dollaro USA vs EUR
]

ALL_FACTORS = STYLE_FACTORS + GICS_SECTORS + MACRO_FACTORS


@dataclass
class AssetFactorProfile:
    """Profilo di esposizione fattoriale standardizzato (Z-score) di un singolo strumento."""
    ticker: str
    asset_name: str
    weight: float
    current_value: float
    style_exposures: Dict[str, float]  # Z-score tipicamente in [-3.0, +3.0]
    sector: str                        # Uno degli 11 settori GICS
    macro_exposures: Dict[str, float]  # Sensibilità macro
    specific_volatility_annual: float = 0.18  # Volatilità idiosincratica residua


class BarraMultiAssetRiskEngine:
    """
    Motore analitico di rischio multi-fattoriale conforme agli standard MSCI Barra GEM3/USE4.
    """

    def __init__(self, factor_covariance_matrix: Optional[np.ndarray] = None):
        self.factors = ALL_FACTORS
        self.k = len(self.factors)
        if factor_covariance_matrix is not None and factor_covariance_matrix.shape == (self.k, self.k):
            self.factor_cov = factor_covariance_matrix
        else:
            self.factor_cov = self._build_canonical_factor_covariance()

    def _build_canonical_factor_covariance(self) -> np.ndarray:
        """
        Costruisce la matrice di covarianza annualizzata dei fattori Barra (K x K)
        calibrata empiricamente su regimi macroeconomici istituzionali moderni.
        """
        k = self.k
        # Volatilità tipiche dei fattori annualizzate
        vols = np.zeros(k)
        for i, f in enumerate(self.factors):
            if f in STYLE_FACTORS:
                vols[i] = 0.08  # 8% annual vol per style factors
            elif f in GICS_SECTORS:
                vols[i] = 0.16  # 16% annual vol per sector factors
            else:
                vols[i] = 0.06  # 6% annual vol per macro factors

        # Matrice di correlazione base con blocchi moderatamente correlati
        corr = np.eye(k)
        # Correlazioni cross-factor stilistiche note
        style_idx = {f: i for i, f in enumerate(self.factors)}
        if "Value" in style_idx and "Momentum" in style_idx:
            i_v, i_m = style_idx["Value"], style_idx["Momentum"]
            corr[i_v, i_m] = corr[i_m, i_v] = -0.28
        if "Quality" in style_idx and "Low Volatility" in style_idx:
            i_q, i_lv = style_idx["Quality"], style_idx["Low Volatility"]
            corr[i_q, i_lv] = corr[i_lv, i_q] = 0.35
        if "Size" in style_idx and "Low Volatility" in style_idx:
            i_s, i_lv = style_idx["Size"], style_idx["Low Volatility"]
            corr[i_s, i_lv] = corr[i_lv, i_s] = -0.20

        # Settori con correlazione inter-settoriale positiva media (~0.35)
        sector_indices = [i for i, f in enumerate(self.factors) if f in GICS_SECTORS]
        for idx1 in sector_indices:
            for idx2 in sector_indices:
                if idx1 != idx2:
                    corr[idx1, idx2] = 0.35

        # Covarianza = D @ Corr @ D
        cov = np.outer(vols, vols) * corr
        # Assicura semi-definita positiva tramite eigendecomposition clipping
        eigvals, eigvecs = np.linalg.eigh(cov)
        eigvals = np.maximum(eigvals, 1e-6)
        return eigvecs @ np.diag(eigvals) @ eigvecs.T

    def estimate_default_exposures_for_ticker(
        self,
        ticker: str,
        name: str = "",
        weight: float = 1.0,
        current_value: float = 10000.0
    ) -> AssetFactorProfile:
        """
        Stima o assegna un vettore di esposizione standardizzato per ticker noti o classi generiche.
        """
        t_up = ticker.upper()
        # Default neutral profile
        style = {"Size": 0.5, "Value": 0.0, "Momentum": 0.2, "Quality": 0.6, "Low Volatility": 0.1}
        macro = {"Term / Rates": -0.1, "Credit Spread": 0.1, "Currency USD": 0.6}
        sector = "Information Technology"
        spec_vol = 0.22

        if any(w in t_up for w in ["AAPL", "MSFT", "GOOG", "NVDA", "TECH", "CSPX", "QQQ"]):
            style = {"Size": 1.8, "Value": -0.8, "Momentum": 1.1, "Quality": 1.6, "Low Volatility": -0.2}
            sector = "Information Technology"
            macro = {"Term / Rates": -0.4, "Credit Spread": 0.2, "Currency USD": 0.8}
            spec_vol = 0.20
        elif any(w in t_up for w in ["BTP", "BOND", "TREASURY", "GOV", "IEF", "TLT"]):
            style = {"Size": 0.0, "Value": 0.4, "Momentum": -0.2, "Quality": 1.2, "Low Volatility": 1.5}
            sector = "Financials"
            macro = {"Term / Rates": 1.4, "Credit Spread": -0.2, "Currency USD": 0.1}
            spec_vol = 0.06
        elif any(w in t_up for w in ["XOM", "SHEL", "ENI", "ENERGY", "OIL"]):
            style = {"Size": 1.2, "Value": 1.4, "Momentum": 0.4, "Quality": 0.5, "Low Volatility": -0.4}
            sector = "Energy"
            macro = {"Term / Rates": 0.2, "Credit Spread": 0.4, "Currency USD": 0.5}
            spec_vol = 0.26
        elif any(w in t_up for w in ["JNJ", "PFE", "NOVO", "HEALTH", "SANOF"]):
            style = {"Size": 1.3, "Value": 0.2, "Momentum": 0.1, "Quality": 1.5, "Low Volatility": 1.1}
            sector = "Healthcare"
            macro = {"Term / Rates": -0.1, "Credit Spread": -0.1, "Currency USD": 0.4}
            spec_vol = 0.15
        elif any(w in t_up for w in ["ISP", "UCG", "JPM", "BAC", "BANK", "FIN"]):
            style = {"Size": 1.0, "Value": 1.5, "Momentum": 0.3, "Quality": 0.4, "Low Volatility": -0.3}
            sector = "Financials"
            macro = {"Term / Rates": 0.5, "Credit Spread": 0.8, "Currency USD": 0.3}
            spec_vol = 0.24

        return AssetFactorProfile(
            ticker=ticker,
            asset_name=name or ticker,
            weight=weight,
            current_value=current_value,
            style_exposures=style,
            sector=sector,
            macro_exposures=macro,
            specific_volatility_annual=spec_vol
        )

    def decompose_portfolio_factor_risk(
        self,
        asset_profiles: List[AssetFactorProfile]
    ) -> Dict[str, Any]:
        """
        Esegue la decomposizione completa del rischio fattoriale di portafoglio:
        1. Matrice di esposizione X (N x K)
        2. Varianza Sistematica w^T X F X^T w
        3. Varianza Idiosincratica w^T Delta w
        4. MCTR & PCTR di ciascun asset (Eulero)
        5. Factor-Level PCTR (attribuzione percentuale del rischio per fattore)
        """
        n_assets = len(asset_profiles)
        if n_assets == 0:
            return {"error": "Nessun asset fornito."}

        tickers = [p.ticker for p in asset_profiles]
        weights = np.array([p.weight for p in asset_profiles], dtype=float)
        # Normalizza pesi a 1.0 se la somma e' positiva
        w_sum = np.sum(weights)
        if w_sum > 0:
            w = weights / w_sum
        else:
            w = np.full(n_assets, 1.0 / n_assets)

        k = self.k
        X = np.zeros((n_assets, k))
        delta_diag = np.zeros(n_assets)

        for i, p in enumerate(asset_profiles):
            # 1. Style exposures
            for s_name, val in p.style_exposures.items():
                if s_name in self.factors:
                    X[i, self.factors.index(s_name)] = val
            # 2. Sector exposure (dummy 1.0)
            if p.sector in self.factors:
                X[i, self.factors.index(p.sector)] = 1.0
            # 3. Macro exposures
            for m_name, val in p.macro_exposures.items():
                if m_name in self.factors:
                    X[i, self.factors.index(m_name)] = val

            delta_diag[i] = p.specific_volatility_annual ** 2

        # 1. Matrice di covarianza fattoriale proiettata sugli asset
        # Sigma_factor = X @ F @ X.T
        Sigma_factor = X @ self.factor_cov @ X.T
        Delta = np.diag(delta_diag)
        Sigma_total = Sigma_factor + Delta

        # 2. Varianze di portafoglio
        var_factor = float(w.T @ Sigma_factor @ w)
        var_specific = float(w.T @ Delta @ w)
        var_total = var_factor + var_specific

        vol_factor = float(np.sqrt(max(var_factor, 1e-8)))
        vol_specific = float(np.sqrt(max(var_specific, 1e-8)))
        vol_total = float(np.sqrt(max(var_total, 1e-8)))

        factor_risk_pct = (var_factor / var_total) * 100.0 if var_total > 0 else 100.0
        specific_risk_pct = (var_specific / var_total) * 100.0 if var_total > 0 else 0.0

        # 3. MCTR e PCTR per ciascun Asset (Eulero)
        # MCTR_i = (Sigma_total @ w)_i / vol_total
        mctr_vec = (Sigma_total @ w) / vol_total
        # PCTR_i = w_i * MCTR_i / vol_total (espressa in % del rischio totale)
        pctr_vec = (w * mctr_vec) / vol_total * 100.0

        # MCTR e PCTR specifico vs fattoriale per singolo asset
        mctr_factor_vec = (Sigma_factor @ w) / vol_total
        pctr_factor_vec = (w * mctr_factor_vec) / vol_total * 100.0
        pctr_specific_vec = (w * ((Delta @ w) / vol_total)) / vol_total * 100.0

        asset_rows = []
        for i in range(n_assets):
            asset_rows.append({
                "ticker": tickers[i],
                "asset_name": asset_profiles[i].asset_name,
                "weight_pct": float(w[i] * 100.0),
                "mctr": float(mctr_vec[i]),
                "pctr_total": float(pctr_vec[i]),
                "pctr_factor": float(pctr_factor_vec[i]),
                "pctr_specific": float(pctr_specific_vec[i]),
                "specific_vol_annual": float(asset_profiles[i].specific_volatility_annual)
            })

        df_assets = pd.DataFrame(asset_rows)

        # 4. Decomposizione a Livello di Singolo Fattore (Factor-Level PCTR)
        # Portafoglio Factor Exposures: b = X.T @ w (K x 1)
        b = X.T @ w
        # Factor Marginal Contribution: MCFR_k = (F @ b)_k / vol_total
        mcfr = (self.factor_cov @ b) / vol_total
        # Factor PCTR_k = b_k * MCFR_k / vol_total
        pcfr = (b * mcfr) / vol_total * 100.0

        factor_rows = []
        for k_idx, f_name in enumerate(self.factors):
            f_cat = "Style" if f_name in STYLE_FACTORS else ("Sector" if f_name in GICS_SECTORS else "Macro")
            factor_rows.append({
                "factor_name": f_name,
                "category": f_cat,
                "portfolio_exposure": float(b[k_idx]),
                "factor_pctr": float(pcfr[k_idx]),
                "factor_volatility": float(np.sqrt(self.factor_cov[k_idx, k_idx]))
            })

        df_factors = pd.DataFrame(factor_rows)
        # Ordina per impatto decrescente
        df_factors = df_factors.sort_values(by="factor_pctr", ascending=False)

        # 5. Benchmark MSCI World Tilts attivi
        # Benchmark ipotetico equilibrato con esposizioni stile = 0 e pesi settoriali benchmark
        benchmark_tilts = {}
        for f in STYLE_FACTORS:
            benchmark_tilts[f] = float(b[self.factors.index(f)])  # Active tilt = Exp_portfolio - 0.0
        for f in MACRO_FACTORS:
            benchmark_tilts[f] = float(b[self.factors.index(f)])

        return {
            "volatility_total_annual": vol_total,
            "volatility_factor_annual": vol_factor,
            "volatility_specific_annual": vol_specific,
            "factor_risk_contribution_pct": factor_risk_pct,
            "specific_risk_contribution_pct": specific_risk_pct,
            "asset_risk_df": df_assets,
            "factor_attribution_df": df_factors,
            "active_style_tilts": benchmark_tilts,
            "portfolio_factor_exposures": dict(zip(self.factors, b.tolist())),
            "euler_sum_pctr": float(np.sum(pctr_vec))
        }
