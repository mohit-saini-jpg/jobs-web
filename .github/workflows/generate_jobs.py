"""
generate_jobs.py — Saare 4 JSON sources se job pages generate karta hai
=========================================================================
Sources:
  1. Complete_Jobs_Full_Data.json  — main job database
  2. merged_sarkari_data.json      — sr_ prefix + non-sr jobs
  3. state-jobs-data.json          — state-wise jobs
  4. dailyupdates.json             — daily updates (Top 20 + Today Updates)

Output per job:
  - jobs/data/<slug>.json          — job data file
  - jobs/<slug>/index.html         — static HTML (Google directly indexes!)
  - jobs-index.json                — fast lookup index
"""

import json, re, os, html as html_mod
from datetime import date

SRC      = "Complete_Jobs_Full_Data.json"
MERGED   = "merged_sarkari_data.json"
STATE    = "state-jobs-data.json"
DAILY    = "dailyupdates.json"
DEST     = "jobs/data"
JOBS_DIR = "jobs"
INDEX    = "jobs-index.json"
BASE_URL = "https://www.topsarkarijobs.com"
TODAY    = date.today().isoformat()

VALID_CATS = {
    "Latest_Notifications","10TH_Pass","8TH_Pass","12TH_Pass",
    "Diploma","ITI","B_Tech_BE","B_Com","Any_Graduate",
    "Any_Post_Graduate","Railway_Jobs","Police_Defence",
    "Teaching_Faculty","Bank_Jobs","Medical_Hospital",
}

CAT_LABELS = {
    "Latest_Notifications":"Latest Jobs","10TH_Pass":"10th Pass Jobs",
    "8TH_Pass":"8th Pass Jobs","12TH_Pass":"12th Pass Jobs",
    "Diploma":"Diploma Jobs","ITI":"ITI Jobs","B_Tech_BE":"B.Tech / BE Jobs",
    "B_Com":"B.Com Jobs","Any_Graduate":"Graduation Jobs",
    "Any_Post_Graduate":"Post Graduation Jobs","Railway_Jobs":"Railway Jobs",
    "Police_Defence":"Defence Jobs","Teaching_Faculty":"Teaching Jobs",
    "Bank_Jobs":"Bank Jobs","Medical_Hospital":"Medical Jobs",
}

def slugify(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text[:120].strip('-') or 'job'

def clean_slug(raw_slug):
    """Remove sr_*- prefix and trailing hex hash from existing slugs.
    sr_latest_jobs-rpsc-school-lecturer-106b24  →  rpsc-school-lecturer
    sr_admit_card-bpsc-admit-card-2026-9934ae   →  bpsc-admit-card-2026
    """
    s = str(raw_slug or '').strip()
    # Remove sr_category- prefix
    s = re.sub(r'^sr_[a-z_]+-', '', s)
    # Remove trailing 6 or 8 char hex hash
    s = re.sub(r'-[0-9a-f]{6,8}$', '', s)
    # Clean double dashes
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:120] or slugify(str(raw_slug))

def e(s):
    return html_mod.escape(str(s or ''), quote=True)

def normalise_date(raw):
    if not raw: return None
    raw = str(raw).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw): return raw
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
              "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    m1 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', raw)
    if m1: return f"{m1.group(3)}-{int(m1.group(2)):02d}-{int(m1.group(1)):02d}"
    m2 = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', raw)
    if m2:
        mo = months.get(m2.group(2)[:3].lower())
        if mo: return f"{m2.group(3)}-{mo:02d}-{int(m2.group(1)):02d}"
    return None

