# Design System: ARGUS Risk Analytics Platform
**Project ID:** argus-risk-analytics

## 1. Visual Theme & Atmosphere
The **ARGUS Risk Analytics Platform** embodies an institutional, high-density financial terminal aesthetic inspired by modern quantitative trading platforms and risk engines. Designed for quantitative financial analysis, corporate valuation, and portfolio risk engineering, the atmosphere is sophisticated, futuristic, and utilitarian. 

Key visual principles:
* **Deep Dark Mode Core:** A dark background (`#0d1117` to `#161b22`) reduces cognitive fatigue during prolonged analysis sessions while highlighting critical numerical variations.
* **Glassmorphism & Layered Depth:** Translucent container surfaces (`rgba(22, 27, 34, 0.6)`) paired with real-time backdrop blurring (`blur(14px)`) create a multi-dimensional spatial hierarchy.
* **Luminous Data Accents:** High-contrast accent glows (e.g., Bloomberg Amber `#ff9900`, Cyberpunk Cyan `#00f3ff`, Emerald Green `#00c853`) highlight primary metrics, interactive hover targets, and structural section headers.
* **Tactile Micro-Interactions:** Subtle vertical elevations (`translateY(-4px)`), smooth scaling (`scale(1.01)`), and ambient shadow halos communicate responsiveness across all data cards.

## 2. Color Palette & Roles

### Primary Brand & Accent Colors
* **Bloomberg Amber Accent (`#ff9900`):** Used as the signature brand color, glowing metric indicators, section divider accents, interactive hover highlights, and active tab borders.
* **Cyberpunk Neon Cyan (`#00f3ff`):** Theme alternative accent color for high-tech data visualization modes, risk matrix overlays, and intense callouts.
* **Emerald Wealth Green (`#00c853`):** Theme alternative accent color tailored for private wealth management modes and positive PnL indicators.

### Structural Base & Background Colors
* **Obsidian Radial Surface (`#0d1117` to `#161b22`):** Base canvas background, rendered as a smooth radial gradient (`radial-gradient(circle at 15% 50%, #0d1117, #161b22, #0d1117)`).
* **Translucent Obsidian Card Fill (`rgba(22, 27, 34, 0.6)`):** Used for metric card containers, floating widget boxes, and analytical modules.
* **Frosted Sidebar Surface (`rgba(13, 17, 23, 0.7)`):** Backdrop-blurred side navigation panel with high-contrast edge demarcation.
* **Modal Deep Obsidian (`#161b22`):** Solid dark surface for popup drill-down windows, glossaries, and detail overlays.

### Typography & Neutral Tones
* **High-Visibility Pure White (`#ffffff`):** Reserved for primary page titles, section headers, and active modal text.
* **Soft Silver Gradient (`#ffffff` to `#c9d1d9`):** Linear text gradient used for high-impact 32px metric values.
* **Slate Gray Subtext (`#8b949e`):** Used for uppercase metric labels, secondary captions, and inactive control elements.
* **Subtle Edge Border (`rgba(255, 255, 255, 0.08)`):** Ultra-thin 1px crisp borders separating containers and grid cells.

### Executive Risk & Health Status Tokens
* **Executive Health Green (`#3fb950` / `rgba(63, 185, 80, 0.15)`):** Used for positive PnL returns, low portfolio drawdown, safe Z-Score, and high Piotroski score.
* **Executive Caution Gold (`#d29922` / `rgba(210, 153, 34, 0.15)`):** Used for moderate volatility, grey Z-Score zone, balanced risk profiles, and warning indicators.
* **Executive Danger Red (`#f85149` / `rgba(248, 81, 73, 0.15)`):** Used for negative PnL, high Value at Risk (VaR), distress Z-Score, aggressive drawdown alerts, and red status badges.

## 3. Typography Rules
* **Primary Font Family:** `Outfit`, sans-serif (imported via Google Fonts). Modern geometric sans-serif providing exceptional clarity for numbers, data tables, and dense dashboards.
* **Metric Values (KPIs):** Size `32px`, font-weight `700` (Bold), letter-spacing `-0.5px`, filled with a subtle metallic linear gradient (`#ffffff` to `#c9d1d9`).
* **Section Headers:** Size `22px`, font-weight `600` (Semi-Bold), pure white (`#ffffff`). Supported by an amber underline accent (`2px` height, `60px` width) with an ambient light glow.
* **Metric Labels:** Size `13px`, font-weight `500` (Medium), uppercase text with `0.8px` letter-spacing, Slate Gray (`#8b949e`).
* **Executive Badges:** Size `13px`, font-weight `600` (Semi-Bold), inline-flex alignment.
* **Modal Body & Tooltips:** Size `14px` - `15px`, line-height `1.6`, font-weight `400` (Regular) / `500` (Medium) for maximum readability.

## 4. Component Stylings

* **Buttons & Action Control Bars:**
  * **Shape:** Pill-shaped or softly rounded corners (`border-radius: 8px` for action buttons, `border-radius: 20px` for pills/badges).
  * **Styling:** Semi-transparent tinted background (`rgba(255, 153, 0, 0.1)`), thin accent border (`1px solid rgba(255, 153, 0, 0.4)`), amber text color (`#ff9900`).
  * **Behavior:** Smooth scaling and upward translation (`translateY(-1px)`) on hover with increased background opacity (`rgba(255, 153, 0, 0.2)`).

