# Changelog

Tutti i cambiamenti significativi a questo progetto saranno documentati in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/),
e questo progetto aderisce a [Semantic Versioning](https://semver.org/lang/it/).

---

## [9.18.0] - 2026-09-25

### 🛡️ ISDA SIMM™ v2.6 & Uncleared Margin Rules (UMR), Asset-Liability Management (ALM / LDI & Cash-Flow Matching LP), Rough Volatility (Rough Bergomi) & SVI Arbitrage-Free Surface, Single-Name CDS & iTraxx/CDX Synthetic CDO Tranches, Avellaneda-Stoikov Market-Making & Hawkes VPIN Toxicity, 1-Click CRO & Investment Committee Board-Pack Generator

Questa major release introduce 6 motori quantitativi e di reporting esecutivo di livello Tier-1:

- **ISDA SIMM™ v2.6 & BCBS-IOSCO Uncleared Margin Rules (UMR) Engine (`core/isda_simm_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Calcolo di *DeltaMargin*, *VegaMargin* e *CurvatureMargin* sulle 6 classi di rischio ISDA (*Interest Rate, Credit Qualifying, Credit Non-Qualifying, Equity, Commodity, FX*) con fattori di concentrazione $CR_k$, correlazioni intra/inter-bucket e matrice cross-risk-class $\psi_{r,s}$.
  - Verifica della soglia regolamentare UMR di €50 Milioni e quantificazione del risparmio MVA tramite Central Clearing (CCP LCH / Eurex con MPOR a 5 giorni vs CSA bilaterale a 10 giorni).
- **Asset-Liability Management (ALM), Redington Immunization & Cash-Flow Matching LP Engine (`core/alm_ldi_engine.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - Valutazione attuariale di passività pluriennali nominali e indicizzate all'inflazione, Funding Ratio ($PV_A / PV_L$), Surplus contabile e **1-Year 99% Surplus-at-Risk ($SaR_{99\%}$)**.
  - Verifica delle condizioni di immunizzazione di Redington ($D_A = D_L$, $\text{Convexity}_A > \text{Convexity}_L$), dimensionamento dell'overlay LDI con Receiver IRS 20Y e risoluzione del **Dedicated Bond Cash-Flow Matching LP (`scipy.optimize.linprog` HiGHS)**.
- **Rough Volatility (Rough Bergomi $H \approx 0.10$) & Gatheral SVI Arbitrage-Free Surface Engine (`core/rough_vol_svi_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Parametrizzazione SVI di Gatheral $w(k) = a + b(\rho(k-m) + \sqrt{(k-m)^2 + \sigma^2})$ con verifica esplicita della condizione di assenza di arbitraggio Butterfly di Durrleman ($g(k) \ge 0$) e Calendar Spread ($\partial_T w \ge 0$).
  - Modello frazionario Rough Bergomi (Bayer-Friz-Gatheral 2016) con esponente di Hurst $H \in (0.05, 0.25)$ per lo scaling a legge di potenza dello skew ATM a breve termine $\mathcal{O}(T^{H - 1/2})$.
- **Single-Name CDS Bootstrapping & Synthetic Credit Index Tranches (`core/cds_tranche_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Bootstrapping delle probabilità di sopravvivenza $Q(0, t)$ e intensità di default $\lambda(t)$ da par spread CDS (`1Y..10Y`), ISDA Standard Model Upfront, Risky PV01, CS01 e Jump-to-Default (JTD).
  - Prezzatura 1-Factor Gaussian Copula (Li 2000 / Laurent-Gregory) & Base Correlation delle tranche sintetiche iTraxx Europe / CDX IG (`Equity 0-3%`, `Junior Mezzanine 3-6%`, `Senior Mezzanine 6-9%`, `Senior 9-12%`, `Super-Senior 12-22%`).
- **Avellaneda-Stoikov (2008) Market-Making & Hawkes / VPIN Order-Flow Toxicity Engine (`core/market_making_vpin_engine.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - Calcolo del *Reservation Price* $r(s, q, t) = s - q \gamma \sigma^2 (T - t)$ e delle quote ottime asimmetriche Bid/Ask in funzione dell'inventario $q$.
  - Calcolo della metrica di selezione avversa **VPIN** (Easley-López de Prado-O'Hara 2012) e dell'intensità auto-eccitante di **Hawkes** ($\lambda_t$) con branching ratio $\alpha/\beta$ per l'allerta precoce di Flash-Crash.
- **1-Click Executive CRO & Investment Committee Board-Pack Generator (`core/executive_board_pack_engine.py`, `src/0_Control_Room.py`)**:
  - Sintesi multi-motore con generazione istantanea del **Dossier del Comitato Rischi & Investimenti (HTML5 / JSON)** e **CRO Prescriptive Action Checklist** automatica.
- **Headless REST API v9.18.0 (`api/main.py`) & Test Suite (`tests/test_v917_institutional_suite.py`, `tests/test_v918_ux_visual_canvas.py`)**:
  - 6 nuovi endpoint REST JSON (`/api/v1/margin/isda-simm`, `/api/v1/wealth/alm-ldi`, `/api/v1/pricing/rough-vol-svi`, `/api/v1/credit/cds-tranches`, `/api/v1/execution/market-making-vpin`, `/api/v1/reporting/executive-board-pack`).
- **Riquadri Informativi Metodologici (`render_institutional_info_box`) & Architettura a Tab Separati (Pages 4, 7, 13)**:
  - Implementato in `core/ux_institutional_hub.py` il componente `render_institutional_info_box(...)` con banner istituzionale + guida espandibile a 3 colonne (*1. Fondamento Matematico & Modello*, *2. Come Leggere i KPI & i Grafici*, *3. Implicazioni Regolamentari & Operative*) presente su tutti i 22 motori quantitativi e regolamentari di `src/pages/4_🔬_Modelli_Quantitativi.py` (15 modelli), `src/pages/7_🌪️_Stress_Testing.py` (10 tab in `STRESS_MODELS_CATALOG`) e `src/pages/13_🏛️_Patrimonio_e_NetWorth.py` (5 sotto-tab dedicati in `main_tab_struct`).
  - Risolto lo stacking verticale in `src/pages/7_🌪️_Stress_Testing.py` e `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`, garantendo che ogni laboratorio sia isolato nel proprio tab e che la barra telemetrica globale e il semaforo CRO siano sempre in cima alla pagina.
  - Ripristinato il collegamento dinamico del portafoglio attivo (*Master Wealth*) dal file reale `data/portfolios/Master_Wealth.json` in `extract_live_portfolio_binding` e consolidato il centro di esportazione in un unico popover `📤 Export Center` nella top-bar di `src/0_Control_Room.py`.
  - Sincronizzata la versione **`v9.18.0`** su tutti i moduli (`pyproject.toml`, `api/main.py`, `core/ux_institutional_hub.py`, `core/sidebar.py`, `src/0_Control_Room.py`, `src/pages/2_🖥️_Live_Terminal.py`, `docs/metriche_rischio.md`, `docs/index.md`, `README.md`).

---

## [9.16.0] - 2026-09-25

### 🖥️ Institutional Terminal UX/UI Overhaul: Global Telemetry Top-Ribbon, 1-Click Live Portfolio Auto-Binding, Segmented Domain Workspaces, Scenario Pin & Delta Comparator, Unified Plotly Crosshair Styling & Executive CRO Traffic-Light Radar

Questa major release trasforma l'ergonomia e la User Experience di ARGUS in un terminale istituzionale di livello Bloomberg Launchpad / BlackRock Aladdin attraverso **6 pilastri UX/UI**:

- **Pillar 1 — Segmented Domain Workspace Switcher (`core/ux_institutional_hub.py`, `src/pages/7_🌪️_Stress_Testing.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - Selettori orizzontali di dominio che eliminano lo scroll infinito verticale raggruppando i laboratori per area operativa (*Capitale Regolamentare 9Q*, *Credito & Controparte*, *Commodity & Optimal Liquidation*).
- **Pillar 2 — Global Telemetry Top-Ribbon (`render_institutional_telemetry_ribbon`, `src/0_Control_Room.py`, Pages 4, 7, 13)**:
  - Barra superiore sticky glassmorphic con visualizzazione in tempo reale di: Portafoglio Attivo, NAV Consolidato (€), VaR 99% (1d in € e %), Sharpe Ratio, Regime di Mercato (`🟢 BULL / NORMAL` vs `🔴 STRESS / HIGH VOL`) e versione dinamica `v9.16.0` sincronizzata anche con lo splash screen della Control Room.
- **Pillar 3 — 1-Click Live Portfolio Auto-Binding (`extract_live_portfolio_binding`, `render_live_portfolio_autobind_banner`)**:
  - Estrazione automatica dal portafoglio reale (`st.session_state["last_results"]`) del titolo primario per peso, prezzo spot reale, quantità detenuta, volatilità storica giornaliera/annua e ADV stimato, con toggle 1-click per collegare i modelli quantitativi (*Optimal Liquidation*, *Commodity*, *Derivatives*) al portafoglio attivo.
- **Pillar 4 — Unified Institutional Plotly Styling & Crosshair Sync (`style_institutional_chart`)**:
  - Standardizzazione estetica dei grafici Plotly con sfondo trasparente glassmorphic (`rgba(0,0,0,0)`), crosshair magnetico sincronizzato (`hovermode="x unified"`, `spikemode="across"`), tipografia `Outfit` / `JetBrains Mono` e palette cromatica istituzionale.
- **Pillar 5 — Scenario Pin & Delta Comparator (`compute_scenario_delta_comparison`, `render_scenario_delta_comparator`)**:
  - Funzionalità *"📌 Fissa come Baseline"* in tutti i laboratori avanzati per congelare i risultati di una simulazione e visualizzare fianco a fianco i differenziali assoluti ($\Delta$) e percentuali ($\Delta\%$) quando si modificano i parametri.
- **Pillar 6 — Executive CRO Traffic-Light Radar (`compute_executive_traffic_light_radar`, `render_executive_traffic_light_radar`)**:
  - Semaforo esecutivo a 6 pilastri regolamentari (`Market Risk VaR 99%`, `Basel III LCR & NSFR`, `Fed CCAR / EBA Stressed CET1`, `PRIIPs KID SRI`, `Concentrazione HHI & UCITS`, `Counterparty XVA & Credit IRB`) con classificazione automatica `PASS (🟢)` / `WARNING (🟡)` / `BREACH (🔴)`.
- **Headless REST API v9.16.0 (`api/main.py`) & Test Suite (`tests/test_v916_ux_ui_overhaul.py`)**:
  - Nuovi endpoint REST JSON `/api/v1/ux/executive-radar` e `/api/v1/ux/scenario-delta`.
  - 761/761 unit e integration test superati al 100% con 0 errori Ruff (`ruff check .`).

---

## [9.15.0] - 2026-09-25

### 🏛️ Multi-Curve OIS Discounting (€STR/SOFR & Dual-Curve Bootstrapping), Hull-White 1F Short Rate & LSMC Bermudan Swaptions, CreditMetrics Rating Migration & Basel IRB Vasicek Credit Portfolio Risk, Schwartz 2-Factor Commodity Convenience Yield Curve, Intraday Optimal Liquidation (Square-Root Impact & POV-Capped VWAP), Supervisory Fed CCAR / EBA 9-Quarter Capital Stress

Questa major release espande l'architettura istituzionale di ARGUS con 6 nuovi motori quantitativi di livello Tier-1 per il trading desk di tassi d'interesse, credito multi-debitore, materie prime, esecuzione algoritmica intraday e stress test di capitale regolamentare:

- **Post-LIBOR Multi-Curve OIS Discounting & Dual-Curve Bootstrapping Engine (`core/multicurve_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  -Separazione formale post-LIBOR tra curva di sconto risk-free OIS (€STR / SOFR) e curve di proiezione dei tassi forward (Euribor 3M / 6M, Term SOFR).
  - Bootstrapping esatto e interpolazione cubica monotona Hermite (Pchip / Hagan-West Monotone Convex) sui log-discount factors per prevenire oscillazioni spurie nei tassi forward istantanei.
  - Prezzatura dual-curve di Interest Rate Swaps (IRS), Forward Rate Agreements (FRA) e Tenor Basis Swaps (3M vs 6M) con quantificazione del Multi-Curve Valuation Adjustment e DV01.
- **1-Factor Gaussian Hull-White Short Rate & Longstaff-Schwartz Bermudan Swaptions Engine (`core/hull_white_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Modello di tasso a breve a 1 fattore $dr_t = [\theta(t) - a r_t] dt + \sigma dW_t$ calibrato analiticamente sulla struttura per scadenza dei bond zero-coupon $P(0, T)$ tramite decomposizione affine $P(t, T) = A(t, T) e^{-B(t, T) r_t}$.
  - Induzione all'indietro Least-Squares Monte Carlo (Longstaff & Schwartz 2001) con polinomi di Laguerre/potenza per la valutazione di Bermudan Swaptions (Payer/Receiver) e Callable Bonds, isolando l'Early Exercise Premium (EEP) rispetto al portafoglio di Swaption Europee co-terminali.
- **CreditMetrics Rating Migration & Vasicek IRB Credit Portfolio Risk Engine (`core/credit_portfolio_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Formula regolamentare Basilea II/III Internal Ratings-Based (IRB) di Vasicek (2002) Asymptotic Single Risk Factor (ASRF): correlazione degli asset $\rho(PD)$, aggiustamento di scadenza $b(PD)$, Expected Loss ($EL$), capitale regolamentare $K_{\text{IRB}}$ e Risk-Weighted Assets (RWA).
  - Simulazione Monte Carlo multi-debitore J.P. Morgan CreditMetrics basata sulla matrice di transizione S&P a 8 stati (`AAA`, `AA`, `A`, `BBB`, `BB`, `B`, `CCC`, `D`), rivalutazione mark-to-market sugli spread creditizi, Credit VaR (99.0% e 99.9%), Expected Shortfall ($ES_{99.9\%}$), Incremental Risk Charge (IRC) e decomposizione di Eulero per controparte.
- **Schwartz (1997) 2-Factor Commodity Futures & Convenience Yield Engine (`core/commodity_engine.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - Modello stocastico a due fattori di Gibson-Schwartz (1990) / Schwartz (1997) per prezzo spot $S_t$ e convenience yield netto istantaneo mean-reverting $\delta_t$.
  - Soluzione analitica chiusa per la curva futures $F(S_0, \delta_0, T) = S_0 \exp(A(T) - B(T)\delta_0)$ con fattore stagionale sinusoidale, classificazione automatica del regime (`BACKWARDATION`, `CONTANGO`, `HUMPED`), Roll Yield annualizzato e prezzatura di opzioni Calendar / Storage Spread tramite approssimazione di Kirk (1995).
- **Intraday Optimal Liquidation & VWAP/TWAP Slicing Engine with Square-Root Impact (`core/optimal_liquidation_engine.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - Estensione del modello di esecuzione ottima di Almgren & Chriss (2001) con legge dell'impatto temporaneo a radice quadrata $h(v_k) = \eta \cdot \sigma_{\text{daily}} S_0 (|v_k| / V_k)^{0.5}$, impatto permanente lineare e profilo volumetrico di mercato intraday a U (aste di apertura/chiusura).
  - Confronto completo tra traiettoria ottima avversa al rischio ($\sinh$), Dynamic Intraday VWAP con vincolo di partecipazione massima (POV cap 5%-35%) e benchmark TWAP uniforme, con Implementation Shortfall in EUR e bps.
- **Supervisory Fed CCAR / EBA 9-Quarter Capital Stress & CET1 Trajectory Engine (`core/ccar_stress_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Proiezione prudenziale su 9 trimestri ($Q_1 \dots Q_9$) attraverso i 3 scenari macroeconomici regolamentari (`Supervisory Baseline`, `Supervisory Adverse`, `Fed CCAR / EBA Severely Adverse`).
  - Dinamica trimestrale di Pre-Provision Net Revenue (PPNR), migrazione del portafoglio crediti a 3 stadi IFRS 9 / CECL (`Stage 1` $\to$ `Stage 2 SICR` $\to$ `Stage 3 Default`), Global Market Shock (GMS), inflazione dei RWA, traiettoria del CET1 Ratio rispetto alla soglia MDA/OCR e calcolo dello Stress Capital Buffer (SCB).
- **Headless REST API v9.15.0 (`api/main.py`) & Test Suite (`tests/test_v915_institutional_suite.py`)**:
  - 6 nuovi endpoint REST JSON documentati con OpenAPI (`/api/v1/pricing/multicurve`, `/api/v1/pricing/hull-white`, `/api/v1/risk/credit-portfolio`, `/api/v1/pricing/commodity`, `/api/v1/execution/optimal-liquidation`, `/api/v1/stress/ccar-capital`).
  - 754/754 unit e integration test superati al 100% con 0 errori Ruff (`ruff check .`).

---

## [9.14.0] - 2026-09-25

### 🏛️ XVA & Counterparty Credit Risk (CVA/DVA/FVA/MVA/KVA), Heston Stochastic Volatility FFT Calibration (Carr-Madan 1999), Bayesian Black-Litterman Portfolio Optimization (Idzorek 2005), Basel III Liquidity Standards (LCR & NSFR), Exotic Derivatives & Worst-Of Structured Products (Phoenix Autocallable), Regulatory PRIIPs KID (SRI 1-7) & SFDR ESG (Annex I PAI Table)

Questa major release istituzionale completa l'infrastruttura di risk analytics e asset allocation di ARGUS con 6 motori quantitativi di livello Tier-1:

- **Bilateral XVA & Counterparty Credit Risk Engine (`core/xva_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Calcolo completo dello stack di aggiustamenti di valore bilaterali per derivati over-the-counter (OTC):
    * CVA (Credit Valuation Adjustment) per il rischio di default della controparte con credit spread e LGD.
    * DVA (Debit Valuation Adjustment) per il beneficio di default proprio (DVA bilaterale).
    * FVA (Funding Valuation Adjustment, FCA/FBA) per i costi asimmetrici di funding del collaterale non segregato.
    * MVA (Margin Valuation Adjustment) per il costo del capitale vincolato nei margini iniziali segregati ISDA SIMM.
    * KVA (Capital Valuation Adjustment) per il costo opportunità del capitale regolamentare (cost of capital hurdle rate).
  - Simulazione Monte Carlo dei profili di esposizione creditizia nel tempo: Expected Exposure ($EE$), Potential Future Exposure ($PFE_{95\%}, PFE_{99\%}$), Expected Negative Exposure ($ENE$) ed Effective Expected Positive Exposure ($EEPE$).
  - Modellazione realistica dei contratti Credit Support Annex (CSA): Netting Set, Soglia di non-collateralizzazione (Threshold), Minimum Transfer Amount (MTA), Independent Amount (IA) e Margin Period of Risk (MPOR a 10 giorni).
- **Heston Stochastic Volatility FFT Option Pricing & Surface Calibration Engine (`core/heston_fft_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Implementazione analitica della funzione caratteristica di Heston (1993) stabilizzata secondo Lord-Kahl / Albrecher per eliminare discontinuità di branch-cut.
  - Prezzatura ultra-rapida di opzioni europee (Call e Put via put-call parity) su griglie arbitrarie di strike tramite la trasformata veloce di Fourier (FFT) di Carr & Madan (1999) con damping factor $\alpha=1.5$ e pesi di Simpson.
  - Verifica analitica della condizione di Feller ($2\kappa\theta > \sigma_v^2$) per la garanzia di non-annullamento del processo di varianza e calcolo del Feller ratio.
  - Calibrazione numerica ad alte prestazioni dei parametri $(v_0, \kappa, \theta, \sigma_v, \rho)$ tramite algoritmi L-BFGS-B e SLSQP contro le quote o volatilità implicite di mercato con vincolo di penalità soft.
  - Ricostruzione della superficie 3D di volatilità implicita $\sigma_{\text{imp}}(K, T)$ tramite inversione numerica robusta di Black-Scholes (Brent).
- **Bayesian Black-Litterman Portfolio Optimization Engine (`core/black_litterman_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Formula maestra di Black-Litterman (1992) con reverse optimization per la stima dei rendimenti impliciti di equilibrio di mercato $\boldsymbol{\Pi} = \lambda \boldsymbol{\Sigma} \mathbf{w}_{\text{mkt}}$.
  - Matrice di picking $\mathbf{P}$ e vettore $\mathbf{q}$ per la formulazione flessibile di view assolute (es. "US Equities renderà il 9.5%") e relative (es. "EM Equities sovraperformerà EU Equities del 3.0%").
  - Modellazione della matrice di covarianza dell'incertezza $\boldsymbol{\Omega}$ secondo il metodo di Idzorek (2005), mappando la confidenza soggettiva espressa in percentuale ($0-100\%$) direttamente nella dispersione della view.
  - Calcolo del vettore bayesiano dei rendimenti attesi a posteriori $\mathbf{E}[R]$ e della matrice di covarianza posteriore $\mathbf{M}$.
  - Risoluzione dei pesi ottimi di portafoglio $\mathbf{w}^*$ con vincoli long-only e concentrazione massima tramite programmazione quadratica / SLSQP, tracking error ed information ratio atteso.
- **Basel III Liquidity Risk Engine (`core/basel_liquidity_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Liquidity Coverage Ratio (LCR $\ge 100\%$): classificazione degli attivi liquidi di alta qualità (HQLA) in Livello 1 (haircut 0%), Livello 2A (haircut 15%), Livello 2B (haircut 50%).
  - Applicazione analitica dei tetti massimi regolamentari (Cap del 40% su Livello 2 e Cap del 15% su Livello 2B) con formula di deduzione dell'eccesso.
  - Calcolo dei deflussi stressati a 30 giorni (retail stable 5%, less stable 10%, wholesale non-operational 100%, committed facilities 20%) e cap del 75% sui flussi in entrata ammissibili.
  - Net Stable Funding Ratio (NSFR = Total ASF / Total RSF $\ge 100\%$) con fattori di ponderazione regolamentari per capitale, depositi stabili, mutui e crediti corporate.
  - Dynamic Cash Flow Stress Ladder multi-orizzonte (1d, 7d, 14d, 30d, 60d, 90d, 180d, 360d) con quantificazione dei deflussi cumulati e calcolo dell'orizzonte di sopravvivenza in giorni.
- **Exotic Derivatives & Worst-Of Structured Products Engine (`core/structured_products_engine.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - Motore di valutazione Monte Carlo correlato per certificati su panieri Worst-Of:
    * Phoenix Autocallables con barriera autocall per rimborso anticipato al 100% del nominale, barriera cedola con effetto memoria (recupero cedole non pagate) e barriera di protezione del capitale a scadenza di tipo europeo.
    * Reverse Convertibles con cedole periodiche garantite fisse e downside short put strike con rimborso cash/physical condizionato.
  - Calcolo delle greche analitico/numerico alle differenze finite: Delta ($\Delta$), Gamma ($\Gamma$), Vega ($\nu$), Theta ($\theta$), Rho ($\rho$) e Sensibilità alla Barriera di Protezione.
  - Probabilità di estinzione anticipata (autocall probability per ogni finestra di osservazione), probabilità di perdita del capitale a scadenza (knock-in hit probability) e vita media attesa / duration del certificato.
- **Regulatory PRIIPs KID & SFDR ESG Reporting Engine (`core/regulatory_reporting_engine.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - PRIIPs RTS (Regolamento Delegato UE 2017/653):
    * Summary Risk Indicator (SRI da 1 a 7) combinando la Market Risk Measure (MRM da 1 a 7, derivata dalla Value-at-Risk Equivalent Volatility - VEV calcolata tramite espansione di Cornish-Fisher con skewness e kurtosis) e la Credit Risk Measure (CRM da 1 a 6 derivata dal rating creditizio dell'emittente).
    * Generazione dei 4 scenari regolamentari di performance (Favorevole 90° percentile, Moderato mediana, Sfavorevole 10° percentile, Stress 99° percentile con volatilità accresciuta) calcolati a 1 Anno, Metà RHP e Scadenza RHP in valore terminale monetario ed annualizzato.
  - SFDR (Regolamento UE 2019/2088 & Reg. Delegato 2022/1288):
    * Classificazione del fondo/mandato in Articolo 6, Articolo 8 ("Light Green") o Articolo 9 ("Dark Green").
    * Prospetto completo dei 14 indicatori obbligatori di impatto negativo sulla sostenibilità (Principal Adverse Impacts - PAI, Allegato I): emissioni GHG Scope 1-2-3, carbon footprint, intensità energetica, biodiversità, emissioni nell'acqua, rifiuti pericolosi, violazioni UNGC/OECD, gender pay gap, diversità nel CdA ed esclusione armi controverse.
    * Percentuale di allineamento alla Tassonomia UE e investimenti sostenibili.
- **Headless REST API v9.14.0 (`api/main.py`)**:
  - 6 nuovi endpoint REST JSON ad alte prestazioni documentati con OpenAPI/Swagger:
    * `POST /api/v1/risk/xva`: Metriche bilaterali CVA, DVA, FVA, MVA, KVA e profili di esposizione CSA.
    * `POST /api/v1/pricing/heston`: Prezzatura opzioni FFT Carr-Madan, verifica Feller e calibrazione L-BFGS-B.
    * `POST /api/v1/optimize/black-litterman`: Ottimizzazione bayesiana Black-Litterman con confidenza Idzorek.
    * `POST /api/v1/risk/basel-liquidity`: Ratios regolamentari Basel III LCR e NSFR con stress ladder.
    * `POST /api/v1/pricing/structured-products`: Valutazione certificati Phoenix/Reverse Convertible e greche.
    * `POST /api/v1/regulatory/priips-sfdr`: Dossier regolamentare PRIIPs KID (SRI) e SFDR (14 PAI).
  - Version bump dell'API e dell'endpoint `/health` a `9.14.0`.
- **Suite di Test Unitari & Integrazione v9.14.0 (`tests/test_v914_institutional_suite.py`)**:
  - 7 test istituzionali dedicati (100% pass rate).
  - Test suite globale portata a **747 test passati al 100%** (0 errori, 0 warnings bloccanti, 0 linting issues).

---

## [9.13.0] - 2026-09-25

### 🏛️ FRTB Standardized Approach (BCBS 365 / Basel IV), SABR Calibration & Dupire Local Volatility Surface (3D), NGFS Climate Stress Engine, Multi-Venue Smart Order Router (MiFID II RTS 28), Private Markets Pacing (Yale Model), Interactive Macro War Room & Correlation Breakdown

Questa major release istituzionale arricchisce la piattaforma ARGUS con 6 motori quantitativi di livello Tier-1 per banche d'investimento, desk derivati, banche centrali, broker MiFID II e family office:

- **FRTB Standardized Approach Engine (`core/frtb_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Implementazione completa dei requisiti patrimoniali Basel IV / BCBS 365:
    * Sensitivities-Based Method (SBM): Delta, Vega e Curvature charges sulle 5 classi di rischio regolamentari (GIRR, CSR non-securitisation, Equity, FX, Commodity).
    * Aggregazione multi-scenario di correlazione: Medium, High (+25%) e Low (-25%).
    * Default Risk Charge (DRC): Jump-to-Default (JTD) su debito ed equity con ponderazioni creditizie e LGD.
    * Residual Risk Add-on (RRAO): add-on per pay-off esotici e rischio di correlazione (0.1% / 1.0%).
    * Basel IV Capital Adequacy Ratio e compliance reporting.
- **SABR Stochastic Volatility & Dupire Local Volatility PDE Engine (`core/sabr_local_vol_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Calibrazione analitica del modello SABR (Hagan et al. 2002) $(\alpha, \rho, \nu)$ con formula asintotica esatta ATM e non-ATM per fixed beta (0.50 tassi, 0.70 equity, 1.0 FX).
  - Inversione PDE di Dupire (1994) alle differenze finite per la superficie di volatilità locale $\sigma_{\text{loc}}(K, T)$ a partire dalle opzioni Black-Scholes.
  - Generazione del Volatility Cube 3D denso e visualizzazione interattiva 3D Mesh in Plotly WebGL.
- **NGFS Phase IV Climate Transition & Physical Risk Stress Engine (`core/climate_stress_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Modellazione dei 3 scenari standard del Network for Greening the Financial System (NGFS Phase IV): Orderly Net Zero 2050, Disorderly Delayed Transition, Current Policies / Hot House World.
  - Contabilità delle emissioni societarie Scope 1, 2, 3 e Weighted Average Carbon Intensity (WACI in $tCO_2e / M€$).
  - Meccanismo di trasmissione del carbon price su margini EBITDA, equity re-rating e allargamento credit spread.
  - Quantificazione del rischio fisico (alluvioni, incendi, stress termico) su immobili e asset reali, con calcolo del Climate VaR aggregato.
- **Multi-Venue Smart Order Router & MiFID II RTS 28 Best Execution (`core/smart_order_router.py`)**:
  - Routing algoritmico intelligente su 5 liquidity pools frammentate (Primary Lit Euronext/MTA, Alt MTF Cboe/Turquoise, Systematic Internalizer Citadel, Dark Pool Liquidnet, Crossing Network).
  - Scoring in tempo reale dei venue basato su fee, latenza, fill rate storico e spread.
  - Slicing e routing concorrente degli ordini child (fill passivi vs aggressivi).
  - Report annuale di disclosure Best Execution conforme a MiFID II RTS 28 (top 5 venue per volume, ordini passivi/aggressivi, price improvement in bps ed EUR).
- **Private Markets & Illiquid Asset Valuation Engine (`core/wealth/private_markets_engine.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - Simulazione del ciclo decennale di cassa secondo il modello di Takahashi & Alexander (2001) per fondi Private Equity e Venture Capital: Chiamate di capitale, Distribuzioni, evoluzione NAV e curva a J.
  - Metriche di performance private equity: Net IRR, multipli TVPI, DPI, RVPI e peak capital deficit.
  - Public Market Equivalent (PME) di Kaplan-Schoar e Direct Alpha rispetto ai benchmark quotati (S&P 500 / MSCI World).
  - Correzione econometrica di de-smoothing di Geltner (1991) e Fisher (1994) per neutralizzare l'inerzia artificiale delle perizie periodiche e ripristinare la vera volatilità e correlazione.
- **Interactive Macro War Room & Correlation Breakdown Stress Engine (`core/macro_war_room.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Costruttore di shock macro a leve multiple: shift parallelo della curva dei tassi, twist pendenza (2Y-10Y flattening/steepening), inflazione CPI, impennata del petrolio/energia, oscillazione FX USD, crollo equity e allargamento spread creditizi OAS.
  - Correlation Breakdown Engine: modellazione del crollo sistemico delle correlazioni verso equicorrelazione di panico $\mathbf{R}_{\text{panic}} \to 0.85$, aumento della volatilità e quantificazione della perdita di diversificazione.
  - Calcolo del fabbisogno di cuscino di liquidità e margin call per variazione nei derivati.
- **Headless REST API v9.13.0 (`api/main.py`)**:
  - 6 nuovi endpoint REST JSON documentati con OpenAPI/Swagger:
    * `POST /api/v1/risk/frtb-sbm`: Calcolo requisiti patrimoniali FRTB.
    * `POST /api/v1/pricing/sabr-vol`: Calibrazione SABR e superficie locale Dupire.
    * `POST /api/v1/stress/climate-ngfs`: Stress test climatico NGFS.
    * `POST /api/v1/execution/smart-route`: Routing SOR e report RTS 28.
    * `POST /api/v1/wealth/private-markets`: Pacing a 10 anni PE e de-smoothing.
    * `POST /api/v1/stress/macro-war-room`: Simulazione Macro War Room e rottura correlazioni.
  - Bump versione API a `9.13.0`.
- **Suite di Test Unitari & Integrazione v9.13.0 (`tests/test_v913_institutional_suite.py`)**:
  - 7 test istituzionali dedicati (100% pass rate).
  - Test suite globale del progetto portata a **740 test passati al 100%** (0 errori, 0 warnings bloccanti, 0 linting issues).

---

## [9.12.0] - 2026-09-25

### 🏛️ Barra Structural Multi-Asset Risk Model, Solvency II SCR Standard Formula, DCC-GARCH & Vine Copula, Mock FIX 4.4 Engine & L2 DOM, Generational Succession Optimizer, Risk Watchdog & Notification Hub

Questa major release istituzionale espande ulteriormente la suite di ingegneria finanziaria e conformita regolamentare di ARGUS con 6 moduli di livello tier-1 per l'investment management, le assicurazioni, l'esecuzione algoritmica e il family office:

- **Barra-Style Structural Multi-Asset Risk Model (`core/barra_risk_model.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Decomposizione formale della covarianza strutturale $\\boldsymbol{\\Sigma} = \\mathbf{X}\\boldsymbol{\\Sigma}_F\\mathbf{X}^T + \\boldsymbol{\\Delta}_\\epsilon$.
  - Stima cross-section e time-series dei factor loadings per 6 fattori di stile (Size, Value, Momentum, Quality, Low Volatility, Liquidity), 11 settori GICS e macro fattori (Term/Rates, Credit Spread, Breakeven Inflation, FX USD).
  - Decomposizione Euleriana di varianza (Systematic vs Specific) e calcolo Marginal/Percent Contribution to Total Risk (MCTR / PCTR) sia a livello di singolo asset che per fattore.
  - Analisi del rischio attivo: Active Risk (Tracking Error) e Factor Tilts rispetto al benchmark.
- **Solvency II Standard Formula & SCR Engine (`core/solvency2_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Calcolo del Requisito Patrimoniale di Solvibilita (SCR) conforme al Regolamento Delegato (UE) 2015/35 EIOPA e Direttiva 2009/138/CE.
  - Sub-moduli Market Risk completi: Interest Rate (shock up/down con duration ladder), Equity (Type 1 a 39%, Type 2 a 49%, strategic equity a 22%, symmetric adjustment +-10%), Property (25%), Spread risk per Credit Quality Step (CQS 0-6), Concentration risk per emittente e Currency (+-25% vs EUR).
  - Matrice di correlazione aggregata EIOPA $\\boldsymbol{\\Omega}_{\\text{mkt}}$, Basic SCR (BSCR), Rischio Operativo $\\text{SCR}_{\\text{op}}$, Loss-Absorbing Capacity (LAC) e Solvency Ratio (EOF / SCR %).
  - Export dati conforme ai Quantitative Reporting Templates (QRT) S.25.01.21 e S.26.01.01.
- **DCC-GARCH Dynamic Conditional Correlation & Vine Copula Tail Risk (`core/dcc_garch_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Modellazione econometrica a due stadi: filtraggio univariate GARCH(1,1) per volatilita condizionale e stima della correlazione dinamica tempo-variante $R_t$ (Engle 2002).
  - Modellazione della dipendenza di coda estrema asimmetrica tramite Regular Vine Copula (Clayton per crash contagion congiunti, Gumbel per rally, Student-t e Gaussian).
  - Previsione $T+1$ e $T+5$ di covarianza condizionale $H_t$ e simulazione Monte Carlo su copula a code spesse per Dynamic VaR / CVaR al 95%, 99% e 99.5%.
- **Mock FIX 4.4 Engine & L2 Depth-of-Market (DOM) Simulator (`core/fix_engine.py`)**:
  - Parser, Lexer e Serializer per protocollo tag-value FIX 4.4 standard con validazione CheckSum a 3 cifre modulo 256.
  - Session state machine per Logon (`35=A`), Heartbeat (`35=0`), NewOrderSingle (`35=D`), ExecutionReport (`35=8`), OrderCancel (`35=F`).
  - Simulatore di Order Book L2 Depth-of-Market a 10 livelli di bid e ask attorno al mid price.
  - Matching engine con book walking per ordini Market e accodamento con probabilita di fill per ordini Limit.
  - Post-Trade Transaction Cost Analysis (TCA) completa: Arrival Price vs Execution VWAP vs Terminal Price, Implementation Shortfall in EUR e bps, scomposizione Slippage, Price Impact e Delay.
- **Family Office Generational Wealth Succession Optimizer (`core/wealth/succession_optimizer.py`, `src/pages/13_🏛️_Patrimonio_e_NetWorth.py`)**:
  - Confronto stocastico a 30 anni su 5 architetture successorie:
    1. Regime Ordinario (successione diretta, franchigie €1M/€100k, imposte 4%/6%/8%, ipo-catastali 3%, CGT 26%).
    2. Holding Familiare (PEX 95% Art. 87 TUIR, Patto di Famiglia Art. 768-bis c.c. con esenzione totale Art. 3 c. 4-ter D.Lgs. 346/1990).
    3. Trust Fiduciario (segregazione patrimoniale, differimento tassazione all'uscita ex AdE Circolare 34/E/2022).
    4. Polizze Vita Ramo I/III PPLI (esenzione successoria Art. 12 D.Lgs. 346/1990, impignorabilita Art. 1923 c.c.).
    5. Ottimizzazione Ibrida (Patto + PPLI + Trust).
  - Simulazione Monte Carlo 30Y con decumulazione fondatore (G1), primo passaggio (G1 -> G2) e secondo passaggio (G2 -> G3).
  - Calcolo del Tax Alpha generazionale (€ e %), probabilità di conservazione del capitale e punteggio di asset protection.
- **Event-Driven Risk Watchdog & Multi-Channel Notification Hub (`core/watchdog/risk_watchdog.py`)**:
  - Monitoraggio proattivo dei limiti del Risk Appetite Framework (RAF): VaR 99%, Solvency Ratio, Max Drawdown, concentrazione singola/settore e runway liquidita.
  - Webhook dispatcher con payload formattati per Telegram Bot API, Discord Webhook (rich embeds), Slack Incoming Webhooks (Block Kit) e SMTP Email, con modalita mock per testing e audit trail in-memory.
- **Nuovi Endpoint REST Headless v9.12.0 (`api/main.py`)**:
  - `POST /api/v1/risk/barra`: Decomposizione fattoriale strutturale Barra.
  - `POST /api/v1/risk/solvency2-scr`: Requisito patrimoniale Solvency II SCR.
  - `POST /api/v1/risk/dcc-garch`: Correlazione dinamica DCC-GARCH e rischio di coda.
  - `POST /api/v1/execution/fix/order`: Esecuzione simulata FIX 4.4 su DOM L2 e TCA.
  - `POST /api/v1/wealth/succession-optimization`: Ottimizzazione successoria 30Y Monte Carlo.
  - `POST /api/v1/watchdog/check`: Valutazione limiti RAF e invio alert.
  - `GET /api/v1/watchdog/alerts`: Registro storico degli alert generati.
- **Suite di Test Unitari & Integrazione v9.12.0 (`tests/test_v912_institutional_suite.py`)**:
  - Suite dedicata con 7 test esaustivi coprenti tutti i pilastri (100% pass rate).

---

## [9.11.0] - 2026-09-25

### 🌐 Walk-Forward Rolling OOS Engine, HMM Adaptive Allocation, Total Wealth Reverse Stress, SciPy HiGHS MIP Rebalancer, Async Job Queue & Regulatory Stress Dossier PDF

Questa major release istituzionale completa l'infrastruttura quantitativa e headless di ARGUS, introducendo 6 pilastri avanzati per la gestione del rischio, l'ottimizzazione discreta e la scalabilità microservizi:

- **Walk-Forward Multi-Strategy Rolling Out-of-Sample Engine (`core/walk_forward_engine.py`, `src/pages/4_🔬_Modelli_Quantitativi.py`)**:
  - Simulazione rolling out-of-sample realistica per strategie quantitative (Equal Weight, HRP, Spinu ERC, Max Sharpe Ledoit-Wolf).
  - Finestre di training in-sample configurabili e finestre out-of-sample rolling con frizioni di mercato (commissioni di ribilanciamento bps, slippage ed execution spread).
  - Serie cumulate out-of-sample, drawdown profile e statistiche complete (CAGR, Volatilità, Sharpe Ratio, Calmar Ratio, Max Drawdown, Annual Turnover).
- **Regime-Conditional Adaptive Allocation & HMM Overlay (`core/regime_allocation.py`)**:
  - Classificazione probabilistica dello stato di mercato (Bull, Neutral, Crisis) con Hidden Markov Model (HMM) e Gaussian Mixture.
  - Modulazione dinamica dei budget di rischio $b_i$: haircut prudenziale sugli asset risk-on in caso di shock/crisi e sovrappeso asimmetrico su safe-haven e cash proxy.
  - Risoluzione dell'allocazione ottima tramite Spinu Convex Risk Budgeting (`solve_spinu_risk_budgeting`).
- **Total Wealth Reverse Stress Testing (Solvency & Ruin Multi-Asset) (`core/wealth/total_wealth_reverse_stress.py`, `core/macro_stress_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Formulazione di Reverse Stress Testing su 5 fattori di ricchezza familiare/HNWI (Liquid Markets, Real Estate, Corporate Equity / PMI, Debito/Mutui Euribor, Illiquid / Luxury).
  - Ottimizzazione vincolata a minima distanza di Mahalanobis $D_M$ sotto matrice di covarianza macroeconomica congiunta per barriere di solvibilità (Debt-to-Assets $\ge 60\%$) e rovina patrimoniale (Net Worth loss).
  - Identificazione analitica del fattore più vulnerabile, stima del periodo di ritorno probabilistico (distribuzione $\chi^2$) e raccomandazioni di salvaguardia patrimoniale.
- **Mixed-Integer Programming (MIP) Cardinality & Lot-Sizing Rebalancer (`core/mip_rebalancer.py`, `core/services/rebalancing_service.py`)**:
  - Solutore MILP basato su SciPy HiGHS (`scipy.optimize.milp`) per l'allocazione con quote intere e vincoli discreti reali.
  - Vincolo di cardinalità massima $\sum z_i \le K$ per portafogli compatti a basso turnover.
  - Vincolo di lotto minimo negoziabile ($L_i \in \mathbb{Z}^+$), soglia minima di trade in EUR e budget fiscale sulle plusvalenze realizzate (CGT budget).
  - Integrazione nativa in `RebalancingService.execute_rebalance` sotto strategia `"mip_cardinality"`.
- **Asynchronous Job Queue & WebSocket Gateway per la REST API Headless (`api/main.py`)**:
  - Motore di job non bloccante con `BackgroundTasks` di FastAPI:
    - `POST /api/v1/jobs/submit`: Accodamento asincrono di task ad alta intensità computazionale.
    - `GET /api/v1/jobs/{job_id}`: Polling di stato e recupero dei risultati.
    - `GET /api/v1/jobs`: Registro storico dei job eseguiti.
  - Streaming in tempo reale tramite WebSocket su `/api/v1/stream/ticks`.
  - Nuovi endpoint REST sincroni: `/api/v1/backtest/walk-forward`, `/api/v1/optimize/regime-adaptive`, `/api/v1/risk/total-wealth-reverse-stress`, `/api/v1/rebalance/mip`, `/api/v1/reports/stress-dossier`.
- **Regulatory Stress Testing Dossier PDF a 4 Pagine (`core/pdf_generator.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Generatore vettoriale di documentazione fiduciaria A4 conforme a EBA Guidelines on Stress Testing / Basel III / Solvency II.
  - 4 pagine strutturate: Executive Macro Summary & Scenari EBA/CCAR (Pag. 1), Decomposizione Fattori & Attribuzione Perdite (Pag. 2), Reverse Stress Testing & Rovina Patrimoniale (Pag. 3), Piano di Mitigazione Capitale & Tracciabilità di Audit con firme CRO/Compliance (Pag. 4).
- **Suite di Test Unitari & Integrazione v9.11.0 (`tests/test_v911_institutional_suite.py`)**:
  - Suite dedicata con 6 test esaustivi coprenti tutti i pilastri (100% pass rate).

---

## [9.10.0] - 2026-09-24

### 💎 Spinu Convex Risk Budgeting, Regulatory Reverse Stress Testing, Gatheral SVI & Institutional Factsheet PDF

Questa release istituzionale eleva le capacità analitiche e l'interoperabilità di ARGUS agli standard qualitativi di un desk tier-1 di Quantitative Risk Management & Portfolio Construction:

- **Ottimizzazione Risk Parity & Budgeting Convesso di Florian Spinu (2013) (`core/advanced_quant.py`)**:
  - Implementata la formulazione del potenziale strettamente convesso:
    $$\min_{x > 0} \frac{1}{2} x^T \Sigma x - \sum_{i=1}^N b_i \ln(x_i)$$
  - Gradiente analitico esatto $\nabla f(x) = \Sigma x - \frac{b}{x}$ e convergenza globale garantita tramite algoritmo quasi-Newton L-BFGS-B con vincoli di positività stretta $x_i > 0$ e fallback SLSQP.
  - Supporto nativo per **Arbitrary Risk Budgeting** (budget di rischio frazionari arbitrari $b_i$, con $\sum b_i = 1$) ed **Equal Risk Contribution (ERC / Pure Risk Parity)** con $b_i = 1/N$.
  - Decomposizione esatta del rischio marginale (MRC) e del contributo percentuale di rischio (PRC).
- **Motore di Regulatory Reverse Stress Testing (Linee Guida EBA & BCE) (`core/macro_stress_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Risoluzione dell'inverso dello stress test sotto vincolo di perdita target prefissata $\mathcal{L}^*$ (es. $-15\%$ o $-20\%$):
    $$\min_{\mathbf{f}} \frac{1}{2} \mathbf{f}^T \Sigma_f^{-1} \mathbf{f} \quad \text{s.t.} \quad \boldsymbol{\beta}^T \mathbf{f} \le \frac{\mathcal{L}^*}{100}$$
  - Calcolo della **distanza statistica di Mahalanobis** $d_M = \sqrt{\mathbf{f}^{*T} \Sigma_f^{-1} \mathbf{f}^*}$ e del relativo $p$-value di plausibilità sotto distribuzione $\chi^2$ a 6 gradi di libertà.
  - Rating qualitativo di plausibilità dello scenario con badge di severità (Plausibile, Severo, Molto Severo, Cigno Nero) e stima della frequenza empirica implicita.
  - Scomposizione della perdita tra 6 macro-fattori regolamentari: Azionario Globale, Tasso Sovrano 10Y, Spread Corporate IG, Spread Corporate HY, FX EUR/USD, Materie Prime/Energia.
  - Nuova tab interattiva dedicata in UI con slider soglia $\mathcal{L}^*$, grafici Plotly e matrici di shock.
- **Superficie di Volatilità 3D No-Arbitrage SVI di Jim Gatheral (2004) (`core/volatility_surface.py`)**:
  - Implementazione della parametrizzazione Raw SVI per la varianza totale implicita:
    $$w(k) = a + b \left[ \rho (k - m) + \sqrt{(k - m)^2 + \sigma^2} \right]$$
  - Verifica rigorosa delle condizioni no-arbitrage: vincoli asintotici sui momenti di Roger Lee ($b(1 + |\rho|) \le 4/T$) e non-negatività della densità neutrale al rischio di Durrleman ($g(k) \ge 0$).
  - Calibrazione numerica del sorriso tramite SLSQP con fitting simultaneo cross-maturity (1M, 3M, 6M, 12M).
- **Generatore di Institutional Portfolio Factsheet PDF a 2 Pagine (`core/pdf_generator.py`, `src/pages/1_📈_Dashboard_Generale.py`)**:
  - Sviluppato motore Platypus su standard Morningstar / BlackRock con canvas numerato `Page X of Y` e palette istituzionale:
    - **Pagina 1 (Executive Tear Sheet)**: Header, 4 KPI cards, donut vettoriale di allocazione, matrice di rischio Cornish-Fisher/Basilea IV e Top 7 posizioni con DTL.
    - **Pagina 2 (Attribution & Stress Profile)**: Tabella di regressione ed esposizione Fama-French a 5 fattori + Carhart con $t$-stat, matrice scenari regolamentari EBA/CCAR, profilo ALM Fixed Income & liquidità ADV, Executive AI Commentary e disclaimer legale MiFID II.
  - Integrato pulsante di download immediato "📄 Scarica Factsheet Istituzionale (2 Pagine PDF)" nella Dashboard Generale.
- **Espansione Headless REST API Microservice (`api/main.py`)**:
  - Rilasciati 7 nuovi endpoint REST ad alte prestazioni:
    - `POST /api/v1/optimize/erc`: Spinu convex risk budgeting ed Equal Risk Contribution.
    - `POST /api/v1/risk/reverse-stress`: EBA/BCE minimum Mahalanobis reverse stress testing.
    - `POST /api/v1/risk/fama-french`: OLS multivariate factor attribution & regression.
    - `POST /api/v1/fixed-income/analytics`: Bloomberg YAS duration, convexity, DV01 e stress matrix.
    - `POST /api/v1/risk/liquidity`: Basel III DTL, Amihud illiquidity e tier breakdown.
    - `POST /api/v1/tax/harvesting`: Italian TUIR tax-loss harvesting & potential savings.
    - `GET /api/v1/reports/factsheet`: Streaming del PDF Factsheet istituzionale a 2 pagine.
- **Suite di Test Unitari Istituzionale (`tests/test_institutional_v910.py`)**:
  - 9 test automatizzati coprenti convergenza del solutore convesso, arbitraggio SVI Durrleman, reverse stress testing, validazione binaria del PDF e suite REST TestClient (100% pass rate).

---

## [9.9.0] - 2026-09-24

### 🚀 Real Multifactor Econometrics, Portfolio Fixed Income ALM, Liquidity Risk & Tax Harvesting

Questa release estende l'infrastruttura quantitativa e di wealth intelligence di ARGUS introducendo motori di livello tier-1 per asset-liability management, liquidità endogena ed efficienza fiscale proattiva:

- **Modello Econometrico Fama-French & Carhart Reale (`core/risk_engine.py`)**:
  - Eliminata ogni simulazione sintetica da `compute_fama_french_exposures` e `compute_carhart_4factor_exposures`, collegandole direttamente alla libreria ufficiale Kenneth French dal Dartmouth College (`core/factor_library.py`).
  - Introdotta la funzione `compute_fama_french_5factor_exposures` a 5 fattori + Momentum (Mkt-RF, SMB, HML, RMW, CMA, MOM).
  - Restituzione completa di $t$-statistiche, $p$-values, $R^2$ aggiustato, confidenza al 95%, scomposizione del rischio sistematico vs specifico e rolling betas a 60 giorni.
- **Aggregatore di Rischio Reddito Fisso & ALM di Portafoglio (`core/fixed_income.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Implementata la funzione `compute_portfolio_fixed_income_analytics`:
    - Filtraggio automatico e classificazione di bond diretti (governativi/corporate) ed ETF obbligazionari.
    - Calcolo di Macaulay Duration, Modified Duration ponderata e Convessità effettiva di portafoglio.
    - Calcolo del **Portfolio DV01 (PVBP)** in unità monetarie (perdita in € per ogni +1 basis point di rialzo tassi).
    - Decomposizione delle Key Rate Durations (2Y, 5Y, 10Y, 30Y) per segmenti di curva.
    - Scenari di stress non-paralleli della curva dei tassi: Bull Steepener, Bear Steepener, Bull Flattener, Bear Flattener e parallel shifts ($\pm 50, \pm 100, \pm 200$ bps).
    - Nuova sub-tab dedicata nella pagina di Stress Testing.
- **Motore di Rischio Liquidità Endogena & Orizzonte DTL (`core/risk_engine.py`, `src/pages/7_🌪️_Stress_Testing.py`)**:
  - Implementata la funzione `compute_portfolio_liquidity_risk`:
    - Stima del Volume Medio Giornaliero (ADV) e turnover ponderato in Euro/USD per ciascun asset.
    - Calcolo puntuale dei **Days to Liquidate (DTL)** a vincolo prudenziale di partecipazione (10% e 20% di ADV).
    - Indice di Illiquidità di Amihud ($|R_t| / \text{Volume}_t$) e impatto di mercato permanente Almgren-Chriss.
    - Ripartizione del portafoglio nei 4 Tier di Liquidità istituzionali (Tier 1: <1g, Tier 2: 1-3g, Tier 3: 3-7g, Tier 4: >7g).
    - Calcolo del **Liquidity-Adjusted VaR (L-VaR)** endogeno e del Liquidity Risk Premium percentuale.
- **Screener & Ottimizzatore di Tax-Loss Harvesting (`core/tax_engine.py`, `src/pages/18_📑_Fiscalita_e_Quadro_RW.py`)**:
  - Implementata la funzione `compute_tax_loss_harvesting_opportunities`:
    - Scansione delle perdite non realizzate e calcolo del Tax Alpha (credito d'imposta recuperabile al 26% o 12.5%).
    - Mappatura intelligente di strumenti sostitutivi compliant ad elevata correlazione ($\rho \ge 0.98$) per evitare la perdita di beta di mercato (es. SWDA $\leftrightarrow$ LCWD, VWCE $\leftrightarrow$ FWRA, CSSPX $\leftrightarrow$ VUAA).
    - Monitoraggio delle minusvalenze in scadenza quadriennale (art. 68 TUIR) con livello di urgenza.
- **Simulatore Stocastico di Cash Flow e Decumulazione a Ciclo di Vita (`core/wealth/tbs_monte_carlo.py`, `core/wealth/__init__.py`)**:
  - Implementata la funzione `compute_stochastic_cash_flow_decumulation`:
    - Simulazione Monte Carlo su N cammini correlando rendimenti di mercato, inflazione, progressione salariale e mutui.
    - Calcolo della probabilità di rovina di cassa a ciclo di vita, età di massima fragilità finanziaria e raccomandazione sul corridoio di spesa sostenibile (Safe Spending Corridor).
- **Nuova Suite di Test Automatizzati**:
  - Aggiunto `tests/test_institutional_enhancements.py` con 7 test di validazione integrata (100% pass rate).

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
