# ============================================================
# tests/test_property_fifo_accounting.py
# ARGUS — Property-Based Testing: FIFO Conservation Law
# Validates accounting invariants under random buy/sell executions and satoshi fractions
# ============================================================

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, settings, strategies as st
from core.risk_engine import _fifo_engine


@st.composite
def transaction_history_strategy(draw):
    """Genera una sequenza stocastica coerente di acquisti e vendite per un singolo asset."""
    n_ops = draw(st.integers(min_value=3, max_value=20))
    curr_qty = 0.0
    rows = []

    for i in range(n_ops):
        date_str = f"2025-01-{(i % 28) + 1:02d}"
        can_sell = curr_qty > 0.005
        tx_type = draw(st.sampled_from(["buy", "sell"])) if can_sell else "buy"

        price = draw(st.floats(min_value=1.0, max_value=400.0, allow_nan=False, allow_infinity=False))
        fee = draw(st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False))

        if tx_type == "buy":
            qty = draw(st.floats(min_value=0.01, max_value=50.0, allow_nan=False, allow_infinity=False))
            curr_qty += qty
        else:
            qty = draw(st.floats(min_value=0.005, max_value=curr_qty, allow_nan=False, allow_infinity=False))
            curr_qty -= qty

        rows.append({
            "tx_date": date_str,
            "tx_type": tx_type,
            "quantity": qty,
            "price": price,
            "fees": fee,
            "currency": "EUR"
        })

    return pd.DataFrame(rows)


@settings(max_examples=40, deadline=None)
@given(transaction_history_strategy())
def test_hypothesis_fifo_conservation_law(df_tx):
    """
    LEGGE DI CONSERVAZIONE CONTABILE FIFO:
    1. La quantità finale netta calcolata deve eguagliare sum(buy_qty) - sum(sell_qty).
    2. La quantità netta non può MAI essere negativa.
    3. Il PMC (Prezzo Medio di Carico) deve essere > 0 se qty_net > 0.
    """
    res = _fifo_engine(df_tx)

    expected_qty = float(df_tx[df_tx["tx_type"] == "buy"]["quantity"].sum() - df_tx[df_tx["tx_type"] == "sell"]["quantity"].sum())
    calc_qty = float(res["qty_net"])

    # Verifica congruenza delle quantità
    assert abs(calc_qty - expected_qty) < 1e-4, f"Discrepanza quantità: attesa {expected_qty}, calcolata {calc_qty}"
    assert calc_qty >= -1e-8, f"Quantità netta negativa: {calc_qty}"

    if calc_qty > 1e-4:
        assert res["avg_cost"] > 0.0, f"PMC non valido su posizione aperta: {res['avg_cost']}"
    else:
        assert res["avg_cost"] == 0.0
