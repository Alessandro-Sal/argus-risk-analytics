# ============================================================
# core/hrp_optimizer.py
# ARGUS — Risk Analytics & BI Platform
# Hierarchical Risk Parity (HRP) Engine (Marcos López de Prado)
# ============================================================

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import squareform


def compute_hrp_portfolio(df_returns: pd.DataFrame, linkage_method: str = "single") -> Dict[str, Any]:
    """
    Calcola l'allocazione ottima secondo l'algoritmo Hierarchical Risk Parity (HRP)
    sviluppato da Marcos López de Prado (2016).

    Fasi dell'algoritmo:
    1. Tree Clustering (Distanza di correlazione e Linkage Gerarchico)
    2. Quasi-Diagonalization (Riordinamento della matrice di covarianza)
    3. Recursive Bisection (Allocazione gerarchica inversa alla varianza di cluster)
    """
    if df_returns.empty or df_returns.shape[1] < 2:
        return {}

    # Bonifica NaN e calcolo matrici di covarianza e correlazione
    clean_returns = df_returns.dropna(axis=0, how="any")
    if clean_returns.shape[0] < 5:
        clean_returns = df_returns.fillna(0.0)

    cov = clean_returns.cov()
    corr = clean_returns.corr().fillna(0.0)
    assets = list(clean_returns.columns)

    # 1. Matrice di Distanza di Correlazione: D_i,j = sqrt( (1 - rho_i,j) / 2 )
    dist = np.sqrt(np.clip((1.0 - corr.values) / 2.0, 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)

    # Condensazione matrice per linkage scipy
    condensed_dist = squareform(dist, checks=False)
    link = sch.linkage(condensed_dist, method=linkage_method)

    # 2. Quasi-Diagonalization: Ottenimento dell'ordinamento dendrogramma
    sorted_indices = _get_quasi_diag(link)
    sorted_assets = [assets[i] for i in sorted_indices]

    # 3. Recursive Bisection
    weights_series = _get_rec_bisection(cov, sorted_assets)
    weights_series = weights_series / weights_series.sum()

    # Calcolo metriche di portafoglio HRP
    weights_vec = weights_series[assets].values
    mean_ret = clean_returns.mean().values * 252.0
    port_expected_return = float(np.dot(weights_vec, mean_ret))
    port_variance = float(np.dot(weights_vec, np.dot(cov.values * 252.0, weights_vec)))
    port_volatility = float(np.sqrt(max(1e-8, port_variance)))
    port_sharpe = float(port_expected_return / port_volatility) if port_volatility > 0 else 0.0

    df_weights = pd.DataFrame({
        "ticker": list(weights_series.index),
        "hrp_weight": weights_series.values,
        "hrp_weight_pct": weights_series.values * 100.0
    }).sort_values(by="hrp_weight", ascending=False)

    return {
        "weights": weights_series.to_dict(),
        "df_weights": df_weights,
        "expected_return_pct": port_expected_return * 100.0,
        "volatility_annual_pct": port_volatility * 100.0,
        "sharpe_ratio": port_sharpe,
        "sorted_assets": sorted_assets,
        "linkage_matrix": link,
        "correlation_matrix": corr,
        "covariance_matrix": cov
    }


def _get_quasi_diag(link: np.ndarray) -> List[int]:
    """Riordina gli indici originali per massimizzare la vicinanza dei cluster simili."""
    link = link.astype(int)
    num_items = link[-1, 3]
    order = [link[-1, 0], link[-1, 1]]

    while any(i >= num_items for i in order):
        new_order = []
        for i in order:
            if i >= num_items:
                cluster_idx = i - num_items
                new_order.append(link[cluster_idx, 0])
                new_order.append(link[cluster_idx, 1])
            else:
                new_order.append(i)
        order = new_order
    return order


def _get_cluster_var(cov: pd.DataFrame, cluster_items: List[str]) -> float:
    """Calcola la varianza minima di un sotto-cluster usando la formula Inverse-Variance Allocation (IVP)."""
    cov_slice = cov.loc[cluster_items, cluster_items].values
    ivp = 1.0 / np.diag(cov_slice)
    ivp = ivp / np.sum(ivp)
    w = ivp.reshape(-1, 1)
    cluster_variance = np.dot(np.dot(w.T, cov_slice), w)[0, 0]
    return float(cluster_variance)


def _get_rec_bisection(cov: pd.DataFrame, sorted_assets: List[str]) -> pd.Series:
    """Esegue la bisezione ricorsiva dei cluster per ripartire i pesi inversamente alla varianza."""
    weights = pd.Series(1.0, index=sorted_assets)
    clusters = [sorted_assets]

    while len(clusters) > 0:
        next_clusters = []
        for cluster in clusters:
            if len(cluster) > 1:
                mid = len(cluster) // 2
                left_cluster = cluster[:mid]
                right_cluster = cluster[mid:]

                var_left = _get_cluster_var(cov, left_cluster)
                var_right = _get_cluster_var(cov, right_cluster)

                # Allocazione proporzionale inversa: alpha = 1 - var_left / (var_left + var_right)
                total_var = var_left + var_right + 1e-12
                alpha = 1.0 - (var_left / total_var)

                weights[left_cluster] *= alpha
                weights[right_cluster] *= (1.0 - alpha)

                next_clusters.append(left_cluster)
                next_clusters.append(right_cluster)

        clusters = next_clusters
    return weights