* **Cards / Containers (Metric Cards & Data Modules):**
  * **Shape:** Generously rounded corners (`border-radius: 14px`).
  * **Styling:** Translucent obsidian background (`rgba(22, 27, 34, 0.6)`), real-time glassmorphism (`backdrop-filter: blur(14px)`), subtle inset top border highlight (`inset 0 1px 0 rgba(255, 255, 255, 0.05)`).
  * **Accent Indicator:** A vertical `4px` glowing gradient strip on the left edge (`linear-gradient(180deg, #ff9900, #ff3366)`).
  * **Behavior:** Lifts on hover (`transform: translateY(-4px) scale(1.01)`), turns border to vibrant accent color, and projects a diffused outer glow (`box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3), 0 0 20px rgba(0, 243, 255, 0.15)`).

* **Inputs & Interactive Controls:**
  * **Styling:** Dark translucent inputs with crisp 1px borders (`rgba(255, 255, 255, 0.1)`), changing to amber highlight on focus.
  * **Typography:** `Outfit` sans-serif, size `14px`.

* **Executive Health Badges:**
  * **Shape:** Pill-shaped (`border-radius: 20px`), compact inline padding (`6px 14px`).
  * **Styling:** 15% translucent colored background with matching 30% border color and high-visibility text color (Green, Gold, Red).

* **Modal Windows & Educational Metric Overlays (`core/ui_utils.py`):**
  * **Shape:** Rounded rectangle (`border-radius: 16px`).
  * **Styling:** Solid obsidian surface (`#161b22`), amber border glow (`1px solid rgba(255, 153, 0, 0.4)`), floating on a dark glassmorphic overlay (`rgba(13, 17, 23, 0.85)` with `blur(8px)`).
  * **Pure-Code Vector SVG Info Icon:** Utilizzo di un'icona vettoriale inline SVG (`<circle cx="8" cy="8" r="6" stroke="rgba(255,153,0,0.7)" stroke-width="1.2".../><line x1="8" y1="7.5" x2="8" y2="11.5".../><circle cx="8" cy="5" r="0.75".../>`) all'interno di `metric_card` e `render_kpi_card`, eliminando caratteri Unicode non standard (U+24D8) e doppi cerchi disallineati per garantire nitidezza assoluta a qualsiasi DPI.
  * **Struttura Standard Istituzionale a 5 Blocchi:** Ogni modale informativo associato a metriche di rischio e bilancio adotta obbligatoriamente la seguente architettura esplicativa:
    1. 📌 **Cos'è (Definizione Formale & Intuizione Finanziaria)**: Definizione rigorosa CFA/FRM e spiegazione intuitiva.
    2. 📐 **Formula Matematica & Spiegazione delle Variabili**: Notazione LaTeX esatta con legenda dettagliata.
    3. 🎯 **Come Interpretarlo & Benchmark Istituzionali**: Range tipici di mercato, soglie di allerta e interpretazione operativa.
    4. ⚙️ **Implementazione nel Codice & Metodologia**: Mappatura esatta del modulo Python, convenzioni (252 giorni, log/simple returns, compounding) e gestione casi limite.
    5. ⚠️ **Limiti, Trappole & Falsi Segnali**: Assunzioni sottostanti, condizioni di stress in cui la metrica fallisce e metriche complementari consigliate.

* **Data Visualizations & Charts (Plotly Integration):**
  * **Canvas:** Fully transparent paper and plot background (`paper_bgcolor="rgba(0,0,0,0)"`, `plot_bgcolor="rgba(0,0,0,0)"`).
  * **Grid Lines:** Minimalist translucent white horizontal/vertical grid lines (`rgba(255, 255, 255, 0.05)`).
  * **Tooltips:** Custom dark callout cards (`#161b22`) bounded by theme-colored accent strokes.

## 5. Layout Principles
* **Dense Financial Information Architecture:** Optimizes screen real estate for maximum data throughput (multi-column KPI rows, radar charts, risk treemaps, and tabular risk matrices) while preventing visual clutter through disciplined alignment.
* **Structured Whitespace Strategy:** Consistent baseline spacing (`16px` margin bottom for card elements, `36px` top margin for section dividers, `20px` card padding).
* **Viewport Canvas Anchoring:** The radial background is fixed to the viewport (`background-attachment: fixed`), providing a continuous luminous surface during vertical page scrolling.
* **Fixed Navigation Docking:** A glassmorphic sidebar (`width: auto`, pinned to left) separated from the main content viewport by a delicate vertical border line (`1px solid rgba(255, 255, 255, 0.08)`).

## 6. Page Hierarchy & Export Center Architecture

### Pagine della Dashboard (21 Moduli Operativi Istituzionali)

