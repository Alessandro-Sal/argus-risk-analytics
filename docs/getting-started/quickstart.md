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


---

## Launching the Interactive Institutional Cockpit

To experience the full visual intelligence platform with 22 institutional modules, start the Streamlit application:

```bash
streamlit run src/0_Control_Room.py
```

### 1. Local Workstation Mode (Zero Password)
- When launched on your local machine, ARGUS detects the desktop environment (`is_local_environment() == True`).
- **1-Click Direct Access**: Click **⚡ Entra Subito al Terminale (Alessandro)** to enter immediately without email or password.
- **Auto-Login Persistence**: Enable *"Ricorda ed entra sempre in automatico all'avvio su questo PC"* to bypass the gate automatically on all future local launches.
- **Offline Storage**: Your balances, trades, and wealth records persist to embedded SQLite databases (`data/argus_local.db` and `data/argus_wealth.db`).

### 2. Gated Connection to Supabase Cloud from Local
- To sync or view portfolios on **Supabase Cloud (PostgreSQL)** while running locally, open the left sidebar -> `⚙️ Global Settings -> Tab 3: Database & Network`.
- Select **Supabase Cloud (PostgreSQL)**.
- **Security Check**: ARGUS detects that you are currently in a local unauthenticated session (`is_supabase_cloud_authenticated() == False`) and displays a warning:
  > *⚠️ Per connetterti a Supabase Cloud è richiesta l'autenticazione. Sblocca la connessione nel riquadro sottostante.*
- Expand the `☁️ Cloud Supabase & Deploy Online` panel, enter your Supabase GoTrue account email and password, and click **Accedi**.
- Once validated, your session receives a cryptographic JWT token and your remote PostgreSQL data source is seamlessly unlocked.

### 3. Online Cloud Mode (Streamlit Community Cloud)
- When deployed on a public URL or container, the local passwordless bypass is strictly disabled.
- **Institutional Pre-Splash Gate**: Users must sign in to their encrypted vault (`PBKDF2-HMAC-SHA256` 120,000 iterations), register a new isolated account, or explore via **🧪 Modalità Demo (1-Click)**.
- **Multi-Tenant Data Isolation**: All queries enforce strict tenant filtering by `user_id`, preventing any data leakage across accounts.
