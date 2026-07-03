#!/usr/bin/env python3
"""
patch_link_labels.py — TSJ Important-Links Backfill
===================================================
Purana build HTML (jobs/state/education/... /index.html) mein do bugs in-place
fix karta hai, WITHOUT generate_all.py chalaye:

  BUG 1  Generic "Click Here" / "Download" link labels  → real, keyword-rich
         labels URL se derive karke (same _smart_link_label() logic as generator).
  BUG 2  Duplicate standalone "Useful Links" box        → uske links ko
         "Important Links & Notification PDF" box mein merge karke box hata deta
         hai. Koi link kabhi lost nahi hota (unique links move hote hain).

Design: PURE-HTML transform. generate_all.py import NAHI karta (usko import karna
poora site rebuild trigger kar deta), isliye label logic yahan self-contained
copy hai — generator ke _smart_link_label / _derive_link_label ke identical.

Usage:
  python3 patch_link_labels.py                 # sabhi hub pages patch
  python3 patch_link_labels.py --dry-run        # sirf report, kuch likhega nahi
  python3 patch_link_labels.py --slug <slug>    # single page (jobs/<slug>/)
  ROOTS="jobs state" python3 patch_link_labels.py   # scan roots override
"""

import re, os, sys, html as _html
from pathlib import Path

try:                       # emoji-safe logging on Windows (cp1252) consoles
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── CLI / config ──────────────────────────────────────────────────────────────
DRY_RUN = "--dry-run" in sys.argv
SINGLE  = None
for i, a in enumerate(sys.argv):
    if a == "--slug" and i + 1 < len(sys.argv):
        SINGLE = sys.argv[i + 1].strip().strip("/")
# Hub roots whose /<slug>/index.html use the same build_all_sections() renderer.
ROOTS = os.environ.get("ROOTS", "jobs state education category section qualification").split()

def e(s):
    return _html.escape(str(s or ""), quote=True)

# ── Label logic — IDENTICAL to generate_all.py (keep in sync) ─────────────────
_GENERIC_LINK_LABELS = {'click here','click','view','here','open','link','open link',
                        'official pdf document','official pdf','pdf','download','click_here'}

_EXAM_PORTAL_HOSTS = ('digialm.com', 'ibpsonline.ibps.in', 'tcsion.com',
                      'cdn3.digialm', 'onlineapplication', 'onlinereg',
                      'apply.', 'recruitment.', 'onlineapp')

def _derive_link_label(url, job_core=''):
    u  = (url or '').strip(); ul = u.lower()
    host = re.sub(r'^https?://', '', ul).split('/')[0]
    path = re.sub(r'^https?://[^/]+', '', ul).split('?')[0].split('#')[0]
    seg  = [s for s in path.split('/') if s]
    stem = re.sub(r'\.(pdf|html?|aspx?|php|jsp)$', '', seg[-1]) if seg else ''
    words = re.sub(r'[^a-z0-9]+', ' ', stem).strip()
    def has(*ks): return any(k in ul for k in ks)
    if any(h in host for h in _EXAM_PORTAL_HOSTS):  return 'Online Application Portal'
    if has('corrigend'):                            return 'Corrigendum Notice PDF'
    if has('addend'):                               return 'Addendum Notice PDF'
    if has('admit', 'hallticket', 'hall-ticket', 'call-letter', 'callletter'): return 'Download Admit Card'
    if has('answer', 'anskey', 'ans-key'):          return 'Answer Key'
    if has('syllabus', 'curriculum'):               return 'Syllabus PDF'
    if has('result', 'merit', 'scorecard', 'score-card'): return 'Result / Merit List'
    if has('cutoff', 'cut-off'):                    return 'Cut Off Marks'
    if has('login', 'signin', 'sign-in'):           return 'Login'
    if has('register', 'signup', 'sign-up', 'registration', 'newreg'): return 'Register Now'
    if has('apply', 'career', 'recruit', 'applic', 'vacan'): return 'Apply Online'
    if has('advt', 'advertisement', 'notif', 'notice', 'circular', 'bharti'): return 'Notification PDF'
    if has('brochure', 'prospectus'):               return 'Information Brochure PDF'
    if ul.endswith('.pdf') or '.pdf?' in ul or '.pdf#' in ul:
        if words and len(words.replace(' ', '')) >= 3 and not words.replace(' ', '').isdigit():
            return ' '.join(w.capitalize() for w in words.split())[:56] + ' PDF'
        return 'Download Notification PDF'
    if seg:
        if words and len(words.replace(' ', '')) >= 4 and not words.replace(' ', '').isdigit():
            return ' '.join(w.capitalize() for w in words.split())[:60]
        if job_core:
            return f'{job_core} — Official Link'[:70]
    return 'Official Website'

