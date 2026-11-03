"""
ARGUS Wealth - Unit Tests for Dynamic Precious Metals & Gold Spot Valuation Engine
==================================================================================
Tests for:
- Deterministic parsing of carats, purity, grams and reference prices
- Real-time spot rates and LBMA/COMEX fixing calculation
- Historical daily EUR/g spot time series and point-in-time retrieval
- Dynamic asset evaluation and latent PnL calculation
- Portfolio historical trajectory reconstruction
"""

from datetime import date, datetime

import pandas as pd
import pytest

from core.wealth.gold_engine import (
    BASELINE_SPOT_18K_EUR_G,
    BASELINE_SPOT_24K_EUR_G,
    CARAT_PURITY_MAP,
    compute_gold_portfolio_historical_trajectory,
    evaluate_metal_asset_dynamically,
    get_gold_historical_series,
    get_gold_spot_on_date,
    get_live_gold_spot_rates,
    parse_precious_metal_specs,
)


def test_parse_precious_metal_specs_18k_jewelry():
    asset = {
        "name": "Bracciali",
        "asset_category": "precious_metals",
        "brand_or_location": "Oro (18K)",
        "model_or_specs": "15g @ € 88,00",
        "current_market_value": 1320.0,
        "purchase_price": 0.0,
    }
    specs = parse_precious_metal_specs(asset)
    assert specs["is_precious_metal"] is True
    assert specs["metal"] == "gold"
    assert specs["carat"] == "18K"
    assert specs["purity_factor"] == 0.750
    assert specs["weight_grams"] == 15.0
    assert specs["fine_gold_grams"] == 11.25
    assert specs["ref_price_per_g"] == 88.0


def test_parse_precious_metal_specs_24k_bullion():
    asset = {
        "name": "Lingotto Oro Puro 999",
        "asset_category": "precious_metals",
        "brand_or_location": "Argor-Heraeus",
        "model_or_specs": "50g Fine Gold 24K",
        "current_market_value": 5600.0,
    }
    specs = parse_precious_metal_specs(asset)
    assert specs["is_precious_metal"] is True
    assert specs["metal"] == "gold"
    assert specs["carat"] == "24K"
    assert specs["purity_factor"] == 1.000
    assert specs["weight_grams"] == 50.0
    assert specs["fine_gold_grams"] == 50.0


def test_parse_precious_metal_specs_22k_sovereign():
    asset = {
        "name": "Sterlina d'Oro Re Carlo III",
        "asset_category": "precious_metals",
        "brand_or_location": "Royal Mint 22K",
        "model_or_specs": "7.98 g 916.7/1000",
        "current_market_value": 800.0,
    }
    specs = parse_precious_metal_specs(asset)
    assert specs["is_precious_metal"] is True
    assert specs["metal"] == "gold"
    assert specs["carat"] == "22K"
    assert specs["purity_factor"] == CARAT_PURITY_MAP["22K"]
    assert specs["weight_grams"] == 7.98


def test_parse_precious_metal_specs_silver():
    asset = {
        "name": "Moneta Argento Filarmonica",
        "asset_category": "precious_metals",
        "brand_or_location": "Argento 999",
        "model_or_specs": "31.1 g",
        "current_market_value": 45.0,
    }
    specs = parse_precious_metal_specs(asset)
    assert specs["is_precious_metal"] is True
    assert specs["metal"] == "silver"
    assert specs["purity_factor"] == 0.999
    assert specs["weight_grams"] == 31.1


def test_parse_non_precious_asset_ignores():
    asset = {
        "name": "Orologio Seiko",
        "asset_category": "luxury_watches",
        "brand_or_location": "Seiko",
        "model_or_specs": "Acciaio Automatico",
        "current_market_value": 100.0,
    }
    specs = parse_precious_metal_specs(asset)
    assert specs["is_precious_metal"] is False
    assert specs["weight_grams"] == 0.0
    assert specs["fine_gold_grams"] == 0.0


def test_get_live_gold_spot_rates():
    rates = get_live_gold_spot_rates()
    assert "gold_eur_per_gram_24k" in rates
    assert "gold_eur_per_gram_18k" in rates
    assert "silver_eur_per_gram" in rates
    assert "eur_usd_rate" in rates

    spot_24k = rates["gold_eur_per_gram_24k"]
    spot_18k = rates["gold_eur_per_gram_18k"]

    assert 20.0 < spot_24k < 300.0
    assert 15.0 < spot_18k < 250.0
    # 18K must be ~75% of 24K spot
    assert abs(spot_18k - (spot_24k * 0.75)) < 0.2


def test_get_gold_historical_series():
    df_hist = get_gold_historical_series(years=5)
    assert isinstance(df_hist, pd.DataFrame)
    assert not df_hist.empty
    assert "eur_g_24k" in df_hist.columns
    assert "eur_g_18k" in df_hist.columns
    assert len(df_hist) >= 200


