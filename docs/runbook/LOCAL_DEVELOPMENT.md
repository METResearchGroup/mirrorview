# Local development runbook

## Prerequisites

- Python 3.12+ (the backend targets the latest runtime and uv-managed environments).
- [`uv`](https://github.com/astral-sh/uv) for dependency management and running FastAPI commands.
- Node.js & npm for the `flip-prototype` Next.js frontend.

## Backend

### Setup

```bash
cd backend
uv sync
```

### Run locally with persistence disabled

```bash
export RUN_MODE=local
export PERSISTENCE_ENABLED=false
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Persistence-disabled behavior (recommended)

- `PERSISTENCE_ENABLED=false` → `get_maybe_session()` yields `None`, so DI returns `NullSubmissionRepo`, `NullGenerationRepo`, `NullThumbFeedbackRepo`, `NullEditFeedbackRepo` (`backend/app/db/repos/null.py`) and `NullUnitOfWork` (`backend/app/db/uow.py`).
- Those Null implementations deliberately drop writes (`NullGenerationRepo.add()` returns the sentinel `NULL_UUID`), which keeps responses identical to the production API while avoiding any database traffic.
- This is the flow we recommend for day-to-day development; it unlocks fast feedback without requiring a Postgres/Supabase instance.

### Opt into persistence when needed

```bash
export PERSISTENCE_ENABLED=true
export DATABASE_URL=<your Supabase/PG pooler URL>
uv run alembic upgrade head
```

After that, start the backend with the same `uv run uvicorn ...` command and DI will return the SQL-backed repos and `SqlAlchemyUnitOfWork`.

## Frontend (`flip-prototype`)

### Frontend setup

```bash
cd flip-prototype
npm install
npm run dev
```

### Configure the backend URL

```bash
export NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

The prototype hits `POST /generate_response`, so keep the backend running in persistence-disabled mode unless you explicitly want writes landing in Postgres.

## Typical local workflow

1. Start the backend with `RUN_MODE=local` and `PERSISTENCE_ENABLED=false`.
2. Launch the Next.js prototype with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
3. Flip a post, inspect logs, and adjust Python/TypeScript code as needed.
4. Run `uv run pytest` before pushing if you touched backend logic.

## Verification checklist

- `uv run ruff check .` (run from the `backend/` directory).
- `uv run pytest`.
- `npm run lint`/`npm run test` inside `flip-prototype` if you edit the frontend.

## Notes

- The Null repos drop writes, so test data does not survive restarts. That’s intentional and keeps local development safe.
- Set `RUN_MODE=local` + `PERSISTENCE_ENABLED=false` for the fastest loop; switch on persistence only when you need to exercise migrations or database-backed features.
