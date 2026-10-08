# ============================================================
# core/wealth/tax_history_engine.py
# ARGUS — Archivio Storico Fiscale, Riconciliazione Dichiarazioni (730 / Redditi PF)
# e Scadenziario Quinquennale Zainetto Fiscale (Art. 68 TUIR & Art. 36-bis d.P.R. 600/1973)
# ============================================================

import io
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from sqlalchemy import Engine
from sqlalchemy import text as sqlt

logger = logging.getLogger("tax_history_engine")

try:
    import pypdf

    HAS_PYPDF = True
except ImportError:
    pypdf = None
    HAS_PYPDF = False


# ============================================================
# DATA STRUCTURES & MODELS
# ============================================================


@dataclass
class TaxDeclaration:
    """Rappresentazione di una dichiarazione fiscale archiviata (730 o Redditi PF)."""

    id: Optional[int] = None
    profile_id: str = "default"
    tax_year: int = 2024  # Anno d'imposta
    filing_year: int = 2025  # Anno di presentazione
    model_type: str = "730_ORDINARIO"  # '730_ORDINARIO', '730_INTEGRATIVO', 'REDDITI_PF'
    protocol_id: Optional[str] = None  # Protocollo telematico Agenzia delle Entrate
    gross_income: float = 0.0  # Reddito complessivo (Rigo 11 / RN1)
    taxable_income: float = 0.0  # Reddito imponibile (Rigo 14 / RN4)
    net_tax_irpef: float = 0.0  # Imposta netta IRPEF (Rigo 50 / RN26)
    capital_gains_declared: float = 0.0  # Plusvalenze lorde dichiarate (T11 / RT11)
    capital_losses_offset: float = 0.0  # Minusvalenze compensate nell'anno (T13 / RT13)
    substitute_tax_paid: float = 0.0  # Imposta sostitutiva versata 26% (Rigo 321 / RT29)
    ivafe_paid: float = 0.0  # IVAFE versata (Rigo 307 / Quadro W / RW16)
    foreign_assets_val: float = 0.0  # Monitoraggio estero valore finale (Quadro W / RW)
    notes: Optional[str] = None
    source_filename: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaxLossCarryforward:
    """Rappresentazione di una tranche dello Zainetto Fiscale / Minusvalenze."""

    id: Optional[int] = None
    profile_id: str = "default"
    generation_year: int = 2024
    expiration_year: int = 2028  # generation_year + 4
    initial_loss_amount: float = 0.0
    offset_amount: float = 0.0
    remaining_amount: float = 0.0
    status: str = "ACTIVE"  # 'ACTIVE', 'EXHAUSTED', 'EXPIRED'
    is_officially_filed: bool = True  # Dichiarata formalmente in Anagrafe Tributaria
    broker_source: str = "DEGIRO"
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReconciliationReport:
    """Esito della riconciliazione tra flussi portafoglio e dichiarazione fiscale."""

    profile_id: str
    tax_year: int
    # Dati da dichiarazione formale
    declared_capital_gains: float = 0.0
    declared_losses_offset: float = 0.0
    declared_substitute_tax: float = 0.0
    declared_foreign_assets_val: float = 0.0
    declared_ivafe: float = 0.0
    # Dati calcolati da ledger/portafoglio ARGUS
    portfolio_capital_gains: float = 0.0
    portfolio_capital_losses: float = 0.0
    portfolio_net_gain: float = 0.0
    portfolio_substitute_tax_est: float = 0.0
    portfolio_foreign_assets_val: float = 0.0
    portfolio_ivafe_est: float = 0.0
    # Scostamenti (Deltas: Portfolio - Dichiarato)
    delta_capital_gains: float = 0.0
    delta_substitute_tax: float = 0.0
    delta_foreign_assets: float = 0.0
    delta_ivafe: float = 0.0
    # Dettaglio Zainetto & Scadenze
    active_losses: List[Dict[str, Any]] = field(default_factory=list)
    expiring_losses: List[Dict[str, Any]] = field(default_factory=list)
    unfiled_losses: List[Dict[str, Any]] = field(default_factory=list)
    total_active_losses: float = 0.0
    total_expiring_losses: float = 0.0
    total_unfiled_losses: float = 0.0
    # Valutazione rischio sanzionatorio art. 36-bis
    art_36_bis_risk_assessment: Dict[str, Any] = field(default_factory=dict)
    # Alert & Raccomandazioni
    alerts: List[Dict[str, str]] = field(default_factory=list)
    harvesting_opportunities: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# HELPER FUNCTIONS & NUMERIC PARSERS
# ============================================================


