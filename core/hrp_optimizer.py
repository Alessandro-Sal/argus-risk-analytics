# ============================================================
# core/hrp_optimizer.py
# ARGUS — Risk Analytics & BI Platform
# Hierarchical Risk Parity (HRP) Engine (Marcos López de Prado)
# ============================================================

r"""
Hierarchical Risk Parity (HRP) Portfolio Optimization Engine.

Implements Marcos López de Prado's (2016) machine-learning approach to portfolio allocation.
HRP addresses Markowitz's Critical Line Algorithm (CLA) instabilities by replacing the ill-conditioned
matrix inversion $\Sigma^{-1}$ with a top-down tree clustering and recursive bisection approach:

1. **Tree Clustering**:
   Calculates correlation distance metric:
   $$D_{i,j} = \sqrt{\frac{1 - \rho_{i,j}}{2}}$$
   and generates a hierarchical tree using agglomerative clustering.

2. **Quasi-Diagonalization**:
   Reorders rows and columns of the covariance matrix so that strongly correlated assets
   are adjacent along the diagonal.

3. **Recursive Bisection**:
   Divides the ordered asset tree into sub-clusters and assigns weights inversely proportional
   to cluster variance:
   $$\alpha_1 = 1 - \frac{V_1}{V_1 + V_2}, \quad \alpha_2 = 1 - \alpha_1$$
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import squareform


def compute_hrp_portfolio(df_returns: pd.DataFrame, linkage_method: str = "single") -> Dict[str, Any]:
    """
    Computes optimal portfolio allocation according to Hierarchical Risk Parity (HRP).

    Parameters:
        df_returns (pd.DataFrame):
            Historical daily returns where columns represent asset tickers and index represents dates.
        linkage_method (str, default='single'):
            Scipy hierarchical linkage criterion: 'single', 'complete', 'average', or 'ward'.

    Returns:
        Dict[str, Any]:
            Dictionary containing:
            - `weights` (Dict[str, float]): Normalized optimal weights summing to 1.0.
            - `df_weights` (pd.DataFrame): Tabular weights and percentages sorted descending.
            - `expected_return_pct` (float): Annualized expected portfolio return.
            - `volatility_annual_pct` (float): Annualized portfolio volatility.
            - `sharpe_ratio` (float): Annualized portfolio Sharpe ratio (r_f = 0 default benchmark).
            - `sorted_assets` (List[str]): Quasi-diagonalized dendrogram asset order.
            - `linkage_matrix` (np.ndarray): Scipy hierarchical linkage matrix.
            - `correlation_matrix` (pd.DataFrame): Asset return correlation matrix.
            - `covariance_matrix` (pd.DataFrame): Daily return covariance matrix.

    Examples:
        >>> import pandas as pd
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> rets = pd.DataFrame({
        ...     'EQ1': np.random.normal(0.001, 0.02, 50),
        ...     'EQ2': np.random.normal(0.001, 0.02, 50),
        ...     'FI1': np.random.normal(0.0002, 0.004, 50)
        ... })
        >>> res = compute_hrp_portfolio(rets)
        >>> 'weights' in res
        True
        >>> round(sum(res['weights'].values()), 2)
        1.0
    """
    if df_returns.empty or df_returns.shape[1] < 2:
        return {}

    # Clean NaN and calculate covariance and correlation matrices
    clean_returns = df_returns.dropna(axis=0, how="any")
    if clean_returns.shape[0] < 5:
        clean_returns = df_returns.fillna(0.0)

    cov = clean_returns.cov()
    corr = clean_returns.corr().fillna(0.0)
    assets = list(clean_returns.columns)

    # 1. Correlation Distance Metric: D_i,j = sqrt( (1 - rho_i,j) / 2 )
    dist = np.sqrt(np.clip((1.0 - corr.values) / 2.0, 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)

    # Condense distance matrix for Scipy linkage
    condensed_dist = squareform(dist, checks=False)
    link = sch.linkage(condensed_dist, method=linkage_method)

    # 2. Quasi-Diagonalization: Obtain dendrogram order
    sorted_indices = _get_quasi_diag(link)
    sorted_assets = [assets[i] for i in sorted_indices]

    # 3. Recursive Bisection
    weights_series = _get_rec_bisection(cov, sorted_assets)
    weights_series = weights_series / weights_series.sum()

    # Portfolio metrics
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
    """
    Reorders original indices to maximize adjacency of similar clusters along the diagonal.

    Parameters:
        link (np.ndarray): Scipy hierarchical linkage matrix of shape (N-1, 4).

    Returns:
        List[int]: Quasi-diagonalized sequence of asset indices.
    """
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
    r"""
    Calculates sub-cluster variance using Inverse-Variance Allocation (IVP).

    Parameters:
        cov (pd.DataFrame): Full covariance matrix of daily asset returns.
        cluster_items (List[str]): List of asset tickers in the current sub-cluster.

    Returns:
        float: Inverse-variance weighted sub-cluster variance $V = w^T \Sigma w$.
    """
    cov_slice = cov.loc[cluster_items, cluster_items].values
    ivp = 1.0 / np.diag(cov_slice)
    ivp = ivp / np.sum(ivp)
    w = ivp.reshape(-1, 1)
    cluster_variance = np.dot(np.dot(w.T, cov_slice), w)[0, 0]
    return float(cluster_variance)


def _get_rec_bisection(cov: pd.DataFrame, sorted_assets: List[str]) -> pd.Series:
    """
    Executes top-down recursive bisection allocating weights inversely to cluster variance.

    Parameters:
        cov (pd.DataFrame): Full covariance matrix of asset returns.
        sorted_assets (List[str]): Ordered list of tickers after quasi-diagonalization.

    Returns:
        pd.Series: Unnormalized or relative weight allocations across all assets.
    """
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

                # Inverse variance allocation factor: alpha = 1 - var_left / (var_left + var_right)
                total_var = var_left + var_right + 1e-12
                alpha = 1.0 - (var_left / total_var)

                weights[left_cluster] *= alpha
                weights[right_cluster] *= (1.0 - alpha)

                next_clusters.append(left_cluster)
                next_clusters.append(right_cluster)

        clusters = next_clusters
    return weights
