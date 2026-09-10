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
streamlit run app.py
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
