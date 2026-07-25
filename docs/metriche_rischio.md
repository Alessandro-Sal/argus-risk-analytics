# Calcolo delle Metriche di Rischio e Modelli Finanziari

Questo documento illustra la metodologia, la formulazione matematica e le applicazioni pratiche adottate all'interno del motore di rischio quantitativo (`core/risk_engine.py`) di **Investment Risk BI Platform**. Tutti i calcoli basati su serie storiche considerano i rendimenti giornalieri rettificati (*Adjusted Close*) ed un anno lavorativo standard di 252 giorni di negoziazione.

---

## 1. Motore Contabile FIFO (First-In, First-Out)

Per determinare accuratamente il costo di carico e i profitti/perdite realizzati su portafogli con acquisti e vendite frazionate nel tempo, il sistema implementa un **motore a code FIFO (`_fifo_engine`)**:

1. **Gestione Acquisti**: Ogni operazione di acquisto (`buy`) aggiunge un lotto $(q_i, p_i)$ alla coda FIFO dell'asset.
2. **Gestione Vendite**: Ogni operazione di vendita (`sell`) consuma le quote a partire dai lotti più vecchi nella coda:
   \[ \text{PnL Realizzato} = \sum_{k} q_{\text{venduti}, k} \cdot (p_{\text{vendita}} - p_{\text{acquisto}, k}) - \text{Commissioni} \]
3. **Costo Medio di Carico Residuo (Cost Basis)**:
   \[ \text{Prezzo Medio di Carico (WACP)} = \frac{\sum_{m} q_{\text{residuo}, m} \cdot p_{\text{acquisto}, m}}{\sum_{m} q_{\text{residuo}, m}} \]
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
- **$\beta_{Mkt}$**: Sensibilità sistematica alle fluttuazioni del mercato azionario.
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

### 3. Simulazione Monte Carlo Multi-Asset (Decomposizione di Cholesky)
Genera 10.000 cammini casuali del valore complessivo di portafoglio su 252 giorni futuri:
1. Si calcola la matrice di covarianza storica $\Sigma$.
2. Si applica la **Decomposizione di Cholesky** per ottenere la matrice triangolare inferiore $L$ tale che $\Sigma = L \cdot L^T$.
3. Per ogni passo temporale, si generano rendimenti casuali correlati:
   \[ R_{\text{sim}} = \mu + L \cdot Z, \quad Z \sim N(0, I) \]
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
   - **Multipli P/E Elevati ($P/E > 45x$)**: Segnalazione d'alert per titoli ad alta valutazione fondamentali.
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

Consente il tracciamento della serie storica degli snapshot salvati a Data Warehouse MySQL (`portfolio_snapshots` e `snapshot_positions`):

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
   - **Azioni, Obbligazioni, ETC, ETN, Derivati**: Generano *Redditi Diversi*. Le plusvalenze di questa categoria **possono essere compensate** con le minusvalenze pregresse nello zainetto fiscale (valibile 4 anni).
   - **ETF**: Generano *Redditi di Capitale*. Le plusvalenze da ETF **NON possono essere utilizzate per abbattere le minusvalenze** presenti nello zainetto fiscale.

3. **Tax-Loss Harvesting Strategy**:
   - Identifica le posizioni in perdita latente su singoli titoli (*Redditi Diversi*) che possono essere liquidate strategicamente prima della fine dell'anno fiscale per azzerare l'imposta dovuta sulle plusvalenze realizzate nello stesso anno solare.
