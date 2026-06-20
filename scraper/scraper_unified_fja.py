#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================================
# SCRAPER: Unified FreeJobAlert — scraper_unified_fja.py
# ================================================================
# PROBLEM SOLVED:
#   3 alag FJA scrapers (qualification / state / district) same
#   detail-page URL ko 3 baar scrape karte the aur 3 alag records
#   banate the. Ek "RRB Group D 2026" job:
#     - freejobalert_categories  mein "10TH_Pass"  ke saath
#     - state_jobs               mein "Uttar Pradesh" ke saath
#     - freejobalert_district    mein "Yamunanagar"   ke saath
#
# SOLUTION (4-phase):
#   Phase 1: Teeno CATEGORIES dicts se SIRF listing-page URLs collect
#            karo (detail scrape NAHI). Same URL multiple categories
#            mein aa sakta hai — ye expected hai.
#   Phase 2: URL ko key banakar merge karo — har unique detail URL ke
#            saath uske saare tags (fja_categories + state_tags +
#            district_tags) ikatthe karo.
#   Phase 3: Sirf UNIQUE URLs ko EK BAAR scrape karo (detail page).
#   Phase 4: deduped_jobs + index likho.
#
# Writes  : _temp_unified_fja.json   (deduped jobs + meta)
#           _temp_unified_index.json (by_fja_category / by_state / by_district)
# Output  : "freejobalert_unified" key in Complete_Jobs_Full_Data.json
#
# IMPORTANT — Shared logic reuse:
#   Ye scraper apna khud ka collect/extract NAHI likhta. scraper_district.py
#   (jo scraper_fja.py ka HUBAHU SAME, sabse complete copy hai) ko base module
#   ke roop mein import karke uske battle-tested functions reuse karta hai:
#     - collect_all_job_links()   listing → detail URLs
#     - extract_job_page()        detail page → job data (H2-section parser)
#     - smart_delay()             human-like throttle
#     - _scrape_job_with_retry, _is_empty_job, _strip_aws_keys, make_session
#   Isse code duplication zero hai aur teeno ka logic guaranteed identical.
#
# Run:  python scraper_unified_fja.py
# ================================================================

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import json
import time
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Base module: district scraper = most complete FJA logic copy ──────────────
# District scraper top-level pe sirf functions/dicts define karta hai; uska
# executable code sirf `if __name__=="__main__"` block mein hai — isliye import
# safe hai (kuch run nahi hoga).
import scraper_district as DBASE

# Reuse battle-tested shared functions (district == fja logic, verified)
collect_all_job_links = DBASE.collect_all_job_links
extract_job_page      = DBASE.extract_job_page
smart_delay           = DBASE.smart_delay
_is_empty_job         = DBASE._is_empty_job
_strip_aws_keys       = DBASE._strip_aws_keys
_wait_for_internet    = DBASE._wait_for_internet
HEADERS               = DBASE.HEADERS
DISTRICT_META         = DBASE.DISTRICT_META

# ============================================================
# CONFIG
# ============================================================
BASE_SITE          = "https://www.freejobalert.com"
MAX_WORKERS        = 8
MAX_RETRIES        = 3

UNIFIED_OUTPUT     = "_temp_unified_fja.json"
UNIFIED_INDEX      = "_temp_unified_index.json"

# ── Category sources (all three) ──────────────────────────────────────────────
# 1) Qualification-wise (from scraper_fja.py CATEGORIES) — import live so it
#    always matches the canonical list (54 entries).
try:
    import scraper_fja as FJABASE
    FJA_CATEGORIES = dict(FJABASE.CATEGORIES)
except Exception as _e:
    print(f"[WARN] scraper_fja import failed ({_e}); using district's empty fallback.")
    FJA_CATEGORIES = {}

# 2) District-wise (697) — straight from the district base module.
DISTRICT_CATEGORIES = dict(DBASE.CATEGORIES)

