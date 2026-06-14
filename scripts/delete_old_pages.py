#!/usr/bin/env python3
"""
delete_old_pages.py — MANUAL old-page cleanup (run only from GitHub Actions UI).

Deletes /jobs/<slug>/ pages whose FIRST-SEEN date is older than a chosen age.
Age threshold and dry-run are passed as environment variables by the workflow:

    OLDER_THAN_DAYS  : integer number of days (e.g. 365 = 1 year, 730 = 2 years)
    DRY_RUN          : "true" to only PREVIEW (delete nothing), "false" to delete
    KEEP_INDEXED     : "true" (default) — never delete a page that is < MIN_KEEP_DAYS
                       old, as an extra safety net so freshly-indexed pages survive.

Age source: data/job-first-seen.json  ({ "<slug>": "YYYY-MM-DD", ... })
Pages with NO first-seen record are treated as UNKNOWN age and are NEVER deleted
(safe default — we don't delete something we can't date).

This script is intentionally conservative: it only touches /jobs/<slug>/ folders,
never section/category/state/education listing pages.
"""

import os
import sys
import json
import shutil
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_DIR = os.path.join(ROOT, 'jobs')
FIRST_SEEN_PATH = os.path.join(ROOT, 'data', 'job-first-seen.json')

# ── Read config from environment (set by the workflow inputs) ────────────────
def _int_env(name, default):
    try:
        return int(str(os.environ.get(name, default)).strip())
    except Exception:
        return default

OLDER_THAN_DAYS = _int_env('OLDER_THAN_DAYS', 365)
DRY_RUN = str(os.environ.get('DRY_RUN', 'true')).strip().lower() != 'false'
KEEP_INDEXED = str(os.environ.get('KEEP_INDEXED', 'true')).strip().lower() != 'false'

# Hard safety floor: never delete anything younger than this, no matter what.
MIN_KEEP_DAYS = 180  # 6 months — protects newly indexed pages

if OLDER_THAN_DAYS < MIN_KEEP_DAYS:
    print(f"⚠️  OLDER_THAN_DAYS ({OLDER_THAN_DAYS}) is below the safety floor "
          f"({MIN_KEEP_DAYS}). Clamping to {MIN_KEEP_DAYS} to protect SEO.")
    OLDER_THAN_DAYS = MIN_KEEP_DAYS

TODAY = date.today()

print("=" * 60)
print("  OLD PAGE CLEANUP (manual)")
print("=" * 60)
print(f"  Threshold : delete pages older than {OLDER_THAN_DAYS} days "
      f"(~{OLDER_THAN_DAYS/365:.1f} years)")
print(f"  Mode      : {'DRY-RUN (preview only, nothing deleted)' if DRY_RUN else 'LIVE DELETE'}")
print(f"  Safety    : keep anything < {MIN_KEEP_DAYS} days old")
print("=" * 60)

# ── Load first-seen dates ────────────────────────────────────────────────────
if not os.path.exists(FIRST_SEEN_PATH):
    print(f"❌ {FIRST_SEEN_PATH} not found — cannot determine page ages. Aborting "
          "(no pages deleted).")
    sys.exit(0)

with open(FIRST_SEEN_PATH, encoding='utf-8') as f:
    first_seen = json.load(f)

def _age_days(slug):
    """Return age in days from first-seen date, or None if unknown/unparseable."""
    ds = first_seen.get(slug)
    if not ds:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            d = datetime.strptime(str(ds).strip(), fmt).date()
            return (TODAY - d).days
        except Exception:
            continue
    return None

# ── Scan /jobs/ folders ──────────────────────────────────────────────────────
if not os.path.isdir(JOBS_DIR):
    print("❌ jobs/ directory not found. Nothing to do.")
    sys.exit(0)

to_delete = []
unknown = 0
kept = 0
skipped_data = 0

for name in sorted(os.listdir(JOBS_DIR)):
    full = os.path.join(JOBS_DIR, name)
    if not os.path.isdir(full):
        continue
    if name == 'data':          # /jobs/data holds per-slug JSON — never delete
        skipped_data += 1
        continue
    age = _age_days(name)
    if age is None:
        unknown += 1            # unknown age → keep (safe)
        continue
    if age >= OLDER_THAN_DAYS:
        to_delete.append((name, age))
    else:
        kept += 1

# ── Report ───────────────────────────────────────────────────────────────────
print(f"\nScanned {len(os.listdir(JOBS_DIR))} entries in jobs/")
print(f"  • kept (younger than threshold) : {kept}")
print(f"  • unknown age (kept, safe)      : {unknown}")
print(f"  • eligible for deletion         : {len(to_delete)}")
print()

if not to_delete:
    print("✅ Nothing matches the threshold. No pages deleted.")
    sys.exit(0)

# Show a preview (oldest first)
to_delete.sort(key=lambda x: -x[1])
print("Pages that " + ("WOULD be" if DRY_RUN else "WILL be") + " deleted "
      "(oldest first, showing up to 40):")
for slug, age in to_delete[:40]:
    print(f"   - {slug}  ({age} days ≈ {age/365:.1f}y)")
if len(to_delete) > 40:
    print(f"   ... and {len(to_delete) - 40} more")

# ── Delete (only if not dry-run) ─────────────────────────────────────────────
if DRY_RUN:
    print(f"\n🔍 DRY-RUN complete. {len(to_delete)} pages matched but NOTHING was "
          "deleted. Re-run with dry_run = false to actually delete.")
    # Write a manifest so you can review in the run artifacts/log
    sys.exit(0)

deleted = 0
removed_slugs = []
for slug, age in to_delete:
    folder = os.path.join(JOBS_DIR, slug)
    try:
        shutil.rmtree(folder)
        # also remove the matching per-slug JSON if present
        pj = os.path.join(JOBS_DIR, 'data', slug + '.json')
        if os.path.exists(pj):
            os.remove(pj)
        # drop it from first-seen so the file stays clean
        first_seen.pop(slug, None)
        removed_slugs.append(slug)
        deleted += 1
    except Exception as ex:
        print(f"   ! failed to delete {slug}: {ex}")

# Save the pruned first-seen file
try:
    with open(FIRST_SEEN_PATH, 'w', encoding='utf-8') as f:
        json.dump(first_seen, f, ensure_ascii=False, indent=0)
except Exception as ex:
    print(f"   ! could not update first-seen file: {ex}")

print(f"\n🗑️  Deleted {deleted} old page(s).")
print("ℹ️  Remember: deleted URLs will 404. Submit a fresh sitemap and, if needed, "
      "add 301 redirects for any high-traffic ones.")
