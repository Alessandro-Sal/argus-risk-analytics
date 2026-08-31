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

from core.wealth.wealth_db import get_wealth_categories, insert_cashflow_tx


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
    Riconosce ed estrae le transazioni da file CSV o Excel di qualunque banca italiana o estera:
    (Data, Importo, Descrizione/Merchant, Direzione).
    """
    errors: List[str] = []
    df_raw = None

    try:
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            df_raw = pd.read_excel(file_bytes_or_buffer)
        else:
            # Prova separatori comuni (, o ;)
            try:
                df_raw = pd.read_csv(file_bytes_or_buffer, sep=";", encoding="utf-8")
            except Exception:
                if hasattr(file_bytes_or_buffer, "seek"):
                    file_bytes_or_buffer.seek(0)
                df_raw = pd.read_csv(file_bytes_or_buffer, sep=",", encoding="utf-8")
    except Exception as e:
        return None, [f"Errore lettura file: {str(e)}"]

    if df_raw is None or df_raw.empty:
        return None, ["File vuoto o non valido."]

    # Normalizza i nomi delle colonne
    col_map = {str(c).strip().lower(): c for c in df_raw.columns}
    
    # 1. Identifica colonna Data
    date_col = None
    for cand in ["data", "date", "data operazione", "data valuta", "transaction date", "booking date"]:
        if cand in col_map:
            date_col = col_map[cand]
            break

    # 2. Identifica colonna Importo
    amount_col = None
    for cand in ["importo", "amount", "importo (eur)", "totale", "valore", "entrate/uscite"]:
        if cand in col_map:
            amount_col = col_map[cand]
            break

    # 3. Identifica colonna Descrizione / Merchant
    desc_col = None
    for cand in ["descrizione", "description", "causale", "dettagli", "merchant", "beneficiario", "ordinante"]:
        if cand in col_map:
            desc_col = col_map[cand]
            break

    if not date_col or not amount_col:
        return None, [f"Colonne obbligatorie non rilevate. Trovate: {list(df_raw.columns)}"]

    records = []
    for _, row in df_raw.iterrows():
        raw_date = row[date_col]
        raw_amt = row[amount_col]
        raw_desc = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else "Spesa generica"

        if pd.isna(raw_date) or pd.isna(raw_amt):
            continue

        # Parsing data
        try:
            parsed_date = pd.to_datetime(raw_date, dayfirst=True).date()
        except Exception:
            continue

        # Parsing importo numerico (gestisce virgole italiane e simboli €)
        if isinstance(raw_amt, str):
            amt_clean = raw_amt.replace("€", "").replace(".", "").replace(",", ".").strip()
            try:
                amt_float = float(amt_clean)
            except ValueError:
                continue
        else:
            amt_float = float(raw_amt)

        direction = "inflow" if amt_float > 0 else "outflow"
        abs_amount = abs(amt_float)

        records.append({
            "tx_date": parsed_date,
            "amount": abs_amount,
            "direction": direction,
            "merchant": raw_desc[:120],
            "notes": raw_desc[:250],
            "payment_method": "Estratto Conto Bancario"
        })

    if not records:
        return None, ["Nessuna transazione valida estratta."]

    df_clean = pd.DataFrame(records)
    return df_clean, []


def auto_categorize_transactions(df_tx: pd.DataFrame, engine: Engine) -> pd.DataFrame:
    """Assegna automaticamente la categoria a ciascuna transazione in base al merchant/descrizione."""
    df_cat = get_wealth_categories(engine)
    cat_map = {row["name"]: row["category_id"] for _, row in df_cat.iterrows()}
    
    # Categorie di default
    default_expense_cat_id = cat_map.get("Casa & Mutuo / Affitto", 6)
    default_income_cat_id = cat_map.get("Stipendio / Compensi", 1)

    assigned_cats = []
    for _, row in df_tx.iterrows():
        desc = str(row.get("merchant", "")).lower()
        matched = False
        
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
    """Scrive le transazioni categorizzate nel database di Wealth Management."""
    imported_count = 0
    for _, row in df_categorized.iterrows():
        tx_dict = {
            "portfolio_id": portfolio_id,
            "account_id": account_id,
            "category_id": int(row["category_id"]),
            "tx_date": row["tx_date"],
            "amount": float(row["amount"]),
            "currency": "EUR",
            "direction": row["direction"],
            "merchant": row.get("merchant"),
            "notes": row.get("notes"),
            "payment_method": row.get("payment_method", "Importazione CSV"),
            "is_recurring": False,
            "tags": "import_csv"
        }
        insert_cashflow_tx(engine, tx_dict)
        imported_count += 1

    return imported_count

