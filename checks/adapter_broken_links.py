# -*- coding: utf-8 -*-
"""Adapter (GLOBAL): wraps .github/workflows/check_broken_links.py.

That script has NO dry-run mode and writes _redirects directly, and it runs its
whole body at import time — so we NEVER import it and never run it in --dry-run.

  * --dry-run  -> detect_global() reports "delegated, not evaluated in dry-run"
  * fix mode   -> fix_global() runs it once as a subprocess and records how many
                  301 redirect rules it added (parsed from its stdout)."""
import os
import sys
import subprocess
from ._base import Issue, NON_CRITICAL

CHECK_ID = "broken_links"
SCOPE = "global"
_SCRIPT = os.path.join(".github", "workflows", "check_broken_links.py")


def detect_global(ctx):
    if ctx.get("dry_run"):
        return [Issue(CHECK_ID, NON_CRITICAL,
            "broken-link / 301-redirect scan delegated to check_broken_links.py "
            "(no dry mode; not run in --dry-run)", "", fixable=False,
            meta={"delegated": True})]
    return []   # fix mode: work happens in fix_global (can't detect without running)


def fix_global(ctx, issues):
    root = ctx["root"]
    notes = ctx.setdefault("_notes", [])
    try:
        res = subprocess.run([sys.executable, _SCRIPT], cwd=root,
                             capture_output=True, text=True, timeout=900)
        out = ((res.stdout or "") + (res.stderr or "")).strip()
        last = out.splitlines()[-1] if out else "(no output)"
        notes.append(f"broken_links: {last}")
    except Exception as ex:
        notes.append(f"broken_links: FAILED to run ({ex})")
