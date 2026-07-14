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

# Junk-job guard (thin/empty title -> junk slug -> future 404). Same logic the
# site generator uses, applied here so junk never even enters the JSON.
from fja_parse_helpers import is_junk_job as _is_junk_job

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
    # /articles/ paths pe trailing slash mat lagao — FJA 404 deta hai.
    # Sirf directory-style paths pe slash rakho (e.g. /search-jobs/xyz/).
    if "/articles/" not in path and not path.endswith("/"):
        path = path + "/"
    return f"{p.scheme or 'https'}://{host}{path}"


import re as _re_global

def _title_slug(url: str) -> str:
    """FJA /articles/ URL se title-slug extract karo (numeric ID strip karke).

    FJA PROBLEM: Same job ke liye FJA multiple article URLs publish karta hai —
    yeh sab DIFFERENT numeric IDs ke saath same title slug hain:
      /articles/wcd-odisha-anganwadi-worker-2026-apply-online-3054942
      /articles/wcd-odisha-anganwadi-worker-2026-apply-online-3053939
      /articles/wcd-odisha-anganwadi-worker-2026-apply-online-3053118

    Ye teeno same job ke liye alag notifications hain (vacancy update, last date
    extension, correction notice etc). Hamare liye ye EK hi job hai.

    FIX: URL ke last segment se trailing numeric ID (-XXXXXXX) strip karo.
    Result sab URLs ke liye identical hoga → title-level dedup possible.

    Non-/articles/ URLs ke liye empty string return karo (URL-level dedup use hoga).
    """
    p = urlparse(url)
    if "/articles/" not in p.path:
        return ""
    # last path segment = "wcd-odisha-...-3054942"
    seg = p.path.rstrip("/").rsplit("/", 1)[-1]
    # trailing numeric block strip (e.g. -3054942 = dash + 7 digits)
    slug = _re_global.sub(r'-\d{5,}$', '', seg).strip("-").lower()
    return slug


