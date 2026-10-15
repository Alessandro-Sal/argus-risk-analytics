# ============================================================
# core/wealth/__init__.py
# ARGUS — Wealth Management & Personal Finance Package
# PEP 562 Lazy Package Loading for Instant Imports
# ============================================================
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.wealth.asset_protection_engine import (
        AssetProtectionEngine,
        FamilyHeir,
        FamilyProfile,
        GenerationalTransferOptimizer,
        OptimizationComparisonResult,
        PlanningLevers,
        ProtectionVehicleAnalysis,
        StatutoryShareItem,
        SuccessionSharesResult,
    )
    from core.wealth.private_markets_engine import (
        DesmoothingResult,
        EconometricDesmoother,
        PacingYearRecord,
        PrivateEquityFundReport,
        TakahashiAlexanderPacingModel,
        compute_private_markets_analytics,
    )
    from core.wealth.succession_optimizer import (
        FamilyOfficeSuccessionOptimizer,
        compute_family_succession_optimization,
    )
    from core.wealth.tbs_monte_carlo import (
        TBSLifecycleConfig,
        TBSMonteCarloEngine,
        compute_stochastic_cash_flow_decumulation,
    )
    from core.wealth.total_wealth_reverse_stress import compute_total_wealth_reverse_stress
    from core.wealth.wealth_db import (
        cleanup_empty_wealth_portfolios,
        clear_wealth_accounts,
        clear_wealth_cashflow,
        clear_wealth_fixed_expenses,
        clear_wealth_snapshots,
        create_wealth_portfolio,
        deduplicate_wealth_accounts,
        delete_wealth_account,
        delete_wealth_portfolio,
        delete_wealth_snapshot,
        get_available_risk_portfolios,
        get_cashflow_records,
        get_linked_risk_portfolios,
        get_linked_risk_portfolios_summary,
        get_pension_plans,
        get_physical_assets,
        get_wealth_accounts,
        get_wealth_categories,
        get_wealth_fixed_expenses,
        get_wealth_portfolios,
        get_wealth_snapshots_history,
        init_wealth_db,
        insert_cashflow_tx,
        load_wealth_snapshot_details,
        reset_all_wealth_database,
        reset_wealth_portfolio_data,
        save_pension_plan,
        save_physical_asset,
        save_wealth_account,
        save_wealth_category,
        save_wealth_fixed_expense,
        save_wealth_snapshot_to_db,
        set_linked_risk_portfolios,
    )
    from core.wealth.wealth_engine import (
        compute_ai_quarterly_wealth_review,
        compute_ai_wealth_diagnostics,
        compute_buy_vs_rent_comparison,
        compute_cashflow_analytics,
        compute_cashflow_forecast_and_anomalies,
        compute_consolidated_net_worth,
        compute_estate_planning_analytics,
        compute_family_governance_and_patti_di_famiglia,
        compute_family_office_multi_entity_consolidation,
        compute_fire_analytics,
        compute_fiscal_analytics,
        compute_mortgage_amortization,
        compute_multi_currency_fx_hedging_engine,
        compute_multi_year_balance_comparison,
        compute_personal_balance_sheet,
        compute_private_equity_deal_metrics,
        compute_real_estate_net_equity_and_ltv,
        compute_real_estate_roi,
        compute_recurring_subscriptions_analytics,
        compute_sequence_of_returns_risk_engine,
        compute_smart_cashflow_reconciliation,
        compute_tax_loss_harvesting_and_latent_taxes,
        compute_tax_smart_rebalancing_watchdog,
        compute_total_wealth_brinson_attribution,
        compute_wealth_health_score,
        compute_wealth_risk_integrated_analytics,
        compute_wealth_stress_test,
        generate_advisory_pitchbook_html,
        generate_executive_tear_sheet_html,
        generate_executive_tear_sheet_pdf,
        simulate_pension_projection,
    )
    from core.wealth.wealth_exporter import export_wealth_master_excel_workbook
    from core.wealth.wealth_importer import (
        auto_categorize_transactions,
        bulk_import_statement,
        parse_universal_statement,
    )
    from core.wealth.wealth_models import (
        AccountType,
        BrinsonWealthBucketItem,
        BrinsonWealthResult,
        CategoryNature,
        FamilyGovernancePlan,
        FamilyOfficeEntityItem,
        FXExposureItem,
        FXHedgingResult,
        LegalEntityType,
        NetWorthSummary,
        PattoFamigliaResult,
        PECashflowItem,
        PEDealMetrics,
        PensionPlanItem,
        PhysicalAssetCategory,
        PhysicalAssetItem,
        PrivateEquityDealItem,
        QuarterlyReviewResult,
        ReconciliationMatchItem,
        ReconciliationResult,
        SRRScenarioResult,
        WealthAccount,
        WealthCashflowItem,
        WealthCategory,
        WealthConsolidatedSummary,
    )
    from core.wealth.wealth_olap import (
        compute_wealth_cashflow_olap_cube,
        compute_wealth_snapshot_trajectory_olap,
        is_wealth_olap_available,
    )
    from core.wealth.wealth_stress_engine import (
        PRESET_STRESS_SCENARIOS,
        UnifiedMacroStressEngine,
        calculate_liquidity_squeeze,
        calculate_stressed_mortgage_impact,
        create_liquidity_squeeze_timeline_chart,
        create_wealth_waterfall_chart,
        run_wealth_stress_test,
        simulate_wealth_recovery_trajectories,
    )
    from core.wealth.wealth_sync import (
        sync_all_historical_expenses_from_gsheets,
        sync_expenses_tracker_2026_from_gsheets,
        sync_wealth_from_payload,
    )
    from core.wealth.wealth_validator import (
        validate_accounts_df,
        validate_cashflow_df,
        validate_pension_df,
        validate_physical_assets_df,
    )

