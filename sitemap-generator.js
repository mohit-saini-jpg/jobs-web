/**
 * Auto Sitemap Generator — Top Sarkari Jobs
 * Run: node sitemap-generator.js
 * Generates sitemap-jobs.xml from dynamic-sections.json
 * 
 * Add to cron/deploy: node sitemap-generator.js
 */

const fs = require('fs');
const path = require('path');

const SITE = 'https://www.topsarkarijobs.com';
const TODAY = new Date().toISOString().split('T')[0];

function slugify(text) {
  return String(text)
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\w\s-]/g, ' ')
    .trim()
    .toLowerCase()
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

function main() {
  const dataPath = path.join(__dirname, 'dynamic-sections.json');
  if (!fs.existsSync(dataPath)) {
    console.error('dynamic-sections.json not found');
    process.exit(1);
  }

  const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
  const sections = data.sections || [];

  const jobUrls = [];
  const seenSlugs = new Set();

  for (const section of sections) {
    const items = section.items || [];
    for (const item of items) {
      const name = item.name || '';
      if (!name || name.length < 5) continue;
      const slug = slugify(name);
      if (!slug || slug === 'official-link' || seenSlugs.has(slug)) continue;
      seenSlugs.add(slug);

      jobUrls.push({
        loc: `${SITE}/jobs/${slug}/`,
        lastmod: TODAY,
        changefreq: 'daily',
        priority: '0.8'
      });
    }
  }

  console.log(`Generated ${jobUrls.length} job URLs`);

  // Write jobs sitemap
  const jobsSitemapPath = path.join(__dirname, 'sitemap-jobs.xml');
  fs.writeFileSync(jobsSitemapPath, generateSitemap(jobUrls), 'utf8');
  console.log(`Written: sitemap-jobs.xml`);

  // Update sitemap-index.xml with current date
  const indexPath = path.join(__dirname, 'sitemap-index.xml');
  if (fs.existsSync(indexPath)) {
    let indexContent = fs.readFileSync(indexPath, 'utf8');
    // Update lastmod dates
    indexContent = indexContent.replace(
      /(<lastmod>)\d{4}-\d{2}-\d{2}(<\/lastmod>)/g,
      `$1${TODAY}$2`
    );
    fs.writeFileSync(indexPath, indexContent, 'utf8');
    console.log(`Updated: sitemap-index.xml dates to ${TODAY}`);
  }

  // Also update sitemap.xml date
  const mainSitemapPath = path.join(__dirname, 'sitemap.xml');
  if (fs.existsSync(mainSitemapPath)) {
    let mainContent = fs.readFileSync(mainSitemapPath, 'utf8');
    mainContent = mainContent.replace(
      /(<lastmod>)\d{4}-\d{2}-\d{2}(<\/lastmod>)/g,
      `$1${TODAY}$2`
    );
    fs.writeFileSync(mainSitemapPath, mainContent, 'utf8');
    console.log(`Updated: sitemap.xml dates to ${TODAY}`);
  }

  console.log('\n✅ Sitemap generation complete!');
  console.log(`📋 Job URLs: ${jobUrls.length}`);
  console.log(`📅 Date: ${TODAY}`);
}

main();
