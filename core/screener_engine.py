"""
ARGUS — Risk Analytics Platform
Core Module: Multi-Factor Market Screener & Pre-Trade Impact Simulator Engine
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from core.cache_shield import get_cached_ticker_history, get_cached_ticker_info

MARKET_UNIVERSES: Dict[str, Dict[str, Any]] = {
    "🇺🇸 US Mega & Large Caps (S&P 100)": {
        "description": "I leader ad elevata capitalizzazione e massima liquidità del mercato USA (Tech, Healthcare, Finanza, Industriali, Energy).",
        "tickers": [
            "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK-B", "JPM", "JNJ",
            "V", "PG", "UNH", "HD", "MA", "LLY", "XOM", "ABBV", "CVX", "MRK",
            "KO", "PEP", "COST", "AVGO", "ADBE", "CSCO", "CRM", "AMD", "NFLX", "WMT",
            "BAC", "MCD", "ACN", "LIN", "DIS", "ABT", "TMO", "TXN", "PM", "ORCL",
            "CAT", "IBM", "GE", "VZ", "HON", "COP", "INTC", "QCOM", "SPGI", "AMAT"
        ]
    },
    "🤖 AI Supercycle, Semiconductors & Infrastructure": {
        "description": "Aziende cardine dell'infrastruttura AI: semiconduttori, foundry, apparecchiature litografiche, datacenter e networking.",
        "tickers": [
            "NVDA", "TSM", "ASML", "AVGO", "AMD", "QCOM", "AMAT", "LRCX", "KLAC", "ARM",
            "MRVL", "MU", "SMCI", "ANET", "VST", "CEG", "NOW", "PLTR", "MSFT", "GOOGL", "DELL", "CRWD"
        ]
    },
    "🇪🇺 European Champions (EuroStoxx 50)": {
        "description": "Le principali blue chips dell'Eurozona per solidità di bilancio, diversificazione e leadership globale.",
        "tickers": [
            "ASML", "SAP", "MC.PA", "OR.PA", "RMS.PA", "NOVO-B.CO", "NESN.SW", "SIE.DE",
            "ALV.DE", "SAN.MC", "IBE.MC", "AIR.PA", "TTE.PA", "BNP.PA", "SU.PA",
            "ABI.BR", "INGA.AS", "EL.PA", "MBG.DE", "ENEL.MI", "ISP.MI", "RACE.MI", "UCG.MI", "BAYN.DE", "BAS.DE"
        ]
    },
    "🇮🇹 FTSE MIB Leaders (Piazza Affari)": {
        "description": "I titoli a maggiore capitalizzazione, dividendi e liquidità del listino italiano (Borsa Italiana).",
        "tickers": [
            "RACE.MI", "ENEL.MI", "ISP.MI", "UCG.MI", "ENI.MI", "STMMI.MI", "PRY.MI",
            "MB.MI", "G.MI", "TIT.MI", "MONC.MI", "SRG.MI", "TRN.MI", "PST.MI",
            "CPR.MI", "AMP.MI", "HER.MI", "BAMI.MI", "A2A.MI", "REC.MI", "LDO.MI", "NEXI.MI"
        ]
    },
    "👑 Dividend Aristocrats & High Yield": {
        "description": "Società con storico impeccabile di dividendi crescenti e solidi flussi di cassa operativi.",
        "tickers": [
            "JNJ", "PG", "KO", "PEP", "ABBV", "O", "MO", "TROW", "MMM", "CVX",
            "IBM", "MCD", "CL", "EMR", "KMB", "BDX", "ED", "ENB", "BNS", "RIO",
            "ADM", "GPC", "SWK", "SPG", "WBA"
        ]
    },
    "🚀 High Growth & Disruptive Tech": {
        "description": "Aziende ad altissimo tasso di crescita nei settori Cloud Software, Cyber-security, E-commerce e FinTech.",
        "tickers": [
            "NVDA", "AMD", "AVGO", "CRM", "NOW", "PANW", "CRWD", "PLTR", "SNOW", "MELI",
            "ASML", "ARM", "SMCI", "SHOP", "UBER", "DDOG", "NET", "ZS", "FTNT", "MDB",
            "COIN", "APP", "TTD", "MSTR", "SE"
        ]
    },
    "💊 Global Healthcare, Pharma & Biotech": {
        "description": "I colossi farmaceutici, biotecnologie innovative, dispositivi medici e protagonisti della rivoluzione GLP-1.",
        "tickers": [
            "LLY", "NVO", "JNJ", "ABBV", "MRK", "AZN", "ROG.SW", "PFE", "TMO", "DHR",
            "ISRG", "VRTX", "REGN", "BMY", "MDT", "SYK", "AMGN", "GILD", "BSX", "ZTS"
        ]
    },
    "🛡️ Aerospace, Defense & Cybersecurity": {
        "description": "Leader globali della sicurezza nazionale, difesa aerospaziale, elettronica militare e cybersecurity strategica.",
        "tickers": [
            "LMT", "RTX", "NOC", "GD", "BA", "LDO.MI", "RHM.DE", "AIR.PA", "PANW", "CRWD",
            "FTNT", "PLTR", "TDG", "HII", "GEN", "SAIC", "KTOS"
        ]
    },
    "⚡ Clean Energy, Transition Metals & Nuclear": {
        "description": "Aziende cardine della transizione energetica, estrazione di materie prime critiche (rame, litio, uranio) e nucleare.",
        "tickers": [
            "ENEL.MI", "IBE.MC", "NEE", "FSLR", "CCJ", "ALB", "SQM", "RIO", "BHP", "ENPH",
            "CEG", "SCCO", "FCX", "VALE", "ENI.MI", "ORSTED.CO", "SEDG"
        ]
    },
    "🌍 Emerging Markets & Global Giants": {
        "description": "I giganti ad alta crescita dei mercati emergenti (Asia, America Latina, India) e piattaforme digitali globali.",
        "tickers": [
            "TSM", "BABA", "0700.HK", "INFY", "MELI", "VALE", "PDD", "SE", "HDB", "NU",
            "BIDU", "JD", "ITUB", "BBD", "CPNG"
        ]
    },
    "🪙 Crypto Blue Chips & Digital Assets Ecosystem": {
        "description": "Asset crittografici a maggiore capitalizzazione e società quotate legate all'infrastruttura blockchain e crypto.",
        "tickers": [
            "BTC-USD", "ETH-USD", "SOL-USD", "COIN", "MSTR", "MARA", "RIOT", "SQ", "HOOD", "CLSK"
        ]
    }
}


def _compute_rsi(series: pd.Series, period: int = 14) -> float:
    """Calcola l'indicatore RSI (Relative Strength Index) a 14 periodi."""
    if series.empty or len(series) < period + 1:
        return 50.0
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean().iloc[-1]
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean().iloc[-1]
    if avg_loss == 0:
        if avg_gain == 0:
            return 50.0
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def fetch_screener_universe_data(
    tickers: List[str],
    benchmark_ticker: str = "SPY",
    progress_callback: Optional[Any] = None
) -> pd.DataFrame:
    """
    Estrae e calcola in modo vettorializzato tutte le metriche multi-fattoriali per l'universo di titoli.
    Utilizza lo scudo di caching multi-tier (L1 RAM + L2 SQLite) per garantire tempi di risposta ultra-rapidi.
    """
    rows = []
    clean_tickers = list(dict.fromkeys([str(t).strip().upper() for t in tickers if str(t).strip()]))
    
    # Pre-caricamento storico del benchmark per calcolo Beta
    df_bm = get_cached_ticker_history(benchmark_ticker)
    sr_bm_ret = pd.Series(dtype=float)
    if df_bm is not None and not df_bm.empty and "close" in df_bm.columns:
        sr_bm_ret = df_bm["close"].pct_change().dropna()

    total = len(clean_tickers)
    for idx, tk in enumerate(clean_tickers):
        if progress_callback:
            progress_callback(idx + 1, total, tk)
            
        try:
            info = get_cached_ticker_info(tk)
            df_hist = get_cached_ticker_history(tk)
            
            name = info.get("shortName") or info.get("longName") or tk
            sector = info.get("sector") or "N/D"
            industry = info.get("industry") or "N/D"
            country = info.get("country") or "N/D"
            currency = info.get("currency") or ("EUR" if tk.endswith("-EUR") or tk.endswith(".MI") or tk.endswith(".PA") or tk.endswith(".DE") else "USD")
            
            quote_type = str(info.get("quoteType", "")).upper()
            if sector == "N/D":
                if quote_type == "CRYPTOCURRENCY" or "-" in tk or tk.startswith(("BTC", "ETH", "SOL")):
                    sector = "Crypto / Digital Assets"
                    industry = "Digital Currency"
                elif quote_type == "ETF" or "ETF" in str(name).upper() or "ISHARES" in str(name).upper() or "VANGUARD" in str(name).upper():
                    sector = "ETF / Fondi"
                    industry = "Exchange Traded Fund"

            # Prezzi e Target Price
            last_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)
            if last_price <= 0 and df_hist is not None and not df_hist.empty and "close" in df_hist.columns:
                last_price = float(df_hist["close"].iloc[-1])
            if last_price <= 0:
                if "FDUSD" in tk or "USDT" in tk or "USDC" in tk:
                    last_price = 0.86 if "-EUR" in tk else 1.00
                
            target_mean = float(info.get("targetMeanPrice") or 0.0)
            
            # Upside % normalizzato
            upside_pct = np.nan
            if last_price > 0 and target_mean > 0:
                # Normalizzazione ratio valute se necessario (es. DKK, SEK, GBp)
                ratio = target_mean / last_price
                if ratio > 3.0 or ratio < 0.2:
                    if tk.endswith(".CO") or (6.5 <= ratio <= 8.5): target_mean /= 7.46
                    elif tk.endswith(".ST") or (10.0 <= ratio <= 13.0): target_mean /= 11.40
                    elif tk.endswith(".OL"): target_mean /= 11.50
                    elif tk.endswith(".T") or ratio > 100: target_mean /= 162.0
                    elif tk.endswith(".L") and ratio > 50: target_mean = (target_mean / 100.0) / 1.17
                upside_pct = ((target_mean - last_price) / last_price) * 100.0

            # Valutazione & Multipli
            pe_trailing = float(info.get("trailingPE") or np.nan)
            pe_forward = float(info.get("forwardPE") or np.nan)
            peg_ratio = float(info.get("pegRatio") or np.nan)
            pb_ratio = float(info.get("priceToBook") or np.nan)
            
            # Dividend Yield % normalizzato istituzionale
            div_rate = float(info.get("dividendRate") or info.get("trailingAnnualDividendRate") or 0.0)
            if div_rate > 0 and last_price > 0:
                div_yield = (div_rate / last_price) * 100.0
            else:
                div_raw = float(info.get("dividendYield") or info.get("trailingAnnualDividendYield") or 0.0)
                if div_raw > 0:
                    div_yield = div_raw if div_raw >= 0.20 else (div_raw * 100.0)
                else:
                    div_yield = 0.0
            div_yield = round(div_yield, 2)
            
            # Redditività & Flussi
            roe = float(info.get("returnOnEquity") or np.nan)
            if pd.notna(roe): roe *= 100.0
            profit_margin = float(info.get("profitMargins") or np.nan)
            if pd.notna(profit_margin): profit_margin *= 100.0
            
            fcf = float(info.get("freeCashflow") or 0.0)
            mcap = float(info.get("marketCap") or 0.0)
            mcap_b = round(mcap / 1e9, 2) if mcap > 0 else np.nan
            if pd.notna(mcap_b):
                if mcap_b >= 200.0: mcap_cat = "Mega-Cap (>$200B)"
                elif mcap_b >= 10.0: mcap_cat = "Large-Cap ($10B-$200B)"
                elif mcap_b >= 2.0: mcap_cat = "Mid-Cap ($2B-$10B)"
                else: mcap_cat = "Small-Cap (<$2B)"
            else:
                mcap_cat = "N/D"

            fcf_yield = (fcf / mcap * 100.0) if mcap > 0 and fcf != 0 else np.nan
            debt_to_equity = float(info.get("debtToEquity") or np.nan)
            if pd.notna(debt_to_equity): debt_to_equity /= 100.0
            
            # Consensus & Analisti Istituzionali
            rec_key = str(info.get("recommendationKey") or "N/D").replace("_", " ").title()
            num_analysts = int(info.get("numberOfAnalystOpinions") or 0)
            rev_growth = float(info.get("revenueGrowth") or np.nan)
            if pd.notna(rev_growth): rev_growth *= 100.0
            gross_margin = float(info.get("grossMargins") or np.nan)
            if pd.notna(gross_margin): gross_margin *= 100.0
            
            # Metriche Tecniche & di Rischio da serie storica
            vol_ann_pct = np.nan
            beta_val = float(info.get("beta") or np.nan)
            sharpe_val = np.nan
            max_dd_pct = np.nan
            rsi_val = 50.0
            p_sma50_pct = np.nan
            p_sma200_pct = np.nan
            perf_3m_pct = np.nan
            perf_1y_pct = np.nan
            
            if df_hist is not None and not df_hist.empty and len(df_hist) > 20:
                closes = df_hist["close"].dropna()
                rets = closes.pct_change().dropna()
                
                if not rets.empty:
                    vol_ann_pct = float(rets.std() * np.sqrt(252) * 100.0)
                    mean_ret_ann = float(rets.mean() * 252 * 100.0)
                    rf_rate = 3.0 # Tasso risk-free prudenziale 3%
                    if vol_ann_pct > 0:
                        sharpe_val = (mean_ret_ann - rf_rate) / vol_ann_pct
                        
                    # Calcolo Max Drawdown
                    cum_rets = (1 + rets).cumprod()
                    peak = cum_rets.cummax()
                    dd = (cum_rets - peak) / peak
                    max_dd_pct = float(dd.min() * 100.0)
                    
                    # Beta se non presente da info
                    if pd.isna(beta_val) and not sr_bm_ret.empty:
                        df_align = pd.concat([rets, sr_bm_ret], axis=1, join="inner").dropna()
                        if len(df_align) > 30:
                            cov_m = np.cov(df_align.iloc[:, 0], df_align.iloc[:, 1])
                            var_bm = cov_m[1, 1]
                            if var_bm > 0:
                                beta_val = float(cov_m[0, 1] / var_bm)

                    # Indicatori Tecnici
                    rsi_val = _compute_rsi(closes, 14)
                    if len(closes) >= 50:
                        sma50 = closes.rolling(50).mean().iloc[-1]
                        if sma50 > 0: p_sma50_pct = ((closes.iloc[-1] - sma50) / sma50) * 100.0
                    if len(closes) >= 200:
                        sma200 = closes.rolling(200).mean().iloc[-1]
                        if sma200 > 0: p_sma200_pct = ((closes.iloc[-1] - sma200) / sma200) * 100.0
                        
                    if len(closes) >= 63:
                        perf_3m_pct = ((closes.iloc[-1] - closes.iloc[-63]) / closes.iloc[-63]) * 100.0
                    if len(closes) >= 252:
                        perf_1y_pct = ((closes.iloc[-1] - closes.iloc[-252]) / closes.iloc[-252]) * 100.0

            # Solvibilità & Accounting Quality (Stima Rapida Istituzionale)
            z_score = np.nan
            if pd.notna(debt_to_equity) and pd.notna(profit_margin):
                z_score = 1.8 + (profit_margin / 15.0) * 0.8 + (1.0 / max(0.2, debt_to_equity)) * 0.4
                if pd.notna(roe) and roe > 15.0: z_score += 0.4
            
            piotroski_score = 6
            if pd.notna(roe) and roe > 10.0: piotroski_score += 1
            if pd.notna(fcf_yield) and fcf_yield > 4.0: piotroski_score += 1
            if pd.notna(debt_to_equity) and debt_to_equity < 0.8: piotroski_score += 1
            piotroski_score = min(9, max(1, piotroski_score))

            # Calcolo Punteggio Istituzionale Globale ARGUS [0 - 100]
            # Basato su 4 pilastri: Valutazione (25%), Qualità (25%), Rischio (25%), Momentum (25%)
            score_val = 50.0
            if pd.notna(upside_pct): score_val += np.clip(upside_pct * 1.5, -25, 25)
            if pd.notna(peg_ratio) and peg_ratio > 0:
                score_val += (1.5 - min(3.0, peg_ratio)) * 15.0
                
            score_qual = 50.0
            if pd.notna(roe): score_qual += np.clip((roe - 12.0) * 1.2, -20, 20)
            if pd.notna(z_score): score_qual += (z_score - 2.5) * 10.0
            
            score_risk = 50.0
            if pd.notna(vol_ann_pct): score_risk += (25.0 - min(45.0, vol_ann_pct)) * 1.5
            if pd.notna(sharpe_val): score_risk += np.clip(sharpe_val * 15.0, -20, 25)
            
            score_mom = 50.0
            if pd.notna(perf_1y_pct): score_mom += np.clip(perf_1y_pct * 0.8, -25, 25)
            if 45 <= rsi_val <= 65: score_mom += 10.0
            elif rsi_val > 75 or rsi_val < 30: score_mom -= 15.0

            argus_composite_score = np.clip(
                (score_val * 0.25) + (score_qual * 0.25) + (score_risk * 0.25) + (score_mom * 0.25),
                5.0, 98.0
            )

            rows.append({
                "ticker": tk,
                "name": name,
                "sector": sector,
                "industry": industry,
                "country": country,
                "currency": currency,
                "market_cap_b": mcap_b,
                "mcap_category": mcap_cat,
                "consensus_rating": rec_key,
                "num_analysts": num_analysts,
                "last_price": round(last_price, 2),
                "target_mean_price": round(target_mean, 2) if target_mean > 0 else np.nan,
                "upside_pct": round(upside_pct, 2) if pd.notna(upside_pct) else np.nan,
                "revenue_growth_pct": round(rev_growth, 2) if pd.notna(rev_growth) else np.nan,
                "gross_margin_pct": round(gross_margin, 2) if pd.notna(gross_margin) else np.nan,
                "trailing_pe": round(pe_trailing, 2) if pd.notna(pe_trailing) else np.nan,
                "forward_pe": round(pe_forward, 2) if pd.notna(pe_forward) else np.nan,
                "peg_ratio": round(peg_ratio, 2) if pd.notna(peg_ratio) else np.nan,
                "price_to_book": round(pb_ratio, 2) if pd.notna(pb_ratio) else np.nan,
                "dividend_yield_pct": round(div_yield, 2) if pd.notna(div_yield) else 0.0,
                "roe_pct": round(roe, 2) if pd.notna(roe) else np.nan,
                "profit_margin_pct": round(profit_margin, 2) if pd.notna(profit_margin) else np.nan,
                "fcf_yield_pct": round(fcf_yield, 2) if pd.notna(fcf_yield) else np.nan,
                "debt_to_equity": round(debt_to_equity, 2) if pd.notna(debt_to_equity) else np.nan,
                "altman_z_score": round(z_score, 2) if pd.notna(z_score) else np.nan,
                "piotroski_score": piotroski_score,
                "beta": round(beta_val, 2) if pd.notna(beta_val) else np.nan,
                "volatility_ann_pct": round(vol_ann_pct, 2) if pd.notna(vol_ann_pct) else np.nan,
                "sharpe_ratio": round(sharpe_val, 2) if pd.notna(sharpe_val) else np.nan,
                "max_drawdown_pct": round(max_dd_pct, 2) if pd.notna(max_dd_pct) else np.nan,
                "rsi_14": round(rsi_val, 1),
                "price_to_sma200_pct": round(p_sma200_pct, 2) if pd.notna(p_sma200_pct) else np.nan,
                "perf_3m_pct": round(perf_3m_pct, 2) if pd.notna(perf_3m_pct) else np.nan,
                "perf_1y_pct": round(perf_1y_pct, 2) if pd.notna(perf_1y_pct) else np.nan,
                "argus_score": round(argus_composite_score, 1)
            })
            
        except Exception:
            rows.append({
                "ticker": tk,
                "name": tk,
                "sector": "N/D",
                "industry": "N/D",
                "country": "N/D",
                "currency": "USD",
                "market_cap_b": np.nan,
                "mcap_category": "N/D",
                "consensus_rating": "N/D",
                "num_analysts": 0,
                "last_price": np.nan,
                "target_mean_price": np.nan,
                "upside_pct": np.nan,
                "revenue_growth_pct": np.nan,
                "gross_margin_pct": np.nan,
                "trailing_pe": np.nan,
                "forward_pe": np.nan,
                "peg_ratio": np.nan,
                "price_to_book": np.nan,
                "dividend_yield_pct": 0.0,
                "roe_pct": np.nan,
                "profit_margin_pct": np.nan,
                "fcf_yield_pct": np.nan,
                "debt_to_equity": np.nan,
                "altman_z_score": np.nan,
                "piotroski_score": 5,
                "beta": np.nan,
                "volatility_ann_pct": np.nan,
                "sharpe_ratio": np.nan,
                "max_drawdown_pct": np.nan,
                "rsi_14": 50.0,
                "price_to_sma200_pct": np.nan,
                "perf_3m_pct": np.nan,
                "perf_1y_pct": np.nan,
                "argus_score": 50.0
            })

    df_out = pd.DataFrame(rows)
    if not df_out.empty and "argus_score" in df_out.columns:
        df_out = df_out.sort_values(by="argus_score", ascending=False).reset_index(drop=True)
    return df_out


