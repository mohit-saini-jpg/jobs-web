# -*- coding: utf-8 -*-
"""Adapter: wraps expire_jobs.py (does NOT reimplement it).

detect() = expire_jobs.is_expired_and_open(); fix() = expire_jobs.close_page().
Never touches JobPosting schema/data -- only replaces the visible apply-CTA
with a closed notice once validThrough has passed. NON_CRITICAL: this is a
UX-honesty fix on an already-indexed page, never a reason to block the
sitemap ping."""
import expire_jobs as X
from ._base import Issue, NON_CRITICAL

CHECK_ID = "expired_job"


def detect(filepath, html):
    if not X.is_expired_and_open(html):
        return []
    vt = X.get_valid_through(html)
    return [Issue(CHECK_ID, NON_CRITICAL,
                  f"expired job (validThrough {vt}) still shows a live apply CTA",
                  filepath, fixable=True, meta={"validThrough": str(vt)})]


def fix(filepath, html, issue):
    return X.close_page(html)
