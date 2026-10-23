# Installation & Modular Architecture

ARGUS is distributed as a modular Python package conforming to PEP 517/621 standards. You can install only the minimal dependencies needed for your specific deployment profile.

---

## Installation Profiles

### 1. Minimal Headless Core (Python Package)
Ideal for quantitative research scripts, headless data pipelines, Airflow DAGs, and Jupyter notebooks without web dependencies:

```bash
pip install argus-risk
```
*Dependencies included*: `numpy`, `pandas`, `scipy`, `scikit-learn`, `duckdb`, `pyarrow`, `pydantic`, `cryptography`, `SQLAlchemy`.

---

### 2. REST API Microservice
Installs the headless engine along with FastAPI and Uvicorn for microservice deployments and containerized Docker images:

```bash
pip install "argus-risk[api]"
```

Launch the production REST API server:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```
Interactive OpenAPI Swagger docs will be live at:
- `http://localhost:8000/docs` (Swagger UI)
- `http://localhost:8000/redoc` (ReDoc)

---

### 3. Full Analytical Cockpit & UI
Installs the complete visual intelligence platform, including Streamlit, Plotly, Excel/PDF reporting engines, and market data fetchers:

```bash
pip install "argus-risk[ui]"
```

Launch the Streamlit analytical platform:
```bash
streamlit run src/0_Control_Room.py
```

---

### 4. Full Institutional Suite (Development & Testing)
Installs all optional components, test runners (`pytest`, `hypothesis`), linters (`ruff`), and the documentation engine (`mkdocs-material`):

```bash
pip install "argus-risk[all]"
```

---

## Local Development Setup

Clone the repository and install in editable mode with development dependencies:

```bash
git clone https://github.com/Alessandro-Sal/argus-risk-analytics.git
cd argus-risk-analytics

# Create isolated virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install editable with dev dependencies
pip install -e ".[all]"

# Verify installation with test suite
pytest
```


---

## Deployment Architectures: Local Workstation vs Cloud Online

ARGUS adapts automatically to the execution environment detected at runtime:

### A. Local Workstation Mode (Zero-Config Desktop / CLI)
When running on your physical PC or workstation (`is_local_environment() == True`):
1. **Desktop Native (Windows 10/11)**: Double-click `setup_desktop.bat` once, then double-click `start_dashboard.bat`.
2. **Terminal CLI**:
   ```bash
   streamlit run src/0_Control_Room.py
   ```
3. **1-Click Passwordless Owner Access**: The login gate presents a dedicated workstation card. Click **⚡ Entra Subito al Terminale (Alessandro)** to enter immediately without email or password.
4. **Auto-Login**: Check *"Ricorda ed entra sempre in automatico all'avvio su questo PC"* to store your local preference in `data/.argus_local_session.json` and bypass the gate entirely on future startups.
5. **Persistence**: Embedded SQLite databases (`data/argus_local.db` and `data/argus_wealth.db`) or local MySQL 8.0, 100% offline-ready.

### B. Cloud Deployment (Streamlit Community Cloud & Multi-Tenant Web)
When deployed on Streamlit Cloud or containerized public servers (`is_streamlit_cloud() == True`):
1. **Pre-Splash Security Gate**: The local passwordless bypass is strictly disabled. Users must authenticate via:
   - **Vault Login**: PBKDF2-HMAC-SHA256 or Supabase GoTrue JWT.
   - **New Account Provisioning**: Automatic allocation of an isolated cloud tenant.
   - **1-Click Demo Sandbox**: In-memory ephemeral demonstration mode with synthetic archetypes.
2. **Persistence**: Supabase PostgreSQL 16 (AWS EU-West-1 Ireland) via encrypted SSL `QueuePool` with multi-tenant row-level isolation by `user_id`.

---

## Configuration & Environment Variables Reference

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `STREAMLIT_RUNTIME_ENV` | `string` | `local` | Set to `cloud` to force cloud security mode and disable local passwordless bypass. |
| `IS_STREAMLIT_CLOUD` | `bool` | `false` | Set to `true` or `1` on containerized cloud deployments. |
| `ARGUS_REQUIRE_LOGIN` | `bool` | `true` | Set to `false` in development environments to bypass the login gate. |
| `SUPABASE_URL` | `string` | `""` | Supabase project URL (e.g., `https://xyz.supabase.co`). |
| `SUPABASE_ANON_KEY` | `string` | `""` | Supabase public anonymous API key for GoTrue client authentication. |
| `SUPABASE_SERVICE_ROLE_KEY`| `string` | `""` | Supabase administrative service role key (optional, server-side only). |
| `DATABASE_URL` | `string` | `""` | Custom PostgreSQL connection string (BYOD — Bring Your Own Database). |
| `GEMINI_API_KEY` | `string` | `""` | Google Gemini API key for AI Narrative Intelligence & Copilot. |
| `OPENAI_API_KEY` | `string` | `""` | OpenAI API key for alternative LLM provider. |

Configure these either in `.env` (local) or in `.streamlit/secrets.toml` (Streamlit Cloud).
