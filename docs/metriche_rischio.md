# Calcolo delle Metriche di Rischio, Modelli Econometrici e Valutazione Aziendale

Questo documento illustra la metodologia, la formulazione matematica e le applicazioni pratiche adottate all'interno del motore quantitativo (`core/risk_engine.py`, `core/financial_analysis.py`, `core/tax_engine.py`, `core/attribution.py`, `core/risk_limits.py`) di **ARGUS Risk Analytics Platform**. Tutti i calcoli basati su serie storiche considerano i rendimenti giornalieri rettificati (*Adjusted Close*) ed un anno lavorativo standard di 252 giorni di negoziazione.

---

## 1. Motore Contabile FIFO (First-In, First-Out)

Per determinare accuratamente il costo di carico e i profitti/perdite realizzati su portafogli con acquisti e vendite frazionate nel tempo, il sistema implementa un **motore a code FIFO (`_fifo_engine`)**:

1. **Gestione Acquisti**: Ogni operazione di acquisto (`buy`) aggiunge un lotto $(q_i, p_i)$ alla coda FIFO dell'asset.
2. **Gestione Vendite**: Ogni operazione di vendita (`sell`) consuma le quote a partire dai lotti più vecchi nella coda:
   \[ \text{PnL Realizzato} = \sum_{k} q_{\text{venduti}, k} \cdot (p_{\text{vendita}} - p_{\text{acquisto}, k}) - \text{Commissioni} \]
3. **Prezzo Medio di Carico Residuo (Weighted Average Cost Basis - WACP)**:
   \[ \text{WACP} = \frac{\sum_{m} q_{\text{residuo}, m} \cdot p_{\text{acquisto}, m}}{\sum_{m} q_{\text{residuo}, m}} \]
4. **Dividendi**: I dividendi storici incassati vengono sommati direttamente per determinare il PnL totale effettivo.

---

## 2. Metriche di Rischio di Mercato e Tail Risk

### Volatilità Annualizzata
Misura la dispersione dei rendimenti del portafoglio attorno alla loro media:
- **Volatilità Giornaliera**: $\sigma_d = \sqrt{\frac{1}{N-1} \sum_{t=1}^N (R_t - \bar{R})^2}$
- **Volatilità Annualizzata**: $\sigma_a = \sigma_d \times \sqrt{252}$

### Asimmetria (Skewness)
Misura la simmetria della distribuzione dei rendimenti attorno alla media:
\[ S = \frac{\frac{1}{N} \sum_{t=1}^N (R_t - \bar{R})^3}{\sigma_d^3} \]
- $S < 0$: Coda sinistra pronunciata (maggiore probabilità di perdite estreme).
- $S > 0$: Coda destra pronunciata.

### Curtosi (Kurtosis / Fat Tails)
Misura la pesantezza delle code della distribuzione rispetto a una distribuzione gaussiana normale:
\[ K = \frac{\frac{1}{N} \sum_{t=1}^N (R_t - \bar{R})^4}{\sigma_d^4} - 3 \]
- $K > 0$: Presenza di code spesse (*fat tails*), ovvero eventi estremi più frequenti rispetto alla normale.

### Tracking Error
Misura la deviazione standard del rendimento attivo rispetto al benchmark ($R_b$):
\[ TE = \sqrt{\frac{1}{N-1} \sum_{t=1}^N \left( (R_t - R_{b,t}) - \overline{(R - R_b)} \right)^2} \times \sqrt{252} \]

---

## 3. Value at Risk (VaR) & Conditional VaR (CVaR)

Il Value at Risk stima la massima perdita potenziale in un orizzonte temporale $T$ (da 1 a 20 giorni) ad un livello di confidenza $1 - \alpha$ (90%, 95%, 99%).

### 1. VaR Storico
È il percentile empirico esatto della distribuzione dei rendimenti giornalieri storici:
\[ VaR_{\text{Storico}}(1, \alpha) = - \text{Percentile}(R, \alpha) \]

### 2. VaR Parametrico (Gaussiano)
Basato sull'assunzione di rendimenti normalmente distribuiti con media $\mu$ e deviazione standard $\sigma_d$:
\[ VaR_{\text{Parametrico}}(1, \alpha) = - (\mu - Z_\alpha \cdot \sigma_d) \]

### 3. VaR Cornish-Fisher (Modello Avanzato)
Incorpora Skewness ($S$) e Kurtosis ($K$) tramite l'espansione di Cornish-Fisher per correggere la stima in presenza di code spesse:
\[ Z_{CF} = Z_\alpha + \frac{1}{6}(Z_\alpha^2 - 1)S + \frac{1}{24}(Z_\alpha^3 - 3Z_\alpha)K - \frac{1}{36}(2Z_\alpha^3 - 5Z_\alpha)S^2 \]
\[ VaR_{CF}(1, \alpha) = - (\mu - Z_{CF} \cdot \sigma_d) \]

