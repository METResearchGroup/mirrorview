# Prod migrations hotfix notes

## Incident
- **Symptom**: `sqlalchemy.exc.ProgrammingError` / `asyncpg.exceptions.UndefinedColumnError` for `submissions.selected_model_id`.
- **Impact**: `POST /generate_response` fails when persistence is enabled.
- **Root cause**: production DB schema behind Alembic head (missing `0002_model_ids` column additions), and deploy/startup does not apply migrations automatically (`backend/Dockerfile` starts Uvicorn only).

## Hotfix approach
- Apply Alembic migrations automatically to `head` on application startup when `PERSISTENCE_ENABLED=true`.
- Harden Alembic async engine connect args for Supabase pooler / transaction mode (disable prepared statement caches).
- Add an integration test that starts from an empty Postgres and succeeds without manually running migrations in the test.

## Verification artifacts (fill as executed)
- Local test run: `uv run pytest` (backend)
- PR link:
- Railway deploy timestamp:
- Post-deploy smoke:
  - `/health` OK
  - `POST /generate_response` OK
  - DB has `submissions.selected_model_id`

