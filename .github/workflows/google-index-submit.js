/**
 * google-index-submit.js — Smart Google Indexing API submitter (quota-safe)
 * =========================================================================
 * Google's Indexing API is officially supported for pages with JobPosting
 * structured data (this site's /jobs/ pages) — it asks Googlebot to (re)crawl
 * a URL far sooner than the normal sitemap crawl. Perfect for a jobs site
 * where new postings must get indexed fast.
 *
 * WHY "SMART": the free quota is 200 URL notifications/project/DAY. The auto
 * pipeline can run several times a day (morning FJA scrape push + any manual
 * SR-data upload), and a naive submitter would resubmit the same URLs each
 * run and blow the quota. This version keeps a small committed state file so
 * that, no matter how many times it runs in a day, it NEVER exceeds the daily
 * cap and NEVER submits the same URL twice in a day. It also drains the
 * backlog of older /jobs/ pages that were never submitted, a slice per day.
 *
 * SELF-CORRECTING (2026-07-14): done_slugs only ever recorded pages *this
 * script* submitted — but Google indexes plenty of pages organically via
 * sitemap/internal-link crawling too, completely invisible to that record.
 * A one-off GSC export showed 244 of 246 already-indexed /jobs/ pages had
 * never been touched by this script, so they kept getting silently re-queued
 * and wasted part of the daily quota on pages that needed no help. Now,
 * before spending a real Indexing-API submission on a new/backlog candidate,
 * the script asks Google's URL Inspection API (separate 2000/day quota,
 * same already-verified service account) whether it's already indexed. If
 * yes, it's recorded into done_slugs for free and skipped; only genuinely
 * un-indexed pages consume the scarce 200/day submission budget. This keeps
 * done_slugs continuously accurate with zero manual GSC exports going
 * forward.
 *
 * Priority order within each day's remaining budget:
 *   1. Hub/section pages (change daily — always submitted, never checked;
 *      it's a "please recrawl, content changed" ping, not an index check)
 *   2. NEW job pages (newest first from posted_jobs.txt) — checked, then
 *      fast-indexed if not already
 *   3. OLD backlog job pages (never submitted yet) — checked, then indexed
 *      oldest-first if not already
 * Once every /jobs/ page has been submitted or confirmed indexed, only #1 +
 * #2 remain, which comfortably fit under the daily cap.
 *
 * Called by auto-update-jobs.yml via:  node .github/workflows/google-index-submit.js
 *
 * Required env:
 *   GOOGLE_INDEXING_SA_JSON  — the FULL service-account JSON (GitHub Secret).
 *
 * State file (committed by the workflow step that follows this one):
 *   data/google_index_state.json
 *     { date, count_today, submitted_today[], done_slugs[] }
 *   - count_today / submitted_today reset each day (fresh budget + dedup)
 *   - done_slugs is permanent (which /jobs/ slugs have EVER been submitted)
 *
 * Zero external dependencies — Node.js built-ins only. Never throws: every
 * failure is logged and it still exits 0 so it can be a non-blocking step.
 * ─────────────────────────────────────────────────────────────────────────
 * ONE-TIME SETUP (already done for this repo):
 *   1. Google Cloud Console → enable "Indexing API".
 *   2. Service account + JSON key.
 *   3. Search Console → Settings → Users and permissions → Add the service
 *      account client_email as OWNER.
 *   4. GitHub secret GOOGLE_INDEXING_SA_JSON = the entire JSON key file.
 */

'use strict';

const https  = require('https');
const crypto = require('crypto');
const fs     = require('fs');
const path   = require('path');

const HOST = 'www.topsarkarijobs.com';
const SITE = `https://${HOST}`;

// Google Indexing API free quota. Kept at the real limit; the 429 handler is
// the ultimate safety net if the day-boundary ever misaligns with Google's.
const DAILY_CAP = 200;

const STATE_FILE = path.join(process.cwd(), 'data', 'google_index_state.json');
const JOBS_DIR   = path.join(process.cwd(), 'jobs');

// Hub / section pages: their listings change every day, so re-submitting them
// once per day (dedup handles multiple runs) is legitimate and useful.
const HUB_PAGES = [
  `${SITE}/`,
  `${SITE}/section/latest-jobs/`,
  `${SITE}/section/latest-jobs-new/`,
  `${SITE}/section/results/`,
  `${SITE}/section/admit-card/`,
  `${SITE}/section/answer-key/`,
  `${SITE}/section/today-updates/`,
  `${SITE}/section/upcoming-jobs/`,
  `${SITE}/app/`,
];

