# ============================================================
# core/streaming_engine.py
# ARGUS — Risk Analytics Platform
# Real-Time Data Streaming, In-Memory Ring Buffer & Order Flow Engine
# Features:
#   - High-Frequency MarketTick Data Structure
#   - Thread-Safe Fixed-Capacity Ring Buffer (O(1) Ingestion)
#   - Real-Time VWAP, Rolling Volatility & Order Flow Imbalance (OFI)
#   - Level-2 Order Book Depth Simulator (Microprice & Book Imbalance)
#   - Real-Time Tick Streamer & Subscription Hub
# ============================================================

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


@dataclass
class MarketTick:
    """Rappresentazione di un singolo tick di mercato ad alta frequenza."""
    timestamp: datetime
    ticker: str
    price: float
    size: float
    bid: float
    ask: float
    volume: float = 0.0

    @property
    def spread(self) -> float:
        return max(0.0, self.ask - self.bid)

    @property
    def mid_price(self) -> float:
        return (self.bid + self.ask) / 2.0 if (self.bid > 0 and self.ask > 0) else self.price


class TickRingBuffer:
    """
    Ring buffer circolare thread-safe con capacità fissa a prestazioni O(1).
    Mantiene gli ultimi N tick in memoria per analisi intraday a bassissima latenza.
    """
    def __init__(self, capacity: int = 1000, ticker: str = "DEFAULT"):
        self.capacity = max(10, capacity)
        self.ticker = ticker
        self._lock = threading.Lock()
        self._buffer: List[MarketTick] = []
        self._head = 0
        self._count = 0

    def append(self, tick: MarketTick) -> None:
        """Inserisce un nuovo tick nel ring buffer con sovrascrittura automatica FIFO."""
        with self._lock:
            if len(self._buffer) < self.capacity:
                self._buffer.append(tick)
            else:
                self._buffer[self._head] = tick
            self._head = (self._head + 1) % self.capacity
            self._count += 1

    def to_dataframe(self) -> pd.DataFrame:
        """Restituisce i tick ordinati cronologicamente come pandas DataFrame."""
        with self._lock:
            if not self._buffer:
                return pd.DataFrame(columns=["timestamp", "ticker", "price", "size", "bid", "ask", "volume"])
            
            if len(self._buffer) < self.capacity:
                ordered = list(self._buffer)
            else:
                # Riordina dal punto di testa
                ordered = self._buffer[self._head:] + self._buffer[:self._head]

        data = [{
            "timestamp": t.timestamp,
            "ticker": t.ticker,
            "price": t.price,
            "size": t.size,
            "bid": t.bid,
            "ask": t.ask,
            "volume": t.volume,
            "spread": t.spread,
            "mid_price": t.mid_price
        } for t in ordered]
        return pd.DataFrame(data)

    def compute_vwap(self) -> float:
        """Calcola il Volume-Weighted Average Price (VWAP) sui tick presenti nel buffer."""
        df = self.to_dataframe()
        if df.empty or df["size"].sum() <= 0:
            return 0.0
        return float((df["price"] * df["size"]).sum() / df["size"].sum())

    def compute_order_flow_imbalance(self) -> float:
        """
        Calcola l'Order Flow Imbalance (OFI) standard di Cont et al. (2014):
        Misura la pressione netta acquirente/venditrice sul book.
        """
        df = self.to_dataframe()
        if len(df) < 2:
            return 0.0

        ofi = 0.0
        for i in range(1, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i - 1]

            # Variazione lato Bid
            if curr["bid"] > prev["bid"]:
                delta_bid = curr["size"]
            elif curr["bid"] == prev["bid"]:
                delta_bid = curr["size"] - prev["size"]
            else:
                delta_bid = -prev["size"]

            # Variazione lato Ask
            if curr["ask"] < prev["ask"]:
                delta_ask = curr["size"]
            elif curr["ask"] == prev["ask"]:
                delta_ask = curr["size"] - prev["size"]
            else:
                delta_ask = -prev["size"]

            ofi += (delta_bid - delta_ask)

        return float(ofi)

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Restituisce un riepilogo in tempo reale di prezzo, VWAP, volatilità rolling e spread."""
        df = self.to_dataframe()
        if df.empty:
            return {
                "ticker": self.ticker,
                "count": 0,
                "last_price": 0.0,
                "vwap": 0.0,
                "mean_spread": 0.0,
                "rolling_volatility_pct": 0.0,
                "order_flow_imbalance": 0.0
            }

        last_p = float(df["price"].iloc[-1])
        vwap = self.compute_vwap()
        mean_spread = float(df["spread"].mean())
        
        # Volatilità rolling sui rendimenti percentuali dei tick
        returns = df["price"].pct_change().dropna()
        rolling_vol = float(returns.std() * np.sqrt(252 * 390 * 60) * 100.0) if len(returns) > 2 else 0.0

        return {
            "ticker": self.ticker,
            "count": len(df),
            "last_price": round(last_p, 4),
            "vwap": round(vwap, 4),
            "mean_spread": round(mean_spread, 4),
            "rolling_volatility_pct": round(rolling_vol, 2),
            "order_flow_imbalance": round(self.compute_order_flow_imbalance(), 2),
            "min_price": round(float(df["price"].min()), 4),
            "max_price": round(float(df["price"].max()), 4),
            "total_volume": round(float(df["size"].sum()), 2)
        }


@dataclass
class OrderBookLevel:
    price: float
    size: float
    order_count: int = 1


@dataclass
class OrderBookL2:
    """Rappresentazione snapshot di un Order Book Level-2 (Top 5 Bids & Asks)."""
    ticker: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0.0

    @property
    def spread(self) -> float:
        return max(0.0, self.best_ask - self.best_bid)

    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2.0 if (self.best_bid > 0 and self.best_ask > 0) else 0.0

    def compute_microprice(self) -> float:
        """
        Calcola il Microprice istituzionale (Stoikov 2018):
        Prezzo fair ponderato per i volumi al Best Bid e Best Ask.
        P_micro = (BestBid * AskVolume + BestAsk * BidVolume) / (BidVolume + AskVolume)
        """
        if not self.bids or not self.asks:
            return self.mid_price
        
        q_bid = self.bids[0].size
        q_ask = self.asks[0].size
        
        if (q_bid + q_ask) <= 0:
            return self.mid_price
            
        return float((self.best_bid * q_ask + self.best_ask * q_bid) / (q_bid + q_ask))

    def compute_book_imbalance(self) -> float:
        """
        Calcola il Book Depth Imbalance Ratio (-1.0 a +1.0):
        (Total Bid Volume - Total Ask Volume) / (Total Bid Volume + Total Ask Volume)
        """
        total_bid_vol = sum(b.size for b in self.bids)
        total_ask_vol = sum(a.size for a in self.asks)
        total_vol = total_bid_vol + total_ask_vol
        if total_vol <= 0:
            return 0.0
        return float((total_bid_vol - total_ask_vol) / total_vol)


# ── GENERATORE SINTETICO STREAMING PER SIMULAZIONE LIVE ────────────

def generate_mock_streaming_ticks(
    ticker: str = "AAPL",
    initial_price: float = 185.0,
    num_ticks: int = 50,
    volatility: float = 0.002,
    spread_pct: float = 0.0005
) -> List[MarketTick]:
    """Genera una sequenza realistica di tick ad alta frequenza per simulazione e test."""
    ticks = []
    curr_p = initial_price
    np.random.seed(42)

    for i in range(num_ticks):
        shock = np.random.normal(0, volatility * curr_p)
        curr_p = max(0.50, curr_p + shock)
        half_spread = (curr_p * spread_pct) / 2.0
        bid = curr_p - half_spread
        ask = curr_p + half_spread
        size = float(np.random.randint(10, 500))

        tick = MarketTick(
            timestamp=datetime.now(timezone.utc),
            ticker=ticker,
            price=round(curr_p, 4),
            size=size,
            bid=round(bid, 4),
            ask=round(ask, 4),
            volume=size
        )
        ticks.append(tick)

    return ticks
