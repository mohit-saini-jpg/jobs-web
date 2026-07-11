#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================================
# SCRAPER: FreeJobAlert District-Wise Jobs — scraper_district.py
# ================================================================
# Source  : freejobalert.com (district-wise jobs:
#           /search-jobs/jobs-in-<district>/)
# Writes  : _temp_district.json  (raw district dict)
# Output  : Updates "freejobalert_district" in Complete_Jobs_Full_Data.json
#           Baaki saare sources (sarkari, education, state,
#           freejobalert_categories) UNCHANGED rehte hain.
#
# NOTE: Ye scraper_fja.py (NEW v9: Qualification-based categories) ka
# HUBAHU SAME LOGIC use karta hai — sirf CATEGORIES dict 37 qualification
# URLs ki jagah 697 district URLs (District_Wise_Jobs.xlsx se) use karta
# hai. Listing-page collection, job-detail extraction, table parsers,
# link classification, retry/resume/throttle — sab kuch IDENTICAL hai.
#
# Run:  python scraper_district.py
# ================================================================

import sys
sys.stdout.reconfigure(encoding="utf-8")

# ================================================================
# SOURCE: FREEJOBALERT DISTRICT-WISE JOBS
# ================================================================

import requests
from bs4 import BeautifulSoup
import time
import json
import re
import os
from urllib.parse import urljoin
from fja_parse_helpers import (
    sanitize_dom, is_ad_text, resolve_href,
    isolate_vacancy_tables, extract_section_text,
    merge_breakdown, looks_like_question, extract_content_sections,
    extended_date_field, needs_refresh, now_iso,
)
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ============================================================
# VERSION: v1 (district-wise, scraper_fja.py v11 logic se adapt kiya)
#
# Ye scraper_fja.py ke saath IDENTICAL hai in cheezon mein:
#   - Listing page link collection (Method A-F, pagination, "Other
#     Latest Govt Jobs" stop-trigger)
#   - extract_job_page() — same H2-section based table parsing
#   - "No jobs" page detection
#   - Retry / resume / throttle / auto-save logic
#
# FARQ sirf itna hai:
#   - CATEGORIES dict = 697 district-wise URLs (District_Wise_Jobs.xlsx
#     se, 30 states/UTs)
#   - DISTRICT_META dict = har category-key ka state + district naam
#     (taaki output job mein "state"/"district" tag ho sake)
#   - QUAL_STRICT_CATEGORIES / QUAL_KEYWORDS / strict-qualification-
#     verification logic REMOVED — districts qualification-based nahi
#     hain, isliye wo cheez yahan applicable nahi
#   - generate_qualification_wise_json() REMOVED — district scraper
#     ke liye irrelevant
#   - PAN_INDIA_CATEGORIES set khali hai (district khud hi location hai)
#   - job["basic_details"]["job_location"] fallback: agar listing/page
#     se location nahi mila toh DISTRICT_META se district+state set
#     ho jata hai (state-extraction fallback se BEHTAR, kyunki yahan
#     district level granularity available hai)
# ============================================================


# ============================================================
# CONFIG
# ============================================================
DELAY          = 1.0          # listing page delay (rate-limit safe)
JOB_DELAY      = 0.5          # per-job delay (rate-limit safe)
MAX_WORKERS    = 8             # parallel job page fetches
MAX_RETRIES    = 3

import random as _random

# ── Smart Delay — human browsing simulate karta hai ─────────────
# Har request ke beech random wait hoga — rate-limit bahut kam aayegi.
#
# Profile     | Base   | Jitter   | When
# ------------|--------|----------|----------------------------------
# "fast"      | 0.4s   | ±0.3s   | parallel job detail fetches
# "normal"    | 1.0s   | ±0.5s   | listing page navigation
# "slow"      | 2.5s   | ±1.0s   | after error / rate-limit signal
# "crawl"     | 5.0s   | ±2.0s   | aggressive bot-detection fallback

_SMART_DELAY_PROFILES = {
    "fast":   (0.4,  0.3),
    "normal": (1.0,  0.5),
    "slow":   (2.5,  1.0),
    "crawl":  (5.0,  2.0),
}

def smart_delay(profile: str = "normal", *, extra: float = 0.0):
    """
    Human-like random wait karo.

    Args:
        profile : "fast" | "normal" | "slow" | "crawl"
        extra   : additional fixed seconds (e.g. retry backoff se)

    Usage:
        smart_delay()            # listing page ke beech
        smart_delay("fast")      # parallel job fetch ke beech
        smart_delay("slow")      # 429 / error ke baad
        smart_delay(extra=10)    # retry ke baad 10s extra
    """
    base, jitter = _SMART_DELAY_PROFILES.get(profile, (1.0, 0.5))
    wait = base + _random.uniform(-jitter, jitter)
    wait = max(0.1, wait) + extra   # kabhi negative nahi
    time.sleep(wait)



HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Referer":         "https://www.google.com/",
}

