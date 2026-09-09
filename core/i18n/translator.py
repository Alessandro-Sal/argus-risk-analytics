"""
ARGUS — Internationalization (i18n) Engine
Multi-language translation and string localization manager.
Supports zero-overhead dictionary lookup, fallback resolution, variable interpolation,
and hot-swapping in Streamlit session state.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

_DEFAULT_LOCALE = "it"
_FALLBACK_LOCALE = "it"
_LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")


class I18nEngine:
    """Motore centrale di traduzione e localizzazione stringhe."""

    _instance: Optional[I18nEngine] = None
    _lock = threading.Lock()

    def __init__(self, locales_dir: Optional[str] = None):
        self._locales_dir = locales_dir or _LOCALES_DIR
        self._dictionaries: Dict[str, Dict[str, Any]] = {}
        self._active_locale: str = _DEFAULT_LOCALE
        self._load_all_dictionaries()

    @classmethod
    def get_instance(cls) -> I18nEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load_all_dictionaries(self) -> None:
        """Carica tutti i file .json presenti nella directory dei dizionari."""
        if not os.path.isdir(self._locales_dir):
            return

        for fname in os.listdir(self._locales_dir):
            if fname.endswith(".json"):
                lang_code = os.path.splitext(fname)[0].lower()
                file_path = os.path.join(self._locales_dir, fname)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self._dictionaries[lang_code] = json.load(f)
                except Exception:
                    # In caso di errore di lettura, non bloccare l'avvio
                    self._dictionaries[lang_code] = {}

    def get_available_locales(self) -> List[str]:
        """Restituisce l'elenco delle lingue supportate."""
        return sorted(list(self._dictionaries.keys())) or [_DEFAULT_LOCALE]

    def set_locale(self, locale: str) -> None:
        """Imposta la lingua attiva nel motore e sincronizza con session_state se presente."""
        code = str(locale).strip().lower()
        if code in self._dictionaries:
            self._active_locale = code
        elif any(code.startswith(k) for k in self._dictionaries):
            for k in self._dictionaries:
                if code.startswith(k):
                    self._active_locale = k
                    break

        # Sincronizza con Streamlit se disponibile
        try:
            import streamlit as st
            if hasattr(st, "session_state"):
                st.session_state["locale"] = self._active_locale
        except Exception:
            pass

    def get_locale(self) -> str:
        """Recupera la lingua attiva tenendo conto dello stato di sessione Streamlit."""
        try:
            import streamlit as st
            if hasattr(st, "session_state") and "locale" in st.session_state:
                loc = str(st.session_state["locale"]).strip().lower()
                if loc in self._dictionaries:
                    return loc
        except Exception:
            pass
        return self._active_locale

    def translate(self, key: str, default: Optional[str] = None, **kwargs: Any) -> str:
        """
        Risolve una chiave gerarchica (es. 'risk.var_95') nella lingua attiva.
        Esegue fallback su 'it' e poi su default/chiave se mancante.
        Supporta l'interpolazione di variabili: t('msg', count=5) -> 'Hai 5 elementi'.
        """
        active = self.get_locale()
        val = self._lookup_key(active, key)

        if val is None and active != _FALLBACK_LOCALE:
            val = self._lookup_key(_FALLBACK_LOCALE, key)

        if val is None:
            val = default if default is not None else key

        if kwargs and isinstance(val, str):
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return str(val)

    def _lookup_key(self, lang: str, key: str) -> Optional[str]:
        """Naviga il dizionario gerarchico separato da punti."""
        d = self._dictionaries.get(lang)
        if not d or not isinstance(d, dict):
            return None

        parts = key.split(".")
        current = d
        for p in parts:
            if isinstance(current, dict) and p in current:
                current = current[p]
            else:
                return None

        return current if isinstance(current, str) else None


# ── Global Facade Functions ──────────────────────────────────────────

def get_i18n() -> I18nEngine:
    """Restituisce l'istanza singleton del motore I18n."""
    return I18nEngine.get_instance()


def t(key: str, default: Optional[str] = None, **kwargs: Any) -> str:
    """Funzione rapida globale per tradurre etichette: t('common.save')."""
    return get_i18n().translate(key, default=default, **kwargs)


def set_locale(locale: str) -> None:
    """Imposta la lingua attiva globalmente."""
    get_i18n().set_locale(locale)


def get_locale() -> str:
    """Ottiene la lingua attiva."""
    return get_i18n().get_locale()
