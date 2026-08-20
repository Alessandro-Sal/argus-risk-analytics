"""
ARGUS — Risk Analytics & Quantitative Platform
Core Module: Crypto Tax Engine & Italian Tax Compliance
Legge di Bilancio n. 197/2022 (Art. 1 commi 126-147) & Circolare AdE n. 30/E/2023
Gestione Fiscale Cripto-Attività: Quadro RT (Sezione II-B), Quadro RW (Codice 21) & IVAFE (0,20%).
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CRYPTO_TAX_RATE = 0.26
CRYPTO_EXEMPTION_THRESHOLD = 2000.0  # Franchigia annuale di 2.000€
CRYPTO_IVAFE_RATE = 0.002  # Imposta sul valore delle cripto-attività (2 per mille annuo)
CRYPTO_RW_CODE = "21"  # Codice Quadro RW per Cripto-attività e valute virtuali


def is_crypto_asset(asset_class: str, ticker: str = "") -> bool:
    """Verifica se l'asset appartiene alla categoria Cripto-Attività."""
    ac_l = str(asset_class).lower().strip()
    t_u = str(ticker).upper().strip()

    if any(k in ac_l for k in ["crypto", "cripto", "token", "coin"]):
        return True

    crypto_patterns = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "AVAX", "LINK", "USDT", "USDC"]
    for cp in crypto_patterns:
        if t_u.startswith(cp) or t_u.endswith(f"-{cp}") or f"{cp}-" in t_u or t_u == cp:
            return True

    if t_u.endswith("-EUR") or t_u.endswith("-USD"):
        prefix = t_u.split("-")[0]
        if prefix in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "AVAX", "LINK", "MATIC", "LTC", "UNI"]:
            return True

    return False


def _get_crypto_transactions(results: Dict[str, Any], db_engine=None) -> pd.DataFrame:
    """Estrae e normalizza le transazioni relative esclusivamente alle cripto-attività."""
    df_tx = results.get("df_tx", pd.DataFrame())
    portfolio_id = results.get("portfolio_id")

    if (df_tx is None or df_tx.empty) and db_engine is not None and portfolio_id is not None:
        try:
            from sqlalchemy import text
            query = text("""
                SELECT t.tx_id, t.tx_date, t.tx_type, t.quantity, t.price, t.currency, a.ticker, a.asset_class
                FROM transactions t
                JOIN assets a ON t.asset_id = a.asset_id
                WHERE t.portfolio_id = :pid
                ORDER BY t.tx_date ASC
            """)
            with db_engine.connect() as conn:
                df_tx = pd.read_sql(query, conn, params={"pid": portfolio_id})
        except Exception:
            df_tx = pd.DataFrame()

    if df_tx is None or df_tx.empty:
        return pd.DataFrame()

    df_tx = df_tx.copy()
    if "asset_class" not in df_tx.columns:
        df_tx["asset_class"] = "Crypto"

    crypto_mask = df_tx.apply(lambda r: is_crypto_asset(r.get("asset_class", ""), r.get("ticker", "")), axis=1)
    df_crypto_tx = df_tx[crypto_mask].copy()

    if not df_crypto_tx.empty:
        df_crypto_tx["tx_date"] = pd.to_datetime(df_crypto_tx["tx_date"])
        df_crypto_tx["year"] = df_crypto_tx["tx_date"].dt.year

    return df_crypto_tx


def _calc_yearly_crypto_stats(df_crypto_tx: pd.DataFrame) -> Dict[int, Dict[str, float]]:
    """Elabora code FIFO per determinare plusvalenze e minusvalenze realizzate anno per anno."""
    yearly_crypto_stats: Dict[int, Dict[str, float]] = {}
    if df_crypto_tx.empty:
        return yearly_crypto_stats

    for _, grp in df_crypto_tx.groupby("ticker"):
        queue: List[List[float]] = []
        grp = grp.sort_values(["tx_date", "tx_id"] if "tx_id" in grp.columns else ["tx_date"])

        for _, row in grp.iterrows():
            txtype = str(row["tx_type"]).lower().strip()
            qty = float(row["quantity"])
            raw_price = float(row["price"])
            yr = int(row["year"])
            curr = str(row.get("currency", "EUR")).upper().strip()

            fx = 0.92 if curr == "USD" else (1.17 if curr == "GBP" else 1.0)
            price_eur = raw_price * fx

            if yr not in yearly_crypto_stats:
                yearly_crypto_stats[yr] = {"gains": 0.0, "losses": 0.0, "volume_sales": 0.0}

            if txtype == "buy":
                queue.append([qty, price_eur])
            elif txtype == "sell":
                qty_to_sell = qty
                yearly_crypto_stats[yr]["volume_sales"] += qty * price_eur

                while qty_to_sell > 1e-9 and queue:
                    lot_qty, lot_price = queue[0]
                    if lot_qty <= qty_to_sell + 1e-9:
                        pnl = lot_qty * (price_eur - lot_price)
                        qty_to_sell -= lot_qty
                        queue.pop(0)
                    else:
                        pnl = qty_to_sell * (price_eur - lot_price)
                        queue[0][0] -= qty_to_sell
                        qty_to_sell = 0.0

                    if pnl > 0:
                        yearly_crypto_stats[yr]["gains"] += pnl
                    else:
                        yearly_crypto_stats[yr]["losses"] += abs(pnl)

    return yearly_crypto_stats


