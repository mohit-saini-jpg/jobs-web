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

    meta_desc = (f"{e(title)} – {org}. {vacancies + ' vacancies. ' if vacancies else ''}"
                 f"Last date: {last_date}. Apply {apply_mode}. "
                 f"{qual_str[:80] + '. ' if qual_str else ''}"
                 f"Check eligibility, salary and apply online on Top Sarkari Jobs.")
    if len(meta_desc) < 200:
        meta_desc += " Visit topsarkarijobs.com for complete job details and official application link 2026."

    job_schema = {
        "@context":"https://schema.org","@type":"JobPosting",
        "name":title,"title":title,
        "description": bd.get("short_information") or meta_desc,
        "datePosted":posted_date,"employmentType":"FULL_TIME","url":canon_url,
        "applicantLocationRequirements":{"@type":"Country","name":"India"},
        "hiringOrganization":{"@type":"Organization","name": bd.get("post_name") or "Government of India"},
        "jobLocation":{"@type":"Place","address":{"@type":"PostalAddress",
            "addressCountry":"IN","addressRegion":"India",
            "addressLocality": bd.get("job_location") or "India"}}
    }
    if last_date_r:
        iso = normalise_date(last_date_r)
        if iso: job_schema["validThrough"] = iso
    if vacancies:
        vac_num = re.search(r'\d+', str(vacancies))
        if vac_num: job_schema["totalJobOpenings"] = int(vac_num.group())
    if qual_str:
        job_schema["educationRequirements"] = {"@type":"EducationalOccupationalCredential","credentialCategory":qual_str[:200]}

    bc_schema = {
        "@context":"https://schema.org","@type":"BreadcrumbList",
        "itemListElement":[
            {"@type":"ListItem","position":1,"name":"Home","item":f"{BASE_URL}/"},
            {"@type":"ListItem","position":2,"name":"Latest Jobs","item":f"{BASE_URL}/section/latest-jobs/"},
            {"@type":"ListItem","position":3,"name":title,"item":canon_url}
        ]
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{e(title)} | Top Sarkari Jobs</title>
  <meta name="description" content="{e(meta_desc[:300])}"/>
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"/>
  <link rel="canonical" href="{canon_url}"/>
  <link rel="alternate" hreflang="en" href="{canon_url}"/>
  <link rel="alternate" hreflang="en-IN" href="{canon_url}"/>
  <link rel="alternate" hreflang="x-default" href="{canon_url}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:site_name" content="Top Sarkari Jobs"/>
  <meta property="og:title" content="{e(title)} | Top Sarkari Jobs"/>
  <meta property="og:description" content="{e(meta_desc[:300])}"/>
  <meta property="og:url" content="{canon_url}"/>
  <meta property="og:image" content="{BASE_URL}/image.png"/>
  <meta property="og:image:width" content="512"/>
  <meta property="og:image:height" content="512"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{e(title)} | Top Sarkari Jobs"/>
  <meta name="twitter:description" content="{e(meta_desc[:200])}"/>
  <script type="application/ld+json">{json.dumps(job_schema, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(bc_schema, ensure_ascii=False)}</script>
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
      <h1>{e(title)}</h1>
      <p><strong>Organisation:</strong> {org}</p>
      {"<p><strong>Total Posts:</strong> " + vacancies + "</p>" if vacancies else ""}
      {"<p><strong>Last Date:</strong> " + last_date + "</p>" if last_date else ""}
      <p><strong>Apply Mode:</strong> {apply_mode}</p>
      {"<p><strong>Qualification:</strong> " + qual_str + "</p>" if qual_str else ""}
      {"<p>" + short_info[:400] + "</p>" if short_info else ""}
      {"<p><a href='" + e(source_url) + "'>Apply Online</a></p>" if source_url else ""}
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
            slug = existing_slug
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
            slug = item.get("slug") or slugify(name)
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
    'Railway_Jobs','Police_Defence','Teaching_Faculty','Bank_Jobs','Medical_Hospital'
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
