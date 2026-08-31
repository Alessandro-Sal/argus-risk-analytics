# ============================================================
# tests/test_wealth_validator.py
# Unit tests for Wealth CSV validation & standardization
# ============================================================

import os
import io
import pytest
import pandas as pd
from core.wealth.wealth_validator import (
    validate_cashflow_df,
    validate_physical_assets_df,
    validate_accounts_df,
    validate_pension_df
)


def test_standard_cashflow_template_validation():
    """Verifica che il template standard di cash flow passi la validazione."""
    csv_path = "data/wealth/template_cashflow_spese.csv"
    assert os.path.exists(csv_path)
    df_raw = pd.read_csv(csv_path)
    is_valid, errors, df_clean = validate_cashflow_df(df_raw)
    assert is_valid
    assert len(errors) == 0
    assert len(df_clean) == len(df_raw)
    assert "tx_date" in df_clean.columns
    assert "amount" in df_clean.columns
    assert "direction" in df_clean.columns


def test_standard_physical_assets_template_validation():
    """Verifica che il template standard degli orologi & asset fisici sia valido."""
    csv_path = "data/wealth/template_orologi_asset_fisici.csv"
    assert os.path.exists(csv_path)
    df_raw = pd.read_csv(csv_path)
    is_valid, errors, df_clean = validate_physical_assets_df(df_raw)
    assert is_valid
    assert len(errors) == 0
    assert len(df_clean) == len(df_raw)
    assert "purchase_price" in df_clean.columns
    assert "current_market_value" in df_clean.columns


def test_standard_accounts_template_validation():
    """Verifica che il template standard dei conti bancari sia valido."""
    csv_path = "data/wealth/template_conti_bancari.csv"
    assert os.path.exists(csv_path)
    df_raw = pd.read_csv(csv_path)
    is_valid, errors, df_clean = validate_accounts_df(df_raw)
    assert is_valid
    assert len(errors) == 0
    assert len(df_clean) == len(df_raw)
    assert "balance" in df_clean.columns


def test_standard_pension_template_validation():
    """Verifica che il template standard della previdenza sia valido."""
    csv_path = "data/wealth/template_fondi_pensione.csv"
    assert os.path.exists(csv_path)
    df_raw = pd.read_csv(csv_path)
    is_valid, errors, df_clean = validate_pension_df(df_raw)
    assert is_valid
    assert len(errors) == 0
    assert len(df_clean) == len(df_raw)
    assert "accumulated_value" in df_clean.columns


def test_fuzzy_header_and_italian_format_parsing():
    """Verifica il parsing fuzzy con formati italiani (virgole e simboli €)."""
    raw_csv = """Data Operazione;Importo EUR;Descrizione Operazione;Tipo
01/08/2026;€ 2.500,50;Accredito Emolumenti;Inflow
02/08/2026;-120,30;Supermercato Conad;Outflow
03/08/2026;-45,00;Ristorante Il Cavallino;Outflow
"""
    df_raw = pd.read_csv(io.StringIO(raw_csv), sep=";")
    is_valid, errors, df_clean = validate_cashflow_df(df_raw)
    assert is_valid
    assert len(df_clean) == 3
    assert df_clean.iloc[0]["amount"] == 2500.50
    assert df_clean.iloc[0]["direction"] == "inflow"
    assert df_clean.iloc[1]["amount"] == 120.30
    assert df_clean.iloc[1]["direction"] == "outflow"


def test_validation_errors_reporting():
    """Verifica la corretta segnalazione di errori su righe incomplete o non valide."""
    raw_csv = """Data,Importo,Descrizione
2026-08-01,150.00,Spesa Valida
DATA_NON_VALIDA,100.00,Spesa Data Errata
2026-08-03,IMPORTO_NON_VALIDO,Spesa Importo Errato
"""
    df_raw = pd.read_csv(io.StringIO(raw_csv))
    is_valid, errors, df_clean = validate_cashflow_df(df_raw)
    assert not is_valid
    assert len(errors) == 2
    assert len(df_clean) == 1 # Recupera la riga valida
