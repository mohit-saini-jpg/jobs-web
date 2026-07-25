// "Custom Form Apply Request" lead capture — user types the name of ANY
// job/scheme/service they want help applying to (not tied to a specific
// job page), submits it here, which inserts into Supabase then fires the
// same admin Telegram alert as the job-page widget (api/submit-lead.js).
//
// Runs server-side (not a direct browser->Supabase insert like the
// helpdesk/govt-services forms) for the same reason as api/submit-lead.js:
// the Telegram bot token must never be exposed to client JS.
//
// Required Vercel env vars (already set for api/submit-lead.js — reused
// here, nothing new to configure if that's already working):
//   TELEGRAM_BOT_TOKEN
//   TELEGRAM_ADMIN_CHAT_ID
//
// The Supabase anon key below is the SAME public key already committed in
// config.json / used by api/submit-lead.js, helpdesk and govt-services —
// safe to reuse (protected by the table's own Row Level Security policy,
// which only allows anonymous INSERT, not SELECT/UPDATE/DELETE).
//
// REQUIRED ONE-TIME SETUP — run this in the Supabase SQL editor before
// this endpoint will work (table does not exist yet, and this code has no
// way to create it):
//
//   create table public.custom_form_requests (
//     id bigint generated always as identity primary key,
//     created_at timestamptz not null default now(),
//     job_title text not null,
//     name text not null,
//     whatsapp text not null,
//     district text,
//     notes text,
//     page_url text
//   );
//
//   alter table public.custom_form_requests enable row level security;
//
//   create policy "Allow anonymous insert" on public.custom_form_requests
//     for insert
//     to anon
//     with check (true);

const SUPABASE_URL = 'https://cykkclkfimmqbahanidg.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5a2tjbGtmaW1tcWJhaGFuaWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNzYxODAsImV4cCI6MjA4MTY1MjE4MH0.iZEnetgYn7j0ltJyjhxUGZ3nCT7YMxGP3_Qd-agI1C0';
const TABLE = 'custom_form_requests';

function isValidPhone(v) {
  return typeof v === 'string' && /^[6-9][0-9]{9}$/.test(v.trim());
}

async function notifyTelegram(lead) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_ADMIN_CHAT_ID;
  if (!token || !chatId) return; // not configured — insert already succeeded, just skip the alert

  const text =
    '🚨 NEW CUSTOM FORM REQUEST!\n\n' +
    `📝 Job / Scheme / Service: ${lead.job_title}\n` +
    `👤 Name: ${lead.name}\n` +
    `📱 WhatsApp: ${lead.whatsapp}\n` +
    `📍 District/City: ${lead.district || '—'}\n` +
    (lead.notes ? `💬 Notes: ${lead.notes}\n` : '') +
    `\n💬 Direct Chat on WhatsApp: https://wa.me/91${lead.whatsapp}`;

  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text: text, disable_web_page_preview: true }),
    });
  } catch (e) {
    // Best-effort only — the lead is already safely in Supabase even if this fails.
    console.error('Telegram notify failed:', e);
  }
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'method not allowed' });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  body = body || {};

  const job_title = String(body.job_title || '').trim().slice(0, 250);
  const name = String(body.name || '').trim().slice(0, 120);
  const whatsapp = String(body.whatsapp || '').trim();
  const district = String(body.district || '').trim().slice(0, 60);
  const notes = String(body.notes || '').trim().slice(0, 1000);
  const page_url = String(body.page_url || '').trim().slice(0, 500);

  // Never trust client-side validation alone — re-check server-side.
  if (!job_title) { res.status(400).json({ error: 'job_title is required' }); return; }
  if (!name) { res.status(400).json({ error: 'name is required' }); return; }
  if (!isValidPhone(whatsapp)) { res.status(400).json({ error: 'valid 10-digit WhatsApp number is required' }); return; }

  const lead = { job_title, name, whatsapp, district, notes, page_url };

  let sbRes;
  try {
    sbRes = await fetch(`${SUPABASE_URL}/rest/v1/${TABLE}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON,
        'Authorization': `Bearer ${SUPABASE_ANON}`,
        'Prefer': 'return=minimal',
      },
      body: JSON.stringify(lead),
    });
  } catch (e) {
    res.status(502).json({ error: 'supabase request failed' });
    return;
  }

  if (!sbRes.ok) {
    const detail = await sbRes.text().catch(() => '');
    console.error('Supabase insert failed:', sbRes.status, detail);
    res.status(502).json({ error: 'could not save request' });
    return;
  }

  await notifyTelegram(lead);

  res.status(200).json({ ok: true });
};
