# Capstone Project — Scaletta Presentazione Orale & Guida alla Difesa (15 Minuti)

**Candidato**: Studente Master in Data Analytics  
**Titolo Progetto**: *ARGUS — Business Intelligence & Risk Management Platform*  
**Stack Tecnologico**: Python 3.11+, MySQL 8.0 (SQLAlchemy ORM), Streamlit, ReportLab, SciPy, Scikit-Learn, Plotly.

---

## 🎬 Struttura delle 10 Slide di Presentazione

### Slide 1: Titolo & Vision del Progetto
* **Titolo**: ARGUS — Piattaforma Istituzionale di Risk Analytics & Business Intelligence Multi-Asset.
* **Problem Statement**: La frammentazione dei dati di broker differenti e la mancanza di metriche di Tail Risk avanzate nei software retail tradizionali.
* **Obiettivo**: Trasformare transazioni grezze in un framework quantitativo completo con stima di Value at Risk, simulazioni stocastiche e reportistica automatizzata.

---

### Slide 2: Architettura del Sistema a 5 Livelli (ETL ➔ DW ➔ Engine ➔ BI)
* **Diagramma a blocchi**:
  1. *Data Ingestion*: Adapter CSV DeGiro / Generico + API yfinance (Prezzi & Tassi FX).
  2. *ETL & Validation*: Clean pipeline in 11 step con contratti dati Pydantic.
  3. *Data Warehouse*: Schema relazionale MySQL ORM (Tabelle Grezze & Snapshot).
  4. *Quantitative Engine*: FIFO Cost Basis, Cornish-Fisher VaR, SciPy SLSQP Markowitz, Cholesky Monte Carlo, Brinson Attribution, Hedging Engine.
  5. *Presentation Layer*: UI Streamlit (7 pagine), PDF Factsheet 2 Pagine, Multi-Tab Excel, Power BI Star Schema.

---

### Slide 3: Contabilità Portafoglio & Motore FIFO (`_fifo_engine`)
* **Punto di Forza**: Scomposizione analitica a code FIFO per vendite parziali e gestione cambi valuta (EUR/USD/GBP/DKK).
* **Validazione Dati Reali**: Testato su ~400 operazioni reali dal 2021 al 2026 dal progetto WealthApp con precisione centesimale nel PnL.

---

### Slide 4: Misurazione del Rischio di Mercato & Tail Risk (VaR & Backtesting)
* **Value at Risk (VaR)**: Confronto a 3 metodologie (Storico, Parametrico Gaussiano, Cornish-Fisher con correzione Skewness & Kurtosis).
* **Kupiec POF Backtest**: Validazione su 252 giorni con classificazione a semafori dell'Accordo di Basilea (*Zona Verde / Gialla / Rossa*).
* **Ulcer Index (UI)**: Penalizzazione quadratica della durata e profondità del Drawdown sotto l'High-Water Mark.

---

### Slide 5: Ottimizzazione di Markowitz & Ledoit-Wolf Shrinkage
* **Problem / Solution**: La matrice di covarianza campionaria soffre di rumore negli ottimizzatori tradizionali.
* **Ledoit-Wolf Shrinkage**: Contrazione della matrice verso un target ad un fattore per la massima stabilizzazione statistica.
* **Risolutore Vincolato `SciPy SLSQP`**: Risoluzione della Frontiera Efficiente per Max Sharpe e Min Volatility.

---

### Slide 6: Simulazione Monte Carlo Multi-Asset (Decomposizione di Cholesky)
* **Algoritmo**: 10.000 cammini casuali distribuiti su 252 giorni futuri.
* **Decomposizione di Cholesky**: $\Sigma = L \cdot L^T \implies R_{\text{sim}} = \mu + L \cdot Z$. Preserva integralmente le correlazioni storiche tra i titoli durante le proiezioni stocastiche.

---

### Slide 7: Attribuzione delle Performance Brinson-Fachler & Hedging Tattico
* **Brinson-Fachler Model**: Scomposizione dell'Alpha nei 3 fattori: *Allocation Effect*, *Selection Effect*, *Interaction Effect*.
* **Beta-Neutral Hedging Simulator**: Calcolo delle quote di ETF Inversi (`SH`, `PSQ`, `VIXY`) necessarie per azzerare il Beta di portafoglio ($\beta = 0.00$) senza liquidare le azioni.

