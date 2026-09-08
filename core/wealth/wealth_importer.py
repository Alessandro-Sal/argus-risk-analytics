# ============================================================
# core/wealth/wealth_importer.py
# ARGUS — Universal Wealth & Cash Flow Statement Importer
# Auto-detects CSV/Excel bank exports and categorizes transactions
# ============================================================

import io
import re
import pandas as pd
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import Engine

from core.wealth.wealth_db import get_wealth_categories, insert_cashflow_tx, bulk_insert_cashflow_tx
from core.wealth.universal_bank_parser import parse_bank_statement_file


# Regole di auto-categorizzazione basate su parole chiave
CATEGORY_KEYWORD_RULES: Dict[str, List[str]] = {
    "Spesa Alimentare & Supermercato": [
        "esselunga", "conad", "coop", "carrefour", "lidl", "eurospin", "pam", "penny",
        "supermercato", "alimentari", "panificio", "macelleria", "ipercoop", "despar"
    ],
    "Ristoranti, Bar & Delivery": [
        "ristorante", "trattoria", "pizzeria", "bar", "caffe", "mcdonald", "burger king",
        "deliveroo", "just eat", "glovo", "uber eats", "osterie", "pub", "gelateria", "sushi"
    ],
    "Bollette & Utenze (Luce/Gas/Internet)": [
        "enel", "eni", "a2a", "edison", "plenitude", "sorgenia", "telecom", "tim", "vodafone",
        "iliad", "fastweb", "windtre", "servizio idrico", "tari", "utenza", "luce gas"
    ],
    "Trasporti, Carburante & Mezzi": [
        "q8", "eni station", "ip", "tamoil", "esso", "distributore", "telepass", "autostrade",
        "trenitalia", "italo", "atm", "atac", "uber", "taxi", "parcheggio", "easy park"
    ],
    "Abbonamenti, Tech & Streaming": [
        "netflix", "spotify", "amazon prime", "disney", "youtube", "apple", "google",
        "icloud", "chatgpt", "openai", "github", "playstation", "xbox", "dazn", "sky"
    ],
    "Salute, Farmaci & Visite": [
        "farmacia", "parafarmacia", "medico", "visita medica", "dentista", "clinica",
        "ospedale", "laboratorio analisi", "ottico", "synlab"
    ],
    "Shopping & Abbigliamento": [
        "zara", "h&m", "nike", "adidas", "amazon", "zalando", "decathlon", "uniqlo",
        "intimissimi", "calzedonia", "negozio", "boutique", "mediaworld", "unieuro"
    ],
    "Stipendio / Compensi": [
        "stipendio", "emolumenti", "salario", "retribuzione", "bonifico da datore",
        "accredito stipendio", "compenso", "fattura n"
    ],
    "PAC / Investimenti Titoli": [
        "directa", "degiro", "scalable", "trade republic", "interactive brokers",
        "acquisto quote", "pac fondo", "investimento", "binance deposit"
    ]
}


def parse_universal_statement(
    file_bytes_or_buffer: Any,
    filename: str = "statement.csv"
) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    Riconosce ed estrae le transazioni da file CSV o Excel di qualunque banca italiana o estera
    sfruttando il motore unificato universale con calcolo di hash univoco deterministico.
    """
    try:
        res = parse_bank_statement_file(file_bytes_or_buffer, filename=filename)
        if res.get("success") and not res.get("df_normalized", pd.DataFrame()).empty:
            df_norm = res["df_normalized"]
            return df_norm, []
        err_msg = res.get("error_msg", "Nessuna transazione valida estratta dal file.")
        return None, [err_msg]
    except Exception as e:
        return None, [f"Errore durante l'analisi dell'estratto conto: {str(e)}"]


def auto_categorize_transactions(df_tx: pd.DataFrame, engine: Engine) -> pd.DataFrame:
    """Assegna automaticamente la categoria a ciascuna transazione in base al merchant/descrizione."""
    df_cat = get_wealth_categories(engine)
    cat_map = {row["name"]: row["category_id"] for _, row in df_cat.iterrows()}
    
    # Categorie di default
    default_expense_cat_id = cat_map.get("Casa & Mutuo / Affitto", 6)
    default_income_cat_id = cat_map.get("Stipendio / Compensi", 1)

    assigned_cats = []
    for _, row in df_tx.iterrows():
        # 1. Se già categorizzato dal parser universale
        existing_cat = str(row.get("category", "")).strip().lower()
        matched = False
        if existing_cat:
            for c_name, c_id in cat_map.items():
                if c_name.lower() in existing_cat or existing_cat in c_name.lower():
                    assigned_cats.append(c_id)
                    matched = True
                    break

        if not matched:
            desc = str(row.get("merchant", "") or row.get("description", "")).lower()
            for cat_name, keywords in CATEGORY_KEYWORD_RULES.items():
                if any(kw in desc for kw in keywords):
                    if cat_name in cat_map:
                        assigned_cats.append(cat_map[cat_name])
                        matched = True
                        break
        
        if not matched:
            if row.get("direction") == "inflow":
                assigned_cats.append(default_income_cat_id)
            else:
                assigned_cats.append(default_expense_cat_id)

    df_res = df_tx.copy()
    df_res["category_id"] = assigned_cats
    return df_res


def bulk_import_statement(
    engine: Engine,
    account_id: int,
    df_categorized: pd.DataFrame,
    portfolio_id: int = 1
) -> int:
    """Scrive le transazioni categorizzate nel database di Wealth Management con deduplicazione idempotente."""
    if df_categorized is None or df_categorized.empty:
        return 0

    records = []
    for _, row in df_categorized.iterrows():
        t_date = row.get("tx_date") or row.get("date")
        tx_dict = {
            "portfolio_id": portfolio_id,
            "account_id": account_id,
            "category_id": int(row.get("category_id", 1)),
            "tx_date": str(t_date),
            "amount": float(row["amount"]),
            "currency": str(row.get("currency", "EUR")),
            "direction": str(row.get("direction", "outflow")),
            "merchant": row.get("merchant") or row.get("description", ""),
            "notes": row.get("notes") or row.get("description", ""),
            "payment_method": row.get("payment_method", "Importazione CSV"),
            "is_recurring": False,
            "tags": "import_csv",
            "tx_hash": row.get("tx_hash"),
        }
        records.append(tx_dict)

    inserted_count, _ = bulk_insert_cashflow_tx(engine, records, deduplicate=True)
    return inserted_count

