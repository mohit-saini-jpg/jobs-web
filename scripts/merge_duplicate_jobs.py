#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_duplicate_jobs.py — Part 1 of the Duplicate Job Pages fix.

Finds live jobs/data/*.json files whose on-disk slug differs from the
canonical slug that generate_all.py would produce TODAY (Priority 1→2→3).
Those are "stale registry" duplicates created in an earlier run when the
slug-registry entry was the only source of truth.

For each confirmed duplicate group (same canonical slug, same version
signature) this script:
  1. Picks the canonical survivor (folder name == canonical slug)
  2. Deletes the non-survivor jobs/<old-slug>/ folder & jobs/data/<old-slug>.json
  3. Appends a 301 redirect to _redirects
  4. Removes the old slug from sitemap-jobs.xml, .sitemap-content-hashes.json,
     jobs-index.json, data/sections-index.json, homepage-mini.json
  5. Corrects the data/slug-registry.json entry for that fingerprint

Genuinely different notification versions (different _version_signature)
are logged to DUPLICATE_MERGE_REVIEW_NEEDED.md instead.

Usage:
  python scripts/merge_duplicate_jobs.py           # dry run (safe, read-only)
  python scripts/merge_duplicate_jobs.py --execute # actually make changes
"""

import os, re, json, sys, shutil, hashlib, io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT       = Path(__file__).resolve().parent.parent
JOBS_DIR   = ROOT / 'jobs'
DATA_DIR   = JOBS_DIR / 'data'
REG_PATH   = ROOT / 'data' / 'slug-registry.json'
REDIRECTS  = ROOT / '_redirects'
SITEMAP_J  = ROOT / 'sitemap-jobs.xml'
HASHES_F   = ROOT / '.sitemap-content-hashes.json'
IDX_F      = ROOT / 'jobs-index.json'
SECTIONS_F = ROOT / 'data' / 'sections-index.json'
MINI_F     = ROOT / 'homepage-mini.json'
REPORT_F   = ROOT / 'DUPLICATE_MERGE_REPORT.md'
REVIEW_F   = ROOT / 'DUPLICATE_MERGE_REVIEW_NEEDED.md'
DRIFT_F    = ROOT / 'REGISTRY_DRIFT_LOG.md'

DRY_RUN = '--execute' not in sys.argv

# ── Replicated helpers (subset of generate_all.py) ────────────────────────────

_SR_STOP = frozenset((
    'the','and','for','of','in','to','a','an','with','on','at','by','top',
    'sarkari','jobs','recruitment','apply','online','offline','notification',
    'out','check','details','post','posts','vacancy','vacancies','form',
    'registration','last','date','here','now','download','pdf','2024',
    '2025','2026','2027','2028','latest','govt','government','result',
    'admit','card','answer','key','syllabus','exam','new','all','various',
))

def _sr_fingerprint(title):
    t = re.sub(r'[^a-z0-9\s]', ' ', str(title or '').lower())
    toks = [w for w in t.split() if w and w not in _SR_STOP and len(w) > 1]
    return ' '.join(sorted(toks))

def _norm_slug(s):
    if not s: return ''
    s = str(s).strip().lower()
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')[:80].strip('-')

def _canonical_slug_from_job(job_obj, registry):
    """Priority 1→2→3 (mirrors generate_all.get_canonical_slug)."""
    # Priority 1
    cs = str(job_obj.get('_canonical_slug') or '').strip()
    if cs:
        return _norm_slug(cs)
    # Priority 2
    raw = str(job_obj.get('slug') or '').strip()
    if raw:
        raw = re.sub(r'^sr_[a-z_]+-', '', raw)
        _tail = re.search(r'-([0-9a-f]{6,8})$', raw)
        if _tail and not _tail.group(1).isdigit():
            raw = raw[:-len(_tail.group(0))]
        s = _norm_slug(raw)
        if s:
            return s
    # Priority 3
    bd = job_obj.get('basic_details') or {}
    title = str(
        bd.get('job_title') or job_obj.get('title') or job_obj.get('name') or ''
    ).strip()
    if title:
        fp = _sr_fingerprint(title)
        if fp and fp in registry:
            return registry[fp]
        # generate fresh
        return _slugify(title)[:80].strip('-')
    return 'page'

def _slugify(text):
    t = str(text or '').lower()
    t = re.sub(r'[^a-z0-9\s-]', ' ', t)
    t = re.sub(r'[\s-]+', '-', t).strip('-')
    return t

# ── Version signature (mirrors generate_all._version_signature) ──────────────

def _extract_year(job):
    for src in (
        str((job.get('meta') or {}).get('articleSection', '')),
        str(job.get('year', '')),
        str(job.get('title', '')),
    ):
        m = re.search(r'\b(20\d{2})\b', src)
        if m: return m.group(1)
    return ''

def _extract_advt_no(job):
    for k in ('advt_no','advtNo','advertisement_no','advertisementNo',
              'notification_no','notificationNo'):
        v = str(job.get(k) or '').strip()
        if v:
            return re.sub(r'[^0-9a-z]+', '-', v.lower()).strip('-')
    for lk in ('subjectWiseVacancy','subject_wise_vacancy','categoryWiseVacancy'):
        rows = job.get(lk)
        if isinstance(rows, list):
            for r in rows:
                if isinstance(r, dict):
                    v = str(r.get('advtNo') or r.get('advt_no') or '').strip()
                    if v:
                        return re.sub(r'[^0-9a-z]+', '-', v.lower()).strip('-')
    m = re.search(r'advt[.\s-]*no[.\s-]*([0-9]+[/\-][0-9]{2,4})',
                  str(job.get('title', '')), re.I)
    if m:
        return re.sub(r'[^0-9a-z]+', '-', m.group(1).lower()).strip('-')
    return ''

def _pdf_name(job):
    links = job.get('importantLinks') or job.get('important_links') or []
    if isinstance(links, list):
        for it in links:
            if isinstance(it, dict):
                u = str(it.get('url') or '')
                if u.lower().endswith('.pdf'):
                    return re.sub(r'[^a-z0-9._-]', '',
                                  u.rsplit('/', 1)[-1].lower())
    return ''

def _version_signature(job):
    d = job.get('importantDates') or job.get('important_dates') or {}
    if isinstance(d, dict):
        dates = '|'.join(str(d.get(k, '')) for k in (
            'applicationBegin','application_begin','lastDateApplyOnline',
            'last_date_apply_online','last_date','examDate','exam_date'))
    else:
        dates = str(d)
    parts = [
        _extract_year(job),
        _extract_advt_no(job),
        dates,
        str(job.get('totalPost') or job.get('total_post') or
            job.get('total_vacancy') or ''),
        _pdf_name(job),
    ]
    raw = '::'.join(parts)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:10]

def _schema_completeness(job):
    """Score: prefer job with more non-empty structured fields."""
    bd = job.get('basic_details') or {}
    score = sum(1 for k in ('organization_name','total_vacancies','notification_number',
                             'application_mode','post_name','job_location')
                if str(bd.get(k) or '').strip())
    score += 1 if job.get('importantDates') or job.get('important_dates') else 0
    score += 1 if job.get('importantLinks') or job.get('important_links') else 0
    return score

# ── Load / save helpers ────────────────────────────────────────────────────────

def load_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def save_json(path, obj):
    if DRY_RUN: return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',',':'), sort_keys=True)

def load_text(path):
    try:
        return Path(path).read_text(encoding='utf-8')
    except Exception:
        return ''

def save_text(path, text):
    if DRY_RUN: return
    Path(path).write_text(text, encoding='utf-8')

# ── Core logic ─────────────────────────────────────────────────────────────────

def main():
    print(f"{'[DRY RUN] ' if DRY_RUN else '[EXECUTE] '}merge_duplicate_jobs.py")
    print(f"  Root: {ROOT}\n")

    registry = load_json(REG_PATH) or {}

    # 1. Walk jobs/data/*.json — compute canonical slug for each
    entries = {}  # disk_slug → {job, canonical, version_sig, json_path}
    for jf in sorted(DATA_DIR.glob('*.json')):
        disk_slug = jf.stem
        job = load_json(jf)
        if not isinstance(job, dict):
            continue
        canonical = _canonical_slug_from_job(job, registry)
        entries[disk_slug] = {
            'job': job,
            'canonical': canonical,
            'version_sig': _version_signature(job),
            'json_path': jf,
            'folder': JOBS_DIR / disk_slug,
        }

    # 2. Group disk_slugs by their canonical slug where disk_slug != canonical
    canon_groups = {}  # canonical_slug → list of disk_slugs
    for disk_slug, info in entries.items():
        canon = info['canonical']
        canon_groups.setdefault(canon, []).append(disk_slug)

    # Only care about groups with >1 member OR where the disk_slug differs from canon
    dup_groups = {
        canon: slugs
        for canon, slugs in canon_groups.items()
        if len(slugs) > 1 or (slugs and slugs[0] != canon)
    }

    print(f"  Found {len(dup_groups)} canonical slugs with duplicate/stale folders")

    merge_groups   = []  # (canonical, [old_slugs_to_delete], survivor_slug)
    review_groups  = []  # (canonical, slugs, reason)
    stats = {'groups': 0, 'deleted_folders': 0, 'redirects': 0,
             'registry_fixed': 0, 'review': 0}

    for canon, slugs in sorted(dup_groups.items()):
        stats['groups'] += 1

        # Get version signatures for all members of this group
        sigs = {s: entries[s]['version_sig'] for s in slugs}
        unique_sigs = set(sigs.values())

        # Conservative: if multiple genuinely different versions, skip
        if len(unique_sigs) > 1:
            # But only skip if ALL slugs are mismatched — if the canonical slug
            # itself exists and is unique, it's fine to leave the others as versioned
            non_canon = [s for s in slugs if s != canon]
            canon_in_group = [s for s in slugs if s == canon]
            if not canon_in_group:
                review_groups.append((
                    canon, slugs,
                    f"{len(unique_sigs)} different version signatures — may be "
                    f"genuine new-notification versions or data inconsistency"
                ))
                stats['review'] += 1
                continue
            # The canonical slug exists; non-canon slugs have different sigs → likely legit versions
            # Only merge non-canon slugs that share the same sig as the canonical version
            canon_sig = sigs[canon]
            to_merge   = [s for s in non_canon if sigs[s] == canon_sig]
            to_keep    = [s for s in non_canon if sigs[s] != canon_sig]
            if to_keep:
                review_groups.append((
                    canon, to_keep,
                    f"Differ from canonical's version sig — may be genuine re-announcements"
                ))
                stats['review'] += len(to_keep)
            if not to_merge:
                continue
            slugs = [canon] + to_merge
        else:
            to_merge = None  # all have same sig; pick survivor below

        # Pick survivor: prefer the slug whose name == canonical
        # If canonical doesn't exist on disk, prefer the one with more complete schema
        candidates = [s for s in slugs if s == canon]
        if not candidates:
            # No exact match — pick by schema completeness, then alphabetical (fewer suffixes)
            candidates = sorted(
                slugs,
                key=lambda s: (-_schema_completeness(entries[s]['job']), len(s))
            )
        survivor  = candidates[0]
        old_slugs = [s for s in slugs if s != survivor]

        if not old_slugs:
            continue

        merge_groups.append((canon, old_slugs, survivor))

    # 3. Execute (or describe) the merges
    new_redirects    = []
    registry_updates = {}  # fingerprint → new_slug
    slugs_to_remove  = []

    for canon, old_slugs, survivor in merge_groups:
        for old in old_slugs:
            info = entries[old]
            print(f"  MERGE: {old!r} -> {survivor!r} (canon={canon!r})")

            # a. Delete jobs/<old-slug>/
            folder = info['folder']
            if folder.exists():
                if not DRY_RUN:
                    shutil.rmtree(folder)
                print(f"    del folder: {folder.relative_to(ROOT)}")
                stats['deleted_folders'] += 1

            # b. Delete jobs/data/<old-slug>.json
            jpath = info['json_path']
            if jpath.exists():
                if not DRY_RUN:
                    jpath.unlink()
                print(f"    del json:   {jpath.relative_to(ROOT)}")

            # c. Redirect
            redirect_line = (
                f"/jobs/{old}/  /jobs/{survivor}/  301"
            )
            new_redirects.append(redirect_line)
            print(f"    redirect:   {redirect_line}")
            stats['redirects'] += 1

            # d. Registry update for all fingerprints pointing to old slug
            for fp, reg_slug in registry.items():
                if reg_slug == old:
                    registry_updates[fp] = survivor

            # e. Collect slug for index cleanup
            slugs_to_remove.append(old)

    # 4. Apply changes to ancillary files
    if new_redirects:
        print(f"\n  Writing {len(new_redirects)} redirects to _redirects ...")
        rtext = load_text(REDIRECTS)
        header = '\n# ══ Auto-merged duplicate job redirects ══\n'
        rtext = header + '\n'.join(new_redirects) + '\n\n' + rtext
        save_text(REDIRECTS, rtext)

    if slugs_to_remove:
        # sitemap-jobs.xml
        print(f"  Removing {len(slugs_to_remove)} entries from sitemap-jobs.xml ...")
        smap = load_text(SITEMAP_J)
        for s in slugs_to_remove:
            smap = re.sub(
                r'\s*<url><loc>[^<]*/jobs/' + re.escape(s) + r'/</loc>.*?</url>',
                '', smap, flags=re.S
            )
        save_text(SITEMAP_J, smap)

        # .sitemap-content-hashes.json
        print(f"  Removing entries from .sitemap-content-hashes.json ...")
        hashes = load_json(HASHES_F) or {}
        for s in slugs_to_remove:
            hashes.pop(s, None)
        save_json(HASHES_F, hashes)

        # jobs-index.json
        print(f"  Removing entries from jobs-index.json ...")
        idx = load_json(IDX_F)
        if isinstance(idx, dict):
            for s in slugs_to_remove:
                idx.pop(s, None)
            save_json(IDX_F, idx)

        # data/sections-index.json
        print(f"  Removing entries from data/sections-index.json ...")
        sections = load_json(SECTIONS_F)
        if isinstance(sections, dict):
            slug_set = set(slugs_to_remove)
            for cat in sections:
                if isinstance(sections[cat], list):
                    sections[cat] = [
                        e for e in sections[cat]
                        if isinstance(e, dict) and e.get('slug') not in slug_set
                    ]
            save_json(SECTIONS_F, sections)

        # homepage-mini.json (jobs array has 's' field for slug)
        print(f"  Removing entries from homepage-mini.json ...")
        mini = load_json(MINI_F)
        if isinstance(mini, dict) and isinstance(mini.get('jobs'), list):
            slug_set = set(slugs_to_remove)
            mini['jobs'] = [
                j for j in mini['jobs']
                if j.get('s') not in slug_set
            ]
            save_json(MINI_F, mini)

    # 5. Fix slug registry
    if registry_updates:
        print(f"  Correcting {len(registry_updates)} registry entries ...")
        registry.update(registry_updates)
        if not DRY_RUN:
            with open(REG_PATH, 'w', encoding='utf-8') as f:
                json.dump(registry, f, ensure_ascii=False,
                          separators=(',',':'), sort_keys=True)
        stats['registry_fixed'] = len(registry_updates)

    # 6. Write reports
    _write_merge_report(stats, merge_groups, review_groups)
    _write_review_file(review_groups)
    _write_drift_init()

    print(f"\n{'[DRY RUN] ' if DRY_RUN else ''}Done.")
    print(f"  Groups found:      {stats['groups']}")
    print(f"  Folders deleted:   {stats['deleted_folders']}")
    print(f"  Redirects added:   {stats['redirects']}")
    print(f"  Registry fixed:    {stats['registry_fixed']}")
    print(f"  For manual review: {stats['review']}")
    if DRY_RUN:
        print("\n  Re-run with --execute to apply changes.")


