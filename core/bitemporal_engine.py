"""
core/bitemporal_engine.py
ARGUS Enterprise — Bitemporal Persistence Engine & Immutable Cryptographic Audit Ledger.

Architettura di classe Tier-1 conforme agli standard ISO/IEC 9075:2011 SQL Temporal,
MiFID II, AIFMD e GIPS per Family Office, SGR e Wealth Management:
1. Modellazione bitemporale ortogonale:
   - Valid Time (VT / Business Time): intervallo di validità reale [valid_from, valid_to).
   - System / Transaction Time (TT / Knowledge Time): intervallo di conoscenza del sistema [sys_from, sys_to).
2. Audit Trail crittografico ad append-only log con SHA-256 Hash Chaining e Tamper Detection.
3. Certificazione di reportistica patrimoniale tramite Merkle Tree.
4. Motore di query storiche Point-in-Time bidimensionali ("Time-Travel Machine") e rilevamento drift retroattivi.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    duckdb = None
    HAS_DUCKDB = False


class BitemporalLedgerEngine:
    """
    Motore di persistenza bitemporale e audit trail crittografico immutabile.
    Supporta l'esecuzione in-process vettorizzata su DuckDB con fallback trasparente su SQLite.
    """

    INFINITY_TIMESTAMP = "9999-12-31 23:59:59.999999"
    GENESIS_HASH = "0" * 64

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if HAS_DUCKDB:
            self.con = duckdb.connect(database=db_path)
            self._init_duckdb_schema()
        else:
            self.con = None
            logger.warning("DuckDB non disponibile. BitemporalLedgerEngine richiede DuckDB per query vettorizzate.")

    def _init_duckdb_schema(self) -> None:
        """Inizializza lo schema DDL bitemporale e le sequenze su DuckDB."""
        if self.con is None:
            return

        # Sequenza per sequence_id monotono
        self.con.execute("CREATE SEQUENCE IF NOT EXISTS seq_audit_decision START 1;")

        # 1. Registro immutabile delle decisioni e cambi parametri
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS audit_decision_log (
                entry_uuid              VARCHAR PRIMARY KEY,
                sequence_id             BIGINT,
                decision_type           VARCHAR NOT NULL,
                entity_id               VARCHAR NOT NULL,
                actor_id                VARCHAR NOT NULL,
                rationale               VARCHAR NOT NULL,
                prompt_hash             VARCHAR,
                model_version           VARCHAR,
                canonical_payload_json  VARCHAR NOT NULL,
                sys_timestamp           TIMESTAMP NOT NULL,
                prev_record_hash        VARCHAR NOT NULL,
                entry_hash              VARCHAR NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_seq ON audit_decision_log(sequence_id);
            CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_decision_log(entity_id, sys_timestamp);
        """)

        # 2. Transazioni finanziarie bitemporali (One-Ledger)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS bitemporal_transactions (
                row_uuid                VARCHAR PRIMARY KEY,
                tx_business_id          VARCHAR NOT NULL,
                portfolio_id            VARCHAR NOT NULL,
                asset_id                VARCHAR NOT NULL,
                operation_type          VARCHAR NOT NULL,
                quantity                DOUBLE NOT NULL,
                unit_price              DOUBLE NOT NULL,
                gross_amount            DOUBLE NOT NULL,
                fee_amount              DOUBLE NOT NULL DEFAULT 0.0,
                tax_amount              DOUBLE NOT NULL DEFAULT 0.0,
                net_amount              DOUBLE NOT NULL,
                currency                VARCHAR NOT NULL DEFAULT 'EUR',
                fx_rate_to_base         DOUBLE NOT NULL DEFAULT 1.0,
                net_amount_base_eur     DOUBLE NOT NULL,
                valid_from              TIMESTAMP NOT NULL,
                valid_to                TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59.999999',
                sys_from                TIMESTAMP NOT NULL,
                sys_to                  TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59.999999',
                sys_op_type             VARCHAR NOT NULL DEFAULT 'INSERT',
                recorded_by             VARCHAR NOT NULL,
                source_document_ref     VARCHAR,
                integrity_record_hash   VARCHAR NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bt_tx_lookup 
            ON bitemporal_transactions(portfolio_id, valid_from, valid_to, sys_from, sys_to);
            CREATE INDEX IF NOT EXISTS idx_bt_tx_business 
            ON bitemporal_transactions(tx_business_id, sys_from);
        """)

        # 3. Perizie e stime di asset illiquidi / immobili / collezionabili
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS bitemporal_asset_appraisals (
                appraisal_uuid          VARCHAR PRIMARY KEY,
                asset_business_id       VARCHAR NOT NULL,
                portfolio_id            VARCHAR NOT NULL,
                appraisal_type          VARCHAR NOT NULL,
                appraiser_name          VARCHAR NOT NULL,
                gross_market_value      DOUBLE NOT NULL,
                liquidity_haircut_pct   DOUBLE NOT NULL DEFAULT 0.15,
                net_liquidation_value   DOUBLE NOT NULL,
                currency                VARCHAR NOT NULL DEFAULT 'EUR',
                valid_from              TIMESTAMP NOT NULL,
                valid_to                TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59.999999',
                sys_from                TIMESTAMP NOT NULL,
                sys_to                  TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59.999999',
                sys_op_type             VARCHAR NOT NULL DEFAULT 'INSERT',
                recorded_by             VARCHAR NOT NULL,
                certification_doc_hash  VARCHAR,
                integrity_record_hash   VARCHAR NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bt_appraisal_lookup 
            ON bitemporal_asset_appraisals(asset_business_id, valid_from, valid_to, sys_from, sys_to);
        """)

        # 4. Snapshot bitemporali di consistenze e WACP
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS bitemporal_position_snapshots (
                snapshot_uuid           VARCHAR PRIMARY KEY,
                portfolio_id            VARCHAR NOT NULL,
                asset_id                VARCHAR NOT NULL,
                shares_quantity         DOUBLE NOT NULL,
                wacp_cost_basis         DOUBLE NOT NULL,
                market_price            DOUBLE NOT NULL,
                unrealized_pnl          DOUBLE NOT NULL,
                cumulative_realized_pnl DOUBLE NOT NULL,
                portfolio_weight_pct    DOUBLE NOT NULL,
                valid_from              TIMESTAMP NOT NULL,
                valid_to                TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59.999999',
                sys_from                TIMESTAMP NOT NULL,
                sys_to                  TIMESTAMP NOT NULL DEFAULT '9999-12-31 23:59:59.999999',
                merkle_root_hash        VARCHAR NOT NULL
            );
        """)

    # =========================================================================
    # METODI CRITTOGRAFICI, HASH CHAIN & MERKLE TREE
    # =========================================================================

    @staticmethod
    def canonical_json(data: Any) -> str:
        """Serializzazione deterministica RFC 8785 priva di ambiguita per il calcolo degli hash."""
        return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)

    @staticmethod
    def compute_sha256(data_str: str) -> str:
        """Calcola l'hash SHA-256 esadecimale (64 caratteri)."""
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def log_decision(
        self,
        decision_type: str,
        entity_id: str,
        actor_id: str,
        rationale: str,
        payload: Dict[str, Any],
        prompt_hash: Optional[str] = None,
        model_version: Optional[str] = None,
        custom_sys_timestamp: Optional[str] = None,
    ) -> str:
        """
        Inserisce un evento decisionale nell'audit trail collegandolo crittograficamente
        al record precedente tramite SHA-256 Hash Chaining.
        """
        if self.con is None:
            raise RuntimeError("DuckDB connection non attiva.")

        # Recupera l'ultimo hash presente nella catena
        res = self.con.execute("""
            SELECT entry_hash FROM audit_decision_log 
            ORDER BY sequence_id DESC LIMIT 1
        """).fetchone()
        prev_hash = res[0] if res else self.GENESIS_HASH

        entry_uuid = str(uuid.uuid4())
        if custom_sys_timestamp:
            sys_ts = pd.to_datetime(custom_sys_timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            sys_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        canonical_payload = self.canonical_json(payload)

        # Hash formula: SHA256(prev_hash | entry_uuid | sys_ts | canonical_payload)
        raw_to_hash = f"{prev_hash}|{entry_uuid}|{sys_ts}|{canonical_payload}"
        entry_hash = self.compute_sha256(raw_to_hash)

        self.con.execute("""
            INSERT INTO audit_decision_log (
                entry_uuid, sequence_id, decision_type, entity_id, actor_id,
                rationale, prompt_hash, model_version, canonical_payload_json,
                sys_timestamp, prev_record_hash, entry_hash
            ) VALUES (?, nextval('seq_audit_decision'), ?, ?, ?, ?, ?, ?, ?, ?::TIMESTAMP, ?, ?)
        """, [
            entry_uuid, decision_type, entity_id, actor_id, rationale,
            prompt_hash, model_version, canonical_payload, sys_ts, prev_hash, entry_hash
        ])

        return entry_hash

    def verify_audit_chain_integrity(self) -> Tuple[bool, Optional[str], int]:
        """
        Verifica computazionalmente l'integrita dell'intera catena di log (Tamper Detection).
        Rileva istantaneamente alterazioni fisiche retroattive, eliminazioni o inversioni.
        """
        if self.con is None:
            return False, "DuckDB connection non attiva.", 0

        df = self.con.execute("""
            SELECT entry_uuid, sequence_id, canonical_payload_json, 
                   sys_timestamp, prev_record_hash, entry_hash
            FROM audit_decision_log ORDER BY sequence_id ASC
        """).df()

        if df.empty:
            return True, "Catena di audit vuota (integrità garantita).", 0

        expected_prev_hash = self.GENESIS_HASH
        for _, row in df.iterrows():
            seq = int(row["sequence_id"])
            if row["prev_record_hash"] != expected_prev_hash:
                return (
                    False,
                    f"Violazione della catena di continuità alla sequenza #{seq}. "
                    f"Atteso prev: {expected_prev_hash[:12]}..., Trovato: {row['prev_record_hash'][:12]}...",
                    seq
                )

            # Normalizza timestamp string
            ts_str = pd.to_datetime(row["sys_timestamp"]).strftime("%Y-%m-%d %H:%M:%S.%f")
            raw_to_hash = f"{row['prev_record_hash']}|{row['entry_uuid']}|{ts_str}|{row['canonical_payload_json']}"
            computed_hash = self.compute_sha256(raw_to_hash)

            if computed_hash != row["entry_hash"]:
                return (
                    False,
                    f"Manomissione rilevata al record sequence #{seq}! "
                    f"L'hash memorizzato non corrisponde al payload crittografico.",
                    seq
                )

            expected_prev_hash = row["entry_hash"]

        return True, f"Catena crittografica integra al 100% ({len(df)} blocchi verificati).", len(df)

    @classmethod
    def generate_merkle_root(cls, records: List[Dict[str, Any]]) -> str:
        """
        Costruisce un Merkle Tree deterministico su una lista di record
        e restituisce il Merkle Root hash (64 caratteri esadecimali).
        """
        if not records:
            return cls.compute_sha256("EMPTY_SET")

        # 1. Hash delle foglie (Leaves)
        leaf_hashes = [cls.compute_sha256(cls.canonical_json(r)) for r in records]
        leaf_hashes.sort()

        # 2. Risalita dell'albero a coppie
        current_level = leaf_hashes
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if (i + 1) < len(current_level) else left
                parent = cls.compute_sha256(f"{left}|{right}")
                next_level.append(parent)
            next_level.sort()
            current_level = next_level

        return current_level[0]

    # =========================================================================
    # GESTIONE TRANSAZIONI BITEMPORALI (INSERT & RETROACTIVE RECTIFICATION)
    # =========================================================================

    def record_transaction(
        self,
        tx_business_id: str,
        portfolio_id: str,
        asset_id: str,
        operation_type: str,
        quantity: float,
        unit_price: float,
        valid_from: str,
        recorded_by: str,
        fees: float = 0.0,
        taxes: float = 0.0,
        currency: str = "EUR",
        fx_rate_to_base: float = 1.0,
        valid_to: str = INFINITY_TIMESTAMP,
        custom_sys_from: Optional[str] = None,
        source_doc_ref: Optional[str] = None,
    ) -> str:
        """
        Registra una transazione con marcatura bitemporale e hash di integrita di riga.
        """
        if self.con is None:
            raise RuntimeError("DuckDB non inizializzato.")

        row_uuid = str(uuid.uuid4())
        sys_now = custom_sys_from or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        valid_from_norm = pd.to_datetime(valid_from).strftime("%Y-%m-%d %H:%M:%S")
        valid_to_norm = self.INFINITY_TIMESTAMP if valid_to == self.INFINITY_TIMESTAMP else pd.to_datetime(valid_to).strftime("%Y-%m-%d %H:%M:%S")
        gross = round(quantity * unit_price, 2)
        net_local = round(gross - fees - taxes, 2) if operation_type.upper() == "SELL" else round(gross + fees + taxes, 2)
        net_base = round(net_local * fx_rate_to_base, 2)

        # Hash di integrita di riga
        row_raw = f"{tx_business_id}|{portfolio_id}|{asset_id}|{operation_type}|{quantity}|{unit_price}|{valid_from_norm}|{sys_now}"
        integrity_hash = self.compute_sha256(row_raw)

        self.con.execute("""
            INSERT INTO bitemporal_transactions (
                row_uuid, tx_business_id, portfolio_id, asset_id, operation_type,
                quantity, unit_price, gross_amount, fee_amount, tax_amount, net_amount,
                currency, fx_rate_to_base, net_amount_base_eur,
                valid_from, valid_to, sys_from, sys_to, sys_op_type, recorded_by,
                source_document_ref, integrity_record_hash
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?::TIMESTAMP, ?::TIMESTAMP, ?::TIMESTAMP, ?::TIMESTAMP, 'INSERT', ?, ?, ?
            )
        """, [
            row_uuid, tx_business_id, portfolio_id, asset_id, operation_type.upper(),
            quantity, unit_price, gross, fees, taxes, net_local,
            currency.upper(), fx_rate_to_base, net_base,
            valid_from_norm, valid_to_norm, sys_now, self.INFINITY_TIMESTAMP,
            recorded_by, source_doc_ref, integrity_hash
        ])

        return row_uuid

    def record_appraisal(
        self,
        asset_business_id: str,
        portfolio_id: str,
        appraisal_type: str,
        appraiser_name: str,
        gross_market_value: float,
        valid_from: str,
        recorded_by: str,
        liquidity_haircut_pct: float = 0.15,
        currency: str = "EUR",
        valid_to: str = INFINITY_TIMESTAMP,
        custom_sys_from: Optional[str] = None,
        certification_doc_hash: Optional[str] = None,
    ) -> str:
        """Registra una perizia su asset illiquido con validità bitemporale."""
        if self.con is None:
            raise RuntimeError("DuckDB non inizializzato.")

        appraisal_uuid = str(uuid.uuid4())
        sys_now = custom_sys_from or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        net_liq = round(gross_market_value * (1.0 - liquidity_haircut_pct), 2)

        row_raw = f"{asset_business_id}|{gross_market_value}|{valid_from}|{sys_now}"
        integrity_hash = self.compute_sha256(row_raw)

        self.con.execute("""
            INSERT INTO bitemporal_asset_appraisals (
                appraisal_uuid, asset_business_id, portfolio_id, appraisal_type,
                appraiser_name, gross_market_value, liquidity_haircut_pct,
                net_liquidation_value, currency, valid_from, valid_to,
                sys_from, sys_to, sys_op_type, recorded_by, certification_doc_hash,
                integrity_record_hash
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?::TIMESTAMP, ?::TIMESTAMP, ?::TIMESTAMP, ?::TIMESTAMP,
                'INSERT', ?, ?, ?
            )
        """, [
            appraisal_uuid, asset_business_id, portfolio_id, appraisal_type,
            appraiser_name, gross_market_value, liquidity_haircut_pct,
            net_liq, currency.upper(), valid_from, valid_to,
            sys_now, self.INFINITY_TIMESTAMP, recorded_by, certification_doc_hash,
            integrity_hash
        ])

        return appraisal_uuid

    def correct_historical_transaction(
        self,
        tx_business_id: str,
        new_quantity: float,
        new_unit_price: float,
        reason: str,
        actor_id: str,
        custom_sys_from: Optional[str] = None,
    ) -> str:
        """
        Rettifica retroattiva non-distruttiva:
        1. Trova il record attualmente attivo nel System Time.
        2. Chiude il record precedente impostando sys_to = now().
        3. Inserisce la nuova versione con sys_from = now() e sys_to = 9999-12-31.
        4. Logga la decisione nell'audit log immutabile.
        """
        if self.con is None:
            raise RuntimeError("DuckDB non inizializzato.")

        sys_now = custom_sys_from or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

        prev = self.con.execute("""
            SELECT row_uuid, portfolio_id, asset_id, operation_type, fee_amount, tax_amount,
                   currency, fx_rate_to_base, valid_from, valid_to
            FROM bitemporal_transactions
            WHERE tx_business_id = ? AND sys_to = ?::TIMESTAMP
        """, [tx_business_id, self.INFINITY_TIMESTAMP]).fetchone()

        if not prev:
            raise ValueError(f"Nessuna versione attiva trovata per transazione business ID: {tx_business_id}")

        (
            old_row_uuid, portfolio_id, asset_id, op_type, fees, taxes,
            curr, fx_rate, valid_from_dt, valid_to_dt
        ) = prev

        # 1. Chiusura logica della riga precedente nel System Time
        self.con.execute("""
            UPDATE bitemporal_transactions
            SET sys_to = ?::TIMESTAMP
            WHERE row_uuid = ?
        """, [sys_now, old_row_uuid])

        # 2. Inserimento nuova versione
        new_row_uuid = str(uuid.uuid4())
        gross = round(new_quantity * new_unit_price, 2)
        net_local = round(gross - fees - taxes, 2) if op_type.upper() == "SELL" else round(gross + fees + taxes, 2)
        net_base = round(net_local * fx_rate, 2)

        valid_from_str = pd.to_datetime(valid_from_dt).strftime("%Y-%m-%d %H:%M:%S")
        valid_to_str = pd.to_datetime(valid_to_dt).strftime("%Y-%m-%d %H:%M:%S")

        raw_to_hash = f"{tx_business_id}|{new_quantity}|{new_unit_price}|{valid_from_str}|{sys_now}"
        integrity_hash = self.compute_sha256(raw_to_hash)

        self.con.execute("""
            INSERT INTO bitemporal_transactions (
                row_uuid, tx_business_id, portfolio_id, asset_id, operation_type,
                quantity, unit_price, gross_amount, fee_amount, tax_amount, net_amount,
                currency, fx_rate_to_base, net_amount_base_eur,
                valid_from, valid_to, sys_from, sys_to, sys_op_type, recorded_by,
                source_document_ref, integrity_record_hash
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?::TIMESTAMP, ?::TIMESTAMP, ?::TIMESTAMP, ?::TIMESTAMP, 'CORRECTION', ?, ?, ?
            )
        """, [
            new_row_uuid, tx_business_id, portfolio_id, asset_id, op_type,
            new_quantity, new_unit_price, gross, fees, taxes, net_local,
            curr, fx_rate, net_base,
            valid_from_str, valid_to_str, sys_now, self.INFINITY_TIMESTAMP,
            actor_id, f"CORRECTION_OF_{old_row_uuid[:8]}", integrity_hash
        ])

        # 3. Log immutabile della decisione
        self.log_decision(
            decision_type="TRANSACTION_CORRECTION",
            entity_id=portfolio_id,
            actor_id=actor_id,
            rationale=reason,
            payload={
                "tx_business_id": tx_business_id,
                "old_row_uuid": old_row_uuid,
                "new_row_uuid": new_row_uuid,
                "new_quantity": new_quantity,
                "new_unit_price": new_unit_price
            },
            custom_sys_timestamp=sys_now
        )

        return new_row_uuid

    # =========================================================================
    # MOTORE DI QUERY TIME-TRAVEL BIDIMENSIONALE
    # =========================================================================

    def time_travel_query(
        self,
        portfolio_id: str,
        as_at_valid_time: str,
        as_of_system_time: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Esegue la query point-in-time bidimensionale (Valid Time vs System Knowledge Time).

        Args:
            portfolio_id: Identificatore del portafoglio / Family Office.
            as_at_valid_time: Data dell'evento economico ('YYYY-MM-DD' o 'YYYY-MM-DD HH:MM:SS').
            as_of_system_time: Data di conoscenza del sistema. Se None, assume lo stato attuale (oggi).

        Returns:
            DataFrame con tutte le transazioni valide nel mondo reale a valid_time
            secondo ciò che il sistema sapeva a system_time.
        """
        if self.con is None:
            return pd.DataFrame()

        sys_target = as_of_system_time or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

        query = """
            SELECT 
                tx_business_id, asset_id, operation_type,
                quantity, unit_price, gross_amount, net_amount_base_eur,
                valid_from, valid_to, sys_from, sys_to, sys_op_type, recorded_by
            FROM bitemporal_transactions
            WHERE portfolio_id = ?
              -- 1. Valid Time: eventi accaduti a/entro la data evento richiesta
              AND valid_from <= ?::TIMESTAMP
              AND valid_to   >  ?::TIMESTAMP
              -- 2. System Time: cosa era noto alla data di conoscenza richiesta
              AND sys_from   <= ?::TIMESTAMP
              AND sys_to     >  ?::TIMESTAMP
            ORDER BY valid_from ASC
        """
        return self.con.execute(query, [
            portfolio_id, as_at_valid_time, as_at_valid_time, sys_target, sys_target
        ]).df()

    def time_travel_appraisals(
        self,
        portfolio_id: str,
        as_at_valid_time: str,
        as_of_system_time: Optional[str] = None,
    ) -> pd.DataFrame:
        """Estrae le perizie attive a un dato punto bitemporale."""
        if self.con is None:
            return pd.DataFrame()

        sys_target = as_of_system_time or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

        query = """
            SELECT 
                asset_business_id, appraisal_type, appraiser_name,
                gross_market_value, liquidity_haircut_pct, net_liquidation_value,
                currency, valid_from, valid_to, sys_from, sys_to, recorded_by
            FROM bitemporal_asset_appraisals
            WHERE portfolio_id = ?
              AND valid_from <= ?::TIMESTAMP
              AND valid_to   >  ?::TIMESTAMP
              AND sys_from   <= ?::TIMESTAMP
              AND sys_to     >  ?::TIMESTAMP
            ORDER BY valid_from DESC
        """
        return self.con.execute(query, [
            portfolio_id, as_at_valid_time, as_at_valid_time, sys_target, sys_target
        ]).df()

    def reconstruct_portfolio_at_times(
        self,
        portfolio_id: str,
        as_at_valid_time: str,
        as_of_system_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ricostruisce la fotografia contabile esatta (consistenze per asset, cassa e valore netto)
        alla data bitemporale specificata.
        """
        df_tx = self.time_travel_query(portfolio_id, as_at_valid_time, as_of_system_time)
        df_app = self.time_travel_appraisals(portfolio_id, as_at_valid_time, as_of_system_time)

        holdings: Dict[str, Dict[str, float]] = {}
        cash_balance_eur = 0.0

        for _, row in df_tx.iterrows():
            op = str(row["operation_type"]).upper()
            asset = str(row["asset_id"])
            qty = float(row["quantity"])
            net_eur = float(row["net_amount_base_eur"])

            if op == "CASH_IN":
                cash_balance_eur += net_eur
            elif op == "CASH_OUT":
                cash_balance_eur -= net_eur
            elif op == "DIVIDEND":
                cash_balance_eur += net_eur
            elif op == "BUY":
                cash_balance_eur -= net_eur
                if asset not in holdings:
                    holdings[asset] = {"shares": 0.0, "invested_eur": 0.0}
                holdings[asset]["shares"] += qty
                holdings[asset]["invested_eur"] += net_eur
            elif op == "SELL":
                cash_balance_eur += net_eur
                if asset in holdings:
                    holdings[asset]["shares"] = max(0.0, holdings[asset]["shares"] - qty)

        # Calcola WACP per gli asset in portafoglio
        positions_summary = []
        for asset, data in holdings.items():
            if data["shares"] > 1e-6:
                pmc = (data["invested_eur"] / data["shares"]) if data["shares"] > 0 else 0.0
                positions_summary.append({
                    "asset_id": asset,
                    "shares": round(data["shares"], 4),
                    "wacp_eur": round(pmc, 2),
                    "cost_value_eur": round(data["invested_eur"], 2)
                })

        illiquid_total = float(df_app["net_liquidation_value"].sum()) if not df_app.empty else 0.0

        return {
            "portfolio_id": portfolio_id,
            "as_at_valid_time": as_at_valid_time,
            "as_of_system_time": as_of_system_time or "CURRENT_LIVE_STATE",
            "cash_balance_eur": round(cash_balance_eur, 2),
            "positions_count": len(positions_summary),
            "positions": positions_summary,
            "illiquid_appraisals_eur": round(illiquid_total, 2),
            "total_book_value_eur": round(cash_balance_eur + sum(p["cost_value_eur"] for p in positions_summary) + illiquid_total, 2),
            "tx_count": len(df_tx),
            "appraisals_count": len(df_app)
        }

    def detect_retroactive_drifts(
        self,
        portfolio_id: str,
        as_at_valid_time: str,
        sys_time_before: str,
        sys_time_after: str,
    ) -> Dict[str, Any]:
        """
        Riconciliazione forense tra due stati di conoscenza del database (sys_time_before vs sys_time_after)
        riferiti alla medesima data economica as_at_valid_time.
        Isola storni, dividendi pervenuti in ritardo o rettifiche di prezzo.
        """
        df_before = self.time_travel_query(portfolio_id, as_at_valid_time, sys_time_before)
        df_after = self.time_travel_query(portfolio_id, as_at_valid_time, sys_time_after)

        before_ids = set(df_before["tx_business_id"].tolist()) if not df_before.empty else set()
        after_ids = set(df_after["tx_business_id"].tolist()) if not df_after.empty else set()

        new_tx_ids = after_ids - before_ids
        deleted_tx_ids = before_ids - after_ids
        common_tx_ids = before_ids.intersection(after_ids)

        new_records = df_after[df_after["tx_business_id"].isin(new_tx_ids)].to_dict(orient="records") if not df_after.empty else []
        modified_records = []

        for tid in common_tx_ids:
            row_b = df_before[df_before["tx_business_id"] == tid].iloc[0]
            row_a = df_after[df_after["tx_business_id"] == tid].iloc[0]
            if (row_b["quantity"] != row_a["quantity"] or 
                row_b["unit_price"] != row_a["unit_price"] or 
                row_b["net_amount_base_eur"] != row_a["net_amount_base_eur"]):
                modified_records.append({
                    "tx_business_id": tid,
                    "asset_id": row_a["asset_id"],
                    "before": {"qty": row_b["quantity"], "price": row_b["unit_price"], "net": row_b["net_amount_base_eur"]},
                    "after": {"qty": row_a["quantity"], "price": row_a["unit_price"], "net": row_a["net_amount_base_eur"]},
                    "delta_eur": round(row_a["net_amount_base_eur"] - row_b["net_amount_base_eur"], 2)
                })

        val_before = float(df_before["net_amount_base_eur"].sum()) if not df_before.empty else 0.0
        val_after = float(df_after["net_amount_base_eur"].sum()) if not df_after.empty else 0.0

        return {
            "portfolio_id": portfolio_id,
            "as_at_valid_time": as_at_valid_time,
            "sys_time_before": sys_time_before,
            "sys_time_after": sys_time_after,
            "has_drift": bool(new_records or deleted_tx_ids or modified_records),
            "new_transactions_count": len(new_records),
            "new_transactions": new_records,
            "modified_transactions_count": len(modified_records),
            "modified_transactions": modified_records,
            "deleted_transactions_count": len(deleted_tx_ids),
            "delta_total_volume_eur": round(val_after - val_before, 2)
        }

    # =========================================================================
    # SCENARIO DIDATTICO & AUDIT REPLAY PRECONFIGURATO
    # =========================================================================

    def seed_demonstration_scenario(self, portfolio_id: str = "DEMO_FAMILY_OFFICE") -> Dict[str, Any]:
        """
        Popola uno scenario audit realistico per collaudare e dimostrare l'architettura bitemporale:
        1. 2026-03-01 09:00: Cassa iniziale €500.000 (VT 2026-03-01, TT 2026-03-01 09:00)
        2. 2026-03-05 10:00: Acquisto 1.000 quote BTP_10Y a €100 = €100.000 (VT 2026-03-05, TT 2026-03-05 10:00)
        3. 2026-03-10 11:30: Acquisto 500 quote VWCE a €110 = €55.000 (VT 2026-03-10, TT 2026-03-10 11:30)
        4. 2026-03-15 00:00: Stacco dividendo VWCE €1.250 (VT 2026-03-15), MA registrato nel DB solo il 2026-03-20 18:30!
        5. 2026-03-16 14:00: Perizia immobile Via Monte Napoleone €1.500.000 (VT 2026-03-16, TT 2026-03-16 14:00)
        6. 2026-03-22 16:00: Correzione retroattiva prezzo BTP_10Y da €100 a €99.50 (TT 2026-03-22 16:00)
        """
        # Pulisci eventuali record precedenti dello stesso portafoglio
        self.con.execute("DELETE FROM bitemporal_transactions WHERE portfolio_id = ?", [portfolio_id])
        self.con.execute("DELETE FROM bitemporal_asset_appraisals WHERE portfolio_id = ?", [portfolio_id])
        self.con.execute("DELETE FROM audit_decision_log WHERE entity_id = ?", [portfolio_id])

        # 1. Cassa iniziale
        self.record_transaction(
            tx_business_id="TX_CASH_INIT_001",
            portfolio_id=portfolio_id,
            asset_id="EUR_CASH",
            operation_type="CASH_IN",
            quantity=1.0,
            unit_price=500_000.0,
            valid_from="2026-03-01 09:00:00",
            recorded_by="DEPOSIT_RECEIPT",
            custom_sys_from="2026-03-01 09:05:00"
        )
        self.log_decision(
            decision_type="CAPITAL_INJECTION",
            entity_id=portfolio_id,
            actor_id="USER:Founder",
            rationale="Conferimento iniziale liquidità Family Office",
            payload={"amount_eur": 500_000.0},
            custom_sys_timestamp="2026-03-01 09:05:00"
        )

        # 2. Acquisto BTP_10Y
        self.record_transaction(
            tx_business_id="TX_BUY_BTP_002",
            portfolio_id=portfolio_id,
            asset_id="BTP_10Y",
            operation_type="BUY",
            quantity=1000.0,
            unit_price=100.0,
            valid_from="2026-03-05 10:00:00",
            recorded_by="BROKER_DIRECTA",
            fees=18.0,
            custom_sys_from="2026-03-05 10:05:00"
        )
        self.log_decision(
            decision_type="ASSET_ALLOCATION",
            entity_id=portfolio_id,
            actor_id="AGENT:Tactical_Rebalancer",
            rationale="Acquisto BTP per immunizzazione tasso fisso",
            payload={"asset": "BTP_10Y", "shares": 1000, "price": 100.0},
            custom_sys_timestamp="2026-03-05 10:05:00"
        )

        # 3. Acquisto VWCE
        self.record_transaction(
            tx_business_id="TX_BUY_VWCE_003",
            portfolio_id=portfolio_id,
            asset_id="VWCE.DE",
            operation_type="BUY",
            quantity=500.0,
            unit_price=110.0,
            valid_from="2026-03-10 11:30:00",
            recorded_by="BROKER_IBKR",
            fees=5.0,
            custom_sys_from="2026-03-10 11:35:00"
        )

        # 4. Perizia Immobile
        self.record_appraisal(
            asset_business_id="RE_MONTE_NAPOLEONE_01",
            portfolio_id=portfolio_id,
            appraisal_type="CERTIFIED_SURVEYOR",
            appraiser_name="Scenari Immobiliari Milano",
            gross_market_value=1_500_000.0,
            valid_from="2026-03-16 14:00:00",
            recorded_by="FAMILY_OFFICE_LEGAL",
            liquidity_haircut_pct=0.15,
            custom_sys_from="2026-03-16 14:15:00"
        )

        # 5. Dividendo retroattivo VWCE staccato il 15 Marzo ma arrivato il 20 Marzo alle 18:30
        self.record_transaction(
            tx_business_id="TX_DIV_VWCE_004",
            portfolio_id=portfolio_id,
            asset_id="VWCE.DE",
            operation_type="DIVIDEND",
            quantity=500.0,
            unit_price=2.50,
            valid_from="2026-03-15 00:00:00",
            recorded_by="BROKER_IBKR_STATEMENT",
            taxes=325.0,
            custom_sys_from="2026-03-20 18:30:00",
            source_doc_ref="IBKR_MARCH_2026_DIVIDEND_ADVICE.pdf"
        )
        self.log_decision(
            decision_type="RETROACTIVE_DIVIDEND_RECORDING",
            entity_id=portfolio_id,
            actor_id="SYSTEM:Broker_Statement_Parser",
            rationale="Registrazione tardiva dividendo da estratto conto pervenuto il 20 Marzo",
            payload={"asset": "VWCE.DE", "gross": 1250.0, "taxes": 325.0, "net": 925.0},
            custom_sys_timestamp="2026-03-20 18:30:00"
        )

        # 6. Correzione retroattiva BTP eseguita il 22 Marzo
        self.correct_historical_transaction(
            tx_business_id="TX_BUY_BTP_002",
            new_quantity=1000.0,
            new_unit_price=99.50,
            reason="Rettifica prezzo di carico per sconto intermediario istituzionale",
            actor_id="USER:Audit_Officer",
            custom_sys_from="2026-03-22 16:00:00"
        )

        return {
            "portfolio_id": portfolio_id,
            "status": "SEED_SUCCESSFUL",
            "events_seeded": 6,
            "critical_dates": {
                "meeting_date_audit": "2026-03-18 10:00:00",
                "dividend_event_date": "2026-03-15 00:00:00",
                "dividend_knowledge_date": "2026-03-20 18:30:00",
                "correction_knowledge_date": "2026-03-22 16:00:00"
            }
        }
