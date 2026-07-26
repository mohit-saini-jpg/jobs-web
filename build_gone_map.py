#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_gone_map.py — compile `_gone_urls.txt` into an ES module `gone-map.js`
consumed by the Vercel Edge Middleware, which answers these paths with a
hard HTTP 410 Gone instead of a plain 404.

WHY 410: Search Console treats 410 as a much stronger "permanently removed"
signal than 404, and deindexes/stops re-crawling faster -- saving crawl
budget for real pages. These are old job postings that expired with no
replacement (a redirect target would be misleading), so 410 is the honest
answer instead of leaving them as an indefinitely-recrawled 404.

Self-healing by design: every candidate path is re-checked against the live
redirect map and the actual /jobs/ (etc.) tree on disk every time this runs.
A path is DROPPED from the compiled output (even though it's still listed in
_gone_urls.txt) if it now has a real 301 redirect or a live generated page --
so it's always safe to just append new candidates to _gone_urls.txt without
manually re-verifying each one, and a page that comes back to life later
automatically stops being marked Gone on the next generate_all.py run.

Run after build_redirect_map.py (needs the freshly-regenerated redirect-map.js
to cross-check against) and after generate_all.py (needs the current on-disk
page tree).
"""
import os
import re
import json
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "_gone_urls.txt")
REDIRECT_MAP = os.path.join(ROOT, "redirect-map.js")
OUT = os.path.join(ROOT, "gone-map.js")

# Same pattern middleware.js already redirects via JOBS_SLUG_HTML_LEAK --
# never mark these Gone, they already resolve with a real 301.
JOBS_SLUG_HTML_LEAK = re.compile(
    r"^/jobs/[^/]+/(index|category|helpdesk|tools|view|govt-services|resume-maker)\.html$"
)


def load_redirects():
    if not os.path.exists(REDIRECT_MAP):
        return {}
    text = open(REDIRECT_MAP, encoding="utf-8").read()
    body = text.split("export default", 1)[1].strip().rstrip(";").strip()
    return json.loads(body)


def file_exists_for_path(path):
    """path like /jobs/foo/ -- does a real generated page exist on disk?"""
    p = path.strip("/")
    if not p:
        return os.path.exists(os.path.join(ROOT, "index.html"))
    if os.path.exists(os.path.join(ROOT, p, "index.html")):
        return True
    literal = os.path.join(ROOT, p)
    return os.path.isfile(literal)


def main():
    redirects = load_redirects()
    candidates = []
    if os.path.exists(SRC):
        for line in open(SRC, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # tolerate a full URL (strip scheme+domain) or a bare path
            if line.startswith("http://") or line.startswith("https://"):
                line = urlparse(line).path
            if not line.startswith("/"):
                continue
            candidates.append(line)

    gone = []
    seen = set()
    dropped_redirect = dropped_live = dropped_leak = 0
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)

        if JOBS_SLUG_HTML_LEAK.match(path):
            dropped_leak += 1
            continue

        variants = [path, path[:-1] if path.endswith("/") else path + "/"]
        if any(v in redirects for v in variants):
            dropped_redirect += 1
            continue

        if any(file_exists_for_path(v) for v in variants):
            dropped_live += 1
            continue

        gone.append(path)

    header = "// AUTO-GENERATED from _gone_urls.txt by build_gone_map.py — do not edit.\n"
    body = "export default new Set(" + json.dumps(gone, ensure_ascii=False, separators=(",", ":")) + ");\n"
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(header + body)

    print(
        f"[gone-map] {len(candidates)} candidates -> {len(gone)} written "
        f"(dropped: {dropped_redirect} now-redirected, {dropped_live} now-live, "
        f"{dropped_leak} html-leak-pattern) -> gone-map.js"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
