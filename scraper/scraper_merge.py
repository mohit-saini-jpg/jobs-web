# -*- coding: utf-8 -*-
# ================================================================
# SCRAPER MERGE ENGINE — scraper_merge.py
# ================================================================
# Shared module — sabhi 4 individual scrapers import karte hain.
#
# Kya karta hai:
#   1. Complete_Jobs_Full_Data.json load karo
#   2. Sirf us source ka data replace karo jo scraper ne fresh scrape kiya
#   3. Baaki teeno sources UNCHANGED rehte hain
#   4. Final merged JSON wapas save karo
#   5. Backup + sync stats bhi handle karta hai
#
# Usage (individual scraper ke end mein):
#   from scraper_merge import merge_into_json
#   merge_into_json(source="freejobalert_categories", fresh_data=scraped_dict)
#
# Sources (exact key names jo JSON mein hain):
#   "freejobalert_categories"  — scraper_fja.py
#   "sarkari_data"             — scraper_sarkari.py
#   "education_jobs"           — scraper_education.py
#   "state_jobs"               — scraper_state.py
# ================================================================

import os
import glob
import shutil
import json as _json_mod
from datetime import datetime as _dt

# ── File paths ─────────────────────────────────────────────────
FINAL_OUTPUT = "Complete_Jobs_Full_Data.json"
BACKUP_DIR   = "backups"
MAX_BACKUPS  = 3

# Source key → JSON field name mapping
SOURCE_KEYS = {
    "freejobalert_categories": "freejobalert_categories",
    "sarkari_data":            "sarkari_data",
    "education_jobs":          "education_jobs",
    "state_jobs":              "state_jobs",
    "freejobalert_unified":    "freejobalert_unified",   # NEW: deduped FJA (qual+state+district)
}

# ================================================================
# INTERNET MONITOR
# ================================================================
_NET_RETRY_INTERVAL = 30

def _is_internet_up(test_url="https://www.google.com", timeout=6):
    import requests as _req
    try:
        _req.head(test_url, timeout=timeout)
        return True
    except Exception:
        return False

def wait_for_internet(label=""):
    if _is_internet_up():
        return
    import time as _t
    tag = f"[{label}] " if label else ""
    print(f"\n  {tag}⚠️  INTERNET DISCONNECTED — scraper paused.")
    print(f"  Har {_NET_RETRY_INTERVAL}s baad check hoga. Scraper apne aap resume ho jayega.\n")
    attempt = 0
    while True:
        _t.sleep(_NET_RETRY_INTERVAL)
        attempt += 1
        if _is_internet_up():
            print(f"  {tag}✅ Internet wapas aaya (attempt #{attempt}) — resume ho raha hai...\n")
            return
        print(f"  {tag}⏳ Still offline... (check #{attempt})")


# ================================================================
# BACKUP HELPERS
# ================================================================

def _create_backup(filepath):
    if not os.path.exists(filepath):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts   = _dt.now().strftime("%Y%m%d_%H%M%S")
    name = os.path.splitext(os.path.basename(filepath))[0]
    dest = os.path.join(BACKUP_DIR, f"{name}__{ts}.json")
    shutil.copy2(filepath, dest)
    print(f"  [BACKUP] Created: {dest}")
    return dest

def _prune_backups(filepath, keep=MAX_BACKUPS):
    name    = os.path.splitext(os.path.basename(filepath))[0]
    pattern = os.path.join(BACKUP_DIR, f"{name}__*.json")
    backups = sorted(glob.glob(pattern))
    for old in backups[: max(0, len(backups) - keep)]:
        os.remove(old)
        print(f"  [BACKUP] Deleted old backup: {old}")


# ================================================================
# JOB IDENTITY — unique fingerprint
# ================================================================

