#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_unindexed_feed.py — pick a rotating batch of un-indexed pages to
feature on the homepage, to get them crawled/indexed faster.

TWO-LAYER SIGNAL, REAL DATA PREFERRED:
  Layer 1 (real): data/gsc_index_state.json, maintained by the daily
    gsc-index-check.yml workflow (.github/workflows/gsc_check_index_status.js)
    via the actual Search Console URL Inspection API. Covers the WHOLE
    5000+ URL backlog over time (not just recently-published pages) --
    a URL confirmed `indexed: true` is excluded here regardless of age;
    a URL confirmed `indexed: false` is included here regardless of age.
    This is the part that satisfies "old AND new" URLs.
  Layer 2 (heuristic fallback): for any URL that workflow hasn't checked
    yet (the API's ~2000/day quota means a full sweep of the backlog takes
    several days), fall back to a PUBLICATION-AGE guess -- a page younger
    than FRESH_WINDOW_DAYS is treated as "probably not indexed yet" (new
    pages take days to get crawled). Self-cleans automatically: once a
    page ages past the window with no GSC data yet, it drops out on its
    own rather than lingering forever on a guess.

Layer 1 results always take priority (sorted first) since they're a real,
confirmed signal instead of a guess. Once gsc_index_state.json covers a
URL, that URL's fate stops depending on the age heuristic at all -- it
rotates on/off the homepage purely based on what Google actually reports.

Data sources (all already maintained elsewhere in the pipeline, no new
per-run state beyond what the GSC workflow itself writes):
  data/gsc_index_state.json -- {url_path: {indexed, verdict, lastChecked}}
  data/job-first-seen.json  -- {slug: "YYYY-MM-DD"} first-published date
  sections-index.json       -- {category_key: [{slug,name,...}, ...]}, used
                                to look up a real display title/category for
                                each candidate slug without re-reading every file

