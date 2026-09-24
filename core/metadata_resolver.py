"""
ARGUS — Risk Analytics Platform
Core Module: Metadata Resolver
Enriches country, sector, and asset class metadata for all securities.
"""

from typing import Optional, Tuple


def resolve_asset_metadata(
    ticker: str, asset_class: Optional[str] = None, yf_country: Optional[str] = None, yf_sector: Optional[str] = None
) -> Tuple[str, str]:
    """
    Risolve ed arricchisce paese e settore dell'asset in lingua italiana, gestendo:
    - Criptovalute (Globale / Criptovalute)
    - Titoli noti con override geografici/settoriali accurati
    - Suffissi di borsa europei (.MI -> Italia, .CO -> Danimarca, .PA -> Francia, .AS -> Paesi Bassi, .DE -> Germania, .L -> Regno Unito, .SW -> Svizzera, .MX -> Messico)
    - Traduzione e armonizzazione in italiano dei paesi e settori GICS.
    """
    t_upper = str(ticker).strip().upper()
    ac_lower = str(asset_class).strip().lower() if asset_class else ""

    # 1. Rilevamento Criptovalute
    is_crypto = (
        ("crypto" in ac_lower)
        or ("-EUR" in t_upper)
        or ("-USD" in t_upper)
        or ("-BTC" in t_upper)
        or (
            t_upper
            in [
                "BTC",
                "ETH",
                "SOL",
                "ADA",
                "XRP",
                "BNB",
                "USDT",
                "FDUSD",
                "SEI",
                "DOGE",
                "AVAX",
                "MATIC",
                "LINK",
                "DOT",
                "NEAR",
                "SUI",
                "APT",
                "TAO",
                "SHIB",
                "PEPE",
            ]
        )
    )
    if is_crypto:
        return "Globale", "Criptovalute"

    # 2. Tabella Titoli Noti & ETF
    KNOWN_METADATA = {
        "ISP.MI": ("Italia", "Servizi Finanziari"),
        "NOVO-B.CO": ("Danimarca", "Salute & Pharma"),
        "BABA": ("Cina", "Beni di Consumo"),
        "NDIA.L": ("India", "ETF Mercati Emergenti"),
        "DFNS.PA": ("Francia", "Difesa & Aerospazio"),
        "DFND.PA": ("Francia", "Difesa & Aerospazio"),
        "DFEN.DE": ("Germania", "Difesa & Aerospazio"),
        "IMEA.SW": ("Svizzera", "ETF Mercati Emergenti"),
        "PRX.AS": ("Paesi Bassi", "Tecnologia"),
        "BMW.DE": ("Germania", "Beni di Consumo"),
        "CCL1N.MX": ("Messico", "Beni di Consumo"),
        "DOYU": ("Cina", "Comunicazioni & Media"),
        "NIO": ("Cina", "Beni di Consumo"),
        "GOOGL": ("Stati Uniti", "Comunicazioni & Media"),
        "GOOG": ("Stati Uniti", "Comunicazioni & Media"),
        "AMZN": ("Stati Uniti", "Beni di Consumo"),
        "MSFT": ("Stati Uniti", "Tecnologia"),
        "META": ("Stati Uniti", "Comunicazioni & Media"),
        "AAPL": ("Stati Uniti", "Tecnologia"),
        "NVDA": ("Stati Uniti", "Tecnologia"),
        "TSLA": ("Stati Uniti", "Beni di Consumo"),
        "PYPL": ("Stati Uniti", "Servizi Finanziari"),
        "ENPH": ("Stati Uniti", "Tecnologia"),
        "CRSR": ("Stati Uniti", "Tecnologia"),
        "BIIB": ("Stati Uniti", "Salute & Pharma"),
        "T": ("Stati Uniti", "Comunicazioni & Media"),
        "KO": ("Stati Uniti", "Beni di Prima Necessità"),
        "C": ("Stati Uniti", "Servizi Finanziari"),
        "INTC": ("Stati Uniti", "Tecnologia"),
        "QCOM": ("Stati Uniti", "Tecnologia"),
        "PLTR": ("Stati Uniti", "Tecnologia"),
        "PINS": ("Stati Uniti", "Comunicazioni & Media"),
        "TDOC": ("Stati Uniti", "Salute & Pharma"),
        "ARRY": ("Stati Uniti", "Tecnologia"),
        "SFT": ("Stati Uniti", "Beni di Consumo"),
        "ONEW": ("Stati Uniti", "Beni di Consumo"),
        "TTCF": ("Stati Uniti", "Beni di Prima Necessità"),
        "SPY": ("Stati Uniti", "Indice Benchmark"),
    }
    if t_upper in KNOWN_METADATA:
        return KNOWN_METADATA[t_upper]

    COUNTRY_MAP = {
        "US": "Stati Uniti",
        "USA": "Stati Uniti",
        "UNITED STATES": "Stati Uniti",
        "STATI UNITI": "Stati Uniti",
        "ITALY": "Italia",
        "ITALIA": "Italia",
        "IT": "Italia",
        "DENMARK": "Danimarca",
        "DANIMARCA": "Danimarca",
        "DK": "Danimarca",
        "CHINA": "Cina",
        "CINA": "Cina",
        "CN": "Cina",
        "INDIA": "India",
        "IN": "India",
        "FRANCE": "Francia",
        "FRANCIA": "Francia",
        "FR": "Francia",
        "GERMANY": "Germania",
        "GERMANIA": "Germania",
        "DE": "Germania",
        "UNITED KINGDOM": "Regno Unito",
        "REGNO UNITO": "Regno Unito",
        "UK": "Regno Unito",
        "GB": "Regno Unito",
        "SWITZERLAND": "Svizzera",
        "SVIZZERA": "Svizzera",
        "CH": "Svizzera",
        "NETHERLANDS": "Paesi Bassi",
        "PAESI BASSI": "Paesi Bassi",
        "NL": "Paesi Bassi",
        "MEXICO": "Messico",
        "MESSICO": "Messico",
        "MX": "Messico",
        "GLOBAL": "Globale",
        "GLOBALE": "Globale",
        "DECENTRALIZED": "Globale",
    }

    SECTOR_MAP = {
        "TECHNOLOGY": "Tecnologia",
        "FINANCIAL SERVICES": "Servizi Finanziari",
        "HEALTHCARE": "Salute & Pharma",
        "CONSUMER CYCLICAL": "Beni di Consumo",
        "CONSUMER DEFENSIVE": "Beni di Prima Necessità",
        "COMMUNICATION SERVICES": "Comunicazioni & Media",
        "INDUSTRIALS": "Industria & Difesa",
        "ENERGY": "Energia",
        "UTILITIES": "Utilities",
        "REAL ESTATE": "Immobiliare",
        "BASIC MATERIALS": "Materiali di Base",
        "CRYPTO": "Criptovalute",
        "CRYPTOCURRENCY": "Criptovalute",
    }

    # Risoluzione Paese
    c_clean = None
    if yf_country and str(yf_country).strip().upper() not in ["NONE", "NAN", "NULL", ""]:
        c_clean = COUNTRY_MAP.get(str(yf_country).strip().upper(), str(yf_country).strip().title())
    else:
        if "." in t_upper:
            suf = t_upper.split(".")[-1]
            suf_map = {
                "MI": "Italia",
                "CO": "Danimarca",
                "PA": "Francia",
                "AS": "Paesi Bassi",
                "DE": "Germania",
                "L": "Regno Unito",
                "SW": "Svizzera",
                "MX": "Messico",
            }
            c_clean = suf_map.get(suf, "Europa")
        else:
            c_clean = "Stati Uniti"

    # Risoluzione Settore
    s_clean = None
    if yf_sector and str(yf_sector).strip().upper() not in ["NONE", "NAN", "NULL", "", "ALTRO", "UNASSIGNED"]:
        s_clean = SECTOR_MAP.get(str(yf_sector).strip().upper(), str(yf_sector).strip().title())
    else:
        if ac_lower == "etf":
            s_clean = "ETF & Fondi"
        elif ac_lower == "bond":
            s_clean = "Obbligazionario"
        elif ac_lower == "cash":
            s_clean = "Liquidità"
        else:
            s_clean = "Azionario Diversificato"

    return c_clean, s_clean


