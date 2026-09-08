import pytest
import numpy as np
import pandas as pd

from core.wealth.unified_stress_bridge import (
    MacroFactorShock,
    UnifiedCrossAssetStressEngine
)
from core.advanced_quant import compute_liquidity_adjusted_var
from core.fixed_income import (
    price_bond_cashflows_nelson_siegel,
    compute_key_rate_durations,
    compute_bond_cash_flows
)
from core.wealth.tax_aware_location import TaxAwareAssetLocator
from core.autonomous_rebalancer import generate_autonomous_rebalancing_proposal


# ==============================================================================
# 1. TEST UNIFIED CROSS-ASSET STRESS ENGINE (RISK ↔ WEALTH CONVERGENCE)
# ==============================================================================

def test_unified_cross_asset_stress_engine():
    # Setup portafoglio con azioni e obbligazioni
    df_pos = pd.DataFrame([
        {"ticker": "SWDA.MI", "weight": 60000.0, "asset_class": "equity", "currency": "EUR"},
        {"ticker": "XG7S.MI", "weight": 40000.0, "asset_class": "bond", "currency": "EUR", "duration": 6.5}
    ])
    df_betas = pd.DataFrame([
        {"ticker": "SWDA.MI", "beta_mkt": 1.05, "beta_rates": -0.10, "beta_fx": 0.0},
        {"ticker": "XG7S.MI", "beta_mkt": 0.05, "beta_rates": -6.50, "beta_fx": 0.0}
    ])

    engine = UnifiedCrossAssetStressEngine(df_pos, df_betas)

    # Snapshot patrimoniale
    wealth_snapshot = {
        "liquid_investments": 100000.0,
        "real_estate_gross": 300000.0,
        "variable_debt_principal": 150000.0,
        "mortgage_months_remaining": 240,
        "mortgage_interest_rate": 0.025,
        "current_monthly_payment": 794.84,
        "monthly_expenses": 2500.0,
        "monthly_income": 3500.0,
        "cash_reserves": 20000.0,
        "pension_total": 50000.0,
        "fire_swr_base": 3.75
    }

    # Shock: -20% azionario, +150 bps tassi, +4% inflazione
    shock = MacroFactorShock(
        equity_mkt_pct=-0.20,
        yield_curve_shift_bps=150.0,
        inflation_rate_pct=0.04,
        scenario_name="Stagflazione con Stretta Creditizia"
    )

    res = engine.evaluate_integrated_shock(shock, wealth_snapshot)

    # Verifiche matematiche
    assert res["liquid_pnl_pct"] < 0.0, "Il portafoglio liquido deve subire una perdita"
    assert res["stressed_liquid_val"] < 100000.0
    assert res["stressed_re_val"] < 300000.0, "L'immobile deve subire repricing da espansione del cap-rate"
    assert res["new_monthly_payment"] > res["curr_monthly_payment"], "Il rialzo tassi deve aumentare la rata del mutuo variabile"
    assert res["delta_monthly_debt"] > 0.0
    assert res["stressed_monthly_expenses"] > 2500.0, "L'inflazione + debito deve incrementare le uscite mensili"
    assert res["months_to_forced_liquidation"] > 0.0
    assert res["fire_swr_stressed_pct"] < res["fire_swr_base_pct"], "L'SWR deve ridursi prudenzialmente sotto shock"
    assert res["post_stress_net_worth"] < res["pre_stress_net_worth"]


# ==============================================================================
# 2. TEST LIQUIDITY-ADJUSTED VALUE AT RISK (L-VaR)
# ==============================================================================

def test_liquidity_adjusted_var_math():
    position_values = [50000.0, 30000.0, 20000.0]
    # Matrice covarianza diagonale semplice
    cov = np.diag([0.0004, 0.0002, 0.0009])  # Volatilità giornaliera ~2%, 1.4%, 3%

    # Caso 1: Spread standard e volumi normali
    res_standard = compute_liquidity_adjusted_var(
        position_values=position_values,
        cov_matrix=cov,
        bid_ask_spreads=[0.0010, 0.0015, 0.0025],
        spread_volatilities=[0.0005, 0.0008, 0.0012],
        daily_volumes_eur=[1000000.0, 800000.0, 500000.0],
        confidence=0.95,
        max_adv_participation=0.10
    )

    assert res_standard["standard_var_eur"] > 0.0
    assert res_standard["l_var_total_eur"] > res_standard["standard_var_eur"], "L-VaR deve essere strettamente superiore al VaR puro"
    assert res_standard["exogenous_spread_cost_eur"] > 0.0
    assert res_standard["effective_liquidation_days"] >= 1
    assert res_standard["l_var_premium_pct"] > 0.0

    # Caso 2: Titolo illiquido con volume bassissimo che costringe a orizzonte prolungato
    res_illiquid = compute_liquidity_adjusted_var(
        position_values=position_values,
        cov_matrix=cov,
        bid_ask_spreads=[0.0010, 0.0015, 0.0200],  # 2% spread sul terzo asset
        spread_volatilities=[0.0005, 0.0008, 0.0100],
        daily_volumes_eur=[1000000.0, 800000.0, 50000.0],  # Solo 50k ADV per 20k posizione -> 4 giorni a 10% ADV
        confidence=0.95,
        max_adv_participation=0.10
    )

    assert res_illiquid["effective_liquidation_days"] >= 4
    assert res_illiquid["l_var_total_eur"] > res_standard["l_var_total_eur"]
    assert res_illiquid["exogenous_spread_cost_eur"] > res_standard["exogenous_spread_cost_eur"]


