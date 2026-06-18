#!/usr/bin/env python3
"""
incremental_cache.py — shared "don't re-scrape what we already have" layer.

PROBLEM THIS SOLVES
--------------------
Every scraper run was hitting EVERY detail-page URL again, even ones already
scraped in a previous run. For 5000+ jobs that means 5000+ requests every single
day, even when only 20-50 new jobs actually appeared. This module makes every
detail-scrape "new URLs only" — same pattern already proven in scraper_fja.py
(its existing_urls / new_links logic), reused here as ONE shared module so the
other 3 scrapers (scraper_sarkari.py covering Shine+SR+SN, scraper_state.py,
scraper_education.py) get the same behaviour without duplicating the logic.

HOW IT WORKS
------------
1. Before scraping a list of detail-page links for a category, call
   `filter_new_links(category, links, current_existing_items)` — it returns only
   the links NOT already present (matched by URL).
2. Already-scraped items are kept AS-IS (no re-fetch) and merged back in by the
   caller — so nothing in JSON is lost, only the genuinely-new ones get a request.
3. `record_removed(category, urls_seen_today)` lets a caller know which
   previously-known URLs were NOT seen on the listing page today (likely closed
   /expired / removed by the source) — caller decides whether to drop them.

This does NOT change what data looks like, what gets shown on the site, or any
existing JSON schema — it only decides WHICH urls get a fresh HTTP request.
"""
import json
import os

# A small sidecar file (separate from the big data JSON) that just tracks which
# URLs we've already fetched, per category — keeps the "have we seen this"
# check cheap and independent of the main 50MB+ data file.
_CACHE_FILE = "scrape_seen_urls.json"


def _load_cache():
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache):
    tmp = _CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, _CACHE_FILE)   # atomic write — never leaves a half-written file


def existing_urls_for(category, existing_items, url_key="_scraped_from"):
    """Given the items already in this category's JSON list, return the set of
    URLs already scraped. Also cross-checks the sidecar cache (covers cases
    where an old item was later pruned from the data JSON but we still don't
    want to re-hit its URL needlessly within the same day's run)."""
    urls = {item.get(url_key) for item in (existing_items or []) if item.get(url_key)}
    cache = _load_cache()
    urls |= set(cache.get(category, []))
    return urls


def filter_new_links(category, links, existing_items, url_key="_scraped_from"):
    """Return only the links that are genuinely new (not already scraped).
    `links` can be a list of URL strings, or a list of dicts with a 'url' key —
    both forms are handled."""
    existing = existing_urls_for(category, existing_items, url_key)

    def _url_of(l):
        return l if isinstance(l, str) else (l.get("url") or l.get("href") or "")

    new_links = [l for l in links if _url_of(l) not in existing]
    return new_links, existing


def mark_scraped(category, urls):
    """Call after successfully scraping a batch of new URLs, so even if they
    later vanish from the main data JSON, we remember we already hit them
    once today (cheap safety net against accidental re-fetch within a run)."""
    cache = _load_cache()
    seen = set(cache.get(category, []))
    seen |= set(urls)
    cache[category] = sorted(seen)
    _save_cache(cache)


def summary_line(category, total_links, new_links_count, existing_count):
    return (f"  [{category}] listing has {total_links} links | "
            f"already scraped: {existing_count} | new to fetch: {new_links_count}")
