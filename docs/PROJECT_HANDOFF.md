# Investment Risk BI Platform — Project Handoff

> File di contesto per riprendere il progetto in una nuova conversazione con un'AI o per presentare l'architettura aggiornata del sistema alla commissione d'esame.
> Incolla questo intero documento come contesto per ripartire istantaneamente.

---

## 1. Contesto Generale e Obiettivi del Capstone Project

**Studente**: Master in Data Analytics (Italia), specializzazione Finanza Quantitativa & Risk Management.

**Stack Tecnologico Richiesto**:
- **Python 3.11+**: Motore ETL, Risk Engine quantitativo, Modelli AI/ML, Generazione PDF/Excel.
- **SQL & MySQL 8.0 (SQLAlchemy ORM)**: Data Warehouse relazionale, tabelle transazionali e storicizzazione snapshot.
- **Streamlit**: Application Web Frontend interattiva per la demo live (6 pagine con interfaccia quantitativa ad alta densità).
- **Power BI & Google Looker Studio**: Executive Dashboards per il reporting direzionale aziendale.
- **Excel (`openpyxl`/`xlsxwriter`)**: Modello tattico di simulazione what-if esportato in-memory.
- **Docker & Docker Compose**: Containerizzazione completa dell'infrastruttura (App Streamlit + Database MySQL).

**Obiettivo del Progetto**:
Costruire una piattaforma di Business Intelligence e Risk Management generica, modulare e riutilizzabile per l'analisi avanzata di portafogli d'investimento multi-asset. Il sistema prende in input uno storico transazioni grezzo (CSV generico o export broker DeGiro), lo arricchisce con dati di mercato reali e genera un quadro quantitativo di rischio/rendimento di livello istituzionale.

**Differenziatore Chiave**:
Il sistema è stato testato e validato su un **dataset di transazioni REALI** (~400 operazioni reali dal 2021 al 2026 dal progetto WealthApp), dimostrando una precisione centesimale nel calcolo di PnL e metriche di rischio in presenza di casi limite reali (dividendi frazionati, cambi valuta EUR/USD/GBP/DKK, acquisti/vendite parziali).

---

## 2. Architettura Completa del Sistema

```text
CSV / DeGiro ──┐
               ├──► core/validator.py ──► core/schemas.py ──► core/fetcher.py ──► MySQL ORM ──► core/risk_engine.py
yfinance API ──┘                           (Pydantic)         (FX / ISIN)      (models.py)          │
                                                                                                    ▼
Power BI / Looker Studio ◄─── core/exporter.py ◄─── core/db_exporter.py ◄─── Presentation Layer (Streamlit App)
                               (CSV Export)         (MySQL Snapshots)        ├── PDF Tear-Sheet (pdf_generator.py)
                                                                             └── Excel What-If (excel_generator.py)
```

---

## 3. Stato di Sviluppo dei Moduli Python (v5.0)

Tutti i moduli sorgente sono stati sviluppati, ottimizzati e verificati con una suite di test automatizzati (**36/36 PyTest PASSED**):

### `core/tax_engine.py` — ✅ Completo (Nuovo Modulo v5.0)
- **Calcolo Imposte secondo Normativa Italiana (TUIR Art. 67)**: Applica la tassazione al 12.5% sui Titoli di Stato (BTP, BOT, Treasury) ed al 26% su Azioni, Obbligazioni societarie, ETF e Cripto.
- **Regola Distintiva ETF vs Titoli Singoli**: Riconosce che le plusvalenze da ETF costituiscono *Redditi di Capitale* e **non possono essere utilizzate per abbattere le minusvalenze** presenti nello zainetto fiscale (*Redditi Diversi*).
- **Diagnostica Dinamica per Anno Solare**: Ripartizione temporale dinamica per ciascun anno solare (2021 — 2026) con menu a tendina interattivo in Streamlit.
- **Tax-Loss Harvesting Advisor**: Identificazione delle posizioni in perdita latente da liquidare prima di fine anno fiscale con indicazione dello stato di compensabilità.

### `scripts/export_star_schema.py` — ✅ Completo (Nuovo Modulo v5.0)
- **Generatore Pacchetto ZIP Star Schema per Power BI**: Creazione in-memory dell'archivio `.zip` contenente le 3 tabelle relazionali Star Schema (`dim_assets.csv`, `fact_positions.csv`, `fact_portfolio_summary.csv`) ed il manuale d'importazione `README_POWERBI.md` per Microsoft Power BI e Google Looker Studio.

### `core/hedging.py` — ✅ Completo
- **Beta-Neutral Hedging Engine**: Calcola il valore e le quote esatte di ETF Inversi (`SH`, `PSQ`, `DOG`, `VIXY`) per portare il Beta di portafoglio da $\beta_p$ a $\beta = 0.00$ senza liquidare gli asset.
- **Tail Risk Protection**: Stima della copertura di protezione da eventi estremi di coda basata sul VaR 99%.

