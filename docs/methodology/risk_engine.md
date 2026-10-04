# Non-Gaussian Tail Risk & Cornish-Fisher Expansion

Standard portfolio theory (Markowitz 1952) and classical risk metrics assume that asset returns are identically and independently distributed according to a normal Gaussian distribution:

$$r \sim \mathcal{N}(\mu, \sigma^2)$$

However, empirical financial time series systematically violate Gaussianity. Asset return distributions display:
1. **Negative Asymmetry (Skewness $\mathcal{S} < 0$)**: Asymmetric risk where market drawdowns are sharper and faster than market rallies.
2. **Heavy Tails (Excess Kurtosis $\mathcal{K} > 0$)**: Leptokurtic fat tails where extreme market shocks occur with a probability orders of magnitude greater than predicted by the 3-sigma rule.

---

## The Cornish-Fisher Quantile Expansion

To overcome the catastrophic underestimation of tail risk by Gaussian models, ARGUS computes the **Cornish-Fisher expansion** (Cornish & Fisher 1937). Given a target confidence level $\alpha$ (e.g. $\alpha = 0.05$ for 95% VaR), let $z_\alpha = \Phi^{-1}(\alpha)$ be the standard normal critical quantile ($z_{0.05} \approx -1.64485$).

The modified Cornish-Fisher quantile $z_{\text{CF}}$ accounts for the sample skewness $\mathcal{S}$ and excess kurtosis $\mathcal{K}$:

$$z_{\text{CF}} = z_\alpha + \frac{1}{6}(z_\alpha^2 - 1)\mathcal{S} + \frac{1}{24}(z_\alpha^3 - 3z_\alpha)\mathcal{K} - \frac{1}{36}(2z_\alpha^3 - 5z_\alpha)\mathcal{S}^2$$

### Monotonicity Guardrails

When extreme sample skewness or kurtosis is present, high-order polynomial expansions can suffer from non-monotonicity (reversal of quantiles). ARGUS enforces institutional guardrails:
- Skewness is clamped: $\mathcal{S} \in [-3.0, +3.0]$
- Excess kurtosis is clamped: $\mathcal{K} \in [-1.0, +10.0]$
- Monotonicity check: if $\alpha < 0.5$ and $z_{\text{CF}} > 0$, the expansion reverts conservatively to standard Gaussian $z_\alpha$.

The Cornish-Fisher Value at Risk is defined as:

$$\text{VaR}_{\alpha}^{\text{CF}} = - \left(\mu + z_{\text{CF}} \cdot \sigma\right)$$

---

## Modified Expected Shortfall (CVaR)

Value at Risk is not a coherent risk measure because it violates sub-additivity:

$$\text{VaR}(X + Y) \not\le \text{VaR}(X) + \text{VaR}(Y)$$

To provide institutional compliance with **Basel III / FRTB (Fundamental Review of the Trading Book)**, ARGUS implements the **Modified Conditional Value at Risk (mCVaR)** developed by **Boudt, Peterson & Croux (2008)**:

$$\text{CVaR}_\alpha^{\text{CF}} = -\mathbb{E}[R \mid R \le -\text{VaR}_\alpha^{\text{CF}}]$$

Analytically expressed:

$$\text{CVaR}_\alpha^{\text{CF}} = -\mu + \frac{\sigma}{\alpha} \cdot \Psi(z_\alpha)$$

where the polynomial tail expectation kernel $\Psi(z_\alpha)$ is:

$$\Psi(z_\alpha) = \phi(z_\alpha) + \frac{\mathcal{S}}{6} z_\alpha \phi(z_\alpha) + \frac{\mathcal{K}}{24}(z_\alpha^2 - 1)\phi(z_\alpha) - \frac{\mathcal{S}^2}{36}(2z_\alpha^3 - 5z_\alpha + \dots)\phi(z_\alpha)$$

where $\phi(\cdot)$ is the standard normal probability density function (PDF).

---

## Coherent Risk Monotonicity Guarantee

