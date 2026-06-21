#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================================
# LOCAL PC PIPELINE — run_local.py
# ================================================================
# CURRENT WORKFLOW (as of Jun 2026):
#   Scraping no longer happens inside this repo. GitHub Actions was
#   removed, and the old scraper/ folder (12 scraper scripts + their
#   stale intermediate JSON outputs) was deleted as part of cleanup.
#
#   You now generate Complete_Jobs_Full_Data.json yourself (wherever
#   your scraper lives) and manually drop the fresh file at the repo
#   ROOT before running this script. There is no fallback copy —
#   generate_all.py will hard-fail if root/Complete_Jobs_Full_Data.json
#   is missing, by design, to prevent silently building from stale data.
#
#   This script now only:
#     1. Runs generate_all.py   (HTML pages + district pages + state cards)
#     2. (generate_all.py itself syncs root/ → data/ at the end of its run,
#         so the deployed frontend's runtime fetch never goes stale)
#     3. Builds sitemaps (if the sitemap script exists)
#
# ── USAGE ──
#   python run_local.py
#
# ── FOLDER STRUCTURE (PC pe) ──
#   repo/
#     generate_all.py                  ← root pe
#     Complete_Jobs_Full_Data.json     ← tum manually yahan drop karte ho
#     run_local.py                     ← yeh file (root pe)
# ================================================================

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
CJ_PATH = Path(ROOT) / "Complete_Jobs_Full_Data.json"


def run(cmd, cwd=None, label=""):
    """Run a command, stream output, return True on success."""
    print(f"\n{'='*64}")
    print(f"  ▶ {label or ' '.join(cmd)}")
    print(f"{'='*64}")
    try:
        r = subprocess.run(cmd, cwd=cwd or ROOT)
        ok = (r.returncode == 0)
        print(f"  {'✅ OK' if ok else '⚠️ exit '+str(r.returncode)}: {label}")
        return ok
    except Exception as ex:
        print(f"  ❌ ERROR: {label} — {ex}")
        return False


def main():
    t0 = time.time()
    print(f"\n{'#'*64}")
    print(f"#  LOCAL PIPELINE START — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*64}")

    if not CJ_PATH.exists():
        print(f"\n❌ {CJ_PATH} not found.")
        print("   Drop your latest Complete_Jobs_Full_Data.json at the repo root, then re-run.")
        sys.exit(1)

    py = sys.executable

    # ── GENERATE SITE ──
    ok = run([py, "generate_all.py"], cwd=ROOT,
             label="generate_all.py (HTML + district pages + state cards)")
    if not ok:
        print("\n❌ generate_all.py failed — stopping before sitemaps.")
        sys.exit(1)

    # ── SITEMAPS (optional — only if the build script exists) ──
    smap = os.path.join(ROOT, ".github", "workflows", "build_sitemaps.py")
    if os.path.exists(smap):
        run([py, smap], cwd=ROOT, label="Build sitemaps")

    dt = int(time.time() - t0)
    print(f"\n{'#'*64}")
    print(f"#  PIPELINE COMPLETE — {dt//60}m {dt%60}s")
    print(f"#  Ab deploy karo:")
    print(f"#    - Complete_Jobs_Full_Data.json + data/Complete_Jobs_Full_Data.json  (auto-synced)")
    print(f"#    - jobs/ state/ district/ section/ qualification/ sitemap*.xml  (poora generated site)")
    print(f"{'#'*64}")


if __name__ == "__main__":
    main()
