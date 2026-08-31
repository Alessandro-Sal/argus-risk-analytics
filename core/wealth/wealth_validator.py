# ============================================================
# core/wealth/wealth_validator.py
# ARGUS — Wealth CSV & Data Ingestion Validator
# Formal schema verification, fuzzy header mapping & sanity checks
# ============================================================

import re
import pandas as pd
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple, Union

# Mappatura fuzzy degli alias di colonna per il Cash Flow
CASHFLOW_COLUMN_ALIASES = {
    "Data": ["data", "date", "data operazione", "data valuta", "transaction date", "booking date", "tx_date"],
    "Importo": ["importo", "amount", "importo (eur)", "totale", "valore", "entrate/uscite", "importo eur"],
    "Descrizione": ["descrizione", "description", "causale", "dettagli", "merchant", "beneficiario", "ordinante", "descrizione operazione"],
    "Direzione": ["direzione", "direction", "tipo", "tipo operazione", "flow_type", "segno"],
    "Categoria": ["categoria", "category", "categoria spesa", "category_name", "macro_categoria"],
    "Conto": ["conto", "account", "nome conto", "account_name", "banca", "istituto"],
    "Metodo_Pagamento": ["metodo", "metodo_pagamento", "payment_method", "tipo pagamento", "canale"],
    "Note": ["note", "notes", "dettagli extra", "commenti", "tag", "tags"]
}

PHYSICAL_ASSETS_ALIASES = {
    "Nome": ["nome", "name", "asset_name", "titolo", "descrizione"],
    "Categoria": ["categoria", "category", "asset_category", "tipo"],
    "Brand_Location": ["brand", "maison", "marca", "localita", "location", "brand_location", "citta"],
    "Modello_Specifiche": ["modello", "model", "specifiche", "specs", "modello_specifiche"],
    "Referenza_Catasto": ["referenza", "reference", "ref", "catasto", "foglio_mappale", "reference_number"],
    "Prezzo_Acquisto": ["prezzo_acquisto", "purchase_price", "costo", "prezzo d'acquisto", "costo acquisto", "prezzo"],
    "Valore_Attuale": ["valore_attuale", "current_value", "valutazione", "current_market_value", "valore stimato", "prezzo mercato"],
    "Data_Acquisto": ["data_acquisto", "acquisition_date", "data", "date"],
    "Condizione_Set": ["condizione", "condition", "set", "condizione_set", "grade"],
    "Note": ["note", "notes", "commenti"]
}

ACCOUNTS_ALIASES = {
    "Nome_Conto": ["nome_conto", "nome conto", "name", "account_name", "conto"],
    "Istituto": ["istituto", "banca", "institution", "bank"],
    "Tipo_Conto": ["tipo_conto", "tipo conto", "account_type", "tipo"],
    "Saldo": ["saldo", "balance", "saldo attuale", "importo", "valore"],
    "Valuta": ["valuta", "currency", "curr"],
    "IBAN": ["iban", "conto_iban", "coordinate"],
    "Note": ["note", "notes"]
}

PENSION_ALIASES = {
    "Nome_Fondo": ["nome_fondo", "nome fondo", "plan_name", "fondo", "nome"],
    "Provider": ["provider", "societa", "sgr", "banca", "compagnia"],
    "Tipo_Piano": ["tipo_piano", "tipo", "plan_type", "tipologia"],
    "Valore_Accumulato": ["valore_accumulato", "accumulated_value", "montante", "capitale", "saldo"],
    "Versamento_Mensile": ["versamento_mensile", "monthly_employee_contrib", "contributo", "versamento lavoratore"],
    "Contributo_Datore": ["contributo_datore", "monthly_employer_contrib", "quota datore"],
    "Linea_Investimento": ["linea_investimento", "linea", "comparto", "investment_line"],
    "Note": ["note", "notes"]
}


