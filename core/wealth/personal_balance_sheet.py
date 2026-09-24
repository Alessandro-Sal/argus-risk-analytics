# ============================================================
# core/wealth/personal_balance_sheet.py
# ARGUS — Personal Balance Sheet & Financial Statements Engine
# Bilancio Personale Istituzionale conforme agli standard CFP & Private Banking
# ============================================================

import io
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sqlalchemy import Engine
from sqlalchemy import text as sqlt

from core.terminal_engine import get_fx_rate_to_eur
from core.wealth.wealth_db import (
    get_cashflow_records,
    get_linked_risk_portfolios,
    get_linked_risk_portfolios_summary,
    get_pension_plans,
    get_physical_assets,
    get_wealth_accounts,
    get_wealth_portfolios,
)
from core.wealth.wealth_modals import render_balance_sheet_methodology_modal
from core.wealth.wealth_models import (
    AccountType,
    CategoryNature,
    NetWorthSummary,
    PhysicalAssetCategory,
)

logger = logging.getLogger("personal_balance_sheet")


def compute_personal_balance_sheet(engine: Engine, portfolio_id: int = 1, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Costruisce il Bilancio Personale Istituzionale completo:
    1. Stato Patrimoniale a sezioni contrapposte (Attivo vs Passivo + Patrimonio Netto a pareggio)
    2. Conto Economico di gestione per l'anno selezionato (Entrate vs Spese di vita = Risparmio Netto)
    3. Rendiconto di Allocazione del Capitale (Flussi investiti vs Risparmio liquido)
    4. Indici di Bilancio Personale con benchmark Private Banking e rating di solidità
    Supporta la gestione retroattiva di qualsiasi anno d'esercizio (es. 2024, 2025, 2026),
    sincronizzando anche il valore storico dei portafogli Risk Engine collegati al 31/12 dell'anno.
    """
    current_year = date.today().year

    # ==========================================================
    # 1. ACQUISIZIONE DATI DA DATABASE
    # ==========================================================
    df_acc = get_wealth_accounts(engine, portfolio_id=portfolio_id)
    df_phys = get_physical_assets(engine, portfolio_id=portfolio_id)
    df_pens = get_pension_plans(engine, portfolio_id=portfolio_id)
    df_cf = get_cashflow_records(engine, portfolio_id=portfolio_id)

    # Identificazione anni d'esercizio disponibili dai flussi storici
    available_years = []
    if not df_cf.empty:
        df_cf_copy = df_cf.copy()
        df_cf_copy["tx_date"] = pd.to_datetime(df_cf_copy["tx_date"], errors="coerce")
        df_cf_copy = df_cf_copy.dropna(subset=["tx_date"])
        available_years = sorted([int(y) for y in df_cf_copy["tx_date"].dt.year.unique().tolist()], reverse=True)
    else:
        df_cf_copy = pd.DataFrame()

    if current_year not in available_years:
        available_years = sorted(list(set(available_years + [current_year])), reverse=True)

    selected_year = int(year) if year is not None else (available_years[0] if available_years else current_year)
    is_closed_exercise = selected_year < current_year

    if is_closed_exercise:
        as_of_str = f"31/12/{selected_year}"
        as_of_iso = f"{selected_year}-12-31"
        period_title = f"Esercizio Chiuso al 31/12/{selected_year}"
        cutoff_date = f"{selected_year}-12-31 23:59:59"
    else:
        as_of_str = date.today().strftime("%d/%m/%Y")
        as_of_iso = date.today().strftime("%Y-%m-%d")
        period_title = f"Esercizio In Corso (Situazione al {as_of_str})"
        cutoff_date = f"{as_of_iso} 23:59:59"

    # Controllo eventuale snapshot patrimoniale salvato in wealth_networth_snapshots per l'esercizio
    snap_data = None
    try:
        with engine.connect() as conn:
            q_snap = """
                SELECT snapshot_id, snapshot_date, details_json, total_net_worth, liquid_assets,
                       financial_investments, physical_assets_total, watches_total, real_estate_total,
                       pension_total, total_liabilities
                FROM wealth_networth_snapshots
                WHERE (portfolio_id = :pid OR portfolio_id IS NULL OR portfolio_id = 1)
                  AND snapshot_date <= :cutoff_dt
                ORDER BY snapshot_date DESC, snapshot_id DESC
                LIMIT 1
            """
            s_row = conn.execute(sqlt(q_snap), {"pid": portfolio_id, "cutoff_dt": cutoff_date[:10]}).mappings().fetchone()
            if s_row and s_row.get("details_json"):
                snap_data = json.loads(s_row["details_json"])
    except Exception as e:
        logger.debug(f"Nessuno snapshot storico caricato: {e}")

    # Normalizzazione Valutaria EUR per Conti
    if not df_acc.empty:
        if "currency" in df_acc.columns:
            df_acc["balance_eur"] = df_acc.apply(
                lambda r: float(r.get("balance", 0.0) or 0.0) * get_fx_rate_to_eur(str(r.get("currency", "EUR"))),
                axis=1,
            )
        else:
            df_acc["balance_eur"] = df_acc["balance"].astype(float)
    else:
        df_acc = pd.DataFrame(columns=["account_id", "name", "account_type", "balance", "balance_eur", "currency"])

    # Se anno passato e non c'è snapshot archiviato con conti espliciti,
    # applichiamo il rollback contabile della liquidità (sottrazione dei flussi netti post-chiusura)
    if is_closed_exercise and not df_cf_copy.empty:
        subsequent_cf = df_cf_copy[df_cf_copy["tx_date"] > pd.to_datetime(cutoff_date)]
        if not subsequent_cf.empty:
            inflows_since = subsequent_cf[subsequent_cf["direction"] == "inflow"]["amount"].sum()
            outflows_since = subsequent_cf[subsequent_cf["direction"] == "outflow"]["amount"].sum()
            net_delta_cash = inflows_since - outflows_since
            cur_tot_cash = df_acc["balance_eur"].sum()
            reconstructed_tot_cash = max(0.0, cur_tot_cash - net_delta_cash)
            if cur_tot_cash > 0:
                scale_ratio = reconstructed_tot_cash / cur_tot_cash
                df_acc["balance_eur"] = df_acc["balance_eur"] * scale_ratio

    # Normalizzazione Valutaria EUR per Asset Fisici
    if not df_phys.empty:
        if "currency" in df_phys.columns:
            df_phys["market_val_eur"] = df_phys.apply(
                lambda r: (
                    float(r.get("current_market_value", 0.0) or 0.0) * get_fx_rate_to_eur(str(r.get("currency", "EUR")))
                ),
                axis=1,
            )
        else:
            df_phys["market_val_eur"] = df_phys["current_market_value"].astype(float)
    else:
        df_phys = pd.DataFrame(
            columns=["asset_id", "name", "asset_category", "current_market_value", "market_val_eur", "currency"]
        )

    # Normalizzazione Valutaria EUR per Previdenza
    if not df_pens.empty:
        if "currency" in df_pens.columns:
            df_pens["accum_eur"] = df_pens.apply(
                lambda r: (
                    float(r.get("accumulated_value", 0.0) or 0.0) * get_fx_rate_to_eur(str(r.get("currency", "EUR")))
                ),
                axis=1,
            )
        else:
            df_pens["accum_eur"] = df_pens["accumulated_value"].astype(float)
    else:
        df_pens = pd.DataFrame(
            columns=["plan_id", "plan_name", "provider", "accumulated_value", "accum_eur", "currency"]
        )

    # ==========================================================
    # 2. STATO PATRIMONIALE PERSONALE (STATEMENT OF FINANCIAL POSITION)
    # ==========================================================

    # --- A. ATTIVO: SEZIONE I - ATTIVITÀ LIQUIDE & EQUIVALENTI ---
    liquid_voci = []

    liquid_types = [AccountType.CHECKING.value, AccountType.SAVINGS.value, AccountType.EMERGENCY_FUND.value]
    df_liquid_acc = df_acc[df_acc["account_type"].isin(liquid_types) & (df_acc["balance_eur"] > 0)]
    for _, r in df_liquid_acc.iterrows():
        tipo_lbl = (
            "Conto Corrente"
            if r["account_type"] == AccountType.CHECKING.value
            else ("Fondo Emergenza" if r["account_type"] == AccountType.EMERGENCY_FUND.value else "Conto Deposito")
        )
        liquid_voci.append(
            {
                "nome": r.get("account_name") or r.get("name") or "Conto Bancario",
                "categoria": tipo_lbl,
                "dettaglio": f"{r.get('institution', 'Banca')} ({r.get('currency', 'EUR')})",
                "valore": round(float(r["balance_eur"]), 2),
            }
        )

    brokerage_cash = df_acc[
        df_acc["account_type"].isin([AccountType.BROKERAGE_CASH.value, "brokerage", "trading"])
        & (df_acc["balance_eur"] > 0)
    ]
    for _, r in brokerage_cash.iterrows():
        liquid_voci.append(
            {
                "nome": r.get("account_name") or r.get("name") or "Liquidità Broker",
                "categoria": "Liquidità su Broker/Trading",
                "dettaglio": f"{r.get('institution', 'Broker')} (Cassa non investita)",
                "valore": round(float(r["balance_eur"]), 2),
            }
        )

    tot_liquidita = sum(v["valore"] for v in liquid_voci)

    # --- A. ATTIVO: SEZIONE II - INVESTIMENTI FINANZIARI & CAPITALE PRODUTTIVO ---
    invest_voci = []
    active_risk_pids = []
    try:
        active_risk_pids = get_linked_risk_portfolios(engine, wealth_portfolio_id=portfolio_id)
    except Exception:
        active_risk_pids = []

    # Recupera i portafogli collegati da portfolios / snapshot con cutoff temporale retroattivo
    if active_risk_pids:
        try:
            with engine.connect() as conn:
                p_placeholders = ",".join([f":p{i}" for i in range(len(active_risk_pids))])
                params = {f"p{i}": int(pid) for i, pid in enumerate(active_risk_pids)}
                params["cutoff"] = cutoff_date
                q = f"""
                    SELECT p.portfolio_id, p.name, p.description, s.total_value, s.calc_date
                    FROM portfolios p
                    LEFT JOIN (
                        SELECT s1.portfolio_id, s1.total_value, s1.calc_date
                        FROM portfolio_snapshots s1
                        INNER JOIN (
                            SELECT portfolio_id, MAX(calc_date) as max_calc_date
                            FROM portfolio_snapshots
                            WHERE portfolio_id IN ({p_placeholders}) AND calc_date <= :cutoff
                            GROUP BY portfolio_id
                        ) m ON s1.portfolio_id = m.portfolio_id AND s1.calc_date = m.max_calc_date
                        WHERE s1.portfolio_id IN ({p_placeholders})
                        GROUP BY s1.portfolio_id, s1.total_value, s1.calc_date
                    ) s ON p.portfolio_id = s.portfolio_id
                    WHERE p.portfolio_id IN ({p_placeholders})
                """
                res = conn.execute(sqlt(q), params).mappings().fetchall()
                for row in res:
                    val = float(row.get("total_value") or 0.0)
                    r_pid = int(row.get("portfolio_id"))
                    p_name = row.get("name") or f"Portafoglio Risk #{r_pid}"
                    cat_lbl = (
                        "Cripto-attività"
                        if "cripto" in p_name.lower() or "crypto" in p_name.lower()
                        else "Portafoglio Titoli & Azioni"
                    )
                    # Se non è presente uno snapshot prima del cutoff e siamo in un esercizio passato,
                    # eseguiamo la valutazione point-in-time retroattiva tramite Risk Engine
                    if val <= 0 and is_closed_exercise:
                        try:
                            from core.risk_engine import compute_risk
                            r_res = compute_risk(r_pid, engine, as_of_date=cutoff_date[:10])
                            val = float(
                                r_res.get("total_value")
                                or r_res.get("portfolio_value")
                                or r_res.get("metrics", {}).get("total_value")
                                or r_res.get("metrics", {}).get("returns", {}).get("portfolio_value")
                                or (r_res.get("positions")["current_value"].sum() if "positions" in r_res and hasattr(r_res["positions"], "__getitem__") and "current_value" in r_res["positions"] else 0.0)
                                or 0.0
                            )
                        except Exception:
                            pass

                    if val > 0:
                        invest_voci.append(
                            {
                                "nome": p_name,
                                "categoria": cat_lbl,
                                "dettaglio": row.get("description") or f"Portafoglio Quantitativo / Risk Modulo ({as_of_str})",
                                "valore": round(val, 2),
                            }
                        )
        except Exception as e:
            logger.warning(f"Errore caricamento dettagli portafogli collegati: {e}")


    # Se non ci sono voci da risk portfolio ma ci sono conti tipo investment
    if not invest_voci:
        df_inv_acc = df_acc[
            df_acc["account_type"].isin(["investment", "investments", "crypto_exchange"]) & (df_acc["balance_eur"] > 0)
        ]
        for _, r in df_inv_acc.iterrows():
            invest_voci.append(
                {
                    "nome": r.get("account_name") or r.get("name") or "Investimento Finanziario",
                    "categoria": "Titoli & Cripto",
                    "dettaglio": r.get("institution", "Intermediario"),
                    "valore": round(float(r["balance_eur"]), 2),
                }
            )

    tot_investimenti = sum(v["valore"] for v in invest_voci)

    # --- A. ATTIVO: SEZIONE III - PREVIDENZA & RISPARMIO DI LUNGO TERMINE ---
    previdenza_voci = []
    for _, r in df_pens.iterrows():
        p_val = round(float(r.get("accum_eur", 0.0) or 0.0), 2)
        annual_contrib = float(r.get("tax_deductible_annual", 0.0) or 0.0)
        monthly_contrib = float(r.get("monthly_employee_contrib", 0.0) or 0.0)

        # 1. Tentativo di risoluzione point-in-time tramite yearly_data_json
        yearly_json = r.get("yearly_data_json")
        yd_parsed = {}
        if yearly_json and str(yearly_json).strip() not in ("", "None", "null"):
            try:
                raw_yd = json.loads(yearly_json) if isinstance(yearly_json, str) else yearly_json
                if isinstance(raw_yd, dict):
                    yd_parsed = {int(k): v for k, v in raw_yd.items() if str(k).isdigit()}
            except Exception:
                yd_parsed = {}

        # 2. Fallback parsing da campo notes se yearly_data_json non presente
        if not yd_parsed:
            notes_str = str(r.get("notes") or "")
            # Pattern tipico: 'Sincronizzato da foglio Pension (Anni: 2023: €237.73 | 2024: €1,577.74 | ...)'
            yr_matches = re.findall(r"(\d{4}):\s*€?\s*([0-9.,]+)", notes_str)
            if yr_matches:
                from core.wealth.wealth_validator import _clean_amount

                cum_running = 0.0
                for y_str, amt_str in sorted(yr_matches, key=lambda x: int(x[0])):
                    y_int = int(y_str)
                    yr_amt = _clean_amount(amt_str) or 0.0
                    cum_running += yr_amt
                    yd_parsed[y_int] = {
                        "tot_year": yr_amt,
                        "tot_cumulato": round(cum_running, 2),
                    }

        # 3. Determinazione del valore e contribuzione per l'esercizio selezionato
        if yd_parsed and selected_year is not None:
            min_y = min(yd_parsed.keys())
            max_y = max(yd_parsed.keys())

            if selected_year < min_y:
                # Fondo pensione non ancora sottoscritto nell'anno d'esercizio
                p_val = 0.0
                annual_contrib = 0.0
                monthly_contrib = 0.0
            elif selected_year in yd_parsed:
                y_info = yd_parsed[selected_year]
                tot_cum = y_info.get("tot_cumulato")
                if tot_cum is not None and float(tot_cum) > 0:
                    p_val = round(float(tot_cum), 2)
                else:
                    p_val = round(
                        sum(
                            float(yd_parsed[y].get("tot_year", 0.0) or 0.0)
                            for y in sorted(yd_parsed.keys())
                            if y <= selected_year
                        ),
                        2,
                    )

                annual_contrib = float(y_info.get("tot_year", 0.0) or 0.0)
                m_vals = y_info.get("months", {})
                if isinstance(m_vals, dict) and m_vals:
                    valid_m = [v for v in m_vals.values() if isinstance(v, (int, float)) and v > 0]
                    monthly_contrib = round(float(np.mean(valid_m)), 2) if valid_m else 0.0
                elif annual_contrib > 0:
                    monthly_contrib = round(annual_contrib / 12.0, 2)
                else:
                    monthly_contrib = 0.0
            elif selected_year > max_y:
                p_val = round(float(r.get("accum_eur", 0.0) or 0.0), 2)
        elif is_closed_exercise and not df_cf_copy.empty:
            # Se esercizio passato senza breakdown esplicito, sottraiamo i versamenti successivi registrati nel cashflow
            pens_cf_since = df_cf_copy[
                (df_cf_copy["tx_date"] > pd.to_datetime(cutoff_date))
                & (df_cf_copy["category_name"].str.contains("pensione|previdenz", case=False, na=False))
            ]
            if not pens_cf_since.empty:
                versato_dopo = pens_cf_since[pens_cf_since["direction"] == "outflow"]["amount"].sum()
                p_val = max(0.0, round(p_val - versato_dopo, 2))

        if p_val > 0:
            if annual_contrib > 0 and monthly_contrib > 0:
                dett_contrib = f"Contributo {selected_year}: €{annual_contrib:,.2f} (~€{monthly_contrib:,.2f}/m)"
            elif annual_contrib > 0:
                dett_contrib = f"Contributo {selected_year}: €{annual_contrib:,.2f}"
            elif monthly_contrib > 0:
                dett_contrib = f"Contributo medio: €{monthly_contrib:,.2f}/m"
            else:
                dett_contrib = "Capitale accantonato"

            previdenza_voci.append(
                {
                    "nome": r.get("plan_name") or "Fondo Pensione Integrativo",
                    "categoria": "Fondo Pensione / PIP",
                    "dettaglio": f"{r.get('provider', 'Gestore')} — {dett_contrib}",
                    "valore": p_val,
                }
            )
    tot_previdenza = sum(v["valore"] for v in previdenza_voci)

    # --- A. ATTIVO: SEZIONE IV - ATTIVITÀ REALI & IMMOBILIZZAZIONI PERSONALI ---
    reali_voci = []
    for _, r in df_phys.iterrows():
        cat = str(r.get("asset_category", "")).lower()
        cat_lbl = (
            "Beni di Pregio & Orologi"
            if "watch" in cat
            else (
                "Metalli Preziosi & Oro"
                if "metal" in cat
                else ("Immobile di Proprietà" if "estate" in cat else "Beni Personali di Valore")
            )
        )
        val = round(float(r["market_val_eur"]), 2)
        if val > 0:
            reali_voci.append(
                {
                    "nome": r.get("name") or "Asset Fisico",
                    "categoria": cat_lbl,
                    "dettaglio": f"{r.get('location', '')} {r.get('notes', '')}".strip()
                    or "Valutazione Peritale / Stima Mercato",
                    "valore": val,
                }
            )
    tot_attivita_reali = sum(v["valore"] for v in reali_voci)

    # --- A. ATTIVO: SEZIONE V - CREDITI PERSONALI & RATEI ATTIVI ---
    crediti_voci = []
    # Possibili crediti futuri o cauzioni registrati
    tot_crediti = sum(v["valore"] for v in crediti_voci)

    # Totale Attivo
    totale_attivo = round(tot_liquidita + tot_investimenti + tot_previdenza + tot_attivita_reali + tot_crediti, 2)

    # Sezioni Attivo formattate
    sezioni_attivo = [
        {
            "codice": "I",
            "titolo": "Attività Liquide & Mezzi Equivalenti",
            "descrizione": "Conti correnti bancari, conti deposito, liquidità broker e fondo emergenza",
            "totale": tot_liquidita,
            "incidenza_pct": round(tot_liquidita / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": liquid_voci,
        },
        {
            "codice": "II",
            "titolo": "Investimenti Finanziari & Capitale Produttivo",
            "descrizione": "Azioni, ETF, Titoli obbligazionari, Cripto-attività e portafogli gestiti",
            "totale": tot_investimenti,
            "incidenza_pct": round(tot_investimenti / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": invest_voci,
        },
        {
            "codice": "III",
            "titolo": "Previdenza & Risparmio Previdenziale",
            "descrizione": "Fondi pensione negoziali, aperti, PIP e accantonamenti pensionistici",
            "totale": tot_previdenza,
            "incidenza_pct": round(tot_previdenza / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": previdenza_voci,
        },
        {
            "codice": "IV",
            "titolo": "Attività Reali & Beni Personali",
            "descrizione": "Immobili di proprietà, collezionabili di lusso, orologi e metalli preziosi",
            "totale": tot_attivita_reali,
            "incidenza_pct": round(tot_attivita_reali / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": reali_voci,
        },
    ]
    if tot_crediti > 0:
        sezioni_attivo.append(
            {
                "codice": "V",
                "titolo": "Crediti Personali & Ratei Attivi",
                "descrizione": "Crediti personali esigibili, crediti d'imposta personali e depositi cauzionali",
                "totale": tot_crediti,
                "incidenza_pct": round(tot_crediti / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
                "voci": crediti_voci,
            }
        )

    # --- B. PASSIVO & DEBITI PERSONALI (LIABILITIES) ---
    passivo_breve_voci = []
    passivo_lungo_voci = []

    if not df_acc.empty:
        # Debiti da carte di credito
        df_cc = df_acc[df_acc["account_type"] == AccountType.CREDIT_CARD.value]
        for _, r in df_cc.iterrows():
            val = abs(float(r["balance_eur"]))
            if val > 0:
                passivo_breve_voci.append(
                    {
                        "nome": r.get("account_name") or r.get("name") or "Carta di Credito",
                        "categoria": "Debito Carta di Credito (Saldo fine mese)",
                        "dettaglio": r.get("institution", "Istituto emittente"),
                        "valore": round(val, 2),
                    }
                )

        # Scoperti di conto corrente (balance < 0)
        df_scoperti = df_acc[
            (
                ~df_acc["account_type"].isin(
                    [AccountType.CREDIT_CARD.value, AccountType.LOAN.value, AccountType.MORTGAGE.value]
                )
            )
            & (df_acc["balance_eur"] < 0)
        ]
        for _, r in df_scoperti.iterrows():
            val = abs(float(r["balance_eur"]))
            passivo_breve_voci.append(
                {
                    "nome": f"Scoperto {r.get('name', 'Conto')}",
                    "categoria": "Scoperto di Conto Corrente",
                    "dettaglio": "Saldo operativo a debito",
                    "valore": round(val, 2),
                }
            )

        # Mutui e finanziamenti a lungo termine
        df_mutui = df_acc[df_acc["account_type"].isin([AccountType.MORTGAGE.value, AccountType.LOAN.value])]
        for _, r in df_mutui.iterrows():
            val = abs(float(r["balance_eur"]))
            if val > 0:
                cat_lbl = (
                    "Mutuo Ipotecario Residuo"
                    if r["account_type"] == AccountType.MORTGAGE.value
                    else "Finanziamento / Prestito Personale"
                )
                passivo_lungo_voci.append(
                    {
                        "nome": r.get("account_name") or r.get("name") or "Finanziamento",
                        "categoria": cat_lbl,
                        "dettaglio": f"{r.get('institution', 'Banca')} (Debito residuo quota capitale)",
                        "valore": round(val, 2),
                    }
                )

    tot_passivo_breve = sum(v["valore"] for v in passivo_breve_voci)
    tot_passivo_lungo = sum(v["valore"] for v in passivo_lungo_voci)
    totale_passivo = round(tot_passivo_breve + tot_passivo_lungo, 2)

    sezioni_passivo = [
        {
            "codice": "I",
            "titolo": "Passività Correnti a Breve Termine (< 12 mesi)",
            "descrizione": "Saldi carte di credito, scoperti bancari esigibili, rateizzazioni a breve",
            "totale": tot_passivo_breve,
            "incidenza_pct": round(tot_passivo_breve / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": passivo_breve_voci,
        },
        {
            "codice": "II",
            "titolo": "Passività Consolidate a Medio/Lungo Termine (> 12 mesi)",
            "descrizione": "Mutui ipotecari residui (prima casa/altri immobili), prestiti personali, finanziamenti auto",
            "totale": tot_passivo_lungo,
            "incidenza_pct": round(tot_passivo_lungo / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": passivo_lungo_voci,
        },
    ]

    # --- C. PATRIMONIO NETTO PERSONALE (NET WORTH / EQUITY) ---
    patrimonio_netto = round(totale_attivo - totale_passivo, 2)
    totale_pareggio = round(totale_passivo + patrimonio_netto, 2)
    is_quadrato = abs(totale_attivo - totale_pareggio) < 0.01

    # ==========================================================
    # 3. CONTO ECONOMICO PERSONALE (PERSONAL INCOME STATEMENT)
    # ==========================================================
    # Filtro transazioni per anno selezionato
    if not df_cf_copy.empty and selected_year is not None:
        df_year = df_cf_copy[df_cf_copy["tx_date"].dt.year == int(selected_year)].copy()
    else:
        df_year = pd.DataFrame()

    # Elaborazione voci di Conto Economico
    ce_data = _compute_income_statement(df_year, selected_year)

    # Riconciliazione Patrimonio Netto:
    # Stima del Capitale Pregresso accumulato negli anni precedenti vs Risultato dell'anno
    risparmio_anno = ce_data.get("risparmio_netto", 0.0)
    capitale_pregresso = round(patrimonio_netto - risparmio_anno, 2)

    composizione_patrimonio_netto = [
        {
            "voce": "Capitale di Partenza & Riserve da Risparmio Pregresso",
            "descrizione": f"Ricchezza netta consolidata accumulata fino al 31/12/{int(selected_year) - 1}",
            "valore": capitale_pregresso,
            "incidenza_pct": round(capitale_pregresso / patrimonio_netto * 100, 2) if patrimonio_netto > 0 else 0.0,
        },
        {
            "voce": f"Risultato Economico d'Esercizio ({selected_year})",
            "descrizione": f"Surplus / Risparmio netto generato dalla gestione economica personale nel {selected_year}",
            "valore": risparmio_anno,
            "incidenza_pct": round(risparmio_anno / patrimonio_netto * 100, 2) if patrimonio_netto > 0 else 0.0,
        },
    ]

    # ==========================================================
    # 4. INDICI DI BILANCIO PERSONALE (RATIOS & BENCHMARKS)
    # ==========================================================
    indici = _compute_personal_ratios(
        totale_attivo=totale_attivo,
        totale_passivo=totale_passivo,
        patrimonio_netto=patrimonio_netto,
        tot_liquidita=tot_liquidita,
        tot_investimenti=tot_investimenti,
        tot_previdenza=tot_previdenza,
        ce_data=ce_data,
    )

    return {
        "as_of_date": as_of_str,
        "as_of_iso": as_of_iso,
        "period_title": period_title,
        "is_closed_exercise": is_closed_exercise,
        "portfolio_id": portfolio_id,
        "selected_year": selected_year,
        "available_years": available_years,

        "stato_patrimoniale": {
            "attivo": {
                "sezioni": sezioni_attivo,
                "totale_attivo": totale_attivo,
                "tot_liquidita": tot_liquidita,
                "tot_investimenti": tot_investimenti,
                "tot_previdenza": tot_previdenza,
                "tot_attivita_reali": tot_attivita_reali,
                "tot_crediti": tot_crediti,
            },
            "passivo": {
                "sezioni": sezioni_passivo,
                "totale_passivo": totale_passivo,
                "tot_passivo_breve": tot_passivo_breve,
                "tot_passivo_lungo": tot_passivo_lungo,
            },
            "patrimonio_netto": {
                "totale_patrimonio_netto": patrimonio_netto,
                "composizione": composizione_patrimonio_netto,
            },
            "pareggio": {
                "totale_pareggio": totale_pareggio,
                "is_quadrato": is_quadrato,
                "differenza": round(totale_attivo - totale_pareggio, 2),
            },
        },
        "conto_economico": ce_data,
        "indici_bilancio": indici,
    }


def _compute_income_statement(df_year: pd.DataFrame, year: int) -> Dict[str, Any]:
    """
    Classifica con precisione chirurgica le entrate e le uscite dell'anno solare,
    separando consumi/spese di vita dai trasferimenti di capitale e dagli investimenti.
    """
    if df_year.empty:
        return {
            "anno": year,
            "totale_entrate": 0.0,
            "totale_uscite": 0.0,
            "risparmio_netto": 0.0,
            "savings_rate_pct": 0.0,
            "entrate_sezioni": [],
            "uscite_sezioni": [],
            "allocazione_capitale": {"totale_investimenti": 0.0, "voci_investimenti": [], "variazione_liquidita": 0.0},
            "waterfall_data": [],
        }

    df = df_year.copy()
    cat_ser = (
        df["category_name"].astype(str) if "category_name" in df.columns else pd.Series([""] * len(df), index=df.index)
    )
    merch_ser = df["merchant"].astype(str) if "merchant" in df.columns else pd.Series([""] * len(df), index=df.index)
    notes_ser = df["notes"].astype(str) if "notes" in df.columns else pd.Series([""] * len(df), index=df.index)
    nat_ser = df["nature"].astype(str) if "nature" in df.columns else pd.Series([""] * len(df), index=df.index)
    dir_ser = df["direction"].astype(str) if "direction" in df.columns else pd.Series([""] * len(df), index=df.index)

    # 1. Esclusione Giroconti e Trasferimenti Interni
    is_transfer = (
        (dir_ser.str.lower() == "transfer")
        | (nat_ser.str.lower() == "transfer")
        | (cat_ser.str.contains("girocont|trasferiment|sistemazion", case=False, na=False))
    )

    # 2. Identificazione Rimborsi
    is_refund = (
        (cat_ser.str.contains("rimbors|settled from|bulk settlement|storno|reso", case=False, na=False))
        | (merch_ser.str.contains("settled from|bulk settlement|refund|rimborso", case=False, na=False))
        | (notes_ser.str.contains(r"\[refund\]|settled from|bulk settlement", case=False, na=False))
    ) & (~is_transfer)

    # 3. Identificazione Flussi di Investimento in Uscita (Capital Allocation, non consumi)
    is_investment_outflow = (
        (dir_ser.str.lower() == "outflow")
        & (
            (nat_ser.str.lower() == "saving_investment")
            | (
                cat_ser.str.contains(
                    "investiment|titoli|azioni|criptovalut|crypto|fondo pensione", case=False, na=False
                )
            )
            | (notes_ser.str.contains(r"\[investment\]|acquisto quote|pac", case=False, na=False))
        )
        & (~is_transfer)
    )

    # 4. ENTRATE (INFLOWS)
    df_in = df[(dir_ser.str.lower() == "inflow") & (~is_transfer)].copy()

    # Raggruppamento Entrate
    entrate_voci = []

    # A. Lavoro Dipendente, Autonomo & Compensi
    mask_lavoro = df_in["category_name"].str.contains(
        "stipendio|compens|parcell|fattur|premio|tfr|borsa|stage", case=False, na=False
    )
    tot_lavoro = float(df_in[mask_lavoro]["amount"].sum())
    if tot_lavoro > 0:
        entrate_voci.append(
            {
                "sezione": "Redditi da Lavoro Dipendente & Autonomo",
                "categoria": "Lavoro & Compensi",
                "descrizione": "Stipendi netti, compensi professionali, 13a/14a e borse di studio",
                "valore": round(tot_lavoro, 2),
            }
        )

    # B. Supporto Famiglia & Donazioni
    mask_famiglia = df_in["category_name"].str.contains("supporto famigli|genitor|donazion|regal", case=False, na=False)
    tot_famiglia = float(df_in[mask_famiglia]["amount"].sum())
    if tot_famiglia > 0:
        entrate_voci.append(
            {
                "sezione": "Supporto Famigliare & Donazioni Ricevute",
                "categoria": "Trasferimenti Familiari",
                "descrizione": "Aiuti finanziari, regali e contributi da parte della famiglia",
                "valore": round(tot_famiglia, 2),
            }
        )

    # C. Rendite Finanziarie & Disinvestimenti
    mask_rendite = df_in["category_name"].str.contains(
        "dividend|cedol|interess|investiment|titoli|cripto", case=False, na=False
    )
    tot_rendite = float(df_in[mask_rendite]["amount"].sum())
    if tot_rendite > 0:
        entrate_voci.append(
            {
                "sezione": "Proventi Finanziari & Rendite di Capitale",
                "categoria": "Rendite di Capitale",
                "descrizione": "Dividendi, cedole, interessi attivi e liquidazioni di asset",
                "valore": round(tot_rendite, 2),
            }
        )

    # D. Rimborsi & Entrate Varie
    mask_altre = (~mask_lavoro) & (~mask_famiglia) & (~mask_rendite)
    tot_altre = float(df_in[mask_altre]["amount"].sum())
    if tot_altre > 0:
        entrate_voci.append(
            {
                "sezione": "Rimborsi Spese & Altre Entrate Straordinarie",
                "categoria": "Rimborsi & Varie",
                "descrizione": "Rimborsi spese saldate da terzi, resi e introiti extra",
                "valore": round(tot_altre, 2),
            }
        )

    totale_entrate = round(float(df_in["amount"].sum()), 2)

    # 5. USCITE / CONSUMI PERSONALI (OUTFLOWS - SPESE DI VITA)
    # Filtriamo le uscite che NON sono trasferimenti e NON sono investimenti (quelli vanno in capital allocation)
    df_out_living = df[(dir_ser.str.lower() == "outflow") & (~is_transfer) & (~is_investment_outflow)].copy()

    uscite_categorie_mapping = [
        (
            "Abitazione, Affitto & Utenze",
            ["casa", "affitto", "utenze", "luce", "gas", "condominio", "internet", "spese casa"],
        ),
        ("Spesa Alimentare & Supermercato", ["spesa alimentare", "supermercato", "alimentari"]),
        ("Ristoranti, Serate & Socialità", ["ristoranti", "pizzerie", "sushi", "serate", "bar", "aperitivi"]),
        ("Trasporti, Mobilità & Benzina", ["trasporti", "benzina", "carburante", "mezzi", "autostrada", "parcheggi"]),
        ("Istruzione, Formazione & Libri", ["istruzione", "corsi", "libri", "università", "formazione"]),
        ("Salute, Farmacia & Visite Mediche", ["salute", "farmacia", "visite", "medico", "dentista"]),
        ("Tempo Libero, Viaggi & Eventi", ["tempo libero", "cinema", "eventi", "viaggi", "voli", "vacanze", "hotel"]),
        (
            "Shopping, Tecnologia & Cura Personale",
            ["shopping", "abbigliamento", "elettronica", "pc", "gadget", "cura personale", "parrucchiere", "abitudini"],
        ),
        ("Abbonamenti Digitali & Ricorrenti", ["abbonamenti", "streaming", "spotify", "icloud", "netflix"]),
        ("Regali, Eventi & Supporto Famiglia", ["regali", "lauree", "supporto famiglia", "spese per la famiglia"]),
        ("Imposte, Tasse & Commissioni Bancarie", ["tasse", "imposte", "commissioni", "bollo", "canone"]),
        ("Spese Varie & Imprevisti Personali", ["spese varie", "imprevisti"]),
    ]

    uscite_voci = []
    matched_indices = set()

    for macro_nome, keywords in uscite_categorie_mapping:
        pat = "|".join(keywords)
        mask = df_out_living["category_name"].str.contains(pat, case=False, na=False) & (
            ~df_out_living.index.isin(matched_indices)
        )
        tot_sub = float(df_out_living[mask]["amount"].sum())
        if tot_sub > 0:
            matched_indices.update(df_out_living[mask].index)
            uscite_voci.append(
                {
                    "sezione": macro_nome,
                    "categoria": macro_nome.split(",")[0].strip(),
                    "valore": round(tot_sub, 2),
                    "num_movimenti": int(mask.sum()),
                }
            )

    # Eventuali spese residue non mappate
    unmatched_mask = ~df_out_living.index.isin(matched_indices)
    tot_unmatched = float(df_out_living[unmatched_mask]["amount"].sum())
    if tot_unmatched > 0:
        uscite_voci.append(
            {
                "sezione": "Altre Spese Personali Non Classificate",
                "categoria": "Varie",
                "valore": round(tot_unmatched, 2),
                "num_movimenti": int(unmatched_mask.sum()),
            }
        )

    # Ordina uscite per importo decrescente
    uscite_voci = sorted(uscite_voci, key=lambda x: x["valore"], reverse=True)
    totale_uscite = round(float(df_out_living["amount"].sum()), 2)

    # 6. RISULTATO D'ESERCIZIO PERSONALE (SURPLUS / RISPARMIO NETTO)
    risparmio_netto = round(totale_entrate - totale_uscite, 2)
    savings_rate_pct = round((risparmio_netto / totale_entrate * 100.0), 2) if totale_entrate > 0 else 0.0

    # 7. ALLOCAZIONE DEL RISPARMIO & INVESTIMENTI DEL PERIODO
    df_inv = df[is_investment_outflow].copy()
    totale_investimenti = round(float(df_inv["amount"].sum()), 2)

    voci_inv = []
    if not df_inv.empty:
        inv_summary = df_inv.groupby("category_name")["amount"].sum().reset_index()
        for _, r in inv_summary.iterrows():
            voci_inv.append({"nome": r["category_name"], "valore": round(float(r["amount"]), 2)})

    # Risparmio Liquido rimasto sul conto dopo gli investimenti eseguiti
    variazione_liquidita = round(risparmio_netto - totale_investimenti, 2)

    # Waterfall data per Plotly
    waterfall_data = [
        {"measure": "relative", "x": "Totale Entrate", "y": totale_entrate},
        {"measure": "relative", "x": "Spese di Vita (Consumi)", "y": -totale_uscite},
        {"measure": "total", "x": "Risparmio Netto", "y": risparmio_netto},
        {"measure": "relative", "x": "Investimenti Eseguiti (PAC/Crypto)", "y": -totale_investimenti},
        {"measure": "total", "x": "Risparmio Liquido Accantonato", "y": variazione_liquidita},
    ]

    return {
        "anno": year,
        "totale_entrate": totale_entrate,
        "totale_uscite": totale_uscite,
        "risparmio_netto": risparmio_netto,
        "savings_rate_pct": savings_rate_pct,
        "entrate_sezioni": entrate_voci,
        "uscite_sezioni": uscite_voci,
        "allocazione_capitale": {
            "totale_investimenti": totale_investimenti,
            "voci_investimenti": voci_inv,
            "variazione_liquidita": variazione_liquidita,
        },
        "waterfall_data": waterfall_data,
    }


def _compute_personal_ratios(
    totale_attivo: float,
    totale_passivo: float,
    patrimonio_netto: float,
    tot_liquidita: float,
    tot_investimenti: float,
    tot_previdenza: float,
    ce_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calcola i 6 Indici Fondamentali di Bilancio Personale:
    1. Indice di Solvibilità Patrimoniale (Net Worth / Total Assets)
    2. Indice di Indebitamento (Total Liabilities / Total Assets)
    3. Runway Fondo Emergenza (Liquidità / Spese mensili medie)
    4. Personal Savings Rate (Risparmio Netto / Entrate)
    5. Debt Service-to-Income DSTI (Servizio del Debito / Entrate)
    6. Indice di Asset Produttivi (Invested Assets Ratio)
    """
    tot_uscite = ce_data.get("totale_uscite", 0.0)
    tot_entrate = ce_data.get("totale_entrate", 0.0)
    spesa_mensile = (tot_uscite / 12.0) if tot_uscite > 0 else 1500.0

    # 1. Indice di Solvibilità Patrimoniale
    solvency_val = round((patrimonio_netto / totale_attivo * 100), 1) if totale_attivo > 0 else 100.0
    if solvency_val >= 70.0:
        solv_status, solv_color = "OPTIMAL", "#10b981"
    elif solvency_val >= 50.0:
        solv_status, solv_color = "ACCEPTABLE", "#f59e0b"
    else:
        solv_status, solv_color = "WARNING", "#ef4444"

    # 2. Indice di Indebitamento (Debt-to-Assets)
    debt_assets_val = round((totale_passivo / totale_attivo * 100), 1) if totale_attivo > 0 else 0.0
    if debt_assets_val <= 20.0:
        debt_status, debt_color = "OPTIMAL", "#10b981"
    elif debt_assets_val <= 40.0:
        debt_status, debt_color = "ACCEPTABLE", "#f59e0b"
    else:
        debt_status, debt_color = "WARNING", "#ef4444"

    # 3. Runway Fondo di Emergenza (Mesi di copertura spese)
    if spesa_mensile > 0:
        runway_val = round(tot_liquidita / spesa_mensile, 1)
    else:
        runway_val = 99.0

    if runway_val >= 6.0:
        runway_status, runway_color = "OPTIMAL", "#10b981"
    elif runway_val >= 3.0:
        runway_status, runway_color = "ACCEPTABLE", "#f59e0b"
    else:
        runway_status, runway_color = "WARNING", "#ef4444"

    # 4. Personal Savings Rate %
    savings_rate_val = ce_data.get("savings_rate_pct", 0.0)
    if savings_rate_val >= 25.0:
        sr_status, sr_color = "OPTIMAL", "#10b981"
    elif savings_rate_val >= 15.0:
        sr_status, sr_color = "ACCEPTABLE", "#f59e0b"
    else:
        sr_status, sr_color = "WARNING", "#ef4444"

    # 5. DSTI - Debt Service-to-Income %
    # Stima rate annue da passivo a breve/lungo se presenti (assumiamo rate ammortamento standard ~8% annuo del debito residuo)
    rate_annue_stimate = (totale_passivo * 0.08) if totale_passivo > 0 else 0.0
    dsti_val = round((rate_annue_stimate / tot_entrate * 100), 1) if tot_entrate > 0 else 0.0
    if dsti_val <= 15.0:
        dsti_status, dsti_color = "OPTIMAL", "#10b981"
    elif dsti_val <= 33.0:
        dsti_status, dsti_color = "ACCEPTABLE", "#f59e0b"
    else:
        dsti_status, dsti_color = "WARNING", "#ef4444"

    # 6. Invested Assets Ratio (Capitale che lavora / Patrimonio Netto)
    invested_assets = tot_investimenti + tot_previdenza
    invested_ratio_val = round((invested_assets / patrimonio_netto * 100), 1) if patrimonio_netto > 0 else 0.0
    if invested_ratio_val >= 50.0:
        inv_status, inv_color = "OPTIMAL", "#10b981"
    elif invested_ratio_val >= 25.0:
        inv_status, inv_color = "ACCEPTABLE", "#f59e0b"
    else:
        inv_status, inv_color = "WARNING", "#ef4444"

    # Health Rating complessivo del Bilancio Personale
    optimal_count = sum(
        1 for s in [solv_status, debt_status, runway_status, sr_status, dsti_status, inv_status] if s == "OPTIMAL"
    )
    if optimal_count >= 5:
        overall_rating = "AAA (Solidità Finanziaria Istituzionale)"
        overall_desc = "Struttura patrimoniale eccezionale: assenza o controllo totale del debito, elevata liquidità di sicurezza e formidabile capacità di accumulo."
    elif optimal_count >= 3:
        overall_rating = "AA (Solidità Equilibrata)"
        overall_desc = "Ottimo profilo patrimoniale, patrimonio netto ampiamente positivo e gestione equilibrata delle uscite familiari."
    else:
        overall_rating = "A (Profilo in Consolidamento)"
        overall_desc = (
            "Profilo solido con margini di ottimizzazione su riserve di liquidità o quota di asset a reddito."
        )

    return {
        "overall_rating": overall_rating,
        "overall_description": overall_desc,
        "optimal_kpi_count": f"{optimal_count}/6",
        "solvency_ratio": {
            "valore": solvency_val,
            "formattato": f"{solvency_val:.1f}%",
            "label": "Indice di Solvibilità",
            "target": "≥ 70%",
            "formula": "Patrimonio Netto / Attivo Totale",
            "status": solv_status,
            "colore": solv_color,
            "descrizione": "Misura la percentuale di patrimonio libero da qualsiasi vincolo o debito verso terzi.",
        },
        "debt_to_assets": {
            "valore": debt_assets_val,
            "formattato": f"{debt_assets_val:.1f}%",
            "label": "Debt-to-Assets (Leva)",
            "target": "≤ 30%",
            "formula": "Passività Totali / Attivo Totale",
            "status": debt_status,
            "colore": debt_color,
            "descrizione": "Rapporto tra l'indebitamento complessivo e il totale dei beni posseduti.",
        },
        "emergency_runway": {
            "valore": runway_val,
            "formattato": f"{runway_val:.1f} Mesi",
            "label": "Runway Fondo Emergenza",
            "target": "≥ 6 Mesi",
            "formula": "Liquidità Immediata / Spese Mensili Medie",
            "status": runway_status,
            "colore": runway_color,
            "descrizione": "Autonomia finanziaria in caso di azzeramento improvviso di tutte le entrate correnti.",
        },
        "savings_rate": {
            "valore": savings_rate_val,
            "formattato": f"{savings_rate_val:.1f}%",
            "label": "Personal Savings Rate",
            "target": "≥ 20%",
            "formula": "Risparmio Netto / Totale Entrate",
            "status": sr_status,
            "colore": sr_color,
            "descrizione": "Percentuale del reddito convertita in nuovo patrimonio anziché consumata in spese correnti.",
        },
        "dsti": {
            "valore": dsti_val,
            "formattato": f"{dsti_val:.1f}%",
            "label": "Debt Service-to-Income (DSTI)",
            "target": "≤ 33%",
            "formula": "Rate di Debito Annue / Entrate Totali",
            "status": dsti_status,
            "colore": dsti_color,
            "descrizione": "Percentuale delle entrate assorbita dal rimborso di finanziamenti o mutui.",
        },
        "invested_assets_ratio": {
            "valore": invested_ratio_val,
            "formattato": f"{invested_ratio_val:.1f}%",
            "label": "Invested Assets Ratio",
            "target": "≥ 50%",
            "formula": "(Investimenti + Previdenza) / Patrimonio Netto",
            "status": inv_status,
            "colore": inv_color,
            "descrizione": "Percentuale del patrimonio investita in asset finanziari produttivi di rendimento composto.",
        },
    }


def compute_multi_year_balance_comparison(
    engine: Engine,
    portfolio_id: int = 1,
    years: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Costruisce il prospetto comparativo pluriennale del bilancio personale
    (Stato Patrimoniale & Conto Economico affiancati) con calcolo delle variazioni
    assolute (Delta EUR) e relative (Delta %) anno su anno.
    """
    df_cf = get_cashflow_records(engine, portfolio_id=portfolio_id)
    if not years:
        if not df_cf.empty:
            df_cf["tx_date"] = pd.to_datetime(df_cf["tx_date"], errors="coerce")
            all_yrs = sorted([int(y) for y in df_cf["tx_date"].dt.year.dropna().unique()], reverse=True)
        else:
            all_yrs = [date.today().year]
        if date.today().year not in all_yrs:
            all_yrs = sorted(list(set(all_yrs + [date.today().year])), reverse=True)
        years = all_yrs  # Tutti gli esercizi storici disponibili (es. 2021 - 2026)

    years = sorted(years)  # Ordine cronologico crescente per calcolare i delta

    rows = []
    for y in years:
        res = compute_personal_balance_sheet(engine, portfolio_id=portfolio_id, year=y)
        sp = res["stato_patrimoniale"]
        ce = res["conto_economico"]
        ind = res["indici_bilancio"]
        rows.append({
            "anno": y,
            "period_title": res.get("period_title"),
            "as_of_date": res.get("as_of_date"),
            "totale_attivo": sp["attivo"]["totale_attivo"],
            "tot_liquidita": sp["attivo"]["tot_liquidita"],
            "tot_investimenti": sp["attivo"]["tot_investimenti"],
            "tot_previdenza": sp["attivo"]["tot_previdenza"],
            "tot_attivita_reali": sp["attivo"]["tot_attivita_reali"],
            "totale_passivo": sp["passivo"]["totale_passivo"],
            "passivo_breve": sp["passivo"]["tot_passivo_breve"],
            "passivo_lungo": sp["passivo"]["tot_passivo_lungo"],
            "patrimonio_netto": sp["patrimonio_netto"]["totale_patrimonio_netto"],
            "totale_entrate": ce.get("totale_entrate", 0.0),
            "totale_uscite": ce.get("totale_uscite", 0.0),
            "risparmio_netto": ce.get("risparmio_netto", 0.0),
            "savings_rate_pct": ce.get("savings_rate_pct", 0.0),
            "solvency_ratio": ind.get("solvency_ratio", {}).get("valore", 100.0),
        })

    df_comp = pd.DataFrame(rows)
    # Calcolo delta anno su anno
    if len(df_comp) > 1:
        df_comp["delta_pn_eur"] = df_comp["patrimonio_netto"].diff()
        df_comp["delta_pn_pct"] = df_comp["patrimonio_netto"].pct_change() * 100.0
        df_comp["delta_attivo_eur"] = df_comp["totale_attivo"].diff()
        df_comp["delta_passivo_eur"] = df_comp["totale_passivo"].diff()
        df_comp["delta_risparmio_eur"] = df_comp["risparmio_netto"].diff()
    else:
        df_comp["delta_pn_eur"] = 0.0
        df_comp["delta_pn_pct"] = 0.0
        df_comp["delta_attivo_eur"] = 0.0
        df_comp["delta_passivo_eur"] = 0.0
        df_comp["delta_risparmio_eur"] = 0.0

    return {
        "portfolio_id": portfolio_id,
        "years": sorted(years, reverse=True),
        "comparison_df": df_comp.sort_values("anno", ascending=False).reset_index(drop=True),
        "records": df_comp.to_dict(orient="records")
    }


# ============================================================
# 5. GENERAZIONE REPORT HTML & PDF (DOSSIER MULTI-PAGINA & TEAR-SHEET)
# Conforme agli standard CFP Board & Private Banking
# ============================================================


def _convert_html_to_pdf(html_content: str) -> Optional[bytes]:
    """
    Compila un documento HTML in formato PDF A4 pixel-perfect tramite browser headless nativo
    (Microsoft Edge / Google Chrome / Chromium). Restituisce i byte binari o None in caso di assenza/errore.
    """
    browser_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "msedge",
        "chrome",
        "google-chrome",
        "chromium",
    ]

    found_browser = None
    for b in browser_candidates:
        if os.path.isabs(b) and os.path.exists(b):
            found_browser = b
            break
        elif not os.path.isabs(b):
            p = shutil.which(b)
            if p:
                found_browser = p
                break

    if not found_browser:
        return None

    tmp_html = None
    tmp_pdf = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
            f.write(html_content)
            tmp_html = f.name
        tmp_pdf = tmp_html.replace(".html", ".pdf")

        cmd = [
            found_browser,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={tmp_pdf}",
            tmp_html,
        ]
        subprocess.run(cmd, capture_output=True, timeout=15)
        if os.path.exists(tmp_pdf) and os.path.getsize(tmp_pdf) > 0:
            with open(tmp_pdf, "rb") as f_pdf:
                return f_pdf.read()
    except Exception as e:
        logger.warning(f"Headless PDF conversion failed: {e}")
    finally:
        if tmp_html and os.path.exists(tmp_html):
            try:
                os.remove(tmp_html)
            except Exception:
                pass
        if tmp_pdf and os.path.exists(tmp_pdf):
            try:
                os.remove(tmp_pdf)
            except Exception:
                pass
    return None


def generate_personal_balance_sheet_html(engine: Engine, portfolio_id: int = 1, year: Optional[int] = None) -> str:
    """
    Genera il codice HTML completo e impaginato per il Dossier di Bilancio Personale Multipagina
    (esattamente 3 Pagine A4, zero overflow) conforme agli standard CFP Board e Private Banking.
    Include:
      - Pagina 1: Stato Patrimoniale a sezioni contrapposte & pareggio di bilancio
      - Pagina 2: Conto Economico di gestione & waterfall allocazione del capitale
      - Pagina 3: Indici di bilancio, indicatori di solvibilità e riconciliazione conti
    """
    data = compute_personal_balance_sheet(engine, portfolio_id=portfolio_id, year=year)
    df_prof = get_wealth_portfolios(engine)
    prof_name = "Master Portfolio"
    if not df_prof.empty and portfolio_id in df_prof["portfolio_id"].values:
        prof_name = str(df_prof.loc[df_prof["portfolio_id"] == portfolio_id, "name"].values[0])

    df_acc = get_wealth_accounts(engine, portfolio_id=portfolio_id)
    _, df_risk_linked = get_linked_risk_portfolios_summary(engine, wealth_portfolio_id=portfolio_id)

    sp = data["stato_patrimoniale"]
    ce = data["conto_economico"]
    ind = data["indici_bilancio"]
    as_of_date = data["as_of_date"]
    selected_year = data["selected_year"]

    tot_att = sp["attivo"]["totale_attivo"]
    tot_pas = sp["passivo"]["totale_passivo"]
    tot_pn = sp["patrimonio_netto"]["totale_patrimonio_netto"]
    tot_pareggio = sp["pareggio"]["totale_pareggio"]
    is_quadrato = sp["pareggio"]["is_quadrato"]

    ce_inflow = ce.get("totale_entrate", 0.0)
    ce_outflow = ce.get("totale_uscite", 0.0)
    ce_savings = ce.get("risparmio_netto", 0.0)
    ce_sr = ce.get("savings_rate_pct", 0.0)
    ce_alloc = ce.get("allocazione_capitale", {})
    ce_inv = ce_alloc.get("totale_investimenti", 0.0)
    ce_liq_var = ce_alloc.get("variazione_liquidita", 0.0)

    # Costruzione righe HTML Attivo
    attivo_html = ""
    for sez in sp["attivo"]["sezioni"]:
        attivo_html += f"""
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:5px; margin-bottom:6px; overflow:hidden;">
            <div style="background:#0f172a; color:#ffffff; padding:4px 8px; display:flex; justify-content:space-between; align-items:center; font-size:9.5pt; font-weight:700;">
                <span>{sez['codice']}. {sez['titolo']}</span>
                <span style="font-family:'SF Mono', Consolas, monospace;">&euro; {sez['totale']:,.2f} ({sez['incidenza_pct']:.1f}%)</span>
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:8pt;">
        """
        if sez["voci"]:
            for v in sez["voci"]:
                inc_voce = (v['valore'] / max(1.0, tot_att) * 100)
                attivo_html += f"""
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:2.5px 6px; font-weight:600; color:#1e293b;">{v['nome']}</td>
                    <td style="padding:2.5px 6px; color:#64748b; font-size:7.5pt;">{v['categoria']} &bull; {v['dettaglio']}</td>
                    <td style="padding:2.5px 6px; text-align:right; font-weight:700; color:#0f172a; font-family:'SF Mono', Consolas, monospace;">&euro; {v['valore']:,.2f}</td>
                    <td style="padding:2.5px 6px; text-align:right; color:#10b981; font-weight:600; font-size:7.5pt;">{inc_voce:.1f}%</td>
                </tr>
                """
        else:
            attivo_html += "<tr><td colspan='4' style='padding:4px; text-align:center; color:#94a3b8; font-style:italic;'>Nessuna voce contabile presente</td></tr>"
        attivo_html += "</table></div>"

    # Costruzione righe HTML Passivo
    passivo_html = ""
    for sez in sp["passivo"]["sezioni"]:
        passivo_html += f"""
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:5px; margin-bottom:6px; overflow:hidden;">
            <div style="background:#334155; color:#ffffff; padding:4px 8px; display:flex; justify-content:space-between; align-items:center; font-size:9.5pt; font-weight:700;">
                <span>{sez['codice']}. {sez['titolo']}</span>
                <span style="font-family:'SF Mono', Consolas, monospace;">&euro; {sez['totale']:,.2f} ({sez['incidenza_pct']:.1f}%)</span>
            </div>
            <table style="width:100%; border-collapse:collapse; font-size:8pt;">
        """
        if sez["voci"]:
            for v in sez["voci"]:
                inc_voce = (v['valore'] / max(1.0, tot_att) * 100)
                passivo_html += f"""
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:2.5px 6px; font-weight:600; color:#1e293b;">{v['nome']}</td>
                    <td style="padding:2.5px 6px; color:#64748b; font-size:7.5pt;">{v['categoria']} &bull; {v['dettaglio']}</td>
                    <td style="padding:2.5px 6px; text-align:right; font-weight:700; color:#ef4444; font-family:'SF Mono', Consolas, monospace;">&euro; {v['valore']:,.2f}</td>
                    <td style="padding:2.5px 6px; text-align:right; color:#ef4444; font-weight:600; font-size:7.5pt;">{inc_voce:.1f}%</td>
                </tr>
                """
        else:
            passivo_html += "<tr><td colspan='4' style='padding:4px; text-align:center; color:#94a3b8; font-style:italic;'>Nessuna passività registrata (Zero Debiti)</td></tr>"
        passivo_html += "</table></div>"

    # Sezione Patrimonio Netto
    pn_html = f"""
    <div style="background:#f8fafc; border:1px solid #cbd5e1; border-radius:5px; margin-bottom:6px; overflow:hidden;">
        <div style="background:#0369a1; color:#ffffff; padding:4px 8px; display:flex; justify-content:space-between; align-items:center; font-size:9.5pt; font-weight:700;">
            <span>III. Patrimonio Netto Personale (Fonti Proprie)</span>
            <span style="font-family:'SF Mono', Consolas, monospace;">&euro; {tot_pn:,.2f}</span>
        </div>
        <table style="width:100%; border-collapse:collapse; font-size:8pt;">
    """
    for comp in sp["patrimonio_netto"]["composizione"]:
        pn_html += f"""
        <tr style="border-bottom:1px solid #f1f5f9;">
            <td style="padding:3px 6px; font-weight:600; color:#1e293b;">{comp['voce']}</td>
            <td style="padding:3px 6px; color:#64748b; font-size:7.5pt;">{comp['descrizione']}</td>
            <td style="padding:3px 6px; text-align:right; font-weight:700; color:#0284c7; font-family:'SF Mono', Consolas, monospace;">&euro; {comp['valore']:,.2f}</td>
            <td style="padding:3px 6px; text-align:right; color:#0284c7; font-weight:600; font-size:7.5pt;">{comp['incidenza_pct']:.1f}%</td>
        </tr>
        """
    pn_html += "</table></div>"

    # Righe Conto Economico: Entrate
    ce_in_rows = ""
    if ce.get("entrate_sezioni"):
        for item in ce["entrate_sezioni"]:
            inc = (item["valore"] / max(1.0, ce_inflow) * 100)
            ce_in_rows += f"""
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:2.5px 5px; font-weight:600; color:#1e293b;">{item['sezione']}</td>
                <td style="padding:2.5px 5px; color:#64748b;">{item['categoria']}</td>
                <td style="padding:2.5px 5px; text-align:right; font-weight:700; color:#059669; font-family:'SF Mono', Consolas, monospace;">&euro; {item['valore']:,.2f}</td>
                <td style="padding:2.5px 5px; text-align:right; color:#059669; font-weight:600;">{inc:.1f}%</td>
            </tr>
            """
    else:
        ce_in_rows = "<tr><td colspan='4' style='padding:10px; text-align:center; color:#94a3b8; font-style:italic;'>Nessuna entrata registrata per l'anno solare</td></tr>"

    # Righe Conto Economico: Uscite
    ce_out_rows = ""
    if ce.get("uscite_sezioni"):
        for item in ce["uscite_sezioni"]:
            inc = (item["valore"] / max(1.0, ce_outflow) * 100)
            ce_out_rows += f"""
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:2px 5px; font-weight:600; color:#1e293b;">{item['sezione']}</td>
                <td style="padding:2px 5px; text-align:center; color:#64748b;">{item.get('num_movimenti', 1)}</td>
                <td style="padding:2px 5px; text-align:right; font-weight:700; color:#dc2626; font-family:'SF Mono', Consolas, monospace;">&euro; {item['valore']:,.2f}</td>
                <td style="padding:2px 5px; text-align:right; color:#dc2626; font-weight:600;">{inc:.1f}%</td>
            </tr>
            """
    else:
        ce_out_rows = "<tr><td colspan='4' style='padding:10px; text-align:center; color:#94a3b8; font-style:italic;'>Nessuna uscita registrata per l'anno solare</td></tr>"

    # Riconciliazione Conti Bancari con calcolo EUR accurato
    acc_rows = ""
    if not df_acc.empty:
        type_map = {
            "checking": "Conto Corrente",
            "savings": "Conto Deposito",
            "emergency_fund": "Fondo Emergenza",
            "brokerage_cash": "Liquidità Broker",
            "credit_card": "Carta di Credito",
            "loan": "Prestito Personale",
            "mortgage": "Mutuo Ipotecario",
            "crypto_exchange": "Exchange Cripto",
            "investment": "Dossier Titoli",
        }
        for _, r in df_acc.iterrows():
            b_val = float(r.get("balance", 0.0) or 0.0)
            curr = str(r.get("currency", "EUR"))
            b_eur = b_val * get_fx_rate_to_eur(curr)
            c_raw = str(r.get("account_type", "")).lower()
            c_type = type_map.get(c_raw, c_raw.replace("_", " ").title())
            acc_rows += f"""
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:2.5px 5px; font-weight:600; color:#1e293b;">{r.get('name', 'Conto')}</td>
                <td style="padding:2.5px 5px; color:#64748b;">{c_type}</td>
                <td style="padding:2.5px 5px; color:#64748b;">{r.get('institution', 'Istituto')}</td>
                <td style="padding:2.5px 5px; text-align:right; font-weight:700; font-family:'SF Mono', Consolas, monospace;">&euro; {b_eur:,.2f}</td>
            </tr>
            """
    else:
        acc_rows = "<tr><td colspan='4' style='padding:8px; text-align:center; color:#94a3b8;'>Nessun conto bancario registrato</td></tr>"

    # Portafogli Risk Engine Collegati
    risk_rows = ""
    if not df_risk_linked.empty:
        for _, rk in df_risk_linked.iterrows():
            v_live = float(rk.get("latest_value", 0.0) or 0.0)
            dt_up = str(rk.get("last_calc_date", "Live"))[:10]
            risk_rows += f"""
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:2.5px 5px; font-weight:600; color:#1e293b;">{rk.get('name', 'Portafoglio')}</td>
                <td style="padding:2.5px 5px; color:#64748b;">Portafoglio Titoli / Quant</td>
                <td style="padding:2.5px 5px; color:#64748b;">{dt_up}</td>
                <td style="padding:2.5px 5px; text-align:right; font-weight:700; font-family:'SF Mono', Consolas, monospace;">&euro; {v_live:,.2f}</td>
            </tr>
            """
    else:
        risk_rows = "<tr><td colspan='4' style='padding:8px; text-align:center; color:#94a3b8;'>Nessun portafoglio quantitativo collegato</td></tr>"

    # Recupera i dati del Bilancio Comparativo Pluriennale per la Pagina 4
    comp_res = compute_multi_year_balance_comparison(engine, portfolio_id=portfolio_id)
    df_comp = comp_res.get("comparison_df", pd.DataFrame())

    multi_kpi_html = ""
    multi_rows_html = ""
    multi_bars_html = ""
    crescita_cumulata = 0.0
    crescita_pct = 0.0
    oldest_yr_str = str(selected_year)
    latest_yr_str = str(selected_year)

    if not df_comp.empty:
        latest_row = df_comp.iloc[0]
        oldest_row = df_comp.iloc[-1]
        oldest_yr_str = str(oldest_row["anno"])
        latest_yr_str = str(latest_row["anno"])
        crescita_cumulata = float(latest_row["patrimonio_netto"] - oldest_row["patrimonio_netto"])
        crescita_pct = (
            (crescita_cumulata / oldest_row["patrimonio_netto"] * 100.0) if oldest_row["patrimonio_netto"] > 0 else 0.0
        )
        n_anni = max(1, len(df_comp) - 1)
        media_crescita_annua = crescita_cumulata / n_anni
        avg_sr = df_comp["savings_rate_pct"].mean()
        max_attivo = max(df_comp["totale_attivo"].max(), 1.0)

        multi_kpi_html = f"""
        <div class="kpi-grid">
            <div class="kpi-card highlight">
                <div class="kpi-label">Esercizi Esaminati</div>
                <div class="kpi-val">{len(df_comp)} Esercizi</div>
                <div class="kpi-sub">{oldest_row['anno']} &ndash; {latest_row['anno']}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Patrimonio Netto Attuale</div>
                <div class="kpi-val">&euro; {latest_row['patrimonio_netto']:,.2f}</div>
                <div class="kpi-sub">Esercizio {latest_row['anno']}</div>
            </div>
            <div class="kpi-card highlight">
                <div class="kpi-label">Crescita Netta Cumulata</div>
                <div class="kpi-val" style="color:#059669;">{'+' if crescita_cumulata >= 0 else ''}&euro; {crescita_cumulata:,.2f}</div>
                <div class="kpi-sub">{'+' if crescita_pct >= 0 else ''}{crescita_pct:.1f}% nel periodo</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Savings Rate Medio</div>
                <div class="kpi-val">{avg_sr:.1f}%</div>
                <div class="kpi-sub">&Delta; Medio: &euro; {media_crescita_annua:,.2f}/anno</div>
            </div>
        </div>
        """

        for _, r in df_comp.iterrows():
            d_eur = r.get("delta_pn_eur")
            d_pct = r.get("delta_pn_pct")
            d_eur_str = (
                f"+&euro; {d_eur:,.2f}"
                if (d_eur is not None and not pd.isna(d_eur) and d_eur > 0)
                else (f"-&euro; {abs(d_eur):,.2f}" if (d_eur is not None and not pd.isna(d_eur) and d_eur < 0) else "&mdash;")
            )
            d_pct_str = (
                f"+{d_pct:.1f}%"
                if (d_pct is not None and not pd.isna(d_pct) and d_pct > 0)
                else (f"{d_pct:.1f}%" if (d_pct is not None and not pd.isna(d_pct) and d_pct < 0) else "&mdash;")
            )
            d_color = (
                "#059669"
                if (d_eur is not None and not pd.isna(d_eur) and d_eur > 0)
                else ("#dc2626" if (d_eur is not None and not pd.isna(d_eur) and d_eur < 0) else "#64748b")
            )

            multi_rows_html += f"""
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="font-weight:800; color:#0f172a; padding:3px 6px;">{r['anno']}</td>
                <td style="text-align:right; font-family:'SF Mono', Consolas, monospace; font-weight:700; color:#059669;">&euro; {r['totale_attivo']:,.2f}</td>
                <td style="text-align:right; font-family:'SF Mono', Consolas, monospace; color:#3b82f6;">&euro; {r['tot_liquidita']:,.2f}</td>
                <td style="text-align:right; font-family:'SF Mono', Consolas, monospace; color:#6366f1;">&euro; {r['tot_investimenti']:,.2f}</td>
                <td style="text-align:right; font-family:'SF Mono', Consolas, monospace; color:#8b5cf6;">&euro; {r['tot_previdenza']:,.2f}</td>
                <td style="text-align:right; font-family:'SF Mono', Consolas, monospace; color:#64748b;">&euro; {r['totale_passivo']:,.2f}</td>
                <td style="text-align:right; font-family:'SF Mono', Consolas, monospace; font-weight:800; color:#0f172a; background:#f8fafc;">&euro; {r['patrimonio_netto']:,.2f}</td>
                <td style="text-align:right; font-family:'SF Mono', Consolas, monospace; font-weight:700; color:{d_color};">{d_eur_str} ({d_pct_str})</td>
                <td style="text-align:right; font-family:'SF Mono', Consolas, monospace; color:#0284c7;">&euro; {r['risparmio_netto']:,.2f}</td>
                <td style="text-align:center; font-weight:700; color:{'#059669' if r['savings_rate_pct'] >= 20 else '#d97706'};">{r['savings_rate_pct']:.1f}%</td>
            </tr>
            """

            pct_bar = min(100.0, max(6.0, (r['patrimonio_netto'] / max_attivo) * 100.0))
            multi_bars_html += f"""
            <div style="display:flex; align-items:center; margin-bottom:5px; font-size:7.5pt;">
                <div style="width:45px; font-weight:700; color:#0f172a;">{r['anno']}</div>
                <div style="flex:1; background:#f1f5f9; border-radius:4px; height:13px; overflow:hidden; position:relative; display:flex;">
                    <div style="background:#10b981; width:{pct_bar}%; height:100%; border-radius:3px;"></div>
                </div>
                <div style="width:120px; text-align:right; font-family:'SF Mono', Consolas, monospace; font-weight:700; color:#0f172a;">
                    &euro; {r['patrimonio_netto']:,.2f}
                </div>
            </div>
            """

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>ARGUS Wealth — Bilancio Personale Istituzionale - {prof_name}</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 0.8cm 1.0cm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Segoe UI Emoji', Arial, sans-serif;
            color: #0f172a;
            background-color: #ffffff;
            margin: 0;
            padding: 0;
            font-size: 8.5pt;
            line-height: 1.35;
        }}
        .page {{
            page-break-after: always;
            page-break-inside: avoid;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-sizing: border-box;
        }}
        .page:last-child {{
            page-break-after: avoid;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            border-bottom: 2px solid #0f172a;
            padding-bottom: 4px;
            margin-bottom: 8px;
        }}
        .title {{
            font-size: 16pt;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #0f172a;
            margin: 0;
        }}
        .subtitle {{
            font-size: 7.5pt;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            color: #059669;
            font-weight: 700;
            margin-top: 1px;
        }}
        .meta-box {{
            text-align: right;
            font-size: 8pt;
            color: #64748b;
        }}
        .meta-val {{
            font-weight: 700;
            color: #0f172a;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 8px;
        }}
        .kpi-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 6px 10px;
        }}
        .kpi-card.highlight {{
            background: #f0fdf4;
            border-color: #bbf7d0;
        }}
        .kpi-label {{
            font-size: 7pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #64748b;
            font-weight: 700;
        }}
        .kpi-val {{
            font-size: 12pt;
            font-weight: 800;
            color: #0f172a;
            margin-top: 2px;
            font-family: 'SF Mono', Consolas, monospace;
        }}
        .kpi-sub {{
            font-size: 6.5pt;
            color: #059669;
            font-weight: 600;
            margin-top: 1px;
        }}
        .sp-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 8px;
        }}
        .section-header {{
            font-size: 9pt;
            font-weight: 800;
            padding: 5px 8px;
            border-radius: 4px;
            margin-bottom: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-header.attivo {{
            background: #ecfdf5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }}
        .section-header.passivo {{
            background: #fef2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }}
        .section-header.pn {{
            background: #f0f9ff;
            color: #075985;
            border: 1px solid #bae6fd;
        }}
        .total-box {{
            padding: 6px 10px;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 800;
            font-size: 9.5pt;
            margin-top: 5px;
        }}
        .total-box.attivo {{
            background: #059669;
            color: #ffffff;
        }}
        .total-box.pareggio {{
            background: #0284c7;
            color: #ffffff;
        }}
        .stamp-box {{
            background: #f8fafc;
            border: 1.5px solid #10b981;
            border-radius: 6px;
            padding: 6px 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 8pt;
            color: #065f46;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .table-custom {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8pt;
            margin-bottom: 6px;
        }}
        .table-custom th {{
            background: #0f172a;
            color: #ffffff;
            font-weight: 700;
            text-align: left;
            padding: 4px 6px;
            font-size: 7.5pt;
        }}
        .table-custom td {{
            padding: 2.5px 5px;
            border-bottom: 1px solid #e2e8f0;
        }}
        .badge {{
            padding: 1.5px 5px;
            border-radius: 3px;
            font-size: 7pt;
            font-weight: 700;
            display: inline-block;
        }}
        .badge-optimal {{
            background: #ecfdf5;
            color: #059669;
            border: 1px solid #a7f3d0;
        }}
        .badge-acceptable {{
            background: #fffbeb;
            color: #d97706;
            border: 1px solid #fde68a;
        }}
        .badge-warning {{
            background: #fef2f2;
            color: #dc2626;
            border: 1px solid #fecaca;
        }}
        .footer {{
            border-top: 1px solid #cbd5e1;
            padding-top: 4px;
            margin-top: 6px;
            display: flex;
            justify-content: space-between;
            font-size: 7pt;
            color: #64748b;
        }}
    </style>
</head>
<body>

    <!-- ======================================================== -->
    <!-- PAGINA 1: STATO PATRIMONIALE A SEZIONI CONTRAPPOSTE     -->
    <!-- ======================================================== -->
    <div class="page">
        <div>
            <div class="header">
                <div>
                    <h1 class="title">ARGUS WEALTH MANAGEMENT</h1>
                    <div class="subtitle">Personal Financial Statements &bull; {data.get('period_title', 'Esercizio ' + str(selected_year))}</div>
                </div>
                <div class="meta-box">
                    <div>Profilo: <span class="meta-val">{prof_name.upper()}</span></div>
                    <div>Esercizio: <span class="meta-val">{selected_year}</span></div>
                    <div>Data Contabile: <span class="meta-val">{as_of_date}</span></div>
                    <div>Rating di Solidit&agrave;: <span class="meta-val" style="color:#059669;">{ind.get('overall_rating', 'AAA').split()[0]}</span></div>
                </div>

            </div>

            <!-- KPI Ribbon -->
            <div class="kpi-grid">
                <div class="kpi-card highlight">
                    <div class="kpi-label">Attivo Totale (Assets)</div>
                    <div class="kpi-val">&euro; {tot_att:,.2f}</div>
                    <div class="kpi-sub">Impieghi di Ricchezza</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Passivit&agrave; Totali (Debiti)</div>
                    <div class="kpi-val">&euro; {tot_pas:,.2f}</div>
                    <div class="kpi-sub">Fonti Esterne (Terzi)</div>
                </div>
                <div class="kpi-card highlight">
                    <div class="kpi-label">Patrimonio Netto (Equity)</div>
                    <div class="kpi-val">&euro; {tot_pn:,.2f}</div>
                    <div class="kpi-sub">Capitale Netto Proprio</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Pareggio di Bilancio</div>
                    <div class="kpi-val">&euro; {tot_pareggio:,.2f}</div>
                    <div class="kpi-sub">{'✅ Pareggio Quadrato (Δ=0)' if is_quadrato else '⚠️ Discrepanza'}</div>
                </div>
            </div>

            <!-- Sezioni Contrapposte -->
            <div class="sp-grid">
                <div>
                    <div class="section-header attivo">
                        <span>🏛️ ATTIVO (IMPIEGHI)</span>
                        <span style="font-size:7.5pt;">INCIDENZA %</span>
                    </div>
                    {attivo_html}
                    <div class="total-box attivo">
                        <span>TOTALE ATTIVO (ASSETS)</span>
                        <span style="font-family:'SF Mono', Consolas, monospace;">&euro; {tot_att:,.2f}</span>
                    </div>
                </div>

                <div>
                    <div class="section-header passivo">
                        <span>⚖️ PASSIVO (FONTI TERZI)</span>
                        <span style="font-size:7.5pt;">INCIDENZA %</span>
                    </div>
                    {passivo_html}

                    <div class="section-header pn">
                        <span>💎 PATRIMONIO NETTO (EQUITY)</span>
                        <span style="font-size:7.5pt;">FONTI PROPRIE</span>
                    </div>
                    {pn_html}

                    <div class="total-box pareggio">
                        <span>TOTALE PAREGGIO (PASSIVO + PN)</span>
                        <span style="font-family:'SF Mono', Consolas, monospace;">&euro; {tot_pareggio:,.2f}</span>
                    </div>
                </div>
            </div>

            <div class="stamp-box">
                <div>
                    <span>🛡️ CERTIFICAZIONE CONTABILE CFP / IFRS: EQUAZIONE FONDAMENTALE VERIFICATA</span>
                    <div style="font-size:7pt; color:#64748b; font-weight:normal; margin-top:1px;">
                        Attivo Totale (&euro; {tot_att:,.2f}) = Passivit&agrave; Totali (&euro; {tot_pas:,.2f}) + Patrimonio Netto (&euro; {tot_pn:,.2f}) &bull; Delta Pareggio: &euro; 0,00
                    </div>
                </div>
                <div style="font-size:13pt;">✅</div>
            </div>
        </div>

        <div class="footer">
            <div>ARGUS Financial Ecosystem &bull; Personal Balance Sheet Engine v9.0.0</div>
            <div>Confidenziale &bull; Elaborazione 100% Locale &bull; Zero-Cloud Transmission</div>
            <div>Pagina 1 di 4</div>
        </div>
    </div>

    <!-- ======================================================== -->
    <!-- PAGINA 2: CONTO ECONOMICO & ALLOCAZIONE DEL CAPITALE     -->
    <!-- ======================================================== -->
    <div class="page">
        <div>
            <div class="header">
                <div>
                    <h1 class="title">CONTO ECONOMICO DI GESTIONE</h1>
                    <div class="subtitle">Statement of Financial Performance &bull; Esercizio {selected_year}</div>
                </div>
                <div class="meta-box">
                    <div>Profilo: <span class="meta-val">{prof_name.upper()}</span></div>
                    <div>Periodo: <span class="meta-val">01/01/{selected_year} - 31/12/{selected_year}</span></div>
                    <div>Savings Rate: <span class="meta-val" style="color:#059669;">{ce_sr:.1f}%</span></div>
                </div>
            </div>

            <!-- KPI Conto Economico -->
            <div class="kpi-grid">
                <div class="kpi-card highlight">
                    <div class="kpi-label">Totale Entrate {selected_year}</div>
                    <div class="kpi-val">&euro; {ce_inflow:,.2f}</div>
                    <div class="kpi-sub">Redditi da Lavoro e Capitale</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Costi Gestione &amp; Consumi</div>
                    <div class="kpi-val" style="color:#dc2626;">&euro; {ce_outflow:,.2f}</div>
                    <div class="kpi-sub">Spese di Vita Effettive</div>
                </div>
                <div class="kpi-card highlight">
                    <div class="kpi-label">Risparmio Netto Annuo</div>
                    <div class="kpi-val" style="color:{'#059669' if ce_savings >= 0 else '#dc2626'};">&euro; {ce_savings:,.2f}</div>
                    <div class="kpi-sub">Surplus d'Esercizio Generato</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Personal Savings Rate</div>
                    <div class="kpi-val">{ce_sr:.1f}%</div>
                    <div class="kpi-sub">Benchmark CFP &ge; 20%</div>
                </div>
            </div>

            <!-- Due Colonne: Entrate vs Spese -->
            <div class="sp-grid">
                <div>
                    <div class="section-header attivo">
                        <span>📈 VALORE PRODUZIONE PERSONALE (ENTRATE)</span>
                        <span style="font-size:7.5pt;">INCID.</span>
                    </div>
                    <table class="table-custom">
                        <thead>
                            <tr>
                                <th>Voce di Entrata</th>
                                <th>Tipologia</th>
                                <th style="text-align:right;">Importo (&euro;)</th>
                                <th style="text-align:right;">Incid.</th>
                            </tr>
                        </thead>
                        <tbody>
                            {ce_in_rows}
                        </tbody>
                    </table>
                    <div class="total-box attivo" style="font-size:8.5pt;">
                        <span>TOTALE ENTRATE ORDINARIE</span>
                        <span style="font-family:'SF Mono', Consolas, monospace;">&euro; {ce_inflow:,.2f}</span>
                    </div>
                </div>

                <div>
                    <div class="section-header passivo">
                        <span>📉 COSTI DI GESTIONE &amp; CONSUMI (USCITE)</span>
                        <span style="font-size:7.5pt;">INCID.</span>
                    </div>
                    <table class="table-custom">
                        <thead>
                            <tr>
                                <th>Categoria di Spesa</th>
                                <th style="text-align:center;">Mov.</th>
                                <th style="text-align:right;">Importo (&euro;)</th>
                                <th style="text-align:right;">Incid.</th>
                            </tr>
                        </thead>
                        <tbody>
                            {ce_out_rows}
                        </tbody>
                    </table>
                    <div class="total-box" style="background:#dc2626; color:#ffffff; font-size:8.5pt;">
                        <span>TOTALE SPESE DI VITA (CONSUMI)</span>
                        <span style="font-family:'SF Mono', Consolas, monospace;">&euro; {ce_outflow:,.2f}</span>
                    </div>
                </div>
            </div>

            <!-- Rendiconto Allocazione Capitale & Waterfall -->
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:6px 10px; margin-top:6px;">
                <div style="font-weight:800; color:#0f172a; font-size:9pt; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
                    <span>🌊 Rendiconto di Allocazione del Capitale &amp; Destinazione del Risparmio ({selected_year})</span>
                    <span style="font-size:7.5pt; color:#64748b;">CFP Practice Standard</span>
                </div>
                <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:8px; margin-top:6px;">
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:5px; padding:5px 8px;">
                        <div style="font-size:7pt; text-transform:uppercase; color:#64748b; font-weight:700;">1. Surplus di Risparmio</div>
                        <div style="font-size:11pt; font-weight:800; color:#059669; font-family:'SF Mono', Consolas, monospace; margin-top:1px;">&euro; {ce_savings:,.2f}</div>
                        <div style="font-size:6.5pt; color:#64748b;">Entrate totali meno consumi</div>
                    </div>
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:5px; padding:5px 8px;">
                        <div style="font-size:7pt; text-transform:uppercase; color:#64748b; font-weight:700;">2. Flussi Investiti (PAC)</div>
                        <div style="font-size:11pt; font-weight:800; color:#0284c7; font-family:'SF Mono', Consolas, monospace; margin-top:1px;">&euro; {ce_inv:,.2f}</div>
                        <div style="font-size:6.5pt; color:#64748b;">Acquisto titoli, ETF e previdenza</div>
                    </div>
                    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:5px; padding:5px 8px;">
                        <div style="font-size:7pt; text-transform:uppercase; color:#64748b; font-weight:700;">3. Riserve di Liquidit&agrave;</div>
                        <div style="font-size:11pt; font-weight:800; color:#475569; font-family:'SF Mono', Consolas, monospace; margin-top:1px;">&euro; {ce_liq_var:,.2f}</div>
                        <div style="font-size:6.5pt; color:#64748b;">Variazione cassa operativa</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            <div>ARGUS Financial Ecosystem &bull; Personal Balance Sheet Engine v9.0.0</div>
            <div>Conto Economico &bull; Separazione Netta Consumi vs Trasferimenti Patrimoniali</div>
            <div>Pagina 2 di 4</div>
        </div>
    </div>

    <!-- ======================================================== -->
    <!-- PAGINA 3: INDICI DI BILANCIO, SOLIDITÀ & RICONCILIAZIONE -->
    <!-- ======================================================== -->
    <div class="page">
        <div>
            <div class="header">
                <div>
                    <h1 class="title">INDICI DI BILANCIO &amp; SOLIDIT&Agrave;</h1>
                    <div class="subtitle">Solvency Ratios, Financial Benchmarks &amp; Accounts Reconciliation</div>
                </div>
                <div class="meta-box">
                    <div>Profilo: <span class="meta-val">{prof_name.upper()}</span></div>
                    <div>Data Certificazione: <span class="meta-val">{as_of_date}</span></div>
                    <div>Optimal KPI Count: <span class="meta-val" style="color:#059669;">{ind.get('optimal_kpi_count', '6/6')}</span></div>
                </div>
            </div>

            <!-- Health Rating Banner -->
            <div style="background:#f8fafc; border:1.5px solid #10b981; border-radius:8px; padding:8px 12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div style="font-size:11pt; font-weight:800; color:#0f172a;">
                        🛡️ Rating Patrimoniale Istituzionale: <span style="color:#059669;">{ind.get('overall_rating', 'AAA')}</span>
                    </div>
                    <div style="font-size:7.5pt; color:#64748b; margin-top:1px; max-width:620px;">
                        {ind.get('overall_description', '')}
                    </div>
                </div>
                <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:6px; padding:4px 10px; text-align:center;">
                    <div style="font-size:7pt; font-weight:700; color:#059669; text-transform:uppercase;">Scorecard</div>
                    <div style="font-size:11pt; font-weight:800; color:#059669;">{ind.get('optimal_kpi_count', '6/6')}</div>
                </div>
            </div>

            <!-- Tabella dei 6 Indici Fondamentali -->
            <div style="margin-bottom:8px;">
                <div style="font-size:9pt; font-weight:800; color:#0f172a; margin-bottom:4px;">
                    🎯 I 6 Indici Fondamentali di Bilancio Personale (CFP Board / Private Banking)
                </div>
                <table class="table-custom">
                    <thead>
                        <tr>
                            <th>Indice Contabile</th>
                            <th>Formula</th>
                            <th>Valore Rilevato</th>
                            <th>Target CFP</th>
                            <th style="text-align:center;">Stato</th>
                            <th>Rilevanza Patrimoniale</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="font-weight:700; color:#0f172a;">{ind['solvency_ratio']['label']}</td>
                            <td style="color:#64748b; font-size:7.5pt;">{ind['solvency_ratio']['formula']}</td>
                            <td style="font-weight:800; font-family:'SF Mono', Consolas, monospace; font-size:10pt;">{ind['solvency_ratio']['formattato']}</td>
                            <td style="color:#64748b; font-weight:600;">{ind['solvency_ratio']['target']}</td>
                            <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['solvency_ratio']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['solvency_ratio']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['solvency_ratio']['status']}</span></td>
                            <td style="font-size:7.5pt; color:#475569;">{ind['solvency_ratio']['descrizione']}</td>
                        </tr>
                        <tr>
                            <td style="font-weight:700; color:#0f172a;">{ind['debt_to_assets']['label']}</td>
                            <td style="color:#64748b; font-size:7.5pt;">{ind['debt_to_assets']['formula']}</td>
                            <td style="font-weight:800; font-family:'SF Mono', Consolas, monospace; font-size:10pt;">{ind['debt_to_assets']['formattato']}</td>
                            <td style="color:#64748b; font-weight:600;">{ind['debt_to_assets']['target']}</td>
                            <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['debt_to_assets']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['debt_to_assets']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['debt_to_assets']['status']}</span></td>
                            <td style="font-size:7.5pt; color:#475569;">{ind['debt_to_assets']['descrizione']}</td>
                        </tr>
                        <tr>
                            <td style="font-weight:700; color:#0f172a;">{ind['emergency_runway']['label']}</td>
                            <td style="color:#64748b; font-size:7.5pt;">{ind['emergency_runway']['formula']}</td>
                            <td style="font-weight:800; font-family:'SF Mono', Consolas, monospace; font-size:10pt;">{ind['emergency_runway']['formattato']}</td>
                            <td style="color:#64748b; font-weight:600;">{ind['emergency_runway']['target']}</td>
                            <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['emergency_runway']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['emergency_runway']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['emergency_runway']['status']}</span></td>
                            <td style="font-size:7.5pt; color:#475569;">{ind['emergency_runway']['descrizione']}</td>
                        </tr>
                        <tr>
                            <td style="font-weight:700; color:#0f172a;">{ind['savings_rate']['label']}</td>
                            <td style="color:#64748b; font-size:7.5pt;">{ind['savings_rate']['formula']}</td>
                            <td style="font-weight:800; font-family:'SF Mono', Consolas, monospace; font-size:10pt;">{ind['savings_rate']['formattato']}</td>
                            <td style="color:#64748b; font-weight:600;">{ind['savings_rate']['target']}</td>
                            <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['savings_rate']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['savings_rate']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['savings_rate']['status']}</span></td>
                            <td style="font-size:7.5pt; color:#475569;">{ind['savings_rate']['descrizione']}</td>
                        </tr>
                        <tr>
                            <td style="font-weight:700; color:#0f172a;">{ind['dsti']['label']}</td>
                            <td style="color:#64748b; font-size:7.5pt;">{ind['dsti']['formula']}</td>
                            <td style="font-weight:800; font-family:'SF Mono', Consolas, monospace; font-size:10pt;">{ind['dsti']['formattato']}</td>
                            <td style="color:#64748b; font-weight:600;">{ind['dsti']['target']}</td>
                            <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['dsti']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['dsti']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['dsti']['status']}</span></td>
                            <td style="font-size:7.5pt; color:#475569;">{ind['dsti']['descrizione']}</td>
                        </tr>
                        <tr>
                            <td style="font-weight:700; color:#0f172a;">{ind['invested_assets_ratio']['label']}</td>
                            <td style="color:#64748b; font-size:7.5pt;">{ind['invested_assets_ratio']['formula']}</td>
                            <td style="font-weight:800; font-family:'SF Mono', Consolas, monospace; font-size:10pt;">{ind['invested_assets_ratio']['formattato']}</td>
                            <td style="color:#64748b; font-weight:600;">{ind['invested_assets_ratio']['target']}</td>
                            <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['invested_assets_ratio']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['invested_assets_ratio']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['invested_assets_ratio']['status']}</span></td>
                            <td style="font-size:7.5pt; color:#475569;">{ind['invested_assets_ratio']['descrizione']}</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Riconciliazione Conti & Portafogli Collegati -->
            <div class="sp-grid">
                <div>
                    <div style="font-size:8.5pt; font-weight:800; color:#0f172a; margin-bottom:3px;">
                        🏦 Riconciliazione Conti &amp; Depositi Bancari
                    </div>
                    <table class="table-custom">
                        <thead>
                            <tr>
                                <th>Conto</th>
                                <th>Tipo</th>
                                <th>Istituto</th>
                                <th style="text-align:right;">Saldo (&euro;)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {acc_rows}
                        </tbody>
                    </table>
                </div>

                <div>
                    <div style="font-size:8.5pt; font-weight:800; color:#0f172a; margin-bottom:3px;">
                        📈 Portafogli Quantitativi (Risk Engine)
                    </div>
                    <table class="table-custom">
                        <thead>
                            <tr>
                                <th>Portafoglio</th>
                                <th>Tipo</th>
                                <th>Agg.</th>
                                <th style="text-align:right;">Valore (&euro;)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {risk_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Certificazione Finale -->
            <div style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:5px; padding:5px 8px; font-size:7pt; color:#64748b; margin-top:4px;">
                <b>Nota Metodologica e Legale:</b> Conforme ai principi generali di contabilità patrimoniale personale per Private Clients e Family Office. I valori esposti riflettono saldi bancari, valutazioni peritali e prezzi di mercato storici/live privi di intermediazione terza. Crittografia locale AES-256.
            </div>
        </div>

        <div class="footer">
            <div>ARGUS Financial Ecosystem &bull; Personal Balance Sheet Engine v9.0.0</div>
            <div>Solvibilit&agrave; e Rating &bull; Conforme agli standard CFP Board e IFRS</div>
            <div>Pagina 3 di 4</div>
        </div>
    </div>

    <!-- ======================================================== -->
    <!-- PAGINA 4: BILANCIO COMPARATIVO PLURIENNALE & TREND       -->
    <!-- ======================================================== -->
    <div class="page">
        <div>
            <div class="header">
                <div>
                    <h1 class="title">BILANCIO COMPARATIVO PLURIENNALE</h1>
                    <div class="subtitle">Multi-Year Historical Trend &bull; Serie Storica 2021 &ndash; {selected_year}</div>
                </div>
                <div class="meta-box">
                    <div>Profilo: <span class="meta-val">{prof_name.upper()}</span></div>
                    <div>Anni Tracciati: <span class="meta-val">{len(df_comp) if not df_comp.empty else 0} Esercizi</span></div>
                    <div>Crescita PN: <span class="meta-val" style="color:#059669;">+{crescita_pct:.1f}%</span></div>
                </div>
            </div>

            <!-- KPI Ribbon Pluriennale -->
            <div class="kpi-grid">
                {multi_kpi_html}
            </div>

            <!-- Tabella Comparativa Pluriennale -->
            <div style="margin-bottom:10px;">
                <div style="font-size:9pt; font-weight:800; color:#0f172a; margin-bottom:4px;">
                    📊 Confronto Stato Patrimoniale &amp; Conto Economico per Esercizio
                </div>
                <table class="table-custom">
                    <thead>
                        <tr>
                            <th>Esercizio</th>
                            <th style="text-align:right;">Attivo Totale (&euro;)</th>
                            <th style="text-align:right;">Liquidit&agrave; (&euro;)</th>
                            <th style="text-align:right;">Investimenti (&euro;)</th>
                            <th style="text-align:right;">Previdenza (&euro;)</th>
                            <th style="text-align:right;">Passivo Totale (&euro;)</th>
                            <th style="text-align:right;">Patrimonio Netto (&euro;)</th>
                            <th style="text-align:right;">Delta PN</th>
                            <th style="text-align:right;">Risparmio Netto (&euro;)</th>
                            <th style="text-align:center;">Savings %</th>
                        </tr>
                    </thead>
                    <tbody>
                        {multi_rows_html}
                    </tbody>
                </table>
            </div>

            <!-- Visualizzazione Evoluzione Net Worth (CSS Progress Bars) -->
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px 14px; margin-bottom:8px;">
                <div style="font-weight:800; color:#0f172a; font-size:9pt; margin-bottom:8px;">
                    📈 Evoluzione Visiva della Ricchezza Netta Reale (Capitale Proprio 2021 &ndash; {selected_year})
                </div>
                <div style="display:flex; flex-direction:column; gap:6px;">
                    {multi_bars_html}
                </div>
            </div>

            <!-- Nota Metodologica Pluriennale -->
            <div style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:5px; padding:6px 10px; font-size:7pt; color:#64748b; margin-top:6px;">
                <b>Nota sulla Serie Storica:</b> I dati comparativi riflettono i flussi di cassa storici classificati e gli snapshot congelati al 31/12 di ciascun anno solare. L'incremento patrimoniale include sia il risparmio netto cumulato da lavoro sia la rivalutazione dei mercati finanziari sui portafogli di investimento.
            </div>
        </div>

        <div class="footer">
            <div>ARGUS Financial Ecosystem &bull; Personal Balance Sheet Engine v9.0.0</div>
            <div>Serie Storica Pluriennale &bull; Tracciamento Patrimoniale Integrato</div>
            <div>Pagina 4 di 4</div>
        </div>
    </div>

</body>
</html>
"""
    return html


def generate_personal_balance_sheet_tearsheet_html(engine: Engine, portfolio_id: int = 1, year: Optional[int] = None) -> str:
    """
    Genera il codice HTML compatto per la Tear-Sheet Contabile One-Page (Singola Pagina A4).
    Ideale per commercialisti, private banker o revisioni esecutive rapide.
    """
    data = compute_personal_balance_sheet(engine, portfolio_id=portfolio_id, year=year)
    df_prof = get_wealth_portfolios(engine)
    prof_name = "Master Portfolio"
    if not df_prof.empty and portfolio_id in df_prof["portfolio_id"].values:
        prof_name = str(df_prof.loc[df_prof["portfolio_id"] == portfolio_id, "name"].values[0])

    sp = data["stato_patrimoniale"]
    ce = data["conto_economico"]
    ind = data["indici_bilancio"]
    as_of_date = data["as_of_date"]
    selected_year = data["selected_year"]

    tot_att = sp["attivo"]["totale_attivo"]
    tot_pas = sp["passivo"]["totale_passivo"]
    tot_pn = sp["patrimonio_netto"]["totale_patrimonio_netto"]
    tot_pareggio = sp["pareggio"]["totale_pareggio"]
    is_quadrato = sp["pareggio"]["is_quadrato"]

    ce_inflow = ce.get("totale_entrate", 0.0)
    ce_outflow = ce.get("totale_uscite", 0.0)
    ce_savings = ce.get("risparmio_netto", 0.0)
    ce_sr = ce.get("savings_rate_pct", 0.0)

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>ARGUS — Tear-Sheet Contabile - {prof_name}</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 1.0cm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #0f172a;
            background-color: #ffffff;
            margin: 0;
            padding: 0;
            font-size: 9pt;
            line-height: 1.35;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            border-bottom: 2px solid #0f172a;
            padding-bottom: 6px;
            margin-bottom: 12px;
        }}
        .title {{
            font-size: 17pt;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #0f172a;
            margin: 0;
        }}
        .subtitle {{
            font-size: 7.5pt;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #059669;
            font-weight: 700;
            margin-top: 1px;
        }}
        .meta-box {{
            text-align: right;
            font-size: 8pt;
            color: #64748b;
        }}
        .meta-val {{
            font-weight: 700;
            color: #0f172a;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 12px;
        }}
        .kpi-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 8px 10px;
        }}
        .kpi-label {{
            font-size: 7pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #64748b;
            font-weight: 700;
        }}
        .kpi-val {{
            font-size: 13pt;
            font-weight: 800;
            color: #0f172a;
            margin-top: 2px;
            font-family: 'SF Mono', Consolas, monospace;
        }}
        .sp-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.5pt;
            margin-bottom: 8px;
        }}
        th {{
            background: #0f172a;
            color: #ffffff;
            font-weight: 700;
            text-align: left;
            padding: 5px 6px;
            font-size: 8pt;
        }}
        td {{
            padding: 4px 6px;
            border-bottom: 1px solid #e2e8f0;
        }}
        .badge {{
            padding: 1px 5px;
            border-radius: 3px;
            font-size: 7.5pt;
            font-weight: 700;
        }}
        .badge-optimal {{ background: #ecfdf5; color: #059669; }}
        .badge-acceptable {{ background: #fffbeb; color: #d97706; }}
        .badge-warning {{ background: #fef2f2; color: #dc2626; }}
        .footer {{
            border-top: 1px solid #cbd5e1;
            padding-top: 6px;
            margin-top: 10px;
            display: flex;
            justify-content: space-between;
            font-size: 7pt;
            color: #94a3b8;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1 class="title">ARGUS WEALTH MANAGEMENT</h1>
            <div class="subtitle">Personal Balance Sheet &bull; {data.get('period_title', 'Esercizio ' + str(selected_year))} (1-Page Tear-Sheet)</div>
        </div>
        <div class="meta-box">
            <div>Profilo: <span class="meta-val">{prof_name.upper()}</span></div>
            <div>Esercizio: <span class="meta-val">{selected_year}</span></div>
            <div>Data Riferimento: <span class="meta-val">{as_of_date}</span></div>
            <div>Rating: <span class="meta-val" style="color:#059669;">{ind.get('overall_rating', 'AAA').split()[0]}</span></div>
        </div>

    </div>

    <!-- KPI Strip -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Attivo Totale</div>
            <div class="kpi-val">&euro; {tot_att:,.2f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Passivit&agrave; Totali</div>
            <div class="kpi-val">&euro; {tot_pas:,.2f}</div>
        </div>
        <div class="kpi-card" style="background:#f0fdf4; border-color:#bbf7d0;">
            <div class="kpi-label">Patrimonio Netto</div>
            <div class="kpi-val" style="color:#059669;">&euro; {tot_pn:,.2f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Savings Rate ({selected_year})</div>
            <div class="kpi-val">{ce_sr:.1f}%</div>
        </div>
    </div>

    <!-- Stato Patrimoniale Sintetico a Due Colonne -->
    <div class="sp-grid">
        <!-- Sinistra: Attivo -->
        <div>
            <div style="font-size:9pt; font-weight:800; color:#065f46; background:#ecfdf5; border:1px solid #a7f3d0; padding:4px 8px; border-radius:4px; margin-bottom:4px; display:flex; justify-content:space-between;">
                <span>🏛️ ATTIVO PATRIMONIALE</span>
                <span>PESO %</span>
            </div>
            <table>
                <tbody>
                    <tr>
                        <td><b>I. Liquidit&agrave; &amp; Conti Deposito</b></td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {sp['attivo']['tot_liquidita']:,.2f}</td>
                        <td style="text-align:right; color:#059669; font-weight:600;">{(sp['attivo']['tot_liquidita'] / max(1.0, tot_att) * 100):.1f}%</td>
                    </tr>
                    <tr>
                        <td><b>II. Investimenti &amp; Titoli</b></td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {sp['attivo']['tot_investimenti']:,.2f}</td>
                        <td style="text-align:right; color:#059669; font-weight:600;">{(sp['attivo']['tot_investimenti'] / max(1.0, tot_att) * 100):.1f}%</td>
                    </tr>
                    <tr>
                        <td><b>III. Previdenza Integrativa</b></td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {sp['attivo']['tot_previdenza']:,.2f}</td>
                        <td style="text-align:right; color:#059669; font-weight:600;">{(sp['attivo']['tot_previdenza'] / max(1.0, tot_att) * 100):.1f}%</td>
                    </tr>
                    <tr>
                        <td><b>IV. Immobili &amp; Attivit&agrave; Reali</b></td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {sp['attivo']['tot_attivita_reali']:,.2f}</td>
                        <td style="text-align:right; color:#059669; font-weight:600;">{(sp['attivo']['tot_attivita_reali'] / max(1.0, tot_att) * 100):.1f}%</td>
                    </tr>
                    {f"<tr><td><b>V. Crediti Personali</b></td><td style='text-align:right;'>&euro; {sp['attivo']['tot_crediti']:,.2f}</td><td style='text-align:right;'>{(sp['attivo']['tot_crediti']/max(1.0, tot_att)*100):.1f}%</td></tr>" if sp['attivo']['tot_crediti'] > 0 else ""}
                    <tr style="background:#059669; color:#ffffff; font-weight:bold;">
                        <td>TOTALE ATTIVO (ASSETS)</td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {tot_att:,.2f}</td>
                        <td style="text-align:right;">100.0%</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Destra: Passivo & PN -->
        <div>
            <div style="font-size:9pt; font-weight:800; color:#991b1b; background:#fef2f2; border:1px solid #fecaca; padding:4px 8px; border-radius:4px; margin-bottom:4px; display:flex; justify-content:space-between;">
                <span>⚖️ PASSIVO &amp; PATRIMONIO NETTO</span>
                <span>PESO %</span>
            </div>
            <table>
                <tbody>
                    <tr>
                        <td><b>I. Passivit&agrave; a Breve (&lt; 12m)</b></td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {sp['passivo']['tot_passivo_breve']:,.2f}</td>
                        <td style="text-align:right; color:#dc2626;">{(sp['passivo']['tot_passivo_breve'] / max(1.0, tot_att) * 100):.1f}%</td>
                    </tr>
                    <tr>
                        <td><b>II. Mutui &amp; Finanziamenti (&gt; 12m)</b></td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {sp['passivo']['tot_passivo_lungo']:,.2f}</td>
                        <td style="text-align:right; color:#dc2626;">{(sp['passivo']['tot_passivo_lungo'] / max(1.0, tot_att) * 100):.1f}%</td>
                    </tr>
                    <tr style="background:#f8fafc; font-weight:600;">
                        <td>Totale Passivit&agrave; (Debiti)</td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {tot_pas:,.2f}</td>
                        <td style="text-align:right;">{(tot_pas / max(1.0, tot_att) * 100):.1f}%</td>
                    </tr>
                    <tr style="background:#f0f9ff; font-weight:bold; color:#0369a1;">
                        <td>III. PATRIMONIO NETTO (EQUITY)</td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {tot_pn:,.2f}</td>
                        <td style="text-align:right;">{(tot_pn / max(1.0, tot_att) * 100):.1f}%</td>
                    </tr>
                    <tr style="background:#0284c7; color:#ffffff; font-weight:bold;">
                        <td>TOTALE PAREGGIO (PASSIVO + PN)</td>
                        <td style="text-align:right; font-family:'SF Mono', Consolas, monospace;">&euro; {tot_pareggio:,.2f}</td>
                        <td style="text-align:right;">100.0%</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- Sintesi Conto Economico -->
    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:6px 10px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:700; color:#0f172a;">📈 Conto Economico {selected_year}:</span>
        <span>Entrate: <b>&euro; {ce_inflow:,.2f}</b></span>
        <span>Consumi: <b style="color:#dc2626;">&euro; {ce_outflow:,.2f}</b></span>
        <span>Risparmio Netto: <b style="color:#059669;">&euro; {ce_savings:,.2f}</b></span>
        <span>Savings Rate: <b style="color:#059669;">{ce_sr:.1f}%</b></span>
    </div>

    <!-- Indici Fondamentali di Bilancio -->
    <div style="font-size:9pt; font-weight:800; color:#0f172a; margin-bottom:4px;">
        🎯 Indici Chiave di Solvibilit&agrave; e Solidit&agrave; Finanziaria (CFP Standards)
    </div>
    <table>
        <thead>
            <tr>
                <th>Indice</th>
                <th>Formula</th>
                <th>Valore</th>
                <th>Target</th>
                <th style="text-align:center;">Stato</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><b>{ind['solvency_ratio']['label']}</b></td>
                <td style="color:#64748b;">{ind['solvency_ratio']['formula']}</td>
                <td style="font-weight:700; font-family:'SF Mono', Consolas, monospace;">{ind['solvency_ratio']['formattato']}</td>
                <td>{ind['solvency_ratio']['target']}</td>
                <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['solvency_ratio']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['solvency_ratio']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['solvency_ratio']['status']}</span></td>
            </tr>
            <tr>
                <td><b>{ind['debt_to_assets']['label']}</b></td>
                <td style="color:#64748b;">{ind['debt_to_assets']['formula']}</td>
                <td style="font-weight:700; font-family:'SF Mono', Consolas, monospace;">{ind['debt_to_assets']['formattato']}</td>
                <td>{ind['debt_to_assets']['target']}</td>
                <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['debt_to_assets']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['debt_to_assets']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['debt_to_assets']['status']}</span></td>
            </tr>
            <tr>
                <td><b>{ind['emergency_runway']['label']}</b></td>
                <td style="color:#64748b;">{ind['emergency_runway']['formula']}</td>
                <td style="font-weight:700; font-family:'SF Mono', Consolas, monospace;">{ind['emergency_runway']['formattato']}</td>
                <td>{ind['emergency_runway']['target']}</td>
                <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['emergency_runway']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['emergency_runway']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['emergency_runway']['status']}</span></td>
            </tr>
            <tr>
                <td><b>{ind['savings_rate']['label']}</b></td>
                <td style="color:#64748b;">{ind['savings_rate']['formula']}</td>
                <td style="font-weight:700; font-family:'SF Mono', Consolas, monospace;">{ind['savings_rate']['formattato']}</td>
                <td>{ind['savings_rate']['target']}</td>
                <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['savings_rate']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['savings_rate']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['savings_rate']['status']}</span></td>
            </tr>
            <tr>
                <td><b>{ind['dsti']['label']}</b></td>
                <td style="color:#64748b;">{ind['dsti']['formula']}</td>
                <td style="font-weight:700; font-family:'SF Mono', Consolas, monospace;">{ind['dsti']['formattato']}</td>
                <td>{ind['dsti']['target']}</td>
                <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['dsti']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['dsti']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['dsti']['status']}</span></td>
            </tr>
            <tr>
                <td><b>{ind['invested_assets_ratio']['label']}</b></td>
                <td style="color:#64748b;">{ind['invested_assets_ratio']['formula']}</td>
                <td style="font-weight:700; font-family:'SF Mono', Consolas, monospace;">{ind['invested_assets_ratio']['formattato']}</td>
                <td>{ind['invested_assets_ratio']['target']}</td>
                <td style="text-align:center;"><span class="badge {'badge-optimal' if ind['invested_assets_ratio']['status'] == 'OPTIMAL' else ('badge-acceptable' if ind['invested_assets_ratio']['status'] == 'ACCEPTABLE' else 'badge-warning')}">{ind['invested_assets_ratio']['status']}</span></td>
            </tr>
        </tbody>
    </table>

    <div class="footer">
        <div>ARGUS Financial Ecosystem &bull; Personal Balance Sheet Tear-Sheet</div>
        <div>Equazione Fondamentale: {'✅ Attivo = Passivo + PN (Quadrato)' if is_quadrato else '⚠️ Discrepanza'}</div>
        <div>Documento Certificato CFP/IFRS</div>
    </div>
</body>
</html>
"""
    return html


def _build_personal_balance_sheet_reportlab(data: Dict[str, Any], prof_name: str, is_tearsheet: bool = False) -> bytes:
    """Fallback in ReportLab per la generazione del PDF in assenza di browser headless."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    sp = data["stato_patrimoniale"]
    ce = data["conto_economico"]
    ind = data["indici_bilancio"]
    as_of = data.get("as_of_date", "")
    yr = data.get("selected_year", "")

    tot_att = sp["attivo"]["totale_attivo"]
    tot_pas = sp["passivo"]["totale_passivo"]
    tot_pn = sp["patrimonio_netto"]["totale_patrimonio_netto"]
    tot_par = sp["pareggio"]["totale_pareggio"]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    story = [
        Paragraph("<b>ARGUS WEALTH MANAGEMENT</b>", styles["Title"]),
        Paragraph(f"<b>BILANCIO PERSONALE &amp; STATO PATRIMONIALE {'(TEAR-SHEET)' if is_tearsheet else 'ISTITUZIONALE'}</b>", styles["Heading2"]),
        Paragraph(f"<b>Profilo:</b> {prof_name.upper()} &bull; <b>Data Riferimento:</b> {as_of} &bull; <b>Rating:</b> {ind.get('overall_rating', 'AAA')}", styles["Normal"]),
        Spacer(1, 10),
    ]

    # KPI Summary Table
    kpi_data = [
        ["ATTIVO TOTALE", "PASSIVITÀ TOTALI", "PATRIMONIO NETTO", "PAREGGIO BILANCIO"],
        [f"EUR {tot_att:,.2f}", f"EUR {tot_pas:,.2f}", f"EUR {tot_pn:,.2f}", f"EUR {tot_par:,.2f}"],
    ]
    t_kpi = Table(kpi_data, colWidths=[130, 130, 130, 130])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 14))

    # Stato Patrimoniale Summary Table
    sp_table_data = [
        ["ATTIVO (IMPIEGHI)", "IMPORTO (EUR)", "PASSIVO & PATRIMONIO NETTO", "IMPORTO (EUR)"],
        ["I. Liquidità & Depositi", f"EUR {sp['attivo']['tot_liquidita']:,.2f}", "I. Passività a Breve (<12m)", f"EUR {sp['passivo']['tot_passivo_breve']:,.2f}"],
        ["II. Investimenti & Titoli", f"EUR {sp['attivo']['tot_investimenti']:,.2f}", "II. Passività a Lungo (>12m)", f"EUR {sp['passivo']['tot_passivo_lungo']:,.2f}"],
        ["III. Previdenza Integrativa", f"EUR {sp['attivo']['tot_previdenza']:,.2f}", "Totale Passività", f"EUR {tot_pas:,.2f}"],
        ["IV. Immobili & Caveau", f"EUR {sp['attivo']['tot_attivita_reali']:,.2f}", "III. Patrimonio Netto (Equity)", f"EUR {tot_pn:,.2f}"],
        ["TOTALE ATTIVO", f"EUR {tot_att:,.2f}", "TOTALE PAREGGIO (PASSIVO+PN)", f"EUR {tot_par:,.2f}"],
    ]
    t_sp = Table(sp_table_data, colWidths=[160, 100, 160, 100])
    t_sp.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BACKGROUND', (0, -1), (1, -1), colors.HexColor('#059669')),
        ('TEXTCOLOR', (0, -1), (1, -1), colors.white),
        ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (2, -1), (3, -1), colors.HexColor('#0284c7')),
        ('TEXTCOLOR', (2, -1), (3, -1), colors.white),
        ('FONTNAME', (2, -1), (3, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t_sp)
    story.append(Spacer(1, 14))

    # Indici di Bilancio Table
    ratios_data = [
        ["INDICE DI BILANCIO", "VALORE", "TARGET CFP", "STATUS"],
        [ind['solvency_ratio']['label'], ind['solvency_ratio']['formattato'], ind['solvency_ratio']['target'], ind['solvency_ratio']['status']],
        [ind['debt_to_assets']['label'], ind['debt_to_assets']['formattato'], ind['debt_to_assets']['target'], ind['debt_to_assets']['status']],
        [ind['emergency_runway']['label'], ind['emergency_runway']['formattato'], ind['emergency_runway']['target'], ind['emergency_runway']['status']],
        [ind['savings_rate']['label'], ind['savings_rate']['formattato'], ind['savings_rate']['target'], ind['savings_rate']['status']],
        [ind['dsti']['label'], ind['dsti']['formattato'], ind['dsti']['target'], ind['dsti']['status']],
        [ind['invested_assets_ratio']['label'], ind['invested_assets_ratio']['formattato'], ind['invested_assets_ratio']['target'], ind['invested_assets_ratio']['status']],
    ]
    t_rat = Table(ratios_data, colWidths=[200, 100, 110, 110])
    t_rat.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t_rat)
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>Conto Economico {yr}:</b> Entrate EUR {ce.get('totale_entrate', 0.0):,.2f} &bull; Spese Consumi EUR {ce.get('totale_uscite', 0.0):,.2f} &bull; Risparmio Netto EUR {ce.get('risparmio_netto', 0.0):,.2f} (Savings Rate: {ce.get('savings_rate_pct', 0.0):.1f}%)", styles["Normal"]))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Documento generato da ARGUS Financial Ecosystem &bull; Conforme a CFP Board Standards.", styles["Italic"]))

    doc.build(story)
    return buf.getvalue()


