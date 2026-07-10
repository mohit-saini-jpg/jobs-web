/**
 * google-index-submit.js — Submit fresh job URLs to the Google Indexing API
 * =========================================================================
 * Google's Indexing API is officially supported for pages with JobPosting
 * structured data (exactly this site) — it asks Googlebot to (re)crawl a URL
 * far sooner than waiting for the normal sitemap crawl. Perfect for a jobs
 * site where new postings must get indexed fast.
 *
 * Called by auto-update-jobs.yml via:  node .github/workflows/google-index-submit.js
 *
 * Required env:
 *   GOOGLE_INDEXING_SA_JSON  — the FULL service-account JSON (GitHub Secret).
 *                              Contains a private_key; never store it in the repo.
 *
 * The service-account email MUST be added as an *Owner* of the property in
 * Google Search Console, or every publish call returns 403 (see SETUP below).
 *
 * Zero external dependencies — uses only Node.js built-ins (crypto, https, fs).
 * Never throws: every failure is logged and the process still exits 0 so it
 * can run as a non-blocking, continue-on-error workflow step.
 *
 * Quota: Google allows 200 URL notifications/project/day by default. We cap
 * per-run submissions well under that and prioritise the newest postings.
 * ─────────────────────────────────────────────────────────────────────────
 * ONE-TIME SETUP (do this once, then it runs automatically forever):
 *   1. Google Cloud Console → enable the "Indexing API" for your project.
 *   2. Create a service account + JSON key (you already have this).
 *   3. Google Search Console → your property → Settings → Users and
 *      permissions → Add user → paste the service account's client_email
 *      → role: OWNER.  (Verified-Owner is what the API checks.)
 *   4. GitHub → repo → Settings → Secrets and variables → Actions →
 *      New repository secret → name: GOOGLE_INDEXING_SA_JSON,
 *      value: paste the ENTIRE contents of the JSON key file.
 *   Done. New jobs get pinged to Google on every clean auto-update run.
 */

'use strict';

const https  = require('https');
const crypto = require('crypto');
const fs     = require('fs');
const path   = require('path');

const HOST = 'www.topsarkarijobs.com';
const SITE = `https://${HOST}`;

// Cap per run — stays safely under the 200/day project quota even if the
// workflow fires several times in a day. Newest jobs are submitted first.
const MAX_URLS = 150;

// ── Load + validate the service-account credential ─────────────────────────
const RAW = process.env.GOOGLE_INDEXING_SA_JSON || '';
if (!RAW.trim()) {
  console.warn('⚠️  GOOGLE_INDEXING_SA_JSON not set — skipping Google Indexing API (this is fine if you have not added the secret yet).');
  process.exit(0);
}

let SA;
try {
  SA = JSON.parse(RAW);
} catch (e) {
  console.warn('⚠️  GOOGLE_INDEXING_SA_JSON is not valid JSON — skipping. Paste the ENTIRE key file as the secret value.');
  process.exit(0);
}

const CLIENT_EMAIL = SA.client_email || '';
// GitHub secrets round-trip fine, but if the private key ever arrives with
// escaped newlines, normalise them so the PEM parses.
const PRIVATE_KEY  = String(SA.private_key || '').replace(/\\n/g, '\n');

if (!CLIENT_EMAIL || !PRIVATE_KEY) {
  console.warn('⚠️  Service-account JSON missing client_email / private_key — skipping.');
  process.exit(0);
}

// ── base64url helper ───────────────────────────────────────────────────────
function b64url(input) {
  return Buffer.from(input)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

// ── Build + sign a JWT (RS256) for the OAuth2 token exchange ───────────────
function buildAssertion() {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: 'RS256', typ: 'JWT' };
  const claim = {
    iss:   CLIENT_EMAIL,
    scope: 'https://www.googleapis.com/auth/indexing',
    aud:   'https://oauth2.googleapis.com/token',
    iat:   now,
    exp:   now + 3600,
  };
  const unsigned = b64url(JSON.stringify(header)) + '.' + b64url(JSON.stringify(claim));
  const signer = crypto.createSign('RSA-SHA256');
  signer.update(unsigned);
  const signature = signer.sign(PRIVATE_KEY)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return unsigned + '.' + signature;
}

// ── Small promise wrapper around https.request ─────────────────────────────
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

