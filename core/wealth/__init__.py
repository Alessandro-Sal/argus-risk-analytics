# ============================================================
# core/wealth/__init__.py
# ARGUS — Wealth Management & Personal Finance Package
# ============================================================

from core.wealth.wealth_models import (
    WealthAccount,
    WealthCategory,
    WealthCashflowItem,
    PhysicalAssetItem,
    PensionPlanItem,
    NetWorthSummary,
    WealthConsolidatedSummary,
    AccountType,
    CategoryNature,
    PhysicalAssetCategory
)
from core.wealth.wealth_db import (
    init_wealth_db,
    get_wealth_accounts,
    save_wealth_account,
    get_wealth_categories,
    save_wealth_category,
    get_cashflow_records,
    insert_cashflow_tx,
    get_physical_assets,
    save_physical_asset,
    get_pension_plans,
    save_pension_plan,
    save_wealth_snapshot_to_db,
    get_wealth_snapshots_history,
    delete_wealth_snapshot,
    load_wealth_snapshot_details,
    delete_wealth_account,
    deduplicate_wealth_accounts,
    get_wealth_portfolios,
    create_wealth_portfolio,
    delete_wealth_portfolio,
    cleanup_empty_wealth_portfolios,
    clear_wealth_cashflow,
    clear_wealth_snapshots,
    clear_wealth_accounts,
    reset_wealth_portfolio_data,
    reset_all_wealth_database,
    get_available_risk_portfolios,
    get_linked_risk_portfolios,
    set_linked_risk_portfolios,
    get_linked_risk_portfolios_summary,
    get_wealth_fixed_expenses,
    save_wealth_fixed_expense,
    clear_wealth_fixed_expenses
)






from core.wealth.wealth_engine import (
    compute_consolidated_net_worth,
    compute_cashflow_analytics,
    compute_wealth_health_score,
    simulate_pension_projection,
    compute_fire_analytics,
    compute_wealth_stress_test,
    compute_fiscal_analytics,
    compute_mortgage_amortization,
    compute_real_estate_roi,
    compute_buy_vs_rent_comparison,
    compute_estate_planning_analytics,
    compute_ai_wealth_diagnostics,
    generate_executive_tear_sheet_html,
    generate_executive_tear_sheet_pdf,
    compute_recurring_subscriptions_analytics,
    compute_cashflow_forecast_and_anomalies,
    compute_tax_loss_harvesting_and_latent_taxes,
    compute_wealth_risk_integrated_analytics
)


from core.wealth.wealth_importer import (
    parse_universal_statement,
    auto_categorize_transactions,
    bulk_import_statement
)
from core.wealth.wealth_validator import (
    validate_cashflow_df,
    validate_physical_assets_df,
    validate_accounts_df,
    validate_pension_df
)
from core.wealth.wealth_sync import (
    sync_expenses_tracker_2026_from_gsheets,
    sync_all_historical_expenses_from_gsheets,
    sync_wealth_from_payload
)

from core.wealth.wealth_exporter import (
    export_wealth_master_excel_workbook
)