### `core/attribution.py` — ✅ Completo (Nuovo Modulo)
- **Brinson-Fachler Performance Attribution**: Modello istituzionale per la scomposizione dell'extra-rendimento di portafoglio rispetto al benchmark nei 3 fattori: **Allocation Effect** (decisioni settoriali), **Selection Effect** (selezione dei titoli) ed **Interaction Effect**.

### `core/risk_limits.py` — ✅ Completo (Nuovo Modulo)
- **Risk Limits & Early Warning Engine**: Valutazione in tempo reale di 6 regole di rischio istituzionali (Peso max singola posizione ≤ 20%, Concentrazione settoriale ≤ 35%, VaR 95% ≤ 3%, Beta ≤ 1.25, Diversification Ratio ≥ 1.20, HHI ≤ 0.25). Calcolo del tasso di conformità (%) e classificazione a semaforo (`PASS`, `WARNING`, `BREACH`).

### `core/advisor.py` — ✅ Completo
- **Health Score Quantitativo (0-100)**: Punteggio sintetico di salute del portafoglio calcolato analizzando concentrazione HHI, contributi al rischio di perdita estrema (Component VaR > 25%), multipli di valutazione elevati (P/E > 45x) ed opportunità di incremento dello Sharpe Ratio via Markowitz.
- **Filtering Posizioni Attive**: Scansione tassativamente ristretta alle sole posizioni attualmente detenute (`qty_net > 0`), escludendo i ticker chiusi in passato.

### `core/rebalancer.py` — ✅ Completo
- **Smart Rebalancing Engine**: Generatore esatto di ordini di trading ($BUY / SELL$) per l'allineamento a strategie *Markowitz Max Sharpe*, *Min Volatility*, *Equal Weight* o *Custom*.
- **Gestione Cassa & Arrotondamenti**: Inserimento/prelievo di liquidità (+/- €), calcolo su prezzi reali di mercato (`last_price`), arrotondamento ad azioni intere e stima del buffer di cassa residuo.

### `core/dividend_engine.py` — ✅ Completo (Nuovo Modulo)
- **Proiezione Flusso di Cassa & Dividendi**: Parsing esatto dei tassi di dividendo, calcolo del Dividend Yield medio di portafoglio e separazione tra **Dividendi Storici Reali Incassati (€)** ed **Incasso Dividendi Stima Annua (€)**.
- **Calendario Stagionalità per Azienda**: Generazione della distribuzione mensile dei dividendi mappata sul calendario reale di stacco delle singole aziende pagatrici, con dettaglio delle società e quote in € per ogni mese.

### `core/report_exporter.py` — ✅ Completo (Nuovo Modulo)
- **Report Executive PDF (Factsheet 2 Pagine)**: Generazione in-memory con ReportLab di un factsheet istituzionale sintetico.
- **Workbook Excel Multi-Tab (.xlsx)**: Generazione tramite `xlsxwriter` di un file Excel completo articolato su 4 schede: *Executive Summary*, *Posizioni Dettaglio*, *Rendimenti Storici* e *Stress Testing*, con allineamento vettoriale `.values` senza disallineamenti di indice.

### `core/db_exporter.py` & `src/pages/7_📊_Analisi_Temporale.py` — ✅ Completo (Nuovo Modulo & Vista)
- **Analisi Temporale Multi-Snapshot**: Recupero dal database MySQL dello storico degli snapshot salvati (`portfolio_snapshots` e `snapshot_positions`) con routing dinamico del DB (`investment_risk_bi` vs `wealth`).
- **Time-Series & Snapshot Comparison**: Visualizzazione interattiva su Plotly delle serie storiche e confronto affiancato tra due snapshot con $\Delta$ Cards, pie charts comparativi e tabella posizioni a livello di singolo ticker.

### `core/validator.py` — ✅ Completo
Pipeline di bonifica in 11 passaggi per la normalizzazione di date (ISO 8601 `YYYY-MM-DD`), valute, quantitativi e tipi transazione (`buy`, `sell`, `dividend`).

### `core/adapters/degiro.py` — ✅ Completo
Adapter dedicato per il parsing e la conversione automatica delle esportazioni CSV native del broker **DeGiro** nello schema unificato dell'applicazione.

### `core/fetcher.py` — ✅ Completo
Gestore dell'ingestione da `yfinance` con lookback di 365 giorni antecedenti la prima transazione, mapping ISIN $\rightarrow$ Ticker automatico via `config.json` e conversione automatica di tutte le serie storiche verso la valuta di base selezionata (EUR, USD, GBP, CHF). Scrittura su MySQL con clausola `INSERT IGNORE`.

### `core/models.py` — ✅ Completo
Classi ORM dichiarative SQLAlchemy (`Portfolio`, `Asset`, `Transaction`, `MarketPrice`, `PortfolioSnapshot`, `SnapshotPosition`) che mappano integralmente il database MySQL.

