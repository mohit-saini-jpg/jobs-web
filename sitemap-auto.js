/**
 * ══════════════════════════════════════════════════════════════════════
 *  TOP SARKARI JOBS — sitemap-auto.js v5.0
 *  Auto Sitemap Generator  (Node.js / GitHub Actions)
 *
 *  Reads data-jobs-index.json → generates sitemap-jobs.xml
 *  Includes ONLY /data/jobs/{slug}/ — NO category/state/education pages
 *
 *  Run: node sitemap-auto.js
 * ══════════════════════════════════════════════════════════════════════
 */
'use strict';

const fs   = require('fs');
const path = require('path');

const BASE_URL    = 'https://www.topsarkarijobs.com';
const INDEX_FILE  = 'data-jobs-index.json';
const SITEMAP_OUT = 'sitemap-jobs.xml';
const TODAY       = new Date().toISOString().split('T')[0];

function generateSitemap() {
  if (!fs.existsSync(INDEX_FILE)) {
    console.error(`ERROR: ${INDEX_FILE} not found. Run generate_jobs.py first.`);
    process.exit(1);
  }

  const raw   = fs.readFileSync(INDEX_FILE, 'utf-8');
  const index = JSON.parse(raw);
  const slugs = Object.keys(index);

  console.log(`Generating sitemap for ${slugs.length} job pages…`);

  const lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
    '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
  ];

  for (const slug of slugs) {
    const meta    = index[slug];
    const lastmod = meta.lastDate || meta.postDate || TODAY;
    const pri     = (meta.cat === 'Latest_Notifications' || meta.cat === 'Railway_Jobs') ? '0.9' : '0.8';

    lines.push(`  <url>
    <loc>${BASE_URL}/data/jobs/${slug}/</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>${pri}</priority>
  </url>`);
  }

  lines.push('</urlset>');
  fs.writeFileSync(SITEMAP_OUT, lines.join('\n'), 'utf-8');
  console.log(`✅ ${SITEMAP_OUT}: ${slugs.length} URLs written`);
}

generateSitemap();
