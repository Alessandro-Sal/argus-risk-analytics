# ============================================================
# core/technical_analysis.py
# ARGUS — Risk Analytics & BI Platform
# Technical Analysis, Volume Profile & Confluence Signal Engine
# ============================================================

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple


def compute_technical_indicators(df_prices: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcola un set completo di indicatori tecnici quantitativi secondo le definizioni standard istituzionali (Wilder smoothing).
    Richiede colonne: 'close', facoltativi 'open', 'high', 'low', 'volume'.
    """
    if df_prices.empty or "close" not in df_prices.columns:
        return {}

    df = df_prices.copy().sort_index()
    close = df["close"].astype(float)
    high = df["high"].astype(float) if "high" in df.columns else close
    low = df["low"].astype(float) if "low" in df.columns else close
    open_p = df["open"].astype(float) if "open" in df.columns else close
    volume = df["volume"].astype(float) if "volume" in df.columns else pd.Series(0, index=df.index)

    # 1. Medie Mobili (EMA 20, EMA 50, SMA 200)
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    sma200 = close.rolling(window=min(200, len(close)), min_periods=1).mean()

    # Trend Cross Status
    golden_cross = (ema50.iloc[-1] > sma200.iloc[-1]) if len(sma200) > 0 else False
    ema20_gt_ema50 = (ema20.iloc[-1] > ema50.iloc[-1]) if len(ema50) > 0 else False

    # 2. MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    # 3. RSI 14 (Wilder Exponential Smoothing: alpha = 1/14)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    rsi14 = 100.0 - (100.0 / (1.0 + rs))
    rsi_latest = float(rsi14.iloc[-1]) if not rsi14.empty else 50.0

    rsi_status = "Neutro"
    if rsi_latest >= 70:
        rsi_status = "Ipercomprato (>= 70)"
    elif rsi_latest <= 30:
        rsi_status = "Ipervenduto (<= 30)"

    # 4. Bande di Bollinger (20 periodi, 2.0 std dev) & Squeeze Detection
    sma20 = close.rolling(window=20, min_periods=1).mean()
    std20 = close.rolling(window=20, min_periods=1).std().fillna(0)
    bb_upper = sma20 + (2.0 * std20)
    bb_lower = sma20 - (2.0 * std20)
    bb_bandwidth = (bb_upper - bb_lower) / (sma20 + 1e-9)
    
    # Squeeze: Bandwidth al di sotto del 20° percentile storico recente
    bandwidth_recent = bb_bandwidth.tail(60)
    is_squeeze = float(bb_bandwidth.iloc[-1]) <= float(bandwidth_recent.quantile(0.20)) if len(bandwidth_recent) > 10 else False

    # 5. ATR 14 (Average True Range - Wilder Smoothing)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1/14, adjust=False).mean()
    atr_latest = float(atr14.iloc[-1]) if not atr14.empty else 0.0

    # 6. ADX 14 (Average Directional Index - Wilder Smoothing)
    up_move = high.diff()
    down_move = -low.diff()
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    tr_smooth = tr.ewm(alpha=1/14, adjust=False).mean() * 14.0
    pos_di = 100.0 * (pd.Series(pos_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() * 14.0 / (tr_smooth + 1e-9))
    neg_di = 100.0 * (pd.Series(neg_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() * 14.0 / (tr_smooth + 1e-9))
    dx = 100.0 * ((pos_di - neg_di).abs() / (pos_di + neg_di + 1e-9))
    adx14 = dx.ewm(alpha=1/14, adjust=False).mean()
    adx_latest = float(adx14.iloc[-1]) if not adx14.empty else 20.0

    adx_strength = "Trend Debole / Laterale"
    if adx_latest > 50:
        adx_strength = "Trend Molto Forte (> 50)"
    elif adx_latest > 25:
        adx_strength = "Trend In Atto (> 25)"

    # Costruzione DataFrame Indicatori Completo
    df_out = pd.DataFrame({
        "close": close,
        "ema20": ema20,
        "ema50": ema50,
        "sma200": sma200,
        "macd_line": macd_line,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "rsi14": rsi14,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_middle": sma20,
        "bb_bandwidth": bb_bandwidth,
        "atr14": atr14,
        "adx14": adx14
    }, index=df.index)

    return {
        "df_indicators": df_out,
        "last_close": float(close.iloc[-1]),
        "last_ema20": float(ema20.iloc[-1]),
        "last_ema50": float(ema50.iloc[-1]),
        "last_sma200": float(sma200.iloc[-1]),
        "golden_cross": golden_cross,
        "ema20_gt_ema50": ema20_gt_ema50,
        "last_macd_line": float(macd_line.iloc[-1]),
        "last_macd_signal": float(macd_signal.iloc[-1]),
        "last_macd_hist": float(macd_hist.iloc[-1]),
        "rsi_latest": rsi_latest,
        "rsi_status": rsi_status,
        "last_bb_upper": float(bb_upper.iloc[-1]),
        "last_bb_lower": float(bb_lower.iloc[-1]),
        "is_bollinger_squeeze": is_squeeze,
        "atr_latest": atr_latest,
        "adx_latest": adx_latest,
        "adx_strength": adx_strength
    }


def compute_volume_profile(df_prices: pd.DataFrame, n_bins: int = 20) -> Dict[str, Any]:
    """
    Calcola il Volume Profile distribuzionale basato sul prezzo tipico ((High+Low+Close)/3).
    Restituisce i bin di prezzo con i volumi totali, il POC (Point of Control),
    il VAH (Value Area High) e il VAL (Value Area Low) contenenti il 70% del volume totale.
    """
    if df_prices.empty or "close" not in df_prices.columns:
        return {}

    close = df_prices["close"].astype(float)
    high = df_prices["high"].astype(float) if "high" in df_prices.columns else close
    low = df_prices["low"].astype(float) if "low" in df_prices.columns else close
    typical_price = (high + low + close) / 3.0

    volume = df_prices["volume"].astype(float) if "volume" in df_prices.columns else pd.Series(1.0, index=df_prices.index)
    
    if volume.sum() == 0:
        volume = pd.Series(1.0, index=df_prices.index)

    min_p = float(low.min())
    max_p = float(high.max())
    if min_p == max_p:
        max_p += 1.0

    bins = np.linspace(min_p, max_p, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2.0
    vol_by_bin = np.zeros(n_bins)

    # Aggrega i volumi per ciascun bin di prezzo sul Typical Price
    cats = pd.cut(typical_price, bins=bins, labels=False, include_lowest=True)
    for c, v in zip(cats, volume):
        if pd.notna(c) and 0 <= int(c) < n_bins:
            vol_by_bin[int(c)] += v

    # POC (Point of Control) = Bin con il massimo volume
    poc_idx = int(np.argmax(vol_by_bin))
    poc_price = float(bin_centers[poc_idx])

    # Value Area (70% del volume totale)
    total_vol = vol_by_bin.sum()
    target_vol = total_vol * 0.70

    sorted_indices = np.argsort(vol_by_bin)[::-1]
    cum_vol = 0.0
    va_indices = []
    for idx in sorted_indices:
        cum_vol += vol_by_bin[idx]
        va_indices.append(idx)
        if cum_vol >= target_vol:
            break

    va_prices = bin_centers[va_indices]
    val_price = float(np.min(va_prices)) if len(va_prices) > 0 else min_p
    vah_price = float(np.max(va_prices)) if len(va_prices) > 0 else max_p

    df_profile = pd.DataFrame({
        "price_bin_mid": bin_centers,
        "price_bin_min": bins[:-1],
        "price_bin_max": bins[1:],
        "volume": vol_by_bin,
        "volume_pct": (vol_by_bin / (total_vol + 1e-9)) * 100.0,
        "is_poc": [i == poc_idx for i in range(n_bins)],
        "in_value_area": [i in va_indices for i in range(n_bins)]
    })

    return {
        "df_profile": df_profile,
        "profile": df_profile,
        "poc_price": poc_price,
        "vah_price": vah_price,
        "val_price": val_price,
        "total_volume": float(total_vol)
    }


def detect_candlestick_patterns(df_prices: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Rileva automaticamente i principali pattern candlestick (Engulfing, Doji, Hammer, Shooting Star).
    Ritorna la lista dei pattern individuati nelle ultime barre di prezzo.
    """
    patterns = []
    if df_prices.empty or len(df_prices) < 3:
        return patterns

    df = df_prices.copy().tail(30)
    close = df["close"].values
    open_p = df["open"].values if "open" in df.columns else close
    high = df["high"].values if "high" in df.columns else np.maximum(close, open_p)
    low = df["low"].values if "low" in df.columns else np.minimum(close, open_p)
    dates = df.index

    for i in range(1, len(close)):
        d_str = str(dates[i])[:10]
        c = close[i]
        o = open_p[i]
        h = high[i]
        l = low[i]

        prev_c = close[i - 1]
        prev_o = open_p[i - 1]

        body = abs(c - o)
        candle_range = max(1e-9, h - l)

        # 1. Doji (corpo piccolissimo <= 10% del range totale)
        if body / candle_range <= 0.10:
            patterns.append({
                "date": d_str,
                "pattern": "Doji ⚖️",
                "bias": "Neutro / Indecisione",
                "description": "Corpo quasi nullo: equilibrio temporaneo tra compratori e venditori."
            })

        # 2. Bullish Engulfing (candela verde che ingloba la precedente rossa)
        elif prev_c < prev_o and c > o and c >= prev_o and o <= prev_c:
            patterns.append({
                "date": d_str,
                "pattern": "Bullish Engulfing 🟢",
                "bias": "Rialzista",
                "description": "Candela verde di inversione che ingloba completamente il corpo rosso precedente."
            })

        # 3. Bearish Engulfing (candela rossa che ingloba la precedente verde)
        elif prev_c > prev_o and c < o and c <= prev_o and o >= prev_c:
            patterns.append({
                "date": d_str,
                "pattern": "Bearish Engulfing 🔴",
                "bias": "Ribassista",
                "description": "Candela rossa di inversione che ingloba completamente il corpo verde precedente."
            })

        # 4. Hammer (Ombra inferiore molto lunga >= 2x corpo, ombra superiore corta)
        elif (min(o, c) - l) >= 2.0 * body and (h - max(o, c)) <= 0.5 * body and body > 0:
            patterns.append({
                "date": d_str,
                "pattern": "Hammer (Martello) 🔨",
                "bias": "Rialzista",
                "description": "Lunga ombra inferiore con chiusura sui massimi: forte rigetto dei prezzi bassi."
            })

        # 5. Shooting Star (Ombra superiore molto lunga >= 2x corpo)
        elif (h - max(o, c)) >= 2.0 * body and (min(o, c) - l) <= 0.5 * body and body > 0:
            patterns.append({
                "date": d_str,
                "pattern": "Shooting Star 🌠",
                "bias": "Ribassista",
                "description": "Lunga ombra superiore con chiusura sui minimi: rigetto dei prezzi alti."
            })

    return patterns[-8:]  # Ritorna gli ultimi 8 pattern più recenti


def compute_technical_confluence_score(df_prices: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcola un punteggio complessivo di confluenza tecnica (0 - 100) per l'asset,
    con verdetto tattico e dettaglio dei fattori positivi, neutri e negativi.
    """
    indicators = compute_technical_indicators(df_prices)
    if not indicators:
        return {
            "score": 50.0,
            "verdict": "Neutro",
            "verdict_icon": "🟡",
            "factors": []
        }

    score = 50.0
    factors = []

    # 1. Trend EMA 20 vs EMA 50 (+12 / -12)
    if indicators["last_ema20"] > indicators["last_ema50"]:
        score += 12.0
        factors.append({"indicator": "EMA 20 vs EMA 50", "status": "🟢 Rialzista", "impact": "+12 pts", "note": "EMA 20 > EMA 50"})
    else:
        score -= 12.0
        factors.append({"indicator": "EMA 20 vs EMA 50", "status": "🔴 Ribassista", "impact": "-12 pts", "note": "EMA 20 < EMA 50"})

    # 2. Prezzo vs SMA 200 (+13 / -13)
    if indicators["last_close"] > indicators["last_sma200"]:
        score += 13.0
        factors.append({"indicator": "Prezzo vs SMA 200", "status": "🟢 Trend Primario Toro", "impact": "+13 pts", "note": "Prezzo sopra la media a 200gg"})
    else:
        score -= 13.0
        factors.append({"indicator": "Prezzo vs SMA 200", "status": "🔴 Trend Primario Orso", "impact": "-13 pts", "note": "Prezzo sotto la media a 200gg"})

    # 3. MACD Hist (+10 / -10)
    if indicators["last_macd_hist"] > 0:
        score += 10.0
        factors.append({"indicator": "MACD Histogram", "status": "🟢 Momentum Positivo", "impact": "+10 pts", "note": "Istogramma MACD sopra lo zero"})
    else:
        score -= 10.0
        factors.append({"indicator": "MACD Histogram", "status": "🔴 Momentum Negativo", "impact": "-10 pts", "note": "Istogramma MACD sotto lo zero"})

    # 4. RSI 14 (+10 / -10 / 0)
    rsi = indicators["rsi_latest"]
    if 45 <= rsi <= 65:
        score += 5.0
        factors.append({"indicator": "RSI (14)", "status": "🟢 Zona Costruttiva", "impact": "+5 pts", "note": f"RSI a {rsi:.1f} in zona neutro-positiva"})
    elif rsi > 70:
        score -= 8.0
        factors.append({"indicator": "RSI (14)", "status": "🔴 Ipercomprato", "impact": "-8 pts", "note": f"RSI a {rsi:.1f} sopra 70"})
    elif rsi < 30:
        score += 8.0
        factors.append({"indicator": "RSI (14)", "status": "🟢 Ipervenduto (Opportunità)", "impact": "+8 pts", "note": f"RSI a {rsi:.1f} sotto 30"})
    else:
        factors.append({"indicator": "RSI (14)", "status": "🟡 Neutro", "impact": "0 pts", "note": f"RSI a {rsi:.1f}"})

    # 5. ADX Trend Strength (+5 se trend forte)
    if indicators["adx_latest"] > 25:
        score += 5.0
        factors.append({"indicator": "ADX (14)", "status": "🟢 Trend Solido", "impact": "+5 pts", "note": f"ADX a {indicators['adx_latest']:.1f} (> 25)"})
    else:
        factors.append({"indicator": "ADX (14)", "status": "🟡 Fase Laterale", "impact": "0 pts", "note": f"ADX a {indicators['adx_latest']:.1f} (< 25)"})

    # Squeeze Indicator Warning
    if indicators["is_bollinger_squeeze"]:
        factors.append({"indicator": "Bollinger Squeeze", "status": "⚡ Imminente Volatilità", "impact": "Alert", "note": "Bande di Bollinger molto strette"})

    final_score = max(0.0, min(100.0, score))

    if final_score >= 75:
        verdict = "Strong Buy"
        verdict_icon = "🟢🟢"
    elif final_score >= 60:
        verdict = "Buy"
        verdict_icon = "🟢"
    elif final_score >= 40:
        verdict = "Hold / Neutral"
        verdict_icon = "🟡"
    elif final_score >= 25:
        verdict = "Sell"
        verdict_icon = "🔴"
    else:
        verdict = "Strong Sell"
        verdict_icon = "🔴🔴"

    return {
        "score": float(final_score),
        "verdict": verdict,
        "verdict_icon": verdict_icon,
        "factors": factors
    }


def compute_multi_timeframe_analysis(df_prices: pd.DataFrame) -> Dict[str, Any]:
    """
    Resample del DataFrame per calcolare l'allineamento dei trend su scala Giornaliera (1D) e Settimanale (1W).
    """
    if df_prices.empty or "close" not in df_prices.columns:
        return {}

    df_d = df_prices.copy()
    close_d = df_d["close"].astype(float)
    ema20_d = close_d.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50_d = close_d.ewm(span=50, adjust=False).mean().iloc[-1]
    trend_d = "🟢 Rialzista" if ema20_d > ema50_d else "🔴 Ribassista"

    # Resample Settimanale
    df_w = df_prices.resample("W").agg({
        "close": "last",
        "open": "first",
        "high": "max",
        "low": "min"
    }).dropna()

    if len(df_w) >= 10:
        close_w = df_w["close"].astype(float)
        ema10_w = close_w.ewm(span=10, adjust=False).mean().iloc[-1]
        ema20_w = close_w.ewm(span=20, adjust=False).mean().iloc[-1]
        trend_w = "🟢 Rialzista" if ema10_w > ema20_w else "🔴 Ribassista"
    else:
        trend_w = "🟡 Dati Insufficienti"

    is_aligned = (trend_d.startswith("🟢") and trend_w.startswith("🟢")) or (trend_d.startswith("🔴") and trend_w.startswith("🔴"))

    return {
        "trend_daily": trend_d,
        "trend_weekly": trend_w,
        "is_aligned": is_aligned,
        "alignment_text": "🟢 Trend Allineato (Confluenza Multi-Timeframe)" if is_aligned else "🟡 Trend Discordante tra Daily e Weekly"
    }
