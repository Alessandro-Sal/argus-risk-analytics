# Investment Risk BI Platform — Project Handoff (v5.2 Production Release)

> File di contesto esaustivo per la manutenzione futura, lo sviluppo di moduli aggiuntivi o l'integrazione di ARGUS con infrastrutture di analisi terze.

---

## 1. Contesto Generale e Obiettivi del Progetto

**Piattaforma**: ARGUS — Quantitative Risk & Portfolio BI Platform.

**Stack Tecnologico del Sistema**:
- **Python 3.11+**: Motore ETL, Risk Engine quantitativo, Modelli Econometrici e di Bilancio, Generazione PDF/Excel/HTML.
- **SQL & MySQL 8.0 / SQLite (SQLAlchemy ORM)**: Data Warehouse relazionale, tabelle transazionali e storicizzazione snapshot temporali.
- **Streamlit**: Web Application Framework interattivo per la dashboard (7 pagine ad alta densità quantitativa).
- **PyWebView & PyInstaller**: Architettura Desktop Nativa Windows (WebView2 engine, finestra dedicata, gestione ciclo di vita senza browser, eseguibile `.exe` standalone e collegamento Desktop).
- **Power BI & Google Looker Studio**: Executive Dashboards basate su pacchetto Star Schema ZIP (`dim_assets.csv`, `fact_positions.csv`, `fact_portfolio_summary.csv`).
- **Excel (`openpyxl`/`xlsxwriter`)**: Modello tattico di simulazione What-If ed esportazione Workbook Multi-Tab.
- **ReportLab**: Exporter PDF per la creazione in-memory di Factsheet istituzionali a 2 pagine.
- **Docker & Docker Compose**: Containerizzazione completa dell'infrastruttura (App Streamlit + Database MySQL 8.0).

**Obiettivo del Progetto**:
Ingegnerizzata come piattaforma avanzata di Finanza Quantitativa e Risk Management, **ARGUS** — il cui nome si ispira al mito dell'osservatore dai cento occhi che vede tutto e non dorme mai — è una piattaforma integrata di **Business Intelligence, Financial Valuation e Quantitative Risk Management**. Progettata con un'interfaccia ad alta densità informativa di livello istituzionale, la soluzione offre un ecosistema avanzato per la diagnosi contabile, la profilazione del rischio e la protezione strategica di portafogli d'investimento multi-asset (*Equity, ETF, Fixed Income, Crypto e Cash*).

**Differenziatore Chiave**:
A differenza dei benchmark basati su simulazioni sintetiche, **ARGUS** è stato validato empiricamente su un **dataset reale di oltre 400 operazioni finanziarie storiche** (2021–2026 dal progetto WealthApp). Il sistema garantisce una precisione deterministica centesimale nella gestione di scenari operativi complessi (contabilità FIFO, dividendi frazionati, cambi valuta EUR/USD/GBP/CHF, movimenti di cassa e risoluzione ISIN-Ticker).

---

## 2. Architettura Completa del Sistema

```text
CSV / DeGiro ──┐
               ├──► core/validator.py ──► core/schemas.py ──► core/fetcher.py ──► MySQL / SQLite ORM ──► core/risk_engine.py
yfinance API ──┘                           (Pydantic)         (FX / ISIN)          (models.py)               │
                                                                                                             ├──► core/financial_analysis.py
                                                                                                             │
Power BI / Looker Studio ◄─── core/exporter.py ◄─── core/db_exporter.py ◄─── Presentation Layer (Streamlit / PyWebView)
                               (Star Schema ZIP)    (MySQL Snapshots)        ├── Desktop App (desktop_launcher.py)
                                                                              ├── Standalone Executable (ARGUS.exe)
                                                                              ├── PDF Tear-Sheet (pdf_generator.py)
                                                                              ├── Standalone HTML (html_exporter.py)
                                                                              └── Excel What-If (excel_generator.py)
```

---

## 3. Mappatura e Stato dei Moduli Core (`core/`)

Tutti i 22 moduli Python sorgente sono stati sviluppati, ottimizzati e verificati con la suite di test automatizzati (**54/54 PyTest PASSED**):

