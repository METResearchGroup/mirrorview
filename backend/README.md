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

### Environment variables

The backend loads `OPENAI_API_KEY` from the repo-root `.env` file.

Add this to the repo root `.env` (recommended):

```bash
RUN_MODE=local
```

### CORS

Set `CORS_ORIGINS` (comma-separated) to allow your Vercel frontend to call the API.

Example:

```bash
CORS_ORIGINS=http://localhost:3000,https://your-app.vercel.app
```

### Railway deployment

- Create a Railway project pointing at this repo.
- Set **service root** to `backend/` (or use the included Dockerfile).
- Set env vars:
  - `OPENAI_API_KEY`
  - `RUN_MODE=local`
  - `CORS_ORIGINS=https://your-app.vercel.app`

Railway will provide `PORT`; the container binds to `0.0.0.0:$PORT`.

