"""
ARGUS — Test Suite: Internationalization (i18n), Localization (L10n) & FX Risk Engine
Verifies translation dictionary lookups, regional number and date formatting,
accounting parentheses notation, ECB reference rates, triangular cross-currency conversion,
and exact mathematical decomposition of foreign exchange risk.
"""

from datetime import date, datetime
import math
import numpy as np
import pandas as pd
import pytest

from core.i18n.translator import I18nEngine, get_i18n, get_locale, set_locale, t
from core.i18n.formatters import (
    format_currency,
    format_date,
    format_number,
    format_percent,
    get_dataframe_styler_formats,
)
from core.i18n.fx_engine import (
    ECBRateProvider,
    FXConversionEngine,
    FXDecompositionResult,
    SUPPORTED_CURRENCIES,
)


# ── 1. TEST TRANSLATOR & LOCALIZATION DICTIONARIES ──────────────────

def test_i18n_translator_keys_and_interpolation():
    engine = I18nEngine.get_instance()
    
    # Verifica dizionario Italiano
    engine.set_locale("it")
    assert engine.get_locale() == "it"
    assert t("common.save") == "Salva"
    assert t("common.cancel") == "Annulla"
    assert t("risk.var_95") == "Value at Risk (VaR 95%)"
    assert t("wealth.net_worth") == "Patrimonio Netto"
    assert t("fx.fx_risk") == "Rischio di Cambio (FX)"

    # Verifica commutazione a caldo in Inglese
    engine.set_locale("en")
    assert engine.get_locale() == "en"
    assert t("common.save") == "Save"
    assert t("common.cancel") == "Cancel"
    assert t("risk.var_95") == "Value at Risk (VaR 95%)"
    assert t("wealth.net_worth") == "Net Worth"
    assert t("fx.fx_risk") == "Foreign Exchange Risk (FX)"

    # Verifica fallback su chiave inesistente
    assert t("non_existent.dummy_key") == "non_existent.dummy_key"
    assert t("non_existent.key_with_default", default="DefaultVal") == "DefaultVal"

    # Ripristina locale italiano
    engine.set_locale("it")


# ── 2. TEST FORMATTAZIONE NUMERI E VALUTE REGIONALI ──────────────────

def test_formatters_currency_locales():
    val = 1234567.89

    # Standard Europeo (Italia)
    formatted_it = format_currency(val, currency="EUR", locale="it", accounting=False)
    assert "1.234.567,89" in formatted_it
    assert "€" in formatted_it
    assert formatted_it.endswith("€")

    # Standard Anglosassone (USA)
    formatted_en = format_currency(val, currency="USD", locale="en", accounting=False)
    assert "1,234,567.89" in formatted_en
    assert formatted_en.startswith("$")

    # Standard Britannico (UK)
    formatted_gb = format_currency(val, currency="GBP", locale="gb", accounting=False)
    assert "1,234,567.89" in formatted_gb
    assert formatted_gb.startswith("£")

    # Standard Svizzero (CHF)
    formatted_ch = format_currency(val, currency="CHF", locale="ch", accounting=False)
    assert "1'234'567.89" in formatted_ch
    assert formatted_ch.startswith("CHF")


# ── 3. TEST NOTAZIONE CONTABILE (PARENTHESES VS MINUS) ───────────────

def test_formatters_accounting_notation():
    neg_val = -1234.56

    # Standard meno
    std_it = format_currency(neg_val, currency="EUR", locale="it", accounting=False)
    assert std_it == "-1.234,56 €"

    std_en = format_currency(neg_val, currency="USD", locale="en", accounting=False)
    assert std_en == "-$1,234.56"

    # Contabile Wall Street (Parentesi)
    acct_it = format_currency(neg_val, currency="EUR", locale="it", accounting=True)
    assert acct_it == "(1.234,56 €)"

    acct_en = format_currency(neg_val, currency="USD", locale="en", accounting=True)
    assert acct_en == "($1,234.56)"

    # Percentuali
    assert format_percent(5.25, locale="it") == "+5,25%"
    assert format_percent(-3.10, locale="it", accounting=False) == "-3,10%"
    assert format_percent(-3.10, locale="it", accounting=True) == "(3,10%)"
    assert format_percent(-0.042, locale="en", accounting=True, is_decimal_fraction=True) == "(4.20%)"


def test_formatters_compact_and_numbers():
    # Numeri compatti
    assert "1,50 Mln €" == format_currency(1_500_000, "EUR", locale="it", compact=True)
    assert "$2.50M" == format_currency(2_500_000, "USD", locale="en", compact=True)
    assert "$1.20B" == format_currency(1_200_000_000, "USD", locale="en", compact=True)

    # Numeri generici
    assert format_number(12345.678, locale="it", decimals=2) == "12.345,68"
    assert format_number(12345.678, locale="en", decimals=2) == "12,345.68"
    assert format_number(-999.5, locale="en", accounting=True) == "(999.50)"

    # Edge cases (NaN, None)
    assert format_currency(None) == "—"
    assert format_percent(float("nan")) == "—"
    assert format_number(float("inf")) == "—"


def test_format_date():
    dt = date(2026, 5, 15)
    assert format_date(dt, locale="it", fmt="short") == "15/05/2026"
    assert format_date(dt, locale="en", fmt="short") == "05/15/2026"
    assert format_date(dt, fmt="iso") == "2026-05-15"
    assert "Mag" in format_date(dt, locale="it", fmt="long")
    assert "May" in format_date(dt, locale="en", fmt="long")


