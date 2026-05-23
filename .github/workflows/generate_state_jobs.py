"""
generate_state_jobs.py — state-jobs-data.json ko per-state files mein split karta hai
========================================================================================
Jab bhi state-jobs-data.json push ho → ye script:
  1. state/data/<state-id>.json — har state ke liye alag file (e.g. state/data/delhi.json)
  2. state-jobs-index.json       — fast index (state-id → state-name, item count, items[])
  3. state-jobs-mini.json        — ultra-light version (sirf state IDs + titles + counts)
  4. Purani stale files          — auto delete

Performance impact:
  Before: state-jobs.html → 2.2 MB state-jobs-data.json fetch karta tha (ALWAYS)
  After:  state-jobs.html → 3-5 KB state-jobs-mini.json + sirf 1 state ki file (~15-80 KB)
"""

import json, re, os

SRC        = "state-jobs-data.json"
DEST       = "state/data"
INDEX_FILE = "state-jobs-index.json"
MINI_FILE  = "state-jobs-mini.json"

print(f"Loading {SRC}...")
with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

sections = data.get("sections", [])
if not isinstance(sections, list):
    print("ERROR: 'sections' array not found in state-jobs-data.json")
    exit(1)

print(f"Total sections (states): {len(sections)}")

os.makedirs(DEST, exist_ok=True)
existing_files = set(os.listdir(DEST))

index      = {}
mini_items = []
new_files  = set()
written    = 0
total_jobs = 0

for section in sections:
    state_id    = (section.get("id", "") or "").strip()
    state_name  = (section.get("state", "") or "").strip()
    section_title = (section.get("title", "") or state_name).strip()
    items       = section.get("items", []) or []

    if not state_id or not state_name:
        print(f"  WARN: Section missing id/state — skipping: {section}")
        continue

    fname = f"{state_id}.json"

    # Individual state file — full data
    state_data = {
        "id":    state_id,
        "state": state_name,
        "title": section_title,
        "items": items,
    }
    with open(os.path.join(DEST, fname), "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, separators=(",", ":"))

    # Index entry — full items (for state-jobs.html lazy load)
    index[state_id] = {
        "state": state_name,
        "title": section_title,
        "count": len(items),
        "items": items,  # Full items for API-style access
    }

    # Mini entry — sirf metadata (homepage / dropdown ke liye)
    mini_items.append({
        "id":    state_id,
        "state": state_name,
        "title": section_title,
        "count": len(items),
    })

    new_files.add(fname)
    written   += 1
    total_jobs += len(items)
    print(f"  {state_id}: {len(items)} jobs")

# Stale files delete karo
stale = existing_files - new_files
for fname in stale:
    try:
        os.remove(os.path.join(DEST, fname))
    except Exception:
        pass

# Full index write (state-jobs-index.json) — each state's full items
with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

# Mini JSON write — sirf state list with counts (state-jobs-mini.json)
mini_data = {"sections": mini_items, "total": total_jobs}
with open(MINI_FILE, "w", encoding="utf-8") as f:
    json.dump(mini_data, f, ensure_ascii=False, separators=(",", ":"))

print(f"\nDone!")
print(f"  Written : {written} state files → {DEST}/")
print(f"  Deleted : {len(stale)} stale files")
print(f"  Total jobs: {total_jobs}")
print(f"  Index   : {INDEX_FILE}")
print(f"  Mini    : {MINI_FILE}")
