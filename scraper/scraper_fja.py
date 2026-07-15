#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================================
# SCRAPER: FreeJobAlert Categories — scraper_fja.py
# ================================================================
# Source  : freejobalert.com (qualification/category jobs)
# Writes  : _temp_fja.json  (raw FJA category dict)
# Output  : Updates "freejobalert_categories" in Complete_Jobs_Full_Data.json
#           Baaki teen sources (sarkari, education, state) UNCHANGED rehte hain.
#
# Run:  python scraper_fja.py
# ================================================================

import sys
sys.stdout.reconfigure(encoding="utf-8")

# ================================================================
# SOURCE 1: FREEJOBALERT CATEGORIES (Free_Job_Complete_v12)
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
# VERSION: v11
# FIXES vs v10:
#   CRITICAL FIX: QUAL_STRICT_CATEGORIES ab sirf v9 ke 37 NAYI
#   categories tak limited hai.
#   OLD categories (10TH_Pass, 8TH_Pass, 12TH_Pass, Diploma, ITI,
#   B_Tech_BE, B_Com, Any_Graduate, Any_Post_Graduate, Railway_Jobs,
#   Bank_Jobs, etc.) par strict qualification check NAHI lagega —
#   unhe pehle ki tarah normally scrape kiya jayega.
#
# v10 se:
#   Qualification-based categories ke liye STRICT VERIFICATION:
#   - Scraped job page ke Qualification section mein EXACT keyword
#     hona chahiye tabhi accept karo, warna SKIP
#   "No jobs" page detection:
#   - "There are no jobs in..." ya similar message mile toh skip
# v9 se:
#   37 nayi qualification-based CATEGORIES add ki gayi hain
#   QUAL_KEYWORDS dict for keyword matching
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

