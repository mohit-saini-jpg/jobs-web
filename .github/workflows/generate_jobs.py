"""
generate_jobs.py — Auto-runs when Complete_Jobs_Full_Data.json is pushed to GitHub
====================================================================================
Sirf Complete_Jobs_Full_Data.json push karo → ye script sab kar deta hai:
  1. jobs/data/<slug>.json — har job ke liye alag file banata hai
  2. jobs-index.json       — fast index (slug → cat/title/date/url)
  3. Purani stale files    — automatically delete ho jaati hain

365 jobs ho ya 1500+ — sab handle hoga!
"""

import json, re, os

SRC   = "Complete_Jobs_Full_Data.json"
DEST  = "jobs/data"
INDEX = "jobs-index.json"

VALID_CATS = {
    "Latest_Notifications", "10TH_Pass", "8TH_Pass", "12TH_Pass",
    "Diploma", "ITI", "B_Tech_BE", "B_Com", "Any_Graduate",
    "Any_Post_Graduate", "Railway_Jobs", "Police_Defence",
    "Teaching_Faculty", "Bank_Jobs", "Medical_Hospital",
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

existing_files = set(os.listdir(DEST))
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

        # Duplicate slug? Add category suffix
        if slug in seen_slugs and seen_slugs[slug] != cat:
            slug  = f"{slug}-{cat.lower().replace('_','-')}"
            fname = f"{slug}.json"

        seen_slugs[slug] = cat
        job["category"]  = cat

        with open(os.path.join(DEST, fname), "w", encoding="utf-8") as f:
            json.dump(job, f, ensure_ascii=False, separators=(",", ":"))

        last_date = (dates.get("last_date", "") or "").strip()
        index[slug] = {
            "cat":       cat,
            "title":     title[:120],
            "last_date": last_date[:30] if last_date else "",
            "url":       url,
        }
        new_files.add(fname)
        written += 1

# Delete stale files
stale = existing_files - new_files
for fname in stale:
    try:
        os.remove(os.path.join(DEST, fname))
    except Exception:
        pass

# Write index
with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

print(f"\nDone!")
print(f"  Written : {written} job files")
print(f"  Deleted : {len(stale)} stale files")
print(f"  Skipped : {skipped} (no title)")
print(f"  Index   : {len(index)} entries")

cat_count = {}
for v in index.values():
    cat_count[v["cat"]] = cat_count.get(v["cat"], 0) + 1
print("\nPer category:")
for cat in ["Latest_Notifications","10TH_Pass","8TH_Pass","12TH_Pass","Diploma",
            "ITI","B_Tech_BE","B_Com","Any_Graduate","Any_Post_Graduate",
            "Railway_Jobs","Police_Defence","Teaching_Faculty","Bank_Jobs","Medical_Hospital"]:
    n = cat_count.get(cat, 0)
    print(f"  {cat:<25} {n}")