### Riscalamento Temporale $\sqrt{T}$
I valori di VaR giornalieri vengono proiettati su un orizzonte di $T$ giorni tramite la regola della radice del tempo:
\[ VaR(T, \alpha) = VaR(1, \alpha) \times \sqrt{T} \]

### Conditional VaR (CVaR / Expected Shortfall)
Misura la perdita media attesa nell'ipotesi in cui la perdita superi la soglia del VaR:
\[ CVaR(1, \alpha) = - E[R_t \mid R_t \le -VaR(1, \alpha)] \]

---

## 4. Validazione VaR (Backtesting & Kupiec POF Test)

Per verificare l'accuratezza predittiva dei modelli VaR, il sistema esegue un backtest sui rendimenti effettivi degli ultimi 252 giorni di negoziazione:

1. **Eccezioni (Breaches)**: Si contano i giorni $t$ in cui $R_t < -VaR_t(1, \alpha)$.
2. **Kupiec Proportion of Failures (POF) Test**: Test del rapporto di verosimiglianza basato su distribuzione binomiale:
   \[ LR_{POF} = -2 \ln \left[ \frac{(1-\alpha)^{N-x} \alpha^x}{\left(1-\frac{x}{N}\right)^{N-x} \left(\frac{x}{N}\right)^x} \right] \sim \chi^2(1) \]
3. **Semaforo di Basilea**:
   - 🟢 **Zona Verde**: Eccezioni comprese nei limiti statistici ($x \le \text{Attesa}$). Modello affidabile.
   - 🟡 **Zona Gialla**: Lieve sottostima del rischio ($\text{Attesa} < x \le 1.5 \times \text{Attesa}$).
   - 🔴 **Zona Rossa**: Gravi violazioni ($x > 1.5 \times \text{Attesa}$). Sottostima del rischio di coda.

---

## 5. Style Analysis Fama-French (Modello a 3 Fattori)

Scompone l'Alpha e l'impronta di rischio del portafoglio sui tre fattori accademici premio Nobel tramite regressione multivariata:

\[ R_p - R_f = \alpha_{FF} + \beta_{Mkt} (R_b - R_f) + s \cdot SMB + h \cdot HML + \epsilon \]

- **$\alpha_{FF}$**: Extra-rendimento annuo puro depurato dallo stile di investimento.
- **$\beta_{Mkt}$**: Sensibilità sistemica alle fluttuazioni del mercato azionario.
- **$s$ (Size SMB Tilt)**: Inclinazione verso titoli *Small Cap* ($s > 0$) o *Large Cap* ($s < 0$).
- **$h$ (Value HML Tilt)**: Inclinazione verso titoli *Value* ($h > 0$) o *Growth* ($h < 0$).

---

## 6. Stress Test e Simulazioni Predittive

### 1. MSCI Barra Multi-Scenario Matrix
Misura il calo stimato in € e % del portafoglio simulando la rievocazione di 5 grandi shock storici:
- **Dot-Com Crash (2000)**
- **Lehman Brothers (2008)**
- **US Credit Downgrade (2011)**
- **COVID-19 Crash (Marzo 2020)**
- **Rate Shock (2022)**

Per i titoli privi di storico nel periodo della crisi, il motore applica un fallback basato sulla sensibilità Beta corrente verso il benchmark.

### 2. Custom What-If Beta Shock Simulator
Simula l'impatto di uno shock arbitrario del benchmark $\Delta R_b \in [-50\%, +30\%]$:
\[ \Delta R_i = \beta_i \times \Delta R_b \]
\[ \text{Perdita Stimata Asset } i (€) = \text{Valore Attuale}_i \times \Delta R_i \]

### 3. Simulazione Monte Carlo Multi-Asset (Decomposizione di Cholesky & Student-t)
Genera fino a 10.000 cammini casuali del valore complessivo di portafoglio su 252–756 giorni futuri:
1. Si calcola la matrice di covarianza storica $\Sigma$.
2. Si applica la **Decomposizione di Cholesky** per ottenere la matrice triangolare inferiore $L$ tale che $\Sigma = L \cdot L^T$.
3. Per ogni passo temporale, si generano rendimenti casuali correlati con supporto opzionale per code grasse (distribuzione Student-t con $\nu=5$):
   \[ Z \sim \sqrt{\frac{\nu-2}{\nu}} \times t_{\nu}(0, 1), \quad R_{\text{sim}} = \mu + L \cdot Z \]
