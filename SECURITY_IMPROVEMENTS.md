# Security Improvements (Supabase + DB + Backend)

Date: 2026-03-10  
Workspace: `/Users/mark/.codex/worktrees/8bd0/mirrorview`

## Executive summary

I was able to scan the repo’s backend + frontend code and Python dependencies with automated tooling (Semgrep + pip-audit) and do a targeted best-practices review for FastAPI + Next.js. Those scans found **no static-code vulnerabilities**, but they did surface several **production security posture gaps** (notably: **public OpenAPI/docs exposure**, **no explicit auth on abuse-prone endpoints**, and **missing supply-chain pinning for the Next.js prototype**).

### Implemented (in this repo)

- Supabase DB remediation SQL scripts (apply in Supabase): `docs/plans/2026-03-10_security_hardening_593842/sql/`
- FastAPI:
  - Supabase Auth JWT required on write endpoints: `backend/app/auth/supabase_jwt.py`
  - OpenAPI/docs disabled in `RUN_MODE=prod`: `backend/app/main.py`
  - Separate migration DB URL + prod startup behavior: `backend/lib/load_env_vars.py`, `backend/app/main.py`
- Next.js prototype:
  - `pnpm-lock.yaml` committed + `packageManager` pinned: `flip-prototype/pnpm-lock.yaml`, `flip-prototype/package.json`
  - Baseline security headers (CSP report-only, etc.): `flip-prototype/next.config.ts`
  - Supabase Auth (magic link) UI and bearer token attachment: `flip-prototype/app/page.tsx`
- CI:
  - GitHub Actions workflow for tests/audit/semgrep: `.github/workflows/security.yml`

For Supabase/DB: the project exists (`MirrorView`, ref `sezczladugasghprqena`) and is **linked** from this worktree via the Supabase CLI. I was able to audit the **`public` schema** and cluster roles via `supabase db dump` artifacts you generated.

The DB audit surfaced a **critical exposure**: your application tables in `public` currently have **`GRANT ALL` to `anon` and `authenticated`** and there is **no evidence of RLS enablement or policies** in the schema dump. In a typical Supabase deployment, that means the tables are likely readable/writable via the REST API by unauthenticated clients.

- The Supabase CLI can now list API keys and edge functions using the linked project ref.
- No Supabase MCP resources are configured/available in this Codex environment (MCP resource list is empty).

Because of those access constraints, the DB/RLS findings below are based on **empirical evidence in your migrations** (which do not enable RLS) plus **explicit “next commands”** to run once DB access is provided, so we can complete the scan in one sweep.

## What I checked (evidence)

### Supabase CLI / MCP access (updated)

- Supabase CLI present: `supabase 2.31.8` (CLI indicates latest available is `2.75.0`).
- `supabase projects list` shows `MirrorView` (`sezczladugasghprqena`) as `linked: true` from this worktree.
- `supabase projects api-keys` succeeds (output contains sensitive secrets; do not paste into PRs/logs).
- `supabase functions list` succeeds (no functions currently listed).
- DB audit inputs (generated locally via `supabase db dump`):
  - `/tmp/mirrorview_public_schema.sql` (public schema)
  - `/tmp/mirrorview_roles.sql` (roles)
- MCP resources: none available (cannot use MCP for Supabase queries in this environment).

### DB audit results (public schema)

From `/tmp/mirrorview_public_schema.sql`:

- Tables present in `public` (all owned by `postgres`): `submissions`, `generations`, `thumb_feedback_events`, `edit_feedback_events`, plus `alembic_version`.
- **No RLS**: no `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` / `FORCE ROW LEVEL SECURITY` statements exist in the dump.
- **No policies**: no `CREATE POLICY` / `ALTER POLICY` statements exist in the dump.
- **Direct table exposure via grants** (selected evidence lines):
  - `public.submissions`: `GRANT ALL ... TO "anon"` (line 303) and `TO "authenticated"` (line 304)
  - `public.generations`: lines 294–295
  - `public.thumb_feedback_events`: lines 312–313
  - `public.edit_feedback_events`: lines 276–277
  - `public.alembic_version`: lines 267–268
