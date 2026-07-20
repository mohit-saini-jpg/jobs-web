/**
 * google-index-diagnose.js — one-off diagnostic (NOT part of the daily pipeline)
 * ============================================================================
 * Asks Google's URL Inspection API for the FULL indexing verdict on a sample
 * of URLs (not just the boolean "is it indexed" used by google-index-submit.js)
 * — coverageState, verdict, robotsTxtState, pageFetchState, lastCrawlTime,
 * googleCanonical vs userCanonical. This is the same data GSC's own "Page
 * Indexing" report is built from, queried directly via API so we don't need
 * interactive GSC UI access to see WHY a sample of pages isn't indexed yet.
 *
 * Run manually: node .github/workflows/google-index-diagnose.js
 * Required env: GOOGLE_INDEXING_SA_JSON (same secret as the daily submitter).
 */
'use strict';

const https  = require('https');
const crypto = require('crypto');
const fs     = require('fs');
const path   = require('path');

const HOST = 'www.topsarkarijobs.com';
const SITE = `https://${HOST}`;

const RAW = process.env.GOOGLE_INDEXING_SA_JSON || '';
if (!RAW.trim()) { console.error('❌ GOOGLE_INDEXING_SA_JSON not set'); process.exit(1); }
let SA;
try { SA = JSON.parse(RAW); } catch (e) { console.error('❌ bad JSON in secret'); process.exit(1); }
const CLIENT_EMAIL = SA.client_email || '';
const PRIVATE_KEY  = String(SA.private_key || '').replace(/\\n/g, '\n');

function b64url(input) {
  return Buffer.from(input).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function buildAssertion() {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: 'RS256', typ: 'JWT' };
  const claim = {
    iss: CLIENT_EMAIL,
    scope: 'https://www.googleapis.com/auth/indexing https://www.googleapis.com/auth/webmasters.readonly',
    aud: 'https://oauth2.googleapis.com/token',
    iat: now, exp: now + 3600,
  };
  const unsigned = b64url(JSON.stringify(header)) + '.' + b64url(JSON.stringify(claim));
  const signer = crypto.createSign('RSA-SHA256');
  signer.update(unsigned);
  const signature = signer.sign(PRIVATE_KEY).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return unsigned + '.' + signature;
}
function httpsRequest(options, body) {
  return new Promise((resolve) => {
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (c) => { data += c; });
      res.on('end', () => resolve({ status: res.statusCode, body: data }));
    });
    req.on('error', (e) => resolve({ status: 0, body: String(e && e.message || e) }));
    req.setTimeout(15000, () => { req.destroy(); resolve({ status: 0, body: 'timeout' }); });
    if (body) req.write(body);
    req.end();
  });
}
async function getAccessToken() {
  const assertion = buildAssertion();
  const form = 'grant_type=' + encodeURIComponent('urn:ietf:params:oauth:grant-type:jwt-bearer') + '&assertion=' + encodeURIComponent(assertion);
  const res = await httpsRequest({
    hostname: 'oauth2.googleapis.com', path: '/token', method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': Buffer.byteLength(form) },
  }, form);
  if (res.status !== 200) { console.error(`❌ token exchange failed (${res.status}): ${res.body.slice(0,300)}`); return null; }
  return JSON.parse(res.body).access_token;
}
async function inspect(token, url, siteUrl) {
  const body = JSON.stringify({ inspectionUrl: url, siteUrl });
  const res = await httpsRequest({
    hostname: 'searchconsole.googleapis.com', path: '/v1/urlInspection/index:inspect', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token, 'Content-Length': Buffer.byteLength(body) },
  }, body);
  if (res.status !== 200) return { url, siteUrl, error: `HTTP ${res.status}: ${res.body.slice(0,200)}` };
  try {
    const r = JSON.parse(res.body)?.inspectionResult?.indexStatusResult || {};
    return {
      url,
      verdict: r.verdict,
      coverageState: r.coverageState,
      robotsTxtState: r.robotsTxtState,
      indexingState: r.indexingState,
      pageFetchState: r.pageFetchState,
      lastCrawlTime: r.lastCrawlTime,
      googleCanonical: r.googleCanonical,
      userCanonical: r.userCanonical,
      sitemap: r.sitemap,
      crawledAs: r.crawledAs,
    };
  } catch (e) { return { url, error: 'parse error: ' + e.message }; }
}

// ── Sample: a spread across page types + ages ───────────────────────────────
function readJobUrlsSample() {
  const jobsDir = path.join(process.cwd(), 'jobs');
  let slugs = [];
  try { slugs = fs.readdirSync(jobsDir, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name); } catch (e) {}
  const oldest = slugs.slice(0, 4);
  const newestFromPosted = [];
  try {
    const lines = fs.readFileSync(path.join(process.cwd(), 'posted_jobs.txt'), 'utf8')
      .split('\n').map(l => l.trim()).filter(l => l.startsWith('http'));
    for (const u of lines.slice(-4)) newestFromPosted.push(u);
  } catch (e) {}
  return { oldest: oldest.map(s => `${SITE}/jobs/${s}/`), newest: newestFromPosted };
}

(async function main() {
  const token = await getAccessToken();
  if (!token) process.exit(1);

  // Try both Search Console property formats — a "Domain" property
  // (sc-domain:example.com, DNS-verified) and a "URL-prefix" property
  // (https://www.example.com/) return "you do not own this site" for
  // urlInspection if you send the wrong one, even with Owner permission.
  const SITE_URL_CANDIDATES = [
    'sc-domain:topsarkarijobs.com',
    `sc-domain:${HOST}`,
    `${SITE}/`,
    'https://topsarkarijobs.com/',
    'http://www.topsarkarijobs.com/',
    'http://topsarkarijobs.com/',
  ];

  console.log('🔎 Testing which Search Console property format is verified...\n');
  for (const siteUrl of SITE_URL_CANDIDATES) {
    const r = await inspect(token, `${SITE}/`, siteUrl);
    console.log('════════════════════════════════════════════════');
    console.log(JSON.stringify(r, null, 2));
  }

  const { oldest, newest } = readJobUrlsSample();
  const urls = [
    `${SITE}/`,
    `${SITE}/section/latest-jobs/`,
    ...newest,
    ...oldest,
  ].filter(Boolean).slice(0, 12);

  console.log(`\n🔎 Inspecting ${urls.length} URLs (using sc-domain: property)...\n`);
  for (const url of urls) {
    const r = await inspect(token, url, `sc-domain:${HOST}`);
    console.log('════════════════════════════════════════════════');
    console.log(JSON.stringify(r, null, 2));
    await new Promise(r2 => setTimeout(r2, 300));
  }
})();
