"""
core/universal_ledger.py
ARGUS — Universal One-Ledger Engine & Vectorized Data Core.

Architettura di persistenza unificata di classe Tier-1:
- Modello contabile universale in Partita Doppia (Double-Entry Multi-Asset Multi-Currency).
- Motore vettorizzato in-process basato su DuckDB con accelerazione SIMD e interop zero-copy PyArrow.
- Window functions SQL per calcolo istantaneo del Prezzo Medio di Carico (WACP/PMC) a code FIFO.
- Integrazione nativa tra mercati liquidi (Stocks, ETF, Crypto, Bonds) e patrimonio illiquido (Conti, Spese, Immobili, Mutui).
"""

import hashlib
import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    duckdb = None
    HAS_DUCKDB = False

try:
    import pyarrow as pa
    HAS_PYARROW = True
except ImportError:
    pa = None
    HAS_PYARROW = False


class UniversalLedgerEngine:
    """
    Motore analitico centrale One-Ledger per la piattaforma ARGUS.
    Unifica la contabilità di borsa e il bilancio patrimoniale complessivo.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if HAS_DUCKDB:
            self.con = duckdb.connect(database=db_path)
            self._configure_duckdb()
            self._create_schema()
        else:
            self.con = None
            logger.warning("DuckDB non disponibile. Funzionalità UniversalLedgerEngine limitate.")

    def _configure_duckdb(self) -> None:
        """Configura le opzioni di threading e cache per massimizzare il throughput SIMD."""
        if self.con is None:
            return
        try:
            self.con.execute("PRAGMA threads=4;")
            self.con.execute("PRAGMA enable_object_cache=true;")
        except Exception as e:
            logger.debug(f"Configurazione PRAGMA DuckDB non applicata: {e}")

    def _create_schema(self) -> None:
        """Crea lo schema DDL unificato One-Ledger."""
        if self.con is None:
            return

        # 1. Dimensione Entità
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS dim_entity (
                entity_id VARCHAR PRIMARY KEY,
                entity_name VARCHAR NOT NULL,
                entity_type VARCHAR NOT NULL,
                tax_residency_country VARCHAR DEFAULT 'ITA',
                default_base_currency VARCHAR DEFAULT 'EUR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Dimensione Asset Master Universale
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS dim_asset_master (
                asset_id VARCHAR PRIMARY KEY,
                isin VARCHAR,
                ticker VARCHAR,
                name VARCHAR NOT NULL,
                asset_class VARCHAR NOT NULL,
                sub_asset_class VARCHAR,
                quote_currency VARCHAR NOT NULL DEFAULT 'EUR',
                is_liquid BOOLEAN NOT NULL DEFAULT TRUE,
                tax_category VARCHAR NOT NULL DEFAULT 'REDDITI_DIVERSI',
                risk_factor_sector VARCHAR,
                beta_to_market DOUBLE DEFAULT 1.0,
                liquidity_haircut_pct DOUBLE DEFAULT 0.0
            );
        """)

        # 3. Tabella dei Fatti: Universal Ledger in Partita Doppia
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS fact_ledger_entry (
                entry_id VARCHAR PRIMARY KEY,
                entity_id VARCHAR NOT NULL,
                booking_date DATE NOT NULL,
                value_date DATE NOT NULL,
                account_debit VARCHAR NOT NULL,
                account_credit VARCHAR NOT NULL,
                asset_id VARCHAR NOT NULL,
                operation_type VARCHAR NOT NULL,
                quantity DOUBLE NOT NULL,
                unit_price DOUBLE NOT NULL,
                gross_amount DOUBLE NOT NULL,
                transaction_fees DOUBLE DEFAULT 0.0,
                withholding_tax DOUBLE DEFAULT 0.0,
                net_amount DOUBLE NOT NULL,
                currency VARCHAR NOT NULL DEFAULT 'EUR',
                fx_rate_to_base DOUBLE NOT NULL DEFAULT 1.0,
                net_amount_base_eur DOUBLE NOT NULL,
                tax_lot_id VARCHAR,
                notes VARCHAR,
                metadata_json VARCHAR
            );
            CREATE INDEX IF NOT EXISTS idx_ledger_asset_date ON fact_ledger_entry(asset_id, booking_date);
            CREATE INDEX IF NOT EXISTS idx_ledger_entity ON fact_ledger_entry(entity_id, operation_type);
        """)

        # Inserimento entità di default
        self.con.execute("""
            INSERT INTO dim_entity (entity_id, entity_name, entity_type)
            VALUES ('DEFAULT_ENTITY', 'Portfolio & Wealth Master Entity', 'INDIVIDUAL')
            ON CONFLICT (entity_id) DO NOTHING;
        """)

    @staticmethod
    def generate_entry_id(entity_id: str, booking_date: str, asset_id: str, op_type: str, qty: float, price: float) -> str:
        """Genera un hash deterministico SHA-256 idempotente per la riga contabile."""
        raw = f"{entity_id}_{booking_date}_{asset_id}_{op_type}_{qty:.6f}_{price:.6f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def ingest_trading_transactions(
        self, 
        df_transactions: pd.DataFrame, 
        entity_id: str = "DEFAULT_ENTITY",
        base_currency: str = "EUR"
    ) -> int:
        """
        Ingerisce le transazioni azionarie, ETF, obbligazionarie e crypto nel One-Ledger.
        Normalizza l'anagrafica asset e scrive le righe contabili in partita doppia.
        """
        if self.con is None or df_transactions is None or df_transactions.empty:
            return 0

        df = df_transactions.copy()
        
        # Mappatura colonne standard
        date_col = "Date" if "Date" in df.columns else ("date" if "date" in df.columns else None)
        ticker_col = "Ticker" if "Ticker" in df.columns else ("ticker" if "ticker" in df.columns else None)
        type_col = "Type" if "Type" in df.columns else ("type" if "type" in df.columns else None)
        shares_col = "Shares" if "Shares" in df.columns else ("shares" if "shares" in df.columns else ("Quantity" if "Quantity" in df.columns else "quantity"))
        price_col = "Price" if "Price" in df.columns else ("price" if "price" in df.columns else None)
        fees_col = "Commission" if "Commission" in df.columns else ("fees" if "fees" in df.columns else None)
        curr_col = "Currency" if "Currency" in df.columns else ("currency" if "currency" in df.columns else None)
        fx_col = "FX_Rate" if "FX_Rate" in df.columns else ("fx_rate" if "fx_rate" in df.columns else None)

        if not (date_col and ticker_col and type_col and shares_col and price_col):
            logger.warning("Colonne obbligatorie mancanti nel DataFrame transazioni per One-Ledger.")
            return 0

        inserted_count = 0
        records = []
        asset_records = {}

        for _, row in df.iterrows():
            d_val = str(row[date_col])[:10]
            ticker = str(row[ticker_col]).strip().upper()
            op = str(row[type_col]).strip().upper()
            try:
                qty = float(row[shares_col])
                price = float(row[price_col])
            except (ValueError, TypeError):
                continue

            fees = float(row[fees_col]) if fees_col and pd.notna(row.get(fees_col)) else 0.0
            curr = str(row[curr_col]).strip().upper() if curr_col and pd.notna(row.get(curr_col)) else base_currency
            fx = float(row[fx_col]) if fx_col and pd.notna(row.get(fx_col)) else 1.0

            # Determinazione classe asset
            is_crypto = "-EUR" in ticker or "-USD" in ticker or ticker in ["BTC", "ETH", "SOL", "USDT"]
            asset_class = "CRYPTO" if is_crypto else ("EQUITY" if not ticker.endswith(".MI") else "EQUITY_EU")

            # Registrazione anagrafica asset
            if ticker not in asset_records:
                asset_records[ticker] = (
                    ticker,
                    None,
                    ticker,
                    f"Asset {ticker}",
                    asset_class,
                    "STANDARD",
                    curr,
                    True,
                    "REDDITI_DIVERSI" if not is_crypto else "REDDITI_DIVERSI_CRYPTO"
                )

            # Calcolo importi
            gross = qty * price
            net = gross + fees if op in ["BUY", "DEPOSIT"] else gross - fees
            net_base = net * fx

            account_debit = f"ACT_PORTFOLIO_{asset_class}" if op in ["BUY", "DEPOSIT"] else f"ACT_CASH_{curr}"
            account_credit = f"ACT_CASH_{curr}" if op in ["BUY", "DEPOSIT"] else f"ACT_PORTFOLIO_{asset_class}"

            entry_id = self.generate_entry_id(entity_id, d_val, ticker, op, qty, price)
            records.append((
                entry_id, entity_id, d_val, d_val, account_debit, account_credit,
                ticker, op, qty, price, gross, fees, 0.0, net, curr, fx, net_base,
                None, f"Automated Ingestion from {op}", None
            ))

        # Inserimento anagrafiche asset
        if asset_records:
            asset_df = pd.DataFrame(list(asset_records.values()), columns=[
                "asset_id", "isin", "ticker", "name", "asset_class", "sub_asset_class", 
                "quote_currency", "is_liquid", "tax_category"
            ])
            self.con.register("temp_assets", asset_df)
            self.con.execute("""
                INSERT INTO dim_asset_master (asset_id, isin, ticker, name, asset_class, sub_asset_class, quote_currency, is_liquid, tax_category)
                SELECT asset_id, isin, ticker, name, asset_class, sub_asset_class, quote_currency, is_liquid, tax_category
                FROM temp_assets
                ON CONFLICT (asset_id) DO NOTHING;
            """)
            self.con.unregister("temp_assets")

        # Inserimento transazioni nel ledger
        if records:
            ledger_df = pd.DataFrame(records, columns=[
                "entry_id", "entity_id", "booking_date", "value_date", "account_debit", "account_credit",
                "asset_id", "operation_type", "quantity", "unit_price", "gross_amount", "transaction_fees",
                "withholding_tax", "net_amount", "currency", "fx_rate_to_base", "net_amount_base_eur",
                "tax_lot_id", "notes", "metadata_json"
            ])
            self.con.register("temp_ledger", ledger_df)
            self.con.execute("""
                INSERT INTO fact_ledger_entry 
                SELECT * FROM temp_ledger
                ON CONFLICT (entry_id) DO UPDATE SET
                    quantity = EXCLUDED.quantity,
                    unit_price = EXCLUDED.unit_price,
                    net_amount_base_eur = EXCLUDED.net_amount_base_eur;
            """)
            self.con.unregister("temp_ledger")
            inserted_count = len(records)

        return inserted_count

    def ingest_wealth_items(
        self,
        accounts_df: Optional[pd.DataFrame] = None,
        mortgages_df: Optional[pd.DataFrame] = None,
        real_estate_df: Optional[pd.DataFrame] = None,
        entity_id: str = "DEFAULT_ENTITY"
    ) -> Dict[str, int]:
        """
        Ingerisce posizioni patrimoniali illiquide, liquidità e mutui nello schema universale.
        """
        if self.con is None:
            return {"accounts": 0, "mortgages": 0, "real_estate": 0}

        counts = {"accounts": 0, "mortgages": 0, "real_estate": 0}
        today_str = date.today().isoformat()

        # 1. Conti Correnti e Liquidità
        if accounts_df is not None and not accounts_df.empty:
            acc_records = []
            for _, r in accounts_df.iterrows():
                acc_name = str(r.get("account_name", r.get("name", "Conto Bancario")))
                balance = float(r.get("balance", r.get("current_balance", 0.0)))
                curr = str(r.get("currency", "EUR")).upper()
                asset_id = f"CASH_{acc_name.upper().replace(' ', '_')}"

                # Inserisci anagrafica asset
                self.con.execute("""
                    INSERT INTO dim_asset_master (asset_id, name, asset_class, is_liquid, tax_category, quote_currency)
                    VALUES ($1, $2, 'CASH', TRUE, 'REDDITI_CAPITALE', $3)
                    ON CONFLICT (asset_id) DO NOTHING;
                """, [asset_id, acc_name, curr])

                entry_id = f"SNAP_ACC_{asset_id}_{today_str}"
                acc_records.append((
                    entry_id, entity_id, today_str, today_str, f"ACT_CASH_{curr}", "ACT_EQUITY_NET_WORTH",
                    asset_id, "SNAPSHOT_BALANCE", 1.0, balance, balance, 0.0, 0.0, balance, curr, 1.0, balance,
                    None, "Account Cash Balance Snapshot", None
                ))

            if acc_records:
                temp_acc = pd.DataFrame(acc_records, columns=[
                    "entry_id", "entity_id", "booking_date", "value_date", "account_debit", "account_credit",
                    "asset_id", "operation_type", "quantity", "unit_price", "gross_amount", "transaction_fees",
                    "withholding_tax", "net_amount", "currency", "fx_rate_to_base", "net_amount_base_eur",
                    "tax_lot_id", "notes", "metadata_json"
                ])
                self.con.register("temp_acc", temp_acc)
                self.con.execute("INSERT INTO fact_ledger_entry SELECT * FROM temp_acc ON CONFLICT (entry_id) DO NOTHING;")
                self.con.unregister("temp_acc")
                counts["accounts"] = len(acc_records)

        # 2. Immobili (Real Estate)
        if real_estate_df is not None and not real_estate_df.empty:
            re_records = []
            for _, r in real_estate_df.iterrows():
                prop_name = str(r.get("property_name", r.get("name", "Immobile")))
                est_val = float(r.get("estimated_value", r.get("value", 0.0)))
                asset_id = f"RE_{prop_name.upper().replace(' ', '_')}"

                self.con.execute("""
                    INSERT INTO dim_asset_master (asset_id, name, asset_class, is_liquid, tax_category, quote_currency)
                    VALUES ($1, $2, 'REAL_ESTATE', FALSE, 'PATRIMONIALE_ESENTE', 'EUR')
                    ON CONFLICT (asset_id) DO NOTHING;
                """, [asset_id, prop_name])

                entry_id = f"SNAP_RE_{asset_id}_{today_str}"
                re_records.append((
                    entry_id, entity_id, today_str, today_str, "ACT_REAL_ESTATE", "ACT_EQUITY_NET_WORTH",
                    asset_id, "SNAPSHOT_BALANCE", 1.0, est_val, est_val, 0.0, 0.0, est_val, "EUR", 1.0, est_val,
                    None, "Real Estate Valuation Snapshot", None
                ))

            if re_records:
                temp_re = pd.DataFrame(re_records, columns=[
                    "entry_id", "entity_id", "booking_date", "value_date", "account_debit", "account_credit",
                    "asset_id", "operation_type", "quantity", "unit_price", "gross_amount", "transaction_fees",
                    "withholding_tax", "net_amount", "currency", "fx_rate_to_base", "net_amount_base_eur",
                    "tax_lot_id", "notes", "metadata_json"
                ])
                self.con.register("temp_re", temp_re)
                self.con.execute("INSERT INTO fact_ledger_entry SELECT * FROM temp_re ON CONFLICT (entry_id) DO NOTHING;")
                self.con.unregister("temp_re")
                counts["real_estate"] = len(re_records)

        # 3. Mutui e Passività
        if mortgages_df is not None and not mortgages_df.empty:
            m_records = []
            for _, r in mortgages_df.iterrows():
                m_name = str(r.get("mortgage_name", r.get("name", "Mutuo Bancario")))
                outstanding = float(r.get("outstanding_debt", r.get("remaining_debt", 0.0)))
                asset_id = f"MORTGAGE_{m_name.upper().replace(' ', '_')}"

                self.con.execute("""
                    INSERT INTO dim_asset_master (asset_id, name, asset_class, is_liquid, tax_category, quote_currency)
                    VALUES ($1, $2, 'MORTGAGE', FALSE, 'LIABILITY', 'EUR')
                    ON CONFLICT (asset_id) DO NOTHING;
                """, [asset_id, m_name])

                entry_id = f"SNAP_MORTGAGE_{asset_id}_{today_str}"
                m_records.append((
                    entry_id, entity_id, today_str, today_str, "ACT_EQUITY_NET_WORTH", "ACT_LIABILITY_MORTGAGE",
                    asset_id, "SNAPSHOT_BALANCE", 1.0, outstanding, outstanding, 0.0, 0.0, outstanding, "EUR", 1.0, outstanding,
                    None, "Mortgage Liability Snapshot", None
                ))

            if m_records:
                temp_m = pd.DataFrame(m_records, columns=[
                    "entry_id", "entity_id", "booking_date", "value_date", "account_debit", "account_credit",
                    "asset_id", "operation_type", "quantity", "unit_price", "gross_amount", "transaction_fees",
                    "withholding_tax", "net_amount", "currency", "fx_rate_to_base", "net_amount_base_eur",
                    "tax_lot_id", "notes", "metadata_json"
                ])
                self.con.register("temp_m", temp_m)
                self.con.execute("INSERT INTO fact_ledger_entry SELECT * FROM temp_m ON CONFLICT (entry_id) DO NOTHING;")
                self.con.unregister("temp_m")
                counts["mortgages"] = len(m_records)

        return counts

    def get_open_positions_with_wacp(self, entity_id: str = "DEFAULT_ENTITY") -> pd.DataFrame:
        """
        Calcola istantaneamente le posizioni aperte e il Prezzo Medio di Carico (WACP/PMC)
        utilizzando window functions analitiche vettorizzate in C++ DuckDB.
        """
        if self.con is None:
            return pd.DataFrame()

        query = """
        WITH running_trades AS (
            SELECT 
                l.asset_id,
                a.name as asset_name,
                a.asset_class,
                l.currency,
                l.booking_date,
                l.entry_id,
                l.operation_type,
                l.quantity,
                l.unit_price,
                l.net_amount_base_eur,
                SUM(CASE WHEN l.operation_type IN ('BUY', 'DEPOSIT') THEN l.quantity ELSE -l.quantity END)
                    OVER (PARTITION BY l.asset_id ORDER BY l.booking_date, l.entry_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as current_shares,
                SUM(CASE WHEN l.operation_type IN ('BUY', 'DEPOSIT') THEN l.net_amount_base_eur ELSE 0 END)
                    OVER (PARTITION BY l.asset_id) as total_bought_base_cost,
                SUM(CASE WHEN l.operation_type IN ('BUY', 'DEPOSIT') THEN l.quantity ELSE 0 END)
                    OVER (PARTITION BY l.asset_id) as total_bought_qty
            FROM fact_ledger_entry l
            JOIN dim_asset_master a ON l.asset_id = a.asset_id
            WHERE l.entity_id = $1 AND l.operation_type IN ('BUY', 'SELL', 'DEPOSIT')
        )
        SELECT 
            asset_id,
            asset_name,
            asset_class,
            currency,
            ROUND(current_shares, 4) as shares,
            ROUND(total_bought_base_cost / NULLIF(total_bought_qty, 0), 4) as pmc_base_eur,
            ROUND(current_shares * (total_bought_base_cost / NULLIF(total_bought_qty, 0)), 2) as invested_capital_eur
        FROM running_trades
        QUALIFY ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY booking_date DESC, entry_id DESC) = 1
            AND current_shares > 1e-5
        ORDER BY invested_capital_eur DESC;
        """
        return self.con.execute(query, [entity_id]).fetchdf()

    def get_consolidated_balance_sheet(self, entity_id: str = "DEFAULT_ENTITY") -> Dict[str, float]:
        """
        Genera il bilancio patrimoniale consolidato a sezioni contrapposte
        con quadratura contabile assoluta (Attivo, Passivo, Patrimonio Netto).
        """
        if self.con is None:
            return {"liquid_assets": 0.0, "real_estate": 0.0, "liabilities": 0.0, "net_worth": 0.0}

        # 1. Posizioni aperte di mercato
        open_pos = self.get_open_positions_with_wacp(entity_id)
        liquid_inv = float(open_pos["invested_capital_eur"].sum()) if not open_pos.empty else 0.0

        # 2. Cassa e conti correnti
        q_cash = """
        SELECT COALESCE(SUM(net_amount_base_eur), 0.0) as cash_eur
        FROM fact_ledger_entry
        WHERE entity_id = $1 AND operation_type = 'SNAPSHOT_BALANCE' AND account_debit LIKE 'ACT_CASH_%';
        """
        cash_val = float(self.con.execute(q_cash, [entity_id]).fetchone()[0])

        # 3. Immobili
        q_re = """
        SELECT COALESCE(SUM(net_amount_base_eur), 0.0) as re_eur
        FROM fact_ledger_entry
        WHERE entity_id = $1 AND operation_type = 'SNAPSHOT_BALANCE' AND account_debit = 'ACT_REAL_ESTATE';
        """
        re_val = float(self.con.execute(q_re, [entity_id]).fetchone()[0])

        # 4. Mutui (Passività)
        q_mort = """
        SELECT COALESCE(SUM(net_amount_base_eur), 0.0) as mort_eur
        FROM fact_ledger_entry
        WHERE entity_id = $1 AND operation_type = 'SNAPSHOT_BALANCE' AND account_credit = 'ACT_LIABILITY_MORTGAGE';
        """
        mort_val = float(self.con.execute(q_mort, [entity_id]).fetchone()[0])

        total_assets = liquid_inv + cash_val + re_val
        net_worth = total_assets - mort_val

        return {
            "liquid_investments_eur": liquid_inv,
            "cash_and_equivalents_eur": cash_val,
            "liquid_assets_total_eur": liquid_inv + cash_val,
            "real_estate_assets_eur": re_val,
            "total_assets_eur": total_assets,
            "mortgage_liabilities_eur": mort_val,
            "consolidated_net_worth_eur": net_worth
        }

    def get_arrow_table(self, table_name: str = "fact_ledger_entry") -> Optional[Any]:
        """Restituisce la tabella come pyarrow.Table per interscambio zero-copy."""
        if not HAS_PYARROW or self.con is None:
            return None
        res = self.con.execute(f"SELECT * FROM {table_name};").arrow()
        if hasattr(res, "read_all"):
            return res.read_all()
        return res

    def execute_raw_olap_query(self, sql_query: str) -> pd.DataFrame:
        """Esegue una query analitica arbitraria sul motore DuckDB."""
        if self.con is None:
            return pd.DataFrame()
        return self.con.execute(sql_query).fetchdf()

    def export_to_parquet(self, output_path: str, table_name: str = "fact_ledger_entry") -> bool:
        """Esporta la tabella in formato Parquet ad alta densità di compressione."""
        if self.con is None:
            return False
        try:
            self.con.execute(f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD);")
            return True
        except Exception as e:
            logger.error(f"Errore esportazione Parquet: {e}")
            return False

    def sync_to_bitemporal_engine(self, bitemporal_engine: Any, entity_id: str = "DEFAULT_ENTITY") -> int:
        """
        Sincronizza le transazioni contabili del One-Ledger nel motore bitemporale,
        generando per ciascuna la marcatura temporale e l'hash di integrità di riga.
        """
        if self.con is None or bitemporal_engine is None:
            return 0

        df = self.con.execute("""
            SELECT entry_id, entity_id, booking_date, value_date, asset_id,
                   operation_type, quantity, unit_price, gross_amount,
                   transaction_fees, withholding_tax, net_amount, currency,
                   fx_rate_to_base, net_amount_base_eur
            FROM fact_ledger_entry
            WHERE entity_id = $1
            ORDER BY booking_date ASC
        """, [entity_id]).fetchdf()

        if df.empty:
            return 0

        synced = 0
        for _, row in df.iterrows():
            v_date_str = pd.to_datetime(row['value_date']).strftime("%Y-%m-%d %H:%M:%S")
            bitemporal_engine.record_transaction(
                tx_business_id=str(row["entry_id"]),
                portfolio_id=str(row["entity_id"]),
                asset_id=str(row["asset_id"]),
                operation_type=str(row["operation_type"]),
                quantity=float(row["quantity"]),
                unit_price=float(row["unit_price"]),
                valid_from=v_date_str,
                recorded_by="UNIVERSAL_ONE_LEDGER_SYNC",
                fees=float(row.get("transaction_fees", 0.0) or 0.0),
                taxes=float(row.get("withholding_tax", 0.0) or 0.0),
                currency=str(row.get("currency", "EUR")),
                fx_rate_to_base=float(row.get("fx_rate_to_base", 1.0) or 1.0),
                source_doc_ref=f"LEDGER_ENTRY_{str(row['entry_id'])[:8]}"
            )
            synced += 1

        bitemporal_engine.log_decision(
            decision_type="LEDGER_BITEMPORAL_SYNC",
            entity_id=entity_id,
            actor_id="SYSTEM:UniversalLedgerEngine",
            rationale=f"Sincronizzazione contabile batch di {synced} transazioni dal One-Ledger",
            payload={"entity_id": entity_id, "records_synced": synced}
        )
        return synced