- **Default privileges in `public` are permissive** for future objects created by `postgres`:
  - tables: lines 371–372 grant default `ALL` to `anon`/`authenticated`
  - sequences: lines 331–332
  - functions: lines 351–352

Note: this dump is scoped to `--schema public`. It does not audit `auth`, `storage`, `extensions`, or any other schemas.

### Backend (FastAPI) code scanning

- Semgrep: `p/python` + `p/owasp-top-ten` over `backend/` → **0 findings**.
- Python dependency audit: generated pinned requirements from `backend/uv.lock` via `uv export`, then ran `pip-audit` → **No known vulnerabilities found**.
- Targeted FastAPI posture review against `python-fastapi-web-server-security.md` (local skill reference).

### Frontend (Next.js/React) code scanning

- Semgrep: `p/javascript` + `p/react` + `p/owasp-top-ten` over `flip-prototype/` → **0 findings**.
- Targeted Next.js/React posture review against:
  - `javascript-typescript-nextjs-web-server-security.md`
  - `javascript-typescript-react-web-frontend-security.md`

## Findings

Severity uses: **Critical / High / Medium / Low** based on “impact × likelihood” for an internet-exposed deployment.

### Critical

**[C-001] `public` tables are fully accessible to `anon`/`authenticated` (no RLS in dump)**  
Impact: Unauthenticated/low-privileged clients can likely read/modify submissions/generations/feedback directly via Supabase REST, including user input text.  
Evidence: In `/tmp/mirrorview_public_schema.sql`, `GRANT ALL` is present for `anon` and `authenticated` on all app tables (e.g. `submissions` at lines 303–304; `generations` at lines 294–295; `thumb_feedback_events` at lines 312–313; `edit_feedback_events` at lines 276–277). There are **no** `ENABLE ROW LEVEL SECURITY` or `CREATE POLICY` statements in the dump.  
Action (immediate): Either (A) **enable RLS** on these tables and add policies (or intentionally add *no* policies to deny all client access), or (B) treat them as backend-only and **revoke privileges** from `anon`/`authenticated` and move them to a non-exposed schema.

**[C-002] Default privileges in `public` grant ALL on future tables/sequences/functions to `anon`/`authenticated`**  
Impact: Any future objects created by role `postgres` in `public` may become immediately accessible to `anon`/`authenticated` unless you remember to enable RLS/policies, creating “silent” regressions.  
Evidence: `/tmp/mirrorview_public_schema.sql` lines 371–372 grant default privileges `GRANT ALL ON TABLES` to `anon`/`authenticated`; similar defaults exist for sequences (lines 331–332) and functions (lines 351–352).  
Action (immediate): Remove these default privileges; require explicit grants per object and enforce “RLS-first” for any table that must be client-accessible.

**[C-003] Alembic migration state table is writable by `anon`/`authenticated`**  
Impact: A client may be able to tamper with migration state (`alembic_version`), corrupting upgrade/downgrade behavior and causing operational incidents.  
Evidence: `/tmp/mirrorview_public_schema.sql` lines 267–268 grant `ALL` on `public.alembic_version` to `anon` and `authenticated`.  
Action (immediate): Revoke all access to `alembic_version` from `anon`/`authenticated` (and ideally from any role except the migration role).

### High

**[H-001] FastAPI OpenAPI + interactive docs appear enabled and unprotected in production**  
Impact: Endpoint/schema discovery and operational details are exposed; increases attack surface and accelerates exploitation.  
Evidence: `FastAPI(...)` is instantiated without disabling `docs_url`, `redoc_url`, or `openapi_url`.  
Action: Disable docs/OpenAPI in prod (or protect behind auth / network allowlist).

**[H-002] No explicit authentication/authorization on write endpoints (abuse/cost risk)**  
Impact: Any internet client can call `POST /generate_response` and feedback endpoints; this can create LLM spend, availability issues, and DB growth.  
Evidence: Routers do not enforce auth dependencies; controls are rate limiting + request size limits.  
Action: Add a consistent auth layer (API key, JWT, or Supabase Auth) and enforce it via FastAPI dependencies.