---

### Slide 8: Modulo Diagnostico ARGUS Quant Advisor & Early Warning
* **Health Score (0-100)**: Punteggio sintetico di salute del portafoglio basato su HHI, Component VaR (> 25%), multipli P/E (> 45x) e Sharpe gain potenziale.
* **Risk Limits Panel**: Controllo in tempo reale di 6 soglie di rischio regolamentari.

---

### Slide 9: Flusso Flussi di Cassa Dividendi & Ottimizzazione Fiscale
* **Calendario Stagionalità Dividendi**: Mappatura sui mesi reali di stacco delle singole società pagatrici (es. Intesa Sanpaolo Maggio/Novembre, Novo Nordisk Marzo/Agosto).
* **Tax-Loss Harvesting Engine**: Calcolo delle imposte dovute (aliquota 26% vs 12.5%) ed individuazione delle minusvalenze compensabili prima di fine anno.

---

### Slide 10: Conclusioni, Impatto di Business & Sviluppi Futuri
* **Risultati Chiave**: Sistema solido con 35 unit test automatizzati PASSED, reportistica istituzionale PDF/Excel in-memory e supporto per Power BI.
* **Sviluppi Futuri**: Integrazione API Broker Live (Interactive Brokers API) e automazione di trading algorithmic Execution.

---

## ❓ Domande Probabili della Commissione & Risposte Vincenti

### Q1: *"Perché avete utilizzato l'espansione di Cornish-Fisher per il VaR al posto del semplice VaR Gaussiano?"*
> **Risposta**: *"I rendimenti finanziari reali non seguono quasi mai una distribuzione normale gaussiana, ma presentano asimmetria (skewness) e code spesse (kurtosis elevate / fat tails). Il VaR Gaussiano tende a sottostimare gravemente il rischio di perdita nelle fasi di crollo. L'espansione di Cornish-Fisher aggiusta il quantile z tenendo conto di skewness e kurtosis, fornendo una stima del rischio di coda immensamente più accurata ed istituzionale."*

### Q2: *"Perché avete applicato la contrazione di Ledoit-Wolf alla matrice di covarianza per Markowitz?"*
> **Risposta**: *"La matrice di covarianza campionaria pura soffre del fenomeno dell'errore di stima campionaria, che porta gli ottimizzatori di Markowitz a prendere posizioni estreme ed instabili ('error maximizers'). La contrazione di Ledoit-Wolf combina la covarianza campionaria con una matrice bersaglio strutturata, riducendo il rumore campionario e producendo pesi ottimi infinitamente più stabili ed eseguibili sul mercato reale."*

### Q3: *"In che modo la Decomposizione di Cholesky preserva le correlazioni nella Simulazione Monte Carlo?"*
> **Risposta**: *"Se generassimo numeri casuali indipendenti per ciascun asset, la simulazione ignorerebbe il fatto che quando ad esempio le Big Tech scendono, tendono a muoversi insieme. Moltiplicando il vettore di shock casuali indipendenti $Z \sim N(0, I)$ per la matrice triangolare inferiore di Cholesky $L$ (derivata dalla matrice di covarianza $\Sigma = L \cdot L^T$), trasformiamo gli shock casuali in variate casuali correlate che rispecchiano la reale dipendenza lineare storica tra gli asset."*

### Q4: *"Come gestisce il sistema la diversa tassazione delle plusvalenze da ETF rispetto ai singoli titoli secondo la normativa italiana (TUIR Art. 67)?"*
> **Risposta**: *"Nel sistema fiscale italiano (TUIR Art. 67), le plusvalenze generate da ETF costituiscono Redditi di Capitale e NON possono essere utilizzate per abbattere le minusvalenze pregresse nello zainetto fiscale (Redditi Diversi). Il nostro motore `core/tax_engine.py` riconosce e separa nettamente gli ETF dai singoli titoli: per gli ETF applica la tassazione al 26% senza compensazione, mentre individua le vere opportunità di Tax-Loss Harvesting esclusivamente sui titoli la cui vendita in perdita genera un risparmio d'imposta reale."*

---

*Guida preparata per la discussione orale del Capstone Project.*
