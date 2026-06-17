#!/usr/bin/env node
/**
 * sitemap-auto.js — Top Sarkari Jobs
 * Auto-generates all sitemaps from job data
 * Run: node sitemap-auto.js
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * ✅ sitemap-index.xml (master index)
 * ✅ sitemap-jobs.xml (all job pages with clean URLs)
 * ✅ sitemap-pages.xml (static pages)
 * ✅ sitemap-categories.xml (category pages)
 * ✅ sitemap-states.xml (state job pages)
 * ✅ sitemap-results.xml
 * ✅ sitemap-admitcards.xml
 * ✅ IndexNow ping after generation
 */

const fs = require('fs');
const path = require('path');

const SITE = 'https://www.topsarkarijobs.com';
const TODAY = new Date().toISOString().split('T')[0];
const DATA_FILE = path.join(__dirname, 'Complete_Jobs_Full_Data.json');
const INDEXNOW_KEY = 'topsarkarijobs-indexnow-key-2026';

// ── Slugify (must match frontend logic) ──────────────────────────────────────
function slugify(title) {
  return title
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, ' and ').replace(/['']/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-')
    .slice(0, 120) || 'official-link';
}

// ── XML helpers ───────────────────────────────────────────────────────────────
function xmlEscape(str) {
  return (str || '').toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function urlEntry(loc, opts = {}) {
  const { lastmod = TODAY, changefreq = 'daily', priority = '0.8' } = opts;
  return `  <url>
    <loc>${xmlEscape(loc)}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>${changefreq}</changefreq>
    <priority>${priority}</priority>
  </url>`;
}

function makeSitemap(urls, filename) {
  const content = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
${urls.join('\n')}
</urlset>`;
  fs.writeFileSync(path.join(__dirname, filename), content, 'utf8');
  console.log(`✅ ${filename} → ${urls.length} URLs`);
  return urls.length;
}

// ── Static pages ──────────────────────────────────────────────────────────────
const STATIC_PAGES = [
  { url: '/', priority: '1.0', changefreq: 'hourly' },
  { url: '/jobs/', priority: '0.95', changefreq: 'hourly' },
  { url: '/admit-card/', priority: '0.9', changefreq: 'daily' },
  { url: '/result/', priority: '0.9', changefreq: 'daily' },
  { url: '/latest-jobs/', priority: '0.95', changefreq: 'hourly' },
  { url: '/railway-jobs/', priority: '0.85', changefreq: 'daily' },
  { url: '/bank-jobs/', priority: '0.85', changefreq: 'daily' },
  { url: '/police-jobs/', priority: '0.85', changefreq: 'daily' },
  { url: '/ssc-jobs/', priority: '0.85', changefreq: 'daily' },
  { url: '/upsc-jobs/', priority: '0.85', changefreq: 'daily' },
  { url: '/teaching-jobs/', priority: '0.8', changefreq: 'daily' },
  { url: '/army-jobs/', priority: '0.8', changefreq: 'daily' },
  { url: '/10th-pass-jobs/', priority: '0.8', changefreq: 'daily' },
  { url: '/12th-pass-jobs/', priority: '0.8', changefreq: 'daily' },
  { url: '/about.html', priority: '0.5', changefreq: 'monthly' },
  { url: '/contact.html', priority: '0.5', changefreq: 'monthly' },
  { url: '/privacy.html', priority: '0.3', changefreq: 'yearly' },
  { url: '/terms.html', priority: '0.3', changefreq: 'yearly' },
  { url: '/search.html', priority: '0.6', changefreq: 'weekly' },
];

const CATEGORIES = [
  'Latest Notifications', 'Railway Jobs', 'Police Defence', 'Bank Jobs',
  'Teaching Faculty', 'Medical Hospital', 'SSC Jobs', 'UPSC Jobs',
  '10TH Pass', '12TH Pass', 'ITI', 'Diploma', 'B Tech BE',
  'Any Graduate', 'Any Post Graduate', 'Defence Army',
  'Last Date Reminder', '8TH Pass', 'B Com'
];

const STATES = [
  'uttar-pradesh', 'bihar', 'rajasthan', 'madhya-pradesh', 'maharashtra',
  'haryana', 'punjab', 'gujarat', 'west-bengal', 'tamil-nadu',
  'karnataka', 'andhra-pradesh', 'telangana', 'odisha', 'jharkhand',
  'chhattisgarh', 'uttarakhand', 'himachal-pradesh', 'jammu-kashmir',
  'assam', 'kerala', 'delhi'
];

// ── Main generation ───────────────────────────────────────────────────────────
async function main() {
  console.log('🚀 Generating sitemaps for Top Sarkari Jobs...\n');

  // Load job data
  let jobData = {};
  try {
    const raw = fs.readFileSync(DATA_FILE, 'utf8');
    jobData = JSON.parse(raw);
    console.log(`📦 Loaded job data: ${Object.keys(jobData).length} categories`);
  } catch (e) {
    console.error('❌ Could not load Complete_Jobs_Full_Data.json:', e.message);
    process.exit(1);
  }

  const newUrls = [];

  // ── 1. Static pages sitemap ────────────────────────────────────────────────
  const pageUrls = STATIC_PAGES.map(p =>
    urlEntry(SITE + p.url, { priority: p.priority, changefreq: p.changefreq })
  );
  makeSitemap(pageUrls, 'sitemap-pages.xml');

  // ── 2. Job pages sitemap ───────────────────────────────────────────────────
  const jobUrls = [];
  const seen = new Set();

  Object.values(jobData).forEach(catJobs => {
    if (!Array.isArray(catJobs)) return;
    catJobs.forEach(job => {
      const bd = job.basic_details || {};
      const title = (bd.job_title || '').trim();
      if (!title) return;

      const slug = slugify(title);
      if (seen.has(slug)) return;
      seen.add(slug);

      const url = `${SITE}/jobs/${slug}/`;
      const lastmod = bd.last_updated
        ? parseDate(bd.last_updated)
        : TODAY;

      // Higher priority for jobs with upcoming last dates
      const dates = job.important_dates || {};
      const lastDate = dates.last_date_to_apply || dates.last_date || '';
      const isUpcoming = lastDate && isDateUpcoming(lastDate);
      const priority = isUpcoming ? '0.9' : '0.7';

      jobUrls.push(urlEntry(url, { lastmod, priority, changefreq: 'daily' }));
      if (isUpcoming) newUrls.push(url);
    });
  });

  makeSitemap(jobUrls, 'sitemap-jobs.xml');

  // ── 3. Categories sitemap ──────────────────────────────────────────────────
  const catUrls = CATEGORIES.map(cat => {
    const catSlug = cat.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    return urlEntry(`${SITE}/category/${catSlug}/`, { priority: '0.85', changefreq: 'daily' });
  });
  makeSitemap(catUrls, 'sitemap-categories.xml');

  // ── 4. States sitemap ──────────────────────────────────────────────────────
  const stateUrls = STATES.map(state =>
    urlEntry(`${SITE}/state-jobs/${state}/`, { priority: '0.8', changefreq: 'daily' })
  );
  makeSitemap(stateUrls, 'sitemap-states.xml');

  // ── 5. Results sitemap ─────────────────────────────────────────────────────
  const resultUrls = [
    urlEntry(`${SITE}/result/`, { priority: '0.9', changefreq: 'hourly' }),
    urlEntry(`${SITE}/result.html`, { priority: '0.85', changefreq: 'hourly' }),
  ];
  makeSitemap(resultUrls, 'sitemap-results.xml');

  // ── 6. Admit cards sitemap ─────────────────────────────────────────────────
  const admitUrls = [
    urlEntry(`${SITE}/admit-card/`, { priority: '0.9', changefreq: 'hourly' }),
    urlEntry(`${SITE}/admit-card.html`, { priority: '0.85', changefreq: 'hourly' }),
  ];
  makeSitemap(admitUrls, 'sitemap-admitcards.xml');

  // ── 7. Sitemap index ───────────────────────────────────────────────────────
  const sitemapFiles = [
    'sitemap-pages.xml',
    'sitemap-jobs.xml',
    'sitemap-categories.xml',
    'sitemap-states.xml',
    'sitemap-results.xml',
    'sitemap-admitcards.xml',
  ];

  const indexContent = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${sitemapFiles.map(f => `  <sitemap>
    <loc>${SITE}/${f}</loc>
    <lastmod>${TODAY}</lastmod>
  </sitemap>`).join('\n')}
</sitemapindex>`;

  fs.writeFileSync(path.join(__dirname, 'sitemap-index.xml'), indexContent, 'utf8');
  console.log(`✅ sitemap-index.xml → ${sitemapFiles.length} sitemaps`);

  // Update sitemap.xml (main entry point for Google)
  fs.writeFileSync(path.join(__dirname, 'sitemap.xml'), indexContent, 'utf8');
  console.log(`✅ sitemap.xml (copy of index)`);

  // ── 8. IndexNow ping ──────────────────────────────────────────────────────
  if (newUrls.length > 0) {
    console.log(`\n🔔 Pinging IndexNow for ${newUrls.length} new/updated URLs...`);
    await pingIndexNow(newUrls.slice(0, 100));
  }

  // ── 9. HTML Sitemap ───────────────────────────────────────────────────────
  generateHTMLSitemap(jobData, seen);

  console.log(`\n✅ All sitemaps generated — ${TODAY}`);
  console.log(`📊 Total job URLs: ${jobUrls.length}`);
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function parseDate(str) {
  if (!str) return TODAY;
  const m = str.match(/(\d{1,2})[\s\-\/]([A-Za-z]+|\d{1,2})[\s\-\/](\d{2,4})/);
  if (!m) return TODAY;
  try {
    const d = new Date(str);
    if (!isNaN(d)) return d.toISOString().split('T')[0];
  } catch (e) {}
  return TODAY;
}

function isDateUpcoming(str) {
  try {
    const d = new Date(str);
    if (isNaN(d)) return false;
    return d > new Date();
  } catch (e) { return false; }
}

async function pingIndexNow(urls) {
  const https = require('https');
  const payload = JSON.stringify({
    host: 'www.topsarkarijobs.com',
    key: INDEXNOW_KEY,
    keyLocation: `${SITE}/${INDEXNOW_KEY}.txt`,
    urlList: urls
  });

  const options = {
    hostname: 'api.indexnow.org',
    path: '/indexnow',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Content-Length': Buffer.byteLength(payload)
    }
  };

  return new Promise((resolve) => {
    const req = https.request(options, (res) => {
      console.log(`IndexNow response: ${res.statusCode}`);
      resolve();
    });
    req.on('error', (e) => { console.warn('IndexNow error:', e.message); resolve(); });
    req.write(payload);
    req.end();
  });
}

function generateHTMLSitemap(jobData, seen) {
  const categories = {};
  Object.entries(jobData).forEach(([cat, jobs]) => {
    if (!Array.isArray(jobs)) return;
    categories[cat] = jobs
      .filter(j => (j.basic_details || {}).job_title)
      .slice(0, 50)
      .map(j => {
        const title = j.basic_details.job_title;
        return { title, slug: slugify(title) };
      });
  });

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HTML Sitemap | Top Sarkari Jobs 2026</title>
  <meta name="description" content="Complete HTML sitemap for Top Sarkari Jobs. Browse all government job categories, state jobs, results, and admit cards.">
  <link rel="canonical" href="https://www.topsarkarijobs.com/sitemap.html">
  <link rel="stylesheet" href="/styles.css">
  <style>
    .sitemap-wrap { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .sitemap-section { margin-bottom: 30px; background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .sitemap-section h2 { color: #1d4ed8; font-size: 1.1rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 12px; }
    .sitemap-links { columns: 3; column-gap: 20px; }
    @media(max-width: 768px) { .sitemap-links { columns: 1; } }
    .sitemap-links a { display: block; padding: 4px 0; font-size: .85rem; color: #1d6dbc; text-decoration: none; border-bottom: 1px solid #f1f5f9; line-height: 1.4; }
    .sitemap-links a:hover { color: #1d4ed8; text-decoration: underline; }
    .sitemap-quick { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
    .sitemap-quick a { background: #dbeafe; color: #1e40af; padding: 5px 12px; border-radius: 20px; font-size: .82rem; text-decoration: none; font-weight: 600; }
    .sitemap-quick a:hover { background: #1d4ed8; color: #fff; }
  </style>
</head>
<body>
  <div class="sitemap-wrap">
    <h1 style="color:#0f172a;font-size:1.4rem;margin-bottom:20px;">📋 Complete Sitemap — Top Sarkari Jobs</h1>

    <div class="sitemap-section">
      <h2>🔗 Quick Navigation</h2>
      <div class="sitemap-quick">
        <a href="/">Home</a>
        <a href="/jobs/">All Jobs</a>
        <a href="/admit-card/">Admit Cards</a>
        <a href="/result/">Results</a>
        <a href="/railway-jobs/">Railway Jobs</a>
        <a href="/bank-jobs/">Bank Jobs</a>
        <a href="/police-jobs/">Police Jobs</a>
        <a href="/ssc-jobs/">SSC Jobs</a>
        <a href="/upsc-jobs/">UPSC Jobs</a>
        <a href="/10th-pass-jobs/">10th Pass Jobs</a>
        <a href="/12th-pass-jobs/">12th Pass Jobs</a>
        <a href="/teaching-jobs/">Teaching Jobs</a>
        <a href="/search/">Search</a>
      </div>
    </div>

    <div class="sitemap-section">
      <h2>🗺️ State Government Jobs</h2>
      <div class="sitemap-links">
        ${STATES.map(s => `<a href="/state-jobs/${s}/">${s.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} Jobs</a>`).join('\n        ')}
      </div>
    </div>

    ${Object.entries(categories).slice(0, 10).map(([cat, jobs]) => `
    <div class="sitemap-section">
      <h2>📌 ${cat.replace(/_/g, ' ')}</h2>
      <div class="sitemap-links">
        ${jobs.map(j => `<a href="/jobs/${j.slug}/">${j.title}</a>`).join('\n        ')}
      </div>
    </div>`).join('\n')}

    <div class="sitemap-section">
      <h2>📄 Pages</h2>
      <div class="sitemap-links">
        <a href="/about/">About Us</a>
        <a href="/contact/">Contact</a>
        <a href="/privacy/">Privacy Policy</a>
        <a href="/terms/">Terms of Use</a>
        <a href="/sitemap.html">HTML Sitemap</a>
      </div>
    </div>
  </div>
</body>
</html>`;

  fs.writeFileSync(path.join(__dirname, 'sitemap.html'), html, 'utf8');
  console.log('✅ sitemap.html generated');
}

const STATES = [
  'uttar-pradesh', 'bihar', 'rajasthan', 'madhya-pradesh', 'maharashtra',
  'haryana', 'punjab', 'gujarat', 'west-bengal', 'tamil-nadu',
  'karnataka', 'andhra-pradesh', 'telangana', 'odisha', 'jharkhand',
  'chhattisgarh', 'uttarakhand', 'himachal-pradesh', 'jammu-kashmir',
  'assam', 'kerala', 'delhi'
];

main().catch(console.error);