_LAZY_EXPORTS: dict[str, str] = {
    # asset_protection_engine
    "AssetProtectionEngine": "core.wealth.asset_protection_engine",
    "FamilyHeir": "core.wealth.asset_protection_engine",
    "FamilyProfile": "core.wealth.asset_protection_engine",
    "GenerationalTransferOptimizer": "core.wealth.asset_protection_engine",
    "OptimizationComparisonResult": "core.wealth.asset_protection_engine",
    "PlanningLevers": "core.wealth.asset_protection_engine",
    "ProtectionVehicleAnalysis": "core.wealth.asset_protection_engine",
    "StatutoryShareItem": "core.wealth.asset_protection_engine",
    "SuccessionSharesResult": "core.wealth.asset_protection_engine",
    # private_markets_engine
    "DesmoothingResult": "core.wealth.private_markets_engine",
    "EconometricDesmoother": "core.wealth.private_markets_engine",
    "PacingYearRecord": "core.wealth.private_markets_engine",
    "PrivateEquityFundReport": "core.wealth.private_markets_engine",
    "TakahashiAlexanderPacingModel": "core.wealth.private_markets_engine",
    "compute_private_markets_analytics": "core.wealth.private_markets_engine",
    # succession_optimizer
    "FamilyOfficeSuccessionOptimizer": "core.wealth.succession_optimizer",
    "compute_family_succession_optimization": "core.wealth.succession_optimizer",
    # tbs_monte_carlo
    "TBSLifecycleConfig": "core.wealth.tbs_monte_carlo",
    "TBSMonteCarloEngine": "core.wealth.tbs_monte_carlo",
    "compute_stochastic_cash_flow_decumulation": "core.wealth.tbs_monte_carlo",
    # total_wealth_reverse_stress
    "compute_total_wealth_reverse_stress": "core.wealth.total_wealth_reverse_stress",
    # wealth_db
    "cleanup_empty_wealth_portfolios": "core.wealth.wealth_db",
    "clear_wealth_accounts": "core.wealth.wealth_db",
    "clear_wealth_cashflow": "core.wealth.wealth_db",
    "clear_wealth_fixed_expenses": "core.wealth.wealth_db",
    "clear_wealth_snapshots": "core.wealth.wealth_db",
    "create_wealth_portfolio": "core.wealth.wealth_db",
    "deduplicate_wealth_accounts": "core.wealth.wealth_db",
    "delete_wealth_account": "core.wealth.wealth_db",
    "delete_wealth_portfolio": "core.wealth.wealth_db",
    "delete_wealth_snapshot": "core.wealth.wealth_db",
    "get_available_risk_portfolios": "core.wealth.wealth_db",
    "get_cashflow_records": "core.wealth.wealth_db",
    "get_linked_risk_portfolios": "core.wealth.wealth_db",
    "get_linked_risk_portfolios_summary": "core.wealth.wealth_db",
    "get_pension_plans": "core.wealth.wealth_db",
    "get_physical_assets": "core.wealth.wealth_db",
    "get_wealth_accounts": "core.wealth.wealth_db",
    "get_wealth_categories": "core.wealth.wealth_db",
    "get_wealth_fixed_expenses": "core.wealth.wealth_db",
    "get_wealth_portfolios": "core.wealth.wealth_db",
    "get_wealth_snapshots_history": "core.wealth.wealth_db",
    "init_wealth_db": "core.wealth.wealth_db",
    "insert_cashflow_tx": "core.wealth.wealth_db",
    "load_wealth_snapshot_details": "core.wealth.wealth_db",
    "reset_all_wealth_database": "core.wealth.wealth_db",
    "reset_wealth_portfolio_data": "core.wealth.wealth_db",
    "save_pension_plan": "core.wealth.wealth_db",
    "save_physical_asset": "core.wealth.wealth_db",
    "save_wealth_account": "core.wealth.wealth_db",
    "save_wealth_category": "core.wealth.wealth_db",
    "save_wealth_fixed_expense": "core.wealth.wealth_db",
    "save_wealth_snapshot_to_db": "core.wealth.wealth_db",
    "set_linked_risk_portfolios": "core.wealth.wealth_db",
    # wealth_engine
    "compute_ai_quarterly_wealth_review": "core.wealth.wealth_engine",
    "compute_ai_wealth_diagnostics": "core.wealth.wealth_engine",
    "compute_buy_vs_rent_comparison": "core.wealth.wealth_engine",
    "compute_cashflow_analytics": "core.wealth.wealth_engine",
    "compute_cashflow_forecast_and_anomalies": "core.wealth.wealth_engine",
    "compute_consolidated_net_worth": "core.wealth.wealth_engine",
    "compute_estate_planning_analytics": "core.wealth.wealth_engine",
    "compute_family_governance_and_patti_di_famiglia": "core.wealth.wealth_engine",
    "compute_family_office_multi_entity_consolidation": "core.wealth.wealth_engine",
    "compute_fire_analytics": "core.wealth.wealth_engine",
    "compute_fiscal_analytics": "core.wealth.wealth_engine",
    "compute_mortgage_amortization": "core.wealth.wealth_engine",
    "compute_multi_currency_fx_hedging_engine": "core.wealth.wealth_engine",
    "compute_multi_year_balance_comparison": "core.wealth.wealth_engine",
    "compute_personal_balance_sheet": "core.wealth.wealth_engine",
    "compute_private_equity_deal_metrics": "core.wealth.wealth_engine",
    "compute_real_estate_net_equity_and_ltv": "core.wealth.wealth_engine",
    "compute_real_estate_roi": "core.wealth.wealth_engine",
    "compute_recurring_subscriptions_analytics": "core.wealth.wealth_engine",
    "compute_sequence_of_returns_risk_engine": "core.wealth.wealth_engine",
    "compute_smart_cashflow_reconciliation": "core.wealth.wealth_engine",
    "compute_tax_loss_harvesting_and_latent_taxes": "core.wealth.wealth_engine",
    "compute_tax_smart_rebalancing_watchdog": "core.wealth.wealth_engine",
    "compute_total_wealth_brinson_attribution": "core.wealth.wealth_engine",
    "compute_wealth_health_score": "core.wealth.wealth_engine",
    "compute_wealth_risk_integrated_analytics": "core.wealth.wealth_engine",
    "compute_wealth_stress_test": "core.wealth.wealth_engine",
    "generate_advisory_pitchbook_html": "core.wealth.wealth_engine",
    "generate_executive_tear_sheet_html": "core.wealth.wealth_engine",
    "generate_executive_tear_sheet_pdf": "core.wealth.wealth_engine",
    "simulate_pension_projection": "core.wealth.wealth_engine",
    # wealth_exporter
    "export_wealth_master_excel_workbook": "core.wealth.wealth_exporter",
    # wealth_importer
    "auto_categorize_transactions": "core.wealth.wealth_importer",
    "bulk_import_statement": "core.wealth.wealth_importer",
    "parse_universal_statement": "core.wealth.wealth_importer",
    # wealth_models
    "AccountType": "core.wealth.wealth_models",
    "BrinsonWealthBucketItem": "core.wealth.wealth_models",
    "BrinsonWealthResult": "core.wealth.wealth_models",
    "CategoryNature": "core.wealth.wealth_models",
    "FamilyGovernancePlan": "core.wealth.wealth_models",
    "FamilyOfficeEntityItem": "core.wealth.wealth_models",
    "FXExposureItem": "core.wealth.wealth_models",
    "FXHedgingResult": "core.wealth.wealth_models",
    "LegalEntityType": "core.wealth.wealth_models",
    "NetWorthSummary": "core.wealth.wealth_models",
    "PattoFamigliaResult": "core.wealth.wealth_models",
    "PECashflowItem": "core.wealth.wealth_models",
    "PEDealMetrics": "core.wealth.wealth_models",
    "PensionPlanItem": "core.wealth.wealth_models",
    "PhysicalAssetCategory": "core.wealth.wealth_models",
    "PhysicalAssetItem": "core.wealth.wealth_models",
    "PrivateEquityDealItem": "core.wealth.wealth_models",
    "QuarterlyReviewResult": "core.wealth.wealth_models",
    "ReconciliationMatchItem": "core.wealth.wealth_models",
    "ReconciliationResult": "core.wealth.wealth_models",
    "SRRScenarioResult": "core.wealth.wealth_models",
    "WealthAccount": "core.wealth.wealth_models",
    "WealthCashflowItem": "core.wealth.wealth_models",
    "WealthCategory": "core.wealth.wealth_models",
    "WealthConsolidatedSummary": "core.wealth.wealth_models",
    # wealth_olap
    "compute_wealth_cashflow_olap_cube": "core.wealth.wealth_olap",
    "compute_wealth_snapshot_trajectory_olap": "core.wealth.wealth_olap",
    "is_wealth_olap_available": "core.wealth.wealth_olap",
    # wealth_stress_engine
    "PRESET_STRESS_SCENARIOS": "core.wealth.wealth_stress_engine",
    "UnifiedMacroStressEngine": "core.wealth.wealth_stress_engine",
    "calculate_liquidity_squeeze": "core.wealth.wealth_stress_engine",
    "calculate_stressed_mortgage_impact": "core.wealth.wealth_stress_engine",
    "create_liquidity_squeeze_timeline_chart": "core.wealth.wealth_stress_engine",
    "create_wealth_waterfall_chart": "core.wealth.wealth_stress_engine",
    "run_wealth_stress_test": "core.wealth.wealth_stress_engine",
    "simulate_wealth_recovery_trajectories": "core.wealth.wealth_stress_engine",
    # wealth_sync
    "sync_all_historical_expenses_from_gsheets": "core.wealth.wealth_sync",
    "sync_expenses_tracker_2026_from_gsheets": "core.wealth.wealth_sync",
    "sync_wealth_from_payload": "core.wealth.wealth_sync",
    # wealth_validator
    "validate_accounts_df": "core.wealth.wealth_validator",
    "validate_cashflow_df": "core.wealth.wealth_validator",
    "validate_pension_df": "core.wealth.wealth_validator",
    "validate_physical_assets_df": "core.wealth.wealth_validator",
}


def __getattr__(name: str) -> Any:
    target_mod = _LAZY_EXPORTS.get(name)
    if target_mod:
        mod = importlib.import_module(target_mod)
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))


__all__ = list(_LAZY_EXPORTS.keys())
