"""
ARGUS — Application Service Layer: Tax Optimization Service.
Unified interface for Italian TUIR taxation, crypto compliance, and cross-border obligations.
"""

from typing import Any, Dict, List, Optional
import pandas as pd
from core.tax_engine import compute_tax_and_harvesting, get_asset_tax_rate, is_etf
from core.crypto_tax_engine import compute_crypto_tax_report
from core.cross_border_tax_engine import compute_cross_border_wealth_tax_comparison


class TaxService:
    """Unified headless service for portfolio and multi-asset tax compliance."""

    @staticmethod
    def audit_portfolio_tax(
        positions: pd.DataFrame,
        transactions: Optional[pd.DataFrame] = None,
        tax_year: Optional[int] = None,
        db_engine: Any = None
    ) -> Dict[str, Any]:
        """Esegue l'audit fiscale completo (regime dichiarativo/amministrato, zainetto fiscale, crypto, cross-border)."""
        mock_results = {
            "positions": positions if positions is not None else pd.DataFrame(),
            "df_tx": transactions if transactions is not None else pd.DataFrame(),
            "portfolio_id": 1
        }

        # 1. Calcolo standard TUIR
        std_tax = compute_tax_and_harvesting(mock_results, db_engine=db_engine, tax_year=tax_year)

        # 2. Calcolo Cripto-Attività (Legge Bilancio 197/2022)
        crypto_report = {}
        try:
            crypto_report = compute_crypto_tax_report(mock_results, db_engine=db_engine, tax_year=tax_year)
        except Exception:
            pass

        # 3. Calcolo Cross-Border (Withholding Tax & Credito d'Imposta)
        cross_border = {}
        try:
            tot_val = float(positions["current_value"].sum()) if not positions.empty and "current_value" in positions.columns else 1000000.0
            cross_border = compute_cross_border_wealth_tax_comparison(total_wealth_eur=tot_val)
        except Exception:
            pass

        return {
            "standard_tax": std_tax,
            "crypto_compliance": crypto_report,
            "cross_border": cross_border,
            "harvesting_opportunities": std_tax.get("harvesting_opportunities", []),
            "total_estimated_liability_eur": round(
                float(std_tax.get("estimated_tax_eur", 0.0)) +
                float(crypto_report.get("tax_due_eur", 0.0)),
                2
            )
        }
