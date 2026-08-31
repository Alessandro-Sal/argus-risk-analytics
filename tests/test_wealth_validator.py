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


SAMPLE_CASHFLOW_CSV = """Data,Importo,Descrizione,Direzione,Categoria,Conto,Metodo_Pagamento,Note
2026-08-01,2800.00,Stipendio e Compensi Mese,inflow,Stipendio / Compensi,Fineco Conto Principale,Bonifico,Accredito stipendio mensile
2026-08-02,120.50,Spesa Alimentare Esselunga,outflow,Spesa Alimentare & Supermercato,Fineco Conto Principale,Carta,Spesa settimanale
2026-08-03,65.00,Cena Ristorante Da Mario,outflow,"Ristoranti, Bar & Delivery",Revolut Daily & Viaggi,Carta,Cena con amici
"""

SAMPLE_PHYSICAL_ASSETS_CSV = """Nome,Categoria,Brand_Location,Modello_Specifiche,Referenza_Catasto,Prezzo_Acquisto,Valore_Attuale,Data_Acquisto,Condizione_Set,Note
Rolex Submariner Date 41,luxury_watches,Rolex,Submariner Date Ghiera Nera Ceramica,126610LN,10250.00,13800.00,2023-05-15,Full Set 2023 / Mai Indossato,Acquistato presso concessionario ufficiale
Rolex GMT-Master II Batman,luxury_watches,Rolex,GMT-Master II Bracciale Jubilee,126710BLNR,10900.00,16200.00,2022-11-20,Full Set / Ottime Condizioni,Set completo garanzia e scatola
"""

SAMPLE_ACCOUNTS_CSV = """Nome_Conto,Istituto,Tipo_Conto,Saldo,Valuta,IBAN,Note
Fineco Conto Principale,FinecoBank,checking,12500.00,EUR,IT60X0542811101000000123456,Conto principale per stipendio e spese
Illimity Deposito Risparmio,Illimity Bank,savings,20000.00,EUR,IT75Y0306909606100000065432,Conto deposito vincolato 3%
"""

SAMPLE_PENSION_CSV = """Nome_Fondo,Provider,Tipo_Piano,Valore_Accumulato,Versamento_Mensile,Contributo_Datore,Linea_Investimento,Note
Amundi SecondaPensione,Amundi SGR,fondo_pensione_aperto,28500.00,350.00,0.00,Espansione 100% Azionario,Fondo pensione aperto deducibile IRPEF
"""


def test_standard_cashflow_template_validation():
    """Verifica che il template standard di cash flow passi la validazione."""
    csv_path = "data/wealth/template_cashflow_spese.csv"
    if os.path.exists(csv_path):
        df_raw = pd.read_csv(csv_path)
    else:
        df_raw = pd.read_csv(io.StringIO(SAMPLE_CASHFLOW_CSV))
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
    if os.path.exists(csv_path):
        df_raw = pd.read_csv(csv_path)
    else:
        df_raw = pd.read_csv(io.StringIO(SAMPLE_PHYSICAL_ASSETS_CSV))
    is_valid, errors, df_clean = validate_physical_assets_df(df_raw)
    assert is_valid
    assert len(errors) == 0
    assert len(df_clean) == len(df_raw)
    assert "purchase_price" in df_clean.columns
    assert "current_market_value" in df_clean.columns


def test_standard_accounts_template_validation():
    """Verifica che il template standard dei conti bancari sia valido."""
    csv_path = "data/wealth/template_conti_bancari.csv"
    if os.path.exists(csv_path):
        df_raw = pd.read_csv(csv_path)
    else:
        df_raw = pd.read_csv(io.StringIO(SAMPLE_ACCOUNTS_CSV))
    is_valid, errors, df_clean = validate_accounts_df(df_raw)
    assert is_valid
    assert len(errors) == 0
    assert len(df_clean) == len(df_raw)
    assert "balance" in df_clean.columns


def test_standard_pension_template_validation():
    """Verifica che il template standard della previdenza sia valido."""
    csv_path = "data/wealth/template_fondi_pensione.csv"
    if os.path.exists(csv_path):
        df_raw = pd.read_csv(csv_path)
    else:
        df_raw = pd.read_csv(io.StringIO(SAMPLE_PENSION_CSV))
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
