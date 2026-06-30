#!/usr/bin/env python3
"""
scripts/inject_dynamic_headings.py
==================================
Retroactive migration: rewrite generic section <h2> headings on EXISTING built
job pages into dynamic, keyword-rich "[Job Title core] : [Context]" headings —
matching exactly what generate_all.py now emits for freshly-built pages.

Why this exists
---------------
generate_all.py regenerates every page whose job is still in
Complete_Jobs_Full_Data.json (TEMPLATE_VERSION bump forces a full rewrite).
But ORPHAN pages on disk — slugs that changed, or jobs removed from the JSON —
are never touched by the generator. This script gives those legacy pages the
same dynamic headings, and doubles as an idempotent safety net.

Why regex, NOT BeautifulSoup
----------------------------
BeautifulSoup re-serializes the whole document (whitespace, attribute order,
self-closing tags), which would silently mutate the exact byte sequences that
ai_html_enricher.py depends on: the `<!-- TSJ_AI_BLOCK_START/END -->` and
`<!-- TSJ_HASH:... -->` markers and the `sec-card`/`sec-head` class strings.
This script only swaps the inner text of <h2> elements inside <div class=
"sec-head"> and leaves every other byte untouched.

Safety guarantees
-----------------
- Only rewrites <h2> whose text EXACTLY matches a known generic section label.
- NEVER touches <h2>s inside a TSJ_AI_BLOCK region (AI-patched headings).
- Idempotent: a heading already containing ' : ' is left alone.
- Dry-run by default; writes only with --apply (atomic .tmp replace).

Usage:
  python scripts/inject_dynamic_headings.py            # dry run
  python scripts/inject_dynamic_headings.py --apply
  python scripts/inject_dynamic_headings.py --apply --verbose
"""

import re, sys, os, glob
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
APPLY   = '--apply' in sys.argv
VERBOSE = '--verbose' in sys.argv

# Generic SECTION_META label  →  dynamic suffix (must match generate_all.py _DYN_HEADING)
GENERIC_TO_SUFFIX = {
    'Job Overview':                 'Job Overview',
    'Important Dates':              'Important Dates & Timelines',
    'Application Fee':              'Application Fee Details',
    'Age Limit':                    'Age Limit',
    'Qualification / Eligibility':  'Eligibility & Qualification',
    'Vacancy Details':              'Vacancy Details',           # count appended below if found
    'Subject-wise Vacancy':         'Subject-wise Vacancy Details',
    'Category-wise Vacancy':        'Category-wise Vacancy Details',
    'Category Wise Vacancy Details': 'Category-wise Vacancy Details',
    'Salary & Pay Scale':           'Salary Details & Pay Scale',
    'Salary &amp; Pay Scale':       'Salary Details & Pay Scale',
    'Selection Process':            'Selection Process & Exam Pattern',
    'Exam Pattern':                 'Exam Pattern',
    'Syllabus':                     'Syllabus',
    'Physical Eligibility':         'Physical Eligibility',
    'How to Apply':                 'How to Apply Online Step-by-Step',
    'Important Instructions':       'Important Instructions',
    'Important Links':              'Important Links & Notification PDF',
    'FAQs':                         'Frequently Asked Questions (FAQ)',
}

_AI_START = '<!-- TSJ_AI_BLOCK_START -->'
_AI_END   = '<!-- TSJ_AI_BLOCK_END -->'

# <div class="sec-head" ...> ... <h2>HEADING</h2>
SEC_HEAD_H2 = re.compile(
    r'(<div class="sec-head"[^>]*>.*?<h2>)(.*?)(</h2>)', re.DOTALL)

H1_RE    = re.compile(r'<h1[^>]*class="[^"]*detail-h1[^"]*"[^>]*>(.*?)</h1>', re.DOTALL)
TITLE_RE = re.compile(r'<title>(.*?)</title>', re.DOTALL)

_HEADING_TITLE_TAIL = re.compile(
    r'\s*[-–—:]\s*(apply online|apply offline|apply now|walk[\s-]?in|notification out|'
    r'last date|online form|short notice|recruitment notification).*$', re.I)

