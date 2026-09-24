"""
ARGUS — Headless Quantitative Risk Engine & REST API Microservice.
Provides institutional REST endpoints for:
1. Advanced Market Risk & Return Metrics (Cornish-Fisher VaR/CVaR, Sharpe, Sortino)
2. Hierarchical Risk Parity (HRP) Portfolio Optimization
3. Bitemporal Time-Travel Ledger & Merkle Audit Seal
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

try:
    from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = object  # Fallback for type hinting

from core.advanced_quant import compute_risk_budgeting_portfolio
from core.barra_risk_model import compute_barra_structural_risk
from core.basel_liquidity_engine import compute_basel_liquidity_ratios
from core.bitemporal_engine import BitemporalLedgerEngine
from core.black_litterman_engine import compute_black_litterman_allocation
from core.climate_stress_engine import compute_ngfs_climate_stress
from core.dcc_garch_engine import compute_dcc_garch_extreme_risk
from core.factor_library import compute_fama_french_factor_model
from core.fix_engine import execute_mock_fix_order
from core.fixed_income import compute_bond_analytics
from core.frtb_engine import compute_frtb_capital_charges
from core.heston_fft_engine import compute_heston_surface_and_calibration
from core.macro_stress_engine import compute_reverse_stress_test
from core.macro_war_room import compute_macro_war_room_stress
from core.mip_rebalancer import solve_mip_rebalance
from core.pdf_generator import (
    generate_institutional_portfolio_factsheet_pdf,
    generate_regulatory_stress_testing_dossier_pdf,
)
from core.regime_allocation import compute_regime_conditional_allocation
from core.regulatory_reporting_engine import compute_regulatory_dossier
from core.risk_engine import compute_portfolio_liquidity_risk
from core.sabr_local_vol_engine import compute_sabr_and_local_vol_surface
from core.services.rebalancing_service import RebalancingService
from core.services.risk_service import RiskService
from core.services.tax_service import TaxService
from core.services.wealth_service import WealthService
from core.smart_order_router import compute_smart_order_routing
from core.solvency2_engine import compute_solvency2_standard_formula
from core.structured_products_engine import compute_structured_product_pricing
from core.tax_engine import compute_tax_and_harvesting
from core.walk_forward_engine import run_walk_forward_backtest
from core.watchdog.risk_watchdog import RiskWatchdogService, evaluate_risk_appetite_framework
from core.wealth.private_markets_engine import compute_private_markets_analytics
from core.wealth.succession_optimizer import compute_family_succession_optimization
from core.wealth.total_wealth_reverse_stress import compute_total_wealth_reverse_stress
from core.xva_engine import compute_xva_metrics

logger = logging.getLogger("argus.api")

# ============================================================
# Pydantic Request & Response Schemas (v2 Compatible)
# ============================================================


class JobSubmitRequest(BaseModel):
    """Payload for submitting an asynchronous background task."""
    task_type: str = Field(..., description="Task type: walk_forward, regime_adaptive, mip_rebalance, reverse_stress")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task-specific payload")


class WalkForwardRequest(BaseModel):
    """Payload for Walk-Forward Rolling Backtesting."""
    returns: Dict[str, List[float]] = Field(..., description="Historical returns dictionary {ticker: [ret1, ret2, ...]}")
    strategy: str = Field(default="equal_weight", description="Strategy: equal_weight, hrp, erc, max_sharpe")
    train_window_days: int = Field(default=252, ge=20)
    test_window_days: int = Field(default=63, ge=5)
    rebalance_cost_bps: float = Field(default=10.0, ge=0.0)
    slippage_bps: float = Field(default=5.0, ge=0.0)
    bid_ask_bps: float = Field(default=5.0, ge=0.0)


class RegimeAdaptiveRequest(BaseModel):
    """Payload for Regime-Conditional Adaptive Allocation."""
    returns: Dict[str, List[float]] = Field(..., description="Historical returns dictionary {ticker: [ret1, ret2, ...]}")
    base_weights: Optional[Dict[str, float]] = None
    current_regime: Optional[str] = None
    crisis_equity_haircut: float = Field(default=0.40, ge=0.0, le=1.0)
    risk_free_rate: float = Field(default=0.02)


class TotalWealthReverseStressRequest(BaseModel):
    """Payload for Total Wealth Reverse Stress Testing."""
    balance_sheet: Dict[str, float] = Field(..., description="Balance sheet: liquid_assets, real_estate, corporate_equity, illiquid_assets, total_liabilities")
    target_type: str = Field(default="solvency", description="'solvency' or 'ruin'")
    target_threshold: float = Field(default=0.60, description="Critical threshold (e.g. 0.60 for D/A ratio or 0.50 for ruin)")


class BarraRiskRequest(BaseModel):
    """Payload for Barra Structural Multi-Asset Risk Model."""
    returns: Dict[str, List[float]] = Field(..., description="Historical returns dictionary {ticker: [ret1, ret2, ...]}")
    weights: Optional[Dict[str, float]] = None
    factor_returns: Optional[Dict[str, List[float]]] = None
    benchmark_weights: Optional[Dict[str, float]] = None


class Solvency2ScrRequest(BaseModel):
    """Payload for Solvency II Standard Formula SCR calculation."""
    positions: List[Dict[str, Any]] = Field(..., description="Portfolio assets list with value, duration, CQS, asset_type")
    eligible_own_funds: float = Field(..., description="Eligible Own Funds (Tier 1 + Tier 2 capital) in EUR")
    technical_provisions: float = Field(default=0.0, description="Gross technical provisions in EUR")
    symmetric_equity_adjustment: float = Field(default=0.0, ge=-0.10, le=0.10)


class DccGarchRequest(BaseModel):
    """Payload for DCC-GARCH and Vine Copula Tail Risk Engine."""
    returns: Dict[str, List[float]] = Field(..., description="Historical returns dictionary {ticker: [ret1, ret2, ...]}")
    weights: Optional[Dict[str, float]] = None
    n_mc_sims: int = Field(default=2000, ge=100)


class FixOrderRequest(BaseModel):
    """Payload for Mock FIX 4.4 Order Execution & L2 DOM Simulator."""
    symbol: str = Field(default="SWDA.MI")
    side: str = Field(default="BUY")
    qty: int = Field(default=1000, gt=0)
    order_type: str = Field(default="MARKET")
    limit_price: Optional[float] = None
    mid_price: float = Field(default=100.0, gt=0.0)


class SuccessionOptimizationRequest(BaseModel):
    """Payload for Generational Wealth Succession Optimizer."""
    liquid_investments_eur: float = Field(default=5_000_000.0)
    operating_business_equity_eur: float = Field(default=10_000_000.0)
    real_estate_properties_eur: float = Field(default=4_000_000.0)
    alternative_investments_eur: float = Field(default=1_000_000.0)
    num_children: int = Field(default=2, ge=1)
    has_spouse: bool = Field(default=True)
    annual_consumption_eur: float = Field(default=120_000.0)


class WatchdogCheckRequest(BaseModel):
    """Payload for Event-Driven Risk Watchdog limit evaluation."""
    metrics: Dict[str, Any] = Field(..., description="Active portfolio metrics dictionary")
    custom_limits: Optional[Dict[str, float]] = None
    channels: Optional[List[str]] = Field(default=["telegram", "discord", "slack"])
    mock_dispatch: bool = Field(default=True)


class MipRebalanceRequest(BaseModel):
    """Payload for Mixed-Integer Programming Discrete Lot & Cardinality Rebalancer."""
    current_holdings: Dict[str, float] = Field(..., description="Current shares {ticker: quantity}")
    current_prices: Dict[str, float] = Field(..., description="Current prices {ticker: price_eur}")
    target_weights: Dict[str, float] = Field(..., description="Target weights {ticker: weight}")
    total_capital: Optional[float] = None
    cash_available: float = Field(default=0.0)
    max_cardinality: Optional[int] = None
    lot_sizes: Optional[Dict[str, int]] = None
    min_trade_eur: float = Field(default=50.0)
    capital_gains_tax_budget_eur: Optional[float] = None
    pmc_dict: Optional[Dict[str, float]] = None
    tax_rate: float = Field(default=0.26)


class FrtbSbmRequest(BaseModel):
    """Payload for BCBS 365 / FRTB Standardized Approach Capital Charges."""
    sensitivities: Optional[List[Dict[str, Any]]] = None
    default_positions: Optional[List[Dict[str, Any]]] = None
    exotic_notionals: Optional[Dict[str, float]] = None
    total_portfolio_value: float = Field(default=100_000_000.0, gt=0.0)


class SabrVolRequest(BaseModel):
    """Payload for Hagan SABR Calibration and Dupire Local Vol Surface Inversion."""
    f0: float = Field(default=100.0, gt=0.0)
    strikes: Optional[List[float]] = None
    maturities: Optional[List[float]] = None
    market_vols: Optional[List[List[float]]] = None
    beta: float = Field(default=0.70, ge=0.0, le=1.0)


class ClimateNgfsRequest(BaseModel):
    """Payload for NGFS Phase IV Climate Transition & Physical Stress."""
    portfolio_holdings: Optional[List[Dict[str, Any]]] = None
    scenario_name: str = Field(default="Net Zero 2050 (Orderly)")
    target_year: int = Field(default=2030, ge=2024, le=2050)


class SmartRouteRequest(BaseModel):
    """Payload for Multi-Venue Smart Order Router & MiFID II Best Execution."""
    symbol: str = Field(default="ASML.AS")
    side: str = Field(default="BUY")
    quantity: int = Field(default=5000, gt=0)
    limit_price: Optional[float] = None
    urgency: str = Field(default="MEDIUM")


class PrivateMarketsRequest(BaseModel):
    """Payload for Private Markets 10-Yr Cash Flow Pacing & De-smoothing."""
    commitment_eur: float = Field(default=5_000_000.0, gt=0.0)
    fund_life_years: int = Field(default=10, ge=5, le=20)
    growth_rate: float = Field(default=0.10)
    observed_returns: Optional[List[float]] = None


class MacroWarRoomRequest(BaseModel):
    """Payload for Interactive Macro War Room & Correlation Breakdown."""
    assets: Optional[List[Dict[str, Any]]] = None
    scenario_params: Optional[Dict[str, Any]] = None



class XvaRequest(BaseModel):
    """Payload for Bilateral XVA & Exposure Profile simulation."""
    trades: Optional[List[Dict[str, Any]]] = None
    csa_params: Optional[Dict[str, Any]] = None
    market_params: Optional[Dict[str, Any]] = None


class HestonPricingRequest(BaseModel):
    """Payload for Heston FFT calibration and volatility surface."""
    s0: float = Field(default=100.0, gt=0.0)
    r: float = Field(default=0.03)
    q: float = Field(default=0.0)
    market_quotes: Optional[List[Dict[str, Any]]] = None
    custom_params: Optional[Dict[str, float]] = None


class BlackLittermanRequest(BaseModel):
    """Payload for Bayesian Black-Litterman Portfolio Optimization."""
    assets: Optional[List[str]] = None
    cov_matrix: Optional[List[List[float]]] = None
    market_weights: Optional[Dict[str, float]] = None
    views: Optional[List[Dict[str, Any]]] = None
    risk_aversion: float = Field(default=3.0, gt=0.0)
    tau: float = Field(default=0.05, gt=0.0)
    risk_free_rate: float = Field(default=0.02)
    long_only: bool = Field(default=True)
    max_weight: float = Field(default=0.40, gt=0.0, le=1.0)


class BaselLiquidityRequest(BaseModel):
    """Payload for Basel III LCR and NSFR Liquidity Ratios."""
    hqla: Optional[List[Dict[str, Any]]] = None
    outflows: Optional[List[Dict[str, Any]]] = None
    inflows: Optional[List[Dict[str, Any]]] = None
    asf: Optional[List[Dict[str, Any]]] = None
    rsf: Optional[List[Dict[str, Any]]] = None


class StructuredProductRequest(BaseModel):
    """Payload for Exotic Derivatives & Structured Products Valuation."""
    product_type: str = Field(default="phoenix_autocallable")
    nominal: float = Field(default=1000.0, gt=0.0)
    maturity_years: float = Field(default=2.0, gt=0.0)
    observation_frequency_months: int = Field(default=6, ge=1, le=12)
    coupon_rate_p_a: float = Field(default=0.08)
    has_memory_coupon: bool = Field(default=True)
    coupon_barrier_pct: float = Field(default=0.70, gt=0.0, le=1.0)
    autocall_barrier_pct: float = Field(default=1.00, gt=0.0)
    protection_barrier_pct: float = Field(default=0.60, gt=0.0, le=1.0)
    underlyings: Optional[List[str]] = None
    spots: Optional[List[float]] = None
    volatilities: Optional[List[float]] = None
    risk_free_rate: float = Field(default=0.03)
    n_simulations: int = Field(default=10000, ge=1000, le=100000)


class RegulatoryReportingRequest(BaseModel):
    """Payload for PRIIPs KID Summary Risk Indicator & SFDR Annex I disclosures."""
    historical_returns: Optional[List[float]] = None
    issuer_credit_rating: str = Field(default="A")
    rhp_years: float = Field(default=5.0, gt=0.0)
    investment_amount_eur: float = Field(default=10000.0, gt=0.0)
    sfdr_article: str = Field(default="Article 8")
    taxonomy_alignment_pct: float = Field(default=24.5, ge=0.0, le=100.0)
    sustainable_investment_pct: float = Field(default=35.0, ge=0.0, le=100.0)
    custom_pai: Optional[Dict[str, float]] = None


# In-memory background jobs registry
_jobs_registry: Dict[str, Dict[str, Any]] = {}


def execute_background_job(job_id: str, task_type: str, payload: Dict[str, Any]):
    """Background worker executing quantitative tasks asynchronously."""
    try:
        _jobs_registry[job_id]["status"] = "RUNNING"
        _jobs_registry[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()

        if task_type == "walk_forward":
            rets_dict = payload.get("returns", {})
            df_rets = pd.DataFrame(rets_dict)
            strat = payload.get("strategy", "equal_weight")
            train_w = int(payload.get("train_window_days", 252))
            test_w = int(payload.get("test_window_days", 63))
            reb_cost = float(payload.get("rebalance_cost_bps", 10.0))
            slip = float(payload.get("slippage_bps", 5.0))
            ba = float(payload.get("bid_ask_bps", 5.0))
            res = run_walk_forward_backtest(
                returns_df=df_rets,
                strategy_name=strat,
                train_window_days=train_w,
                test_window_days=test_w,
                rebalance_cost_bps=reb_cost,
                slippage_bps=slip,
                bid_ask_bps=ba,
            )
            output = {
                "summary": res["summary_table"].to_dict(orient="records"),
                "params": res["params"],
                "rebalance_dates": res["rebalance_dates"],
            }
        elif task_type == "regime_adaptive":
            rets_dict = payload.get("returns", {})
            df_rets = pd.DataFrame(rets_dict)
            output = compute_regime_conditional_allocation(
                returns_df=df_rets,
                base_weights=payload.get("base_weights"),
                current_regime=payload.get("current_regime"),
                crisis_equity_haircut=float(payload.get("crisis_equity_haircut", 0.40)),
            )
        elif task_type == "mip_rebalance":
            output = solve_mip_rebalance(
                current_holdings=payload.get("current_holdings", {}),
                current_prices=payload.get("current_prices", {}),
                target_weights=payload.get("target_weights", {}),
                total_capital=payload.get("total_capital"),
                cash_available=float(payload.get("cash_available", 0.0)),
                max_cardinality=payload.get("max_cardinality"),
                lot_sizes=payload.get("lot_sizes"),
                min_trade_eur=float(payload.get("min_trade_eur", 50.0)),
                capital_gains_tax_budget_eur=payload.get("capital_gains_tax_budget_eur"),
                pmc_dict=payload.get("pmc_dict"),
            )
        elif task_type == "reverse_stress":
            output = compute_total_wealth_reverse_stress(
                balance_sheet=payload.get("balance_sheet", {}),
                target_type=payload.get("target_type", "solvency"),
                target_threshold=float(payload.get("target_threshold", 0.60)),
            )
        else:
            output = {"message": f"Task {task_type} completed", "payload": payload}

        _jobs_registry[job_id]["status"] = "COMPLETED"
        _jobs_registry[job_id]["result"] = output
        _jobs_registry[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
        _jobs_registry[job_id]["status"] = "FAILED"
        _jobs_registry[job_id]["error"] = str(exc)
        _jobs_registry[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()

class RiskMetricsRequest(BaseModel):
    """Payload for computing portfolio risk and performance metrics."""
    returns: List[float] = Field(
        ...,
        description="Chronological series of daily returns (e.g. [0.012, -0.005, ...])",
        min_length=2
    )
    risk_free_rate: float = Field(
        default=0.0275,
        description="Annual risk-free benchmark rate (e.g. 0.0275 for 2.75% BCE €STR)"
    )
    benchmark_returns: Optional[List[float]] = Field(
        default=None,
        description="Optional benchmark return series aligned with portfolio returns"
    )
    confidence_levels: List[float] = Field(
        default=[0.95, 0.99],
        description="List of statistical confidence intervals (e.g. [0.95, 0.99])"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "returns": [0.005, -0.012, 0.008, 0.003, -0.021, 0.015, -0.002, 0.009],
                "risk_free_rate": 0.0275,
                "confidence_levels": [0.95, 0.99]
            }
        }
    }


class RiskMetricsResponse(BaseModel):
    """Institutional risk and return metrics response."""
    var_historical: Dict[str, float] = Field(..., description="Historical Value at Risk by confidence level")
    cvar_historical: Dict[str, float] = Field(..., description="Historical Conditional VaR (Expected Shortfall)")
    var_parametric: Dict[str, float] = Field(..., description="Gaussian Parametric VaR")
    cvar_parametric: Dict[str, float] = Field(..., description="Gaussian Parametric CVaR")
    var_cornish_fisher: Dict[str, float] = Field(..., description="Modified Cornish-Fisher VaR with skew/kurtosis adjustment")
    cvar_cornish_fisher: Dict[str, float] = Field(..., description="Modified Cornish-Fisher CVaR (Boudt-Peterson-Croux 2008)")
    sharpe_ratio: float = Field(..., description="Annualized Sharpe ratio")
    sortino_ratio: float = Field(..., description="Annualized Sortino ratio (downside deviation)")
    max_drawdown: float = Field(..., description="Maximum peak-to-trough drawdown")
    volatility_annual: float = Field(..., description="Annualized volatility (fraction)")
    volatility_annual_pct: float = Field(..., description="Annualized volatility in percent")
    cagr: Optional[float] = Field(None, description="Compound Annual Growth Rate")
    skewness: float = Field(..., description="Empirical return skewness")
    kurtosis: float = Field(..., description="Excess kurtosis (Fisher)")


class HRPOptimizeRequest(BaseModel):
    """Payload for Hierarchical Risk Parity portfolio allocation."""
    asset_returns: Dict[str, List[float]] = Field(
        ...,
        description="Dictionary mapping ticker symbols to equal-length chronological return lists"
    )
    linkage_method: str = Field(
        default="single",
        description="Hierarchical clustering linkage: 'single', 'complete', 'average', 'ward'"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "asset_returns": {
                    "AAPL": [0.01, -0.02, 0.015, 0.004, -0.008, 0.012],
                    "MSFT": [0.008, -0.015, 0.011, 0.002, -0.005, 0.009],
                    "GOOGL": [0.012, -0.025, 0.018, 0.006, -0.011, 0.014],
                    "BND": [0.001, 0.002, -0.001, 0.000, 0.001, -0.001]
                },
                "linkage_method": "single"
            }
        }
    }


class HRPOptimizeResponse(BaseModel):
    """Optimal portfolio weights derived from Hierarchical Risk Parity."""
    weights: Dict[str, float] = Field(..., description="Normalized optimal weights summing to 1.0")
    expected_return_pct: float = Field(..., description="Annualized expected return in percentage")
    volatility_annual_pct: float = Field(..., description="Annualized portfolio volatility in percentage")
    sharpe_ratio: float = Field(..., description="Expected Sharpe ratio")
    sorted_assets: List[str] = Field(..., description="Quasi-diagonalized asset ordering from dendrogram")


class TimeTravelRequest(BaseModel):
    """Payload for querying bitemporal portfolio state as of specific valid and system times."""
    portfolio_id: str = Field(default="DEMO_FAMILY_OFFICE", description="Unique portfolio identifier")
    as_of_valid_time: str = Field(
        ...,
        description="Business/Valid time cut-off (ISO 8601 string, e.g. '2026-03-31T23:59:59')"
    )
    as_of_system_time: Optional[str] = Field(
        default=None,
        description="Knowledge/System time cut-off (defaults to infinity / present state)"
    )
    seed_demo: bool = Field(
        default=True,
        description="If True and ledger is empty, populate demo family office scenario"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "portfolio_id": "DEMO_FAMILY_OFFICE",
                "as_of_valid_time": "2026-03-31T23:59:59",
                "as_of_system_time": "2026-04-05T12:00:00",
                "seed_demo": True
            }
        }
    }


class PositionSnapshot(BaseModel):
    """Reconstructed point-in-time holding."""
    ticker: str
    asset_class: str
    total_shares: float
    avg_cost: float
    current_price: float
    current_nav: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class TimeTravelResponse(BaseModel):
    """Bitemporal state reconstruction with cryptographic integrity seal."""
    portfolio_id: str
    as_of_valid_time: str
    as_of_system_time: str
    positions: List[PositionSnapshot]
    total_portfolio_nav: float
    merkle_root: str


class HealthResponse(BaseModel):
    """Service health and capability metadata."""
    status: str
    version: str
    engine: str
    duckdb_available: bool
    timestamp: str


class RebalanceHoldingItem(BaseModel):
    """Individual holding item for portfolio rebalancing."""
    ticker: str = Field(..., description="Asset ticker symbol, e.g. SWDA.MI or AAPL")
    shares: float = Field(..., description="Current quantity of shares/units held", ge=0.0)
    current_price: float = Field(..., description="Current market price per share", gt=0.0)
    pmc: float = Field(default=0.0, description="Prezzo Medio di Carico (tax acquisition cost)", ge=0.0)
    asset_class: str = Field(default="Equity", description="Asset class: Equity, ETF, Bond_Gov, Bond_Corp, Crypto, etc.")


class RebalanceRequest(BaseModel):
    """Payload for institutional multi-strategy portfolio rebalancing."""
    holdings: List[RebalanceHoldingItem] = Field(..., min_length=1, description="List of current portfolio holdings")
    target_weights: Dict[str, float] = Field(..., description="Target allocation weights (e.g. {'SWDA.MI': 0.6, 'XEON.MI': 0.4})")
    strategy: str = Field(default="autonomous", description="Rebalancing strategy: 'autonomous', 'tax_aware', 'prescriptive', 'heuristic'")
    total_portfolio_value: Optional[float] = Field(default=None, description="Optional target total portfolio value in EUR")
    minusvalenze_available: float = Field(default=0.0, description="Available past capital losses in tax wallet (TUIR Art. 67)", ge=0.0)
    max_turnover_pct: float = Field(default=50.0, description="Maximum permissible turnover percentage", ge=0.0, le=100.0)
    min_trade_eur: float = Field(default=50.0, description="Minimum order size threshold in EUR", ge=0.0)
    cash_injection: float = 0.0

    model_config = {
        "json_schema_extra": {
            "example": {
                "holdings": [
                    {"ticker": "SWDA.MI", "shares": 100, "current_price": 100.0, "pmc": 80.0, "asset_class": "ETF"},
                    {"ticker": "ISP.MI", "shares": 1000, "current_price": 4.0, "pmc": 3.0, "asset_class": "Equity"}
                ],
                "target_weights": {"SWDA.MI": 0.50, "ISP.MI": 0.50},
                "strategy": "autonomous",
                "minusvalenze_available": 500.0,
                "max_turnover_pct": 30.0,
                "min_trade_eur": 100.0,
                "cash_injection": 0.0
            }
        }
    }


class PlannedOrderItem(BaseModel):
    """Calculated execution order item."""
    ticker: str
    action: str
    shares: float
    price: float
    order_value: float
    tax_category: str
    realized_gain: float
    estimated_tax: float
    estimated_fees: float
    current_weight_pct: float
    target_weight_pct: float
    delta_weight_pct: float
    fix_message: Optional[str] = None
    notes: str = ""


class RebalanceResponse(BaseModel):
    """Institutional rebalancing response with orders, metrics, and compliance audit."""
    strategy: str
    orders: List[PlannedOrderItem]
    summary: Dict[str, Any]
    tax_report: Dict[str, Any]
    compliance: Dict[str, Any]
    status: str


class RiskParityRequest(BaseModel):
    """Payload for Spinu (2013) Convex Potential Risk Budgeting & Equal Risk Contribution."""
    asset_returns: Dict[str, List[float]] = Field(
        ...,
        description="Dictionary mapping ticker symbols to equal-length chronological return lists",
        min_length=2,
    )
    risk_budgets: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional dictionary mapping tickers to target fractional risk budgets. If omitted, Equal Risk Contribution is used."
    )
    risk_free_rate: float = Field(
        default=0.0275,
        description="Annual risk-free benchmark rate (e.g. 0.0275 for 2.75% BCE €STR)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "asset_returns": {
                    "SPY": [0.01, -0.015, 0.008, 0.002, -0.005],
                    "TLT": [-0.002, 0.005, -0.001, 0.003, 0.001],
                    "GLD": [0.003, -0.002, 0.004, -0.001, 0.002],
                },
                "risk_budgets": {"SPY": 0.5, "TLT": 0.3, "GLD": 0.2},
                "risk_free_rate": 0.0275,
            }
        }
    }


class RiskParityResponse(BaseModel):
    """Optimal portfolio weights and risk contributions from Risk Parity."""
    weights: Dict[str, float] = Field(..., description="Normalized optimal weights summing to 1.0")
    risk_contributions_pct: Dict[str, float] = Field(..., description="Percentage Risk Contribution (PRC) per asset")
    risk_budgets_pct: Dict[str, float] = Field(..., description="Target risk budget percentage per asset")
    expected_return_pct: float = Field(..., description="Annualized expected return in percent")
    volatility_annual_pct: float = Field(..., description="Annualized portfolio volatility in percent")
    sharpe_ratio: float = Field(..., description="Expected Sharpe ratio")
    diversification_ratio: float = Field(..., description="Choueifaty diversification ratio")
    algorithm: str = Field(default="Spinu (2013) Strictly Convex Potential", description="Optimization algorithm")
    status: str = Field(default="optimal", description="Solver status ('optimal' or 'heuristic_fallback')")


class ReverseStressRequest(BaseModel):
    """Payload for Regulatory Reverse Stress Testing (EBA / BCE Framework)."""
    target_loss_pct: float = Field(
        default=15.0,
        description="Target portfolio loss threshold in percent (e.g. 15.0 for -15%)",
        gt=0.0
    )
    asset_weights: Dict[str, float] = Field(
        ...,
        description="Dictionary mapping ticker symbols or asset classes to weights (summing to ~1.0)",
        min_length=1,
    )
    portfolio_value: float = Field(
        default=1_000_000.0,
        description="Total portfolio value in EUR",
        gt=0.0
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_loss_pct": 15.0,
                "asset_weights": {"EQUITY": 0.60, "BONDS": 0.30, "COMMODITIES": 0.10},
                "portfolio_value": 1000000.0,
            }
        }
    }


class ReverseStressResponse(BaseModel):
    """Regulatory Reverse Stress Test result with minimum Mahalanobis distance shocks."""
    target_loss_pct: float = Field(..., description="Target portfolio loss threshold in percent")
    target_loss_eur: float = Field(..., description="Target portfolio loss in EUR")
    simulated_loss_pct: float = Field(..., description="Simulated joint stress loss in percent")
    simulated_loss_eur: float = Field(..., description="Simulated joint stress loss in EUR")
    mahalanobis_distance: float = Field(..., description="Mahalanobis statistical distance d_M of joint scenario")
    p_value_chi2: float = Field(..., description="Statistical plausibility p-value under Chi-squared distribution")
    plausibility_rating: str = Field(..., description="Qualitative plausibility category")
    severity_badge: str = Field(..., description="Severity level badge")
    implied_frequency_estimate: str = Field(..., description="Estimated recurrence frequency")
    shocks_by_factor: Dict[str, float] = Field(..., description="Optimal risk factor shock magnitudes (decimal or bps)")
    factor_betas: Dict[str, float] = Field(..., description="Portfolio beta exposures to macro factors")
    break_even_solutions: Dict[str, Any] = Field(..., description="Univariate break-even crash scenarios")


class FamaFrenchRequest(BaseModel):
    """Payload for Kenneth French Multi-Factor Regression & Performance Attribution."""
    returns: List[float] = Field(
        ...,
        description="Chronological series of daily portfolio returns",
        min_length=15
    )
    model_type: str = Field(
        default="5_factor_mom",
        description="Factor model: '3_factor', '4_factor', '5_factor', '5_factor_mom'"
    )


class FamaFrenchResponse(BaseModel):
    """Institutional Fama-French & Carhart factor exposures and attribution."""
    model_type: str
    alpha_annual: float
    alpha_t_stat: float
    r_squared: float
    r_squared_adj: float
    systematic_risk_pct: float
    factor_details: List[Dict[str, Any]]
    attribution: Dict[str, float]


class FixedIncomeAnalyticsRequest(BaseModel):
    """Payload for Institutional Fixed Income & Bond Analytics."""
    face_value: float = Field(default=100.0, description="Nominal/Face value", gt=0.0)
    coupon_rate: float = Field(default=0.04, description="Annual coupon rate in decimal (e.g. 0.04 for 4%)", ge=0.0)
    maturity_years: float = Field(default=10.0, description="Remaining maturity in years", gt=0.0)
    market_price: float = Field(default=100.0, description="Current clean/dirty market price", gt=0.0)
    coupon_frequency: int = Field(default=2, description="Coupons per year (1=annual, 2=semi-annual, 4=quarterly)")
    yield_shift_bps: float = Field(default=10.0, description="Yield shift in basis points for DV01/PVBP")


class FixedIncomeAnalyticsResponse(BaseModel):
    """Bloomberg YAS-style fixed income analytics."""
    ytm_pct: float
    current_yield_pct: float
    macaulay_duration_years: float
    modified_duration: float
    convexity: float
    dv01_eur: float
    pvbp_eur: float
    price_impact_100bps_pct: float
    price_impact_minus100bps_pct: float
    interest_rate_stress_matrix: Dict[str, float]


class LiquidityPositionItem(BaseModel):
    ticker: str
    current_value: float
    asset_class: str = "Equity"


class LiquidityRiskRequest(BaseModel):
    """Payload for Basel III / UCITS Liquidity Risk & Days-to-Liquidate Analysis."""
    positions: List[LiquidityPositionItem] = Field(..., min_length=1)
    participation_rate: float = Field(default=0.10, description="Max daily market participation rate (0.01 to 0.50)", ge=0.01, le=0.50)


class LiquidityRiskResponse(BaseModel):
    """Liquidity risk metrics, tiers, and liquidation horizon."""
    total_portfolio_value: float
    weighted_dtl_days: float
    max_dtl_days: float
    bottleneck_ticker: str
    liquidity_tiers_pct: Dict[str, float]
    liquidity_risk_premium_pct: float
    total_liquidation_cost_eur: float
    positions_liquidity_breakdown: List[Dict[str, Any]]


class TaxHarvestingPositionItem(BaseModel):
    ticker: str
    shares: float
    current_price: float
    pmc: float
    asset_class: str = "Equity"


class TaxHarvestingRequest(BaseModel):
    """Payload for Italian TUIR Tax-Loss Harvesting Optimization."""
    positions: List[TaxHarvestingPositionItem] = Field(..., min_length=1)
    tax_year: Optional[int] = Field(default=None, description="Fiscal year (defaults to current year)")


class TaxHarvestingResponse(BaseModel):
    """Identified tax-loss harvesting candidates and fiscal savings."""
    summary: Dict[str, Any]
    harvesting_opportunities: List[Dict[str, Any]]
    potential_tax_savings_eur: float


# ============================================================
# FastAPI Application Factory
# ============================================================

def create_app() -> FastAPI:
    """Creates and configures the FastAPI application instance."""
    if not HAS_FASTAPI:
        raise RuntimeError("FastAPI is not installed. Install with `pip install argus-risk[api]`")

    app = FastAPI(
        title="ARGUS Headless Quantitative Risk Engine",
        description=(
            "High-performance REST API for institutional quantitative finance: "
            "Cornish-Fisher VaR/CVaR, Hierarchical Risk Parity (HRP) & Spinu Risk Parity optimization, "
            "EBA Reverse Stress Testing, Fama-French multi-factor attribution, Fixed Income YAS, "
            "and ISO/IEC 9075:2011 bitemporal ledger time-travel reconstruction."
        ),
        version="9.14.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # In-memory bitemporal ledger instance and watchdog service
    ledger_instance = BitemporalLedgerEngine(db_path=":memory:")
    watchdog_instance = RiskWatchdogService(mock_dispatch=True)

    # ── Health Endpoint ──────────────────────────────────────────

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    def get_health() -> HealthResponse:
        """Returns microservice health status, engine version, and DuckDB availability."""
        from core.bitemporal_engine import HAS_DUCKDB
        return HealthResponse(
            status="healthy",
            version="9.14.0",
            engine="ARGUS Headless Core",
            duckdb_available=HAS_DUCKDB,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    # ── Risk Metrics Endpoint ────────────────────────────────────

    @app.post(
        "/api/v1/risk/metrics",
        response_model=RiskMetricsResponse,
        tags=["Quantitative Risk Engine"],
        summary="Compute Cornish-Fisher VaR/CVaR and Return Performance Metrics"
    )
    def compute_metrics(req: RiskMetricsRequest) -> RiskMetricsResponse:
        """
        Computes institutional-grade risk measures:
        - Historical, Parametric Gaussian, and Cornish-Fisher VaR and CVaR (Modified Expected Shortfall)
        - Annualized Volatility, Sharpe Ratio, Sortino Ratio, and Max Drawdown
        - Higher empirical moments: Skewness and Fisher Kurtosis
        """
        try:
            metrics_data = RiskService.compute_risk_metrics(
                returns=req.returns,
                benchmark_returns=req.benchmark_returns,
                risk_free_rate=req.risk_free_rate,
                confidence_levels=req.confidence_levels,
            )
            return RiskMetricsResponse(**metrics_data)
        except HTTPException:
            raise
        except ValueError as v_err:
            raise HTTPException(status_code=422, detail=str(v_err))
        except Exception as exc:
            logger.error("Error computing risk metrics: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Risk computation failure: {str(exc)}"
            )

    # ── HRP Optimization Endpoint ────────────────────────────────

    @app.post(
        "/api/v1/optimize/hrp",
        response_model=HRPOptimizeResponse,
        tags=["Portfolio Optimization"],
        summary="Hierarchical Risk Parity (HRP) Portfolio Allocation"
    )
    def optimize_hrp(req: HRPOptimizeRequest) -> HRPOptimizeResponse:
        """
        Executes Marcos López de Prado's Hierarchical Risk Parity algorithm:
        1. Tree Clustering (Single, Complete, or Average linkage on correlation distance)
        2. Quasi-Diagonalization (Dendrogram leaf ordering)
        3. Recursive Bisection (Inverse-variance tree weight allocation)
        """
        if not req.asset_returns or len(req.asset_returns) < 2:
            raise HTTPException(
                status_code=422,
                detail="At least two asset return series are required for portfolio optimization."
            )

        try:
            hrp_res = RiskService.optimize_hrp(
                asset_returns=req.asset_returns,
                linkage_method=req.linkage_method
            )
            return HRPOptimizeResponse(**hrp_res)
        except HTTPException:
            raise
        except ValueError as v_err:
            raise HTTPException(status_code=422, detail=str(v_err))
        except RuntimeError as r_err:
            raise HTTPException(status_code=400, detail=str(r_err))
        except Exception as exc:
            logger.error("HRP optimization failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"HRP optimization error: {str(exc)}"
            )

    # ── Wealth Intelligence Net Worth Endpoint ────────────────────

    @app.get(
        "/api/v1/wealth/networth",
        tags=["Wealth Intelligence"],
        summary="Get Consolidated Balance Sheet & Net Worth"
    )
    def get_net_worth(portfolio_id: Optional[int] = None) -> Dict[str, Any]:
        """Restituisce il Net Worth consolidato, solvibilità e ripartizione asset class."""
        try:
            return WealthService.get_consolidated_net_worth(db_engine=None, portfolio_id=portfolio_id)
        except Exception as exc:
            logger.error("Wealth net worth error: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Wealth calculation failure: {str(exc)}")

    # ── Portfolio Rebalancing Endpoint ───────────────────────────

    @app.post(
        "/api/v1/rebalance",
        response_model=RebalanceResponse,
        tags=["Rebalancing & Execution"],
        summary="Compute Institutional Portfolio Rebalancing Plan"
    )
    def compute_rebalancing_plan(req: RebalanceRequest) -> RebalanceResponse:
        """
        Calcola gli ordini di ribilanciamento istituzionale, impatto fiscale TUIR Art. 44 vs 67,
        matrice di attrito e gate MiFID II su strategie polimorfiche.
        """
        try:
            holdings_dicts = [h.model_dump() for h in req.holdings]
            res = RebalancingService.execute_rebalance(
                positions=holdings_dicts,
                target_weights=req.target_weights,
                strategy=req.strategy,
                total_portfolio_value=req.total_portfolio_value,
                minusvalenze_available=req.minusvalenze_available,
                max_turnover_pct=req.max_turnover_pct,
                min_trade_eur=req.min_trade_eur,
                cash_injection=req.cash_injection,
            )

            formatted_orders = [
                PlannedOrderItem(
                    ticker=o["ticker"],
                    action=o["action"],
                    shares=float(o["shares"]),
                    price=float(o["price"]),
                    order_value=float(o["order_value"]),
                    tax_category=str(o["tax_category"]),
                    realized_gain=float(o["realized_gain"]),
                    estimated_tax=float(o["estimated_tax"]),
                    estimated_fees=float(o.get("estimated_fees", 0.0)),
                    current_weight_pct=float(o["current_weight_pct"]),
                    target_weight_pct=float(o["target_weight_pct"]),
                    delta_weight_pct=float(o["delta_weight_pct"]),
                    fix_message=o.get("fix_message"),
                    notes=o.get("notes", ""),
                )
                for o in res.get("orders", [])
            ]

            return RebalanceResponse(
                strategy=res["strategy"],
                orders=formatted_orders,
                summary=res["summary"],
                tax_report=res["tax_report"],
                compliance=res["compliance"],
                status=res["status"],
            )
        except ValueError as v_err:
            raise HTTPException(status_code=422, detail=str(v_err))
        except Exception as exc:
            logger.error("Rebalancing execution failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Rebalancing calculation failure: {str(exc)}"
            )

    # ── Bitemporal Time-Travel Endpoint ──────────────────────────

    @app.post(
        "/api/v1/ledger/timetravel",
        response_model=TimeTravelResponse,
        tags=["Bitemporal Ledger & Audit Trail"],
        summary="Reconstruct Point-in-Time Portfolio with Merkle Seal"
    )
    def query_timetravel(req: TimeTravelRequest) -> TimeTravelResponse:
        """
        Performs orthogonal two-dimensional bitemporal point-in-time reconstruction:
        - Valid Time (What was the real portfolio holding as of date T?)
        - System Time (What did the system record/know as of date T_sys?)
        Returns verified positions, total NAV, and SHA-256 Merkle root seal.
        """
        try:
            if req.seed_demo:
                # Seed demo data if not already present
                existing = ledger_instance.time_travel_query(
                    portfolio_id=req.portfolio_id,
                    as_at_valid_time="9999-12-31 23:59:59"
                )
                if existing.empty:
                    ledger_instance.seed_demonstration_scenario(portfolio_id=req.portfolio_id)

            as_of_sys = req.as_of_system_time or BitemporalLedgerEngine.INFINITY_TIMESTAMP

            recon = ledger_instance.reconstruct_portfolio_at_times(
                portfolio_id=req.portfolio_id,
                as_at_valid_time=req.as_of_valid_time,
                as_of_system_time=as_of_sys
            )

            positions_raw = recon.get("positions", [])
            merkle_root = BitemporalLedgerEngine.generate_merkle_root(positions_raw) if positions_raw else BitemporalLedgerEngine.GENESIS_HASH

            formatted_positions = [
                PositionSnapshot(
                    ticker=p.get("asset_id", p.get("ticker", "UNKNOWN")),
                    asset_class=p.get("asset_class", "Multi-Asset"),
                    total_shares=round(float(p.get("shares", p.get("total_shares", 0.0))), 4),
                    avg_cost=round(float(p.get("wacp_eur", p.get("avg_cost", 0.0))), 4),
                    current_price=round(float(p.get("current_price", p.get("wacp_eur", 0.0))), 4),
                    current_nav=round(float(p.get("cost_value_eur", p.get("current_nav", 0.0))), 2),
                    unrealized_pnl=round(float(p.get("unrealized_pnl", 0.0)), 2),
                    unrealized_pnl_pct=round(float(p.get("unrealized_pnl_pct", 0.0)), 2),
                )
                for p in positions_raw
            ]

            total_nav = float(recon.get("total_book_value_eur", recon.get("total_portfolio_nav", 0.0)))

            return TimeTravelResponse(
                portfolio_id=req.portfolio_id,
                as_of_valid_time=req.as_of_valid_time,
                as_of_system_time=as_of_sys,
                positions=formatted_positions,
                total_portfolio_nav=round(total_nav, 2),
                merkle_root=merkle_root
            )
        except Exception as exc:
            logger.error("Bitemporal reconstruction error: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Bitemporal time-travel failure: {str(exc)}"
            )

    # ── Risk Parity / Spinu Convex Risk Budgeting Endpoint ───────

    @app.post(
        "/api/v1/optimize/erc",
        response_model=RiskParityResponse,
        tags=["Portfolio Optimization"],
        summary="Spinu (2013) Convex Potential Risk Budgeting & Equal Risk Contribution"
    )
    def optimize_risk_parity(req: RiskParityRequest) -> RiskParityResponse:
        """
        Executes Florian Spinu's (2013) strictly convex potential formulation for Risk Budgeting & ERC:
        - Exact marginal risk contributions (MRC) and percentage risk contributions (PRC)
        - Arbitrary percentage risk budgets or uniform Equal Risk Contribution (1/N)
        - Guaranteed unique global optimum via L-BFGS-B / SLSQP
        """
        if not req.asset_returns or len(req.asset_returns) < 2:
            raise HTTPException(
                status_code=422,
                detail="At least two asset return series are required for risk parity optimization."
            )
        try:
            df_returns = pd.DataFrame(req.asset_returns)
            res = compute_risk_budgeting_portfolio(
                returns_df=df_returns,
                risk_budgets=req.risk_budgets,
                risk_free_rate=req.risk_free_rate,
            )
            return RiskParityResponse(
                weights=res["weights"],
                risk_contributions_pct=res["risk_contributions_pct"],
                risk_budgets_pct=res["risk_budgets_pct"],
                expected_return_pct=round(res["expected_return"] * 100.0, 2),
                volatility_annual_pct=round(res["volatility"] * 100.0, 2),
                sharpe_ratio=res["sharpe_ratio"],
                diversification_ratio=res["diversification_ratio"],
                algorithm="Spinu (2013) Strictly Convex Potential",
                status="optimal" if res.get("success", True) else "heuristic_fallback",
            )
        except ValueError as v_err:
            raise HTTPException(status_code=422, detail=str(v_err))
        except Exception as exc:
            logger.error("Risk parity optimization error: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Risk parity optimization error: {str(exc)}")

    # ── Reverse Stress Testing Endpoint ──────────────────────────

    @app.post(
        "/api/v1/risk/reverse-stress",
        response_model=ReverseStressResponse,
        tags=["Quantitative Risk Engine"],
        summary="Regulatory Reverse Stress Testing (EBA / BCE Guidelines)"
    )
    def run_reverse_stress(req: ReverseStressRequest) -> ReverseStressResponse:
        """
        Calculates the most plausible joint macroeconomic shock that causes a predetermined portfolio loss:
        - Minimum Mahalanobis statistical distance optimization (SLSQP with Karush-Kuhn-Tucker bounds)
        - 6 core regulatory macro factors: Equity, 10Y Yield, IG Spread, HY Spread, FX EUR/USD, Commodities
        - Chi-squared plausibility p-value and loss attribution decomposition
        """
        try:
            df_pos = pd.DataFrame([
                {"ticker": t, "current_value": req.portfolio_value * w, "asset_class": t}
                for t, w in req.asset_weights.items()
            ])
            res = compute_reverse_stress_test(
                target_loss_pct=req.target_loss_pct,
                df_positions=df_pos,
                portfolio_value=req.portfolio_value,
            )
            return ReverseStressResponse(
                target_loss_pct=res["target_loss_pct"],
                target_loss_eur=res["target_loss_eur"],
                simulated_loss_pct=res["simulated_loss_pct"],
                simulated_loss_eur=res["simulated_loss_eur"],
                mahalanobis_distance=res["mahalanobis_distance"],
                p_value_chi2=res["p_value_chi2"],
                plausibility_rating=res["plausibility_rating"],
                severity_badge=res["severity_badge"],
                implied_frequency_estimate=res["implied_frequency_estimate"],
                shocks_by_factor=res["shocks_by_factor"],
                factor_betas=res["factor_betas"],
                break_even_solutions=res["break_even_solutions"],
            )
        except Exception as exc:
            logger.error("Reverse stress test failure: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Reverse stress test error: {str(exc)}")

    # ── Fama-French Factor Attribution Endpoint ──────────────────

    @app.post(
        "/api/v1/risk/fama-french",
        response_model=FamaFrenchResponse,
        tags=["Quantitative Risk Engine"],
        summary="Kenneth French Multi-Factor Regression & Risk Attribution"
    )
    def compute_fama_french(req: FamaFrenchRequest) -> FamaFrenchResponse:
        """
        Executes multivariate OLS regression on Fama-French & Carhart factor benchmarks:
        - Models: 3-Factor (Mkt-RF, SMB, HML), 4-Factor (+MOM), 5-Factor (+RMW, +CMA), 5-Factor+Mom
        - Annualized Jensen's alpha, t-statistics, p-values, R², and systematic risk share
        """
        try:
            sr_returns = pd.Series(req.returns)
            res = compute_fama_french_factor_model(sr_returns, model_type=req.model_type)
            return FamaFrenchResponse(
                model_type=res.get("model_type", req.model_type),
                alpha_annual=round(float(res.get("alpha_annual", 0.0)), 4),
                alpha_t_stat=round(float(res.get("alpha_t_stat", 0.0)), 2),
                r_squared=round(float(res.get("r_squared", 0.0)), 4),
                r_squared_adj=round(float(res.get("r_squared_adj", 0.0)), 4),
                systematic_risk_pct=round(float(res.get("systematic_risk_pct", 0.0)), 2),
                factor_details=res.get("factor_details", []),
                attribution=res.get("attribution", {}),
            )
        except Exception as exc:
            logger.error("Fama-French attribution failure: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Fama-French computation error: {str(exc)}")

    # ── Fixed Income & Bond Analytics Endpoint ───────────────────

    @app.post(
        "/api/v1/fixed-income/analytics",
        response_model=FixedIncomeAnalyticsResponse,
        tags=["Fixed Income & ALM"],
        summary="Institutional Fixed Income Analytics (Bloomberg YAS Parity)"
    )
    def compute_fixed_income_analytics(req: FixedIncomeAnalyticsRequest) -> FixedIncomeAnalyticsResponse:
        """
        Computes institutional bond pricing and sensitivity measures:
        - Yield to Maturity (YTM) via Newton-Raphson & Brent solver
        - Macaulay Duration, Modified Duration, Convexity, DV01/PVBP
        - Taylor expansion interest rate shock matrix (-200bps to +200bps)
        """
        try:
            res = compute_bond_analytics(
                face_value=req.face_value,
                coupon_rate=req.coupon_rate,
                maturity_years=req.maturity_years,
                market_price=req.market_price,
                coupon_frequency=req.coupon_frequency,
                yield_shift_bps=req.yield_shift_bps,
            )
            sens_df = res.get("sensitivity_table", pd.DataFrame())
            stress_map = {}
            if isinstance(sens_df, pd.DataFrame) and not sens_df.empty:
                for _, row in sens_df.iterrows():
                    stress_map[f"{int(row['shift_bps']):+d}bps"] = float(row["pct_change_exact"])

            p_100 = stress_map.get("+100bps", round(-float(res.get("modified_duration", 0.0)), 2))
            p_m100 = stress_map.get("-100bps", round(float(res.get("modified_duration", 0.0)), 2))

            return FixedIncomeAnalyticsResponse(
                ytm_pct=float(res.get("ytm_pct", 0.0)),
                current_yield_pct=float(res.get("current_yield_pct", 0.0)),
                macaulay_duration_years=float(res.get("macaulay_duration_years", 0.0)),
                modified_duration=float(res.get("modified_duration", 0.0)),
                convexity=float(res.get("convexity", 0.0)),
                dv01_eur=float(res.get("dv01", 0.0)),
                pvbp_eur=float(res.get("pvbp", 0.0)),
                price_impact_100bps_pct=float(p_100),
                price_impact_minus100bps_pct=float(p_m100),
                interest_rate_stress_matrix=stress_map,
            )
        except Exception as exc:
            logger.error("Fixed income analytics failure: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Fixed income analytics error: {str(exc)}")

    # ── Liquidity Risk Endpoint ──────────────────────────────────

    @app.post(
        "/api/v1/risk/liquidity",
        response_model=LiquidityRiskResponse,
        tags=["Quantitative Risk Engine"],
        summary="Basel III / UCITS Liquidity Risk & Days to Liquidate (DTL)"
    )
    def compute_liquidity(req: LiquidityRiskRequest) -> LiquidityRiskResponse:
        """
        Evaluates portfolio liquidation horizon under institutional market participation constraints:
        - Days to Liquidate (DTL) per asset and portfolio weighted DTL
        - Amihud illiquidity ratio and Almgren-Chriss market impact cost
        - Basel III 4-tier liquidity classification (Tier 1 <1d to Tier 4 >7d)
        """
        try:
            df_pos = pd.DataFrame([p.model_dump() for p in req.positions])
            res = compute_portfolio_liquidity_risk(
                df_positions=df_pos,
                participation_rate=req.participation_rate,
            )
            return LiquidityRiskResponse(
                total_portfolio_value=res["total_portfolio_value"],
                weighted_dtl_days=res["weighted_dtl_days"],
                max_dtl_days=res["max_dtl_days"],
                bottleneck_ticker=res["bottleneck_ticker"],
                liquidity_tiers_pct=res["liquidity_tiers_pct"],
                liquidity_risk_premium_pct=res["liquidity_risk_premium_pct"],
                total_liquidation_cost_eur=res["total_liquidation_cost_eur"],
                positions_liquidity_breakdown=res["positions_liquidity_breakdown"],
            )
        except Exception as exc:
            logger.error("Liquidity risk computation failure: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Liquidity risk error: {str(exc)}")

    # ── Tax-Loss Harvesting Optimization Endpoint ────────────────

    @app.post(
        "/api/v1/tax/harvesting",
        response_model=TaxHarvestingResponse,
        tags=["Tax Optimization"],
        summary="Italian TUIR Tax-Loss Harvesting & Minusvalenze Optimization"
    )
    def compute_tax_harvesting(req: TaxHarvestingRequest) -> TaxHarvestingResponse:
        """
        Audits portfolio for fiscal loss-harvesting opportunities under Italian TUIR:
        - Identifies unrealized losses in compensable assets (Redditi Diversi)
        - Computes potential tax credits and four-year Zainetto Fiscale timeline
        """
        try:
            positions_data = [p.model_dump() for p in req.positions]
            for p in positions_data:
                p["current_value"] = p["shares"] * p["current_price"]
                p["cost_basis"] = p["shares"] * p["pmc"]
                p["unrealized_pnl"] = p["current_value"] - p["cost_basis"]
            df_pos = pd.DataFrame(positions_data)
            res = compute_tax_and_harvesting(
                {"positions": df_pos, "df_tx": pd.DataFrame()},
                tax_year=req.tax_year,
            )
            raw_opps = res.get("harvesting_opportunities", [])
            if isinstance(raw_opps, pd.DataFrame):
                opps = raw_opps.to_dict(orient="records")
            else:
                opps = list(raw_opps)

            summary = res.get("summary", {})
            return TaxHarvestingResponse(
                summary=summary,
                harvesting_opportunities=opps,
                potential_tax_savings_eur=float(summary.get("potential_tax_savings_eur", 0.0)),
            )
        except Exception as exc:
            logger.error("Tax harvesting failure: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Tax harvesting error: {str(exc)}")

    # ── Institutional Portfolio Factsheet PDF Stream Endpoint ────

    @app.get(
        "/api/v1/reports/factsheet",
        tags=["Reporting & Factsheets"],
        summary="Generate Institutional 2-Page Factsheet PDF"
    )
    def download_institutional_factsheet(
        portfolio_name: str = Query("ARGUS Institutional Portfolio", description="Portfolio title"),
        total_value: float = Query(1_000_000.0, description="Total portfolio value in EUR", gt=0.0),
        currency: str = Query("EUR", description="Base reporting currency"),
    ):
        """
        Streams a certified 2-page Institutional Portfolio Factsheet PDF (BlackRock / Morningstar Standard):
        - Page 1: Executive Tear Sheet, Key Metrics, Allocation Donut, Cornish-Fisher VaR/CVaR Matrix, Top 7 Holdings
        - Page 2: Fama-French Factor Attribution, Regulatory Stress Tests, Fixed Income & Liquidity Profile, AI Commentary, MiFID II Disclaimer
        """
        try:
            sample_risk_data = {
                "positions": pd.DataFrame([
                    {"ticker": "SWDA.MI", "current_value": total_value * 0.60, "unrealized_pnl": total_value * 0.08, "asset_class": "Equity ETF"},
                    {"ticker": "XEON.MI", "current_value": total_value * 0.25, "unrealized_pnl": total_value * 0.01, "asset_class": "Govt Bond"},
                    {"ticker": "GLD", "current_value": total_value * 0.15, "unrealized_pnl": total_value * 0.03, "asset_class": "Commodities"},
                ]),
                "metrics": {
                    "market_risk": {
                        "var_cf_95_pct": 1.45,
                        "cvar_cf_95_pct": 2.20,
                        "var_cf_99_pct": 2.65,
                        "cvar_cf_99_pct": 3.85,
                        "volatility_annual_pct": 11.2,
                        "max_drawdown_pct": 8.4,
                        "skewness": -0.25,
                        "kurtosis": 1.85,
                    },
                    "returns": {
                        "cagr_pct": 9.4,
                        "sharpe_ratio": 1.25,
                        "sortino_ratio": 1.68,
                    },
                    "concentration": {
                        "herfindahl_index": 0.42,
                        "effective_n_assets": 2.4,
                    },
                },
            }
            pdf_bytes = generate_institutional_portfolio_factsheet_pdf(
                portfolio_name=portfolio_name,
                risk_data=sample_risk_data,
                base_currency=currency,
            )
            safe_filename = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in portfolio_name)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="Factsheet_{safe_filename}.pdf"',
                    "Content-Type": "application/pdf",
                },
            )
        except Exception as exc:
            logger.error("Factsheet PDF generation failure: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=f"PDF generation error: {str(exc)}")


    # --- Asynchronous Job Queue Endpoints ---
    @app.post("/api/v1/jobs/submit", tags=["Async Job Queue"])
    def submit_job(req: JobSubmitRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        import uuid
        job_id = uuid.uuid4().hex
        _jobs_registry[job_id] = {
            "job_id": job_id,
            "task_type": req.task_type,
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
        }
        background_tasks.add_task(execute_background_job, job_id, req.task_type, req.payload)
        return {"job_id": job_id, "status": "PENDING", "task_type": req.task_type}

    @app.get("/api/v1/jobs/{job_id}", tags=["Async Job Queue"])
    def get_job(job_id: str) -> Dict[str, Any]:
        if job_id not in _jobs_registry:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return _jobs_registry[job_id]

    @app.get("/api/v1/jobs", tags=["Async Job Queue"])
    def list_jobs(limit: int = 50) -> List[Dict[str, Any]]:
        return list(_jobs_registry.values())[-limit:]

    # --- WebSocket Streaming Gateway ---
    @app.websocket("/api/v1/stream/ticks")
    async def websocket_ticks(websocket: WebSocket):
        await websocket.accept()
        import asyncio
        tickers = ["SPY", "QQQ", "TLT", "GLD", "BND"]
        prices = {"SPY": 580.0, "QQQ": 490.0, "TLT": 95.0, "GLD": 240.0, "BND": 72.0}
        try:
            for _ in range(10):
                for t in tickers:
                    shock = float(np.random.normal(0, 0.0005))
                    prices[t] = round(prices[t] * (1.0 + shock), 2)
                    bid = round(prices[t] - 0.02, 2)
                    ask = round(prices[t] + 0.02, 2)
                    await websocket.send_json({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "ticker": t,
                        "price": prices[t],
                        "bid": bid,
                        "ask": ask,
                        "spread_bps": 4.0,
                    })
                await asyncio.sleep(0.1)
            await websocket.send_json({"event": "STREAM_FINISHED"})
            await websocket.close()
        except WebSocketDisconnect:
            logger.info("Client disconnected from tick stream")
        except Exception as exc:
            logger.warning("WebSocket stream exception: %s", exc)

    # --- Synchronous Quantitative REST Endpoints ---
    @app.post("/api/v1/backtest/walk-forward", tags=["Quantitative Optimization"])
    def backtest_walk_forward(req: WalkForwardRequest) -> Dict[str, Any]:
        try:
            df_rets = pd.DataFrame(req.returns)
            res = run_walk_forward_backtest(
                returns_df=df_rets,
                strategy_name=req.strategy,
                train_window_days=req.train_window_days,
                test_window_days=req.test_window_days,
                rebalance_cost_bps=req.rebalance_cost_bps,
                slippage_bps=req.slippage_bps,
                bid_ask_bps=req.bid_ask_bps,
            )
            return {
                "status": "SUCCESS",
                "summary": res["summary_table"].to_dict(orient="records"),
                "params": res["params"],
                "rebalance_dates": res["rebalance_dates"],
            }
        except Exception as exc:
            logger.error("Walk-forward failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/optimize/regime-adaptive", tags=["Quantitative Optimization"])
    def optimize_regime_adaptive(req: RegimeAdaptiveRequest) -> Dict[str, Any]:
        try:
            df_rets = pd.DataFrame(req.returns)
            return compute_regime_conditional_allocation(
                returns_df=df_rets,
                base_weights=req.base_weights,
                current_regime=req.current_regime,
                crisis_equity_haircut=req.crisis_equity_haircut,
                risk_free_rate=req.risk_free_rate,
            )
        except Exception as exc:
            logger.error("Regime adaptive allocation failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/risk/total-wealth-reverse-stress", tags=["Risk Analytics"])
    def run_wealth_reverse_stress(req: TotalWealthReverseStressRequest) -> Dict[str, Any]:
        try:
            return compute_total_wealth_reverse_stress(
                balance_sheet=req.balance_sheet,
                target_type=req.target_type,
                target_threshold=req.target_threshold,
            )
        except Exception as exc:
            logger.error("Total wealth reverse stress failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/rebalance/mip", tags=["Portfolio Rebalancing"])
    def rebalance_mip(req: MipRebalanceRequest) -> Dict[str, Any]:
        try:
            return solve_mip_rebalance(
                current_holdings=req.current_holdings,
                current_prices=req.current_prices,
                target_weights=req.target_weights,
                total_capital=req.total_capital,
                cash_available=req.cash_available,
                max_cardinality=req.max_cardinality,
                lot_sizes=req.lot_sizes,
                min_trade_eur=req.min_trade_eur,
                capital_gains_tax_budget_eur=req.capital_gains_tax_budget_eur,
                pmc_dict=req.pmc_dict,
                tax_rate=req.tax_rate,
            )
        except Exception as exc:
            logger.error("MIP rebalance failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/v1/reports/stress-dossier", tags=["Reporting & Factsheets"])
    def download_stress_dossier_pdf(
        portfolio_name: str = Query("Global All-Weather", description="Portfolio denomination"),
        currency: str = Query("EUR", description="Base reporting currency")
    ):
        try:
            pdf_bytes = generate_regulatory_stress_testing_dossier_pdf(
                portfolio_name=portfolio_name,
                stress_data={"portfolio_nav": 1_000_000.0, "worst_loss_pct": -28.45},
                base_currency=currency,
            )
            safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in portfolio_name)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="Stress_Dossier_{safe_name}.pdf"',
                    "Content-Type": "application/pdf",
                },
            )
        except Exception as exc:
            logger.error("Stress dossier PDF failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    # ── V9.12.0 Institutional Endpoints ─────────────────────────

    @app.post("/api/v1/risk/barra", tags=["Quantitative Risk Engine"])
    def run_barra_structural_risk(req: BarraRiskRequest) -> Dict[str, Any]:
        """Barra-style structural multi-asset factor risk decomposition."""
        try:
            df_returns = pd.DataFrame(req.returns)
            df_factors = pd.DataFrame(req.factor_returns) if req.factor_returns else None
            return compute_barra_structural_risk(
                asset_returns=df_returns,
                weights=req.weights,
                factor_returns=df_factors,
                benchmark_weights=req.benchmark_weights,
            )
        except Exception as exc:
            logger.error("Barra risk model failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/risk/solvency2-scr", tags=["Risk Analytics"])
    def run_solvency2_scr(req: Solvency2ScrRequest) -> Dict[str, Any]:
        """EIOPA Solvency II Standard Formula Solvency Capital Requirement (SCR)."""
        try:
            return compute_solvency2_standard_formula(
                portfolio_assets=req.positions,
                eligible_own_funds=req.eligible_own_funds,
                technical_provisions=req.technical_provisions,
                symmetric_equity_adjustment=req.symmetric_equity_adjustment,
            )
        except Exception as exc:
            logger.error("Solvency II SCR failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/risk/dcc-garch", tags=["Quantitative Risk Engine"])
    def run_dcc_garch_tail_risk(req: DccGarchRequest) -> Dict[str, Any]:
        """DCC-GARCH Dynamic Conditional Correlation and Vine Copula Tail Risk."""
        try:
            df_returns = pd.DataFrame(req.returns)
            return compute_dcc_garch_extreme_risk(
                returns_df=df_returns,
                weights=req.weights,
                n_mc_sims=req.n_mc_sims,
            )
        except Exception as exc:
            logger.error("DCC-GARCH tail risk failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/execution/fix/order", tags=["Execution & Algos"])
    def run_fix_order_execution(req: FixOrderRequest) -> Dict[str, Any]:
        """Mock FIX 4.4 simulated order execution against 10-level DOM and TCA."""
        try:
            return execute_mock_fix_order(
                symbol=req.symbol,
                side=req.side,
                qty=req.qty,
                order_type=req.order_type,
                limit_price=req.limit_price,
                mid_price=req.mid_price,
            )
        except Exception as exc:
            logger.error("FIX execution failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/wealth/succession-optimization", tags=["Wealth Management"])
    def run_succession_optimization(req: SuccessionOptimizationRequest) -> Dict[str, Any]:
        """Family Office 30-year multi-generational succession Monte Carlo optimizer."""
        try:
            return compute_family_succession_optimization(
                liquid_investments_eur=req.liquid_investments_eur,
                operating_business_equity_eur=req.operating_business_equity_eur,
                real_estate_properties_eur=req.real_estate_properties_eur,
                alternative_investments_eur=req.alternative_investments_eur,
                num_children=req.num_children,
                has_spouse=req.has_spouse,
                annual_consumption_eur=req.annual_consumption_eur,
            )
        except Exception as exc:
            logger.error("Succession optimization failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/watchdog/check", tags=["System"])
    def run_watchdog_check(req: WatchdogCheckRequest) -> Dict[str, Any]:
        """Evaluates active risk limits against RAF thresholds and dispatches alerts."""
        try:
            return watchdog_instance.evaluate_and_notify(
                metrics=req.metrics,
                channels=req.channels,
                custom_limits=req.custom_limits,
            )
        except Exception as exc:
            logger.error("Watchdog evaluation failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/v1/watchdog/alerts", tags=["System"])
    def get_watchdog_alerts(limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent watchdog alert events."""
        return watchdog_instance.get_recent_alerts(limit=limit)

    # ── V9.13.0 Institutional Endpoints ─────────────────────────

    @app.post("/api/v1/risk/frtb-sbm", tags=["Risk Analytics"])
    def run_frtb_capital_charges(req: FrtbSbmRequest) -> Dict[str, Any]:
        """BCBS 365 / FRTB Standardized Approach SBM, DRC, and RRAO capital requirements."""
        try:
            return compute_frtb_capital_charges(
                sensitivities_data=req.sensitivities,
                default_positions_data=req.default_positions,
                exotic_notionals=req.exotic_notionals,
                total_portfolio_value=req.total_portfolio_value,
            )
        except Exception as exc:
            logger.error("FRTB capital charges failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/pricing/sabr-vol", tags=["Quantitative Risk Engine"])
    def run_sabr_local_vol(req: SabrVolRequest) -> Dict[str, Any]:
        """Hagan SABR calibration and Dupire local volatility PDE surface inversion."""
        try:
            return compute_sabr_and_local_vol_surface(
                f0=req.f0,
                strikes=req.strikes,
                maturities=req.maturities,
                market_vols=req.market_vols,
                beta=req.beta,
            )
        except Exception as exc:
            logger.error("SABR/Local vol calculation failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/stress/climate-ngfs", tags=["Stress Testing & Regulatory"])
    def run_climate_ngfs_stress(req: ClimateNgfsRequest) -> Dict[str, Any]:
        """NGFS Phase IV transition & physical climate risk stress testing."""
        try:
            return compute_ngfs_climate_stress(
                portfolio_holdings=req.portfolio_holdings,
                scenario_name=req.scenario_name,
                target_year=req.target_year,
            )
        except Exception as exc:
            logger.error("NGFS climate stress failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/execution/smart-route", tags=["Execution & Algos"])
    def run_smart_order_routing(req: SmartRouteRequest) -> Dict[str, Any]:
        """Multi-venue SOR, liquidity slicing and MiFID II RTS 28 Best Execution."""
        try:
            return compute_smart_order_routing(
                symbol=req.symbol,
                side=req.side,
                quantity=req.quantity,
                limit_price=req.limit_price,
                urgency=req.urgency,
            )
        except Exception as exc:
            logger.error("Smart order routing failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/wealth/private-markets", tags=["Wealth Management"])
    def run_private_markets_pacing(req: PrivateMarketsRequest) -> Dict[str, Any]:
        """Takahashi-Alexander 10-yr cash flow pacing and Geltner de-smoothing."""
        try:
            return compute_private_markets_analytics(
                commitment_eur=req.commitment_eur,
                fund_life_years=req.fund_life_years,
                growth_rate=req.growth_rate,
                observed_returns=req.observed_returns,
            )
        except Exception as exc:
            logger.error("Private markets analytics failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/stress/macro-war-room", tags=["Stress Testing & Regulatory"])
    def run_macro_war_room_stress(req: MacroWarRoomRequest) -> Dict[str, Any]:
        """Interactive Macro War Room multi-lever shock and systemic correlation breakdown."""
        try:
            return compute_macro_war_room_stress(
                assets_data=req.assets,
                scenario_params=req.scenario_params,
            )
        except Exception as exc:
            logger.error("Macro war room stress failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))


    # ── V9.14.0 Institutional Tier-1 Endpoints ─────────────────────────

    @app.post("/api/v1/risk/xva", tags=["Risk Analytics"])
    def run_xva_metrics(req: XvaRequest) -> Dict[str, Any]:
        """Bilateral CVA, DVA, FVA, MVA, KVA and exposure profile under CSA netting sets."""
        try:
            return compute_xva_metrics(
                trades_data=req.trades,
                csa_params=req.csa_params,
                market_params=req.market_params,
            )
        except Exception as exc:
            logger.error("XVA metrics calculation failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/pricing/heston", tags=["Derivatives & Volatility"])
    def run_heston_pricing(req: HestonPricingRequest) -> Dict[str, Any]:
        """Heston (1993) Carr-Madan FFT option pricing, Feller check, and surface calibration."""
        try:
            return compute_heston_surface_and_calibration(
                s0=req.s0,
                r=req.r,
                q=req.q,
                market_quotes=req.market_quotes,
                custom_params=req.custom_params,
            )
        except Exception as exc:
            logger.error("Heston pricing failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/optimize/black-litterman", tags=["Portfolio Optimization"])
    def run_black_litterman_optimization(req: BlackLittermanRequest) -> Dict[str, Any]:
        """Bayesian Black-Litterman optimization with Idzorek confidence weighting."""
        try:
            return compute_black_litterman_allocation(
                assets=req.assets,
                cov_matrix=req.cov_matrix,
                market_weights=req.market_weights,
                views_data=req.views,
                risk_aversion=req.risk_aversion,
                tau=req.tau,
                risk_free_rate=req.risk_free_rate,
                long_only=req.long_only,
                max_weight=req.max_weight,
            )
        except Exception as exc:
            logger.error("Black-Litterman optimization failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/risk/basel-liquidity", tags=["Stress Testing & Regulatory"])
    def run_basel_liquidity_ratios(req: BaselLiquidityRequest) -> Dict[str, Any]:
        """Basel III Liquidity Coverage Ratio (LCR), Net Stable Funding Ratio (NSFR), and cash ladder."""
        try:
            return compute_basel_liquidity_ratios(
                hqla_data=req.hqla,
                outflows_data=req.outflows,
                inflows_data=req.inflows,
                asf_data=req.asf,
                rsf_data=req.rsf,
            )
        except Exception as exc:
            logger.error("Basel liquidity ratios failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/pricing/structured-products", tags=["Derivatives & Volatility"])
    def run_structured_products_pricing(req: StructuredProductRequest) -> Dict[str, Any]:
        """Worst-Of Phoenix Autocallables with memory coupons & Reverse Convertibles pricer with Greeks."""
        try:
            return compute_structured_product_pricing(
                product_type=req.product_type,
                nominal=req.nominal,
                maturity_years=req.maturity_years,
                observation_frequency_months=req.observation_frequency_months,
                coupon_rate_p_a=req.coupon_rate_p_a,
                has_memory_coupon=req.has_memory_coupon,
                coupon_barrier_pct=req.coupon_barrier_pct,
                autocall_barrier_pct=req.autocall_barrier_pct,
                protection_barrier_pct=req.protection_barrier_pct,
                underlyings=req.underlyings,
                spots=req.spots,
                volatilities=req.volatilities,
                risk_free_rate=req.risk_free_rate,
                n_simulations=req.n_simulations,
            )
        except Exception as exc:
            logger.error("Structured products pricing failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/v1/regulatory/priips-sfdr", tags=["Stress Testing & Regulatory"])
    def run_regulatory_dossier(req: RegulatoryReportingRequest) -> Dict[str, Any]:
        """PRIIPs RTS Summary Risk Indicator (SRI 1-7), 4 Performance Scenarios, and SFDR Annex I 14 PAI table."""
        try:
            return compute_regulatory_dossier(
                historical_returns=req.historical_returns,
                issuer_credit_rating=req.issuer_credit_rating,
                rhp_years=req.rhp_years,
                investment_amount_eur=req.investment_amount_eur,
                sfdr_article=req.sfdr_article,
                taxonomy_alignment_pct=req.taxonomy_alignment_pct,
                sustainable_investment_pct=req.sustainable_investment_pct,
                custom_pai=req.custom_pai,
            )
        except Exception as exc:
            logger.error("Regulatory dossier generation failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

    return app


# Application singleton
app = create_app() if HAS_FASTAPI else None


def run_api():
    """CLI entrypoint for running the headless FastAPI microservice."""
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run_api()

