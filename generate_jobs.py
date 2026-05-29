#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_jobs.py  —  TopSarkariJobs Master Build Pipeline  v5.0
================================================================
ARCHITECTURE:
  ✅ ONE MASTER DATA SOURCE  (merge → dedupe → normalise)
  ✅ ONE HTML PER JOB         /data/jobs/{slug}/index.html
  ✅ ZERO DUPLICATE HTML
  ✅ CATEGORY/STATE/EDUCATION = listing only (NO full HTML)
  ✅ SINGLE RENDER ENGINE     (preferred-source-renderer.js)
  ✅ FULL SEO (canonical, meta, schemas: Job/FAQ/Breadcrumb/Article)
  ✅ SITEMAP includes ONLY /data/jobs/{slug}/

SOURCES merged:
  1. Complete_Jobs_Full_Data.json   — main category-wise job DB
  2. Education_Jobs.json            — state + entrance exam jobs
  3. Qualification_Wise_Jobs.json   — qual-filtered jobs with full detail
  4. merged_sarkari_data.json       — sr_ prefix + misc categories
  5. state-jobs-data.json           — state-wise listing
  6. dailyupdates.json              — Top 20 + Today Updates

OUTPUT:
  data/jobs/{slug}/index.html   — ONE canonical HTML per job
  data/jobs/{slug}.json         — raw JSON data (for renderer)
  data-jobs-index.json          — fast slug→meta lookup
  sitemap-jobs.xml              — jobs-only sitemap
  sections-index.json           — category listing (no dup HTML)
  data/merged-summary.json      — homepage card data
