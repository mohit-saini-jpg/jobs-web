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
    """Convert any date string to ISO 8601 YYYY-MM-DD format."""
    if not raw: return ''
    raw = str(raw).strip()
    # Format: DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})', raw)
    if m: return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    # Format: YYYY-MM-DD (already ISO)
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', raw)
    if m: return raw[:10]
    # Format: "23 May. 2026" or "23 May 2026"
    MONTHS = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
              'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    m = re.match(r'^(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})', raw)
    if m:
        mon = MONTHS.get(m.group(2).lower()[:3])
        if mon: return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    # Format: "May 29, 2026" or "May 29 2026"
    m = re.match(r'^([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})', raw)
    if m:
        mon = MONTHS.get(m.group(1).lower()[:3])
        if mon: return f"{m.group(3)}-{mon:02d}-{int(m.group(2)):02d}"
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

# ═══════════════════════════════════════════════════════════════════════════════
# MASTER RENDER SYSTEM — 100% JSON coverage, single universal renderer
# ═══════════════════════════════════════════════════════════════════════════════

def render_value(v, depth=0):
    """Render ANY JSON value — string/int/list/dict — to HTML. Zero data loss."""
    if v is None or v == '' or v == {} or v == []: return ''
    if isinstance(v, bool):
        return f'<span class="val-flag">{"Yes" if v else "No"}</span>'
    if isinstance(v, (int, float)):
        return f'<span>{esc(str(v))}</span>'
    if isinstance(v, str):
        v = v.strip()
        if not v: return ''
        # Strip HTML tags from jobs_info
        v = re.sub(r'<[^>]+>', ' ', v)
        v = re.sub(r'\s{2,}', ' ', v).strip()
        if not v: return ''
        if v.startswith('http'):
            sv = sanitize_url(v)
            if sv and not is_blocked(sv):
                lbl = sv[:60] + ('…' if len(sv) > 60 else '')
                return f'<a href="{esc(sv)}" class="inline-link" target="_blank" rel="noopener noreferrer">{esc(lbl)}</a>'
            return ''
        lines = [l.strip() for l in v.split('\n') if l.strip()]
        if len(lines) > 1:
            return ''.join(f'<p class="text-block">{esc(l)}</p>' for l in lines)
        return f'<p class="text-block">{esc(v)}</p>'
    if isinstance(v, list):
        if not v: return ''
        # List of dicts with keys → responsive table
        if any(isinstance(i, dict) and i for i in v):
            dicts = [i for i in v if isinstance(i, dict) and i]
            if dicts: return render_list_of_dicts_as_table(dicts)
        # Mixed list → ul
        items = []
        for item in v:
            r = render_value(item, depth+1)
            if r: items.append(f'<li>{r}</li>')
        return f'<ul class="data-list">{"".join(items)}</ul>' if items else ''
    if isinstance(v, dict):
        if not v: return ''
        if 'pattern_table' in v and isinstance(v['pattern_table'], list):
            other = {k: val for k, val in v.items() if k != 'pattern_table'}
            parts = []
            if other: parts.append(render_kv_table(other, depth))
            parts.append(render_list_of_dicts_as_table(v['pattern_table']))
            return ''.join(parts)
        return render_kv_table(v, depth)
    return esc(str(v))


def render_kv_table(d, depth=0):
    """Render dict as two-column key-value table."""
    if not d: return ''
    rows = ''
    for k, v in d.items():
        if v is None or v == '' or v == {} or v == []: continue
        kl = str(k).replace('_',' ').title()
        vr = render_value(v, depth+1)
        if not vr: continue
        rows += f'<tr><th>{esc(kl)}</th><td>{vr}</td></tr>'
    return f'<div class="table-scroll"><table class="info-table kv-table"><tbody>{rows}</tbody></table></div>' if rows else ''


def render_list_of_dicts_as_table(lst):
    """Render list-of-dicts as responsive multi-column table."""
    if not lst: return ''
    all_keys = []
    seen = set()
    for item in lst:
        if isinstance(item, dict):
            for k in item.keys():
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)
    if not all_keys: return ''
    ths = ''.join(f'<th>{esc(str(k))}</th>' for k in all_keys)
    rows = ''
    for item in lst:
        if not isinstance(item, dict): continue
        tds = ''
        for k in all_keys:
            v = item.get(k, '')
            cell = render_value(v) if v not in ('', None) else ''
            tds += f'<td>{cell}</td>'
        rows += f'<tr>{tds}</tr>'
    return f'<div class="table-scroll"><table class="info-table multi-col"><thead><tr>{ths}</tr></thead><tbody>{rows}</tbody></table></div>'


def render_tables(tables_data):
    """Render sarkari_data 'tables' key — list of {{table_name, rows}} with auto sub-table split."""
    if not tables_data or not isinstance(tables_data, list): return ''
    html = ''
    for tbl in tables_data:
        if not isinstance(tbl, dict): continue
        tname = tbl.get('table_name', '')
        rows  = tbl.get('rows', [])
        if not rows: continue
        if tname:
            html += f'<p class="table-note"><strong>{esc(tname)}</strong></p>'

        def looks_like_header(row, current_cols):
            if not row: return False
            if current_cols is not None and len(row) != current_cols: return True
            return all(not str(c).strip().isdigit() for c in row)

        sub_tables = []
        cur_hdr, cur_body, cur_cols = None, [], None
        for i, row in enumerate(rows):
            if i == 0:
                cur_hdr, cur_cols, cur_body = row, len(row), []
            elif looks_like_header(row, cur_cols):
                if cur_hdr is not None: sub_tables.append((cur_hdr, cur_body))
                cur_hdr, cur_cols, cur_body = row, len(row), []
            else:
                cur_body.append(row)
        if cur_hdr is not None: sub_tables.append((cur_hdr, cur_body))

        for (hdr, body) in sub_tables:
            if not hdr: continue
            ths = ''.join(f'<th>{esc(str(c))}</th>' for c in hdr)
            tbody_inner = ''
            for row in body:
                if not row: continue
                padded = list(row) + [''] * (len(hdr) - len(row))
                tds = ''.join(f'<td>{esc(str(c))}</td>' for c in padded[:len(hdr)])
                tbody_inner += f'<tr>{tds}</tr>'
            tbody = f'<tbody>{tbody_inner}</tbody>' if tbody_inner else ''
            html += f'<div class="table-scroll"><table class="info-table"><thead><tr>{ths}</tr></thead>{tbody}</table></div>'
    return html


