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

* **Modal Windows & Glossary Overlays:**
  * **Shape:** Rounded rectangle (`border-radius: 16px`).
  * **Styling:** Solid obsidian surface (`#161b22`), amber border glow (`1px solid rgba(255, 153, 0, 0.4)`), floating on a dark glassmorphic overlay (`rgba(13, 17, 23, 0.85)` with `blur(8px)`).

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

### Pagine della Dashboard (1 to 7)
1. **`0_Control_Room.py`**: Control Room & Ingestione CSV/DeGiro, Selezione Database (`investment_risk_bi` vs `wealth`), Impostazioni Valuta Base.
2. **`1_📈_Dashboard_Generale.py`**: Executive Cockpit, Health Score, Radar 360°, ARGUS Quant Advisor, Centro Esportazione Report (in fondo alla pagina).
3. **`2_🔴_Analisi_Rischio.py`**: Matrice di Correlazione e K-Means Clustering sui titoli.
4. **`3_🔬_Modelli_Quantitativi.py`**: Frontiera Efficiente Markowitz, Simulatore Monte Carlo Fan/Ribbon Chart, Backtesting VaR (Kupiec Test), Fama-French 3-Factor.
5. **`4_📋_Posizioni_e_Dettagli.py`**: Posizioni attive, Costo di carico FIFO, Smart Rebalancer con prezzi reali, Flusso e Calendario Dividendi per Azienda.
6. **`5_🏛️_Valutazione_Aziendale.py`**: Altman Z-Score, Scomposizione DuPont, Piotroski F-Score, WACC CAPM, Valutazione DCF Monte Carlo, Bilanci 10-K e Comparativa Multiaziendale.
7. **`6_🌪️_Stress_Testing.py`**: MSCI Barra Multi-Scenario Matrix e Beta Shock Waterfall.
8. **`7_📊_Analisi_Temporale.py`**: Tracciamento storico multi-snapshot e confronto affiancato con metriche $\Delta$.

### Posizionamento Centro Esportazione Report
Tutti i pulsanti di esportazione (**Report PDF Factsheet 2 Pagine**, **Workbook Excel Multi-Tab .xlsx**, **Report Standalone HTML**, **CSV / ZIP per Power BI**) sono raggruppati in un'unica **Glass Card** posizionata **esclusivamente in fondo alla pagina `1_📈_Dashboard_Generale.py`**, eliminando ogni duplicato nella barra superiore o nelle schede secondarie.

### Regola di Terminologia UI
Non viene utilizzato l'acronimo "AI" nell'interfaccia utente. Si utilizzano definizioni quantitative formali come **"ARGUS Quant Advisor"** e **"Diagnostica Quantitativa"**.

## 7. Desktop Application Shell & Icon Specifications

* **Native Desktop Window (`pywebview` + Edge WebView2):**
  * **Window Dimensions:** Default viewport `1366px` width × `850px` height, resizable with minimum boundary `1024px` × `700px`.
  * **Window Title:** `ARGUS — Risk Analytics Platform`.
  * **Chromeless Native Feel:** Eliminates browser tabs, address bars, bookmarks, and developer overlays for a pure institutional software aesthetic.

* **Icon Asset: "L'Occhio di Argus" (`docs/argus_icon.ico`):**
  * **Visual Symbolism:** Cybernetic all-seeing eye with an almond-shaped neon cyan outline (`#00f5d4`), deep cobalt iris (`#4895ef`), and a quantitative trading candlestick embedded in the glowing pupil (`#f72585`).
  * **Formats:** Multi-resolution `.ico` bundle (16x16, 32x32, 48x48, 64x64, 128x128, 256x256) assigned to the executable resources, Windows taskbar, and Desktop shortcut.
