/**
 * indexnow-ping.js — Submit URLs to IndexNow (Bing/Yandex)
 * ==========================================================
 * Called by auto-update-jobs.yml via: node .github/workflows/indexnow-ping.js
 *
 * Required env: INDEXNOW_KEY (from GitHub Secrets)
 * Zero external dependencies — uses only Node.js built-in https module
 * Failures are logged but never throw — continue-on-error behavior baked in
 */

'use strict';

const https = require('https');
const fs    = require('fs');
const path  = require('path');

const KEY   = process.env.INDEXNOW_KEY || '';
const HOST  = 'www.topsarkarijobs.com';
const SITE  = `https://${HOST}`;

if (!KEY) {
  console.warn('⚠️  INDEXNOW_KEY not set — skipping IndexNow ping');
  process.exit(0);
}

// ── Base URLs to always submit ─────────────────────────────────────────
const BASE_URLS = [
  `${SITE}/`,
  `${SITE}/section/latest-jobs/`,
  `${SITE}/section/results/`,
  `${SITE}/section/admit-card/`,
  `${SITE}/section/answer-key/`,
  `${SITE}/section/today-updates/`,
  `${SITE}/section/upcoming-jobs/`,
];

// ── Add top 20 most recent job URLs from jobs-index.json ───────────────
let jobUrls = [];
const indexPaths = ['jobs-index.json', path.join(process.cwd(), 'jobs-index.json')];
for (const p of indexPaths) {
  try {
    if (fs.existsSync(p)) {
      const idx = JSON.parse(fs.readFileSync(p, 'utf8'));
      // jobs-index.json format: { slug: { cat, title, last_date, org } }
      const entries = Object.entries(idx);
      // Sort by last_date descending to get most recent
      entries.sort((a, b) => {
        const da = (a[1].last_date || '').slice(0, 10);
        const db = (b[1].last_date || '').slice(0, 10);
        return db.localeCompare(da);
      });
      jobUrls = entries.slice(0, 20).map(([slug]) => `${SITE}/jobs/${slug}/`);
      console.log(`📋 Loaded ${jobUrls.length} recent job URLs from jobs-index.json`);
      break;
    }
  } catch (e) {
    console.warn('⚠️  Could not load jobs-index.json:', e.message);
  }
}

const ALL_URLS = [...BASE_URLS, ...jobUrls];
console.log(`📡 Submitting ${ALL_URLS.length} URLs to IndexNow...`);

// ── Build IndexNow payload ─────────────────────────────────────────────
const payload = JSON.stringify({
  host:       HOST,
  key:        KEY,
  keyLocation: `${SITE}/${KEY}.txt`,
  urlList:    ALL_URLS,
});

// ── Send to IndexNow API ───────────────────────────────────────────────
function postIndexNow(endpointHost) {
  return new Promise((resolve) => {
    const options = {
      hostname: endpointHost,
      path:     '/indexnow',
      method:   'POST',
      headers:  {
        'Content-Type':   'application/json; charset=utf-8',
        'Content-Length': Buffer.byteLength(payload),
      },
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        if (res.statusCode === 200 || res.statusCode === 202) {
          console.log(`✅ ${endpointHost}: ${res.statusCode} — ${ALL_URLS.length} URLs accepted`);
        } else if (res.statusCode === 422) {
          console.warn(`⚠️  ${endpointHost}: 422 — some URLs may be invalid`);
        } else {
          console.warn(`⚠️  ${endpointHost}: ${res.statusCode} — ${data.slice(0, 100)}`);
        }
        resolve();
      });
    });

    req.on('error', (e) => {
      console.warn(`⚠️  ${endpointHost} request failed:`, e.message);
      resolve(); // never reject — continue-on-error behavior
    });

    req.setTimeout(10000, () => {
      console.warn(`⚠️  ${endpointHost} timeout`);
      req.destroy();
      resolve();
    });

    req.write(payload);
    req.end();
  });
}

// Submit to both IndexNow endpoints
Promise.all([
  postIndexNow('api.indexnow.org'),
  postIndexNow('www.bing.com'),
]).then(() => {
  console.log('✅ IndexNow ping complete');
  process.exit(0);
}).catch(() => {
  process.exit(0); // never fail the workflow
});