def _seo_heading_title(raw_title):
    """Same trimming logic as generate_all.py _seo_heading_title()."""
    t = re.sub(r'<[^>]+>', '', raw_title or '').strip()
    t = re.sub(r'\s*\|\s*Top Sarkari Jobs\s*$', '', t, flags=re.I).strip()
    if not t:
        return ''
    t = _HEADING_TITLE_TAIL.sub('', t).strip()
    t = re.sub(r'\s+for\s+\d[\d,]*\s+.*$', '', t, flags=re.I).strip()
    t = re.sub(r'\s+(notification out|notification|online form|apply online|'
               r'short notice|out)\s*$', '', t, flags=re.I).strip()
    if len(t) > 58:
        t = t[:58].rsplit(' ', 1)[0].rstrip(' ,;:-–(')
    return t

def _ai_spans(html):
    """Return list of (start,end) char ranges covering TSJ_AI_BLOCK regions."""
    spans = []
    pos = 0
    while True:
        s = html.find(_AI_START, pos)
        if s == -1:
            break
        e = html.find(_AI_END, s)
        if e == -1:
            spans.append((s, len(html))); break
        spans.append((s, e + len(_AI_END)))
        pos = e + len(_AI_END)
    return spans

def _vacancy_total(html):
    """Best-effort: pull the grand-total from a vacancy total row for the count."""
    m = re.search(r'<tr class="vac-tot">.*?<strong>\s*(\d[\d,]*)\s*</strong>\s*</td>\s*</tr>',
                  html, re.DOTALL)
    if m:
        return re.sub(r'[^\d,]', '', m.group(1))
    return ''

stats = {'scanned': 0, 'migrated': 0, 'headings': 0, 'already': 0, 'no_title': 0, 'errors': 0}

def migrate(html, path):
    raw_title = ''
    m = H1_RE.search(html)
    if m:
        raw_title = m.group(1)
    elif TITLE_RE.search(html):
        raw_title = TITLE_RE.search(html).group(1)
    title = _seo_heading_title(raw_title)
    if not title:
        stats['no_title'] += 1
        return html, 0

    ai_spans = _ai_spans(html)
    def _in_ai(pos):
        return any(a <= pos < b for a, b in ai_spans)

    vac_total = _vacancy_total(html)
    changed = [0]

    def _repl(mt):
        head_open, heading, head_close = mt.group(1), mt.group(2).strip(), mt.group(3)
        # skip AI-block headings
        if _in_ai(mt.start()):
            return mt.group(0)
        # already dynamic
        if ' : ' in heading:
            return mt.group(0)
        suffix = GENERIC_TO_SUFFIX.get(heading)
        if not suffix:
            return mt.group(0)
        if heading in ('Vacancy Details',):
            suffix = (f'Vacancy Details Total : {vac_total} Posts'
                      if vac_total else 'Vacancy Details & Eligibility')
        new_heading = f'{title} : {suffix}'
        # re-encode the ampersand the way the page already encodes entities
        new_heading = new_heading.replace('&', '&amp;')
        changed[0] += 1
        return head_open + new_heading + head_close

    new_html = SEC_HEAD_H2.sub(_repl, html)
    return new_html, changed[0]

# ── Main ─────────────────────────────────────────────────────────────────────
pages = sorted(glob.glob(str(ROOT / 'jobs' / '*' / 'index.html')))
print(f"{'[DRY RUN] ' if not APPLY else ''}Scanning {len(pages)} job pages…")

for fpath in pages:
    stats['scanned'] += 1
    try:
        original = open(fpath, encoding='utf-8', errors='replace').read()
    except Exception as ex:
        print(f'  ERROR reading {fpath}: {ex}'); stats['errors'] += 1; continue

    new_html, n = migrate(original, fpath)
    if n == 0:
        stats['already'] += 1
        continue
    stats['migrated'] += 1
    stats['headings'] += n
    if VERBOSE or not APPLY:
        slug = fpath.split(os.sep)[-2]
        print(f"  {'WOULD FIX' if not APPLY else 'FIXED'} [{slug[:55]}]: {n} headings")
    if APPLY and new_html != original:
        try:
            tmp = Path(fpath).with_suffix('.tmp')
            tmp.write_text(new_html, encoding='utf-8')
            tmp.replace(fpath)
        except Exception as ex:
            print(f'  ERROR writing {fpath}: {ex}'); stats['errors'] += 1

print()
print('=' * 60)
print(f"  Pages scanned      : {stats['scanned']}")
print(f"  Pages migrated     : {stats['migrated']}")
print(f"  Headings rewritten : {stats['headings']}")
print(f"  Already dynamic/skip: {stats['already']}")
print(f"  No title found     : {stats['no_title']}")
print(f"  Errors             : {stats['errors']}")
if not APPLY:
    print("\n  DRY RUN — no files written. Run with --apply to migrate.")
print('=' * 60)
