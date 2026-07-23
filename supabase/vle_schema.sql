-- District Notice Board & VLE Dashboard — one-time manual setup.
-- Run once in the Supabase SQL Editor (same project as job_form_requests /
-- csc_service_requests / helpdesk_submissions — see config.json).
--
-- VLE accounts are ADMIN-CREATED ONLY (no public signup):
--   1. Supabase Dashboard -> Authentication -> Users -> Add User
--      (set an email + password for the VLE, e.g. sonipat.csc@topsarkarijobs.com)
--   2. Copy that user's UUID, then:
--        insert into public.vle_profiles (id, state, district, slot, center_name, owner_name, shop_address, contact_phone, whatsapp_number)
--        values ('<uuid-from-step-1>', 'Haryana', 'Sonipat', 1, 'Sonipat CSC Center', 'Owner Name', 'Shop address...', '9876543210', '9876543210');
--   That row maps this login to ONE state+district+slot — RLS below
--   enforces that this VLE can only ever post/edit/delete posts for that
--   exact state+district+slot, even if the client-side JS is bypassed
--   entirely.
--
-- `slot` (1-4) exists because every district gets its OWN page per VLE —
-- no VLE wants a stranger's posts mixed onto their page. The first VLE in
-- a district is slot 1 (URL: /vle/<state>/<district>/, no suffix). A
-- SECOND CSC center in the same district goes in slot 2
-- (/vle/<state>/<district>/2/), a third in slot 3, etc, up to slot 4 —
-- generate_all.py pre-builds all 4 slot pages for every district (showing
-- a friendly "no VLE here yet" state until one is assigned), so adding
-- VLE #2/#3/#4 to an already-used district never needs a new site
-- generation, just this insert.
--
-- Supported states/districts are whatever VLE_STATE_DISTRICTS in
-- generate_all.py lists (that's what controls which /vle/<state>/<district>/
-- public pages actually get built) — currently Haryana, Delhi, Punjab,
-- Uttar Pradesh, Rajasthan.

create table if not exists public.vle_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  state text not null,
  district text not null,
  slot smallint not null default 1 check (slot between 1 and 4),
  center_name text not null,
  owner_name text,
  shop_address text,
  contact_phone text,
  whatsapp_number text not null,
  created_at timestamptz not null default now(),
  unique (state, district, slot)
);

create table if not exists public.vle_posts (
  id bigint generated always as identity primary key,
  vle_id uuid not null references public.vle_profiles(id) on delete cascade,
  state text not null,
  district text not null,
  slot smallint not null default 1,
  title text not null,
  description text,
  image_url text,
  image_public_id text,   -- Cloudinary public_id, needed to delete the asset later
  pdf_url text,
  pdf_public_id text,
  video_type text,        -- 'youtube' | 'instagram' | 'upload' | null
  video_url text,
  video_public_id text,   -- only set when video_type = 'upload'
  cta_text text not null default 'Ghar Baithe Form Bharwayein',
  whatsapp_number text not null,
  expiry_date date not null,
  created_at timestamptz not null default now()
);

create index if not exists vle_posts_state_district_slot_idx on public.vle_posts (state, district, slot);
create index if not exists vle_posts_vle_id_idx on public.vle_posts (vle_id);

alter table public.vle_profiles enable row level security;
alter table public.vle_posts enable row level security;

-- Profiles: readable by anyone (public district page shows center name /
-- address / contact in its header) — never writable by anon/authenticated
-- clients, only by admin via the Supabase Dashboard/SQL Editor directly.
create policy "vle_profiles: public read" on public.vle_profiles
  for select to anon, authenticated using (true);

-- Posts: public can see only non-expired posts; a logged-in VLE can also
-- see their OWN posts regardless of expiry (so the dashboard's "my posts"
-- list still shows already-expired ones for management/deletion).
create policy "vle_posts: public read active + own read all" on public.vle_posts
  for select to anon, authenticated
  using (expiry_date >= current_date or auth.uid() = vle_id);

-- Insert: a VLE may only create a post for THEIR OWN mapped state+district+
-- slot — this is the core "Sonipat_CSC can only post for
-- /vle/haryana/sonipat" rule, enforced at the database level (not just
-- trusted from client-side JS).
create policy "vle_posts: insert own state+district+slot only" on public.vle_posts
  for insert to authenticated
  with check (
    auth.uid() = vle_id
    and state = (select state from public.vle_profiles where id = auth.uid())
    and district = (select district from public.vle_profiles where id = auth.uid())
    and slot = (select slot from public.vle_profiles where id = auth.uid())
  );

create policy "vle_posts: update own posts only" on public.vle_posts
  for update to authenticated
  using (auth.uid() = vle_id)
  with check (
    auth.uid() = vle_id
    and state = (select state from public.vle_profiles where id = auth.uid())
    and district = (select district from public.vle_profiles where id = auth.uid())
    and slot = (select slot from public.vle_profiles where id = auth.uid())
  );

create policy "vle_posts: delete own posts only" on public.vle_posts
  for delete to authenticated
  using (auth.uid() = vle_id);
