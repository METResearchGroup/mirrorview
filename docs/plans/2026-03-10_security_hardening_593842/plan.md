# MirrorView security hardening sweep

Date: 2026-03-10  
Workspace: `/Users/mark/.codex/worktrees/8bd0/mirrorview`

## Overview

Fix the security issues captured in `/Users/mark/.codex/worktrees/8bd0/mirrorview/SECURITY_IMPROVEMENTS.md` by removing accidental public DB access in Supabase, moving the backend to least-privilege DB credentials, requiring Supabase Auth JWTs on write endpoints, disabling FastAPI docs/OpenAPI in production, and hardening the Next.js prototype (lockfile + baseline security headers).

## Happy Flow

1. **Sign-in** — User signs in via Supabase magic-link in `/Users/mark/.codex/worktrees/8bd0/mirrorview/flip-prototype/app/page.tsx` and receives an access token.
2. **Authenticated API calls** — Frontend attaches `Authorization: Bearer <token>` for:
   - `POST /generate_response`
   - `POST /feedback/thumb`
   - `POST /feedback/edit`
3. **Backend JWT verification** — FastAPI validates token signature/issuer/audience/expiry in `/Users/mark/.codex/worktrees/8bd0/mirrorview/backend/app/auth/supabase_jwt.py`.
4. **Least-privilege persistence** — Backend connects using `DATABASE_URL` (runtime role), and migrations use `MIGRATION_DATABASE_URL` (migrator role) when needed.
5. **DB private-by-default** — Supabase `public` exposure is removed by applying:
   - `sql/000_emergency_containment.sql` (revoke `anon`/`authenticated`, tighten default privileges)
   - `sql/010_roles_and_grants.sql` (create runtime + migrator roles)
   - `sql/020_rls_backend_only.sql` (optional defense-in-depth RLS policies)

## Manual Verification

### DB / Supabase (manual)

- Apply `docs/plans/2026-03-10_security_hardening_593842/sql/000_emergency_containment.sql` in Supabase SQL editor.
- Re-dump and confirm no `GRANT ALL` to `anon`/`authenticated` remains:
  - `supabase db dump --schema public --keep-comments --file /tmp/mirrorview_public_schema.sql`
  - `rg -n 'GRANT ALL .* TO \"anon\"|GRANT ALL .* TO \"authenticated\"|ALTER DEFAULT PRIVILEGES .* TO \"anon\"|ALTER DEFAULT PRIVILEGES .* TO \"authenticated\"' /tmp/mirrorview_public_schema.sql` → no matches
- Apply `docs/plans/2026-03-10_security_hardening_593842/sql/010_roles_and_grants.sql`, set passwords for the new roles, and update backend deployment env vars accordingly.
- (Optional) Apply `docs/plans/2026-03-10_security_hardening_593842/sql/020_rls_backend_only.sql` and confirm backend still reads/writes successfully.

### Backend

From `/Users/mark/.codex/worktrees/8bd0/mirrorview/backend`:

- `uv sync`
- `uv run pytest` → all tests pass
- `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- With `RUN_MODE=prod`:
  - `GET /docs` → 404
  - `GET /openapi.json` → 404
- With `AUTH_REQUIRED=true`, `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, `SUPABASE_JWT_AUDIENCE=authenticated`:
  - `POST /generate_response` without token → 401
  - same call with Supabase JWT → 200

### Frontend

From `/Users/mark/.codex/worktrees/8bd0/mirrorview/flip-prototype`:

- `pnpm install --frozen-lockfile`
- `pnpm lint`
- `pnpm build`
- `pnpm dev`
- Confirm:
  - “Sign in” card appears when Supabase env vars are not set
  - After signing in, requests include `Authorization: Bearer …`

## Alternative approaches

- **Client-accessible tables + full per-user RLS policies**: rejected; product currently persists via backend and schema lacks per-user ownership fields.
- **Static API key auth**: rejected; not safe for browser clients.

## Artifacts

- UI screenshots:
  - `images/before/`
  - `images/after/`
- SQL scripts:
  - `sql/000_emergency_containment.sql`
  - `sql/010_roles_and_grants.sql`
  - `sql/020_rls_backend_only.sql`
