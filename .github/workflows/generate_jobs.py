"""
generate_jobs.py — Complete_Jobs_Full_Data.json se static pages generate karta hai
==================================================================================
SINGLE SOURCE: Complete_Jobs_Full_Data.json (root)
  └── freejobalert_categories  → 53 qualification/type categories → HTML pages
  └── sarkari_data.jobs        → SR_Latest_Jobs, SR_Result, SR_Admit_Card, etc.
  └── education_jobs.sections  → education pages data (section pages use ye directly)
  └── state_jobs.sections      → state pages data (state pages use ye directly)

UNTOUCHED (as-is, no changes):
  - dailyupdates.json          → apna function continue (daily sections render)
  - jobs.json                  → apna function continue
  - tools.json                 → apna function continue

OUTPUT:
  - jobs/{slug}/index.html     → static HTML (Google directly indexes)
  - jobs/data/{slug}.json      → job data file
  - jobs-index.json            → fast lookup index
  - sections-index.json        → homepage + section page cards
  - data/master_clean_jobs.json→ dedup'd clean list
"""

import json, re, os, html as html_mod
from datetime import date
from pathlib import Path
from collections import defaultdict

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT     = Path('.')
# Try data/Complete_Jobs_Full_Data.json first (has freejobalert_categories wrapper)
# Fallback to root Complete_Jobs_Full_Data.json
_cj_data  = ROOT / 'data' / 'Complete_Jobs_Full_Data.json'
_cj_root  = ROOT / 'Complete_Jobs_Full_Data.json'
CJ_FILE   = _cj_data if _cj_data.exists() else _cj_root  # prefer data/ version
DAILY    = ROOT / 'dailyupdates.json'                  # UNTOUCHED — only read for Top20/Today
DEST     = ROOT / 'jobs' / 'data'
JOBS_DIR = ROOT / 'jobs'
INDEX    = ROOT / 'jobs-index.json'
SINDEX   = ROOT / 'sections-index.json'
MASTER   = ROOT / 'data' / 'master_clean_jobs.json'
BASE_URL = 'https://www.topsarkarijobs.com'
TODAY    = date.today().isoformat()

BLOCKED_DOMAINS = {
    'sarkariresult.com','freejobalert.com','sarkarinetwork.com','sarkariresultshine.com',
    'www.sarkariresult.com','www.freejobalert.com','www.sarkarinetwork.com','www.sarkariresultshine.com',
}

# ─── Helpers ─────────────────────────────────────────────────────────────────
def slugify(text):
    import unicodedata
    t = unicodedata.normalize('NFKD', str(text))
    t = t.encode('ascii', 'ignore').decode('ascii')
    t = t.replace('&', ' and ')
    for ch in "''`\"": t = t.replace(ch, '')
    t = t.lower()
    t = re.sub(r'[^a-z0-9]+', '-', t)
    t = t.strip('-')
    t = re.sub(r'-{2,}', '-', t)
    return t[:120] or 'job'

def esc(s):
    return html_mod.escape(str(s or ''), quote=True)

def normalise_date(raw):
    if not raw: return ''
    raw = str(raw).strip()
    m = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})', raw)
    if m: return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', raw)
    if m: return raw[:10]
    return ''

def is_blocked(url):
    if not url or not isinstance(url, str): return True
    u = url.strip().lower()
    return any(d in u for d in BLOCKED_DOMAINS)

def sanitize_url(url):
    """Remove AWS presigned URL params — they expire & trigger secret scanners"""
    if not url or not isinstance(url, str): return url
    url = url.strip()
    if 'X-Amz-' in url or 'x-amz-' in url:
        # Strip everything from ? onward (presigned params)
        base = url.split('?')[0]
        return base if base.startswith('http') else ''
    return url

def fmt_date(d):
    nd = normalise_date(d)
    if nd:
        parts = nd.split('-')
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return d or ''

def normalize_title(t):
    return re.sub(r'[^a-z0-9]', '', str(t).lower().strip())