// ── Load + validate the service-account credential ─────────────────────────
const RAW = process.env.GOOGLE_INDEXING_SA_JSON || '';
if (!RAW.trim()) {
  console.warn('⚠️  GOOGLE_INDEXING_SA_JSON not set — skipping Google Indexing API (fine if the secret is not added yet).');
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
    // webmasters.readonly added (2026-07-14) so the same already-verified
    // service account (it must already be a Search Console OWNER for the
    // indexing scope to work at all — see setup note above) can also call
    // the URL Inspection API. That lets us ask Google directly "is this
    // already indexed?" instead of guessing from our own submit history,
    // which was drifting badly: a GSC export showed 244 of 246 indexed
    // /jobs/ pages had never gone through this script (organic sitemap/
    // link discovery), so they kept getting silently re-queued for
    // submission, burning part of the 200/day quota on pages that needed
    // no help.
    scope: 'https://www.googleapis.com/auth/indexing https://www.googleapis.com/auth/webmasters.readonly',
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

// ── Daily state (committed to the repo so it survives across runs) ─────────
function todayIST() {
  // Consistent day boundary for our own budget counter (Asia/Kolkata). The
  // 429 handler covers any misalignment with Google's own quota reset.
  return new Date(Date.now() + 5.5 * 3600 * 1000).toISOString().slice(0, 10);
}

function loadState() {
  let s;
  try {
    s = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  } catch (e) {
    s = {};
  }
  if (!s || typeof s !== 'object') s = {};
  if (s.date !== todayIST()) {
    // New day → reset the daily counters, KEEP the permanent backlog record.
    s.date = todayIST();
    s.count_today = 0;
    s.submitted_today = [];
  }
  if (!Array.isArray(s.submitted_today)) s.submitted_today = [];
  if (!Array.isArray(s.done_slugs))      s.done_slugs = [];
  if (typeof s.count_today !== 'number') s.count_today = 0;
  return s;
}

function saveState(s) {
  try {
    fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
    fs.writeFileSync(STATE_FILE, JSON.stringify(s));
  } catch (e) {
    console.warn('⚠️  Could not write state file:', e && e.message);
  }
}

// ── URL sources ─────────────────────────────────────────────────────────────
function slugFromJobUrl(url) {
  const m = String(url).match(/\/jobs\/([^/]+)\/?$/);
  return m ? m[1] : null;
}

// Newest job URLs first (posted_jobs.txt is appended chronologically → tail is
// freshest). These are the "new jobs" we want indexed fastest.
function readNewestJobUrls() {
  const out = [];
  try {
    const p = path.join(process.cwd(), 'posted_jobs.txt');
    if (fs.existsSync(p)) {
      const lines = fs.readFileSync(p, 'utf8')
        .split('\n').map((l) => l.trim()).filter((l) => l.startsWith('http'));
      // last 250 newest, reversed so the very newest go first
      for (const url of lines.slice(-250).reverse()) out.push(url);
    }
  } catch (e) {
    console.warn('⚠️  Could not read posted_jobs.txt:', e && e.message);
  }
  return out;
}

// Every /jobs/<slug>/ page currently on disk (for backlog coverage).
function listAllJobSlugs() {
  try {
    return fs.readdirSync(JOBS_DIR, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name);
  } catch (e) {
    return [];
  }
}

// ── NEVER SUBMIT A BROKEN URL (2026-07-14) ──────────────────────────────────
// Root cause of a live 404 (pau-young-professional-ii-...) reaching Google:
// a slug-computation mismatch in generate_all.py wrote a redirect/candidate
// that pointed at a page that was never actually rendered. That class of bug
// is now fixed at the source (generate_all.py) plus a build-time guard that
// heals any dead-end redirect — but THIS script is the last checkpoint
// before a URL reaches Google, so it re-verifies independently: only a URL
// that (a) is not itself a redirect origin in _redirects, and (b) resolves
// to a real index.html in this exact repo checkout (the same checkout
// Vercel deploys from) is eligible for submission. Zero cost — no network
// calls, pure filesystem/text checks — so it's safe to run on every URL.
let REDIRECT_SOURCES = new Set();
try {
  const rtext = fs.readFileSync(path.join(process.cwd(), '_redirects'), 'utf8');
  for (const line of rtext.split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const m = t.match(/^(\/\S+)\s+\/\S*\s+301/);
    if (m) REDIRECT_SOURCES.add(m[1]);
  }
} catch (e) { /* _redirects missing — cross-check simply skipped */ }

function urlIsRealPage(url) {
  try {
    const u = new URL(url);
    const p = u.pathname;
    if (REDIRECT_SOURCES.has(p)) return false;   // this URL 301s elsewhere — submit the destination, not this
    if (p === '/') return fs.existsSync(path.join(process.cwd(), 'index.html'));
    const clean = p.replace(/^\/+|\/+$/g, '');
    if (!clean) return false;
    return fs.existsSync(path.join(process.cwd(), clean, 'index.html'));
  } catch (e) {
    return false;
  }
}

// Build the prioritised submit list, skipping anything already sent today.
function collectCandidates(state) {
  const submittedToday = new Set(state.submitted_today);
  const doneSlugs      = new Set(state.done_slugs);
  const out = [];
  const seen = new Set();
  let skippedBroken = 0;
  // slug is set only for /jobs/ URLs (backlog tracking); hub pages have none.
  // kind: 'hub' | 'new' | 'backlog' — for accurate log counts only.
  const add = (url, slug, kind) => {
    if (!url || seen.has(url) || submittedToday.has(url)) return;
    if (!urlIsRealPage(url)) { skippedBroken++; return; }
    seen.add(url);
    out.push({ url, slug: slug || null, kind });
  };

  // 1. Hub / section pages (daily) — always eligible once per day.
  HUB_PAGES.forEach((u) => add(u, null, 'hub'));

  // 2. NEW job pages — newest first.
  for (const url of readNewestJobUrls()) add(url, slugFromJobUrl(url), 'new');

  // 3. OLD backlog — job slugs on disk that were never submitted.
  for (const slug of listAllJobSlugs()) {
    if (doneSlugs.has(slug)) continue;
    add(`${SITE}/jobs/${slug}/`, slug, 'backlog');
  }

  out.skippedBroken = skippedBroken;
  return out;
}

// ── Ask Google directly: is this URL already indexed? ──────────────────────
// URL Inspection API quota is a generous 2000 queries/day/property (separate
// pool from the 200/day Indexing API cap), so checking before submitting
// costs us nothing that matters. Returns true only on the unambiguous
// "Submitted and indexed" coverage state — anything else (not yet crawled,
// excluded, error, etc.) falls through to a real submission as before.
async function isAlreadyIndexed(token, url) {
  const body = JSON.stringify({ inspectionUrl: url, siteUrl: SITE + '/' });
  const res = await httpsRequest({
    hostname: 'searchconsole.googleapis.com',
    path: '/v1/urlInspection/index:inspect',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
      'Content-Length': Buffer.byteLength(body),
    },
  }, body);
  if (res.status !== 200) return { indexed: false, checked: false };
  try {
    const coverage = JSON.parse(res.body)
      ?.inspectionResult?.indexStatusResult?.coverageState || '';
    return { indexed: coverage === 'Submitted and indexed', checked: true };
  } catch (e) {
    return { indexed: false, checked: false };
  }
}