# ==============================================================================
# 3. TEST NELSON-SIEGEL CASHFLOW PRICING & KEY RATE DURATION
# ==============================================================================

def test_nelson_siegel_cashflow_pricing_and_krd():
    # Parametri calibrati tipici: Level=3.5%, Slope=-0.8%, Curvature=1.2%, tau=2.5
    ns_params = {
        "beta0": 3.50,
        "beta1": -0.80,
        "beta2": 1.20,
        "tau": 2.50
    }

    # BTP Decennale: nominale 100, cedola 4% semestrale
    cfs = compute_bond_cash_flows(face_value=100.0, coupon_rate=0.04, maturity_years=10.0, coupon_frequency=2)
    assert len(cfs) == 20

    pricing_res = price_bond_cashflows_nelson_siegel(cfs, ns_params, compounding_freq=2)
    assert pricing_res["fair_price"] > 90.0 and pricing_res["fair_price"] < 120.0
    assert pricing_res["macaulay_duration"] > 6.0 and pricing_res["macaulay_duration"] < 9.5
    assert pricing_res["modified_duration"] > 5.5 and pricing_res["modified_duration"] < 9.0
    assert pricing_res["convexity"] > 0.0

    # Key Rate Duration
    krd = compute_key_rate_durations(
        face_value=100.0,
        coupon_rate=0.04,
        maturity_years=10.0,
        ns_params=ns_params,
        key_rates=[2.0, 5.0, 10.0, 30.0],
        coupon_freq=2
    )

    assert "2Y" in krd and "5Y" in krd and "10Y" in krd and "30Y" in krd
    # Per un titolo a 10 anni, la massima sensibilità KRD deve concentrarsi attorno al nodo 10Y
    assert krd["10Y"] > krd["2Y"]
    assert krd["10Y"] > krd["30Y"]


# ==============================================================================
# 4. TEST TAX-AWARE ASSET LOCATOR
# ==============================================================================

def test_tax_aware_asset_locator():
    target_weights = {
        "GOV_BONDS": 0.30,
        "ACC_WORLD_EQUITY": 0.50,
        "HIGH_DIV_STOCKS": 0.20
    }
    capacities = {
        "PENSION_ACCOUNT": 30000.0,
        "TAXABLE_ACCOUNT": 70000.0
    }

    locator = TaxAwareAssetLocator(target_weights, capacities)
    res = locator.optimize_location()

    assert res["total_wealth_eur"] == 100000.0
    loc_matrix = res["location_matrix"]

    # Verifica rispetto capienze
    assert sum(loc_matrix["PENSION_ACCOUNT"].values()) <= 30000.01
    assert sum(loc_matrix["TAXABLE_ACCOUNT"].values()) <= 70000.01

    # High dividend / Gov bonds devono essere privilegiati nel bucket pensionistico
    assert "HIGH_DIV_STOCKS" in loc_matrix["PENSION_ACCOUNT"] or "GOV_BONDS" in loc_matrix["PENSION_ACCOUNT"]
    assert res["tax_alpha_bps"] > 0.0
    assert res["annual_tax_saving_eur"] > 0.0


# ==============================================================================
# 5. TEST AUTONOMOUS REBALANCING PROPOSAL WITH REAL PMC AND MINUSVALENZE OFFSET
# ==============================================================================

def test_autonomous_rebalancing_with_pmc_and_minusvalenze():
    # Portafoglio con PMC e prezzo corrente
    df_positions = pd.DataFrame([
        {
            "ticker": "AAPL",
            "controvalore": 40000.0,
            "prezzo_corrente": 200.0,
            "prezzo_medio_carico": 150.0  # Plusvalenza potenziale di 50€/azione
        },
        {
            "ticker": "BND",
            "controvalore": 10000.0,
            "prezzo_corrente": 100.0,
            "prezzo_medio_carico": 110.0  # Minusvalenza potenziale di 10€/azione
        }
    ])

    # Target: riduci AAPL a 20%, porta BND a 80% (richiede vendita massiccia di AAPL)
    targets = {"AAPL": 0.20, "BND": 0.80}

    # Caso 1: Nessuna minusvalenza nello zainetto -> paga imposta 26% piena
    res_no_minus = generate_autonomous_rebalancing_proposal(
        df_positions=df_positions,
        target_weights=targets,
        min_trade_eur=100.0,
        available_minusvalenze_eur=0.0
    )

    assert res_no_minus["total_sell_volume_eur"] > 0.0
    assert res_no_minus["estimated_tax_liability_eur"] > 0.0
    assert res_no_minus["total_tax_saved_by_harvesting_eur"] == 0.0

    # Caso 2: Zainetto capiente di € 10.000 -> assorbe la plusvalenza e azzera o abbatte le tasse
    res_with_minus = generate_autonomous_rebalancing_proposal(
        df_positions=df_positions,
        target_weights=targets,
        min_trade_eur=100.0,
        available_minusvalenze_eur=10000.0
    )

    assert res_with_minus["estimated_tax_liability_eur"] < res_no_minus["estimated_tax_liability_eur"]
    assert res_with_minus["total_tax_saved_by_harvesting_eur"] > 0.0
    assert res_with_minus["remaining_minusvalenze_eur"] < 10000.0
