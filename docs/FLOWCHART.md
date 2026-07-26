# Diagramma di Flusso e Architettura del Sistema: Investment Risk BI Platform

Il flusso di elaborazione di **Investment Risk BI Platform** segue un'architettura **Data Pipeline / ETL** professionale, articolata in **5 livelli (Layers)** distinti e disaccoppiati. Questa struttura garantisce modularità, scalabilità e perfetta separazione delle responsabilità tra validazione dei dati, calcolo quantitativo, persistenza su database relazionale e visualizzazione multilivello.

---

## 🗺️ Diagramma di Flusso Generale (Mermaid)

```mermaid
flowchart TD
    %% -------------------------------------
    %% STYLING (Colori, bordi, font)
    %% -------------------------------------
    classDef source fill:#E1F5FE,stroke:#0288D1,stroke-width:2px,color:#01579B,rx:10,ry:10,font-weight:bold
    classDef script fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#1B5E20,rx:5,ry:5,font-weight:bold
    classDef engine fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#E65100,rx:5,ry:5,font-weight:bold
    classDef storage fill:#ECEFF1,stroke:#607D8B,stroke-width:3px,color:#263238,font-weight:bold
    classDef frontend fill:#F3E5F5,stroke:#8E24AA,stroke-width:2px,color:#4A148C,rx:10,ry:10,font-weight:bold

    %% -------------------------------------
    %% NODI E SUBGRAPHS (Architettura a 5 Livelli)
    %% -------------------------------------
    subgraph Layer1 ["📡 1. DATA SOURCES & INGESTION"]
        direction TB
        CSV[/"📄 File CSV Utente Generico"/]:::source
        DEGIRO[/"📄 Export Broker DeGiro CSV"/]:::source
        YF(("🌐 yfinance API (Prezzi & Metadati)")):::source
    end

    subgraph Layer2 ["⚙️ 2. ETL & VALIDATION PIPELINE"]
        direction TB
        ADAPT{"🔌 core/adapters/degiro.py\n(DeGiro Parser)"}:::script
        VAL{"⚙️ core/validator.py\n(Cleaning & Normalization)"}:::script
        SCH{"🛡️ core/schemas.py\n(Pydantic Data Contracts)"}:::script
        FETCH{"⚙️ core/fetcher.py\n(Market & FX Enrichment)"}:::script
    end

    subgraph Layer3 ["🗄️ 3. DATA WAREHOUSE (MySQL ORM)"]
        direction TB
        DB_RAW[("Tabelle Grezze ORM\n(portfolios, assets, transactions, market_prices)")]:::storage
        DB_SNAP[("Tabelle Snapshot Metriche\n(portfolio_snapshots, snapshot_positions)")]:::storage
    end

    subgraph Layer4 ["🧠 4. ANALYTICS & QUANTITATIVE ENGINE"]
        direction TB
        RE{"⚙️ core/risk_engine.py\n(FIFO Basis, VaR Cornish-Fisher, Kupiec Test,\nLedoit-Wolf SLSQP, Fama-French, Cholesky MC)"}:::engine
        ADV{"🛡️ core/advisor.py\n(ARGUS Quant Advisor & Health Score)"}:::engine
        HEDGE{"🛡️ core/hedging.py\n(Beta-Neutral Hedging & Tail Protection)"}:::engine
        ATTR{"🎯 core/attribution.py\n(Brinson-Fachler Performance Attribution)"}:::engine
        LIMITS{"🚨 core/risk_limits.py\n(Risk Limits & Early Warning Engine)"}:::engine
        TAX{"💰 core/tax_engine.py\n(Tax Optimization & TUIR Art. 67 ETF Rules)"}:::engine
        REBAL{"⚖️ core/rebalancer.py\n(Smart Rebalancer & Order Generator)"}:::engine
        DIV{"📅 core/dividend_engine.py\n(Dividend Forecast & Company Cash Schedule)"}:::engine
        DBEXP{"⚙️ core/db_exporter.py\n(Storicizzazione DB & Multi-Snapshot)"}:::script
    end

    subgraph Layer5 ["📊 5. PRESENTATION & DESKTOP REPORTING LAYER"]
        direction TB
        APP("💻 Streamlit App / Control Room (7 Pagine Live)"):::frontend
        DESK("🖥️ Native Desktop App\n(desktop_launcher.py + WebView2)"):::frontend
        EXE("📦 Standalone Executable\n(dist/ARGUS_Desktop/ARGUS.exe)"):::frontend
        REPEXP{"📄 core/report_exporter.py\n(PDF Factsheet & Multi-Tab Excel)"}:::script
        STARZIP{"🗃️ scripts/export_star_schema.py\n(Power BI Star Schema ZIP Package)"}:::script
        RELZIP{"📦 scripts/package_release.py\n(GitHub Release ZIP Package)"}:::script
        BIEXP{"📤 core/exporter.py\n(Esportatore CSV Denormalizzati)"}:::script
        POWERBI[/"📈 Power BI / Looker Studio\n(Executive Dashboards)"/]:::frontend
    end

    %% -------------------------------------
    %% CONNESSIONI E FLUSSI (Routing)
    %% -------------------------------------
    %% Ingestion & Parsing
    DEGIRO ==>|Parse| ADAPT
    ADAPT --> VAL
    CSV ==>|Upload| VAL
    VAL --> SCH
    SCH --> FETCH
    YF <==>|Request Storici & Tassi FX| FETCH
    FETCH ==>|Insert IGNORE| DB_RAW

    %% Analytics Processing
    DB_RAW ==>|Query ORM| RE
    RE --> ADV
    RE --> REBAL
    RE --> DIV
    RE -->|Genera Snapshot| DBEXP
    DBEXP ==>|Storicizza| DB_SNAP

    %% Presentation & Reporting
    RE ==>|Session State Dataframes| APP
    ADV ==>|Health Score & Alerts| APP
    REBAL ==>|Orders Table| APP
    DIV ==>|Company Cash Flow| APP
    RE ==>|Dati In-Memory| REPEXP
    RE ==>|Dati Denormalizzati| BIEXP
    
    REPEXP -->|Download Direct PDF/Excel| APP
    BIEXP -->|Esporta CSV| POWERBI
    DB_SNAP -.->|Direct Query SQL| POWERBI
```