def _job_key(job):
    # ================================================================
    # ROOT CAUSE FIX (Issue 1 — Duplicate Drop Bug):
    # ─────────────────────────────────────────────────────────────────
    # Pehle _job_key() official govt website URL ko unique ID maanta
    # tha. Ye WRONG tha — BEL, RITES jaise orgs 4-5 alag posts ke
    # liye SAME official career URL use karte hain. Iska result:
    # merge engine sabko "same job" samajhke drop kar deta tha.
    # (Haryana category: 24 posts => sirf 5 save hoti thi)
    #
    # FIX: `_scraped_from` (source article URL) ko Priority 0 banaya.
    # Har FJA/state article URL GLOBALLY unique hota hai — same org ke
    # alag posts alag article slugs pe published hote hain.
    # "One URL = One HTML = One Content" principle enforce hota hai.
    # ================================================================

    # ── Priority 0: _scraped_from = source article URL (MOST UNIQUE) ─
    # Har scraper (fja, state, district, education) apne items mein
    # `_scraped_from` set karta hai. Ye sabse reliable unique ID hai.
    scraped_from = job.get("_scraped_from", "")
    if isinstance(scraped_from, str) and scraped_from.strip().startswith("http"):
        key = "src::" + scraped_from.strip().rstrip("/")
        # SARKARI FIX: sarkariresultshine.com articles can legitimately be
        # listed under BOTH "LATEST_JOBS NEW" and "OFFLINE_FORM" (same source
        # site/article, two different site sections). Without this, plain
        # _scraped_from collapses them into "the same job" and one category's
        # copy gets silently dropped during merge — even though the site
        # renders both categories as separate sections that each need it.
        cat = job.get("category", "")
        if cat in ("LATEST_JOBS NEW", "OFFLINE_FORM"):
            key += "::" + cat
        return key

    # ── Priority 1: STATE-JOBS item shape (fallback for old cached data) ──
    # state_jobs items are {name, url, board, lastDate, detail:{...}}
    # Old cached state items may lack _scraped_from — handle gracefully.
    # NOTE: `url` field (official govt site) is NOT used as key here
    #       because same org shares same official URL for multiple posts.
    if ("detail" in job or "board" in job) and (job.get("name") or job.get("url")):
        name  = str(job.get("name", "")).strip()
        board = str(job.get("board", "")).strip()
        ld    = str(job.get("lastDate", "") or job.get("postDate", "")).strip()
        if name and board:
            return f"state::{name}::{board}::{ld}"
        if name:
            return f"state::{name}::{ld}"

    # ── Priority 2: Notification number + org (structured data) ──────
    bd = job.get("basic_details", {})
    notif = (bd.get("notification_number") or bd.get("notification_no")
             or bd.get("advt_no") or "")
    org   = (bd.get("organization_name") or bd.get("organization")
             or bd.get("department") or "").strip()
    if notif and str(notif).strip():
        return f"notif::{str(notif).strip()}::{org}"

    # ── Priority 3: title + org + vacancies ───────────────────────────
    title = (bd.get("job_title") or bd.get("post_name")
             or bd.get("title") or job.get("title", "")).strip()
    vac   = str(bd.get("total_vacancies") or "").strip()
    if title and org:
        return f"title::{title}::{org}::{vac}"
    if title:
        return f"title::{title}::{vac}"

    # ── Priority 4: Last resort — important_links URL fields ──────────
    # ONLY used when _scraped_from absent AND no structured fields exist.
    # Moved to LAST to avoid false-duplicate drops on shared org URLs.
    links = job.get("important_links", {})
    for field in ("apply_online", "official_notification",
                  "download_notification", "apply_link", "notification_pdf"):
        val = links.get(field, "")
        if isinstance(val, str) and val.strip().startswith("http"):
            return "link::" + val.strip().rstrip("/")
    for field in ("apply_link", "official_link", "notification_link"):
        val = bd.get(field, "")
        if isinstance(val, str) and val.strip().startswith("http"):
            return "link::" + val.strip().rstrip("/")

    return None

# ================================================================
# SYNC ENGINES
# ================================================================

