# -*- coding: utf-8 -*-
"""Check (a): missing/duplicate <title>, <meta name="description">,
<link rel="canonical">.

Auto-fix ONLY removes duplicates (keeps the first occurrence) — that is a safe
structural fix. A MISSING tag is marked fixable=False (we must not invent title
or description text — that would be fabricating DATA)."""
import re
from ._base import Issue, CRITICAL, NON_CRITICAL

CHECK_ID = "meta_head"

_TITLE_RE = re.compile(r'<title\b[^>]*>.*?</title>', re.S | re.I)
_DESC_RE = re.compile(r'<meta\b[^>]*\bname\s*=\s*"description"[^>]*>', re.I)
_CANON_RE = re.compile(r'<link\b[^>]*\brel\s*=\s*"canonical"[^>]*>', re.I)

# (kind, regex, severity, human label)
_TARGETS = [
    ("title", _TITLE_RE, CRITICAL, "<title>"),
    ("description", _DESC_RE, NON_CRITICAL, '<meta name="description">'),
    ("canonical", _CANON_RE, CRITICAL, '<link rel="canonical">'),
]


def _head(html):
    m = re.search(r'<head\b[^>]*>(.*?)</head>', html, re.S | re.I)
    return m.group(1) if m else html


def detect(filepath, html):
    issues = []
    head = _head(html)
    for kind, rx, sev, label in _TARGETS:
        n = len(rx.findall(head))
        if n == 0:
            issues.append(Issue(CHECK_ID, sev, f"missing {label}", filepath,
                                fixable=False, meta={"kind": kind, "problem": "missing"}))
        elif n > 1:
            issues.append(Issue(CHECK_ID, sev, f"duplicate {label} (x{n})", filepath,
                                fixable=True, meta={"kind": kind, "problem": "duplicate"}))
    return issues


def fix(filepath, html, issue):
    if issue.meta.get("problem") != "duplicate":
        return html  # missing tags are not auto-fixable
    kind = issue.meta.get("kind")
    rx = dict((k, r) for k, r, _s, _l in _TARGETS)[kind]
    # remove every occurrence AFTER the first, inside <head>
    m = re.search(r'(<head\b[^>]*>)(.*?)(</head>)', html, re.S | re.I)
    if not m:
        return html
    head_inner = m.group(2)
    seen = {"n": 0}

    def _drop(mo):
        seen["n"] += 1
        return mo.group(0) if seen["n"] == 1 else ""
    new_inner = rx.sub(_drop, head_inner)
    if new_inner == head_inner:
        return html
    return html[:m.start(2)] + new_inner + html[m.end(2):]
