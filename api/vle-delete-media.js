// Deletes a VLE post's media files from Cloudflare R2. Called by the
// dashboard right after a post row is deleted from Supabase (vle-dashboard.js)
// — R2 deletion needs the secret R2 credentials, which only ever live here
// server-side, never in the browser (same reasoning as vle-upload-url.js).
//
// Auth: caller must be a logged-in VLE. This route only deletes keys that
// live under `<folder>/<that VLE's own user id>/...` (see the key layout
// vle-upload-url.js writes) — so one VLE's session can never be used to
// delete another VLE's files even if a key were guessed/leaked.

const { S3Client, DeleteObjectsCommand } = require('@aws-sdk/client-s3');

const SUPABASE_URL = 'https://cykkclkfimmqbahanidg.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5a2tjbGtmaW1tcWJhaGFuaWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNzYxODAsImV4cCI6MjA4MTY1MjE4MH0.iZEnetgYn7j0ltJyjhxUGZ3nCT7YMxGP3_Qd-agI1C0';

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
  const publicUrls = Array.isArray(body && body.publicUrls) ? body.publicUrls : [];
  if (!publicUrls.length) {
    res.status(200).json({ ok: true, deleted: 0 });
    return;
  }

  const accountId = process.env.R2_ACCOUNT_ID;
  const accessKeyId = process.env.R2_ACCESS_KEY_ID;
  const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY;
  const bucket = process.env.R2_BUCKET_NAME;
  const publicBase = process.env.R2_PUBLIC_URL_BASE;
  if (!accountId || !accessKeyId || !secretAccessKey || !bucket || !publicBase) {
    res.status(500).json({ error: 'R2 not configured on server' });
    return;
  }

  // Only ever delete keys that belong to THIS VLE (folder/<user.id>/...) —
  // strips the public base URL back down to the R2 object key and rejects
  // anything that doesn't match the caller's own uploads.
  const ownPrefix = new RegExp(`^(images|pdfs|videos)/${user.id}/`);
  const keys = publicUrls
    .map((u) => String(u || '').replace(publicBase + '/', ''))
    .filter((k) => ownPrefix.test(k));

  if (!keys.length) {
    res.status(200).json({ ok: true, deleted: 0 });
    return;
  }

  const s3 = new S3Client({
    region: 'auto',
    endpoint: `https://${accountId}.r2.cloudflarestorage.com`,
    credentials: { accessKeyId, secretAccessKey },
  });

  try {
    await s3.send(new DeleteObjectsCommand({
      Bucket: bucket,
      Delete: { Objects: keys.map((Key) => ({ Key })) },
    }));
    res.status(200).json({ ok: true, deleted: keys.length });
  } catch (e) {
    console.error('R2 delete failed:', e);
    // Best-effort — the Supabase post row is already gone by the time this
    // is called, so a storage-cleanup failure shouldn't read as a hard error
    // to the VLE. Orphaned files just sit in R2 (10GB free tier is generous).
    res.status(200).json({ ok: false, error: 'media cleanup failed, post was still deleted' });
  }
};
