/**
 * Sitemap Generator — Top Sarkari Jobs
 * Works in: Local, GitHub Actions, cPanel
 * Run: node sitemap-generator.js
 */

const fs = require('fs');
const path = require('path');

const SITE = 'https://www.topsarkarijobs.com';
const TODAY = new Date().toISOString().split('T')[0];

console.log('🗺️  Sitemap Generator Started...');
console.log('📅 Date:', TODAY);

function slugify(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, ' ')
    .trim()
    .replace(/[\s_]+/g, '-')
    .replace(/-{2,}/g, '-')
    .slice(0, 100);
}

function generateSitemap(urls) {
  const urlEntries = urls.map(u => `  <url>
    <loc>${u.loc}</loc>
    <lastmod>${u.lastmod || TODAY}</lastmod>
    <changefreq>${u.changefreq || 'daily'}</changefreq>
    <priority>${u.priority || '0.8'}</priority>
  </url>`).join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urlEntries}
</urlset>`;
}

// ── Read Complete_Jobs_Full_Data.json ───────────────────
const dataPath = path.join(__dirname, 'Complete_Jobs_Full_Data.json');

if (!fs.existsSync(dataPath)) {
  console.error('❌ Complete_Jobs_Full_Data.json not found at:', dataPath);
  console.log('📁 Files in directory:', fs.readdirSync(__dirname).join(', '));
  process.exit(1);
}

let rawData;
try {
  rawData = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
  console.log('✅ Complete_Jobs_Full_Data.json loaded');
} catch (e) {
  console.error('❌ JSON parse error:', e.message);
  process.exit(1);
}

// Convert Complete_Jobs_Full_Data format → sections format
// Structure: { "CATEGORY_KEY": [ { basic_details: { job_title, ... }, ... } ] }
const sections = Object.entries(rawData).map(([categoryKey, jobs]) => ({
  id: categoryKey,
  title: categoryKey.replace(/_/g, ' '),
  items: (Array.isArray(jobs) ? jobs : []).map(job => ({
    name: (job.basic_details && (job.basic_details.job_title || job.basic_details.post_name)) || ''
  })).filter(item => item.name.length >= 3)
})).filter(section => section.items.length > 0);

console.log('📦 Total sections:', sections.length);
console.log('NEW JSON FILE NAME -Complete_Jobs_Full_Data.json');

// ── Generate Job URLs ───────────────────────────────────
const jobUrls = [];
const seenSlugs = new Set();

for (const section of sections) {
  const items = section.items || [];
  for (const item of items) {
    const name = item.name || item.title || '';
    if (!name || name.length < 3) continue;
    const slug = slugify(name);
    if (!slug || slug.length < 3 || seenSlugs.has(slug)) continue;
    seenSlugs.add(slug);
    jobUrls.push({
      loc: `${SITE}/view.html?section=${encodeURIComponent(section.id || section.title || '')}&name=${encodeURIComponent(name)}`,
      lastmod: TODAY,
      changefreq: 'daily',
      priority: '0.8'
    });
  }
}

console.log('🔗 Job URLs generated:', jobUrls.length);

// ── Write sitemap-jobs.xml ──────────────────────────────
try {
  fs.writeFileSync(
    path.join(__dirname, 'sitemap-jobs.xml'),
    generateSitemap(jobUrls),
    'utf8'
  );
  console.log('✅ sitemap-jobs.xml written');
} catch (e) {
  console.error('❌ Error writing sitemap-jobs.xml:', e.message);
  process.exit(1);
}

// ── Update sitemap-index.xml dates ─────────────────────
const indexPath = path.join(__dirname, 'sitemap-index.xml');
if (fs.existsSync(indexPath)) {
  try {
    let content = fs.readFileSync(indexPath, 'utf8');
    content = content.replace(/(<lastmod>)\d{4}-\d{2}-\d{2}(<\/lastmod>)/g, `$1${TODAY}$2`);
    fs.writeFileSync(indexPath, content, 'utf8');
    console.log('✅ sitemap-index.xml updated');
  } catch (e) {
    console.error('⚠️  Could not update sitemap-index.xml:', e.message);
  }
}

// ── Update sitemap.xml dates ────────────────────────────
const mainPath = path.join(__dirname, 'sitemap.xml');
if (fs.existsSync(mainPath)) {
  try {
    let content = fs.readFileSync(mainPath, 'utf8');
    content = content.replace(/(<lastmod>)\d{4}-\d{2}-\d{2}(<\/lastmod>)/g, `$1${TODAY}$2`);
    fs.writeFileSync(mainPath, content, 'utf8');
    console.log('✅ sitemap.xml updated');
  } catch (e) {
    console.error('⚠️  Could not update sitemap.xml:', e.message);
  }
}

console.log('\n✅ Sitemap generation complete!');
console.log(`📋 Total job URLs: ${jobUrls.length}`);
console.log(`📅 Date: ${TODAY}`);
