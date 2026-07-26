#!/usr/bin/env node
/**
 * gsc_check_index_status.js — Search Console URL Inspection API sweep.
 * ============================================================================
 * Checks real Google indexing status for a quota-limited, prioritized batch
 * of site URLs and persists the result to data/gsc_index_state.json. Consumed
 * by build_unindexed_feed.py (Python), which prefers this real signal over
 * its publication-age heuristic whenever a URL has been checked here.
 *
 * Auth: copied from the already-working google-index-submit.js /
 * google-index-diagnose.js (same secret, same JWT-signing pattern, same
 * `sc-domain:` property gotcha already solved there — see those files for
 * the original notes). No new Google Cloud setup needed; this reuses the
 * exact service account already granted Owner access in Search Console.
 *
 * WHY ONCE-DAILY, NOT MORE: google-index-daily.yml's header comment records
 * that running Google's Indexing API more than once a day burned quota on
 * 429s from overlapping runs instead of steadily draining the backlog.
 * Applying the same lesson here even though URL Inspection's documented
 * quota (2000/day, 600/min) is larger than Indexing's (~200/day) — one
 * clean run per day, via the same skip-daily-duplicate guard used
 * elsewhere in this repo.
 *
 * Priority order for the day's budget (MAX_CHECKS_PER_RUN):
 *   1. Never-checked URLs (~70% of budget) -- most likely to surface
 *      brand-new pages Google hasn't seen at all yet.
 *   2. Previously-confirmed-unindexed URLs, oldest-checked-first (~30%) --
 *      periodic re-verification so a page that DID get indexed since its
 *      last check can rotate out of the homepage feed and free its slot.
 *   Confirmed-indexed (verdict PASS) URLs are never re-checked -- once
 *   indexed they're very unlikely to become un-indexed, so re-spending
 *   quota on them isn't worth it.
 *
 * Required env: GOOGLE_INDEXING_SA_JSON (same secret as the daily indexing
 * submitter). If unset, exits 0 doing nothing -- build_unindexed_feed.py's
 * age-heuristic fallback keeps the homepage feed working either way.
 */
'use strict';

const https  = require('https');
const crypto = require('crypto');
const fs     = require('fs');
const path   = require('path');

const HOST        = 'www.topsarkarijobs.com';
const SITE        = `https://${HOST}`;
const GSC_PROPERTY = 'sc-domain:topsarkarijobs.com';
const STATE_PATH  = path.join(process.cwd(), 'data', 'gsc_index_state.json');
const JOBS_DIR    = path.join(process.cwd(), 'jobs');

const MAX_CHECKS_PER_RUN   = 1500;   // conservative vs the 2000/day quota
const REQUEST_DELAY_MS     = 250;    // ~4/sec, well under the 600/min burst cap
const NEVER_CHECKED_SHARE  = 0.7;    // fraction of budget spent on unseen URLs

function b64url(input) {
  return Buffer.from(input).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function buildAssertion(clientEmail, privateKey) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: 'RS256', typ: 'JWT' };
  const claim = {
    iss: clientEmail,
    scope: 'https://www.googleapis.com/auth/indexing https://www.googleapis.com/auth/webmasters.readonly',
    aud: 'https://oauth2.googleapis.com/token',
    iat: now, exp: now + 3600,
  };
  const unsigned = b64url(JSON.stringify(header)) + '.' + b64url(JSON.stringify(claim));
  const signer = crypto.createSign('RSA-SHA256');
  signer.update(unsigned);
  const signature = signer.sign(privateKey).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
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

async function getAccessToken(clientEmail, privateKey) {
  const assertion = buildAssertion(clientEmail, privateKey);
  const form = 'grant_type=' + encodeURIComponent('urn:ietf:params:oauth:grant-type:jwt-bearer') + '&assertion=' + encodeURIComponent(assertion);
  const res = await httpsRequest({
    hostname: 'oauth2.googleapis.com', path: '/token', method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': Buffer.byteLength(form) },
  }, form);
  if (res.status !== 200) { console.error(`❌ token exchange failed (${res.status}): ${res.body.slice(0, 300)}`); return null; }
  return JSON.parse(res.body).access_token;
}

