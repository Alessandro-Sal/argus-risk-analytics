# Investment Risk & Wealth Intelligence Platform — Project Handoff (v8.1.0 Enterprise Release)

> File di contesto esaustivo per la manutenzione futura, lo sviluppo di moduli aggiuntivi o l'integrazione di ARGUS con infrastrutture di analisi terze.

---

## 1. Contesto Generale e Obiettivi del Progetto

**Piattaforma**: ARGUS — Quantitative Risk, AI Analytics, Portfolio BI, Wealth Ecosystem & Enterprise Resilience v8.1.0.

**Stack Tecnologico del Sistema**:
- **Python 3.11+ / 3.14**: Motore ETL, Data Quality Gate (Pydantic v2), Risk Engine quantitativo, Live Terminal Desk (Pre-Trade Checks & OMS Blotter), Backup Engine, Security Vault, AI Analyst (Dual-Engine LLM/NLG con Guardrails MiFID II / Art. 21 TUF), Modelli Econometrici e di Bilancio, Generazione PDF/Excel/HTML/Parquet, Plotly Institutional Framework e Design System.
- **Embedded DuckDB & MySQL 8.0 / SQLite (SQLAlchemy ORM)**: Data Warehouse relazionale, calcolo analitico colonnare vettorizzato (C++ SIMD), indici B-Tree time-series compositi e storicizzazione snapshot (`data/argus_local.db`, `data/argus_wealth.db`).
- **Streamlit**: Web Application Framework reattivo ad alta densità per 21 moduli istituzionali divisi tra Sezione Risk e Sezione Wealth con Navigation Rail ad albero bidirezionale, State Management isolato (`core/workspace_context.py`), Design System *Obsidian Sovereign* (`core/ui_utils.py`) e Plotly Chart Factory (`apply_custom_chart_layout`).
- **PyWebView & PyInstaller**: Architettura Desktop Nativa Windows (WebView2 engine, finestra dedicata, backup pre-flight, bootstrap in-process fallback, compilazione standalone portatile con `argus_desktop.spec`).
- **Power BI & Google Looker Studio**: Executive Dashboards basate su pacchetto Star Schema ZIP (`dim_assets.csv`, `fact_positions.csv`, `fact_portfolio_summary.csv`).
- **Excel (`openpyxl`/`xlsxwriter`)**: Modello tattico What-If, formule RTD Bloomberg (`=ARGUS_BDP`, `=ARGUS_BDH`, `=ARGUS_RISK`), tabelle native `ListObject` con formule live sanitizzate anti-formula injection.
- **ReportLab**: Exporter PDF vettoriale in-memory con `InstitutionalNumberedCanvas` per Factsheet istituzionali a 2 pagine, Pitchbook advisory a 6 pagine e report trimestrali white-label.
- **Docker & Docker Compose**: Containerizzazione hardening multi-stage non-root (`argus:argus`) con healthcheck integrato.

**Obiettivo del Progetto**:
Ingegnerizzata come piattaforma avanzata di Finanza Quantitativa, Wealth Intelligence e Risk Management, **ARGUS** — il cui nome si ispira al mito dell'osservatore dai cento occhi che vede tutto e non dorme mai — è un ecosistema completo per la diagnosi contabile, la profilazione del rischio, la pianificazione patrimoniale multi-generazionale e la protezione strategica di patrimoni d'investimento multi-asset (*Equity, ETF, Fixed Income, Crypto, Immobili, Illiquidi e Cash*).

**Differenziatore Chiave**:
A differenza dei benchmark basati su simulazioni sintetiche, **ARGUS** è stato validato empiricamente su un **dataset reale di oltre 400 operazioni finanziarie storiche** (2021–2026 dal progetto WealthApp) e testato con **510 test automatizzati (100% passed)** su 88 file di test. Il sistema garantisce una precisione deterministica centesimale nella gestione di scenari operativi complessi (contabilità FIFO, dividendi frazionati, cambi valuta EUR/USD/GBP/CHF, movimenti di cassa, deduplicazione deterministica SHA-256 e risoluzione ISIN-Ticker).

---

## 2. Architettura Completa del Sistema