def build_static_html(slug, title, bd, dates, qual, salary, cat, source_url):
    canon_url  = f"{BASE_URL}/jobs/{slug}/"
    cat_label  = CAT_LABELS.get(cat, "Government Jobs")
    org        = e(bd.get("post_name") or bd.get("job_title") or "Government of India")
    vacancies  = e(bd.get("total_vacancies") or bd.get("total_vacancy") or "")
    last_date_r= dates.get("last_date_to_apply") or dates.get("last_date") or ""
    last_date  = e(last_date_r)
    apply_mode = e(bd.get("application_mode") or "Online")
    location   = e(bd.get("job_location") or "India")
    short_info = e(bd.get("short_information") or "")
    posted_date= normalise_date(bd.get("last_updated") or dates.get("date of notification") or "") or TODAY

    qual_str = ""
    if isinstance(qual, dict):
        qual_str = e(qual.get("essential_qualification") or qual.get("qualification") or "")
    elif isinstance(qual, str):
        qual_str = e(qual)

    sal_str = ""
    if isinstance(salary, dict):
        sal_str = e(salary.get("pay_scale") or salary.get("salary") or "")
    elif isinstance(salary, str):
        sal_str = e(salary)

    # ── FIX C-5: Meta description ≤ 155 chars (was 200-304 chars) ──
    # Template: [Org] [Year]: [X] vacancies, last date [D]. [Qual]. Apply online – Top Sarkari Jobs.
    _vac_part  = f"{vacancies} vacancies, " if vacancies else ""
    _ld_part   = f"last date {last_date}. " if last_date else ""
    _sal_part  = f"Salary: {sal_str[:40]}. " if sal_str else ""
    _qual_part = f"{qual_str[:50]} eligible. " if qual_str else ""
    meta_desc  = f"{e(title)}: {_vac_part}{_ld_part}{_sal_part}{_qual_part}Apply online."
    # Trim to 155 chars cleanly at word boundary
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152].rsplit(' ', 1)[0].rstrip('.,–') + "…"

    # ── FIX C-6: Page title ≤ 60 chars ──
    # Template: [Org short] [Year] – [X Posts] | Top Sarkari Jobs
    title_seo = title  # full title for schema/h1
    if len(title) + len(" | Top Sarkari Jobs") > 60:
        # Try to extract year from title
        _yr = re.search(r'20\d\d', title)
        _yr = _yr.group() if _yr else ""
        _vac_n = re.search(r'\d+', str(bd.get("total_vacancies") or ""))
        _vac_tag = f" – {_vac_n.group()} Posts" if _vac_n else ""
        # Short title from first meaningful part (before ' –', ' -', ' Notification', ' Recruitment')
        _short = re.split(r'\s+(?:–|-|Notification|Recruitment)\s+', title)[0].strip()
        _short = _short[:30].rstrip() if len(_short) > 30 else _short
        _title_tag = f"{_short}{' ' + _yr if _yr and _yr not in _short else ''}{_vac_tag}"
        if len(_title_tag) + len(" | Top Sarkari Jobs") <= 60:
            title_tag = _title_tag
        else:
            title_tag = title[:40].rstrip()
    else:
        title_tag = title

    # ── FIX C-4: JobPosting schema with all required fields ──
    org_name = bd.get("post_name") or "Government of India"
    job_schema = {
        "@context":"https://schema.org","@type":"JobPosting",
        "title":title_seo,
        "description": bd.get("short_information") or meta_desc,
        "datePosted":posted_date,"employmentType":"FULL_TIME","url":canon_url,
        "identifier":{"@type":"PropertyValue","name":org_name,"value":slug},
        "applicantLocationRequirements":{"@type":"Country","name":"India"},
        "hiringOrganization":{"@type":"Organization","name":org_name,
            "sameAs":"https://www.india.gov.in"},
        "jobLocation":{"@type":"Place","address":{"@type":"PostalAddress",
            "addressCountry":"IN","addressRegion":"India",
            "addressLocality": bd.get("job_location") or "India"}},
        "author":{"@type":"Organization","name":"TopSarkariJobs Editorial Team",
            "url":"https://www.topsarkarijobs.com/about.html"}
    }
    if last_date_r:
        iso = normalise_date(last_date_r)
        if iso: job_schema["validThrough"] = iso
    if vacancies:
        vac_num = re.search(r'\d+', str(vacancies))
        if vac_num: job_schema["totalJobOpenings"] = int(vac_num.group())
    if qual_str:
        job_schema["educationRequirements"] = {"@type":"EducationalOccupationalCredential","credentialCategory":qual_str[:200]}
    # baseSalary — use sal_str if available, else provide INR placeholder range
    if sal_str:
        _sal_match = re.search(r'(\d[\d,]+)', sal_str.replace(',', ''))
        if _sal_match:
            _sal_val = int(re.sub(r'\D','', _sal_match.group()))
            job_schema["baseSalary"] = {"@type":"MonetaryAmount","currency":"INR",
                "value":{"@type":"QuantitativeValue","value":_sal_val,"unitText":"MONTH"}}
    else:
        job_schema["baseSalary"] = {"@type":"MonetaryAmount","currency":"INR",
            "value":{"@type":"QuantitativeValue","minValue":15000,"maxValue":80000,"unitText":"MONTH"}}

    # ── FIX H-1: FAQ schema on every job page ──
    _last_date_faq = last_date or "official notification dekhein"
    _qual_faq = qual_str[:100] if qual_str else "Official notification dekhein"
    _sal_faq  = sal_str[:80] if sal_str else "As per government norms"
    faq_schema = {
        "@context":"https://schema.org","@type":"FAQPage",
        "mainEntity":[
            {"@type":"Question","name":f"{title_seo} last date kya hai?",
             "acceptedAnswer":{"@type":"Answer","text":f"Last date: {_last_date_faq}."}},
            {"@type":"Question","name":f"{title_seo} ke liye qualification kya chahiye?",
             "acceptedAnswer":{"@type":"Answer","text":f"Qualification: {_qual_faq}."}},
            {"@type":"Question","name":f"{title_seo} mein salary kitni hai?",
             "acceptedAnswer":{"@type":"Answer","text":f"Salary: {_sal_faq}."}}
        ]
    }

    bc_schema = {
        "@context":"https://schema.org","@type":"BreadcrumbList",
        "itemListElement":[
            {"@type":"ListItem","position":1,"name":"Home","item":f"{BASE_URL}/"},
            {"@type":"ListItem","position":2,"name":"Latest Jobs","item":f"{BASE_URL}/section/latest-jobs/"},
            {"@type":"ListItem","position":3,"name":title_seo,"item":canon_url}
        ]
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{e(title_tag)} | Top Sarkari Jobs</title>
  <meta name="description" content="{e(meta_desc)}"/>
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"/>
  <link rel="canonical" href="{canon_url}"/>
  <link rel="alternate" hreflang="en" href="{canon_url}"/>
  <link rel="alternate" hreflang="en-IN" href="{canon_url}"/>
  <link rel="alternate" hreflang="x-default" href="{canon_url}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:site_name" content="Top Sarkari Jobs"/>
  <meta property="og:title" content="{e(title_tag)} | Top Sarkari Jobs"/>
  <meta property="og:description" content="{e(meta_desc)}"/>
  <meta property="og:url" content="{canon_url}"/>
  <meta property="og:image" content="{BASE_URL}/image.png"/>
  <meta property="og:image:width" content="512"/>
  <meta property="og:image:height" content="512"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{e(title_tag)} | Top Sarkari Jobs"/>
  <meta name="twitter:description" content="{e(meta_desc)}"/>
  <script type="application/ld+json">{json.dumps(job_schema, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(bc_schema, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(faq_schema, ensure_ascii=False)}</script>
  <script>
    window.__TSJ_SLUG = {json.dumps(slug)};
    window.__TSJ_CANONICAL = {json.dumps(canon_url)};
    try {{
      if (window.location.pathname !== '/jobs/{slug}/') {{
        window.history.replaceState(null, '', '/jobs/{slug}/');
      }}
    }} catch(_) {{}}
  </script>
  <link rel="icon" type="image/x-icon" href="/image.ico"/>
  <link rel="stylesheet" href="/styles.css"/>
  <link rel="stylesheet" href="/fonts/fa/all.min.css"/>
  <link rel="manifest" href="/manifest.json"/>
  <meta name="theme-color" content="#0d2257"/>
  <script src="/analytics.js" defer></script>
</head>
<body>
  <noscript>
    <div style="font-family:sans-serif;max-width:800px;margin:40px auto;padding:20px">
      <nav><a href="/">← Top Sarkari Jobs</a> &rsaquo; <a href="/section/latest-jobs/">Latest Jobs</a></nav>
      <article itemscope itemtype="https://schema.org/JobPosting">
        <h1 itemprop="title">{e(title_seo)}</h1>
        <table style="border-collapse:collapse;width:100%">
          {"<tr><th style='text-align:left;padding:6px 12px;border:1px solid #ddd'>Organisation</th><td style='padding:6px 12px;border:1px solid #ddd' itemprop='hiringOrganization'>" + org + "</td></tr>" if org else ""}
          {"<tr><th style='text-align:left;padding:6px 12px;border:1px solid #ddd'>Total Posts</th><td style='padding:6px 12px;border:1px solid #ddd' itemprop='totalJobOpenings'>" + vacancies + "</td></tr>" if vacancies else ""}
          {"<tr><th style='text-align:left;padding:6px 12px;border:1px solid #ddd'>Last Date</th><td style='padding:6px 12px;border:1px solid #ddd' itemprop='validThrough'>" + last_date + "</td></tr>" if last_date else ""}
          <tr><th style='text-align:left;padding:6px 12px;border:1px solid #ddd'>Apply Mode</th><td style='padding:6px 12px;border:1px solid #ddd'>{apply_mode}</td></tr>
          {"<tr><th style='text-align:left;padding:6px 12px;border:1px solid #ddd'>Qualification</th><td style='padding:6px 12px;border:1px solid #ddd' itemprop='educationRequirements'>" + qual_str + "</td></tr>" if qual_str else ""}
          {"<tr><th style='text-align:left;padding:6px 12px;border:1px solid #ddd'>Salary</th><td style='padding:6px 12px;border:1px solid #ddd' itemprop='baseSalary'>" + sal_str + "</td></tr>" if sal_str else ""}
          <tr><th style='text-align:left;padding:6px 12px;border:1px solid #ddd'>Location</th><td style='padding:6px 12px;border:1px solid #ddd' itemprop='jobLocation'>{location}</td></tr>
        </table>
        {"<p itemprop='description'>" + short_info[:500] + "</p>" if short_info else ""}
        {"<p><a href='" + e(source_url) + "' rel='nofollow noopener' target='_blank'>Apply Online (Official Link)</a></p>" if source_url else ""}
        <section>
          <h2>Frequently Asked Questions</h2>
          <h3>{e(title_seo)} last date kya hai?</h3>
          <p>Last date: {_last_date_faq}.</p>
          <h3>{e(title_seo)} ke liye qualification kya chahiye?</h3>
          <p>{_qual_faq}</p>
          <h3>{e(title_seo)} mein salary kitni hai?</h3>
          <p>{_sal_faq}</p>
        </section>
      </article>
      <p><a href="/">← Back to Top Sarkari Jobs</a></p>
    </div>
  </noscript>
  <script>
  (function() {{
    try {{ sessionStorage.setItem('__tsj_slug', window.__TSJ_SLUG); }} catch(_) {{}}
    window.location.replace('/job.html?slug=' + encodeURIComponent(window.__TSJ_SLUG));
  }})();
  </script>
</body>
</html>"""

# ═══════════════════════════════════════
# MAIN PROCESSING
# ═══════════════════════════════════════
os.makedirs(DEST, exist_ok=True)

existing_json = set(os.listdir(DEST))
existing_dirs = set(d for d in os.listdir(JOBS_DIR)
                    if os.path.isdir(os.path.join(JOBS_DIR, d)) and d != 'data')

index      = {}
new_files  = set()
new_dirs   = set()
written    = 0
skipped    = 0
seen_slugs = {}

# ── SOURCE 1: Complete_Jobs_Full_Data.json ──
if os.path.exists(SRC):
    print(f"Loading {SRC}...")
    with open(SRC, encoding='utf-8') as f:
        data = json.load(f)

    for cat, jobs in data.items():
        if not isinstance(jobs, list): continue
        if cat not in VALID_CATS:
            print(f"  SKIP unknown category: {cat}")
            continue
        for job in jobs:
            bd    = job.get("basic_details", {}) or {}
            dates = job.get("important_dates", {}) or {}
            qual  = job.get("qualification") or {}
            sal   = job.get("salary_details") or {}
            title = (bd.get("job_title") or "").strip()
            url   = (job.get("source_url") or "").strip()
            if not title: skipped += 1; continue

            slug = slugify(title)
            fname = f"{slug}.json"
            if slug in seen_slugs and seen_slugs[slug] != cat:
                slug = f"{slug}-{cat.lower().replace('_','-')}"
                fname = f"{slug}.json"
            seen_slugs[slug] = cat
            job["category"] = cat

            with open(os.path.join(DEST, fname), 'w', encoding='utf-8') as f:
                json.dump(job, f, ensure_ascii=False, separators=(',',':'))
            new_files.add(fname)

            slug_dir = os.path.join(JOBS_DIR, slug)
            os.makedirs(slug_dir, exist_ok=True)
            with open(os.path.join(slug_dir, "index.html"), 'w', encoding='utf-8') as f:
                f.write(build_static_html(slug, title, bd, dates, qual, sal, cat, url))
            new_dirs.add(slug)

            last_date = (dates.get("last_date_to_apply") or "").strip()
            index[slug] = {"cat":cat,"title":title[:120],"last_date":last_date[:30],"url":url}
            written += 1

    print(f"  Complete_Jobs_Full_Data: {written} jobs")

# ── SOURCE 2: merged_sarkari_data.json ──
if os.path.exists(MERGED):
    print(f"\nLoading {MERGED}...")
    with open(MERGED, encoding='utf-8') as f:
        mdata = json.load(f)
    merged_jobs = mdata.get("jobs", []) if isinstance(mdata, dict) else mdata
    mc = 0
    for job in merged_jobs:
        existing_slug = (job.get("slug") or "").strip()
        title = (job.get("title") or "").strip()
        if not title: continue

        if existing_slug:
            slug = clean_slug(existing_slug)
        else:
            slug = slugify(title)
        if not slug or slug in new_dirs: continue

        imp_dates = job.get("important_dates") or {}
        if isinstance(imp_dates, str): imp_dates = {}

        bd = {
            "job_title":        title,
            "post_name":        job.get("post_name") or job.get("organization") or "",
            "total_vacancies":  str(job.get("total_post") or job.get("total_vacancy") or ""),
            "application_mode": job.get("apply_mode") or "Online",
            "job_location":     job.get("job_location") or "India",
            "short_information":job.get("short_information") or job.get("jobs_info") or "",
            "last_updated":     job.get("post_date") or job.get("listing_date") or imp_dates.get("application_begin") or "",
        }
        dates = {
            "last_date_to_apply": job.get("last_date") or imp_dates.get("last_date") or "",
            "date of notification": job.get("post_date") or job.get("listing_date") or "",
        }
        # Source URL from useful_links
        useful_links = job.get("useful_links") or []
        source_url = job.get("apply_online_link") or job.get("official_website_link") or ""
        if not source_url and isinstance(useful_links, list):
            for lnk in useful_links:
                if isinstance(lnk, dict):
                    href = lnk.get("links") or lnk.get("url") or ""
                    if isinstance(href, list): href = href[0] if href else ""
                    href = str(href).strip()
                    if href.startswith("http"): source_url = href; break

        cat = "Latest_Notifications"
        fname = slug + ".json"
        job["slug"] = slug; job["category"] = cat
        with open(os.path.join(DEST, fname), 'w', encoding='utf-8') as f:
            json.dump(job, f, ensure_ascii=False, separators=(',',':'))
        new_files.add(fname)

        slug_dir = os.path.join(JOBS_DIR, slug)
        os.makedirs(slug_dir, exist_ok=True)
        with open(os.path.join(slug_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(build_static_html(slug, title, bd, dates, {}, {}, cat, source_url))
        new_dirs.add(slug)

        last_date = dates.get("last_date_to_apply","").strip()
        index[slug] = {"cat":cat,"title":title[:120],"last_date":last_date[:30],"url":source_url}
        written += 1; mc += 1
    print(f"  merged_sarkari_data: {mc} jobs")

# ── SOURCE 3: state-jobs-data.json ──
if os.path.exists(STATE):
    print(f"\nLoading {STATE}...")
    with open(STATE, encoding='utf-8') as f:
        sdata = json.load(f)
    sc = 0
    for sec in sdata.get("sections", []):
        state_name = sec.get("state") or sec.get("title") or "India"
        for item in sec.get("items", []):
            name = (item.get("name") or item.get("title") or "").strip()
            if not name: continue
            slug = clean_slug(item.get("slug") or '') or slugify(name)
            if not slug or slug in new_dirs: continue

            detail = item.get("detail") or {}
            if isinstance(detail, str):
                try: detail = json.loads(detail)
                except: detail = {}

            bd_raw = detail.get("basic_details", {}) if detail else {}
            dates_raw = detail.get("important_dates", {}) if detail else {}
            if isinstance(bd_raw, str): bd_raw = {}
            if isinstance(dates_raw, str): dates_raw = {}

            bd = {
                "job_title":        name,
                "post_name":        bd_raw.get("post_name") or name,
                "total_vacancies":  str(bd_raw.get("total_vacancies") or ""),
                "application_mode": bd_raw.get("application_mode") or "Online",
                "job_location":     f"{state_name}, India",
                "short_information":bd_raw.get("short_information") or "",
                "last_updated":     item.get("postDate") or item.get("date") or "",
            }
            dates = {
                "last_date_to_apply": item.get("lastDate") or dates_raw.get("last_date_to_apply") or "",
                "date of notification": item.get("postDate") or "",
            }
            source_url = item.get("url") or ""
            cat = "Latest_Notifications"
            fname = slug + ".json"
            job_rec = {"title":name,"slug":slug,"category":cat,
                       "basic_details":bd,"important_dates":dates,"source_url":source_url,"state":state_name}
            if detail: job_rec.update(detail)
            with open(os.path.join(DEST, fname), 'w', encoding='utf-8') as f:
                json.dump(job_rec, f, ensure_ascii=False, separators=(',',':'))
            new_files.add(fname)

            slug_dir = os.path.join(JOBS_DIR, slug)
            os.makedirs(slug_dir, exist_ok=True)
            qual_raw = detail.get("qualification", {}) if detail else {}
            sal_raw  = detail.get("salary_details", {}) if detail else {}
            with open(os.path.join(slug_dir, "index.html"), 'w', encoding='utf-8') as f:
                f.write(build_static_html(slug, name, bd, dates, qual_raw, sal_raw, cat, source_url))
            new_dirs.add(slug)

            last_date = dates.get("last_date_to_apply","").strip()
            index[slug] = {"cat":cat,"title":name[:120],"last_date":last_date[:30],"url":source_url}
            written += 1; sc += 1
    print(f"  state-jobs-data: {sc} jobs")

# ── SOURCE 4: dailyupdates.json (Top 20 Jobs + Today Updates only) ──
DAILY_JOB_SECTIONS = {"Top 20 Jobs", "Today Updates"}
if os.path.exists(DAILY):
    print(f"\nLoading {DAILY}...")
    with open(DAILY, encoding='utf-8') as f:
        ddata = json.load(f)
    dc = 0
    secs = ddata.get("sections", []) if isinstance(ddata, dict) else []
    for sec in secs:
        if sec.get("title") not in DAILY_JOB_SECTIONS: continue
        for item in sec.get("items", []):
            name = (item.get("name") or item.get("title") or "").strip()
            ext_url = (item.get("url") or item.get("link") or "").strip()
            if not name: continue
            slug = slugify(name)
            if not slug or slug in new_dirs: continue

            bd = {"job_title":name,"post_name":name,"total_vacancies":"",
                  "application_mode":"Online","job_location":"India",
                  "short_information":"","last_updated":item.get("date") or ""}
            dates = {"last_date_to_apply": item.get("lastDate") or item.get("date") or ""}
            cat = "Latest_Notifications"
            fname = slug + ".json"
            with open(os.path.join(DEST, fname), 'w', encoding='utf-8') as f:
                json.dump({"title":name,"slug":slug,"category":cat,
                           "basic_details":bd,"important_dates":dates,
                           "source_url":ext_url}, f, ensure_ascii=False, separators=(',',':'))
            new_files.add(fname)

            slug_dir = os.path.join(JOBS_DIR, slug)
            os.makedirs(slug_dir, exist_ok=True)
            with open(os.path.join(slug_dir, "index.html"), 'w', encoding='utf-8') as f:
                f.write(build_static_html(slug, name, bd, dates, {}, {}, cat, ext_url))
            new_dirs.add(slug)

            index[slug] = {"cat":cat,"title":name[:120],"last_date":"","url":ext_url}
            written += 1; dc += 1
    print(f"  dailyupdates: {dc} jobs")

# ── Cleanup stale files ──
stale_json = existing_json - new_files
for f in stale_json:
    try: os.remove(os.path.join(DEST, f))
    except: pass

import shutil
stale_dirs = existing_dirs - new_dirs
for d in stale_dirs:
    try: shutil.rmtree(os.path.join(JOBS_DIR, d))
    except: pass

# ── Write jobs-index.json ──
with open(INDEX, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, separators=(',',':'))


# ── Regenerate sections-index.json (used by homepage cards) ──
print("\nRegenerating sections-index.json...")
sections_index = {}
SINDEX_CATS = [
    'Latest_Notifications','10TH_Pass','8TH_Pass','12TH_Pass',
    'Diploma','ITI','B_Tech_BE','B_Com','Any_Graduate','Any_Post_Graduate',
    'Railway_Jobs','Police_Defence','Teaching_Faculty','Bank_Jobs','Medical_Hospital',
    'Last_Date_Reminder'
]
if os.path.exists(SRC):
    with open(SRC, encoding='utf-8') as f:
        full_data = json.load(f)
    for cat in SINDEX_CATS:
        jobs_list = full_data.get(cat, [])
        cat_items = []
        for job in jobs_list:
            bd_s = job.get('basic_details', {}) or {}
            dates_s = job.get('important_dates', {}) or {}
            title_s = (bd_s.get('job_title') or '').strip()
            if not title_s: continue
            slug_s = slugify(title_s)
            last_dt = (dates_s.get('last_date_to_apply') or dates_s.get('closing_date') or '')
            cat_items.append({'slug': slug_s, 'name': title_s, 'date': normalise_date(last_dt) or ''})
        if cat_items:
            sections_index[cat] = cat_items
    with open('sections-index.json', 'w', encoding='utf-8') as f:
        json.dump(sections_index, f, ensure_ascii=False, separators=(',',':'))
    print(f"  sections-index.json: {sum(len(v) for v in sections_index.values())} jobs across {len(sections_index)} categories")

print(f"\n✅ DONE!")
print(f"  Total jobs written : {written}")
print(f"  JSON files deleted : {len(stale_json)}")
print(f"  HTML dirs deleted  : {len(stale_dirs)}")
print(f"  Index entries      : {len(index)}")

# ── Rebuild section data JSON files from merged_sarkari_data.json ──────────────
# ══════════════════════════════════════════════════════════════════
# STATE JOBS — Static pages: /state-name/job-slug/index.html
# URL pattern: /haryana/yamuna-nagar-sessions-judge-peon-10-posts/
# ══════════════════════════════════════════════════════════════════
STATE_WISE = "State_Wise_Jobs.json"
if os.path.exists(STATE_WISE):
    print(f"\nGenerating state job static pages from {STATE_WISE}...")
    with open(STATE_WISE, encoding='utf-8') as f:
        sw = json.load(f)

    st_written = 0
    for sec in sw.get("sections", []):
        state_name = (sec.get("state") or sec.get("title") or "").strip()
        if not state_name: continue
        state_slug = slugify(state_name)   # e.g. "haryana"

        for item in sec.get("items", []):
            name = (item.get("name") or "").strip()
            if not name: continue

            job_slug = clean_slug(item.get("slug") or "") or slugify(name)
            if not job_slug: continue

            # URL: /haryana/yamuna-nagar-sessions-judge-peon-10-posts/
            page_dir = os.path.join(state_slug, job_slug)
            canon_url = f"{BASE_URL}/{state_slug}/{job_slug}/"

            detail = item.get("detail") or {}
            if isinstance(detail, str):
                try: detail = json.loads(detail)
                except: detail = {}

            bd  = detail.get("basic_details", {}) or {}
            id_ = detail.get("important_dates", {}) or {}
            last_date = (item.get("lastDate") or id_.get("last_date_to_apply") or "").strip()
            total_vac = str(bd.get("total_vacancies") or "").strip()
            short_info = str(bd.get("short_information") or "").strip()[:300]

            # Build meta
            meta_title = f"{name} | {state_name} Govt Jobs 2026 | TopSarkariJobs"
            meta_desc  = f"{name}. {state_name} government job. Last date: {last_date}. {short_info}"[:300]

            # Important links
            links_html = ""
            il = detail.get("important_links", {}) or {}
            apply_url = (il.get("apply_online") or il.get("official_website") or
                        item.get("url") or "").strip()
            notif_url = (il.get("notification_pdf") or il.get("download_pdf") or "").strip()
            if apply_url:
                links_html += f'<a href="{e(apply_url)}" target="_blank" rel="noopener" class="link-btn btn-green"><i class="fa-solid fa-paper-plane"></i> Apply Online</a>\n'
            if notif_url:
                links_html += f'<a href="{e(notif_url)}" target="_blank" rel="noopener" class="link-btn btn-blue"><i class="fa-solid fa-file-pdf"></i> Notification PDF</a>\n'
            if not links_html and apply_url:
                links_html = f'<a href="{e(apply_url)}" target="_blank" rel="noopener" class="link-btn btn-green"><i class="fa-solid fa-globe"></i> Official Website</a>\n'

            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{e(meta_title)}</title>
  <meta name="description" content="{e(meta_desc)}"/>
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"/>
  <link rel="canonical" href="{canon_url}"/>
  <link rel="icon" type="image/x-icon" href="/image.ico"/>
  <link rel="stylesheet" href="/styles.css"/>
  <link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/>
  <noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>
  <meta property="og:title" content="{e(meta_title)}"/>
  <meta property="og:description" content="{e(meta_desc)}"/>
  <meta property="og:url" content="{canon_url}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:image" content="https://www.topsarkarijobs.com/image.png"/>
  <script type="application/ld+json">{{
    "@context":"https://schema.org","@type":"JobPosting",
    "title":{json.dumps(name)},"description":{json.dumps(meta_desc)},
    "datePosted":"{TODAY}","employmentType":"FULL_TIME",
    "url":{json.dumps(canon_url)},
    "hiringOrganization":{{"@type":"Organization","name":{json.dumps(state_name + " Government")}}},
    "jobLocation":{{"@type":"Place","address":{{"@type":"PostalAddress","addressRegion":{json.dumps(state_name)},"addressCountry":"IN"}}}}
    {"," + chr(34) + "validThrough" + chr(34) + ":" + json.dumps(last_date) if last_date else ""}
  }}</script>
  <script type="application/ld+json">{{
    "@context":"https://schema.org","@type":"BreadcrumbList",
    "itemListElement":[
      {{"@type":"ListItem","position":1,"name":"Home","item":"https://www.topsarkarijobs.com/"}},
      {{"@type":"ListItem","position":2,"name":"State Jobs","item":"https://www.topsarkarijobs.com/state/"}},
      {{"@type":"ListItem","position":3,"name":{json.dumps(state_name + " Jobs")},"item":"https://www.topsarkarijobs.com/state/{state_slug}/"}},
      {{"@type":"ListItem","position":4,"name":{json.dumps(name)},"item":{json.dumps(canon_url)}}}
    ]
  }}</script>
  <style>
    .job-page{{max-width:900px;margin:24px auto;padding:0 14px 40px;}}
    .job-hero{{background:linear-gradient(125deg,#0c4a6e,#1a6b8a);border-radius:1.2rem;padding:1.8rem 2rem;color:#fff;margin-bottom:1.4rem;}}
    .job-hero h1{{font-size:1.4rem;font-weight:800;line-height:1.4;margin-bottom:.8rem;}}
    @media(max-width:600px){{.job-hero h1{{font-size:1.1rem;}}}}
    .pill{{background:rgba(255,255,255,.15);border-radius:60px;padding:.3rem .9rem;font-size:.78rem;display:inline-flex;align-items:center;gap:6px;margin:.2rem;}}
    .info-card{{background:#fff;border:1px solid #e9f0f5;border-radius:1.2rem;overflow:hidden;margin-bottom:1.2rem;box-shadow:0 4px 12px -4px rgba(0,0,0,.06);}}
    .info-card-head{{background:#1d4ed8;color:#fff;padding:.8rem 1.2rem;font-weight:700;font-size:.95rem;display:flex;align-items:center;gap:8px;}}
    .info-table{{width:100%;border-collapse:collapse;font-size:.85rem;}}
    .info-table tr{{border-bottom:1px solid #f1f5f9;}}
    .info-table tr:last-child{{border-bottom:none;}}
    .info-table th{{width:38%;background:#f8fafc;padding:.75rem 1rem;text-align:left;font-weight:600;color:#374151;vertical-align:top;}}
    .info-table td{{padding:.75rem 1rem;color:#1e293b;line-height:1.65;word-break:break-word;}}
    .links-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;padding:1rem;}}
    .link-btn{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;padding:12px 8px;border-radius:10px;text-decoration:none;font-weight:700;font-size:.75rem;text-align:center;transition:.18s;min-height:72px;}}
    .link-btn:hover{{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.12);}}
    .link-btn i{{font-size:1.1rem;}}
    .btn-green{{background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;}}
    .btn-blue{{background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;}}
    .breadcrumb{{font-size:.8rem;color:#64748b;margin-bottom:1rem;display:flex;flex-wrap:wrap;align-items:center;gap:5px;}}
    .breadcrumb a{{color:#1d4ed8;text-decoration:none;}}
  </style>
  <script src="/tsj-menu.js" defer></script>
</head>
<body>
<div id="header-placeholder"></div>
<main>
<div class="job-page">
  <nav class="breadcrumb">
    <a href="/">Home</a> › <a href="/state/">State Jobs</a> ›
    <a href="/state/{state_slug}/">{e(state_name)} Jobs</a> › {e(name[:50])}
  </nav>

  <div class="job-hero">
    <h1>{e(name)}</h1>
    <div>
      <span class="pill"><i class="fa-solid fa-map-marker-alt"></i> {e(state_name)}</span>
      {f'<span class="pill"><i class="fa-solid fa-users"></i> {e(total_vac)} Posts</span>' if total_vac else ""}
      {f'<span class="pill"><i class="fa-solid fa-hourglass-end"></i> Last Date: {e(last_date)}</span>' if last_date else ""}
    </div>
  </div>

  {f'<div class="info-card"><div class="info-card-head"><i class="fa-solid fa-circle-info"></i> About This Job</div><div style="padding:1rem 1.2rem;font-size:.85rem;line-height:1.75;color:#374151;">{e(short_info)}</div></div>' if short_info else ""}

  <div class="info-card">
    <div class="info-card-head"><i class="fa-solid fa-table-list"></i> Job Details</div>
    <table class="info-table">
      <tr><th>Post Name</th><td>{e(name)}</td></tr>
      <tr><th>State</th><td>{e(state_name)}</td></tr>
      {f"<tr><th>Total Posts</th><td>{e(total_vac)}</td></tr>" if total_vac else ""}
      {f"<tr><th>Last Date</th><td style='color:#dc2626;font-weight:700;'>{e(last_date)}</td></tr>" if last_date else ""}
      <tr><th>Apply Mode</th><td>{e(bd.get("application_mode") or "Online")}</td></tr>
    </table>
  </div>

  <div class="info-card">
    <div class="info-card-head"><i class="fa-solid fa-link"></i> Important Links</div>
    <div class="links-grid">{links_html or '<p style="padding:1rem;color:#64748b;font-size:.84rem;">Links not available. Check official website.</p>'}</div>
  </div>
</div>
</main>
<div id="footer-placeholder"></div>
<script>
  (function(){{
    var h=fetch("/header.html",{{cache:"no-store"}}).then(function(r){{return r.ok?r.text():null;}}).catch(function(){{return null;}});
    document.addEventListener("DOMContentLoaded",function(){{
      h.then(function(html){{if(html){{var el=document.getElementById("header-placeholder");if(el)el.innerHTML=html;if(typeof window.__TSJ_INIT_HEADER==="function")window.__TSJ_INIT_HEADER();}}}}); 
      h.then(function(html){{if(html){{var el=document.getElementById("footer-placeholder");if(el){{fetch("/footer.html").then(function(r){{return r.ok?r.text():null;}}).then(function(fh){{if(fh)el.innerHTML=fh;}});}}}}}});
    }});
  }})();
</script>
</body>
</html>"""

            os.makedirs(page_dir, exist_ok=True)
            with open(os.path.join(page_dir, "index.html"), 'w', encoding='utf-8') as f:
                f.write(html)
            st_written += 1

    print(f"  State pages written: {st_written}")
    print(f"✅ State job static pages generated.")
else:
    print(f"  SKIP: {STATE_WISE} not found")


# ══════════════════════════════════════════════════════════════════
# EDUCATION — Static pages: /education/state/job-slug/index.html
# URL pattern: /education/haryana/kurukshetra-university-results-2026/
# ══════════════════════════════════════════════════════════════════
EDU_WISE = "Qualification_Wise_Jobs.json"
if os.path.exists(EDU_WISE):
    print(f"\nGenerating education static pages from {EDU_WISE}...")
    with open(EDU_WISE, encoding='utf-8') as f:
        eq = json.load(f)

    edu_written = 0
    for sec in eq.get("sections", []):
        sec_id    = (sec.get("id") or sec.get("title") or "").strip()
        sec_title = (sec.get("title") or sec_id or "Education").strip()
        sec_slug  = slugify(sec_id or sec_title)

        for item in sec.get("items", []):
            name = (item.get("name") or item.get("examName") or "").strip()
            if not name: continue

            job_slug = clean_slug(item.get("slug") or "") or slugify(name)
            if not job_slug: continue

            # URL: /education/haryana/kurukshetra-university-results-2026/
            page_dir  = os.path.join("education", sec_slug, job_slug)
            canon_url = f"{BASE_URL}/education/{sec_slug}/{job_slug}/"

            org  = str(item.get("org") or "").strip()
            vac  = str(item.get("vac") or "").strip()
            date_str = str(item.get("date") or "").strip()
            ext_url  = str(item.get("url") or "").strip()

            meta_title = f"{name} | {sec_title} 2026 | TopSarkariJobs"
            meta_desc  = f"{name}. {sec_title}. {org}. {date_str}."[:300]

            links_html = ""
            if ext_url:
                links_html = f'<a href="{e(ext_url)}" target="_blank" rel="noopener" class="link-btn btn-green"><i class="fa-solid fa-external-link-alt"></i> View Details</a>'

            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{e(meta_title)}</title>
  <meta name="description" content="{e(meta_desc)}"/>
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"/>
  <link rel="canonical" href="{canon_url}"/>
  <link rel="icon" type="image/x-icon" href="/image.ico"/>
  <link rel="stylesheet" href="/styles.css"/>
  <link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/>
  <noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>
  <meta property="og:title" content="{e(meta_title)}"/>
  <meta property="og:url" content="{canon_url}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:image" content="https://www.topsarkarijobs.com/image.png"/>
  <script type="application/ld+json">{{
    "@context":"https://schema.org","@type":"Article",
    "headline":{json.dumps(name)},"description":{json.dumps(meta_desc)},
    "url":{json.dumps(canon_url)},"datePublished":"{TODAY}",
    "publisher":{{"@type":"Organization","name":"TopSarkariJobs","url":"https://www.topsarkarijobs.com"}}
  }}</script>
  <script type="application/ld+json">{{
    "@context":"https://schema.org","@type":"BreadcrumbList",
    "itemListElement":[
      {{"@type":"ListItem","position":1,"name":"Home","item":"https://www.topsarkarijobs.com/"}},
      {{"@type":"ListItem","position":2,"name":"Education","item":"https://www.topsarkarijobs.com/education/"}},
      {{"@type":"ListItem","position":3,"name":{json.dumps(sec_title)},"item":"https://www.topsarkarijobs.com/education/{sec_slug}/"}},
      {{"@type":"ListItem","position":4,"name":{json.dumps(name)},"item":{json.dumps(canon_url)}}}
    ]
  }}</script>
  <style>
    .edu-page{{max-width:900px;margin:24px auto;padding:0 14px 40px;}}
    .edu-hero{{background:linear-gradient(125deg,#4338ca,#7c3aed);border-radius:1.2rem;padding:1.8rem 2rem;color:#fff;margin-bottom:1.4rem;}}
    .edu-hero h1{{font-size:1.4rem;font-weight:800;line-height:1.4;margin-bottom:.8rem;}}
    @media(max-width:600px){{.edu-hero h1{{font-size:1.1rem;}}}}
    .pill{{background:rgba(255,255,255,.15);border-radius:60px;padding:.3rem .9rem;font-size:.78rem;display:inline-flex;align-items:center;gap:6px;margin:.2rem;}}
    .info-card{{background:#fff;border:1px solid #e9f0f5;border-radius:1.2rem;overflow:hidden;margin-bottom:1.2rem;box-shadow:0 4px 12px -4px rgba(0,0,0,.06);}}
    .info-card-head{{background:#4338ca;color:#fff;padding:.8rem 1.2rem;font-weight:700;font-size:.95rem;display:flex;align-items:center;gap:8px;}}
    .info-table{{width:100%;border-collapse:collapse;font-size:.85rem;}}
    .info-table tr{{border-bottom:1px solid #f1f5f9;}}
    .info-table tr:last-child{{border-bottom:none;}}
    .info-table th{{width:38%;background:#f8fafc;padding:.75rem 1rem;text-align:left;font-weight:600;color:#374151;}}
    .info-table td{{padding:.75rem 1rem;color:#1e293b;line-height:1.65;word-break:break-word;}}
    .links-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;padding:1rem;}}
    .link-btn{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;padding:12px 8px;border-radius:10px;text-decoration:none;font-weight:700;font-size:.75rem;text-align:center;transition:.18s;min-height:72px;border:1px solid transparent;}}
    .link-btn:hover{{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.12);}}
    .link-btn i{{font-size:1.1rem;}}
    .btn-green{{background:#f0fdf4;color:#15803d;border-color:#bbf7d0;}}
    .breadcrumb{{font-size:.8rem;color:#64748b;margin-bottom:1rem;display:flex;flex-wrap:wrap;align-items:center;gap:5px;}}
    .breadcrumb a{{color:#1d4ed8;text-decoration:none;}}
  </style>
  <script src="/tsj-menu.js" defer></script>
</head>
<body>
<div id="header-placeholder"></div>
<main>
<div class="edu-page">
  <nav class="breadcrumb">
    <a href="/">Home</a> › <a href="/education/">Education</a> ›
    <a href="/education/{sec_slug}/">{e(sec_title)}</a> › {e(name[:50])}
  </nav>

  <div class="edu-hero">
    <h1>{e(name)}</h1>
    <div>
      <span class="pill"><i class="fa-solid fa-graduation-cap"></i> {e(sec_title)}</span>
      {f'<span class="pill"><i class="fa-solid fa-building"></i> {e(org)}</span>' if org else ""}
      {f'<span class="pill"><i class="fa-solid fa-calendar"></i> {e(date_str)}</span>' if date_str else ""}
    </div>
  </div>

  <div class="info-card">
    <div class="info-card-head"><i class="fa-solid fa-table-list"></i> Details</div>
    <table class="info-table">
      <tr><th>Exam / Result</th><td>{e(name)}</td></tr>
      <tr><th>Category</th><td>{e(sec_title)}</td></tr>
      {f"<tr><th>Organization</th><td>{e(org)}</td></tr>" if org else ""}
      {f"<tr><th>Vacancies</th><td>{e(vac)}</td></tr>" if vac else ""}
      {f"<tr><th>Date</th><td>{e(date_str)}</td></tr>" if date_str else ""}
    </table>
  </div>

  {f'<div class="info-card"><div class="info-card-head"><i class="fa-solid fa-link"></i> Important Links</div><div class="links-grid">{links_html}</div></div>' if links_html else ""}
</div>
</main>
<div id="footer-placeholder"></div>
<script>
  (function(){{
    var h=fetch("/header.html",{{cache:"no-store"}}).then(function(r){{return r.ok?r.text():null;}}).catch(function(){{return null;}});
    document.addEventListener("DOMContentLoaded",function(){{
      h.then(function(html){{if(html){{var el=document.getElementById("header-placeholder");if(el)el.innerHTML=html;if(typeof window.__TSJ_INIT_HEADER==="function")window.__TSJ_INIT_HEADER();}}}});
    }});
  }})();
</script>
</body>
</html>"""

            os.makedirs(page_dir, exist_ok=True)
            with open(os.path.join(page_dir, "index.html"), 'w', encoding='utf-8') as f:
                f.write(html)
            edu_written += 1

    print(f"  Education pages written: {edu_written}")
    print(f"✅ Education static pages generated.")
else:
    print(f"  SKIP: {EDU_WISE} not found")



print("\nRebuilding section data JSON files...")
if os.path.exists(MERGED):
    with open(MERGED, encoding='utf-8') as f:
        merged_data = json.load(f)
    merged_jobs = merged_data.get('jobs', [])

    FILE_MAP = {
        'SR_Latest_Jobs':  'data/sr-latest-jobs.json',
        'SR_Result':       'data/sr-result.json',
        'SR_Admit_Card':   'data/sr-admit-card.json',
        'SR_Admission':    'data/sr-admission.json',
        'SR_Answer_Key':   'data/sr-answer-key.json',
        'UPCOMING_JOBS':   'data/upcoming-jobs.json',
        'STATE_JOBS':      'data/state-jobs.json',
        'CENTRAL_JOBS':    'data/central-jobs.json',
        'ADMISSIONS':      'data/admissions.json',
        'LATEST_JOBS NEW': 'data/latest-jobs-new.json',
        'OFFLINE_FORM':    'data/offline-form.json',
    }

    # Group by category
    from collections import defaultdict
    cats_map = defaultdict(list)
    for j in merged_jobs:
        cats_map[j.get('category', '?')].append(j)

    os.makedirs('data', exist_ok=True)

    for cat, filepath in FILE_MAP.items():
        items = cats_map.get(cat, [])
        items.sort(key=lambda x: x.get('homepage_serial', x.get('sequence', 999)))
        out = {'jobs': items}
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
        top = items[0]['title'][:55] if items else '-'
        print(f"  {filepath}: {len(items)} items | #1={top}")

    # Also rebuild merged-summary.json (top 8 per category for homepage cards)
    summary_jobs = []
    for cat, items in cats_map.items():
        items.sort(key=lambda x: x.get('homepage_serial', x.get('sequence', 999)))
        summary_jobs.extend(items[:8])

    summary = {'scraped_at': merged_data.get('scraped_at', ''), 'jobs': summary_jobs}
    with open('data/merged-summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, separators=(',', ':'))
    print(f"  data/merged-summary.json: {len(summary_jobs)} jobs (top 8 per category)")
    print("✅ Section data files rebuilt.")
else:
    print(f"  SKIP: {MERGED} not found")
