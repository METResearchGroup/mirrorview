# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency manifests first for caching
COPY pyproject.toml ./
COPY uv.lock ./

# Install dependencies (system-wide in image)
RUN uv sync --frozen --no-dev

# Copy the rest of the backend
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

