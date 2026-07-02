#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brand_seo_audit.py — Brand-authority / homepage-consolidation guardrail.

Prevents the "topsarkarijobs" brand-ranking regression from coming back by
checking, across the generated static site:

  1. Duplicate homepage-equivalent URLs (index.html / view.html) that are
     INTERNALLY linked (external links to some .../index.html are ignored).
  2. Missing / non-www canonical tags.
  3. Sitemaps containing more than one homepage-equivalent <loc>.
  4. Presence of the /index.html and /view.html -> / 301 rules in _redirects.

Run manually before deploy:   python brand_seo_audit.py
Exit code is 0 when clean, 1 when issues are found (CI-friendly).
"""
import os
import re
import sys
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
HOMEPAGE_CANONICAL = "https://www.topsarkarijobs.com/"
SKIP_DIRS = {".git", ".github", "node_modules", "backups", "__pycache__"}
# Templates / fragments / dev files — not standalone indexed pages, so they are
# not expected to carry a canonical tag. Exclude from the canonical audit.
SKIP_FILES = {
    "header.html", "footer.html", "job.html", "state-job-detail.html",
    "education-detail.html", "offline.html", "og-template.html", "redirect.html",
    "preload_snippet.html", "integration-snippet.html", "seo-audit-report.html",
    "seo-optimization-code.html", "job_html_patch_instructions.html", "r.html",
    "cache-dashboard.html", "view.html", "404.html",
}


def _is_template(rel):
    base = os.path.basename(rel).lower()
    return (base in SKIP_FILES or base.endswith("-snippet.html")
            or base.endswith("-template.html") or base.endswith("_snippet.html"))

# Internal (root-relative / relative) links to the homepage duplicates.
# NOTE: external links like href="https://gov.in/x/index.html" are NOT matched
# because we only look for the root-relative / bare forms.
_DUP_LINK_PATTERNS = [
    re.compile(r'href="/index\.html"'), re.compile(r'href="index\.html"'),
    re.compile(r'href="\./index\.html"'), re.compile(r'href="/view\.html"'),
    re.compile(r'href="view\.html"'), re.compile(r'href="\./view\.html"'),
]
_CANON_RE = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)


def _iter_html():
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".html"):
                yield os.path.join(root, f)


def find_duplicate_homepage_links():
    hits = []
    for path in _iter_html():
        try:
            content = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for pat in _DUP_LINK_PATTERNS:
            if pat.search(content):
                hits.append((os.path.relpath(path, ROOT), pat.pattern))
    return hits


def check_canonical_consistency(limit=60):
    missing, non_www = [], []
    for path in _iter_html():
        rel = os.path.relpath(path, ROOT)
        # Templates / fragments / redirect stubs are not indexed pages — skip.
        if _is_template(rel):
            continue
        try:
            content = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        m = _CANON_RE.search(content)
        if not m:
            if len(missing) < limit:
                missing.append(rel)
        elif "www." not in m.group(1):
            if len(non_www) < limit:
                non_www.append((rel, m.group(1)))
    return missing, non_www


def check_sitemaps():
    issues = []
    home_variants = re.compile(
        r"<loc>https://www\.topsarkarijobs\.com/(index\.html|view\.html)</loc>", re.I)
    for path in os.listdir(ROOT):
        if path.startswith("sitemap") and path.endswith(".xml"):
            try:
                content = open(os.path.join(ROOT, path), encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for bad in home_variants.findall(content):
                issues.append((path, bad))
    return issues


def check_redirects():
    """Site is hosted on Vercel — redirects live in vercel.json (the Netlify-style
    _redirects file is ignored by Vercel). Ensure /index.html and /view.html
    consolidate to / there."""
    path = os.path.join(ROOT, "vercel.json")
    if not os.path.exists(path):
        return ["vercel.json MISSING (Vercel redirects config)"]
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"vercel.json parse error: {e}"]
    srcs = {r.get("source"): r for r in data.get("redirects", []) if isinstance(r, dict)}
    missing = []
    for dup in ("/index.html", "/view.html"):
        r = srcs.get(dup)
        if not r or r.get("destination") != "/":
            missing.append(f"{dup} -> / redirect missing in vercel.json")
    return missing


def main():
    dup_links = find_duplicate_homepage_links()
    missing_canon, non_www = check_canonical_consistency()
    sitemap_issues = check_sitemaps()
    redirect_issues = check_redirects()

    report = {
        "duplicate_homepage_internal_links": dup_links,
        "pages_missing_canonical": missing_canon,
        "non_www_canonical": non_www,
        "sitemap_homepage_duplicates": sitemap_issues,
        "redirect_rule_issues": redirect_issues,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    problems = (len(dup_links) + len(missing_canon) + len(non_www)
                + len(sitemap_issues) + len(redirect_issues))
    if problems:
        print(f"\n[BRAND-SEO] {problems} issue(s) found.", file=sys.stderr)
        return 1
    print("\n[BRAND-SEO] All checks passed ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