# ── Categories (District-Wise) ───────────────────────────────
# 697 districts across 30 states/UTs (source: District_Wise_Jobs.xlsx)
# URL pattern: https://www.freejobalert.com/search-jobs/jobs-in-<district>/
CATEGORIES = {
    # ── Haryana ─────────────────────────────────
    "Ambala": "https://www.freejobalert.com/search-jobs/jobs-in-ambala/",
    "Fatehabad": "https://www.freejobalert.com/search-jobs/jobs-in-fatehabad/",
    "Jhajjar": "https://www.freejobalert.com/search-jobs/jobs-in-jhajjar/",
    "Karnal": "https://www.freejobalert.com/search-jobs/jobs-in-karnal/",
    "Mewat": "https://www.freejobalert.com/search-jobs/jobs-in-mewat/",
    "Panchkula": "https://www.freejobalert.com/search-jobs/jobs-in-panchkula/",
    "Rohtak": "https://www.freejobalert.com/search-jobs/jobs-in-rohtak/",
    "Yamunanagar": "https://www.freejobalert.com/search-jobs/jobs-in-yamunanagar/",
    "Bhiwani": "https://www.freejobalert.com/search-jobs/jobs-in-bhiwani/",
    "Gurgaon": "https://www.freejobalert.com/search-jobs/jobs-in-gurgaon/",
    "Jind": "https://www.freejobalert.com/search-jobs/jobs-in-jind/",
    "Kurukshetra": "https://www.freejobalert.com/search-jobs/jobs-in-kurukshetra/",
    "Narnaul": "https://www.freejobalert.com/search-jobs/jobs-in-narnaul/",
    "Panipat": "https://www.freejobalert.com/search-jobs/jobs-in-panipat/",
    "Sirsa": "https://www.freejobalert.com/search-jobs/jobs-in-sirsa/",
    "Faridabad": "https://www.freejobalert.com/search-jobs/jobs-in-faridabad/",
    "Hissar": "https://www.freejobalert.com/search-jobs/jobs-in-hissar/",
    "Kaithal": "https://www.freejobalert.com/search-jobs/jobs-in-kaithal/",
    "Mahendergarh": "https://www.freejobalert.com/search-jobs/jobs-in-mahendergarh/",
    "Palwal": "https://www.freejobalert.com/search-jobs/jobs-in-palwal/",
    "Rewari": "https://www.freejobalert.com/search-jobs/jobs-in-rewari/",
    "Sonepat": "https://www.freejobalert.com/search-jobs/jobs-in-sonepat/",
    # ── Andhra Pradesh ─────────────────────────────────
    "Anantapur": "https://www.freejobalert.com/search-jobs/jobs-in-anantapur/",
    "East_Godavari": "https://www.freejobalert.com/search-jobs/jobs-in-east-godavari/",
    "Kakinada": "https://www.freejobalert.com/search-jobs/jobs-in-kakinada/",
    "Machilipatnam": "https://www.freejobalert.com/search-jobs/jobs-in-machilipatnam/",
    "Prakasam": "https://www.freejobalert.com/search-jobs/jobs-in-prakasam/",
    "Srikakulam": "https://www.freejobalert.com/search-jobs/jobs-in-srikakulam/",
    "Visakhapatnam": "https://www.freejobalert.com/search-jobs/jobs-in-visakhapatnam/",
    "Chittoor": "https://www.freejobalert.com/search-jobs/jobs-in-chittoor/",
    "Guntakal": "https://www.freejobalert.com/search-jobs/jobs-in-guntakal/",
    "Krishna": "https://www.freejobalert.com/search-jobs/jobs-in-krishna/",
    "Nandyal": "https://www.freejobalert.com/search-jobs/jobs-in-nandyal/",
    "Purbam_Medinipur": "https://www.freejobalert.com/search-jobs/jobs-in-purbam-medinipur/",
    "Tirupati": "https://www.freejobalert.com/search-jobs/jobs-in-tirupati/",
    "Vizianagaram": "https://www.freejobalert.com/search-jobs/jobs-in-vizianagaram/",
    "Cuddapah": "https://www.freejobalert.com/search-jobs/jobs-in-cuddapah/",
    "Guntur": "https://www.freejobalert.com/search-jobs/jobs-in-guntur/",
    "Kurnool": "https://www.freejobalert.com/search-jobs/jobs-in-kurnool/",
    "Nellore": "https://www.freejobalert.com/search-jobs/jobs-in-nellore/",
    "Rajahmundry": "https://www.freejobalert.com/search-jobs/jobs-in-rajahmundry/",
    "Vijayawada": "https://www.freejobalert.com/search-jobs/jobs-in-vijayawada/",
    "West_Godavari": "https://www.freejobalert.com/search-jobs/jobs-in-west-godavari/",
    # ── Arunachal Pradesh ─────────────────────────────────
    "Aalo": "https://www.freejobalert.com/search-jobs/jobs-in-aalo/",
    "Basar": "https://www.freejobalert.com/search-jobs/jobs-in-basar/",
    "Bomdila": "https://www.freejobalert.com/search-jobs/jobs-in-bomdila/",
    "Chowkham": "https://www.freejobalert.com/search-jobs/jobs-in-chowkham/",
    "Deomali": "https://www.freejobalert.com/search-jobs/jobs-in-deomali/",
    "East_Siang": "https://www.freejobalert.com/search-jobs/jobs-in-east-siang/",
    "Itanagar": "https://www.freejobalert.com/search-jobs/jobs-in-itanagar/",
    "Khonsa": "https://www.freejobalert.com/search-jobs/jobs-in-khonsa/",
    "Lumla": "https://www.freejobalert.com/search-jobs/jobs-in-lumla/",
    "Namsang": "https://www.freejobalert.com/search-jobs/jobs-in-namsang/",
    "Pasighat": "https://www.freejobalert.com/search-jobs/jobs-in-pasighat/",
    "Sagalee": "https://www.freejobalert.com/search-jobs/jobs-in-sagalee/",
    "Tawang": "https://www.freejobalert.com/search-jobs/jobs-in-tawang/",
    "Tirap": "https://www.freejobalert.com/search-jobs/jobs-in-tirap/",
    "Yingkiong": "https://www.freejobalert.com/search-jobs/jobs-in-yingkiong/",
    "Doimukh": "https://www.freejobalert.com/search-jobs/jobs-in-doimukh/",
    "Gandhigram": "https://www.freejobalert.com/search-jobs/jobs-in-gandhigram/",
    "Jairampur": "https://www.freejobalert.com/search-jobs/jobs-in-jairampur/",
    "Liromoba": "https://www.freejobalert.com/search-jobs/jobs-in-liromoba/",
    "Naharlagun": "https://www.freejobalert.com/search-jobs/jobs-in-naharlagun/",
    "Nyapin": "https://www.freejobalert.com/search-jobs/jobs-in-nyapin/",
    "Roing": "https://www.freejobalert.com/search-jobs/jobs-in-roing/",
    "Seppa": "https://www.freejobalert.com/search-jobs/jobs-in-seppa/",
    "Tezu": "https://www.freejobalert.com/search-jobs/jobs-in-tezu/",
    "Tuting": "https://www.freejobalert.com/search-jobs/jobs-in-tuting/",
    "Yupia": "https://www.freejobalert.com/search-jobs/jobs-in-yupia/",
    "Dumporijo": "https://www.freejobalert.com/search-jobs/jobs-in-dumporijo/",
    "Hawai": "https://www.freejobalert.com/search-jobs/jobs-in-hawai/",
    "Kanubari": "https://www.freejobalert.com/search-jobs/jobs-in-kanubari/",
    "Longding": "https://www.freejobalert.com/search-jobs/jobs-in-longding/",
    "Namsai": "https://www.freejobalert.com/search-jobs/jobs-in-namsai/",
    "Pangin": "https://www.freejobalert.com/search-jobs/jobs-in-pangin/",
    "Ruksin": "https://www.freejobalert.com/search-jobs/jobs-in-ruksin/",
    "Taliha": "https://www.freejobalert.com/search-jobs/jobs-in-taliha/",
    "Tinsukia_Assam": "https://www.freejobalert.com/search-jobs/jobs-in-tinsukia-assam/",
    "Vijaynagar": "https://www.freejobalert.com/search-jobs/jobs-in-vijaynagar/",
    "Ziro": "https://www.freejobalert.com/search-jobs/jobs-in-ziro/",
    # ── Assam ─────────────────────────────────
    "Baksa": "https://www.freejobalert.com/search-jobs/jobs-in-baksa/",
    "Bongaigaon": "https://www.freejobalert.com/search-jobs/jobs-in-bongaigaon/",
    "Darrang": "https://www.freejobalert.com/search-jobs/jobs-in-darrang/",
    "Dibrugarh": "https://www.freejobalert.com/search-jobs/jobs-in-dibrugarh/",
    "Goalpara": "https://www.freejobalert.com/search-jobs/jobs-in-goalpara/",
    "Hailakandi": "https://www.freejobalert.com/search-jobs/jobs-in-hailakandi/",
    "Kamrup": "https://www.freejobalert.com/search-jobs/jobs-in-kamrup/",
    "Kokrajhar": "https://www.freejobalert.com/search-jobs/jobs-in-kokrajhar/",
    "Nagaon": "https://www.freejobalert.com/search-jobs/jobs-in-nagaon/",
    "Silchar": "https://www.freejobalert.com/search-jobs/jobs-in-silchar/",
    "Tezpur": "https://www.freejobalert.com/search-jobs/jobs-in-tezpur/",
    "Barpeta": "https://www.freejobalert.com/search-jobs/jobs-in-barpeta/",
    "Cachar": "https://www.freejobalert.com/search-jobs/jobs-in-cachar/",
    "Dhemaji": "https://www.freejobalert.com/search-jobs/jobs-in-dhemaji/",
    "Dima_Hasao": "https://www.freejobalert.com/search-jobs/jobs-in-dima-hasao/",
    "Golaghat": "https://www.freejobalert.com/search-jobs/jobs-in-golaghat/",
    "Hojai": "https://www.freejobalert.com/search-jobs/jobs-in-hojai/",
    "Karbi_Anglong": "https://www.freejobalert.com/search-jobs/jobs-in-karbi-anglong/",
    "Lakhimpur": "https://www.freejobalert.com/search-jobs/jobs-in-lakhimpur/",
    "Nalbari": "https://www.freejobalert.com/search-jobs/jobs-in-nalbari/",
    "Sivasagar": "https://www.freejobalert.com/search-jobs/jobs-in-sivasagar/",
    "Tinsukia": "https://www.freejobalert.com/search-jobs/jobs-in-tinsukia/",
    "Biswanath": "https://www.freejobalert.com/search-jobs/jobs-in-biswanath/",
    "Chirang": "https://www.freejobalert.com/search-jobs/jobs-in-chirang/",
    "Dhubri": "https://www.freejobalert.com/search-jobs/jobs-in-dhubri/",
    "Dispur": "https://www.freejobalert.com/search-jobs/jobs-in-dispur/",
    "Guwahati": "https://www.freejobalert.com/search-jobs/jobs-in-guwahati/",
    "Jorhat": "https://www.freejobalert.com/search-jobs/jobs-in-jorhat/",
    "Karimganj": "https://www.freejobalert.com/search-jobs/jobs-in-karimganj/",
    "Morigaon": "https://www.freejobalert.com/search-jobs/jobs-in-morigaon/",
    "Sibsagar": "https://www.freejobalert.com/search-jobs/jobs-in-sibsagar/",
    "Sonitpur": "https://www.freejobalert.com/search-jobs/jobs-in-sonitpur/",
    "Udalguri": "https://www.freejobalert.com/search-jobs/jobs-in-udalguri/",
    # ── Bihar ─────────────────────────────────
    "Araria": "https://www.freejobalert.com/search-jobs/jobs-in-araria/",
    "Banka": "https://www.freejobalert.com/search-jobs/jobs-in-banka/",
    "Bhojpur": "https://www.freejobalert.com/search-jobs/jobs-in-bhojpur/",
    "Gaya": "https://www.freejobalert.com/search-jobs/jobs-in-gaya/",
    "Jehanabad": "https://www.freejobalert.com/search-jobs/jobs-in-jehanabad/",
    "Khagaria": "https://www.freejobalert.com/search-jobs/jobs-in-khagaria/",
    "Madhepura": "https://www.freejobalert.com/search-jobs/jobs-in-madhepura/",
    "Muzaffarpur": "https://www.freejobalert.com/search-jobs/jobs-in-muzaffarpur/",
    "Pashchim_Champaran": "https://www.freejobalert.com/search-jobs/jobs-in-pashchim-champaran/",
    "Purnia": "https://www.freejobalert.com/search-jobs/jobs-in-purnia/",
    "Samastipur": "https://www.freejobalert.com/search-jobs/jobs-in-samastipur/",
    "Arwal": "https://www.freejobalert.com/search-jobs/jobs-in-arwal/",
    "Begusarai": "https://www.freejobalert.com/search-jobs/jobs-in-begusarai/",
    "Buxar": "https://www.freejobalert.com/search-jobs/jobs-in-buxar/",
    "Gopalganj": "https://www.freejobalert.com/search-jobs/jobs-in-gopalganj/",
    "Kaimur": "https://www.freejobalert.com/search-jobs/jobs-in-kaimur/",
    "Kishanganj": "https://www.freejobalert.com/search-jobs/jobs-in-kishanganj/",
    "Madhubani": "https://www.freejobalert.com/search-jobs/jobs-in-madhubani/",
    "Nalanda": "https://www.freejobalert.com/search-jobs/jobs-in-nalanda/",
    "Patna": "https://www.freejobalert.com/search-jobs/jobs-in-patna/",
    "Rohtas": "https://www.freejobalert.com/search-jobs/jobs-in-rohtas/",
    "Saran": "https://www.freejobalert.com/search-jobs/jobs-in-saran/",
    "Aurangabad_Bihar": "https://www.freejobalert.com/search-jobs/jobs-in-aurangabad-bihar/",
    "Bhagalpur": "https://www.freejobalert.com/search-jobs/jobs-in-bhagalpur/",
    "Darbhanga": "https://www.freejobalert.com/search-jobs/jobs-in-darbhanga/",
    "Jamui": "https://www.freejobalert.com/search-jobs/jobs-in-jamui/",
    "Katihar": "https://www.freejobalert.com/search-jobs/jobs-in-katihar/",
    "Lakhisarai": "https://www.freejobalert.com/search-jobs/jobs-in-lakhisarai/",
    "Munger": "https://www.freejobalert.com/search-jobs/jobs-in-munger/",
    "Nawada": "https://www.freejobalert.com/search-jobs/jobs-in-nawada/",
    "Purbi_Champaran": "https://www.freejobalert.com/search-jobs/jobs-in-purbi-champaran/",
    "Saharsa": "https://www.freejobalert.com/search-jobs/jobs-in-saharsa/",
    "Sheikhpura": "https://www.freejobalert.com/search-jobs/jobs-in-sheikhpura/",
    # ── Chhattisgarh ─────────────────────────────────
    "Bastar": "https://www.freejobalert.com/search-jobs/jobs-in-bastar/",
    "Bijapur": "https://www.freejobalert.com/search-jobs/jobs-in-bijapur/",
    "Dhamtari": "https://www.freejobalert.com/search-jobs/jobs-in-dhamtari/",
    "Janjgir_Champa": "https://www.freejobalert.com/search-jobs/jobs-in-janjgir-champa/",
    "Kanker": "https://www.freejobalert.com/search-jobs/jobs-in-kanker/",
    "Mahasamund": "https://www.freejobalert.com/search-jobs/jobs-in-mahasamund/",
    "Raipur": "https://www.freejobalert.com/search-jobs/jobs-in-raipur/",
    "Surguja": "https://www.freejobalert.com/search-jobs/jobs-in-surguja/",
    "Bemetara": "https://www.freejobalert.com/search-jobs/jobs-in-bemetara/",
    "Bilaspur_Chhattisgarh": "https://www.freejobalert.com/search-jobs/jobs-in-bilaspur-chhattisgarh/",
    "Durg": "https://www.freejobalert.com/search-jobs/jobs-in-durg/",
    "Jashpur": "https://www.freejobalert.com/search-jobs/jobs-in-jashpur/",
    "Korba": "https://www.freejobalert.com/search-jobs/jobs-in-korba/",
    "Narayanpur": "https://www.freejobalert.com/search-jobs/jobs-in-narayanpur/",
    "Rajnandgaon": "https://www.freejobalert.com/search-jobs/jobs-in-rajnandgaon/",
    "Bhilai_Durg": "https://www.freejobalert.com/search-jobs/jobs-in-bhilai-durg/",
    "Dantewada": "https://www.freejobalert.com/search-jobs/jobs-in-dantewada/",
    "Gariaband": "https://www.freejobalert.com/search-jobs/jobs-in-gariaband/",
    "Kabirdham": "https://www.freejobalert.com/search-jobs/jobs-in-kabirdham/",
    "Korea": "https://www.freejobalert.com/search-jobs/jobs-in-korea/",
    "Raigarh_Chhattisgarh": "https://www.freejobalert.com/search-jobs/jobs-in-raigarh-chhattisgarh/",
    "Surajpur": "https://www.freejobalert.com/search-jobs/jobs-in-surajpur/",
    # ── Delhi ─────────────────────────────────
    "Alwar_Delhi": "https://www.freejobalert.com/search-jobs/jobs-in-alwar-delhi/",
    "Bahadurgarh": "https://www.freejobalert.com/search-jobs/jobs-in-bahadurgarh/",
    "Ballabgarh": "https://www.freejobalert.com/search-jobs/jobs-in-ballabgarh/",
    "Bhiwadi": "https://www.freejobalert.com/search-jobs/jobs-in-bhiwadi/",
    "Bhiwani_Delhi": "https://www.freejobalert.com/search-jobs/jobs-in-bhiwani-delhi/",
    "Faridabad_Delhi": "https://www.freejobalert.com/search-jobs/jobs-in-faridabad-delhi/",
    "Ghaziabad_Delhi": "https://www.freejobalert.com/search-jobs/jobs-in-ghaziabad-delhi/",
    "Gurgaon_Delhi": "https://www.freejobalert.com/search-jobs/jobs-in-gurgaon-delhi/",
    "Kundli_CharkhiDadri": "https://www.freejobalert.com/search-jobs/jobs-in-kundli-charkhidadri/",
    "Loni": "https://www.freejobalert.com/search-jobs/jobs-in-loni/",
    "Manesar": "https://www.freejobalert.com/search-jobs/jobs-in-manesar/",
    "New_Delhi": "https://www.freejobalert.com/search-jobs/jobs-in-new-delhi/",
    "Noida_Delhi": "https://www.freejobalert.com/search-jobs/jobs-in-noida-greater-noida-delhi/",
    "Sonepat_Delhi": "https://www.freejobalert.com/search-jobs/jobs-in-sonepat-delhi/",
    # ── Goa ─────────────────────────────────
    "North_Goa": "https://www.freejobalert.com/search-jobs/jobs-in-north-goa/",
    "Panaji": "https://www.freejobalert.com/search-jobs/jobs-in-panjim-panaji/",
    "South_Goa": "https://www.freejobalert.com/search-jobs/jobs-in-south-goa/",
    "Vasco_Da_Gama": "https://www.freejobalert.com/search-jobs/jobs-in-vasco-da-gama/",
    # ── Gujarat ─────────────────────────────────
    "Bhuj": "https://www.freejobalert.com/search-jobs/jobs-in-bhuj/",
    "Gandhinagar": "https://www.freejobalert.com/search-jobs/jobs-in-gandhinagar/",
    "Junagadh": "https://www.freejobalert.com/search-jobs/jobs-in-junagadh/",
    "Kandla": "https://www.freejobalert.com/search-jobs/jobs-in-kandla/",
    "Narmada": "https://www.freejobalert.com/search-jobs/jobs-in-narmada/",
    "Patan": "https://www.freejobalert.com/search-jobs/jobs-in-patan/",
    "Sabarkantha": "https://www.freejobalert.com/search-jobs/jobs-in-sabarkantha/",
    "Tapi": "https://www.freejobalert.com/search-jobs/jobs-in-tapi/",
    "Valsad_Vapi": "https://www.freejobalert.com/search-jobs/jobs-in-valsad-vapi/",
    "Dohad": "https://www.freejobalert.com/search-jobs/jobs-in-dohad/",
    "Gir": "https://www.freejobalert.com/search-jobs/jobs-in-gir/",
    "Junagarh": "https://www.freejobalert.com/search-jobs/jobs-in-junagarh/",
    "Mehsana": "https://www.freejobalert.com/search-jobs/jobs-in-mehsana/",
    "Navsari": "https://www.freejobalert.com/search-jobs/jobs-in-navsari/",
    "Porbandar": "https://www.freejobalert.com/search-jobs/jobs-in-porbandar/",
    "Surat": "https://www.freejobalert.com/search-jobs/jobs-in-surat/",
    "The_Dangs": "https://www.freejobalert.com/search-jobs/jobs-in-dangs/",
    "Gandhidham": "https://www.freejobalert.com/search-jobs/jobs-in-gandhidham/",
    "Jamnagar": "https://www.freejobalert.com/search-jobs/jobs-in-jamnagar/",
    "Kachchh": "https://www.freejobalert.com/search-jobs/jobs-in-kachchh/",
    "Morbi": "https://www.freejobalert.com/search-jobs/jobs-in-morbi/",
    "PanchMahal": "https://www.freejobalert.com/search-jobs/jobs-in-panchmahal/",
    "Rajkot": "https://www.freejobalert.com/search-jobs/jobs-in-rajkot/",
    "Surendranagar": "https://www.freejobalert.com/search-jobs/jobs-in-surendranagar/",
    "Vadodara": "https://www.freejobalert.com/search-jobs/jobs-in-vadodara/",
    # ── Himachal Pradesh ─────────────────────────────────
    "Baddi": "https://www.freejobalert.com/search-jobs/jobs-in-baddi/",
    "Dalhousie": "https://www.freejobalert.com/search-jobs/jobs-in-dalhousie/",
    "Kangra": "https://www.freejobalert.com/search-jobs/jobs-in-kangra/",
    "Kullu": "https://www.freejobalert.com/search-jobs/jobs-in-kullu/",
    "Mandi": "https://www.freejobalert.com/search-jobs/jobs-in-mandi/",
    "Shimla": "https://www.freejobalert.com/search-jobs/jobs-in-shimla/",
    "Bilaspur": "https://www.freejobalert.com/search-jobs/jobs-in-bilaspur/",
    "Dharamshala": "https://www.freejobalert.com/search-jobs/jobs-in-dharamshala/",
    "Kasauli": "https://www.freejobalert.com/search-jobs/jobs-in-kasauli/",
    "Lahaul_Spiti": "https://www.freejobalert.com/search-jobs/jobs-in-lahaul-and-spiti/",
    "Nalagarh": "https://www.freejobalert.com/search-jobs/jobs-in-nalagarh/",
    "sirmaur": "https://www.freejobalert.com/search-jobs/jobs-in-sirmaur/",
    "Chamba": "https://www.freejobalert.com/search-jobs/jobs-in-chamba/",
    "Hamirpur": "https://www.freejobalert.com/search-jobs/jobs-in-hamirpur/",
    "Kinnaur": "https://www.freejobalert.com/search-jobs/jobs-in-kinnaur/",
    "Manali": "https://www.freejobalert.com/search-jobs/jobs-in-manali/",
    "Parwanoo": "https://www.freejobalert.com/search-jobs/jobs-in-parwanoo/",
    "Solan": "https://www.freejobalert.com/search-jobs/jobs-in-solan/",
    # ── Jammu and Kashmir ─────────────────────────────────
    "Anantnag": "https://www.freejobalert.com/search-jobs/jobs-in-anantnag/",
    "Bandipora": "https://www.freejobalert.com/search-jobs/jobs-in-bandipora/",
    "Baramulla": "https://www.freejobalert.com/search-jobs/jobs-in-baramulla/",
    "Budgam": "https://www.freejobalert.com/search-jobs/jobs-in-budgam/",
    "Doda": "https://www.freejobalert.com/search-jobs/jobs-in-doda/",
    "Ganderbal": "https://www.freejobalert.com/search-jobs/jobs-in-ganderbal/",
    "Jammu": "https://www.freejobalert.com/search-jobs/jobs-in-jammu/",
    "Kargil": "https://www.freejobalert.com/search-jobs/jobs-in-kargil/",
    "Kathua": "https://www.freejobalert.com/search-jobs/jobs-in-kathua/",
    "Kishtwar": "https://www.freejobalert.com/search-jobs/jobs-in-kishtwar/",
    "Kulgam": "https://www.freejobalert.com/search-jobs/jobs-in-kulgam/",
    "Kupwara": "https://www.freejobalert.com/search-jobs/jobs-in-kupwara/",
    "Leh": "https://www.freejobalert.com/search-jobs/jobs-in-leh/",
    "Poonch": "https://www.freejobalert.com/search-jobs/jobs-in-poonch/",
    "Pulwama": "https://www.freejobalert.com/search-jobs/jobs-in-pulwama/",
    "Punch": "https://www.freejobalert.com/search-jobs/jobs-in-punch/",
    "Rajouri": "https://www.freejobalert.com/search-jobs/jobs-in-rajouri/",
    "Ramban": "https://www.freejobalert.com/search-jobs/jobs-in-ramban/",
    "Reasi": "https://www.freejobalert.com/search-jobs/jobs-in-reasi/",
    "Samba": "https://www.freejobalert.com/search-jobs/jobs-in-samba/",
    "Shupiyan": "https://www.freejobalert.com/search-jobs/jobs-in-shupiyan/",
    "Srinagar": "https://www.freejobalert.com/search-jobs/jobs-in-srinagar/",
    "Udhampur": "https://www.freejobalert.com/search-jobs/jobs-in-udhampur/",
    # ── Jharkhand ─────────────────────────────────
    "Bokaro": "https://www.freejobalert.com/search-jobs/jobs-in-bokaro/",
    "Dhanbad": "https://www.freejobalert.com/search-jobs/jobs-in-dhanbad/",
    "Giridih": "https://www.freejobalert.com/search-jobs/jobs-in-giridih/",
    "Hazaribagh": "https://www.freejobalert.com/search-jobs/jobs-in-hazaribagh/",
    "Khunti": "https://www.freejobalert.com/search-jobs/jobs-in-khunti/",
    "Latehar": "https://www.freejobalert.com/search-jobs/jobs-in-latehar/",
    "Palamu": "https://www.freejobalert.com/search-jobs/jobs-in-palamu/",
    "Ramgarh": "https://www.freejobalert.com/search-jobs/jobs-in-ramgarh/",
    "Saraikela_Kharsawan": "https://www.freejobalert.com/search-jobs/jobs-in-saraikela-kharsawan/",
    "Chatra": "https://www.freejobalert.com/search-jobs/jobs-in-chatra/",
    "Dumka": "https://www.freejobalert.com/search-jobs/jobs-in-dumka/",
    "Godda": "https://www.freejobalert.com/search-jobs/jobs-in-godda/",
    "Jamshedpur": "https://www.freejobalert.com/search-jobs/jobs-in-jamshedpur/",
    "Kodarma": "https://www.freejobalert.com/search-jobs/jobs-in-kodarma/",
    "Lohardaga": "https://www.freejobalert.com/search-jobs/jobs-in-lohardaga/",
    "Pashchimi_Singhbhum": "https://www.freejobalert.com/search-jobs/jobs-in-pashchimi-singhbhum/",
    "Ranchi": "https://www.freejobalert.com/search-jobs/jobs-in-ranchi/",
    "Deoghar": "https://www.freejobalert.com/search-jobs/jobs-in-deoghar/",
    "Garhwa": "https://www.freejobalert.com/search-jobs/jobs-in-garhwa/",
    "Gumla": "https://www.freejobalert.com/search-jobs/jobs-in-gumla/",
    "Jamtara": "https://www.freejobalert.com/search-jobs/jobs-in-jamtara/",
    "Koderma": "https://www.freejobalert.com/search-jobs/jobs-in-koderma/",
    "Pakur": "https://www.freejobalert.com/search-jobs/jobs-in-pakur/",
    "Purbi_Singhbhum": "https://www.freejobalert.com/search-jobs/jobs-in-purbi-singhbhum/",
    "Sahibganj": "https://www.freejobalert.com/search-jobs/jobs-in-sahibganj/",
    # ── Karnataka ─────────────────────────────────
    "Bagalkot": "https://www.freejobalert.com/search-jobs/jobs-in-bagalkot/",
    "Belgaum": "https://www.freejobalert.com/search-jobs/jobs-in-belgaum/",
    "Bijapur_Karnataka": "https://www.freejobalert.com/search-jobs/jobs-in-bijapur-karnataka/",
    "Chikmagalur": "https://www.freejobalert.com/search-jobs/jobs-in-chikmagalur/",
    "Davanagere": "https://www.freejobalert.com/search-jobs/jobs-in-davanagere/",
    "Gulbarga": "https://www.freejobalert.com/search-jobs/jobs-in-gulbarga/",
    "Hubli": "https://www.freejobalert.com/search-jobs/jobs-in-hubli/",
    "Koppal": "https://www.freejobalert.com/search-jobs/jobs-in-koppal/",
    "Mysore": "https://www.freejobalert.com/search-jobs/jobs-in-mysore/",
    "Shimoga": "https://www.freejobalert.com/search-jobs/jobs-in-shimoga/",
    "Uttara_Kannada": "https://www.freejobalert.com/search-jobs/jobs-in-uttara-kannada/",
    "Bangalore": "https://www.freejobalert.com/search-jobs/jobs-in-bengaluru-bangalore/",
    "Bellary": "https://www.freejobalert.com/search-jobs/jobs-in-bellary/",
    "Chamarajanagar": "https://www.freejobalert.com/search-jobs/jobs-in-chamarajanagar/",
    "Chitradurga": "https://www.freejobalert.com/search-jobs/jobs-in-chitradurga/",
    "Dharwad": "https://www.freejobalert.com/search-jobs/jobs-in-dharwad/",
    "Hassan": "https://www.freejobalert.com/search-jobs/jobs-in-hassan/",
    "Kodagu": "https://www.freejobalert.com/search-jobs/jobs-in-kodagu/",
    "Mandya": "https://www.freejobalert.com/search-jobs/jobs-in-mandya/",
    "Raichur": "https://www.freejobalert.com/search-jobs/jobs-in-raichur/",
    "Tumkur": "https://www.freejobalert.com/search-jobs/jobs-in-tumkur/",
    "Vijaya_Nagara": "https://www.freejobalert.com/search-jobs/jobs-in-vijaya-nagara/",
    "Chikkaballapura": "https://www.freejobalert.com/search-jobs/jobs-in-chikkaballapura/",
    "Dakshina_Kannada": "https://www.freejobalert.com/search-jobs/jobs-in-dakshina-kannada/",
    "Gadag": "https://www.freejobalert.com/search-jobs/jobs-in-gadag/",
    "Haveri": "https://www.freejobalert.com/search-jobs/jobs-in-haveri/",
    "Kolar": "https://www.freejobalert.com/search-jobs/jobs-in-kolar/",
    "Mangalore": "https://www.freejobalert.com/search-jobs/jobs-in-mangalore/",
    "Ramanagara": "https://www.freejobalert.com/search-jobs/jobs-in-ramanagara/",
    "Udupi": "https://www.freejobalert.com/search-jobs/jobs-in-udupi/",
    # ── Kerala ─────────────────────────────────
    "Alappuzha": "https://www.freejobalert.com/search-jobs/jobs-in-alappuzha/",
    "Idukki": "https://www.freejobalert.com/search-jobs/jobs-in-idukki/",
    "Kannur": "https://www.freejobalert.com/search-jobs/jobs-in-kannur/",
    "Kasaragod": "https://www.freejobalert.com/search-jobs/jobs-in-kasaragod/",
    "Kochi": "https://www.freejobalert.com/search-jobs/jobs-in-cochin-kochi-ernakulam/",
    "Kollam": "https://www.freejobalert.com/search-jobs/jobs-in-kollam/",
    "Kottayam": "https://www.freejobalert.com/search-jobs/jobs-in-kottayam/",
    "Kozhikode": "https://www.freejobalert.com/search-jobs/jobs-in-calicut-kozhikode/",
    "Malappuram": "https://www.freejobalert.com/search-jobs/jobs-in-malappuram/",
    "Palakkad": "https://www.freejobalert.com/search-jobs/jobs-in-palakkad/",
    "Pathanamthitta": "https://www.freejobalert.com/search-jobs/jobs-in-pathanamthitta/",
    "Thiruvananthapuram": "https://www.freejobalert.com/search-jobs/jobs-in-thiruvananthapuram/",
    "Thrissur": "https://www.freejobalert.com/search-jobs/jobs-in-thrissur/",
    "Wayanad": "https://www.freejobalert.com/search-jobs/jobs-in-wayanad/",
    # ── Madhya Pradesh ─────────────────────────────────
    "Alirajpur": "https://www.freejobalert.com/search-jobs/jobs-in-alirajpur/",
    "Balaghat": "https://www.freejobalert.com/search-jobs/jobs-in-balaghat/",
    "Bhind": "https://www.freejobalert.com/search-jobs/jobs-in-bhind/",
    "Chhattarpur": "https://www.freejobalert.com/search-jobs/jobs-in-chhattarpur/",
    "Datia": "https://www.freejobalert.com/search-jobs/jobs-in-datia/",
    "Dindori": "https://www.freejobalert.com/search-jobs/jobs-in-dindori/",
    "Gwalior": "https://www.freejobalert.com/search-jobs/jobs-in-gwalior/",
    "Indore": "https://www.freejobalert.com/search-jobs/jobs-in-indore/",
    "Katni": "https://www.freejobalert.com/search-jobs/jobs-in-katni/",
    "Mandsaur": "https://www.freejobalert.com/search-jobs/jobs-in-mandsaur/",
    "Neemuch": "https://www.freejobalert.com/search-jobs/jobs-in-neemuch/",
    "Rajgarh": "https://www.freejobalert.com/search-jobs/jobs-in-rajgarh/",
    "Sagar": "https://www.freejobalert.com/search-jobs/jobs-in-sagar/",
    "Seoni": "https://www.freejobalert.com/search-jobs/jobs-in-seoni/",
    "Sheopur": "https://www.freejobalert.com/search-jobs/jobs-in-sheopur/",
    "Singrauli": "https://www.freejobalert.com/search-jobs/jobs-in-singrauli/",
    "Ujjain": "https://www.freejobalert.com/search-jobs/jobs-in-ujjain/",
    "Morena": "https://www.freejobalert.com/search-jobs/jobs-in-morena/",
    "Panna": "https://www.freejobalert.com/search-jobs/jobs-in-panna/",
    "Ratlam": "https://www.freejobalert.com/search-jobs/jobs-in-ratlam/",
    "Satna": "https://www.freejobalert.com/search-jobs/jobs-in-satna/",
    "Shahdol": "https://www.freejobalert.com/search-jobs/jobs-in-shahdol/",
    "Shivpuri": "https://www.freejobalert.com/search-jobs/jobs-in-shivpuri/",
    "Tikamgarh": "https://www.freejobalert.com/search-jobs/jobs-in-tikamgarh/",
    "Umaria": "https://www.freejobalert.com/search-jobs/jobs-in-umaria/",
    "Narsimhapur": "https://www.freejobalert.com/search-jobs/jobs-in-narsimhapur/",
    "Raisen": "https://www.freejobalert.com/search-jobs/jobs-in-raisen/",
    "Rewa": "https://www.freejobalert.com/search-jobs/jobs-in-rewa/",
    "Sehore": "https://www.freejobalert.com/search-jobs/jobs-in-sehore/",
    "Shajapur": "https://www.freejobalert.com/search-jobs/jobs-in-shajapur/",
    "Sidhi": "https://www.freejobalert.com/search-jobs/jobs-in-sidhi/",
    "Uijain": "https://www.freejobalert.com/search-jobs/jobs-in-uijain/",
    "Vidisha": "https://www.freejobalert.com/search-jobs/jobs-in-vidisha/",
    # ── Maharashtra ─────────────────────────────────
    "Ahmednagar": "https://www.freejobalert.com/search-jobs/jobs-in-ahmednagar/",
    "Aurangabad": "https://www.freejobalert.com/search-jobs/jobs-in-aurangabad/",
    "Bid": "https://www.freejobalert.com/search-jobs/jobs-in-bid/",
    "Dhule": "https://www.freejobalert.com/search-jobs/jobs-in-dhule/",
    "Hingoli": "https://www.freejobalert.com/search-jobs/jobs-in-hingoli/",
    "Kolhapur": "https://www.freejobalert.com/search-jobs/jobs-in-kolhapur/",
    "Mahabaleshwar": "https://www.freejobalert.com/search-jobs/jobs-in-mahabaleshwar/",
    "Nagpur": "https://www.freejobalert.com/search-jobs/jobs-in-nagpur/",
    "Nasik": "https://www.freejobalert.com/search-jobs/jobs-in-nasik/",
    "Parbhani": "https://www.freejobalert.com/search-jobs/jobs-in-parbhani/",
    "Ratnagiri": "https://www.freejobalert.com/search-jobs/jobs-in-ratnagiri/",
    "Sindhudurg": "https://www.freejobalert.com/search-jobs/jobs-in-sindhudurg/",
    "Wardha": "https://www.freejobalert.com/search-jobs/jobs-in-wardha/",
    "Jalgaon": "https://www.freejobalert.com/search-jobs/jobs-in-jalgaon/",
    "Latur": "https://www.freejobalert.com/search-jobs/jobs-in-latur/",
    "Mumbai": "https://www.freejobalert.com/search-jobs/jobs-in-mumbai/",
    "Nanded": "https://www.freejobalert.com/search-jobs/jobs-in-nanded/",
    "Navi_Mumbai": "https://www.freejobalert.com/search-jobs/jobs-in-navi-mumbai/",
    "Pune": "https://www.freejobalert.com/search-jobs/jobs-in-pune/",
    "Sangli": "https://www.freejobalert.com/search-jobs/jobs-in-sangli/",
    "Solapur": "https://www.freejobalert.com/search-jobs/jobs-in-solapur/",
    "Washim": "https://www.freejobalert.com/search-jobs/jobs-in-washim/",
    "Jalna": "https://www.freejobalert.com/search-jobs/jobs-in-jalna/",
    "Lonavala": "https://www.freejobalert.com/search-jobs/jobs-in-lonavala/",
    "Mumbai_Suburban": "https://www.freejobalert.com/search-jobs/jobs-in-mumbai-suburban/",
    "Nandurbar": "https://www.freejobalert.com/search-jobs/jobs-in-nandurbar/",
    "Osmanabad": "https://www.freejobalert.com/search-jobs/jobs-in-osmanabad/",
    "Raigarh": "https://www.freejobalert.com/search-jobs/jobs-in-raigarh/",
    "Satara": "https://www.freejobalert.com/search-jobs/jobs-in-satara/",
    "Thane": "https://www.freejobalert.com/search-jobs/jobs-in-thane/",
    # ── Manipur ─────────────────────────────────
    "Bishnupur": "https://www.freejobalert.com/search-jobs/jobs-in-bishnupur/",
    "Chandel": "https://www.freejobalert.com/search-jobs/jobs-in-chandel/",
    "Churachandpur": "https://www.freejobalert.com/search-jobs/jobs-in-churachandpur/",
    "Imphal": "https://www.freejobalert.com/search-jobs/jobs-in-imphal/",
    "Senapati": "https://www.freejobalert.com/search-jobs/jobs-in-senapati/",
    "Tamenglong": "https://www.freejobalert.com/search-jobs/jobs-in-tamenglong/",
    "Thoubal": "https://www.freejobalert.com/search-jobs/jobs-in-thoubal/",
    "Ukhrul": "https://www.freejobalert.com/search-jobs/jobs-in-ukhrul/",
    # ── Meghalaya ─────────────────────────────────
    "East_Garo_Hills": "https://www.freejobalert.com/search-jobs/jobs-in-east-garo-hills/",
    "East_Khasi_Hills": "https://www.freejobalert.com/search-jobs/jobs-in-east-khasi-hills/",
    "Jaintia_Hills": "https://www.freejobalert.com/search-jobs/jobs-in-jaintia-hills/",
    "North_Garo_Hills": "https://www.freejobalert.com/search-jobs/jobs-in-north-garo-hills/",
    "Ri_Bhoi": "https://www.freejobalert.com/search-jobs/jobs-in-ri-bhoi/",
    "Shillong": "https://www.freejobalert.com/search-jobs/jobs-in-shilong/",
    "South_Garo_Hills": "https://www.freejobalert.com/search-jobs/jobs-in-south-garo-hills/",
    "West_Garo_Hills": "https://www.freejobalert.com/search-jobs/jobs-in-west-garo-hills/",
    "West_Khasi_Hills": "https://www.freejobalert.com/search-jobs/jobs-in-west-khasi-hills/",
    # ── Mizoram ─────────────────────────────────
    "Aizawal": "https://www.freejobalert.com/search-jobs/jobs-in-aizawal/",
    "Champhai": "https://www.freejobalert.com/search-jobs/jobs-in-champhai/",
    "Kolasib": "https://www.freejobalert.com/search-jobs/jobs-in-kolasib/",
    "Lawngtlai": "https://www.freejobalert.com/search-jobs/jobs-in-lawngtlai/",
    "Lunglei": "https://www.freejobalert.com/search-jobs/jobs-in-lunglei/",
    "Mamit": "https://www.freejobalert.com/search-jobs/jobs-in-mamit/",
    "Saiha": "https://www.freejobalert.com/search-jobs/jobs-in-saiha/",
    "Serchhip": "https://www.freejobalert.com/search-jobs/jobs-in-serchhip/",
    # ── Nagaland ─────────────────────────────────
    "Dimapur": "https://www.freejobalert.com/search-jobs/jobs-in-dimapur/",
    "Kiphire": "https://www.freejobalert.com/search-jobs/jobs-in-kiphire/",
    "Kohima": "https://www.freejobalert.com/search-jobs/jobs-in-kohima/",
    "Longleng": "https://www.freejobalert.com/search-jobs/jobs-in-longleng/",
    "Mokokchung": "https://www.freejobalert.com/search-jobs/jobs-in-mokokchung/",
    "Mon": "https://www.freejobalert.com/search-jobs/jobs-in-mon/",
    "Peren": "https://www.freejobalert.com/search-jobs/jobs-in-peren/",
    "Phek": "https://www.freejobalert.com/search-jobs/jobs-in-phek/",
    "Tuensang": "https://www.freejobalert.com/search-jobs/jobs-in-tuensang/",
    "Wokha": "https://www.freejobalert.com/search-jobs/jobs-in-wokha/",
    "Zunheboto": "https://www.freejobalert.com/search-jobs/jobs-in-zunheboto/",
    # ── Odisha ─────────────────────────────────
    "Anugul": "https://www.freejobalert.com/search-jobs/jobs-in-anugul/",
    "Balangir": "https://www.freejobalert.com/search-jobs/jobs-in-balangir/",
    "Baleshwar": "https://www.freejobalert.com/search-jobs/jobs-in-baleshwar/",
    "Bargarh": "https://www.freejobalert.com/search-jobs/jobs-in-bargarh/",
    "Baudh": "https://www.freejobalert.com/search-jobs/jobs-in-baudh/",
    "Bhadrak": "https://www.freejobalert.com/search-jobs/jobs-in-bhadrak/",
    "Bhubaneshwar": "https://www.freejobalert.com/search-jobs/jobs-in-bhubaneshwar/",
    "Cuttack": "https://www.freejobalert.com/search-jobs/jobs-in-cuttack/",
    "Debagarh": "https://www.freejobalert.com/search-jobs/jobs-in-debagarh/",
    "Dhenkanal": "https://www.freejobalert.com/search-jobs/jobs-in-dhenkanal/",
    "Gajapati": "https://www.freejobalert.com/search-jobs/jobs-in-gajapati/",
    "Ganjam": "https://www.freejobalert.com/search-jobs/jobs-in-ganjam/",
    "Jagatsinghapur": "https://www.freejobalert.com/search-jobs/jobs-in-jagatsinghapur/",
    "Jajapur": "https://www.freejobalert.com/search-jobs/jobs-in-jajapur/",
    "Jharsuguda": "https://www.freejobalert.com/search-jobs/jobs-in-jharsuguda/",
    "Kalahandi": "https://www.freejobalert.com/search-jobs/jobs-in-kalahandi/",
    "Kandhamal": "https://www.freejobalert.com/search-jobs/jobs-in-kandhamal/",
    "Kendrapara": "https://www.freejobalert.com/search-jobs/jobs-in-kendrapara/",
    "Kendujhar": "https://www.freejobalert.com/search-jobs/jobs-in-kendujhar/",
    "Khordha": "https://www.freejobalert.com/search-jobs/jobs-in-khordha/",
    "Koraput": "https://www.freejobalert.com/search-jobs/jobs-in-koraput/",
    "Malkangiri": "https://www.freejobalert.com/search-jobs/jobs-in-malkangiri/",
    "Mayurbhanj": "https://www.freejobalert.com/search-jobs/jobs-in-mayurbhanj/",
    "Nabarangapur": "https://www.freejobalert.com/search-jobs/jobs-in-nabarangapur/",
    "Nayagarh": "https://www.freejobalert.com/search-jobs/jobs-in-nayagarh/",
    "Nuapada": "https://www.freejobalert.com/search-jobs/jobs-in-nuapada/",
    "Paradeep": "https://www.freejobalert.com/search-jobs/jobs-in-paradeep/",
    "Puri": "https://www.freejobalert.com/search-jobs/jobs-in-puri/",
    "Rayagada": "https://www.freejobalert.com/search-jobs/jobs-in-rayagada/",
    "Rourkela": "https://www.freejobalert.com/search-jobs/jobs-in-rourkela/",
    "Sambalpur": "https://www.freejobalert.com/search-jobs/jobs-in-sambalpur/",
    "Subarnapur": "https://www.freejobalert.com/search-jobs/jobs-in-subarnapur/",
    "Sundargarh": "https://www.freejobalert.com/search-jobs/jobs-in-sundargarh/",
    # ── Punjab ─────────────────────────────────
    "Amritsar": "https://www.freejobalert.com/search-jobs/jobs-in-amritsar/",
    "Barnala": "https://www.freejobalert.com/search-jobs/jobs-in-barnala/",
    "Batala": "https://www.freejobalert.com/search-jobs/jobs-in-batala/",
    "Bathinda": "https://www.freejobalert.com/search-jobs/jobs-in-bathinda/",
    "Faridkot": "https://www.freejobalert.com/search-jobs/jobs-in-faridkot/",
    "Fatehgarh_Sahib": "https://www.freejobalert.com/search-jobs/jobs-in-fatehgarh-sahib/",
    "Fazilka": "https://www.freejobalert.com/search-jobs/jobs-in-fazilka/",
    "Ferozepur": "https://www.freejobalert.com/search-jobs/jobs-in-ferozepur/",
    "Gurdaspur": "https://www.freejobalert.com/search-jobs/jobs-in-gurdaspur/",
    "Hoshiarpur": "https://www.freejobalert.com/search-jobs/jobs-in-hoshiarpur/",
    "Jalandhar": "https://www.freejobalert.com/search-jobs/jobs-in-jalandhar/",
    "Kapurthala": "https://www.freejobalert.com/search-jobs/jobs-in-kapurthala/",
    "Ludhiana": "https://www.freejobalert.com/search-jobs/jobs-in-ludhiana/",
    "Mansa": "https://www.freejobalert.com/search-jobs/jobs-in-mansa/",
    "Moga": "https://www.freejobalert.com/search-jobs/jobs-in-moga/",
    "Mohali": "https://www.freejobalert.com/search-jobs/jobs-in-mohali/",
    "Muktsar": "https://www.freejobalert.com/search-jobs/jobs-in-muktsar/",
    "Nawanshahr": "https://www.freejobalert.com/search-jobs/jobs-in-nawanshahr/",
    "Pathankot": "https://www.freejobalert.com/search-jobs/jobs-in-pathankot/",
    "Patiala": "https://www.freejobalert.com/search-jobs/jobs-in-patiala/",
    "Rewari_Haryana": "https://www.freejobalert.com/search-jobs/jobs-in-rewari-haryana/",
    "Ropar": "https://www.freejobalert.com/search-jobs/jobs-in-ropar/",
    "Rupnagar": "https://www.freejobalert.com/search-jobs/jobs-in-rupnagar/",
    "Sangrur": "https://www.freejobalert.com/search-jobs/jobs-in-sangrur/",
    "Shahid_Bhagat_Singh_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-shahid-bhagat-singh-nagar/",
    "Tarn_Taran": "https://www.freejobalert.com/search-jobs/jobs-in-tarn-taran/",
    # ── Rajasthan ─────────────────────────────────
    "Ajmer": "https://www.freejobalert.com/search-jobs/jobs-in-ajmer/",
    "Baran": "https://www.freejobalert.com/search-jobs/jobs-in-baran/",
    "Bhilwara": "https://www.freejobalert.com/search-jobs/jobs-in-bhilwara/",
    "Chittaurgarh": "https://www.freejobalert.com/search-jobs/jobs-in-chittaurgarh/",
    "Dhaulpur": "https://www.freejobalert.com/search-jobs/jobs-in-dhaulpur/",
    "Hanumangarh": "https://www.freejobalert.com/search-jobs/jobs-in-hanumangarh/",
    "Jalor": "https://www.freejobalert.com/search-jobs/jobs-in-jalor/",
    "Jodhpur": "https://www.freejobalert.com/search-jobs/jobs-in-jodhpur/",
    "Nagaur": "https://www.freejobalert.com/search-jobs/jobs-in-nagaur/",
    "Rajsamand": "https://www.freejobalert.com/search-jobs/jobs-in-rajsamand/",
    "Sirohi": "https://www.freejobalert.com/search-jobs/jobs-in-sirohi/",
    "Alwar": "https://www.freejobalert.com/search-jobs/jobs-in-alwar/",
    "Barmer": "https://www.freejobalert.com/search-jobs/jobs-in-barmer/",
    "Bikaner": "https://www.freejobalert.com/search-jobs/jobs-in-bikaner/",
    "Churu": "https://www.freejobalert.com/search-jobs/jobs-in-churu/",
    "Dungarpur": "https://www.freejobalert.com/search-jobs/jobs-in-dungarpur/",
    "Jaipur": "https://www.freejobalert.com/search-jobs/jobs-in-jaipur/",
    "Jhalawar": "https://www.freejobalert.com/search-jobs/jobs-in-jhalawar/",
    "Karauli": "https://www.freejobalert.com/search-jobs/jobs-in-karauli/",
    "Pali": "https://www.freejobalert.com/search-jobs/jobs-in-pali/",
    "Sawai_Madhopur": "https://www.freejobalert.com/search-jobs/jobs-in-sawai-madhopur/",
    "Tonk": "https://www.freejobalert.com/search-jobs/jobs-in-tonk/",
    "Bundi": "https://www.freejobalert.com/search-jobs/jobs-in-bundi/",
    "Dausa": "https://www.freejobalert.com/search-jobs/jobs-in-dausa/",
    "Ganganagar": "https://www.freejobalert.com/search-jobs/jobs-in-ganganagar/",
    "Jaisalmer": "https://www.freejobalert.com/search-jobs/jobs-in-jaisalmer/",
    "Jhunjhunun": "https://www.freejobalert.com/search-jobs/jobs-in-jhunjhunun/",
    "Kota": "https://www.freejobalert.com/search-jobs/jobs-in-kota/",
    "Pratapgarh_Rajasthan": "https://www.freejobalert.com/search-jobs/jobs-in-pratapgarh-rajasthan/",
    "Sikar": "https://www.freejobalert.com/search-jobs/jobs-in-sikar/",
    # ── Sikkim ─────────────────────────────────
    "East_Sikkim": "https://www.freejobalert.com/search-jobs/jobs-in-east-sikkim/",
    "Gangtok": "https://www.freejobalert.com/search-jobs/jobs-in-gangtok/",
    "North_Sikkim": "https://www.freejobalert.com/search-jobs/jobs-in-north-sikkim/",
    "South_Sikkim": "https://www.freejobalert.com/search-jobs/jobs-in-south-sikkim/",
    "West_Sikkim": "https://www.freejobalert.com/search-jobs/jobs-in-west-sikkim/",
    # ── Tamil Nadu ─────────────────────────────────
    "Ariyalur": "https://www.freejobalert.com/search-jobs/jobs-in-ariyalur/",
    "Coimbatore": "https://www.freejobalert.com/search-jobs/jobs-in-coimbatore/",
    "Dindigul": "https://www.freejobalert.com/search-jobs/jobs-in-dindigul/",
    "Kancheepuram": "https://www.freejobalert.com/search-jobs/jobs-in-kancheepuram/",
    "Karur": "https://www.freejobalert.com/search-jobs/jobs-in-karur/",
    "Madurai": "https://www.freejobalert.com/search-jobs/jobs-in-madurai/",
    "Namakkal": "https://www.freejobalert.com/search-jobs/jobs-in-namakkal/",
    "Perambalur": "https://www.freejobalert.com/search-jobs/jobs-in-perambalur/",
    "Salem": "https://www.freejobalert.com/search-jobs/jobs-in-salem/",
    "Theni": "https://www.freejobalert.com/search-jobs/jobs-in-theni/",
    "Tirunelveli": "https://www.freejobalert.com/search-jobs/jobs-in-tirunelveli/",
    "Tiruvannamalai": "https://www.freejobalert.com/search-jobs/jobs-in-tiruvannamalai/",
    "Vellore": "https://www.freejobalert.com/search-jobs/jobs-in-vellore/",
    "Chennai": "https://www.freejobalert.com/search-jobs/jobs-in-chennai/",
    "Cuddalore": "https://www.freejobalert.com/search-jobs/jobs-in-cuddalore/",
    "Erode": "https://www.freejobalert.com/search-jobs/jobs-in-erode/",
    "Kanniyakumari": "https://www.freejobalert.com/search-jobs/jobs-in-kanniyakumari/",
    "Krishnagiri": "https://www.freejobalert.com/search-jobs/jobs-in-krishnagiri/",
    "Nagapattinam": "https://www.freejobalert.com/search-jobs/jobs-in-nagapattinam/",
    "Nilgiris": "https://www.freejobalert.com/search-jobs/jobs-in-nilgiris/",
    "Pudukkottai": "https://www.freejobalert.com/search-jobs/jobs-in-pudukkottai/",
    "Sivaganga": "https://www.freejobalert.com/search-jobs/jobs-in-sivaganga/",
    "Thiruvallur": "https://www.freejobalert.com/search-jobs/jobs-in-thiruvallur/",
    "Tirupathur": "https://www.freejobalert.com/search-jobs/jobs-in-tirupathur/",
    "Trichy": "https://www.freejobalert.com/search-jobs/jobs-in-trichy/",
    "Viluppuram": "https://www.freejobalert.com/search-jobs/jobs-in-viluppuram/",
    "Kumbakonam": "https://www.freejobalert.com/search-jobs/jobs-in-kumbakonam/",
    "Nagercoil": "https://www.freejobalert.com/search-jobs/jobs-in-nagercoil/",
    "Ooty": "https://www.freejobalert.com/search-jobs/jobs-in-ooty/",
    "Ramanathapuram": "https://www.freejobalert.com/search-jobs/jobs-in-ramanathapuram/",
    "Thanjavur": "https://www.freejobalert.com/search-jobs/jobs-in-thanjavur/",
    "Thiruvarur": "https://www.freejobalert.com/search-jobs/jobs-in-thiruvarur/",
    "Tiruppur": "https://www.freejobalert.com/search-jobs/jobs-in-tiruppur/",
    "Tuticorin": "https://www.freejobalert.com/search-jobs/jobs-in-tuticorin/",
    # ── Telangana ─────────────────────────────────
    "Adilabad": "https://www.freejobalert.com/search-jobs/jobs-in-adilabad/",
    "Jagtial": "https://www.freejobalert.com/search-jobs/jobs-in-jagtial/",
    "Jogulamba_Gadwal": "https://www.freejobalert.com/search-jobs/jobs-in-jogulamba-gadwal/",
    "Khammam": "https://www.freejobalert.com/search-jobs/jobs-in-khammam/",
    "Mahabubnagar": "https://www.freejobalert.com/search-jobs/jobs-in-mahabubnagar/",
    "Medak": "https://www.freejobalert.com/search-jobs/jobs-in-medak/",
    "Nalgonda": "https://www.freejobalert.com/search-jobs/jobs-in-nalgonda/",
    "Peddapalli": "https://www.freejobalert.com/search-jobs/jobs-in-peddapalli/",
    "Sangareddy": "https://www.freejobalert.com/search-jobs/jobs-in-sangareddy/",
    "Vikarabad": "https://www.freejobalert.com/search-jobs/jobs-in-vikarabad/",
    "Kamareddy": "https://www.freejobalert.com/search-jobs/jobs-in-kamareddy/",
    "Komaram_Bheem_Asifabad": "https://www.freejobalert.com/search-jobs/jobs-in-komaram-bheem-asifabad/",
    "Mahbubnagar": "https://www.freejobalert.com/search-jobs/jobs-in-mahbubnagar/",
    "Medchal": "https://www.freejobalert.com/search-jobs/jobs-in-medchal/",
    "Nirmal": "https://www.freejobalert.com/search-jobs/jobs-in-nirmal/",
    "Rajanna_Sircilla": "https://www.freejobalert.com/search-jobs/jobs-in-rajanna-sircilla/",
    "Siddipet": "https://www.freejobalert.com/search-jobs/jobs-in-siddipet/",
    "Wanaparthy": "https://www.freejobalert.com/search-jobs/jobs-in-wanaparthy/",
    "Karimnagar": "https://www.freejobalert.com/search-jobs/jobs-in-karimnagar/",
    "Mahabubabad": "https://www.freejobalert.com/search-jobs/jobs-in-mahabubabad/",
    "Mancherial": "https://www.freejobalert.com/search-jobs/jobs-in-mancherial/",
    "Nagarkurnool": "https://www.freejobalert.com/search-jobs/jobs-in-nagarkurnool/",
    "Nizamabad": "https://www.freejobalert.com/search-jobs/jobs-in-nizamabad/",
    "Ranga_Reddy": "https://www.freejobalert.com/search-jobs/jobs-in-ranga-reddy/",
    "Suryapet": "https://www.freejobalert.com/search-jobs/jobs-in-suryapet/",
    "Warangal": "https://www.freejobalert.com/search-jobs/jobs-in-warangal/",
    # ── Tripura ─────────────────────────────────
    "Agartala": "https://www.freejobalert.com/search-jobs/jobs-in-agartala/",
    "Dhalai": "https://www.freejobalert.com/search-jobs/jobs-in-dhalai/",
    "North_Tripura": "https://www.freejobalert.com/search-jobs/jobs-in-north-tripura/",
    "South_Tripura": "https://www.freejobalert.com/search-jobs/jobs-in-south-tripura/",
    "Unakoti": "https://www.freejobalert.com/search-jobs/jobs-in-unakoti/",
    "West_Tripura": "https://www.freejobalert.com/search-jobs/jobs-in-west-tripura/",
    # ── Uttar Pradesh ─────────────────────────────────
    "Agra": "https://www.freejobalert.com/search-jobs/jobs-in-agra/",
    "Ambedkar_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-ambedkar-nagar/",
    "Baghpat": "https://www.freejobalert.com/search-jobs/jobs-in-baghpat/",
    "Balrampur": "https://www.freejobalert.com/search-jobs/jobs-in-balrampur/",
    "Bareilly": "https://www.freejobalert.com/search-jobs/jobs-in-bareilly/",
    "Budaun": "https://www.freejobalert.com/search-jobs/jobs-in-budaun/",
    "Chitrakoot": "https://www.freejobalert.com/search-jobs/jobs-in-chitrakoot/",
    "Etawah": "https://www.freejobalert.com/search-jobs/jobs-in-etawah/",
    "Fatehpur": "https://www.freejobalert.com/search-jobs/jobs-in-fatehpur/",
    "Ghaziabad": "https://www.freejobalert.com/search-jobs/jobs-in-ghaziabad/",
    "Gorakhpur": "https://www.freejobalert.com/search-jobs/jobs-in-gorakhpur/",
    "Hathras": "https://www.freejobalert.com/search-jobs/jobs-in-hathras/",
    "Jhansi": "https://www.freejobalert.com/search-jobs/jobs-in-jhansi/",
    "Kanpur": "https://www.freejobalert.com/search-jobs/jobs-in-kanpur/",
    "Kheri": "https://www.freejobalert.com/search-jobs/jobs-in-kheri/",
    "Lucknow": "https://www.freejobalert.com/search-jobs/jobs-in-lucknow/",
    "Mahoba": "https://www.freejobalert.com/search-jobs/jobs-in-mahoba/",
    "Mau": "https://www.freejobalert.com/search-jobs/jobs-in-mau/",
    "Moradabad": "https://www.freejobalert.com/search-jobs/jobs-in-moradabad/",
    "Pilibhit": "https://www.freejobalert.com/search-jobs/jobs-in-pilibhit/",
    "Ramabai_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-ramabai-nagar/",
    "Sant_Kabir_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-sant-kabir-nagar/",
    "Shrawasti": "https://www.freejobalert.com/search-jobs/jobs-in-shrawasti/",
    "Sonbhadra": "https://www.freejobalert.com/search-jobs/jobs-in-sonbhadra/",
    "Varanasi": "https://www.freejobalert.com/search-jobs/jobs-in-varanasi-banaras/",
    "Aligarh": "https://www.freejobalert.com/search-jobs/jobs-in-aligarh/",
    "Auraiya": "https://www.freejobalert.com/search-jobs/jobs-in-auraiya/",
    "Bahraich": "https://www.freejobalert.com/search-jobs/jobs-in-bahraich/",
    "Banda": "https://www.freejobalert.com/search-jobs/jobs-in-banda/",
    "Basti": "https://www.freejobalert.com/search-jobs/jobs-in-basti/",
    "Bulandshahar": "https://www.freejobalert.com/search-jobs/jobs-in-bulandshahar/",
    "Deoria": "https://www.freejobalert.com/search-jobs/jobs-in-deoria/",
    "Faizabad": "https://www.freejobalert.com/search-jobs/jobs-in-faizabad/",
    "Firozabad": "https://www.freejobalert.com/search-jobs/jobs-in-firozabad/",
    "Ghazipur": "https://www.freejobalert.com/search-jobs/jobs-in-ghazipur/",
    "Hamirpur_Uttar_Pradesh": "https://www.freejobalert.com/search-jobs/jobs-in-hamirpur-uttar-pradesh/",
    "Jalaun": "https://www.freejobalert.com/search-jobs/jobs-in-jalaun/",
    "Jyotiba_Phule_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-jyotiba-phule-nagar/",
    "Kanshiram_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-kanshiram-nagar/",
    "Kushinagar": "https://www.freejobalert.com/search-jobs/jobs-in-kushinagar/",
    "Mahamaya_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-mahamaya-nagar/",
    "Mainpuri": "https://www.freejobalert.com/search-jobs/jobs-in-mainpuri/",
    "Meerut": "https://www.freejobalert.com/search-jobs/jobs-in-meerut/",
    "Muzaffarnagar": "https://www.freejobalert.com/search-jobs/jobs-in-muzaffarnagar/",
    "Pratapgarh": "https://www.freejobalert.com/search-jobs/jobs-in-pratapgarh/",
    "Rampur": "https://www.freejobalert.com/search-jobs/jobs-in-rampur/",
    "Sant_Ravidas_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-sant-ravidas-nagar/",
    "Siddharth_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-siddharth-nagar/",
    "Sultanpur": "https://www.freejobalert.com/search-jobs/jobs-in-sultanpur/",
    "Allahabad": "https://www.freejobalert.com/search-jobs/jobs-in-allahabad/",
    "Azamgarh": "https://www.freejobalert.com/search-jobs/jobs-in-azamgarh/",
    "Ballia": "https://www.freejobalert.com/search-jobs/jobs-in-ballia/",
    "Barabanki": "https://www.freejobalert.com/search-jobs/jobs-in-barabanki/",
    "Bijnor": "https://www.freejobalert.com/search-jobs/jobs-in-bijnor/",
    "Chandauli": "https://www.freejobalert.com/search-jobs/jobs-in-chandauli/",
    "Etah": "https://www.freejobalert.com/search-jobs/jobs-in-etah/",
    "Farrukhabad": "https://www.freejobalert.com/search-jobs/jobs-in-farrukhabad/",
    "Gautam_Buddha_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-gautam-buddha-nagar/",
    "Gonda": "https://www.freejobalert.com/search-jobs/jobs-in-gonda/",
    "Hardoi": "https://www.freejobalert.com/search-jobs/jobs-in-hardoi/",
    "Jaunpur": "https://www.freejobalert.com/search-jobs/jobs-in-jaunpur/",
    "Kannauj": "https://www.freejobalert.com/search-jobs/jobs-in-kannauj/",
    "Kaushambi": "https://www.freejobalert.com/search-jobs/jobs-in-kaushambi/",
    "Lalitpur": "https://www.freejobalert.com/search-jobs/jobs-in-lalitpur/",
    "Maharajganj": "https://www.freejobalert.com/search-jobs/jobs-in-maharajganj/",
    "Mathura": "https://www.freejobalert.com/search-jobs/jobs-in-mathura/",
    "Mirzapur": "https://www.freejobalert.com/search-jobs/jobs-in-mirzapur/",
    "Noida": "https://www.freejobalert.com/search-jobs/jobs-in-noida-greater-noida/",
    "Rae_Bareli": "https://www.freejobalert.com/search-jobs/jobs-in-rae-bareli/",
    "Saharanpur": "https://www.freejobalert.com/search-jobs/jobs-in-saharanpur/",
    "Shahjahanpur": "https://www.freejobalert.com/search-jobs/jobs-in-shahjahanpur/",
    "Sitapur": "https://www.freejobalert.com/search-jobs/jobs-in-sitapur/",
    "Unnao": "https://www.freejobalert.com/search-jobs/jobs-in-unnao/",
    # ── Uttarakhand ─────────────────────────────────
    "Almora": "https://www.freejobalert.com/search-jobs/jobs-in-almora/",
    "Champawat": "https://www.freejobalert.com/search-jobs/jobs-in-champawat/",
    "Haridwar": "https://www.freejobalert.com/search-jobs/jobs-in-haridwar/",
    "Pithoragarh": "https://www.freejobalert.com/search-jobs/jobs-in-pithoragarh/",
    "Rudrapur": "https://www.freejobalert.com/search-jobs/jobs-in-rudrapur/",
    "Udham_Singh_Nagar": "https://www.freejobalert.com/search-jobs/jobs-in-udham-singh-nagar/",
    "Bageshwar": "https://www.freejobalert.com/search-jobs/jobs-in-bageshwar/",
    "Dehradun": "https://www.freejobalert.com/search-jobs/jobs-in-dehradun/",
    "Nainital": "https://www.freejobalert.com/search-jobs/jobs-in-nainital/",
    "Roorkee": "https://www.freejobalert.com/search-jobs/jobs-in-roorkee/",
    "Srinagar_Garhwal": "https://www.freejobalert.com/search-jobs/jobs-in-srinagar-garhwal/",
    "Chamoli": "https://www.freejobalert.com/search-jobs/jobs-in-chamoli/",
    "Haldwani": "https://www.freejobalert.com/search-jobs/jobs-in-haldwani/",
    "Pauri_Garhwal": "https://www.freejobalert.com/search-jobs/jobs-in-pauri-garhwal/",
    "Rudraprayag": "https://www.freejobalert.com/search-jobs/jobs-in-rudraprayag/",
    "Tehri_Garhwal": "https://www.freejobalert.com/search-jobs/jobs-in-tehri-garhwal/",
    # ── West Bengal ─────────────────────────────────
    "Alipurduar": "https://www.freejobalert.com/search-jobs/jobs-in-alipurduar/",
    "Barddhaman": "https://www.freejobalert.com/search-jobs/jobs-in-barddhaman/",
    "Dakshin_Dinajpur": "https://www.freejobalert.com/search-jobs/jobs-in-dakshin-dinajpur/",
    "Haldia": "https://www.freejobalert.com/search-jobs/jobs-in-haldia/",
    "Jalpaiguri": "https://www.freejobalert.com/search-jobs/jobs-in-jalpaiguri/",
    "Koch_Bihar": "https://www.freejobalert.com/search-jobs/jobs-in-koch-bihar/",
    "Midnapur": "https://www.freejobalert.com/search-jobs/jobs-in-midnapur/",
    "North_Twenty_Four_Parganas": "https://www.freejobalert.com/search-jobs/jobs-in-north-twenty-four-parganas/",
    "Puruliya": "https://www.freejobalert.com/search-jobs/jobs-in-puruliya/",
    "South_Twenty_Four_Parganas": "https://www.freejobalert.com/search-jobs/jobs-in-south-twenty-four-parganas/",
    "Asansol": "https://www.freejobalert.com/search-jobs/jobs-in-asansol/",
    "Birbhum": "https://www.freejobalert.com/search-jobs/jobs-in-birbhum/",
    "Darjiling": "https://www.freejobalert.com/search-jobs/jobs-in-darjiling/",
    "Howrah": "https://www.freejobalert.com/search-jobs/jobs-in-haora-howrah/",
    "Jhargram": "https://www.freejobalert.com/search-jobs/jobs-in-jhargram/",
    "Kolkata": "https://www.freejobalert.com/search-jobs/jobs-in-kolkata/",
    "Murshidabad": "https://www.freejobalert.com/search-jobs/jobs-in-murshidabad/",
    "Paschim_Medinipur": "https://www.freejobalert.com/search-jobs/jobs-in-paschim-medinipur/",
    "Raniganj": "https://www.freejobalert.com/search-jobs/jobs-in-raniganj/",
    "Bankura": "https://www.freejobalert.com/search-jobs/jobs-in-bankura/",
    "Burdwan": "https://www.freejobalert.com/search-jobs/jobs-in-burdwan/",
    "Durgapur": "https://www.freejobalert.com/search-jobs/jobs-in-durgapur/",
    "Hugli": "https://www.freejobalert.com/search-jobs/jobs-in-hugli/",
    "Kharagpur": "https://www.freejobalert.com/search-jobs/jobs-in-kharagpur/",
    "Malda": "https://www.freejobalert.com/search-jobs/jobs-in-malda/",
    "Nadia": "https://www.freejobalert.com/search-jobs/jobs-in-nadia/",
    "Purba_Medinipur": "https://www.freejobalert.com/search-jobs/jobs-in-purba-medinipur/",
    "Siliguri": "https://www.freejobalert.com/search-jobs/jobs-in-siliguri/",
}

