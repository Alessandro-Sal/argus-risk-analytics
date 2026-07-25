# Specifica Tecnica del Formato CSV di Input & Supporto DeGiro

Questo documento fornisce le specifiche tecniche dettagliate per i file CSV di input accettati da **Investment Risk BI Platform**. Il sistema supporta sia uno standard CSV universale sia le esportazioni native dal broker **DeGiro** tramite l'adapter integrato (`core/adapters/degiro.py`).

---

## 1. Schema CSV Standard Universale

### Tabelle delle Colonne

| Nome Colonna | Obbligatoria | Tipo Dato | Descrizione / Formato | Esempio |
| :--- | :---: | :---: | :--- | :--- |
| `tx_date` | **Sì** | Data | Data dell'operazione (`YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`). | `2024-01-15` |
| `ticker` | **Sì** | Stringa | Ticker Yahoo Finance o codice identificativo ISIN. | `AAPL`, `ISP.MI`, `BTC-USD` |
| `tx_type` | **Sì** | ENUM | Tipo di operazione: `buy`, `sell`, o `dividend`. | `buy` |
| `quantity` | **Sì** | Numerico | Quantità di quote negoziate. Per i dividendi, impostare `1`. | `10.5` |
| `price` | **Sì** | Numerico | Prezzo unitario di acquisto/vendita. Per i dividendi, l'importo totale net. | `150.25` |
| `currency` | **Sì** | Stringa | Valuta dell'operazione (codice ISO 3 lettere: `EUR`, `USD`, `GBP`, `CHF`). | `EUR` |
| `fees` | No | Numerico | Commissioni totali pagate per l'operazione (Default: `0.0`). | `2.50` |
| `asset_class` | No | Stringa | Categoria strumento (`Stock`, `ETF`, `Bond`, `Crypto`, `Cash`). Auto-detected se omesso. | `Stock` |
| `notes` | No | Stringa | Note o descrizione opzionale della transazione. | `Piano di accumulo` |

---

## 2. Regole di Gestione dei Dividendi (`tx_type = dividend`)

Nel formato standard dell'applicazione:
- **`quantity`**: Deve essere impostato su **`1`**.
- **`price`**: Rappresenta l'**importo totale incassato** dal dividendo espresso nella valuta dell'operazione (non l'importo per singola azione).

> ⚠️ **Nota di Validazione (`core/validator.py`)**: Il motore di validazione garantisce che le righe con `tx_type = dividend` non subiscano alterazioni o rettifiche di quantitativo, preservando l'integrità del flusso di cassa generato dai dividendi.

---

## 3. Gestione dei Casi Limite (Edge Cases)

La pipeline ETL esegue i seguenti passaggi di normalizzazione automatica durante la fase di ingestion:

1. **Date Multi-Formato**: Conversione automatica di `DD/MM/YYYY` e `MM/DD/YYYY` nel formato standard ISO 8601 `YYYY-MM-DD`.
2. **Separatori Decimali**: Supporto sia per il punto (`150.25`) che per la virgola italiana (`150,25`).
3. **Ticker Crypto**: Auto-fix dei codici crypto incompleti (es. `BTC` o `ETH` vengono automaticamente convertiti in `BTC-USD` e `ETH-USD`).
4. **Mappatura ISIN $\rightarrow$ Ticker**: Qualora nel campo `ticker` venga inserito un codice ISIN (es. `IE00B4K48X80`), il sistema utilizza la mappa persistente `config.json` e le API di Yahoo Finance per risolvere il ticker di negoziazione corrispondente (`IMEA.SW`).

---

## 4. Supporto Native Export Broker DeGiro (`core/adapters/degiro.py`)

La piattaforma include un adapter dedicato per importare direttamente l'export delle transazioni esportato dalla dashboard di **DeGiro** senza richiedere alcuna riattrezzatura manuale.

### Mappatura Campi DeGiro $\rightarrow$ Schema Standard

| Campo Export DeGiro | Campo Schema Standard | Trasformazione Applicata |
| :--- | :--- | :--- |
| `Data` + `Ora` | `tx_date` | Parsing della data in formato ISO `YYYY-MM-DD`. |
| `Prodotto` / `ISIN` | `ticker` | Risoluzione da ISIN a Ticker Yahoo Finance via `config.json`. |
| `Numero` | `quantity` | Valore assoluto della quantità negoziata. |
| `Prezzo` | `price` | Prezzo unitario di esecuzione. |
| `Valuta` | `currency` | Codice ISO della valuta originale dell'operazione. |
| `Commissioni` | `fees` | Conversione e somma delle commissioni di negoziazione. |
| `Descrizione` | `tx_type` | Inferenza automatica del tipo: `Acquisto` $\rightarrow$ `buy`, `Vendita` $\rightarrow$ `sell`, `Dividendo` $\rightarrow$ `dividend`. |

---

## 5. Esempio File CSV Valido (Standard)

```csv
tx_date,ticker,tx_type,quantity,price,currency,fees,asset_class,notes
2023-01-10,AAPL,buy,10,145.50,USD,1.50,Stock,Acquisto iniziale
2023-03-15,ISP.MI,buy,500,2.40,EUR,2.00,Stock,Dividendo value
2023-06-01,AAPL,dividend,1,24.50,USD,0.00,Stock,Dividendo Q2
2023-09-20,AAPL,sell,5,175.00,USD,1.50,Stock,Presa di beneficio parziale
2024-01-15,BTC-USD,buy,0.05,42000.00,USD,5.00,Crypto,Allocazione alternativa
```