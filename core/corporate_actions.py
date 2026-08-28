"""
ARGUS — Risk Analytics Platform
Core Module: Corporate Actions & Stock Split Engine
Gestione, rilevazione e rettifica contabile-fiscale di Stock Split, Reverse Split e Stock Dividend.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ── 1. TABELLA FALLBACK DI SPLIT STORICI NOTI ────────────────────────────────
# Formato: { "TICKER": [ {"date": "YYYY-MM-DD", "ratio": float, "desc": "10:1 Forward Split"}, ... ] }
KNOWN_HISTORICAL_SPLITS: Dict[str, List[Dict[str, Any]]] = {
    "NVDA": [
        {"date": "2024-06-10", "ratio": 10.0, "desc": "10:1 Forward Stock Split"},
        {"date": "2021-07-20", "ratio": 4.0, "desc": "4:1 Forward Stock Split"},
        {"date": "2007-09-11", "ratio": 1.5, "desc": "3:2 Forward Stock Split"},
        {"date": "2006-04-07", "ratio": 2.0, "desc": "2:1 Forward Stock Split"},
    ],
    "AAPL": [
        {"date": "2020-08-31", "ratio": 4.0, "desc": "4:1 Forward Stock Split"},
        {"date": "2014-06-09", "ratio": 7.0, "desc": "7:1 Forward Stock Split"},
        {"date": "2005-02-28", "ratio": 2.0, "desc": "2:1 Forward Stock Split"},
        {"date": "2000-06-21", "ratio": 2.0, "desc": "2:1 Forward Stock Split"},
    ],
    "TSLA": [
        {"date": "2022-08-25", "ratio": 3.0, "desc": "3:1 Forward Stock Split"},
        {"date": "2020-08-31", "ratio": 5.0, "desc": "5:1 Forward Stock Split"},
    ],
    "AMZN": [
        {"date": "2022-06-06", "ratio": 20.0, "desc": "20:1 Forward Stock Split"},
        {"date": "1999-09-02", "ratio": 2.0, "desc": "2:1 Forward Stock Split"},
        {"date": "1999-01-05", "ratio": 3.0, "desc": "3:1 Forward Stock Split"},
    ],
    "GOOGL": [
        {"date": "2022-07-18", "ratio": 20.0, "desc": "20:1 Forward Stock Split"},
        {"date": "2014-04-03", "ratio": 1.998, "desc": "Stock Dividend / Class C Split"},
    ],
    "GOOG": [
        {"date": "2022-07-18", "ratio": 20.0, "desc": "20:1 Forward Stock Split"},
    ],
    "META": [],
    "MSFT": [
        {"date": "2003-02-18", "ratio": 2.0, "desc": "2:1 Forward Stock Split"},
    ],
    "AVGO": [
        {"date": "2024-07-15", "ratio": 10.0, "desc": "10:1 Forward Stock Split"},
    ],
    "CMG": [
        {"date": "2024-06-26", "ratio": 50.0, "desc": "50:1 Forward Stock Split"},
    ],
    "WMT": [
        {"date": "2024-02-26", "ratio": 3.0, "desc": "3:1 Forward Stock Split"},
    ],
    "NFLX": [
        {"date": "2015-07-15", "ratio": 7.0, "desc": "7:1 Forward Stock Split"},
    ],
    "GE": [
        {"date": "2021-08-02", "ratio": 0.125, "desc": "1:8 Reverse Stock Split / Raggruppamento"},
    ],
    "C": [
        {"date": "2011-05-09", "ratio": 0.10, "desc": "1:10 Reverse Stock Split / Raggruppamento"},
    ],
    "NOVO-B.CO": [
        {"date": "2023-09-13", "ratio": 2.0, "desc": "2:1 Forward Stock Split"},
        {"date": "2014-01-02", "ratio": 5.0, "desc": "5:1 Forward Stock Split"},
    ],
    "ASML.AS": [
        {"date": "2000-05-04", "ratio": 3.0, "desc": "3:1 Forward Stock Split"},
    ],
    "BMW.DE": [
        {"date": "1999-05-10", "ratio": 3.0, "desc": "3:1 Forward Stock Split"},
    ],
    "ISP.MI": [
        {"date": "2018-06-18", "ratio": 1.0, "desc": "Conversione Azioni Risparmio / Fusione Categorie"},
    ]
}

# Cache in memoria per evitare chiamate ripetute a Yahoo Finance (TTL 24h)
_SPLIT_CACHE: Dict[str, Tuple[datetime, pd.Series]] = {}
_SPLIT_CACHE_TTL_SECONDS = 86400  # 24 ore


# ── 2. DOWNLOAD & FETCHING DEGLI SPLIT AZIONARI ──────────────────────────────

def fetch_stock_splits(ticker: str, start_date: Optional[str] = None) -> pd.Series:
    """
    Recupera la serie storica degli split azionari per un dato ticker.
    Utilizza la cache locale in memoria, le API di Yahoo Finance e la tabella di fallback nota.

    Returns
    -------
    pd.Series
        Serie indicizzata per data (pd.Timestamp) con i valori del rapporto di split (float).
        Es. 2024-06-10 -> 10.0 (10 nuove azioni per ogni 1 vecchia).
    """
    clean_tk = str(ticker).upper().strip()
    now = datetime.now()

    # 1. Controllo Cache in memoria
    if clean_tk in _SPLIT_CACHE:
        cached_time, cached_series = _SPLIT_CACHE[clean_tk]
        if (now - cached_time).total_seconds() < _SPLIT_CACHE_TTL_SECONDS:
            if start_date and not cached_series.empty:
                st_ts = pd.to_datetime(start_date)
                return cached_series[cached_series.index >= st_ts]
            return cached_series

    splits_series = pd.Series(dtype=float, index=pd.DatetimeIndex([]))

    # 2. Query live a Yahoo Finance via yfinance
    try:
        import yfinance as yf
        t_obj = yf.Ticker(clean_tk)
        splits_raw = t_obj.splits
        if splits_raw is not None and not splits_raw.empty:
            # Normalizzazione indice a timezone-naive date
            if hasattr(splits_raw.index, "tz") and splits_raw.index.tz is not None:
                splits_raw.index = splits_raw.index.tz_localize(None)
            splits_raw.index = pd.to_datetime(splits_raw.index).normalize()
            splits_series = splits_raw.astype(float)
            splits_series = splits_series[splits_series > 0.0]
    except Exception as ex:
        logger.debug(f"Errore download split per {clean_tk} da Yahoo Finance: {ex}")

    # 3. Integrazione / Fallback con tabella di split noti se yfinance è vuoto o offline
    if splits_series.empty and clean_tk in KNOWN_HISTORICAL_SPLITS:
        known = KNOWN_HISTORICAL_SPLITS[clean_tk]
        if known:
            dates = [pd.to_datetime(item["date"]).normalize() for item in known]
            ratios = [float(item["ratio"]) for item in known]
            splits_series = pd.Series(ratios, index=dates, dtype=float).sort_index()

    # Salva in cache
    _SPLIT_CACHE[clean_tk] = (now, splits_series)

    if start_date and not splits_series.empty:
        st_ts = pd.to_datetime(start_date)
        return splits_series[splits_series.index >= st_ts]

    return splits_series


# ── 3. RETTIFICA TRANSAZIONI PER CORPORATE ACTIONS ───────────────────────────

def _resolve_splits_for_ticker(
    ticker: str,
    grp: pd.DataFrame,
    auto_fetch: bool,
    custom_splits: Optional[Dict[str, List[Dict[str, Any]]]]
) -> List[Dict[str, Any]]:
    """Recupera ed unifica tutti gli split applicabili per un ticker (custom, live o espliciti)."""
    splits_to_apply = []
    min_date = grp["tx_date"].min()

    if custom_splits and ticker in custom_splits:
        for sp in custom_splits[ticker]:
            splits_to_apply.append({
                "date": pd.to_datetime(sp["date"]).normalize(),
                "ratio": float(sp["ratio"]),
                "desc": sp.get("desc", f"{sp['ratio']}:1 Split")
            })
    elif auto_fetch:
        sp_series = fetch_stock_splits(ticker, start_date=str(min_date.date()))
        for sp_date, ratio in sp_series.items():
            if ratio > 0.0 and ratio != 1.0:
                splits_to_apply.append({
                    "date": pd.to_datetime(sp_date).normalize(),
                    "ratio": float(ratio),
                    "desc": f"{ratio:.4g}:1 Split" if ratio > 1.0 else f"1:{1.0/ratio:.4g} Reverse Split"
                })

    explicit_splits = grp[grp["tx_type"].astype(str).str.lower().str.strip().isin([
        "split", "frazionamento", "raggruppamento", "reverse_split", "reverse split",
        "stock_split", "stock split", "stock_dividend", "fusione", "merger",
        "scambio", "scambio_azioni", "spinoff", "scissione"
    ])]
    for _, sp_row in explicit_splits.iterrows():
        sp_ratio = float(sp_row.get("quantity") or sp_row.get("price") or 1.0)
        if sp_ratio > 0.0 and sp_ratio != 1.0:
            sp_date = pd.to_datetime(sp_row["tx_date"]).normalize()
            if not any(abs((s["date"] - sp_date).days) <= 1 for s in splits_to_apply):
                splits_to_apply.append({
                    "date": sp_date,
                    "ratio": sp_ratio,
                    "desc": f"Transazione Corporate Action ({sp_ratio:.4g}:1)"
                })

    return sorted(splits_to_apply, key=lambda x: x["date"])


def _apply_split_to_dataframe(
    df: pd.DataFrame,
    ticker: str,
    sp: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Applica un singolo split su tutte le transazioni ante-split del ticker specificato."""
    sp_date = sp["date"]
    sp_ratio = sp["ratio"]
    valid_tx = ["buy", "sell", "dividend", "acquisto", "vendita", "b", "s", "cedola", "div"]

    mask = (
        (df["ticker"] == ticker) &
        (df["tx_date"] < sp_date) &
        (df["tx_type"].astype(str).str.lower().str.strip().isin(valid_tx))
    )
    affected_rows = df[mask]
    if affected_rows.empty:
        return None

    buys = affected_rows[affected_rows["tx_type"].isin(["buy", "acquisto", "b"])]
    total_qty_before = float(buys["quantity"].sum()) if not buys.empty else 0.0

    df.loc[mask, "quantity"] = df.loc[mask, "quantity"] * sp_ratio
    df.loc[mask, "price"] = df.loc[mask, "price"] / sp_ratio
    df.loc[mask, "split_factor_applied"] = df.loc[mask, "split_factor_applied"] * sp_ratio

    total_qty_after = total_qty_before * sp_ratio

    return {
        "ticker": ticker,
        "split_date": sp_date.strftime("%Y-%m-%d"),
        "split_ratio": sp_ratio,
        "split_type": "Forward Split" if sp_ratio > 1.0 else ("Reverse Split / Raggruppamento" if sp_ratio < 1.0 else "Fusione / Conversione"),
        "description": sp["desc"],
        "affected_lots_count": len(affected_rows),
        "shares_before": round(total_qty_before, 4),
        "shares_after": round(total_qty_after, 4),
        "cost_basis_invariant": True
    }


