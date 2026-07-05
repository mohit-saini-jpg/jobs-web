# -*- coding: utf-8 -*-
"""Helper (NOT a check): wraps scripts/build_sitemaps.py.

scripts/build_sitemaps.py rebuilds every sitemap-*.xml FROM DISK (it walks the
directories that actually contain index.html), so running it drops stale/renamed
URLs that no longer exist on disk and adds pages missing from the sitemap. It is
the correct auto-heal for the sitemap<->disk drift that sitemap_sync detects.

This module deliberately exposes NO detect()/detect_global() so seo_guardian's
plugin discovery ignores it — it is a fix helper imported by sitemap_sync, not a
standalone check (avoids double-reporting the same issue)."""
import os
import sys
import subprocess

_SCRIPT = os.path.join("scripts", "build_sitemaps.py")


def regenerate(root):
    """Run build_sitemaps.py from disk. Returns (ok: bool, note: str)."""
    if not os.path.exists(os.path.join(root, _SCRIPT)):
        return False, "build_sitemaps: scripts/build_sitemaps.py not found"
    try:
        res = subprocess.run([sys.executable, _SCRIPT], cwd=root,
                             capture_output=True, text=True, timeout=900)
        out = ((res.stdout or "") + (res.stderr or "")).strip()
        last = out.splitlines()[-1] if out else "(no output)"
        return res.returncode == 0, f"build_sitemaps: {last}"
    except Exception as ex:
        return False, f"build_sitemaps: FAILED ({ex})"
