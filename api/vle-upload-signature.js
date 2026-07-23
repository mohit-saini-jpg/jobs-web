// Cloudinary signed-upload issuer for the VLE Dashboard.
//
// Media (compressed images, PDFs, short video files) upload DIRECTLY from
// the VLE's browser straight to Cloudinary — this route only ISSUES a
// signature, the actual file bytes never pass through this Vercel function.
// That matters because Vercel's Node functions cap request bodies
// (~4.5MB on most plans) and would be slow/costly for video uploads.
//
// No Cloudinary SDK / npm dependency needed — Cloudinary's upload signature
// is just a SHA-1 hash of the sorted params-to-sign plus the API secret,
// computable with Node's built-in `crypto` module (see CLOUDINARY_DOCS:
// https://cloudinary.com/documentation/signatures).
//
// Auth: the caller must be a logged-in VLE (a valid Supabase session
// token) — same reasoning as the rest of the VLE API routes: this only
// confirms "some real VLE is asking for an upload slot", the actual post
// insert is what matters for data integrity and that's protected by the
// vle_posts RLS policies (see supabase/vle_schema.sql).
//
// Required Vercel env vars (Project Settings -> Environment Variables) —
// all three are on the Cloudinary Dashboard home page, no card required
// for the free ~25GB tier:
//   CLOUDINARY_CLOUD_NAME
//   CLOUDINARY_API_KEY
//   CLOUDINARY_API_SECRET

const crypto = require('crypto');

const SUPABASE_URL = 'https://cykkclkfimmqbahanidg.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5a2tjbGtmaW1tcWJhaGFuaWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNzYxODAsImV4cCI6MjA4MTY1MjE4MH0.iZEnetgYn7j0ltJyjhxUGZ3nCT7YMxGP3_Qd-agI1C0';

const ALLOWED_FOLDERS = new Set(['images', 'pdfs', 'videos']);

async function verifyVleSession(authHeader) {
  if (!authHeader || !authHeader.startsWith('Bearer ')) return null;
  const token = authHeader.slice(7);
  try {
    const res = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
      headers: { apikey: SUPABASE_ANON, Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    const user = await res.json();
    return user && user.id ? user : null;
  } catch (e) {
    return null;
  }
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'method not allowed' });
    return;
  }

  const user = await verifyVleSession(req.headers.authorization);
  if (!user) {
    res.status(401).json({ error: 'not logged in' });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  const folderKey = String((body || {}).folder || '');
  if (!ALLOWED_FOLDERS.has(folderKey)) {
    res.status(400).json({ error: 'invalid folder' });
    return;
  }

  const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
  const apiKey = process.env.CLOUDINARY_API_KEY;
  const apiSecret = process.env.CLOUDINARY_API_SECRET;
  if (!cloudName || !apiKey || !apiSecret) {
    res.status(500).json({ error: 'Cloudinary not configured on server' });
    return;
  }

  // Namespacing uploads under vle/<type>/<this VLE's own user id> lets the
  // delete endpoint verify a public_id actually belongs to the caller
  // before destroying it (same defense used for the R2 version of this).
  const folder = `vle/${folderKey}/${user.id}`;
  const timestamp = Math.floor(Date.now() / 1000);

  // Cloudinary signature: SHA-1 of "key1=value1&key2=value2...<api_secret>"
  // over every param that will also be sent to the upload endpoint, sorted
  // alphabetically by key (file/api_key/signature themselves are excluded).
  const toSign = `folder=${folder}&timestamp=${timestamp}${apiSecret}`;
  const signature = crypto.createHash('sha1').update(toSign).digest('hex');

  res.status(200).json({ signature, timestamp, folder, apiKey, cloudName });
};
