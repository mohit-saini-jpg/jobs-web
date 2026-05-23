"""
generate_sarkari.py — merged_sarkari_data.json ko split karta hai
====================================================================
Jab bhi merged_sarkari_data.json push ho → ye script:
  1. jobs/data/<slug>.json   — har sarkari job ke liye alag file
                               (SAME folder jahan Complete_Jobs_Full_Data.json split hoti hai)
  2. sarkari-index.json      — fast index (slug → cat/title/last_date)
  3. merged-sarkari-mini.json — homepage ke liye lightweight version
  4. Purani stale files      — auto delete (sirf sarkari-source wali)

Note: jobs/data/ mein already Complete_Jobs_Full_Data.json ki files hain.
      Slug conflicts avoid karne ke liye sarkari slugs mein "-sr" suffix lagta hai
      agar same slug pehle se exist kare.
"""

import json, re, os

SRC        = "merged_sarkari_data.json"
DEST       = "sarkari/data"
INDEX_FILE = "sarkari-index.json"
MINI_FILE  = "merged-sarkari-mini.json"

# Sarkari files ko track karne ke liye marker (taaki stale delete sahi ho)
SARKARI_MARKER = "__src_sarkari"   # job JSON mein ye field hogi

# Mini me sirf ye fields chahiye (homepage display ke liye)
MINI_FIELDS = {"category", "title", "listing_date", "organization",
               "total_vacancy", "apply_mode", "job_location",
               "important_dates", "slug"}

def slugify(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text[:120].strip("-") or "job"

print(f"Loading {SRC}...")
with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

jobs = data.get("jobs", [])
if not isinstance(jobs, list):
    print("ERROR: 'jobs' array not found in merged_sarkari_data.json")
    exit(1)

print(f"Total sarkari jobs: {len(jobs)}")

os.makedirs(DEST, exist_ok=True)

# Existing files mein sirf sarkari-source wali files track karo
# (jobs/data mein Complete_Jobs_Full_Data ki files bhi hain — unhe touch mat karo)
existing_all   = set(os.listdir(DEST))
existing_sarkari = set()
for fname in existing_all:
    fpath = os.path.join(DEST, fname)
    try:
        with open(fpath, encoding="utf-8") as f:
            obj = json.load(f)
        if obj.get(SARKARI_MARKER):
            existing_sarkari.add(fname)
    except Exception:
        pass

print(f"Existing sarkari files in jobs/data: {len(existing_sarkari)}")

# Complete_Jobs slugs — to avoid overwriting them
complete_slugs = existing_all - existing_sarkari

index      = {}
mini_jobs  = []
new_files  = set()
written    = 0
skipped    = 0
seen_slugs = {}

for job in jobs:
    title = (job.get("title", "") or "").strip()
    if not title:
        skipped += 1
        continue

    cat  = (job.get("category", "") or "SARKARI").strip()
    slug = slugify(title)

    # Duplicate slug within sarkari? Add category suffix
    if slug in seen_slugs and seen_slugs[slug] != cat:
        slug = f"{slug}-{slugify(cat)}"

    # Conflict with Complete_Jobs_Full_Data slug? Add -sr suffix
    fname_candidate = f"{slug}.json"
    if fname_candidate in complete_slugs:
        slug  = f"{slug}-sr"
        fname_candidate = f"{slug}.json"

    seen_slugs[slug] = cat
    fname = fname_candidate

    # Mark as sarkari source + embed slug
    job[SARKARI_MARKER] = True
    job["slug"]          = slug
    job["category"]      = cat

    with open(os.path.join(DEST, fname), "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False, separators=(",", ":"))

    # Index entry
    dates     = job.get("important_dates", {}) or {}
    last_date = (dates.get("last_date", "") or "").strip()
    index[slug] = {
        "cat":       cat,
        "title":     title[:120],
        "last_date": last_date[:30] if last_date else "",
        "org":       (job.get("organization", "") or "")[:80],
    }

    # Mini entry (homepage ke liye)
    mini_job = {k: v for k, v in job.items() if k in MINI_FIELDS}
    mini_job["slug"] = slug
    mini_jobs.append(mini_job)

    new_files.add(fname)
    written += 1

# Stale sarkari files delete karo (sirf jo is run mein nahi bani)
stale = existing_sarkari - new_files
for fname in stale:
    try:
        os.remove(os.path.join(DEST, fname))
        print(f"  Deleted stale: {fname}")
    except Exception:
        pass

# Index write
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

# Mini JSON write
mini_data = {
    "scraped_at": data.get("scraped_at", ""),
    "total":      len(mini_jobs),
    "jobs":       mini_jobs,
}
with open(MINI_FILE, "w", encoding="utf-8") as f:
    json.dump(mini_data, f, ensure_ascii=False, separators=(",", ":"))

# Category count
cat_count = {}
for v in index.values():
    cat_count[v["cat"]] = cat_count.get(v["cat"], 0) + 1

print(f"\nDone!")
print(f"  Written : {written} sarkari job files → {DEST}/")
print(f"  Deleted : {len(stale)} stale sarkari files")
print(f"  Skipped : {skipped} (no title)")
print(f"  Index   : {INDEX_FILE} ({len(index)} entries)")
print(f"  Mini    : {MINI_FILE}")
print(f"  Total jobs/data files now: {len(os.listdir(DEST))}")
print(f"\nPer category:")
for cat, n in sorted(cat_count.items()):
    print(f"  {cat:<30} {n}")