def _smart_link_label(url, fallback='', job_core=''):
    fb = (fallback or '').strip()
    if fb and fb.lower() not in _GENERIC_LINK_LABELS:
        return fb[:70]
    return _derive_link_label(url, job_core)

def _row_style(url, label):
    ul = (url or '').lower(); ll = (label or '').lower()
    if ul.endswith('.pdf'):                              return ('lk-pdf', 'fa-file-pdf')
    if 'apply' in ll or 'apply' in ul or 'career' in ul: return ('lk-apply', 'fa-paper-plane')
    if 'result' in ll or 'merit' in ll:                  return ('lk-result', 'fa-trophy')
    if 'admit' in ll or 'admit' in ul:                   return ('lk-admit', 'fa-id-card')
    if 'answer' in ll:                                   return ('lk-answer', 'fa-key')
    if 'login' in ll:                                    return ('lk-login', 'fa-right-to-bracket')
    if 'register' in ll:                                 return ('lk-register', 'fa-user-plus')
    if 'official' in ll or 'website' in ll:              return ('lk-official', 'fa-globe')
    return ('lk-default', 'fa-link')

def _row(label, url):
    """Canonical Important-Links row — byte-identical to generate_all._row()."""
    css, icon = _row_style(url, label)
    dl = ' download' if str(url).lower().endswith('.pdf') else ''
    return (f'<div class="lk-row">'
            f'<span class="lk-label">{e(label)}</span>'
            f'<a href="{e(url)}" class="lk-open {css}" target="_blank" rel="nofollow noopener noreferrer"{dl}>'
            f'<i class="fa-solid {icon}"></i> Open</a></div>\n')

# ── HTML parsing ──────────────────────────────────────────────────────────────
SECCARD_RE = re.compile(r'<section class="sec-card">.*?</section>\s*', re.S)
HEAD_RE    = re.compile(r'<div class="sec-head".*?</div>', re.S)
H2_RE      = re.compile(r'<h2>(.*?)</h2>', re.S)
ROW_RE     = re.compile(r'<div class="lk-row"><span class="lk-label">(.*?)</span>\s*<a\s+href="([^"]+)"', re.S)
H1_RE      = re.compile(r'<h1[^>]*post-title[^>]*>(.*?)</h1>', re.S | re.I)
_TAG_RE    = re.compile(r'<[^>]+>')

def _text(html_frag):
    return _html.unescape(_TAG_RE.sub('', html_frag or '')).strip()

def _rows_of(seccard):
    """Return ordered [(raw_label, url)] from a sec-card's lk-rows."""
    out = []
    for m in ROW_RE.finditer(seccard):
        out.append((_html.unescape(m.group(1)).strip(), _html.unescape(m.group(2)).strip()))
    return out

_IMPORTANT_HEAD = 'Important Links & Notification PDF'

