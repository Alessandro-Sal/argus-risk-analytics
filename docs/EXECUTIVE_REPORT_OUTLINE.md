# Struttura Dettagliata del Report di Capstone Project (Tesi Finale)
**Titolo Progetto:** ARGUS — Business Intelligence, Financial Valuation & Quantitative Risk Management Platform
**Corso di Studi:** Master in Data Analytics (Specializzazione Finanza Quantitativa)

---

## Indice Generale della Tesi

### Capitolo 1: Introduzione e Inquadramento del Problema
1.1 **Contesto del Mercato Finanziario Moderno**: Necessità di strumenti trasparenti ed istituzionali per investitori privati e family office per il monitoraggio del rischio multi-asset.  
1.2 **Gli Obiettivi del Capstone Project**: Sviluppo di una piattaforma integrata di Business Intelligence, valutazione aziendale e gestione del rischio quantitativo.  
1.3 **Architettura e Principi Guida**: Autonomia nativa, zero dati sintetici, estetica terminale ad alta densità (Dark Mode) e supporto per casi limite reali.  
1.4 **Struttura del Documento**: Panoramica della trattazione.

### Capitolo 2: Ingestione Dati, ETL & Architettura Data Warehouse
2.1 **Fonti Dati & Broker Ingestion**: Normalizzazione di file CSV generici e parser dedicato per gli export nativi del broker DeGiro (`core/adapters/degiro.py`).  
2.2 **Pipeline di Validazione & Data Contracts**: Bonifica in 11 passaggi (`core/validator.py`), modelli Pydantic (`core/schemas.py`) e mapping ISIN-Ticker via Yahoo Finance.  
2.3 **Modello Relazionale Data Warehouse (SQLAlchemy ORM)**: Mappatura delle tabelle grezze (`portfolios`, `assets`, `transactions`, `market_prices`) e snapshot temporali (`portfolio_snapshots`, `snapshot_positions`).  
2.4 **Architettura Fallback Dual-Engine**: Gestione trasparente del passaggio tra MySQL 8.0 ed il database locale SQLite (`data/argus_local.db`).

### Capitolo 3: Motore Quantitativo & Misurazione del Rischio
3.1 **Contabilità FIFO (First-In, First-Out)**: Tracciamento dei lotti di acquisto/vendita per il calcolo esatto del Prezzo Medio di Carico (WACP) e separazione PnL realizzato/non realizzato.  
3.2 **Analisi delle Code & Metriche di Mercato**: Volatilità annualizzata, Skewness, Kurtosis e Tracking Error.  
3.3 **Stima del Value at Risk (VaR) e Conditional VaR (CVaR)**: Confronto metodologico tra VaR Storico, VaR Parametrico e VaR Cornish-Fisher con correzione per asimmetria e curtosi.  
3.4 **Validazione Regolamentare tramite Kupiec POF Test**: Backtesting del VaR su 252 giorni di negoziazione e classificazione secondo il semaforo dell'Accordo di Basilea.  
3.5 **Style Analysis Fama-French (3 Fattori)**: Regressione multivariata per l'estrazione di Alpha puro ($\alpha_{FF}$), Beta di mercato, Size tilt (SMB) e Value tilt (HML).  
3.6 **Simulazione Stocastica Monte Carlo Fan / Ribbon Chart**: Modellizzazione stocastica su 10.000 cammini con Moto Browniano Geometrico, decomposizione di Cholesky e supporto per distribuzioni Student-t ($\nu=5$).

### Capitolo 4: Valutazione Aziendale, Solvibilità & Diagnostica di Bilancio
4.1 **Altman Z-Score Model (1968)**: Previsione dell'insolvenza a 24 mesi con verdetto a semaforo per le aziende in portafoglio.  
4.2 **Scomposizione DuPont (3 e 5 Fattori)**: Decomposizione del ROE nei driver di redditività margin, rotazione dell'attivo e leva finanziaria.  
4.3 **Piotroski F-Score (9 Punti Stanford)**: Valutazione di salute contabile basata su 9 segnali binari.  
4.4 **Stima Dinamica del WACC via CAPM**: Costo del capitale medio ponderato con tasso dell'equity CAPM e costo del debito netto.  
4.5 **Valutazione Intrinseca DCF Monte Carlo**: Modello Discounted Cash Flow a 2 stadi con 1.000 iterazioni stocastiche per la stima del Fair Value per azione e della probabilità di sottovalutazione.  
4.6 **Consultazione Bilanci 10-K & Comparativa Multiaziendale**: Download ed estrazione dei bilanci ufficiali e confronto affiancato tra competitor.

### Capitolo 5: Ottimizzazione di Portafoglio, Ribilanciamento & Fiscalità
5.1 **Frontiera Efficiente di Markowitz & Ledoit-Wolf Shrinkage**: Risoluzione vincolata via SciPy SLSQP per Max Sharpe e Min Volatility con contrazione della covarianza.  
5.2 **Smart Rebalancer & Ordini di Trading**: Generazione di ordini ad azioni intere e gestione del buffer di cassa residuo.  
5.3 **Ottimizzazione Fiscale TUIR Art. 67**: Aliquote d'imposta (12.5% vs 26.0%), disciplina delle plusvalenze da ETF ed advisor per il Tax-Loss Harvesting.  
5.4 **Early Warning System & Limiti di Rischio**: Monitoraggio in tempo reale di 6 regole di rischio istituzionali (`core/risk_limits.py`).  
5.5 **Ecosistema Wealth & Family Office**: Pianificazione patrimoniale, bilancio personale a sezioni contrapposte, dinamica del Net Worth, simulatore mutui alla francese e successione generazionale.

### Capitolo 6: Stress Testing, Reporting, UI Modulare & Architettura Cloud
6.1 **MSCI Barra Multi-Scenario Matrix & Beta Shock Waterfall**: Stima delle perdite nei 5 principali crolli storici e shock arbitrari sul benchmark.  
6.2 **Centro Esportazione Report Multi-Formato**: Generazione in-memory di Factsheet PDF (ReportLab), Workbook Excel Multi-Tab (.xlsx), Report HTML Standalone e pacchetto Star Schema ZIP per Power BI.  
6.3 **Architettura Desktop Nativa Windows**: Shell nativa basata su PyWebView (Edge WebView2), eseguibile standalone `ARGUS.exe` e lifecycle manager.  
6.4 **Architettura Cloud Multi-Tenant & Persistenza Ibrida (v10.0.0)**: Supabase PostgreSQL 16 SSL Pooler, isolamento PBKDF2-SHA256 zero-leakage, e design system modulare `components/ui_core/` con motore zero-flicker.

### Capitolo 7: Risultati Sperimentali & Caso di Studio Reale
7.1 **Descrizione del Dataset di Prova**: Analisi delle ~400 transazioni reali del dataset WealthApp (2021–2026).  
7.2 **Validazione dei Risultati Quantitativi**: Verifica delle metriche PnL, VaR backtest e rendimenti aggregati.  
7.3 **Test Suite Automatizzata & Benchmarking**: Copertura completa con 970 test PyTest (100% passed), zero-leakage test su multi-tenancy, e latenza di rendering sub-secondo.

### Capitolo 8: Conclusioni e Sviluppi Futuri
8.1 **Sintesi dei Risultati Raggiunti**.  
8.2 **Sviluppi Futuri**: Integrazione API Broker Live (Interactive Brokers API) e scheduler notturno (APScheduler).
