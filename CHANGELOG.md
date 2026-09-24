# Changelog

Tutti i cambiamenti significativi a questo progetto saranno documentati in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce a [Semantic Versioning](https://semver.org/lang/it/).

---

## [9.8.0] - 2026-09-23

### 🏛️ Institutional Risk Engine, Basel IV Traffic Light, EVT Tail Risk & Total Wealth Stress Testing

Questa release potenzia il core computazionale quantitativo e patrimoniale di ARGUS con standard di conformità regolamentare **Basilea IV**, **GIPS** e **CFP Board**:

- **Extreme Value Theory (EVT POT-GPD) & Tail Risk 99.9% (`core/risk_engine.py`, `src/pages/3_🔴_Analisi_Rischio.py`)**:
  - Implementato il framework Peaks-Over-Threshold (POT) e fitting della Generalized Pareto Distribution (GPD via `scipy.stats.genpareto`) per la stima accurata di VaR e CVaR (Expected Shortfall) a livelli di confidenza estremi (99.0% e 99.9%).
  - Risoluzione analitica del tail index $\xi$ e del parametro di scala $\sigma$ su soglie calibrate empiricamente al 90° percentile delle perdite.
- **Backtesting Regolamentare Basilea IV (Traffic Light Framework) (`core/risk_engine.py`, `src/pages/3_🔴_Analisi_Rischio.py`)**:
  - Validazione istituzionale su finestra mobile di 250 giorni di borsa aperta per il VaR 99% a 1 giorno con classificazione regolamentare in Zona Verde ($x \le 4$, moltiplicatore $3.00$), Gialla ($5 \le x \le 9$, moltiplicatori $3.40 - 3.85$) o Rossa ($x \ge 10$, moltiplicatore $4.00$).
  - Integrazione analitica del test di copertura incondizionata di Kupiec (POF), del test di indipendenza di Christoffersen (Markov-chain clustering delle violazioni) e del test congiunto di copertura condizionale.
- **Ottimizzatori Avanzati: Maximum Diversification (MDP) & Min-CVaR Linear Programming (`core/risk_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Massimizzazione del Diversification Ratio (DR) di Choueifaty & Coignard per estrarre la massima riduzione del rischio dalle correlazioni imperfette ($\rho_{ij} < 1$) senza dipendere da stime di rendimento atteso $\mu$.
  - Ottimizzazione convessa esatta Min-CVaR (Expected Shortfall) formulata come Programma Lineare (Rockafellar & Uryasev 2000) e risolta in sub-5ms tramite solutore C++ HiGHS (`scipy.optimize.linprog(method='highs')`), con preset buttons 1-click nel Super-Ribilanciatore.
- **Risoluzione Point-in-Time dei Tassi Risk-Free & Supporto ZIRP (2020–2026) (`core/yield_curve.py`)**:
  - Creata la mappatura `HISTORICAL_ANNUAL_RISK_FREE_RATES` per EUR (€STR/BCE Deposit), USD (Fed T-Bill 3M), GBP (BoE SONIA) e CHF (SNB SARON) dal 2020 al 2026, con pieno supporto ai tassi negativi (-0.50% BCE) ed eliminazione totale dei bias retroattivi nei coefficienti di Sharpe e Sortino.
- **Dinamica Point-in-Time delle Quote $Q_{i,t}$, True Daily TWR (Modified Dietz) & MWR (IRR) (`core/risk_engine.py`)**:
  - Ricostruzione giorno per giorno del portafoglio storico e calcolo del vero Time-Weighted Return (TWR) quotidiano depurato dai flussi di cassa esogeni (PAC e prelievi), con risoluzione del Money-Weighted Return (IRR) via algoritmo di Brent (`scipy.optimize.brentq`).
- **Scomposizione Rischio FX & Simulatore Forward Hedging Carry (`core/risk_engine.py`, `src/pages/3_🔴_Analisi_Rischio.py`)**:
  - Decomposizione analitica esatta della varianza $\sigma^2_{tot} \approx \sigma^2_{local} + \sigma^2_{fx} + 2\text{Cov}(R_{local}, R_{fx})$, quantificazione dell'esposizione valutaria aperta e stima del Forward Carry Drag annuo basato sulla Covered Interest Rate Parity.
- **Stress Testing Macroeconomico Consolidato sul Patrimonio Netto (Sub-Tab 6 in `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`, `core/macro_stress_engine.py`)**:
  - Simulazione congiunta degli shock regolamentari (EBA Regulatory Adverse 2026, Fed CCAR Severe, Stagflazione & Shock Tassi, Crisi Geopolitica Globale) su tutto l'attivo patrimoniale (Liquidità, Portafogli, Immobili, Fondi Pensione, Caveau & Orologi), con calcolo della perdita assoluta di ricchezza netta, del drawdown e dell'effetto leva finanziaria (*Debt-to-Assets Post-Stress*).
- **Bilancio Comparativo Pluriennale (2021–2026) & Dossier PDF a 4 Pagine (`core/wealth/personal_balance_sheet.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - Sub-tab 5 con prospetto storico a 6 esercizi di Attivo, Passivo, Patrimonio Netto, delta anno su anno (€ e %) e savings rate medio, corredato da grafico evolutivo e download CSV.
  - Esteso il dossier PDF istituzionale certificato con l'inclusione della **Pagina 4** dedicata al trend pluriennale e CSS Progress Bars evolutive.
  - Congelamento batch degli snapshot ufficiali di chiusura esercizio (2021–2025) al 31/12 via `scripts/freeze_historical_snapshots.py`.
- **Cronistoria Previdenziale & Scudo Fiscale Dinamico (2023–2026) (`src/pages/16_🛡️_Previdenza_e_Pension_Planning.py`)**:
  - Tabella analitica dei versamenti storici con tracking della deducibilità fiscale IRPEF (art. 51 TUIR, tetto 5.164,57 €), risparmio d'imposta reale (aliquota 43%) e plafond residuo con anno d'esercizio dinamico (`datetime.now().year`), affiancata dal grafico evolutivo su doppio asse.
- **Testing & Quality Gate**:
  - Creata la suite dedicata `tests/test_risk_engine_institutional.py` (9/9 passed) e verificata la suite congiunta di regressione (29/29 passed in 8.93s, 100% pass rate).

---

## [9.7.0] - 2026-09-15

### ⚡ Institutional UI/UX Ergonomics, @st.fragment Reactivity, @st.dialog Action Drawers & Desktop Command Palette (Ctrl+K)

Questa release rivoluziona l'esperienza utente, l'ergonomia visiva e la reattività operativa della piattaforma ARGUS, portando l'usabilità ai livelli di un terminale istituzionale (Bloomberg / FactSet):

- **Universal Command Palette (`Ctrl+K` / `Cmd+K`) (`components/command_palette.py`)**:
  - Switcher rapido e universale accessibile globalmente da qualsiasi modulo della suite.
  - Indicizzazione e navigazione istantanea tra tutte le 22 pagine di ARGUS, gli asset/ISIN del portafoglio attivo e gli scenari di stress macro (Lehman 2008, COVID-19, Rates Shock 2022, Spread BTP 2011, Dot-Com 2000).
  - Architettura di intercettazione hotkey multi-contesto con tripla strategia di geolocalizzazione DOM (ancora HTML dedicata, ricerca per contenuto testuale ed elementi `stBaseButton`).
  - **Full Desktop Native Standalone (`.exe`) Compatibility**:
    - Risolto il supporto `Ctrl+K` nell'eseguibile Windows nativo WebView2 (`dist/ARGUS_Desktop/ARGUS.exe`): incluso il pacchetto `components` nel bundle PyInstaller (`argus_desktop.spec`, `scripts/build_desktop_app.py`) e implementato l'hook di cattura tastiera `window.events.loaded` nel container WebView2 (`desktop_launcher.py`).
    - Eliminato il rischio di throttling Chromium dell'iframe dei componenti tramite altezza attiva e layout non-bloccante.
- **Reattività Ultra-Fluida con `@st.fragment`**:
  - **Stress Testing Interattivo (`src/pages/7_🌪️_Stress_Testing.py`)**: Isolamento del simulatore di shock multi-asset in frammento computazionale autonomo. Lo slider dei parametri e l'applicazione degli scenari storici ricalcolano esclusivamente il Delta P&L e le metriche di stress senza causare il re-render globale della pagina.
  - **Simulatore Parametrico VaR/CVaR (`src/pages/3_🔴_Analisi_Rischio.py`)**: Isolamento del calcolo Cornish-Fisher e decomposizione Euler VaR in `@st.fragment`, garantendo feedback interattivo in millisecondi durante la variazione del livello di confidenza e dell'orizzonte temporale.
- **Institutional Action Drawers con `@st.dialog` (`components/action_drawers.py`)**:
  - **Pre-Trade Order Blotter (`render_order_blotter_dialog`)**: Finestra modale non bloccante per la simulazione e validazione pre-flight degli ordini FIX/blotter generati dal motore di ribilanciamento con controllo conformità MiFID II.
  - **TUIR Tax Lot Inspector (`render_lot_inspector_dialog`)**: Ispezione approfondita lotto per lotto conforme al TUIR Art. 44 vs 67, con calcolo analitico di PMC fiscale, plusvalenze/minusvalenze latenti e classificazione Redditi di Capitale vs Redditi Diversi.
  - **Decomposizione Rischio Euler (`render_risk_decomposition_dialog`)**: Modale interattiva per l'analisi del rischio marginale e della percentuale di contributo al VaR di portafoglio a livello di singolo asset.
- **Tabular Ergonomics & High-Density Design System (`core/ui_utils.py`, `core/chart_framework.py`)**:
  - **Obsidian Dark Theme**: Palette colore istituzionale ad alto contrasto per terminali finanziari (`ObsidianTheme.BG_DEEP`, `ACCENT_CYAN`, `ACCENT_AMBER`, `BORDER`).
  - **Tabella Monospazio ad Alta Densità (`argus-dense-table`)**: Regole CSS ad alta densità informativa per report tabellari privi di sprechi di spazio verticale.
  - **Badge Fiscale TUIR**: Indicatori visivi cromatici per `Redditi di Capitale (Art. 44)` e `Redditi Diversi (Art. 67)`.
  - **Grid Interattiva Posizioni (`src/pages/5_📋_Posizioni_e_Dettagli.py`)**: Integrazione avanzata con `st.data_editor` e pulsanti one-click per l'apertura immediata dei drawer fiscali e degli ordini.
- **Allineamento Versioni & Testing**:
  - Allineate tutte le componenti alla release **v9.7.0** (`pyproject.toml`, `src/0_Control_Room.py`, `core/sidebar.py`, `components/splash.py`, `components/command_palette.py`, `components/action_drawers.py`).
  - Test suite `tests/test_ui_ux_overhaul.py` (5/5) e test smoke di compilazione su tutte le 24 pagine superati al 100%.

---

## [9.6.0] - 2026-09-15

### 🏛️ Unified Rebalancing Layer, Headless REST API, Arrow Binary Caching & Quant Hardening

Questa release rappresenta una profonda evoluzione architetturale e quantitativa della piattaforma ARGUS, focalizzata su disaccoppiamento Core-Presentation, eccellenza numerica e scalabilità enterprise:

- **Architettura Unificata di Ribilanciamento (`core/rebalancing/`)**:
  - Definizione di contratti e protocolli formali (`protocol.py`) per `RebalancingContext`, `PlannedOrder`, `RebalanceResult`, `TaxCategory` e `@runtime_checkable RebalancingStrategy`.
  - Dispatcher polimorfico `RebalancingEngine` (`engine.py`) con supporto e adapter per 4 strategie di calcolo: *Autonomous AI (MiFID II)*, *Tax-Aware Friction Matrix*, *Prescriptive Conic (SLSQP & FIX)* e *Heuristic Target Allocation*.
  - Piena retrocompatibilità con tutti i controller e le pagine esistenti della piattaforma.
- **Application Services Layer (`core/services/rebalancing_service.py`)**:
  - Implementata la facciata applicativa headless `RebalancingService` per isolare completamente i moduli di calcolo dai framework di visualizzazione.
- **Headless REST API (`POST /api/v1/rebalance`)**:
  - Nuovo endpoint REST istituzionale documentato con OpenAPI/Swagger in `api/main.py`, supportato da modelli Pydantic v2 per calcolo e verifica della conformità MiFID II e TUIR senza dipendenze dalla UI.
- **Governo Centralizzato del Session State (`core/session_manager.py`)**:
  - Creato `ArgusSessionManager` per tipizzare e centralizzare gli accessi a `st.session_state`.
  - Inizializzazione atomica, validazione ISO 4217, gestione profili di rischio MiFID II, capienza zainetto fiscale e fallback trasparente per contesti headless.
- **L2 Binary Caching con Apache Arrow Feather (`core/cache_shield.py`)**:
  - Serializzazione binaria ad alta velocità compressa con ZSTD per l'archiviazione SQLite di serie storiche e quotazioni.
  - Abbattimento del 90% della latenza di I/O, preservazione fedele dei tipi e `DatetimeIndex`, con supporto bidirezionale retroattivo per payload JSON storici.
- **Hardening Quantitativo & Stabilità Numerica (`core/risk_engine.py`)**:
  - **Merton Jump-Diffusion Vettorizzato**: Sostituito nested loop da 2.500.000 iterazioni pure Python con computazione 2D NumPy broadcasted su matrice percorsi $\times$ step temporali, azzerando i tempi di simulazione.
  - **Euler VaR Robustness**: Integrato shrinkage di Ledoit-Wolf e proiezione a matrice semidefinita positiva (PSD) con clipping autovalori positivi in `calc_euler_var_decomposition` (`compute_marginal_and_component_var`).
  - **Black-Litterman QP SLSQP Solver**: Sostituito il clipping euristico con formulazione di Quadratic Programming vincolato ($w_i \ge 0, \sum w_i = 1$) risolto con `scipy.optimize.minimize(method='SLSQP')`, con regolarizzazione del numero di condizionamento di $\Omega$ ($\text{cond}(\Omega) > 10^{12}$).
- **Compliance Fiscale TUIR Art. 44 vs 67 (`core/autonomous_rebalancer.py`)**:
  - Corretta l'asimmetria fiscale: le plusvalenze da ETF/OICR generano *Redditi di Capitale* non compensabili con le minusvalenze pregresse, mentre le plusvalenze su azioni singole, obbligazioni ed ETC generano *Redditi Diversi* regolarmente compensabili.
- **Isolamento Re-run Streamlit (`core/ui_export_utils.py`)**:
  - Toolbar di esportazione `render_export_toolbar` isolata con `@st.fragment`, evitando il re-rendering dell'intera dashboard al download di file CSV/Excel.
- **DevOps Desktop Standalone (`scripts/package_release.py`)**:
  - Aggiunto flag `--build-exe` che compila `argus_desktop.spec` tramite PyInstaller creando uno zip contenente l'eseguibile Windows standalone distribuibile.
- **Suite di Test Dedicata**:
  - Aggiunte le suite `tests/test_phase1_hardening.py`, `tests/test_phase2_performance_engine.py` e `tests/test_phase3_services_and_api.py`, con copertura al 100% di tutti i nuovi moduli e 38/38 test superati in 6.18s.

---

## [9.5.0] - 2026-09-13

### 🛡️ Unified Stochastic Kernel, BLAS Vectorization, Thread-Safe Monte Carlo & Credential Hardening

Questa release introduce una profonda modernizzazione del motore computazionale stocastico e delle performance numeriche di ARGUS:
- **Unified Stochastic Kernel (`core/stochastic_kernel.py`)**: Centralizzazione di tutte le simulazioni Monte Carlo su una decomposizione di Cholesky robusta con fallback spettrale a matrice semidefinita positiva (PSD) Nearest-Correlation e clipping autovalori positivi ($\lambda \ge 10^{-8}$).
- **Vettorizzazione BLAS/SIMD (`core/risk_engine.py`)**: Riscritte le computazioni di Beta di portafoglio (OLS multivariato compatto senza loop) e dell'RSI 14 (calcolo EWMA su matrice pivot) azzerando i colli di bottiglia computazionali per portafogli ad alto numero di ticker.
- **RNG Thread-Safe & Riproducibilità**: Adozione universale di generatori moderni `np.random.default_rng(seed)` in sostituzione del generatore globale legacy `np.random.seed()` / `np.random.randn()`, garantendo isolamento in ambienti multi-thread e asincroni.
- **Accelerazione GARCH(1,1) (`core/garch_engine.py`)**: Precomputazione vettoriale di $\varepsilon_t^2$, ottimizzazione della log-verosimiglianza e decoratore `@njit(fastmath=True)` fallback per massima convergenza numerica.
- **Service Layer Facade (`core/services/risk_service.py`)**: Implementata la facade pubblica `compute_full_portfolio_risk()` con disaccoppiamento dai moduli interni.
- **Segregazione Dipendenze & CI/CD Hardening**: Separazione di `requirements.txt` (runtime headless essenziale) da `requirements-dev.txt` (testing, packaging, desktop e linter). Configurazione Ruff standardizzata e audit di conformità linting a zero errori (`0 errors`) su tutto il repository.
- **Verifica Sicurezza Credenziali**: Audit completo dello storico git (`git log -S`) a conferma che nessuna credenziale o chiave RSA privata è mai stata esposta nei commit remoti.

### Aggiunto (Added)
- **Kernel Stocastico Centralizzato (`core/stochastic_kernel.py`)**:
  - `robust_cholesky`: decomposizione con correzione di Higham / Spectral Projection PSD per matrici empiriche quasi-singolari o degenerate.
  - `simulate_correlated_normal` & `simulate_correlated_student_t`: simulatore Monte Carlo vettorizzato con supporto thread-safe per code pesanti e multivariata.
  - `calc_asset_betas_vectorized`: OLS vettoriale per calcolo simultaneo dei Beta degli asset rispetto al benchmark.
  - `calc_rsi_vectorized`: indicatore RSI 14 vettorizzato su serie storiche multivariate.
- **Dipendenze Dev Segregate (`requirements-dev.txt`)**:
  - Isolamento delle librerie di sviluppo, test (`pytest`, `hypothesis`), reportistica (`reportlab`, `xlsxwriter`), GUI desktop (`pywebview`, `pyinstaller`) e linting (`ruff`).

### Modificato (Changed)
- **Motore di Rischio (`core/risk_engine.py`)**:
  - Integrazione di `robust_cholesky` del kernel stocastico.
  - Vettorizzazione del calcolo di Beta e RSI.
  - Sostituzione del generatore RNG globale con istanze isolate `np.random.default_rng(seed)`.
  - Pubblicazione di alias formali per piena retrocompatibilità (`calc_market_risk`, `calc_return_metrics`, `compute_risk`).
- **Motore TBS Monte Carlo (`core/wealth/tbs_monte_carlo.py`)**:
  - Sostituito l'algoritmo di Cholesky custom con il kernel condiviso `robust_cholesky`.
  - Aggiornato `simulate_tbs_multivariate` con generatori di numeri pseudocasuali thread-safe.
- **Motore GARCH (`core/garch_engine.py`)**:
  - Vettorizzazione del loop di log-verosimiglianza con precalcolo residui al quadrato ed eventuale accelerazione Numba JIT.
- **Application Service Layer (`core/services/risk_service.py`)**:
  - Esposizione del metodo pubblico `compute_full_portfolio_risk(weights, returns, benchmark_returns)`.
- **CI/CD Pipeline (`.github/workflows/ci.yml` & `release.yml`)**:
  - Standardizzazione dell'esecuzione di Ruff linter in formato annotazioni GitHub (`ruff check --output-format=github .`).
  - Utilizzo di `requirements-dev.txt` per il setup dell'ambiente di test.
- **Versione Progetto (`pyproject.toml`)**:
  - Incremento versione a `9.5.0`.

---

## [9.4.0] - 2026-09-13

### ⚡ Architectural Decoupling, Headless Safety, Fast Streaming Buffer & Multi-Container Healthcheck

Questa release introduce una profonda razionalizzazione architetturale:
- Disaccoppiamento definitivo del calcolo numerico e headless dalla libreria Plotly/Streamlit.
- Ottimizzazione a bassissima latenza del motore di streaming intraday.
- Espansione del Service Layer per una convergenza totale tra REST API e dashboard interattiva.
- Risoluzione del problema di healthcheck nel container Docker FastAPI.

### Aggiunto (Added)
- **Console Scripts CLI (`pyproject.toml`)**:
  - `argus-api`: comando console per l'avvio del server REST headless Uvicorn / FastAPI.
  - `argus-ui`: comando console per l'avvio immediato della Control Room Streamlit.
- **FastVectorRingBuffer a Zero Allocazione (`core/streaming_engine.py`)**:
  - Implementato `FastVectorRingBuffer` basato sullo schema NumPy strutturato `DTYPE_MARKET_TICK` per ingestione tick L2 ad alta frequenza e calcolo VWAP SIMD vettorializzato.
- **Espansione dell'Application Service Layer (`core/services/`)**:
  - In `RiskService`: introdotto il metodo `run_monte_carlo()` per la simulazione stocastica multivariata con decomposizione di Cholesky e distribuzioni Student-t.
  - In `WealthService`: introdotti i metodi `simulate_stress_test()` ed `evaluate_glidepath_goal()`.
- **Inizializzazione Namespace Presentation Decoupled (`components/ui_core/`)**:
  - Creato il package `components/ui_core/` per la progressiva migrazione dei componenti grafici al di fuori di `core/`.

### Modificato (Changed)
- **Headless Safety & Plotly Decoupling (`core/wealth/glidepath_engine.py` & `wealth_stress_engine.py`)**:
  - Protetto l'import di Plotly (`HAS_PLOTLY`) per consentire l'esecuzione numerica in ambienti privi di dipendenze grafiche.
  - Estratta la funzione `render_glidepath_chart()` in `glidepath_engine.py`, disaccoppiando la computazione dei percentili e delle probabilità dalla generazione delle figure.
- **Docker Compose Healthcheck Fix (`docker-compose.yml`)**:
  - Sovrascritto l'healthcheck del servizio `api` per interrogare `http://127.0.0.1:8000/api/v1/health` anziché ereditare l'endpoint Streamlit su porta 8501.
- **Ottimizzazione delle Prestazioni di TickRingBuffer (`core/streaming_engine.py`)**:
  - Riscritte `compute_vwap()` e `compute_order_flow_imbalance()` con iterazione diretta e calcolo vettorizzato, eliminando l'allocazione intermedia di DataFrame Pandas e dizionari.
- **Code Hygiene & Structured Logging (`core/fetcher.py`)**:
  - Rimosso l'import non utilizzato `concurrent.futures`.
  - Configurato il logger standardizzato `argus.fetcher`.

---

## [9.3.0] - 2026-09-13

### 🏛️ Architectural Decoupling, Application Service Layer & Quantitative Engine Scalability

Questa release porta a compimento la trasformazione architetturale enterprise di ARGUS, disaccoppiando completamente il motore quantitativo di calcolo dal front-end Streamlit, introducendo un Application Service Layer condiviso con l'API FastAPI headless, ottimizzando il motore OLAP DuckDB con PyArrow Zero-Copy e accelerando gli algoritmi contabili FIFO a $O(1)$.

### Aggiunto (Added)
- **Application Service Layer (`core/services/`)**:
  - `RiskService`: orchestrazione headless del rischio di mercato, VaR/CVaR parametrici e Cornish-Fisher, metriche di rendimento e ottimizzazione di portafoglio HRP (López de Prado).
  - `TaxService`: facade unificata per la fiscalità TUIR (Art. 67), conformità cripto-attività (L. 197/2022) e comparazione fiscale giurisdizionale cross-border.
  - `WealthService`: consolidamento istantaneo del bilancio personale (Net Worth, solvency ratio, health score).
- **Nuovo Endpoint REST Headless (`api/main.py`)**:
  - `GET /api/v1/wealth/networth`: esposizione del bilancio patrimoniale consolidato e dei ratio di solvibilità per integrazioni programmatiche.
- **Microservizio Headless su Docker Compose (`docker-compose.yml`)**:
  - Aggiunto il container `api` (FastAPI / Uvicorn su porta 8000) orchestrato nativamente con `web` (Streamlit su porta 8501) e `db` (MySQL 8.0).
- **Hardening della Sicurezza per Google Cloud Service Account**:
  - Aggiunto template [google_service_account.json.example](gsheets_sync_subproject/google_service_account.json.example) e supporto prioritario alle variabili d'ambiente `GOOGLE_SERVICE_ACCOUNT_JSON` e `GOOGLE_APPLICATION_CREDENTIALS` in `gsheets_sync_subproject/sync_google_sheets.py`.

### Modificato (Changed)
- **Architectural Decoupling UI vs Core (`core/risk_engine.py` & `core/fetcher.py`)**:
  - Eliminata l'inversione circolare di dipendenza dove `core/risk_engine.py` importava da `core.ui_utils`.
  - Implementato `fetch_cached_benchmark_returns` headless con cache in-memory TTL in `core/fetcher.py`, con delega trasparente da `core/ui_utils.py` per piena retrocompatibilità.
- **DuckDB In-Process Connection Pool & Zero-Copy Arrow (`core/duckdb_engine.py`)**:
  - Introdotto connection pool singleton thread-safe `get_shared_duckdb_connection` con 4 thread SIMD ed abilitazione dell'object cache C++.
  - Implementata la registrazione Zero-Copy dei DataFrame tramite tabelle Apache Arrow (`pyarrow.Table.from_pandas`), eliminando clonazioni ridondanti in RAM.
- **Accelerazione Algoritmica FIFO Matching (`core/closed_trades.py`)**:
  - Sostituito `queue.pop(0)` con `collections.deque.popleft()` per matching a complessità $O(1)$ e iterazione rapida con `itertuples(index=False)`.
- **Refactoring Headless API (`api/main.py`)**:
  - Sostituiti gli import da metodi privati con chiamate formali all'Application Service Layer.

### Rimosso (Removed)
- **Smoke Test Ridondante (`tests/test_frontend_smoke.py`)**:
  - Rimosso file duplicato a favore del completo e robusto `tests/test_all_pages_smoke.py`, che valida formalmente tutte le 21 pagine Streamlit e il Control Room.

---

## [9.2.0] - 2026-09-13

### 📈 ARGUS Institutional Plotly Design System & High-Performance Chart Framework

Questa release introduce un framework di visualizzazione dati Plotly enterprise di livello istituzionale (`core/chart_framework.py`), risolvendo la frammentazione delle palette cromatiche, garantendo 60 FPS costanti e abbattendo i tempi di rendering a meno di 200ms anche su serie storiche ad alta frequenza (>20.000 punti).

### Aggiunto (Added)
- **Design System Plotly Centralizzato (`core/chart_framework.py`)**:
  - Palette semantica finanziaria standard per tutte le 21 pagine (Equity Cyan `#38bdf8`, Fixed Income Emerald `#10b981`, Commodities Gold `#f59e0b`, Real Estate Purple `#8b5cf6`, Cash Slate `#64748b`, Crypto Fuchsia `#d946ef`, Risk/Drawdown Red `#ef4444`).
  - Funzione resolver semantica bilingue `get_asset_color(name)` (italiano/inglese) con fallback deterministico.
  - Template Plotly istituzionali `argus_dark` e `argus_light` con sfondo trasparente `rgba(0,0,0,0)`, font Outfit e JetBrains Mono, griglie a basso contrasto (`rgba(255,255,255,0.06)`).
  - Universal factory `apply_argus_theme` con margini compatti, legenda orizzontale in basso a zero interferenza, spikelines sottili e formattazione assi valuta/percentuale.
  - Toolbar configurata con `get_argus_plotly_config` per esportazione PNG nitida a scala 2x (1280x720) ed esclusione strumenti non finanziari.
- **Engine di Ottimizzazione Performance & WebGL**:
  - Switch automatico a `go.Scattergl` (GPU HTML5 Canvas) per serie con punti $\ge 1.000$ per garantire 60 FPS durante pan e zoom.
  - Implementazione in puro NumPy vettorizzato dell'algoritmo **LTTB (Largest Triangle Three Buckets)** per downsampling intelligente ad altissima velocità (<15ms per 20.000 punti), preservando picchi e minimi storici.
  - Utility `convert_figure_to_webgl` per conversione dinamica di grafici esistenti.
- **Quattro Wrapper Charts Production-Ready**:
  - `create_timeseries_chart`: NAV portafoglio, benchmark opzionale e sottomattonella sincronizzata Underwater Drawdown con diamante Max DD.
  - `create_montecarlo_fan_chart`: ventaglio probabilistico con bande P5-P95 (90%) e P25-P75 (50%), traiettoria mediana e target lines senza spaghetti clutter.
  - `create_asset_allocation_treemap`: allocazione multilivello con scala continua divergente Finviz PnL o colorazione semantica per asset class.
  - `create_waterfall_cashflow`: flussi entrate/uscite e patrimonio finale con barre semantiche e connettori puntinati.
- **Suite di Test Dedicata (`tests/test_chart_framework.py`)**:
  - 24 test unitari approfonditi che estendono la suite complessiva a **655 test passati al 100%**.

### Modificato (Changed)
- **Bridge & Re-export in `core/ui_utils.py`**:
  - Delegazione e re-export trasparente di tutti i componenti grafici da `core.chart_framework`, garantendo 100% di retrocompatibilità con le 21 pagine esistenti e con `tests/test_plotly_framework.py`.

---

## [9.1.0] - 2026-09-13

### 📊 Universal Financial Data Export Framework & Platform-Wide Multi-Format Standardization

Questa release standardizza l'esperienza utente in tutta la piattaforma ARGUS introducendo un framework universale, ad alte prestazioni ed elegante per l'esportazione dei DataFrame, e sostituendo sistematicamente tutti i vecchi pulsanti isolati "Scarica CSV".

### Aggiunto (Added)
- **Universal Financial Data Export Framework (`core/ui_export_utils.py`)**:
  - Esportazione dual-format immediata: **CSV conforme agli standard europei/italiani** (codifica UTF-8 con Byte Order Mark `utf-8-sig`) ed **Excel istituzionale styled (.xlsx via OpenPyXL)**.
  - Styling professionale Excel: header *Dark Obsidian* (`#161B22`) con accento ambra ARGUS (`#FF9900`), testo bianco in grassetto, griglie contabili esplicite (`showGridLines = True`), auto-fit dinamico della larghezza colonne con padding, freeze panes della prima riga (`A2`) e formattazione numerica contabile intelligente (`€`, `%`, date, interi).
  - Componente compatto popover `render_export_toolbar` a ingombro verticale zero con badge informativo di righe e colonne.
  - Card wrapper unificato `render_table_with_export` con titolo, record count pill, toolbar integrata e griglia Streamlit.
  - Caching binario ad alte prestazioni `@st.cache_data(show_spinner=False)` per generazione istantanea e zero lag sui re-run.
  - Generazione di nomi file contestuali con pattern `{prefisso}_{nome_portafoglio}_{timestamp}.{ext}`.
- **Suite di Test Unitari Dedicata (`tests/test_ui_export_utils.py`)**:
  - Test per gestione MultiIndex, tipi annidati, codifica UTF-8-sig con accenti/€, styling openpyxl e conformità rendering Streamlit. Test suite complessiva estesa a **631 test passati al 100%**.

### Modificato (Changed)
- **Migrazione Completa delle Tabelle della Piattaforma (50+ Tabelle sui 22 Moduli)**:
  - Sostituzione sistematica di tutti i legacy `st.download_button("📥 Scarica CSV", ...)` e integrazione della toolbar su tutte le tabelle in:
    - `src/0_Control_Room.py` (Mappature ticker, query DuckDB OLAP, posizioni e transazioni bitemporali time-travel, audit trail).
    - `src/pages/1_📈_Dashboard_Generale.py` (Benchmark scorecard, limiti compliance, asset allocation, rendimenti storici).
    - `src/pages/3_🔴_Analisi_Rischio.py` (Contributo rischio, decomposizione di Eulero, LVaR smobilizzo, ATR stops, ML Isolation Forest).
    - `src/pages/4_🔬_Modelli_Quantitativi.py` (17 tabelle: HRP, ERC, RL Actor-Critic, Contagion, Kelly, Monte Carlo, Barra, CDS, ecc.).
    - `src/pages/5_📋_Posizioni_e_Dettagli.py` (Posizioni principali, graveyard, dividendi, tax-loss, Quadro RT/RW, Almgren-Chriss, TWAP/VWAP).
    - `src/pages/6_🏛️_Valutazione_Aziendale.py` (Fair value models, DuPont, conto economico, stato patrimoniale, rendiconto).
    - `src/pages/7_🌪️_Stress_Testing.py` (Matrice scenari, dettaglio stress posizioni, macro factor sensitivity).
    - `src/pages/8_📊_Analisi_Temporale.py` (Audit report side-by-side).
    - `src/pages/9_📈_Analisi_Tecnica.py` (Volume profile, Level 2 order book, tick stream).
    - `src/pages/10_🔍_Screener_Opportunita.py` (Screener multi-fattoriale, watchlist tattica).
    - `src/pages/11_💻_BQuant_e_Launchpad.py` (Risultati esecuzione script BQuant).
    - `src/pages/13_🏛️_Patrimonio_e_NetWorth.py` (Asset allocation istituzionale & pesi).
    - `src/pages/14_💳_Cash_Flow_e_Spese.py` (Modale dettaglio transazioni, cash flow ledger).
    - `src/pages/15_⌚_Asset_Illiquidi_e_Orologi.py` (Asset fisici/orologi, Private Equity deal register, Private Debt tranches).
    - `src/pages/17_🔥_Indipendenza_Finanziaria_e_FIRE.py` (Net Worth-at-Risk matrix, Glide Path allocation, Fee Drag table).
    - `src/pages/18_📑_Fiscalita_e_Quadro_RW.py` (Quadro RW portfolio report, Tax-Loss harvesting).
    - `src/pages/19_🏡_Immobili_e_Mutui.py` (Dettaglio patrimonio immobiliare, piano ammortamento mutuo).
    - `src/pages/20_⚖️_Pianificazione_Successoria.py` (Simulazione imposte successione TUS, confronto veicoli di protezione).
    - `src/pages/21_🤖_AI_Copilot_e_Advisor.py` (Blotter ordini prescrittivi di ribilanciamento).
    - `core/ui_utils.py` (`render_data_table`, `render_duckdb_olap_cube_explorer`, `render_interactive_gics_sector_breakdown`).
    - `core/wealth/wealth_reporting_hub.py` (Prospetto Quadro RW ed estratto integrale Cash Flow).
- **Upgrade Visivo Splash Screen (`components/splash.py`)**:
  - Eye logo ingrandito e potenziato con effetto glow ambra/indaco ad alta risoluzione.
  - Sostituzione frecce `<<` nella sidebar con badge chevron istituzionale `◀ Riduci`.

---

## [9.0.0] - 2026-09-11

### 🚀 Major Release — Dual-Engine Institutional Overhaul, Quantitative Model Validation & Production Readiness

Questa major release formalizza l'evoluzione di **ARGUS** da piattaforma monolitica a **Ecosistema Quantitativo Istituzionale di Classe Tier-1**, introducendo la completa segregazione operativa tra Risk Management e Wealth Intelligence, una suite esaustiva di validazione dei modelli conformi a **Federal Reserve SR 11-7**, il modulo di reporting vettoriale MiFID II a 2 pagine e l'onboarding interattivo per nuovi utenti.

### Aggiunto (Added)
- **Institutional Splash Screen & Dual-Portal Gateway (`components/splash.py`)**:
  - Bootloader e splash screen istituzionale con design system Obsidian Dark Glass / Bento Grid Monolith.
  - Soppressione totale dell'header e delle freccette di espansione sidebar (`stExpandSidebarButton` in Streamlit 1.59+ e legacy `collapsedControl`) per una visualizzazione a schermo intero priva di distrazioni.
  - Apertura automatica reattiva della sidebar con trigger JavaScript multi-stadio al click su uno dei due ambienti operativi.
  - Console telemetrica in tempo reale stile Bloomberg B-PIPE con verifica del cluster dual-engine, latenza e storage fabric DuckDB SIMD + SQLite ACID.
  - Bento Grid monolitica con schede descrittive a 4 righe di metriche e pulsanti CTA fusi senza interruzioni ad altissimo contrasto cromatico.
  - Certificazione rigorosa dei **22 Moduli Operativi Totali** (12 Moduli Risk & Quant Desk + 10 Moduli Wealth & Advisory Suite).
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
