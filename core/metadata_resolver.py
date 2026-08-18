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