# ── Categories ──────────────────────────────────────────────
CATEGORIES = {
    # ── Existing categories ──────────────────────────────────
    "10TH_Pass":            "https://www.freejobalert.com/search-jobs/10th-pass-government-jobs/",
    "8TH_Pass":             "https://www.freejobalert.com/search-jobs/8th-pass-government-jobs/",
    "12TH_Pass":            "https://www.freejobalert.com/search-jobs/12th-pass-government-jobs/",
    "Diploma":              "https://www.freejobalert.com/search-jobs/diploma-government-jobs/",
    "ITI":                  "https://www.freejobalert.com/search-jobs/iti-government-jobs/",
    "B_Tech_BE":            "https://www.freejobalert.com/search-jobs/btech-be-government-jobs/",
    "B_Com":                "https://www.freejobalert.com/search-jobs/bcom-government-jobs/",
    "Any_Graduate":         "https://www.freejobalert.com/search-jobs/any-graduate-government-jobs/",
    "Any_Post_Graduate":    "https://www.freejobalert.com/search-jobs/any-post-graduate-government-jobs/",
    "Railway_Jobs":         "https://www.freejobalert.com/railway-jobs/",
    "Police_Defence":       "https://www.freejobalert.com/police-defence-jobs/",
    "Teaching_Faculty":     "https://www.freejobalert.com/teaching-faculty-jobs/",
    "Bank_Jobs":            "https://www.freejobalert.com/bank-jobs/",
    "Medical_Hospital":     "https://www.freejobalert.com/medical-hospital-jobs/",
    "Last_Date_Reminder":   "https://www.freejobalert.com/last-date-reminder/",
    "Latest_Notifications": "https://www.freejobalert.com/latest-notifications/",

    # ── NEW v9: Qualification-based categories ───────────────
    "4th_Pass":             "https://www.freejobalert.com/search-jobs/4th-pass-government-jobs/",
    "5th_Pass":             "https://www.freejobalert.com/search-jobs/5th-pass-government-jobs/",
    "6th_Pass":             "https://www.freejobalert.com/search-jobs/6th-pass-government-jobs/",
    "7th_Pass":             "https://www.freejobalert.com/search-jobs/7th-pass-government-jobs/",
    "9th_Pass":             "https://www.freejobalert.com/search-jobs/9th-pass-government-jobs/",
    "Intermediate":         "https://www.freejobalert.com/search-jobs/intermediate-government-jobs/",
    "GNM":                  "https://www.freejobalert.com/search-jobs/gnm-government-jobs/",
    "ANM":                  "https://www.freejobalert.com/search-jobs/anm-government-jobs/",
    "D_Pharm":              "https://www.freejobalert.com/search-jobs/dpharm-government-jobs/",
    "DMLT":                 "https://www.freejobalert.com/search-jobs/dmlt-government-jobs/",
    "D_El_Ed":              "https://www.freejobalert.com/search-jobs/deled-government-jobs/",
    "D_P_Ed":               "https://www.freejobalert.com/search-jobs/dped-government-jobs/",
    "DLT":                  "https://www.freejobalert.com/search-jobs/dlt-government-jobs/",
    "VHSE":                 "https://www.freejobalert.com/search-jobs/vhse-government-jobs/",
    "B_Sc":                 "https://www.freejobalert.com/search-jobs/bsc-government-jobs/",
    "BCA":                  "https://www.freejobalert.com/search-jobs/bca-government-jobs/",
    "MA":                   "https://www.freejobalert.com/search-jobs/ma-government-jobs/",
    "BBA":                  "https://www.freejobalert.com/search-jobs/bba-government-jobs/",
    "LLB":                  "https://www.freejobalert.com/search-jobs/llb-government-jobs/",
    "B_Ed":                 "https://www.freejobalert.com/search-jobs/bed-government-jobs/",
    "MBBS":                 "https://www.freejobalert.com/search-jobs/mbbs-government-jobs/",
    "B_Pharma":             "https://www.freejobalert.com/search-jobs/bpharma-government-jobs/",
    "BAMS":                 "https://www.freejobalert.com/search-jobs/bams-government-jobs/",
    "BDS":                  "https://www.freejobalert.com/search-jobs/bds-government-jobs/",
    "MBA_PGDM":             "https://www.freejobalert.com/search-jobs/mba-pgdm-government-jobs/",
    "M_A":                  "https://www.freejobalert.com/search-jobs/ma-government-jobs/",
    "M_Com":                "https://www.freejobalert.com/search-jobs/mcom-government-jobs/",
    "M_Sc":                 "https://www.freejobalert.com/search-jobs/msc-government-jobs/",
    "M_E_MTech":            "https://www.freejobalert.com/search-jobs/me-mtech-government-jobs/",
    "MCA":                  "https://www.freejobalert.com/search-jobs/mca-government-jobs/",
    "M_Ed":                 "https://www.freejobalert.com/search-jobs/med-government-jobs/",
    "MS_MD":                "https://www.freejobalert.com/search-jobs/ms-md-government-jobs/",
    "M_Pharma":             "https://www.freejobalert.com/search-jobs/mpharma-government-jobs/",
    "CA":                   "https://www.freejobalert.com/search-jobs/ca-government-jobs/",
    "CS":                   "https://www.freejobalert.com/search-jobs/cs-government-jobs/",
    "ICWA":                 "https://www.freejobalert.com/search-jobs/icwa-government-jobs/",
    "MPhil_PhD":            "https://www.freejobalert.com/search-jobs/mphil-phd-government-jobs/",

    # -- NEW (2026-07-15): 73 additional qualification categories --
    "B_A":                     "https://www.freejobalert.com/search-jobs/ba-government-jobs/",
    "BBM":                     "https://www.freejobalert.com/search-jobs/bbm-government-jobs/",
    "B_El_Ed":                 "https://www.freejobalert.com/search-jobs/beled-government-jobs/",
    "B_Voc":                   "https://www.freejobalert.com/search-jobs/bvoc-government-jobs/",
    "B_Lib":                   "https://www.freejobalert.com/search-jobs/blib-government-jobs/",
    "BFA":                     "https://www.freejobalert.com/search-jobs/bfa-government-jobs/",
    "BHA":                     "https://www.freejobalert.com/search-jobs/bha-government-jobs/",
    "BHM":                     "https://www.freejobalert.com/search-jobs/bhm-government-jobs/",
    "B_Optom":                 "https://www.freejobalert.com/search-jobs/boptom-government-jobs/",
    "BSW":                     "https://www.freejobalert.com/search-jobs/bsw-government-jobs/",
    "BVA":                     "https://www.freejobalert.com/search-jobs/bva-government-jobs/",
    "BPEd":                    "https://www.freejobalert.com/search-jobs/bped-government-jobs/",
    "BASLP":                   "https://www.freejobalert.com/search-jobs/baslp-government-jobs/",
    "BOT":                     "https://www.freejobalert.com/search-jobs/bot-government-jobs/",
    "BPMT":                    "https://www.freejobalert.com/search-jobs/bpmt-government-jobs/",
    "BSMS":                    "https://www.freejobalert.com/search-jobs/bsms-government-jobs/",
    "BPT":                     "https://www.freejobalert.com/search-jobs/bpt-government-jobs/",
    "BHMS":                    "https://www.freejobalert.com/search-jobs/bhms-government-jobs/",
    "BUMS":                    "https://www.freejobalert.com/search-jobs/bums-government-jobs/",
    "BVSC":                    "https://www.freejobalert.com/search-jobs/bvsc-government-jobs/",
    "BMLT":                    "https://www.freejobalert.com/search-jobs/bmlt-government-jobs/",
    "B_Plan":                  "https://www.freejobalert.com/search-jobs/bplan-government-jobs/",
    "B_Arch":                  "https://www.freejobalert.com/search-jobs/barch-government-jobs/",
    "B_Des":                   "https://www.freejobalert.com/search-jobs/bdes-government-jobs/",
    "BFSc":                    "https://www.freejobalert.com/search-jobs/bfsc-government-jobs/",
    "BPO":                     "https://www.freejobalert.com/search-jobs/bpo-government-jobs/",
    "BS":                      "https://www.freejobalert.com/search-jobs/bs-government-jobs/",
    "Any_Bachelors_Degree":    "https://www.freejobalert.com/search-jobs/any-bachelors-degree-government-jobs/",
    "Professional_Degree":     "https://www.freejobalert.com/search-jobs/professional-degree-government-jobs/",
    "ICMAI":                   "https://www.freejobalert.com/search-jobs/icmai-government-jobs/",
    "ICSI":                    "https://www.freejobalert.com/search-jobs/icsi-government-jobs/",
    "Member_of_ICAI":          "https://www.freejobalert.com/search-jobs/member-of-icai-government-jobs/",
    "M_Lib":                   "https://www.freejobalert.com/search-jobs/mlib-government-jobs/",
    "M_Voc":                   "https://www.freejobalert.com/search-jobs/mvoc-government-jobs/",
    "M_Des":                   "https://www.freejobalert.com/search-jobs/mdes-government-jobs/",
    "M_Plan":                  "https://www.freejobalert.com/search-jobs/mplan-government-jobs/",
    "M_Arch":                  "https://www.freejobalert.com/search-jobs/march-government-jobs/",
    "MSW":                     "https://www.freejobalert.com/search-jobs/msw-government-jobs/",
    "MS":                      "https://www.freejobalert.com/search-jobs/ms-government-jobs/",
    "MD_Pathology":            "https://www.freejobalert.com/search-jobs/md-pathology-government-jobs/",
    "M_Ch":                    "https://www.freejobalert.com/search-jobs/mch-government-jobs/",
    "DM":                      "https://www.freejobalert.com/search-jobs/dm-government-jobs/",
    "DNB":                     "https://www.freejobalert.com/search-jobs/dnb-government-jobs/",
    "DNB_Pathology":           "https://www.freejobalert.com/search-jobs/dnb-pathology-government-jobs/",
    "MFSc":                    "https://www.freejobalert.com/search-jobs/mfsc-government-jobs/",
    "MVSC":                    "https://www.freejobalert.com/search-jobs/mvsc-government-jobs/",
    "Master_of_Dental_Surgery":"https://www.freejobalert.com/search-jobs/master-of-dental-surgery-government-jobs/",
    "MHA":                     "https://www.freejobalert.com/search-jobs/mha-government-jobs/",
    "Master_in_Health_Administration":"https://www.freejobalert.com/search-jobs/master-inhealth-administration-government-jobs/",
    "MPH":                     "https://www.freejobalert.com/search-jobs/mph-government-jobs/",
    "MHS":                     "https://www.freejobalert.com/search-jobs/mhs-government-jobs/",
    "MPA":                     "https://www.freejobalert.com/search-jobs/mpa-government-jobs/",
    "MPT":                     "https://www.freejobalert.com/search-jobs/mpt-government-jobs/",
    "MHM":                     "https://www.freejobalert.com/search-jobs/mhm-government-jobs/",
    "M_P_Ed":                  "https://www.freejobalert.com/search-jobs/mped-government-jobs/",
    "MOT":                     "https://www.freejobalert.com/search-jobs/mot-government-jobs/",
    "MPO":                     "https://www.freejobalert.com/search-jobs/mpo-government-jobs/",
    "MASLP":                   "https://www.freejobalert.com/search-jobs/maslp-government-jobs/",
    "MFA":                     "https://www.freejobalert.com/search-jobs/mfa-government-jobs/",
    "MCM":                     "https://www.freejobalert.com/search-jobs/mcm-government-jobs/",
    "MLT":                     "https://www.freejobalert.com/search-jobs/mlt-government-jobs/",
    "PGDMLT":                  "https://www.freejobalert.com/search-jobs/pgdmlt-government-jobs/",
    "PG_Diploma":              "https://www.freejobalert.com/search-jobs/pg-diploma-government-jobs/",
    "PGDCA":                   "https://www.freejobalert.com/search-jobs/pgdca-government-jobs/",
    "PGDM":                    "https://www.freejobalert.com/search-jobs/pgdm-government-jobs/",
    "PGDBM":                   "https://www.freejobalert.com/search-jobs/pgdbm-government-jobs/",
    "PGDBA":                   "https://www.freejobalert.com/search-jobs/pgdba-government-jobs/",
    "PGP":                     "https://www.freejobalert.com/search-jobs/pgp-government-jobs/",
    "Any_Masters_Degree":      "https://www.freejobalert.com/search-jobs/any-masters-degree-government-jobs/",
    "Intergrated_PG":          "https://www.freejobalert.com/search-jobs/intergrated-pg-government-jobs/",
    "LLM":                     "https://www.freejobalert.com/search-jobs/llm-government-jobs/",
    "M_Th":                    "https://www.freejobalert.com/search-jobs/mth-government-jobs/",
    "Retired_Staff":           "https://www.freejobalert.com/search-jobs/retired-staff-government-jobs/",
}