def _sync_fja_categories(old_data, new_data):
    synced = {}
    total_stats = {"added": 0, "removed": 0, "unchanged": 0}

    all_cats = list(new_data.keys())
    for cat in old_data:
        if cat not in all_cats:
            all_cats.append(cat)

    for cat in all_cats:
        new_jobs = new_data.get(cat, [])
        old_jobs = old_data.get(cat, [])

        new_key_map = {_job_key(j): j for j in new_jobs if _job_key(j)}
        old_key_map = {_job_key(j): j for j in old_jobs if _job_key(j)}

        result_jobs = []
        seen_keys = set()
        added = removed = unchanged = 0

        for job in new_jobs:
            k = _job_key(job)
            if k:
                # ── FIX (Issue 1 + Issue 3): Same-run duplicate check SIRF
                # URL-keyed items par karo. k = None wale items KABHI drop
                # mat karo — agar kisi item ka _job_key() None return karta
                # hai (old cached item jisme _scraped_from absent hai), use
                # unconditionally include karo. Ye "One URL = One HTML" rule
                # enforce karta hai bina valid items ko silently drop kiye.
                if k in seen_keys:
                    continue          # same-run duplicate (same URL) — skip
                seen_keys.add(k)
                if k not in old_key_map:
                    added += 1
                else:
                    unchanged += 1
            # k == None: no reliable key — include unconditionally (no dedup possible)
            result_jobs.append(job)

        for k in old_key_map:
            if k not in new_key_map:
                removed += 1

        if added or removed:
            print(f"    [{cat}] +{added} new | -{removed} removed | {unchanged} unchanged")

        total_stats["added"]     += added
        total_stats["removed"]   += removed
        total_stats["unchanged"] += unchanged

        # result_jobs = fresh scraped jobs in website sequence order — old fully replaced
        if result_jobs:
            synced[cat] = result_jobs
        elif cat in old_data and not new_jobs:
            print(f"    [{cat}] Category site se hat gayi — removing from JSON")

    return synced, total_stats