def _parse_italian_float(val: Any) -> float:
    """Converte stringhe o numeri in float gestendo sia formato IT (1.234,56) che US (1234.56)."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip().replace("€", "").replace(" ", "")
    if not s:
        return 0.0

    # Se ci sono sia virgole che punti (es: 1.250,50 o 1,250.50)
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            # Formato IT: 1.234,56 -> 1234.56
            s = s.replace(".", "").replace(",", ".")
        else:
            # Formato US con separatore migliaia: 1,234.56 -> 1234.56
            s = s.replace(",", "")
    elif "," in s:
        # Solo virgola: 1234,56 -> 1234.56
        s = s.replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return 0.0


def fmt_eur_it(val: float) -> str:
    """Formatta un numero float in formato valuta italiana (€ 1.250,00)."""
    s = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {s}"



# ============================================================
# DATABASE CRUD: TAX DECLARATIONS
# ============================================================


def record_declaration(engine: Engine, data: Dict[str, Any]) -> int:
    """
    Inserisce o aggiorna una dichiarazione dei redditi in tax_declarations.
    Se esiste già un record con (profile_id, tax_year, model_type), lo aggiorna.
    """
    profile_id = str(data.get("profile_id", "default") or "default")
    tax_year = int(data.get("tax_year", datetime.now().year - 1))
    filing_year = int(data.get("filing_year") or (tax_year + 1))
    model_type = str(data.get("model_type", "730_ORDINARIO") or "730_ORDINARIO").upper()
    if model_type not in ["730_ORDINARIO", "730_INTEGRATIVO", "REDDITI_PF"]:
        model_type = "730_ORDINARIO"

    protocol_id = data.get("protocol_id")
    gross_income = _parse_italian_float(data.get("gross_income", 0.0))
    taxable_income = _parse_italian_float(data.get("taxable_income", 0.0))
    net_tax_irpef = _parse_italian_float(data.get("net_tax_irpef", 0.0))
    capital_gains_declared = _parse_italian_float(data.get("capital_gains_declared", 0.0))
    capital_losses_offset = _parse_italian_float(data.get("capital_losses_offset", 0.0))
    substitute_tax_paid = _parse_italian_float(data.get("substitute_tax_paid", 0.0))
    ivafe_paid = _parse_italian_float(data.get("ivafe_paid", 0.0))
    foreign_assets_val = _parse_italian_float(data.get("foreign_assets_val", 0.0))
    notes = data.get("notes")
    source_filename = data.get("source_filename")

    with engine.begin() as conn:
        # Verifica se esiste già
        check_q = sqlt("""
            SELECT id FROM tax_declarations
            WHERE profile_id = :profile_id AND tax_year = :tax_year AND model_type = :model_type
            LIMIT 1
        """)
        row = conn.execute(
            check_q,
            {"profile_id": profile_id, "tax_year": tax_year, "model_type": model_type},
        ).fetchone()

        if row:
            decl_id = row[0]
            update_q = sqlt("""
                UPDATE tax_declarations
                SET filing_year = :filing_year,
                    protocol_id = :protocol_id,
                    gross_income = :gross_income,
                    taxable_income = :taxable_income,
                    net_tax_irpef = :net_tax_irpef,
                    capital_gains_declared = :capital_gains_declared,
                    capital_losses_offset = :capital_losses_offset,
                    substitute_tax_paid = :substitute_tax_paid,
                    ivafe_paid = :ivafe_paid,
                    foreign_assets_val = :foreign_assets_val,
                    notes = :notes,
                    source_filename = :source_filename
                WHERE id = :id
            """)
            conn.execute(
                update_q,
                {
                    "id": decl_id,
                    "filing_year": filing_year,
                    "protocol_id": protocol_id,
                    "gross_income": gross_income,
                    "taxable_income": taxable_income,
                    "net_tax_irpef": net_tax_irpef,
                    "capital_gains_declared": capital_gains_declared,
                    "capital_losses_offset": capital_losses_offset,
                    "substitute_tax_paid": substitute_tax_paid,
                    "ivafe_paid": ivafe_paid,
                    "foreign_assets_val": foreign_assets_val,
                    "notes": notes,
                    "source_filename": source_filename,
                },
            )
            logger.info("Aggiornata dichiarazione ID %s per profilo %s anno %s", decl_id, profile_id, tax_year)
            return int(decl_id)
        else:
            insert_q = sqlt("""
                INSERT INTO tax_declarations (
                    profile_id, tax_year, filing_year, model_type, protocol_id,
                    gross_income, taxable_income, net_tax_irpef,
                    capital_gains_declared, capital_losses_offset, substitute_tax_paid,
                    ivafe_paid, foreign_assets_val, notes, source_filename
                ) VALUES (
                    :profile_id, :tax_year, :filing_year, :model_type, :protocol_id,
                    :gross_income, :taxable_income, :net_tax_irpef,
                    :capital_gains_declared, :capital_losses_offset, :substitute_tax_paid,
                    :ivafe_paid, :foreign_assets_val, :notes, :source_filename
                )
            """)
            res = conn.execute(
                insert_q,
                {
                    "profile_id": profile_id,
                    "tax_year": tax_year,
                    "filing_year": filing_year,
                    "model_type": model_type,
                    "protocol_id": protocol_id,
                    "gross_income": gross_income,
                    "taxable_income": taxable_income,
                    "net_tax_irpef": net_tax_irpef,
                    "capital_gains_declared": capital_gains_declared,
                    "capital_losses_offset": capital_losses_offset,
                    "substitute_tax_paid": substitute_tax_paid,
                    "ivafe_paid": ivafe_paid,
                    "foreign_assets_val": foreign_assets_val,
                    "notes": notes,
                    "source_filename": source_filename,
                },
            )
            # In SQLite / MySQL lastrowid
            new_id = getattr(res, "lastrowid", None)
            if new_id is None:
                # Query fallback
                r = conn.execute(
                    sqlt("SELECT MAX(id) FROM tax_declarations WHERE profile_id = :profile_id"),
                    {"profile_id": profile_id},
                ).fetchone()
                new_id = r[0] if r else 1
            logger.info("Creata nuova dichiarazione ID %s per profilo %s anno %s", new_id, profile_id, tax_year)
            return int(new_id)


def get_declarations(
    engine: Engine,
    profile_id: str = "default",
    tax_year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Restituisce le dichiarazioni fiscali archiviate per il profilo."""
    query = "SELECT * FROM tax_declarations WHERE profile_id = :profile_id"
    params: Dict[str, Any] = {"profile_id": str(profile_id)}
    if tax_year is not None:
        query += " AND tax_year = :tax_year"
        params["tax_year"] = int(tax_year)
    query += " ORDER BY tax_year DESC, filing_year DESC"

    with engine.connect() as conn:
        res = conn.execute(sqlt(query), params).mappings().fetchall()
        return [dict(r) for r in res]