SCREENER_FIELD_ALIASES: Dict[str, str] = {
    "piotroski": "piotroski_score",
    "piotroski_score": "piotroski_score",
    "altman": "altman_z_score",
    "altman_z": "altman_z_score",
    "altman_z_score": "altman_z_score",
    "z_score": "altman_z_score",
    "zscore": "altman_z_score",
    "roic": "roe_pct",
    "roe": "roe_pct",
    "roe_pct": "roe_pct",
    "wacc": "wacc",
    "profit_margin": "profit_margin_pct",
    "profit_margin_pct": "profit_margin_pct",
    "profitmargin": "profit_margin_pct",
    "margin": "profit_margin_pct",
    "gross_margin": "gross_margin_pct",
    "gross_margin_pct": "gross_margin_pct",
    "grossmargin": "gross_margin_pct",
    "revenue_growth": "revenue_growth_pct",
    "revenue_growth_pct": "revenue_growth_pct",
    "revenuegrowth": "revenue_growth_pct",
    "rev_growth": "revenue_growth_pct",
    "revgrowth": "revenue_growth_pct",
    "pe": "trailing_pe",
    "trailing_pe": "trailing_pe",
    "trailingpe": "trailing_pe",
    "forward_pe": "forward_pe",
    "forwardpe": "forward_pe",
    "peg": "peg_ratio",
    "peg_ratio": "peg_ratio",
    "pegratio": "peg_ratio",
    "pb": "price_to_book",
    "price_to_book": "price_to_book",
    "pricetobook": "price_to_book",
    "divyield": "dividend_yield_pct",
    "div_yield": "dividend_yield_pct",
    "dividend_yield": "dividend_yield_pct",
    "dividend_yield_pct": "dividend_yield_pct",
    "dividendyield": "dividend_yield_pct",
    "fcf_yield": "fcf_yield_pct",
    "fcf_yield_pct": "fcf_yield_pct",
    "fcfyield": "fcf_yield_pct",
    "debt_to_equity": "debt_to_equity",
    "de": "debt_to_equity",
    "debttoequity": "debt_to_equity",
    "beta": "beta",
    "vol": "volatility_ann_pct",
    "volatility": "volatility_ann_pct",
    "volatility_ann_pct": "volatility_ann_pct",
    "sharpe": "sharpe_ratio",
    "sharpe_ratio": "sharpe_ratio",
    "sharperatio": "sharpe_ratio",
    "max_dd": "max_drawdown_pct",
    "max_drawdown": "max_drawdown_pct",
    "max_drawdown_pct": "max_drawdown_pct",
    "maxdd": "max_drawdown_pct",
    "rsi": "rsi_14",
    "rsi_14": "rsi_14",
    "rsi14": "rsi_14",
    "sma200": "price_to_sma200_pct",
    "sma_200": "price_to_sma200_pct",
    "price_to_sma200": "price_to_sma200_pct",
    "price_to_sma200_pct": "price_to_sma200_pct",
    "perf_3m": "perf_3m_pct",
    "perf_3m_pct": "perf_3m_pct",
    "perf3m": "perf_3m_pct",
    "perf_1y": "perf_1y_pct",
    "perf_1y_pct": "perf_1y_pct",
    "perf1y": "perf_1y_pct",
    "upside": "upside_pct",
    "upside_pct": "upside_pct",
    "score": "argus_score",
    "argus_score": "argus_score",
    "mcap": "market_cap_b",
    "market_cap": "market_cap_b",
    "market_cap_b": "market_cap_b",
    "last_price": "last_price",
    "price": "last_price",
    "target_price": "target_mean_price",
    "target": "target_mean_price"
}