def render_sarkari_sections(sections):
    """Render sarkari_data 'sections' array: paragraph/list/table content."""
    if not sections: return ''
    html = ''
    SKIP_TITLES = {'Set as Preferred Source on Google', 'Also Read :'}
    for sec in sections:
        title_s = sec.get('title', '').strip()
        if title_s in SKIP_TITLES: continue
        content_items = sec.get('content', [])
        if not content_items: continue
        body = ''
        for c in content_items:
            ctype = c.get('type', '')
            if ctype == 'paragraph':
                text = re.sub(r'<[^>]+>', ' ', c.get('text','')).strip()
                if text: body += f'<p class="text-block">{esc(text)}</p>'
            elif ctype == 'list':
                items = c.get('items', [])
                if isinstance(items, list):
                    lis = ''.join(f'<li>{esc(str(i))}</li>' for i in items if i)
                    if lis: body += f'<ul class="data-list">{lis}</ul>'
            elif ctype == 'table':
                rows_raw = c.get('rows', [])
                if rows_raw:
                    header = rows_raw[0] if rows_raw else []
                    data_rows = rows_raw[1:]
                    def cell_html(cell):
                        if isinstance(cell, dict):
                            t = esc(cell.get('text',''))
                            for lnk in cell.get('links', []):
                                url = lnk.get('url','') if isinstance(lnk, dict) else str(lnk)
                                sv = sanitize_url(url)
                                if sv and not is_blocked(sv):
                                    t += f' <a href="{esc(sv)}" class="inline-link" target="_blank" rel="noopener noreferrer">↗</a>'
                            return t
                        return esc(str(cell))
                    ths = ''.join(f'<th>{cell_html(c)}</th>' for c in header)
                    trs = ''.join(f'<tr>{"".join(f"<td>{cell_html(c)}</td>" for c in row)}</tr>' for row in data_rows)
                    body += f'<div class="table-scroll"><table class="info-table multi-col"><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table></div>'
        if body:
            sec_id = re.sub(r'[^a-z0-9]+', '-', title_s.lower()).strip('-')
            html += f'''
    <section class="job-card" id="sec-{sec_id}">
      <div class="job-card-head" style="background:linear-gradient(135deg,#334155,#1e293b)">
        <i class="fa-solid fa-file-lines"></i><h2>{esc(title_s)}</h2>
      </div>
      <div class="job-card-body">{body}</div>
    </section>'''
    return html


def render_important_links(job):
    """Render ALL clickable URLs from every link-related field."""
    LINK_MAP = {
        'apply_online':                ('Apply Online',             'btn-green',  'fa-pen-to-square'),
        'apply_online_link':           ('Apply Online',             'btn-green',  'fa-pen-to-square'),
        'login':                       ('Login / Apply',            'btn-green',  'fa-right-to-bracket'),
        'notification_pdf':            ('Download Notification',    'btn-blue',   'fa-file-pdf'),
        'official_notification_pdf':   ('Official Notification',    'btn-blue',   'fa-file-pdf'),
        'official_notification_pdf_link':('Official Notification',  'btn-blue',   'fa-file-pdf'),
        'official_website':            ('Official Website',         'btn-grey',   'fa-globe'),
        'official_website_link':       ('Official Website',         'btn-grey',   'fa-globe'),
        'result':                      ('View Result',              'btn-purple', 'fa-trophy'),
        'admit_card':                  ('Admit Card',               'btn-orange', 'fa-id-card'),
        'answer_key':                  ('Answer Key',               'btn-yellow', 'fa-key'),
        'form_pdf_link':               ('Application Form PDF',     'btn-blue',   'fa-file-pdf'),
        'form_pdf_free_link':          ('Free Application Form',    'btn-teal',   'fa-file-pdf'),
        'application_form_pdf_link':   ('Application Form',         'btn-blue',   'fa-file'),
        'click_here':                  ('Click Here',               'btn-grey',   'fa-arrow-up-right-from-square'),
    }
    seen_urls = set()
    html = ''

    def add_link(url, lbl, cls, ico):
        nonlocal html
        sv = sanitize_url(str(url or ''))
        if not sv or is_blocked(sv) or sv in seen_urls: return
        seen_urls.add(sv)
        html += f'<a href="{esc(sv)}" class="link-btn {cls}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ico}"></i> {lbl}</a>\n'

    # important_links dict
    il = job.get('important_links', {})
    if isinstance(il, dict):
        for k, v in il.items():
            lbl, cls, ico = LINK_MAP.get(k, ('Link', 'btn-grey', 'fa-link'))
            if k == 'click_here':
                if isinstance(v, list):
                    for u in v: add_link(u, lbl, cls, ico)
                elif isinstance(v, str): add_link(v, lbl, cls, ico)
            elif isinstance(v, str): add_link(v, lbl, cls, ico)
            elif isinstance(v, list):
                for u in v: add_link(u, lbl, cls, ico)

    # all_links [{label/title, url}]
    for lnk in job.get('all_links', []):
        if isinstance(lnk, dict):
            add_link(lnk.get('url',''), lnk.get('title') or lnk.get('label','Link'), 'btn-grey', 'fa-link')

    # useful_links [{title, links}]
    for lnk in job.get('useful_links', []):
        if isinstance(lnk, dict):
            add_link(lnk.get('links','') or lnk.get('url',''), lnk.get('title','Link'), 'btn-grey', 'fa-link')

    # Direct URL fields
    for field, (lbl, cls, ico) in LINK_MAP.items():
        if field in ('click_here',): continue
        url = job.get(field, '')
        if isinstance(url, str): add_link(url, lbl, cls, ico)

    # basic_details.official_website (pipe-separated)
    ow = job.get('official_website', '')
    if ow:
        for u in re.split(r'[\|,;\s]+', ow):
            u = u.strip()
            if u.startswith('http'): add_link(u, 'Official Website', 'btn-grey', 'fa-globe')

    if not html:
        html = '<p class="muted-note">Official notification ke liye upar di gayi information dekhein.</p>'
    return html


