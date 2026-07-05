# -*- coding: utf-8 -*-
"""Check (e): sitemap <-> disk consistency (GLOBAL / cross-file).

  * sitemap loc with NO page on disk  -> CRITICAL: pinging Google with a URL that
    404s hurts crawl budget. This is exactly the class that must gate the ping.
  * page on disk NOT in any sitemap    -> NON_CRITICAL: it just isn't advertised
    for discovery; no 404.

AUTO-FIXABLE via regeneration. We never hand-edit sitemap XML. Instead the fix
re-runs scripts/build_sitemaps.py (through checks/adapter_build_sitemaps.py),
which rebuilds every sitemap FROM DISK — dropping the stale/renamed URLs that
404 and adding disk pages that were missing. If regeneration still leaves a
critical mismatch, it stays UNFIXABLE and blocks the ping."""
import os
import re
import glob
from ._base import Issue, CRITICAL, NON_CRITICAL

CHECK_ID = "sitemap_sync"
SCOPE = "global"
BASE_URL = "https://www.topsarkarijobs.com"
# only reconcile these trees (skip helper/asset URLs)
_TREES = ("jobs/", "state/", "education/", "category/", "section/", "qualification/")
_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
_MAX_SAMPLES = 200  # cap issues emitted per side so a broken build can't flood


def _url_to_diskpath(root, url):
    path = url[len(BASE_URL):] if url.startswith(BASE_URL) else url
    path = path.split("#", 1)[0].split("?", 1)[0].strip("/")
    if not path:
        return os.path.join(root, "index.html")
    return os.path.join(root, path.replace("/", os.sep), "index.html")


def _diskpath_to_urlpath(root, filepath):
    rel = os.path.relpath(filepath, root).replace(os.sep, "/")
    rel = rel[:-len("index.html")] if rel.endswith("index.html") else rel
    return "/" + rel.strip("/") + ("/" if rel.strip("/") else "")


def _in_trees(rel):
    return any(rel.startswith(t) for t in _TREES)


def _reachable_page_urls(root):
    """Collect page URLs ONLY from sitemaps Google actually reads: start from the
    submitted/pinged roots (sitemap-index.xml, sitemap.xml) and follow child
    <loc>...xml</loc> references. Stale, UNREFERENCED sitemap*.xml files on disk
    (e.g. an old sitemap-results.xml no longer in the index) are ignored — their
    URLs can never 404 a crawl because Google never sees them."""
    page_urls = set()
    visited = set()
    queue = ["sitemap-index.xml", "sitemap.xml"]
    while queue:
        fname = queue.pop()
        if fname in visited:
            continue
        visited.add(fname)
        fpath = os.path.join(root, fname)
        if not os.path.exists(fpath):
            continue
        try:
            txt = open(fpath, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for loc in _LOC_RE.findall(txt):
            loc = loc.strip()
            if loc.lower().endswith(".xml"):          # child sitemap reference
                queue.append(loc.rsplit("/", 1)[-1])  # enqueue by basename
            else:
                page_urls.add(loc)
    return page_urls


def detect_global(ctx):
    root = ctx["root"]
    issues = []

    # 1) collect page URLs reachable from the sitemap index / pinged sitemap
    locs = _reachable_page_urls(root)
    if not locs:
        return issues  # no reachable sitemaps to reconcile (nothing to say)

    # 2) sitemap loc -> disk missing (CRITICAL)
    n = 0
    for u in locs:
        dp = _url_to_diskpath(root, u)
        rel = os.path.relpath(dp, root).replace(os.sep, "/")
        if not _in_trees(rel):
            continue
        if not os.path.exists(dp):
            issues.append(Issue(CHECK_ID, CRITICAL,
                f"sitemap URL has no page on disk (would 404): {u}", dp,
                fixable=True, meta={"side": "sitemap_orphan", "url": u}))
            n += 1
            if n >= _MAX_SAMPLES:
                break

    # 3) disk page -> not in any sitemap (NON_CRITICAL)
    loc_paths = set()
    for u in locs:
        p = (u[len(BASE_URL):] if u.startswith(BASE_URL) else u)
        loc_paths.add("/" + p.split("#")[0].split("?")[0].strip("/") + "/")
    n = 0
    for fp in ctx.get("files", []):
        rel = os.path.relpath(fp, root).replace(os.sep, "/")
        if not _in_trees(rel):
            continue
        up = _diskpath_to_urlpath(root, fp)
        if up not in loc_paths:
            issues.append(Issue(CHECK_ID, NON_CRITICAL,
                f"page on disk not in any sitemap: {up}", fp,
                fixable=True, meta={"side": "disk_orphan", "urlpath": up}))
            n += 1
            if n >= _MAX_SAMPLES:
                break
    return issues


def fix_global(ctx, issues):
    """Regenerate all sitemaps from disk (once) if there is any drift. This is
    the auto-heal: build_sitemaps.py rebuilds the XML from the dirs that actually
    contain index.html, so stale 404 URLs drop out and missing pages get added."""
    if not issues:
        return
    from . import adapter_build_sitemaps
    ok, note = adapter_build_sitemaps.regenerate(ctx["root"])
    ctx.setdefault("_notes", []).append(note + (" [ok]" if ok else " [FAILED]"))
