# 🌐 ARGUS Headless API & Interactive OpenAPI Explorer

L'architettura **Headless Microservice** di ARGUS espone un gateway ad alte prestazioni **FastAPI** (`api/main.py`) con oltre 40 endpoint per la gestione del rischio istituzionale, pricing di derivati esotici, allocazione ottima, reporting regolamentare e audit bitemporale.

---

## ⚡ Caratteristiche Principali del Servizio REST

* **Framework**: FastAPI (Asincrono con Starlette & Uvicorn)
* **Standard di Validazione**: Pydantic v2 (Strict Typing & Sanity Ingestion Gates)
* **Performance**: Calcoli quantitativi NumPy/SciPy/DuckDB vettorizzati con tempi di risposta $< 25\,\text{ms}$
* **Conformità Regolamentare**: Output conforme a Basilea IV (FRTB), ISDA SIMM™ v2.6, Solvency II SCR, e MiFID II RTS 28

---

## 🚀 Avvio Rapido Microservice

Per avviare il gateway REST & WebSocket in locale:

```bash
# Avvio standalone con Uvicorn
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Oppure tramite container Docker dedicato
docker compose up api
```

L'interfaccia interattiva nativa Swagger è disponibile all'indirizzo locale:
* **Swagger UI**: `http://localhost:8000/docs`
* **ReDoc**: `http://localhost:8000/redoc`
* **OpenAPI Schema JSON**: `http://localhost:8000/openapi.json`

---

## 🏛️ Catalogo degli Endpoint Principali

### 1. Market Risk & Tail Analytics
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/api/v1/risk/evaluate` | Calcolo VaR Parametrico, Storico, Cornish-Fisher 95%/99% ed Expected Shortfall |
| `POST` | `/api/v1/risk/euler-decomposition` | Decomposizione additiva del rischio e quadratura di Eulero ($MCTR_i$, $PCTR_i$) |
| `POST` | `/api/v1/risk/garch` | Volatilità condizionale GARCH(1,1) e forecasting ad orizzonte dinamico |
| `POST` | `/api/v1/risk/liquidity-var` | Liquidity-Adjusted VaR (L-VaR Bangia) con modello bid-ask spread |

### 2. Portfolio Optimization & Allocation
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/api/v1/optimization/hrp` | Hierarchical Risk Parity (HRP) con clustering gerarchico dei pesi |
| `POST` | `/api/v1/optimization/michaud-resampled` | Michaud Resampled Efficient Frontier (REF 1998) con bootstrap Monte Carlo |
| `POST` | `/api/v1/optimization/black-litterman` | Bayesian Black-Litterman con matrice delle views e Idzorek Confidence |
| `POST` | `/api/v1/optimization/risk-budgeting` | Equal Risk Contribution (ERC) e allocazione convessa SLSQP |
| `POST` | `/api/v1/optimization/mip-rebalance` | Mixed-Integer Programming (MIP) con vincoli di cardinalità e lotto minimo |

### 3. Derivati, Curve & Volatilità
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/api/v1/derivatives/heston-fft` | Calibrazione superficie e pricing opzioni Heston con FFT di Carr-Madan |
| `POST` | `/api/v1/derivatives/sabr-surface` | Hagan SABR (2002) e superficie di volatilità locale Dupire |
| `POST` | `/api/v1/derivatives/hull-white` | Hull-White 1-Factor per Bermudan Swaption con albero trinomiale |
| `POST` | `/api/v1/fixed-income/multicurve` | Dual Bootstrapping post-LIBOR multi-curva OIS (€STR / SOFR) |

### 4. Stress Testing & Regolamentare
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/api/v1/stress/macro` | Reverse Stress Test e scenari EBA 2026 / Fed CCAR / Geopolitica |
| `POST` | `/api/v1/stress/macro-scenarios-2026` | Valutazione scenari macro 2026 (Guerra Dazi, AI Bubble Reset, Curva Invertita BCE) |
| `POST` | `/api/v1/regulatory/isda-simm` | Calcolo margine iniziale ISDA SIMM v2.6 e regola UMR €50M |
| `POST` | `/api/v1/regulatory/frtb` | Standardized Approach Basilea IV (SBM, DRC, RRAO - BCBS 365) |
| `POST` | `/api/v1/regulatory/solvency2` | Standard Formula SCR e aggregazione correlata sottomoduli di mercato |

### 5. Execution, Compliance Pre-Trade & Reporting Istituzionale
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/api/v1/compliance/pre-trade-check` | Pre-Trade Risk Gate MiFID II RTS 28 & SEC 15c3-5 con sigillo SHA-256 |
| `GET` | `/api/v1/reporting/cro-institutional-dossier` | Download pacchetto ZIP completo 1-Click CRO Institutional Dossier |
| `POST` | `/api/v1/execution/market-making-vpin` | Avellaneda-Stoikov (2008) Market-Making & Hawkes VPIN Toxicity |

### 6. Audit Crittografico & Bitemporale
| Metodo | Endpoint | Descrizione |
|---|---|---|
| `POST` | `/api/v1/bitemporal/append` | Inserimento operazione a partita doppia con timestamp bitemporale |
| `GET` | `/api/v1/bitemporal/time-travel` | Ricostruzione dello stato del patrimonio alla data $T_{\text{valid}}$ registrata al tempo $T_{\text{system}}$ |
| `GET` | `/api/v1/bitemporal/merkle-seal` | Verifica integrità crittografica e Merkle Root SHA-256 della catena dei blocchi |

---

## 🖥️ Interfaccia Interattiva OpenAPI Integrata

Di seguito è integrato il visualizzatore **Redoc** interattivo:

<div style="border-radius: 8px; overflow: hidden; border: 1px solid rgba(255, 153, 0, 0.4); margin-top: 15px;">
<iframe src="https://petstore.swagger.io/?url=https://alessandro-sal.github.io/argus-risk-analytics/argus-architecture.json" width="100%" height="700px" style="border: none; background: #0d1117;"></iframe>
</div>