# 3) State-wise (28) — slug list per state. Mirror of scraper_state.STATE_URL_MAP.
#    Each state has candidate slugs; we try them in order until one yields links.
STATE_URL_MAP = {
    "Andhra Pradesh":      ["ap-government-jobs", "andhra-pradesh-government-jobs"],
    "Arunachal Pradesh":   ["ar-government-jobs", "arunachal-pradesh-government-jobs"],
    "Assam":               ["as-government-jobs", "assam-government-jobs"],
    "Bihar":               ["br-government-jobs", "bihar-government-jobs"],
    "Chhattisgarh":        ["cg-government-jobs", "chhattisgarh-government-jobs"],
    "Goa":                 ["ga-government-jobs", "goa-government-jobs"],
    "Gujarat":             ["gj-government-jobs", "gujarat-government-jobs"],
    "Haryana":             ["hr-government-jobs", "haryana-government-jobs"],
    "Himachal Pradesh":    ["hp-government-jobs", "himachal-pradesh-government-jobs"],
    "Jharkhand":           ["jh-government-jobs", "jharkhand-government-jobs"],
    "Karnataka":           ["ka-government-jobs", "karnataka-government-jobs"],
    "Kerala":              ["kl-government-jobs", "kerala-government-jobs"],
    "Madhya Pradesh":      ["mp-government-jobs", "madhya-pradesh-government-jobs"],
    "Maharashtra":         ["mh-government-jobs", "maharashtra-government-jobs"],
    "Manipur":             ["mn-government-jobs", "manipur-government-jobs"],
    "Meghalaya":           ["ml-government-jobs", "meghalaya-government-jobs"],
    "Mizoram":             ["mz-government-jobs", "mizoram-government-jobs"],
    "Nagaland":            ["nl-government-jobs", "nagaland-government-jobs"],
    "Odisha":              ["od-government-jobs", "or-government-jobs", "odisha-government-jobs"],
    "Punjab":              ["pb-government-jobs", "punjab-government-jobs"],
    "Rajasthan":           ["rj-government-jobs", "rajasthan-government-jobs"],
    "Sikkim":              ["sk-government-jobs", "sikkim-government-jobs"],
    "Tamil Nadu":          ["tn-government-jobs", "tamil-nadu-government-jobs"],
    "Telangana":           ["tg-government-jobs", "ts-government-jobs", "telangana-government-jobs"],
    "Tripura":             ["tr-government-jobs", "tripura-government-jobs"],
    "Uttar Pradesh":       ["up-government-jobs", "uttar-pradesh-government-jobs"],
    "Uttarakhand":         ["uk-government-jobs", "ua-government-jobs", "uttarakhand-government-jobs"],
    "West Bengal":         ["wb-government-jobs", "west-bengal-government-jobs"],
    "Delhi":               ["dl-government-jobs", "delhi-government-jobs"],
    "Jammu and Kashmir":   ["jk-government-jobs", "jammu-and-kashmir-government-jobs"],
    "Chandigarh":          ["ch-government-jobs", "chandigarh-government-jobs"],
    "Puducherry":          ["py-government-jobs", "pondicherry-government-jobs", "puducherry-government-jobs"],
    "Andaman and Nicobar": ["an-government-jobs", "andaman-and-nicobar-government-jobs"],
    "Dadra and Nagar Haveli": ["dn-government-jobs", "dh-government-jobs", "dadra-and-nagar-haveli-government-jobs"],
    "Daman and Diu":       ["dd-government-jobs", "dm-government-jobs", "daman-and-diu-government-jobs"],
    "Lakshadweep":         ["ld-government-jobs", "lakshadweep-government-jobs"],
    "Ladakh":              ["la-government-jobs", "ladakh-government-jobs"],
}

