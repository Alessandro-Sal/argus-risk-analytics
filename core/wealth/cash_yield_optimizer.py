"""
ARGUS Wealth - Cash Yield Optimizer & Liquidity Opportunity Cost Engine
=======================================================================
Institutional engine for cash management and liquidity optimization:
- Analysis of idle cash balances on checking, savings and brokerage accounts
- Determination of Operational Cash Buffer vs Emergency Buffer vs Excess Liquidity
- Opportunity Cost calculation vs BCE / €STR risk-free benchmark
- Tax-adjusted yield comparison (BOT / BTP at 12.5% White List vs 26% Bank Deposits/ETFs)
- Execution strategy for laddered government bills (BOT) and overnight liquidity (XEON)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sqlalchemy import Engine

from core.wealth.wealth_db import get_cashflow_records, get_wealth_accounts
from core.wealth.wealth_models import AccountType

logger = logging.getLogger(__name__)

# Institutional Market Benchmarks (calibrated Q4 2026 EUR reference)
BENCHMARKS = {
    "bce_deposit_rate": {
        "name": "Tasso Deposito BCE (€STR Base)",
        "gross_yield_pct": 3.25,
        "tax_rate_pct": 0.0,
        "net_yield_pct": 3.25,
        "type": "Central Bank Policy Rate",
        "description": "Tasso ufficiale di deposito presso la Banca Centrale Europea.",
    },
    "bot_12m": {
        "name": "BOT 12 Mesi (Buoni Ordinari del Tesoro)",
        "ticker_ref": "BOT 12M",
        "gross_yield_pct": 3.20,
        "tax_rate_pct": 12.5,  # Aliquota agevolata White List Titoli di Stato
        "net_yield_pct": 2.80,
        "type": "Governativo Zero Coupon",
        "stamp_duty_pct": 0.0,
        "risk_grade": "AAA/BTP Sovereign (Rischio Minimo)",
        "description": "Titolo di Stato italiano zero coupon a 12 mesi con imposta agevolata al 12,5%.",
    },
    "btp_short_2y": {
        "name": "BTP Short-Term 18-24 Mesi",
        "ticker_ref": "BTP Short",
        "gross_yield_pct": 3.10,
        "tax_rate_pct": 12.5,
        "net_yield_pct": 2.71,
        "type": "Governativo Cedola Fissa",
        "stamp_duty_pct": 0.0,
        "risk_grade": "BTP Sovereign",
        "description": "Obbligazione governativa a cedola fissa semestrale tassata al 12,5%.",
    },
    "etf_monetary_xeon": {
        "name": "ETF Monetario Overnight (XEON / SMART)",
        "ticker_ref": "XEON.DE / SMART.MI",
        "gross_yield_pct": 3.33,
        "tax_rate_pct": 18.0,  # Tassazione mista White List su collaterale sovrano
        "net_yield_pct": 2.73,
        "type": "ETF Liquidità a Vista",
        "stamp_duty_pct": 0.20,
        "risk_grade": "Overnight Swap UCITS",
        "description": "Replica l'indice €STR + 8.5 bps con liquidità istantanea T+2 sul conto broker.",
    },
    "deposit_account_12m": {
        "name": "Conto Deposito Vincolato 12 Mesi",
        "ticker_ref": "Conto Deposito",
        "gross_yield_pct": 3.40,
        "tax_rate_pct": 26.0,  # Tassazione ordinaria bancaria
        "stamp_duty_pct": 0.20,
        "net_yield_pct": 2.32,  # 3.40% * (1-0.26) - 0.20% bollo = 2.316%
        "type": "Deposito Bancario Tutelato FITD",
        "risk_grade": "Fondo Interbancario Tutela Depositi (€100k)",
        "description": "Vincolo bancario a 12 mesi con tassazione ordinaria al 26% e bollo 0,20%.",
    },
    "current_account_idle": {
        "name": "Conto Corrente Tipico a Vista",
        "ticker_ref": "C/C Bancario",
        "gross_yield_pct": 0.05,
        "tax_rate_pct": 26.0,
        "stamp_duty_pct": 0.0,
        "net_yield_pct": 0.037,
        "type": "Liquidità Cassa Operativa",
        "risk_grade": "Bancario Libero",
        "description": "Conto corrente bancario convenzionale con remunerazione vicina allo zero.",
    },
}


def compute_cash_yield_optimization(
    engine: Engine,
    portfolio_id: Optional[int] = None,
    emergency_months: int = 6,
    custom_monthly_expenses: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Analizza i saldi di cassa di tutti i conti del profilo e calcola il piano ottimale
    di allocazione della liquidità per azzerare il costo opportunità rispetto ai rendimenti risk-free.
    """
    df_acc = get_wealth_accounts(engine, portfolio_id=portfolio_id)

    # Filtra i conti di liquidità e contanti
    liquid_types = [
        AccountType.CHECKING.value,
        AccountType.SAVINGS.value,
        AccountType.EMERGENCY_FUND.value,
        AccountType.BROKERAGE_CASH.value,
        "brokerage",
        "trading",
        "cash",
    ]

    accounts_breakdown = []
    tot_liquid_cash = 0.0
    tot_estimated_current_interest = 0.0

    if not df_acc.empty:
        df_liq = df_acc[df_acc["account_type"].isin(liquid_types)].copy()
        for _, row in df_liq.iterrows():
            bal = float(row.get("balance", 0.0) or 0.0)
            if bal <= 0:
                continue
            curr = str(row.get("currency", "EUR")).upper()
            from core.wealth.personal_balance_sheet import get_fx_rate_to_eur
            bal_eur = bal * get_fx_rate_to_eur(curr)
            tot_liquid_cash += bal_eur

            # Stima interesse attuale (default 0.05% se non specificato)
            int_rate_gross = float(row.get("interest_rate", 0.0) or 0.05)
            net_rate = int_rate_gross * (1.0 - 0.26)
            annual_earn = bal_eur * (net_rate / 100.0)
            tot_estimated_current_interest += annual_earn

            accounts_breakdown.append({
                "account_id": row.get("account_id"),
                "name": row.get("name") or row.get("account_name") or "Conto",
                "institution": row.get("institution") or "Banca",
                "account_type": row.get("account_type"),
                "balance_eur": round(bal_eur, 2),
                "interest_rate_gross": int_rate_gross,
                "annual_net_earning_eur": round(annual_earn, 2),
            })

    # Calcolo spese mensili medie
    monthly_expenses = 2000.0
    if custom_monthly_expenses is not None and custom_monthly_expenses > 0:
        monthly_expenses = float(custom_monthly_expenses)
    else:
        df_cf = get_cashflow_records(engine, portfolio_id=portfolio_id)
        if df_cf is not None and not df_cf.empty:
            df_cf_copy = df_cf.copy()
            df_cf_copy["tx_date"] = pd.to_datetime(df_cf_copy["tx_date"], errors="coerce")
            df_out = df_cf_copy[df_cf_copy["direction"] == "outflow"].dropna(subset=["tx_date"])
            if not df_out.empty:
                # Escludi trasferimenti/giroconti
                if "category" in df_out.columns:
                    df_out = df_out[~df_out["category"].astype(str).str.lower().str.contains("giroconto|transfer", na=False)]
                tot_out = float(df_out["amount"].sum())
                n_months = max(1.0, (df_out["tx_date"].max() - df_out["tx_date"].min()).days / 30.4375)
                n_months = max(1.0, min(12.0, n_months))
                calc_exp = tot_out / n_months
                if 500.0 <= calc_exp <= 50000.0:
                    monthly_expenses = round(calc_exp, 2)

    # ── DETERMINAZIONE DEI TRE SECCHI DELLA LIQUIDITÀ ──────────────
    # 1. Cassa Operativa Spese Correnti: 2 mesi di uscite (su C/C principale a vista)
    operational_cash_needed = round(monthly_expenses * 2.0, 2)
    operational_allocated = min(tot_liquid_cash, operational_cash_needed)

    # 2. Cuscinetto Emergenza a Rendimento Istantaneo: Mesi di emergenza (es. 4 mesi) su ETF monetario / Deposito libero
    emergency_target = round(monthly_expenses * max(1, emergency_months - 2), 2)
    rem_after_op = max(0.0, tot_liquid_cash - operational_allocated)
    emergency_allocated = min(rem_after_op, emergency_target)

    # 3. Liquidità Inerte / Excess Cash: eccedenza investibile a tasso garantito (BOT / BTP Short)
    excess_cash_allocated = max(0.0, rem_after_op - emergency_allocated)

    # ── CALCOLO RENDIMENTO OTTIMIZZATO & COSTO OPPORTUNITÀ ────────
    rate_bot = BENCHMARKS["bot_12m"]["net_yield_pct"] / 100.0
    rate_xeon = BENCHMARKS["etf_monetary_xeon"]["net_yield_pct"] / 100.0
    rate_op = BENCHMARKS["current_account_idle"]["net_yield_pct"] / 100.0

    annual_op_earn = operational_allocated * rate_op
    annual_em_earn = emergency_allocated * rate_xeon
    annual_ex_earn = excess_cash_allocated * rate_bot

    tot_optimized_annual_interest = round(annual_op_earn + annual_em_earn + annual_ex_earn, 2)
    annual_opportunity_cost = max(0.0, round(tot_optimized_annual_interest - tot_estimated_current_interest, 2))

    # Proiezione a 3 e 5 anni del mancato guadagno (compounded)
    five_year_loss = round(annual_opportunity_cost * 5.25, 2)

    # Runway attuale di sopravvivenza
    runway_months = round(tot_liquid_cash / monthly_expenses, 1) if monthly_expenses > 0 else 99.0

    # ── PIANO DI ALLOCAZIONE CONSIGLIATO ─────────────────────────
    recommendations = [
        {
            "tranche": "1. Cassa Operativa (0-2 Mesi)",
            "amount_eur": operational_allocated,
            "share_pct": round(operational_allocated / tot_liquid_cash * 100.0, 1) if tot_liquid_cash > 0 else 0.0,
            "instrument": "Conto Corrente Principale (Cassa a Vista)",
            "gross_yield": "0.05%",
            "net_yield": "0.04%",
            "tax_regime": "Ordinario 26%",
            "liquidity_term": "Immediata (Bancomat / Bonifici)",
            "action": "Mantieni sul conto corrente operativo per le spese vive mensili.",
        },
        {
            "tranche": f"2. Fondo Emergenza ({emergency_months} Mesi)",
            "amount_eur": emergency_allocated,
            "share_pct": round(emergency_allocated / tot_liquid_cash * 100.0, 1) if tot_liquid_cash > 0 else 0.0,
            "instrument": "ETF Monetario Overnight (XEON.DE / SMART.MI)",
            "gross_yield": f"{BENCHMARKS['etf_monetary_xeon']['gross_yield_pct']:.2f}%",
            "net_yield": f"{BENCHMARKS['etf_monetary_xeon']['net_yield_pct']:.2f}%",
            "tax_regime": "Misto White List (~18%)",
            "liquidity_term": "Istantanea T+2 (Vendibile in qualsiasi giorno)",
            "action": "Investi su XEON via broker: rendimento giornaliero legato all'€STR senza vincoli di durata.",
        },
        {
            "tranche": "3. Liquidità Inerte / Excess Cash",
            "amount_eur": excess_cash_allocated,
            "share_pct": round(excess_cash_allocated / tot_liquid_cash * 100.0, 1) if tot_liquid_cash > 0 else 0.0,
            "instrument": "BOT 12 Mesi / Buoni Ordinari del Tesoro",
            "gross_yield": f"{BENCHMARKS['bot_12m']['gross_yield_pct']:.2f}%",
            "net_yield": f"{BENCHMARKS['bot_12m']['net_yield_pct']:.2f}%",
            "tax_regime": "White List Agevolata 12,5%",
            "liquidity_term": "Scadenza a 6-12 Mesi",
            "action": "Acquista BOT a 12 mesi all'asta o sul MOT per bloccare il rendimento netto al 2,80% al riparo dal calo tassi.",
        },
    ]

    return {
        "total_liquid_cash_eur": round(tot_liquid_cash, 2),
        "monthly_expenses_eur": round(monthly_expenses, 2),
        "runway_months": runway_months,
        "current_annual_interest_eur": round(tot_estimated_current_interest, 2),
        "optimized_annual_interest_eur": tot_optimized_annual_interest,
        "annual_opportunity_cost_eur": annual_opportunity_cost,
        "five_year_projected_loss_eur": five_year_loss,
        "benchmarks": BENCHMARKS,
        "recommendations": recommendations,
        "accounts_breakdown": accounts_breakdown,
        "tranches": {
            "operational": operational_allocated,
            "emergency": emergency_allocated,
            "excess": excess_cash_allocated,
        },
    }
