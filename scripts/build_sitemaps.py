#!/usr/bin/env python3
"""
build_sitemaps.py  —  C5 FIX
Rebuilds all sitemaps from the real folder tree so they are never empty/circular.
- sitemap-index.xml  : the ONLY <sitemapindex> (lists child urlsets, never another index)
- sitemap.xml        : converted to a real urlset of core pages (no longer a second index)
- child sitemaps     : populated from actual directories that contain index.html
Run from repo root:  python3 scripts/build_sitemaps.py
"""
import os
import re
from datetime import date

# ROOT = repo root. Works whether this script lives in scripts/ or .github/workflows/
# because the workflow always runs it from the repo root (CWD).
ROOT = os.environ.get("GITHUB_WORKSPACE") or os.getcwd()
# Safety: if jobs/ isn't here, walk up from the file location to find it.
if not os.path.isdir(os.path.join(ROOT, "jobs")):
    _p = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        if os.path.isdir(os.path.join(_p, "jobs")):
            ROOT = _p; break
        _p = os.path.dirname(_p)
BASE = "https://www.topsarkarijobs.com"
TODAY = date.today().isoformat()

# FIX #11: per-job lastmod — load first-seen dates so /jobs/ URLs get a real
# lastmod (the date the job was first published) instead of the deploy date.
# Google ignores sitemaps where every lastmod is identical to "today".
import json as _json
_JOB_LASTMOD = {}
try:
    _fs_path = os.path.join(ROOT, "data", "job-first-seen.json")
    if os.path.isfile(_fs_path):
        with open(_fs_path, encoding="utf-8") as _f:
            _JOB_LASTMOD = _json.load(_f)
except Exception:
    _JOB_LASTMOD = {}

def _lastmod_for(url):
    """Return a real lastmod for /jobs/<slug>/ URLs from first-seen data."""
    try:
        if "/jobs/" in url:
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            d = _JOB_LASTMOD.get(slug)
            if d and len(str(d)) >= 10:
                return str(d)[:10]
    except Exception:
        pass
    return TODAY

def has_index(p):
    return os.path.isfile(os.path.join(p, "index.html"))

def urls_from_dir(rel_root, changefreq="weekly", priority="0.7", recursive=False):
    """Collect clean URLs for every subdir containing index.html under rel_root."""
    out = []
    base_dir = os.path.join(ROOT, rel_root)
    if not os.path.isdir(base_dir):
        return out
    if recursive:
        for dp, dns, fns in os.walk(base_dir):
            if "index.html" in fns:
                rel = os.path.relpath(dp, ROOT).replace(os.sep, "/")
                if rel == rel_root:  # skip the hub root itself here; added separately
                    continue
                out.append(f"{BASE}/{rel}/")
    else:
        for name in sorted(os.listdir(base_dir)):
            d = os.path.join(base_dir, name)
            if os.path.isdir(d) and has_index(d):
                out.append(f"{BASE}/{rel_root}/{name}/")
    return out

def write_urlset(path, urls, changefreq="weekly", priority="0.7"):
    # FIX #11: normalize trailing slash before dedup so /jobs/x and /jobs/x/
    # don't both appear; use per-job lastmod from first-seen data.
    # SEO FIX: NEVER emit a legacy ".html" path into any sitemap — only clean,
    # extension-less canonical URLs are allowed (legacy .html are redirect stubs).
    seen, uniq = set(), []
    for u in urls:
        # drop any legacy .html filename (e.g. /about.html, /result.html)
        if re.search(r'\.html/?$', u, re.I):
            continue
        nu = u.rstrip("/") + "/"
        if nu not in seen:
            seen.add(nu); uniq.append(nu)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in uniq:
        lines.append(f'  <url><loc>{u}</loc><lastmod>{_lastmod_for(u)}</lastmod>'
                     f'<changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>')
    lines.append('</urlset>')
    with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return len(uniq)

def write_index(path, children):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for c in children:
        lines.append(f'  <sitemap><loc>{BASE}/{c}</loc><lastmod>{TODAY}</lastmod></sitemap>')
    lines.append('</sitemapindex>')
    with open(os.path.join(ROOT, path), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    counts = {}

    # Jobs
    counts["sitemap-jobs.xml"] = write_urlset(
        "sitemap-jobs.xml", urls_from_dir("jobs"), "weekly", "0.8")

    # States (both /state/ and /state-jobs/ hubs)
    state_urls = urls_from_dir("state") + urls_from_dir("state-jobs")
    state_urls = [u for u in state_urls if not u.endswith("/index.html/")]
    counts["sitemap-states.xml"] = write_urlset(
        "sitemap-states.xml", state_urls, "weekly", "0.7")

    # Education (recursive: state -> topic)
    counts["sitemap-education.xml"] = write_urlset(
        "sitemap-education.xml", urls_from_dir("education", recursive=True), "weekly", "0.6")

    # Categories (recursive)
    counts["sitemap-categories.xml"] = write_urlset(
        "sitemap-categories.xml", urls_from_dir("category", recursive=True), "weekly", "0.6")

    # Sections
    counts["sitemap-sections.xml"] = write_urlset(
        "sitemap-sections.xml", urls_from_dir("section"), "daily", "0.7")

    # Districts (recursive: state -> district). urls_from_dir(recursive=True) skips
    # the hub root, so add /district/ itself explicitly (mirrors how /education/ is
    # added via core). Without this the whole /district/ tree was absent from the
    # sitemap (698 indexable pages) and a regen dropped the /district/ hub too.
    district_dir = os.path.join(ROOT, "district")
    district_urls = urls_from_dir("district", recursive=True)
    if os.path.isdir(district_dir) and has_index(district_dir):
        district_urls = [f"{BASE}/district/"] + district_urls
    counts["sitemap-districts.xml"] = write_urlset(
        "sitemap-districts.xml", district_urls, "weekly", "0.6")

    # Qualification (extra hub, fold into sections file if desired) -> own optional file
    qual_urls = urls_from_dir("qualification")

    # Core static pages -> sitemap.xml is now a REAL urlset (no longer a 2nd index)
    core = [f"{BASE}/"]
    for p in ["about","contact","terms","privacy","disclaimer","helpdesk","sitemap",
              "tools","govt-services","resume-maker","search","education",
              "state","state-jobs",
              "editorial-policy","fact-check-policy","correction-policy"]:
        d = os.path.join(ROOT, p)
        if os.path.isdir(d) and has_index(d):
            core.append(f"{BASE}/{p}/")
    core += qual_urls
    counts["sitemap.xml"] = write_urlset("sitemap.xml", core, "daily", "0.9")

    # sitemap-pages.xml — ALWAYS regenerate from clean core URLs so it can never
    # go stale and reintroduce legacy .html paths.
    write_urlset("sitemap-pages.xml", core, "monthly", "0.5")

    # THE ONLY INDEX — references child urlsets ONLY (never another index)
    children = ["sitemap.xml", "sitemap-pages.xml", "sitemap-sections.xml",
                "sitemap-jobs.xml", "sitemap-categories.xml",
                "sitemap-states.xml", "sitemap-education.xml",
                "sitemap-districts.xml"]
    write_index("sitemap-index.xml", children)

    print("Sitemap rebuild complete:")
    for k, v in counts.items():
        print(f"  {k:28s} {v:>6} urls")

if __name__ == "__main__":
    main()
