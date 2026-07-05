#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
heal_jobposting_schema.py — audit + opt-in auto-heal for stale JobPosting schema
on already-rendered /jobs/<slug>/index.html pages.

WHY THIS EXISTS
---------------
Some pages were rendered by an older generator pass and never regenerated (the
"permanent page / __disk__ skip" bug), so their baked JobPosting schema went
stale. Two concrete, Google-flagged symptoms:

  1. A duplicate, hidden microdata block (<!-- tsj-microdata --> ... <div
     itemscope itemtype="schema.org/JobPosting"> ... <!-- tsj-microdata -->)
     injected by ai_html_enricher.py. It mirrored the JSON-LD but wrote
     `directApply content="False"` (a capitalised string, which Google parses as
     the URI http://schema.org/False) and carried NO streetAddress -> the exact
     "directApply: http://schema.org/False" + "Missing field streetAddress"
     errors seen in the Rich Results Test. The injector is now disabled in
     ai_html_enricher.py; this script removes the blocks already on disk.

  2. A stale jobLocation in the JSON-LD itself (e.g. a Telangana TGPSC job baked
     with addressRegion "Gujarat" / postalCode 380001), because state detection
     was fixed after those pages were rendered.

WHAT IT DOES
------------
Audit mode (default, READ-ONLY): walks jobs/*/index.html, matches each page to
its own source JSON (jobs/data/<slug>.json, best-effort prefix match), and
reports counts + samples per issue:
    has_duplicate_microdata, stale_region, stale_description,
    non_boolean_directApply, canonical_issue, orphaned_no_source_json

Heal mode (--fix, opt-in): fixes only what the page's OWN source JSON confirms:
    - delete the duplicate microdata block            (always safe)
    - coerce non-boolean directApply -> real boolean  (always safe)
    - re-derive addressRegion/postalCode/addressLocality/streetAddress from the
      job's source JSON, ONLY when detection is CONFIDENT and differs
    - re-derive a stale description (== title) from source short_information
Orphan pages (no source JSON) still get microdata removed + directApply coerced
(neither needs source data); their region is reported but never guessed.

State detection mirrors generate_all.py build_schemas() but reads the shared
canonical map data/state_pincode_map.json (single source of truth, avoids the
three-hand-maintained-maps drift). generate_all.py is NOT imported because it
has no __main__ guard and would run the whole site generator on import.

Pure stdlib + json + re. Idempotent: a second --fix run makes zero changes.

USAGE
    python heal_jobposting_schema.py                 # audit whole jobs/ tree
    python heal_jobposting_schema.py <path-substr>   # audit only matching paths
    python heal_jobposting_schema.py --fix           # heal whole tree
    python heal_jobposting_schema.py --fix <substr>  # heal only matching paths
"""
import os
import re
import sys
import glob
import html as _htmllib
import json
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", ".github", "node_modules", "backups", "__pycache__", "data"}
SCAN_DIRS = ("jobs", "education", "district", "state")  # dirs that may carry JobPosting

# ── canonical state map (shared single source of truth) ──────────────────────
_MAP_PATH = os.path.join(ROOT, "data", "state_pincode_map.json")
with open(_MAP_PATH, encoding="utf-8") as _f:
    _SMAP = json.load(_f)
DEFAULT_REGION, DEFAULT_PIN = _SMAP["default"]
NAME_MAP = _SMAP["name_map"]                                   # {name: [region, pin]}
SLUG_MAP = [(kw, r, p) for kw, r, p in _SMAP["slug_map"]]      # ordered list

_LDJSON_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
# whole microdata block incl. both wrapping comment markers and surrounding newlines
_MICRODATA_RE = re.compile(r'[ \t]*<!-- tsj-microdata -->.*?<!-- tsj-microdata -->[ \t]*\n?', re.S)
# a bare itemscope JobPosting div (fallback: microdata without the comment markers)
_MICRODATA_DIV_RE = re.compile(
    r'[ \t]*<div[^>]*itemscope[^>]*itemtype="https://schema\.org/JobPosting"[^>]*>.*?</div>\s*\n?',
    re.S)
_CANON_RE = re.compile(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', re.I)


# ── helpers mirroring generate_all.py ────────────────────────────────────────
def _striptags(v):
    """Plain text: drop tags, unescape entities, collapse whitespace."""
    s = re.sub(r'<[^>]+>', ' ', str(v or ''))
    s = _htmllib.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def _detect_state_from_text(text):
    """slug/title/org keyword -> (region, pin) or (None, None). Order-sensitive."""
    t = str(text).lower().replace(' ', '-')
    for kw, region, pin in SLUG_MAP:
        if kw in t:
            return region, pin
    return None, None


def _name_in(name, text):
    """Whole-word match of a state name inside free text. Critical for the short
    keys 'mp'/'up' — a plain substring test matches them inside unrelated words
    ('i[mp]hal' -> Madhya Pradesh, 'grou[p]' etc). Word boundaries stop that."""
    return re.search(r'(?<![a-z])' + re.escape(name) + r'(?![a-z])', text) is not None


def detect_region(job_obj, slug):
    """4-level detection identical in spirit to build_schemas():
       L1 ai_data.job_location -> L2 basic_details.job_location -> L3 slug+title+org.
    Returns (region, pin, level) where level is 'L1'/'L2'/'L3'/'default'.

    L1/L2 come from the job's OWN stated location (high trust) and MAY overwrite an
    existing baked region. L3 is only a slug/org keyword guess and 'default' is a
    blind fallback — callers must NOT overwrite an existing region from those."""
    bd = job_obj.get('basic_details', {}) or {}
    ai_data = job_obj.get('ai_extracted_structured_data') or {}
    title = _striptags(bd.get('job_title', '') or job_obj.get('title', ''))
    org = _striptags(bd.get('organization_name', '') or '')
    loc = _striptags(bd.get('job_location', '') or 'India')

    region, pin, level = DEFAULT_REGION, DEFAULT_PIN, 'default'

    # L1: ai_data.job_location. Skip the pseudo-entry 'india' (national default ->
    # Delhi): a "PAN India" location is NOT an authoritative state and must never
    # overwrite a baked region — otherwise 'PAN India' would flip pages to Delhi.
    ai_region = _striptags(ai_data.get('job_location') or '')
    if ai_region and ai_region.lower() not in ('null', 'none', ''):
        for name, (rv, pv) in NAME_MAP.items():
            if name == 'india':
                continue
            if _name_in(name, ai_region.lower()):
                region, pin, level = rv, pv, 'L1'
                break

    # L2: basic_details.job_location (skip generic 'india' — see L1 note)
    if level == 'default' and loc.lower().strip() not in ('india', ''):
        for name, (rv, pv) in NAME_MAP.items():
            if name == 'india':
                continue
            if _name_in(name, loc.lower()):
                region, pin, level = rv, pv, 'L2'
                break

    # L3: slug + title + org keyword match
    if level == 'default':
        r3, p3 = _detect_state_from_text(f"{slug or ''} {title} {org}")
        if r3:
            region, pin, level = r3, p3, 'L3'

    # ai_data.postal_code hard override (6-digit only)
    ai_pin = str(ai_data.get('postal_code') or '').strip()
    if len(ai_pin) == 6 and ai_pin.isdigit():
        pin = ai_pin

    return region, pin, level


# Pages whose SOURCE job_location is itself wrong (bad scrape) — never auto-apply
# a region change from them, even though it is a confident L1/L2 match.
#   tanuvas-enumerators: source says "New Delhi, Delhi" but TANUVAS is a Tamil
#   Nadu university; the existing Tamil Nadu region on the page is correct.
REGION_SKIP = {
    'tanuvas-enumerators-recruitment-2026-walkin',
}


def region_should_apply(level, slug):
    """Only overwrite an existing baked region from the job's own stated location
    (L1/L2), never from an L3 keyword guess or the blind default, and never for a
    page on the bad-source skip list."""
    return level in ('L1', 'L2') and slug not in REGION_SKIP


def build_street(org, loc, region):
    """streetAddress '<Org>, <City>, <State>, India' — mirrors build_schemas()."""
    org = _striptags(org)
    region = _striptags(region)
    city = _striptags(loc)
    # reject a messy locality (multi-state list / embeds region / too long / india)
    if (not city or ',' in city or len(city) > 28
            or city.strip().lower() in ('india', '')
            or region.lower() in city.lower()):
        city = ''
    org_l = org.lower()
    bits = [org] if org else []
    if city and city.lower() not in org_l:
        bits.append(city)
    if region and region.lower() not in org_l:
        bits.append(region)
    if not (bits and bits[-1].lower().endswith('india')):
        bits.append('India')
    seen = []
    for b in bits:
        if b and b not in seen:
            seen.append(b)
    return ', '.join(seen) or (f"{org} Head Office".strip() or 'Head Office')


def clean_description(short_info, title):
    """sanitize short_information -> <=500 chars, else fall back to title."""
    d = _striptags(short_info)[:500]
    return d or title


# ── source-JSON index (jobs/data/<slug>.json) ────────────────────────────────
def build_source_index():
    """slug -> parsed record, from jobs/data/*.json. Keyed by the record's own
    slug and by the filename stem (both, since either may be the truncated form)."""
    idx = {}
    for fp in glob.glob(os.path.join(ROOT, "jobs", "data", "*.json")):
        try:
            rec = json.load(open(fp, encoding="utf-8"))
        except Exception as ex:
            print("  [warn] bad source json:", os.path.basename(fp), ex)
            continue
        stem = os.path.splitext(os.path.basename(fp))[0]
        for key in {stem, str(rec.get('slug') or '')}:
            if key:
                idx.setdefault(key, rec)
    return idx


def find_source(folder_slug, idx, idx_keys):
    """Match a page folder slug to a source record. Exact first, else longest
    prefix overlap (data slugs are truncated ~78 chars vs 80-char folders)."""
    rec = idx.get(folder_slug)
    if rec is not None:
        return rec
    best_key, best_len = None, 0
    for k in idx_keys:
        # one is a prefix of the other, and the overlap is long enough to trust
        if folder_slug.startswith(k) or k.startswith(folder_slug):
            n = min(len(folder_slug), len(k))
            if n >= 55 and n > best_len:
                best_key, best_len = k, n
    return idx.get(best_key) if best_key else None


# ── per-page work ────────────────────────────────────────────────────────────
def find_jobposting_ldblock(html):
    """Return (match, dict) for the first ld+json JobPosting block, or (None, None)."""
    for m in _LDJSON_RE.finditer(html):
        if '"JobPosting"' not in m.group(2) and 'JobPosting' not in m.group(2):
            continue
        try:
            data = json.loads(m.group(2))
        except Exception:
            continue
        if isinstance(data, dict) and data.get('@type') == 'JobPosting':
            return m, data
    return None, None


def audit_page(path, idx, idx_keys):
    """Return a dict of booleans/values describing issues on this page (no writes)."""
    slug = os.path.basename(os.path.dirname(path))
    try:
        html = open(path, encoding='utf-8', errors='ignore').read()
    except Exception as ex:
        return {'slug': slug, 'read_error': str(ex)}
    if 'JobPosting' not in html:
        return None  # not a job page — ignore

    info = {'slug': slug, 'path': path}
    info['has_duplicate_microdata'] = bool(_MICRODATA_RE.search(html)
                                           or _MICRODATA_DIV_RE.search(html))

    m, jp = find_jobposting_ldblock(html)
    info['has_jsonld_jobposting'] = jp is not None

    # non-boolean directApply — in JSON-LD (string) or a microdata content="False/True"
    info['non_boolean_directApply'] = False
    if jp is not None and not isinstance(jp.get('directApply', False), bool):
        info['non_boolean_directApply'] = True
    if re.search(r'itemprop="directApply"\s+content="(?:True|False|true|false)"', html):
        info['non_boolean_directApply'] = True

    # canonical present & single
    canons = _CANON_RE.findall(html)
    info['canonical_issue'] = (len(canons) != 1)

    # source-JSON cross-checks
    rec = find_source(slug, idx, idx_keys)
    info['orphaned_no_source_json'] = rec is None
    info['stale_region'] = False
    info['stale_description'] = False
    info['region_lowconf_review'] = False
    if rec is not None and jp is not None:
        region, pin, level = detect_region(rec, slug)
        addr = ((jp.get('jobLocation') or {}).get('address') or {})
        cur_region = str(addr.get('addressRegion') or '')
        cur_pin = str(addr.get('postalCode') or '')
        differs = (region != cur_region or pin != cur_pin)
        if differs and region_should_apply(level, slug):
            info['stale_region'] = True
            info['region_from'] = f"{cur_region}/{cur_pin}"
            info['region_to'] = f"{region}/{pin}"
        elif differs and level in ('L3',) or (slug in REGION_SKIP and differs):
            # a weaker signal disagrees with the baked value — report, never auto-fix
            info['region_lowconf_review'] = True
            info['region_from'] = f"{cur_region}/{cur_pin}"
            info['region_to'] = f"{region}/{pin} [{level}{' skip' if slug in REGION_SKIP else ''}]"
        # description staleness: JSON-LD desc == title (placeholder) & source has real short_info
        title = _striptags((rec.get('basic_details') or {}).get('job_title')
                           or rec.get('title') or '')
        cur_desc = _striptags(jp.get('description') or '')
        si = (rec.get('basic_details') or {}).get('short_information') or ''
        new_desc = clean_description(si, title)
        if cur_desc and title and cur_desc == title and new_desc and new_desc != title:
            info['stale_description'] = True
    return info


def heal_page(path, idx, idx_keys, diffs):
    """Apply fixes to one page. Returns list of change tags, [] if nothing changed."""
    slug = os.path.basename(os.path.dirname(path))
    try:
        html = open(path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return []
    if 'JobPosting' not in html:
        return []
    original = html
    changes = []

    # (A) delete duplicate microdata block(s) — always safe
    new_html, n = _MICRODATA_RE.subn('', html)
    if n:
        html = new_html
        changes.append(f'microdata_removed x{n}')
    else:
        new_html, n2 = _MICRODATA_DIV_RE.subn('', html)
        if n2:
            html = new_html
            changes.append(f'microdata_div_removed x{n2}')

    # (B)+(C) patch the JSON-LD JobPosting block
    m, jp = find_jobposting_ldblock(html)
    if m is not None and jp is not None:
        jp_changed = False

        # (C) directApply -> real boolean
        if not isinstance(jp.get('directApply', False), bool):
            v = str(jp.get('directApply')).strip().lower()
            jp['directApply'] = v in ('true', '1')
            jp_changed = True
            changes.append('directApply_coerced')

        rec = find_source(slug, idx, idx_keys)
        if rec is not None:
            # (B) region — only from the job's own stated location (L1/L2), never
            # an L3 keyword guess, the blind default, or a bad-source skip page.
            region, pin, level = detect_region(rec, slug)
            jl = jp.get('jobLocation')
            if not isinstance(jl, dict):
                jl = {'@type': 'Place'}; jp['jobLocation'] = jl
            addr = jl.get('address')
            if not isinstance(addr, dict):
                addr = {'@type': 'PostalAddress', 'addressCountry': 'IN'}
                jl['address'] = addr
            org = (rec.get('basic_details') or {}).get('organization_name') or \
                  (jp.get('hiringOrganization') or {}).get('name') or ''
            loc = (rec.get('basic_details') or {}).get('job_location') or ''
            cur_region = str(addr.get('addressRegion') or '')
            cur_pin = str(addr.get('postalCode') or '')
            if region_should_apply(level, slug) and (region != cur_region or pin != cur_pin):
                addr['addressCountry'] = 'IN'
                addr['addressRegion'] = region
                addr['postalCode'] = pin
                # locality: use city if clean else region (mirrors build_schemas)
                city = _striptags(loc)
                if (not city or ',' in city or len(city) > 28
                        or city.lower() in ('india', '')
                        or region.lower() in city.lower()):
                    city = ''
                addr['addressLocality'] = city or region
                addr['streetAddress'] = build_street(org, loc, region)
                jp_changed = True
                changes.append(f'region {cur_region}->{region}')

            # (B) description — INTENTIONALLY NOT auto-fixed.
            # Audit still counts `stale_description` (desc == title) for visibility,
            # but a large fraction of source basic_details.short_information is
            # polluted scraped junk ("DON'T MISS ... RRB 6565 Technician ...", AI
            # filler "Here is a government-linked job opportunity ..."). Replacing a
            # clean title-based description with that would make the schema WORSE.
            # description == title is valid for Google; leave it. Fix the source
            # short_information data quality separately, then re-enable here.

        if jp_changed:
            new_block = m.group(1) + json.dumps(jp, ensure_ascii=False) + m.group(3)
            html = html.replace(m.group(0), new_block, 1)

    if html != original:
        # atomic-ish write, same convention as fix_jobposting_schema.py
        open(path, 'w', encoding='utf-8').write(html)
        if len(diffs) < 5:
            diffs.append((os.path.relpath(path, ROOT), changes))
        return changes
    return []


# ── driver ───────────────────────────────────────────────────────────────────
def iter_pages(only):
    for base in SCAN_DIRS:
        for root, dirs, files in os.walk(os.path.join(ROOT, base)):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if f != 'index.html':
                    continue
                fp = os.path.join(root, f)
                if only and only not in fp.replace('\\', '/'):
                    continue
                yield fp


def main():
    args = [a for a in sys.argv[1:]]
    do_fix = '--fix' in args
    args = [a for a in args if a != '--fix']
    only = args[0] if args else None

    print("Loading source JSON index (jobs/data/*.json) ...")
    idx = build_source_index()
    idx_keys = list(idx.keys())
    print(f"  indexed {len(idx_keys)} source keys\n")

    if not do_fix:
        counts = defaultdict(int)
        samples = defaultdict(list)
        scanned = 0
        for fp in iter_pages(only):
            info = audit_page(fp, idx, idx_keys)
            if info is None:
                continue
            scanned += 1
            for key in ('has_duplicate_microdata', 'stale_region', 'stale_description',
                        'non_boolean_directApply', 'canonical_issue',
                        'orphaned_no_source_json', 'region_lowconf_review'):
                if info.get(key):
                    counts[key] += 1
                    if len(samples[key]) < 20:
                        extra = ''
                        if key in ('stale_region', 'region_lowconf_review'):
                            extra = f"  ({info.get('region_from')} -> {info.get('region_to')})"
                        samples[key].append(info['slug'] + extra)
        print("=" * 68)
        print(f"AUDIT REPORT (READ-ONLY) — {scanned} job pages scanned")
        print("=" * 68)
        order = ['has_duplicate_microdata', 'non_boolean_directApply', 'stale_region',
                 'stale_description', 'canonical_issue', 'orphaned_no_source_json',
                 'region_lowconf_review']
        labels = {
            'has_duplicate_microdata': 'Duplicate hidden microdata block (delete)',
            'non_boolean_directApply': 'directApply not a real boolean (coerce)',
            'stale_region':            'Region wrong vs source JSON, L1/L2 (auto-fix)',
            'stale_description':       'Description == title (REPORT ONLY — source short_info often junk, not auto-fixed)',
            'canonical_issue':         'canonical missing/duplicate',
            'orphaned_no_source_json': 'Orphan page — no source JSON (report only)',
            'region_lowconf_review':   'Region differs on weak/bad signal (MANUAL review, NOT auto-fixed)',
        }
        for key in order:
            print(f"\n[{counts[key]:>4}] {labels[key]}")
            for s in samples[key][:20]:
                print(f"        - {s}")
            if counts[key] > 20:
                print(f"        ... (+{counts[key] - 20} more)")
        print("\n" + "=" * 68)
        print("Nothing was modified. Re-run with --fix to apply A/B/C fixes.")
        print("=" * 68)
        # machine-readable summary
        summary_path = os.path.join(ROOT, 'heal_audit_summary.json')
        json.dump({'scanned': scanned, 'counts': dict(counts)},
                  open(summary_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print("JSON summary:", os.path.relpath(summary_path, ROOT))
        return 0

    # ── FIX MODE ──
    scanned = fixed = 0
    diffs = []
    tag_counts = defaultdict(int)
    for fp in iter_pages(only):
        if 'JobPosting' not in open(fp, encoding='utf-8', errors='ignore').read():
            continue
        scanned += 1
        ch = heal_page(fp, idx, idx_keys, diffs)
        if ch:
            fixed += 1
            for c in ch:
                tag_counts[c.split(' ')[0].split('->')[0]] += 1
    print("=" * 68)
    print(f"HEAL COMPLETE — scanned {scanned}, files changed {fixed}")
    print("=" * 68)
    for tag, c in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"  {c:>5}  {tag}")
    print("\nFirst changed files (spot-check):")
    for rel, ch in diffs:
        print(f"  {rel}\n        {', '.join(ch)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