```text
CSV Broker / Estratti Conto / GSheets ──┐
                                         ├──► core/data_quality_gate.py ──► core/schemas.py ──► core/cache_shield.py
Yahoo Finance API / Crypto Providers ────┘     (Pydantic v2 Canonical)         (Contracts)        (LRU + SQLite 24h)
                                                                                                        │
    ┌───────────────────────────────────────────────────────────────────────────────────────────────────┘
    ▼
Persistenza Dati & Continuità Operativa:
 ├── core/universal_ledger.py  ──► Double-Entry One-Ledger, WACP FIFO SQL Qualify, Zero-Copy PyArrow & Parquet
 ├── core/wealth/wealth_db.py  ──► SQLite (argus_wealth.db) / MySQL 8.0 [Star Schema Time-Series]
 ├── core/database_migration_manager.py ──► DBRE Dual-Versioning (PRAGMA user_version & schema_migrations), Pre-Flight Backup & Drift Inspector
 ├── core/duckdb_engine.py     ──► In-Process Vectorized OLAP & Apache Parquet
 ├── core/security_engine.py   ──► CWE-1236 Sanitization, PII Masking & ArgusDataVault (AES-Fernet)
 └── core/backup_engine.py     ──► Hot Backup (SQLite Backup API), WAL Checkpoint & Atomic Restore Rollback
    │
    ▼
Computational Core:
 ├── core/universal_ledger.py  ──► Vectorized Transaction Ledger & WACP FIFO Cost Basis
 ├── core/wealth/human_capital_engine.py ──► Human Capital Actuarial Valuation, TBS-VaR & Debt Stress
 ├── core/wealth/tbs_monte_carlo.py      ──► Total Balance Sheet Lifetime Solvency Monte Carlo Engine
 ├── core/msci_barra_risk_engine.py      ──► Asset-Level Factor Risk Decomposition (MSCI Barra GEM3/USE4)
 ├── core/prescriptive_rebalancer.py     ──► Conic/SLSQP Multi-Objective Rebalancer & FIX 4.4 Order Blotter
 ├── core/risk_engine.py       ──► FIFO Engine, Cornish-Fisher CVaR, Euler VaR, L-VaR Bangia, Almgren-Chriss
 ├── core/advanced_quant.py    ──► Tail Copulas, Kelly Criterion, ERC, Liquidity-Adjusted VaR (L-VaR)
 ├── core/fixed_income.py      ──► Nelson-Siegel Zero-Coupon Curve, 5 Key Rate Durations (KRD), Z-Spread, CDS
 ├── core/wealth/unified_stress_bridge.py ──► Cross-Asset Macro Factor Stress Bridge Engine
 ├── core/wealth/tax_aware_location.py    ──► Tax-Aware Asset Location Optimizer
 ├── core/autonomous_rebalancer.py        ──► Autonomous Rebalancer con WACP/PMC reale & Zainetto Fiscale
 ├── core/wealth/wealth_engine.py ──► FIRE 50/30/20, Mutui/LTV, Orologi/Illiquidi, Successione
 ├── core/factor_library.py    ──► Fama-French 5-Factor & Carhart Momentum Live Regression
 ├── core/ai_analyst.py        ──► Tri-Agent Quantitative Governance Council & Dual-Engine LLM/NLG
 └── core/terminal_engine.py   ──► Pre-Trade Risk Guardrails, Stoikov Microprice & OMS Execution Slicing
    │
    ▼
Presentation Layer (21 Moduli Streamlit / PyWebView):
 ├── Desktop Native App (desktop_launcher.py + argus_desktop.spec)
 ├── Spotlight Command Palette (Ctrl+K) & Bloomberg Terminal Mnemonic Parser
 ├── Institutional 5-Block Educational Modals & Crisp Vector SVG Icons
 ├── Client-Ready PDF Exporters (Factsheet, Pitchbook A4 6-Pagine, White-Label Quarterly)
 ├── Multi-Sheet Excel Dossiers con protezione CWE-1236
 └── Star Schema ZIP Packager per Power BI / Looker Studio
```

---

## 3. Mappatura e Stato dei Moduli Core (`core/`)

Tutti i moduli Python sorgente sono stati sviluppati, ottimizzati e verificati con la suite di test automatizzati (**510/510 PyTest PASSED - 100%**):

### `core/ai_analyst.py` — ✅ AI Narrative Intelligence & Quant Copilot
- **Dual-Engine Executive Memorandum**: Generazione di diagnosi narrative strutturate in 4 sezioni via REST API con Google Gemini / OpenAI, e fallback istantaneo su motore Natural Language Generation (NLG) quantitativo deterministico offline al 100%.
- **ARGUS Quant Copilot**: Assistente conversazionale integrato per interrogare il portafoglio su VaR, Sharpe, ribilanciamenti e titoli componenti.

### `core/advanced_quant.py` — ✅ Modelli Quantitativi di Frontiera & Liquidity-Adjusted VaR (L-VaR)
- **Asymmetric Tail Copulas (Clayton & Gumbel)**: Calcolo della dipendenza non lineare di coda ($\lambda_L, \lambda_U$) e matrice di asimmetria ($\lambda_L - \lambda_U$) per intercettare il rischio di contagio e crollo simultaneo durante i crash di borsa, con allerta per coppie $\lambda_L \ge 0.30$.
- **Simulatore Interattivo Trade Sizing (Kelly Criterion)**: Calcolo dell'allocazione ottima continua e discreta con raccomandazione *Half-Kelly ($f^*/2$)*, dimensionamento monetario del nozionale in base allo Stop-Loss inserito e stima dell'Edge statistico e del tasso di crescita geometrico atteso.
- **Equal Risk Contribution (ERC / Risk Parity Pura)**: Ottimizzazione non lineare SLSQP con matrice di covarianza Ledoit-Wolf per ripartire in modo rigorosamente paritario il contributo marginale al rischio ($RC_i = \sigma_p / N$).
- **Liquidity-Adjusted Value at Risk (L-VaR Bangia 1999)**: Scomposizione analitica del rischio totale tra perdita di mercato e costo di liquidazione da allargamento esogeno dello spread $(\mu_S + z_{\alpha} \sigma_S)$, con scaling per orizzonte di smobilizzo ordinato ($\sqrt{T_{\text{liq}}}$) e calcolo del Liquidity Haircut.

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
- Discovery globale su 11 universi e archetipi quantitativi istituzionali (*GARP*, *Deep Value*, *Dividend Champions*, *Low Volatility*, *Momentum Breakout*, *Portafoglio Attivo Live*).
- **Parallel Multi-Thread Engine (8 Workers)**: Scansione concorrente ad altissima velocità su universi fino a 100 titoli in soli ~3s con retry esponenziale anti-429 e fallback automatico `fast_info` per ETF/Crypto.
- **Granular Cache Invalidation & Force Live Refresh**: Tracciamento granulare del contenuto degli universi con pulsante `🔄 Forza Live` per bypassare istantaneamente la cache L2.
- **Smart Sizing Optimizer & Pre-Trade Impact Simulator**: Simulazione d'impatto pre-trade con massimizzazione dell'indice di Sharpe o del Diversification Ratio (Choueifaty 2008), determinazione del peso ottimo del candidato $w^*$ e curva continua di frontiera Sharpe.
- **Normalizzazione Istituzionale Dividend Yield %**: Calcolo normalizzato su $\frac{\text{dividendRate}}{\text{last\_price}}\times 100$, pricing sintetico per stablecoin ed ETF europei.