def adjust_transactions_for_splits(
    df_tx: pd.DataFrame,
    auto_fetch: bool = True,
    custom_splits: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Rettifica l'intero registro delle transazioni (df_tx) applicando i coefficienti di split.

    Regole Contabili & Fiscali (TUIR Art. 67 / IFRS):
    - Per ogni acquisto effettuato PRIMA della data di efficacia dello split:
        Q_rettificata = Q_originale * Split_Ratio
        P_rettificato = P_originale / Split_Ratio
    - Il Cost Basis totale del lotto rimane RIGOROSAMENTE INVARIANTE (Q * P = costante).
    - Eventuali commissioni restano invariate.
    - Se df_tx contiene già transazioni di tipo 'split', queste vengono elaborate
      oppure integrate per evitare doppi conteggi.

    Returns
    -------
    df_adjusted : pd.DataFrame
        Copia di df_tx con quantity e price rettificati per gli split azionari.
    audit_trail : List[Dict[str, Any]]
        Lista degli split rilevati ed applicati con i dettagli dei lotti impattati.
    """
    if df_tx is None or df_tx.empty:
        return df_tx, []

    df = df_tx.copy()
    if "tx_date" not in df.columns or "ticker" not in df.columns:
        return df, []

    df["tx_date"] = pd.to_datetime(df["tx_date"])
    audit_trail: List[Dict[str, Any]] = []

    # Se ci sono colonne originali, le conserviamo per tracciabilità
    if "quantity_orig" not in df.columns:
        df["quantity_orig"] = df["quantity"]
    if "price_orig" not in df.columns:
        df["price_orig"] = df["price"]
    if "split_factor_applied" not in df.columns:
        df["split_factor_applied"] = 1.0

    # Raggruppa per ticker
    for ticker, grp in df.groupby("ticker"):
        t_clean = str(ticker).upper().strip()
        if not t_clean:
            continue

        splits_to_apply = _resolve_splits_for_ticker(t_clean, grp, auto_fetch, custom_splits)
        for sp in splits_to_apply:
            audit_entry = _apply_split_to_dataframe(df, t_clean, sp)
            if audit_entry:
                audit_trail.append(audit_entry)

    # Rimuovi righe di corporate actions esplicite dal dataset di esecuzione FIFO per evitare duplicazioni
    corp_act_types = [
        "split", "frazionamento", "raggruppamento", "reverse_split", "reverse split",
        "stock_split", "stock split", "stock_dividend", "fusione", "merger",
        "scambio", "scambio_azioni", "spinoff", "scissione"
    ]
    df_clean_fifo = df[~df["tx_type"].astype(str).str.lower().str.strip().isin(corp_act_types)].copy()

    return df_clean_fifo, audit_trail


# ── 4. HELPER PER IL CONTROLLO DI CONSISTENZA DEL WACP ────────────────────────

def verify_split_accounting_invariance(
    qty_before: float,
    price_before: float,
    split_ratio: float
) -> Dict[str, Any]:
    """
    Verifica e certifica l'invarianza del Cost Basis secondo la formula:
    Cost_Basis = Q_orig * P_orig = Q_adj * P_adj
    """
    qty_after = qty_before * split_ratio
    price_after = price_before / split_ratio if split_ratio > 0 else price_before
    cost_before = qty_before * price_before
    cost_after = qty_after * price_after

    return {
        "qty_before": qty_before,
        "price_before": price_before,
        "cost_before": cost_before,
        "split_ratio": split_ratio,
        "qty_after": qty_after,
        "price_after": price_after,
        "cost_after": cost_after,
        "diff_cost": abs(cost_before - cost_after),
        "is_invariant": abs(cost_before - cost_after) < 1e-6
    }