# ── Qualification Keywords (v4 FIXED) ───────────────────────
# Job ke qualification/eligibility text mein keyword match karne ke liye.
# _post_process_job() aur filtering mein use ho sakta hai.
#
# v4 CRITICAL FIX: Ambiguous short tokens (ca , cs , ms , md , ma , me )
# remove kiye — ye "categories", "candidates", "maximum", "forms" jaisi
# common words mein false positive dete the (1900+ wrong matches).
# Ab STRICT word-boundary regex patterns use ho rahe hain.
#
# IMPORTANT: In keywords ka use sirf QUAL_STRICT_CATEGORIES par hota hai.
# Inhe re.search() se match karo — plain 'in' operator se NAHI.
# _post_process_job() mein _match_qual_keywords() helper use karo.
QUAL_KEYWORDS = {
    "4th_Pass":    [r"\b4th\s*(class|pass|std)\b"],
    "5th_Pass":    [r"\b5th\s*(class|pass|std)\b"],
    "6th_Pass":    [r"\b6th\s*(class|pass|std)\b"],
    "7th_Pass":    [r"\b7th\s*(class|pass|std)\b"],
    "9th_Pass":    [r"\b9th\s*(class|pass|std)\b"],
    "Intermediate":[r"\bintermediate\b", r"\b10\s*\+\s*2\b", r"\b\+2\b", r"\bhsc\b"],
    "GNM":         [r"\bgnm\b"],
    "ANM":         [r"\banm\b"],
    "D_Pharm":     [r"\bd\.?\s*pharm(a|acy)?\b"],
    "DMLT":        [r"\bdmlt\b"],
    "D_El_Ed":     [r"\bd\.?\s*el\.?\s*ed\b", r"\bdeled\b"],
    "D_P_Ed":      [r"\bd\.?\s*p\.?\s*ed\b", r"\bdped\b"],
    "DLT":         [r"\bdlt\b"],
    "VHSE":        [r"\bvhse\b"],
    "10TH_Pass":   [r"\b10th\b", r"\bmatric(ulation)?\b", r"\bsslc\b", r"\bx\s*(class|std|pass)\b"],
    "8TH_Pass":    [r"\b8th\s*(class|pass|std)\b", r"\bviii\s*(class|std)\b"],
    "12TH_Pass":   [r"\b12th\b", r"\bintermediate\b", r"\b10\s*\+\s*2\b", r"\bhsc\b", r"\bxii\s*(class|pass|std)\b"],
    "ITI":         [r"\biti\b", r"\bindustrial\s*training\s*institute\b"],
    "Diploma":     [r"\bdiploma\b"],
    "B_Tech_BE":   [r"\bb\.?\s*e\.?\b", r"\bb\.?\s*tech\b", r"\bbtech\b", r"\bengineering\s*degree\b"],
    "B_Sc":        [r"\bb\.?\s*sc\b", r"\bbsc\b"],
    "B_Com":       [r"\bb\.?\s*com\b", r"\bbcom\b"],
    "BCA":         [r"\bbca\b"],
    "MA":          [r"\bm\.?\s*a\.?\b(?!\s*mbbs|\s*tech)", r"\bmaster\s*of\s*arts\b"],
    "BBA":         [r"\bbba\b"],
    "LLB":         [r"\bllb\b", r"\bll\.?\s*b\b"],
    "B_Ed":        [r"\bb\.?\s*ed\b"],
    "MBBS":        [r"\bmbbs\b"],
    "B_Pharma":    [r"\bb\.?\s*pharm(a|acy)?\b"],
    "BAMS":        [r"\bbams\b"],
    "BDS":         [r"\bbds\b"],
    "Any_Graduate":     [r"\bany\s*graduate\b", r"\bgraduation\b", r"\bbachelor('?s)?\s*(degree|of)\b"],
    "MBA_PGDM":    [r"\bmba\b", r"\bpgdm\b", r"\bpost\s*graduate\s*diploma\s*in\s*management\b"],
    "M_A":         [r"\bm\.?\s*a\.?\b(?!\s*mbbs|\s*tech)", r"\bmaster\s*of\s*arts\b"],
    "M_Com":       [r"\bm\.?\s*com\b"],
    "M_Sc":        [r"\bm\.?\s*sc\b", r"\bmaster\s*of\s*science\b"],
    "M_E_MTech":   [r"\bm\.?\s*e\.?\b(?!\s*mbbs)", r"\bm\.?\s*tech\b", r"\bmtech\b", r"\bmaster\s*of\s*(engineering|technology)\b"],
    "MCA":         [r"\bmca\b"],
    "M_Ed":        [r"\bm\.?\s*ed\b"],
    "MS_MD":       [r"\bms\s*/\s*md\b", r"\bmaster\s*of\s*surgery\b", r"\bdoctor\s*of\s*medicine\b",
                    r"\bm\.?\s*d\.?\b(?!\s*phd)", r"\bm\.?\s*s\.?\b(?!\s*office|\s*excel|\s*word|\s*access)"],
    "M_Pharma":    [r"\bm\.?\s*pharm(a|acy)?\b"],
    "CA":          [r"\bchartered\s*accountant\b", r"\bca\s*(qualified|final|inter|degree|course)\b",
                    r"\bicai\b", r"\bc\.?\s*a\.?\b(?=\s*(degree|qualified|course|exam|final|inter|pass))"],
    "CS":          [r"\bcompany\s*secretary\b", r"\bcs\s*(qualified|final|course)\b", r"\bicsi\b",
                    r"\bc\.?\s*s\.?\b(?=\s*(degree|qualified|course|exam|final|pass))"],
    "ICWA":        [r"\bicwa\b", r"\bcma\b(?!\s*exam\s*code)", r"\bcost\s*(and\s*works?\s*)?accountant\b"],
    "MPhil_PhD":   [r"\bm\.?\s*phil\b", r"\bph\.?\s*d\b", r"\bphd\b", r"\bmphil\b"],
    "Any_Post_Graduate": [r"\bpost\s*graduate\b", r"\bpostgraduate\b", r"\bpg\s*(degree|diploma|course|qualification)\b"],
}