SCREENER_FORMULA_PRESETS: Dict[str, Dict[str, str]] = {
    "magic_formula": {
        "title": "👑 Magic Formula (Joel Greenblatt)",
        "formula": "ROE > 18 AND PE < 22 AND DebtToEquity < 1.0 AND Altman > 2.5",
        "description": "Massima redditività del capitale investito (alta qualità) combinata con multipli compressi (alto rendimento degli utili)."
    },
    "fcf_kings": {
        "title": "🏰 Free Cash Flow Kings & Solvency",
        "formula": "FCF_Yield > 5.0 AND DebtToEquity < 0.6 AND Piotroski >= 7 AND ROE > 12",
        "description": "Società che generano fiumi di cassa libera, con bilanci ultra-solidi e protezione assoluta contro il default."
    },
    "buffett_moat": {
        "title": "🏛️ Buffett Quality Moat",
        "formula": "Piotroski >= 7 AND Altman > 2.9 AND ROE > 15 AND DebtToEquity < 0.8",
        "description": "Aziende con fossato economico competitivo inespugnabile, forte redditività del capitale e bilancio conservativo."
    },
    "ai_supercycle": {
        "title": "🤖 AI Supercycle & Tech Growth",
        "formula": "RevenueGrowth > 15 AND ROE > 15 AND Upside > 10 AND PEG < 2.2",
        "description": "Leader tecnologici in forte espansione dei ricavi legati al superciclo dell'AI e del Cloud a multipli sostenibili."
    },
    "peter_lynch": {
        "title": "🚀 Peter Lynch Growth at Reasonable Price",
        "formula": "PEG < 1.2 AND Upside > 15 AND ROE > 12 AND DebtToEquity < 1.2",
        "description": "Crescita a valutazione attraente con solido potenziale di apprezzamento del consensus istituzionale."
    },
    "graham_value": {
        "title": "💎 Graham Deep Value & Margin of Safety",
        "formula": "PE < 16 AND PB < 2.0 AND DivYield > 2.5 AND Altman > 2.0",
        "description": "Margine di sicurezza classico con multipli compressi, rendimento da dividendo e solvibilità."
    },
    "turnaround_deep_value": {
        "title": "🔄 Turnaround & Mean Reversion",
        "formula": "PB < 1.8 AND Upside > 20 AND RSI >= 35 AND Altman > 1.8",
        "description": "Opportunità in fase di recupero ciclico con forte sconto sul patrimonio netto e potenziale asimmetrico di ripresa."
    },
    "low_beta_income": {
        "title": "🛡️ Low-Beta Dividend Fortress",
        "formula": "Beta < 0.85 AND Volatility < 22 AND DivYield > 3.0 AND Sharpe > 0.6",
        "description": "Titoli difensivi a bassa correlazione con il mercato e flusso cedolare stabile."
    },
    "momentum_breakout": {
        "title": "⚡ Momentum & Trend Breakout",
        "formula": "RSI >= 50 AND RSI <= 72 AND Perf1Y > 15 AND SMA200 > 0",
        "description": "Trend primario positivo, prezzo sopra la media mobile a 200 periodi e momentum intatto."
    }
}