def _sync_unified_fja(old_data, new_data):
    """Sync the deduped unified FJA payload.

    Payload shape:
      { "deduped_jobs": [...], "meta": {...},
        "by_fja_category": {...}, "by_state": {...}, "by_district": {...} }

    Dedup key = job["_scraped_from"] (normalized detail URL). Fresh scrape wins
    for any URL it covers; old jobs whose URL is absent from the fresh run are
    dropped (they're no longer live). The index blocks are taken from the fresh
    payload as-is (the scraper rebuilds them from the merged job set).

    FJA TITLE DEDUP (same-job multiple-article-URL fix):
    FJA publishes multiple /articles/ URLs for the same vacancy (update/reminder/
    correction notices). scraper_unified_fja.py already dedupes these at Phase 2
    (merge_url_maps) and Phase 3b (title_dedup_merge). However the MERGE ENGINE
    (this function) receives the final all_jobs list from the scraper which already
    has title dedup applied — so we just do a safety pass here too using the same
    title-slug strip logic to catch anything the scraper missed.
    """
    import re as _re_merge

    def _title_slug_merge(url: str) -> str:
        from urllib.parse import urlparse as _up
        p = _up(url)
        if "/articles/" not in p.path:
            return ""
        seg = p.path.rstrip("/").rsplit("/", 1)[-1]
        return _re_merge.sub(r'-\d{5,}$', '', seg).strip("-").lower()

    def _job_title_key_merge(job: dict) -> str:
        bd = job.get("basic_details") or {}
        title = (bd.get("job_title") or "").strip().lower()
        if not title:
            title = (job.get("title") or "").strip().lower()
        return _re_merge.sub(r'\s+', ' ', title)

    def _article_id_merge(j):
        m = _re_merge.search(r'-(\d+)$', (j.get("_scraped_from") or "").rstrip("/"))
        return int(m.group(1)) if m else 0

    def _title_dedup(jobs):
        """Dedup by title AND track every URL that got discarded/renamed in the
        process, so the caller can fix up stale references in the by_fja_category
        / by_state / by_district index lists (ROOT CAUSE of the "category order
        mix / wrong item" bug — see url_remap usage below).

        FALSE-POSITIVE GUARD: some organizations reuse the exact same generic/
        templated job_title for genuinely different postings at different
        locations (e.g. a Delhi-only walk-in and a separate Tamil-Nadu-only
        walk-in both titled "X Technical Fellow Recruitment 2026 - Walkin").
        If both candidates already carry their own non-empty state/district
        tags and those tags don't overlap at all, treat them as different real
        postings and keep them separate — don't merge, don't union tags (this
        is what was causing a Chennai-only posting to inherit a Delhi tag)."""
        seen = {}
        result = []
        url_remap = {}   # old _scraped_from url -> final canonical url it now lives at
        for job in jobs:
            tkey = _job_title_key_merge(job)
            if not tkey:
                result.append(job); continue
            if tkey not in seen:
                seen[tkey] = len(result)
                result.append(job)
            else:
                kept = result[seen[tkey]]

                kept_loc = set(kept.get("state_tags", []) or []) | set(kept.get("inferred_states", []) or [])
                dup_loc  = set(job.get("state_tags", []) or [])  | set(job.get("inferred_states", []) or [])
                kept_dist = set(kept.get("district_tags", []) or [])
                dup_dist  = set(job.get("district_tags", []) or [])
                disjoint_location = (
                    (kept_loc and dup_loc and not (kept_loc & dup_loc)) or
                    (kept_dist and dup_dist and not (kept_dist & dup_dist))
                )
                if disjoint_location:
                    result.append(job)
                    continue

                dup_url      = job.get("_scraped_from")
                old_kept_url = kept.get("_scraped_from")
                for field in ("fja_categories", "state_tags", "district_tags", "inferred_states"):
                    merged_vals = sorted(set(kept.get(field, []) + job.get(field, [])))
                    kept[field] = merged_vals
                if not kept.get("slug") and job.get("slug"):
                    kept["slug"] = job["slug"]
                if _article_id_merge(job) > _article_id_merge(kept):
                    kept["_scraped_from"] = job["_scraped_from"]
                    # canonical URL just moved — anything that pointed at the OLD
                    # kept-url must now be remapped to the new one too.
                    if old_kept_url and old_kept_url != kept["_scraped_from"]:
                        url_remap[old_kept_url] = kept["_scraped_from"]
                # the duplicate's own url is being discarded regardless of which
                # side "won" — point it at wherever the kept record ended up.
                if dup_url and dup_url != kept["_scraped_from"]:
                    url_remap[dup_url] = kept["_scraped_from"]

        # collapse remap chains (a -> b -> c, from multiple merges of the same
        # title) so every stale url points straight at its FINAL destination.
        for u in list(url_remap.keys()):
            target = url_remap[u]
            chain_seen = {u}
            while target in url_remap and target not in chain_seen:
                chain_seen.add(target)
                target = url_remap[target]
            url_remap[u] = target

        return result, url_remap

    stats = {"added": 0, "removed": 0, "unchanged": 0}
    old_jobs = old_data.get("deduped_jobs", []) if isinstance(old_data, dict) else []
    new_jobs = new_data.get("deduped_jobs", []) if isinstance(new_data, dict) else []

    # If the fresh run produced nothing, keep old data untouched (safety).
    if not new_jobs:
        print("    [unified] fresh run empty — keeping existing unified data")
        return (old_data or {}), stats

    # Apply title dedup to the incoming fresh payload (safety — scraper should
    # have already done this, but belt-and-suspenders costs nothing here).
    new_jobs, url_remap = _title_dedup(new_jobs)

    old_by_url = {j.get("_scraped_from"): j for j in old_jobs if j.get("_scraped_from")}
    new_by_url = {j.get("_scraped_from"): j for j in new_jobs if j.get("_scraped_from")}

    for url in new_by_url:
        if url in old_by_url:
            stats["unchanged"] += 1
        else:
            stats["added"] += 1
    for url in old_by_url:
        if url not in new_by_url:
            stats["removed"] += 1

    print(f"    [unified] +{stats['added']} new | -{stats['removed']} removed "
          f"| {stats['unchanged']} unchanged")

    # ── STALE INDEX-URL FIX ────────────────────────────────────
    # ROOT BUG: this function's own _title_dedup pass (above) can rename or
    # discard a job's `_scraped_from` (when it merges a duplicate title into an
    # existing kept record). by_fja_category / by_state / by_district were
    # built by the SCRAPER before this pass ran, so they can still list the OLD
    # url — a url that no longer exists as a key in deduped_jobs. On the site,
    # that slot fails to resolve and the category/state/district page shows a
    # missing/wrong item with everything after it shifted — this is exactly the
    # "order mix" symptom.
    #
    # FIX: remap every stale url in the three index dicts to its final
    # canonical url (from url_remap), de-duping any resulting collisions while
    # preserving the existing listing-page order.
    def _remap_index(idx):
        if not isinstance(idx, dict):
            return idx
        fixed = {}
        for tag, urls in idx.items():
            new_list = []
            seen_u = set()
            for u in (urls or []):
                u2 = url_remap.get(u, u)
                if u2 not in seen_u:
                    new_list.append(u2)
                    seen_u.add(u2)
            fixed[tag] = new_list
        return fixed

    by_fja_fixed   = _remap_index(new_data.get("by_fja_category", {}))
    by_state_fixed = _remap_index(new_data.get("by_state", {}))
    by_dist_fixed  = _remap_index(new_data.get("by_district", {}))

    if url_remap:
        print(f"    [unified] {len(url_remap)} stale index url(s) remapped "
              f"after merge-level title dedup")
    # ── END STALE INDEX-URL FIX ─────────────────────────────────

    # Fresh payload is authoritative (it already merged resume data internally).
    synced = {
        "deduped_jobs":    new_jobs,
        "meta":            new_data.get("meta", {}),
        "by_fja_category": by_fja_fixed,
        "by_state":        by_state_fixed,
        "by_district":     by_dist_fixed,
    }
    return synced, stats


