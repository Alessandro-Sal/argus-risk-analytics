# Calcolo delle Metriche di Rischio, Modelli Econometrici e Valutazione Aziendale

Questo documento illustra la metodologia, la formulazione matematica e le applicazioni pratiche adottate all'interno del motore quantitativo (`core/risk_engine.py`, `core/financial_analysis.py`, `core/tax_engine.py`, `core/attribution.py`, `core/risk_limits.py`, `core/garch_fhs_engine.py`, `core/volatility_surface.py`, `core/crypto_tax_engine.py`, `core/factor_library.py`, `core/sec_rag_engine.py`, `core/duckdb_engine.py`, `core/yield_curve.py`, `core/streaming_engine.py`, `core/screener_engine.py`, `core/bquant_engine.py`, `core/workspace_engine.py`, `core/excel_connector.py`) di **ARGUS Risk Analytics Platform v5.18.0**. Tutti i calcoli basati su serie storiche considerano i rendimenti giornalieri rettificati (*Adjusted Close*) ed un anno lavorativo standard di 252 giorni di negoziazione.

---

## 1. Motore Contabile FIFO (First-In, First-Out)

Per determinare accuratamente il costo di carico e i profitti/perdite realizzati su portafogli con acquisti e vendite frazionate nel tempo, il sistema implementa un **motore a code FIFO (`_fifo_engine`)**:

1. **Gestione Acquisti**: Ogni operazione di acquisto (`buy`) aggiunge un lotto $(q_i, p_i)$ alla coda FIFO dell'asset.
2. **Gestione Vendite**: Ogni operazione di vendita (`sell`) consuma le quote a partire dai lotti più vecchi nella coda:
   

$$
\text{PnL Realizzato} = \sum_{k} q_{\text{venduti}, k} \cdot (p_{\text{vendita}} - p_{\text{acquisto}, k}) - \text{Commissioni}
$$

3. **Prezzo Medio di Carico Residuo (Weighted Average Cost Basis - WACP)**:
   

$$
\text{WACP} = \frac{\sum_{m} q_{\text{residuo}, m} \cdot p_{\text{acquisto}, m}}{\sum_{m} q_{\text{residuo}, m}}
$$

4. **Dividendi**: I dividendi storici incassati vengono sommati direttamente per determinare il PnL totale effettivo.

---

## 2. Metriche di Rischio di Mercato e Tail Risk

### Volatilità Annualizzata
Misura la dispersione dei rendimenti del portafoglio attorno alla loro media:
- **Volatilità Giornaliera**:

$$
\sigma_d = \sqrt{\frac{1}{N-1} \sum_{t=1}^N (R_t - \bar{R})^2}
$$

- **Volatilità Annualizzata**:

$$
\sigma_a = \sigma_d \times \sqrt{252}
$$

### Asimmetria (Skewness)
Misura la simmetria della distribuzione dei rendimenti attorno alla media:

$$
S = \frac{\frac{1}{N} \sum_{t=1}^N (R_t - \bar{R})^3}{\sigma_d^3}
$$

- $S < 0$: Coda sinistra pronunciata (maggiore probabilità di perdite estreme).
- $S > 0$: Coda destra pronunciata.

### Curtosi (Kurtosis / Fat Tails)
Misura la pesantezza delle code della distribuzione rispetto a una distribuzione gaussiana normale:

$$
K = \frac{\frac{1}{N} \sum_{t=1}^N (R_t - \bar{R})^4}{\sigma_d^4} - 3
$$

- $K > 0$: Presenza di code spesse (*fat tails*), ovvero eventi estremi più frequenti rispetto alla normale.

### Tracking Error
Misura la deviazione standard del rendimento attivo rispetto al benchmark ($R_b$):

$$
TE = \sqrt{\frac{1}{N-1} \sum_{t=1}^N \left( (R_t - R_{b,t}) - \overline{(R - R_b)} \right)^2} \times \sqrt{252}
$$

### Massimo Drawdown (Max Drawdown) & High-Water Mark
Il **Max Drawdown** misura la peggiore perdita percentuale di capitale subita tra un picco massimo storico relativo (*High-Water Mark*, $\text{HWM}_t$) e il minimo successivo (*Trough*), prima del raggiungimento di un nuovo massimo:

$$
\text{HWM}_t = \max_{s \le t} V_s
$$

$$
\text{Drawdown}_t = \frac{V_t - \text{HWM}_t}{\text{HWM}_t}
$$

$$
\text{Max Drawdown} = \min_{t} \text{Drawdown}_t
$$

#### Dimostrazione Algebrica: Perché il Drawdown non è la sottrazione sull'asse Y del Rendimento Cumulato
Sia $V_0$ il capitale iniziale e:

$$
V_t = V_0 \prod_{i=1}^t (1 + R_i)
$$

il valore del portafoglio. Il rendimento cumulato indicizzato a base zero è:

$$
\text{CumRet}_t = \frac{V_t - V_0}{V_0}
$$

La differenza aritmetica tra il picco e il minimo successivo osservata sull'asse delle ordinate (in punti percentuali) è:

$$
\Delta_{\text{asse } Y} = \text{CumRet}_{\text{peak}} - \text{CumRet}_{\text{trough}} = \frac{V_{\text{peak}} - V_{\text{trough}}}{V_0}
$$

Il vero **Drawdown Relativo** subito dall'investitore rispetto al picco è invece:

$$
DD = \frac{V_{\text{trough}} - V_{\text{peak}}}{V_{\text{peak}}} = -\frac{V_{\text{peak}} - V_{\text{trough}}}{V_0 \cdot (1 + \text{CumRet}_{\text{peak}})} = -\frac{\Delta_{\text{asse } Y}}{1 + \text{CumRet}_{\text{peak}}}
$$

**Conseguenza Matematica:**
Poiché al picco il rendimento cumulato è positivo ($\text{CumRet}_{\text{peak}} > 0$), il denominatore $(1 + \text{CumRet}_{\text{peak}}) > 1$. Pertanto, il valore assoluto della perdita percentuale effettiva è sistematicamente inferiore alla caduta visiva in punti percentuali sull'asse $Y$:

$$
|DD| = \frac{\Delta_{\text{asse } Y}}{1 + \text{CumRet}_{\text{peak}}} < \Delta_{\text{asse } Y}
$$

*Esempio numerico:* Se il portafoglio raggiunge **+98.4%** e poi cade a **+20.6%**, la discesa visiva sull'asse $Y$ è $\Delta = 98.4 - 20.6 = 77.8\%$. Tuttavia, la perdita reale subita dal patrimonio è:

$$
DD = -\frac{77.8\%}{1 + 0.984} = -\frac{77.8\%}{1.984} = \mathbf{-39.21\%}
$$

### Ulcer Index (UI)
Misura la profondità e la persistenza temporale dei periodi trascorsi sott'acqua (*underwater*), penalizzando quadraticamente i drawdown prolungati:

$$
\text{UI} = \sqrt{\frac{1}{N} \sum_{t=1}^N (\text{Drawdown}_t \times 100)^2}
$$

---

## 3. Value at Risk (VaR) & Conditional VaR (CVaR)

Il Value at Risk stima la massima perdita potenziale in un orizzonte temporale $T$ (da 1 a 20 giorni) ad un livello di confidenza $1 - \alpha$ (90%, 95%, 99%).

### 1. VaR Storico
È il percentile empirico esatto della distribuzione dei rendimenti giornalieri storici:

$$
VaR_{\text{Storico}}(1, \alpha) = - \text{Percentile}(R, \alpha)
$$

### 2. VaR Parametrico (Gaussiano)
Basato sull'assunzione di rendimenti normalmente distribuiti con media $\mu$, deviazione standard $\sigma_d$ e quantile normale standard $Z_\alpha = \Phi^{-1}(\alpha) < 0$ (es. $Z_{0.05} = -1.64485$):

$$
q_{\text{Param}} = \mu + Z_\alpha \cdot \sigma_d
$$

$$
VaR_{\text{Parametrico}}(1, \alpha) = - q_{\text{Param}} = -\mu + |Z_\alpha| \cdot \sigma_d
$$

### 3. VaR Cornish-Fisher (Modello Asimmetrico & Code Spesse)
Incorpora Asimmetria ($S$) e Curtosi ($K$) tramite l'espansione di Cornish-Fisher per correggere la stima in presenza di code non gaussiane:

$$
Z_{CF} = Z_\alpha + \frac{1}{6}(Z_\alpha^2 - 1)S + \frac{1}{24}(Z_\alpha^3 - 3Z_\alpha)K - \frac{1}{36}(2Z_\alpha^3 - 5Z_\alpha)S^2
$$

$$
q_{CF} = \mu + Z_{CF} \cdot \sigma_d
$$

$$
VaR_{CF}(1, \alpha) = - q_{CF} = -\mu + |Z_{CF}| \cdot \sigma_d
$$

### Riscalamento Temporale $\sqrt{T}$
I valori di VaR giornalieri vengono proiettati su un orizzonte di $T$ giorni tramite la regola della radice del tempo:

$$
VaR(T, \alpha) = VaR(1, \alpha) \times \sqrt{T}
$$

### Conditional VaR (CVaR / Expected Shortfall)
Misura la perdita media attesa nell'ipotesi in cui la perdita superi la soglia del VaR:

$$
CVaR(1, \alpha) = - E[R_t \mid R_t \le -VaR(1, \alpha)]
$$

---

## 4. Validazione VaR (Backtesting & Kupiec POF Test)

Per verificare l'accuratezza predittiva dei modelli VaR, il sistema esegue un backtest sui rendimenti effettivi degli ultimi 252 giorni di negoziazione:

1. **Eccezioni (Breaches)**: Si contano i giorni $t$ in cui:

$$
R_t < -VaR_t(1, \alpha)
$$

2. **Kupiec Proportion of Failures (POF) Test**: Test del rapporto di verosimiglianza basato su distribuzione binomiale:
   

$$
LR_{POF} = -2 \ln \left[ \frac{(1-\alpha)^{N-x} \alpha^x}{\left(1-\frac{x}{N}\right)^{N-x} \left(\frac{x}{N}\right)^x} \right] \sim \chi^2(1)
$$

3. **Semaforo di Basilea**:
   - 🟢 **Zona Verde**: Eccezioni comprese nei limiti statistici ($x \le \text{Attesa}$). Modello affidabile.
   - 🟡 **Zona Gialla**: Lieve sottostima del rischio ($\text{Attesa} < x \le 1.5 \times \text{Attesa}$).
   - 🔴 **Zona Rossa**: Gravi violazioni ($x > 1.5 \times \text{Attesa}$). Sottostima del rischio di coda.

---

## 5. Style Analysis Fama-French (Modello a 3 Fattori)

Scompone l'Alpha e l'impronta di rischio del portafoglio sui tre fattori accademici premio Nobel tramite regressione multivariata:

$$
R_p - R_f = \alpha_{FF} + \beta_{Mkt} (R_b - R_f) + s \cdot SMB + h \cdot HML + \epsilon
$$

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

$$
\Delta R_i = \beta_i \times \Delta R_b
$$

$$
\text{Perdita Stimata Asset } i \text{ (EUR)} = \text{Valore Attuale}_i \times \Delta R_i
$$

### 3. Simulazione Monte Carlo Multi-Asset (Decomposizione di Cholesky & Student-t)
Genera fino a 10.000 cammini casuali del valore complessivo di portafoglio su 252–756 giorni futuri:
1. Si calcola la matrice di covarianza storica $\Sigma$.
2. Si applica la **Decomposizione di Cholesky** per ottenere la matrice triangolare inferiore $L$ tale che $\Sigma = L \cdot L^T$.
3. Per ogni passo temporale, si generano rendimenti casuali correlati con supporto opzionale per code grasse (distribuzione Student-t con $\nu=5$):
   

$$
Z \sim \sqrt{\frac{\nu-2}{\nu}} \times t_{\nu}(0, 1), \quad R_{\text{sim}} = \mu + L \cdot Z
$$

4. Evoluzione del prezzo via Moto Browniano Geometrico:
   

$$
P_t = P_0 \cdot \exp\left( \sum_{k=1}^t R_{k, \text{sim}} \right)
$$

---

## 7. Ottimizzazione di Markowitz & Ledoit-Wolf Shrinkage

### Ledoit-Wolf Shrinkage
Per stabilizzare la stima della matrice di covarianza contro il rumore campionario, si contrae la covarianza campionaria $S$ verso una matrice bersaglio a singolo fattore $F$:

$$
\Sigma_{LW} = (1 - \delta) S + \delta F, \quad \delta \in [0, 1]
$$

### Ottimizzazione Vincolata SciPy SLSQP
- **Max Sharpe Ratio**:

$$
\max_w \frac{w^T \mu - R_f}{\sqrt{w^T \Sigma_{LW} w}} \quad \text{s.t. } \sum w_i = 1, w_i \ge 0
$$

- **Min Volatility**:

$$
\min_w w^T \Sigma_{LW} w \quad \text{s.t. } \sum w_i = 1, w_i \ge 0
$$

### Ordini di Ribilanciamento
Per ogni asset $i$, le quote da negoziare per raggiungere il peso ottimale $w_{i, \text{ott}}$ sono:

$$
\Delta Q_i = \frac{V_{\text{totale}} \cdot w_{i, \text{ott}} - V_{i, \text{attuale}}}{P_{i, \text{corrente}}}
$$

---

## 8. Ulcer Index, Rischio Liquidità & Concentrazione

### Ulcer Index (UI) & Recovery Analysis
Misura la severità dello stress psicologico dell'investitore penalizzando quadraticamente sia la profondità che la durata dei cali sotto l'High-Water Mark:

$$
UI = \sqrt{\frac{1}{N} \sum_{t=1}^N D_t^2}, \quad D_t = \frac{P_t - \max_{\tau \le t} P_\tau}{\max_{\tau \le t} P_\tau} \times 100
$$

### Rischio Liquidità (Giorni alla Liquidazione ADV)
Stima il tempo necessario a smobilizzare una posizione senza causare market impact:

$$
\text{Giorni alla Liquidazione} = \frac{\text{Quantità Posizione}}{0.15 \times \text{ADV}_{90g}}
$$

### Concentrazione & Diversificazione
- **Herfindahl-Hirschman Index (HHI)**:

$$
HHI = \sum_{i=1}^M w_i^2
$$

- **N Asset Effettivi**:

$$
N_{\text{eff}} = \frac{1}{HHI}
$$