4. Evoluzione del prezzo via Moto Browniano Geometrico:
   \[ P_t = P_0 \cdot \exp\left( \sum_{k=1}^t R_{k, \text{sim}} \right) \]

---

## 7. Ottimizzazione di Markowitz & Ledoit-Wolf Shrinkage

### Ledoit-Wolf Shrinkage
Per stabilizzare la stima della matrice di covarianza contro il rumore campionario, si contrae la covarianza campionaria $S$ verso una matrice bersaglio a singolo fattore $F$:
\[ \Sigma_{LW} = (1 - \delta) S + \delta F, \quad \delta \in [0, 1] \]

### Ottimizzazione Vincolata SciPy SLSQP
- **Max Sharpe Ratio**: $\max_w \frac{w^T \mu - R_f}{\sqrt{w^T \Sigma_{LW} w}} \quad \text{s.t. } \sum w_i = 1, w_i \ge 0$
- **Min Volatility**: $\min_w w^T \Sigma_{LW} w \quad \text{s.t. } \sum w_i = 1, w_i \ge 0$

### Ordini di Ribilanciamento
Per ogni asset $i$, le quote da negoziare per raggiungere il peso ottimale $w_{i, \text{ott}}$ sono:
\[ \Delta Q_i = \frac{V_{\text{totale}} \cdot w_{i, \text{ott}} - V_{i, \text{attuale}}}{P_{i, \text{corrente}}} \]

---

## 8. Ulcer Index, Rischio Liquidità & Concentrazione

### Ulcer Index (UI) & Recovery Analysis
Misura la severità dello stress psicologico dell'investitore penalizzando quadraticamente sia la profondità che la durata dei cali sotto l'High-Water Mark:
\[ UI = \sqrt{\frac{1}{N} \sum_{t=1}^N D_t^2}, \quad D_t = \frac{P_t - \max_{\tau \le t} P_\tau}{\max_{\tau \le t} P_\tau} \times 100 \]

### Rischio Liquidità (Giorni alla Liquidazione ADV)
Stima il tempo necessario a smobilizzare una posizione senza causare market impact:
\[ \text{Giorni alla Liquidazione} = \frac{\text{Quantità Posizione}}{0.15 \times \text{ADV}_{90g}} \]

### Concentrazione & Diversificazione
- **Herfindahl-Hirschman Index (HHI)**: $HHI = \sum_{i=1}^M w_i^2$
- **N Asset Effettivi**: $N_{\text{eff}} = \frac{1}{HHI}$
- **Diversification Ratio (DR)**: $DR = \frac{\sum w_i \sigma_i}{\sigma_p}$

---

## 9. ARGUS Quant Advisor & Health Score Engine (`core/advisor.py`)

Il modulo di diagnostica analizza il portafoglio alla ricerca di vulnerabilità o opportunità quantitative calcolando uno **Health Score (0-100)**:

1. **Punteggio Base**: Inizia da $100$.
2. **Penalizzazioni**:
   - **Alta Concentrazione ($HHI > 0.25$ o Top 3 Asset $> 50\%$)**: $-15$ punti.
   - **Contributo sproporzionato al Rischio ($\text{Component VaR}_i > 25\%$)**: $-15$ punti (calcolato solo sui titoli attivi $q_i > 0$).
   - **Multipli P/E Elevati ($P/E > 45x$)**: Segnalazione d'alert per titoli ad alta valutazione fondamentale.
   - **Inefficienza di Sharpe ($\Delta \text{Sharpe} > 0.30$)**: $-10$ punti quando l'ottimizzatore Markowitz individua un guadagno significativo di rendimento corretto per il rischio.
   - **Aggressività Sistemica ($\beta > 1.3$)**: Alert per elevata sensibilità al mercato.

---

## 10. Smart Rebalancer Engine & Generatore Ordini (`core/rebalancer.py`)

Simula le transazioni esatte necessarie per portare il portafoglio dalla composizione attuale a quella target (*Max Sharpe*, *Min Volatility*, *Equal Weight*, *Custom*):

1. **Patrimonio Target**: $V_{\text{target}} = V_{\text{attuale}} + \text{Cash}_{\text{deposit/withdraw}}$
2. **Quota Teorica**: $Q_{i, \text{raw}} = \frac{V_{\text{target}} \cdot w_{i, \text{target}}}{P_{i, \text{ultimo}}}$
3. **Arrotondamento ad Azioni Intere**: $Q_{i, \text{int}} = \text{round}(Q_{i, \text{raw}})$
4. **Valore Ordine**: $\text{Controvalore}_i = (Q_{i, \text{int}} - Q_{i, \text{attuale}}) \cdot P_{i, \text{ultimo}}$
5. **Buffer Liquidità Residua**: $\text{Cash Residuo} = V_{\text{target}} - \sum Q_{i, \text{int}} \cdot P_{i, \text{ultimo}}$

