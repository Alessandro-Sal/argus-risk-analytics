# ============================================================
# tests/test_wealth_sync.py
# Unit tests for Wealth Google Sheets synchronization & parsing
# ============================================================

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
import gsheets_sync_subproject.sync_google_sheets
from core.wealth.wealth_sync import (
    sync_expenses_tracker_2026_from_gsheets,
    GSHEET_CATEGORY_MAPPING
)
from core.wealth.wealth_db import (
    init_wealth_db,
    get_wealth_accounts,
    get_cashflow_records,
    get_wealth_categories
)


def test_wealth_gsheet_category_mapping_completeness():
    """Verifica che tutte le categorie target 50/30/20 siano definite con flow_type e nature."""
    from core.wealth.wealth_sync import TARGET_CATEGORIES, classify_category_semantic

    for c_name, c_info in TARGET_CATEGORIES.items():
        assert "flow_type" in c_info
        assert "nature" in c_info
        assert "icon" in c_info
        assert "color" in c_info

    # Test coverage semantica
    raw_cats = ["Salary", "Groceries", "Housing", "Transportation", "Health", "Education", "Dining Out", "Going Out", "Shopping", "Travel", "Subscriptions", "Stocks", "Crypto", "Internal Transfers"]
    for rc in raw_cats:
        mapped = classify_category_semantic(rc)
        assert mapped in TARGET_CATEGORIES



def test_sync_expenses_tracker_2026_mocked():
    """Verifica il parsing e la sincronizzazione di Expenses Tracker con mock dei dati di gspread."""
    mock_rows = [
        ['  ', '', '', '', '', '', '', ''],
        ['2026', 'Current Balance', '', '', ' Intesa San Paolo', ' N26', ' On the go Wallet', ' BuddyBank', 'Revolut', 'Food stamps', 'Controllo Automatismi'],
        ['', '17.165,13', '', '', ' € 15.178,85 ', ' € 403,26 ', ' € 5,20 ', ' € 3,70 ', ' € 1.574,12 ', ' € 228,00 ', ''],
        ['', '', '', '', '', '', '', '', '', '', ''],
        ['', 'Initial/Monthly average', '', '', ' € 21.674,64 ', ' € 1.382,11 ', ' € 133,35 ', ' € 3,70 ', ' € 1.540,62 ', ' € 64,00 ', ''],
        ['1', 'January ', '', '', ' € -1.045,07 ', ' € -844,75 ', ' € 227,35 ', ' € -   ', ' € -319,20 ', ' € -8,00 ', ''],
        ['2026', 'Transactions', 'Category', 'Details', 'Intesa San Paolo', 'N26', 'On the go Wallet', 'BuddyBank', 'Revolut', 'Food stamps', 'Controllo Automatismi'],
        ['04/01/2026', 'Expense', 'Personal Care', 'Apple pay', '', '', '', '', '-€ 2,99', '', ''],
        ['05/01/2026', 'Expense', 'Travel', 'Tirana', '', '-€ 701,66', '-€ 105,00', '', '€ 383,94', '', ''],
        ['05/01/2026', 'Transfer', 'Internal Transfers', 'Sistemazioni', '-€ 2,50', '', '', '', '', '', ''],
        ['10/01/2026', 'Expense', 'Housing', 'Affitto', '-€ 270,00', '', '-€ 180,00', '', '', '', ''],
        ['14/01/2026', 'Income', 'Salary', 'Buoni pasto', '', '', '', '', '', '€ 100,00', ''],
        ['27/01/2026', 'Income', 'Salary', 'Sixtema', '€ 1.480,00', '', '', '', '', '', ''],
        ['29/01/2026', 'Investment', 'Stocks', 'Degiro', '-€ 418,16', '', '', '', '', '', 'ID_1769718158852_26']
    ]

    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()
    mock_worksheet.get_all_values.return_value = mock_rows
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    mock_client.open.return_value = mock_spreadsheet

    engine = create_engine("sqlite:///:memory:")

    with patch("gsheets_sync_subproject.sync_google_sheets.get_gspread_client", return_value=mock_client):
        res = sync_expenses_tracker_2026_from_gsheets(engine, "My All financial Statements", "Expenses Tracker 2026")
        assert res["status"] == "success"
        assert res["accounts_synced"] == 6

        df_acc = get_wealth_accounts(engine)
        assert len(df_acc) == 6
        intesa_row = df_acc[df_acc["name"] == "Intesa San Paolo"].iloc[0]
        assert intesa_row["balance"] == 15178.85
        rev_row = df_acc[df_acc["name"] == "Revolut"].iloc[0]
        assert rev_row["balance"] == 1574.12

        df_tx = get_cashflow_records(engine)
        assert len(df_tx) > 0


