# ============================================================
# core/security_engine.py
# ARGUS — Security, Cryptography & Compliance Engine
# Compliance: GDPR Art. 32 (Security of Processing), OWASP Top 10, CWE-1236 (Formula Injection)
# ============================================================

import os
import re
import html
import base64
import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger("argus.security")

# Caratteri trigger per Formula Injection (CSV / Excel Injection - CWE-1236)
FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")
DANGEROUS_PATTERNS = re.compile(r"^(cmd|powershell|mshta|calc)\|", re.IGNORECASE)

# Prefisso per campi crittografati a riposo (Authenticated Encryption)
CIPHER_PREFIX = "argus_enc::"


# ── 1. FORMULA INJECTION & EXPORT SANITIZATION (CWE-1236) ──────

def sanitize_for_export(val: Any) -> Any:
    """
    Sanitizza un valore prima della scrittura in file CSV o fogli Excel (.xlsx).
    Previene l'esecuzione involontaria di macro o formule malevole (CSV/Excel Formula Injection, CWE-1236).
    Se il valore testuale inizia con '=', '+', '-', '@', '\\t', '\\r', viene anteposto un apice singolo (').
    """
    if val is None or pd.isna(val):
        return val

    if isinstance(val, str):
        val_clean = val.replace("\x00", "").strip()
        if not val_clean:
            return val
        # Verifica se inizia con trigger di formula o comandi DDE
        if val_clean.startswith(FORMULA_TRIGGERS) or DANGEROUS_PATTERNS.match(val_clean):
            return f"'{val_clean}"
        return val_clean

    return val


def sanitize_dataframe_for_export(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Restituisce una copia profonda del DataFrame con tutte le colonne testuali
    sanitizzate contro Formula Injection e caratteri di controllo malevoli.
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    df_clean = df.copy()
    target_cols = columns if columns is not None else df_clean.select_dtypes(include=["object", "string"]).columns

    for col in target_cols:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].apply(sanitize_for_export)

    return df_clean


# ── 2. DATA MASKING & ANONIMIZZAZIONE PII (GDPR Art. 32) ───────

def mask_iban(iban: Optional[str], visible_start: int = 4, visible_end: int = 4) -> str:
    """
    Maschera un codice IBAN per la visualizzazione e reportistica condivisa.
    Esempio: 'IT60X0542811101000000123456' -> 'IT60 ******************** 3456'
    """
    if not iban or not isinstance(iban, str):
        return "N/D"

    clean_iban = iban.strip().replace(" ", "").upper()
    total_len = len(clean_iban)

    if total_len <= (visible_start + visible_end):
        return "*" * total_len

    masked_part = "*" * (total_len - visible_start - visible_end)
    return f"{clean_iban[:visible_start]} {masked_part} {clean_iban[-visible_end:]}"


def mask_account_number(acc_num: Optional[str], visible_end: int = 4) -> str:
    """Maschera un numero di conto bancario mostrando solo le ultime cifre."""
    if not acc_num or not isinstance(acc_num, str):
        return "N/D"
    clean = acc_num.strip()
    if len(clean) <= visible_end:
        return "*" * len(clean)
    return f"{'*' * (len(clean) - visible_end)}{clean[-visible_end:]}"


def mask_tax_id(tax_id: Optional[str]) -> str:
    """
    Maschera un codice fiscale o codice identificativo fiscale.
    Esempio: 'RSSMRA85M01H501Z' -> 'RSSMRA********01Z'
    """
    if not tax_id or not isinstance(tax_id, str):
        return "N/D"
    clean = tax_id.strip().upper()
    if len(clean) < 8:
        return "*" * len(clean)
    return f"{clean[:6]}{'*' * (len(clean) - 9)}{clean[-3:]}"


def pseudonymize_identifier(val: str, salt: Optional[str] = None) -> str:
    """
    Genera uno pseudonimo crittografico deterministico (HMAC-SHA256) per log di audit
    e telemetria conforme a GDPR (pseudonimizzazione Art. 4 comma 5 e Art. 32).
    """
    if not val:
        return ""
    secret_salt = (salt or os.getenv("ARGUS_SALT") or "ARGUS_CORE_FINTECH_SALT").encode("utf-8")
    h = hmac.new(secret_salt, val.strip().encode("utf-8"), hashlib.sha256)
    return f"pseudonym_{h.hexdigest()[:16]}"


# ── 3. HTML & XSS SANITIZATION PER STREAMLIT ───────────────────

def escape_html_content(text: Any) -> str:
    """
    Esegue l'escape sicuro di codice HTML/JS per stringhe dinamiche (LLM response,
    input utente, messaggi di eccezione) renderizzate in contesti con unsafe_allow_html=True.
    """
    if text is None:
        return ""
    return html.escape(str(text), quote=True)


# ── 4. FIELD-LEVEL ENCRYPTION AT REST (AES-256 / FERNET) ───────

class ArgusDataVault:
    """
    Motore crittografico locale per dati a riposo (Data at Rest Encryption).
    Utilizza Fernet (AES-128-CBC + HMAC-SHA256) con derivazione della chiave
    tramite PBKDF2HMAC (SHA-256, 600.000 iterazioni secondo raccomandazioni OWASP).
    """

    _instance: Optional["ArgusDataVault"] = None
    _fernet: Optional[Fernet] = None

    def __init__(self, master_key: Optional[str] = None, salt: Optional[bytes] = None):
        key_material = (master_key or os.getenv("ARGUS_MASTER_KEY") or "ARGUS_DEFAULT_VAULT_KEY_2026").encode("utf-8")
        salt_bytes = salt or (os.getenv("ARGUS_VAULT_SALT") or "ARGUS_SECURE_SALT_99").encode("utf-8")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_bytes,
            iterations=600_000,
            backend=default_backend()
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key_material))
        self._fernet = Fernet(derived_key)

    @classmethod
    def get_instance(cls) -> "ArgusDataVault":
        if cls._instance is None:
            cls._instance = ArgusDataVault()
        return cls._instance

    def encrypt_field(self, plaintext: Optional[str]) -> Optional[str]:
        """Crittografa una stringa in formato sicuro authenticated ciphertext con prefisso."""
        if plaintext is None:
            return None
        if not isinstance(plaintext, str):
            plaintext = str(plaintext)
        if plaintext.startswith(CIPHER_PREFIX):
            return plaintext  # Già crittografato

        encrypted_bytes = self._fernet.encrypt(plaintext.encode("utf-8"))
        return f"{CIPHER_PREFIX}{encrypted_bytes.decode('utf-8')}"

    def decrypt_field(self, ciphertext: Optional[str]) -> Optional[str]:
        """Decrittografa un campo protetto. Se il campo non è crittografato, lo restituisce inalterato."""
        if ciphertext is None or not isinstance(ciphertext, str):
            return ciphertext
        if not ciphertext.startswith(CIPHER_PREFIX):
            return ciphertext

        raw_token = ciphertext[len(CIPHER_PREFIX):].encode("utf-8")
        try:
            decrypted_bytes = self._fernet.decrypt(raw_token)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            logger.warning("Decrittazione campo fallita (chiave non valida o token alterato): %s", e)
            return "[ENCRYPTED_DATA_ACCESS_DENIED]"

    def is_encrypted(self, val: Any) -> bool:
        return isinstance(val, str) and val.startswith(CIPHER_PREFIX)