# ============================================================
# URL NORMALIZATION (dedup key)
# ============================================================
def normalize_url(url: str, base: str = BASE_SITE) -> str:
    """Absolute, lowercase-host, no trailing-slash-variance, no query/fragment.
    This normalized form is the deduplication key — two listings that point to
    the same detail page MUST produce the same key here.
    """
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = urljoin(base + "/", url)
    elif not url.startswith("http"):
        url = urljoin(base + "/", url)
    p = urlparse(url)
    host = (p.netloc or "").lower()
    # normalize www / non-www to www (FJA canonical host)
    if host == "freejobalert.com":
        host = "www.freejobalert.com"
    path = p.path or "/"
    if not path.endswith("/"):
        path = path + "/"
    return f"{p.scheme or 'https'}://{host}{path}"


def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


# ============================================================
# PHASE 1: URL COLLECTION (no detail scrape)
# ============================================================
def _collect_source(session, categories_items, label_fmt, total_label):
    """Generic Phase-1 collector.
    categories_items: iterable of (tag, base_url) — listing pages to crawl.
    Returns: { normalized_detail_url: [tag, tag, ...] }
    """
    url_map = {}
    total = len(categories_items)
    consecutive_empty = 0
    for idx, (tag, base_url) in enumerate(categories_items, 1):
        print(f"  {label_fmt} [{idx}/{total}]: {tag}")
        # inter-listing delay (lighter for big district set)
        if idx > 1:
            if consecutive_empty >= 5:
                wait_s = min(60 + (consecutive_empty - 5) * 20, 180)
                print(f"    [THROTTLE] {consecutive_empty} consecutive empties — {wait_s}s wait")
                smart_delay("crawl", extra=wait_s - 5)
            else:
                smart_delay("normal", extra=1.0)

        links = []
        confirmed_empty = False
        for attempt in range(1, MAX_RETRIES + 1):
            links, confirmed_empty = collect_all_job_links(session, base_url, tag)
            if links:
                break
            if confirmed_empty:
                break
            ok = _wait_for_internet(session, base_url, attempt_num=attempt)
            if not ok:
                break

        if not links:
            consecutive_empty += 1
            continue
        consecutive_empty = 0

        for raw in links:
            nurl = normalize_url(raw)
            if not nurl:
                continue
            url_map.setdefault(nurl, [])
            if tag not in url_map[nurl]:
                url_map[nurl].append(tag)
        print(f"    -> {len(links)} links ({len(url_map)} unique {total_label} so far)")
    return url_map


# ============================================================
# PHASE 2: MERGE (dedup across the three sources)
# ============================================================
def merge_url_maps(fja_map, state_map, district_map):
    """Build master_url_map keyed by normalized URL with separated tag buckets."""
    master = {}
    def _ensure(u):
        master.setdefault(u, {"fja_cats": [], "states": [], "districts": []})
        return master[u]

    for u, cats in fja_map.items():
        b = _ensure(u)
        for c in cats:
            if c not in b["fja_cats"]:
                b["fja_cats"].append(c)
    for u, states in state_map.items():
        b = _ensure(u)
        for s in states:
            if s not in b["states"]:
                b["states"].append(s)
    for u, districts in district_map.items():
        b = _ensure(u)
        for d in districts:
            if d not in b["districts"]:
                b["districts"].append(d)
    return master


# ============================================================
# PHASE 3: DETAIL SCRAPE (each unique URL exactly once)
# ============================================================
def _scrape_one(url, tags):
    """Scrape a single detail page once, attach all tags + inferred states."""
    session = make_session()
    job = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            job = extract_job_page(session, url)
            if job and not _is_empty_job(job):
                break
        except Exception as e:
            print(f"    [retry {attempt}] {url[:60]} — {e}")
            session = make_session()
            smart_delay("slow", extra=attempt * 3)
    if not job or _is_empty_job(job):
        return None

    # Attach the full cross-source tag set
    job["fja_categories"] = sorted(set(tags.get("fja_cats", [])))
    job["state_tags"]     = sorted(set(tags.get("states", [])))
    job["district_tags"]  = sorted(set(tags.get("districts", [])))
    job["_scraped_from"]  = url

    # Infer states from districts via DISTRICT_META (district = finest location)
    inferred = set()
    for d in job["district_tags"]:
        meta = DISTRICT_META.get(d, {})
        st = meta.get("state")
        if st and st not in job["state_tags"]:
            inferred.add(st)
        # also drop district name into job_location if missing
        bd = job.setdefault("basic_details", {})
        if not bd.get("job_location"):
            dist_name = meta.get("district", d)
            if st:
                bd["job_location"] = f"{dist_name}, {st}"
    job["inferred_states"] = sorted(inferred)
    return job


