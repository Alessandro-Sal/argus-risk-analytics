# Politica di Sicurezza & Compliance (Security Policy)

## Versioni Supportate (Supported Versions)

La sicurezza e l'integrità dei dati patrimoniali e finanziari degli utenti sono priorità assolute per **ARGUS — Institutional Risk & Wealth Intelligence Platform**. Di seguito lo stato delle versioni supportate:

| Versione | Stato Supporto | Note di Sicurezza |
| :--- | :---: | :--- |
| **10.0.x** | :white_check_mark: **Attivo (Latest)** | Multi-User Cloud Vault (PBKDF2-SHA256), Zero-Leakage Tenant Isolation, Supabase SSL Pooler, Fernet Vault, CWE-1236 & PII Masking |
| **9.x** | :white_check_mark: **Attivo** | Suite di sicurezza completa, Universal Ledger, protezione CWE-1236, PII masking, Fernet Vault |
| **8.x** | :warning: Manutenzione | Solo patch critiche; raccomandato l'aggiornamento a v10.0.0 |
| **< 8.0** | :x: Deprecato | Fine supporto ciclo vitale |

---

## Presidi di Sicurezza e Hardening Applicativo

ARGUS implementa un'architettura difensiva a più livelli (*Defense-in-Depth*) concepita secondo gli standard Fintech, WealthTech e le linee guida GDPR (Art. 5, 25 e 32):

### 1. Protezione contro Formula Injection (CWE-1236)
- Tutte le esportazioni tabellari (file CSV, estratti conto, fogli Excel `.xlsx` multi-tab) sono processate dal modulo `core/security_engine.py` (`sanitize_csv_cell`).
- Qualsiasi valore testuale che inizi con caratteri di controllo di calcolo (`=`, `+`, `-`, `@`, tabulazione `\t`, ritorno a capo `\r`) viene neutralizzato anteponendo un apice singolo (`'`), prevenendo l'esecuzione arbitraria di comandi (DDE/Formula Execution) all'apertura dei file in Microsoft Excel, LibreOffice Calc o Google Sheets.

### 2. Riservatezza dei Dati Personali & Minimizzazione PII (GDPR Art. 5/32)
- Le informazioni finanziarie e bancarie identificative vengono automaticamente offuscate dal motore di sanitizzazione:
  - **IBAN bancari**: Vengono visualizzati conservando unicamente le prime 4 cifre (codice paese e cin) e le ultime 4 cifre (es. `IT60****************1234`).
  - **Codici Fiscali / Tax IDs**: Mascherati preservando solo i primi 3 caratteri e le ultime 2 cifre.
  - **Numeri di Conto e Deposito**: Ridotti a identificativi parziali con mascheramento a asterischi.
- È implementata una funzione di anonimizzazione completa (`mask_wealth_dataframe`) per l'esportazione di dossier destinati a terze parti o per scopi dimostrativi.

### 3. Crittografia a Riposo (Data at Rest Encryption)
- Il motore `ArgusDataVault` in `core/security_engine.py` consente la cifratura simmetrica a 128/256-bit dei campi sensibili salvati su database locale (SQLite/DuckDB) o esportazioni JSON tramite standard **Fernet (AES in modalità CBC con firma HMAC-SHA256)**.
- Derivazione della chiave di cifratura tramite **PBKDF2-HMAC-SHA256** con salt crittografico casuale a 16 byte e 100.000 iterazioni standard.

### 4. Zero-Leakage Credential Stripping & AI Isolation
- Tutte le chiavi API (broker, Yahoo Finance, connettori macroeconomici, token LLM OpenAI/Google Gemini) sono caricate esclusivamente tramite variabili d'ambiente (`.env` / `.streamlit/secrets.toml`) e isolate dal filesystem di repository (`.gitignore`).
- Prima dell'inoltro di dati di bilancio o prompt all'AI Copilot e ai modelli LLM esterni, il testo viene analizzato e depurato (`strip_sensitive_headers`) per prevenire la fuga accidentale di token di autenticazione o credenziali di sessione.

