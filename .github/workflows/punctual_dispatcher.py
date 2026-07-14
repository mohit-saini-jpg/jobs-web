#!/usr/bin/env python3
"""Runs every 5 minutes via punctual-dispatch.yml. For each daily-scheduled
workflow below, if its target time (UTC) has passed today and no run has
happened for it since that target time, fires an immediate workflow_dispatch
via `gh workflow run`.

Exists because GitHub Actions' own `schedule:` trigger has been observed
firing 2-4 hours late on this repo during high-load minutes (:00/:30 UTC).
A 5-minute poll loop catches up far faster than waiting on one precise daily
cron slot, using only this workflow's own GITHUB_TOKEN -- no external
service, no extra credentials.
"""
import json
import subprocess
from datetime import datetime, timezone

REPO = "mohit-saini-jpg/jobs-web"

# (workflow filename, target UTC hour, target UTC minute) -- mirrors each
# workflow's own `schedule:` cron value.
TARGETS = [
    ("scraper-fja-education.yml", 0, 7),
    ("auto-update-jobs.yml", 1, 30),
    ("check-broken-links.yml", 3, 30),
    ("ai-nightly.yml", 4, 0),
    ("ai-patch-html.yml", 7, 30),
    ("seo-guardian-fullscan.yml", 8, 0),
    ("google-index-daily.yml", 8, 30),
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def last_run_time(workflow):
    out = run(["gh", "run", "list", "--repo", REPO, "--workflow", workflow,
               "--limit", "1", "--json", "createdAt"])
    data = json.loads(out)
    if not data:
        return None
    return datetime.fromisoformat(data[0]["createdAt"].replace("Z", "+00:00"))


def main():
    now = datetime.now(timezone.utc)
    today = now.date()
    fired = []
    for workflow, hh, mm in TARGETS:
        target = datetime(today.year, today.month, today.day, hh, mm, tzinfo=timezone.utc)
        if now < target:
            continue  # not due yet today
        last = last_run_time(workflow)
        if last is not None and last >= target:
            continue  # something already ran for today's slot (on time or via this dispatcher)
        print(f"DUE: {workflow} (target {target.isoformat()}Z, last run {last})")
        run(["gh", "workflow", "run", workflow, "--repo", REPO, "--ref", "main"])
        fired.append(workflow)
    print(("Dispatched: " + ", ".join(fired)) if fired else "Nothing due right now.")


if __name__ == "__main__":
    main()
