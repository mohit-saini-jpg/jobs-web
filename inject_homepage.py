#!/usr/bin/env python3
"""C1 FIX: server-render the homepage's "Latest Jobs" ticker and "Today's
Updates" widget into the static index.html at build time, so a non-JS crawler
(and Google's first wave) sees real <a> links + job titles instead of
"Loading latest jobs…" / "Loading latest updates...".

The existing client-side JS still runs after load and refreshes/replaces these
blocks for interactivity — this only guarantees the INITIAL HTML has real
content. Run this AFTER generate_all.py / generate_website.py, as the final
build step.

Idempotent: re-running replaces the previously-injected block, never stacks.
"""
import json
import re
import os
import html as _html

ROOT = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ROOT, 'index.html')
SECTIONS_INDEX = os.path.join(ROOT, 'sections-index.json')
DAILY = os.path.join(ROOT, 'dailyupdates.json')

TICKER_N = 15      # jobs in the live ticker
TODAY_N = 8        # items in Today's Updates sidebar


def esc(s):
    return _html.escape(str(s or ''), quote=True)


def load_latest_jobs():
    """Top-N latest jobs from sections-index.json (same source the ticker JS
    uses), de-duplicated by slug, preserving insertion order."""
    try:
        data = json.load(open(SECTIONS_INDEX, encoding='utf-8'))
    except Exception:
        return []
    jobs, seen = [], set()
    # iterate categories in order; pull jobs round-robin-ish (just in order)
    for cat, items in data.items():
        if not isinstance(items, list):
            continue
        for it in items:
            slug = (it or {}).get('slug', '')
            name = (it or {}).get('name', '')
            if not slug or not name or slug in seen:
                continue
            seen.add(slug)
            jobs.append({'slug': slug, 'name': name, 'date': it.get('date', '')})
            if len(jobs) >= TICKER_N:
                return jobs
    return jobs


def load_today_updates():
    """Top-N items from the 'Today Updates' section of dailyupdates.json."""
    try:
        data = json.load(open(DAILY, encoding='utf-8'))
    except Exception:
        return []
    for sec in data.get('sections', []):
        sid = (sec.get('id', '') + sec.get('title', '')).lower()
        if 'today' in sid:
            out = []
            for it in (sec.get('items') or [])[:TODAY_N]:
                name = (it or {}).get('name', '')
                url = (it or {}).get('url', '') or '/section/today-updates/'
                if name:
                    out.append({'name': name, 'url': url})
            return out
    return []


# ── markers so re-runs replace, never stack ──
TICKER_START = '<!-- SSR-TICKER-START -->'
TICKER_END = '<!-- SSR-TICKER-END -->'
TODAY_START = '<!-- SSR-TODAY-START -->'
TODAY_END = '<!-- SSR-TODAY-END -->'


def build_ticker_html(jobs):
    if not jobs:
        return ''
    spans = ''.join(
        f'<a class="ticker-item" href="/jobs/{esc(j["slug"])}/">'
        f'<i class="fa-solid fa-bolt" aria-hidden="true"></i> {esc(j["name"])}</a>'
        for j in jobs
    )
    return f'{TICKER_START}{spans}{TICKER_END}'


def build_today_html(items):
    if not items:
        return ''
    links = ''.join(
        f'<a href="{esc(it["url"])}"><i class="fa-solid fa-bolt" style="color:var(--red);"></i>'
        f'<span>{esc(it["name"])}</span><i class="fa-solid fa-chevron-right arrow"></i></a>'
        for it in items
    )
    return f'{TODAY_START}{links}{TODAY_END}'


def inject():
    html = open(INDEX, encoding='utf-8').read()
    orig = html

    # 1) Ticker: replace the loading span (or a previously-injected block)
    jobs = load_latest_jobs()
    ticker = build_ticker_html(jobs)
    if ticker:
        # remove any prior injected block first (idempotent)
        html = re.sub(re.escape(TICKER_START) + r'.*?' + re.escape(TICKER_END),
                      '', html, flags=re.S)
        # replace the loading placeholder span
        html = re.sub(
            r'<span class="ticker-loading"[^>]*>Loading latest jobs…</span>',
            ticker, html, count=1)
        # if placeholder already gone (re-run), insert after ticker-track open
        if TICKER_START not in html:
            html = re.sub(r'(<div class="ticker-track" id="tickerTrack">)',
                          r'\1' + ticker, html, count=1)

    # 2) Today's Updates: replace the loading link
    today = load_today_updates()
    today_html = build_today_html(today)
    if today_html:
        html = re.sub(re.escape(TODAY_START) + r'.*?' + re.escape(TODAY_END),
                      '', html, flags=re.S)
        html = re.sub(
            r'<a href="/section/today-updates/"><i class="fa-solid fa-bolt"[^>]*>'
            r'</i><span>Loading latest updates\.\.\.</span>'
            r'<i class="fa-solid fa-chevron-right arrow"></i></a>',
            today_html, html, count=1)
        if TODAY_START not in html:
            html = re.sub(r'(<div class="sec-list" id="today-sidebar-list">)',
                          r'\1' + today_html, html, count=1)

    if html != orig:
        open(INDEX, 'w', encoding='utf-8').write(html)
        print(f"injected: ticker={len(jobs)} jobs, today={len(today)} updates")
    else:
        print("no changes (placeholders not found or no data)")


if __name__ == '__main__':
    inject()