# ── District Metadata ─────────────────────────────────────────
# Category-key -> {state, district} mapping, taaki job["basic_details"]
# ["job_location"] aur job["district_meta"] mein use ho sake.
DISTRICT_META = {
    "Ambala": {"state": "Haryana", "district": "Ambala"},
    "Fatehabad": {"state": "Haryana", "district": "Fatehabad"},
    "Jhajjar": {"state": "Haryana", "district": "Jhajjar"},
    "Karnal": {"state": "Haryana", "district": "Karnal"},
    "Mewat": {"state": "Haryana", "district": "Mewat"},
    "Panchkula": {"state": "Haryana", "district": "Panchkula"},
    "Rohtak": {"state": "Haryana", "district": "Rohtak"},
    "Yamunanagar": {"state": "Haryana", "district": "Yamunanagar"},
    "Bhiwani": {"state": "Haryana", "district": "Bhiwani"},
    "Gurgaon": {"state": "Haryana", "district": "Gurgaon"},
    "Jind": {"state": "Haryana", "district": "Jind"},
    "Kurukshetra": {"state": "Haryana", "district": "Kurukshetra"},
    "Narnaul": {"state": "Haryana", "district": "Narnaul"},
    "Panipat": {"state": "Haryana", "district": "Panipat"},
    "Sirsa": {"state": "Haryana", "district": "Sirsa"},
    "Faridabad": {"state": "Haryana", "district": "Faridabad"},
    "Hissar": {"state": "Haryana", "district": "Hissar"},
    "Kaithal": {"state": "Haryana", "district": "Kaithal"},
    "Mahendergarh": {"state": "Haryana", "district": "Mahendergarh"},
    "Palwal": {"state": "Haryana", "district": "Palwal"},
    "Rewari": {"state": "Haryana", "district": "Rewari"},
    "Sonepat": {"state": "Haryana", "district": "Sonepat"},
    "Anantapur": {"state": "Andhra Pradesh", "district": "Anantapur"},
    "East_Godavari": {"state": "Andhra Pradesh", "district": "East Godavari"},
    "Kakinada": {"state": "Andhra Pradesh", "district": "Kakinada"},
    "Machilipatnam": {"state": "Andhra Pradesh", "district": "Machilipatnam"},
    "Prakasam": {"state": "Andhra Pradesh", "district": "Prakasam"},
    "Srikakulam": {"state": "Andhra Pradesh", "district": "Srikakulam"},
    "Visakhapatnam": {"state": "Andhra Pradesh", "district": "Visakhapatnam"},
    "Chittoor": {"state": "Andhra Pradesh", "district": "Chittoor"},
    "Guntakal": {"state": "Andhra Pradesh", "district": "Guntakal"},
    "Krishna": {"state": "Andhra Pradesh", "district": "Krishna"},
    "Nandyal": {"state": "Andhra Pradesh", "district": "Nandyal"},
    "Purbam_Medinipur": {"state": "Andhra Pradesh", "district": "Purbam Medinipur"},
    "Tirupati": {"state": "Andhra Pradesh", "district": "Tirupati"},
    "Vizianagaram": {"state": "Andhra Pradesh", "district": "Vizianagaram"},
    "Cuddapah": {"state": "Andhra Pradesh", "district": "Cuddapah"},
    "Guntur": {"state": "Andhra Pradesh", "district": "Guntur"},
    "Kurnool": {"state": "Andhra Pradesh", "district": "Kurnool"},
    "Nellore": {"state": "Andhra Pradesh", "district": "Nellore"},
    "Rajahmundry": {"state": "Andhra Pradesh", "district": "Rajahmundry"},
    "Vijayawada": {"state": "Andhra Pradesh", "district": "Vijayawada"},
    "West_Godavari": {"state": "Andhra Pradesh", "district": "West Godavari"},
    "Aalo": {"state": "Arunachal Pradesh", "district": "Aalo"},
    "Basar": {"state": "Arunachal Pradesh", "district": "Basar"},
    "Bomdila": {"state": "Arunachal Pradesh", "district": "Bomdila"},
    "Chowkham": {"state": "Arunachal Pradesh", "district": "Chowkham"},
    "Deomali": {"state": "Arunachal Pradesh", "district": "Deomali"},
    "East_Siang": {"state": "Arunachal Pradesh", "district": "East Siang"},
    "Itanagar": {"state": "Arunachal Pradesh", "district": "Itanagar"},
    "Khonsa": {"state": "Arunachal Pradesh", "district": "Khonsa"},
    "Lumla": {"state": "Arunachal Pradesh", "district": "Lumla"},
    "Namsang": {"state": "Arunachal Pradesh", "district": "Namsang"},
    "Pasighat": {"state": "Arunachal Pradesh", "district": "Pasighat"},
    "Sagalee": {"state": "Arunachal Pradesh", "district": "Sagalee"},
    "Tawang": {"state": "Arunachal Pradesh", "district": "Tawang"},
    "Tirap": {"state": "Arunachal Pradesh", "district": "Tirap"},
    "Yingkiong": {"state": "Arunachal Pradesh", "district": "Yingkiong"},
    "Doimukh": {"state": "Arunachal Pradesh", "district": "Doimukh"},
    "Gandhigram": {"state": "Arunachal Pradesh", "district": "Gandhigram"},
    "Jairampur": {"state": "Arunachal Pradesh", "district": "Jairampur"},
    "Liromoba": {"state": "Arunachal Pradesh", "district": "Liromoba"},
    "Naharlagun": {"state": "Arunachal Pradesh", "district": "Naharlagun"},
    "Nyapin": {"state": "Arunachal Pradesh", "district": "Nyapin"},
    "Roing": {"state": "Arunachal Pradesh", "district": "Roing"},
    "Seppa": {"state": "Arunachal Pradesh", "district": "Seppa"},
    "Tezu": {"state": "Arunachal Pradesh", "district": "Tezu"},
    "Tuting": {"state": "Arunachal Pradesh", "district": "Tuting"},
    "Yupia": {"state": "Arunachal Pradesh", "district": "Yupia"},
    "Dumporijo": {"state": "Arunachal Pradesh", "district": "Dumporijo"},
    "Hawai": {"state": "Arunachal Pradesh", "district": "Hawai"},
    "Kanubari": {"state": "Arunachal Pradesh", "district": "Kanubari"},
    "Longding": {"state": "Arunachal Pradesh", "district": "Longding"},
    "Namsai": {"state": "Arunachal Pradesh", "district": "Namsai"},
    "Pangin": {"state": "Arunachal Pradesh", "district": "Pangin"},
    "Ruksin": {"state": "Arunachal Pradesh", "district": "Ruksin"},
    "Taliha": {"state": "Arunachal Pradesh", "district": "Taliha"},
    "Tinsukia_Assam": {"state": "Arunachal Pradesh", "district": "Tinsukia Assam"},
    "Vijaynagar": {"state": "Arunachal Pradesh", "district": "Vijaynagar"},
    "Ziro": {"state": "Arunachal Pradesh", "district": "Ziro"},
    "Baksa": {"state": "Assam", "district": "Baksa"},
    "Bongaigaon": {"state": "Assam", "district": "Bongaigaon"},
    "Darrang": {"state": "Assam", "district": "Darrang"},
    "Dibrugarh": {"state": "Assam", "district": "Dibrugarh"},
    "Goalpara": {"state": "Assam", "district": "Goalpara"},
    "Hailakandi": {"state": "Assam", "district": "Hailakandi"},
    "Kamrup": {"state": "Assam", "district": "Kamrup"},
    "Kokrajhar": {"state": "Assam", "district": "Kokrajhar"},
    "Nagaon": {"state": "Assam", "district": "Nagaon"},
    "Silchar": {"state": "Assam", "district": "Silchar"},
    "Tezpur": {"state": "Assam", "district": "Tezpur"},
    "Barpeta": {"state": "Assam", "district": "Barpeta"},
    "Cachar": {"state": "Assam", "district": "Cachar"},
    "Dhemaji": {"state": "Assam", "district": "Dhemaji"},
    "Dima_Hasao": {"state": "Assam", "district": "Dima Hasao"},
    "Golaghat": {"state": "Assam", "district": "Golaghat"},
    "Hojai": {"state": "Assam", "district": "Hojai"},
    "Karbi_Anglong": {"state": "Assam", "district": "Karbi Anglong"},
    "Lakhimpur": {"state": "Assam", "district": "Lakhimpur"},
    "Nalbari": {"state": "Assam", "district": "Nalbari"},
    "Sivasagar": {"state": "Assam", "district": "Sivasagar"},
    "Tinsukia": {"state": "Assam", "district": "Tinsukia"},
    "Biswanath": {"state": "Assam", "district": "Biswanath"},
    "Chirang": {"state": "Assam", "district": "Chirang"},
    "Dhubri": {"state": "Assam", "district": "Dhubri"},
    "Dispur": {"state": "Assam", "district": "Dispur"},
    "Guwahati": {"state": "Assam", "district": "Guwahati"},
    "Jorhat": {"state": "Assam", "district": "Jorhat"},
    "Karimganj": {"state": "Assam", "district": "Karimganj"},
    "Morigaon": {"state": "Assam", "district": "Morigaon"},
    "Sibsagar": {"state": "Assam", "district": "Sibsagar"},
    "Sonitpur": {"state": "Assam", "district": "Sonitpur"},
    "Udalguri": {"state": "Assam", "district": "Udalguri"},
    "Araria": {"state": "Bihar", "district": "Araria"},
    "Banka": {"state": "Bihar", "district": "Banka"},
    "Bhojpur": {"state": "Bihar", "district": "Bhojpur"},
    "Gaya": {"state": "Bihar", "district": "Gaya"},
    "Jehanabad": {"state": "Bihar", "district": "Jehanabad"},
    "Khagaria": {"state": "Bihar", "district": "Khagaria"},
    "Madhepura": {"state": "Bihar", "district": "Madhepura"},
    "Muzaffarpur": {"state": "Bihar", "district": "Muzaffarpur"},
    "Pashchim_Champaran": {"state": "Bihar", "district": "Pashchim Champaran"},
    "Purnia": {"state": "Bihar", "district": "Purnia"},
    "Samastipur": {"state": "Bihar", "district": "Samastipur"},
    "Arwal": {"state": "Bihar", "district": "Arwal"},
    "Begusarai": {"state": "Bihar", "district": "Begusarai"},
    "Buxar": {"state": "Bihar", "district": "Buxar"},
    "Gopalganj": {"state": "Bihar", "district": "Gopalganj"},
    "Kaimur": {"state": "Bihar", "district": "Kaimur"},
    "Kishanganj": {"state": "Bihar", "district": "Kishanganj"},
    "Madhubani": {"state": "Bihar", "district": "Madhubani"},
    "Nalanda": {"state": "Bihar", "district": "Nalanda"},
    "Patna": {"state": "Bihar", "district": "Patna"},
    "Rohtas": {"state": "Bihar", "district": "Rohtas"},
    "Saran": {"state": "Bihar", "district": "Saran"},
    "Aurangabad_Bihar": {"state": "Bihar", "district": "Aurangabad Bihar"},
    "Bhagalpur": {"state": "Bihar", "district": "Bhagalpur"},
    "Darbhanga": {"state": "Bihar", "district": "Darbhanga"},
    "Jamui": {"state": "Bihar", "district": "Jamui"},
    "Katihar": {"state": "Bihar", "district": "Katihar"},
    "Lakhisarai": {"state": "Bihar", "district": "Lakhisarai"},
    "Munger": {"state": "Bihar", "district": "Munger"},
    "Nawada": {"state": "Bihar", "district": "Nawada"},
    "Purbi_Champaran": {"state": "Bihar", "district": "Purbi Champaran"},
    "Saharsa": {"state": "Bihar", "district": "Saharsa"},
    "Sheikhpura": {"state": "Bihar", "district": "Sheikhpura"},
    "Bastar": {"state": "Chhattisgarh", "district": "Bastar"},
    "Bijapur": {"state": "Chhattisgarh", "district": "Bijapur"},
    "Dhamtari": {"state": "Chhattisgarh", "district": "Dhamtari"},
    "Janjgir_Champa": {"state": "Chhattisgarh", "district": "Janjgir Champa"},
    "Kanker": {"state": "Chhattisgarh", "district": "Kanker"},
    "Mahasamund": {"state": "Chhattisgarh", "district": "Mahasamund"},
    "Raipur": {"state": "Chhattisgarh", "district": "Raipur"},
    "Surguja": {"state": "Chhattisgarh", "district": "Surguja"},
    "Bemetara": {"state": "Chhattisgarh", "district": "Bemetara"},
    "Bilaspur_Chhattisgarh": {"state": "Chhattisgarh", "district": "Bilaspur Chhattisgarh"},
    "Durg": {"state": "Chhattisgarh", "district": "Durg"},
    "Jashpur": {"state": "Chhattisgarh", "district": "Jashpur"},
    "Korba": {"state": "Chhattisgarh", "district": "Korba"},
    "Narayanpur": {"state": "Chhattisgarh", "district": "Narayanpur"},
    "Rajnandgaon": {"state": "Chhattisgarh", "district": "Rajnandgaon"},
    "Bhilai_Durg": {"state": "Chhattisgarh", "district": "Bhilai-Durg"},
    "Dantewada": {"state": "Chhattisgarh", "district": "Dantewada"},
    "Gariaband": {"state": "Chhattisgarh", "district": "Gariaband"},
    "Kabirdham": {"state": "Chhattisgarh", "district": "Kabirdham"},
    "Korea": {"state": "Chhattisgarh", "district": "Korea"},
    "Raigarh_Chhattisgarh": {"state": "Chhattisgarh", "district": "Raigarh Chhattisgarh"},
    "Surajpur": {"state": "Chhattisgarh", "district": "Surajpur"},
    "Alwar_Delhi": {"state": "Delhi", "district": "Alwar Delhi"},
    "Bahadurgarh": {"state": "Delhi", "district": "Bahadurgarh"},
    "Ballabgarh": {"state": "Delhi", "district": "Ballabgarh"},
    "Bhiwadi": {"state": "Delhi", "district": "Bhiwadi"},
    "Bhiwani_Delhi": {"state": "Delhi", "district": "Bhiwani Delhi"},
    "Faridabad_Delhi": {"state": "Delhi", "district": "Faridabad Delhi"},
    "Ghaziabad_Delhi": {"state": "Delhi", "district": "Ghaziabad Delhi"},
    "Gurgaon_Delhi": {"state": "Delhi", "district": "Gurgaon Delhi"},
    "Kundli_CharkhiDadri": {"state": "Delhi", "district": "Kundli CharkhiDadri"},
    "Loni": {"state": "Delhi", "district": "Loni"},
    "Manesar": {"state": "Delhi", "district": "Manesar"},
    "New_Delhi": {"state": "Delhi", "district": "New Delhi"},
    "Noida_Delhi": {"state": "Delhi", "district": "Noida Delhi"},
    "Sonepat_Delhi": {"state": "Delhi", "district": "Sonepat Delhi"},
    "North_Goa": {"state": "Goa", "district": "North Goa"},
    "Panaji": {"state": "Goa", "district": "Panaji"},
    "South_Goa": {"state": "Goa", "district": "South Goa"},
    "Vasco_Da_Gama": {"state": "Goa", "district": "Vasco Da Gama"},
    "Bhuj": {"state": "Gujarat", "district": "Bhuj"},
    "Gandhinagar": {"state": "Gujarat", "district": "Gandhinagar"},
    "Junagadh": {"state": "Gujarat", "district": "Junagadh"},
    "Kandla": {"state": "Gujarat", "district": "Kandla"},
    "Narmada": {"state": "Gujarat", "district": "Narmada"},
    "Patan": {"state": "Gujarat", "district": "Patan"},
    "Sabarkantha": {"state": "Gujarat", "district": "Sabarkantha"},
    "Tapi": {"state": "Gujarat", "district": "Tapi"},
    "Valsad_Vapi": {"state": "Gujarat", "district": "Valsad-Vapi"},
    "Dohad": {"state": "Gujarat", "district": "Dohad"},
    "Gir": {"state": "Gujarat", "district": "Gir"},
    "Junagarh": {"state": "Gujarat", "district": "Junagarh"},
    "Mehsana": {"state": "Gujarat", "district": "Mehsana"},
    "Navsari": {"state": "Gujarat", "district": "Navsari"},
    "Porbandar": {"state": "Gujarat", "district": "Porbandar"},
    "Surat": {"state": "Gujarat", "district": "Surat"},
    "The_Dangs": {"state": "Gujarat", "district": "The Dangs"},
    "Gandhidham": {"state": "Gujarat", "district": "Gandhidham"},
    "Jamnagar": {"state": "Gujarat", "district": "Jamnagar"},
    "Kachchh": {"state": "Gujarat", "district": "Kachchh"},
    "Morbi": {"state": "Gujarat", "district": "Morbi"},
    "PanchMahal": {"state": "Gujarat", "district": "PanchMahal"},
    "Rajkot": {"state": "Gujarat", "district": "Rajkot"},
    "Surendranagar": {"state": "Gujarat", "district": "Surendranagar"},
    "Vadodara": {"state": "Gujarat", "district": "Vadodara"},
    "Baddi": {"state": "Himachal Pradesh", "district": "Baddi"},
    "Dalhousie": {"state": "Himachal Pradesh", "district": "Dalhousie"},
    "Kangra": {"state": "Himachal Pradesh", "district": "Kangra"},
    "Kullu": {"state": "Himachal Pradesh", "district": "Kullu"},
    "Mandi": {"state": "Himachal Pradesh", "district": "Mandi"},
    "Shimla": {"state": "Himachal Pradesh", "district": "Shimla"},
    "Bilaspur": {"state": "Himachal Pradesh", "district": "Bilaspur"},
    "Dharamshala": {"state": "Himachal Pradesh", "district": "Dharamshala"},
    "Kasauli": {"state": "Himachal Pradesh", "district": "Kasauli"},
    "Lahaul_Spiti": {"state": "Himachal Pradesh", "district": "Lahaul & Spiti"},
    "Nalagarh": {"state": "Himachal Pradesh", "district": "Nalagarh"},
    "sirmaur": {"state": "Himachal Pradesh", "district": "sirmaur"},
    "Chamba": {"state": "Himachal Pradesh", "district": "Chamba"},
    "Hamirpur": {"state": "Himachal Pradesh", "district": "Hamirpur"},
    "Kinnaur": {"state": "Himachal Pradesh", "district": "Kinnaur"},
    "Manali": {"state": "Himachal Pradesh", "district": "Manali"},
    "Parwanoo": {"state": "Himachal Pradesh", "district": "Parwanoo"},
    "Solan": {"state": "Himachal Pradesh", "district": "Solan"},
    "Anantnag": {"state": "Jammu and Kashmir", "district": "Anantnag"},
    "Bandipora": {"state": "Jammu and Kashmir", "district": "Bandipora"},
    "Baramulla": {"state": "Jammu and Kashmir", "district": "Baramulla"},
    "Budgam": {"state": "Jammu and Kashmir", "district": "Budgam"},
    "Doda": {"state": "Jammu and Kashmir", "district": "Doda"},
    "Ganderbal": {"state": "Jammu and Kashmir", "district": "Ganderbal"},
    "Jammu": {"state": "Jammu and Kashmir", "district": "Jammu"},
    "Kargil": {"state": "Jammu and Kashmir", "district": "Kargil"},
    "Kathua": {"state": "Jammu and Kashmir", "district": "Kathua"},
    "Kishtwar": {"state": "Jammu and Kashmir", "district": "Kishtwar"},
    "Kulgam": {"state": "Jammu and Kashmir", "district": "Kulgam"},
    "Kupwara": {"state": "Jammu and Kashmir", "district": "Kupwara"},
    "Leh": {"state": "Jammu and Kashmir", "district": "Leh"},
    "Poonch": {"state": "Jammu and Kashmir", "district": "Poonch"},
    "Pulwama": {"state": "Jammu and Kashmir", "district": "Pulwama"},
    "Punch": {"state": "Jammu and Kashmir", "district": "Punch"},
    "Rajouri": {"state": "Jammu and Kashmir", "district": "Rajouri"},
    "Ramban": {"state": "Jammu and Kashmir", "district": "Ramban"},
    "Reasi": {"state": "Jammu and Kashmir", "district": "Reasi"},
    "Samba": {"state": "Jammu and Kashmir", "district": "Samba"},
    "Shupiyan": {"state": "Jammu and Kashmir", "district": "Shupiyan"},
    "Srinagar": {"state": "Jammu and Kashmir", "district": "Srinagar"},
    "Udhampur": {"state": "Jammu and Kashmir", "district": "Udhampur"},
    "Bokaro": {"state": "Jharkhand", "district": "Bokaro"},
    "Dhanbad": {"state": "Jharkhand", "district": "Dhanbad"},
    "Giridih": {"state": "Jharkhand", "district": "Giridih"},
    "Hazaribagh": {"state": "Jharkhand", "district": "Hazaribagh"},
    "Khunti": {"state": "Jharkhand", "district": "Khunti"},
    "Latehar": {"state": "Jharkhand", "district": "Latehar"},
    "Palamu": {"state": "Jharkhand", "district": "Palamu"},
    "Ramgarh": {"state": "Jharkhand", "district": "Ramgarh"},
    "Saraikela_Kharsawan": {"state": "Jharkhand", "district": "Saraikela Kharsawan"},
    "Chatra": {"state": "Jharkhand", "district": "Chatra"},
    "Dumka": {"state": "Jharkhand", "district": "Dumka"},
    "Godda": {"state": "Jharkhand", "district": "Godda"},
    "Jamshedpur": {"state": "Jharkhand", "district": "Jamshedpur"},
    "Kodarma": {"state": "Jharkhand", "district": "Kodarma"},
    "Lohardaga": {"state": "Jharkhand", "district": "Lohardaga"},
    "Pashchimi_Singhbhum": {"state": "Jharkhand", "district": "Pashchimi Singhbhum"},
    "Ranchi": {"state": "Jharkhand", "district": "Ranchi"},
    "Deoghar": {"state": "Jharkhand", "district": "Deoghar"},
    "Garhwa": {"state": "Jharkhand", "district": "Garhwa"},
    "Gumla": {"state": "Jharkhand", "district": "Gumla"},
    "Jamtara": {"state": "Jharkhand", "district": "Jamtara"},
    "Koderma": {"state": "Jharkhand", "district": "Koderma"},
    "Pakur": {"state": "Jharkhand", "district": "Pakur"},
    "Purbi_Singhbhum": {"state": "Jharkhand", "district": "Purbi Singhbhum"},
    "Sahibganj": {"state": "Jharkhand", "district": "Sahibganj"},
    "Bagalkot": {"state": "Karnataka", "district": "Bagalkot"},
    "Belgaum": {"state": "Karnataka", "district": "Belgaum"},
    "Bijapur_Karnataka": {"state": "Karnataka", "district": "Bijapur Karnataka"},
    "Chikmagalur": {"state": "Karnataka", "district": "Chikmagalur"},
    "Davanagere": {"state": "Karnataka", "district": "Davanagere"},
    "Gulbarga": {"state": "Karnataka", "district": "Gulbarga"},
    "Hubli": {"state": "Karnataka", "district": "Hubli"},
    "Koppal": {"state": "Karnataka", "district": "Koppal"},
    "Mysore": {"state": "Karnataka", "district": "Mysore"},
    "Shimoga": {"state": "Karnataka", "district": "Shimoga"},
    "Uttara_Kannada": {"state": "Karnataka", "district": "Uttara Kannada"},
    "Bangalore": {"state": "Karnataka", "district": "Bangalore"},
    "Bellary": {"state": "Karnataka", "district": "Bellary"},
    "Chamarajanagar": {"state": "Karnataka", "district": "Chamarajanagar"},
    "Chitradurga": {"state": "Karnataka", "district": "Chitradurga"},
    "Dharwad": {"state": "Karnataka", "district": "Dharwad"},
    "Hassan": {"state": "Karnataka", "district": "Hassan"},
    "Kodagu": {"state": "Karnataka", "district": "Kodagu"},
    "Mandya": {"state": "Karnataka", "district": "Mandya"},
    "Raichur": {"state": "Karnataka", "district": "Raichur"},
    "Tumkur": {"state": "Karnataka", "district": "Tumkur"},
    "Vijaya_Nagara": {"state": "Karnataka", "district": "Vijaya Nagara"},
    "Chikkaballapura": {"state": "Karnataka", "district": "Chikkaballapura"},
    "Dakshina_Kannada": {"state": "Karnataka", "district": "Dakshina Kannada"},
    "Gadag": {"state": "Karnataka", "district": "Gadag"},
    "Haveri": {"state": "Karnataka", "district": "Haveri"},
    "Kolar": {"state": "Karnataka", "district": "Kolar"},
    "Mangalore": {"state": "Karnataka", "district": "Mangalore"},
    "Ramanagara": {"state": "Karnataka", "district": "Ramanagara"},
    "Udupi": {"state": "Karnataka", "district": "Udupi"},
    "Alappuzha": {"state": "Kerala", "district": "Alappuzha"},
    "Idukki": {"state": "Kerala", "district": "Idukki"},
    "Kannur": {"state": "Kerala", "district": "Kannur"},
    "Kasaragod": {"state": "Kerala", "district": "Kasaragod"},
    "Kochi": {"state": "Kerala", "district": "Kochi"},
    "Kollam": {"state": "Kerala", "district": "Kollam"},
    "Kottayam": {"state": "Kerala", "district": "Kottayam"},
    "Kozhikode": {"state": "Kerala", "district": "Kozhikode"},
    "Malappuram": {"state": "Kerala", "district": "Malappuram"},
    "Palakkad": {"state": "Kerala", "district": "Palakkad"},
    "Pathanamthitta": {"state": "Kerala", "district": "Pathanamthitta"},
    "Thiruvananthapuram": {"state": "Kerala", "district": "Thiruvananthapuram"},
    "Thrissur": {"state": "Kerala", "district": "Thrissur"},
    "Wayanad": {"state": "Kerala", "district": "Wayanad"},
    "Alirajpur": {"state": "Madhya Pradesh", "district": "Alirajpur"},
    "Balaghat": {"state": "Madhya Pradesh", "district": "Balaghat"},
    "Bhind": {"state": "Madhya Pradesh", "district": "Bhind"},
    "Chhattarpur": {"state": "Madhya Pradesh", "district": "Chhattarpur"},
    "Datia": {"state": "Madhya Pradesh", "district": "Datia"},
    "Dindori": {"state": "Madhya Pradesh", "district": "Dindori"},
    "Gwalior": {"state": "Madhya Pradesh", "district": "Gwalior"},
    "Indore": {"state": "Madhya Pradesh", "district": "Indore"},
    "Katni": {"state": "Madhya Pradesh", "district": "Katni"},
    "Mandsaur": {"state": "Madhya Pradesh", "district": "Mandsaur"},
    "Neemuch": {"state": "Madhya Pradesh", "district": "Neemuch"},
    "Rajgarh": {"state": "Madhya Pradesh", "district": "Rajgarh"},
    "Sagar": {"state": "Madhya Pradesh", "district": "Sagar"},
    "Seoni": {"state": "Madhya Pradesh", "district": "Seoni"},
    "Sheopur": {"state": "Madhya Pradesh", "district": "Sheopur"},
    "Singrauli": {"state": "Madhya Pradesh", "district": "Singrauli"},
    "Ujjain": {"state": "Madhya Pradesh", "district": "Ujjain"},
    "Morena": {"state": "Madhya Pradesh", "district": "Morena"},
    "Panna": {"state": "Madhya Pradesh", "district": "Panna"},
    "Ratlam": {"state": "Madhya Pradesh", "district": "Ratlam"},
    "Satna": {"state": "Madhya Pradesh", "district": "Satna"},
    "Shahdol": {"state": "Madhya Pradesh", "district": "Shahdol"},
    "Shivpuri": {"state": "Madhya Pradesh", "district": "Shivpuri"},
    "Tikamgarh": {"state": "Madhya Pradesh", "district": "Tikamgarh"},
    "Umaria": {"state": "Madhya Pradesh", "district": "Umaria"},
    "Narsimhapur": {"state": "Madhya Pradesh", "district": "Narsimhapur"},
    "Raisen": {"state": "Madhya Pradesh", "district": "Raisen"},
    "Rewa": {"state": "Madhya Pradesh", "district": "Rewa"},
    "Sehore": {"state": "Madhya Pradesh", "district": "Sehore"},
    "Shajapur": {"state": "Madhya Pradesh", "district": "Shajapur"},
    "Sidhi": {"state": "Madhya Pradesh", "district": "Sidhi"},
    "Uijain": {"state": "Madhya Pradesh", "district": "Uijain"},
    "Vidisha": {"state": "Madhya Pradesh", "district": "Vidisha"},
    "Ahmednagar": {"state": "Maharashtra", "district": "Ahmednagar"},
    "Aurangabad": {"state": "Maharashtra", "district": "Aurangabad"},
    "Bid": {"state": "Maharashtra", "district": "Bid"},
    "Dhule": {"state": "Maharashtra", "district": "Dhule"},
    "Hingoli": {"state": "Maharashtra", "district": "Hingoli"},
    "Kolhapur": {"state": "Maharashtra", "district": "Kolhapur"},
    "Mahabaleshwar": {"state": "Maharashtra", "district": "Mahabaleshwar"},
    "Nagpur": {"state": "Maharashtra", "district": "Nagpur"},
    "Nasik": {"state": "Maharashtra", "district": "Nasik"},
    "Parbhani": {"state": "Maharashtra", "district": "Parbhani"},
    "Ratnagiri": {"state": "Maharashtra", "district": "Ratnagiri"},
    "Sindhudurg": {"state": "Maharashtra", "district": "Sindhudurg"},
    "Wardha": {"state": "Maharashtra", "district": "Wardha"},
    "Jalgaon": {"state": "Maharashtra", "district": "Jalgaon"},
    "Latur": {"state": "Maharashtra", "district": "Latur"},
    "Mumbai": {"state": "Maharashtra", "district": "Mumbai"},
    "Nanded": {"state": "Maharashtra", "district": "Nanded"},
    "Navi_Mumbai": {"state": "Maharashtra", "district": "Navi Mumbai"},
    "Pune": {"state": "Maharashtra", "district": "Pune"},
    "Sangli": {"state": "Maharashtra", "district": "Sangli"},
    "Solapur": {"state": "Maharashtra", "district": "Solapur"},
    "Washim": {"state": "Maharashtra", "district": "Washim"},
    "Jalna": {"state": "Maharashtra", "district": "Jalna"},
    "Lonavala": {"state": "Maharashtra", "district": "Lonavala"},
    "Mumbai_Suburban": {"state": "Maharashtra", "district": "Mumbai Suburban"},
    "Nandurbar": {"state": "Maharashtra", "district": "Nandurbar"},
    "Osmanabad": {"state": "Maharashtra", "district": "Osmanabad"},
    "Raigarh": {"state": "Maharashtra", "district": "Raigarh"},
    "Satara": {"state": "Maharashtra", "district": "Satara"},
    "Thane": {"state": "Maharashtra", "district": "Thane"},
    "Bishnupur": {"state": "Manipur", "district": "Bishnupur"},
    "Chandel": {"state": "Manipur", "district": "Chandel"},
    "Churachandpur": {"state": "Manipur", "district": "Churachandpur"},
    "Imphal": {"state": "Manipur", "district": "Imphal"},
    "Senapati": {"state": "Manipur", "district": "Senapati"},
    "Tamenglong": {"state": "Manipur", "district": "Tamenglong"},
    "Thoubal": {"state": "Manipur", "district": "Thoubal"},
    "Ukhrul": {"state": "Manipur", "district": "Ukhrul"},
    "East_Garo_Hills": {"state": "Meghalaya", "district": "East Garo Hills"},
    "East_Khasi_Hills": {"state": "Meghalaya", "district": "East Khasi Hills"},
    "Jaintia_Hills": {"state": "Meghalaya", "district": "Jaintia Hills"},
    "North_Garo_Hills": {"state": "Meghalaya", "district": "North Garo Hills"},
    "Ri_Bhoi": {"state": "Meghalaya", "district": "Ri Bhoi"},
    "Shillong": {"state": "Meghalaya", "district": "Shillong"},
    "South_Garo_Hills": {"state": "Meghalaya", "district": "South Garo Hills"},
    "West_Garo_Hills": {"state": "Meghalaya", "district": "West Garo Hills"},
    "West_Khasi_Hills": {"state": "Meghalaya", "district": "West Khasi Hills"},
    "Aizawal": {"state": "Mizoram", "district": "Aizawal"},
    "Champhai": {"state": "Mizoram", "district": "Champhai"},
    "Kolasib": {"state": "Mizoram", "district": "Kolasib"},
    "Lawngtlai": {"state": "Mizoram", "district": "Lawngtlai"},
    "Lunglei": {"state": "Mizoram", "district": "Lunglei"},
    "Mamit": {"state": "Mizoram", "district": "Mamit"},
    "Saiha": {"state": "Mizoram", "district": "Saiha"},
    "Serchhip": {"state": "Mizoram", "district": "Serchhip"},
    "Dimapur": {"state": "Nagaland", "district": "Dimapur"},
    "Kiphire": {"state": "Nagaland", "district": "Kiphire"},
    "Kohima": {"state": "Nagaland", "district": "Kohima"},
    "Longleng": {"state": "Nagaland", "district": "Longleng"},
    "Mokokchung": {"state": "Nagaland", "district": "Mokokchung"},
    "Mon": {"state": "Nagaland", "district": "Mon"},
    "Peren": {"state": "Nagaland", "district": "Peren"},
    "Phek": {"state": "Nagaland", "district": "Phek"},
    "Tuensang": {"state": "Nagaland", "district": "Tuensang"},
    "Wokha": {"state": "Nagaland", "district": "Wokha"},
    "Zunheboto": {"state": "Nagaland", "district": "Zunheboto"},
    "Anugul": {"state": "Odisha", "district": "Anugul"},
    "Balangir": {"state": "Odisha", "district": "Balangir"},
    "Baleshwar": {"state": "Odisha", "district": "Baleshwar"},
    "Bargarh": {"state": "Odisha", "district": "Bargarh"},
    "Baudh": {"state": "Odisha", "district": "Baudh"},
    "Bhadrak": {"state": "Odisha", "district": "Bhadrak"},
    "Bhubaneshwar": {"state": "Odisha", "district": "Bhubaneshwar"},
    "Cuttack": {"state": "Odisha", "district": "Cuttack"},
    "Debagarh": {"state": "Odisha", "district": "Debagarh"},
    "Dhenkanal": {"state": "Odisha", "district": "Dhenkanal"},
    "Gajapati": {"state": "Odisha", "district": "Gajapati"},
    "Ganjam": {"state": "Odisha", "district": "Ganjam"},
    "Jagatsinghapur": {"state": "Odisha", "district": "Jagatsinghapur"},
    "Jajapur": {"state": "Odisha", "district": "Jajapur"},
    "Jharsuguda": {"state": "Odisha", "district": "Jharsuguda"},
    "Kalahandi": {"state": "Odisha", "district": "Kalahandi"},
    "Kandhamal": {"state": "Odisha", "district": "Kandhamal"},
    "Kendrapara": {"state": "Odisha", "district": "Kendrapara"},
    "Kendujhar": {"state": "Odisha", "district": "Kendujhar"},
    "Khordha": {"state": "Odisha", "district": "Khordha"},
    "Koraput": {"state": "Odisha", "district": "Koraput"},
    "Malkangiri": {"state": "Odisha", "district": "Malkangiri"},
    "Mayurbhanj": {"state": "Odisha", "district": "Mayurbhanj"},
    "Nabarangapur": {"state": "Odisha", "district": "Nabarangapur"},
    "Nayagarh": {"state": "Odisha", "district": "Nayagarh"},
    "Nuapada": {"state": "Odisha", "district": "Nuapada"},
    "Paradeep": {"state": "Odisha", "district": "Paradeep"},
    "Puri": {"state": "Odisha", "district": "Puri"},
    "Rayagada": {"state": "Odisha", "district": "Rayagada"},
    "Rourkela": {"state": "Odisha", "district": "Rourkela"},
    "Sambalpur": {"state": "Odisha", "district": "Sambalpur"},
    "Subarnapur": {"state": "Odisha", "district": "Subarnapur"},
    "Sundargarh": {"state": "Odisha", "district": "Sundargarh"},
    "Amritsar": {"state": "Punjab", "district": "Amritsar"},
    "Barnala": {"state": "Punjab", "district": "Barnala"},
    "Batala": {"state": "Punjab", "district": "Batala"},
    "Bathinda": {"state": "Punjab", "district": "Bathinda"},
    "Faridkot": {"state": "Punjab", "district": "Faridkot"},
    "Fatehgarh_Sahib": {"state": "Punjab", "district": "Fatehgarh Sahib"},
    "Fazilka": {"state": "Punjab", "district": "Fazilka"},
    "Ferozepur": {"state": "Punjab", "district": "Ferozepur"},
    "Gurdaspur": {"state": "Punjab", "district": "Gurdaspur"},
    "Hoshiarpur": {"state": "Punjab", "district": "Hoshiarpur"},
    "Jalandhar": {"state": "Punjab", "district": "Jalandhar"},
    "Kapurthala": {"state": "Punjab", "district": "Kapurthala"},
    "Ludhiana": {"state": "Punjab", "district": "Ludhiana"},
    "Mansa": {"state": "Punjab", "district": "Mansa"},
    "Moga": {"state": "Punjab", "district": "Moga"},
    "Mohali": {"state": "Punjab", "district": "Mohali"},
    "Muktsar": {"state": "Punjab", "district": "Muktsar"},
    "Nawanshahr": {"state": "Punjab", "district": "Nawanshahr"},
    "Pathankot": {"state": "Punjab", "district": "Pathankot"},
    "Patiala": {"state": "Punjab", "district": "Patiala"},
    "Rewari_Haryana": {"state": "Punjab", "district": "Rewari Haryana"},
    "Ropar": {"state": "Punjab", "district": "Ropar"},
    "Rupnagar": {"state": "Punjab", "district": "Rupnagar"},
    "Sangrur": {"state": "Punjab", "district": "Sangrur"},
    "Shahid_Bhagat_Singh_Nagar": {"state": "Punjab", "district": "Shahid Bhagat Singh Nagar"},
    "Tarn_Taran": {"state": "Punjab", "district": "Tarn Taran"},
    "Ajmer": {"state": "Rajasthan", "district": "Ajmer"},
    "Baran": {"state": "Rajasthan", "district": "Baran"},
    "Bhilwara": {"state": "Rajasthan", "district": "Bhilwara"},
    "Chittaurgarh": {"state": "Rajasthan", "district": "Chittaurgarh"},
    "Dhaulpur": {"state": "Rajasthan", "district": "Dhaulpur"},
    "Hanumangarh": {"state": "Rajasthan", "district": "Hanumangarh"},
    "Jalor": {"state": "Rajasthan", "district": "Jalor"},
    "Jodhpur": {"state": "Rajasthan", "district": "Jodhpur"},
    "Nagaur": {"state": "Rajasthan", "district": "Nagaur"},
    "Rajsamand": {"state": "Rajasthan", "district": "Rajsamand"},
    "Sirohi": {"state": "Rajasthan", "district": "Sirohi"},
    "Alwar": {"state": "Rajasthan", "district": "Alwar"},
    "Barmer": {"state": "Rajasthan", "district": "Barmer"},
    "Bikaner": {"state": "Rajasthan", "district": "Bikaner"},
    "Churu": {"state": "Rajasthan", "district": "Churu"},
    "Dungarpur": {"state": "Rajasthan", "district": "Dungarpur"},
    "Jaipur": {"state": "Rajasthan", "district": "Jaipur"},
    "Jhalawar": {"state": "Rajasthan", "district": "Jhalawar"},
    "Karauli": {"state": "Rajasthan", "district": "Karauli"},
    "Pali": {"state": "Rajasthan", "district": "Pali"},
    "Sawai_Madhopur": {"state": "Rajasthan", "district": "Sawai Madhopur"},
    "Tonk": {"state": "Rajasthan", "district": "Tonk"},
    "Bundi": {"state": "Rajasthan", "district": "Bundi"},
    "Dausa": {"state": "Rajasthan", "district": "Dausa"},
    "Ganganagar": {"state": "Rajasthan", "district": "Ganganagar"},
    "Jaisalmer": {"state": "Rajasthan", "district": "Jaisalmer"},
    "Jhunjhunun": {"state": "Rajasthan", "district": "Jhunjhunun"},
    "Kota": {"state": "Rajasthan", "district": "Kota"},
    "Pratapgarh_Rajasthan": {"state": "Rajasthan", "district": "Pratapgarh Rajasthan"},
    "Sikar": {"state": "Rajasthan", "district": "Sikar"},
    "East_Sikkim": {"state": "Sikkim", "district": "East Sikkim"},
    "Gangtok": {"state": "Sikkim", "district": "Gangtok"},
    "North_Sikkim": {"state": "Sikkim", "district": "North Sikkim"},
    "South_Sikkim": {"state": "Sikkim", "district": "South Sikkim"},
    "West_Sikkim": {"state": "Sikkim", "district": "West Sikkim"},
    "Ariyalur": {"state": "Tamil Nadu", "district": "Ariyalur"},
    "Coimbatore": {"state": "Tamil Nadu", "district": "Coimbatore"},
    "Dindigul": {"state": "Tamil Nadu", "district": "Dindigul"},
    "Kancheepuram": {"state": "Tamil Nadu", "district": "Kancheepuram"},
    "Karur": {"state": "Tamil Nadu", "district": "Karur"},
    "Madurai": {"state": "Tamil Nadu", "district": "Madurai"},
    "Namakkal": {"state": "Tamil Nadu", "district": "Namakkal"},
    "Perambalur": {"state": "Tamil Nadu", "district": "Perambalur"},
    "Salem": {"state": "Tamil Nadu", "district": "Salem"},
    "Theni": {"state": "Tamil Nadu", "district": "Theni"},
    "Tirunelveli": {"state": "Tamil Nadu", "district": "Tirunelveli"},
    "Tiruvannamalai": {"state": "Tamil Nadu", "district": "Tiruvannamalai"},
    "Vellore": {"state": "Tamil Nadu", "district": "Vellore"},
    "Chennai": {"state": "Tamil Nadu", "district": "Chennai"},
    "Cuddalore": {"state": "Tamil Nadu", "district": "Cuddalore"},
    "Erode": {"state": "Tamil Nadu", "district": "Erode"},
    "Kanniyakumari": {"state": "Tamil Nadu", "district": "Kanniyakumari"},
    "Krishnagiri": {"state": "Tamil Nadu", "district": "Krishnagiri"},
    "Nagapattinam": {"state": "Tamil Nadu", "district": "Nagapattinam"},
    "Nilgiris": {"state": "Tamil Nadu", "district": "Nilgiris"},
    "Pudukkottai": {"state": "Tamil Nadu", "district": "Pudukkottai"},
    "Sivaganga": {"state": "Tamil Nadu", "district": "Sivaganga"},
    "Thiruvallur": {"state": "Tamil Nadu", "district": "Thiruvallur"},
    "Tirupathur": {"state": "Tamil Nadu", "district": "Tirupathur"},
    "Trichy": {"state": "Tamil Nadu", "district": "Trichy"},
    "Viluppuram": {"state": "Tamil Nadu", "district": "Viluppuram"},
    "Kumbakonam": {"state": "Tamil Nadu", "district": "Kumbakonam"},
    "Nagercoil": {"state": "Tamil Nadu", "district": "Nagercoil"},
    "Ooty": {"state": "Tamil Nadu", "district": "Ooty"},
    "Ramanathapuram": {"state": "Tamil Nadu", "district": "Ramanathapuram"},
    "Thanjavur": {"state": "Tamil Nadu", "district": "Thanjavur"},
    "Thiruvarur": {"state": "Tamil Nadu", "district": "Thiruvarur"},
    "Tiruppur": {"state": "Tamil Nadu", "district": "Tiruppur"},
    "Tuticorin": {"state": "Tamil Nadu", "district": "Tuticorin"},
    "Adilabad": {"state": "Telangana", "district": "Adilabad"},
    "Jagtial": {"state": "Telangana", "district": "Jagtial"},
    "Jogulamba_Gadwal": {"state": "Telangana", "district": "Jogulamba Gadwal"},
    "Khammam": {"state": "Telangana", "district": "Khammam"},
    "Mahabubnagar": {"state": "Telangana", "district": "Mahabubnagar"},
    "Medak": {"state": "Telangana", "district": "Medak"},
    "Nalgonda": {"state": "Telangana", "district": "Nalgonda"},
    "Peddapalli": {"state": "Telangana", "district": "Peddapalli"},
    "Sangareddy": {"state": "Telangana", "district": "Sangareddy"},
    "Vikarabad": {"state": "Telangana", "district": "Vikarabad"},
    "Kamareddy": {"state": "Telangana", "district": "Kamareddy"},
    "Komaram_Bheem_Asifabad": {"state": "Telangana", "district": "Komaram Bheem Asifabad"},
    "Mahbubnagar": {"state": "Telangana", "district": "Mahbubnagar"},
    "Medchal": {"state": "Telangana", "district": "Medchal"},
    "Nirmal": {"state": "Telangana", "district": "Nirmal"},
    "Rajanna_Sircilla": {"state": "Telangana", "district": "Rajanna Sircilla"},
    "Siddipet": {"state": "Telangana", "district": "Siddipet"},
    "Wanaparthy": {"state": "Telangana", "district": "Wanaparthy"},
    "Karimnagar": {"state": "Telangana", "district": "Karimnagar"},
    "Mahabubabad": {"state": "Telangana", "district": "Mahabubabad"},
    "Mancherial": {"state": "Telangana", "district": "Mancherial"},
    "Nagarkurnool": {"state": "Telangana", "district": "Nagarkurnool"},
    "Nizamabad": {"state": "Telangana", "district": "Nizamabad"},
    "Ranga_Reddy": {"state": "Telangana", "district": "Ranga Reddy"},
    "Suryapet": {"state": "Telangana", "district": "Suryapet"},
    "Warangal": {"state": "Telangana", "district": "Warangal"},
    "Agartala": {"state": "Tripura", "district": "Agartala"},
    "Dhalai": {"state": "Tripura", "district": "Dhalai"},
    "North_Tripura": {"state": "Tripura", "district": "North Tripura"},
    "South_Tripura": {"state": "Tripura", "district": "South Tripura"},
    "Unakoti": {"state": "Tripura", "district": "Unakoti"},
    "West_Tripura": {"state": "Tripura", "district": "West Tripura"},
    "Agra": {"state": "Uttar Pradesh", "district": "Agra"},
    "Ambedkar_Nagar": {"state": "Uttar Pradesh", "district": "Ambedkar Nagar"},
    "Baghpat": {"state": "Uttar Pradesh", "district": "Baghpat"},
    "Balrampur": {"state": "Uttar Pradesh", "district": "Balrampur"},
    "Bareilly": {"state": "Uttar Pradesh", "district": "Bareilly"},
    "Budaun": {"state": "Uttar Pradesh", "district": "Budaun"},
    "Chitrakoot": {"state": "Uttar Pradesh", "district": "Chitrakoot"},
    "Etawah": {"state": "Uttar Pradesh", "district": "Etawah"},
    "Fatehpur": {"state": "Uttar Pradesh", "district": "Fatehpur"},
    "Ghaziabad": {"state": "Uttar Pradesh", "district": "Ghaziabad"},
    "Gorakhpur": {"state": "Uttar Pradesh", "district": "Gorakhpur"},
    "Hathras": {"state": "Uttar Pradesh", "district": "Hathras"},
    "Jhansi": {"state": "Uttar Pradesh", "district": "Jhansi"},
    "Kanpur": {"state": "Uttar Pradesh", "district": "Kanpur"},
    "Kheri": {"state": "Uttar Pradesh", "district": "Kheri"},
    "Lucknow": {"state": "Uttar Pradesh", "district": "Lucknow"},
    "Mahoba": {"state": "Uttar Pradesh", "district": "Mahoba"},
    "Mau": {"state": "Uttar Pradesh", "district": "Mau"},
    "Moradabad": {"state": "Uttar Pradesh", "district": "Moradabad"},
    "Pilibhit": {"state": "Uttar Pradesh", "district": "Pilibhit"},
    "Ramabai_Nagar": {"state": "Uttar Pradesh", "district": "Ramabai Nagar"},
    "Sant_Kabir_Nagar": {"state": "Uttar Pradesh", "district": "Sant Kabir Nagar"},
    "Shrawasti": {"state": "Uttar Pradesh", "district": "Shrawasti"},
    "Sonbhadra": {"state": "Uttar Pradesh", "district": "Sonbhadra"},
    "Varanasi": {"state": "Uttar Pradesh", "district": "Varanasi"},
    "Aligarh": {"state": "Uttar Pradesh", "district": "Aligarh"},
    "Auraiya": {"state": "Uttar Pradesh", "district": "Auraiya"},
    "Bahraich": {"state": "Uttar Pradesh", "district": "Bahraich"},
    "Banda": {"state": "Uttar Pradesh", "district": "Banda"},
    "Basti": {"state": "Uttar Pradesh", "district": "Basti"},
    "Bulandshahar": {"state": "Uttar Pradesh", "district": "Bulandshahar"},
    "Deoria": {"state": "Uttar Pradesh", "district": "Deoria"},
    "Faizabad": {"state": "Uttar Pradesh", "district": "Faizabad"},
    "Firozabad": {"state": "Uttar Pradesh", "district": "Firozabad"},
    "Ghazipur": {"state": "Uttar Pradesh", "district": "Ghazipur"},
    "Hamirpur_Uttar_Pradesh": {"state": "Uttar Pradesh", "district": "Hamirpur Uttar Pradesh"},
    "Jalaun": {"state": "Uttar Pradesh", "district": "Jalaun"},
    "Jyotiba_Phule_Nagar": {"state": "Uttar Pradesh", "district": "Jyotiba Phule Nagar"},
    "Kanshiram_Nagar": {"state": "Uttar Pradesh", "district": "Kanshiram Nagar"},
    "Kushinagar": {"state": "Uttar Pradesh", "district": "Kushinagar"},
    "Mahamaya_Nagar": {"state": "Uttar Pradesh", "district": "Mahamaya Nagar"},
    "Mainpuri": {"state": "Uttar Pradesh", "district": "Mainpuri"},
    "Meerut": {"state": "Uttar Pradesh", "district": "Meerut"},
    "Muzaffarnagar": {"state": "Uttar Pradesh", "district": "Muzaffarnagar"},
    "Pratapgarh": {"state": "Uttar Pradesh", "district": "Pratapgarh"},
    "Rampur": {"state": "Uttar Pradesh", "district": "Rampur"},
    "Sant_Ravidas_Nagar": {"state": "Uttar Pradesh", "district": "Sant Ravidas Nagar"},
    "Siddharth_Nagar": {"state": "Uttar Pradesh", "district": "Siddharth Nagar"},
    "Sultanpur": {"state": "Uttar Pradesh", "district": "Sultanpur"},
    "Allahabad": {"state": "Uttar Pradesh", "district": "Allahabad"},
    "Azamgarh": {"state": "Uttar Pradesh", "district": "Azamgarh"},
    "Ballia": {"state": "Uttar Pradesh", "district": "Ballia"},
    "Barabanki": {"state": "Uttar Pradesh", "district": "Barabanki"},
    "Bijnor": {"state": "Uttar Pradesh", "district": "Bijnor"},
    "Chandauli": {"state": "Uttar Pradesh", "district": "Chandauli"},
    "Etah": {"state": "Uttar Pradesh", "district": "Etah"},
    "Farrukhabad": {"state": "Uttar Pradesh", "district": "Farrukhabad"},
    "Gautam_Buddha_Nagar": {"state": "Uttar Pradesh", "district": "Gautam Buddha Nagar"},
    "Gonda": {"state": "Uttar Pradesh", "district": "Gonda"},
    "Hardoi": {"state": "Uttar Pradesh", "district": "Hardoi"},
    "Jaunpur": {"state": "Uttar Pradesh", "district": "Jaunpur"},
    "Kannauj": {"state": "Uttar Pradesh", "district": "Kannauj"},
    "Kaushambi": {"state": "Uttar Pradesh", "district": "Kaushambi"},
    "Lalitpur": {"state": "Uttar Pradesh", "district": "Lalitpur"},
    "Maharajganj": {"state": "Uttar Pradesh", "district": "Maharajganj"},
    "Mathura": {"state": "Uttar Pradesh", "district": "Mathura"},
    "Mirzapur": {"state": "Uttar Pradesh", "district": "Mirzapur"},
    "Noida": {"state": "Uttar Pradesh", "district": "Noida"},
    "Rae_Bareli": {"state": "Uttar Pradesh", "district": "Rae Bareli"},
    "Saharanpur": {"state": "Uttar Pradesh", "district": "Saharanpur"},
    "Shahjahanpur": {"state": "Uttar Pradesh", "district": "Shahjahanpur"},
    "Sitapur": {"state": "Uttar Pradesh", "district": "Sitapur"},
    "Unnao": {"state": "Uttar Pradesh", "district": "Unnao"},
    "Almora": {"state": "Uttarakhand", "district": "Almora"},
    "Champawat": {"state": "Uttarakhand", "district": "Champawat"},
    "Haridwar": {"state": "Uttarakhand", "district": "Haridwar"},
    "Pithoragarh": {"state": "Uttarakhand", "district": "Pithoragarh"},
    "Rudrapur": {"state": "Uttarakhand", "district": "Rudrapur"},
    "Udham_Singh_Nagar": {"state": "Uttarakhand", "district": "Udham Singh Nagar"},
    "Bageshwar": {"state": "Uttarakhand", "district": "Bageshwar"},
    "Dehradun": {"state": "Uttarakhand", "district": "Dehradun"},
    "Nainital": {"state": "Uttarakhand", "district": "Nainital"},
    "Roorkee": {"state": "Uttarakhand", "district": "Roorkee"},
    "Srinagar_Garhwal": {"state": "Uttarakhand", "district": "Srinagar(Garhwal)"},
    "Chamoli": {"state": "Uttarakhand", "district": "Chamoli"},
    "Haldwani": {"state": "Uttarakhand", "district": "Haldwani"},
    "Pauri_Garhwal": {"state": "Uttarakhand", "district": "Pauri Garhwal"},
    "Rudraprayag": {"state": "Uttarakhand", "district": "Rudraprayag"},
    "Tehri_Garhwal": {"state": "Uttarakhand", "district": "Tehri Garhwal"},
    "Alipurduar": {"state": "West Bengal", "district": "Alipurduar"},
    "Barddhaman": {"state": "West Bengal", "district": "Barddhaman"},
    "Dakshin_Dinajpur": {"state": "West Bengal", "district": "Dakshin Dinajpur"},
    "Haldia": {"state": "West Bengal", "district": "Haldia"},
    "Jalpaiguri": {"state": "West Bengal", "district": "Jalpaiguri"},
    "Koch_Bihar": {"state": "West Bengal", "district": "Koch Bihar"},
    "Midnapur": {"state": "West Bengal", "district": "Midnapur"},
    "North_Twenty_Four_Parganas": {"state": "West Bengal", "district": "North Twenty Four Parganas"},
    "Puruliya": {"state": "West Bengal", "district": "Puruliya"},
    "South_Twenty_Four_Parganas": {"state": "West Bengal", "district": "South Twenty Four Parganas"},
    "Asansol": {"state": "West Bengal", "district": "Asansol"},
    "Birbhum": {"state": "West Bengal", "district": "Birbhum"},
    "Darjiling": {"state": "West Bengal", "district": "Darjiling"},
    "Howrah": {"state": "West Bengal", "district": "Howrah"},
    "Jhargram": {"state": "West Bengal", "district": "Jhargram"},
    "Kolkata": {"state": "West Bengal", "district": "Kolkata"},
    "Murshidabad": {"state": "West Bengal", "district": "Murshidabad"},
    "Paschim_Medinipur": {"state": "West Bengal", "district": "Paschim Medinipur"},
    "Raniganj": {"state": "West Bengal", "district": "Raniganj"},
    "Bankura": {"state": "West Bengal", "district": "Bankura"},
    "Burdwan": {"state": "West Bengal", "district": "Burdwan"},
    "Durgapur": {"state": "West Bengal", "district": "Durgapur"},
    "Hugli": {"state": "West Bengal", "district": "Hugli"},
    "Kharagpur": {"state": "West Bengal", "district": "Kharagpur"},
    "Malda": {"state": "West Bengal", "district": "Malda"},
    "Nadia": {"state": "West Bengal", "district": "Nadia"},
    "Purba_Medinipur": {"state": "West Bengal", "district": "Purba Medinipur"},
    "Siliguri": {"state": "West Bengal", "district": "Siliguri"},
}