### `core/tax_engine.py` — ✅ Ottimizzazione Fiscale, Modello Redditi PF & Tax-Loss Harvesting (TUIR Artt. 44, 67, 68)
- **Tassazione Normativa Italiana & Aliquote Differenziate**: Tassazione agevolata al 12.5% sui Titoli di Stato ed enti sovranazionali (White List D.M. 04/09/1996) e 26.0% su Azioni, Obbligazioni societarie, ETF, Derivati e Cripto-attività (L. 197/2022).
- **Asimmetria Normativa ETF vs Titoli Singoli**: Rigorosa distinzione codificata tra *Redditi di Capitale* (Art. 44 TUIR, plusvalenze da ETF armonizzati non compensabili con minus pregresse) e *Redditi Diversi negativi* (Art. 67-68 TUIR, minusvalenze da ETF accreditabili a zainetto fiscale quadriennale e compensabili solo da titoli azionari, obbligazionari, ETC o derivati).
- **Integrazione Motori di Rebalancing Tax-Aware (`tax_aware_rebalancer.py`, `prescriptive_rebalancer.py`)**: Vincolo matematico che inibisce la compensazione indebita di minusvalenze pregresse su realizzi in utile di ETF.
- **Prospetto Fiscale Modello Redditi PF (Persone Fisiche)**:
  - **Quadro RT**: Sezione II (Plusvalenze/Minusvalenze su partecipazioni e titoli azionari/obbligazionari/derivati) e Sezione II-B (Plusvalenze su Cripto-attività ex L. 197/2022 con verifica soglia di realizzo a 2.000€).
  - **Quadro RW**: Monitoraggio fiscale investimenti esteri e conti correnti offshore (es. Degiro, IBKR, Revolut). Algoritmo di calcolo ponderato della **Giacenza Media** ($\bar{G} > 5.000€$ per assoggettamento all'imposta fissa IVAFE di 34,20€) e tracciamento del **Picco Massimo** intraday ($> 15.000€$ per obbligo di monitoraggio esente da IVAFE). Aliquota IVAFE Paesi Black List (D.M. 04/05/1999) elevata allo 0,40% (4 per mille) ai sensi della L. 213/2023.
  - **Quadro RM**: Sezione V (Rigo RM12) per proventi da capitale e dividendi esteri percepiti tramite intermediari non residenti senza ritenuta alla fonte a titolo d'imposta (tassazione sostitutiva al 26% su "Netto Frontiera" ex Art. 18 TUIR).
- **Tax-Loss Harvesting & Step-Up Wizard (Art. 10-bis L. 212/2000)**:
  - *Step-Up Fiscale a 0€ Imposte*: Calcolo per vendere e ricomprare posizioni in utile su *Redditi Diversi*, azzerando minusvalenze in scadenza senza esborso fiscale ed elevando il prezzo medio di carico.
  - *Raccolta Minusvalenze & Proxy Substitution*: Individuazione posizioni in perdita latente da monetizzare per generare scudi fiscali, con raccomandazione di sostituzione su Proxy Asset benchmark-correlati (es. cambio ETF/ETC analogo) per preservare l'esposizione di mercato ed evitare fattispecie di abuso del diritto o wash-sale risk.

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
- Fallback automatico su Stooq Data Provider per azioni ed indici in caso di congestione su Yahoo Finance.

### `core/resilient_market_engine.py` — ✅ Enterprise SRE Market Data Resilience Engine
- **Circuit Breaker a 3 Stati (`CLOSED`, `OPEN`, `HALF_OPEN`)**: Macchina a stati finiti thread-safe conforme allo standard Netflix Hystrix per prevenire il sovraccarico di endpoint in throttling (429/503) garantendo il Fast-Fail a 0ms su provider secondari o cache locale.
- **Retry Policy con Full Jitter (AWS Architecture Pattern)**: Algoritmo di backoff esponenziale con decorrelazione uniforme casuale $t = \text{random}(0.1, \min(T_{\max}, T_{\text{base}} \cdot 2^{\text{attempt}}))$ per azzerare l'effetto "Thundering Herd" e rispetto dell'header `Retry-After`.
- **Stooq Free Fallback Engine**: Connettore mondiale per quotazioni azionarie, ETF, indici e valute senza vincoli di chiavi API.
- **Market-Aware Freshness & Staleness Evaluator**: Classificazione formale della freschezza dei dati sincronizzata con il calendario di mercato borsistico reale (`LIVE_REALTIME`, `END_OF_DAY_FRESH`, `MARKET_CLOSED_BENIGN`, `STALE_WARNING`, `OFFLINE_EMERGENCY`).
- **Data Envelope `MarketDataEnvelope`**: Busta di trasporto dati con indicazione di latenza in ms, timestamp di acquisizione e warning informativi per la dashboard.
### `core/bquant_engine.py` — ✅ BQuant In-Memory Python Sandbox & DuckDB SQL
- **In-Memory Sandboxed Execution**: Esecuzione dinamica sicura di script Python con iniezione del bundle di sessione (`df_positions`, `df_returns`, `df_prices`, `results`, `duckdb`).
- **DuckDB SQL Integration**: Registrazione automatica dei DataFrame in sessione in-memory per query analitiche SQL con sintassi ANSI e aggregazioni OLAP sub-millisecondo.
- **Dynamic Output Interception**: Cattura automatica di flussi stdout/stderr, tabelle `df_out` e figure Plotly/Matplotlib con misurazione precisa dei tempi di esecuzione in secondi.
- **5 Snippet Quantitativi Istituzionali**: Rolling Correlation Heatmap, DuckDB Aggregation, OLS Factor Regression & Hedge, Drawdown Underwater Plot, Dynamic Risk-Parity Rebalancing.

### `core/workspace_engine.py` — ✅ ARGUS Launchpad & Institutional Role Profiles
- **5 Profili di Ruolo Istituzionali**: Trading Desk & Execution, Risk Officer & Compliance, Portfolio Manager & CIO, Quantitative Analyst & Data Scientist, Corporate Treasurer & Fixed Income.
- **Persistenza Layout SQLite**: Salvataggio e ripristino istantaneo delle preferenze utente, widget attivi e routing predefinito su database locale.

### `core/excel_connector.py` — ✅ Excel Live Connector, Bloomberg Formulas & Multi-Sheet Exporter
- **Bloomberg Formula Builder**: Generazione formule native `=ARGUS_BDP(ticker, field)`, `=ARGUS_BDH(ticker, field, start, end)`, `=ARGUS_RISK(metric)`.
- **Integrazione Duale VBA / Office Scripts**: Modulo VBA per Excel Desktop (.bas) e script TypeScript per Excel 365/Web con chiamate REST non bloccanti.
- **Esportatore Multi-Foglio OpenPyXL/XlsxWriter**: Creazione di cartelle di lavoro professionali con fogli *Executive_Summary*, *Positions_Portfolio*, *Fixed_Income_YAS*, *Execution_Schedule* con stili grafici e formattazione colonnare automatica.

### `core/backup_engine.py` — ✅ Zero-Downtime Hot Backup & Disaster Recovery Atomico
- **SQLite Online Backup API**: Esecuzione di copie snapshot a caldo consistenti senza interruzione di lettura/scrittura sui database patrimoniali.
- **WAL Checkpoint `TRUNCATE`**: Svuotamento preventivo del Write-Ahead Log per garantire l'inclusione di tutte le transazioni pendenti nel file principale `.db`.
- **Integrità & Retention**: Doppio audit `PRAGMA integrity_check` e `PRAGMA foreign_key_check`, compressione gzip trasparente con pruning basato su anzianità.
- **Rollback Atomico**: Salvataggio automatico di una copia d'emergenza `.emergency_pre_restore` prima di ogni ripristino per annullare all'istante snapshot corrotti.

### `core/database_migration_manager.py` — ✅ DBRE Database Migration & Schema Reliability Manager
- **Dual-Layer Schema Versioning**: Lettura $O(1)$ a livello di file header con `PRAGMA user_version` (check di avvio sub-millisecondo senza overhead) combinata con la tabella di audit `schema_migrations` (checksum crittografici SHA-256 anti-manomissione, execution time in ms, audit trail e flag di rollback).
- **Pre-Flight Silent Shadow Backup**: Generazione automatica di snapshot a caldo prima di qualsiasi DDL (`.db.gz` o shadow copy) e validazione preventiva con `PRAGMA integrity_check`.
- **Transazionalità Atomica DDL & Disaster Recovery Rollback**: Esecuzione in blocchi `BEGIN IMMEDIATE` / `COMMIT` con rollback automatico immediato e ripristino istantaneo dello snapshot di sicurezza in caso di eccezioni DDL a metà esecuzione.
- **Schema Drift Inspector**: Ispezione automatica dei cataloghi fisici SQLite contro i modelli SQLAlchemy ORM (`core/models.py`) e modelli Wealth (`core/wealth/wealth_models.py`), controllo orfani referenziali `PRAGMA foreign_key_check` e diagnostica con severità `INFO`, `WARNING`, `CRITICAL`.
- **Indici Compositi Analitici & Integrazione DuckDB C++**: Deploy idempotente di indici compositi coprenti (`transactions`, `market_prices`, `wealth_cashflow`, `portfolio_snapshots`) per accelerare query multidimensionali e compatibilità al 100% con l'attach nativo DuckDB (`ATTACH '...' (TYPE SQLITE)`).

### `core/security_engine.py` — ✅ Cybersecurity, Anti-Formula Injection & ArgusDataVault
- **CWE-1236 Formula Injection Defense**: Sanitizzazione sistematica con prefisso apostrofo (`'`) per stringhe che iniziano con `=`, `+`, `-`, `@`, `\t` o `\r` esportate in CSV e XLSX.
- **Data Minimization & PII Masking**: Mascheramento dinamico a standard GDPR (Art. 5/32) per IBAN (`IT60****************1234`), Codici Fiscali e numeri di conto bancario.
- **ArgusDataVault (Crittografia a Riposo)**: Cifratura simmetrica AES-128/256 Fernet (CBC + HMAC-SHA256) con derivazione chiave PBKDF2 a 100.000 iterazioni.
- **AI Prompt Credential Stripping**: Pulizia trasparente di token di autenticazione e chiavi segrete da qualsiasi contesto destinato a LLM esterni.

### `core/data_quality_gate.py` — ✅ Data Integration Gate & Ingestion Middleware
- **Pydantic v2 Declarative Schemas**: Contratti di tipo rigorosi (`CanonicalTradeRecord`, `QualityGateReport`) per l'interscambio tra parser broker e DB.
- **Semantic Sanity Checks**: Rilevamento automatico di saldi negativi ingiustificati, blocco di vendite allo scoperto non autorizzate e segnalazione di operazioni eseguite nei weekend.
- **Deduplicazione Naturale SHA-256 (`tx_hash`)**: Generazione di un hash deterministico basato su data, ticker, tipo operazione, quantità e prezzo per garantire l'idempotenza assoluta nei ricaricamenti degli estratti conto.

### `core/workspace_context.py` — ✅ State Management & Multi-Workspace Isolation
- **Sottocontesti Tipizzati**: Strutturazione deterministica in `RiskSubContext`, `WealthSubContext` e `UIViewState` per isolare calcoli, filtri e viste.
- **Session Cache Persistence**: Salvataggio atomico su file (`data/cache/sessions/session_{id}.pkl`) con ripristino istantaneo e isolamento multi-workspace.
- **Bonifica Chiavi Orfane (`flush_risk_domain()`)**: Purga chirurgica dello `st.session_state` al cambio di scenario o portafoglio per prevenire l'inquinamento incrociato (*cross-contamination*).
- **Consolidamento Reattivo Net Worth**: Aggregazione in-memory del portafoglio titoli liquido nel bilancio patrimoniale complessivo senza round-trip DB obbligatori.

### `core/reporting_design_system.py` & `core/modular_factsheet_builder.py` — ✅ Reporting Design System & PDF Exporters
- **Palette Obsidian Sovereign**: Grammatica cromatica scura istituzionale ad alta leggibilità (`#0a0e14`, `#121820`, `#ff9900`, `#10b981`, `#ef4444`, `#c9d1d9`).
- **`InstitutionalNumberedCanvas`**: Rendering A4 ReportLab a due passaggi con numerazione progressiva automatica ("Pagina X di Y"), running headers/footers e filigrana riservata.
- **Grafici Vettoriali In-Memory**: Ciambelle e barre native ReportLab (`Drawing`, `Wedge`, `String`) che azzerano leak di memoria ed eliminano dipendenze da processi esterni di rasterizzazione.

### `core/ingestion_utils.py` & `core/wealth/universal_bank_parser.py` — ✅ Universal Bank Ingestion & Layout Sniffer
- **Sniffing Euristico del Layout**: Rilevamento automatico della riga di intestazione, del delimitatore (virgola, punto e virgola, tab) e dell'encoding (UTF-8, Latin-1, CP1252) su estratti conto bancari eterogenei.
- **Parser Adattivo Multi-Banca**: Normalizzazione trasparente di movimenti bancari da formati standard e non convenzionali con riconciliazione contabile e tolleranza su date e separatori decimali.

### `core/wealth/unified_stress_bridge.py` — ✅ Unified Multi-Asset Factor Stress Bridge
- **Cross-Asset Macro Bridge (`UnifiedCrossAssetStressEngine`)**: Unificazione della trasmissione degli shock macroeconomici tra portafoglio titoli liquido e patrimonio complessivo illiquido.
- **Shock Multi-Fattoriale (`MacroFactorShock`)**: Perturbazione simultanea su 5 fattori (tassi di interesse $\Delta r$, azionario $\Delta S$, inflazione $\Delta \pi$, immobiliare $\Delta P_{\text{re}}$ e spread creditizio $\Delta s$).
- **Impatto Consolidato sul Net Worth**: Quantificazione monetaria del deprezzamento azionario/obbligazionario, rivalutazione/svalutazione immobiliare, aumento dell'onere del debito su mutui a tasso variabile ed erosione del fondo di emergenza da inflazione.

### `core/wealth/tax_aware_location.py` — ✅ Tax-Aware Asset Location Optimizer
- **Arbitraggio Fiscale Multi-Conto (`TaxAwareAssetLocator`)**: Allocazione ottimale degli attivi patrimoniali tra conti Tassabili (Regime Amministrato/Dichiarativo) e veicoli fiscalmente agevolati (Fondo Pensione complementare deducibile fino a €5.164,57, Piani Individuali di Risparmio PIR).
- **Indice di Inefficienza Fiscale (IFI)**: Prioritizzazione automatica degli strumenti con alto carico fiscale o cedole non compensabili nei veicoli protetti, lasciando gli asset azionari ed ETC compensabili nel conto ordinario.

### `core/autonomous_rebalancer.py` — ✅ Autonomous Rebalancer con WACP/PMC reale & Recupero Minusvalenze
- **Ottimizzazione Tattica di Ribilanciamento**: Generazione autonoma di ordini vincolati a turnover e tolleranza sul tracking error rispetto all'allocazione strategica.
- **Integrazione Fiscale TUIR & Zainetto Fiscale**: Calcolo esatto del capital gain realizzato tramite il Prezzo Medio di Carico (WACP / PMC) reale estratto dalla contabilità FIFO e compensazione preventiva con le minusvalenze pregresse disponibili per minimizzare il carico d'imposta netto generato.

### `core/ui_utils.py` — ✅ Obsidian Sovereign Design System, 5-Block Modals & Vector SVG Icons
- **Standardizzazione Istituzionale Modali Informativi**: Revisione e allineamento di tutte le schede informative sulle metriche di rischio e patrimonio allo schema rigoroso a 5 blocchi: 📌 *Cos'è*, 📐 *Formula Matematica*, 🎯 *Come interpretarlo & Benchmark*, ⚙️ *Implementazione nel Codice*, ⚠️ *Limiti & Falsi Segnali*.
- **Icona Vettoriale SVG Pure-Code**: Risoluzione definitiva delle anomalie di rendering dei caratteri Unicode grazie all'icona SVG vettoriale inline `<circle> + <line>` integrata in `metric_card` e `render_kpi_card`.

### `core/wealth/` & `core/wealth/personal_balance_sheet.py` — ✅ Wealth Ecosystem & Personal Financial Statements
- **`wealth_db.py`**: Star Schema relazionale per conti correnti, cash flow, asset fisici, immobili e snapshot temporali con indici compositi B-Tree ottimizzati per query time-series.
- **`personal_balance_sheet.py`**: Motore contabile per il Bilancio Personale Istituzionale (Personal Financial Statements):
  - *Stato Patrimoniale a Sezioni Contrapposte*: Attivo (Liquidità, Investimenti, Previdenza, Asset Reali, Crediti) vs Passivo (Breve e Medio/Lungo termine) vs Patrimonio Netto con quadratura a pareggio matematico esatto ($\text{Attivo} = \text{Passivo} + \text{Patrimonio Netto}$).
  - *Conto Economico di Gestione*: Rendiconto annuale delle Entrate (Lavoro, Capitale, Donazioni, Rimborsi) e Costi di Vita/Consumi con margine di Risparmio Netto e Savings Rate %.
  - *Rendiconto di Allocazione del Capitale*: Scomposizione del surplus tra investimenti in asset produttivi (PAC Titoli/ETF, Cripto, Fondi Pensione) e riserva liquida.
  - *6 Indici di Bilancio & Rating*: Solvency Ratio ($\ge 70\%$), Debt-to-Assets ($\le 30\%$), Emergency Runway ($\ge 6\text{ mesi}$), Personal Savings Rate ($\ge 20\%$), DSTI ($\le 33\%$), Invested Assets Ratio ($\ge 50\%$) con Radar Chart e rating Private Banking (AAA/AA/A).
- **`wealth_engine.py`**: Modelli computazionali per indipendenza finanziaria (FIRE), simulazione mutui/ammortamenti, calcolo Net Worth at Risk (NWaR), successioni e pianificazione generazionale conforme ad Artt. 536-564 c.c.
- **`asset_protection_engine.py`**: Motore di tutela del patrimonio e **`GenerationalTransferOptimizer`** istituzionale per Family Office HNWI:
  - *Riunione Fittizia (Art. 556 c.c.)*: $\text{Asse} = \max(0, \text{Relictum} - \text{Debiti}) + \text{Donatum}$.
  - *Quote di Riserva e Disponibile (Artt. 536-544 c.c.)*: Risoluzione per tutte le configurazioni (coniuge, figli, ascendenti) con diritto di abitazione art. 540 c.c.
  - *Diagnostica Azione di Riduzione (Artt. 553-564 c.c.)*: Rilevamento lesioni e simulazione conguagli.
  - *Fiscalità Successoria & Donazioni (D.Lgs. 346/1990 TUS)*: Aliquote 4%/6%/8%, franchigie 1M€ / 100k€ e maggiorata ad € 1.500.000 per handicap grave L. 104/1992.
  - *Imposte Ipo-Catastali (D.Lgs. 347/1990)*: 2% + 1% ordinarie o fisse € 400 (€ 200 + € 200) Prima Casa.
  - *Tabella Attuariale Usufrutto (D.P.R. 131/1986)*: Calcolo coefficienti ministeriali usufrutto vitalizio e nuda proprietà per età donante.
  - *Simulazione Dinamica Ante vs. Post*: 4 leve di ottimizzazione (Polizze Vita Ramo I/III esenti art. 12 TUS / art. 1923 c.c., Patto di Famiglia ex art. 768-bis c.c. con esenzione totale art. 3 c. 4-ter TUS, Donazione nuda proprietà, Cointestazione 50% art. 1298 c.c.) e generazione Memorandum Markdown.
- **`wealth_stress_engine.py`**: Motore congiunto di macro stress testing che modella la trasmissione dello shock tassi sull'ammortamento non-lineare dei mutui alla francese ($\Delta PMT$), identifica il *Point of Forced Liquidation* ($t^*$) sul fondo di emergenza, stima la perdita irreversibile da liquidazione forzata di asset depressi e ricalcola il Safe Withdrawal Rate dinamico con regole di Guyton-Klinger.
- **`wealth_importer.py` & `wealth_validator.py`**: Parser universale con tolleranza a format drift e riconciliazione automatica con `DataQualityGate`.
- **`wealth_exporter.py`**: Generazione del Master Workbook Excel (.xlsx multi-tab) sanitizzato con bilancio consolidato e tabelle `ListObject` con formule live.


---

## 4. Architettura dei Moduli Streamlit (`src/` — 21 Moduli Istituzionali)

### 🏛️ SEZIONE 1: QUANTITATIVE RISK & PORTFOLIO BI (Moduli 0 – 11)
1. **`0_Control_Room.py`**: Control Room & Ingestione CSV/DeGiro/Google Sheets Live Sync, Switch Database, Selezione Valuta Base, **Total Wealth Hub (Multi-Account)** con Master Wealth Fusion, **Database & Memory Storage Cockpit** con Donut Chart e 1-Click Maintenance Tools, **⚡ Motore Analitico Embedded DuckDB (OLAP) & Parquet Storage**.
2. **`1_📈_Dashboard_Generale.py`**: Executive Cockpit, Badges Istituzionali, Radar Factor 360°, **Multi-Benchmark Overlay fino a 4 indici con Scorecard**, Early Warning Risk Limits, ARGUS AI Analyst, Quant Copilot e Centro Esportazione Report.
3. **`2_🖥️_Live_Terminal.py`**: Live Market Streaming Tape, Level-2 Order Book (Stoikov Microprice 2018), Fast Ladder Trading, Pre-Trade Risk Checks vincolanti, OMS Execution Blotter (TWAP/VWAP) e Bloomberg CLI (`ARGUS:LIVE>`).
4. **`3_🔴_Analisi_Rischio.py`**: Matrice di Correlazione, Risk Heatmap Grid, Decomposizione Euler VaR/CVaR, Cornish-Fisher CVaR analitico (Boudt 2008), **Volatilità Condizionale GARCH(1,1) & FHS**, **Market Regime Switching (3-State Markov Model)**, Rischio Liquidità (ADV & L-VaR Bangia 1999), Backtesting VaR (Kupiec Test), ATR Chandelier Exit Manager e **Machine Learning Anomaly Detector (Isolation Forest & Correlation Drift)**.
5. **`4_🔬_Modelli_Quantitativi.py`**: Frontiera Efficiente Markowitz (Ledoit-Wolf), **🧬 Tail Copula (Clayton/Gumbel) & Crash Contagion Matrix**, **⚖️ Simulatore Interattivo Trade Sizing (Kelly Criterion)**, **Live Rebalancing Sandbox**, **Hierarchical Risk Parity (HRP — López de Prado)**, Simulatore Monte Carlo (Student-t), **Simulatore Jump-Diffusion di Merton**, Hedging Tattico, **Modello Black-Scholes con Superficie di Volatilità 3D, Skew/Smile Calibration & Covered Call**, Attribuzione Brinson-Fachler, Carino Multi-Periodo (Zero-Residual), Karnosky-Singer FX, Backtest Fattoriale a Quintili, e **Fixed Income YAS / Nelson-Siegel Key Rate Durations (KRD) / Z-Spread / CDS Default Curve**.
6. **`5_📋_Posizioni_e_Dettagli.py`**: Posizioni attive, Costo di carico FIFO, **🪦 Posizioni Chiuse & Graveyard Cockpit Multi-Prospettiva**, **💰 Tax-Loss Harvesting & Step-Up Wizard (TUIR Art. 67)**, **🪙 Modulo Fiscale Cripto-Attività (Quadri RT/RW/IVAFE L. 197/2022)**, Smart Rebalancer, Calendario Dividendi per Azienda e **Modello Almgren-Chriss Optimal Execution Schedule**.
7. **`6_🏛️_Valutazione_Aziendale.py`**: Altman Z-Score, Scomposizione DuPont (3 e 5 fattori), Piotroski F-Score (9pt), **Contabilità Forense: Beneish M-Score & Sloan Accrual Ratio**, WACC CAPM, Valutazione DCF Monte Carlo, Bilanci 10-K, **🔍 Local RAG & SEC Filing Vector Store (10-K/10-Q Q&A)** con Chunking Semantico e RRF, Comparativa Multiaziendale e **Diagnostica Predittiva Machine Learning (Random Forest Distress Risk Classifier)**.
8. **`7_🌪️_Stress_Testing.py`**: MSCI Barra Multi-Scenario Matrix, Beta Shock Waterfall, Macro Scenario Builder interattivo ($\Delta r$, $\Delta \text{FX}$, $\Delta \text{Commodity}$, $\Delta \text{Equity}$) e **Visualizzatore 3D della Superficie di Rischio (Plotly Surface)**.
9. **`8_📊_Analisi_Temporale.py`**: Storicizzazione Multi-Snapshot su Data Warehouse MySQL/SQLite, Evoluzione Temporale del Valore di Portafoglio, Matrice dei Delta ($\Delta$) tra Snapshot e Calcolatore del Tasso di Risparmio & Iniezioni di Liquidità.
10. **`9_📈_Analisi_Tecnica.py`**: Cockpit di Analisi Tecnica & Quantitative Charting, Volume Profile (POC/VAH/VAL), Candlestick Pattern Recognition, Technical Confluence Score Card (0-100), Multi-Timeframe Alignment (1D vs 1W), Screener di Confluenza e **Real-Time Streaming Engine con Ring Buffer L2 & Order Flow Imbalance**.
11. **`10_🔍_Screener_Opportunita.py`**: Screener Quantitativo Multi-Fattoriale (Valutazione, Qualità Contabile, Rischio, Momentum), **⚡ Formula Engine EQS (Custom Query Builder)**, Archetipi Istituzionali, Parallel Multi-Thread Downloader (8 Workers), Granular Cache Invalidation con pulsante `🔄 Forza Live`, Smart Sizing Optimizer, Pre-Trade Impact Simulator e Generatore Factsheet PDF One-Pager.
12. **`11_💻_BQuant_e_Launchpad.py`**: **🐍 ARGUS BQuant Python Sandbox In-App**, **🎛️ ARGUS Launchpad & Workspace Customizer (5 Ruoli Istituzionali)**, **📊 Excel Live Connector & Generatore Formule Bloomberg (=ARGUS_BDP, =ARGUS_BDH, =ARGUS_RISK) con Esportazione Multi-Foglio XLSX**.

### 💎 SEZIONE 2: WEALTH MANAGEMENT & PERSONAL FINANCE (Moduli 12 – 21)
13. **`12_🎛️_Wealth_Control_Room.py`**: Control Room del patrimonio complessivo, sincronizzazione estratti conto bancari, Universal Bank Ingestion Hub (Layout Sniffer) e switch profili patrimoniali.
14. **`13_🏛️_Patrimonio_e_NetWorth.py`**: **Bilancio Personale Istituzionale (Stato Patrimoniale a sezioni contrapposte con quadratura a pareggio, Conto Economico di gestione per anno solare, Waterfall Flussi di Risparmio, 6 Indici di Solidità con Radar e Rating AAA)**, Bilancio patrimoniale consolidato a 5 livelli (Liquidità, Investimenti, Previdenza, Asset Fisici, Passività), **Unified Macro Stress Engine (Shock Tassi, Ammortamento Mutui $\Delta PMT$, Liquidity Squeeze $t^*$ & Guyton-Klinger SWR)**, Family Office Holding Consolidator (PEX 1,2% vs 26%), Currency Overlay ed Advisory Pitchbook PDF a 6 pagine.
15. **`14_💳_Cash_Flow_e_Spese.py`**: Budgeting con regola 50/30/20, diagramma di flusso Sankey interattivo, tracciamento entrate/uscite e diagnosi dei costi fissi.
16. **`15_⌚_Asset_Illiquidi_e_Orologi.py`**: Gestione asset fisici e collezionabili (orologi di lusso, metalli preziosi, opere d'arte) con storico rivalutazioni, perizie e liquidity haircut.
17. **`16_🛡️_Previdenza_e_Pension_Planning.py`**: Simulazione pensione pubblica (INPS) e integrativa, stima del tasso di sostituzione, gap pensionistico e deducibilità fiscale contributi (€5.164,57 annui).
18. **`17_🔥_Indipendenza_Finanziaria_e_FIRE.py`**: Analizzatore di indipendenza finanziaria (FatFIRE, LeanFIRE, CoastFIRE), simulazione stocastica Merton Jump-Diffusion SPI %, Safe Withdrawal Rate (SWR 3%-4%) e target age.
19. **`18_📑_Fiscalita_e_Quadro_RW.py`**: Compilazione pre-dichiarativa per monitoraggio fiscale estero (Quadro RW con giacenza media e picco max, Quadro RT, Quadro RM per dividendi esteri a tassazione sostitutiva, tributo 1100, IVAFE ordinaria 0,20% e Black List 0,40%) e ottimizzazione minusvalenze/step-up fiscale.
20. **`19_🏡_Immobili_e_Mutui.py`**: Registro patrimonio immobiliare, simulazione piani di ammortamento a rate costanti (francese), calcolo LTV dinamico e Net Home Equity.
21. **`20_⚖️_Pianificazione_Successoria.py`**: Simulazione asse ereditario con Riunione Fittizia ex art. 556 c.c., quote di legittima e disponibile secondo il Codice Civile (artt. 536-544 c.c.), diagnosi azione di riduzione (artt. 553-564 c.c.), calcolo imposte di successione (D.Lgs. 346/1990) con franchigie ordinarie e maggiorata L. 104 ad € 1.500.000, imposte ipo-catastali e **Generational Transfer Optimizer (Ante vs. Post)** con 4 leve di ottimizzazione (Polizze Vita esenti art. 12 TUS / art. 1923 c.c., Patto di Famiglia art. 768-bis c.c. con esenzione totale art. 3 c. 4-ter TUS, Donazione Nuda Proprietà con tabella usufrutto per età D.P.R. 131/1986, Cointestazione 50% art. 1298 c.c.) e Memorandum Markdown Family Office.
22. **`21_🤖_AI_Copilot_e_Advisor.py`**: Assistente patrimoniale conversazionale con accesso contestuale ai dati di bilancio consolidato, validazione di aderenza numerica, guardrails MiFID II / Art. 21 TUF ed Executive Voice Briefing a due voci (CIO & CRO).

---

## 5. Suite di Test Automatizzati (PyTest)

Tutti i **510 test automatizzati passano con successo (100%)** distribuiti su 88 file di test (inclusi i test di resilienza SRE Circuit Breaker/Jitter, il modulo `tests/test_estate_planning_optimizer.py` e la suite DBRE `tests/test_migration_manager.py`):

```bash
py -m pytest
```

Output atteso:
```text
======================= 510 passed in ~59.00s (100%) =======================
```

---

*ARGUS Risk & Wealth Analytics Platform — Documento di Handoff Tecnico v8.1.0 Enterprise Release.*
