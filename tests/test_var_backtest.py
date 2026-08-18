import pandas as pd
import numpy as np

def get_basel_zone(exc_count, expected):
    if exc_count <= expected:
        return "🟢 Modello Valido (Conservativo)"
    elif exc_count <= expected * 1.5:
        return "🟡 Modello Accettabile (Sotto-stima lieve)"
    else:
        return "🔴 Modello Debole (Sotto-stima grave)"

def test_basel_zone_classification():
    expected = 12.6  # 252 * 0.05
    
    # 0 to 12 breaches should be Green
    assert get_basel_zone(0, expected) == "🟢 Modello Valido (Conservativo)"
    assert get_basel_zone(5, expected) == "🟢 Modello Valido (Conservativo)"
    assert get_basel_zone(12, expected) == "🟢 Modello Valido (Conservativo)"
    
    # 13 to 18 breaches should be Yellow (expected * 1.5 = 18.9)
    assert get_basel_zone(13, expected) == "🟡 Modello Accettabile (Sotto-stima lieve)"
    assert get_basel_zone(18, expected) == "🟡 Modello Accettabile (Sotto-stima lieve)"
    
    # 19+ breaches should be Red
    assert get_basel_zone(19, expected) == "🔴 Modello Debole (Sotto-stima grave)"
    assert get_basel_zone(30, expected) == "🔴 Modello Debole (Sotto-stima grave)"

def test_var_breaches_counting():
    # 20 days of simulated returns: 18 normal, 2 crolli
    returns = pd.Series([
        0.005, 0.002, -0.001, 0.008, 0.004, -0.003, 0.001, 0.006, 0.002, -0.002,
        0.005, -0.001, 0.003, 0.007, 0.004, -0.005, 0.002, 0.001,
        -0.035, -0.045  # Breaches (below -3.0%)
    ])
    
    threshold = -0.030  # VaR threshold at -3.0%
    
    breaches = len(returns[returns < threshold])
    assert breaches == 2
