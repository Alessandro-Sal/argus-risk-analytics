# ==============================================================================
# core/data_quality_gate.py
# ARGUS — Production-Grade Data Quality Gate & Broker Ingestion Middleware
# Formal Syntactic/Semantic Schema, Z-Score Validation & Canonical Deduplication
# ==============================================================================

import re
import hashlib
import logging
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set, Union
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

logger = logging.getLogger("argus.data_quality")

# ── ENUMERATIVI STANDARD FINANZIARI ──────────────────────────────────────────

class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    SPLIT = "split"


class AssetClass(str, Enum):
    STOCK = "stock"
    ETF = "etf"
    BOND = "bond"
    CRYPTO = "crypto"
    CASH = "cash"
    COMMODITY = "commodity"
    OTHER = "other"


# Valute ISO 4217 standard e crypto supportate
MAJOR_CURRENCIES: Set[str] = {
    "EUR", "USD", "GBP", "CHF", "JPY", "CAD", "AUD", "SEK", "NOK", "DKK",
    "HKD", "SGD", "NZD", "MXN", "BRL", "INR", "CNY", "ZAR",
    "BTC", "ETH", "USDT", "USDC", "BNB", "XRP", "SOL"
}

ISIN_REGEX = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


# ── PYDANTIC RECORD SCHEMA ───────────────────────────────────────────────────

