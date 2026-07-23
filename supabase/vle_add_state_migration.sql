-- Migration: add `state` support to the VLE Dashboard (multi-state rollout
-- beyond Haryana: Delhi, Punjab, Uttar Pradesh, Rajasthan).
-- Run this ONCE in the Supabase SQL Editor — only needed if you already ran
-- the original vle_schema.sql (which had no `state` column). Safe to run
-- even with existing rows (your one real Hisar profile/post gets backfilled
-- to state='Haryana' automatically).

alter table public.vle_profiles add column if not exists state text;
alter table public.vle_posts add column if not exists state text;

-- Backfill: every VLE profile/post created so far was for a Haryana
-- district (the only state supported until now).
update public.vle_profiles set state = 'Haryana' where state is null;
update public.vle_posts set state = 'Haryana' where state is null;

alter table public.vle_profiles alter column state set not null;
alter table public.vle_posts alter column state set not null;

drop index if exists vle_posts_district_idx;
create index if not exists vle_posts_state_district_idx on public.vle_posts (state, district);

-- Replace the district-only RLS insert/update policies with state+district
-- versions (old policies only checked district, which is no longer unique
-- once multiple states are supported).
drop policy if exists "vle_posts: insert own district only" on public.vle_posts;
create policy "vle_posts: insert own state+district only" on public.vle_posts
  for insert to authenticated
  with check (
    auth.uid() = vle_id
    and state = (select state from public.vle_profiles where id = auth.uid())
    and district = (select district from public.vle_profiles where id = auth.uid())
  );

drop policy if exists "vle_posts: update own posts only" on public.vle_posts;
create policy "vle_posts: update own posts only" on public.vle_posts
  for update to authenticated
  using (auth.uid() = vle_id)
  with check (
    auth.uid() = vle_id
    and state = (select state from public.vle_profiles where id = auth.uid())
    and district = (select district from public.vle_profiles where id = auth.uid())
  );
