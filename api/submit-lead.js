// "Form Filling Request" lead capture — receives the job-page widget's
// submission (job-form-widget.js), inserts it into Supabase, then fires an
// admin Telegram alert.
//
// Runs server-side (not a direct browser->Supabase insert like the existing
// helpdesk/govt-services forms) specifically so the Telegram bot token never
// has to be exposed to client JS — a token embedded in the page would let
// anyone spam the admin chat within hours on a public site, same reasoning
// as api/chat.js keeping GROQ_API_KEY server-side.
//
// Required Vercel env vars (Project Settings -> Environment Variables):
//   TELEGRAM_BOT_TOKEN    — same bot already used by the scheduled social-
//                           autopost GitHub Action; add it to Vercel too
//                           (GitHub Actions secrets and Vercel env vars are
//                           separate stores, so this needs adding here even
//                           if already set as a repo secret).
//   TELEGRAM_ADMIN_CHAT_ID — chat id for the PRIVATE admin alert (distinct
//                           from the public @TopSarkariJobs channel the
//                           autopost workflow posts to). Get it by messaging
//                           the bot once, then visiting
//                           https://api.telegram.org/bot<TOKEN>/getUpdates
//                           and reading "chat":{"id": ...} from the reply.
//
// The Supabase anon key below is the SAME public key already committed in
// config.json / used by the helpdesk and govt-services forms — safe to
// reuse (protected by the table's own Row Level Security policy, which only
// allows anonymous INSERT, not SELECT/UPDATE/DELETE).

const SUPABASE_URL = 'https://cykkclkfimmqbahanidg.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5a2tjbGtmaW1tcWJhaGFuaWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNzYxODAsImV4cCI6MjA4MTY1MjE4MH0.iZEnetgYn7j0ltJyjhxUGZ3nCT7YMxGP3_Qd-agI1C0';
const TABLE = 'job_form_requests';

function isValidPhone(v) {
  return typeof v === 'string' && /^[6-9][0-9]{9}$/.test(v.trim());
}

async function notifyTelegram(lead) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_ADMIN_CHAT_ID;
  if (!token || !chatId) return; // not configured — insert already succeeded, just skip the alert

  const text =
    '🚨 NEW FORM FILLING REQUEST!\n\n' +
    `👤 Name: ${lead.name}\n` +
    `📱 WhatsApp: ${lead.whatsapp}\n` +
    `📍 District: ${lead.district}\n` +
    `💼 Job: ${lead.job_title}\n` +
    `🔗 URL: ${lead.page_url}\n\n` +
    `💬 Direct Chat on WhatsApp: https://wa.me/91${lead.whatsapp}`;

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

  const name = String(body.name || '').trim().slice(0, 120);
  const whatsapp = String(body.whatsapp || '').trim();
  const district = String(body.district || '').trim().slice(0, 60);
  const job_title = String(body.job_title || '').trim().slice(0, 250);
  const page_url = String(body.page_url || '').trim().slice(0, 500);

  // Never trust client-side validation alone — re-check server-side.
  if (!name) { res.status(400).json({ error: 'name is required' }); return; }
  if (!isValidPhone(whatsapp)) { res.status(400).json({ error: 'valid 10-digit WhatsApp number is required' }); return; }
  if (!district) { res.status(400).json({ error: 'district is required' }); return; }

  const lead = { name, whatsapp, district, job_title, page_url };

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

  // Fire-and-forget-ish: awaited so Vercel doesn't kill the function before
  // the Telegram call completes, but its own failure never fails the request
  // (the lead is already safely stored).
  await notifyTelegram(lead);

  res.status(200).json({ ok: true });
};