# ─── Section renderer ─────────────────────────────────────────────────────────
def render_section(data):
    if not data: return ''
    if isinstance(data, str):
        return f'<div class="job-text-block">{esc(data)}</div>'
    if isinstance(data, list):
        items = ''.join(f'<li>{esc(str(i))}</li>' for i in data if i)
        return f'<ul class="job-list">{items}</ul>' if items else ''
    if isinstance(data, dict):
        rows = ''
        for k, v in data.items():
            if v is None or v == '' or v == {} or v == []: continue
            kl = str(k).replace('_', ' ').title()
            if isinstance(v, (dict, list)):
                vh = render_section(v)
            else:
                vs = str(v)
                if vs.startswith('http') and not is_blocked(vs):
                    vh = f'<a href="{esc(vs)}" target="_blank" rel="noopener noreferrer">{esc(vs[:60])}</a>'
                elif vs.startswith('http'):
                    continue
                else:
                    vh = esc(vs)
            rows += f'<tr><th>{esc(kl)}</th><td>{vh}</td></tr>'
        return f'<div class="table-scroll"><table class="info-table"><tbody>{rows}</tbody></table></div>' if rows else ''
    return ''

# ─── HTML page builder ────────────────────────────────────────────────────────
def build_html(slug, job):
    title    = job.get('title', slug.replace('-', ' ').title())
    org      = job.get('organization') or 'Government of India'
    posts    = job.get('total_vacancies') or 'Various'
    last_date= job.get('last_date') or 'See Notification'
    mode     = job.get('application_mode') or 'Online'
    short_info = job.get('short_info', '')
    year     = '2026'
    canonical = f'{BASE_URL}/jobs/{slug}/'

    # SEO
    seo_title = f"{title} | Top Sarkari Jobs"
    if len(seo_title) > 65:
        seo_title = title[:45].rstrip() + '… | Top Sarkari Jobs'
    meta_desc = f"{title}: {posts} vacancies, last date {last_date}. {short_info[:70] if short_info else org + ' recruitment ' + year}."
    meta_desc = meta_desc[:160]

    # Schemas
    job_schema = {
        '@context': 'https://schema.org', '@type': 'JobPosting',
        'title': title,
        'description': short_info or f'{org} is recruiting {posts} posts.',
        'datePosted': job.get('notification_date') or job.get('last_updated', '') or TODAY,
        'validThrough': last_date,
        'employmentType': 'FULL_TIME',
        'url': canonical,
        'identifier': {'@type': 'PropertyValue', 'name': job.get('post_name', title), 'value': slug},
        'hiringOrganization': {'@type': 'Organization', 'name': org, 'sameAs': 'https://www.india.gov.in'},
        'applicantLocationRequirements': {'@type': 'Country', 'name': 'India'},
        'jobLocation': {'@type': 'Place', 'address': {'@type': 'PostalAddress', 'addressCountry': 'IN'}},
        'author': {'@type': 'Organization', 'name': 'TopSarkariJobs Editorial Team', 'url': f'{BASE_URL}/about/'}
    }
    vac_str = str(posts)
    if re.search(r'^\d+$', vac_str): job_schema['totalJobOpenings'] = int(vac_str)

    bc_schema = {
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': f'{BASE_URL}/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Latest Jobs', 'item': f'{BASE_URL}/section/latest-jobs/'},
            {'@type': 'ListItem', 'position': 3, 'name': title, 'item': canonical}
        ]
    }

    faq_items = [
        (f'{title} last date kya hai?', f'Last date: {last_date}.'),
        (f'{title} ke liye eligibility kya hai?', 'Qualification ke liye official notification dekhein.'),
        (f'{title} mein total vacancies kitni hain?', f'Total {posts} posts hain.'),
        (f'{title} apply kaise karein?', f'{mode} mode mein apply karein. Official website par jakar form fill karein.'),
        (f'{org} ki official website kya hai?', 'Important Links section mein official website ka link diya gaya hai.'),
        (f'{title} ka selection process kya hai?', 'Written Test / Interview / Document Verification. Official notification dekhein.'),
    ]
    faq_schema = {
        '@context': 'https://schema.org', '@type': 'FAQPage',
        'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faq_items]
    }
    art_schema = {
        '@context': 'https://schema.org', '@type': 'Article',
        'headline': title, 'url': canonical,
        'author': {'@type': 'Organization', 'name': 'TopSarkariJobs Editorial Team'},
        'publisher': {'@type': 'Organization', 'name': 'Top Sarkari Jobs', 'url': BASE_URL}
    }

    # Content sections
    sections_html = ''
    if job.get('important_dates'):
        rows = ''.join(
            f"<tr><td>{esc(str(k).replace('_',' ').title())}</td><td><strong>{esc(str(v))}</strong></td></tr>"
            for k, v in job['important_dates'].items() if v
        )
        if rows:
            sections_html += f'''
    <section class="job-card" id="important-dates">
      <div class="job-card-head" style="background:linear-gradient(135deg,#0f766e,#0d9488)">
        <i class="fa-solid fa-calendar-days"></i><h2>Important Dates</h2>
      </div>
      <div class="job-card-body"><div class="table-scroll"><table class="info-table"><tbody>{rows}</tbody></table></div></div>
    </section>'''

    SECTION_MAP = [
        ('application_fee','Application Fee','fa-indian-rupee-sign','linear-gradient(135deg,#dc2626,#b91c1c)'),
        ('age_limit','Age Limit','fa-user-clock','linear-gradient(135deg,#7c3aed,#6d28d9)'),
        ('qualification','Qualification / Eligibility','fa-graduation-cap','linear-gradient(135deg,#0284c7,#0369a1)'),
        ('vacancy_details','Vacancy Details','fa-users','linear-gradient(135deg,#059669,#047857)'),
        ('category_wise_vacancy','Category Wise Vacancy','fa-table','linear-gradient(135deg,#047857,#065f46)'),
        ('salary_details','Salary / Pay Scale','fa-money-bill-wave','linear-gradient(135deg,#ca8a04,#a16207)'),
        ('selection_process','Selection Process','fa-list-check','linear-gradient(135deg,#4f46e5,#4338ca)'),
        ('exam_pattern','Exam Pattern','fa-file-alt','linear-gradient(135deg,#0e7490,#0891b2)'),
        ('syllabus','Syllabus','fa-book-open','linear-gradient(135deg,#16a34a,#15803d)'),
        ('physical_eligibility','Physical Eligibility','fa-person-running','linear-gradient(135deg,#b45309,#92400e)'),
        ('how_to_apply','How To Apply','fa-pen-to-square','linear-gradient(135deg,#1e40af,#1e3a8a)'),
        ('important_instructions','Important Instructions','fa-triangle-exclamation','linear-gradient(135deg,#e11d48,#be123c)'),
    ]
    for key, label, icon, color in SECTION_MAP:
        content = job.get(key)
        if not content: continue
        rendered = render_section(content)
        if not rendered: continue
        sections_html += f'''
    <section class="job-card" id="{key.replace('_','-')}">
      <div class="job-card-head" style="background:{color}">
        <i class="fa-solid {icon}"></i><h2>{label}</h2>
      </div>
      <div class="job-card-body">{rendered}</div>
    </section>'''

    # Important links (filtered)
    links = job.get('important_links', {})
    links_html = ''
    LINK_MAP = {
        'apply_online': ('Apply Online', 'btn-green', 'fa-pen-to-square'),
        'apply_online_link': ('Apply Online', 'btn-green', 'fa-pen-to-square'),
        'notification_pdf': ('Download Notification', 'btn-blue', 'fa-file-pdf'),
        'official_notification_pdf': ('Official Notification', 'btn-blue', 'fa-file-pdf'),
        'official_website': ('Official Website', 'btn-grey', 'fa-globe'),
        'result': ('View Result', 'btn-purple', 'fa-trophy'),
        'admit_card': ('Admit Card', 'btn-orange', 'fa-id-card'),
        'answer_key': ('Answer Key', 'btn-yellow', 'fa-key'),
        'click_here': ('Click Here', 'btn-grey', 'fa-arrow-up-right-from-square'),
    }
    if isinstance(links, dict):
        for k, v in links.items():
            if k == 'click_here' and isinstance(v, list):
                for url in v:
                    if url and isinstance(url, str) and url.startswith('http') and not is_blocked(url):
                        lbl, cls, ico = LINK_MAP['click_here']
                        links_html += f'<a href="{esc(url)}" class="link-btn {cls}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ico}"></i> {lbl}</a>\n'
            elif isinstance(v, str) and v.startswith('http') and not is_blocked(v):
                lbl, cls, ico = LINK_MAP.get(k, ('Link', 'btn-grey', 'fa-link'))
                links_html += f'<a href="{esc(v)}" class="link-btn {cls}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ico}"></i> {lbl}</a>\n'
    if not links_html:
        links_html = '<p>Official notification ke liye upar di gayi information dekhein.</p>'

    faq_html = '\n'.join(
        f'<div class="faq-item"><h3 class="faq-q"><i class="fa-solid fa-circle-question"></i> {esc(q)}</h3>'
        f'<div class="faq-a"><p>{esc(a)}</p></div></div>'
        for q, a in faq_items
    )

    seo_p1 = f"{org} ne {title} ke liye official notification jari kiya hai. Is recruitment mein kul {posts} posts ke liye eligible candidates se applications mangi gayi hain. Last date {last_date} hai."
    seo_p2 = f"Application {mode} mode mein ki ja sakti hai. Selection process mein written test aur/ya interview shamil ho sakta hai. Salary aur age limit ke liye upar di gayi table dekhein."
    seo_p3 = f"{title} ek achi opportunity hai un candidates ke liye jo government jobs dhundh rahe hain. Kisi bhi query ke liye official website visit karein ya notification download karein."

    return f'''<!DOCTYPE html>
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
  <script type="application/ld+json">{json.dumps(job_schema, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(bc_schema, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(faq_schema, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(art_schema, ensure_ascii=False)}</script>
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
</head>
<body>
<div id="header-placeholder"></div>
<main id="main-content">
  <div class="container">
    <nav class="breadcrumb" aria-label="breadcrumb">
      <a href="/">Home</a> &rsaquo; <a href="/section/latest-jobs/">Latest Jobs</a> &rsaquo; <span>{esc(title)}</span>
    </nav>
    <article itemscope itemtype="https://schema.org/JobPosting">
      <header class="job-hero-card">
        <h1 itemprop="title">{esc(title)}</h1>
        <p class="job-org" itemprop="hiringOrganization" itemscope itemtype="https://schema.org/Organization">
          <span itemprop="name">{esc(org)}</span>
        </p>
        <div class="job-badges">
          <span class="badge badge-posts"><i class="fa-solid fa-users"></i> Posts: {esc(posts)}</span>
          <span class="badge badge-date"><i class="fa-solid fa-calendar-days"></i> Last Date: {esc(last_date)}</span>
          <span class="badge badge-mode"><i class="fa-solid fa-computer"></i> {esc(mode)}</span>
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
        <div class="job-card-body"><div class="faq-list">{faq_html}</div></div>
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
</main>
<div id="footer-placeholder"></div>
<script src="/tsj-menu.js" defer></script>
</body>
</html>'''