# ── "No Jobs" page detection phrases (v10) ──────────────────
# Agar listing page par ye phrases milein to category skip karo
NO_JOBS_PHRASES = [
    "there are no jobs in",
    "no jobs found",
    "no government jobs found",
    "currently no jobs",
    "no job available",
    "no vacancy available",
    "no recruitment available",
    "0 jobs found",
    "jobs not found",
    "sorry, no results",
    "no posts found",
]

PAN_INDIA_CATEGORIES = set()   # Empty — district scraper mein har category khud ek
                                 # specific location hai, "Pan India" fallback ki zaroorat nahi

INDIA_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu & Kashmir", "Jammu and Kashmir", "Ladakh", "Chandigarh",
    "Puducherry", "Andaman", "Lakshadweep",
]

# Scraper/aggregator domains — inke links JSON mein NAHI jayenge
SCRAPER_DOMAINS = [
    "freejobalert.com",
    "sarkariresult.com",
    "sarkarinaukri.com",
    "rojgarresult.com",
    "employment-news.in",
    "naukri.com",
    "shine.com",
    "timesjobs.com",
    "monsterindia.com",
    "rojgarsamachar",
    "govtjobsalert",
    "sarkariexam",
]

# App / download junk phrases — ye links filter ho jayenge
APP_JUNK_PHRASES = [
    "get app", "download app", "get it on", "app store", "play store",
    "google play", "download now", "install app", "mobile app",
    "click here to download", "download mobile",
]

