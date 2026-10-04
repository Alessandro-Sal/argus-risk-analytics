"""Script di utilità per rigenerare e validare la struttura del repository in README.md."""

import os
import sys


def build_tree():
    lines = []
    lines.append("```text")
    lines.append("argus-risk-analytics/")
    lines.append("├── .github/                     # Workflows di CI/CD e Release automatizzata")
    lines.append("│   └── workflows/")
    lines.append("│       ├── ci.yml")
    lines.append("│       ├── deploy-pages.yml")
    lines.append("│       └── release.yml")
    lines.append("├── api/                         # Headless FastAPI Microservice (REST OpenAPI & WebSocket Gateway)")
    lines.append("│   ├── __init__.py")
    lines.append("│   └── main.py                  # API Hub v9.19.0: 40+ Endpoint Istituzionali (SIMM, XVA, FRTB, Heston, Solvency II)")
    lines.append("├── components/                  # Modali Istituzionali @st.dialog, Command Palette (Ctrl+K) & Splash Screen")
    lines.append("│   ├── __init__.py")
    lines.append("│   ├── action_drawers.py        # Institutional Drawers (Pre-Trade Blotter, TUIR Lot Inspector, Euler Risk)")
    lines.append("│   ├── command_palette.py       # Bloomberg-Style Command Palette (Ctrl+K) & Switcher Multi-Modulo")
    lines.append("│   └── splash.py                # Bootloader Splash Screen, Animated Vector Logo & Diagnostics")
    lines.append("├── config/                      # Configurazione e mapping ISIN-Ticker")
    lines.append("│   └── config.json")
    lines.append("├── core/                        # Engine quantitativo, calcoli di rischio e moduli istituzionali")
    lines.append("│   ├── adapters/                # Adapter per broker esterni (DeGiro, Directa, Fineco, IBKR, ecc.)")
    lines.append("│   │   ├── __init__.py")
    lines.append("│   │   ├── broker_hub.py        # Hub centralizzato di rilevamento ed esecuzione adapter")
    lines.append("│   │   ├── degiro.py            # Adapter DeGiro CSV (formato standard e avanzato con commissioni)")
    lines.append("│   │   ├── directa.py           # Adapter Directa SIM CSV")
    lines.append("│   │   ├── etoro.py             # Adapter eToro Account Statement XLSX/CSV")
    lines.append("│   │   ├── fineco.py            # Adapter Fineco Bank estratto conto titoli e liquidità")
    lines.append("│   │   ├── ibkr.py              # Adapter Interactive Brokers (IBKR) Activity Statement CSV/XML")
    lines.append("│   │   ├── isin_resolver.py     # Risoluzione deterministica ISIN <-> Ticker via cache e lookup online")
    lines.append("│   │   ├── revolut.py           # Adapter Revolut Trading CSV")
    lines.append("│   │   ├── scalable.py          # Adapter Scalable Capital Baader Bank PDF/CSV")
    lines.append("│   │   └── traderepublic.py     # Adapter Trade Republic PDF/CSV")
    lines.append("│   ├── i18n/                    # Framework Internazionalizzazione, L10n & Multi-Currency FX Engine")
    lines.append("│   │   ├── __init__.py")
    lines.append("│   │   ├── formatters.py        # Regional Number/Date Formatters, Wall Street Accounting & Currencies")
    lines.append("│   │   ├── fx_engine.py         # ECB Official Historical Rates, Triangular Arbitrage & FX Risk Decomposition")
    lines.append("│   │   ├── translator.py        # O(1) Key-Path Translation Engine con Interpolazione & Fallback")
    lines.append("│   │   └── locales/             # Dizionari Linguistici Strutturati")
    lines.append("│   │       ├── en.json          # Dizionario istituzionale lingua inglese")
    lines.append("│   │       └── it.json          # Dizionario istituzionale lingua italiana")
    lines.append("│   ├── wealth/                  # Wealth Management & Personal Finance Subsystem (27 Moduli)")
    lines.append("│   │   ├── __init__.py")
    lines.append("│   │   ├── asset_protection_engine.py # Asset Protection, Trust, Fondo Patrimoniale, Polizze & Holding (S.s.)")
    lines.append("│   │   ├── glidepath_engine.py  # Goal-Based Dynamic Glide Path 3D & Life Events Probabilistic Engine")
    lines.append("│   │   ├── human_capital_engine.py # Human Capital Actuarial Valuation, Quasi-Asset & TBS-VaR")
    lines.append("│   │   ├── neural_advisor_engine.py # Neural Wealth Advisor & Conversational Action Memo Engine")
    lines.append("│   │   ├── personal_balance_sheet.py # Personal Balance Sheet & Net Worth Reconciliation")
    lines.append("│   │   ├── private_markets_engine.py # Private Equity, Venture Capital, J-Curve & Illiquid Valuation")
    lines.append("│   │   ├── succession_optimizer.py # Generational Transfer Optimizer, Patto di Famiglia & Nuda Proprietà")
    lines.append("│   │   ├── tax_aware_location.py # Tax-Aware Asset Location & Frictional Optimization (TUIR Art. 44 vs 67)")
    lines.append("│   │   ├── tbs_monte_carlo.py   # Lifetime Total Balance Sheet Monte Carlo Engine (5000 Paths)")
    lines.append("│   │   ├── total_wealth_reverse_stress.py # Reverse Stress Testing sul Patrimonio Netto Consolidato (Solvency II)")
    lines.append("│   │   ├── unified_stress_bridge.py # Cross-Asset Macro Factor Stress Bridge Engine")
    lines.append("│   │   ├── universal_bank_parser.py # Universal Bank Ingestion Hub & Multi-Broker Layout Sniffer")
    lines.append("│   │   ├── wealth_db.py         # SQLite / MySQL Star Schema & Snapshot Storicizzati Wealth")
    lines.append("│   │   ├── wealth_engine.py     # Net Worth Engine, FIRE SWR, Mutui alla Francese & Dynamic Glide Path")
    lines.append("│   │   ├── wealth_exporter.py   # Master Excel Dossier & Multi-Tab Exporter (.xlsx)")
    lines.append("│   │   ├── wealth_importer.py   # Ingestion Pipeline & Transaction Deduplication SHA-256")
    lines.append("│   │   ├── wealth_modals.py     # Modali Informativi ed Educativi Istituzionali Wealth (@st.dialog)")
    lines.append("│   │   ├── wealth_models.py     # Schemi, Enums e Dataclass tipizzate di bilancio personale")
    lines.append("│   │   ├── wealth_olap.py       # Motore OLAP Vettorizzato DuckDB In-Memory & Aggregazioni Temporali")
    lines.append("│   │   ├── wealth_reporting_hub.py # Centralized Wealth Reporting & Factsheet Hub")
    lines.append("│   │   ├── wealth_snapshot.py   # Gestione snapshot patrimoniali temporali e riconciliazione Net Worth")
    lines.append("│   │   ├── wealth_stress_engine.py # Unified Macro Stress Engine & French Mortgage Variable Rate Model")
    lines.append("│   │   ├── wealth_sync.py       # Sincronizzazione Google Sheets & Config_FixedExpenses")
    lines.append("│   │   ├── wealth_temporal_engine.py # Time-Series Wealth Analytics & Historic Reconciliation")
    lines.append("│   │   ├── wealth_validator.py  # Validazione template e formati bancari italiani")
    lines.append("│   │   └── wealth_watchdog.py   # Smart Financial Watchdog & Proactive Anomaly Alert Engine")

    core_desc = {
        "__init__.py": "Package init e versione dell'ecosistema (v9.19.0)",
        "advanced_quant.py": "Tail Copulas, Kelly Criterion & Equal Risk Contribution (ERC)",
        "advisor.py": "ARGUS Quant Advisor & Health Score Engine",
        "ai_analyst.py": "AI & LLM Narrative Intelligence (Gemini/OpenAI & NLG Offline)",
        "alm_ldi_engine.py": "ALM, Redington Immunization, LDI Receiver Swap & Cash-Flow Matching LP",
        "archetype_manager.py": "Gestione profili patrimoniali istituzionali e archetipi didattici",
        "attribution.py": "Brinson-Fachler, Carino Multi-Period & Karnosky-Singer FX",
        "autonomous_rebalancer.py": "Autonomous Rebalancer con WACP/PMC reale & Recupero Minusvalenze",
        "backup_engine.py": "Zero-Downtime Hot Backup, WAL Checkpoint, PRAGMA Audit & Rollback",
        "barra_risk_model.py": "MSCI Barra GEM3/USE4 Structural Multi-Factor Risk Decomposition",
        "basel_liquidity_engine.py": "Basilea III LCR, NSFR & Dynamic Cash Flow Stress Ladder (BCBS 238)",
        "bitemporal_engine.py": "Motore di persistenza bitemporale (Valid Time vs Transaction Time) & Audit Hash SHA-256",
        "black_litterman_engine.py": "Bayesian Black-Litterman Portfolio Optimization & Idzorek Confidence",
        "bquant_engine.py": "ARGUS BQuant In-App Python Sandbox & DuckDB In-Memory SQL",
        "cache_shield.py": "Multi-Tier LRU & SQLite Rate-Limit Shield (yfinance)",
        "ccar_stress_engine.py": "Supervisory Fed CCAR / EBA 9-Quarter Capital Stress & CET1 Trajectory",
        "cds_tranche_engine.py": "ISDA Single-Name CDS Bootstrapping & Tranche Sintetiche iTraxx/CDX",
        "chart_framework.py": "ARGUS Institutional Plotly Design System & High-Performance Chart Framework",
        "climate_stress_engine.py": "NGFS Phase IV Climate Transition & Physical Risk Stress Engine",
        "closed_trades.py": "Graveyard, FIFO Closed Trades Journal & Tax Step-Up Analytics",
        "commodity_engine.py": "Gibson-Schwartz 2-Factor Commodity Futures, Convenience Yield & Kirk Spread",
        "confirm_dialogs.py": "Modali interattivi di conferma operazioni critiche e transazioni (@st.dialog)",
        "corporate_actions.py": "Corporate Actions, Stock Splits & Stock Dividends Engine",
        "credit_portfolio_engine.py": "CreditMetrics S&P 8-State Migration & Vasicek Multi-Obligor IRB",
        "cross_border_tax_engine.py": "Fisco cross-border, convenzioni contro le doppie imposizioni & W-8BEN",
        "crypto_provider.py": "Aggregatore multi-provider crypto (Binance, Kraken, CoinGecko)",
        "crypto_tax_engine.py": "Fisco Cripto-Attività, Quadri RT/RW/IVAFE & Zainetto Cripto",
        "data_quality_gate.py": "Pydantic v2 Ingestion Gate, Semantic Sanity & SHA-256 Deduplication",
        "database_migration_manager.py": "DBRE Migration Engine, Dual Versioning, Shadow Backup & Drift Inspector",
        "db_exporter.py": "Layer di storicizzazione snapshot su DB (MySQL & SQLite)",
        "dcc_garch_engine.py": "Engle Dynamic Conditional Correlation (DCC-GARCH) & Asymmetric GJR",
        "diagnostics.py": "System Diagnostics, Storage Cockpit & Lead SRE Observability",
        "dividend_engine.py": "Cash Flow Forecast & Dividend Calendar",
        "duckdb_engine.py": "Motore Analitico In-Process DuckDB (OLAP) & Parquet Storage",
        "esg_engine.py": "ESG Scoring, Carbon Intensity Scope 1-3 & SFDR Art. 8/9 Classification",
        "excel_connector.py": "Bloomberg Formula Generator, VBA Macro, Office Scripts & XLSX Exporter",
        "excel_generator.py": "Modello tattico Excel What-If",
        "execution_algo.py": "Algoritmi di esecuzione TWAP, VWAP, POV & Square-Root Market Impact",
        "execution_algo_engine.py": "Motore di simulazione avanzata esecuzione algoritmica & Almgren-Chriss",
        "executive_board_pack_engine.py": "1-Click CRO Executive Board-Pack & Actionable Playbook Synthesizer",
        "exporter.py": "Esportatore CSV denormalizzati",
        "factor_library.py": "Kenneth French Factor Library (5-Factor, MOM & Q1-Q5 Backtest)",
        "fetcher.py": "Download dati storici yfinance & conversione valute",
        "financial_analysis.py": "Altman Z-Score, DuPont, Piotroski, WACC, DCF Monte Carlo",
        "fix_engine.py": "Protocollo di negoziazione istituzionale FIX 4.4 (Execution & Routing Mock)",
        "fixed_income.py": "Fixed Income YTM, Duration, Convexity, DV01, Z-Spread, CDS, Nelson-Siegel KRD",
        "forensic_accounting.py": "Beneish M-Score (1999) & Sloan Accrual Ratio (1996)",
        "frtb_engine.py": "FRTB Basilea IV Standardized Approach (SBM, DRC & RRAO - BCBS 365)",
        "fx_overlay_engine.py": "Dynamic FX Hedging Overlay, Carry Trade & Forward FX Pricing",
        "garch_engine.py": "Volatilità condizionale GARCH(1,1), architettura di stima ML & forecasting",
        "hedging.py": "Copertura Beta-Neutral & Tail Risk Protection",
        "heston_fft_engine.py": "Heston Stochastic Volatility FFT Option Pricing & Surface Calibration",
        "hmm_regime_engine.py": "Hidden Markov Model (HMM) Adaptive Regime Switching & Viterbi Decoding",
        "hrp_optimizer.py": "Hierarchical Risk Parity (HRP - Marcos López de Prado)",
        "html_exporter.py": "Exporter Report Standalone HTML",
        "hull_white_engine.py": "Hull-White 1-Factor Short Rate & Bermudan Swaption Tree Pricing",
        "ingestion_utils.py": "Universal Bank Ingestion, Sniffer & Encoding Detection",
        "isda_simm_engine.py": "ISDA SIMM v2.6 Initial Margin & BCBS-IOSCO UMR €50M Rule Checker",
        "loading_states.py": "UI Lifecycle, Skeleton Loaders, Atomicity & Loading Transitions",
        "macro_provider.py": "Connettore dati macroeconomici FRED, BCE & Term Structure",
        "macro_stress_engine.py": "Stress testing macroeconomico congiunto (tassi, spread, inflazione, PIL)",
        "macro_war_room.py": "Interactive Macro War Room, Geopolitical Stress & Correlation Breakdown",
        "market_making_vpin_engine.py": "Avellaneda-Stoikov Market-Making & Hawkes VPIN Toxicity Engine",
        "metadata_resolver.py": "Risoluzione metadati e anagrafiche asset",
        "mip_rebalancer.py": "Mixed-Integer Programming (MIP/MILP) Cardinality & Lot-Sizing Rebalancer",
        "models.py": "Schema ORM SQLAlchemy (MySQL & SQLite)",
        "modular_factsheet_builder.py": "Institutional Factsheet Generator & Section Compositor",
        "morning_meeting_engine.py": "Morning Meeting Audio Briefing & Executive Daily Note Engine",
        "msci_barra_risk_engine.py": "MSCI Barra Structural Factor Risk & Euler Decomposition (GEM3)",
        "multi_portfolio.py": "Total Wealth Multi-Account Registry, Scorecard & Consolidator",
        "multicurve_engine.py": "Post-LIBOR Multi-Curve OIS Discounting (€STR/SOFR) & Dual Bootstrapping",
        "onboarding_guard.py": "Onboarding Wizard & Guardrail per primo avvio piattaforma",
        "optimal_liquidation_engine.py": "Optimal Liquidation con Square-Root Impact, POV VWAP & Almgren-Chriss",
        "options_hedging.py": "Black-Scholes 1973, 5 Greci, Delta-Hedging & Covered Call",
        "options_workbench.py": "Workbench opzioni interattivo, pay-off diagram & strategie complesse",
        "pdf_generator.py": "Exporter Factsheet PDF (ReportLab) con Numbered Canvas",
        "prescriptive_rebalancer.py": "Prescriptive Conic Rebalancer & FIX 4.4 Protocol Blotter",
        "priips_kid_generator.py": "PRIIPs KID Regulatory Engine (SRI 1-7, 4 Scenari di Performance, SFDR)",
        "private_debt_engine.py": "Private Debt, Mezzanine Financing, Cash Flow Waterfall & Covenants",
        "quarterly_report_generator.py": "Generatore di report trimestrali istituzionali white-label",
        "rebalancer.py": "Smart Rebalancer & Generatore Ordini",
        "regime_allocation.py": "Asset allocation tattica condizionata al regime di mercato",
        "regime_switching.py": "Market Regime Switching (3-State Markov Model)",
        "regulatory_reporting_engine.py": "Motore unificato per reporting regolamentare (PRIIPs, SFDR, MiFID II)",
        "reinforcement_learning.py": "Deep Q-Learning & Actor-Critic Portfolio Rebalancing Agent",
        "report_exporter.py": "Manager Centralizzato Esportazione Report",
        "reporting_design_system.py": "Obsidian Sovereign Design System & Numbered Canvas",
        "resilient_market_engine.py": "Enterprise SRE Circuit Breaker, Jittered Retry & Multi-Provider Engine",
        "risk_engine.py": "Motore FIFO, VaR/CVaR Euler, L-VaR Bangia, Almgren-Chriss, Kupiec",
        "risk_limits.py": "Early Warning System & Controlli di Rischio UCITS/MiFID",
        "rough_vol_svi_engine.py": "Rough Volatility (rBergomi H~0.10) & Gatheral SVI Arbitrage-Free Surface",
        "sabr_local_vol_engine.py": "Hagan SABR (2002) & Dupire Local Volatility Surface Calibration",
        "schemas.py": "Data Contracts & Validazione Pydantic v2",
        "screener_engine.py": "EQS Formula Engine, Screener Multi-Fattoriale & Pre-Trade Simulator",
        "sec_rag_engine.py": "Local RAG & Vector Store Semantico sui Bilanci SEC (10-K/10-Q)",
        "security_engine.py": "CWE-1236 Anti-Formula Injection, PII Masking & ArgusDataVault AES",
        "session_manager.py": "ArgusSessionManager: Type-Safe Session State Governance & Fallback",
        "sidebar.py": "Navigation Rail v9.19.0, Command Palette (Ctrl+K) & Spotlight Search",
        "smart_order_router.py": "MiFID II RTS 28 Smart Order Router & Execution Venues Slicing",
        "solvency2_engine.py": "Solvency II Standard Formula SCR & Market Risk Correlation Aggregation",
        "stochastic_kernel.py": "Simulatore stocastico Monte Carlo vettorizzato (Browniano, Jump, CIR)",
        "streaming_engine.py": "Real-Time Ring Buffer, VWAP, Order Flow Imbalance & Level-2 Book",
        "structured_products_engine.py": "Derivati esotici, Phoenix Autocallable Worst-Of & Reverse Convertible",
        "tax_aware_rebalancer.py": "Ribilanciamento tax-aware con compensazione plusvalenze e minusvalenze pregresse",
        "tax_engine.py": "Ottimizzazione Fiscale TUIR Art. 67 & Tax-Loss Harvesting Wizard",
        "technical_analysis.py": "Motore Analisi Tecnica, Volume Profile & Confluenza",
        "temporal_engine.py": "Motore di Analisi Temporale, Rolling Risk & Performance Matrix",
        "terminal_engine.py": "Live Terminal Desk, Pre-Trade Risk Checks, OMS Blotter & PnL Attribution",
        "trade_staging_blotter.py": "Blotter per staging ordini pre-trade con validazione limiti",
        "ui_export_utils.py": "Universal Export Toolbar isolata con @st.fragment per tabelle e report",
        "ui_lifecycle.py": "Gestione ciclo di vita UI, caching transitorio e teardown sicuro",
        "ui_utils.py": "Helper Grafici Plotly, Modali Informativi Istituzionali & Vector SVG Icons",
        "unified_demo_seeder.py": "Seeder universale dataset demo & scenari di prova realistici",
        "universal_ledger.py": "Universal One-Ledger Core, Star Schema & Vectorized PyArrow/DuckDB",
        "ux_institutional_hub.py": "Institutional Terminal UX/UI Hub, Bloomberg Command Bar & Top Bar",
        "ux_quant_canvas.py": "Visual Quant Canvas 3D & 2D Interactive Figures Engine",
        "validator.py": "Pipeline di Bonifica & Normalizzazione Dati",
        "voice_advisor_engine.py": "Executive Voice Briefing & Script a 2 Voci (CIO & CRO)",
        "volatility_surface.py": "Superficie di Volatilità Implicita 3D, Skew & Smile Calibration",
        "walk_forward_engine.py": "Walk-Forward Rolling Out-of-Sample Optimizer con attrito reale",
        "workspace_context.py": "Typed Multi-Session Context & Domain Flush Manager",
        "workspace_engine.py": "ARGUS Launchpad, 5 Ruoli Istituzionali & Layout Persistence",
        "workspace_manager.py": "State Manager, Routing Dinamico & URL State Sync",
        "xva_engine.py": "Bilateral XVA (CVA, DVA, FVA, MVA, KVA) & CSA Netting Exposure Simulation",
        "yield_curve.py": "Curva Tassi Privi di Rischio Live Dinamica Multi-Valuta & Nelson-Siegel",
    }

    core_files = sorted([f for f in os.listdir("core") if f.endswith(".py")])
    for f in core_files:
        desc = core_desc[f]
        pad = max(1, 30 - len(f))
        pad_str = " " * pad
        lines.append(f"│   ├── {f}{pad_str}# {desc}")

    # Data directory
    lines.append("├── data/                        # Dataset di input & database SQLite fallback")
    lines.append("│   ├── archetypes/              # Profili didattici patrimoniali (Giovane Accumulatore, Famiglia, HNWI)")
    lines.append("│   ├── multi_portfolios/        # Repository JSON profili multi-portafoglio registrati")
    lines.append("│   ├── Transactions.csv         # Dataset storico reale DeGiro WealthApp (400+ operazioni verificate)")
    lines.append("│   ├── portfolio_transactions_realistic.csv # Dataset realistico multi-asset multi-valuta (EUR, USD, GBP, CHF)")
    lines.append("│   ├── argus_local.db           # Database SQLite locale Data Warehouse e snapshot storici")
    lines.append("│   ├── argus_wealth.db          # Database SQLite locale Wealth Management Ecosystem")
    lines.append("│   ├── argus_workspaces.db      # Database SQLite per persistenza profili Launchpad & workspaces")
    lines.append("│   ├── bitemporal_ledger.duckdb # Database analitico colonnare DuckDB per One-Ledger bitemporale")
    lines.append("│   ├── yfinance_cache.db        # Database SQLite Cache Shield per rate-limiting e caching 24h")
    lines.append("│   └── .gitkeep")

    # Docker
    lines.append("├── docker/                      # File di containerizzazione Docker")
    lines.append("│   └── Dockerfile               # Multi-stage build hardening (non-root unprivileged user argus:argus)")

    # Docs
    lines.append("├── docs/                        # Documentazione Tecnica & Specifica Architetturale")
    lines.append("│   ├── compliance/")
    lines.append("│   │   └── whitepaper.md        # Whitepaper di conformità normativa (Basilea IV, MiFID II, TUIR, Solvency II)")
    lines.append("│   ├── getting-started/")
    lines.append("│   │   ├── installation.md      # Guida all'installazione locale, virtual environment e dipendenze")
    lines.append("│   │   └── quickstart.md        # Guida rapida di primo avvio e importazione del primo portafoglio")
    lines.append("│   ├── methodology/")
    lines.append("│   │   ├── bitemporal.md        # Fondamenti teorici del ledger bitemporale e tracciabilità rettifiche")
    lines.append("│   │   ├── execution.md         # Modelli di esecuzione ottima, Almgren-Chriss e market impact radice quadrata")
    lines.append("│   │   ├── hrp.md               # Metodologia Hierarchical Risk Parity (HRP) e clustering gerarchico dei pesi")
    lines.append("│   │   └── risk_engine.md       # Manuale metodologico del Quantitative Risk Engine e quadratura di Eulero")
    lines.append("│   ├── CSV_Format_Specification.md # Specifica tecnica formato CSV & DeGiro")
    lines.append("│   ├── DESIGN.md                # Design System Sovereign Obsidian & Specifiche UI/UX")
    lines.append("│   ├── EXECUTIVE_REPORT_OUTLINE.md # Struttura standard del dossier esecutivo trimestrale")
    lines.append("│   ├── FLOWCHART.md             # Diagramma di Flusso ETL a 5 Livelli")
    lines.append("│   ├── POWER_BI_GUIDE.md        # Guida all'integrazione del Data Warehouse Star Schema in Microsoft Power BI")
    lines.append("│   ├── PRESENTATION_SLIDES.md   # Presentazione esecutiva e slide deck del progetto")
    lines.append("│   ├── PROJECT_HANDOFF.md       # Documento di Consegna & Handoff Tecnico (v9.19.0)")
    lines.append("│   ├── architecture-map.html    # Mappa architetturale interattiva a nodi")
    lines.append("│   ├── argus-architecture.html  # Diagramma Architetturale HTML Standalone v9.19.0")
    lines.append("│   ├── argus-architecture.json  # Specifica Architetturale JSON IR v9.19.0")
    lines.append("│   ├── argus_banner.jpg         # Banner grafico istituzionale ARGUS")
    lines.append("│   ├── argus_icon.ico           # Asset icona Occhio di Argus")
    lines.append("│   ├── index.md                 # Home page documentazione MkDocs")
    lines.append("│   └── metriche_rischio.md      # Manuale Matematico ed Econometrico completo (101 Sezioni Istituzionali)")

    # Exports
    lines.append("├── exports/                     # Cartella di destinazione report esportati (.xlsx, .pdf, .zip)")
    lines.append("│   └── .gitkeep")

    # Google Sheets
    lines.append("├── gsheets_sync_subproject/     # Sub-servizio Sincronizzazione ETL Google Sheets")
    lines.append("│   ├── run_daily_scheduler.py   # Schedulatore cron giornaliero")
    lines.append("│   └── sync_google_sheets.py    # Pipeline ETL Google Sheets con iniezione dati")

    # Notebooks
    lines.append("├── notebooks/                   # Jupyter Notebooks di prototyping quantitativo")
    lines.append("│   └── test_pipeline.ipynb")

    # Scripts
    lines.append("├── scripts/                     # Script di Build, Schema SQL, Verifica e Pacchettizzazione")
    lines.append("│   ├── DB.sql                   # Schema DDL Data Warehouse MySQL 8.0 (Risk & Assets)")
    lines.append("│   ├── DB_wealth.sql            # Schema DDL Wealth Management MySQL 8.0")
    lines.append("│   ├── build_desktop_app.py     # Automazione compilazione PyInstaller (.exe standalone)")
    lines.append("│   ├── check_percent_math.py    # Validatore automatico scala percentuale (0-1 vs 0-100%) nelle formule")
    lines.append("│   ├── create_desktop_shortcut.py # Generatore collegamento Desktop con icona (.lnk)")
    lines.append("│   ├── export_star_schema.py    # Generatore pacchetto ZIP Star Schema per Power BI & Looker Studio")
    lines.append("│   ├── find_versions.py         # Script di audit e allineamento versione dell'ecosistema")
    lines.append("│   ├── fix_duplicate_portfolios.py # Utility per deduplicazione e bonifica profili multi-portafoglio")
    lines.append("│   ├── fix_duplicate_portfolios.sql # Script SQL di deduplicazione record portafoglio")
    lines.append("│   ├── freeze_historical_snapshots.py # Script per congelamento deterministico snapshot patrimoniali")
    lines.append("│   ├── generate_excel_model.py  # Generatore standalone modello Excel dinamico con formule RTD")
    lines.append("│   ├── generate_icon.py         # Generatore icona ICO multi-risoluzione")
    lines.append("│   ├── generate_readme_tree.py  # Generatore e validatore deterministico dell'albero repository README")
    lines.append("│   ├── generate_realistic_portfolio.py # Quantitative Simulation Engine (3 Archetipi, PAC, Mutui, Solvibilità)")
    lines.append("│   ├── inspect_readme.py        # Validatore di consistenza per la documentazione del repository")
    lines.append("│   ├── package_release.py       # Pacchettizzatore Release ZIP con hash crittografici")
    lines.append("│   ├── test_latex_syntax.py     # Test suite CI per validazione sintattica KaTeX/LaTeX su tutta la documentazione")
    lines.append("│   ├── test_run.py              # Script di esecuzione rapida smoke test")
    lines.append("│   └── verify_portfolio_test.py # Verifica deterministica di quadratura contabile sui portafogli di test")

    # Src
    lines.append("├── src/                         # Codice sorgente dell'applicazione Streamlit (22 Moduli Operativi)")
    lines.append("│   ├── 0_Control_Room.py        # Entry point principale, Total Wealth Hub & Control Room")
    lines.append("│   └── pages/                   # Moduli e viste della dashboard (1..21)")
    lines.append("│       ├── 1_📈_Dashboard_Generale.py # Executive Cockpit, Asset Allocation & Performance Summary")
    lines.append("│       ├── 2_🖥️_Live_Terminal.py     # Institutional Terminal Desk, Pre-Trade Risk Checks & OMS Blotter")
    lines.append("│       ├── 3_🔴_Analisi_Rischio.py   # Cornish-Fisher CVaR, Euler VaR, GARCH(1,1), L-VaR & Basilea IV")
    lines.append("│       ├── 4_🔬_Modelli_Quantitativi.py # Markowitz, HRP, Copula, Heston FFT, SABR 3D, Hull-White & CDS")
    lines.append("│       ├── 5_📋_Posizioni_e_Dettagli.py # Analisi Granulare Posizioni, PnL Storico & Movimenti")
    lines.append("│       ├── 6_🏛️_Valutazione_Aziendale.py # Altman Z-Score, Beneish M-Score, DCF & DuPont Analysis")
    lines.append("│       ├── 7_🌪️_Stress_Testing.py    # Macro Stress, EBA 2026, CCAR, FRTB SBM, NGFS Climate, ISDA SIMM & XVA")
    lines.append("│       ├── 8_📊_Analisi_Temporale.py  # Rolling Risk Metrics, Drawdown Matrix & Regime Switching")
    lines.append("│       ├── 9_📈_Analisi_Tecnica.py    # Volume Profile (POC/VAH/VAL), ATR Chandelier & Oscillatori")
    lines.append("│       ├── 10_🔍_Screener_Opportunita.py # Multi-Factor Screener, EQS Engine & Fundamental Filters")
    lines.append("│       ├── 11_💻_BQuant_e_Launchpad.py # In-App Python Sandbox, DuckDB SQL & Launchpad Workspace")
    lines.append("│       ├── 12_🎛️_Wealth_Control_Room.py # Wealth Management Cockpit & Data Quality Overview")
    lines.append("│       ├── 13_🏛️_Patrimonio_e_NetWorth.py # Net Worth Consolidato, ALM/LDI Cash-Flow Matching & Reverse Stress")
    lines.append("│       ├── 14_💳_Cash_Flow_e_Spese.py # Cash Flow Analysis, Budgeting 50/30/20 & Emergency Runway")
    lines.append("│       ├── 15_⌚_Asset_Illiquidi_e_Orologi.py # Passion Assets, Real Estate & Private Equity Valuation")
    lines.append("│       ├── 16_🛡️_Previdenza_e_Pension_Planning.py # Human Capital Actuarial Valuation, TBS-VaR & Pension Gap")
    lines.append("│       ├── 17_🔥_Indipendenza_Finanziaria_e_FIRE.py # FIRE Simulator, Guyton-Klinger Dynamic SWR & Monte Carlo")
    lines.append("│       ├── 18_📑_Fiscalita_e_Quadro_RW.py # Ottimizzazione Fiscale TUIR, Quadro RW/RT/IVAFE & Tax-Loss Harvesting")
    lines.append("│       ├── 19_🏡_Immobili_e_Mutui.py  # Mutui alla Francese, Sensibilità Tassi +200 bps & LTV Ratio")
    lines.append("│       ├── 20_⚖️_Pianificazione_Successoria.py # Asse Ereditario, Riunione Fittizia ex art. 556 c.c., Trust & Donazioni")
    lines.append("│       └── 21_🤖_AI_Copilot_e_Advisor.py # Conversational Wealth Copilot, Action Memo Istituzionale & Voice Briefing")

    # Tests
    lines.append("├── tests/                       # Test suite automatizzata PyTest (844 Test su 132 File)")
    test_files = sorted([f for f in os.listdir("tests") if f.endswith(".py")])
    for i, f in enumerate(test_files):
        prefix = "└──" if i == len(test_files) - 1 else "├──"
        lines.append(f"│   {prefix} {f}")

    # Root files
    lines.append("├── .env.example                 # Esempio configurazione variabili d'ambiente")
    lines.append("├── CHANGELOG.md                 # Registro cronologico dettagliato delle versioni (v1.0.0 -> v9.19.0)")
    lines.append("├── CODE_OF_CONDUCT.md           # Codice di Condotta per i contributori")
    lines.append("├── CONTRIBUTING.md              # Guida ai contributi e workflow pull request")
    lines.append("├── LICENSE.md                   # Licenza Open Source MIT")
    lines.append("├── README.md                    # Documentazione Principale del Progetto")
    lines.append("├── SECURITY.md                  # Politica di Sicurezza & Compliance")
    lines.append("├── app.py                       # Launcher alias per l'applicazione Streamlit")
    lines.append("├── argus_desktop.spec           # Spec PyInstaller per build standalone con isolamento percorsi")
    lines.append("├── desktop_launcher.py          # Entry point nativo Desktop App (PyWebView + Backup pre-flight)")
    lines.append("├── docker-compose.yml           # Configurazione Docker Compose (App + MySQL 8.0)")
    lines.append("├── mkdocs.yml                   # Configurazione documentazione MkDocs Material con supporto KaTeX")
    lines.append("├── pyproject.toml               # Configurazione tool di sviluppo, PyTest e linter Ruff")
    lines.append("├── pytest.ini                   # Configurazione test runner PyTest e filtri warning")
    lines.append("├── requirements.txt             # Dipendenze Python di produzione (pyarrow, pydantic v2, duckdb, ecc.)")
    lines.append("├── requirements-dev.txt         # Dipendenze per sviluppo, linting e testing (pytest, ruff, mkdocs)")
    lines.append("├── setup_desktop.bat            # Script di setup 1-Click per ambiente Desktop Windows")
    lines.append("├── start_dashboard.bat          # Script d'avvio rapido per Windows")
    lines.append("└── start_dashboard.sh           # Script d'avvio per Linux/macOS")
    lines.append("```")

    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    tree = build_tree()
    print("Tree built successfully. Lines:", len(tree.splitlines()))

    # Read current README.md
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    # Find where the tree starts and ends
    start_tag = "```text\nargus-risk-analytics/"
    end_tag = "└── start_dashboard.sh           # Script d'avvio per Linux/macOS\n```"
    
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)

    if start_idx == -1 or end_idx == -1:
        print(f"Error: could not find tree boundaries! start_idx={start_idx}, end_idx={end_idx}")
        sys.exit(1)

    end_idx += len(end_tag)

    new_content = content[:start_idx] + tree + content[end_idx:]

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Updated README.md successfully!")
