#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_search_index.py -- compile a small, disk-truth search index for the
homepage hero search, replacing its reliance on Complete_Jobs_Full_Data.json
(26MB raw / 5MB+ gzipped) for the common case of searching a job by title.

WHY THIS EXISTS
---------------
The hero search (smart-search.js) only shows real job results after
downloading and parsing the entire 26MB job data file -- deliberately
deferred until the user has typed 2+ characters, so the first couple of
keystrokes show nothing while that file is still loading. It also resolves
each result's URL client-side by GUESSING a slug from the title (its own
canonical_slug field, else a slugified title, else a fuzzy normalized-title
lookup) -- a chain that can point a correctly-titled result at the WRONG
job page if that guess collides with a different job (e.g. a stale-cached
jobs-index.json, or a source record with no canonical_slug at all).

This script builds search-index.json directly from jobs-index.json (which
IS disk truth -- every key is a slug that was verified to have a real
jobs/<slug>/index.html when generate_all.py wrote it), enriched with the
organization name from jobs/data/<slug>.json where available. Every entry's
slug is therefore already guaranteed-correct: the browser needs zero
guessing to build a URL from it. Small enough (~1-2MB) to load immediately
alongside dailyupdates.json instead of being gated behind typing.

Run after generate_all.py (needs the jobs-index.json it just wrote):
    python3 build_search_index.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import heal_jobposting_schema as H

JOBS_INDEX_PATH = os.path.join(ROOT, "jobs-index.json")
OUT_PATH = os.path.join(ROOT, "search-index.json")


def main():
    with open(JOBS_INDEX_PATH, encoding="utf-8") as f:
        jobs_index = json.load(f)

    src_idx = H.build_source_index()
    src_keys = list(src_idx.keys())

    out = {}
    enriched = 0
    for slug, meta in jobs_index.items():
        title = str(meta.get("title") or "").strip()
        if not title:
            continue
        org = ""
        rec = H.find_source(slug, src_idx, src_keys)
        if rec:
            org = str((rec.get("basic_details") or {}).get("organization_name") or "").strip()[:80]
            if org:
                enriched += 1
        entry = {"t": title, "c": str(meta.get("cat") or "")[:40]}
        if meta.get("last_date"):
            entry["d"] = str(meta["last_date"])[:30]
        if org:
            entry["o"] = org
        out[slug] = entry

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"[search-index] wrote {len(out)} entries ({enriched} with organization) "
          f"-> search-index.json ({size_kb:.0f} KB)")


if __name__ == "__main__":
    sys.exit(main())
