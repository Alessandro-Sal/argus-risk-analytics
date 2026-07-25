# ============================================================
# validator.py
# Investment Risk BI Platform
# 
# Input:  DataFrame grezzo letto dal CSV
# Output: (df_clean, report)
#         df_clean → DataFrame normalizzato, pronto per MySQL
#         report   → dict con errori bloccanti, warning, fix applicati
# ============================================================

import pandas as pd
import numpy as np
import re
from datetime import datetime

# ── Costanti ────────────────────────────────────────────────

REQUIRED_COLS = ["tx_date", "ticker", "tx_type", "quantity", "price", "currency"]
OPTIONAL_COLS = {"fees": 0.0, "asset_class": None, "notes": None}

VALID_TX_TYPES    = {"buy", "sell", "dividend"}
VALID_ASSET_CLASS = {"stock", "etf", "bond", "crypto", "cash"}

# Codici ISO 4217 comuni + crypto principali
VALID_CURRENCIES = {
    "EUR","USD","GBP","CHF","JPY","CAD","AUD","SEK","NOK","DKK",
    "HKD","SGD","NZD","MXN","BRL","INR","CNY","ZAR",
    "BTC","ETH","USDT","BNB","XRP","SOL"
}

# Pattern ISIN: 2 lettere + 10 alfanumerici
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")


# ── Funzione principale ──────────────────────────────────────

