"""
ARGUS — Headless Quantitative Risk Engine & REST API Microservice.
Provides institutional REST endpoints for:
1. Advanced Market Risk & Return Metrics (Cornish-Fisher VaR/CVaR, Sharpe, Sortino)
2. Hierarchical Risk Parity (HRP) Portfolio Optimization
3. Bitemporal Time-Travel Ledger & Merkle Audit Seal
"""

from datetime import datetime, timezone
import logging
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
from core.hrp_optimizer import compute_hrp_portfolio
from core.risk_engine import _calc_market_risk, _calc_return_metrics

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
        version="8.4.0",
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
            version="8.4.0",
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
            sr_portfolio = pd.Series(req.returns, dtype=float).dropna()
            if len(sr_portfolio) < 2:
                raise HTTPException(
                    status_code=422,
                    detail="Return series must contain at least 2 non-null observations."
                )

            if req.benchmark_returns is not None:
                sr_bm = pd.Series(req.benchmark_returns, dtype=float).reindex(sr_portfolio.index).fillna(0.0)
            else:
                sr_bm = pd.Series(0.0, index=sr_portfolio.index)

            mkt_risk = _calc_market_risk(
                sr_portfolio=sr_portfolio,
                sr_benchmark=sr_bm,
                benchmark_ticker="BENCHMARK",
                risk_free_rate=req.risk_free_rate
            )

            ret_metrics = _calc_return_metrics(
                sr_portfolio=sr_portfolio,
                sr_benchmark=sr_bm,
                risk_free_rate=req.risk_free_rate
            )

            var_raw = mkt_risk.get("var", {})
            cvar_raw = mkt_risk.get("cvar", {})

            var_hist = {f"{k}%": v for k, v in var_raw.items() if not k.startswith("var_parametric") and not k.startswith("var_cf")}
            cvar_hist = {f"{k}%": v for k, v in cvar_raw.items() if not k.startswith("cvar_parametric") and not k.startswith("cvar_cf")}

            var_param = {k.replace("var_parametric_", "") + "%": v for k, v in var_raw.items() if k.startswith("var_parametric_")}
            cvar_param = {k.replace("cvar_parametric_", "") + "%": v for k, v in cvar_raw.items() if k.startswith("cvar_parametric_")}

            var_cf = {k.replace("var_cf_", "") + "%": v for k, v in var_raw.items() if k.startswith("var_cf_")}
            cvar_cf = {k.replace("cvar_cf_", "") + "%": v for k, v in cvar_raw.items() if k.startswith("cvar_cf_")}

            vol_pct = float(mkt_risk.get("volatility_annual_pct", 0.0))

            return RiskMetricsResponse(
                var_historical=var_hist,
                cvar_historical=cvar_hist,
                var_parametric=var_param,
                cvar_parametric=cvar_param,
                var_cornish_fisher=var_cf,
                cvar_cornish_fisher=cvar_cf,
                sharpe_ratio=float(ret_metrics.get("sharpe", 0.0)),
                sortino_ratio=float(ret_metrics.get("sortino", 0.0)),
                max_drawdown=float(ret_metrics.get("max_drawdown", 0.0)),
                volatility_annual=round(vol_pct / 100.0, 6),
                volatility_annual_pct=round(vol_pct, 4),
                cagr=ret_metrics.get("cagr"),
                skewness=float(mkt_risk.get("skewness", 0.0)),
                kurtosis=float(mkt_risk.get("kurtosis", 0.0)),
            )
        except HTTPException:
            raise
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
            df_returns = pd.DataFrame(req.asset_returns).dropna(axis=0, how="any")
            if df_returns.shape[0] < 5:
                df_returns = pd.DataFrame(req.asset_returns).fillna(0.0)

            result = compute_hrp_portfolio(df_returns, linkage_method=req.linkage_method)
            if not result or "weights" not in result:
                raise HTTPException(
                    status_code=400,
                    detail="HRP optimization could not converge on provided asset returns."
                )

            return HRPOptimizeResponse(
                weights={k: round(float(v), 6) for k, v in result["weights"].items()},
                expected_return_pct=round(float(result.get("expected_return_pct", 0.0)), 4),
                volatility_annual_pct=round(float(result.get("volatility_annual_pct", 0.0)), 4),
                sharpe_ratio=round(float(result.get("sharpe_ratio", 0.0)), 4),
                sorted_assets=result.get("sorted_assets", list(req.asset_returns.keys())),
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("HRP optimization failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"HRP optimization error: {str(exc)}"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