#### 🏛️ Sezione 1: Quantitative Risk & Portfolio BI (Moduli 0 – 11)
1. **`0_Control_Room.py`**: Control Room & Ingestione CSV/DeGiro/Google Sheets, Selezione Database (`investment_risk_bi` vs `wealth`), Impostazioni Valuta Base, Total Wealth Hub & Storage Cockpit, DuckDB OLAP Sandbox.
2. **`1_📈_Dashboard_Generale.py`**: Executive Cockpit, Health Score, Radar 360°, ARGUS AI Analyst, Quant Copilot, Multi-Benchmark Overlay e Centro Esportazione Report.
3. **`2_🖥️_Live_Terminal.py`**: Live Market Streaming Tape, Level-2 Order Book (Stoikov Microprice 2018), Fast Ladder Trading, Pre-Trade Compliance Checks, OMS Execution Blotter (TWAP/VWAP) e Bloomberg CLI (`ARGUS:LIVE>`).
4. **`3_🔴_Analisi_Rischio.py`**: VaR/CVaR Euler, Cornish-Fisher (Boudt 2008), Backtesting Kupiec, Volatilità Condizionale GARCH(1,1) & FHS, Market Regime Switching, Isolation Forest ML e Stop-Loss ATR Chandelier.
5. **`4_🔬_Modelli_Quantitativi.py`**: Frontiera Markowitz Ledoit-Wolf, **🧬 Tail Copula (Clayton/Gumbel) & Crash Contagion**, **⚖️ Simulatore Interattivo Trade Sizing (Kelly Criterion)**, Sandbox Ribilanciamento, Hierarchical Risk Parity (HRP), Monte Carlo Student-t, Merton Jump-Diffusion, Black-Scholes Hedging & Covered Call, Attribuzione Brinson-Fachler, Carino Multi-Periodo, Modelli Fattoriali (Carhart 4-Factor, MSCI Barra 5-Factor) e Fixed Income YAS / Z-Spread / CDS.
6. **`5_📋_Posizioni_e_Dettagli.py`**: Posizioni attive, Costo di carico FIFO, **🪦 Posizioni Chiuse & Graveyard Cockpit Multi-Prospettiva (Curva Cumulativa, High-Water Mark, Trading Calendar & Heatmap Mensile, Scomposizione Settori/Asset Class)**, **💰 Tax-Loss Harvesting & Step-Up Wizard (TUIR Art. 67)**, Fisco Cripto-Attività (RT/RW/IVAFE), Smart Rebalancer, Calendario Dividendi e Liquidità Almgren-Chriss.
7. **`6_🏛️_Valutazione_Aziendale.py`**: Altman Z-Score, Scomposizione DuPont (3 e 5 fattori), Piotroski F-Score (9pt), Contabilità Forense (Beneish M-Score & Sloan Accruals), WACC CAPM, Valutazione DCF Monte Carlo, Bilanci 10-K, **🔍 Local RAG SEC Filing Vector Store** e Classificatore ML Distress Risk.
8. **`7_🌪️_Stress_Testing.py`**: Matrice Comparativa MSCI Barra, Analisi Scenari Storici, Macro Scenario Builder e Superficie 3D di Rischio.
9. **`8_📊_Analisi_Temporale.py`**: Tracciamento storico multi-snapshot su MySQL/SQLite, Evoluzione temporale e confronto affiancato con metriche $\Delta$.
10. **`9_📈_Analisi_Tecnica.py`**: Cockpit di Analisi Tecnica & Quantitative Charting, Volume Profile (POC/VAH/VAL), Candlestick Pattern Recognition, Technical Confluence Score Card (0-100) e Multi-Timeframe Alignment (1D vs 1W).
11. **`10_🔍_Screener_Opportunita.py`**: Screener Quantitativo Multi-Fattoriale (Valutazione, Qualità Contabile, Rischio, Momentum), Formula Engine EQS, Archetipi Istituzionali, Pre-Trade Portfolio Impact Simulator e Generatore Factsheet PDF.
12. **`11_💻_BQuant_e_Launchpad.py`**: BQuant In-App Python Sandbox & DuckDB SQL, Institutional Launchpad (5 Ruoli Istituzionali) ed Excel Live Connector (Bloomberg RTD & OpenPyXL).

