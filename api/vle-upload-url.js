// Cloudflare R2 presigned-upload URL issuer for the VLE Dashboard.
//
// Media (compressed images, PDFs, short video files) upload DIRECTLY from
// the VLE's browser straight to R2 using a short-lived presigned PUT URL —
// this route only ISSUES that URL, the actual file bytes never pass through
// this Vercel function. That matters because Vercel's Node functions cap
// request bodies (~4.5MB on most plans) and would be slow/costly for video
// uploads; a presigned URL has no such limit and R2 has zero egress fees.
//
// Auth: the caller must be a logged-in VLE (a valid Supabase session token).
// This route only confirms "some real VLE is asking for an upload slot" —
// it does NOT check which district, because the actual post insert is what
// matters for data integrity, and THAT is protected by the vle_posts RLS
// policies (see supabase/vle_schema.sql) regardless of what this endpoint
// allows. Rejecting anonymous callers here just stops randoms from filling
// up the R2 bucket for free.
//
// Required Vercel env vars (Project Settings -> Environment Variables):
//   R2_ACCOUNT_ID         — Cloudflare dashboard -> R2 -> Overview (right side)
//   R2_ACCESS_KEY_ID      — R2 -> Manage API Tokens -> create a token
//   R2_SECRET_ACCESS_KEY  — shown once when the token above is created
//   R2_BUCKET_NAME        — the bucket you create for this (e.g. "tsj-vle-media")
//   R2_PUBLIC_URL_BASE    — the bucket's public base URL, either the
//                           auto-generated https://pub-<id>.r2.dev domain
//                           (enable "Public Access" on the bucket) or a
//                           custom domain you attach to it. No trailing slash.

const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');

const SUPABASE_URL = 'https://cykkclkfimmqbahanidg.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5a2tjbGtmaW1tcWJhaGFuaWRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNzYxODAsImV4cCI6MjA4MTY1MjE4MH0.iZEnetgYn7j0ltJyjhxUGZ3nCT7YMxGP3_Qd-agI1C0';

const ALLOWED_FOLDERS = new Set(['images', 'pdfs', 'videos']);
const ALLOWED_TYPES = {
  images: ['image/webp', 'image/jpeg', 'image/png'],
  pdfs: ['application/pdf'],
  videos: ['video/mp4'],
};
const MAX_BYTES = { images: 2 * 1024 * 1024, pdfs: 15 * 1024 * 1024, videos: 60 * 1024 * 1024 };

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

function safeExt(fileName, fallback) {
  const m = /\.([a-zA-Z0-9]{2,5})$/.exec(fileName || '');
  return (m ? m[1] : fallback).toLowerCase();
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
  body = body || {};

  const folder = String(body.folder || '');
  const fileType = String(body.fileType || '');
  const fileName = String(body.fileName || 'upload');
  const fileSize = Number(body.fileSize || 0);

  if (!ALLOWED_FOLDERS.has(folder)) {
    res.status(400).json({ error: 'invalid folder' });
    return;
  }
  if (!ALLOWED_TYPES[folder].includes(fileType)) {
    res.status(400).json({ error: `invalid file type for ${folder}` });
    return;
  }
  if (fileSize > MAX_BYTES[folder]) {
    res.status(400).json({ error: 'file too large' });
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

  const ext = safeExt(fileName, folder === 'images' ? 'webp' : folder === 'pdfs' ? 'pdf' : 'mp4');
  const key = `${folder}/${user.id}/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;

  const s3 = new S3Client({
    region: 'auto',
    endpoint: `https://${accountId}.r2.cloudflarestorage.com`,
    credentials: { accessKeyId, secretAccessKey },
  });

  try {
    const uploadUrl = await getSignedUrl(
      s3,
      new PutObjectCommand({ Bucket: bucket, Key: key, ContentType: fileType }),
      { expiresIn: 300 }
    );
    res.status(200).json({ uploadUrl, publicUrl: `${publicBase}/${key}` });
  } catch (e) {
    console.error('R2 presign failed:', e);
    res.status(502).json({ error: 'could not create upload URL' });
  }
};
