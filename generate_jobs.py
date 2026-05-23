"""
generate_jobs.py — Auto-runs when Complete_Jobs_Full_Data.json is pushed to GitHub
====================================================================================
Sirf Complete_Jobs_Full_Data.json push karo → ye script sab kar deta hai:
  1. jobs/data/<slug>.json        — har job ke liye data file
  2. jobs/<slug>/index.html       — STATIC HTML (Google directly index karta hai!)
  3. jobs-index.json              — fast index (slug → cat/title/date/url)
  4. Purani stale files           — automatically delete ho jaati hain

Static HTML files kyun? GitHub Pages mein _redirects kaam nahi karta.
/jobs/<slug>/ URL pe agar actual index.html ho toh Google directly fetch kar sakta hai.
"""

import json, re, os, html as html_mod

SRC        = "Complete_Jobs_Full_Data.json"
DEST       = "jobs/data"
JOBS_DIR   = "jobs"
INDEX      = "jobs-index.json"
BASE_URL   = "https://www.topsarkarijobs.com"

VALID_CATS = {
    "Latest_Notifications", "10TH_Pass", "8TH_Pass", "12TH_Pass",
    "Diploma", "ITI", "B_Tech_BE", "B_Com", "Any_Graduate",
    "Any_Post_Graduate", "Railway_Jobs", "Police_Defence",
    "Teaching_Faculty", "Bank_Jobs", "Medical_Hospital",
}

CAT_LABELS = {
    "Latest_Notifications": "Latest Jobs",
    "10TH_Pass":            "10th Pass Jobs",
    "8TH_Pass":             "8th Pass Jobs",
    "12TH_Pass":            "12th Pass Jobs",
    "Diploma":              "Diploma Jobs",
    "ITI":                  "ITI Jobs",
    "B_Tech_BE":            "B.Tech / BE Jobs",
    "B_Com":                "B.Com Jobs",
    "Any_Graduate":         "Graduation Jobs",
    "Any_Post_Graduate":    "Post Graduation Jobs",
    "Railway_Jobs":         "Railway Jobs",
    "Police_Defence":       "Defence Jobs",
    "Teaching_Faculty":     "Teaching Jobs",
    "Bank_Jobs":            "Bank Jobs",
    "Medical_Hospital":     "Medical Jobs",
}

