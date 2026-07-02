#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_redirect_map.py — compile the (Netlify-style) _redirects file into an ES
module `redirect-map.js` consumed by the Vercel Edge Middleware.

Vercel ignores _redirects, and vercel.json can hold at most 1024 redirects. The
site has thousands of historical /jobs/ slug-rename 301s. The edge middleware
(middleware.js) reads this generated map and issues those 301s with no limit.

Only EXACT literal 301 redirects are emitted here (source + destination are plain
paths). Netlify param/splat rules (":slug", "*") are handled by pattern logic in
the middleware instead. Run after generate_all.py so the map tracks _redirects.
"""
import os
import re
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "_redirects")
OUT = os.path.join(ROOT, "redirect-map.js")


def main():
    mapping = {}
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
            # exact literal paths only (skip Netlify params / splats / query)
            if any(c in src for c in (":", "*", "?")) or any(c in dst for c in (":", "*", "?")):
                continue
            if src == dst or not src.startswith("/"):
                continue
            mapping[src] = dst

    header = "// AUTO-GENERATED from _redirects by build_redirect_map.py — do not edit.\n"
    body = "export default " + json.dumps(mapping, ensure_ascii=False, separators=(",", ":")) + ";\n"
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(header + body)
    print(f"[redirect-map] wrote {len(mapping)} exact 301 redirects -> redirect-map.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