async function inspect(token, url) {
  const body = JSON.stringify({ inspectionUrl: url, siteUrl: GSC_PROPERTY });
  const res = await httpsRequest({
    hostname: 'searchconsole.googleapis.com', path: '/v1/urlInspection/index:inspect', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token, 'Content-Length': Buffer.byteLength(body) },
  }, body);
  return res;
}

function readJobSlugs() {
  try {
    return fs.readdirSync(JOBS_DIR, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .filter(d => fs.existsSync(path.join(JOBS_DIR, d.name, 'index.html')))
      .map(d => d.name);
  } catch (e) {
    return [];
  }
}

function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8')); } catch (e) { return {}; }
}

function buildCheckBatch(slugs, state) {
  const neverChecked = [];
  const staleUnindexed = [];
  for (const slug of slugs) {
    const url = `/jobs/${slug}/`;
    const entry = state[url];
    if (!entry || typeof entry.indexed !== 'boolean') {
      neverChecked.push(url);
    } else if (entry.indexed === false) {
      staleUnindexed.push([url, entry.lastChecked || '']);
    }
    // indexed === true -> never re-checked, intentionally excluded
  }
  staleUnindexed.sort((a, b) => (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0)); // oldest-checked first

  const neverBudget = Math.min(neverChecked.length, Math.round(MAX_CHECKS_PER_RUN * NEVER_CHECKED_SHARE));
  const remaining = MAX_CHECKS_PER_RUN - neverBudget;
  const staleBudget = Math.min(staleUnindexed.length, remaining);
  // if never-checked pool is smaller than its share, spend the leftover on stale re-checks too
  const extraForStale = Math.min(staleUnindexed.length - staleBudget, MAX_CHECKS_PER_RUN - neverBudget - staleBudget);

  return [
    ...neverChecked.slice(0, neverBudget),
    ...staleUnindexed.slice(0, staleBudget + Math.max(0, extraForStale)).map(x => x[0]),
  ];
}

async function main() {
  const RAW = process.env.GOOGLE_INDEXING_SA_JSON || '';
  if (!RAW.trim()) {
    console.log('ℹ️  GOOGLE_INDEXING_SA_JSON not set — skipping GSC index-status check '
      + '(build_unindexed_feed.py\'s age-heuristic fallback keeps the homepage feed working).');
    return;
  }
  let SA;
  try { SA = JSON.parse(RAW); } catch (e) { console.error('❌ bad JSON in GOOGLE_INDEXING_SA_JSON secret'); process.exit(1); }
  const clientEmail = SA.client_email || '';
  const privateKey = String(SA.private_key || '').replace(/\\n/g, '\n');

  const token = await getAccessToken(clientEmail, privateKey);
  if (!token) process.exit(1);

  const slugs = readJobSlugs();
  console.log(`📚 Master URL pool: ${slugs.length} job pages on disk.`);
  const state = loadState();
  const batch = buildCheckBatch(slugs, state);
  console.log(`🔎 Checking ${batch.length} URLs this run (budget ${MAX_CHECKS_PER_RUN}/day).`);

  let checked = 0, indexed = 0, unindexed = 0, errors = 0, quotaStopped = false;
  for (const urlPath of batch) {
    const res = await inspect(token, SITE + urlPath);
    if (res.status === 429 || /RESOURCE_EXHAUSTED|quota/i.test(res.body)) {
      console.log(`⛔ Quota exhausted after ${checked} checks — stopping early, will resume next run.`);
      quotaStopped = true;
      break;
    }
    if (res.status !== 200) {
      errors++;
    } else {
      try {
        const r = JSON.parse(res.body)?.inspectionResult?.indexStatusResult || {};
        const isIndexed = r.verdict === 'PASS';
        state[urlPath] = { indexed: isIndexed, verdict: r.verdict || null, lastChecked: new Date().toISOString() };
        isIndexed ? indexed++ : unindexed++;
      } catch (e) {
        errors++;
      }
    }
    checked++;
    if (checked % 100 === 0) console.log(`  ...${checked}/${batch.length} checked`);
    await new Promise(r => setTimeout(r, REQUEST_DELAY_MS));
  }

  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify(state));
  console.log(
    `✅ Done: ${checked} checked (${indexed} indexed, ${unindexed} not indexed, ${errors} errors)` +
    (quotaStopped ? ', stopped early on quota' : '') +
    `. State now covers ${Object.keys(state).length} URLs total.`
  );
}

main();