"""

import json, re, os, html as html_mod, shutil
from datetime import date
from collections import defaultdict

# ══════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════
BASE_URL   = "https://www.topsarkarijobs.com"
TODAY      = date.today().isoformat()

# Source files
SRC_MAIN   = "Complete_Jobs_Full_Data.json"
SRC_EDU    = "Education_Jobs.json"
SRC_QUAL   = "Qualification_Wise_Jobs.json"
SRC_MERGED = "merged_sarkari_data.json"
SRC_STATE  = "state-jobs-data.json"
SRC_DAILY  = "dailyupdates.json"

# Output paths (ALL job HTML/JSON go here — NEVER in /state/, /category/, /education/)
JOBS_HTML_DIR  = "data/jobs"   # data/jobs/{slug}/index.html
JOBS_DATA_DIR  = "data/jobs"   # data/jobs/{slug}.json  (same dir, different names)
JOBS_INDEX     = "data-jobs-index.json"
SITEMAP_FILE   = "sitemap-jobs.xml"
SECTIONS_INDEX = "sections-index.json"

# Category labels for SEO
CAT_LABELS = {
    "Latest_Notifications" : "Latest Sarkari Jobs",
    "10TH_Pass"            : "10th Pass Govt Jobs",
    "8TH_Pass"             : "8th Pass Govt Jobs",
    "12TH_Pass"            : "12th Pass Govt Jobs",
    "Diploma"              : "Diploma Govt Jobs",
    "ITI"                  : "ITI Govt Jobs",
    "B_Tech_BE"            : "B.Tech / BE Govt Jobs",
    "B_Com"                : "B.Com Govt Jobs",
    "Any_Graduate"         : "Graduate Govt Jobs",
    "Any_Post_Graduate"    : "Post Graduate Govt Jobs",
    "Railway_Jobs"         : "Railway Sarkari Jobs",
    "Police_Defence"       : "Police & Defence Jobs",
    "Teaching_Faculty"     : "Teaching & Faculty Jobs",
    "Bank_Jobs"            : "Bank Sarkari Jobs",
    "Medical_Hospital"     : "Medical & Hospital Jobs",
    "Last_Date_Reminder"   : "Last Date Reminder Jobs",
    "OFFLINE_FORM"         : "Offline Form Jobs",
    "STATE_JOBS"           : "State Govt Jobs",
    "Education"            : "Education Jobs",
    "Qualification"        : "Qualification-wise Jobs",
}

VALID_CATS = set(CAT_LABELS.keys())

# ══════════════════════════════════════════════════════════════════
#  STEP 1 — UTILITIES
# ══════════════════════════════════════════════════════════════════
def slugify(text):
    text = str(text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s\-]", "", text)
    text = re.sub(r"[\s\-]+", "-", text)
    return text[:120].strip("-") or "job"

def e(s):
    return html_mod.escape(str(s or ""), quote=True)

def normalise_date(raw):
    if not raw:
        return None
    raw = str(raw).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
               "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    m1 = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", raw)
    if m1:
        return f"{m1.group(3)}-{int(m1.group(2)):02d}-{int(m1.group(1)):02d}"
    m2 = re.search(r"(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})", raw)
    if m2:
        mo = months.get(m2.group(2)[:3].lower())
        if mo:
            return f"{m2.group(3)}-{mo:02d}-{int(m2.group(1)):02d}"
    return None

def safe_str(v, max_len=None):
    s = str(v or "").strip()
    if max_len and len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0].rstrip(".,–")
    return s

def load_json(path):
    if not os.path.exists(path):
        print(f"  ⚠️  NOT FOUND: {path}")
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"  ❌ ERROR reading {path}: {ex}")
        return None

# ══════════════════════════════════════════════════════════════════
#  STEP 2 — NORMALISED JOB RECORD
# ══════════════════════════════════════════════════════════════════
def make_normalised(
        title, slug, category="Latest_Notifications",
        org="", vacancies="", last_date="", post_date="",
        apply_mode="Online", location="India",
        short_info="", source_url="",
        education=None, state=None, tags=None,
        raw_detail=None):
    """
    Returns a normalised job dict that is the canonical single truth.
    raw_detail carries the full original JSON for the renderer.
    """
    nd = normalise_date(last_date)
    return {
        "slug"        : slug,
        "id"          : slug,
        "title"       : title,
        "category"    : category,
        "org"         : org or "",
        "vacancies"   : safe_str(vacancies),
        "lastDate"    : nd or last_date or "",
        "postDate"    : normalise_date(post_date) or post_date or TODAY,
        "applyMode"   : apply_mode or "Online",
        "location"    : location or "India",
        "shortInfo"   : short_info or "",
        "sourceUrl"   : source_url or "",
        "education"   : education or [],
        "state"       : state or [],
        "tags"        : tags or [],
        "detail"      : raw_detail or {},   # full JSON for renderer
    }

# ══════════════════════════════════════════════════════════════════
#  STEP 3 — MERGE ALL SOURCES
# ══════════════════════════════════════════════════════════════════
def merge_all_sources():
    """
    Read all 6 JSON sources, normalise each record, return flat list.
    Priority for duplicate resolution: slug → title+lastDate.
    """
    all_records = []

    # ── SOURCE 1: Complete_Jobs_Full_Data.json ──────────────────────
    print("\n[1] Loading Complete_Jobs_Full_Data.json …")
    cjf = load_json(SRC_MAIN)
    if cjf:
        for cat, jobs in cjf.items():
            if not isinstance(jobs, list):
                continue
            for job in jobs:
                bd    = job.get("basic_details") or {}
                dates = job.get("important_dates") or {}
                title = safe_str(bd.get("job_title"))
                if not title:
                    continue
                slug  = slugify(title)
                nd    = (dates.get("last_date_to_apply") or dates.get("closing_date") or "")
                rec = make_normalised(
                    title     = title,
                    slug      = slug,
                    category  = cat if cat in VALID_CATS else "Latest_Notifications",
                    org       = safe_str(bd.get("organization_name") or bd.get("post_name")),
                    vacancies = safe_str(bd.get("total_vacancies") or bd.get("total_vacancy")),
                    last_date = nd,
                    post_date = safe_str(bd.get("last_updated")),
                    apply_mode= safe_str(bd.get("application_mode") or "Online"),
                    location  = safe_str(bd.get("job_location") or "India"),
                    short_info= safe_str(bd.get("short_information")),
                    source_url= safe_str((job.get("important_links") or [{}])[0].get("links", [""])[0]
                                         if isinstance(job.get("important_links"), list) and job.get("important_links") else ""),
                    tags      = _extract_tags(cat, title, bd.get("job_location", "")),
                    raw_detail= job,
                )
                all_records.append(rec)
        print(f"   → {sum(len(v) for v in cjf.values() if isinstance(v,list))} jobs loaded")

    # ── SOURCE 2: Qualification_Wise_Jobs.json ──────────────────────
    print("[2] Loading Qualification_Wise_Jobs.json …")
    qwj = load_json(SRC_QUAL)
    if qwj:
        cnt = 0
        for sec in qwj.get("sections", []):
            for item in sec.get("items", []):
                name = safe_str(item.get("name") or item.get("title"))
                if not name:
                    continue
                detail  = item.get("detail") or {}
                if isinstance(detail, str):
                    try: detail = json.loads(detail)
                    except: detail = {}
                bd    = detail.get("basic_details") or {}
                dates = detail.get("important_dates") or {}
                slug  = slugify(name)
                nd    = safe_str(dates.get("last_date_to_apply") or item.get("lastDate") or "")
                rec = make_normalised(
                    title     = name,
                    slug      = slug,
                    category  = "Qualification",
                    org       = safe_str(bd.get("post_name") or bd.get("organization_name")),
                    vacancies = safe_str(bd.get("total_vacancies") or ""),
                    last_date = nd,
                    post_date = safe_str(item.get("postDate") or bd.get("last_updated")),
                    apply_mode= safe_str(bd.get("application_mode") or "Online"),
                    location  = safe_str(bd.get("job_location") or "India"),
                    short_info= safe_str(bd.get("short_information") or item.get("qualification")),
                    source_url= safe_str(item.get("url") or ""),
                    tags      = _extract_tags("Qualification", name, ""),
                    raw_detail= detail if detail else item,
                )
                all_records.append(rec)
                cnt += 1
        print(f"   → {cnt} jobs loaded")

    # ── SOURCE 3: Education_Jobs.json ───────────────────────────────
    print("[3] Loading Education_Jobs.json …")
    edj = load_json(SRC_EDU)
    if edj:
        cnt = 0
        for sec in edj.get("sections", []):
            state_name = safe_str(sec.get("title") or sec.get("state") or "India")
            for item in sec.get("items", []):
                name = safe_str(item.get("name") or item.get("title"))
                if not name:
                    continue
                detail = item.get("detail") or {}
                if isinstance(detail, str):
                    try: detail = json.loads(detail)
                    except: detail = {}
                bd    = (detail.get("basic_details") if detail else {}) or {}
                dates = (detail.get("important_dates") if detail else {}) or {}
                slug  = slugify(name)
                nd    = safe_str(dates.get("last_date_to_apply") or item.get("lastDate") or "")
                rec = make_normalised(
                    title     = name,
                    slug      = slug,
                    category  = "Education",
                    org       = safe_str(bd.get("post_name") or bd.get("organization_name") or state_name),
                    vacancies = safe_str(bd.get("total_vacancies") or ""),
                    last_date = nd,
                    post_date = safe_str(item.get("postDate") or bd.get("last_updated")),
                    location  = state_name,
                    short_info= safe_str(bd.get("short_information") or item.get("category")),
                    source_url= safe_str(item.get("url") or ""),
                    state     = [state_name] if state_name and state_name != "India" else [],
                    tags      = _extract_tags("Education", name, state_name),
                    raw_detail= detail if detail else item,
                )
                all_records.append(rec)
                cnt += 1
        print(f"   → {cnt} jobs loaded")

    # ── SOURCE 4: merged_sarkari_data.json ─────────────────────────
    print("[4] Loading merged_sarkari_data.json …")
    msd = load_json(SRC_MERGED)
    if msd:
        merged_jobs = msd.get("jobs", []) if isinstance(msd, dict) else (msd if isinstance(msd, list) else [])
        cnt = 0
        for job in merged_jobs:
            title = safe_str(job.get("title"))
            if not title:
                continue
            existing_slug = safe_str(job.get("slug"))
            slug = existing_slug if existing_slug else slugify(title)
            imp_dates = job.get("important_dates") or {}
            if isinstance(imp_dates, str):
                imp_dates = {}
            nd = safe_str(job.get("last_date") or imp_dates.get("last_date") or "")
            # Find best source URL
            src_url = (job.get("apply_online_link") or job.get("official_website_link")
                       or job.get("official_notification_pdf_link") or "")
            if not src_url:
                for lnk in (job.get("useful_links") or []):
                    if isinstance(lnk, dict):
                        href = lnk.get("links") or lnk.get("url") or ""
                        if isinstance(href, list): href = href[0] if href else ""
                        if str(href).startswith("http"):
                            src_url = str(href)
                            break
            cat = safe_str(job.get("category") or "Latest_Notifications")
            if cat not in VALID_CATS:
                cat = "Latest_Notifications"
            rec = make_normalised(
                title     = title,
                slug      = slug,
                category  = cat,
                org       = safe_str(job.get("organization") or job.get("post_name")),
                vacancies = safe_str(job.get("total_vacancy") or job.get("total_vacancies") or ""),
                last_date = nd,
                post_date = safe_str(job.get("listing_date") or job.get("post_date") or imp_dates.get("application_begin") or ""),
                apply_mode= safe_str(job.get("apply_mode") or "Online"),
                location  = safe_str(job.get("job_location") or "India"),
                short_info= safe_str(job.get("short_information") or job.get("jobs_info")),
                source_url= src_url,
                tags      = _extract_tags(cat, title, job.get("job_location", "")),
                raw_detail= job,
            )
            all_records.append(rec)
            cnt += 1
        print(f"   → {cnt} jobs loaded")

    # ── SOURCE 5: state-jobs-data.json ─────────────────────────────
    print("[5] Loading state-jobs-data.json …")
    sjd = load_json(SRC_STATE)
    if sjd:
        cnt = 0
        for sec in sjd.get("sections", []):
            state_name = safe_str(sec.get("state") or sec.get("title") or "India")
            for item in sec.get("items", []):
                name = safe_str(item.get("name") or item.get("title"))
                if not name:
                    continue
                slug    = safe_str(item.get("slug")) or slugify(name)
                detail  = item.get("detail") or {}
                if isinstance(detail, str):
                    try: detail = json.loads(detail)
                    except: detail = {}
                bd_raw    = (detail.get("basic_details") or {}) if detail else {}
                dates_raw = (detail.get("important_dates") or {}) if detail else {}
                if isinstance(bd_raw, str): bd_raw = {}
                if isinstance(dates_raw, str): dates_raw = {}
                nd = safe_str(item.get("lastDate") or dates_raw.get("last_date_to_apply") or "")
                rec = make_normalised(
                    title     = name,
                    slug      = slug,
                    category  = "STATE_JOBS",
                    org       = safe_str(bd_raw.get("post_name") or bd_raw.get("organization_name") or state_name),
                    vacancies = safe_str(bd_raw.get("total_vacancies") or ""),
                    last_date = nd,
                    post_date = safe_str(item.get("postDate") or item.get("date") or bd_raw.get("last_updated") or ""),
                    apply_mode= safe_str(bd_raw.get("application_mode") or "Online"),
                    location  = f"{state_name}, India",
                    short_info= safe_str(bd_raw.get("short_information")),
                    source_url= safe_str(item.get("url") or ""),
                    state     = [state_name],
                    tags      = _extract_tags("STATE_JOBS", name, state_name),
                    raw_detail= detail if detail else item,
                )
                all_records.append(rec)
                cnt += 1
        print(f"   → {cnt} jobs loaded")

    # ── SOURCE 6: dailyupdates.json (Top 20 + Today Updates only) ──
    print("[6] Loading dailyupdates.json …")
    DAILY_SECS = {"Top 20 Jobs", "Today Updates"}
    dju = load_json(SRC_DAILY)
    if dju:
        cnt = 0
        for sec in dju.get("sections", []):
            if sec.get("title") not in DAILY_SECS:
                continue
            for item in sec.get("items", []):
                name = safe_str(item.get("name") or item.get("title"))
                if not name:
                    continue
                slug = slugify(name)
                rec = make_normalised(
                    title     = name,
                    slug      = slug,
                    category  = "Latest_Notifications",
                    post_date = safe_str(item.get("date") or ""),
                    last_date = safe_str(item.get("lastDate") or item.get("date") or ""),
                    location  = "India",
                    source_url= safe_str(item.get("url") or item.get("link") or ""),
                    tags      = _extract_tags("Latest_Notifications", name, ""),
                    raw_detail= item,
                )
                all_records.append(rec)
                cnt += 1
        print(f"   → {cnt} jobs loaded")

    return all_records


def _extract_tags(category, title, location):
    """
    Build comprehensive tags list from available signals.
    """
    tags = []
    t = title.lower()
    l = (location or "").lower()

    # Education level tags
    if "10th" in t or "matric" in t or "ssc" in t:      tags.append("10th")
    if "12th" in t or "inter" in t or "higher secondary" in t: tags.append("12th")
    if "graduate" in t or "graduation" in t:              tags.append("graduate")
    if "post graduate" in t or "pg " in t:                tags.append("post-graduate")
    if "iti" in t:                                         tags.append("iti")
    if "diploma" in t:                                     tags.append("diploma")
    if "b.tech" in t or "b tech" in t or "btech" in t or "be " in t: tags.append("btech")
    if "mbbs" in t or "medical" in t:                     tags.append("medical")

    # Job type tags
    if "railway" in t or "rrb" in t or "rrc" in t:       tags.append("railway")
    if "bank" in t or "sbi" in t or "nabard" in t:        tags.append("bank")
    if "police" in t or "constable" in t:                 tags.append("police")
    if "army" in t or "navy" in t or "air force" in t or "defence" in t: tags.append("defence")
    if "teacher" in t or "faculty" in t or "lecturer" in t: tags.append("teaching")
    if "admit card" in t:                                  tags.append("admit-card")
    if "result" in t:                                      tags.append("result")
    if "answer key" in t:                                  tags.append("answer-key")
    if "admission" in t:                                   tags.append("admission")
    if "apprentice" in t:                                  tags.append("apprentice")

    # Category tags
    cat_tag_map = {
        "Railway_Jobs": "railway", "Bank_Jobs": "bank",
        "Police_Defence": "police", "Teaching_Faculty": "teaching",
        "Medical_Hospital": "medical", "10TH_Pass": "10th",
        "12TH_Pass": "12th", "8TH_Pass": "8th",
    }
    if category in cat_tag_map:
        t2 = cat_tag_map[category]
        if t2 not in tags:
            tags.append(t2)

    # Location / state tags
    STATES = ["haryana","rajasthan","up","uttar pradesh","bihar","maharashtra",
               "mp","madhya pradesh","gujarat","karnataka","tamil","andhra",
               "telangana","odisha","assam","punjab","kerala","jharkhand",
               "chhattisgarh","uttarakhand","himachal","jammu","delhi"]
    for st in STATES:
        if st in l or st in t:
            tags.append(st.replace(" ", "-"))
            break

    tags.append("latest")
    return list(dict.fromkeys(tags))   # preserve order, remove dups


# ══════════════════════════════════════════════════════════════════
#  STEP 4 — ADVANCED DEDUPLICATION
# ══════════════════════════════════════════════════════════════════
def deduplicate(records):
    """
    Priority:
      1. Slug-level dedup (keep first occurrence — Complete_Jobs first)
      2. title + lastDate dedup (fuzzy: normalised lower title)
    Returns clean list.
    """
    seen_slugs   = {}   # slug → index
    seen_titledt = {}   # (normalised_title, lastDate) → index
    unique = []

    for rec in records:
        slug = rec["slug"]
        key2 = (re.sub(r"\s+", " ", rec["title"].lower().strip()), rec["lastDate"])

        if slug in seen_slugs:
            # Slug collision — enrich existing with any missing detail
            existing = unique[seen_slugs[slug]]
            if not existing["detail"] and rec["detail"]:
                existing["detail"] = rec["detail"]
            continue

        if key2 in seen_titledt and key2[0]:
            existing = unique[seen_titledt[key2]]
            if not existing["detail"] and rec["detail"]:
                existing["detail"] = rec["detail"]
            # Keep slug mapping to this existing record
            seen_slugs[slug] = seen_titledt[key2]
            continue

        idx = len(unique)
        unique.append(rec)
        seen_slugs[slug]  = idx
        if key2[0]:
            seen_titledt[key2] = idx

    print(f"\n  Deduplication: {len(records)} raw → {len(unique)} unique records")
    return unique


# ══════════════════════════════════════════════════════════════════
#  STEP 5 — SEO HTML GENERATOR  (central, single render engine)
# ══════════════════════════════════════════════════════════════════
def build_job_html(rec):
    """
    Generate a complete, SEO-optimised index.html for one job.
    The JS renderer (preferred-source-renderer.js) handles dynamic
    section expansion from the paired .json file.
    """
    slug       = rec["slug"]
    title      = rec["title"]
    canon_url  = f"{BASE_URL}/data/jobs/{slug}/"
    cat        = rec["category"]
    cat_label  = CAT_LABELS.get(cat, "Government Jobs")
    org        = e(rec["org"] or "Government of India")
    vacancies  = e(rec["vacancies"] or "")
    last_date  = e(rec["lastDate"] or "")
    apply_mode = e(rec["applyMode"] or "Online")
    location   = e(rec["location"] or "India")
    short_info = e(rec["shortInfo"] or "")
    post_date  = rec["postDate"] or TODAY

    # Derive from raw detail if available
    detail    = rec.get("detail") or {}
    bd        = detail.get("basic_details") or {}
    salary_d  = detail.get("salary_details") or {}
    qual_d    = detail.get("qualification") or {}

    sal_str   = ""
    if isinstance(salary_d, dict):
        sal_str = e(salary_d.get("pay_scale") or salary_d.get("salary") or "")
    elif isinstance(salary_d, str):
        sal_str = e(salary_d)

    qual_str  = ""
    if isinstance(qual_d, dict):
        qual_str = e(qual_d.get("essential_qualification") or qual_d.get("qualification") or "")
    elif isinstance(qual_d, str):
        qual_str = e(qual_d)

    # ── Meta description ≤ 155 chars ──
    _vac   = f"{vacancies} vacancies, " if vacancies else ""
    _ld    = f"last date {last_date}. " if last_date else ""
    _sal   = f"Salary: {sal_str[:40]}. " if sal_str else ""
    _qual  = f"{qual_str[:50]} eligible. " if qual_str else ""
    meta_desc = f"{e(title)}: {_vac}{_ld}{_sal}{_qual}Apply online – TopSarkariJobs."
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152].rsplit(" ", 1)[0].rstrip(".,–") + "…"

    # ── SEO Title ≤ 60 chars ──
    _yr   = re.search(r"20\d\d", title)
    _yr   = _yr.group() if _yr else ""
    _vn   = re.search(r"\d+", rec["vacancies"]) if rec["vacancies"] else None
    _vtag = f" – {_vn.group()} Posts" if _vn else ""
    _short = re.split(r"\s+(?:–|-|Notification|Recruitment)\s+", title)[0].strip()
    _short = _short[:30].rstrip() if len(_short) > 30 else _short
    title_tag = f"{_short}{' '+_yr if _yr and _yr not in _short else ''}{_vtag}"
    if len(title_tag) + len(" | Top Sarkari Jobs") > 60:
        title_tag = title[:40].rstrip()
    full_title_tag = f"{title_tag} | Top Sarkari Jobs"

    # ── JSON-LD: JobPosting schema ──
    org_name    = rec["org"] or bd.get("organization_name") or "Government of India"
    job_schema  = {
        "@context"   : "https://schema.org",
        "@type"      : "JobPosting",
        "title"      : title,
        "description": rec["shortInfo"] or meta_desc,
        "datePosted" : post_date,
        "employmentType": "FULL_TIME",
        "url"        : canon_url,
        "identifier" : {"@type":"PropertyValue","name":org_name,"value":slug},
        "applicantLocationRequirements": {"@type":"Country","name":"India"},
        "hiringOrganization": {
            "@type" : "Organization",
            "name"  : org_name,
            "sameAs": "https://www.india.gov.in"
        },
        "jobLocation": {
            "@type"  : "Place",
            "address": {
                "@type"           : "PostalAddress",
                "addressCountry"  : "IN",
                "addressRegion"   : "India",
                "addressLocality" : rec["location"] or "India",
            }
        },
        "author": {
            "@type": "Organization",
            "name" : "TopSarkariJobs Editorial Team",
            "url"  : "https://www.topsarkarijobs.com/about.html"
        }
    }
    if rec["lastDate"]:
        iso = normalise_date(rec["lastDate"])
        if iso:
            job_schema["validThrough"] = iso
    if rec["vacancies"]:
        vn = re.search(r"\d+", rec["vacancies"])
        if vn:
            job_schema["totalJobOpenings"] = int(vn.group())
    if qual_str:
        job_schema["educationRequirements"] = {
            "@type"              : "EducationalOccupationalCredential",
            "credentialCategory" : qual_str[:200]
        }
    if sal_str:
        _sm = re.search(r"(\d[\d,]+)", sal_str.replace(",",""))
        if _sm:
            _sv = int(re.sub(r"\D","", _sm.group()))
            job_schema["baseSalary"] = {
                "@type":"MonetaryAmount","currency":"INR",
                "value":{"@type":"QuantitativeValue","value":_sv,"unitText":"MONTH"}
            }
    else:
        job_schema["baseSalary"] = {
            "@type":"MonetaryAmount","currency":"INR",
            "value":{"@type":"QuantitativeValue","minValue":15000,"maxValue":80000,"unitText":"MONTH"}
        }

    # ── JSON-LD: FAQ schema ──
    _ld_faq  = last_date or "official notification dekhein"
    _q_faq   = qual_str[:100] if qual_str else "official notification dekhein"
    _s_faq   = sal_str[:80]   if sal_str  else "as per government norms"
    faq_schema = {
        "@context"   : "https://schema.org",
        "@type"      : "FAQPage",
        "mainEntity" : [
            {"@type":"Question","name":f"{title} last date kya hai?",
             "acceptedAnswer":{"@type":"Answer","text":f"Last date: {_ld_faq}."}},
            {"@type":"Question","name":f"{title} ke liye qualification kya chahiye?",
             "acceptedAnswer":{"@type":"Answer","text":f"Qualification: {_q_faq}."}},
            {"@type":"Question","name":f"{title} mein salary kitni hai?",
             "acceptedAnswer":{"@type":"Answer","text":f"Salary: {_s_faq}."}},
            {"@type":"Question","name":f"How to apply for {title}?",
             "acceptedAnswer":{"@type":"Answer","text":f"Visit official website or apply online at {canon_url}"}},
        ]
    }

    # ── JSON-LD: BreadcrumbList schema ──
    bc_schema = {
        "@context"        : "https://schema.org",
        "@type"           : "BreadcrumbList",
        "itemListElement" : [
            {"@type":"ListItem","position":1,"name":"Home","item":f"{BASE_URL}/"},
            {"@type":"ListItem","position":2,"name":cat_label,"item":f"{BASE_URL}/section/{cat.lower().replace('_','-')}/"},
            {"@type":"ListItem","position":3,"name":title,"item":canon_url},
        ]
    }

    # ── JSON-LD: Article schema ──
    article_schema = {
        "@context"       : "https://schema.org",
        "@type"          : "Article",
        "headline"       : title,
        "description"    : rec["shortInfo"] or meta_desc,
        "datePublished"  : post_date,
        "dateModified"   : TODAY,
        "url"            : canon_url,
        "image"          : f"{BASE_URL}/image.ico",
        "author"         : {"@type":"Organization","name":"TopSarkariJobs","url":BASE_URL},
        "publisher"      : {
            "@type" : "Organization",
            "name"  : "Top Sarkari Jobs",
            "url"   : BASE_URL,
            "logo"  : {"@type":"ImageObject","url":f"{BASE_URL}/image.ico"}
        },
        "mainEntityOfPage": {"@type":"WebPage","@id":canon_url},
    }

    # ── Tags / keywords ──
    keywords = ", ".join(rec.get("tags", []) + [title[:60]])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{e(full_title_tag)}</title>
  <meta name="description" content="{e(meta_desc)}"/>
  <meta name="keywords" content="{e(keywords)}"/>
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"/>
  <link rel="canonical" href="{canon_url}"/>
  <link rel="alternate" hreflang="en"     href="{canon_url}"/>
  <link rel="alternate" hreflang="en-IN"  href="{canon_url}"/>
  <link rel="alternate" hreflang="x-default" href="{canon_url}"/>
  <!-- Open Graph -->
  <meta property="og:type"        content="article"/>
  <meta property="og:site_name"   content="Top Sarkari Jobs"/>
  <meta property="og:title"       content="{e(full_title_tag)}"/>
  <meta property="og:description" content="{e(meta_desc)}"/>
  <meta property="og:url"         content="{canon_url}"/>
  <meta property="og:image"       content="{BASE_URL}/image.ico"/>
  <meta property="og:locale"      content="en_IN"/>
  <!-- Twitter Card -->
  <meta name="twitter:card"        content="summary"/>
  <meta name="twitter:title"       content="{e(full_title_tag)}"/>
  <meta name="twitter:description" content="{e(meta_desc)}"/>
  <!-- Preconnect for performance -->
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="dns-prefetch" href="//www.topsarkarijobs.com"/>
  <!-- Stylesheets -->
  <link rel="stylesheet" href="/all.min.css"/>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" crossorigin="anonymous"/>
  <!-- JSON-LD Schemas -->
  <script type="application/ld+json">{json.dumps(job_schema,    ensure_ascii=False, separators=(',',':'))}</script>
  <script type="application/ld+json">{json.dumps(faq_schema,    ensure_ascii=False, separators=(',',':'))}</script>
  <script type="application/ld+json">{json.dumps(bc_schema,     ensure_ascii=False, separators=(',',':'))}</script>
  <script type="application/ld+json">{json.dumps(article_schema,ensure_ascii=False, separators=(',',':'))}</script>
</head>
<body>
  <!-- HEADER -->
  <div id="header-placeholder"></div>

  <!-- MAIN CONTENT -->
  <main id="main-content" data-slug="{e(slug)}" data-json="/data/jobs/{e(slug)}.json">

    <!-- Static SEO content — rendered by preferred-source-renderer.js -->
    <div id="psr-v4-root">
      <!-- Hero -->
      <section class="job-hero" itemscope itemtype="https://schema.org/JobPosting">
        <h1 itemprop="title">{e(title)}</h1>
        <p class="job-org"  itemprop="hiringOrganization">{org}</p>
        <div class="job-meta-strip">
          {f'<span class="jm-badge jm-vacancies"><i class="fa fa-users"></i> {vacancies} Posts</span>' if vacancies else ""}
          {f'<span class="jm-badge jm-lastdate"><i class="fa fa-calendar"></i> Last Date: {last_date}</span>' if last_date else ""}
          {f'<span class="jm-badge jm-mode"><i class="fa fa-laptop"></i> {apply_mode}</span>' if apply_mode else ""}
          {f'<span class="jm-badge jm-location"><i class="fa fa-map-marker"></i> {location}</span>' if location else ""}
        </div>
        {f'<p class="job-short-info" itemprop="description">{short_info}</p>' if short_info else ""}
      </section>

      <!-- Breadcrumbs -->
      <nav aria-label="Breadcrumb" class="breadcrumb-nav">
        <ol>
          <li><a href="/">Home</a></li>
          <li><a href="/section/{cat.lower().replace('_','-')}/">{e(cat_label)}</a></li>
          <li aria-current="page">{e(title[:60])}</li>
        </ol>
      </nav>

      <!-- Dynamic renderer target — JS fills this -->
      <div id="psr-v4-card" role="main"></div>
    </div>

  </main>

  <!-- FOOTER -->
  <div id="footer-placeholder"></div>

  <!-- Single render engine -->
  <script src="/preferred-source-renderer.js?v=5.0" defer></script>
  <script src="/seo-engine.js?v=5.0"               defer></script>
  <script src="/analytics.js"                       defer></script>
  <script src="/sw-register.js"                     defer></script>

</body>
</html>
"""