def _sync_sections(old_data, new_data, label):
    if not isinstance(new_data, dict) or "sections" not in new_data:
        return new_data, {"added": 0, "removed": 0, "unchanged": 0}

    old_sections_map = {}
    for sec in (old_data.get("sections", []) if isinstance(old_data, dict) else []):
        old_sections_map[sec.get("id", "")] = sec

    total_stats = {"added": 0, "removed": 0, "unchanged": 0}
    synced_sections = []

    for new_sec in new_data["sections"]:
        sec_id    = new_sec.get("id", "")
        old_sec   = old_sections_map.get(sec_id, {})
        new_items = new_sec.get("items", [])
        old_items = old_sec.get("items", [])

        new_key_map = {_job_key(i): i for i in new_items if _job_key(i)}
        old_key_map = {_job_key(i): i for i in old_items if _job_key(i)}

        result_items = []
        seen_keys = set()
        added = removed = unchanged = 0

        for item in new_items:
            k = _job_key(item)
            if k:
                # FIX: None-key items kabhi drop nahi — sirf URL-keyed same-run
                # duplicates skip karo. Website row count = JSON item count.
                if k in seen_keys:
                    continue          # same-run duplicate (same URL) — skip
                seen_keys.add(k)
                if k not in old_key_map:
                    added += 1
                else:
                    unchanged += 1
            # k == None: unconditionally include
            result_items.append(item)

        for k in old_key_map:
            if k not in new_key_map:
                removed += 1

        if added or removed:
            print(f"    [{label} / {new_sec.get('title', sec_id)}] +{added} new | -{removed} removed | {unchanged} unchanged")

        total_stats["added"]     += added
        total_stats["removed"]   += removed
        total_stats["unchanged"] += unchanged

        synced_sec = dict(new_sec)
        synced_sec["items"] = result_items
        synced_sections.append(synced_sec)

    synced_data = dict(new_data)
    synced_data["sections"] = synced_sections
    return synced_data, total_stats


def _sync_sarkari(old_data, new_data):
    if not isinstance(new_data, dict):
        return new_data, {"added": 0, "removed": 0, "unchanged": 0}

    if "sections" in new_data:
        return _sync_sections(old_data, new_data, "Sarkari")

    total_stats = {"added": 0, "removed": 0, "unchanged": 0}
    synced = dict(new_data)

    for key, val in new_data.items():
        if isinstance(val, list) and val and isinstance(val[0], dict):
            old_list    = old_data.get(key, []) if isinstance(old_data, dict) else []
            new_key_map = {_job_key(i): i for i in val if _job_key(i)}
            old_key_map = {_job_key(i): i for i in old_list if _job_key(i)}

            result = []
            seen_keys = set()
            added = removed = unchanged = 0

            for item in val:
                k = _job_key(item)
                if k:
                    # FIX: None-key items kabhi drop nahi — sirf URL-keyed duplicates skip
                    if k in seen_keys:
                        continue      # same-run duplicate (same URL) — skip
                    seen_keys.add(k)
                    if k not in old_key_map:
                        added += 1
                    else:
                        unchanged += 1
                # k == None: unconditionally include
                result.append(item)

            for k in old_key_map:
                if k not in new_key_map:
                    removed += 1

            if added or removed:
                print(f"    [Sarkari / {key}] +{added} new | -{removed} removed | {unchanged} unchanged")

            total_stats["added"]     += added
            total_stats["removed"]   += removed
            total_stats["unchanged"] += unchanged
            synced[key] = result

    return synced, total_stats


# ================================================================
# AWS KEY STRIPPER
# ================================================================