def test_classify_category_semantic():
    """Verifica la classificazione semantica delle oltre 300 varianti storiche."""
    from core.wealth.wealth_sync import classify_category_semantic

    assert classify_category_semantic("Stipendio Factory", "Bologna", "Income") == "Stipendio & Compensi"
    assert classify_category_semantic("Borsa di studio", "Unimore", "Income") == "Borse di Studio & Premi"
    assert classify_category_semantic("Zia Rosa", "Regalo compleanno", "Income") == "Supporto Famiglia & Genitori"
    assert classify_category_semantic("Affitto natalizio", "Casa Modena", "Expense") == "Casa, Affitto & Utenze"
    assert classify_category_semantic("Alimentazione", "Supermercato Conad", "Expense") == "Spesa Alimentare & Supermercato"
    assert classify_category_semantic("Trasporti", "Benzina Roma", "Expense") == "Trasporti, Benzina & Mezzi"
    assert classify_category_semantic("Crypto Portfolio", "Binance", "Investment") == "Investimenti Criptovalute"
    assert classify_category_semantic("DEGIRO", "Azioni Googl", "Investment") == "Investimenti Titoli & Azioni"
    assert classify_category_semantic("Free-Time", "Cinema Modena", "Expense") == "Tempo Libero, Cinema & Eventi"


def test_sync_config_fixed_expenses_and_integration():
    """Verifica il parsing e il salvataggio delle spese fisse da Config_FixedExpenses."""
    from sqlalchemy import create_engine
    from core.wealth.wealth_sync import _sync_config_fixed_expenses_sheet
    from core.wealth.wealth_db import get_wealth_fixed_expenses, save_wealth_fixed_expense
    from core.wealth.wealth_engine import compute_recurring_subscriptions_analytics

    engine = create_engine("sqlite:///:memory:")

    class MockFixedExpensesWorksheet:
        def get_all_values(self):
            return [
                ["ID", "Categoria", "Nota", "Importo", "Banca Colonna", "Giorno Pagamento", "Data Inizio", "Data Fine", "Is Split?", "Split Details"],
                ["0", "Housing", "Affitto (Intesa + Wallet)", "€ 450,00", "9", "12", "", "", "TRUE", "5:270,00|7:180,00"],
                ["1", "Subscriptions", "Prime Video", "€ 4,99", "9", "6", "", "", "FALSE", ""],
                ["2", "Subscriptions", "iCloud", "€ 2,99", "9", "4", "", "", "FALSE", ""],
                ["3", "Subscriptions", "Phone Top-up", "€ 9,99", "9", "22", "", "", "FALSE", ""],
                ["4", "Subscriptions", "Spotify", "€ 6,49", "6", "18", "", "", "FALSE", ""],
                ["5", "Education", "Corso Data Analytics", "€ 600,00", "5", "24", "2026-02-24", "2026-07-24", "FALSE", ""],
                ["6", "Education", "Corso Inglese", "€ 169,80", "5", "17", "2026-01-17", "2027-01-17", "FALSE", ""],
                ["7", "Shopping", "Occhiali da Sole - Rayb", "€ 31,30", "6", "9", "2026-06-09", "2026-08-09", "FALSE", ""],
                ["8", "Personal Care", "Parrucchiere", "€ 27,00", "9", "", "", "", "FALSE", ""]
            ]

    class MockSpreadsheet:
        def worksheet(self, title):
            if "fixed" in title.lower():
                return MockFixedExpensesWorksheet()
            raise Exception("Worksheet not found")

    saved_ids = _sync_config_fixed_expenses_sheet(engine, MockSpreadsheet(), portfolio_id=1)
    assert len(saved_ids) == 9

    df_fixed = get_wealth_fixed_expenses(engine, portfolio_id=1)
    assert len(df_fixed) == 9
    assert "Prime Video" in df_fixed["note"].values
    assert "Spotify" in df_fixed["note"].values

    # Test calcolo analytics collegato a engine
    res = compute_recurring_subscriptions_analytics(engine=engine, portfolio_id=1)
    assert res["total_count"] == 9
    assert res["count"] >= 6
    assert res["total_monthly_burn"] > 600.0
    assert "Subscriptions" in res["category_breakdown"]
    assert "Housing" in res["category_breakdown"]
    assert res["opportunity_cost_10y"] > 0
    
    # Verifica che le date e gli stati siano stati calcolati correttamente
    subs_map = {s["merchant"]: s for s in res["subscriptions"]}
    assert "Corso Data Analytics" in subs_map
    assert subs_map["Corso Data Analytics"]["start_date"] == "2026-02-24"
    assert subs_map["Corso Data Analytics"]["end_date"] == "2026-07-24"
    assert "Corso Inglese" in subs_map
    assert subs_map["Corso Inglese"]["end_date"] == "2027-01-17"



