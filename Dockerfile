# GlitchHunter v3.0 Docker Image - Simplified
# Schneller Build für Deployment

FROM python:3.11-slim

WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python-Dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Anwendung kopieren
COPY src/ src/
COPY ui/ ui/
COPY scripts/ scripts/
COPY config.yaml ./

# Verzeichnisse erstellen
RUN mkdir -p /app/logs /app/data /app/cache /app/reports

# Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV GLITCHHUNTER_HOME=/app
ENV GLITCHHUNTER_DATA=/app/data
ENV GLITCHHUNTER_LOGS=/app/logs
ENV GLITCHHUNTER_CACHE=/app/cache

# Port
EXPOSE 6262

# Health-Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6262/api/v1/status || exit 1

# Start
CMD ["uvicorn", "ui.web.backend.app:app", "--host", "0.0.0.0", "--port", "6262", "--workers", "4"]