_global_seen_urls: set  = set()
_seen_lock               = threading.Lock()
_POST_KEY_RE             = re.compile(r'^[a-z0-9_]+_jobs___\d+_posts$')
JSON_PATH        = "_temp_district.json"   # Resume tracking (in-memory only reference)
OUTPUT_JSON_PATH        = "_temp_district.json"    # Final output — sirf yahi ek file banega

# ── State/aggregator URL patterns — ye actual job pages NAHI hain ──────────
# Ye freejobalert ke internal listing/state pages hain jo scrape nahi hone chahiye
JUNK_URL_PATTERNS = [
    re.compile(r'freejobalert\.com/(uttar-pradesh|bihar|rajasthan|madhya-pradesh|'
               r'maharashtra|west-bengal|gujarat|karnataka|tamil-nadu|andhra-pradesh|'
               r'telangana|kerala|punjab|haryana|himachal-pradesh|uttarakhand|'
               r'jharkhand|chhattisgarh|odisha|assam|delhi|jammu-kashmir|'
               r'chandigarh|goa|sikkim|manipur|meghalaya|mizoram|nagaland|'
               r'tripura|arunachal-pradesh|ladakh|puducherry|lakshadweep|andaman)/?$'),
    re.compile(r'freejobalert\.com/(latest-notifications|last-date-reminder|'
               r'railway-jobs|police-defence-jobs|bank-jobs|teaching-faculty-jobs|'
               r'medical-hospital-jobs)/?$'),
    re.compile(r'freejobalert\.com/search-jobs/[^/]+/?$'),  # search-jobs listing pages
    re.compile(r'freejobalert\.com/(page|category|tag)/'),
]

