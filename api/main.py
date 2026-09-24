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
    from fastapi import FastAPI, HTTPException, Query, Response
    from fastapi.middleware.cors import CORSMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = object  # Fallback for type hinting

from core.advanced_quant import compute_risk_budgeting_portfolio
from core.bitemporal_engine import BitemporalLedgerEngine
from core.factor_library import compute_fama_french_factor_model
from core.fixed_income import compute_bond_analytics
from core.macro_stress_engine import compute_reverse_stress_test
from core.pdf_generator import generate_institutional_portfolio_factsheet_pdf
from core.risk_engine import compute_portfolio_liquidity_risk
from core.services.rebalancing_service import RebalancingService
from core.services.risk_service import RiskService
from core.services.tax_service import TaxService
from core.services.wealth_service import WealthService
from core.tax_engine import compute_tax_and_harvesting

logger = logging.getLogger("argus.api")

# ============================================================
# Pydantic Request & Response Schemas (v2 Compatible)
# ============================================================

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
        version="9.10.0",
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

    # In-memory bitemporal ledger instance for demonstration and stateless caching
    ledger_instance = BitemporalLedgerEngine(db_path=":memory:")

    # ── Health Endpoint ──────────────────────────────────────────

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    def get_health() -> HealthResponse:
        """Returns microservice health status, engine version, and DuckDB availability."""
        from core.bitemporal_engine import HAS_DUCKDB
        return HealthResponse(
            status="healthy",
            version="9.10.0",
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

    return app


# Application singleton
app = create_app() if HAS_FASTAPI else None


def run_api():
    """CLI entrypoint for running the headless FastAPI microservice."""
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run_api()

