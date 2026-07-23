-- One-time manual setup for the "Form Filling Request" lead-capture widget
-- (job-form-widget.js/css + api/submit-lead.js). Run this once in the
-- Supabase project's SQL Editor — nothing in the app runs this
-- automatically, there is no DB migration tooling in this repo.
--
-- Same Supabase project already used for csc_service_requests /
-- helpdesk_submissions (see config.json for the project URL/anon key).

create table if not exists public.job_form_requests (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  name text not null,
  whatsapp text not null,
  district text not null,
  job_title text,
  page_url text,
  status text not null default 'Pending'
);

alter table public.job_form_requests enable row level security;

-- api/submit-lead.js inserts using the public anon key (same as the
-- existing csc_service_requests / helpdesk_submissions forms) — without
-- this policy every insert fails with a 401/RLS error. No SELECT/UPDATE/
-- DELETE policy is granted to anon, so submitted leads can only be read
-- from the Supabase dashboard, not by any client.
create policy "Allow anonymous insert" on public.job_form_requests
  for insert
  to anon
  with check (true);