In every market condition, ARGUS guarantees the mathematical coherence constraint:

$$\text{CVaR}_\alpha \ge \text{VaR}_\alpha$$

If non-linear numerical artefacts occur due to sparse sample tails, the engine automatically clamps $\text{CVaR}_\alpha = \max(\text{CVaR}_\alpha, 1.05 \cdot \text{VaR}_\alpha)$.

---

## Temporal Scaling & The Square-Root of Time ($\sqrt{t}$) Rule

### Theoretical Foundations
The standard square-root of time scaling rule for Value at Risk and Volatility:

$$\sigma_{T} = \sigma_1 \times \sqrt{T}, \quad \text{VaR}_\alpha(T) = \text{VaR}_\alpha(1) \times \sqrt{T}$$

is analytically exact **if and only if** consecutive asset returns $r_t$ satisfy:
1. **Independent and Identically Distributed (i.i.d.)**: $\text{Cov}(r_t, r_{t-k}) = 0$ for all lag $k > 0$.
2. **Finite Second Moments with Gaussian Stability**: Returns follow a stable Lévy distribution (specifically the Gaussian distribution, where the sum of normals is normal).

### Statistical Limitations on Fat-Tailed & Clustered Series
In empirical financial time series, the $\sqrt{t}$ rule suffers from known quantitative biases:
- **Volatility Clustering (ARCH/GARCH effects)**: Conditional variance is serially correlated. A shock today increases volatility tomorrow, leading $\sqrt{t}$ to underestimate short-term multi-day risk during crisis regimes.
- **Leptokurtosis & Central Limit Convergence**: Under independent fat-tailed distributions, the Central Limit Theorem (CLT) causes sum distributions over longer horizons ($T \ge 20$) to converge toward Gaussianity slower than $\sqrt{t}$ anticipates, leading to potential mis-estimation of multi-day tail quantiles.
- **Mean Reversion & Auto-correlation**: High autocorrelation in illiquid or fixed income assets causes variance to scale at $T^\alpha$ where $\alpha \ne 0.5$.

### ARGUS Solution: GARCH(1,1) & Filtered Historical Simulation (FHS)
To overcome the structural deficiencies of crude $\sqrt{t}$ scaling for multi-horizon risk assessments, ARGUS provides:
1. **GARCH(1,1) Dynamic Term-Structure**: Explicit forward volatility projection accounting for persistent variance regimes $\sigma_{t+h}^2 = \sigma_L^2 + (\alpha + \beta)^h (\sigma_t^2 - \sigma_L^2)$.
2. **Filtered Historical Simulation (FHS - Barone-Adesi, Giannopoulos & Vosper 1999)**: Non-parametric bootstrapping on standardized residuals $\epsilon_t = \frac{r_t}{\sigma_t}$ combined with conditional volatility forecasts, preserving empirical tail dependence without imposing $\sqrt{t}$ Gaussian assumptions.

---

## Model Risk Management & Continuous Validation (SR 11-7)

In alignment with **Federal Reserve SR 11-7 / OCC 2011-12** guidelines, the analytical engine is verified via automated quantitative unit tests (`tests/test_model_risk_audit.py`):
1. **Axiomatic Coherence**: Monotonicity of historical and parametric VaR and CVaR.
2. **Peak-to-Trough Drawdown**: Exact verification of Maximum Drawdown and High-Water Mark tracking against theoretical paths.
3. **FIFO Accounting with Fees**: Verification of acquisition cost capitalization and selling fee deduction under Italian fiscal law (TUIR Art. 68 c. 6).
4. **Covariance Robustness & PSD**: Numerical verification of symmetry, positive semi-definiteness, and Ledoit-Wolf shrinkage condition number regularization.
5. **Amortization Exactness**: French constant payment loan schedule convergence to zero balance.

---

## Extreme Value Theory (EVT) Peaks-Over-Threshold (POT) & GPD

When estimating risk in deep tail regions (e.g. 99.0% and 99.9% confidence levels), empirical quantiles become noisy due to sparse observations, while parametric Gaussian or Student-$t$ models impose arbitrary global symmetry.

