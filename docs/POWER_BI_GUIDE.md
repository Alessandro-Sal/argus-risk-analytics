# Guida all'Integrazione con Microsoft Power BI & Google Looker Studio (Executive Dashboards)

Questa guida illustra come connettere i dati analitici, le metriche di rischio e i dati storici generati da **ARGUS Risk Analytics Platform** a **Microsoft Power BI Desktop** e **Google Looker Studio** per la creazione di report direzionali aziendali.

La piattaforma storicizza ad ogni esecuzione uno snapshot completo sul database relazionale **MySQL/SQLite** ed esporta un pacchetto **Star Schema ZIP** (`dim_assets.csv`, `fact_positions.csv`, `fact_portfolio_summary.csv`) nella cartella `exports/`.

---

## Metodo 1: Importazione del Pacchetto Star Schema ZIP (Consigliato per Power BI & Looker)

Il generatore automatico **`scripts/export_star_schema.py`** crea un archivio `.zip` pronto per la Business Intelligence contenente le 3 tabelle relazionali Star Schema:

### Tabelle del Pacchetto Star Schema
1. **`dim_assets.csv`**: Tabella dimensione degli asset (Ticker, Nome Azienda, Settore GICS, Paese, Asset Class, Valuta).
2. **`fact_positions.csv`**: Tabella fatti posizioni (Snapshot ID, Ticker, Quantità Netta, Costo Medio WACP, Prezzo Attuale, Controvalore €, Peso %, PnL Realizzato/Non Realizzato, Volatilità, Component VaR %, Label Cluster K-Means).
3. **`fact_portfolio_summary.csv`**: Tabella fatti aggregata di portafoglio (Snapshot ID, Data Snapshot, Valore Totale €, PnL Totale €, Sharpe Ratio, Sortino Ratio, Max Drawdown %, VaR 95% Storico/Parametrico/Cornish-Fisher, CVaR 95%, Health Score, Alpha Fama-French).

### Passo 1: Generazione del Pacchetto
Nel Centro Esportazione di ARGUS (in fondo alla pagina *1_📈_Dashboard_Generale.py*) o da terminale:
```bash
py scripts/export_star_schema.py
```
Il file `argus_powerbi_star_schema.zip` verrà salvato nella cartella `exports/`.

### Passo 2: Importazione in Power BI Desktop
1. Apri **Power BI Desktop**.
2. Estrarre il pacchetto `.zip` ed utilizzare **Recupera dati** $\rightarrow$ **Testo/CSV** per ciascuna delle 3 tabelle.
3. Nella vista **Modello** di Power BI, verificare le seguenti relazioni relazionali:
   - `dim_assets[ticker]` $\rightarrow$ `fact_positions[ticker]` (Relazione 1 a Molti, Filtro Unidirezionale).
   - `fact_portfolio_summary[snapshot_id]` $\rightarrow$ `fact_positions[snapshot_id]` (Relazione 1 a Molti, Filtro Unidirezionale).

---

## Metodo 2: Connessione Diretta al Database MySQL

Per gli ambienti enterprise con aggiornamento automatico continuo:

1. In Power BI, seleziona **Recupera dati** $\rightarrow$ **Database MySQL**.
2. Server: `localhost:3306`, Database: `investment_risk_bi`.
3. Seleziona le tabelle ORM: `portfolios`, `portfolio_snapshots`, `snapshot_positions`, `transactions`, `market_prices`.

---

## Metodo 3: Connessione Diretta a Supabase Cloud (PostgreSQL 16) o SQLite Locale

A partire dalla versione **v10.0.0**, ARGUS supporta nativamente il deployment cloud su **Supabase PostgreSQL 16 (AWS EU-West-1)**:

### Connessione Power BI a Supabase PostgreSQL:
1. In Power BI Desktop, seleziona **Recupera dati** $\rightarrow$ **Database PostgreSQL**.
2. **Server**: `aws-0-eu-west-1.pooler.supabase.com:5432` (o porta diretta `6543` per session pooler).
3. **Database**: `postgres`.
4. Inserire le credenziali dell'utente del database e abilitare la crittografia SSL obbligatoria.
5. Selezionare le tabelle relative al proprio profilo:
   - Modulo Trading & Rischio: `portfolios`, `portfolio_snapshots`, `snapshot_positions`, `transactions`.
   - Modulo Wealth & Family Office: `wealth_portfolios`, `wealth_accounts`, `wealth_cashflow`, `wealth_mortgages`, `wealth_physical_assets`.

### Connessione a SQLite Locale:
Per istanze desktop offline (`data/argus_local.db` e `data/argus_wealth.db`), è possibile connettere Power BI Desktop tramite driver **ODBC SQLite3** o esportare il pacchetto Star Schema ZIP periodico.

---

## 🎨 Suggerimenti per la Creazione di Visualizzazioni Direzionali

### 1. Risk Treemap (Esposizione Capitale vs Risk Weight)
- **Visual**: Mappa ad Albero (Treemap).
- **Tabella**: `fact_positions`.
- **Raggruppamento**: `gics_sector` $\rightarrow$ `ticker`.
- **Dimensione Riquadro**: `current_value` (€).
- **Saturazione Colore**: `component_var_pct` %.

### 2. Scatter Plot dei Cluster (Machine Learning Profiling)
- **Visual**: Grafico a Dispersione (Scatter Plot).
- **Tabella**: `fact_positions`.
- **Asse X**: `volatility_pct` (Volatilità annualizzata).
- **Asse Y**: `weight_pct` (Peso di portafoglio %).
- **Dettagli**: `ticker`.
- **Legenda**: `cluster_label`.

### 3. Matrice Multi-Scenario di Stress Testing
- **Visual**: Grafico a barre raggruppate o Card Multi-Riga.
- **Tabella**: `fact_portfolio_summary`.
- **Valori**: Perdita stimata nei 5 scenari (*Dot-Com*, *Lehman*, *US Downgrade*, *COVID*, *Rate Shock*).
