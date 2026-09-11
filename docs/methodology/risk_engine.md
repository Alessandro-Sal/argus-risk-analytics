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