### The Pickands-Balkema-de Haan Theorem
According to the second fundamental theorem of EVT, for a sufficiently high threshold $u$, the distribution of excess losses $Y = X - u$ given $X > u$ converges asymptotically to the **Generalized Pareto Distribution (GPD)**:

$$F_u(y) = \mathbb{P}(X - u \le y \mid X > u) \approx G_{\xi, \sigma}(y) = 1 - \left(1 + \frac{\xi y}{\sigma}\right)^{-1/\xi}$$

where:
- $\xi$ is the **shape parameter** (tail index). $\xi > 0$ denotes heavy, Fréchet-type fat tails common in financial returns.
- $\sigma > 0$ is the **scale parameter**.
- For $\xi = 0$, $G_{0, \sigma}(y) = 1 - \exp(-y/\sigma)$ (exponential distribution).

### EVT Quantile (VaR) and Expected Shortfall (CVaR)
Let $N$ be the total sample size and $N_u$ the number of exceedances ($X_i > u$). The unconditional probability of exceedance is $\mathbb{P}(X > u) = \frac{N_u}{N}$. For a target confidence level $\alpha$ (e.g. $0.99$ or $0.999$):

$$\text{VaR}_\alpha^{\text{EVT}} = u + \frac{\sigma}{\xi} \left[ \left(\frac{N}{N_u} (1 - \alpha)\right)^{-\xi} - 1 \right]$$

For $\xi < 1$, the analytical Conditional Value at Risk (Expected Shortfall) is:

$$\text{CVaR}_\alpha^{\text{EVT}} = \frac{\text{VaR}_\alpha^{\text{EVT}}}{1 - \xi} + \frac{\sigma - \xi u}{1 - \xi}$$

ARGUS fits the parameters $(\xi, \sigma)$ via Maximum Likelihood Estimation (`scipy.stats.genpareto.fit`) on sample thresholds calibrated at the 90th percentile of loss distributions.

---

## Basel IV Regulatory Traffic Light Backtesting Framework

To validate 99% 1-day Value-at-Risk models, the Basel Committee on Banking Supervision (BCBS) establishes the **Regulatory Traffic Light** framework over a standard testing window of $T = 250$ trading days.

### Hypothesis Testing: Kupiec POF Test
The Kupiec (1995) Proportion of Failures (POF) test evaluates whether the empirical exception count $x = \sum_{t=1}^T \mathbf{1}_{\{L_t > \text{VaR}_{0.99, t}\}}$ is statistically consistent with the target failure rate $p = 0.01$:

$$H_0: p = 0.01 \quad \text{vs} \quad H_1: p \ne 0.01$$

The likelihood ratio test statistic is:

$$\text{LR}_{\text{POF}} = -2 \ln \left[ \frac{(1 - p)^{T - x} p^x}{(1 - \hat{p})^{T - x} \hat{p}^x} \right] \sim \chi^2(1)$$

where $\hat{p} = x / T$.

### Christoffersen Independence Test
Even if $x$ is acceptable, violations must not cluster in time. Christoffersen (1998) tests first-order Markov dependence between consecutive hits:

$$\text{LR}_{\text{ind}} = -2 \ln \left[ \frac{(1 - \pi)^{n_{00} + n_{10}} \pi^{n_{01} + n_{11}}}{(1 - \pi_{01})^{n_{00}} \pi_{01}^{n_{01}} (1 - \pi_{11})^{n_{10}} \pi_{11}^{n_{11}}} \right] \sim \chi^2(1)$$

where $n_{ij}$ counts transitions from state $i$ to state $j$ ($0 = \text{no exception}$, $1 = \text{exception}$), $\pi_{01} = \frac{n_{01}}{n_{00} + n_{01}}$, and $\pi_{11} = \frac{n_{11}}{n_{10} + n_{11}}$.

### Conditional Coverage & Basel Zones
The joint conditional coverage test statistic is:

