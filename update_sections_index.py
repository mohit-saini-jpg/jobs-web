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
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')

def _norm_slug(s):
    """Mirror of generate_all.py _norm_slug — collapse dashes, cap at 80."""
    s = str(s or '').strip().lower()
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')[:80].strip('-')

def canonical_slug(job, title):
    """THE single source of truth for a job's URL slug — identical priority to
    generate_all.py get_canonical_slug(). Prevents the section-card list (built
    from sections-index.json) from diverging from the physical /jobs/<slug>/ page.
      1. _canonical_slug (scraper-set, immutable)
      2. slug field (strip sr_ prefix + trailing hex hash)
      3. slugify(title) fallback
    """
    cs = str(job.get('_canonical_slug') or '').strip()
    if cs:
        return _norm_slug(cs)
    raw = str(job.get('slug') or '').strip()
    if raw:
        raw = re.sub(r'^sr_[a-z_]+-', '', raw)
        m = re.search(r'-([0-9a-f]{6,8})$', raw)
        if m and not m.group(1).isdigit():
            raw = raw[:-len(m.group(0))]
        s = _norm_slug(raw)
        if s:
            return s
    return slugify(title)[:80]

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

# Ground-truth set of pages that physically exist, so we never list a 404 slug.
# Only enforced when pages are present (avoids emptying lists in a bare checkout).
_JOB_DIRS = {p.name for p in (ROOT / 'jobs').glob('*') if p.is_dir()} if (ROOT / 'jobs').is_dir() else set()
def _page_exists(slug):
    return (not _JOB_DIRS) or (slug in _JOB_DIRS)

# --- Fix ALL FJA categories (10TH_Pass, 12TH_Pass, ITI, Diploma, etc.) ---
fja = cj.get('freejobalert_categories', {})
for cat, jobs in fja.items():
    if not isinstance(jobs, list) or not jobs: continue
    items = []
    for j in jobs:
        bd = (j.get('basic_details') or {})
        title = (bd.get('job_title','') or '').strip()
        if not title: continue
        slug = canonical_slug(j, title)   # canonical — matches /jobs/<slug>/ page
        if not _page_exists(slug): continue   # never list a 404
        imp = (j.get('important_dates') or {})
        ld = (imp.get('last_date_to_apply','') or imp.get('last_date','')).strip()
        items.append({'slug': slug, 'name': title, 'date': ld})
        if len(items) >= 10: break
    if items:
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
    slug = canonical_slug(j, title)   # canonical — matches /jobs/<slug>/ page
    if not _page_exists(slug): continue   # never list a 404
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
