#!/usr/bin/env python3
"""
scripts/fix_ai_duplication.py
==============================
One-time + safe-to-re-run cleanup for AI content duplication in built HTML files.

Problem:
  Old patch_ai_html.py injected AI sections (Overview, Expert Analysis, FAQs…)
  WITHOUT sentinel markers. The generator's SECTION_ORDER then ALSO rendered:
    - "Job Overview" (basic_details)  → visual duplicate of AI "Overview"
    - "FAQs"                          → true duplicate of AI-injected FAQs

  Also: pages built by old generator have no TSJ_AI_BLOCK_START/END sentinels,
  so future patch_ai_html.py runs re-inject, creating duplicates again.

Fix applied per page:
  1. Duplicate FAQs  → remove the SECOND (raw JSON) FAQs <section> entirely
  2. Stale "All Official Links" section → remove (now merged into Important Links)
  3. AI sections without sentinels → wrap in TSJ_AI_BLOCK_START/END
  4. Already-correct pages (has sentinels, no dups) → skip

Usage:
  python scripts/fix_ai_duplication.py             # dry run by default
  python scripts/fix_ai_duplication.py --apply     # write files
  python scripts/fix_ai_duplication.py --apply --verbose
"""

import re, sys, os, glob
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
APPLY   = '--apply' in sys.argv
VERBOSE = '--verbose' in sys.argv

# ── Sentinel constants (must match generate_all.py / patch_ai_html.py) ───────
_AI_BLOCK_START = '<!-- TSJ_AI_BLOCK_START -->'
_AI_BLOCK_END   = '<!-- TSJ_AI_BLOCK_END -->'
_AI_FAQ_START   = '<!-- TSJ_AI_FAQ_START -->'
_AI_FAQ_END     = '<!-- TSJ_AI_FAQ_END -->'

# Regex: one full <section class="sec-card">…</section> (non-greedy, DOTALL)
SEC_RE = re.compile(r'<section class="sec-card">.*?</section>', re.DOTALL)
H2_RE  = re.compile(r'<h2>([^<]+)</h2>')

# AI section headings injected by old patch_ai_html.py
AI_HEADINGS = {
    'Overview', 'Expert Analysis', 'Who Should Apply',
    'Preparation Tips', 'Salary Insights', 'Job Profile', 'Selection Strategy',
}
# HTML attributes that appear ONLY in AI sec-cards (gradient colours)
AI_GRADIENTS = re.compile(
    r'background:linear-gradient\(135deg,#(?:1d4ed8|7c3aed|0f766e|047857|b45309|475569|be123c)'
)

# DON'T MISS sidebar widget text leaked into qualification/details fields
# Matches the HTML-escaped form (<li>DON&#x27;T MISS...) or raw form
_DONT_MISS_LI = re.compile(
    r'<li>DON(?:&#x27;|&apos;|\'|’|‘)?T\s+MISS.*?</li>',
    re.DOTALL | re.IGNORECASE
)

# ── Stats ─────────────────────────────────────────────────────────────────────
stats = {'scanned': 0, 'already_ok': 0, 'dup_faq_fixed': 0,
         'aol_removed': 0, 'sentinel_added': 0, 'dont_miss_fixed': 0,
         'written': 0, 'errors': 0}