**[H-003] Backend likely connects as `postgres` (BYPASSRLS) via pooler URL**  
Impact: Using a super-privileged role increases blast radius: any SSRF/SQLi/credential leak becomes full DB compromise.  
Evidence: The Supabase pooler URL template in `supabase/.temp/pooler-url` uses user `postgres.sezczladugasghprqena`; the roles dump indicates `postgres` has `BYPASSRLS`.  
Action: Create and use a dedicated backend DB role with least privilege (no BYPASSRLS), and ensure migrations run under a separate migration role.

**[H-004] Frontend dependency set is not pinned (missing lockfile)**  
Impact: Reproducibility + supply-chain control are weakened; audits are less reliable and builds can drift.  
Evidence: `flip-prototype/` contains `package.json` but no `package-lock.json`/`pnpm-lock.yaml`/`yarn.lock`.  
Action: Pick one package manager and commit the lockfile; add CI audit.

### Medium

**[M-001] Next.js app does not configure security headers (CSP, frame-ancestors, etc.)**  
Impact: Reduced defense-in-depth against XSS/clickjacking; mitigations depend entirely on hosting defaults.  
Evidence: `flip-prototype/next.config.ts` has no `headers()` configuration; no Vercel header config in repo.  
Action: Set baseline security headers at the edge (recommended) or via `next.config.ts`.

**[M-002] Rate limiting is process-local (not safe under horizontal scaling)**  
Impact: Limits can be bypassed across instances; risk increases as you scale.  
Evidence: `backend/app/security.py` uses an in-memory store.  
Action: Move rate-limit storage to Redis (or edge) before multi-instance deployment.

**[M-003] Supabase CLI is significantly behind latest**  
Impact: You may miss security-related features/bugfixes and have reduced compatibility with current Supabase features.  
Evidence: CLI reports installed `2.31.8` and latest available `2.75.0`.  
Action: Upgrade CLI and re-run Supabase-related checks.

### Low

**[L-001] Supabase MCP not configured in this environment**  
Impact: Slower auditing workflows; not a vulnerability by itself.  
Evidence: MCP resource list returned empty.  
Action: Configure Supabase MCP and provide token/permissions if you want MCP-driven audits/migrations.

## One full-sweep remediation plan

This is ordered to minimize rework and ensure we can verify each control empirically.

### Phase 0 (same day): Emergency DB containment (stop public exposure)

1. **Immediately restrict `anon`/`authenticated` access to app tables**
   - Fastest safe option (backend-only tables): `REVOKE ALL` from `anon`/`authenticated` on the four app tables + their sequences, and on `alembic_version`.
   - Defense-in-depth: also **enable RLS** (even if you plan “backend-only”) so accidental grants don’t re-expose data.
2. **Fix default privileges** so new objects aren’t silently exposed (remove `ALTER DEFAULT PRIVILEGES ... GRANT ALL ... TO anon/authenticated` for tables, sequences, functions).
3. Re-run `supabase db dump --schema public` and confirm the grants and defaults are corrected.

Suggested emergency SQL (apply via a migration / SQL editor; adjust to your chosen access model):

```sql
-- 1) Enable RLS (deny-by-default for anon/authenticated unless policies added)
alter table public.submissions enable row level security;
alter table public.generations enable row level security;
alter table public.thumb_feedback_events enable row level security;
alter table public.edit_feedback_events enable row level security;
alter table public.alembic_version enable row level security;

-- 2) Revoke direct privileges from client roles (recommended if backend-only)
revoke all on table public.submissions, public.generations, public.thumb_feedback_events, public.edit_feedback_events, public.alembic_version from anon, authenticated;
revoke all on sequence public.thumb_feedback_events_id_seq, public.edit_feedback_events_id_seq from anon, authenticated;

-- 3) Tighten default privileges for future objects in public created by postgres
alter default privileges for role postgres in schema public revoke all on tables from anon, authenticated;
alter default privileges for role postgres in schema public revoke all on sequences from anon, authenticated;
alter default privileges for role postgres in schema public revoke all on functions from anon, authenticated;
```

### Phase 1 (same day): Backend posture hardening (FastAPI)

