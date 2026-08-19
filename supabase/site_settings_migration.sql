-- Migration: site-wide feature toggles, controllable from /vle/admin/
-- without a code push. Run this ONCE in the Supabase SQL Editor (after
-- vle_signup_approval_migration.sql, since it reuses admin_users).
--
-- What this adds:
--   1. `site_settings` — a tiny key/value table. Starts with one row,
--      "jfw_enabled", controlling the "Form Filling Request" (CSC Partner)
--      widget shown on job/result/admit-card/etc. detail pages.
--   2. Public (anon) read — job-form-widget.js and api/submit-lead.js both
--      need to check the flag without a logged-in session.
--   3. Admin-only write — same admin_users allow-list already used by the
--      VLE approval panel, so no new "who's an admin" concept is introduced.

create table if not exists public.site_settings (
  key        text primary key,
  value_bool boolean not null,
  updated_at timestamptz not null default now()
);

insert into public.site_settings (key, value_bool)
values ('jfw_enabled', true)
on conflict (key) do nothing;

alter table public.site_settings enable row level security;

create policy "site_settings: public read" on public.site_settings
  for select to anon, authenticated
  using (true);

create policy "site_settings: admin update" on public.site_settings
  for update to authenticated
  using (exists (select 1 from public.admin_users a where a.id = auth.uid()))
  with check (exists (select 1 from public.admin_users a where a.id = auth.uid()));