- **Diversification Ratio (DR)**:

$$
DR = \frac{\sum w_i \sigma_i}{\sigma_p}
$$

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

1. **Patrimonio Target**:

$$
V_{\text{target}} = V_{\text{attuale}} + \text{Cash}_{\text{deposit/withdraw}}
$$

2. **Quota Teorica**:

$$
Q_{i, \text{raw}} = \frac{V_{\text{target}} \cdot w_{i, \text{target}}}{P_{i, \text{ultimo}}}
$$

3. **Arrotondamento ad Azioni Intere**:

$$
Q_{i, \text{int}} = \text{round}(Q_{i, \text{raw}})
$$

4. **Valore Ordine**:

$$
\text{Controvalore}_i = (Q_{i, \text{int}} - Q_{i, \text{attuale}}) \cdot P_{i, \text{ultimo}}
$$

5. **Buffer Liquidità Residua**:

$$
\text{Cash Residuo} = V_{\text{target}} - \sum Q_{i, \text{int}} \cdot P_{i, \text{ultimo}}
$$

---

## 11. Dividendi & Proiezione Flussi di Cassa (`core/dividend_engine.py`)

1. **Tasso Dividend Yield (%)**: I tassi $DY_i$ memorizzati a database come valori percentuali (es. 6.05%, 0.26%) vengono divisi per $100$ per ottenere il fattore decimale di calcolo ($dy_i = DY_i / 100$).
2. **Flusso Annuo Stimato**:

$$
\text{Dividendo Annuo}_i = V_{i, \text{attuale}} \cdot dy_i
$$

3. **Yield Medio di Portafoglio**:

$$
\text{Yield}_p = \frac{\sum \text{Dividendo Annuo}_i}{V_{\text{portafoglio}}} \times 100
$$

4. **Dividendi Storici Reali Incassati**: Somma algebrica del PnL reale registrato nelle transazioni storiche di tipo `dividend`.
5. **Calendario Mensile per Azienda**: Scomposizione delle scadenze di stacco sui mesi reali di pagamento delle singole società ($m \in [1..12]$) per calcolare la massa di incasso mensile e l'elenco dei titoli pagatori.

---

## 12. Analisi Temporale Multi-Snapshot (`core/db_exporter.py`)

Consente il tracciamento della serie storica degli snapshot salvati a Data Warehouse MySQL/SQLite (`portfolio_snapshots` e `snapshot_positions`):

1. **Serie Temporale Metriche**: Recupero ordinato per data di $V_t$, $PnL_t$, $\text{Sharpe}_t$, $\text{Sortino}_t$, $VaR_{95, t}$, $MaxDD_t$.
2. **Confronto Affiancato (Snapshot A vs Snapshot B)**:
   - Variazione Valore:

$$
\Delta V = V_B - V_A
$$

   - Variazione PnL:

$$
\Delta PnL = PnL_B - PnL_A
$$

   - Variazione Sharpe:

$$
\Delta \text{Sharpe} = \text{Sharpe}_B - \text{Sharpe}_A
$$

   - Variazione pesi e quote a livello di singolo ticker:

$$
\Delta w_i = w_{i, B} - w_{i, A}
$$

---

## 13. Simulatore di Copertura & Hedging Tattico (`core/hedging.py`)

1. **Valore Copertura Beta-Neutral**:
   Per ridurre o azzerare la sensibilità sistemica ($\beta_{\text{target}}$):
   

$$
\Delta \beta = \beta_p - \beta_{\text{target}}
$$

   

$$
H = - \frac{\Delta \beta \cdot V_{\text{portafoglio}}}{|\text{Beta}_{\text{strumento}}|}
$$

2. **Numero di Quote dell'ETF Inverso**:
   

$$
N_{\text{quote}} = \text{round}\left( \frac{|H|}{P_{\text{ETF Inverso}}} \right)
$$

3. **Protezione Tail Risk ($\text{VaR}_{99}$)**:
   

$$
\text{Copertura Coda (EUR)} = V_{\text{portafoglio}} \cdot \text{VaR}_{99, \text{storico}}
$$

---

## 14. Attribuzione delle Performance Brinson-Fachler (`core/attribution.py`)

Scompone l'extra-rendimento di portafoglio rispetto al benchmark nei 3 fattori:

1. **Allocation Effect (Effetto Allocazione Settoriale)**:
   

$$
A_i = (w_i^p - w_i^b) \cdot (R_i^b - R^b)
$$

2. **Selection Effect (Effetto Selezione Titoli)**:
   

$$
S_i = w_i^b \cdot (R_i^p - R_i^b)
$$

3. **Interaction Effect (Effetto Interazione)**:
   

$$
I_i = (w_i^p - w_i^b) \cdot (R_i^p - R_i^b)
$$

4. **Extra-Rendimento Totale**:
   

$$
R^p - R^b = \sum_{i} (A_i + S_i + I_i)
$$

---

## 15. Controllo Limiti di Rischio & Early Warning Engine (`core/risk_limits.py`)

Monitora in tempo reale 6 regole di rischio istituzionali:

1. **Peso Max Singola Posizione**:

$$
\max w_i \le 20\%
$$

2. **Concentrazione Settoriale**:

$$
\max \sum_{i \in \text{Settore}_k} w_i \le 35\%
$$

3. **Value at Risk Max**:

$$
\text{VaR}_{95} \le 3.00\%
$$

4. **Beta Sistemico Max**:

$$
\beta_p \le 1.25
$$

5. **Diversification Ratio Min**:

$$
DR = \frac{\sum w_i \sigma_i}{\sigma_p} \ge 1.20
$$

6. **Indice HHI Max**:

$$
HHI = \sum w_i^2 \le 0.25
$$

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

$$
Z = 1.2 X_1 + 1.4 X_2 + 3.3 X_3 + 0.6 X_4 + 0.999 X_5
$$

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
  

$$
ROE = \frac{\text{Net Income}}{\text{Sales}} \times \frac{\text{Sales}}{\text{Total Assets}} \times \frac{\text{Total Assets}}{\text{Total Equity}} = \text{Profit Margin} \times \text{Asset Turnover} \times \text{Equity Multiplier}
$$

- **DuPont 5 Fattori**:
  

$$
ROE = \frac{\text{Net Income}}{\text{EBT}} \times \frac{\text{EBT}}{\text{EBIT}} \times \frac{\text{EBIT}}{\text{Sales}} \times \frac{\text{Sales}}{\text{Assets}} \times \frac{\text{Assets}}{\text{Equity}}
$$

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

$$
PV(FCF) = \sum_{t=1}^{5} \frac{FCF_0 \cdot (1 + g)^t}{(1 + WACC)^t}
$$

$$
TV = \frac{FCF_5 \cdot (1 + g_{\text{terminal}})}{WACC - g_{\text{terminal}}}
$$

$$
PV(TV) = \frac{TV}{(1 + WACC)^5}
$$

$$
\text{Enterprise Value} = PV(FCF) + PV(TV)
$$

$$
\text{Equity Value} = \text{Enterprise Value} + \text{Cassa Netta} - \text{Debito Totale}
$$

$$
\text{Fair Value per Azione} = \frac{\text{Equity Value}}{\text{Azioni Totali Diluite}}
$$

### 2. Simulazione Stocastica Monte Carlo (1,000 Iterazioni)
Campiona simultaneamente il tasso di crescita del fatturato $g \sim \mathcal{N}(\mu_g, \sigma_g)$, il costo del capitale $WACC \sim \mathcal{N}(\mu_w, \sigma_w)$ ed il tasso di crescita terminale $g_{\text{term}} \sim \mathcal{N}(\mu_{tg}, \sigma_{tg})$ per ricavare la distribuzione completa del Fair Value e calcolare la percentuale di probabilità di sottovalutazione:

$$
\text{Probabilità Sottovalutazione (pct)} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(\text{Fair Value}_i > \text{Prezzo Attuale}) \times 100
$$

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
- **Costo dell'Equity ($r_e$)**:

$$
r_e = R_f + \beta \cdot \text{ERP}
$$

- **Costo del Debito al netto delle imposte ($r_{d,\text{net}}$)**: $r_{d,\text{raw}} \cdot (1 - t_{\text{eff}})$, dove $t_{\text{eff}} = \frac{\text{Imposte}}{\text{Utile ante Imposte}}$.
- **Pesi Strutturali**:

$$
w_e = \frac{\text{Market Cap}}{\text{Market Cap} + \text{Debito}}
$$

, $w_d = \frac{\text{Debito}}{\text{Market Cap} + \text{Debito}}$.
- **$\text{WACC}$**: $w_e \cdot r_e + w_d \cdot r_{d,\text{net}}$.

### 3. Matrice dei Multipli di Mercato Benchmark
Estrazione ed analisi comparativa in tempo reale dei multipli ufficiali di valutazione (*P/E Trailing*, *Forward P/E*, *PEG Ratio*, *EV/EBITDA*, *EV/Sales*, *P/B*, *P/S*) con verdetto a semaforo rispetto ai range target di fair value.

---

## 20. ATR Trailing Stop-Loss & Chandelier Exit Manager (`compute_atr_chandelier_exits`)

### 1. True Range (TR) & Average True Range ($ATR_{14}$)
L'Average True Range misura la volatilità fisiologica reale di ciascun asset tenendo conto anche dei gap di apertura:

$$
TR_t = \max \left( H_t - L_t, \, |H_t - C_{t-1}|, \, |L_t - C_{t-1}| \right)
$$

$$
ATR_{14,t} = \frac{1}{14} \sum_{k=0}^{13} TR_{t-k}
$$

### 2. Chandelier Exit Level ($3 \times ATR_{14}$)
Stop-loss dinamico agganciato al massimo più alto degli ultimi 22 giorni lavorativi ($H_{22}$), sottratto di 3 volte la volatilità media reale:

$$
\text{Chandelier Exit}_t = \max_{k=0..21}(H_{t-k}) - 3 \times ATR_{14,t}
$$

### 3. Distanza Percentuale & Alert Condition

$$
\text{Distanza Stop (pct)} = \frac{P_{\text{mkt}} - \text{Chandelier Exit}_t}{P_{\text{mkt}}} \times 100
$$

$$
\text{Alert Status} = \begin{cases} \text{🔴 TRIGGER}, & \text{se } P_{\text{mkt}} \le \text{Chandelier Exit}_t \\ \text{🟢 REGOLARE}, & \text{se } P_{\text{mkt}} > \text{Chandelier Exit}_t \end{cases}
$$

---

## 21. Impatto di Mercato & Costi di Liquidazione Almgren-Chriss (`compute_almgren_chriss_market_impact`)

### 1. Scomposizione dell'Impatto sui Prezzi (Almgren & Chriss, 2000)
Modello istituzionale per la stima dello slippage e dei costi di esecuzione durante la smobilizzazione o il bilanciamento di posizioni azionarie:
- **Impatto Permanente ($I_{\text{perm}}$)**: Spostamento strutturale del prezzo di equilibrio dovuto alla pressione informativa dell'ordine:
  

$$
I_{\text{perm}} = \gamma \cdot \left( \frac{\text{Volume Operativo}}{ADV} \right) \cdot P_{\text{attuale}}
$$

- **Impatto Temporaneo ($I_{\text{temp}}$)**: Pressione immediata sul book di negoziazione che si riassorbe nel tempo:
  

$$
I_{\text{temp}} = \eta \cdot \sqrt{\frac{\text{Volume Operativo}}{ADV \cdot T_{\text{ore}}}} \cdot P_{\text{attuale}}
$$

### 2. Slippage Stimato % & Impatto Monetario (€)

$$
\text{Slippage Stimato (pct)} = \frac{I_{\text{perm}} + I_{\text{temp}}}{P_{\text{attuale}}} \times 100
$$

$$
\text{Impatto Monetario Totale (EUR)} = \text{Quote Scambiate} \times (I_{\text{perm}} + I_{\text{temp}})
$$

---

## 22. Visualizzatore 3D della Superficie di Rischio (`compute_3d_stress_surface`)

### 1. Griglia Bivariata Tassi vs Volatilità
Modellizzazione della superficie di PnL su una griglia bivariata $X \times Y$:
- **Asse $X$ (Tassi $\Delta r$)**: Varie variazioni dei tassi da $-200\,\text{bps}$ a $+200\,\text{bps}$ (sensibilità duration $-4.5$).
- **Asse $Y$ (Volatilità $\Delta \sigma$)**: Varie variazioni della volatilità da $-30\%$ a $+50\%$ (sensibilità vega/equity $-0.35$).
- **Matrice $Z_{i,j}$ (Impatto PnL €)**:
  

$$
Z_{i,j} = \text{Capitale Totale} \times \left( \frac{\Delta r_j}{10000} \cdot (-4.5) + \frac{\Delta \sigma_i}{100} \cdot (-0.35) \right)
$$

---

## 23. Modello Macro-Fattoriale MSCI Barra a 5 Fattori Ortogonalizzati (`compute_msci_barra_multifactor_model`)

### 1. Equazione di Ortogonalizzazione dei Fattori (Gram-Schmidt OLS)
Per prevenire la multicollinearità ed isolare le reali esposizioni pure ai fattori di stile, ciascun fattore grezzo viene proiettato ed ortogonalizzato rispetto al fattore di mercato $F_{\text{MKT}}$:

$$
F_{\text{SMB}} = \text{SMB}_{\text{raw}} - \frac{\text{cov}(\text{SMB}_{\text{raw}}, F_{\text{MKT}})}{\text{var}(F_{\text{MKT}})} F_{\text{MKT}}
$$

$$
F_{\text{HML}} = \text{HML}_{\text{raw}} - \frac{\text{cov}(\text{HML}_{\text{raw}}, F_{\text{MKT}})}{\text{var}(F_{\text{MKT}})} F_{\text{MKT}}
$$

$$
F_{\text{WML}} = \text{WML}_{\text{raw}} - \frac{\text{cov}(\text{WML}_{\text{raw}}, F_{\text{MKT}})}{\text{var}(F_{\text{MKT}})} F_{\text{MKT}}
$$

$$
F_{\text{TERM}} = \text{TERM}_{\text{raw}} - \frac{\text{cov}(\text{TERM}_{\text{raw}}, F_{\text{MKT}})}{\text{var}(F_{\text{MKT}})} F_{\text{MKT}}
$$

### 2. Equazione di Regressione Multivariata OLS
Esposizione del rendimento in eccesso del portafoglio ai 5 fattori macro/di stile ortogonali:

$$
R_{p,t} - R_{f,t} = \alpha + \beta_{\text{MKT}} F_{\text{MKT},t} + \beta_{\text{SMB}} F_{\text{SMB},t} + \beta_{\text{HML}} F_{\text{HML},t} + \beta_{\text{WML}} F_{\text{WML},t} + \beta_{\text{TERM}} F_{\text{TERM},t} + \epsilon_t
$$

### 3. Decomposizione della Varianza & Statistica $t$
- **Rischio Sistemico Fattoriale \%**:

$$
R^2 \times 100
$$

- **Rischio Specifico Residuo \%**:

$$
(1 - R^2) \times 100
$$

- **Statistica $t$ dei Betas**:
  

$$
t_{\beta_k} = \frac{\hat{\beta}_k}{\text{SE}(\hat{\beta}_k)}, \quad \text{SE}(\hat{\beta}_k) = \sqrt{\hat{\sigma}_{\epsilon}^2 (X^T X)^{-1}_{kk}}
$$

  Valori di $|t_{\beta_k}| \ge 1.96$ indicano un'esposizione statisticamente significativa al livello di confidenza del 95% (`🟢 Significativo`).

---

## 25. Simulatore Stocastico Merton Jump-Diffusion (`compute_merton_jump_diffusion_simulation`)

### 1. Processo Stocastico Bivariato Diffusione + Salto Poissoniano
Modellizzazione non-gaussiana dei rendimenti per la misurazione del *Tail Risk* e delle *Fat Tails* durante crolli finanziari improvvisi:

$$
dS_t = \mu S_t dt + \sigma S_t dW_t + (e^{Y_t} - 1) S_t dN_t
$$

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

$$
s(x, n) = 2^{-\frac{\mathbb{E}(h(x))}{c(n)}}
$$

Dove $c(n)$ è la lunghezza media dei cammini negli alberi binari di ricerca per $n$ campioni. Valori di $s(x,n) \approx 1$ indicano anomalie marcate (giornate di panico o picchi di correlazione).

### 2. Vettore Multidimensionale delle Feature
- Rendimento giornaliero di portafoglio $R_{p,t}$
- Volatilità rolling a 20 giorni $\sigma_{20d}$
- Correlazione media di coppia tra tutti gli asset $\bar{\rho}_{20d}$
- Drawdown cumulato $DD_t$

---

## 27. Hierarchical Risk Parity — HRP (`core/hrp_optimizer.py`)

Sviluppato da Marcos López de Prado (2016), l'algoritmo **Hierarchical Risk Parity (HRP)** risolve i limiti strutturali della Frontiera Efficiente di Markowitz (instabilità dell'inversione della matrice di covarianza $\Sigma^{-1}$, amplificazione del rumore di stima e allocazioni con pesi polarizzati o irrealistici):

1. **Tree Clustering & Correlation Distance**:
   Definisce la distanza metrica tra asset $i$ e $j$ partendo dalla matrice di correlazione empirica $\rho_{i,j}$:
   

$$
D_{i,j} = \sqrt{\frac{1 - \rho_{i,j}}{2}}
$$

   Applica il clustering gerarchico (linkage singolo) per costruire il dendrogramma delle relazioni tra asset.
2. **Quasi-Diagonalization**:
   Riordina righe e colonne della matrice di covarianza secondo la sequenza dei nodi dell'albero gerarchico, posizionando gli asset più correlati in blocchi contigui lungo la diagonale principale.
3. **Recursive Bisection (Allocazione Inversa della Varianza)**:
   Per ogni sotto-ramo bipartito $V_1, V_2$, calcola la varianza di cluster:
   

$$
\tilde{V}_k = w_k^T \Sigma_k w_k, \quad w_k = \frac{\text{diag}(\Sigma_k)^{-1}}{\text{Tr}(\text{diag}(\Sigma_k)^{-1})}
$$

   Il fattore di ripartizione $\alpha$ tra i due raggruppamenti è:
   

$$
\alpha = 1 - \frac{\tilde{V}_1}{\tilde{V}_1 + \tilde{V}_2}
$$

   I pesi definitivi vengono scalati ricorsivamente:

$$
w_1 \leftarrow w_1 \cdot \alpha, \quad w_2 \leftarrow w_2 \cdot (1 - \alpha)
$$

---

## 28. Black-Scholes Pricing & Delta Hedging (`core/options_hedging.py`)

### 1. Prezzo Analitico Black-Scholes-Merton (1973)
Per un'opzione Europea con sottostante $S$, strike $K$, scadenza $T$, tasso privo di rischio $r$ e volatilità implicita $\sigma$:

$$
d_1 = \frac{\ln(S/K) + (r + \frac{1}{2}\sigma^2)T}{\sigma \sqrt{T}}, \quad d_2 = d_1 - \sigma \sqrt{T}
$$

- **Call**:

$$
C = S N(d_1) - K e^{-rT} N(d_2)
$$

- **Put**:

$$
P = K e^{-rT} N(-d_2) - S N(-d_1)
$$

### 2. I 5 Greci Analitici
- **Delta ($\Delta$)**:

$$
\Delta_{\text{Call}} = N(d_1), \quad \Delta_{\text{Put}} = N(d_1) - 1
$$

- **Gamma ($\Gamma$)**:

$$
\Gamma = \frac{N'(d_1)}{S \sigma \sqrt{T}}
$$

- **Vega**:

$$
\mathcal{V} = S \sqrt{T} N'(d_1)
$$

- **Theta ($\Theta$)**: Decadimento temporale dell'opzione per giorno
- **Rho ($\rho$)**: Sensibilità al tasso d'interesse

### 3. Portfolio Delta-Hedging con Opzioni Put
Il numero di contratti Put (ciascuno rappresentante un moltiplicatore standard di 100 azioni) per immunizzare o ridurre il Beta di portafoglio:

$$
N_{\text{contratti}} = \left\lceil \frac{\text{Valore Portafoglio} \times \beta_{\text{portafoglio}} \times \text{Copertura (pct)}}{S_{\text{benchmark}} \times |\Delta_{\text{put}}| \times 100} \right\rceil
$$

---

## 29. Market Regime Switching a 3 Stati (`core/regime_switching.py`)

Classificatore statistico di regime macroeconomico basato sull'osservazione congiunta del rendimento rolling a 21 giorni e della volatilità rolling a 21 giorni rispetto a soglie empiriche calibrate:

- **Stato 1: 🟢 Bull Low-Vol**: Rendimento rolling $\ge +0.5\%$ e Volatilità $\le 16.0\%$. Regime di espansione e trend rialzista ordinato.
- **Stato 2: 🟡 Transizione / Range-Bound**: Mercato laterale, rotazione settoriale o moderata incertezza macroeconomica.
- **Stato 3: 🔴 Crisi / Panic Selling (High-Vol)**: Rendimento rolling $< -3.0\%$ o Volatilità $> 24.0\%$. Regime di liquidazione e crollo di mercato.

Il modulo calcola la matrice di transizione di stato e la distribuzione delle probabilità recenti.

---

## 30. Contabilità Forense: Beneish M-Score & Sloan Accruals (`core/forensic_accounting.py`)

### 1. Beneish M-Score (1999) — 8-Factor Fraud Detection
Modello econometrico multivariato per quantificare la probabilità di manipolazione dei bilanci aziendali:

$$
M = -4.84 + 0.920 \cdot \text{DSRI} + 0.528 \cdot \text{GMI} + 0.404 \cdot \text{AQI} + 0.892 \cdot \text{SGI} + 0.115 \cdot \text{DEPI} - 0.172 \cdot \text{SGAI} + 4.037 \cdot \text{TATA} + 0.0327 \cdot \text{LVGI}
$$

- **Soglia Istituzionale**: $M > -1.78 \implies$ 🔴 **Probabile Manipolatore di Bilancio**.
- **$M \le -1.78 \implies$** 🟢 **Bilancio Genuino e Conforme**.

### 2. Sloan Accrual Ratio (1996) — Qualità degli Utili
Quantifica la discrepanza tra utile netto contabile e flussi di cassa operativi reali:

$$
\text{Accrual Ratio} = \frac{\text{Net Income} - \text{Operating Cash Flow}}{\text{Total Assets}}
$$

- $\text{Ratio} \le -0.05 \implies$ 🟢🟢 **Qualità Eccellente** (Flussi di cassa reali eccedenti gli utili contabili).
- $\text{Ratio} \in (-0.05, +0.10) \implies$ 🟢 **Qualità Stabile**.
- $\text{Ratio} > +0.10 \implies$ 🔴 **Bassa Qualità Contabile** (Utili gonfiati da crediti e scritture contabili).

---

## 31. Multi-Tier Caching & Rate-Limit Shield (`core/cache_shield.py`)

Architettura di protezione a doppio livello per prevenire rate-limiting e blocchi `HTTP 429 Too Many Requests` su API esterne (yfinance):
- **Tier 1 (RAM LRU Cache)**: Look-up in-memory a latenza sub-millisecondo per azzerare i ricalcoli ridondanti nei re-render di Streamlit.
- **Tier 2 (SQLite Disk Cache)**: Tabella `yfinance_cache` nel database SQLite `data/yfinance_cache.db` con validità (TTL) a 24 ore ($86.400$ secondi) per ticker e tipo dato (prezzi, corporate metadata).
- **Throttling & Backoff Esponenziale**: Jittering casuale e ritardi progressivi nei tentativi di connessione per una navigazione conforme e stabile.
- **Seamless Offline Fallback**: In caso di mancata connessione a internet o timeout del fornitore esterno, il sistema serve in modo trasparente l'ultimo record valido presente su disco.

---

## 32. System Diagnostics & Health-Check Cockpit (`core/diagnostics.py`)

Suite integrata di monitoraggio e telemetria per la verifica continua delle prestazioni di calcolo e dell'integrità del sistema:
- **Benchmark di Latenza Real-Time (ms)**: Cronometraggio ad alta precisione con `time.perf_counter()` per ciascuno dei motori quantitativi critici (HRP, Black-Scholes, Regime Switching, Merton Jump-Diffusion, Forensic Accounting, Technical Charting).
- **Controllo di Integrità dei Database**: Ping test e verifica dello schema e del conteggio delle tabelle su MySQL ed SQLite locale.
- **Verifica del Determinismo Pseudo-Casuale**: Validazione di riproducibilità numerica al 100% per i generatori stocastici e le simulazioni Monte Carlo basate su Numpy PRNG.

---

## 33. Dipendenza di Coda & Copule Asimmetriche (`core/advanced_quant.py`)

Superamento della correlazione lineare di Pearson nei momenti di crollo di mercato tramite l'analisi della dipendenza non lineare di coda (Tail Copula Dependence).

### 1. Lower Tail Dependence ($\lambda_L$) — Rischio di Crash Congiunto
Misura la probabilità condizionata che l'asset $j$ registri una perdita estrema (sotto il percentile $q$) dato che l'asset $i$ è in una fase di crollo sistemico:

$$
\lambda_L(i, j) = \lim_{q \to 0^+} P(U_j \le q \mid U_i \le q) = \lim_{q \to 0^+} \frac{C(q, q)}{q}
$$

dove $U_i, U_j \sim \text{Uniform}(0, 1)$ sono le marginali ottenute tramite trasformazione di rango empirica.

### 2. Parametrizzazione tramite Copula di Clayton
Nei modelli parametrici archimedei di Clayton (con $\tau > 0$ Kendall's Tau):

$$
\theta = \frac{2\tau}{1 - \tau}, \quad \lambda_L^{\text{Clayton}} = 2^{-1/\theta}
$$

Valori elevati ($\lambda_L > 0.35$) evidenziano che la diversificazione di portafoglio collassa durante le giornate di panic selling (*Asymmetric Crash Contagion*).

---

## 34. Criterio di Kelly & Fractional Position Sizing (`core/advanced_quant.py`)

Calcolo del dimensionamento matematico ottimale delle posizioni per massimizzare il tasso atteso di crescita logaritmica del capitale nel lungo periodo:

### 1. Formulazione Continua (Gaussian / MPT)

$$
f^* = \frac{\mu - R_f}{\sigma^2}
$$

dove $\mu$ è il rendimento atteso annualizzato, $R_f$ è il tasso risk-free e $\sigma^2$ è la varianza annualizzata dell'asset.

### 2. Formulazione Discreta di Bernoulli

$$
f^* = \frac{p \cdot (b + 1) - 1}{b}
$$

dove $p = P(R > 0)$ è il Win Rate e $b = \frac{\text{Media Guadagni}}{|\text{Media Perdite}|}$ è il rapporto vincita/perdita.

### 3. Approccio Istituzionale Half-Kelly ($f^* / 2$)
L'allocazione a Pieno Kelly ($f^*$) massimizza la crescita geometrica ma espone a drawdown violenti ($>50\%$). L'approccio istituzionale **Half-Kelly** cattura il **75% del tasso di crescita teorico massimo** con il **50% in meno di volatilità** ed azzera la probabilità statistica di dimezzamento del patrimonio.

---

## 35. Equal Risk Contribution / Risk Parity Pura (`core/advanced_quant.py`)

Algoritmo di allocazione in cui ogni singolo asset contribuisce esattamente per la stessa quota ($1/N$) alla volatilità complessiva di portafoglio:

### 1. Contributo Marginale al Rischio

$$
RC_i(w) = w_i \cdot \frac{(\Sigma w)_i}{\sigma_p}
$$

dove $\Sigma$ è la matrice di covarianza Ledoit-Wolf e $\sigma_p = \sqrt{w^T \Sigma w}$ è la volatilità di portafoglio.

### 2. Problema di Ottimizzazione SLSQP

$$
\min_w \sum_{i=1}^N \sum_{j=1}^N \left( RC_i(w) - RC_j(w) \right)^2 \quad \text{s.t.} \quad \sum_{i=1}^N w_i = 1, \quad w_i \ge 0
$$

A differenza dell'approccio ingenuo $1/N$ in capitale, l'Equal Risk Contribution garantisce un'equa ripartizione del rischio senza concentrazioni nei titoli a più elevata volatilità.

---

## 36. Total Wealth Hub & Consolidamento Multi-Portafoglio (`core/multi_portfolio.py`)

Framework per la gestione, la sincronizzazione duale (Google Sheets Stocks & Crypto) e la fusione simultanea di più conti o strategie (Crescita, Dividendi, Previdenza, Crypto):
- **Fusione Posizioni e WACP**: Aggregazione delle quote $Q_{\text{tot}} = \sum Q_k$ e ricalcolo del costo medio ponderato:
  

$$
WACP_{\text{cons}} = \frac{\sum Q_k \cdot WACP_k}{\sum Q_k}
$$

- **Standard Temporale GIPS (Global Investment Performance Standards)**: Per portafogli multi-asset comprendenti sia mercati azionari tradizionali (252 giorni/anno) sia mercati a contrattazione continua 24/7 come le criptovalute (365 giorni/anno), la durata temporale viene calcolata ancorandosi alla reale distanza solare tra le date:
  

$$
n_{\text{years}} = \frac{\text{Data}_{\max} - \text{Data}_{\min}}{365.2425}
$$

  garantendo un calcolo del CAGR privo di distorsioni da sovrastima dei giorni lavorativi:
  

$$
\text{CAGR} = (1 + R_{\text{tot}})^{\frac{1}{n_{\text{years}}}} - 1
$$

- **Serie Storica Rendimenti Consolidata**: Fonde le serie storiche dei rendimenti ponderandole per il peso patrimoniale:

$$
w_k = \frac{V_k}{V_{\text{tot}}}
$$

  

$$
R_t^{\text{master}} = \sum_{k=1}^K w_k \cdot R_{t, k}
$$

- **Allineamento Regressione Beta e Style Analysis Fama-French**: Il Beta del Master Wealth e i fattori $\alpha_{\text{FF}}$, $\beta_{\text{MKT}}$, SMB e HML vengono stimati tramite regressione OLS multivariata allineata sulle date di effettiva contrattazione del mercato:
  

$$
\beta_{\text{Master}} = \frac{\text{Cov}(R_{\text{master}}, R_{\text{bm}})}{\text{Var}(R_{\text{bm}})}
$$

- **Frontiera Efficiente e Ottimizzazione Ledoit-Wolf**: Il consolidatore calcola automaticamente i portafogli ottimali a Massimo Sharpe Ratio e Minima Volatilità sulla matrice di covarianza a shrinkage antirumore di Ledoit-Wolf.

---

## 37. Database & Memory Storage Cockpit (`core/diagnostics.py`)

Framework per l'analisi telemetrica dell'occupazione fisica dei database SQLite/MySQL, della memoria di processo e delle procedure di manutenzione ad alte prestazioni:

### 1. Storage Footprint & Freelist Page Recovery
- **Occupazione Fisica**: Misurazione esatta dei byte su disco per ciascun contenitore relazionale (`argus_local.db`, `yfinance_cache.db`, file binari `.pkl`).
- **Pagine Libere (Freelist Space)**: Quantificazione delle pagine liberate in seguito a cancellazioni di record ma non ancora restituite al file system:
  

$$
\text{Reclaimable Space (Bytes)} = \text{Freelist Count} \times \text{Page Size}
$$

- **Compattazione Dinamica (`VACUUM`)**: Esecuzione del comando SQLite `VACUUM` e `PRAGMA optimize` per deframmentare il database, azzerare le pagine orfane e recuperare spazio fisico su disco.

### 2. Monitoraggio della Memoria di Processo (RAM RSS)
- **Resident Set Size (RSS)**: Misurazione in tempo reale della RAM fisica effettivamente allocata al processo Python interprete (`psutil.Process().memory_info().rss`), prevenendo memory leak durante sessioni prolungate di calcolo intensivo Monte Carlo.
- **Session Memory Footprint**: Ispezione dell'ingombro in RAM degli oggetti DataFrame e serie storiche attualmente residenti nello stato dell'applicazione.

### 3. Manutenzione e Reindicizzazione B-Tree
- **Cache Eviction TTL**: Rimozione automatizzata dei record con timestamp superiore al Time-To-Live ($TTL > 24\text{h}$):
  

$$
\Delta t = t_{\text{now}} - t_{\text{cached}} > 86.400\,\text{s}
$$

- **Reindexing B-Tree**: Ricostruzione periodica degli indici compositi su `(ticker, price_date)` tramite `REINDEX` per mantenere le latenze di ricerca temporale su complessità logaritmica $\mathcal{O}(\log N)$.

---

## 38. Posizioni Chiuse & Graveyard Analytics (`core/closed_trades.py`)

Framework analitico per la ricostruzione e l'audit delle operazioni di disinvestimento totale o parziale elaborate con precisione contabile FIFO:

### 1. Curva Cumulativa di PnL Realizzato & High-Water Mark (HWM)
Traccia l'evoluzione progressiva del profitto o perdita monetizzato nel tempo:

$$
\text{CumPnL}_t = \sum_{\tau \le t} \text{RealizedPnL}_\tau
$$

La linea di **High-Water Mark (Picco)** quantifica il massimo storico di capitale realizzato:

$$
\text{HWM}_t = \max_{\tau \le t} \text{CumPnL}_\tau
$$

Il **Trade Drawdown** associato misura l'erosione del capitale realizzato rispetto al picco:

$$
\text{DD}_t = \text{CumPnL}_t - \text{HWM}_t
$$

### 2. Trading Calendar & Heatmap Stagionale (Mese $\times$ Anno)
Matrice di monitoraggio temporale delle chiusure:

$$
\text{PnL}_{\text{Anno}, \text{Mese}} = \sum_{i \in \text{Trades}_{\text{Anno}, \text{Mese}}} \text{RealizedPnL}_i
$$

Evidenzia la ciclicità delle decisioni di monetizzazione e la consistenza temporale del processo di gestione.

### 3. Scomposizione Settoriale e per Asset Class
Aggrega il PnL realizzato, i volumi transati e il Win Rate percentuale su base GICS:

$$
\text{Win Rate}_{\text{settore}} = \frac{\sum \mathbf{1}_{\{\text{RealizedPnL}_i > 0\}}}{N_{\text{settore}}} \times 100
$$

---

## 39. Fisco Italiano & Tax-Loss Harvesting Wizard (TUIR Art. 67) (`core/tax_engine.py`)

Motore di ottimizzazione e pianificazione fiscale per investitori residenti in Italia basato sul Testo Unico delle Imposte sui Redditi (TUIR, D.P.R. 917/1986):

### 1. Asimmetria Fiscale: Redditi di Capitale vs Redditi Diversi
- **ETF e Fondi Comuni**: Le plusvalenze sono qualificate come *Redditi di Capitale* (tassazione 26%) e **non possono** essere compensate con le minusvalenze pregresse. Le minusvalenze generate da ETF sono invece *Redditi Diversi* e vanno a confluire nello Zainetto Fiscale.
- **Azioni Singole, Obbligazioni ed ETC**: Le plusvalenze costituiscono *Redditi Diversi* e possono compensare **1:1** le minusvalenze accumulate nello Zainetto Fiscale.
- **Titoli di Stato White List**: Aliquota agevolata al 12.5% (equivalente al 48.08% di imponibilità a fini di compensazione).

### 2. Strategia Step-Up Fiscale a 0\text{ EUR} Imposte
Per evitare la decadenza delle minusvalenze dopo 4 anni solari ($t + 4$), il wizard individua le posizioni in utile appartenenti ai *Redditi Diversi* da vendere e ricomprare immediatamente:

$$
\text{Controvalore Vendita} = \min\left(\text{Valore Posizione}, \frac{\text{Minusvalenza Residua}}{\text{Plusvalenza Percentuale}}\right)
$$

- **Effetto Fiscale**: La plusvalenza monetizzata azzera le minusvalenze in scadenza senza versare 1€ di imposte.
- **Vantaggio Futuro**: Il nuovo prezzo di carico (WACP) viene innalzato al prezzo di mercato, generando un risparmio fiscale futuro certo del **26%** sulla quota di plusvalenza assorbita:
  

$$
\text{Risparmio Fiscale Futuro} = \text{Minusvalenza Compensata} \times 26\%
$$

### 3. Strategia Tax-Loss Harvesting (Raccolta Minusvalenze)
Monetizzazione strategica delle perdite latenti prima del 31 dicembre per compensare plusvalenze maturate nell'anno o rinnovare lo scudo fiscale quadriennale.

---

## 40. Simulatore Interattivo Trade-Level Kelly Criterion (`core/advanced_quant.py`)

Algoritmo di dimensionamento ottimale delle scommesse (Position Sizing) derivato dalla teoria dell'informazione di John L. Kelly Jr. (1956):

### 1. Formulazione Discreta e Fractional Sizing
Dati il Win Rate storico $p$ e il Payoff Ratio $b = \frac{\overline{\text{Win}}}{\overline{\text{Loss}}}$ estratti dal registro FIFO:

$$
f^* = \frac{p(b + 1) - 1}{b}
$$

- **Half-Kelly ($f^*_{\text{half}} = f^*/2$)**: Frazione raccomandata che massimizza il trade-off rendimento/volatilità, catturando il 75% della crescita geometrica massima con un dimezzamento della varianza e abbattimento del rischio di rovina.
- **Quarter-Kelly ($f^*_{\text{quarter}} = f^*/4$)**: Profilo ultra-difensivo per mercati ad elevata incertezza o regimi di crisi.

### 2. Dimensionamento del Nozionale in Funzione dello Stop-Loss
Dato un capitale di portafoglio $C$ e una distanza di Stop-Loss percentuale:

$$
SL\% = \frac{P_{\text{entry}} - P_{\text{stop}}}{P_{\text{entry}}}
$$

$$
\text{Capitale a Rischio (EUR)} = C \times f^*_{\text{half}}
$$

$$
\text{Controvalore Nozionale Posizione (EUR)} = \frac{\text{Capitale a Rischio (EUR)}}{SL\%}
$$

$$
\text{Numero Quote Operative} = \left\lfloor \frac{\text{Controvalore Nozionale}}{P_{\text{entry}}} \right\rfloor
$$

### 3. Tasso di Crescita Geometrico Atteso

$$
G(f) = p \ln(1 + f \cdot b) + (1 - p) \ln(1 - f)
$$

Se l'Edge matematico $E = p \cdot b - (1 - p) \le 0$, l'algoritmo impone $f^* = 0$ (esposizione nulla).

---

## 41. Curva Tassi Privi di Rischio (Risk-Free Yield Curve) & Calibrazione Multi-Valuta (`core/yield_curve.py`)

La piattaforma integra un motore dedicato di calibrazione automatica del tasso privo di rischio ($R_f$) ancorato alle principali curve monetarie interbancarie e governative internazionali a breve termine, con caching resiliente (TTL 12h) e fallback deterministici su dati ufficiali delle Banche Centrali:

### 1. Benchmark Istituzionali per Valuta Base
- **EUR (€STR / Deposit Facility BCE)**: Tasso overnight interbancario dell'Eurozona monitorato in tempo reale tramite il proxy monetario `XEON.DE` (Xtrackers II EUR Overnight Rate Swap UCITS ETF). Tasso di fallback ufficiale BCE: **2.75%**.
- **USD (US 3M Treasury Bill / SOFR)**: Rendimento del Buono del Tesoro USA a 3 mesi monitorato tramite indice live `^IRX` (CBOE 13-Week Treasury Yield Index). Tasso di fallback ufficiale Federal Reserve: **4.35%**.
- **GBP (BoE SONIA)**: Sterling Overnight Index Average tracciato tramite `CSH2.L` (Lyxor Smart Overnight Return UCITS ETF). Tasso di fallback ufficiale Bank of England: **4.75%**.
- **CHF (SNB SARON)**: Swiss Average Rate Overnight. Tasso di fallback ufficiale Banca Nazionale Svizzera: **1.00%**.

### 2. Conversione e Compounding Giornaliero
Dato il tasso risk-free nominale annualizzato $R_f$, il tasso privo di rischio giornaliero $R_{f,d}$ applicato sui rendimenti logaritmici o discreti di portafoglio viene calcolato su base convenzionale a 252 giorni di borsa aperta:

$$
R_{f,d} = \frac{R_f}{252}
$$

### 3. Propagazione Analitica nei Moduli Quantitativi
Il tasso risk-free dinamico viene propagato automaticamente su tutte le metriche e i modelli della piattaforma:
1. **Indice di Sharpe Annualizzato**:
   

$$
\text{Sharpe} = \frac{\mu_p - R_f}{\sigma_p}
$$

2. **Indice di Sortino**:
   

$$
\text{Sortino} = \frac{\mu_p - R_f}{\sigma_{\text{downside}}(R_{f,d})}
$$

3. **Jensen's Alpha**:
   

$$
\alpha = (R_p - R_f) - \beta (R_m - R_f)
$$

4. **Prezzatura Opzioni Black-Scholes (1973) & Delta-Hedging**:
   

$$
d_1 = \frac{\ln(S/K) + \left(R_f + \frac{\sigma^2}{2}\right)T}{\sigma \sqrt{T}}, \quad d_2 = d_1 - \sigma \sqrt{T}
$$

   

$$
C = S \cdot N(d_1) - K e^{-R_f T} N(d_2), \quad P = K e^{-R_f T} N(-d_2) - S \cdot N(-d_1)
$$

   

$$
\rho_{\text{call}} = K T e^{-R_f T} N(d_2), \quad \rho_{\text{put}} = -K T e^{-R_f T} N(-d_2)
$$

5. **Costo Medio Ponderato del Capitale (WACC & CAPM)**:
   

$$
K_e = R_f + \beta_e \times \text{ERP}
$$

6. **Kelly Criterion Continuo**:
   

$$
f^* = \frac{\mu - R_f}{\sigma^2}
$$

---

## 42. Corporate Actions & Stock Split Accounting Engine (`core/corporate_actions.py`)

Il modulo gestisce le operazioni straordinarie sul capitale (Stock Split, Reverse Split e Stock Dividend) garantendo la continuità contabile, l'integrità delle code FIFO e la conformità fiscale (TUIR Art. 67).

### 1. Principio di Invarianza del Costo di Carico Fiscale
Dato un lotto di acquisto $k$ registrato prima della data di efficacia dello split ($t_k < t_{\text{split}}$) con $Q_{\text{orig}, k}$ quote al prezzo unitario $P_{\text{orig}, k}$:

$$
Q_{\text{adj}, k} = Q_{\text{orig}, k} \times R
$$

$$
P_{\text{adj}, k} = \frac{P_{\text{orig}, k}}{R}
$$

$$
\text{Cost Basis}_k = Q_{\text{adj}, k} \times P_{\text{adj}, k} = Q_{\text{orig}, k} \times P_{\text{orig}, k}
$$

dove $R$ è il coefficiente di frazionamento ($R > 1$ per Forward Split, $R < 1$ per Reverse Split).

### 2. Rettifica FIFO Retroattiva e Prevenzione Errori di Inventario
1. **Prevenzione Falsi Sbilanciamenti**: Se un investitore acquista 10 azioni a 500\text{ EUR} e successivamente interviene uno split 10:1 ($R=10$), il saldo rettificato diviene di 100 azioni a 50\text{ EUR}. Una successiva vendita di 30 azioni a 70\text{ EUR} viene abbinata al lotto rettificato, determinando:
   

$$
\text{PnL Realizzato} = 30 \times (70 - 50) = +600\text{ EUR}
$$

   

$$
\text{Quote Residue} = 70 \text{ azioni con WACP} = 50\text{ EUR}
$$

2. **Sincronizzazione con Prezzi di Mercato**: Poiché le serie storiche dei prezzi scaricate dai provider (Yahoo Finance) sono rettificate (*Adjusted Close*), la rettifica dei lotti di acquisto garantisce che il PnL latente ($P_{\text{market}} - \text{WACP}$) rifletta il reale guadagno economico senza distorsioni artificiali.

---

## 43. Volatilità Condizionale GARCH(1,1) & Filtered Historical Simulation (FHS) (`core/garch_fhs_engine.py`)

Il modulo modella i cluster di volatilità e la varianza condizionale time-varying nei mercati finanziari (Bollerslev 1986), superando il limite dell'omoschedasticità tipico dei modelli a volatilità costante.

### 1. Equazione del Modello GARCH(1,1)
Dati i rendimenti giornalieri:

$$
r_t = \mu + \epsilon_t, \quad \epsilon_t = \sigma_t z_t, \quad z_t \sim \text{i.i.d.}(0, 1)
$$

$$
\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2
$$

Vincoli di stazionarietà e regolarità:
- $\omega > 0$: Costante di varianza di base.
- $\alpha \ge 0$: Reattività agli shock di mercato a breve termine (effetto ARCH).
- $\beta \ge 0$: Persistenza della volatilità passata (effetto GARCH).
- $\alpha + \beta < 1$: Condizione necessaria e sufficiente per la stazionarietà in senso debole.

### 2. Stima dei Parametri tramite Maximum Likelihood Estimation (MLE)
La funzione di log-verosimiglianza Gaussiana da massimizzare numericamente (algoritmo SLSQP o L-BFGS-B) è:

$$
\ln L(\omega, \alpha, \beta) = -\frac{1}{2} \sum_{t=1}^T \left( \ln(2\pi) + \ln(\sigma_t^2) + \frac{\epsilon_t^2}{\sigma_t^2} \right)
$$

### 3. Varianza Incondizionata di Lungo Periodo ed Emodimezzamento (Half-Life)
1. **Varianza di Lungo Periodo ($V_L$)**:
   

$$
V_L = \frac{\omega}{1 - \alpha - \beta}, \quad \sigma_{\text{annuale, asymptotic}} = \sqrt{252 \times V_L}
$$

2. **Half-Life degli Shock ($T_{1/2}$)**:
   Misura il numero di giorni necessari affinché uno shock di volatilità si riassorba del 50% tornando verso la media di lungo termine:
   

$$
T_{1/2} = \frac{\ln(0.5)}{\ln(\alpha + \beta)}
$$

### 4. Struttura a Termine della Volatilità (Term Structure a $k$ Giorni)
La previsione della varianza condizionale a $k$ passi in avanti è espressa in forma chiusa:

$$
\mathbb{E}_t[\sigma_{t+k}^2] = V_L + (\alpha + \beta)^k (\sigma_t^2 - V_L)
$$

- Se $\sigma_t^2 > V_L$: Struttura a termine decrescente (*Mean Reversion* da regime di alta volatilità).
- Se $\sigma_t^2 < V_L$: Struttura a termine crescente (espansione della volatilità verso la media storica).

### 5. Filtered Historical Simulation (FHS - Hull-White 1998, Barone-Adesi 1999)
La FHS combina la capacità del modello GARCH di catturare il livello di rischio contingente con la distribuzione non parametrica dei residui empirici:
1. **De-volatilizzazione dei Rendimenti Storici**:
   

$$
z_t = \frac{r_t - \bar{r}}{\sigma_t^{\text{GARCH}}}, \quad \forall t \in [1, T]
$$

2. **Generazione dei Rendimenti Filtrati per il Periodo Successivo ($T+1$)**:
   

$$
r_{T+1, t}^* = \bar{r} + z_t \cdot \sigma_{T+1}^{\text{GARCH}}
$$

3. **Calcolo di VaR e CVaR FHS a Code Spesse (Conformità Basel III / FRTB)**:
   

$$
VaR_{\text{FHS}}(h, \alpha) = - \text{Percentile}(r^*, \alpha) \cdot \sqrt{h} \cdot V_{\text{portfolio}}
$$

   

$$
CVaR_{\text{FHS}}(h, \alpha) = - \mathbb{E}[r^* \mid r^* \le -VaR_{\text{FHS}}] \cdot \sqrt{h} \cdot V_{\text{portfolio}}
$$

---

## 44. Superficie di Volatilità Implicita 3D, Inversione Numerica e Calibrazione Skew/Smile (`core/volatility_surface.py`)

Il modulo calibra la struttura di volatilità implicita delle opzioni su moneyness e scadenze, quantificando il premio per il rischio di crash e dimensionando coperture con opzioni Put.

### 1. Inversione Numerica di Black-Scholes tramite Metodo di Newton-Raphson
Data la formula di prezzatura Black-Scholes (1973) per un'opzione Put europea:

$$
P_{\text{BS}}(S, K, T, r, \sigma) = K e^{-r T} N(-d_2) - S N(-d_1)
$$

$$
d_1 = \frac{\ln(S/K) + \left(r + \frac{\sigma^2}{2}\right)T}{\sigma \sqrt{T}}, \quad d_2 = d_1 - \sigma \sqrt{T}
$$

La volatilità implicita $\sigma_{\text{IV}}$ è la radice dell'equazione non lineare $f(\sigma) = P_{\text{BS}}(\sigma) - P_{\text{market}} = 0$, risolta iterativamente:

$$
\sigma_{n+1} = \sigma_n - \frac{P_{\text{BS}}(\sigma_n) - P_{\text{market}}}{\mathcal{V}(\sigma_n)}
$$

dove il Vega dell'opzione è la derivata parziale analitica:

$$
\mathcal{V} = \frac{\partial P_{\text{BS}}}{\partial \sigma} = S \sqrt{T} \phi(d_1) = S \sqrt{T} \frac{1}{\sqrt{2\pi}} e^{-\frac{d_1^2}{2}}
$$

In caso di fallimento di convergenza o Vega nullo ($\mathcal{V} \approx 0$ su contratti deep-ITM/OTM), il sistema attiva un algoritmo robusto di bisezione / Brent entro l'intervallo $\sigma \in [0.001, 5.0]$.

### 2. Calibrazione Parametrica di Volatility Skew e Smile
Sia il log-moneyness normalizzato definito come $m = \ln(K / S)$:

$$
\sigma_{\text{IV}}(m) = a + b \cdot m + c \cdot m^2
$$

- **Parametro $a$**: Livello di volatilità at-the-money ($m=0$, $K=S$).
- **Parametro $b < 0$ (*Skew Slope*)**: Pendenza della curva. Un valore negativo riflette la tipica asimmetria dei mercati azionari (*Crash Risk Premium* per Put Out-of-the-Money).
- **Parametro $c > 0$ (*Smile Curvature*)**: Curvatura convessa associata al costo delle opzioni con strike estremi (fat-tail hedging).

### 3. Delta-Hedging Skew-Adjusted con Opzioni Put
Dato un portafoglio di valore nominale $V_{\text{port}}$ con esposizione Delta equivalente $\Delta_{\text{port}} = \beta_{\text{port}} \cdot V_{\text{port}}$, il dimensionamento della copertura con opzioni Put a strike OTM ($K < S$) è:

$$
\Delta_{\text{put}} = -N(-d_1(\sigma_{\text{IV}}(m_{\text{OTM}})))
$$

$$
N_{\text{contratti}} = \frac{\Delta_{\text{port}}}{|\Delta_{\text{put}}| \times \text{Multiplier} \times S}
$$

$$
\text{Costo Annuo Assicurazione (pct AUM)} = \frac{N_{\text{contratti}} \times P_{\text{put}} \times \text{Multiplier}}{V_{\text{port}}} \times \frac{365.25}{T_{\text{giorni}}}
$$

---

## 45. Modulo Fiscale Cripto-Attività e Quadri RT / RW / IVAFE (`core/crypto_tax_engine.py`)

Il motore applica il quadro normativo introdotto dalla **Legge 29 dicembre 2022, n. 197 (Legge di Bilancio 2023)** e dalla **Circolare dell'Agenzia delle Entrate n. 30/E/2023**.

### 1. Inquadramento TUIR (Art. 67, comma 1, lett. c-sexies)
Le plusvalenze realizzate mediante cessione a titolo oneroso, rimborso o permuta di cripto-attività costituiscono *Redditi Diversi di Natura Finanziaria*.
1. **Franchigia Annuale di 2.000\text{ EUR}**:
   

$$
\text{Base Imponibile Netta} = \max\left(0, \sum \text{Plusvalenze} - \sum \text{Minusvalenze} - 2.000\text{ EUR}\right)
$$

2. **Imposta Sostitutiva (26%)**:
   

$$
\text{Debito Fiscale RT} = \text{Base Imponibile Netta} \times 26\%
$$

3. **Irrilevanza Fiscale delle Permute Cripto-to-Cripto**: La conversione di un token in un altro token avente le medesime caratteristiche non genera fattispecie fiscalmente imponibile. Il costo di carico del token ceduto si trasferisce proporzionalmente sul nuovo token acquistato.

### 2. Zainetto Fiscale Cripto Separato (Regime a 4 Anni)
Le minusvalenze cripto realizzate in eccedenza possono essere portate in deduzione dalle plusvalenze cripto dei 4 periodi d'imposta successivi ($t+1, t+2, t+3, t+4$):
- **Principio di Segregazione Contabile**: Le minusvalenze su cripto-attività **non sono compensabili** con plusvalenze derivanti da azioni, obbligazioni o fondi tradizionali, e viceversa.

### 3. Monitoraggio Fiscale (Quadro RW, Codice 21) ed Imposta di Bollo / IVAFE
1. **Quadro RW**: Obbligo di monitoraggio per le cripto-attività detenute su exchange esteri o private keys/cold wallet, con indicazione di valore iniziale (1/1) e valore finale (31/12).
2. **Imposta sul Valore delle Cripto-Attività (0,20% annuo)**:
   

$$
\text{Imposta Cripto-Attività} = \text{Controvalore al 31/12} \times 0.20\% \times \frac{\text{Giorni di Detenzione}}{365.25}
$$

---

## 46. Kenneth French Factor Library Live (Fama-French 5-Factor & Momentum) (`core/factor_library.py`)

Il modulo integra le serie storiche ufficiali di ricerca accademica del *Dartmouth College (Kenneth R. French Data Library)* per eseguire regressioni multifattoriali avanzate.

### 1. Equazione del Modello Fama-French a 5 Fattori + Carhart Momentum

$$
R_{i,t} - R_{f,t} = \alpha_i + \beta_{MKT} (R_{m,t} - R_{f,t}) + \beta_{SMB} SMB_t + \beta_{HML} HML_t + \beta_{RMW} RMW_t + \beta_{CMA} CMA_t + \beta_{MOM} MOM_t + \epsilon_{i,t}
$$

### 2. Definizione dei Driver Accademici di Rendimento
- **Mkt-RF**: Eccesso di rendimento del portafoglio di mercato su tutti i titoli NYSE/AMEX/NASDAQ rispetto al tasso privo di rischio US 1M T-Bill.
- **SMB (*Small Minus Big*)**: Spread di rendimento basato sulla dimensione (*Market Cap*), misurando l'extra-rendimento storico delle small cap.
- **HML (*High Minus Low*)**: Spread basato sul valore contabile/prezzo (*Book-to-Market*), catturando il premio per il rischio dei titoli Value rispetto ai titoli Growth.
- **RMW (*Robust Minus Weak*)**: Spread basato sulla qualità della redditività operativa (*Operating Profitability*).
- **CMA (*Conservative Minus Aggressive*)**: Spread basato sulla prudenza negli investimenti di capitale (*Investment Factor*).
- **MOM / WML (*Winners Minus Losers*)**: Spread tra titoli con momentum relativo positivo vs negativo nei precedenti 12 mesi.

### 3. Risoluzione OLS Multivariata e Test Statistici

$$
\hat{\boldsymbol{\beta}} = (\mathbf{X}^T \mathbf{X})^{-1} \mathbf{X}^T \mathbf{Y}
$$

$$
\hat{\sigma}_\epsilon^2 = \frac{\sum_{t=1}^T \hat{\epsilon}_t^2}{T - K - 1}, \quad \text{SE}(\hat{\beta}_k) = \sqrt{\hat{\sigma}_\epsilon^2 \cdot [(\mathbf{X}^T \mathbf{X})^{-1}]_{kk}}
$$

$$
t_k = \frac{\hat{\beta}_k}{\text{SE}(\hat{\beta}_k)}, \quad p\text{-value} = 2 \cdot (1 - \Phi(|t_k|))
$$

### 4. Factor Return Attribution e Rolling OLS
1. **Attribuzione di Rendimento Annualizzata**:
   

$$
\text{Contributo Fattoriale}_k = \hat{\beta}_k \times \overline{\text{Factor}}_k \times 252
$$

   

$$
\text{Alpha Annualizzato} = \hat{\alpha} \times 252
$$

2. **Rolling Factor Betas a 60 Giorni**: Identificazione dinamica di cambi di allocazione, transizioni tra regimi di mercato e rotazioni di stile (*Style Drift*).

---

## 47. Retrieval-Augmented Generation (RAG) & Vector Store Semantico sui Bilanci SEC (`core/sec_rag_engine.py`)

Il modulo esegue analisi documentale forense e risposte in linguaggio naturale sui bilanci ufficiali SEC (Form 10-K annuali e Form 10-Q trimestrali).

### 1. Chunking Normativo Strutturato (SEC Standard Taxonomy)
I documenti vengono normalizzati e partizionati per Item normativi conformi al Regolamento S-K:
- **Item 1**: *Business Model, Moat, Segment Breakdown, Key Clients*.
- **Item 1A**: *Risk Factors, Geopolitical Threats, Supply Chain Hazards, Regulatory Liabilities*.
- **Item 7**: *Management's Discussion & Analysis (MD&A), Gross Margins, Capital Expenditures, Guidance*.
- **Item 8**: *Financial Statements, Supplementary Debt Schedule, Commitments & Contingencies*.

### 2. Algoritmo di Ponderazione Lessicale BM25 Okapi

$$
\text{Score}_{\text{BM25}}(D, Q) = \sum_{i=1}^n \text{IDF}(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}
$$

con parametri calibrati $k_1 = 1.5, b = 0.75$, e Inverse Document Frequency:

$$
\text{IDF}(q_i) = \ln\left( \frac{N - n(q_i) + 0.5}{n(q_i) + 0.5} + 1 \right)
$$

### 3. Dense Vector Similarity e Pipeline di Risposta Grounded
1. **Similarità Coseno su Vettori TF-IDF Normalizzati**:
   

$$
\text{Cosine}(Q, D) = \frac{\mathbf{v}_Q \cdot \mathbf{v}_D}{\|\mathbf{v}_Q\|_2 \cdot \|\mathbf{v}_D\|_2}
$$

2. **Punteggio Ibrido di Rilevanza**:
   

$$
\text{Score}_{\text{Hybrid}} = 0.60 \times \text{Norm}(\text{Score}_{\text{BM25}}) + 0.40 \times \text{Cosine}(Q, D)
$$

3. **Citazioni Grounded**: Ogni insight generato include metadati verificabili: `[SEC Filing: Form 10-K | Sezione: Item 1A (Risk Factors) | Rilevanza: 94.2%]`.

---

## 48. Motore Analitico Embedded DuckDB & Archiviazione Apache Parquet (`core/duckdb_engine.py`)

Il modulo integra un database analitico vettorizzato colonnare in-process per abilitare interrogazioni OLAP a latenza sub-millisecondo ed esportazioni ad alta efficienza di memoria.

### 1. Architettura Vettorizzata SIMD (OLAP vs OLTP)
- **OLTP Tradizionale (MySQL/SQLite)**: Memorizzazione per riga (Row-Oriented). Ottimale per inserimenti/aggiornamenti singoli, ma inefficiente per aggregazioni su milioni di record a causa dell'overhead di decodifica di ogni singola riga.
- **DuckDB Vectorized Engine (C++)**: Elaborazione colonnare in vettori di dimensione fissa (solitamente 2048 elementi). I cicli di calcolo sfruttano i registri SIMD (Single Instruction Multiple Data: AVX-512, NEON) della CPU per elaborare simultaneamente decine di valori numerici per ciclo di clock.

### 2. Registrazione Zero-Copy Arrow/Pandas
Le strutture dati in memoria (`st.session_state.portfolio_data`) vengono registrate direttamente nel motore DuckDB tramite puntatori Arrow (`con.register('positions', df)`) senza duplicazione fisica in RAM, garantendo latenze di esecuzione $< 1 \text{ ms}$.

### 3. Cubi Multi-Dimensionali e Window Functions con QUALIFY
1. **Cubo di Rischio Multi-Dimensionale (`GROUPING SETS`)**:
   Calcolo simultaneo di tutti i subtotali di esposizione per `Asset Class`, `Settore GICS` e `Valuta`:
   ```sql
   SELECT asset_class, sector, currency,
          COUNT(*) as n_positions,
          SUM(market_value) as total_exposure,
          AVG(pnl_pct) as avg_return
   FROM positions
   GROUP BY GROUPING SETS ((asset_class, sector, currency), (asset_class), (sector), ());
   ```
2. **Ranking Settoriale con `QUALIFY` e `DENSE_RANK()`**:
   Estrazione immediata dei migliori e peggiori asset per settore senza sottoquery nidificate:
   ```sql
   SELECT ticker, sector, pnl_pct,
          DENSE_RANK() OVER (PARTITION BY sector ORDER BY pnl_pct DESC) as sector_rank
   FROM positions
   QUALIFY sector_rank <= 3;
   ```

### 4. Compressione Colonnare Apache Parquet
La serializzazione del portafoglio nel formato binario aperto Apache Parquet sfrutta:
- **Dictionary Encoding**: Sostituzione di stringhe ripetitive (settori, valute) con indici interi compatti a 1-2 byte.
- **Snappy Compression**: Algoritmo di compressione lossless ad altissimo throughput di decompressione (> 250 MB/s per core).
- **Risparmio di Storage**:
  

$$
\text{Storage Savings} = 1 - \frac{\text{Dimensione}_{\text{Parquet}}}{\text{Dimensione}_{\text{CSV}}} \approx 85\%
$$

- **Column Pruning & Predicate Pushdown**: In lettura, il motore carica esclusivamente le colonne referenziate nella query, saltando i blocchi di byte irrilevanti tramite metadati di pagina (min/max bounds).

---

## 49. Modello Parametrico Nelson-Siegel per la Curva dei Rendimenti (`core/yield_curve.py`)

Il modulo implementa il modello parametrico a 4 parametri di **Nelson-Siegel (1987)** per l'interpolazione ed estrapolazione continua della struttura a termine dei tassi d'interesse zero-coupon privi di rischio (*Risk-Free Term Structure*).

### 1. Formulazione Matematica
Il tasso zero-coupon spot continuo $y(t)$ per una scadenza temporale $t > 0$ (espressa in anni) è espresso come combinazione lineare di tre componenti economiche:

$$
y(t) = \beta_0 + \beta_1 \left( \frac{1 - e^{-t/\tau}}{t/\tau} \right) + \beta_2 \left( \frac{1 - e^{-t/\tau}}{t/\tau} - e^{-t/\tau} \right)
$$

Dove:
- **$\beta_0$ (Livello / Long-Term Level)**: Rappresenta il tasso asintotico di lungo termine per $t \to \infty$. Determina lo shift parallelo della curva.
- **$\beta_1$ (Pendenza / Slope)**: Controlla l'inclinazione della curva a breve termine. Per $t \to 0$, il tasso spot converge a $\beta_0 + \beta_1$ (Short Rate). Se $\beta_1 < 0$, la curva è normalmente inclinata verso l'alto (*Normal Yield Curve*); se $\beta_1 > 0$, la curva è invertita (*Inverted Yield Curve*).
- **$\beta_2$ (Curvatura / Humdrum)**: Modella la convessità/gobba intermedia (*Hump/Trough*) della term structure.
- **$\tau$ (Parametro di Scala / Decay Factor)**: Determina la posizione temporale esatta in cui la funzione di curvatura raggiunge il suo massimo ($\tau \approx t_{\text{peak}}$).

### 2. Calibrazione Numerica OLS Condizionata
Fissato un valore candidato di $\tau$ su una griglia densa $\tau \in [0.2, 5.0]$, il modello risulta **perfettamente lineare** nei coefficienti $(\beta_0, \beta_1, \beta_2)$:

$$
\mathbf{X}(\tau) = \begin{bmatrix} 1 & f_1(t_1, \tau) & f_2(t_1, \tau) \\ \vdots & \vdots & \vdots \\ 1 & f_1(t_N, \tau) & f_2(t_N, \tau) \end{bmatrix}
$$

La stima dei coefficienti ottimali viene eseguita istantaneamente tramite Ordinary Least Squares (OLS):

$$
\hat{\boldsymbol{\beta}}(\tau) = (\mathbf{X}^T \mathbf{X})^{-1} \mathbf{X}^T \mathbf{y}
$$

Il valore ottimale $\tau^*$ viene selezionato massimizzando il coefficiente di determinazione $R^2$ (o minimizzando il Root Mean Square Error, $\text{RMSE}$).

### 3. Fattori di Sconto Continui (Discount Factors)
Dalla curva continua dei rendimenti stimata $y(t)$, il fattore di sconto $DF(t)$ per attualizzare flussi di cassa alla data $t$ è calcolato in capitalizzazione continua:

$$
DF(t) = \exp(-y(t) \cdot t)
$$

I fattori di sconto $DF(t) \in (0, 1]$ risultano strettamente decrescenti con la maturità $t$, garantendo l'assenza di arbitraggi temporali.

---

## 50. Decomposizione del Rischio di Eulero & Marginal VaR (`core/risk_engine.py`)

Poiché il Value at Risk (VaR) e la deviazione standard di portafoglio sono funzioni omogenee di grado 1 rispetto ai pesi di allocazione $\mathbf{w}$, per il **Teorema di Eulero per funzioni omogenee** il rischio totale di portafoglio può essere esattamente scomposto nella somma dei contributi marginali dei singoli asset senza residui:

$$
\text{VaR}_p = \sum_{i=1}^N w_i \cdot \frac{\partial \text{VaR}_p}{\partial w_i}
$$

### 1. Marginal VaR ($\text{MVaR}_i$)
Rappresenta la derivata prima parziale del VaR di portafoglio rispetto al peso dell'asset $i$-esimo:

$$
\text{MVaR}_i = \frac{\partial \text{VaR}_p}{\partial w_i} = z_\alpha \cdot \frac{(\boldsymbol{\Sigma} \mathbf{w})_i}{\sigma_p}
$$

### 2. Component VaR ($\text{CVaR}_i$)
Quantifica l'ammontare monetario assoluto (o percentuale) di rischio apportato dalla posizione $i$-esima al portafoglio complessivo:

$$
\text{CVaR}_i = w_i \cdot \text{MVaR}_i
$$

$$
\text{Contributo pct Rischio}_i = \frac{\text{CVaR}_i}{\text{VaR}_p} \times 100\%
$$

Proprietà di chiusura esatta:

$$
\sum_{i=1}^N \text{Contributo pct Rischio}_i = 100.0\%
$$

---

## 51. Liquidity-Adjusted Value at Risk (LVaR - Bangia / Basel III) (`core/risk_engine.py`)

Il VaR tradizionale ipotizza che le posizioni possano essere liquidate istantaneamente a prezzi mid-market senza costi di attrito. Il modello **LVaR** estende il profilo di rischio considerando l'orizzonte effettivo di smobilizzo $T$ e l'impatto esogeno del bid-ask spread medio di mercato $S$:

$$
\text{LVaR} = \text{VaR}_1 \cdot \sqrt{T} + \frac{1}{2} \cdot V_{\text{port}} \cdot \left( \bar{S} + z_\alpha \cdot \sigma_S \right)
$$

Dove:
- $\text{VaR}_1 \cdot \sqrt{T}$: VaR di mercato scalato temporalmente per l'orizzonte di liquidazione ordinata a $T$ giorni.
- $\frac{1}{2} \cdot V_{\text{port}} \cdot \bar{S}$: Costo atteso di attraversamento dello spread (Costo di Liquidità Esogeno).
- **Premio Illiquidità**:

$$
\text{Premio Illiquidità (pct)} = \frac{\text{LVaR} - \text{VaR}_1}{\text{VaR}_1} \times 100\%
$$

---

## 52. Analisi Obbligazionaria Istituzionale & Credit Default Swap (YAS Cockpit) (`core/yield_curve.py`)

### 1. Prezzo Obbligazionario e Yield to Maturity (YTM)
Dati il valore nominale $F$, la cedola annua $C$, la frequenza $m$, la maturità $T$ e il prezzo di mercato $P$, il rendimento a scadenza $y$ (YTM) risolve per via numerica (algoritmo di Newton-Raphson/Brent) l'equazione:

$$
P = \sum_{k=1}^{m \cdot T} \frac{C/m}{\left(1 + \frac{y}{m}\right)^k} + \frac{F}{\left(1 + \frac{y}{m}\right)^{m \cdot T}}
$$

### 2. Duration, Convessità & DV01
- **Macaulay Duration**:

$$
D_{\text{mac}} = \frac{1}{P} \sum_{k=1}^{m \cdot T} t_k \cdot \text{PV}(CF_k)
$$

- **Modified Duration**:

$$
D_{\text{mod}} = \frac{D_{\text{mac}}}{1 + y/m}
$$

- **Convexity**:

$$
C = \frac{1}{P \left(1 + \frac{y}{m}\right)^2} \sum_{k=1}^{m \cdot T} \frac{t_k (t_k + 1/m) \cdot CF_k}{\left(1 + \frac{y}{m}\right)^{m \cdot t_k}}
$$

- **DV01 (Dollar Value of an 01 / PVBP)**:

$$
\text{DV01} = P \cdot D_{\text{mod}} \cdot 0.0001
$$

- **Espansione di Taylor di 2° Ordine**:

$$
\frac{\Delta P}{P} \approx -D_{\text{mod}} \cdot \Delta y + \frac{1}{2} \cdot C \cdot (\Delta y)^2
$$

### 3. Z-Spread (Zero-Volatility Spread)
Lo spread costante $z$ (espresso in bps) da aggiungere a ciascun nodo della curva spot sovrana $r(t)$ tale per cui:

$$
P_{\text{mkt}} = \sum_{k=1}^N \frac{CF_k}{\left(1 + \frac{r(t_k) + z}{m}\right)^{m \cdot t_k}}
$$

### 4. Modello Credit Default Swap (Hazard Rate & Default Probability)
Dato lo spread CDS a 5 anni $S_{\text{CDS}}$ e il Recovery Rate $R = 40\%$, l'intensità di default (Hazard Rate $\lambda$) e la probabilità cumulativa di default su orizzonte $t$ sono date da:

$$
\lambda = \frac{S_{\text{CDS}}}{1 - R}
$$

$$
PD(t) = 1 - e^{-\lambda \cdot t}
$$

---

## 53. Real-Time High-Frequency Streaming Engine & Level-2 Book (`core/streaming_engine.py`)

### 1. Ring Buffer O(1) FIFO Thread-Safe
Struttura dati circolare a memoria fissa pre-allocata con puntatore atomico di scrittura per ingestione ad alta frequenza di stream di tick senza allocazione dinamica o overhead di garbage collection.

### 2. Stoikov Microprice (2018) & Depth Imbalance
Dato l'order book L2 con i migliori livelli di denaro $(P_b, Q_b)$ e lettera $(P_a, Q_a)$:

$$
\text{Mid Price} = \frac{P_a + P_b}{2}
$$

$$
\text{Depth Imbalance} = \frac{Q_b - Q_a}{Q_b + Q_a} \in [-1, +1]
$$

$$
\text{Microprice} = \frac{Q_b \cdot P_a + Q_a \cdot P_b}{Q_b + Q_a} = P_b + \left(\frac{Q_b}{Q_b + Q_a}\right) \cdot (P_a - P_b)
$$

Il microprice anticipa la direzione immediata del prezzo d'equilibrio incorporando la pressione asimmetrica della liquidità presente sul book.

---

## 54. Motore di Formula EQS Bloomberg-Style (`core/screener_engine.py`)

### 1. Parsing ed Esecuzione Vettorializzata di Formule Arbitrarie
Il motore `evaluate_custom_screener_query` supporta espressioni logico-matematiche complesse composte dall'utente (es. `Piotroski >= 7 AND Altman > 2.9 AND ROIC > WACC * 1.5 AND Beta < 1.0`).

1. **Normalizzazione Operatori**: Conversione case-insensitive di `AND` $\to$ `&`, `OR` $\to$ `|`, `NOT` $\to$ `~` ed eguaglianze `=` $\to$ `==`.
2. **Risoluzione Alias Elastica**: Mappatura biunivoca di oltre 35 alias finanziari (`Piotroski`, `Altman`, `ROE`, `PE`, `PEG`, `PB`, `DivYield`, `FCFYield`, `DebtToEquity`, `Beta`, `Vol`, `Sharpe`, `RSI`, `SMA200`, `Perf1Y`, `Score`).
3. **Valutazione AST Protetta**: Esecuzione sandbox vettorizzata tramite motore Python con isolamento da injection e feedback di sintassi in tempo reale.

---

## 55. Modello di Traiettoria Ottimale di Liquidazione Almgren-Chriss (`core/risk_engine.py`)

### 1. Dinamica di Impatto di Mercato (Almgren & Chriss, 2000)
Dato un portafoglio di $X_0$ quote/valore da liquidare su un orizzonte $T$ suddiviso in $N$ intervalli $\tau = T/N$:
- **Impatto Permanente**:

$$
\gamma \cdot \frac{\sigma_{\text{daily}}}{\text{ADV}}
$$

 (spostamento duraturo del prezzo mid-market).
- **Impatto Temporaneo**:

$$
\eta \cdot \frac{\sigma_{\text{daily}}}{\text{ADV}}
$$

 (attrito istantaneo da svuotamento del book ordini).
- **Parametro di Urgenza ($\kappa$)**:
  

$$
\kappa \tau = \operatorname{arccosh}\left( 1 + \frac{\lambda \sigma^2 \tau^2}{2 \eta} \right) \approx \sqrt{\frac{\lambda \sigma^2}{\eta}} \cdot \tau
$$

### 2. Traiettoria Ottimale e Half-Life
La quota residua al tempo $t_j = j \cdot \tau$ è governata dalla funzione iperbolica:

$$
x(t_j) = X_0 \cdot \frac{\sinh(\kappa (T - t_j))}{\sinh(\kappa T)}
$$

$$
\text{Half-Life di Liquidazione } t_{1/2} = \frac{\ln(2)}{\kappa}
$$

### 3. Costo Atteso $E[x]$, Varianza $V[x]$ e VaR di Esecuzione al 95%

$$
E[x] = \frac{1}{2} \gamma X_0^2 + \tau \eta \sum_{j=1}^N v_j^2 + \frac{\text{Spread}}{2} \cdot X_0
$$

$$
V[x] = \sigma_{\text{daily}}^2 \tau \sum_{j=1}^N x_j^2
$$

$$
\text{Execution VaR}_{95\%} = E[x] + 1.645 \cdot \sqrt{V[x]}
$$

---

## 56. Backtesting di Strategie Multi-Fattoriali a 5 Quintili (`core/factor_library.py`)

### 1. Partizionamento dell'Universo & Ribilanciamento Periodico
A ogni nodo di ribilanciamento temporale $t$ (mensile o trimestrale), l'intero universo azionario viene ordinato in base allo score del fattore accademico selezionato:
- **Q1 (Top 20% · High Factor)**: Paniere dei titoli con massima esposizione desiderata (es. Quality-Minus-Junk, Low-Beta, High Profitability).
- **Q2, Q3, Q4**: Panieri intermedi di transizione.
- **Q5 (Bottom 20% · Junk / High Risk)**: Paniere dei titoli con minima qualità o massima speculazione.

### 2. Spread Long-Short & Test di Monotonicità di Spearman
- **Rendimento dello Spread Long-Short**:

$$
R_{\text{L/S}, t} = R_{Q1, t} - R_{Q5, t}
$$

- **Information Ratio di Q1 vs Universo**:

$$
\text{IR} = \frac{\text{mean}(R_{Q1} - R_{\text{Univ}})}{\text{std}(R_{Q1} - R_{\text{Univ}})} \cdot \sqrt{252}
$$

- **Coefficiente di Monotonicità di Spearman ($r_s$)**: Misura la correlazione di rango decrescente tra i quintili $1 \dots 5$ e il rendimento medio annualizzato:
  

$$
r_s = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}
$$

---

## 57. ARGUS BQuant In-Memory Python Sandbox & DuckDB SQL (`core/bquant_engine.py`)

### 1. Architettura di Esecuzione Sandboxed In-Memory
La console BQuant (Bloomberg Quant parity) consente l'esecuzione di script analitici Python direttamente sui DataFrame in-memory della sessione attiva senza overhead di serializzazione o persistenza intermedia su disco:
- **Namespace Injection**: Iniezione automatica delle strutture di mercato e portafoglio:
  - `df_positions`: tabella dettagliata delle posizioni aperte, pesi percentuali, PnL e classificazione GICS.
  - `df_returns`: matrice dei rendimenti storici logaritmici e percentuali per asset e benchmark.
  - `df_prices`: serie temporali dei prezzi di chiusura rettificati.
  - `results`: dizionario generale delle metriche di rischio VaR/CVaR, Fama-French ed elasticità di stress test.
- **DuckDB SQL Engine Integrato**: Registrazione automatica delle tabelle pandas in una sessione in-process DuckDB (`:memory:`) per consentire aggregazioni OLAP complesse, window functions e query SQL ANSI a latenza sub-millisecondo.
- **Intercettazione Dinamica degli Output**:
  - Reindirizzamento dei flussi `sys.stdout` e `sys.stderr` verso il log visuale del terminale.
  - Rilevamento automatico di variabili DataFrame assegnate a `df_out` o `df_result` con rendering in tabella interattiva ed esportazione CSV.
  - Rilevamento automatico di figure Plotly (`fig`, `figure`) o grafici Matplotlib attivi con rendering grafico ad alta risoluzione.

---

## 58. ARGUS Launchpad & Institutional Role Workspace Profiles (`core/workspace_engine.py`)

### 1. Personalizzazione dei Layout Operativi per Ruolo Organizzativo
Il modulo Launchpad struttura l'accesso ai moduli della piattaforma in base a 5 profili operativi istituzionali predefiniti:
1. **Trading Desk & Execution (`#ff9900`)**: Focus su microstructure ad alta frequenza, order book L2, Order Flow Imbalance (OFI), microprice Stoikov, traiettorie di liquidazione Almgren-Chriss e coperture delta-hedging. Refresh rate consigliato: 5s.
2. **Risk Officer & Compliance (`#f85149`)**: Focus su limiti normativi Basel III/IV, backtesting VaR Kupiec/Christoffersen, volatilità condizionale GARCH(1,1), stress testing macroeconomico 3D e LVaR Bangia. Refresh rate consigliato: 60s.
3. **Portfolio Manager & CIO (`#58a6ff`)**: Focus su frontiera efficiente Markowitz & Hierarchical Risk Parity (HRP), attribuzione di performance Brinson/Carino, factor backtest a quintili e flussi cedolari. Refresh rate consigliato: 30s.
4. **Quantitative Analyst & Data Scientist (`#d2a8ff`)**: Focus su sandbox Python BQuant, calibrazione Merton Jump-Diffusion, superfici di volatilità SVI/Spline e clustering non supervisionato K-Means. Esecuzione on-demand.
5. **Corporate Treasurer & Fixed Income (`#3fb950`)**: Focus su Yield to Maturity (YTM), Duration/Convexity/DV01, Z-Spread Nelson-Siegel, monitoraggio CDS sovrano/corporate e ottimizzazione fiscale minusvalenze. Refresh rate consigliato: 120s.

### 2. Persistenza Locale su SQLite
I layout utente, i ruoli attivi e le configurazioni personalizzate vengono salvati nella tabella `user_workspaces` del database SQLite locale (`data/argus_workspaces.db`), garantendo continuità operativa tra le sessioni.

---

## 59. Bloomberg-Style Excel Live Connector UDFs & Multi-Sheet Architecture (`core/excel_connector.py`)

### 1. Formule UDF Bloomberg Parity per Microsoft Excel e Google Sheets
Il connettore genera formule pronte all'uso conformi alla sintassi Bloomberg Professional:
- **`=ARGUS_BDP(Ticker, Field)`**: Bloomberg Data Point istantaneo (es. `=ARGUS_BDP("AAPL", "LAST_PRICE")`, `=ARGUS_BDP("IT10Y", "YTM")`, `=ARGUS_BDP("MSFT", "BETA")`).
- **`=ARGUS_BDH(Ticker, Field, StartDate, EndDate)`**: Bloomberg Data History per serie storiche (es. `=ARGUS_BDH("AAPL", "CLOSE", "2024-01-01", "2026-08-01")`).
- **`=ARGUS_RISK(MetricName)`**: Metrica di rischio di portafoglio (es. `=ARGUS_RISK("PORTFOLIO_VAR_95")`, `=ARGUS_RISK("PORTFOLIO_SHARPE")`).

### 2. Generatore di Codice VBA & Office Scripts (TypeScript)
- **VBA Macro Module (`.bas`)**: Funzioni UDF per Excel Desktop basate su chiamate non bloccanti `MSXML2.ServerXMLHTTP.6.0` all'endpoint locale di ARGUS (`/api/bdp`, `/api/risk`).
- **Microsoft Office Scripts (`.ts`)**: Script asincrono TypeScript per Excel 365 e Web per sincronizzare e formattare automaticamente snapshot di portafoglio tramite `fetch()`.

### 3. Esportazione Multi-Foglio OpenPyXL / XlsxWriter
Generazione automatica di workbook Excel strutturati con formattazione istituzionale Bloomberg Dark Palette e larghezze di colonna auto-adattate:
- `Executive_Summary`: KPI generali di rischio, Sharpe, VaR, CVaR e tasso risk-free.
- `Positions_Portfolio`: Tabella integrale delle posizioni con pesi, PnL e moltiplicatori.
- `Fixed_Income_YAS`: Duration, Convessità, DV01 e Z-Spread delle emissioni obbligazionarie.
- `Execution_Schedule`: Scaglioni temporali e costi di impatto del modello Almgren-Chriss.

---

## 60. Superficie di Frontiera Efficiente 3D & Campionamento Multi-Alpha Dirichlet (`core/risk_engine.py`)

### 1. Iperspazio Quantitativo a 3 Dimensioni
Nelle tradizionali analisi di Markowitz, la frontiera è proiettata nello spazio bidimensionale $(\sigma_p, R_p)$. ARGUS estende l'analisi al volume tridimensionale introducendo una terza dimensione quantitativa $Z$:
- **Indice di Concentrazione HHI (Herfindahl-Hirschman Index)**:
  

$$
HHI = \sum_{i=1}^N w_i^2 \in \left[ \frac{1}{N}, 1.0 \right]
$$

  Permette di mappare l'iperspazio da portafogli perfettamente equi-pesati ($HHI = 1/N$) a portafogli iper-concentrati su singoli asset ($HHI \to 1.0$).
- **Tail Risk (CVaR 95% / Expected Shortfall)**:
  Quantifica la perdita attesa nella coda estrema del 5% per ciascuna combinazione di pesi.
- **Sortino Ratio (Downside Volatility Efficiency)**:
  Misura l'efficienza ponderata esclusivamente sulla semi-deviazione standard negativa.

### 2. Algoritmo di Campionamento Multi-Alpha Dirichlet con Sparse Masking
Il campionamento uniforme standard $U(0,1)$ concentra la quasi totalità dei punti campionati attorno al baricentro ($1/N$). Per generare una vera cupola volumetrica continua nello spazio $3D$, ARGUS implementa un campionamento composito:
1. **Multi-Concentration Dirichlet**: Variazione dinamica del parametro di concentrazione $\alpha \in [0.05, 5.0]$ per esplorare sia le zone interne del simplesso che le regioni periferiche.
2. **Sparse Subset Masking**: Selezione casuale di sottoinsiemi sparsi di $k < N$ asset per garantire la presenza di portafogli realistici a concentrazione medio-alta.
3. **Vertici Puri**: Inclusione deterministica dei portafogli monomarca ($w_i = 1$) per ancorare i limiti massimi della superficie.

---

## 61. Suite Fiscale Avanzata TUIR, Dichiarativo & Withholding Tax a 4 Pilastri (`core/tax_engine.py`)

### 1. Pilastro 1: Simulatore Riforma Fiscale 2026 (Armonizzazione ETF)
* **Quadro Attuale (TUIR Art. 67)**: I proventi da ETF sono classificati come *Redditi di Capitale* e tassati al 26% alla fonte, senza possibilità di compensare le perdite pregresse (*Redditi Diversi*).
* **Quadro Post-Riforma**: Unificazione di tutti i redditi finanziari in un'unica categoria di redditi da capitale/diversi.
* **Formulazione del Tax Drag Asimmetrico**:
  

$$
\text{Tax Drag}_{\text{ETF}} = \text{Tax}_{\text{Attuale}} - \text{Tax}_{\text{Riformata}} = \max\left(0, \min(\text{Gain}_{\text{ETF}}, \text{Minus}_{\text{Disponibili}} - \text{Gain}_{\text{Diversi}}) \times 0.26\right)
$$

### 2. Pilastro 2: Prospetto Precompilato Modello Redditi Persone Fisiche (Regime Dichiarativo)
Per gli investitori che operano con intermediari esteri o in regime dichiarativo (IBKR, Degiro, Scalable, Revolut, Crypto Wallets):
* **Quadro RT (Sezione II)**:
  - `RT21`: $\sum (\text{Quantità} \times \text{Prezzo di Vendita})$ (Corrispettivi totali).
  - `RT22`: $\sum (\text{Quantità} \times \text{Costo Fiscale FIFO})$ (Costi rilevanti).
  - `RT23`: $\max(0, RT21 - RT22)$ (Plusvalenza lorda).
  - `RT24`: $\min(RT23, \text{Minus Pregresse})$ (Minusvalenze dedotte).
  - `RT25`: Minusvalenza residua da riportare ai 4 anni successivi.
  - `RT26`: $(RT23 - RT24) \times 0.26$ (Imposta sostitutiva da versare con Codice Tributo F24 **1100**).
* **Quadro RW & Liquidazione IVAFE**:
  - Mappatura codici investimento (1 per titoli esteri, 21 per crypto).
  - Identificazione codice paese ISO (es. 069 USA, 018 DE, 080 CH).
  - Calcolo dell'IVAFE: $IVAFE = \text{Valore Finale al 31/12} \times 0.002$.
  - Applicazione della franchigia di esenzione per debiti complessivi $< 12.00$ €.

### 3. Pilastro 3: Analizzatore Withholding Tax (WHT) & Doppia Imposizione Dividendi Esteri
* **Convenzioni contro le Doppie Imposizioni (DTT) & Modulo W-8BEN**:
  - Tassazione alla fonte estera: $WHT_{\text{USA}} = 15\%$, $WHT_{\text{DE}} = 26.375\%$, $WHT_{\text{CH}} = 35\%$, $WHT_{\text{FR}} = 12.8\%$.
  - Tassazione italiana sul "Netto Frontiera": $T_{\text{IT}} = (\text{Dividendo Lordo} \times (1 - WHT)) \times 0.26$.
  - **Aliquota Effettiva Combinata**:
    

$$
\tau_{\text{eff}} = 1 - (1 - WHT) \times (1 - 0.26)
$$

    *(Per i titoli USA con W-8BEN: $\tau_{\text{eff}} = 1 - 0.85 \times 0.74 = 37.10\%$)*.
* **Tax Drag vs ETF UCITS ad Accumulazione**:
  Gli ETF ad accumulazione trattengono internamente il 15% alla fonte senza subire l'imposta italiana immediata sul netto frontiera fino al realizzo finale, eliminando la perdita di rendimento composto da tassazione anticipata.

### 4. Pilastro 4: Simulatore Pre-Trade "Tax-Smart Lot Sizing" (Lotti FIFO Puntuali)
Consente di simulare lo scarico della coda dei lotti d'acquisto prima di inviare un ordine di vendita a mercato:
- Per ogni lotto $k \in \{1 \dots M\}$ consumato fino al raggiungimento della quantità target $Q$:
  

$$
\text{PnL}_k = q_k \cdot (P_{\text{vendita}} - P_{\text{carico}, k})
$$

  

$$
\text{Imposta}_k = \max(0, \text{PnL}_k \times \tau_k)
$$

- Calcola in tempo reale il nuovo prezzo medio di carico residuo (WACP) delle quote rimanenti in portafoglio.

---

## 62. Smart Order Routing & Algoritmi di Esecuzione Intraday TWAP e VWAP (`core/execution_algo.py`)

### 1. Curva di Liquidità Intraday a "U" (U-Shaped Volume Profile)
La distribuzione dei volumi scambiati durante la sessione ordinaria di contrattazione (09:00 - 17:30) viene modellata come una funzione convessa parametrica con picchi in apertura (Open Rush) e in chiusura (Market-on-Close):

$$
V_{\text{norm}}(t) = 2.4 \cdot (t - 0.45)^2 + 0.35
$$

normalizzata in modo che $\sum_{i=1}^N V_{\text{norm}}(t_i) = 1.0$. Questa profilazione riflette l'evidenza empirica di microstruttura dei mercati regolamentati (Borsa Italiana, NYSE, NASDAQ), dove circa il 35-45% dei volumi giornalieri si concentra nella prima e nell'ultima ora di negoziazione.

### 2. Algoritmo TWAP (Time-Weighted Average Price) con Jitter Anti-Frontrunning
Suddivide un ordine totale $Q$ in $N$ intervalli temporali discreti applicando una leggera perturbazione stocastica $\epsilon_t \sim U(-\delta, \delta)$ (con $\delta = 4\%$) per impedire l'identificazione e il front-running da parte di algoritmi HFT concorrenti:

$$
q_t = \frac{Q}{N} \cdot (1 + \epsilon_t), \quad \text{con vincolo di conservazione } \sum_{t=1}^N q_t = Q
$$

Lo slippage stimato per ciascuna tranche include il costo base del mezzo spread bid-ask sommato alla componente di impatto temporaneo:

$$
\text{Slippage}_{\text{TWAP}}(t) = \text{HalfSpread} + \gamma \cdot \sqrt{\frac{\text{POV}_t}{100}} \times \frac{100}{\sqrt{N}}
$$

### 3. Algoritmo VWAP (Volume-Weighted Average Price) con POV Cap
Pesa le quote da negoziare in ciascuna tranche $t$ proporzionalmente al volume di mercato atteso per quell'intervallo ($V_t = \text{ADV} \cdot V_{\text{norm}}(t)$), vincolando la tranche a un tetto di partecipazione massima (Percentage of Volume Cap, tipicamente $15\%$):

$$
q_t = \min\left( Q \cdot V_{\text{norm}}(t), \; V_t \cdot \text{POV}_{\text{cap}} \right)
$$

Le quote eccedenti il cap vengono redistribuite proporzionalmente sulle tranche con capienza residua per garantire l'esecuzione integrale dell'ordine.

### 4. Modello Microstrutturale TCA di Slippage & Square-Root Law
La stima del Transaction Cost Analysis (TCA) impiega la legge della radice quadrata dell'impatto di mercato (*Square-Root Law*, Bouchaud et al. 2008, Almgren et al. 2005):
- **Esecuzione Blocco Unico a Mercato (Market Order)**:
  L'intero controvalore viene eseguito istantaneamente assorbendo la liquidità disponibile sui primi livelli del book:
  

$$
\text{Slippage}_{\text{Market}} = \text{HalfSpread}_{\text{base}} + \gamma_{\text{mkt}} \cdot \sqrt{\frac{\text{Controvalore}}{\text{ADV}}} \times 10000
$$

  Per ordini che superano l'1% dell'ADV, lo slippage cresce rapidamente verso 20–60 bps.
- **Esecuzione Algoritmica Sliced (VWAP / TWAP)**:
  La frammentazione in $N$ intervalli temporali concede al book il tempo di rigenerare la liquidità tra una tranche e l'altra, abbattendo l'impatto quadratico:
  

$$
\text{Slippage}_{\text{VWAP}} = \text{HalfSpread}_{\text{eff}} + \gamma_{\text{vwap}} \cdot \sqrt{\frac{\text{POV}_{\text{interval}}}{100}} \times \frac{100}{\sqrt{N}}
$$

  riducendo l'attrito complessivo a soli 1.0–2.5 bps.

### 5. Quantificazione del Risparmio Netto
Il differenziale monetario risparmiato tramite esecuzione algoritmica istituzionale è definito da:

$$
\text{Risparmio Netto (EUR)} = \text{Costo}_{\text{Market Order}} - \text{Costo}_{\text{VWAP}} = \text{Controvalore} \times \left( \frac{\text{Slippage}_{\text{Market}} - \text{Slippage}_{\text{VWAP}}}{10000} \right)
$$

---

## 63. Dynamic Portfolio Optimization via Reinforcement Learning (`core/reinforcement_learning.py`)

### 1. Formulazione MDP (Markov Decision Process)
Il ribilanciamento continuo del portafoglio viene formulato come un MDP $(\mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma)$:
- **Spazio degli Stati ($S_t \in \mathbb{R}^{3N}$)**: Include medie rolling dei rendimenti a 25 giorni $\mu_{i,t}$, deviazioni standard rolling $\sigma_{i,t}$ e momentum direzionale $\Delta R_{i,t}$ per ciascuno degli $N$ asset.
- **Spazio delle Azioni ($A_t \in \Delta^{N-1}$)**: Vettore di pesi sul simplesso:

$$
w_t = [w_{1,t}, \dots, w_{N,t}], \quad \sum w_i = 1, \quad w_i \ge 0
$$

generato mediante strato di attivazione Softmax.

### 2. Funzione di Ricompensa Orientata al Sortino Ratio con Attrito di Turnover
La funzione di ricompensa premia il rendimento netto penalizzando quadraticamente le sole perdite (semi-varianza negativa / Downside Risk) e i costi di transazione da turnover:

$$
R_t = r_{p,t} \cdot 100 - \gamma \cdot \max(0, -r_{p,t})^2 \cdot 100 - \lambda \cdot \|w_t - w_{t-1}\|_1
$$

dove $\gamma = 4.5$ è il coefficiente di avversione alle perdite e $\lambda$ è la penalità di turnover.

### 3. Policy Gradient REINFORCE con Baseline di Riduzione della Varianza
I parametri $\theta = \{W_1, b_1, W_2, b_2\}$ della rete neurale Policy Actor vengono aggiornati a fine episodio calcolando il gradiente dei ritorni cumulati scontati:

$$
G_t = \sum_{k=t}^T \gamma^{k-t} R_k
$$

normalizzati con baseline standardizzata per minimizzare la varianza del gradiente:

$$
\nabla_\theta J(\theta) = \mathbb{E}_{\pi_\theta} \left[ \nabla_\theta \ln \pi_\theta(a_t | s_t) \cdot (G_t - b(s_t)) \right]
$$

---

## 64. Motore Quantitativo EQS Screener, Pre-Trade Impact & Smart Sizing Optimization (`core/screener_engine.py`)

### 1. Punteggio Multi-Fattoriale Istituzionale ARGUS Composite Score
Il modello valuta ogni asset candidato sintetizzando quattro pilastri quantitativi ortogonali, ciascuno ponderato al 25%:

$$
\text{ARGUS Score} = 0.25 \cdot S_{\text{Valutazione}} + 0.25 \cdot S_{\text{Qualità}} + 0.25 \cdot S_{\text{Rischio}} + 0.25 \cdot S_{\text{Momentum}}
$$

- **$S_{\text{Valutazione}}$**: Potenziale di rialzo implicito dal consensus target price normalizzato per il differenziale valutario ($\text{Upside } \% = \frac{\text{Target} - P}{P} \times 100$) e PEG Ratio.
- **$S_{\text{Qualità}}$**: Redditività operativa (Return on Equity ROE), margine netto e indice di solvibilità contabile Altman Z-Score integrato con Piotroski F-Score.
- **$S_{\text{Rischio}}$**: Volatilità annualizzata storica ($\sigma_a = \sigma_d \sqrt{252}$), Sharpe Ratio rispetto al benchmark e Max Drawdown a 2 anni.
- **$S_{\text{Momentum}}$**: Performance relativa a 1 anno, posizione del prezzo rispetto alla media mobile SMA 200 e indice di forza relativa RSI 14 oscillatore.

### 2. Simulatore Pre-Trade What-If & Decomposizione del Rischio Marginale
Prima di impegnare capitale a mercato, il motore calcola l'impatto marginale dell'introduzione di una quota $w_{\text{cand}} \in [0.01, 0.30]$ del titolo candidato nel portafoglio reale:

- **Ribilanciamento Vettoriale dei Pesi**:
  
$$
w_{\text{new}} = (1 - w_{\text{cand}}) \cdot w_{\text{current}} + w_{\text{cand}} \cdot e_{\text{cand}}
$$

- **Impatto Marginale su Volatilità e Sharpe Ratio**:
  
$$
\Delta \sigma_p = \sigma(w_{\text{new}}) - \sigma(w_{\text{current}})
$$

$$
\Delta \text{Sharpe} = \frac{R(w_{\text{new}}) - R_f}{\sigma(w_{\text{new}})} - \frac{R(w_{\text{current}}) - R_f}{\sigma(w_{\text{current}})}
$$

- **Diversification Ratio di Choueifaty (2008)**:
  
$$
DR(w) = \frac{\sum_{i=1}^N w_i \cdot \sigma_i}{\sqrt{w^T \Sigma w}}
$$

  Un $\Delta DR > 0$ certifica che il candidato apporta diversificazione decorrelata, riducendo la concentrazione del rischio sistemico.

### 3. Smart Sizing Optimizer (Allocazione Ottima Pre-Trade)
Il modulo determina la quota esatta $w^*$ che massimizza l'efficienza marginale o il Diversification Ratio tramite ottimizzazione vincolata unidimensionale (metodo di Brent / SLSQP):

$$
w^* = \arg\max_{w \in [0.01, 0.25]} \text{Sharpe}(w_{\text{new}}(w))
$$

generando la curva di frontiera continua dell'indice di Sharpe in funzione del peso del candidato.

---

## 65. Riferimenti Bibliografici & Standard Istituzionali

1. **Almgren, R., & Chriss, N. (2000)**. *Optimal execution of portfolio transactions*. Journal of Risk, 3(2), 5-40.
2. **Almgren, R., Thum, C., Hauptmann, E., & Li, H. (2005)**. *Direct estimation of equity market impact*. Risk, 18(7), 58-62.
3. **Bouchaud, J. P., Gefen, Y., Potters, M., & Wyart, M. (2008)**. *Fluctuations and response in financial markets: the subtle nature of "random" price changes*. Quantitative Finance, 4(2), 176-190.
4. **Choueifaty, Y., & Coignard, Y. (2008)**. *Toward Maximum Diversification*. The Journal of Portfolio Management, 35(1), 40-51.
5. **Hasbrouck, J. (2007)**. *Empirical Market Microstructure: The Institutions, Economics, and Econometrics of Securities Trading*. Oxford University Press.
6. **Markowitz, H. (1952)**. *Portfolio Selection*. The Journal of Finance, 7(1), 77-91.
7. **López de Prado, M. (2016)**. *Building Diversified Portfolios that Outperform Out of Sample*. Journal of Portfolio Management, 42(4), 59-69.
8. **Stoikov, S. (2018)**. *The Micro-Price: a High-Frequency Estimator of Future Prices*. Quantitative Finance, 18(12), 1959-1966.
9. **Testo Unico delle Imposte sui Redditi (TUIR)**, D.P.R. 22 dicembre 1986, n. 917, Art. 67 & 68 (Plusvalenze finanziarie, compensazione minusvalenze quadriennali).
10. **Legge 29 dicembre 2022, n. 197 (Legge di Bilancio 2023)** & **Circolare Agenzia delle Entrate n. 30/E del 27 ottobre 2023** (Fiscalità delle cripto-attività).