---

## 11. Dividendi & Proiezione Flussi di Cassa (`core/dividend_engine.py`)

1. **Tasso Dividend Yield (%)**: I tassi $DY_i$ memorizzati a database come valori percentuali (es. $6.05\%$, $0.26\%$) vengono divisi per $100$ per ottenere il fattore decimale di calcolo ($dy_i = DY_i / 100$).
2. **Flusso Annuo Stimato**: $\text{Dividendo Annuo}_i = V_{i, \text{attuale}} \cdot dy_i$
3. **Yield Medio di Portafoglio**: $\text{Yield}_p = \frac{\sum \text{Dividendo Annuo}_i}{V_{\text{portafoglio}}} \times 100$
4. **Dividendi Storici Reali Incassati**: Somma algebrica del PnL reale registrato nelle transazioni storiche di tipo `dividend`.
5. **Calendario Mensile per Azienda**: Scomposizione delle scadenze di stacco sui mesi reali di pagamento delle singole società ($m \in [1..12]$) per calcolare la massa di incasso mensile e l'elenco dei titoli pagatori.

---

## 12. Analisi Temporale Multi-Snapshot (`core/db_exporter.py`)

Consente il tracciamento della serie storica degli snapshot salvati a Data Warehouse MySQL/SQLite (`portfolio_snapshots` e `snapshot_positions`):

1. **Serie Temporale Metriche**: Recupero ordinato per data di $V_t$, $PnL_t$, $\text{Sharpe}_t$, $\text{Sortino}_t$, $VaR_{95, t}$, $MaxDD_t$.
2. **Confronto Affiancato (Snapshot A vs Snapshot B)**:
   - $\Delta V = V_B - V_A$
   - $\Delta PnL = PnL_B - PnL_A$
   - $\Delta \text{Sharpe} = \text{Sharpe}_B - \text{Sharpe}_A$
   - Variazione pesi e quote a livello di singolo ticker: $\Delta w_i = w_{i, B} - w_{i, A}$.

---

## 13. Simulatore di Copertura & Hedging Tattico (`core/hedging.py`)

1. **Valore Copertura Beta-Neutral**:
   Per ridurre o azzerare la sensibilità sistemica ($\beta_{\text{target}}$):
   \[ \Delta \beta = \beta_p - \beta_{\text{target}} \]
   \[ H = - \frac{\Delta \beta \cdot V_{\text{portafoglio}}}{|\text{Beta}_{\text{strumento}}|} \]
2. **Numero di Quote dell'ETF Inverso**:
   \[ N_{\text{quote}} = \text{round}\left( \frac{|H|}{P_{\text{etf\_inverso}}} \right) \]
3. **Protezione Tail Risk ($\text{VaR}_{99\text{\%}}$)**:
   \[ \text{Copertura Coda} (€) = V_{\text{portafoglio}} \cdot \text{VaR}_{99\text{\%}, \text{storico}} \]

---

## 14. Attribuzione delle Performance Brinson-Fachler (`core/attribution.py`)

Scompone l'extra-rendimento di portafoglio rispetto al benchmark nei 3 fattori:

1. **Allocation Effect (Effetto Allocazione Settoriale)**:
   \[ A_i = (w_i^p - w_i^b) \cdot (R_i^b - R^b) \]
2. **Selection Effect (Effetto Selezione Titoli)**:
   \[ S_i = w_i^b \cdot (R_i^p - R_i^b) \]
3. **Interaction Effect (Effetto Interazione)**:
   \[ I_i = (w_i^p - w_i^b) \cdot (R_i^p - R_i^b) \]
4. **Extra-Rendimento Totale**:
   \[ R^p - R^b = \sum_{i} (A_i + S_i + I_i) \]

---

## 15. Controllo Limiti di Rischio & Early Warning Engine (`core/risk_limits.py`)

Monitora in tempo reale 6 regole di rischio istituzionali:

1. **Peso Max Singola Posizione**: $\max w_i \le 20\text{\%}$
2. **Concentrazione Settoriale**: $\max \sum_{i \in \text{Settore}_k} w_i \le 35\text{\%}$
3. **Value at Risk Max**: $\text{VaR}_{95\text{\%}} \le 3.00\text{\%}$
4. **Beta Sistemico Max**: $\beta_p \le 1.25$
5. **Diversification Ratio Min**: $DR = \frac{\sum w_i \sigma_i}{\sigma_p} \ge 1.20$
6. **Indice HHI Max**: $HHI = \sum w_i^2 \le 0.25$