def delete_declaration(engine: Engine, declaration_id: int) -> bool:
    """Elimina una dichiarazione fiscale dal database."""
    with engine.begin() as conn:
        res = conn.execute(sqlt("DELETE FROM tax_declarations WHERE id = :id"), {"id": int(declaration_id)})
        return (res.rowcount or 0) > 0


# ============================================================
# DATABASE CRUD: TAX LOSS CARRYFORWARD (ZAINETTO FISCALE)
# ============================================================


def record_tax_loss(engine: Engine, data: Dict[str, Any]) -> int:
    """
    Registra o aggiorna una minusvalenza nello Zainetto Fiscale.
    Applica la regola TUIR: expiration_year = generation_year + 4.
    Calcola lo stato in base a remaining_amount ed expiration_year.
    """
    profile_id = str(data.get("profile_id", "default") or "default")
    generation_year = int(data.get("generation_year", datetime.now().year))
    expiration_year = int(data.get("expiration_year") or (generation_year + 4))

    initial_loss = _parse_italian_float(data.get("initial_loss_amount", 0.0))
    offset_amount = _parse_italian_float(data.get("offset_amount", 0.0))

    if "remaining_amount" in data and data["remaining_amount"] is not None:
        remaining_amount = _parse_italian_float(data["remaining_amount"])
    else:
        remaining_amount = max(0.0, initial_loss - offset_amount)

    current_year = int(data.get("current_year", datetime.now().year))

    # Determinazione automatica stato
    if remaining_amount <= 0.001:
        status = "EXHAUSTED"
    elif current_year > expiration_year:
        status = "EXPIRED"
    else:
        status = "ACTIVE"

    is_officially_filed = bool(data.get("is_officially_filed", True))
    broker_source = str(data.get("broker_source", "DEGIRO") or "DEGIRO").upper()

    with engine.begin() as conn:
        insert_q = sqlt("""
            INSERT INTO tax_loss_carryforward (
                profile_id, generation_year, expiration_year,
                initial_loss_amount, offset_amount, remaining_amount,
                status, is_officially_filed, broker_source
            ) VALUES (
                :profile_id, :generation_year, :expiration_year,
                :initial_loss_amount, :offset_amount, :remaining_amount,
                :status, :is_officially_filed, :broker_source
            )
        """)
        res = conn.execute(
            insert_q,
            {
                "profile_id": profile_id,
                "generation_year": generation_year,
                "expiration_year": expiration_year,
                "initial_loss_amount": initial_loss,
                "offset_amount": offset_amount,
                "remaining_amount": remaining_amount,
                "status": status,
                "is_officially_filed": 1 if is_officially_filed else 0,
                "broker_source": broker_source,
            },
        )
        new_id = getattr(res, "lastrowid", None)
        if new_id is None:
            r = conn.execute(
                sqlt("SELECT MAX(id) FROM tax_loss_carryforward WHERE profile_id = :profile_id"),
                {"profile_id": profile_id},
            ).fetchone()
            new_id = r[0] if r else 1
        logger.info("Registrata minusvalenza ID %s (Anno %s, Exp %s)", new_id, generation_year, expiration_year)
        return int(new_id)


