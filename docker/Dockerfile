# ==============================================================================
# docker/Dockerfile
# ARGUS — Hardened Multi-Stage Production Container
# Non-root unprivileged execution, layer caching, and built-in healthcheck
# ==============================================================================

# ── STAGE 1: Builder ──
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── STAGE 2: Runtime Ristretto ──
FROM python:3.11-slim AS runtime

# Creazione utente non-root dedicato
RUN groupadd -g 10001 argus && \
    useradd -u 10001 -g argus -m -s /bin/bash argus

WORKDIR /app
ENV PYTHONPATH=/app \
    PATH=/home/argus/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

# Copia pacchetti installati dallo stage builder
COPY --from=builder /root/.local /home/argus/.local

# Copia codice sorgente con ownership ad argus
COPY --chown=argus:argus . .

# Creazione cartella dati e backup locale persistente
RUN mkdir -p /app/data/backups && chown -R argus:argus /app/data

USER argus
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')" || exit 1

STOPSIGNAL SIGTERM

CMD ["streamlit", "run", "src/0_Control_Room.py"]