#### 💎 Sezione 2: Wealth Management & Private Banking (Moduli 12 – 21)
13. **`12_🎛️_Wealth_Control_Room.py`**: Control Room del patrimonio complessivo, sincronizzazione estratti conto bancari, Universal Bank Ingestion Hub (Layout Sniffer) e gestione profili patrimoniali.
14. **`13_🏛️_Patrimonio_e_NetWorth.py`**: Bilancio patrimoniale consolidato a 5 livelli (Liquidità, Investimenti, Previdenza, Asset Fisici, Passività), **🌪️ Unified Macro Stress Engine (Shock Tassi, Ammortamento Mutui $\Delta PMT$, Liquidity Squeeze $t^*$ & Guyton-Klinger SWR)**, Family Office Holding Consolidator e Advisory Pitchbook PDF a 6 pagine.
15. **`14_💳_Cash_Flow_e_Spese.py`**: Budgeting con regola 50/30/20, diagramma Sankey interattivo dei flussi di cassa, monitoraggio entrate/uscite e diagnosi costi fissi.
16. **`15_⌚_Asset_Illiquidi_e_Orologi.py`**: Asset fisici e collezionabili (orologi di lusso, metalli preziosi, opere d'arte) con storico rivalutazioni, perizie e liquidity haircut.
17. **`16_🛡️_Previdenza_e_Pension_Planning.py`**: Simulazione pensione pubblica (INPS) e integrativa, stima del tasso di sostituzione, gap pensionistico e deducibilità fiscale contributi (€5.164,57).
18. **`17_🔥_Indipendenza_Finanziaria_e_FIRE.py`**: Modelli di indipendenza finanziaria (FatFIRE, LeanFIRE, CoastFIRE), simulazione stocastica Merton Jump-Diffusion SPI %, Safe Withdrawal Rate dinamico e target age.
19. **`18_📑_Fiscalita_e_Quadro_RW.py`**: Prospetto precompilato per monitoraggio fiscale estero (Quadro RW, Quadro RT, tributo 1100, IVAFE/IVIE) e ottimizzazione minusvalenze.
20. **`19_🏡_Immobili_e_Mutui.py`**: Registro patrimonio immobiliare, simulazione piani di ammortamento alla francese, calcolo LTV dinamico e Net Home Equity.
21. **`20_⚖️_Pianificazione_Successoria.py`**: Asse ereditario, quote di legittima e disponibile secondo il Codice Civile, imposte di successione/donazione con franchigie e strumenti di protezione (Trust, Polizze Vita, Patti di Famiglia).
22. **`21_🤖_AI_Copilot_e_Advisor.py`**: Assistente patrimoniale conversazionale con accesso contestuale ai dati di bilancio consolidato, validazione di aderenza numerica, guardrails MiFID II / Art. 21 TUF ed Executive Voice Briefing a due voci (CIO & CRO).

### Posizionamento Centro Esportazione Report
Tutti i pulsanti di esportazione (**Report PDF Factsheet 2 Pagine**, **Workbook Excel Multi-Tab .xlsx**, **Report Standalone HTML**, **CSV / ZIP per Power BI**) sono raggruppati in un'unica **Glass Card** posizionata **esclusivamente in fondo alla pagina `1_📈_Dashboard_Generale.py`**, eliminando ogni duplicato nella barra superiore o nelle schede secondarie.

### Regola di Terminologia UI
Non viene utilizzato l'acronimo generico "AI" nell'interfaccia utente. Si utilizzano definizioni quantitative formali come **"ARGUS Quant Advisor"** e **"Diagnostica Quantitativa"**.

## 7. Desktop Application Shell & Icon Specifications

* **Native Desktop Window (`pywebview` + Edge WebView2):**
  * **Window Dimensions:** Default viewport `1366px` width × `850px` height, resizable with minimum boundary `1024px` × `700px`.
  * **Window Title:** `ARGUS — Risk Analytics Platform`.
  * **Chromeless Native Feel:** Eliminates browser tabs, address bars, bookmarks, and developer overlays for a pure institutional software aesthetic.

* **Icon Asset: "L'Occhio di Argus" (`docs/argus_icon.ico`):**
  * **Visual Symbolism:** Cybernetic all-seeing eye with an almond-shaped neon cyan outline (`#00f5d4`), deep cobalt iris (`#4895ef`), and a quantitative trading candlestick embedded in the glowing pupil (`#f72585`).
  * **Formats:** Multi-resolution `.ico` bundle (16x16, 32x32, 48x48, 64x64, 128x128, 256x256) assigned to the executable resources, Windows taskbar, and Desktop shortcut.

## 8. Institutional Reporting Design System & Document Exporting Standards

La generazione documentale istituzionale di ARGUS (PDF Factsheet, Pitchbook a 6 pagine, Master Dossier Excel) adotta una rigorosa specifica formale orientata al Private Banking e Family Office, codificata nei moduli `core/reporting_design_system.py`, `core/modular_factsheet_builder.py` e `core/excel_generator.py`.

### Palette Tipografica e Cromatica "Obsidian Sovereign"
Tutti i documenti esportati condividono la medesima grammatica visiva dell'applicazione desktop:
* **Deep Canvas Base (`#0a0e14` / `colors.HexColor('#0a0e14')`):** Sfondo scuro istituzionale ad alto contrasto.
* **Elevated Card Surface (`#121820`):** Contenitori di tabelle e box metrici con bordi sottili (`#1a222d`).
* **Sovereign Amber Accent (`#ff9900`):** Evidenziazione di KPI critici, intestazioni primarie e indicatori di performance.
* **Positive Green (`#10b981`):** Indicatori di rendimento favorevole, solvibilità e surplus di cassa.
* **Risk Alert Red (`#ef4444`):** Drawdown eccessivo, violazione limiti VaR o shortfall di liquidità.
* **High-Visibility Slate (`#c9d1d9` / `#8b949e`):** Testi corpo e didascalie secondarie per garantire la massima leggibilità a stampa.

### Architettura PDF Vector In-Memory (`InstitutionalNumberedCanvas`)
* **Two-Pass Dynamic Numbering:** Il canvas specializzato `InstitutionalNumberedCanvas` memorizza le chiamate grafiche nel primo passaggio e inietta la numerazione progressiva esatta ("Pagina X di Y") nel secondo passaggio, garantendo la coerenza del conteggio pagine su dossier a lunghezza variabile.
* **Running Headers & Footers Automatici:** Ogni pagina include l'intestazione istituzionale con logo/metadati (`CONFIDENTIAL — PRIVATE WEALTH & RISK DOSSIER`), la data e ora di generazione, il codice portafoglio e il disclaimer regolamentare MiFID II in calce.
* **Watermark di Sicurezza Istituzionale:** Rendering opzionale in filigrana a 45° (`STRICTLY CONFIDENTIAL`) a bassa opacità.
* **Pure Vector Graphics (Zero Memory Leak):** I grafici di asset allocation e ripartizione del rischio vengono renderizzati come elementi vettoriali ReportLab nativi (`Drawing`, `Wedge`, `String`), eliminando radicalmente dipendenze da processi esterni (es. rasterizzazione headless Kaleido o Matplotlib) ed azzerando il rischio di crash da consumo di memoria (leak) nei loop di esportazione massiva.

### Specifiche di Esportazione Excel Interattivo (`openpyxl`)
* **Tabelle Native `ListObject`:** Ogni intervallo tabellare viene convertito in un oggetto tabella nativo di Excel (`TableStyleMedium9`), consentendo l'ordinamento dinamico, il filtraggio automatico e l'espansione automatica delle formule.
* **Formule Dinamiche Live:** Le righe totalizzatrici e di sintesi contengono formule native (`=SUM(...)`, `=AVERAGE(...)`, `=XIRR(...)`), preservando la piena interattività del modello finanziario per l'analista.
* **Formattazione Numerica Coerente:** Applicazione di maschere formali esplicite per valute (`€#,##0.00`), percentuali (`0.00%`) e date ISO (`YYYY-MM-DD`).
* **Sanitizzazione Anti-Formula Injection (CWE-1236):** Trattamento automatico di tutte le celle di testo con escape `'` preventivo sui caratteri sensibili (`=`, `+`, `-`, `@`).

## 9. State Management & Workspace Multi-Tenant Architecture

La sincronizzazione dello stato tra il modulo di Rischio Quantitativo e l'Ecosistema Wealth è orchestrata dal motore di contesto multi-tenant `core/workspace_context.py`:

* **Sottocontesti Tipizzati e Isolati:**
  * `RiskSubContext`: Incapsula posizioni titoli, curve dei rendimenti, matrice di covarianza Ledoit-Wolf, scenari di stress e risultati analitici.
  * `WealthSubContext`: Gestisce conti bancari, budget mensili, debiti immobiliari, perizie su beni collezionabili e pianificazione successoria.
  * `UIViewState`: Traccia i filtri attivi, i timeframe selezionati e lo stato della navigazione senza interferire con i dati di calcolo.
* **Persistenza Deterministica su File (`data/cache/sessions/session_{id}.pkl`):** Salvataggio atomico e caricamento dello stato completo di sessione con audit di integrità.
* **Bonifica Chirurgica delle Chiavi Orfane (`flush_risk_domain()`):** Previene l'inquinamento incrociato (*Cross-Contamination*) tra portafogli o scenari alternativi eliminando selettivamente da `st.session_state` le chiavi dei widget di input senza alterare lo stato globale dell'applicazione.
* **Consolidamento Reattivo In-Memory del Net Worth:** Il portafoglio investimenti liquido del modulo Risk confluisce istantaneamente nel bilancio patrimoniale consolidato del modulo Wealth mediante aggregazione in memoria in tempo reale, senza richiedere il salvataggio preventivo di snapshot su database fisico.

## 10. Quantitative AI Governance & Regulatory Guardrails

La piattaforma integra rigorosi vincoli etici, matematici e normativi per l'intelligenza artificiale generativa e vocale (`core/ai_analyst.py`, `core/sec_rag_engine.py`, `core/voice_advisor_engine.py`):

* **Conformità Regolamentare MiFID II & Art. 21 TUF:**
  * Iniezione automatica e vincolante di disclaimer espliciti che definiscono le analisi come simulazioni quantitative a scopo puramente informativo e di supporto decisionale.
  * Divieto assoluto di raccomandazioni d'investimento personalizzate o sollecitazione al pubblico risparmio senza profilazione formale di adeguatezza (*suitability check*).
* **Validazione di Aderenza Numerica (Anti-Allucinazione):**
  * Configurazione a temperatura conservativa (`temperature: 0.1`) per minimizzare la dispersione semantica.
  * Post-processing con **Numerical Grounding Verifier**: estrazione tramite espressioni regolari di tutti i valori monetari e percentuali generati dal modello LLM e confronto con i valori effettivi presenti nel contesto di calcolo; ogni scostamento ingiustificato viene segnalato o corretto prima del rendering all'utente.
* **Local RAG & Semantic Window Chunking sui Bilanci SEC Form 10-K/10-Q:**
  * Segmentazione del testo normativo con chunking a finestra mobile (800 token con 150 token di overlap) nel pieno rispetto dei confini dei paragrafi.
  * Recupero ibrido potenziato da **Reciprocal Rank Fusion (RRF, $k=60$)** tra ricerca lessicale BM25 ed embedding vettoriali densi con similarità del coseno, per l'interrogazione mirata di sezioni critiche (*Item 1A Risk Factors*, *Item 7 MD&A*).
* **Executive Voice Briefing a Due Voci (CIO & CRO):**
  * Sintesi audio esecutiva basata su un dialogo strutturato tra la tesi macro/strategica del Chief Investment Officer e l'antitesi di rischio e copertura del Chief Risk Officer, garantendo un'analisi dialettica bilanciata.

## 11. Obsidian Sovereign UI/UX Institutional Design System (`core/ui_utils.py`)

Per superare i limiti visuali delle tipiche web app Streamlit e avvicinare l'esperienza a terminali finanziari professionali (Bloomberg, FactSet, Aladdin), è stato implementato il framework visivo **Obsidian Sovereign**:

### 11.1 Matrice dei Token e Contrasti WCAG AAA
| Token CSS | Valore Esadecimale / RGBA | Ruolo Applicativo | Contrasto / Regola |
| :--- | :--- | :--- | :--- |
| `--bg-canvas` | `#0b0f19` (Dark) / `#f8fafc` (Light) | Fondo globale viewport | Antiriflesso, contrasto elevato |
| `--bg-surface` | `#111827` (Dark) / `#ffffff` (Light) | Card di primo livello, pannelli | Separazione netta da canvas |
| `--bg-elevated` | `#1f2937` (Dark) / `#f1f5f9` (Light) | Header card, input field, hover | Elevazione gerarchica visiva |
| `--bg-glass` | `rgba(17, 24, 39, 0.75)` | Modali, overlay, dock sintetici | `backdrop-filter: blur(12px)` |
| `--border-subtle` | `#1f2937` / `#e2e8f0` | Griglie e delimitatori | Spessore 1px |
| `--border-accent` | `rgba(59, 130, 246, 0.4)` | Focus di selezione, contorni KPI | Accento ciano/blu tenue |
| `--accent-bull` | `#10b981` (Fill) / `#34d399` (Text) | Rendimenti positivi, Sharpe | Sfondo `rgba(16, 185, 129, 0.12)` |
| `--accent-bear` | `#ef4444` (Fill) / `#f87171` (Text) | Drawdown, perdite, VaR breach | Sfondo `rgba(239, 68, 68, 0.12)` |
| `--accent-warn` | `#f59e0b` (Fill) / `#fbbf24` (Text) | Warning liquidità, alert | Sfondo `rgba(245, 158, 11, 0.12)` |
| `--accent-info` | `#06b6d4` / `#3b82f6` | Benchmark, mercati aperti | Sfondo `rgba(59, 130, 246, 0.12)` |

### 11.2 Tipografia Monospaziata Tabulare
I dati quantitativi, i prezzi, le percentuali e i valori contabili adottano obbligatoriamente il font `'JetBrains Mono'` con feature CSS `font-feature-settings: "tnum" 1, "zero" 1`. Questo garantisce il perfetto allineamento verticale delle cifre nelle tabelle e nei widget KPI, eliminando l'oscillazione visiva durante i refresh.

### 11.3 Componenti Istituzionali Centralizzati
* **`generate_svg_sparkline(data, width=80, height=24, color=None, show_dot=True)`**: Genera micro-grafici SVG inline in puro codice Python (< 250 byte). Elimina l'overhead di canvas/Plotly per le sparkline nelle metriche, azzerando la latenza e il consumo di RAM del browser.
* **`render_status_badge(text, level='success'|'warning'|'danger'|'critical'|'info'|'neutral', pulse=False, icon=None)`**: Badge a pillola con contrasto WCAG AAA ed animazione pulsante per mercati aperti o sync live.
* **`render_page_header(title, subtitle, icon, badge_status, badge_level)`**: Header standard a 3 livelli con pill di stato dinamica a destra.
* **`render_kpi_metric(title, value, delta, sparkline_data, tooltip, subtitle, level)`**: Card KPI esecutiva con numeri monospaziati tabulari, badge direzionale delta, sparkline SVG e benchmark subtitle.
* **`render_glassmorphic_card(content_html, title, subtitle, badge_text, badge_level)`**: Container in vetro acrilico con backdrop blur ed header contestualizzato.
* **`render_data_table(df, currency_cols, pct_cols, progress_cols, hide_index, height, download_filename)`**: Data grid istituzionale compatta con mapping su `st.column_config.ProgressColumn` per barre orizzontali comparative di allocazione e drawdown.

---

## 12. Plotly Quantitative Data Visualization Framework (`core/ui_utils.py`)

La suite standardizza l'intero stack di rappresentazione grafica su Plotly per garantire identico layout, margini compatti, hover ricchi e toolbar pulite su tutte le 21 pagine applicative:

### 12.1 Template Ufficiali `argus_dark` e `argus_light`
Registrati in `plotly.io.templates`, integrano:
* Griglie cartesiane discrete (`gridcolor="rgba(255, 255, 255, 0.06)"`).
* Margini compatti (`margin=dict(l=40, r=20, t=44, b=40)`).
* Tipografia a due livelli: `'Outfit'` per titoli/annotazioni e `'JetBrains Mono'` per tick degli assi.
* Palette sequenziali finanziarie (`ARGUS_SEQUENTIAL_WEALTH`, `ARGUS_SEQUENTIAL_RISK`) e divergente fissa (`ARGUS_DIVERGING_SCALE`).

### 12.2 Toolbar Configurazione Minima & Export HD (`get_plotly_config`)
Elimina il clutter consumer (lazo, box select, toggle spikelines) mantenendo Pan, Zoom, Reset e Download PNG ad alta definizione (scala 2x, 2400x1440 px).

### 12.3 Factory Layout Unificata (`apply_custom_chart_layout`)
Funzione centrale per l'applicazione coerente di:
* Titoli con gerarchia visiva ed etichette assi.
* Formattazione asse Y: valute (`tickprefix="€ "`, `tickformat=",.2f"`) e percentuali (`tickformat=",.2%"`).
* Spikelines temporali verticali coordinate a mirino (`showspikes=True, spikedash='dot'`).
* Legenda orizzontale posizionata in alto a destra (`orientation="h", y=1.02, x=1.0`).
* Compressione memoria float (`optimize_plotly_figure_memory`).

### 12.4 Pattern Library per i 4 Grafici Fondamentali
1. **Monte Carlo Fan Chart (`create_monte_carlo_fan_chart`)**:
   * Bande percentili stratificate: 5th-95th (90% confidenza), 25th-75th (interquartile 50%).
   * Traiettoria mediana P50 ad alta visibilità (`#38bdf8`, 2.5px).
   * Linea target FIRE / soglia limite orizzontale tratteggiata.
2. **Matrice di Correlazione Cross-Asset (`create_correlation_heatmap`)**:
   * Scala divergente fissa da -1.0 a +1.0 (evita aberrazioni cromatiche su panieri parzialmente decorrelati).
   * Valori `.2f` stampati direttamente in ogni cella con testo monospaziato.
   * Hovertemplate arricchito con coppie di asset e coefficiente di Pearson.
3. **Cash Flow Waterfall Chart (`create_cashflow_waterfall_chart`)**:
   * Flussi positivi in verde smeraldo, spese/uscite in rosso corallo e saldo netto cumulato in blu.
   * Connettori sottili tra barre e cifre valutarie posizionate sopra i blocchi.
4. **NAV Cumulativo + Underwater Drawdown Sincronizzato (`create_equity_drawdown_chart`)**:
   * Subplot a due righe con asse temporale condiviso (`shared_xaxes=True`, `hovermode="x unified"`).
   * Pannello superiore (72%): NAV con riempimento verso zero + benchmark tratteggiato.
   * Pannello inferiore (28%): Underwater Drawdown con riempimento rosso corallo ed evidenziazione picco-valle del Max Drawdown con marker a diamante.
5. **Asset Allocation Multilivello (`create_hierarchical_allocation_chart`)**:
   * Scomposizione gerarchica (Macro-classe ➔ Sotto-classe ➔ Singolo Asset) in formato Sunburst o Treemap ad alta leggibilità.

---

## 13. Personal Financial Statements Architecture (`core/wealth/personal_balance_sheet.py`)

La piattaforma integra un motore contabile dedicato per il **Bilancio Personale Istituzionale**, progettato specificamente per persone fisiche, nuclei familiari e Family Office secondo i principi del CFP Board (*Certified Financial Planner*) e le linee guida del Private Banking:

### 13.1 Stato Patrimoniale a Sezioni Contrapposte (Statement of Financial Position)
* **Equazione Fondamentale di Bilancio Personale:**
  $$\text{TOTALE ATTIVO} = \text{TOTALE PASSIVITÀ} + \text{PATRIMONIO NETTO}$$
* **Attivo (Impieghi di Ricchezza):**
  * *I. Attività Liquide & Mezzi Equivalenti:* Conti correnti bancari, conti deposito, liquidità broker/trading e fondo di emergenza dedicato.
  * *II. Investimenti Finanziari & Capitale Produttivo:* Portafogli azionari, ETF, titoli obbligazionari e cripto-attività collegati al modulo Risk Analytics.
  * *III. Previdenza Integrativa & Risparmio Previdenziale:* Fondi pensione negoziali/aperti, PIP e TFR maturato accantonato.
  * *IV. Attività Reali & Beni Personali:* Abitazione di residenza, immobili a reddito, orologi di lusso e metalli preziosi nel caveau.
  * *V. Crediti Personali & Ratei Attivi:* Depositi cauzionali, crediti d'imposta e crediti verso terzi esigibili.
* **Passivo (Fonti di Terzi / Debiti):**
  * *I. Passività a Breve Termine (< 12 mesi):* Debiti carte di credito a saldo, scoperti bancari esigibili e rateizzazioni a breve.
  * *II. Passività a Medio/Lungo Termine (> 12 mesi):* Mutui ipotecari residui (quota capitale) e finanziamenti personali.
* **Patrimonio Netto (Fonti Proprie / Equity):**
  * Capitale di partenza e riserve da risparmio pregresso cumulato.
  * Risultato economico d'esercizio (surplus generato nell'anno).
  * Riserva di rivalutazione latente di mercato.
  * Quadratura a pareggio perfetta ($\Delta = 0,00\text{ €}$) verificata matematicamente ad ogni caricamento.