# ─── Extract all jobs from Complete_Jobs_Full_Data.json ──────────────────────
def extract_all_jobs(cj):
    all_jobs = []
    seen_slugs = set()
    seen_keys  = set()

    def add_job(job):
        slug = job.get('slug', '')
        title = job.get('title', '')
        if not slug or not title: return
        title_norm = normalize_title(title)
        date_norm  = normalise_date(job.get('last_date', ''))
        key1 = slug
        key2 = f"{title_norm}|{date_norm}"
        if key1 in seen_slugs: return
        if key2 in seen_keys and title_norm: return
        seen_slugs.add(key1)
        seen_keys.add(key2)
        all_jobs.append(job)

    # 1. freejobalert_categories (new format) OR flat top-level keys (old format)
    fj_cats = cj.get('freejobalert_categories')
    if not fj_cats:
        # Old flat format: root keys ARE the categories
        OLD_CATS = {'10TH_Pass','8TH_Pass','12TH_Pass','Diploma','ITI','B_Tech_BE',
                    'B_Com','Any_Graduate','Any_Post_Graduate','Railway_Jobs',
                    'Police_Defence','Teaching_Faculty','Bank_Jobs','Medical_Hospital',
                    'Last_Date_Reminder','Latest_Notifications'}
        fj_cats = {k: v for k, v in cj.items() if k in OLD_CATS and isinstance(v, list)}
    for cat, jobs in fj_cats.items():
        if not isinstance(jobs, list): continue
        for job in jobs:
            bd    = job.get('basic_details', {})
            title = bd.get('job_title', '').strip()
            if not title: continue
            dates = job.get('important_dates', {})
            last_date = (dates.get('last_date_to_apply') or dates.get('last_date') or
                         dates.get('Last Date to Apply') or dates.get('Last Date') or '')
            notif_date = dates.get('notification date') or bd.get('last_updated', '')
            # Filter important_links
            raw_links = job.get('important_links', {})
            clean_links = {}
            if isinstance(raw_links, dict):
                for k, v in raw_links.items():
                    if k == 'click_here' and isinstance(v, list):
                        filtered = [sanitize_url(u) for u in v if isinstance(u, str) and not is_blocked(u)]
                        filtered = [u for u in filtered if u]
                        if filtered: clean_links[k] = filtered
                    elif isinstance(v, str) and not is_blocked(v):
                        sv = sanitize_url(v)
                        if sv: clean_links[k] = sv

            add_job({
                'slug': slugify(title), 'title': title,
                'organization': bd.get('organization_name', ''),
                'post_name': bd.get('post_name', ''),
                'total_vacancies': str(bd.get('total_vacancies', '')),
                'application_mode': bd.get('application_mode', ''),
                'job_type': bd.get('job_type', ''),
                'short_info': bd.get('short_information', ''),
                'last_date': last_date, 'last_updated': bd.get('last_updated', ''),
                'notification_date': notif_date, 'category': cat,
                'source': 'freejobalert',
                'important_dates': dates,
                'application_fee': job.get('application_fee', {}),
                'age_limit': job.get('age_limit', {}),
                'qualification': job.get('qualification', {}),
                'vacancy_details': job.get('vacancy_details', {}),
                'category_wise_vacancy': job.get('category_wise_vacancy', {}),
                'salary_details': job.get('salary_details', {}),
                'selection_process': job.get('selection_process', {}),
                'exam_pattern': job.get('exam_pattern', {}),
                'syllabus': job.get('syllabus', {}),
                'physical_eligibility': job.get('physical_eligibility', {}),
                'how_to_apply': job.get('how_to_apply', {}),
                'important_instructions': job.get('important_instructions', {}),
                'important_links': clean_links,
                'faq': job.get('faq', {}), 'seo_tags': job.get('seo_tags', {}),
            })

    # 2. sarkari_data
    for job in cj.get('sarkari_data', {}).get('jobs', []):
        title = job.get('title', '').strip()
        if not title: continue
        imp_links = {}
        for key in ['apply_online_link', 'official_website_link', 'official_notification_pdf_link']:
            url = job.get(key, '')
            if url and not is_blocked(url):
                imp_links[key.replace('_link', '').replace('_pdf', '')] = url
        add_job({
            'slug': slugify(title), 'title': title,
            'organization': job.get('organization', ''),
            'post_name': job.get('post_name', ''),
            'total_vacancies': str(job.get('total_vacancy', '')),
            'application_mode': job.get('apply_mode', ''),
            'job_type': '', 'short_info': job.get('jobs_info', ''),
            'last_date': job.get('important_dates', {}).get('Last Date', ''),
            'last_updated': job.get('listing_date', ''),
            'notification_date': '', 'category': job.get('category', 'LATEST_JOBS NEW'),
            'source': 'sarkari',
            'important_dates': job.get('important_dates', {}),
            'application_fee': {}, 'age_limit': {},
            'qualification': {}, 'vacancy_details': {},
            'category_wise_vacancy': {},
            'salary_details': {'salary': job.get('salary_pay_scale', '')},
            'selection_process': {}, 'exam_pattern': {}, 'syllabus': {},
            'physical_eligibility': {}, 'how_to_apply': {},
            'important_instructions': {}, 'important_links': imp_links,
            'faq': {}, 'seo_tags': {},
        })

    # 3. dailyupdates.json — Top 20 Jobs + Today Updates sections only
    #    (dailyupdates.json UNTOUCHED — only reading Top20/Today for job pages)
    DAILY_SECTIONS = {'Top 20 Jobs', 'Today Updates'}
    if DAILY.exists():
        try:
            with open(DAILY, encoding='utf-8') as f:
                ddata = json.load(f)
            secs = ddata.get('sections', []) if isinstance(ddata, dict) else []
            for sec in secs:
                if sec.get('title') not in DAILY_SECTIONS: continue
                for item in sec.get('items', []):
                    name = (item.get('name') or item.get('title') or '').strip()
                    if not name: continue
                    add_job({
                        'slug': slugify(name), 'title': name,
                        'organization': '', 'post_name': name,
                        'total_vacancies': '', 'application_mode': 'Online',
                        'job_type': '', 'short_info': '',
                        'last_date': item.get('lastDate') or item.get('date') or '',
                        'last_updated': item.get('date', ''),
                        'notification_date': '', 'category': 'Latest_Notifications',
                        'source': 'daily',
                        'important_dates': {}, 'application_fee': {}, 'age_limit': {},
                        'qualification': {}, 'vacancy_details': {},
                        'category_wise_vacancy': {}, 'salary_details': {},
                        'selection_process': {}, 'exam_pattern': {}, 'syllabus': {},
                        'physical_eligibility': {}, 'how_to_apply': {},
                        'important_instructions': {},
                        'important_links': {} if is_blocked(item.get('url','')) else ({'apply_online': item.get('url','')} if item.get('url','').startswith('http') else {}),
                        'faq': {}, 'seo_tags': {},
                    })
        except Exception as e:
            print(f"  dailyupdates.json read error: {e}")

    return all_jobs

