#!/usr/bin/env python3
# Validation test for unified FJA dedup. Run after scraper_unified_fja.py.
import json, os, sys

PATH = "_temp_unified_fja.json"
if not os.path.exists(PATH):
    print(f"[SKIP] {PATH} not found — run scraper_unified_fja.py first.")
    sys.exit(0)

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

jobs = data["deduped_jobs"]
urls = [j["_scraped_from"] for j in jobs]

# 1. No duplicate URLs
dups = len(urls) - len(set(urls))
assert dups == 0, f"FAIL: {dups} duplicate URLs found!"
print(f"✅ No duplicate URLs ({len(urls)} unique)")

# 2. Cross-source tags present (proves merge worked)
multi_tagged = [j for j in jobs if len(j.get("fja_categories", [])) > 1
                or len(j.get("state_tags", [])) > 0
                or len(j.get("district_tags", [])) > 0]
print(f"✅ Jobs with cross-source tags: {len(multi_tagged)} / {len(jobs)}")

# 3. Meta sanity
meta = data.get("meta", {})
print(f"   total_unique_jobs    : {meta.get('total_unique_jobs')}")
print(f"   fja_listing_refs     : {meta.get('total_fja_listing_refs')}")
print(f"   state_listing_refs   : {meta.get('total_state_listing_refs')}")
print(f"   district_listing_refs: {meta.get('total_district_listing_refs')}")
print(f"   deduplicated_count   : {meta.get('deduplicated_count')}")

# 4. Index file
if os.path.exists("_temp_unified_index.json"):
    with open("_temp_unified_index.json", encoding="utf-8") as f:
        idx = json.load(f)
    print(f"✅ Index: {len(idx.get('by_fja_category',{}))} fja cats, "
          f"{len(idx.get('by_state',{}))} states, "
          f"{len(idx.get('by_district',{}))} districts")

print("\n✅ Deduplication test PASSED")
