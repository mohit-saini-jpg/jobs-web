"""
generate_jobs.py — Auto-runs when Complete_Jobs_Full_Data.json is pushed to GitHub
====================================================================================
Sirf Complete_Jobs_Full_Data.json push karo → ye script sab kar deta hai:
  1. jobs/data/<category>/<slug>.json — category-wise subfolders mein split
  2. jobs-index.json  — fast index (slug → cat/cat_folder/title/date/url)
  3. Purani stale files — automatically delete ho jaati hain

Category folders:
  latest-notifications, 10th-pass, 8th-pass, 12th-pass, diploma, iti,
  b-tech-be, b-com, any-graduate, any-post-graduate, railway-jobs,
  police-defence, teaching-faculty, bank-jobs, medical-hospital
"""

import json, re, os, shutil

SRC   = "Complete_Jobs_Full_Data.json"
DEST  = "jobs/data"
INDEX = "jobs-index.json"

VALID_CATS = {
    "Latest_Notifications", "10TH_Pass", "8TH_Pass", "12TH_Pass",
    "Diploma", "ITI", "B_Tech_BE", "B_Com", "Any_Graduate",
    "Any_Post_Graduate", "Railway_Jobs", "Police_Defence",
    "Teaching_Faculty", "Bank_Jobs", "Medical_Hospital",
    "Last_Date_Reminder",
}

# Category name → folder name mapping
CAT_FOLDER = {
    "Latest_Notifications": "latest-notifications",
    "10TH_Pass":            "10th-pass",
    "8TH_Pass":             "8th-pass",
    "12TH_Pass":            "12th-pass",
    "Diploma":              "diploma",
    "ITI":                  "iti",
    "B_Tech_BE":            "b-tech-be",
    "B_Com":                "b-com",
    "Any_Graduate":         "any-graduate",
    "Any_Post_Graduate":    "any-post-graduate",
    "Railway_Jobs":         "railway-jobs",
    "Police_Defence":       "police-defence",
    "Teaching_Faculty":     "teaching-faculty",
    "Bank_Jobs":            "bank-jobs",
    "Medical_Hospital":     "medical-hospital",
    "Last_Date_Reminder":   "last-date-reminder",
}

def slugify(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text[:120].strip("-") or "job"

print(f"Loading {SRC}...")
with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

os.makedirs(DEST, exist_ok=True)

# ── Build set of ALL existing files (slug → cat_folder/slug.json) ──
existing_files = set()
for cat_folder in os.listdir(DEST):
    cat_path = os.path.join(DEST, cat_folder)
    if os.path.isdir(cat_path):
        for fname in os.listdir(cat_path):
            existing_files.add(f"{cat_folder}/{fname}")
    elif cat_folder.endswith(".json"):
        # Old flat files — will be migrated/deleted
        existing_files.add(cat_folder)

# Create all category subfolders
for folder in CAT_FOLDER.values():
    os.makedirs(os.path.join(DEST, folder), exist_ok=True)

index      = {}
new_files  = set()
written    = 0
skipped    = 0
seen_slugs = {}

for cat, jobs in data.items():
    if not isinstance(jobs, list):
        continue
    if cat not in VALID_CATS:
        print(f"  WARN: Unknown category '{cat}' — skipping")
        continue

    cat_folder = CAT_FOLDER.get(cat, slugify(cat))

    for job in jobs:
        bd    = job.get("basic_details", {}) or {}
        dates = job.get("important_dates", {}) or {}
        title = (bd.get("job_title", "") or "").strip()
        url   = (job.get("source_url", "") or "").strip()

        if not title:
            skipped += 1
            continue

        slug  = slugify(title)
        fname = f"{slug}.json"

        # Duplicate slug across categories? Add category suffix
        if slug in seen_slugs and seen_slugs[slug] != cat:
            slug  = f"{slug}-{cat.lower().replace('_','-')}"
            fname = f"{slug}.json"

        seen_slugs[slug] = cat
        job["category"]  = cat

        # Write to category subfolder: jobs/data/<cat_folder>/<slug>.json
        rel_path = f"{cat_folder}/{fname}"
        full_path = os.path.join(DEST, cat_folder, fname)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(job, f, ensure_ascii=False, separators=(",", ":"))

        last_date = (dates.get("last_date", "") or "").strip()
        index[slug] = {
            "cat":        cat,
            "cat_folder": cat_folder,
            "title":      title[:120],
            "last_date":  last_date[:30] if last_date else "",
            "url":        url,
        }
        new_files.add(rel_path)
        written += 1

# ── Delete stale files ──
# Remove files that are no longer generated
stale_count = 0
for rel_path in existing_files - new_files:
    full = os.path.join(DEST, rel_path)
    try:
        if os.path.isfile(full):
            os.remove(full)
            stale_count += 1
    except Exception:
        pass

# Remove empty old flat files (migration: flat → subfolders)
for item in os.listdir(DEST):
    item_path = os.path.join(DEST, item)
    if item.endswith(".json") and os.path.isfile(item_path):
        try:
            os.remove(item_path)
            stale_count += 1
        except Exception:
            pass

# Remove empty category folders (cleanup)
for item in os.listdir(DEST):
    item_path = os.path.join(DEST, item)
    if os.path.isdir(item_path) and not os.listdir(item_path):
        try:
            os.rmdir(item_path)
        except Exception:
            pass

# Write index
with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

print(f"\nDone!")
print(f"  Written : {written} job files → category subfolders")
print(f"  Deleted : {stale_count} stale/old files")
print(f"  Skipped : {skipped} (no title)")
print(f"  Index   : {len(index)} entries → {INDEX}")

cat_count = {}
for v in index.values():
    cat_count[v["cat"]] = cat_count.get(v["cat"], 0) + 1
print("\nPer category folder:")
for cat, folder in sorted(CAT_FOLDER.items()):
    n = cat_count.get(cat, 0)
    print(f"  jobs/data/{folder:<30} {n} files")
