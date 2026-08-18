"""
scripts/generate_realistic_portfolio.py
============================================================
ARGUS Risk Analytics Platform — Realistic Portfolio Generator

Generates a 100% realistic, authentic, and compliant portfolio CSV
based on real Yahoo Finance historical market prices, real dividend
ex-dates & payout rates, multi-asset diversification (Stock, ETF,
Bond, Crypto), and multi-currency transactions (USD, EUR, GBP).

Adheres strictly to docs/CSV_Format_Specification.md.
============================================================
"""

import os
import sys
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf

# Root path configuration
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Target output files
OUT_FILE_REALISTIC = DATA_DIR / "test_portfolio_realistic.csv"
OUT_FILE_90S = DATA_DIR / "test_portfolio_realistic_90s.csv"


# ─────────────────────────────────────────────────────────────
# 1. Definizione dell'Universo di Asset
# ─────────────────────────────────────────────────────────────
ASSET_UNIVERSE = {
    # ── US Blue Chips & Dividend Aristocrats (USD) ──
    "KO":    {"name": "The Coca-Cola Company", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    "JNJ":   {"name": "Johnson & Johnson", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    "PG":    {"name": "Procter & Gamble", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    "WMT":   {"name": "Walmart Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    "IBM":   {"name": "International Business Machines", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    "DIS":   {"name": "The Walt Disney Company", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    "PEP":   {"name": "PepsiCo, Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    
    # ── Tech Growth & Mega-Caps (USD) ──
    "MSFT":  {"name": "Microsoft Corporation", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    "AAPL":  {"name": "Apple Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    "INTC":  {"name": "Intel Corporation", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990},
    "AMZN":  {"name": "Amazon.com, Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1997},
    "NVDA":  {"name": "NVIDIA Corporation", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1999},
    "GOOGL": {"name": "Alphabet Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 2004},
    "TSLA":  {"name": "Tesla, Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 2010},
    "META":  {"name": "Meta Platforms, Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 2012},
    
    # ── European Equities (EUR / DKK) ──
    "ISP.MI":  {"name": "Intesa Sanpaolo S.p.A.", "asset_class": "Stock", "currency": "EUR", "fee": 2.00, "start_year": 2000},
    "BMW.DE":  {"name": "Bayerische Motoren Werke AG", "asset_class": "Stock", "currency": "EUR", "fee": 2.00, "start_year": 2000},
    "ASML.AS": {"name": "ASML Holding N.V.", "asset_class": "Stock", "currency": "EUR", "fee": 2.00, "start_year": 2005},
    
    # ── Core Global & Sector ETFs (USD / EUR / GBP) ──
    "SPY":     {"name": "SPDR S&P 500 ETF Trust", "asset_class": "ETF", "currency": "USD", "fee": 1.00, "start_year": 1993},
    "QQQ":     {"name": "Invesco QQQ Trust (Nasdaq 100)", "asset_class": "ETF", "currency": "USD", "fee": 1.00, "start_year": 1999},
    "VWRL.L":  {"name": "Vanguard FTSE All-World UCITS ETF", "asset_class": "ETF", "currency": "GBP", "fee": 2.00, "start_year": 2012},
    
    # ── Bonds & Fixed Income (USD) ──
    "BND":     {"name": "Vanguard Total Bond Market ETF", "asset_class": "Bond", "currency": "USD", "fee": 1.00, "start_year": 2007},
    
    # ── Crypto Assets (USD) ──
    "BTC-USD": {"name": "Bitcoin USD", "asset_class": "Crypto", "currency": "USD", "fee": 2.50, "start_year": 2018},
    "ETH-USD": {"name": "Ethereum USD", "asset_class": "Crypto", "currency": "USD", "fee": 2.50, "start_year": 2019},
}


def fetch_all_market_data():
    """Scarica prezzi storici e serie dei dividendi reali per tutti i ticker."""
    print("📡 Download dei dati storici reali da Yahoo Finance...")
    all_tickers = list(ASSET_UNIVERSE.keys())
    
    prices_dict = {}
    dividends_dict = {}
    
    start_str = "1990-01-01"
    end_str = datetime.today().strftime("%Y-%m-%d")
    
    for ticker in all_tickers:
        try:
            print(f"   • Scaricamento {ticker:8s} ...", end="", flush=True)
            yf_obj = yf.Ticker(ticker)
            hist = yf_obj.history(start=start_str, end=end_str, auto_adjust=False)
            
            if not hist.empty:
                # Yahoo Finance date index tz-naive normalization
                hist.index = hist.index.tz_localize(None) if hist.index.tz is not None else hist.index
                hist["date_str"] = hist.index.strftime("%Y-%m-%d")
                prices_dict[ticker] = hist
                
                # Dividends series
                divs = yf_obj.dividends
                if divs is not None and not divs.empty:
                    divs.index = divs.index.tz_localize(None) if divs.index.tz is not None else divs.index
                    dividends_dict[ticker] = divs
                else:
                    dividends_dict[ticker] = pd.Series(dtype=float)
                    
                print(f" OK ({len(hist)} barre giornaliere, {len(dividends_dict[ticker])} dividendi)")
            else:
                print(" ⚠️ Nessun dato")
        except Exception as e:
            print(f" ❌ Errore: {e}")
            
    return prices_dict, dividends_dict


def get_market_price(prices_df: pd.DataFrame, target_date: pd.Timestamp) -> float:
    """Restituisce il prezzo di chiusura reale più vicino disponibile alla data target."""
    if prices_df is None or prices_df.empty:
        return None
    # Trova la riga esatta o la precedente giornata di negoziazione
    valid_dates = prices_df.index[prices_df.index <= target_date]
    if len(valid_dates) == 0:
        # Se la data è prima dell'inizio delle quotazioni, prendi la prima disponibile
        valid_dates = prices_df.index[prices_df.index >= target_date]
        if len(valid_dates) == 0:
            return None
        closest_idx = valid_dates[0]
    else:
        closest_idx = valid_dates[-1]
        
    row = prices_df.loc[closest_idx]
    price = float(row.get("Close", row.get("Adj Close", 100.0)))
    actual_date = closest_idx.strftime("%Y-%m-%d")
    return price, actual_date


def generate_portfolio_events(prices_dict, dividends_dict):
    """
    Costruisce l'intera cronologia di investimento con acquisti, vendite,
    ribilanciamenti e accrediti di dividendi reali calcolati sulle ex-date.
    """
    print("\n🔨 Costruzione delle transazioni e simulazione del piano di accumulo...")
    
    transactions = []
    current_holdings = {t: 0.0 for t in ASSET_UNIVERSE}
    
    # ── Timeline di Generazione (1990 -> 2026) ──
    # Creiamo date di PAC periodico e interventi tattici
    
    # Inizializziamo un generatore con seed deterministico per riproducibilità
    rng = random.Random(42)
    
    # 1. Allocazione iniziale 1990-1994 (Blue Chips classiche)
    initial_allocations = [
        ("1990-01-15", "WMT", 40, "Acquisto iniziale Core"),
        ("1990-01-18", "KO",  50, "Acquisto iniziale Dividend Aristocrat"),
        ("1990-01-18", "JNJ", 30, "Acquisto iniziale Healthcare Core"),
        ("1990-01-22", "IBM", 20, "Acquisto iniziale Tech Leader"),
        ("1990-01-25", "PG",  25, "Acquisto iniziale Consumer Defensive"),
        ("1990-02-12", "DIS", 30, "Acquisto iniziale Entertainment"),
        ("1990-02-20", "MSFT", 60, "Acquisto iniziale Software"),
        ("1990-03-05", "AAPL", 80, "Acquisto iniziale Hardware Tech"),
        ("1990-03-15", "INTC", 50, "Acquisto iniziale Semiconductors"),
        ("1990-04-10", "PEP", 35, "Acquisto iniziale Consumer Goods"),
    ]
    
    for dt_str, ticker, qty, note in initial_allocations:
        dt = pd.to_datetime(dt_str)
        if ticker in prices_dict:
            res = get_market_price(prices_dict[ticker], dt)
            if res:
                price, actual_dt = res
                meta = ASSET_UNIVERSE[ticker]
                transactions.append({
                    "tx_date": actual_dt,
                    "ticker": ticker,
                    "tx_type": "buy",
                    "quantity": float(qty),
                    "price": round(price, 2),
                    "currency": meta["currency"],
                    "fees": meta["fee"],
                    "asset_class": meta["asset_class"],
                    "notes": note
                })
                current_holdings[ticker] += qty

    # 2. Generazione DCA Periodico e ribilanciamenti su base trimestrale dal 1991 al 2026
    start_date = pd.to_datetime("1991-01-15")
    end_date = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
    
    current_date = start_date
    
    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        
        # Filtra i ticker attivi in questo anno
        active_tickers = [t for t, m in ASSET_UNIVERSE.items() if m["start_year"] <= year]
        
        # ── PAC Trimestrale (Gennaio, Aprile, Luglio, Ottobre) ──
        if month in [1, 4, 7, 10]:
            # Seleziona 3-5 ticker per il PAC periodico
            quarterly_picks = rng.sample(active_tickers, min(len(active_tickers), rng.randint(3, 5)))
            
            for ticker in quarterly_picks:
                meta = ASSET_UNIVERSE[ticker]
                if ticker in prices_dict:
                    res = get_market_price(prices_dict[ticker], current_date)
                    if res:
                        price, actual_dt = res
                        # Quantità calcolata in base al prezzo (es. ~300 - 800 USD/EUR per acquisto)
                        target_investment = rng.uniform(350, 750)
                        
                        if meta["asset_class"] == "Crypto":
                            qty = round(target_investment / price, 4)
                        else:
                            qty = max(1, int(target_investment / price))
                            
                        if qty > 0 and price > 0:
                            transactions.append({
                                "tx_date": actual_dt,
                                "ticker": ticker,
                                "tx_type": "buy",
                                "quantity": float(qty),
                                "price": round(price, 2),
                                "currency": meta["currency"],
                                "fees": meta["fee"],
                                "asset_class": meta["asset_class"],
                                "notes": f"PAC Trimestrale Q{(month-1)//3 + 1} {year}"
                            })
                            current_holdings[ticker] += qty
                            
        # ── Ingressi Tattici & Prese di Profitto (Opportunità di mercato) ──
        # Simulazione prese di beneficio su posizioni ampie con forte guadagno
        if month in [3, 9] and rng.random() < 0.45:
            candidate_sells = [t for t, q in current_holdings.items() if q >= 10 and ASSET_UNIVERSE[t]["asset_class"] != "Bond"]
            if candidate_sells:
                sell_ticker = rng.choice(candidate_sells)
                meta = ASSET_UNIVERSE[sell_ticker]
                res = get_market_price(prices_dict[sell_ticker], current_date)
                if res:
                    price, actual_dt = res
                    # Vendi tra il 15% e il 30% delle quote possedute
                    sell_qty = max(1, int(current_holdings[sell_ticker] * rng.uniform(0.15, 0.30)))
                    
                    if sell_qty <= current_holdings[sell_ticker]:
                        transactions.append({
                            "tx_date": actual_dt,
                            "ticker": sell_ticker,
                            "tx_type": "sell",
                            "quantity": float(sell_qty),
                            "price": round(price, 2),
                            "currency": meta["currency"],
                            "fees": meta["fee"],
                            "asset_class": meta["asset_class"],
                            "notes": f"Presa di profitto parziale / Ribilanciamento {year}"
                        })
                        current_holdings[sell_ticker] -= sell_qty
                        
        # Avanza di 1 mese
        # Trova il primo giorno lavorativo del mese successivo
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        current_date = pd.to_datetime(f"{next_year:04d}-{next_month:02d}-15")
        
    print(f"   • Generate {len(transactions)} transazioni di compravendita (buy/sell).")
    
    # ── 3. Calcolo e Generazione Dividendi Reali su Ex-Date ──
    print("💰 Calcolo dei dividendi reali su base quote possedute alle ex-date...")
    
    # Convertiamo le transazioni in DataFrame temporaneo per tracciare le quote a ogni data
    df_tx_temp = pd.DataFrame(transactions)
    df_tx_temp["dt"] = pd.to_datetime(df_tx_temp["tx_date"])
    df_tx_temp = df_tx_temp.sort_values("dt").reset_index(drop=True)
    
    dividend_transactions = []
    
    for ticker, div_series in dividends_dict.items():
        if div_series is None or div_series.empty:
            continue
            
        meta = ASSET_UNIVERSE[ticker]
        ticker_txs = df_tx_temp[df_tx_temp["ticker"] == ticker].copy()
        
        if ticker_txs.empty:
            continue
            
        for ex_date, div_rate in div_series.items():
            ex_date_ts = pd.to_datetime(ex_date)
            
            # Calcola quote possedute alla data di stacco (strettamente prima o il giorno stesso)
            prior_buys = ticker_txs[(ticker_txs["dt"] <= ex_date_ts) & (ticker_txs["tx_type"] == "buy")]["quantity"].sum()
            prior_sells = ticker_txs[(ticker_txs["dt"] <= ex_date_ts) & (ticker_txs["tx_type"] == "sell")]["quantity"].sum()
            held_shares = prior_buys - prior_sells
            
            if held_shares > 0 and div_rate > 0:
                payout_total = held_shares * div_rate
                # Considera solo dividendi con importo significativo (> $0.10)
                if payout_total >= 0.10:
                    dividend_transactions.append({
                        "tx_date": ex_date_ts.strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "tx_type": "dividend",
                        "quantity": 1.0,  # Conforme a CSV_Format_Specification.md: quantity = 1
                        "price": round(payout_total, 2),  # Prezzo = importo totale netto incassato
                        "currency": meta["currency"],
                        "fees": 0.0,
                        "asset_class": meta["asset_class"],
                        "notes": f"Dividendo ({held_shares:.0f} quote @ {div_rate:.4f} {meta['currency']})"
                    })
                    
    print(f"   • Generati {len(dividend_transactions)} flussi di dividendi reali.")
    
    # ── 4. Unione, Ordinamento Cronologico e Pulizia ──
    all_records = transactions + dividend_transactions
    df_final = pd.DataFrame(all_records)
    df_final["dt"] = pd.to_datetime(df_final["tx_date"])
    df_final = df_final.sort_values(["dt", "ticker", "tx_type"]).reset_index(drop=True)
    
    # Rimuovi colonna ausiliaria
    df_final = df_final.drop(columns=["dt"])
    
    return df_final


def verify_portfolio_invariants(df: pd.DataFrame):
    """Verifica che tutte le quantità rimangano non-negative (FIFO Solvency)."""
    print("\n🔍 Verifica degli invarianti di consistenza e solvenza...")
    errors = []
    
    for ticker, grp in df.groupby("ticker"):
        running_qty = 0.0
        for idx, row in grp.iterrows():
            if row["tx_type"] == "buy":
                running_qty += float(row["quantity"])
            elif row["tx_type"] == "sell":
                running_qty -= float(row["quantity"])
                if running_qty < -1e-5:
                    errors.append(f"Errore Solvenza: {ticker} a data {row['tx_date']} ha quantità negativa: {running_qty:.4f}")
            elif row["tx_type"] == "dividend":
                if row["quantity"] != 1.0:
                    errors.append(f"Errore Dividendo: {ticker} a data {row['tx_date']} ha quantity={row['quantity']} (deve essere 1.0)")
                if row["price"] <= 0:
                    errors.append(f"Errore Dividendo: {ticker} a data {row['tx_date']} ha price={row['price']} <= 0")
                    
        print(f"   • {ticker:8s} | Posizione finale: {running_qty:8.2f} quote | Invariante: {'✅ OK' if running_qty >= 0 else '❌ NEGATIVA'}")
        
    if errors:
        print("\n❌ Rilevati errori negli invarianti:")
        for err in errors[:10]:
            print(f"   - {err}")
        raise ValueError(f"Invarianti violati: {len(errors)} errori.")
    else:
        print("✅ Tutti gli invarianti di portafoglio sono rispettati al 100%!")


def main():
    print("="*70)
    print("🚀 ARGUS Platform — Generatore Dataset Portafoglio Realistico")
    print("="*70)
    
    prices_dict, dividends_dict = fetch_all_market_data()
    
    df_portfolio = generate_portfolio_events(prices_dict, dividends_dict)
    
    verify_portfolio_invariants(df_portfolio)
    
    # Salvataggio su data/
    print(f"\n💾 Scrittura file CSV in {DATA_DIR} ...")
    df_portfolio.to_csv(OUT_FILE_REALISTIC, index=False, encoding="utf-8")
    print(f"   ✅ Salvato: {OUT_FILE_REALISTIC} ({len(df_portfolio)} righe, {OUT_FILE_REALISTIC.stat().st_size / 1024:.1f} KB)")
    
    # Aggiornamento anche di test_portfolio_realistic_90s.csv per mantenere allineati entrambi
    df_portfolio.to_csv(OUT_FILE_90S, index=False, encoding="utf-8")
    print(f"   ✅ Salvato: {OUT_FILE_90S} ({len(df_portfolio)} righe)")
    
    # Statistiche riassuntive
    print("\n📊 RIEPILOGO STATISTICO DEL PORTAFOGLIO:")
    print(f"   • Totale transazioni: {len(df_portfolio)}")
    print(f"   • Distribuzione tipi: {df_portfolio['tx_type'].value_counts().to_dict()}")
    print(f"   • Asset Class:       {df_portfolio['asset_class'].value_counts().to_dict()}")
    print(f"   • Valute:            {df_portfolio['currency'].value_counts().to_dict()}")
    print(f"   • Ticker unici ({len(df_portfolio['ticker'].unique())}): {sorted(df_portfolio['ticker'].unique().tolist())}")
    print(f"   • Intervallo date:   {df_portfolio['tx_date'].min()} -> {df_portfolio['tx_date'].max()}")
    print(f"   • Totale fees:       €/$ {df_portfolio['fees'].sum():.2f}")
    
    # Anteprima prime e ultime righe
    print("\n🔎 ANTEPRIMA INIZIO DATASET:")
    print(df_portfolio.head(6))
    print("\n🔎 ANTEPRIMA FINE DATASET:")
    print(df_portfolio.tail(6))
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
