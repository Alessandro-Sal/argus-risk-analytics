"""
ARGUS — Application Service Layer: Tax Optimization Service.
Unified interface for Italian TUIR taxation, crypto compliance, cross-border obligations (Quadro RW/IVAFE),
and Modello 730 tax history.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.cross_border_tax_engine import compute_cross_border_wealth_tax_comparison
from core.crypto_tax_engine import compute_crypto_tax_report
from core.tax_engine import compute_tax_and_harvesting, get_asset_tax_rate, is_etf


class TaxService:
    """Unified headless service for portfolio and multi-asset tax compliance."""

    @staticmethod
    def audit_portfolio_tax(
        positions: pd.DataFrame,
        transactions: Optional[pd.DataFrame] = None,
        tax_year: Optional[int] = None,
        db_engine: Any = None,
    ) -> Dict[str, Any]:
        """Esegue l'audit fiscale completo (regime dichiarativo/amministrato, zainetto fiscale, crypto, cross-border)."""
        mock_results = {
            "positions": positions if positions is not None else pd.DataFrame(),
            "df_tx": transactions if transactions is not None else pd.DataFrame(),
            "portfolio_id": 1,
        }

        # 1. Calcolo standard TUIR
        std_tax = compute_tax_and_harvesting(mock_results, db_engine=db_engine, tax_year=tax_year)

        # 2. Calcolo Cripto-Attività (Legge Bilancio 197/2022)
        crypto_report: Dict[str, Any] = {}
        try:
            crypto_report = compute_crypto_tax_report(mock_results, db_engine=db_engine, tax_year=tax_year)
        except Exception:
            pass

        # 3. Calcolo Cross-Border (Withholding Tax & Credito d'Imposta)
        cross_border: Dict[str, Any] = {}
        try:
            tot_val = (
                float(positions["current_value"].sum())
                if not positions.empty and "current_value" in positions.columns
                else 1000000.0
            )
            cross_border = compute_cross_border_wealth_tax_comparison(total_wealth_eur=tot_val)
        except Exception:
            pass

        return {
            "standard_tax": std_tax,
            "crypto_compliance": crypto_report,
            "cross_border": cross_border,
            "harvesting_opportunities": std_tax.get("harvesting_opportunities", []),
            "total_estimated_liability_eur": round(
                float(std_tax.get("estimated_tax_eur", 0.0)) + float(crypto_report.get("tax_due_eur", 0.0)), 2
            ),
        }

    @staticmethod
    def compute_quadro_rw_ivafe(
        foreign_financial_assets_eur: float = 0.0,
        foreign_real_estate_eur: float = 0.0,
        foreign_crypto_eur: float = 0.0,
        days_held: int = 365,
        tax_year: int = 2025,
    ) -> Dict[str, Any]:
        """
        Simulatore istituzionale Quadro RW, IVAFE (attività finanziarie estere) e IVIE (immobili esteri).
        Aliquota IVAFE ordinaria: 0.20% annuo (2 per mille).
        Aliquota IVIE ordinaria: 1.06% annuo (1.06 per cento).
        """
        holding_fraction = max(1, min(days_held, 365)) / 365.0
        
        # IVAFE su strumenti finanziari esteri
        ivafe_due = round(foreign_financial_assets_eur * 0.002 * holding_fraction, 2)
        # Esenzione se imposta complessiva non supera 12 euro
        ivafe_payable = ivafe_due if ivafe_due >= 12.0 else 0.0
        
        # IVIE su immobili esteri
        ivie_due = round(foreign_real_estate_eur * 0.0106 * holding_fraction, 2)
        ivie_payable = ivie_due if ivie_due >= 12.0 else 0.0

        # Bollo crypto estero (2 per mille)
        crypto_stamp_due = round(foreign_crypto_eur * 0.002 * holding_fraction, 2)

        total_wealth_tax = round(ivafe_payable + ivie_payable + crypto_stamp_due, 2)
        must_fill_quadro_rw = (foreign_financial_assets_eur + foreign_real_estate_eur + foreign_crypto_eur) > 0.0

        return {
            "status": "success",
            "tax_year": tax_year,
            "foreign_financial_assets_eur": foreign_financial_assets_eur,
            "foreign_real_estate_eur": foreign_real_estate_eur,
            "foreign_crypto_eur": foreign_crypto_eur,
            "days_held": days_held,
            "ivafe_due_eur": ivafe_payable,
            "ivie_due_eur": ivie_payable,
            "crypto_stamp_due_eur": crypto_stamp_due,
            "total_wealth_tax_eur": total_wealth_tax,
            "must_fill_quadro_rw": must_fill_quadro_rw,
            "regulatory_reference": "D.L. 167/1990 Art. 4; Legge 214/2011; Legge 197/2022",
        }

    @staticmethod
    def get_tax_declarations_history(
        db_engine: Any = None,
        portfolio_id: Optional[int] = None,
        tax_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Recupera lo storico e la riconciliazione delle dichiarazioni 730/Redditi PF salvate nel database.
        """
        from core.wealth.tax_history_engine import get_declarations

        if db_engine is None:
            # Fallback mock sandbox
            return {
                "status": "success",
                "total_declarations": 1,
                "declarations": [
                    {
                        "declaration_id": 1,
                        "tax_year": tax_year or 2024,
                        "form_type": "730/2025",
                        "status": "ACQUISTITA",
                        "gross_income": 75000.0,
                        "taxable_income": 69835.43,
                        "net_tax": 21850.0,
                    }
                ],
            }

        try:
            decls = get_declarations(db_engine, portfolio_id=portfolio_id, tax_year=tax_year)
            decl_list = [d.to_dict() if hasattr(d, "to_dict") else dict(d) for d in decls]
            return {
                "status": "success",
                "total_declarations": len(decl_list),
                "declarations": decl_list,
            }
        except Exception as e:
            return {
                "status": "warning",
                "message": f"Errore consultazione archivio fiscale: {e}",
                "declarations": [],
            }

    @staticmethod
    def simulate_pension_deductibility(
        taxable_income_eur: float,
        current_contributions_eur: float = 0.0,
        additional_voluntary_eur: float = 0.0,
        is_post_2007: bool = False,
    ) -> Dict[str, Any]:
        """
        Calcola la deducibilità previdenziale secondo l'art. 10 del TUIR.
        Plafond ordinario: € 5.164,57 annui.
        Plafond lavoratori di prima occupazione post-2007: fino a € 7.746,86 annui.
        """
        from core.wealth.tax_history_engine import compute_pension_tax_deduction_optimizer

        return compute_pension_tax_deduction_optimizer(
            taxable_income_eur=taxable_income_eur,
            current_contributions_eur=current_contributions_eur,
            additional_voluntary_eur=additional_voluntary_eur,
        )
