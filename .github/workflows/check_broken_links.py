#!/usr/bin/env python3
"""
Auto-fix broken job links:
- Checks all sections-index.json slugs vs actual disk pages
- Adds 301 redirects for slugs that have fuzzy-match on disk
- Inserts new rules at TOP of /jobs/ section (NOT bottom) so Netlify limit doesn't cut them
- Reports truly missing pages
"""
import json, os, re, sys, datetime

ROOT = '.'
jobs_dir = os.path.join(ROOT, 'jobs')
redirects_path = os.path.join(ROOT, '_redirects')
summary_path = os.environ.get('GITHUB_STEP_SUMMARY', '/tmp/summary.md')

def norm(s):
    """Normalize slug for fuzzy matching: remove all non-alphanumeric"""
    return re.sub(r'[^a-z0-9]', '', s.lower())

# Load current redirects
existing = open(redirects_path, encoding='utf-8').read() if os.path.exists(redirects_path) else ''

# Get all valid disk pages (exclude "Page Not Available" pages)
disk_pages = set()
if os.path.isdir(jobs_dir):
    for d in os.listdir(jobs_dir):
        page_path = os.path.join(jobs_dir, d, 'index.html')
        if os.path.isfile(page_path):
            try:
                content = open(page_path, encoding='utf-8').read()
                if 'Page Not Available' not in content:
                    disk_pages.add(d)
            except Exception:
                pass

print(f"Valid disk pages: {len(disk_pages)}")

# Build normalized → actual slug map
disk_norm = {}
for s in disk_pages:
    n = norm(s)
    if n not in disk_norm:
        disk_norm[n] = s

# Load sections-index.json
si_path = os.path.join(ROOT, 'sections-index.json')
si = json.load(open(si_path, encoding='utf-8'))

broken = []
ok_count = 0
seen_broken = set()

for cat, items in si.items():
    if not isinstance(items, list):
        continue
    for item in items:
        slug = item.get('slug', '')
        if not slug:
            continue
        if slug in disk_pages:
            ok_count += 1
            continue
        if slug in seen_broken:
            continue
        seen_broken.add(slug)

        # Try normalized (fuzzy) match
        n = norm(slug)
        if n in disk_norm:
            broken.append((slug, disk_norm[n], 'fuzzy', cat))
            continue

        # Try prefix match (first 35 normalized chars)
        prefix = n[:35]
        matches = [v for k, v in disk_norm.items() if k.startswith(prefix) and len(k) >= len(prefix)]
        if matches:
            best = max(matches, key=lambda x: len(os.path.commonprefix([norm(x), n])))
            broken.append((slug, best, 'prefix', cat))
        else:
            broken.append((slug, None, 'no-match', cat))

print(f"OK links: {ok_count}")
print(f"Broken links: {len(broken)}")

# Build redirect rules for fixable ones
new_rules = []
truly_missing = []

for broken_slug, match, match_type, cat in broken:
    if match and match_type in ('fuzzy', 'prefix'):
        rule = f"/jobs/{broken_slug}/  /jobs/{match}/  301"
        if rule not in existing:
            new_rules.append(rule)
            print(f"  REDIRECT: {broken_slug[:55]}")
            print(f"         -> {match[:55]}")
    else:
        truly_missing.append((broken_slug, cat))

# ── KEY FIX: Insert new rules at TOP of /jobs/ section, NOT at bottom ──
if new_rules:
    lines = existing.split('\n')
    
    # Find the /jobs/ slug mismatch section header
    insert_pos = None
    for i, line in enumerate(lines):
        if '# ── 4. /jobs/ slug mismatch' in line or '# ── PRIORITY FIX' in line:
            insert_pos = i + 1
            break
    
    # Fallback: insert after www/canonical section (first 15 lines)
    if insert_pos is None:
        for i, line in enumerate(lines):
            if line.strip().startswith('/jobs/') and '301' in line:
                insert_pos = i
                break
    
    if insert_pos is None:
        insert_pos = 10  # safe fallback

    block_lines = [f"# Auto-fixed broken links ({len(new_rules)}) — {datetime.date.today()}"] + new_rules + ['']
    new_content = '\n'.join(lines[:insert_pos] + block_lines + lines[insert_pos:])
    
    with open(redirects_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"\nAdded {len(new_rules)} redirect rules at TOP of /jobs/ section in _redirects")
else:
    print("\nNo new redirects needed — all links OK")

if truly_missing:
    print(f"\nTruly missing ({len(truly_missing)}) — need new scrape:")
    for slug, cat in truly_missing[:20]:
        print(f"  [{cat}] {slug}")

# GitHub Actions summary
summary = f"""## Broken Link Check Results

| Metric | Count |
|--------|-------|
| Valid disk pages | {len(disk_pages)} |
| OK links | {ok_count} |
| Auto-fixed (redirect added) | {len(new_rules)} |
| Truly missing (no match found) | {len(truly_missing)} |
"""

if truly_missing:
    summary += "\n### Truly Missing Pages (no fuzzy match — need scraper re-run):\n"
    for slug, cat in truly_missing:
        summary += f"- `[{cat}]` `{slug}`\n"

if new_rules:
    summary += f"\n### Auto-fixed Redirects Added ({len(new_rules)}):\n"
    for rule in new_rules[:10]:
        summary += f"- `{rule}`\n"

with open(summary_path, 'w', encoding='utf-8') as f:
    f.write(summary)

sys.exit(0)