def evaluate_custom_screener_query(
    df_screener: pd.DataFrame,
    query_str: str
) -> tuple[pd.DataFrame, bool, str]:
    """
    Esegue il parsing e la valutazione vettorializzata di una formula di screening personalizzata EQS.
    Restituisce: (DataFrame filtrato, successo booleano, messaggio diagnostico).
    """
    if df_screener is None or df_screener.empty:
        return pd.DataFrame(), True, "Dataset vuoto."
    
    if not query_str or not str(query_str).strip():
        return df_screener.copy(), True, "Nessun filtro applicato (mostrati tutti i titoli)."
    
    import re
    
    df_work = df_screener.copy()
    for col in set(SCREENER_FIELD_ALIASES.values()):
        if col not in df_work.columns:
            if col == "wacc":
                df_work[col] = 8.0
            else:
                df_work[col] = np.nan
    
    # 1. Pulizia e normalizzazione sintassi
    expr = str(query_str).strip()
    
    # Sostituzione operatori logici
    expr = re.sub(r'\bAND\b', ' & ', expr, flags=re.IGNORECASE)
    expr = re.sub(r'\bOR\b', ' | ', expr, flags=re.IGNORECASE)
    expr = re.sub(r'\bNOT\b', ' ~ ', expr, flags=re.IGNORECASE)
    
    # Normalizza singoli '=' in '==' (ma non '<=', '>=', '!=', '==')
    expr = re.sub(r'(?<![<>=!])=(?![=])', ' == ', expr)
    
    # 2. Sostituisci gli identificatori/alias dei campi
    def replace_identifier(match):
        tok = match.group(0)
        tok_lower = tok.lower()
        if tok_lower in SCREENER_FIELD_ALIASES:
            return SCREENER_FIELD_ALIASES[tok_lower]
        return tok

    parsed_expr = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', replace_identifier, expr)
    
    # 3. Valutazione sicura
    try:
        filtered_df = df_work.query(parsed_expr, engine="python")
        count = len(filtered_df)
        msg = f"✅ Filtro EQS applicato: {count} titoli selezionati su {len(df_screener)}."
        return filtered_df, True, msg
    except Exception as e:
        err_msg = f"❌ Errore nella formula EQS: {str(e)}"
        return df_screener.copy(), False, err_msg