# render_section kept as alias for backward compat
def render_section(data):
    return render_value(data)

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

    # ── SEO helpers ─────────────────────────────────────────────────────────────
    def _extract_org(t):
        cut_rx = re.compile(r'\b(vacancy|vacancies|recruitment|notification|result|admit|answer|online\s*form|application|exam|test|interview)\b', re.IGNORECASE)
        words = t.split()
        cut = next((i for i,w in enumerate(words) if cut_rx.search(w)), None)
        part = (' '.join(words[:cut]) if cut and cut > 1 else ' '.join(words[:6])).rstrip(',').strip()
        return part if len(part) > 3 else 'Government of India'

    def _extract_state(t):
        STATE_MAP = {
            'haryana':'Haryana','rajasthan':'Rajasthan','uttar pradesh':'Uttar Pradesh',
            'bihar':'Bihar','madhya pradesh':'Madhya Pradesh','gujarat':'Gujarat',
            'maharashtra':'Maharashtra','karnataka':'Karnataka','tamilnadu':'Tamil Nadu',
            'tamil nadu':'Tamil Nadu','kerala':'Kerala','punjab':'Punjab','delhi':'Delhi',
            'odisha':'Odisha','jharkhand':'Jharkhand','assam':'Assam',
            'himachal pradesh':'Himachal Pradesh','uttarakhand':'Uttarakhand',
            'chhattisgarh':'Chhattisgarh','telangana':'Telangana',
            'andhra pradesh':'Andhra Pradesh','west bengal':'West Bengal',
            'tripura':'Tripura','manipur':'Manipur','meghalaya':'Meghalaya',
            'nagaland':'Nagaland','mizoram':'Mizoram','goa':'Goa',
            'arunachal':'Arunachal Pradesh','jammu':'Jammu & Kashmir',
        }
        tl = t.lower()
        for key, val in STATE_MAP.items():
            if key in tl: return val
        return 'India'

    def _build_desc(job, title, org, posts, last_date, short_info):
        parts = []
        if short_info:
            parts.append(short_info)
        else:
            parts.append(f'{org} ne {title} ke liye {posts} vacancies notify ki hain.')
        _dates = job.get('important_dates', {}) or {}
        if isinstance(_dates, dict):
            app_s = _dates.get('application_start') or _dates.get('Application Begin') or ''
            app_e = _dates.get('application_end') or _dates.get('Last Date Apply Online') or last_date
            if app_s: parts.append(f'Application start: {app_s}.')
            if app_e: parts.append(f'Last date: {app_e}.')
        _qual = job.get('qualification', {}) or {}
        q_txt = ''
        if isinstance(_qual, dict):
            q_txt = (_qual.get('education_qualification') or _qual.get('details') or '')[:120]
        elif isinstance(_qual, str):
            q_txt = _qual[:120]
        if not q_txt: q_txt = (job.get('eligibility') or '')[:120]
        if q_txt: parts.append(f'Eligibility: {q_txt}.')
        sal = (job.get('salary_pay_scale') or job.get('salary') or '')[:80]
        if sal: parts.append(f'Salary: {sal}.')
        _sp = job.get('selection_process', [])
        if isinstance(_sp, list) and _sp:
            parts.append(f'Selection: {chr(44).join(str(s) for s in _sp[:3])}.')
        elif isinstance(_sp, str) and _sp:
            parts.append(f'Selection: {_sp[:80]}.')
        desc = ' '.join(parts)
        if len(desc) < 200:
            desc += f' {title} ke liye official notification zaroor dekhein. Apply karne se pehle eligibility, age limit aur fee carefully check karein.'
        return desc[:500]

    # ── Build JobPosting schema ──────────────────────────────────────────────────
    _org_name     = (org if org and org != 'Government of India' else '') or _extract_org(title)
    _state        = _extract_state(title)
    _desc         = _build_desc(job, title, _org_name, posts, last_date, short_info)
    _raw_posted   = (job.get('notification_date') or job.get('last_updated') or job.get('listing_date') or '')
    _date_posted  = normalise_date(_raw_posted) or TODAY
    _valid_through = normalise_date(last_date) if last_date and last_date != 'See Notification' else ''

    job_schema = {
        '@context': 'https://schema.org', '@type': 'JobPosting',
        'title': title,
        'description': _desc,
        'datePosted': _date_posted,
        'employmentType': 'FULL_TIME',
        'url': canonical,
        'identifier': {'@type': 'PropertyValue', 'name': 'Top Sarkari Jobs', 'value': slug},
        'hiringOrganization': {'@type': 'Organization', 'name': _org_name, 'sameAs': 'https://www.india.gov.in'},
        'applicantLocationRequirements': {'@type': 'Country', 'name': 'India'},
        'jobLocation': {'@type': 'Place', 'address': {
            '@type': 'PostalAddress', 'addressCountry': 'IN',
            'addressRegion': _state, 'addressLocality': (_state if _state != 'India' else 'India')
        }},
        'author': {'@type': 'Organization', 'name': 'TopSarkariJobs Editorial Team', 'url': BASE_URL + '/about/'}
    }
    if _valid_through: job_schema['validThrough'] = _valid_through
    _vd = re.sub(r'[^0-9]', '', str(posts))
    if _vd and int(_vd) > 0: job_schema['totalJobOpenings'] = int(_vd)
    _sal_raw = str(job.get('salary_pay_scale') or job.get('salary') or '')
    _sal_m = re.search(r'\d[\d,]+', _sal_raw)
    if _sal_m:
        _sal_num = int(_sal_m.group().replace(',', ''))
        if _sal_num > 10000:
            job_schema['baseSalary'] = {
                '@type': 'MonetaryAmount', 'currency': 'INR',
                'value': {'@type': 'QuantitativeValue', 'value': _sal_num, 'unitText': 'MONTH'}
            }

    bc_schema = {
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': f'{BASE_URL}/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Latest Jobs', 'item': f'{BASE_URL}/section/latest-jobs/'},
            {'@type': 'ListItem', 'position': 3, 'name': title, 'item': canonical}
        ]
    }

    # FAQ: use JSON faq data if available, else auto-generate
    _json_faq = job.get('faq', [])
    if isinstance(_json_faq, list) and _json_faq:
        faq_items = [(esc(str(f.get('question',''))), esc(str(f.get('answer','')))) for f in _json_faq if f.get('question') and f.get('answer')]
        faq_items = faq_items[:6]  # max 6
    else:
        faq_items = []
    # Always ensure minimum 4 auto-generated FAQs are present
    auto_faq = [
        (f'{title} last date kya hai?', f'Last date: {last_date}. Official notification zaroor dekhein.'),
        (f'{title} ke liye eligibility kya hai?', 'Qualification ke liye official notification dekhein.'),
        (f'{title} mein total vacancies kitni hain?', f'Total {posts} posts hain.'),
        (f'{title} apply kaise karein?', f'{mode} mode mein apply karein. Official website par jakar form fill karein.'),
        (f'{org} ki official website kya hai?', 'Important Links section mein official website ka link diya gaya hai.'),
        (f'{title} ka selection process kya hai?', 'Written Test / Interview / Document Verification. Official notification dekhein.'),
    ]
    if len(faq_items) < 4:
        faq_items = auto_faq[:6]

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

    # ── Helper: render one card section ─────────────────────────────────────────
    def _card(sec_id, label, icon, color, body_html):
        return f'''
    <section class="job-card" id="{sec_id}">
      <div class="job-card-head" style="background:{color}">
        <i class="fa-solid {icon}"></i><h2>{label}</h2>
      </div>
      <div class="job-card-body">{body_html}</div>
    </section>'''

    # ══════════════════════════════════════════════════════
    # SECTION ORDER (matches your spec exactly):
    # 1  Hero            → rendered separately in <header>
    # 2  Short Info      → rendered inline below header
    # 3  Highlights      → auto-generated from key fields
    # 4  Important Dates
    # 5  Application Fee
    # 6  Age Limit
    # 7  Qualification
    # 8  Vacancy Details (SECTION_MAP + tables key)
    # 9  Selection Process
    # 10 Salary
    # 11 Exam Pattern
    # 12 Syllabus
    # 13 Physical Eligibility
    # 14 How To Apply
    # 15 Important Instructions
    # 16 Important Links  → rendered separately below
    # 17 FAQ              → rendered separately below
    # 18 SEO Content      → rendered separately below
    # ══════════════════════════════════════════════════════

    sections_html = ''

    # ── 3. Highlights (auto-generated from key fields) ───────────────────────
    _hi = []
    if posts and str(posts) not in ('', 'Various', 'None'):
        _hi.append(f'<li><i class="fa-solid fa-users" aria-hidden="true"></i> <strong>Total Posts:</strong> {esc(str(posts))}</li>')
    if last_date:
        _hi.append(f'<li><i class="fa-solid fa-calendar-days" aria-hidden="true"></i> <strong>Last Date:</strong> {esc(last_date)}</li>')
    if mode:
        _hi.append(f'<li><i class="fa-solid fa-computer" aria-hidden="true"></i> <strong>Apply Mode:</strong> {esc(mode)}</li>')
    _dept = job.get('post_name') or job.get('organization', '')
    if _dept:
        _hi.append(f'<li><i class="fa-solid fa-building" aria-hidden="true"></i> <strong>Department:</strong> {esc(str(_dept))}</li>')
    _loc = job.get('job_location', '')
    if _loc:
        _hi.append(f'<li><i class="fa-solid fa-location-dot" aria-hidden="true"></i> <strong>Location:</strong> {esc(str(_loc))}</li>')
    # Age from age_limit
    _age = job.get('age_limit', {})
    if isinstance(_age, dict):
        _age_str = _age.get('age_details') or _age.get('minimum_age') or ''
        if _age_str:
            _hi.append(f'<li><i class="fa-solid fa-user-clock" aria-hidden="true"></i> <strong>Age Limit:</strong> {esc(str(_age_str))}</li>')
    elif isinstance(_age, str) and _age.strip():
        _hi.append(f'<li><i class="fa-solid fa-user-clock" aria-hidden="true"></i> <strong>Age Limit:</strong> {esc(_age)}</li>')
    # Min/max age from sarkari_data format
    _minage = job.get('minimum_age', '')
    _maxage = job.get('maximum_age', '')
    if _minage and _maxage and not any('Age' in h for h in _hi):
        _hi.append(f'<li><i class="fa-solid fa-user-clock" aria-hidden="true"></i> <strong>Age:</strong> {esc(str(_minage))}–{esc(str(_maxage))} Years</li>')
    if _hi:
        sections_html += _card('highlights', 'Key Highlights', 'fa-star',
            'linear-gradient(135deg,#0891b2,#0e7490)',
            f'<ul class="highlights-list">{"".join(_hi)}</ul>')

    # ── 4. Important Dates ───────────────────────────────────────────────────
    _dates = job.get('important_dates', {})
    if _dates and isinstance(_dates, dict):
        _date_rows = ''.join(
            f"<tr><td>{esc(str(k).replace('_',' ').title())}</td><td><strong>{esc(str(v))}</strong></td></tr>"
            for k, v in _dates.items()
            if v and k not in ('events',) and not isinstance(v, (dict, list))
        )
        if _date_rows:
            sections_html += _card('important-dates', 'Important Dates', 'fa-calendar-days',
                'linear-gradient(135deg,#0f766e,#0d9488)',
                f'<div class="table-scroll"><table class="info-table"><tbody>{_date_rows}</tbody></table></div>')

    # ── 5–15. SECTION_MAP (in correct spec order) ────────────────────────────
    SECTION_MAP = [
        ('application_fee',       'Application Fee',        'fa-indian-rupee-sign', 'linear-gradient(135deg,#dc2626,#b91c1c)'),
        ('age_limit',             'Age Limit',              'fa-user-clock',        'linear-gradient(135deg,#7c3aed,#6d28d9)'),
        ('qualification',         'Qualification / Eligibility','fa-graduation-cap','linear-gradient(135deg,#0284c7,#0369a1)'),
        ('vacancy_details',       'Vacancy Details',        'fa-users',             'linear-gradient(135deg,#059669,#047857)'),
        ('category_wise_vacancy', 'Category Wise Vacancy',  'fa-table',             'linear-gradient(135deg,#047857,#065f46)'),
        ('selection_process',     'Selection Process',      'fa-list-check',        'linear-gradient(135deg,#4f46e5,#4338ca)'),
        ('salary_details',        'Salary / Pay Scale',     'fa-money-bill-wave',   'linear-gradient(135deg,#ca8a04,#a16207)'),
        ('exam_pattern',          'Exam Pattern',           'fa-file-alt',          'linear-gradient(135deg,#0e7490,#0891b2)'),
        ('syllabus',              'Syllabus',               'fa-book-open',         'linear-gradient(135deg,#16a34a,#15803d)'),
        ('physical_eligibility',  'Physical Eligibility',   'fa-person-running',    'linear-gradient(135deg,#b45309,#92400e)'),
        ('how_to_apply',          'How To Apply',           'fa-pen-to-square',     'linear-gradient(135deg,#1e40af,#1e3a8a)'),
        ('important_instructions','Important Instructions', 'fa-triangle-exclamation','linear-gradient(135deg,#e11d48,#be123c)'),
    ]
    for key, label, icon, color in SECTION_MAP:
        content = job.get(key)
        if not content: continue
        rendered = render_section(content)
        if not rendered: continue
        sections_html += _card(key.replace('_','-'), label, icon, color, rendered)

    # ── 8b. tables key (Vacancy & Eligibility — sarkari_data format) ─────────
    raw_tables = job.get('tables')
    if raw_tables:
        tables_rendered = render_tables(raw_tables)
        if tables_rendered:
            sections_html += _card('vacancy-eligibility', 'Vacancy &amp; Eligibility Details',
                'fa-users', 'linear-gradient(135deg,#059669,#047857)', tables_rendered)

    # ── 16b. sarkari 'sections' array (paragraph/list/table content) ─────────
    sections_html += render_sarkari_sections(job.get('sections', []))

    # ── 16c. text_sections [{section, content}] ──────────────────────────────
    for ts in job.get('text_sections', []):
        if not isinstance(ts, dict): continue
        ts_title = ts.get('section', '').strip()
        ts_body  = ts.get('content', '').strip()
        if ts_title and ts_body:
            ts_id = re.sub(r'[^a-z0-9]+', '-', ts_title.lower()).strip('-')
            rendered_body = render_value(ts_body)
            if rendered_body:
                sections_html += _card(f'ts-{ts_id}', ts_title,
                    'fa-file-lines', 'linear-gradient(135deg,#334155,#1e293b)', rendered_body)

    # ── 16d. notification_number / dept / selection_process_brief (meta) ─────
    _meta = {}
    if job.get('notification_number'): _meta['Notification Number'] = job['notification_number']
    if job.get('department'):          _meta['Department']           = job['department']
    if job.get('job_type'):            _meta['Job Type']             = job['job_type']
    if job.get('job_category'):        _meta['Job Category']         = job['job_category']
    if job.get('selection_process_brief'): _meta['Selection Brief']  = job['selection_process_brief']
    if _meta:
        meta_rows = ''.join(
            f'<tr><th>{esc(k)}</th><td>{esc(str(v))}</td></tr>'
            for k, v in _meta.items()
        )
        sections_html += _card('job-meta', 'Job Details', 'fa-circle-info',
            'linear-gradient(135deg,#0369a1,#0284c7)',
            f'<div class="table-scroll"><table class="info-table kv-table"><tbody>{meta_rows}</tbody></table></div>')

    # ── Important Links — ALL sources ────────────────────────────────────────
    links_html = render_important_links(job)

    # ── FAQ ───────────────────────────────────────────────────────────────────
    faq_items_render = []
    _json_faq = job.get('faq', [])
    if isinstance(_json_faq, list):
        for f in _json_faq:
            if isinstance(f, dict):
                q = str(f.get('question','')).strip()
                a = str(f.get('answer','')).strip()
                if q and a: faq_items_render.append((q, a))

    if len(faq_items_render) < 4:
        faq_items_render = [
            (f'{title} last date kya hai?', f'Last date: {last_date}. Official notification zaroor dekhein.'),
            (f'{title} ke liye eligibility kya hai?', 'Qualification ke liye official notification dekhein.'),
            (f'{title} mein total vacancies kitni hain?', f'Total {posts} posts hain.'),
            (f'{title} apply kaise karein?', f'{mode} mode mein apply karein. Official website par jakar form fill karein.'),
            (f'{org} ki official website kya hai?', 'Important Links section mein official website ka link diya gaya hai.'),
            (f'{title} ka selection process kya hai?', 'Written Test / Interview / Document Verification. Official notification dekhein.'),
        ]

    faq_html = '\n'.join(
        f'<div class="faq-item"><h3 class="faq-q"><i class="fa-solid fa-circle-question"></i> {esc(q)}</h3>'
        f'<div class="faq-a"><p>{esc(a)}</p></div></div>'
        for q, a in faq_items_render[:8]
        if q and a
    )

    # Update faq_schema with actual faq items
    faq_schema['mainEntity'] = [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
        for q, a in faq_items_render[:6]
    ]

    # SEO Content — 200-300 words auto-generated
    _sel = ''
    _sp = job.get('selection_process', [])
    if isinstance(_sp, list) and _sp:
        _sel = str(_sp[0])[:120]
    elif isinstance(_sp, str) and _sp:
        _sel = _sp[:120]
    _qual = ''
    _qd = job.get('qualification', {})
    if isinstance(_qd, dict):
        _qual = (_qd.get('education_qualification') or _qd.get('details') or '')[:120]
    elif isinstance(_qd, str):
        _qual = _qd[:120]

    seo_p1 = f"{org} ne {title} ke liye official notification jari kiya hai. Is recruitment drive mein kul {posts} posts ke liye eligible candidates se applications mangi gayi hain. Yeh ek sarkari naukri ka behad acha mauka hai. Interested candidates last date {last_date} se pehle apply karein."
    seo_p2 = f"Application {mode} mode mein ki ja sakti hai. {'Qualification: ' + _qual + '. ' if _qual else ''}Age limit aur category-wise relaxation ke liye official notification zaroor padhen. Application fee aur payment process ke liye upar di gayi jankari dekhein."
    seo_p3 = f"{'Selection process mein ' + _sel[:80] + ' shamil hai. ' if _sel else 'Selection process ke liye official notification dekhein. '}Salary, pay scale, aur job location ki puri jankari notification mein di gayi hai. Exam pattern aur syllabus ke liye official website visit karein."
    seo_p4 = f"{title} ke liye apply karne se pehle sabhi eligibility criteria, age limit, aur qualification carefully check karein. Important dates miss mat karein — application begin date aur last date ke beech hi apply possible hai. Agar koi doubt ho toh official website par jaayein ya helpline se contact karein."

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
  <meta property="og:image:width" content="1200"/>
  <meta property="og:image:height" content="630"/>
  <meta property="og:image:type" content="image/png"/>
  <meta property="article:published_time" content="{_date_posted}T00:00:00+05:30"/>
  <meta property="article:modified_time" content="{TODAY}T00:00:00+05:30"/>
  <meta property="article:section" content="Government Jobs"/>
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
  <style>
    /* ══ Vacancy Table: Multi-table horizontal scroll ══ */

    .table-scroll {{
      width: 100%;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      display: block;
      margin-bottom: 14px;
      border-radius: 8px;
      border: 1px solid #d1fae5;
    }}

    /* Table: let content set width → scroll triggers naturally */
    .table-scroll table.info-table {{
      border-collapse: collapse;
      font-size: 13.5px;
      table-layout: auto;
      /* Do NOT set width:100% — content determines width */
    }}

    /* Header */
    .table-scroll table.info-table thead tr {{
      background: linear-gradient(90deg, #059669 0%, #047857 100%);
      color: #fff;
    }}
    .table-scroll table.info-table thead th {{
      padding: 10px 14px;
      text-align: left;
      font-weight: 600;
      font-size: 13px;
      border: 1px solid rgba(255,255,255,0.2);
      white-space: nowrap;      /* headers never break */
    }}

    /* Body rows */
    .table-scroll table.info-table tbody tr:nth-child(odd)  {{ background: #fff; }}
    .table-scroll table.info-table tbody tr:nth-child(even) {{ background: #f0fdf4; }}
    .table-scroll table.info-table tbody tr:hover {{ background: #dcfce7; transition: background .15s; }}

    /* All body cells */
    .table-scroll table.info-table td {{
      padding: 9px 14px;
      border: 1px solid #d1fae5;
      vertical-align: middle;
      font-size: 13px;
      color: #1f2937;
      /* KEY: normal word wrap — words stay whole, no character split */
      white-space: normal;
      word-break: normal;
      overflow-wrap: break-word;
    }}

    /* First column: dept/post name — wider, left-aligned */
    .table-scroll table.info-table td:first-child {{
      font-weight: 500;
      min-width: 180px;
      max-width: 280px;
    }}

    /* Number/count columns (UR, OBC, SC, ST etc.) — narrow, centered */
    .table-scroll table.info-table td:not(:first-child) {{
      text-align: center;
      min-width: 52px;
      white-space: nowrap;
    }}

    /* Last column (Total / Eligibility) — can be wider */
    .table-scroll table.info-table td:last-child {{
      text-align: left;
      min-width: 80px;
      white-space: normal;
    }}

    /* Caption above each sub-table */
    .table-note {{
      font-size: 12.5px;
      font-weight: 600;
      color: #065f46;
      background: #ecfdf5;
      border-left: 4px solid #059669;
      padding: 9px 14px;
      margin: 10px 0 8px;
      border-radius: 0 6px 6px 0;
      line-height: 1.55;
    }}

    /* Highlights list */
    .highlights-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 8px;
    }}
    .highlights-list li {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13.5px;
      padding: 7px 10px;
      background: #f0fdf4;
      border-radius: 6px;
      border: 1px solid #d1fae5;
      color: #1f2937;
    }}
    .highlights-list li i {{ color: #059669; font-size: 14px; flex-shrink: 0; }}
    @media (max-width: 640px) {{
      .highlights-list {{ grid-template-columns: 1fr; }}
    }}
      .table-scroll {{
        box-shadow: inset -6px 0 10px -6px rgba(0,0,0,0.15);
      }}
      .table-scroll table.info-table {{ font-size: 12px; }}
      .table-scroll table.info-table td,
      .table-scroll table.info-table thead th {{ padding: 7px 10px; }}
      .table-scroll table.info-table td:first-child {{ min-width: 130px; max-width: 200px; }}
      .table-scroll table.info-table td:not(:first-child) {{ min-width: 42px; }}
    }}

    /* ══ Skeleton Loading — for homepage/section card lists ══ */
    .tsj-skeleton {{
      display: block;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: tsj-shimmer 1.4s infinite;
      border-radius: 6px;
    }}
    @keyframes tsj-shimmer {{
      0%   {{ background-position: 200% 0; }}
      100% {{ background-position: -200% 0; }}
    }}
    .tsj-skeleton-card {{
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
      padding: 14px 16px;
      margin-bottom: 10px;
    }}
    .tsj-skeleton-title  {{ height: 16px; width: 75%; margin-bottom: 10px; }}
    .tsj-skeleton-sub    {{ height: 12px; width: 50%; margin-bottom: 6px; }}
    .tsj-skeleton-badge  {{ height: 12px; width: 30%; }}
  </style>
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
          <p>{esc(seo_p4)}</p>
        </div>
      </section>
    </article>
  </div>
</main>
<div id="footer-placeholder"></div>
<script src="/tsj-menu.js" defer></script>
</body>
</html>'''

# ─── Data quality fixes ───────────────────────────────────────────────────────
def fix_job_record(job):
    title = job.get('title', '')
    if not job.get('organization'):
        cut_rx = re.compile(r'\b(vacancy|vacancies|recruitment|notification|result|online\s*form|application)\b', re.IGNORECASE)
        words = title.split()
        cut = next((i for i,w in enumerate(words) if cut_rx.search(w)), None)
        part = (' '.join(words[:cut]) if cut and cut > 1 else ' '.join(words[:6])).rstrip(',').strip()
        job['organization'] = part if len(part) > 3 else ''
    if not job.get('total_vacancies'):
        m = re.search(r'(\d[\d,]*)\s*(?:posts?|vacancies|vacancy|seats?)', title, re.IGNORECASE)
        if m: job['total_vacancies'] = m.group(1).replace(',', '')
    if job.get('entry_type') == 'NON_JOB':
        job_rx = re.compile(r'\b(vacancy|vacancies|recruitment|apply\s*online|online\s*form|application\s*form)\b', re.IGNORECASE)
        if job_rx.search(title): job['entry_type'] = 'JOB'
    return job

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
        all_jobs.append(fix_job_record(job))

    # 1. freejobalert_categories — ALL fields extracted
    fj_cats = cj.get('freejobalert_categories')
    if not fj_cats:
        OLD_CATS = {'10TH_Pass','8TH_Pass','12TH_Pass','Diploma','ITI','B_Tech_BE',
                    'B_Com','Any_Graduate','Any_Post_Graduate','Railway_Jobs',
                    'Police_Defence','Teaching_Faculty','Bank_Jobs','Medical_Hospital',
                    'Last_Date_Reminder','Latest_Notifications'}
        fj_cats = {k: v for k, v in cj.items() if k in OLD_CATS and isinstance(v, list)}

    for cat, jobs in fj_cats.items():
        if not isinstance(jobs, list): continue
        for job in jobs:
            bd = job.get('basic_details', {}) or {}
            title = bd.get('job_title', '').strip()
            if not title: continue
            dates = job.get('important_dates', {}) or {}
            last_date = (dates.get('last_date_to_apply') or dates.get('last_date') or
                         dates.get('Last Date to Apply') or dates.get('Last Date') or '')

            # ALL important_links — preserve full structure, only sanitize URLs
            raw_links = job.get('important_links', {}) or {}
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
                    elif isinstance(v, list):
                        filtered = [sanitize_url(u) for u in v if isinstance(u, str) and not is_blocked(u)]
                        filtered = [u for u in filtered if u]
                        if filtered: clean_links[k] = filtered

            add_job({
                # Identity
                'slug': slugify(title), 'title': title, 'source': 'freejobalert', 'category': cat,
                # basic_details — ALL 14 fields
                'organization':             bd.get('organization_name', ''),
                'department':               bd.get('department', ''),
                'post_name':                bd.get('post_name', ''),
                'total_vacancies':          str(bd.get('total_vacancies', '')),
                'notification_number':      bd.get('notification_number', ''),
                'application_mode':         bd.get('application_mode', 'Online'),
                'job_type':                 bd.get('job_type', ''),
                'job_category':             bd.get('job_category', ''),
                'job_location':             bd.get('job_location', ''),
                'official_website':         bd.get('official_website', ''),
                'short_info':               bd.get('short_information', ''),
                'last_updated':             bd.get('last_updated', ''),
                'selection_process_brief':  bd.get('selection_process_brief', ''),
                # Dates
                'last_date': last_date,
                'notification_date': dates.get('notification date') or bd.get('last_updated', ''),
                'important_dates': dates,
                # Content sections — COMPLETE, no truncation
                'application_fee':          job.get('application_fee', {}),
                'age_limit':                job.get('age_limit', {}),
                'qualification':            job.get('qualification', {}),
                'vacancy_details':          job.get('vacancy_details', []),
                'category_wise_vacancy':    job.get('category_wise_vacancy', {}),
                'salary_details':           job.get('salary_details', {}),
                'selection_process':        job.get('selection_process', []),
                'exam_pattern':             job.get('exam_pattern', {}),
                'syllabus':                 job.get('syllabus', {}),
                'physical_eligibility':     job.get('physical_eligibility', {}),
                'how_to_apply':             job.get('how_to_apply', []),
                'important_instructions':   job.get('important_instructions', []),
                'faq':                      job.get('faq', []),
                'seo_tags':                 job.get('seo_tags', []),
                # Links
                'important_links': clean_links,
                'all_links': [], 'useful_links': [],
                # Sarkari fields (empty for freejobalert)
                'tables': None, 'sections': [], 'text_sections': [],
                'jobs_info': '', 'salary_pay_scale': '',
                'minimum_age': '', 'maximum_age': '',
                'status': 'active', 'post_date': '',
            })

    # 2. sarkari_data — ALL fields extracted
    for job in cj.get('sarkari_data', {}).get('jobs', []):
        title = job.get('title', '').strip()
        if not title: continue

        # Merge ALL link sources
        raw_links = {}
        for field in ['apply_online_link', 'official_website_link', 'official_notification_pdf_link',
                      'form_pdf_link', 'form_pdf_free_link', 'application_form_pdf_link']:
            url = job.get(field, '')
            if url and not is_blocked(url):
                key = field.replace('_link','').replace('_pdf','')
                raw_links[key] = sanitize_url(url)
        il = job.get('important_links', {})
        if isinstance(il, dict):
            for k, v in il.items():
                if isinstance(v, str) and v.startswith('http') and not is_blocked(v):
                    raw_links.setdefault(k, sanitize_url(v))
                elif isinstance(v, list):
                    filtered = [sanitize_url(u) for u in v if isinstance(u, str) and not is_blocked(u)]
                    if filtered: raw_links.setdefault(k, filtered)

        imp_dates = job.get('important_dates', {}) or {}
        last_date = ''
        if isinstance(imp_dates, dict):
            last_date = (imp_dates.get('last_date') or imp_dates.get('Last Date') or
                         imp_dates.get('last_date_to_apply') or job.get('last_date',''))
        else:
            last_date = job.get('last_date', '')
            imp_dates = {}

        add_job({
            'slug': job.get('slug') or slugify(title), 'title': title,
            'source': 'sarkari', 'category': job.get('category', ''),
            # Identity
            'organization':         job.get('organization', ''),
            'department':           '',
            'post_name':            job.get('post_name', ''),
            'total_vacancies':      str(job.get('total_post') or job.get('total_vacancy') or ''),
            'notification_number':  '',
            'application_mode':     job.get('apply_mode', 'Online'),
            'job_type':             '',
            'job_category':         '',
            'job_location':         job.get('job_location', ''),
            'official_website':     job.get('official_website_link', ''),
            'short_info':           re.sub(r'<[^>]+>', ' ', str(job.get('short_information') or job.get('jobs_info') or '')).strip(),
            'last_updated':         job.get('listing_date', ''),
            'selection_process_brief': '',
            'last_date':            last_date,
            'notification_date':    '',
            'important_dates':      imp_dates,
            # Content
            'application_fee':      job.get('application_fee') or job.get('application_fees') or {},
            'age_limit':            job.get('age_limit', {}),
            'qualification':        job.get('eligibility') or {},
            'vacancy_details':      job.get('vacancy_details', []),
            'category_wise_vacancy':{},
            'salary_details':       {'pay_scale': job.get('salary_pay_scale','')} if job.get('salary_pay_scale') else {},
            'selection_process':    [],
            'exam_pattern':         {},
            'syllabus':             {},
            'physical_eligibility': {},
            'how_to_apply':         job.get('how_to_apply', []),
            'important_instructions': [],
            'faq':                  job.get('faq', []),
            'seo_tags':             [],
            # Links — ALL sources
            'important_links':      raw_links,
            'all_links':            job.get('all_links', []),
            'useful_links':         job.get('useful_links', []),
            # Sarkari-specific rich fields
            'tables':               job.get('tables'),
            'sections':             job.get('sections', []),
            'text_sections':        job.get('text_sections', []),
            'jobs_info':            job.get('jobs_info', ''),
            'salary_pay_scale':     job.get('salary_pay_scale', ''),
            'minimum_age':          str(job.get('minimum_age', '')),
            'maximum_age':          str(job.get('maximum_age', '')),
            'status':               job.get('status', 'active'),
            'post_date':            job.get('post_date', ''),
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
        # Include enough data so homepage JS renders cards WITHOUT extra fetches
        buckets[cat].append((
            normalise_date(job.get('last_date', '')),
            {
                'slug':  job['slug'],
                'name':  job['title'],
                'date':  job.get('last_date', ''),
                'org':   job.get('organization', ''),
                'vac':   str(job.get('total_vacancies', '') or ''),
                'mode':  job.get('application_mode', 'Online'),
                'status': job.get('status', 'active'),
            }
        ))
    result = {}
    for cat, items in buckets.items():
        # Preserve JSON insertion order — no date-based sorting
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

# FORCE_REGEN=1 or FORCE_REGENERATE=true → regenerate ALL existing pages
# GitHub Actions workflow passes FORCE_REGENERATE; CLI can use FORCE_REGEN=1
import os as _os
_fr1 = _os.environ.get('FORCE_REGEN', '0').strip() == '1'
_fr2 = _os.environ.get('FORCE_REGENERATE', 'false').strip().lower() in ('1', 'true', 'yes')
FORCE_REGEN = _fr1 or _fr2
if FORCE_REGEN:
    print("   ⚡ FORCE_REGEN — all existing pages will be regenerated")

for job in all_jobs:
    slug = job.get('slug', '')
    if not slug: continue

    out_dir  = JOBS_DIR / slug
    out_html = out_dir / 'index.html'
    out_json = DEST / f'{slug}.json'

    # Skip existing pages UNLESS force regen is set
    if out_html.exists() and not FORCE_REGEN:
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