1. **Disable or protect OpenAPI/docs in prod**
   - Disable by config when `RUN_MODE=prod`, or
   - Serve docs only behind an internal network allowlist / auth gate.
2. **Add explicit authentication for abuse-prone endpoints**
   - Minimum: static API key header for write endpoints (`POST /generate_response`, feedback).
   - Better: JWT-based auth (could be Supabase Auth) with per-request validation and consistent dependency enforcement.
3. **Host/proxy correctness**
   - In prod behind a trusted proxy, set `TRUST_PROXY_HEADERS=true` and ensure the edge sanitizes `X-Forwarded-For`.
   - Add host/origin validation at the edge or app layer if you construct absolute URLs from headers.

Verification:
- Add/extend tests to assert OpenAPI/docs are unavailable in prod.
- Add tests ensuring write endpoints reject missing/invalid auth.

### Phase 2 (same day): DB security audit (RLS, policies, grants)

Run the following SQL against the Supabase Postgres database (as an admin or an audit role with catalog access). Even after the hotfix above, keep these as regression checks:

1. **Tables and RLS flags**
   ```sql
   select
     n.nspname as schema,
     c.relname as table,
     c.relrowsecurity as rls_enabled,
     c.relforcerowsecurity as rls_forced
   from pg_class c
   join pg_namespace n on n.oid = c.relnamespace
   where c.relkind = 'r'
     and n.nspname not in ('pg_catalog', 'information_schema')
   order by 1, 2;
   ```
2. **Policies**
   ```sql
   select schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
   from pg_policies
   order by schemaname, tablename, policyname;
   ```
3. **Grants to common Supabase roles**
   ```sql
   select table_schema, table_name, grantee, privilege_type
   from information_schema.role_table_grants
   where grantee in ('anon', 'authenticated', 'service_role', 'postgres', 'public')
   order by table_schema, table_name, grantee, privilege_type;
   ```
4. **Default privileges (future tables)**
   ```sql
   select defaclrole::regrole as owner_role, defaclnamespace::regnamespace as schema, defaclobjtype, defaclacl
   from pg_default_acl
   order by 1, 2, 3;
   ```

Output of these queries should be captured and attached to the remediation PR/issue so we can confirm closure.

### Phase 3 (same day): DB hardening (choose one model)

**Model A (recommended for this repo as written): backend-only DB access**

Goal: The browser never talks to Postgres; only the backend connects using a least-privilege role.

1. Create a dedicated schema (e.g. `app_private`) for these persistence tables.
2. Move tables out of `public` schema (or create them there from the start).
3. Revoke all privileges from `anon` and `authenticated` roles on that schema/tables.
4. Create a dedicated DB role for the backend with only the needed privileges.
5. Use that role in `DATABASE_URL` (not `postgres` / not a broad admin role).

**Model B: client-accessible via Supabase APIs**

Goal: Tables can be accessed by Supabase client roles safely.

1. Enable RLS on each table.
2. Add explicit `SELECT/INSERT/UPDATE/DELETE` policies (or restrict to server-only via RPC).
3. Ensure policies reference correct identities (`auth.uid()` or JWT claims) and are tested.
4. Consider forcing RLS (`ALTER TABLE ... FORCE ROW LEVEL SECURITY`) for defense-in-depth.

### Phase 4 (next 1–2 days): Frontend posture + supply chain

1. Add a lockfile for `flip-prototype/` and enforce deterministic installs in CI.
2. Add baseline security headers (prefer edge config):
   - `Content-Security-Policy` (or start with report-only and iterate)
   - `X-Frame-Options` / `frame-ancestors`
   - `X-Content-Type-Options: nosniff`
   - `Referrer-Policy`
3. Add CI security checks:
   - Semgrep (same configs used here)
   - Dependency audit (`pip-audit` for backend; `npm audit`/`pnpm audit` for frontend)

## Immediate next step to complete the “DB/RLS” portion

Completed for `public` schema via the dump artifacts listed above. Remaining “full sweep” work, if you want it:

- Dump and audit any other schemas that may contain custom tables (if applicable), or
- Provide a credentialed `DATABASE_URL` so we can run the Phase 2 catalog queries directly (preferred for completeness).