def _job_title_key(job: dict) -> str:
    """Job dict se canonical title key banao (title-level dedup ke liye)."""
    bd = job.get("basic_details") or {}
    title = (bd.get("job_title") or "").strip().lower()
    if not title:
        title = (job.get("title") or "").strip().lower()
    return _re_global.sub(r'\s+', ' ', title)


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

    Returns: (url_map, per_tag_ordered)
      url_map         : { normalized_url: [tag, ...] }   — for dedup / merge
      per_tag_ordered : { tag: [url, url, ...] }         — PER-CATEGORY ORDER
                        Preserves the exact listing-page order for each category
                        so by_fja_category index matches source site order.
    """
    url_map       = {}   # url -> [tags]   (for dedup merge)
    per_tag_order = {}   # tag -> [url...] (ordered list, preserves listing order)
    total = len(categories_items)
    for idx, (tag, base_url) in enumerate(categories_items, 1):
        print(f"  {label_fmt} [{idx}/{total}]: {tag}")
        # Sirf actual requests ke beech minimal delay — NO throttle on empty pages.
        # "NO JOBS PAGE" = genuinely empty district, NOT a rate-limit. Throttling
        # on empty pages wastes hours on 697 districts (most are empty).
        if idx > 1:
            smart_delay("fast")   # ~0.5-1s — enough to be polite

        links = []
        confirmed_empty = False
        for attempt in range(1, MAX_RETRIES + 1):
            links, confirmed_empty = collect_all_job_links(session, base_url, tag)
            if links:
                break
            if confirmed_empty:
                break   # genuinely empty — no retry, no wait
            # Only reach here on network error — then wait
            ok = _wait_for_internet(session, base_url, attempt_num=attempt)
            if not ok:
                break

        if not links:
            continue   # empty/error — move on immediately, no counter

        # Build per-tag ordered list (deduped, listing-page order preserved)
        _seen_for_tag = set()
        for raw in links:
            nurl = normalize_url(raw)
            if not nurl:
                continue
            url_map.setdefault(nurl, [])
            if tag not in url_map[nurl]:
                url_map[nurl].append(tag)
            # Per-tag order: first-seen order from this category's listing page
            if nurl not in _seen_for_tag:
                per_tag_order.setdefault(tag, []).append(nurl)
                _seen_for_tag.add(nurl)

        print(f"    -> {len(links)} links ({len(url_map)} unique {total_label} so far)")
    return url_map, per_tag_order


# ============================================================
# PHASE 2: MERGE (dedup across the three sources)
# ============================================================
def merge_url_maps(fja_map, state_map, district_map):
    """Build master_url_map keyed by normalized URL with separated tag buckets.

    FJA TITLE-LEVEL DEDUP (Phase 2 extension):
    FJA same job ke liye multiple /articles/ URLs publish karta hai — ek hi
    vacancy ke liye update/correction/reminder articles. Ye sab ALAG normalized
    URLs hain isliye URL-level dedup inhe miss karta hai aur Phase 3 mein multiple
    baar scrape hote hain.

    Fix: /articles/ URLs ke liye title-slug (numeric ID stripped) bhi track karo.
    Pehla URL jo ek title-slug ke liye aaya use "canonical" maano. Baad mein same
    title-slug wale URLs ko canonical pe merge karo — tags union, URL discard.
    Non-/articles/ URLs pe ye logic nahi lagta (URL-level dedup sufficient).
    """
    master = {}

    def _ensure(u):
        master.setdefault(u, {"fja_cats": [], "states": [], "districts": []})
        return master[u]

    # title_slug → canonical URL (first-seen wins as canonical for /articles/)
    _title_to_canonical: dict = {}

    def _resolve_canonical(url: str) -> str:
        """Return canonical URL for this url. For /articles/ URLs with same
        title-slug, redirect to the first-seen canonical."""
        tslug = _title_slug(url)
        if not tslug:
            return url   # non-/articles/ — URL is its own canonical
        if tslug in _title_to_canonical:
            return _title_to_canonical[tslug]   # redirect to canonical
        _title_to_canonical[tslug] = url        # first-seen = canonical
        return url

    def _add_tags(url_map, tag_key):
        for u, tags in url_map.items():
            canonical = _resolve_canonical(u)
            b = _ensure(canonical)
            for t in tags:
                if t not in b[tag_key]:
                    b[tag_key].append(t)

    _add_tags(fja_map,      "fja_cats")
    _add_tags(state_map,    "states")
    _add_tags(district_map, "districts")

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

    # Derive slug from JOB TITLE (matches generate_all.py site URL pattern)
    # This ensures consistency between scraper output and generated HTML pages.
    # OLD: URL-based slug created mismatched pages (one-job-three-URLs problem).
    # NEW: Title-based = same slug across scraper, generate, and live site.
    import re as _re
    _bd = job.get("basic_details") or {}
    _title = (_bd.get("job_title") or "").strip()
    _slug = ""
    if _title:
        _slug = _re.sub(r'[\s_]+', '-',
                _re.sub(r'[^a-z0-9\s-]', '', _title.lower())).strip('-')[:80]
        if _slug:
            job["slug"] = _slug

    # JUNK GUARD: thin/empty title + junk slug -> this page would become a /jobs/
    # 404 on the site. Reject it here so it never enters deduped_jobs / the JSON.
    if _is_junk_job(_title, _slug):
        print(f"    [skip-junk] {url[:70]}  title={_title!r} slug={_slug!r}")
        return None

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


def title_dedup_merge(jobs: list) -> list:
    """Phase 3b — title-level post-scrape dedup.

    WHY THIS IS NEEDED:
    master_url_map already deduplicates /articles/ URLs via title-slug at Phase 2.
    But existing_jobs (loaded from _temp_unified_fja.json) were scraped in PREVIOUS
    runs when the fix wasn't applied — they can still carry duplicate title entries
    under different _scraped_from URLs.

    This function does a final pass over ALL jobs (new + existing combined) and for
    any title seen more than once:
      - Keeps the job with the MOST tags (richest data).
      - Merges fja_categories, state_tags, district_tags from ALL duplicates into it.
      - Discards the rest.

    Result: 1 URL, 1 content item, union of ALL categories it appeared in.
    This satisfies the rule: "ek item ek hona chahiye — jitni categories mein tha,
    utni categories mein dikhega."

    FALSE-POSITIVE GUARD (important):
    Some organizations (e.g. TANUVAS, CCRUM-style recurring walk-ins) reuse the
    EXACT SAME generic/templated job_title text for genuinely DIFFERENT postings
    at DIFFERENT locations — e.g. "TANUVAS Technical Fellow Recruitment 2026 -
    Walkin" can be one real posting under Delhi's own listing AND a completely
    separate one under Tamil Nadu's, with different article IDs, different dates.
    These are NOT the same job — merging them would leak a Delhi tag onto a
    Chennai-only posting (or vice versa) — the exact "wrong category" bug.
    Signal: if both candidates already carry their OWN non-empty state/district
    tags and those tags DON'T OVERLAP AT ALL, they're almost certainly different
    real-world postings that just share templated title text. In that case, keep
    them as SEPARATE jobs — don't merge, don't union their tags.
    """
    seen_title: dict = {}   # title_key -> index into `result`
    result: list = []

    for job in jobs:
        tkey = _job_title_key(job)
        if not tkey:
            result.append(job)
            continue

        if tkey not in seen_title:
            seen_title[tkey] = len(result)
            result.append(job)
        else:
            kept = result[seen_title[tkey]]

            kept_loc = set(kept.get("state_tags", []) or []) | set(kept.get("inferred_states", []) or [])
            dup_loc  = set(job.get("state_tags", []) or [])  | set(job.get("inferred_states", []) or [])
            kept_dist = set(kept.get("district_tags", []) or [])
            dup_dist  = set(job.get("district_tags", []) or [])

            disjoint_location = (
                (kept_loc and dup_loc and not (kept_loc & dup_loc)) or
                (kept_dist and dup_dist and not (kept_dist & dup_dist))
            )
            if disjoint_location:
                # Different real postings sharing a templated title — keep separate.
                result.append(job)
                continue

            # Merge this duplicate's tags into the kept copy
            for field in ("fja_categories", "state_tags", "district_tags", "inferred_states"):
                merged_vals = sorted(set(kept.get(field, []) + job.get(field, [])))
                kept[field] = merged_vals
            # Keep the copy with a slug (prefer slugged version)
            if not kept.get("slug") and job.get("slug"):
                kept["slug"] = job["slug"]
            # Keep the copy with the highest-numbered article URL (most recent update)
            def _article_id(j):
                m = _re_global.search(r'-(\d+)$', (j.get("_scraped_from") or "").rstrip("/"))
                return int(m.group(1)) if m else 0
            if _article_id(job) > _article_id(kept):
                # newer article → update _scraped_from but keep merged tags
                kept["_scraped_from"] = job["_scraped_from"]

    before = len(jobs)
    after  = len(result)
    if before != after:
        print(f"  [TITLE DEDUP] {before} → {after} jobs "
              f"({before - after} duplicates merged, categories preserved)")
    return result


# ============================================================
# OUTPUT
# ============================================================
def _load_existing():
    """Resume: existing deduped jobs (URL-level skip) + saved per-tag orders."""
    if os.path.exists(UNIFIED_OUTPUT):
        try:
            with open(UNIFIED_OUTPUT, encoding="utf-8") as f:
                d = json.load(f)
            jobs = d.get("deduped_jobs", [])
            saved_order = d.get("fja_per_tag_order", {})
            # Also load saved state_url_order for resilience when state page fails
            saved_state_order = d.get("state_url_order", {})
            # Also load saved district_per_tag_order (listing-page order per district)
            saved_district_order = d.get("district_per_tag_order", {})
            return jobs, saved_order, saved_state_order, saved_district_order
        except Exception:
            return [], {}, {}, {}
    return [], {}, {}, {}


def _fja_article_id(url: str) -> int:
    """Trailing numeric article ID from a /articles/...-NNNNNNN URL. FJA assigns
    these sequentially at publish time, so higher ID == published more recently —
    this is the site's own de-facto newest-first ordering key."""
    m = _re_global.search(r'-(\d+)/?$', (url or '').rstrip('/'))
    return int(m.group(1)) if m else 0


