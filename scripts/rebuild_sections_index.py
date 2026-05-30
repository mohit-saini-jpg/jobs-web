#!/usr/bin/env python3
"""
Rebuild sections-index.json from master_clean_jobs.json
Maps all categories that JOBS_CAT_META in script.js expects
"""
import json, re, os
from pathlib import Path

os.chdir(Path(__file__).parent.parent)

with open('data/master_clean_jobs.json', encoding='utf-8') as f:
    jobs = json.load(f)

print(f'Loaded {len(jobs)} jobs')

def parse_date_for_sort(d):
    if not d: return '0000-00-00'
    d = str(d).strip()
    m = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})', d)
    if m: return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', d)
    if m: return d[:10]
    return '0000-00-00'

# Build per-category buckets
sections = {}
for job in jobs:
    cat = job.get('category', '').strip()
    if not cat: continue
    slug = job.get('slug', '').strip()
    name = job.get('title', '').strip()
    if not slug or not name: continue
    
    item = {
        'slug': slug,
        'name': name,
        'date': job.get('last_date', ''),
        'org':  job.get('organization', ''),
        'vac':  job.get('total_vacancies', ''),
    }
    sections.setdefault(cat, []).append((parse_date_for_sort(job.get('last_date','')), item))

# Sort each category descending by date
result = {}
for cat, items in sections.items():
    items.sort(key=lambda x: x[0], reverse=True)
    result[cat] = [x[1] for x in items]

# Save compact JSON
with open('sections-index.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

total = sum(len(v) for v in result.values())
print(f'Written sections-index.json: {len(result)} categories, {total} total items')
for cat in sorted(result.keys()):
    print(f'  {cat}: {len(result[cat])}')
