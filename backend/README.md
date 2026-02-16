# MirrorView backend (FastAPI)

## Prereqs

- Python (recommended: 3.12.x)
- [`uv`](https://github.com/astral-sh/uv)

## Setup

From `backend/`:

```bash
uv sync
```

## Run locally

From `backend/`:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

From `backend/`:

```bash
uv run pytest
```

## Environment variables

The backend loads `OPENAI_API_KEY` from the repo-root `.env` file.

Add this to the repo root `.env` (recommended):

```bash
RUN_MODE=local
```

## Persistence (Supabase Postgres)

This backend can persist generations + feedback events to **Postgres** (recommended: Supabase).

- **Enable/disable persistence**
  - `PERSISTENCE_ENABLED=true|false`
  - Defaults:
    - `RUN_MODE=local|prod`: enabled by default
    - `RUN_MODE=test`: disabled by default (tests stay hermetic)

- **Database connection**
  - `DATABASE_URL`: SQLAlchemy async connection string.
  - Recommended (Supabase): use the **Supabase pooler** connection string from the Supabase dashboard “Connect” dialog.

### Migrations

From `backend/`:

```bash
uv run alembic upgrade head
```

### Integration tests

The test suite includes a hermetic Postgres integration test using `testcontainers` (requires Docker).

### Supabase MCP (optional)

If you’re using Cursor’s Supabase MCP tooling, set:

```bash
SUPABASE_ACCESS_TOKEN=...
```

Then you can use the MCP tools to list tables, apply SQL migrations, and sanity-check inserts directly against your Supabase project.

## CORS

Set `CORS_ORIGINS` (comma-separated) to allow your Vercel frontend to call the API.

Example:

```bash
CORS_ORIGINS=http://localhost:3000,https://your-app.vercel.app
```

## Security controls

The API includes baseline request hardening for anonymous traffic:

- In-memory, IP-keyed rate limits on:
  - `POST /generate_response` (strict)
  - `POST /feedback/thumb` (moderate)
  - `POST /feedback/edit` (moderate)
- Fail-closed limiter behavior (if limiter checks cannot run, requests are denied).
- Request body size limit (`MAX_REQUEST_BODY_BYTES`, default: `65536`).
- Security response headers:
  - `X-Request-ID`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
  - `Content-Security-Policy-Report-Only` (or enforce mode via `CSP_REPORT_ONLY=false`)
- Standardized JSON error envelope for `4xx/5xx`.

### Security environment variables

```bash
# Proxy/IP handling
TRUST_PROXY_HEADERS=false

# Body size guard (bytes)
MAX_REQUEST_BODY_BYTES=65536

# Per-endpoint limits
RATE_LIMIT_GENERATE=5/minute,30/hour
RATE_LIMIT_FEEDBACK_THUMB=30/minute,300/hour
RATE_LIMIT_FEEDBACK_EDIT=15/minute,120/hour

# CSP mode
CSP_REPORT_ONLY=true
```

### Scale-up criteria (when to move beyond baseline)

- Move limiter storage to Redis when either:
  - backend is running with more than 1 app instance, or
  - rate-limit false positives appear after horizontal scaling.
- Add API key protection for write endpoints when either:
  - sustained `429` rate is above 5% of write traffic for 3 consecutive days, or
  - repeated abuse requires manual IP blocklist updates more than twice per week.
- Revisit thresholds weekly until traffic stabilizes, then monthly.

### Verification checklist

- Unit: rate-limit key extraction and fixed-window counter behavior.
- Integration: `429` response shape + `Retry-After` header.
- Integration: request-body overflow returns `413`.
- Integration: validation failures return standardized envelope.
- Security smoke test: required response headers present on `/health` and write endpoints.

## Model selection

The backend exposes a model catalog and accepts a selected model per submission.

- `GET /models` returns:
  - `default_model_id`
  - `models[]` with `{ model_id, display_name, provider }`
- `POST /generate_response` expects `submission.model_id` and validates it against
  the available model catalog.

### Model config and availability

- Source of truth: `backend/ml_tooling/llm/config/models.yaml`
- `models.default.default_model` controls default selection (currently `gpt-5-nano`)
- Each configured model has:
  - `litellm_route` (provider runtime route)
  - `available` (whether UI/API should expose/accept it)

### Provider credentials

Set keys for any provider you enable:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
OPENROUTER_API_KEY=...
GOOGLE_AI_STUDIO_KEY=...
GROQ_API_KEY=...
```

## Railway deployment

- Create a Railway project pointing at this repo.
- In the service **Settings**, set **Root Directory** to `backend` so Railway builds from this directory (finds `Dockerfile` and `railway.json` here).
- Set env vars:
  - `OPENAI_API_KEY`
  - `RUN_MODE=local`
  - `CORS_ORIGINS=https://your-app.vercel.app`
  - `PERSISTENCE_ENABLED=true`
  - `DATABASE_URL=...` (Supabase pooler URL)

Railway will provide `PORT`; the container binds to `0.0.0.0:$PORT`.