# ══════════════════════════════════════════════════════════════════
#  STEP 6 — WRITE FILES
# ══════════════════════════════════════════════════════════════════
def write_job_files(records):
    """
    For each deduplicated record:
      • data/jobs/{slug}/index.html  — static SEO HTML
      • data/jobs/{slug}.json        — full JSON for renderer
    Returns (index dict, written count, skipped count)
    """
    os.makedirs(JOBS_HTML_DIR, exist_ok=True)
    index   = {}
    written = 0
    skipped = 0

    for rec in records:
        slug = rec["slug"]
        if not slug:
            skipped += 1
            continue

        # ── Write JSON data file ──
        json_path = os.path.join(JOBS_DATA_DIR, f"{slug}.json")
        json_out = dict(rec)
        # Flatten detail fields for renderer compatibility
        if rec.get("detail"):
            for k, v in rec["detail"].items():
                if k not in json_out:
                    json_out[k] = v
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_out, f, ensure_ascii=False, separators=(",", ":"))

        # ── Write HTML file ──
        html_dir  = os.path.join(JOBS_HTML_DIR, slug)
        html_path = os.path.join(html_dir, "index.html")
        os.makedirs(html_dir, exist_ok=True)

        html_content = build_job_html(rec)
        # Only overwrite if content changed (save I/O on re-runs)
        existing = None
        if os.path.exists(html_path):
            with open(html_path, encoding="utf-8") as f:
                existing = f.read()
        if existing != html_content:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            written += 1
        else:
            skipped += 1

        # ── Index entry ──
        index[slug] = {
            "title"    : rec["title"][:120],
            "cat"      : rec["category"],
            "lastDate" : rec["lastDate"][:30] if rec["lastDate"] else "",
            "location" : rec["location"][:80],
            "tags"     : rec["tags"],
            "url"      : f"/data/jobs/{slug}/",
        }

    return index, written, skipped


