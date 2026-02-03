# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

# System-level installs (run as root): curl for HEALTHCHECK, uv for deps
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Copy dependency manifests first for caching
COPY pyproject.toml ./
COPY uv.lock ./

# Install dependencies (system-wide in image)
RUN uv sync --frozen --no-dev

# Copy the rest of the backend
COPY . .

# Non-root user: create appuser and chown WORKDIR and copied files
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser \
    && chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8000}/health" || exit 1
