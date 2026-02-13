## MirrorView backend (FastAPI)

### Prereqs

- Python (recommended: 3.12.x)
- [`uv`](https://github.com/astral-sh/uv)

### Setup

From `backend/`:

```bash
uv sync
```

### Run locally

From `backend/`:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Tests

From `backend/`:

```bash
uv run pytest
```

### Environment variables

The backend loads `OPENAI_API_KEY` from the repo-root `.env` file.

Add this to the repo root `.env` (recommended):

```bash
RUN_MODE=local
```

### Persistence (Supabase Postgres)

This backend can persist generations + feedback events to **Postgres** (recommended: Supabase).

- **Enable/disable persistence**
  - `PERSISTENCE_ENABLED=true|false`
  - Defaults:
    - `RUN_MODE=local|prod`: enabled by default
    - `RUN_MODE=test`: disabled by default (tests stay hermetic)

- **Database connection**
  - `DATABASE_URL`: SQLAlchemy async connection string.
  - Recommended (Supabase): use the **Supabase pooler** connection string from the Supabase dashboard “Connect” dialog.

#### Migrations

From `backend/`:

```bash
uv run alembic upgrade head
```

#### Integration tests

The test suite includes a hermetic Postgres integration test using `testcontainers` (requires Docker).

#### Supabase MCP (optional)

If you’re using Cursor’s Supabase MCP tooling, set:

```bash
SUPABASE_ACCESS_TOKEN=...
```

Then you can use the MCP tools to list tables, apply SQL migrations, and sanity-check inserts directly against your Supabase project.

### CORS

Set `CORS_ORIGINS` (comma-separated) to allow your Vercel frontend to call the API.

Example:

```bash
CORS_ORIGINS=http://localhost:3000,https://your-app.vercel.app
```

### Railway deployment

- Create a Railway project pointing at this repo.
- In the service **Settings**, set **Root Directory** to `backend` so Railway builds from this directory (finds `Dockerfile` and `railway.json` here).
- Set env vars:
  - `OPENAI_API_KEY`
  - `RUN_MODE=local`
  - `CORS_ORIGINS=https://your-app.vercel.app`
  - `PERSISTENCE_ENABLED=true`
  - `DATABASE_URL=...` (Supabase pooler URL)

Railway will provide `PORT`; the container binds to `0.0.0.0:$PORT`.

