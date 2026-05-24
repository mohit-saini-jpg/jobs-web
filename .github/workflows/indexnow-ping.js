/**
 * indexnow-ping.js
 * ================
 * Naye job URLs ko Google aur Bing ko IndexNow se instantly notify karta hai.
 * Sitemap ping bhi karta hai.
 * Run: node .github/workflows/indexnow-ping.js
 */

'use strict';

const https = require('https');
const fs    = require('fs');
const path  = require('path');

const SITE    = 'https://www.topsarkarijobs.com';
const KEY     = 'topsarkarijobs-indexnow-key-2026';   // IndexNow key
const KEY_LOC = `${SITE}/${KEY}.txt`;
const ROOT    = path.join(__dirname, '..', '..');
const IDX     = path.join(ROOT, 'jobs-index.json');
const TODAY   = new Date().toISOString().split('T')[0];

function post(hostname, pathname, body) {
  return new Promise((resolve) => {
    const data = JSON.stringify(body);
    const opts = {
      hostname, path: pathname, method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
    };
    const req = https.request(opts, (res) => {
      console.log(`  ${hostname}: HTTP ${res.statusCode}`);
      resolve(res.statusCode);
    });
    req.on('error', (e) => { console.log(`  ${hostname}: Error — ${e.message}`); resolve(0); });
    req.setTimeout(10000, () => { req.destroy(); resolve(0); });
    req.write(data); req.end();
  });
}

function ping(url) {
  return new Promise((resolve) => {
    const req = https.get(url, (res) => {
      console.log(`  Ping ${url.slice(0,60)}: HTTP ${res.statusCode}`);
      resolve(res.statusCode);
    });
    req.on('error', (e) => { console.log(`  Ping error: ${e.message}`); resolve(0); });
    req.setTimeout(10000, () => { req.destroy(); resolve(0); });
  });
}

async function main() {
  if (!fs.existsSync(IDX)) {
    console.log('⚠️  jobs-index.json not found — skipping IndexNow');
    return;
  }

  const index = JSON.parse(fs.readFileSync(IDX, 'utf8'));
  const allSlugs = Object.keys(index).filter(s => s && !s.endsWith('-latest-notifications'));

  // Only ping URLs that have TODAY as last_date (newly added/updated jobs)
  // OR all URLs if running for the first time / manual run
  let newSlugs = allSlugs.filter(slug => {
    const info = index[slug];
    const lastmod = info.last_date || '';
    // Include if last_date is today or no date (new job)
    return !lastmod || lastmod === TODAY;
  });

  // If no new jobs today, just ping sitemap (don't spam IndexNow with all URLs)
  if (newSlugs.length === 0) {
    console.log('ℹ️  No new jobs today — pinging sitemap only');
    await ping(`https://www.google.com/ping?sitemap=${encodeURIComponent(SITE + '/sitemap-index.xml')}`);
    await ping(`https://www.bing.com/ping?sitemap=${encodeURIComponent(SITE + '/sitemap-index.xml')}`);
    return;
  }

  // IndexNow supports max 10,000 URLs per request
  const MAX_URLS = 500;
  const urlsToSend = newSlugs.slice(0, MAX_URLS).map(slug => `${SITE}/jobs/${slug}/`);

  console.log(`📡 Sending ${urlsToSend.length} new URLs to IndexNow...`);

  const body = {
    host: 'www.topsarkarijobs.com',
    key: KEY,
    keyLocation: KEY_LOC,
    urlList: urlsToSend
  };

  // Ping IndexNow API (works for Google, Bing, Yandex simultaneously)
  await post('api.indexnow.org', '/indexnow', body);

  // Also ping Google & Bing sitemaps
  console.log('\n🔔 Pinging sitemaps...');
  await ping(`https://www.google.com/ping?sitemap=${encodeURIComponent(SITE + '/sitemap-index.xml')}`);
  await ping(`https://www.bing.com/ping?sitemap=${encodeURIComponent(SITE + '/sitemap-index.xml')}`);

  console.log(`\n✅ IndexNow ping complete — ${urlsToSend.length} URLs sent`);
}

main().catch(e => console.error('IndexNow error:', e.message));