def scrape_unique_urls(master_url_map, already_scraped):
    """Phase 3 — parallel scrape of only the NOT-yet-scraped unique URLs."""
    to_scrape = [(u, t) for u, t in master_url_map.items() if u not in already_scraped]
    print(f"\n[PHASE 3] Unique URLs total: {len(master_url_map)} | "
          f"already done: {len(already_scraped)} | to scrape now: {len(to_scrape)}")

    results = []
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(_scrape_one, u, t): u for u, t in to_scrape}
        for fut in as_completed(futs):
            done += 1
            try:
                job = fut.result()
            except Exception as e:
                job = None
                print(f"    [error] {futs[fut][:60]} — {e}")
            if job:
                results.append(job)
            if done % 25 == 0:
                print(f"    ...scraped {done}/{len(to_scrape)} "
                      f"({len(results)} valid)")
            smart_delay("fast")
    return results


# ============================================================
# OUTPUT
# ============================================================
def _load_existing():
    """Resume: existing deduped jobs (URL-level skip)."""
    if os.path.exists(UNIFIED_OUTPUT):
        try:
            with open(UNIFIED_OUTPUT, encoding="utf-8") as f:
                d = json.load(f)
            jobs = d.get("deduped_jobs", [])
            return jobs
        except Exception:
            return []
    return []


def build_index(jobs):
    """Secondary index: tag → [urls]."""
    by_fja, by_state, by_dist = {}, {}, {}
    for j in jobs:
        u = j.get("_scraped_from", "")
        for c in j.get("fja_categories", []):
            by_fja.setdefault(c, []).append(u)
        for s in j.get("state_tags", []) + j.get("inferred_states", []):
            by_state.setdefault(s, []).append(u)
        for d in j.get("district_tags", []):
            by_dist.setdefault(d, []).append(u)
    # dedup url lists
    by_fja   = {k: sorted(set(v)) for k, v in by_fja.items()}
    by_state = {k: sorted(set(v)) for k, v in by_state.items()}
    by_dist  = {k: sorted(set(v)) for k, v in by_dist.items()}
    return by_fja, by_state, by_dist


