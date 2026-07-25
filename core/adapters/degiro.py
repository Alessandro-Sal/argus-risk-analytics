import pandas as pd
import numpy as np
import re
import os
import json
from pathlib import Path

def _get_config_file_path() -> Path:
    root_dir = Path(__file__).resolve().parent.parent.parent
    candidates = [
        root_dir / "config" / "config.json",
        Path.cwd() / "config" / "config.json",
        Path.cwd() / "config.json",
        root_dir / "config.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


# Dizionario essenziale per mappare gli ISIN europei più scambiati 
# e le azioni principali americane nei ticker riconosciuti da Yahoo Finance.
# In futuro questo potrebbe essere spostato in un file di configurazione o database.
ISIN_TO_TICKER = {
    # ETF Comuni
    "IE00B4L5Y983": "SWDA.MI",  # iShares Core MSCI World (su Borsa Italiana)
    "IE00B3RBWM25": "VWCE.MI",  # Vanguard FTSE All-World (su Borsa Italiana)
    "IE00B5BMR087": "CSSPX.MI", # iShares Core S&P 500 (su Borsa Italiana)
    "IE00B1XNHC34": "INRG.MI",  # iShares Global Clean Energy
    "LU1681043599": "AMEM.MI",  # Amundi MSCI Emerging Markets
    
    # Stock Popolari
    "US0378331005": "AAPL",
    "US5949181045": "MSFT",
    "US0231351067": "AMZN",
    "US88160R1014": "TSLA",
    "US02079K1079": "GOOGL",
    "US02079K3059": "GOOG",
    "US30303M1027": "META",
    "US67066G1040": "NVDA",
    "US01609W1027": "BABA",
    "DK0062498333": "NOV.DE"  # Novo Nordisk (Listing in EUR su Xetra/Tradegate)
}

def parse_degiro_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Legge il dataframe grezzo esportato da Degiro (Transazioni) 
    e lo formatta nello standard compatibile con il validator.py del progetto.
    """
    df = df_raw.copy()
    
    # Carica le mappature salvate in config.json
    saved_mappings = {}
    cfg_file = _get_config_file_path()
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                saved_mappings = config_data.get("ticker_mapping", {})
        except Exception:
            pass
            
    for k, v in saved_mappings.items():
        if k and v:
            ISIN_TO_TICKER[str(k).strip().upper()] = str(v).strip().upper()
    
    # 1. Normalizziamo i nomi delle colonne per supportare sia export in Italiano che in Inglese
    # Rimuoviamo gli spazi finali e mettiamo minuscolo
    df.columns = df.columns.str.strip().str.lower()
    
    # Degiro esporta file con molte colonne "valuta" (currency), rendendo i nomi duplicati.
    # Pandas li rinomina in valuta, valuta.1, valuta.2 ecc.
    
    # Trova i nomi effettivi delle colonne usate nel CSV di Degiro
    date_col = next((c for c in df.columns if c in ["data", "date"]), None)
    product_col = next((c for c in df.columns if c in ["prodotto", "product"]), None)
    isin_col = next((c for c in df.columns if "isin" in c), None)
    qty_col = next((c for c in df.columns if "quantit" in c or "quantity" in c), None)
    price_col = next((c for c in df.columns if c in ["prezzo", "price", "quotazione"]), None)
    
    # La valuta del prezzo è di solito la prima colonna "valuta" o "currency" dopo "prezzo"
    # (in italiano spesso è un'unnamed column a fianco di Quotazione)
    currency_col = None
    if price_col:
        price_idx = df.columns.get_loc(price_col)
        if price_idx + 1 < len(df.columns):
            currency_col = df.columns[price_idx + 1]
            
    # Le fees (commissioni)
    fees_col = next((c for c in df.columns if "costi di transazione" in c or "commissioni" in c or "transaction costs" in c or "fee" in c), None)
    
    if not all([date_col, product_col, isin_col]):
        raise ValueError("Il file non sembra un export valido delle Transazioni Degiro. Mancano colonne chiave (Data, Prodotto, ISIN).")

    # Inizializziamo il dataframe finale
    df_out = pd.DataFrame()
    
    # Estrazione Data
    df_out["tx_date"] = df[date_col]
    
    import requests
    import time

    def resolve_isin(isin):
        isin = str(isin).strip().upper()
        if isin in ISIN_TO_TICKER:
            return ISIN_TO_TICKER[isin]
        
        # Se non è in cache, cercalo su Yahoo Finance
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if "quotes" in data and len(data["quotes"]) > 0:
                    # Prendi il primo simbolo trovato
                    symbol = data["quotes"][0]["symbol"]
                    ISIN_TO_TICKER[isin] = symbol
                    
                    # Salva persistentemente nel file config.json
                    try:
                        config_data = {}
                        cfg_file = _get_config_file_path()
                        if cfg_file.exists():
                            with open(cfg_file, "r", encoding="utf-8") as f:
                                config_data = json.load(f)
                        if "ticker_mapping" not in config_data:
                            config_data["ticker_mapping"] = {}
                        config_data["ticker_mapping"][isin] = symbol
                        cfg_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(cfg_file, "w", encoding="utf-8") as f:
                            json.dump(config_data, f, indent=4)
                    except Exception:
                        pass
                        
                    time.sleep(0.1) # Evita rate limit
                    return symbol
        except Exception:
            pass
            
        return isin # fallback

        
    df_out["ticker"] = df[isin_col].apply(resolve_isin)
    
    # Parsing delle quantità e prezzi (possono contenere virgole al posto dei punti in IT)
    def clean_numeric(series):
        if series is None or series.empty:
            return pd.Series([0.0]*len(df))
        return pd.to_numeric(series.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)

    qty_series = clean_numeric(df[qty_col]) if qty_col else pd.Series([0.0]*len(df))
    price_series = clean_numeric(df[price_col]) if price_col else pd.Series([0.0]*len(df))
    fees_series = clean_numeric(df[fees_col]) if fees_col else pd.Series([0.0]*len(df))
    
    # Determiniamo il tx_type
    # Degiro mette le vendite come quantità negative
    conditions = [
        qty_series > 0,
        qty_series < 0,
        df[product_col].str.lower().str.contains("dividend|dividendo", na=False)
    ]
    choices = ["buy", "sell", "dividend"]
    df_out["tx_type"] = np.select(conditions, choices, default="unknown")
    
    # Rimuoviamo le righe non identificabili
    mask_valid = df_out["tx_type"] != "unknown"
    df_out = df_out[mask_valid].copy()
    qty_series = qty_series[mask_valid]
    price_series = price_series[mask_valid]
    fees_series = fees_series[mask_valid]
    df = df[mask_valid].copy()
    
    # Normalizziamo le quantità (le vendite nel nostro sistema usano tx_type='sell' e quantità positiva)
    df_out["quantity"] = qty_series.abs()
    
    df_out["price"] = price_series
    
    if currency_col:
        df_out["currency"] = df[currency_col].astype(str).str.strip().str.upper()
    else:
        df_out["currency"] = "EUR" # Default fallback
        
    df_out["fees"] = fees_series.abs() # Fees assolute
    
    df_out["asset_class"] = None # Verrà dedotto da yfinance se possibile
    
    # Nelle note salviamo il nome del prodotto originale di Degiro per debugging e chiarezza
    df_out["notes"] = df[product_col]
    
    return df_out
