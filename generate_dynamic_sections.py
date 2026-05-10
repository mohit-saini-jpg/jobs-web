#!/usr/bin/env python3
"""
generate_dynamic_sections.py
============================
Daily run karo yeh script:
    python3 generate_dynamic_sections.py

Kya karta hai:
  - Complete_Jobs_Full_Data.json padhta hai
  - Har category ke jobs se name + internal /jobs/ URL banata hai
  - dynamic-sections.json generate karta hai jo homepage pe render hota hai

Script.js already name se /jobs/<slug>/ URL banata hai,
isliye URL field mein sirf "#" ya placeholder chahiye —
lekin hum "" (empty string nahi, placeholder) dete hain
taaki script.js slug-based routing use kare.

Usage:
    python3 generate_dynamic_sections.py
    python3 generate_dynamic_sections.py --input data/jobs_2026_05_10.json
    python3 generate_dynamic_sections.py --input Complete_Jobs_Full_Data.json --output dynamic-sections.json
"""

import json
import re
import unicodedata
import argparse
import os
from datetime import datetime

# ─── CONFIG ──────────────────────────────────────────────────────────────────

INPUT_FILE  = "Complete_Jobs_Full_Data.json"
OUTPUT_FILE = "dynamic-sections.json"

# Category → section config mapping
# id must match what script.js / view.html expects
CATEGORY_MAP = [
    {
        "data_key":  "Latest_Notifications",
        "id":        "latest jobs",
        "title":     "Latest Jobs",
        "icon":      "fas fa-briefcase",
        "color":     "#3b82f6",
    },
    {
        "data_key":  "8TH_Pass",
        "id":        "8th Pass",
        "title":     "8th Pass",
        "icon":      "fas fa-school",
        "color":     "#f59e0b",
    },
    {
        "data_key":  "10TH_Pass",
        "id":        "10th Pass jobs",
        "title":     "10th Pass Jobs",
        "icon":      "fas fa-graduation-cap",
        "color":     "#10b981",
    },
    {
        "data_key":  "12TH_Pass",
        "id":        "12th Pass jobs",
        "title":     "12th Pass Jobs",
        "icon":      "fas fa-graduation-cap",
        "color":     "#f97316",
    },
    {
        "data_key":  "ITI",
        "id":        "ITI Pass jobs",
        "title":     "ITI Pass Jobs",
        "icon":      "fas fa-wrench",
        "color":     "#8b5cf6",
    },
    {
        "data_key":  "Diploma",
        "id":        "Diploma Jobs",
        "title":     "Diploma Jobs",
        "icon":      "fas fa-scroll",
        "color":     "#06b6d4",
    },
    {
        "data_key":  "B_Tech_BE",
        "id":        "B.Tech Jobs",
        "title":     "B.Tech Jobs",
        "icon":      "fas fa-microchip",
        "color":     "#3b82f6",
    },
    {
        "data_key":  "B_Com",
        "id":        "B.Com Jobs",
        "title":     "B.Com Jobs",
        "icon":      "fas fa-calculator",
        "color":     "#14b8a6",
    },
    {
        "data_key":  "Any_Graduate",
        "id":        "Graduation jobs",
        "title":     "Graduation Jobs",
        "icon":      "fas fa-university",
        "color":     "#6366f1",
    },
    {
        "data_key":  "Any_Post_Graduate",
        "id":        "Post Graduation jobs",
        "title":     "Post Graduation Jobs",
        "icon":      "fas fa-user-tie",
        "color":     "#a855f7",
    },
    {
        "data_key":  "Railway_Jobs",
        "id":        "Railway Jobs",
        "title":     "Railway Jobs",
        "icon":      "fas fa-train",
        "color":     "#ef4444",
    },
    {
        "data_key":  "Police_Defence",
        "id":        "Police Jobs",
        "title":     "Police & Defence Jobs",
        "icon":      "fas fa-shield-halved",
        "color":     "#1d4ed8",
    },
    {
        "data_key":  "Teaching_Faculty",
        "id":        "Teacher Jobs",
        "title":     "Teacher Jobs",
        "icon":      "fas fa-chalkboard-user",
        "color":     "#059669",
    },
    {
        "data_key":  "Bank_Jobs",
        "id":        "Bank Jobs",
        "title":     "Bank Jobs",
        "icon":      "fas fa-building-columns",
        "color":     "#0ea5e9",
    },
    {
        "data_key":  "Medical_Hospital",
        "id":        "Medical/ Healthcare Jobs",
        "title":     "Medical/Healthcare Jobs",
        "icon":      "fas fa-stethoscope",
        "color":     "#dc2626",
    },
]

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Same logic as script.js slugifyTitle()"""
    text = str(text or "")
    # NFKD normalize
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", " and ").replace("'", "").replace("'", "")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    text = re.sub(r"-{2,}", "-", text)
    return text[:120] or "official-link"


def format_last_date(raw: str) -> str:
    """
    Convert various date formats to DD/MM/YYYY for display in item name.
    '14 May 2026' → '14/05/2026'
    Returns empty string if unparseable or too long.
    """
    raw = str(raw or "").strip()
    if not raw or len(raw) > 50:
        return ""

    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }

    # "14 May 2026"
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw)
    if m:
        day, mon, yr = m.groups()
        mo = months.get(mon[:3].lower(), "")
        if mo:
            return f"{int(day):02d}/{mo}/{yr}"

    # "14-05-2026" or "14/05/2026"
    m = re.match(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", raw)
    if m:
        d, mo, yr = m.groups()
        return f"{int(d):02d}/{int(mo):02d}/{yr}"

    # "21.05.2026 (11:59 PM)" — strip time
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", raw)
    if m:
        d, mo, yr = m.groups()
        return f"{int(d):02d}/{int(mo):02d}/{yr}"

    # "01-06-2026"
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})", raw)
    if m:
        d, mo, yr = m.groups()
        return f"{d}/{mo}/{yr}"

    return ""


def make_item_name(job: dict) -> str:
    """
    Build the display name for a job item.
    Format: "<job_title> Last Date: DD/MM/YYYY"
    """
    bd = job.get("basic_details", {})
    title = str(bd.get("job_title", "")).strip()
    if not title:
        return ""

    last_date_raw = job.get("important_dates", {}).get("last_date", "")
    last_date_fmt = format_last_date(last_date_raw)

    if last_date_fmt:
        return f"{title} Last Date: {last_date_fmt}"
    return title


def make_internal_url(job: dict) -> str:
    """
    Build internal /jobs/<slug>/ URL from job title.
    script.js also does this on the fly, but having it in JSON
    makes view.html direct linking work too.
    """
    bd = job.get("basic_details", {})
    title = str(bd.get("job_title", "")).strip()
    slug = slugify(title)
    return f"/jobs/{slug}/"


# ─── MAIN ────────────────────────────────────────────────────────────────────

def generate(input_file: str, output_file: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Reading: {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    sections = []
    total_items = 0

    for cat_cfg in CATEGORY_MAP:
        data_key = cat_cfg["data_key"]
        jobs = full_data.get(data_key, [])

        if not jobs:
            print(f"  ⚠ Skipping '{data_key}' — no data found")
            continue

        items = []
        seen_names = set()

        for job in jobs:
            name = make_item_name(job)
            if not name:
                continue

            # Deduplicate by name
            name_key = name.lower().strip()
            if name_key in seen_names:
                continue
            seen_names.add(name_key)

            url = make_internal_url(job)
            items.append({"name": name, "url": url})

        section = {
            "id":          cat_cfg["id"],
            "title":       cat_cfg["title"],
            "icon":        cat_cfg["icon"],
            "color":       cat_cfg["color"],
            "viewMoreType": "list",
            "items":       items,
        }
        sections.append(section)
        total_items += len(items)
        print(f"  ✓ [{cat_cfg['id']}] {len(items)} jobs added")

    output = {"sections": sections}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(output_file) / 1024
    print(f"\n✅ Done! {len(sections)} sections, {total_items} total jobs")
    print(f"   Output: {output_file} ({size_kb:.1f} KB)")
    print(f"\n📋 Next steps:")
    print(f"   1. Copy '{output_file}' to your GitHub repo root")
    print(f"   2. Copy 'Complete_Jobs_Full_Data.json' to your GitHub repo root")
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"   3. git add . && git commit -m 'Update jobs {date_str}' && git push")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate dynamic-sections.json from Complete_Jobs_Full_Data.json")
    parser.add_argument("--input",  default=INPUT_FILE,  help=f"Input JSON file (default: {INPUT_FILE})")
    parser.add_argument("--output", default=OUTPUT_FILE, help=f"Output JSON file (default: {OUTPUT_FILE})")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        print(f"   Place your scraped JSON as '{args.input}' and run again.")
        exit(1)

    generate(args.input, args.output)