# ─── Build sections-index.json ───────────────────────────────────────────────
def build_sections_index(all_jobs):
    buckets = defaultdict(list)
    for job in all_jobs:
        cat = job.get('category', '')
        if not cat: continue
        buckets[cat].append((
            normalise_date(job.get('last_date', '')),
            {'slug': job['slug'], 'name': job['title'],
             'date': job.get('last_date', ''),
             'org': job.get('organization', ''),
             'vac': job.get('total_vacancies', '')}
        ))
    result = {}
    for cat, items in buckets.items():
        items.sort(key=lambda x: x[0], reverse=True)
        result[cat] = [x[1] for x in items]
    return result

# ─── MAIN ─────────────────────────────────────────────────────────────────────
print("=" * 55)
print("TSJ Static Page Generator")
print(f"Source: Complete_Jobs_Full_Data.json")
print(f"Date:   {TODAY}")
print("=" * 55)

if not CJ_FILE.exists():
    print(f"❌ {CJ_FILE} not found!")
    exit(1)

print(f"\n📖 Reading {CJ_FILE}...")
with open(CJ_FILE, encoding='utf-8') as f:
    cj = json.load(f)
print(f"   freejobalert categories: {len(cj.get('freejobalert_categories', {}))}")
print(f"   sarkari_data jobs:       {len(cj.get('sarkari_data', {}).get('jobs', []))}")
print(f"   education sections:      {len(cj.get('education_jobs', {}).get('sections', []))}")
print(f"   state sections:          {len(cj.get('state_jobs', {}).get('sections', []))}")

