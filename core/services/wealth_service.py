"""
ARGUS — Application Service Layer: Wealth Intelligence Service.
Headless orchestration of Personal Balance Sheet, Net Worth consolidation, and Cash Flow dynamics.
"""

from typing import Any, Dict, Optional
from core.wealth.wealth_engine import compute_consolidated_net_worth


class WealthService:
    """Headless application service for personal wealth management and balance sheet."""

    @staticmethod
    def get_consolidated_net_worth(db_engine: Any = None, portfolio_id: Optional[int] = None) -> Dict[str, Any]:
        """Restituisce il riepilogo consolidato del patrimonio netto e della ripartizione per asset class."""
        if db_engine is None:
            # Fallback mock/sandbox se nessun engine passato
            return {
                "total_net_worth": 100000.0,
                "liquid_cash": 20000.0,
                "financial_investments": 50000.0,
                "real_estate_total": 30000.0,
                "physical_assets": 0.0,
                "pension_total": 0.0,
                "total_liabilities": 0.0,
                "solvency_ratio": 1.0,
                "health_score": 85.0
            }

        nw = compute_consolidated_net_worth(db_engine, portfolio_id=portfolio_id)
        return {
            "total_net_worth": float(getattr(nw, "total_net_worth", 0.0)),
            "liquid_cash": float(getattr(nw, "liquid_cash", 0.0)),
            "financial_investments": float(getattr(nw, "financial_investments", 0.0)),
            "real_estate_total": float(getattr(nw, "real_estate_total", 0.0)),
            "physical_assets": float(getattr(nw, "physical_assets", 0.0)),
            "pension_total": float(getattr(nw, "pension_total", 0.0)),
            "total_liabilities": float(getattr(nw, "total_liabilities", 0.0)),
            "solvency_ratio": float(getattr(nw, "solvency_ratio", 1.0)),
            "health_score": float(getattr(nw, "health_score", 75.0))
        }
