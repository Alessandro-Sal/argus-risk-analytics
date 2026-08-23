# Investment Risk BI Platform — Project Handoff (v5.17.0 Production Release)

> File di contesto esaustivo per la manutenzione futura, lo sviluppo di moduli aggiuntivi o l'integrazione di ARGUS con infrastrutture di analisi terze.

---

## 1. Contesto Generale e Obiettivi del Progetto

**Piattaforma**: ARGUS — Quantitative Risk, AI Analytics & Portfolio BI Platform v5.17.0.

**Stack Tecnologico del Sistema**:
- **Python 3.11+ / 3.14**: Motore ETL, Risk Engine quantitativo, AI Analyst (Dual-Engine LLM/NLG), Modelli Econometrici e di Bilancio, Generazione PDF/Excel/HTML.
- **SQL & MySQL 8.0 / SQLite (SQLAlchemy ORM)**: Data Warehouse relazionale, tabelle transazionali e storicizzazione snapshot temporali (`data/argus_local.db`).
- **Streamlit**: Web Application Framework interattivo per la dashboard (10 moduli ad alta densità quantitativa con Navigation Rail ad albero).
- **PyWebView & PyInstaller**: Architettura Desktop Nativa Windows (WebView2 engine, finestra dedicata, gestione ciclo di vita senza browser, eseguibile `.exe` standalone e collegamento Desktop).
- **Power BI & Google Looker Studio**: Executive Dashboards basate su pacchetto Star Schema ZIP (`dim_assets.csv`, `fact_positions.csv`, `fact_portfolio_summary.csv`).
- **Excel (`openpyxl`/`xlsxwriter`)**: Modello tattico di simulazione What-If ed esportazione Workbook Multi-Tab.
- **ReportLab**: Exporter PDF per la creazione in-memory di Factsheet istituzionali a 2 pagine e Factsheet One-Pager.
- **Docker & Docker Compose**: Containerizzazione completa dell'infrastruttura (App Streamlit + Database MySQL 8.0).

**Obiettivo del Progetto**:
Ingegnerizzata come piattaforma avanzata di Finanza Quantitativa e Risk Management, **ARGUS** — il cui nome si ispira al mito dell'osservatore dai cento occhi che vede tutto e non dorme mai — è una piattaforma integrata di **Business Intelligence, Financial Valuation, AI Narrative Intelligence e Quantitative Risk Management**. Progettata con un'interfaccia ad alta densità informativa di livello istituzionale, la soluzione offre un ecosistema avanzato per la diagnosi contabile, la profilazione del rischio e la protezione strategica di portafogli d'investimento multi-asset (*Equity, ETF, Fixed Income, Crypto e Cash*).

**Differenziatore Chiave**:
A differenza dei benchmark basati su simulazioni sintetiche, **ARGUS** è stato validato empiricamente su un **dataset reale di oltre 400 operazioni finanziarie storiche** (2021–2026 dal progetto WealthApp). Il sistema garantisce una precisione deterministica centesimale nella gestione di scenari operativi complessi (contabilità FIFO, dividendi frazionati, cambi valuta EUR/USD/GBP/CHF, movimenti di cassa e risoluzione ISIN-Ticker).

---

## 2. Architettura Completa del Sistema

```text
CSV / DeGiro / Google Sheets ──┐
                               ├──► core/validator.py ──► core/schemas.py ──► core/cache_shield.py ──► MySQL / SQLite ORM ──► core/risk_engine.py
yfinance API ──────────────────┘                           (Pydantic)         (LRU + SQLite 24h)     (models.py)               │
                                                                                                                               ├──► core/ai_analyst.py
                                                                                                                               ├──► core/advanced_quant.py
                                                                                                                               ├──► core/closed_trades.py
                                                                                                                               ├──► core/multi_portfolio.py
                                                                                                                               ├──► core/diagnostics.py
                                                                                                                               └──► core/financial_analysis.py
Power BI / Looker Studio ◄─── core/exporter.py ◄─── core/db_exporter.py ◄─── Presentation Layer (Streamlit / PyWebView)
                                (Star Schema ZIP)    (MySQL Snapshots)        ├── Desktop App (desktop_launcher.py)
                                                                               ├── Standalone Executable (ARGUS.exe)
                                                                               ├── Spotlight Search (Ctrl+K)
                                                                               ├── PDF Tear-Sheet (pdf_generator.py)
                                                                               ├── Standalone HTML (html_exporter.py)
                                                                               └── Excel What-If (excel_generator.py)
```