KNOWN_VALUATION_METRICS = {
    "ISP.MI": {
        "target_mean_price": 7.27,
        "currency": "EUR",
        "trailing_pe": 12.10,
        "forward_pe": 10.39,
        "peg_ratio": 1.84,
        "price_to_book": 1.73,
        "dividend_yield": 0.0567,
        "roe": 0.143,
    },
    "NOVO-B.CO": {
        "target_mean_price": 310.17,
        "currency": "DKK",
        "trailing_pe": 10.48,
        "forward_pe": 12.60,
        "peg_ratio": 3.04,
        "price_to_book": 5.51,
        "dividend_yield": 0.0424,
        "roe": 0.598,
    },
    "MSFT": {
        "target_mean_price": 572.92,
        "currency": "USD",
        "trailing_pe": 27.70,
        "forward_pe": 20.78,
        "peg_ratio": 1.61,
        "price_to_book": 8.23,
        "dividend_yield": 0.0073,
        "roe": 0.340,
    },
    "GOOGL": {
        "target_mean_price": 428.07,
        "currency": "USD",
        "trailing_pe": 17.30,
        "forward_pe": 23.08,
        "peg_ratio": 1.25,
        "price_to_book": 6.74,
        "dividend_yield": 0.0026,
        "roe": 0.487,
    },
    "GOOG": {
        "target_mean_price": 422.34,
        "currency": "USD",
        "trailing_pe": 17.12,
        "forward_pe": 22.84,
        "peg_ratio": 1.24,
        "price_to_book": 6.67,
        "dividend_yield": 0.0026,
        "roe": 0.487,
    },
    "META": {
        "target_mean_price": 758.28,
        "currency": "USD",
        "trailing_pe": 25.26,
        "forward_pe": 19.26,
        "peg_ratio": 0.88,
        "price_to_book": 6.57,
        "dividend_yield": 0.0031,
        "roe": 0.298,
    },
    "BABA": {
        "target_mean_price": 186.08,
        "currency": "USD",
        "trailing_pe": 24.72,
        "forward_pe": 11.58,
        "peg_ratio": 0.51,
        "price_to_book": 1.60,
        "dividend_yield": 0.0096,
        "roe": 0.064,
    },
    "PRX.AS": {
        "target_mean_price": 61.05,
        "currency": "EUR",
        "trailing_pe": 7.86,
        "forward_pe": 8.26,
        "peg_ratio": 1.63,
        "price_to_book": 1.66,
        "dividend_yield": 0.0077,
        "roe": 0.222,
    },
    "PYPL": {
        "target_mean_price": 57.07,
        "currency": "USD",
        "trailing_pe": 10.18,
        "forward_pe": 9.11,
        "peg_ratio": 0.95,
        "price_to_book": 2.29,
        "dividend_yield": 0.0104,
        "roe": 0.245,
    },
    "ENPH": {
        "target_mean_price": 53.23,
        "currency": "USD",
        "trailing_pe": 36.29,
        "forward_pe": 15.64,
        "peg_ratio": 0.79,
        "price_to_book": 3.98,
        "dividend_yield": 0.0,
        "roe": 0.130,
    },
    "TDOC": {
        "target_mean_price": 7.67,
        "currency": "USD",
        "trailing_pe": 18.0,
        "forward_pe": 15.0,
        "peg_ratio": 1.20,
        "price_to_book": 0.89,
        "dividend_yield": 0.0,
        "roe": -0.130,
    },
    "AAPL": {
        "target_mean_price": 327.20,
        "currency": "USD",
        "trailing_pe": 38.03,
        "forward_pe": 34.67,
        "peg_ratio": 2.67,
        "price_to_book": 45.16,
        "dividend_yield": 0.0033,
        "roe": 1.488,
    },
    "NVDA": {
        "target_mean_price": 328.66,
        "currency": "USD",
        "trailing_pe": 26.80,
        "forward_pe": 13.70,
        "peg_ratio": 0.46,
        "price_to_book": 22.56,
        "dividend_yield": 0.0047,
        "roe": 1.172,
    },
    "TSLA": {
        "target_mean_price": 390.09,
        "currency": "USD",
        "trailing_pe": 334.65,
        "forward_pe": 162.94,
        "peg_ratio": 4.37,
        "price_to_book": 16.28,
        "dividend_yield": 0.0,
        "roe": 0.047,
    },
    "AMZN": {
        "target_mean_price": 328.17,
        "currency": "USD",
        "trailing_pe": 20.00,
        "forward_pe": 23.71,
        "peg_ratio": 1.48,
        "price_to_book": 4.81,
        "dividend_yield": 0.0,
        "roe": 0.306,
    },
    "RACE.MI": {
        "target_mean_price": 388.39,
        "currency": "EUR",
        "trailing_pe": 38.71,
        "forward_pe": 32.60,
        "peg_ratio": 3.53,
        "price_to_book": 17.27,
        "dividend_yield": 0.0102,
        "roe": 0.454,
    },
    "ENEL.MI": {
        "target_mean_price": 10.27,
        "currency": "EUR",
        "trailing_pe": 21.31,
        "forward_pe": 11.83,
        "peg_ratio": 0.77,
        "price_to_book": 3.60,
        "dividend_yield": 0.0595,
        "roe": 0.123,
    },
    "NDIA.L": {
        "target_mean_price": 8.80,
        "currency": "USD",
        "trailing_pe": 21.82,
        "forward_pe": 19.0,
        "peg_ratio": 1.30,
        "price_to_book": 3.20,
        "dividend_yield": 0.002,
        "roe": 0.160,
    },
    "BIIB": {
        "target_mean_price": 237.19,
        "currency": "USD",
        "trailing_pe": 38.44,
        "forward_pe": 13.06,
        "peg_ratio": 2.24,
        "price_to_book": 1.69,
        "dividend_yield": 0.0,
        "roe": 0.046,
    },
    "CRSR": {
        "target_mean_price": 13.22,
        "currency": "USD",
        "trailing_pe": 42.45,
        "forward_pe": 15.88,
        "peg_ratio": 1.20,
        "price_to_book": 2.14,
        "dividend_yield": 0.0,
        "roe": 0.058,
    },
    "DFNS.PA": {
        "target_mean_price": 58.50,
        "currency": "EUR",
        "trailing_pe": 24.0,
        "forward_pe": 20.0,
        "peg_ratio": 1.50,
        "price_to_book": 3.5,
        "dividend_yield": 0.008,
        "roe": 0.15,
    },
    "DFND.PA": {
        "target_mean_price": 9.20,
        "currency": "EUR",
        "trailing_pe": 24.0,
        "forward_pe": 20.0,
        "peg_ratio": 1.50,
        "price_to_book": 3.5,
        "dividend_yield": 0.008,
        "roe": 0.15,
    },
    "SPY": {
        "target_mean_price": 610.0,
        "currency": "USD",
        "trailing_pe": 26.5,
        "forward_pe": 22.0,
        "peg_ratio": 1.8,
        "price_to_book": 4.8,
        "dividend_yield": 0.013,
        "roe": 0.22,
    },
}


def resolve_asset_valuation_metrics(ticker: str) -> dict:
    """Restituisce le metriche di valutazione e consensus analisti per un ticker noto."""
    t_clean = str(ticker).strip().upper()
    return KNOWN_VALUATION_METRICS.get(t_clean, {})
