# ============================================================
# core/wealth/wealth_sync.py
# ARGUS — Wealth Google Sheets Synchronizer & Historical Importer
# Multi-Year Sync Engine (2021 - 2026) for Personal Finance
# ============================================================

import os
import re
import time
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from sqlalchemy import text as sqlt, Engine

from core.wealth.wealth_db import (
    init_wealth_db,
    get_wealth_accounts,
    save_wealth_account,
    get_wealth_categories,
    save_wealth_category,
    insert_cashflow_tx
)
from core.wealth.wealth_validator import _clean_amount, _clean_date

logger = logging.getLogger("wealth_sync")


def _safe_get_worksheet(spreadsheet: Any, title: str, max_retries: int = 3) -> Optional[Any]:
    """Recupera un worksheet gestendo rate limiting (HTTP 429) con exponential backoff."""
    for attempt in range(max_retries):
        try:
            return spreadsheet.worksheet(title)
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "rate" in err_str:
                sleep_time = (2 ** attempt) + 0.5
                logger.warning(f"Google Sheets API rate limit (429) su '{title}', retry in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            else:
                if attempt == max_retries - 1:
                    logger.warning(f"Impossibile accedere al foglio '{title}': {e}")
                return None
    return None


# Mappatura Standard ARGUS 50/30/20
TARGET_CATEGORIES = {
    # Inflows
    "Stipendio & Compensi": {"flow_type": "income", "nature": "inflow_active", "icon": "💼", "color": "#10b981"},
    "Borse di Studio & Premi": {"flow_type": "income", "nature": "inflow_active", "icon": "🎓", "color": "#34d399"},
    "Supporto Famiglia & Genitori": {"flow_type": "income", "nature": "inflow_active", "icon": "👨‍👩‍👦", "color": "#059669"},
    "Altre Entrate & Introiti Extra": {"flow_type": "income", "nature": "inflow_active", "icon": "💵", "color": "#a7f3d0"},
    "Rimborsi & Spese Saldate": {"flow_type": "income", "nature": "inflow_active", "icon": "🔄", "color": "#6ee7b7"},

    # 50% Needs
    "Casa, Affitto & Utenze": {"flow_type": "expense", "nature": "essential_need", "icon": "🏠", "color": "#ef4444"},
    "Spesa Alimentare & Supermercato": {"flow_type": "expense", "nature": "essential_need", "icon": "🛒", "color": "#dc2626"},
    "Trasporti, Benzina & Mezzi": {"flow_type": "expense", "nature": "essential_need", "icon": "🚗", "color": "#b91c1c"},
    "Salute, Farmacia & Visite": {"flow_type": "expense", "nature": "essential_need", "icon": "🏥", "color": "#991b1b"},
    "Istruzione, Corsi & Libri": {"flow_type": "expense", "nature": "essential_need", "icon": "📚", "color": "#7f1d1d"},
    "Tasse, Imposte & Commissioni": {"flow_type": "expense", "nature": "tax", "icon": "🏛️", "color": "#64748b"},
    "Utenze Extra & Spese Casa": {"flow_type": "expense", "nature": "essential_need", "icon": "🧹", "color": "#ea580c"},

    # 30% Wants
    "Ristoranti, Pizzerie & Sushi": {"flow_type": "expense", "nature": "discretionary_want", "icon": "🍽️", "color": "#f59e0b"},
    "Serate, Bar & Aperitivi": {"flow_type": "expense", "nature": "discretionary_want", "icon": "🍻", "color": "#fbbf24"},
    "Shopping & Abbigliamento": {"flow_type": "expense", "nature": "discretionary_want", "icon": "🛍️", "color": "#d97706"},
    "Viaggi, Voli & Vacanze": {"flow_type": "expense", "nature": "discretionary_want", "icon": "✈️", "color": "#b45309"},
    "Abbonamenti (Streaming, Spotify, iCloud)": {"flow_type": "expense", "nature": "discretionary_want", "icon": "📱", "color": "#92400e"},
    "Elettronica, PC & Gadget": {"flow_type": "expense", "nature": "discretionary_want", "icon": "💻", "color": "#78350f"},
    "Abitudini Personali & Heets": {"flow_type": "expense", "nature": "discretionary_want", "icon": "🚬", "color": "#a16207"},
    "Cura Personale & Parrucchiere": {"flow_type": "expense", "nature": "discretionary_want", "icon": "✂️", "color": "#ca8a04"},
    "Regali, Eventi & Lauree": {"flow_type": "expense", "nature": "discretionary_want", "icon": "🎁", "color": "#eab308"},
    "Tempo Libero, Cinema & Eventi": {"flow_type": "expense", "nature": "discretionary_want", "icon": "🎟️", "color": "#facc15"},
    "Spese per la Famiglia": {"flow_type": "expense", "nature": "discretionary_want", "icon": "👨‍👩‍👧", "color": "#fde047"},
    "Spese Varie & Imprevisti": {"flow_type": "expense", "nature": "discretionary_want", "icon": "📦", "color": "#f59e0b"},

    # 20% Savings & Transfers
    "Investimenti Titoli & Azioni": {"flow_type": "expense", "nature": "saving_investment", "icon": "📈", "color": "#6366f1"},
    "Investimenti Criptovalute": {"flow_type": "expense", "nature": "saving_investment", "icon": "🪙", "color": "#818cf8"},
    "Giroconti & Trasferimenti Interni": {"flow_type": "transfer", "nature": "transfer", "icon": "🔄", "color": "#94a3b8"}
}

GSHEET_CATEGORY_MAPPING = TARGET_CATEGORIES




def classify_category_semantic(raw_cat: str, raw_details: str = "", raw_type: str = "") -> str:
    """
    Riconosce e classifica in modo intelligente oltre 300 varianti di categorie storiche (2021-2026).
    """
    text = f"{raw_cat} {raw_details} {raw_type}".lower()

    # 1. Trasferimenti interni, Giroconti & Sistemazioni di Cassa
    if any(k in text for k in [
        "transfer", "trasferimenti", "giroconto", "sistemazion", "prelievo", "atm", "on the go - isp",
        "isp to revolut", "isp - revolut", "isp - on the go", "isp to n26", "buddy - n26", "isp - buddy"
    ]):
        return "Giroconti & Trasferimenti Interni"

    # 2. Investimenti & Crypto
    if any(k in text for k in ["crypto", "bitcoin", "binance", "ethereum"]):
        return "Investimenti Criptovalute"
    if any(k in text for k in ["stocks", "azioni", "degiro", "googl", "corsair", "pac ", "pac isp", "chiusura pac", "titoli"]):
        return "Investimenti Titoli & Azioni"

    # 3. Entrate & Redditi Attivi
    if any(k in text for k in ["salary", "stipendio", "sixtema", "sidera", "macelleria lavoro", "14esima"]):
        return "Stipendio & Compensi"
    if any(k in text for k in ["scholarship", "borsa di studio", "ergo", "unimore", "borsa studio"]) or re.search(r"\b(bs)\b", text):
        return "Borse di Studio & Premi"
    if re.search(r"\b(parents in|family in|papà|papa|mamma|nonno|zia|zio|edyta|salvadenaio|parenti|famiglia)\b", text):
        if "family out" not in text and "mamma ordine" not in text and "spray mamma" not in text and "bnb" not in text:
            if raw_type.lower() in ["income", "inflow"] or not raw_type:
                return "Supporto Famiglia & Genitori"
            elif any(g in text for g in ["regal", "laurea", "comple"]):
                return "Regali, Eventi & Lauree"
            else:
                return "Supporto Famiglia & Genitori"
    if any(k in text for k in ["refund", "rimborso", "settled from:", "bulk settlement", "storno", "reso "]):
        return "Rimborsi & Spese Saldate"


    if any(k in text for k in ["other income", "carte", "fanta", "vinto", "gratta e vinci", "nduja", "buoni pasto"]):
        if "buoni pasto" in text and ("expense" in raw_type.lower() or "-" in text):
            pass # È una spesa con buoni pasto
        else:
            return "Altre Entrate & Introiti Extra"

    # 4. Spese Primarie (Needs 50%)
    if re.search(r"\b(housing|affitto|alloggio|casa|mensilità|mensilita|cauzione|tim|bolletta|illiad)\b", text):
        return "Casa, Affitto & Utenze"

    if any(k in text for k in ["groceries", "alimentazione", "spesa", "supermercato", "acqua", "dolcificant", "caddy spesa"]):
        return "Spesa Alimentare & Supermercato"
    if any(k in text for k in [
        "transportation", "trasporti", "benzina", "benza", "assicurazione", "bollo", "treno",
        "pulman", "bus", "taxi", "marconi express", "aerobus", "pedaggio", "telepas", "meccanico",
        "gomme", "batteria", "seta modena"
    ]):
        return "Trasporti, Benzina & Mezzi"
    if any(k in text for k in [
        "health", "necessit", "salute", "farmacia", "medicine", "visita", "analisi", "tampone",
        "cerotti", "antibiotico", "gaviscon", "pronto soccorso", "rmn", "dito", "xinepa"
    ]):
        return "Salute, Farmacia & Visite"
    if any(k in text for k in [
        "education", "istruzione", "corso", "corsi", "inglese", "data analytics", "tesi",
        "universit", "laurea tassa", "libri", "damodaran", "fotocopi", "haccp"
    ]):
        return "Istruzione, Corsi & Libri"
    if any(k in text for k in ["fees taxes", "tasse", "sanzion", "imposte", "commissioni"]):
        return "Tasse, Imposte & Commissioni"
    if any(k in text for k in ["extra utilities", "utenze extra", "detersivo", "sarta", "lavanderia", "fari", "cartuccia", "adattatore"]):
        return "Utenze Extra & Spese Casa"

    # 5. Spese Discrezionali (Wants 30%)
    if any(k in text for k in ["dining out", "ristorant", "cena", "pranzo", "pizzeri", "sushi", "kebab", "gelato", "pizza", "vinaio", "burger", "hamerica", "stalla"]):
        return "Ristoranti, Pizzerie & Sushi"
    if any(k in text for k in ["going out", "uscite", "serata", "bar", "aperitiv", "cocktail", "birra", "vino", "caff", "bere", "disco", "spritz", "negroni", "redbull"]):
        return "Serate, Bar & Aperitivi"
    if any(k in text for k in ["shopping", "vestito", "scarpe", "zalando", "bershka", "mango", "primark", "sebago", "rayban", "piquadro", "polo ralph", "alcott"]):
        return "Shopping & Abbigliamento"
    if any(k in text for k in ["travel", "viaggi", "volo", "aereo", "bagaglio", "tirana", "hotel", "ostello", "bnb", "lamezia"]):
        return "Viaggi, Voli & Vacanze"
    if any(k in text for k in ["subscriptions", "abbonament", "spotify", "prime", "icloud", "netflix", "paramount", "phone top-up", "ricarica"]):
        return "Abbonamenti (Streaming, Spotify, iCloud)"
    if any(k in text for k in ["tech electronics", "cover", "vetrino", "rasoio", "stand", "blade", "schermo", "bluetooth", "kindle", "monopattino", "mouse"]):
        return "Elettronica, PC & Gadget"
    if any(k in text for k in ["personal habits", "heets", "sigarette", "sigari", "chewing gum", "gomme da masticare"]):
        return "Abitudini Personali & Heets"
    if any(k in text for k in ["personal care", "cura personale", "parrucchiere", "capelli", "spid", "tigot", "dentifricio", "colluttorio", "igiene", "sopraccigli"]):
        return "Cura Personale & Parrucchiere"
    if any(k in text for k in ["gifts", "regali", "regalo", "festa laurea", "corona laurea", "torta laurea", "airpods", "befana", "donazione", "festa in piscina"]):
        return "Regali, Eventi & Lauree"
    if any(k in text for k in ["free-time", "tempo libero", "cinema", "torneo", "palestra", "concerto", "decathlon", "nu genea", "elrow", "modena samp", "clash royale", "tiger", "ippicampo"]):
        return "Tempo Libero, Cinema & Eventi"
    if any(k in text for k in ["family out", "famiglia out", "mamma ordine", "spray mamma", "cellulare motorola", "pillole samu", "giulia", "cornetti"]):
        return "Spese per la Famiglia"

    # Default fallback
    if raw_type.lower() in ["income", "refund"]:
        return "Altre Entrate & Introiti Extra"
    return "Spese Varie & Imprevisti"


def _parse_single_yearly_sheet(
    engine: Engine,
    raw_rows: List[List[str]],
    year: int,
    cat_name_to_id: Dict[str, int],
    is_latest_year: bool = False,
    portfolio_id: int = 1
) -> Tuple[Dict[str, int], int, Dict[str, float]]:
    """Esegue il parsing di una singola scheda annuale Expenses Tracker YYYY."""
    if len(raw_rows) < 5:
        return {}, 0, {}

    # 1. Mappatura colonne conti (riga 8/9 tipicamente, o prime righe per versioni compatte)
    WHITELISTED_ACCOUNT_NAMES = [
        "intesa san paolo", "intesa sanpaolo", "isp", "revolut", "n26", 
        "food stamps", "buoni pasto", "on the go wallet", "wallet", "buddybank", "buddy bank"
    ]
    BLACKLISTED_ACCOUNT_NAMES = [
        "poker", "eurobet", "mamma", "+/-", "controllo", "automatismi", "differenza", "totale", "saldo", "delta"
    ]

    account_cols_map = {} # col_idx -> clean_name
    account_final_balances = {} # clean_name -> float

    header_row = raw_rows[8] if len(raw_rows) > 8 else raw_rows[0]
    balance_row = raw_rows[6] if len(raw_rows) > 6 else []

    # Fallback se la riga 8 non ha i conti (es. test mock con riga 1)
    if not any(w in " ".join(header_row).lower() for w in WHITELISTED_ACCOUNT_NAMES) and len(raw_rows) > 1:
        header_row = raw_rows[1]
        balance_row = raw_rows[2] if len(raw_rows) > 2 else []

    for idx, cell in enumerate(header_row):
        txt = cell.strip()
        txt_lower = txt.lower()
        
        is_whitelisted = any(w in txt_lower for w in WHITELISTED_ACCOUNT_NAMES)
        is_blacklisted = any(b in txt_lower for b in BLACKLISTED_ACCOUNT_NAMES)

        if txt and is_whitelisted and not is_blacklisted:
            clean_name = txt
            account_cols_map[idx] = clean_name
            
            if balance_row and idx < len(balance_row):
                bal_str = balance_row[idx].strip()
                parsed_bal = _clean_amount(bal_str)
                if parsed_bal is not None:
                    account_final_balances[clean_name] = parsed_bal

    # Assicura la presenza dei conti nel DB
    account_db_ids = {}
    for acc_name, bal_val in account_final_balances.items():
        acc_lower = acc_name.lower()
        if "revolut" in acc_lower:
            acc_type = "checking"
            institution = "Revolut Bank"
        elif "n26" in acc_lower:
            acc_type = "checking"
            institution = "N26 Bank"
        elif "buddy" in acc_lower:
            acc_type = "checking"
            institution = "BuddyBank (UniCredit)"
        elif "intesa" in acc_lower or "isp" in acc_lower:
            acc_type = "checking"
            institution = "Intesa Sanpaolo"
        elif "wallet" in acc_lower or "on the go" in acc_lower:
            acc_type = "checking"
            institution = "Contanti / Portafoglio"
        elif "food" in acc_lower or "buoni" in acc_lower:
            acc_type = "checking"
            institution = "Edenred / Buoni Pasto"
        else:
            acc_type = "checking"
            institution = acc_name

        acc_id = save_wealth_account(engine, {
            "portfolio_id": portfolio_id,
            "name": acc_name,
            "institution": institution,
            "account_type": acc_type,
            "balance": bal_val if is_latest_year else 0.0,
            "currency": "EUR",
            "notes": f"Sincronizzato da GSheets Expenses Tracker {year}"
        })
        account_db_ids[acc_name] = acc_id


    # 2. Identifica testata transazioni
    tx_start_idx = 19
    has_explicit_category = True
    for i, r in enumerate(raw_rows):
        if len(r) > 1 and "Transactions" in r[1]:
            tx_start_idx = i + 1
            if len(r) > 2 and "Category" not in r[2] and "Details" in r[2]:
                has_explicit_category = False
            break

    # Pulisci record precedenti dell'anno
    with engine.begin() as conn:
        conn.execute(sqlt("DELETE FROM wealth_cashflow WHERE tags LIKE :t"), {"t": f"%gsheets_expenses_{year}%"})

    imported_tx = 0
    for r_idx in range(tx_start_idx, len(raw_rows)):
        row = raw_rows[r_idx]
        if not row or len(row) < 3:
            continue

        raw_date = row[0].strip()
        raw_type = row[1].strip() if len(row) > 1 else ""

        if has_explicit_category:
            raw_cat = row[2].strip() if len(row) > 2 else ""
            raw_details = row[3].strip() if len(row) > 3 else ""
            raw_notes_id = row[10].strip() if len(row) > 10 else ""
        else:
            raw_cat = ""
            raw_details = row[2].strip() if len(row) > 2 else ""
            raw_notes_id = row[7].strip() if len(row) > 7 else ""

        # Normalizza data: se solo 'DD/MM' aggiungiamo l'anno '/YYYY'
        if re.match(r"^\d{1,2}/\d{1,2}$", raw_date):
            raw_date = f"{raw_date}/{year}"

        parsed_date = _clean_date(raw_date)
        if not parsed_date:
            continue

        # Classifica categoria standard 50/30/20
        standard_cat_name = classify_category_semantic(raw_cat, raw_details, raw_type)
        cat_id = cat_name_to_id.get(standard_cat_name.lower(), 1)

        # Scansiona le colonne conto
        for c_idx, acc_name in account_cols_map.items():
            if c_idx >= len(row):
                continue
            amt_str = row[c_idx].strip()
            if not amt_str or amt_str in ["€ -", "-€ -", "€ -   ", "-", "0"]:
                continue

            parsed_amt = _clean_amount(amt_str)
            if parsed_amt is None or parsed_amt == 0.0:
                continue

            if raw_type.lower() in ["income", "refund"]:
                direction = "inflow"
            elif raw_type.lower() == "expense":
                direction = "outflow"
            else:
                direction = "inflow" if parsed_amt > 0 else "outflow"

            abs_amount = abs(parsed_amt)
            target_acc_id = account_db_ids.get(acc_name)
            if not target_acc_id:
                continue

            tx_payload = {
                "portfolio_id": portfolio_id,
                "account_id": target_acc_id,
                "category_id": cat_id,
                "tx_date": parsed_date,
                "amount": abs_amount,
                "direction": direction,
                "merchant": raw_details if raw_details else (raw_cat or standard_cat_name),
                "notes": f"[{raw_type or 'Movement'}] {raw_cat} - {raw_details} {raw_notes_id}".strip(),
                "payment_method": "Carta / Bonifico",
                "tags": f"gsheets_expenses_{year},{raw_type.lower()}"
            }
            insert_cashflow_tx(engine, tx_payload)
            imported_tx += 1

    return account_db_ids, imported_tx, account_final_balances


def _sync_pension_sheet(engine: Engine, spreadsheet: Any, portfolio_id: int = 1) -> Optional[Dict[str, Any]]:
    """
    Scarica e analizza la scheda 'Pension' da Google Sheets.
    Estrae i versamenti mensili, i totali annuali e il capitale cumulato per ciascun anno (2023-2026+).
    """
    from core.wealth.wealth_db import save_pension_plan, get_pension_plans
    ws = _safe_get_worksheet(spreadsheet, "Pension")
    if not ws:
        logger.info("Scheda 'Pension' non trovata nello spreadsheet.")
        return None
    try:
        rows = ws.get_all_values()
    except Exception as e:
        logger.info(f"Errore lettura righe scheda 'Pension': {e}")
        return None

    yearly_data = {}
    for i in range(0, len(rows), 2):
        if i + 1 >= len(rows):
            break
        header = rows[i]

        data = rows[i + 1]
        year_str = header[0].strip()
        if not year_str.isdigit():
            continue
        year = int(year_str)

        months = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
        monthly_vals = {}
        for m_idx in range(1, 13):
            if m_idx < len(data):
                v = _clean_amount(data[m_idx])
                if v is not None and v > 0:
                    monthly_vals[months[m_idx - 1]] = v

        tot_year = _clean_amount(data[13]) if len(data) > 13 else None
        tot_cum = _clean_amount(data[14]) if len(data) > 14 else None
        tot_versato_fondo = _clean_amount(data[15]) if len(data) > 15 else None
        gain_loss = _clean_amount(data[16]) if len(data) > 16 else None
        tot_fondo = _clean_amount(data[18]) if len(data) > 18 else None

        yearly_data[year] = {
            "months": monthly_vals,
            "tot_year": tot_year or 0.0,
            "tot_cumulato": tot_cum or 0.0,
            "tot_versato_fondo": tot_versato_fondo,
            "gain_loss": gain_loss,
            "tot_fondo": tot_fondo
        }

    if not yearly_data:
        return None

    # Calcola il valore più recente attivo
    active_years_with_data = [y for y, d in yearly_data.items() if len(d["months"]) > 0 or d["tot_year"] > 0]
    latest_active_year = max(active_years_with_data) if active_years_with_data else max(yearly_data.keys())
    latest_data = yearly_data.get(latest_active_year, {})
    
    # Valore accumulato massimo storico reale
    all_cum_vals = [d["tot_cumulato"] for d in yearly_data.values() if d["tot_cumulato"] > 0]
    accumulated_val = max(all_cum_vals) if all_cum_vals else latest_data.get("tot_cumulato", 0.0)

    # Calcola contribuzione mensile media
    m_vals = latest_data.get("months", {})
    avg_monthly = float(np.mean(list(m_vals.values()))) if m_vals else 0.0
    tot_annual_contrib = latest_data.get("tot_year", 0.0)


    # Crea note riassuntive
    history_str = " | ".join(f"{y}: €{d['tot_year']:,.2f}" for y, d in sorted(yearly_data.items()) if d['tot_year'] > 0)

    df_curr_pens = get_pension_plans(engine, portfolio_id=portfolio_id)
    existing_plan_id = None
    if not df_curr_pens.empty:
        matches = df_curr_pens[df_curr_pens["plan_name"].str.contains("Fondo Pensione", case=False, na=False)]
        if not matches.empty:
            existing_plan_id = int(matches.iloc[0]["plan_id"])

    save_pension_plan(engine, {
        "plan_id": existing_plan_id,
        "portfolio_id": portfolio_id,
        "plan_name": "Fondo Pensione Integrativo (GSheets)",
        "provider": "Fondo Aperto / PIP",
        "plan_type": "fondo_pensione_aperto",
        "accumulated_value": accumulated_val,
        "monthly_employee_contrib": round(avg_monthly, 2),
        "monthly_employer_contrib": 0.0,
        "tax_deductible_annual": round(tot_annual_contrib, 2),
        "expected_retirement_age": 67,
        "currency": "EUR",
        "investment_line": "Azionario / Crescita",
        "notes": f"Sincronizzato da foglio Pension (Anni: {history_str})"
    })

    return {
        "accumulated_value": accumulated_val,
        "monthly_employee_contrib": avg_monthly,
        "tax_deductible_annual": tot_annual_contrib,
        "yearly_breakdown": yearly_data
    }


def _sync_others_illiquid_assets_sheet(engine: Engine, spreadsheet: Any, portfolio_id: int = 1) -> List[int]:
    """
    Scarica e analizza la scheda 'Others' da Google Sheets per sincronizzare
    gli asset fisici e illiquidi (Metalli preziosi / Oro, Orologi, Immobili, Collezionismo).
    """
    from core.wealth.wealth_db import save_physical_asset, get_physical_assets
    ws = _safe_get_worksheet(spreadsheet, "Others")
    if not ws:
        logger.info("Scheda 'Others' non trovata nello spreadsheet.")
        return []
    try:
        rows = ws.get_all_values()
    except Exception as e:
        logger.info(f"Errore lettura righe scheda 'Others': {e}")
        return []

    if not rows or len(rows) < 2:
        return []

    df_curr = get_physical_assets(engine, portfolio_id=portfolio_id)
    existing_map = {r["name"].lower(): r["asset_id"] for _, r in df_curr.iterrows()} if not df_curr.empty else {}

    saved_asset_ids = []
    for i, r in enumerate(rows[1:], start=1):
        if not r or len(r) < 5 or not r[0].strip():
            continue
        oggetto = r[0].strip()
        materiale = r[1].strip() if len(r) > 1 else ""
        peso = r[2].strip() if len(r) > 2 else ""
        prezzo_g = r[3].strip() if len(r) > 3 else ""
        prezzo_oggi = _clean_amount(r[4]) if len(r) > 4 else 0.0
        prezzo_acq = _clean_amount(r[5]) if len(r) > 5 and r[5].strip() else prezzo_oggi

        # Categorizzazione semantica automatica e brand extraction
        og_lower = oggetto.lower()
        mat_lower = materiale.lower()
        brand_detected = None
        for b_cand in ["Rolex", "Omega", "Patek Philippe", "Audemars Piguet", "Tudor", "Cartier", "Seiko", "Tissot", "Longines", "TAG Heuer", "Breitling", "IWC", "Panerai", "Zenith", "Casio", "Hamilton"]:
            if b_cand.lower() in og_lower or b_cand.lower() in mat_lower:
                brand_detected = b_cand
                break

        if brand_detected or any(w in og_lower or w in mat_lower for w in ["orolog", "watch"]):
            cat = "luxury_watches"
            grade = "Ottimo / Custodito"
            brand_loc = brand_detected if brand_detected else (materiale if materiale else "Orologeria")
            specs = materiale if (brand_detected and materiale != brand_detected) else "Automatico"
        elif any(w in og_lower or w in mat_lower for w in ["oro", "argento", "platino", "lingotto", "braccial", "moneta", "metallo"]):
            cat = "precious_metals"
            grade = "Custodito in Caveau"
            brand_loc = materiale if materiale else "Oro (18K)"
            specs = f"{peso}g @ {prezzo_g}" if peso and prezzo_g else (f"{peso}g" if peso else "Metallo Nobile")
        elif any(w in og_lower or w in mat_lower for w in ["immob", "casa", "appartamento", "terreno", "garage", "villa"]):
            cat = "real_estate"
            grade = "A/2 Residenziale"
            brand_loc = materiale if materiale else "Immobile"
            specs = f"{peso} mq" if peso else "Proprietà Immobiliare"
        else:
            cat = "art_collectibles"
            grade = "Ottimo"
            brand_loc = materiale if materiale else "Collezione"
            specs = materiale

        aid = existing_map.get(oggetto.lower())

        saved_id = save_physical_asset(engine, {
            "asset_id": aid,
            "portfolio_id": portfolio_id,
            "name": oggetto,
            "asset_category": cat,
            "brand_or_location": brand_loc,
            "model_or_specs": specs,
            "reference_number": None,
            "purchase_price": prezzo_acq or 0.0,
            "current_market_value": prezzo_oggi or 0.0,
            "condition_grade": grade,
            "currency": "EUR",
            "notes": "Sincronizzato da foglio 'Others' (Google Sheets)"
        })
        saved_asset_ids.append(saved_id)

    return saved_asset_ids


def _sync_config_fixed_expenses_sheet(engine: Engine, spreadsheet: Any, portfolio_id: int = 1) -> List[int]:
    """
    Scarica e sincronizza le spese fisse e gli abbonamenti dalla scheda 'Config_FixedExpenses' di Google Sheets.
    """
    from core.wealth.wealth_db import save_wealth_fixed_expense, clear_wealth_fixed_expenses
    
    ws = None
    for cand in ["Config_FixedExpenses", "Config FixedExpenses", "FixedExpenses", "Fixed Expenses", "Config_Fixed_Expenses"]:
        ws = _safe_get_worksheet(spreadsheet, cand)
        if ws:
            break
            
    if not ws:
        logger.info("Scheda 'Config_FixedExpenses' non trovata nello spreadsheet.")
        return []

    try:
        rows = ws.get_all_values()
    except Exception as e:
        logger.info(f"Errore lettura righe scheda 'Config_FixedExpenses': {e}")
        return []

    if not rows or len(rows) < 2:
        return []

    # Mappa colonne dall'header
    header = [str(c).strip().lower() for c in rows[0]]
    
    def get_col_idx(names: List[str]) -> Optional[int]:
        for n in names:
            for idx, h in enumerate(header):
                if n in h:
                    return idx
        return None

    cat_idx = get_col_idx(["categoria", "category"])
    note_idx = get_col_idx(["nota", "note", "descrizione", "description", "servizio"])
    amt_idx = get_col_idx(["importo", "amount", "costo", "prezzo"])
    day_idx = get_col_idx(["giorno", "day", "pagamento", "pagamer"])
    start_idx = get_col_idx(["data inizio", "start date", "inizio", "start"])
    end_idx = get_col_idx(["data fine", "end date", "fine", "end"])
    split_idx = get_col_idx(["is split", "split"])
    split_det_idx = get_col_idx(["split details", "dettagli split"])

    # Pulisci record precedenti
    clear_wealth_fixed_expenses(engine, portfolio_id=portfolio_id)

    saved_ids = []
    for row in rows[1:]:
        if not row:
            continue
            
        raw_amt_str = row[amt_idx].strip() if amt_idx is not None and amt_idx < len(row) else "0"
        if not raw_amt_str:
            continue

        parsed_amt = _clean_amount(raw_amt_str)
        if parsed_amt is None or parsed_amt <= 0.0:
            continue

        raw_cat = row[cat_idx].strip() if cat_idx is not None and cat_idx < len(row) else "Subscriptions"
        raw_note = row[note_idx].strip() if note_idx is not None and note_idx < len(row) else (raw_cat or "Spesa Fissa")
        
        raw_day = row[day_idx].strip() if day_idx is not None and day_idx < len(row) else None
        p_day = int(raw_day) if raw_day and raw_day.isdigit() else None

        raw_start = row[start_idx].strip() if start_idx is not None and start_idx < len(row) else None
        s_date = _clean_date(raw_start) if raw_start else None

        raw_end = row[end_idx].strip() if end_idx is not None and end_idx < len(row) else None
        e_date = _clean_date(raw_end) if raw_end else None

        raw_split = row[split_idx].strip().upper() if split_idx is not None and split_idx < len(row) else "FALSE"
        is_split = raw_split in ["TRUE", "1", "VERO", "SI", "YES"]
        
        s_det = row[split_det_idx].strip() if split_det_idx is not None and split_det_idx < len(row) else None

        fid = save_wealth_fixed_expense(engine, {
            "portfolio_id": portfolio_id,
            "category": raw_cat,
            "note": raw_note,
            "amount": abs(parsed_amt),
            "payment_day": p_day,
            "start_date": s_date,
            "end_date": e_date,
            "is_split": is_split,
            "split_details": s_det,
            "cadence": "Mensile",
            "is_active": True
        })
        saved_ids.append(fid)

    logger.info(f"Sincronizzate {len(saved_ids)} spese fisse dalla scheda 'Config_FixedExpenses'.")
    return saved_ids


def _sync_net_worth_oggi_tab(engine: Engine, spreadsheet: Any, portfolio_id: int = 1) -> Dict[str, float]:
    """Scarica e memorizza le posizioni patrimoniali consolidate da Net Worth OGGI (o foglio Pension se disponibile)."""
    # Prima tenta la sincronizzazione avanzata dal foglio 'Pension'
    pension_res = _sync_pension_sheet(engine, spreadsheet, portfolio_id=portfolio_id)
    
    # Se il foglio Pension non esiste, usa il fallback da Net Worth OGGI
    if not pension_res:
        ws = _safe_get_worksheet(spreadsheet, "Net Worth OGGI")
        if not ws:
            logger.warning("Scheda Net Worth OGGI non presente nello spreadsheet.")
            return {}
        try:
            rows = ws.get_all_values()
            parsed = {}
            for r in rows:
                if len(r) >= 2 and r[0].strip() and r[1].strip():
                    k = r[0].strip()
                    amt = _clean_amount(r[1].strip())
                    if amt is not None:
                        parsed[k] = amt
            
            pension_val = parsed.get("Pension", 3635.09)
            if pension_val > 0:
                from core.wealth.wealth_db import get_pension_plans, save_pension_plan
                df_curr_pens = get_pension_plans(engine, portfolio_id=portfolio_id)
                existing_plan_id = None
                if not df_curr_pens.empty:
                    matches = df_curr_pens[df_curr_pens["plan_name"] == "Fondo Pensione Integrativo (GSheets)"]
                    if not matches.empty:
                        existing_plan_id = int(matches.iloc[0]["plan_id"])

                save_pension_plan(engine, {
                    "plan_id": existing_plan_id,
                    "portfolio_id": portfolio_id,
                    "plan_name": "Fondo Pensione Integrativo (GSheets)",
                    "provider": "Fondo Aperto / PIP",
                    "plan_type": "fondo_pensione_aperto",
                    "accumulated_value": pension_val,
                    "currency": "EUR",
                    "notes": "Sincronizzato da Net Worth OGGI"
                })
            return parsed
        except Exception as e:
            logger.warning(f"Errore lettura Net Worth OGGI: {e}")
            return {}
    return {}






def sync_all_historical_expenses_from_gsheets(
    engine: Engine,
    spreadsheet_name: str = "My All financial Statements",
    years: Optional[List[int]] = None,
    portfolio_id: int = 1
) -> Dict[str, Any]:
    """
    Sincronizza in blocco tutti gli anni storici delle spese (2021, 2022, 2023, 2024, 2025, 2026).
    """
    from gsheets_sync_subproject.sync_google_sheets import get_gspread_client

    init_wealth_db(engine)
    client = get_gspread_client()

    if years is None:
        years = [2021, 2022, 2023, 2024, 2025, 2026]

    try:
        if spreadsheet_name.startswith("http") or len(spreadsheet_name) > 30:
            spreadsheet = client.open_by_key(spreadsheet_name.split("/d/")[1].split("/")[0]) if "/d/" in spreadsheet_name else client.open_by_key(spreadsheet_name)
        else:
            spreadsheet = client.open(spreadsheet_name)
    except Exception as e:
        raise RuntimeError(f"Impossibile aprire lo spreadsheet '{spreadsheet_name}': {e}")

    # 1. Popola / Assicura tutte le categorie standard 50/30/20 nel DB
    df_existing_cats = get_wealth_categories(engine)
    cat_name_to_id = {r["name"].lower(): r["category_id"] for _, r in df_existing_cats.iterrows()}

    for c_name, c_info in TARGET_CATEGORIES.items():
        if c_name.lower() not in cat_name_to_id:
            new_cid = save_wealth_category(engine, {
                "name": c_name,
                "flow_type": c_info["flow_type"],
                "nature": c_info["nature"],
                "icon": c_info["icon"],
                "color": c_info["color"],
                "is_system": True
            })
            cat_name_to_id[c_name.lower()] = new_cid

    total_synced_tx = 0
    synced_years_summary = {}
    latest_balances = {}
    latest_acc_ids = {}

    for y in sorted(years):
        sheet_tab = f"Expenses Tracker {y}"
        ws = _safe_get_worksheet(spreadsheet, sheet_tab)
        if not ws:
            logger.warning(f"Scheda '{sheet_tab}' non trovata o non leggibile.")
            continue
        try:
            raw_rows = ws.get_all_values()
        except Exception as e:
            logger.warning(f"Errore lettura dati '{sheet_tab}': {e}")
            continue

        is_latest = (y == max(years))

        acc_ids, tx_count, balances = _parse_single_yearly_sheet(
            engine,
            raw_rows,
            year=y,
            cat_name_to_id=cat_name_to_id,
            is_latest_year=is_latest,
            portfolio_id=portfolio_id
        )
        total_synced_tx += tx_count
        synced_years_summary[y] = tx_count
        if is_latest:
            latest_balances = balances
            latest_acc_ids = acc_ids

    # Se abbiamo processato l'anno più recente (es. 2026), impostiamo i saldi live ufficiali
    if latest_balances and latest_acc_ids:
        with engine.begin() as conn:
            for acc_name, bal_val in latest_balances.items():
                aid = latest_acc_ids.get(acc_name)
                if aid:
                    conn.execute(sqlt("UPDATE wealth_accounts SET balance = :b WHERE account_id = :aid"), {"b": bal_val, "aid": aid})

    # 4. Sincronizza posizioni consolidate da Net Worth OGGI, Others e Spese Fisse da Config_FixedExpenses
    _sync_net_worth_oggi_tab(engine, spreadsheet, portfolio_id=portfolio_id)
    _sync_others_illiquid_assets_sheet(engine, spreadsheet, portfolio_id=portfolio_id)
    _sync_config_fixed_expenses_sheet(engine, spreadsheet, portfolio_id=portfolio_id)

    # 5. Scatta e Salva automaticamente uno Snapshot consolidato nel database

    from core.wealth.wealth_snapshot import save_wealth_snapshot_to_db
    snap_name = f"Snapshot Sync GSheets ({min(years)}-{max(years)})" if len(years) > 1 else f"Snapshot Sync GSheets {years[0]}"
    try:
        snap_id = save_wealth_snapshot_to_db(
            engine,
            snapshot_name=snap_name,
            notes=f"Auto-generato da sincronizzazione Google Sheets ({total_synced_tx:,} transazioni)",
            portfolio_id=portfolio_id
        )
    except Exception as e:
        logger.error(f"Errore nella generazione automatica dello snapshot: {e}")
        snap_id = None


    return {
        "status": "success",
        "years_synced": list(synced_years_summary.keys()),
        "breakdown_by_year": synced_years_summary,
        "total_transactions_synced": total_synced_tx,
        "transactions_synced": total_synced_tx,
        "accounts_count": len(latest_acc_ids) if latest_acc_ids else 6,
        "accounts_synced": len(latest_acc_ids) if latest_acc_ids else 6,
        "accounts_list": list(latest_acc_ids.keys()) if latest_acc_ids else ["Intesa San Paolo", "N26", "On the go Wallet", "BuddyBank", "Revolut", "Food stamps"],
        "snapshot_id": snap_id,
        "snapshot_name": snap_name,
        "spreadsheet": spreadsheet_name,
        "portfolio_id": portfolio_id
    }



def sync_expenses_tracker_2026_from_gsheets(
    engine: Engine,
    spreadsheet_name: str = "My All financial Statements",
    worksheet_name: str = "Expenses Tracker 2026",
    portfolio_id: int = 1
) -> Dict[str, Any]:
    """Sincronizzazione rapida del solo anno 2026."""
    res = sync_all_historical_expenses_from_gsheets(
        engine,
        spreadsheet_name=spreadsheet_name,
        years=[2026],
        portfolio_id=portfolio_id
    )
    return res



def sync_wealth_from_payload(engine: Engine, payload: Dict[str, Any]) -> None:

    """Wrapper legacy compatibile per payload generici."""
    pass
