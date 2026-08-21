"""
ARGUS — Risk Analytics Platform
Core Module: Metadata Resolver
Enriches country, sector, and asset class metadata for all securities.
"""

from typing import Tuple, Optional


def resolve_asset_metadata(
    ticker: str,
    asset_class: Optional[str] = None,
    yf_country: Optional[str] = None,
    yf_sector: Optional[str] = None
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
        ("crypto" in ac_lower) or
        ("-EUR" in t_upper) or
        ("-USD" in t_upper) or
        ("-BTC" in t_upper) or
        (t_upper in [
            "BTC", "ETH", "SOL", "ADA", "XRP", "BNB", "USDT", "FDUSD", "SEI",
            "DOGE", "AVAX", "MATIC", "LINK", "DOT", "NEAR", "SUI", "APT", "TAO", "SHIB", "PEPE"
        ])
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
        "SPY": ("Stati Uniti", "Indice Benchmark")
    }
    if t_upper in KNOWN_METADATA:
        return KNOWN_METADATA[t_upper]

    COUNTRY_MAP = {
        "US": "Stati Uniti", "USA": "Stati Uniti", "UNITED STATES": "Stati Uniti", "STATI UNITI": "Stati Uniti",
        "ITALY": "Italia", "ITALIA": "Italia", "IT": "Italia",
        "DENMARK": "Danimarca", "DANIMARCA": "Danimarca", "DK": "Danimarca",
        "CHINA": "Cina", "CINA": "Cina", "CN": "Cina",
        "INDIA": "India", "IN": "India",
        "FRANCE": "Francia", "FRANCIA": "Francia", "FR": "Francia",
        "GERMANY": "Germania", "GERMANIA": "Germania", "DE": "Germania",
        "UNITED KINGDOM": "Regno Unito", "REGNO UNITO": "Regno Unito", "UK": "Regno Unito", "GB": "Regno Unito",
        "SWITZERLAND": "Svizzera", "SVIZZERA": "Svizzera", "CH": "Svizzera",
        "NETHERLANDS": "Paesi Bassi", "PAESI BASSI": "Paesi Bassi", "NL": "Paesi Bassi",
        "MEXICO": "Messico", "MESSICO": "Messico", "MX": "Messico",
        "GLOBAL": "Globale", "GLOBALE": "Globale", "DECENTRALIZED": "Globale"
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
        "CRYPTOCURRENCY": "Criptovalute"
    }

    # Risoluzione Paese
    c_clean = None
    if yf_country and str(yf_country).strip().upper() not in ["NONE", "NAN", "NULL", ""]:
        c_clean = COUNTRY_MAP.get(str(yf_country).strip().upper(), str(yf_country).strip().title())
    else:
        if "." in t_upper:
            suf = t_upper.split(".")[-1]
            suf_map = {
                "MI": "Italia", "CO": "Danimarca", "PA": "Francia", "AS": "Paesi Bassi",
                "DE": "Germania", "L": "Regno Unito", "SW": "Svizzera", "MX": "Messico"
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
    "ISP.MI": {"target_mean_price": 4.30, "trailing_pe": 8.4, "forward_pe": 7.9, "peg_ratio": 1.1, "price_to_book": 1.15, "dividend_yield": 0.076, "roe": 0.16},
    "NOVO-B.CO": {"target_mean_price": 860.0, "trailing_pe": 34.2, "forward_pe": 28.5, "peg_ratio": 1.5, "price_to_book": 27.5, "dividend_yield": 0.014, "roe": 0.82},
    "MSFT": {"target_mean_price": 495.0, "trailing_pe": 35.8, "forward_pe": 29.2, "peg_ratio": 2.1, "price_to_book": 12.4, "dividend_yield": 0.0075, "roe": 0.38},
    "GOOGL": {"target_mean_price": 208.0, "trailing_pe": 23.5, "forward_pe": 19.8, "peg_ratio": 1.3, "price_to_book": 6.8, "dividend_yield": 0.0048, "roe": 0.31},
    "GOOG": {"target_mean_price": 208.0, "trailing_pe": 23.5, "forward_pe": 19.8, "peg_ratio": 1.3, "price_to_book": 6.8, "dividend_yield": 0.0048, "roe": 0.31},
    "META": {"target_mean_price": 690.0, "trailing_pe": 27.4, "forward_pe": 22.1, "peg_ratio": 1.2, "price_to_book": 8.5, "dividend_yield": 0.0035, "roe": 0.36},
    "BABA": {"target_mean_price": 120.0, "trailing_pe": 15.2, "forward_pe": 11.8, "peg_ratio": 0.95, "price_to_book": 1.45, "dividend_yield": 0.021, "roe": 0.12},
    "PRX.AS": {"target_mean_price": 50.0, "trailing_pe": 14.5, "forward_pe": 12.2, "peg_ratio": 1.1, "price_to_book": 1.25, "dividend_yield": 0.008, "roe": 0.10},
    "PYPL": {"target_mean_price": 92.0, "trailing_pe": 18.2, "forward_pe": 14.5, "peg_ratio": 1.2, "price_to_book": 3.6, "dividend_yield": 0.0, "roe": 0.22},
    "ENPH": {"target_mean_price": 105.0, "trailing_pe": 38.0, "forward_pe": 24.5, "peg_ratio": 1.6, "price_to_book": 11.2, "dividend_yield": 0.0, "roe": 0.18},
    "TDOC": {"target_mean_price": 12.5, "trailing_pe": 22.0, "forward_pe": 16.5, "peg_ratio": 1.4, "price_to_book": 0.85, "dividend_yield": 0.0, "roe": 0.05},
    "AAPL": {"target_mean_price": 250.0, "trailing_pe": 33.5, "forward_pe": 28.0, "peg_ratio": 2.1, "price_to_book": 39.0, "dividend_yield": 0.005, "roe": 1.45},
    "NVDA": {"target_mean_price": 155.0, "trailing_pe": 46.0, "forward_pe": 33.0, "peg_ratio": 1.1, "price_to_book": 48.0, "dividend_yield": 0.001, "roe": 1.18},
    "TSLA": {"target_mean_price": 260.0, "trailing_pe": 65.0, "forward_pe": 45.0, "peg_ratio": 3.2, "price_to_book": 12.0, "dividend_yield": 0.0, "roe": 0.19},
    "AMZN": {"target_mean_price": 235.0, "trailing_pe": 42.0, "forward_pe": 31.0, "peg_ratio": 1.4, "price_to_book": 7.8, "dividend_yield": 0.0, "roe": 0.21},
    "RACE.MI": {"target_mean_price": 460.0, "trailing_pe": 49.0, "forward_pe": 42.0, "peg_ratio": 2.8, "price_to_book": 19.0, "dividend_yield": 0.006, "roe": 0.42},
    "ENEL.MI": {"target_mean_price": 8.20, "trailing_pe": 10.8, "forward_pe": 9.9, "peg_ratio": 1.4, "price_to_book": 1.4, "dividend_yield": 0.063, "roe": 0.14},
    "NDIA.L": {"target_mean_price": 8.80, "trailing_pe": 22.0, "forward_pe": 19.0, "peg_ratio": 1.3, "price_to_book": 3.2, "dividend_yield": 0.002, "roe": 0.16},
    "DFNS.PA": {"target_mean_price": 38.5, "trailing_pe": 24.0, "forward_pe": 20.0, "peg_ratio": 1.5, "price_to_book": 3.5, "dividend_yield": 0.008, "roe": 0.15},
    "DFND.PA": {"target_mean_price": 38.5, "trailing_pe": 24.0, "forward_pe": 20.0, "peg_ratio": 1.5, "price_to_book": 3.5, "dividend_yield": 0.008, "roe": 0.15},
    "SPY": {"target_mean_price": 610.0, "trailing_pe": 26.5, "forward_pe": 22.0, "peg_ratio": 1.8, "price_to_book": 4.8, "dividend_yield": 0.013, "roe": 0.22}
}


def resolve_asset_valuation_metrics(ticker: str) -> dict:
    """Restituisce le metriche di valutazione e consensus analisti per un ticker noto."""
    t_clean = str(ticker).strip().upper()
    return KNOWN_VALUATION_METRICS.get(t_clean, {})