### 13.2 Conto Economico di Gestione (Personal Operating Income Statement)
* **Valore della Produzione Personale (Inflows):**
  * Redditi netti da lavoro dipendente, autonomo e borse di studio.
  * Supporto familiare, regali e donazioni ricevute.
  * Proventi finanziari (dividendi, cedole, plusvalenze realizzate).
  * Rimborsi spese netti saldate da terzi ed entrate straordinarie.
* **Costi di Gestione & Consumi Correnti (Outflows):**
  * Spese di vita depurate dai trasferimenti patrimoniali e raggruppate in macro-categorie: Casa/Utenze, Alimentari, Ristoranti/Socialità, Trasporti, Formazione, Salute, Viaggi/Svago, Shopping/Tech, Tasse e Commissioni bancarie.
* **Rendiconto di Allocazione del Capitale (Capital Deployment):**
  * Distinzione rigorosa tra spese di consumo e **Flussi di Investimento** (PAC Azioni/ETF, Cripto-attività, Versamenti Fondo Pensione).
  * Calcolo del **Risparmio Netto d'Esercizio** e della **Variazione Netta della Liquidità** sui conti correnti, illustrati tramite Plotly Waterfall Chart interattivo.

### 13.3 Indici Fondamentali di Bilancio & Rating di Solidità
La salute del bilancio personale è sintetizzata tramite 6 indici con benchmark istituzionali e traffic-light indicator:
1. **Indice di Solvibilità Patrimoniale** ($\frac{\text{Patrimonio Netto}}{\text{Attivo Totale}}$): Target $\ge 70\%$.
2. **Debt-to-Assets** ($\frac{\text{Passività Totali}}{\text{Attivo Totale}}$): Target $\le 30\%$.
3. **Runway Fondo di Emergenza** ($\frac{\text{Liquidità Immediata}}{\text{Spese Mensili Medie}}$): Target $\ge 6,0\text{ mesi}$.
4. **Personal Savings Rate** ($\frac{\text{Risparmio Netto}}{\text{Entrate Totali}}$): Target $\ge 20\%$.
5. **Debt Service-to-Income (DSTI)** ($\frac{\text{Rate Debito Annue}}{\text{Entrate Totali}}$): Target $\le 33\%$.
6. **Invested Assets Ratio** ($\frac{\text{Investimenti} + \text{Previdenza}}{\text{Patrimonio Netto}}$): Target $\ge 50\%$.
* **Radar Chart di Solidità:** Proiezione su coordinate polari normalizzate a 100 per il confronto istantaneo del profilo reale dell'utente rispetto al Benchmark di Private Banking.

