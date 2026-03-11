# Add Ruff + Pyright + Pytest gates (backend-scoped)

## Overview
Add a Python CI gate and local developer hooks so the `backend/` Python codebase is consistently formatted (Ruff), linted (Ruff), type-checked (Pyright in strict mode), and tested (Pytest). This repo’s Python project lives in `backend/`, so CI and tooling run from that directory.

## Happy Flow
1. Install dependencies: `cd backend && uv sync --extra test`
2. Run gates locally:
   - `uv run ruff check .`
   - `uv run ruff format --check .`
   - `uv run pyright .`
   - `uv run pytest`
3. GitHub Actions runs the same gates for Python 3.10/3.11/3.12.

## Key Changes
- `backend/pyproject.toml`: add `pyright` and a `test` extra (`uv sync --extra test`).
- `backend/pyrightconfig.json`: strict Pyright config with missing-import/type-stub noise disabled.
- `.github/workflows/ci.yml`: Python matrix gate matching the reference workflow’s test job behavior, adapted to `backend/`.
- `.pre-commit-config.yaml`: Ruff hooks mirror CI + local Pyright hook.

## Manual Verification
- [ ] `cd backend && uv sync --extra test`
- [ ] `cd backend && uv run ruff check .`
- [ ] `cd backend && uv run ruff format --check .`
- [ ] `cd backend && uv run pyright .`
- [ ] `cd backend && uv run pytest`
- [ ] `pre-commit run --all-files` (optional)

## Alternative approaches
- Moving the Python project to repo root would match reference paths more literally, but would be a larger refactor and is not needed.

