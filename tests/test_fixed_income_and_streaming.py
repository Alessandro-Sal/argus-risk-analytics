# ============================================================
# tests/test_fixed_income_and_streaming.py
# Unit Tests for ARGUS Fixed Income Analytics & Real-Time Streaming Engine
# Phase 2: Bloomberg YAS/FI Parity, Z-Spread, CDS Default & Ring Buffer
# ============================================================

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from core.fixed_income import (
    compute_bond_cash_flows,
    compute_bond_price_from_ytm,
    compute_bond_ytm,
    compute_bond_analytics,
    compute_z_spread,
    compute_cds_implied_default_probability,
    INSTITUTIONAL_BOND_PRESETS
)
from core.streaming_engine import (
    MarketTick,
    TickRingBuffer,
    OrderBookLevel,
    OrderBookL2,
    generate_mock_streaming_ticks
)
from core.ui_utils import parse_terminal_command


def test_bond_cash_flows_and_pricing_at_par():
    """Verifica che un bond quotato alla pari abbia YTM esattamente uguale al coupon rate."""
    face_value = 100.0
    coupon_rate = 0.05  # 5%
    maturity_years = 5.0
    freq = 2  # Semestrale

    cfs = compute_bond_cash_flows(face_value, coupon_rate, maturity_years, freq)
    assert len(cfs) == 10
    assert cfs[0] == (0.5, 2.5)
    assert cfs[-1] == (5.0, 102.5)

    # Prezzo a YTM = 5% deve essere esattamente 100.0
    p = compute_bond_price_from_ytm(face_value, coupon_rate, maturity_years, ytm=0.05, coupon_frequency=freq)
    assert abs(p - 100.0) < 1e-4

    # Risoluzione YTM da prezzo 100.0
    ytm_solved = compute_bond_ytm(face_value, coupon_rate, maturity_years, market_price=100.0, coupon_frequency=freq)
    assert abs(ytm_solved - 0.05) < 1e-5


def test_bond_ytm_discount_and_premium():
    """Verifica la corretta risoluzione di YTM per bond a sconto e a premio."""
    face_value = 100.0
    coupon_rate = 0.03
    maturity_years = 10.0
    freq = 1  # Annuale

    # Bond a sconto (Prezzo 90.0) -> YTM > coupon_rate (3%)
    ytm_discount = compute_bond_ytm(face_value, coupon_rate, maturity_years, market_price=90.0, coupon_frequency=freq)
    assert ytm_discount > 0.03
    p_recalc_discount = compute_bond_price_from_ytm(face_value, coupon_rate, maturity_years, ytm_discount, freq)
    assert abs(p_recalc_discount - 90.0) < 1e-4

    # Bond a premio (Prezzo 110.0) -> YTM < coupon_rate (3%)
    ytm_premium = compute_bond_ytm(face_value, coupon_rate, maturity_years, market_price=110.0, coupon_frequency=freq)
    assert ytm_premium < 0.03
    p_recalc_premium = compute_bond_price_from_ytm(face_value, coupon_rate, maturity_years, ytm_premium, freq)
    assert abs(p_recalc_premium - 110.0) < 1e-4


def test_bond_analytics_duration_convexity_and_dv01():
    """Verifica le proprietà matematiche di Macaulay Duration, Modified Duration, Convexity e DV01."""
    face_value = 100.0
    coupon_rate = 0.04
    maturity_years = 10.0
    market_price = 101.50
    freq = 2

    res = compute_bond_analytics(face_value, coupon_rate, maturity_years, market_price, coupon_frequency=freq)
    
    assert "ytm_pct" in res
    assert "macaulay_duration_years" in res
    assert "modified_duration" in res
    assert "convexity" in res
    assert "dv01" in res
    assert "sensitivity_table" in res

    # 1. Macaulay Duration deve essere minore o uguale alla scadenza (D_mac <= 10)
    assert 0.0 < res["macaulay_duration_years"] <= maturity_years

    # 2. Modified Duration = Macaulay / (1 + YTM/m) < Macaulay Duration
    assert res["modified_duration"] < res["macaulay_duration_years"]

    # 3. Convessità deve essere rigorosamente positiva per plain vanilla bond
    assert res["convexity"] > 0.0

    # 4. DV01 = Modified Duration * P * 0.0001
    expected_dv01 = res["modified_duration"] * market_price * 0.0001
    assert abs(res["dv01"] - expected_dv01) < 1e-4

    # 5. Verifica tabella di sensibilità: dP con Convessità è sempre maggiore o uguale di dP con sola Duration
    df_sens = res["sensitivity_table"]
    assert len(df_sens) == 8
    for _, row in df_sens.iterrows():
        assert row["pct_change_duration_plus_convexity"] >= row["pct_change_duration_only"] - 1e-5


def test_z_spread_calculation():
    """Verifica la calibrazione dello Z-Spread su curva flat e benchmark."""
    face_value = 100.0
    coupon_rate = 0.04
    maturity_years = 5.0
    market_price = 98.0  # Bond sotto la pari

    # Curva spot costante al 3.0%
    flat_spot = lambda t: 0.030

    z_spread_bps = compute_z_spread(face_value, coupon_rate, maturity_years, market_price, spot_curve_fn_or_params=flat_spot, coupon_frequency=2)
    
    # Se il bond quota a 98.0 con cedola 4% e tasso base 3%, lo Z-spread deve essere positivo (> 100 bps)
    assert z_spread_bps > 100.0

    # Presets benchmark
    assert "IT10Y" in INSTITUTIONAL_BOND_PRESETS
    assert "DE10Y" in INSTITUTIONAL_BOND_PRESETS