$$\text{LR}_{\text{CC}} = \text{LR}_{\text{POF}} + \text{LR}_{\text{ind}} \sim \chi^2(2)$$

Based on $x$ over 250 days, the model is classified into:
- **Green Zone ($x \le 4$)**: Model accepted. Regulatory capital multiplier $k = 3.00$.
- **Yellow Zone ($5 \le x \le 9$)**: Supervisory attention. Capital multiplier increases monotonically from $k = 3.40$ ($x=5$) to $k = 3.85$ ($x=9$).
- **Red Zone ($x \ge 10$)**: Model presumption of invalidity. Capital multiplier $k = 4.00$, and model approval is suspended.

---

## Maximum Diversification Portfolio (MDP) & Min-CVaR Optimization

### 1. Maximum Diversification Portfolio (Choueifaty & Coignard 2008)
Rather than optimizing for variance alone, the MDP maximizes the **Diversification Ratio (DR)**:

$$\text{DR}(w) = \frac{w^T \sigma}{\sqrt{w^T \Sigma w}}$$

where $w^T \sigma = \sum_{i=1}^N w_i \sigma_i$ is the weighted average volatility of individual assets, and $\sqrt{w^T \Sigma w}$ is total portfolio volatility.
- $\text{DR}(w) \ge 1$ always, due to sub-additivity.
- $\text{DR}(w) = 1$ if and only if all assets are perfectly correlated ($\rho_{ij} = 1$).
- Maximizing $\text{DR}(w)$ extracts the maximal risk reduction achievable purely through correlation diversity, without requiring expected return estimates $\mu$.

### 2. Min-CVaR Exact Linear Programming (Rockafellar & Uryasev 2000)
To avoid non-convexity in tail-risk optimization, Rockafellar and Uryasev demonstrated that minimizing Conditional Value at Risk can be formulated as a strictly convex linear program.

Given $T$ historical or Monte Carlo return scenarios $r_{t, i}$, the optimization solves:

$$\min_{w, \gamma, z} \quad \gamma + \frac{1}{(1 - \alpha) T} \sum_{t=1}^T z_t$$

subject to:
$$z_t \ge - \sum_{i=1}^N w_i r_{t, i} - \gamma, \quad \forall t = 1, \dots, T$$
$$z_t \ge 0, \quad \forall t = 1, \dots, T$$
$$\sum_{i=1}^N w_i = 1, \quad w_i \ge 0, \quad \forall i = 1, \dots, N$$

where $\gamma$ is the VaR auxiliary variable and $z_t$ captures tail exceedances. ARGUS solves this LP in < 5ms via SciPy's HiGHS solver (`scipy.optimize.linprog(method='highs')`).

---

## FX Risk Decomposition & Forward Hedging Carry Simulator

For international assets denominated in foreign currency (e.g. USD, GBP, CHF) against base currency (EUR), total asset return in EUR is:

$$R_{\text{total}} = (1 + R_{\text{local}}) (1 + R_{\text{fx}}) - 1 = R_{\text{local}} + R_{\text{fx}} + R_{\text{local}} \cdot R_{\text{fx}}$$

Total variance decomposes into three distinct structural components:

$$\sigma_{\text{total}}^2 \approx \sigma_{\text{local}}^2 + \sigma_{\text{fx}}^2 + 2 \cdot \text{Cov}(R_{\text{local}}, R_{\text{fx}})$$

1. **Local Asset Variance ($\sigma_{\text{local}}^2$)**: Pure business risk of the underlying security.
2. **Currency Variance ($\sigma_{\text{fx}}^2$)**: Pure foreign exchange volatility.
3. **Interaction / Covariance ($2 \cdot \text{Cov}(R_{\text{local}}, R_{\text{fx}})$)**: Natural hedging effect if negative, risk amplification if positive.

The Forward Hedging Simulator estimates the annual **Carry Drag** under Covered Interest Rate Parity:

$$\text{Carry Cost (bps)} \approx (r_{\text{base}} - r_{\text{foreign}}) \times 10,000$$