def _insert_by_recency(lst: list, url: str) -> None:
    """Insert url into lst keeping descending article-ID order (newest first),
    matching the source site's own ordering.

    ORDER BUG (2026-07-14): the old code always did lst.insert(0, url) for any
    item missed by this run's listing-page capture, on the assumption a missed
    item must be brand-new. That's only true when the item genuinely IS the
    newest. When an OLDER job gets missed (e.g. it fell off this run's table
    scrape for an unrelated reason) it was wrongly shoved to position 0 —
    e.g. DFPD (article ~3049724) landed above IIT Delhi / AIIMS Delhi postings
    from ~3057000-3058000, weeks newer, at the very top of the Delhi state
    page. Inserting by article-ID rank fixes both cases: a truly-new item
    still has the highest ID and lands at position 0 anyway; an old item
    lands back where it chronologically belongs.
    """
    uid = _fja_article_id(url)
    if uid == 0 or not lst:
        lst.insert(0, url)
        return
    for i, existing in enumerate(lst):
        if _fja_article_id(existing) < uid:
            lst.insert(i, url)
            return
    lst.append(url)


def build_index(jobs, fja_per_tag_order=None, state_url_order=None, district_per_tag_order=None):
    """Secondary index: tag → [urls].

    fja_per_tag_order: optional dict {tag: [url, ...]} from _collect_source.
    When provided, by_fja_category uses the EXACT listing-page order for each
    category — not the master_url_map insertion order which mixes all sources.
    This ensures the site page for e.g. '10TH_Pass' shows jobs in the same
    order as FJA's /search-jobs/10th-pass/ listing page.

    state_url_order: optional dict {state_name: [url, ...]} from state page scrape.
    When provided, by_state uses the EXACT listing-page order for each state.

    district_per_tag_order: optional dict {district_name: [url, ...]} from
    _collect_source (district listing pages). When provided, by_district uses
    the EXACT listing-page order per district — same fix as fja/state above.
    Previously this was collected but discarded, so by_district silently fell
    back to master_url_map/title-dedup order instead of the source site's order.

    NOTE: After title_dedup_merge, a job's _scraped_from may have been updated to
    a newer article URL that was NOT in fja_per_tag_order. We therefore build
    by_fja in two passes:
      1. fja_per_tag_order for listing-page order (URL-keyed lookup by title-slug).
      2. job.fja_categories for any tags the index missed (belt-and-suspenders).
    """
    # Build url→job AND title_slug→job for resilient lookup after _scraped_from update
    job_by_url   = {j.get("_scraped_from", ""): j for j in jobs}
    job_by_tslug = {}
    for j in jobs:
        ts = _title_slug(j.get("_scraped_from", ""))
        if ts:
            job_by_tslug[ts] = j

    def _find_job(url):
        """Lookup by URL first; fall back to title-slug (handles _scraped_from updates).
        Also tries trailing-slash variant to handle normalization edge cases."""
        # 1. Exact match (fastest path)
        j = job_by_url.get(url)
        if j:
            return j
        # 2. Title-slug fallback (handles _scraped_from updates after title_dedup_merge)
        ts = _title_slug(url)
        if ts:
            j = job_by_tslug.get(ts)
            if j:
                return j
        # 3. Trailing-slash variant (normalization edge cases)
        alt = url.rstrip("/") if url.endswith("/") else url + "/"
        return job_by_url.get(alt)

    if fja_per_tag_order:
        by_fja = {}
        for tag, ordered_urls in fja_per_tag_order.items():
            _seen = set()
            by_fja[tag] = []
            for u in ordered_urls:
                j = _find_job(u)
                if j:
                    canonical_u = j.get("_scraped_from", u)
                    if canonical_u not in _seen:
                        by_fja[tag].append(canonical_u)
                        _seen.add(canonical_u)
        # Safety: include any tags present in job.fja_categories but not in index.
        # ORDER FIX (2026-07-13, refined 2026-07-14): a job caught here was
        # missed by this run's category-listing capture — could be brand-new
        # (posted after that fetch) OR an older item missed for an unrelated
        # reason. Insert by article-ID rank (see _insert_by_recency) instead of
        # always prepending, so old items don't get wrongly shoved to the top.
        for j in jobs:
            u = j.get("_scraped_from", "")
            for c in j.get("fja_categories", []):
                if c not in by_fja:
                    by_fja[c] = []
                if u not in by_fja[c]:
                    _insert_by_recency(by_fja[c], u)
    else:
        # Fallback: derive from job tags (dedup order-preserving)
        by_fja = {}
        for j in jobs:
            u = j.get("_scraped_from", "")
            for c in j.get("fja_categories", []):
                by_fja.setdefault(c, []).append(u)
        by_fja = {k: list(dict.fromkeys(v)) for k, v in by_fja.items()}

    # by_state: prefer state_url_order (listing-page order), fallback to job tags
    if state_url_order:
        by_state = {}
        for state_name, ordered_urls in state_url_order.items():
            _seen = set()
            by_state[state_name] = []
            for u in ordered_urls:
                j = _find_job(u)
                if j:
                    canonical_u = j.get("_scraped_from", u)
                    if canonical_u not in _seen:
                        by_state[state_name].append(canonical_u)
                        _seen.add(canonical_u)
        # Safety: include any tags present in job.state_tags but not in index.
        # ORDER FIX (2026-07-13, refined 2026-07-14): a job lands here only
        # when it was NOT seen in this run's state-table capture
        # (state_per_tag_order) but IS tagged for this state some other way.
        # That's usually a brand-new post (posted in the gap between this
        # run's state-page fetch and its other phases) — but can also be an
        # OLDER job that fell off this run's table capture for an unrelated
        # reason. Blindly prepending (old behavior) fixed the first case but
        # broke the second: e.g. DFPD (article ~3049724, weeks old) got
        # shoved above IIT Delhi / AIIMS Delhi posts from ~3057000-3058000 at
        # the very top of the Delhi state page. Insert by article-ID rank
        # instead — a genuinely new item still has the highest ID and lands
        # at the top anyway; an old item lands back where it belongs.
        for j in jobs:
            u = j.get("_scraped_from", "")
            for s in j.get("state_tags", []) + j.get("inferred_states", []):
                if s not in by_state:
                    by_state[s] = []
                if u not in by_state[s]:
                    _insert_by_recency(by_state[s], u)
    else:
        # Fallback: derive from job tags
        by_state = {}
        for j in jobs:
            u = j.get("_scraped_from", "")
            for s in j.get("state_tags", []) + j.get("inferred_states", []):
                by_state.setdefault(s, []).append(u)
        by_state = {k: list(dict.fromkeys(v)) for k, v in by_state.items()}

    # by_district: prefer district_per_tag_order (listing-page order), same
    # pattern as by_fja/by_state above — fallback to job-tag order only if the
    # per-tag order wasn't supplied (e.g. very old saved data / cold start).
    if district_per_tag_order:
        by_dist = {}
        for dist_name, ordered_urls in district_per_tag_order.items():
            _seen = set()
            by_dist[dist_name] = []
            for u in ordered_urls:
                j = _find_job(u)
                if j:
                    canonical_u = j.get("_scraped_from", u)
                    if canonical_u not in _seen:
                        by_dist[dist_name].append(canonical_u)
                        _seen.add(canonical_u)
        # Safety: include any tags present in job.district_tags but not in index.
        # ORDER FIX (2026-07-13, refined 2026-07-14): same reasoning as the
        # by_state fallback above — a job caught here was missed by this run's
        # district-table capture, which could mean brand-new OR an older item
        # missed for an unrelated reason. Insert by article-ID rank instead of
        # always prepending, so old items don't get wrongly shoved to the top.
        for j in jobs:
            u = j.get("_scraped_from", "")
            for d in j.get("district_tags", []):
                if d not in by_dist:
                    by_dist[d] = []
                if u not in by_dist[d]:
                    _insert_by_recency(by_dist[d], u)
    else:
        # Fallback: derive from job tags (old behavior — order matches jobs list,
        # NOT the district listing page's own order)
        by_dist = {}
        for j in jobs:
            u = j.get("_scraped_from", "")
            for d in j.get("district_tags", []):
                by_dist.setdefault(d, []).append(u)
        by_dist  = {k: list(dict.fromkeys(v)) for k, v in by_dist.items()}
    return by_fja, by_state, by_dist