# ══════════════════════════════════════════════════════════════════
#  STEP 7 — SECTIONS INDEX (listing only — no duplicate HTML)
# ══════════════════════════════════════════════════════════════════
def build_sections_index(records):
    """
    Build sections-index.json: category → [{slug, name, date, url}]
    Category pages use this to LIST jobs without generating HTML.
    NO duplicate detail pages.
    """
    by_cat = defaultdict(list)
    for rec in records:
        by_cat[rec["category"]].append({
            "slug"  : rec["slug"],
            "name"  : rec["title"],
            "date"  : rec["lastDate"],
            "url"   : f"/data/jobs/{rec['slug']}/",
            "org"   : rec["org"],
            "vac"   : rec["vacancies"],
        })

    with open(SECTIONS_INDEX, "w", encoding="utf-8") as f:
        json.dump(by_cat, f, ensure_ascii=False, separators=(",", ":"))

    total = sum(len(v) for v in by_cat.values())
    print(f"\n  sections-index.json: {total} entries across {len(by_cat)} categories")
    return by_cat


# ══════════════════════════════════════════════════════════════════
#  STEP 8 — SITEMAP (jobs only — /data/jobs/{slug}/)
# ══════════════════════════════════════════════════════════════════
def build_sitemap(records):
    """
    Sitemap includes ONLY /data/jobs/{slug}/ — no category pages,
    no state pages, no duplicate pages.
    """
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
    ]
    for rec in records:
        slug     = rec["slug"]
        lastmod  = rec["postDate"] or TODAY
        priority = "0.9" if rec["category"] == "Latest_Notifications" else "0.8"
        lines.append(f"""  <url>
    <loc>{BASE_URL}/data/jobs/{slug}/</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>{priority}</priority>
  </url>""")
    lines.append("</urlset>")

    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  {SITEMAP_FILE}: {len(records)} URLs")


