import pytest
import numpy as np
import pandas as pd

# Nota: per testare in modo completo risk_engine.py sarebbe necessario 
# fare mocking del database (SQLAlchemy) e dei DataFrame storici.
# Qui aggiungiamo un test matematico di base per verificare che l'ambiente pytest funzioni.

def test_dummy_math():
    """Un test segnaposto per assicurarsi che pytest sia configurato correttamente."""
    returns = pd.Series([0.01, -0.02, 0.03, -0.01])
    assert returns.mean() == pytest.approx(0.0025)
    assert len(returns) == 4

from core.risk_engine import _fifo_engine

def test_fifo_engine_basic_buy():
    # Arrange
    data = {
        "tx_date": ["2023-01-01"],
        "tx_type": ["buy"],
        "quantity": [10.0],
        "price": [100.0],
        "tx_id": [1]
    }
    df = pd.DataFrame(data)

    # Act
    res = _fifo_engine(df)

    # Assert
    assert res["qty_net"] == 10.0
    assert res["avg_cost"] == 100.0
    assert res["realized_pnl"] == 0.0
    assert res["dividends_total"] == 0.0

def test_fifo_engine_partial_sell():
    # Arrange
    data = {
        "tx_date": ["2023-01-01", "2023-01-02"],
        "tx_type": ["buy", "sell"],
        "quantity": [10.0, 4.0],
        "price": [100.0, 150.0],
        "tx_id": [1, 2]
    }
    df = pd.DataFrame(data)

    # Act
    res = _fifo_engine(df)

    # Assert
    assert res["qty_net"] == 6.0
    assert res["avg_cost"] == 100.0
    # 4 * (150 - 100) = 200
    assert res["realized_pnl"] == 200.0
    assert res["dividends_total"] == 0.0

def test_fifo_engine_multiple_lots():
    # Arrange
    # Buy 5 @ 100 (cost 500)
    # Buy 5 @ 120 (cost 600)
    # Sell 7 @ 150 -> consumes 5 @ 100 and 2 @ 120
    # Realized: 5 * (150 - 100) + 2 * (150 - 120) = 250 + 60 = 310
    # Remaining: 3 @ 120, avg cost should be 120.0
    data = {
        "tx_date": ["2023-01-01", "2023-01-02", "2023-01-03"],
        "tx_type": ["buy", "buy", "sell"],
        "quantity": [5.0, 5.0, 7.0],
        "price": [100.0, 120.0, 150.0],
        "tx_id": [1, 2, 3]
    }
    df = pd.DataFrame(data)

    # Act
    res = _fifo_engine(df)

    # Assert
    assert res["qty_net"] == 3.0
    assert res["avg_cost"] == 120.0
    assert res["realized_pnl"] == 310.0
    assert res["dividends_total"] == 0.0

def test_fifo_engine_with_dividends():
    # Arrange
    data = {
        "tx_date": ["2023-01-01", "2023-02-01"],
        "tx_type": ["buy", "dividend"],
        "quantity": [10.0, 1.0],
        "price": [100.0, 25.0],
        "tx_id": [1, 2]
    }
    df = pd.DataFrame(data)

    # Act
    res = _fifo_engine(df)

    # Assert
    assert res["qty_net"] == 10.0
    assert res["avg_cost"] == 100.0
    assert res["dividends_total"] == 25.0


from core.risk_engine import _calc_return_metrics
from core.db_exporter import _safe_float


def test_zero_volatility_sharpe_safe():
    """Verifica che con rendimenti costanti o nulli (volatilità 0) lo Sharpe ratio non esploda né generi overflow."""
    dates = pd.date_range("2023-01-01", periods=100, freq="B")
    sr_portfolio = pd.Series(0.0, index=dates)
    sr_benchmark = pd.Series(0.0, index=dates)
    df_tx = pd.DataFrame([{"tx_date": "2023-01-01"}])
    df_positions = pd.DataFrame([{"current_value": 0.0, "cost_basis": 0.0, "total_return": -15000.0, "dividends_total": 0.0}])

    res = _calc_return_metrics(sr_portfolio, sr_benchmark, df_tx, df_positions)
    
    assert res["sharpe_ratio"] is None or abs(res["sharpe_ratio"]) <= 1000.0
    assert res["portfolio_value"] == 0.0
    assert res["total_pnl"] == -15000.0


def test_safe_float_clamping():
    """Verifica che _safe_float filtri NaN/inf e limiti i decimali ai massimi supportati da MySQL Decimal."""
    assert _safe_float(None) is None
    assert _safe_float(np.nan) is None
    assert _safe_float(np.inf) is None
    assert _safe_float(-np.inf) is None
    
    # Extreme float overflow test
    overflow_val = -4.6462054719669624e+16
    clamped = _safe_float(overflow_val, max_limit=999999.9999, min_limit=-999999.9999)
    assert clamped == -999999.9999
    
    pos_overflow = 1e20
    clamped_pos = _safe_float(pos_overflow, max_limit=999999.9999, min_limit=-999999.9999)
    assert clamped_pos == 999999.9999


from core.risk_engine import _calc_market_risk


def test_parametric_var_drift_sensitivity():
    """
    Verifica che con media di rendimenti positiva (drift positivo), il VaR parametrico
    sia inferiore a quello con drift nullo (riduzione della perdita attesa).
    """
    dates = pd.date_range("2024-01-01", periods=500, freq="B")
    np.random.seed(42)
    vol = 0.01
    white_noise = np.random.normal(0, vol, 500)

    sr_zero_drift = pd.Series(white_noise, index=dates)
    sr_pos_drift = pd.Series(white_noise + 0.002, index=dates)

    sr_bm = pd.Series(white_noise * 0.8, index=dates)

    res_zero = _calc_market_risk(sr_zero_drift, sr_bm, "SPY")
    res_pos = _calc_market_risk(sr_pos_drift, sr_bm, "SPY")

    # A parità di volatilità, un drift positivo deve RIDURRE il VaR parametrico e Cornish-Fisher
    assert res_pos["var_parametric_95"] < res_zero["var_parametric_95"]
    assert res_pos["var_cf_95"] < res_zero["var_cf_95"]
    assert res_pos["var_parametric_95"] > 0
    assert res_pos["var_cf_95"] > 0


def test_market_risk_fama_french_integration():
    """Verifica che _calc_market_risk calcoli correttamente i coefficienti Fama-French integrati."""
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(42)
    sr_p = pd.Series(np.random.normal(0.0005, 0.012, 100), index=dates)
    sr_bm = pd.Series(np.random.normal(0.0004, 0.010, 100), index=dates)

    res = _calc_market_risk(sr_p, sr_bm, "SPY")
    assert "ff_alpha_pct" in res
    assert "ff_beta_mkt" in res
    assert "smb_tilt" in res
    assert "hml_tilt" in res
    assert isinstance(res["ff_alpha_pct"], float)
    assert isinstance(res["ff_beta_mkt"], float)