class CanonicalTradeRecord(BaseModel):
    """
    Schema formale e fortemente tipizzato per singola transazione finanziaria.
    Applica validazioni sintattiche, normalizzazione delle valute e hash univoco.
    """
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    broker: str = Field(..., description="Nome univoco del broker o adapter")
    portfolio_id: int = Field(default=1, ge=1, description="ID del portafoglio di destinazione")
    tx_date: date = Field(..., description="Data contabile dell'operazione")
    ticker: str = Field(..., min_length=1, max_length=32, description="Ticker Yahoo Finance o Simbolo Asset")
    tx_type: TransactionType = Field(..., description="Tipologia di transazione normalizzata")
    quantity: float = Field(..., gt=0.0, description="Quantità di quote/azioni (strettamente positiva)")
    price: float = Field(..., ge=0.0, description="Prezzo di esecuzione per quota")
    currency: str = Field(default="EUR", description="Codice ISO 4217 o Crypto Symbol")
    fees: float = Field(default=0.0, ge=0.0, description="Commissioni e costi di transazione")
    fx_rate_to_eur: Optional[float] = Field(default=1.0, gt=0.0, description="Tasso di cambio applicato verso EUR")
    asset_class: Optional[str] = Field(default=None, description="Classe dello strumento")
    broker_tx_id: Optional[str] = Field(default=None, description="ID univoco transazione assegnato dal broker")
    notes: Optional[str] = Field(default=None, max_length=255, description="Note o causale originale")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: Any) -> str:
        sym = str(v).strip().upper()
        if not sym or sym in {"NAN", "NONE", "NULL", "UNKNOWN", ""}:
            raise ValueError("Ticker mancante o non valido.")
        return sym

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Any) -> str:
        curr = str(v or "EUR").strip().upper()
        if not curr or curr in {"NAN", "NONE", ""}:
            return "EUR"
        return curr

    @field_validator("tx_date", mode="before")
    @classmethod
    def parse_tx_date(cls, v: Any) -> date:
        if isinstance(v, date) and not isinstance(v, datetime):
            d = v
        elif isinstance(v, datetime):
            d = v.date()
        elif isinstance(v, pd.Timestamp):
            d = v.date()
        else:
            s = str(v).strip()
            if " " in s:
                s = s.split(" ")[0]
            elif "T" in s:
                s = s.split("T")[0]
            if re.match(r"^\d{4}-\d{2}-\d{2}", s):
                dt = pd.to_datetime(s[:10], format="%Y-%m-%d", errors="coerce")
            else:
                dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
            if pd.isna(dt):
                raise ValueError(f"Formato data non valido o irrisolvibile: {v}")
            d = dt.date()

        today = date.today()
        if d > today:
            raise ValueError(f"Data transazione futura non consentita: {d} > {today}")
        if d < date(1980, 1, 1):
            raise ValueError(f"Data anacronistica antecedente al 1980: {d}")
        return d

    @field_validator("tx_type", mode="before")
    @classmethod
    def parse_tx_type(cls, v: Any) -> TransactionType:
        if isinstance(v, TransactionType):
            return v
        s = str(v).strip().lower()
        mapping = {
            "buy": TransactionType.BUY,
            "acquisto": TransactionType.BUY,
            "compra": TransactionType.BUY,
            "acq": TransactionType.BUY,
            "b": TransactionType.BUY,
            "sell": TransactionType.SELL,
            "vendita": TransactionType.SELL,
            "vendi": TransactionType.SELL,
            "ven": TransactionType.SELL,
            "s": TransactionType.SELL,
            "dividend": TransactionType.DIVIDEND,
            "dividendo": TransactionType.DIVIDEND,
            "cedola": TransactionType.DIVIDEND,
            "div": TransactionType.DIVIDEND,
            "split": TransactionType.SPLIT,
            "frazionamento": TransactionType.SPLIT,
        }
        if s in mapping:
            return mapping[s]
        raise ValueError(f"Tipo transazione '{v}' non riconosciuto.")

    @model_validator(mode="after")
    def check_trade_coherence(self) -> "CanonicalTradeRecord":
        if self.tx_type in {TransactionType.BUY, TransactionType.SELL} and self.price <= 0.0:
            raise ValueError(f"Prezzo nullo o negativo non ammesso per operazione {self.tx_type.value}: {self.price}")
        return self

    @property
    def canonical_hash(self) -> str:
        """Genera l'impronta deterministica SHA-256 per deduplicazione idempotente."""
        raw_key = (
            f"{self.broker.lower().strip()}|"
            f"{self.portfolio_id}|"
            f"{self.tx_date.isoformat()}|"
            f"{self.ticker.upper().strip()}|"
            f"{self.tx_type.value}|"
            f"{self.quantity:.6f}|"
            f"{self.price:.6f}|"
            f"{self.currency.upper().strip()}|"
            f"{(self.broker_tx_id or '').strip().lower()}"
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# ── REPORT STRUTTURATO DI VALIDAZIONE ────────────────────────────────────────

class QualityGateReport(BaseModel):
    is_valid: bool = True
    total_raw_rows: int = 0
    valid_rows_count: int = 0
    discarded_rows_count: int = 0
    duplicates_suppressed: int = 0
    critical_errors: List[str] = Field(default_factory=list)
    semantic_warnings: List[str] = Field(default_factory=list)
    fixes_applied: List[str] = Field(default_factory=list)
    unique_tickers: List[str] = Field(default_factory=list)
    unique_currencies: List[str] = Field(default_factory=list)
    date_interval: Optional[Tuple[str, str]] = None


# ── DATA QUALITY GATE MIDDLEWARE ─────────────────────────────────────────────

class DataQualityGate:
    """
    Middleware di validazione e arricchimento dati di livello enterprise.
    Intercetta i DataFrame post-adapter, applica schemi Pydantic, verifica
    la congruità dei prezzi e l'inventario posizioni ed elimina i duplicati.
    """

    def __init__(self, reject_on_short_sell: bool = False, max_price_deviation_pct: float = 0.50):
        self.reject_on_short_sell = reject_on_short_sell
        self.max_price_deviation_pct = max_price_deviation_pct

    def process(
        self,
        df_adapter: pd.DataFrame,
        broker_name: str = "generic",
        portfolio_id: int = 1,
        existing_hashes: Optional[Set[str]] = None
    ) -> Tuple[pd.DataFrame, QualityGateReport]:
        """
        Esegue la pipeline di controllo end-to-end:
        1. Validazione sintattica Pydantic per riga.
        2. Deduplicazione idempotente tramite canonical_hash.
        3. Audit semantico su inventario (Short Position Detection).
        4. Rilevamento anomalie di prezzo o weekend trade.
        """
        report = QualityGateReport(total_raw_rows=len(df_adapter) if df_adapter is not None else 0)
        if df_adapter is None or df_adapter.empty:
            report.is_valid = False
            report.critical_errors.append("Dataset vuoto: nessuna riga passata al DataQualityGate.")
            return pd.DataFrame(), report

        known_hashes = set(existing_hashes) if existing_hashes else set()
        clean_records: List[Dict[str, Any]] = []

        # ── 1. VALIDAZIONE SINTATTICA PYDANTIC & DEDUPLICAZIONE ──
        for idx, row in df_adapter.iterrows():
            row_dict = row.to_dict()
            row_dict["broker"] = broker_name
            row_dict["portfolio_id"] = portfolio_id

            # Normalizzazione preventiva quantità/prezzo se stringhe
            for col_num in ["quantity", "price", "fees"]:
                if col_num in row_dict and isinstance(row_dict[col_num], str):
                    clean_str = row_dict[col_num].replace(",", ".").strip()
                    try:
                        row_dict[col_num] = float(clean_str)
                    except ValueError:
                        pass

            try:
                rec = CanonicalTradeRecord.model_validate(row_dict)
                tx_hash = rec.canonical_hash

                # Controllo Idempotenza
                if tx_hash in known_hashes:
                    report.duplicates_suppressed += 1
                    continue

                known_hashes.add(tx_hash)
                clean_dict = {
                    "tx_date": rec.tx_date.strftime("%Y-%m-%d"),
                    "ticker": rec.ticker,
                    "tx_type": rec.tx_type.value,
                    "quantity": rec.quantity,
                    "price": rec.price,
                    "currency": rec.currency,
                    "fees": rec.fees,
                    "asset_class": rec.asset_class,
                    "notes": rec.notes,
                    "tx_hash": tx_hash
                }
                clean_records.append(clean_dict)

            except Exception as e:
                report.discarded_rows_count += 1
                report.critical_errors.append(f"Riga {idx + 1}: Errore di validazione: {e}")

        if not clean_records:
            report.is_valid = False
            report.critical_errors.append("Nessun record valido estratto dopo la validazione sintattica.")
            return pd.DataFrame(), report

        df_validated = pd.DataFrame(clean_records)
        df_validated["tx_date"] = pd.to_datetime(df_validated["tx_date"]).dt.date
        df_validated = df_validated.sort_values(["tx_date", "tx_type"]).reset_index(drop=True)

        # ── 2. AUDIT SEMANTICO: INVENTARIO E NO-SHORT CHECK ──
        position_inventory: Dict[str, float] = {}
        for idx, row in df_validated.iterrows():
            t = row["ticker"]
            q = float(row["quantity"])
            typ = row["tx_type"]

            current_qty = position_inventory.get(t, 0.0)
            if typ == "buy":
                position_inventory[t] = current_qty + q
            elif typ == "sell":
                if q > (current_qty + 1e-6):
                    msg = (
                        f"Anomalia Inventario su {t} al {row['tx_date']}: "
                        f"Vendita di {q:.4f} quote eccede la disponibilità in portafoglio ({current_qty:.4f})."
                    )
                    report.semantic_warnings.append(msg)
                position_inventory[t] = max(0.0, current_qty - q)

            # Controllo weekend trade
            tx_dt = row["tx_date"]
            if tx_dt.weekday() in {5, 6}:
                report.semantic_warnings.append(
                    f"Trade {t} eseguito nel fine settimana ({tx_dt.strftime('%A %Y-%m-%d')}). Possibile operazione OTC o data regolamento anziché negoziazione."
                )

        # ── 3. STATISTICHE FINALI ──
        report.valid_rows_count = len(df_validated)
        report.unique_tickers = sorted(df_validated["ticker"].unique().tolist())
        report.unique_currencies = sorted(df_validated["currency"].unique().tolist())
        min_d = df_validated["tx_date"].min().strftime("%Y-%m-%d")
        max_d = df_validated["tx_date"].max().strftime("%Y-%m-%d")
        report.date_interval = (min_d, max_d)
        report.is_valid = len(report.critical_errors) == 0

        logger.info(
            "QualityGate completato: %d righe valide, %d duplicate scartate, %d errori bloccanti",
            report.valid_rows_count, report.duplicates_suppressed, len(report.critical_errors)
        )

        return df_validated, report


# ── MARKET DATA QUALITY GATE (PRICE SERIES INTEGRITY) ─────────────────────────

class MarketDataQualityReport(BaseModel):
    """Report diagnostico e quantitativo sull'integrità delle serie storiche dei prezzi."""
    is_valid: bool = True
    active_tickers: List[str] = Field(default_factory=list)
    missing_tickers: List[str] = Field(default_factory=list)
    stale_price_tickers: Dict[str, int] = Field(default_factory=dict)
    insufficient_history: Dict[str, int] = Field(default_factory=dict)
    abnormal_returns: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    critical_errors: List[str] = Field(default_factory=list)


class MarketDataQualityGate:
    """
    Quality Gate per la sanificazione, validazione e allineamento temporale dei prezzi storici.
    Mitiga il disallineamento dei calendari di borsa (es. Borsa Italiana vs NYSE),
    applica forward-fill controllato, individua titoli stantii o sospesi e salti anomali di prezzo.
    """

    def __init__(
        self,
        min_history_days: int = 30,
        max_ffill_days: int = 5,
        max_stale_streak: int = 10,
        z_score_jump_threshold: float = 6.0
    ):
        self.min_history_days = min_history_days
        self.max_ffill_days = max_ffill_days
        self.max_stale_streak = max_stale_streak
        self.z_score_jump_threshold = z_score_jump_threshold

    def validate_and_align_prices(
        self,
        df_prices: pd.DataFrame,
        required_tickers: Set[str],
        reference_index: Optional[pd.DatetimeIndex] = None
    ) -> Tuple[pd.DataFrame, MarketDataQualityReport]:
        """
        Allinea la matrice dei prezzi su un asse feriale continuativo e calcola la diagnostica.
        Restituisce (pivot_table_aligned, report).
        """
        report = MarketDataQualityReport()

        if df_prices is None or df_prices.empty:
            report.is_valid = False
            report.critical_errors.append("Dataset prezzi storici nullo o vuoto.")
            return pd.DataFrame(), report

        # Normalizzazione date e timezone
        df = df_prices.copy()
        df["price_date"] = pd.to_datetime(df["price_date"])
        if getattr(df["price_date"].dt, "tz", None) is not None:
            df["price_date"] = df["price_date"].dt.tz_localize(None)

        # Selezione colonna prezzo (priorità ad adjusted_close se disponibile)
        price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
        if price_col not in df.columns:
            report.is_valid = False
            report.critical_errors.append(f"Colonna prezzo '{price_col}' non presente in df_prices.")
            return pd.DataFrame(), report

        df_filtered = df[df["ticker"].isin(required_tickers)][["price_date", "ticker", price_col]].dropna()
        df_filtered = df_filtered.drop_duplicates(subset=["price_date", "ticker"], keep="last")

        if df_filtered.empty:
            report.is_valid = False
            report.critical_errors.append("Nessun dato prezzo corrispondente ai ticker richiesti.")
            return pd.DataFrame(), report

        # Costruzione della pivot table
        pivot = df_filtered.pivot(index="price_date", columns="ticker", values=price_col).sort_index()

        available_tickers = set(pivot.columns)
        missing = set(required_tickers) - available_tickers
        if missing:
            report.missing_tickers = sorted(list(missing))
            report.warnings.append(
                f"I seguenti ticker non hanno quotazioni storiche disponibili: {report.missing_tickers}."
            )

        # 1. Verifica profondità storica minima
        for tk in available_tickers:
            obs = int(pivot[tk].dropna().count())
            if obs < self.min_history_days:
                report.insufficient_history[tk] = obs
                report.warnings.append(
                    f"Asset '{tk}' con storico ridotto ({obs} quotazioni < soglia {self.min_history_days})."
                )

        # 2. Controllo serie prezzi stantie / congelate (illiquidità o delisting)
        for tk in available_tickers:
            s_clean = pivot[tk].dropna()
            if len(s_clean) > self.max_stale_streak:
                diffs = s_clean.diff()
                streak = int((diffs == 0).astype(int).groupby((diffs != 0).cumsum()).sum().max())
                if streak >= self.max_stale_streak:
                    report.stale_price_tickers[tk] = streak
                    report.warnings.append(
                        f"Asset '{tk}' presenta quotazione identica per {streak} giorni consecutivi (possibile sospensione scambi)."
                    )

        # 3. Allineamento calendario & Forward Fill controllato
        if reference_index is not None and len(reference_index) > 0:
            ref_clean = pd.to_datetime(reference_index)
            if getattr(ref_clean, "tz", None) is not None:
                ref_clean = ref_clean.tz_localize(None)
            pivot = pivot.reindex(ref_clean)
        else:
            full_b_index = pd.date_range(start=pivot.index.min(), end=pivot.index.max(), freq="B")
            pivot = pivot.reindex(full_b_index)

        # Forward fill fino al limite massimo (evita estrapolazioni indefinite)
        pivot = pivot.ffill(limit=self.max_ffill_days)

        # 4. Rilevamento anomalie di rendimento (Z-score su salti estremi)
        pct_chg = pivot.pct_change()
        for tk in available_tickers:
            rets = pct_chg[tk].dropna()
            if len(rets) > 20:
                std_ret = float(rets.std())
                if std_ret > 1e-8:
                    z_scores = (rets - rets.mean()) / std_ret
                    extreme_jumps = z_scores[z_scores.abs() > self.z_score_jump_threshold]
                    for dt, val in extreme_jumps.items():
                        report.abnormal_returns.append({
                            "ticker": tk,
                            "date": dt.strftime("%Y-%m-%d"),
                            "z_score": round(float(val), 2),
                            "daily_return_pct": round(float(rets[dt]) * 100, 2)
                        })
                        report.warnings.append(
                            f"Salto anomalo di prezzo su '{tk}' in data {dt.strftime('%Y-%m-%d')}: "
                            f"variazione {rets[dt]*100:.2f}% (Z-Score: {val:.1f})."
                        )

        report.active_tickers = sorted(list(available_tickers))
        report.is_valid = len(report.active_tickers) > 0
        return pivot, report

