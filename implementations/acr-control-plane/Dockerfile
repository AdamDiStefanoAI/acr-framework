FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos "" acr

# Copy application code before install so the image builds reproducibly.
COPY pyproject.toml ./
COPY src/ ./src/
COPY policies/ ./policies/
COPY alembic.ini ./
COPY README.md ./

# Install production dependencies only.
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# WEB_CONCURRENCY controls the number of uvicorn worker processes.
# Default: 2 (safe baseline). Tune via docker-compose environment or
# Kubernetes deployment env. Rule of thumb: 2-4 × vCPU count.
ENV WEB_CONCURRENCY=2

EXPOSE 8000

USER acr

CMD uvicorn acr.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${WEB_CONCURRENCY} \
    --loop uvloop \
    --http httptools
