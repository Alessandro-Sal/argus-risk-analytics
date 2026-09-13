"""
core/stochastic_kernel.py
ARGUS — Unified Stochastic Simulation Kernel & Robust Cholesky Decomposer.

Provides institutional numerical primitives for:
1. Robust positive semi-definite (PSD) Cholesky factorization with eigenvalue clipping.
2. Vectorized multivariate shock generation (Gaussian, Student-t fat-tailed).
3. Thread-safe Random Number Generation (NumPy default_rng PCG64).
"""

from typing import Optional, Tuple

import numpy as np


def robust_cholesky(matrix: np.ndarray, min_eigval: float = 1e-8) -> np.ndarray:
    """
    Esegue la fattorizzazione di Cholesky A = L @ L.T in modo numericamente stabile.
    In caso di matrice semi-definita o singolare (es. correlazioni stimate imperfette),
    applica una proiezione spettrale troncando gli autovalori a min_eigval.

    Parameters
    ----------
    matrix : np.ndarray
        Matrice quadrata simmetrica di covarianza o correlazione (N x N).
    min_eigval : float
        Soglia minima per gli autovalori nel fallback spettrale.

    Returns
    -------
    np.ndarray
        Matrice triangolare inferiore L (N x N) tale che L @ L.T approx matrix.
    """
    mat = np.asarray(matrix, dtype=np.float64)
    if mat.ndim != 2 or mat.shape[0] != mat.shape[1]:
        raise ValueError(f"Attesa matrice quadrata 2D, ricevuta forma: {mat.shape}")

    n = mat.shape[0]
    if n == 1:
        return np.sqrt(np.maximum(mat, min_eigval))

    # Tenta Cholesky standard con leggera regolarizzazione di Tikhonov
    jittered = mat + np.eye(n) * min_eigval
    try:
        return np.linalg.cholesky(jittered)
    except np.linalg.LinAlgError:
        # Fallback: decomposizione spettrale (Eigendecomposition / Nearest PSD)
        eigvals, eigvecs = np.linalg.eigh(mat)
        eigvals_clipped = np.maximum(eigvals, min_eigval)
        return eigvecs @ np.diag(np.sqrt(eigvals_clipped))


def generate_correlated_shocks(
    lower_cholesky: np.ndarray,
    n_steps: int,
    n_simulations: int,
    rng: Optional[np.random.Generator] = None,
    distribution: str = "gaussian",
    df_deg: int = 5,
) -> np.ndarray:
    """
    Genera un tensore di shock casuali correlati multivariati.

    Parameters
    ----------
    lower_cholesky : np.ndarray
        Fattore triangolare inferiore L (N x N) derivato da robust_cholesky.
    n_steps : int
        Orizzonte temporale (numero di passi / giorni / anni).
    n_simulations : int
        Numero di cammini stocastici da simulare.
    rng : Optional[np.random.Generator]
        Generatore di numeri casuali thread-safe NumPy.
    distribution : str
        'gaussian' (default) oppure 'student_t' per code spesse.
    df_deg : int
        Gradi di libertà per la distribuzione Student-t (default 5).

    Returns
    -------
    np.ndarray
        Tensore di shock con forma (n_steps, n_assets, n_simulations).
    """
    if rng is None:
        rng = np.random.default_rng()

    n_assets = lower_cholesky.shape[0]

    if distribution == "student_t":
        raw = rng.standard_t(df_deg, size=(n_steps, n_assets, n_simulations))
        if df_deg > 2:
            raw = raw * np.sqrt((df_deg - 2) / df_deg)
    else:
        raw = rng.normal(0.0, 1.0, size=(n_steps, n_assets, n_simulations))

    # Moltiplicazione lungo l'asse degli asset: L @ raw
    # raw ha forma (T, N, Sims) -> swapaxes -> (T, Sims, N) @ L.T
    raw_transposed = np.transpose(raw, (0, 2, 1))  # (T, Sims, N)
    corr_transposed = raw_transposed @ lower_cholesky.T  # (T, Sims, N)
    return np.transpose(corr_transposed, (0, 2, 1))  # (T, N, Sims)
