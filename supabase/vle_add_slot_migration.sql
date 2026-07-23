-- Migration: give every VLE their OWN separate page (no more sharing a
-- district page with another VLE's posts mixed in).
-- Run this ONCE in the Supabase SQL Editor. Requires the `state` column
-- to already exist (run vle_add_state_migration.sql first if you haven't).
-- Safe with existing rows — your one real Hisar profile/post gets
-- backfilled to slot=1 automatically (same URL as before, no change for it).

alter table public.vle_profiles add column if not exists slot smallint;
alter table public.vle_posts add column if not exists slot smallint;

update public.vle_profiles set slot = 1 where slot is null;
update public.vle_posts set slot = 1 where slot is null;

alter table public.vle_profiles alter column slot set not null;
alter table public.vle_profiles alter column slot set default 1;
alter table public.vle_profiles add constraint vle_profiles_slot_range check (slot between 1 and 4);
alter table public.vle_profiles add constraint vle_profiles_state_district_slot_unique unique (state, district, slot);

alter table public.vle_posts alter column slot set not null;
alter table public.vle_posts alter column slot set default 1;

drop index if exists vle_posts_state_district_idx;
create index if not exists vle_posts_state_district_slot_idx on public.vle_posts (state, district, slot);

-- Replace the state+district-only RLS insert/update policies with
-- state+district+slot versions.
drop policy if exists "vle_posts: insert own state+district only" on public.vle_posts;
create policy "vle_posts: insert own state+district+slot only" on public.vle_posts
  for insert to authenticated
  with check (
    auth.uid() = vle_id
    and state = (select state from public.vle_profiles where id = auth.uid())
    and district = (select district from public.vle_profiles where id = auth.uid())
    and slot = (select slot from public.vle_profiles where id = auth.uid())
  );

drop policy if exists "vle_posts: update own posts only" on public.vle_posts;
create policy "vle_posts: update own posts only" on public.vle_posts
  for update to authenticated
  using (auth.uid() = vle_id)
  with check (
    auth.uid() = vle_id
    and state = (select state from public.vle_profiles where id = auth.uid())
    and district = (select district from public.vle_profiles where id = auth.uid())
    and slot = (select slot from public.vle_profiles where id = auth.uid())
  );
