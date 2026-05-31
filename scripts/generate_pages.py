#!/usr/bin/env python3
"""
Top Sarkari Jobs — Static HTML Generator
Tasks 1+2+3+4+5+6+7 combined
Input:  data/Complete_Jobs_Full_Data.json
Output: jobs/{slug}/index.html (one per NEW job)
        data/master_clean_jobs.json
"""

import json, os, re, unicodedata, html as htmllib
from pathlib import Path

BASE_URL = "https://www.topsarkarijobs.com"
OUTPUT_DIR = Path("jobs")
DATA_FILE = Path("data/Complete_Jobs_Full_Data.json")

BLOCKED_DOMAINS = {
    "sarkariresult.com", "www.sarkariresult.com",
    "freejobalert.com", "www.freejobalert.com",
    "sarkarinetwork.com", "www.sarkarinetwork.com",
    "sarkariresultshine.com", "www.sarkariresultshine.com",
}

# ── Slug Generator (EXACT — matches existing 2722 pages) ─────────────
def generate_slug(title):
    if not title: return ""
    t = unicodedata.normalize("NFKD", str(title))
    t = t.encode("ascii", "ignore").decode("ascii")
    t = t.replace("&", " and ")
    for ch in "''`\"": t = t.replace(ch, "")
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = t.strip("-")
    t = re.sub(r"-{2,}", "-", t)
    return t[:120] or "official-link"

# ── Date Normalizer ───────────────────────────────────────────────────
def normalize_date(raw):
    if not raw: return ""
    raw = str(raw).strip()
    patterns = [
        (r'^(\d{4})-(\d{2})-(\d{2})', lambda m: f"{m.group(3)}-{m.group(2)}-{m.group(1)}"),
        (r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})', lambda m: f"{m.group(1).zfill(2)}-{m.group(2).zfill(2)}-{m.group(3)}"),
    ]
    for pat, fmt in patterns:
        m = re.match(pat, raw)
        if m: return fmt(m)
    return raw[:20]

def normalize_title(t):
    return re.sub(r'[^a-z0-9]', '', str(t).lower().strip())

# ── HTML Escaper ──────────────────────────────────────────────────────
def esc(s): return htmllib.escape(str(s or ""))

# ── Blocked URL checker ───────────────────────────────────────────────
def is_blocked_url(url):
    if not url or not isinstance(url, str): return True
    url_lower = url.strip().lower()
    for domain in BLOCKED_DOMAINS:
        if domain in url_lower: return True
    return False

def filter_links(links_data):
    if not isinstance(links_data, dict): return {}
    clean = {}
    for key, val in links_data.items():
        if isinstance(val, str) and not is_blocked_url(val):
            clean[key] = val
        elif isinstance(val, list):
            filtered = [v for v in val if isinstance(v, str) and not is_blocked_url(v)]
            if filtered:
                clean[key] = filtered
    return clean

# ── Section Renderer: dict/list → HTML ───────────────────────────────
def render_section(data):
    if not data: return ""
    if isinstance(data, str):
        return f'<div class="job-text-block">{esc(data)}</div>'
    if isinstance(data, list):
        items = "".join(f"<li>{esc(str(item))}</li>" for item in data if item)
        return f'<ul class="job-list">{items}</ul>' if items else ""
    if isinstance(data, dict):
        rows = ""
        for k, v in data.items():
            if v is None or v == "" or v == {} or v == []: continue
            key_label = str(k).replace("_", " ").title()
            if isinstance(v, (dict, list)):
                val_html = render_section(v)
            else:
                val_str = str(v)
                if val_str.startswith("http") and not is_blocked_url(val_str):
                    val_html = f'<a href="{esc(val_str)}" target="_blank" rel="noopener noreferrer">{esc(val_str[:60])}</a>'
                elif val_str.startswith("http") and is_blocked_url(val_str):
                    continue  # skip blocked URLs
                else:
                    val_html = esc(val_str)
            rows += f"<tr><th>{esc(key_label)}</th><td>{val_html}</td></tr>"
        if rows:
            return f'<div class="table-scroll"><table class="info-table"><tbody>{rows}</tbody></table></div>'
    return ""