def validate_csv(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Valida e normalizza un DataFrame letto da CSV.

    Returns
    -------
    df_clean : pd.DataFrame
        DataFrame normalizzato, pronto per l'ETL verso MySQL.
        None se ci sono errori bloccanti.
    report : dict
        {
          "errors":   list[str],   # errori bloccanti → pipeline si ferma
          "warnings": list[str],   # problemi non bloccanti → pipeline continua
          "fixes":    list[str],   # correzioni automatiche applicate
          "stats":    dict         # statistiche di sintesi
        }
    """
    report = {"errors": [], "warnings": [], "fixes": [], "stats": {}}
    df = df_raw.copy()

    # ── STEP 1: colonne ─────────────────────────────────────
    df.columns = df.columns.str.strip().str.lower()

    missing_required = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_required:
        report["errors"].append(
            f"Colonne obbligatorie mancanti: {missing_required}"
        )
        return None, report

    # Aggiunge colonne opzionali mancanti con i default
    for col, default in OPTIONAL_COLS.items():
        if col not in df.columns:
            df[col] = default
            report["fixes"].append(
                f"Colonna '{col}' assente → aggiunta con default '{default}'"
            )

    # ── STEP 2: righe vuote ─────────────────────────────────
    n_before = len(df)
    df = df.dropna(subset=REQUIRED_COLS, how="all")
    dropped = n_before - len(df)
    if dropped > 0:
        report["fixes"].append(f"{dropped} righe completamente vuote rimosse")

    # ── STEP 3: tx_date ─────────────────────────────────────
    df, report = _normalize_dates(df, report)
    if report["errors"]:
        return None, report

    # ── STEP 4: ticker ──────────────────────────────────────
    df, report = _normalize_tickers(df, report)

    # ── STEP 5: tx_type ─────────────────────────────────────
    df["tx_type"] = df["tx_type"].str.strip().str.lower()
    invalid_types = df[~df["tx_type"].isin(VALID_TX_TYPES)]
    if not invalid_types.empty:
        report["errors"].append(
            f"tx_type non valido in {len(invalid_types)} righe: "
            f"{invalid_types['tx_type'].unique().tolist()} — valori accettati: {VALID_TX_TYPES}"
        )
        return None, report

    # ── STEP 6: quantity e price ─────────────────────────────
    df, report = _normalize_numerics(df, report)
    if report["errors"]:
        return None, report

    # ── STEP 7: currency ────────────────────────────────────
    df["currency"] = df["currency"].str.strip().str.upper()
    unknown_currencies = df[~df["currency"].isin(VALID_CURRENCIES)]["currency"].unique()
    if len(unknown_currencies) > 0:
        report["warnings"].append(
            f"Valute non riconosciute (potrebbero essere valide ma rare): "
            f"{unknown_currencies.tolist()}"
        )

    # ── STEP 8: fees ────────────────────────────────────────
    df["fees"] = pd.to_numeric(
        df["fees"].astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    ).fillna(0.0)
    df["fees"] = df["fees"].clip(lower=0.0)

    # ── STEP 9: asset_class ──────────────────────────────────
    df, report = _normalize_asset_class(df, report)

    # ── STEP 10: dividend edge case ──────────────────────────
    #df, report = _fix_dividend_quantity(df, report)

    # ── STEP 11: notes ───────────────────────────────────────
    df["notes"] = df["notes"].astype(str).str.strip().str[:255]
    df["notes"] = df["notes"].replace({"nan": None, "None": None, "": None})

    # ── STEP 12: ordina e resetta index ──────────────────────
    df = df.sort_values("tx_date").reset_index(drop=True)

    # ── Stats ────────────────────────────────────────────────
    report["stats"] = {
        "total_rows":       len(df),
        "tx_type_counts":   df["tx_type"].value_counts().to_dict(),
        "asset_classes":    df["asset_class"].value_counts(dropna=False).to_dict(),
        "tickers":          sorted(df["ticker"].unique().tolist()),
        "currencies":       sorted(df["currency"].unique().tolist()),
        "date_range":       (df["tx_date"].min().strftime("%Y-%m-%d"), df["tx_date"].max().strftime("%Y-%m-%d")),
        "is_valid":         len(report["errors"]) == 0,
    }

    return df, report


# ── Helper: date ─────────────────────────────────────────────

def _normalize_dates(df: pd.DataFrame, report: dict) -> tuple:
    """
    Accetta YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY.
    Converte tutto in datetime.date.
    """
    original = df["tx_date"].copy()

    # Tenta con dayfirst=True (DD/MM/YYYY e YYYY-MM-DD)
    df["tx_date"] = pd.to_datetime(
        df["tx_date"].astype(str).str.strip(),
        dayfirst=True,
        errors="coerce"
    )

    # Righe ancora NaT → tenta dayfirst=False (MM/DD/YYYY)
    mask_nat = df["tx_date"].isna()
    if mask_nat.any():
        df.loc[mask_nat, "tx_date"] = pd.to_datetime(
            original[mask_nat].astype(str).str.strip(),
            dayfirst=False,
            errors="coerce"
        )

    # Ancora NaT → errore bloccante
    still_nat = df["tx_date"].isna()
    if still_nat.any():
        bad = original[still_nat].unique().tolist()
        report["errors"].append(
            f"Formato data non riconoscibile in {still_nat.sum()} righe: {bad}"
        )
        return df, report

    # Date future → warning
    today = pd.Timestamp.today().normalize()
    future = df["tx_date"] > today
    if future.any():
        report["warnings"].append(
            f"{future.sum()} transazioni con data futura — controlla i dati"
        )

    report["fixes"].append("Date normalizzate a formato YYYY-MM-DD")
    return df, report


# ── Helper: ticker ───────────────────────────────────────────

def _normalize_tickers(df: pd.DataFrame, report: dict) -> tuple:
    """
    - Strip e uppercase
    - Crypto senza coppia valuta → autocorrect a {TICKER}-{CURRENCY}
    - ISIN → segnala warning (no fetch yfinance)
    """
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()

    crypto_mask = (
        df["asset_class"].str.lower() == "crypto"
        if "asset_class" in df.columns
        else pd.Series(False, index=df.index)
    )

    # Crypto senza suffisso valuta (es. BTC → BTC-USD)
    needs_fix = crypto_mask & ~df["ticker"].str.contains("-", na=False)
    if needs_fix.any():
        df.loc[needs_fix, "ticker"] = (
            df.loc[needs_fix, "ticker"] + "-" +
            df.loc[needs_fix, "currency"].str.upper()
        )
        fixed = df.loc[needs_fix, "ticker"].unique().tolist()
        report["fixes"].append(
            f"Ticker crypto corretti aggiungendo coppia valuta: {fixed}"
        )

    # ISIN → warning
    isin_mask = df["ticker"].str.match(ISIN_PATTERN)
    if isin_mask.any():
        isins = df.loc[isin_mask, "ticker"].unique().tolist()
        report["warnings"].append(
            f"Ticker ISIN rilevati (yfinance non supportato, prezzo da CSV): {isins}"
        )

    return df, report


# ── Helper: quantity e price ──────────────────────────────────

def _normalize_numerics(df: pd.DataFrame, report: dict) -> tuple:
    """
    Converte quantity e price in float, gestisce virgola/punto decimale.
    Errore bloccante se non convertibili.
    """
    for col in ["quantity", "price"]:
        df[col] = (
            df[col].astype(str)
            .str.strip()
            .str.replace(",", ".", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

        if df[col].isna().any():
            bad_count = df[col].isna().sum()
            report["errors"].append(
                f"'{col}' contiene {bad_count} valori non numerici"
            )

        # quantity non può essere negativa
        if col == "quantity":
            neg = df["quantity"] < 0
            if neg.any():
                report["errors"].append(
                    f"'quantity' negativa in {neg.sum()} righe — "
                    f"usa tx_type='sell' invece di quantity negativa"
                )

        # price non può essere negativo (tranne dividend che può essere 0)
        if col == "price":
            neg_price = (df["price"] < 0)
            if neg_price.any():
                report["errors"].append(
                    f"'price' negativo in {neg_price.sum()} righe"
                )

    return df, report


# ── Helper: asset_class ───────────────────────────────────────

def _normalize_asset_class(df: pd.DataFrame, report: dict) -> tuple:
    """
    Normalizza asset_class in minuscolo.
    Valori sconosciuti → None (yfinance li inferirà dopo).
    """
    df["asset_class"] = df["asset_class"].astype(str).str.strip().str.lower()
    df["asset_class"] = df["asset_class"].replace({"nan": None, "none": None, "": None})

    unknown = df[
        df["asset_class"].notna() &
        ~df["asset_class"].isin(VALID_ASSET_CLASS)
    ]["asset_class"].unique()

    if len(unknown) > 0:
        report["warnings"].append(
            f"asset_class non riconosciuta: {unknown.tolist()} → impostata a None "
            f"(yfinance proverà a inferirla). Valori validi: {VALID_ASSET_CLASS}"
        )
        df.loc[~df["asset_class"].isin(VALID_ASSET_CLASS), "asset_class"] = None

    return df, report


# ── Helper: dividend edge case ────────────────────────────────

def _fix_dividend_quantity(df: pd.DataFrame, report: dict) -> tuple:
    """
    Normalizza i dividendi:
    - Se tx_type='dividend' e quantity=1 → probabilmente l'utente ha messo
      l'importo totale in price. Impostiamo quantity=0 e lasciamo price.
    - Se tx_type='dividend' e quantity>1 → warning: potrebbe essere errato.
    """
    div_mask = df["tx_type"] == "dividend"

    # quantity=1 su dividendo → fix automatico
    div_qty1 = div_mask & (df["quantity"] == 1)
    if div_qty1.any():
        df.loc[div_qty1, "quantity"] = 0.0
        report["fixes"].append(
            f"{div_qty1.sum()} righe dividend con quantity=1 normalizzate a 0 "
            f"(price interpretato come importo totale)"
        )

    # quantity>1 su dividendo → warning
    div_qty_big = div_mask & (df["quantity"] > 1)
    if div_qty_big.any():
        report["warnings"].append(
            f"{div_qty_big.sum()} righe dividend con quantity > 1 — "
            f"verifica che 'price' sia l'importo per azione, non il totale"
        )

    return df, report


# ── Pretty print report ───────────────────────────────────────

def print_report(report: dict) -> None:
    """Stampa il report di validazione in modo leggibile."""
    print("\n" + "="*60)
    print("  VALIDATION REPORT")
    print("="*60)

    if report["errors"]:
        print(f"\n🔴 ERRORI BLOCCANTI ({len(report['errors'])}):")
        for e in report["errors"]:
            print(f"   • {e}")

    if report["warnings"]:
        print(f"\n🟡 WARNING ({len(report['warnings'])}):")
        for w in report["warnings"]:
            print(f"   • {w}")

    if report["fixes"]:
        print(f"\n🟢 FIX APPLICATI ({len(report['fixes'])}):")
        for f in report["fixes"]:
            print(f"   • {f}")

    if report.get("stats"):
        s = report["stats"]
        print(f"\n📊 STATISTICHE:")
        print(f"   Righe valide:  {s['total_rows']}")
        print(f"   Transazioni:   {s['tx_type_counts']}")
        print(f"   Asset class:   {s['asset_classes']}")
        print(f"   Ticker:        {s['tickers']}")
        print(f"   Valute:        {s['currencies']}")
        print(f"   Intervallo:    {s['date_range'][0]}  →  {s['date_range'][1]}")
        print(f"   Valido:        {'✅ SÌ' if s['is_valid'] else '❌ NO'}")

    print("="*60 + "\n")