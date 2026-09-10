# Quickstart: From Raw CSV to HRP in 5 Lines

The core philosophy of **ARGUS Headless** is maximum analytical power with minimal boilerplate. Quantitative researchers can perform machine-learning portfolio allocation directly from raw asset price or return CSV files.

---

## 5-Line HRP Portfolio Optimization

```python
import pandas as pd
from core.hrp_optimizer import compute_hrp_portfolio

# 1. Load historical asset returns
df_returns = pd.read_csv("portfolio_returns.csv", index_col="Date", parse_dates=True)

# 2. Compute Hierarchical Risk Parity allocation
result = compute_hrp_portfolio(df_returns, linkage_method="single")

# 3. Print optimal allocation weights
print(result["df_weights"])
```

### Sample Output

```
  ticker  hrp_weight  hrp_weight_pct
0    BND    0.485210           48.52
1   MSFT    0.283120           28.31
2   AAPL    0.231670           23.17
```

---

## End-to-End Walkthrough with Synthetic Data

If you do not have a CSV on disk yet, run this complete snippet in your Python terminal or Jupyter notebook:

```python
import numpy as np
import pandas as pd
from core.hrp_optimizer import compute_hrp_portfolio

# Generate synthetic asset daily returns
np.random.seed(42)
dates = pd.date_range("2025-01-01", periods=252, freq="B")
df_returns = pd.DataFrame({
    "AAPL": np.random.normal(0.0008, 0.018, 252),  # Tech Equity
    "NVDA": np.random.normal(0.0012, 0.026, 252),  # High Beta Semiconductor
    "BND":  np.random.normal(0.0002, 0.003, 252),  # US Total Bond Market
    "GLD":  np.random.normal(0.0004, 0.009, 252),  # Gold Safe Haven
}, index=dates)

# Run HRP Engine
result = compute_hrp_portfolio(df_returns)

print(f"Annualized Expected Return: {result['expected_return_pct']:.2f}%")
print(f"Annualized Volatility:      {result['volatility_annual_pct']:.2f}%")
print(f"Portfolio Sharpe Ratio:     {result['sharpe_ratio']:.2f}")
print("\nOptimal Asset Weights:")
for ticker, weight in result["weights"].items():
    print(f"  {ticker:6s}: {weight * 100:6.2f}%")
```

---

## Consuming HRP via the REST API

If your architecture uses a microservice model (e.g. Node.js backend, C# trading system, or mobile app), query the ARGUS REST API directly:

```bash
curl -X POST http://localhost:8000/api/v1/optimize/hrp \
  -H "Content-Type: application/json" \
  -d '{
    "asset_returns": {
      "AAPL": [0.01, -0.02, 0.015, 0.004, -0.008, 0.012],
      "MSFT": [0.008, -0.015, 0.011, 0.002, -0.005, 0.009],
      "BND": [0.001, 0.002, -0.001, 0.000, 0.001, -0.001]
    },
    "linkage_method": "single"
  }'
```

### JSON Response

```json
{
  "weights": {
    "BND": 0.658211,
    "MSFT": 0.187324,
    "AAPL": 0.154465
  },
  "expected_return_pct": 8.4215,
  "volatility_annual_pct": 6.8912,
  "sharpe_ratio": 1.222,
  "sorted_assets": ["BND", "AAPL", "MSFT"]
}
```
