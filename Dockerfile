# ============================================================
# ARGUS Institutional Risk & Wealth Platform — Cloud Dockerfile
# Compatible with:
#   - Hugging Face Spaces (Free 16 GB RAM, 2 vCPU, Port 7860)
#   - Render / Railway / Fly.io / Cloud Run
#   - Local Docker Compose
# ============================================================

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

WORKDIR /app

# Install system dependencies required by psycopg2, reportlab, and pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application source
COPY . .

# Create writable directories for non-root execution (Hugging Face Spaces uses UID 1000)
RUN mkdir -p /app/data /app/logs && chmod -R 777 /app/data /app/logs

EXPOSE 7860 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl --fail http://localhost:${PORT}/_stcore/health || exit 1

CMD ["sh", "-c", "streamlit run src/0_Control_Room.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true"]