def patch_html(html: str) -> tuple[str, list]:
    changes = []
    cards = list(SECCARD_RE.finditer(html))
    if not cards:
        return html, changes

    important = None          # (match, heading, head_html, rows)
    usefuls   = []            # [(match, rows)]
    for m in cards:
        block = m.group(0)
        h2m = H2_RE.search(block)
        heading = _text(h2m.group(1)) if h2m else ''
        hl = heading.lower()
        if 'important links' in hl:
            if important is None:
                hm = HEAD_RE.search(block)
                important = (block, heading, hm.group(0) if hm else '', _rows_of(block))
        elif hl == 'useful links':
            usefuls.append((block, _rows_of(block)))

    if not usefuls and important is None:
        return html, changes
    # Pages with ZERO useful boxes and an existing important box may still carry
    # stale generic labels — fix those in place too.
    if not usefuls and important is not None:
        _, _, head_html, rows = important
        new_rows = _rebuild_rows(rows, '')
        if new_rows is None:
            return html, changes                       # nothing to change
        rebuilt = _build_card(head_html, important[1], new_rows)
        html = html.replace(important[0], rebuilt, 1)
        changes.append(f"fixed {len(rows)} important-link label(s)")
        return html, changes

    # Derive a job-title core from the H1 for nicer URL-derived labels.
    h1m = H1_RE.search(html)
    job_core = ''
    if h1m:
        job_core = _text(h1m.group(1))
        job_core = re.sub(r'\s*[-–—:].*$', '', job_core).strip()[:58]

    # ── Merge order: important rows first, then unique useful rows ────────────
    merged, seen = [], set()
    if important:
        for lbl, url in important[3]:
            k = url.lower()
            if k in seen: continue
            seen.add(k); merged.append((lbl, url))
    moved = 0
    for _block, rows in usefuls:
        for lbl, url in rows:
            k = url.lower()
            if not url.lower().startswith('http'): continue
            if k in seen: continue
            seen.add(k); merged.append((lbl, url)); moved += 1

    new_rows_html = ''.join(_row(_smart_link_label(u, raw, job_core), u) for raw, u in merged)
    body_html = f'<div class="links-rows">{new_rows_html}</div>'

    if important:
        rebuilt = _build_card(important[2], important[1], body_html)
        html = html.replace(important[0], rebuilt, 1)
    else:
        # No important box existed → convert the FIRST useful box into one.
        head_html = ('<div class="sec-head" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)">'
                     '<i class="fa-solid fa-link"></i><h2>' + e(
                         (job_core + ' : ' + _IMPORTANT_HEAD) if job_core else _IMPORTANT_HEAD) + '</h2></div>')
        rebuilt = _build_card(head_html, _IMPORTANT_HEAD, body_html)
        first_block = usefuls[0][0]
        html = html.replace(first_block, rebuilt, 1)
        usefuls = usefuls[1:]                           # remaining ones just get deleted

    for block, _rows in usefuls:
        html = html.replace(block, '', 1)

    changes.append(f"removed {len(usefuls) + (0 if important else 1)} 'Useful Links' box, "
                   f"merged {moved} link(s), {len(merged)} total rows")
    return html, changes

def _build_card(head_html, heading, body_or_rows):
    body = body_or_rows if body_or_rows.lstrip().startswith('<div class="links-rows"') \
           else f'<div class="links-rows">{body_or_rows}</div>'
    return (f'<section class="sec-card">{head_html}'
            f'<div class="sec-body">{body}</div></section>\n')

def _rebuild_rows(rows, job_core):
    """Return rebuilt links-rows HTML if any label would change, else None."""
    out = []; changed = False; seen = set()
    for raw, url in rows:
        k = url.lower()
        if k in seen: continue
        seen.add(k)
        new_lbl = _smart_link_label(url, raw, job_core)
        if new_lbl != raw: changed = True
        out.append(_row(new_lbl, url))
    if not changed and len(out) == len(rows):
        return None
    return f'<div class="links-rows">{"".join(out)}</div>'

# ── Walk files ────────────────────────────────────────────────────────────────
def iter_pages():
    if SINGLE:
        p = Path("jobs") / SINGLE / "index.html"
        if p.exists():
            yield p
        return
    for root in ROOTS:
        base = Path(root)
        if not base.exists():
            continue
        for p in base.rglob("index.html"):
            yield p

def main():
    print("=" * 60)
    print("🔧 TSJ Important-Links Backfill (labels + dup box)")
    print(f"   mode: {'DRY RUN (no writes)' if DRY_RUN else 'WRITE'}"
          + (f"   slug: {SINGLE}" if SINGLE else f"   roots: {' '.join(ROOTS)}"))
    print("=" * 60)

    scanned = patched = skipped = errors = 0
    for path in iter_pages():
        scanned += 1
        try:
            original = path.read_text(encoding="utf-8")
            # fast pre-filter — skip pages with nothing to do
            if ('>Useful Links<' not in original
                    and 'lk-label">Click Here<' not in original
                    and '>Download<' not in original):
                skipped += 1
                continue
            new_html, changes = patch_html(original)
            if not changes or new_html == original:
                skipped += 1
                continue
            slug = path.parent.name
            if DRY_RUN:
                print(f"  🔵 {slug[:52]:52} | {'; '.join(changes)}")
            else:
                tmp = path.with_suffix(".tmp")
                tmp.write_text(new_html, encoding="utf-8")
                tmp.replace(path)
                print(f"  ✅ {slug[:52]:52} | {'; '.join(changes)}")
            patched += 1
        except Exception as ex:
            print(f"  ❌ {path}: {ex}")
            errors += 1

    print("=" * 60)
    print(f"  scanned: {scanned}   patched: {patched}   skipped: {skipped}   errors: {errors}")
    print("=" * 60)
    if patched and not DRY_RUN:
        print("\n✨ Done. Commit:")
        print("  git add jobs/ state/ education/ category/ section/ qualification/")
        print('  git commit -m "Backfill: fix Click Here labels + remove duplicate Useful Links box"')

if __name__ == "__main__":
    main()
