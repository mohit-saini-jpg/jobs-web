#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seo_guardian.py — Auto-Healing & Self-Fixing SEO Gatekeeper for topsarkarijobs.com

Runs as the LAST content step of the 7 AM pipeline (auto-update-jobs.yml, Step 8b,
just before the commit) and, in a weekly manual full-scan, over the whole tree.

WHAT IT DOES
  1. Auto-discovers every plugin in checks/*.py (no manual registry).
  2. Per file: detect -> fix -> re-detect, up to 3 passes; anything still broken is
     logged UNFIXABLE (never crashes the pipeline). After every fix the HTML is
     re-checked for structural well-formedness; if a fix breaks it, the fix is
     reverted and the issue marked UNFIXABLE.
  3. Runs cross-file "global" checks (sitemap<->disk, slug dupes via validate.py,
     broken-link redirects via check_broken_links.py) through the same interface.
  4. Writes seo_guardian_report.json and prints an Actions-readable summary.
  5. Emits SEO_CLEAN=true/false to $GITHUB_ENV. SEO_CLEAN is false ONLY when a
     CRITICAL issue remains UNFIXABLE (malformed JSON-LD, missing required schema,
     a sitemap URL that would 404). Non-critical issues never block the ping.

It NEVER touches job title/description/vacancy/date DATA — structural / SEO
metadata only. Existing fixer scripts are wrapped (imported / subprocessed), never
reimplemented or modified.

USAGE
  python seo_guardian.py --dry-run --full-scan   # report only, whole tree (SAFE)
  python seo_guardian.py --dry-run --changed-only # report only, git-changed pages
  python seo_guardian.py --changed-only          # heal git-changed pages (7 AM)
  python seo_guardian.py --full-scan             # heal whole tree (weekly)
  python seo_guardian.py --changed-only <substr> # limit to matching paths
Exit code is always 0 (deploy is never blocked); the ping gate is SEO_CLEAN.
"""
import os
import sys
import time
import json
import importlib
import subprocess
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from checks._base import Issue, CRITICAL, structural_ok  # noqa: E402

SCAN_DIRS = ("jobs", "state", "education", "category", "section", "qualification")
MAX_PASSES = 3
REPORT_PATH = os.path.join(ROOT, "seo_guardian_report.json")


# ── plugin discovery ─────────────────────────────────────────────────────────
def discover_checks():
    """Import every checks/<name>.py (skip _base/__init__). Returns
    (perfile_modules, global_modules)."""
    perfile, glob_ = [], []
    checks_dir = os.path.join(ROOT, "checks")
    for fn in sorted(os.listdir(checks_dir)):
        if not fn.endswith(".py") or fn.startswith("_") or fn == "__init__.py":
            continue
        name = "checks." + fn[:-3]
        try:
            mod = importlib.import_module(name)
        except Exception as ex:
            print(f"  [guardian] could not load {name}: {ex}")
            continue
        if getattr(mod, "SCOPE", "") == "global" and hasattr(mod, "detect_global"):
            glob_.append(mod)
        elif hasattr(mod, "detect"):
            perfile.append(mod)
    return perfile, glob_


# ── file discovery ───────────────────────────────────────────────────────────
def _rel_in_scan(rel):
    rel = rel.replace("\\", "/")
    return any(rel == d + "/index.html" or rel.startswith(d + "/") for d in SCAN_DIRS)


def full_scan_files():
    out = []
    for base in SCAN_DIRS:
        for root, _dirs, files in os.walk(os.path.join(ROOT, base)):
            if "index.html" in files:
                out.append(os.path.join(root, "index.html"))
    return out


def changed_files():
    seen = set()
    cmds = (["git", "diff", "--name-only"],
            ["git", "diff", "--cached", "--name-only"],
            ["git", "ls-files", "--others", "--exclude-standard"])
    for cmd in cmds:
        try:
            res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
        except Exception:
            continue
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.endswith("index.html") and _rel_in_scan(line):
                seen.add(os.path.join(ROOT, line.replace("/", os.sep)))
    return sorted(p for p in seen if os.path.exists(p))


# ── per-file engine ──────────────────────────────────────────────────────────
def _safe_write(path, html):
    try:
        open(path, "w", encoding="utf-8").write(html)
    except Exception:
        pass


def detect_all(perfile_mods, path, html):
    issues = []
    for mod in perfile_mods:
        try:
            issues.extend(mod.detect(path, html) or [])
        except Exception as ex:
            print(f"  [guardian] {getattr(mod,'CHECK_ID','?')}.detect failed on "
                  f"{os.path.relpath(path, ROOT)}: {ex}")
    return issues


def heal_file(perfile_mods, by_id, path, html):
    """Fix loop (max 3 passes). Returns (final_html, changed_bool)."""
    changed = False
    for _pass in range(MAX_PASSES):
        actionable = [i for i in detect_all(perfile_mods, path, html) if i.fixable]
        if not actionable:
            break
        progressed = False
        for iss in actionable:
            mod = by_id.get(iss.check)
            if mod is None:
                continue
            # keep disk in sync so adapter fixes (which read the file) see the
            # latest in-memory state, regardless of check ordering
            _safe_write(path, html)
            try:
                new = mod.fix(path, html, iss)
            except Exception as ex:
                print(f"  [guardian] {iss.check}.fix failed on "
                      f"{os.path.relpath(path, ROOT)}: {ex}")
                new = html
            if new and new != html:
                if structural_ok(html, new):
                    html = new
                    changed = True
                    progressed = True
                # else: fix broke structure -> reject, leave as UNFIXABLE
        _safe_write(path, html)   # ensure disk == in-memory after the pass
        if not progressed:
            break
    return html, changed


# ── driver ───────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    full = "--full-scan" in args
    changed = "--changed-only" in args
    # --only=a,b  -> restrict to these CHECK_IDs (targeted testing / ops)
    only = None
    for a in args:
        if a.startswith("--only="):
            only = {x.strip() for x in a.split("=", 1)[1].split(",") if x.strip()}
    known_flags = {"--dry-run", "--full-scan", "--changed-only"}
    path_filter = next((a for a in args
                        if a not in known_flags and not a.startswith("--only=")), None)
    mode = "full-scan" if full else "changed-only"   # full-scan wins; default changed-only

    perfile_mods, global_mods = discover_checks()
    if only:
        perfile_mods = [m for m in perfile_mods if getattr(m, "CHECK_ID", "") in only]
        global_mods = [m for m in global_mods if getattr(m, "CHECK_ID", "") in only]
    by_id = {getattr(m, "CHECK_ID", m.__name__): m for m in perfile_mods}

    files = full_scan_files() if full else changed_files()
    if path_filter:
        files = [f for f in files if path_filter in f.replace("\\", "/")]

    print("=" * 70)
    print(f"SEO GUARDIAN — mode={mode} dry_run={dry_run} files={len(files)}")
    print(f"  per-file checks: {', '.join(sorted(by_id)) or '-'}")
    print(f"  global checks  : {', '.join(getattr(m,'CHECK_ID','?') for m in global_mods) or '-'}")
    print("=" * 70)

    found = Counter()
    auto_fixed = 0
    unfixable = []   # list[Issue]

    # per-file
    for path in files:
        try:
            html = open(path, encoding="utf-8", errors="ignore").read()
        except Exception as ex:
            print(f"  [guardian] read failed {os.path.relpath(path, ROOT)}: {ex}")
            continue
        initial = detect_all(perfile_mods, path, html)
        for i in initial:
            found[i.check] += 1
        if not initial:
            continue
        if dry_run:
            unfixable.extend(i for i in initial if not i.fixable)  # projected
            continue
        new_html, _ch = heal_file(perfile_mods, by_id, path, html)
        try:
            final_html = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            final_html = new_html
        remaining = detect_all(perfile_mods, path, final_html)
        auto_fixed += max(0, len(initial) - len(remaining))
        unfixable.extend(remaining)

    # global
    ctx = {"root": ROOT, "files": files, "dry_run": dry_run, "_notes": []}
    for mod in global_mods:
        cid = getattr(mod, "CHECK_ID", "?")
        try:
            gissues = mod.detect_global(ctx) or []
        except Exception as ex:
            print(f"  [guardian] {cid}.detect_global failed: {ex}")
            continue
        for i in gissues:
            found[i.check] += 1
        has_fix = hasattr(mod, "fix_global")
        if dry_run or not has_fix:
            unfixable.extend(i for i in gissues if not i.fixable)
        else:
            try:
                mod.fix_global(ctx, gissues)
                remaining = mod.detect_global(ctx) or []
            except Exception as ex:
                print(f"  [guardian] {cid}.fix_global failed: {ex}")
                remaining = gissues
            auto_fixed += max(0, len(gissues) - len(remaining))
            unfixable.extend(remaining)

    # ── gate ──
    crit_unfixable = [i for i in unfixable if i.severity == CRITICAL]
    seo_clean = len(crit_unfixable) == 0

    # ── report ──
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "dry_run": dry_run,
        "files_scanned": len(files),
        "issues_found_by_check": dict(found),
        "issues_auto_fixed": auto_fixed,
        "unfixable": [{"file": os.path.relpath(i.filepath, ROOT) if i.filepath else "",
                       "check": i.check, "severity": i.severity, "reason": i.message}
                      for i in unfixable],
        "critical_unfixable": len(crit_unfixable),
        "seo_clean": seo_clean,
        "notes": ctx.get("_notes", []),
        "duration_sec": round(time.time() - t0, 1),
    }
    try:
        json.dump(report, open(REPORT_PATH, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    except Exception as ex:
        print(f"  [guardian] could not write report: {ex}")

    # ── console summary ──
    print("\n" + "-" * 70)
    print(f"Issues found ({sum(found.values())}):")
    for chk, n in found.most_common():
        print(f"    {n:>5}  {chk}")
    if not dry_run:
        print(f"Auto-fixed: {auto_fixed}")
    for note in ctx.get("_notes", []):
        print(f"    note: {note}")
    print(f"\nUNFIXABLE: {len(unfixable)}  (critical: {len(crit_unfixable)})")
    shown = crit_unfixable[:15] if crit_unfixable else unfixable[:15]
    for i in shown:
        loc = os.path.relpath(i.filepath, ROOT) if i.filepath else "-"
        print(f"    [{i.severity}] {i.check}: {i.message}  ({loc})")
    if len(shown) < len(unfixable):
        print(f"    ... (+{len(unfixable) - len(shown)} more in seo_guardian_report.json)")
    print("-" * 70)
    print(f"SEO_CLEAN={'true' if seo_clean else 'false'}   "
          f"({'ping allowed' if seo_clean else 'PING WILL BE SKIPPED — critical unfixable'})")
    print("-" * 70)

    # ── emit gate to GitHub Actions ──
    ghenv = os.environ.get("GITHUB_ENV")
    if ghenv:
        try:
            with open(ghenv, "a", encoding="utf-8") as f:
                f.write(f"SEO_CLEAN={'true' if seo_clean else 'false'}\n")
        except Exception:
            pass

    return 0   # never block the pipeline; the gate is SEO_CLEAN, not exit code


if __name__ == "__main__":
    sys.exit(main())
