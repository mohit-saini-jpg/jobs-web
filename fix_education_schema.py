#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_education_schema.py — replace the (semantically wrong) JobPosting schema on
legacy /education/ informational pages with a proper NewsArticle.

/education/ pages are Admit Cards, Results, Answer Keys, Exam Dates, Admissions,
Cutoffs — NOT job postings. A JobPosting schema on them is incorrect (and generates
Google "Job Postings" field warnings). NewsArticle is the correct, warning-free,
crawl-friendly type for this news/informational content (datePublished/dateModified
help Google crawl freshness).

Only /education/ pages are touched. /jobs/ and /state/ pages (real recruitment)
keep their JobPosting. Idempotent — skips pages that already have no JobPosting.

The active generator (generate_all.py -> build_schemas) already emits the correct
intent-based schema (Event for admit cards, Article for answer keys, etc.) for
newly generated pages; this backfills the older stale /education/ pages.
"""
import os
import re
import sys
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://www.topsarkarijobs.com"
EDU_DIR = os.path.join(ROOT, "education")
_PUBLISHER = {
    "@type": "Organization",
    "name": "Top Sarkari Jobs",
    "url": BASE_URL + "/",
    "logo": {"@type": "ImageObject", "url": BASE_URL + "/image.webp"},
}
_LDJSON_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
_CANON_RE = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)
_DATEONLY_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _iso_dt(d):
    """Full ISO-8601 with IST timezone so Google never flags missing timezone."""
    d = (d or '').strip()
    if not d:
        return ''
    if _DATEONLY_RE.match(d):
        return d + 'T00:00:00+05:30'
    m = re.match(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?)$', d)
    if m:
        return d + '+05:30'
    return d


def _meta(html, key):
    for pat in (r'<meta[^>]+(?:property|name)="' + re.escape(key) + r'"[^>]+content="([^"]*)"',
                r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="' + re.escape(key) + r'"'):
        m = re.search(pat, html, re.I)
        if m:
            return m.group(1)
    return ''


def _newsarticle_from(jp, html, canon):
    title = (jp.get('title') if isinstance(jp, dict) else '') or _meta(html, 'og:title') \
        or re.sub(r'<[^>]+>', '', (re.search(r'<title>(.*?)</title>', html, re.S) or [None, ''])[1])
    title = re.sub(r'\s*\|\s*Top Sarkari Jobs.*$', '', title).strip()
    desc = (jp.get('description') if isinstance(jp, dict) else '') or _meta(html, 'description') \
        or _meta(html, 'og:description')
    dp = (jp.get('datePosted') if isinstance(jp, dict) else '') or _meta(html, 'article:published_time')
    dm = _meta(html, 'article:modified_time') or dp
    img = _meta(html, 'og:image') or (BASE_URL + '/og-jobs.png')
    url = canon or (jp.get('url', '') if isinstance(jp, dict) else '') or ''
    art = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title[:110],
        "image": [img],
        "author": _PUBLISHER,
        "publisher": _PUBLISHER,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "url": url,
    }
    if desc:
        art["description"] = desc[:300]
    dp = _iso_dt(dp)
    dm = _iso_dt(dm) or dp
    if dp:
        art["datePublished"] = dp
        art["dateModified"] = dm or dp
    return art


def convert_file(path):
    try:
        html = open(path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return False
    if 'JobPosting' not in html:
        return False
    canon_m = _CANON_RE.search(html)
    canon = canon_m.group(1) if canon_m else ''
    new_html = html
    changed = False
    for m in _LDJSON_RE.finditer(html):
        body = m.group(2)
        if 'JobPosting' not in body:
            continue
        try:
            data = json.loads(body)
        except Exception:
            continue
        # Only convert blocks whose PRIMARY object is a JobPosting (skip @graph mixes
        # that also legitimately carry other types — education pages are standalone).
        is_jp = (isinstance(data, dict) and data.get('@type') == 'JobPosting')
        if not is_jp:
            continue
        art = _newsarticle_from(data, html, canon)
        replacement = m.group(1) + json.dumps(art, ensure_ascii=False, separators=(',', ':')) + m.group(3)
        new_html = new_html.replace(m.group(0), replacement, 1)
        changed = True
    if changed and new_html != html:
        open(path, 'w', encoding='utf-8').write(new_html)
        return True
    return False


def main():
    if not os.path.isdir(EDU_DIR):
        print("[edu-schema] no /education/ dir — nothing to do.")
        return 0
    converted = scanned = 0
    for root, _, files in os.walk(EDU_DIR):
        for f in files:
            if not f.endswith('.html'):
                continue
            scanned += 1
            if convert_file(os.path.join(root, f)):
                converted += 1
                if converted <= 5:
                    print("  JobPosting->NewsArticle:", os.path.relpath(os.path.join(root, f), ROOT))
    print(f"\n[edu-schema] scanned {scanned} /education/ pages, converted {converted}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