print("\n🔄 Extracting + deduplicating jobs...")
all_jobs = extract_all_jobs(cj)
print(f"   Unique jobs: {len(all_jobs)}")

# Save master_clean_jobs.json
MASTER.parent.mkdir(exist_ok=True)
with open(MASTER, 'w', encoding='utf-8') as f:
    json.dump(all_jobs, f, ensure_ascii=False, indent=2)
print(f"   ✅ Saved {MASTER}")

# Build sections-index.json
print("\n📊 Building sections-index.json...")
sindex = build_sections_index(all_jobs)
with open(SINDEX, 'w', encoding='utf-8') as f:
    json.dump(sindex, f, ensure_ascii=False, separators=(',', ':'))
total_si = sum(len(v) for v in sindex.values())
print(f"   ✅ {len(sindex)} categories, {total_si} items")

# Generate HTML pages + JSON data files
print("\n🏗️  Generating static HTML pages...")
DEST.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(exist_ok=True)

generated = skipped = errors = 0
index = {}

for job in all_jobs:
    slug = job.get('slug', '')
    if not slug: continue

    out_dir  = JOBS_DIR / slug
    out_html = out_dir / 'index.html'
    out_json = DEST / f'{slug}.json'

    # Skip existing pages (preserve manually edited pages)
    if out_html.exists():
        skipped += 1
    else:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            html_content = build_html(slug, job)
            out_html.write_text(html_content, encoding='utf-8')
            generated += 1
            if generated % 200 == 0:
                print(f"   Generated {generated} pages...")
        except Exception as e:
            print(f"   ❌ Error {slug}: {e}")
            errors += 1

    # Always update JSON data file
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(job, f, ensure_ascii=False, separators=(',', ':'))

    # Index entry
    index[slug] = {
        'cat':       job.get('category', ''),
        'title':     job['title'][:120],
        'last_date': job.get('last_date', '')[:30],
        'org':       job.get('organization', '')[:60],
    }

# Write jobs-index.json
with open(INDEX, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, separators=(',', ':'))

print(f"\n✅ COMPLETE!")
print(f"   New pages generated: {generated}")
print(f"   Existing (skipped):  {skipped}")
print(f"   Errors:              {errors}")
print(f"   Total in index:      {len(index)}")
print(f"   sections-index:      {total_si} items")