# ══════════════════════════════════════════════════════════════════
#  STEP 9 — CLEANUP STALE FILES
# ══════════════════════════════════════════════════════════════════
def cleanup_stale(records):
    """Remove job JSON/HTML that no longer exist in source data."""
    if not os.path.isdir(JOBS_DATA_DIR):
        return
    live_slugs = {rec["slug"] for rec in records}

    # JSON files
    removed_json = 0
    for f in os.listdir(JOBS_DATA_DIR):
        if f.endswith(".json"):
            slug = f[:-5]
            if slug not in live_slugs:
                try:
                    os.remove(os.path.join(JOBS_DATA_DIR, f))
                    removed_json += 1
                except: pass

    # HTML dirs
    removed_html = 0
    for d in os.listdir(JOBS_HTML_DIR):
        full_path = os.path.join(JOBS_HTML_DIR, d)
        if os.path.isdir(full_path) and d not in live_slugs:
            try:
                shutil.rmtree(full_path)
                removed_html += 1
            except: pass

    if removed_json or removed_html:
        print(f"  Cleanup: {removed_json} stale JSON, {removed_html} stale HTML dirs removed")


# ══════════════════════════════════════════════════════════════════
#  STEP 10 — REBUILD data/ SECTION JSON FILES
# ══════════════════════════════════════════════════════════════════
def rebuild_section_data_files(records):
    """
    Rebuild data/sr-*.json, data/state-jobs.json etc from merged data.
    These feed the homepage and section listing pages.
    """
    os.makedirs("data", exist_ok=True)

    FILE_MAP = {
        "Latest_Notifications" : "data/latest-jobs-new.json",
        "STATE_JOBS"           : "data/state-jobs.json",
        "OFFLINE_FORM"         : "data/offline-form.json",
        "Railway_Jobs"         : "data/railway-jobs.json",
        "Bank_Jobs"            : "data/bank-jobs.json",
        "Police_Defence"       : "data/defence-jobs.json",
        "Teaching_Faculty"     : "data/teaching-jobs.json",
        "Medical_Hospital"     : "data/medical-jobs.json",
        "10TH_Pass"            : "data/10th-pass-jobs.json",
        "12TH_Pass"            : "data/12th-pass-jobs.json",
        "Any_Graduate"         : "data/graduate-jobs.json",
    }

    by_cat = defaultdict(list)
    for rec in records:
        by_cat[rec["category"]].append({
            "slug"     : rec["slug"],
            "title"    : rec["title"],
            "org"      : rec["org"],
            "vacancies": rec["vacancies"],
            "lastDate" : rec["lastDate"],
            "location" : rec["location"],
            "url"      : f"/data/jobs/{rec['slug']}/",
            "tags"     : rec["tags"],
        })

    for cat, filepath in FILE_MAP.items():
        items = by_cat.get(cat, [])
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"category": cat, "total": len(items), "jobs": items},
                      f, ensure_ascii=False, separators=(",", ":"))
        print(f"  {filepath}: {len(items)} items")

    # merged-summary.json — top 10 per category for homepage cards
    summary_jobs = []
    for cat, items in by_cat.items():
        summary_jobs.extend(items[:10])
    with open("data/merged-summary.json", "w", encoding="utf-8") as f:
        json.dump({"generated": TODAY, "total": len(summary_jobs), "jobs": summary_jobs},
                  f, ensure_ascii=False, separators=(",", ":"))
    print(f"  data/merged-summary.json: {len(summary_jobs)} items (top 10 per category)")


