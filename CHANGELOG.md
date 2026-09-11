# Changelog

Tutti i cambiamenti significativi a questo progetto saranno documentati in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce a [Semantic Versioning](https://semver.org/lang/it/).

---

## [9.0.0] - 2026-09-11

### 🚀 Major Release — Dual-Engine Institutional Overhaul, Quantitative Model Validation & Production Readiness

Questa major release formalizza l'evoluzione di **ARGUS** da piattaforma monolitica a **Ecosistema Quantitativo Istituzionale di Classe Tier-1**, introducendo la completa segregazione operativa tra Risk Management e Wealth Intelligence, una suite esaustiva di validazione dei modelli conformi a **Federal Reserve SR 11-7**, il modulo di reporting vettoriale MiFID II a 2 pagine e l'onboarding interattivo per nuovi utenti.

### Aggiunto (Added)
- **Dual-Engine Sidebar Navigation Rail**:
  - Segregazione strutturale tra il modulo *Risk Analytics & Quantitative Intelligence* (11 pagine) e il modulo *Wealth Management & Fiscalità Patrimoniale* (11 pagine).
  - Navigation Rail ad albero con sottomenu e sub-tab binding deterministico bidirezionale.
  - Selettore modalità di esecuzione in cima alla sidebar con persistenza della sessione e isolamento dello stato.
  - Snellimento dei parametri di calcolo con container comprimibili *"Impostazioni Avanzate di Calcolo"* e smart defaults istituzionali.
- **Model Risk Management & Validazione Quantitativa (SR 11-7 Guidelines)**:
  - Validazione formale del Value at Risk (VaR) ed Expected Shortfall (CVaR) parametrico, simulazione storica ed espansione di Cornish-Fisher.
  - Regolarizzazione delle matrici di covarianza empiriche tramite shrinkage di Ledoit-Wolf per garantire la stretta semidefinita positività ($M > 0$) e prevenire errori di inversione in portafogli illiquidi o con elevato numero di asset.
  - Backtesting statistico del VaR mediante test di copertura incondizionata di Kupiec (*Likelihood Ratio Test*) per la calibrazione dinamica del livello di confidenza.
- **Enterprise Data Quality Gate (Pydantic v2)**:
  - Middleware di pre-ingestione con contratti dichiarativi (`CanonicalTradeRecord`, `QualityGateReport`).
  - Deduplicazione deterministica a chiave naturale SHA-256 (`tx_hash`) per l'idempotenza assoluta nei ricaricamenti contabili.
  - Riconciliazione cross-broker di valute estere con serie storiche ufficiali BCE (con forward-fill su festività TARGET2).
  - Normalizzazione delle serie storiche dei prezzi con allineamento dei calendari di negoziazione (Borsa Italiana vs NYSE/NASDAQ) e gestione dei corporate actions.
- **Institutional Factsheet Engine & ReportLab Vector Exporter**:
  - Exporter PDF vettoriale a 2 pagine conforme agli standard di rendicontazione MiFID II e riepilogo fiscale Quadro RW.
  - Disaccoppiamento tra rendering interattivo a schermo (Plotly WebGL) e rendering vettoriale per stampa ad alta risoluzione (ReportLab A4 `InstitutionalNumberedCanvas`).
  - Generatore di Executive Summary Excel con tabelle native `ListObject` e formule live (`XIRR`, somme condizionali).
- **Empty-State Experience & 5-Pillar Demo Seeder**:
  - Schermata di accoglienza al primo avvio privo di portafoglio, con card contestuale di benvenuto e guida al caricamento dati.
  - Iniezione atomica 1-click del portafoglio dimostrativo realistico sui 5 pilastri (*Liquidità, BTP/Treasury, Azioni Globali, Real Estate, Capitale Umano Attuariale*).
- **Headless Core REST API (`api/main.py`)**:
  - Server asincrono FastAPI v9.0.0 per l'integrazione di ARGUS in pipeline di produzione e notebook Jupyter.
  - Endpoint `/health`, `/api/v1/risk/metrics`, `/api/v1/optimize/hrp`, `/api/v1/ledger/timetravel` con contratti Pydantic e OpenAPI Swagger interattivo.

### Modificato (Changed)
- **Architettura Caching & Streamlit Lifecycle**:
  - Gerarchizzazione rigorosa tra `@st.cache_data` (ingestione CSV, download serie storiche, FX rates) e `@st.cache_resource` (connessioni DB SQLAlchemy/DuckDB, motori di ottimizzazione).
  - Snapshot di sessione esportabili in JSON atomico (`schema_version: "9.0.0"`) per la portabilità completa tra dispositivi e ambienti di test.
- **Contabilità Fiscale & WACP / PMC Reale**:
  - Inclusione formale delle commissioni d'acquisto nel costo di carico fiscalmente riconosciuto (Prezzo Medio di Carico ex TUIR).
  - Separazione vincolante tra *Redditi di Capitale* (plusvalenze ETF tassate al 26% non compensabili) e *Redditi Diversi* (azioni, bond, ETC con compensazione minusvalenze pregresse).
- **Test Suite PyTest**:
  - Espansione della copertura a **597 test automatizzati (100% passed)** su 99 moduli di test, includendo regression test completi su tutte le 22 pagine istituzionali.

### Risolto (Fixed)
- Risolto disallineamento nei dividendi frazionati e nelle transazioni multi-valuta con commissioni in valuta estera.
- Risolto potenziale blocco da orfani referenziali tramite controllo di integrità relazionale SQLite/DuckDB.
- Sanificazione preventiva anti-Formula Injection (CWE-1236) su tutti gli esportatori CSV e fogli di calcolo Excel XLSX.
- Correzione dei tag di versione obsoleti nei template di sistema, header di modulo e workflow CI/CD.

---

## [8.4.0] - 2026-08-20
- Disaccoppiamento del motore quantitativo dal front-end Streamlit (Headless Analytical Package `argus-risk`).
- Microservizio REST API con FastAPI e documentazione OpenAPI Swagger.
- Portale di documentazione interattivo Material for MkDocs.

---

## [8.1.0] - 2026-06-15
- Next-Level Enterprise Transformation: Universal One-Ledger Core su DuckDB C++ e PyArrow.
- Human Capital Valuation e Total Balance Sheet VaR (TBS-VaR 95%).
- Prescriptive Conic Rebalancer con protocollo FIX 4.4.
- Tri-Agent AI Quantitative Governance Council.
- Decomposizione del rischio fattoriale MSCI Barra GEM3/USE4 con teorema di Eulero.
- Total Balance Sheet Lifetime Monte Carlo Simulation Engine.

---

## [7.0.0] - 2026-03-30
- Enterprise Masterplan: Cross-Asset Macro Factor Stress Bridge Engine.
- Tax-Aware Asset Location Optimizer e Autonomous Rebalancer.
- Calibrazione zero-coupon Nelson-Siegel & Key Rate Durations a 5 nodi.
- Stima del Liquidity-Adjusted Value at Risk (L-VaR Bangia 1999).

---

## [6.3.0] - 2026-01-10
- Institutional Navigation Rail con Spotlight Search.
- Live Terminal Desk con console comandi Bloomberg Parity.
- Suite Fiscale Avanzata con quadri precompilati RT, RW e RM per Modello Redditi PF.
- Support Bundle diagnostico 1-click e telemetria strutturata JSONL.
