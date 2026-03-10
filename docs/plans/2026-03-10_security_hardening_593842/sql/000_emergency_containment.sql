-- Emergency containment: stop public access to application data.
--
-- Apply via Supabase Dashboard SQL editor (or equivalent privileged channel).
-- This file is intentionally explicit and narrow in scope: only the app tables
-- observed in the `public` schema dump plus alembic_version and the two sequences.
--
-- After applying, re-run:
--   supabase db dump --schema public --keep-comments --file /tmp/mirrorview_public_schema.sql
-- and confirm:
--   - no GRANT ALL to anon/authenticated remains on these tables/sequences
--   - no permissive DEFAULT PRIVILEGES remain for anon/authenticated in public

begin;

-- 1) Revoke direct privileges from client roles
revoke all on table public.submissions from anon, authenticated;
revoke all on table public.generations from anon, authenticated;
revoke all on table public.thumb_feedback_events from anon, authenticated;
revoke all on table public.edit_feedback_events from anon, authenticated;
revoke all on table public.alembic_version from anon, authenticated;

revoke all on sequence public.thumb_feedback_events_id_seq from anon, authenticated;
revoke all on sequence public.edit_feedback_events_id_seq from anon, authenticated;

-- 2) Tighten default privileges to prevent silent re-exposure for future objects
alter default privileges for role postgres in schema public revoke all on tables from anon, authenticated;
alter default privileges for role postgres in schema public revoke all on sequences from anon, authenticated;
alter default privileges for role postgres in schema public revoke all on functions from anon, authenticated;

commit;