# ── Extract ALL Jobs from JSON (Task 1) ───────────────────────────────
def extract_all_jobs(data):
    all_jobs = []

    # Source 1: freejobalert_categories (2830 jobs)
    for cat, jobs in data.get("freejobalert_categories", {}).items():
        if not isinstance(jobs, list): continue
        for job in jobs:
            bd = job.get("basic_details", {})
            title = bd.get("job_title", "")
            if not title: continue
            dates = job.get("important_dates", {})
            last_date = (dates.get("last_date_to_apply") or
                         dates.get("last_date") or
                         dates.get("Last Date to Apply") or
                         dates.get("Last Date") or "")
            notif_date = (dates.get("notification date") or
                          dates.get("Notification Date") or
                          bd.get("last_updated") or "")
            all_jobs.append({
                "slug": generate_slug(title),
                "title": title,
                "organization": bd.get("organization_name", ""),
                "post_name": bd.get("post_name", ""),
                "total_vacancies": str(bd.get("total_vacancies", "")),
                "application_mode": bd.get("application_mode", ""),
                "job_type": bd.get("job_type", ""),
                "short_info": bd.get("short_information", ""),
                "last_date": last_date,
                "last_updated": bd.get("last_updated", ""),
                "notification_date": notif_date,
                "category": cat,
                "source": "freejobalert",
                "important_dates": job.get("important_dates", {}),
                "application_fee": job.get("application_fee", {}),
                "age_limit": job.get("age_limit", {}),
                "qualification": job.get("qualification", {}),
                "vacancy_details": job.get("vacancy_details", {}),
                "category_wise_vacancy": job.get("category_wise_vacancy", {}),
                "salary_details": job.get("salary_details", {}),
                "selection_process": job.get("selection_process", {}),
                "exam_pattern": job.get("exam_pattern", {}),
                "syllabus": job.get("syllabus", {}),
                "physical_eligibility": job.get("physical_eligibility", {}),
                "how_to_apply": job.get("how_to_apply", {}),
                "important_instructions": job.get("important_instructions", {}),
                "important_links": filter_links(job.get("important_links", {})),
                "faq": job.get("faq", {}),
                "seo_tags": job.get("seo_tags", {}),
            })

    # Source 2: sarkari_data (302 jobs)
    for job in data.get("sarkari_data", {}).get("jobs", []):
        title = job.get("title", "")
        if not title: continue
        all_jobs.append({
            "slug": generate_slug(title),
            "title": title,
            "organization": job.get("organization", ""),
            "post_name": job.get("post_name", ""),
            "total_vacancies": str(job.get("total_vacancy", "")),
            "application_mode": job.get("apply_mode", ""),
            "job_type": "",
            "short_info": "",
            "last_date": job.get("important_dates", {}).get("Last Date", ""),
            "last_updated": job.get("listing_date", ""),
            "notification_date": "",
            "category": job.get("category", ""),
            "source": "sarkari",
            "important_dates": job.get("important_dates", {}),
            "application_fee": {},
            "age_limit": {},
            "qualification": {},
            "vacancy_details": {},
            "category_wise_vacancy": {},
            "salary_details": {"salary": job.get("salary_pay_scale", "")},
            "selection_process": {},
            "exam_pattern": {},
            "syllabus": {},
            "physical_eligibility": {},
            "how_to_apply": {},
            "important_instructions": {},
            "important_links": filter_links(job.get("important_links", {})),
            "faq": {},
            "seo_tags": {},
        })

    # Source 3: education_jobs
    for section in data.get("education_jobs", {}).get("sections", []):
        cat = section.get("category", section.get("title", "education"))
        for item in section.get("items", []):
            title = item.get("title", "")
            if not title: continue
            all_jobs.append({
                "slug": generate_slug(title),
                "title": title,
                "organization": item.get("organization", item.get("org", "")),
                "post_name": item.get("post_name", ""),
                "total_vacancies": str(item.get("total_vacancies", item.get("vacancies", ""))),
                "application_mode": item.get("application_mode", "Online"),
                "job_type": "",
                "short_info": item.get("short_info", item.get("description", "")),
                "last_date": item.get("last_date", ""),
                "last_updated": item.get("last_updated", ""),
                "notification_date": "",
                "category": cat,
                "source": "education",
                "important_dates": item.get("important_dates", {}),
                "application_fee": item.get("application_fee", {}),
                "age_limit": item.get("age_limit", {}),
                "qualification": item.get("qualification", {}),
                "vacancy_details": item.get("vacancy_details", {}),
                "category_wise_vacancy": {},
                "salary_details": item.get("salary_details", {}),
                "selection_process": item.get("selection_process", {}),
                "exam_pattern": {},
                "syllabus": {},
                "physical_eligibility": {},
                "how_to_apply": {},
                "important_instructions": {},
                "important_links": filter_links(item.get("important_links", {})),
                "faq": {},
                "seo_tags": {},
            })

    # Source 4: state_jobs
    for section in data.get("state_jobs", {}).get("sections", []):
        cat = section.get("category", section.get("title", "state"))
        for item in section.get("items", []):
            title = item.get("title", "")
            if not title: continue
            all_jobs.append({
                "slug": generate_slug(title),
                "title": title,
                "organization": item.get("organization", item.get("org", "")),
                "post_name": item.get("post_name", ""),
                "total_vacancies": str(item.get("total_vacancies", item.get("vacancies", ""))),
                "application_mode": item.get("application_mode", "Online"),
                "job_type": "",
                "short_info": item.get("short_info", item.get("description", "")),
                "last_date": item.get("last_date", ""),
                "last_updated": item.get("last_updated", ""),
                "notification_date": "",
                "category": cat,
                "source": "state",
                "important_dates": item.get("important_dates", {}),
                "application_fee": item.get("application_fee", {}),
                "age_limit": item.get("age_limit", {}),
                "qualification": item.get("qualification", {}),
                "vacancy_details": item.get("vacancy_details", {}),
                "category_wise_vacancy": {},
                "salary_details": item.get("salary_details", {}),
                "selection_process": item.get("selection_process", {}),
                "exam_pattern": {},
                "syllabus": {},
                "physical_eligibility": {},
                "how_to_apply": {},
                "important_instructions": {},
                "important_links": filter_links(item.get("important_links", {})),
                "faq": {},
                "seo_tags": {},
            })

    return all_jobs

