"""
generate_mini.py — Automatic Mini JSON Generator
=================================================
Yeh script automatically 4 mini JSON files banata hai jo homepage ki
speed 3x fast karti hain. GitHub Actions me auto-run hoti hai.

Kaise kaam karta hai:
  Complete_Jobs_Full_Data.json  →  sections-mini.json  (section cards)
                                →  ticker-mini.json    (red ticker bar)
  merged_sarkari_data.json      →  merged-mini.json    (sarkari result cards)
  dailyupdates.json             →  daily-mini.json     (sidebar updates)

Kuch bhi update karo — yeh script apne aap sahi mini file bana dega.
"""

import json, re, os, datetime

print("=" * 55)
print("  Mini JSON Generator — TopSarkariJobs.com")
print("=" * 55)
print(f"  Run time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ── Helper ────────────────────────────────────────────────
def slugify(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text[:120].strip("-") or "job"

def write_json(path, data):
    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    size_kb = round(len(out) / 1024, 1)
    return size_kb

def load_json(path):
    if not os.path.exists(path):
        print(f"  ⚠️  File not found: {path} — skipping")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# ═══════════════════════════════════════════════════════════
# 1. sections-mini.json + ticker-mini.json
#    Source: Complete_Jobs_Full_Data.json
# ═══════════════════════════════════════════════════════════
print("▶ Reading Complete_Jobs_Full_Data.json ...")
full = load_json("Complete_Jobs_Full_Data.json")

if full:
    SECTION_CATS = [
        "Latest_Notifications", "10TH_Pass", "8TH_Pass", "12TH_Pass",
        "Diploma", "ITI", "B_Tech_BE", "B_Com", "Any_Graduate",
        "Any_Post_Graduate", "Railway_Jobs", "Police_Defence",
        "Teaching_Faculty", "Bank_Jobs", "Medical_Hospital",
        "Last_Date_Reminder",
    ]

    # ── sections-mini.json (homepage section cards) ──────
    # Top 10 jobs per category with only required fields
    sections_mini = {}
    total_jobs = 0
    for cat in SECTION_CATS:
        jobs = full.get(cat, [])
        if not isinstance(jobs, list):
            continue
        mini_jobs = []
        seen = set()
        for job in jobs:
            bd    = job.get("basic_details", {}) or {}
            dates = job.get("important_dates", {}) or {}
            title = (bd.get("job_title", "") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            slug = slugify(title)
            last_date = (dates.get("last_date", "") or "").strip()
            mini_jobs.append({
                "name": title[:120],
                "slug": slug,
                "date": last_date[:30] if last_date else "",
            })
            if len(mini_jobs) >= 10:
                break
        if mini_jobs:
            sections_mini[cat] = mini_jobs
            total_jobs += len(mini_jobs)

    size = write_json("sections-mini.json", sections_mini)
    print(f"  ✅ sections-mini.json — {size}KB | {total_jobs} jobs across {len(sections_mini)} categories")

    # ── ticker-mini.json (red ticker bar) ────────────────
    # Latest_Notifications only, top 40, slug+title only
    ticker_jobs = full.get("Latest_Notifications", [])
    ticker_mini = {}
    count = 0
    seen = set()
    for job in ticker_jobs:
        bd    = job.get("basic_details", {}) or {}
        title = (bd.get("job_title", "") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        slug = slugify(title)
        ticker_mini[slug + "-latest-notifications"] = {
            "title": title[:120],
            "cat":   "Latest_Notifications",
        }
        count += 1
        if count >= 40:
            break

    size = write_json("ticker-mini.json", ticker_mini)
    print(f"  ✅ ticker-mini.json   — {size}KB | {count} latest notifications")

else:
    print("  ⚠️  Skipped sections-mini.json and ticker-mini.json")

print()

# ═══════════════════════════════════════════════════════════
# 2. merged-mini.json
#    Source: merged_sarkari_data.json
#    Contains: SR_Latest_Jobs, SR_Result, SR_Admit_Card,
#              LATEST_JOBS NEW, OFFLINE_FORM, UPCOMING_JOBS etc.
# ═══════════════════════════════════════════════════════════
print("▶ Reading merged_sarkari_data.json ...")
merged = load_json("merged_sarkari_data.json")

if merged:
    all_jobs = merged.get("jobs", [])

    # Group by category
    by_cat = {}
    for job in all_jobs:
        cat = job.get("category", "OTHER")
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(job)

    # Take top 8 per category — preserves ALL categories
    selected = []
    for cat, jobs in by_cat.items():
        selected.extend(jobs[:8])

    merged_mini = {
        "scraped_at": merged.get("scraped_at", ""),
        "total":      merged.get("total", len(all_jobs)),
        "jobs":       selected,
    }

    size = write_json("merged-mini.json", merged_mini)
    cat_summary = {cat: len(jobs[:8]) for cat, jobs in by_cat.items()}
    print(f"  ✅ merged-mini.json   — {size}KB | {len(selected)} jobs")
    for cat, cnt in cat_summary.items():
        print(f"     {cat}: {cnt}")

else:
    print("  ⚠️  Skipped merged-mini.json")

print()

# ═══════════════════════════════════════════════════════════
# 3. daily-mini.json
#    Source: dailyupdates.json
#    Contains: Today Updates, Top 20 Jobs, Govt Scheme etc.
# ═══════════════════════════════════════════════════════════
print("▶ Reading dailyupdates.json ...")
daily = load_json("dailyupdates.json")

if daily:
    sections = daily.get("sections", [])
    mini_sections = []
    for sec in sections:
        items = sec.get("items", [])
        # "Today Updates" section — show all (usually 6-10)
        # Other sections — top 6 only (sidebar me space kam hai)
        limit = len(items) if sec.get("title") == "Today Updates" else 6
        mini_sec = dict(sec)
        mini_sec["items"] = items[:limit]
        mini_sections.append(mini_sec)

    daily_mini = {"sections": mini_sections}
    size = write_json("daily-mini.json", daily_mini)
    total_items = sum(len(s.get("items", [])) for s in mini_sections)
    print(f"  ✅ daily-mini.json    — {size}KB | {total_items} items across {len(mini_sections)} sections")
    for sec in mini_sections:
        print(f"     {sec.get('title','?')}: {len(sec.get('items',[]))}")

else:
    print("  ⚠️  Skipped daily-mini.json")

print()
print("=" * 55)
print("  ✅ All mini files generated successfully!")
print("=" * 55)
