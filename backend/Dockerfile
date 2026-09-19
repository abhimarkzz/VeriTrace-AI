# ==============================================================================
# VeriTrace AI — Backend Service Dockerfile
# ==============================================================================

FROM python:3.12-slim AS runtime

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_ENV=production \
    MODEL_LOAD_ON_STARTUP=false

# Install minimal OS dependencies for Postgres client, SSL, and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root system user for security compliance
RUN groupadd -g 1000 veritrace && \
    useradd -u 1000 -g veritrace -s /bin/bash -m veritrace

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

# Copy application source code and migration scripts
COPY app/ /app/app/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY scripts/ /app/scripts/

# Ensure scripts are executable
RUN chmod +x /app/scripts/*.sh 2>/dev/null || true

# Ensure non-root user ownership of the application directory and cache dirs
RUN mkdir -p /app/models /home/veritrace/.cache && \
    chown -R veritrace:veritrace /app /home/veritrace

USER veritrace

EXPOSE 8000

# Docker Healthcheck
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]

# Start Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
