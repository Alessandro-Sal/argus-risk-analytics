# Slide di Presentazione per la Discussione del Capstone Project
**Titolo:** ARGUS — Business Intelligence, Financial Valuation & Quantitative Risk Management Platform  
**Autore:** Candidato Master in Data Analytics  

---

## Slide 1: Titolo della Presentazione
- **Titolo**: ARGUS — Institutional Risk Analytics & Wealth Intelligence Platform
- **Sottotitolo**: Framework Quantitativo Multi-Asset per l'Analisi di Portafoglio, Valutazione Aziendale, Pianificazione Patrimoniale e Protezione dal Rischio
- **Candidato**: Master in Data Analytics (Finanza Quantitativa & Risk Management)
- **Visual**: Logo / Banner "L'Occhio di Argus" e Badge Version v10.0.0 Enterprise Release.

---

## Slide 2: Il Problema & Gli Obiettivi di Progetto
- **La Sfida**: Gli investitori privati, i Family Office e i desk quantitativi mancano di strumenti integrati ad alta precisione che combinino contabilità fiscale FIFO, stima rigorosa del rischio di coda (VaR/CVaR), bilancio patrimoniale consolidato e reporting direzionale istituzionale.
- **La Soluzione (ARGUS v10.0.0)**:
  - Piattaforma end-to-end con architettura a due macro-ambienti: **Trading & Risk Desk** e **Wealth & Family Office**.
  - Validazione empirica su **~400 operazioni REALI** (2021–2026 dal dataset WealthApp).
  - Persistenza ibrida: **SQLite locale offline** (zero dipendenze di rete) $\leftrightarrow$ **Supabase Cloud PostgreSQL 16 (AWS EU-West-1)** con isolamento multi-tenant rigoroso.
  - Estetica terminale ad alta densità informativa (*Obsidian Sovereign*) fruibile via Web o Desktop Nativo Windows (WebView2).

---

## Slide 3: Architettura del Sistema a 5 Livelli
- **Layer 1 (Data Ingestion & Multi-Broker Hub)**: Ingestione universale CSV, parser nativi (Directa, DeGiro, Fineco, IBKR, Trade Republic, Scalable, eToro, Revolut), estratti conto bancari universali e connettori live Yahoo Finance / crypto.
- **Layer 2 (ETL & Validation Pipeline)**: Data Quality Gate (Pydantic v2), deduplicazione deterministica SHA-256 (`tx_hash`), risoluzione ISIN su borse europee (.MI, .DE, .PA) e tassi FX ufficiali BCE.
- **Layer 3 (Data Warehouse & Multi-Engine Storage)**: Persistenza duale SQLAlchemy ORM (Supabase PostgreSQL 16 SSL, SQLite locale `argus_local.db` & `argus_wealth.db`, MySQL 8.0) e motore analitico vettorizzato DuckDB C++ con PyArrow.
- **Layer 4 (Analytics, Wealth & Quantitative Engine)**: FIFO WACP, Cornish-Fisher VaR/CVaR, Kupiec Backtest, Markowitz SLSQP, Ledoit-Wolf Shrinkage, HRP, Black-Litterman, Fama-French, Almgren-Chriss, Heston FFT, SABR/SVI, Solvency II SCR, ISDA SIMM v2.6 e Total Balance Sheet Monte Carlo (5.000 path).
- **Layer 5 (Presentation, UI Core & Institutional Reporting Layer)**: Streamlit (22 Moduli Live: Pagine 0-21), design system modulare `components/ui_core/` con zero-flicker CSS engine, native desktop app (Edge WebView2), exporter PDF vettoriali (Factsheet & Pitchbook A4 6-pagine), Excel Live RTD e Star Schema ZIP per Power BI / Looker Studio.

---

## Slide 4: Motore Quantitativo di Rischio & Tail Risk
- **Contabilità FIFO Rigorosa**: Prezzo medio ponderato di carico (WACP), separazione PnL realizzato/non realizzato e rettifica istantanea per Corporate Actions (stock split).
- **Value at Risk (VaR) & Conditional VaR (CVaR)**: Stima a confidenza 95% e 99% con modello Cornish-Fisher (correzione per Skewness & Kurtosis) e Boudt-Peterson-Croux mCVaR sub-additivo.
- **Validazione Regolamentare VaR**: Backtest Kupiec POF su 252 giorni con classificazione a semaforo dell'Accordo di Basilea (*Verde/Giallo/Rosso*) e test di indipendenza di Christoffersen.
- **Style Analysis Fama-French & Carhart**: Regressione multivariata per determinare $\alpha_{FF}$, Beta di mercato, Size tilt (SMB), Value tilt (HML) e Momentum tilt (WML).

---

## Slide 5: Simulazione Stocastica Monte Carlo & Stress Testing
- **Monte Carlo Fan / Ribbon Chart**: Proiezione stocastica su 10.000 cammini con Moto Browniano Geometrico, decomposizione di Cholesky e supporto code grasse (Student-t $\nu=5$).
- **MSCI Barra Multi-Scenario Matrix**: Stima immediata dell'impatto finanziario nei 5 grandi crolli storici (*Dot-Com 2000*, *Lehman 2008*, *US Downgrade 2011*, *COVID-19*, *Rate Shock 2022*).
- **Unified Stress Bridge & Macro Shock Waterfall**: Propagazione congiunta degli shock macroeconomici dalle posizioni mobiliari di trading al bilancio patrimoniale complessivo (immobili, mutui, fondi pensione, orologi e passività).