---

## 14. Institutional UI/UX Patterns for Enterprise Next-Level Architecture (v8.1)

Con la trasformazione Next-Level Tier-1, il design system di ARGUS introduce 4 nuovi pattern visuali interattivi allineati agli standard BlackRock Aladdin, Bloomberg AIM e MSCI Barra:

### 14.1 MSCI Barra Multi-Asset Factor Risk Decomposition (`src/pages/4_🔬_Modelli_Quantitativi.py`)
* **Waterfall Chart di Varianza:** Visualizzazione a cascata del rischio totale di portafoglio, distinguendo la quota di Varianza Sistematica Fattoriale ($w^T X F X^T w$) dalla Varianza Idiosincratica/Specifica ($w^T \Delta w$) con palette bicolore (Cyan `#00f3ff` per i fattori di stile e Corallo `#f85149` per il rischio specifico).
* **Active Style Factor Tilts Radar Chart:** Grafico a coordinate polari centrato su zero per evidenziare le scommesse attive di stile ($X^T (w - w_{\text{bench}})$) rispetto al benchmark (Market, Value, Size, Momentum, Quality, Low Volatility).
* **Tabella MCTR & PCTR di Eulero:** Data table ad alta densità con gradiente dinamico per PCTR asset ($\sum \text{PCTR}_i = 100\%$) e alert di concentrazione sui titoli con contributo marginale anomalo.