// ── Exchange the signed JWT for an OAuth2 access token ─────────────────────
async function getAccessToken() {
  let assertion;
  try {
    assertion = buildAssertion();
  } catch (e) {
    console.warn('⚠️  Could not sign JWT (bad private_key?):', e && e.message);
    return null;
  }
  const form = 'grant_type=' + encodeURIComponent('urn:ietf:params:oauth:grant-type:jwt-bearer') +
               '&assertion=' + encodeURIComponent(assertion);
  const res = await httpsRequest({
    hostname: 'oauth2.googleapis.com',
    path: '/token',
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Content-Length': Buffer.byteLength(form),
    },
  }, form);

  if (res.status !== 200) {
    console.warn(`⚠️  Token exchange failed (${res.status}): ${res.body.slice(0, 200)}`);
    return null;
  }
  try {
    const tok = JSON.parse(res.body).access_token;
    if (!tok) { console.warn('⚠️  Token response had no access_token.'); return null; }
    return tok;
  } catch (e) {
    console.warn('⚠️  Could not parse token response.');
    return null;
  }
}

// ── Collect the URLs to submit (newest jobs first) ─────────────────────────
function collectUrls() {
  const urls = [];
  const seen = new Set();
  const add = (u) => { if (u && !seen.has(u)) { seen.add(u); urls.push(u); } };

  // Key hub pages — legitimately change every run as new jobs list on them.
  [
    `${SITE}/`,
    `${SITE}/section/latest-jobs/`,
    `${SITE}/section/latest-jobs-new/`,
    `${SITE}/section/results/`,
    `${SITE}/section/admit-card/`,
    `${SITE}/section/answer-key/`,
    `${SITE}/section/today-updates/`,
    `${SITE}/section/upcoming-jobs/`,
  ].forEach(add);

  // Newest job pages: posted_jobs.txt is appended chronologically, so the
  // TAIL is the freshest. These are exactly the "new jobs" we want indexed fast.
  try {
    const candidates = ['posted_jobs.txt', path.join(process.cwd(), 'posted_jobs.txt')];
    for (const p of candidates) {
      if (fs.existsSync(p)) {
        const lines = fs.readFileSync(p, 'utf8')
          .split('\n')
          .map((l) => l.trim())
          .filter((l) => l.startsWith('http'));
        // last ~120 newest, reversed so the very newest go first
        lines.slice(-120).reverse().forEach(add);
        break;
      }
    }
  } catch (e) {
    console.warn('⚠️  Could not read posted_jobs.txt:', e && e.message);
  }

  return urls.slice(0, MAX_URLS);
}

// ── Publish one URL notification ───────────────────────────────────────────
async function publish(token, url) {
  const body = JSON.stringify({ url, type: 'URL_UPDATED' });
  const res = await httpsRequest({
    hostname: 'indexing.googleapis.com',
    path: '/v3/urlNotifications:publish',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
      'Content-Length': Buffer.byteLength(body),
    },
  }, body);
  return res;
}

// ── Main ───────────────────────────────────────────────────────────────────
(async function main() {
  const token = await getAccessToken();
  if (!token) {
    console.warn('⚠️  No access token — skipping Google Indexing submission (workflow continues).');
    process.exit(0);
  }

  const urls = collectUrls();
  console.log(`📡 Google Indexing API: submitting ${urls.length} URL(s) (newest first, cap ${MAX_URLS})...`);

  let ok = 0, quota = 0, forbidden = 0, other = 0;
  for (const url of urls) {
    const res = await publish(token, url);
    if (res.status === 200) {
      ok++;
    } else if (res.status === 429) {
      quota++;
      // Daily quota hit — no point hammering the rest this run.
      console.warn('⚠️  Daily quota (200/day) reached — stopping early. Remaining URLs go out on the next run.');
      break;
    } else if (res.status === 403) {
      forbidden++;
      if (forbidden === 1) {
        console.warn('⚠️  403 Permission denied. The service-account email must be added as an OWNER of the property in Google Search Console. Details: ' + res.body.slice(0, 180));
      }
      // 403 will apply to every URL — stop early instead of spamming.
      break;
    } else {
      other++;
      if (other <= 3) console.warn(`⚠️  ${url} → ${res.status}: ${String(res.body).slice(0, 140)}`);
    }
  }

  console.log(`✅ Google Indexing done — submitted ${ok}, quota-stopped ${quota ? 'yes' : 'no'}, forbidden ${forbidden}, other-errors ${other}.`);
  process.exit(0);
})().catch((e) => {
  console.warn('⚠️  Unexpected error (ignored):', e && e.message);
  process.exit(0);
});