Classificazione a semaforo:
- 🟢 **PASS**: Parametro entro i limiti di tolleranza.
- 🟡 **WARNING**: Parametro entro il 15% dal superamento della soglia.
- 🔴 **BREACH**: Soglia regolamentare superata.

---

## 16. Ottimizzazione Fiscale & Normativa Italiana (TUIR Art. 67) (`core/tax_engine.py`)

1. **Aliquote d'Imposta**:
   - Titoli di Stato White List (BTP, BOT, Treasury): Aliquota agevolata **12.5%**.
   - Azioni, ETF, Criptovalute, Obbligazioni Societarie: Aliquota ordinaria **26.0%**.

2. **Qualificazione Fiscale delle Plusvalenze (TUIR Art. 67)**:
   - **Azioni, Obbligazioni, ETC, ETN, Derivati**: Generano *Redditi Diversi*. Le plusvalenze di questa categoria **possono essere compensate** con le minusvalenze pregresse nello zainetto fiscale (valida 4 anni).
   - **ETF**: Generano *Redditi di Capitale*. Le plusvalenze da ETF **NON possono essere utilizzate per abbattere le minusvalenze** presenti nello zainetto fiscale.

3. **Tax-Loss Harvesting Strategy**:
   - Identifica le posizioni in perdita latente su singoli titoli (*Redditi Diversi*) che possono essere liquidate strategicamente prima della fine dell'anno fiscale per azzerare l'imposta dovuta sulle plusvalenze realizzate nello stesso anno solare.

---

## 17. Analisi dei Bilanci, Solvibilità & Comparativa Multiaziendale (`core/financial_analysis.py`)

