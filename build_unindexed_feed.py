#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_unindexed_feed.py — pick a rotating batch of recently-published pages
to feature on the homepage, to get them crawled/indexed faster.

WHY NOT THE REAL GSC INDEX STATUS: the ask was to check Search Console's
URL Inspection API and only feature genuinely un-indexed URLs. That API
needs OAuth/service-account credentials this repo doesn't have configured,
and its quota (~2000 requests/day/property) isn't enough to status-check
the site's full page count on every run anyway. Substituting a PUBLICATION
-AGE heuristic instead: a page younger than FRESH_WINDOW_DAYS is treated as
"probably not indexed yet" (new pages take days to get crawled), which
needs no external API and self-cleans automatically -- once a page ages
past the window it drops out of the feed on its own (either it got
indexed, in which case great, or it didn't and continuing to feature it
forgone isn't buying anything further).

If real GSC Inspection API data ever gets wired up (service-account JSON as
a repo secret), the natural upgrade point is here: prefer an explicit
`indexed: true/false` field when present for a slug, falling back to the
age heuristic only when it's missing.

Data sources (both already maintained by generate_all.py, no new state):
  data/job-first-seen.json  -- {slug: "YYYY-MM-DD"} first-published date
  sections-index.json       -- {category_key: [{slug,name,...}, ...]}, used
                                to look up a real display title/category for
                                each fresh slug without re-reading every file

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


def main():
    try:
        first_seen = json.load(open(FIRST_SEEN_PATH, encoding='utf-8'))
    except Exception:
        print('[unindexed-feed] no job-first-seen.json yet, nothing to do')
        first_seen = {}

    try:
        sections_index = json.load(open(SECTIONS_INDEX_PATH, encoding='utf-8'))
    except Exception:
        sections_index = {}

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

    today = date.today()
    jobs, nonjobs = [], []
    skipped_missing_file = 0

    for slug, seen_str in first_seen.items():
        try:
            seen_dt = datetime.strptime(seen_str, '%Y-%m-%d').date()
        except Exception:
            continue
        age_days = (today - seen_dt).days
        if age_days < 0 or age_days > FRESH_WINDOW_DAYS:
            continue

        info = slug_info.get(slug)
        if info:
            title, kind, cat_label = info
        else:
            # Not in sections-index (typically state-wise/education slugs) --
            # confirm the page genuinely exists before featuring it (mirrors
            # build_gone_map.py's "never point to a dead link" discipline),
            # then fall back to a slug-derived title.
            if not os.path.exists(os.path.join(ROOT, 'jobs', slug, 'index.html')):
                skipped_missing_file += 1
                continue
            title, kind, cat_label = _title_from_slug(slug), 'job', 'Latest'

        entry = {
            'url': f'/jobs/{slug}/',
            'title': title,
            'type': kind,
            'category': cat_label,
            'age_days': age_days,
        }
        (nonjobs if kind == 'nonjob' else jobs).append(entry)

    # freshest-first within each bucket
    jobs.sort(key=lambda x: x['age_days'])
    nonjobs.sort(key=lambda x: x['age_days'])

    # round-robin interleave so the featured set is a genuine mix, not
    # whichever bucket happens to have the most candidates
    items = []
    ji, ni = 0, 0
    while len(items) < MAX_ITEMS and (ji < len(jobs) or ni < len(nonjobs)):
        if ji < len(jobs):
            items.append(jobs[ji]); ji += 1
        if len(items) < MAX_ITEMS and ni < len(nonjobs):
            items.append(nonjobs[ni]); ni += 1

    out = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'window_days': FRESH_WINDOW_DAYS,
        'count': len(items),
        'items': items,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

    print(
        f'[unindexed-feed] {len(jobs)} fresh job candidates, {len(nonjobs)} fresh non-job '
        f'candidates (window={FRESH_WINDOW_DAYS}d, {skipped_missing_file} skipped as missing-file) '
        f'-> {len(items)} written to data/unindexed_feed.json'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
