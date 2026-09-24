# Non-Gaussian Tail Risk & Cornish-Fisher Expansion

Standard portfolio theory (Markowitz 1952) and classical risk metrics assume that asset returns are identically and independently distributed according to a normal Gaussian distribution:

$$r \sim \mathcal{N}(\mu, \sigma^2)$$

However, empirical financial time series systematically violate Gaussianity. Asset return distributions display:
1. **Negative Asymmetry (Skewness $\mathcal{S} < 0$)**: Asymmetric risk where market drawdowns are sharper and faster than market rallies.
2. **Heavy Tails (Excess Kurtosis $\mathcal{K} > 0$)**: Leptokurtic fat tails where extreme market shocks occur with a probability orders of magnitude greater than predicted by the 3-sigma rule.

---

## The Cornish-Fisher Quantile Expansion

To overcome the catastrophic underestimation of tail risk by Gaussian models, ARGUS computes the **Cornish-Fisher expansion** (Cornish & Fisher 1937). Given a target confidence level $\alpha$ (e.g. $\alpha = 0.05$ for $95\%$ VaR), let $z_\alpha = \Phi^{-1}(\alpha)$ be the standard normal critical quantile ($z_{0.05} \approx -1.64485$).

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

When estimating risk in deep tail regions (e.g. $99.0\%$ and $99.9\%$ confidence levels), empirical quantiles become noisy due to sparse observations, while parametric Gaussian or Student-$t$ models impose arbitrary global symmetry.

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