// ── Publish one URL notification ───────────────────────────────────────────
async function publish(token, url) {
  const body = JSON.stringify({ url, type: 'URL_UPDATED' });
  return httpsRequest({
    hostname: 'indexing.googleapis.com',
    path: '/v3/urlNotifications:publish',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
      'Content-Length': Buffer.byteLength(body),
    },
  }, body);
}

// ── Main ───────────────────────────────────────────────────────────────────
(async function main() {
  const token = await getAccessToken();
  if (!token) {
    console.warn('⚠️  No access token — skipping Google Indexing submission (workflow continues).');
    process.exit(0);
  }

  const state = loadState();
  const budget = DAILY_CAP - state.count_today;
  const totalJobs = listAllJobSlugs().length;
  const backlogLeft = Math.max(0, totalJobs - state.done_slugs.length);

  if (budget <= 0) {
    console.log(`✅ Daily budget already used (${state.count_today}/${DAILY_CAP}) — nothing submitted this run. Backlog remaining: ${backlogLeft}. Resets tomorrow (IST).`);
    saveState(state);   // still persist (keeps date fresh)
    process.exit(0);
  }

  const candidates = collectCandidates(state);
  if (candidates.skippedBroken) {
    console.warn(`🛡️  Skipped ${candidates.skippedBroken} candidate URL(s) that don't resolve to a real page (redirect origin or missing index.html) — never submitted to Google.`);
  }
  console.log(`📡 Google Indexing — day ${state.date} | used ${state.count_today}/${DAILY_CAP} | budget ${budget} | candidates ${candidates.length} | backlog left ${backlogLeft}`);

  const doneSet = new Set(state.done_slugs);
  let ok = 0, hubOk = 0, newOk = 0, backlogOk = 0, quotaStopped = false, forbidden = 0, other = 0;
  let inspected = 0, alreadyIndexed = 0;
  const INSPECT_CAP = 500;  // stay well under the 2000/day, 600/min URL Inspection quota

  // Pass 1: hub pages always submit unconditionally (freshness ping, not an
  // "is it indexed" question) — never checked, never skipped.
  const toSubmit = candidates.filter((c) => c.kind === 'hub').slice(0, budget);

  // Pass 2: for new/backlog job pages, ask Google first. Already-indexed ones
  // get recorded into done_slugs for free (no Indexing-API quota spent) so
  // done_slugs stays continuously accurate instead of drifting like before.
  // Genuinely not-indexed ones queue for a real submission.
  for (const item of candidates) {
    if (item.kind === 'hub') continue;
    if (toSubmit.length >= budget) break;   // already have enough to fill today's budget
    if (inspected >= INSPECT_CAP) break;    // hit the inspection safety cap for this run

    inspected++;
    const { indexed } = await isAlreadyIndexed(token, item.url);
    if (indexed) {
      alreadyIndexed++;
      if (item.slug && !doneSet.has(item.slug)) {
        doneSet.add(item.slug);
        state.done_slugs.push(item.slug);
      }
      continue;
    }
    toSubmit.push(item);
    if (inspected % 50 === 0) saveState(state);  // periodic save mid-inspection pass
  }

  for (const item of toSubmit) {
    const res = await publish(token, item.url);
    if (res.status === 200) {
      ok++;
      state.count_today++;
      state.submitted_today.push(item.url);
      if (item.slug && !doneSet.has(item.slug)) {
        doneSet.add(item.slug);
        state.done_slugs.push(item.slug);
      }
      if (item.kind === 'hub') hubOk++;
      else if (item.kind === 'new') newOk++;
      else backlogOk++;
      // periodic save so a mid-run crash doesn't lose progress
      if (ok % 25 === 0) saveState(state);
    } else if (res.status === 429) {
      quotaStopped = true;
      console.warn('⚠️  Daily quota reached (429) — stopping early. Remaining go out next run.');
      break;
    } else if (res.status === 403) {
      forbidden++;
      console.warn('⚠️  403 Permission denied — is the service account an OWNER in Search Console? ' + String(res.body).slice(0, 160));
      break;   // 403 applies to every URL — no point continuing
    } else {
      other++;
      if (other <= 3) console.warn(`⚠️  ${item.url} → ${res.status}: ${String(res.body).slice(0, 140)}`);
    }
  }

  saveState(state);
  const backlogAfter = Math.max(0, totalJobs - state.done_slugs.length);
  console.log(`🔎 Inspected ${inspected} candidate(s) — ${alreadyIndexed} already indexed by Google (recorded free, no quota spent)`);
  console.log(`✅ Google Indexing done — submitted ${ok} (hub ${hubOk}, new ${newOk}, backlog ${backlogOk}) | today ${state.count_today}/${DAILY_CAP} | quota-stopped ${quotaStopped ? 'yes' : 'no'} | forbidden ${forbidden} | other ${other}`);
  console.log(`   📊 Backlog: ${state.done_slugs.length}/${totalJobs} job pages ever submitted — ${backlogAfter} remaining.`);
  process.exit(0);
})().catch((e) => {
  console.warn('⚠️  Unexpected error (ignored):', e && e.message);
  process.exit(0);
});