---

## 3. Mappatura e Stato dei Moduli Core (`core/`)

Tutti i moduli Python sorgente sono stati sviluppati, ottimizzati e verificati con la suite di test automatizzati (**110/110 PyTest PASSED - 100%**):

### `core/ai_analyst.py` — ✅ AI Narrative Intelligence & Quant Copilot
- **Dual-Engine Executive Memorandum**: Generazione di diagnosi narrative strutturate in 4 sezioni via REST API con Google Gemini / OpenAI, e fallback istantaneo su motore Natural Language Generation (NLG) quantitativo deterministico offline al 100%.
- **ARGUS Quant Copilot**: Assistente conversazionale integrato per interrogare il portafoglio su VaR, Sharpe, ribilanciamenti e titoli componenti.

### `core/advanced_quant.py` — ✅ Modelli Quantitativi di Frontiera
- **Asymmetric Tail Copulas (Clayton & Gumbel)**: Calcolo della dipendenza non lineare di coda ($\lambda_L, \lambda_U$) e matrice di asimmetria ($\lambda_L - \lambda_U$) per intercettare il rischio di contagio e crollo simultaneo durante i crash di borsa, con allerta per coppie $\lambda_L \ge 0.30$.
- **Simulatore Interattivo Trade Sizing (Kelly Criterion)**: Calcolo dell'allocazione ottima continua e discreta con raccomandazione *Half-Kelly ($f^*/2$)*, dimensionamento monetario del nozionale in base allo Stop-Loss inserito e stima dell'Edge statistico e del tasso di crescita geometrico atteso.
- **Equal Risk Contribution (ERC / Risk Parity Pura)**: Ottimizzazione non lineare SLSQP con matrice di covarianza Ledoit-Wolf per ripartire in modo rigorosamente paritario il contributo marginale al rischio ($RC_i = \sigma_p / N$).

### `core/closed_trades.py` — ✅ Graveyard, FIFO Closed Trades Journal & Multi-View Analytics
- **Closed Trades Journal**: Estrazione rigorosa a code FIFO dei singoli lotti chiusi con prezzi di carico/scarico, controvalori, PnL monetario/percentuale e holding period effettivo.
- **Curva Cumulativa di PnL Realizzato**: Tracciamento cronologico della crescita del profitto monetizzato con linea di **High-Water Mark (Picco)** e telemetria di trade drawdown.
- **Trading Calendar & Heatmap Mensile**: Matrice di performance Mese $\times$ Anno con totali annuali per l'identificazione della stagionalità dei profitti.
- **Scomposizione Settori GICS & Asset Class**: Normalizzazione istituzionale e ripartizione del PnL e del Win Rate per settore economico e classe di attivo.

### `core/multi_portfolio.py` — ✅ Total Wealth Multi-Account & Master Wealth Engine
- **Multi-Account Registry**: Salvataggio, caricamento ed eliminazione di profili di portafoglio con etichette strategiche (*Crescita*, *Dividendi*, *Previdenza*, *Crypto*).
- **Master Wealth Consolidation**: Fusione automatica di più conti in un unico Master Portfolio con aggregazione delle quote, ricalcolo del costo medio ponderato (WACP) e fusione delle serie storiche dei rendimenti ponderate per il controvalore ($\bar{R}_t = \sum w_i R_{i,t}$) su oltre 5.000 osservazioni giornaliere.
- **Standard GIPS Durata Temporale**: Calcolo del CAGR e della durata storica ancorata ai giorni di calendario effettivi ($n_{\text{years}} = \frac{T_{\max} - T_{\min}}{365.2425}$), azzerando le distorsioni tipiche delle classi di asset 24/7 (Crypto) unite a quelle azionarie 252d.
- **Fama-French & Markowitz Integration**: Regressione OLS multivariata integrata nel Master Wealth e calcolo automatico della frontiera efficiente Ledoit-Wolf.
- **Scorecard Comparativa**: Confronto affiancato multi-portafoglio su rendimento, volatilità, Sharpe, VaR e drawdown.

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