def _build_crypto_rt_dataframe(
    yearly_crypto_stats: Dict[int, Dict[str, float]],
    tax_year: Optional[int]
) -> tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Genera la tabella Quadro RT con deduzione minusvalenze pregresse e franchigia 2.000€."""
    rt_rows = []
    crypto_buckets: List[Dict[str, Any]] = []
    years = sorted(yearly_crypto_stats.keys()) if yearly_crypto_stats else [tax_year or 2024]

    for yr in years:
        s = yearly_crypto_stats.get(yr, {"gains": 0.0, "losses": 0.0, "volume_sales": 0.0})
        gains = float(s["gains"])
        losses = float(s["losses"])
        net_raw = gains - losses

        prior_deducted = 0.0
        taxable_base = 0.0
        threshold_applied = False

        if net_raw > 0:
            excess_gain = net_raw
            for b in crypto_buckets:
                if b["residual"] > 1e-6 and yr <= b["expiry_year"]:
                    offset = min(excess_gain, b["residual"])
                    b["compensated"] += offset
                    b["residual"] -= offset
                    prior_deducted += offset
                    excess_gain -= offset
                    if excess_gain <= 1e-6:
                        break

            if excess_gain <= CRYPTO_EXEMPTION_THRESHOLD:
                taxable_base = 0.0
                threshold_applied = True
            else:
                taxable_base = excess_gain
        else:
            net_loss = abs(net_raw)
            if net_loss > 1e-2:
                crypto_buckets.append({
                    "origin_year": yr,
                    "expiry_year": yr + 4,
                    "initial": round(net_loss, 2),
                    "compensated": 0.0,
                    "residual": round(net_loss, 2)
                })

        tax_due = taxable_base * CRYPTO_TAX_RATE
        active_zainetto = sum(b["residual"] for b in crypto_buckets if yr <= b["expiry_year"])

        rt_rows.append({
            "year": yr,
            "realized_gains_eur": round(gains, 2),
            "realized_losses_eur": round(losses, 2),
            "net_pnl_eur": round(net_raw, 2),
            "prior_crypto_minus_deducted_eur": round(prior_deducted, 2),
            "taxable_base_rt_eur": round(taxable_base, 2),
            "tax_due_rt_eur": round(tax_due, 2),
            "threshold_exempt": bool(threshold_applied),
            "crypto_zainetto_residual_eur": round(active_zainetto, 2)
        })

    df_rt = pd.DataFrame(rt_rows)
    if tax_year is not None and not df_rt.empty:
        df_rt_filtered = df_rt[df_rt["year"] == tax_year]
        df_rt_view = df_rt_filtered if not df_rt_filtered.empty else df_rt
    else:
        df_rt_view = df_rt

    return df_rt_view, crypto_buckets


def _build_crypto_rw_dataframe(df_crypto_pos: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, float]]:
    """Costruisce il prospetto Quadro RW e calcola l'IVAFE Cripto (0,20%)."""
    rw_rows = []
    tot_val_initial, tot_val_final, tot_ivafe = 0.0, 0.0, 0.0

    if not df_crypto_pos.empty:
        for _, pos_row in df_crypto_pos.iterrows():
            ticker = str(pos_row.get("ticker", "CRYPTO"))
            qty = float(pos_row.get("qty_net", pos_row.get("quantity", 0.0)) or 0.0)
            cost_basis = float(pos_row.get("cost_basis", pos_row.get("book_value", 0.0)) or 0.0)
            cur_val = float(pos_row.get("current_value", pos_row.get("market_value", 0.0)) or 0.0)
            pnl_unreal = float(pos_row.get("pnl_unrealized", 0.0) or 0.0)

            if cur_val <= 0 and cost_basis <= 0:
                continue

            val_initial = cost_basis if cost_basis > 0 else cur_val
            val_final = cur_val if cur_val > 0 else cost_basis
            val_max = max(val_initial, val_final, val_initial + max(0.0, pnl_unreal))
            days_held = 365

            ivafe_item = val_final * CRYPTO_IVAFE_RATE * (days_held / 365.0)

            tot_val_initial += val_initial
            tot_val_final += val_final
            tot_ivafe += ivafe_item

            rw_rows.append({
                "quadro": "RW",
                "codice_investimento": CRYPTO_RW_CODE,
                "descrizione_bene": f"Cripto-attività ({ticker})",
                "ticker": ticker,
                "quantita_detenuta": qty,
                "valore_iniziale_eur": round(val_initial, 2),
                "valore_finale_eur": round(val_final, 2),
                "valore_massimo_eur": round(val_max, 2),
                "giorni_detenzione": days_held,
                "quota_possesso_pct": 100.0,
                "imposta_valore_ivafe_eur": round(ivafe_item, 2)
            })

    return pd.DataFrame(rw_rows), {
        "tot_val_initial": tot_val_initial,
        "tot_val_final": tot_val_final,
        "tot_ivafe": tot_ivafe
    }