def _match_column_aliases(df: pd.DataFrame, alias_dict: Dict[str, List[str]]) -> Dict[str, str]:
    """Mappa le colonne del DataFrame ai nomi canonici dello schema standard."""
    col_map = {}
    df_cols_lower = {str(c).strip().lower(): c for c in df.columns}
    
    for canonical, aliases in alias_dict.items():
        # Match esatto prima
        if canonical.lower() in df_cols_lower:
            col_map[canonical] = df_cols_lower[canonical.lower()]
            continue
        # Match alias
        for alias in aliases:
            if alias.lower() in df_cols_lower:
                col_map[canonical] = df_cols_lower[alias.lower()]
                break
    return col_map


def _clean_amount(val: Any) -> Optional[float]:
    """Pulisce e converte una stringa o numero in float gestendo valute e virgole."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    
    s = str(val).strip().replace("€", "").replace("$", "").replace("£", "").replace(" ", "")
    # Se contiene sia punto che virgola (es. 1.250,50 o 1,250.50)
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    
    try:
        return float(s)
    except ValueError:
        return None


def _clean_date(val: Any) -> Optional[date]:
    """Converte un valore in oggetto date standard."""
    if pd.isna(val):
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    val_str = str(val).strip()
    if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", val_str):
        try:
            return pd.to_datetime(val_str, dayfirst=False).date()
        except Exception:
            pass
    try:
        dt = pd.to_datetime(val_str, dayfirst=True)
        return dt.date()
    except Exception:
        return None



def validate_cashflow_df(df_raw: pd.DataFrame) -> Tuple[bool, List[str], pd.DataFrame]:
    """
    Valida e normalizza un DataFrame di Cash Flow / Estratto Conto.
    Ritorna: (is_valid, errors_list, df_clean).
    """
    errors: List[str] = []
    if df_raw is None or df_raw.empty:
        return False, ["Il file o DataFrame è completamente vuoto."], pd.DataFrame()

    matched = _match_column_aliases(df_raw, CASHFLOW_COLUMN_ALIASES)
    
    # Campi obbligatori
    if "Data" not in matched:
        errors.append("Colonna obbligatoria 'Data' non trovata.")
    if "Importo" not in matched:
        errors.append("Colonna obbligatoria 'Importo' non trovata.")
    if "Descrizione" not in matched:
        errors.append("Colonna obbligatoria 'Descrizione' (o Beneficiario/Merchant) non trovata.")

    if errors:
        return False, errors, pd.DataFrame()

    records = []
    for idx, row in df_raw.iterrows():
        r_num = idx + 1
        raw_d = row[matched["Data"]]
        raw_amt = row[matched["Importo"]]
        raw_desc = str(row[matched["Descrizione"]]) if pd.notna(row[matched["Descrizione"]]) else "Spesa generica"

        p_date = _clean_date(raw_d)
        if not p_date:
            errors.append(f"Riga {r_num}: Data '{raw_d}' non valida.")
            continue

        p_amt = _clean_amount(raw_amt)
        if p_amt is None:
            errors.append(f"Riga {r_num}: Importo '{raw_amt}' non numerico.")
            continue

        # Direzione: se esplicita usa quella, altrimenti deduce dal segno
        if "Direzione" in matched and pd.notna(row[matched["Direzione"]]):
            dir_raw = str(row[matched["Direzione"]]).strip().lower()
            direction = "inflow" if ("in" in dir_raw or "entr" in dir_raw or "accred" in dir_raw or "+" in dir_raw) else "outflow"
        else:
            direction = "inflow" if p_amt > 0 else "outflow"

        abs_amount = abs(p_amt)
        if abs_amount == 0.0:
            continue

        cat_val = str(row[matched["Categoria"]]) if "Categoria" in matched and pd.notna(row[matched["Categoria"]]) else None
        acc_val = str(row[matched["Conto"]]) if "Conto" in matched and pd.notna(row[matched["Conto"]]) else None
        pay_val = str(row[matched["Metodo_Pagamento"]]) if "Metodo_Pagamento" in matched and pd.notna(row[matched["Metodo_Pagamento"]]) else "Carta / Bonifico"
        note_val = str(row[matched["Note"]]) if "Note" in matched and pd.notna(row[matched["Note"]]) else raw_desc

        records.append({
            "tx_date": p_date,
            "amount": abs_amount,
            "direction": direction,
            "merchant": raw_desc[:120],
            "category_name": cat_val,
            "account_name": acc_val,
            "payment_method": pay_val,
            "notes": note_val
        })

    if not records:
        return False, ["Nessuna transazione valida estratta dopo la pulizia."] + errors, pd.DataFrame()

    df_clean = pd.DataFrame(records)
    is_valid = len(errors) == 0
    return is_valid, errors, df_clean


def validate_physical_assets_df(df_raw: pd.DataFrame) -> Tuple[bool, List[str], pd.DataFrame]:
    """Valida e normalizza il DataFrame degli Asset Fisici (Orologi, Immobili, Metalli)."""
    errors: List[str] = []
    if df_raw is None or df_raw.empty:
        return False, ["Il file è vuoto."], pd.DataFrame()

    matched = _match_column_aliases(df_raw, PHYSICAL_ASSETS_ALIASES)
    if "Nome" not in matched:
        errors.append("Colonna obbligatoria 'Nome' non trovata.")
    if "Prezzo_Acquisto" not in matched:
        errors.append("Colonna obbligatoria 'Prezzo_Acquisto' non trovata.")
    if "Valore_Attuale" not in matched:
        errors.append("Colonna obbligatoria 'Valore_Attuale' non trovata.")

    if errors:
        return False, errors, pd.DataFrame()

    records = []
    for idx, row in df_raw.iterrows():
        r_num = idx + 1
        name = str(row[matched["Nome"]]).strip()
        cost = _clean_amount(row[matched["Prezzo_Acquisto"]])
        val = _clean_amount(row[matched["Valore_Attuale"]])

        if not name:
            errors.append(f"Riga {r_num}: Nome asset vuoto.")
            continue
        if cost is None or cost < 0:
            errors.append(f"Riga {r_num}: Prezzo d'acquisto non valido per '{name}'.")
            continue
        if val is None or val < 0:
            errors.append(f"Riga {r_num}: Valore attuale non valido per '{name}'.")
            continue

        cat = str(row[matched["Categoria"]]).strip().lower() if "Categoria" in matched and pd.notna(row[matched["Categoria"]]) else "luxury_watches"
        brand = str(row[matched["Brand_Location"]]) if "Brand_Location" in matched and pd.notna(row[matched["Brand_Location"]]) else None
        specs = str(row[matched["Modello_Specifiche"]]) if "Modello_Specifiche" in matched and pd.notna(row[matched["Modello_Specifiche"]]) else None
        ref = str(row[matched["Referenza_Catasto"]]) if "Referenza_Catasto" in matched and pd.notna(row[matched["Referenza_Catasto"]]) else None
        cond = str(row[matched["Condizione_Set"]]) if "Condizione_Set" in matched and pd.notna(row[matched["Condizione_Set"]]) else "Full Set"
        acq_d = _clean_date(row[matched["Data_Acquisto"]]) if "Data_Acquisto" in matched and pd.notna(row[matched["Data_Acquisto"]]) else None
        notes = str(row[matched["Note"]]) if "Note" in matched and pd.notna(row[matched["Note"]]) else None

        records.append({
            "name": name,
            "asset_category": cat,
            "brand_or_location": brand,
            "model_or_specs": specs,
            "reference_number": ref,
            "condition_grade": cond,
            "purchase_price": cost,
            "current_market_value": val,
            "acquisition_date": acq_d,
            "notes": notes
        })

    df_clean = pd.DataFrame(records)
    return (len(errors) == 0), errors, df_clean


def validate_accounts_df(df_raw: pd.DataFrame) -> Tuple[bool, List[str], pd.DataFrame]:
    """Valida e normalizza il DataFrame dei Conti Bancari e Liquidità."""
    errors: List[str] = []
    if df_raw is None or df_raw.empty:
        return False, ["Il file è vuoto."], pd.DataFrame()

    matched = _match_column_aliases(df_raw, ACCOUNTS_ALIASES)
    if "Nome_Conto" not in matched:
        errors.append("Colonna obbligatoria 'Nome_Conto' non trovata.")
    if "Saldo" not in matched:
        errors.append("Colonna obbligatoria 'Saldo' non trovata.")

    if errors:
        return False, errors, pd.DataFrame()

    records = []
    for idx, row in df_raw.iterrows():
        r_num = idx + 1
        name = str(row[matched["Nome_Conto"]]).strip()
        bal = _clean_amount(row[matched["Saldo"]])

        if not name:
            errors.append(f"Riga {r_num}: Nome conto vuoto.")
            continue
        if bal is None:
            errors.append(f"Riga {r_num}: Saldo non valido per conto '{name}'.")
            continue

        inst = str(row[matched["Istituto"]]).strip() if "Istituto" in matched and pd.notna(row[matched["Istituto"]]) else "Banca"
        acc_type = str(row[matched["Tipo_Conto"]]).strip().lower() if "Tipo_Conto" in matched and pd.notna(row[matched["Tipo_Conto"]]) else "checking"
        curr = str(row[matched["Valuta"]]).strip().upper() if "Valuta" in matched and pd.notna(row[matched["Valuta"]]) else "EUR"
        iban = str(row[matched["IBAN"]]).strip() if "IBAN" in matched and pd.notna(row[matched["IBAN"]]) else None
        notes = str(row[matched["Note"]]).strip() if "Note" in matched and pd.notna(row[matched["Note"]]) else None

        records.append({
            "name": name,
            "institution": inst,
            "account_type": acc_type,
            "currency": curr,
            "balance": bal,
            "iban": iban,
            "notes": notes
        })

    df_clean = pd.DataFrame(records)
    return (len(errors) == 0), errors, df_clean


def validate_pension_df(df_raw: pd.DataFrame) -> Tuple[bool, List[str], pd.DataFrame]:
    """Valida e normalizza il DataFrame dei Piani Pensionistici e Previdenza."""
    errors: List[str] = []
    if df_raw is None or df_raw.empty:
        return False, ["Il file è vuoto."], pd.DataFrame()

    matched = _match_column_aliases(df_raw, PENSION_ALIASES)
    if "Nome_Fondo" not in matched:
        errors.append("Colonna obbligatoria 'Nome_Fondo' non trovata.")
    if "Valore_Accumulato" not in matched:
        errors.append("Colonna obbligatoria 'Valore_Accumulato' non trovata.")

    if errors:
        return False, errors, pd.DataFrame()

    records = []
    for idx, row in df_raw.iterrows():
        r_num = idx + 1
        name = str(row[matched["Nome_Fondo"]]).strip()
        pot = _clean_amount(row[matched["Valore_Accumulato"]])

        if not name:
            errors.append(f"Riga {r_num}: Nome fondo vuoto.")
            continue
        if pot is None or pot < 0:
            errors.append(f"Riga {r_num}: Valore accumulato non valido per '{name}'.")
            continue

        prov = str(row[matched["Provider"]]).strip() if "Provider" in matched and pd.notna(row[matched["Provider"]]) else "Fondo Pensione"
        p_type = str(row[matched["Tipo_Piano"]]).strip().lower() if "Tipo_Piano" in matched and pd.notna(row[matched["Tipo_Piano"]]) else "fondo_pensione_aperto"
        c_emp = _clean_amount(row[matched["Versamento_Mensile"]]) if "Versamento_Mensile" in matched and pd.notna(row[matched["Versamento_Mensile"]]) else 0.0
        c_empr = _clean_amount(row[matched["Contributo_Datore"]]) if "Contributo_Datore" in matched and pd.notna(row[matched["Contributo_Datore"]]) else 0.0
        line = str(row[matched["Linea_Investimento"]]).strip() if "Linea_Investimento" in matched and pd.notna(row[matched["Linea_Investimento"]]) else "Azionario / Crescita"
        notes = str(row[matched["Note"]]).strip() if "Note" in matched and pd.notna(row[matched["Note"]]) else None

        records.append({
            "plan_name": name,
            "provider": prov,
            "plan_type": p_type,
            "accumulated_value": pot,
            "monthly_employee_contrib": c_emp or 0.0,
            "monthly_employer_contrib": c_empr or 0.0,
            "tax_deductible_annual": (c_emp or 0.0) * 12.0,
            "investment_line": line,
            "notes": notes
        })

    df_clean = pd.DataFrame(records)
    return (len(errors) == 0), errors, df_clean