### 14.2 Total Balance Sheet & Human Capital Cockpit (`src/pages/7_🌪️_Stress_Testing.py`)
* **Holistic Net Worth Breakdown Card:** Visualizzazione aggregata a 3 pilastri (Portafoglio Liquido, Real Estate, Capitale Umano Attuariale Nelson-Siegel) con calcolo live del TBS-VaR 95% e TBS-CVaR 95%.
* **Emergency Runway Health Meter:** Indicatore di autonomia finanziaria mensile a stipendio azzerato con soglia critica di sicurezza a 6 mesi.
* **Catastrophic Correlation Trap Alert:** Banner reattivo di avviso in caso di eccessiva correlazione ($\rho > 0.60$) tra settore di impiego lavorativo e asset azionari in portafoglio, con prescrizione quantitativa di de-risking.

### 14.3 Prescriptive Conic Rebalancer & Tri-Agent Council Blotter (`src/pages/21_🤖_AI_Copilot_e_Advisor.py`)
* **Tri-Agent Deliberative Cards:** 3 container affiancati con avatar dedicati (`QuantRiskAuditor`, `TaxEfficiencySpecialist`, `MacroExecutionStrategist`), punteggi individuali (/100) e motivazioni analitiche in linguaggio naturale istituzionale.
* **Consensus Score Gauge:** Indicatore di delibera collegiale (Approved $\ge 70$, Conditional Approval 50-69, Rejected $< 50$) con verbale esecutivo conforme ai requisiti di auditabilità MiFID II.
* **Terminal Blotter FIX Protocol 4.4:** Visualizzatore in monospace scuro ad alto contrasto dei messaggi d'ordine conformi a FIX Protocol 4.4 (`35=D`, `54=Side`, `38=Qty`, `44=LimitPx`, `59=TIF`, `10=Checksum`), con pulsante nativo per copia negli appunti e download del file di routing broker.

