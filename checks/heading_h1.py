# -*- coding: utf-8 -*-
"""Check (b): missing or duplicate <h1>.

REPORT ONLY (fixable=False). Auto-demoting an extra <h1> to <h2>, or inventing a
missing <h1>, changes the visible heading structure / content, which violates the
"never touch data, structural-metadata only, don't guess" rule. Non-critical, so
it never blocks the ping — it is surfaced for a human to correct."""
import re
from ._base import Issue, NON_CRITICAL

CHECK_ID = "heading_h1"
_H1_RE = re.compile(r'<h1\b[^>]*>', re.I)


def detect(filepath, html):
    n = len(_H1_RE.findall(html))
    if n == 0:
        return [Issue(CHECK_ID, NON_CRITICAL, "missing <h1>", filepath,
                      fixable=False, meta={"count": 0})]
    if n > 1:
        return [Issue(CHECK_ID, NON_CRITICAL, f"duplicate <h1> (x{n})", filepath,
                      fixable=False, meta={"count": n})]
    return []


def fix(filepath, html, issue):
    return html  # never auto-fixed
