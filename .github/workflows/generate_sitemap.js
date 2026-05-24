/**
 * generate_sitemap.js
 * ===================
 * jobs-index.json padh ke sitemap-jobs.xml banata hai.
 * Saare 4 JSON sources ke slugs include hote hain.
 * Run: node .github/workflows/generate_sitemap.js
 */

'use strict';
const fs   = require('fs');
const path = require('path');

const SITE    = 'https://www.topsarkarijobs.com';
const TODAY   = new Date().toISOString().split('T')[0];
const ROOT    = path.join(__dirname, '..', '..');
const IDX     = path.join(ROOT, 'jobs-index.json');
const OUT     = path.join(ROOT, 'sitemap-jobs.xml');
const IDX_OUT = path.join(ROOT, 'sitemap-index.xml');
const MAIN_SM = path.join(ROOT, 'sitemap.xml');
const SEC_SM  = path.join(ROOT, 'sitemap-sections.xml');

// ── Read jobs-index.json ──
if (!fs.existsSync(IDX)) {
  console.error('❌ jobs-index.json not found');
  process.exit(1);
}

const index = JSON.parse(fs.readFileSync(IDX, 'utf8'));
const slugs = Object.keys(index);
console.log(`📦 Total slugs in index: ${slugs.length}`);

// ── Build URL entries ──
const urlEntries = slugs
  .filter(slug => slug && !slug.endsWith('-latest-notifications'))
  .map(slug => {
    const info = index[slug];
    // Use last_date as lastmod if it's a valid ISO date, else use TODAY
    let lastmod = TODAY;
    if (info.last_date && /^\d{4}-\d{2}-\d{2}$/.test(info.last_date)) {
      lastmod = info.last_date;
    }
    return `  <url>
    <loc>${SITE}/jobs/${slug}/</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>`;
  })
  .join('\n');

// ── Write sitemap-jobs.xml ──
const xml = `<?xml version="1.0" encoding="UTF-8"?>
<!-- sitemap-jobs.xml — auto-generated ${TODAY} — ${slugs.length} job pages -->
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urlEntries}
</urlset>`;

fs.writeFileSync(OUT, xml, 'utf8');
console.log(`✅ sitemap-jobs.xml written: ${slugs.length} URLs`);

// ── Update lastmod in sitemap-index.xml ──
if (fs.existsSync(IDX_OUT)) {
  let content = fs.readFileSync(IDX_OUT, 'utf8');
  content = content.replace(/(<lastmod>)\d{4}-\d{2}-\d{2}(<\/lastmod>)/g, `$1${TODAY}$2`);
  fs.writeFileSync(IDX_OUT, content, 'utf8');
  console.log('✅ sitemap-index.xml lastmod updated');
}

// ── Update lastmod in sitemap.xml ──
if (fs.existsSync(MAIN_SM)) {
  let content = fs.readFileSync(MAIN_SM, 'utf8');
  content = content.replace(/(<lastmod>)\d{4}-\d{2}-\d{2}(<\/lastmod>)/g, `$1${TODAY}$2`);
  fs.writeFileSync(MAIN_SM, content, 'utf8');
  console.log('✅ sitemap.xml lastmod updated');
}

// ── Update lastmod in sitemap-sections.xml ──
if (fs.existsSync(SEC_SM)) {
  let content = fs.readFileSync(SEC_SM, 'utf8');
  content = content.replace(/(<lastmod>)\d{4}-\d{2}-\d{2}(<\/lastmod>)/g, `$1${TODAY}$2`);
  fs.writeFileSync(SEC_SM, content, 'utf8');
  console.log('✅ sitemap-sections.xml lastmod updated');
}

console.log(`\n✅ All sitemaps updated for ${TODAY}`);
