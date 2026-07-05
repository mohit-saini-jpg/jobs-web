# -*- coding: utf-8 -*-
"""Adapter: wraps heal_jobposting_schema.py (does NOT reimplement it).

detect() = heal's own audit_page(); fix() = heal's heal_page() (which removes the
duplicate microdata block, coerces directApply to a real boolean, and re-derives
a stale jobLocation region from the job's own source JSON). heal_page writes the
file in place, so fix() re-reads and returns the new HTML to the orchestrator."""
import heal_jobposting_schema as H
from ._base import Issue, CRITICAL, NON_CRITICAL

CHECK_ID = "jobposting_schema"

_IDX = None
_KEYS = None


def _index():
    global _IDX, _KEYS
    if _IDX is None:
        _IDX = H.build_source_index()
        _KEYS = list(_IDX.keys())
    return _IDX, _KEYS


def detect(filepath, html):
    if "JobPosting" not in html:
        return []
    idx, keys = _index()
    try:
        info = H.audit_page(filepath, idx, keys)
    except Exception:
        return []
    if not info:
        return []
    issues = []
    if info.get("has_duplicate_microdata"):
        issues.append(Issue(CHECK_ID, CRITICAL,
            "duplicate hidden JobPosting microdata block", filepath, True,
            {"kind": "microdata"}))
    if info.get("non_boolean_directApply"):
        issues.append(Issue(CHECK_ID, CRITICAL,
            "directApply is not a real boolean", filepath, True,
            {"kind": "directApply"}))
    if info.get("stale_region"):
        issues.append(Issue(CHECK_ID, CRITICAL,
            f"stale jobLocation region ({info.get('region_from')} -> "
            f"{info.get('region_to')})", filepath, True, {"kind": "region"}))
    # informational — heal intentionally does NOT auto-fix these
    if info.get("region_lowconf_review"):
        issues.append(Issue(CHECK_ID, NON_CRITICAL,
            f"region differs on weak/bad signal ({info.get('region_from')} -> "
            f"{info.get('region_to')}) — manual review", filepath, False,
            {"kind": "region_review"}))
    return issues


def fix(filepath, html, issue):
    if not issue.fixable:
        return html
    idx, keys = _index()
    try:
        H.heal_page(filepath, idx, keys, [])   # fixes all three kinds at once
        return open(filepath, encoding="utf-8", errors="ignore").read()
    except Exception:
        return html