providing quantitative guidance on whether 100% FX hedging is cost-effective.

---

## Consolidated Total Wealth Stress Testing (EBA & Fed CCAR)

To avoid viewing liquid portfolios in isolation, ARGUS applies joint institutional macroeconomic shocks across the consolidated personal balance sheet:
- **EBA Regulatory Adverse 2026**: GDP contraction, equity crash -28%, real estate -15%, pension funds -16%, luxury caveau -20%.
- **Fed CCAR Severely Adverse**: Severe global distress, equity -42%, real estate -25%, private equity -45%.
- **Stagflation & Rates Hike**: Central bank rate shock (+200 bps), equity -18%, real estate -10%.
- **Geopolitical Risk-Off**: Flight to liquidity, equity -32%, gold/caveau -12%.

Because liabilities (mortgages, personal debt) are fixed in nominal terms while asset values contract:

$$\text{Debt-to-Assets}_{\text{stressed}} = \frac{\text{Liabilities}}{\sum \text{Assets}_{\text{stressed}}} > \text{Debt-to-Assets}_{\text{initial}}$$

This quantifies the financial leverage amplification during severe downturns.

---

## Multi-Asset Hybrid Calendar Harmonization (Compounding Weekend Returns)

In multi-asset portfolios spanning traditional securities (equities, fixed income, ETFs) and digital assets (cryptocurrencies), return time series possess fundamentally incompatible trading calendars:
- Traditional securities trade on business days ($\sim 252$ trading days/year, excluding exchange holidays).
- Cryptocurrencies trade continuously 24/7/365.

### Failure of Naïve Approaches
1. **Truncation / Dropping Weekends**: Discarding Saturday and Sunday returns destroys the continuous compounding identity, underestimating cumulative performance and omitting significant volatility clusters that occur during weekend market hours.
2. **Zero-Return / Forward-Fill on Equities**: Expanding equity calendars to 365 days by padding weekend returns with zero ($R=0$) artificially depresses annualized volatility ($\sigma_{\text{ann}} = \sigma_{\text{daily}} \sqrt{365}$ with dampened variance) and distorts cross-asset correlation estimates.

### Exact Continuous Compounding Synchronization
ARGUS maps all assets onto the canonical institutional business day calendar $\mathcal{T}_{\text{business}} = \{t_1, t_2, \dots, t_T\}$ by tracking cumulative geometric wealth:

$$W_t = \prod_{\tau=1}^t (1 + R_\tau)$$

Reindexing cumulative wealth onto business days with forward-fill:

$$W_{t_k}^{\text{business}} = W_{\max\{\tau \le t_k\}}$$

The synchronized daily return series is given by:

$$R_{t_k}^{\text{aligned}} = \frac{W_{t_k}^{\text{business}}}{W_{t_{k-1}}^{\text{business}}} - 1$$

For Monday ($t_{\text{Mon}}$) following a standard weekend:

$$R_{\text{Mon}}^{\text{aligned}} = (1 + R_{\text{Sat}})(1 + R_{\text{Sun}})(1 + R_{\text{Mon}}) - 1 = \prod_{d \in \{\text{Sat}, \text{Sun}, \text{Mon}\}} (1 + R_d) - 1$$

This ensures:
- **Total Compounded Return Preservation**: $\prod_{t=1}^T (1 + R_t^{\text{aligned}}) \equiv \prod_{\tau=1}^{T_{365}} (1 + R_\tau)$.
- **Accurate Tail Risk Capture**: Weekend market shocks are fully transmitted to Monday openings, eliminating artificial zero-variance artifacts.
- **Unbiased Covariance Estimation**: Cross-asset correlations between TradFi equities and crypto accurately reflect systemic spillover effects.

---

## Exact Euler Risk Decomposition & Deterministic Weight Normalization

Because Parametric Value at Risk ($\text{VaR}_p$) and portfolio volatility ($\sigma_p$) are linearly homogeneous functions of degree 1 with respect to the portfolio weight vector $\mathbf{w}$:

$$\text{VaR}_p(\lambda \mathbf{w}) = \lambda \text{VaR}_p(\mathbf{w}), \quad \forall \lambda > 0$$

By **Euler's Homogeneous Function Theorem**, total portfolio risk decomposes exactly into the sum of component risk contributions without residual:

$$\text{VaR}_p = \sum_{i=1}^N w_i \cdot \frac{\partial \text{VaR}_p}{\partial w_i} = \sum_{i=1}^N \text{Component VaR}_i$$

### 1. Deterministic Weight Normalization
To prevent numerical residuals or truncation of fractional micro-positions ($w_i < 0.01$, i.e. < 1%) caused by pre-rounded percentage weights, ARGUS computes the continuous weight vector directly from live position valuations $V_i$:

$$w_i = \frac{V_i}{\sum_{k=1}^N V_k}, \quad \text{with } \sum_{i=1}^N w_i \equiv 1.00000000$$

### 2. Marginal and Component VaR Formulation
The Marginal VaR ($\text{MVaR}_i$) measures the sensitivity of total portfolio VaR to an incremental allocation in asset $i$:

$$\text{MVaR}_i = \frac{\partial \text{VaR}_p}{\partial w_i} = z_\alpha \cdot \sqrt{T} \cdot \frac{(\boldsymbol{\Sigma} \mathbf{w})_i}{\sigma_p}$$

where $(\boldsymbol{\Sigma} \mathbf{w})_i = \text{Cov}(R_i, R_p)$ is the covariance between asset $i$ and the total portfolio.

The Component VaR in percentage and base currency (EUR) terms is:

$$\text{CVaR}_i = w_i \cdot \text{MVaR}_i = w_i \left( z_\alpha \sqrt{T} \frac{(\boldsymbol{\Sigma} \mathbf{w})_i}{\sigma_p} \right)$$

$$\text{Component VaR Amount}_i = \text{CVaR}_i \times V_{\text{port}}$$

$$\text{Percentage Contribution}_i = \frac{\text{CVaR}_i}{\text{VaR}_p} \times 100$$

### 3. Exact Mathematical Closure
Summing across all $N$ positions:

$$\sum_{i=1}^N \text{CVaR}_i = \frac{z_\alpha \sqrt{T}}{\sigma_p} \sum_{i=1}^N w_i (\boldsymbol{\Sigma} \mathbf{w})_i = \frac{z_\alpha \sqrt{T}}{\sigma_p} (\mathbf{w}^T \boldsymbol{\Sigma} \mathbf{w}) = \frac{z_\alpha \sqrt{T}}{\sigma_p} \sigma_p^2 = z_\alpha \sigma_p \sqrt{T} \equiv \text{VaR}_p$$

$$\sum_{i=1}^N \text{Component VaR Amount}_i = \text{Total VaR Amount}_p$$

The engine verifies this identity on every calculation cycle:

$$\epsilon_{\text{Euler}} = \left| \sum_{i=1}^N \text{Component VaR Amount}_i - \text{Total VaR Amount}_p \right| < 10^{-2}\text{ EUR}$$

---

## Dynamic Wealth ⇄ Risk Bridge: Liquidity-at-Risk & Anti-Forced Selling Buffer

Personal wealth management requires that liquid cash reserves (*Emergency Runway*) adapt dynamically to the market risk profile of liquid investments.

### The Forced Selling Dilemma
When an investor encounters unexpected liquidity needs during severe market downturns, an inadequate cash buffer forces the distress liquidation of volatile assets (equities or crypto) at market lows (*Forced Selling at Market Trough*), locking in permanent capital losses and forfeiting subsequent market recovery.

### Quantitative Formulation
ARGUS links balance sheet liquidity to market risk via the **Liquidity-at-Risk** protocol. The target emergency runway is dynamically scaled by the portfolio's annualized Expected Shortfall ($\text{CVaR}_{0.95}$ / 95%) and the equity weighting relative to total net worth:

