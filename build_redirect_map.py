#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_redirect_map.py — compile the (Netlify-style) _redirects file into two ES
modules consumed by the Vercel Edge Middleware: redirect-map.js (exact pathname
redirects) and redirect-map-query.js (pathname+query-string redirects).

Vercel ignores _redirects, and vercel.json can hold at most 1024 redirects. The
site has thousands of historical /jobs/ slug-rename 301s. The edge middleware
(middleware.js) reads these generated maps and issues those 301s with no limit.

BUGFIX: _redirects also has ~1,850 rules whose SOURCE is a legacy query-string
URL (state-job-detail.html?state=X&slug=Y, view.html?section=X, category.html?
group=X, education/<state>/?slug=X, ...) -- real historical URLs Google has
crawled and linked to (confirmed via a real GSC "Page indexing" export: these
patterns make up a large share of the "Not found (404)" bucket). These were
previously dropped entirely (this script only emitted exact-pathname rules),
and the legacy .html files that still exist on disk for some of these patterns
only redirect via client-side JS (window.location.replace) -- unreliable for
search engines, since it depends on Googlebot successfully rendering the page.
Now compiled into a second map, keyed by pathname + a SORTED, semicolon-joined
list of "key=value" query params (order-independent, robust to Googlebot
requesting params in a different order than they were originally crawled in).

Only EXACT literal 301 redirects are emitted here (source + destination are plain
paths, optionally with a query string on the source only). Netlify true splat
rules ("*", or a ":param" with no matching _redirects rule) are handled by
pattern logic in the middleware instead. Run after generate_all.py so the map
tracks _redirects.
"""
import os
import re
import json
from urllib.parse import urlsplit, parse_qsl

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "_redirects")
OUT = os.path.join(ROOT, "redirect-map.js")
OUT_QUERY = os.path.join(ROOT, "redirect-map-query.js")
_SITE_ORIGINS = ("https://www.topsarkarijobs.com", "http://www.topsarkarijobs.com",
                  "https://topsarkarijobs.com", "http://topsarkarijobs.com")


def query_key(path, query):
    """pathname + sorted 'k=v' pairs joined by ';' -- order-independent."""
    pairs = sorted(f"{k}={v}" for k, v in parse_qsl(query, keep_blank_values=True))
    return path + "?" + ";".join(pairs)


def normalize_dst(dst):
    """Strip a same-origin absolute prefix down to a bare path (middleware's
    redirect() does origin + dst, so an absolute same-origin dst must become
    relative first or it doubles up into a malformed URL). Returns None for
    anything middleware can't safely consume (a true Netlify placeholder, or
    an off-site absolute URL, which _redirects never actually contains)."""
    for pfx in _SITE_ORIGINS:
        if dst.startswith(pfx):
            dst = dst[len(pfx):] or "/"
            break
    if ":" in dst or "*" in dst or "?" in dst:
        return None
    return dst


def main():
    mapping = {}
    query_mapping = {}
    if os.path.exists(SRC):
        for line in open(SRC, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            src, dst, code = parts[0], parts[1], parts[2].rstrip("!")
            if code != "301":
                continue
            if ":" in src or "*" in src:
                continue
            dst = normalize_dst(dst)
            if dst is None or not dst.startswith("/"):
                continue
            if src == dst or not src.startswith("/"):
                continue
            if "?" not in src:
                mapping[src] = dst
                continue
            split = urlsplit(src)
            key = query_key(split.path, split.query)
            query_mapping.setdefault(key, dst)

    header = "// AUTO-GENERATED from _redirects by build_redirect_map.py — do not edit.\n"
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "export default " + json.dumps(mapping, ensure_ascii=False, separators=(",", ":")) + ";\n")
    with open(OUT_QUERY, "w", encoding="utf-8", newline="\n") as f:
        f.write(header + "export default " + json.dumps(query_mapping, ensure_ascii=False, separators=(",", ":")) + ";\n")

    print(f"[redirect-map] wrote {len(mapping)} exact 301 redirects -> redirect-map.js")
    print(f"[redirect-map] wrote {len(query_mapping)} query-string 301 redirects -> redirect-map-query.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