### `core/risk_engine.py` — ✅ Completo (Motore Quantitativo v3.5)
- **FIFO Engine (`_fifo_engine`)**: Gestione a code FIFO per il calcolo esatto del costo medio ponderato di carico e separazione tra PnL realizzato e non realizzato.
- **Rischio di Mercato**: Volatilità annualizzata, Skewness, Kurtosis, Tracking Error, Ulcer Index (UI) & Recovery Analysis.
- **Value at Risk & CVaR**: VaR Storico, Parametrico e Cornish-Fisher con riscalamento temporale $\sqrt{T}$ ed Expected Shortfall.
- **Validazione VaR (Kupiec Backtest)**: Backtest su 252 giorni di negoziazione con classificazione regolamentare a semaforo dell'Accordo di Basilea (*Verde/Giallo/Rosso*).
- **Ottimizzazione di Markowitz esatta**: Risoluzione della Frontiera Efficiente (Max Sharpe e Min Volatility) via `SciPy SLSQP` e stima della matrice di covarianza con **Ledoit-Wolf Shrinkage** (`sklearn.covariance.LedoitWolf`).
- **Simulazione Monte Carlo**: 10.000 cammini casuali distribuiti su 252 giorni basati su Moto Browniano Geometrico con **Decomposizione di Cholesky**.
- **Style Analysis Fama-French**: Modello a 3 fattori per determinare $\alpha_{FF}$, Market Beta, Size SMB tilt e Value HML tilt.
- **Stress Testing Storico e Custom**: 5 scenari reali (*Dot-Com*, *Lehman*, *US Downgrade*, *COVID*, *Rate Shock*) e simulatore custom Beta Shock Waterfall.

---

## 4. Cronologia dei Bug Critici Risolti

1. **Dividendi Azzerati dal Validator**: Rimosso il vecchio step che azzerava la quantità dei dividendi. I dividendi in formato `quantity=1` e `price=totale` sono mantenuti intatti.
2. **Parsing Dividend Yield < 1%**: Risolta l'errata interpretazione dei tassi percentuali inferiori all'1% (es. GOOGL 0.26%, BABA 0.90%, MSFT 0.95%) che venivano scambiati per fattori decimali ($0.26 = 26\%$). Ora tutti i tassi vengono divisi per 100 per un calcolo impeccabile.
3. **Mappatura Prezzi Ribilanciatore**: Sostituita la lettura di `row.get("price")` con la colonna ufficiale `row.get("last_price")` collegando l'engine `core/rebalancer.py`. Elimina il fallback di € 1.00 per azione.
4. **Filtraggio Ticker Advisor**: Limitata la scansione dell'advisor alle sole posizioni attive con `qty_net > 0`, rimuovendo la notifica di multipli elevati su ticker chiusi in passato (`PLTR`, `PINS`, `TSLA`).
5. **Indice Multi-Tab Excel**: Allineate le serie dei rendimenti storici tramite estrazione vettoriale `.values` (`sr_bm.reindex(sr_port.index).fillna(0.0).values`), risolvendo il bug `Length of values (5099) does not match length of index (1436)`.
6. **KeyError Schema Dividendi**: Definita la struttura colonne completa anche su DataFrame vuoti e filtraggio preventivo in UI per prevenire eccezioni di Pandas.

---

## 5. Suite di Test Automatizzati (PyTest)

La suite di test verifica l'integrità dell'applicazione ad ogni modifica (**31 / 31 test PASSED**):

```bash
pytest
```
- **Test Ingestione & Schemi**: `test_validator.py`, `test_enhancements.py` (schema validation)
- **Test Engine Quantitativo**: `test_risk_engine.py`, `test_var_cvar.py`, `test_var_backtest.py`, `test_var_lookback.py`, `test_diversification.py`
- **Test Modelli & Ottimizzazione**: `test_optimization.py`, `test_kmeans_elbow.py`, `test_monte_carlo_ui.py`, `test_custom_stress.py`, `test_backtest.py`
- **Test Moduli Istituzionali**: `test_rebalancer_and_advisor.py` (Rebalancer, Quant Advisor, Dividend Forecast, PDF & Excel Exporters)
- **Test Analisi Temporale**: `test_history_analytics.py`
- **Test Esportazione & Reporting**: `test_excel.py`, `test_enhancements.py` (PDF generation)
- **Test Smoke UI Streamlit**: `test_frontend_smoke.py`

---

## 6. Prossimi Passi Consigliati (Post-Capstone)

1. **Integrazione API Broker Live**: Estendere l'ingestione tramite API dirette (es. Interactive Brokers API o Plaid) per azzerare l'importazione manuale da CSV.
2. **Supporto Benchmark Multi-Indice**: Slegare il benchmark di default `SPY` (S&P 500) consentendo la selezione di indici globali configurabili (es. MSCI World `URTH`, NASDAQ `QQQ`, FTSE MIB).
3. **Scheduler Job di Ingestione (APScheduler)**: Attivare il livello 2 di automazione per il sync notturno dei prezzi e l'invio automatico di alert email via webhook.
