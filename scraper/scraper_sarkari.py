#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================================
# SCRAPER: Sarkari Data — scraper_sarkari.py
# ================================================================
# Sources : sarkariresultshine.com + sarkariresult.com + sarkarinetwork.com
# Writes  : merged_sarkari_data.json  (intermediate)
# Output  : Updates "sarkari_data" in Complete_Jobs_Full_Data.json
#           Baaki teen sources (fja, education, state) UNCHANGED rehte hain.
#
# Run:  python scraper_sarkari.py
# ================================================================

import sys
import time
sys.stdout.reconfigure(encoding="utf-8")

# SOURCE 2: SARKARI DATA (merged_sarkari_scraper_fixed)
# ================================================================

# =========================================================
# MERGED SARKARI SCRAPER — UNIFIED OUTPUT
# Sources:
#   1. sarkariresultshine.com  (offline forms — active jobs only)
#   2. sarkariresult.com       (latest jobs, admit card, result,
#                               admission, answer key)
# Output: merged_sarkari_data.json
# =========================================================


import re
import json
import hashlib
import random
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

# curl_cffi impersonates a real Chrome browser's TLS/JA3 fingerprint, which is
# what gets past Cloudflare's bot detection on sarkariresult.com. Plain
# `requests` always returns 403 from datacenter IPs (GitHub Actions) because its
# TLS fingerprint screams "Python script" even with perfect headers. We import
# it lazily/optionally so the scraper still runs if the package isn't installed.
try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except Exception:
    cffi_requests = None
    HAS_CURL_CFFI = False


# =========================================================
# SETTINGS — Source 1: sarkariresultshine.com
# =========================================================

SHINE_CATEGORY_URLS = [
    "https://sarkariresultshine.com/category/offline-form/",
    "https://sarkariresultshine.com/category/offline-form/page/2/",
    "https://sarkariresultshine.com/category/offline-form/page/3/"
]

SHINE_LATEST_JOBS_URLS = [
    "https://sarkariresultshine.com/category/latest-jobs/",
    "https://sarkariresultshine.com/category/latest-jobs/page/2/",
    "https://sarkariresultshine.com/category/latest-jobs/page/3/",
    "https://sarkariresultshine.com/category/latest-jobs/page/4/",
    "https://sarkariresultshine.com/category/latest-jobs/page/5/",
    "https://sarkariresultshine.com/category/latest-jobs/page/6/",
    "https://sarkariresultshine.com/category/latest-jobs/page/7/",
    "https://sarkariresultshine.com/category/latest-jobs/page/8/",
    "https://sarkariresultshine.com/category/latest-jobs/page/9/",
    "https://sarkariresultshine.com/category/latest-jobs/page/10/",
]

SHINE_SOURCE_DOMAIN = "sarkariresultshine.com"
SHINE_MAX_THREADS   = 25

SHINE_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
]

# =========================================================
# SETTINGS — Source 2: sarkariresult.com
# =========================================================

SR_HOMEPAGE_URL = "https://www.sarkariresult.com/"

# Mapping: homepage section heading  →  internal category key
# Keys must match SR_CATEGORY_STATUS keys exactly
SR_SECTION_MAP = {
    "Latest Jobs":   "SR_Latest_Jobs",
    "Latest Job":    "SR_Latest_Jobs",   # site kabhi kabhi singular use karta hai
    "LatestJob":     "SR_Latest_Jobs",
    "New Jobs":      "SR_Latest_Jobs",
    "Latest Naukri": "SR_Latest_Jobs",
    "Result":        "SR_Result",
    "Results":       "SR_Result",
    "Admit Card":    "SR_Admit_Card",
    "Admit Cards":   "SR_Admit_Card",
    "Hall Ticket":   "SR_Admit_Card",
    "Admission":     "SR_Latest_Jobs",   # SR_Admission category retired
    "Admissions":    "SR_Latest_Jobs",   # SR_Admission category retired
    "Answer Key":    "SR_Answer_Key",
    "Answer Keys":   "SR_Answer_Key",
    "AnswerKey":     "SR_Answer_Key",
}

# ── GenerateBlocks gb-container class IDs → category key ────────────────────
# sarkariresult.com WordPress site GenerateBlocks plugin use karta hai.
# Homepage ke har box ka ek unique gb-container-XXXXXXXX class hota hai.
# Ye IDs CSS mein border styles se bhi confirm hote hain.
# IMPORTANT: Agar site update hone par ye IDs change ho jayein to yahan update karo.
SR_GB_CONTAINER_MAP = {
    # Container class ID   →  category key
    "gb-container-0b76599a": "SR_Result",
    "gb-container-e64d3148": "SR_Admit_Card",
    "gb-container-c7488d9a": "SR_Latest_Jobs",
    "gb-container-d19ddc59": "SR_Answer_Key",
    "gb-container-b48dca36": "SR_Latest_Jobs",   # was SR_Admission (retired)
    "gb-container-51daea0e": "SR_Latest_Jobs",   # Important / extra latest
    "gb-container-62cc0772": "SR_Latest_Jobs",   # was SR_Admission 2nd (retired)
    "gb-container-e623eef5": "SR_Latest_Jobs",   # Outsourcing/Offline Jobs
    "gb-container-46442b40": "SR_Latest_Jobs",   # Important 2nd
}

# Case-insensitive lookup helper
def _sr_section_lookup(text: str) -> str | None:
    """SR_SECTION_MAP mein case-insensitive match karo."""
    direct = SR_SECTION_MAP.get(text)
    if direct:
        return direct
    tl = text.lower().strip()
    for k, v in SR_SECTION_MAP.items():
        if k.lower() == tl:
            return v
    return None

# Kept for backward-compat (summary output uses these keys)
SR_CATEGORIES = {
    "SR_Latest_Jobs": None,
    "SR_Admit_Card":  None,
    "SR_Result":      None,
    "SR_Admission":   None,
    "SR_Answer_Key":  None,
}

SR_CATEGORY_STATUS = {
    "SR_Latest_Jobs":  "active",
    "SR_Admit_Card":   "admit_card_released",
    "SR_Result":       "result_declared",
    "SR_Admission":    "active",
    "SR_Answer_Key":   "answer_key_released",
}

# ── Sirf ye 5 SR categories valid hain ─────────────────────────────────
# Har SR item par in 5 mein se EXACTLY ek category name likha hona chahiye.
SR_VALID_CATEGORIES = (
    "SR_Latest_Jobs",
    "SR_Result",
    "SR_Admit_Card",
    "SR_Answer_Key",
)


def sr_resolve_category(category, title="", url=""):
    """
    Category name guarantee karta hai — hamesha 5 valid SR categories mein se ek.
    Agar passed category galat/khaali ho, to title + URL slug se detect karta hai.
    Fallback = SR_Latest_Jobs (prompt rule: default fallback).
    """
    if category in SR_VALID_CATEGORIES:
        return category

    blob = f"{title} {url}".lower()

    # Answer key sabse pehle (kyunki "answer key" mein "result" jaisa overlap nahi)
    if any(k in blob for k in ("answer key", "answerkey", "answer-key",
                               "response sheet", "objection")):
        return "SR_Answer_Key"
    if any(k in blob for k in ("admit card", "admitcard", "admit-card",
                               "hall ticket", "call letter", "hall-ticket")):
        return "SR_Admit_Card"
    if any(k in blob for k in ("admission", "counselling", "counseling",
                               "allotment", "entrance", "prospectus")):
        return "SR_Latest_Jobs"   # SR_Admission retired → fold into Latest Jobs
    if any(k in blob for k in ("result", "merit list", "merit-list", "cut off",
                               "cutoff", "cut-off", "scorecard", "score card",
                               "selected", "selection list")):
        return "SR_Result"
    if any(k in blob for k in ("recruitment", "apply online", "online form",
                               "vacancy", "vacancies", "notification",
                               "latestjob", "latest-job", "latest job")):
        return "SR_Latest_Jobs"

    return "SR_Latest_Jobs"


def sr_stamp_category(item, category, title="", url=""):
    """
    Item dict par 'category' field ko FIRST key ke roop mein set karta hai,
    valid SR category name ke saath. Saath hi branding/own-site/social/
    source_url scrub karta hai. Item ko in-place rebuild karke return karta hai.
    """
    if not isinstance(item, dict):
        return item
    resolved = sr_resolve_category(
        category,
        title or item.get("title", ""),
        url or item.get("source_url", "") or item.get("url", ""),
    )
    # branding / own-site / social / source_url safai
    item = sr_scrub_obj(item)
    # category ko sabse pehle rakhne ke liye dict rebuild karo
    rebuilt = {"category": resolved}
    for k, v in item.items():
        if k == "category":
            continue
        rebuilt[k] = v
    return rebuilt

SR_BLOCK_WORDS = [
    "telegram", "t.me", "sarkariresult2012",
    "whatsapp", "facebook", "instagram", "youtube",
    "twitter", "x.com", "android-app", "apple-ios",
    "play.google", "itunes", "remove-background",
    "background-remover", "sarkariresultportal",
    "tinyurl", "doc.sarkariresults.org.in",
    "sarkariresults.org.in", "sarkariresult.tools",
]

# =========================================================
# SHARED CONSTANTS
# =========================================================

TODAY        = datetime.today()
MSS_OUTPUT_FILE  = "merged_sarkari_data.json"  # standalone ref only

SR_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection":      "keep-alive",
    "Referer":         "https://www.google.com/search?q=sarkari+result",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest":  "document",
    "Sec-Fetch-Mode":  "navigate",
    "Sec-Fetch-Site":  "cross-site",
    "Sec-Fetch-User":  "?1",
    "sec-ch-ua":       '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Cache-Control":   "max-age=0",
}

# =========================================================
# SHARED HELPERS
# =========================================================

def clean(text):
    if not text:
        return ""
    text = str(text).replace("\xa0", " ").replace("Â", " ")
    return " ".join(text.split()).strip()


def clean_extra_text(text):
    if not text:
        return ""
    text = clean(text).replace("❓", "")
    text = re.sub(r"\.{2,}", ".", text)
    return clean(text)


def clean_total_value(value):
    if not value:
        return ""
    value = clean(value)
    bad_words = ["rs", "₹", "salary", "per month", "monthly", "inr"]
    for b in bad_words:
        if b.lower() in value.lower():
            return ""
    m = re.search(r"\d+", value)
    return m.group(0) if m else ""


def parse_date(date_str):
    if not date_str:
        return None
    date_str = clean(date_str)
    for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%d %B %Y", "%d %b %Y", "%d %b. %Y",
                "%Y-%m-%d"]:
        try:
            return datetime.strptime(date_str, fmt)
        except Exception:
            pass
    return None


def date_to_iso(date_str):
    """Convert DD/MM/YYYY or DD-MM-YYYY to YYYY-MM-DD. Non-date strings kept as-is."""
    if not date_str:
        return ""
    date_str = clean(date_str)
    for fmt in ("%d/%m/%Y", "%d-%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return date_str


def is_expired(date_str):
    if not date_str:
        return False
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            d = datetime.strptime(clean(date_str), fmt)
            return d.date() < TODAY.date()
        except ValueError:
            pass
    return False


def is_active_job(last_date):
    if not last_date:
        return False
    parsed = parse_date(last_date)
    if not parsed:
        return False
    return parsed.date() >= TODAY.date()


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:120]


def make_slug(title, category):
    h = hashlib.md5(title.encode()).hexdigest()[:6]
    return f"{category.lower()}-{slugify(title)}-{h}"


SR_OWN_DOMAINS = ["sarkariresult.com", "sarkariresultshine.com"]

def is_sr_blocked(url):
    low = url.lower()
    if any(d in low for d in SR_OWN_DOMAINS):
        return True
    return any(b in low for b in SR_BLOCK_WORDS)


def is_sr_valid_url(url):
    try:
        p = urlparse(url)
        return p.scheme in ["http", "https"]
    except Exception:
        return False


# =========================================================
# OUTPUT SCRUBBERS — branding / own-site / social safai
# =========================================================
# Requirement:
#   1) source_url / www.sarkariresult.com ka koi bhi link output mein NAHI
#   2) "Sarkari Result" naam / branding / social media NAHI
#   3) Sirf official govt/university/board links rakho — ek bhi skip nahi
# Ye helpers har string/dict/list ko recursively saaf karte hain.

# Branding / site-name / social — text se hatane ke liye
SR_BRAND_TEXT_RE = re.compile(
    r"sarkari\s*result(?:\.com)?|www\.sarkariresult|sarkariresult\.com|"
    r"sarkariresultshine|rojgarresult|"
    r"telegram|t\.me|whatsapp|facebook|instagram|youtube|youtu\.be|"
    r"twitter|x\.com|join\s*(?:channel|now|group)|subscribe|"
    r"android\s*app|apple\s*ios|play\s*store|app\s*store|google\s*play|"
    r"download\s*the\s*sarkari|mobile\s*app\s*from|since\s*201\d|"
    r"image\s*resizer|age\s*calculator|resume\s*cv\s*maker|jpg\s*to\s*pdf",
    re.I,
)

# Koi bhi URL jo in domains/patterns mein ho — output se hatao
SR_BLOCK_URL_PATTERNS = [
    "sarkariresult.com", "sarkariresultshine.com", "rojgarresult.com",
    "telegram", "t.me", "whatsapp", "facebook", "instagram",
    "youtube.com", "youtu.be", "twitter.com", "x.com",
    "play.google", "itunes", "apple-ios", "android-app", "tinyurl",
    "sarkariresults.org.in", "sarkariresult.tools", "sarkariresultportal",
]


def sr_is_blocked_url(url):
    """Own-site / social / app-store link → True (output se hatao)."""
    if not isinstance(url, str) or not url.strip():
        return False
    low = url.lower()
    return any(b in low for b in SR_BLOCK_URL_PATTERNS)


def sr_scrub_text(text):
    """
    String se branding / site-name / social mentions hatao.
    Agar string ek blocked URL hai → khaali kar do.
    """
    if not isinstance(text, str):
        return text
    # FIX D: remove zero-width / non-breaking chars that split words ("Telanga n a")
    text = (text.replace('\u200b', '')   # zero-width space
                .replace('\u00a0', ' ')  # non-breaking space → regular space
                .replace('\u200c', '')   # zero-width non-joiner
                .replace('\u200d', '')   # zero-width joiner
                .replace('\ufeff', ''))  # BOM
    if text.startswith("http") and sr_is_blocked_url(text):
        return ""
    cleaned = SR_BRAND_TEXT_RE.sub("", text)
    # double spaces / stray separators saaf karo
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"^[\s|:\-–—,]+|[\s|:\-–—,]+$", "", cleaned)
    return cleaned.strip()


def sr_scrub_obj(obj, _is_meta_block=False):
    """
    Kisi bhi dict/list/string ko recursively saaf karo:
      - source_url / branding keys drop
      - blocked (own-site/social) URLs drop
      - branding text strip

    INCREMENTAL-SCRAPE FIX: meta.sourceUrl is the ONE exception — it's an
    internal bookkeeping field (never rendered on the public site, see
    generate_all.py which only reads meta.articleSection) used to skip
    re-scraping URLs we already have. It must survive the blocked-URL scrub
    even though its value is literally a sarkariresult.com link, otherwise
    every run loses track of what's already been scraped and re-fetches
    everything every time.
    Empty hue strings/links filter ho jaate hain.
    """
    DROP_KEYS = {"source_url", "url_source", "scraped_from", "site", "site_name",
                 "website_name", "source_site", "source"}

    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in DROP_KEYS:
                continue
            _child_is_meta = _is_meta_block or k == "meta"
            if _child_is_meta and k == "sourceUrl" and isinstance(v, str):
                out[k] = v   # keep as-is, skip the blocked-URL scrub below
                continue
            cv = sr_scrub_obj(v, _is_meta_block=_child_is_meta)
            # link-type values jo blocked hain → skip
            if isinstance(cv, str):
                if cv.startswith("http") and sr_is_blocked_url(cv):
                    continue
                cv = sr_scrub_text(cv) if not cv.startswith("http") else cv
            out[k] = cv
        return out

    if isinstance(obj, list):
        cleaned_list = []
        for it in obj:
            ci = sr_scrub_obj(it, _is_meta_block=_is_meta_block)
            # blocked URL strings list se hatao
            if isinstance(ci, str) and ci.startswith("http") and sr_is_blocked_url(ci):
                continue
            # khaali title/url wale link-dicts hatao
            if isinstance(ci, dict) and set(ci.keys()) <= {"title", "url"}:
                u = ci.get("url", "")
                if not u or sr_is_blocked_url(u):
                    continue
            cleaned_list.append(ci)
        return cleaned_list

    if isinstance(obj, str):
        if obj.startswith("http"):
            return "" if sr_is_blocked_url(obj) else obj
        return sr_scrub_text(obj)

    return obj


def sr_extract_extra_fields(soup, known_labels=None):
    """
    DYNAMIC: Har job page ka HTML alag hota hai. Jo labeled key:value
    sections kisi known field mein map nahi hote, unhe extra_fields{} mein
    capture karo — taaki koi nayi info kabhi miss na ho.

    Detect karta hai:
      - 2-col tables  → col1 = label, col2 = value
      - <li>/<p> with <strong>/<b> inline label → "Label: value"
    Branding/own-site/social entries skip ho jaate hain.
    """
    extra = {}
    if soup is None:
        return extra

    known = set(known_labels or [])

    def _norm_key(label):
        key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        return key[:60]

    def _store(label, value):
        label = clean(label)
        value = clean(value)
        if not label or not value:
            return
        if len(label) > 80 or len(value) > 500:
            return
        # branding/social skip
        if SR_BRAND_TEXT_RE.search(label) or SR_BRAND_TEXT_RE.search(value):
            return
        # link-row values skip (Click Here / yahan click / bare URL)
        if re.search(r"^\s*(click\s*here|यहाँ|download|view|check)\b", value, re.I):
            return
        if value.lower().startswith("http"):
            return
        key = _norm_key(label)
        if not key or key in known:
            return
        # already-known structured labels skip (dates/fee/age/vacancy/links)
        if re.search(r"date|fee|age|vacanc|post|eligib|qualif|salary|link|"
                     r"apply|notification|admit|result|answer|how to|"
                     r"selection|important|website|official|download|"
                     r"click|url|visit|syllabus|login", key):
            return
        if key not in extra:
            extra[key] = value

    content = (soup.find("div", class_="entry-content")
               or soup.find("article") or soup)

    # 2-col tables
    for table in content.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) == 2:
                _store(cells[0].get_text(), cells[1].get_text())

    # <li>/<p> with bold inline label
    for tag in content.find_all(["li", "p"]):
        strong = tag.find(["strong", "b"])
        if not strong:
            continue
        label = strong.get_text()
        full = tag.get_text()
        value = full.replace(label, "", 1)
        value = re.sub(r"^\s*[:\-–—]\s*", "", value)
        if value.strip():
            _store(label, value)

    return extra


# =========================================================
# SOURCE 1 — sarkariresultshine.com HELPERS
# =========================================================

def shine_get_headers():
    return {
        "User-Agent": random.choice(SHINE_USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    }


shine_session = requests.Session()


def shine_get_html(url):
    try:
        r = shine_session.get(url, headers=shine_get_headers(), timeout=30)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print("SHINE REQUEST ERROR:", e)
    return ""


def shine_make_slug(url):
    path = urlparse(url).path.strip("/")
    return path.split("/")[-1]


def shine_is_source_url(url):
    if not url:
        return True
    return SHINE_SOURCE_DOMAIN.lower() in url.lower()


def shine_is_valid_url(url):
    if not url:
        return False
    url = url.strip()
    if not url.startswith("http"):
        return False
    if shine_is_source_url(url):
        return False
    bad = [
        "whatsapp", "telegram", "facebook", "instagram", "twitter", "linkedin",
        # youtube — job links nahi hote
        "youtube.com", "youtu.be",
        # Third-party redirect/affiliate/spam domains
        "uprorg.in", "rojgarresult.com", "govtjobsalert", "sarkariexam.com",
        "sarkarinaukri.com", "naukri.com", "shine.com", "timesjobs.com",
        "monsterindia.com", "rojgarsamachar", "employment-news.in",
        "allindiaroundups", "jobriya", "sarkariresultportal",
        "sarkariresults.org.in", "sarkariresult.tools", "tinyurl.com",
        "bit.ly", "tiny.cc", "cutt.ly", "shorturl", "rebrand.ly",
    ]
    url_lower = url.lower()
    for b in bad:
        if b in url_lower:
            return False
    # EXPLICIT ALLOW: document hosting platforms — always valid for form PDFs
    doc_hosts = [
        "drive.google.com", "docs.google.com",
        "firebasestorage.googleapis.com",
        "storage.googleapis.com",
    ]
    for d in doc_hosts:
        if d in url_lower:
            return True
    return True


def clean_title(title):
    title = re.sub(r"Sarkari\s*Result\s*Shine", "", title, flags=re.I)
    title = re.sub(r"Sarkari Result", "", title, flags=re.I)
    title = re.sub(r"SarkariResult", "", title, flags=re.I)
    title = re.sub(r"\|.*", "", title)
    # trailing " - Sarkari Result" / " -" / stray dashes/pipes
    title = re.sub(r"\s*[-–—|]\s*$", "", title)
    title = re.sub(r"\s*[-–—|]\s*$", "", title)   # twice for "- -"
    return clean(title).strip(" -–—|")


def is_job_page(title, text):
    data = (title + " " + text).lower()
    keywords = ["recruitment", "vacancy", "apply online", "offline form",
                "notification", "application form", "important dates"]
    return sum(1 for k in keywords if k in data) >= 2


def is_news_page(title):
    title = title.lower()
    bad = ["latest news", "breaking", "result live", "live update", "जानिए", "पूरी जानकारी"]
    return any(b in title for b in bad)


def shine_extract_field(labels, soup):
    HEADER_WORDS = {"post name", "total", "eligibility", "name of post",
                    "qualification", "vacancy", "sr no", "s.no", "subject name",
                    "advt no", "category"}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for ridx, row in enumerate(rows):
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue
            key   = clean(cols[0].get_text())
            value = clean(cols[1].get_text())
            # HEADER-ROW GUARD: skip if this row is a table header
            # (all <th>, ya dono cells known header words hain)
            all_th = all(c.name == "th" for c in cols)
            if all_th:
                continue
            if key.lower() in HEADER_WORDS and value.lower() in HEADER_WORDS:
                continue
            for label in labels:
                if label.lower() in key.lower():
                    # value bhi header word ho to galat match → skip
                    if value.lower() in HEADER_WORDS:
                        continue
                    bad_values = ["coming soon", "notify later", "read notice", "-2026"]
                    if value.lower() in bad_values or len(value) > 300:
                        return ""
                    return value
    return ""



def _is_placeholder_date(date_str):
    """
    Fake/placeholder dates filter karo.
    01/01/2026, 01-01-2026 jaise dates real nahi hoti —
    sarkariresultshine aksar inhe "TBD" ki jagah daal deta hai.
    """
    if not date_str:
        return True
    # Normalize
    normalized = date_str.replace("-", "/").strip()
    # 01/01/YYYY pattern — clearly a placeholder
    if re.match(r"^01/01/\d{4}$", normalized):
        return True
    return False


def _cell_first_date(value):
    """Cell se PEHLI real date extract karo (placeholder skip)."""
    dates = re.findall(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', value)
    dates = [d for d in dates if not _is_placeholder_date(d)]
    return dates[0] if dates else ""


def _cell_last_date(value):
    """
    Cell se AAKHIRI real date extract karo (Last Date ke liye).
    Reason: sarkariresultshine ka Last Date cell aksar range format mein hota hai:
      "16-05-2026 to 30-05-2026"  →  Last Date = 30-05-2026  (AAKHIRI date)
    Agar sirf ek real date ho toh wahi return hogi.
    Placeholder dates (01/01/XXXX) skip karta hai.
    """
    dates = re.findall(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', value)
    dates = [d for d in dates if not _is_placeholder_date(d)]
    if len(dates) >= 2:
        return dates[-1]
    return dates[0] if dates else ""


def _extract_real_date(value, mode="first"):
    """
    Cell value se real date(s) nikalo.
    mode="first"  → pehli date (Start Date ke liye)
    mode="last"   → aakhiri date (Last Date ke liye, range mein)
    Sirf DD-MM-YYYY ya DD/MM/YYYY format accept karo.
    Placeholder dates (01/01/XXXX) reject karo.
    """
    dates = re.findall(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', value)
    # Filter out placeholder dates
    dates = [d for d in dates if not _is_placeholder_date(d)]
    if not dates:
        return ""
    if mode == "last":
        return dates[-1]
    return dates[0]


def _match_date_key(key, patterns):
    """Check if any pattern string appears in the key (case-insensitive, already lowered)."""
    return any(p in key for p in patterns)


def shine_extract_dates_from_table(soup):
    result = {"application_start": "", "last_date": "", "exam_date": "", "interview_date": ""}

    # Bad values jo dates nahi hain — inhe skip karo
    BAD_VALUES = {
        "", "-2026", "notify later", "coming soon", "read notice", "notified later",
        "to be notified", "announce later", "will be notified", "tbd", "n/a", "na"
    }

    # Fee-related keywords — agar key mein ye hain toh date row nahi hai, skip karo
    FEE_KEYWORDS = ["fee", "₹", "rs.", "general", "obc", "ews", "sc/st", "female", "payment"]

    # Important Dates table ko identify karne ke liye
    DATE_TABLE_MARKERS = ["important date", "key date", "schedule", "application date",
                          "start date", "last date", "exam date", "interview date"]

    # ── STEP 1: TABLE rows (2-column) ──────────────────────────────────────────
    for table in soup.find_all("table"):
        table_text_lower = clean(table.get_text(" ", strip=True)).lower()

        has_date_marker = any(m in table_text_lower for m in DATE_TABLE_MARKERS)
        has_fee_only    = (
            any(f in table_text_lower for f in ["general/obc/ews", "sc/st fee", "application fee"])
            and not has_date_marker
        )
        if has_fee_only:
            continue

        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])

            # ── 2-column row: key | value ──────────────────────────────────
            if len(cols) >= 2:
                key   = clean(cols[0].get_text()).lower().strip()
                value = clean(cols[1].get_text()).strip()

                if any(f in key for f in FEE_KEYWORDS):
                    continue
                if value.lower() in BAD_VALUES:
                    continue

                if not result["application_start"] and _match_date_key(key, [
                    "start date", "application start", "starting date",
                    "online start", "form start", "begin date", "apply start",
                    "application begin", "apply from", "open date"
                ]):
                    d = _extract_real_date(value, mode="first")
                    if d:
                        result["application_start"] = d

                if not result["last_date"] and _match_date_key(key, [
                    "last date", "closing date", "apply last date",
                    "end date", "last date to apply", "last date for apply",
                    "apply before", "submission last date", "apply upto", "apply up to",
                    "apply till", "close date", "final date"
                ]):
                    d = _extract_real_date(value, mode="last")
                    if d:
                        result["last_date"] = d

                if not result["exam_date"] and _match_date_key(key, [
                    "exam date", "examination date", "written exam", "written test date",
                    "test date", "screening date", "written test", "exam schedule",
                    "examination schedule"
                ]):
                    d = _extract_real_date(value, mode="first")
                    if d:
                        result["exam_date"] = d

                if not result["interview_date"] and _match_date_key(key, [
                    "interview date", "interview schedule", "interview on",
                    "skill test date", "document verification date", "dv date",
                    "walk in", "walk-in", "interview", "counselling date"
                ]):
                    d = _extract_real_date(value, mode="first")
                    if d:
                        result["interview_date"] = d

            # ── 1-column row: key: value inside single cell (some sites) ──
            elif len(cols) == 1:
                cell_text = clean(cols[0].get_text())
                _parse_inline_date_text(cell_text, result, BAD_VALUES)

    # ── STEP 2: <ul><li> tags — sarkariresultshine uses li for Important Dates ─
    # Find all <ul> that contain date-like li items
    for ul in soup.find_all(["ul", "ol"]):
        for li in ul.find_all("li"):
            li_text = clean(li.get_text())
            _parse_inline_date_text(li_text, result, BAD_VALUES)

    # ── STEP 3: Standalone <p> tags with inline "Start Date: ..." pattern ──────
    for p in soup.find_all("p"):
        p_text = clean(p.get_text())
        _parse_inline_date_text(p_text, result, BAD_VALUES)

    return result


def _parse_inline_date_text(text, result, BAD_VALUES):
    """
    "Start Date: 15-05-2026" jaise inline text se dates extract karo.
    `result` dict in-place update hota hai — sirf blank fields fill hote hain.
    """
    if not text:
        return
    text_lower = text.lower()

    # ── application_start ──────────────────────────────────────────────────────
    if not result["application_start"]:
        if any(p in text_lower for p in [
            "start date", "application start", "starting date",
            "online start", "form start", "begin date", "apply start",
            "apply from", "open date", "application begin"
        ]):
            m = re.search(
                r'(?:start date|application start|starting date|online start|'
                r'form start|begin date|apply start|apply from|open date|'
                r'application begin)\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                text, re.I
            )
            if m:
                d = m.group(1)
                if not _is_placeholder_date(d) and d.lower() not in BAD_VALUES:
                    result["application_start"] = d

    # ── last_date ──────────────────────────────────────────────────────────────
    if not result["last_date"]:
        if any(p in text_lower for p in [
            "last date", "closing date", "end date", "apply before",
            "apply upto", "apply till", "close date", "final date",
            "last date to apply", "apply last date"
        ]):
            m = re.search(
                r'(?:last date(?:\s+to\s+apply)?|closing date|end date|'
                r'apply before|apply upto|apply till|close date|final date|'
                r'apply last date)\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                text, re.I
            )
            if m:
                d = m.group(1)
                if not _is_placeholder_date(d) and d.lower() not in BAD_VALUES:
                    result["last_date"] = d
            else:
                # Range format: "16-05-2026 to 30-05-2026" — take last date
                m2 = re.search(
                    r'(?:last date|closing date|end date|apply before|'
                    r'apply upto|apply till|final date)\s*[:\-]?\s*'
                    r'\d{1,2}[-/]\d{1,2}[-/]\d{4}\s+to\s+(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                    text, re.I
                )
                if m2:
                    d = m2.group(1)
                    if not _is_placeholder_date(d) and d.lower() not in BAD_VALUES:
                        result["last_date"] = d

    # ── exam_date ──────────────────────────────────────────────────────────────
    if not result["exam_date"]:
        if any(p in text_lower for p in [
            "exam date", "examination date", "written exam", "test date",
            "written test", "screening date", "exam schedule"
        ]):
            m = re.search(
                r'(?:exam date|examination date|written exam(?:\s+date)?|'
                r'test date|written test(?:\s+date)?|screening date|'
                r'exam schedule)\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                text, re.I
            )
            if m:
                d = m.group(1)
                if not _is_placeholder_date(d) and d.lower() not in BAD_VALUES:
                    result["exam_date"] = d

    # ── interview_date ─────────────────────────────────────────────────────────
    if not result["interview_date"]:
        if any(p in text_lower for p in [
            "interview date", "interview schedule", "walk in", "walk-in",
            "skill test", "document verification", "dv date", "interview on",
            "counselling date"
        ]):
            m = re.search(
                r'(?:interview date|interview schedule|walk[- ]in(?:\s+interview)?|'
                r'skill test(?:\s+date)?|document verification(?:\s+date)?|dv date|'
                r'interview on|counselling date)\s*[:\-]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                text, re.I
            )
            if m:
                d = m.group(1)
                if not _is_placeholder_date(d) and d.lower() not in BAD_VALUES:
                    result["interview_date"] = d


def shine_extract_dates(text):
    # Text-based fallback — table/li parsing ke baad use hota hai sirf
    # Yahan bhi "Start Date" aur "Last Date" dono properly match honge.

    def _extract_first(labels, text):
        """Label ke baad PEHLI real date lo (placeholder 01/01/XXXX skip karo)."""
        for label in labels:
            patterns = [
                rf"{label}\s*[:\-]?\s*([0-9]{{1,2}}[-/][0-9]{{1,2}}[-/][0-9]{{4}})",
                rf"{label}\s*[:\-]?\s*([0-9]{{1,2}}\s+[A-Za-z]+\s+[0-9]{{4}})",
                rf"{label}.*?([0-9]{{1,2}}[-/][0-9]{{1,2}}[-/][0-9]{{4}})",
            ]
            for pattern in patterns:
                for m in re.finditer(pattern, text, re.I | re.S):
                    date_val = clean(m.group(1))
                    if not _is_placeholder_date(date_val):
                        return date_val
        return ""

    def _extract_last_date_from_text(labels, text):
        """
        Last Date ke liye: label ke baad aayi saari dates dhundo
        aur AAKHIRI real date lo (placeholder 01/01/XXXX skip karo).
        Reason: "Last Date : 16-05-2026 to 30-05-2026" mein
        pehli date start date hai, aakhiri actual last date.
        """
        for label in labels:
            # Pehle label ke baad ka segment nikalo
            # Broader lookahead: next recognized label ya newline tak
            m = re.search(
                rf"{label}\s*[:\-]?\s*(.{{1,150}}?)(?=\n\s*(?:Start Date|Exam Date|Interview Date|Application Fee|Selection Process|How to Apply)|$)",
                text, re.I | re.S
            )
            if m:
                segment = m.group(1)
                dates = re.findall(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', segment)
                dates = [d for d in dates if not _is_placeholder_date(d)]
                if dates:
                    return clean(dates[-1])
        return ""

    return {
        "application_start": _extract_first(
            ["Start Date", "Application Start", "Starting Date", "Online Start Date",
             "Form Start Date", "Apply From", "Open Date", "Application Begin"],
            text
        ),
        "last_date": _extract_last_date_from_text(
            ["Last Date to Apply", "Last Date for Apply", "Apply Last Date",
             "Closing Date", "End Date", "Apply Before", "Apply Upto", "Apply Till",
             "Close Date", "Final Date", "Last Date"],
            text
        ),
        "exam_date": _extract_first(
            ["Exam Date", "Examination Date", "Written Exam Date", "Test Date",
             "Written Test Date", "Screening Date", "Exam Schedule"],
            text
        ),
        "interview_date": _extract_first(
            ["Interview Date", "Interview Schedule", "Skill Test Date", "DV Date",
             "Document Verification Date", "Walk-in Interview", "Walk in Interview",
             "Interview On", "Counselling Date"],
            text
        ),
    }


def shine_extract_min_age(text):
    m = re.search(r"Minimum Age\s*[:\-]?\s*([0-9]{1,2})", text, re.I)
    return clean(m.group(1)) if m else ""


def shine_extract_max_age(text):
    m = re.search(r"Maximum Age\s*[:\-]?\s*([0-9]{1,2})", text, re.I)
    return clean(m.group(1)) if m else ""


def shine_extract_fee(label, text):
    m = re.search(rf"{label}\s*[:\-]?\s*(?:Rs\.?)?\s*([0-9]+)", text, re.I)
    return clean(m.group(1)) if m else ""


def shine_extract_application_fees_dynamic(soup, text=""):
    """
    DYNAMIC fee extraction — fee table/list ke saare category labels capture karo,
    verbatim (e.g. 'General (Male)', 'OSC/DSC/ESM', 'PH (Divyang)').
    Returns dict {label: value} + payment_mode agar mile.
    """
    fees = {}
    BRAND = re.compile(r"sarkari|whatsapp|telegram|read also|join", re.I)

    def _norm(lbl):
        return re.sub(r"[^a-z0-9]+", "_", lbl.lower()).strip("_")[:50]

    def _fee_val(v):
        v = clean(v)
        if re.search(r"nil|free|exempt", v, re.I):
            return "0"
        m = re.search(r"\d[\d,]*", v)
        return m.group(0).replace(",", "") if m else ""

    # 1) Fee heading ke neeche ka table ya list
    for tag in soup.find_all(["h2", "h3", "h4", "strong", "b", "p"]):
        ht = clean(tag.get_text()).lower()
        if not re.search(r"application fee|exam fee|fee detail|आवेदन शुल्क", ht):
            continue
        for sib in tag.find_all_next():
            if sib.name in ("h2", "h3") and sib is not tag:
                break
            if sib.name in ("ul", "ol"):
                for li in sib.find_all("li"):
                    t = clean(li.get_text(" "))
                    if BRAND.search(t):
                        continue
                    m = re.match(r"(.+?)\s*[:：]\s*(.+)", t)
                    if m:
                        lbl, val = m.group(1).strip(), _fee_val(m.group(2))
                        if "payment" in lbl.lower() or "mode" in lbl.lower():
                            fees["payment_mode"] = clean(m.group(2))
                        elif val:
                            fees[_norm(lbl)] = val
                break
            if sib.name == "table":
                for tr in sib.find_all("tr"):
                    cells = [clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
                    if len(cells) >= 2 and cells[0] and not BRAND.search(cells[0]):
                        lbl = cells[0]
                        if "payment" in lbl.lower() or "mode" in lbl.lower():
                            fees["payment_mode"] = cells[1]
                        else:
                            val = _fee_val(cells[1])
                            if val:
                                fees[_norm(lbl)] = val
                break
        if fees:
            break

    # 2) Fallback: inline text patterns
    if not fees and text:
        for lbl in ["General", "OBC", "EWS", "SC/ST", "SC", "ST", "Female", "PH"]:
            v = shine_extract_fee(re.escape(lbl), text)
            if v:
                fees[_norm(lbl)] = v
    return fees


def shine_extract_application_fees(text):
    return {
        "general_obc_ews": shine_extract_fee("General", text),
        "sc_st":           shine_extract_fee("SC/ST", text),
        "female":          shine_extract_fee("Female", text),
    }


def shine_extract_links(soup):
    """
    Job detail page ke Important Links table se saare relevant links scrape karta hai.

    Supported label variants (case-insensitive, partial match):
    ┌─────────────────────────────────┬─────────────────────────────────────────┐
    │ Label on site                   │ Output key                              │
    ├─────────────────────────────────┼─────────────────────────────────────────┤
    │ Form PDF Free                   │ form_pdf_free_link                      │
    │ Application Form PDF Free       │ form_pdf_free_link                      │
    │ Application Form PDF            │ application_form_pdf_link               │
    │ Form PDF                        │ form_pdf_link                           │
    │ Apply Online                    │ apply_online_link                       │
    │ Official Notification PDF       │ official_notification_pdf_link          │
    │ Official Website                │ official_website_link                   │
    └─────────────────────────────────┴─────────────────────────────────────────┘
    Each key stores the first valid URL found for that label.
    """
    result = {
        "form_pdf_free_link":            "",   # "Form PDF Free" / "Application Form PDF Free"
        "application_form_pdf_link":     "",   # "Application Form PDF"
        "form_pdf_link":                 "",   # "Form PDF" (no "free" in label)
        "apply_online_link":             "",   # "Apply Online"
        "official_notification_pdf_link":"",   # "Official Notification PDF"
        "official_website_link":         "",   # "Official Website"
    }

    # ── Label → key mapping rules (checked IN ORDER; first match wins per row) ──
    # Each rule: (list_of_substrings_that_must_ALL_be_in_label, output_key)
    # More specific rules come FIRST so they take priority over generic ones.
    LABEL_RULES = [
        # ── Free form variants (with OR without "pdf" word) ──────────────
        (["form pdf free"],                      "form_pdf_free_link"),
        (["application form pdf free"],          "form_pdf_free_link"),
        # "Application Form Free" (no "pdf") — common on Shine pages
        (["application form free"],              "form_pdf_free_link"),
        (["form free"],                          "form_pdf_free_link"),
        # "application form pdf" (no "free")  → application_form_pdf_link
        (["application form pdf"],               "application_form_pdf_link"),
        # "application form" alone → application_form_pdf_link
        (["application form"],                   "application_form_pdf_link"),
        # "form pdf" alone (no "free", no "application") → form_pdf_link
        (["form pdf"],                           "form_pdf_link"),
        # "download" as label — treat as free form link on Shine pages
        (["download"],                           "form_pdf_free_link"),
        # "apply online"
        (["apply online"],                       "apply_online_link"),
        (["apply link"],                         "apply_online_link"),
        (["apply now"],                          "apply_online_link"),
        # "official notification pdf" / "notification pdf"
        (["notification pdf"],                   "official_notification_pdf_link"),
        (["official notification"],              "official_notification_pdf_link"),
        (["advertisement"],                      "official_notification_pdf_link"),
        (["advt"],                               "official_notification_pdf_link"),
        (["notification"],                       "official_notification_pdf_link"),
        # "official website" / "official site"
        (["official website"],                   "official_website_link"),
        (["official site"],                      "official_website_link"),
        (["official link"],                      "official_website_link"),
    ]

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue

            label_raw = clean(cols[0].get_text())
            label     = label_raw.lower()

            # Collect all valid hrefs from this row (could be multiple <a> tags)
            hrefs = []
            for a in cols[1].find_all("a", href=True):
                link = a["href"].strip()
                if shine_is_valid_url(link):
                    hrefs.append(link)
            if not hrefs:
                continue

            # Match label against rules
            for substrings, key in LABEL_RULES:
                if all(s in label for s in substrings):
                    # Only set if not already filled (first occurrence wins)
                    if not result[key]:
                        result[key] = hrefs[0]
                    break   # One rule per row

    return result


def shine_extract_how_to_apply_soup(soup):
    """How to Apply — heading ke neeche ka <ul>/<ol> list (structured)."""
    BRAND = re.compile(r"sarkari|whatsapp|telegram|read also|join now|disclaimer|"
                       r"sarkariresultshine|follow x", re.I)
    for tag in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
        ht = clean(tag.get_text()).lower()
        if not re.search(r"how to apply|how to fill|apply process|आवेदन कैसे", ht):
            continue
        nxt = tag.find_next(["ul", "ol"])
        if nxt:
            steps = []
            for li in nxt.find_all("li"):
                t = clean(li.get_text(" "))
                if t and not BRAND.search(t) and len(t) > 4:
                    steps.append(t)
            if steps:
                return steps
    return []


def shine_extract_how_to_apply(text):
    m = re.search(
        r"How to Apply(.*?)(Important Dates|Application Fee|Selection Process|"
        r"Important Links|Read Also|Disclaimer|Join WhatsApp|Join Telegram|"
        r"Frequently asked|$)",
        text, re.I | re.S
    )
    if m:
        data = clean(m.group(1))
        data = re.sub(r"Frequently asked questions.*", "", data, flags=re.I | re.S)
        data = re.sub(r"Important Links\s*📌.*", "", data, flags=re.I | re.S)
        data = re.sub(r"📌\s*Read Also.*", "", data, flags=re.I | re.S)
        data = re.sub(r"Read Also\s*[:\-].*", "", data, flags=re.I | re.S)
        data = re.sub(r"Disclaimer\s*[:\-]?.*", "", data, flags=re.I | re.S)
        data = re.sub(
            r"(?:SarkariResultShine\.com|SarkariResult(?:Shine)?)\s*(?:\(Sarkari Result\))?"
            r"[^\n]*", "", data, flags=re.I)
        data = re.sub(r"(?:Sarkari Result\s+)?(?:WhatsApp|Telegram)\s+Channel.*", "", data, flags=re.I | re.S)
        data = re.sub(r"\bJoin Now\b.*", "", data, flags=re.I | re.S)
        data = re.sub(r"[^\n]*sarkariresultshine[^\n]*", "", data, flags=re.I)
        data = re.sub(r"[^\n]*sarkariresult\.com[^\n]*", "", data, flags=re.I)
        data = re.sub(r"[📌🔗📢📣]+", "", data)
        data = clean(data)
        return data          # no hard truncation
    return ""


def shine_extract_jobs_info(soup):
    for p in soup.find_all("p"):
        txt = clean(p.get_text())
        if len(txt) > 120 and "vacancy" in txt.lower():
            txt = re.sub(r"Join WhatsApp.*", "", txt, flags=re.I)
            txt = re.sub(r"Join Telegram.*", "", txt, flags=re.I)
            return f'<p style="text-align: justify;">{txt}</p>'
    return ""


def shine_extract_vacancy_details(soup):
    final = []
    seen  = set()
    junk = ["organization", "salary", "apply mode", "job location",
            "important links", "post name", "whatsapp", "telegram",
            "join now", "name of division/project", "official notification",
            "official website", "apply online", "form pdf", "download",
            "admit card", "result", "answer key", "syllabus"]
    invalid = ["coming soon", "notify later", "read notice", "click", "click here",
               "join", "visit", "download", "apply now"]
    LINK_HDR = re.compile(r"important link|useful link|download|apply online", re.I)
    ELIG_HDR = re.compile(r"eligib|vacancy|post detail|qualification", re.I)
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        # table context heading — link tables skip karo
        prev = table.find_previous(["h2", "h3", "h4"])
        prev_txt = clean(prev.get_text()) if prev else ""
        if LINK_HDR.search(prev_txt):
            continue
        # heading eligibility/vacancy nahi aur table me links hain → skip
        if not ELIG_HDR.search(prev_txt) and table.find("a", href=True):
            continue
        hdr_cells = [clean(c.get_text()).lower() for c in rows[0].find_all(["td", "th"])]
        has_total = any("total" in h for h in hdr_cells)
        for row in rows:
            if row.find("a", href=True):       # link row → skip
                continue
            cols = [clean(c.get_text()) for c in row.find_all(["td", "th"])]
            cols = [c for c in cols if c]
            if len(cols) < 2:
                continue
            post_name = cols[0]
            if any(j in post_name.lower() for j in junk):
                continue
            if len(cols) >= 3:
                total = clean_total_value(cols[1])
                eligibility = clean_extra_text(cols[2])
            else:
                if has_total:
                    continue
                total = ""
                eligibility = clean_extra_text(cols[1])
            if total.lower() in invalid or eligibility.lower() in invalid:
                continue
            if not eligibility or len(eligibility) < 5:
                continue
            if len(eligibility) > 400:
                eligibility = eligibility[:400]
            key = post_name + total
            if key in seen:
                continue
            seen.add(key)
            final.append({"post_name": post_name, "total": total,
                          "eligibility": eligibility})
    return final


def shine_get_job_links(category_url):
    """
    Offline Form category page se ORDERED links scrape karta hai.
    - Active Jobs section completely IGNORE karta hai
    - Sirf Offline Form table rows consider karta hai
    - Page sequence aur row sequence exactly preserve hoti hai
    Returns list of dicts: [{"date": ..., "href": ..., "title": ...}, ...]
    """
    html = shine_get_html(category_url)
    if not html:
        return []
    soup  = BeautifulSoup(html, "html.parser")
    links = []
    seen_hrefs = set()

    for table in soup.find_all("table"):
        # Table header check — "Active Jobs" wali table skip karo
        header_text = ""
        # Check thead or first tr for header
        first_tr = table.find("tr")
        if first_tr:
            header_text = clean(first_tr.get_text()).lower()
        # Also check any th/caption
        caption = table.find("caption")
        if caption:
            header_text += " " + clean(caption.get_text()).lower()

        # "Active Jobs" table? SKIP completely
        if "active" in header_text and "job" in header_text:
            print(f"  [SKIP] Active Jobs table detected — ignoring")
            continue

        # Look for "Offline Form" marker — accept only such tables
        # (Some pages have the heading in a preceding element; check table text)
        table_text_lower = clean(table.get_text(" ", strip=True)).lower()
        if "active job" in table_text_lower and "offline form" not in table_text_lower:
            print(f"  [SKIP] Table contains only Active Jobs — ignoring")
            continue

        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            # col[0] = date, col[1] = post link
            date_text = clean(cols[0].get_text())
            a = cols[1].find("a", href=True)
            if not a:
                continue

            href  = a["href"].strip()
            title = clean(a.get_text())

            if SHINE_SOURCE_DOMAIN not in href:
                continue
            if "/category/" in href or "page/" in href:
                continue

            slug = shine_make_slug(href)
            if any(x in slug for x in ["about", "contact", "privacy-policy", "disclaimer", "feed"]):
                continue

            keywords = ["recruitment", "vacancy", "bharti", "apply", "notification", "posts"]
            if not any(k in title.lower() for k in keywords):
                continue

            # Duplicate href skip
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            links.append({"date": date_text, "href": href, "title": title})

    print(f"  SHINE ORDERED LINKS FOUND: {len(links)}")
    return links


def shine_get_latest_job_links(category_url):
    """
    Latest Jobs category page se ORDERED links scrape karta hai.
    Job + Non-Job dono types collect karta hai (Result, Admit Card, etc. bhi).

    Strategy (4-tier):
      Tier-1: Tables with date column — most structured (date + title pairs)
      Tier-2: class="side_info_th" sidebar container
      Tier-3: Main article loop — h2.entry-title / .post-title / article a
      Tier-4: Broad page scan (last resort)

    Returns list of dicts: [{"date": ..., "href": ..., "title": ...}, ...]
    """
    html = shine_get_html(category_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen_hrefs = set()

    # Accept ALL content types — Jobs + Non-Jobs both
    # Only skip pure navigation/utility pages
    SKIP_SLUGS = {"about", "contact", "privacy-policy", "disclaimer",
                  "feed", "tag", "author", "sitemap", "advertise"}

    def _is_valid_latest_job_href(href):
        """Latest Jobs ke liye valid href check — ALL content types accept."""
        if not href:
            return False
        href = href.strip()
        if not href.startswith("http"):
            return False
        if SHINE_SOURCE_DOMAIN not in href:
            return False
        if "/category/" in href or "/page/" in href or "?p=" in href:
            return False
        slug = shine_make_slug(href)
        if any(x in slug for x in SKIP_SLUGS):
            return False
        return True

    def _add_link(href, title, date_text=""):
        """Deduplicate aur add karo — NO keyword filter (job + non-job dono)."""
        if not href:
            return
        href = href.strip()
        if href in seen_hrefs:
            return
        if not _is_valid_latest_job_href(href):
            return
        title = clean(title)
        if not title or len(title) < 6:
            return
        seen_hrefs.add(href)
        links.append({"date": date_text, "href": href, "title": title})

    # ── Tier-1: Tables with date column (most structured) ─────────────────────
    # sarkariresultshine category pages often have a table with:
    # col[0]=date, col[1]=title+link
    tier1_count = 0
    for table in soup.find_all("table"):
        # Skip nav/footer tables
        table_text = clean(table.get_text(" ", strip=True)).lower()
        if any(nav in table_text for nav in ["home", "about us", "contact us",
                                              "privacy policy", "disclaimer"]):
            if len(table_text) < 300:  # Small nav table
                continue
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue
            # date in col[0], link in col[1] (or col[1] onwards)
            date_text = clean(cols[0].get_text())
            # Validate it looks like a date or date-like text
            date_like = bool(re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}|'
                                        r'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec',
                                        date_text, re.I))
            if not date_like:
                date_text = ""
            # Find anchor in remaining columns
            for col in cols[1:]:
                a = col.find("a", href=True)
                if a:
                    href  = a["href"].strip()
                    title = clean(a.get_text())
                    _add_link(href, title, date_text)
                    tier1_count += 1
                    break

    print(f"  [T1-tables] Checked: {tier1_count}, Links so far: {len(links)}")

    # ── Tier-2: side_info_th / sidebar containers ─────────────────────────────
    side_containers = []
    side_containers += soup.find_all(class_=lambda c: c and "side_info_th" in c)
    for tag in soup.find_all(id=lambda i: i and any(
            x in i.lower() for x in ["side_info", "sidebar", "latest-job",
                                      "latest_job", "recentposts"])):
        side_containers.append(tag)
    for cls in ["widget_recent_entries", "widget-recent-posts",
                "recent-posts-widget", "lcp_catlist", "cat-post-widget",
                "widget_categories"]:
        side_containers += soup.find_all(class_=lambda c: c and cls in c)

    tier2_count = 0
    for container in side_containers:
        for a in container.find_all("a", href=True):
            href  = a["href"].strip()
            title = clean(a.get_text())
            # Try to find associated date (sibling or parent td)
            date_text = ""
            parent = a.find_parent(["li", "tr", "td"])
            if parent:
                date_m = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',
                                   clean(parent.get_text()))
                if date_m:
                    date_text = date_m.group(0)
            _add_link(href, title, date_text)
            tier2_count += 1

    print(f"  [T2-sidebar] Candidates: {tier2_count}, Links so far: {len(links)}")

    # ── Tier-3: Main article loop (WordPress post cards) ─────────────────────
    article_count = 0
    main_content = soup.find(["main", "div"],
                              id=lambda i: i and any(
                                  x in i.lower() for x in
                                  ["main", "content", "primary", "blog-entries"]))
    if not main_content:
        main_content = soup

    for article in main_content.find_all(
            ["article", "div"],
            class_=lambda c: c and any(
                x in " ".join(c if isinstance(c, list) else [c]) for x in
                ["post-", "entry", "article", "hentry", "blog-post", "td-block-span"])):
        # Find date metadata
        date_text = ""
        date_el = article.find(["time", "span", "div"],
                                class_=lambda c: c and any(
                                    x in " ".join(c if isinstance(c, list) else [c])
                                    for x in ["date", "time", "published", "entry-date"]))
        if date_el:
            dt_attr = date_el.get("datetime", "")
            date_text = clean(dt_attr or date_el.get_text())

        # Title/heading anchor
        heading = article.find(
            ["h1", "h2", "h3"],
            class_=lambda c: c and any(
                x in " ".join(c if isinstance(c, list) else [c]) for x in
                ["entry-title", "post-title", "article-title", "td-module-title"]))
        if not heading:
            heading = article.find(["h2", "h3", "h1"])

        if heading:
            a = heading.find("a", href=True)
            if a:
                _add_link(a["href"].strip(), clean(a.get_text()), date_text)
                article_count += 1
                continue

        # Fallback: article's first substantive anchor
        for a in article.find_all("a", href=True):
            title = clean(a.get_text())
            if len(title) > 12:
                _add_link(a["href"].strip(), title, date_text)
                article_count += 1
                break

    print(f"  [T3-articles] Checked: {article_count}, Links so far: {len(links)}")

    # ── Tier-4: Broad page scan (last resort) ────────────────────────────────
    if len(links) < 5:
        print(f"  [T4-broad] Tiers 1-3 insufficient ({len(links)}), broad scan...")
        for skip_tag in soup.find_all(["nav", "header", "footer"]):
            skip_tag.decompose()
        for a in soup.find_all("a", href=True):
            href  = a["href"].strip()
            title = clean(a.get_text())
            if len(title) > 10:
                _add_link(href, title, "")

    print(f"  SHINE LATEST JOB LINKS FOUND ON PAGE: {len(links)}")
    return links



# ── Smart classification for sarkariresultshine_latest_jobs_top100 ───────────

_LJ_JOB_TYPES = {
    "Government Job": [
        "sarkari naukri", "government job", "govt job", "public sector",
        "state government", "central government", "psc", "upsc", "ssc",
        "rajya sarkar", "kendriya", "recruitment", "bharti",
    ],
    "Railway": [
        "railway", "rrb", "rer", "indian railways", "rail", "ntpc",
        "group d", "group c", "loco pilot", "technician",
    ],
    "Bank": [
        "bank", "ibps", "sbi", "rbi", "nabard", "rrb bank", "banking",
        "clerk", "po ", "probationary officer", "financial services",
    ],
    "Defense": [
        "army", "navy", "air force", "airforce", "defence", "defense",
        "military", "crpf", "bsf", "cisf", "itbp", "ssb", "nda", "cds",
        "constable", "police", "paramilitary",
    ],
    "Teaching": [
        "teacher", "teaching", "lecturer", "professor", "faculty",
        "principal", "headmaster", "shikshak", "tet", "ctet", "b.ed",
        "school", "college", "university", "education department",
        "shiksha vibhag",
    ],
    "Bank": [
        "bank", "ibps", "sbi", "rbi", "nabard", "banking",
    ],
    "Apprentice": [
        "apprentice", "apprenticeship", "trainee", "trade apprentice",
        "iti apprentice",
    ],
    "Walk-in": [
        "walk-in", "walk in interview", "walkin",
    ],
    "Private Job": [
        "private", "pvt", "ltd", "corporate", "mnc", "it job", "software",
    ],
    "Contractual": [
        "contractual", "contract basis", "temporary", "adhoc",
        "engagement", "deputation",
    ],
    "Overseas Job": [
        "abroad", "overseas", "foreign", "gulf", "dubai", "canada",
        "international", "videsh",
    ],
}

_LJ_NON_JOB_TYPES = {
    "Result": [
        "result", "परिणाम", "final result", "merit list", "score card",
        "marks", "selection list", "written result",
    ],
    "Admit Card": [
        "admit card", "hall ticket", "call letter", "pravesha patra",
        "admit", "pravesh patra",
    ],
    "Answer Key": [
        "answer key", "answerkey", "answer sheet", "official key",
        "objection", "provisional key",
    ],
    "Syllabus": [
        "syllabus", "exam pattern", "pattern", "curriculum", "paatyakram",
    ],
    "Admission": [
        "admission", "counselling", "counseling", "pravesh", "enrollment",
        "seat allotment", "round allotment",
    ],
    "Scholarship": [
        "scholarship", "fellowship", "stipend", "chatravritti",
    ],
    "Yojana": [
        "yojana", "scheme", "योजना", "mission", "abhiyan",
    ],
    "Loan": [
        "loan", "kisan credit", "mudra", "financial assistance",
    ],
    "Merit List": [
        "merit list", "waiting list", "provisional list", "cut off",
        "cutoff",
    ],
    "News Update": [
        "latest news", "breaking news", "update", "notification news",
        "जानिए", "पूरी जानकारी",
    ],
    "Counseling": [
        "counselling", "counseling", "काउंसलिंग",
    ],
    "Registration": [
        "registration", "apply online", "online form", "avedan",
    ],
    "Exam Date": [
        "exam date", "exam schedule", "pariksha tithi", "exam notice",
    ],
    "PPP/BPL/Family ID Updates": [
        "ppp", "bpl", "family id", "parivar pehchan patra",
        "ration card", "aadhar", "aayushman",
    ],
}


def shine_classify_latest_job_entry(title, url, heading_text="", content_text=""):
    """
    Smart classification: Job ya Non-Job — exact type bhi batata hai.
    Returns: (entry_type, sub_type)
    """
    title_low = (title or "").lower()
    combined = " ".join([
        title or "", url or "", heading_text or "", (content_text or "")[:500]
    ]).lower()

    # ── STRONG JOB signal from TITLE — recruitment/vacancy pages ──────────────
    # Ye result/merit-list signals se PEHLE dominate karte hain.
    STRONG_JOB = [
        "vacancy", "recruitment", "bharti", "apply online for",
        "online form", "recruitment drive", "various post", "posts recruitment",
    ]
    # ...lekin sirf tab jab title clearly result/admit/answer-key na ho
    PURE_NONJOB = ["result", "merit list", "admit card", "hall ticket",
                   "answer key", "cut off", "cutoff", "score card",
                   "selected candidates", "counselling result"]
    title_is_nonjob = any(k in title_low for k in PURE_NONJOB)

    if not title_is_nonjob and any(k in title_low for k in STRONG_JOB):
        # job type detect karo (department-wise) warna Government Job
        for sub_type, keywords in _LJ_JOB_TYPES.items():
            if any(k in combined for k in keywords):
                return ("JOB", sub_type)
        return ("JOB", "Recruitment")

    # ── Non-Job check — TITLE pe priority (content me 'result' branding se galat match) ──
    # Pass 1: title-only match (sabse reliable signal)
    for sub_type, keywords in _LJ_NON_JOB_TYPES.items():
        if sub_type == "Registration":
            continue
        if any(k in title_low for k in keywords):
            return ("NON_JOB", sub_type)

    # Pass 2: combined (heading+content) match — title me clear signal nahi tha
    for sub_type, keywords in _LJ_NON_JOB_TYPES.items():
        if sub_type == "Registration":
            continue
        if any(k in combined for k in keywords):
            return ("NON_JOB", sub_type)

    # ── Job type check ────────────────────────────────────────────────────────
    for sub_type, keywords in _LJ_JOB_TYPES.items():
        if any(k in combined for k in keywords):
            return ("JOB", sub_type)

    # ── Fallback ──────────────────────────────────────────────────────────────
    job_signals = ["vacancy", "post", "notification", "application", "form",
                   "qualification", "age limit", "eligibility", "bharti",
                   "नौकरी", "रिक्ति", "आवेदन"]
    if any(s in combined for s in job_signals):
        return ("JOB", "Government Job")

    return ("NON_JOB", "News Update")


def _shine_lj_get_content_container(soup):
    """
    Detail page se main content container nikalo.
    Multiple selectors try karta hai — first match return.
    """
    CONTENT_SELECTORS = [
        # Class-based
        {"class_": lambda c: c and "td-post-content" in " ".join(c if isinstance(c, list) else [c])},
        {"class_": lambda c: c and "entry-content" in " ".join(c if isinstance(c, list) else [c])},
        {"class_": lambda c: c and "post-content" in " ".join(c if isinstance(c, list) else [c])},
        {"class_": lambda c: c and "inside-article" in " ".join(c if isinstance(c, list) else [c])},
        {"class_": lambda c: c and "single-content" in " ".join(c if isinstance(c, list) else [c])},
        {"class_": lambda c: c and "the-content" in " ".join(c if isinstance(c, list) else [c])},
        {"class_": lambda c: c and "thecontent" in " ".join(c if isinstance(c, list) else [c])},
        {"class_": lambda c: c and "article-content" in " ".join(c if isinstance(c, list) else [c])},
    ]

    # Tag-based fallbacks
    for tag in ["article", "main"]:
        el = soup.find(tag)
        if el:
            inner = el.find("div", class_=lambda c: c and any(
                x in " ".join(c if isinstance(c, list) else [c])
                for x in ["content", "post", "entry", "article-body"]))
            if inner:
                return inner

    for sel in CONTENT_SELECTORS:
        el = soup.find(["div", "section", "article"], **sel)
        if el:
            return el

    # Last resort: article or main tag
    for tag in ["article", "main"]:
        el = soup.find(tag)
        if el:
            return el

    return soup.find("body") or soup


def _shine_lj_clean_container(container):
    """
    Noise elements remove karo — ads, socials, nav, tracking.
    Tables aur important content preserve karo.
    """
    REMOVE_CLASSES = [
        "sharedaddy", "share-buttons", "jp-relatedposts", "related-posts",
        "related_posts", "wpcnt", "wp-block-ad", "ad-wrapper", "adsbygoogle",
        "sidebar", "widget", "popup", "modal", "overlay", "cookie",
        "breadcrumb", "crumb", "pagination", "nav-links", "post-navigation",
        "author-box", "author-bio", "comments", "respond", "comment-form",
        "social-share", "social-icons", "sharing-buttons", "newsletter-form",
        "subscribe", "subscription", "disclaimer-box",
    ]
    REMOVE_TAGS = ["script", "style", "iframe", "noscript", "form",
                   "button", "input", "select", "textarea"]

    container = BeautifulSoup(str(container), "html.parser")
    for tag in container.find_all(REMOVE_TAGS):
        tag.decompose()
    for cls in REMOVE_CLASSES:
        for el in container.find_all(
                class_=lambda c: c and cls in " ".join(c if isinstance(c, list) else [c])):
            el.decompose()
    # Remove tracking pixels / tiny images
    for img in container.find_all("img"):
        w = img.get("width", "")
        h = img.get("height", "")
        try:
            if int(w) <= 1 or int(h) <= 1:
                img.decompose()
        except Exception:
            pass
    return container


def _shine_lj_extract_table(table):
    """
    Single table ko structured dict me convert karo.
    Nested tables bhi handle karta hai.
    Social media / channel rows automatically skip karta hai.
    """
    rows = []
    headers = []

    # Social/spam row detection — agar kisi cell me ye words ho toh row skip
    _TABLE_ROW_BLOCKED_WORDS = [
        "telegram channel", "whatsapp channel", "join telegram", "join whatsapp",
        "join now", "follow x", "follow twitter", "follow facebook",
        "youtube channel", "subscribe", "gokulgopal",
        "sarkari result telegram", "sarkari result whatsapp",
        "sarkariresult", "sarkariresultshine",
        "join channel", "follow us",
    ]

    def _is_social_row(cells):
        """Return True if any cell text matches social/spam pattern."""
        for cell in cells:
            ct = cell.get_text(" ", strip=True).lower()
            if any(w in ct for w in _TABLE_ROW_BLOCKED_WORDS):
                return True
        return False

    # Headers from thead or first tr with th
    thead = table.find("thead")
    if thead:
        header_row = thead.find("tr")
        if header_row:
            headers = [clean(th.get_text(" ", strip=True))
                       for th in header_row.find_all(["th", "td"])]

    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr", recursive=False):
        # Check if this is a header row
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        # If all cells are th, treat as header
        if all(c.name == "th" for c in cells) and not headers:
            headers = [clean(c.get_text(" ", strip=True)) for c in cells]
            continue

        # Skip social media / channel rows
        if _is_social_row(cells):
            continue

        row_data = []
        for cell in cells:
            # Check for nested table
            nested = cell.find("table")
            if nested:
                cell_text = clean(cell.get_text(" ", strip=True))
            else:
                cell_text = clean(cell.get_text(" ", strip=True))
            row_data.append(cell_text)

        if any(row_data):
            rows.append(row_data)

    return {"headers": headers, "rows": rows}


def _shine_dedup_tables(tables, vacancy_details):
    """
    details_page_content.tables se woh tables hatao jo already structured
    fields me capture ho chuke hain (vacancy_details = eligibility table,
    link tables = all_links/important_links).  Duplicate data avoid karne ke liye.
    """
    if not tables:
        return []
    # vacancy post-names set (eligibility table detect karne ke liye)
    vac_posts = {(v.get("post_name") or "").strip().lower()
                 for v in (vacancy_details or [])}
    out = []
    LINKWORD = re.compile(r"download|click here|notification pdf|apply online|"
                          r"official website|admit card|view|visit|form pdf", re.I)
    for t in tables:
        rows = t.get("rows", [])
        headers = [h.lower() for h in t.get("headers", [])]
        heading = (t.get("table_heading") or "").lower()

        # 1) Link table: rows me 'Download'/'Click Here' jaise link-cells →
        #    ye all_links me already hai → skip
        link_cells = 0
        total_cells = 0
        for r in rows:
            for c in r:
                total_cells += 1
                if LINKWORD.search(str(c)):
                    link_cells += 1
        if total_cells and link_cells / total_cells >= 0.4:
            continue
        if "important link" in heading or "useful link" in heading:
            continue

        # 2) Eligibility/vacancy table: rows ke first-col post-names
        #    vacancy_details se match karte hain → already captured → skip
        if vac_posts and rows:
            row_posts = {(r[0].strip().lower() if r else "") for r in rows}
            overlap = row_posts & vac_posts
            if len(overlap) >= max(1, len(rows) // 2):
                continue
        if "eligibility" in heading or "vacancy" in heading or \
           any("post name" in h for h in headers):
            continue

        out.append(t)
    return out


def _shine_dedup_headings(headings):
    """FAQ question headings (Q1./Q2./Frequently asked) ko headings se hatao —
    ye faqs[] me already structured hain."""
    FAQ_H = re.compile(r"^(❓|q\d+[.\)]|frequently asked|faq)", re.I)
    return [h for h in (headings or []) if not FAQ_H.match(h.strip())]


def _shine_lj_extract_all_tables(container):
    """All tables from content container — structured extraction."""
    tables_data = []
    seen_tables = set()
    _READ_ALSO = re.compile(r"read also|join (?:whatsapp|telegram|channel)|"
                            r"sarkari result shine|disclaimer", re.I)

    for table in container.find_all("table"):
        table_html = str(table)
        table_hash = hashlib.md5(table_html.encode()).hexdigest()[:8]
        if table_hash in seen_tables:
            continue
        seen_tables.add(table_hash)

        # Skip cross-promo "Read Also" tables entirely
        if _READ_ALSO.search(clean(table.get_text(" "))[:120]):
            continue

        tbl = _shine_lj_extract_table(table)
        # Skip empty or header-only tables
        if not tbl["rows"] and not tbl["headers"]:
            continue
        # Try to detect table heading from preceding sibling
        heading = ""
        prev = table.find_previous_sibling(["h2", "h3", "h4", "p", "strong"])
        if prev:
            h_text = clean(prev.get_text())
            if 3 < len(h_text) < 120 and not _READ_ALSO.search(h_text):
                heading = h_text
        if not heading:
            caption = table.find("caption")
            if caption and not _READ_ALSO.search(caption.get_text()):
                heading = clean(caption.get_text())

        tbl["table_heading"] = heading
        tables_data.append(tbl)

    return tables_data


def _shine_lj_extract_important_links(soup, base_url=""):
    """
    Important Links table + all external links from content.
    Returns structured dict of labelled links + a list of all_links.

    FILTER RULES (sarkariresultshine_latest_jobs_top100 only):
      - Source domain (sarkariresultshine.com) links NEVER included
      - Social/channel URLs blocked: telegram, t.me, whatsapp, facebook,
        instagram, youtube, twitter, x.com, and similar
      - Bad labels blocked: join now, channel, follow x, gokulgopal, etc.
      - Only official job-relevant links kept in all_links
    """
    result = {
        "apply_online":            "",
        "official_notification":   "",
        "official_website":        "",
        "admit_card":              "",
        "result_link":             "",
        "answer_key":              "",
        "syllabus":                "",
        "login":                   "",
        "download":                "",
    }
    all_links = []
    seen_urls = set()

    LINK_LABEL_MAP = [
        (["apply online"],              "apply_online"),
        (["online form"],               "apply_online"),
        (["admit card"],                "admit_card"),
        (["hall ticket"],               "admit_card"),
        (["download admit"],            "admit_card"),
        (["result"],                    "result_link"),
        (["final result"],              "result_link"),
        (["answer key"],                "answer_key"),
        (["answerkey"],                 "answer_key"),
        (["syllabus"],                  "syllabus"),
        (["notification pdf"],          "official_notification"),
        (["official notification"],     "official_notification"),
        (["notification"],              "official_notification"),
        (["advertisement"],             "official_notification"),
        (["advt"],                      "official_notification"),
        (["official website"],          "official_website"),
        (["official site"],             "official_website"),
        (["login"],                     "login"),
        (["download"],                  "download"),
    ]

    # ── Blocked URL patterns (social media, source domain, spam) ─────────────
    _LJ_BLOCKED_URL_WORDS = [
        SHINE_SOURCE_DOMAIN,           # sarkariresultshine.com
        "t.me/", "telegram.me", "telegram.org",
        "whatsapp.com", "wa.me",
        "facebook.com", "fb.com",
        "instagram.com",
        "youtube.com", "youtu.be",
        "twitter.com", "x.com",
        "linkedin.com",
        "play.google.com",
        "apps.apple.com",
        "allcityjob",                  # sarkariresultshine Telegram group
        "resultshine",                 # any resultshine sub-domain/path
        # Third-party redirect/affiliate/spam domains
        "uprorg.in", "rojgarresult.com", "govtjobsalert", "sarkariexam.com",
        "sarkarinaukri.com", "naukri.com", "shine.com", "timesjobs.com",
        "monsterindia.com", "rojgarsamachar", "employment-news.in",
        "allindiaroundups", "jobriya", "sarkariresultportal",
        "sarkariresults.org.in", "sarkariresult.tools",
        "tinyurl.com", "bit.ly", "tiny.cc", "cutt.ly", "shorturl", "rebrand.ly",
    ]

    # ── Blocked label/title patterns (social channel join prompts, noise) ─────
    _LJ_BLOCKED_LABEL_WORDS = [
        "join now", "join telegram", "join whatsapp", "join channel",
        "telegram channel", "whatsapp channel",
        "follow x", "follow twitter", "follow facebook",
        "subscribe", "youtube channel",
        "gokulgopal",
        "sarkari result whatsapp",
        "sarkari result telegram",
        "sarkariresult",
        "sarkariresultshine",
    ]

    def _lj_is_blocked_url(url):
        """Return True if URL should be excluded from all_links."""
        if not url:
            return True
        url_low = url.lower().strip()
        if not url_low.startswith("http"):
            return True
        return any(b in url_low for b in _LJ_BLOCKED_URL_WORDS)

    def _lj_is_blocked_label(text):
        """Return True if label/title indicates a social/channel/noise link."""
        if not text:
            return False
        text_low = text.lower().strip()
        return any(b in text_low for b in _LJ_BLOCKED_LABEL_WORDS)

    # Extract from tables (Important Links table)
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue
            label_raw = clean(cols[0].get_text()).lower()

            # Skip rows whose label indicates a social/channel entry
            if _lj_is_blocked_label(label_raw):
                continue

            for col in cols[1:]:
                for a in col.find_all("a", href=True):
                    href = a["href"].strip()
                    if _lj_is_blocked_url(href):
                        continue
                    link_title = clean(a.get_text())
                    # Also skip if anchor text itself is a blocked label
                    if _lj_is_blocked_label(link_title):
                        continue
                    if href not in seen_urls:
                        seen_urls.add(href)
                        all_links.append({"label": label_raw, "title": link_title,
                                          "url": href})
                    # Labelled link mapping for structured result dict
                    for substrings, key in LINK_LABEL_MAP:
                        if all(s in label_raw for s in substrings):
                            if not result[key]:
                                result[key] = href
                            break

    # Also collect all external anchors from content (not just tables)
    content_div = _shine_lj_get_content_container(soup)
    for a in content_div.find_all("a", href=True):
        href = a["href"].strip()
        if _lj_is_blocked_url(href):
            continue
        if href in seen_urls:
            continue
        link_title = clean(a.get_text())
        # Skip if anchor text is a blocked/social label
        if _lj_is_blocked_label(link_title):
            continue
        label = link_title.lower()
        if _lj_is_blocked_label(label):
            continue
        seen_urls.add(href)
        all_links.append({"label": label, "title": link_title, "url": href})
        # Map to structured key if unlabelled
        for substrings, key in LINK_LABEL_MAP:
            if all(s in label for s in substrings):
                if not result[key]:
                    result[key] = href
                break

    return result, all_links


def _shine_lj_extract_full_content(container, soup_orig):
    """
    Content container se complete structured content nikalo.
    Returns dict with: headings, paragraphs, tables, lists, sections, full_text
    """
    headings = []
    paragraphs = []
    lists = []
    sections = {}
    current_section = "General"
    seen_texts = set()

    # Spam patterns jo paragraphs/text se NEVER include karne hain
    _PARA_SPAM_WORDS = [
        "sarkariresultshine", "sarkariresult.com", "sarkari result shine",
        "sarkaril result", "sarkari result is a platform",
        "join whatsapp", "join facebook", "follow x (twitter)", "follow telegram",
        "join telegram", "join channel", "join arattai",
        "design by mukesh", "about || contact", "privacy policy || disclaimer",
        "preferred source on google", "set as preferred source",
        "if the form we provide is rejected, sarkari result shine",
        "download mobile app",
        "read also", "read also:-", "read also this", "disclaimer:",
        "leave a reply", "leave a comment", "responses to", "follow x",
    ]

    def _is_para_spam(text: str) -> bool:
        tl = text.lower()
        return any(w in tl for w in _PARA_SPAM_WORDS)

    def _dedup_add(lst, text):
        text = clean(text)
        if text and text not in seen_texts and len(text) > 3:
            if _is_para_spam(text):
                return                 # spam paragraph → skip
            seen_texts.add(text)
            lst.append(text)

    # Walk all elements in document order (NOT recursive=False — that misses
    # <h2>+<ul> in separate sibling wrappers). Use full descendant walk and
    # associate each heading with following content until next heading.
    _HEAD = {"h1", "h2", "h3", "h4", "h5", "h6"}
    seen_els = set()
    for el in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6",
                                  "p", "ul", "ol", "table"]):
        if id(el) in seen_els:
            continue
        seen_els.add(id(el))
        tag = el.name

        if tag in _HEAD:
            htext = clean(el.get_text(" ", strip=True))
            if htext and len(htext) > 2 and not _is_para_spam(htext):
                _dedup_add(headings, htext)
                current_section = htext
                sections.setdefault(current_section, [])

        elif tag == "p":
            ptext = clean(el.get_text(" ", strip=True))
            if ptext and len(ptext) > 5 and not _is_para_spam(ptext):
                _dedup_add(paragraphs, ptext)
                sections.setdefault(current_section, [])
                if ptext not in sections[current_section]:
                    sections[current_section].append(ptext)

        elif tag in ["ul", "ol"]:
            items = []
            for li in el.find_all("li"):
                li_text = clean(li.get_text(" ", strip=True))
                if li_text and not _is_para_spam(li_text):
                    items.append(li_text)
            if items:
                lists.append({"type": tag, "items": items})
                sections.setdefault(current_section, [])
                sections[current_section].extend(items)

    # Also do a recursive scan for paragraphs inside nested divs
    for p in container.find_all("p"):
        ptext = clean(p.get_text(" ", strip=True))
        if ptext and len(ptext) > 10 and ptext not in seen_texts \
                and not _is_para_spam(ptext):
            seen_texts.add(ptext)
            paragraphs.append(ptext)

    # Tables
    tables_data = _shine_lj_extract_all_tables(container)

    # Full plain text — spam phrases strip karo (regex, line drop nahi)
    full_text = clean(container.get_text("\n", strip=True))
    import re as _re
    full_text = _re.sub(r"(?:Sarkari Result\s+)?(?:WhatsApp|Telegram)\s+Channel[^\n]*", "", full_text, flags=_re.I)
    full_text = _re.sub(r"\bJoin Now\b[^\n]*", "", full_text, flags=_re.I)
    full_text = _re.sub(r"Read Also\s*:?-?[^\n]*", "", full_text, flags=_re.I)
    full_text = _re.sub(r"Disclaimer\s*:[^\n]*", "", full_text, flags=_re.I)
    full_text = _re.sub(r"[^\n]*sarkariresultshine[^\n]*", "", full_text, flags=_re.I)
    full_text = _re.sub(r"[^\n]*sarkari result shine[^\n]*", "", full_text, flags=_re.I)
    full_text = _re.sub(r"\bFollow X\b[^\n]*", "", full_text, flags=_re.I)
    full_text = _re.sub(r"[^\n]*Join WhatsApp[^\n]*", "", full_text, flags=_re.I)
    full_text = _re.sub(r"[^\n]*Join Telegram[^\n]*", "", full_text, flags=_re.I)
    full_text = _re.sub(r"\n{3,}", "\n\n", full_text).strip()

    return {
        "headings":   headings,
        "paragraphs": paragraphs,
        "tables":     tables_data,
        "lists":      lists,
        "sections":   {k: v for k, v in sections.items() if v},
        "full_text":  full_text[:8000],   # Preserve up to 8000 chars
    }


def _shine_lj_extract_named_sections(full_text, soup):
    """
    Named important sections extract karo:
    Important Dates, Application Fee, Age Limit, Eligibility, etc.
    Both table-based aur text-based extraction karta hai.
    """
    SECTION_KEYWORDS = {
        "important_dates":    ["important date", "key date", "schedule", "महत्वपूर्ण तिथि"],
        "application_fee":    ["application fee", "exam fee", "fee detail", "आवेदन शुल्क"],
        "age_limit":          ["age limit", "age relaxation", "आयु सीमा"],
        "eligibility":        ["eligibility", "qualification", "educational", "योग्यता"],
        "vacancy_details":    ["vacancy detail", "post detail", "रिक्ति विवरण"],
        "selection_process":  ["selection process", "selection criteria",
                               "mode of selection", "चयन प्रक्रिया"],
        "salary":             ["salary", "stipend", "pay scale", "pay band",
                               "pay matrix", "वेतन"],
        "apply_process":      ["how to apply", "how to fill", "apply process",
                               "आवेदन कैसे करें"],
        "exam_pattern":       ["exam pattern", "test pattern", "marking scheme",
                               "परीक्षा पैटर्न"],
        "syllabus":           ["syllabus", "पाठ्यक्रम"],
        "documents_required": ["documents required", "documents needed",
                               "required documents"],
    }

    sections_found = {}

    # Table-based section extraction
    for table in soup.find_all("table"):
        table_text = clean(table.get_text(" ", strip=True)).lower()
        for section_key, keywords in SECTION_KEYWORDS.items():
            if any(kw in table_text for kw in keywords):
                tbl = _shine_lj_extract_table(table)
                if tbl["rows"]:
                    sections_found.setdefault(section_key, [])
                    sections_found[section_key].append(tbl)

    # Text-based section extraction (regex)
    text_lower = full_text.lower()
    _BRAND = re.compile(r"read also|sarkariresultshine|sarkari result shine|"
                        r"disclaimer\s*:|join (?:whatsapp|telegram)", re.I)
    for section_key, keywords in SECTION_KEYWORDS.items():
        if section_key in sections_found:
            continue  # Already got from table
        for kw in keywords:
            if kw in text_lower:
                # Extract section text
                pattern = rf"(?:{re.escape(kw)})\s*[:\-]?\s*(.{{10,600}}?)(?=\n\s*(?:{'|'.join(re.escape(k2) for k2 in ['important date', 'application fee', 'age limit', 'eligibility', 'vacancy', 'selection', 'salary', 'how to apply', 'exam pattern', 'syllabus', 'important link', 'read also', 'disclaimer'])})|\Z)"
                m = re.search(pattern, full_text, re.I | re.S)
                if m:
                    val = clean(m.group(1))
                    # branding line aaye to wahi se cut kar do
                    bm = _BRAND.search(val)
                    if bm:
                        val = val[:bm.start()].strip()
                    if val and not _BRAND.search(val):
                        sections_found[section_key] = val
                break

    return sections_found


def shine_scrape_latest_job(url, listing_title="", listing_date=""):
    """
    Latest Jobs detail page scrape karta hai — Job + Non-Job dono types.

    MAJOR IMPROVEMENTS:
    1. No is_job_page() gate — ALL entry types accepted (Result, Admit Card, etc.)
    2. Smart classification: entry_type (JOB/NON_JOB) + sub_type
    3. Full content extraction: tables, sections, headings, paragraphs, lists
    4. Complete Important Links extraction
    5. Hindi + English text preservation
    6. Fallback selectors for multiple page layouts
    7. details_page_content — complete structured content
    """
    try:
        print("  SHINE LATEST SCRAPING:", url)
        html = shine_get_html(url)
        if not html:
            return None
        soup  = BeautifulSoup(html, "html.parser")

        # ── Title ─────────────────────────────────────────────────────────────
        title = clean_title(soup.title.text if soup.title else "")
        if not title and listing_title:
            title = clean(listing_title)
        if not title:
            return None

        # Skip pure navigation/utility pages
        if is_news_page(title) and not listing_title:
            return None

        # ── Content container ─────────────────────────────────────────────────
        container_raw = _shine_lj_get_content_container(soup)
        container     = _shine_lj_clean_container(container_raw)

        # ── Full text (for field extraction) ──────────────────────────────────
        full_text = clean(container.get_text("\n", strip=True))

        # ── Classification ────────────────────────────────────────────────────
        # Get main heading for classification signals
        main_heading = ""
        for h in soup.find_all(["h1", "h2"]):
            h_text = clean(h.get_text())
            if h_text and len(h_text) > 8:
                main_heading = h_text
                break

        entry_type, sub_type = shine_classify_latest_job_entry(
            title, url, main_heading, full_text[:600])

        # ── Dates ─────────────────────────────────────────────────────────────
        important_dates = shine_extract_dates_from_table(soup)
        if not all(important_dates.values()):
            text_dates = shine_extract_dates(full_text)
            for field in ["application_start", "last_date", "exam_date", "interview_date"]:
                if not important_dates[field] and text_dates.get(field):
                    important_dates[field] = text_dates[field]

        # ── Standard fields (table-based) ─────────────────────────────────────
        organization   = shine_extract_field(["Organization", "संगठन"], soup)
        post_name      = shine_extract_field(["Post Name", "पद नाम"], soup)
        total_vacancy  = clean_total_value(shine_extract_field(
            ["Total Vacancy", "Total Post", "Total Vacancies", "रिक्ति"], soup))
        salary         = shine_extract_field(
            ["Salary", "Salary/Pay Scale", "Pay Scale", "Pay Band", "वेतन"], soup)
        apply_mode     = shine_extract_field(["Apply Mode"], soup)
        job_location   = clean_extra_text(shine_extract_field(
            ["Job Location", "Location", "स्थान"], soup))

        # ── Application Fees (DYNAMIC — all labels) ───────────────────────────
        application_fees = shine_extract_application_fees_dynamic(soup, full_text)
        if not application_fees:
            application_fees = shine_extract_application_fees(full_text)

        # ── Age Limit ─────────────────────────────────────────────────────────
        min_age = shine_extract_min_age(full_text)
        max_age = shine_extract_max_age(full_text)
        # age relaxation free-text note
        age_relax = ""
        arm = re.search(r"age\s+relaxation[^\n.]{0,160}", full_text, re.I)
        if arm:
            age_relax = clean_extra_text(arm.group(0))

        # ── How to Apply (structured list first, no truncation) ───────────────
        how_steps = shine_extract_how_to_apply_soup(soup)
        how_to_apply = " ".join(how_steps) if how_steps else \
            clean_extra_text(shine_extract_how_to_apply(full_text))

        # ── Salary / Selection Process (from named sections) ──────────────────
        salary_stipend = ""
        selection_process = []
        for h in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
            ht = clean(h.get_text()).lower()
            if not salary_stipend and re.search(r"salary|stipend|pay scale|pay band", ht):
                nx = h.find_next(["p", "ul", "ol", "table"])
                if nx:
                    sv = clean_extra_text(nx.get_text(" "))
                    if sv and "sarkari" not in sv.lower():
                        salary_stipend = sv[:300]
            if not selection_process and re.search(r"selection process|selection criteria|mode of selection", ht):
                nx = h.find_next(["ul", "ol"])
                if nx:
                    for li in nx.find_all("li"):
                        t = clean(li.get_text(" "))
                        if t and "sarkari" not in t.lower() and len(t) < 90:
                            selection_process.append(t)
        if not salary:
            salary = salary_stipend

        # ── Intro-paragraph fallbacks (FIX 6) ─────────────────────────────────
        intro = ""
        for p in soup.find_all("p"):
            pt = clean(p.get_text(" "))
            if len(pt) > 100 and re.search(r"vacanc|recruit|notification|post", pt, re.I) \
                    and "sarkari" not in pt.lower():
                intro = pt
                break
        if not total_vacancy and intro:
            vm = re.search(r"(\d[\d,]{1,6})\s*(?:vacanc|posts?)", intro, re.I)
            if vm:
                total_vacancy = vm.group(1).replace(",", "")
        if not job_location and intro:
            lm = re.search(r"\(([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\)", intro)
            if lm:
                job_location = lm.group(1)

        # ── Jobs info paragraph ───────────────────────────────────────────────
        jobs_info = shine_extract_jobs_info(soup)

        # ── Vacancy details ───────────────────────────────────────────────────
        vacancy_details = shine_extract_vacancy_details(soup)

        # ── Important links ───────────────────────────────────────────────────
        legacy_links   = shine_extract_links(soup)   # existing structured links
        new_links, all_links = _shine_lj_extract_important_links(soup, url)

        # ── FAQs (clean Q&A) ──────────────────────────────────────────────────
        faqs = shine_extract_faqs(soup)
        if not apply_mode:
            apply_mode = shine_apply_mode_from_faqs(faqs)

        # ── Full structured content (slimmed — no duplicate lists/sections) ───
        full_content   = _shine_lj_extract_full_content(container, soup)
        # JUNK sections filter: nav menus, related posts, FAQ-answer dumps hatao
        _JUNK_SEC = re.compile(r"^(general|latest updates|❓|q\d+\.|frequently|"
                               r"read also|disclaimer)", re.I)
        # tables: vacancy/eligibility + link tables already structured hain → drop
        clean_tables = _shine_dedup_tables(full_content.get("tables", []),
                                           vacancy_details)
        # headings: FAQ question headings faqs[] me hain → drop
        clean_headings = _shine_dedup_headings(full_content.get("headings", []))
        # content_sections: SIRF woh sections jo structured fields me NAHI hain
        # (fees/age/salary/selection/dates/eligibility/how-to-apply already alag
        #  fields me hain → unhe yahan se hatao, warna duplicate).  Bachenge sirf
        #  descriptive/extra content (scheme details, objective, eligibility notes).
        #  NOTE: NON_JOB entries (news/scheme/portal updates) ke paas alag
        #  structured fields nahi hote — unke liye structured-filter HATAO, saara
        #  descriptive content rakho warna detail page khali reh jata hai.
        _STRUCT_SEC = re.compile(
            r"important date|application fee|age limit|salary|stipend|"
            r"selection process|eligibility detail|how to apply|important link|"
            r"vacancy detail|pay scale|fee detail", re.I)
        is_non_job = (entry_type == "NON_JOB")
        content_sections = {}
        for sec_name, sec_items in full_content.get("sections", {}).items():
            nm = sec_name.strip()
            # Always drop nav/junk; only drop structured-duplicate sections for JOBs
            if _JUNK_SEC.match(nm):
                continue
            if (not is_non_job) and _STRUCT_SEC.search(nm):
                continue
            if sec_items:
                content_sections[sec_name] = sec_items

        # ── Build output ──────────────────────────────────────────────────────
        job = {
            # ── Core metadata ────────────────────────────────────────────────
            "category":         "LATEST_JOBS NEW",
            "_scraped_from":    url,   # INTERNAL ONLY — incremental-scrape bookkeeping,
                                        # never rendered (see note on OFFLINE_FORM above).
            "entry_type":       entry_type,        # "JOB" or "NON_JOB"
            "sub_type":         sub_type,           # e.g. "Government Job", "Result"
            "title":            title,
            "listing_date":     listing_date,
            "source_url":       "",

            # ── Standard job fields ──────────────────────────────────────────
            "organization":     organization,
            "post_name":        post_name,
            "total_vacancy":    total_vacancy,
            "salary_pay_scale": salary,
            "apply_mode":       apply_mode,
            "job_location":     job_location,
            "important_dates":  important_dates,
            "application_fees": application_fees,
            "minimum_age":      min_age,
            "maximum_age":      max_age,
            "age_relaxation_notes": age_relax,
            "salary_stipend":   salary_stipend,
            "selection_process": selection_process,
            "how_to_apply":     how_to_apply,

            # ── Legacy link fields (backward compat) ─────────────────────────
            "form_pdf_free_link":             legacy_links.get("form_pdf_free_link", ""),
            "application_form_pdf_link":      legacy_links.get("application_form_pdf_link", ""),
            "form_pdf_link":                  legacy_links.get("form_pdf_link", ""),
            "apply_online_link":              legacy_links.get("apply_online_link", "")
                                              or new_links.get("apply_online", ""),
            "official_notification_pdf_link": legacy_links.get("official_notification_pdf_link", "")
                                              or new_links.get("official_notification", ""),
            "official_website_link":          legacy_links.get("official_website_link", "")
                                              or new_links.get("official_website", ""),

            # ── Extended links ────────────────────────────────────────────────
            "important_links": {
                "apply_online":          new_links.get("apply_online", ""),
                "official_notification": new_links.get("official_notification", ""),
                "official_website":      new_links.get("official_website", ""),
                "admit_card":            new_links.get("admit_card", ""),
                "result":                new_links.get("result_link", ""),
                "answer_key":            new_links.get("answer_key", ""),
                "syllabus":              new_links.get("syllabus", ""),
                "login":                 new_links.get("login", ""),
                "download":              new_links.get("download", ""),
            },
            "all_links":       all_links,           # All external links list

            # ── Content fields ────────────────────────────────────────────────
            "jobs_info":        jobs_info,
            "vacancy_details":  vacancy_details,
            "faqs":             faqs,

            # ── Full details page content (slim — no duplicate lists/sections) ─
            "details_page_content": {
                "headings":          clean_headings,
                "content_sections":  content_sections,
                "tables":            clean_tables,
                "full_text":         full_content["full_text"],
            },
        }

        # Require at least title (relaxed gate — accepts all types)
        if not job["title"]:
            return None

        return job

    except Exception as e:
        print("  SHINE LATEST SCRAPE ERROR:", url, e)
        return None


def shine_extract_faqs(soup):
    """FAQ Q&A pairs — H2 'Frequently asked' ke baad H3-question + ul/p-answer."""
    BRAND = re.compile(r"sarkari result shine|sarkariresultshine|read also|"
                       r"join (?:whatsapp|telegram)|apply now|notification out|"
                       r"vacancy 2026|recruitment 2026", re.I)
    faqs = []
    _seen_q = set()
    faq_h = None
    for h in soup.find_all(["h2", "h3"]):
        if re.search(r"frequently asked|faq", clean(h.get_text()), re.I):
            faq_h = h
            break
    if not faq_h:
        return faqs
    for q in faq_h.find_all_next(["h3", "h4", "h2"]):
        qt = clean(q.get_text())
        if q.name == "h2":          # next major section → FAQ khatam
            break
        if not qt or "?" not in qt and not re.match(r"q\d|^\d+\.", qt, re.I):
            continue
        qt = re.sub(r"^q?\d+[.\)]\s*", "", qt, flags=re.I).strip()
        # duplicate question (Q1 + bina-prefix same Q) → skip
        norm = qt.lower()
        if norm in _seen_q:
            continue
        _seen_q.add(norm)
        ans = ""
        nx = q.find_next(["ul", "ol", "p"])
        if nx:
            ans = clean(nx.get_text(" "))
            ans = re.sub(r"^answer\s*[:\-]?\s*", "", ans, flags=re.I)
        # answer me related-post junk aaye to cut
        if ans and not BRAND.search(qt):
            bm = BRAND.search(ans)
            if bm:
                ans = ans[:bm.start()].strip()
            if ans:
                faqs.append({"question": qt, "answer": ans})
    return faqs[:8]


def _shine_section_list(soup, *keywords):
    """Heading (keyword) ke neeche ki <ul>/<ol> ke clean li items → list."""
    BRAND = re.compile(r"sarkari result shine|sarkariresultshine|read also|"
                       r"join (?:whatsapp|telegram)|latest updates check|"
                       r"preferred source|govt jobs 2026|latest govt vacancy", re.I)
    for h in soup.find_all(["h2", "h3", "h4"]):
        ht = clean(h.get_text()).lower()
        if any(k in ht for k in keywords):
            nx = h.find_next(["ul", "ol", "p"])
            if nx and nx.name in ("ul", "ol"):
                items = []
                for li in nx.find_all("li"):
                    t = clean(li.get_text(" "))
                    if t and not BRAND.search(t):
                        items.append(t)
                if items:
                    return items
            elif nx:
                t = clean(nx.get_text(" "))
                if t and not BRAND.search(t):
                    return [t]
    return []


def shine_extract_salary_stipend(soup):
    items = _shine_section_list(soup, "salary", "stipend", "pay scale", "pay band")
    return " ".join(items)[:600] if items else ""


def shine_extract_selection_process(soup):
    return _shine_section_list(soup, "selection process", "selection criteria",
                               "mode of selection")


def shine_extract_age_relaxation(text):
    """Age relaxation note + reference date from Age Limit lines."""
    relax, ref = "", ""
    m = re.search(r"age relaxation[^\n.]{0,160}", text, re.I)
    if m:
        relax = clean_extra_text(m.group(0))
    m2 = re.search(r"(?:age calculation|age reference|age as on)[^\d]{0,30}"
                   r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})", text, re.I)
    if m2:
        ref = m2.group(1)
    return relax, ref


def shine_extract_interview_details(soup):
    """Walk-in interview date/time/venue from Important Dates li lines."""
    out = {"date": "", "time": "", "venue": ""}
    for h in soup.find_all(["h2", "h3"]):
        if "important date" in clean(h.get_text()).lower():
            nx = h.find_next(["ul", "ol"])
            if nx:
                for li in nx.find_all("li"):
                    t = clean(li.get_text(" "))
                    low = t.lower()
                    m = re.match(r"(.+?)\s*[:：]\s*(.+)", t)
                    if not m:
                        continue
                    lbl, val = m.group(1).lower(), m.group(2).strip()
                    if "interview" in lbl and "time" not in lbl and "venue" not in lbl:
                        out["date"] = val
                    elif "time" in lbl:
                        out["time"] = val
                    elif "venue" in lbl or "address" in lbl or "place" in lbl:
                        out["venue"] = val
            break
    return out if any(out.values()) else {}


def shine_apply_mode_from_faqs(faqs):
    """FAQ answers se apply_mode derive karo."""
    for f in faqs:
        a = f.get("answer", "").lower()
        if "walk" in a and "interview" in a:
            return "Walk-in Interview"
        if "apply offline" in a or "offline" in a:
            return "Offline"
        if "apply online" in a or "online" in a:
            return "Online"
    return ""


def shine_address_from_steps(steps):
    """How to Apply steps me postal address line dhundo."""
    for s in (steps if isinstance(steps, list) else [steps]):
        if re.search(r"send (?:the )?application|post(?:al)? address|"
                     r"by post|address\s*[:：]", s, re.I):
            return clean_extra_text(s)
    return ""


def shine_scrape_job(url, listing_title="", listing_date=""):
    try:
        print("  SHINE SCRAPING:", url)
        html = shine_get_html(url)
        if not html:
            return None
        soup  = BeautifulSoup(html, "html.parser")
        title = clean_title(soup.title.text if soup.title else "")
        if not title and listing_title:
            title = clean(listing_title)
        if not title:
            return None
        if is_news_page(title) and not listing_title:
            return None

        # Content container (same template as LATEST_JOBS)
        container_raw = _shine_lj_get_content_container(soup)
        container     = _shine_lj_clean_container(container_raw)
        full_text     = clean(container.get_text("\n", strip=True))

        # Dates (table + text fallback)
        important_dates = shine_extract_dates_from_table(soup)
        if not all(important_dates.values()):
            text_dates = shine_extract_dates(full_text)
            for f in ["application_start", "last_date", "exam_date", "interview_date"]:
                if not important_dates[f] and text_dates.get(f):
                    important_dates[f] = text_dates[f]

        # Fees (dynamic)
        application_fees = shine_extract_application_fees_dynamic(soup, full_text)
        if not application_fees:
            application_fees = shine_extract_application_fees(full_text)

        # Age + relaxation
        min_age = shine_extract_min_age(full_text)
        max_age = shine_extract_max_age(full_text)
        age_relax, age_ref = shine_extract_age_relaxation(full_text)

        # Salary / Selection (heading+list sections)
        salary_stipend    = shine_extract_salary_stipend(soup)
        selection_process = shine_extract_selection_process(soup)

        # How to Apply (structured list first)
        how_steps = shine_extract_how_to_apply_soup(soup)
        how_to_apply = how_steps if how_steps else \
            clean_extra_text(shine_extract_how_to_apply(full_text))
        application_address = shine_address_from_steps(how_steps)

        # Vacancy (2-col + 3-col)
        vacancy_details = shine_extract_vacancy_details(soup)

        # FAQs + apply_mode derive
        faqs = shine_extract_faqs(soup)
        apply_mode = shine_apply_mode_from_faqs(faqs)

        # Interview details (walk-in variant)
        interview_details = shine_extract_interview_details(soup)

        # Links
        legacy_links = shine_extract_links(soup)
        new_links, all_links = _shine_lj_extract_important_links(soup, url)

        # Slim content (headings + content_sections + tables + full_text)
        full_content = _shine_lj_extract_full_content(container, soup)
        _JUNK_SEC_OFF = re.compile(r"^(general|latest updates|❓|q\d+\.|frequently|"
                                   r"read also|disclaimer)", re.I)
        clean_tables_off    = _shine_dedup_tables(full_content.get("tables", []),
                                                  vacancy_details)
        clean_headings_off  = _shine_dedup_headings(full_content.get("headings", []))
        _STRUCT_SEC_OFF = re.compile(
            r"important date|application fee|age limit|salary|stipend|"
            r"selection process|eligibility detail|how to apply|important link|"
            r"vacancy detail|pay scale|fee detail", re.I)
        content_sections_off = {}
        for sec_name, sec_items in full_content.get("sections", {}).items():
            nm = sec_name.strip()
            if _JUNK_SEC_OFF.match(nm) or _STRUCT_SEC_OFF.search(nm):
                continue
            if sec_items:
                content_sections_off[sec_name] = sec_items

        # post_name / total_vacancy fallback from vacancy_details / intro
        post_name = vacancy_details[0]["post_name"] if vacancy_details else ""
        total_vacancy = ""
        if vacancy_details:
            try:
                total_vacancy = str(sum(int(re.sub(r"[^\d]", "", v.get("total", "") or "0") or 0)
                                        for v in vacancy_details)) or ""
                if total_vacancy == "0":
                    total_vacancy = ""
            except Exception:
                total_vacancy = ""
        if not total_vacancy:
            vm = re.search(r"(\d[\d,]{1,6})\s*(?:vacanc|posts?)", full_text, re.I)
            if vm:
                total_vacancy = vm.group(1).replace(",", "")

        job = {
            "category":         "OFFLINE_FORM",
            "title":            title,
            "_scraped_from":    url,   # INTERNAL ONLY: never rendered publicly (see
                                        # generate_all.py — only named fields are read,
                                        # this is used purely to skip re-scraping the
                                        # same URL on the next run).
            "listing_date":     listing_date,
            "organization":     "",
            "post_name":        post_name,
            "total_vacancy":    total_vacancy,
            "salary_pay_scale": salary_stipend,
            "apply_mode":       apply_mode,
            "job_location":     "",
            "important_dates":  important_dates,
            "interview_details": interview_details,
            "application_fees": application_fees,
            "minimum_age":      min_age,
            "maximum_age":      max_age,
            "age_relaxation_notes": age_relax,
            "age_reference_date":   age_ref,
            "salary_stipend":   salary_stipend,
            "selection_process": selection_process,
            "application_address": application_address,
            "how_to_apply":     how_to_apply,
            "form_pdf_free_link":             legacy_links.get("form_pdf_free_link", ""),
            "application_form_pdf_link":      legacy_links.get("application_form_pdf_link", ""),
            "form_pdf_link":                  legacy_links.get("form_pdf_link", ""),
            "apply_online_link":              legacy_links.get("apply_online_link", "")
                                              or new_links.get("apply_online", ""),
            "official_notification_pdf_link": legacy_links.get("official_notification_pdf_link", "")
                                              or new_links.get("official_notification", ""),
            "official_website_link":          legacy_links.get("official_website_link", "")
                                              or new_links.get("official_website", ""),
            "important_links": {
                "apply_online":          new_links.get("apply_online", ""),
                "official_notification": new_links.get("official_notification", ""),
                "official_website":      new_links.get("official_website", ""),
                "admit_card":            new_links.get("admit_card", ""),
                "result":                new_links.get("result_link", ""),
                "answer_key":            new_links.get("answer_key", ""),
                "syllabus":              new_links.get("syllabus", ""),
                "login":                 new_links.get("login", ""),
                "download":              new_links.get("download", ""),
            },
            "all_links":        all_links,
            "jobs_info":        shine_extract_jobs_info(soup),
            "vacancy_details":  vacancy_details,
            "faqs":             faqs,
            "details_page_content": {
                "headings":          clean_headings_off,
                "content_sections":  content_sections_off,
                "tables":            clean_tables_off,
                "full_text":         full_content["full_text"],
            },
        }

        # ── DROP-GATE FIX: title + koi bhi real content ho ────────────────────
        has_content = any([
            important_dates.get("last_date"),
            application_fees,
            vacancy_details,
            how_to_apply,
            salary_stipend,
        ])
        if not job["title"] or not has_content:
            return None
        return job

    except Exception as e:
        print("  SHINE SCRAPE ERROR:", url, e)
        return None


def sort_jobs_latest(jobs):
    def get_date(job):
        last_date = job.get("important_dates", {}).get("last_date", "")
        parsed    = parse_date(last_date)
        return parsed if parsed else datetime(2000, 1, 1)
    return sorted(jobs, key=get_date, reverse=True)


# =========================================================
# SOURCE 2 — sarkariresult.com HELPERS
# =========================================================

def sr_load_page(url):
    """Load a sarkariresult.com page with retry on transient failures.
    Returns BeautifulSoup or None.

    sarkariresult.com sits behind Cloudflare, which blocks plain `requests`
    (and any datacenter IP) with a 403 because of TLS/JA3 fingerprinting — the
    headers can be perfect but the fingerprint gives away that it's a script.
    Strategy:
      1. Try curl_cffi impersonating Chrome (real browser TLS) — this is the
         layer that actually clears Cloudflare. Rotate through a couple of
         impersonation targets if the first is challenged.
      2. Fall back to plain requests (works if Cloudflare isn't challenging,
         e.g. when run from a residential IP locally).
    """
    import time as _time
    RETRIES = 3
    DELAYS  = [0, 6, 18]   # wait before each attempt (0 = first try immediate)
    # Chrome versions to impersonate; newer first. curl_cffi ships these JA3s.
    IMPERSONATE_TARGETS = ["chrome131", "chrome124", "chrome120"]

    for attempt, delay in enumerate(DELAYS):
        if delay:
            _time.sleep(delay)

        # ── Attempt 1: curl_cffi with Chrome TLS impersonation (Cloudflare bypass)
        if HAS_CURL_CFFI:
            target = IMPERSONATE_TARGETS[attempt % len(IMPERSONATE_TARGETS)]
            try:
                r = cffi_requests.get(
                    url, headers=SR_HEADERS, timeout=30, impersonate=target
                )
                if r.status_code == 200:
                    return BeautifulSoup(r.text, "lxml")
                print(f"  SR LOAD [{r.status_code}] (cffi:{target}) {url[:55]}"
                      f" (attempt {attempt+1}/{RETRIES})")
                # 403/429/503 → retry with next impersonation target + delay
                if r.status_code in (403, 429, 503) and attempt < RETRIES - 1:
                    continue
                # On final cffi attempt, fall through to plain requests below
            except Exception as e:
                print(f"  SR LOAD ERROR (cffi attempt {attempt+1}): {e}")
                # fall through to plain requests as a backup

        # ── Attempt 2: plain requests (backup; works on non-challenged IPs)
        try:
            r = requests.get(url, headers=SR_HEADERS, timeout=25)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "lxml")
            print(f"  SR LOAD [{r.status_code}] (requests) {url[:55]}"
                  f" (attempt {attempt+1}/{RETRIES})")
            if r.status_code in (403, 429, 503) and attempt < RETRIES - 1:
                continue
            return None
        except Exception as e:
            print(f"  SR LOAD ERROR (requests attempt {attempt+1}): {e}")
            if attempt < RETRIES - 1:
                continue
            return None
    return None


def sr_get_homepage_sections():
    """
    Homepage se category-wise links scrape karta hai.
    Returns dict:  { "SR_Latest_Jobs": [{"serial": 1, "title": ..., "url": ...}, ...], ... }

    sarkariresult.com homepage ACTUAL structures (multiple versions handled):
    ─────────────────────────────────────────────────────────────────────────

    Structure A — GenerateBlocks (WordPress gb-container, CURRENT 2024-2026):
      <div class="gb-container gb-container-c7488d9a">  <!-- Latest Job box -->
        <h3 ...>Latest Job</h3>
        <ul class="wp-block-list">
          <li><a href="https://www.sarkariresult.com/2026/some-job/">Title</a></li>
          ...
        </ul>
      </div>
      Container class IDs: SR_GB_CONTAINER_MAP mein defined hain.

    Structure B — Old center-tables (legacy, pre-2023):
      <div class="center-tables">
        <div id="heading"><a href=".../latestjob/">Latest Jobs</a></div>
        <div id="post"><ul><li><a href="...">Title</a></li></ul></div>
      </div>

    Structure C — Section heading text match (universal fallback):
      Page mein heading text "Latest Job", "Result" etc dhundo,
      phir uske container mein valid links collect karo.

    Detection Order:
      1. gb-container class ID match (SR_GB_CONTAINER_MAP)
      2. Heading text → URL slug match (h2/h3/h4/h5/h6 ya div heading)
      3. Old center-tables / div#heading structure
      4. URL-anchor scan (section anchor href se container dhundo)
      5. Proximity scan (last resort)
    """
    soup = sr_load_page(SR_HOMEPAGE_URL)
    if not soup:
        print("  [HOMEPAGE] Could not load homepage.")
        return {}

    result = {cat: [] for cat in set(SR_SECTION_MAP.values())}

    # ── URL slug → category map ───────────────────────────────────────────────
    URL_SLUG_TO_CATEGORY = {
        "result":      "SR_Result",
        "admitcard":   "SR_Admit_Card",
        "latestjob":   "SR_Latest_Jobs",
        "answerkey":   "SR_Answer_Key",
        "admission":   "SR_Latest_Jobs",   # SR_Admission retired
    }

    # ── STRATEGY 1: gb-container class ID match (GenerateBlocks / current site) ──
    # sarkariresult.com ab WordPress + GenerateBlocks use karta hai.
    # Har section box ka ek unique gb-container-XXXXXXXX class hota hai.
    _strategy_gb_containers(soup, result)
    filled = [cat for cat, items in result.items() if items]
    print(f"  [HOMEPAGE] Strategy-1 (gb-container): filled={filled}, "
          f"total_links={sum(len(v) for v in result.values())}")

    # ── STRATEGY 2: Heading text se container identify karo ──────────────────
    # h2/h3/h4/h5/h6 ya bold div mein section name dhundo
    empty_cats = [cat for cat, items in result.items() if not items]
    if empty_cats:
        _strategy_heading_text(soup, URL_SLUG_TO_CATEGORY, result)
        newly_filled = [cat for cat in empty_cats if result.get(cat)]
        print(f"  [HOMEPAGE] Strategy-2 (heading-text): newly filled={newly_filled}")

    # ── STRATEGY 3: Old center-tables / div#heading (legacy structure) ───────
    empty_cats = [cat for cat, items in result.items() if not items]
    if empty_cats:
        _strategy_old_center_tables(soup, URL_SLUG_TO_CATEGORY, result)
        newly_filled = [cat for cat in empty_cats if result.get(cat)]
        print(f"  [HOMEPAGE] Strategy-3 (center-tables): newly filled={newly_filled}")

    # ── STRATEGY 4: URL-anchor scan ───────────────────────────────────────────
    empty_cats = [cat for cat, items in result.items() if not items]
    if empty_cats:
        print(f"  [HOMEPAGE] Strategy-4 partial miss: {empty_cats}. Trying URL-anchor scan.")
        _strategy_url_anchor_scan(soup, URL_SLUG_TO_CATEGORY, result)

    # ── STRATEGY 5: Proximity scan (last resort) ──────────────────────────────
    still_empty = [cat for cat, items in result.items() if not items]
    if still_empty:
        print(f"  [HOMEPAGE] Strategy-5: still empty={still_empty}. Proximity scan...")
        _strategy_proximity_scan(soup, result)

    for cat, items in result.items():
        print(f"  [HOMEPAGE] {cat}: {len(items)} links")

    return result


def _strategy_gb_containers(soup, result):
    """
    Strategy 1: GenerateBlocks gb-container class IDs se boxes identify karo.
    sarkariresult.com ka current WordPress theme ye structure use karta hai.

    Har box div ke classes mein 'gb-container-XXXXXXXX' pattern hota hai.
    SR_GB_CONTAINER_MAP mein ye IDs category keys se mapped hain.

    Item extraction order (priority):
      1. wp-block-list ul > li > a  (WordPress block editor list)
      2. entry-content ul > li > a
      3. div#post ul > li > a       (old inner structure agar ho)
      4. Any valid <a> in container
    """
    if not soup:
        return

    for div in soup.find_all("div", class_=True):
        classes = div.get("class", [])
        # gb-container-XXXXXXXX class dhundo
        category_key = None
        for cls in classes:
            if cls in SR_GB_CONTAINER_MAP:
                category_key = SR_GB_CONTAINER_MAP[cls]
                break
        if not category_key:
            continue
        if category_key not in result:
            result[category_key] = []

        # Links extract karo — multiple patterns try karo
        anchors = []

        # Pattern A: wp-block-list
        for ul in div.find_all("ul", class_=lambda c: c and "wp-block-list" in c):
            anchors.extend(ul.find_all("a", href=True))

        # Pattern B: any ul > li > a inside this container
        if not anchors:
            for ul in div.find_all("ul"):
                anchors.extend(ul.find_all("a", href=True))

        # Pattern C: div#post
        if not anchors:
            post_div = div.find("div", id="post")
            if post_div:
                anchors = post_div.find_all("a", href=True)

        # Pattern D: direct anchors in container
        if not anchors:
            anchors = div.find_all("a", href=True)

        if anchors:
            _extract_links_from_anchor_list(anchors, category_key, result)


def _strategy_heading_text(soup, url_slug_map, result):
    """
    Strategy 2: Heading tags (h2/h3/h4/h5/h6) se section name detect karo,
    phir us heading ke parent container se valid links nikalo.

    Handles both:
    - <h3>Latest Job</h3> followed by <ul><li><a>
    - <div><b>Result</b></div> followed by list
    """
    if not soup:
        return

    heading_tags = soup.find_all(["h2", "h3", "h4", "h5", "h6"])

    for htag in heading_tags:
        text = clean(htag.get_text())
        if not text:
            continue

        # Category resolve karo
        category_key = _sr_section_lookup(text)
        if not category_key:
            # URL slug se try
            for slug, cat in url_slug_map.items():
                if slug in text.lower().replace(" ", ""):
                    category_key = cat
                    break
        if not category_key:
            continue

        # Already filled? Skip
        if result.get(category_key):
            continue

        # Parent container mein links dhundo
        # Walk up max 4 levels to find a container with links
        container = htag.parent
        for _ in range(4):
            if not container or container.name in ["html", "body"]:
                break

            # wp-block-list try karo
            anchors = []
            for ul in container.find_all("ul", class_=lambda c: c and "wp-block-list" in c):
                anchors.extend(ul.find_all("a", href=True))

            # Any ul
            if not anchors:
                for ul in container.find_all("ul"):
                    anchors.extend(ul.find_all("a", href=True))

            # div#post
            if not anchors:
                pd = container.find("div", id="post")
                if pd:
                    anchors = pd.find_all("a", href=True)

            valid = [a for a in anchors if _is_valid_sr_item_link(a.get("href", ""))]
            if valid:
                _extract_links_from_anchor_list(valid, category_key, result)
                break

            container = container.parent


def _strategy_old_center_tables(soup, url_slug_map, result):
    """
    Strategy 3: Old center-tables / div#heading structure.
    Legacy sarkariresult.com structure (pre-2024).
    """
    if not soup:
        return

    center_tables = soup.find("div", class_="center-tables")
    search_root   = center_tables if center_tables else soup

    heading_divs = search_root.find_all("div", id="heading")
    if not heading_divs:
        return

    print(f"  [HOMEPAGE] Found {len(heading_divs)} div#heading blocks (legacy structure)")

    for hdiv in heading_divs:
        heading_anchor = hdiv.find("a", href=True)
        if not heading_anchor:
            continue

        section_name = clean(heading_anchor.get_text())
        href         = heading_anchor.get("href", "").rstrip("/")
        url_slug     = href.split("/")[-1].lower()

        category_key = _sr_section_lookup(section_name)
        if not category_key:
            category_key = url_slug_map.get(url_slug)
        if not category_key:
            sl = section_name.lower()
            for sec_name, key in SR_SECTION_MAP.items():
                if sec_name.lower() in sl:
                    category_key = key
                    break
        if not category_key:
            continue

        if result.get(category_key):
            continue

        parent_box = hdiv.parent
        post_div   = parent_box.find("div", id="post")

        if not post_div:
            sib = hdiv.find_next_sibling("div")
            if sib and sib.get("id") == "post":
                post_div = sib

        if not post_div and parent_box.parent:
            post_div = parent_box.parent.find("div", id="post")

        if not post_div:
            valid_anchors = [
                a for a in parent_box.find_all("a", href=True)
                if _is_valid_sr_item_link(a.get("href", ""))
            ]
            if valid_anchors:
                _extract_links_from_anchor_list(valid_anchors, category_key, result)
            continue

        _extract_links_from_post_div(post_div, category_key, result)


def _is_valid_sr_item_link(href):
    """
    Valid SR listing item link hai ya nahi check karta hai.
    - sarkariresult.com domain hona chahiye
    - Depth >= 4 slashes (e.g. https://www.sarkariresult.com/post-slug/ or /2026/post/)
    - Category index pages nahi hone chahiye

    NOTE: is_sr_blocked() yahan NAHI call karte — woh sarkariresult.com domain
    ko hi block kar deta hai jo yahan hamare valid links hain.
    is_sr_blocked() sirf sr_extract_useful_links() mein use hota hai
    jahan external/third-party links filter karne hote hain.
    """
    if not href or not href.startswith("https://www.sarkariresult.com/"):
        return False
    if href.count("/") < 4:
        return False  # needs at least one path segment after domain
    slug = href.rstrip("/").split("/")[-1].lower()
    index_slugs = {"latestjob", "admitcard", "result", "admission", "answerkey",
                   "syllabus", "important", "verification", "boardall", "sscall",
                   "railwayall", "upscall", "uppscall", "policeall", "ibpsall",
                   "tetall", "bpsc", "upsssc", "rpsc"}
    if slug in index_slugs:
        return False
    # Static/non-job pages — About Us, Contact, Privacy, Terms etc. block karo
    non_job_slugs = {"about", "about-us", "contact", "contact-us",
                     "privacy-policy", "privacy", "terms", "terms-and-conditions",
                     "disclaimer", "sitemap", "feed", "rss", "advertise"}
    if slug in non_job_slugs:
        return False
    # Slug mein bhi check karo (partial match)
    non_job_patterns = ["about-us", "contact-us", "privacy-policy",
                        "terms-and-conditions", "terms-condition", "disclaimer"]
    low = href.lower()
    if any(p in low for p in non_job_patterns):
        return False
    # Spam/social words check (is_sr_blocked use nahi karte yahan)
    spam_words = ["telegram", "t.me", "whatsapp", "facebook", "instagram",
                  "youtube", "twitter", "x.com", "android-app", "apple-ios",
                  "play.google", "itunes", "tinyurl"]
    if any(s in low for s in spam_words):
        return False
    return True


def _extract_links_from_post_div(post_div, category_key, result):
    """
    div#post ke andar se serial-wise links extract karta hai.
    ul > li > a pattern follow karta hai, serial = list position.
    """
    seen   = set()
    serial = len(result[category_key])  # Existing items ke baad continue karo

    for a in post_div.find_all("a", href=True):
        href  = a.get("href", "").strip()
        title = clean(a.get_text())

        if not _is_valid_sr_item_link(href):
            continue
        if len(title) < 5:
            continue
        if href in seen:
            continue

        seen.add(href)
        serial += 1
        result[category_key].append({
            "serial": serial,
            "title":  title,
            "url":    href,
        })


def _strategy_url_anchor_scan(soup, url_slug_map, result):
    """
    Saare anchors scan karta hai jinka href section URL slug se match kare,
    phir unke parent container se listing links nikalta hai.
    Yeh strategy tab use hoti hai jab div#heading se section nahi mila.
    """
    for url_slug, category_key in url_slug_map.items():
        if result.get(category_key):
            continue  # Already filled

        # Section anchor dhundho (e.g. href ending in /result/ or /latestjob/)
        section_anchor = None
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").rstrip("/")
            if href.split("/")[-1].lower() == url_slug:
                section_anchor = a
                break

        if not section_anchor:
            continue

        # Upar walk karke container dhundho jisme div#post ya listing items hain
        container = section_anchor
        for _ in range(6):
            container = container.parent
            if not container or container.name in ["html", "body"]:
                break
            post_div = container.find("div", id="post")
            if post_div:
                _extract_links_from_post_div(post_div, category_key, result)
                if result[category_key]:
                    break
            # Direct anchors bhi try karo
            valid_anchors = [
                a for a in container.find_all("a", href=True)
                if _is_valid_sr_item_link(a.get("href", ""))
            ]
            if len(valid_anchors) >= 5:
                _extract_links_from_anchor_list(valid_anchors, category_key, result)
                if result[category_key]:
                    break


def _extract_links_from_anchor_list(anchor_tags, category_key, result):
    """Anchor tag list se serial-wise links extract karta hai."""
    seen   = set()
    serial = len(result[category_key])
    for a in anchor_tags:
        href  = a.get("href", "").strip()
        title = clean(a.get_text())
        if not _is_valid_sr_item_link(href):
            continue
        if len(title) < 5:
            continue
        if href in seen:
            continue
        seen.add(href)
        serial += 1
        result[category_key].append({
            "serial": serial,
            "title":  title,
            "url":    href,
        })


def _strategy_proximity_scan(soup, result):
    """
    Saare page anchors ko nearest preceding heading se group karta hai.
    Yeh last-resort strategy hai jab upar wali dono fail ho jaaye.
    """
    anchor_map  = {}
    current_cat = None

    all_elements = soup.find_all(["div", "td", "th", "h2", "h3", "h4", "span", "b", "a"])

    for el in all_elements:
        text = clean(el.get_text()).strip()

        # Check if this element IS a section heading (case-insensitive)
        matched_cat = _sr_section_lookup(text)
        if matched_cat:
            current_cat = matched_cat
            if current_cat not in anchor_map:
                anchor_map[current_cat] = []
            continue

        # Valid anchor check
        if el.name == "a" and current_cat:
            href = el.get("href", "").strip()
            if not _is_valid_sr_item_link(href):
                continue
            if result.get(current_cat):  # already filled
                continue
            anchor_map.setdefault(current_cat, []).append(el)

    for cat, anchors in anchor_map.items():
        if result.get(cat):
            continue
        _extract_links_from_anchor_list(anchors, cat, result)


def sr_extract_title(soup):
    if not soup.title:
        return ""
    title = clean(soup.title.text)
    title = re.sub(r"Sarkari Result.*", "", title, flags=re.I)
    title = re.sub(r"\|.*", "", title)
    return clean(title)


def sr_get_full_text(soup):
    for tag in soup(["script", "style", "iframe", "svg", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n+", "\n", text)
    return clean(text)


def sr_extract_short_info(text):
    patterns = [
        r"Short Information\s*:?(.*?)(Application Fee|Important Dates)",
        r"Short Details\s*:?(.*?)(Application Fee|Important Dates)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I | re.S)
        if m:
            val = clean(m.group(1))
            val = re.sub(r'Sarkari Result.*', '', val, flags=re.I)
            val = re.sub(r'WWW\.SARKARIRESULT\.COM.*', '', val, flags=re.I)
            val = clean(val)
            return val[:2500]
    return ""


def sr_extract_application_fee(text):
    patterns = [
        r'Application Fee(.*?)(?:Important Dates|Age Limit)',
        r'Application Fee(.*?)(?:Eligibility|Vacancy Details)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I | re.S)
        if not m:
            continue
        value = clean(m.group(1))
        for noise in [r'Application Begin.*', r'Last Date.*', r'Exam Date.*', r'Notification\s*20\d\d.*']:
            value = re.sub(noise, '', value, flags=re.I)
        value = clean(value)
        if len(value) < 10:
            return ""
        return value[:1500]
    return ""


def sr_extract_age_limit(text):
    # Pehle full text se SR branding saaf karo
    text = re.sub(r'WWW\.SARKARIRESULT\.COM[^\n]*', '', text, flags=re.I)
    text = re.sub(r'Sarkari\s*Result[^\n]*', '', text, flags=re.I)
    text = re.sub(r'https?://(?:www\.)?sarkariresult\.com[^\s]*', '', text, flags=re.I)

    patterns = [
        r'Age Limit.*?(Minimum Age.*?)(?:Vacancy Details|Eligibility|Total Post)',
        r'Age Limit\s*[:\-]?\s*([\s\S]{10,400}?)(?:Vacancy Details|Eligibility|Total Post|How to Fill|Important Links|Application Fee)',
        r'(?:Age Limit|Age)\s*[:\-]\s*(\d{2}.*?Years)',
    ]

    # Bad content indicators — agar match mein ye hain toh galat field capture hua
    BAD_CONTENT = [
        "course and university list", "admission 2026", "apply online",
        "recruitment", "notification", "short details", "fees,",
        "duvasu", "mathura", "upadhyaya", "pashu", "chikitsa",
        "information and other types",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.I | re.S)
        if not m:
            continue
        val = clean(m.group(1))
        # Skip if bad content detected
        if any(b in val.lower() for b in BAD_CONTENT):
            continue
        # Must contain age-related content
        if not re.search(r'\d{2}\s*(?:years?|वर्ष|year)', val, re.I):
            continue
        val = re.sub(r'WWW\.SARKARIRESULT\.COM[^\n]*', '', val, flags=re.I)
        val = re.sub(r'https?://[^\s]+', '', val)
        val = clean(val)
        if len(val) > 10:
            return val[:800]
    return ""


def sr_extract_eligibility(text):
    patterns = [
        # Vacancy Details section ke andar eligibility column
        r'Vacancy\s*Details[^\n]{0,100}\n(.*?)(?:Physical\s*Eligib|How\s*to\s*Fill|How\s*to\s*Apply|'
        r'Important\s*Links|Interested\s*Candidates|Download\s*Notification)',
        # Direct Eligibility heading
        r'(?:Indian\s+\w+\s+)?Eligibility\s*[:\-]?\s*(.*?)(?:Physical\s*Eligib|How\s*to\s*Fill|'
        r'How\s*to\s*Apply|Important\s*Links|Interested\s*Candidates)',
        r'Eligibility\s*Details?\s*(.*?)(?:Vacancy\s*Details|Important\s*Links)',
        r'Post\s*Name.*?Eligibility\s*(.*?)(?:Vacancy\s*Details|Important\s*Links)',
        r'Educational\s*Qualification\s*[:\-]?\s*(.*?)(?:Vacancy\s*Details|Important\s*Links|Age\s*Limit|How\s*to\s*Fill)',
        r'\bQualification\s*[:\-]\s*(.*?)(?:Vacancy|Important|Age|How\s*to)',
        # Fallback: "Only for" type eligibility (Navy pattern)
        r'(Only\s*for\s*(?:Unmarried|Male|Female)[^\n]{10,400})',
    ]
    BAD_LINES = ["post information", "selection procedure", "pay scale",
                 "all other information", "how to apply", "subject details information",
                 "document required", "official", "sarkari result",
                 "click here", "apply online", "download notification",
                 "candidates who are interested", "candidates who want to",
                 "those candidates", "read the notification for", "before applying",
                 "can apply online", "invited online application",
                 "notification and invited", "candidates are invited",
                 "apply online from", "recruitment notification"]
    for pat in patterns:
        m = re.search(pat, text, re.I | re.S)
        if not m:
            continue
        value = clean(m.group(1))
        low = value.lower()
        if any(x in low for x in BAD_LINES):
            continue
        value = re.sub(r'WWW\.SARKARIRESULT\.COM[^\n]*', '', value, flags=re.I)
        value = re.sub(r'Sarkari\s*Result[^\n]*', '', value, flags=re.I)
        value = clean(value)
        if len(value) < 20:
            continue
        return value[:2000]
    return ""


def sr_extract_total_post(text):
    patterns = [
        r'Total\s*:\s*(\d+)\s*Post',
        r'Total Post\s*[:\-]?\s*(\d+)',
        r'Vacancy Details Total\s*[:\-]?\s*(\d+)',
        r'Total Vacancy\s*[:\-]?\s*(\d+)',
        r'\bTotal\b\s*[:\-]\s*(\d{1,6})\b',
        r'Total Vacancies\s*[:\-]?\s*(\d+)',
        r'Total Posts\s*[:\-]?\s*(\d+)',
        r'No\.?\s*of\s*Posts?\s*[:\-]?\s*(\d+)',
        r'No\.?\s*of\s*Vacanc(?:y|ies)\s*[:\-]?\s*(\d+)',
        r'\bVacanc(?:y|ies)\s*[:\-]\s*(\d+)',
        r'\bTotal\s{2,}(\d{1,6})\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1)
    return ""


def sr_extract_dates(text):
    patterns = {
        "application_begin": r'Application Begin\s*:\s*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4})',
        "last_date":         r'Last Date[^:\n]{0,40}:\s*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4})',
        "exam_date":         r'Exam Date\s*:\s*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4})',
        "admit_card":        r'Admit Card Available\s*:\s*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4}|Before Exam|Available Soon|Notified Soon)',
        "result_date":       r'Result Declared\s*:\s*([A-Za-z]{3,15}\s?[0-9]{0,4})',
    }
    data = {}
    for key, pat in patterns.items():
        m = re.search(pat, text, re.I)
        if m:
            data[key] = date_to_iso(clean(m.group(1)))
    return data


def sr_extract_tables(soup):
    """
    Dynamic Job Structure Recognition & Extraction System
    ═══════════════════════════════════════════════════════════════════════════
    Problem: sarkariresult.com ke alag-alag pages pe table structure alag-alag
    hoti hai. Kuch pages pe "Important Dates", "Application Fee", "Vacancy Details"
    alag-alag tables hoti hain. Kuch pages pe sab ek hi table mein hoti hain.
    Pehle sab mix ho jaati thi, koi table name nahi aata tha.

    Solution — Intelligent Table Detection:
      1. Har table ka heading/name detect karo (preceding sibling, caption,
         thead row, ya table ke andar ka pehla merged/bold row).
      2. Known section names map karo (Important Dates, Application Fee,
         Vacancy Details, Age Limit, Eligibility, Important Links etc.)
      3. Sirf meaningful rows rakho — social, noise, Sarkari Result branding,
         promotional content hata do.
      4. Output: [{table_name: str, rows: [[col, col, ...], ...]}, ...]
         — downstream compatible (same structure, naam extra field hai)

    Table Name Detection Priority:
      P1: Preceding <h2>/<h3>/<h4>/<strong>/<b> sibling (nearest above table)
      P2: <caption> tag andar table ke
      P3: First <tr> with single colspan (header row spanning full width)
      P4: First <thead> row ya pehli <tr> jisme sab <th> hain
      P5: Parent div ka ID/class ya heading sibling
      P6: "Unknown Table" (fallback)
    ═══════════════════════════════════════════════════════════════════════════
    """

    # ── Noise/Social filters ────────────────────────────────────────────────
    SOCIAL_ROW_WORDS = [
        "android apps", "apple ios", "telegram", "whatsapp",
        "remove background", "join channel", "join now", "subscribe",
        "sarkari result tools", "sarkariresult.tools",
    ]
    SOCIAL_TABLE_MARKERS = [
        "join telegram", "join whatsapp", "android apps download", "apple ios app",
    ]
    # Promotional / self-referential content filter
    PROMO_PATTERNS = [
        r"thank you for visiting.*sarkari result",
        r"sarkariresult\.com.*official website",
        r"www\.sarkariresult\.com",
        r"through this website.*information related to",
        r"rojgarresult\.com",
    ]
    PROMO_RE = re.compile("|".join(PROMO_PATTERNS), re.I)

    # Sarkari Result branding row words
    SR_BRAND_WORDS = [
        "sarkari result", "sarkariresult", "sarkariresult.com",
        "sarkari result portal", "image resizer", "jpg to pdf",
        "age calculator", "resume cv maker",
    ]

    # ── Known section name normalization ───────────────────────────────────
    SECTION_NAME_MAP = {
        # Important Dates
        "important date":      "Important Dates",
        "key date":            "Important Dates",
        "application date":    "Important Dates",
        "exam schedule":       "Important Dates",
        "schedule":            "Important Dates",
        # Application Fee
        "application fee":     "Application Fee",
        "exam fee":            "Application Fee",
        "fee detail":          "Application Fee",
        # Vacancy Details
        "vacancy detail":      "Vacancy Details",
        "post detail":         "Vacancy Details",
        "post name":           "Vacancy Details",
        "post wise":           "Vacancy Details",
        "category wise":       "Vacancy Details",
        "district wise":       "Vacancy Details",
        "total vacancy":       "Vacancy Details",
        "total post":          "Vacancy Details",
        # Age Limit
        "age limit":           "Age Limit",
        "age detail":          "Age Limit",
        # Eligibility
        "eligibility":         "Eligibility",
        "qualification":       "Eligibility",
        "educational":         "Eligibility",
        # Important Links
        "important link":      "Important Links",
        "useful link":         "Important Links",
        "some useful":         "Important Links",
        "apply online":        "Important Links",
        # Selection Process
        "selection process":   "Selection Process",
        "selection procedure": "Selection Process",
        # Salary / Pay Scale
        "pay scale":           "Salary / Pay Scale",
        "salary":              "Salary / Pay Scale",
        "pay matrix":          "Salary / Pay Scale",
        # Short Information
        "short information":   "Short Information",
        "short detail":        "Short Information",
        "brief detail":        "Short Information",
    }

    def _normalize_section_name(raw_name):
        """
        Raw heading text ko standard section name mein map karo.

        RULE: Table names EXACTLY as they appear in HTML preserve karo.
        Sirf ek kaam: trailing punctuation clean karo.

        Koi rename mat karo:
          "Age Limit as on 01/07/2024" → stays exactly as is
          "UPSSSC Technical Assistant 2024 : Category Wise" → stays exactly as is
          "Important Dates" → "Important Dates" (short generic → OK to map)
        """
        if not raw_name:
            return ""
        raw_name = re.sub(r"\s+", " ", raw_name).strip()
        raw_name = re.sub(r"[:\-–]+$", "", raw_name).strip()
        low = raw_name.lower()

        # Preserve any heading that contains a date (like "Age Limit as on 01/07/2024")
        if re.search(r"\d{2}[/\-]\d{2}[/\-]\d{4}", raw_name):
            return raw_name[:200]

        # Preserve long descriptive names (> 50 chars) as-is
        if len(raw_name) > 50:
            return raw_name[:200]

        # Short generic headings only — map to standard names
        for key, val in SECTION_NAME_MAP.items():
            if key in low:
                return val

        return raw_name[:200] if raw_name else ""

    # Sarkari Result ke watermark / brand strings jo table name nahi hain
    SR_WATERMARK_WORDS = [
        "sarkari result", "sarkariresult", "www.sarkariresult",
        "®", "©", "copyright", "all rights reserved",
    ]

    def _is_watermark_text(text):
        """Text ek SR watermark/brand hai — valid table name nahi."""
        low = text.lower()
        return any(w in low for w in SR_WATERMARK_WORDS)

    def _get_table_name(table_tag):
        """
        Table ka naam detect karo — sarkariresult.com-specific logic.

        Sarkariresult.com page structure:
        ─────────────────────────────────────────────────────────────
        Har section ek <table> hai. Table structure:
          Row 0  : Single merged cell (colspan=N) = TABLE NAME
                   e.g. "Vacancy Details Total 12256 Post"
                        "SSC CGL Exam 2026 : Department Wise Post Details"
                        "Important Dates"
                        "Application Fee"
          Row 1+ : Actual data rows (2-column key|value, or multi-col)

        Lekin kuch tables mein Row-0 ek SR watermark/logo hota hai
        jaise "SARKARI RESULT ®" — yeh table name NAHI hai, skip karo.

        Detection priority:
          P1 : Table ke andar PEHLI single-cell row (colspan >= total cols)
               → Yeh actual table heading hai (sarkariresult.com primary pattern)
               → Watermark/brand text skip karo
               → Text length limit 400 tak (dates+fee ek saath bhi aa sakti hain)
          P2 : Table ke bahar nearest preceding <h2>/<h3>/<h4>/<b>/<strong>
               → Only if NOT watermark
          P3 : <caption> tag
          P4 : Table ke andar koi bhi single-cell row (not just first)
               → Iteratively scan karo
          P5 : Parent div ID/class hint
          P6 : "" (fallback — "General Information" baad mein assign hoga)

        Returns: (name_str, rows_to_skip: int)
          rows_to_skip = kitni starting rows table name ke liye use hui hain
        """

        all_trs = table_tag.find_all("tr", recursive=False)
        if not all_trs:
            # Nested table — find all trs
            all_trs = table_tag.find_all("tr")

        total_cols_hint = 0
        # Figure out max columns in this table (for colspan check)
        for tr in all_trs[:5]:
            n = len(tr.find_all(["td", "th"]))
            if n > total_cols_hint:
                total_cols_hint = n

        # ── P1: Scan table rows for single merged header cell ──────────────────
        # Check first 4 rows normally. BUT also detect mid-table "section break"
        # rows — SR packs multiple sections in ONE table, each section starts
        # with a colspan heading. Use the LAST vacancy/post heading found.
        _mid_vacancy_name = None
        for _tr in all_trs[:12]:  # scan more rows for mid-table headings
            _cells = _tr.find_all(["td","th"])
            if len(_cells) == 1:
                _cs = int(_cells[0].get("colspan", 1))
                _txt = clean(_cells[0].get_text(" ", strip=True))
                if _cs >= 2 and 5 < len(_txt) <= 200 and not _is_watermark_text(_txt):
                    _low = _txt.lower()
                    if any(k in _low for k in ["vacancy", "post detail", "post wise",
                                               "category wise", "department wise",
                                               "district wise", "total post"]):
                        # Strip Age Limit boilerplate if packed together
                        for _sp in [r"\s*:?\s*Age\s+Limit",
                                    r"\s*:?\s*Application\s+Fee"]:
                            _pp = re.split(_sp, _txt, maxsplit=1, flags=re.I)
                            if len(_pp) > 1 and _pp[0].strip():
                                _txt = _pp[0].strip().rstrip(":").strip()
                                break
                        _mid_vacancy_name = _normalize_section_name(_txt)

        for row_idx, tr in enumerate(all_trs[:4]):   # Check first 4 rows only
            cells = tr.find_all(["td", "th"])
            if len(cells) != 1:
                continue
            cell      = cells[0]
            colspan   = int(cell.get("colspan", 1))
            cell_text = clean(cell.get_text(" ", strip=True))

            # Must have content
            if not cell_text or len(cell_text) < 3:
                continue

            # Skip watermark/brand cells
            if _is_watermark_text(cell_text):
                continue

            # Skip pure noise (social, promo)
            if PROMO_RE.search(cell_text):
                continue

            # Valid table name: colspan >= 2 OR it's the only cell in row
            # AND length reasonable (upto 400 — sarkariresult packs dates+fee together)
            if (colspan >= 2 or total_cols_hint <= 1) and len(cell_text) <= 400:
                # Extract just the section title — sarkariresult often puts
                # "Vacancy Details Total 12256 Post" or
                # "SSC CGL 2026 : Department Wise Post Details"
                # We preserve the full text as name (it IS the heading)
                name = re.sub(r"\s+", " ", cell_text).strip()
                # STRIP: Age Limit / fee / date boilerplate jo SR packs
                # into the title cell — sirf recruitment title part rakhna hai.
                # e.g. "HCL Executive Notification 2026 : Age Limit as on 01/05/2026
                #        Minimum Age : ... Rules." → "HCL Executive Notification 2026"
                for _split_pat in [
                    r"\s*:?\s*Age\s+Limit\b",
                    r"\s*:?\s*Application\s+Fee\b",
                    r"\s*:?\s*Important\s+Dates?\b",
                ]:
                    _parts = re.split(_split_pat, name, maxsplit=1, flags=re.I)
                    if len(_parts) > 1 and _parts[0].strip():
                        name = _parts[0].strip().rstrip(":").strip()
                        break
                if len(name) > 120:
                    name = name[:120].rsplit(" ", 1)[0]
                return name, row_idx + 1   # skip up-to-and-including this row

        # ── P1b: Use mid-table vacancy heading if found ────────────────────────
        if _mid_vacancy_name:
            return _mid_vacancy_name, 0

        # ── P2: Nearest preceding sibling heading ──────────────────────────────
        for sib in table_tag.previous_siblings:
            if not hasattr(sib, "get_text"):
                continue
            tag_name = getattr(sib, "name", "")

            if tag_name in ["h1", "h2", "h3", "h4", "h5"]:
                text = clean(sib.get_text())
                if 3 < len(text) < 200 and not _is_watermark_text(text):
                    return _normalize_section_name(text), 0

            if tag_name in ["p", "div"]:
                # Bold/strong inside
                inner = sib.find(["strong", "b", "h3", "h4"])
                if inner:
                    text = clean(inner.get_text())
                    if 3 < len(text) < 150 and not _is_watermark_text(text):
                        return _normalize_section_name(text), 0
                # Short plain div
                text = clean(sib.get_text())
                if 3 < len(text) < 80 and not _is_watermark_text(text):
                    return _normalize_section_name(text), 0

            # Stop walking up after 3 non-empty siblings (too far = wrong table)
            if tag_name:
                sib_text_len = len(clean(sib.get_text()))
                if sib_text_len > 5:
                    break

        # ── P3: <caption> tag ──────────────────────────────────────────────────
        caption = table_tag.find("caption")
        if caption:
            text = clean(caption.get_text())
            if text and not _is_watermark_text(text):
                return _normalize_section_name(text), 0

        # ── P4: Any single-cell row anywhere (deeper scan) ─────────────────────
        for tr in all_trs:
            cells = tr.find_all(["td", "th"])
            if len(cells) == 1:
                text = clean(cells[0].get_text(" ", strip=True))
                if 3 < len(text) < 300 and not _is_watermark_text(text) and not PROMO_RE.search(text):
                    return _normalize_section_name(text), 0

        # ── P5: Parent div ID/class ────────────────────────────────────────────
        # STRICT: CSS utility classes (gb-headline-HASH, numeric slugs, etc.)
        # ko table_name mat banao. Sirf meaningful semantic IDs allow karo.
        import re as _re2
        def _is_css_junk(attr_text):
            """True agar attr_text sirf CSS class names/hashes hai."""
            # Hash segments: 6-8 hex chars (like 60ccea19)
            if _re2.search(r'\b[0-9a-f]{6,8}\b', attr_text):
                return True
            # Pure framework class patterns: gb-headline, wp-block-*, gb-container etc.
            if _re2.search(r'\b(?:gb|wp|et|elementor|vc|fusion)\b', attr_text):
                return True
            # More than half the "words" are single chars or pure digits
            words = attr_text.split()
            if not words:
                return True
            junk_words = sum(1 for w in words if len(w) <= 1 or w.isdigit())
            return junk_words / len(words) > 0.4

        parent = table_tag.parent
        depth  = 0
        while parent and parent.name not in ["body", "html", None] and depth < 4:
            pid = parent.get("id", "").replace("-", " ").replace("_", " ").strip()
            if pid and not _is_css_junk(pid.lower()):
                norm = _normalize_section_name(pid)
                if norm and len(norm) > 5:
                    return norm, 0
            # CSS class list — skip entirely (too noisy, causes "gb headline..." bugs)
            parent = parent.parent
            depth += 1

        return "", 0

    # Important Links table markers — ye tables `tables` array mein nahi aani chahiye
    # (woh already `useful_links` mein capture hoti hain)
    LINKS_TABLE_MARKERS = [
        "some useful important links", "useful important links",
        "important links", "some important links", "important useful links",
        "useful links", "some useful links",
    ]

    # Right-cell values jo sirf link placeholders hain (actual data nahi)
    CLICK_HERE_VALUES = {
        "click here", "यहाँ क्लिक करें", "here", "link", "open",
        "view", "check", "download here", "apply here", "register here",
        "click", "visit", "login here", "register | login", "registration | login",
    }

    def _is_noise_row(cols):
        """Row noise/social/branding/link-placeholder hai toh True."""
        joined = " ".join(cols).lower()
        if any(x in joined for x in SOCIAL_ROW_WORDS):
            return True
        if any(x in joined for x in SR_BRAND_WORDS):
            return True
        if PROMO_RE.search(joined):
            return True

        # 2-column row jahan right cell sirf "Click Here" ya similar hai
        # → Yeh Important Links row hai, table data nahi
        if len(cols) == 2:
            left_val  = cols[0].lower().strip()
            right_val = cols[1].lower().strip()

            # Exact match ya very short click-type text
            if right_val in CLICK_HERE_VALUES:
                return True
            # "Click Here" / "Click here to" pattern
            if re.match(r'^click\s*here', right_val, re.I):
                return True
            # "Registration | Login" / "Register | Login" — link buttons
            if re.match(r'^(register|login|registration)\s*[\|\/]', right_val, re.I):
                return True
            # Video Hindi / How to check (video) — instructional links in tables
            if re.search(r'video\s*(?:hindi|english)', right_val, re.I):
                return True
            # "Version I | Version II" — video link variants
            if re.search(r'version\s*i{1,2}\b', right_val, re.I):
                return True

            # Left cell is a known "Useful Links" label — not vacancy data
            # These rows slip in from "Some Useful Important Links" section
            _USEFUL_LINK_LABELS = {
                "how to fill form", "how to fill", "download syllabus",
                "download notification", "download admit card",
                "signature resizer", "age calculator", "resume maker",
                "photo resizer", "pdf converter", "image resizer",
                "image to pdf", "word to pdf", "pdf to word",
                "how to check", "how to apply video", "video tutorial",
                "official website", "official site",
                "mock test", "previous paper",
                "ssc otr", "otr instruction", "photo instruction",
            }
            for _lbl in _USEFUL_LINK_LABELS:
                if _lbl in left_val:
                    return True

            # Right cell is a generic tool/website name placeholder
            _PLACEHOLDER_RIGHTS = {
                "tools", "tool", "website", "portal",
            }
            if right_val in _PLACEHOLDER_RIGHTS:
                return True

            # Right is "XYZ Official Website" / "XYZ Syllabus" (link label, not data)
            if re.search(r'official\s+website$', right_val, re.I):
                return True
            if re.search(r'syllabus$', right_val, re.I) and len(right_val) < 50:
                return True

        return False

    def _clean_cell(text):
        """Cell text se Sarkari Result branding hata do."""
        text = re.sub(r"Sarkari Result\s*(?:Portal)?", "", text, flags=re.I)
        text = re.sub(r"SarkariResult(?:\.Com)?", "", text, flags=re.I)
        text = re.sub(r"WWW\.SARKARIRESULT\.COM", "", text, flags=re.I)
        return clean(text)

    # ── First-table detector: "Name Of Post" / "Short Information" table ──────
    # Sarkariresult.com ka pehla table hamesha job overview hota hai (no visible heading).
    # Isko "Job Overview" naam do.
    def _is_overview_table(table_tag):
        """True agar yeh SR ka pehla 'Name Of Post / Short Info' table hai."""
        trs = table_tag.find_all("tr")
        if not trs:
            return False
        first_cells = trs[0].find_all(["td","th"])
        if len(first_cells) >= 1:
            txt = clean(first_cells[0].get_text()).lower()
            if any(k in txt for k in ["name of post", "post name :", "short information"]):
                return True
        return False

    # ── Main extraction loop ────────────────────────────────────────────────
    output      = []
    table_seen  = set()
    row_seen    = set()

    for table in soup.select("table, div.table-responsive table"):
        table_text = clean(table.get_text(" ", strip=True)).lower()

        # Skip pure social/promotional tables
        if any(m in table_text for m in SOCIAL_TABLE_MARKERS) and len(table_text) < 300:
            continue
        if PROMO_RE.search(table_text) and len(table_text) < 500:
            continue

        # Skip Important Links tables — already captured in useful_links
        # (Check first ~200 chars of table text for link-table markers)
        table_head_text = table_text[:300]
        if any(m in table_head_text for m in LINKS_TABLE_MARKERS):
            continue

        # Detect table name
        table_name, rows_to_skip = _get_table_name(table)

        rows = []
        row_idx = 0
        # rowspan carry-forward: col_pos → (cell_text, remaining_rows)
        _rs_carry = {}

        for tr in table.find_all("tr"):
            if row_idx < rows_to_skip:
                row_idx += 1
                continue
            row_idx += 1

            raw_cells = tr.find_all(["td", "th"])

            # Build cols with rowspan carry-forward
            cols = []
            ci = 0       # index into raw_cells
            vp = 0       # virtual column position

            while vp < 30 and (ci < len(raw_cells) or vp in _rs_carry):
                if vp in _rs_carry:
                    txt, left = _rs_carry[vp]
                    cols.append(txt)
                    left -= 1
                    if left <= 0:
                        del _rs_carry[vp]
                    else:
                        _rs_carry[vp] = (txt, left)
                    vp += 1
                    continue
                if ci >= len(raw_cells):
                    break
                cell = raw_cells[ci]
                txt  = _clean_cell(cell.get_text(" ", strip=True))
                rs   = int(cell.get("rowspan", 1))
                cs   = int(cell.get("colspan", 1))
                if rs > 1 and txt:
                    _rs_carry[vp] = (txt, rs - 1)
                # colspan: sirf ONCE add karo (duplicate columns avoid)
                if txt:
                    cols.append(txt)
                vp += cs   # skip all spanned positions
                ci += 1

            cols = [x for x in cols if x]

            if not cols or len(cols) == 1:
                continue
            if _is_noise_row(cols):
                continue

            # Skip rows that are purely the table name repeated
            if len(cols) == 1 and cols[0].lower().strip() == table_name.lower().strip():
                continue

            row_key = hashlib.md5(json.dumps(cols).encode()).hexdigest()
            if row_key in row_seen:
                continue
            row_seen.add(row_key)
            rows.append(cols)

        rows = rows[:80]
        if not rows:
            continue

        table_key = hashlib.md5(json.dumps(rows).encode()).hexdigest()
        if table_key in table_seen:
            continue
        table_seen.add(table_key)

        # Job Overview table (Name Of Post / Short Information) skip karo
        # — ye data already short_information, name_of_post fields mein hai
        if _is_overview_table(table):
            continue

        # ── headers detection ──────────────────────────────────────────────
        # First row: agar saari cells short text hain (< 60 chars) aur koi bhi
        # numeric value nahi hai → ye header row hai → headers[] mein rakho
        headers = []
        data_rows = rows
        if rows:
            first_row = rows[0]
            is_header = (
                len(first_row) >= 2
                and all(len(str(c)) < 80 for c in first_row)
                and not any(re.match(r'^\d{3,}$', str(c).strip()) for c in first_row)
                and any(re.search(
                    r'post.?name|total|eligib|grade|subject|category|general|obc|sc\b|st\b|ews|'
                    r'date|fee|age|year|detail|marks|vacanci|department|district',
                    str(c), re.I) for c in first_row)
            )
            if is_header:
                headers = [str(c).strip() for c in first_row]
                data_rows = rows[1:]

        entry = {"table_name": table_name if table_name else "General Information"}
        if headers:
            entry["headers"] = headers
        entry["rows"] = data_rows
        output.append(entry)

    return output[:30]


def sr_extract_useful_links(soup):
    """
    Universal Dynamic Official Link Detection System
    ═══════════════════════════════════════════════════════════════════════════════
    Problem: sarkariresult.com ke alag-alag job pages pe useful_links alag-alag
    format mein hote hain:
      - Kuch pages pe "Some Useful Important Links" heading wali table hoti hai
      - Kuch pages pe (e.g. Delhi DSSSB Result) heading alag hoti hai ya nahi hoti
      - Links table format, button format, text format, redirect URLs mein ho sakti hain
      - Click Here / यहाँ क्लिक करें / button anchors — sab ko handle karna hai

    Solution — 5-layer detection cascade:
      Layer 1 : "Some Useful Important Links" exact table (original logic — highest precision)
      Layer 2 : ANY table jisme heading row "important links" / "useful links" / "links" ho
      Layer 3 : Known anchor-text keywords (Download/Apply/Result/Admit etc.) from ALL tables
      Layer 4 : "Click Here" / "यहाँ क्लिक करें" button pattern — left cell = label, right = Click Here
      Layer 5 : Proximity scan — valid URL anchors ke nearest preceding label-like text

    Output format (unchanged so downstream code breaks nahi hota):
      [{"title": "<label>", "links": "<url>" | ["<url1>", "<url2>"]}, ...]
    ═══════════════════════════════════════════════════════════════════════════════
    """

    # ── Shared constants ────────────────────────────────────────────────────────

    # Label keywords jo VALID official job links indicate karte hain
    VALID_LABEL_KEYWORDS = [
        "apply online", "apply now", "registration", "login",
        "notification", "download notification", "download notice", "official notice",
        "advertisement", "advt",
        "admit card", "download admit card", "hall ticket",
        "result", "download result", "check result", "merit list", "score card",
        "answer key", "download answer key", "challenge answer key",
        "response sheet", "omr sheet",
        "syllabus", "exam pattern", "exam notice",
        "cutoff", "cut off", "cutoff notice",
        "revised vacancy", "vacancy notice",
        "eligibility", "eligibility result",
        "fees payment", "date extended", "exam date notice",
        "check exam city", "exam city",
        "correction", "edit form", "form correction",
        "skill test", "skill test admit card", "skill test result",
        "document verification", "dv schedule",
        "interview schedule", "interview notice",
        "joining letter", "appointment letter",
        "official website", "official site",
        "download", "check here", "click here",
    ]

    # BAD labels — social media, tools, noise — skip
    BAD_LABEL_KEYWORDS = [
        "telegram", "whatsapp", "android", "apple ios", "youtube",
        "facebook", "instagram", "twitter", "x.com",
        "remove background", "tool portal", "join channel",
        "sarkari result tools", "join now", "subscribe",
        "play store", "app store", "google play",
        "thank you for visiting", "official website of sarkari",
        "sarkariresult.com", "sarkari result portal",
        "image resizer", "age calculator", "resume cv maker", "jpg to pdf",
    ]

    # Promotional / self-referential content that should never appear as a link entry
    PROMO_TITLE_RE = re.compile(
        r"(thank you for visiting|sarkari result portal|sarkariresult\.com"
        r"|image resizer|age calculator|resume cv maker|jpg to pdf"
        r"|through this website.*job|rojgarresult\.com)",
        re.I
    )

    # BAD URL patterns — block list (same as is_sr_blocked but explicit here)
    BAD_URL_PATTERNS = SR_BLOCK_WORDS + [
        "sarkariresult.com", "sarkariresultshine.com",
        "play.google", "itunes", "apple-ios", "android-app",
        "rojgarresult.com",
        "youtube.com", "youtu.be", "youtube",
    ]

    def _is_valid_official_url(url):
        """URL valid official link hai ya nahi."""
        if not url or not url.strip():
            return False
        url = url.strip()
        try:
            p = urlparse(url)
            if p.scheme not in ("http", "https"):
                return False
        except Exception:
            return False
        url_low = url.lower()
        return not any(bad in url_low for bad in BAD_URL_PATTERNS)

    def _is_valid_label(label_text):
        """Label genuine job-link label hai ya noise."""
        if not label_text:
            return False
        low = label_text.lower().strip()
        if len(low) < 3 or len(low) > 160:
            return False
        if any(b in low for b in BAD_LABEL_KEYWORDS):
            return False
        if PROMO_TITLE_RE.search(label_text):
            return False
        return True

    def _is_useful_label(label_text):
        """Label kisi useful official link ko refer karta hai."""
        low = label_text.lower()
        return any(v in low for v in VALID_LABEL_KEYWORDS)

    def _collect_urls_from_cell(cell_tag):
        """Table cell ya element se sab valid URLs nikalo."""
        urls = []
        seen = set()
        for a in cell_tag.find_all("a", href=True):
            url = a.get("href", "").strip()
            if url and url not in seen and _is_valid_official_url(url):
                urls.append(url)
                seen.add(url)
        return urls

    def _build_entry(title, urls):
        """Output dict banana."""
        urls = list(dict.fromkeys(urls))  # dedupe, order preserve
        if not urls:
            return None
        return {
            "title": title,
            "links": urls[0] if len(urls) == 1 else urls,
        }

    # ── Deduplication across all layers ────────────────────────────────────────
    seen_titles = set()
    seen_urls   = set()
    results     = []

    def _add(title, urls):
        title_key = title.lower().strip()
        # Promotional / branding titles — skip
        if PROMO_TITLE_RE.search(title):
            return
        new_urls  = [u for u in urls if u not in seen_urls]
        if not new_urls or title_key in seen_titles:
            return
        seen_titles.add(title_key)
        for u in new_urls:
            seen_urls.add(u)
        entry = _build_entry(title, new_urls)
        if entry:
            results.append(entry)

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 1: "Some Useful Important Links" exact heading table
    # ══════════════════════════════════════════════════════════════════════════
    LAYER1_MARKERS = [
        "some useful important links",
        "useful important links",
        "important links",
        "some important links",
        "important useful links",
    ]

    layer1_tables = []
    for table in soup.find_all("table"):
        txt_low = clean(table.get_text(" ", strip=True)).lower()
        if any(m in txt_low for m in LAYER1_MARKERS):
            layer1_tables.append(table)

    for target_table in layer1_tables:
        for row in target_table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue
            label = clean(cols[0].get_text(" ", strip=True))
            if not _is_valid_label(label):
                continue
            urls = _collect_urls_from_cell(row)
            if urls:
                _add(label, urls)

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 2: Any table with "links" in heading row / caption
    # (catches pages where heading text is different)
    # ══════════════════════════════════════════════════════════════════════════
    LAYER2_HEADING_WORDS = ["link", "download", "result link", "important"]

    for table in soup.find_all("table"):
        # Check first row or caption for heading clue
        heading_text = ""
        caption = table.find("caption")
        if caption:
            heading_text = clean(caption.get_text()).lower()
        first_tr = table.find("tr")
        if first_tr:
            heading_text += " " + clean(first_tr.get_text()).lower()

        if not any(w in heading_text for w in LAYER2_HEADING_WORDS):
            continue

        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue
            label = clean(cols[0].get_text(" ", strip=True))
            if not _is_valid_label(label) or not _is_useful_label(label):
                continue
            urls = _collect_urls_from_cell(row)
            if urls:
                _add(label, urls)

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 3: Keyword-matched anchor text anywhere in ALL tables
    # (handles tables with NO section heading — e.g. Delhi DSSSB type pages)
    # 2-column rows: left = label, right = links
    # ══════════════════════════════════════════════════════════════════════════
    CLICK_WORDS = {"click here", "यहाँ क्लिक करें", "here", "link", "open", "view", "check"}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue

            left_text  = clean(cols[0].get_text(" ", strip=True))
            right_text = clean(cols[-1].get_text(" ", strip=True)).lower()

            # Skip header rows
            if left_text.lower() in {"some useful important links", "important links",
                                     "useful links", "links", "action", "download"}:
                continue

            if not _is_valid_label(left_text):
                continue

            # Must be useful (download/apply/result etc.)
            if not _is_useful_label(left_text):
                # Also accept if right cell is a "Click Here"-type button
                if not any(cw in right_text for cw in CLICK_WORDS):
                    continue

            urls = _collect_urls_from_cell(row)
            if urls:
                _add(left_text, urls)

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 4: "Click Here" button pattern outside tables
    # (Some pages render links as <p>/<div> with label + button)
    # Pattern: <tag>label text</tag> <a>Click Here</a>
    # ══════════════════════════════════════════════════════════════════════════
    CLICK_ANCHORS = re.compile(
        r"click\s*here|यहाँ\s*क्लिक|download\s*here|apply\s*here|check\s*here|view\s*here",
        re.I
    )

    for a_tag in soup.find_all("a", href=True):
        a_text = clean(a_tag.get_text())
        if not CLICK_ANCHORS.search(a_text):
            continue
        url = a_tag.get("href", "").strip()
        if not _is_valid_official_url(url):
            continue

        # Walk up to find the nearest container and extract label
        label = ""
        parent = a_tag.parent
        if parent:
            # Try: text before this anchor in same parent
            siblings_text_parts = []
            for sib in a_tag.previous_siblings:
                sib_text = clean(sib.get_text()) if hasattr(sib, "get_text") else str(sib).strip()
                if sib_text:
                    siblings_text_parts.insert(0, sib_text)
            label = " ".join(siblings_text_parts).strip()

            if not label:
                # Fallback: parent text minus anchor text
                parent_text = clean(parent.get_text(" ", strip=True))
                anchor_text = clean(a_tag.get_text())
                label = parent_text.replace(anchor_text, "").strip(" :-|–")

        label = label[:160].strip()
        if not _is_valid_label(label) or not _is_useful_label(label):
            continue
        _add(label, [url])

    # ══════════════════════════════════════════════════════════════════════════
    # LAYER 5: Proximity / context scan
    # Walk all elements; when we find a valid URL anchor whose nearest
    # preceding text element looks like a label — capture it.
    # Used as last-resort for highly irregular page structures.
    # ══════════════════════════════════════════════════════════════════════════
    if len(results) < 3:  # Only run if earlier layers found very few links
        all_anchors = soup.find_all("a", href=True)
        for a_tag in all_anchors:
            url = a_tag.get("href", "").strip()
            if not _is_valid_official_url(url):
                continue

            # Find the nearest preceding text block
            label = ""
            for sib in a_tag.previous_siblings:
                t = clean(sib.get_text()) if hasattr(sib, "get_text") else str(sib).strip()
                if t and len(t) > 3:
                    label = t[:160]
                    break
            if not label:
                # Try parent's preceding sibling
                p = a_tag.parent
                if p:
                    for sib in p.previous_siblings:
                        t = clean(sib.get_text()) if hasattr(sib, "get_text") else str(sib).strip()
                        if t and len(t) > 3:
                            label = t[:160]
                            break

            if not _is_valid_label(label) or not _is_useful_label(label):
                # Use anchor's own text as label if it is descriptive enough
                a_own = clean(a_tag.get_text())
                if _is_useful_label(a_own) and len(a_own) > 5:
                    label = a_own
                else:
                    continue

            _add(label, [url])

    return results[:60]


def sr_extract_text_sections(soup):
    """
    Non-table text/list sections extract karo sarkariresult.com pages se.

    Sarkariresult.com pe kuch sections table format mein nahi hoti:
      - "How to Fill SSC CGL 2026 Exam Online Form"
      - "How to Apply"
      - "Selection Process"
      - Numbered/bulleted steps

    Strategy:
      1. Page ke <h2>/<h3>/<h4>/<b>/<strong> headings dhundho
      2. Jo headings known text-section keywords se match karti hain
         (How to Fill, How to Apply, Selection Process, etc.)
      3. Unke baad ka text (next sibling paras/lists tak next heading)
         extract karo — table nahi

    Output: [{"section": "How to Fill ...", "content": "Step 1: ..."}, ...]
    """
    TEXT_SECTION_KEYWORDS = [
        "how to fill", "how to apply", "how to register",
        "selection process", "selection procedure",
        "document required", "required documents",
        "exam pattern", "exam scheme",
        "important instruction", "general instruction",
        "note :", "note:", "important note",
    ]

    # Noise phrases — agar heading mein ye hain toh skip
    HEADING_NOISE = [
        "sarkari result", "sarkariresult", "click here",
        "apply online", "download", "official website",
    ]

    BRAND_RE = re.compile(
        r"(sarkari\s*result|sarkariresult|www\.sarkariresult|"
        r"whatsapp|telegram|join\s+channel|join\s+now|"
        r"android\s+app|apple\s+ios)",
        re.I
    )

    sections = []
    seen_headings = set()

    # Find all candidate heading elements
    heading_tags = soup.find_all(["h2", "h3", "h4", "strong", "b", "p"])

    for tag in heading_tags:
        # Must be a block-level or near-block element
        text = clean(tag.get_text())
        if not text or len(text) < 8 or len(text) > 200:
            continue

        low = text.lower()

        # Must match a text-section keyword
        if not any(kw in low for kw in TEXT_SECTION_KEYWORDS):
            continue

        # Skip noise headings
        if any(n in low for n in HEADING_NOISE):
            continue

        # Dedup
        heading_key = low.strip()
        if heading_key in seen_headings:
            continue
        seen_headings.add(heading_key)

        # Now collect content after this heading
        content_parts = []
        for sib in tag.next_siblings:
            sib_name = getattr(sib, "name", None)
            if not sib_name:
                # NavigableString
                t = str(sib).strip()
                if t:
                    content_parts.append(t)
                continue

            sib_text = clean(sib.get_text())

            # Stop at next section heading
            if sib_name in ["h2", "h3", "h4"] and sib_text:
                break

            # Stop at table (tables handled separately)
            if sib_name == "table":
                break

            # Stop at another bold/strong that looks like a heading
            if sib_name in ["p", "div"]:
                inner_heading = sib.find(["h3", "h4", "strong", "b"])
                if inner_heading:
                    inner_text = clean(inner_heading.get_text())
                    if len(inner_text) > 10 and any(
                        kw in inner_text.lower() for kw in TEXT_SECTION_KEYWORDS
                    ):
                        break

            if not sib_text:
                continue

            # Skip brand/social lines
            if BRAND_RE.search(sib_text):
                continue

            # Collect list items or paragraph text
            if sib_name in ["ul", "ol"]:
                items = [clean(li.get_text()) for li in sib.find_all("li")]
                items = [i for i in items if i and not BRAND_RE.search(i)]
                if items:
                    content_parts.extend(items)
            elif sib_name in ["p", "div", "span", "li"]:
                if len(sib_text) > 5:
                    content_parts.append(sib_text)

            # Stop collecting after ~800 chars to avoid runaway
            if sum(len(x) for x in content_parts) > 800:
                break

        content = " | ".join(content_parts).strip()
        # Clean up brand references from content
        content = re.sub(r"(sarkari\s*result|sarkariresult\.com)[^\n]*", "", content, flags=re.I)
        content = clean(content)

        if len(content) > 20:
            sections.append({
                "section": text,
                "content": content[:1000],
            })

    return sections[:10]


def sr_extract_important_dates_structured(text):
    """
    Important Dates section se structured dict extract karo.

    ── Dynamic approach ──────────────────────────────────────────────────────
    Koi hardcoded keys nahi. Strategy:
      1. "Important Dates" section isolate karo (text ke andar)
      2. Har "Label : Value" line parse karo dynamically
      3. Date/text value detect karo (DD/MM/YYYY, Month YYYY, "Before Exam" etc.)
      4. Label ko snake_case key mein convert karo
      5. Known labels ke liye normalized keys bhi assign karo
         (e.g. "Application Begin" → application_begin)
      6. Fallback: full text regex agar section nahi mila
    ──────────────────────────────────────────────────────────────────────────
    """

    # ── Date value detection patterns ────────────────────────────────────
    DATE_RE = re.compile(
        r'(\d{1,2}[\/\-]\d{2}[\/\-]\d{4}'                              # DD/MM/YYYY
        r'|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|'
        r'Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|'
        r'Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}'                         # DD Month YYYY
        r'|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|'
        r'Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|'
        r'Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}'                         # Month YYYY
        r'|Before\s+Exam|Available\s+Soon|Notified\s+Soon|'
        r'As\s+Per\s+Schedule|To\s+Be\s+Notified|Will\s+Be\s+Notified)',
        re.I
    )

    # ── Known label → normalized key map ─────────────────────────────────
    LABEL_KEY_MAP = [
        # (regex_for_label, output_key)
        (r'application\s*(?:begin|start|open)',      'application_begin'),
        (r'last\s*date.*apply\s*online',             'last_date_apply_online'),
        (r'last\s*date.*online\s*apply',             'last_date_apply_online'),
        (r'last\s*date.*submit.*online',             'last_date_apply_online'),
        (r'last\s*date.*apply',                      'last_date_apply_online'),
        (r'closing\s*date',                          'last_date_apply_online'),
        (r'last\s*date.*(?:pay|fee)',                'last_date_pay_fee'),
        (r'pay.*exam.*fee.*last',                    'last_date_pay_fee'),
        (r'exam.*fee.*last',                         'last_date_pay_fee'),
        (r'fee.*last\s*date',                        'last_date_pay_fee'),
        (r'correction\s*(?:date|window|last)',       'correction_date'),
        (r'form\s*correction',                       'correction_date'),
        (r'edit.*form',                              'correction_date'),
        (r'exam\s*date',                             'exam_date'),
        (r'date\s*of\s*exam',                        'exam_date'),
        (r'written\s*exam',                          'exam_date'),
        (r'stage\s*[12i]+\s*exam',                   'exam_date'),
        (r'admit\s*card\s*(?:available|release)',    'admit_card_available'),
        (r'hall\s*ticket',                           'admit_card_available'),
        (r'call\s*letter',                           'admit_card_available'),
        (r'result\s*(?:date|declared|available|out)','result_date'),
        (r'answer\s*key',                            'answer_key_date'),
        (r'interview\s*(?:date|schedule)',           'interview_date'),
        (r'document\s*verif',                        'dv_date'),
        (r'skill\s*test',                            'skill_test_date'),
        (r'last\s*date',                             'last_date_apply_online'),  # generic fallback
    ]

    def _label_to_key(label_raw):
        """Label string → snake_case key, normalized if known."""
        low = label_raw.lower().strip()
        # Try known map first (longest match wins)
        for pat, key in LABEL_KEY_MAP:
            if re.search(pat, low):
                return key
        # Fallback: raw label → snake_case
        key = re.sub(r'[^a-z0-9]+', '_', low).strip('_')
        return key[:40] if key else None

    def _extract_date_value(raw_val):
        """Raw value string se date/text extract karo."""
        # "upto HH PM/AM" suffix strip
        raw_val = re.sub(r'\s*upto\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)\b.*', '', raw_val, flags=re.I)
        raw_val = re.sub(r'\s*by\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)\b.*', '', raw_val, flags=re.I)
        raw_val = raw_val.strip()
        m = DATE_RE.search(raw_val)
        if m:
            return clean(m.group(0))
        # If short meaningful text (Before Exam, etc.) → keep as-is
        val = clean(raw_val)
        if val and len(val) < 80 and not re.search(r'sarkari|result\.com|www\b', val, re.I):
            return val
        return ""

    # ── Step 1: Isolate Important Dates section ───────────────────────────
    SECTION_END_ANCHORS = (
        r'Application\s*Fee|Age\s*Limit|Vacancy\s*Details|Eligibility|'
        r'How\s*to\s*(?:Fill|Apply)|Important\s*Links|Selection\s*Process|'
        r'Physical\s*Eligib|Salary|Pay\s*Scale'
    )
    m_sec = re.search(
        r'Important\s*Dates?\s*[:\-]?\s*\n?(.*?)(?=' + SECTION_END_ANCHORS + r')',
        text, re.I | re.S
    )
    section_text = m_sec.group(1) if m_sec else text

    # Clean branding
    section_text = re.sub(r'WWW\.SARKARIRESULT\.COM[^\n]*', '', section_text, flags=re.I)
    section_text = re.sub(r'Sarkari\s*Result[^\n]*', '', section_text, flags=re.I)

    structured = {}
    seen_keys = set()

    # ── Step 2: Parse line-by-line Label : Value pairs ────────────────────
    for line in section_text.split('\n'):
        line = line.strip()
        if not line or len(line) < 5:
            continue
        # Match "Label : Value" or "Label - Value" pattern
        m = re.match(r'^([A-Za-z][^:\-\n]{3,80}?)\s*[:\-]\s*(.{3,200})$', line)
        if not m:
            continue
        label_raw = m.group(1).strip()
        val_raw   = m.group(2).strip()

        # Skip noise labels
        if re.search(r'sarkari|result\.com|whatsapp|telegram|click\s*here', label_raw, re.I):
            continue
        # Skip non-date value lines (long paragraphs, branding)
        if len(val_raw) > 250:
            continue

        date_val = _extract_date_value(val_raw)
        if not date_val:
            continue

        key = _label_to_key(label_raw)
        if not key:
            continue

        # For normalized keys: first occurrence wins
        if key in seen_keys and key in [k for _, k in LABEL_KEY_MAP]:
            # But raw dynamic keys can overwrite with same label
            continue
        seen_keys.add(key)

        # If key already exists (e.g. two "last date" variations), keep first
        if key not in structured:
            structured[key] = date_val

    # ── Step 3: Fallback regex for stubborn formats ───────────────────────
    if not structured.get('application_begin'):
        m = re.search(r'Application\s*(?:Begin|Start)\s*[:\-]?\s*(.{3,80}?)(?:\n|$)', section_text, re.I)
        if m:
            v = _extract_date_value(m.group(1))
            if v: structured['application_begin'] = v

    if not structured.get('last_date_apply_online'):
        for pat in [r'Last\s*Date[^:\n]{0,40}[:\-]\s*(.{3,80}?)(?:\n|$)']:
            m = re.search(pat, section_text, re.I)
            if m:
                v = _extract_date_value(m.group(1))
                if v:
                    structured['last_date_apply_online'] = v
                    break

    if not structured.get('exam_date'):
        m = re.search(r'Exam\s*Date\s*[:\-]?\s*(.{3,80}?)(?:\n|$)', section_text, re.I)
        if m:
            v = _extract_date_value(m.group(1))
            if v: structured['exam_date'] = v

    return structured


def sr_extract_application_fee_structured(text):
    """
    Application Fee section se structured dict extract karo.

    ── Dynamic approach ──────────────────────────────────────────────────────
    Koi hardcoded category labels nahi.
    Strategy:
      1. Fee section isolate karo
      2. Har "Label : Amount" line dynamically parse karo
      3. Amount pattern detect karo (Rs.550/-, 550/-, Free, Nil etc.)
      4. Label → snake_case key (category name preserve karo)
      5. Payment mode detect karo
      6. "No Fee" case handle karo
    ──────────────────────────────────────────────────────────────────────────
    """
    SECTION_END_ANCHORS = (
        r'Important\s*Dates|Age\s*Limit|Vacancy\s*Details|Eligibility|'
        r'How\s*to\s*(?:Fill|Apply)|Selection\s*Process|Physical\s*Eligib'
    )

    # Isolate fee section
    fee_m = re.search(
        r'Application\s*Fee\s*[:\-]?\s*\n?(.*?)(?=' + SECTION_END_ANCHORS + r')',
        text, re.I | re.S
    )
    if not fee_m:
        # Fallback: grab raw fee text
        raw = sr_extract_application_fee(text)
        return {"raw": raw} if raw else {}

    fee_text = fee_m.group(1)
    fee_text = re.sub(r'WWW\.SARKARIRESULT\.COM[^\n]*', '', fee_text, flags=re.I)
    fee_text = re.sub(r'Sarkari\s*Result[^\n]*', '', fee_text, flags=re.I)

    structured = {}

    # ── Amount detection ──────────────────────────────────────────────────
    AMOUNT_RE = re.compile(
        r'(?:Rs\.?\s*|₹\s*)?\d[\d,\.]*\s*(?:/\-|/-|Rs|₹)?'    # Numeric fee
        r'|Free\s*of\s*Cost|No\s*Fee|Nil|Zero',                  # Free cases
        re.I
    )

    def _extract_amount(val_raw):
        m = AMOUNT_RE.search(val_raw)
        return clean(m.group(0)) if m else ""

    # ── Skip patterns ─────────────────────────────────────────────────────
    NOISE_LABELS = re.compile(
        r'sarkari|result\.com|whatsapp|telegram|android|apple|'
        r'click\s*here|join\s*now|download',
        re.I
    )
    PAYMENT_MODE_RE = re.compile(
        r'(?:pay(?:ment)?\s*(?:mode|through|via|by|using)|'
        r'fee\s*mode|mode\s*of\s*payment)',
        re.I
    )

    # ── Line-by-line dynamic parse ────────────────────────────────────────
    for line in fee_text.split('\n'):
        line = line.strip()
        if not line or len(line) < 3:
            continue

        # Payment mode line
        if PAYMENT_MODE_RE.search(line):
            m = re.match(r'^[^:\-\n]{3,60}[:\-]\s*(.{5,300})$', line)
            if m:
                structured['payment_mode'] = clean(m.group(1))[:250]
            else:
                # Entire line as payment mode description
                val = re.sub(r'^(?:pay(?:ment)?\s*(?:mode|through|via|by)|fee\s*mode)\s*[:\-]?\s*', '', line, flags=re.I)
                if val:
                    structured['payment_mode'] = clean(val)[:250]
            continue

        # No fee
        if re.search(r'\bno\s*(?:exam|application)?\s*fee\b|fee\s*(?:is\s*)?nil|free\s*of\s*cost', line, re.I):
            structured['fee_note'] = 'No Application Fee'
            continue

        # Label : Amount line
        m = re.match(r'^([A-Za-z(][^:\n]{2,60}?)\s*[:\-]\s*(.{2,100})$', line)
        if not m:
            continue
        label_raw = m.group(1).strip()
        val_raw   = m.group(2).strip()

        if NOISE_LABELS.search(label_raw):
            continue

        amount = _extract_amount(val_raw)
        if not amount:
            continue

        # Key: snake_case from label, preserve category name
        key = re.sub(r'[^a-z0-9]+', '_', label_raw.lower()).strip('_')
        key = key[:40]
        if key and key not in structured:
            structured[key] = amount

    # ── Fallback: bulk scan for fee lines if nothing found ────────────────
    if not any(k for k in structured if k not in ('payment_mode', 'fee_note')):
        # Scan all "Category : Rs.XXX" style lines anywhere in fee_text
        for m in re.finditer(
            r'([A-Za-z(][^:\n]{2,50}?)\s*[:\-]\s*((?:Rs\.?\s*)?\d[\d,\.]*\s*(?:/\-|₹)?)',
            fee_text, re.I
        ):
            label_raw = m.group(1).strip()
            amount    = clean(m.group(2))
            if NOISE_LABELS.search(label_raw):
                continue
            key = re.sub(r'[^a-z0-9]+', '_', label_raw.lower()).strip('_')[:40]
            if key and key not in structured:
                structured[key] = amount

    if not structured:
        structured['raw'] = clean(fee_text)[:500]

    return structured


def sr_extract_age_limit_structured(text):
    """
    Age Limit section se structured dict extract karo.

    ── Universal Dynamic Approach ────────────────────────────────────────────
    SR pages pe age limit BAHUT alag-alag formats mein aati hai:
      Format A: "Minimum Age : 18 Years / Maximum Age : 25 Years"
      Format B: "Age Limit : 18 to 25 Years (relaxation as per rules)"
      Format C: "Age : 18-30 Years"   (compact)
      Format D: "01/2027 Batch Age Limit : 01/12/2004 – 31/05/2009"  (DOB range)
      Format E: "Born between 01/01/1999 to 31/12/2006"
      Format F: "Upper Age : 30 Years"
      Format G: Multi-category "Gen: 35 Yrs | OBC: 38 Yrs | SC/ST: 40 Yrs"
      Format H: "As per Govt Rules" / "No Age Limit"

    Strategy:
      1. Section isolate karo
      2. Har line dynamically parse karo — Label : Value
      3. Age value detect: "XX Years", DOB range, text values
      4. Label → normalized key OR snake_case preserve
      5. Category-wise relaxation table bhi capture karo
    ──────────────────────────────────────────────────────────────────────────
    """
    SECTION_END_ANCHORS = (
        r'Vacancy\s*Details|Eligibility|How\s*to\s*(?:Fill|Apply)|'
        r'Important\s*Links|Physical\s*Eligib|Selection\s*Process|'
        r'Salary|Pay\s*Scale|Telegram|WhatsApp|Instagram|Join\s*Us|'
        r'Short\s*Details|Short\s*Information|Name\s*of\s*Post'
    )

    # Isolate age section
    m_sec = re.search(
        r'Age\s*Limit[^\n]{0,80}\n?(.*?)(?=' + SECTION_END_ANCHORS + r')',
        text, re.I | re.S
    )
    if not m_sec:
        # Fallback: grab raw age text
        raw = sr_extract_age_limit(text)
        if not raw:
            return {}
        age_section = raw
    else:
        age_section = m_sec.group(1)
        # Section bahut bada hai toh galat capture hua — 500 chars limit
        if len(age_section) > 500:
            age_section = age_section[:500]

    # Clean branding + social noise
    age_section = re.sub(r'WWW\.SARKARIRESULT\.COM[^\n]*', '', age_section, flags=re.I)
    age_section = re.sub(r'Sarkari\s*Result[^\n]*', '', age_section, flags=re.I)
    age_section = re.sub(r'(?:Telegram|WhatsApp|Instagram|Twitter|Facebook|Join\s*Us|Follow)[^\n]*', '', age_section, flags=re.I)
    age_section = re.sub(r'https?://\S+', '', age_section)
    age_section = age_section.strip()

    if not age_section:
        return {}

    structured = {}

    # ── Value detectors ───────────────────────────────────────────────────

    # Format A/B/C/F: "XX Years" style
    AGE_YEARS_RE = re.compile(
        r'(\d{1,2})\s*(?:years?|yrs?)\b', re.I
    )
    # Format: "18 to 25 Years" → (18, 25)
    AGE_RANGE_RE = re.compile(
        r'(\d{1,2})\s*(?:to|[-–])\s*(\d{1,2})\s*(?:years?|yrs?)\b', re.I
    )
    # Format D/E: DOB range "DD/MM/YYYY – DD/MM/YYYY"
    DOB_RANGE_RE = re.compile(
        r'(\d{2}[\/\-]\d{2}[\/\-]\d{4})\s*[–\-—to]+\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})'
    )
    # "as on date" reference
    AS_ON_RE = re.compile(
        r'(?:as\s*on|on\s*date|as\s*on\s*date)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
        re.I
    )
    # "born between" format
    BORN_RE = re.compile(
        r'born\s*(?:between|from|after|before)\s*(.{10,80}?)(?:\n|$)', re.I
    )
    # Category-wise relaxation inline e.g. "OBC : 3 Years | SC/ST : 5 Years"
    CAT_RELAX_RE = re.compile(
        r'(OBC|SC[\s/]*ST|SC|ST|EWS|PwD|Ex[\s-]*Servicemen?|PWD|Divyang)'
        r'\s*[:\-]?\s*(\d+)\s*(?:years?|yrs?)\s*(?:relaxation)?',
        re.I
    )
    # Text values: "As per Govt Rules", "No Age Limit" etc.
    TEXT_VAL_RE = re.compile(
        r'(As\s*per\s*(?:Govt\.?\s*)?Rules?|No\s*Age\s*Limit|'
        r'As\s*per\s*notification|Refer\s*notification)',
        re.I
    )

    # ── Label → normalized key map ────────────────────────────────────────
    LABEL_KEY_MAP = [
        (r'minimum\s*age',           'minimum_age'),
        (r'\bmin\b.*age',            'minimum_age'),
        (r'lower\s*age',             'minimum_age'),
        (r'maximum\s*age',           'maximum_age'),
        (r'\bmax\b.*age',            'maximum_age'),
        (r'upper\s*age',             'maximum_age'),
        (r'age\s*relaxation',        'age_relaxation'),
        (r'relaxation',              'age_relaxation'),
        (r'as\s*on\s*date',          'as_on_date'),
        (r'born\s*between',          'dob_range'),
        (r'batch.*age\s*limit',      'batch_dob'),   # Navy-style
        (r'age\s*limit',             'age_limit'),   # generic
        (r'\bage\b',                 'age_limit'),
    ]

    def _label_to_key(label_raw):
        low = label_raw.lower().strip()
        for pat, key in LABEL_KEY_MAP:
            if re.search(pat, low):
                return key
        key = re.sub(r'[^a-z0-9]+', '_', low).strip('_')
        return key[:40] if key else None

    def _extract_age_value(val_raw, label_raw=""):
        """Val string se age value dict extract karo."""
        result = {}
        val_low = val_raw.lower()

        # DOB range first (highest priority for Navy/batch style)
        dob = DOB_RANGE_RE.search(val_raw)
        if dob:
            result['dob_from'] = dob.group(1)
            result['dob_to']   = dob.group(2)
            return result

        # "Born between" phrase
        born = BORN_RE.search(val_raw)
        if born:
            dob2 = DOB_RANGE_RE.search(born.group(1))
            if dob2:
                result['dob_from'] = dob2.group(1)
                result['dob_to']   = dob2.group(2)
                return result

        # Range "18 to 25 Years"
        rng = AGE_RANGE_RE.search(val_raw)
        if rng:
            result['minimum_age'] = rng.group(1) + " Years"
            result['maximum_age'] = rng.group(2) + " Years"
            return result

        # Single age value
        yr = AGE_YEARS_RE.search(val_raw)
        if yr:
            result['value'] = yr.group(1) + " Years"
            return result

        # Text value
        tv = TEXT_VAL_RE.search(val_raw)
        if tv:
            result['value'] = clean(tv.group(0))
            return result

        # As-on date (reference)
        ao = AS_ON_RE.search(val_raw)
        if ao:
            result['as_on_date'] = ao.group(1)
            return result

        return {}

    # ── Line-by-line parse ────────────────────────────────────────────────
    NOISE_RE = re.compile(r'sarkari|result\.com|click\s*here|whatsapp|telegram', re.I)

    # Also scan full section for as_on_date
    ao_m = AS_ON_RE.search(age_section)
    if ao_m:
        structured['as_on_date'] = ao_m.group(1)

    for line in age_section.split('\n'):
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if NOISE_RE.search(line):
            continue

        # Batch-wise DOB line: "01/2027 Batch Age Limit : 01/12/2004 – 31/05/2009"
        batch_m = re.match(
            r'^(.{3,60}?Batch[^:\n]{0,40})\s*[:\-]\s*'
            r'(\d{2}[\/\-]\d{2}[\/\-]\d{4})\s*[–\-—]+\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
            line, re.I
        )
        if batch_m:
            batch_label = re.sub(r'\s+', '_', batch_m.group(1).strip().lower())[:40]
            if 'batch_wise_dob' not in structured:
                structured['batch_wise_dob'] = {}
            structured['batch_wise_dob'][batch_label] = {
                'dob_from': batch_m.group(2),
                'dob_to':   batch_m.group(3)
            }
            continue

        # Category-wise relaxation inline "OBC : 3 Years relaxation"
        for cat_m in CAT_RELAX_RE.finditer(line):
            cat  = cat_m.group(1).upper().replace(' ', '_').replace('/', '_')
            yrs  = cat_m.group(2) + " Years"
            if 'category_relaxation' not in structured:
                structured['category_relaxation'] = {}
            structured['category_relaxation'][cat] = yrs

        # Standard Label : Value line
        m = re.match(r'^([A-Za-z(][^:\n]{2,80}?)\s*[:\-]\s*(.{2,200})$', line)
        if not m:
            # Check for standalone range "18 to 25 Years" or DOB range on a line
            dob = DOB_RANGE_RE.search(line)
            if dob and 'dob_from' not in structured and 'batch_wise_dob' not in structured:
                structured['dob_from'] = dob.group(1)
                structured['dob_to']   = dob.group(2)
            rng = AGE_RANGE_RE.search(line)
            if rng and 'minimum_age' not in structured:
                structured['minimum_age'] = rng.group(1) + " Years"
                structured['maximum_age'] = rng.group(2) + " Years"
            continue

        label_raw = m.group(1).strip()
        val_raw   = m.group(2).strip()

        if NOISE_RE.search(label_raw):
            continue

        age_val = _extract_age_value(val_raw, label_raw)
        if not age_val:
            continue

        key = _label_to_key(label_raw)
        if not key:
            continue

        # Merge extracted values into structured
        if key == 'batch_dob':
            # Already handled by batch_m above, skip
            continue
        elif key in ('minimum_age', 'maximum_age', 'age_relaxation', 'as_on_date'):
            # Single-value normalized keys
            val = age_val.get('value') or age_val.get('minimum_age') or age_val.get('dob_from', '')
            if val and key not in structured:
                structured[key] = val
            # If range detected
            if 'minimum_age' in age_val and 'minimum_age' not in structured:
                structured['minimum_age'] = age_val['minimum_age']
            if 'maximum_age' in age_val and 'maximum_age' not in structured:
                structured['maximum_age'] = age_val['maximum_age']
        elif key == 'dob_range':
            # DOB range — store both from and to
            if 'dob_from' in age_val and 'dob_from' not in structured:
                structured['dob_from'] = age_val['dob_from']
                structured['dob_to']   = age_val.get('dob_to', '')
            elif 'value' in age_val and 'dob_from' not in structured:
                structured['dob_from'] = age_val['value']
        elif key == 'age_limit':
            # Could be range or single
            if 'minimum_age' in age_val and 'minimum_age' not in structured:
                structured['minimum_age'] = age_val['minimum_age']
            if 'maximum_age' in age_val and 'maximum_age' not in structured:
                structured['maximum_age'] = age_val['maximum_age']
            if 'value' in age_val and 'maximum_age' not in structured:
                structured['maximum_age'] = age_val['value']
            if 'dob_from' in age_val and 'dob_from' not in structured:
                structured['dob_from'] = age_val['dob_from']
                structured['dob_to']   = age_val.get('dob_to', '')
        else:
            # Dynamic key
            if age_val and key not in structured:
                if 'value' in age_val:
                    structured[key] = age_val['value']
                elif 'minimum_age' in age_val:
                    structured[key] = f"{age_val['minimum_age']} – {age_val.get('maximum_age','')}"
                elif 'dob_from' in age_val:
                    structured[key] = {'dob_from': age_val['dob_from'], 'dob_to': age_val.get('dob_to','')}

    # ── Fallback: scan full section for any missed age values ─────────────
    if not any(k for k in structured if k not in ('as_on_date', 'category_relaxation')):
        # Try range
        rng = AGE_RANGE_RE.search(age_section)
        if rng:
            structured['minimum_age'] = rng.group(1) + " Years"
            structured['maximum_age'] = rng.group(2) + " Years"
        else:
            # Single max age
            yr = AGE_YEARS_RE.search(age_section)
            if yr:
                structured['maximum_age'] = yr.group(1) + " Years"
        # DOB range fallback
        dob = DOB_RANGE_RE.search(age_section)
        if dob and 'batch_wise_dob' not in structured:
            structured.setdefault('dob_from', dob.group(1))
            structured.setdefault('dob_to',   dob.group(2))

    # ── Always add raw details for reference ──────────────────────────────
    if structured:
        raw_clean = re.sub(r'\s+', ' ', age_section).strip()
        structured['details'] = raw_clean[:600]
    else:
        raw_clean = re.sub(r'\s+', ' ', age_section).strip()
        # raw sirf tabhi store karo jab actual age content ho
        if raw_clean and re.search(r'\d{2}\s*(?:years?|yrs?)|dob|born|age', raw_clean, re.I):
            structured['raw'] = raw_clean[:600]

    return structured


def sr_age_fallback_from_faq_tables(faq_list, tables_list, text):
    """
    Fallback: age_limit empty ho toh FAQ + table_name se extract karo.

    SR pages pe FAQ mein question/answer REVERSED hote hain:
      { "question": "18 Years",  "answer": "Minimum Age :" }
      { "question": "28 Male",   "answer": "Maximum Age :" }

    Table names mein bhi age info hoti hai:
      "Age Limit as on 07/07/2026 Minimum Age : Maximum Age :"

    Strategy:
      1. FAQ scan karo — reversed Q/A se min/max age nikalo
      2. Table names scan karo — age heading se parse karo
      3. Text se direct regex fallback
    """
    result = {}

    # ── 1. FAQ reversed-format scan ─────────────────────────
    LABEL_RE = re.compile(
        r'(minimum|min|lower)\s*age|'
        r'(maximum|max|upper)\s*age|'
        r'age\s*relaxation|'
        r'as\s*on\s*date',
        re.I
    )
    AGE_VAL_RE = re.compile(r'(\d{1,2})\s*(?:years?|yrs?)', re.I)
    DATE_VAL_RE = re.compile(r'\d{2}[\/\-]\d{2}[\/\-]\d{4}')

    for item in faq_list:
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()

        # Reversed format: answer = label, question = value
        if LABEL_RE.search(a) and not LABEL_RE.search(q):
            label_text = a.lower()
            val_text   = q

            if re.search(r'minimum|min|lower', label_text) and not result.get('minimum_age'):
                m = AGE_VAL_RE.search(val_text)
                if m:
                    result['minimum_age'] = m.group(1) + " Years"
                else:
                    result['minimum_age'] = val_text[:30]

            elif re.search(r'maximum|max|upper', label_text) and not result.get('maximum_age'):
                m = AGE_VAL_RE.search(val_text)
                if m:
                    result['maximum_age'] = m.group(1) + " Years"
                else:
                    result['maximum_age'] = val_text[:30]

            elif re.search(r'relaxation', label_text) and not result.get('age_relaxation'):
                result['age_relaxation'] = val_text[:80]

            elif re.search(r'as\s*on\s*date', label_text) and not result.get('as_on_date'):
                d = DATE_VAL_RE.search(val_text)
                if d:
                    result['as_on_date'] = d.group(0)

        # Normal format: question = label, answer = value
        elif LABEL_RE.search(q) and not LABEL_RE.search(a):
            label_text = q.lower()
            val_text   = a

            if re.search(r'minimum|min|lower', label_text) and not result.get('minimum_age'):
                m = AGE_VAL_RE.search(val_text)
                if m:
                    result['minimum_age'] = m.group(1) + " Years"

            elif re.search(r'maximum|max|upper', label_text) and not result.get('maximum_age'):
                m = AGE_VAL_RE.search(val_text)
                if m:
                    result['maximum_age'] = m.group(1) + " Years"
                else:
                    result['maximum_age'] = val_text[:30]

            elif re.search(r'relaxation', label_text) and not result.get('age_relaxation'):
                result['age_relaxation'] = val_text[:80]

    # ── 2. Table name scan ───────────────────────────────────
    # "Age Limit as on 07/07/2026 Minimum Age : Maximum Age :"
    for tbl in tables_list:
        tname = tbl.get("table_name", "")
        if not re.search(r'age\s*limit', tname, re.I):
            continue

        # as_on_date from table name
        if not result.get('as_on_date'):
            d = DATE_VAL_RE.search(tname)
            if d:
                result['as_on_date'] = d.group(0)

        # Scan table rows for age data
        for row in tbl.get("rows", []):
            if not isinstance(row, list) or len(row) < 2:
                continue
            label_raw = str(row[0]).strip().lower()
            val_raw   = str(row[1]).strip()

            if re.search(r'minimum|min\s*age', label_raw) and not result.get('minimum_age'):
                m = AGE_VAL_RE.search(val_raw)
                if m:
                    result['minimum_age'] = m.group(1) + " Years"

            elif re.search(r'maximum|max\s*age', label_raw) and not result.get('maximum_age'):
                m = AGE_VAL_RE.search(val_raw)
                if m:
                    result['maximum_age'] = m.group(1) + " Years"
                elif val_raw:
                    result['maximum_age'] = val_raw[:30]

            elif re.search(r'relaxation', label_raw) and not result.get('age_relaxation'):
                result['age_relaxation'] = val_raw[:80]

    # ── 3. Text direct regex fallback ───────────────────────
    if not result.get('minimum_age'):
        m = re.search(r'Minimum\s*Age\s*[:\-]?\s*(\d{1,2})\s*(?:Years?|Yrs?)', text, re.I)
        if m:
            result['minimum_age'] = m.group(1) + " Years"

    if not result.get('maximum_age'):
        m = re.search(r'Maximum\s*Age\s*[:\-]?\s*(\d{1,2}[^\n]{0,20}?)(?:\n|$)', text, re.I)
        if m:
            val = m.group(1).strip()
            age_m = AGE_VAL_RE.search(val)
            result['maximum_age'] = (age_m.group(1) + " Years") if age_m else val[:30]

    return result


def sr_extract_vacancy_details_structured(soup, text):
    """
    Vacancy Details table + total post extract karo.

    ── Dynamic approach ──────────────────────────────────────────────────────
    SR pages pe vacancy tables kaafi varied hoti hain:
      - 2-col: Post Name | Total
      - 3-col: Post Name | Eligibility | Total
      - Multi-col: Post | Gen | OBC | SC | ST | EWS | Total
      - 2-col K:V style: "Post Name : Clerk | Total : 500"
      - No header row — just data rows
      - Multiple vacancy tables on one page (different posts)

    Strategy:
      1. HTML tables se vacancy table identify karo (name + heuristic)
      2. Header row dynamically detect karo (first/second row)
      3. All columns capture karo → normalized key names
      4. K:V 2-col tables bhi handle karo
      5. Fallback: text regex se total + post names
    ──────────────────────────────────────────────────────────────────────────
    """
    total = sr_extract_total_post(text)
    tables = sr_extract_tables(soup)
    post_wise = []
    seen_entries = set()

    # ── Column header normalizer ──────────────────────────────────────────
    HEADER_KEY_MAP = [
        (r'post\s*name|designation|name\s*of\s*post|post',   'post_name'),
        (r'total|vacancies|vacancy|no\.?\s*of\s*post',        'total_post'),
        (r'eligib|qualification|edu',                          'eligibility'),
        (r'gen(?:eral)?(?:\s*/\s*ur)?|ur\b',                  'general_ur'),
        (r'\bobc\b',                                           'obc'),
        (r'\bews\b',                                           'ews'),
        (r'\bsc\b(?!\s*/\s*st)',                               'sc'),
        (r'\bst\b',                                            'st'),
        (r'sc\s*/\s*st',                                       'sc_st'),
        (r'ex[\s-]*serv|exsm',                                 'ex_servicemen'),
        (r'pwd|divyang|ph\b',                                  'pwd'),
        (r'female|women',                                      'female'),
        (r'male',                                              'male'),
        (r'salary|pay\s*scale|pay\s*level',                    'salary'),
        (r'category',                                          'category'),
        (r'sr\.?\s*no|s\.?\s*no',                             'sr_no'),
        (r'age\s*limit',                                       'age_limit'),
    ]

    def _col_to_key(header_text):
        low = header_text.lower().strip()
        for pat, key in HEADER_KEY_MAP:
            if re.search(pat, low):
                return key
        # Fallback: snake_case
        key = re.sub(r'[^a-z0-9]+', '_', low).strip('_')
        return key[:30] if key else None

    # Noise rows to skip — dates, timestamps, branding etc.
    NOISE_ROW_RE = re.compile(
        r'sarkari\s*result|total\s*:\s*\d+\s*post|grand\s*total|'
        r'click\s*here|apply\s*online|official\s*website|whatsapp|telegram',
        re.I
    )

    # Date/timestamp pattern — standalone date strings ko post_name mein accept nahi karte
    DATE_NOISE_RE = re.compile(
        r'^\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}'
        r'|^\d{4}-\d{2}-\d{2}$'
        r'|^\d{1,2}/\d{1,2}/\d{4}$'
        r'|^\d{1,2}:\d{2}\s*(?:AM|PM)$'
        r'|.*\d{1,2}:\d{2}\s*(?:AM|PM)',  # "07:55 PM" wale timestamp rows
        re.I
    )

    def _is_valid_post_name(val: str) -> bool:
        val = val.strip()
        if not val or len(val) < 2:
            return False
        if DATE_NOISE_RE.search(val):
            return False
        if re.match(r'^\d+$', val):
            return False
        return True

    def _clean_eligibility(val: str) -> str:
        val = val.strip()
        val = re.sub(r'\n{2,}', ' | ', val)
        val = re.sub(r'\n', ' ', val)
        val = re.sub(r'\s{2,}', ' ', val)
        return val[:500]

    # ── Vacancy table identifier ──────────────────────────────────────────
    VACANCY_TABLE_KEYWORDS = [
        "vacancy", "post", "recruitment", "total", "eligib",
        "category wise", "district wise", "department wise",
    ]
    VACANCY_TABLE_NAME_RE = re.compile(
        r'vacancy\s*detail|post\s*detail|post\s*name|post\s*wise|'
        r'category\s*wise|total\s*vacancy|total\s*post|recruitment\s*detail|'
        r'general\s*information|district\s*wise',
        re.I
    )

    def _is_vacancy_table(tbl):
        tname = tbl.get('table_name', '').lower()
        rows  = tbl.get('rows', [])
        if VACANCY_TABLE_NAME_RE.search(tname):
            return True
        if not rows:
            return False
        # Check first 2 rows for vacancy keywords
        check_text = ' '.join(' '.join(r) for r in rows[:2]).lower()
        return any(kw in check_text for kw in VACANCY_TABLE_KEYWORDS)

    def _parse_table_rows(rows):
        """Rows se entries extract karo — header auto-detect."""
        if not rows:
            return []
        entries = []

        # Try to detect header row (first or second row)
        header = None
        data_start = 0

        # Check if first row looks like headers (no numeric values, all short strings)
        first_row = rows[0]
        first_joined = ' '.join(first_row).lower()
        is_header = (
            any(re.search(pat, first_joined) for pat, _ in HEADER_KEY_MAP[:5])
            or all(not re.search(r'\d{3,}', c) for c in first_row)
               and len(first_row) >= 2
               and all(len(c) < 60 for c in first_row)
        )
        if is_header:
            header = [_col_to_key(c) for c in first_row]
            data_start = 1
        # Second row check
        elif len(rows) > 1:
            sec_joined = ' '.join(rows[1]).lower()
            if any(re.search(pat, sec_joined) for pat, _ in HEADER_KEY_MAP[:5]):
                header = [_col_to_key(c) for c in rows[1]]
                data_start = 2

        for row in rows[data_start:]:
            if not row or len(row) < 1:
                continue
            row_text = ' '.join(row)
            if NOISE_ROW_RE.search(row_text):
                continue
            if all(len(c) < 2 for c in row):
                continue

            if header and len(header) == len(row):
                # Header-aligned entry
                entry = {}
                for i, key in enumerate(header):
                    val = clean(row[i])
                    if not val or not key:
                        continue
                    # Eligibility: clean + cap length
                    if key == 'eligibility':
                        val = _clean_eligibility(val)
                    entry[key] = val
                # post_name date/timestamp noise filter
                if 'post_name' in entry and not _is_valid_post_name(entry['post_name']):
                    continue
                if entry and ('post_name' in entry or 'total_post' in entry):
                    entry_key = entry.get('post_name', '') + entry.get('total_post', '')
                    if entry_key not in seen_entries:
                        seen_entries.add(entry_key)
                        entries.append(entry)
            elif len(row) == 2:
                # K:V style row  e.g. ["Post Name", "Clerk Grade II"]
                key = _col_to_key(row[0])
                val = clean(row[1])
                if key and val:
                    if key == 'post_name' and not _is_valid_post_name(val):
                        continue
                    # Build or extend last entry
                    if not entries or any(key in e for e in entries[-1:]):
                        entries.append({})
                    entries[-1][key] = _clean_eligibility(val) if key == 'eligibility' else val
            else:
                # No header — col_0, col_1 ...
                entry = {}
                for i, v in enumerate(row):
                    v = clean(v)
                    if v:
                        # Try to guess key from value content
                        if i == 0:
                            if not _is_valid_post_name(v):
                                break  # Skip entire row if col_0 is a date
                            # Long org names / recruitment titles → heading, not post name
                            if len(v) > 80:
                                break
                            _org_ind = [
                                "commission", "corporation", "department",
                                "ministry", "institute", "university",
                                "board", "council", "authority",
                                "recruitment 20", "advt no", "advertisement no",
                                "notification 20",
                            ]
                            if any(ind in v.lower() for ind in _org_ind):
                                break
                            entry['post_name'] = v
                        elif re.match(r'^\d+$', v):
                            entry.setdefault('total_post', v)
                        else:
                            entry[f'col_{i}'] = v
                if entry:
                    entry_key = str(entry)
                    if entry_key not in seen_entries:
                        seen_entries.add(entry_key)
                        entries.append(entry)

        return entries

    # ── Process all vacancy tables ────────────────────────────────────────
    for tbl in tables:
        if not _is_vacancy_table(tbl):
            continue
        rows = tbl.get('rows', [])
        entries = _parse_table_rows(rows)
        post_wise.extend(entries)

    # ── Text fallback if no structured entries ────────────────────────────
    if not post_wise and total:
        # At minimum record total
        post_wise = []

    return {
        'total_post': total,
        'post_wise':  post_wise,
    }


def sr_extract_how_to_apply(text):
    """
    How to Fill / How to Apply section extract karo as list of steps.
    Handles sarkariresult.com pattern: heading + bullet lines.
    """
    HOW_PATTERNS = [
        # "How to Fill Navy Agniveer..." heading ke baad ka content
        r'How\s*to\s*(?:Fill|Apply)[^\n]{0,100}\n((?:.|\n){50,3000}?)'
        r'(?:Apply\s*Online|Important\s*Links|Some\s*Useful|Sarkari\s*Result\s*Android|'
        r'Interested\s*Candidates|Note\s*:|\Z)',
        r'(?:Steps?\s*to\s*Apply|Application\s*Process)[^\n]*((?:.|\n){50,1500}?)'
        r'(?:Apply\s*Online|Important\s*Links|Note\s*:|$)',
    ]
    # Noise lines to skip entirely
    SKIP_PATTERNS = re.compile(
        r'(Sarkari\s*Result|WWW\.SARKARIRESULT\.COM|sarkariresult\.com|'
        r'always\s*visit\s*sarkari|official\s*website\s*of\s*sarkari|'
        r'download\s*the\s*sarkari|mobile\s*app\s*from|since\s*201\d|'
        r'for\s*the\s*latest\s*updates)',
        re.I
    )
    for pat in HOW_PATTERNS:
        m = re.search(pat, text, re.I | re.S)
        if not m:
            continue
        raw = m.group(1)
        raw = re.sub(r'https?://[^\s]+', '', raw)
        # Line-by-line filter
        lines = []
        for line in raw.split('\n'):
            line = clean(line)
            if not line or len(line) < 10:
                continue
            if SKIP_PATTERNS.search(line):
                continue
            lines.append(line)
        if lines:
            return lines[:15]
    return []


def sr_extract_useful_links_structured(soup):
    """
    Useful links ko structured form mein extract karo.
    Reference format mein separate keys: apply_online, notification,
    admit_card, result, answer_key, syllabus, date_extended, etc.
    Existing sr_extract_useful_links() se data leke structured bana do.
    """
    raw_links = sr_extract_useful_links(soup)

    KEY_MAP = [
        # (keywords_in_title_lower, output_key)
        (["apply online", "apply now", "register", "registration", "online form", "login", "apply here"], "apply_online"),
        (["notification", "advertisement", "advt", "official notice", "download notification"], "notification"),
        (["admit card", "hall ticket", "call letter"], "admit_card"),
        (["result", "merit list", "final result", "score card", "mark sheet"], "result"),
        (["answer key", "response sheet", "omr sheet", "provisional key"], "answer_key"),
        (["syllabus", "exam pattern", "exam syllabus"], "syllabus"),
        (["date extended", "extension", "revised date", "new date"], "date_extended"),
        (["cutoff", "cut off", "cut-off"], "cutoff"),
        (["official website", "official site"], "official_website"),
        (["download", "pdf"], "document"),
    ]

    structured = {}

    def _get_url(link_val):
        if isinstance(link_val, list):
            return link_val[0] if link_val else ""
        return link_val or ""

    for item in raw_links:
        title = item.get("title", "").lower()
        url   = _get_url(item.get("links", ""))
        if not url:
            continue

        matched = False
        for keywords, key in KEY_MAP:
            if any(kw in title for kw in keywords):
                if key == "apply_online":
                    # apply_online mein multiple links ho sakti hain
                    if key not in structured:
                        structured[key] = url
                    elif isinstance(structured[key], str):
                        structured[key] = [structured[key], url]
                    elif isinstance(structured[key], list):
                        structured[key].append(url)
                elif key not in structured:
                    structured[key] = url
                matched = True
                break

        if not matched:
            # Generic key bana do
            safe_key = re.sub(r'[^a-z0-9_]', '_', title[:30]).strip('_')
            if safe_key and safe_key not in structured:
                structured[safe_key] = url

    # Full list bhi rakho for completeness
    structured["_all"] = raw_links

    return structured


def sr_extract_faq(soup, text):
    """
    FAQ section extract karo sarkariresult.com pages se.
    Sarkariresult.com pe FAQ ek dedicated div/section mein hoti hai
    jiske andar heading "Frequently Asked Questions" hoti hai aur
    har FAQ ek <b>/<strong> question + plain text answer hota hai.

    Strategies:
      1. JSON-LD FAQPage schema (@type: FAQPage)
      2. HTML: div jisme "frequently asked" text ho, wahan se Q&A pairs
      3. Text regex: "1. Question\n Answer" style numbered FAQ
    Returns: [{"question": ..., "answer": ...}, ...]
    """
    faqs = []
    seen_q = set()

    # Branding / boilerplate patterns to strip from answers
    _BRAND_STRIP = re.compile(
        r'[^\n]*(?:sarkariresult\.com|sarkari\s*result\s*portal|'
        r'since\s*20\d\d|official\s*website\s*of\s*sarkari\s*result)[^\n]*',
        re.I
    )
    # Question noise: pure dates / single words as question = wrong extraction
    _Q_NOISE = re.compile(
        r'^\d{2}[/\-]\d{2}[/\-]\d{4}$|'      # "04/06/2026" pure date
        r'^\d{1,2}\s+\w+\s+\d{4}\.?$|'        # "04 June 2026"
        r'^(?:before exam|as per schedule|not given)$',
        re.I
    )

    def _add(q, a):
        q = clean(q)
        a = clean(a)
        if not q or not a:
            return
        # Skip if question is actually a date/value (reversed extraction)
        if _Q_NOISE.match(q.strip()):
            return
        # Strip SR branding from answer
        a = _BRAND_STRIP.sub('', a).strip()
        a = clean(a)
        if len(q) < 5 or len(a) < 5:
            return
        if q.lower() in seen_q:
            return
        seen_q.add(q.lower())
        faqs.append({"question": q, "answer": a})

    # ── Strategy 1: JSON-LD FAQPage ────────────────────────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json as _json
            ld = _json.loads(script.string or "")
            if isinstance(ld, dict) and ld.get("@type") == "FAQPage":
                for entity in ld.get("mainEntity", []):
                    q_text = entity.get("name", "")
                    a_text = entity.get("acceptedAnswer", {}).get("text", "")
                    _add(q_text, a_text)
        except Exception:
            pass

    if faqs:
        return faqs[:15]

    # ── Strategy 2A: FAQ container — generic detection (no hardcoded ID) ────
    # "Frequently Asked" text wala div/section dhundo. SR theme ID badalta rehta
    # hai isliye hardcode nahi karte.
    sr_faq_div = None
    for div in soup.find_all(["div", "section"]):
        dt = div.get_text(" ", strip=True).lower()
        if ("frequently asked" in dt or "faq" in dt[:200]) and 80 < len(dt) < 25000:
            sr_faq_div = div
            break
    if not sr_faq_div:
        sr_faq_div = soup.find("div", class_=lambda c: c and "gb-container-6da1cb96" in c)
    if sr_faq_div:
        # H5-question + UL/P-answer pattern bhi handle karo
        h5q = sr_faq_div.find_all(["h4", "h5", "h6"])
        if h5q:
            for h in h5q:
                q = clean(h.get_text())
                q = re.sub(r"^\d+\.\s*", "", q)
                if not q or "?" not in q and len(q) < 12:
                    continue
                ans = ""
                nx = h.find_next(["ul", "ol", "p"])
                if nx:
                    ans = clean(nx.get_text())
                if q and ans and len(ans) > 3:
                    faqs.append({"question": q, "answer": ans})
        paras = sr_faq_div.find_all("p")
        i = 0
        while i < len(paras):
            b_tag = paras[i].find(["b", "strong"])
            para_text = clean(paras[i].get_text())
            # Question: bold text ya numbered pattern ("1. Question?")
            is_question = (
                (b_tag and len(b_tag.get_text(strip=True)) > 8)
                or re.match(r'^\d+\.\s+\S', para_text)
            )
            if is_question:
                q = clean(b_tag.get_text() if b_tag else para_text)
                q = re.sub(r'^\d+\.\s*', '', q).strip()  # "1. " prefix hatao
                # Next non-empty para = answer
                a = ""
                j = i + 1
                while j < len(paras):
                    a_candidate = clean(paras[j].get_text())
                    if a_candidate:
                        a = a_candidate
                        i = j + 1
                        break
                    j += 1
                else:
                    i += 1
                _add(q, a)
            else:
                i += 1

    if faqs:
        return faqs[:15]

    # ── Strategy 2C: gb-headline FAQ — h5 = Question, ul/li = Answer ────────
    # SarkariResult pages pe FAQ structure:
    #   <div class="gb-headline ...">
    #     <h5>1. Question text?</h5>
    #     <ul><li>Answer text with <strong>highlighted value</strong>.</li></ul>
    #     <h5>2. Next question?</h5>
    #     <ul><li>Next answer.</li></ul>
    #   </div>
    # Current Strategy 2B galat karta tha: <strong> inside <li> ko question
    # samajhta tha (jo actually answer ka highlighted part hai).

    # Find FAQ container — div with "frequently asked" text
    _faq_block = None
    for _tag in soup.find_all(["div", "section"]):
        _tag_txt = _tag.get_text(" ", strip=True).lower()
        if "frequently asked" in _tag_txt and 50 < len(_tag_txt) < 20000:
            _faq_block = _tag
            break

    if _faq_block:
        # Strategy 2C: h5 (question) followed by ul/li (answer)
        _BRANDING_RE = re.compile(
            r'sarkariresult\.com|sarkari\s*result\s*portal|'
            r'since\s*20\d\d|official\s*website\s*of\s*sarkari',
            re.I
        )
        _NOISE_Q = re.compile(
            r'^\d{2}[/\-]\d{2}[/\-]\d{4}$|'      # pure date "04/06/2026"
            r'^\d{1,2}\s+\w+\s+\d{4}\.?$|'         # "04 June 2026"
            r'^(?:before exam|as per schedule)$',   # generic phrases
            re.I
        )

        _children = list(_faq_block.children)
        i = 0
        _h5_faqs = []
        while i < len(_children):
            child = _children[i]
            if not hasattr(child, 'name'):
                i += 1
                continue

            # h5 = question (may be inside a gb-headline wrapper div)
            q_text = ""
            if child.name == "h5":
                q_text = clean(child.get_text(" "))
            elif child.name == "div":
                inner_h5 = child.find("h5")
                if inner_h5:
                    q_text = clean(inner_h5.get_text(" "))

            if q_text and re.match(r'^\d+\.', q_text):
                # Strip numbering "1. " prefix
                q_text = re.sub(r'^\d+\.\s*', '', q_text).strip()
                # Find next ul/li sibling for answer
                a_text = ""
                j = i + 1
                while j < len(_children):
                    sib = _children[j]
                    if not hasattr(sib, 'name'):
                        j += 1
                        continue
                    if sib.name in ["ul", "ol"]:
                        li = sib.find("li")
                        if li:
                            a_text = clean(li.get_text(" "))
                        i = j + 1
                        break
                    elif sib.name in ["h5", "div"] and (
                        sib.find("h5") or re.match(r'^\d+\.', clean(sib.get_text(" ")))
                    ):
                        # Next question reached without finding answer
                        i = j
                        break
                    j += 1
                else:
                    i = j

                # Skip branding answers
                if a_text and not _BRANDING_RE.search(a_text):
                    if not _NOISE_Q.match(q_text):
                        _h5_faqs.append({"question": q_text, "answer": a_text})
            else:
                i += 1

        if _h5_faqs:
            for item in _h5_faqs:
                _add(item["question"], item["answer"])

    if faqs:
        return faqs[:15]

    # ── Strategy 2B: Any HTML block mentioning "frequently asked" ──────────
    faq_container = None
    for tag in soup.find_all(["div", "section", "ul", "ol"]):
        tag_text = tag.get_text(" ", strip=True).lower()
        if "frequently asked" in tag_text and len(tag_text) < 15000:
            faq_container = tag
            break

    if faq_container:
        # Pattern A: <p><b>Question</b></p> + <p>Answer</p> pairs
        # NOTE: <li><strong>value</strong> rest of answer</li> pattern
        # is NOT used here — strong inside li = highlighted answer value,
        # NOT the question. Strategy 2C above handles h5+ul structure.
        paras = faq_container.find_all("p")
        i = 0
        while i < len(paras) - 1:
            b_tag = paras[i].find(["b", "strong"])
            para_text = clean(paras[i].get_text())
            # Question must look like a question (ends with ? or is numbered)
            is_q_para = (
                b_tag
                and len(b_tag.get_text(strip=True)) > 10
                and (para_text.endswith("?") or re.match(r'^\d+\.', para_text))
            )
            if is_q_para:
                q = clean(b_tag.get_text(" ", strip=True))
                q = re.sub(r'^\d+\.\s*', '', q)
                a = clean(paras[i+1].get_text())
                _add(q, a)
                i += 2
            else:
                i += 1

    if faqs:
        return faqs[:15]

    # ── Strategy 3: Text regex — "N. Question\nAnswer" ────────────────────
    # sarkariresult.com: "1. When did the ... start?\nThe online application..."
    faq_section_m = re.search(
        r'Frequently\s*Asked\s*Questions?(.*?)(?:\Z|Some\s*Useful|Apply\s*Online)',
        text, re.I | re.S
    )
    faq_text = faq_section_m.group(1) if faq_section_m else text

    qa_blocks = re.findall(
        r'\d+\.\s+(.{15,300}?)\s*\n\s*[•\-]?\s*(.{15,600}?)(?=\n\s*\d+\.|\Z)',
        faq_text, re.S
    )
    for q, a in qa_blocks:
        _add(q, a)

    return faqs[:15]


def sr_extract_name_of_post(soup, text):
    """
    Page ka proper 'Name of Post' extract karo — title tag ya h1/h2 se.
    """
    # h1 se try karo pehle
    h1 = soup.find("h1")
    if h1:
        val = clean(h1.get_text())
        val = re.sub(r'(Sarkari\s*Result|WWW\.SARKARIRESULT\.COM)[^\n]*', '', val, flags=re.I)
        val = clean(val)
        if val and len(val) > 10:
            return val

    # Title tag se
    if soup.title:
        val = clean(soup.title.text)
        val = re.sub(r'Sarkari Result.*', '', val, flags=re.I)
        val = re.sub(r'\|.*', '', val)
        val = clean(val)
        if val and len(val) > 10:
            return val

    # Text se "Name of Post :" pattern
    m = re.search(r'Name\s*of\s*Post\s*[:\-]?\s*(.{10,200}?)(?:\n|Short\s*Information|$)',
                  text, re.I)
    if m:
        return clean(m.group(1))[:200]

    return sr_extract_title(soup)


def sr_parse_main_table_sections(soup):
    """
    SarkariResult detail page ke bade content table ko parse karo.
    Page structure pe H2/H3 headings aur UL/LI lists table cells
    ke andar hoti hain — is function ko specifically usi structure
    ke liye design kiya gaya hai.
    """
    result = {
        "name_of_post": "",
        "short_information": "",
        "important_dates": {},
        "application_fee": {},
        "age_limit": {},
        "vacancy_details": {"total_post": "", "post_wise": []},
        "category_wise_vacancy": {},
        "how_to_apply": [],
        "useful_links": {"_all": []},
    }

    content = (
        soup.find("div", class_="entry-content")
        or soup.find("article")
        or soup
    )

    NOISE_RE = re.compile(
        r"sarkari\s*result|sarkariresult\.com|www\.sarkariresult|"
        r"android\s*app|apple\s*ios|telegram|whatsapp|join\s*channel|"
        r"instagram|facebook|twitter|youtube|x\.com|rojgarresult|"
        r"since\s*201\d|mobile\s*app\s*from|copyright|download\s*the\s*sarkari",
        re.I
    )

    def _clean_li_text(li_tag):
        t = clean(li_tag.get_text())
        return t if t and not NOISE_RE.search(t) else ""

    def _extract_ul_items(container):
        items = []
        for ul in container.find_all(["ul", "ol"]):
            for li in ul.find_all("li", recursive=False):
                t = _clean_li_text(li)
                if t:
                    items.append(t)
        if not items:
            for p in container.find_all("p"):
                t = clean(p.get_text())
                if t and not NOISE_RE.search(t) and len(t) > 5:
                    items.append(t)
        return items

    DATES_LABEL_MAP = [
        (r"application\s*begin|application\s*start|apply\s*begin", "application_begin"),
        (r"last\s*date.*apply\s*online|last\s*date.*apply|closing\s*date|last\s*date\s*for\s*apply",
         "last_date_apply_online"),
        (r"fee.*exam.*payment|pay.*exam.*fee|fee.*payment.*last|exam.*fee.*last",
         "last_date_pay_fee"),
        (r"correction", "correction_date"),
        (r"exam\s*date|date\s*of\s*exam|written\s*exam", "exam_date"),
        (r"admit\s*card|hall\s*ticket", "admit_card_available"),
        (r"result\s*date|result\s*declared", "result_date"),
        (r"last\s*date", "last_date_apply_online"),
    ]
    FEE_LABEL_MAP = [
        (r"general.*obc.*ews|general.*obc|obc.*ews.*general|ur.*obc|gen.*obc", "general_obc_ews"),
        (r"general\s*/\s*obc|general\s*obc", "general_obc"),
        (r"\bgeneral\b|\bur\b|\bunreserved\b", "general"),
        (r"\bobc\b", "obc"),
        (r"sc\s*/\s*st|sc.*st|st.*sc", "sc_st"),
        (r"\bsc\b", "sc"),
        (r"\bst\b", "st"),
        (r"\bews\b", "ews"),
        (r"pwd|ph\b|divyang", "pwd"),
        (r"female|women|lady", "female"),
        (r"pay.*mode|mode.*pay|payment\s*mode", "payment_mode"),
    ]
    AGE_LABEL_MAP = [
        (r"minimum\s*age|min\s*age|lower\s*age", "minimum_age"),
        (r"maximum\s*age|max\s*age|upper\s*age", "maximum_age"),
        (r"age\s*relaxation|relaxation", "age_relaxation"),
        (r"age\s*(?:limit|as\s*on)", "age_details"),
    ]

    def _map_label(label_raw, label_map):
        low = label_raw.lower().strip().rstrip(":")
        for pat, key in label_map:
            if re.search(pat, low):
                return key
        return None

    def _parse_kv_ul(container, label_map):
        result_dict = {}
        items = _extract_ul_items(container)
        for item in items:
            m = re.match(r'^([^:]{3,60}?)\s*:\s*(.{1,200})$', item)
            if m:
                label_raw = m.group(1).strip()
                val_raw = m.group(2).strip()
                if NOISE_RE.search(label_raw) or NOISE_RE.search(val_raw):
                    continue
                key = _map_label(label_raw, label_map)
                if key and key not in result_dict:
                    result_dict[key] = val_raw
        return result_dict, items

    seen_sections = set()
    all_tables = content.find_all("table")

    for table in all_tables:
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])

            # ── Header table row: Name Of Post / Short Info ──
            if len(cells) >= 2:
                key_raw = clean(cells[0].get_text()).lower()
                val_cell = cells[-1]
                if "name of post" in key_raw and not result["name_of_post"]:
                    h1 = val_cell.find("h1")
                    val = clean(h1.get_text()) if h1 else clean(val_cell.get_text())
                    if val and len(val) > 5:
                        result["name_of_post"] = val
                elif ("short information" in key_raw or "short info" in key_raw) and not result["short_information"]:
                    val = clean(val_cell.get_text())
                    lines = [l.strip() for l in val.split("\n") if l.strip() and not NOISE_RE.search(l)]
                    result["short_information"] = " ".join(lines)[:800]

            # ── Section cells with H2/H3 headings ───────────
            for cell in cells:
                heading = cell.find(["h2", "h3"])
                if not heading:
                    continue
                h_text = clean(heading.get_text())
                h_low = h_text.lower()
                if NOISE_RE.search(h_text):
                    continue
                if h_low[:40] in seen_sections:
                    continue
                seen_sections.add(h_low[:40])

                if "important date" in h_low or "key date" in h_low:
                    dates_dict, items = _parse_kv_ul(cell, DATES_LABEL_MAP)
                    result["important_dates"].update(dates_dict)
                    if not dates_dict and items:
                        for item in items:
                            m2 = re.match(r'^([^:]{3,60}?)\s*:\s*(.{1,100})$', item)
                            if m2:
                                k = re.sub(r'[^a-z0-9]+', '_', m2.group(1).lower().strip()).strip('_')
                                if k and not NOISE_RE.search(m2.group(2)):
                                    result["important_dates"][k] = m2.group(2).strip()

                elif "application fee" in h_low or "exam fee" in h_low:
                    fee_dict, items = _parse_kv_ul(cell, FEE_LABEL_MAP)
                    result["application_fee"].update(fee_dict)
                    if not fee_dict and items:
                        for item in items:
                            m2 = re.match(r'^([^:]{2,50}?)\s*:\s*(.{1,100})$', item)
                            if m2:
                                k = re.sub(r'[^a-z0-9]+', '_', m2.group(1).lower().strip()).strip('_')
                                if k:
                                    result["application_fee"][k] = m2.group(2).strip()
                    for item in _extract_ul_items(cell):
                        if any(w in item.lower() for w in ["upi", "debit", "credit", "net banking"]):
                            result["application_fee"]["payment_mode"] = item[:200]
                            break

                elif "age limit" in h_low or ("age" in h_low and "notification" in h_low):
                    age_dict, items = _parse_kv_ul(cell, AGE_LABEL_MAP)
                    result["age_limit"].update(age_dict)
                    m_as = re.search(r'as\s*on\s*([\d/\-]+)', h_text, re.I)
                    if m_as:
                        result["age_limit"]["as_on_date"] = m_as.group(1)
                    if not age_dict and items:
                        # Collect multiple values per key into lists
                        # (e.g. multiple "Maximum Age" lines for different posts)
                        _multi = {}
                        for item in items:
                            m2 = re.match(r'^([^:]{2,50}?)\s*:\s*(.{1,200})$', item)
                            if m2:
                                k = _map_label(m2.group(1), AGE_LABEL_MAP)
                                if k:
                                    if k not in _multi:
                                        _multi[k] = []
                                    _multi[k].append(m2.group(2).strip())
                            else:
                                # No colon — check if it's a relaxation note
                                if re.search(r'age\s*relaxation', item, re.I):
                                    k = "age_relaxation"
                                    _multi.setdefault(k, []).append(
                                        re.sub(r'^age\s*relaxation\s*[:\-]?\s*', '', item, flags=re.I).strip()
                                    )
                        for k, vals in _multi.items():
                            if k not in result["age_limit"]:
                                # Single value → string, multiple → list
                                result["age_limit"][k] = vals[0] if len(vals) == 1 else vals

                elif any(w in h_low for w in ["vacancy detail", "total post", "total vacancy",
                                               "recruitment 2", "post detail"]):
                    m_tot = re.search(r'total\s*[:\-]?\s*(\d+)\s*post', h_text, re.I)
                    if m_tot and not result["vacancy_details"]["total_post"]:
                        result["vacancy_details"]["total_post"] = m_tot.group(1)
                    for itbl in cell.find_all("table"):
                        rows_i = itbl.find_all("tr")
                        if not rows_i:
                            continue
                        hdrs = [clean(c.get_text()) for c in rows_i[0].find_all(["th", "td"])]
                        hdr_low = " ".join(hdrs).lower()
                        if any(w in hdr_low for w in ["post name", "total post", "eligib",
                                                        "general", "obc", "sc", "ews"]):
                            for dr in rows_i[1:]:
                                dcells = dr.find_all("td")
                                if not dcells:
                                    continue
                                entry = {}
                                for i, h in enumerate(hdrs):
                                    if i < len(dcells):
                                        v = clean(dcells[i].get_text())
                                        if v and not NOISE_RE.search(v):
                                            k = re.sub(r'[^a-z0-9]+', '_', h.lower().strip()).strip('_')
                                            entry[k] = v
                                if entry:
                                    result["vacancy_details"]["post_wise"].append(entry)

                elif "category wise" in h_low or ("category" in h_low and "vacancy" in h_low):
                    for itbl in cell.find_all("table"):
                        rows_i = itbl.find_all("tr")
                        if not rows_i:
                            continue
                        hdrs = [clean(c.get_text()) for c in rows_i[0].find_all(["th", "td"])]
                        for dr in rows_i[1:]:
                            dcells = dr.find_all("td")
                            if not dcells:
                                continue
                            entry = {}
                            for i, h in enumerate(hdrs):
                                if i < len(dcells):
                                    v = clean(dcells[i].get_text())
                                    if v:
                                        k = re.sub(r'[^a-z0-9]+', '_', h.lower().strip()).strip('_')
                                        entry[k] = v
                            if entry:
                                result["vacancy_details"]["post_wise"].append(entry)
                                for k, v in entry.items():
                                    if any(x in k for x in ["general", "obc", "sc", "st", "ews",
                                                              "ur", "pwd", "total"]):
                                        result["category_wise_vacancy"][k] = v

                elif any(w in h_low for w in ["how to fill", "how to apply"]):
                    items = _extract_ul_items(cell)
                    result["how_to_apply"].extend(
                        [i for i in items if not NOISE_RE.search(i) and len(i) > 10]
                    )

                elif any(w in h_low for w in ["useful link", "important link", "some useful"]):
                    LINK_KEY_MAP = [
                        (r"apply\s*online|registration|online\s*form|apply\s*now", "apply_online"),
                        (r"notification|advertisement|advt", "notification"),
                        (r"admit\s*card|hall\s*ticket", "admit_card"),
                        (r"\bresult\b|merit\s*list|score\s*card", "result"),
                        (r"answer\s*key|response\s*sheet", "answer_key"),
                        (r"syllabus|exam\s*pattern", "syllabus"),
                        (r"official\s*website", "official_website"),
                    ]
                    for itbl in cell.find_all("table"):
                        for irow in itbl.find_all("tr"):
                            icells = irow.find_all(["td", "th"])
                            if len(icells) < 2:
                                continue
                            link_title = clean(icells[0].get_text())
                            link_cell = icells[-1]
                            anchors = link_cell.find_all("a", href=True)
                            hrefs = [a["href"] for a in anchors
                                     if a["href"].startswith("http")
                                     and not NOISE_RE.search(a["href"])]
                            if not hrefs or not link_title or NOISE_RE.search(link_title):
                                continue
                            href = hrefs[0]
                            result["useful_links"]["_all"].append({"title": link_title, "links": href})
                            t_low = link_title.lower()
                            for pat, out_key in LINK_KEY_MAP:
                                if re.search(pat, t_low) and out_key not in result["useful_links"]:
                                    result["useful_links"][out_key] = href
                                    break

    return result


# =========================================================
# SR-DEEP v1.0 — new camelCase schema builders
# (sarkariresult.com detail page → prompt SR-DEEP-v1.0 output)
# =========================================================

# importantLinks ke liye allowed sirf official; ye domains/patterns block
SR_LINK_BLOCK = [
    "sarkariresult.com", "sarkariresults.org.in", "sarkariresultportal",
    "sarkariresult.tools", "doc.sarkariresults.org.in", "rojgarresult.com",
    "t.me", "telegram", "whatsapp.com", "wa.me",
    "facebook.com", "fb.me", "instagram.com",
    "youtube.com", "youtu.be", "twitter.com", "x.com",
    "play.google.com", "itunes.apple.com", "apps.apple.com",
    "cdn-icons-png.flaticon.com", "share.google", "threads.com",
    "linkedin.com", "sarkariresultshine.com",
    "tinyurl.com", "bit.ly", "goo.gl", "t.co", "rebrand.ly", "cutt.ly",
]


def sr_link_is_official(url):
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return False
    low = url.lower()
    return not any(b in low for b in SR_LINK_BLOCK)


def _first(d, *keys):
    """Dict se pehli non-empty value jo kisi diye key par mile."""
    if not isinstance(d, dict):
        return ""
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return ""


def sr_clean_num(value):
    """'600/-' → '600', '121 Post' → '121'. Number na ho to clean string."""
    if value in (None, ""):
        return ""
    s = str(value)
    m = re.search(r"\d[\d,]*", s)
    return m.group(0).replace(",", "") if m else sr_scrub_text(s)


def sr_clean_shortinfo(text):
    """shortInfo se promo/disclaimer/branding hatao."""
    if not text:
        return ""
    t = sr_scrub_text(text)
    PROMO = [
        r"sarkari\s*result®?\s*official.*?sarkariresult\.com",
        r"www\.sarkariresult\.com",
        r"sarkariresult\.com\s*\(since\s*201\d\)",
        r"official\s*website\s*of\s*sarkari\s*result",
        r"download\s*the\s*sarkari\s*result®?\s*mobile\s*app",
        r"registered\s*trademark\s*of\s*sarkari\s*result",
        r"copyright\s*©?\s*201\d[-–]?20\d\d.*?sarkariresult",
        r"interested\s*candidates\s*can\s*read\s*the\s*full\s*notification\s*before\s*apply\s*online",
        r"download\s*sarkariresult\.com\s*official\s*mobile\s*apps",
        r"android\s*apps?|apple\s*ios\s*apps?",
        r"the\s*examination\s*results.*?(?:website|portal)\.?",
    ]
    for p in PROMO:
        t = re.sub(p, "", t, flags=re.I)
    t = re.sub(r"\s{2,}", " ", t).strip(" .|-–—,")
    return t.strip()


def sr_build_important_links(useful_links_arr):
    """[{title,url}] → [{label,url}] sirf official URLs, dedup by URL."""
    out, seen = [], set()
    for it in useful_links_arr or []:
        label = sr_scrub_text(it.get("title", "")).strip()
        url   = (it.get("url", "") or "").strip()
        if not url or url in seen:
            continue
        if not sr_link_is_official(url):
            continue
        if not label or label.lower() in ("click here", "here", "www", "www."):
            label = sr_infer_link_label(url)
        seen.add(url)
        out.append({"label": label, "url": url})
    return out


def sr_infer_link_label(url):
    """URL se label guess karo agar anchor text 'Click Here' tha."""
    u = url.lower()
    if "syllabus" in u:                       return "Download Syllabus"
    if "admit" in u or "hall" in u:           return "Download Admit Card"
    if "result" in u or "merit" in u:         return "Download Result"
    if "answer" in u:                         return "Download Answer Key"
    if "notif" in u or "advt" in u or "advertisement" in u or ".pdf" in u:
        return "Download Notification"
    if "apply" in u or "online" in u or "reg" in u or "signin" in u or "login" in u:
        return "Apply Online"
    return "Official Website"


def sr_collect_all_links(soup, content_scope=None):
    """
    PAGE-WIDE: content area ke saare official <a> links collect karo
    (label = anchor text ya nearest preceding cell/label). Dedup by URL.
    Returns [{title,url}].
    """
    scope = content_scope or soup.find("div", class_="entry-content") or \
            soup.find("article") or soup
    out, seen = [], set()
    for a in scope.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith("http") or href in seen:
            continue
        if not sr_link_is_official(href):
            continue
        label = sr_scrub_text(a.get_text(" ")).strip()
        if not label or label.lower() in ("click here", "here", "www", "www.", "download"):
            # preceding cell (2-col link table) se label lo
            td = a.find_parent(["td", "th"])
            if td:
                prev = td.find_previous_sibling(["td", "th"])
                if prev:
                    label = sr_scrub_text(prev.get_text(" ")).strip()
            if not label or label.lower() in ("click here", "here"):
                label = sr_infer_link_label(href)
        seen.add(href)
        out.append({"title": label, "url": href})
    return out


# Keys/values jo additionalData me NAHI aane chahiye (already structured + junk)
def sr_clean_additional(extra, important_dates, application_fee, age_limit, vacancy):
    """
    additionalData se duplicate/junk hatao:
      - numeric ya date keys (reversed pairs: '21_05_2026': 'Application Begin')
      - value jo date/number hai aur already importantDates/fee me hai
      - label jo already known structured field hai
    """
    cleaned = {}
    known_vals = set()
    for src in (important_dates, application_fee, age_limit):
        if isinstance(src, dict):
            for v in src.values():
                known_vals.add(str(v).strip().lower())
    if isinstance(vacancy, list):
        for row in vacancy:
            if isinstance(row, dict):
                for v in row.values():
                    known_vals.add(str(v).strip().lower())

    DATE_RE = re.compile(r"^\d{1,2}[_/\-]\d{1,2}[_/\-]\d{2,4}$")
    JUNK_KEY = re.compile(
        r"^[\d_]+$"
        r"|^\d{1,2}_\d{1,2}_\d{2,4}"
        r"|^\d+_\w+$|_nil$|^na$|^nil$"
        r"|^(male|female|or|and|first|second|third|pm|am|rs|yes|no|the|in|of|"
        r"already_start|upto|only|more|etc|read|click|here|now)$"
        r"|^[a-z]{1,2}$"
        r"|^\d+_years?$"
        r"|^(gen|obc|sc|st|ews|ur|ph|pwd)$", re.I)
    # status phrases jo galti se KEY ban jaate hain (reversed pair)
    STATUS_KEY = re.compile(
        r"^(as_per_schedule|before_exam|available_soon|notified_soon|"
        r"coming_soon|to_be_notified|update_soon|announced_soon|"
        r"\d+_years?|\d+_marks?|nil|online_mode|offline_mode|na)$", re.I)
    BAD_LABEL = re.compile(
        r"date|fee|age|begin|last|exam|admit|result|answer|application|"
        r"vacanc|post|qualif|eligib|salary|minimum|maximum|payment|"
        r"video|how_to|how to|android|apple|app|tool|background|resizer|"
        r"^general$|^obc$|^sc$|^st$|^ews$|^ph$|short_information|click", re.I)
    # value-level junk: link-residue / version labels / branding
    BAD_VALUE = re.compile(
        r"^(version\s*i+|click|join|here|download|view|visit|sub|like|"
        r"android apps?|apple ios apps?)\.?$|version\s*i|sarkari\s*result|"
        r"^sc\s*/\s*st$|^minimum age$", re.I)

    for k, v in (extra or {}).items():
        ks = str(k).strip()
        vs = str(v).strip()
        if not ks or not vs:
            continue
        # reversed/numeric/date/status key → junk
        if JUNK_KEY.match(ks) or DATE_RE.match(ks) or STATUS_KEY.match(ks):
            continue
        # key looks like a known structured label → skip
        if BAD_LABEL.search(ks):
            continue
        # value-level junk → skip
        if BAD_VALUE.search(vs):
            continue
        # value duplicate of known structured data → skip
        if vs.lower() in known_vals:
            continue
        # link-residue value (Click/Join/Here/Download) → skip
        if re.fullmatch(r"(click|join|here|download|view|visit|sub|like|"
                        r"click here|read more)\.?", vs, re.I):
            continue
        # value is a bare date/number that belongs to dates/fee → skip
        if DATE_RE.match(vs) or re.fullmatch(r"\d{1,6}", vs):
            continue
        if len(vs) > 400:
            vs = vs[:400]
        cleaned[ks] = vs
    return cleaned


def sr_build_vacancy(final_vacancy):
    """internal vacancy dict → prompt vacancyDetails[] (camelCase)."""
    out = []
    if not isinstance(final_vacancy, dict):
        return out
    # B4 FIX: physical/test parameters that are NOT post-wise vacancy rows
    _JUNK_POST_NAMES = re.compile(
        # Only standalone physical-test junk — NOT general/male/female/obc/sc/st
        # which appear in real post names.
        r"^(height|chest|weight|physical\s*test|physical\s*standard|"
        r"physical\s*efficiency|"
        r"\d+\s*m(?:eter|tr)?s?\s*(?:race|run)?|\d+\.?\d*\s*km|"
        r"long\s*jump|high\s*jump|shot\s*put|pull[\s-]*up|push[\s-]*up|"
        r"running|swimming|endurance|race|jump|throw)(\s|$)",
        re.I
    )
    total = sr_clean_num(_first(final_vacancy, "total_post", "totalPost", "total"))
    post_wise = final_vacancy.get("post_wise") or final_vacancy.get("postWise") or []
    if isinstance(post_wise, list) and post_wise:
        for row in post_wise:
            if not isinstance(row, dict):
                continue
            obj = {}
            pn = sr_scrub_text(_first(row, "post_name", "postName", "post", "name"))
            # B4 FIX: physical test / junk rows skip karo
            if pn and _JUNK_POST_NAMES.match(pn.strip()):
                continue
            if pn:
                obj["postName"] = pn
            tp = sr_clean_num(_first(row, "total_post", "totalPost", "total", "posts"))
            if tp:
                obj["totalPost"] = tp
            elig = sr_scrub_text(_first(row, "eligibility", "qualification"))
            if elig:
                obj["eligibility"] = elig
            pay = sr_scrub_text(_first(row, "pay_scale", "payScale", "salary", "pay"))
            if pay:
                obj["payScale"] = pay
            cw = row.get("category_wise") or row.get("categoryWise")
            if isinstance(cw, dict) and cw:
                obj["categoryWise"] = {kk: sr_clean_num(vv) for kk, vv in cw.items() if vv}
            if obj:
                out.append(obj)
    if not out and total:
        out.append({"totalPost": total})
    return out


def sr_build_meta(url, soup, page_title, detected, overridden):
    """meta{} build karo — og/article meta tags se."""
    def _meta(prop):
        tag = soup.find("meta", attrs={"property": prop}) or \
              soup.find("meta", attrs={"name": prop})
        if not tag:
            return ""
        c = tag.get("content", "")
        if isinstance(c, list):          # multi-valued attr → join
            c = " ".join(str(x) for x in c)
        return str(c).strip()
    meta = {
        "sourceUrl":          url,
        "scrapedAt":          datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "pageTitle":          sr_scrub_text(page_title) or sr_scrub_text(
                                  (soup.title.get_text() if soup.title else "")),
        "detectedCategory":   detected,
        "categoryOverridden": bool(overridden),
    }
    pub = _meta("article:published_time")
    mod = _meta("article:modified_time")
    sec = _meta("article:section")
    if pub: meta["publishedTime"] = pub
    if mod: meta["modifiedTime"]  = mod
    if sec: meta["articleSection"] = sr_scrub_text(sec)
    return meta


def sr_prune_empty(obj):
    """Khaali "", [], {} keys recursively hatao (prompt rule #2 / #10)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            cv = sr_prune_empty(v)
            if cv in ("", [], {}, None):
                continue
            out[k] = cv
        return out
    if isinstance(obj, list):
        res = [sr_prune_empty(i) for i in obj]
        return [i for i in res if i not in ("", [], {}, None)]
    return obj


def sr_deep_extract(soup):
    """
    SR detail page ek bade <table> me sections rakhta hai. Har section ek
    <h2> heading + uske neeche <ul>/rows hota hai. Ye function deeply parse karke
    nikalta hai:
      - vacancyDetails (trade-wise: TradeName | TotalPost + shared eligibility)
      - howToApply steps
      - selectionProcess (agar ho)
    Returns dict.
    """
    out = {"vacancyDetails": [], "howToApply": [], "selectionProcess": [],
           "courseDetails": [], "importantDatesExtra": {},
           "subjectWiseVacancy": [], "subjectLinkUrls": set(),
           "eligibilitySection": [],
           "allTables": []}
    scope = (soup.find("div", class_="entry-content") or soup.find("article") or soup)

    # ── GENERIC TABLE CAPTURE — koi bhi meaningful table miss na ho ─────────
    # (specialized parsers ke alawa, har data-table ko clean {heading,headers,
    #  rows} form me preserve karo. Link-only / dates / fee tables skip.)
    def _sr_generic_tables():
        cap = []
        seen_sig = set()
        SKIP_HEAD = re.compile(r"important date|application fee|how to apply|"
                               r"important link|useful link", re.I)
        LINKWORD = re.compile(r"click here|download|apply online|view|visit|"
                              r"join now|notification pdf", re.I)
        # info/metadata table labels (title/date/shortInfo already structured)
        META_LBL = re.compile(r"name of post|post date|post update|short information|"
                              r"short info|update\b|department|organization", re.I)
        for tbl in scope.find_all("table"):
            # I11 FIX: SR mega-table layout — the outer wrapper has all sections.
            # If a table has very few DIRECT child rows but wraps nested tables,
            # skip the outer (its nested tables are processed in their own
            # iterations) so real supplementary tables aren't lost to section_kw.
            _direct_rows = tbl.find_all("tr", recursive=False)
            if len(_direct_rows) <= 3 and tbl.find_all("table"):
                continue
            rows_raw = tbl.find_all("tr")
            if len(rows_raw) < 2:
                continue
            grid = []
            for tr in rows_raw:
                cells = [sr_scrub_text(c.get_text(" "))
                         for c in tr.find_all(["td", "th"])]
                cells = [c for c in cells if c is not None]
                if any(cells):
                    grid.append(cells)
            if len(grid) < 2:
                continue
            # link-heavy table? (Important Links etc.) → skip (already in links)
            cell_total = sum(len(r) for r in grid)
            link_cells = sum(1 for r in grid for c in r if LINKWORD.search(c))
            if cell_total and link_cells / cell_total >= 0.4:
                continue
            # metadata/info table? (first-col labels = Name Of Post/Post Date/etc)
            first_col_labels = " ".join(r[0] for r in grid if r).lower()
            meta_hits = len(META_LBL.findall(first_col_labels))
            if meta_hits >= 2:
                continue
            # SR mega-container layout table? (ek cell me poore sections crammed —
            #  Important Dates + Application Fee + Age Limit ek saath) → skip,
            #  kyunki ye sab already structured fields me hai (duplicate + messy)
            full_blob = " ".join(c for r in grid for c in r).lower()
            section_kw = sum(1 for kw in ["important date", "application fee",
                                          "age limit", "vacancy detail",
                                          "how to apply", "short information"]
                             if kw in full_blob)
            # B3 FIX: raise threshold 3 → 4. If 3 section keywords but the table
            # has real data rows (>3), keep it instead of skipping.
            # MEGA-TABLE SALVAGE: when a SR mega-table crams ALL sections into one
            # table (4+ section keywords), we used to drop the WHOLE table — which
            # also threw away genuine data rows (eligibility, post details) that
            # live in the same table. Instead, keep only the "data" rows: those
            # whose cells are short-ish and don't themselves contain section blobs.
            if section_kw >= 4:
                _SEC_BLOB = re.compile(
                    r"important date|application fee|age limit|how to (fill|apply)|"
                    r"short information|some useful|interested candidate|"
                    r"download sarkari|android app|apple ios|click here|"
                    r"join sarkari|telegram|whatsapp|official website|"
                    r"sarkari result", re.I)
                salvage = []
                for r in grid:
                    blob = " ".join(r)
                    # keep rows that look like real tabular data:
                    #  - 2+ columns, OR a label+value pair
                    #  - not a section-blob row, not pure links
                    if len(r) >= 2 and not _SEC_BLOB.search(blob) and \
                            not LINKWORD.search(blob) and \
                            not any(len(c) > 300 for c in r):
                        salvage.append(r)
                if len(salvage) >= 2:
                    # find a heading for the salvaged data (eligibility/post/etc.)
                    _sh = ""
                    for r in grid:
                        rj = " ".join(r).lower()
                        if ("eligibility detail" in rj or "post detail" in rj or
                                "vacancy detail" in rj) and len(" ".join(r)) < 120:
                            _sh = " ".join(r); break
                    sig2 = (_sh.lower() + "|" + "|".join(salvage[0])[:80])
                    if sig2 not in seen_sig:
                        seen_sig.add(sig2)
                        _hdr = salvage[0] if salvage else []
                        _bdy = salvage[1:] if len(salvage) > 1 else []
                        if any(re.fullmatch(r"\d[\d,]*", c) for c in _hdr):
                            _hdr, _bdy = [], salvage
                        cap.append({"heading": _sh or "Eligibility Details",
                                    "headers": _hdr, "rows": _bdy})
                continue
            if section_kw == 3 and len(grid) <= 3:
                continue
            # koi single cell bahut bada (>250 char) jisme multiple labels → layout junk
            if any(len(c) > 250 and (":" in c) and
                   (c.lower().count("date") + c.lower().count("fee") +
                    c.lower().count("age")) >= 2
                   for r in grid for c in r):
                continue
            # heading detect
            heading = ""
            prev = tbl.find_previous(["h2", "h3", "h4", "strong", "p"])
            if prev:
                ht = sr_scrub_text(prev.get_text(" "))
                if ht and 3 < len(ht) < 120:
                    heading = ht
            if heading and SKIP_HEAD.search(heading):
                continue
            # dedup by signature
            sig = heading.lower() + "|" + "|".join(grid[0])[:80]
            if sig in seen_sig:
                continue
            seen_sig.add(sig)
            headers = grid[0] if grid else []
            body = grid[1:] if len(grid) > 1 else []
            # header row heuristic: first row me number nahi (labels hain)
            if any(re.fullmatch(r"\d[\d,]*", c) for c in headers):
                headers, body = [], grid
            cap.append({"heading": heading or "Table",
                        "headers": headers, "rows": body})
        return cap


    def _cells_text(tr):
        """colspan-aware: har cell ka text (merged cells ek hi value)."""
        return [sr_scrub_text(c.get_text(" ")) for c in tr.find_all(["td", "th"])]

    # ── Vacancy + Subject-Wise + CategoryWise tables (heading-row driven) ──
    # SR ek bade table me multiple sub-tables rakhta hai. Hum row-by-row
    # heading detect karke uske neeche ki data rows parse karte hain.

    # Junk post names filter (physical test rows)
    _JUNK_POST = re.compile(
        # Only match STANDALONE physical-measurement/test junk words.
        # REMOVED: general, obc, sc, st, ews, male, female, details — these appear
        # in REAL post names ("General Duty Medical Officer", "Female Constable").
        r"^(height|chest|weight|physical\s*test|physical\s*standard|"
        r"physical\s*efficiency|"
        r"\d+\s*m(?:eter|tr)?s?\s*(?:race|run)?|\d+\.?\d*\s*km|"
        r"long\s*jump|high\s*jump|shot\s*put|pull[\s-]*up|push[\s-]*up|"
        r"running|swimming|endurance|race|jump|throw)(\s|$)",
        re.I
    )
    # Category-wise column headers
    _CATWISE_COLS = re.compile(
        r"^(general|ur|obc|sc|st|ews|ph|pwd|dviyang|exsm|"
        r"unreserved|total|female|male|others?)$", re.I
    )
    # FIX B: gender-wise column headers (NDA: Service | Male | Female | Total Post)
    _GENDERWISE_COLS = re.compile(
        r"^(male|female|transgender|women|men|man|total|total\s*post)$", re.I
    )

    for table in scope.find_all("table"):
        rows = table.find_all("tr")
        mode = None          # None | vacancy | catwise | vacancy_gender | statewise
        catwise_headers = []  # category-wise column names
        _genderwise_headers = []   # FIX B: gender-wise column names
        _statewise_headers = []    # FIX D: state-wise column names
        _vac_cols = []             # column-mapped vacancy header names
        _current_vacancy_heading = ""  # vacancy table section heading
        for tr in rows:
            texts = [t for t in _cells_text(tr) if t]
            joined = " ".join(texts).lower()
            links_in_row = tr.find_all("a", href=True)

            # ---- heading rows that switch mode ----
            if "subject wise" in joined and "vacanc" in joined:
                mode = "subject_hdr"; continue

            # BUG2 FIX: category-wise vacancy heading detect (check BEFORE plain vacancy)
            if ("category wise" in joined or "cat wise" in joined or
                    "category-wise" in joined) and "vacanc" in joined:
                # I9: capture heading (branding-stripped)
                _h = " ".join(texts).strip()
                _current_vacancy_heading = re.sub(
                    r'(sarkari\s*result|www\.sarkariresult|since\s*201\d)[^\n]*',
                    '', _h, flags=re.I).strip()
                mode = "catwise_hdr"; continue

            # FIX D: state-wise / zone-wise vacancy heading
            if (("state wise" in joined or "zone wise" in joined or
                 "state-wise" in joined or "district wise" in joined) and
                    ("vacanc" in joined or "post" in joined)):
                _h = " ".join(texts).strip()
                _current_vacancy_heading = re.sub(
                    r'(sarkari\s*result|www\.sarkariresult|since\s*201\d)[^\n]*',
                    '', _h, flags=re.I).strip()
                mode = "statewise_hdr"; continue

            # FIX B: vacancy heading — ONLY from colspan/single-cell rows, never from
            # column-header rows (prevents "heading Service Male Female..." accumulation)
            if "vacancy detail" in joined or "vacancy details" in joined:
                all_cells_vac = tr.find_all(["td", "th"])
                is_true_heading = (
                    len(all_cells_vac) == 1 or
                    (len(texts) <= 2 and not any(re.search(r'\d{2,}', t) for t in texts))
                )
                if is_true_heading or len(texts) <= 3:
                    _h = " ".join(texts).strip()
                    # FIX B: cut heading at first column-indicator word so the
                    # column-header text never gets glued onto the heading
                    _h = re.split(r'\s+(Service|Male|Female|Post Name|Trade|Campus|Branch)\s+',
                                  _h)[0]
                    _current_vacancy_heading = re.sub(
                        r'(sarkari\s*result|www\.sarkariresult|since\s*201\d)[^\n]*',
                        '', _h, flags=re.I).strip()
                    mode = "vacancy_hdr"; continue
                else:
                    # multi-cell row WITH numbers labelled "vacancy details" is actually
                    # a column-header row — switch mode but DON'T touch the heading
                    mode = "vacancy_hdr"; continue

            # Also: single-cell heading row with "Vacancy" in colspan td
            all_cells = tr.find_all(["td", "th"])
            if (len(all_cells) == 1 and "vacanc" in joined and
                    all_cells[0].get("colspan")):
                _h = " ".join(texts).strip()
                _h = re.split(r'\s+(Service|Male|Female|Post Name|Trade|Campus|Branch)\s+',
                              _h)[0]
                _current_vacancy_heading = re.sub(
                    r'(sarkari\s*result|www\.sarkariresult|since\s*201\d)[^\n]*',
                    '', _h, flags=re.I).strip()
                mode = "vacancy_hdr"; continue

            # ── ELIGIBILITY-DETAILS table (e.g. JHTET "Primary Level | eligibility",
            #    "Junior Level | eligibility"). These 2-col rows have NO Total Post
            #    column so they were never captured as vacancyDetails AND the mega-table
            #    they live in gets skipped by _sr_generic_tables (4+ section keywords),
            #    so the eligibility text was silently lost. Capture it here. ──
            #    GUARD: only treat as a standalone eligibility table when this is a
            #    single-cell heading row (colspan) — NOT a "Post Name | Eligibility"
            #    column-header row, which the normal vacancy flow handles better.
            if (("eligibility detail" in joined or "eligibility details" in joined)
                    and "vacanc" not in joined and "post name" not in joined
                    and "post detail" not in joined):
                _ecells = tr.find_all(["td", "th"])
                _h = " ".join(texts).strip()
                # heading-style row = 1 cell (colspan) OR a single short text, and
                # must NOT itself be a 2-col data row (label + eligibility text)
                _is_elig_heading = (
                    (len(_ecells) == 1 or len([t for t in texts if t.strip()]) == 1)
                    and len(_h) < 140
                )
                if _is_elig_heading:
                    _current_vacancy_heading = re.sub(
                        r'(sarkari\s*result|www\.sarkariresult|since\s*201\d)[^\n]*',
                        '', _h, flags=re.I).strip()
                    mode = "eligibility"; continue

            if mode == "eligibility":
                # A "Post Name" column header means this is really a vacancy table —
                # hand control to the normal vacancy detection below.
                if "post name" in joined or ("post" in joined and "total" in joined):
                    mode = "vacancy_hdr"
                    # fall through to column-header detection (do NOT continue)
                else:
                    # end the eligibility block at a new section / links / "how to"
                    if (not texts or
                            any(k in joined for k in [
                                "how to fill", "how to apply", "some useful",
                                "important link", "interested candidate",
                                "download sarkari", "android app", "click here",
                                "vacancy detail"])):
                        mode = None; continue
                    # a real eligibility row = label cell + meaningful eligibility cell
                    if len(texts) >= 2:
                        label = texts[0].strip()
                        elig  = " ".join(texts[1:]).strip()
                        if (label and elig and len(elig) >= 8 and
                                not _JUNK_POST.match(label) and
                                not re.fullmatch(r'[\d,]+', label)):
                            entry = {"postName": label, "eligibility": elig[:600]}
                            if _current_vacancy_heading:
                                entry["tableHeading"] = _current_vacancy_heading
                            if not any(v.get("postName", "").lower() == label.lower() and
                                       v.get("eligibility") for v in out["vacancyDetails"]):
                                out["vacancyDetails"].append(entry)
                    continue

            # ---- column-header row detection ----
            # Trigger when we're in vacancy_hdr mode OR when a row directly looks
            # like a multi-column header (Post Name + Total/Age/Eligibility...),
            # e.g. UPSC Geo "Cat|Post Name|Total Post|Age Limit|Eligibility" whose
            # heading said "Total : 85 Post" (no "Vacancy Details" words).
            _looks_like_colhdr = (
                mode not in ("vacancy_mapped", "vacancy", "catwise_hdr",
                             "catwise", "statewise_hdr", "statewise") and
                len(texts) >= 3 and
                ("post name" in joined or "exam name" in joined) and
                any(k in joined for k in ["total", "eligib", "age", "department",
                                          "subject", "qualif"]) and
                # NOT a category-wise header (≥2 of UR/EWS/OBC/SC/ST present)
                sum(1 for t in texts
                    if re.match(r'^(ur|ews|obc|sc|st|general|unreserved|pwd|ph)$',
                                t.strip(), re.I)) < 2 and
                not any(re.search(r'\d{2,}', t) for t in texts[:1])  # 1st cell not a number
            )
            # 2-column "Exam Name | <X> Eligibility" header (NCET / JIPMAT) →
            # treat as a simple eligibility table (Exam | eligibility text).
            if (mode not in ("vacancy", "vacancy_mapped", "eligibility")
                    and len(texts) == 2
                    and ("exam name" in texts[0].lower() or "post name" in texts[0].lower())
                    and "eligib" in texts[1].lower()):
                _current_vacancy_heading = _current_vacancy_heading or texts[1].strip()
                mode = "eligibility"; continue
            if mode == "vacancy_hdr" or _looks_like_colhdr:
                _has_post_col = any(k in joined for k in [
                    "post name", "trade name", "trade", "course name", "post",
                    "service", "branch", "campus", "state", "district",
                    "zone", "centre", "exam name", "name of exam", "exam",
                ])
                _has_count_col = any(k in joined for k in [
                    "total", "eligib", "vacancy", "post", "male", "female",
                    "age", "department", "subject",
                ])
                if _has_post_col and _has_count_col:
                    # FIX B: detect gender-wise columns (Service | Male | Female | Total)
                    _has_gender = (
                        any(_GENDERWISE_COLS.match(t.strip()) for t in texts) and
                        sum(1 for t in texts
                            if re.match(r'^(male|female|women|men)$', t.strip(), re.I)) >= 1
                    )
                    if _has_gender:
                        _genderwise_headers = [t.strip() for t in texts]
                        mode = "vacancy_gender"; continue
                    # MULTI-COLUMN vacancy (e.g. UPSC Geo: Cat|Post Name|Total Post|
                    # Age Limit|Eligibility). Remember the header positions so the
                    # data rows can be mapped to the right field by column name.
                    _hdr_low = [t.strip().lower() for t in texts]
                    _has_named_cols = sum(1 for h in _hdr_low if any(
                        kw in h for kw in ["post name", "total", "age", "eligib",
                                           "department", "subject", "exam name"])) >= 2
                    if _has_named_cols and len(texts) >= 3:
                        _vac_cols = _hdr_low
                        mode = "vacancy_mapped"; continue
                    mode = "vacancy"; continue

            # ---- COLUMN-MAPPED vacancy rows (header-position aware) ----
            if mode == "vacancy_mapped":
                if (not texts or (len(texts) == 1 and not re.search(r'\d', texts[0]))
                        or any(k in joined for k in [
                            "how to fill", "how to apply", "some useful",
                            "important link", "interested candidate",
                            "download sarkari", "android app"])):
                    mode = None; _vac_cols = []; continue
                if len(texts) >= 2 and _vac_cols:
                    # align cells to header columns; if fewer cells than headers,
                    # a leading "Cat" group-cell may be merged — best-effort align
                    cells = texts
                    obj = {}
                    # map by header keyword
                    for ci, cell in enumerate(cells):
                        if ci >= len(_vac_cols):
                            break
                        h = _vac_cols[ci]
                        # IMPORTANT: check specific columns (eligibility/total/age/
                        # subject/department) BEFORE the generic "post" match, because
                        # headers like "...Various Post Eligibility Details" contain
                        # the word "post" and would wrongly grab the eligibility text.
                        if "eligib" in h or "qualif" in h:
                            obj["eligibility"] = cell[:600]
                        elif "total" in h or "vacanc" in h:
                            _t = cell.replace(",", "")
                            if re.fullmatch(r'\d+', _t):
                                obj["totalPost"] = _t
                        elif "age" in h:
                            obj["ageLimit"] = cell
                        elif "subject" in h:
                            obj["subjects"] = cell[:600]
                        elif "department" in h:
                            obj["department"] = cell
                        elif "post name" in h or "name of post" in h or "exam name" in h:
                            obj["postName"] = cell
                        elif h.strip() in ("post", "posts", "name", "trade"):
                            obj["postName"] = cell
                    # if no postName mapped but row has a long text cell, use it
                    if not obj.get("postName"):
                        # if a department was mapped, promote it to postName
                        if obj.get("department"):
                            obj["postName"] = obj.pop("department")
                        else:
                            _cand = [c for c in cells if len(c) > 2
                                     and not re.fullmatch(r'[\dIVX,\-–]+', c)]
                            if _cand:
                                obj["postName"] = _cand[0]
                    pn = obj.get("postName", "").strip()
                    # skip physical-eligibility header leakage (Details | Male | Female)
                    if pn.lower() in ("details", "category", "s no", "s no.", "sl no"):
                        mode = None; _vac_cols = []; continue
                    if pn and not _JUNK_POST.match(pn) and len(obj) >= 2:
                        if _current_vacancy_heading:
                            obj["tableHeading"] = _current_vacancy_heading
                        out["vacancyDetails"].append(obj)
                continue

            # FIX D: state-wise column-header + data rows
            if mode == "statewise_hdr":
                if any(k in joined for k in ["state", "zone", "district", "total"]):
                    _statewise_headers = [t.strip() for t in texts]
                    mode = "statewise"; continue

            if mode == "statewise":
                if not texts or (len(texts) == 1 and not re.search(r'\d', texts[0])):
                    mode = None; _statewise_headers = []; continue
                if len(texts) >= 2:
                    state_name = texts[0].strip()
                    total_val = next(
                        (t.replace(',', '') for t in texts[1:]
                         if re.fullmatch(r'[\d,]+', t.replace(',', ''))), "")
                    if state_name and not _JUNK_POST.match(state_name):
                        entry = {"postName": state_name}
                        if total_val:
                            entry["totalPost"] = total_val
                        if _current_vacancy_heading:
                            entry["tableHeading"] = _current_vacancy_heading
                        if not any(v.get("postName", "").lower() == state_name.lower()
                                   for v in out["vacancyDetails"]):
                            out["vacancyDetails"].append(entry)
                continue

            # ---- GENDER-WISE data rows (FIX B: NDA Service | Male | Female | Total) ----
            if mode == "vacancy_gender":
                if not texts or (len(texts) == 1 and not re.search(r'\d', texts[0])):
                    mode = None; _genderwise_headers = []; continue
                if len(texts) >= 2:
                    post_name = texts[0].strip()
                    if not post_name or _JUNK_POST.match(post_name):
                        continue
                    gw = {}
                    total_val = ""
                    for i, hdr in enumerate(_genderwise_headers[1:], 1):
                        if i >= len(texts):
                            break
                        val = texts[i].replace(",", "").strip()
                        if not re.fullmatch(r'\d+', val):
                            continue
                        h_low = hdr.lower().strip()
                        if h_low in ('total', 'total post', 'total posts'):
                            total_val = val
                        elif re.match(r'^(male|men|man)$', h_low):
                            gw["male"] = val
                        elif re.match(r'^(female|women|lady)$', h_low):
                            gw["female"] = val
                        elif h_low == 'transgender':
                            gw["transgender"] = val
                    obj = {"postName": post_name}
                    if total_val:
                        obj["totalPost"] = total_val   # actual Total column, NOT male count
                    elif gw:
                        try:
                            obj["totalPost"] = str(sum(int(v) for v in gw.values()))
                        except Exception:
                            pass
                    if gw:
                        obj["genderWise"] = gw
                    if _current_vacancy_heading:
                        obj["tableHeading"] = _current_vacancy_heading
                    existing = next((v for v in out["vacancyDetails"]
                                     if v.get("postName", "").lower() == post_name.lower()), None)
                    if existing:
                        if gw: existing["genderWise"] = gw
                        if total_val: existing["totalPost"] = total_val
                    else:
                        out["vacancyDetails"].append(obj)
                continue

            if mode == "catwise_hdr":
                # Next row with category columns (General | EWS | OBC | SC | ST | Total)
                if any(_CATWISE_COLS.match(t.strip()) for t in texts):
                    catwise_headers = [t.strip() for t in texts]
                    mode = "catwise"; continue

            if mode == "subject_hdr" and ("advt" in joined or "subject" in joined) \
                    and ("total" in joined or "post" in joined):
                mode = "subject"; continue

            # DIRECT subject-wise column header (no "Subject Wise" heading before it):
            # "Advt No | Subject Name | Total Post | Download Notification" (MPPSC type)
            if (mode not in ("subject", "catwise", "vacancy_mapped") and
                    "subject" in joined and
                    ("advt" in joined or "advt no" in joined) and
                    ("total" in joined or "post" in joined) and
                    not any(re.search(r'\d{2,}', t) for t in texts[:1])):
                mode = "subject"; continue

            # ---- CATEGORY-WISE data rows (BUG2 FIX) ----
            if mode == "catwise":
                if tr.find(["h2", "h3"]) or (len(texts) == 1 and not re.search(r"\d", texts[0])):
                    mode = None; catwise_headers = []; continue
                if len(texts) >= 2 and catwise_headers:
                    # FIX C: blank-first-cell detection. If the Post Name cell is BLANK
                    # (filtered out of `texts`), then texts[0] is actually the first
                    # category VALUE (e.g. UR=2148) — using it as postName shifts all
                    # columns. Re-align against RAW cells (which keep the empty cell).
                    raw_cells = _cells_text(tr)  # includes empty strings
                    post_name = ""
                    aligned_values = []
                    if len(raw_cells) >= len(catwise_headers):
                        post_name = sr_scrub_text(raw_cells[0]) if raw_cells else ""
                        aligned_values = raw_cells[1:]
                    else:
                        post_name = texts[0] if texts else ""
                        # texts[0] numeric AND first header is a Post-Name col → blank cell
                        if (re.fullmatch(r'[\d,]+', post_name.replace(',', '')) and
                                catwise_headers and 'post' in catwise_headers[0].lower()):
                            post_name = ""
                            aligned_values = texts        # all texts are category values
                        else:
                            aligned_values = texts[1:]

                    if not post_name:
                        # BOB: blank post means "same as the previous real post" (Apprentice)
                        prev_posts = [v.get("postName", "") for v in out["vacancyDetails"]
                                      if v.get("postName") and
                                      not re.fullmatch(r'[\d,]+', v.get("postName", "").replace(',', ''))]
                        post_name = prev_posts[-1] if prev_posts else "Unknown"

                    if _JUNK_POST.match(post_name.strip()):
                        continue
                    cw = {}
                    _cw_total = ""
                    for i, hdr in enumerate(catwise_headers[1:]):
                        if i < len(aligned_values):
                            val = sr_scrub_text(aligned_values[i]).replace(",", "")
                            if re.fullmatch(r"\d+", val):
                                # I3 FIX: Total/Total Post is NOT a category — keep separate
                                if hdr.strip().lower() in ('total', 'total post', 'total posts'):
                                    _cw_total = val
                                    continue
                                cw[hdr.strip()] = val
                    # IMPORTANT: categoryWise ko vacancy entry me MERGE mat karo.
                    # SarkariResult pe "Vacancy Details" (Post|Total|Eligibility)
                    # aur "Category Wise" (Post|UR|OBC|SC|ST|Total) DO ALAG tables
                    # hote hain — bhale hi postName same ho (e.g. CBI Apprentice).
                    # Inhe alag entries rakho taaki renderer 2 alag tables banaye.
                    # Duplicate catwise entry (same post + same cw) skip karo.
                    _dup = next((v for v in out["vacancyDetails"]
                                 if v.get("postName", "").lower() == post_name.lower()
                                 and v.get("categoryWise")), None)
                    if _dup:
                        # already have a catwise entry for this post → don't duplicate
                        pass
                    else:
                        entry = {"postName": post_name}
                        if _cw_total:
                            entry["totalPost"] = _cw_total
                        if cw:
                            entry["categoryWise"] = cw
                        if _current_vacancy_heading:
                            entry["tableHeading"] = _current_vacancy_heading
                        out["vacancyDetails"].append(entry)
                continue

            # ---- VACANCY data rows (Post | Total | Eligibility) ----
            if mode == "vacancy":
                # naya heading aaya to ruk jao
                if tr.find(["h2", "h3"]) or (len(texts) == 1 and not re.search(r"\d", texts[0])):
                    mode = None
                    continue
                # eligibility cell = jisme <ul> ho
                elig = ""
                for c in tr.find_all(["td", "th"]):
                    if c.find("ul"):
                        lis = [sr_scrub_text(li.get_text(" ")) for li in c.find_all("li")]
                        lis = [x for x in lis if x]
                        if lis:
                            elig = "; ".join(lis)
                # non-eligibility cell texts (blank cells skip, dedup)
                simple = []
                seen_vals = set()
                for c in tr.find_all(["td", "th"]):
                    if c.find("ul"):
                        continue
                    t = sr_scrub_text(c.get_text(" "))
                    if t and t not in seen_vals:
                        seen_vals.add(t)
                        simple.append(t)
                # numeric totalPost dhundo (first numeric cell after post name)
                if len(simple) >= 1:
                    post_name = simple[0]
                    # BUG1 FIX: junk rows skip
                    if _JUNK_POST.match(post_name.strip()):
                        continue
                    total = ""
                    for s in simple[1:]:
                        if re.fullmatch(r"[\d,]+", s):
                            total = s.replace(",", "")
                            break
                    # PLAIN-TEXT ELIGIBILITY FIX: SR ki kai tables me eligibility
                    # <ul> me nahi, seedha <td> text me hoti hai (e.g. SSC CGL
                    # "Junior Statistical Officer | Bachelor Degree in Any Stream").
                    # Agar <ul>-eligibility nahi mili to last non-numeric cell ko
                    # eligibility maan lo (taaki ye rows drop na hon).
                    if not elig:
                        _elig_cand = [s for s in simple[1:]
                                      if not re.fullmatch(r"[\d,]+", s)
                                      and len(s) >= 8
                                      and "click here" not in s.lower()]
                        if _elig_cand:
                            elig = max(_elig_cand, key=len)[:600]
                    if post_name and total:
                        obj = {"postName": post_name, "totalPost": total}
                        if elig:
                            obj["eligibility"] = elig
                        if _current_vacancy_heading:
                            obj["tableHeading"] = _current_vacancy_heading
                        out["vacancyDetails"].append(obj)
                    elif post_name and not total and elig:
                        _o = {"postName": post_name, "eligibility": elig}
                        if _current_vacancy_heading:
                            _o["tableHeading"] = _current_vacancy_heading
                        out["vacancyDetails"].append(_o)

            # ---- SUBJECT-WISE data rows (Advt | Subject | Total | PDF) ----
            elif mode == "subject":
                if tr.find(["h2", "h3"]) or len(texts) < 2:
                    mode = None
                    continue
                # advt no, subject, total + notification link
                pdf = ""
                for a in links_in_row:
                    href = a["href"].strip()
                    if sr_link_is_official(href):
                        pdf = href
                        out["subjectLinkUrls"].add(href)
                # numeric total dhundo
                total = ""
                for t in texts:
                    if re.fullmatch(r"\d+", t.replace(",", "")):
                        total = t.replace(",", "")
                        break
                # subject name = sabse lamba text jo number/advt nahi
                cand = [t for t in texts if not re.fullmatch(r"\d+", t)
                        and not re.match(r"\d+/\d{4}", t) and "click here" not in t.lower()]
                subject = max(cand, key=len) if cand else ""
                advt = next((t for t in texts if re.match(r"\d+/\d{4}", t)), "")
                if subject and total:
                    row = {"advtNo": advt, "subject": subject, "totalPost": total}
                    if pdf:
                        row["notificationPdf"] = pdf
                    out["subjectWiseVacancy"].append(row)

    # ── howToApply / selectionProcess — heading ke neeche ki list ──────────
    for h in scope.find_all(["h2", "h3", "h4"]):
        htext = h.get_text(" ").lower()
        if re.search(r"how to (fill|apply)|apply.*online form|filling", htext):
            ul = h.find_next("ul")
            if ul:
                for li in ul.find_all("li"):
                    t = sr_scrub_text(li.get_text(" "))
                    if t and len(t) > 5:
                        out["howToApply"].append(t)
        if re.search(r"selection process|mode of selection|selection criteria|"
                     r"selection procedure|how to select|selection basis", htext):
            # Try UL first, then P tags, then table cells
            nxt = h.find_next_sibling()
            steps = []
            while nxt and getattr(nxt, "name", None) not in ["h2", "h3", "h4"]:
                if getattr(nxt, "name", None) in ["ul", "ol"]:
                    for li in nxt.find_all("li"):
                        t = sr_scrub_text(li.get_text(" "))
                        if t and 3 < len(t) < 150:
                            steps.append(t)
                    break
                elif getattr(nxt, "name", None) in ["p", "div"]:
                    t = sr_scrub_text(nxt.get_text(" "))
                    if t and 3 < len(t) < 200:
                        steps.append(t)
                elif getattr(nxt, "name", None) == "table":
                    for tr in nxt.find_all("tr"):
                        cells = [sr_scrub_text(c.get_text(" "))
                                 for c in tr.find_all(["td", "th"])]
                        row_text = " / ".join(c for c in cells if c)
                        if row_text and 3 < len(row_text) < 150:
                            steps.append(row_text)
                    break
                nxt = nxt.next_sibling
            # I10 Strategy 4: inline text with separators (Written Test / Interview / DV)
            if not steps:
                inline = sr_scrub_text(h.find_next_sibling(string=True) or "")
                if inline and re.search(r'written\s*test|interview|document|medical|skill|merit', inline, re.I):
                    parts = re.split(r'\s*/\s*|\s+and\s+|\s*,\s*', inline)
                    steps = [p.strip() for p in parts if 3 < len(p.strip()) < 80]
            for s in steps[:10]:
                s = sr_scrub_text(s)
                if s and s not in out["selectionProcess"]:
                    out["selectionProcess"].append(s)

    # ── courseDetails — Course/Admission tables (BUG7: broader detection) ──
    _COURSE_HEAD_RE = re.compile(
        r"course\s*detail|admission\s*detail|course\s*wise|"
        r"admission\s*test|admissions?\s*details?|course\s*name", re.I)
    for table in scope.find_all("table"):
        rows = table.find_all("tr")
        chdr = None
        # BUG7 FIX: also treat as course table if a heading above it / its first
        # row mentions course/admission, even without eligib/group/seat keywords.
        _prev = table.find_previous(["h2", "h3", "h4", "td", "th"])
        _prev_txt = sr_scrub_text(_prev.get_text(" ")) if _prev else ""
        _table_is_course = bool(_COURSE_HEAD_RE.search(_prev_txt))
        for i, tr in enumerate(rows):
            cells = tr.find_all(["td", "th"])
            joined = " ".join(c.get_text(" ") for c in cells).lower()
            # STRICT: a real course table header must mention "course" (or trade/
            # admission), NOT just "post". A vacancy table header is
            # "Post Name | Total Post | ... Eligibility" — that contains "post" +
            # "eligib" but is NOT a course table. Exclude it so vacancy rows don't
            # get duplicated into courseDetails (SGPGI bug).
            # ALSO: the header must be SHORT column LABELS — a long data row that
            # merely contains the word "course" inside eligibility text
            # (e.g. "Diploma (2 yrs. course) in Radiography...") is NOT a header.
            _cell_texts = [sr_scrub_text(c.get_text(" ")) for c in cells]
            _is_short_hdr = (len(cells) >= 2 and
                             all(len(ct) <= 45 for ct in _cell_texts))
            # "Post Name" / "Trade Name" + Total = a VACANCY table, NOT a course
            # table. vacancyDetails already captures it. Treating it as a course
            # table duplicates the data AND mis-maps (Total Post → courseName).
            _is_vacancy_hdr = (
                ("post name" in joined or "trade name" in joined or
                 "trade" in joined or "post" in joined) and
                ("total post" in joined or "total" in joined))
            # a genuine course table header explicitly says "course"/"admission"
            _is_real_course_hdr = ("course name" in joined or
                                   "course" in joined or "admission" in joined)
            if (_is_real_course_hdr
                    and _is_short_hdr
                    and not _is_vacancy_hdr
                    and ("eligib" in joined or "group" in joined
                         or "seat" in joined or "duration" in joined
                         or "course name" in joined)):
                chdr = [ct.lower() for ct in _cell_texts]
                continue
            # BUG7: if table flagged as course table and first row is a header
            if (chdr is None and _table_is_course and i == 0 and len(cells) >= 2
                    and _is_short_hdr and not _is_vacancy_hdr):
                chdr = [ct.lower() for ct in _cell_texts]
                continue
            if chdr is None or i == 0:
                continue
            texts = [sr_scrub_text(c.get_text(" ")) for c in cells]
            texts = [t for t in texts if t]
            if len(texts) < 2:
                if out["courseDetails"]:
                    break
                continue
            obj = {}
            for j, val in enumerate(texts):
                col = chdr[j] if j < len(chdr) else f"col{j}"
                if "group" in col:        obj["group"] = val
                elif "course" in col or "trade" in col or "post" in col: obj["courseName"] = val
                elif "eligib" in col or "qualif" in col: obj["eligibility"] = val
                elif "seat" in col:       obj["totalSeats"] = re.sub(r"[^\d]", "", val) or val
                elif "duration" in col:   obj["duration"] = val
                else:                     obj[re.sub(r'[^a-z0-9]+','_',col).strip('_') or f"col{j}"] = val
            # require a usable course name
            if obj.get("courseName") and len(obj["courseName"]) >= 3:
                if not any(c.get("courseName","").lower() == obj["courseName"].lower()
                           for c in out["courseDetails"]):
                    out["courseDetails"].append(obj)
            elif obj and not _table_is_course:
                out["courseDetails"].append(obj)

    # ── ELIGIBILITY SECTION — "X Eligibility 2026 : detail" jaise blocks jo
    #    mega-table ki heading-cell me hote hain (e.g. NDA "UPSC NDA II
    #    Eligibility 2026 Army Wing : ... For Airforce & Naval Wing : ...").
    #    Ye structured vacancy/category table me nahi aate, isliye alag capture
    #    karke render karte hain (warna ye eligibility data gayab ho jata hai). ──
    _ELIG_HEAD_RE = re.compile(
        r"\beligibility\b\s*20\d\d?\b|qualification\s*details|"
        r"educational\s*qualification", re.I)
    _seen_elig = set()
    for tbl in scope.find_all("table"):
        for tr in tbl.find_all("tr"):
            for cell in tr.find_all(["td", "th"]):
                ctext = sr_scrub_text(cell.get_text(" "))
                if not ctext or len(ctext) < 25:
                    continue
                # must be an eligibility heading-cell, NOT age/date/fee/links
                if not _ELIG_HEAD_RE.search(ctext):
                    continue
                low = ctext.lower()
                if any(b in low for b in [
                        "age limit", "important date", "application fee",
                        "click here", "how to fill", "official website",
                        "some useful", "vacancy detail", "total post",
                        "category wise", "post name"]):
                    continue
                # split into "Label : value" parts (Army Wing : ... etc.)
                # strip the leading "X Eligibility 20xx" prefix
                body = re.sub(r"^.*?eligibility\s*20\d\d?\s*", "", ctext, flags=re.I).strip()
                if not body:
                    body = ctext
                # collect <li> items if present (cleaner), else split on " : "
                items = []
                lis = cell.find_all("li")
                if lis:
                    for li in lis:
                        t = sr_scrub_text(li.get_text(" "))
                        if t and len(t) > 4:
                            items.append(t)
                else:
                    # split "Army Wing : detail For Airforce & Naval Wing : detail"
                    parts = re.split(r"(?<=\.)\s+(?=[A-Z][A-Za-z &/]{2,40}\s*:)", body)
                    for p in parts:
                        p = sr_scrub_text(p)
                        if p and len(p) > 6:
                            items.append(p)
                if not items:
                    items = [body[:500]]
                sig = items[0][:50].lower()
                if sig in _seen_elig:
                    continue
                _seen_elig.add(sig)
                # heading = the "X Eligibility 20xx" prefix
                m = re.match(r"(.*?eligibility\s*20\d\d?)", ctext, re.I)
                head = sr_scrub_text(m.group(1)) if m else "Eligibility Details"
                head = re.sub(
                    r'(sarkari\s*result|www\.sarkariresult)[^\n]*', '', head,
                    flags=re.I).strip()
                out["eligibilitySection"].append(
                    {"heading": head, "items": [i[:500] for i in items]})

    # ── importantDates — DYNAMIC: "Important Dates" section ki har li ──────
    for h in scope.find_all(["h2", "h3", "h4"]):
        if re.search(r"important dates", h.get_text(" "), re.I):
            ul = h.find_next("ul")
            if ul:
                for li in ul.find_all("li"):
                    t = sr_scrub_text(li.get_text(" "))
                    m = re.match(r"(.+?)\s*[:：]\s*(.+)", t)
                    if m:
                        label = m.group(1).strip()
                        val = m.group(2).strip()
                        out["importantDatesExtra"][label] = val
            break

    # ── generic table capture (har table preserve — koi miss na ho) ────────
    try:
        out["allTables"] = _sr_generic_tables()
    except Exception:
        out["allTables"] = []

    return out


def sr_map_date_label(label):
    """Date label (free text) → camelCase importantDates key. Dynamic."""
    l = label.lower()
    if "answer key" in l:                          return "answerKeyDate"
    if "objection" in l:                           return "objectionDate"
    if "result" in l:                              return "resultDate"
    if "admit card" in l or "hall ticket" in l:    return "admitCardDate"
    if "noc" in l or "no objection" in l:          return "nocSubmissionLastDate"
    if "exam city" in l or "city detail" in l or "city avail" in l: return "examCityDate"
    if "skill test" in l:                          return "skillTestDate"
    if "vacancy increase" in l or "vacancy update" in l: return "vacancyUpdateDate"
    if "exam" in l and "date" in l:                return "examDate"
    if "exam" in l:                                return "examDate"
    if "interview" in l:                           return "interviewDate"
    if "counsel" in l:                             return "counselingStartDate"
    if "correction" in l:                          return "formCorrectionDate"
    if "fee" in l and ("last" in l or "pay" in l): return "lastDatePayFee"
    if "last date" in l or "closing" in l:         return "lastDateApplyOnline"
    if "begin" in l or "start" in l or "open" in l or "notification out" in l:
        return "applicationBegin"
    if "re-open" in l or "reopen" in l:            return "reOpenFormDate"
    if "dv" in l or "document verification" in l:  return "documentVerificationDate"
    if "pmt" in l or "pet" in l:                   return "pmtPetDate"
    # fallback: camelCase the label
    key = re.sub(r"[^a-z0-9]+", " ", l).strip().title().replace(" ", "")
    return (key[0].lower() + key[1:]) if key else ""


def sr_extract_physical_eligibility(soup, text):
    """Physical standards: Height, Chest, Weight, Vision, Running. dict ya {}.
    STRICT: sirf real physical-measurement rows lo. Mega-table me 'Physical
    Eligibility' heading hone se links/junk rows (Apply Online | Click Here,
    Post Name | Total Post) galti se na aaye."""
    result = {}
    KW = ["physical eligib", "physical standard", "physical test", "physical requirement",
          "physical measurement", "body measurement"]
    text_low = (text or "").lower()
    if not any(k in text_low for k in KW) and not any(
            k in text_low for k in ["height", "chest", "running"]):
        return result
    # what a REAL physical-measurement key looks like
    _PHYS_KEY = re.compile(
        r"^(height|chest|chest\s*expansion|weight|vision|eye\s*sight|"
        r"running|race|long\s*jump|high\s*jump|shot\s*put|pull[\s-]*up|"
        r"endurance|male|female|men|women|gender|category|standard)", re.I)
    # junk that must NEVER be treated as physical data
    _PHYS_JUNK = re.compile(
        r"click\s*here|apply\s*online|download|notification|official\s*website|"
        r"how\s*to\s*fill|video|telegram|whatsapp|join|sarkari\s*result|"
        r"useful|link|app\b|tools?|post\s*name|total\s*post|grand\s*total|"
        r"^\d+$", re.I)
    for table in soup.find_all("table"):
        ttext = table.get_text(" ", strip=True).lower()
        # table must mention a real physical measurement value (cm/kg/cms)
        if not any(k in ttext for k in ["height", "chest", "weight", "vision", "running"]):
            continue
        if not re.search(r"\d+\s*(cm|cms|kg|kgs|mtr|meter|km|feet|ft)\b", ttext):
            continue  # no real measurement value → not a physical table
        for tr in table.find_all("tr"):
            cols = [sr_scrub_text(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            cols = [c for c in cols if c]
            if len(cols) < 2 or len(cols[0]) >= 40:
                continue
            label = cols[0].strip()
            value = cols[1].strip()
            # REJECT junk rows
            if _PHYS_JUNK.search(label) or _PHYS_JUNK.search(value):
                continue
            # value must contain a measurement OR the label must be a real phys key
            if not (_PHYS_KEY.match(label) or
                    re.search(r"\d+\s*(cm|cms|kg|mtr|km|feet|ft|year)", value, re.I)):
                continue
            if SR_BRAND_TEXT_RE.search(cols[0]):
                continue
            key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40]
            if key and value:
                result.setdefault(key, value[:200])
    if not result:
        for pat, key in [(r"Height\s*[:\-]?\s*(.{3,80}?)(?:\n|$)", "height"),
                         (r"Chest\s*[:\-]?\s*(.{3,80}?)(?:\n|$)", "chest"),
                         (r"Weight\s*[:\-]?\s*(.{3,80}?)(?:\n|$)", "weight"),
                         (r"Vision\s*[:\-]?\s*(.{3,80}?)(?:\n|$)", "vision")]:
            m = re.search(pat, text or "", re.I)
            if m:
                v = sr_scrub_text(m.group(1))
                # only keep if it has a real measurement
                if v and re.search(r"\d+\s*(cm|cms|kg|mtr|km|feet|ft)", v, re.I):
                    result[key] = v[:200]
    return result


def sr_extract_documents_required(soup, text):
    """Documents Required → list."""
    KW = ["document required", "required document", "documents needed",
          "documents to be submitted", "document need"]
    if not any(k in (text or "").lower() for k in KW):
        return []
    docs, seen = [], set()
    for tag in soup.find_all(["h2", "h3", "h4", "p", "strong", "b"]):
        ht = clean(tag.get_text()).lower()
        if not any(k in ht for k in KW):
            continue
        for sib in tag.next_siblings:
            if not hasattr(sib, "name"):
                continue
            if sib.name in ["h2", "h3", "h4"]:
                break
            if sib.name in ["ul", "ol"]:
                for li in sib.find_all("li"):
                    t = sr_scrub_text(li.get_text(" "))
                    if t and t not in seen and not SR_BRAND_TEXT_RE.search(t) and len(t) > 4:
                        seen.add(t)
                        docs.append(t)
            if len(docs) > 20:
                break
        if docs:
            break
    return docs[:20]


def sr_extract_exam_pattern(soup, text):
    """Exam Pattern / Scheme tables → list of {headers, rows}."""
    KW = ["exam pattern", "exam scheme", "test pattern", "marking scheme",
          "paper pattern", "examination scheme"]
    if not any(k in (text or "").lower() for k in KW):
        return []
    result = []
    for table in soup.find_all("table"):
        ttext = table.get_text(" ").lower()
        if not any(k in ttext for k in ["subject", "marks", "question", "duration", "paper"]):
            continue
        prev = ""
        for sib in table.find_previous_siblings():
            if hasattr(sib, "get_text"):
                prev = clean(sib.get_text()).lower()
                break
        if not (any(k in ttext[:300] for k in KW) or any(k in prev for k in KW)):
            continue
        headers, rows = [], []
        for tr in table.find_all("tr"):
            cols = [sr_scrub_text(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            cols = [c for c in cols if c]
            if not cols:
                continue
            if not headers and all(len(c) < 60 for c in cols):
                headers = cols
            else:
                rows.append(cols)
        if rows:
            result.append({"headers": headers, "rows": rows[:20]})
    return result[:3]


def sr_final_brand_clean(text):
    """Post-extraction final branding residue cleanup (str ya list)."""
    PATS = [
        r"Join\s+Us\b[^\n.]*", r"Follow\s+X\b[^\n.]*",
        r"Follow\s+[A-Z][a-zA-Z\s]{3,50}(?:Pradesh|Commission|Board|Limited|India|Ministry)[^\n.]*",
        r",\s*the\s+official\s+website\s+for[^.]*\.?",
        r"always\s+visit\s+[^,.\n]*[,.]?",
        r"For\s+the\s+latest\s+updates\s+on\s*[,.]",
        r"\(\s*\)", r"®\s*", r"\(since\s*201\d\)",
    ]
    def _one(t):
        for p in PATS:
            t = re.sub(p, " ", t, flags=re.I)
        return re.sub(r"\s{2,}", " ", t).strip(" .,|-")
    if isinstance(text, list):
        out = []
        for it in text:
            c = _one(sr_scrub_text(it))
            if len(c) > 18:
                out.append(c)
        return out
    return _one(sr_scrub_text(text or ""))


def sr_extract_all_named_sections(soup, text):
    """
    Universal dynamic section extractor — koi bhi named section detect + extract.
    Returns {output_key: {"type": "list"|"table", "content": ...}}.
    """
    SECTION_KEYS = {
        "selection process": "selectionProcess", "selection criteria": "selectionProcess",
        "mode of selection": "selectionProcess",
        "document required": "documentsRequired", "required document": "documentsRequired",
        "physical eligib": "physicalEligibility", "physical standard": "physicalEligibility",
        "physical test": "physicalEligibility", "physical measurement": "physicalEligibility",
        "exam pattern": "examPattern", "exam scheme": "examPattern", "marking scheme": "examPattern",
        "important instruction": "importantInstructions", "important note": "importantInstructions",
        "general instruction": "importantInstructions",
    }
    result = {}
    scope = soup.find("div", class_="entry-content") or soup.find("article") or soup.body
    if not scope:
        return result
    for tag in scope.find_all(["h1", "h2", "h3", "h4", "h5", "strong", "b"]):
        tt = clean(tag.get_text())
        tl = tt.lower()
        if not tt or len(tt) < 4 or len(tt) > 120 or SR_BRAND_TEXT_RE.search(tt):
            continue
        mk = None
        for kw, ok in SECTION_KEYS.items():
            if kw in tl:
                mk = ok
                break
        if not mk or mk in result:
            continue
        items, tables_found, cc = [], [], 0
        for sib in tag.next_siblings:
            if not hasattr(sib, "name"):
                continue
            if sib.name in ["h2", "h3", "h4", "h5"]:
                break
            if sib.name == "table":
                hdr, rows = [], []
                for tr in sib.find_all("tr"):
                    cols = [sr_scrub_text(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
                    cols = [c for c in cols if c and not SR_BRAND_TEXT_RE.search(c)]
                    if not cols:
                        continue
                    if not hdr and all(len(c) < 80 for c in cols):
                        hdr = cols
                    else:
                        rows.append(cols)
                if rows:
                    tables_found.append({"headers": hdr, "rows": rows[:30]})
            elif sib.name in ["ul", "ol"]:
                for li in sib.find_all("li"):
                    t = sr_scrub_text(li.get_text(" "))
                    if t and not SR_BRAND_TEXT_RE.search(t) and len(t) > 3:
                        items.append(t)
                        cc += len(t)
            elif sib.name in ["p", "div"]:
                t = sr_scrub_text(sib.get_text(" "))
                if t and len(t) > 5 and not SR_BRAND_TEXT_RE.search(t):
                    items.append(t)
                    cc += len(t)
            if cc > 1500:
                break
        if tables_found:
            result[mk] = {"type": "table", "content": tables_found}
        elif items:
            result[mk] = {"type": "list", "content": items[:20]}
    return result


def sr_scrape_detail(category, url):
    soup = sr_load_page(url)
    if not soup:
        return None
    text  = sr_get_full_text(soup)
    title = sr_extract_title(soup)

    # PRIMARY: HTML table structure parser (SarkariResult specific)
    # SarkariResult pages pe H2/H3 headings aur UL/LI sections HTML tables
    # ke TD cells ke andar hote hain.
    parsed = sr_parse_main_table_sections(soup)

    # FALLBACK: text-based parsers
    text_based_dates = sr_extract_important_dates_structured(text)
    text_based_fee   = sr_extract_application_fee_structured(text)
    text_based_age   = sr_extract_age_limit_structured(text)
    vacancy_struct   = sr_extract_vacancy_details_structured(soup, text)
    faq              = sr_extract_faq(soup, text)
    tables           = sr_extract_tables(soup)
    text_sections    = sr_extract_text_sections(soup)

    # Merge: HTML parser (primary) + text parser (fallback fills gaps)
    imp_dates = parsed["important_dates"]
    for k, v in text_based_dates.items():
        if k not in imp_dates and v:
            imp_dates[k] = v

    app_fee = parsed["application_fee"]
    for k, v in text_based_fee.items():
        if k not in app_fee and v:
            app_fee[k] = v

    age_limit = parsed["age_limit"]
    for k, v in text_based_age.items():
        if k not in age_limit and v:
            age_limit[k] = v
    if not age_limit or all(k in ["details", "as_on_date"] for k in age_limit):
        fallback_age = sr_age_fallback_from_faq_tables(faq, tables, text)
        if fallback_age:
            age_limit = fallback_age

    html_vacancy = parsed["vacancy_details"]
    if html_vacancy.get("post_wise"):
        final_vacancy = html_vacancy
        if not final_vacancy["total_post"] and vacancy_struct.get("total_post"):
            final_vacancy["total_post"] = vacancy_struct["total_post"]
    else:
        final_vacancy = vacancy_struct

    name_of_post = parsed["name_of_post"] or sr_extract_name_of_post(soup, text)
    short_info   = parsed["short_information"] or sr_extract_short_info(text)
    how_to_apply = parsed["how_to_apply"] or sr_extract_how_to_apply(text)

    useful_links = parsed["useful_links"]
    legacy_links = sr_extract_useful_links_structured(soup)
    for k, v in legacy_links.items():
        if k == "_all":
            # FIX: links value can be a list (unhashable) — normalize to tuple for set
            existing_hrefs = set()
            for i in useful_links.get("_all", []):
                lv = i.get("links")
                existing_hrefs.add(tuple(lv) if isinstance(lv, list) else lv)
            for item in v:
                lv = item.get("links")
                lv_key = tuple(lv) if isinstance(lv, list) else lv
                if lv_key not in existing_hrefs:
                    useful_links["_all"].append(item)
        elif k not in useful_links and v:
            useful_links[k] = v

    last_date = imp_dates.get("last_date_apply_online", "")
    if not last_date:
        legacy = sr_extract_dates(text)
        last_date = date_to_iso(legacy.get("last_date", ""))

    # ── useful_links → flat array of {title, url} ─────────────────────────
    useful_links_arr = []
    seen_urls = set()
    for item in useful_links.get("_all", []):
        tv = item.get("title", "")
        uv = item.get("links", "")
        # links/title list ho sakta hai → normalize to string
        if isinstance(tv, list):
            tv = tv[0] if tv else ""
        if isinstance(uv, list):
            uv = uv[0] if uv else ""
        title_v = str(tv).strip()
        url_v   = str(uv).strip()
        if title_v and url_v and url_v not in seen_urls:
            seen_urls.add(url_v)
            useful_links_arr.append({"title": title_v, "url": url_v})

    # ── text_sections — how_to_apply bhi include karo ─────────────────────
    text_sections_out = list(text_sections) if text_sections else []
    if how_to_apply:
        # How to apply section already parsed hai — text_sections mein add karo
        # agar duplicate nahi hai
        how_section = {
            "section": "How to Fill / How to Apply",
            "content": how_to_apply,
        }
        # Check if already present
        existing_sections = [s.get("section","").lower() for s in text_sections_out]
        if not any("how to" in s for s in existing_sections):
            text_sections_out.append(how_section)

    # Category detection — content-first (hint verify/override per prompt STEP 1)
    content_cat = sr_resolve_category("", title, url)   # purely content-based
    if category in SR_VALID_CATEGORIES:
        # hint valid hai — par agar content clearly kuch aur kehta hai to override
        title_low = (title or "").lower()
        strong_signal = (
            ("answer key" in title_low and content_cat == "SR_Answer_Key") or
            ("admit card" in title_low and content_cat == "SR_Admit_Card") or
            ("result" in title_low and content_cat == "SR_Result")
        )
        detected = content_cat if (strong_signal and content_cat != category) else category
    else:
        detected = content_cat
    overridden = (category in SR_VALID_CATEGORIES and detected != category)
    safe_category = detected

    # ── importantDates (snake → camel) ─────────────────────────────────────
    DATE_MAP = {
        "application_begin":      "applicationBegin",
        "last_date_apply_online": "lastDateApplyOnline",
        "last_date_pay_fee":      "lastDatePayFee",
        "correction_date":        "formCorrectionDate",
        "exam_date":              "examDate",
        "admit_card_available":   "admitCardDate",
        "admit_card_date":        "admitCardDate",
        "result_date":            "resultDate",
        "answer_key_date":        "answerKeyDate",
        "objection_date":         "objectionDate",
        "interview_date":         "interviewDate",
        "dv_date":                "documentVerificationDate",
        "counseling_start":       "counselingStartDate",
        "counselling_start":      "counselingStartDate",
        "pmt_pet_date":           "pmtPetDate",
        "re_open_form_date":      "reOpenFormDate",
        "skill_test_date":        "skillTestDate",
        "noc_submission_last_date": "nocSubmissionLastDate",
        "noc_last_date":          "nocSubmissionLastDate",
        "noc_date":               "nocSubmissionLastDate",
        "exam_city_date":         "examCityDate",
        "exam_city_available":    "examCityDate",
        "vacancy_update_date":    "vacancyUpdateDate",
        "document_verification_date": "documentVerificationDate",
        "counseling_date":        "counselingDate",
    }
    important_dates = {}
    other_dates = {}
    for k, v in (imp_dates or {}).items():
        if not v or k in ("_", "raw"):
            continue
        val = sr_scrub_text(str(v))
        if not val:
            continue
        if k in DATE_MAP:
            important_dates.setdefault(DATE_MAP[k], val)
        else:
            ck = re.sub(r"_([a-z])", lambda m: m.group(1).upper(), k)
            other_dates.setdefault(ck, val)

    # DYNAMIC dates — "Important Dates" section ki har li (jo upar miss hui)
    deep = sr_deep_extract(soup)
    for label, val in deep.get("importantDatesExtra", {}).items():
        val = sr_scrub_text(val)
        if not val:
            continue
        ck = sr_map_date_label(label)
        if ck and ck not in important_dates and ck != "otherDates":
            important_dates[ck] = val
    if other_dates:
        important_dates["otherDates"] = other_dates

    # ── applicationFee (snake → camel + isFree) ────────────────────────────
    FEE_MAP = {
        "general": "general", "gen": "general", "ur": "general",
        "general_obc_ews": "general", "general_obc": "general",
        "obc": "obc", "sc": "sc", "st": "st", "ews": "ews",
        "sc_st": "sc", "female": "female", "women": "female",
        "ex_serviceman": "exServiceman", "exsm": "exServiceman",
        "ph": "ph", "pwd": "ph", "ph_divyang": "ph", "divyang": "ph",
        "nil_ph": "ph", "ph_nil": "ph", "pwbd": "ph",
        # I4 FIX: gender-split fee keys (CBI Apprentice type)
        "for_male_candidate_general_obc_ews": "generalMale",
        "for_female_candidate_general_obc_ews": "generalFemale",
        "for_male_candidate_general_obc": "generalMale",
        "for_female_candidate_general_obc": "generalFemale",
        "for_male_candidate_sc_st": "scMale",
        "for_female_candidate_sc_st": "scFemale",
        "for_male_female_candidate_ph_transgender": "ph",
        "for_all_candidates_ncc_special_entry": "nccSpecial",
        "for_all_candidate": "general",
        "male_candidate": "generalMale",
        "female_candidate": "generalFemale",
        "payment_mode": "paymentMode",
    }
    application_fee = {}
    for k, v in (app_fee or {}).items():
        if not v or k in ("_", "raw"):
            continue
        if k == "fee_note":
            if re.search(r"no\s*(?:application)?\s*fee|nil|free", str(v), re.I):
                application_fee["isFree"] = True
            continue
        ck = FEE_MAP.get(k)
        if not ck:
            ck = re.sub(r"_([a-z])", lambda m: m.group(1).upper(), k)
        if ck == "paymentMode":
            application_fee.setdefault("paymentMode", sr_scrub_text(str(v)))
        else:
            application_fee.setdefault(ck, sr_clean_num(v))
    # I4 FIX: any remaining verbose keys (forMaleCandidate...) → short camelCase
    _ugly = {k: v for k, v in list(application_fee.items())
             if re.match(r'^(forMale|forFemale|forAll|forMaleFemale|candidate)', k)}
    for k, v in _ugly.items():
        application_fee.pop(k, None)
        k_low = re.sub(r'([A-Z])', r'_\1', k).lower().lstrip('_')
        if 'male' in k_low and 'female' not in k_low and 'general' in k_low:
            application_fee.setdefault('generalMale', v)
        elif 'female' in k_low and 'general' in k_low:
            application_fee.setdefault('generalFemale', v)
        elif 'ph' in k_low or 'transgender' in k_low:
            application_fee.setdefault('ph', v)
        elif 'sc' in k_low or 'st' in k_low:
            application_fee.setdefault('sc', v)
        else:
            short = re.sub(r'(for|candidate|male|female|all|the)', '', k_low)
            short = re.sub(r'_+', '_', short).strip('_')
            if short:
                ck2 = re.sub(r'_([a-z])', lambda m: m.group(1).upper(), short)
                application_fee.setdefault(ck2[:20], v)

    # isFree auto: agar saari fee 0
    fee_nums = [application_fee[k] for k in application_fee
                if k not in ("paymentMode", "isFree")]
    if fee_nums and all(str(x) in ("0", "") for x in fee_nums):
        application_fee["isFree"] = True

    # ── ageLimit (snake → camel) ───────────────────────────────────────────
    AGE_MAP = {
        "minimum_age": "minAge", "min_age": "minAge",
        "maximum_age": "maxAge", "max_age": "maxAge",
        "as_on_date": "ageAsOnDate", "relaxation": "relaxation",
        "age_relaxation": "relaxation",
    }
    age_limit_out = {}
    for k, v in (age_limit or {}).items():
        if not v or k in ("_", "raw", "value"):
            continue
        ck = AGE_MAP.get(k)
        if ck:
            age_limit_out.setdefault(ck, sr_clean_num(v) if ck in ("minAge", "maxAge")
                                     else sr_scrub_text(str(v)))
        else:
            ck2 = re.sub(r"_([a-z])", lambda m: m.group(1).upper(), k)
            age_limit_out.setdefault(ck2, sr_scrub_text(str(v)))

    # ── vacancyDetails / courseDetails / importantLinks / faq / additionalData ─
    vacancy_out = sr_build_vacancy(final_vacancy)
    # deep trade/post-wise vacancy zyada rich ho to use karo
    deep_vac = deep.get("vacancyDetails", [])
    if deep_vac and (len(deep_vac) > len(vacancy_out) or
                     any(v.get("postName") for v in deep_vac)):
        vacancy_out = deep_vac
    course_out = deep.get("courseDetails", [])
    subject_wise = deep.get("subjectWiseVacancy", [])
    subject_urls = deep.get("subjectLinkUrls", set())
    # PAGE-WIDE links + useful_links merge → dedup by URL
    page_links = sr_collect_all_links(soup)
    merged_links = list(useful_links_arr or []) + page_links
    important_links_out = sr_build_important_links(merged_links)
    # url-less / blocked / subject-wise-PDF entries hatao
    important_links_out = [l for l in important_links_out
                           if l.get("url") and sr_link_is_official(l["url"])
                           and l["url"] not in subject_urls
                           and not re.match(r"^\d+/\d{4}$", l.get("label", ""))]

    # FAQ junk patterns — vacancy table headers + comment/date noise
    _FAQ_JUNK_Q = re.compile(
        r"^(\d{2}/\d{2}/\d{4})"            # I5: date-pattern question
        r"|^(post\s*name|total\s*post|s\.?\s*no\.?|serial\s*no|"
        r"post\s*wise|sl\s*no|category|post\s*code)$"
        r"|comments?\s*(are\s*)?closed"
        r"|^\([^)]{1,30}\)$"               # FIX E: "(Karaikal)" "(Puducherry)" location-only
        r"|^[A-Z][a-z]+\s*\([A-Z][a-z]+\)$", re.I  # FIX E: "City (State)" fragments
    )
    # I6: empty/branding-shell answers (e.g. "through .", "Official of ®", "() –")
    _FAQ_EMPTY_A = re.compile(
        r"through\s*\.\s*$"
        r"|official\s*(of\s*)?®"
        r"|\(\s*\)\s*[–\-]"
        r"|®\s*$"
        r"|\(\s*\)\s*$"
        r"|^\s*\.\s*$", re.I
    )
    _FAQ_JUNK_A = re.compile(
        r"^comments?\s*(are\s*)?closed"
        r"|^(total\s*post|post\s*name|eligibility|qualification|"
        r"vacancy|pay\s*scale|s\.?\s*no\.?)$"
        r"|^\([^)]{1,30}\)$", re.I    # FIX E: location-only answers too
    )

    def _is_valid_faq(q_text, a_text):
        # FIX E: FAQ quality gate
        if not q_text or not a_text:
            return False
        if _FAQ_JUNK_Q.search(q_text.strip()):
            return False
        if _FAQ_EMPTY_A.search(a_text.strip()) or _FAQ_JUNK_A.match(a_text.strip()):
            return False
        # a real FAQ question is ≥20 chars OR contains a "?"
        if len(q_text.strip()) < 20 and '?' not in q_text:
            return False
        return True

    faq_out = []
    _faq_seen = set()
    for q in (faq or []):
        if isinstance(q, dict):
            ques = sr_scrub_text(q.get("question", ""))
            ans  = sr_scrub_text(q.get("answer", ""))
            # FIX E: single quality gate (junk Q, empty/junk A, location fragments, min-length)
            if not _is_valid_faq(ques, ans):
                continue
            if ques and ans:
                # normalize: 'Q1.'/'Q2)' prefix hatao taaki duplicate na aaye
                norm = re.sub(r"^q?\d+[.\):]\s*", "", ques, flags=re.I).strip().lower()
                if norm in _faq_seen:
                    continue
                _faq_seen.add(norm)
                # question se bhi Q-number prefix hata do (clean output)
                ques = re.sub(r"^q?\d+[.\):]\s*", "", ques, flags=re.I).strip()
                faq_out.append({"question": ques, "answer": ans})

    # selectionProcess — deep-extract se ya parsed se
    selection_out = []
    for s in (deep.get("selectionProcess") or parsed.get("selection_process") or []):
        s = sr_scrub_text(str(s))
        if s and s not in selection_out:
            selection_out.append(s)
    selection_out = selection_out[:10]

    additional = {}
    # howToApply — deep-extract ko priority
    ht_src = deep.get("howToApply") or how_to_apply
    if ht_src:
        ht = ht_src if isinstance(ht_src, list) else [ht_src]
        ht = [sr_scrub_text(x) for x in ht if sr_scrub_text(x)]
        # branding-only steps hatao
        ht = [x for x in ht if not re.search(r"sarkari\s*result|sarkariresult|since\s*201\d", x, re.I)]
        if ht:
            additional["howToApply"] = ht
    # extra labeled keys (dynamic) → additionalData, but CLEANED (no junk/dupe)
    extra_fields = sr_extract_extra_fields(soup)
    extra_clean = sr_clean_additional(extra_fields, important_dates,
                                      application_fee, age_limit_out, vacancy_out)
    for k, v in extra_clean.items():
        if k not in additional:
            additional[k] = v

    # I7 FIX: remove junk month_year keys (e.g. "july_2026", "augustUpdate2026")
    # artifacts from dynamic date-keyword extraction hitting FAQ/comment text
    _MONTH_YEAR_KEY = re.compile(
        r"^(january|february|march|april|may|june|july|august|"
        r"september|october|november|december|jan|feb|mar|apr|"
        r"jun|jul|aug|sep|oct|nov|dec)[a-z]*_?\d{4}$", re.I)
    for junk_k in [k for k in additional if _MONTH_YEAR_KEY.match(k)]:
        additional.pop(junk_k, None)

    # ── NEW dedicated extractors → additionalData ──────────────────────────
    physical_elig = sr_extract_physical_eligibility(soup, text)
    if physical_elig:
        additional["physicalEligibility"] = physical_elig
    docs_req = sr_extract_documents_required(soup, text)
    if docs_req:
        additional["documentsRequired"] = docs_req
    exam_pattern = sr_extract_exam_pattern(soup, text)
    if exam_pattern:
        additional["examPattern"] = exam_pattern

    # ── Universal named-section extractor (gap-filler) ─────────────────────
    named = sr_extract_all_named_sections(soup, text)
    if not selection_out and named.get("selectionProcess"):
        sc = named["selectionProcess"]["content"]
        selection_out = [x for x in (sc if isinstance(sc, list) else [str(sc)]) if x][:10]
    if "documentsRequired" not in additional and named.get("documentsRequired"):
        dc = named["documentsRequired"]["content"]
        if named["documentsRequired"]["type"] == "list":
            additional["documentsRequired"] = dc
    if "physicalEligibility" not in additional and named.get("physicalEligibility"):
        additional["physicalEligibility"] = named["physicalEligibility"]["content"]
    if "examPattern" not in additional and named.get("examPattern"):
        if named["examPattern"]["type"] == "table":
            additional["examPattern"] = named["examPattern"]["content"]
    if named.get("importantInstructions"):
        ic = named["importantInstructions"]["content"]
        if named["importantInstructions"]["type"] == "list":
            additional["importantInstructions"] = ic

    # I8 FIX: howToApply — remove branding tail fragments + final brand clean
    _HTA_TAIL_JUNK = re.compile(
        r"^(admit\s*card[,\s]*answer\s*key[,\s]*(and\s*)?result"
        r"|for\s*the\s*latest.*sarkari"
        r"|always\s*visit\s*sarkari"
        r"|official\s*website\s*for\s*sarkari\s*result"
        r"|sarkariresult\.com.*since\s*201\d"
        r"|visit\s*our\s*(official\s*)?website)", re.I)
    if additional.get("howToApply"):
        additional["howToApply"] = [
            step for step in additional["howToApply"]
            if not _HTA_TAIL_JUNK.search(step.strip())
        ]
        additional["howToApply"] = sr_final_brand_clean(additional["howToApply"])
        if not additional["howToApply"]:
            additional.pop("howToApply", None)

    # ── meta ───────────────────────────────────────────────────────────────
    meta = sr_build_meta(url, soup, title, detected, overridden)

    # title = actual post heading; organization = derive
    post_title = sr_scrub_text(name_of_post) or sr_scrub_text(title)
    organization = ""
    org_m = re.search(r"\(([A-Z]{2,8})\)", post_title) or \
            re.search(r"\b([A-Z]{2,8})\b", short_info or "")
    if org_m:
        organization = org_m.group(1)

    # totalPost: vacancy → warna title se number
    total_post = sr_clean_num(final_vacancy.get("total_post", "")) if isinstance(final_vacancy, dict) else ""
    if not total_post:
        tm = re.search(r"for\s+(\d[\d,]*)\s*post", post_title, re.I)
        if tm:
            total_post = tm.group(1).replace(",", "")

    # paymentMode sanitize — junk text hatao, clean payment modes raho
    if "paymentMode" in application_fee:
        pm = application_fee["paymentMode"]

        # Pattern 1: "Challan UPSSSC/UPPSC/SSC <recruitment name>" — pure junk, normalize
        challan_junk = re.match(
            r"^(challan)\s+(upsssc|uppsc|ssc|rrb|bpsc|hssc|dsssb|rpsc)\b",
            pm.strip(), re.I)
        if challan_junk:
            application_fee["paymentMode"] = "Offline E Challan"
        else:
            # Extract only payment-mode keywords, drop recruitment-name suffix
            PAYMENT_KWORDS = (
                r"(debit\s*card|credit\s*card|net\s*banking|upi|"
                r"e[\s-]?challan|challan|online|offline|"
                r"sbi\s*i[\s-]?collect|sbi\s*e[\s-]?pay|"
                r"e[\s-]?mitra|mobile\s*wallet|cash\s*card|"
                r"imps|neft|rtgs)"
            )
            found = re.findall(PAYMENT_KWORDS, pm, re.I)
            if found:
                seen_kw = set(); clean_parts = []
                for kw in found:
                    k = kw.strip().lower()
                    if k not in seen_kw:
                        seen_kw.add(k); clean_parts.append(kw.strip().title())
                application_fee["paymentMode"] = " / ".join(clean_parts)
            elif len(pm) > 100:
                application_fee.pop("paymentMode", None)

    # postDate — parsed se ya meta published time se
    post_date = (parsed.get("post_date") or parsed.get("name_of_post_table_date") or "")
    if not post_date:
        pub = meta.get("publishedTime", "")
        if pub:
            # ISO → DD/MM/YYYY readable
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", pub)
            if m:
                post_date = f"{m.group(3)}/{m.group(2)}/{m.group(1)}"

    # ── dataTables — PERMANENT CLEAN BUILD ─────────────────────────────────
    # vacancyDetails / subjectWiseVacancy / categoryWise / ageLimit /
    # importantDates / applicationFee / physicalEligibility ALL already capture
    # the structured data cleanly. dataTables ko sirf wahi rows rakhne hain jo
    # genuinely kisi structured field me NAHI gaye — aur har junk row
    # (dates / fee / how-to-fill / links / app / click here / branding) HAMESHA
    # drop. Isse site pe duplicate/mixed/wrong table kabhi nahi banegi.
    _ROW_JUNK = re.compile(
        r"important\s*date|application\s*fee|how\s*to\s*(fill|apply)|"
        r"some\s*useful|interested\s*candidate|download\s*the\s*sarkari|"
        r"sarkari\s*result\s*(android|apple|mobile|channel)|"
        r"join\s*sarkari|telegram|whatsapp|signature\s*resizer|"
        r"pdf\s*compress|age\s*calculat|"
        r"^app$|^click\s*here$|official\s*website\s*of|"
        r"result®|since\s*201\d|^app\b|"
        r"^apply\s*online$|^download\b|notification\s*:?\s*$|"
        r"for\s*the\s*latest\s*updates", re.I)
    # headings whose data is ALREADY structured elsewhere → skip whole table
    _STRUCT_TBL = re.compile(
        r"subject.?wise|course detail|important link|useful link|"
        r"application fee|important date|vacancy detail|category\s*wise|"
        r"eligibility detail|physical eligib|age limit|how to (fill|apply)|"
        r"selection process|pay scale|salary", re.I)

    vac_post_set = {(v.get("postName") or "").strip().lower()
                    for v in vacancy_out if isinstance(v, dict)}
    # all eligibility/subjects text already captured → use to detect duplicates
    _captured_text = set()
    for v in vacancy_out:
        if isinstance(v, dict):
            for fld in ("eligibility", "subjects"):
                tv = (v.get(fld) or "").strip().lower()
                if len(tv) > 20:
                    _captured_text.add(tv[:60])

    def _row_is_junk(row):
        blob = " ".join(str(c) for c in row).strip()
        if not blob:
            return True
        # link-only row: 2 cells where 2nd is "Click Here"/"Official Website"
        if len(row) == 2 and re.fullmatch(
                r"(click\s*here|official\s*website|telegram\s*\|?\s*whatsapp|"
                r"english\s*\|?\s*hindi|sarkari\s*result.*)",
                str(row[1]).strip(), re.I):
            return True
        if _ROW_JUNK.search(blob):
            return True
        # single-cell SECTION-HEADING rows ("... : Eligibility Details",
        # "... : Age Limit Details", "... Notification 2026 : ...") — these are
        # heading rows of a section already captured structurally → drop.
        if len([c for c in row if str(c).strip()]) == 1 and re.search(
                r":\s*(eligibility|age\s*limit|vacancy|physical|category|"
                r"subject|selection|exam\s*pattern|important\s*date|"
                r"application\s*fee)\b|notification\s*20\d\d\s*:|"
                r"recruitment\s*20\d\d\s*:|exam\s*20\d\d\s*:", blob, re.I):
            return True
        # column-header rows (Post Name | ... | Eligibility / Total / Subjects)
        _bl = blob.lower()
        if ("post name" in _bl and
                any(k in _bl for k in ["eligib", "total", "subject", "qualif",
                                       "age", "department"])):
            return True
        # "Join Channel" / app / single short junk
        if re.fullmatch(r"(join\s*channel|app|tools?|"
                        r"sarkari\s*result\s*tools?)", blob.strip(), re.I):
            return True
        # row already captured as eligibility/subjects
        for c in row:
            cl = str(c).strip().lower()[:60]
            if cl in _captured_text:
                return True
        return False

    data_tables = []
    for t in deep.get("allTables", []):
        heading = (t.get("heading") or "")
        rows = t.get("rows", [])
        if not rows:
            continue
        # skip tables whose heading is already a structured section
        if heading and _STRUCT_TBL.search(heading):
            continue
        # vacancyDetails overlap (same post-names) → already captured → skip
        if vac_post_set:
            first_col = {(r[0].strip().lower() if r else "") for r in rows}
            overlap = first_col & vac_post_set
            if len(overlap) >= max(1, len(rows) // 2):
                continue
        # CLEAN the rows: drop every junk row
        clean_rows = [r for r in rows if not _row_is_junk(r)]
        # need at least 2 meaningful rows AND at least one multi-column data row
        _multi = [r for r in clean_rows if len([c for c in r if str(c).strip()]) >= 2]
        if len(clean_rows) < 1 or not _multi:
            continue
        t = dict(t)
        t["rows"] = clean_rows
        data_tables.append(t)

    out = {
        "category":          safe_category,
        "title":             post_title,
        "postDate":          post_date,
        "organization":      organization,
        "totalPost":         total_post,
        "shortInfo":         sr_final_brand_clean(sr_clean_shortinfo(short_info)),
        "importantDates":    important_dates,
        "applicationFee":    application_fee,
        "ageLimit":          age_limit_out,
        "vacancyDetails":    vacancy_out,
        "subjectWiseVacancy": subject_wise,
        "eligibilitySection": deep.get("eligibilitySection", []),
        "courseDetails":     course_out,
        "dataTables":        data_tables,
        "selectionProcess":  selection_out,
        "textSections":      text_sections_out,   # B1 FIX: was computed but never added
        "importantLinks":    important_links_out,
        "additionalData":    additional,
        "faq":               faq_out,
        "meta":              meta,
    }

    # FIX 10 — category-specific dedicated URL shortcuts
    def _find_link(*kw):
        for l in important_links_out:
            lab = l.get("label", "").lower()
            if any(k in lab for k in kw):
                return l.get("url", "")
        return ""
    if safe_category == "SR_Admit_Card":
        u = _find_link("admit", "hall ticket", "call letter")
        if u: out["admitCardUrl"] = u
    elif safe_category == "SR_Result":
        u = _find_link("result", "merit", "scorecard")
        if u: out["resultUrl"] = u
    elif safe_category == "SR_Answer_Key":
        # BUG6 FIX (v2): broader match for answer-key link variants
        u = (_find_link("answer key") or
             _find_link("download answer") or
             _find_link("revised answer") or
             _find_link("answer") or
             _find_link("question paper") or
             _find_link("objection"))
        if u: out["answerKeyUrl"] = u

    # FINAL SCRUB + prune empties + category-first guarantee
    out = sr_scrub_obj(out)
    out = sr_prune_empty(out)
    out = {"category": safe_category, **{k: v for k, v in out.items() if k != "category"}}
    # NOTE: meta.sourceUrl deliberately NOT restored — user rule: jis site se
    # scrape ho rahi (sarkariresult.com) uska koi link/naam output me nahi aana chahiye.
    return out

SN_STATE_JOB_URL   = "https://sarkarinetwork.com/state-job/"
SN_CENTRAL_JOB_URL = "https://sarkarinetwork.com/central-job/"
SN_UPCOMING_URL    = "https://sarkarinetwork.com/upcoming/"
SN_ADMISSION_URL   = "https://sarkarinetwork.com/Admission/"

SN_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def sn_get_soup(url):
    try:
        r = requests.get(url, headers=SN_HEADERS, timeout=30)
        print("  SN STATUS:", r.status_code)
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print("  SN REQUEST ERROR:", e)
        return None


def sn_clean_text(text):
    if not text:
        return ""
    remove_words = [
        "SarkariNetwork.Com", "Sarkari Network",
        "sarkarinetwork.com", "WWW.SARKARINETWORK.COM",
        "Free Job Alert", "Sarkari Result", "WWW."
    ]
    for word in remove_words:
        text = re.sub(re.escape(word), "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sn_slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def sn_clean_soup(soup):
    for tag in soup(["script", "style", "noscript", "iframe", "svg",
                     "header", "footer", "nav", "aside", "form", "ins"]):
        tag.decompose()
    return soup


def sn_is_bad_link(url):
    if not url:
        return True
    bad = ["whatsapp", "telegram", "facebook", "twitter", "instagram", "youtube"]
    url = url.lower()
    return any(b in url for b in bad)


def sn_is_internal_scrap_link(url):
    """
    True agar link block karna hai.

    Block karo:
      - SarkariNetwork ke internal navigation/category/tag pages
      - Social media, messaging apps

    ALLOW karo:
      - SarkariNetwork ke hosted PDFs / notification files
        (e.g. /wp-content/uploads/*.pdf, /notification/, /download/)
      - Koi bhi external government / official URL
    """
    import re as _re_sn
    if not url:
        return True
    url_l = url.lower().strip()

    # Social/messaging — hamesha block
    social = ["whatsapp", "telegram", "facebook", "twitter", "instagram",
              "youtube", "youtu.be", "t.me"]
    if any(s in url_l for s in social):
        return True

    # SarkariNetwork URLs — sirf navigation pages block karo
    if "sarkarinetwork.com" in url_l or "sarkari.network" in url_l:
        # ALLOW: PDF/document/notification links hosted on SN
        sn_allow_patterns = [
            r"/wp-content/uploads/",   # hosted files
            r"\.pdf($|\?)",           # direct PDF
            r"/download",              # download pages
            r"/notification",          # notification pages
        ]
        for pat in sn_allow_patterns:
            if _re_sn.search(pat, url_l):
                return False           # allow karo
        # Block: category, tag, page, author, home navigation
        sn_block_patterns = [
            r"/category/", r"/tag/", r"/page/\d",
            r"/author/", r"/privacy", r"/contact",
            r"sarkarinetwork\.com/?$",  # homepage
        ]
        for pat in sn_block_patterns:
            if _re_sn.search(pat, url_l):
                return True            # block karo
        # Baaki SN links (like /central-jobs/job-slug/) — article pages — allow
        return False

    return False


def sn_is_valid_job_link(url):
    url = url.lower()
    blocked = ["/category/", "/tag/", "/page/", "/author/", "/privacy", "/contact"]
    for b in blocked:
        if b in url:
            return False
    keywords = ["recruitment", "vacancy", "online-form", "admission", "cet",
                "group-d", "jobs", "notification", "exam", "re-evaluation", "posts"]
    return any(k in url for k in keywords)


def sn_detect_important_links(text, href, important_links):
    lower = text.lower()
    if sn_is_bad_link(href) or sn_is_internal_scrap_link(href):
        return
    if "apply" in lower or "online form" in lower or "apply now" in lower:
        important_links["apply_online"] = href
    elif "full notification" in lower or "english" in lower or "hindi" in lower:
        # "English / Hindi" cell = full notification link
        important_links["full_notification"] = href
    elif "short notification" in lower or (
            "download" in lower and "notification" not in important_links.get("full_notification","").lower()):
        # "Download" cell = short notification
        important_links["short_notification"] = href
    elif "official website" in lower or "visit now" in lower or "official" in lower:
        important_links["official_website"] = href
    elif "notification" in lower or "advertisement" in lower or "advt" in lower:
        important_links["notification"] = href


def sn_extract_job_links():
    from urllib.parse import urljoin as _urljoin
    print("\n  Fetching SarkariNetwork Upcoming Jobs...")
    soup = sn_get_soup(SN_START_URL)
    if not soup:
        return []
    soup = sn_clean_soup(soup)
    job_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = _urljoin(SN_BASE_URL, href).split("?")[0].split("#")[0]
        if sn_is_valid_job_link(full_url) and full_url not in job_links:
            job_links.append(full_url)
    return job_links


def _sn_is_meta_overview_table(rows_data):
    """
    True agar ye sarkarinetwork ka meta-info table hai jo scrape nahi karna:
    - Pehla row: Form Mode | Job State | Total Posts | Job Type
    - Ya pehla row: Title/Short Details merged cell + baaki rows mein
      Important Dates, Application Fees, Age Limit, Selection Process sab ek table mein

    Ye table listing page ka overview widget hota hai — saari info
    proper sections mein alag se duplicate aa jaati hai. Skip karo.
    """
    if not rows_data:
        return False

    # Pattern 1: Header row = ["Form Mode", "Job State", "Total Posts", "Job Type"]
    first_row_texts = [cell.get("text","").strip().lower() for cell in rows_data[0]]
    meta_headers = {"form mode", "job state", "total posts", "job type"}
    if meta_headers.issubset(set(first_row_texts)):
        return True

    # Pattern 2: Single-cell merged row with "Short Details" in text
    # followed by single-cell rows for "Important Dates", "Application Fees" etc.
    # → entire notification packed into ONE table (sarkarinetwork summary widget)
    if len(rows_data) >= 4:
        section_heading_count = 0
        for row in rows_data:
            if len(row) == 1:
                txt = row[0].get("text", "").strip().lower()
                for keyword in ["important dates", "application fee", "age limit",
                                "selection process", "salary", "short details",
                                "application begin", "last date"]:
                    if keyword in txt:
                        section_heading_count += 1
                        break
        # 3+ section headings packed as single-cell rows = summary widget
        if section_heading_count >= 3:
            return True

    return False


def sn_scrape_job(url):
    from urllib.parse import urljoin as _urljoin
    print("  SN SCRAPING:", url)
    soup = sn_get_soup(url)
    if not soup:
        return None
    soup = sn_clean_soup(soup)

    # Title
    title = ""
    h1 = soup.find("h1")
    if h1:
        title = sn_clean_text(h1.get_text(" "))
    if not title:
        title_tag = soup.find("title")
        if title_tag:
            title = sn_clean_text(title_tag.get_text(" "))
    if not title:
        title = url.split("/")[-2].replace("-", " ").title()

    entry = soup.find("div", class_="entry-content")
    if not entry:
        return None

    data = {
        "category":        "UPCOMING_JOBS",
        "title":           title,
        "slug":            sn_slugify(title),
        "important_links": {},
        "sections":        []
    }

    current_section  = {"title": "Overview", "content": []}
    processed_tables = set()
    seen_paragraphs  = set()

    elements = entry.find_all(["h2", "h3", "h4", "p", "ul", "ol", "table"])

    for el in elements:

        if el.name in ["h2", "h3", "h4"]:
            if current_section["content"]:
                data["sections"].append(current_section)
            current_section = {
                "title":   sn_clean_text(el.get_text(" ")),
                "content": []
            }

        elif el.name == "p":
            text = sn_clean_text(el.get_text(" "))
            if not text or text in seen_paragraphs:
                continue
            seen_paragraphs.add(text)
            skip_words = ["post name", "total", "gen", "ews", "obc", "sc", "st",
                          "male", "female", "type", "content type", "issued on",
                          "source title", "source link"]
            if text.lower() in skip_words:
                continue
            current_section["content"].append({"type": "paragraph", "text": text})

        elif el.name in ["ul", "ol"]:
            items = []
            for li in el.find_all("li"):
                li_text = sn_clean_text(li.get_text(" "))
                if li_text and li_text not in items:
                    items.append(li_text)
            if items:
                current_section["content"].append({"type": "list", "items": items})

        elif el.name == "table":
            table_text = sn_clean_text(el.get_text(" "))
            if table_text in processed_tables:
                continue
            processed_tables.add(table_text)
            rows_data = []
            for row in el.find_all("tr"):
                cols     = row.find_all(["td", "th"])
                row_data = []
                for col in cols:
                    col_text = sn_clean_text(col.get_text(" "))
                    if not col_text:
                        continue
                    links = []
                    for a in col.find_all("a", href=True):
                        href      = _urljoin(url, a["href"]).split("?")[0]
                        link_text = sn_clean_text(a.get_text(" "))
                        if not link_text.strip():
                            continue
                        if link_text.lower() in ["www.", "www"]:
                            continue
                        if sn_is_bad_link(href) or sn_is_internal_scrap_link(href):
                            continue
                        links.append({"text": link_text, "url": href})
                        sn_detect_important_links(col_text, href, data["important_links"])
                    row_data.append({"text": col_text, "links": links})
                if row_data:
                    rows_data.append(row_data)
            if rows_data and not _sn_is_meta_overview_table(rows_data):
                current_section["content"].append({"type": "table", "rows": rows_data})

    if current_section["content"]:
        data["sections"].append(current_section)

    return data


# =========================================================
# SOURCE 4 — sarkarinetwork.com STATE JOB  (active only, top 100)
# SOURCE 5 — sarkarinetwork.com CENTRAL JOB (active only, top 100)
# SOURCE 6 — sarkarinetwork.com ADMISSION  (active only, top 50)
# =========================================================

# --- Domains whose links must be blocked (no sarkarinetwork internal links) ---
SN_NEW_BLOCK_DOMAINS = [
    # OWN SITE
    "sarkarinetwork.com", "sarkari.network",
    # SOCIAL MEDIA
    "telegram.org", "t.me", "telegram.me",
    "whatsapp.com", "wa.me",
    "facebook.com", "fb.me", "fb.com",
    "instagram.com",
    "youtube.com", "youtu.be",
    "twitter.com", "x.com",
    # APP STORES
    "play.google.com", "apps.apple.com", "itunes.apple.com",
    # OTHER SCRAPER SITES
    "sarkariresult.com", "sarkariresultshine.com",
    "rojgarresult.com", "sarkariresults.org.in",
    "ignouking.com", "rojgarhelper.com",
    "tinyurl.com",
]


SN_STATE_SLUGS = {
    "haryana", "rajasthan", "punjab", "delhi", "chandigarh", "bihar",
    "uttar-pradesh", "maharashtra", "uttarakhand", "madhya-pradesh",
    "himachal-pradesh", "gujarat", "tamil-nadu", "chhattisgarh", "telangana",
    "odisha", "kerala", "assam", "jharkhand", "west-bengal", "karnataka",
    "meghalaya", "tripura", "goa", "nagaland", "manipur", "arunachal-pradesh",
    "mizoram", "sikkim", "jammu-kashmir", "andhra-pradesh",
}

def sn_new_is_blocked_url(url):
    if not url:
        return True
    url_l = url.lower().strip()
    return any(d in url_l for d in SN_NEW_BLOCK_DOMAINS)


def sn_new_get_soup(url):
    last_err = None
    headers = dict(SN_HEADERS)
    headers["Accept-Encoding"] = "gzip, deflate"   # br/zstd avoid (requests decode nahi karta)
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=30,
                             allow_redirects=True)
            body = r.text or ""
            # garbage/compressed detection: HTML signature na ho to raw bytes try karo
            low = body[:2000].lower()
            if r.status_code == 200 and ("<html" in low or "<!doctype" in low
                                          or "<a " in low or "<body" in low):
                print(f"  [SN-FETCH] {url} → status=200 bytes={len(body)} OK")
                return BeautifulSoup(body, "html.parser")
            # content garbage? maybe wrong encoding — content bytes se manually decode
            if r.status_code == 200 and r.content:
                for enc in ("utf-8", "latin-1"):
                    try:
                        txt = r.content.decode(enc, errors="ignore")
                        if "<html" in txt[:2000].lower() or "<a " in txt[:3000].lower():
                            print(f"  [SN-FETCH] {url} → recovered via {enc}")
                            return BeautifulSoup(txt, "html.parser")
                    except Exception:
                        pass
                # brotli try (agar installed ho)
                try:
                    import brotli
                    txt = brotli.decompress(r.content).decode("utf-8", "ignore")
                    if "<html" in txt[:2000].lower():
                        print(f"  [SN-FETCH] {url} → recovered via brotli")
                        return BeautifulSoup(txt, "html.parser")
                except Exception:
                    pass
            last_err = f"status {r.status_code}, non-HTML body ({len(body)}b)"
            print(f"  [SN-FETCH] {url} → status={r.status_code} bytes={len(body)} "
                  f"(non-HTML — retrying)")
        except Exception as e:
            last_err = str(e)
        time.sleep(1.5 * (attempt + 1))
    print(f"  SN_NEW FETCH FAILED ({last_err}): {url}")
    return None


def sn_new_clean(text):
    """Strip SarkariNetwork branding + social mentions and normalise whitespace."""
    if not text:
        return ""
    text = SN_BRAND_RE.sub("", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"^[\s|:\-–—,]+|[\s|:\-–—,]+$", "", text)
    return text.strip()


# =========================================================
# SN ENGINE — branding filter, field detection, link mapping
# (Prompt v1.0 — sarkarinetwork State/Central/Admissions only)
# =========================================================

# STEP 7 — branding / social ZERO-TOLERANCE regex
SN_BRAND_RE = re.compile(
    r"sarkarinetwork(?:\.com)?|sarkari\s*network|"
    r"www\.sarkarinetwork\.com|"
    r"telegram|t\.me|whatsapp|wa\.me|facebook|fb\.me|instagram|"
    r"youtube|youtu\.be|twitter|x\.com|"
    r"join\s*(?:channel|now|group|us)|subscribe|"
    r"download\s*(?:our\s*)?app|mobile\s*app|"
    r"android\s*app|apple\s*ios|play\s*store|app\s*store|"
    r"google\s*play|since\s*201\d|a\s*job\s*information\s*portal",
    re.I,
)

# STEP 2A — known field label map (label variants → output key)
SN_FIELD_MAP = {
    "last_date": ["last date", "closing date", "end date", "apply last",
                  "last date to apply", "apply before", "apply upto", "apply till",
                  "submission last date", "final date", "close date",
                  "last date for apply", "apply up to"],
    "application_start": ["start date", "application start", "starting date",
                          "online start", "form start", "begin date", "apply start",
                          "apply from", "open date", "application begin",
                          "online form start", "registration start",
                          "notification out", "notification date"],
    "exam_date": ["exam date", "examination date", "written exam", "written test date",
                  "test date", "screening date", "exam schedule",
                  "examination schedule", "written test"],
    "interview_date": ["interview date", "interview schedule", "interview on",
                       "skill test date", "document verification date", "dv date",
                       "walk in", "walk-in", "counselling date", "dv & document"],
    "result_date": ["result date", "result declaration", "result out",
                    "result expected", "result announce"],
    "admit_card_date": ["admit card date", "admit card available", "hall ticket date",
                        "call letter date", "e-admit card", "admit card"],
    "total_vacancy": ["total post", "total vacancy", "total vacancies", "total posts",
                      "total seats", "number of posts", "no. of post", "no of post",
                      "total no of post", "vacancy"],
    "post_name": ["post name", "name of post", "designation",
                  "post/designation", "name of position"],
    "department": ["department", "organization", "board", "commission",
                   "ministry", "authority", "corporation"],
    "advt_no": ["advt no", "advertisement no", "notification no",
                "advt number", "advt.", "ref no", "reference no"],
    "age_limit": ["age limit", "minimum age", "maximum age",
                  "age relaxation", "upper age", "lower age",
                  "age as on", "age criteria"],
    "fee_general": ["general fee", "general/obc fee", "unreserved fee",
                    "general/obc/ews fee", "application fee", "gen fee", "ur fee",
                    "general (male)", "general male"],
    "fee_obc": ["obc fee", "obc/ews fee", "other backward",
                "bca / bcb / ews", "bca", "bcb", "bc-a", "bc-b"],
    "fee_sc_st": ["sc/st fee", "sc fee", "st fee", "sc/st/ph fee",
                  "reserved fee", "scheduled caste", "scheduled tribe",
                  "osc / dsc / esm", "osc/dsc/esm", "ph (divyang)", "ph divyang",
                  "pwd", "divyang"],
    "fee_female": ["female fee", "women fee", "girl fee", "female/sc/st", "all women",
                   "general (female)", "general female"],
    "fee_payment_mode": ["payment mode", "fee payment", "pay through",
                         "fee through", "payment method"],
    "qualification": ["qualification", "educational qualification", "education",
                      "eligibility", "required qualification", "minimum qualification",
                      "academic qualification", "educational eligibility"],
    "salary": ["salary", "pay scale", "pay band", "pay matrix",
               "remuneration", "stipend", "emoluments",
               "grade pay", "ctc"],
    "selection_process": ["selection process", "selection criteria",
                          "selection procedure", "mode of selection",
                          "selection mode", "recruitment process"],
    "application_mode": ["application mode", "apply mode",
                         "mode of application", "form mode",
                         "apply through", "apply via"],
    "job_location": ["job location", "posting location", "place of posting",
                     "work location", "job state"],
    "course_name": ["course name", "course", "trade", "trades", "programme", "program"],
    "admission_type": ["admission type", "admission based", "selection basis",
                       "merit based", "entrance based"],
}

# STEP 3A — link label → key map (first matching wins)
SN_LINK_LABEL_MAP = [
    (["apply online", "fill online", "online form", "apply here",
      "apply now", "register online", "fill form"], "apply_online"),
    (["notification", "advertisement", "advt", "official notice",
      "recruitment notice", "detailed notification"], "full_notification"),
    (["official website", "visit official", "official site",
      "visit now", "official portal"], "official_website"),
    (["admit card", "hall ticket", "call letter", "e-admit card", "admit-card"], "admit_card"),
    (["answer key", "provisional answer", "final answer key", "response sheet"], "answer_key"),
    (["result", "merit list", "final result", "selection list", "written result"], "result"),
    (["syllabus", "exam syllabus", "curriculum", "exam pattern", "pattern & syllabus"], "syllabus"),
    (["prospectus", "admission form", "admission notification", "counselling schedule"], "admission_form"),
    (["information brochure", "download pdf", "pdf download", "brochure"], "brochure"),
    (["login", "candidate login", "student login", "applicant login"], "login"),
    (["fee payment", "pay fee", "challan"], "fee_payment"),
    (["correction", "edit form", "modify application"], "correction_window"),
    (["cut off", "cutoff", "cut-off marks"], "cut_off"),
]


def sn_is_official_url(url):
    """Sirf official/non-blocked external URLs allow karo."""
    if not url or not url.startswith("http"):
        return False
    return not sn_new_is_blocked_url(url)


def sn_brand_scrub(obj):
    """
    Recursively: sarkarinetwork URL / branding / social — sab hatao.
    Official govt/edu links untouched.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            cv = sn_brand_scrub(v)
            if isinstance(cv, str) and cv.startswith("http") and sn_new_is_blocked_url(cv):
                continue
            out[k] = cv
        return out
    if isinstance(obj, list):
        res = []
        for it in obj:
            ci = sn_brand_scrub(it)
            if isinstance(ci, str) and ci.startswith("http") and sn_new_is_blocked_url(ci):
                continue
            res.append(ci)
        return res
    if isinstance(obj, str):
        if obj.startswith("http"):
            return "" if sn_new_is_blocked_url(obj) else obj
        return sn_new_clean(obj)
    return obj


def sn_extract_iso_date(text):
    """Text se date nikaalo, YYYY-MM-DD return. Range ho to last value."""
    if not text:
        return ""
    found = re.findall(
        r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}"
        r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}"
        r"|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}",
        text, re.I,
    )
    if not found:
        return ""
    raw = found[-1].strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d",
                "%d %b %Y", "%d %B %Y"):
        try:
            d = datetime.strptime(raw, fmt)
            if d.year < 2000:
                return ""
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def sn_match_field_key(label):
    """Label kis known field se match karta hai? Sabse specific (longest variant) match.
    key ya None return."""
    low = label.lower().strip()
    best_key = None
    best_len = 0
    for key, variants in SN_FIELD_MAP.items():
        for v in variants:
            if v in low and len(v) > best_len:
                best_key = key
                best_len = len(v)
    return best_key


def sn_auto_detect_new_fields(kv_pairs, captured_keys):
    """
    STEP 2B — Unknown labeled key:value pairs ko extra_fields ke liye capture karo.
    kv_pairs: list of (label, value). captured_keys: already-used field keys set.
    """
    AUTO_SKIP = ["click here", "visit", "www", "http", "sarkari", "network",
                 "follow", "join", "subscribe", "download app", "mobile app"]
    new_fields = {}
    for label, value in kv_pairs:
        key_raw = clean(label).lower()
        val_raw = clean(value)
        if len(key_raw) < 4 or not val_raw:
            continue
        if key_raw.replace(" ", "").isdigit():
            continue
        if any(p in key_raw for p in AUTO_SKIP):
            continue
        if SN_BRAND_RE.search(key_raw) or SN_BRAND_RE.search(val_raw):
            continue
        if val_raw.lower() in ("-", "click here", "na", "n/a"):
            continue
        if sn_match_field_key(key_raw):     # known field → skip
            continue
        field_key = re.sub(r"[^a-z0-9]+", "_", key_raw).strip("_")[:60]
        if field_key and field_key not in captured_keys and field_key not in new_fields:
            new_fields[field_key] = val_raw
    return new_fields


def sn_parse_vacancy_table(table):
    """STEP 6 — vacancy table → list of row dicts (header-keyed).
    Sirf genuine category-wise tables (3+ cols, UR/OBC/SC/ST header) parse karo."""
    rows = table.find_all("tr")
    headers = []
    out = []
    for row in rows:
        cells = row.find_all(["th", "td"])
        texts = [sn_new_clean(c.get_text(" ")) for c in cells]
        nonempty = [t for t in texts if t]
        joined = " ".join(texts).lower()
        is_header = (len(nonempty) >= 3) and (
            bool(row.find("th")) or
            sum(h in joined for h in ["ur", "obc", "sc", "st", "ews", "total", "gen"]) >= 2
        )
        if is_header and not headers:
            headers = [t.lower().replace(" ", "_") for t in texts]
            continue
        if headers and len(nonempty) >= 3:
            row_dict = {}
            for i, val in enumerate(texts):
                key = headers[i] if i < len(headers) and headers[i] else f"col_{i}"
                if val:
                    row_dict[key] = val
            if row_dict:
                out.append(row_dict)
    return out


def sn_is_active(item):
    """STEP 9 — last_date past → False (exclude). Missing → True."""
    last_date = item.get("last_date", "")
    if not last_date:
        return True
    try:
        return datetime.strptime(last_date, "%Y-%m-%d").date() >= TODAY.date()
    except Exception:
        return True


def sn_new_extract_listing_links(page_url, limit):
    """
    Listing page se top `limit` individual job/admission post links extract karo.
    Whole-page scan + raw-HTML regex fallback (robust against layout changes).
    """
    soup = sn_new_get_soup(page_url)
    if not soup:
        return []

    # nav/header/footer/sidebar noise hatao (par body links rakho)
    for tag in soup(["script", "style", "noscript", "iframe", "header",
                     "footer", "aside", "ins"]):
        tag.decompose()

    BLOCKED = ["/category/", "/tag/", "/page/", "/author/",
               "/privacy", "/contact", "/disclaimer", "/tools",
               "/active-applications", "/latest-job", "/offline-form",
               "/exam-date", "/admit-card", "/answer-key", "/result",
               "/state-job", "/central-job", "/admission",
               "/upcoming", "/rojgar-samachar", "/syllabus",
               "/question-paper", "/pinned-link", "/todays-updates",
               "/last-date-calendar", "/last-date-today",
               "/copy-post-list", "/govt-scheme", "/ignou", "/feed",
               "/?p=", "/wp-", "ignouking.com", "rojgarhelper.com",
               "facebook.com", "telegram", "whatsapp", "instagram",
               "youtube", "twitter", "x.com"]
    JOB_SLUG = re.compile(
        r"-(?:recruitment|vacancy|online-form|offline-form|bharti|exam|"
        r"posts?|form)-?\d{0,4}/?$|-20\d{2}/?$|/[a-z0-9-]+-20\d{2}/?$", re.I)

    def _accept(href):
        if not href:
            return None
        if not href.startswith("http"):
            href = "https://sarkarinetwork.com" + href
        href = href.split("?")[0].split("#")[0].rstrip("/")
        low = href.lower()
        if "sarkarinetwork.com" not in low:
            return None
        if any(p in low for p in BLOCKED):
            return None
        slug = href.rsplit("/", 1)[-1]
        if slug.lower() in SN_STATE_SLUGS:
            return None
        # homepage / bare domain skip
        if low.rstrip("/").endswith("sarkarinetwork.com"):
            return None
        if not (JOB_SLUG.search(href) or ("-" in slug and len(slug) > 8)):
            return None
        return href

    links, seen = [], set()

    # Pass 1: <a> tags whole page (order preserved)
    for a in soup.find_all("a", href=True):
        href = _accept(a["href"].strip())
        if href and href not in seen:
            seen.add(href)
            links.append(href)
        if len(links) >= limit:
            return links

    # Pass 2: raw-HTML regex fallback (agar <a> parse miss ho gaya)
    if len(links) < 3:
        try:
            raw = str(soup)
        except Exception:
            raw = ""
        for m in re.finditer(r'href=["\'](https?://(?:www\.)?sarkarinetwork\.com/[^"\']+)["\']', raw, re.I):
            href = _accept(m.group(1))
            if href and href not in seen:
                seen.add(href)
                links.append(href)
            if len(links) >= limit:
                break

    if not links:
        print(f"  [SN] WARNING: 0 links extracted from {page_url} "
              f"(page may be JS-rendered/bot-protected)")
    return links


def sn_new_scrape_detail(url, category):
    """
    Single job/admission detail page scrape karo.
    content-area div se saara relevant data extract karo.
    Only official external links (non-sarkarinetwork) keep karo.
    Returns dict or None.
    """
    soup = sn_new_get_soup(url)
    if not soup:
        return None

    # Remove noise tags
    for tag in soup(["script", "style", "noscript", "iframe", "ins",
                     "header", "nav", "aside"]):
        tag.decompose()

    # Title from h1
    title = ""
    h1 = soup.find("h1", class_="entry-title") or soup.find("h1")
    if h1:
        title = sn_new_clean(h1.get_text(" "))
    if not title:
        t = soup.find("title")
        if t:
            title = sn_new_clean(t.get_text(" "))
            title = re.sub(r"\|.*", "", title).strip()
    if not title:
        title = url.split("/")[-1].replace("-", " ").title()

    # Focus only on content-area (priority order from prompt STEP 1A)
    content_div = (
        soup.find("div", class_="entry-content") or
        soup.find("div", class_="post-content") or
        soup.find("div", class_="td-post-content") or
        soup.find("div", class_="content-area") or
        soup.find("div", id="primary") or
        soup.find("main", id="main") or
        soup.find("div", class_="site-content") or
        soup.find("article") or
        soup.find("body")
    )
    if not content_div:
        return None

    # ── Build structured sections ─────────────────────────
    sections     = []
    cur_section  = {"title": "Overview", "content": []}
    proc_tables  = set()
    seen_paras   = set()

    def _flush():
        if cur_section["content"]:
            sections.append(dict(cur_section))

    for el in content_div.find_all(["h2", "h3", "h4", "p", "ul", "ol", "table"]):

        if el.name in ["h2", "h3", "h4"]:
            _flush()
            sec_title = sn_new_clean(el.get_text(" "))
            # Spam section titles — clear the title, keep content under ""
            _SPAM_SEC_TITLES = [
                "set as preferred source on google", "preferred source on google",
                "follow us", "join our channel", "join telegram", "join whatsapp",
                "download our app", "sarkari result", "sarkariresult",
            ]
            if any(sp in sec_title.lower() for sp in _SPAM_SEC_TITLES):
                sec_title = ""
            cur_section = {
                "title":   sec_title,
                "content": []
            }

        elif el.name == "p":
            txt = sn_new_clean(el.get_text(" "))
            if not txt or txt in seen_paras:
                continue
            # Skip very short noise
            if len(txt) < 4:
                continue
            # Skip spam paragraphs
            _SPAM_PARA_WORDS = [
                "sarkariresultshine", "sarkariresult.com", "sarkari result shine",
                "join whatsapp", "join facebook", "follow telegram", "join telegram",
                "preferred source on google", "set as preferred source",
                "if the form we provide is rejected, sarkari result shine",
                "design by mukesh", "about || contact",
            ]
            if any(sp in txt.lower() for sp in _SPAM_PARA_WORDS):
                continue
            seen_paras.add(txt)
            cur_section["content"].append({"type": "paragraph", "text": txt})

        elif el.name in ["ul", "ol"]:
            items = []
            for li in el.find_all("li"):
                li_t = sn_new_clean(li.get_text(" "))
                if li_t and li_t not in items:
                    items.append(li_t)
            if items:
                cur_section["content"].append({"type": "list", "items": items})

        elif el.name == "table":
            tbl_key = el.get_text(" ")[:200]
            if tbl_key in proc_tables:
                continue
            proc_tables.add(tbl_key)

            rows_data = []
            for row in el.find_all("tr"):
                cols     = row.find_all(["td", "th"])
                row_data = []
                for col in cols:
                    col_text = sn_new_clean(col.get_text(" "))
                    if not col_text:
                        continue
                    # Collect only official (non-sarkarinetwork) links
                    cell_links = []
                    for a in col.find_all("a", href=True):
                        href     = a["href"].strip()
                        lnk_txt  = sn_new_clean(a.get_text(" "))
                        if not href.startswith("http"):
                            continue
                        if sn_new_is_blocked_url(href):
                            continue
                        if not lnk_txt or lnk_txt.lower() in ["www", "www."]:
                            continue
                        cell_links.append({"text": lnk_txt, "url": href})
                    row_data.append({"text": col_text, "links": cell_links})
                if row_data:
                    rows_data.append(row_data)

            if rows_data:
                cur_section["content"].append({"type": "table", "rows": rows_data})

    _flush()

    # ── Collect all label:value pairs (li + blob cells + paragraphs) ───────
    kv_pairs = []   # (label, value)

    def _split_blob(text):
        """'A : x B : y C : z' jaise blob ko (label,value) pairs me todo."""
        pairs = []
        # har 'Label :' ke aage ka value agle 'Label :' tak
        matches = list(re.finditer(
            r"([A-Za-z][A-Za-z0-9 ()/&.\-]{2,45}?)\s*[:：]\s*", text))
        for i, m in enumerate(matches):
            label = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            value = text[start:end].strip(" .|–—-")
            if label and value:
                pairs.append((label, value))
        return pairs

    # 2-col table rows
    for table in content_div.find_all("table"):
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) == 2:
                lbl = sn_new_clean(cols[0].get_text(" "))
                val = sn_new_clean(cols[-1].get_text(" "))
                if lbl and val and ":" not in lbl:
                    kv_pairs.append((lbl, val))
            elif len(cols) == 1:
                # single-cell blob row (Important Dates / Fees blob)
                blob = sn_new_clean(cols[0].get_text(" "))
                if blob.count(":") >= 2:
                    kv_pairs.extend(_split_blob(blob))
    # bullet list <li> lines
    for li in content_div.find_all("li"):
        t = sn_new_clean(li.get_text(" "))
        if t.count(":") >= 2:
            kv_pairs.extend(_split_blob(t))
        else:
            m = re.match(r"\s*([A-Za-z][A-Za-z0-9 ()/&.\-]{2,45}?)\s*[:：]\s*(.+)", t)
            if m:
                kv_pairs.append((m.group(1), m.group(2)))
    # paragraphs that are blob-style
    for p in content_div.find_all("p"):
        t = sn_new_clean(p.get_text(" "))
        if t.count(":") >= 2 and len(t) < 400:
            kv_pairs.extend(_split_blob(t))

    # dedup kv_pairs (label.lower, value)
    _seen_kv = set()
    _dedup_kv = []
    for lbl, val in kv_pairs:
        key = (lbl.strip().lower(), val.strip())
        if key in _seen_kv:
            continue
        _seen_kv.add(key)
        _dedup_kv.append((lbl.strip(), val.strip()))
    kv_pairs = _dedup_kv

    # ── Known structured fields (STEP 2A) ──────────────────────────────────
    fields = {k: "" for k in (
        "advt_no", "department", "post_name", "total_vacancy",
        "last_date", "application_start", "exam_date", "interview_date",
        "result_date", "admit_card_date", "age_limit", "salary",
        "qualification", "selection_process", "application_mode",
        "fee_general", "fee_obc", "fee_sc_st", "fee_female", "fee_payment_mode",
        "job_location",
    )}
    DATE_FIELDS = {"last_date", "application_start", "exam_date",
                   "interview_date", "result_date", "admit_card_date"}
    FEE_FIELDS = {"fee_general", "fee_obc", "fee_sc_st", "fee_female"}
    for lbl, val in kv_pairs:
        fk = sn_match_field_key(lbl)
        if not fk or fk not in fields:
            continue
        if fields[fk]:          # pehla match rakho
            continue
        if fk in DATE_FIELDS:
            iso = sn_extract_iso_date(val)
            if iso:
                fields[fk] = iso
            elif re.search(r"available\s*soon|notified\s*soon|before\s*exam|"
                           r"as\s*per\s*schedule|coming\s*soon|to\s*be\s*notified",
                           val, re.I):
                fields[fk] = sn_new_clean(val)[:40]
        elif fk in FEE_FIELDS:
            num = re.sub(r"[^\d]", "", val.split("(")[0])
            fields[fk] = num if num else ("0" if re.search(r"nil|free|0", val, re.I) else val)
        else:
            fields[fk] = val

    full_text = sn_new_clean(content_div.get_text(" "))

    # last_date fallback — full text se
    if not fields["last_date"]:
        m = re.search(r"(?:last\s+date|closing\s+date)\b[^\d]{0,20}"
                      r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})", full_text, re.I)
        if m:
            fields["last_date"] = sn_extract_iso_date(m.group(1))

    # ── selection_process — "Selection Process" section list se (multi-value) ──
    sel_items = []
    for sec in sections:
        if "selection" in (sec.get("title", "") or "").lower():
            for c in sec.get("content", []):
                if c.get("type") == "list":
                    for it in c.get("items", []):
                        it = sn_new_clean(it)
                        if it and ":" not in it and len(it) < 80 and it not in sel_items:
                            sel_items.append(it)
    if sel_items:
        fields["selection_process"] = ", ".join(sel_items)

    # ── derive department / advt_no / post_name / total_vacancy ────────────
    if not fields["advt_no"]:
        m = re.search(r"Advt\.?\s*No\.?\s*[:\-]?\s*([A-Za-z0-9/\-]+(?:/[A-Za-z0-9/\-]+)*)",
                      full_text, re.I)
        if m:
            fields["advt_no"] = m.group(1).strip()
    if not fields["department"]:
        # title se org guess: pehle 3-5 words tak (Recruitment/Online se pehle)
        dep_m = re.match(r"(.+?)\s+(?:\d|recruitment|online|clerk|bharti|vacancy)",
                         title, re.I)
        if dep_m and len(dep_m.group(1)) > 3:
            fields["department"] = dep_m.group(1).strip()
    if not fields["total_vacancy"]:
        m = re.search(r"(\d[\d,]{1,6})\s*(?:posts?|vacanc)", full_text, re.I)
        if m:
            fields["total_vacancy"] = m.group(1).replace(",", "")

    # ── Admissions-specific fields ─────────────────────────────────────────
    course_name = admission_type = ""
    if category == "ADMISSIONS":
        for lbl, val in kv_pairs:
            low = lbl.lower()
            if not course_name and any(v in low for v in SN_FIELD_MAP["course_name"]):
                course_name = val
            if not admission_type and any(v in low for v in SN_FIELD_MAP["admission_type"]):
                admission_type = val

    # ── Vacancy details (STEP 6) — sirf genuine category-wise tables ───────
    vacancy_details = []
    _vac_seen = set()
    for table in content_div.find_all("table"):
        first_row = table.find("tr")
        if not first_row:
            continue
        ncols = len(first_row.find_all(["th", "td"]))
        head = sn_new_clean(table.get_text(" ")).lower()
        if ncols >= 3 and sum(h in head for h in
                              ("ur", "obc", "sc", "st", "ews", "total", "category")) >= 2:
            parsed_v = sn_parse_vacancy_table(table)
            for row in parsed_v:
                sig = json.dumps(row, sort_keys=True, ensure_ascii=False)
                if sig not in _vac_seen:
                    _vac_seen.add(sig)
                    vacancy_details.append(row)
        # post_name / qualification single-row table
        if not fields["qualification"]:
            for tr in table.find_all("tr"):
                tds = [sn_new_clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
                if len(tds) >= 3 and "qualification" in head and tds[0].lower() not in ("post name",):
                    if not fields["post_name"]:
                        fields["post_name"] = tds[0]
                    if not fields["total_vacancy"] and tds[1].isdigit():
                        fields["total_vacancy"] = tds[1]
                    fields["qualification"] = tds[-1]
                    break

    # ── Important links — PAGE-WIDE, saare official links (dedup) ───────────
    important_links = {}
    _link_urls = set()

    def _add_link(label, href):
        if not sn_is_official_url(href) or href in _link_urls:
            return
        label = (label or "").lower().strip()
        mapped = None
        for variants, key in SN_LINK_LABEL_MAP:
            if any(v in label for v in variants):
                mapped = key
                break
        if not mapped:
            mapped = re.sub(r"[^a-z0-9_]", "_", label[:40]).strip("_") or "other_link"
        _link_urls.add(href)
        if mapped in important_links:
            cur = important_links[mapped]
            if isinstance(cur, list):
                if href not in cur:
                    cur.append(href)
            elif cur != href:
                important_links[mapped] = [cur, href]
        else:
            important_links[mapped] = href

    # (a) table rows: label cell + link cell
    for table in content_div.find_all("table"):
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue
            label = sn_new_clean(cols[0].get_text(" "))
            for a in cols[-1].find_all("a", href=True):
                _add_link(label, a["href"].strip())
    # (b) any remaining official links on page — label from link text
    for a in content_div.find_all("a", href=True):
        href = a["href"].strip()
        if href in _link_urls:
            continue
        ltxt = sn_new_clean(a.get_text(" "))
        if ltxt and ltxt.lower() not in ("click here", "www", "www.", "here"):
            _add_link(ltxt, href)

    # ── Dynamic auto-detected new fields (STEP 2B) ─────────────────────────
    captured = set(k for k, v in fields.items() if v)
    # fee/date labels jo map ho chuke unhe extra se rokne ke liye known me daalo
    extra_fields = sn_auto_detect_new_fields(kv_pairs, captured)
    # known fee/date residue extra se hatao
    extra_fields = {k: v for k, v in extra_fields.items()
                    if not sn_match_field_key(k.replace("_", " "))}

    # ── Section dedup (comprehensive) ──────────────────────────────────────
    #   1) paragraph jo kisi table cell me already hai → hatao
    #   2) duplicate content-block (same list/table) → hatao
    #   3) list ke andar duplicate items → hatao
    #   4) same-title consecutive sections → merge
    _table_texts = set()
    for sec in sections:
        for c in sec.get("content", []):
            if c.get("type") == "table":
                for r in c.get("rows", []):
                    for cell in r:
                        tv = cell.get("text", "")
                        if tv:
                            _table_texts.add(tv)

    _seen_para = set()
    _seen_block = set()          # list/table block signatures (whole-item)
    cleaned = []
    for sec in sections:
        new_content = []
        for c in sec.get("content", []):
            ctype = c.get("type")
            if ctype == "paragraph":
                tv = c.get("text", "")
                if not tv or tv in _table_texts or tv in _seen_para:
                    continue
                _seen_para.add(tv)
                new_content.append(c)
            elif ctype == "list":
                # list items dedup (order preserve)
                seen_it = set(); items = []
                for it in c.get("items", []):
                    if it and it not in seen_it:
                        seen_it.add(it); items.append(it)
                if not items:
                    continue
                sig = "L:" + json.dumps(items, ensure_ascii=False)
                if sig in _seen_block:
                    continue
                _seen_block.add(sig)
                new_content.append({"type": "list", "items": items})
            elif ctype == "table":
                sig = "T:" + json.dumps(c.get("rows", []), sort_keys=True, ensure_ascii=False)
                if sig in _seen_block:
                    continue
                _seen_block.add(sig)
                new_content.append(c)
            else:
                new_content.append(c)
        if new_content:
            cleaned.append({"title": sec.get("title", ""), "content": new_content})

    # merge consecutive/repeated same-title sections
    merged = []
    for sec in cleaned:
        if merged and (sec["title"] or "").strip().lower() == (merged[-1]["title"] or "").strip().lower() and sec["title"]:
            # same title → content merge (block-dedup already global, safe)
            merged[-1]["content"].extend(sec["content"])
        else:
            merged.append(sec)
    sections = merged

    # ── Build output (category FIRST key) ──────────────────────────────────
    item = {"category": category, "title": title, "slug": sn_slugify(title),
             "_scraped_from": url}   # INTERNAL ONLY — incremental-scrape bookkeeping
    item.update(fields)
    if category == "ADMISSIONS":
        item["course_name"]    = course_name
        item["admission_type"] = admission_type
    item["status"]          = "active"
    item["important_links"] = important_links
    item["vacancy_details"] = vacancy_details
    item["sections"]        = sections
    item["extra_fields"]    = extra_fields

    # ── Active filter (STEP 9) — expired skip ──────────────────────────────
    if not sn_is_active(item):
        return None

    # ── FINAL SCRUB — sarkarinetwork URL / branding / social kuch na bache ─
    item = sn_brand_scrub(item)
    item = {"category": category, **{k: v for k, v in item.items() if k != "category"}}
    return item


def sn_scrape_listing(page_url, category, limit, existing_items=None):
    """
    Full listing scrape: get links → scrape each detail page.
    Returns list of job/admission dicts (active only, deduped by title).

    INCREMENTAL: if `existing_items` (previously-scraped items for this
    category, each carrying `_scraped_from`) is given, links already in
    there are skipped entirely — no HTTP request — and the old item is
    carried forward as-is. Cuts SarkariNetwork requests from "every link,
    every run" down to just genuinely new postings.
    """
    print(f"\n  Fetching listing: {page_url}  (limit={limit})")
    links = sn_new_extract_listing_links(page_url, limit)
    print(f"  Found {len(links)} candidate links")

    _existing_urls = {it.get("_scraped_from", "") for it in (existing_items or [])
                      if it.get("_scraped_from")}
    _existing_by_url = {it["_scraped_from"]: it for it in (existing_items or [])
                        if it.get("_scraped_from")}
    _carry_forward = [_existing_by_url[l] for l in links if l in _existing_urls]
    new_links = [l for l in links if l not in _existing_urls]
    print(f"  [INCREMENTAL] {category}: {len(_carry_forward)} already scraped "
          f"(skipped), {len(new_links)} new to fetch")
    links = new_links

    # DIAGNOSTIC: agar 0 links mile, dekho server ne kya HTML diya
    if not links and not _carry_forward:
        try:
            r = requests.get(page_url, headers=SN_HEADERS, timeout=30,
                             allow_redirects=True)
            body = r.text or ""
            a_count = body.lower().count("<a ")
            sn_links = body.count("sarkarinetwork.com/")
            print(f"  [SN-DIAG] status={r.status_code} bytes={len(body)} "
                  f"<a>tags={a_count} sarkarinetwork-links-in-html={sn_links}")
            low = body.lower()
            for sig in ["cloudflare", "captcha", "just a moment",
                        "enable javascript", "challenge-platform",
                        "access denied", "are you human"]:
                if sig in low:
                    print(f"  [SN-DIAG] BOT-WALL signal detected: '{sig}'")
            # pehla ~500 char sample (branding strip ke baad)
            sample = re.sub(r"\s+", " ", body[:600])
            print(f"  [SN-DIAG] HTML head sample: {sample[:400]}")
        except Exception as e:
            print(f"  [SN-DIAG] diag fetch error: {e}")

    results    = list(_carry_forward)
    seen_titles = {it.get("title", "").lower().strip() for it in _carry_forward}

    for idx, link in enumerate(links, 1):
        print(f"  [{idx}/{len(links)}] {link}")
        try:
            item = sn_new_scrape_detail(link, category)
            if not item:
                continue
            key = item.get("slug") or item["title"].lower().strip()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            item["sequence"] = idx
            results.append(item)
        except Exception as e:
            print(f"  ERROR scraping {link}: {e}")
            continue

    return results


# =========================================================
# MAIN — SCRAPE BOTH SOURCES & MERGE INTO ONE JSON
# =========================================================

def sarkari_main():
    print("\n" + "=" * 60)
    print("MERGED SARKARI SCRAPER STARTED")
    print("=" * 60)

    # ── INCREMENTAL SCRAPE SETUP: load whatever we already have so every
    # source below can skip URLs it has already scraped. This is the same
    # "only fetch what's new" pattern already proven in scraper_fja.py — cuts
    # daily requests from ~150-200 (every job, every run) down to just the
    # handful of genuinely new postings. ──
    _existing_by_cat = {}
    if os.path.exists(MSS_OUTPUT_FILE):
        try:
            with open(MSS_OUTPUT_FILE, encoding="utf-8") as _f:
                _prev_all = json.load(_f)
            for _j in _prev_all.get("jobs", []):
                _existing_by_cat.setdefault(_j.get("category", ""), []).append(_j)
        except Exception as _e:
            print(f"  [INCREMENTAL] could not load previous data: {_e}")

    def _existing_offline_urls():
        return {j.get("_scraped_from", "") for j in _existing_by_cat.get("OFFLINE_FORM", [])
                if j.get("_scraped_from")}

    def _existing_latestnew_urls():
        return {j.get("_scraped_from", "") for j in _existing_by_cat.get("LATEST_JOBS NEW", [])
                if j.get("_scraped_from")}

    # ── Source 1: sarkariresultshine.com ──────────────────
    print("\n[SOURCE 1] sarkariresultshine.com — Offline Form Jobs (Page-ordered, Top 30)")
    print("-" * 60)

    # Step 1: Collect ordered links across all 3 pages (sequence preserved)
    all_shine_link_objs = []   # list of {"date": ..., "href": ..., "title": ...}
    seen_href_global = set()

    for cat in SHINE_CATEGORY_URLS:
        print(f"\nGETTING: {cat}")
        page_links = shine_get_job_links(cat)
        for obj in page_links:
            if obj["href"] not in seen_href_global:
                seen_href_global.add(obj["href"])
                all_shine_link_objs.append(obj)

    print(f"\nTOTAL ORDERED SHINE LINKS (deduped): {len(all_shine_link_objs)}")

    # Step 2: Limit to first 30 (page-sequence order exactly as seen on site)
    shine_link_objs_top30 = all_shine_link_objs[:30]

    # INCREMENTAL: split into already-scraped (carry forward, no re-fetch) vs new
    _offline_existing_urls = _existing_offline_urls()
    _shine_existing_items = {j["_scraped_from"]: j for j in _existing_by_cat.get("OFFLINE_FORM", [])
                             if j.get("_scraped_from")}
    _shine_carry_forward = [
        _shine_existing_items[obj["href"]] for obj in shine_link_objs_top30
        if obj["href"] in _offline_existing_urls
    ]
    shine_link_objs_top30 = [obj for obj in shine_link_objs_top30
                              if obj["href"] not in _offline_existing_urls]
    print(f"  [INCREMENTAL] Offline Form: {len(_shine_carry_forward)} already scraped "
          f"(skipped), {len(shine_link_objs_top30)} new to fetch")
    print(f"PROCESSING {len(shine_link_objs_top30)} NEW LINKS:")
    for i, obj in enumerate(shine_link_objs_top30, 1):
        print(f"  [{i:02d}] {obj['date']}  |  {obj['title'][:70]}")


    # Step 3: Scrape detail pages IN ORDER using threads, then re-sort by original index
    # We need to preserve insertion order so we use index-keyed dict
    shine_results = {}
    with ThreadPoolExecutor(max_workers=SHINE_MAX_THREADS) as executor:
        future_to_idx = {
            executor.submit(shine_scrape_job, obj["href"], obj["title"], obj["date"]): idx
            for idx, obj in enumerate(shine_link_objs_top30)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            result = future.result()
            if result:
                # Preserve original sequence number
                result["sequence"] = idx + 1
                shine_results[idx] = result

    # Step 4: Re-assemble in original page order, THEN merge in the carried-
    # forward already-scraped items (no re-fetch needed for those — INCREMENTAL).
    shine_jobs = _shine_carry_forward + [shine_results[i] for i in sorted(shine_results.keys())]

    # Deduplicate by title (keep first occurrence = earlier in page order)
    seen_shine = set()
    shine_dedup = []
    for item in shine_jobs:
        key = item.get("title", "").lower().strip()
        if key and key not in seen_shine:
            seen_shine.add(key)
            shine_dedup.append(item)

    # NO sort_jobs_latest() — order must stay as-is from page sequence
    print(f"\nSHINE OFFLINE JOBS (page-ordered, top 30): {len(shine_dedup)}")
    for i, job in enumerate(shine_dedup, 1):
        print(f"  [{i:02d}] {job.get('listing_date','')}  {job.get('title','')[:70]}")


    # -- Source 1b: sarkariresultshine.com -- Latest Jobs --
    print("\n[SOURCE 1b] sarkariresultshine.com -- Latest Jobs (Page-ordered, Top 100)")
    print("-" * 60)

    # Step 1: Collect ordered links across all 10 pages (sequence preserved)
    all_shine_lj_link_objs = []
    seen_lj_href_global = set()

    for cat_url in SHINE_LATEST_JOBS_URLS:
        print(f"\nGETTING: {cat_url}")
        page_links = shine_get_latest_job_links(cat_url)
        for obj in page_links:
            if obj["href"] not in seen_lj_href_global:
                seen_lj_href_global.add(obj["href"])
                all_shine_lj_link_objs.append(obj)

    print(f"\nTOTAL ORDERED LATEST JOB LINKS (deduped): {len(all_shine_lj_link_objs)}")

    # Step 2: Top 100 -- 10 pages x ~10 jobs/page
    shine_lj_top100 = all_shine_lj_link_objs[:100]

    # INCREMENTAL: skip already-scraped URLs, carry them forward as-is
    _latestnew_existing_urls = _existing_latestnew_urls()
    _lj_existing_items = {j["_scraped_from"]: j for j in _existing_by_cat.get("LATEST_JOBS NEW", [])
                          if j.get("_scraped_from")}
    _lj_carry_forward = [
        _lj_existing_items[obj["href"]] for obj in shine_lj_top100
        if obj["href"] in _latestnew_existing_urls
    ]
    shine_lj_top100 = [obj for obj in shine_lj_top100
                       if obj["href"] not in _latestnew_existing_urls]
    print(f"  [INCREMENTAL] Latest Jobs New: {len(_lj_carry_forward)} already scraped "
          f"(skipped), {len(shine_lj_top100)} new to fetch")
    print(f"PROCESSING {len(shine_lj_top100)} NEW LINKS:")
    for i, obj in enumerate(shine_lj_top100, 1):
        print(f"  [{i:03d}] {obj['date']}  |  {obj['title'][:70]}")

    # Step 3: Scrape detail pages IN ORDER via threads, preserve index
    shine_lj_results = {}
    with ThreadPoolExecutor(max_workers=SHINE_MAX_THREADS) as executor:
        future_to_idx = {
            executor.submit(shine_scrape_latest_job, obj["href"], obj["title"], obj["date"]): idx
            for idx, obj in enumerate(shine_lj_top100)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            result = future.result()
            if result:
                result["sequence"] = idx + 1
                shine_lj_results[idx] = result

    # Step 4: Re-assemble in original page order, merge in carried-forward
    # already-scraped items (INCREMENTAL — no re-fetch needed for those).
    shine_lj_jobs_ordered = _lj_carry_forward + [shine_lj_results[i] for i in sorted(shine_lj_results.keys())]

    # Deduplicate by title (keep first occurrence = earlier in page order)
    seen_lj = set()
    shine_lj_dedup = []
    for item in shine_lj_jobs_ordered:
        key = item.get("title", "").lower().strip()
        if key and key not in seen_lj:
            seen_lj.add(key)
            shine_lj_dedup.append(item)

    print(f"\nSHINE LATEST JOBS (page-ordered, top 100): {len(shine_lj_dedup)}")
    for i, job in enumerate(shine_lj_dedup, 1):
        print(f"  [{i:03d}] {job.get('listing_date','')}  {job.get('title','')[:70]}")

    # ── Source 2: sarkariresult.com ───────────────────────
    print("\n[SOURCE 2] sarkariresult.com — Homepage Center-Tables")
    print("-" * 60)

    # Step 1: Homepage se ek hi baar mein sab categories ke links lao
    print("\n  Fetching homepage sections...")
    homepage_sections = sr_get_homepage_sections()

    sr_data = {}
    sr_seen = set()

    # ── INCREMENTAL SCRAPE: load what we already have for SR so we only fetch
    # NEW links today (same proven pattern as scraper_fja.py's existing_urls
    # check). Cuts SR requests from ~150/run to just the handful of genuinely
    # new postings. ──
    import incremental_cache as _ic
    _sr_existing_by_cat = {}
    if os.path.exists(MSS_OUTPUT_FILE):
        try:
            with open(MSS_OUTPUT_FILE, encoding="utf-8") as _f:
                _prev = json.load(_f)
            for _j in _prev.get("jobs", []):
                _sr_existing_by_cat.setdefault(_j.get("category", ""), []).append(_j)
        except Exception:
            pass

    for category, links in homepage_sections.items():
        print(f"\n  CATEGORY: {category}  ({len(links)} links found)")

        # Category-wise limit — same logic as before
        # Latest Jobs & Admission: active filter; rest: top_n
        LIMITS = {
            "SR_Latest_Jobs": 80,
            "SR_Admit_Card":  25,
            "SR_Result":      25,
            "SR_Answer_Key":  20,
        }
        ACTIVE_FILTER = {"SR_Latest_Jobs"}

        max_links = LIMITS.get(category, 25)
        links = links[:max_links]

        # Keep only links we haven't already scraped for this category.
        # SR jobs store their source URL at meta.sourceUrl (the only field
        # exempted from the own-site-link scrub — see sr_scrub_obj). Already-
        # scraped items are carried forward as-is below (no re-fetch).
        _existing_items = _sr_existing_by_cat.get(category, [])
        _existing_url_set = {(it.get("meta") or {}).get("sourceUrl", "")
                             for it in _existing_items if (it.get("meta") or {}).get("sourceUrl")}
        _new_link_objs = [l for l in links if l.get("url") not in _existing_url_set]
        print(_ic.summary_line(category, len(links), len(_new_link_objs), len(_existing_url_set)))

        # carry forward items whose source URL is still on today's listing page
        # (still live) and that we are NOT about to re-fetch
        _new_urls = {l.get("url") for l in _new_link_objs}
        _today_urls = {l.get("url") for l in links}
        category_items = [it for it in _existing_items
                          if (it.get("meta") or {}).get("sourceUrl") in _today_urls
                          and (it.get("meta") or {}).get("sourceUrl") not in _new_urls]
        links = _new_link_objs   # only the NEW links go through the fetch loop below
        for item in links:
            try:
                serial = item.get("serial", "")
                print(f"    [{serial}] {item['title'][:70]}")
                detail = sr_scrape_detail(category, item["url"])
                if not detail:
                    continue
                # Active-filter: skip expired last_date for active categories
                if category in ACTIVE_FILTER:
                    last_date = (detail.get("importantDates", {}) or {}).get("lastDateApplyOnline", "")
                    if last_date and is_expired(date_to_iso(last_date)):
                        continue
                key = detail["title"].lower()
                if key in sr_seen:
                    continue
                sr_seen.add(key)
                # Serial number preserve karo (homepage mein jis order mein tha)
                if isinstance(detail.get("meta"), dict):
                    detail["meta"]["homepageSerial"] = serial

                # FINAL GUARANTEE: category name har item par (first key),
                # hamesha 5 valid SR categories mein se ek + branding scrub.
                detail = sr_stamp_category(detail, category,
                                           detail.get("title", ""),
                                           item.get("url", ""))
                category_items.append(detail)
            except Exception as e:
                print("    SR ERROR:", e)
                continue

        sr_data[category] = category_items
        print(f"  SCRAPED: {len(category_items)}")

    sr_total = sum(len(v) for v in sr_data.values())
    print(f"\nSARKARIRESULT.COM TOTAL: {sr_total}")

    # ── SR CACHE FALLBACK (Cloudflare IP-block workaround) ─────────────────────
    # sarkariresult.com Cloudflare GitHub-Actions ke datacenter IP ko 403 deta
    # hai (TLS perfect ho tab bhi — IP reputation block). Solution: SR data
    # apne PC (residential IP) se scrape karke `sr_cache.json` repo mein commit
    # karo. Yahan logic:
    #   - Agar fresh SR scrape se kuch mila (sr_total > 0) → cache update kar do
    #     (ye tab hoga jab scraper residential IP/PC pe chale).
    #   - Agar fresh scrape se 0 mila (GitHub pe 403) → cache se load kar lo,
    #     taaki SR data site se gayab na ho.
    SR_CACHE_FILE = "sr_cache.json"
    if sr_total > 0:
        # Fresh data mila — cache refresh karo (PC run pe useful)
        try:
            with open(SR_CACHE_FILE, "w", encoding="utf-8") as _cf:
                json.dump({"saved_at": datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
                           "sr_data": sr_data}, _cf, ensure_ascii=False, indent=2)
            print(f"  [SR CACHE] Updated {SR_CACHE_FILE} with {sr_total} fresh records.")
        except Exception as _e:
            print(f"  [SR CACHE] Could not write cache: {_e}")
    else:
        # Fresh scrape blocked/empty — cache se load karo
        if os.path.exists(SR_CACHE_FILE):
            try:
                with open(SR_CACHE_FILE, encoding="utf-8") as _cf:
                    _cached = json.load(_cf)
                sr_data = _cached.get("sr_data", {}) or {}
                sr_total = sum(len(v) for v in sr_data.values())
                _saved_at = _cached.get("saved_at", "unknown")
                print(f"  [SR CACHE] Fresh scrape blocked — loaded {sr_total} cached "
                      f"records from {SR_CACHE_FILE} (saved {_saved_at}).")
            except Exception as _e:
                print(f"  [SR CACHE] Could not read cache: {_e}")
        else:
            print(f"  [SR CACHE] No {SR_CACHE_FILE} found — SR data will be empty "
                  f"this run. Apne PC pe scrape_sr_only.py chalakar cache banao.")
    print("\n[SOURCE 3] sarkarinetwork.com — Upcoming Jobs (top 50)")
    print("-" * 60)
    sn_jobs = sn_scrape_listing(SN_UPCOMING_URL, "UPCOMING_JOBS", limit=50, existing_items=_existing_by_cat.get("UPCOMING_JOBS", []))
    print(f"\nSARKARINETWORK UPCOMING JOBS: {len(sn_jobs)}")
    for i, j in enumerate(sn_jobs, 1):
        print(f"  [{i:03d}] {j.get('last_date','')}  {j.get('title','')[:70]}")

    # ── Source 4 & 5: sarkarinetwork.com State/Central Jobs — REMOVED ─────
    # State Jobs and Central Jobs categories have been retired from the site.
    # (State-wise pages under /state-jobs/ come from a separate data source and
    #  are unaffected.) Scraping disabled so these never re-enter the JSON.
    sn_state_jobs = []
    sn_central_jobs = []
    print("\n[SOURCE 4+5] State Jobs / Central Jobs — DISABLED (categories retired)")

    # ── Source 6: sarkarinetwork.com — Admissions ─────────
    print("\n[SOURCE 6] sarkarinetwork.com — Admissions (active only, top 50)")
    print("-" * 60)
    sn_admissions = sn_scrape_listing(SN_ADMISSION_URL, "ADMISSIONS", limit=50, existing_items=_existing_by_cat.get("ADMISSIONS", []))
    print(f"\nSARKARINETWORK ADMISSIONS (active): {len(sn_admissions)}")
    for i, j in enumerate(sn_admissions, 1):
        print(f"  [{i:02d}] {j.get('last_date','')}  {j.get('title','')[:70]}")

    # ── Merge into single JSON ────────────────────────────
    all_jobs = list(shine_dedup) + list(shine_lj_dedup)
    for items in sr_data.values():
        all_jobs.extend(items)
    all_jobs.extend(sn_jobs)
    all_jobs.extend(sn_state_jobs)
    all_jobs.extend(sn_central_jobs)
    all_jobs.extend(sn_admissions)

    # Group by category for easy filtering
    jobs_by_category = {}
    for job in all_jobs:
        cat = job.get("category", "UNKNOWN")
        jobs_by_category.setdefault(cat, []).append(job)

    # SR categories ko specified order mein sort karo
    SR_CATEGORY_ORDER = [
        "SR_Latest_Jobs",
        "SR_Result",
        "SR_Admit_Card",
        "SR_Answer_Key",
    ]
    # ── Retired categories — never write these to the JSON ───────────────
    # State Jobs, Central Jobs, SR Admission removed from the site.
    _RETIRED_CATS = {"STATE_JOBS", "CENTRAL_JOBS", "SR_Admission"}
    jobs_by_category = {c: v for c, v in jobs_by_category.items() if c not in _RETIRED_CATS}
    sorted_by_category = {}
    for cat in SR_CATEGORY_ORDER:
        if cat in jobs_by_category:
            sorted_by_category[cat] = jobs_by_category[cat]
    # Remaining categories (non-SR) preserve karo
    for cat, items in jobs_by_category.items():
        if cat not in sorted_by_category:
            sorted_by_category[cat] = items
    jobs_by_category = sorted_by_category

    # ── Final jobs list — sorted_by_category se rebuild karo ──────────────
    # all_jobs mein categories mixed order mein hain.
    # jobs_by_category ab SR_Latest_Jobs → SR_Result → SR_Admit_Card →
    # SR_Admission → SR_Answer_Key → remaining categories ke order mein hai.
    # Is order ko jobs list mein bhi reflect karna zaroori hai.
    sorted_jobs_list = []
    for cat_items in jobs_by_category.values():
        sorted_jobs_list.extend(cat_items)

    output = {
        "scraped_at": TODAY.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(sorted_jobs_list),
        "summary": {
            "sarkariresultshine_offline_jobs_top30":    len(shine_dedup),
            "sarkariresultshine_latest_jobs_top100":    len(shine_lj_dedup),
            "sarkariresult_categories":                 {k: len(v) for k, v in sr_data.items()},
            "sarkariresult_total":                      sr_total,
            "upcoming_jobs":                            len(sn_jobs),
            "state_jobs_active":                        len(sn_state_jobs),
            "central_jobs_active":                      len(sn_central_jobs),
            "admissions_active":                        len(sn_admissions),
        },
        "category_counts": {cat: len(items) for cat, items in jobs_by_category.items()},
        "jobs": sorted_jobs_list,
    }

    with open(MSS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("SCRAPER FINISHED")
    print(f"TOTAL RECORDS : {len(sorted_jobs_list)}")
    print(f"  SHINE OFFLINE  : {len(shine_dedup)} (page-ordered, top 30)")
    print(f"  SHINE LATEST   : {len(shine_lj_dedup)} (page-ordered, top 100)")
    print(f"  SR RECORDS     : {sr_total}")
    print(f"  SN UPCOMING    : {len(sn_jobs)}")
    print(f"  SN STATE JOBS  : {len(sn_state_jobs)} (active only)")
    print(f"  SN CENTRAL JOBS: {len(sn_central_jobs)} (active only)")
    print(f"  SN ADMISSIONS  : {len(sn_admissions)} (active only)")
    print(f"OUTPUT FILE    : {MSS_OUTPUT_FILE}")
    print("=" * 60)


# =========================================================
# START
# =========================================================


# ================================================================


# ================================================================
# MERGE INTO UNIFIED JSON
# ================================================================
if __name__ == "__main__":
    from scraper_merge import merge_into_json, wait_for_internet
    import json as _json_mod, os

    wait_for_internet("Sarkari")

    print("\n" + "="*60)
    print("  SCRAPER: Sarkari (Shine + SR + SN)")
    print("="*60)

    error_str = ""
    try:
        sarkari_main()   # saves to merged_sarkari_data.json
    except Exception as e:
        import traceback; traceback.print_exc()
        error_str = str(e)

    scraped = {}
    if os.path.exists("merged_sarkari_data.json"):
        with open("merged_sarkari_data.json", encoding="utf-8") as f:
            scraped = _json_mod.load(f)

    merge_into_json(
        source        = "sarkari_data",
        fresh_data    = scraped,
        scraper_error = error_str,
    )