---

## Slide 6: Analisi dei Bilanci & Solvibilità Aziendale
- **Altman Z-Score Model**: Previsione del rischio di insolvenza a 24 mesi con verdetto a semaforo (*Safe*, *Grey*, *Distress*).
- **Scomposizione DuPont (3 & 5 Fattori)**: Decomposizione del ROE nei driver di redditività operativa, efficienza dell'attivo e leva finanziaria.
- **Piotroski F-Score (9 Punti Stanford)**: Diagnosi di salute contabile su Profittabilità, Liquidità ed Efficienza.
- **Valutazione Intrinseca DCF Monte Carlo**: 2-Stage Discounted Cash Flow a 1.000 iterazioni stocastiche con probabilità % di sottovalutazione.
- **Consultazione Bilanci 10-K & Radar Multiaziendale**: Confronto affiancato di 2+ aziende con grafico Radar sovrapposto ed estrazione automatica dai filing SEC.

---

## Slide 7: Ribilanciamento, Wealth Suite & Fiscalità Italiana
- **Prescriptive Rebalancer (FIX 4.4)**: Generatore esatto di ordini di negoziazione ad azioni intere ($BUY/SELL$) vincolati e formattati secondo lo standard FIX Protocol 4.4.
- **Personal Financial Statements (Stato Patrimoniale & Conto Economico)**: Bilancio a sezioni contrapposte, calcolo del Net Worth consolidato, ammortamento mutui alla francese, asset illiquidi/orologi e successione generazionale.
- **Suite Fiscale Italiana**: 
  - Distinzione tra **Redditi di Capitale** (ETF UCITS, dividendi, non compensabili con minusvalenze) e **Redditi Diversi** (azioni, ETC, certificates).
  - Aliquota 12.5% Titoli di Stato vs 26.0% Azioni/ETF vs disciplina Cripto-attività 2026.
  - Monitoraggio **Quadro RW, IVAFE (0,2% vs 0,4%) e IVIE (1,06%)**, con gestione quadriennale dello Zainetto Fiscale ($T+4$).

---

## Slide 8: Centro Esportazione Report & Business Intelligence
- **Report PDF Factsheet (2 Pagine) & Pitchbook Advisory (6 Pagine)**: Generati in-memory con ReportLab e canvas a due passaggi `InstitutionalNumberedCanvas`.
- **Workbook Excel Multi-Tab (.xlsx)**: Tabelle native `ListObject`, formule live sanitizzate anti-formula injection (CWE-1236) e connettore Bloomberg RTD (`=ARGUS_BDP`, `=ARGUS_RISK`).
- **Report Standalone HTML**: Esportazione di dashboard reattiva autonoma in dark mode.
- **Star Schema ZIP per Power BI / Looker Studio**: Archivio `.zip` con `dim_assets.csv`, `fact_positions.csv` e `fact_portfolio_summary.csv` per modelli direzionali relazionali.

---

## Slide 9: Architettura Ibrida Desktop & Cloud Multi-Tenant
- **Desktop Nativa Windows (Edge WebView2)**: Shell nativa basata su **PyWebView** con icona dell'**Occhio di Argus**, lifecycle manager integrato e backup atomico pre-flight.
- **Cloud-Native Multi-Tenant (Streamlit Cloud + Supabase)**: 
  - Portale di accesso istituzionale pre-splash con hashing password **PBKDF2-HMAC-SHA256** (120.000 iterazioni).
  - Segregazione rigorosa dei portafogli e delle posizioni via `user_id` crittografico UUID (Zero-Leakage Multi-Tenancy).
  - Supporto BYOD (*Bring Your Own Database*) per connettere istanze PostgreSQL esterne dedicate.

---

## Slide 10: Risultati Sperimentali & Test Suite (970/970 PASSED - 100%)
- **Validazione su Dataset Reale**: Precisione deterministica centesimale su oltre 400 transazioni reali del dataset storico WealthApp (2021–2026).
- **Test Suite Automatizzata**: **970 test PyTest superati al 100%** su risk engine, modelli econometrici, isolamento multi-tenant, motori fiscali, stress bridge ed esportazione report.
- **Performance**: Calcolo sub-secondo per la maggior parte dei motori analitici e rendering dell'interfaccia a 0-flicker grazie alla gestione del ciclo di vita CSS via `ctx.cursors`.

---

## Slide 11: Conclusioni & Sviluppi Futuri
- **Risultati Raggiunti**: Piattaforma quantitativa e patrimoniale completa a 22 moduli, conforme a standard regolamentari (Basilea IV, Solvency II, ISDA SIMM, MiFID II) e pronta per l'operatività multi-tenant.
- **Prossimi Passi**: Integrazione diretta con broker API (Interactive Brokers TWS Client / Directa Open API) per l'instradamento automatico degli ordini FIX e scheduler di ribilanciamento notturno.
