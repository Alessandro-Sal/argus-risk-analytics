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
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = object  # Fallback for type hinting

from core.bitemporal_engine import BitemporalLedgerEngine
from core.services.rebalancing_service import RebalancingService
from core.services.risk_service import RiskService
from core.services.tax_service import TaxService
from core.services.wealth_service import WealthService

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
            "Cornish-Fisher VaR/CVaR, Hierarchical Risk Parity (HRP) portfolio optimization, "
            "and ISO/IEC 9075:2011 bitemporal ledger time-travel reconstruction."
        ),
        version="9.0.0",
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
            version="9.0.0",
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

    return app


# Application singleton
app = create_app() if HAS_FASTAPI else None


def run_api():
    """CLI entrypoint for running the headless FastAPI microservice."""
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run_api()

