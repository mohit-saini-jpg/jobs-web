#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================================
# LOCAL PC PIPELINE — run_local.py
# ================================================================
# Ye ek hi command se PURA pipeline tumhare PC pe chala deta hai:
#   1. Saare scrapers       (FJA + Sarkari + Education + State)
#   2. SR cache             (sarkariresult.com — PC ke residential IP se)
#   3. Merge                (sab sources → Complete_Jobs_Full_Data.json)
#   4. Dedup engine         (duplicate jobs hatao)
#   5. AI content layer     (optional — skip kar sakte ho)
#   6. generate_all.py      (HTML pages + district pages + state cards)
#   7. Sitemaps
#
# Iske baad sirf `Complete_Jobs_Full_Data.json` (aur agar chaaho to poora
# generated site) GitHub/site pe daal do.
#
# GitHub Actions ki ZAROORAT NAHI — sab kuch yahan PC pe.
#
# ── SETUP (ek baar) ──
#   pip install requests beautifulsoup4 lxml curl_cffi
#   (Node.js optional — sirf version bump/sitemap ping ke liye, skip kar sakte ho)
#
# ── USAGE ──
#   python run_local.py                  # pura pipeline, AI ke saath
#   python run_local.py --skip-ai        # AI skip (fast)
#   python run_local.py --only-generate  # sirf HTML banao (scrape skip)
#   python run_local.py --no-scrape      # scrape skip, baaki sab
#
# ── FOLDER STRUCTURE (PC pe) ──
#   repo/
#     scraper/         ← saare scraper .py yahan
#     generate_all.py  ← root pe
#     Complete_Jobs_Full_Data.json
#     run_local.py     ← yeh file (root pe)
# ================================================================

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import subprocess
import argparse
import time
import shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRAPER_DIR = os.path.join(ROOT, "scraper")
CJ = "Complete_Jobs_Full_Data.json"


def run(cmd, cwd=None, env=None, label=""):
    """Run a command, stream output, return True on success."""
    print(f"\n{'='*64}")
    print(f"  ▶ {label or ' '.join(cmd)}")
    print(f"{'='*64}")
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        r = subprocess.run(cmd, cwd=cwd or ROOT, env=e)
        ok = (r.returncode == 0)
        print(f"  {'✅ OK' if ok else '⚠️ exit '+str(r.returncode)}: {label}")
        return ok
    except Exception as ex:
        print(f"  ❌ ERROR: {label} — {ex}")
        return False


def ensure_cj_locations():
    """generate_all.py expects CJ at root AND scraper/ uses it too. Keep both."""
    root_cj = os.path.join(ROOT, CJ)
    scr_cj = os.path.join(SCRAPER_DIR, CJ)
    # Prefer the scraper copy (freshest after scrape+merge)
    if os.path.exists(scr_cj):
        shutil.copy2(scr_cj, root_cj)
        print(f"  [sync] scraper/{CJ} → root/{CJ}")
    elif os.path.exists(root_cj):
        shutil.copy2(root_cj, scr_cj)
        print(f"  [sync] root/{CJ} → scraper/{CJ}")


def main():
    ap = argparse.ArgumentParser(description="Local PC pipeline for topsarkarijobs")
    ap.add_argument("--skip-ai", action="store_true", help="AI content layer skip karo")
    ap.add_argument("--no-scrape", action="store_true", help="scraping skip karo (existing JSON use karo)")
    ap.add_argument("--only-generate", action="store_true", help="sirf HTML generate karo")
    ap.add_argument("--sr-only", action="store_true", help="sirf SR cache refresh karo")
    args = ap.parse_args()

    t0 = time.time()
    print(f"\n{'#'*64}")
    print(f"#  LOCAL PIPELINE START — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*64}")

    py = sys.executable  # current python

    # ── SR-only shortcut ──
    if args.sr_only:
        run([py, "scrape_sr_only.py"], cwd=SCRAPER_DIR, label="SR cache refresh")
        print("\n✅ SR cache updated. Ab pura pipeline chalao: python run_local.py")
        return

    if not args.only_generate and not args.no_scrape:
        # ── 1. SR CACHE (PC residential IP — Cloudflare allow karega) ──
        if os.path.exists(os.path.join(SCRAPER_DIR, "scrape_sr_only.py")):
            run([py, "scrape_sr_only.py"], cwd=SCRAPER_DIR,
                label="SR cache (sarkariresult.com)")

        # ── 2. ALL SCRAPERS ──
        run([py, "scraper_all.py"], cwd=SCRAPER_DIR,
            label="All scrapers (FJA + Sarkari + Education + State)")

        # ── 3. MERGE ──
        run([py, "scraper_merge.py"], cwd=SCRAPER_DIR, label="Merge sources")

    if not args.only_generate:
        # ── 4. DEDUP ENGINE (hamesha chale, even alag scraper ke baad) ──
        ensure_cj_locations()
        dedup = os.path.join(SCRAPER_DIR, "dedup_engine.py")
        if os.path.exists(dedup):
            run([py, "dedup_engine.py", "--input", CJ], cwd=SCRAPER_DIR,
                label="Dedup engine (duplicate jobs hatao)")
        else:
            print("  ⚠️ dedup_engine.py not found — skipping dedup")

        # ── 5. AI CONTENT LAYER (optional) ──
        if args.skip_ai:
            print("\n  ⏭️  AI content layer SKIPPED (--skip-ai)")
        else:
            ai = os.path.join(SCRAPER_DIR, "ai_content_layer.py")
            if os.path.exists(ai):
                ai_env = {
                    "AI_DATA_FILE": CJ,
                    "AI_MAX_MINUTES": "600",   # PC pe lamba chal sakta hai
                    "GEMINI_MODEL": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite"),
                    "GEMINI_DAILY_LIMIT": os.environ.get("GEMINI_DAILY_LIMIT", "1000"),
                    "GEMINI_SAFE_RPM": os.environ.get("GEMINI_SAFE_RPM", "5"),
                }
                if not os.environ.get("GEMINI_API_KEY"):
                    print("\n  ⚠️ GEMINI_API_KEY set nahi hai — AI skip ho raha hai.")
                    print("     Set karo: export GEMINI_API_KEY=your_key (Mac/Linux)")
                    print("              set GEMINI_API_KEY=your_key    (Windows)")
                else:
                    run([py, "ai_content_layer.py"], cwd=SCRAPER_DIR, env=ai_env,
                        label="AI content layer (Gemini)")

    # ── 6. GENERATE SITE ──
    ensure_cj_locations()
    run([py, "generate_all.py"], cwd=ROOT,
        label="generate_all.py (HTML + district pages + state cards)")

    # ── 7. SITEMAPS (optional — needs the build script) ──
    smap = os.path.join(ROOT, ".github", "workflows", "build_sitemaps.py")
    if os.path.exists(smap):
        run([py, smap], cwd=ROOT, label="Build sitemaps")

    dt = int(time.time() - t0)
    print(f"\n{'#'*64}")
    print(f"#  PIPELINE COMPLETE — {dt//60}m {dt%60}s")
    print(f"#  Ab GitHub/site pe daalo:")
    print(f"#    - Complete_Jobs_Full_Data.json  (zaroori)")
    print(f"#    - jobs/ state/ district/ sitemap*.xml  (agar full site update)")
    print(f"{'#'*64}")


if __name__ == "__main__":
    main()