def _build_crypto_zainetto_dataframe(crypto_buckets: List[Dict[str, Any]], cur_year: int) -> pd.DataFrame:
    """Costruisce la timeline dei bucket di minusvalenze cripto."""
    zainetto_crypto_rows = []
    for b in crypto_buckets:
        years_left = max(0, b["expiry_year"] - cur_year)
        status = "✅ Totalmente Compensato" if b["residual"] < 1e-4 else (
            "❌ Prescritto / Scaduto" if cur_year > b["expiry_year"] else f"⏳ Attivo ({years_left}a rimanenti)"
        )
        zainetto_crypto_rows.append({
            "origin_year": b["origin_year"],
            "expiry_year": b["expiry_year"],
            "initial_minus_eur": b["initial"],
            "compensated_eur": round(b["compensated"], 2),
            "residual_active_eur": round(b["residual"], 2),
            "years_to_expiry": years_left,
            "status": status
        })
    return pd.DataFrame(zainetto_crypto_rows)


def compute_crypto_tax_report(
    results: Dict[str, Any],
    db_engine=None,
    tax_year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Genera il prospetto fiscale integrato per Cripto-Attività conforme alla L. 197/2022:
    1. Quadro RT (Sezione II-B): Plusvalenze, Minusvalenze, Franchigia 2.000€ e Imposta Sostitutiva 26%.
    2. Zainetto Fiscale Cripto: Bucket di minusvalenze separate con validità 4 anni solari.
    3. Quadro RW: Monitoraggio fiscale attività estere / self-custody (Codice 21) e calcolo IVAFE (0,20%).
    """
    pos = results.get("positions", pd.DataFrame())
    df_crypto_pos = pd.DataFrame()
    if isinstance(pos, pd.DataFrame) and not pos.empty:
        crypto_mask = pos.apply(lambda r: is_crypto_asset(r.get("asset_class", ""), r.get("ticker", "")), axis=1)
        df_crypto_pos = pos[crypto_mask].copy()

    df_crypto_tx = _get_crypto_transactions(results, db_engine)
    yearly_crypto_stats = _calc_yearly_crypto_stats(df_crypto_tx)

    df_rt, crypto_buckets = _build_crypto_rt_dataframe(yearly_crypto_stats, tax_year)
    df_rw, rw_totals = _build_crypto_rw_dataframe(df_crypto_pos)
    df_crypto_zainetto = _build_crypto_zainetto_dataframe(crypto_buckets, tax_year or 2024)

    tot_gains = float(df_rt["realized_gains_eur"].sum()) if not df_rt.empty else 0.0
    tot_losses = float(df_rt["realized_losses_eur"].sum()) if not df_rt.empty else 0.0
    tot_tax_rt = float(df_rt["tax_due_rt_eur"].sum()) if not df_rt.empty else 0.0
    tot_crypto_credit = float(df_crypto_zainetto["residual_active_eur"].sum()) if not df_crypto_zainetto.empty else 0.0

    summary = {
        "total_crypto_portfolio_val_eur": round(rw_totals["tot_val_final"], 2),
        "total_realized_gains_eur": round(tot_gains, 2),
        "total_realized_losses_eur": round(tot_losses, 2),
        "total_tax_due_rt_eur": round(tot_tax_rt, 2),
        "total_ivafe_rw_eur": round(rw_totals["tot_ivafe"], 2),
        "total_crypto_tax_burden_eur": round(tot_tax_rt + rw_totals["tot_ivafe"], 2),
        "active_crypto_zainetto_eur": round(tot_crypto_credit, 2),
        "has_crypto_positions": not df_crypto_pos.empty or not df_crypto_tx.empty
    }

    return {
        "summary": summary,
        "df_rt": df_rt,
        "df_rw": df_rw,
        "df_crypto_zainetto": df_crypto_zainetto,
        "df_crypto_positions": df_crypto_pos
    }