def is_junk_fja_url(href: str) -> bool:
    """freejobalert ke internal state/aggregator/listing pages block karo."""
    for pat in JUNK_URL_PATTERNS:
        if pat.search(href):
            return True
    return False


# ============================================================
# (QUAL_KEYWORDS helpers removed — district scraper mein qualification-
# based keyword matching applicable nahi hai. District ek location hai,
# qualification nahi.)
# ============================================================


def _detect_no_jobs_page(soup, category: str) -> bool:
    """
    Listing page par 'no jobs' message detect karo.
    True return karo agar page indicates koi job nahi hai.
    FIXED: Block/Captcha/Rate-limit page ko no-jobs se alag karo.
    """
    page_text = soup.get_text(" ", strip=True).lower()

    # ── Block / Captcha / Rate-limit signals — False return karo ──
    # Matlab jobs exist ho sakti hain, site ne block kiya hai
    block_signals = [
        "access denied", "403 forbidden", "captcha", "cloudflare",
        "ray id", "please verify", "unusual traffic", "automated",
        "just a moment", "checking your browser", "ddos protection",
        "enable javascript", "enable cookies", "are you human",
        "robot", "bot detected",
    ]
    for signal in block_signals:
        if signal in page_text:
            print(f"  [WARN] Block/Captcha page detected — waiting...")
            smart_delay("crawl", extra=25)
            return False  # Skip nahi karo — retry karega

    # ── Page content bahut chhota — blocked/redirect ho sakta hai ──
    if len(page_text) < 500:
        print(f"  [WARN] Page too small ({len(page_text)} chars) — likely blocked")
        return False

    # ── Actual no-jobs phrases ──────────────────────────────────
    for phrase in NO_JOBS_PHRASES:
        if phrase in page_text:
            return True

    # ── Common empty-result CSS classes ────────────────────────
    for cls in ["no-results", "no-posts-found", "nothing-found",
                "not-found", "empty-results", "no-jobs"]:
        if soup.find(class_=cls):
            return True

    # ── Paragraph mein "0 jobs" ya "no jobs" ───────────────────
    for p in soup.find_all("p"):
        txt = p.get_text(" ", strip=True).lower()
        if re.search(r'\bno\s+jobs?\b|\b0\s+jobs?\b', txt):
            return True

    return False


# ============================================================
# HELPERS
# ============================================================
def clean(x) -> str:
    if not x:
        return ""
    return " ".join(str(x).split()).strip()


def is_scraper_link(href: str) -> bool:
    if not href:
        return True
    hl = href.lower()
    return any(d in hl for d in SCRAPER_DOMAINS)


def is_app_junk_link(text: str, href: str) -> bool:
    """'Get App', 'Download Click Here' jaisi links block karo."""
    combined = (text + " " + href).lower()
    return any(phrase in combined for phrase in APP_JUNK_PHRASES)


def is_junk_link(href: str, text: str = "") -> bool:
    if not href:
        return True
    junk_domains = [
        "t.me", "telegram", "whatsapp", "youtube", "youtu.be",
        "facebook", "twitter", "instagram", "bit.ly", "tinyurl",
        "javascript:", "mailto:", "arattai", "onelink", "app.adjust",
        "play.google", "apps.apple",
    ]
    if any(j in href.lower() for j in junk_domains):
        return True
    if href in ("#", ""):
        return True
    if is_app_junk_link(text, href):
        return True
    return False


def is_valid_official_link(href: str, text: str = "") -> bool:
    if not href or not href.startswith("http"):
        return False
    if is_junk_link(href, text):
        return False
    if is_scraper_link(href):
        return False
    return True


def classify_link(text: str, href: str) -> str:
    combined = (text + " " + href).lower()
    if "offline" not in combined and any(w in combined for w in [
            "apply online", "apply here", "online form", "register",
            "online application", "apply now", "apply link",
            "application form", "apply for"]):
        return "apply_online"
    if any(w in combined for w in ["notification", "advt", "advertisement", "official notice", "notice pdf"]):
        return "notification_pdf"
    if "syllabus" in combined:
        return "syllabus_pdf"
    if any(w in combined for w in ["admit card", "hall ticket", "call letter"]):
        return "admit_card"
    if "result" in combined:
        return "result"
    if "answer key" in combined:
        return "answer_key"
    if "login" in combined:
        return "login"
    if any(w in combined for w in ["official website", "official site", "home page", "homepage"]):
        return "official_website"
    if "apply offline" in combined:
        return "apply_offline"
    if any(w in combined for w in ["cut off", "cutoff", "cut-off"]):
        return "cut_off"
    return "other"


def _extract_state(text: str) -> str:
    for state in INDIA_STATES:
        if state.lower() in text.lower():
            return state
    return ""


def _add_link(links_dict: dict, key: str, href: str, label: str = ""):
    """URL store karo. label provide karo to parallel _labels dict mein bhi save hoga."""
    if key not in links_dict:
        links_dict[key] = href
    else:
        existing = links_dict[key]
        if isinstance(existing, str) and existing != href:
            links_dict[key] = [existing, href]
        elif isinstance(existing, list) and href not in existing:
            existing.append(href)
    # Label parallel dict mein store karo (overwrite nahi — pehla label hi rakho)
    if label:
        labels = links_dict.setdefault("_labels", {})
        if key not in labels:
            labels[key] = label


def _first(val):
    if isinstance(val, list):
        return val[0] if val else ""
    return val or ""


# ============================================================
# POST-PROCESS
# ============================================================
def _post_process_job(job: dict, category: str):
    bd = job["basic_details"]
    dt = job["important_dates"]
    lk = job["important_links"]
    ql = job["qualification"]

    # Application mode normalize
    mode = bd.get("application_mode", "")
    if mode:
        m = mode.lower()
        if m.startswith("online"):
            bd["application_mode"] = "Online"
        elif m.startswith("offline"):
            bd["application_mode"] = "Offline"
        elif "walk" in m:
            bd["application_mode"] = "Walk-in"
        elif "email" in m:
            bd["application_mode"] = "Email"

    # Apply online fallback from auto-generated post keys
    if not lk.get("apply_online"):
        for k, v in list(lk.items()):
            if _POST_KEY_RE.match(k) and isinstance(v, str) and v.startswith("http"):
                if is_valid_official_link(v):
                    lk["apply_online"] = v
                break

    if not lk.get("apply_online"):
        for alt in ["apply_link", "application_form"]:
            if lk.get(alt):
                v = _first(lk[alt])
                if is_valid_official_link(v):
                    lk["apply_online"] = v
                break

    # Auto-generated post keys hatao
    for k in list(lk.keys()):
        if _POST_KEY_RE.match(k):
            del lk[k]

    # Junk keys hatao
    for jk in ["join_arattai_channel", "download_mobile_app", "get_app",
                "download_app", "click_here_to_download"]:
        lk.pop(jk, None)

    # "other" links clean karo
    if "other" in lk:
        specific = set()
        for k, v in lk.items():
            if k in ("other", "_labels"):  # _labels dict skip karo
                continue
            if isinstance(v, str):
                specific.add(v)
            elif isinstance(v, list):
                specific.update(v)
        other = lk["other"]
        if isinstance(other, str):
            if other in specific or not is_valid_official_link(other):
                del lk["other"]
        elif isinstance(other, list):
            filtered = [u for u in other if u not in specific and is_valid_official_link(u)]
            if not filtered:
                del lk["other"]
            else:
                lk["other"] = filtered[0] if len(filtered) == 1 else filtered

    # Final cleanup — scraper/app links nikalo (_labels dict preserve karo)
    for k in list(lk.keys()):
        if k == "_labels":  # label metadata — kabhi delete nahi karna
            continue
        v = lk[k]
        if isinstance(v, str):
            if not is_valid_official_link(v):
                del lk[k]
        elif isinstance(v, list):
            cleaned = [u for u in v if is_valid_official_link(u)]
            if not cleaned:
                del lk[k]
            elif len(cleaned) == 1:
                lk[k] = cleaned[0]
            else:
                lk[k] = cleaned

    # Application start date synonyms
    if not dt.get("application_start_date"):
        synonyms = [
            "opening date for online registration",
            "opening date for online registration of applications",
            "opening date of online application",
            "starting date for online application",
            "starting date of online application",
            "start date of online application",
            "commencement of online application",
            "date of commencement",
            "registration start",
            "online registration start",
        ]
        for syn in synonyms:
            if dt.get(syn):
                dt["application_start_date"] = dt[syn]
                break

    # ── Job location (district scraper — DISTRICT_META priority) ──
    # Sabse reliable source: category-key khud hi district hai, isliye
    # DISTRICT_META se directly "District, State" set karo.
    meta = DISTRICT_META.get(category)
    if meta:
        bd["job_location"] = f"{meta['district']}, {meta['state']}"
        bd["district"] = meta["district"]
        bd["state"] = meta["state"]
    else:
        # Fallback — agar kisi wajah se meta na mile (safety net)
        if not bd.get("job_location"):
            loc = _extract_state(bd.get("job_title", ""))
            if loc:
                bd["job_location"] = loc
        if not bd.get("job_location"):
            loc = _extract_state(ql.get("domicile", ""))
            if loc:
                bd["job_location"] = loc

    # (Qualification keyword matching removed — district scraper mein
    # applicable nahi hai; matched_qualifications field FJA qualification
    # scraper (scraper_fja.py) ke output mein hi rehta hai.)

    # Total vacancies fallback
    if not bd.get("total_vacancies"):
        best = 0
        for row in job.get("vacancy_details", []):
            for k, v in row.items():
                if any(w in k.lower() for w in ["total", "posts", "vacancy"]):
                    try:
                        n = int(re.sub(r"[^\d]", "", str(v)))
                        best = max(best, n)
                    except Exception:
                        pass
        if best:
            bd["total_vacancies"] = str(best)

# ============================================================
# HELPER: "Other Latest Govt Jobs Updated Today" SECTION SCRAPER
# ============================================================
def _scrape_other_latest_section(content_area, base_url: str, try_add_fn):
    """
    entry-content ke andar se "Other Latest Govt Jobs Updated Today"
    wali section ke baad ki poori job link list collect karo.

    ACTUAL HTML structure (image se confirmed):
      <div class="entry-content" itemprop="text">
        <div class="org_tab">...</div>   ← qualification-specific jobs
        <div class="org_tab">...</div>
        ...
        <div style="font-weight: bold; margin-bottom: 10px;">
          <span class="latest">Other Latest Govt Jobs Updated Today 07-Jun-2026</span>
        </div>                           ← YE HEADING hai — iske BAAD koi sibling nahi
      </div>

    NOTE: Image se clear hai ki span.latest wali div entry-content ka LAST
    element hai. "Other Latest" jobs actually span se PEHLE wali org_tab divs
    hi hoti hain jo heading ke context mein include hoti hain.

    REVISED STRATEGY:
      1. entry-content mein span.latest dhundo
      2. Us span ke parent div ka position note karo
      3. entry-content ke direct children mein:
         - span.latest parent se PEHLE ke saare org_tab divs = category-specific jobs
           (already Method A se collect ho chuki hain)
         - span.latest parent KHUD = "Other Latest" section heading
         - span.latest parent ke BAAD wale org_tab divs = "Other Latest" jobs
           → ye try_add_fn se collect karo
      4. Agar span.latest ke baad koi org_tab nahi (ye last element hai), toh
         entry-content ke POORE org_tab/be-table links scan karo — Method A
         already handle karta hai, toh yahan kuch extra karne ki zaroorat nahi.

    Returns: None
    """
    # span.latest dhundo
    trigger_span = None
    for span in content_area.find_all("span", class_="latest"):
        txt = span.get_text(" ", strip=True).lower()
        if "other latest" in txt and "govt jobs" in txt:
            trigger_span = span
            break

    # Broader fallback: koi bhi element jisme text ho
    if not trigger_span:
        for el in content_area.find_all(True):
            txt = el.get_text(" ", strip=True).lower()
            if "other latest govt jobs" in txt and len(txt) < 200:
                trigger_span = el
                break

    if not trigger_span:
        return  # Section nahi mila

    # Trigger ka parent div (jo font-weight:bold wala container hai)
    heading_div = trigger_span.parent

    # entry-content ke direct children mein heading_div ke BAAD wale elements scan karo
    # Image structure mein heading_div last hai — lekin agar future mein links baad mein
    # aayein to bhi handle ho jayega
    found_heading = False
    count = 0

    for child in content_area.children:
        if child == heading_div:
            found_heading = True
            continue
        if not found_heading:
            continue
        # Heading ke baad wale elements mein links dhundo
        if hasattr(child, "find_all"):
            for a in child.find_all("a", href=True):
                href = a["href"]
                if not href.startswith("http"):
                    href = urljoin(base_url, href)
                if "freejobalert.com" in href and not is_junk_fja_url(href):
                    try_add_fn(href)
                    count += 1

    # Agar heading last element thi (count==0), toh poore content_area ke
    # org_tab divs scan karo jo already Method A se miss ho sakti hain —
    # specifically tables ke andar chhupe links
    if count == 0:
        for org_div in content_area.find_all("div", class_="org_tab"):
            for a in org_div.find_all("a", href=True):
                href = a["href"]
                if not href.startswith("http"):
                    href = urljoin(base_url, href)
                if "freejobalert.com" in href and not is_junk_fja_url(href):
                    try_add_fn(href)
                    count += 1
        if count:
            print(f"  [Method G: Other Latest Jobs — org_tab fallback] +{count} links collected")
    else:
        print(f"  [Method G: Other Latest Jobs] +{count} links collected")



def _is_valid_fja_article(href: str) -> bool:
    """
    FJA article URL valid hai ya nahi check karo.
    Ye accept karta hai:
    - /word-word-recruitment-2026/ style
    - /word-word-2026/ style (year stamped)
    - /word-word-bharti-word/ style
    Ye REJECT karta hai:
    - /search-jobs/ listing pages
    - /page/N/ pagination
    - /category/ /tag/ pages
    """
    if not href or "freejobalert.com" not in href:
        return False
    path = href.split("freejobalert.com", 1)[-1].rstrip("/")
    if "?" in path or path.count("/") > 2:
        return False
    for skip in ["/search-jobs/", "/category/", "/tag/", "/page/"]:
        if skip in path:
            return False
    slug = path.strip("/")
    if not slug or len(slug) < 5:
        return False
    if re.search(r'(?:20\d\d|recruitment|notification|bharti|vacancy|result|admit|answer|syllabus|apply|jobs?|exam|selection|interview|merit|cutoff|walkin|walk-in)', slug, re.I):
        return True
    return False

# ============================================================
# STEP 1: COLLECT ALL JOB PAGE LINKS (ALL PAGES)
# FIX: _global_seen_urls se match nahi karte listing mein —
#      resume check sirf scraping step par hota hai.
# ============================================================
def collect_all_job_links(session, base_url: str, category: str = "") -> tuple:
    """
    Listing pages se SABHI job links collect karo.
    Global seen set ka use NAHI karte yahan — warna resume mode mein
    already scraped jobs ki URLs skip ho jaati hain aur naye duplicates
    ke liye check nahi hota correctly.

    FIXES (v6):
    - entry-content div ke ANDAR se hi links lo (bahar wali nav/sidebar ignore)
    - search-jobs pagination: ?page=N aur /page/N/ dono try karo
    - _try_numbered_next ka None return properly handle karo
    - 0-new-links early stop sirf page > 3 par (page 2 kabhi kabhi empty hoti hai)

    v10: no-jobs page detection, category label for logging

    Returns: (links_list, confirmed_empty)
      confirmed_empty=True  -> site ne no-jobs confirm kar diya, retry mat karo
      confirmed_empty=False -> rate-limit ya error ho sakta hai, retry valid hai
    """
    # Qualification categories use /search-jobs/ URL pattern
    is_search_jobs = "/search-jobs/" in base_url

    links    = []
    seen_loc = set()       # sirf is category ke duplicate links block karo
    current_url = base_url
    page_num    = 1

    while current_url:
        try:
            print(f"  [Page {page_num}] Fetching listing: {current_url}")
            r = session.get(current_url, timeout=25)
            if r.status_code == 404:
                print(f"  [Page {page_num}] HTTP 404 — no more pages, stopping")
                break
            if r.status_code in (403, 429):
                wait_s = 90 if r.status_code == 429 else 60
                print(f"  [WARN] HTTP {r.status_code} — Rate limited! Waiting...")
                smart_delay("crawl", extra=wait_s - 5)
                continue  # retry same page
            if r.status_code != 200:
                print(f"  [WARN] HTTP {r.status_code} on listing page — stopping")
                break

            soup = BeautifulSoup(r.text, "html.parser")

            # v10: "No Jobs" page early detection
            # Sirf page 1 par check karo — agar no-jobs message mila
            # toh is category mein koi job hai hi nahi, retry waste hai
            if page_num == 1 and _detect_no_jobs_page(soup, ""):
                print(f"  NO JOBS PAGE detected on page 1 — skipping entire category")
                return [], True   # confirmed_empty=True — retry mat karo

            # ── Scope: sirf entry-content ke andar dhundo ───
            # Sidebar, nav, header ke links ignore karo
            content_area = (
                soup.find("div", class_="entry-content") or
                soup.find("div", id="content") or
                soup.find("main") or
                soup
            )

            links_before = len(links)

            def try_add(href: str):
                if not href:
                    return
                # Absolute URL banana
                if not href.startswith("http"):
                    href = urljoin(current_url, href)
                # Only freejobalert article links
                if "freejobalert.com" not in href:
                    return
                if is_junk_link(href):
                    return
                # Category/pagination/state-aggregator pages nahi chahiye
                if any(x in href for x in ["/search-jobs/", "/page/", "/category/",
                                            "/tag/", "?page=", "#"]):
                    return
                # State listing pages aur internal FJA aggregator pages block karo
                if is_junk_fja_url(href):
                    return
                if href not in seen_loc:
                    links.append(href)
                    seen_loc.add(href)

            # ── Method A: org_tab divs ──────────────────────
            # STOP CONDITION: entry-content ke direct children ko sequence mein
            # iterate karo. Jaise hi kisi child ke andar span.latest milti hai
            # jisme "Other Latest Govt Jobs Updated Today" text ho, WAHAN RUKKO.
            # Baad ke saare org_tab = "Other Latest" section = SKIP.
            def _has_latest_trigger(element) -> bool:
                """True agar element ke andar stop-trigger span hai."""
                for sp in element.find_all("span", class_="latest"):
                    txt = sp.get_text(" ", strip=True).lower()
                    if "other latest" in txt and "govt jobs" in txt:
                        return True
                return False

            for _child in content_area.children:
                if not hasattr(_child, "get"):   # NavigableString skip
                    continue
                # Stop trigger milte hi aage kuch mat karo
                if _has_latest_trigger(_child):
                    print("  [Method A] Stop trigger mila — 'Other Latest Govt Jobs' heading. Iske baad ke org_tab SKIP.")
                    break
                # org_tab div — link lo
                if _child.get("class") and "org_tab" in _child.get("class", []):
                    _a = _child.find("a", href=True)
                    if _a:
                        try_add(_a["href"])

            # ── Method B: be-table ──────────────────────────
            for table in content_area.find_all("table", class_="be-table"):
                for row in table.find_all("tr"):
                    a = row.find("a", href=True)
                    if a:
                        try_add(a["href"])

            # ── Method C: lattrbord rows ────────────────────
            for row in content_area.find_all("tr", class_="lattrbord"):
                a = row.find("a", href=True)
                if a:
                    try_add(a["href"])

            # ── Method D: h2 / h3 headings with links ──────
            for heading in content_area.find_all(["h2", "h3"]):
                a = heading.find("a", href=True)
                if a and "freejobalert.com" in a.get("href", ""):
                    try_add(a["href"])

            # ── Method E: entry-list / post-list items ──────
            for cls in ["entry-list", "post-list", "job-list", "job_list",
                        "posts-list", "listing-post"]:
                for div in content_area.find_all("div", class_=cls):
                    for a in div.find_all("a", href=True):
                        if "freejobalert.com" in a["href"]:
                            try_add(a["href"])

            # ── Method F: article/h2 links inside entry-content ─
            # search-jobs pages mostly have links inside <p> or <div> inside entry-content
            # STRICT: sirf actual job/recruitment article URLs lo, state pages nahi
            # STOP CONDITION: span.latest "Other Latest Govt Jobs..." ke baad ke links SKIP
            if len(links) - links_before == 0 or is_search_jobs:
                # Step 1: find the trigger element (stop boundary)
                _f_stop_el = None
                for _sp in content_area.find_all("span", class_="latest"):
                    _sp_txt = _sp.get_text(" ", strip=True).lower()
                    if "other latest" in _sp_txt and "govt jobs" in _sp_txt:
                        # parent container (bold div) is the boundary
                        _f_stop_el = _sp.parent
                        break

                # Step 2: iterate children, collect links only BEFORE boundary
                for _f_child in content_area.children:
                    if not hasattr(_f_child, "get"):
                        continue
                    if _f_stop_el is not None and _f_child == _f_stop_el:
                        break   # boundary mila — stop
                    for a in _f_child.find_all("a", href=True):
                        href = a["href"]
                        if not href.startswith("http"):
                            href = urljoin(current_url, href)
                        if (_is_valid_fja_article(href) and
                                not is_junk_fja_url(href) and
                                "?" not in href):
                            try_add(href)

            # ── Method G: DISABLED ──────────────────────────────
            # Method G pehle "Other Latest Govt Jobs" heading ke BAAD
            # ki links collect karta tha. Ab requirements changed:
            # heading ke BAAD ki koi bhi job nahi chahiye.
            # Method A aur F ab correct stop condition ke saath kaam kar rahe hain.
            # _scrape_other_latest_section() call removed.

            new_count = len(links) - links_before
            print(f"  [Page {page_num}] +{new_count} links | Total: {len(links)}")

            # ── Next page detection ─────────────────────────
            # Priority 1: rel="next" link tag (most reliable)
            next_url = None

            nxt_link = soup.find("link", attrs={"rel": "next"})
            if nxt_link and nxt_link.get("href"):
                next_url = urljoin(current_url, nxt_link["href"])

            # Priority 2: <a rel="next"> or class="next"
            if not next_url:
                nxt_a = (
                    soup.find("a", attrs={"rel": "next"}) or
                    soup.find("a", class_="next") or
                    soup.find("a", string=re.compile(r"(?i)^(next|»|next\s*page|next\s*»)$"))
                )
                if nxt_a and nxt_a.get("href"):
                    candidate = urljoin(current_url, nxt_a["href"])
                    if candidate != current_url:
                        next_url = candidate

            # Priority 3: search-jobs use ?page=N format
            if not next_url and is_search_jobs:
                next_url = _try_search_jobs_next(current_url, page_num, soup)

            # Priority 4: numbered pagination /page/N/ fallback
            if not next_url:
                next_url = _try_numbered_next(soup, current_url, page_num)

            if next_url and next_url != current_url:
                current_url = next_url
                page_num   += 1
                smart_delay("normal")
            else:
                print(f"  [Page {page_num}] No more pages.")
                break

            # Stop if consistently 0 new links (after page 3)
            if new_count == 0 and page_num > 3:
                print(f"  [Page {page_num}] 0 new links 2 times — stopping early")
                break

        except Exception as e:
            err = str(e)
            is_net = ("ConnectionError" in err or "Max retries" in err
                      or "NameResolution" in err or "RemoteDisconnected" in err
                      or "NewConnectionError" in err or "timed out" in err.lower())
            if is_net:
                print(f"  [NET-ERROR] Listing page {page_num}: {e}")
                _wait_for_net_reconnect()   # internet aane tak ruko, phir same page retry
                continue               # same current_url pe retry
            print(f"  [ERROR] Listing page {page_num}: {e}")
            break

    print(f"  ✓ Total links collected: {len(links)}")

    # Rate-limit sanity check
    # Agar page 1 pe 0 links mile lekin _detect_no_jobs_page ne True nahi
    # kaha — matlab page load hua hai lekin job listings nahi aayi
    # (rate-limited stripped response). confirmed_empty=False — retry valid.
    if not links:
        print(f"  [WARN] 0 links — possible rate-limit or empty category")

    return links, False   # confirmed_empty=False — caller retry kar sakta hai


