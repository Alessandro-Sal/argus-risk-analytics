# Specifica Tecnica del Formato CSV di Input & Multi-Broker Ingestion Hub

Questo documento fornisce le specifiche tecniche dettagliate per i file CSV di input accettati da **ARGUS Risk Analytics Platform**. Il sistema supporta sia uno standard CSV universale sia le esportazioni native dai principali broker italiani ed internazionali tramite il **Multi-Broker Ingestion Hub** (`core/adapters/broker_hub.py`).

---

## 1. Schema CSV Standard Universale

### Tabella delle Colonne

| Nome Colonna | Obbligatoria | Tipo Dato | Descrizione / Formato | Esempio |
| :--- | :---: | :---: | :--- | :--- |
| `tx_date` | **Sì** | Data | Data dell'operazione (`YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`). | `2024-01-15` |
| `ticker` | **Sì** | Stringa | Ticker Yahoo Finance o codice identificativo ISIN. | `AAPL`, `ISP.MI`, `BTC-USD` |
| `tx_type` | **Sì** | ENUM | Tipo di operazione: `buy`, `sell`, `dividend` o `split`. | `buy`, `split` |
| `quantity` | **Sì** | Numerico | Quantità di quote negoziate. Per `dividend` = 1; per `split` = coefficiente (es. 10 per 10:1). | `10.5` |
| `price` | **Sì** | Numerico | Prezzo unitario di acquisto/vendita. Per dividendi = importo netto; per `split` = coefficiente. | `150.25` |
| `currency` | **Sì** | Stringa | Valuta dell'operazione (codice ISO 3 lettere: `EUR`, `USD`, `GBP`, `CHF`). | `EUR` |
| `fees` | No | Numerico | Commissioni totali pagate per l'operazione (Default: `0.0`). | `2.50` |
| `asset_class` | No | Stringa | Categoria strumento (`Stock`, `ETF`, `Bond`, `Crypto`, `Cash`). Auto-detected se omesso. | `Stock` |
| `notes` | No | Stringa | Note o descrizione opzionale della transazione. | `Piano di accumulo` |

---

## 2. Regole di Gestione dei Dividendi & Stock Split

### A. Dividendi (`tx_type = dividend`)
Nel formato standard dell'applicazione:
- **`quantity`**: Deve essere impostato su **`1`**.
- **`price`**: Rappresenta l'**importo totale netto incassato** dal dividendo espresso nella valuta dell'operazione (non l'importo per singola azione).

### B. Stock Split & Corporate Actions (`tx_type = split`)
- **`quantity`** (o **`price`**): Rappresenta il **rapporto di frazionamento** (es. `10.0` per uno split 10:1, `0.1` per un reverse split 1:10).
- Il motore contabile di ARGUS rettifica retroattivamente tutti i lotti d'acquisto registrati prima della data dello split, moltiplicando le quote per il coefficiente e dividendo il prezzo di carico, mantenendo il **costo fiscale totale (Cost Basis) rigorosamente invariante**.
- *Nota*: La piattaforma esegue inoltre la rilevazione automatica online da Yahoo Finance per gli split storici noti (es. NVDA 10:1, AAPL 4:1, TSLA 3:1).

> ⚠️ **Nota di Validazione (`core/validator.py`)**: Il motore di validazione accetta i 4 tipi operativi ufficiali (`buy`, `sell`, `dividend`, `split`) garantendo coerenza e integrità del database.

---

## 3. Multi-Broker Ingestion Hub & Auto-Detector (`core/adapters/`)

ARGUS include un modulo di auto-rilevamento (**Auto-Detection**) e adapter specifici per convertire automaticamente i file esportati dai principali broker nel formato standard:

| Piattaforma Broker | Adapter Modulo | Formati Supportati & Note |
| :--- | :--- | :--- |
| **Directa SIM** | `core/adapters/directa.py` | Ordini eseguiti ed estratto conto titoli da *dLite* e *Classic*. Normalizza formati numerici italiani con virgola. |
| **Fineco Bank** | `core/adapters/fineco.py` | Movimenti Conto Trading, Ordini Eseguiti e Rendiconto Fiscale. Gestisce intestazioni bancarie multilinea. |
| **Interactive Brokers (IBKR)** | `core/adapters/ibkr.py` | Activity Statement CSV multi-sezione (filtrando selettivamente `Trades,Data,Order`) e Trades Report tabellari. |
| **Trade Republic** | `core/adapters/traderepublic.py` | Estratto conto, transazioni singole, ordini PAC (*Savings Plan / Sparplan*) e dividendi (IT, EN, DE). |
| **Scalable Capital** | `core/adapters/scalable.py` | Esportazioni Baader Bank / Scalable Broker per compravendite, dividendi e PAC ETF. |
| **DeGiro** | `core/adapters/degiro.py` | Report *Attività > Transazioni* (IT, EN, NL) con calcolo automatico del cambio valuta e fee. |

### Riconoscimento Automatico dei Codici ISIN (`core/adapters/isin_resolver.py`)
Per tutti i broker che esportano codici ISIN anziché ticker azionari (es. `IE00B4L5Y983`), il risolutore universale opera su 3 livelli:
1. **Cache di sessione in memoria** per accesso istantaneo.
2. **Mappatura persistente** in `config/config.json` con oltre 30 tra i principali ETF e stock mondiali preconfigurati.
3. **Lookup dinamico live su Yahoo Finance Search API** con auto-apprendimento e memorizzazione automatica nel file di configurazione locale.

---

## 4. Supporto Google Sheets Live Dual Sync (`History B/S Stocks` & `History B/S Crypto`)

ARGUS include un connettore live crittografato tramite Google Service Account in grado di estrarre e separare nativamente due portafogli distinti da un unico foglio di calcolo:

1. **`History B/S Stocks`**:
   - Gestisce compravendite azionarie ed ETF con colonne: `Date`, `Security`, `Action` (Buy/Sell), `Quantity`, `Price`, `Total`.
   - Normalizza automaticamente i ticker su borse internazionali (es. `.MI`, `.PA`, `.AS`, `.CO`, `.L`).
2. **`History B/S Crypto`**:
   - Gestisce transazioni crypto e movimenti di cassa/deposito (`Action = Deposit` / `Security = Cash`).
   - Normalizza i simboli crypto nella valuta di riferimento (es. `BTC` $\rightarrow$ `BTC-EUR`, `ETH` $\rightarrow$ `ETH-EUR`).
   - Isola e serializza i due portafogli in profili separati (`Wealth Stocks Portfolio` e `Wealth Crypto Portfolio`) pronti per il consolidamento Master Wealth.

---

## 5. Esempio File CSV Valido (Standard ARGUS)

```csv
tx_date,ticker,tx_type,quantity,price,currency,fees,asset_class,notes
2023-01-10,AAPL,buy,10,145.50,USD,1.50,Stock,Acquisto iniziale
2023-03-15,ISP.MI,buy,500,2.40,EUR,2.00,Stock,Dividendo value
2023-06-01,AAPL,dividend,1,24.50,USD,0.00,Stock,Dividendo Q2
2023-09-20,AAPL,sell,5,175.00,USD,1.50,Stock,Presa di beneficio parziale
2024-01-15,BTC-USD,buy,0.05,42000.00,USD,5.00,Crypto,Allocazione alternativa
```