---

## 🏛️ Descrizione Dettagliata dei 5 Livelli Architetturali

### 1. Data Sources & Ingestion
- **CSV Generico Utente**: File di input contenente le transazioni finanziarie storiche.
- **DeGiro Export Adapter**: File CSV nativo esportato direttamente dalla piattaforma DeGiro, parsato e convertito automaticamente nello schema standard del sistema via `core/adapters/degiro.py`.
- **yfinance API**: Fonte dati di mercato live per il recupero delle serie storiche dei prezzi di chiusura rettificati (*Adjusted Close*), metadati aziendali (GICS Sector, Country) e tassi di cambio multi-valuta (es. EUR/USD, DKK/EUR).

### 2. ETL & Validation Pipeline
- **`core/validator.py`**: Pipeline a 11 passaggi per la bonifica dei dati (sanitizzazione stringhe, normalizzazione date in formato ISO `YYYY-MM-DD`, correzione ticker crypto e valute).
- **`core/schemas.py`**: Validazione rigorosa a runtime dei contratti dati mediante modelli Pydantic / Dataclasses per intercettare incongruenze o anomalie prima dell'ingestione.
- **`core/fetcher.py`**: Gestione del lookback window a 365 giorni precedenti alla prima transazione, mapping automatico ISIN $\rightarrow$ Ticker tramite `config.json` e chiamate ottimizzate a Yahoo Finance con risoluzione dinamica delle conversioni valutarie verso la valuta base.

### 3. Data Warehouse (MySQL ORM)
- **`core/models.py`**: Struttura relazionale gestita tramite classi dichiarative SQLAlchemy ORM.
  - *Tabelle Grezze*: `portfolios`, `assets`, `transactions`, `market_prices` (con vincolo `UNIQUE(asset_id, price_date)` e query `INSERT IGNORE` per prevenire duplicazioni).
  - *Tabelle Snapshot*: `portfolio_snapshots`, `snapshot_positions` per il tracciamento temporale delle metriche di rischio e dei cluster calcolati ad ogni esecuzione.

### 4. Analytics & Quantitative Engine
- **`core/risk_engine.py`**: Il cervello quantitativo dell'applicazione (FIFO, VaR Cornish-Fisher, Kupiec Test, Markowitz, Monte Carlo Cholesky, Fama-French, K-Means).
- **`core/advisor.py`**: Motore di diagnostica quantitativa e calcolo dello Health Score (0-100) basato su anomalie di concentrazione, Component VaR, P/E elevati e potenziale Sharpe delta.
- **`core/rebalancer.py`**: Generatore di ordini di trading in € e n° quote intere per l'allineamento a strategie target con gestione di versamenti/prelievi di cassa (+/- €).
- **`core/dividend_engine.py`**: Calcolo del Dividend Yield medio, dividendi storici reali e proiezione del calendario di incassi mensili per singola azienda pagatrice.
- **`core/db_exporter.py`**: Layer di storicizzazione snapshot su MySQL e recupero delle serie storiche per l'analisi temporale multi-run.

### 5. Presentation & Desktop Reporting Layer
- **Streamlit App & Desktop Launcher (`desktop_launcher.py` & `app.py`)**: Dashboard a 7 pagine interattive fruibile sia via browser sia come **Applicazione Desktop Nativa Windows** (`pywebview` + Edge WebView2) con l'icona personalizzata **Occhio di Argus**, gestione del ciclo di vita dei processi ed avvio protetto con polling attivo `wait_for_server`.
- **Standalone Executable & Release Pipeline (`scripts/build_desktop_app.py` & `scripts/package_release.py`)**: Pacchetto eseguibile standalone `ARGUS.exe` e generatore dell'archivio distribuiscibile `ARGUS_Desktop_v5.0.zip` per la pubblicazione su GitHub Releases.
- **`core/report_exporter.py`**: Generazione dinamica in-memory sia del report Executive PDF Factsheet (2 pagine) sia del Workbook Excel Multi-Tab (.xlsx) con 4 schede tematiche.
- **`core/exporter.py` & `scripts/export_star_schema.py`**: Esportazione di tabelle denormalizzate e Star Schema in formato `.zip` per la connessione nativa verso Microsoft Power BI e Google Looker Studio.