# ── Categories jinmein STRICT qualification check lagega (v10) ──
# IMPORTANT: Sirf v9 mein add kiye gaye 37 NAYI qualification categories
# par strict check lagega.
# OLD categories (10TH_Pass, 8TH_Pass, 12TH_Pass, Diploma, ITI,
# B_Tech_BE, B_Com, Any_Graduate, Any_Post_Graduate, Railway_Jobs,
# Bank_Jobs, Police_Defence, Teaching_Faculty, Medical_Hospital,
# Last_Date_Reminder, Latest_Notifications) par KOI STRICT CHECK NAHI.
QUAL_STRICT_CATEGORIES = {
    "4th_Pass", "5th_Pass", "6th_Pass", "7th_Pass", "9th_Pass",
    "Intermediate",
    "GNM", "ANM",
    "D_Pharm", "DMLT", "D_El_Ed", "D_P_Ed", "DLT", "VHSE",
    "B_Sc", "BCA", "MA", "BBA", "LLB", "B_Ed",
    "MBBS", "B_Pharma", "BAMS", "BDS",
    "MBA_PGDM",
    "M_A", "M_Com", "M_Sc", "M_E_MTech", "MCA", "M_Ed",
    "MS_MD", "M_Pharma",
    "CA", "CS", "ICWA",
    "MPhil_PhD",
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

PAN_INDIA_CATEGORIES = {"Railway_Jobs", "Bank_Jobs", "Police_Defence", "Latest_Notifications"}

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
JSON_PATH        = "_temp_fja.json"   # Resume tracking (in-memory only reference)
OUTPUT_JSON_PATH        = "_temp_fja.json"    # Final output — sirf yahi ek file banega

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
# QUALIFICATION KEYWORD HELPERS (v4 NEW)
# ============================================================
def _match_qual_keywords(text: str, qual_key: str) -> bool:
    """
    QUAL_KEYWORDS ke patterns ko re.search() se match karo.
    v4: plain 'in' operator ki jagah strict regex — false positives band.
    """
    patterns = QUAL_KEYWORDS.get(qual_key, [])
    if not patterns:
        return False
    text_lower = text.lower()
    for pat in patterns:
        try:
            if re.search(pat, text_lower, re.IGNORECASE):
                return True
        except re.error:
            pass
    return False


# ============================================================
# QUALIFICATION VERIFICATION (v10 NEW)
# ============================================================
def _verify_qualification_match(job: dict, category: str) -> bool:
    """
    Check karo ki scraped job page ki qualification actually us
    category se match karti hai ya nahi.

    Rules:
    1. Sirf QUAL_STRICT_CATEGORIES par apply hota hai.
       Railway, Bank, Police jaise general categories mein koi
       restriction nahi hai.
    2. Category ke QUAL_KEYWORDS mein se KOI EK keyword
       qualification text mein hona ZAROORI hai.
    3. Agar qualification section bilkul khali hai toh PASS karo
       (benefit of doubt — scraping miss ho sakti hai).

    Returns:
        True  → job accept karo
        False → job reject karo (wrong qualification)
    """
    # Sirf strict categories par check
    if category not in QUAL_STRICT_CATEGORIES:
        return True

    keywords = QUAL_KEYWORDS.get(category)
    if not keywords:
        return True  # koi keyword define nahi — allow karo

    ql = job.get("qualification", {})

    # Qualification text collect karo — saare possible fields se
    qual_parts = []
    for field in ["details", "minimum_qualification", "educational_qualification",
                  "education_qualification", "qualification", "eligibility", "raw"]:
        val = ql.get(field, "")
        if val:
            qual_parts.append(str(val))

    # post_wise_qualification list se bhi text collect karo (multi-col tables)
    for entry in ql.get("post_wise_qualification", []):
        for fld in ["essential_qualification", "desirable"]:
            v = entry.get(fld, "")
            if v:
                qual_parts.append(v)

    # vacancy_details mein bhi qualification column hota hai kabhi kabhi
    for row in job.get("vacancy_details", []):
        for k, v in row.items():
            if any(w in k.lower() for w in ["qual", "eligib", "education"]):
                qual_parts.append(str(v))

    # short_information fallback
    si = job.get("basic_details", {}).get("short_information", "")
    if si:
        qual_parts.append(si)

    qual_text = " ".join(qual_parts).lower().strip()

    # Agar qualification text hi nahi mila — benefit of doubt, pass karo
    if not qual_text:
        return True

    # Keyword match check — strict regex (v4)
    return _match_qual_keywords(qual_text, category)


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

    # Job location
    if not bd.get("job_location"):
        loc = _extract_state(bd.get("job_title", ""))
        if loc:
            bd["job_location"] = loc

    if not bd.get("job_location"):
        loc = _extract_state(ql.get("domicile", ""))
        if loc:
            bd["job_location"] = loc

    if not bd.get("job_location") and category in PAN_INDIA_CATEGORIES:
        bd["job_location"] = "Pan India"

    # ── Qualification keyword matching (v9 NEW) ──────────────
    # qualification.details text mein QUAL_KEYWORDS se match karke
    # matched_qualifications list fill karo
    qual_parts_pp = [
        str(ql.get("details", "")),
        str(ql.get("minimum_qualification", "")),
        str(ql.get("education_qualification", "")),
        str(bd.get("short_information", "")),
    ]
    # post_wise_qualification list se bhi text extract karo
    for entry in ql.get("post_wise_qualification", []):
        for fld in ["essential_qualification", "desirable"]:
            v = entry.get(fld, "")
            if v:
                qual_parts_pp.append(str(v))
    qual_text = " ".join(qual_parts_pp).lower()
    if qual_text.strip():
        matched = []
        for qual_key in QUAL_KEYWORDS:
            if _match_qual_keywords(qual_text, qual_key):
                if qual_key not in matched:
                    matched.append(qual_key)
        if matched:
            ql["matched_qualifications"] = matched

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
    - State aggregator pages (already filtered by is_junk_fja_url)
    """
    if not href or "freejobalert.com" not in href:
        return False
    path = href.split("freejobalert.com", 1)[-1].rstrip("/")
    # Must be a slug-style path (not query string, not nested)
    if "?" in path or path.count("/") > 2:
        return False
    # Exclude listing/category/tag pages
    for skip in ["/search-jobs/", "/category/", "/tag/", "/page/"]:
        if skip in path:
            return False
    # Accept: slug has at least 2 parts and looks like an article
    slug = path.strip("/")
    # Must be a non-empty slug
    if not slug or len(slug) < 5:
        return False
    # Accept year-stamped or job-keyword articles
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
            # Extended/revised date rows inside a generic table → distinct field.
            _ext = extended_date_field(key)
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
            # generic 'last date' match, latest value always wins). Renders as a
            # distinct row and drives the effective deadline site-side.
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

            # Descriptive label: anchor text prefer karo, warna row ka left-col label
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
            # Parent element se context label nikalo
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

        # Parent context se label nikalo
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
    """Internet wapas aane tak wait karo (network disconnect pe call hoti hai)."""
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
    {key: url_str, _labels: {key: label}} →
    {key: {url: ..., label: ...}}  (ya list of such objects agar multiple URLs)
    
    Ye renderer ke liye consistent {url, label} format ensure karta hai
    bina _labels alag dict ke.
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

    # all_official_links already {label, url} format mein hai — ensure karo
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
        if cat_idx > 1:
            if consecutive_empty >= 3:
                # 3+ consecutive failures = site ne block kiya, lamba wait
                wait_s = 90 + (consecutive_empty - 3) * 30
                wait_s = min(wait_s, 300)
                print(f" [THROTTLE] {consecutive_empty} consecutive empty categories"
                      f" — {wait_s}s wait kar raha hoon...")
                smart_delay("crawl", extra=wait_s - 5)
            else:
                # Normal inter-category gap: 15-25s
                smart_delay("crawl", extra=10)

        all_json.setdefault(label, [])
        # Already scraped URLs for THIS category (URL → item map for carry-forward)
        existing_by_url = {j.get("_scraped_from"): j for j in all_json[label] if j.get("_scraped_from")}
        existing_urls   = set(existing_by_url.keys())
        print(f" Already scraped: {len(existing_urls)} jobs")

        # ── Collect ALL links (no global-seen filter here) ────
        links = []
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
        #   - Agar URL already scraped hai → carry-forward (purana item)
        #   - Naya URL → fresh scrape
        # Final category list is website-ordered sequence se banta hai.
        # RE-SCRAPE-ON-UPDATE: a URL is (re)fetched when it's brand new OR when an
        # already-scraped job is still ACTIVE and hasn't been re-checked recently
        # (needs_refresh) — so source updates like a date extension / corrigendum
        # get picked up. Expired jobs are never re-fetched (bounded request count).
        def _should_scrape(u):
            old = existing_by_url.get(u)
            return old is None or needs_refresh(old)
        new_links = [l for l in links if _should_scrape(l)]
        _refresh_ct = sum(1 for l in new_links if l in existing_urls)
        print(f" -> Total links found : {len(links)}")
        print(f" -> To fetch: {len(new_links)} ({len(new_links) - _refresh_ct} new + {_refresh_ct} updated/active re-check)")

        # Consecutive rate-limit tracker update
        if not links:
            consecutive_empty += 1
        else:
            consecutive_empty = 0   # Reset on success

        # Build ordered_rows: (url, "carry"|"new") in exact website sequence
        ordered_rows = []
        for lnk in links:
            # carry-forward only if already scraped AND not due for a refresh
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
        # results_by_url: URL → scraped job data (new items only)
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
                data["_last_checked"] = now_iso()   # for needs_refresh() next run
                _post_process_job(data, label)
                results_by_url[job_url] = data

                with _seen_lock:
                    _global_seen_urls.add(job_url)

                print(f"   [{done_count:04d}/{len(new_links)}] ✓ {job_url[-70:]}")

                # Periodic save (in-progress partial order — final rebuild below)
                if done_count % 10 == 0:
                    _save_json(all_json)
                    print(f"    [AUTO-SAVE] {done_count} done → {JSON_PATH}")

        # ── Rebuild category in EXACT WEBSITE ROW ORDER ────────────────────────
        # Walk ordered_rows: carry old item OR insert freshly scraped item.
        # Items not on site anymore (old URL not in links) are naturally dropped.
        final_items = []
        for url, kind in ordered_rows:
            if kind == "carry":
                item = existing_by_url.get(url)
            else:
                # fresh scrape; if a re-fetch of an EXISTING job failed/empty,
                # fall back to the old item so we never lose already-good data.
                item = results_by_url.get(url) or existing_by_url.get(url)
            if item:
                final_items.append(item)

        all_json[label] = final_items
        _save_json(all_json)
        print(f" ✓ {label} COMPLETE — Total: {len(all_json[label])} jobs saved")

    # ── FINAL SAVE ────────────────────────────────────────────
    _save_json(all_json)
    _print_summary(all_json)

    # ── v4: Qualification_Wise_Jobs.json generate karo ────────
    generate_qualification_wise_json(all_json)


def generate_qualification_wise_json(fja_data: dict, output_path: str = "Qualification_Wise_Jobs.json"):
    """
    Complete_Jobs_Full_Data.json (freejobalert_categories) se
    Qualification_Wise_Jobs.json generate karo.

    Strategy (v4 — false-positive free):
    ─────────────────────────────────────
    1. PRIMARY: FJA category name se DIRECT grouping
       (e.g. "12TH_Pass" category ke sabhi jobs → 12TH_Pass group)
       Ye 100% accurate hai — site ne already qualify kiya hua hai.

    2. SECONDARY: Cross-matching — ek job multiple quals mention kar sakti hai
       (e.g. A&N CHSL has 12th + Diploma + B.Tech in one notification)
       Sirf qualification.details / education_qualification / post_wise_qualification
       se match karo — short_information se NAHI (false positives avoid karne ke liye)
       Strict regex patterns use karo (QUAL_KEYWORDS v4)

    Output format:
    {
      "generated_at": "...",
      "total_qualifications": N,
      "total_job_entries": N,
      "qualifications": {
        "12TH_Pass": [ {job_obj}, ... ],
        "Diploma":   [ {job_obj}, ... ],
        ...
      }
    }
    """
    # Categories jinhe qualification group mein map karna hai
    # (Railway, Bank, Police, etc. exclude — ye qual-based nahi hain)
    DIRECT_QUAL_CATS = {
        "10TH_Pass", "8TH_Pass", "12TH_Pass", "Diploma", "ITI",
        "B_Tech_BE", "B_Com", "Any_Graduate", "Any_Post_Graduate",
        "GNM", "ANM", "D_Pharm", "DMLT", "D_El_Ed", "D_P_Ed", "DLT", "VHSE",
        "B_Sc", "BCA", "MA", "BBA", "LLB", "B_Ed", "MBBS", "B_Pharma",
        "BAMS", "BDS", "MBA_PGDM", "M_A", "M_Com", "M_Sc", "M_E_MTech",
        "MCA", "M_Ed", "MS_MD", "M_Pharma", "CA", "CS", "ICWA", "MPhil_PhD",
        "4th_Pass", "5th_Pass", "6th_Pass", "7th_Pass", "9th_Pass", "Intermediate",
    }

    print(f"\n{'='*60}")
    print("  GENERATING Qualification_Wise_Jobs.json ...")
    print(f"{'='*60}")

    qual_wise = {}

    # ── Step 1: Direct category → qual group ──────────────────
    for cat, jobs in fja_data.items():
        if cat not in DIRECT_QUAL_CATS:
            continue
        for job in jobs:
            title = job.get("basic_details", {}).get("job_title", "")
            qual_wise.setdefault(cat, [])
            # Deduplicate by job title
            if not any(j.get("basic_details", {}).get("job_title", "") == title
                       for j in qual_wise[cat]):
                qual_wise[cat].append(job)

    # ── Step 2: Cross-match — strict qual text only ────────────
    for cat, jobs in fja_data.items():
        for job in jobs:
            qual = job.get("qualification", {})

            # ONLY use qual.details + education_qualification + post_wise_qualification
            # short_information se NAHI — false positives wahan se aate hain
            qual_parts = []
            d  = qual.get("details", "").strip()
            eq = qual.get("education_qualification", "").strip()
            if d:  qual_parts.append(d)
            if eq: qual_parts.append(eq)
            for entry in qual.get("post_wise_qualification", []):
                v = entry.get("essential_qualification", "")
                if v: qual_parts.append(v)

            qual_text = " ".join(qual_parts)
            if not qual_text.strip():
                continue

            title = job.get("basic_details", {}).get("job_title", "")

            for qkey in DIRECT_QUAL_CATS:
                # Already in this group (direct mapped) — skip
                if cat == qkey:
                    continue
                # Check strict keyword match
                if _match_qual_keywords(qual_text, qkey):
                    qual_wise.setdefault(qkey, [])
                    # Deduplicate
                    if not any(j.get("basic_details", {}).get("job_title", "") == title
                               for j in qual_wise[qkey]):
                        qual_wise[qkey].append(job)

    # ── Step 3: Sort each group by last_updated desc ──────────
    def _sort_key(job):
        lu = job.get("basic_details", {}).get("last_updated", "")
        try:
            return datetime.strptime(lu, "%d %b %Y")
        except Exception:
            return datetime(2000, 1, 1)

    for qkey in qual_wise:
        qual_wise[qkey].sort(key=_sort_key, reverse=True)

    # ── Step 4: Build output ───────────────────────────────────
    total_entries = sum(len(v) for v in qual_wise.values())
    output = {
        "generated_at":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_qualifications": len(qual_wise),
        "total_job_entries":   total_entries,
        "qualifications":      qual_wise,
    }
    output = _strip_aws_keys(output)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Qualification_Wise_Jobs.json saved → {output_path}")
    print(f"  Total qual groups : {len(qual_wise)}")
    print(f"  Total job entries : {total_entries}")
    for qkey, jobs in sorted(qual_wise.items(), key=lambda x: -len(x[1])):
        print(f"    {qkey:20s}: {len(jobs)} jobs")
    print(f"{'='*60}")


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
        print(f"  {label:30s}: {len(jobs):5d} jobs")
        total += len(jobs)
    print(f"{'='*60}")
    print(f"  {'TOTAL':30s}: {total:5d} jobs")
    print(f"  JSON (output)   -> {OUTPUT_JSON_PATH}")
    print(f"  ✅ source_url (scraper site) JSON mein nahi hai")
    print(f"  ✅ Sirf official links (Apply, Notification, Result, etc.)")
    print(f"  ✅ App/download links filtered")
    print(f"  ✅ Last Date Reminder category included")
    print(f"  ✅ Parallel scraping ({MAX_WORKERS} workers)")
    print(f"  ✅ v9: 37 nayi qualification categories added (4th Pass → M.Phil/Ph.D)")
    print(f"  ✅ v10: 'No Jobs' page detection — empty categories auto-skipped")
    print(f"  ✅ v11 CRITICAL FIX: Strict check SIRF 37 nayi categories par")
    print(f"       Old categories (10th,8th,12th,Diploma,ITI,B.Tech etc.) unaffected")
    print(f"  ✅ v12: Qual SKIP removed — Method G 'Other Latest Govt Jobs' section")


# ================================================================


# ================================================================
# MERGE INTO UNIFIED JSON
# ================================================================
if __name__ == "__main__":
    from scraper_merge import merge_into_json, wait_for_internet
    import json as _json_mod, os

    wait_for_internet("FreeJobAlert")

    print("\n" + "="*60)
    print("  SCRAPER: FreeJobAlert Categories")
    print("="*60)

    error_str = ""
    try:
        scrape_all()   # saves to _temp_fja.json
    except Exception as e:
        import traceback; traceback.print_exc()
        error_str = str(e)

    # Temp file se FJA dict load karo
    scraped = {}
    if os.path.exists("_temp_fja.json"):
        with open("_temp_fja.json", encoding="utf-8") as f:
            scraped = _json_mod.load(f)
        # Temp file clean up
        os.remove("_temp_fja.json")

    # Qualification_Wise_Jobs.json bhi update karo
    if scraped and isinstance(scraped, dict):
        generate_qualification_wise_json(scraped)

    merge_into_json(
        source        = "freejobalert_categories",
        fresh_data    = scraped,
        scraper_error = error_str,
    )
