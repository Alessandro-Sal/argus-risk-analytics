"""
scripts/generate_realistic_portfolio.py
============================================================
ARGUS Risk Analytics Platform — Quantitative Simulation Engine
Synthetic Financial Data & Realistic Portfolio Generator

Generates 100% realistic, authentic, and accounting-compliant
datasets for both Trading (portfolio transactions conforming to
docs/CSV_Format_Specification.md) and Wealth Management
(multi-account cashflows, French mortgage amortization, periodic
illiquid asset appraisals with haircuts, and pension deductibility).

Supports 3 Pre-configured User Archetypes:
1. Young Accumulator (High risk tolerance, 20+ yr horizon, tech/crypto, aggressive PAC, zero real estate)
2. FIRE / Decumulation (High net worth, dividend aristocrats & bonds, constant SWR 3.5%, debt-free)
3. HNWI / Family Office (Multi-asset €3.5M+, French mortgage, watches/gold caveau, rental income, max pension deduction)
============================================================
"""

import os
import sys
import math
import random
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

# Root path configuration
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ARCHETYPES_DIR = DATA_DIR / "archetypes"
ARCHETYPES_DIR.mkdir(parents=True, exist_ok=True)

# Default output files for legacy compatibility
OUT_FILE_REALISTIC = DATA_DIR / "test_portfolio_realistic.csv"
OUT_FILE_90S = DATA_DIR / "test_portfolio_realistic_90s.csv"


# ─────────────────────────────────────────────────────────────
# 1. Calendario di Mercato & Trading Days Helper
# ─────────────────────────────────────────────────────────────

class MarketCalendarHelper:
    """
    Gestisce il calendario di negoziazione escludendo i fine settimana
    e le principali festività borsistiche internazionali (NYSE, Euronext, Borsa Italiana).
    """

    @staticmethod
    def is_weekend(dt: datetime) -> bool:
        return dt.weekday() >= 5

    @staticmethod
    def is_market_holiday(dt: datetime) -> bool:
        month = dt.month
        day = dt.day

        # Capodanno (1 Gennaio)
        if month == 1 and day == 1:
            return True
        # Festa del Lavoro (1 Maggio)
        if month == 5 and day == 1:
            return True
        # Ferragosto (15 Agosto)
        if month == 8 and day == 15:
            return True
        # Natale e Santo Stefano (25 e 26 Dicembre)
        if month == 12 and day in (25, 26):
            return True
        # US Independence Day (4 Luglio)
        if month == 7 and day == 4:
            return True
        # US Juneteenth (19 Giugno)
        if month == 6 and day == 19:
            return True

        # MLK Day: 3° lunedì di gennaio
        if month == 1 and dt.weekday() == 0 and 15 <= day <= 21:
            return True
        # Washington's Birthday / Presidents Day: 3° lunedì di febbraio
        if month == 2 and dt.weekday() == 0 and 15 <= day <= 21:
            return True
        # Memorial Day: ultimo lunedì di maggio
        if month == 5 and dt.weekday() == 0 and day >= 25:
            return True
        # Labor Day: 1° lunedì di settembre
        if month == 9 and dt.weekday() == 0 and day <= 7:
            return True
        # Thanksgiving: 4° giovedì di novembre
        if month == 11 and dt.weekday() == 3 and 22 <= day <= 28:
            return True

        return False

    @classmethod
    def is_trading_day(cls, dt: datetime) -> bool:
        return not cls.is_weekend(dt) and not cls.is_market_holiday(dt)

    @classmethod
    def get_next_trading_day(cls, dt: datetime) -> datetime:
        curr = dt
        while not cls.is_trading_day(curr):
            curr += timedelta(days=1)
        return curr

    @classmethod
    def get_trading_days(cls, start_dt: datetime, end_dt: datetime) -> List[datetime]:
        days = []
        curr = start_dt
        while curr <= end_dt:
            if cls.is_trading_day(curr):
                days.append(curr)
            curr += timedelta(days=1)
        return days


# ─────────────────────────────────────────────────────────────
# 2. Universo Strumenti & Motore Prezzi / Dividendi
# ─────────────────────────────────────────────────────────────

