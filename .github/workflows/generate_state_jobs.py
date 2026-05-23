"""
generate_state_jobs.py — state-jobs-data.json ko per-state files mein split karta hai
========================================================================================
Output:
  state/data/<state-id>.json       — state-jobs.html ke liye (direct fetch path)
  state/<state-id>/data/<id>.json  — GitHub folder structure ke andar bhi
  state-jobs-mini.json             — 3KB lightweight list
  state-jobs-index.json            — full index
"""

import json, os

SRC        = "state-jobs-data.json"
DEST       = "state/data"
INDEX_FILE = "state-jobs-index.json"
MINI_FILE  = "state-jobs-mini.json"

print(f"Loading {SRC}...")
with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

sections = data.get("sections", [])
if not isinstance(sections, list):
    print("ERROR: 'sections' array not found")
    exit(1)

print(f"Total sections: {len(sections)}")
os.makedirs(DEST, exist_ok=True)
existing_files = set(os.listdir(DEST))

index      = {}
mini_items = []
new_files  = set()
written    = 0
total_jobs = 0

for section in sections:
    state_id      = (section.get("id", "") or "").strip()
    state_name    = (section.get("state", "") or "").strip()
    section_title = (section.get("title", "") or state_name).strip()
    items         = section.get("items", []) or []

    if not state_id or not state_name:
        continue

    fname      = f"{state_id}.json"
    state_data = {
        "id":    state_id,
        "state": state_name,
        "title": section_title,
        "items": items,
    }
    json_bytes = json.dumps(state_data, ensure_ascii=False, separators=(",", ":"))

    # Path 1: state/data/<id>.json  (state-jobs.html fetch karta hai)
    with open(os.path.join(DEST, fname), "w", encoding="utf-8") as f:
        f.write(json_bytes)

    # Path 2: state/<id>/data/<id>.json  (GitHub folder structure)
    sub_data_dir = os.path.join("state", state_id, "data")
    os.makedirs(sub_data_dir, exist_ok=True)
    with open(os.path.join(sub_data_dir, fname), "w", encoding="utf-8") as f:
        f.write(json_bytes)

    print(f"  {state_id}: {len(items)} jobs → state/data/ + state/{state_id}/data/")

    index[state_id] = {
        "state": state_name,
        "title": section_title,
        "count": len(items),
        "items": items,
    }
    mini_items.append({
        "id":    state_id,
        "state": state_name,
        "title": section_title,
        "count": len(items),
    })
    new_files.add(fname)
    written   += 1
    total_jobs += len(items)

# Stale cleanup
stale = existing_files - new_files
for fname in stale:
    try:
        os.remove(os.path.join(DEST, fname))
    except Exception:
        pass

with open(INDEX_FILE, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

mini_data = {"sections": mini_items, "total": total_jobs}
with open(MINI_FILE, "w", encoding="utf-8") as f:
    json.dump(mini_data, f, ensure_ascii=False, separators=(",", ":"))

print(f"\nDone!")
print(f"  Written : {written} state files")
print(f"  Deleted : {len(stale)} stale files")
print(f"  Total jobs: {total_jobs}")