### 14.4 Lifetime Total Balance Sheet Monte Carlo Fan Chart
* **Stochastic Area Bands ($P_{10}-P_{90}$):** Fascia semi-trasparente per le traiettorie stocastiche di decumulazione patrimoniale su 5.000 simulazioni fino a 95 anni di età.
* **Median Trajectory Line ($P_{50}$):** Linea continua in verde smeraldo che traccia l'aspettativa mediana di patrimonio netto aggregato.
* **Safe Spending Corridor Overlay:** Linea tratteggiata in oro ambrato che delimita il tetto massimo di spesa annua sostenibile al 95° percentile senza rischio di rovina finanziaria precoce.

---

## 15. Institutional Dual-Engine Architecture & Onboarding Experience (v9.0.0)

La major release **v9.0.0** introduce un'evoluzione radicale dell'esperienza utente e dell'architettura di front-end istituzionale:

### 15.1 Dual-Engine Sidebar & Navigation Rail Segregation
* **Segregazione Rigorosa dei Domini**: Separazione fisica e visiva tra il modulo *Risk Analytics & Quantitative Intelligence* (11 pagine analitiche) e il modulo *Wealth Management, Cash Flow & Fiscalità* (11 pagine di pianificazione patrimoniale).
* **Zero-Recalc Session Persistence**: Gestione dello stato tramite `WorkspaceContext` tipizzato con salvataggio isolato e ripristino istantaneo senza ricalcoli onerosi tra cambi di pagina o widget switch.
* **Parametri Snelliti & Smart Defaults**: Raggruppamento dei controlli avanzati in container comprimibili (*"Impostazioni Avanzate di Calcolo"*), riducendo il rumore visivo iniziale e velocizzando l'operatività quotidiana.

### 15.2 Empty-State Onboarding & 5-Pillar Demo Seeder
* **Accoglienza al Primo Avvio**: Gestione elegante delle sessioni prive di portafoglio caricato, con card interattiva di benvenuto e guida al caricamento.
* **One-Click Demo Seeder**: Iniezione istantanea di un portafoglio dimostrativo realistico basato sui 5 pilastri (*Liquidità, Obbligazioni Governative, Azioni Globali, Real Estate e Capitale Umano*) per esplorare l'intera piattaforma senza configurazioni preliminari.

### 15.3 Vector Factsheet Engine & ReportLab MiFID II Compliance
* **Separazione Plotly / Vettoriale**: Disaccoppiamento tra visualizzazione interattiva a schermo (Plotly WebGL) e rendering vettoriale per stampa/export (ReportLab A4 `InstitutionalNumberedCanvas`).
* **Factsheet Conforme MiFID II & Quadro RW**: Generatore PDF istituzionale a 2 pagine con risk disclosure formale, matrici di rendimento, scomposizione della volatilità e riepilogo fiscale per il monitoraggio transfrontaliero.



