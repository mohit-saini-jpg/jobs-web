# -*- coding: utf-8 -*-
"""Adapter (GLOBAL): wraps scripts/validate.py (does NOT reimplement it).

validate.py checks jobs-index slug dupes, listing->disk links, blocked-domain
leaks and duplicate AI sentinels, printing '[ERROR]' / '[WARN]' lines. It runs
its whole body at import and os.chdir()s, so we call it as a read-only subprocess
(without --fail, so it exits 0) and turn its [ERROR]/[WARN] lines into Issues.

REPORT ONLY (fixable=False) and NON_CRITICAL: these are structural problems we do
not auto-fix here, and they must NOT permanently block the ping — they are
surfaced in the report/summary for a human, while pings keep flowing."""
import os
import sys
import subprocess
from ._base import Issue, NON_CRITICAL

CHECK_ID = "slug_validate"
SCOPE = "global"
_SCRIPT = os.path.join("scripts", "validate.py")


def detect_global(ctx):
    root = ctx["root"]
    try:
        res = subprocess.run([sys.executable, _SCRIPT], cwd=root,
                             capture_output=True, text=True, timeout=900)
    except Exception as ex:
        return [Issue(CHECK_ID, NON_CRITICAL,
                      f"validate.py could not run ({ex})", "", fixable=False)]
    out = (res.stdout or "") + "\n" + (res.stderr or "")
    issues = []
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("[ERROR]"):
            issues.append(Issue(CHECK_ID, NON_CRITICAL, "validate " + s, "",
                                fixable=False, meta={"level": "error"}))
        elif s.startswith("[WARN]"):
            issues.append(Issue(CHECK_ID, NON_CRITICAL, "validate " + s, "",
                                fixable=False, meta={"level": "warn"}))
    return issues
