#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_chat_index.py — lightweight search index for the TSJ AI chat widget.

Complete_Jobs_Full_Data.json is ~40MB — far too big to fetch/parse in a
browser (especially on mobile). This produces chat-search-index.json: just
{title, org, category, date, url} per item across sarkari_data, the FJA
unified feed and education_jobs — a few MB at most — which the widget loads
once, caches, and fuzzy-searches locally (Fuse.js) before ever calling the
AI backend, so most "does this job exist" questions never need a network
round-trip to answer.

Run from repo root:  python3 scripts/build_chat_index.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = 'https://www.topsarkarijobs.com'


def _norm_slug(s):
    s = str(s or '').strip().lower()
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')[:80].strip('-')


def slugify(text):
    text = str(text or '').lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:80] or 'job'


def canonical_slug(job, title):
    """Mirrors get_canonical_slug()'s Priority 1/2 (direct fields) — the
    registry-dependent Priority 3 fallback is intentionally not replicated
    here (this index is best-effort search context, not the page generator;
    a rare mismatched link is an acceptable trade-off for staying a simple,
    self-contained script)."""
    cs = str(job.get('_canonical_slug') or '').strip()
    if cs:
        return _norm_slug(cs)
    raw = str(job.get('slug') or '').strip()
    if raw:
        raw = re.sub(r'^sr_[a-z_]+-', '', raw)
        m = re.search(r'-([0-9a-f]{6,8})$', raw)
        if m and not m.group(1).isdigit():
            raw = raw[:-len(m.group(0))]
        s = _norm_slug(raw)
        if s:
            return s
    return slugify(title)


def norm_date(d):
    d = str(d or '').strip()
    if not d:
        return ''
    m = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})', d)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', d)
    return d[:10] if m else d[:20]


def main():
    cj_path = os.path.join(ROOT, 'Complete_Jobs_Full_Data.json')
    if not os.path.exists(cj_path):
        cj_path = os.path.join(ROOT, 'data', 'Complete_Jobs_Full_Data.json')
    if not os.path.exists(cj_path):
        print('Complete_Jobs_Full_Data.json not found — skipping chat index build')
        return

    with open(cj_path, encoding='utf-8') as f:
        cj = json.load(f)

    _disk_slugs = set()
    jobs_dir = os.path.join(ROOT, 'jobs')
    if os.path.isdir(jobs_dir):
        _disk_slugs = set(os.listdir(jobs_dir))

    seen_slugs = set()
    out = []

    def add(title, org, category, date, slug):
        if not title or not slug:
            return
        if _disk_slugs and slug not in _disk_slugs:
            return  # never index a link that 404s
        if slug in seen_slugs:
            return
        seen_slugs.add(slug)
        out.append({
            't': title[:160],
            'o': (org or '')[:100],
            'c': (category or '')[:60],
            'd': norm_date(date),
            'u': f'/jobs/{slug}/',
        })

    # sarkari_data.jobs
    for j in (cj.get('sarkari_data', {}) or {}).get('jobs', []) or []:
        title = str(j.get('title', '')).strip()
        if not title:
            continue
        slug = canonical_slug(j, title)
        date = j.get('important_dates', {}).get('last_date', '') if isinstance(j.get('important_dates'), dict) else ''
        add(title, j.get('organization', ''), j.get('category', ''), date or j.get('postDate', ''), slug)

    # freejobalert_unified.deduped_jobs
    for j in (cj.get('freejobalert_unified', {}) or {}).get('deduped_jobs', []) or []:
        bd = j.get('basic_details', {}) or {}
        title = str(bd.get('job_title', '')).strip()
        if not title:
            continue
        slug = canonical_slug(j, title)
        imp = j.get('important_dates', {}) or {}
        date = imp.get('last_date_to_apply', '') or imp.get('last_date', '')
        add(title, bd.get('organization_name', ''), j.get('category', ''), date, slug)

    # education_jobs.sections[].items[]
    for sec in (cj.get('education_jobs', {}) or {}).get('sections', []) or []:
        cat = sec.get('category', '') or sec.get('title', '')
        for it in sec.get('items', []) or []:
            title = str(it.get('name', '') or it.get('title', '')).strip()
            if not title:
                continue
            slug = canonical_slug(it, title)
            add(title, it.get('organization', ''), cat, it.get('postDate', '') or it.get('date', ''), slug)

    out_path = os.path.join(ROOT, 'chat-search-index.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'chat-search-index.json: {len(out)} items ({os.path.getsize(out_path)/1024:.0f} KB)')


if __name__ == '__main__':
    main()
