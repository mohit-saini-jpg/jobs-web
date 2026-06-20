# -*- coding: utf-8 -*-
# ================================================================
# MASTER RUNNER — scraper_all.py
# ================================================================
# Sabhi 4 scrapers ek saath run karta hai, checkpoint/resume ke saath.
# Individual scrapers seedhe bhi chalaye ja sakte hain:
#
#   python scraper_fja.py       — FreeJobAlert categories only
#   python scraper_sarkari.py   — Sarkari (Shine+SR+SN) only
#   python scraper_education.py — Education jobs only
#   python scraper_state.py     — State Govt jobs only
#   python scraper_all.py       — Sabhi 4 (ye file)
#
# Har scraper sirf apna section update karta hai.
# Baaki sources UNTOUCHED rehte hain.
# ================================================================

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import json
from datetime import datetime
from scraper_merge import wait_for_internet, FINAL_OUTPUT

# ── Checkpoint file ────────────────────────────────────────────
_CHECKPOINT_FILE = "scraper_checkpoint.json"

def _checkpoint_load():
    if os.path.exists(_CHECKPOINT_FILE):
        try:
            with open(_CHECKPOINT_FILE, encoding="utf-8") as f:
                return set(json.load(f).get("done", []))
        except Exception:
            pass
    return set()

def _checkpoint_mark_done(name):
    done = _checkpoint_load()
    done.add(name)
    with open(_CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({"done": sorted(done), "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)

def _checkpoint_clear():
    if os.path.exists(_CHECKPOINT_FILE):
        os.remove(_CHECKPOINT_FILE)


# ── Net error signals ─────────────────────────────────────────
_NET_ERR_SIGNALS = (
    "ConnectionError", "NameResolution", "Max retries",
    "RemoteDisconnected", "ChunkedEncodingError",
    "NewConnectionError", "Network", "timed out",
    "ConnectionReset", "BrokenPipe",
)


def _run_scraper(name, script_path, done_set):
    """Ek scraper script subprocess mein chalao."""
    import subprocess

    if name in done_set:
        print(f"\n  [SKIP] {name} — already done (checkpoint)")
        return True

    wait_for_internet(name)

    print(f"\n{'='*60}")
    print(f"  STARTING: {name}")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, script_path],
        cwd=os.path.dirname(os.path.abspath(script_path)),
    )

    if result.returncode == 0:
        _checkpoint_mark_done(name)
        print(f"  ✅ {name} COMPLETE")
        return True
    else:
        print(f"  ❌ {name} FAILED (exit code {result.returncode})")
        return False


def run_all():
    base = os.path.dirname(os.path.abspath(__file__))

    scrapers = [
        # ── UNIFIED FJA (replaces separate qual + state + district scrapers) ──
        # One pass collects listing URLs from all three FJA category sources,
        # dedups by detail-page URL, and scrapes each unique job exactly once.
        # Output → "freejobalert_unified" key (deduped_jobs + index).
        ("Unified FJA (qual+state+district)", os.path.join(base, "scraper_unified_fja.py")),
        ("Sarkari (Shine+SR+SN)",   os.path.join(base, "scraper_sarkari.py")),
        ("Education",               os.path.join(base, "scraper_education.py")),
        # ── LEGACY (kept for backward-compat; data still populated for the live
        # site until generate_all.py is migrated to read freejobalert_unified).
        # Once migrated, these three can be removed safely.
        ("FreeJobAlert Categories", os.path.join(base, "scraper_fja.py")),
        ("State Govt Jobs",         os.path.join(base, "scraper_state.py")),
    ]

    done_set = _checkpoint_load()
    if done_set:
        print(f"\n  [CHECKPOINT] Pehle se complete: {sorted(done_set)}")
        print(f"  Inhe skip karke baaki se resume hoga.\n")

    results = {}
    for name, script in scrapers:
        ok = _run_scraper(name, script, done_set)
        results[name] = ok
        done_set = _checkpoint_load()   # refresh after each run

    # ── Final summary ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  ALL SCRAPERS COMPLETE")
    print(f"{'='*60}")
    for name, ok in results.items():
        mark = "✅" if ok else "❌"
        print(f"  {mark}  {name}")

    if os.path.exists(FINAL_OUTPUT):
        size_mb = os.path.getsize(FINAL_OUTPUT) / (1024 * 1024)
        with open(FINAL_OUTPUT, encoding="utf-8") as f:
            data = json.load(f)
        print(f"\n  OUTPUT FILE    : {FINAL_OUTPUT}  ({size_mb:.1f} MB)")
        print(f"  TOTAL RECORDS  : {data.get('total_records', '?')}")
        for src, cnt in data.get("sources", {}).items():
            print(f"    {src:35s}: {cnt}")
        ss = data.get("sync_stats", {})
        print(f"\n  SYNC STATS (last run):")
        print(f"    ✅ Added    : {ss.get('added', 0)}")
        print(f"    ❌ Removed  : {ss.get('removed', 0)}")
        print(f"    ⏸  Unchanged: {ss.get('unchanged', 0)}")

    _checkpoint_clear()
    print(f"\n  [CHECKPOINT] Cleared — next run fresh start karega.")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_all()
