#!/usr/bin/env python3
"""
sanitize_short_info.py — Part 3c one-time fix.

Strips "DON'T MISS" sidebar-widget text that was concatenated into
short_information by the scraper. Operates in-place on jobs/data/*.json.

Usage:
  python scripts/sanitize_short_info.py          # dry run
  python scripts/sanitize_short_info.py --execute
"""

import os, re, json, sys
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'jobs' / 'data'
DRY_RUN  = '--execute' not in sys.argv

_DONT_MISS_RE = re.compile(r"DON[''']?T\s+MISS.*", re.I | re.S)

def sanitize(text):
    return _DONT_MISS_RE.sub('', str(text or '')).strip()

def process():
    files    = sorted(DATA_DIR.glob('*.json'))
    patched  = 0
    skipped  = 0

    for jf in files:
        try:
            raw = jf.read_text(encoding='utf-8')
        except Exception:
            continue

        try:
            job = json.loads(raw)
        except Exception:
            continue

        changed = False

        # Patch at every location short_information can appear
        bd = job.get('basic_details')
        if isinstance(bd, dict):
            si = bd.get('short_information', '')
            if si and _DONT_MISS_RE.search(str(si)):
                bd['short_information'] = sanitize(si)
                changed = True

        for field in ('short_information', 'jobs_info', 'short_info'):
            si = job.get(field, '')
            if si and _DONT_MISS_RE.search(str(si)):
                job[field] = sanitize(si)
                changed = True

        if changed:
            patched += 1
            print(f"  {'[DRY] ' if DRY_RUN else ''}patch: {jf.name}")
            if not DRY_RUN:
                jf.write_text(
                    json.dumps(job, ensure_ascii=False, separators=(',', ':')),
                    encoding='utf-8'
                )
        else:
            skipped += 1

    print(f"\n{'[DRY RUN] ' if DRY_RUN else ''}Done.")
    print(f"  Files patched: {patched}")
    print(f"  Files clean:   {skipped}")
    if DRY_RUN:
        print("  Re-run with --execute to apply changes.")

if __name__ == '__main__':
    process()
