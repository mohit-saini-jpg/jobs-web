# -*- coding: utf-8 -*-
"""Check (g): orphan / unbalanced AI blocks left by ai_html_enricher.py.

ai_html_enricher wraps injected content in paired markers:
    <!-- tsj-ai-enriched -->  ... <!-- tsj-ai-enriched -->   (open/close, even count)
    <!-- TSJ_AI_BLOCK_START --> ... <!-- TSJ_AI_BLOCK_END -->
    <!-- TSJ_AI_FAQ_START -->   ... <!-- TSJ_AI_FAQ_END -->
An interrupted enrich run can leave these unbalanced. We DETECT that (report
only). We do NOT auto-remove/close: we cannot know where the missing boundary
belongs without risking deletion of real content (DATA). Non-critical — the
comment markers don't break rendering; surfaced for a human / a re-run of the
enricher to repair."""
from ._base import Issue, NON_CRITICAL

CHECK_ID = "ai_marker_integrity"

# (label, open_marker, close_marker) — enriched uses the SAME marker twice
_PAIRS = [
    ("tsj-ai-enriched", "<!-- tsj-ai-enriched -->", "<!-- tsj-ai-enriched -->"),
    ("TSJ_AI_BLOCK", "<!-- TSJ_AI_BLOCK_START -->", "<!-- TSJ_AI_BLOCK_END -->"),
    ("TSJ_AI_FAQ", "<!-- TSJ_AI_FAQ_START -->", "<!-- TSJ_AI_FAQ_END -->"),
]


def detect(filepath, html):
    issues = []
    for label, opn, cls in _PAIRS:
        if opn == cls:
            # same marker used to open & close -> count must be even
            n = html.count(opn)
            if n % 2 != 0:
                issues.append(Issue(CHECK_ID, NON_CRITICAL,
                    f"orphan '{label}' marker (odd count {n})", filepath,
                    fixable=False, meta={"label": label, "count": n}))
        else:
            no, nc = html.count(opn), html.count(cls)
            if no != nc:
                issues.append(Issue(CHECK_ID, NON_CRITICAL,
                    f"unbalanced '{label}' ({no} START vs {nc} END)", filepath,
                    fixable=False, meta={"label": label, "start": no, "end": nc}))
    return issues


def fix(filepath, html, issue):
    return html  # never auto-fixed