def get_tax_losses(
    engine: Engine,
    profile_id: str = "default",
    status: Optional[str] = None,
    current_year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Restituisce le quote di minusvalenze registrate per il profilo.
    Verifica e aggiorna dinamicamente lo stato EXPIRED rispetto all'anno corrente.
    """
    if current_year is None:
        current_year = datetime.now().year

    query = "SELECT * FROM tax_loss_carryforward WHERE profile_id = :profile_id"
    params: Dict[str, Any] = {"profile_id": str(profile_id)}
    if status is not None:
        query += " AND status = :status"
        params["status"] = status.upper()
    query += " ORDER BY expiration_year ASC, generation_year ASC"

    with engine.connect() as conn:
        res = conn.execute(sqlt(query), params).mappings().fetchall()
        rows = [dict(r) for r in res]

    # Post-processing per stato dinamico e boolean conversion
    clean_rows = []
    for r in rows:
        item = dict(r)
        # Normalizzazione boolean
        item["is_officially_filed"] = bool(item.get("is_officially_filed", 1))
        # Verifica se scaduta o attiva rispetto a current_year
        rem = float(item.get("remaining_amount", 0.0))
        exp = int(item.get("expiration_year", 0))
        if rem <= 0.001:
            item["status"] = "EXHAUSTED"
        elif current_year > exp:
            item["status"] = "EXPIRED"
        else:
            item["status"] = "ACTIVE"

        if status is not None and item["status"] != status.upper():
            continue

        clean_rows.append(item)

    return clean_rows


def update_tax_loss_offset(engine: Engine, loss_id: int, offset_to_add: float) -> bool:
    """Compensa una quota della minusvalenza indicata, riducendo la quota residua."""
    with engine.begin() as conn:
        row = conn.execute(
            sqlt("SELECT initial_loss_amount, offset_amount, expiration_year FROM tax_loss_carryforward WHERE id = :id"),
            {"id": int(loss_id)},
        ).fetchone()
        if not row:
            return False

        initial = float(row[0])
        current_offset = float(row[1])
        expiration_year = int(row[2])

        new_offset = current_offset + offset_to_add
        new_remaining = max(0.0, initial - new_offset)

        current_year = datetime.now().year
        if new_remaining <= 0.001:
            status = "EXHAUSTED"
        elif current_year > expiration_year:
            status = "EXPIRED"
        else:
            status = "ACTIVE"

        conn.execute(
            sqlt("""
                UPDATE tax_loss_carryforward
                SET offset_amount = :offset_amount,
                    remaining_amount = :remaining_amount,
                    status = :status
                WHERE id = :id
            """),
            {
                "id": int(loss_id),
                "offset_amount": new_offset,
                "remaining_amount": new_remaining,
                "status": status,
            },
        )
        return True


def delete_tax_loss(engine: Engine, loss_id: int) -> bool:
    """Elimina una riga dello zainetto fiscale."""
    with engine.begin() as conn:
        res = conn.execute(sqlt("DELETE FROM tax_loss_carryforward WHERE id = :id"), {"id": int(loss_id)})
        return (res.rowcount or 0) > 0


# ============================================================
# PARSER 730 / REDDITI PF (PDF / JSON / TEXT)
# ============================================================


def parse_730_pdf_or_json(
    file_content: Union[bytes, bytearray, str, dict],
    filename: str = "",
) -> Dict[str, Any]:
    """
    Estrae i quadri chiave da file PDF, JSON o payload testo di dichiarazioni fiscali:
    - Anno d'imposta e Modello (730 Ordinario, 730 Integrativo, Redditi PF)
    - Protocollo telematico
    - Reddito Complessivo (Rigo 11 / RN1) e Imponibile (Rigo 14 / RN4)
    - Imposta Netta IRPEF (Rigo 50 / RN26)
    - Quadro T/RT: Plusvalenze dichiarate (T11/RT11) e Minusvalenze compensate (T13/RT13)
    - Liquidazione Rigo 321 / 527 (Imposta sostitutiva capital gain 26%)
    - Quadro W / RW: Valore finale attività estere e IVAFE versata (Rigo 307)
    """
    # 1. Se è già un dizionario Python
    if isinstance(file_content, dict):
        return _standardize_declaration_dict(file_content, filename=filename)

    # 2. Se è una stringa, prova prima il parsing JSON
    if isinstance(file_content, str):
        try:
            parsed_json = json.loads(file_content)
            if isinstance(parsed_json, dict):
                return _standardize_declaration_dict(parsed_json, filename=filename)
        except json.JSONDecodeError:
            pass
        # Altrimenti trattala come testo grezzo estratto
        return _extract_from_text(file_content, filename=filename)

    # 3. Se sono bytes o bytearray
    if isinstance(file_content, (bytes, bytearray)):
        # Prova prima decodifica JSON testuale
        try:
            text_candidate = file_content.decode("utf-8")
            parsed_json = json.loads(text_candidate)
            if isinstance(parsed_json, dict):
                return _standardize_declaration_dict(parsed_json, filename=filename)
        except Exception:
            pass

        # Parsing PDF tramite pypdf
        extracted_text = ""
        if HAS_PYPDF:
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_content))
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        extracted_text += t + "\n"
            except Exception as e:
                logger.warning("Errore durante l'estrazione PDF con pypdf: %s", e)

        if not extracted_text:
            # Fallback euristico su bytes per stringhe ASCII visibili
            try:
                extracted_text = file_content.decode("latin-1", errors="ignore")
            except Exception:
                extracted_text = ""

        return _extract_from_text(extracted_text, filename=filename)

    return _standardize_declaration_dict({}, filename=filename)


def _standardize_declaration_dict(d: Dict[str, Any], filename: str = "") -> Dict[str, Any]:
    """Uniforma le chiavi di un dizionario alle colonne della tabella tax_declarations."""
    tax_year = int(d.get("tax_year") or d.get("anno_imposta") or (datetime.now().year - 1))
    filing_year = int(d.get("filing_year") or d.get("anno_presentazione") or (tax_year + 1))
    model_type = str(d.get("model_type") or d.get("modello") or "730_ORDINARIO").upper()
    if model_type not in ["730_ORDINARIO", "730_INTEGRATIVO", "REDDITI_PF"]:
        model_type = "730_ORDINARIO"

    return {
        "profile_id": str(d.get("profile_id", "default")),
        "tax_year": tax_year,
        "filing_year": filing_year,
        "model_type": model_type,
        "protocol_id": d.get("protocol_id") or d.get("protocollo"),
        "gross_income": _parse_italian_float(d.get("gross_income", d.get("reddito_complessivo", 0.0))),
        "taxable_income": _parse_italian_float(d.get("taxable_income", d.get("reddito_imponibile", 0.0))),
        "net_tax_irpef": _parse_italian_float(d.get("net_tax_irpef", d.get("imposta_netta", 0.0))),
        "capital_gains_declared": _parse_italian_float(
            d.get("capital_gains_declared", d.get("plusvalenze_dichiarate", d.get("rt11", 0.0)))
        ),
        "capital_losses_offset": _parse_italian_float(
            d.get("capital_losses_offset", d.get("minusvalenze_compensate", d.get("rt13", 0.0)))
        ),
        "substitute_tax_paid": _parse_italian_float(
            d.get("substitute_tax_paid", d.get("imposta_sostitutiva", d.get("rigo_321", 0.0)))
        ),
        "ivafe_paid": _parse_italian_float(d.get("ivafe_paid", d.get("ivafe", d.get("rigo_307", 0.0)))),
        "foreign_assets_val": _parse_italian_float(
            d.get("foreign_assets_val", d.get("quadro_rw_valore_finale", d.get("quadro_w", 0.0)))
        ),
        "notes": d.get("notes") or f"Importato da file: {filename}" if filename else None,
        "source_filename": filename or d.get("source_filename"),
    }


def _extract_from_text(text: str, filename: str = "") -> Dict[str, Any]:
    """Analisi regex ad alta precisione su testo estratto da modelli 730 / Redditi PF."""
    lower_text = text.lower()

    # 1. Anno d'imposta & Filing Year
    tax_year = datetime.now().year - 1
    # Check "730/2025 redditi 2024" o "Modello 730/2025"
    m_730 = re.search(r"730\s*/\s*(20\d{2})", text, re.IGNORECASE)
    m_periodo = re.search(r"(?:periodo\s+d['’]imposta|redditi\s+anno|redditi)\s*[:\s]*(20\d{2})", text, re.IGNORECASE)

    if m_periodo:
        tax_year = int(m_periodo.group(1))
    elif m_730:
        tax_year = int(m_730.group(1)) - 1

    filing_year = tax_year + 1

    # 2. Modello
    if "integrativo" in lower_text:
        model_type = "730_INTEGRATIVO"
    elif "redditi pf" in lower_text or "modello redditi" in lower_text or "quadro rn" in lower_text:
        model_type = "REDDITI_PF"
    else:
        model_type = "730_ORDINARIO"

    # 3. Protocollo Telematico
    protocol_id = None
    m_proto = re.search(
        r"(?:protocollo\s*(?:n\.?|telematico|invio)?\s*[:\s]*)([0-9A-Z]{17,35}|[0-9A-Z\-]{17,35})",
        text,
        re.IGNORECASE,
    )
    if m_proto:
        protocol_id = m_proto.group(1).strip()

    # Helper per estrazione valori monetari rigo per rigo
    def _find_amount_by_patterns(patterns: List[str]) -> float:
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return _parse_italian_float(m.group(1))
        return 0.0

    # 4. Reddito Complessivo (Rigo 11 / RN1)
    gross_income = _find_amount_by_patterns(
        [
            r"(?:reddito\s+complessivo|rigo\s+11)\D{0,30}?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})|[0-9]+(?:\.[0-9]{2})?)",
            r"(?:rn1\s+col\.\s*5|rn1\D{0,15}?)\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})|[0-9]+(?:\.[0-9]{2})?)",
        ]
    )

    # 5. Reddito Imponibile (Rigo 14 / RN4)
    taxable_income = _find_amount_by_patterns(
        [
            r"(?:reddito\s+imponibile|rigo\s+14)\D{0,30}?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})|[0-9]+(?:\.[0-9]{2})?)",
            r"(?:rn4\D{0,15}?)\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})|[0-9]+(?:\.[0-9]{2})?)",
        ]
    )

    # 6. Imposta Netta IRPEF (Rigo 50 / RN26)
    net_tax_irpef = _find_amount_by_patterns(
        [
            r"(?:imposta\s+netta|rigo\s+50)\D{0,30}?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})|[0-9]+(?:\.[0-9]{2})?)",
            r"(?:rn26\D{0,15}?)\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})|[0-9]+(?:\.[0-9]{2})?)",
        ]
    )

    # 7. Plusvalenze dichiarate (Quadro T / RT11)
    capital_gains = _find_amount_by_patterns(
        [
            r"(?:totale\s+plusvalenze(?:\s*(?:t11|rt11))?|rt11|t11)\s*[:\s]\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
            r"(?:plusvalenze\s+di\s+natura\s+finanziaria)\D{0,30}?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
        ]
    )

    # 8. Minusvalenze compensate (Quadro T / RT13)
    capital_losses = _find_amount_by_patterns(
        [
            r"(?:minusvalenze\s+compensate(?:\s*(?:t13|rt13))?|rt13|t13)\s*[:\s]\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
            r"(?:eccedenza\s+minusvalenze)\D{0,30}?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
        ]
    )

    # 9. Imposta sostitutiva capital gain (Rigo 321 / 527 / RT29 / cod. 1100)
    substitute_tax = _find_amount_by_patterns(
        [
            r"(?:rigo\s*(?:321|527)|rt29|imposta\s+sostitutiva[^\d\n]*)\s*[:\s]\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
            r"(?:codice\s+tributo\s+1100)\D{0,30}?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
        ]
    )

    # 10. IVAFE (Rigo 307 / Quadro W / RW16)
    ivafe_val = _find_amount_by_patterns(
        [
            r"(?:rigo\s*307|rw16|ivafe)\s*[:\s]\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
            r"(?:imposta\s+sul\s+valore\s+delle\s+attivit[aà]\s+finanziarie\s+all['’]estero)\D{0,30}?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})|[0-9]+(?:\.[0-9]{2})?)",
        ]
    )

    # 11. Valore finale estero Quadro W / RW
    foreign_assets = _find_amount_by_patterns(
        [
            r"(?:quadro\s+[wr]\s+valore\s+finale|valore\s+al\s+31/12|rw\s+col\.\s*8|consistenza\s+finale\s+estero)\s*[:\s]\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)",
            r"(?:quadro\s+[wr]\s+valore\s+finale|valore\s+al\s+31/12|rw\s+col\.\s*8)\D{0,30}?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})|[0-9]+(?:\.[0-9]{2})?)",
        ]
    )

    return {
        "profile_id": "default",
        "tax_year": tax_year,
        "filing_year": filing_year,
        "model_type": model_type,
        "protocol_id": protocol_id,
        "gross_income": gross_income,
        "taxable_income": taxable_income,
        "net_tax_irpef": net_tax_irpef,
        "capital_gains_declared": capital_gains,
        "capital_losses_offset": capital_losses,
        "substitute_tax_paid": substitute_tax,
        "ivafe_paid": ivafe_val,
        "foreign_assets_val": foreign_assets,
        "notes": f"Estratto automaticamente da {filename}" if filename else "Estratto da documento",
        "source_filename": filename,
    }


# ============================================================
# MOTORE DI RICONCILIAZIONE & ADVISOR AUDIT
# ============================================================


def reconcile_with_portfolio(
    engine: Engine,
    profile_id: str = "default",
    tax_year: int = 2024,
    portfolio_data: Optional[Dict[str, Any]] = None,
) -> ReconciliationReport:
    """
    Riconcilia le risultanze della dichiarazione fiscale con i dati effettivi
    calcolati dal motore di portafoglio/ledger di ARGUS:
    1. Confronta plusvalenze e IVAFE dichiarate vs flussi broker/ledger.
    2. Monitora le minusvalenze dello zainetto fiscale con la regola quadriennale.
    3. Segnala pericoli di avviso di irregolarità ex art. 36-bis d.P.R. 600/1973
       se risultano minusvalenze non formalmente registrate (is_officially_filed=False).
    4. Suggerisce manovre di Tax-Loss Harvesting prima del 31/12.
    """
    # 1. Recupera la dichiarazione archiviata per l'anno d'imposta
    declarations = get_declarations(engine, profile_id=profile_id, tax_year=tax_year)
    decl = declarations[0] if declarations else {}

    dec_cg = float(decl.get("capital_gains_declared", 0.0) or 0.0)
    dec_losses_off = float(decl.get("capital_losses_offset", 0.0) or 0.0)
    dec_sub_tax = float(decl.get("substitute_tax_paid", 0.0) or 0.0)
    dec_for_val = float(decl.get("foreign_assets_val", 0.0) or 0.0)
    dec_ivafe = float(decl.get("ivafe_paid", 0.0) or 0.0)

    # 2. Ottiene i dati reali di portafoglio
    if portfolio_data is None:
        portfolio_data = _gather_portfolio_tax_metrics(engine, profile_id=profile_id, tax_year=tax_year)

    port_cg = float(portfolio_data.get("capital_gains", 0.0) or 0.0)
    port_cl = float(portfolio_data.get("capital_losses", 0.0) or 0.0)
    port_net_gain = max(0.0, port_cg - port_cl)
    port_sub_tax_est = float(portfolio_data.get("substitute_tax_est", round(port_net_gain * 0.26, 2)))
    port_for_val = float(portfolio_data.get("foreign_assets_val", 0.0) or 0.0)
    port_ivafe_est = float(portfolio_data.get("ivafe_est", round(port_for_val * 0.0020, 2)))

    # 3. Calcolo scostamenti (Delta: Portafoglio - Dichiarato)
    delta_cg = round(port_cg - dec_cg, 2)
    delta_sub_tax = round(port_sub_tax_est - dec_sub_tax, 2)
    delta_for_val = round(port_for_val - dec_for_val, 2)
    delta_ivafe = round(port_ivafe_est - dec_ivafe, 2)

    # 4. Analisi Zainetto Fiscale e Scadenze
    losses = get_tax_losses(engine, profile_id=profile_id, current_year=tax_year)
    active_losses = [l for l in losses if l.get("status") == "ACTIVE" and l.get("remaining_amount", 0.0) > 0.0]

    # Minusvalenze in scadenza nell'anno (expiration_year <= tax_year)
    expiring_losses = [
        l for l in active_losses if int(l.get("expiration_year", 9999)) <= tax_year and l.get("remaining_amount", 0.0) > 0.0
    ]

    # Minusvalenze non formalmente depositate (is_officially_filed == False)
    unfiled_losses = [l for l in losses if not bool(l.get("is_officially_filed", True))]

    tot_active_losses = round(sum(float(l.get("remaining_amount", 0.0)) for l in active_losses), 2)
    tot_expiring_losses = round(sum(float(l.get("remaining_amount", 0.0)) for l in expiring_losses), 2)
    tot_unfiled_losses = round(sum(float(l.get("remaining_amount", 0.0)) for l in unfiled_losses), 2)

    # 5. Rischio sanzionatorio Art. 36-bis d.P.R. 600/1973
    # Se il contribuente ha usato o intende compensare minusvalenze prive di riscontro ufficiale all'AdE
    unfiled_tax_recovery = round(tot_unfiled_losses * 0.26, 2)
    unfiled_penalty_30pct = round(unfiled_tax_recovery * 0.30, 2)
    unfiled_interest_est = round(unfiled_tax_recovery * 0.05, 2)
    total_36bis_risk = round(unfiled_tax_recovery + unfiled_penalty_30pct + unfiled_interest_est, 2)

    art_36_bis_assessment = {
        "has_risk": tot_unfiled_losses > 0.0,
        "unfiled_loss_amount": tot_unfiled_losses,
        "tax_recovery_base_26pct": unfiled_tax_recovery,
        "sanzione_amministrativa_30pct": unfiled_penalty_30pct,
        "interessi_mora_stimati": unfiled_interest_est,
        "total_potential_liability": total_36bis_risk,
        "normativa_rif": "Art. 36-bis, c. 2, lett. c), d.P.R. 600/1973",
    }

    # 6. Generazione Alert & Raccomandazioni Intelligenti
    alerts: List[Dict[str, str]] = []

    # Alert 1: Rischio formale 36-bis
    if tot_unfiled_losses > 0.0:
        alerts.append(
            {
                "type": "danger",
                "code": "36BIS_UNFILED_LOSS_RISK",
                "title": "🚨 Rischio Accertamento Automatico Art. 36-bis d.P.R. 600/1973",
                "message": (
                    f"Rilevate minusvalenze per € {tot_unfiled_losses:,.2f} registrate su broker esteri o fogli interni "
                    f"MA NON formalmente dichiarate in Anagrafe Tributaria (Quadro RT/T). In sede di liquidazione automatica "
                    f"ex art. 36-bis, l'Agenzia delle Entrate disconoscerà la compensazione applicando il recupero d'imposta "
                    f"(€ {unfiled_tax_recovery:,.2f}) maggiorato di sanzione 30% (€ {unfiled_penalty_30pct:,.2f}) e interessi, "
                    f"per un debito complessivo stimato di € {total_36bis_risk:,.2f}. Si raccomanda ravvedimento o dichiarazione integrativa."
                ),
            }
        )

    # Alert 2: Minusvalenze in scadenza
    if tot_expiring_losses > 0.0:
        tax_shield_lost = round(tot_expiring_losses * 0.26, 2)
        alerts.append(
            {
                "type": "warning",
                "code": "EXPIRING_LOSS_FOUR_YEAR_LIMIT",
                "title": f"⏳ Minusvalenze in Scadenza al 31/12/{tax_year} ({fmt_eur_it(tot_expiring_losses)})",
                "message": (
                    f"Minusvalenze pregresse per un importo residuo di {fmt_eur_it(tot_expiring_losses)} decadono definitivamente "
                    f"al termine del quarto anno solare (31 dicembre {tax_year}, ex art. 68 TUIR). "
                    f"La mancata compensazione comporterà la perdita definitiva di {fmt_eur_it(tax_shield_lost)} di credito d'imposta."
                ),
            }
        )

    # Alert 3: Discrepanza Capital Gains tra broker e dichiarazione
    if abs(delta_cg) > 50.0:
        severity = "danger" if delta_cg > 100.0 else "warning"
        alerts.append(
            {
                "type": severity,
                "code": "CAPITAL_GAINS_DISCREPANCY",
                "title": f"⚠️ Discrepanza Plusvalenze Dichiarate (Delta: {fmt_eur_it(delta_cg)})",
                "message": (
                    f"Il motore contabile ARGUS rileva plusvalenze realizzate per {fmt_eur_it(port_cg)}, mentre in dichiarazione "
                    f"risultano indicate {fmt_eur_it(dec_cg)}. Scostamento di {fmt_eur_it(abs(delta_cg))} da verificare con "
                    f"i report fiscali degli intermediari (DeGiro, Directa, IBKR)."
                ),
            }
        )

    # Alert 4: Discrepanza IVAFE / Monitoraggio Estero
    if abs(delta_ivafe) > 5.0:
        alerts.append(
            {
                "type": "warning",
                "code": "IVAFE_DISCREPANCY",
                "title": f"🌐 Discrepanza IVAFE Estero (Delta: {fmt_eur_it(delta_ivafe)})",
                "message": (
                    f"L'IVAFE stimata sulle posizioni e conti esteri ARGUS è di {fmt_eur_it(port_ivafe_est)}, "
                    f"a fronte di {fmt_eur_it(dec_ivafe)} dichiarati/versati a modello."
                ),
            }
        )

    # Alert 5: Ottimizzazione Tax-Loss Harvesting prima del 31/12
    harvesting_opportunities = []
    if port_cg > 0.0 and tot_active_losses > 0.0:
        offsettable = min(port_cg, tot_active_losses)
        potential_saving = round(offsettable * 0.26, 2)
        alerts.append(
            {
                "type": "optimization",
                "code": "TAX_LOSS_HARVESTING_ACTIVE",
                "title": f"💡 Opportunità Tax-Loss Harvesting Entro il 31/12 (Risparmio {fmt_eur_it(potential_saving)})",
                "message": (
                    f"Hai generato plusvalenze per {fmt_eur_it(port_cg)} e disponi di uno zainetto fiscale residuo di {fmt_eur_it(tot_active_losses)}. "
                    f"Puoi azzerare o ridurre l'imposta sostitutiva del 26% compensando minusvalenze su singoli titoli, ETC o certificati "
                    f"(Redditi Diversi), conseguendo un risparmio tributario netto fino a {fmt_eur_it(potential_saving)}."
                ),
            }
        )
        harvesting_opportunities.append(
            {
                "strategy": "Compensazione Zainetto Fiscale",
                "available_losses": tot_active_losses,
                "current_capital_gains": port_cg,
                "offset_potential": offsettable,
                "tax_savings_eur": potential_saving,
                "action_deadline": f"31/12/{tax_year}",
            }
        )

    return ReconciliationReport(
        profile_id=profile_id,
        tax_year=tax_year,
        declared_capital_gains=dec_cg,
        declared_losses_offset=dec_losses_off,
        declared_substitute_tax=dec_sub_tax,
        declared_foreign_assets_val=dec_for_val,
        declared_ivafe=dec_ivafe,
        portfolio_capital_gains=port_cg,
        portfolio_capital_losses=port_cl,
        portfolio_net_gain=port_net_gain,
        portfolio_substitute_tax_est=port_sub_tax_est,
        portfolio_foreign_assets_val=port_for_val,
        portfolio_ivafe_est=port_ivafe_est,
        delta_capital_gains=delta_cg,
        delta_substitute_tax=delta_sub_tax,
        delta_foreign_assets=delta_for_val,
        delta_ivafe=delta_ivafe,
        active_losses=active_losses,
        expiring_losses=expiring_losses,
        unfiled_losses=unfiled_losses,
        total_active_losses=tot_active_losses,
        total_expiring_losses=tot_expiring_losses,
        total_unfiled_losses=tot_unfiled_losses,
        art_36_bis_risk_assessment=art_36_bis_assessment,
        alerts=alerts,
        harvesting_opportunities=harvesting_opportunities,
    )


def _gather_portfolio_tax_metrics(
    engine: Engine,
    profile_id: str = "default",
    tax_year: int = 2024,
) -> Dict[str, Any]:
    """
    Raccoglie le metriche fiscali stimate dal portafoglio collegato o dai flussi cashflow di ARGUS.
    """
    capital_gains = 0.0
    capital_losses = 0.0
    foreign_assets_val = 0.0
    ivafe_est = 0.0

    try:
        pid = int(profile_id) if str(profile_id).isdigit() else 1
    except Exception:
        pid = 1

    try:
        from core.wealth.wealth_engine import compute_fiscal_analytics

        fiscal = compute_fiscal_analytics(engine, portfolio_id=pid)
        foreign_assets_val = float(fiscal.get("total_foreign_assets", 0.0) or 0.0)
        ivafe_est = float(fiscal.get("total_ivafe", 0.0) or 0.0)
    except Exception as e:
        logger.debug("compute_fiscal_analytics fallback: %s", e)

    # Calcolo da cashflow se presente
    try:
        with engine.connect() as conn:
            # Dividendi e proventi finanziari nell'anno
            q_in = sqlt("""
                SELECT SUM(amount) FROM wealth_cashflow
                WHERE direction = 'inflow'
                  AND strftime('%Y', tx_date) = :yr
            """)
            r = conn.execute(q_in, {"yr": str(tax_year)}).fetchone()
            if r and r[0] is not None:
                # Una porzione come stima prudenziale
                capital_gains = max(capital_gains, float(r[0]) * 0.15)
    except Exception:
        pass

    return {
        "capital_gains": round(capital_gains, 2),
        "capital_losses": round(capital_losses, 2),
        "foreign_assets_val": round(foreign_assets_val, 2),
        "ivafe_est": round(ivafe_est, 2),
        "substitute_tax_est": round(max(0.0, capital_gains - capital_losses) * 0.26, 2),
    }