def _try_search_jobs_next(current_url: str, current_page: int, soup) -> str:
    """
    search-jobs pages ke liye next page URL banao.
    Ye pages ?page=N ya /page/N/ dono format use kar sakti hain.
    Pehle soup mein numbered links check karo, phir construct karo.
    """
    next_page = current_page + 1

    # Soup mein /page/N+1/ link dhundo
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            href = urljoin(current_url, href)
        m = re.search(r'/page/(\d+)/', href)
        if m and int(m.group(1)) == next_page:
            return href
        m2 = re.search(r'[?&]page=(\d+)', href)
        if m2 and int(m2.group(1)) == next_page and "freejobalert.com" in href:
            return href

    # Construct: try /page/N/ first
    base = current_url.rstrip("/")
    # Remove existing page param
    base = re.sub(r'/page/\d+/?$', '', base)
    base = re.sub(r'[?&]page=\d+', '', base).rstrip("?&")

    candidate_slash = base.rstrip("/") + f"/page/{next_page}/"
    # For ?page= style
    sep = "&" if "?" in base else "?"
    candidate_query = base + f"{sep}page={next_page}"

    # Prefer /page/ style for search-jobs
    return candidate_slash


def _try_numbered_next(soup, current_url: str, current_page: int):
    """
    Numbered pagination try karo — e.g. /page/2/, /page/3/
    Returns next page URL or None.
    """
    # Find all pagination links in soup
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            href = urljoin(current_url, href)
        m = re.search(r'/page/(\d+)/', href)
        if m and int(m.group(1)) == current_page + 1:
            return href

    # Construct next page URL from current URL pattern
    m = re.search(r'/page/(\d+)/?$', current_url.rstrip("/"))
    if m:
        next_n = int(m.group(1)) + 1
        return re.sub(r'/page/\d+/?$', f'/page/{next_n}/', current_url)

    return None


# ============================================================
# STEP 2: EXTRACT DATA FROM JOB PAGE
# ============================================================
def extract_job_page(session, url: str) -> dict:
    job = {
        "basic_details":          {},
        "important_dates":        {},
        "application_fee":        {},
        "age_limit":              {},
        "qualification":          {},
        "vacancy_details":        [],
        "vacancy_breakdown":      {},
        "category_wise_vacancy":  {},
        "salary_details":         {},
        "selection_process":      [],
        "exam_pattern":           {},
        "syllabus":               {},
        "physical_eligibility":   {},
        "how_to_apply":           [],
        "important_instructions": [],
        "important_links":        {},
        "all_official_links":     [],
        "content_sections":       [],
        "faq":                    [],
    }

    try:
        r = session.get(url, timeout=30)
        if r.status_code != 200:
            print(f"    [WARN] HTTP {r.status_code} -> {url}")
            return job

        soup = BeautifulSoup(r.text, "html.parser")

        # ── Job Title ────────────────────────────────────────
        h1 = soup.find("h1", class_="entry-title") or soup.find("h1")
        if h1:
            job["basic_details"]["job_title"] = clean(h1.get_text())

        # ── Last Updated ─────────────────────────────────────
        time_tag = soup.find("time", class_="entry-date") or soup.find("time")
        if time_tag:
            dt_attr = time_tag.get("datetime", "")
            if dt_attr:
                try:
                    dt_obj = datetime.fromisoformat(dt_attr.split("+")[0].split("Z")[0])
                    job["basic_details"]["last_updated"] = dt_obj.strftime("%d %b %Y")
                except Exception:
                    job["basic_details"]["last_updated"] = clean(time_tag.get_text())
        else:
            lu = soup.find("p", class_="lastupdated")
            if lu:
                text = clean(lu.get_text())
                text = re.sub(r'\s*by\s+[\w][\w\s]*$', '', text, flags=re.IGNORECASE).strip()
                text = re.sub(r'^last\s+updated[\s:\-]*', '', text, flags=re.IGNORECASE).strip()
                if text:
                    job["basic_details"]["last_updated"] = text

        # ── Content area ─────────────────────────────────────
        content = soup.find("div", class_="entry-content") or soup.find("article")
        if not content:
            return job

        # ── FAQs (section) ───────────────────────────────────
        faq_section = soup.find("section", class_="faq-section")
        if faq_section:
            for item in faq_section.find_all("div", class_="faq-item"):
                q = item.find("h3", class_="faq-question")
                a = item.find("div", class_="faq-answer")
                if q and a:
                    _q = clean(q.get_text())
                    # FAQ guard: sirf genuine question accept karo (statement/
                    # table-cell text ko FAQ me mat daalo)
                    if looks_like_question(_q):
                        job["faq"].append({
                            "question": _q,
                            "answer":   clean(a.get_text()),
                        })

        # ── FAQs (JSON-LD) ────────────────────────────────────
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string or "")
                if isinstance(ld, dict) and ld.get("@type") == "FAQPage":
                    for entity in ld.get("mainEntity", []):
                        q_text = entity.get("name", "")
                        a_text = entity.get("acceptedAnswer", {}).get("text", "")
                        if (q_text and a_text and looks_like_question(q_text)
                                and not any(f["question"] == q_text for f in job["faq"])):
                            job["faq"].append({
                                "question": clean(q_text),
                                "answer":   clean(re.sub(r'<[^>]+>', '', a_text)),
                            })
            except Exception:
                pass

        # ── Noise removal ─────────────────────────────────────
        for cls in [
            "fja-follow-bar", "fja-social-follow-row", "article-social-icons",
            "whatsapp-button-container", "join-play-games-container",
            "yarpp", "author-bio-container", "fja-alert-widget",
            "games-buttons-row", "video-ad-container", "ad_div",
            "addtoany_shortcode", "faq-section",
        ]:
            for el in content.find_all(class_=cls):
                el.decompose()
        for tag in content.find_all(["script", "style", "noscript", "iframe"]):
            tag.decompose()
        # Bug 4 fix: ad-network / "DON'T MISS" recommendation widgets destroy karo
        # taaki unka text qualification/physical_eligibility me leak na kare.
        sanitize_dom(content)

        # ── H2 section parsing ────────────────────────────────
        for h2 in content.find_all("h2"):
            section_title = clean(h2.get_text()).lower()

            siblings = []
            for sib in h2.find_next_siblings():
                if sib.name == "h2":
                    break
                siblings.append(sib)

            text_parts = []
            for sib in siblings:
                if sib.name in ["p", "ul", "ol"]:
                    t = clean(sib.get_text())
                    if t and not is_ad_text(t):
                        text_parts.append(t)
                elif sib.name == "div":
                    # FJA section content ko <div> me wrap karta hai. Agar div me
                    # table hai to uski PROSE lo (table cells chhod kar) — chahe woh
                    # <p> me ho ya seedhe div me. Warna poora div text.
                    if sib.find("table"):
                        t = clean(" ".join(s for s in sib.find_all(string=True)
                                           if not s.find_parent("table")))
                    else:
                        t = clean(sib.get_text())
                    if t and not is_ad_text(t):
                        text_parts.append(t)

            def get_tables():
                tbls = []
                for sib in siblings:
                    if sib.name == "table":
                        tbls.append(sib)
                    elif sib.name == "div":
                        tbls.extend(sib.find_all("table"))
                return tbls

            if any(w in section_title for w in ["overview", "basic detail"]) and "vacancy" not in section_title:
                for tbl in get_tables():
                    _parse_overview_table(tbl, job)
                if not job["basic_details"].get("short_information") and text_parts:
                    job["basic_details"]["short_information"] = " ".join(text_parts[:2])

            elif (any(w in section_title for w in ["vacancy detail", "post detail", "vacancy 2",
                                                    "post wise", "post-wise"])
                  # FJA heading me "... Vacancy 2026" suffix hota hai jisse "vacancy 2"
                  # galat sections (Selection/Fee/Age/etc.) ko bhi match kar leta tha.
                  # Agar heading kisi aur section ka clear keyword rakhti hai to skip.
                  and not any(w in section_title for w in
                              ["selection", "how to apply", "application fee", "exam fee",
                               "age limit", "important date", "key date", "notification",
                               "admit card", "answer key", "syllabus", "exam pattern",
                               "salary", "pay scale", "pay band", "pay level",
                               "remuneration", "stipend", "emolument"])):
                for tbl in get_tables():
                    _parse_vacancy_table(tbl, job)
                # Bug 1 fix: multiple tables (company/category/PwD) ko unke header
                # ke hisaab se alag-alag breakdown me isolate karo (khichdi na bane)
                _breakdown = isolate_vacancy_tables(siblings, clean=clean)
                if _breakdown:
                    # merge + exact-duplicate rows skip (triple-clone fix)
                    merge_breakdown(job.setdefault("vacancy_breakdown", {}), _breakdown)
                # Miss fix: vacancy prose me ho (koi table nahi) to details rakho
                if not job["vacancy_details"] and not job.get("vacancy_breakdown") and text_parts:
                    job["vacancy_details"].append({"details": " ".join(text_parts)[:800]})

            elif any(w in section_title for w in ["important date", "key date", "schedule",
                                                   "important dates"]):
                for tbl in get_tables():
                    _parse_dates_table(tbl, job)
                if not get_tables() and text_parts:
                    job["important_dates"]["raw"] = " | ".join(text_parts)

            elif any(w in section_title for w in ["application fee", "exam fee", "fee detail",
                                                   "fee structure"]):
                for tbl in get_tables():
                    _parse_fee_table(tbl, job)
                if text_parts:
                    job["application_fee"]["details"] = " | ".join(text_parts)
                # "No application fee" note table-cell me ho to capture karo
                if not job["application_fee"]:
                    _sec = clean(" ".join(s.get_text(" ") for s in siblings))
                    if re.search(r"no\s+(?:application|exam(?:ination)?)?\s*fee|"
                                 r"fee\s*[:\-]?\s*nil|not\s+prescribed", _sec, re.IGNORECASE):
                        job["application_fee"]["details"] = "No application fee"

            elif "age" in section_title and "limit" in section_title:
                for tbl in get_tables():
                    _parse_age_table(tbl, job)
                if text_parts:
                    job["age_limit"]["details"] = " | ".join(text_parts)

            elif any(w in section_title for w in ["qualification", "eligibility", "education"]):
                for tbl in get_tables():
                    _parse_qualification_table(tbl, job)
                if text_parts:
                    job["qualification"]["details"] = " | ".join(text_parts)

            elif any(w in section_title for w in ["salary", "pay scale", "pay band",
                                                   "remuneration", "emolument", "stipend"]):
                for tbl in get_tables():
                    _parse_kv_to_dict(tbl, job["salary_details"])
                if text_parts:
                    job["salary_details"]["details"] = " | ".join(text_parts)

            elif any(w in section_title for w in ["selection process", "selection procedure",
                                                   "selection criteria"]):
                for tbl in get_tables():
                    for row in tbl.find_all("tr"):
                        txt = clean(row.get_text())
                        if txt and txt not in job["selection_process"]:
                            job["selection_process"].append(txt)
                for tp in text_parts:
                    for item in re.split(r"[,|•\n]", tp):
                        item = item.strip()
                        if item and item not in job["selection_process"]:
                            job["selection_process"].append(item)

            elif any(w in section_title for w in ["exam pattern", "test pattern"]):
                for tbl in get_tables():
                    rows = tbl.find_all("tr")
                    if rows:
                        hdrs = [clean(c.get_text()) for c in rows[0].find_all(["th", "td"])]
                        for row in rows[1:]:
                            cells = row.find_all("td")
                            entry = {hdrs[i]: clean(cells[i].get_text())
                                     for i in range(min(len(hdrs), len(cells))) if i < len(hdrs)}
                            if entry:
                                job["exam_pattern"].setdefault("pattern_table", []).append(entry)
                if text_parts:
                    job["exam_pattern"]["details"] = " | ".join(text_parts)

            elif "syllabus" in section_title:
                if text_parts:
                    job["syllabus"]["details"] = " | ".join(text_parts)

            elif any(w in section_title for w in ["physical", "pst", "pet"]):
                for tbl in get_tables():
                    _parse_kv_to_dict(tbl, job["physical_eligibility"])
                if text_parts:
                    job["physical_eligibility"]["details"] = " | ".join(text_parts)

            elif any(w in section_title for w in ["how to apply", "apply process",
                                                   "application process"]):
                for sib in siblings:
                    if sib.name in ["ol", "ul"]:
                        for li in sib.find_all("li"):
                            step = clean(li.get_text())
                            if step:
                                job["how_to_apply"].append(step)
                    elif sib.name == "p":
                        step = clean(sib.get_text())
                        if step:
                            job["how_to_apply"].append(step)
                    elif sib.name == "div":
                        # steps <div> ke andar ho sakte hain (ol/ul/p)
                        for el in sib.find_all(["ol", "ul", "p"]):
                            if el.name in ["ol", "ul"]:
                                for li in el.find_all("li"):
                                    step = clean(li.get_text())
                                    if step and step not in job["how_to_apply"]:
                                        job["how_to_apply"].append(step)
                            else:
                                step = clean(el.get_text())
                                if step and step not in job["how_to_apply"]:
                                    job["how_to_apply"].append(step)
                # Fallback: kuch structured nahi mila to prose text_parts hi le lo
                if not job["how_to_apply"] and text_parts:
                    for tp in text_parts:
                        if tp not in job["how_to_apply"]:
                            job["how_to_apply"].append(tp)

            elif any(w in section_title for w in ["important link", "useful link"]):
                for tbl in get_tables():
                    _parse_links_table(tbl, url, job)
                # ── IMPROVED: table ke bahar bhi links dhundo ──
                _scan_section_links(siblings, url, job)

            elif any(w in section_title for w in ["instruction", "rule", "note", "guideline"]):
                job["important_instructions"].extend(text_parts)

        # ── DYNAMIC MASTER CAPTURE ────────────────────────────
        # Har section ki saari tables (structured, titled, un-mixed) + text.
        # Naya table/section site kabhi add kare to yahan AUTO aa jayega.
        job["content_sections"] = extract_content_sections(content, clean=clean)

        # ── Bug 3 fix: age_limit / syllabus / qualification jab hard-table me
        #    nahi, sirf <p>/<ul> paragraphs me hote hain — heading-based fallback.
        if not job["age_limit"]:
            _age_txt = extract_section_text(content,
                ["age limit", "age criteria", "age relaxation", "upper age",
                 "lower age", "minimum age", "maximum age", "age as on"],
                clean=clean)
            if _age_txt:
                job["age_limit"]["details"] = _age_txt
        if not job["syllabus"]:
            _syl_txt = extract_section_text(content, ["syllabus"], clean=clean)
            if _syl_txt:
                job["syllabus"]["details"] = _syl_txt
        if not job["qualification"]:
            _qual_txt = extract_section_text(content,
                ["qualification", "eligibility", "educational"], clean=clean)
            if _qual_txt:
                job["qualification"]["details"] = _qual_txt

        # ── Fallback: last table links ────────────────────────
        all_tables = content.find_all("table")
        if not job["important_links"] and all_tables:
            _parse_links_table(all_tables[-1], url, job)

        # ── Scan ALL <a> for official links ───────────────────
        _scan_all_links(content, url, job)

        # ── short_information fallback ────────────────────────
        if not job["basic_details"].get("short_information"):
            for p in content.find_all("p"):
                txt = clean(p.get_text())
                if len(txt) > 40:
                    job["basic_details"]["short_information"] = txt[:600]
                    break

    except Exception as e:
        print(f"    [ERROR] {url} -> {e}")

    return job


# ============================================================
# TABLE PARSERS
# ============================================================
def _parse_overview_table(table, job: dict):
    FIELD_MAP = {
        "company name":         ("basic_details", "organization_name"),
        "organization name":    ("basic_details", "organization_name"),
        "organization":         ("basic_details", "organization_name"),
        "board name":           ("basic_details", "organization_name"),
        "authority":            ("basic_details", "organization_name"),
        "dept name":            ("basic_details", "organization_name"),
        "institute":            ("basic_details", "organization_name"),
        "department":           ("basic_details", "department"),
        "post name":            ("basic_details", "post_name"),
        "name of post":         ("basic_details", "post_name"),
        "post":                 ("basic_details", "post_name"),
        "no of posts":          ("basic_details", "total_vacancies"),
        "no. of posts":         ("basic_details", "total_vacancies"),
        "number of posts":      ("basic_details", "total_vacancies"),
        "total posts":          ("basic_details", "total_vacancies"),
        "total vacancy":        ("basic_details", "total_vacancies"),
        "total vacancies":      ("basic_details", "total_vacancies"),
        "no of vacancy":        ("basic_details", "total_vacancies"),
        "no. of vacancy":       ("basic_details", "total_vacancies"),
        "vacancies":            ("basic_details", "total_vacancies"),
        "vacancy":              ("basic_details", "total_vacancies"),
        "posts":                ("basic_details", "total_vacancies"),
        "application start date":     ("important_dates", "application_start_date"),
        "starting date":              ("important_dates", "application_start_date"),
        "last date":                  ("important_dates", "last_date_to_apply"),
        "last date to apply":         ("important_dates", "last_date_to_apply"),
        "last date to apply online":  ("important_dates", "last_date_to_apply"),
        "closing date":               ("important_dates", "last_date_to_apply"),
        "application last date":      ("important_dates", "last_date_to_apply"),
        "exam date":                  ("important_dates", "exam_date"),
        "date of exam":               ("important_dates", "exam_date"),
        "application mode":           ("basic_details", "application_mode"),
        "mode of apply":              ("basic_details", "application_mode"),
        "apply mode":                 ("basic_details", "application_mode"),
        "job location":               ("basic_details", "job_location"),
        "location":                   ("basic_details", "job_location"),
        "state":                      ("basic_details", "job_location"),
        "job type":                   ("basic_details", "job_type"),
        "employment type":            ("basic_details", "job_type"),
        "category":                   ("basic_details", "job_category"),
        "notification number":        ("basic_details", "notification_number"),
        "advt no":                    ("basic_details", "notification_number"),
        "advt. no":                   ("basic_details", "notification_number"),
        "advertisement no":           ("basic_details", "notification_number"),
        "qualification":              ("qualification", "education_qualification"),
        "education":                  ("qualification", "education_qualification"),
        "educational qualification":  ("qualification", "education_qualification"),
        "age limit":                  ("age_limit", "age_details"),
        "age":                        ("age_limit", "age_details"),
        "salary":                     ("salary_details", "pay_scale"),
        "pay scale":                  ("salary_details", "pay_scale"),
        "pay":                        ("salary_details", "pay_scale"),
        "stipend":                    ("salary_details", "pay_scale"),
        "selection process":          ("basic_details", "selection_process_brief"),
        "official website":           ("basic_details", "official_website"),
        "website":                    ("basic_details", "official_website"),
    }

    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            key = clean(cells[0].get_text()).lower().rstrip(":").strip()
            val = clean(cells[1].get_text())
            if not val:
                continue
            _ext = extended_date_field(key)   # extended/revised dates → own field
            if _ext:
                job["important_dates"][_ext] = val
                continue
            if key in FIELD_MAP:
                section, field = FIELD_MAP[key]
                if not job[section].get(field):
                    job[section][field] = val
            else:
                for map_key, (section, field) in FIELD_MAP.items():
                    if map_key in key:
                        if not job[section].get(field):
                            job[section][field] = val
                        break


def _parse_vacancy_table(table, job: dict):
    rows = table.find_all("tr")
    if not rows:
        return
    headers = [clean(c.get_text()) for c in rows[0].find_all(["th", "td"])]
    # Row de-dup: same table 2-3 baar parse ho to identical rows dobara na aayein
    _seen = {json.dumps(r, sort_keys=True, ensure_ascii=False)
             for r in job["vacancy_details"]}
    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue
        entry = {}
        for i, h in enumerate(headers):
            if i < len(cells):
                entry[h] = clean(cells[i].get_text())
        if any(entry.values()):
            _k = json.dumps(entry, sort_keys=True, ensure_ascii=False)
            if _k not in _seen:
                _seen.add(_k)
                job["vacancy_details"].append(entry)

    cat_keys = [h for h in headers if any(w in h.lower() for w in
                ["ur", "obc", "sc", "st", "ews", "general", "unreserved", "pwd", "ph", "ex-servicemen"])]
    if cat_keys:
        for row_entry in job["vacancy_details"]:
            for k in cat_keys:
                if row_entry.get(k):
                    job["category_wise_vacancy"][k] = row_entry[k]


def _parse_dates_table(table, job: dict):
    DATE_MAP = {
        "start date":                  "application_start_date",
        "starting date":               "application_start_date",
        "opening date":                "application_start_date",
        "commencement":                "application_start_date",
        "last date":                   "last_date_to_apply",
        "closing date":                "last_date_to_apply",
        "end date":                    "last_date_to_apply",
        "last date to apply":          "last_date_to_apply",
        "last date to apply online":   "last_date_to_apply",
        "last date for apply":         "last_date_to_apply",
        "last date to submit":         "last_date_to_apply",
        "application last date":       "last_date_to_apply",
        "exam date":                   "exam_date",
        "date of exam":                "exam_date",
        "written exam":                "exam_date",
        "admit card":                  "admit_card_date",
        "hall ticket":                 "admit_card_date",
        "result":                      "result_date",
        "interview":                   "interview_date",
        "interview date":              "interview_date",
        "payment of fee":              "fee_payment_last_date",
        "fee payment":                 "fee_payment_last_date",
        "correction":                  "correction_date",
        "edit":                        "correction_date",
    }

    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            key = clean(cells[0].get_text()).lower().rstrip(":").strip()
            val = clean(cells[1].get_text())
            if not val:
                continue
            # Extended/revised/postponed dates → own field (never swallowed by the
            # generic 'last date' match; latest value wins). Renders distinctly.
            _ext = extended_date_field(key)
            if _ext:
                job["important_dates"][_ext] = val
                continue
            matched = False
            for map_key, field in DATE_MAP.items():
                if map_key in key:
                    if not job["important_dates"].get(field):
                        job["important_dates"][field] = val
                    matched = True
                    break
            if not matched:
                job["important_dates"][key] = val


def _parse_fee_table(table, job: dict):
    FEE_MAP = {
        "general":       "general_fee",
        "unreserved":    "general_fee",
        "ur":            "general_fee",
        "all applicant": "general_fee",
        "all candidate": "general_fee",
        "all categor":   "general_fee",
        "all post":      "general_fee",
        "everyone":      "general_fee",
        "obc":           "obc_fee",
        "sc":            "sc_fee",
        "st":            "st_fee",
        "ews":           "ews_fee",
        "pwbd":          "pwd_fee",
        "pwd":           "pwd_fee",
        "ph":            "pwd_fee",
        "divyang":       "pwd_fee",
        "female":        "female_fee",
        "women":         "female_fee",
        "payment mode":  "payment_mode",
        "mode of pay":   "payment_mode",
        "mode":          "payment_mode",
    }
    SKIP = {"category", "categories", "sl", "sl no", "s.no", "sl. no.", "fee",
            "exam stage", "stage", "sr", "sr no", "sr. no.", "#", ""}
    fee = job["application_fee"]
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            key = clean(cells[0].get_text()).lower().rstrip(":").strip()
            val = clean(cells[1].get_text())
            if not val:
                continue
            matched = False
            for map_key, field in FEE_MAP.items():
                # word-boundary: "st" ab "stage"/"estate" me galat match nahi karega
                if re.search(r"\b" + re.escape(map_key) + r"\b", key):
                    if not fee.get(field):
                        fee[field] = val
                    matched = True
                    break
            # Catch-all: koi bhi valued fee-row drop na ho (All Applicants/PwBD/etc.)
            if not matched and key not in SKIP:
                slug = re.sub(r"[^a-z0-9]+", "_", key).strip("_")[:30]
                if slug:
                    fee.setdefault(slug if slug.endswith("fee") else slug + "_fee", val)


def _parse_age_table(table, job: dict):
    AGE_MAP = {
        "minimum age":    "minimum_age",
        "min age":        "minimum_age",
        "maximum age":    "maximum_age",
        "max age":        "maximum_age",
        "upper age":      "maximum_age",
        "lower age":      "minimum_age",
        "age limit":      "age_details",
        "age relaxation": "age_relaxation",
        "relaxation":     "age_relaxation",
        "age as on":      "age_as_on",
        "as on":          "age_as_on",
    }
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            key = clean(cells[0].get_text()).lower().rstrip(":").strip()
            val = clean(cells[1].get_text())
            if not val:
                continue
            for map_key, field in AGE_MAP.items():
                if map_key in key:
                    if not job["age_limit"].get(field):
                        job["age_limit"][field] = val
                    break


