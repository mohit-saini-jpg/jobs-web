# -*- coding: utf-8 -*-
"""Check (c): <img> tags missing an alt attribute.

Auto-fix adds alt="" (empty = decorative). This is the only safe universal fix:
inventing descriptive alt text would be guessing DATA. Empty alt satisfies
accessibility/SEO validators without asserting anything false. Non-critical."""
import re
from ._base import Issue, NON_CRITICAL

CHECK_ID = "img_alt"
_IMG_RE = re.compile(r'<img\b[^>]*>', re.I)
_HAS_ALT = re.compile(r'\balt\s*=', re.I)


def detect(filepath, html):
    missing = [t for t in _IMG_RE.findall(html) if not _HAS_ALT.search(t)]
    if not missing:
        return []
    return [Issue(CHECK_ID, NON_CRITICAL,
                  f"{len(missing)} <img> missing alt", filepath,
                  fixable=True, meta={"count": len(missing)})]


def fix(filepath, html, issue):
    def _add(m):
        tag = m.group(0)
        if _HAS_ALT.search(tag):
            return tag
        selfclose = tag.endswith("/>")
        core = (tag[:-2] if selfclose else tag[:-1]).rstrip()
        return core + ' alt=""' + ("/>" if selfclose else ">")
    return _IMG_RE.sub(_add, html)