# ══════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════
def main():
    print("=" * 65)
    print("  TOP SARKARI JOBS — Master Build Pipeline v5.0")
    print(f"  Run date: {TODAY}")
    print("=" * 65)

    # 1. Merge all sources
    raw_records = merge_all_sources()
    print(f"\n  Total raw records: {len(raw_records)}")

    # 2. Deduplicate
    records = deduplicate(raw_records)

    # 3. Write job HTML + JSON files
    print("\n[7] Writing job files …")
    os.makedirs(JOBS_HTML_DIR, exist_ok=True)
    index, written, skipped = write_job_files(records)
    print(f"  Written (new/changed): {written} | Skipped (unchanged): {skipped}")

    # 4. Write master index
    print("\n[8] Writing index …")
    with open(JOBS_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  {JOBS_INDEX}: {len(index)} entries")

    # 5. Build sections index (listing only — no dup HTML)
    print("\n[9] Building sections index …")
    build_sections_index(records)

    # 6. Build sitemap
    print("\n[10] Building sitemap …")
    build_sitemap(records)

    # 7. Cleanup stale files
    print("\n[11] Cleaning up stale files …")
    cleanup_stale(records)

    # 8. Rebuild section data files
    print("\n[12] Rebuilding section data JSON files …")
    rebuild_section_data_files(records)

    print("\n" + "=" * 65)
    print(f"  ✅ DONE!")
    print(f"  Total unique jobs  : {len(records)}")
    print(f"  HTML pages written : {written}")
    print(f"  HTML pages skipped : {skipped} (unchanged)")
    print(f"  Index entries      : {len(index)}")
    print(f"  Sitemap URLs       : {len(records)}")
    print("=" * 65)


if __name__ == "__main__":
    main()
