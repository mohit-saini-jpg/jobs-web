#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_schema_dates.py — normalize every schema.org datetime value in JSON-LD to a
full ISO-8601 string with the India timezone (+05:30), site-wide.

Google's Rich Results / Search Console flags date-only values ("2026-06-17") on
datePublished/dateModified/datePosted/validThrough/startDate/... as
"Invalid datetime value" / "missing a timezone". This script converts them to
"2026-06-17T00:00:00+05:30" (or T23:59:59 for end-type fields) so no page — old or
newly generated — ever carries a malformed datetime.

Idempotent. Runs across ALL *.html; only rewrites blocks it actually changes.
"""
import os
import re
import sys
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", ".github", "node_modules", "backups", "__pycache__"}
TZ = "+05:30"
# fields whose bare date should snap to start-of-day, and end-of-day respectively
START_FIELDS = {"datePosted", "datePublished", "dateModified", "dateCreated",
                "uploadDate", "startDate", "availabilityStarts", "foundingDate"}
END_FIELDS = {"validThrough", "expires", "endDate", "availabilityEnds"}
_LDJSON_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
_DATEONLY_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_DT_NOTZ_RE = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$')


def _norm(v, end=False):
    if not isinstance(v, str):
        return v, False
    s = v.strip()
    if _DATEONLY_RE.match(s):
        return s + ("T23:59:59" + TZ if end else "T00:00:00" + TZ), True
    if _DT_NOTZ_RE.match(s):
        return s + TZ, True
    return v, False


def _walk(o):
    changed = False
    if isinstance(o, dict):
        for k, val in list(o.items()):
            if k in START_FIELDS or k in END_FIELDS:
                # foundingDate is legitimately a year/date — leave bare dates alone
                if k == "foundingDate":
                    continue
                nv, c = _norm(val, end=(k in END_FIELDS))
                if c:
                    o[k] = nv
                    changed = True
                else:
                    changed = _walk(val) or changed
            else:
                changed = _walk(val) or changed
    elif isinstance(o, list):
        for item in o:
            changed = _walk(item) or changed
    return changed


def patch_file(path):
    try:
        html = open(path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return False
    if 'application/ld+json' not in html:
        return False
    new_html = html
    for m in _LDJSON_RE.finditer(html):
        try:
            data = json.loads(m.group(2))
        except Exception:
            continue
        if _walk(data):
            repl = m.group(1) + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + m.group(3)
            new_html = new_html.replace(m.group(0), repl, 1)
    if new_html != html:
        open(path, 'w', encoding='utf-8').write(new_html)
        return True
    return False


def main():
    patched = scanned = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith('.html'):
                continue
            scanned += 1
            if patch_file(os.path.join(root, f)):
                patched += 1
    print(f"[schema-dates] scanned {scanned} HTML files, normalized datetimes in {patched}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