def _parse_qualification_table(table, job: dict):
    """
    Universal qualification table parser — 3 formats handle karta hai:

    Format A — 2-column KV (e.g. BBMB overview table):
      | Qualification | 10th + ITI |

    Format B — Multi-column post-wise table (e.g. A&N CHSL):
      | Post Name | Essential Qualification | Desirable |
      | Forester  | 12th Science + ...      | Nil       |

    Format C — Single-column list (qualification described in rows/paragraphs):
      | Must have passed 12th from recognized board... |
    """
    QUAL_MAP = {
        "qualification":   "education_qualification",
        "educational":     "education_qualification",
        "education":       "education_qualification",
        "required degree": "required_degree",
        "degree":          "required_degree",
        "experience":      "experience",
        "domicile":        "domicile",
        "nationality":     "nationality",
        "citizen":         "nationality",
    }

    rows = table.find_all("tr")
    if not rows:
        return

    # ── Header detection ─────────────────────────────────────
    # Header row ke columns dekho — format decide karne ke liye
    header_row = rows[0]
    header_cells = header_row.find_all(["th", "td"])
    headers = [clean(c.get_text()).lower() for c in header_cells]

    # ── QUAL keywords jo column headers mein indicate karte hain multi-col format ──
    QUAL_HEADER_WORDS = ["qualification", "educational", "eligib", "education",
                         "essential", "requirement", "degree", "criteria"]
    POST_HEADER_WORDS = ["post", "position", "name of post", "post name"]

    has_qual_col  = any(any(w in h for w in QUAL_HEADER_WORDS) for h in headers)
    has_post_col  = any(any(w in h for w in POST_HEADER_WORDS) for h in headers)
    is_multicolumn = len(headers) >= 3 and (has_qual_col or has_post_col)
    is_kv_table    = len(headers) == 2

    # ── Format B: Multi-column post-wise table ────────────────
    if is_multicolumn:
        # Find qual column index (first column whose header has qual keywords)
        qual_col_idx = None
        post_col_idx = None
        desirable_col_idx = None
        for i, h in enumerate(headers):
            if any(w in h for w in QUAL_HEADER_WORDS) and qual_col_idx is None:
                qual_col_idx = i
            if any(w in h for w in POST_HEADER_WORDS) and post_col_idx is None:
                post_col_idx = i
            if "desirable" in h and desirable_col_idx is None:
                desirable_col_idx = i

        # Fallback: agar header se nahi mila to column 1 (index 1) use karo
        if qual_col_idx is None:
            qual_col_idx = 1
        if post_col_idx is None:
            post_col_idx = 0

        post_qual_list = []
        raw_parts      = []

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            # Grand total / summary rows skip karo
            row_text = clean(row.get_text()).lower()
            if re.search(r'^grand\s+total|^total\s*$', row_text):
                continue

            post_val  = clean(cells[post_col_idx].get_text())  if post_col_idx  < len(cells) else ""
            qual_val  = clean(cells[qual_col_idx].get_text())  if qual_col_idx  < len(cells) else ""
            desirable = ""
            if desirable_col_idx is not None and desirable_col_idx < len(cells):
                desirable = clean(cells[desirable_col_idx].get_text())

            if not qual_val or qual_val.lower() in ("nil", "-", "—", "n/a", "na"):
                continue

            entry = {}
            if post_val:
                entry["post_name"] = post_val
            entry["essential_qualification"] = qual_val
            if desirable and desirable.lower() not in ("nil", "-", "—", "n/a", "na"):
                entry["desirable"] = desirable

            post_qual_list.append(entry)

            # raw text ke liye bhi collect karo — _verify_qualification_match ke liye
            raw_parts.append(f"{post_val}: {qual_val}" if post_val else qual_val)

        if post_qual_list:
            # post_wise_qualification mein structured data save karo
            existing = job["qualification"].get("post_wise_qualification", [])
            existing.extend(post_qual_list)
            job["qualification"]["post_wise_qualification"] = existing

            # details mein flat text bhi rakho — keyword matching ke liye
            combined = " | ".join(raw_parts)
            if job["qualification"].get("details"):
                job["qualification"]["details"] += " | " + combined
            else:
                job["qualification"]["details"] = combined

        return  # Multi-col processed — aage nahi jaana

    # ── Format A: 2-column KV table ───────────────────────────
    if is_kv_table or not is_multicolumn:
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = clean(cells[0].get_text()).lower().rstrip(":").strip()
                val = clean(cells[1].get_text())
                if not val:
                    continue
                matched = False
                for map_key, field in QUAL_MAP.items():
                    if map_key in key:
                        if not job["qualification"].get(field):
                            job["qualification"][field] = val
                        matched = True
                        break
                # KV match nahi hua but value meaningful hai — details mein append karo
                if not matched and val and key not in ("sl no", "sl.", "s.no", "#"):
                    existing = job["qualification"].get("details", "")
                    new_part = f"{key}: {val}" if key else val
                    job["qualification"]["details"] = (existing + " | " + new_part).strip(" |") if existing else new_part

            # ── Format C: Single-column meaningful text ───────
            elif len(cells) == 1:
                val = clean(cells[0].get_text())
                # Header-like rows skip karo
                if not val or len(val) < 10 or val.lower() in headers:
                    continue
                # Qualification-related text hona chahiye
                qual_words = ["pass", "degree", "diploma", "graduate", "12th", "10th",
                              "iti", "b.tech", "mbbs", "b.sc", "certificate", "recognized"]
                if any(w in val.lower() for w in qual_words):
                    existing = job["qualification"].get("details", "")
                    job["qualification"]["details"] = (existing + " | " + val).strip(" |") if existing else val


def _parse_kv_to_dict(table, target_dict: dict):
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            key = clean(cells[0].get_text()).lower().rstrip(":").strip()
            val = clean(cells[1].get_text())
            if key and val and not target_dict.get(key):
                target_dict[key] = val


# Link type → human-readable default label mapping
_LINK_TYPE_LABELS = {
    "apply_online":    "Apply Online",
    "notification_pdf":"Official Notification PDF",
    "official_website":"Official Website",
    "admit_card":      "Admit Card",
    "result":          "Result",
    "syllabus_pdf":    "Syllabus PDF",
    "answer_key":      "Answer Key",
    "cut_off":         "Cut Off",
    "login":           "Login",
    "apply_offline":   "Apply Offline",
    "other":           "Official Link",
}

# Anchor text jo generic/useless hain
_GENERIC_ANCHOR_TEXTS = {
    "click here", "here", "link", "click", "download", "view", "open",
    "official link", "check here", "see here", "visit here", "apply",
    "read more", "more details", "details", "official", "go here", "visit",
    # "Click Here to Apply" style generic anchor texts
    "click here to apply", "click here to download", "click here to view",
    "click here to check", "click here to register", "click here to login",
    "click here to access", "apply here", "apply now", "apply online",
    "download here", "view here", "register here",
    "click here for details", "click here for more", "click here to open",
}


def _best_link_label(anchor_text: str, context_text: str, href: str, anchor_tag=None) -> str:
    """
    Ek meaningful label return karo har link ke liye.
    Priority:
    1. anchor_text (agar generic nahi hai)
    2a. anchor_tag se <li> parent label extract karo (colon separator pattern)
    2b. context_text se meaningful portion (table row_label ya sibling text)
    3. URL pattern se derive karo
    4. link_type label fallback

    anchor_tag (optional): BeautifulSoup <a> element — <li> parent se label nikalne ke liye.
    """
    # 1. Anchor text use karo agar meaningful hai
    a = anchor_text.strip()
    if a and a.lower() not in _GENERIC_ANCHOR_TEXTS and 2 < len(a) <= 80:
        return a[:100]

    # 2a. <li> parent se label extract karo
    #     Pattern: <li>Label Text: <a>Click here</a></li>
    if anchor_tag is not None:
        li_parent = anchor_tag.find_parent("li")
        if li_parent:
            li_full_text = li_parent.get_text(" ", strip=True)
            anchor_str = anchor_tag.get_text(" ", strip=True)
            li_label = li_full_text.replace(anchor_str, "").strip().rstrip(":").strip().rstrip("\u00a0").strip()
            if ":" in li_label:
                li_label = li_label.split(":")[0].strip()
            if li_label and li_label.lower() not in _GENERIC_ANCHOR_TEXTS and len(li_label) > 2:
                return li_label[:100]

    # 2b. context_text se meaningful label extract karo (table row ya sibling text)
    ctx = context_text.strip()
    if ctx and len(ctx) > 2:
        if ":" in ctx:
            candidate = ctx.split(":")[0].strip()
        else:
            candidate = ctx.split("\n")[0].strip()
        if candidate and candidate.lower() not in _GENERIC_ANCHOR_TEXTS and 2 < len(candidate) <= 80:
            return candidate[:100]

    # 3. URL pattern se derive karo
    hl = href.lower()
    if "apply" in hl and "offline" not in hl:
        return "Apply Online"
    if "notification" in hl or "advt" in hl or "advertisement" in hl:
        return "Official Notification PDF" if ".pdf" in hl else "Official Notification"
    if "syllabus" in hl:
        return "Syllabus PDF" if ".pdf" in hl else "Syllabus"
    if "admit" in hl or "hallticket" in hl or "hall_ticket" in hl:
        return "Admit Card"
    if "result" in hl:
        return "Result"
    if "answer" in hl and "key" in hl:
        return "Answer Key"
    if "cutoff" in hl or "cut_off" in hl or "cut-off" in hl:
        return "Cut Off"
    if ".pdf" in hl:
        return "Official PDF Document"
    if "login" in hl:
        return "Login"
    if "register" in hl or "registration" in hl:
        return "Registration Link"

    # 4. link_type fallback
    ltype = classify_link(anchor_text, href)
    return _LINK_TYPE_LABELS.get(ltype, "Official Link")


def _parse_links_table(table, base_url: str, job: dict):
    """Important Links table — ONLY official/govt links."""
    lk = job["important_links"]
    for row in table.find_all("tr"):
        # Row ke td/th se context label nikalo (left col = label, right col = link)
        cells = row.find_all(["td", "th"])
        row_label = ""
        if len(cells) >= 2:
            row_label = clean(cells[0].get_text())
        for a in row.find_all("a", href=True):
            href = resolve_href(base_url, a["href"])
            text = clean(a.get_text())

            if not is_valid_official_link(href, text):
                continue

            anchor_label = _best_link_label(text, row_label, href, anchor_tag=a)
            link_type = classify_link(text, href)
            link_key  = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60] or link_type
            _add_link(lk, link_key if link_type == "other" else link_type, href, label=anchor_label)


def _scan_section_links(siblings, base_url: str, job: dict):
    """
    Important Links section ke sibling elements mein bhi links dhundo
    (table ke bahar ke divs/paragraphs mein).
    """
    lk = job["important_links"]
    for sib in siblings:
        for a in sib.find_all("a", href=True):
            href = resolve_href(base_url, a["href"])
            text = clean(a.get_text())
            if not is_valid_official_link(href, text):
                continue
            parent_text = clean(a.parent.get_text()) if a.parent else ""
            anchor_label = _best_link_label(text, parent_text, href, anchor_tag=a)
            link_type = classify_link(text, href)
            link_key  = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60] or link_type
            _add_link(lk, link_key if link_type == "other" else link_type, href, label=anchor_label)


def _scan_all_links(content, base_url: str, job: dict):
    """Page ke sabhi <a> scan — official/job-related links lo (a-to-z).
    Classified types + koi bhi official .pdf / gov link bhi preserve karo
    taaki notification/form jaise links miss na ho."""
    lk = job["important_links"]
    extra = job.setdefault("all_official_links", [])
    seen = {e["url"] for e in extra if isinstance(e, dict)}  # FIX: dict se url extract karo
    for a in content.find_all("a", href=True):
        href = resolve_href(base_url, a["href"]).split("#")[0]
        text = clean(a.get_text())

        if not is_valid_official_link(href, text):
            continue

        parent_text = clean(a.parent.get_text()) if a.parent else ""
        anchor_label = _best_link_label(text, parent_text, href, anchor_tag=a)

        link_type = classify_link(text, href)
        if link_type in ["apply_online", "notification_pdf", "official_website",
                         "admit_card", "result", "syllabus_pdf", "answer_key", "cut_off"]:
            if not lk.get(link_type):
                _add_link(lk, link_type, href, label=anchor_label)
        # generic official link (PDF / gov / nic / ac.in) — preserve in all_official_links
        hl = href.lower()
        if (".pdf" in hl or ".gov" in hl or "nic.in" in hl or "ac.in" in hl
                or "org.in" in hl) and href not in seen:
            seen.add(href)
            extra.append({"label": anchor_label, "url": href})


# ============================================================
# INTERNET WAIT
# ============================================================
def _wait_for_net_reconnect(max_wait=300):
    """Internet wapas aane tak wait karo (network disconnect pe call hoti hai).
    Simple exponential backoff — 5s intervals tak 5 min tak."""
    import urllib.request as _ur
    import time as _t
    waited = 0
    interval = 5
    print("  [NET] Internet nahi hai. Dobara try kar raha hoon...")
    while waited < max_wait:
        try:
            _ur.urlopen("https://www.google.com", timeout=5)
            print(f"  [NET] Internet wapas aa gaya! ({waited}s baad)")
            return
        except Exception:
            _t.sleep(interval)
            waited += interval
            if waited % 30 == 0:
                print(f"  [NET] Abhi bhi nahi... ({waited}s wait ho gaya)")
    print("  [NET] 5 minute ho gaye, internet nahi aaya. Skip kar raha hoon.")


def _wait_for_internet(session, check_url="https://www.freejobalert.com", max_wait=300,
                       attempt_num=1):
    """
    FIXED: Pehle Google se check — neutral URL.
    Agar Google chale lekin freejobalert na chale = rate-limit.
    Progressive wait: attempt 1=150s, 2=210s, 3=270s — server pe load kam karo.
    """
    import urllib.request as _ur
    for nurl in ["https://www.google.com", "https://httpbin.org/get"]:
        try:
            _ur.urlopen(nurl, timeout=5)
            # Progressive wait based on attempt number
            base_wait   = 150
            extra_wait  = (attempt_num - 1) * 60   # 0, 60, 120
            total_wait  = min(base_wait + extra_wait, 300)
            print(f"\n  [NET] Google accessible — freejobalert rate-limit hoga.")
            print(f"  [NET] {total_wait}s wait kar raha hoon (attempt {attempt_num})...")
            smart_delay("crawl", extra=total_wait - 5)
            return True
        except Exception:
            pass
    print("\n  [NET] Internet nahi hai. Dobara try kar raha hoon...")
    waited = 0
    while waited < max_wait:
        smart_delay("slow", extra=12)
        waited += 15
        try:
            r = session.get(check_url, timeout=10)
            if r.status_code < 500:
                print(f"  [NET] Internet wapas aa gaya! ({waited}s baad)")
                return True
        except Exception:
            print(f"  [NET] Abhi bhi nahi... ({waited}s wait ho gaya)")
    print("  [NET] 5 minute ho gaye, internet nahi aaya. Skip kar raha hoon.")
    return False


# ============================================================
# SAVE
# ============================================================
def _strip_aws_keys(obj):
    """
    JSON object (dict/list/str) mein se Amazon AWS Access Key IDs remove karo.
    Pattern: AKIA[0-9A-Z]{16}  — yeh S3 presigned URLs mein embedded hoti hai.
    Baaki saara data same rehta hai — sirf key string redact hoti hai.
    """
    import re as _re
    AWS_KEY_PATTERN = _re.compile(r'AKIA[0-9A-Z]{16}')
    if isinstance(obj, dict):
        return {k: _strip_aws_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_strip_aws_keys(item) for item in obj]
    elif isinstance(obj, str):
        return AWS_KEY_PATTERN.sub("REMOVED", obj)
    return obj


def _normalize_links(job: dict):
    """
    important_links dict ko normalize karo:
    {key: url_str, _labels: {key: label}} ->
    {key: {url: ..., label: ...}}
    """
    lk = job.get("important_links", {})
    if not lk:
        return
    labels = lk.pop("_labels", {}) or {}
    normalized = {}
    for k, v in lk.items():
        label = labels.get(k, _LINK_TYPE_LABELS.get(k, "Official Link"))
        if isinstance(v, str) and v:
            normalized[k] = {"url": v, "label": label}
        elif isinstance(v, list):
            normalized[k] = [{"url": u, "label": label} for u in v if u]
    job["important_links"] = normalized

    # all_official_links ensure {label, url} format
    aol = job.get("all_official_links", [])
    cleaned_aol = []
    for entry in aol:
        if isinstance(entry, dict) and entry.get("url"):
            if "label" not in entry:
                entry["label"] = _best_link_label("", "", entry["url"])
            cleaned_aol.append(entry)
        elif isinstance(entry, str) and entry:
            cleaned_aol.append({"url": entry, "label": _best_link_label("", "", entry)})
    job["all_official_links"] = cleaned_aol


def _save_json(all_json: dict):
    # Sirf ek clean output file — _scraped_from strip karke + AWS keys remove
    clean_json = {}
    for cat, jobs in all_json.items():
        clean_jobs = []
        for job in jobs:
            j = {k: v for k, v in job.items() if k not in ("_scraped_from", "_last_checked")}
            _normalize_links(j)
            clean_jobs.append(j)
        clean_json[cat] = clean_jobs
    clean_json = _strip_aws_keys(clean_json)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(clean_json, f, indent=2, ensure_ascii=False)


# ============================================================
# PARALLEL JOB SCRAPER
# ============================================================
def _scrape_job_with_retry(session_factory, url: str) -> dict:
    """Thread-safe job scraping with retries. Internet cut ho toh wait karo."""
    session = session_factory()
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            data = extract_job_page(session, url)
            smart_delay("fast")
            return data
        except Exception as e:
            err = str(e)
            is_net = ("ConnectionError" in err or "Max retries" in err
                      or "NameResolution" in err or "RemoteDisconnected" in err
                      or "NewConnectionError" in err or "timed out" in err.lower())
            if is_net:
                # Internet cut ho gaya — wait karo wapas aane tak
                _wait_for_net_reconnect()
                session = session_factory()   # fresh session banana
                print(f"    [NET-RETRY] {url[-60:]}")
            elif attempt < MAX_RETRIES:
                print(f"    [RETRY {attempt}] {url[-60:]}")
                smart_delay("slow", extra=8 * attempt)
            else:
                print(f"    [FAIL] {url[-60:]} -> {e}")
                break
    return None


def _is_empty_job(job: dict) -> bool:
    """
    Job page se kuch meaningful data scrape nahi hua — likely ek listing/state page tha.
    Agar basic info bhi nahi hai toh skip karo.
    """
    bd = job.get("basic_details", {})
    has_org     = bool(bd.get("organization_name") or bd.get("post_name"))
    has_vacancy = bool(bd.get("total_vacancies") or job.get("vacancy_details"))
    has_dates   = bool(job.get("important_dates"))
    has_links   = bool(job.get("important_links"))
    has_fee     = bool(job.get("application_fee"))
    has_age     = bool(job.get("age_limit"))

    meaningful = sum([has_org, has_vacancy, has_dates, has_links, has_fee, has_age])
    return meaningful < 2  # 2 se kam fields = junk page
    return {
        "basic_details": {}, "important_dates": {}, "application_fee": {},
        "age_limit": {}, "qualification": {}, "vacancy_details": [],
        "category_wise_vacancy": {}, "salary_details": {}, "selection_process": [],
        "exam_pattern": {}, "syllabus": {}, "physical_eligibility": {},
        "how_to_apply": [], "important_instructions": [], "important_links": {},
        "faq": [],
    }


# ============================================================
# MAIN
# ============================================================
def scrape_all():
    global _global_seen_urls

    # ── RESUME ───────────────────────────────────────────────
    if os.path.exists(JSON_PATH):
        print(f"[RESUME] Pehle ka data mila: {JSON_PATH}")
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            all_json = json.load(f)

        # Purane junk/empty jobs clean karo (jo pehle versions mein slip through ho gayi thi)
        cleaned_count = 0
        for cat in all_json:
            before = len(all_json[cat])
            all_json[cat] = [j for j in all_json[cat] if not _is_empty_job(j)]
            cleaned_count += before - len(all_json[cat])
        if cleaned_count:
            print(f"[RESUME] {cleaned_count} empty/junk jobs removed from existing data")
            _save_json(all_json)

        _global_seen_urls = set()
        for cat_jobs in all_json.values():
            for j in cat_jobs:
                if j.get("_scraped_from"):
                    _global_seen_urls.add(j["_scraped_from"])
        print(f"[RESUME] {len(_global_seen_urls)} URLs already scraped.")
    else:
        all_json           = {}
        _global_seen_urls  = set()

    # Session factory — parallel threads ke liye alag sessions
    def make_session():
        s = requests.Session()
        s.headers.update(HEADERS)
        return s

    main_session = make_session()
    total_categories = len(CATEGORIES)
    consecutive_empty = 0   # Kitni consecutive categories mein 0 links mile

    for cat_idx, (label, base_url) in enumerate(CATEGORIES.items(), 1):
        print(f"\n{'='*60}")
        print(f" CATEGORY [{cat_idx}/{total_categories}]: {label}")
        print(f" URL: {base_url}")
        print(f"{'='*60}")

        # ── Inter-category delay — server pe load mat daalo ─────────
        # NOTE: 697 districts hain (qualification scraper ke 37 categories
        # se bohot zyada), isliye delay profile lighter rakha hai —
        # warna sirf delays mein hi 3+ ghante nikal jayenge.
        if cat_idx > 1:
            if consecutive_empty >= 5:
                # 5+ GENUINE consecutive failures (network/block) = lamba wait
                wait_s = 60 + (consecutive_empty - 5) * 20
                wait_s = min(wait_s, 180)
                print(f" [THROTTLE] {consecutive_empty} consecutive failures"
                      f" — {wait_s}s wait kar raha hoon...")
                smart_delay("crawl", extra=wait_s - 5)
            else:
                # Normal inter-category gap: ~2-4s (district scale ke liye)
                smart_delay("normal", extra=1.5)

        all_json.setdefault(label, [])
        # Already scraped URLs for THIS category (URL → item map for carry-forward)
        existing_by_url = {j.get("_scraped_from"): j for j in all_json[label] if j.get("_scraped_from")}
        existing_urls   = set(existing_by_url.keys())
        print(f" Already scraped: {len(existing_urls)} jobs")

        # ── Collect ALL links (no global-seen filter here) ────
        links = []
        confirmed_empty = False
        for attempt in range(1, 4):
            print(f" -> Collecting job links (attempt {attempt})...")
            links, confirmed_empty = collect_all_job_links(main_session, base_url, label)
            if links:
                break
            # Site ne confirm kar diya koi job nahi — retry + wait bilkul waste
            if confirmed_empty:
                print(f" [SKIP] Category genuinely empty on site — no retry needed.")
                break
            ok = _wait_for_internet(main_session, base_url, attempt_num=attempt)
            if not ok:
                break

        # ── ORDER-PRESERVING INCREMENTAL SCRAPE (Issue 2 Fix) ─────────────────
        # ROOT CAUSE FIX: Pehle _flush_results() naye items ko existing items ke
        # BAAD append karta tha, jisse website ka live order tod jaata tha.
        # FIX: `links` (website listing order) ko master sequence maano.
        # RE-SCRAPE-ON-UPDATE: fetch new URLs + already-scraped ACTIVE jobs due for
        # a re-check (needs_refresh) so source updates (date extension/corrigendum)
        # are captured. Expired jobs are never re-fetched.
        def _should_scrape(u):
            old = existing_by_url.get(u)
            return old is None or needs_refresh(old)
        new_links = [l for l in links if _should_scrape(l)]
        print(f" -> Total links found : {len(links)}")
        print(f" -> To fetch (new + active re-check): {len(new_links)}")

        # Consecutive rate-limit tracker update
        # confirmed_empty = genuine district with no jobs — not a block signal
        if not links and not confirmed_empty:
            consecutive_empty += 1
        else:
            consecutive_empty = 0   # Reset on success OR genuine-empty district

        # Build ordered_rows in exact website sequence
        ordered_rows = []
        for lnk in links:
            if lnk in existing_urls and not needs_refresh(existing_by_url.get(lnk)):
                ordered_rows.append((lnk, "carry"))
            else:
                ordered_rows.append((lnk, "new"))

        if not new_links:
            # No new jobs — rebuild category in website order using carry-forwards
            if links:
                all_json[label] = [existing_by_url[u] for u, _ in ordered_rows if u in existing_by_url]
                _save_json(all_json)
            print(f" [SKIP] No new jobs for {label}")
            continue

        # ── Parallel fetch of new URLs only ──────────────────
        results_by_url = {}
        done_count     = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {
                executor.submit(_scrape_job_with_retry, make_session, url): url
                for url in new_links
            }

            for future in as_completed(future_map):
                job_url    = future_map[future]
                done_count += 1

                try:
                    data = future.result()
                except Exception as e:
                    print(f"   [FUTURE ERROR] {job_url[-60:]} -> {e}")
                    data = None

                if data is None:
                    data = _empty_job()

                # Junk/empty pages skip karo
                if _is_empty_job(data):
                    print(f"   [{done_count:04d}/{len(new_links)}] ⚠ SKIP (empty) {job_url[-70:]}")
                    with _seen_lock:
                        _global_seen_urls.add(job_url)
                    continue

                data["category"]      = label
                data["_scraped_from"] = job_url
                data["_last_checked"] = now_iso()
                _post_process_job(data, label)
                results_by_url[job_url] = data

                with _seen_lock:
                    _global_seen_urls.add(job_url)

                print(f"   [{done_count:04d}/{len(new_links)}] ✓ {job_url[-70:]}")

                if done_count % 10 == 0:
                    _save_json(all_json)
                    print(f"    [AUTO-SAVE] {done_count} done → {JSON_PATH}")

        # ── Rebuild category in EXACT WEBSITE ROW ORDER ────────────────────────
        final_items = []
        for url, kind in ordered_rows:
            if kind == "carry":
                item = existing_by_url.get(url)
            else:
                # keep old data if a re-fetch of an existing job failed/empty
                item = results_by_url.get(url) or existing_by_url.get(url)
            if item:
                final_items.append(item)

        all_json[label] = final_items
        _save_json(all_json)
        print(f" ✓ {label} COMPLETE — Total: {len(all_json[label])} jobs saved")

    # ── FINAL SAVE ────────────────────────────────────────────
    _save_json(all_json)
    _print_summary(all_json)
    # (Qualification_Wise_Jobs.json generation removed — not applicable
    # for district-wise scraper.)



def _flush_results(all_json: dict, label: str, results_ordered: list):
    """Non-None results ko all_json mein append karo."""
    existing = {j.get("_scraped_from") for j in all_json[label]}
    for data in results_ordered:
        if data is not None and data.get("_scraped_from") not in existing:
            all_json[label].append(data)
            existing.add(data["_scraped_from"])


def _print_summary(all_json: dict):
    print(f"\n{'='*60}")
    print(f" SCRAPING COMPLETE - SUMMARY")
    print(f"{'='*60}")
    total = 0
    for label, jobs in all_json.items():
        meta = DISTRICT_META.get(label, {})
        tag = f" ({meta.get('state', '')})" if meta else ""
        print(f"  {label:30s}{tag}: {len(jobs):5d} jobs")
        total += len(jobs)
    print(f"{'='*60}")
    print(f"  {'TOTAL':30s}: {total:5d} jobs")
    print(f"  Districts covered : {len(all_json)} / {len(CATEGORIES)}")
    print(f"  JSON (output)   -> {OUTPUT_JSON_PATH}")
    print(f"  ✅ source_url (scraper site) JSON mein nahi hai")
    print(f"  ✅ Sirf official links (Apply, Notification, Result, etc.)")
    print(f"  ✅ App/download links filtered")
    print(f"  ✅ Parallel scraping ({MAX_WORKERS} workers)")
    print(f"  ✅ 'No Jobs' page detection — empty districts auto-skipped")
    print(f"  ✅ job_location/state/district set from DISTRICT_META (697 districts, 30 states/UTs)")


# ================================================================


# ================================================================
# MERGE INTO UNIFIED JSON
# ================================================================
if __name__ == "__main__":
    from scraper_merge import merge_into_json, wait_for_internet
    import json as _json_mod, os

    wait_for_internet("FreeJobAlert")

    print("\n" + "="*60)
    print("  SCRAPER: FreeJobAlert District-Wise Jobs")
    print("="*60)

    error_str = ""
    try:
        scrape_all()   # saves to _temp_district.json
    except Exception as e:
        import traceback; traceback.print_exc()
        error_str = str(e)

    # Temp file se district dict load karo
    scraped = {}
    if os.path.exists("_temp_district.json"):
        with open("_temp_district.json", encoding="utf-8") as f:
            scraped = _json_mod.load(f)
        # Temp file clean up
        os.remove("_temp_district.json")

    merge_into_json(
        source        = "freejobalert_district",
        fresh_data    = scraped,
        scraper_error = error_str,
    )