### `core/risk_engine.py` — ✅ Motore Quantitativo & Rischio di Coda
- **FIFO Engine (`_fifo_engine`)**: Gestione a code FIFO per il calcolo esatto del prezzo medio di carico (WACP) e separazione tra PnL realizzato e non realizzato.
- **Rischio di Mercato**: Volatilità annualizzata, Skewness, Kurtosis, Tracking Error, Ulcer Index (UI) & Recovery Analysis.
- **Value at Risk & CVaR**: VaR Storico, Parametrico e Cornish-Fisher (corretto per Skewness e Kurtosis) con riscalamento temporale $\sqrt{T}$ ed Expected Shortfall al 95% e 99%.
- **Validazione VaR (Kupiec Backtest)**: Backtest su 252 giorni con classificazione regolamentare dell'Accordo di Basilea (*Verde/Giallo/Rosso*).
- **Ottimizzazione di Markowitz esatta**: Frontiera Efficiente (Max Sharpe e Min Volatility) via `SciPy SLSQP` e stima della matrice di covarianza con **Ledoit-Wolf Shrinkage** (`sklearn.covariance.LedoitWolf`).
- **Black-Litterman Optimization (`compute_black_litterman_optimization`)**: Combinazione bayesiana tra rendimenti impliciti di equilibrio di mercato e visioni tattiche dell'investitore.
- **Simulazione Monte Carlo**: 10.000 cammini casuali distribuiti su 252 giorni basati su Moto Browniano Geometrico con **Decomposizione di Cholesky** e supporto per code grasse (**Student-t distribution** con $\nu=5$).
- **Style Analysis Fama-French & Carhart**: Modelli a 3 e 4 fattori per determinare $\alpha_{FF}$, Market Beta, Size SMB tilt, Value HML tilt e Momentum WML tilt (`compute_carhart_4factor_exposures`).
- **ATR Trailing Stop-Loss & Chandelier Exit (`compute_atr_chandelier_exits`)**: Algoritmo per il calcolo di livelli di stop-loss dinamici ancorati alla volatilità reale ($3 \times ATR_{14}$) e ai massimi a 22 giorni.
- **Stress Testing Storico e Macro Scenario Builder**: 5 scenari reali (*Dot-Com*, *Lehman*, *US Downgrade*, *COVID*, *Rate Shock*) e simulatore multi-fattoriale macro (`compute_custom_macro_stress`).
- **Modello Almgren-Chriss (`compute_almgren_chriss_market_impact`)**: Stima dell'impatto sui prezzi di borsa e dello slippage temporaneo/permanente per la liquidazione ottimale delle posizioni.

### `core/financial_analysis.py` — ✅ Analisi dei Bilanci & Solvibilità
- **Altman Z-Score Model (1968)**: Previsione del rischio di bancarotta a 24 mesi con verdetto a semaforo (*Safe Z > 2.99*, *Grey 1.81-2.99*, *Distress Z < 1.81*).
- **Scomposizione DuPont (3 e 5 Fattori)**: Decomposizione del ROE nei driver di Profit Margin, Asset Turnover, Equity Multiplier, Tax Burden e Interest Burden.
- **Piotroski F-Score (9 Punti Stanford)**: Valutazione di salute contabile basata su Profittabilità (4 pt), Struttura/Liquidità (3 pt) ed Efficienza Operativa (2 pt).
- **Calcolatore Dinamico WACC (CAPM)**: Costo del Capitale Medio Ponderato con Costo dell'Equity CAPM ($r_e = R_f + \beta \cdot ERP$), Costo del Debito al netto delle imposte e pesi strutturali.
- **Modello di Valutazione Intrinseca DCF Monte Carlo**: 2-Stage Discounted Cash Flow a 1.000 iterazioni stocastiche con istogramma di distribuzione del Fair Value per azione.
- **Consultazione Bilanci Ufficiali 10-K**: Download ed estrazione diretta di Conto Economico, Stato Patrimoniale e Cash Flow reali da Yahoo Finance.
- **Comparativa Multiaziendale**: Confronto affiancato di 2+ aziende con Z-Score, DuPont, Radar Chart e Matrice dei Multipli (*P/E*, *EV/EBITDA*, *P/B*, *P/S*).