### 1. Altman Z-Score Model (Original 1968)
Stima la probabilità di insolvenza/bancarotta aziendale su un orizzonte di 24 mesi tramite combinazione lineare di 5 indici patrimoniali e reddituali:
\[ Z = 1.2 X_1 + 1.4 X_2 + 3.3 X_3 + 0.6 X_4 + 0.999 X_5 \]
- $X_1 = \frac{\text{Working Capital}}{\text{Total Assets}}$ (Indice di liquidità operativa)
- $X_2 = \frac{\text{Retained Earnings}}{\text{Total Assets}}$ (Redditività cumulativa reinvestita)
- $X_3 = \frac{\text{EBIT}}{\text{Total Assets}}$ (Produttività dell'attivo aziendale)
- $X_4 = \frac{\text{Market Value of Equity}}{\text{Total Liabilities}}$ (Struttura di leva e copertura dei debiti)
- $X_5 = \frac{\text{Sales}}{\text{Total Assets}}$ (Efficienza di rotazione dell'attivo)

Zone di rischio:
- 🟢 **Safe Zone ($Z > 2.99$)**: Solvibilità elevata e bilancio equilibrato.
- 🟡 **Grey Zone ($1.81 \le Z \le 2.99$)**: Zona di moderata attenzione.
- 🔴 **Distress Zone ($Z < 1.81$)**: Rischio elevato di tensione finanziaria o insolvenza.

### 2. Scomposizione DuPont (3-Factor & 5-Factor Models)
Scompone il Return on Equity (ROE) nei suoi driver costitutivi:
- **DuPont 3 Fattori**:
  \[ ROE = \frac{\text{Net Income}}{\text{Sales}} \times \frac{\text{Sales}}{\text{Total Assets}} \times \frac{\text{Total Assets}}{\text{Total Equity}} = \text{Profit Margin} \times \text{Asset Turnover} \times \text{Equity Multiplier} \]
- **DuPont 5 Fattori**:
  \[ ROE = \frac{\text{Net Income}}{\text{EBT}} \times \frac{\text{EBT}}{\text{EBIT}} \times \frac{\text{EBIT}}{\text{Sales}} \times \frac{\text{Sales}}{\text{Assets}} \times \frac{\text{Assets}}{\text{Equity}} \]

### 3. Consultazione Bilanci Ufficiali 10-K (`fetch_detailed_financial_statements`)
Download ed esplorazione dei rendiconti contabili di esercizio da Yahoo Finance:
- **Conto Economico (Income Statement)**
- **Stato Patrimoniale (Balance Sheet)**
- **Rendiconto Finanziario (Cash Flow Statement)**
Formattazione automatica in Milioni (**M €**) con gestione dei separatori delle migliaia e trattino `—` per le voci non disponibili.

### 4. Engine di Comparativa Multiaziendale (`compare_multiple_companies`)
Permette il confronto affiancato di due o più aziende (del portafoglio o del mercato globale):
- **Grafico a barre & Tabella Altman Z-Score**: Confronto visivo della solvibilità con soglie $Z=1.81$ e $Z=2.99$.
- **Tabella Driver DuPont**: Confronto di Profit Margin %, Asset Turnover, Equity Multiplier e ROE Resultante %.
- **Overlaid Radar Chart degli Indici Fondamentali**: Confronto visivo multi-traccia per Liquidità, Solvibilità e Margini.
- **Matrice degli Indici Fondamentali**: Matrice comparativa per Current/Quick Ratio, Debt/Equity, Interest Coverage, Net Margin % ed EBITDA Margin %.

---

## 18. Modello di Valutazione Intrinseca DCF Monte Carlo (`compute_dcf_monte_carlo_valuation`)

### 1. Attualizzazione Flussi di Cassa Liberi (2-Stage DCF)
Modello fondamentale di finanza aziendale che calcola l'Enterprise Value ($EV$) ed il Fair Value intrinseco per azione attualizzando i Flussi di Cassa Liberi ($FCF$) ed il Valore Terminale ($TV$):
\[ PV(FCF) = \sum_{t=1}^{5} \frac{FCF_0 \cdot (1 + g)^t}{(1 + WACC)^t} \]
\[ TV = \frac{FCF_5 \cdot (1 + g_{\text{terminal}})}{WACC - g_{\text{terminal}}} \]
\[ PV(TV) = \frac{TV}{(1 + WACC)^5} \]
\[ \text{Enterprise Value} = PV(FCF) + PV(TV) \]
\[ \text{Equity Value} = \text{Enterprise Value} + \text{Cassa Netta} - \text{Debito Totale} \]
\[ \text{Fair Value per Azione} = \frac{\text{Equity Value}}{\text{Azioni Totali Diluite}} \]

### 2. Simulazione Stocastica Monte Carlo (1,000 Iterazioni)
Campiona simultaneamente il tasso di crescita del fatturato $g \sim \mathcal{N}(\mu_g, \sigma_g)$, il costo del capitale $WACC \sim \mathcal{N}(\mu_w, \sigma_w)$ ed il tasso di crescita terminale $g_{\text{term}} \sim \mathcal{N}(\mu_{tg}, \sigma_{tg})$ per ricavare la distribuzione completa del Fair Value e calcolare la percentuale di probabilità di sottovalutazione:
\[ \text{Probabilità Sottovalutazione \%} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(\text{Fair Value}_i > \text{Prezzo Attuale}) \times 100 \]

---

## 19. Diagnostica Avanzata: Piotroski F-Score, WACC & Multipli di Mercato

### 1. Piotroski F-Score (Joseph Piotroski — Stanford University)
Punteggio sintetico di salute finanziaria contabile basato su 9 segnali binari:
- **Profittabilità (4 punti)**: Utile Netto > 0 (+1), Cash Flow Operativo > 0 (+1), Crescita ROA (+1), Qualità degli Utili ($\text{OCF} > \text{Utile Netto}$) (+1).
- **Struttura Finanziaria & Liquidità (3 punti)**: Riduzione del Debito a Lungo Termine (+1), Miglioramento del Current Ratio (+1), Assenza di Diluizione Azionaria (+1).
- **Efficienza Operativa (2 punti)**: Espansione del Margine Lordo (+1), Miglioramento dell'Asset Turnover (+1).

Fasce di valutazione:
- 🟢 **High F-Score (8 - 9)**: Eccellente salute finanziaria e solidità contabile.
- 🟡 **Mid F-Score (5 - 7)**: Struttura contabile stabile e moderata.
- 🔴 **Low F-Score (0 - 4)**: Elevato rischio di stress o debolezza finanziaria.

### 2. Stima Dinamica del WACC (Weighted Average Cost of Capital)
Calcolo dinamico del costo medio del capitale aziendale tramite modello CAPM:
- **Costo dell'Equity ($r_e$)**: $r_e = R_f + \beta \cdot \text{ERP}$
- **Costo del Debito al netto delle imposte ($r_{d,\text{net}}$)**: $r_{d,\text{raw}} \cdot (1 - t_{\text{eff}})$, dove $t_{\text{eff}} = \frac{\text{Imposte}}{\text{Utile ante Imposte}}$.
- **Pesi Strutturali**: $w_e = \frac{\text{Market Cap}}{\text{Market Cap} + \text{Debito}}$, $w_d = \frac{\text{Debito}}{\text{Market Cap} + \text{Debito}}$.
- **$\text{WACC}$**: $w_e \cdot r_e + w_d \cdot r_{d,\text{net}}$.

### 3. Matrice dei Multipli di Mercato Benchmark
Estrazione ed analisi comparativa in tempo reale dei multipli ufficiali di valutazione (*P/E Trailing*, *Forward P/E*, *PEG Ratio*, *EV/EBITDA*, *EV/Sales*, *P/B*, *P/S*) con verdetto a semaforo rispetto ai range target di fair value.

---

## 20. ATR Trailing Stop-Loss & Chandelier Exit Manager (`compute_atr_chandelier_exits`)

### 1. True Range (TR) & Average True Range ($ATR_{14}$)
L'Average True Range misura la volatilità fisiologica reale di ciascun asset tenendo conto anche dei gap di apertura:
\[ TR_t = \max \left( H_t - L_t, \, |H_t - C_{t-1}|, \, |L_t - C_{t-1}| \right) \]
\[ ATR_{14,t} = \frac{1}{14} \sum_{k=0}^{13} TR_{t-k} \]

### 2. Chandelier Exit Level ($3 \times ATR_{14}$)
Stop-loss dinamico agganciato al massimo più alto degli ultimi 22 giorni lavorativi ($H_{22}$), sottratto di 3 volte la volatilità media reale:
\[ \text{Chandelier Exit}_t = \max_{k=0..21}(H_{t-k}) - 3 \times ATR_{14,t} \]

### 3. Distanza Percentuale & Alert Condition
\[ \text{Distanza Stop \%} = \frac{P_{\text{mkt}} - \text{Chandelier Exit}_t}{P_{\text{mkt}}} \times 100 \]
\[ \text{Alert Status} = \begin{cases} \text{🔴 TRIGGER}, & \text{se } P_{\text{mkt}} \le \text{Chandelier Exit}_t \\ \text{🟢 REGOLARE}, & \text{se } P_{\text{mkt}} > \text{Chandelier Exit}_t \end{cases} \]

---

## 21. Impatto di Mercato & Costi di Liquidazione Almgren-Chriss (`compute_almgren_chriss_market_impact`)

### 1. Scomposizione dell'Impatto sui Prezzi (Almgren & Chriss, 2000)
Modello istituzionale per la stima dello slippage e dei costi di esecuzione durante la smobilizzazione o il bilanciamento di posizioni azionarie:
- **Impatto Permanente ($I_{\text{perm}}$)**: Spostamento strutturale del prezzo di equilibrio dovuto alla pressione informativa dell'ordine:
  \[ I_{\text{perm}} = \gamma \cdot \left( \frac{\text{Volume Operativo}}{ADV} \right) \cdot P_{\text{attuale}} \]
- **Impatto Temporaneo ($I_{\text{temp}}$)**: Pressione immediata sul book di negoziazione che si riassorbe nel tempo:
  \[ I_{\text{temp}} = \eta \cdot \sqrt{\frac{\text{Volume Operativo}}{ADV \cdot T_{\text{ore}}}} \cdot P_{\text{attuale}} \]

### 2. Slippage Stimato % & Impatto Monetario (€)
\[ \text{Slippage Stimato \%} = \frac{I_{\text{perm}} + I_{\text{temp}}}{P_{\text{attuale}}} \times 100 \]
\[ \text{Impatto Monetario Totale (€)} = \text{Quote Scambiate} \times (I_{\text{perm}} + I_{\text{temp}}) \]

---

## 22. Visualizzatore 3D della Superficie di Rischio (`compute_3d_stress_surface`)

### 1. Griglia Bivariata Tassi vs Volatilità
Modellizzazione della superficie di PnL su una griglia bivariata $X \times Y$:
- **Asse $X$ (Tassi $\Delta r$)**: Varie variazioni dei tassi da $-200\,\text{bps}$ a $+200\,\text{bps}$ (sensibilità duration $-4.5$).
- **Asse $Y$ (Volatilità $\Delta \sigma$)**: Varie variazioni della volatilità da $-30\%$ a $+50\%$ (sensibilità vega/equity $-0.35$).
- **Matrice $Z_{i,j}$ (Impatto PnL €)**:
  \[ Z_{i,j} = \text{Capitale Totale} \times \left( \frac{\Delta r_j}{10000} \cdot (-4.5) + \frac{\Delta \sigma_i}{100} \cdot (-0.35) \right) \]

---

## 23. Modello Macro-Fattoriale MSCI Barra a 5 Fattori Ortogonalizzati (`compute_msci_barra_multifactor_model`)

### 1. Equazione di Ortogonalizzazione dei Fattori (Gram-Schmidt OLS)
Per prevenire la multicollinearità ed isolare le reali esposizioni pure ai fattori di stile, ciascun fattore grezzo viene proiettato ed ortogonalizzato rispetto al fattore di mercato $F_{\text{MKT}}$:
\[ F_{\text{SMB}} = \text{SMB}_{\text{raw}} - \frac{\text{cov}(\text{SMB}_{\text{raw}}, F_{\text{MKT}})}{\text{var}(F_{\text{MKT}})} F_{\text{MKT}} \]
\[ F_{\text{HML}} = \text{HML}_{\text{raw}} - \frac{\text{cov}(\text{HML}_{\text{raw}}, F_{\text{MKT}})}{\text{var}(F_{\text{MKT}})} F_{\text{MKT}} \]
\[ F_{\text{WML}} = \text{WML}_{\text{raw}} - \frac{\text{cov}(\text{WML}_{\text{raw}}, F_{\text{MKT}})}{\text{var}(F_{\text{MKT}})} F_{\text{MKT}} \]
\[ F_{\text{TERM}} = \text{TERM}_{\text{raw}} - \frac{\text{cov}(\text{TERM}_{\text{raw}}, F_{\text{MKT}})}{\text{var}(F_{\text{MKT}})} F_{\text{MKT}} \]

### 2. Equazione di Regressione Multivariata OLS
Esposizione del rendimento in eccesso del portafoglio ai 5 fattori macro/di stile ortogonali:
\[ R_{p,t} - R_{f,t} = \alpha + \beta_{\text{MKT}} F_{\text{MKT},t} + \beta_{\text{SMB}} F_{\text{SMB},t} + \beta_{\text{HML}} F_{\text{HML},t} + \beta_{\text{WML}} F_{\text{WML},t} + \beta_{\text{TERM}} F_{\text{TERM},t} + \epsilon_t \]

### 3. Decomposizione della Varianza & Statistica $t$
- **Rischio Sistemico Fattoriale \%**: $R^2 \times 100$
- **Rischio Specifico Residuo \%**: $(1 - R^2) \times 100$
- **Statistica $t$ dei Betas**:
  \[ t_{\beta_k} = \frac{\hat{\beta}_k}{\text{SE}(\hat{\beta}_k)}, \quad \text{SE}(\hat{\beta}_k) = \sqrt{\hat{\sigma}_{\epsilon}^2 (X^T X)^{-1}_{kk}} \]
  Valori di $|t_{\beta_k}| \ge 1.96$ indicano un'esposizione statisticamente significativa al livello di confidenza del 95% (`🟢 Significativo`).

---

## 25. Simulatore Stocastico Merton Jump-Diffusion (`compute_merton_jump_diffusion_simulation`)

### 1. Processo Stocastico Bivariato Diffusione + Salto Poissoniano
Modellizzazione non-gaussiana dei rendimenti per la misurazione del *Tail Risk* e delle *Fat Tails* durante crolli finanziari improvvisi:
\[ dS_t = \mu S_t dt + \sigma S_t dW_t + (e^{Y_t} - 1) S_t dN_t \]

Dove:
- $dW_t \sim \mathcal{N}(0, dt)$: Moto Browniano standard per la diffusione continua.
- $N_t \sim \text{Poisson}(\lambda dt)$: Processo di conteggio di Poisson con intensità di salto $\lambda$ (salti/anno).
- $Y_i \sim \mathcal{N}(\mu_J, \sigma_J^2)$: Dimensione logaritmica casuale dello shock di prezzo.
- $k = \mathbb{E}[e^Y - 1] = e^{\mu_J + \frac{1}{2}\sigma_J^2} - 1$: Fattore di compensazione dell'aspettativa di salto.

### 2. Valutazione del Tail Risk (Jump VaR 99% vs Gaussiano)
Il VaR ed il CVaR a confidenza 99% integrano gli shock Poissoniani per evitare la sottostima sistematica del rischio catastrofico tipica della curva normale.

---

## 26. Rilevatore di Anomalie ML Isolation Forest (`detect_portfolio_anomalies_isolation_forest`)

### 1. Algoritmo di Isolamento Non Supervisionato
Algoritmo basato su una foresta di alberi decisionali casuali ($N=100$) che misura il numero di partizioni (profondità dell'albero $h(x)$) necessarie per isolare un'osservazione $x$:
\[ s(x, n) = 2^{-\frac{\mathbb{E}(h(x))}{c(n)}} \]
Dove $c(n)$ è la lunghezza media dei cammini negli alberi binari di ricerca per $n$ campioni. Valori di $s(x,n) \approx 1$ indicano anomalie marcate (giornate di panico o picchi di correlazione).

### 2. Vettore Multidimensionale delle Feature
- Rendimento giornaliero di portafoglio $R_{p,t}$
- Volatilità rolling a 20 giorni $\sigma_{20d}$
- Correlazione media di coppia tra tutti gli asset $\bar{\rho}_{20d}$
- Drawdown cumulato $DD_t$