def test_dataframe_styler_generator():
    cols_config = {
        "valore": "currency",
        "variazione": "signed_percent",
        "data": "date"
    }
    stylers = get_dataframe_styler_formats(cols_config, locale="it", base_currency="EUR")
    assert "valore" in stylers and callable(stylers["valore"])
    assert "variazione" in stylers and callable(stylers["variazione"])
    assert "data" in stylers and callable(stylers["data"])

    assert "€" in stylers["valore"](100.5)
    assert "+" in stylers["variazione"](4.2)
    assert "/" in stylers["data"](date(2026, 1, 1))


# ── 4. TEST ECB RATE PROVIDER & CALENDARIO TARGET2 ───────────────────

def test_ecb_rate_provider_and_calendar_ffill():
    provider = ECBRateProvider()
    df_fx = provider.fetch_historical_rates(days_back=90)
    
    assert isinstance(df_fx, pd.DataFrame)
    assert not df_fx.empty
    assert "USDEUR" in df_fx.columns
    assert "GBPEUR" in df_fx.columns

    # Verifica assenza di buchi temporali (forward fill continuo)
    assert df_fx.isna().sum().sum() == 0
    # Verifica che tutti i giorni siano presenti
    date_diffs = (df_fx.index[1:] - df_fx.index[:-1]).days
    assert set(date_diffs).issubset({1})  # Passo esattamente giornaliero


# ── 5. TEST FX CONVERSION ENGINE & ARBITRAGGIO TRIANGOLARE ───────────

def test_fx_conversion_engine_triangular_arbitrage():
    # Creazione serie tassi nota e controllata
    dates = pd.date_range("2025-01-01", "2025-01-10", freq="D")
    df_test_rates = pd.DataFrame({
        "USDEUR": [0.92] * len(dates),   # 1 USD = 0.92 EUR
        "GBPEUR": [1.15] * len(dates),   # 1 GBP = 1.15 EUR
        "CHFEUR": [1.00] * len(dates),   # 1 CHF = 1.00 EUR
    }, index=dates)

    engine = FXConversionEngine(fx_rates_df=df_test_rates)

    # Identità stessa valuta
    assert engine.get_rate("EUR", "EUR") == 1.0
    assert engine.get_rate("USD", "USD") == 1.0

    # Tasso diretto verso EUR
    assert abs(engine.get_rate("USD", "EUR") - 0.92) < 1e-9
    assert abs(engine.get_rate("EUR", "USD") - (1.0 / 0.92)) < 1e-9

    # Arbitraggio triangolare cross-rate: USD -> GBP
    # Rate(USD -> GBP) = Rate(USD -> EUR) / Rate(GBP -> EUR) = 0.92 / 1.15 = 0.8
    rate_usd_gbp = engine.get_rate("USD", "GBP")
    expected_rate = 0.92 / 1.15
    assert abs(rate_usd_gbp - expected_rate) < 1e-9

    # Conversione importi monetari
    amount_gbp = engine.convert_amount(100.0, from_currency="USD", to_currency="GBP")
    assert abs(amount_gbp - 80.0) < 1e-9

    # Riconversione reversibile esatta
    back_to_usd = engine.convert_amount(amount_gbp, from_currency="GBP", to_currency="USD")
    assert abs(back_to_usd - 100.0) < 1e-9


# ── 6. TEST DECOMPOSIZIONE MATEMATICA DEL RISCHIO FX ─────────────────

def test_fx_risk_decomposition_mathematical_identity():
    # Generazione serie prezzi asset in USD e serie cambio USDEUR
    dates = pd.date_range("2024-01-01", "2024-06-30", freq="B")
    n = len(dates)

    np.random.seed(123)
    shocks_asset = np.random.normal(0.0005, 0.015, n)
    shocks_fx = np.random.normal(-0.0002, 0.008, n)

    # Prezzi locali USD
    p_local = 100.0 * np.exp(np.cumsum(shocks_asset))
    # Tassi di cambio USDEUR (quanti EUR per 1 USD)
    s_fx = 0.90 * np.exp(np.cumsum(shocks_fx))

    df_rates = pd.DataFrame({"USDEUR": s_fx}, index=dates)
    s_asset = pd.Series(p_local, index=dates)

    engine = FXConversionEngine(fx_rates_df=df_rates)
    result = engine.decompose_asset_fx_risk(
        local_price_series=s_asset,
        asset_currency="USD",
        base_currency="EUR",
        ticker="TEST_STOCK",
        holding_quantity=10.0
    )

    # 1. Verifica identità fondamentale: 1 + R_base = (1 + R_local) * (1 + R_fx)
    lhs = 1.0 + result.total_return_base
    rhs = (1.0 + result.asset_return_local) * (1.0 + result.fx_return)
    assert abs(lhs - rhs) < 1e-9, f"Identità infranta: LHS={lhs}, RHS={rhs}"

    # 2. Verifica scomposizione additiva con termine di cross-interaction:
    # R_base = R_local + R_fx + (R_local * R_fx)
    sum_terms = result.asset_return_local + result.fx_return + result.cross_interaction
    assert abs(result.total_return_base - sum_terms) < 1e-9

    # 3. Verifica quadratura esatta del PnL monetario in valuta base:
    # Total PnL = Asset PnL + FX PnL + Cross PnL
    sum_pnl = result.holding_asset_pnl + result.holding_fx_pnl + result.holding_cross_pnl
    assert abs(result.holding_pnl_base - sum_pnl) < 1e-7, f"Quadratura PnL fallita: diff={abs(result.holding_pnl_base - sum_pnl)}"

    # 4. Proprietà statistiche coerenti
    assert result.asset_volatility_ann > 0
    assert result.fx_volatility_ann > 0
    assert -1.0 <= result.correlation_asset_fx <= 1.0
    assert 0.0 <= result.fx_risk_share_pct <= 100.0
    assert isinstance(result.is_natural_hedge, bool)