### `core/hrp_optimizer.py` — ✅ Hierarchical Risk Parity (HRP — López de Prado)
- **Tree Clustering & Quasi-Diagonalization**: Clustering gerarchico basato sulla distanza di correlazione $D_{i,j} = \sqrt{(1 - \rho_{i,j})/2}$ e linkage ad albero che supera la singolarità e l'instabilità delle matrici inverse di Markowitz.
- **Recursive Bisection**: Allocazione ricorsiva inversa della varianza sui sotto-cluster con calcolo del rendimento atteso, della volatilità annuale e dello Sharpe Ratio di portafoglio.

### `core/options_hedging.py` — ✅ Black-Scholes Pricing & Delta Hedging
- **Black-Scholes-Merton (1973) & 5 Greci**: Calcolo del prezzo analitico di opzioni Call/Put e dei 5 Greci ($\Delta, \Gamma, \Theta, \text{Vega}, \rho$).
- **Portfolio Delta-Hedging**: Calcolo dei contratti Put necessari per immunizzare o ridurre il Beta di portafoglio a livelli target.
- **Covered Call Yield Enhancer**: Strategia sistematica per generare rendimento passivo extra vendendo Call Out-of-the-Money (OTM) sulle posizioni azionarie in portafoglio.

### `core/regime_switching.py` — ✅ Market Regime Switching (3-State Markov Model)
- **Classificatore di Regime Macroeconomico**: Identificazione statistica a 3 stati (*Bull Low-Vol*, *Range-Bound Transition*, *Crisis High-Vol*) basata su rendimento e volatilità rolling a 21 giorni con matrice delle probabilità di transizione e stato recente.

### `core/forensic_accounting.py` — ✅ Contabilità Forense (Beneish & Sloan)
- **Beneish M-Score (1999)**: Modello econometrico a 8 fattori (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) per intercettare manipolazioni contabili e frodi di bilancio con soglia critica a $M > -1.78$.
- **Sloan Accrual Ratio (1996)**: Misura quantitativa della qualità dell'utile contabile rispetto ai flussi di cassa operativi reali per isolare gli utili artificiali.

### `core/financial_analysis.py` — ✅ Analisi dei Bilanci & Solvibilità
- **Altman Z-Score Model (1968)**: Previsione del rischio di bancarotta a 24 mesi con verdetto a semaforo (*Safe Z > 2.99*, *Grey 1.81-2.99*, *Distress Z < 1.81*).
- **Scomposizione DuPont (3 e 5 Fattori)**: Decomposizione del ROE nei driver di Profit Margin, Asset Turnover, Equity Multiplier, Tax Burden e Interest Burden.
- **Piotroski F-Score (9 Punti Stanford)**: Valutazione di salute contabile basata su Profittabilità (4 pt), Struttura/Liquidità (3 pt) ed Efficienza Operativa (2 pt).
- **Calcolatore Dinamico WACC (CAPM)**: Costo del Capitale Medio Ponderato con Costo dell'Equity CAPM ($r_e = R_f + \beta \cdot ERP$), Costo del Debito al netto delle imposte e pesi strutturali.
- **Modello di Valutazione Intrinseca DCF Monte Carlo**: 2-Stage Discounted Cash Flow a 1.000 iterazioni stocastiche con istogramma di distribuzione del Fair Value per azione.
- **Consultazione Bilanci Ufficiali 10-K**: Download ed estrazione diretta di Conto Economico, Stato Patrimoniale e Cash Flow reali da Yahoo Finance.
- **Comparativa Multiaziendale**: Confronto affiancato di 2+ aziende con Z-Score, DuPont, Radar Chart e Matrice dei Multipli (*P/E*, *EV/EBITDA*, *P/B*, *P/S*).

### `core/screener_engine.py` — ✅ Screener Quantitativo & Pre-Trade Impact Simulator
- Discovery globale su 4 universi e archetipi quantitativi istituzionali (*GARP*, *Deep Value*, *Dividend Fortress*, *Low Volatility*, *Momentum Breakout*).
- Simulatore di impatto pre-trade con ricalcolo dei delta su rischio, diversificazione e rendimento.

