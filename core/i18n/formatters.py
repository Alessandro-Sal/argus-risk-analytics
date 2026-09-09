"""
ARGUS — Internationalization (i18n) & Localization (L10n) Formatters
Institutional number, currency, percentage, and date formatting engine.
Compliant with European, Anglo-Saxon, and Swiss conventions, plus Wall Street accounting notation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Dict, Optional, Union


@dataclass(frozen=True)
class LocaleConvention:
    """Convenzioni tipografiche e contabili per una specifica regione/lingua."""
    code: str
    decimal_sep: str
    thousand_sep: str
    date_format_short: str
    date_format_long: str
    default_currency: str
    currency_prefix: bool
    currency_space: bool


_CONVENTIONS: Dict[str, LocaleConvention] = {
    "it": LocaleConvention(
        code="it",
        decimal_sep=",",
        thousand_sep=".",
        date_format_short="%d/%m/%Y",
        date_format_long="%d %B %Y",
        default_currency="EUR",
        currency_prefix=False,
        currency_space=True,
    ),
    "en": LocaleConvention(
        code="en",
        decimal_sep=".",
        thousand_sep=",",
        date_format_short="%m/%d/%Y",
        date_format_long="%B %d, %Y",
        default_currency="USD",
        currency_prefix=True,
        currency_space=False,
    ),
    "gb": LocaleConvention(
        code="gb",
        decimal_sep=".",
        thousand_sep=",",
        date_format_short="%d/%m/%Y",
        date_format_long="%d %B %Y",
        default_currency="GBP",
        currency_prefix=True,
        currency_space=False,
    ),
    "ch": LocaleConvention(
        code="ch",
        decimal_sep=".",
        thousand_sep="'",
        date_format_short="%d.%m.%Y",
        date_format_long="%d. %B %Y",
        default_currency="CHF",
        currency_prefix=True,
        currency_space=True,
    ),
}

_CURRENCY_SYMBOLS: Dict[str, str] = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "CHF": "CHF",
    "JPY": "¥",
    "CAD": "C$",
    "AUD": "A$",
    "BTC": "₿",
    "ETH": "Ξ",
}


def _resolve_convention(locale: Optional[str] = None) -> LocaleConvention:
    """Risolve la convenzione attiva controllando locale esplicito o session_state."""
    if not locale:
        try:
            import streamlit as st
            if hasattr(st, "session_state") and "locale" in st.session_state:
                locale = str(st.session_state["locale"]).strip().lower()
        except Exception:
            pass

    loc = str(locale or "it").strip().lower()
    if loc in _CONVENTIONS:
        return _CONVENTIONS[loc]
    if loc.startswith("it"):
        return _CONVENTIONS["it"]
    if loc.startswith("en"):
        return _CONVENTIONS["en"]
    if loc.startswith("ch") or loc.startswith("de_ch"):
        return _CONVENTIONS["ch"]
    if loc.startswith("gb") or loc.startswith("en_gb"):
        return _CONVENTIONS["gb"]
    return _CONVENTIONS["it"]


def _resolve_accounting_notation(accounting: Optional[bool] = None) -> bool:
    """Rileva se utilizzare la notazione contabile a parentesi per i numeri negativi."""
    if accounting is not None:
        return bool(accounting)
    try:
        import streamlit as st
        if hasattr(st, "session_state"):
            val = st.session_state.get("accounting_notation", "standard")
            return val in ["accounting", "parentheses", True]
    except Exception:
        pass
    return False


def _format_raw_number(
    val: float,
    decimals: int,
    thousand_sep: str,
    decimal_sep: str
) -> str:
    """Formatta un numero float assoluto con separatori specificati."""
    fmt_str = f"{{:,.{decimals}f}}"
    formatted = fmt_str.format(abs(val))
    # Il formattatore standard di Python usa virgola per migliaia e punto per decimali
    # Effettuiamo la traslitterazione coerente
    if thousand_sep == "." and decimal_sep == ",":
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    elif thousand_sep == "'" and decimal_sep == ".":
        formatted = formatted.replace(",", "'")
    elif thousand_sep == " " and decimal_sep == ",":
        formatted = formatted.replace(",", " ").replace(".", ",")
    return formatted


# ── Public Formatting APIs ───────────────────────────────────────────

def format_number(
    value: Union[int, float, None],
    locale: Optional[str] = None,
    accounting: Optional[bool] = None,
    decimals: int = 2
) -> str:
    """
    Formatta un valore numerico generico rispettando i separatori del locale
    e la convenzione contabile dei negativi (segno meno vs parentesi).
    """
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"

    conv = _resolve_convention(locale)
    is_acct = _resolve_accounting_notation(accounting)
    num_str = _format_raw_number(float(value), decimals, conv.thousand_sep, conv.decimal_sep)

    if value < 0:
        return f"({num_str})" if is_acct else f"-{num_str}"
    return num_str


def format_currency(
    value: Union[int, float, None],
    currency: Optional[str] = None,
    locale: Optional[str] = None,
    accounting: Optional[bool] = None,
    compact: bool = False,
    decimals: int = 2
) -> str:
    """
    Formatta un importo monetario con simbolo valuta (prefisso/suffisso),
    separatori regionali corretti e notazione contabile per importi negativi.
    """
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"

    conv = _resolve_convention(locale)
    is_acct = _resolve_accounting_notation(accounting)

    curr_code = (currency or conv.default_currency).upper().strip()
    symbol = _CURRENCY_SYMBOLS.get(curr_code, curr_code)

    val_f = float(value)
    is_neg = val_f < 0
    abs_val = abs(val_f)

    if compact:
        if abs_val >= 1_000_000_000:
            compact_val = abs_val / 1_000_000_000
            suffix = "B" if conv.code in ["en", "gb"] else " Mld"
            num_str = f"{compact_val:.2f}{suffix}".replace(".", conv.decimal_sep)
        elif abs_val >= 1_000_000:
            compact_val = abs_val / 1_000_000
            suffix = "M" if conv.code in ["en", "gb"] else " Mln"
            num_str = f"{compact_val:.2f}{suffix}".replace(".", conv.decimal_sep)
        elif abs_val >= 1_000:
            compact_val = abs_val / 1_000
            suffix = "k"
            num_str = f"{compact_val:.1f}{suffix}".replace(".", conv.decimal_sep)
        else:
            num_str = _format_raw_number(abs_val, decimals, conv.thousand_sep, conv.decimal_sep)
    else:
        num_str = _format_raw_number(abs_val, decimals, conv.thousand_sep, conv.decimal_sep)

    # Assemblaggio con simbolo di valuta
    sp = " " if conv.currency_space else ""
    if conv.currency_prefix:
        res = f"{symbol}{sp}{num_str}"
    else:
        res = f"{num_str}{sp}{symbol}"

    if is_neg:
        return f"({res})" if is_acct else f"-{res}"
    return res


def format_percent(
    value: Union[int, float, None],
    locale: Optional[str] = None,
    accounting: Optional[bool] = None,
    decimals: int = 2,
    signed: bool = True,
    is_decimal_fraction: bool = False
) -> str:
    """
    Formatta una percentuale (es. 0.0525 con is_decimal_fraction=True o 5.25 standard).
    Supporta notazione con segno esplicito (+5,25%) e contabile a parentesi ((3,10%)).
    """
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"

    conv = _resolve_convention(locale)
    is_acct = _resolve_accounting_notation(accounting)

    val_f = float(value) * 100.0 if is_decimal_fraction else float(value)
    is_neg = val_f < 0
    abs_val = abs(val_f)

    num_str = _format_raw_number(abs_val, decimals, conv.thousand_sep, conv.decimal_sep)

    if is_neg:
        return f"({num_str}%)" if is_acct else f"-{num_str}%"
    if signed and val_f > 0:
        return f"+{num_str}%"
    return f"{num_str}%"


def format_date(
    dt: Union[datetime, date, str, None],
    locale: Optional[str] = None,
    fmt: str = "short"
) -> str:
    """Formatta una data secondo la convenzione locale attiva."""
    if dt is None or dt == "":
        return "—"

    if isinstance(dt, str):
        try:
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            dt = parsed
        except Exception:
            try:
                dt = datetime.strptime(dt[:10], "%Y-%m-%d")
            except Exception:
                return str(dt)

    conv = _resolve_convention(locale)
    if fmt == "iso":
        return dt.strftime("%Y-%m-%d")
    if fmt == "long":
        # Formattazione mese localizzato essenziale
        months_it = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
        months_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        m_idx = dt.month - 1
        m_str = months_it[m_idx] if conv.code == "it" else months_en[m_idx]
        if conv.code in ["en", "gb"]:
            return f"{m_str} {dt.day:02d}, {dt.year}"
        return f"{dt.day:02d} {m_str} {dt.year}"

    return dt.strftime(conv.date_format_short)


def get_dataframe_styler_formats(
    columns_config: Dict[str, str],
    locale: Optional[str] = None,
    accounting: Optional[bool] = None,
    base_currency: Optional[str] = None
) -> Dict[str, Callable[[Any], str]]:
    """
    Genera un dizionario di callable di formattazione compatibile con df.style.format()
    per sostituire le stringhe hardcoded nei template Streamlit.
    columns_config mappa: 'NomeColonna' -> 'currency' | 'percent' | 'number' | 'date'.
    """
    styler_map: Dict[str, Callable[[Any], str]] = {}
    for col, ctype in columns_config.items():
        if ctype == "currency":
            styler_map[col] = lambda x, c=base_currency, l=locale, a=accounting: format_currency(x, currency=c, locale=l, accounting=a)
        elif ctype == "percent":
            styler_map[col] = lambda x, l=locale, a=accounting: format_percent(x, locale=l, accounting=a, signed=False)
        elif ctype == "signed_percent":
            styler_map[col] = lambda x, l=locale, a=accounting: format_percent(x, locale=l, accounting=a, signed=True)
        elif ctype == "number":
            styler_map[col] = lambda x, l=locale, a=accounting: format_number(x, locale=l, accounting=a)
        elif ctype == "date":
            styler_map[col] = lambda x, l=locale: format_date(x, locale=l)
    return styler_map
