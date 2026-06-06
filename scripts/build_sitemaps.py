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
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://www.topsarkarijobs.com"
TODAY = date.today().isoformat()

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
    seen, uniq = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); uniq.append(u)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in uniq:
        lines.append(f'  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod>'
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

    # Qualification (extra hub, fold into sections file if desired) -> own optional file
    qual_urls = urls_from_dir("qualification")

    # Core static pages -> sitemap.xml is now a REAL urlset (no longer a 2nd index)
    core = [f"{BASE}/"]
    for p in ["about","contact","terms","privacy","helpdesk","sitemap",
              "tools","govt-services","resume-maker","search","education",
              "state","state-jobs"]:
        d = os.path.join(ROOT, p)
        if os.path.isdir(d) and has_index(d):
            core.append(f"{BASE}/{p}/")
    core += qual_urls
    counts["sitemap.xml"] = write_urlset("sitemap.xml", core, "daily", "0.9")

    # sitemap-pages.xml (keep if exists; ensure it's a urlset, otherwise regenerate as core)
    if not os.path.isfile(os.path.join(ROOT, "sitemap-pages.xml")):
        write_urlset("sitemap-pages.xml", core, "monthly", "0.5")

    # THE ONLY INDEX — references child urlsets ONLY (never another index)
    children = ["sitemap.xml", "sitemap-pages.xml", "sitemap-sections.xml",
                "sitemap-jobs.xml", "sitemap-categories.xml",
                "sitemap-states.xml", "sitemap-education.xml"]
    write_index("sitemap-index.xml", children)

    print("Sitemap rebuild complete:")
    for k, v in counts.items():
        print(f"  {k:28s} {v:>6} urls")

if __name__ == "__main__":
    main()
