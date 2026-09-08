# ==============================================================================
# core/wealth/universal_bank_parser.py
# ARGUS — Universal Zero-Config Banking & Broker Ingestion Engine
# ==============================================================================

import io
import re
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from core.ingestion_utils import read_tabular_stream


# ── BANCHE & BROKER SIGNATURE DEFINITIONS ──
BANK_SIGNATURES: Dict[str, Dict[str, Any]] = {
    "INTESA_SANPAOLO": {
        "name": "Intesa Sanpaolo",
        "keywords": ["operazione", "valuta", "descrizione", "accrediti", "addebiti", "intesa", "movimenti conto"],
        "date_cols": ["Data", "Data Operazione", "Data Contabile", "Data Valuta"],
        "desc_cols": ["Descrizione", "Descrizione Operazione", "Operazione", "Causale"],
        "amount_cols": ["Importo", "Addebiti/Accrediti", "Importo (EUR)", "Importo(EUR)"],
        "credit_cols": ["Accrediti", "Entrate", "Avere"],
        "debit_cols": ["Addebiti", "Uscite", "Dare"],
    },
    "UNICREDIT": {
        "name": "UniCredit",
        "keywords": ["data registrazione", "data valuta", "descrizione", "importo in euro", "unicredit"],
        "date_cols": ["Data Registrazione", "Data Contabile", "Data", "Data Valuta"],
        "desc_cols": ["Descrizione", "Descrizione Completa", "Causale"],
        "amount_cols": ["Importo in Euro", "Importo", "Importo Euro"],
        "credit_cols": ["Entrate", "Accrediti"],
        "debit_cols": ["Uscite", "Addebiti"],
    },
    "FINECO_BANK": {
        "name": "FinecoBank (Conto Corrente)",
        "keywords": ["data registrazione", "data valuta", "entrate", "uscite", "descrizione completa", "fineco"],
        "date_cols": ["Data Registrazione", "Data", "Data Contabile"],
        "desc_cols": ["Descrizione Completa", "Descrizione", "Causale"],
        "amount_cols": ["Importo"],
        "credit_cols": ["Entrate", "Entrate (Euro)"],
        "debit_cols": ["Uscite", "Uscite (Euro)"],
    },
    "REVOLUT": {
        "name": "Revolut",
        "keywords": ["type", "product", "started date", "completed date", "description", "amount", "fee", "currency", "state"],
        "date_cols": ["Completed Date", "Started Date", "Date", "Data"],
        "desc_cols": ["Description", "Descrizione", "Merchant"],
        "amount_cols": ["Amount", "Importo", "Total Amount"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "BBVA_ITALIA": {
        "name": "BBVA Italia",
        "keywords": ["data operazione", "data valuta", "movimento", "importo", "saldo disponibile", "bbva"],
        "date_cols": ["Data Operazione", "Data Movimento", "Data", "Data Valuta"],
        "desc_cols": ["Movimento", "Descrizione", "Concetto"],
        "amount_cols": ["Importo", "Importo (€)"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "MEDIOLANUM": {
        "name": "Banca Mediolanum",
        "keywords": ["data contabile", "data valuta", "causale", "descrizione", "importo", "mediolanum"],
        "date_cols": ["Data Contabile", "Data Valuta", "Data"],
        "desc_cols": ["Descrizione", "Causale", "Movimento"],
        "amount_cols": ["Importo", "Importo Euro"],
        "credit_cols": ["Accredito"],
        "debit_cols": ["Addebito"],
    },
    "N26": {
        "name": "N26 Bank",
        "keywords": ["date", "payee", "account number", "transaction type", "payment reference", "amount (eur)"],
        "date_cols": ["Date", "Data"],
        "desc_cols": ["Payee", "Payment reference", "Description", "Descrizione"],
        "amount_cols": ["Amount (EUR)", "Amount", "Importo"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "WIDIBA": {
        "name": "Banca Widiba",
        "keywords": ["data", "valuta", "descrizione", "importo", "widiba"],
        "date_cols": ["Data", "Data Operazione", "Data Valuta"],
        "desc_cols": ["Descrizione", "Causale"],
        "amount_cols": ["Importo", "Importo (EUR)"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "WEBANK": {
        "name": "Webank / Banco BPM",
        "keywords": ["data contabile", "data valuta", "descrizione operazione", "importo", "webank"],
        "date_cols": ["Data Contabile", "Data Valuta", "Data"],
        "desc_cols": ["Descrizione Operazione", "Descrizione", "Causale"],
        "amount_cols": ["Importo", "Importo Euro"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "POSTE_ITALIANE": {
        "name": "Poste Italiane (BancoPosta / Postepay)",
        "keywords": ["data contabile", "data valuta", "addebiti (euro)", "accrediti (euro)", "descrizione operazioni", "postepay", "bancoposta"],
        "date_cols": ["Data Contabile", "Data Valuta", "Data Operazione", "Data"],
        "desc_cols": ["Descrizione Operazioni", "Descrizione", "Causale"],
        "amount_cols": ["Importo", "Importo in Euro"],
        "credit_cols": ["Accrediti (Euro)", "Accrediti", "Entrate"],
        "debit_cols": ["Addebiti (Euro)", "Addebiti", "Uscite"],
    },
    "WISE": {
        "name": "Wise (TransferWise)",
        "keywords": ["transferwise id", "source amount (after fees)", "target amount (after fees)", "direction", "created on"],
        "date_cols": ["Created on", "Finished on", "Date"],
        "desc_cols": ["Target name", "Reference", "Source name"],
        "amount_cols": ["Target amount (after fees)", "Amount", "Source amount (after fees)"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "PAYPAL": {
        "name": "PayPal",
        "keywords": ["data", "ora", "fuso orario", "nome", "tipo", "stato", "valuta", "lordo", "tariffa", "netto"],
        "date_cols": ["Data", "Date"],
        "desc_cols": ["Nome", "Tipo", "Descrizione articolo", "Name", "Description"],
        "amount_cols": ["Netto", "Lordo", "Net", "Gross", "Importo"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "DEGIRO": {
        "name": "Degiro Account Statement",
        "keywords": ["data", "ora", "data valuta", "prodotto", "isin", "descrizione", "variazione", "saldo"],
        "date_cols": ["Data", "Date"],
        "desc_cols": ["Descrizione", "Prodotto", "Description"],
        "amount_cols": ["Variazione", "Importo", "Amount"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "INTERACTIVE_BROKERS": {
        "name": "Interactive Brokers (Cash / Activity)",
        "keywords": ["cash report", "deposits & withdrawals", "dividends", "withholding tax", "transaction history", "statement of funds"],
        "date_cols": ["Date", "Settle Date", "Data"],
        "desc_cols": ["Description", "Descrizione", "Activity Description"],
        "amount_cols": ["Amount", "Total", "Net Cash"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "TRADE_REPUBLIC": {
        "name": "Trade Republic (Cash Account)",
        "keywords": ["timestamp", "type", "asset", "amount", "cash", "trade republic"],
        "date_cols": ["Timestamp", "Date", "Data"],
        "desc_cols": ["Type", "Description", "Asset"],
        "amount_cols": ["Amount", "Importo"],
        "credit_cols": [],
        "debit_cols": [],
    },
    "SCALABLE_CAPITAL": {
        "name": "Scalable Capital (Account Statement)",
        "keywords": ["date", "time", "type", "description", "amount", "scalable"],
        "date_cols": ["Date", "Valuta", "Data"],
        "desc_cols": ["Description", "Type", "Text"],
        "amount_cols": ["Amount", "Importo"],
        "credit_cols": [],
        "debit_cols": [],
    }
}


# ── MOTORE DI CATEGORIZZAZIONE AUTOMATICA SEMANTICA ──
CATEGORY_RULES: List[Tuple[str, str, List[str]]] = [
    ("🍽️ Cibo & Spesa Alimentare", "Needs", [
        "conad", "esselunga", "coop", "carrefour", "lidl", "eurospin", "iper", "pam", "penny",
        "tigros", "despar", "alimentar", "supermercat", "grocery", "ristorant", "pizzeri",
        "trattori", "bar ", "cafe", "caffe", "mcdonald", "burger king", "kfc", "sushi", "poke",
        "deliveroo", "just eat", "glovo", "uber eats", "panifici", "macelleri", "pescheri"
    ]),
    ("🏠 Casa, Affitto & Utenze", "Needs", [
        "affitto", "condomini", "enel", "eni ", "plenitude", "a2a", "edison", "servizio elettrico",
        "iren", "sorgenia", "luce", "gas", "acqua", "tari", "imu", "mutuo", "rata mutuo",
        "telecom", "tim ", "vodafone", "windtre", "iliad", "fastweb", "internet", "fibra"
    ]),
    ("🚗 Trasporti & Mobilità", "Needs", [
        "eni station", "q8", "ip ", "tamoil", "esso", "carburant", "benzina", "diesel", "metano",
        "telepass", "autostrade", "trenitalia", "italo", "atm milano", "atac", "metro", "bus",
        "taxi", "uber", "freenow", "parcheggio", "parking", "garage", "bollo auto", "tagliando"
    ]),
    ("💊 Salute, Farmacia & Cure", "Needs", [
        "farmaci", "parafarmaci", "visita medic", "dentist", "odontoiatr", "ospedale", "asl",
        "ticket", "analisi", "laboratorio", "ottic", "occhiali", "sanitari", "medico"
    ]),
    ("🛡️ Assicurazioni & Protezione", "Needs", [
        "assicurazion", "unipolsai", "generali", "allianz", "axa", "prima assicurazioni",
        "zurich", "polizza", "rc auto", "cattolica"
    ]),
    ("✈️ Viaggi, Hotel & Vacanze", "Wants", [
        "ryanair", "easyjet", "wizzair", "lufthansa", "air france", "booking.com", "airbnb",
        "hotel", "resort", "b&b", "expedia", "trivago", "volo", "traghetto", "crociera"
    ]),
    ("🛍️ Shopping, Abbigliamento & Elettronica", "Wants", [
        "amazon", "zara", "h&m", "zalando", "nike", "adidas", "apple", "mediaworld", "unieuro",
        "shein", "asos", "yoox", "ebay", "aliexpress", "abbigliamento", "calzature", "profumeri",
        "sephora", "douglas", "kiko"
    ]),
    ("🎮 Svago, Cinema & Abbonamenti", "Wants", [
        "netflix", "spotify", "amazon prime", "disney", "dazn", "sky", "youtube", "playstation",
        "xbox", "nintendo", "steam", "cinema", "teatro", "concerto", "ticketone", "palestra",
        "gym", "fitness", "padel", "calcetto", "bowling", "club"
    ]),
    ("📈 Investimenti, PAC & Broker", "Savings", [
        "degiro", "directa", "interactive brokers", "scalable", "trade republic", "fineco bank",
        "pac ", "etf", "azioni", "acquisto quote", "reinvest", "crypto", "binance", "coinbase",
        "kraken", "young platform", "anima sgr", "eurizon", "fondi comuni", "moneyfarm", "tinaba"
    ]),
    ("🛡️ Previdenza & Fondo Pensione", "Savings", [
        "fondo pensione", "cometa", "fonte", "fonchim", "perseo", "laborfonds", "secondapensione",
        "allianz insieme", "previdenza integrativa", "pip", "fondopensione", "tfr"
    ]),
    ("💼 Stipendio, Compensi & Entrate", "Income", [
        "stipendio", "emolumenti", "salario", "retribuzione", "cedolino", "bonifico da datore",
        "compenso", "fattura", "onorario", "prestazione", "incasso pos", "dividendo", "cedola",
        "rendita", "pensione inps", "accredito stipendio", "rimborso 730"
    ]),
    ("🔄 Trasferimento / Giroconto", "Transfer", [
        "giroconto", "giroconto da", "giroconto a", "trasferimento tra conti", "bonifico mio conto",
        "ricarica carta", "ricarica prepagata", "alimentazione conto", "me stesso", "auto-bonifico"
    ])
]


def clean_currency_amount(val: Any) -> float:
    """Pulisce e converte qualsiasi valore monetario (stringa o float) in float numerico standard."""
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if not s:
        return 0.0

    is_neg = "-" in s or "CR" in s.upper() or (s.startswith("(") and s.endswith(")"))
    s_clean = re.sub(r"[^\d.,\-+]", "", s)

    if "," in s_clean and "." in s_clean:
        if s_clean.rfind(",") > s_clean.rfind("."):
            s_clean = s_clean.replace(".", "").replace(",", ".")
        else:
            s_clean = s_clean.replace(",", "")
    elif "," in s_clean:
        s_clean = s_clean.replace(",", ".")

    try:
        res = float(s_clean)
        return -abs(res) if is_neg else res
    except Exception:
        return 0.0


def parse_date_universal(val: Any) -> Optional[str]:
    """Interpreta date in molteplici formati italiani e internazionali restituendo stringa YYYY-MM-DD."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.strftime("%Y-%m-%d")

    s = str(val).strip()
    if not s:
        return None

    formats = [
        "%d/%m/%Y", "%d/%m/%y",
        "%d-%m-%Y", "%d-%m-%y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d.%m.%Y", "%d.%m.%y",
        "%d %b %Y", "%d %B %Y",
        "%Y%m%d", "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(s[:19], fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
            
    try:
        dt = pd.to_datetime(s, dayfirst=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def categorize_transaction(description: str, amount: float) -> Tuple[str, str, bool]:
    """
    Categorizza automaticamente una transazione in base al testo descrittivo.
    Restituisce: (category_name, pillar, is_transfer).
    Pillars: 'Needs', 'Wants', 'Savings', 'Income', 'Transfer'.
    """
    d_lower = str(description or "").lower()
    
    if any(k in d_lower for k in ["giroconto", "trasferimento conto", "ricarica prepagata", "alimentazione conto", "giroconto tra conti"]):
        return "🔄 Giroconto Interno", "Transfer", True

    for cat_name, pillar, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in d_lower:
                is_tr = (pillar == "Transfer")
                return cat_name, pillar, is_tr

    if amount > 0:
        return "💼 Altre Entrate / Introiti", "Income", False
    else:
        return "📦 Spese Varie & Generali", "Needs", False


def detect_bank_format(df_sample: pd.DataFrame, file_text: str = "") -> Tuple[str, Dict[str, Any]]:
    """
    Riconosce automaticamente l'istituto bancario o il broker dal contenuto del file.
    Restituisce: (bank_id, config_dict).
    """
    combined_cols = " ".join([str(c).lower() for c in df_sample.columns])
    combined_text = (file_text[:3000].lower() + " " + combined_cols)

    best_bank = "GENERIC_CSV"
    max_matches = 0

    for bank_id, cfg in BANK_SIGNATURES.items():
        matches = sum(1 for kw in cfg["keywords"] if kw in combined_text)
        if matches > max_matches and matches >= 2:
            max_matches = matches
            best_bank = bank_id

    return best_bank, BANK_SIGNATURES.get(best_bank, {
        "name": "Estratto Conto Standard",
        "keywords": [],
        "date_cols": ["Data", "Date", "Data Operazione", "Data Contabile"],
        "desc_cols": ["Descrizione", "Description", "Causale", "Movimento", "Dettagli"],
        "amount_cols": ["Importo", "Amount", "Valore", "Totale"],
        "credit_cols": ["Entrate", "Accrediti", "Credit"],
        "debit_cols": ["Uscite", "Addebiti", "Debit"]
    })


def parse_bank_statement_file(
    file_bytes_or_buffer: Union[bytes, io.BytesIO, str],
    filename: str = "",
    account_name: str = "Conto Corrente"
) -> Dict[str, Any]:
    """
    Ingestion Hub Universale Zero-Config:
    Accetta un file CSV, XLS, XLSX o TSV di qualsiasi banca italiana/europea e restituisce
    un DataFrame pulito e normalizzato pronto per il salvataggio nel database patrimoniale.
    """
    try:
        df_raw = read_tabular_stream(file_bytes_or_buffer, filename=filename)
        if df_raw is None or df_raw.empty:
            return {
                "success": False,
                "error_msg": "File vuoto o formato non leggibile.",
                "df_normalized": pd.DataFrame(),
                "bank_detected": "Sconosciuto"
            }

        # Estrazione testo campione per rilevamento firma bancaria
        cols_text = " ".join([str(c) for c in df_raw.columns])
        sample_vals = " ".join([str(v) for v in df_raw.iloc[:15].values.flatten() if pd.notna(v)])
        raw_text = f"{cols_text} {sample_vals}"
        bank_id, bank_cfg = detect_bank_format(df_raw, raw_text)

        col_date = None
        col_desc = None
        col_amount = None
        col_credit = None
        col_debit = None

        for target in bank_cfg["date_cols"] + ["Data", "Date", "Data Operazione", "Data Valuta", "Data Registrazione", "Data Movimento"]:
            for c in df_raw.columns:
                if target.lower() == c.lower() or target.lower() in c.lower():
                    col_date = c
                    break
            if col_date:
                break

        for target in bank_cfg["desc_cols"] + ["Descrizione", "Description", "Causale", "Movimento", "Dettagli", "Payee", "Nome"]:
            for c in df_raw.columns:
                if target.lower() == c.lower() or target.lower() in c.lower():
                    col_desc = c
                    break
            if col_desc:
                break

        for target in bank_cfg["amount_cols"] + ["Importo", "Amount", "Valore", "Totale", "Netto", "Importo Euro", "Variazione"]:
            for c in df_raw.columns:
                if target.lower() == c.lower() or target.lower() in c.lower():
                    col_amount = c
                    break
            if col_amount:
                break

        if not col_amount:
            for target in bank_cfg.get("credit_cols", []) + ["Entrate", "Accrediti", "Avere", "Credit"]:
                for c in df_raw.columns:
                    if target.lower() == c.lower() or target.lower() in c.lower():
                        col_credit = c
                        break
                if col_credit:
                    break

            for target in bank_cfg.get("debit_cols", []) + ["Uscite", "Addebiti", "Dare", "Debit"]:
                for c in df_raw.columns:
                    if target.lower() == c.lower() or target.lower() in c.lower():
                        col_debit = c
                        break
                if col_debit:
                    break

        normalized_records = []
        tot_in = 0.0
        tot_out = 0.0
        tr_cnt = 0

        for _, row in df_raw.iterrows():
            raw_dt = row.get(col_date) if col_date else None
            clean_dt = parse_date_universal(raw_dt)
            if not clean_dt:
                continue

            raw_desc = str(row.get(col_desc, "Movimento Bancario")).strip()
            if not raw_desc or raw_desc.lower() in ["nan", "none", "null"]:
                raw_desc = "Movimento Senza Descrizione"

            amt = 0.0
            if col_amount:
                amt = clean_currency_amount(row.get(col_amount))
            elif col_credit or col_debit:
                c_val = clean_currency_amount(row.get(col_credit)) if col_credit else 0.0
                d_val = clean_currency_amount(row.get(col_debit)) if col_debit else 0.0
                if c_val != 0:
                    amt = abs(c_val)
                elif d_val != 0:
                    amt = -abs(d_val)

            if amt == 0.0:
                continue

            cat_name, pillar, is_tr = categorize_transaction(raw_desc, amt)
            r_amt = round(abs(amt), 2)
            r_dir = "transfer" if is_tr else ("inflow" if amt > 0 else "outflow")

            if is_tr:
                tr_cnt += 1
            elif amt > 0:
                tot_in += r_amt
            else:
                tot_out += r_amt

            # Calcolo hash deterministico univoco per deduplicazione idempotente
            raw_hash_key = f"{account_name}|{clean_dt}|{r_amt:.2f}|{r_dir}|{raw_desc.strip().lower()}"
            rec_hash = hashlib.sha256(raw_hash_key.encode("utf-8")).hexdigest()

            normalized_records.append({
                "date": clean_dt,
                "tx_date": clean_dt,
                "description": raw_desc,
                "merchant": raw_desc[:120],
                "amount": r_amt,
                "direction": r_dir,
                "category": cat_name,
                "pillar": pillar,
                "is_transfer": 1 if is_tr else 0,
                "account_name": account_name,
                "currency": "EUR",
                "notes": f"{bank_cfg.get('name', 'Banca')}: {raw_desc[:150]}",
                "payment_method": "Estratto Conto Bancario",
                "tx_hash": rec_hash
            })

        df_norm = pd.DataFrame(normalized_records)
        if df_norm.empty:
            return {
                "success": False,
                "error_msg": "Nessuna transazione valida estratta dal file.",
                "df_normalized": pd.DataFrame(),
                "bank_detected": bank_cfg.get("name", "Sconosciuto")
            }

        df_norm = df_norm.reset_index(drop=True)

        return {
            "success": True,
            "bank_detected": bank_cfg.get("name", "Estratto Conto"),
            "df_normalized": df_norm,
            "total_inflow": round(tot_in, 2),
            "total_outflow": round(tot_out, 2),
            "transfers_count": tr_cnt,
            "rows_count": len(df_norm),
            "error_msg": ""
        }

    except Exception as e:
        return {
            "success": False,
            "error_msg": f"Errore durante l'elaborazione del file: {str(e)}",
            "df_normalized": pd.DataFrame(),
            "bank_detected": "Errore"
        }


def reconcile_internal_transfers(df_tx: pd.DataFrame, max_days_diff: int = 2) -> Tuple[pd.DataFrame, int]:
    """
    Riconciliazione automatica giroconti interni a 2 vie tra conti correnti diversi.
    Identifica movimenti speculari (|importo_A| == |importo_B|, direzioni opposte, |data_A - data_B| <= max_days_diff)
    e li marca come giroconti per neutralizzare il doppio conteggio nel budget 50/30/20.
    """
    if df_tx is None or df_tx.empty or len(df_tx) < 2:
        return df_tx, 0

    df = df_tx.copy()
    acc_col = "account_name" if "account_name" in df.columns else ("account_id" if "account_id" in df.columns else None)
    if not acc_col:
        return df, 0

    date_col = "tx_date" if "tx_date" in df.columns else "date"
    amt_col = "amount"
    dir_col = "direction"

    # Conversione date per calcolo differenze temporali
    dt_series = pd.to_datetime(df[date_col], errors="coerce")
    matched_indices = set()
    pairs_found = 0

    for i in range(len(df)):
        if i in matched_indices:
            continue

        row_a = df.iloc[i]
        dt_a = dt_series.iloc[i]
        if pd.isna(dt_a):
            continue

        amt_a = abs(float(row_a[amt_col]))
        dir_a = str(row_a.get(dir_col, "")).lower()
        acc_a = str(row_a[acc_col])

        # Cerca un movimento speculare nei record successivi
        for j in range(i + 1, len(df)):
            if j in matched_indices:
                continue

            row_b = df.iloc[j]
            acc_b = str(row_b[acc_col])
            if acc_a == acc_b:
                continue  # Stesso conto, non è un giroconto tra conti diversi

            dt_b = dt_series.iloc[j]
            if pd.isna(dt_b):
                continue

            if abs((dt_a - dt_b).days) > max_days_diff:
                continue

            amt_b = abs(float(row_b[amt_col]))
            if round(amt_a, 2) != round(amt_b, 2):
                continue

            dir_b = str(row_b.get(dir_col, "")).lower()
            # Devono avere direzioni opposte (uno entrata/inflow, l'altro uscita/outflow)
            is_opposite = (
                (dir_a in ["inflow", "entrate"] and dir_b in ["outflow", "uscite"]) or
                (dir_a in ["outflow", "uscite"] and dir_b in ["inflow", "entrate"])
            )

            if is_opposite:
                matched_indices.add(i)
                matched_indices.add(j)
                pairs_found += 1
                break

    if matched_indices:
        df.loc[list(matched_indices), "is_transfer"] = 1
        df.loc[list(matched_indices), "direction"] = "transfer"
        df.loc[list(matched_indices), "pillar"] = "Transfer"
        df.loc[list(matched_indices), "category"] = "🔄 Giroconto Interno"

    return df, pairs_found

