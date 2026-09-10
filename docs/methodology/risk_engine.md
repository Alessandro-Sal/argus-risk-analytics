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
