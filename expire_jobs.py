#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
expire_jobs.py — mark job postings whose validThrough has passed as closed
on the VISIBLE page (never touches schema or job data).

WHY THIS EXISTS
---------------
This site deliberately never deletes or 410s an expired job page (see the
comment in .github/workflows/auto-update-jobs.yml: deleting a page whose
last-date passed 404'd already-indexed URLs and cost organic traffic, so
generate_all.py overwrites expired jobs in place and keeps them live). But
leaving a live "Apply Online" call-to-action next to a deadline that has
already passed is misleading to a reader landing on the page. This script
finds pages where JobPosting.validThrough is in the past AND the page still
shows the live apply-CTA, and replaces just that CTA with a visible
"Applications Closed" notice.

It does NOT touch validThrough, JobPosting @type, or any job data field.
validThrough is already accurate (that IS how expiry is detected here), and
Google's Job Search feature already stops surfacing a listing once
validThrough passes — there's nothing to "fix" in the schema without
guessing at data we don't have. This only fixes what a human reader sees.

Idempotent: a second run makes zero changes (skips pages already marked
via the data-tsj-applications-closed marker).

USAGE
    python expire_jobs.py                 # audit (read-only)
    python expire_jobs.py --fix           # apply fixes
    python expire_jobs.py --fix <substr>  # only paths containing <substr>
"""
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
SCAN_DIRS = ("jobs", "state", "education")

_VALIDTHROUGH_RE = re.compile(r'"validThrough"\s*:\s*"(\d{4}-\d{2}-\d{2})')
_JOBPOSTING_MARKERS = ('"@type": "JobPosting"', '"@type":"JobPosting"')
_APPLY_CTA_RE = re.compile(r'<a\b[^>]*\bclass="apply-cta"[^>]*>.*?</a>', re.S)
_CLOSED_MARKER = 'data-tsj-applications-closed'

CLOSED_HTML = (
    '<div class="notice closed-notice" ' + _CLOSED_MARKER + '="1">'
    '<i class="fa-solid fa-circle-xmark"></i> '
    '<span><strong>Applications Closed:</strong> The last date to apply for this '
    'recruitment has passed. This page is kept for reference — check the official '
    'website for any newer notification.</span></div>'
)


def iter_pages(only=None):
    for base in SCAN_DIRS:
        for root, _dirs, files in os.walk(os.path.join(ROOT, base)):
            if 'index.html' not in files:
                continue
            fp = os.path.join(root, 'index.html')
            if only and only not in fp:
                continue
            yield fp


def get_valid_through(html):
    m = _VALIDTHROUGH_RE.search(html)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def is_expired_and_open(html, today=None):
    """True only if this page has a JobPosting with a past validThrough AND
    still shows the live apply CTA -- i.e. there's actually something to fix."""
    if not any(mk in html for mk in _JOBPOSTING_MARKERS):
        return False
    if _CLOSED_MARKER in html:
        return False  # already fixed
    vt = get_valid_through(html)
    if vt is None:
        return False
    if vt >= (today or date.today()):
        return False
    return bool(_APPLY_CTA_RE.search(html))


def close_page(html):
    return _APPLY_CTA_RE.sub(CLOSED_HTML, html, count=1)


def main():
    args = sys.argv[1:]
    fix = '--fix' in args
    only = next((a for a in args if a != '--fix'), None)

    scanned = matched = fixed = 0
    examples = []
    for fp in iter_pages(only):
        scanned += 1
        try:
            with open(fp, encoding='utf-8', errors='ignore') as f:
                html = f.read()
        except Exception:
            continue
        if not is_expired_and_open(html):
            continue
        matched += 1
        if len(examples) < 15:
            examples.append(os.path.relpath(fp, ROOT))
        if fix:
            new_html = close_page(html)
            if new_html != html:
                with open(fp, 'w', encoding='utf-8') as f:
                    f.write(new_html)
                fixed += 1

    print(f"scanned: {scanned}")
    print(f"expired + still showing live apply CTA: {matched}")
    if fix:
        print(f"fixed: {fixed}")
    else:
        print("(dry run -- pass --fix to apply)")
    print("examples:")
    for ex in examples:
        print(" ", ex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