def _write_merge_report(stats, merge_groups, review_groups):
    total_deleted = sum(len(olds) for _, olds, _ in merge_groups)
    lines = [
        "# DUPLICATE_MERGE_REPORT",
        "",
        f"- Canonical groups found: {stats['groups']}",
        f"- Non-survivor folders deleted: {total_deleted}",
        f"- Redirects added to _redirects: {stats['redirects']}",
        f"- slug-registry.json entries corrected: {stats['registry_fixed']}",
        f"- Groups flagged for manual review: {stats['review']}",
        "",
        "## Merged groups",
        "",
    ]
    for canon, olds, survivor in merge_groups:
        lines.append(f"### canonical: `{canon}`")
        lines.append(f"  Survivor: `{survivor}`")
        for old in olds:
            lines.append(f"  Deleted:  `{old}`  → redirect to `/jobs/{survivor}/`")
        lines.append("")
    mode = "DRY RUN (no changes made)" if DRY_RUN else "EXECUTED"
    lines.append(f"\n_Report generated in {mode} mode._")
    save_text(ROOT / 'DUPLICATE_MERGE_REPORT.md', '\n'.join(lines))
    if DRY_RUN:
        # Always write even in dry-run so user can review
        (ROOT / 'DUPLICATE_MERGE_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def _write_review_file(review_groups):
    if not review_groups:
        save_text(ROOT / 'DUPLICATE_MERGE_REVIEW_NEEDED.md',
                  "# DUPLICATE_MERGE_REVIEW_NEEDED\n\nNo items require manual review.\n")
        if DRY_RUN:
            (ROOT / 'DUPLICATE_MERGE_REVIEW_NEEDED.md').write_text(
                "# DUPLICATE_MERGE_REVIEW_NEEDED\n\nNo items require manual review.\n",
                encoding='utf-8')
        return
    lines = [
        "# DUPLICATE_MERGE_REVIEW_NEEDED",
        "",
        "These groups were NOT auto-merged because version signatures differ.",
        "Manually verify whether these are genuine re-announcements or true duplicates.",
        "",
    ]
    for canon, slugs, reason in review_groups:
        lines.append(f"### canonical: `{canon}`")
        lines.append(f"  Reason: {reason}")
        for s in slugs:
            lines.append(f"  Slug: `{s}`")
        lines.append("")
    text = '\n'.join(lines)
    # Always write even in dry-run
    (ROOT / 'DUPLICATE_MERGE_REVIEW_NEEDED.md').write_text(text, encoding='utf-8')


def _write_drift_init():
    """Create REGISTRY_DRIFT_LOG.md if it doesn't exist (Part 2 will append to it)."""
    if not DRIFT_F.exists():
        DRIFT_F.write_text(
            "# REGISTRY_DRIFT_LOG\n\n"
            "Auto-populated by generate_all.py when a job's slug field (Priority 2)\n"
            "differs from a stale slug-registry entry for the same fingerprint.\n\n",
            encoding='utf-8'
        )


if __name__ == '__main__':
    main()