### 5. Hot Backup & Disaster Recovery Atomico
- Il modulo `core/backup_engine.py` garantisce snapshot coerenti a caldo del database patrimoniale (`data/argus_wealth.db` e `data/argus_local.db`) tramite le API SQLite Online Backup con checkpointing esplicito del WAL (`PRAGMA wal_checkpoint(TRUNCATE)`).
- Ogni operazione di ripristino genera preliminarmente una copia d'emergenza (`.emergency_pre_restore`) per garantire il rollback immediato in caso di fallimento o corruzione.

### 6. Autenticazione Multi-Utente Cloud & Isolamento Multi-Tenant (v10.0.0)
- **Password Hashing Crittografico**: Le credenziali utente nel database cloud (`argus_cloud_users`) sono protette tramite **PBKDF2-HMAC-SHA256** con 120.000 iterazioni, salt crittografico univoco a 16 byte generato con `secrets.token_hex(16)` e verifica in tempo costante (`hmac.compare_digest`) contro attacchi di timing.
- **Isolamento Rigoroso dei Portafogli (Zero-Leakage Multi-Tenancy)**: Tutte le query SQL sul patrimonio (`core/wealth/wealth_db.py`) e sui portafogli di rischio (`core/db_exporter.py`) applicano un filtro dinamico (`_resolve_isolated_portfolio_filter`) basato sull'identità autenticata in sessione, impedendo qualsiasi accesso trasversale ai dati di altri utenti o al profilo riservato del proprietario (`profile_id = 1`).
- **Connessioni Cloud Cifrate (TLS/SSL)**: Le connessioni verso Supabase PostgreSQL utilizzano obbligatoriamente `sslmode=require` e supporto **BYOD (Bring Your Own Database)** isolato in memoria di sessione.

### 7. Modello di Sicurezza Locale vs Cloud & Escalation Protetta
- **Bypass Locale Confinato**: La modalità di accesso diretto senza password per il titolare (`login_local_owner`) è strettamente limitata all'esecuzione locale su workstation (`is_local_environment()`). Non è esportabile né attivabile in alcun modo su istanze Streamlit Cloud o container accessibili pubblicamente.
- **Transizione Protetta a Supabase Cloud**: Una sessione locale opera con identificativo fittizio `local-owner` e senza token crittografico remoto. Qualora l'utente locale decida di switchare il motore relazionale su **Supabase Cloud (PostgreSQL)** tramite la barra laterale (`Tab 3: Database & Rete`), il sistema intercetta la richiesta (`is_supabase_cloud_authenticated()`) e blocca la connessione, richiedendo obbligatoriamente l'autenticazione con credenziali reali Supabase (GoTrue) per generare un token JWT verificato e garantire che i dati cloud non siano esposti a utenti fisicamente presenti sulla macchina locale privi di autorizzazione.

### 8. Idempotenza di Ingestione & Fingerprinting Transazioni SHA-256 (Anti-Duplicazione)
- **Deterministic Transaction Hashing**: Ogni operazione finanziaria importata da broker esterni (Directa, DeGiro, Fineco, IBKR, Trade Republic, Scalable, eToro, Revolut) o da estratti conto bancari viene associata a un hash univoco deterministico SHA-256 basato sulla quintupla naturale (tx_date, ticker, tx_type, quantity, price, currency).
- **Prevenzione Duplicazioni Contabili**: Ingestioni multiple o accidentali del medesimo estratto conto o report transazioni non creano mai duplicati all\'interno dell\'Universal Ledger contabile o delle tabelle del database patrimoniale (wealth_cashflow, wealth_accounts), garantendo la rigorosa idempotenza delle operazioni contabili e fiscali.

---

## Segnalazione di Vulnerabilità (Responsible Disclosure)

Se identifichi una potenziale vulnerabilità o un rischio di sicurezza all'interno di ARGUS:

1. **Non aprire una issue pubblica su GitHub.**
2. Invia una segnalazione dettagliata via email al maintainer del progetto o apri una segnalazione privata tramite il canale di **GitHub Security Advisories**.
3. Includi nella segnalazione:
   - Descrizione dettagliata della vulnerabilità e impatto stimato (CVSS).
   - Passaggi riproducibili o proof-of-concept (PoC).
   - Componenti o file coinvolti (`core/security_engine.py`, `core/backup_engine.py`, ecc.).
4. Riceverai una conferma di ricezione entro **48 ore**, seguita da aggiornamenti regolari sul rilascio del fix.

---

*La sicurezza dei dati patrimoniali è un impegno continuo.*
