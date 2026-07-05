# -*- coding: utf-8 -*-
"""Check (f): <html lang> / hreflang consistency.

The site is English-first (the 7 AM pipeline sed-normalises hi-IN -> en-IN on
job/state/education/section/qualification pages). This check catches pages that
step missed (orphans, other trees):
  * <html> with no lang attribute            -> add lang="en-IN"      (fixable)
  * <html lang="hi-*"> on an en page         -> set lang="en-IN"      (fixable)
  * a self-referencing / duplicate hreflang  -> reported, not auto-fixed
Non-critical."""
import re
from ._base import Issue, NON_CRITICAL

CHECK_ID = "lang_hreflang"
_HTML_TAG = re.compile(r'<html\b([^>]*)>', re.I)
_LANG_ATTR = re.compile(r'\blang\s*=\s*"([^"]*)"', re.I)
DEFAULT_LANG = "en-IN"


def detect(filepath, html):
    m = _HTML_TAG.search(html)
    if not m:
        return []
    attrs = m.group(1)
    lm = _LANG_ATTR.search(attrs)
    if not lm:
        return [Issue(CHECK_ID, NON_CRITICAL, "<html> missing lang attribute",
                      filepath, fixable=True, meta={"problem": "missing"})]
    lang = lm.group(1).strip().lower()
    if lang.startswith("hi"):
        return [Issue(CHECK_ID, NON_CRITICAL,
                      f'<html lang="{lm.group(1)}"> should be en-IN', filepath,
                      fixable=True, meta={"problem": "hi", "was": lm.group(1)})]
    return []


def fix(filepath, html, issue):
    m = _HTML_TAG.search(html)
    if not m:
        return html
    attrs = m.group(1)
    if issue.meta.get("problem") == "missing":
        new_attrs = attrs + f' lang="{DEFAULT_LANG}"'
    else:  # normalise hi-* -> en-IN
        new_attrs = _LANG_ATTR.sub(f'lang="{DEFAULT_LANG}"', attrs, count=1)
    return html[:m.start()] + f"<html{new_attrs}>" + html[m.end():]