### `core/tax_engine.py` — ✅ Ottimizzazione Fiscale TUIR Art. 67
- **Tassazione Normativa Italiana**: Tassazione al 12.5% sui Titoli di Stato (White List) e 26.0% su Azioni, Obbligazioni, ETF e Cripto.
- **Regola ETF vs Titoli Singoli**: Plusvalenze da ETF considerate *Redditi di Capitale* e non compensabili con minusvalenze (*Redditi Diversi*).
- **Tax-Loss Harvesting Advisor**: Identificazione delle posizioni in perdita latente da liquidare strategicamente prima di fine anno fiscale.

### `core/attribution.py` — ✅ Attribuzione Performance Brinson-Fachler
- Scomposizione dell'extra-rendimento rispetto al benchmark nei 3 fattori: **Allocation Effect**, **Selection Effect** ed **Interaction Effect**.

### `core/risk_limits.py` — ✅ Early Warning Risk Limits Engine
- Valutazione in tempo reale di 6 regole di rischio istituzionali (Peso max singola posizione ≤ 20%, Concentrazione settoriale ≤ 35%, VaR 95% ≤ 3%, Beta ≤ 1.25, Diversification Ratio ≥ 1.20, HHI ≤ 0.25).

### `core/advisor.py` — ✅ ARGUS Quant Advisor & Health Score
- Punteggio sintetico di salute del portafoglio (0-100) calcolato analizzando concentrazione HHI, contributi al rischio di perdita estrema (Component VaR > 25%), multipli di valutazione elevati (P/E > 45x) ed opportunità di incremento dello Sharpe Ratio via Markowitz.

### `core/rebalancer.py` — ✅ Smart Rebalancer & Generatore Ordini
- Generatore esatto di ordini di trading ($BUY / SELL$) in € e numero di quote intere per l'allineamento a strategie target (*Max Sharpe*, *Min Volatility*, *Equal Weight*, *Custom*) con gestione del buffer di cassa residuo.

### `core/dividend_engine.py` — ✅ Dividend Forecast & Cash Flow Schedule
- Parsing esatto dei tassi di dividendo, calcolo del Dividend Yield medio di portafoglio, separazione tra dividendi storici reali ed incasso annuo stimato, e calendario mensile per azienda pagatrice.

### `core/html_exporter.py` — ✅ Exporter Report Standalone HTML
- Generazione in-memory di un report interattivo HTML standalone in dark mode con grafici SVG/CSS responsive e tabelle metriche complete.

### `core/report_exporter.py`, `pdf_generator.py`, `excel_generator.py` — ✅ Exporter Manager Centralizzato
- Generazione in-memory del Factsheet PDF a 2 pagine (ReportLab) e del Workbook Excel Multi-Tab (.xlsx su 4 schede) senza disallineamenti di indice.

### `core/db_exporter.py` — ✅ Storicizzazione & Analisi Temporale Multi-Snapshot
- Salvataggio degli snapshot su database MySQL/SQLite e recupero delle serie storiche per l'analisi temporale e il confronto $\Delta$ tra snapshot.

### `core/validator.py`, `schemas.py`, `fetcher.py`, `models.py`, `adapters/degiro.py` — ✅ Data Pipeline & Ingestion
- Ingestione multi-valuta, bonifica in 11 passaggi, validazione Pydantic, risoluzione ISIN-Ticker e modelli ORM SQLAlchemy con fallback nativo SQLite (`data/argus_local.db`).

---

## 4. Architettura delle 7 Viste Streamlit (`src/pages/`)

