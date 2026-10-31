# ==============================================================================
# ARGUS — Institutional Quantitative Risk & Wealth Intelligence Platform
# Production Hardened Multi-Stage Dockerfile (Canonical Root Entrypoint)
# Compatible with:
#   - Local Docker Compose & Production VPS (Port 8501)
#   - Hugging Face Spaces (Port 7860, Non-Root UID 1000/10001)
#   - Google Cloud Run / Render / Railway / AWS ECS
# ==============================================================================

# ── STAGE 1: Dependency Builder ──
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# ── STAGE 2: Hardened Runtime ──
FROM python:3.11-slim AS runtime

# Creazione utente non-root dedicato per isolamento runtime
RUN groupadd -g 10001 argus && \
    useradd -u 10001 -g argus -m -s /bin/bash argus

WORKDIR /app

# Variabili d'ambiente essenziali per Streamlit & Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/home/argus/.local/bin:$PATH \
    PORT=8501 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Installazione librerie C runtime necessarie per psycopg2 e reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia delle dipendenze compilate dallo stage builder
COPY --from=builder /root/.local /home/argus/.local

# Copia del codice sorgente con ownership ad argus
COPY --chown=argus:argus . .

# Creazione cartelle per storage persistente, SQLite locale e log
RUN mkdir -p /app/data /app/data/backups /app/logs && \
    chown -R argus:argus /app/data /app/logs && \
    chmod -R 775 /app/data /app/logs

USER argus
EXPOSE 8501 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl --fail http://127.0.0.1:${PORT}/_stcore/health || exit 1

STOPSIGNAL SIGTERM

CMD ["sh", "-c", "streamlit run src/0_Control_Room.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
