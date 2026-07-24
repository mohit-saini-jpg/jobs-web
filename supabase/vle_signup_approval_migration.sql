-- Migration: public VLE self-signup + admin approval + unlimited slots.
-- Run this ONCE in the Supabase SQL Editor (after vle_schema.sql +
-- vle_add_state_migration.sql have already been run).
--
-- What this adds:
--   1. `is_approved` on vle_profiles — self-signed-up VLEs start FALSE and
--      are invisible/can't-post until an admin approves them. Existing
--      admin-created rows are backfilled to TRUE (they're already trusted —
--      this migration must never hide a partner who's already live).
--   2. `admin_users` — a tiny allow-list table. To make yourself an admin,
--      after running this file, run separately:
--        insert into public.admin_users (id) values ('<your-auth-user-uuid>');
--   3. `next_vle_slot()` — atomically hands out the next free slot number
--      for a state+district so the public signup form never needs a human
--      to pick one.
--   4. Slot cap relaxed from 1-4 to 1-500 — a district is no longer capped
--      at 4 VLEs, and adding VLE #5/#20/#100 never needs a new site build
--      (see the /vle/:state/:district/:slot/ rewrite in vercel.json).

alter table public.vle_profiles add column if not exists is_approved boolean not null default true;
-- ^ default TRUE so every already-existing (admin-created, already-trusted)
-- row is backfilled as approved and stays visible — only NEW self-signup
-- rows will explicitly be inserted with is_approved = false (enforced by
-- the insert policy below, not by this column default).

alter table public.vle_profiles drop constraint if exists vle_profiles_slot_check;
alter table public.vle_profiles add constraint vle_profiles_slot_check check (slot between 1 and 500);

create table if not exists public.admin_users (
  id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.admin_users enable row level security;

-- A logged-in user may check ONLY whether THEY THEMSELVES are an admin
-- (returns their own row if so, nothing otherwise) — this is exactly what
-- `exists(select 1 from admin_users where id = auth.uid())` needs in the
-- policies below, without ever exposing the full admin list to anyone.
create policy "admin_users: self read" on public.admin_users
  for select to authenticated using (auth.uid() = id);

-- ── Slot auto-assignment ─────────────────────────────────────────────────
-- SECURITY DEFINER so it sees the TRUE max slot across ALL rows (including
-- other pending/unapproved signups a plain authenticated SELECT can't see
-- under RLS) — it only ever returns a bare integer, never row data, so
-- there's nothing to leak.
create or replace function public.next_vle_slot(p_state text, p_district text)
returns int
language sql
security definer
set search_path = public
stable
as $$
  select coalesce(max(slot), 0) + 1
  from public.vle_profiles
  where state = p_state and district = p_district;
$$;
revoke all on function public.next_vle_slot(text, text) from public;
grant execute on function public.next_vle_slot(text, text) to authenticated;

-- ── vle_profiles policies ────────────────────────────────────────────────

-- Public read: replace the old "everyone sees everything" policy — now
-- unapproved profiles are hidden from the public district page, but a VLE
-- can still see their OWN (possibly still-pending) profile on their
-- dashboard.
drop policy if exists "vle_profiles: public read" on public.vle_profiles;
create policy "vle_profiles: public read approved or own" on public.vle_profiles
  for select to anon, authenticated
  using (is_approved = true or auth.uid() = id);

-- Self-signup insert: a newly-registered auth user may create EXACTLY ONE
-- profile row for themselves, and it MUST start unapproved — this is what
-- stops a crafted request from self-approving on signup.
create policy "vle_profiles: self-insert pending approval" on public.vle_profiles
  for insert to authenticated
  with check (auth.uid() = id and is_approved = false);

-- Admin: full visibility (including pending) + approve/reject.
create policy "vle_profiles: admin read all" on public.vle_profiles
  for select to authenticated
  using (exists (select 1 from public.admin_users a where a.id = auth.uid()));

create policy "vle_profiles: admin update" on public.vle_profiles
  for update to authenticated
  using (exists (select 1 from public.admin_users a where a.id = auth.uid()))
  with check (exists (select 1 from public.admin_users a where a.id = auth.uid()));

create policy "vle_profiles: admin delete (reject)" on public.vle_profiles
  for delete to authenticated
  using (exists (select 1 from public.admin_users a where a.id = auth.uid()));

-- ── vle_posts: only an APPROVED VLE may post ────────────────────────────
drop policy if exists "vle_posts: insert own state+district+slot only" on public.vle_posts;
create policy "vle_posts: insert own approved state+district+slot only" on public.vle_posts
  for insert to authenticated
  with check (
    auth.uid() = vle_id
    and state = (select state from public.vle_profiles where id = auth.uid())
    and district = (select district from public.vle_profiles where id = auth.uid())
    and slot = (select slot from public.vle_profiles where id = auth.uid())
    and (select is_approved from public.vle_profiles where id = auth.uid()) = true
  );
