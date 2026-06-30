#!/usr/bin/env python3
"""
scripts/validate.py — Pre-deploy 404 and integrity validation
=============================================================
Checks that every job linked from listing/index pages has an
actual index.html on disk, and that no blocked domains leaked
into generated HTML.

Usage:
  python scripts/validate.py          # warns only
  python scripts/validate.py --fail   # exit 1 on any error (CI use)
"""
import json, re, sys, os, glob
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
FAIL    = '--fail' in sys.argv

os.chdir(ROOT)

errors   = []
warnings = []

def err(msg):
    errors.append(msg)
    print(f'  [ERROR] {msg}')

def warn(msg):
    warnings.append(msg)
    print(f'  [WARN]  {msg}')

# ── 1. jobs-index.json slug check ─────────────────────────────────────────────
print('Checking jobs-index.json slugs...')
index_path = ROOT / 'jobs-index.json'
if not index_path.exists():
    warn('jobs-index.json not found — skipping slug check')
else:
    try:
        idx = json.loads(index_path.read_text(encoding='utf-8'))
    except Exception as ex:
        err(f'jobs-index.json parse error: {ex}')
        idx = []

    missing_pages = []
    slugs_seen = set()
    dup_slugs = []
    for job in (idx if isinstance(idx, list) else []):
        slug = (job.get('slug') or job.get('_canonical_slug') or '').strip()
        if not slug:
            continue
        if slug in slugs_seen:
            dup_slugs.append(slug)
        slugs_seen.add(slug)
        page = ROOT / 'jobs' / slug / 'index.html'
        if not page.exists():
            missing_pages.append(slug)

    if dup_slugs:
        for s in dup_slugs[:10]:
            err(f'Duplicate slug in jobs-index.json: {s}')
    if missing_pages:
        for s in missing_pages[:20]:
            warn(f'jobs-index slug has no built page: /jobs/{s}/')
        print(f'  → {len(missing_pages)} job(s) in index have no built page')
    else:
        print(f'  OK — all {len(slugs_seen)} index slugs have built pages')

# ── 2. Link-to-disk: scan listing HTML for /jobs/{slug}/ hrefs ────────────────
print('Checking listing-page links against disk...')
HREF_RE = re.compile(r'href="/jobs/([^/"]+)/', re.I)
listing_pages = (
    list(glob.glob('section/*/index.html')) +
    list(glob.glob('state/*/index.html')) +
    list(glob.glob('category/**/index.html', recursive=True)) +
    list(glob.glob('education/*/index.html')) +
    ['index.html']
)
link_missing = {}
scanned = 0
for fpath in listing_pages:
    fp = Path(fpath)
    if not fp.exists():
        continue
    scanned += 1
    html = fp.read_text(encoding='utf-8', errors='replace')
    for m in HREF_RE.finditer(html):
        slug = m.group(1)
        page = ROOT / 'jobs' / slug / 'index.html'
        if not page.exists():
            link_missing.setdefault(slug, []).append(str(fpath))

if link_missing:
    for slug, sources in sorted(link_missing.items())[:20]:
        warn(f'Link to /jobs/{slug}/ in [{sources[0]}] has no built page')
    print(f'  → {len(link_missing)} unique broken link target(s) across {scanned} listing pages')
else:
    print(f'  OK — all links in {scanned} listing pages resolve to built pages')

# ── 3. Blocked-domain leak check ──────────────────────────────────────────────
print('Checking for blocked-domain leakage in job pages...')
BLOCKED = {'sarkariresult.com', 'freejobalert.com', 'sarkarinetwork.com',
           'sarkariresultshine.com'}
all_pages = list(glob.glob('jobs/*/index.html'))
domain_violations = []
for fpath in all_pages:
    try:
        html = open(fpath, encoding='utf-8', errors='ignore').read().lower()
    except Exception:
        continue
    # Only flag blocked domains inside href/src/action attributes (not in page text)
    for domain in BLOCKED:
        if f'href="https://{domain}' in html or f'href="http://{domain}' in html:
            domain_violations.append(f"'{domain}' in href: {fpath}")

if domain_violations:
    for v in domain_violations[:20]:
        err(v)
else:
    print(f'  OK — no blocked domains in hrefs across {len(all_pages)} job pages')

# ── 4. Duplicate TSJ_AI_BLOCK sentinels ───────────────────────────────────────
print('Checking for duplicate AI block sentinels...')
dup_ai = []
for fpath in all_pages:
    try:
        content = open(fpath, encoding='utf-8', errors='ignore').read()
    except Exception:
        continue
    if content.count('<!-- TSJ_AI_BLOCK_START -->') > 1:
        dup_ai.append(fpath)
    if content.count('<!-- TSJ_AI_FAQ_START -->') > 1:
        dup_ai.append(f'{fpath} (FAQ)')

if dup_ai:
    for f in dup_ai[:10]:
        err(f'Duplicate AI sentinel in: {f}')
else:
    print(f'  OK — no duplicate AI sentinels in {len(all_pages)} job pages')

# ── Summary ────────────────────────────────────────────────────────────────────
print()
print(f'VALIDATION SUMMARY:')
print(f'  Errors:   {len(errors)}')
print(f'  Warnings: {len(warnings)}')

if errors and FAIL:
    sys.exit(1)
elif errors:
    print('  (run with --fail to exit 1 on errors)')
else:
    print('  All checks passed.')