# Fields jo index build ke liye internally chahiye the, lekin final JSON mein nahi chahiye
_INTERNAL_ONLY_FIELDS = frozenset({
    "fja_categories", "state_tags", "district_tags", "inferred_states", "seo_tags",
})


def _strip_internal_fields(jobs: list) -> list:
    """Internal-only metadata fields job objects se hatao before saving."""
    cleaned = []
    for job in jobs:
        j = {k: v for k, v in job.items() if k not in _INTERNAL_ONLY_FIELDS}
        cleaned.append(j)
    return cleaned


def _drop_junk_jobs(jobs: list) -> list:
    """Final safety net: thin/empty-title + junk-slug jobs ko deduped_jobs se
    hata do (site pe /jobs/ 404 churn rokta hai). Fresh scrapes _scrape_one me
    hi ruk jaate hain; yeh pass PURANE cached entries (pichhle runs ke) ko bhi
    saaf karta hai."""
    kept, dropped = [], 0
    for job in jobs:
        bd = job.get("basic_details") or {}
        title = (bd.get("job_title") or job.get("title") or "").strip()
        slug = job.get("_canonical_slug") or job.get("slug") or ""
        if _is_junk_job(title, slug or None):
            dropped += 1
            continue
        kept.append(job)
    if dropped:
        print(f"    [save] dropped {dropped} junk job(s) from deduped_jobs")
    return kept


