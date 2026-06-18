#!/usr/bin/env python3
"""PERFORMANCE: subset fonts/fa/all.min.css to only the icon glyphs actually used
on the site. Font Awesome Free 6 ships ~2000 icons in a 100KB CSS; this site uses
~207. We keep ALL structural/base CSS (.fa, sizing, animation, @font-face, stacks)
and drop only the unused `.fa-<name>::before{content:...}` glyph rules.

SAFE: only removes glyph-content rules for icons that appear nowhere in the site.
No layout/structure change — icon classes still resolve, just a smaller file.
Output: fonts/fa/all.min.css (overwrites; original backed up to all.min.css.bak)."""
import re
import os
import glob
import random

ROOT = os.path.dirname(os.path.abspath(__file__))
FA = os.path.join(ROOT, 'fonts', 'fa', 'all.min.css')


def collect_used_icons():
    used = set()
    patterns = (glob.glob(os.path.join(ROOT, '*.html'))
                + glob.glob(os.path.join(ROOT, '*.js'))
                + glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True))
    for f in patterns:
        if '/jobs/' in f:
            continue
        try:
            txt = open(f, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        used.update(re.findall(r'fa-[a-z0-9-]+', txt))
    # scan ALL generated job pages (no sampling) — sampling could miss an icon
    # used on only a few pages and wrongly drop it
    jobfiles = glob.glob(os.path.join(ROOT, 'jobs', '*', 'index.html'))
    for f in jobfiles:
        try:
            txt = open(f, encoding='utf-8', errors='ignore').read()
            used.update(re.findall(r'fa-[a-z0-9-]+', txt))
        except Exception:
            pass
    return used


def subset():
    css = open(FA, encoding='utf-8').read()
    orig_len = len(css)
    used = collect_used_icons()

    # Match individual icon glyph rules: .fa-NAME:before{content:"\xxxx"}
    # (FA 6 uses ::before or :before). Keep the rule ONLY if fa-NAME is used.
    # Rule shape (minified): .fa-paper-plane:before{content:"\f1d8"}
    glyph_rx = re.compile(
        r'\.fa-([a-z0-9-]+):{1,2}before\{content:"\\[0-9a-fA-F]+"\}')

    kept = [0]
    dropped = [0]

    def repl(m):
        name = 'fa-' + m.group(1)
        if name in used:
            kept[0] += 1
            return m.group(0)
        dropped[0] += 1
        return ''

    new_css = glyph_rx.sub(repl, css)
    # also handle aliased rules like ".fa-NAME,.fa-ALIAS:before{content:...}"
    # (FA defines some aliases). Keep if ANY name in the selector group is used.
    alias_rx = re.compile(
        r'((?:\.fa-[a-z0-9-]+,)+\.fa-[a-z0-9-]+):{1,2}before\{content:"\\[0-9a-fA-F]+"\}')

    def alias_repl(m):
        names = set(re.findall(r'\.fa-([a-z0-9-]+)', m.group(0)))
        if any(('fa-' + n) in used for n in names):
            return m.group(0)
        return ''

    new_css = alias_rx.sub(alias_repl, new_css)

    # backup + write
    if not os.path.exists(FA + '.bak'):
        open(FA + '.bak', 'w', encoding='utf-8').write(css)
    open(FA, 'w', encoding='utf-8').write(new_css)
    print(f"FA CSS: {orig_len//1024}KB -> {len(new_css)//1024}KB "
          f"(kept {kept[0]} glyphs, dropped {dropped[0]})")


if __name__ == '__main__':
    subset()
