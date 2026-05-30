#!/usr/bin/env python3
"""
scripts/validate.py — Validate master_clean_jobs.json and generated pages
"""
import json, glob, os
from pathlib import Path

# Run from site root
import sys
site_root = Path(__file__).parent.parent
os.chdir(site_root)

print("🔍 Validating master_clean_jobs.json...")
with open("data/master_clean_jobs.json", encoding="utf-8") as f:
    jobs = json.load(f)

slugs = [j['slug'] for j in jobs]
assert len(slugs) == len(set(slugs)), "❌ DUPLICATE SLUGS FOUND!"
assert all(j.get('title') for j in jobs), "❌ EMPTY TITLES FOUND!"
assert all(j.get('slug') for j in jobs), "❌ EMPTY SLUGS FOUND!"

print(f"   ✅ {len(jobs)} jobs — no duplicate slugs, no empty titles")

print("🔍 Checking all job pages exist...")
missing = []
for job in jobs:
    page = Path(f"jobs/{job['slug']}/index.html")
    if not page.exists():
        missing.append(job['slug'])

if missing:
    print(f"   ⚠️  {len(missing)} pages missing (may be existing pages from before dedup):")
    for m in missing[:10]:
        print(f"      - {m}")
else:
    print(f"   ✅ All {len(jobs)} job pages exist")

# Competitor domain check
BLOCKED_DOMAINS = [
    "sarkariresult.com", "freejobalert.com",
    "sarkarinetwork.com", "sarkariresultshine.com"
]

print("🔍 Checking for competitor domain violations...")
violations = []
all_pages = list(glob.glob("jobs/*/index.html"))
for filepath in all_pages:
    html = open(filepath, encoding='utf-8', errors='ignore').read().lower()
    for domain in BLOCKED_DOMAINS:
        if domain in html:
            violations.append(f"BLOCKED DOMAIN '{domain}' in: {filepath}")

if violations:
    print(f"   ❌ {len(violations)} VIOLATIONS FOUND:")
    for v in violations[:20]:
        print(f"      {v}")
else:
    print(f"   ✅ No competitor domains found in {len(all_pages)} job pages")

# Source field check
print("🔍 Checking source field not exposed in HTML...")
source_violations = []
for filepath in all_pages:
    html = open(filepath, encoding='utf-8', errors='ignore').read()
    for s in ['freejobalert', 'sarkarinetwork', 'sarkariresult']:
        if s in html.lower():
            source_violations.append(f"Source field visible: '{s}' in {filepath}")
            break

if source_violations:
    print(f"   ❌ {len(source_violations)} source field violations:")
    for v in source_violations[:10]:
        print(f"      {v}")
else:
    print(f"   ✅ No source field leakage found")

# Count pages
total_pages = len(all_pages)
print(f"\n📊 SUMMARY:")
print(f"   Clean jobs in master JSON: {len(jobs)}")
print(f"   Total job HTML pages:      {total_pages}")
print(f"   Violations:                {len(violations) + len(source_violations)}")
print(f"\n✅ Validation complete.")