Output: data/unindexed_feed.json, consumed by generate_all.py's homepage
patch step on the NEXT run (same one-cycle-behind relationship
redirect-map.js/gone-map.js already have with their sources).
"""
import os
import re
import json
from datetime import date, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
FIRST_SEEN_PATH = os.path.join(ROOT, 'data', 'job-first-seen.json')
SECTIONS_INDEX_PATH = os.path.join(ROOT, 'sections-index.json')
GSC_STATE_PATH = os.path.join(ROOT, 'data', 'gsc_index_state.json')
OUT_PATH = os.path.join(ROOT, 'data', 'unindexed_feed.json')

FRESH_WINDOW_DAYS = 21   # a page older than this ages out of the feed
MAX_ITEMS = 70           # total featured links (spec asked for 50-100)

# sections-index.json buckets that are NOT recruitment postings -- tagged
# 'nonjob' so the homepage card can show a mixed, representative sample
# instead of being dominated by whichever category happens to publish most.
NONJOB_BUCKETS = {
    'SR_Result': 'Result',
    'SR_Admit_Card': 'Admit Card',
    'SR_Answer_Key': 'Answer Key',
    'ADMISSIONS': 'Admission',
    'Govt Scheme & Yojna': 'Yojana',
}


def _title_from_slug(slug):
    words = slug.replace('-', ' ').split()
    return ' '.join(w.upper() if w.isupper() or len(w) <= 3 and w.isalpha() else w.capitalize() for w in words)[:90]


def _category_label(bucket):
    # bucket keys look like '10TH_Pass', 'B_Tech_BE', 'ITI' -- plain .title()
    # mangles the digit-prefixed ones ('10TH Pass' -> '10Th Pass'), so keep
    # short/already-uppercase tokens as-is and only capitalize normal words.
    words = bucket.replace('_', ' ').split()
    return ' '.join(w if (w.isupper() or any(c.isdigit() for c in w)) else w.capitalize() for w in words)


def _interleave(jobs, nonjobs, cap):
    """Round-robin two lists so the result is a genuine job/non-job mix,
    not whichever bucket happens to have more candidates."""
    out = []
    ji, ni = 0, 0
    while len(out) < cap and (ji < len(jobs) or ni < len(nonjobs)):
        if ji < len(jobs):
            out.append(jobs[ji]); ji += 1
        if len(out) < cap and ni < len(nonjobs):
            out.append(nonjobs[ni]); ni += 1
    return out


def main():
    try:
        first_seen = json.load(open(FIRST_SEEN_PATH, encoding='utf-8'))
    except Exception:
        first_seen = {}

    try:
        sections_index = json.load(open(SECTIONS_INDEX_PATH, encoding='utf-8'))
    except Exception:
        sections_index = {}

    try:
        gsc_state = json.load(open(GSC_STATE_PATH, encoding='utf-8'))
    except Exception:
        gsc_state = {}

    # slug -> (title, type, category_label), built once from sections-index.json
    slug_info = {}
    for bucket, items in sections_index.items():
        if not isinstance(items, list):
            continue
        is_nonjob = bucket in NONJOB_BUCKETS
        label = NONJOB_BUCKETS.get(bucket, _category_label(bucket))
        for it in items:
            if not isinstance(it, dict):
                continue
            s = (it.get('slug') or '').strip()
            nm = (it.get('name') or '').strip()
            if not s or not nm or s in slug_info:
                continue
            slug_info[s] = (nm[:90], 'nonjob' if is_nonjob else 'job', label)

    def _entry_for(slug, url):
        info = slug_info.get(slug)
        if info:
            title, kind, cat_label = info
        else:
            # Not in sections-index (typically state-wise/education slugs) --
            # confirm the page genuinely exists before featuring it (mirrors
            # build_gone_map.py's "never point to a dead link" discipline),
            # then fall back to a slug-derived title.
            if not os.path.exists(os.path.join(ROOT, 'jobs', slug, 'index.html')):
                return None
            title, kind, cat_label = _title_from_slug(slug), 'job', 'Latest'
        return {'url': url, 'title': title, 'type': kind, 'category': cat_label}

    # ── Layer 1: real GSC-confirmed status, covers the whole backlog ──────
    gsc_indexed_urls = set()
    gsc_jobs, gsc_nonjobs = [], []
    skipped_missing_file = 0
    for url, rec in gsc_state.items():
        if not isinstance(rec, dict) or not isinstance(rec.get('indexed'), bool):
            continue
        if rec['indexed']:
            gsc_indexed_urls.add(url)
            continue
        slug = url.strip('/').split('/')[-1] if url.startswith('/jobs/') else ''
        if not slug:
            continue
        entry = _entry_for(slug, url)
        if not entry:
            skipped_missing_file += 1
            continue
        entry['source'] = 'gsc'
        (gsc_nonjobs if entry['type'] == 'nonjob' else gsc_jobs).append(entry)
    # oldest-checked first within each bucket (most overdue for a recheck
    # already got the priority slot in gsc_check_index_status.js -- keep
    # that same ordering here so the homepage matches the check queue)
    gsc_jobs.sort(key=lambda x: gsc_state.get(x['url'], {}).get('lastChecked', ''))
    gsc_nonjobs.sort(key=lambda x: gsc_state.get(x['url'], {}).get('lastChecked', ''))
    layer1 = _interleave(gsc_jobs, gsc_nonjobs, MAX_ITEMS)
    layer1_urls = {it['url'] for it in layer1}

    # ── Layer 2: publication-age fallback for anything GSC hasn't checked ─
    today = date.today()
    age_jobs, age_nonjobs = [], []
    remaining = MAX_ITEMS - len(layer1)
    if remaining > 0:
        for slug, seen_str in first_seen.items():
            url = f'/jobs/{slug}/'
            if url in gsc_indexed_urls or url in layer1_urls:
                continue  # real GSC signal already decided this one either way
            try:
                seen_dt = datetime.strptime(seen_str, '%Y-%m-%d').date()
            except Exception:
                continue
            age_days = (today - seen_dt).days
            if age_days < 0 or age_days > FRESH_WINDOW_DAYS:
                continue
            entry = _entry_for(slug, url)
            if not entry:
                skipped_missing_file += 1
                continue
            entry['source'] = 'age_heuristic'
            entry['age_days'] = age_days
            (age_nonjobs if entry['type'] == 'nonjob' else age_jobs).append(entry)
        age_jobs.sort(key=lambda x: x['age_days'])
        age_nonjobs.sort(key=lambda x: x['age_days'])
    layer2 = _interleave(age_jobs, age_nonjobs, remaining)

    items = (layer1 + layer2)[:MAX_ITEMS]

    out = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'window_days': FRESH_WINDOW_DAYS,
        'gsc_checked_urls': len(gsc_state),
        'count': len(items),
        'items': items,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

    print(
        f'[unindexed-feed] GSC state covers {len(gsc_state)} URLs '
        f'({len(gsc_indexed_urls)} confirmed indexed, {len(gsc_jobs) + len(gsc_nonjobs)} confirmed un-indexed). '
        f'Layer 1 (real GSC): {len(layer1)} items. Layer 2 (age<={FRESH_WINDOW_DAYS}d fallback): {len(layer2)} items '
        f'({skipped_missing_file} candidates skipped as missing-file). '
        f'-> {len(items)} written to data/unindexed_feed.json'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