def test_get_gold_spot_on_date():
    # Historical checks
    spot_2021 = get_gold_spot_on_date("2021-12-31", carat="18K")
    spot_2023 = get_gold_spot_on_date("2023-12-31", carat="18K")
    spot_2024 = get_gold_spot_on_date("2024-12-31", carat="18K")

    assert spot_2021 > 25.0
    assert spot_2023 > spot_2021  # Gold price appreciated
    assert spot_2024 > spot_2023  # Gold rallied in 2024

    # 24K spot should be higher than 18K
    spot_24k_2024 = get_gold_spot_on_date("2024-12-31", carat="24K")
    assert spot_24k_2024 > spot_2024


def test_evaluate_metal_asset_dynamically():
    asset = {
        "name": "Bracciali",
        "asset_category": "precious_metals",
        "brand_or_location": "Oro (18K)",
        "model_or_specs": "15g @ € 88,00",
        "current_market_value": 1320.0,
        "purchase_price": 500.0,
    }
    eval_live = evaluate_metal_asset_dynamically(asset)
    assert eval_live["weight_grams"] == 15.0
    assert eval_live["carat"] == "18K"
    assert eval_live["dynamic_market_value"] > 500.0
    assert eval_live["unrealized_gain"] > 0.0

    # Historical evaluation in 2022
    eval_2022 = evaluate_metal_asset_dynamically(asset, as_of_date="2022-12-31")
    assert eval_2022["spot_price_eur_per_g"] < eval_live["spot_price_eur_per_g"]
    assert eval_2022["dynamic_market_value"] < eval_live["dynamic_market_value"]


def test_compute_gold_portfolio_historical_trajectory():
    df_assets = pd.DataFrame([
        {
            "asset_id": 1,
            "name": "Bracciali",
            "asset_category": "precious_metals",
            "brand_or_location": "Oro (18K)",
            "model_or_specs": "15g @ € 88,00",
            "current_market_value": 1320.0,
            "purchase_price": 0.0,
            "acquisition_date": "2022-01-01",
        },
        {
            "asset_id": 2,
            "name": "Orologio Seiko",
            "asset_category": "luxury_watches",
            "brand_or_location": "Seiko",
            "model_or_specs": "Acciaio",
            "current_market_value": 100.0,
            "purchase_price": 123.75,
            "acquisition_date": "2023-01-01",
        }
    ])

    traj = compute_gold_portfolio_historical_trajectory(df_assets, timeframe_months=24)
    assert not traj.empty
    assert "Total_Gold_Value_EUR" in traj.columns
    assert "Spot_18K_EUR_g" in traj.columns
    # Final value should be close to 15g * current 18K spot
    final_val = float(traj["Total_Gold_Value_EUR"].iloc[-1])
    assert 1000.0 < final_val < 1600.0


def test_bullion_coin_evaluation():
    from core.wealth.gold_engine import BULLION_COIN_CATALOG, evaluate_bullion_coin

    assert "sovereign_full" in BULLION_COIN_CATALOG
    assert "krugerrand_1oz" in BULLION_COIN_CATALOG

    sov = evaluate_bullion_coin("sovereign_full", quantity=2, live_spot_24k_eur_g=100.0)
    assert sov["quantity"] == 2
    assert sov["fine_gold_total_g"] == 7.322 * 2
    # 7.322g * 100 = 732.20€ melt value unit + 3.8% premium = ~760€ unit
    assert sov["market_price_unit_eur"] > 732.20
    assert sov["total_market_price_eur"] == round(sov["market_price_unit_eur"] * 2, 2)


def test_gold_sale_tax_simulator_with_document():
    from core.wealth.gold_engine import compute_gold_sale_tax_impact

    # Acquisto a 2.000€, Vendita a 3.000€ con fattura
    res = compute_gold_sale_tax_impact(sale_price_eur=3000.0, purchase_price_eur=2000.0, has_purchase_document=True)
    assert res["taxable_base_eur"] == 1000.0
    assert res["tax_due_eur"] == 260.0  # 26% di 1.000€
    assert res["net_proceeds_eur"] == 2740.0
    assert res["effective_tax_pct"] == round(260.0 / 3000.0 * 100, 2)


def test_gold_sale_tax_simulator_without_document_2024_reform():
    from core.wealth.gold_engine import compute_gold_sale_tax_impact

    # Vendita a 10.000€ senza documenti (L. Bilancio 2024: 26% su 100% incasso)
    res = compute_gold_sale_tax_impact(sale_price_eur=10000.0, has_purchase_document=False)
    assert res["taxable_base_eur"] == 10000.0
    assert res["tax_due_eur"] == 2600.0  # 26% di 10.000€
    assert res["net_proceeds_eur"] == 7400.0
    assert res["effective_tax_pct"] == 26.0
    assert res["delta_vs_pre_2024_eur"] == 2600.0 - 650.0  # +1.950€ rispetto al vecchio forfettario 25%