### `core/tax_engine.py` — ✅ Ottimizzazione Fiscale & Tax-Loss Harvesting Wizard (TUIR Art. 67)
- **Tassazione Normativa Italiana**: Tassazione al 12.5% sui Titoli di Stato (White List) e 26.0% su Azioni, Obbligazioni, ETF e Cripto.
- **Regola ETF vs Titoli Singoli**: Plusvalenze da ETF considerate *Redditi di Capitale* e non compensabili con minusvalenze (*Redditi Diversi*).
- **Tax-Loss Harvesting & Step-Up Wizard**:
  - *Step-Up Fiscale a 0€ Imposte*: Calcolo esatto per vendere e ricomprare posizioni in utile su *Redditi Diversi*, azzerando minusvalenze in scadenza senza esborso fiscale e alzando il prezzo di carico a zero tasse.
  - *Raccolta Minusvalenze*: Individuazione posizioni in perdita latente da monetizzare per generare scudi fiscali quadriennali.

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

### `core/technical_analysis.py` — ✅ Motore di Analisi Tecnica, Volume Profile & Confluenza
- Calcolo degli indicatori tecnici quantitativi: Medie Mobili (EMA 20, EMA 50, SMA 200 con Golden/Death Cross), MACD Line/Signal/Hist, RSI 14, Bande di Bollinger con **Bollinger Squeeze Detection**, ATR 14 e ADX 14.
- Volume Profile distribuzionale per la stima del **Point of Control (POC)** e della **Value Area (VAH / VAL 70%)**.
- Candlestick Pattern Recognition per il rilevamento automatico di Engulfing, Doji, Hammer e Shooting Star.
- **Technical Confluence Score Card (0-100)** con verdetto tattico ed allineamento trend **Multi-Timeframe (Daily 1D vs Weekly 1W)**.

### `core/cache_shield.py` — ✅ Multi-Tier Caching & Rate-Limit Shield
- Architettura a 2 livelli (L1 RAM LRU + L2 SQLite `data/yfinance_cache.db` con TTL a 24h).
- Exponential backoff con jitter e polite throttling per schermare gli errori `HTTP 429 Too Many Requests`.

### `core/diagnostics.py` — ✅ System Diagnostics, Storage Cockpit & Maintenance
- **Storage & Memory Profiler**: Calcolo in tempo reale dello spazio su disco per tabella/file, delle pagine libere compattabili (*freelist*) e della RAM (RSS) del processo Python.
- **1-Click Maintenance Utilities**: `optimize_database_storage` (VACUUM & compatta DB), `clean_expired_cache_records` (pulizia TTL 24h), `reindex_databases` (reindicizzazione B-Tree su ticker e date).
- **Benchmark di Latenza**: Monitoraggio della latenza in millisecondi (ms) sui 26 motori quantitativi istituzionali e test di integrità `PRAGMA integrity_check`.

### `core/workspace_manager.py` & `core/sidebar.py` — ✅ Navigation Rail v5.14.0, Spotlight & Workspace State
- Gestione dello stato sessione e URL query parameters (`st.query_params`) per routing e permalink affidabili.
- Command Palette Spotlight (`Ctrl+K` / `Cmd+K`) per saltare all'istante a qualsiasi modulo o ticker con fuzzy search.
- Sistema di Tree Rail istituzionale a 10 moduli con routing reattivo a sotto-schede e persistenza multi-sessione.

---

## 4. Architettura dei 10 Moduli Streamlit (`src/`)

