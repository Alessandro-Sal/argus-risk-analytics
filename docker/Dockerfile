# Usa un'immagine Python ufficiale e leggera
FROM python:3.11-slim

# Imposta la directory di lavoro
WORKDIR /app
ENV PYTHONPATH=/app

# Installa le dipendenze di sistema minime
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia i requisiti e installali
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del codice sorgente
COPY . .

# Esponi la porta usata da Streamlit
EXPOSE 8501

# Avvia l'applicazione Streamlit
CMD ["streamlit", "run", "src/0_Control_Room.py", "--server.port=8501", "--server.address=0.0.0.0"]
