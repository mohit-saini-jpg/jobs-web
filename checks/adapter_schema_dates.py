# -*- coding: utf-8 -*-
"""Adapter: wraps fix_schema_dates.py (does NOT reimplement it).

fix_schema_dates.patch_file() normalises schema datetimes to ISO-8601 + IST tz
and writes in place. It has no pure "would-change" function, so detect() runs the
REAL patch_file on a throwaway temp copy of the HTML (zero touch to the actual
file) and reports if it would change. fix() runs patch_file on the real path."""
import os
import tempfile
import fix_schema_dates as FSD
from ._base import Issue, NON_CRITICAL

CHECK_ID = "schema_dates"


def detect(filepath, html):
    if "application/ld+json" not in html:
        return []
    tmp = None
    would = False
    try:
        fd, tmp = tempfile.mkstemp(suffix=".html")
        os.close(fd)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(html)
        would = FSD.patch_file(tmp)      # runs on the COPY, not the real file
    except Exception:
        would = False
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except Exception:
                pass
    if would:
        return [Issue(CHECK_ID, NON_CRITICAL,
                      "schema datetime not ISO-8601 / missing timezone", filepath,
                      True, {})]
    return []


def fix(filepath, html, issue):
    try:
        FSD.patch_file(filepath)
        return open(filepath, encoding="utf-8", errors="ignore").read()
    except Exception:
        return html
