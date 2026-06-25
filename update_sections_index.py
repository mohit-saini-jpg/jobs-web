#!/usr/bin/env python3
"""
update_sections_index.py
Regenerates sections-index.json from Complete_Jobs_Full_Data.json
preserving JSON order (scraper output order = display order on homepage).

Covers ALL 53+ categories:
  - FJA categories (10TH_Pass, 12TH_Pass, ITI, Diploma, etc.)
  - Sarkari categories (SR_Latest_Jobs, SR_Result, OFFLINE_FORM, etc.)

Run this after the scraper updates Complete_Jobs_Full_Data.json:
    python update_sections_index.py
"""
import json, re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent

def slugify(text):
    """Must match generate_jobs.py slugify exactly — 60-char limit."""
    import re as _re
    text = str(text).lower()
    text = _re.sub(r'[^a-z0-9\s-]', '', text)
    text = _re.sub(r'[\s-]+', '-', text)
    return text[:60].strip('-') or 'job' 

# Load root Complete_Jobs_Full_Data.json (scraper output = source of truth)
cj_path = ROOT / 'Complete_Jobs_Full_Data.json'
if not cj_path.exists():
    cj_path = ROOT / 'data' / 'Complete_Jobs_Full_Data.json'
print(f"Loading: {cj_path}")
with open(cj_path, encoding='utf-8') as f:
    cj = json.load(f)

# Load existing sections-index.json
si_path = ROOT / 'sections-index.json'
with open(si_path, encoding='utf-8') as f:
    si = json.load(f)

fixed = 0

# --- Fix ALL FJA categories from freejobalert_unified.deduped_jobs ---
# Group deduped_jobs by their fja_categories, take top 10 per category
fja_unified_jobs = (cj.get('freejobalert_unified') or {}).get('deduped_jobs', [])
fja_by_cat = {}
for j in fja_unified_jobs:
    bd = (j.get('basic_details') or {})
    title = (bd.get('job_title','') or j.get('title','')).strip()
    if not title: continue
    cats = j.get('fja_categories') or []
    slug = slugify(title)
    imp = (j.get('important_dates') or {})
    ld = (imp.get('last_date_to_apply','') or imp.get('last_date','')).strip()
    org = (bd.get('organization_name','') or '').strip()
    vac = (bd.get('total_vacancies','') or '').strip()
    for cat in cats:
        if cat not in fja_by_cat:
            fja_by_cat[cat] = []
        if len(fja_by_cat[cat]) < 10:
            fja_by_cat[cat].append({'slug': slug, 'name': title, 'date': ld, 'org': org, 'vac': vac})

for cat, items in fja_by_cat.items():
    si[cat] = items
    fixed += 1
    print(f"  FJA {cat}: {len(items)} items | first: {items[0]['name'][:55]}")

# --- Fix ALL Sarkari categories (SR_Latest_Jobs, SR_Result, OFFLINE_FORM, etc.) ---
sark_jobs = (cj.get('sarkari_data') or {}).get('jobs', [])
new_sark = {}
for j in sark_jobs:
    cat = (j.get('category') or '').strip()
    if not cat: continue
    title = (j.get('title') or '').strip()
    if not title: continue
    if cat not in new_sark:
        new_sark[cat] = []
    if len(new_sark[cat]) >= 10:
        continue
    slug = slugify(title)
    imp = (j.get('important_dates') or {})
    ld = (imp.get('last_date','') or imp.get('last_date_to_apply','')).strip()
    new_sark[cat].append({'slug': slug, 'name': title, 'date': ld})

for cat, items in new_sark.items():
    si[cat] = items
    fixed += 1
    print(f"  SARK {cat}: {len(items)} items | first: {items[0]['name'][:55]}")

# Write updated sections-index.json
with open(si_path, 'w', encoding='utf-8') as f:
    json.dump(si, f, ensure_ascii=False, separators=(',',':'))
print(f"\n✅ Done! {fixed} categories updated in {si_path}")

# Update cache-buster version in index.html
ver = datetime.now().strftime('%Y%m%d%H%M')
idx_path = ROOT / 'index.html'
if idx_path.exists():
    with open(idx_path, encoding='utf-8') as f:
        html = f.read()
    new_html = re.sub(r'sections-index\.json\?v=\d+', f'sections-index.json?v={ver}', html)
    if new_html != html:
        with open(idx_path, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print(f"✅ Cache-busted index.html: v={ver}")