def slugify(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text[:120].strip("-") or "job"

def e(s):
    """HTML-escape a string safely."""
    return html_mod.escape(str(s or ""), quote=True)

def normalise_date(raw):
    """Convert various date formats to YYYY-MM-DD for schema."""
    if not raw:
        return None
    raw = str(raw).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
        return raw
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
              "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    m1 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', raw)
    if m1:
        return f"{m1.group(3)}-{int(m1.group(2)):02d}-{int(m1.group(1)):02d}"
    m2 = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', raw)
    if m2:
        mo = months.get(m2.group(2)[:3].lower())
        if mo:
            return f"{m2.group(3)}-{mo:02d}-{int(m2.group(1)):02d}"
    return None

def build_static_html(slug, title, bd, dates, qualification, salary, cat, source_url):
    """
    Build a complete static HTML page for a job.
    This is the page Google will index directly at /jobs/<slug>/
    It loads job.html via JS after render for the full interactive experience,
    but contains all SEO-critical content in static HTML for crawlers.
    """
    canon_url   = f"{BASE_URL}/jobs/{slug}/"
    cat_label   = CAT_LABELS.get(cat, "Government Jobs")
    org         = e(bd.get("post_name") or bd.get("job_title") or "Government of India")
    vacancies   = e(bd.get("total_vacancies") or "")
    last_date_r = dates.get("last_date_to_apply") or dates.get("last_date") or ""
    last_date   = e(last_date_r)
    apply_mode  = e(bd.get("application_mode") or "Online")
    location    = e(bd.get("job_location") or "India")
    short_info  = e(bd.get("short_information") or "")
    posted_date = normalise_date(bd.get("last_updated") or dates.get("date of notification") or "") or \
                  __import__("datetime").date.today().isoformat()
    qual_str    = ""
    if isinstance(qualification, dict):
        qual_str = e(qualification.get("essential_qualification") or qualification.get("qualification") or "")
    elif isinstance(qualification, str):
        qual_str = e(qualification)
    sal_str = ""
    if isinstance(salary, dict):
        sal_str = e(salary.get("pay_scale") or salary.get("salary") or "")
    elif isinstance(salary, str):
        sal_str = e(salary)

    # Meta description — rich, ≥200 chars
    meta_desc = f"{e(title)} – {org}. {vacancies} vacancies. Last date: {last_date}. " \
                f"Apply {apply_mode}. {qual_str[:100] + '. ' if qual_str else ''}" \
                f"Check eligibility, salary, admit card and apply online on Top Sarkari Jobs."
    if len(meta_desc) < 200:
        meta_desc += " Visit topsarkarijobs.com for complete details and official application link."

    # JobPosting schema
    job_schema = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "name": title,
        "title": title,
        "description": (short_info[:1000] if short_info else meta_desc),
        "datePosted": posted_date,
        "employmentType": "FULL_TIME",
        "url": canon_url,
        "hiringOrganization": {
            "@type": "Organization",
            "name": bd.get("post_name", "Government of India")[:100]
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressCountry": "IN",
                "addressRegion": "India",
                "addressLocality": bd.get("job_location", "India")[:100]
            }
        }
    }
    if last_date_r:
        iso_last = normalise_date(last_date_r)
        if iso_last:
            job_schema["validThrough"] = iso_last
    if bd.get("total_vacancies"):
        vac_num = re.search(r'\d+', str(bd["total_vacancies"]))
        if vac_num:
            job_schema["totalJobOpenings"] = int(vac_num.group())
    if qual_str:
        job_schema["educationRequirements"] = {
            "@type": "EducationalOccupationalCredential",
            "credentialCategory": qual_str[:200]
        }

    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home",        "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "Latest Jobs", "item": f"{BASE_URL}/section/latest-jobs/"},
            {"@type": "ListItem", "position": 3, "name": title,         "item": canon_url}
        ]
    }

    job_schema_json      = json.dumps(job_schema,      ensure_ascii=False)
    breadcrumb_schema_json = json.dumps(breadcrumb_schema, ensure_ascii=False)
    slug_json            = json.dumps(slug)
    canon_json           = json.dumps(canon_url)
    title_json           = json.dumps(title + " | Top Sarkari Jobs")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>

  <!-- SEO: All critical tags are STATIC — no JS needed for Google to read these -->
  <title>{e(title)} | Top Sarkari Jobs</title>
  <meta name="description" content="{e(meta_desc[:300])}"/>
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"/>
  <link rel="canonical" href="{canon_url}"/>
  <link rel="alternate" hreflang="en"       href="{canon_url}"/>
  <link rel="alternate" hreflang="en-IN"    href="{canon_url}"/>
  <link rel="alternate" hreflang="x-default" href="{canon_url}"/>

  <!-- Open Graph -->
  <meta property="og:type"        content="article"/>
  <meta property="og:site_name"   content="Top Sarkari Jobs"/>
  <meta property="og:title"       content="{e(title)} | Top Sarkari Jobs"/>
  <meta property="og:description" content="{e(meta_desc[:300])}"/>
  <meta property="og:url"         content="{canon_url}"/>
  <meta property="og:image"       content="{BASE_URL}/image.png"/>
  <!-- Twitter -->
  <meta name="twitter:card"        content="summary_large_image"/>
  <meta name="twitter:title"       content="{e(title)} | Top Sarkari Jobs"/>
  <meta name="twitter:description" content="{e(meta_desc[:200])}"/>
  <meta name="twitter:image"       content="{BASE_URL}/image.png"/>

  <!-- Structured Data: JobPosting + BreadcrumbList — STATIC, Google reads immediately -->
  <script type="application/ld+json">{job_schema_json}</script>
  <script type="application/ld+json">{breadcrumb_schema_json}</script>

  <!-- Expose slug to job.html scripts -->
  <script>
    window.__TSJ_SLUG       = {slug_json};
    window.__TSJ_PAGE_TITLE = {title_json};
    window.__TSJ_CANONICAL  = {canon_json};
    // Set correct URL immediately (back/forward navigation)
    try {{
      if (window.location.pathname !== '/jobs/' + window.__TSJ_SLUG + '/') {{
        window.history.replaceState(null, '', '/jobs/' + window.__TSJ_SLUG + '/');
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
  <!--
    STATIC CONTENT: Visible to Google even without JS.
    The full interactive job page loads via job.html script below.
  -->
  <noscript>
    <div style="font-family:sans-serif;max-width:800px;margin:40px auto;padding:20px">
      <h1>{e(title)}</h1>
      <p><strong>Organisation:</strong> {org}</p>
      <p><strong>Total Posts:</strong> {vacancies}</p>
      <p><strong>Last Date:</strong> {last_date}</p>
      <p><strong>Apply Mode:</strong> {apply_mode}</p>
      <p><strong>Location:</strong> {location}</p>
      {"<p><strong>Qualification:</strong> " + qual_str + "</p>" if qual_str else ""}
      {"<p><strong>Salary:</strong> " + sal_str + "</p>" if sal_str else ""}
      {("<p>" + short_info[:500] + "</p>") if short_info else ""}
      {"<p><a href='" + e(source_url) + "'>Apply Online / Official Website</a></p>" if source_url else ""}
      <p><a href="/">← Back to Top Sarkari Jobs</a></p>
    </div>
  </noscript>

  <!-- Loading indicator while job.html initialises -->
  <div id="__tsj_loader" style="display:flex;align-items:center;justify-content:center;
       min-height:100vh;background:#f0f4f8;font-family:sans-serif;">
    <div style="text-align:center">
      <div style="width:40px;height:40px;border:4px solid #e2e8f0;border-top-color:#1d4ed8;
           border-radius:50%;animation:spin 0.7s linear infinite;margin:0 auto 12px"></div>
      <p style="color:#374151;font-weight:600;margin:0">Loading job details…</p>
      <style>@keyframes spin{{to{{transform:rotate(360deg)}}}}</style>
    </div>
  </div>

  <!--
    Load job.html's scripts — they read window.__TSJ_SLUG and render
    the full interactive job page, replacing the loader above.
  -->
  <script>
  (function() {{
    // job.html inline scripts expect these sessionStorage values
    try {{ sessionStorage.setItem('__tsj_slug', window.__TSJ_SLUG); }} catch(_) {{}}

    // Dynamically load job.html body content via fetch and inject
    fetch('/job.html')
      .then(function(r) {{ return r.text(); }})
      .then(function(html) {{
        // Extract only the <body> content from job.html to avoid duplicate <head>
        var bodyMatch = html.match(/<body[^>]*>([\\s\\S]*)</body>/i);
        if (bodyMatch) {{
          var loader = document.getElementById('__tsj_loader');
          if (loader) loader.remove();
          // Create a container and inject body HTML
          var wrapper = document.createElement('div');
          wrapper.innerHTML = bodyMatch[1];
          // Move all children to document body
          while (wrapper.firstChild) {{
            document.body.appendChild(wrapper.firstChild);
          }}
          // Re-execute inline scripts from job.html body
          Array.from(document.body.querySelectorAll('script')).forEach(function(oldScript) {{
            if (oldScript.hasAttribute('data-executed')) return;
            var s = document.createElement('script');
            if (oldScript.src) {{
              s.src = oldScript.src;
              if (oldScript.defer) s.defer = true;
              if (oldScript.async) s.async = true;
            }} else {{
              s.textContent = oldScript.textContent;
            }}
            oldScript.setAttribute('data-executed', '1');
            oldScript.parentNode.replaceChild(s, oldScript);
          }});
        }}
      }})
      .catch(function(e) {{
        // Fallback: full page redirect to job.html with slug param
        window.location.href = '/job.html?slug=' + encodeURIComponent(window.__TSJ_SLUG);
      }});
  }})();
  </script>
</body>
</html>"""

# ═══════════════════════════════════════════════════════════
# MAIN PROCESSING
# ═══════════════════════════════════════════════════════════

print(f"Loading {SRC}...")
with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

os.makedirs(DEST, exist_ok=True)

existing_json_files  = set(os.listdir(DEST))
existing_html_dirs   = set()
# Track existing /jobs/<slug>/ dirs (excluding 'data' subfolder)
for item in os.listdir(JOBS_DIR):
    item_path = os.path.join(JOBS_DIR, item)
    if os.path.isdir(item_path) and item != "data":
        existing_html_dirs.add(item)

index       = {}
new_files   = set()
new_dirs    = set()
written     = 0
skipped     = 0
seen_slugs  = {}

for cat, jobs in data.items():
    if not isinstance(jobs, list):
        continue
    if cat not in VALID_CATS:
        print(f"  WARN: Unknown category '{cat}' — skipping")
        continue

    for job in jobs:
        bd     = job.get("basic_details", {}) or {}
        dates  = job.get("important_dates", {}) or {}
        qual   = job.get("qualification") or {}
        salary = job.get("salary_details") or {}
        title  = (bd.get("job_title", "") or "").strip()
        url    = (job.get("source_url", "") or "").strip()

        if not title:
            skipped += 1
            continue

        slug  = slugify(title)
        fname = f"{slug}.json"

        # Duplicate slug? Add category suffix
        if slug in seen_slugs and seen_slugs[slug] != cat:
            slug  = f"{slug}-{cat.lower().replace('_','-')}"
            fname = f"{slug}.json"

        seen_slugs[slug] = cat
        job["category"]  = cat

        # 1. Write jobs/data/<slug>.json
        with open(os.path.join(DEST, fname), "w", encoding="utf-8") as f:
            json.dump(job, f, ensure_ascii=False, separators=(",", ":"))
        new_files.add(fname)

        # 2. Write jobs/<slug>/index.html  ← THE KEY SEO FIX
        slug_dir = os.path.join(JOBS_DIR, slug)
        os.makedirs(slug_dir, exist_ok=True)
        html_path = os.path.join(slug_dir, "index.html")
        html_content = build_static_html(slug, title, bd, dates, qual, salary, cat, url)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        new_dirs.add(slug)

        # 3. Update index
        last_date = (dates.get("last_date_to_apply") or dates.get("last_date") or "").strip()
        index[slug] = {
            "cat":       cat,
            "title":     title[:120],
            "last_date": last_date[:30] if last_date else "",
            "url":       url,
        }
        written += 1

# ── Cleanup stale JSON files ──
stale_json = existing_json_files - new_files
for fname in stale_json:
    try:
        os.remove(os.path.join(DEST, fname))
    except Exception:
        pass

# ── Cleanup stale HTML dirs ──
stale_dirs = existing_html_dirs - new_dirs
for dname in stale_dirs:
    import shutil
    try:
        shutil.rmtree(os.path.join(JOBS_DIR, dname))
    except Exception:
        pass

# ── Write jobs-index.json ──
with open(INDEX, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, separators=(",", ":"))

print(f"\nDone!")
print(f"  JSON files  : {written} written, {len(stale_json)} deleted")
print(f"  HTML pages  : {written} static /jobs/<slug>/index.html created")
print(f"  HTML stale  : {len(stale_dirs)} deleted")
print(f"  Skipped     : {skipped} (no title)")
print(f"  Index       : {len(index)} entries")

cat_count = {}
for v in index.values():
    cat_count[v["cat"]] = cat_count.get(v["cat"], 0) + 1
print("\nPer category:")
for cat in ["Latest_Notifications","10TH_Pass","8TH_Pass","12TH_Pass","Diploma",
            "ITI","B_Tech_BE","B_Com","Any_Graduate","Any_Post_Graduate",
            "Railway_Jobs","Police_Defence","Teaching_Faculty","Bank_Jobs","Medical_Hospital"]:
    n = cat_count.get(cat, 0)
    print(f"  {cat:<25} {n}")
