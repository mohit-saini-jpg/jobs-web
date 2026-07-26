#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_sark_hex_duplicates.py — Part 2 of the Duplicate Job Pages fix.

merge_duplicate_jobs.py (Part 1) only sees jobs that have a saved
jobs/data/<slug>.json file — which SARK-sourced jobs never get (only the
FJA ingestion loop in generate_all.py saves one). So it is completely blind
to the duplicate class fixed at the SOURCE in the 2026-07-25/26
_versioned_slug() commits: when a SARK job has no advt_no and no
distinguishing year, _versioned_slug() used to fall back to appending its
_version_signature() hash as the slug suffix -- and that hash could differ
between two scrapes of the EXACT SAME posting from pure noise (PDF
re-uploaded under a different filename, date-string formatting drift, or
-- confirmed empirically below -- simply hashing to the same
"all fields blank" constant across many unrelated postings), producing a
near-duplicate page instead of being recognized as the same job.

This script finds those retroactively by scanning jobs/*/index.html
directly (title + rendered content, no JSON needed):

  1. A slug matches <base>-<hex> where <hex> is exactly 8 or 10 lowercase
     hex characters AND contains at least one letter a-f (excludes
     legitimate numeric date/advt-number suffixes like "-01032026" or
     "-052026", which are correct, intentional version distinctions).
  2. <base> also exists as a separate job folder on disk.
  3. SAFETY GATE (the important part -- the repeated "ffa638515d" suffix
     across dozens of unrelated postings proves the hash itself carries
     NO reliable duplicate signal here, it's just the MD5 of an empty
     string): the two pages' <h1> titles must be EXACTLY identical after
     whitespace normalization. Not fuzzy, not fingerprint-based -- exact.
  4. SECOND SAFETY GATE: their rendered Vacancy Details text (post names +
     counts) must also match, or both be absent. This is defense-in-depth
     against the false-positive class found auditing Part 1 (two postings
     that can share a title-like string but have genuinely different
     vacancy breakdowns) -- here titles are already exact-identical, but
     costs nothing to double-check.

Anything that fails either gate is left alone (not merged, not reported
as a problem -- most <base>-<hex> slugs are correctly NOT duplicates,
e.g. "up-iti-admission-apply-online-form-2026-0a0f546d0c" may be a
distinct one-off page with no real base-slug collision in intent even
though a folder of that base name happens to exist).

Reuses the exact same downstream steps as merge_duplicate_jobs.py:
_redirects, sitemap-jobs.xml, jobs-index.json, data/sections-index.json,
homepage-mini.json, then deletes the duplicate's jobs/<slug>/ folder.
NOTE: run build_redirect_map.py afterward -- Vercel's edge middleware
reads the compiled redirect-map.js, not _redirects directly.

Usage:
  python scripts/merge_sark_hex_duplicates.py            # dry run (safe)
  python scripts/merge_sark_hex_duplicates.py --execute  # actually make changes
  python scripts/merge_sark_hex_duplicates.py --execute --limit 10   # small batch
"""

import os, re, sys, shutil, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT       = Path(__file__).resolve().parent.parent
JOBS_DIR   = ROOT / 'jobs'
REDIRECTS  = ROOT / '_redirects'
SITEMAP_J  = ROOT / 'sitemap-jobs.xml'
HASHES_F   = ROOT / '.sitemap-content-hashes.json'
IDX_F      = ROOT / 'jobs-index.json'
SECTIONS_F = ROOT / 'data' / 'sections-index.json'
MINI_F     = ROOT / 'homepage-mini.json'
REPORT_F   = ROOT / 'SARK_HEX_MERGE_REPORT.md'
SKIP_F     = ROOT / 'SARK_HEX_MERGE_SKIPPED.md'

DRY_RUN = '--execute' not in sys.argv
LIMIT = None
if '--limit' in sys.argv:
    try:
        LIMIT = int(sys.argv[sys.argv.index('--limit') + 1])
    except (IndexError, ValueError):
        LIMIT = None

HEX_SUFFIX_RE = re.compile(r'^(.+)-([0-9a-f]{8}|[0-9a-f]{10})$')
H1_RE = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)
TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')


def norm_text(s):
    s = TAG_RE.sub(' ', s)
    s = WS_RE.sub(' ', s)
    return s.strip()


def read_title(slug):
    p = JOBS_DIR / slug / 'index.html'
    try:
        c = p.read_text(encoding='utf-8')
    except Exception:
        return None, None
    m = H1_RE.search(c)
    title = norm_text(m.group(1)) if m else None
    return title, c


def vacancy_text(html):
    """Rendered 'Vacancy Details' section text, or '' if not present."""
    idx = html.find('Vacancy Details')
    if idx == -1:
        return ''
    # Section bodies in this template run a few hundred chars before the
    # next <section class="sec-card">; 900 chars comfortably covers the
    # post-name/count table without pulling in the next section's heading.
    chunk = html[idx:idx + 900]
    nxt = chunk.find('<section class="sec-card">', 40)
    if nxt != -1:
        chunk = chunk[:nxt]
    return norm_text(chunk)


def find_candidates():
    out = []
    for d in sorted(os.listdir(JOBS_DIR)):
        full = JOBS_DIR / d
        if not full.is_dir() or d == 'data':
            continue
        m = HEX_SUFFIX_RE.match(d)
        if not m:
            continue
        base, suf = m.group(1), m.group(2)
        if not re.search(r'[a-f]', suf):
            continue  # pure-digit suffix -> real date/advt-no, not a hash
        if not (JOBS_DIR / base / 'index.html').is_file():
            continue  # no base-slug counterpart -> not our bug pattern
        out.append((d, base))
    return out


def main():
    print(f"{'[DRY RUN] ' if DRY_RUN else '[EXECUTE] '}merge_sark_hex_duplicates.py")
    if LIMIT:
        print(f"  (limited to first {LIMIT} confirmed merges)")
    print(f"  Root: {ROOT}\n")

    candidates = find_candidates()
    print(f"  {len(candidates)} slug(s) match the hex-suffix + existing-base pattern\n")

    confirmed = []   # (dup_slug, base_slug)
    skipped   = []   # (dup_slug, base_slug, reason)

    for dup_slug, base_slug in candidates:
        dup_title, dup_html = read_title(dup_slug)
        base_title, base_html = read_title(base_slug)
        if dup_title is None or base_title is None:
            skipped.append((dup_slug, base_slug, "could not read title from one or both pages"))
            continue
        if dup_title != base_title:
            skipped.append((dup_slug, base_slug,
                             f"titles differ: {dup_title!r} vs {base_title!r}"))
            continue
        dv, bv = vacancy_text(dup_html), vacancy_text(base_html)
        if dv != bv:
            skipped.append((dup_slug, base_slug,
                             "titles match but Vacancy Details section differs -- needs manual review"))
            continue
        confirmed.append((dup_slug, base_slug))
        if LIMIT and len(confirmed) >= LIMIT:
            break

    print(f"  Confirmed safe merges: {len(confirmed)}")
    print(f"  Skipped (failed a safety gate): {len(skipped)}\n")

    for dup_slug, base_slug in confirmed:
        print(f"  MERGE: {dup_slug!r} -> {base_slug!r}")

    # ── Apply ──
    new_redirects = []
    slugs_to_remove = []

    for dup_slug, base_slug in confirmed:
        folder = JOBS_DIR / dup_slug
        if folder.exists():
            if not DRY_RUN:
                shutil.rmtree(folder)
            print(f"    del folder: jobs/{dup_slug}")
        redirect_line = f"/jobs/{dup_slug}/  /jobs/{base_slug}/  301"
        new_redirects.append(redirect_line)
        slugs_to_remove.append(dup_slug)

    if new_redirects:
        print(f"\n  Writing {len(new_redirects)} redirects to _redirects ...")
        rtext = REDIRECTS.read_text(encoding='utf-8') if REDIRECTS.exists() else ''
        header = '\n# ══ Auto-merged SARK hex-suffix duplicate redirects ══\n'
        rtext = header + '\n'.join(new_redirects) + '\n\n' + rtext
        if not DRY_RUN:
            REDIRECTS.write_text(rtext, encoding='utf-8')

    if slugs_to_remove:
        import json as _json

        print(f"  Removing {len(slugs_to_remove)} entries from sitemap-jobs.xml ...")
        smap = SITEMAP_J.read_text(encoding='utf-8') if SITEMAP_J.exists() else ''
        for s in slugs_to_remove:
            smap = re.sub(
                r'\s*<url><loc>[^<]*/jobs/' + re.escape(s) + r'/</loc>.*?</url>',
                '', smap, flags=re.S)
        if not DRY_RUN:
            SITEMAP_J.write_text(smap, encoding='utf-8')

        for f, key_is_dict_of_dicts in ((HASHES_F, True), (IDX_F, True)):
            try:
                data = _json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}
            except Exception:
                data = {}
            if isinstance(data, dict):
                for s in slugs_to_remove:
                    data.pop(s, None)
                if not DRY_RUN:
                    f.write_text(_json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

        print("  Removing entries from data/sections-index.json ...")
        try:
            sections = _json.loads(SECTIONS_F.read_text(encoding='utf-8')) if SECTIONS_F.exists() else {}
        except Exception:
            sections = {}
        if isinstance(sections, dict):
            slug_set = set(slugs_to_remove)
            for cat in sections:
                if isinstance(sections[cat], list):
                    sections[cat] = [e for e in sections[cat]
                                      if isinstance(e, dict) and e.get('slug') not in slug_set]
            if not DRY_RUN:
                SECTIONS_F.write_text(_json.dumps(sections, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

        print("  Removing entries from homepage-mini.json ...")
        try:
            mini = _json.loads(MINI_F.read_text(encoding='utf-8')) if MINI_F.exists() else {}
        except Exception:
            mini = {}
        if isinstance(mini, dict) and isinstance(mini.get('jobs'), list):
            slug_set = set(slugs_to_remove)
            mini['jobs'] = [j for j in mini['jobs'] if j.get('s') not in slug_set]
            if not DRY_RUN:
                MINI_F.write_text(_json.dumps(mini, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    # ── Reports (always written, even dry-run) ──
    lines = [
        "# SARK_HEX_MERGE_REPORT", "",
        f"- Candidates scanned: {len(candidates)}",
        f"- Confirmed safe merges: {len(confirmed)}",
        f"- Skipped (failed a safety gate): {len(skipped)}", "",
        "## Merged", "",
    ]
    for dup_slug, base_slug in confirmed:
        lines.append(f"- `{dup_slug}` -> `{base_slug}`")
    mode = "DRY RUN (no changes made)" if DRY_RUN else "EXECUTED"
    lines.append(f"\n_Report generated in {mode} mode._")
    REPORT_F.write_text('\n'.join(lines), encoding='utf-8')

    skip_lines = ["# SARK_HEX_MERGE_SKIPPED", "",
                  "Slugs that matched the hex-suffix pattern but failed a safety gate",
                  "(not merged -- left exactly as-is):", ""]
    for dup_slug, base_slug, reason in skipped:
        skip_lines.append(f"- `{dup_slug}` vs `{base_slug}`: {reason}")
    SKIP_F.write_text('\n'.join(skip_lines), encoding='utf-8')

    print(f"\n{'[DRY RUN] ' if DRY_RUN else ''}Done.")
    print(f"  Merged:  {len(confirmed)}")
    print(f"  Skipped: {len(skipped)}")
    if DRY_RUN:
        print("\n  Re-run with --execute to apply changes (optionally --limit N for a small batch).")
    else:
        print("\n  IMPORTANT: now run `python3 build_redirect_map.py` to compile the new")
        print("  redirects into redirect-map.js -- Vercel's edge middleware won't see")
        print("  them otherwise.")


if __name__ == '__main__':
    main()
