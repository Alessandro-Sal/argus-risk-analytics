import pandas as pd
import numpy as np
import yfinance as yf
import random
from datetime import datetime, timedelta

def generate_realistic_portfolio(output_path, start_date="1990-01-01", end_date="2026-07-12"):
    print("Scaricando i dati storici per avere prezzi reali...")
    
    # Tickers storici che partono almeno dagli anni '90 (o vicini)
    tickers = {
        "AAPL": "1990-01-01",
        "MSFT": "1990-01-01",
        "JNJ": "1990-01-01",
        "WMT": "1990-01-01",
        "PG": "1990-01-01",
        "KO": "1990-01-01",
        "PEP": "1990-01-01",
        "DIS": "1990-01-01",
        "INTC": "1990-01-01",
        "IBM": "1990-01-01",
        "AMZN": "1997-06-01",
        "NVDA": "1999-02-01",
        "GOOGL": "2004-09-01",
        "META": "2012-06-01",
        "TSLA": "2010-07-01",
    }
    
    # Scarica i dati per trovare i giorni in cui il mercato era aperto e i prezzi
    data = yf.download(list(tickers.keys()), start=start_date, end=end_date)["Close"]
    
    # Riempiamo in avanti i prezzi per evitare NaN nei giorni di mercato
    data = data.ffill()
    
    print("Generazione transazioni in corso...")
    
    transactions = []
    positions = {tk: 0.0 for tk in tickers.keys()}
    
    # Costruiamo un piano di investimenti mensile + trade casuali
    date_range = data.index
    
    for current_date in date_range:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Facciamo finta che l'utente faccia trade circa 3-5 volte al mese (1 su 4 giorni lavorativi)
        if random.random() < 0.25:
            # Scegli 1-3 ticker da tradare oggi
            num_trades = random.randint(1, 3)
            
            # Filtra i ticker che sono "nati" prima della data corrente e che hanno dati
            available_tickers = [tk for tk, start in tickers.items() if date_str >= start and pd.notna(data.loc[current_date, tk])]
            if not available_tickers:
                continue
                
            chosen_tickers = random.sample(available_tickers, min(num_trades, len(available_tickers)))
            
            for tk in chosen_tickers:
                price = float(data.loc[current_date, tk])
                if pd.isna(price) or price <= 0:
                    continue
                
                # Decidiamo se comprare o vendere
                # Se non abbiamo posizioni, compriamo. Se ne abbiamo, 70% buy, 30% sell
                if positions[tk] <= 0:
                    action = "buy"
                else:
                    action = "buy" if random.random() < 0.7 else "sell"
                
                if action == "buy":
                    # Investimento casuale tra $500 e $5000
                    investment = random.uniform(500, 5000)
                    qty = investment / price
                    positions[tk] += qty
                    fee = max(1.0, investment * 0.001) # 0.1% fee
                    
                    transactions.append({
                        "tx_date": date_str,
                        "ticker": tk,
                        "tx_type": "buy",
                        "quantity": round(qty, 4),
                        "price": round(price, 2),
                        "currency": "USD",
                        "fees": round(fee, 2),
                        "asset_class": "stock",
                        "notes": "Acquisto periodico" if random.random() < 0.8 else "Opportunità"
                    })
                
                elif action == "sell":
                    # Vendiamo tra il 10% e il 100% della posizione
                    sell_fraction = random.uniform(0.1, 1.0)
                    qty = positions[tk] * sell_fraction
                    positions[tk] -= qty
                    revenue = qty * price
                    fee = max(1.0, revenue * 0.001)
                    
                    transactions.append({
                        "tx_date": date_str,
                        "ticker": tk,
                        "tx_type": "sell",
                        "quantity": round(qty, 4),
                        "price": round(price, 2),
                        "currency": "USD",
                        "fees": round(fee, 2),
                        "asset_class": "stock",
                        "notes": "Presa di profitto" if sell_fraction < 0.8 else "Liquidazione"
                    })
                    
        # Simulate dividends? Let's just do buy/sell for simplicity, or we could inject random dividends
        if random.random() < 0.01: # 1% of days we get a dividend for a stock we hold
            held_tickers = [tk for tk, qty in positions.items() if qty > 0]
            if held_tickers:
                tk = random.choice(held_tickers)
                div_amount = positions[tk] * random.uniform(0.01, 0.05) # dummy dividend per share
                transactions.append({
                    "tx_date": date_str,
                    "ticker": tk,
                    "tx_type": "dividend",
                    "quantity": 1.0,
                    "price": round(div_amount, 2), # price = importo del dividendo in questo caso
                    "currency": "USD",
                    "fees": 0.0,
                    "asset_class": "stock",
                    "notes": "Dividendo"
                })

    
    df = pd.DataFrame(transactions)
    print(f"Generate {len(df)} transazioni reali dal 1990. Salvataggio in {output_path}...")
    df.to_csv(output_path, index=False)
    print("Fatto!")

if __name__ == "__main__":
    generate_realistic_portfolio("data/test_portfolio_realistic_90s.csv")
