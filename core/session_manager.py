"""
core/session_manager.py
ARGUS — Type-Safe Session State Manager & State Contract.

Centralizes, validates, and governs access to Streamlit's `st.session_state`.
Eliminates state drift, duplicate key naming, and runtime KeyError anomalies across ARGUS modules.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    st = None
    HAS_STREAMLIT = False


class ArgusSessionKeys:
    """Costanti univoche per le chiavi di st.session_state."""
    APP_INITIALIZED = "_app_initialized"
    SPLASH_DISMISSED = "splash_dismissed"
    BASE_CURRENCY = "base_currency"
    RISK_PROFILE = "risk_profile"
    PORTFOLIO_ID = "current_portfolio_id"
    SELECTED_PORTFOLIO = "selected_portfolio"
    ACTIVE_POSITIONS = "df_positions"
    PORTFOLIO_RESULTS = "results"
    MINUSVALENZE = "minusvalenze_available"
    ACTIVE_QUANT_TAB = "active_quant_tab"
    LAST_REBALANCE = "last_rebalance_result"
    THEME = "argus_theme"


class ArgusSessionManager:
    """
    Gestore centralizzato e type-safe per st.session_state con fallback per ambienti headless e testing.
    """

    _MEMORY_FALLBACK: Dict[str, Any] = {}

    @classmethod
    def _state(cls) -> Any:
        """Restituisce st.session_state se disponibile in runtime Streamlit, altrimenti il dizionario fallback."""
        if HAS_STREAMLIT and hasattr(st, "session_state"):
            try:
                # Verifica che session_state sia accessibile (non solleva eccezioni in script context)
                _ = st.session_state.get(ArgusSessionKeys.APP_INITIALIZED, None)
                return st.session_state
            except Exception:
                pass
        return cls._MEMORY_FALLBACK

    @classmethod
    def ensure_initialized(cls) -> None:
        """
        Inizializza atomicamente lo stato dell'applicazione con valori predefiniti istituzionali.
        """
        state = cls._state()
        defaults = {
            ArgusSessionKeys.APP_INITIALIZED: True,
            ArgusSessionKeys.BASE_CURRENCY: "EUR",
            ArgusSessionKeys.RISK_PROFILE: "Moderate",
            ArgusSessionKeys.PORTFOLIO_ID: 1,
            ArgusSessionKeys.SELECTED_PORTFOLIO: "Default Institutional Portfolio",
            ArgusSessionKeys.MINUSVALENZE: 0.0,
            ArgusSessionKeys.ACTIVE_QUANT_TAB: "📊 Markowitz & Rebalancing",
            ArgusSessionKeys.THEME: "obsidian_dark",
        }
        for k, v in defaults.items():
            if k not in state or state[k] is None:
                state[k] = v

    @classmethod
    def get_base_currency(cls) -> str:
        """Restituisce la valuta base istituzionale (default: EUR)."""
        val = cls._state().get(ArgusSessionKeys.BASE_CURRENCY, "EUR")
        return str(val).upper().strip()

    @classmethod
    def set_base_currency(cls, currency: str) -> None:
        """Imposta la valuta base con validazione standard ISO 4217."""
        clean_curr = str(currency).upper().strip()
        if clean_curr not in ["EUR", "USD", "CHF", "GBP"]:
            raise ValueError(f"Valuta non supportata: {currency}. Consentite: EUR, USD, CHF, GBP")
        cls._state()[ArgusSessionKeys.BASE_CURRENCY] = clean_curr

    @classmethod
    def get_risk_profile(cls) -> str:
        """Restituisce il profilo di rischio MiFID II (Conservative, Moderate, Aggressive)."""
        return str(cls._state().get(ArgusSessionKeys.RISK_PROFILE, "Moderate"))

    @classmethod
    def set_risk_profile(cls, profile: str) -> None:
        """Imposta il profilo di rischio MiFID II."""
        clean_profile = str(profile).strip().capitalize()
        if clean_profile not in ["Conservative", "Moderate", "Aggressive"]:
            raise ValueError(f"Profilo di rischio non valido: {profile}. Consentiti: Conservative, Moderate, Aggressive")
        cls._state()[ArgusSessionKeys.RISK_PROFILE] = clean_profile

    @classmethod
    def get_portfolio_id(cls) -> int:
        """Restituisce l'identificativo del portafoglio attivo."""
        try:
            return int(cls._state().get(ArgusSessionKeys.PORTFOLIO_ID, 1))
        except (ValueError, TypeError):
            return 1

    @classmethod
    def set_portfolio_id(cls, portfolio_id: int) -> None:
        """Imposta l'identificativo del portafoglio attivo."""
        cls._state()[ArgusSessionKeys.PORTFOLIO_ID] = int(portfolio_id)

    @classmethod
    def get_active_positions(cls, df_fallback: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Recupera il DataFrame delle posizioni attive normalizzato,
        cercando in 'df_positions', in 'results'['positions'] o nel fallback.
        """
        state = cls._state()
        if ArgusSessionKeys.ACTIVE_POSITIONS in state:
            pos = state[ArgusSessionKeys.ACTIVE_POSITIONS]
            if isinstance(pos, pd.DataFrame) and not pos.empty:
                return pos.copy()

        if ArgusSessionKeys.PORTFOLIO_RESULTS in state:
            res = state[ArgusSessionKeys.PORTFOLIO_RESULTS]
            if isinstance(res, dict) and "positions" in res:
                pos = res["positions"]
                if isinstance(pos, pd.DataFrame) and not pos.empty:
                    return pos.copy()

        if df_fallback is not None and isinstance(df_fallback, pd.DataFrame):
            return df_fallback.copy()

        return pd.DataFrame()

    @classmethod
    def set_active_positions(cls, df_positions: pd.DataFrame) -> None:
        """Salva il DataFrame delle posizioni attive."""
        cls._state()[ArgusSessionKeys.ACTIVE_POSITIONS] = df_positions.copy() if df_positions is not None else pd.DataFrame()

    @classmethod
    def get_minusvalenze_available(cls) -> float:
        """Recupera l'importo delle minusvalenze fiscali pregresse disponibili (TUIR Art. 67)."""
        try:
            return float(cls._state().get(ArgusSessionKeys.MINUSVALENZE, 0.0))
        except (ValueError, TypeError):
            return 0.0

    @classmethod
    def set_minusvalenze_available(cls, amount: float) -> None:
        """Imposta l'importo delle minusvalenze disponibili."""
        cls._state()[ArgusSessionKeys.MINUSVALENZE] = max(0.0, float(amount))

    @classmethod
    def save_rebalance_result(cls, result: Dict[str, Any]) -> None:
        """Salva in sessione l'esito dell'ultimo ribilanciamento con timestamp UTC."""
        payload = dict(result)
        payload["timestamp_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cls._state()[ArgusSessionKeys.LAST_REBALANCE] = payload

    @classmethod
    def get_last_rebalance_result(cls) -> Optional[Dict[str, Any]]:
        """Recupera l'esito dell'ultimo ribilanciamento effettuato."""
        return cls._state().get(ArgusSessionKeys.LAST_REBALANCE, None)

    @classmethod
    def reset_session(cls) -> None:
        """Ripristina lo stato ai valori predefiniti di fabbrica."""
        state = cls._state()
        state.clear()
        cls.ensure_initialized()
