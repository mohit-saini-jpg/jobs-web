#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================================
# PC-ONLY SCRAPER: sarkariresult.com (Cloudflare IP-block workaround)
# ================================================================
# PROBLEM:
#   sarkariresult.com Cloudflare GitHub Actions ke datacenter IP ko 403
#   deta hai (IP reputation block — code/TLS se fix nahi hota). Lekin
#   tumhare PC ka residential IP clean hai, wahan se 403 nahi aata.
#
# SOLUTION:
#   Ye script SIRF sarkariresult.com (Source 2) scrape karta hai aur
#   `sr_cache.json` banata hai. Tum ise apne PC pe chalao, phir
#   sr_cache.json ko GitHub repo (scraper/ folder) mein commit/upload
#   kar do. GitHub workflow jab chalega aur SR pe 403 khayega, to
#   automatically sr_cache.json se SR data load kar lega.
#
#   Baaki sab kuch (FJA, State, Education, sarkarinetwork, dedup, AI,
#   site generate) GitHub Actions pe normal chalta rahega — tumhe sirf
#   ye ek chhoti file update karni hai jab bhi fresh SR data chahiye.
#
# USAGE (apne PC pe):
#   1. Python install karo (3.9+)
#   2. pip install requests beautifulsoup4 lxml curl_cffi
#   3. Is file ko scraper/ folder mein rakho (scraper_sarkari.py ke saath)
#   4. Run:  python scrape_sr_only.py
#   5. sr_cache.json banegi — usse GitHub pe scraper/sr_cache.json pe upload karo
#
# Kitni baar chalana hai?
#   Jab bhi fresh SR data chahiye — har 2-3 din mein ek baar kaafi hai
#   (SR jobs roz dramatically nahi badalte). Cache purana ho to bhi site
#   chalti rahegi, bas SR section thoda stale hoga.
# ================================================================

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import json
from datetime import datetime

# scraper_sarkari.py se SR ke saare functions import karo (re-use, no dup)
import scraper_sarkari as SS


def scrape_sr_only():
    print("=" * 60)
    print("  SR-ONLY SCRAPER (PC / residential IP)")
    print("  Target: sarkariresult.com  →  sr_cache.json")
    print("=" * 60)

    # Homepage se category-wise links
    print("\n  Fetching homepage sections...")
    homepage_sections = SS.sr_get_homepage_sections()

    if not homepage_sections:
        print("\n  [ERROR] Homepage load nahi hui. Tumhare PC pe bhi block?")
        print("  - Internet check karo")
        print("  - VPN OFF karo (VPN ka IP bhi block ho sakta hai)")
        print("  - Browser mein https://www.sarkariresult.com khulta hai? Verify karo.")
        return None

    sr_data = {}
    sr_seen = set()

    # Same limits as the main scraper
    LIMITS = {
        "SR_Latest_Jobs": 80,
        "SR_Admit_Card":  25,
        "SR_Result":      25,
        "SR_Answer_Key":  20,
    }
    ACTIVE_FILTER = {"SR_Latest_Jobs"}

    for category, links in homepage_sections.items():
        print(f"\n  CATEGORY: {category}  ({len(links)} links found)")
        max_links = LIMITS.get(category, 25)
        links = links[:max_links]
        category_items = []

        for item in links:
            try:
                serial = item.get("serial", "")
                print(f"    [{serial}] {item['title'][:70]}")
                detail = SS.sr_scrape_detail(category, item["url"])
                if not detail:
                    continue
                # Active categories: skip expired
                if category in ACTIVE_FILTER:
                    last_date = (detail.get("importantDates", {}) or {}).get("lastDateApplyOnline", "")
                    if last_date and SS.is_expired(SS.date_to_iso(last_date)):
                        continue
                key = detail["title"].lower()
                if key in sr_seen:
                    continue
                sr_seen.add(key)
                if isinstance(detail.get("meta"), dict):
                    detail["meta"]["homepageSerial"] = serial
                detail = SS.sr_stamp_category(detail, category,
                                              detail.get("title", ""),
                                              item.get("url", ""))
                category_items.append(detail)
            except Exception as e:
                print("    SR ERROR:", e)
                continue

        sr_data[category] = category_items
        print(f"  SCRAPED: {len(category_items)}")

    sr_total = sum(len(v) for v in sr_data.values())
    print(f"\n  SARKARIRESULT.COM TOTAL: {sr_total}")

    if sr_total == 0:
        print("\n  [WARNING] 0 records scraped. Cache update NAHI kiya")
        print("  (purani cache safe rahegi). Internet/VPN check karo.")
        return None

    # Write cache
    out = {
        "saved_at": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
        "sr_data": sr_data,
    }
    with open("sr_cache.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"  ✅ sr_cache.json banayi gayi — {sr_total} records")
    print(f"  Categories: " + ", ".join(f"{k}={len(v)}" for k, v in sr_data.items()))
    print("\n  AGLA STEP:")
    print("  1. sr_cache.json ko GitHub repo mein scraper/sr_cache.json pe upload karo")
    print("  2. Commit karo")
    print("  3. Workflow agli baar chalega to SR data cache se aa jayega")
    print("=" * 60)
    return sr_data


if __name__ == "__main__":
    scrape_sr_only()