def test_cds_implied_default_probability_curve():
    """Verifica la curva di probabilità di default implicita dai CDS."""
    cds_spread_bps = 150.0  # 150 bps
    recovery_rate = 0.40    # 40%

    res = compute_cds_implied_default_probability(cds_spread_bps, recovery_rate)
    
    assert res["cds_spread_bps"] == 150.0
    assert res["loss_given_default_pct"] == 60.0
    assert res["implied_hazard_rate_pct"] == pytest.approx(2.50, rel=1e-3)

    df_pd = res["default_probability_curve"]
    assert len(df_pd) > 5

    # Le probabilità cumulative di default devono essere comprese tra 0 e 100% e strettamente crescenti con la scadenza
    cum_pds = df_pd["cumulative_default_prob_pct"].tolist()
    assert cum_pds[0] > 0.0
    for i in range(1, len(cum_pds)):
        assert cum_pds[i] > cum_pds[i - 1]
        assert cum_pds[i] < 100.0


def test_streaming_ring_buffer_fifo_and_vwap():
    """Verifica il comportamento del RingBuffer circolare a capacità fissa O(1) e il calcolo del VWAP."""
    capacity = 10
    buf = TickRingBuffer(capacity=capacity, ticker="AAPL")

    # Inserisce 15 tick per testare l'eviction FIFO dei primi 5
    for i in range(15):
        tick = MarketTick(
            timestamp=datetime.now(timezone.utc),
            ticker="AAPL",
            price=100.0 + i,
            size=10.0,
            bid=99.95 + i,
            ask=100.05 + i,
            volume=10.0
        )
        buf.append(tick)

    df = buf.to_dataframe()
    assert len(df) == 10
    # L'elemento più vecchio deve essere il tick #5 (prezzo 105.0) e il più recente il tick #14 (prezzo 114.0)
    assert df["price"].iloc[0] == 105.0
    assert df["price"].iloc[-1] == 114.0

    # Calcolo VWAP: essendo pesi uguali (size=10), VWAP = media aritmetica dei prezzi (105..114) = 109.5
    vwap = buf.compute_vwap()
    assert abs(vwap - 109.5) < 1e-4

    stats = buf.get_summary_statistics()
    assert stats["count"] == 10
    assert stats["last_price"] == 114.0
    assert stats["min_price"] == 105.0
    assert stats["max_price"] == 114.0


def test_order_book_l2_microprice_and_imbalance():
    """Verifica il calcolo di Microprice e Book Imbalance su Order Book L2."""
    bids = [
        OrderBookLevel(price=100.00, size=500.0),
        OrderBookLevel(price=99.90, size=1000.0),
    ]
    asks = [
        OrderBookLevel(price=100.10, size=100.0),
        OrderBookLevel(price=100.20, size=800.0),
    ]
    book = OrderBookL2(ticker="MSFT", bids=bids, asks=asks)

    assert book.best_bid == 100.00
    assert book.best_ask == 100.10
    assert abs(book.spread - 0.10) < 1e-5
    assert abs(book.mid_price - 100.05) < 1e-5

    # Poiché il lato Bid ha molto più volume (500 vs 100), il Microprice deve essere sbilanciato verso l'Ask (> mid_price 100.05)
    microprice = book.compute_microprice()
    # Microprice = (100.00 * 100 + 100.10 * 500) / 600 = (10000 + 50050) / 600 = 60050 / 600 = 100.0833
    assert microprice > book.mid_price
    assert abs(microprice - 100.0833) < 1e-3

    # Book Imbalance: (1500 - 900) / 2400 = 600 / 2400 = +0.25 (Pressione rialzista)
    imbalance = book.compute_book_imbalance()
    assert abs(imbalance - 0.25) < 1e-4


def test_mock_streaming_ticks_generation():
    """Verifica il generatore di tick sintetici per simulazione e test."""
    ticks = generate_mock_streaming_ticks(ticker="NVDA", initial_price=120.0, num_ticks=30)
    assert len(ticks) == 30
    assert all(t.ticker == "NVDA" for t in ticks)
    assert all(t.bid <= t.ask for t in ticks)
    assert all(t.spread >= 0 for t in ticks)


def test_terminal_command_gateway_phase2_mnemonics():
    """Verifica che il parser riconosca i nuovi comandi YAS, FI, CDS, STREAM."""
    cmd_yas = parse_terminal_command("BTP YAS")
    assert cmd_yas is not None
    assert cmd_yas["mnemonic"] == "YAS"
    assert cmd_yas["ticker"] == "BTP"

    cmd_fi = parse_terminal_command("US10Y FI")
    assert cmd_fi is not None
    assert cmd_fi["mnemonic"] == "FI"
    assert cmd_fi["ticker"] == "US10Y"

    cmd_cds = parse_terminal_command("CDS")
    assert cmd_cds is not None
    assert cmd_cds["mnemonic"] == "CDS"

    cmd_stream = parse_terminal_command("STREAM")
    assert cmd_stream is not None
    assert cmd_stream["mnemonic"] == "STREAM"
