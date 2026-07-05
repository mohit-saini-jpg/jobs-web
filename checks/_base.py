# -*- coding: utf-8 -*-
"""
Shared contract + helpers for SEO Guardian check plugins.

PLUGIN CONTRACT
---------------
Each checks/<name>.py module defines:

    CHECK_ID = "short_slug"              # unique id, appears in the report

  Per-file check (default):
    def detect(filepath: str, html: str) -> list[Issue]
    def fix(filepath: str, html: str, issue: Issue) -> str   # return NEW html

  Global / cross-file check:
    SCOPE = "global"
    def detect_global(ctx: dict) -> list[Issue]
    def fix_global(ctx: dict, issues: list[Issue]) -> None   # applies fixes in place

Rules every plugin must honour:
  * detect() must NEVER raise on a single bad file — return [] instead. The
    orchestrator also wraps every call in try/except, but be defensive.
  * fix() returns the full new HTML string. If it cannot safely fix, return the
    html unchanged (the orchestrator then keeps the issue as UNFIXABLE).
  * Only touch structural / SEO-metadata. NEVER edit job title, description,
    vacancy, salary or date DATA fields.
  * Issues that cannot be auto-fixed must set fixable=False in detect().
"""
from dataclasses import dataclass, field

# ── severity ────────────────────────────────────────────────────────────────
CRITICAL = "critical"          # blocks the sitemap ping if left UNFIXABLE
NON_CRITICAL = "non_critical"  # reported/fixed but never blocks the ping


@dataclass
class Issue:
    check: str                 # CHECK_ID of the plugin that raised it
    severity: str              # CRITICAL | NON_CRITICAL
    message: str               # human-readable one-liner
    filepath: str = ""         # page the issue belongs to ("" for run-level)
    fixable: bool = True        # False -> orchestrator won't call fix()
    meta: dict = field(default_factory=dict)  # extra data fix() may need


# ── HTML structural safety net ──────────────────────────────────────────────
_ANCHORS = ("<html", "</html>", "<head", "</head>", "<body", "</body>")


def structural_ok(old_html: str, new_html: str) -> bool:
    """Conservative well-formedness gate used AFTER every fix. If a fix breaks
    page structure we revert instead of shipping broken HTML. Checks that the
    key document anchors survive and <script>/</script> stay balanced. This is a
    safety net, not a full validator — when unsure it returns False so the fix
    is rejected (fail safe)."""
    if not new_html:
        return False
    low = new_html.lower()
    for a in _ANCHORS:
        if low.count(a) < 1:
            return False
    if low.count("<script") != low.count("</script>"):
        return False
    return True


# ── ld+json iteration (shared) ──────────────────────────────────────────────
import re as _re
_LDJSON_RE = _re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', _re.S | _re.I)


def iter_ldjson(html: str):
    """Yield (raw_inner_json_str, full_match_str) for every ld+json block."""
    for m in _LDJSON_RE.finditer(html):
        yield m.group(1), m.group(0)
