#!/usr/bin/env python3
"""
ai_quota_monitor.py — Track AI quota usage and completion progress.

Usage:
  python3 ai_quota_monitor.py          # today's status
  python3 ai_quota_monitor.py --history  # last 30 days
  python3 ai_quota_monitor.py --estimate  # when will all 5000+ jobs be done?
"""
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path


def load_today_usage():
    """Load today's API usage from the sidecar file."""
    usage_file = Path("scraper/ai_usage_tracker.json")
    if not usage_file.exists():
        return {"date": date.today().isoformat(), "requests_today": 0, "tokens_today": 0}
    
    u = json.load(open(usage_file, encoding="utf-8"))
    today = date.today().isoformat()
    
    # if file is from a previous day, reset
    if u.get("date") != today:
        return {"date": today, "requests_today": 0, "tokens_today": 0}
    return u


def load_history():
    """Load historical usage (last 30 days)."""
    hist_file = Path("ai_daily_usage_history.json")
    if hist_file.exists():
        return json.load(open(hist_file, encoding="utf-8"))
    return []


def count_jobs_with_ai():
    """Count how many jobs already have AI content (have content_hash set)."""
    data_file = Path("scraper/data/Complete_Jobs_Full_Data.json")
    if not data_file.exists():
        data_file = Path("Complete_Jobs_Full_Data.json")
    
    if not data_file.exists():
        return 0, 0
    
    m = json.load(open(data_file, encoding="utf-8"))
    total = m.get("total_records", 0)
    
    with_ai = 0
    for job, source in iter_all_jobs(m):
        if job.get("content_hash"):
            with_ai += 1
    
    return with_ai, total


def iter_all_jobs(m):
    """Iterate over all jobs in the 4 sources (same pattern as ai_content_layer.py)."""
    for j in m.get("sarkari_data", {}).get("jobs", []):
        yield j, "sarkari"
    for cat, jobs in m.get("freejobalert_categories", {}).items():
        if isinstance(jobs, list):
            for j in jobs:
                yield j, "fja"
    for sec in m.get("state_jobs", {}).get("sections", []):
        for j in sec.get("items", []):
            yield j, "state"
    for sec in m.get("education_jobs", {}).get("sections", []):
        for j in sec.get("items", []):
            yield j, "education"


def show_today_status():
    """Show today's quota status."""
    u = load_today_usage()
    used = u["requests_today"]
    daily_limit = 1000
    remaining = max(0, daily_limit - used)
    pct = (used / daily_limit * 100) if daily_limit > 0 else 0
    
    jobs_with_ai, total_jobs = count_jobs_with_ai()
    
    print("\n" + "="*70)
    print("  AI CONTENT LAYER — TODAY'S STATUS")
    print("="*70)
    print(f"  Date:              {u.get('date', 'N/A')}")
    print(f"  API Requests:      {used:5d} / {daily_limit}")
    print(f"  Remaining:         {remaining:5d}")
    print(f"  Usage:             {pct:6.1f}%")
    print()
    print(f"  Jobs with AI:      {jobs_with_ai:5d} / {total_jobs}")
    print(f"  Progress:          {(jobs_with_ai/total_jobs*100 if total_jobs > 0 else 0):6.1f}%")
    
    if remaining > 0:
        jobs_left = total_jobs - jobs_with_ai
        avg_per_day = (used if used > 0 else 100)  # conservative: use actual today or 100
        est_days = max(1, (jobs_left + avg_per_day - 1) // avg_per_day)
        est_complete = date.today() + timedelta(days=est_days)
        print(f"  Estimate:          ~{est_days} more days (complete by {est_complete.isoformat()})")
    else:
        print(f"  Status:            ✅ Daily quota exhausted — will resume tomorrow")
    
    print("="*70 + "\n")


def show_history(days=30):
    """Show historical usage over the last N days."""
    hist = load_history()
    if not hist:
        print("No history available yet.\n")
        return
    
    # keep last N days
    hist = hist[-days:]
    
    print("\n" + "="*70)
    print(f"  AI QUOTA HISTORY — Last {days} days")
    print("="*70)
    print(f"  {'Date':<12} {'Requests':<12} {'% of 1000':<15} {'Cumulative':<15}")
    print("-"*70)
    
    cumulative = 0
    for entry in hist:
        d = entry.get("date", "")
        req = entry.get("requests_today", 0)
        cumulative += req
        pct = (req / 1000 * 100) if req > 0 else 0
        print(f"  {d:<12} {req:>5d}/1000    {pct:>6.1f}%       {cumulative:>5d}")
    
    print("-"*70)
    avg_per_day = cumulative / len(hist) if hist else 0
    print(f"  Average per day: {avg_per_day:.0f} requests")
    print(f"  Total so far: {cumulative} requests")
    print("="*70 + "\n")


def show_estimate():
    """Estimate when all jobs will have AI content."""
    hist = load_history()
    u = load_today_usage()
    jobs_with_ai, total_jobs = count_jobs_with_ai()
    
    if total_jobs == 0:
        print("No jobs data found.\n")
        return
    
    # calculate average daily burn
    if hist:
        recent_7 = hist[-7:] if len(hist) >= 7 else hist
        total_recent = sum(h.get("requests_today", 0) for h in recent_7)
        avg_daily = total_recent / len(recent_7)
    else:
        # fallback: use today
        avg_daily = u.get("requests_today", 0) or 100
    
    jobs_left = total_jobs - jobs_with_ai
    days_remaining = max(1, (jobs_left + avg_daily - 1) // avg_daily)
    complete_date = date.today() + timedelta(days=days_remaining)
    
    print("\n" + "="*70)
    print("  COMPLETION ESTIMATE")
    print("="*70)
    print(f"  Total jobs:        {total_jobs}")
    print(f"  With AI content:   {jobs_with_ai}")
    print(f"  Remaining:         {jobs_left}")
    print()
    print(f"  Daily average:     {avg_daily:.0f} requests/day")
    print(f"  Days to complete:  ~{days_remaining} days")
    print(f"  Est. complete by:  {complete_date.isoformat()}")
    print("="*70 + "\n")


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--history":
            show_history(30)
        elif sys.argv[1] == "--estimate":
            show_estimate()
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Usage: python3 ai_quota_monitor.py [--history|--estimate]")
    else:
        show_today_status()


if __name__ == "__main__":
    main()
