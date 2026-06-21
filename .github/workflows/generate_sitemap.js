/**
 * generate_sitemap.js
 * ===================
 * jobs-index.json padh ke sitemap-jobs.xml banata hai.
 * 
 * PERMANENT FIX: lastmod sirf jab content actually change ho.
 * - sitemap-content-hashes.json mein per-slug hash store hota hai
 * - Agar slug ka hash same hai → purani lastmod rakhi jaati hai
 * - Agar hash change → new lastmod (TODAY) + hash update
 */

'use strict';
const fs   = require('fs');
const path = require('path');
const crypto = require('crypto');

const SITE    = 'https://www.topsarkarijobs.com';
const TODAY   = new Date().toISOString().split('T')[0];
const ROOT    = path.join(__dirname, '..', '..');
const IDX     = path.join(ROOT, 'jobs-index.json');
const OUT     = path.join(ROOT, 'sitemap-jobs.xml');
const IDX_OUT = path.join(ROOT, 'sitemap-index.xml');
const MAIN_SM = path.join(ROOT, 'sitemap.xml');
const SEC_SM  = path.join(ROOT, 'sitemap-sections.xml');
const HASH_F  = path.join(ROOT, '.sitemap-content-hashes.json');

if (!fs.existsSync(IDX)) {
  console.error('❌ jobs-index.json not found');
  process.exit(1);
}

const index = JSON.parse(fs.readFileSync(IDX, 'utf8'));
const slugs = Object.keys(index);
console.log(`📦 Total slugs in index: ${slugs.length}`);

// ── Load previous hashes (per-slug) ──
let prevHashes = {};
if (fs.existsSync(HASH_F)) {
  try { prevHashes = JSON.parse(fs.readFileSync(HASH_F, 'utf8')); } catch (e) {}
}

// ── Build URL entries (lastmod = TODAY only if content changed) ──
const newHashes = {};
let changedCount = 0, sameCount = 0;

const urlEntries = slugs
  .filter(slug => slug && !slug.endsWith('-latest-notifications'))
  .map(slug => {
    const info = index[slug] || {};
    // Hash key fields that signal real content change (NOT timestamps)
    const hashKey = JSON.stringify({
      t: info.title || '',
      ld: info.last_date || '',
      v: info.vacancies || info.total_vacancy || '',
      f: info.fee || '',
      o: info.org || info.organization || '',
      s: info.status || ''
    });
    const hash = crypto.createHash('md5').update(hashKey).digest('hex').slice(0, 12);
    newHashes[slug] = { h: hash, m: prevHashes[slug] && prevHashes[slug].h === hash
                            ? (prevHashes[slug].m || TODAY) : TODAY };
    if (prevHashes[slug] && prevHashes[slug].h === hash) sameCount++;
    else changedCount++;

    let lastmod = newHashes[slug].m;
    // Override with last_date if it's a valid recent ISO date
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

console.log(`📊 lastmod stats: ${changedCount} changed, ${sameCount} unchanged (preserving old lastmod)`);

// Save updated hashes for next run
fs.writeFileSync(HASH_F, JSON.stringify(newHashes), 'utf8');

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<!-- sitemap-jobs.xml — auto-generated ${TODAY} — ${slugs.length} job pages -->
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urlEntries}
</urlset>`;

fs.writeFileSync(OUT, xml, 'utf8');
console.log(`✅ sitemap-jobs.xml written: ${slugs.length} URLs`);

// For sitemap-index.xml, sitemap.xml, sitemap-sections.xml: 
// update lastmod ONLY if jobs sitemap had changes (content actually changed)
if (changedCount > 0) {
  [IDX_OUT, MAIN_SM, SEC_SM].forEach(f => {
    if (fs.existsSync(f)) {
      let c = fs.readFileSync(f, 'utf8');
      c = c.replace(/(<lastmod>)\d{4}-\d{2}-\d{2}(<\/lastmod>)/g, `$1${TODAY}$2`);
      fs.writeFileSync(f, c, 'utf8');
      console.log(`✅ ${path.basename(f)} lastmod updated (real content changed)`);
    }
  });
} else {
  console.log('⏸ No content changes — keeping existing lastmod on index sitemaps');
}

console.log(`\n✅ Sitemap pass complete: ${TODAY}`);
