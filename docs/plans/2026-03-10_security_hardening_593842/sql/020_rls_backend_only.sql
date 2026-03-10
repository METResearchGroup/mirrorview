-- Defense-in-depth (optional but recommended): enable RLS and allow only mirrorview_backend.
--
-- Apply AFTER you have created roles via 010_roles_and_grants.sql.
--
-- Notes:
-- - Enabling RLS without policies denies access for roles that do not bypass RLS.
-- - Supabase's service_role and postgres often have BYPASSRLS; do not rely on that.
-- - This policy set is intentionally permissive for the backend role (USING true / WITH CHECK true).

begin;

-- Enable RLS
alter table public.submissions enable row level security;
alter table public.generations enable row level security;
alter table public.thumb_feedback_events enable row level security;
alter table public.edit_feedback_events enable row level security;

-- Backend-only policies
drop policy if exists submissions_backend_all on public.submissions;
create policy submissions_backend_all on public.submissions
  for all
  to mirrorview_backend
  using (true)
  with check (true);

drop policy if exists generations_backend_all on public.generations;
create policy generations_backend_all on public.generations
  for all
  to mirrorview_backend
  using (true)
  with check (true);

drop policy if exists thumb_feedback_events_backend_all on public.thumb_feedback_events;
create policy thumb_feedback_events_backend_all on public.thumb_feedback_events
  for all
  to mirrorview_backend
  using (true)
  with check (true);

drop policy if exists edit_feedback_events_backend_all on public.edit_feedback_events;
create policy edit_feedback_events_backend_all on public.edit_feedback_events
  for all
  to mirrorview_backend
  using (true)
  with check (true);

commit;