def apply_strategy_preset(df_screener: pd.DataFrame, preset_key: str) -> pd.DataFrame:
    """
    Filtra i titoli in base a uno specifico archetipo di investimento quantitativo istituzionale.
    """
    if df_screener.empty:
        return df_screener

    df = df_screener.copy()
    
    if preset_key == "garp":
        # Growth at a Reasonable Price
        mask = (
            (df["peg_ratio"].isna() | (df["peg_ratio"] <= 1.4)) &
            (df["roe_pct"].isna() | (df["roe_pct"] >= 12.0)) &
            (df["upside_pct"].isna() | (df["upside_pct"] >= 5.0)) &
            (df["trailing_pe"].isna() | (df["trailing_pe"] <= 38.0))
        )
        return df[mask]
        
    elif preset_key == "dividend_fortress":
        # Dividendi solidi & bilancio immune al default
        mask = (
            (df["dividend_yield_pct"] >= 2.0) &
            (df["altman_z_score"].isna() | (df["altman_z_score"] >= 2.2)) &
            (df["debt_to_equity"].isna() | (df["debt_to_equity"] <= 1.6))
        )
        return df[mask]
        
    elif preset_key == "deep_value":
        # Graham Deep Value Margin of Safety
        mask = (
            (df["price_to_book"].isna() | (df["price_to_book"] <= 2.8)) &
            (df["trailing_pe"].isna() | (df["trailing_pe"] <= 18.0)) &
            (df["upside_pct"].isna() | (df["upside_pct"] >= 10.0))
        )
        return df[mask]
        
    elif preset_key == "low_volatility":
        # Minima Varianza & Difensivo
        mask = (
            (df["volatility_ann_pct"].isna() | (df["volatility_ann_pct"] <= 22.0)) &
            (df["beta"].isna() | (df["beta"] <= 0.95)) &
            (df["sharpe_ratio"].isna() | (df["sharpe_ratio"] >= 0.70))
        )
        return df[mask]
        
    elif preset_key == "momentum_breakout":
        # Trend positivo & espansione
        mask = (
            (df["price_to_sma200_pct"].isna() | (df["price_to_sma200_pct"] >= 0.0)) &
            (df["rsi_14"].between(45, 75)) &
            (df["perf_1y_pct"].isna() | (df["perf_1y_pct"] >= 8.0))
        )
        return df[mask]
        
    return df


