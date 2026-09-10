# Institutional Technical Whitepaper

<p align="center">
  <strong>ARGUS Enterprise Platform: Architecture, Quantitative Risk Governance & Bitemporal Auditing</strong><br/>
  <em>A Modern Framework for SGRs, Family Offices, and Institutional Asset Managers</em>
</p>

---

## Executive Summary

Traditional wealth management and risk platforms suffer from three systemic vulnerabilities:
1. **Gaussian Blindness**: Assuming normal return distributions, leading to the catastrophic underestimation of tail risks and drawdowns during market dislocations.
2. **Markowitz Optimization Instability**: Inverting ill-conditioned covariance matrices, which amplifies estimation noise and leads to extreme, erratic rebalancing turnovers.
3. **Destructive Database Mutations**: Using conventional `UPDATE` and `DELETE` queries that destroy historical states, rendering backward-looking MiFID II and GIPS performance audits difficult or inaccurate.

The **ARGUS Platform** introduces a unified, headless architecture combining:
- **Modified Cornish-Fisher Value-at-Risk and Expected Shortfall** for non-Gaussian tails.
- **Hierarchical Risk Parity (HRP)** machine learning portfolio allocation.
- **Square-Root Law Market Impact & Almgren-Chriss (2000)** optimal execution.
- **ISO/IEC 9075:2011 Bitemporal Persistence & Merkle Tree** immutable audit trails.

---

## 1. Non-Gaussian Tail Risk Modeling

### 1.1 The Failure of Mean-Variance Models
Standard financial models assume returns $r_t \sim \mathcal{N}(\mu, \sigma^2)$. In reality, market assets exhibit pronounced asymmetry ($\mathcal{S} < 0$) and fat tails ($\mathcal{K} > 0$). Under Gaussian assumptions:
- A $4\sigma$ shock is expected once every 125 years.
- In actual financial markets, $4\sigma$ and $5\sigma$ events occur several times per decade.

### 1.2 Cornish-Fisher Expansion and Coherence
ARGUS computes the higher-moment adjusted quantile:

$$z_{\text{CF}} = z_\alpha + \frac{1}{6}(z_\alpha^2 - 1)\mathcal{S} + \frac{1}{24}(z_\alpha^3 - 3z_\alpha)\mathcal{K} - \frac{1}{36}(2z_\alpha^3 - 5z_\alpha)\mathcal{S}^2$$

To comply with **Basel III / FRTB**, the platform computes the Modified Expected Shortfall (CVaR) using the Boudt-Peterson-Croux (2008) formulation, satisfying the sub-additivity condition of Artzner et al. (1999):

$$\text{CVaR}_\alpha(X + Y) \le \text{CVaR}_\alpha(X) + \text{CVaR}_\alpha(Y)$$

---

## 2. Machine-Learning Portfolio Allocation (HRP)

Classical Markowitz Critical Line Algorithm (CLA) solves:

$$\min_w \quad w^T \Sigma w \quad \text{s.t.} \quad w^T \mathbf{1} = 1, \; w \ge 0$$

When the condition number $\kappa(\Sigma) = \lambda_{\max} / \lambda_{\min}$ is large, matrix inversion $\Sigma^{-1}$ magnifies sample error. HRP (López de Prado 2016) replaces matrix inversion with:
1. **Metric Distance Tree Clustering**: $D_{i,j} = \sqrt{(1 - \rho_{i,j})/2}$.
2. **Quasi-Diagonalization**: Reordering $\Sigma$ so that clustered assets are adjacent.
3. **Recursive Bisection**: Top-down inverse-variance allocation without any matrix inversion.

Empirical simulations demonstrate that HRP achieves significantly lower out-of-sample variance and half the maximum drawdown of CLA in volatile market regimes.

---

## 3. Optimal Algorithmic Execution & Microstructure

When managing multi-million euro rebalances, market impact costs can easily erode investment alpha. ARGUS models total transaction costs $\mathcal{C}_{\text{total}}$ as:

$$\mathcal{C}_{\text{total}} = \text{Commission} + \text{Cost}_{\text{half-spread}} + I_{\text{temp}} + I_{\text{perm}}$$

The **Square-Root Law** is parameterized using daily volatility $\sigma$ and Average Daily Volume ($\text{ADV}$):

$$I_{\text{temp}} = \eta \cdot \sigma \cdot \left(\frac{v_t}{V_t}\right)^{0.5}, \qquad I_{\text{perm}} = \gamma \cdot \sigma \cdot \left(\frac{Q}{\text{ADV}}\right)$$

The platform generates execution schedules for **Almgren-Chriss (2000)** optimal liquidation, **TWAP**, and **VWAP**, with automated generation of **FIX 4.4** blotters and broker-ready CSV files (Interactive Brokers, Directa SIM).

---

## 4. Bitemporal Data Architecture & Cryptographic Audit Trail

### 4.1 Orthogonal Time Dimensions
ARGUS enforces the ISO/IEC 9075:2011 temporal SQL standard:
- **Valid Time ($VT$)**: Real-world occurrence time $[VT_{\text{from}}, VT_{\text{to}})$.
- **System Time ($TT$)**: Transaction knowledge time $[TT_{\text{from}}, TT_{\text{to}})$.

Retroactive dividend adjustments, trade amendments, and backdated corporate actions create new system-time intervals without deleting or altering previous historical knowledge.

### 4.2 Merkle Tree Report Certification
Factsheets exported from the platform contain a SHA-256 Merkle root hash:

$$\text{MerkleRoot} = \mathcal{H}(\mathcal{H}(\text{Pos}_1, \text{Pos}_2), \mathcal{H}(\text{Pos}_3, \dots))$$

This provides institutional stakeholders (auditors, risk committees, custodians) with cryptographic proof of data integrity.

---

## 5. Technology Stack & Operational Architecture

| Component | Technology | Rationale |
|---|---|---|
| **Headless Core** | Python 3.11+, NumPy, SciPy | Native vectorized quantitative performance |
| **Bitemporal OLAP Engine** | DuckDB (In-Process) | Sub-second analytical queries on millions of rows |
| **REST Microservice** | FastAPI, Uvicorn, Pydantic v2 | High-throughput asynchronous API layer |
| **Interactive BI Cockpit** | Streamlit, Plotly | Low-latency exploratory data analytics |
| **Packaging & CI/CD** | PEP 517/621, GitHub Actions | Automated testing, linting, and docs deployment |

---

## 6. Governance & Regulatory Compliance Mapping

- **MiFID II (RTS 28 / Best Execution)**: Comprehensive tracking of slippage and execution performance vs benchmark (TWAP/VWAP).
- **AIFMD / UCITS**: Formal multi-factor stress testing (MSCI Barra, custom macro shocks) and liquidity-adjusted VaR (L-VaR).
- **GIPS (Global Investment Performance Standards)**: Exact point-in-time portfolio reconstruction without look-ahead bias or survivorship distortion.
