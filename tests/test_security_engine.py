# ============================================================
# tests/test_security_engine.py
# Unit tests for ARGUS Security & Compliance Engine
# ============================================================

import pandas as pd
import pytest
from core.security_engine import (
    sanitize_for_export,
    sanitize_dataframe_for_export,
    mask_iban,
    mask_account_number,
    mask_tax_id,
    pseudonymize_identifier,
    escape_html_content,
    ArgusDataVault,
    CIPHER_PREFIX
)


def test_sanitize_for_export_formula_triggers():
    """Verifica che i trigger di formula CSV/Excel vengano sanitizzati con l'apice singolo."""
    assert sanitize_for_export("=1+1") == "'=1+1"
    assert sanitize_for_export("+SUM(A1:A10)") == "'+SUM(A1:A10)"
    assert sanitize_for_export("-2+3") == "'-2+3"
    assert sanitize_for_export("@SUM(A1)") == "'@SUM(A1)"
    assert sanitize_for_export("\tCMD|' /C calc'!A0") == "'CMD|' /C calc'!A0"
    assert sanitize_for_export("cmd|'/C calc'!A0") == "'cmd|'/C calc'!A0"
    assert sanitize_for_export("Normal Text") == "Normal Text"
    assert sanitize_for_export(1234.5) == 1234.5
    assert sanitize_for_export(None) is None


def test_sanitize_dataframe_for_export():
    """Verifica che un intero DataFrame venga sanitizzato preservando colonne numeriche."""
    df = pd.DataFrame({
        "tx_id": [1, 2],
        "merchant": ["Amazon", "=cmd|'/C calc'!A0"],
        "amount": [100.5, 250.0],
        "notes": ["+Bonus", "Normale"]
    })
    clean_df = sanitize_dataframe_for_export(df)

    assert clean_df["merchant"].iloc[0] == "Amazon"
    assert clean_df["merchant"].iloc[1] == "'=cmd|'/C calc'!A0"
    assert clean_df["notes"].iloc[0] == "'+Bonus"
    assert clean_df["notes"].iloc[1] == "Normale"
    assert clean_df["amount"].iloc[0] == 100.5


def test_mask_iban():
    """Verifica il mascheramento di codici IBAN italiani ed esteri."""
    iban = "IT60X0542811101000000123456"
    masked = mask_iban(iban)
    assert masked.startswith("IT60")
    assert masked.endswith("3456")
    assert "0542811101000000" not in masked
    assert "*" in masked

    assert mask_iban(None) == "N/D"
    assert mask_iban("") == "N/D"
    assert mask_iban("SHORT") == "*****"


def test_mask_account_number():
    """Verifica il mascheramento di numeri conto."""
    acc = "1234567890"
    masked = mask_account_number(acc)
    assert masked == "******7890"
    assert mask_account_number(None) == "N/D"


def test_mask_tax_id():
    """Verifica il mascheramento del codice fiscale."""
    cf = "RSSMRA85M01H501Z"
    masked = mask_tax_id(cf)
    assert masked.startswith("RSSMRA")
    assert masked.endswith("01Z")
    assert "85M" not in masked
    assert mask_tax_id(None) == "N/D"


def test_pseudonymize_identifier():
    """Verifica che lo pseudonimo sia deterministico e non reversibile."""
    id1 = "user_account_12345"
    p1 = pseudonymize_identifier(id1)
    p2 = pseudonymize_identifier(id1)
    p3 = pseudonymize_identifier("user_account_99999")

    assert p1.startswith("pseudonym_")
    assert p1 == p2
    assert p1 != p3


def test_escape_html_content():
    """Verifica l'escape sicuro di caratteri HTML/JS."""
    malicious = "<script>alert('XSS')</script>"
    safe = escape_html_content(malicious)
    assert "<script>" not in safe
    assert "&lt;script&gt;" in safe


def test_argus_data_vault_encryption_decryption():
    """Verifica la crittografia e decrittografia a riposo con Fernet/PBKDF2."""
    vault = ArgusDataVault(master_key="MySuperSecretKey123!_Test")
    plaintext = "IBAN_SEGRETO_IT60X0542811101000000123456"

    ciphertext = vault.encrypt_field(plaintext)
    assert ciphertext.startswith(CIPHER_PREFIX)
    assert plaintext not in ciphertext

    decrypted = vault.decrypt_field(ciphertext)
    assert decrypted == plaintext

    # Decrittazione di testo già in chiaro
    assert vault.decrypt_field("plain") == "plain"
    assert vault.encrypt_field(None) is None