def simulate_pre_trade_impact(
    current_positions_df: pd.DataFrame,
    candidate_ticker: str,
    candidate_weight_pct: float,
    benchmark_ticker: str = "SPY"
) -> Dict[str, Any]:
    """
    Simula in tempo reale l'impatto pre-trade dell'aggiunta o espansione di un titolo candidato sul portafoglio.
    Calcola le metriche 'Prima vs Dopo' (Rendimento, Volatilità, Sharpe, Beta, Diversification Ratio).
    """
    w_cand = max(0.01, min(0.50, candidate_weight_pct / 100.0))
    clean_cand = str(candidate_ticker).strip().upper()
    
    if current_positions_df is None or current_positions_df.empty:
        return {
            "valid": False,
            "message": "Nessun portafoglio attivo caricato per la simulazione."
        }
        
    # Estrazione pesi attuali
    df_pos = current_positions_df.copy()
    if "current_value" not in df_pos.columns:
        df_pos["current_value"] = 1000.0
    tot_val = df_pos["current_value"].sum()
    if tot_val <= 0:
        tot_val = 1000.0
    df_pos["weight"] = df_pos["current_value"] / tot_val
    
    # Raccogli tutti i ticker del portafoglio + candidato
    tickers = list(df_pos["ticker"].unique())
    all_tickers = list(dict.fromkeys(tickers + [clean_cand]))
    
    # Scarica serie storiche per tutti i titoli
    price_dict = {}
    for tk in all_tickers:
        df_h = get_cached_ticker_history(tk)
        if df_h is not None and not df_h.empty and "close" in df_h.columns:
            price_dict[tk] = df_h["close"]
            
    df_prices = pd.DataFrame(price_dict).dropna(how="all").ffill().dropna()
    if df_prices.empty or df_prices.shape[1] < 1 or clean_cand not in df_prices.columns:
        return {
            "valid": False,
            "message": f"Dati storici insufficienti per il titolo candidato {clean_cand}."
        }
        
    df_returns = df_prices.pct_change().dropna()
    if df_returns.empty or len(df_returns) < 30:
        return {
            "valid": False,
            "message": "Storico rendimenti troppo breve per una simulazione affidabile."
        }
        
    # Benchmark returns
    df_bm = get_cached_ticker_history(benchmark_ticker)
    sr_bm = pd.Series(dtype=float)
    if df_bm is not None and not df_bm.empty and "close" in df_bm.columns:
        sr_bm = df_bm["close"].pct_change().dropna()

    # Vettore pesi PRIMA (Old)
    w_old_map = {r["ticker"]: r["weight"] for _, r in df_pos.iterrows()}
    w_old = np.array([w_old_map.get(c, 0.0) for c in df_returns.columns])
    if w_old.sum() > 0:
        w_old = w_old / w_old.sum()
    else:
        w_old = np.ones(len(df_returns.columns)) / len(df_returns.columns)
        
    # Vettore pesi DOPO (New, normalizzato)
    w_new = w_old * (1.0 - w_cand)
    cand_idx = df_returns.columns.get_loc(clean_cand)
    w_new[cand_idx] += w_cand
    w_new = w_new / w_new.sum()

    # Rendimenti portafoglio Prima vs Dopo
    ret_port_old = (df_returns * w_old).sum(axis=1)
    ret_port_new = (df_returns * w_new).sum(axis=1)
    
    # 1. Rendimento Annuo
    cagr_old = float(ret_port_old.mean() * 252 * 100.0)
    cagr_new = float(ret_port_new.mean() * 252 * 100.0)
    delta_cagr = cagr_new - cagr_old
    
    # 2. Volatilità Annua
    vol_old = float(ret_port_old.std() * np.sqrt(252) * 100.0)
    vol_new = float(ret_port_new.std() * np.sqrt(252) * 100.0)
    delta_vol = vol_new - vol_old
    
    # 3. Sharpe Ratio (Rf = 3.0%)
    rf = 3.0
    sharpe_old = float((cagr_old - rf) / max(0.01, vol_old))
    sharpe_new = float((cagr_new - rf) / max(0.01, vol_new))
    delta_sharpe = sharpe_new - sharpe_old
    
    # 4. Beta vs Benchmark
    def calc_beta(sr_p, sr_b):
        if sr_b.empty: return 1.0
        df_ab = pd.concat([sr_p, sr_b], axis=1, join="inner").dropna()
        if len(df_ab) < 20: return 1.0
        cov = np.cov(df_ab.iloc[:, 0], df_ab.iloc[:, 1])
        var_b = cov[1, 1]
        return float(cov[0, 1] / var_b) if var_b > 0 else 1.0
        
    beta_old = calc_beta(ret_port_old, sr_bm)
    beta_new = calc_beta(ret_port_new, sr_bm)
    delta_beta = beta_new - beta_old
    
    # 5. Diversification Ratio (Choueifaty & Coignard)
    # DR = (somma w_i * sigma_i) / sigma_portafoglio
    vols = df_returns.std() * np.sqrt(252) * 100.0
    dr_old = float((w_old * vols).sum() / max(0.01, vol_old))
    dr_new = float((w_new * vols).sum() / max(0.01, vol_new))
    delta_dr = dr_new - dr_old
    
    # 6. Correlazione tra il Titolo Candidato e il Portafoglio Esistente
    ret_cand = df_returns[clean_cand]
    corr_cand_port = float(ret_cand.corr(ret_port_old))
    
    # Verdetto sintetico
    if delta_sharpe > 0.03 and delta_vol <= 0.2:
        verdict = "🟢 Fortemente Accrescitivo (Aumenta l'efficienza Sharpe e diversifica)"
    elif delta_vol < -0.3:
        verdict = "🟢 Difensivo (Riduce significativamente la volatilità di portafoglio)"
    elif delta_cagr > 1.0 and delta_sharpe >= -0.02:
        verdict = "🟡 Aggressivo / Alpha Booster (Aumenta il rendimento con rischio controllato)"
    else:
        verdict = "⚪ Neutro / Diagonale (Impatto bilanciato sulla struttura esistente)"

    return {
        "valid": True,
        "candidate_ticker": clean_cand,
        "simulated_weight_pct": round(w_cand * 100.0, 1),
        "correlation_with_portfolio": round(corr_cand_port, 2),
        "verdict": verdict,
        "metrics_comparison": {
            "Rendimento Atteso Annuo (%)": {"before": cagr_old, "after": cagr_new, "delta": delta_cagr, "format": "{:+.2f}%"},
            "Volatilità Annua (%)": {"before": vol_old, "after": vol_new, "delta": delta_vol, "format": "{:.2f}%", "lower_better": True},
            "Sharpe Ratio": {"before": sharpe_old, "after": sharpe_new, "delta": delta_sharpe, "format": "{:.2f}"},
            "Beta di Portafoglio": {"before": beta_old, "after": beta_new, "delta": delta_beta, "format": "{:.2f}"},
            "Diversification Ratio": {"before": dr_old, "after": dr_new, "delta": delta_dr, "format": "{:.2f}x"}
        },
        "weights_table": pd.DataFrame({
            "Ticker": df_returns.columns,
            "Peso Attuale %": np.round(w_old * 100.0, 2),
            "Nuovo Peso %": np.round(w_new * 100.0, 2),
            "Delta Allocazione %": np.round((w_new - w_old) * 100.0, 2)
        }).sort_values(by="Nuovo Peso %", ascending=False)
    }


