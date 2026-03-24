-- Backend-only access model: create least-privilege runtime role and a separate migrator role.
--
-- Apply via Supabase Dashboard SQL editor (or equivalent privileged channel).
--
-- IMPORTANT:
-- - You must choose strong passwords for the LOGIN roles (via ALTER ROLE ... PASSWORD ...).
-- - Ensure your backend runtime uses mirrorview_backend credentials, NOT postgres.*.
-- - Ensure your migrations use mirrorview_migrator credentials, NOT mirrorview_backend.

begin;

-- 1) Create roles
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'mirrorview_backend') then
    create role mirrorview_backend login noinherit nocreatedb nocreaterole nobypassrls;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'mirrorview_migrator') then
    create role mirrorview_migrator login noinherit nocreatedb nocreaterole nobypassrls;
  end if;
end
$$;

-- 2) Grants for runtime role (explicit-only, minimal)
grant usage on schema public to mirrorview_backend;

grant select, insert, update, delete on table
  public.submissions,
  public.generations,
  public.thumb_feedback_events,
  public.edit_feedback_events
to mirrorview_backend;

-- Sequences used by identity columns (may be required for inserts depending on usage).
grant usage, select on sequence
  public.thumb_feedback_events_id_seq,
  public.edit_feedback_events_id_seq
to mirrorview_backend;

-- 3) Grants for migrator role: allow schema migrations and alembic_version management
grant usage on schema public to mirrorview_migrator;
grant all on table
  public.submissions,
  public.generations,
  public.thumb_feedback_events,
  public.edit_feedback_events,
  public.alembic_version
to mirrorview_migrator;
grant all on sequence
  public.thumb_feedback_events_id_seq,
  public.edit_feedback_events_id_seq
to mirrorview_migrator;

commit;