$$\mathcal{M}_{\text{risk-buffer}} = 1.0 + \left( \lambda \cdot \text{CVaR}_{0.95}^{\text{annual}} \cdot w_{\text{equity}}^{\text{NW}} \right)$$

where:
- $\lambda = 1.5$ is the institutional anti-forced selling multiplier.
- $\text{CVaR}_{0.95}^{\text{annual}} \approx \text{CVaR}_{0.95, 1d} \times \sqrt{252}$ is the annualized Expected Shortfall of the liquid portfolio.
- $w_{\text{equity}}^{\text{NW}} = \frac{V_{\text{equity}}}{\text{Total Net Worth}}$ is the balance-sheet equity concentration ratio.

The risk-adjusted liquidity targets are:

$$\text{Runway Target}_{\text{risk-adjusted}} = \text{Runway Target}_{\text{base}} \times \mathcal{M}_{\text{risk-buffer}}$$

$$\text{Target Emergency Reserve (EUR)} = \text{Runway Target}_{\text{risk-adjusted}} \times \text{Monthly Burn Rate}$$

$$\text{Liquidity Gap (EUR)} = \max\left(0, \; \text{Target Emergency Reserve} - \text{Liquid Cash}\right)$$

A positive Liquidity Gap triggers an automatic advisory constraint prohibiting further risky asset accumulation until the cash runway is replenished.

---

## Spectral Covariance Regularization & Ledoit-Wolf Shrinkage

Sample covariance matrices $\mathbf{S} = \frac{1}{T-1} \mathbf{X}^T \mathbf{X}$ are often ill-conditioned or singular when asset count $N$ approaches sample size $T$, or under high multicollinearity.

### 1. Ledoit-Wolf Optimal Linear Shrinkage (2004)
To minimize estimation risk without subjective priors, ARGUS employs the **Ledoit-Wolf shrinkage estimator**:

$$\boldsymbol{\Sigma}_{\text{LW}} = (1 - \delta^*) \mathbf{S} + \delta^* \mathbf{F}$$

where:
- $\mathbf{S}$ is the unbiased sample covariance matrix.
- $\mathbf{F}$ is the structured target matrix (constant correlation model).
- $\delta^* \in [0, 1]$ is the analytically optimal shrinkage intensity minimizing the expected Frobenius norm error $\mathbb{E}[\|\boldsymbol{\Sigma}_{\text{LW}} - \boldsymbol{\Sigma}_{\text{true}}\|_F^2]$.

### 2. Positive Semi-Definite (PSD) Spectral Guarantee
To guarantee invertibility and prevent numerical breakdown in Cholesky factorization ($\boldsymbol{\Sigma} = \mathbf{L} \mathbf{L}^T$) and Monte Carlo sampling, ARGUS enforces spectral eigenvalue clipping:

1. **Symmetrization**: $\boldsymbol{\Sigma}_{\text{sym}} = \frac{1}{2}(\boldsymbol{\Sigma} + \boldsymbol{\Sigma}^T)$.
2. **Eigenvalue Decomposition**: $\boldsymbol{\Sigma}_{\text{sym}} = \mathbf{V} \boldsymbol{\Lambda} \mathbf{V}^T$, where $\boldsymbol{\Lambda} = \text{diag}(\lambda_1, \dots, \lambda_N)$.
3. **Eigenvalue Floor**: $\tilde{\lambda}_i = \max(\lambda_i, 10^{-8})$.
4. **Reconstructed Covariance**: $\boldsymbol{\Sigma}_{\text{PSD}} = \mathbf{V} \cdot \text{diag}(\tilde{\lambda}_1, \dots, \tilde{\lambda}_N) \cdot \mathbf{V}^T$.

This guarantees strictly positive portfolio variances $\mathbf{w}^T \boldsymbol{\Sigma}_{\text{PSD}} \mathbf{w} > 0$ for all non-trivial allocations $\mathbf{w} \ne \mathbf{0}$, ensuring mathematical stability across all downstream quantitative engines.


