#!/usr/bin/env python3
"""Generate sitemaps from actual built pages"""
import glob, os
from datetime import date

TODAY = date.today().isoformat()
BASE = 'https://www.topsarkarijobs.com'

def mkmap(patterns, out_file, priority='0.8'):
    paths = []
    for pattern in (patterns if isinstance(patterns, list) else [patterns]):
        paths.extend(glob.glob(pattern))
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for path in sorted(set(paths))[:49999]:
        url = path.replace('./', '').replace('/index.html', '/')
        if not url.startswith('/'): url = '/' + url
        xml += f'  <url><loc>{BASE}{url}</loc><lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq><priority>{priority}</priority></url>\n'
    xml += '</urlset>'
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(xml)
    return len(paths)

n1 = mkmap('./jobs/*/index.html', 'sitemap-jobs.xml', '0.8')
n2 = mkmap('./state/*/*/index.html', 'sitemap-states.xml', '0.7')
n3 = mkmap('./education/*/*/index.html', 'sitemap-education.xml', '0.7')
n4 = mkmap('./category/study/*/*/index.html', 'sitemap-categories.xml', '0.7')
n5 = mkmap(['./section/*/index.html', './qualification/*/index.html'], 'sitemap-sections.xml', '0.6')

# Sitemap index
index = f'''<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>{BASE}/sitemap-jobs.xml</loc><lastmod>{TODAY}</lastmod></sitemap>
  <sitemap><loc>{BASE}/sitemap-states.xml</loc><lastmod>{TODAY}</lastmod></sitemap>
  <sitemap><loc>{BASE}/sitemap-education.xml</loc><lastmod>{TODAY}</lastmod></sitemap>
  <sitemap><loc>{BASE}/sitemap-categories.xml</loc><lastmod>{TODAY}</lastmod></sitemap>
  <sitemap><loc>{BASE}/sitemap-sections.xml</loc><lastmod>{TODAY}</lastmod></sitemap>
  <sitemap><loc>{BASE}/sitemap-pages.xml</loc><lastmod>{TODAY}</lastmod></sitemap>
</sitemapindex>'''
with open('sitemap.xml', 'w') as f: f.write(index)

total = n1 + n2 + n3 + n4 + n5
print(f'Sitemaps built: jobs={n1} state={n2} edu={n3} cat={n4} sections={n5} TOTAL={total}')