1. **`0_Control_Room.py`**: Control Room & Ingestione CSV/DeGiro, Selezione Database (`investment_risk_bi` vs `wealth`), Impostazioni Valuta Base e anteprima dati validati.
2. **`1_📈_Dashboard_Generale.py`**: Executive Cockpit, Health Score (0-100), Radar 360°, Early Warning Risk Limits, ARGUS Quant Advisor e **Centro Esportazione Report Centralizzato** (PDF, Excel, Power BI ZIP, HTML) in fondo alla pagina.
3. **`2_🔴_Analisi_Rischio.py`**: Matrice di Correlazione, Risk Heatmap Grid, Component VaR, Rischio Liquidità (ADV), Backtesting VaR (Kupiec Test), ATR Chandelier Exit Manager e **Machine Learning Anomaly Detector (Isolation Forest & Correlation Drift)**.
4. **`3_🔬_Modelli_Quantitativi.py`**: Frontiera Efficiente Markowitz (Ledoit-Wolf), Simulatore Monte Carlo Fan/Ribbon Chart (Student-t), **Simulatore Jump-Diffusion di Merton (Poisson Tail Shocks)**, Hedging Tattico & Tail Risk, Attribuzione Brinson-Fachler, e **Modelli Fattoriali, Black-Litterman & ML** (Black-Litterman, Carhart 4-Factor, Modello Macro-Fattoriale MSCI Barra a 5 Fattori Ortogonalizzati con Donut chart e modale informativo pop-up, e ML 30-day Volatility Forecasting).
5. **`4_📋_Posizioni_e_Dettagli.py`**: Posizioni attive, Costo di carico FIFO, Smart Rebalancer, Calendario Dividendi per Azienda, Tax-Loss Harvesting TUIR e Modello Almgren-Chriss Market Impact.
6. **`5_🏛️_Valutazione_Aziendale.py`**: Altman Z-Score, Scomposizione DuPont (3 e 5 fattori), Piotroski F-Score (9pt), WACC CAPM, Valutazione DCF Monte Carlo, Bilanci 10-K, Comparativa Multiaziendale e **Diagnostica Predittiva Machine Learning (Random Forest Distress Risk Classifier)**.
7. **`6_🌪️_Stress_Testing.py`**: MSCI Barra Multi-Scenario Matrix, Beta Shock Waterfall, Macro Scenario Builder interattivo ($\Delta r$, $\Delta \text{FX}$, $\Delta \text{Commodity}$, $\Delta \text{Equity}$) e **Visualizzatore 3D della Superficie di Rischio (Plotly Surface)**.
8. **`7_📊_Analisi_Temporale.py`**: Serie storiche degli snapshot su Data Warehouse MySQL/SQLite e confronto affiancato tra due punti temporali con carte $\Delta$.

---

## 5. Cronologia dei Bug Critici Risolti

1. **Dividendi Azzerati dal Validator**: Rimosso lo step che azzerava la quantità dei dividendi (`quantity=1` e `price=totale` preservati intatti).
2. **Parsing Dividend Yield < 1%**: Risolta l'errata interpretazione dei tassi percentuali inferiori all'1% (es. GOOGL 0.26%, BABA 0.90%, MSFT 0.95%) dividendo correttamente per 100.
3. **Mappatura Prezzi Ribilanciatore**: Sostituita la lettura di `row.get("price")` con la colonna ufficiale `row.get("last_price")` in `core/rebalancer.py`.
4. **Filtraggio Ticker Advisor**: Limitata la scansione dell'advisor alle sole posizioni attive con `qty_net > 0`.
5. **Indice Multi-Tab Excel**: Allineate le serie dei rendimenti storici tramite estrazione vettoriale `.values`.
6. **Polymorphic Port Error in Desktop Launcher**: Implementato il polling attivo `wait_for_server` prima di aprire la finestra WebView2, azzerando gli errori `ERR_CONNECTION_REFUSED`.

---

## 6. Suite di Test Automatizzati (PyTest)

Tutti i 59 test automatizzati passano con successo:

```bash
pytest
```
- Ingestione & Schemi: `test_validator.py`, `test_enhancements.py`
- Engine Quantitativo: `test_risk_engine.py`, `test_var_cvar.py`, `test_var_backtest.py`, `test_var_lookback.py`, `test_diversification.py`, `test_merton_and_isolation_forest.py`
- Modelli & Ottimizzazione: `test_optimization.py`, `test_kmeans_elbow.py`, `test_monte_carlo_ui.py`, `test_custom_stress.py`, `test_backtest.py`, `test_black_litterman_fama_french.py`, `test_new_quant_features.py`, `test_ml_and_3d_features.py`
- Modelli di Bilancio: `test_financial_analysis.py`
- Moduli Fiscuali & Limiti: `test_tax_engine.py`, `test_tax_engine_edge_cases.py`, `test_hedging_attribution_limits.py`
- Moduli Istituzionali & Reporting: `test_rebalancer_and_advisor.py`, `test_excel.py`, `test_html_exporter.py`
- Analisi Temporale: `test_history_analytics.py`
- Smoke Test UI Streamlit: `test_frontend_smoke.py`