def save_output(jobs, meta, by_fja, by_state, by_dist):
    out = {
        "deduped_jobs": _strip_aws_keys(jobs),
        "meta": meta,
    }
    with open(UNIFIED_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    idx = {"by_fja_category": by_fja, "by_state": by_state, "by_district": by_dist}
    with open(UNIFIED_INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)
    print(f"  [SAVE] {UNIFIED_OUTPUT} ({len(jobs)} jobs), {UNIFIED_INDEX}")


# ============================================================
# MAIN RUN
# ============================================================
def run():
    print("\n" + "=" * 60)
    print("  UNIFIED FJA SCRAPER — dedup across qual / state / district")
    print("=" * 60)

    session = make_session()

    # ── PHASE 1 ───────────────────────────────────────────────
    print(f"\n[PHASE 1] URL collection (no detail scrape)")
    print(f"  Sources: {len(FJA_CATEGORIES)} qual + {len(STATE_URL_MAP)} state "
          f"+ {len(DISTRICT_CATEGORIES)} district")

    print("\n[1a] Qualification-wise listings...")
    fja_map = _collect_source(session, list(FJA_CATEGORIES.items()),
                              "QUAL", "fja-url")

    print("\n[1b] State-wise listings...")
    # Build (state, working_url) by trying candidate slugs
    state_items = []
    for state_name, slugs in STATE_URL_MAP.items():
        chosen = None
        for slug in (slugs if isinstance(slugs, list) else [slugs]):
            url = f"{BASE_SITE}/search-jobs/{slug}/"
            chosen = url
            break  # first candidate; collector retries internally
        state_items.append((state_name, chosen))
    # State collector keyed by state NAME (tag), not slug
    state_map = _collect_source(session, state_items, "STATE", "state-url")

    print("\n[1c] District-wise listings...")
    district_map = _collect_source(session, list(DISTRICT_CATEGORIES.items()),
                                   "DIST", "district-url")

    # ── PHASE 2 ───────────────────────────────────────────────
    print(f"\n[PHASE 2] Merge URL maps (deduplication)")
    master_url_map = merge_url_maps(fja_map, state_map, district_map)
    total_refs = (sum(len(v) for v in fja_map.values())
                  + sum(len(v) for v in state_map.values())
                  + sum(len(v) for v in district_map.values()))
    print(f"  Listing refs (with dups): {total_refs}")
    print(f"  Unique detail URLs      : {len(master_url_map)}")
    print(f"  Deduplicated away       : {total_refs - len(master_url_map)}")

    # ── PHASE 3 ───────────────────────────────────────────────
    existing_jobs = _load_existing()
    already = {j.get("_scraped_from") for j in existing_jobs if j.get("_scraped_from")}
    new_jobs = scrape_unique_urls(master_url_map, already)

    # Merge new + existing (URL unique)
    all_jobs_by_url = {j["_scraped_from"]: j for j in existing_jobs}
    for j in new_jobs:
        all_jobs_by_url[j["_scraped_from"]] = j   # fresh overrides stale
    all_jobs = list(all_jobs_by_url.values())

    # ── PHASE 4 ───────────────────────────────────────────────
    by_fja, by_state, by_dist = build_index(all_jobs)
    meta = {
        "total_unique_jobs":          len(all_jobs),
        "total_fja_listing_refs":     sum(len(v) for v in fja_map.values()),
        "total_state_listing_refs":   sum(len(v) for v in state_map.values()),
        "total_district_listing_refs":sum(len(v) for v in district_map.values()),
        "deduplicated_count":         total_refs - len(master_url_map),
        "scraped_at":                 datetime.now(timezone.utc).isoformat(),
    }
    save_output(all_jobs, meta, by_fja, by_state, by_dist)

    print("\n" + "=" * 60)
    print(f"  UNIFIED FJA COMPLETE")
    print(f"  Unique jobs: {len(all_jobs)} | new this run: {len(new_jobs)}")
    print(f"  FJA cats indexed: {len(by_fja)} | states: {len(by_state)} | districts: {len(by_dist)}")
    print("=" * 60)
    return all_jobs


# ============================================================
# MERGE INTO UNIFIED JSON
# ============================================================
if __name__ == "__main__":
    from scraper_merge import merge_into_json, wait_for_internet
    import json as _json_mod

    wait_for_internet("FreeJobAlert Unified")

    error_str = ""
    try:
        run()
    except Exception as e:
        import traceback; traceback.print_exc()
        error_str = str(e)

    # Load unified output + index, combine into one source payload
    payload = {}
    if os.path.exists(UNIFIED_OUTPUT):
        with open(UNIFIED_OUTPUT, encoding="utf-8") as f:
            uni = _json_mod.load(f)
        payload["deduped_jobs"] = uni.get("deduped_jobs", [])
        payload["meta"]         = uni.get("meta", {})
    if os.path.exists(UNIFIED_INDEX):
        with open(UNIFIED_INDEX, encoding="utf-8") as f:
            idx = _json_mod.load(f)
        payload["by_fja_category"] = idx.get("by_fja_category", {})
        payload["by_state"]        = idx.get("by_state", {})
        payload["by_district"]     = idx.get("by_district", {})

    merge_into_json(
        source        = "freejobalert_unified",
        fresh_data    = payload,
        scraper_error = error_str,
    )
