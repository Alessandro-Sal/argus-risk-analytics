# ============================================================
# core/wealth/personal_balance_sheet.py
# ARGUS — Personal Balance Sheet & Financial Statements Engine
# Bilancio Personale Istituzionale conforme agli standard CFP & Private Banking
# ============================================================

import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sqlalchemy import Engine, text as sqlt

from core.wealth.wealth_models import (
    NetWorthSummary,
    AccountType,
    CategoryNature,
    PhysicalAssetCategory,
)
from core.wealth.wealth_db import (
    get_wealth_accounts,
    get_cashflow_records,
    get_physical_assets,
    get_pension_plans,
    get_linked_risk_portfolios,
)
from core.terminal_engine import get_fx_rate_to_eur

logger = logging.getLogger("personal_balance_sheet")


def compute_personal_balance_sheet(
    engine: Engine,
    portfolio_id: int = 1,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Costruisce il Bilancio Personale Istituzionale completo:
    1. Stato Patrimoniale a sezioni contrapposte (Attivo vs Passivo + Patrimonio Netto a pareggio)
    2. Conto Economico di gestione per l'anno selezionato (Entrate vs Spese di vita = Risparmio Netto)
    3. Rendiconto di Allocazione del Capitale (Flussi investiti vs Risparmio liquido)
    4. Indici di Bilancio Personale con benchmark Private Banking e rating di solidità
    """
    as_of_str = date.today().strftime("%d/%m/%Y")
    as_of_iso = date.today().strftime("%Y-%m-%d")

    # ==========================================================
    # 1. ACQUISIZIONE DATI DA DATABASE
    # ==========================================================
    df_acc = get_wealth_accounts(engine, portfolio_id=portfolio_id)
    df_phys = get_physical_assets(engine, portfolio_id=portfolio_id)
    df_pens = get_pension_plans(engine, portfolio_id=portfolio_id)
    df_cf = get_cashflow_records(engine, portfolio_id=portfolio_id)

    # Normalizzazione Valutaria EUR per Conti
    if not df_acc.empty:
        if "currency" in df_acc.columns:
            df_acc["balance_eur"] = df_acc.apply(
                lambda r: float(r.get("balance", 0.0) or 0.0) * get_fx_rate_to_eur(str(r.get("currency", "EUR"))),
                axis=1
            )
        else:
            df_acc["balance_eur"] = df_acc["balance"].astype(float)
    else:
        df_acc = pd.DataFrame(columns=["account_id", "name", "account_type", "balance", "balance_eur", "currency"])

    # Normalizzazione Valutaria EUR per Asset Fisici
    if not df_phys.empty:
        if "currency" in df_phys.columns:
            df_phys["market_val_eur"] = df_phys.apply(
                lambda r: float(r.get("current_market_value", 0.0) or 0.0) * get_fx_rate_to_eur(str(r.get("currency", "EUR"))),
                axis=1
            )
        else:
            df_phys["market_val_eur"] = df_phys["current_market_value"].astype(float)
    else:
        df_phys = pd.DataFrame(columns=["asset_id", "name", "asset_category", "current_market_value", "market_val_eur", "currency"])

    # Normalizzazione Valutaria EUR per Previdenza
    if not df_pens.empty:
        if "currency" in df_pens.columns:
            df_pens["accum_eur"] = df_pens.apply(
                lambda r: float(r.get("accumulated_value", 0.0) or 0.0) * get_fx_rate_to_eur(str(r.get("currency", "EUR"))),
                axis=1
            )
        else:
            df_pens["accum_eur"] = df_pens["accumulated_value"].astype(float)
    else:
        df_pens = pd.DataFrame(columns=["plan_id", "plan_name", "provider", "accumulated_value", "accum_eur", "currency"])

    # ==========================================================
    # 2. STATO PATRIMONIALE PERSONALE (STATEMENT OF FINANCIAL POSITION)
    # ==========================================================

    # --- A. ATTIVO: SEZIONE I - ATTIVITÀ LIQUIDE & EQUIVALENTI ---
    liquid_voci = []
    liquid_types = [AccountType.CHECKING.value, AccountType.SAVINGS.value, AccountType.EMERGENCY_FUND.value]
    df_liquid_acc = df_acc[df_acc["account_type"].isin(liquid_types) & (df_acc["balance_eur"] > 0)]
    for _, r in df_liquid_acc.iterrows():
        tipo_lbl = "Conto Corrente" if r["account_type"] == AccountType.CHECKING.value else (
            "Fondo Emergenza" if r["account_type"] == AccountType.EMERGENCY_FUND.value else "Conto Deposito"
        )
        liquid_voci.append({
            "nome": r.get("account_name") or r.get("name") or "Conto Bancario",
            "categoria": tipo_lbl,
            "dettaglio": f"{r.get('institution', 'Banca')} ({r.get('currency', 'EUR')})",
            "valore": round(float(r["balance_eur"]), 2)
        })

    brokerage_cash = df_acc[df_acc["account_type"].isin([AccountType.BROKERAGE_CASH.value, "brokerage", "trading"]) & (df_acc["balance_eur"] > 0)]
    for _, r in brokerage_cash.iterrows():
        liquid_voci.append({
            "nome": r.get("account_name") or r.get("name") or "Liquidità Broker",
            "categoria": "Liquidità su Broker/Trading",
            "dettaglio": f"{r.get('institution', 'Broker')} (Cassa non investita)",
            "valore": round(float(r["balance_eur"]), 2)
        })

    tot_liquidita = sum(v["valore"] for v in liquid_voci)

    # --- A. ATTIVO: SEZIONE II - INVESTIMENTI FINANZIARI & CAPITALE PRODUTTIVO ---
    invest_voci = []
    active_risk_pids = []
    try:
        active_risk_pids = get_linked_risk_portfolios(engine, wealth_portfolio_id=portfolio_id)
    except Exception:
        active_risk_pids = []

    # Recupera i portafogli collegati da portfolios / snapshot
    if active_risk_pids:
        try:
            with engine.connect() as conn:
                p_placeholders = ",".join([f":p{i}" for i in range(len(active_risk_pids))])
                params = {f"p{i}": int(pid) for i, pid in enumerate(active_risk_pids)}
                q = f"""
                    SELECT p.portfolio_id, p.name, p.description, s.total_value
                    FROM portfolios p
                    LEFT JOIN (
                        SELECT portfolio_id, total_value
                        FROM portfolio_snapshots
                        WHERE snapshot_id IN (
                            SELECT MAX(snapshot_id) FROM portfolio_snapshots WHERE portfolio_id IN ({p_placeholders}) GROUP BY portfolio_id
                        )
                    ) s ON p.portfolio_id = s.portfolio_id
                    WHERE p.portfolio_id IN ({p_placeholders})
                """
                res = conn.execute(sqlt(q), params).mappings().fetchall()
                for row in res:
                    val = float(row.get("total_value") or 0.0)
                    p_name = row.get("name") or f"Portafoglio Risk #{row.get('portfolio_id')}"
                    cat_lbl = "Cripto-attività" if "cripto" in p_name.lower() or "crypto" in p_name.lower() else "Portafoglio Titoli & Azioni"
                    if val > 0:
                        invest_voci.append({
                            "nome": p_name,
                            "categoria": cat_lbl,
                            "dettaglio": row.get("description") or "Portafoglio Quantitativo / Risk Modulo",
                            "valore": round(val, 2)
                        })
        except Exception as e:
            logger.warning(f"Errore caricamento dettagli portafogli collegati: {e}")

    # Se non ci sono voci da risk portfolio ma ci sono conti tipo investment
    if not invest_voci:
        df_inv_acc = df_acc[df_acc["account_type"].isin(["investment", "investments", "crypto_exchange"]) & (df_acc["balance_eur"] > 0)]
        for _, r in df_inv_acc.iterrows():
            invest_voci.append({
                "nome": r.get("account_name") or r.get("name") or "Investimento Finanziario",
                "categoria": "Titoli & Cripto",
                "dettaglio": r.get("institution", "Intermediario"),
                "valore": round(float(r["balance_eur"]), 2)
            })

    tot_investimenti = sum(v["valore"] for v in invest_voci)

    # --- A. ATTIVO: SEZIONE III - PREVIDENZA & RISPARMIO DI LUNGO TERMINE ---
    previdenza_voci = []
    for _, r in df_pens.iterrows():
        p_val = round(float(r["accum_eur"]), 2)
        if p_val > 0:
            previdenza_voci.append({
                "nome": r.get("plan_name") or "Fondo Pensione Integrativo",
                "categoria": "Fondo Pensione / PIP",
                "dettaglio": f"{r.get('provider', 'Gestore')} — Contributo: €{float(r.get('employer_monthly_contribution', 0.0) or 0.0):,.2f}/m",
                "valore": p_val
            })
    tot_previdenza = sum(v["valore"] for v in previdenza_voci)

    # --- A. ATTIVO: SEZIONE IV - ATTIVITÀ REALI & IMMOBILIZZAZIONI PERSONALI ---
    reali_voci = []
    for _, r in df_phys.iterrows():
        cat = str(r.get("asset_category", "")).lower()
        cat_lbl = "Beni di Pregio & Orologi" if "watch" in cat else (
            "Metalli Preziosi & Oro" if "metal" in cat else (
                "Immobile di Proprietà" if "estate" in cat else "Beni Personali di Valore"
            )
        )
        val = round(float(r["market_val_eur"]), 2)
        if val > 0:
            reali_voci.append({
                "nome": r.get("name") or "Asset Fisico",
                "categoria": cat_lbl,
                "dettaglio": f"{r.get('location', '')} {r.get('notes', '')}".strip() or "Valutazione Peritale / Stima Mercato",
                "valore": val
            })
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
            "voci": liquid_voci
        },
        {
            "codice": "II",
            "titolo": "Investimenti Finanziari & Capitale Produttivo",
            "descrizione": "Azioni, ETF, Titoli obbligazionari, Cripto-attività e portafogli gestiti",
            "totale": tot_investimenti,
            "incidenza_pct": round(tot_investimenti / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": invest_voci
        },
        {
            "codice": "III",
            "titolo": "Previdenza & Risparmio Previdenziale",
            "descrizione": "Fondi pensione negoziali, aperti, PIP e accantonamenti pensionistici",
            "totale": tot_previdenza,
            "incidenza_pct": round(tot_previdenza / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": previdenza_voci
        },
        {
            "codice": "IV",
            "titolo": "Attività Reali & Beni Personali",
            "descrizione": "Immobili di proprietà, collezionabili di lusso, orologi e metalli preziosi",
            "totale": tot_attivita_reali,
            "incidenza_pct": round(tot_attivita_reali / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": reali_voci
        }
    ]
    if tot_crediti > 0:
        sezioni_attivo.append({
            "codice": "V",
            "titolo": "Crediti Personali & Ratei Attivi",
            "descrizione": "Crediti personali esigibili, crediti d'imposta personali e depositi cauzionali",
            "totale": tot_crediti,
            "incidenza_pct": round(tot_crediti / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": crediti_voci
        })

    # --- B. PASSIVO & DEBITI PERSONALI (LIABILITIES) ---
    passivo_breve_voci = []
    passivo_lungo_voci = []

    if not df_acc.empty:
        # Debiti da carte di credito
        df_cc = df_acc[df_acc["account_type"] == AccountType.CREDIT_CARD.value]
        for _, r in df_cc.iterrows():
            val = abs(float(r["balance_eur"]))
            if val > 0:
                passivo_breve_voci.append({
                    "nome": r.get("account_name") or r.get("name") or "Carta di Credito",
                    "categoria": "Debito Carta di Credito (Saldo fine mese)",
                    "dettaglio": r.get("institution", "Istituto emittente"),
                    "valore": round(val, 2)
                })

        # Scoperti di conto corrente (balance < 0)
        df_scoperti = df_acc[(~df_acc["account_type"].isin([AccountType.CREDIT_CARD.value, AccountType.LOAN.value, AccountType.MORTGAGE.value])) & (df_acc["balance_eur"] < 0)]
        for _, r in df_scoperti.iterrows():
            val = abs(float(r["balance_eur"]))
            passivo_breve_voci.append({
                "nome": f"Scoperto {r.get('name', 'Conto')}",
                "categoria": "Scoperto di Conto Corrente",
                "dettaglio": "Saldo operativo a debito",
                "valore": round(val, 2)
            })

        # Mutui e finanziamenti a lungo termine
        df_mutui = df_acc[df_acc["account_type"].isin([AccountType.MORTGAGE.value, AccountType.LOAN.value])]
        for _, r in df_mutui.iterrows():
            val = abs(float(r["balance_eur"]))
            if val > 0:
                cat_lbl = "Mutuo Ipotecario Residuo" if r["account_type"] == AccountType.MORTGAGE.value else "Finanziamento / Prestito Personale"
                passivo_lungo_voci.append({
                    "nome": r.get("account_name") or r.get("name") or "Finanziamento",
                    "categoria": cat_lbl,
                    "dettaglio": f"{r.get('institution', 'Banca')} (Debito residuo quota capitale)",
                    "valore": round(val, 2)
                })

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
            "voci": passivo_breve_voci
        },
        {
            "codice": "II",
            "titolo": "Passività Consolidate a Medio/Lungo Termine (> 12 mesi)",
            "descrizione": "Mutui ipotecari residui (prima casa/altri immobili), prestiti personali, finanziamenti auto",
            "totale": tot_passivo_lungo,
            "incidenza_pct": round(tot_passivo_lungo / totale_attivo * 100, 2) if totale_attivo > 0 else 0.0,
            "voci": passivo_lungo_voci
        }
    ]

    # --- C. PATRIMONIO NETTO PERSONALE (NET WORTH / EQUITY) ---
    patrimonio_netto = round(totale_attivo - totale_passivo, 2)
    totale_pareggio = round(totale_passivo + patrimonio_netto, 2)
    is_quadrato = abs(totale_attivo - totale_pareggio) < 0.01

    # ==========================================================
    # 3. CONTO ECONOMICO PERSONALE (PERSONAL INCOME STATEMENT)
    # ==========================================================
    available_years = []
    if not df_cf.empty:
        df_cf_copy = df_cf.copy()
        df_cf_copy["tx_date"] = pd.to_datetime(df_cf_copy["tx_date"], errors="coerce")
        df_cf_copy = df_cf_copy.dropna(subset=["tx_date"])
        available_years = sorted(df_cf_copy["tx_date"].dt.year.unique().tolist(), reverse=True)

    selected_year = year
    if selected_year is None:
        selected_year = available_years[0] if available_years else date.today().year

    # Filtro transazioni per anno selezionato
    if not df_cf.empty and selected_year is not None:
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
            "descrizione": f"Ricchezza netta consolidata accumulata fino al 31/12/{int(selected_year)-1}",
            "valore": capitale_pregresso,
            "incidenza_pct": round(capitale_pregresso / patrimonio_netto * 100, 2) if patrimonio_netto > 0 else 0.0
        },
        {
            "voce": f"Risultato Economico d'Esercizio ({selected_year})",
            "descrizione": f"Surplus / Risparmio netto generato dalla gestione economica personale nel {selected_year}",
            "valore": risparmio_anno,
            "incidenza_pct": round(risparmio_anno / patrimonio_netto * 100, 2) if patrimonio_netto > 0 else 0.0
        }
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
        ce_data=ce_data
    )

    return {
        "as_of_date": as_of_str,
        "as_of_iso": as_of_iso,
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
                "differenza": round(totale_attivo - totale_pareggio, 2)
            }
        },
        "conto_economico": ce_data,
        "indici_bilancio": indici
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
            "allocazione_capitale": {
                "totale_investimenti": 0.0,
                "voci_investimenti": [],
                "variazione_liquidita": 0.0
            },
            "waterfall_data": []
        }

    df = df_year.copy()
    cat_ser = df["category_name"].astype(str) if "category_name" in df.columns else pd.Series([""] * len(df), index=df.index)
    merch_ser = df["merchant"].astype(str) if "merchant" in df.columns else pd.Series([""] * len(df), index=df.index)
    notes_ser = df["notes"].astype(str) if "notes" in df.columns else pd.Series([""] * len(df), index=df.index)
    nat_ser = df["nature"].astype(str) if "nature" in df.columns else pd.Series([""] * len(df), index=df.index)
    dir_ser = df["direction"].astype(str) if "direction" in df.columns else pd.Series([""] * len(df), index=df.index)

    # 1. Esclusione Giroconti e Trasferimenti Interni
    is_transfer = (
        (dir_ser.str.lower() == "transfer") |
        (nat_ser.str.lower() == "transfer") |
        (cat_ser.str.contains("girocont|trasferiment|sistemazion", case=False, na=False))
    )

    # 2. Identificazione Rimborsi
    is_refund = (
        (cat_ser.str.contains("rimbors|settled from|bulk settlement|storno|reso", case=False, na=False)) |
        (merch_ser.str.contains("settled from|bulk settlement|refund|rimborso", case=False, na=False)) |
        (notes_ser.str.contains(r"\[refund\]|settled from|bulk settlement", case=False, na=False))
    ) & (~is_transfer)

    # 3. Identificazione Flussi di Investimento in Uscita (Capital Allocation, non consumi)
    is_investment_outflow = (
        (dir_ser.str.lower() == "outflow") &
        (
            (nat_ser.str.lower() == "saving_investment") |
            (cat_ser.str.contains("investiment|titoli|azioni|criptovalut|crypto|fondo pensione", case=False, na=False)) |
            (notes_ser.str.contains(r"\[investment\]|acquisto quote|pac", case=False, na=False))
        ) &
        (~is_transfer)
    )

    # 4. ENTRATE (INFLOWS)
    df_in = df[(dir_ser.str.lower() == "inflow") & (~is_transfer)].copy()
    
    # Raggruppamento Entrate
    entrate_voci = []
    
    # A. Lavoro Dipendente, Autonomo & Compensi
    mask_lavoro = df_in["category_name"].str.contains("stipendio|compens|parcell|fattur|premio|tfr|borsa|stage", case=False, na=False)
    tot_lavoro = float(df_in[mask_lavoro]["amount"].sum())
    if tot_lavoro > 0:
        entrate_voci.append({
            "sezione": "Redditi da Lavoro Dipendente & Autonomo",
            "categoria": "Lavoro & Compensi",
            "descrizione": "Stipendi netti, compensi professionali, 13a/14a e borse di studio",
            "valore": round(tot_lavoro, 2)
        })

    # B. Supporto Famiglia & Donazioni
    mask_famiglia = df_in["category_name"].str.contains("supporto famigli|genitor|donazion|regal", case=False, na=False)
    tot_famiglia = float(df_in[mask_famiglia]["amount"].sum())
    if tot_famiglia > 0:
        entrate_voci.append({
            "sezione": "Supporto Famigliare & Donazioni Ricevute",
            "categoria": "Trasferimenti Familiari",
            "descrizione": "Aiuti finanziari, regali e contributi da parte della famiglia",
            "valore": round(tot_famiglia, 2)
        })

    # C. Rendite Finanziarie & Disinvestimenti
    mask_rendite = df_in["category_name"].str.contains("dividend|cedol|interess|investiment|titoli|cripto", case=False, na=False)
    tot_rendite = float(df_in[mask_rendite]["amount"].sum())
    if tot_rendite > 0:
        entrate_voci.append({
            "sezione": "Proventi Finanziari & Rendite di Capitale",
            "categoria": "Rendite di Capitale",
            "descrizione": "Dividendi, cedole, interessi attivi e liquidazioni di asset",
            "valore": round(tot_rendite, 2)
        })

    # D. Rimborsi & Entrate Varie
    mask_altre = (~mask_lavoro) & (~mask_famiglia) & (~mask_rendite)
    tot_altre = float(df_in[mask_altre]["amount"].sum())
    if tot_altre > 0:
        entrate_voci.append({
            "sezione": "Rimborsi Spese & Altre Entrate Straordinarie",
            "categoria": "Rimborsi & Varie",
            "descrizione": "Rimborsi spese saldate da terzi, resi e introiti extra",
            "valore": round(tot_altre, 2)
        })

    totale_entrate = round(float(df_in["amount"].sum()), 2)

    # 5. USCITE / CONSUMI PERSONALI (OUTFLOWS - SPESE DI VITA)
    # Filtriamo le uscite che NON sono trasferimenti e NON sono investimenti (quelli vanno in capital allocation)
    df_out_living = df[(dir_ser.str.lower() == "outflow") & (~is_transfer) & (~is_investment_outflow)].copy()

    uscite_categorie_mapping = [
        ("Abitazione, Affitto & Utenze", ["casa", "affitto", "utenze", "luce", "gas", "condominio", "internet", "spese casa"]),
        ("Spesa Alimentare & Supermercato", ["spesa alimentare", "supermercato", "alimentari"]),
        ("Ristoranti, Serate & Socialità", ["ristoranti", "pizzerie", "sushi", "serate", "bar", "aperitivi"]),
        ("Trasporti, Mobilità & Benzina", ["trasporti", "benzina", "carburante", "mezzi", "autostrada", "parcheggi"]),
        ("Istruzione, Formazione & Libri", ["istruzione", "corsi", "libri", "università", "formazione"]),
        ("Salute, Farmacia & Visite Mediche", ["salute", "farmacia", "visite", "medico", "dentista"]),
        ("Tempo Libero, Viaggi & Eventi", ["tempo libero", "cinema", "eventi", "viaggi", "voli", "vacanze", "hotel"]),
        ("Shopping, Tecnologia & Cura Personale", ["shopping", "abbigliamento", "elettronica", "pc", "gadget", "cura personale", "parrucchiere", "abitudini"]),
        ("Abbonamenti Digitali & Ricorrenti", ["abbonamenti", "streaming", "spotify", "icloud", "netflix"]),
        ("Regali, Eventi & Supporto Famiglia", ["regali", "lauree", "supporto famiglia", "spese per la famiglia"]),
        ("Imposte, Tasse & Commissioni Bancarie", ["tasse", "imposte", "commissioni", "bollo", "canone"]),
        ("Spese Varie & Imprevisti Personali", ["spese varie", "imprevisti"])
    ]

    uscite_voci = []
    matched_indices = set()

    for macro_nome, keywords in uscite_categorie_mapping:
        pat = "|".join(keywords)
        mask = df_out_living["category_name"].str.contains(pat, case=False, na=False) & (~df_out_living.index.isin(matched_indices))
        tot_sub = float(df_out_living[mask]["amount"].sum())
        if tot_sub > 0:
            matched_indices.update(df_out_living[mask].index)
            uscite_voci.append({
                "sezione": macro_nome,
                "categoria": macro_nome.split(",")[0].strip(),
                "valore": round(tot_sub, 2),
                "num_movimenti": int(mask.sum())
            })

    # Eventuali spese residue non mappate
    unmatched_mask = ~df_out_living.index.isin(matched_indices)
    tot_unmatched = float(df_out_living[unmatched_mask]["amount"].sum())
    if tot_unmatched > 0:
        uscite_voci.append({
            "sezione": "Altre Spese Personali Non Classificate",
            "categoria": "Varie",
            "valore": round(tot_unmatched, 2),
            "num_movimenti": int(unmatched_mask.sum())
        })

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
            voci_inv.append({
                "nome": r["category_name"],
                "valore": round(float(r["amount"]), 2)
            })

    # Risparmio Liquido rimasto sul conto dopo gli investimenti eseguiti
    variazione_liquidita = round(risparmio_netto - totale_investimenti, 2)

    # Waterfall data per Plotly
    waterfall_data = [
        {"measure": "relative", "x": "Totale Entrate", "y": totale_entrate},
        {"measure": "relative", "x": "Spese di Vita (Consumi)", "y": -totale_uscite},
        {"measure": "total", "x": "Risparmio Netto", "y": risparmio_netto},
        {"measure": "relative", "x": "Investimenti Eseguiti (PAC/Crypto)", "y": -totale_investimenti},
        {"measure": "total", "x": "Risparmio Liquido Accantonato", "y": variazione_liquidita}
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
            "variazione_liquidita": variazione_liquidita
        },
        "waterfall_data": waterfall_data
    }


def _compute_personal_ratios(
    totale_attivo: float,
    totale_passivo: float,
    patrimonio_netto: float,
    tot_liquidita: float,
    tot_investimenti: float,
    tot_previdenza: float,
    ce_data: Dict[str, Any]
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
    optimal_count = sum(1 for s in [solv_status, debt_status, runway_status, sr_status, dsti_status, inv_status] if s == "OPTIMAL")
    if optimal_count >= 5:
        overall_rating = "AAA (Solidità Finanziaria Istituzionale)"
        overall_desc = "Struttura patrimoniale eccezionale: assenza o controllo totale del debito, elevata liquidità di sicurezza e formidabile capacità di accumulo."
    elif optimal_count >= 3:
        overall_rating = "AA (Solidità Equilibrata)"
        overall_desc = "Ottimo profilo patrimoniale, patrimonio netto ampiamente positivo e gestione equilibrata delle uscite familiari."
    else:
        overall_rating = "A (Profilo in Consolidamento)"
        overall_desc = "Profilo solido con margini di ottimizzazione su riserve di liquidità o quota di asset a reddito."

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
            "descrizione": "Misura la percentuale di patrimonio libero da qualsiasi vincolo o debito verso terzi."
        },
        "debt_to_assets": {
            "valore": debt_assets_val,
            "formattato": f"{debt_assets_val:.1f}%",
            "label": "Debt-to-Assets (Leva)",
            "target": "≤ 30%",
            "formula": "Passività Totali / Attivo Totale",
            "status": debt_status,
            "colore": debt_color,
            "descrizione": "Rapporto tra l'indebitamento complessivo e il totale dei beni posseduti."
        },
        "emergency_runway": {
            "valore": runway_val,
            "formattato": f"{runway_val:.1f} Mesi",
            "label": "Runway Fondo Emergenza",
            "target": "≥ 6 Mesi",
            "formula": "Liquidità Immediata / Spese Mensili Medie",
            "status": runway_status,
            "colore": runway_color,
            "descrizione": "Autonomia finanziaria in caso di azzeramento improvviso di tutte le entrate correnti."
        },
        "savings_rate": {
            "valore": savings_rate_val,
            "formattato": f"{savings_rate_val:.1f}%",
            "label": "Personal Savings Rate",
            "target": "≥ 20%",
            "formula": "Risparmio Netto / Totale Entrate",
            "status": sr_status,
            "colore": sr_color,
            "descrizione": "Percentuale del reddito convertita in nuovo patrimonio anziché consumata in spese correnti."
        },
        "dsti": {
            "valore": dsti_val,
            "formattato": f"{dsti_val:.1f}%",
            "label": "Debt Service-to-Income (DSTI)",
            "target": "≤ 33%",
            "formula": "Rate di Debito Annue / Entrate Totali",
            "status": dsti_status,
            "colore": dsti_color,
            "descrizione": "Percentuale delle entrate assorbita dal rimborso di finanziamenti o mutui."
        },
        "invested_assets_ratio": {
            "valore": invested_ratio_val,
            "formattato": f"{invested_ratio_val:.1f}%",
            "label": "Invested Assets Ratio",
            "target": "≥ 50%",
            "formula": "(Investimenti + Previdenza) / Patrimonio Netto",
            "status": inv_status,
            "colore": inv_color,
            "descrizione": "Percentuale del patrimonio investita in asset finanziari produttivi di rendimento composto."
        }
    }