# ── Deduplication (Task 1) ────────────────────────────────────────────
def deduplicate(jobs):
    seen_slugs = set()
    seen_keys = set()
    clean = []
    for job in jobs:
        slug = job.get("slug", "")
        title = job.get("title", "")
        if not slug or not title: continue
        title_norm = normalize_title(title)
        date_norm = normalize_date(job.get("last_date", ""))
        composite_key = f"{title_norm}|{date_norm}"
        if slug in seen_slugs: continue
        if composite_key in seen_keys and title_norm: continue
        seen_slugs.add(slug)
        seen_keys.add(composite_key)
        clean.append(job)
    return clean

# ── HTML Generator (Tasks 2+3+4+5+6) ─────────────────────────────────
def generate_html(job):
    slug = job["slug"]
    title = job["title"]
    org = job.get("organization") or "Government of India"
    posts = job.get("total_vacancies") or "Various"
    last_date = job.get("last_date") or "See Notification"
    mode = job.get("application_mode") or "Online"
    short_info = job.get("short_info", "")
    year = "2026"

    seo_title = f"{title} | Top Sarkari Jobs"
    if len(seo_title) > 60:
        seo_title = seo_title[:57] + "..."
    meta_desc = f"{title}: {posts} vacancies, last date {last_date}. {short_info[:80] if short_info else org + ' recruitment ' + year}."
    meta_desc = meta_desc[:160]
    canonical = f"{BASE_URL}/jobs/{slug}/"

    # JobPosting schema (Task 4 — CORRECTED: org name fix)
    job_schema_obj = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "description": short_info or f"{org} is recruiting {posts} posts.",
        "datePosted": job.get("notification_date") or job.get("last_updated", ""),
        "validThrough": last_date,
        "employmentType": "FULL_TIME",
        "url": canonical,
        "identifier": {"@type": "PropertyValue", "name": job.get("post_name", title), "value": slug},
        "hiringOrganization": {
            "@type": "Organization",
            "name": org,  # FIX: use org, not post_name
            "sameAs": "https://www.india.gov.in"
        },
        "applicantLocationRequirements": {"@type": "Country", "name": "India"},
        "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressCountry": "IN"}},
        "author": {"@type": "Organization", "name": "TopSarkariJobs Editorial Team", "url": f"{BASE_URL}/about.html"}
    }
    vac_str = str(posts)
    if vac_str.isdigit():
        job_schema_obj["totalJobOpenings"] = int(vac_str)

    job_schema = json.dumps(job_schema_obj, ensure_ascii=False)

    breadcrumb_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "Latest Jobs", "item": f"{BASE_URL}/section/latest-jobs/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": canonical}
        ]
    }, ensure_ascii=False)

    # FAQ — minimum 6 (Task 4)
    faq_items = [
        (f"{title} last date kya hai?", f"Last date: {last_date}."),
        (f"{title} ke liye eligibility kya hai?", "Qualification: Official notification dekhein."),
        (f"{title} mein total vacancies kitni hain?", f"Total {posts} posts hain."),
        (f"{title} apply kaise karein?", f"{mode} mode mein apply kar sakte hain. Official website par jakar apply karein."),
        (f"{org} ki recruitment {year} kab tak hai?", f"Last date {last_date} hai. Time par apply karein."),
        (f"{title} ka selection process kya hai?", "Written Test / Interview. Exact process ke liye official notification dekhein."),
    ]

    # Use actual FAQ if available, supplement
    job_faqs = job.get("faq", {})
    if isinstance(job_faqs, dict) and job_faqs:
        custom = []
        for q, a in list(job_faqs.items())[:4]:
            if q and a:
                custom.append((str(q)[:200], str(a)[:300]))
        if custom:
            faq_items = custom + faq_items[len(custom):]
    faq_items = faq_items[:6]

    faq_qa_html = "\n".join(
        f'<div class="faq-item"><h3 class="faq-q"><i class="fa-solid fa-circle-question"></i> {esc(q)}</h3>'
        f'<div class="faq-a"><p>{esc(a)}</p></div></div>'
        for q, a in faq_items
    )

    faq_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq_items
        ]
    }, ensure_ascii=False)

    article_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "url": canonical,
        "author": {"@type": "Organization", "name": "TopSarkariJobs Editorial Team"},
        "publisher": {"@type": "Organization", "name": "Top Sarkari Jobs", "url": BASE_URL},
    }, ensure_ascii=False)

    # Build content sections
    sections_html = ""

    # Important Dates
    if job.get("important_dates"):
        dates_rows = ""
        for k, v in job["important_dates"].items():
            if v and str(v).strip():
                dates_rows += f"<tr><td>{esc(str(k).replace('_',' ').title())}</td><td><strong>{esc(str(v))}</strong></td></tr>"
        if dates_rows:
            sections_html += f"""
    <section class="job-card" id="important-dates">
      <div class="job-card-head" style="background:linear-gradient(135deg,#0f766e,#0d9488)">
        <i class="fa-solid fa-calendar-days"></i><h2>Important Dates</h2>
      </div>
      <div class="job-card-body">
        <div class="table-scroll"><table class="info-table"><tbody>{dates_rows}</tbody></table></div>
      </div>
    </section>"""

    section_map = [
        ("application_fee",       "Application Fee",            "fa-indian-rupee-sign",   "linear-gradient(135deg,#dc2626,#b91c1c)"),
        ("age_limit",             "Age Limit",                  "fa-user-clock",           "linear-gradient(135deg,#7c3aed,#6d28d9)"),
        ("qualification",         "Qualification / Eligibility","fa-graduation-cap",       "linear-gradient(135deg,#0284c7,#0369a1)"),
        ("vacancy_details",       "Vacancy Details",            "fa-users",                "linear-gradient(135deg,#059669,#047857)"),
        ("category_wise_vacancy", "Category Wise Vacancy",      "fa-table",                "linear-gradient(135deg,#047857,#065f46)"),
        ("salary_details",        "Salary / Pay Scale",         "fa-money-bill-wave",      "linear-gradient(135deg,#ca8a04,#a16207)"),
        ("selection_process",     "Selection Process",          "fa-list-check",           "linear-gradient(135deg,#4f46e5,#4338ca)"),
        ("exam_pattern",          "Exam Pattern",               "fa-file-alt",             "linear-gradient(135deg,#0e7490,#0891b2)"),
        ("syllabus",              "Syllabus",                   "fa-book-open",            "linear-gradient(135deg,#16a34a,#15803d)"),
        ("physical_eligibility",  "Physical Eligibility",       "fa-person-running",       "linear-gradient(135deg,#b45309,#92400e)"),
        ("how_to_apply",          "How To Apply",               "fa-pen-to-square",        "linear-gradient(135deg,#1e40af,#1e3a8a)"),
        ("important_instructions","Important Instructions",     "fa-triangle-exclamation", "linear-gradient(135deg,#e11d48,#be123c)"),
    ]

    for key, label, icon, color in section_map:
        content = job.get(key)
        if not content: continue
        rendered = render_section(content)
        if not rendered: continue
        sections_html += f"""
    <section class="job-card" id="{key.replace('_','-')}">
      <div class="job-card-head" style="background:{color}">
        <i class="fa-solid {icon}"></i><h2>{label}</h2>
      </div>
      <div class="job-card-body">{rendered}</div>
    </section>"""

    # Important Links (Task 6 — filtered)
    links = filter_links(job.get("important_links", {}))
    links_html = ""
    link_map = {
        "apply_online":            ("Apply Online",          "btn-green",  "fa-pen-to-square"),
        "apply_online_link":       ("Apply Online",          "btn-green",  "fa-pen-to-square"),
        "notification_pdf":        ("Download Notification", "btn-blue",   "fa-file-pdf"),
        "official_notification_pdf":("Official Notification","btn-blue",   "fa-file-pdf"),
        "official_website":        ("Official Website",      "btn-grey",   "fa-globe"),
        "result":                  ("View Result",           "btn-purple", "fa-trophy"),
        "admit_card":              ("Admit Card",            "btn-orange", "fa-id-card"),
        "answer_key":              ("Answer Key",            "btn-yellow", "fa-key"),
        "syllabus":                ("Download Syllabus",     "btn-teal",   "fa-book"),
        "click_here":              ("Click Here",            "btn-grey",   "fa-arrow-up-right-from-square"),
    }
    if isinstance(links, dict):
        for k, v in links.items():
            if k == "click_here" and isinstance(v, list):
                for url in v:
                    if url and isinstance(url, str) and url.startswith("http"):
                        lbl, cls, ico = link_map["click_here"]
                        links_html += f'<a href="{esc(url)}" class="link-btn {cls}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ico}"></i> {lbl}</a>\n'
            elif isinstance(v, str) and v.startswith("http"):
                lbl, cls, ico = link_map.get(k, ("Link", "btn-grey", "fa-link"))
                links_html += f'<a href="{esc(v)}" class="link-btn {cls}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ico}"></i> {lbl}</a>\n'
    if not links_html:
        links_html = "<p>Official notification ke liye upar di gayi information dekhein.</p>"

    # SEO paragraphs (Task 5)
    seo_p1 = f"{org} ne {title} ke liye official notification jari kiya hai. Is recruitment mein kul {posts} posts ke liye eligible candidates se applications mangi gayi hain. Jo bhi candidates is post ke liye eligible hain, woh last date {last_date} se pehle apply kar sakte hain."
    seo_p2 = f"Application {mode} mode mein ki ja sakti hai. Selection process mein written test aur/ya interview shamil ho sakta hai. Salary aur age limit ki jankari ke liye upar di gayi table dekhein. Sahi jankari ke liye official notification zaroor padhein."
    seo_p3 = f"{title} ek achi opportunity hai un candidates ke liye jo government jobs dhundh rahe hain. Top Sarkari Jobs par aapko latest sarkari naukri updates milte rehte hain. Kisi bhi query ke liye official website visit karein ya official notification download karein."

    # Extract primary apply URL for sidebar button
    links_raw = job.get("important_links", {}) or {}
    apply_url = ""
    for k in ("apply_online", "apply_online_link", "official_website"):
        v = links_raw.get(k)
        if isinstance(v, str) and v.startswith("http"):
            apply_url = v
            break
    if not apply_url:
        v = links_raw.get("click_here")
        if isinstance(v, list) and v:
            apply_url = v[0]
        elif isinstance(v, str) and v.startswith("http"):
            apply_url = v

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{esc(seo_title)}</title>
  <meta name="description" content="{esc(meta_desc)}"/>
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"/>
  <link rel="canonical" href="{canonical}"/>
  <link rel="alternate" hreflang="en" href="{canonical}"/>
  <link rel="alternate" hreflang="en-IN" href="{canonical}"/>
  <link rel="alternate" hreflang="x-default" href="{canonical}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:site_name" content="Top Sarkari Jobs"/>
  <meta property="og:title" content="{esc(seo_title)}"/>
  <meta property="og:description" content="{esc(meta_desc)}"/>
  <meta property="og:url" content="{canonical}"/>
  <meta property="og:image" content="{BASE_URL}/image.png"/>
  <meta property="og:image:width" content="512"/>
  <meta property="og:image:height" content="512"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{esc(seo_title)}"/>
  <meta name="twitter:description" content="{esc(meta_desc)}"/>
  <script type="application/ld+json">{job_schema}</script>
  <script type="application/ld+json">{breadcrumb_schema}</script>
  <script type="application/ld+json">{faq_schema}</script>
  <script type="application/ld+json">{article_schema}</script>
  <script>
    window.__TSJ_SLUG = "{slug}";
    window.__TSJ_CANONICAL = "{canonical}";
    window.__TSJ_PSR_DISABLED = true;
    window.__TSJ_STATIC_PAGE = true;
    window.__TSJ_RENDERER_DISABLED = true;
  </script>
  <link rel="icon" type="image/x-icon" href="/image.ico"/>
  <link rel="stylesheet" href="/styles.css"/>
  <link rel="stylesheet" href="/fonts/fa/all.min.css"/>
  <link rel="manifest" href="/manifest.json"/>
  <meta name="theme-color" content="#0d2257"/>
  <script src="/analytics.js" defer></script>
  <!-- NO universal-renderer.js | NO job-renderer-patch.js | NO preferred-source-renderer.js -->
  <style>
    /* ══ Modern 3-Column Layout ══ */
    .jp-wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px 12px 40px; }}
    .jp-three-col {{ display: grid; grid-template-columns: 1fr 300px; gap: 20px; align-items: start; }}
    @media (max-width: 900px) {{ .jp-three-col {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 480px) {{ .jp-wrap {{ padding: 12px 8px max(32px, env(safe-area-inset-bottom, 32px)); }} }}
    .jp-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; border-top: 1px solid #e2e8f0; margin-top: 14px; }}
    @media (max-width: 640px) {{ .jp-stats {{ grid-template-columns: repeat(2, 1fr); }} }}
    .jp-stat {{ text-align: center; padding: 12px 8px; border-right: 1px solid #e2e8f0; }}
    .jp-stat:last-child {{ border-right: none; }}
    .jp-stat-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 4px; }}
    .jp-stat-value {{ font-size: 14px; font-weight: 700; color: #0f172a; }}
    .jp-stat-value.green {{ color: #16a34a; }}
    .jp-stat-value.blue {{ color: #2563eb; }}
    .jp-sidebar {{ display: flex; flex-direction: column; gap: 14px; }}
    .jp-sidebar-card {{ background: #fff; border-radius: 12px; border: 1.5px solid #e2e8f0; overflow: hidden; }}
    .jp-sidebar-card-head {{ background: linear-gradient(135deg,#dc2626,#b91c1c); color: #fff; padding: 10px 14px; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 7px; }}
    .jp-sidebar-card-body {{ padding: 12px 14px; }}
    .jp-hl-list {{ list-style: none; margin: 0; padding: 0; }}
    .jp-hl-list li {{ display: flex; align-items: flex-start; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 12.5px; color: #374151; }}
    .jp-hl-list li:last-child {{ border-bottom: none; }}
    .jp-hl-list li i {{ color: #16a34a; margin-top: 2px; flex-shrink: 0; font-size: 12px; }}
    .jp-share-card-head {{ background: linear-gradient(135deg,#7c3aed,#6d28d9); color: #fff; padding: 10px 14px; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 7px; }}
    .jp-share-btns {{ display: flex; flex-direction: column; gap: 8px; padding: 12px 14px; }}
    .jp-share-btn {{ display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 7px; font-size: 13px; font-weight: 600; text-decoration: none; color: #fff; cursor: pointer; border: none; transition: opacity .2s; }}
    .jp-share-btn:hover {{ opacity: .88; }}
    .jp-share-btn.wa {{ background: #25D366; }}
    .jp-share-btn.tg {{ background: #229ED9; }}
    .jp-share-btn.fb {{ background: #1877F2; }}
    .jp-share-btn.cp {{ background: #475569; }}
  </style>
</head>
<body>
<div id="header-placeholder"></div>
<main id="main-content">
  <div class="jp-wrap">
    <nav class="breadcrumb" aria-label="breadcrumb" style="margin-bottom:16px">
      <a href="/">Home</a> &rsaquo; <a href="/section/latest-jobs/">Latest Jobs</a> &rsaquo; <span>{esc(title)}</span>
    </nav>
    <div class="jp-three-col">
      <!-- LEFT: main content -->
      <div class="jp-main-col">
        <article itemscope itemtype="https://schema.org/JobPosting">
          <header class="job-hero-card">
            <h1 itemprop="title">{esc(title)}</h1>
            <p class="job-org" itemprop="hiringOrganization" itemscope itemtype="https://schema.org/Organization">
              <span itemprop="name">{esc(org)}</span>
            </p>
            <div class="jp-stats">
              <div class="jp-stat"><div class="jp-stat-label">Organisation</div><div class="jp-stat-value">{esc(org) if org else "—"}</div></div>
              <div class="jp-stat"><div class="jp-stat-label">Total Posts</div><div class="jp-stat-value blue">{esc(posts) if posts else "Various"}</div></div>
              <div class="jp-stat"><div class="jp-stat-label">Last Date</div><div class="jp-stat-value" style="color:#dc2626">{esc(last_date) if last_date else "See Notification"}</div></div>
              <div class="jp-stat"><div class="jp-stat-label">Apply Mode</div><div class="jp-stat-value green">{esc(mode) if mode else "Online"}</div></div>
            </div>
          </header>

          {"<section class='job-card' id='short-info'><div class='job-card-head' style='background:linear-gradient(135deg,#0369a1,#0284c7)'><i class='fa-solid fa-circle-info'></i><h2>Short Information</h2></div><div class='job-card-body'><p itemprop='description'>" + esc(short_info) + "</p></div></section>" if short_info else ""}

          {sections_html}

          <section class="job-card" id="important-links">
            <div class="job-card-head" style="background:linear-gradient(135deg,#1e40af,#1e3a8a)">
              <i class="fa-solid fa-link"></i><h2>Important Links</h2>
            </div>
            <div class="job-card-body"><div class="links-grid">{links_html}</div></div>
          </section>

          <section class="job-card" id="faq">
            <div class="job-card-head" style="background:linear-gradient(135deg,#9333ea,#7e22ce)">
              <i class="fa-solid fa-circle-question"></i><h2>Frequently Asked Questions</h2>
            </div>
            <div class="job-card-body"><div class="faq-list">{faq_qa_html}</div></div>
          </section>

          <section class="job-card" id="about-recruitment">
            <div class="job-card-head" style="background:linear-gradient(135deg,#0f766e,#0d9488)">
              <i class="fa-solid fa-circle-info"></i><h2>About {esc(org)} Recruitment {year}</h2>
            </div>
            <div class="job-card-body">
              <p>{esc(seo_p1)}</p>
              <p>{esc(seo_p2)}</p>
              <p>{esc(seo_p3)}</p>
            </div>
          </section>
        </article>
      </div>

      <!-- RIGHT: sidebar -->
      <aside class="jp-sidebar">
        <div class="jp-sidebar-card">
          <div class="jp-sidebar-card-head"><i class="fa-solid fa-star"></i> Quick Highlights</div>
          <div class="jp-sidebar-card-body">
            <ul class="jp-hl-list">
              <li><i class="fa-solid fa-circle-check"></i> <div><strong>Organisation:</strong> {esc(org) if org else "See Notification"}</div></li>
              <li><i class="fa-solid fa-circle-check"></i> <div><strong>Total Posts:</strong> {esc(posts) if posts else "Various"}</div></li>
              <li><i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b"></i> <div><strong>Last Date:</strong> {esc(last_date) if last_date else "See Notification"}</div></li>
              <li><i class="fa-solid fa-circle-check"></i> <div><strong>Apply Mode:</strong> {esc(mode) if mode else "Online"}</div></li>
            </ul>
          </div>
        </div>
        <div class="jp-sidebar-card">
          <div class="jp-share-card-head"><i class="fa-solid fa-share-nodes"></i> Share This Job</div>
          <div class="jp-share-btns">
            <a class="jp-share-btn wa" href="https://wa.me/?text={esc(title)}%0A{canonical}" target="_blank" rel="noopener"><i class="fa-brands fa-whatsapp"></i> WhatsApp</a>
            <a class="jp-share-btn tg" href="https://t.me/share/url?url={canonical}&text={esc(title)}" target="_blank" rel="noopener"><i class="fa-brands fa-telegram"></i> Telegram</a>
            <a class="jp-share-btn fb" href="https://www.facebook.com/sharer/sharer.php?u={canonical}" target="_blank" rel="noopener"><i class="fa-brands fa-facebook-f"></i> Facebook</a>
            <button class="jp-share-btn cp" onclick="navigator.clipboard.writeText('{canonical}').then(function(){{var t=this;this.textContent='✅ Copied!';setTimeout(function(){{t.textContent='🔗 Copy Link'}},2000)}}.bind(this))"><i class="fa-solid fa-link"></i> Copy Link</button>
          </div>
        </div>
        {"<div class='jp-sidebar-card'><div class='jp-sidebar-card-head' style='background:linear-gradient(135deg,#0369a1,#0284c7)'><i class='fa-solid fa-calendar-days'></i> Important Dates</div><div class='jp-sidebar-card-body'><ul class='jp-hl-list'><li><i class='fa-solid fa-calendar-check' style='color:#0369a1'></i><div><strong>Last Date:</strong> " + esc(last_date) + "</div></li></ul></div></div>" if last_date else ""}
        {"<a href='" + esc(apply_url) + "' target='_blank' rel='noopener noreferrer' style='display:flex;align-items:center;justify-content:center;gap:8px;padding:14px;border-radius:10px;font-size:15px;font-weight:700;text-decoration:none;color:#fff;background:linear-gradient(135deg,#059669,#047857);'><i class='fa-solid fa-arrow-up-right-from-square'></i> Apply Online / Official Website</a>" if apply_url else ""}
      </aside>
    </div><!-- /jp-three-col -->
  </div><!-- /jp-wrap -->
</main>
<div id="footer-placeholder"></div>
<script src="/tsj-menu.js" defer></script>
<script src="/pwa-install.js?v=6.0" defer></script>
<script src="/tsj-push.js"></script>
</body>
</html>"""

# ── Main ──────────────────────────────────────────────────────────────
def main():
    print(f"📖 Reading {DATA_FILE}...")
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)

    print("🔄 Extracting all jobs from 4 sources...")
    all_jobs = extract_all_jobs(data)
    print(f"   Total extracted (raw): {len(all_jobs)}")

    print("🧹 Deduplicating...")
    clean_jobs = deduplicate(all_jobs)
    print(f"   After dedup: {len(clean_jobs)} unique jobs")

    # Save master clean file
    Path("data").mkdir(exist_ok=True)
    master_path = "data/master_clean_jobs.json"
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(clean_jobs, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {master_path} ({len(clean_jobs)} jobs)")

    # Generate HTML pages
    OUTPUT_DIR.mkdir(exist_ok=True)
    generated = skipped = errors = 0

    for job in clean_jobs:
        slug = job.get("slug", "")
        if not slug: continue

        out_dir = OUTPUT_DIR / slug
        out_file = out_dir / "index.html"

        if out_file.exists():
            skipped += 1
            continue

        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            html_content = generate_html(job)
            out_file.write_text(html_content, encoding="utf-8")
            generated += 1
            if generated % 200 == 0:
                print(f"   Generated {generated} new pages...")
        except Exception as e:
            print(f"   ❌ Error: {slug} — {e}")
            errors += 1

    print(f"\n✅ DONE!")
    print(f"   Generated new:  {generated}")
    print(f"   Skipped (exist):{skipped}")
    print(f"   Errors:         {errors}")
    print(f"   Total clean:    {len(clean_jobs)}")

if __name__ == "__main__":
    import os
    # Run from site root
    site_root = Path(__file__).parent.parent
    os.chdir(site_root)
    main()
