import pandas as pd
import numpy as np

def slice_returns_series(sr_port, lookback_sel):
    r = sr_port.dropna()
    if lookback_sel == "Ultimo Anno (252g)":
        r = r.tail(252)
    elif lookback_sel == "Ultimi 3 Anni":
        r = r.tail(252 * 3)
    elif lookback_sel == "Ultimi 5 Anni":
        r = r.tail(252 * 5)
    return r

def test_var_lookback_slicing():
    # Mock return series with 1000 days
    np.random.seed(42)
    sr_port = pd.Series(np.random.normal(0, 0.01, 1000))
    
    # 1. Storico Completo
    r_all = slice_returns_series(sr_port, "Storico Completo")
    assert len(r_all) == 1000
    
    # 2. 1 Year lookback
    r_1y = slice_returns_series(sr_port, "Ultimo Anno (252g)")
    assert len(r_1y) == 252
    assert abs(r_1y.iloc[0] - sr_port.iloc[1000 - 252]) < 1e-7
    
    # 3. 3 Years lookback
    r_3y = slice_returns_series(sr_port, "Ultimi 3 Anni")
    assert len(r_3y) == 756
    assert abs(r_3y.iloc[0] - sr_port.iloc[1000 - 756]) < 1e-7
    
    # 4. Underflow (slicing more than available)
    r_5y = slice_returns_series(sr_port, "Ultimi 5 Anni") # requires 1260 days, only 1000 available
    assert len(r_5y) == 1000 # returns all available days