def _strip_aws_keys(obj):
    import re as _re
    AWS_KEY_PATTERN = _re.compile(r'AKIA[0-9A-Z]{16}')
    if isinstance(obj, dict):
        return {k: _strip_aws_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_aws_keys(i) for i in obj]
    if isinstance(obj, str):
        return AWS_KEY_PATTERN.sub("[REDACTED]", obj)
    return obj


# ================================================================
# COUNT HELPERS
# ================================================================

def _count_fja(data):
    if not isinstance(data, dict): return 0
    return sum(len(v) for v in data.values() if isinstance(v, list))

def _count_sections(data):
    if not isinstance(data, dict): return 0
    return sum(len(s.get("items", [])) for s in data.get("sections", []))

def _count_sarkari(data):
    # NOTE: always count the actual list contents, never trust a "total" key
    # carried over from the pre-sync input dict — after _sync_sarkari() runs,
    # that stale field can disagree with the real (deduped) "jobs" list
    # length, which made the merge summary print a misleading count.
    if isinstance(data, dict):
        return sum(len(v) for v in data.values() if isinstance(v, list))
    return 0


# ================================================================
# CORE: merge_into_json — ek source ka data update karo
# ================================================================

def merge_into_json(source: str, fresh_data: dict, scraper_error: str = ""):
    """
    Sirf ek source ka data update karo Complete_Jobs_Full_Data.json mein.
    Baaki teeno sources BILKUL UNTOUCHED rehte hain.

    Args:
        source        : source key — "freejobalert_categories" | "sarkari_data"
                        | "education_jobs" | "state_jobs"
        fresh_data    : us source ka naya scraped data (same format as JSON mein stored)
        scraper_error : agar scraper crash hua toh error string (optional)
    """
    if source not in SOURCE_KEYS:
        raise ValueError(f"Unknown source: '{source}'. Valid: {list(SOURCE_KEYS.keys())}")

    print(f"\n{'='*60}")
    print(f"  MERGE ENGINE — updating: {source}")
    print(f"{'='*60}")

    # ── Step 1: Existing JSON load karo ───────────────────────
    if os.path.exists(FINAL_OUTPUT):
        print(f"  [LOAD] Existing JSON load ho raha hai...")
        with open(FINAL_OUTPUT, encoding="utf-8") as f:
            existing = _json_mod.load(f)
        is_first = False
        _create_backup(FINAL_OUTPUT)
        _prune_backups(FINAL_OUTPUT, keep=MAX_BACKUPS)
    else:
        print(f"  [INIT] Pehli run — naya JSON banega.")
        existing  = {}
        is_first  = True

    # ── Step 2: Existing sections extract karo ────────────────
    old_fja     = existing.get("freejobalert_categories", {})
    old_sarkari = existing.get("sarkari_data", {})
    old_edu     = existing.get("education_jobs", {})
    old_state   = existing.get("state_jobs", {})
    old_unified = existing.get("freejobalert_unified", {})   # NEW: deduped FJA
    old_errors  = existing.get("scraper_errors", {})
    old_sync    = existing.get("sync_stats", {})

    # ── Step 3: Sirf is source ka data sync karo ──────────────
    stats = {"added": 0, "removed": 0, "unchanged": 0}

    # Default: every source preserves the unified payload untouched. Only the
    # "freejobalert_unified" branch below overwrites it. This keeps the new key
    # safe no matter which scraper triggers the merge.
    synced_unified = old_unified

    if source == "freejobalert_categories":
        if is_first:
            synced_fja = fresh_data
        else:
            print(f"  [SYNC] FreeJobAlert Categories syncing...")
            synced_fja, stats = _sync_fja_categories(old_fja, fresh_data)
        # Baaki unchanged
        synced_sarkari = old_sarkari
        synced_edu     = old_edu
        synced_state   = old_state

    elif source == "sarkari_data":
        if is_first:
            synced_sarkari = fresh_data
        else:
            print(f"  [SYNC] Sarkari data syncing...")
            synced_sarkari, stats = _sync_sarkari(old_sarkari, fresh_data)
        synced_fja   = old_fja
        synced_edu   = old_edu
        synced_state = old_state

    elif source == "education_jobs":
        if is_first:
            synced_edu = fresh_data
        else:
            print(f"  [SYNC] Education Jobs syncing...")
            synced_edu, stats = _sync_sections(old_edu, fresh_data, "Education")
        synced_fja     = old_fja
        synced_sarkari = old_sarkari
        synced_state   = old_state

    elif source == "state_jobs":
        if is_first:
            synced_state = fresh_data
        else:
            print(f"  [SYNC] State Jobs syncing...")
            synced_state, stats = _sync_sections(old_state, fresh_data, "State")
        synced_fja     = old_fja
        synced_sarkari = old_sarkari
        synced_edu     = old_edu

    elif source == "freejobalert_unified":
        if is_first:
            synced_unified = fresh_data
        else:
            print(f"  [SYNC] Unified FJA (deduped) syncing...")
            synced_unified, stats = _sync_unified_fja(old_unified, fresh_data)
        # All legacy sources untouched
        synced_fja     = old_fja
        synced_sarkari = old_sarkari
        synced_edu     = old_edu
        synced_state   = old_state

    # ── Step 4: Counts ────────────────────────────────────────
    cnt_fja     = _count_fja(synced_fja)
    cnt_sarkari = _count_sarkari(synced_sarkari)
    cnt_edu     = _count_sections(synced_edu)
    cnt_state   = _count_sections(synced_state)
    cnt_unified = len(synced_unified.get("deduped_jobs", [])) if isinstance(synced_unified, dict) else 0

    # ── Step 5: Errors update ─────────────────────────────────
    new_errors = dict(old_errors)
    if scraper_error:
        new_errors[source] = scraper_error
    elif source in new_errors:
        del new_errors[source]   # pichli error clear karo

    # ── Step 6: Cumulative sync stats ────────────────────────
    prev_added     = old_sync.get("added",     0) if not is_first else 0
    prev_removed   = old_sync.get("removed",   0) if not is_first else 0
    prev_unchanged = old_sync.get("unchanged", 0) if not is_first else 0

    merged = {
        "generated_at": _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": {
            "freejobalert_categories": cnt_fja,
            "sarkari_data":            cnt_sarkari,
            "education_jobs":          cnt_edu,
            "state_jobs":              cnt_state,
            "freejobalert_unified":    cnt_unified,
        },
        "total_records":           cnt_fja + cnt_sarkari + cnt_edu + cnt_state,
        "freejobalert_categories": synced_fja,
        "sarkari_data":            synced_sarkari,
        "education_jobs":          synced_edu,
        "state_jobs":              synced_state,
        "freejobalert_unified":    synced_unified,
        "scraper_errors":          new_errors,
        "sync_stats": {
            "run_type":       "first_run" if is_first else "incremental",
            "last_updated":   source,
            "added":          stats["added"],
            "removed":        stats["removed"],
            "unchanged":      stats["unchanged"],
            "synced_at":      _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

    # ── Step 7: AWS key strip + write ────────────────────────
    merged = _strip_aws_keys(merged)
    with open(FINAL_OUTPUT, "w", encoding="utf-8") as f:
        _json_mod.dump(merged, f, ensure_ascii=False, indent=2)

    # ── Step 8: Summary ──────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  MERGE COMPLETE — {source}")
    print(f"  Run Type       : {'FIRST RUN' if is_first else 'INCREMENTAL UPDATE'}")
    print(f"  Updated source : {source}")
    print(f"  TOTAL RECORDS  : {merged['total_records']}")
    for src, cnt in merged["sources"].items():
        marker = " ◄ UPDATED" if src == source else ""
        print(f"    {src:35s}: {cnt}{marker}")
    if not is_first:
        print(f"\n  SYNC ({source}):")
        print(f"    ✅ New added    : {stats['added']}")
        print(f"    ❌ Removed      : {stats['removed']}")
        print(f"    ⏸  Unchanged    : {stats['unchanged']}")
    if new_errors:
        print(f"\n  ERRORS: {list(new_errors.keys())}")
    print(f"\n  OUTPUT FILE    : {FINAL_OUTPUT}")

    backup_files = sorted(glob.glob(os.path.join(BACKUP_DIR, "Complete_Jobs_Full_Data__*.json")))
    if backup_files:
        print(f"  BACKUPS ({len(backup_files)}/{MAX_BACKUPS}) :")
        for b in backup_files:
            size_mb = os.path.getsize(b) / (1024 * 1024)
            print(f"    {b}  ({size_mb:.1f} MB)")
    print(f"{'='*60}")

    return merged
