# -*- coding: utf-8 -*-
"""Check (d): malformed JSON-LD — every <script type="application/ld+json">
block must parse with json.loads.

CRITICAL + fixable=False: broken structured data is exactly the kind of issue
that must BLOCK the sitemap ping (don't push a page with invalid schema to
Google). We do not attempt risky auto-repair of arbitrary broken JSON — that
could silently corrupt valid data. A malformed block surfaces as UNFIXABLE so
SEO_CLEAN flips to false and the ping is skipped until a real fix lands."""
import json
from ._base import Issue, CRITICAL, iter_ldjson

CHECK_ID = "jsonld_valid"


def detect(filepath, html):
    issues = []
    for idx, (raw, _full) in enumerate(iter_ldjson(html)):
        try:
            json.loads(raw)
        except Exception as ex:
            snippet = raw.strip().replace("\n", " ")[:80]
            issues.append(Issue(
                CHECK_ID, CRITICAL,
                f"malformed JSON-LD block #{idx + 1}: {ex}", filepath,
                fixable=False, meta={"block": idx, "snippet": snippet}))
    return issues


def fix(filepath, html, issue):
    return html  # never auto-repaired — reported as unfixable/critical