1. **`0_Control_Room.py`**: Control Room & Ingestione CSV/DeGiro/Google Sheets Live Sync, Switch Database, Selezione Valuta Base, **Total Wealth Hub (Multi-Account)** con Master Wealth Fusion, **Database & Memory Storage Cockpit** con Donut Chart e 1-Click Maintenance Tools, **⚡ Motore Analitico Embedded DuckDB (OLAP) & Parquet Storage**.
2. **`1_📈_Dashboard_Generale.py`**: Executive Cockpit, Badges Istituzionali, Radar Factor 360°, **Multi-Benchmark Overlay fino a 4 indici con Scorecard**, Early Warning Risk Limits, ARGUS AI Analyst, Quant Copilot e Centro Esportazione Report.
3. **`2_🔴_Analisi_Rischio.py`**: Matrice di Correlazione, Risk Heatmap Grid, Component VaR, **Volatilità Condizionale GARCH(1,1) & FHS**, **Market Regime Switching (3-State Markov Model)**, Rischio Liquidità (ADV), Backtesting VaR (Kupiec Test), ATR Chandelier Exit Manager e **Machine Learning Anomaly Detector (Isolation Forest & Correlation Drift)**.
4. **`3_🔬_Modelli_Quantitativi.py`**: Frontiera Efficiente Markowitz (Ledoit-Wolf), **🧬 Tail Copula (Clayton/Gumbel) & Crash Contagion Matrix**, **⚖️ Simulatore Interattivo Trade Sizing (Kelly Criterion)**, **Live Rebalancing Sandbox (What-If Weight Matrix)**, **Hierarchical Risk Parity (HRP — López de Prado)**, Simulatore Monte Carlo Fan/Ribbon Chart (Student-t), **Simulatore Jump-Diffusion di Merton (Poisson Tail Shocks)**, Hedging Tattico & Tail Risk, **Modello Black-Scholes con Superficie di Volatilità Implicita 3D, Skew/Smile Calibration & Covered Call Yield Enhancer**, Attribuzione Brinson-Fachler, e **Modelli Fattoriali (Kenneth French 5-Factor + Momentum Live Library, Carhart 4-Factor, MSCI Barra 5-Factor Ortogonalizzato, Black-Litterman)**.
5. **`4_📋_Posizioni_e_Dettagli.py`**: Posizioni attive, Costo di carico FIFO, **🪦 Posizioni Chiuse & Graveyard Cockpit Multi-Prospettiva (Curva Cumulativa, High-Water Mark, Trading Calendar & Heatmap Mensile, Scomposizione Settori/Asset Class)**, **💰 Tax-Loss Harvesting & Step-Up Wizard (TUIR Art. 67)**, **🪙 Modulo Fiscale Cripto-Attività (Quadri RT/RW/IVAFE L. 197/2022)**, Smart Rebalancer, Calendario Dividendi per Azienda e Modello Almgren-Chriss Market Impact.
6. **`5_🏛️_Valutazione_Aziendale.py`**: Altman Z-Score, Scomposizione DuPont (3 e 5 fattori), Piotroski F-Score (9pt), **Contabilità Forense: Beneish M-Score & Sloan Accrual Ratio**, WACC CAPM, Valutazione DCF Monte Carlo, Bilanci 10-K, **🔍 Local RAG & SEC Filing Vector Store (10-K/10-Q Q&A)**, Comparativa Multiaziendale e **Diagnostica Predittiva Machine Learning (Random Forest Distress Risk Classifier)**.
7. **`6_🌪️_Stress_Testing.py`**: MSCI Barra Multi-Scenario Matrix, Beta Shock Waterfall, Macro Scenario Builder interattivo ($\Delta r$, $\Delta \text{FX}$, $\Delta \text{Commodity}$, $\Delta \text{Equity}$) e **Visualizzatore 3D della Superficie di Rischio (Plotly Surface)**.
8. **`7_📊_Analisi_Temporale.py`**: Storicizzazione Multi-Snapshot su Data Warehouse MySQL/SQLite, Evoluzione Temporale del Valore di Portafoglio, Matrice dei Delta ($\Delta$) tra Snapshot e Calcolatore del Tasso di Risparmio & Iniezioni di Liquidità.
9. **`8_📈_Analisi_Tecnica.py`**: Cockpit di Analisi Tecnica & Quantitative Charting, Volume Profile (POC/VAH/VAL), Candlestick Pattern Recognition, Technical Confluence Score Card (0-100), Multi-Timeframe Alignment (1D vs 1W) e Tabella Screener di Confluenza.
10. **`9_🔍_Screener_Opportunita.py`**: Screener Quantitativo Multi-Fattoriale (Valutazione, Qualità Contabile, Rischio, Momentum), **⚡ Formula Engine EQS (Custom Query Builder con sintassi logica avanzata)**, Archetipi Istituzionali, Pre-Trade Impact Simulator e Generatore Factsheet PDF One-Pager.

---

## 5. Suite di Test Automatizzati (PyTest)

Tutti i **207 test automatizzati passano con successo (100%)**:

```bash
py -m pytest
```

---

*ARGUS Risk Analytics Platform — Documento di Handoff Tecnico v5.17.0.*

