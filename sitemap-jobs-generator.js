/**
 * sitemap-jobs-generator.js
 * =========================
 * Run this script locally (Node.js) to regenerate sitemap-jobs.xml
 * from your dynamic-sections.json file.
 *
 * Usage:
 *   node sitemap-jobs-generator.js
 *
 * Output:
 *   sitemap-jobs.xml  — include this in your main sitemap index
 *
 * Requirements:
 *   - dynamic-sections.json must be in the same directory (or adjust path below)
 *   - Node.js 14+
 */

'use strict';

const fs   = require('fs');
const path = require('path');

/* ── Config ── */
const BASE_URL       = 'https://www.topsarkarijobs.com';
const DATA_FILE      = path.join(__dirname, 'dynamic-sections.json');
const OUTPUT_FILE    = path.join(__dirname, 'sitemap-jobs.xml');
const CHANGEFREQ     = 'weekly';
const PRIORITY       = '0.8';
const TODAY          = new Date().toISOString().split('T')[0];

/* ── Slug generator (mirrors script.js slugifyTitle) ── */
function slugifyTitle(raw) {
  const text = (raw ?? '').toString().trim()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/&/g, ' and ')
    .replace(/['']/g, '')
    .toLowerCase();

  const slug = text
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-')
    .slice(0, 120);

  return slug || 'official-link';
}

/* ── Read data ── */
const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
const seen = new Set();
const urls = [];

for (const section of (data.sections || [])) {
  for (const item of (section.items || [])) {
    const name = (item.name || item.title || '').trim();
    if (!name) continue;

    const slug = slugifyTitle(name);
    if (!slug || slug === 'official-link') continue;
    if (seen.has(slug)) continue;
    seen.add(slug);

    urls.push(`  <url>
    <loc>${BASE_URL}/jobs/${slug}/</loc>
    <lastmod>${TODAY}</lastmod>
    <changefreq>${CHANGEFREQ}</changefreq>
    <priority>${PRIORITY}</priority>
  </url>`);
  }
}

/* ── Write XML ── */
const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join('\n')}
</urlset>
`;

fs.writeFileSync(OUTPUT_FILE, xml, 'utf8');
console.log(`✅ Generated ${urls.length} job URLs → ${OUTPUT_FILE}`);