def save_output(jobs, meta, by_fja, by_state, by_dist, fja_per_tag_order=None,
                 state_url_order=None, district_per_tag_order=None):
    clean_jobs = _strip_internal_fields(_strip_aws_keys(_drop_junk_jobs(jobs)))
    out = {
        "deduped_jobs": clean_jobs,
        "meta": meta,
    }
    if fja_per_tag_order:
        out["fja_per_tag_order"] = fja_per_tag_order  # persisted for resume runs
    if district_per_tag_order:
        out["district_per_tag_order"] = district_per_tag_order  # persisted for resume runs
    if state_url_order:
        out["state_url_order"] = state_url_order  # persisted for resume runs (state page fallback)
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
    fja_map, fja_per_tag_order = _collect_source(
        session, list(FJA_CATEGORIES.items()), "QUAL", "fja-url")

    print("\n[1b] State-wise listings (combined page — 1 request)...")
    # FJA /state-government-jobs/ = combined page, per-state slugs ab 404 dete hain.
    state_map = {}
    # state_per_tag_order: {state_name: [url, ...]} — THIS state's own table row
    # order, captured directly while parsing. Kept separate from state_map
    # (see ROOT CAUSE note below).
    state_per_tag_order = {}
    try:
        _sresp = session.get("https://www.freejobalert.com/state-government-jobs/", timeout=30)
        if _sresp.status_code == 200:
            from bs4 import BeautifulSoup as _BS
            _ssoup = _BS(_sresp.text, "lxml")
            _content = _ssoup.find("div", class_="entry-content") or _ssoup
            _sc = 0
            for _h in _content.find_all("h4", class_="latsec"):
                _sn = _h.get_text(strip=True)
                if not _sn: continue
                _tbl = _h.find_next("table")
                if not _tbl: continue
                _seen_for_state = set()
                for _row in _tbl.find_all("tr")[1:]:
                    _cols = _row.find_all("td")
                    if len(_cols) < 7: continue
                    _a = _cols[6].find("a", href=True)
                    if not _a: continue
                    _url = normalize_url(_a["href"])
                    if not _url: continue
                    state_map.setdefault(_url, [])
                    if _sn not in state_map[_url]: state_map[_url].append(_sn)
                    # Per-state order: preserve THIS state's own table row order.
                    # ROOT CAUSE FIX: some job URLs are cross-listed under
                    # multiple states (e.g. "Punjab and Haryana High Court",
                    # BBMB — shared boards). state_map is a single flat
                    # {url: [states]} dict, so such a URL's dict position gets
                    # fixed at whichever state's table lists it FIRST in the
                    # page (e.g. Chandigarh, parsed before Haryana). Every
                    # other state sharing that URL (e.g. Haryana) would then
                    # inherit that wrong position if by_state order were
                    # rebuilt from state_map.items() — instead of this state's
                    # OWN row order. Capturing order here, per state, while we
                    # still have the actual row sequence, avoids that entirely.
                    if _url not in _seen_for_state:
                        state_per_tag_order.setdefault(_sn, []).append(_url)
                        _seen_for_state.add(_url)
                _sc += 1
            print(f"  [OK] {_sc} states, {len(state_map)} unique job URLs")
        else:
            print(f"  [WARN] State page HTTP {_sresp.status_code} — state tags skip")
    except Exception as _e:
        print(f"  [WARN] State page error: {_e}")

    print("\n[1c] District-wise listings...")
    district_map, district_per_tag_order = _collect_source(
        session, list(DISTRICT_CATEGORIES.items()), "DIST", "district-url")

    # ── PHASE 2 ───────────────────────────────────────────────
    print(f"\n[PHASE 2] Merge URL maps (deduplication)")
    master_url_map = merge_url_maps(fja_map, state_map, district_map)
    total_refs = (sum(len(v) for v in fja_map.values())
                  + len(state_map)          # state_map = {url: [states]} — len = unique URLs
                  + sum(len(v) for v in district_map.values()))
    print(f"  Listing refs (with dups): {total_refs}")
    print(f"  Unique detail URLs      : {len(master_url_map)}")
    print(f"  Deduplicated away       : {total_refs - len(master_url_map)}")

    # ── PHASE 3 ───────────────────────────────────────────────
    existing_jobs, _saved_per_tag, _saved_state_order, _saved_district_order = _load_existing()
    already = {j.get("_scraped_from") for j in existing_jobs if j.get("_scraped_from")}
    new_jobs = scrape_unique_urls(master_url_map, already)

    # Merge saved per-tag order with fresh per-tag order.
    # Fresh run (fja_per_tag_order non-empty) takes priority — it reflects today's
    # listing page order. Saved order fills in any categories that weren't re-scraped
    # in this run (e.g. district-only resume).
    _merged_per_tag = dict(_saved_per_tag)
    for _tag, _urls in fja_per_tag_order.items():
        _merged_per_tag[_tag] = _urls  # fresh listing-page order wins
    fja_per_tag_order = _merged_per_tag

    # Merge saved district per-tag order with fresh district per-tag order —
    # same pattern as fja_per_tag_order above. This was previously collected
    # in Phase 1 and then silently discarded, which is why by_district didn't
    # follow the source site's listing order (see build_index).
    _merged_district_order = dict(_saved_district_order)
    for _tag, _urls in district_per_tag_order.items():
        _merged_district_order[_tag] = _urls  # fresh listing-page order wins
    district_per_tag_order = _merged_district_order
    print(f"  [DISTRICT ORDER] {len(district_per_tag_order)} districts, "
          f"{sum(len(v) for v in district_per_tag_order.values())} total refs")

    # Build state_url_order from fresh state_per_tag_order (or fallback to saved)
    # state_url_order: { state_name: [url, url, ...] } in listing-page order
    # This is analogous to fja_per_tag_order for qualification categories.
    state_url_order = dict(_saved_state_order)  # start with saved
    if state_per_tag_order:
        # Fresh run wins — use each state's OWN table row order directly.
        # (Previously this was rebuilt from state_map.items(), which is the
        # flat {url: [states]} dict — see ROOT CAUSE note in [1b] above for
        # why that silently broke order for any URL shared across states.)
        state_url_order.update(state_per_tag_order)
        print(f"  [STATE ORDER] {len(state_url_order)} states, "
              f"{sum(len(v) for v in state_url_order.values())} total refs")

    # Merge new + existing (URL unique)
    all_jobs_by_url = {
        j["_scraped_from"]: j
        for j in existing_jobs
        if j.get("_scraped_from")          # skip any job missing this key
    }
    for j in new_jobs:
        _sf = j.get("_scraped_from")
        if _sf:
            all_jobs_by_url[_sf] = j      # fresh overrides stale

    # ── TAG REFRESH FIX ───────────────────────────────────────
    # ROOT BUG: Existing jobs (from previous runs) retain their OLD state_tags,
    # district_tags, fja_categories. New state/district/qual tags discovered in
    # THIS run's master_url_map are NEVER merged into already-scraped jobs.
    # Result: by_state["Haryana"] only shows 2 jobs instead of 24 because 22
    # of them were scraped previously when their state_tags were empty/wrong.
    #
    # FIX: After building all_jobs_by_url, iterate master_url_map and UNION
    # the fresh tags from this run into every job (new OR existing).
    # This ensures EVERY scraped job reflects the complete current-run tag set.
    print(f"\n[TAG REFRESH] Syncing fresh tags into all {len(all_jobs_by_url)} jobs...")
    _refreshed = 0
    for _url, _tags in master_url_map.items():
        _job = all_jobs_by_url.get(_url)
        if not _job:
            continue
        _changed = False
        # fja_categories
        _fresh_fja = sorted(set(_tags.get("fja_cats", [])))
        _old_fja   = sorted(set(_job.get("fja_categories", [])))
        if set(_fresh_fja) != set(_old_fja):
            _job["fja_categories"] = sorted(set(_old_fja) | set(_fresh_fja))
            _changed = True
        # state_tags
        _fresh_st = sorted(set(_tags.get("states", [])))
        _old_st   = sorted(set(_job.get("state_tags", [])))
        if set(_fresh_st) != set(_old_st):
            _job["state_tags"] = sorted(set(_old_st) | set(_fresh_st))
            _changed = True
        # district_tags
        _fresh_dt = sorted(set(_tags.get("districts", [])))
        _old_dt   = sorted(set(_job.get("district_tags", [])))
        if set(_fresh_dt) != set(_old_dt):
            _job["district_tags"] = sorted(set(_old_dt) | set(_fresh_dt))
            _changed = True
        # inferred_states: re-derive from updated district_tags
        # FIX: .get() use karo — old cached jobs mein district_tags key absent
        # ho sakti hai (fresh_dt aur old_dt dono empty the → if block skip hua)
        _inferred = set(_job.get("inferred_states", []))
        for _d in _job.get("district_tags", []):
            _dmeta = DISTRICT_META.get(_d, {})
            _dst = _dmeta.get("state")
            if _dst and _dst not in _job.get("state_tags", []):
                _inferred.add(_dst)
        if _inferred != set(_job.get("inferred_states", [])):
            _job["inferred_states"] = sorted(_inferred)
            _changed = True
        if _changed:
            _refreshed += 1
    print(f"  [TAG REFRESH] {_refreshed} jobs had tags updated/expanded")

    # Safety: ensure ALL jobs (including those NOT in this run's master_url_map,
    # e.g. expired/removed jobs from previous runs) have tag fields initialised.
    # Prevents downstream KeyError on these keys in build_index / callers.
    for _job in all_jobs_by_url.values():
        _job.setdefault("fja_categories", [])
        _job.setdefault("state_tags", [])
        _job.setdefault("district_tags", [])
        _job.setdefault("inferred_states", [])
    # ── END TAG REFRESH FIX ────────────────────────────────────

    # ROOT CAUSE FIX: order karna master_url_map ke order ke hisaab se, na ki
    # dict-accumulation ke arbitrary order se. master_url_map FJA/state/district
    # listing pages ke scrape order me bana hai (jo newest-first hota hai), isliye
    # yeh order hi "JSON ka pehla item" wala sahi order hai. Pehle all_jobs
    # all_jobs_by_url.values() se ban raha tha jiska order purane runs ke
    # accumulation par depend karta tha — wahi wajah thi ki site har category
    # me JSON ke actual order ko follow nahi kar rahi thi.
    all_jobs = [all_jobs_by_url[u] for u in master_url_map if u in all_jobs_by_url]
    # Safety: agar koi job kisi wajah se master_url_map me na ho (purana/legacy
    # entry), use bhi list ke end me rakho — koi data silently drop na ho.
    _seen_u = set(master_url_map.keys())
    for u, j in all_jobs_by_url.items():
        if u not in _seen_u:
            all_jobs.append(j)

    # ── PHASE 3b: Title-level dedup ───────────────────────────
    # FJA same job ke liye multiple article URLs publish karta hai (update /
    # correction / reminder notices). Phase 2 (merge_url_maps) nayi URLs ke liye
    # title-slug dedup karta hai, lekin existing_jobs (pichle run se) mein ab bhi
    # duplicate title entries ho sakti hain. Title dedup unhe merge karta hai:
    #   1 job, 1 URL, union of all categories it appeared in.
    all_jobs = title_dedup_merge(all_jobs)

    # ── PHASE 4 ───────────────────────────────────────────────
    by_fja, by_state, by_dist = build_index(
        all_jobs,
        fja_per_tag_order=fja_per_tag_order,
        state_url_order=state_url_order,
        district_per_tag_order=district_per_tag_order,
    )
    meta = {
        "total_unique_jobs":          len(all_jobs),
        "total_fja_listing_refs":     sum(len(v) for v in fja_map.values()),
        "total_state_listing_refs":   len(state_map),  # unique job URLs seen on state listing page
        "total_district_listing_refs":sum(len(v) for v in district_map.values()),
        "deduplicated_count":         total_refs - len(master_url_map),
        "scraped_at":                 datetime.now(timezone.utc).isoformat(),
    }
    save_output(all_jobs, meta, by_fja, by_state, by_dist,
                fja_per_tag_order=fja_per_tag_order,
                state_url_order=state_url_order,
                district_per_tag_order=district_per_tag_order)

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