def fix_page(html: str, path: str) -> tuple[str, list]:
    """Return (new_html, list_of_changes) or (html, []) if nothing changed."""
    changes = []

    # ── 0. Remove DON'T MISS leaked sidebar text from <li> items ─────────────
    new_html = _DONT_MISS_LI.sub('', html)
    if new_html != html:
        html = new_html
        changes.append("removed DON'T MISS sidebar text from list items")

    # ── 1. Remove duplicate FAQs ─────────────────────────────────────────────
    # Count all FAQs section cards
    faq_secs = [(m.start(), m.end()) for m in SEC_RE.finditer(html)
                if H2_RE.search(m.group(0)) and
                   re.search(r'<h2>FAQs</h2>', m.group(0))]

    if len(faq_secs) >= 2:
        # AI-injected FAQ section comes FIRST; raw JSON FAQ comes LATER.
        # Keep the first; remove subsequent ones.
        # Build new HTML by excising all but the first FAQs section.
        new_html = html
        # Remove from last to first so positions don't shift
        for start, end in reversed(faq_secs[1:]):
            new_html = new_html[:start] + new_html[end:]
        if new_html != html:
            html = new_html
            changes.append(f'removed {len(faq_secs)-1} duplicate FAQs section(s)')

    # ── 2. Remove stale "All Official Links" section ──────────────────────────
    # (These are now merged into Important Links by the new generator)
    aol_secs = [(m.start(), m.end()) for m in SEC_RE.finditer(html)
                if re.search(r'<h2>All Official Links</h2>', m.group(0))]
    if aol_secs:
        new_html = html
        for start, end in reversed(aol_secs):
            new_html = new_html[:start] + new_html[end:]
        if new_html != html:
            html = new_html
            changes.append(f'removed {len(aol_secs)} "All Official Links" section(s)')

    # ── 3. Add TSJ_AI_BLOCK_START/END around injected AI sections ────────────
    # Only act on pages that have AI sections WITHOUT existing sentinels
    if _AI_BLOCK_START not in html:
        # Find the AI section block: look for a run of consecutive sec-cards
        # whose headings are all in AI_HEADINGS or whose gradient is AI-gradient
        sections = list(SEC_RE.finditer(html))
        ai_run_start = None
        ai_run_end   = None

        for m in sections:
            sec = m.group(0)
            h2 = H2_RE.search(sec)
            heading = h2.group(1).strip() if h2 else ''
            is_ai = (heading in AI_HEADINGS) or bool(AI_GRADIENTS.search(sec))

            if is_ai:
                if ai_run_start is None:
                    ai_run_start = m.start()
                ai_run_end = m.end()
            else:
                # Non-AI section found → stop if we've seen AI sections
                if ai_run_start is not None:
                    break

        if ai_run_start is not None and ai_run_end is not None:
            ai_block = html[ai_run_start:ai_run_end]
            new_block = f'{_AI_BLOCK_START}\n{ai_block}{_AI_BLOCK_END}\n'
            html = html[:ai_run_start] + new_block + html[ai_run_end:]
            changes.append('added TSJ_AI_BLOCK_START/END around existing AI sections')

    # ── 4. Add TSJ_AI_FAQ_START/END around first FAQs section (if no sentinel) ─
    if _AI_FAQ_START not in html:
        faq_now = [(m.start(), m.end()) for m in SEC_RE.finditer(html)
                   if re.search(r'<h2>FAQs</h2>', m.group(0))]
        if faq_now:
            # Wrap the FAQ section body only (not the outer <section> wrapper)
            # Actually wrap the entire first FAQs section's body content
            # Find the sec-body div inside the first FAQ section
            faq_sec_match = next(
                m for m in SEC_RE.finditer(html)
                if re.search(r'<h2>FAQs</h2>', m.group(0))
            )
            faq_sec_html = faq_sec_match.group(0)
            # Only wrap the inner body (inside sec-body div)
            body_pat = re.compile(
                r'(<div class="sec-body">)(.*?)(</div></section>)', re.DOTALL)
            def wrap_faq_body(m2):
                inner = m2.group(2)
                # Don't double-wrap
                if _AI_FAQ_START in inner:
                    return m2.group(0)
                return (m2.group(1) +
                        _AI_FAQ_START + inner + _AI_FAQ_END +
                        m2.group(3))
            new_faq_sec = body_pat.sub(wrap_faq_body, faq_sec_html, count=1)
            if new_faq_sec != faq_sec_html:
                html = html[:faq_sec_match.start()] + new_faq_sec + html[faq_sec_match.end():]
                changes.append('added TSJ_AI_FAQ_START/END inside FAQs section')

    return html, changes


# ── Main loop ─────────────────────────────────────────────────────────────────
all_pages = sorted(glob.glob(str(ROOT / 'jobs' / '*' / 'index.html')))
print(f"{'[DRY RUN] ' if not APPLY else ''}Scanning {len(all_pages)} pages…")

for fpath in all_pages:
    stats['scanned'] += 1
    try:
        original = open(fpath, encoding='utf-8', errors='replace').read()
    except Exception as ex:
        print(f'  ERROR reading {fpath}: {ex}')
        stats['errors'] += 1
        continue

    new_html, changes = fix_page(original, fpath)

    if not changes:
        stats['already_ok'] += 1
        continue

    # Update stats
    for c in changes:
        if 'FAQs' in c:          stats['dup_faq_fixed'] += 1
        if 'Official Links' in c: stats['aol_removed'] += 1
        if 'sentinel' in c or 'TSJ_AI_BLOCK' in c: stats['sentinel_added'] += 1
        if "DON'T MISS" in c:    stats['dont_miss_fixed'] += 1

    if VERBOSE or not APPLY:
        slug = fpath.split(os.sep)[-2]
        print(f"  {'WOULD FIX' if not APPLY else 'FIXED'} [{slug[:55]}]:")
        for c in changes:
            print(f"    > {c}")

    if APPLY and new_html != original:
        try:
            tmp = Path(fpath).with_suffix('.tmp')
            tmp.write_text(new_html, encoding='utf-8')
            tmp.replace(fpath)
            stats['written'] += 1
        except Exception as ex:
            print(f'  ERROR writing {fpath}: {ex}')
            stats['errors'] += 1

# ── Summary ────────────────────────────────────────────────────────────────────
print()
print('=' * 60)
print(f"  Pages scanned   : {stats['scanned']}")
print(f"  Already OK      : {stats['already_ok']}")
print(f"  Dup FAQs fixed  : {stats['dup_faq_fixed']}")
print(f"  AOL removed     : {stats['aol_removed']}")
print(f"  DON'T MISS fixed: {stats['dont_miss_fixed']}")
print(f"  Sentinels added : {stats['sentinel_added']}")
if APPLY:
    print(f"  Files written   : {stats['written']}")
    print(f"  Errors          : {stats['errors']}")
else:
    print()
    print("  DRY RUN — no files written. Run with --apply to fix.")
print('=' * 60)