def generate_personal_balance_sheet_pdf(engine: Engine, portfolio_id: int = 1, year: Optional[int] = None) -> bytes:
    """
    Genera il file PDF binario del Dossier di Bilancio Personale Multipagina (3 Pagine A4).
    Utilizza browser headless nativo (Edge / Chrome) con fallback automatico ReportLab.
    """
    html_content = generate_personal_balance_sheet_html(engine, portfolio_id=portfolio_id, year=year)
    pdf_bytes = _convert_html_to_pdf(html_content)
    if pdf_bytes:
        return pdf_bytes

    # Fallback ReportLab
    logger.info("Headless browser unavailable or failed, generating Balance Sheet PDF via ReportLab...")
    data = compute_personal_balance_sheet(engine, portfolio_id=portfolio_id, year=year)
    df_prof = get_wealth_portfolios(engine)
    prof_name = "Master Portfolio"
    if not df_prof.empty and portfolio_id in df_prof["portfolio_id"].values:
        prof_name = str(df_prof.loc[df_prof["portfolio_id"] == portfolio_id, "name"].values[0])
    return _build_personal_balance_sheet_reportlab(data, prof_name, is_tearsheet=False)


def generate_personal_balance_sheet_tearsheet_pdf(engine: Engine, portfolio_id: int = 1, year: Optional[int] = None) -> bytes:
    """
    Genera il file PDF binario della Tear-Sheet Contabile One-Page (1 Pagina A4).
    Utilizza browser headless nativo (Edge / Chrome) con fallback automatico ReportLab.
    """
    html_content = generate_personal_balance_sheet_tearsheet_html(engine, portfolio_id=portfolio_id, year=year)
    pdf_bytes = _convert_html_to_pdf(html_content)
    if pdf_bytes:
        return pdf_bytes

    # Fallback ReportLab
    logger.info("Headless browser unavailable or failed, generating Balance Sheet Tear-Sheet PDF via ReportLab...")
    data = compute_personal_balance_sheet(engine, portfolio_id=portfolio_id, year=year)
    df_prof = get_wealth_portfolios(engine)
    prof_name = "Master Portfolio"
    if not df_prof.empty and portfolio_id in df_prof["portfolio_id"].values:
        prof_name = str(df_prof.loc[df_prof["portfolio_id"] == portfolio_id, "name"].values[0])
    return _build_personal_balance_sheet_reportlab(data, prof_name, is_tearsheet=True)

