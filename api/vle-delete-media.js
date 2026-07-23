// Deletes a VLE post's media files from Cloudinary. Called by the
// dashboard right after a post row is deleted from Supabase (vle-dashboard.js)
// — Cloudinary's destroy call needs a signature made with the secret API
// key, which only ever lives here server-side, never in the browser (same
// reasoning as vle-upload-signature.js). No Cloudinary SDK needed — destroy
// is just a signed POST, computable with Node's built-in `crypto` module.
//
// Auth: caller must be a logged-in VLE. This route only deletes public_ids
// that live under `vle/<type>/<that VLE's own user id>/...` (the folder
// layout vle-upload-signature.js writes) — so one VLE's session can never
// be used to delete another VLE's files even if a public_id were
// guessed/leaked.

const crypto = require('crypto');

const SUPABASE_URL = 'https://cykkclkfimmqbahanidg.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5a2tjbGtmaW1tcWJhaGFuaWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNzYxODAsImV4cCI6MjA4MTY1MjE4MH0.iZEnetgYn7j0ltJyjhxUGZ3nCT7YMxGP3_Qd-agI1C0';

// Cloudinary needs to be told which resource_type a public_id belongs to
// in order to destroy it. Deterministic from which field it came from —
// see vle-dashboard.js: images/videos upload as their own type, PDFs
// upload through the "auto" endpoint but Cloudinary always stores them
// under resource_type "image" (PDFs are treated as image-like assets so
// they can be page-rendered/transformed).
const RESOURCE_TYPE_BY_FOLDER = { images: 'image', pdfs: 'image', videos: 'video' };

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

async function destroyOne(cloudName, apiKey, apiSecret, publicId, resourceType) {
  const timestamp = Math.floor(Date.now() / 1000);
  const toSign = `public_id=${publicId}&timestamp=${timestamp}${apiSecret}`;
  const signature = crypto.createHash('sha1').update(toSign).digest('hex');
  const form = new URLSearchParams({ public_id: publicId, api_key: apiKey, timestamp: String(timestamp), signature });
  const r = await fetch(`https://api.cloudinary.com/v1_1/${cloudName}/${resourceType}/destroy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form.toString(),
  });
  return r.ok;
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
  // items: [{ publicId, folder }] — folder is 'images'|'pdfs'|'videos', used
  // to pick the right Cloudinary resource_type.
  const items = Array.isArray(body && body.items) ? body.items : [];
  if (!items.length) {
    res.status(200).json({ ok: true, deleted: 0 });
    return;
  }

  const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
  const apiKey = process.env.CLOUDINARY_API_KEY;
  const apiSecret = process.env.CLOUDINARY_API_SECRET;
  if (!cloudName || !apiKey || !apiSecret) {
    res.status(500).json({ error: 'Cloudinary not configured on server' });
    return;
  }

  // Only ever delete public_ids that belong to THIS VLE
  // (vle/<folder>/<user.id>/...) — mirrors the R2 version's ownership check.
  const ownPrefix = new RegExp(`^vle/(images|pdfs|videos)/${user.id}/`);
  const own = items.filter((it) => it && typeof it.publicId === 'string' && ownPrefix.test(it.publicId) && RESOURCE_TYPE_BY_FOLDER[it.folder]);

  if (!own.length) {
    res.status(200).json({ ok: true, deleted: 0 });
    return;
  }

  let deleted = 0;
  for (const it of own) {
    try {
      const ok = await destroyOne(cloudName, apiKey, apiSecret, it.publicId, RESOURCE_TYPE_BY_FOLDER[it.folder]);
      if (ok) deleted++;
    } catch (e) {
      // Best-effort — the Supabase post row is already gone by the time
      // this is called, so a storage-cleanup failure shouldn't read as a
      // hard error to the VLE. Orphaned files just sit in Cloudinary
      // (25GB free tier is generous).
      console.error('Cloudinary destroy failed:', e);
    }
  }
  res.status(200).json({ ok: true, deleted });
};
