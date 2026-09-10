# Optimal Algorithmic Execution & Microstructure

When executing large portfolio rebalances, institutional traders cannot send single market orders without suffering severe price depreciation (**market impact** and **slippage**). 

The ARGUS execution engine (`core/execution_algo.py`) models the trade-off between **market execution impact** (trading too fast) and **market volatility risk** (trading too slowly).

---

## The Almgren-Chriss (2000) Framework

The foundational model developed by **Robert Almgren and Neil Chriss (2000)** formulates optimal liquidation as an optimization problem minimizing expected execution costs subject to a portfolio manager's risk aversion $\lambda$:

$$\min_{x} \quad \mathbb{E}[x] + \lambda \mathbb{V}[x]$$

Where:
- $X$: Total number of shares to liquidate.
- $x_k$: Number of shares remaining at time step $k \in \{0, \dots, N\}$.
- $v_k = x_{k-1} - x_k$: Number of shares traded in interval $k$.
- $\tau$: Length of each execution slice.

### The Objective Function

$$\min_{\{x_k\}} \quad \sum_{k=1}^N \left[ \tau \eta \left(\frac{v_k}{\tau}\right)^2 + \frac{1}{2} \gamma v_k X \right] + \lambda \frac{1}{2} \sigma^2 \sum_{k=1}^N \tau x_k^2$$

The optimal trajectory takes an analytical hyperbolic profile:

$$x_j = \frac{\sinh(\kappa(T - t_j))}{\sinh(\kappa T)} X$$

where the urgency parameter $\kappa$ governs liquidation speed:

$$\kappa \approx \sqrt{\frac{\lambda \sigma^2}{\eta}}$$

---

## Market Microstructure & The Square-Root Law

Empirical research across global equity exchanges (Barra, Kissell-Glantz 2003, Almgren et al. 2005) confirms that price impact follows the **Square-Root Law**:

### 1. Touch Cost (Half-Spread)
The instantaneous friction of crossing the bid-ask spread:

$$\text{Cost}_{\text{spread}} = \frac{1}{2} \cdot s_{\text{bps}}$$

### 2. Temporary Market Impact ($I_{\text{temp}}$)
The concave, dissipative liquidity absorption during interval $t$:

$$I_{\text{temp}} = \eta \cdot \sigma_{\text{daily}} \cdot \left(\frac{v_t}{V_t}\right)^\alpha \times 10^4 \quad (\text{bps})$$

where:
- $\eta \approx 0.142$ is the temporary impact coefficient.
- $v_t / V_t$ is the instantaneous participation rate (POV).
- $\alpha \approx 0.5$ represents the square-root regime.

### 3. Permanent Market Impact ($I_{\text{perm}}$)
The informational price drift caused by revealing order flow to the market:

$$I_{\text{perm}} = \gamma \cdot \sigma_{\text{daily}} \cdot \left(\frac{Q}{\text{ADV}}\right) \times 10^4 \quad (\text{bps})$$

where $\gamma \approx 0.314$ and $Q/\text{ADV}$ is the order size relative to 30-day Average Daily Volume.

---

## Intraday Liquidity Dynamics: The U-Shaped Profile

Market liquidity is non-uniform across the trading day. ARGUS generates normalized quadratic volume curves:

$$V(t) = a(t - 0.45)^2 + b$$

amplified by:
- **Morning Open Rush ($\times 1.35$)**: High volatility and price discovery from 09:00 to 10:30 CET/EST.
- **Midday Lunch Lull**: Lower participation from 12:00 to 14:00.
- **Market-on-Close Rush ($\times 1.55$)**: Institutional fixing auctions from 16:30 to 17:30 MOC.

---

## Execution Routing Strategies

ARGUS implements four core execution strategies:

| Strategy | Mechanism | Best Suited For |
|---|---|---|
| **Almgren-Chriss** | Hyperbolic liquidation curve balancing market risk vs slippage | Large block rebalances with strict risk limits |
| **VWAP** | Volume-Weighted Average Price tracking the intraday U-curve | Benchmark tracking against official day VWAP |
| **TWAP** | Time-Weighted Average Price with uniform time slicing | Low ADV illiquid assets or algorithmic stealth |
| **POV Cap** | Hard ceiling on participation rate ($\le 15\%$ ADV) | Avoiding predatory front-running algorithms |

---

## Institutional Broker Interfaces

ARGUS exports order schedules directly to institutional venues:
- **FIX 4.4 Protocol Blotter**: Standard tag-value messages (`MsgType=D`, `HandlInst=1`, `OrdType=1/2`).
- **Interactive Brokers (IBKR) Basket Trader**: CSV format ready for TWS upload.
- **Directa SIM CSV**: Italian retail & institutional brokerage integration.