ASSET_UNIVERSE = {
    # ── US Blue Chips & Dividend Aristocrats (USD) ──
    "KO":    {"name": "The Coca-Cola Company", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 60.0, "annual_div": 1.94, "div_months": [3, 6, 9, 12]},
    "JNJ":   {"name": "Johnson & Johnson", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 155.0, "annual_div": 4.96, "div_months": [2, 5, 8, 11]},
    "PG":    {"name": "Procter & Gamble", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 160.0, "annual_div": 4.02, "div_months": [1, 4, 7, 10]},
    "WMT":   {"name": "Walmart Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 68.0, "annual_div": 0.83, "div_months": [3, 5, 8, 12]},
    "IBM":   {"name": "International Business Machines", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 190.0, "annual_div": 6.68, "div_months": [2, 5, 8, 11]},
    "DIS":   {"name": "The Walt Disney Company", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 95.0, "annual_div": 0.90, "div_months": [1, 7]},
    "PEP":   {"name": "PepsiCo, Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 170.0, "annual_div": 5.42, "div_months": [1, 3, 6, 9]},

    # ── Tech Growth & Mega-Caps (USD) ──
    "MSFT":  {"name": "Microsoft Corporation", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 420.0, "annual_div": 3.30, "div_months": [2, 5, 8, 11]},
    "AAPL":  {"name": "Apple Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 220.0, "annual_div": 1.00, "div_months": [2, 5, 8, 11]},
    "INTC":  {"name": "Intel Corporation", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1990, "base_price": 30.0, "annual_div": 0.50, "div_months": [2, 5, 8, 11]},
    "AMZN":  {"name": "Amazon.com, Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1997, "base_price": 185.0, "annual_div": 0.0, "div_months": []},
    "NVDA":  {"name": "NVIDIA Corporation", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 1999, "base_price": 125.0, "annual_div": 0.16, "div_months": [3, 6, 9, 12]},
    "GOOGL": {"name": "Alphabet Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 2004, "base_price": 170.0, "annual_div": 0.80, "div_months": [3, 6, 9, 12]},
    "TSLA":  {"name": "Tesla, Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 2010, "base_price": 210.0, "annual_div": 0.0, "div_months": []},
    "META":  {"name": "Meta Platforms, Inc.", "asset_class": "Stock", "currency": "USD", "fee": 1.50, "start_year": 2012, "base_price": 500.0, "annual_div": 2.00, "div_months": [3, 6, 9, 12]},

    # ── European Equities (EUR) ──
    "ISP.MI":  {"name": "Intesa Sanpaolo S.p.A.", "asset_class": "Stock", "currency": "EUR", "fee": 2.00, "start_year": 2000, "base_price": 3.60, "annual_div": 0.30, "div_months": [5, 11]},
    "BMW.DE":  {"name": "Bayerische Motoren Werke AG", "asset_class": "Stock", "currency": "EUR", "fee": 2.00, "start_year": 2000, "base_price": 85.0, "annual_div": 6.00, "div_months": [5]},
    "ASML.AS": {"name": "ASML Holding N.V.", "asset_class": "Stock", "currency": "EUR", "fee": 2.00, "start_year": 2005, "base_price": 750.0, "annual_div": 6.10, "div_months": [2, 5, 8, 11]},

    # ── Core Global & Sector ETFs (USD / EUR / GBP) ──
    "SPY":     {"name": "SPDR S&P 500 ETF Trust", "asset_class": "ETF", "currency": "USD", "fee": 1.00, "start_year": 1993, "base_price": 540.0, "annual_div": 6.80, "div_months": [3, 6, 9, 12]},
    "QQQ":     {"name": "Invesco QQQ Trust (Nasdaq 100)", "asset_class": "ETF", "currency": "USD", "fee": 1.00, "start_year": 1999, "base_price": 460.0, "annual_div": 2.70, "div_months": [3, 6, 9, 12]},
    "VWRL.L":  {"name": "Vanguard FTSE All-World UCITS ETF", "asset_class": "ETF", "currency": "GBP", "fee": 2.00, "start_year": 2012, "base_price": 105.0, "annual_div": 1.95, "div_months": [3, 6, 9, 12]},

    # ── Bonds & Fixed Income (USD / EUR) ──
    "BND":     {"name": "Vanguard Total Bond Market ETF", "asset_class": "Bond", "currency": "USD", "fee": 1.00, "start_year": 2007, "base_price": 72.0, "annual_div": 2.65, "div_months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]},

    # ── Crypto Assets (USD) ──
    "BTC-USD": {"name": "Bitcoin USD", "asset_class": "Crypto", "currency": "USD", "fee": 2.50, "start_year": 2018, "base_price": 60000.0, "annual_div": 0.0, "div_months": []},
    "ETH-USD": {"name": "Ethereum USD", "asset_class": "Crypto", "currency": "USD", "fee": 2.50, "start_year": 2019, "base_price": 2600.0, "annual_div": 0.0, "div_months": []},
}


class PriceAndDividendEngine:
    """
    Fornisce serie storiche di prezzi e dividendi.
    Tenta di scaricare dati da Yahoo Finance quando online;
    in modalità offline (o se la rete fallisce) impiega una simulazione
    stocastica Geometric Brownian Motion (GBM) calibrata sui parametri empirici reali.
    """

    def __init__(self, offline: bool = False, seed: int = 42):
        self.offline = offline
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.prices_dict: Dict[str, pd.DataFrame] = {}
        self.dividends_dict: Dict[str, pd.Series] = {}

    def fetch_or_synthesize_data(
        self,
        tickers: Optional[List[str]] = None,
        start_date: str = "2023-01-01",
        end_date: Optional[str] = None
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.Series]]:
        if end_date is None:
            end_date = datetime.today().strftime("%Y-%m-%d")

        target_tickers = tickers or list(ASSET_UNIVERSE.keys())

        if not self.offline:
            try:
                import yfinance as yf
                print("📡 Connessione online Yahoo Finance...")
                for ticker in target_tickers:
                    try:
                        yf_obj = yf.Ticker(ticker)
                        hist = yf_obj.history(start=start_date, end=end_date, auto_adjust=False)
                        if not hist.empty and len(hist) > 20:
                            hist.index = hist.index.tz_localize(None) if hist.index.tz is not None else hist.index
                            hist["date_str"] = hist.index.strftime("%Y-%m-%d")
                            self.prices_dict[ticker] = hist

                            divs = yf_obj.dividends
                            if divs is not None and not divs.empty:
                                divs.index = divs.index.tz_localize(None) if divs.index.tz is not None else divs.index
                                self.dividends_dict[ticker] = divs[divs.index >= pd.to_datetime(start_date)]
                            else:
                                self.dividends_dict[ticker] = pd.Series(dtype=float)
                    except Exception:
                        pass
            except Exception:
                pass

        # Genera per i ticker mancanti o per tutti se offline
        trading_days = MarketCalendarHelper.get_trading_days(
            pd.to_datetime(start_date).to_pydatetime(),
            pd.to_datetime(end_date).to_pydatetime()
        )
        dates_idx = pd.DatetimeIndex(trading_days)

        for ticker in target_tickers:
            if ticker not in self.prices_dict or self.prices_dict[ticker].empty:
                meta = ASSET_UNIVERSE.get(ticker, {
                    "base_price": 100.0, "asset_class": "Stock",
                    "annual_div": 2.0, "div_months": [3, 6, 9, 12]
                })

                # Parametri GBM calibrati
                ac = meta.get("asset_class", "Stock")
                if ac == "Crypto":
                    mu, sigma = 0.25, 0.65
                elif ac == "Bond":
                    mu, sigma = 0.03, 0.06
                elif ac == "ETF":
                    mu, sigma = 0.09, 0.16
                else:
                    mu, sigma = 0.08, 0.22

                n_steps = len(dates_idx)
                if n_steps == 0:
                    continue

                dt_yr = 1.0 / 252.0
                shocks = self.rng.normal((mu - 0.5 * sigma**2) * dt_yr, sigma * math.sqrt(dt_yr), size=n_steps)
                price_path = meta.get("base_price", 100.0) * np.exp(np.cumsum(shocks))

                df_synth = pd.DataFrame({
                    "Close": price_path,
                    "Open": price_path * self.rng.uniform(0.995, 1.005, size=n_steps),
                    "High": price_path * self.rng.uniform(1.002, 1.015, size=n_steps),
                    "Low": price_path * self.rng.uniform(0.985, 0.998, size=n_steps),
                    "Volume": self.rng.integers(100_000, 10_000_000, size=n_steps)
                }, index=dates_idx)
                df_synth["date_str"] = df_synth.index.strftime("%Y-%m-%d")
                self.prices_dict[ticker] = df_synth

                # Serie dividendi sintetici calibrati
                ann_div = meta.get("annual_div", 0.0)
                div_months = meta.get("div_months", [])
                div_records = {}

                if ann_div > 0 and div_months:
                    per_payout = ann_div / len(div_months)
                    for yr in sorted(list(set(dates_idx.year))):
                        for m in div_months:
                            cand_dt = pd.to_datetime(f"{yr:04d}-{m:02d}-15")
                            eff_dt = MarketCalendarHelper.get_next_trading_day(cand_dt.to_pydatetime())
                            if eff_dt <= pd.to_datetime(end_date).to_pydatetime():
                                div_records[pd.Timestamp(eff_dt)] = round(per_payout * self.rng.uniform(0.98, 1.05), 4)

                self.dividends_dict[ticker] = pd.Series(div_records).sort_index()

        return self.prices_dict, self.dividends_dict

    def get_price_at(self, ticker: str, target_date: datetime) -> Optional[Tuple[float, str]]:
        if ticker not in self.prices_dict or self.prices_dict[ticker].empty:
            return None
        df = self.prices_dict[ticker]
        ts = pd.Timestamp(target_date)
        valid = df.index[df.index <= ts]
        if len(valid) == 0:
            valid = df.index[df.index >= ts]
            if len(valid) == 0:
                return None
            idx = valid[0]
        else:
            idx = valid[-1]

        row = df.loc[idx]
        price = float(row.get("Close", 100.0))
        return price, idx.strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────
# 3. Motore Ammortamento Mutuo alla Francese
# ─────────────────────────────────────────────────────────────

class FrenchMortgageEngine:
    """
    Calcola l'ammortamento alla francese con rata costante (PMT),
    scomposizione della quota capitale ed interessi mese per mese,
    e tracciamento dell'evoluzione del debito residuo.
    """

    @staticmethod
    def compute_pmt(principal: float, annual_rate_pct: float, duration_years: int) -> float:
        if principal <= 0 or duration_years <= 0:
            return 0.0
        r_monthly = (annual_rate_pct / 100.0) / 12.0
        n_months = duration_years * 12
        if r_monthly > 0:
            pmt = principal * (r_monthly * (1.0 + r_monthly)**n_months) / ((1.0 + r_monthly)**n_months - 1.0)
        else:
            pmt = principal / n_months
        return round(pmt, 2)

    @classmethod
    def generate_installment(
        cls,
        remaining_principal: float,
        monthly_payment: float,
        annual_rate_pct: float
    ) -> Tuple[float, float, float]:
        """
        Restituisce: (quota_capitale, quota_interessi, nuovo_debito_residuo).
        """
        if remaining_principal <= 0:
            return 0.0, 0.0, 0.0
        r_monthly = (annual_rate_pct / 100.0) / 12.0
        interest_part = round(remaining_principal * r_monthly, 2)
        principal_part = round(min(remaining_principal, monthly_payment - interest_part), 2)
        new_balance = round(max(0.0, remaining_principal - principal_part), 2)
        return principal_part, interest_part, new_balance


# ─────────────────────────────────────────────────────────────
# 4. Cash Ledger & Invariante di Solvibilità
# ─────────────────────────────────────────────────────────────

class CashLedger:
    """
    Mantiene i saldi dei conti correnti, risparmio e brokerage cash.
    Garantisce matematicamente la solvibilità (C_t >= 0): nessun
    prelievo, acquisto o spesa eccede la liquidità disponibile.
    """

    def __init__(
        self,
        checking: float = 0.0,
        savings: float = 0.0,
        emergency: float = 0.0,
        brokerage: float = 0.0
    ):
        self.checking = float(checking)
        self.savings = float(savings)
        self.emergency = float(emergency)
        self.brokerage = float(brokerage)
        self.min_checking_buffer = 500.0

    def credit_checking(self, amount: float):
        if amount > 0:
            self.checking = round(self.checking + amount, 2)

    def debit_checking(self, amount: float) -> float:
        """Addebita fino alla disponibilità massima senza andare a saldo negativo."""
        actual = min(self.checking, amount)
        self.checking = round(self.checking - actual, 2)
        return actual

    def credit_brokerage(self, amount: float):
        if amount > 0:
            self.brokerage = round(self.brokerage + amount, 2)

    def debit_brokerage(self, amount: float) -> float:
        actual = min(self.brokerage, amount)
        self.brokerage = round(self.brokerage - actual, 2)
        return actual

    def transfer_checking_to_brokerage(self, amount: float) -> float:
        available = max(0.0, self.checking - self.min_checking_buffer)
        transfer_amount = min(available, amount)
        if transfer_amount > 0:
            self.checking = round(self.checking - transfer_amount, 2)
            self.brokerage = round(self.brokerage + transfer_amount, 2)
        return transfer_amount

    def transfer_brokerage_to_checking(self, amount: float) -> float:
        transfer_amount = min(self.brokerage, amount)
        if transfer_amount > 0:
            self.brokerage = round(self.brokerage - transfer_amount, 2)
            self.checking = round(self.checking + transfer_amount, 2)
        return transfer_amount

    @property
    def total_liquid(self) -> float:
        return round(self.checking + self.savings + self.emergency + self.brokerage, 2)


# ─────────────────────────────────────────────────────────────
# 5. Definizione degli Archetipi Quantitativi
# ─────────────────────────────────────────────────────────────

@dataclass
class UserArchetypeConfig:
    code: str
    name: str
    description: str
    horizon_years: int
    risk_tolerance: str
    # Saldi iniziali conti
    init_checking: float
    init_savings: float
    init_emergency: float
    init_brokerage: float
    # Redditi attivi e passivi
    monthly_salary: float
    salary_growth_rate: float
    monthly_rental_income: float
    # Spese mensili
    rent_or_housing_expense: float
    utilities_bills_expense: float
    groceries_food_expense: float
    transport_expense: float
    discretionary_lifestyle_expense: float
    # Mutuo francese
    has_mortgage: bool
    mortgage_principal: float
    mortgage_rate: float
    mortgage_years: int
    # Previdenza integrativa
    has_pension: bool
    pension_name: str
    pension_provider: str
    pension_initial_value: float
    pension_monthly_employee: float
    pension_monthly_employer: float
    # Asset fisici & caveau
    physical_assets: List[Dict[str, Any]]
    # Portafoglio investimenti & PAC
    trading_universe: List[str]
    initial_allocations: List[Tuple[str, float]]  # (ticker, target_eur)
    monthly_pac_target: float
    pac_weights: Dict[str, float]
    safe_withdrawal_rate_annual: float = 0.0  # Per decumulo FIRE
    rebalance_quarterly: bool = True


ARCHETYPES: Dict[str, UserArchetypeConfig] = {
    # ── 1. GIOVANE ACCUMULATORE ──
    "young_accumulator": UserArchetypeConfig(
        code="young_accumulator",
        name="Giovane Accumulatore",
        description="Profilo ad alta propensione al rischio, orizzonte 20+ anni, 100% Equity & Crypto, PAC aggressivo, zero debiti/immobili.",
        horizon_years=25,
        risk_tolerance="Aggressivo",
        init_checking=6500.0,
        init_savings=4000.0,
        init_emergency=5000.0,
        init_brokerage=1500.0,
        monthly_salary=2600.0,
        salary_growth_rate=0.045,  # +4.5% annuo
        monthly_rental_income=0.0,
        rent_or_housing_expense=750.0,
        utilities_bills_expense=120.0,
        groceries_food_expense=320.0,
        transport_expense=90.0,
        discretionary_lifestyle_expense=380.0,
        has_mortgage=False,
        mortgage_principal=0.0,
        mortgage_rate=0.0,
        mortgage_years=0,
        has_pension=True,
        pension_name="SecondaPensione Espansione",
        pension_provider="Amundi SGR",
        pension_initial_value=4500.0,
        pension_monthly_employee=120.0,
        pension_monthly_employer=0.0,
        physical_assets=[],
        trading_universe=["VWRL.L", "QQQ", "AAPL", "NVDA", "BTC-USD", "ETH-USD"],
        initial_allocations=[
            ("VWRL.L", 6000.0),
            ("QQQ", 3500.0),
            ("AAPL", 2000.0),
            ("NVDA", 1500.0),
            ("BTC-USD", 1000.0),
            ("ETH-USD", 500.0),
        ],
        monthly_pac_target=850.0,
        pac_weights={
            "VWRL.L": 0.45,
            "QQQ": 0.25,
            "AAPL": 0.10,
            "NVDA": 0.10,
            "BTC-USD": 0.05,
            "ETH-USD": 0.05,
        },
        safe_withdrawal_rate_annual=0.0,
        rebalance_quarterly=False
    ),

    # ── 2. FIRE / DECUMULO ──
    "fire_decumulation": UserArchetypeConfig(
        code="fire_decumulation",
        name="FIRE / Decumulo",
        description="Patrimonio elevato (€1.3M+), portafoglio difensivo incentrato su dividendi aristocrats e obbligazioni, prelievo costante (SWR 3.5%), debito zero.",
        horizon_years=35,
        risk_tolerance="Conservativo / Bilanciato",
        init_checking=45000.0,
        init_savings=50000.0,
        init_emergency=30000.0,
        init_brokerage=25000.0,
        monthly_salary=0.0,  # Ritirato dal lavoro attivo
        salary_growth_rate=0.0,
        monthly_rental_income=0.0,
        rent_or_housing_expense=350.0,  # Manutenzione casa di proprietà
        utilities_bills_expense=280.0,
        groceries_food_expense=550.0,
        transport_expense=180.0,
        discretionary_lifestyle_expense=1800.0,  # Viaggi, svago, salute
        has_mortgage=False,
        mortgage_principal=0.0,
        mortgage_rate=0.0,
        mortgage_years=0,
        has_pension=False,
        pension_name="",
        pension_provider="",
        pension_initial_value=0.0,
        pension_monthly_employee=0.0,
        pension_monthly_employer=0.0,
        physical_assets=[
            {
                "name": "Abitazione Principale (Villa Residenziale)",
                "category": "real_estate",
                "location": "Torino Collina",
                "specs": "Villa Unifamiliare 240mq con Giardino",
                "ref": "FG 24 MAP 88 SUB 2",
                "purchase_price": 380000.0,
                "market_value": 420000.0,
                "annual_appreciation": 0.02,
                "haircut": 0.15
            },
            {
                "name": "Omega Speedmaster Professional Moonwatch",
                "category": "luxury_watches",
                "location": "Cassetta di Sicurezza",
                "specs": "Calibro 3861 Vetro Zaffiro Bracciale Acciaio",
                "ref": "310.30.42.50.01.002",
                "purchase_price": 6800.0,
                "market_value": 7400.0,
                "annual_appreciation": 0.03,
                "haircut": 0.12
            }
        ],
        trading_universe=["KO", "JNJ", "PG", "PEP", "WMT", "IBM", "ISP.MI", "BMW.DE", "SPY", "BND"],
        initial_allocations=[
            ("KO", 80000.0),
            ("JNJ", 90000.0),
            ("PG", 85000.0),
            ("PEP", 75000.0),
            ("WMT", 70000.0),
            ("IBM", 60000.0),
            ("ISP.MI", 65000.0),
            ("BMW.DE", 55000.0),
            ("SPY", 120000.0),
            ("BND", 150000.0),
        ],
        monthly_pac_target=0.0,  # Zero PAC in fase di decumulo
        pac_weights={},
        safe_withdrawal_rate_annual=0.035,  # 3.5% SWR prelievo annuale
        rebalance_quarterly=True
    ),

    # ── 3. HNWI / FAMIGLIA ──
    "hnwi_family": UserArchetypeConfig(
        code="hnwi_family",
        name="HNWI / Famiglia",
        description="Patrimonio multi-asset (€3.6M+), immobili con mutuo francese attivo, caveau orologi e oro fisico, fondo pensione al massimo della deducibilità fiscale (art. 10 TUIR €5.164,57/anno).",
        horizon_years=30,
        risk_tolerance="Multi-Asset Istituzionale",
        init_checking=95000.0,
        init_savings=200000.0,
        init_emergency=60000.0,
        init_brokerage=75000.0,
        monthly_salary=14500.0,  # Dirigente / Imprenditore
        salary_growth_rate=0.035,
        monthly_rental_income=1650.0,  # Immobile locato
        rent_or_housing_expense=900.0,  # Spese condominiali e gestione ville
        utilities_bills_expense=550.0,
        groceries_food_expense=1400.0,
        transport_expense=450.0,
        discretionary_lifestyle_expense=3800.0,  # Scuole private, viaggi, club
        has_mortgage=True,
        mortgage_principal=420000.0,  # Mutuo attivo prima casa
        mortgage_rate=2.85,          # Tasso fisso 2.85%
        mortgage_years=20,           # 20 anni residui
        has_pension=True,
        pension_name="Allianz Insieme Previdenza",
        pension_provider="Allianz S.p.A.",
        pension_initial_value=82000.0,
        pension_monthly_employee=430.38,  # €5.164,57 annui / 12 mesi per deduzione IRPEF
        pension_monthly_employer=200.0,
        physical_assets=[
            {
                "name": "Attico Padronale Milano Porta Nuova",
                "category": "real_estate",
                "location": "Milano Centro",
                "specs": "Attico 220mq con Terrazzo Panoramico",
                "ref": "FG 12 MAP 405 SUB 14",
                "purchase_price": 1150000.0,
                "market_value": 1350000.0,
                "annual_appreciation": 0.025,
                "haircut": 0.15
            },
            {
                "name": "Bilocale a Reddito Milano Isola",
                "category": "real_estate",
                "location": "Milano Isola",
                "specs": "Bilocale 65mq Ristrutturato a Nuovo",
                "ref": "FG 18 MAP 92 SUB 4",
                "purchase_price": 310000.0,
                "market_value": 370000.0,
                "annual_appreciation": 0.03,
                "haircut": 0.15
            },
            {
                "name": "Rolex Cosmograph Daytona Ceramica",
                "category": "luxury_watches",
                "location": "Caveau Privato",
                "specs": "Quadrante Bianco Panda Ghiera Ceramica 40mm",
                "ref": "116500LN",
                "purchase_price": 28000.0,
                "market_value": 31500.0,
                "annual_appreciation": 0.04,
                "haircut": 0.18
            },
            {
                "name": "Patek Philippe Aquanaut Acciaio",
                "category": "luxury_watches",
                "location": "Caveau Privato",
                "specs": "Cinturino Tropical Quadrante Nero 40.8mm",
                "ref": "5167A-001",
                "purchase_price": 54000.0,
                "market_value": 62000.0,
                "annual_appreciation": 0.035,
                "haircut": 0.20
            },
            {
                "name": "Lingotto Oro Puro 1kg 999.9 LBMA",
                "category": "precious_metals",
                "location": "Caveau Blindato Bancario",
                "specs": "Lingotto da Fusione Certificato London Bullion Market",
                "ref": "LBMA-1000G-IT",
                "purchase_price": 62000.0,
                "market_value": 76500.0,
                "annual_appreciation": 0.05,
                "haircut": 0.05
            }
        ],
        trading_universe=["MSFT", "AAPL", "NVDA", "ASML.AS", "SPY", "VWRL.L", "BND", "KO", "JNJ"],
        initial_allocations=[
            ("MSFT", 160000.0),
            ("AAPL", 150000.0),
            ("NVDA", 120000.0),
            ("ASML.AS", 110000.0),
            ("SPY", 240000.0),
            ("VWRL.L", 180000.0),
            ("BND", 140000.0),
            ("KO", 75000.0),
            ("JNJ", 75000.0),
        ],
        monthly_pac_target=3200.0,
        pac_weights={
            "SPY": 0.35,
            "VWRL.L": 0.25,
            "MSFT": 0.15,
            "NVDA": 0.15,
            "BND": 0.10,
        },
        safe_withdrawal_rate_annual=0.0,
        rebalance_quarterly=True
    )
}


# ─────────────────────────────────────────────────────────────
# 6. Simulatore Vettorizzato Multidimensionale
# ─────────────────────────────────────────────────────────────

@dataclass
class SimulationResult:
    archetype: UserArchetypeConfig
    start_date: str
    end_date: str
    trading_transactions_df: pd.DataFrame
    wealth_accounts_df: pd.DataFrame
    wealth_cashflow_df: pd.DataFrame
    wealth_physical_assets_df: pd.DataFrame
    wealth_pension_plans_df: pd.DataFrame
    wealth_snapshots_df: pd.DataFrame
    summary_stats: Dict[str, Any]


class PortfolioSimulationEngine:
    """
    Orchestra la simulazione congiunta di Trading e Wealth:
    - Esecuzione ordini trading nel rispetto del calendario borsistico
    - Accrediti stipendi indicizzati e rendite prima delle spese
    - Ammortamento francese del mutuo con split quota capitale/interessi
    - Rispetto rigoroso di solvibilità dei conti bancari
    - Dividendi reali su ex-date in base alle quote possedute
    - Perizie semestrali/annuali con rivalutazione e calcolo haircut
    - Versamenti fondo pensione con limite di deducibilità art. 10 TUIR
    """

    def __init__(self, offline: bool = True, seed: int = 42):
        self.offline = offline
        self.seed = seed
        self.price_engine = PriceAndDividendEngine(offline=offline, seed=seed)

    def simulate(
        self,
        archetype_key: str,
        years: int = 3,
        start_date: Optional[str] = None
    ) -> SimulationResult:
        if archetype_key not in ARCHETYPES:
            raise ValueError(f"Archetipo non valido: '{archetype_key}'. Valori ammessi: {list(ARCHETYPES.keys())}")

        cfg = ARCHETYPES[archetype_key]

        # Configurazione date
        if start_date is None:
            end_dt = datetime.today()
            start_dt = end_dt - timedelta(days=years * 365)
        else:
            start_dt = pd.to_datetime(start_date).to_pydatetime()
            end_dt = start_dt + timedelta(days=years * 365)

        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        print(f"\n🚀 Avvio simulazione quantitativa per archetipo: **{cfg.name}**")
        print(f"   • Periodo: {start_str} -> {end_str} ({years} anni)")
        print(f"   • Orizzonte strategico: {cfg.horizon_years} anni | Profilo di rischio: {cfg.risk_tolerance}")

        # Inizializza dati di mercato
        prices_dict, dividends_dict = self.price_engine.fetch_or_synthesize_data(
            tickers=cfg.trading_universe,
            start_date=start_str,
            end_date=end_str
        )

        # Inizializza Cash Ledger
        ledger = CashLedger(
            checking=cfg.init_checking,
            savings=cfg.init_savings,
            emergency=cfg.init_emergency,
            brokerage=cfg.init_brokerage
        )

        # Strutture dati di output con campi espliciti name e account_type
        trading_transactions: List[Dict[str, Any]] = []
        wealth_cashflow_records: List[Dict[str, Any]] = []
        wealth_accounts_state: Dict[str, Dict[str, Any]] = {
            "Conto Corrente Principale": {"account_id": 1, "name": "Conto Corrente Principale", "account_type": "checking", "institution": "FinecoBank", "currency": "EUR", "balance": cfg.init_checking, "notes": "Conto operativo stipendio e spese"},
            "Conto Deposito Risparmio": {"account_id": 2, "name": "Conto Deposito Risparmio", "account_type": "savings", "institution": "Illimity Bank", "currency": "EUR", "balance": cfg.init_savings, "notes": "Riserva di risparmio a rendimento"},
            "Fondo Emergenza Dedicato": {"account_id": 3, "name": "Fondo Emergenza Dedicato", "account_type": "emergency_fund", "institution": "Banca Mediolanum", "currency": "EUR", "balance": cfg.init_emergency, "notes": "Cuscino di liquidità per imprevisti"},
            "Brokerage Cash Liquidità": {"account_id": 4, "name": "Brokerage Cash Liquidità", "account_type": "brokerage_cash", "institution": "Directa / IBKR", "currency": "EUR", "balance": cfg.init_brokerage, "notes": "Liquidità per trading e investimenti"}
        }

        # Mutuo
        mortgage_remaining = cfg.mortgage_principal if cfg.has_mortgage else 0.0
        mortgage_pmt = FrenchMortgageEngine.compute_pmt(cfg.mortgage_principal, cfg.mortgage_rate, cfg.mortgage_years) if cfg.has_mortgage else 0.0
        if cfg.has_mortgage:
            wealth_accounts_state["Mutuo Ipotecario Prima Casa"] = {
                "account_id": 5, "name": "Mutuo Ipotecario Prima Casa", "account_type": "mortgage", "institution": "Intesa Sanpaolo", "currency": "EUR",
                "balance": -round(mortgage_remaining, 2), "notes": f"Mutuo Francese {cfg.mortgage_rate}% su {cfg.mortgage_years} anni"
            }

        # Pension
        pension_accumulated = cfg.pension_initial_value if cfg.has_pension else 0.0

        # Physical assets tracking
        current_physical_assets = []
        for pa in cfg.physical_assets:
            current_physical_assets.append({
                "name": pa["name"],
                "category": pa["category"],
                "location": pa.get("location", "Italia"),
                "specs": pa.get("specs", ""),
                "ref": pa.get("ref", ""),
                "purchase_price": float(pa["purchase_price"]),
                "current_market_value": float(pa["market_value"]),
                "annual_appreciation": float(pa.get("annual_appreciation", 0.02)),
                "haircut": float(pa.get("haircut", 0.15)),
                "valuation_date": start_str
            })

        # Holdings azionari attuali (quote)
        current_holdings: Dict[str, float] = {t: 0.0 for t in cfg.trading_universe}

        # ── 1. ALLOCAZIONE INIZIALE PORTAFOGLIO TRADING ──
        first_trading_day = MarketCalendarHelper.get_next_trading_day(start_dt)
        for ticker, target_eur in cfg.initial_allocations:
            res = self.price_engine.get_price_at(ticker, first_trading_day)
            if res:
                price, actual_dt = res
                meta = ASSET_UNIVERSE[ticker]
                qty = target_eur / price if meta["asset_class"] == "Crypto" else float(max(1, int(target_eur / price)))
                trading_transactions.append({
                    "tx_date": actual_dt,
                    "ticker": ticker,
                    "tx_type": "buy",
                    "quantity": round(qty, 4) if meta["asset_class"] == "Crypto" else float(qty),
                    "price": round(price, 2),
                    "currency": meta["currency"],
                    "fees": meta["fee"],
                    "asset_class": meta["asset_class"],
                    "notes": "Costruzione posizione iniziale di portafoglio"
                })
                current_holdings[ticker] += qty

        # ── 2. SIMULAZIONE CRONOLOGICA MENSILE DEI FLUSSI WEALTH & TRADING ──
        curr_sim_dt = start_dt
        month_idx = 0
        snapshots_data: List[Dict[str, Any]] = []

        while curr_sim_dt <= end_dt:
            month_idx += 1
            year = curr_sim_dt.year
            month = curr_sim_dt.month
            year_ratio = (month_idx - 1) / 12.0

            m_first_day = datetime(year, month, 1)
            salary_day = MarketCalendarHelper.get_next_trading_day(m_first_day)
            pac_day = MarketCalendarHelper.get_next_trading_day(m_first_day + timedelta(days=7))

            # A. Accredito Reddito Attivo (Stipendio indicizzato)
            monthly_sal = cfg.monthly_salary * ((1.0 + cfg.salary_growth_rate) ** year_ratio)
            if monthly_sal > 0:
                ledger.credit_checking(monthly_sal)
                wealth_cashflow_records.append({
                    "account_name": "Conto Corrente Principale",
                    "account_id": 1,
                    "category_id": 1,
                    "category_name": "Stipendio / Compensi",
                    "tx_date": salary_day.strftime("%Y-%m-%d"),
                    "amount": round(monthly_sal, 2),
                    "currency": "EUR",
                    "direction": "inflow",
                    "merchant": "Datore di Lavoro / Studio",
                    "notes": f"Accredito stipendio netto mese {month}/{year}",
                    "is_recurring": 1,
                    "payment_method": "Bonifico Sepa",
                    "tags": "stipendio,lavoro_attivo"
                })

            # B. Accredito Redditi Immobiliari Passivi
            if cfg.monthly_rental_income > 0:
                rent_inc_day = MarketCalendarHelper.get_next_trading_day(m_first_day + timedelta(days=4))
                ledger.credit_checking(cfg.monthly_rental_income)
                wealth_cashflow_records.append({
                    "account_name": "Conto Corrente Principale",
                    "account_id": 1,
                    "category_id": 4,
                    "category_name": "Affitti & Rendite Immobiliari",
                    "tx_date": rent_inc_day.strftime("%Y-%m-%d"),
                    "amount": round(cfg.monthly_rental_income, 2),
                    "currency": "EUR",
                    "direction": "inflow",
                    "merchant": "Inquilino Conduttore",
                    "notes": f"Canone locazione mensile bilocale {month}/{year}",
                    "is_recurring": 1,
                    "payment_method": "Bonifico",
                    "tags": "affitto,rendita_passiva"
                })

            # C. Debito Spese Fisse Primarie
            fixed_expenses = [
                ("Casa & Mutuo / Affitto", 6, cfg.rent_or_housing_expense, "Proprietario / Condominio", "Spese abitative / canone locazione"),
                ("Bollette & Utenze (Luce/Gas/Internet)", 7, cfg.utilities_bills_expense, "Enel / Fastweb / A2A", "Utenze domestiche bimestrali/mensili"),
                ("Spesa Alimentare & Supermercato", 8, cfg.groceries_food_expense, "Esselunga / Conad", "Spesa alimentare supermercato"),
                ("Trasporti, Carburante & Mezzi", 9, cfg.transport_expense, "Eni Station / ATM / Telepass", "Carburante e abbonamento trasporti")
            ]

            for cat_name, cat_id, exp_amount, merch, exp_note in fixed_expenses:
                if exp_amount > 0:
                    deb_amt = ledger.debit_checking(exp_amount)
                    wealth_cashflow_records.append({
                        "account_name": "Conto Corrente Principale",
                        "account_id": 1,
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "tx_date": (m_first_day + timedelta(days=6)).strftime("%Y-%m-%d"),
                        "amount": round(deb_amt, 2),
                        "currency": "EUR",
                        "direction": "outflow",
                        "merchant": merch,
                        "notes": exp_note,
                        "is_recurring": 1,
                        "payment_method": "SDD / Carta",
                        "tags": "essential_need,spese_fisse"
                    })

            # D. Rata Mutuo Francese (Scomposizione Quota Capitale ed Interessi)
            if cfg.has_mortgage and mortgage_remaining > 0:
                p_part, i_part, new_bal = FrenchMortgageEngine.generate_installment(
                    mortgage_remaining, mortgage_pmt, cfg.mortgage_rate
                )
                tot_pmt = p_part + i_part
                ledger.debit_checking(tot_pmt)
                mortgage_remaining = new_bal
                wealth_accounts_state["Mutuo Ipotecario Prima Casa"]["balance"] = -round(mortgage_remaining, 2)

                mortgage_day = (m_first_day + timedelta(days=10)).strftime("%Y-%m-%d")
                wealth_cashflow_records.append({
                    "account_name": "Conto Corrente Principale",
                    "account_id": 1,
                    "category_id": 6,
                    "category_name": "Casa & Mutuo / Affitto",
                    "tx_date": mortgage_day,
                    "amount": round(tot_pmt, 2),
                    "currency": "EUR",
                    "direction": "outflow",
                    "merchant": "Banca Mutuataria",
                    "notes": f"Rata Mutuo Francese (Quota Capitale: €{p_part:.2f} | Quota Interessi: €{i_part:.2f})",
                    "is_recurring": 1,
                    "payment_method": "SDD Addebito Diretto",
                    "tags": "debito_mutuo,ammortamento_francese"
                })

            # E. Fondo Pensione Complementare (Deducibilità fiscale art. 10 TUIR)
            if cfg.has_pension and cfg.pension_monthly_employee > 0:
                ledger.debit_checking(cfg.pension_monthly_employee)
                monthly_pension_return = pension_accumulated * (0.05 / 12.0)
                pension_accumulated = round(
                    pension_accumulated + monthly_pension_return + cfg.pension_monthly_employee + cfg.pension_monthly_employer,
                    2
                )

                pension_day = (m_first_day + timedelta(days=12)).strftime("%Y-%m-%d")
                wealth_cashflow_records.append({
                    "account_name": "Conto Corrente Principale",
                    "account_id": 1,
                    "category_id": 20,
                    "category_name": "Versamento Fondo Pensione",
                    "tx_date": pension_day,
                    "amount": round(cfg.pension_monthly_employee, 2),
                    "currency": "EUR",
                    "direction": "outflow",
                    "merchant": cfg.pension_provider,
                    "notes": f"Contribuzione {cfg.pension_name} (Deducibilità annua max €5.164,57)",
                    "is_recurring": 1,
                    "payment_method": "Bonifico / SDD",
                    "tags": "previdenza,fondo_pensione,deducibile"
                })

            # F. Spese Discrezionali Lifestyle (Wants 30%)
            if cfg.discretionary_lifestyle_expense > 0:
                disc_amt = ledger.debit_checking(cfg.discretionary_lifestyle_expense)
                wealth_cashflow_records.append({
                    "account_name": "Conto Corrente Principale",
                    "account_id": 1,
                    "category_id": 12,
                    "category_name": "Ristoranti, Bar & Delivery",
                    "tx_date": (m_first_day + timedelta(days=18)).strftime("%Y-%m-%d"),
                    "amount": round(disc_amt * 0.45, 2),
                    "currency": "EUR",
                    "direction": "outflow",
                    "merchant": "Ristoranti e Svago",
                    "notes": "Cene, ristoranti e convivialità",
                    "is_recurring": 0,
                    "payment_method": "Carta",
                    "tags": "discretionary_want"
                })
                wealth_cashflow_records.append({
                    "account_name": "Conto Corrente Principale",
                    "account_id": 1,
                    "category_id": 13,
                    "category_name": "Viaggi, Vacanze & Weekend",
                    "tx_date": (m_first_day + timedelta(days=22)).strftime("%Y-%m-%d"),
                    "amount": round(disc_amt * 0.55, 2),
                    "currency": "EUR",
                    "direction": "outflow",
                    "merchant": "Hotel & Compagnie Aeree",
                    "notes": "Vacanze e weekend fuori porta",
                    "is_recurring": 0,
                    "payment_method": "Carta",
                    "tags": "discretionary_want"
                })

            # G. FIRE Decumulo: Prelievo costante SWR
            if cfg.safe_withdrawal_rate_annual > 0:
                needed_cash = 3200.0 - ledger.checking
                if needed_cash > 0:
                    ledger.transfer_brokerage_to_checking(needed_cash)

            # H. Esecuzione PAC Trading Mensile
            if cfg.monthly_pac_target > 0 and cfg.pac_weights:
                actual_pac_transfer = ledger.transfer_checking_to_brokerage(cfg.monthly_pac_target)
                if actual_pac_transfer > 50.0:
                    wealth_cashflow_records.append({
                        "account_name": "Conto Corrente Principale",
                        "account_id": 1,
                        "category_id": 19,
                        "category_name": "PAC / Investimenti Titoli",
                        "tx_date": pac_day.strftime("%Y-%m-%d"),
                        "amount": round(actual_pac_transfer, 2),
                        "currency": "EUR",
                        "direction": "transfer",
                        "merchant": "Directa SIM / Fineco Trading",
                        "notes": f"Giroconto per alimentazione PAC periodico {month}/{year}",
                        "is_recurring": 1,
                        "payment_method": "Giroconto",
                        "tags": "saving_investment,pac"
                    })

                    for ticker, weight in cfg.pac_weights.items():
                        alloc_amount = actual_pac_transfer * weight
                        res = self.price_engine.get_price_at(ticker, pac_day)
                        if res:
                            price, actual_tx_date = res
                            meta = ASSET_UNIVERSE[ticker]
                            if meta["asset_class"] == "Crypto":
                                qty = round(alloc_amount / price, 4)
                            else:
                                qty = float(max(1, int(alloc_amount / price)))
                            cost = qty * price + meta["fee"]
                            ledger.debit_brokerage(cost)
                            current_holdings[ticker] += qty
                            trading_transactions.append({
                                "tx_date": actual_tx_date,
                                "ticker": ticker,
                                "tx_type": "buy",
                                "quantity": round(qty, 4) if meta["asset_class"] == "Crypto" else float(qty),
                                "price": round(price, 2),
                                "currency": meta["currency"],
                                "fees": meta["fee"],
                                "asset_class": meta["asset_class"],
                                "notes": f"PAC Mensile {month}/{year}"
                            })

            # I. Ribilanciamento Trimestrale Tattico
            if cfg.rebalance_quarterly and month in [3, 6, 9, 12]:
                rebal_day = MarketCalendarHelper.get_next_trading_day(m_first_day + timedelta(days=20))
                candidate_sells = [t for t, q in current_holdings.items() if q >= 15 and ASSET_UNIVERSE[t]["asset_class"] != "Bond"]
                if candidate_sells:
                    sell_ticker = candidate_sells[0]
                    sell_qty = max(1, int(current_holdings[sell_ticker] * 0.15))
                    res = self.price_engine.get_price_at(sell_ticker, rebal_day)
                    if res:
                        price, actual_tx_date = res
                        meta = ASSET_UNIVERSE[sell_ticker]
                        proceeds = sell_qty * price - meta["fee"]
                        ledger.credit_brokerage(proceeds)
                        current_holdings[sell_ticker] -= sell_qty
                        trading_transactions.append({
                            "tx_date": actual_tx_date,
                            "ticker": sell_ticker,
                            "tx_type": "sell",
                            "quantity": float(sell_qty),
                            "price": round(price, 2),
                            "currency": meta["currency"],
                            "fees": meta["fee"],
                            "asset_class": meta["asset_class"],
                            "notes": f"Ribilanciamento trimestrale Q{(month-1)//3 + 1} {year}"
                        })

            # J. Perizia Periodica Semestrale / Annuale Asset Illiquidi
            if month in [6, 12]:
                for pa in current_physical_assets:
                    appreciation_factor = 1.0 + (pa["annual_appreciation"] * 0.5)
                    pa["current_market_value"] = round(pa["current_market_value"] * appreciation_factor, 2)
                    pa["valuation_date"] = (m_first_day + timedelta(days=25)).strftime("%Y-%m-%d")

            # K. Aggiorna stato conti e calcola snapshot Net Worth di fine mese
            wealth_accounts_state["Conto Corrente Principale"]["balance"] = ledger.checking
            wealth_accounts_state["Conto Deposito Risparmio"]["balance"] = ledger.savings
            wealth_accounts_state["Fondo Emergenza Dedicato"]["balance"] = ledger.emergency
            wealth_accounts_state["Brokerage Cash Liquidità"]["balance"] = ledger.brokerage

            fin_investments_val = 0.0
            end_of_month_dt = MarketCalendarHelper.get_next_trading_day(m_first_day + timedelta(days=27))
            for t, q in current_holdings.items():
                if q > 0:
                    res_p = self.price_engine.get_price_at(t, end_of_month_dt)
                    if res_p:
                        fin_investments_val += q * res_p[0]

            phys_val_total = sum(pa["current_market_value"] for pa in current_physical_assets)
            watches_val = sum(pa["current_market_value"] for pa in current_physical_assets if pa["category"] == "luxury_watches")
            re_val = sum(pa["current_market_value"] for pa in current_physical_assets if pa["category"] == "real_estate")

            tot_liabilities = mortgage_remaining
            tot_net_worth = ledger.total_liquid + fin_investments_val + phys_val_total + pension_accumulated - tot_liabilities

            snapshots_data.append({
                "snapshot_date": end_of_month_dt.strftime("%Y-%m-%d"),
                "total_net_worth": round(tot_net_worth, 2),
                "liquid_assets": round(ledger.total_liquid, 2),
                "financial_investments": round(fin_investments_val, 2),
                "physical_assets_total": round(phys_val_total, 2),
                "watches_total": round(watches_val, 2),
                "real_estate_total": round(re_val, 2),
                "pension_total": round(pension_accumulated, 2),
                "total_liabilities": round(tot_liabilities, 2),
                "monthly_income_avg": round(monthly_sal + cfg.monthly_rental_income, 2),
                "monthly_expense_avg": round(cfg.rent_or_housing_expense + cfg.utilities_bills_expense + cfg.groceries_food_expense + cfg.transport_expense + cfg.discretionary_lifestyle_expense, 2),
                "savings_rate_pct": round(actual_pac_transfer / monthly_sal * 100.0, 2) if monthly_sal > 0 else 0.0,
                "emergency_runway_months": round(ledger.total_liquid / max(1.0, cfg.groceries_food_expense + cfg.rent_or_housing_expense), 1),
                "wealth_health_score": round(min(100.0, max(40.0, 60.0 + (tot_net_worth / 50000.0) - (tot_liabilities / 30000.0))), 1)
            })

            # Avanza di 1 mese
            next_m = month + 1 if month < 12 else 1
            next_y = year if month < 12 else year + 1
            curr_sim_dt = datetime(next_y, next_m, 1)

        # ── 3. CALCOLO DIVIDENDI REALI SU EX-DATE ──
        print("💰 Riconciliazione dividendi reali sulle quote possedute alle ex-dates...")
        df_tx_temp = pd.DataFrame(trading_transactions)
        df_tx_temp["dt"] = pd.to_datetime(df_tx_temp["tx_date"])
        df_tx_temp = df_tx_temp.sort_values("dt").reset_index(drop=True)

        dividend_transactions: List[Dict[str, Any]] = []

        for ticker, div_series in dividends_dict.items():
            if div_series is None or div_series.empty:
                continue
            meta = ASSET_UNIVERSE[ticker]
            ticker_txs = df_tx_temp[df_tx_temp["ticker"] == ticker]
            if ticker_txs.empty:
                continue

            for ex_date, div_rate in div_series.items():
                ex_dt = pd.to_datetime(ex_date)
                if ex_dt < pd.to_datetime(start_str) or ex_dt > pd.to_datetime(end_str):
                    continue

                buys = ticker_txs[(ticker_txs["dt"] <= ex_dt) & (ticker_txs["tx_type"] == "buy")]["quantity"].sum()
                sells = ticker_txs[(ticker_txs["dt"] <= ex_dt) & (ticker_txs["tx_type"] == "sell")]["quantity"].sum()
                held = buys - sells

                if held > 0 and div_rate > 0:
                    net_payout = held * div_rate
                    if net_payout >= 0.50:
                        dividend_transactions.append({
                            "tx_date": ex_dt.strftime("%Y-%m-%d"),
                            "ticker": ticker,
                            "tx_type": "dividend",
                            "quantity": 1.0,
                            "price": round(net_payout, 2),
                            "currency": meta["currency"],
                            "fees": 0.0,
                            "asset_class": meta["asset_class"],
                            "notes": f"Dividendo ({held:.0f} quote @ {div_rate:.4f} {meta['currency']})"
                        })
                        ledger.credit_brokerage(net_payout)
                        wealth_cashflow_records.append({
                            "account_name": "Brokerage Cash Liquidità",
                            "account_id": 4,
                            "category_id": 3,
                            "category_name": "Dividendi & Cedole",
                            "tx_date": ex_dt.strftime("%Y-%m-%d"),
                            "amount": round(net_payout, 2),
                            "currency": meta["currency"],
                            "direction": "inflow",
                            "merchant": f"{ticker} Payout",
                            "notes": f"Stacco dividendo {held:.0f} azioni @ {div_rate:.4f}",
                            "is_recurring": 0,
                            "payment_method": "Accredito Cedola",
                            "tags": "dividendo,rendita_finanziaria"
                        })

        # ── 4. CONSOLIDAMENTO & ORDINAMENTO DATASET ──
        all_trading = trading_transactions + dividend_transactions
        df_trading = pd.DataFrame(all_trading)
        df_trading["dt"] = pd.to_datetime(df_trading["tx_date"])
        df_trading = df_trading.sort_values(["dt", "ticker", "tx_type"]).reset_index(drop=True)
        df_trading = df_trading.drop(columns=["dt"])

        df_accounts = pd.DataFrame(list(wealth_accounts_state.values()))
        df_cashflow = pd.DataFrame(wealth_cashflow_records)
        df_cashflow = df_cashflow.sort_values("tx_date").reset_index(drop=True)
        df_physical = pd.DataFrame(current_physical_assets)
        df_snapshots = pd.DataFrame(snapshots_data)

        pension_data = []
        if cfg.has_pension:
            pension_data.append({
                "plan_name": cfg.pension_name,
                "provider": cfg.pension_provider,
                "plan_type": "fondo_pensione_aperto",
                "accumulated_value": round(pension_accumulated, 2),
                "monthly_employee_contrib": cfg.pension_monthly_employee,
                "monthly_employer_contrib": cfg.pension_monthly_employer,
                "tax_deductible_annual": round(min(5164.57, cfg.pension_monthly_employee * 12.0), 2),
                "expected_retirement_age": 67,
                "currency": "EUR",
                "investment_line": "Azionario 100% / Crescita",
                "notes": "Massimizzazione deduzione fiscale art. 10 TUIR"
            })
        df_pension = pd.DataFrame(pension_data)

        summary = {
            "archetype_code": cfg.code,
            "archetype_name": cfg.name,
            "sim_years": years,
            "start_date": start_str,
            "end_date": end_str,
            "total_trades": len(df_trading),
            "total_dividends_count": len(dividend_transactions),
            "total_dividends_eur": round(sum(d["price"] for d in dividend_transactions), 2),
            "final_net_worth": df_snapshots.iloc[-1]["total_net_worth"] if not df_snapshots.empty else 0.0,
            "final_liquid_cash": round(ledger.total_liquid, 2),
            "final_mortgage_remaining": round(mortgage_remaining, 2),
            "final_pension_val": round(pension_accumulated, 2)
        }

        print(f"   ✅ Generazione completata con successo:")
        print(f"      • {len(df_trading)} operazioni di borsa (buy, sell, dividend)")
        print(f"      • {len(df_cashflow)} movimenti di cassa coerenti e solvibili")
        print(f"      • Net Worth finale simulato: € {summary['final_net_worth']:,.2f}")
        print(f"      • Liquidità residua multi-conto: € {summary['final_liquid_cash']:,.2f}")

        return SimulationResult(
            archetype=cfg,
            start_date=start_str,
            end_date=end_str,
            trading_transactions_df=df_trading,
            wealth_accounts_df=df_accounts,
            wealth_cashflow_df=df_cashflow,
            wealth_physical_assets_df=df_physical,
            wealth_pension_plans_df=df_pension,
            wealth_snapshots_df=df_snapshots,
            summary_stats=summary
        )


# ─────────────────────────────────────────────────────────────
# 7. Validatore degli Invarianti di Portafoglio & Contabilità
# ─────────────────────────────────────────────────────────────

def verify_simulation_invariants(res: SimulationResult):
    errors = []
    df_tx = res.trading_transactions_df

    # Invariante 1: Solvibilità quote
    for ticker, grp in df_tx.groupby("ticker"):
        running_qty = 0.0
        for _, row in grp.iterrows():
            if row["tx_type"] == "buy":
                running_qty += float(row["quantity"])
            elif row["tx_type"] == "sell":
                running_qty -= float(row["quantity"])
                if running_qty < -1e-4:
                    errors.append(f"Invariante Quote Violato: {ticker} ha quantità negativa ({running_qty:.4f}) a {row['tx_date']}")
            elif row["tx_type"] == "dividend":
                if row["quantity"] != 1.0:
                    errors.append(f"Invariante Dividendo Violato: {ticker} a {row['tx_date']} ha quantity={row['quantity']} != 1.0")
                if row["price"] <= 0:
                    errors.append(f"Invariante Dividendo Violato: {ticker} a {row['tx_date']} ha importo <= 0 ({row['price']})")

    # Invariante 2: Calendario lavorativo
    for _, row in df_tx.iterrows():
        dt = pd.to_datetime(row["tx_date"]).to_pydatetime()
        if MarketCalendarHelper.is_weekend(dt):
            errors.append(f"Invariante Weekend Violato: Transazione {row['ticker']} a {row['tx_date']} eseguita di sabato/domenica!")

    # Invariante 3: Conti bancari solvibili
    df_accs = res.wealth_accounts_df
    for _, r in df_accs.iterrows():
        acc_type = r.get("account_type", r.get("type", "checking"))
        if acc_type in ("checking", "savings", "emergency_fund", "brokerage_cash") and r["balance"] < 0:
            errors.append(f"Invariante Cassa Violato: Conto {r['name']} ({acc_type}) ha saldo negativo ({r['balance']})")

    # Invariante 4: Ammortamento mutuo
    if res.archetype.has_mortgage:
        if res.summary_stats["final_mortgage_remaining"] >= res.archetype.mortgage_principal:
            errors.append("Invariante Mutuo Violato: Il debito residuo non è diminuito nel tempo")

    if errors:
        raise ValueError(f"Validazione Invarianti Fallita ({len(errors)} anomalie):\n" + "\n".join(errors[:10]))

    print(f"   🛡️ Tutti gli invarianti di finanza quantitativa e solvibilità sono verificati al 100%!")


# ─────────────────────────────────────────────────────────────
# 8. Esportazione File CSV & Popolamento Database Relazionale
# ─────────────────────────────────────────────────────────────

def export_simulation_to_files(res: SimulationResult, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    code = res.archetype.code

    tx_file = output_dir / f"{code}_trading_transactions.csv"
    res.trading_transactions_df.to_csv(tx_file, index=False, encoding="utf-8")

    acc_file = output_dir / f"{code}_wealth_accounts.csv"
    res.wealth_accounts_df.to_csv(acc_file, index=False, encoding="utf-8")

    cf_file = output_dir / f"{code}_wealth_cashflow.csv"
    res.wealth_cashflow_df.to_csv(cf_file, index=False, encoding="utf-8")

    phys_file = output_dir / f"{code}_wealth_physical_assets.csv"
    res.wealth_physical_assets_df.to_csv(phys_file, index=False, encoding="utf-8")

    pens_file = output_dir / f"{code}_wealth_pension_plans.csv"
    res.wealth_pension_plans_df.to_csv(pens_file, index=False, encoding="utf-8")

    snap_file = output_dir / f"{code}_wealth_snapshots.csv"
    res.wealth_snapshots_df.to_csv(snap_file, index=False, encoding="utf-8")

    print(f"   💾 File CSV esportati con successo in: {output_dir}")
    print(f"      • Trading:   {tx_file.name} ({len(res.trading_transactions_df)} righe)")
    print(f"      • Cashflow:  {cf_file.name} ({len(res.wealth_cashflow_df)} movimenti)")
    print(f"      • Snapshots: {snap_file.name} ({len(res.wealth_snapshots_df)} snapshot)")


def populate_argus_database(
    res: SimulationResult,
    sqlite_path: str = "data/argus_local.db",
    portfolio_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Popola direttamente il database SQLite di ARGUS sia lato Trading (portfolios, assets, transactions)
    sia lato Wealth (wealth_profiles, wealth_accounts, wealth_cashflow, wealth_physical_assets,
    wealth_pension_plans, wealth_networth_snapshots, wealth_portfolio_risk_links).
    """
    import sqlite3
    db_file = Path(sqlite_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    p_name = portfolio_name or f"Archetipo: {res.archetype.name}"

    try:
        conn.execute("BEGIN TRANSACTION;")

        # ── 1. Popolamento Trading Portfolio ──
        cursor.execute("SELECT portfolio_id FROM portfolios WHERE name = ?", (p_name,))
        row_p = cursor.fetchone()
        if row_p:
            risk_pid = row_p[0]
            cursor.execute("DELETE FROM transactions WHERE portfolio_id = ?", (risk_pid,))
        else:
            cursor.execute("""
                INSERT INTO portfolios (name, owner, base_currency, created_at, description)
                VALUES (?, 'quant_sim', 'EUR', CURRENT_TIMESTAMP, ?)
            """, (p_name, f"Portafoglio didattico simulato: {res.archetype.description}"))
            risk_pid = cursor.lastrowid

        # Inserisci / Assicura Assets
        for ticker in res.trading_transactions_df["ticker"].unique():
            meta = ASSET_UNIVERSE.get(ticker, {"name": ticker, "asset_class": "Stock", "currency": "EUR"})
            cursor.execute("""
                INSERT OR IGNORE INTO assets (ticker, name, asset_class, currency)
                VALUES (?, ?, ?, ?)
            """, (ticker, meta.get("name", ticker), meta.get("asset_class", "Stock"), meta.get("currency", "EUR")))

        cursor.execute("SELECT ticker, asset_id FROM assets")
        asset_map = dict(cursor.fetchall())

        for _, tx in res.trading_transactions_df.iterrows():
            aid = asset_map.get(tx["ticker"])
            if aid:
                cursor.execute("""
                    INSERT INTO transactions (portfolio_id, asset_id, tx_date, tx_type, quantity, price, currency, fees, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (risk_pid, aid, tx["tx_date"], tx["tx_type"], float(tx["quantity"]), float(tx["price"]), tx["currency"], float(tx.get("fees", 0.0)), tx.get("notes", "")))

        # ── 2. Popolamento Wealth Profile ──
        w_prof_name = f"Patrimonio {res.archetype.name}"
        cursor.execute("SELECT profile_id FROM wealth_profiles WHERE name = ?", (w_prof_name,))
        row_wp = cursor.fetchone()
        if row_wp:
            wealth_pid = row_wp[0]
            # Ripulitura record precedenti per questo profilo per garantire idempotenza
            cursor.execute("DELETE FROM wealth_cashflow WHERE portfolio_id = ?", (wealth_pid,))
            cursor.execute("DELETE FROM wealth_accounts WHERE portfolio_id = ?", (wealth_pid,))
            cursor.execute("DELETE FROM wealth_physical_assets WHERE portfolio_id = ?", (wealth_pid,))
            cursor.execute("DELETE FROM wealth_pension_plans WHERE portfolio_id = ?", (wealth_pid,))
            cursor.execute("DELETE FROM wealth_networth_snapshots WHERE portfolio_id = ?", (wealth_pid,))
        else:
            cursor.execute("""
                INSERT INTO wealth_profiles (name, description, owner, base_currency)
                VALUES (?, ?, 'quant_sim', 'EUR')
            """, (w_prof_name, res.archetype.description))
            wealth_pid = cursor.lastrowid

        cursor.execute("""
            INSERT OR REPLACE INTO wealth_portfolio_risk_links (wealth_portfolio_id, risk_portfolio_id)
            VALUES (?, ?)
        """, (wealth_pid, risk_pid))

        # Inserisci Conti Wealth con portfolio_id
        acc_id_map = {}
        for _, acc in res.wealth_accounts_df.iterrows():
            acc_name = str(acc["name"])
            acc_type = str(acc.get("account_type", acc.get("type", "checking")))
            acc_inst = str(acc["institution"])
            acc_curr = str(acc["currency"])
            acc_bal = float(acc["balance"])
            acc_notes = str(acc.get("notes", ""))
            cursor.execute("""
                INSERT INTO wealth_accounts (name, account_type, institution, currency, balance, notes, portfolio_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (acc_name, acc_type, acc_inst, acc_curr, acc_bal, acc_notes, wealth_pid))
            acc_id_map[acc_name] = cursor.lastrowid

        # Assicura le categorie in wealth_categories per evitare violazioni di foreign key
        cursor.execute("SELECT category_id FROM wealth_categories")
        existing_cat_ids = set(r[0] for r in cursor.fetchall())
        for _, cf in res.wealth_cashflow_df.iterrows():
            cid = int(cf.get("category_id", 1))
            if cid not in existing_cat_ids:
                cname = str(cf.get("category_name", f"Categoria #{cid}"))
                cflow = "income" if cf.get("direction") == "inflow" else "expense"
                cursor.execute("""
                    INSERT OR IGNORE INTO wealth_categories (category_id, name, flow_type)
                    VALUES (?, ?, ?)
                """, (cid, cname, cflow))
                existing_cat_ids.add(cid)

        # Inserisci Movimenti Cashflow con portfolio_id
        for _, cf in res.wealth_cashflow_df.iterrows():
            acc_id = acc_id_map.get(cf.get("account_name"), list(acc_id_map.values())[0] if acc_id_map else 1)
            cat_id = int(cf.get("category_id", 1))
            cursor.execute("""
                INSERT INTO wealth_cashflow (account_id, category_id, tx_date, amount, currency, direction, merchant, notes, is_recurring, payment_method, tags, portfolio_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (acc_id, cat_id, cf["tx_date"], float(cf["amount"]), cf.get("currency", "EUR"), cf["direction"], cf.get("merchant", ""), cf.get("notes", ""), int(cf.get("is_recurring", 0)), cf.get("payment_method", "Bonifico"), cf.get("tags", ""), wealth_pid))

        # Inserisci Asset Fisici con portfolio_id
        if not res.wealth_physical_assets_df.empty:
            for _, pa in res.wealth_physical_assets_df.iterrows():
                cursor.execute("""
                    INSERT INTO wealth_physical_assets (name, asset_category, brand_or_location, model_or_specs, reference_number, purchase_price, current_market_value, valuation_date, notes, portfolio_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (pa["name"], pa["category"], pa.get("location", ""), pa.get("specs", ""), pa.get("ref", ""), float(pa["purchase_price"]), float(pa["current_market_value"]), pa.get("valuation_date", ""), f"Haircut: {pa.get('haircut', 0.15):.0%}", wealth_pid))

        # Inserisci Piani Pensione con portfolio_id
        if not res.wealth_pension_plans_df.empty:
            for _, pen in res.wealth_pension_plans_df.iterrows():
                cursor.execute("""
                    INSERT INTO wealth_pension_plans (plan_name, provider, plan_type, accumulated_value, monthly_employee_contrib, monthly_employer_contrib, tax_deductible_annual, notes, portfolio_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (pen["plan_name"], pen["provider"], pen["plan_type"], float(pen["accumulated_value"]), float(pen["monthly_employee_contrib"]), float(pen["monthly_employer_contrib"]), float(pen["tax_deductible_annual"]), pen.get("notes", ""), wealth_pid))

        # Inserisci Snapshot Net Worth con portfolio_id
        if not res.wealth_snapshots_df.empty:
            for _, snap in res.wealth_snapshots_df.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO wealth_networth_snapshots (
                        portfolio_id, snapshot_date, snapshot_name, total_net_worth, liquid_assets,
                        financial_investments, physical_assets_total, watches_total, real_estate_total,
                        pension_total, total_liabilities, monthly_income_avg, monthly_expense_avg,
                        savings_rate_pct, emergency_runway_months, wealth_health_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    wealth_pid, snap["snapshot_date"], f"Snapshot {res.archetype.name}",
                    float(snap["total_net_worth"]), float(snap["liquid_assets"]), float(snap["financial_investments"]),
                    float(snap["physical_assets_total"]), float(snap["watches_total"]), float(snap["real_estate_total"]),
                    float(snap["pension_total"]), float(snap["total_liabilities"]), float(snap["monthly_income_avg"]),
                    float(snap["monthly_expense_avg"]), float(snap["savings_rate_pct"]), float(snap["emergency_runway_months"]),
                    float(snap["wealth_health_score"])
                ))

        conn.commit()
        print(f"   🏛️ Database {sqlite_path} popolato con successo:")
        print(f"      • Trading Portfolio ID: {risk_pid} ('{p_name}')")
        print(f"      • Wealth Profile ID:    {wealth_pid} ('{w_prof_name}')")
        return {"risk_portfolio_id": risk_pid, "wealth_profile_id": wealth_pid, "status": "SUCCESS"}

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Errore durante il popolamento del database SQLite: {e}") from e
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# 9. CLI Entry Point
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ARGUS Quantitative Portfolio & Wealth Simulation Engine"
    )
    parser.add_argument(
        "--archetype",
        choices=["young_accumulator", "fire_decumulation", "hnwi_family", "all"],
        default="all",
        help="Archetipo didattico da simulare (default: all)"
    )
    parser.add_argument(
        "--years",
        type=int,
        default=3,
        help="Durata della cronologia in anni (default: 3)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Data di inizio simulazione YYYY-MM-DD (default: 3 anni fa)"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=True,
        help="Usa modello GBM stocastico deterministico senza chiamate esterne (default: True)"
    )
    parser.add_argument(
        "--online",
        dest="offline",
        action="store_false",
        help="Tenta il download di prezzi reali da Yahoo Finance"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(ARCHETYPES_DIR),
        help="Cartella di destinazione per i file CSV generati"
    )
    parser.add_argument(
        "--populate-db",
        action="store_true",
        default=False,
        help="Inserisce i dati generati direttamente in data/argus_local.db"
    )

    args = parser.parse_args()

    print("=" * 75)
    print("🏛️  ARGUS — Quantitative Simulation Engine & Realistic Portfolios")
    print("=" * 75)

    engine = PortfolioSimulationEngine(offline=args.offline, seed=42)
    target_archetypes = list(ARCHETYPES.keys()) if args.archetype == "all" else [args.archetype]
    out_dir = Path(args.output_dir)

    for arch_key in target_archetypes:
        sim_res = engine.simulate(arch_key, years=args.years, start_date=args.start_date)
        verify_simulation_invariants(sim_res)
        export_simulation_to_files(sim_res, out_dir / arch_key)

        if args.populate_db:
            populate_argus_database(sim_res)

        if arch_key == "hnwi_family" or args.archetype == "all":
            sim_res.trading_transactions_df.to_csv(OUT_FILE_REALISTIC, index=False, encoding="utf-8")
            sim_res.trading_transactions_df.to_csv(OUT_FILE_90S, index=False, encoding="utf-8")
            print(f"   💾 Allineato file di default: {OUT_FILE_REALISTIC}")

    print("\n" + "=" * 75)
    print("🎯 Generazione e validazione quantitativa completate con successo!")
    print("=" * 75)


if __name__ == "__main__":
    main()
