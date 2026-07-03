"""
run_social_autopost.py
-----------------------
Standalone entry point for the social auto-posting workflow.

Unlike generate_all.py (which runs on every code/JSON push and rebuilds the
whole site), this script does ONE thing: load the already-committed
Complete_Jobs_Full_Data.json and post any new jobs to X and Telegram.

Meant to be run by its own GitHub Actions workflow (social-autopost.yml) on
its own schedule — completely decoupled from the site-build pipeline.

Usage:
    python3 run_social_autopost.py
"""

import os
import json

from social_autopost import autopost_new_jobs

DATA_FILE_CANDIDATES = [
    "Complete_Jobs_Full_Data.json",
    "data/Complete_Jobs_Full_Data.json",
]


def _load_job_data():
    for path in DATA_FILE_CANDIDATES:
        if os.path.exists(path):
            print(f"[AutoPost] Loading {path}")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(
        f"Could not find Complete_Jobs_Full_Data.json in any of: {DATA_FILE_CANDIDATES}"
    )


def _collect_jobs(data):
    """
    Pulls together the same job pool generate_all.py builds pages from:
      - sarkari_data.jobs           (SarkariResult-sourced jobs)
      - freejobalert_unified.deduped_jobs   (FreeJobAlert-sourced jobs)
    We don't need generate_all.py's full filtering (garbage-title removal,
    admission re-categorization, etc.) here — get_own_site_url() in
    social_autopost.py already skips any job with no usable slug, and a job
    without a real title just won't make sense as a post, which is a safe
    enough filter on its own.
    """
    jobs = []

    sark_jobs = ((data.get("sarkari_data") or {}).get("jobs") or [])
    jobs.extend(sark_jobs)

    fja_jobs = ((data.get("freejobalert_unified") or {}).get("deduped_jobs") or [])
    jobs.extend(fja_jobs)

    # Basic sanity filter: skip anything with no title at all.
    jobs = [j for j in jobs if str(j.get("title") or "").strip()]

    print(f"[AutoPost] Collected {len(sark_jobs)} SarkariResult jobs + "
          f"{len(fja_jobs)} FreeJobAlert jobs = {len(jobs)} total.")
    return jobs


if __name__ == "__main__":
    data = _load_job_data()
    jobs = _collect_jobs(data)
    autopost_new_jobs(jobs)