def compute_market_and_watchlist_alerts(df_screened: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Rileva segnali e anomalie quantitative su un insieme di titoli screenati o in watchlist:
    - Oversold Quality (RSI < 35 & Altman Z > 2.8)
    - Deep Value & High Upside (Upside > 15% & P/E < 18)
    - High Growth Momentum (1Y Perf > 20% & RSI 50-70)
    - Solvency / Leverage Alert (Altman Z < 1.8 o Debt/Equity > 2.5)
    """
    alerts = []
    if df_screened.empty:
        return alerts

    for _, r in df_screened.iterrows():
        tk = r.get("ticker", "N/A")
        name = r.get("name", tk)
        rsi = r.get("rsi_14", 50.0)
        z = r.get("altman_z_score", np.nan)
        upside = r.get("upside_pct", np.nan)
        pe = r.get("trailing_pe", np.nan)
        perf_1y = r.get("perf_1y_pct", np.nan)
        de = r.get("debt_to_equity", np.nan)
        
        # 1. Oversold Quality
        if pd.notna(rsi) and rsi < 35.0 and pd.notna(z) and z >= 2.6:
            alerts.append({
                "ticker": tk,
                "name": name,
                "type": "opportunity",
                "badge": "🟢 OVERSOLD QUALITY",
                "color": "#3fb950",
                "description": f"Titolo con solida qualità di bilancio (Altman Z: {z:.2f}) temporaneamente ipervenduto (RSI: {rsi:.1f})."
            })
            
        # 2. Deep Value
        if pd.notna(upside) and upside >= 15.0 and pd.notna(pe) and 0 < pe <= 16.0:
            alerts.append({
                "ticker": tk,
                "name": name,
                "type": "opportunity",
                "badge": "💎 DEEP VALUE",
                "color": "#58a6ff",
                "description": f"Forte sconto sul Fair Value (Upside: {upside:+.1f}%) associato a multiplo P/E contenuto ({pe:.1f}x)."
            })
            
        # 3. High Momentum Breakout
        if pd.notna(perf_1y) and perf_1y >= 20.0 and pd.notna(rsi) and 50.0 <= rsi <= 70.0:
            alerts.append({
                "ticker": tk,
                "name": name,
                "type": "momentum",
                "badge": "🚀 MOMENTUM BREAKOUT",
                "color": "#d2a8ff",
                "description": f"Trend rialzista consolidato a 12 mesi (+{perf_1y:.1f}%) con RSI equilibrato ({rsi:.1f})."
            })
            
        # 4. Solvency Warning
        if (pd.notna(z) and z < 1.8) or (pd.notna(de) and de > 2.5):
            alerts.append({
                "ticker": tk,
                "name": name,
                "type": "warning",
                "badge": "⚠️ LEVERAGE & SOLVENCY RISK",
                "color": "#f85149",
                "description": f"Livello di indebitamento o rischio insolvenza elevato (Altman Z: {z if pd.notna(z) else 'N/D'}, D/E: {de if pd.notna(de) else 'N/D'})."
            })

    return alerts


def compute_optimal_candidate_weight(
    current_positions_df: pd.DataFrame,
    candidate_ticker: str,
    benchmark_ticker: str = "SPY"
) -> Dict[str, Any]:
    """
    Calcola la quota di portafoglio ottimale (0.5% - 30%) per un titolo candidato.
    Ottimizza per:
    1. Massimo Indice di Sharpe (Max Sharpe Weight)
    2. Massima Diversificazione (Max Choueifaty DR)
    3. Analisi della frontiera rischio/rendimento marginale
    """
    clean_cand = str(candidate_ticker).strip().upper()
    if current_positions_df is None or current_positions_df.empty:
        return {"valid": False, "message": "Nessun portafoglio attivo caricato."}
        
    df_pos = current_positions_df.copy()
    if "current_value" not in df_pos.columns:
        df_pos["current_value"] = 1000.0
    tot_val = df_pos["current_value"].sum()
    if tot_val <= 0:
        tot_val = 1000.0
    df_pos["weight"] = df_pos["current_value"] / tot_val
    
    tickers = list(df_pos["ticker"].unique())
    all_tickers = list(dict.fromkeys(tickers + [clean_cand]))
    
    price_dict = {}
    for tk in all_tickers:
        df_h = get_cached_ticker_history(tk)
        if df_h is not None and not df_h.empty and "close" in df_h.columns:
            price_dict[tk] = df_h["close"]
            
    df_prices = pd.DataFrame(price_dict).dropna(how="all").ffill().dropna()
    if df_prices.empty or df_prices.shape[1] < 1 or clean_cand not in df_prices.columns:
        return {"valid": False, "message": f"Dati storici insufficienti per {clean_cand}."}
        
    df_returns = df_prices.pct_change().dropna()
    if df_returns.empty or len(df_returns) < 30:
        return {"valid": False, "message": "Storico rendimenti troppo breve per una simulazione accurata."}
        
    w_old_map = {r["ticker"]: r["weight"] for _, r in df_pos.iterrows()}
    w_old = np.array([w_old_map.get(c, 0.0) for c in df_returns.columns])
    w_old = w_old / w_old.sum() if w_old.sum() > 0 else np.ones(len(df_returns.columns)) / len(df_returns.columns)
    
    cand_idx = df_returns.columns.get_loc(clean_cand)
    rf = 3.0
    vols = df_returns.std() * np.sqrt(252) * 100.0
    
    # Metriche Base Portafoglio Attuale
    ret_old = (df_returns * w_old).sum(axis=1)
    base_cagr = float(ret_old.mean() * 252 * 100.0)
    base_vol = float(ret_old.std() * np.sqrt(252) * 100.0)
    base_sharpe = float((base_cagr - rf) / max(0.01, base_vol))
    base_dr = float((w_old * vols).sum() / max(0.01, base_vol))
    
    # Griglia di simulazione da 0.5% a 30% con passo 0.5%
    best_sharpe = base_sharpe
    best_sharpe_w = 0.0
    best_dr = base_dr
    best_dr_w = 0.0
    
    grid = np.linspace(0.005, 0.30, 60)
    curve_data = []
    
    for w in grid:
        w_test = w_old * (1.0 - w)
        w_test[cand_idx] += w
        w_test = w_test / w_test.sum()
        
        r_test = (df_returns * w_test).sum(axis=1)
        cagr_t = float(r_test.mean() * 252 * 100.0)
        vol_t = float(r_test.std() * np.sqrt(252) * 100.0)
        sh_t = float((cagr_t - rf) / max(0.01, vol_t))
        dr_t = float((w_test * vols).sum() / max(0.01, vol_t))
        
        curve_data.append({
            "weight_pct": round(w * 100.0, 1),
            "sharpe_ratio": round(sh_t, 3),
            "volatility_pct": round(vol_t, 2),
            "cagr_pct": round(cagr_t, 2),
            "diversification_ratio": round(dr_t, 2)
        })
        
        if sh_t > best_sharpe:
            best_sharpe = sh_t
            best_sharpe_w = w
            
        if dr_t > best_dr:
            best_dr = dr_t
            best_dr_w = w
            
    optimal_weight_pct = round(best_sharpe_w * 100.0, 1) if best_sharpe_w > 0 else 5.0
    
    return {
        "valid": True,
        "candidate_ticker": clean_cand,
        "base_sharpe": round(base_sharpe, 3),
        "base_volatility": round(base_vol, 2),
        "base_cagr": round(base_cagr, 2),
        "base_dr": round(base_dr, 2),
        "optimal_sharpe_weight_pct": optimal_weight_pct,
        "optimal_sharpe": round(best_sharpe, 3),
        "delta_sharpe_optimal": round(best_sharpe - base_sharpe, 3),
        "max_dr_weight_pct": round(best_dr_w * 100.0, 1) if best_dr_w > 0 else optimal_weight_pct,
        "curve_df": pd.DataFrame(curve_data)
    }

