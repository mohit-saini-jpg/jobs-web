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
    # ── Priority 0: STATE-JOBS item shape ─────────────────────
    # state_jobs items are {name, url, board, lastDate, detail:{...}} — the
    # real basic_details/important_links sit INSIDE `detail`, not at top level.
    # Without this branch _job_key returned None for every state job, so the
    # merge could not match fresh vs old items (stale data survived).
    if ("detail" in job or "board" in job) and (job.get("name") or job.get("url")):
        # 0a: official URL is the most unique signal
        url = job.get("url", "")
        if isinstance(url, str) and url.strip().startswith("http"):
            return "state::" + url.strip().rstrip("/")
        # 0b: name + board (+ lastDate to disambiguate re-runs of same post)
        name  = str(job.get("name", "")).strip()
        board = str(job.get("board", "")).strip()
        ld    = str(job.get("lastDate", "") or job.get("postDate", "")).strip()
        if name and board:
            return f"state::{name}::{board}::{ld}"
        if name:
            return f"state::{name}::{ld}"

    # ── Priority 1: apply_online / notification_pdf URL (sabse unique) ─
    links = job.get("important_links", {})
    for field in ("apply_online", "official_notification", "official_website",
                  "download_notification", "apply_link", "official_link",
                  "notification_pdf"):
        val = links.get(field, "")
        if isinstance(val, str) and val.strip().startswith("http"):
            return val.strip().rstrip("/")

    # ── Priority 2: basic_details URL fields ──────────────────
    bd = job.get("basic_details", {})
    for field in ("apply_link", "official_link", "notification_link", "official_website"):
        val = bd.get(field, "")
        if isinstance(val, str) and val.strip().startswith("http"):
            return val.strip().rstrip("/")

    # ── Priority 3: Notification number + org ─────────────────
    notif = (bd.get("notification_number") or bd.get("notification_no")
             or bd.get("advt_no") or "")
    org   = (bd.get("organization_name") or bd.get("organization")
             or bd.get("department") or "").strip()
    if notif and str(notif).strip():
        return f"notif::{str(notif).strip()}::{org}"

    # ── Priority 4: title + org + vacancies (same-title jobs differentiate) ─
    title = (bd.get("job_title") or bd.get("post_name")
             or bd.get("title") or job.get("title", "")).strip()
    vac   = str(bd.get("total_vacancies") or "").strip()
    if title and org:
        return f"title::{title}::{org}::{vac}"
    if title:
        return f"title::{title}::{vac}"

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
                if k in seen_keys:
                    continue          # same-run duplicate skip karo
                seen_keys.add(k)
                if k not in old_key_map:
                    added += 1
                else:
                    unchanged += 1
            result_jobs.append(job)

        for k in old_key_map:
            if k not in new_key_map:
                removed += 1

        if added or removed:
            print(f"    [{cat}] +{added} new | -{removed} removed | {unchanged} unchanged")

        total_stats["added"]     += added
        total_stats["removed"]   += removed
        total_stats["unchanged"] += unchanged

        # result_jobs = only fresh scraped jobs — old data fully replaced
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
    """
    stats = {"added": 0, "removed": 0, "unchanged": 0}
    old_jobs = old_data.get("deduped_jobs", []) if isinstance(old_data, dict) else []
    new_jobs = new_data.get("deduped_jobs", []) if isinstance(new_data, dict) else []

    # If the fresh run produced nothing, keep old data untouched (safety).
    if not new_jobs:
        print("    [unified] fresh run empty — keeping existing unified data")
        return (old_data or {}), stats

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

    # Fresh payload is authoritative (it already merged resume data internally).
    synced = {
        "deduped_jobs":    new_jobs,
        "meta":            new_data.get("meta", {}),
        "by_fja_category": new_data.get("by_fja_category", {}),
        "by_state":        new_data.get("by_state", {}),
        "by_district":     new_data.get("by_district", {}),
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
                if k in seen_keys:
                    continue          # same-run duplicate skip karo
                seen_keys.add(k)
                if k not in old_key_map:
                    added += 1
                else:
                    unchanged += 1
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
                    if k in seen_keys:
                        continue      # same-run duplicate skip karo
                    seen_keys.add(k)
                    if k not in old_key_map:
                        added += 1
                    else:
                        unchanged += 1
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
    if isinstance(data, dict):
        if "total" in data:
            return data["total"]
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
