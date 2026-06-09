#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  UNIFIED MASTER GENERATOR — topsarkarijobs.com              ║
║  ONE script → ALL pages → ALL indexes                       ║
║  Run: python3 generate_all.py                               ║
╚══════════════════════════════════════════════════════════════╝

Sources : Complete_Jobs_Full_Data.json + dailyupdates.json
Output  : /jobs/ /state/ /education/ /category/study/
          /section/ /qualification/
          jobs-index.json  sections-index.json
"""

import json, re, os, html as _html, shutil
from datetime import date, datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────
ROOT     = Path('.')
# Prefer root Complete_Jobs_Full_Data.json (scraper output = source of truth for ordering)
# Fall back to data/ subdirectory if root not found
_root_cj = ROOT / 'Complete_Jobs_Full_Data.json'
_data_cj  = ROOT / 'data' / 'Complete_Jobs_Full_Data.json'
CJ_FILE   = _root_cj if _root_cj.exists() else _data_cj
DU_FILE  = ROOT / 'dailyupdates.json'
BASE_URL = 'https://www.topsarkarijobs.com'

# ── Garbage title filter (scraper navigation links) ──────────────────────────
GARBAGE_PATTERNS = [
    'about us','terms and conditions','contact us','privacy policy',
    'disclaimer','sitemap','advertise with us','sarkari result®','sarkarl result',
    'copyright','follow us','home page','back to top','whatsapp group',
    'telegram channel','youtube channel','facebook page','google news',
]

# ── Date parsing for sort ────────────────────────────────────────────────────
_MONTH_MAP = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
              'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}

def _parse_date_str(d):
    """Parse various date formats → comparable string YYYY-MM-DD for sort."""
    if not d: return '2000-01-01'
    d = str(d).strip().lower().split('(')[0].strip()  # remove trailing notes
    # DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', d)
    if m:
        try: return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        except: pass
    # DD Mon/Month YYYY
    m = re.match(r'(\d{1,2})\s+([a-z]+)\s+(\d{4})', d)
    if m:
        mon = _MONTH_MAP.get(m.group(2)[:3], 0)
        if mon: 
            try: return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
            except: pass
    # YYYY-MM-DD
    m = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', d)
    if m:
        try: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except: pass
    return '2000-01-01'

def _job_sort_key(job):
    """Sort key: last_date_to_apply DESC, then last_updated DESC."""
    imp = job.get('important_dates', {}) or {}
    bd  = job.get('basic_details', {}) or {}
    ld  = (imp.get('last_date_to_apply') or imp.get('last_date') or '').strip()
    lu  = (bd.get('last_updated') or '').strip()
    return (_parse_date_str(ld), _parse_date_str(lu))

def is_garbage_title(title):
    if not title or not title.strip(): return True
    tl = title.lower().strip()
    return any(p in tl for p in GARBAGE_PATTERNS)
TODAY    = date.today().isoformat()
YEAR     = date.today().year
from datetime import datetime as _dt_assetver
ASSET_VER = _dt_assetver.now().strftime('%Y%m%d%H%M%S')  # cache-bust query for shared JS
BLOCKED  = {'sarkariresult.com','freejobalert.com','sarkarinetwork.com','sarkariresultshine.com'}

# ── C1 FIX: Stable per-slug first-seen dates (datePosted must NOT be build-date) ──
_FIRST_SEEN_PATH = None  # set after ROOT is defined
_FIRST_SEEN = {}
_FIRST_SEEN_DIRTY = False

def _load_first_seen(root_path):
    global _FIRST_SEEN, _FIRST_SEEN_PATH
    import os as _os
    _FIRST_SEEN_PATH = _os.path.join(str(root_path), 'data', 'job-first-seen.json')
    try:
        with open(_FIRST_SEEN_PATH, encoding='utf-8') as f:
            _FIRST_SEEN = json.load(f)
    except Exception:
        _FIRST_SEEN = {}

def _save_first_seen():
    if not _FIRST_SEEN_DIRTY or not _FIRST_SEEN_PATH: return
    try:
        import os as _os
        _os.makedirs(_os.path.dirname(_FIRST_SEEN_PATH), exist_ok=True)
        with open(_FIRST_SEEN_PATH, 'w', encoding='utf-8') as f:
            json.dump(_FIRST_SEEN, f, ensure_ascii=False, separators=(',', ':'))
    except Exception:
        pass

def get_date_posted(slug, job_obj):
    """C1: Stable datePosted. Priority: real job date -> persisted first-seen -> today (saved)."""
    global _FIRST_SEEN_DIRTY
    dts = job_obj.get('important_dates', {}) or {}
    bd  = job_obj.get('basic_details', {}) or {}
    # normalize keys (handle 'date of advertisement' vs 'date_of_advertisement')
    def _norm_key(k): return re.sub(r'[^a-z0-9]+', '_', str(k).lower()).strip('_')
    merged = {}
    for src in (dts, bd):
        if isinstance(src, dict):
            for k, v in src.items():
                merged.setdefault(_norm_key(k), v)
    for k in ('post_date', 'date_of_advertisement', 'opening_of_online_registration_of_application',
              'start_date', 'application_begin', 'notification_date', 'date'):
        raw = merged.get(k)
        if raw:
            nd = norm_date(raw)
            if nd:
                return nd
    if slug in _FIRST_SEEN and _FIRST_SEEN[slug]:
        return _FIRST_SEEN[slug]
    _FIRST_SEEN[slug] = TODAY
    _FIRST_SEEN_DIRTY = True
    return TODAY

# ── C2 FIX: Page intent classifier (job vs result vs admit vs article/scheme) ──
import re as _re_intent
_RX_RESULT  = _re_intent.compile(r'\b(result|results|scorecard|score card|merit list|cut[\s-]?off|rank card|declared|revaluation|answer key|answer sheet)\b', _re_intent.I)
_RX_ADMIT   = _re_intent.compile(r'\b(admit card|hall ticket|call letter|exam date|date sheet|time table|exam city|slot booking)\b', _re_intent.I)
_RX_SCHEME  = _re_intent.compile(r'\b(yojana|yojna|scheme|pension|scholarship|card download|registration|kyc|certificate download|status check|apply link|e-?shram|pm[\s-]?kisan|samman|loan)\b', _re_intent.I)
_RX_JOB     = _re_intent.compile(r'\b(recruitment|vacancy|vacancies|online form|apply online|posts|notification|bharti|engagement|walk[\s-]?in|hiring|appointment)\b', _re_intent.I)

def page_intent(job_obj):
    """Return one of: job | result | admitcard | scheme | article"""
    bd = job_obj.get('basic_details', {}) or {}
    title = str(bd.get('job_title','') or job_obj.get('title','') or '')
    cat   = str(job_obj.get('category','') or '')
    blob  = (title + ' ' + cat).lower()
    # vacancy_details / salary presence strongly indicates a real job
    has_vacancy = bool(job_obj.get('vacancy_details') or job_obj.get('category_wise_vacancy'))
    if _RX_RESULT.search(blob) and not _RX_JOB.search(blob):
        return 'result'
    if _RX_ADMIT.search(blob) and not _RX_JOB.search(blob):
        return 'admitcard'
    if _RX_JOB.search(blob) or has_vacancy:
        return 'job'
    if _RX_SCHEME.search(blob):
        return 'scheme'
    return 'article'

# ── Qualification maps ────────────────────────────────────────
QUAL_SLUG = {
    '10TH_Pass':'10th-pass','8TH_Pass':'8th-pass','12TH_Pass':'12th-pass',
    '4th_Pass':'4th-pass','5th_Pass':'5th-pass','6th_Pass':'6th-pass',
    '7th_Pass':'7th-pass','9th_Pass':'9th-pass','Intermediate':'intermediate',
    'Diploma':'diploma','ITI':'iti','B_Tech_BE':'b-tech-be','B_Com':'b-com',
    'Any_Graduate':'any-graduate','Any_Post_Graduate':'any-post-graduate',
    'Railway_Jobs':'railway-jobs','Police_Defence':'police-defence',
    'Teaching_Faculty':'teaching-faculty','Bank_Jobs':'bank-jobs',
    'Medical_Hospital':'medical-hospital','Latest_Notifications':'latest-jobs',
    'Last_Date_Reminder':'last-date-reminder',
    'GNM':'gnm','ANM':'anm','D_Pharm':'d-pharm','DMLT':'dmlt',
    'D_El_Ed':'d-el-ed','D_P_Ed':'d-p-ed','B_Sc':'b-sc','BCA':'bca',
    'MA':'ma','BBA':'bba','LLB':'llb','B_Ed':'b-ed','MBBS':'mbbs',
    'B_Pharma':'b-pharma','BAMS':'bams','BDS':'bds','M_Sc':'m-sc',
    'M_Com':'m-com','M_Ed':'m-ed','M_A':'m-a','M_E_MTech':'me-mtech',
    'MCA':'mca','MBA_PGDM':'mba-pgdm','MS_MD':'ms-md','M_Pharma':'m-pharma',
    'CA':'ca','CS':'cs','ICWA':'icwa','MPhil_PhD':'mphil-phd',
    'VHSE':'vhse','DLT':'dlt',
}
QUAL_LABEL = {
    '10TH_Pass':'10th Pass','8TH_Pass':'8th Pass','12TH_Pass':'12th Pass',
    'Intermediate':'Intermediate','Diploma':'Diploma','ITI':'ITI',
    'B_Tech_BE':'B.Tech / BE','B_Com':'B.Com','Any_Graduate':'Any Graduate',
    'Any_Post_Graduate':'Any PG','Railway_Jobs':'Railway Jobs',
    'Police_Defence':'Police / Defence','Teaching_Faculty':'Teaching / Faculty',
    'Bank_Jobs':'Bank Jobs','Medical_Hospital':'Medical / Hospital',
    'Latest_Notifications':'Latest Jobs','Last_Date_Reminder':'Last Date Reminder',
    'GNM':'GNM','ANM':'ANM','MBBS':'MBBS','BDS':'BDS','BCA':'BCA',
    'MCA':'MCA','MBA_PGDM':'MBA / PGDM','LLB':'LLB','CA':'CA','CS':'CS',
    'VHSE':'VHSE','DLT':'DLT',
}
# N6: Qualification priority for breadcrumb selection
QUAL_PRIORITY_MAP = {
    'mphil-phd':1,'any-post-graduate':2,'m-sc':2,'m-com':2,'m-ed':2,'m-a':2,
    'me-mtech':2,'ms-md':2,'mca':2,'mba-pgdm':2,'m-pharma':2,
    'mbbs':3,'bds':3,'bams':3,'b-pharma':3,'b-sc':3,'b-tech-be':3,
    'b-com':3,'bca':3,'bba':3,'llb':3,'b-ed':3,'ca':3,'cs':3,
    'any-graduate':4,'intermediate':5,'diploma':6,'iti':7,
    '12th-pass':8,'10th-pass':9,'8th-pass':10,
    'latest-jobs':50,'latest-notifications':50,'bank-jobs':50,
    'railway-jobs':50,'police-defence':50,'teaching-faculty':50,
    'medical-hospital':50,'last-date-reminder':50,
}

def get_best_bc_category(cat, job_obj=None):
    """Return (label, url) for breadcrumb — highest qualification wins."""
    cat_slug = QUAL_SLUG.get(cat, cat.lower().replace('_','-'))
    cat_label = QUAL_LABEL.get(cat, cat.replace('_',' ').title())
    best_priority = QUAL_PRIORITY_MAP.get(cat_slug, 99)
    best_slug = cat_slug
    best_label = cat_label

    # Check if job is in multiple categories — use highest qualification
    if job_obj:
        job_cats = job_obj.get('categories') or []
        for jc in job_cats:
            jc_slug = QUAL_SLUG.get(jc, jc.lower().replace('_','-'))
            jc_priority = QUAL_PRIORITY_MAP.get(jc_slug, 99)
            if jc_priority < best_priority:
                best_priority = jc_priority
                best_slug = jc_slug
                best_label = QUAL_LABEL.get(jc, jc.replace('_',' ').title())

    return (f"{best_label} Jobs", f"/category/study/{best_slug}/")



# ── Helpers ───────────────────────────────────────────────────
def e(s): return _html.escape(str(s or ''), quote=True)

def strip_html(text):
    if not text: return ''
    t = str(text)
    t = re.sub(r'<[^>]+>', ' ', t)
    for ent, ch in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&nbsp;',' '),('&quot;','"'),('&#39;',"'")]:
        t = t.replace(ent, ch)
    return ' '.join(t.split())

def safe(v):
    if v is None: return ''
    if isinstance(v, str):
        s = v.strip()
        return strip_html(s) if ('<' in s and '>' in s) else s
    if isinstance(v, (int, float, bool)): return str(v).strip()
    if isinstance(v, list):
        parts = [safe(x) for x in v if x is not None]
        return ', '.join(p for p in parts if p)
    if isinstance(v, dict):
        for k in ['text','value','name','description','details','pay_scale','salary','title']:
            if isinstance(v.get(k), str) and v[k].strip(): return strip_html(v[k].strip())
        return ' | '.join(safe(val) for val in v.values() if val)
    return str(v).strip()

def slugify(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text[:80].strip('-') or 'page'

def clean_slug(s):
    s = str(s or '').strip()
    s = re.sub(r'^sr_[a-z_]+-', '', s)
    s = re.sub(r'-[0-9a-f]{6,8}$', '', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:80] or ''

def is_blocked(url):
    return any(d in str(url).lower() for d in BLOCKED)

def key_label(key):
    label = str(key).replace('_',' ').replace('-',' ')
    label = re.sub(r'\b([a-z])', lambda m: m.group(1).upper(), label)
    for k,v in {'Url':'URL','Pdf':'PDF','Obc':'OBC','Sc':'SC','St':'ST','Ur':'UR','Ews':'EWS','Pwd':'PwD','Cbt':'CBT'}.items():
        label = re.sub(r'\b'+k+r'\b', v, label)
    return label

def norm_date(raw):
    if not raw: return None
    raw = str(raw).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw): return raw
    months = dict(jan=1,feb=2,mar=3,apr=4,may=5,jun=6,jul=7,aug=8,sep=9,oct=10,nov=11,dec=12)
    m1 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', raw)
    if m1: return f"{m1.group(3)}-{int(m1.group(2)):02d}-{int(m1.group(1)):02d}"
    m2 = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', raw)
    if m2:
        mo = months.get(m2.group(2)[:3].lower())
        if mo: return f"{m2.group(3)}-{mo:02d}-{int(m2.group(1)):02d}"
    return None

written = 0
def write(path, html_content):
    global written
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(html_content)
    written += 1

# ── Cell extractor (handles {text, links} format) ─────────────
def extract_cell(cell):
    if cell is None: return '', False
    if isinstance(cell, str): return e(cell), False
    if isinstance(cell, (int, float)): return e(str(cell)), False
    if isinstance(cell, dict):
        text = str(cell.get('text','') or cell.get('value','') or '').strip()
        links = cell.get('links', []) or []
        if isinstance(links, list) and links:
            btns = ''
            for lnk in links:
                if not isinstance(lnk, dict): continue
                url = str(lnk.get('url','') or '').strip()
                lbl = str(lnk.get('text','') or lnk.get('label','') or text or 'View').strip()
                if not url or not url.startswith('http') or is_blocked(url): continue
                ul = url.lower()
                ic = 'fa-file-pdf' if ul.endswith('.pdf') else 'fa-arrow-up-right-from-square'
                cl = 'btn-pdf' if ul.endswith('.pdf') else 'btn-default'
                btns += f'<a href="{e(url)}" class="lnk-btn {cl}" style="font-size:.73rem;padding:3px 9px" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ic}"></i> {e(lbl[:40])}</a> '
            if btns:
                return (f'{e(text)}<br>{btns}' if text else btns), True
        return e(text), False
    if isinstance(cell, list):
        parts = [extract_cell(c)[0] for c in cell if c is not None]
        return '<br>'.join(p for p in parts if p), False
    return e(str(cell)), False

# ── Smart table renderer ──────────────────────────────────────
def render_smart_table(rows):
    if not rows: return ''
    valid = [r for r in rows if isinstance(r, (list, tuple)) and r]
    if not valid: return ''
    # Skip single-cell rows at top (section title rows)
    while valid and len(valid[0]) == 1:
        valid = valid[1:]
    if not valid: return ''
    head_row = valid[0]
    data_rows = valid[1:]
    ncol = len(head_row)
    head = ''.join(f'<th>{extract_cell(h)[0]}</th>' for h in head_row)
    # Normalize ragged rows: a row with fewer cells than the header (very common in
    # scraped notification tables where section-title / long-text rows have a single
    # cell) would otherwise collapse the whole table's column widths. Make a short row
    # span all columns with colspan, and pad rows that are only slightly short.
    body_parts = []
    for r in data_rows:
        if not r: continue
        cells = list(r)
        if len(cells) == 1 and ncol > 1:
            # full-width separator / long-text row
            body_parts.append(f'<tr><td colspan="{ncol}">{extract_cell(cells[0])[0]}</td></tr>')
        else:
            tds = ''.join(f'<td>{extract_cell(c)[0]}</td>' for c in cells[:ncol])
            # pad if this row is shorter than the header (keeps columns aligned)
            if len(cells) < ncol:
                tds += '<td></td>' * (ncol - len(cells))
            body_parts.append(f'<tr>{tds}</tr>')
    body = ''.join(body_parts)
    if not body: return ''
    return f'<div class="tbl-scroll"><table class="data-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'

# ── Section card builder ──────────────────────────────────────
SECTION_META = {
    'basic_details':        ('Job Overview',              'fa-circle-info',        '1e40af,#3b82f6'),
    'important_dates':      ('Important Dates',           'fa-calendar-check',     'b91c1c,#dc2626'),
    'application_fee':      ('Application Fee',           'fa-indian-rupee-sign',  'c2410c,#ea580c'),
    'age_limit':            ('Age Limit',                 'fa-user-clock',         '0f766e,#0891b2'),
    'qualification':        ('Qualification / Eligibility','fa-graduation-cap',    '4338ca,#6366f1'),
    'vacancy_details':      ('Vacancy Details',           'fa-chart-pie',          '15803d,#16a34a'),
    'category_wise_vacancy':('Category-wise Vacancy',     'fa-chart-bar',          '15803d,#16a34a'),
    'salary_details':       ('Salary & Pay Scale',        'fa-indian-rupee-sign',  '15803d,#16a34a'),
    'selection_process':    ('Selection Process',         'fa-list-check',         '5b21b6,#7c3aed'),
    'exam_pattern':         ('Exam Pattern',              'fa-file-lines',         '0369a1,#0284c7'),
    'syllabus':             ('Syllabus',                  'fa-book',               '4338ca,#6366f1'),
    'physical_eligibility': ('Physical Eligibility',      'fa-dumbbell',           'be123c,#e11d48'),
    'how_to_apply':         ('How to Apply',              'fa-clipboard-list',     '0f766e,#0891b2'),
    'important_instructions':('Important Instructions',   'fa-circle-exclamation', 'b45309,#ca8a04'),
    'important_links':      ('Important Links',           'fa-link',               '1e40af,#1e3a8a'),
    'faq':                  ('FAQs',                      'fa-circle-question',    '4338ca,#6366f1'),
    'tables':               ('Details',                   'fa-table',              '0f766e,#0891b2'),
    'all_links':            ('Useful Links',              'fa-link',               '1d4ed8,#1e3a8a'),
    'details_page_content': ('Scholarship Details',       'fa-circle-info',        '1e40af,#3b82f6'),
    'text_sections':        ('How to Apply',              'fa-clipboard-list',     '0f766e,#0891b2'),
    'useful_links':         ('Useful Links',              'fa-link',               '1d4ed8,#1e3a8a'),
    'sections':             ('Details',                   'fa-circle-info',        '1e40af,#3b82f6'),
}

def sec_card(key_or_title, icon, grad, body):
    if not body or not str(body).strip(): return ''
    meta = SECTION_META.get(key_or_title)
    title = meta[0] if meta else (key_or_title if isinstance(key_or_title, str) else key_label(key_or_title))
    return (f'<section class="sec-card">'
            f'<div class="sec-head" style="background:linear-gradient(135deg,#{grad})">'
            f'<i class="fa-solid {icon}"></i><h2>{e(title)}</h2></div>'
            f'<div class="sec-body">{body}</div></section>\n')

# ── Renderers ─────────────────────────────────────────────────

def render_basic_details(bd):
    if not bd or not isinstance(bd, dict): return ''
    SKIP = {'job_title','short_information'}
    PRIO = ['organization_name','post_name','total_vacancies','application_mode',
            'job_location','job_type','notification_number','advt_no','official_website','last_updated']
    rows = ''
    done = set(SKIP)
    for k in PRIO:
        v = safe(bd.get(k,''))
        if not v or k in done: continue
        done.add(k)
        rows += f'<tr><th>{e(key_label(k))}</th><td>{e(v)}</td></tr>'
    for k, v in bd.items():
        if k in done: continue
        sv = safe(v)
        if not sv: continue
        done.add(k)
        rows += f'<tr><th>{e(key_label(k))}</th><td>{e(sv)}</td></tr>'
    si = safe(bd.get('short_information',''))
    si_html = f'<div class="short-info"><i class="fa-solid fa-circle-info"></i> {e(si)}</div>' if si else ''
    return si_html + (f'<table class="kv-table"><tbody>{rows}</tbody></table>' if rows else '')

def render_dates(obj):
    if not obj or not isinstance(obj, dict): return ''
    PRIO = ['application_start_date','application_begin','start_date','date_of_notification',
            'notification_date','last_date_to_apply','last_date','application_last_date',
            'fee_payment_last_date','exam_date','written_exam_date','online_exam_date',
            'omr_exam_date','interview_date','admit_card_date','result_date','event',
            'आवेदन शुरू','अंतिम तिथि','परीक्षा तिथि','महत्वपूर्ण तिथि','अधिसूचना']
    rows = ''; seen = set()
    for k in PRIO:
        v = safe(obj.get(k,''))
        lbl = key_label(k)
        if not v or lbl in seen: continue
        seen.add(lbl)
        is_last = bool(re.search(r'last|closing|अंतिम', k, re.I))
        cls = ' class="date-last"' if is_last else ''
        rows += f'<tr><th scope="row"><i class="fa-regular fa-calendar"></i> {e(lbl)}</th><td{cls}>{e(v)}</td></tr>'
    for k, v in obj.items():
        lbl = key_label(k); sv = safe(v)
        if not sv or lbl in seen: continue
        seen.add(lbl)
        rows += f'<tr><th scope="row"><i class="fa-regular fa-calendar"></i> {e(lbl)}</th><td>{e(sv)}</td></tr>'
    return f'<table class="kv-table"><tbody>{rows}</tbody></table>' if rows else ''

def render_fee(obj):
    if not obj or not isinstance(obj, dict): return ''
    FEE_KEYS = [('general_fee','General/UR'),('general','General/UR'),('ur','UR'),
                ('obc_fee','OBC'),('obc','OBC'),('sc_fee','SC'),('sc','SC'),
                ('st_fee','ST'),('st','ST'),('ews','EWS'),('pwd_fee','PwD'),
                ('pwd','PwD'),('ph','PwD'),('female_fee','Female'),('female','Female'),
                ('ex_serviceman_fee','Ex-Serviceman'),('all','All Categories')]
    seen = set(); items = ''
    def is_free(v): return bool(re.search(r'nil|^0$|free|no fee|exempt|शून्य', str(v), re.I))
    for key, lbl in FEE_KEYS:
        v = safe(obj.get(key,''))
        if not v or lbl in seen: continue
        seen.add(lbl)
        cls = 'fee-free' if is_free(v) else 'fee-paid'
        items += f'<div class="fee-cell"><span class="fee-cat">{e(lbl)}</span><span class="fee-amt {cls}">{e(v)}</span></div>'
    for k, v in obj.items():
        if k in {'details','fee_mode','payment_mode'}: continue
        lbl = key_label(k); sv = safe(v)
        if not sv or lbl in seen: continue
        seen.add(lbl)
        items += f'<div class="fee-cell"><span class="fee-cat">{e(lbl)}</span><span class="fee-amt">{e(sv)}</span></div>'
    note = ' | '.join(safe(obj.get(k,'')) for k in ['details','fee_mode','payment_mode'] if safe(obj.get(k,'')))
    body = (f'<div class="fee-grid">{items}</div>' if items else '') + \
           (f'<div class="fee-note"><i class="fa-solid fa-circle-info"></i> {e(note)}</div>' if note else '')
    return body

# ── C4 FIX: strip navigation/footer/tool/city-jobs pollution from section lists ──
_POLLUTION_RX = [
    re.compile(r'\bjobs?\s*\(\d+\)', re.I),                       # "Hyderabad Jobs (435)"
    re.compile(r'\b(pdf|word|image)\s+to\s+(word|pdf|image)\b', re.I),
    re.compile(r'\b(image\s+resizer|free\s+mock\s+test|free\s+ai|ai\s+interview|games?)\b', re.I),
    re.compile(r'\b(online\s+form\s+2026|admit\s+card\s+2026\s*-\s*out|result\s+2026\s*-\s*out)\b', re.I),
    re.compile(r'\b(privacy\s+policy|terms|disclaimer|contact\s+us|about\s+us|sitemap|advertise)\b', re.I),
    re.compile(r'\b(follow\s+us|whatsapp|telegram\s+channel|youtube\s+channel|facebook\s+page|google\s+news)\b', re.I),
]
_POLLUTION_EXACT = {
    'education','games','sarkari job','sarkari naukri','sarkari result','admit card',
    'exam results','answer key','cutoff marks','written marks','interview results',
    'last date reminder','eligibility','syllabus','exam pattern','selection process',
    'previous papers','image resizer','free mock test','anganwadi recruitment',
    'forest jobs','search jobs','employment news','latest notifications',
    '10th jobs','8th jobs','12th jobs','diploma jobs','iti jobs','ba jobs','ma jobs',
    'b.com jobs','mba jobs','msw jobs','b.sc jobs','m.sc jobs','b.tech/b.e jobs',
    'any graduate jobs','any post graduate jobs','pdf to word converter',
    'image to pdf converter','word to pdf converter','free ai interview tool',
}

def _clean_section_items(items):
    """Remove menu/footer/tool/city/other-job pollution that bled into section arrays."""
    out = []
    for s in items:
        if not s: continue
        t = str(s).strip()
        tl = t.lower().strip(' .:')
        if tl in _POLLUTION_EXACT:
            continue
        if any(rx.search(t) for rx in _POLLUTION_RX):
            continue
        # very short menu-like single tokens (no sentence) are likely nav labels
        if len(t) <= 3:
            continue
        out.append(t)
    # de-dup preserving order
    seen = set(); ded = []
    for x in out:
        k = x.lower()
        if k in seen: continue
        seen.add(k); ded.append(x)
    return ded

def render_list_items(items, ordered=False):
    filtered = [safe(s) for s in (items if isinstance(items, list) else [str(items)]) if safe(s)]
    filtered = _clean_section_items(filtered)
    if not filtered: return ''
    tag = 'ol' if ordered else 'ul'
    return f'<{tag} class="val-list">' + ''.join(f'<li>{e(s)}</li>' for s in filtered) + f'</{tag}>'

def render_selection(sp):
    if not sp: return ''
    if isinstance(sp, str): sp = [s.strip() for s in re.split(r'[,\n;/→]', sp) if s.strip()]
    steps = [safe(s) for s in sp if safe(s)]
    steps = _clean_section_items(steps)[:25]   # C4: cap + clean
    if not steps: return ''
    return '<div class="sel-steps">' + ''.join(
        f'<div class="sel-step"><span class="sel-num">{i+1}</span>{e(s[:140])}</div>'
        for i, s in enumerate(steps)
    ) + '</div>'

def render_hta(steps):
    if not steps: return ''
    if isinstance(steps, str): steps = [s.strip() for s in steps.split('\n') if s.strip()]
    filtered = [safe(s) for s in steps if safe(s)]
    filtered = _clean_section_items(filtered)[:25]   # C4: cap + clean
    if not filtered: return ''
    items = ''.join(f'<li class="hta-item"><span class="hta-num">{i+1}</span><span>{e(s)}</span></li>'
                    for i, s in enumerate(filtered))
    return f'<ul class="hta-list">{items}</ul>'

def render_links(il_obj):
    if not il_obj or not isinstance(il_obj, dict): return ''
    LINK_CFG = {
        'apply_online':         ('Apply Online',          'btn-apply',   'fa-paper-plane'),
        'official_website':     ('Official Website',      'btn-official','fa-globe'),
        'notification_pdf':     ('Download Notification', 'btn-pdf',     'fa-file-pdf'),
        'download_notification':('Download Notification', 'btn-pdf',     'fa-file-pdf'),
        'official_notification':('Official Notification', 'btn-pdf',     'fa-file-pdf'),
        'application_form':     ('Download Application Form', 'btn-pdf', 'fa-file-pdf'),
        'registration_link':    ('Register Now',          'btn-register','fa-user-plus'),
        'login_link':           ('Login',                 'btn-login',   'fa-right-to-bracket'),
        'admit_card':           ('Admit Card',            'btn-admit',   'fa-id-card'),
        'answer_key':           ('Answer Key',            'btn-answer',  'fa-key'),
        'syllabus_pdf':         ('Syllabus PDF',          'btn-syllabus','fa-book'),
        'result_link':          ('Result',                'btn-result',  'fa-trophy'),
        'click_here':           ('Click Here',            'btn-default', 'fa-link'),
        'merit_list':           ('Merit List',            'btn-merit',   'fa-list'),
    }
    buttons = ''; seen = set()
    for key, val in il_obj.items():
        if key in ('structured_links','seo_tags'): continue
        urls = val if isinstance(val, list) else [val]
        label, css, icon = LINK_CFG.get(key, (key_label(key), 'btn-default', 'fa-link'))
        for url in urls:
            u = str(url or '').strip()
            if not u.startswith('http') or is_blocked(u) or u in seen: continue
            seen.add(u)
            ul = u.lower()
            if ul.endswith('.pdf'): icon, css = 'fa-file-pdf', 'btn-pdf'
            elif 'apply' in key: icon, css = 'fa-paper-plane', 'btn-apply'
            elif 'result' in key: icon, css = 'fa-trophy', 'btn-result'
            elif 'admit' in key: icon, css = 'fa-id-card', 'btn-admit'
            elif 'answer' in key: icon, css = 'fa-key', 'btn-answer'
            dl = ' download' if ul.endswith('.pdf') else ''
            buttons += f'<a href="{e(u)}" class="lnk-btn {css}" target="_blank" rel="noopener noreferrer"{dl}><i class="fa-solid {icon}"></i> {e(label)}</a>\n'
    for item in (il_obj.get('structured_links') or []):
        if not isinstance(item, dict): continue
        u = str(item.get('url','') or item.get('href','')).strip()
        lbl = str(item.get('label','') or item.get('title','View')).strip() or 'View'
        if not u.startswith('http') or is_blocked(u) or u in seen: continue
        seen.add(u)
        ll = lbl.lower()
        ic,cl = ('fa-paper-plane','btn-apply') if 'apply' in ll else \
                ('fa-trophy','btn-result') if 'result' in ll else \
                ('fa-id-card','btn-admit') if 'admit' in ll else \
                ('fa-key','btn-answer') if 'answer' in ll else \
                ('fa-file-pdf','btn-pdf') if u.endswith('.pdf') else \
                ('fa-globe','btn-official') if 'official' in ll else ('fa-link','btn-default')
        dl = ' download' if u.lower().endswith('.pdf') else ''
        buttons += f'<a href="{e(u)}" class="lnk-btn {cl}" target="_blank" rel="noopener noreferrer"{dl}><i class="fa-solid {ic}"></i> {e(lbl[:55])}</a>\n'
    return f'<div class="links-grid">{buttons}</div>' if buttons else ''

def render_faq(faq_list):
    if not isinstance(faq_list, list) or not faq_list: return ''
    items = ''
    seen = set()
    idx = 0
    for f in faq_list:
        if not isinstance(f, dict): continue
        q = safe(f.get('question','')); a = safe(f.get('answer',''))
        if not q or not a: continue
        # strip any pre-existing "Q1." / "Q12)" / "1." numbering from the question text
        # (renderer adds its own Q{n} badge, so leaving it causes "Q1 Q1." double numbering)
        q = re.sub(r'^\s*Q?\s*\d{1,3}\s*[\.\):\-]\s*', '', q, flags=re.I).strip()
        # de-duplicate by normalized question text
        key = re.sub(r'\s+', ' ', q.lower()).strip()
        if not key or key in seen: continue
        seen.add(key)
        idx += 1
        items += (f'<div class="faq-item" id="faq-{idx}">'
                  f'<div class="faq-q"><span class="faq-icon">Q{idx}</span><span>{e(q)}</span></div>'
                  f'<div class="faq-a"><span class="faq-icon" style="background:#15803d">A</span><div>{e(a)}</div></div></div>')
    return items

def render_vacancy_table(vac_list):
    if not vac_list or not isinstance(vac_list, list): return ''
    ALL_COLS = [
        ('post_name',['post_name','post','name','Post Name','Name Of Post','Post']),
        ('state',['State / UT','State/UT','state','State','State / Ut']),
        ('language',['Language','language','Medium','medium']),
        ('total',['total','total_vacancies','total_posts','vacancies','Total Posts','Total','Vacancy']),
        ('ur',['ur','general','UR','General (UR)','General']),
        ('obc',['obc','OBC']),('sc',['sc','SC']),('st',['st','ST']),('ews',['ews','EWS']),
        ('women',['women','Women','female','Female']),
        ('salary',['salary','pay_scale','Scale of Pay','Salary']),
        ('qualification',['eligibility','qualification','Educational Qualification']),
        ('department',['department','Department']),
    ]
    LABELS = {'post_name':'Post Name','state':'State / UT','language':'Language',
              'total':'Total','ur':'UR/General','obc':'OBC',
              'sc':'SC','st':'ST','ews':'EWS','women':'Women','salary':'Salary',
              'qualification':'Qualification','department':'Department'}
    norm = []; avail = set()
    for row in vac_list:
        if not isinstance(row, dict): continue
        # skip rows that clearly belong to a different table (e.g. disability Category/Description
        # rows leaked into vacancy_details) — they carry none of our known columns
        if not any(a in row for _c, al in ALL_COLS for a in al):
            continue
        n = {}
        for col, aliases in ALL_COLS:
            for a in aliases:
                if a in row and row[a] not in (None,'',{},[]):
                    n[col] = safe(row[a]); avail.add(col); break
        if n: norm.append(n)
    if not norm: return ''
    cols = [c for c,_ in ALL_COLS if c in avail]
    if not cols: return ''

    # ── C3 FIX: clean rows + compute the real grand total ──
    def _to_int(v):
        m = re.search(r'\d[\d,]*', str(v or ''))
        return int(m.group().replace(',', '')) if m else None
    def _is_total_label(v):
        return bool(re.search(r'\b(total|grand\s*total|sum)\b', str(v or ''), re.I))

    has_name = 'post_name' in cols
    # label column = first non-total descriptive column (post_name/state/language)
    _label_cols = [c for c in cols if c in ('post_name','state','language','department')]
    clean = []
    explicit_total = None
    for r in norm:
        name = r.get('post_name', '') or r.get('state','') or r.get('language','')
        # capture an explicitly-labelled total row, don't render it as a data line
        if _is_total_label(r.get('post_name','') or r.get('state','') or r.get('language','')):
            t = _to_int(r.get('total'))
            if t: explicit_total = t
            continue
        # capture an UNLABELLED total row: has a Total value but no descriptive label at all
        if _label_cols and not any(str(r.get(lc,'')).strip() for lc in _label_cols) and str(r.get('total','')).strip():
            t = _to_int(r.get('total'))
            if t: explicit_total = t
            continue
        # drop rows completely empty of label AND total
        if _label_cols and not any(str(r.get(lc,'')).strip() for lc in _label_cols) and not str(r.get('total','')).strip():
            continue
        clean.append(r)
    if not clean and not explicit_total:
        clean = norm

    # If post-name column is entirely blank, render without it (keep state/language)
    if has_name and all(not str(r.get('post_name','')).strip() for r in clean):
        cols = [c for c in cols if c != 'post_name'] or ['total']
        has_name = False

    grand_total = explicit_total
    # sanity: a real grand total can't be smaller than the largest single data row
    if 'total' in cols:
        data_nums = [x for x in (_to_int(r.get('total')) for r in clean) if x]
        data_sum = sum(data_nums) if data_nums else 0
        data_max = max(data_nums) if data_nums else 0
        if grand_total is not None and grand_total < data_max:
            grand_total = data_sum or None      # captured "total" was bogus -> use real sum
        if grand_total is None and data_nums:
            grand_total = data_sum

    head = '<th>Sr.</th>' + ''.join(f'<th>{LABELS[c]}</th>' for c in cols)
    rows = ''.join(f'<tr><td>{i+1}</td>' + ''.join(f'<td>{e(r.get(c,""))}</td>' for c in cols) + '</tr>'
                   for i, r in enumerate(clean))
    # append a correct, clearly-labelled total row (only when meaningful and >1 data row)
    if grand_total and 'total' in cols and len(clean) > 1:
        tot_cells = ''
        first_done = False
        for c in cols:
            if not first_done:
                tot_cells += '<td><strong>Total</strong></td>'; first_done = True
            elif c == 'total':
                tot_cells += f'<td><strong>{grand_total}</strong></td>'
            else:
                tot_cells += '<td></td>'
        rows += f'<tr class="vac-tot">{tot_cells}</tr>'
    return f'<div class="tbl-scroll"><table class="data-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'

# ── Sarkari sections processor ────────────────────────────────
TITLE_MAP = {
    'important dates':'important_dates', 'application fees':'application_fee',
    'application fee':'application_fee', 'age limit':'age_limit',
    'age limit details':'age_limit', 'selection process':'selection_process',
    'total post & qualification':'vacancy_details',
    'total post and qualification':'vacancy_details',
    'vacancy details':'vacancy_details', 'pay scale details':'salary_details',
    'salary details':'salary_details', 'salary / pay scale':'salary_details',
    'monthly salary details':'salary_details', 'monthly salary':'salary_details',
    'salary & pay scale':'salary_details', 'pay scale':'salary_details',
    'how to apply':'how_to_apply', 'gender wise vacancies':'category_wise_vacancy',
    'category wise vacancy':'category_wise_vacancy',
    'exam pattern':'exam_pattern', 'stage-ii exam pattern':'physical_eligibility',
    'stage-i exam pattern':'exam_pattern', 'written exam pattern':'exam_pattern',
    'syllabus':'syllabus',
    'physical eligibility':'physical_eligibility',
    'physical eligibility details':'physical_eligibility',
    'physical standards':'physical_eligibility',
    'physical fitness test':'physical_eligibility',
    'physical measurement':'physical_eligibility',
    'also read :':'important_links_extra', 'also read':'important_links_extra',
    'important related links':'important_links_extra',
    'important instructions':'important_instructions',
    'qualification details':'qualification_section',
    'post wise vacancies':'vacancy_details',
}
SKIP_TITLES = {'set as preferred source on google','set as preferred source','about'}

def render_sarkari_sections(sections_list, existing_il=None):
    """Map titled sections to proper renderers"""
    if not sections_list: return ''
    data = {
        'dates':[],'fee':[],'age':[],'sel':[],'vac_tables':[],'cat_vac':[],
        'salary':[],'hta':[],'inst':[],'exam':[],'syllabus':[],'physical':[],
        'also_read':None,'raw':[],'_has_phys_table':False
    }

    def get_list(content_blocks):
        items = []
        for b in content_blocks:
            if b.get('type') == 'list': items.extend(b.get('items',[]))
            elif b.get('type') == 'paragraph':
                t = safe(b.get('text','')); 
                if t: items.append(t)
        return items

    def get_tables(content_blocks):
        return [b.get('rows',[]) for b in content_blocks if b.get('type')=='table' and b.get('rows')]

    for sec in sections_list:
        title = safe(sec.get('title','') or sec.get('heading','')).strip()
        if title.lower() in SKIP_TITLES: continue
        mapped = TITLE_MAP.get(title.lower())
        content = sec.get('content',[])
        if mapped == 'important_dates': data['dates'].extend(get_list(content))
        elif mapped == 'application_fee': data['fee'].extend(get_list(content))
        elif mapped == 'age_limit': data['age'].extend(get_list(content))
        elif mapped == 'selection_process':
            data['sel'].extend(get_list(content))
            data['vac_tables'].extend(get_tables(content))
        elif mapped == 'vacancy_details':
            items = get_list(content); tables = get_tables(content)
            if items: data['vac_tables'].append({'_list': items})
            data['vac_tables'].extend(tables)
        elif mapped == 'category_wise_vacancy':
            tables = get_tables(content); items = get_list(content)
            data['cat_vac'].extend(tables)
            if items: data['cat_vac'].append({'_list': items})
        elif mapped == 'salary_details':
            data['salary'].extend(get_list(content))
            data['salary'].extend(get_tables(content))  # capture salary tables too
        elif mapped == 'how_to_apply': data['hta'].extend(get_list(content))
        elif mapped == 'important_instructions': data['inst'].extend(get_list(content))
        elif mapped == 'exam_pattern':
            data['exam'].extend(get_list(content)); data['exam'].extend(get_tables(content))
        elif mapped == 'syllabus': data['syllabus'].extend(get_list(content))
        elif mapped == 'physical_eligibility':
            tables = get_tables(content)
            items = get_list(content)
            if tables:
                # Table is authoritative — add to vac_tables, mark that phys table exists
                for t in tables: data['vac_tables'].append({'_phys_table': t})
                data['_has_phys_table'] = True
            elif not data.get('_has_phys_table'):
                # Only add text items if no table has been seen yet for physical
                data['physical'].extend(items)
        elif mapped == 'qualification_section':
            items = get_list(content); tables = get_tables(content)
            if tables:
                for t in tables: data['vac_tables'].append({'_qual_table': t})
            # Items only go to raw if no table — avoid double render
            if items and not tables:
                data['raw'].append({'title': 'Qualification Details', 'content': [{'type':'list','items':items}]})
        elif mapped == 'important_links_extra':
            for b in content:
                if b.get('type')=='table' and b.get('rows'):
                    data['also_read'] = b['rows']; break
        else:
            if content: data['raw'].append({'title':title,'content':content})

    # Post-process: if structured data was extracted (dates/fee/age/sel),
    # strip tables from empty-title raw sections — they're summary duplicates
    if data['dates'] or data['fee'] or data['age'] or data['sel']:
        cleaned_raw = []
        for raw_sec in data['raw']:
            if not raw_sec.get('title','').strip():
                # Keep only non-table blocks (paragraphs, lists)
                clean_content = [b for b in raw_sec.get('content',[]) if b.get('type') != 'table']
                if clean_content:
                    cleaned_raw.append({'title': raw_sec['title'], 'content': clean_content})
            else:
                cleaned_raw.append(raw_sec)
        data['raw'] = cleaned_raw

    html = ''
    if data['dates']:
        lis = render_list_items(data['dates'])
        if lis: html += sec_card('important_dates','fa-calendar-check','b91c1c,#dc2626', lis)
    if data['fee']:
        lis = render_list_items(data['fee'])
        if lis: html += sec_card('application_fee','fa-indian-rupee-sign','c2410c,#ea580c', lis)
    if data['age']:
        lis = render_list_items(data['age'])
        if lis: html += sec_card('age_limit','fa-user-clock','0f766e,#0891b2', lis)
    if data['sel']:
        html += sec_card('selection_process','fa-list-check','5b21b6,#7c3aed', render_selection(data['sel']))
    for tbl in data['vac_tables']:
        if isinstance(tbl, list):
            rendered = render_smart_table(tbl)
            if rendered: html += sec_card('vacancy_details','fa-chart-pie','15803d,#16a34a', rendered)
        elif isinstance(tbl, dict) and tbl.get('_phys_table'):
            # Physical eligibility table — render in physical section
            rendered = render_smart_table(tbl['_phys_table'])
            if rendered: html += sec_card('physical_eligibility','fa-dumbbell','be123c,#e11d48', rendered)
        elif isinstance(tbl, dict) and tbl.get('_qual_table'):
            rendered = render_smart_table(tbl['_qual_table'])
            if rendered: html += sec_card('qualification','fa-graduation-cap','4338ca,#6366f1', rendered)
        elif isinstance(tbl, dict) and tbl.get('_list'):
            lis = render_list_items(tbl['_list'])
            if lis: html += sec_card('vacancy_details','fa-chart-pie','15803d,#16a34a', lis)
    for tbl in data['cat_vac']:
        if isinstance(tbl, list):
            rendered = render_smart_table(tbl)
            if rendered: html += sec_card('category_wise_vacancy','fa-chart-bar','15803d,#16a34a', rendered)
        elif isinstance(tbl, dict) and tbl.get('_list'):
            lis = render_list_items(tbl['_list'])
            if lis: html += sec_card('vacancy_details','fa-chart-pie','15803d,#16a34a', lis)
    if data['salary']:
        salary_items = [x for x in data['salary'] if isinstance(x, str)]
        salary_tables = [x for x in data['salary'] if isinstance(x, list)]
        sal_body = render_list_items(salary_items) + ''.join(render_smart_table(t) for t in salary_tables)
        if sal_body: html += sec_card('salary_details','fa-indian-rupee-sign','15803d,#16a34a', sal_body)
    if data['exam']:
        items = [x for x in data['exam'] if isinstance(x,str)]
        tables = [x for x in data['exam'] if isinstance(x,list)]
        body = render_list_items(items) + ''.join(render_smart_table(t) for t in tables)
        if body: html += sec_card('exam_pattern','fa-file-lines','0369a1,#0284c7', body)
    if data['syllabus']:
        lis = render_list_items(data['syllabus'])
        if lis: html += sec_card('syllabus','fa-book','4338ca,#6366f1', lis)
    if data['physical']:
        lis = render_list_items(data['physical'])
        if lis: html += sec_card('physical_eligibility','fa-dumbbell','be123c,#e11d48', lis)
    if data['hta']:
        html += sec_card('how_to_apply','fa-clipboard-list','0f766e,#0891b2', render_hta(data['hta']))
    if data['inst']:
        items = ''.join(f'<div class="inst-box"><i class="fa-solid fa-triangle-exclamation"></i><span>{e(s)}</span></div>'
                        for s in data['inst'] if s)
        if items: html += sec_card('important_instructions','fa-circle-exclamation','b45309,#ca8a04', items)
    if data['also_read'] and not (existing_il and any(v for v in existing_il.values() if v)):
        btns = ''
        for row in data['also_read']:
            if not isinstance(row, list) or len(row) < 2: continue
            title_cell = row[0]; link_cell = row[-1]
            title_text = re.sub(r'<[^>]+>','',extract_cell(title_cell)[0])
            if isinstance(link_cell, dict) and link_cell.get('links'):
                for lnk in link_cell.get('links',[]):
                    if not isinstance(lnk, dict): continue
                    url = str(lnk.get('url','') or '').strip()
                    lbl = str(lnk.get('text','') or title_text or 'View').strip()
                    if not url.startswith('http') or is_blocked(url): continue
                    ul = url.lower()
                    ic,cl = (('fa-paper-plane','btn-apply') if 'apply' in lbl.lower() else
                             ('fa-globe','btn-official') if 'official' in lbl.lower() else
                             ('fa-file-pdf','btn-pdf') if ul.endswith('.pdf') else
                             ('fa-arrow-up-right-from-square','btn-default'))
                    btns += f'<a href="{e(url)}" class="lnk-btn {cl}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ic}"></i> {e(lbl[:50])}</a>\n'
        if btns: html += sec_card('important_links','fa-link','1e40af,#1e3a8a', f'<div class="links-grid">{btns}</div>')
    # Wrap raw sections in proper sec-card — prevents orphan edu-sec blocks floating outside cards
    raw_html = render_edu_sections(data['raw'])
    if raw_html.strip():
        html += sec_card('Details', 'fa-circle-info', '0369a1,#0284c7', raw_html)
    return html



def render_edu_sections(sections_list):
    """Render education-format sections with heading+content"""
    if not sections_list: return ''
    html = ''
    for sec in sections_list:
        heading = safe(sec.get('heading','') or sec.get('title',''))
        if heading.lower() in SKIP_TITLES: continue
        contents = sec.get('content',[])
        if not contents: continue
        body = ''
        for block in contents:
            btype = (block.get('type','') or '').lower()
            if btype == 'paragraph':
                text = safe(block.get('text',''))
                if text: body += f'<p class="edu-para">{e(text)}</p>'
            elif btype == 'table':
                rows = block.get('rows',[])
                if not rows: continue
                is_obj = (isinstance(rows[0], list) and rows[0] and isinstance(rows[0][0], dict) and 'text' in rows[0][0])
                if is_obj:
                    rendered = render_smart_table(rows)
                    if rendered: body += rendered
                else:
                    headers = block.get('headers',[])
                    data_rows = rows
                    if not headers and rows: headers = rows[0]; data_rows = rows[1:]
                    head = ''.join(f'<th>{e(str(h))}</th>' for h in (headers or []))
                    ncol = len(headers or [])
                    _rparts = []
                    for r in data_rows:
                        if not isinstance(r,(list,tuple)) or not r: continue
                        cells = list(r)
                        if ncol > 1 and len(cells) == 1:
                            _rparts.append(f'<tr><td colspan="{ncol}">{extract_cell(cells[0])[0]}</td></tr>')
                        else:
                            tds = ''.join(f'<td>{extract_cell(c)[0]}</td>' for c in (cells[:ncol] if ncol else cells))
                            if ncol and len(cells) < ncol:
                                tds += '<td></td>' * (ncol - len(cells))
                            _rparts.append(f'<tr>{tds}</tr>')
                    body_rows = ''.join(_rparts)
                    if body_rows:
                        body += f'<div class="tbl-scroll"><table class="data-table">{f"<thead><tr>{head}</tr></thead>" if head else ""}<tbody>{body_rows}</tbody></table></div>'
            elif btype == 'list':
                items = block.get('items',[])
                if items:
                    lis = ''.join(f'<li>{e(str(li)) if isinstance(li,str) else extract_cell(li)[0]}</li>' for li in items if li)
                    if lis: body += f'<ul class="val-list">{lis}</ul>'
            elif btype == 'merged_info':
                for mi in block.get('items',[]):
                    if not isinstance(mi, dict): continue
                    lbl = safe(mi.get('label','')); txt = safe(mi.get('text',''))
                    if lbl or txt:
                        body += f'<div class="mi-item">{f"<b>{e(lbl)}</b>: " if lbl else ""}{e(txt)}</div>'
            elif btype == 'important_links':
                links_data = block.get('links',[])
                if isinstance(links_data, list):
                    btns = ''
                    for lnk in links_data:
                        if not isinstance(lnk, dict): continue
                        url = str(lnk.get('url','') or '').strip()
                        lbl = str(lnk.get('label','') or lnk.get('text','') or 'View').strip() or 'View'
                        if not url.startswith('http') or is_blocked(url): continue
                        ul = url.lower()
                        ic = 'fa-file-pdf' if ul.endswith('.pdf') else 'fa-arrow-up-right-from-square'
                        cl = 'btn-pdf' if ul.endswith('.pdf') else 'btn-default'
                        btns += f'<a href="{e(url)}" class="lnk-btn {cl}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ic}"></i> {e(lbl[:60])}</a>\n'
                    if btns: body += f'<div class="links-grid">{btns}</div>'
            else:
                text = safe(block.get('text','') or block.get('content',''))
                if text: body += f'<p class="edu-para">{e(text)}</p>'
        if body.strip():
            if heading:
                html += f'<div class="edu-sec"><h3 class="edu-sec-h">{e(heading)}</h3>{body}</div>'
            else:
                html += f'<div class="edu-sec">{body}</div>'
    return html

# ── Build all sections from job object ─────────────────────────
SKIP_KEYS = {'seo_tags','category','slug','source_url','url','_slug',
             'sequence','entry_type','sub_type','listing_date','post_date',
             'form_pdf_free_link','application_form_pdf_link','form_pdf_link',
             'apply_online_link','official_notification_pdf_link','official_website_link',
             'jobs_info','status','last_date',
             'application_fees',
             'minimum_age','maximum_age','salary_pay_scale','homepage_serial',
             'organization','post_name','total_vacancy','apply_mode','job_location',
             'short_information','board_name','listing_date','title'}

SECTION_ORDER = ['basic_details','important_dates','application_fee','age_limit',
                 'qualification','vacancy_details','category_wise_vacancy','salary_details',
                 'selection_process','exam_pattern','syllabus','physical_eligibility',
                 'tables','text_sections','useful_links','all_links','details_page_content',
                 'how_to_apply','important_instructions','important_links','faq']

def build_all_sections(job_obj):
    html = ''
    rendered = set()
    # Check for sarkari titled sections
    sections = job_obj.get('sections') or []
    has_sarkari = bool(sections and any(sec.get('title') for sec in sections if isinstance(sec,dict)))
    has_edu_secs = bool(sections and any(sec.get('heading') is not None for sec in sections if isinstance(sec,dict)) and not has_sarkari)
    il = job_obj.get('important_links') or {}

    if has_sarkari:
        html += render_sarkari_sections(sections, il)
        rendered.add('sections')
    elif has_edu_secs:
        # For education/state pages: render Job Overview + Important Dates FIRST (above edu content)
        for _pre_key in ('basic_details', 'important_dates', 'application_fee'):
            _pre_val = job_obj.get(_pre_key)
            if not _pre_val or _pre_val == {} or _pre_val == []: continue
            rendered.add(_pre_key)
            if _pre_key == 'basic_details':   _pre_body = render_basic_details(_pre_val)
            elif _pre_key == 'important_dates': _pre_body = render_dates(_pre_val)
            elif _pre_key == 'application_fee': _pre_body = render_fee(_pre_val)
            else: continue
            if _pre_body and _pre_body.strip():
                _pre_meta = SECTION_META.get(_pre_key, (_pre_key.replace('_',' ').title(), 'fa-circle-info', '1d4ed8,#2563eb'))
                html += sec_card(_pre_meta[0], _pre_meta[1], _pre_meta[2], _pre_body)
        # Now render the edu content sections
        html += render_edu_sections(sections)
        rendered.add('sections')

    for key in SECTION_ORDER:
        if key in rendered: continue
        val = job_obj.get(key)
        if val is None or val == '' or val == [] or val == {}: continue
        rendered.add(key)
        if key == 'basic_details':      body = render_basic_details(val)
        elif key == 'important_dates':  body = render_dates(val)
        elif key == 'application_fee':  body = render_fee(val)
        elif key == 'age_limit':        body = render_list_items(val) if isinstance(val,list) else (f'<table class="kv-table"><tbody>' + ''.join(f'<tr><th>{e(key_label(k))}</th><td>{e(safe(v))}</td></tr>' for k,v in val.items() if safe(v)) + '</tbody></table>' if isinstance(val,dict) else e(safe(val)))
        elif key == 'qualification':    body = (render_list_items(val) if isinstance(val,list) else (render_edu_sections(val) if isinstance(val,list) else f'<div class="edu-sec">{e(safe(val))}</div>'))
        elif key == 'vacancy_details':  body = render_vacancy_table(val)
        elif key == 'category_wise_vacancy': body = (render_vacancy_table(val) if isinstance(val,list) else f'<table class="kv-table"><tbody>' + ''.join(f'<tr><td>{e(key_label(k))}</td><td>{e(safe(v))}</td></tr>' for k,v in val.items() if safe(v)) + '</tbody></table>' if isinstance(val,dict) else '')
        elif key == 'salary_details':   body = render_list_items(val) if isinstance(val,list) else (f'<table class="kv-table"><tbody>' + ''.join(f'<tr><th>{e(key_label(k))}</th><td>{e(safe(v))}</td></tr>' for k,v in val.items() if safe(v)) + '</tbody></table>' if isinstance(val,dict) else f'<div class="edu-sec">{e(safe(val))}</div>')
        elif key == 'selection_process': body = render_selection(val)
        elif key == 'exam_pattern':     body = (render_smart_table(val) if isinstance(val,list) and val and isinstance(val[0],dict) else render_list_items(val) if isinstance(val,list) else f'<div class="edu-sec">{e(safe(val))}</div>')
        elif key == 'tables':
            # sarkari_data tables: [{table_name, rows:[[]]}]
            # gb headline tables = junk (short_info repeat), skip entirely
            # Link rows ("Apply Online", "Official Website" etc) = extract to useful_links pool
            LINK_ROW_RE = re.compile(r'^(apply\s+online|official\s+website|notification|admit\s+card|result|answer\s+key|syllabus|login|register|click\s+here|download)', re.I)
            LINK_KEY_MAP = {
                'apply online': 'apply_online', 'official website': 'official_website',
                'notification': 'notification_pdf', 'admit card': 'admit_card',
                'result': 'result_link', 'answer key': 'answer_key',
                'login': 'login_link', 'download': 'notification_pdf',
            }
            if isinstance(val, list):
                body_parts = []
                # Collect link rows to inject into useful_links if not already set
                _extracted_links = {}
                for tbl in val:
                    if not isinstance(tbl, dict): continue
                    tname = (tbl.get('table_name') or '').strip()
                    rows  = tbl.get('rows') or []
                    if not rows: continue
                    # Skip gb headline / short-info tables entirely
                    if any(x in tname.lower() for x in ['gb headline','headline text','60ccea','gb headline gb']):
                        continue
                    # Filter rows: extract link rows, keep data rows
                    data_rows = []
                    for row in rows:
                        if not isinstance(row, (list, tuple)) or not row: continue
                        c0 = str(row[0]).strip()
                        c1 = str(row[1]).strip() if len(row) > 1 else ''
                        # Timestamp-only rows — skip
                        if re.match(r'^\d{1,2}\s+\w+\s+\d{4}', c0) and len(row) == 1: continue
                        # Link rows — extract URL if present
                        if LINK_ROW_RE.match(c0):
                            if c1.startswith('http') and not is_blocked(c1):
                                map_key = next((v for k,v in LINK_KEY_MAP.items() if c0.lower().startswith(k)), 'apply_online')
                                if map_key not in _extracted_links:
                                    _extracted_links[map_key] = {'title': c0, 'url': c1}
                            continue  # Don't render link rows in table
                        data_rows.append(row)
                    if not data_rows: continue
                    t_html = ''
                    if tname:
                        _total = ''
                        # Only extract total if tname explicitly mentions vacancy/post/recruit
                        if re.search(r'(vacancy|recruit)', tname, re.I):
                            for _row in data_rows:
                                for _cell in _row:
                                    _cell_str = re.sub(r'\d+\+\d+|\d+th|\d+rd|\d+nd|\d+st', '', str(_cell))
                                    _m = re.search(r'\b(\d{3,6})\b', _cell_str)
                                    if _m and 100 <= int(_m.group(1)) <= 99999:
                                        _total = _m.group(1); break
                                if _total: break
                        if _total:
                            smart_name = f"Vacancy Details Total : {_total} Post"
                        else:
                            smart_name = re.sub(r'\s*:\s*Age Limit.*$', '', tname, flags=re.I).strip()[:80] or tname[:80]
                        t_html += f'<div class="tbl-name">{e(smart_name)}</div>'
                    # Split rows into groups by column count
                    # Header detection: text row AND all cells short (< 120 chars) — long cells = data, not headers
                    def is_text_row(r): return bool(r) and all(not re.search(r'^\d+$', str(c).strip()) for c in r)
                    def is_header_row(r): return is_text_row(r) and all(len(str(c).strip()) < 120 for c in r)
                    groups = []
                    i = 0
                    while i < len(data_rows):
                        row = data_rows[i]
                        ncols = len(row)
                        header = None
                        if is_header_row(row):
                            header = row; i += 1
                        body_rows = []
                        while i < len(data_rows):
                            r = data_rows[i]
                            if is_header_row(r) and len(r) != ncols:
                                break
                            body_rows.append(r); i += 1
                        groups.append((header, body_rows, ncols))
                    for (hdr, brows, ncols) in groups:
                        if not hdr and not brows: continue
                        t_html += '<div class="tbl-scroll"><table class="data-table">'
                        if hdr:
                            t_html += '<thead><tr>' + ''.join(f'<th>{e(str(c))}</th>' for c in hdr) + '</tr></thead>'
                        if brows:
                            t_html += '<tbody>'
                            for row in brows:
                                cells = list(row) + [''] * max(0, ncols - len(row))
                                t_html += '<tr>' + ''.join(f'<td>{e(str(cell))}</td>' for cell in cells) + '</tr>'
                            t_html += '</tbody>'
                        t_html += '</table></div>'
                    body_parts.append(t_html)
                body = ''.join(body_parts) if body_parts else ''
                # Store extracted links for useful_links section (if job has no useful_links)
                if _extracted_links and not job_obj.get('useful_links'):
                    job_obj['_table_links'] = _extracted_links
        elif key == 'text_sections':
            # sarkari_data text_sections: [{section, content}]
            # Skip entirely if how_to_apply is already populated — prevents duplicate "How to Apply"
            if job_obj.get('how_to_apply') and (isinstance(job_obj['how_to_apply'], list) and len(job_obj['how_to_apply']) > 0):
                body = ''
            elif isinstance(val, list):
                body_parts = []
                for ts in val:
                    if not isinstance(ts, dict): continue
                    sec_title = safe(ts.get('section') or ts.get('heading') or '')
                    sec_text  = safe(ts.get('content') or ts.get('text') or '')
                    if not sec_text: continue
                    ts_html = ''
                    if sec_title:
                        ts_html += f'<div class="ts-title">{e(sec_title)}</div>'
                    # Split pipe-separated content into bullet list
                    items_list = [s.strip() for s in sec_text.split('|') if s.strip()]
                    if len(items_list) > 1:
                        ts_html += '<ul class="val-list">' + ''.join(f'<li>{e(it)}</li>' for it in items_list) + '</ul>'
                    else:
                        ts_html += f'<p class="edu-para">{e(sec_text)}</p>'
                    body_parts.append(ts_html)
                body = ''.join(body_parts) if body_parts else ''
        elif key == 'useful_links':
            # sarkari_data useful_links:
            #   FORMAT A (list): [{title, links: str|[str]}]
            #   FORMAT B (dict): {apply_online: url, official_website: url, _all: [{title, links}], ...}
            ul_items = []  # normalize to list of {title, url}

            if isinstance(val, list):
                # Format A — direct list
                for ul_item in val:
                    if not isinstance(ul_item, dict): continue
                    title = safe(ul_item.get('title') or ul_item.get('name') or 'Link')
                    links = ul_item.get('links') or ul_item.get('url') or ''
                    if isinstance(links, list):
                        for lnk in links:
                            lnk = str(lnk).strip()
                            if lnk.startswith('http') and not is_blocked(lnk):
                                ul_items.append({'title': title, 'url': lnk})
                    elif isinstance(links, str) and links.startswith('http') and not is_blocked(links):
                        ul_items.append({'title': title, 'url': links})

            elif isinstance(val, dict):
                # Format B — dict with known keys + optional _all array
                # Prefer _all array (has explicit titles), fall back to known keys
                all_arr = val.get('_all') or []
                if isinstance(all_arr, list) and all_arr:
                    for ul_item in all_arr:
                        if not isinstance(ul_item, dict): continue
                        title = safe(ul_item.get('title') or ul_item.get('name') or 'Link')
                        links = ul_item.get('links') or ul_item.get('url') or ''
                        if isinstance(links, list): links = links[0] if links else ''
                        lnk = str(links).strip()
                        if lnk.startswith('http') and not is_blocked(lnk):
                            ul_items.append({'title': title, 'url': lnk})
                else:
                    # No _all — use known keys
                    KEY_TITLES = {
                        'apply_online': 'Apply Online',
                        'notification_pdf': 'Download Notification',
                        'notification': 'Download Notification',
                        'document': 'Download Document',
                        'official_website': 'Official Website',
                        'result_link': 'Result',
                        'admit_card': 'Admit Card',
                        'answer_key': 'Answer Key',
                        'login_link': 'Login',
                        'registration_link': 'Register Now',
                    }
                    for k, title in KEY_TITLES.items():
                        lnk = str(val.get(k) or '').strip()
                        if lnk.startswith('http') and not is_blocked(lnk):
                            ul_items.append({'title': title, 'url': lnk})

            # Also check _table_links extracted from tables section
            tbl_links = job_obj.get('_table_links') or {}
            TBL_KEY_TITLES = {'apply_online':'Apply Online','notification_pdf':'Download Notification',
                              'official_website':'Official Website','admit_card':'Admit Card',
                              'result_link':'Result','answer_key':'Answer Key'}
            seen_urls = {it['url'] for it in ul_items}
            for k, title in TBL_KEY_TITLES.items():
                info = tbl_links.get(k)
                if info and isinstance(info, dict):
                    lnk = info.get('url','')
                    if lnk and lnk not in seen_urls:
                        ul_items.append({'title': info.get('title', title), 'url': lnk})
                        seen_urls.add(lnk)

            # Render ul_items as smart link buttons
            if ul_items:
                def _smart_link(title, url):
                    ul = url.lower()
                    t  = title.lower()
                    if ul.endswith('.pdf') or 'pdf' in ul or 'notice' in ul or 'advertisement' in ul:
                        return ('fa-file-pdf', 'btn-pdf')
                    if 'result' in t or 'merit' in t: return ('fa-trophy', 'btn-result')
                    if 'admit' in t: return ('fa-id-card', 'btn-admit')
                    if 'answer' in t or 'key' in t: return ('fa-key', 'btn-pdf')
                    if 'official' in t or 'website' in t: return ('fa-globe', 'btn-default')
                    if 'apply' in t or 'register' in t or 'ibpsreg' in ul or 'career' in ul:
                        return ('fa-paper-plane', 'btn-apply')
                    return ('fa-arrow-up-right-from-square', 'btn-default')

                rows_html = ''
                seen_render = set()
                for item in ul_items:
                    lnk = item['url']
                    if lnk in seen_render: continue
                    seen_render.add(lnk)
                    ic, cl = _smart_link(item['title'], lnk)
                    rows_html += (f'<tr><td class="ul-title">{e(item["title"])}</td>'
                                  f'<td><a href="{e(lnk)}" class="lnk-btn {cl}" target="_blank" rel="noopener noreferrer">'
                                  f'<i class="fa-solid {ic}"></i> Open</a></td></tr>\n')
                if rows_html:
                    body = (f'<div class="tbl-scroll"><table class="data-table ul-table"><tbody>'
                            f'{rows_html}</tbody></table></div>')
        elif key == 'all_links':
            # all_links: [{label, title, url}] — render as labeled link buttons table
            if isinstance(val, list):
                valid = [lnk for lnk in val if isinstance(lnk,dict) and str(lnk.get('url','')).startswith('http') and not is_blocked(str(lnk.get('url','')))]
                if valid:
                    rows_html = ''
                    for lnk in valid:
                        lbl   = safe(lnk.get('label') or lnk.get('title') or 'Click Here').strip()[:80]
                        title = safe(lnk.get('title') or 'Click Here').strip()[:30]
                        url_l = str(lnk.get('url','')).strip()
                        if not lbl: lbl = title
                        ul_lower = url_l.lower()
                        ic = 'fa-file-pdf' if ul_lower.endswith('.pdf') else 'fa-arrow-up-right-from-square'
                        cl = 'btn-pdf' if ul_lower.endswith('.pdf') else 'btn-default'
                        rows_html += (f'<tr><td class="ul-title">{e(lbl)}</td>'
                                      f'<td><a href="{e(url_l)}" class="lnk-btn {cl}" target="_blank" rel="noopener noreferrer">'
                                      f'<i class="fa-solid {ic}"></i> {e(title)}</a></td></tr>\n')
                    body = (f'<div class="tbl-scroll"><table class="data-table ul-table"><tbody>'
                            f'{rows_html}</tbody></table></div>')
        elif key == 'details_page_content':
            # LATEST_JOBS NEW format: {headings:[str], paragraphs:[str], tables:[{headers,rows,table_heading}], lists:[]}
            if isinstance(val, dict):
                # Determine section title from headings[0], else 'Details'
                _dpc_headings = val.get('headings') or []
                _dpc_title = safe(_dpc_headings[0]).strip() if _dpc_headings else 'Details'
                if not _dpc_title or len(_dpc_title) < 3: _dpc_title = 'Details'
                parts = []
                # Paragraphs — skip junk/noise lines
                _JUNK_RX = re.compile(r'read also|google पर|sarkari result shine|disclaimer|take me to google|preferred source|save the payment|payment receipt|latest updates check here', re.I)
                _LINK_LIKE = re.compile(r'^(apply online|official notification|official website|visit|download|apply now|click here)$', re.I)
                for para in (val.get('paragraphs') or []):
                    para = safe(para).strip()
                    if not para or len(para) < 15: continue
                    if _JUNK_RX.search(para): continue
                    if _LINK_LIKE.match(para): continue
                    parts.append(f'<p class="edu-para">{e(para)}</p>')
                # Tables — skip link-only tables
                for tbl in (val.get('tables') or []):
                    if not isinstance(tbl, dict): continue
                    heading = safe(tbl.get('table_heading') or tbl.get('heading') or '').strip()
                    headers = tbl.get('headers') or []
                    rows    = tbl.get('rows') or []
                    if not rows: continue
                    # Skip tables that are just Apply Online / Official Website link rows
                    all_link_rows = all(
                        len(r) >= 1 and re.match(r'^(apply online|official notification|official website|visit|download|apply now|click here)$', str(r[0]).strip(), re.I)
                        for r in rows if isinstance(r,(list,tuple)) and r
                    )
                    if all_link_rows: continue
                    if _JUNK_RX.search(heading): heading = ''
                    t_html = ''
                    if heading:
                        t_html += f'<div class="tbl-name">{e(heading)}</div>'
                    t_html += '<div class="tbl-scroll"><table class="data-table"><thead><tr>'
                    t_html += ''.join(f'<th>{e(str(h))}</th>' for h in headers)
                    t_html += '</tr></thead><tbody>'
                    for row in rows:
                        if not isinstance(row, (list,tuple)): continue
                        t_html += '<tr>' + ''.join(f'<td>{e(str(c))}</td>' for c in row) + '</tr>'
                    t_html += '</tbody></table></div>'
                    parts.append(t_html)
                # Lists
                for lst in (val.get('lists') or []):
                    items_l = lst.get('items',[]) if isinstance(lst,dict) else (lst if isinstance(lst,list) else [])
                    if items_l:
                        parts.append('<ul class="val-list">' + ''.join(f'<li>{e(str(it))}</li>' for it in items_l if it) + '</ul>')
                body = ''.join(parts) if parts else ''
                # Use dynamic title instead of hardcoded SECTION_META label
                if body and body.strip():
                    html += sec_card(_dpc_title, 'fa-circle-info', '1e40af,#3b82f6', body)
                body = ''  # mark as already rendered
        elif key == 'syllabus':         body = (render_list_items(val) if isinstance(val,list) else f'<div class="edu-sec">{e(safe(val))}</div>')
        elif key == 'physical_eligibility': body = (f'<table class="kv-table"><tbody>' + ''.join(f'<tr><th>{e(key_label(k))}</th><td>{e(safe(v))}</td></tr>' for k,v in val.items() if safe(v)) + '</tbody></table>' if isinstance(val,dict) else render_list_items(val) if isinstance(val,list) else f'<div class="edu-sec">{e(safe(val))}</div>')
        elif key == 'how_to_apply':     body = render_hta(val)
        elif key == 'important_instructions': body = ''.join(f'<div class="inst-box"><i class="fa-solid fa-triangle-exclamation"></i><span>{e(safe(s))}</span></div>' for s in (val if isinstance(val,list) else [val]) if safe(s))
        elif key == 'important_links':  body = render_links(val)
        elif key == 'faq':              body = render_faq(val)
        elif key == 'sections':
            body = render_edu_sections(val) if isinstance(val,list) else ''
        else:                           body = ''
        meta = SECTION_META.get(key)
        if meta and body and body.strip():
            html += sec_card(key, meta[1], meta[2], body)

    # Unknown/future keys
    for key, val in job_obj.items():
        if key in rendered or key in SKIP_KEYS: continue
        if not val or val == {} or val == []: continue
        sv = safe(val) if not isinstance(val,(list,dict)) else None
        if sv:
            body = f'<div class="edu-sec">{e(sv)}</div>'
            html += sec_card(key_label(key), 'fa-circle-dot', '475569,#334155', body)
    return html

# ── Schema builder ─────────────────────────────────────────────

# N9: Parse salary from pay_scale string for accurate JobPosting schema
_LEVEL_PAY = {1:18000,2:19900,3:21700,4:25500,5:29200,6:35400,
              7:44900,8:47600,9:53100,10:56100,11:67700,12:78800,
              13:123100,14:144200,15:182200,16:205400,17:225000,18:250000}

def parse_salary(pay_str):
    if not pay_str: return (18000, 92300)
    lm = re.search(r'level[- ]?(\d+)', str(pay_str).lower())
    if lm:
        lvl = int(lm.group(1))
        base = _LEVEL_PAY.get(lvl, 25000)
        return (base, min(int(base * 2.5), 250000))
    nums = [int(n.replace(',','')) for n in re.findall(r'[\d,]{4,}', str(pay_str))
            if 5000 <= int(n.replace(',','')) <= 500000]
    if len(nums) >= 2: return (min(nums), max(nums))
    if len(nums) == 1: return (nums[0], min(int(nums[0]*2), 250000))
    return (18000, 92300)

def build_schemas(job_obj, canon_url, breadcrumbs, slug=None):
    bd    = job_obj.get('basic_details', {}) or {}
    dates = job_obj.get('important_dates', {}) or {}
    faq   = job_obj.get('faq', []) or []
    title = safe(bd.get('job_title','') or job_obj.get('title',''))
    org   = safe(bd.get('organization_name','') or 'Government of India')
    loc   = safe(bd.get('job_location','') or 'India')
    desc  = safe(bd.get('short_information',''))[:500] or title
    last_d = safe(dates.get('last_date_to_apply','') or dates.get('last_date',''))

    if slug is None:
        slug = slugify(title)[:80]
    intent = page_intent(job_obj)
    # C1: stable datePosted (never build-date for the same job across rebuilds)
    date_posted = get_date_posted(slug, job_obj)

    # ── Breadcrumb schema (always) ──
    bc_items = [{'@type':'ListItem','position':1,'name':'Home','item':BASE_URL+'/'}]
    for i,(lbl,url) in enumerate(breadcrumbs, 2):
        bc_items.append({'@type':'ListItem','position':i,'name':lbl,'item':url})
    bc_items.append({'@type':'ListItem','position':len(bc_items)+1,'name':title,'item':canon_url})
    bc_schema = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':bc_items}

    if intent == 'job':
        # ── H1: proper JobPosting only for real jobs ──
        jp = {'@context':'https://schema.org','@type':'JobPosting','title':title,
              'description':desc,'datePosted':date_posted,'url':canon_url,
              'employmentType':'FULL_TIME','directApply':False,
              'identifier':{'@type':'PropertyValue','name':org,
                            'value':safe(bd.get('advt_no','') or bd.get('notification_no','') or slug)},
              'hiringOrganization':{'@type':'Organization','name':org,'sameAs':BASE_URL},
              'jobLocation':{'@type':'Place','address':{'@type':'PostalAddress','addressCountry':'IN','addressLocality':loc}},
              'applicantLocationRequirements':{'@type':'Country','name':'India'}}
        # H1: only emit baseSalary when we actually have a salary string (no min:0 spam)
        _pay_str = safe((job_obj.get('basic_details') or {}).get('pay_scale','') or
                        (job_obj.get('salary_details') or {}).get('pay_scale','') or '')
        if _pay_str:
            _sal_min, _sal_max = parse_salary(_pay_str)
            if _sal_min and _sal_min > 0:
                jp['baseSalary'] = {'@type':'MonetaryAmount','currency':'INR',
                    'value':{'@type':'QuantitativeValue','minValue':_sal_min,'maxValue':_sal_max,'unitText':'MONTH'}}
        if last_d:
            nd = norm_date(last_d)
            if nd: jp['validThrough'] = nd + 'T00:00:00'
        primary = jp
    else:
        # C2: result / admitcard / scheme / article -> Article (NOT JobPosting)
        primary = {'@context':'https://schema.org','@type':'Article',
                   'headline':title[:110],'description':desc,'url':canon_url,
                   'datePublished':date_posted,'dateModified':TODAY,
                   'author':{'@type':'Organization','name':'Top Sarkari Jobs','url':BASE_URL},
                   'publisher':{'@type':'Organization','name':'Top Sarkari Jobs',
                                'logo':{'@type':'ImageObject','url':BASE_URL+'/image.png'}},
                   'mainEntityOfPage':{'@type':'WebPage','@id':canon_url},
                   'image':BASE_URL+'/og-jobs.png'}

    out = (f'<script type="application/ld+json">{json.dumps(primary, ensure_ascii=False)}</script>\n'
           f'<script type="application/ld+json">{json.dumps(bc_schema, ensure_ascii=False)}</script>\n')

    # de-dup FAQs + strip pre-existing Q-number prefix for clean structured data
    _seen_q = set(); valid_faqs = []
    for f in faq:
        if not isinstance(f, dict): continue
        q = str(f.get('question','') or '').strip()
        a = str(f.get('answer','') or '').strip()
        if not q or not a: continue
        q = re.sub(r'^\s*Q?\s*\d{1,3}\s*[\.\):\-]\s*', '', q, flags=re.I).strip()
        k = re.sub(r'\s+', ' ', q.lower()).strip()
        if not k or k in _seen_q: continue
        _seen_q.add(k)
        valid_faqs.append({'question': q, 'answer': a})
        if len(valid_faqs) >= 10: break
    if valid_faqs:
        faq_schema = {'@context':'https://schema.org','@type':'FAQPage',
            'mainEntity':[{'@type':'Question','name':f['question'],'acceptedAnswer':{'@type':'Answer','text':f['answer']}} for f in valid_faqs]}
        out += f'<script type="application/ld+json">{json.dumps(faq_schema, ensure_ascii=False)}</script>\n'
    return out

# ── CSS ────────────────────────────────────────────────────────
PAGE_CSS = """
*,*::before,*::after{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f4f8;margin:0;color:#1e293b}
a{text-decoration:none}.skip-link{position:absolute;left:-9999px}.skip-link:focus{left:8px;top:8px;z-index:999;background:#1d4ed8;color:#fff;padding:8px 16px;border-radius:6px}
.pg-wrap{max-width:880px;margin:0 auto;padding:12px 10px max(80px,calc(60px + env(safe-area-inset-bottom,0px)))}
.bc{font-size:.74rem;color:#64748b;padding:8px 10px;display:flex;flex-wrap:wrap;gap:4px;align-items:center;background:#fff;border-bottom:1px solid #e2e8f0}
.bc a{color:#1d4ed8}.bc a:hover{text-decoration:underline}.bc-sep{color:#d1d5db;font-size:.6rem}
.notice{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:9px 14px;font-size:.8rem;color:#78350f;margin-bottom:12px;display:flex;gap:8px;align-items:flex-start}
.detail-header{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px 0;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.detail-h1{font-size:1.18rem;font-weight:900;color:#0f172a;line-height:1.4;margin:0 0 8px}
.badges{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:9px}
.badge{display:inline-flex;align-items:center;gap:4px;font-size:.7rem;font-weight:700;text-transform:uppercase;padding:3px 9px;border-radius:20px;letter-spacing:.04em}
.badge-cat{background:#dbeafe;color:#1e40af}.badge-loc{background:#dcfce7;color:#15803d}.badge-mode{background:#ede9fe;color:#5b21b6}
.stats-bar{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #e2e8f0;margin-top:10px}
.stat{text-align:center;padding:10px 4px;border-right:1px solid #e2e8f0}
.stat:last-child{border-right:none}
.stat-val{font-size:.95rem;font-weight:800;color:#0f172a;word-break:break-word}
.stat-lbl{font-size:.65rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
@media(max-width:600px){.stats-bar{grid-template-columns:repeat(2,1fr)}.stat:nth-child(2){border-right:none}.stat:nth-child(3){border-top:1px solid #e2e8f0}.stat:nth-child(4){border-top:1px solid #e2e8f0;border-right:none}}
.short-info{background:#eff6ff;border-left:4px solid #1d4ed8;padding:10px 14px;font-size:.84rem;color:#1e293b;line-height:1.7;margin-bottom:10px;border-radius:0 8px 8px 0;display:flex;gap:8px;align-items:flex-start}
.sec-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.04)}
.sec-head{display:flex;align-items:center;gap:8px;padding:10px 14px;color:#fff;font-size:.86rem;font-weight:700}
.sec-head h2{margin:0;font-size:.86rem;font-weight:700;color:#fff}
.sec-body{padding:0}
.kv-table{width:100%;border-collapse:collapse;font-size:.82rem}
.kv-table th{background:#f8fafc;color:#374151;font-weight:700;padding:9px 13px;text-align:left;border-bottom:1px solid #e9eef4;width:38%;vertical-align:top;word-break:break-word}
.kv-table td{padding:9px 13px;color:#1e293b;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word;overflow-wrap:break-word;line-height:1.6}
.kv-table tr:last-child th,.kv-table tr:last-child td{border-bottom:none}
.date-last{color:#dc2626;font-weight:700}
.fee-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}
.fee-cell{padding:9px 13px;border-right:1px solid #f1f5f9;border-bottom:1px solid #f1f5f9}
.fee-cat{display:block;font-size:.68rem;font-weight:700;text-transform:uppercase;color:#64748b;margin-bottom:3px;letter-spacing:.04em}
.fee-amt{font-size:.93rem;font-weight:800;color:#1e293b}.fee-free{color:#16a34a}.fee-paid{color:#dc2626}
.fee-note{padding:9px 14px;font-size:.8rem;color:#78350f;background:#fffbeb;border-top:1px solid #fde68a;display:flex;gap:6px}
.tbl-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%}
.data-table{width:100%;border-collapse:collapse;font-size:.81rem;min-width:420px;table-layout:auto}
.data-table th{background:#1d4ed8;color:#fff;padding:8px 10px;font-weight:700;text-align:left;white-space:nowrap;min-width:70px}
.data-table td{padding:8px 10px;border-bottom:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top;line-height:1.5;min-width:60px}
.data-table tr:last-child td{border-bottom:none}
.data-table tr:nth-child(even) td{background:#f8fafc}
.sel-steps{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
.sel-step{display:inline-flex;align-items:center;gap:7px;background:#f0f7ff;border:1px solid #bfdbfe;border-radius:8px;padding:6px 12px;font-size:.8rem;font-weight:600;color:#1e40af}
.sel-num{background:#1e40af;color:#fff;border-radius:50%;width:20px;height:20px;display:inline-flex;align-items:center;justify-content:center;font-size:.66rem;font-weight:800;flex-shrink:0}
.hta-list{list-style:none;margin:0;padding:0}
.hta-item{display:flex;align-items:flex-start;gap:11px;padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:.83rem;line-height:1.65}
.hta-item:last-child{border-bottom:none}
.hta-num{flex-shrink:0;width:24px;height:24px;background:#0f766e;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:800}
.inst-box{display:flex;align-items:flex-start;gap:10px;padding:9px 14px;border-bottom:1px solid #f1f5f9;font-size:.82rem;color:#78350f;line-height:1.6}
.inst-box:last-child{border-bottom:none}
.inst-box i{color:#ca8a04;flex-shrink:0;margin-top:2px}
.links-grid{display:flex;flex-wrap:wrap;gap:8px;padding:13px 14px}
.lnk-btn{display:inline-flex;align-items:center;gap:6px;padding:8px 15px;border-radius:8px;font-size:.81rem;font-weight:700;text-decoration:none;white-space:nowrap;transition:all .15s;border:1px solid transparent;min-height:38px}
.btn-apply{background:#dcfce7;color:#15803d;border-color:#86efac}.btn-apply:hover{background:#15803d;color:#fff}
.btn-official{background:#d1fae5;color:#065f46;border-color:#6ee7b7}.btn-official:hover{background:#059669;color:#fff}
.btn-pdf{background:#fee2e2;color:#991b1b;border-color:#fca5a5}.btn-pdf:hover{background:#dc2626;color:#fff}
.btn-register{background:#fef3c7;color:#92400e;border-color:#fcd34d}.btn-register:hover{background:#d97706;color:#fff}
.btn-login{background:#ede9fe;color:#5b21b6;border-color:#c4b5fd}.btn-login:hover{background:#6d28d9;color:#fff}
.btn-admit{background:#ccfbf1;color:#0f766e;border-color:#5eead4}.btn-admit:hover{background:#0f766e;color:#fff}
.btn-answer{background:#e0e7ff;color:#3730a3;border-color:#a5b4fc}.btn-answer:hover{background:#3730a3;color:#fff}
.btn-result{background:#fefce8;color:#713f12;border-color:#fde047}.btn-result:hover{background:#a16207;color:#fff}
.btn-syllabus{background:#f0fdf4;color:#15803d;border-color:#86efac}.btn-syllabus:hover{background:#15803d;color:#fff}
.btn-merit{background:#f0f9ff;color:#0369a1;border-color:#7dd3fc}.btn-merit:hover{background:#0369a1;color:#fff}
.btn-default{background:#dbeafe;color:#1e40af;border-color:#93c5fd}.btn-default:hover{background:#1e40af;color:#fff}
.faq-item{border-bottom:1px solid #f1f5f9;padding:12px 14px}
.faq-item:last-child{border-bottom:none}
.faq-q{display:flex;gap:9px;align-items:flex-start;font-weight:700;color:#0f172a;font-size:.84rem;line-height:1.5;margin-bottom:7px}
.faq-icon{background:#1d4ed8;color:#fff;border-radius:5px;padding:2px 7px;font-size:.71rem;font-weight:800;flex-shrink:0;margin-top:1px}
.faq-a{display:flex;gap:9px;align-items:flex-start;font-size:.82rem;color:#475569;line-height:1.7}
.edu-sec{padding:11px 14px;border-bottom:1px solid #f1f5f9}.edu-sec:last-child{border-bottom:none}
.edu-sec-h{font-size:.85rem;font-weight:700;color:#1e293b;margin:0 0 8px}
.edu-para{font-size:.82rem;color:#374151;line-height:1.7;margin:0 0 7px}
.mi-item{font-size:.82rem;color:#374151;line-height:1.6;padding:3px 0}
.val-list{margin:8px 0;padding-left:22px;font-size:.82rem;color:#374151;line-height:1.7}
.rel-section{background:#fff;border:1px solid #e2e8f0;border-radius:12px;margin-top:10px;overflow:hidden}
.rel-head{padding:10px 14px;background:#f8fafc;border-bottom:1px solid #e2e8f0;font-size:.82rem;font-weight:700;color:#374151}
.rel-grid{display:flex;flex-wrap:wrap;gap:7px;padding:11px 14px}
.rel-btn{display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:8px;font-size:.77rem;font-weight:600;text-decoration:none;background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;transition:all .15s;white-space:nowrap}
.rel-btn:hover{background:#1d4ed8;color:#fff;border-color:#1d4ed8}
.cat-wrap{max-width:880px;margin:0 auto;padding:12px 10px 48px}
.cat-header{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:15px 18px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.cat-h1{font-size:1.1rem;font-weight:900;color:#0f172a;margin:0 0 4px}
.cat-count{font-size:.78rem;color:#64748b;margin:0}
.search-bar{display:flex;gap:8px;margin-bottom:12px}
.search-bar input{flex:1;min-width:200px;padding:9px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:.84rem;outline:none}
.search-bar input:focus{border-color:#1d4ed8;box-shadow:0 0 0 2px #dbeafe}
.job-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:9px;box-shadow:0 1px 3px rgba(0,0,0,.04);transition:box-shadow .15s}
.job-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.1)}
.job-card-title{font-size:.9rem;font-weight:800;color:#0f172a;line-height:1.4;margin-bottom:5px}
.job-card-title a{color:inherit}.job-card-title a:hover{color:#1d4ed8;text-decoration:underline}
.job-card-org{color:#64748b;font-size:.79rem;margin-bottom:5px;display:flex;gap:5px;align-items:center}
.job-card-meta{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px}
.jm-badge{font-size:.67rem;font-weight:700;padding:2px 8px;border-radius:12px}
.job-card-date{font-size:.76rem;font-weight:700}.job-card-date.urgent{color:#dc2626}
.job-card-links{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}
.jl-btn{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:6px;font-size:.72rem;font-weight:700;text-decoration:none;transition:all .12s;border:1px solid transparent;min-height:28px}
.btn-answer{background:#fef9c3;color:#854d0e;border-color:#fde68a}.btn-answer:hover{background:#b45309;color:#fff}
"""

# ── Page builder ───────────────────────────────────────────────
def build_detail_page(job_obj, slug, canon_url, breadcrumbs, badge_label='Govt Job', noindex_dup=False):
    bd    = job_obj.get('basic_details', {}) or {}
    dates = job_obj.get('important_dates', {}) or {}
    il    = job_obj.get('important_links', {}) or {}
    seo   = job_obj.get('seo_tags', []) or []
    faq   = job_obj.get('faq', []) or []

    title     = safe(bd.get('job_title','') or job_obj.get('title','') or 'Government Job')
    org       = safe(bd.get('organization_name','') or 'Government of India')
    vacancies = safe(bd.get('total_vacancies','') or job_obj.get('total_post','') or job_obj.get('total_vacancy',''))
    last_d    = safe(dates.get('last_date_to_apply','') or dates.get('last_date_apply_online','') or dates.get('last_date','') or job_obj.get('last_date',''))
    apply_m   = safe(bd.get('application_mode','') or job_obj.get('apply_mode','') or ('Offline' if job_obj.get('category') == 'OFFLINE_FORM' else 'Online'))
    location  = safe(bd.get('job_location','') or job_obj.get('job_location','') or 'India')

    # Build SEO title inline (50-60 chars)
    _BRAND = ' | Top Sarkari Jobs'
    _vac_n = vacancies if vacancies and vacancies not in ('—','') else ''
    _vac_s = f', {_vac_n} Posts' if _vac_n else ''
    # Shorten org name for title
    _ORG_MAP = {
        'Delhi Subordinate Services Selection Board':'DSSSB',
        'Staff Selection Commission':'SSC','Union Public Service Commission':'UPSC',
        'Railway Recruitment Board':'RRB','State Bank of India':'SBI',
        'Reserve Bank of India':'RBI','Employees Provident Fund Organisation':'EPFO',
        'Institute of Banking Personnel Selection':'IBPS',
        'All India Institute of Medical Sciences':'AIIMS',
        'National Testing Agency':'NTA','Bharat Sanchar Nigam Limited':'BSNL',
    }
    _org_s = next((s for f,s in _ORG_MAP.items() if f.lower() in org.lower()), None)
    if not _org_s:
        _w = org.split()
        _org_s = org if len(_w)<=3 else ' '.join(_w[:3])
    _MAX = 60 - len(_BRAND)
    # Content type detection
    import re as _re
    _tl = title.lower()
    _ctype_map = {
        'result': r'\b(result|declared|scorecard|merit list)\b',
        'admit':  r'\b(admit card|hall ticket|call letter)\b',
        'answer': r'\b(answer key|answer sheet)\b',
    }
    _ct = next((c for c,p in _ctype_map.items() if _re.search(p, _tl)), 'default')
    _yr_m = _re.search(r'20\d\d', title)
    _yr = _yr_m.group() if _yr_m else str(YEAR)
    if _ct != 'default':
        _fmt = {'result':'{o} {y} Result','admit':'{o} {y} Admit Card','answer':'{o} {y} Answer Key'}
        _jp = _fmt[_ct].format(o=_org_s, y=_yr)
    else:
        # H2: prefer the real, intent-rich title (post name + Recruitment/Vacancy/Form),
        # trimmed to fit; fall back to org-based only if title is unusable.
        _clean_title = re.sub(r'\s*-\s*(latest jobs|big update|notification out).*$', '', title, flags=re.I).strip()
        _has_intent = bool(re.search(r'\b(recruitment|vacancy|vacancies|online form|apply online|posts|notification|admit card|result)\b', _clean_title, re.I))
        if _has_intent and 15 <= len(_clean_title):
            _jp = _clean_title
        else:
            _jp = f'{_org_s} {_yr} Recruitment{_vac_s}'
            if len(_jp) > _MAX:
                _jp = f'{_org_s} {_yr}{_vac_s}'
            if len(_jp) < 15:
                _jp = title[:_MAX]
    if len(_jp) > _MAX:
        _jp = _jp[:_MAX-1].rsplit(' ',1)[0].rstrip(',-–(') + '…'
    title_tag = (_jp + _BRAND)[:60]
    keywords   = ', '.join(str(k) for k in (seo if isinstance(seo,list) else []) + [org, location, 'sarkari job'])[:200]
    short_info = safe(bd.get('short_information','') or job_obj.get('jobs_info','') or job_obj.get('short_information',''))
    # Build meta description inline
    _si = short_info.rstrip('.,; ').strip() if short_info else ''
    _vd = vacancies if vacancies and vacancies not in ('—','') else ''
    _ld_s = last_d.strip() if last_d and last_d not in ('—','') else ''
    _base_md = _si[:100] if _si else f'{title[:60].rstrip()} Recruitment {YEAR}'
    if _si and len(_si) > 100:
        _base_md = _si[:_si.rfind(' ', 80, 100)] if ' ' in _si[80:100] else _si[:100]
    _parts = [_base_md]
    if _vd: _parts.append(f'{_vd} Posts')
    if _ld_s: _parts.append(f'Last Date: {_ld_s}')
    _cta_md = f'Apply {apply_m.lower() if apply_m else "online"} at Top Sarkari Jobs.'
    _md_full = '. '.join(p.rstrip('.') for p in _parts) + '. ' + _cta_md
    if len(_md_full) > 155:
        _cut = _md_full[:155]
        # back off to last full word; avoid mid-word cut
        if ' ' in _cut:
            _cut = _cut[:_cut.rfind(' ')]
        meta_desc = _cut.rstrip(' ,;:-') + '…'
    else:
        meta_desc = _md_full

    schemas_html = build_schemas(job_obj, canon_url, breadcrumbs, slug)

    # Breadcrumb HTML
    bc_html = '<nav class="bc" aria-label="Breadcrumb"><a href="/">Home</a>'
    for lbl, url in breadcrumbs:
        bc_html += f'<span class="bc-sep">›</span><a href="{e(url)}">{e(lbl)}</a>'
    bc_html += f'<span class="bc-sep">›</span><span aria-current="page">{e(title[:55])}{"…" if len(title)>55 else ""}</span></nav>'

    # Quick apply link
    apply_url = safe(il.get('apply_online','') or il.get('registration_link','') or bd.get('official_website',''))
    apply_banner = ''
    if apply_url and not is_blocked(apply_url):
        apply_banner = (f'<a href="{e(apply_url)}" target="_blank" rel="noopener noreferrer" class="apply-cta">'
                       f'<i class="fa-solid fa-paper-plane"></i> Apply Online / Official Website ↗</a>')

    # Header
    cat_badge = safe(job_obj.get('category','') or badge_label).replace('_',' ')
    header_html = f'''<div class="detail-header">
  <div class="badges">
    <span class="badge badge-cat"><i class="fa-solid fa-briefcase"></i> {e(cat_badge or badge_label)}</span>
    <span class="badge badge-loc"><i class="fa-solid fa-map-pin"></i> {e(location[:25])}</span>
    <span class="badge badge-mode"><i class="fa-solid fa-laptop"></i> {e(apply_m)}</span>
  </div>
  <h1 class="detail-h1">{e(title)}</h1>
  <div class="stats-bar">
    <div class="stat"><div class="stat-val">{e(vacancies or "—")}</div><div class="stat-lbl">Vacancies</div></div>
    <div class="stat"><div class="stat-val" style="color:#dc2626">{e(last_d or "—")}</div><div class="stat-lbl">Last Date</div></div>
    <div class="stat"><div class="stat-val">{e(apply_m or "Online")}</div><div class="stat-lbl">Apply Mode</div></div>
    <div class="stat"><div class="stat-val">{e(location[:15] or "India")}</div><div class="stat-lbl">Location</div></div>
  </div>
</div>'''

    sections_html = build_all_sections(job_obj)
    if not sections_html.strip():
        sections_html = '<div class="sec-card"><div class="sec-body" style="padding:24px;text-align:center;color:#94a3b8"><i class="fa-solid fa-clock" style="font-size:1.5rem;display:block;margin-bottom:8px"></i>Detailed information will be updated soon. Please visit the official website.</div></div>'

    rel_links = '''<div class="rel-section"><div class="rel-head">Related Categories</div><div class="rel-grid">
  <a href="/section/latest-jobs/" class="rel-btn"><i class="fa-solid fa-briefcase"></i> Latest Jobs</a>
  <a href="/section/admit-card/" class="rel-btn"><i class="fa-solid fa-id-card"></i> Admit Cards</a>
  <a href="/section/results/" class="rel-btn"><i class="fa-solid fa-trophy"></i> Results</a>
  <a href="/state-jobs/" class="rel-btn"><i class="fa-solid fa-map-location-dot"></i> State Jobs</a>
  <a href="/education/" class="rel-btn"><i class="fa-solid fa-graduation-cap"></i> Education</a>
</div></div>'''

    body = f'''<div class="pg-wrap">
  {bc_html}
  <div class="notice"><i class="fa-solid fa-triangle-exclamation"></i><span><strong>Important:</strong> Always verify details on official website. Dates &amp; eligibility may change.</span></div>
  {header_html}
  {f'<div style="margin-bottom:12px">{apply_banner}</div>' if apply_banner else ''}
  {sections_html}
  {rel_links}
</div>'''

    return f'''<!DOCTYPE html>
<html lang="en-IN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{e(title_tag[:60])}</title>
<meta name="description" content="{e(meta_desc)}"/>
<meta name="keywords" content="{e(keywords)}"/>
<meta name="robots" content="{'noindex,follow' if noindex_dup else 'index,follow,max-snippet:-1,max-image-preview:large'}"/>
<link rel="canonical" href="{e(canon_url)}"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="Top Sarkari Jobs"/>
<meta property="og:title" content="{e(title_tag[:60])}"/>
<meta property="og:description" content="{e(meta_desc)}"/>
<meta property="og:url" content="{e(canon_url)}"/>
<meta property="og:image" content="{BASE_URL}/{'og-results.png' if any(x in canon_url for x in ['/result','/result']) else 'og-admit.png' if 'admit' in canon_url else 'og-jobs.png'}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{e(title_tag[:60])}"/>
<meta name="twitter:description" content="{e(meta_desc)}"/>
{schemas_html}
<script src="/tsj-config.js"></script>
<link rel="preconnect" href="https://www.google-analytics.com" crossorigin/>
<link rel="dns-prefetch" href="https://www.googletagmanager.com"/>
<meta name="author" content="Top Sarkari Jobs"/>
<meta name="geo.region" content="IN"/>
<link rel="icon" href="/image.ico"/>
<link rel="stylesheet" href="/styles.css"/>
<link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/>
<noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>
<link rel="manifest" href="/manifest.json"/>
<meta name="theme-color" content="#0d2257"/>
<script src="/analytics.js" defer></script>
<link rel="stylesheet" href="/styles-detail.css" media="print" onload="this.media='all'"/>
<noscript><link rel="stylesheet" href="/styles-detail.css"/></noscript>
<style>
.apply-cta{{display:flex;align-items:center;justify-content:center;gap:8px;background:linear-gradient(135deg,#059669,#047857);color:#fff;padding:12px 20px;border-radius:10px;font-size:.9rem;font-weight:800;text-decoration:none}}
.apply-cta:hover{{background:linear-gradient(135deg,#047857,#065f46)}}
</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<div id="headerPlaceholder"></div>
<script src="/tsj-init.js?v={ASSET_VER}"></script>
<main id="main">{body}</main>
<div id="footerPlaceholder"></div>
<script src="/tsj-footer-init.js?v={ASSET_VER}"></script>
<script src="/tsj-menu.js?v={ASSET_VER}" defer></script>
</body>
</html>'''

# ── Listing page builder ───────────────────────────────────────
def build_listing_page(title, jobs, canon_url, breadcrumbs, desc=''):
    _yr_str = str(YEAR)
    title_tag  = (f"{title} — Apply Online | Top Sarkari Jobs" if _yr_str in title else f"{title} {YEAR} — Apply Online | Top Sarkari Jobs")
    meta_desc  = (desc[:130] or f"{title}: Latest notifications, apply online, check dates. {YEAR}")[:155]
    bc_html    = '<nav class="bc" aria-label="Breadcrumb"><a href="/">Home</a>'
    for lbl, url in breadcrumbs:
        bc_html += f'<span class="bc-sep">›</span><a href="{e(url)}">{e(lbl)}</a>'
    bc_html   += f'<span class="bc-sep">›</span><span aria-current="page">{e(title)}</span></nav>'
    bc_schema  = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':
        [{'@type':'ListItem','position':1,'name':'Home','item':BASE_URL+'/'}] +
        [{'@type':'ListItem','position':i+2,'name':b[0],'item':BASE_URL+b[1]} for i,b in enumerate(breadcrumbs)] +
        [{'@type':'ListItem','position':len(breadcrumbs)+2,'name':title,'item':canon_url}]}
    schemas_tag = f'<script type="application/ld+json">{json.dumps(bc_schema,ensure_ascii=False)}</script>'

    cards_html = ''
    for job in jobs:
        bd    = job.get('basic_details',{}) or {}
        dates = job.get('important_dates',{}) or {}
        il    = job.get('important_links',{}) or {}
        jtitle = safe(bd.get('job_title','') or job.get('title','') or job.get('name',''))
        if not jtitle: continue
        _raw_slug = safe(job.get('_slug','') or job.get('slug',''))
        # Clean SR prefix (sr_result-, sr_admit_card-, etc.) for URL
        import re as _re2
        jslug = _re2.sub(r'^sr_[a-z_]+-','', _raw_slug) if _raw_slug else ''
        # Also strip trailing hash suffix (-xxxxxx)
        jslug = _re2.sub(r'-[0-9a-f]{6,8}$','', jslug) if jslug else ''
        jslug = jslug or slugify(jtitle)
        jorg   = safe(bd.get('organization_name','') or 'Government')
        jvac   = safe(bd.get('total_vacancies','') or job.get('total_post',''))
        jld    = safe(dates.get('last_date_to_apply','') or dates.get('last_date_apply_online','') or dates.get('last_date','') or job.get('last_date',''))
        jmode  = safe(bd.get('application_mode','') or job.get('apply_mode','') or 'Online')
        # Quick links — with fallbacks for non-standard key names
        ql = ''
        # apply_online: try direct key, then click_here[0] as fallback
        _il = job.get('important_links') or {}
        _ul = job.get('useful_links') or {}
        def _get_link(key):
            v = safe(_il.get(key,'') or _ul.get(key,''))
            if v and not v.startswith('[') and not v.startswith('{'):
                return v
            return ''
        apply_url = _get_link('apply_online') or _get_link('registration_link') or _get_link('login_link')
        if not apply_url:
            ch = _il.get('click_here') or _ul.get('click_here') or []
            if isinstance(ch, str): ch = [ch]
            if isinstance(ch, list):
                for cu in ch:
                    cu = safe(cu)
                    if cu.startswith('http') and not is_blocked(cu):
                        apply_url = cu; break
        notif_url = _get_link('notification_pdf') or _get_link('download_notification') or _get_link('official_notification')
        result_url = _get_link('result_link') or _get_link('result')
        admit_url = _get_link('admit_card') or _get_link('admit')
        answer_url = _get_link('answer_key') or _get_link('answerkey')
        for url, lbl, css, ic in [
            (apply_url,'Apply','btn-apply jl-btn','fa-paper-plane'),
            (notif_url,'Notification','btn-pdf jl-btn','fa-file-pdf'),
            (result_url,'Result','btn-result jl-btn','fa-trophy'),
            (admit_url,'Admit Card','btn-admit jl-btn','fa-id-card'),
            (answer_url,'Answer Key','btn-answer jl-btn','fa-key'),
        ]:
            if url and not is_blocked(url):
                ql += f'<a href="{e(url)}" class="{css}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ic}"></i> {lbl}</a>'
        urgent_cls = ''
        if jld:
            try:
                from datetime import datetime
                for fmt in ['%d %b %Y','%d/%m/%Y','%d-%m-%Y']:
                    try:
                        dt = datetime.strptime(jld, fmt)
                        if (dt.date() - date.today()).days <= 7: urgent_cls = ' urgent'
                        break
                    except: pass
            except: pass
        # Status badge
        jstatus = safe(job.get('status',''))
        status_badge = ''
        if jstatus:
            _smap = {
                'result_declared': ('#d1fae5','#065f46','Result Declared'),
                'admit_card_out':  ('#cffafe','#0e7490','Admit Card Out'),
                'answer_key_out':  ('#fef9c3','#854d0e','Answer Key Out'),
                'application_open':('#dbeafe','#1e40af','Apply Now'),
                'notification_out':('#ede9fe','#5b21b6','Notification Out'),
                'admission_open':  ('#fce7f3','#9d174d','Admission Open'),
            }
            if jstatus in _smap:
                _bg, _cl, _lb = _smap[jstatus]
                status_badge = f'<span class="jm-badge" style="background:{_bg};color:{_cl}">{_lb}</span>'
        cards_html += f'''<article class="job-card" data-title="{e(jtitle.lower())}" data-org="{e(jorg.lower())}">
  <div class="job-card-title"><a href="/jobs/{e(jslug)}/">{e(jtitle)}</a></div>
  <div class="job-card-org"><i class="fa-regular fa-building"></i> {e(jorg[:60])}</div>
  <div class="job-card-meta">
    {f'<span class="jm-badge" style="background:#dcfce7;color:#15803d">{e(jvac)} Posts</span>' if jvac else ''}
    <span class="jm-badge" style="background:#ede9fe;color:#5b21b6">{e(jmode)}</span>
    {status_badge}
  </div>
  {f'<div class="job-card-date{urgent_cls}"><i class="fa-regular fa-clock"></i> Last Date: <strong>{e(jld)}</strong></div>' if jld else ''}
  {f'<div class="job-card-links">{ql}</div>' if ql else ''}
</article>'''

    if not cards_html:
        cards_html = '<div style="padding:30px;text-align:center;color:#94a3b8"><i class="fa-solid fa-inbox" style="font-size:1.5rem;display:block;margin-bottom:8px"></i>No records found.</div>'

    filter_js = ('<script>function filterJobs(q){'
                 'q=q.toLowerCase().trim();'
                 'var cards=document.querySelectorAll(".job-card");'
                 'for(var i=0;i<cards.length;i++){'
                 'var t=cards[i].dataset.title||"",o=cards[i].dataset.org||"";'
                 'cards[i].style.display=(!q||t.includes(q)||o.includes(q))?"":"none";}}'
                 '</script>')

    body = (f'<div class="cat-wrap">'
            f'<h1 class="cat-h1" style="margin:12px 10px 4px">{e(title)}</h1>'
            f'<p class="cat-count" style="margin:0 10px 12px;color:#64748b;font-size:.78rem">{len(jobs)} records</p>'
            f'<div class="search-bar" style="margin:0 10px 12px">'
            f'<input type="search" placeholder="Search..." aria-label="Search" onkeyup="filterJobs(this.value)" autocomplete="off"/>'
            f'</div><div id="jobList" style="padding:0 10px">{cards_html}</div></div>'
            f'{filter_js}')

    return f'''<!DOCTYPE html>
<html lang="en-IN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{e(title_tag[:60])}</title>
<meta name="description" content="{e(meta_desc)}"/>
<meta name="robots" content="index,follow"/>
<link rel="canonical" href="{e(canon_url)}"/>
<meta property="og:title" content="{e(title_tag[:60])}"/>
<meta property="og:url" content="{e(canon_url)}"/>
{schemas_tag}
<script src="/tsj-config.js"></script>
<link rel="icon" href="/image.ico"/>
<link rel="stylesheet" href="/styles.css"/>
<link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/>
<noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>
<link rel="manifest" href="/manifest.json"/>
<meta name="theme-color" content="#0d2257"/>
<script src="/analytics.js" defer></script>
<link rel="stylesheet" href="/styles-detail.css" media="print" onload="this.media='all'"/><noscript><link rel="stylesheet" href="/styles-detail.css"/></noscript>
</head>
<body>
<div id="headerPlaceholder"></div>
<script src="/tsj-init.js?v={ASSET_VER}"></script>
<main id="main">{bc_html}{body}</main>
<div id="footerPlaceholder"></div>
<script src="/tsj-footer-init.js?v={ASSET_VER}"></script>
<script src="/tsj-menu.js?v={ASSET_VER}" defer></script>
</body>
</html>'''

# ═══════════════════════════════════════════════════════════════
# LOAD JSON DATA
# ═══════════════════════════════════════════════════════════════
print("Loading JSON data...")
_load_first_seen(ROOT)   # C1: load persisted datePosted map
with open(CJ_FILE, encoding='utf-8') as f: CJ = json.load(f)
with open(DU_FILE, encoding='utf-8') as f: DU = json.load(f)
# Inject slug field into DU items (for script.js buildSectionCard)
import hashlib as _hlib2
for _dsec in DU.get('sections', []):
    for _dit in _dsec.get('items', []):
        _dn = (_dit.get('name') or '').strip()
        _du = (_dit.get('url') or '').strip()
        if _dn and 'slug' not in _dit:
            _ds = slugify(_dn)
            if not _ds:
                _dom = re.sub(r'https?://(www\.)?','',_du).split('/')[0].replace('.','-')[:20]
                _h = _hlib2.md5(_dn.encode()).hexdigest()[:8]
                _ds = f"{_dom}-{_h}" if _dom else f"item-{_h}"
            _dit['slug'] = _ds[:80]
# Save updated dailyupdates.json with slugs
with open(DU_FILE, 'w', encoding='utf-8') as _f:
    json.dump(DU, _f, ensure_ascii=False, separators=(',',':'))

FJA_RAW = CJ.get('freejobalert_categories', {})
FJA     = {cat: [j for j in jobs if not is_garbage_title(
               (j.get('basic_details') or {}).get('job_title','') or j.get('title',''))]
           for cat, jobs in FJA_RAW.items() if isinstance(jobs, list)}
SARK    = [j for j in (CJ.get('sarkari_data',{}) or {}).get('jobs', []) if not is_garbage_title(j.get('title',''))]
EDU_SEC = (CJ.get('education_jobs',{}) or {}).get('sections', [])
SJ_SEC  = (CJ.get('state_jobs',{}) or {}).get('sections', [])
DU_SECS = DU.get('sections', [])

STATE_SLUG_FIX = {
    'andaman-and-nicobar':'andaman-nicobar','dadra-and-nagar-haveli':'dadra-nh',
    'daman-and-diu':'daman-diu','jammu-and-kashmir':'jk',
}

# Track slugs to avoid duplicates
seen_jobs    = {}  # slug → source
jobs_index   = {}  # for jobs-index.json
sindex       = {}  # for sections-index.json

j_count = s_count = e_count = c_count = sec_count = qual_count = 0

# ─────────────────────────────────────────────────────────────
# 1. JOB DETAIL PAGES — freejobalert_categories
# ─────────────────────────────────────────────────────────────
print("Generating /jobs/ pages (FJA categories)...")
for cat, jobs_list in FJA.items():
    if not isinstance(jobs_list, list): continue
    cat_slug  = QUAL_SLUG.get(cat, slugify(cat))
    cat_label = QUAL_LABEL.get(cat, cat.replace('_',' ').title())
    for job in jobs_list:
        bd = job.get('basic_details', {}) or {}
        title = safe(bd.get('job_title',''))
        if not title: continue
        slug = slugify(title)
        if slug in seen_jobs: slug = f"{slug}-{cat_slug}"[:80]
        seen_jobs[slug] = cat; job['category'] = cat
        canon = f"{BASE_URL}/jobs/{slug}/"
        # R9 FIX: Breadcrumb uses correct qualification hierarchy
        _bc_lbl, _bc_url = get_best_bc_category(cat, job)
        bc    = [('Study Wise', f"{BASE_URL}/category/study/"),
                 (_bc_lbl, f"{BASE_URL}{_bc_url}")]
        write(str(ROOT/'jobs'/slug/'index.html'), build_detail_page(job, slug, canon, bc, cat_label))
        # Save data JSON
        (ROOT/'jobs'/'data').mkdir(exist_ok=True)
        with open(ROOT/'jobs'/'data'/f"{slug}.json",'w',encoding='utf-8') as f:
            json.dump(job, f, ensure_ascii=False, separators=(',',':'))
        dt = job.get('important_dates',{}) or {}
        ld = safe(dt.get('last_date_to_apply',''))
        jobs_index[slug] = {'cat':cat,'title':title[:120],'last_date':ld[:30]}
        j_count += 1

print(f"  FJA jobs: {j_count}")

# 2. JOB DETAIL PAGES — sarkari_data
print("Generating /jobs/ pages (sarkari_data)...")
for job in SARK:
    title = safe(job.get('title',''))
    if not title: continue
    raw_slug = job.get('slug','') or ''
    slug = clean_slug(raw_slug) if raw_slug.strip() else slugify(title)
    if not slug or slug in seen_jobs: continue
    seen_jobs[slug] = job.get('category','')

    # Build important_links from all sources
    il = {}
    raw_il = job.get('important_links') or {}
    if isinstance(raw_il, dict):
        for k, v in raw_il.items():
            if v and not is_blocked(str(v)): il[k] = v
    for field, key in [
        ('apply_online_link',            'apply_online'),
        ('official_notification_pdf_link','notification_pdf'),
        ('official_website_link',        'official_website'),
        ('form_pdf_link',                'notification_pdf'),
        ('form_pdf_free_link',           'application_form'),   # OFFLINE_FORM free application PDF
        ('application_form_pdf_link',    'application_form'),   # OFFLINE_FORM application form
    ]:
        v = str(job.get(field,'') or '').strip()
        if v and v.startswith('http') and not is_blocked(v) and key not in il: il[key] = v
    useful = job.get('useful_links') or []
    if isinstance(useful, list):
        for lnk in useful:
            if not isinstance(lnk, dict): continue
            href = lnk.get('links') or lnk.get('url') or ''
            if isinstance(href, list): href = href[0] if href else ''
            href = str(href or '').strip()
            lbl = (lnk.get('title') or '').lower()
            if not href.startswith('http') or is_blocked(href): continue
            k = ('apply_online' if 'apply' in lbl else 'notification_pdf' if any(x in lbl for x in ['notif','pdf']) else 'result_link' if 'result' in lbl else 'admit_card' if 'admit' in lbl else 'answer_key' if 'answer' in lbl else 'official_website' if 'official' in lbl else 'click_here')
            if k not in il: il[k] = href

    # Build sections from all possible sources
    sections_out = job.get('sections') or []
    dpc = job.get('details_page_content') or {}
    if isinstance(dpc, dict) and not sections_out:
        paragraphs = [strip_html(str(p)) for p in (dpc.get('paragraphs') or []) if p]
        tables = [t for t in (dpc.get('tables') or []) if isinstance(t, list)]
        blocks = ([{'type':'paragraph','text':p} for p in paragraphs if p] +
                  [{'type':'table','rows':t} for t in tables])
        if blocks: sections_out = [{'title':'','content':blocks}]
    # Handle tables field (SR_Latest_Jobs/SR_Result format)
    # NOTE: raw_tables are NOT pushed into sections_out — they go via 'tables' key
    # in SECTION_ORDER so their position (after qualification, before useful_links) is controlled

    _vac_d = job.get('vacancy_details') or {}
    _total_vac = safe(job.get('total_vacancy','') or job.get('total_post','') or
                      (_vac_d.get('total_post','') if isinstance(_vac_d, dict) else ''))
    _apply_mode = safe(job.get('apply_mode',''))
    # OFFLINE_FORM category = always Offline, even if apply_mode field says otherwise
    if job.get('category') == 'OFFLINE_FORM':
        _apply_mode = 'Offline'
    elif not _apply_mode:
        _apply_mode = 'Online'
    bd = {'job_title':title,'organization_name':safe(job.get('organization','') or job.get('board_name','')),'post_name':safe(job.get('post_name','')),'total_vacancies':_total_vac,'application_mode':_apply_mode,'job_location':safe(job.get('job_location','') or job.get('state','') or 'India'),'short_information':strip_html(safe(job.get('short_information','') or job.get('jobs_info',''))),'last_updated':safe(job.get('post_date','') or job.get('listing_date','')),'job_type':safe(job.get('entry_type',''))}
    imp_dates = {}
    raw_d = job.get('important_dates') or {}
    if isinstance(raw_d, dict): imp_dates.update({k:v for k,v in raw_d.items() if v})
    age = {}
    if job.get('minimum_age'): age['minimum_age'] = safe(job['minimum_age'])
    if job.get('maximum_age'): age['maximum_age'] = safe(job['maximum_age'])
    # Merge age_limit dict (has minimum_age, maximum_age, as_on_date)
    age_obj = job.get('age_limit') or {}
    if isinstance(age_obj, dict):
        for k,v in age_obj.items():
            if v and k not in age: age[k] = safe(v)
    # Extract as_on_date hint from table_name (e.g. "Age Limit as on 01/01/2026 ...")
    if not age.get('as_on_date'):
        for tbl in (job.get('tables') or []):
            tname = safe(tbl.get('table_name',''))
            m = re.search(r'as\s+on\s+(\d{1,2}/\d{1,2}/\d{4})', tname, re.I)
            if m:
                age['as_on_date'] = m.group(1)
                break
    full = {'basic_details':bd,'important_dates':imp_dates,'application_fee':job.get('application_fees') or job.get('application_fee') or {},'age_limit':age,'qualification':job.get('eligibility') or job.get('qualification') or {},'vacancy_details':job.get('vacancy_details') or [],'salary_details':{'pay_scale':safe(job.get('salary_pay_scale',''))} if job.get('salary_pay_scale') else {},'how_to_apply':[job['how_to_apply']] if isinstance(job.get('how_to_apply'),str) and job.get('how_to_apply') else (job.get('how_to_apply') or []),'important_links':il,'sections':sections_out,'faq':job.get('faq') or [],'category':job.get('category',''),'slug':slug,
             'tables':job.get('tables') or [],'text_sections':job.get('text_sections') or [],'useful_links':job.get('useful_links') or [],'all_links':job.get('all_links') or [],'details_page_content':job.get('details_page_content') or {}}
    canon = f"{BASE_URL}/jobs/{slug}/"
    bc    = [('Latest Jobs', f"{BASE_URL}/section/latest-jobs/")]
    write(str(ROOT/'jobs'/slug/'index.html'), build_detail_page(full, slug, canon, bc))
    ld = safe(imp_dates.get('last_date_to_apply','') or imp_dates.get('last_date',''))
    jobs_index[slug] = {'cat':job.get('category',''),'title':title[:120],'last_date':ld[:30]}
    j_count += 1

print(f"  All /jobs/: {j_count}")

# 3. STATE PAGES
print("Generating /state/ pages...")
for sec in SJ_SEC:
    state_name = safe(sec.get('state') or sec.get('title',''))
    raw_state_slug = slugify(state_name)
    state_slug = STATE_SLUG_FIX.get(raw_state_slug, raw_state_slug)
    for item in sec.get('items', []):
        name = safe(item.get('name','') or item.get('title',''))
        if not name: continue
        item_slug = slugify(name)[:80]
        detail = item.get('detail') or {}
        if isinstance(detail, str):
            try: detail = json.loads(detail)
            except: detail = {}
        if not detail.get('basic_details'):
            detail['basic_details'] = {}
        bd2 = detail['basic_details']
        if not bd2.get('job_title'): bd2['job_title'] = name
        if not bd2.get('job_location'): bd2['job_location'] = f"{state_name}, India"
        if not detail.get('important_dates'): detail['important_dates'] = {}
        if item.get('lastDate') and not detail['important_dates'].get('last_date_to_apply'):
            detail['important_dates']['last_date_to_apply'] = item['lastDate']
        detail['source_url'] = safe(item.get('url',''))
        detail['category'] = state_name

        canon = f"{BASE_URL}/jobs/{item_slug}/"
        bc    = [('State Jobs', f"{BASE_URL}/state-jobs/{state_slug}/"), (state_name, f"{BASE_URL}/state-jobs/{state_slug}/")]
        # State detail pages: noindex (canonical → /jobs/) to avoid duplicate indexing
        # Single URL rule: only /jobs/{slug}/ — no /state/{state}/{slug}/
        if item_slug not in seen_jobs:
            seen_jobs[item_slug] = state_name
            jobs_html = build_detail_page(detail, item_slug, canon, bc, f'{state_name} Govt Job', noindex_dup=False)
            write(str(ROOT/'jobs'/item_slug/'index.html'), jobs_html)
        s_count += 1

# Generate /state/{state-slug}/index.html listing pages
for sec in SJ_SEC:
    state_name = safe(sec.get('state') or sec.get('title',''))
    raw_state_slug = slugify(state_name)
    state_slug = STATE_SLUG_FIX.get(raw_state_slug, raw_state_slug)
    if not state_name or not state_slug: continue
    state_jobs_list = sec.get('items', [])
    if not state_jobs_list: continue
    canon_listing = f"{BASE_URL}/state/{state_slug}/"
    # Build simple listing page for /state/{slug}/
    state_listing = build_listing_page(
        f"{state_name} Government Jobs {YEAR}",
        [{'basic_details':{'job_title':safe(it.get('name') or it.get('title','')),'organization_name':state_name,
          'total_vacancies':safe(it.get('total_vacancy',''))}}
         for it in state_jobs_list if (it.get('name') or it.get('title',''))],
        canon_listing,
        [('Home','/'),('State Jobs','/state-jobs/')],
        f"Latest {state_name} government jobs {YEAR}. All sarkari naukri for {state_name} state."
    )
    write(str(ROOT/'state'/state_slug/'index.html'), state_listing)

print(f"  State pages: {s_count}")

# 4. EDUCATION PAGES
print("Generating /education/ pages...")
for sec in EDU_SEC:
    sec_id    = safe(sec.get('id','') or sec.get('title',''))
    sec_title = safe(sec.get('title','') or sec_id)
    if not sec_id: continue
    # Merge duplicate slugs
    slug_map = {}
    for item in sec.get('items', []):
        name = safe(item.get('name','') or item.get('examName',''))
        if not name: continue
        item_slug = slugify(name)[:80]
        detail = item.get('detail') or {}
        if item_slug not in slug_map:
            slug_map[item_slug] = {'basic_details':{'job_title':detail.get('title') or name,'organization_name':sec_title,'job_location':sec_title,'short_information':detail.get('short_info',''),'last_updated':safe(item.get('postDate') or item.get('date',''))},'important_dates':{'notification_date':safe(item.get('date') or item.get('postDate',''))},'important_links':{},'sections':[],'faq':[],'source_url':safe(item.get('url','')),'category':sec_title}
        fd = slug_map[item_slug]
        new_il = detail.get('important_links') or {}
        if isinstance(new_il, dict):
            for k, v in new_il.items():
                if k == 'structured_links':
                    fd['important_links']['structured_links'] = fd['important_links'].get('structured_links',[]) + (v if isinstance(v,list) else [])
                elif k not in fd['important_links']:
                    fd['important_links'][k] = v
        new_secs = detail.get('sections') or []
        if len(new_secs) > len(fd['sections']): fd['sections'] = new_secs

    for item_slug, full_d in slug_map.items():
        canon = f"{BASE_URL}/jobs/{item_slug}/"
        bc    = [('Education', f"{BASE_URL}/education/"), (sec_title, f"{BASE_URL}/education/{sec_id}/")]
        html  = build_detail_page(full_d, item_slug, canon, bc, sec_title)
        # Education pages: noindex (canonical → /jobs/) 
        # Single URL rule: only /jobs/{slug}/ — no /education/{state}/{slug}/
        if item_slug not in seen_jobs:
            seen_jobs[item_slug] = sec_title
            jobs_html = build_detail_page(full_d, item_slug, canon, bc, sec_title, noindex_dup=False)
            write(str(ROOT/'jobs'/item_slug/'index.html'), jobs_html)
        e_count += 1

    # Listing page
    edu_jobs = [{'basic_details':{'job_title':safe(it.get('name') or it.get('examName','')),'organization_name':sec_title,'application_mode':'Online','job_location':sec_title,'last_updated':safe(it.get('postDate') or it.get('date',''))},'important_dates':{'notification_date':safe(it.get('date') or it.get('postDate',''))},'important_links':(it.get('detail') or {}).get('important_links') or {},'category':sec_title} for it in sec.get('items',[]) if it.get('name') or it.get('examName')]
    if edu_jobs:
        write(str(ROOT/'education'/sec_id/'index.html'), build_listing_page(f"{sec_title} Education Updates", edu_jobs, f"{BASE_URL}/education/{sec_id}/", [('Education','/education/')]))

print(f"  Education pages: {e_count}")

# 5. CATEGORY/STUDY PAGES
print("Generating /category/study/ pages...")
_cat_listing_jobs = {}  # cat_slug → list of jobs (for listing page)
for cat, jobs_list in FJA.items():
    if not isinstance(jobs_list, list): continue
    cat_slug  = QUAL_SLUG.get(cat, slugify(cat))
    cat_label = QUAL_LABEL.get(cat, cat.replace('_',' ').title())
    if cat_slug not in _cat_listing_jobs:
        _cat_listing_jobs[cat_slug] = {'label': cat_label, 'jobs': []}
    for job in jobs_list:
        bd = job.get('basic_details',{}) or {}
        title = safe(bd.get('job_title',''))
        if not title: continue
        item_slug = slugify(title)[:80]
        canon = f"{BASE_URL}/category/study/{cat_slug}/{item_slug}/"
        bc    = [('Study Wise Jobs', f"{BASE_URL}/category/study/"), (f'{cat_label} Jobs', f"{BASE_URL}/category/study/{cat_slug}/")]
        _canon_j = f"{BASE_URL}/jobs/{item_slug}/"  # canonical always points to /jobs/
        # Category detail pages removed — /jobs/{slug}/ is the canonical URL
        _cat_listing_jobs[cat_slug]['jobs'].append(job)
        c_count += 1

# Generate category LISTING pages (index.html for each category)
print("Generating /category/study/{slug}/ listing pages...")
_listing_count = 0
for cat_slug, cat_data in _cat_listing_jobs.items():
    cat_label = cat_data['label']
    jobs = cat_data['jobs']
    if not jobs: continue
    cat_canon = f"{BASE_URL}/category/study/{cat_slug}/"
    bc_listing = [('Home', '/'), ('Study Wise Jobs', '/category/study/')]
    listing_html = build_listing_page(
        f"{cat_label} Government Jobs {YEAR}",
        jobs,
        cat_canon,
        bc_listing,
        f"Latest {cat_label} government job notifications {YEAR}. Find all sarkari naukri for {cat_label} candidates updated daily."
    )
    write(str(ROOT/'category'/'study'/cat_slug/'index.html'), listing_html)
    _listing_count += 1

print(f"  Category/study detail pages: {c_count}")
print(f"  Category/study listing pages: {_listing_count}")

# Rebuild Qualification_Wise_Jobs.json (the /category/study/ index page fetches this).
# ids MUST equal the generated /category/study/<slug>/ folder slugs so links resolve.
# Exclude non-qualification buckets (these belong to /section/, not study-wise).
_NON_STUDY = {'railway-jobs','bank-jobs','police-defence','medical-hospital',
              'teaching-faculty','latest-jobs','last-date-reminder'}
_qual_sections = []
for cat_slug, cat_data in _cat_listing_jobs.items():
    if cat_slug in _NON_STUDY: continue
    jobs = cat_data.get('jobs', [])
    if not jobs: continue
    _items = []
    for j in jobs:
        bd = j.get('basic_details', {}) or {}
        t = safe(bd.get('job_title', '') or j.get('title', ''))
        if not t: continue
        _items.append({'name': t, 'slug': slugify(t)[:80]})
    if not _items: continue
    _qual_sections.append({
        'id': cat_slug,
        'qualification': cat_data.get('label', cat_slug.replace('-', ' ').title()),
        'items': _items,
    })
with open(ROOT / 'Qualification_Wise_Jobs.json', 'w', encoding='utf-8') as _qf:
    json.dump({'sections': _qual_sections}, _qf, ensure_ascii=False, separators=(',', ':'))
print(f"  Qualification_Wise_Jobs.json: {len(_qual_sections)} sections")

# 6. SECTION LISTING PAGES
print("Generating /section/ pages...")
SARK_CAT_MAP = {
    'SR_Latest_Jobs':  'latest-jobs',
    'SR_Result':       'results',
    'SR_Admit_Card':   'admit-card',
    'SR_Admission':    'admission',
    'SR_Answer_Key':   'answer-key',
    'OFFLINE_FORM':    'offline-form',
    'LATEST_JOBS NEW': 'latest-jobs',
    'UPCOMING_JOBS':   'upcoming-jobs',
    'STATE_JOBS':      'latest-jobs',
    'CENTRAL_JOBS':    'latest-jobs',
    'ADMISSIONS':      'admission',
}
FJA_CAT_MAP = {
    '10TH_Pass':           '10th-pass-jobs',
    '8TH_Pass':            '8th-pass',
    '12TH_Pass':           '12th-pass-jobs',
    'Diploma':             'diploma-jobs',
    'ITI':                 'iti-jobs',
    'B_Tech_BE':           'btech-jobs',
    'B_Com':               'ba-pass',
    'Any_Graduate':        'graduation-jobs',
    'Any_Post_Graduate':   'post-graduation-jobs',
    'Railway_Jobs':        'railway-jobs',
    'Police_Defence':      'police-jobs',
    'Teaching_Faculty':    'teaching-jobs',
    'Bank_Jobs':           'bank-jobs',
    'Medical_Hospital':    'healthcare-jobs',
    'Last_Date_Reminder':  'last-date-reminder',
    'Latest_Notifications':'latest-notifications',
}
for cat_key, url_slug in FJA_CAT_MAP.items():
    jobs = FJA.get(cat_key,[])
    if not isinstance(jobs, list): continue
    lbl = QUAL_LABEL.get(cat_key, cat_key.replace('_',' ').title())
    write(str(ROOT/'section'/url_slug/'index.html'), build_listing_page(f"{lbl}", jobs, f"{BASE_URL}/section/{url_slug}/", []))
    sec_count += 1

for cat_key, url_slug in SARK_CAT_MAP.items():
    sark_jobs = [j for j in SARK if j.get('category') == cat_key]
    if not sark_jobs: continue
    norm = []
    for j in sark_jobs:
        if not j.get('title'): continue
        _imp = j.get('important_dates') or {}
        _last_d = safe(_imp.get('last_date_to_apply','') or _imp.get('last_date','') or j.get('last_date',''))
        _il = j.get('important_links') or {}
        _ul = j.get('useful_links') or {}
        # Merge useful_links keys into important_links for quick buttons
        if isinstance(_ul, dict):
            for _k in ['apply_online','result','result_link','admit_card','notification','notification_pdf','official_website','answer_key','admit']:
                if _ul.get(_k) and not _il.get(_k): _il[_k] = _ul[_k]
            # map 'result' → 'result_link' for uniform access
            if _ul.get('result') and not _il.get('result_link'): _il['result_link'] = _ul['result']
            if _ul.get('answer_key') and not _il.get('answer_key'): _il['answer_key'] = _ul['answer_key']
            # _all array → extract known keys
            for _item in (_ul.get('_all') or []):
                _t = safe(_item.get('title','')).lower()
                _lnk = _item.get('links','')
                if isinstance(_lnk, list): _lnk = _lnk[0] if _lnk else ''
                _lnk = safe(_lnk)
                if not _lnk: continue
                if 'result' in _t or 'score card' in _t:
                    if not _il.get('result_link'): _il['result_link'] = _lnk
                elif 'admit' in _t or 'hall ticket' in _t:
                    if not _il.get('admit_card'): _il['admit_card'] = _lnk
                elif 'apply' in _t:
                    if not _il.get('apply_online'): _il['apply_online'] = _lnk
                elif 'notification' in _t:
                    if not _il.get('notification_pdf'): _il['notification_pdf'] = _lnk
        norm.append({
            'basic_details': {
                'job_title': safe(j.get('title','')),
                'organization_name': safe(j.get('organization','')),
                'total_vacancies': safe(j.get('total_post','') or j.get('total_vacancy','')),
                'application_mode': safe(j.get('apply_mode','')) or ('Offline' if j.get('entry_type') == 'OFFLINE' else 'Online'),
                'job_location': 'India',
            },
            'important_dates': _imp,
            'last_date': _last_d,
            'important_links': _il,
            'useful_links': j.get('useful_links') or {},
            '_slug': safe(j.get('slug','')),
            'category': cat_key,
            'status': safe(j.get('status','')),
        })
    lbl = cat_key.replace('_',' ').replace('SR ','').title()
    write(str(ROOT/'section'/url_slug/'index.html'), build_listing_page(lbl, norm, f"{BASE_URL}/section/{url_slug}/", []))
    sec_count += 1

# DAILYUPDATES INDIVIDUAL ITEM PAGES → /jobs/{slug}/
# Proper pages with header/footer + auto-redirect to external URL
import hashlib as _hlib
print("Generating dailyupdates detail pages...")
print(f"  DU_SECS: {len(DU_SECS)} sections, items: {sum(len(s.get(chr(105)+chr(116)+chr(101)+chr(109)+chr(115),[])) for s in DU_SECS)}")
_DU_SEC_META = {
    'Govt Scheme & Yojna':{'color':'#065f46','icon':'🏛️','badge':'Govt Scheme'},
    'ImportantCSC PDF':   {'color':'#7c3aed','icon':'📄','badge':'PDF Download'},
    'ImportantCSC link':  {'color':'#1d4ed8','icon':'🔗','badge':'Useful Link'},
    'Today Updates':      {'color':'#b45309','icon':'📰','badge':'Today Update'},
}
_du_count = 0
_du_seen  = set()

def _du_slug(name, url=''):
    s = slugify(name)
    if s: return s
    # Hindi or empty: use url domain + md5 hash
    dom = re.sub(r'https?://(www\.)?','',url).split('/')[0].replace('.','-')[:20]
    h   = _hlib.md5(name.encode()).hexdigest()[:8]
    return f"{dom}-{h}" if dom else f"item-{h}"

def _du_page(name, url, sec_title, other_items):
    meta   = _DU_SEC_META.get(sec_title, {'color':'#1d4ed8','icon':'\U0001f4cb','badge':sec_title})
    is_pdf = 'drive.google.com' in url or url.lower().endswith('.pdf')
    btn_ic = 'fa-file-pdf' if is_pdf else 'fa-arrow-up-right-from-square'
    btn_cl = 'btn-pdf' if is_pdf else 'btn-default'
    btn_tx = 'Download PDF' if is_pdf else 'Open Official Link'
    sec_sl = slugify(sec_title)
    slug   = _du_slug(name, url)
    canon  = BASE_URL + '/jobs/' + slug + '/'
    clr    = meta['color']

    bc = (
        '<nav class="bc" aria-label="Breadcrumb">'
        + '<a href="/">Home</a><span class="bc-sep">\u203a</span>'
        + '<a href="/section/' + e(sec_sl) + '/">' + e(sec_title) + '</a>'
        + '<span class="bc-sep">\u203a</span>'
        + '<span aria-current="page">' + e(name[:60]) + '</span>'
        + '</nav>'
    )
    card_hd = (
        '<div style="background:linear-gradient(135deg,' + clr + ',#1e3a8a);'
        + 'border-radius:12px 12px 0 0;padding:18px 20px 16px;color:#fff;">'
        + '<div style="margin-bottom:10px;">'
        + '<span style="background:rgba(255,255,255,.18);padding:3px 10px;border-radius:20px;'
        + 'font-size:.75rem;font-weight:700;">'
        + e(meta['icon']) + ' ' + e(meta['badge']) + '</span>'
        + '</div>'
        + '<h1 style="font-size:1.05rem;font-weight:900;margin:0 0 10px;line-height:1.4;">'
        + e(name) + '</h1>'
        + '<div style="font-size:.76rem;opacity:.88;">\U0001f4c2 ' + e(sec_title) + '</div>'
        + '</div>'
    )
    card_bd = (
        '<div style="background:#fff;border-radius:0 0 12px 12px;'
        + 'border:1px solid #e2e8f0;border-top:none;padding:16px 18px;">'
        + '<a href="' + e(url) + '" class="lnk-btn ' + btn_cl + '" target="_blank" rel="noopener noreferrer" '
        + 'style="display:flex;align-items:center;justify-content:center;gap:8px;'
        + 'width:100%;padding:12px 18px;font-size:.9rem;font-weight:800;margin-bottom:10px;">'
        + '<i class="fa-solid ' + btn_ic + '"></i> ' + e(btn_tx) + ' \u2197'
        + '</a>'
        + '<a href="/" style="display:flex;align-items:center;justify-content:center;'
        + 'background:#f1f5f9;color:#374151;padding:9px 18px;border-radius:8px;'
        + 'font-size:.82rem;font-weight:600;text-decoration:none;border:1px solid #e2e8f0;">'
        + '\u2190 Back to Home</a>'
        + '</div>'
    )
    others = ''
    for oi in [i for i in (other_items or []) if (i.get('name') or '').strip()][:6]:
        on  = (oi.get('name') or '').strip()[:80]
        ou  = (oi.get('url') or '').strip()
        osl = _du_slug(on, ou)
        others += '<li class="sec-item"><a href="/jobs/' + osl + '/">' + e(on) + '</a></li>'
    if others:
        others = (
            '<section class="sec-card" style="margin-top:16px;">'
            + '<div class="sec-head"><div class="left">MORE FROM ' + e(sec_title).upper() + '</div></div>'
            + '<div class="sec-body"><ul class="sec-list">' + others + '</ul></div>'
            + '</section>'
        )

    tl = e(name[:60]) + ' | Top Sarkari Jobs'
    md = e((name[:130] + ' - ' + sec_title + '. Top Sarkari Jobs.')[:155])

    lines = [
        '<!DOCTYPE html>', '<html lang="en-IN">', '<head>',
        '<meta charset="UTF-8"/>',
        '<meta name="viewport" content="width=device-width,initial-scale=1.0"/>',
        '<title>' + tl + '</title>',
        '<meta name="description" content="' + md + '"/>',
        '<meta name="robots" content="noindex,follow"/>',
        '<link rel="canonical" href="' + e(canon) + '"/>',
        '<link rel="icon" href="/image.ico"/>',
        '<link rel="stylesheet" href="/styles.css"/>',
        '<link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel=\'stylesheet\'"/>',
        '<noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>',
        '<link rel="stylesheet" href="/styles-detail.css" media="print" onload="this.media=\'all\'"/>',
        '<noscript><link rel="stylesheet" href="/styles-detail.css"/></noscript>',
        '<script src="/tsj-config.js"></script>',
        '</head>', '<body>',
        '<div id="headerPlaceholder"></div>',
        '<script src="/tsj-init.js?v=' + ASSET_VER + '"></script>',
        '<main id="main">',
        '<div style="max-width:680px;margin:0 auto;padding:12px 10px 60px;">',
        bc,
        '<div class="important-notice"><i class="fa-solid fa-circle-exclamation"></i>'
        + '<span><strong>Important:</strong> Always verify details on official website. '
        + 'Dates &amp; eligibility may change.</span></div>',
        '<div style="border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.07);margin-bottom:14px;">',
        card_hd, card_bd,
        '</div>',
        others,
        '</div>', '</main>',
        '<div id="footerPlaceholder"></div>',
        '<script src="/tsj-footer-init.js?v=' + ASSET_VER + '"></script>',
        '<script src="/tsj-menu.js?v=' + ASSET_VER + '" defer></script>',
        '</body>', '</html>',
    ]
    return '\n'.join(lines)


# ── DU loop ─────────────────────────────────────────────────────
for _du_sec in DU_SECS:
    _du_st   = _du_sec.get('title','')
    _du_items = _du_sec.get('items', [])
    for _du_item in _du_items:
        _du_name = (_du_item.get('name') or '').strip()
        _du_url  = (_du_item.get('url') or '').strip()
        if not _du_name or not _du_url or not _du_url.startswith('http'):
            continue
        _du_sl = _du_slug(_du_name, _du_url)
        if _du_sl in {'drive-google-com-dca2e21e','drive-google-com-97ed3afd','indiapost-gov-in-f03ec018'}:
            print(f'  DEBUG: found target {_du_sl}, in_seen={_du_sl in _du_seen}, sl_bool={bool(_du_sl)}')
        if not _du_sl or _du_sl in _du_seen:
            continue
        _du_seen.add(_du_sl)
        _du_path = ROOT/'jobs'/_du_sl/'index.html'
        if _du_path.exists():
            _ex = _du_path.read_text(encoding='utf-8')
            # Only skip if it's a real job page (has both important_dates AND application_fee)
            if 'important_dates' in _ex and 'application_fee' in _ex:
                continue
        _du_path.parent.mkdir(parents=True, exist_ok=True)
        _others = [i for i in _du_items if i != _du_item]
        _page_content = _du_page(_du_name, _du_url, _du_st, _others)
        write(str(_du_path), _page_content)
        if _du_sl in {"drive-google-com-dca2e21e","drive-google-com-97ed3afd","indiapost-gov-in-f03ec018"}: print(f"  TARGET written: {_du_path}")
        _du_count += 1

print(f"  Dailyupdates detail pages: {_du_count}")

# Explicit pass for items with non-Latin (Hindi/Unicode) names that hash-slug
for _du_sec2 in DU_SECS:
    _st2 = _du_sec2.get('title','')
    for _di2 in _du_sec2.get('items', []):
        _dn2 = (_di2.get('name') or '').strip()
        _du2 = (_di2.get('url') or '').strip()
        if not _dn2 or not _du2 or not _du2.startswith('http'): continue
        # Only process items with non-ASCII names (pure Hindi etc.)
        if all(ord(c) < 128 for c in _dn2): continue
        _sl2 = _du_slug(_dn2, _du2)
        if not _sl2: continue
        _dp2 = ROOT/'jobs'/_sl2/'index.html'
        if _dp2.exists():
            _ex2 = _dp2.read_text(encoding='utf-8')
            if 'important_dates' in _ex2 and 'application_fee' in _ex2:
                continue
        _dp2.parent.mkdir(parents=True, exist_ok=True)
        try:
            _others2 = [i for i in _du_sec2.get('items',[]) if i != _di2]
            write(str(_dp2), _du_page(_dn2, _du2, _st2, _others2))
            print(f"  Unicode page: {_sl2}")
        except Exception as _ue:
            print(f"  Unicode ERROR {_sl2}: {_ue}")

# ─────────────────────────────────────────────────────────────────
# 7. SECTION LISTING PAGES
# ─────────────────────────────────────────────────────────────────
print("Generating /section/ pages...")
SARK_CAT_MAP = {
    'SR_Latest_Jobs':'latest-jobs','SR_Result':'result','SR_Admit_Card':'admit-card',
    'SR_Admission':'admission','SR_Answer_Key':'answer-key','OFFLINE_FORM':'offline-form',
    'LATEST_JOBS NEW':'latest-jobs-new','UPCOMING_JOBS':'upcoming-jobs',
    'STATE_JOBS':'state-jobs-central','CENTRAL_JOBS':'central-jobs',
    'ADMISSIONS':'admissions',
}
sec_count2 = 0
# Sarkari sections
for cat_key, url_slug in SARK_CAT_MAP.items():
    jobs_in_cat = [j for j in SARK if j.get('category') == cat_key]
    if not jobs_in_cat: continue
    lbl = SECTION_META.get('important_links',('Important Links','',''))[0]
    lbl = {'SR_Latest_Jobs':'Latest Jobs','SR_Result':'Results','SR_Admit_Card':'Admit Cards',
           'SR_Admission':'Admissions','SR_Answer_Key':'Answer Keys','OFFLINE_FORM':'Offline Forms',
           'LATEST_JOBS NEW':'Latest Jobs New','UPCOMING_JOBS':'Upcoming Jobs',
           'STATE_JOBS':'State Jobs','CENTRAL_JOBS':'Central Govt Jobs','ADMISSIONS':'Admissions'}.get(cat_key, cat_key.replace('_',' ').title())
    norm2 = []
    for j in jobs_in_cat:
        if not j.get('title'): continue
        _imp2 = j.get('important_dates') or {}
        _last2 = (j.get('important_dates') or {}).get('last_date_apply_online','') or                  (j.get('important_dates') or {}).get('last_date_to_apply','') or                  (j.get('important_dates') or {}).get('last_date','') or                  j.get('last_date','')
        _il2 = {}
        _ul2 = j.get('useful_links') or {}
        if isinstance(_ul2, dict):
            for _k2 in ['apply_online','result','result_link','admit_card','notification','notification_pdf','answer_key']:
                if _ul2.get(_k2): _il2[_k2] = _ul2[_k2]
            if _ul2.get('result') and not _il2.get('result_link'): _il2['result_link'] = _ul2['result']
        _raw_slug2 = j.get('slug','')
        import re as _re3
        _clean_slug2 = _re3.sub(r'^sr_[a-z_]+-','', _raw_slug2) if _raw_slug2 else ''
        _clean_slug2 = _re3.sub(r'-[0-9a-f]{6,8}$','', _clean_slug2) if _clean_slug2 else ''
        norm2.append({
            'basic_details': {
                'job_title': j.get('title',''),
                'organization_name': j.get('organization',''),
                'total_vacancies': j.get('total_post','') or j.get('total_vacancy',''),
                'application_mode': j.get('apply_mode','') or ('Offline' if j.get('entry_type') == 'OFFLINE' else 'Online'),
                'job_location': 'India',
            },
            'important_dates': _imp2,
            'last_date': str(_last2),
            'important_links': _il2,
            '_slug': _clean_slug2 or j.get('slug',''),
            'status': j.get('status',''),
        })
    write(str(ROOT/'section'/url_slug/'index.html'), build_listing_page(lbl, norm2, f"{BASE_URL}/section/{url_slug}/", []))
    sec_count2 += 1

# DU sections (Govt Scheme, ImportantCSC PDF, ImportantCSC link, Today Updates …)
for sec in DU_SECS:
    sec_title = sec.get('title','')
    url_slug  = slugify(sec_title)
    items     = sec.get('items',[])
    if not url_slug or not items: continue
    norm = []
    for it in items:
        nm = it.get('name','') or it.get('title','')
        if not nm: continue
        # slugify(title) resolves to the generated /jobs/<slug>/ page more reliably
        # than the raw dailyupdates 'slug' field, so we let build_listing_page slugify.
        norm.append({'basic_details':{'job_title':nm}})
    write(str(ROOT/'section'/url_slug/'index.html'), build_listing_page(sec_title, norm, f"{BASE_URL}/section/{url_slug}/", []))
    sec_count2 += 1

# Top 20 Jobs — deliberate data source: the 20 most-recent latest jobs
# (no "Top 20" section exists in dailyupdates.json, so build it from latest jobs)
_top_src = [j for j in SARK if j.get('category') == 'SR_Latest_Jobs' and j.get('title')]
if not _top_src:
    _top_src = [j for j in SARK if j.get('title')]
_top20 = [{'basic_details':{'job_title':j.get('title',''),
           'organization_name':j.get('organization',''),
           'total_vacancies':j.get('total_post','')}} for j in _top_src[:20]]
if _top20:
    write(str(ROOT/'section'/'top-20-jobs'/'index.html'),
          build_listing_page('Top 20 Jobs', _top20, f"{BASE_URL}/section/top-20-jobs/", []))
    sec_count2 += 1

print(f"  Section pages: {sec_count2}")

# EXTRA section pages (matching cat-bar URLs in index.html)
_EXTRA_SEC = {
    'army-jobs':           ('Army & Defence Jobs',       ['Police_Defence'], []),
    'btech-jobs':          ('B.Tech / B.E. Jobs',        ['B_Tech_BE'],      []),
    'graduation-jobs':     ('Any Graduate Jobs',         ['Any_Graduate'],   []),
    'post-graduation-jobs':('Post Graduate Jobs',        ['Any_Post_Graduate'],[]),
    'healthcare-jobs':     ('Medical / Healthcare Jobs', ['Medical_Hospital'],[]),
    'results':             ('Results 2026',              [],         ['SR_Result']),
    '8th-pass':            ('8th Pass Jobs',             ['8TH_Pass'],       []),
    'ba-pass':             ('BA Pass / B.Com Jobs',      ['B_Com'],          []),
    'jobs-with-last-date': ('Jobs with Last Date',       ['Last_Date_Reminder'],[]),
    'latest-govt-jobs':    ('Latest Govt Jobs',          ['Latest_Notifications'],[]),
    # NOTE: top-20-jobs, govt-scheme-yojna, important-csc-pdf, importantcsc-link and
    # today-updates are built from dailyupdates.json in the "DU sections" loop above
    # with REAL data. Do NOT recreate them here with empty lists — that would
    # overwrite the populated pages with "0 records".
    'syllabus':            ('Syllabus & Study Material', [],                 []),
}
for _eslug, (_elbl, _efja, _esark) in _EXTRA_SEC.items():
    _ejobs = []
    for _ec in _efja:
        _items = FJA.get(_ec, [])
        if isinstance(_items, list): _ejobs.extend(_items)
    for _ec in _esark:
        _ejobs.extend([j for j in SARK if j.get('category') == _ec])
    _esl_html = '<ul class="sec-list">'
    for _ej in _ejobs[:50]:
        _ebd  = (_ej.get('basic_details') or {})
        _et   = safe(_ebd.get('job_title') or _ej.get('title',''))
        if not _et: continue
        _esl  = slugify(_et)[:80]
        _eld  = safe(_ebd.get('last_updated') or _ej.get('post_date',''))
        _esl_html += (f'<li class="sec-item"><a href="/jobs/{_esl}/">{e(_et[:90])}</a>'
                      + (f'<span class="sec-date">{e(_eld)}</span>' if _eld else '')
                      + '</li>')
    _esl_html += '</ul>' if _ejobs else '<p style="text-align:center;color:#94a3b8;padding:30px">No jobs found. Check back soon!</p>'
    _edir = ROOT/'section'/_eslug
    _edir.mkdir(parents=True, exist_ok=True)
    # Use build_listing_page for Image 2 style layout (cards with search)
    _enorm = []
    for _ej in _ejobs:
        _ebd = (_ej.get('basic_details') or {})
        _et  = safe(_ebd.get('job_title') or _ej.get('title',''))
        if not _et: continue
        _enorm.append({'basic_details':{
            'job_title':       _et,
            'organization_name':safe(_ebd.get('organization_name') or _ej.get('organization','')),
            'total_vacancies': safe(_ebd.get('total_vacancies') or _ej.get('total_post','')),
            'application_mode':safe(_ebd.get('application_mode') or _ej.get('apply_mode','Online')),
        },'important_dates': _ej.get('important_dates') or {}})
    write(str(_edir/'index.html'), build_listing_page(
        _elbl, _enorm,
        f'{BASE_URL}/section/{_eslug}/',
        [('Home','/')]
    ))

# ─────────────────────────────────────────────────────────────────
# 8. QUALIFICATION LISTING PAGES
# ─────────────────────────────────────────────────────────────────
print("Generating /qualification/ pages...")
q_count = 0
for cat_key, q_slug in QUAL_SLUG.items():
    q_label = QUAL_LABEL.get(cat_key, cat_key.replace('_',' ').title())
    jobs_q  = FJA.get(cat_key, [])
    if not jobs_q: continue
    norm = [{'basic_details':{'job_title':safe((j.get('basic_details',{}) or {}).get('job_title','')),'organization_name':safe((j.get('basic_details',{}) or {}).get('organization_name','')),'total_vacancies':safe((j.get('basic_details',{}) or {}).get('total_vacancies',''))}} for j in jobs_q]
    write(str(ROOT/'qualification'/q_slug/'index.html'), build_listing_page(f"{q_label} Government Jobs {YEAR}", norm, f"{BASE_URL}/qualification/{q_slug}/", [('Qualification Wise Jobs','/category/study/')]))
    q_count += 1

print(f"  Qualification pages: {q_count}")

# ─────────────────────────────────────────────────────────────────
# UPDATE JSON INDEXES
# ─────────────────────────────────────────────────────────────────
write(str(ROOT/'jobs-index.json'),   json.dumps(jobs_index, ensure_ascii=False, separators=(',',':')))

# Generate lightweight sarkari-mini.json for homepage (42KB vs 53MB)
_mini_jobs = []
for _mj in SARK:
    _mt = safe(_mj.get('title',''))
    if not _mt: continue
    _mini_jobs.append({
        'title': _mt,
        'slug':  slugify(_mt)[:80],
        'cat':   _mj.get('category',''),
        'date':  safe((_mj.get('important_dates') or {}).get('last_date','') or _mj.get('post_date',''))
    })
write(str(ROOT/'data'/'sarkari-mini.json'), json.dumps({'jobs':_mini_jobs}, ensure_ascii=False, separators=(',',':')))
print(f"  sarkari-mini.json: {len(_mini_jobs)} jobs")
# Build sections_index: FJA categories + SARK categories
sections_index = {}

# FJA categories
for _si_cat, _si_jobs in FJA.items():
    if not isinstance(_si_jobs, list): continue
    _si_items = []
    for _j in _si_jobs[:10]:  # top 10 per category (homepage shows max 10)
        _bd = (_j.get('basic_details') or {})
        _t  = safe(_bd.get('job_title',''))
        if not _t: continue
        _sl = slugify(_t)[:80]
        _imp = (_j.get('important_dates') or {})
        _ld  = safe(_imp.get('last_date_to_apply','') or _imp.get('last_date',''))
        _si_items.append({'slug':_sl,'name':_t,'date':_ld})
    if _si_items:
        sections_index[_si_cat] = _si_items

# SARK categories (SR_Result, LATEST_JOBS NEW, OFFLINE_FORM, etc.)
for _sj in SARK:
    _scat = _sj.get('category','')
    if not _scat: continue
    _st = safe(_sj.get('title',''))
    if not _st: continue
    _sl = slugify(_st)[:80]
    _ld = safe((_sj.get('important_dates') or {}).get('last_date','') or _sj.get('last_date',''))
    if _scat not in sections_index:
        sections_index[_scat] = []
    if len(sections_index[_scat]) < 10:
        sections_index[_scat].append({'slug':_sl,'name':_st,'date':_ld})

# UPCOMING_JOBS: populate from jobs with future exam_date or application_begin
import datetime as _dt
_today_str = _dt.date.today().strftime('%d/%m/%Y')
_today = _dt.date.today()

def _parse_date(s):
    """Try common date formats, return date or None."""
    if not s: return None
    s = str(s).strip()
    for fmt in ('%d/%m/%Y','%Y-%m-%d','%d-%m-%Y','%d %B %Y','%B %d, %Y'):
        try: return _dt.datetime.strptime(s[:len(fmt)+2].strip(), fmt).date()
        except: pass
    # Try extracting first date-like pattern
    _m = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', s)
    if _m:
        try: return _dt.date(int(_m.group(3)), int(_m.group(2)), int(_m.group(1)))
        except: pass
    return None

if 'UPCOMING_JOBS' not in sections_index or len(sections_index.get('UPCOMING_JOBS',[])) < 3:
    _upcoming_candidates = []
    for _sj in SARK:
        _st = safe(_sj.get('title',''))
        if not _st: continue
        _imp = _sj.get('important_dates') or {}
        # Check exam_date or application_begin is in the future
        _exam_d = _parse_date(_imp.get('exam_date','') or _imp.get('written_exam_date',''))
        _begin_d = _parse_date(_imp.get('application_begin','') or _imp.get('start_date',''))
        _future_d = None
        if _exam_d and _exam_d > _today: _future_d = _exam_d
        elif _begin_d and _begin_d > _today: _future_d = _begin_d
        if _future_d:
            _sl = slugify(_st)[:80]
            _ld = safe(_imp.get('last_date_apply_online','') or _imp.get('last_date_to_apply','') or _imp.get('last_date',''))
            _upcoming_candidates.append((_future_d, {'slug':_sl,'name':_st,'date':_ld}))
    # Sort by nearest future date first
    _upcoming_candidates.sort(key=lambda x: x[0])
    if _upcoming_candidates:
        sections_index['UPCOMING_JOBS'] = [item for _, item in _upcoming_candidates[:10]]

write(str(ROOT/'sections-index.json'), json.dumps(sections_index, ensure_ascii=False, separators=(',',':')))
# Update version string in index.html to bust cache
_ver = __import__('datetime').datetime.now().strftime('%Y%m%d%H%M')
_idx_path = str(ROOT/'index.html')
if __import__('os').path.exists(_idx_path):
    _idx = open(_idx_path, encoding='utf-8').read()
    import re as _re
    _idx_new = _re.sub(r'sections-index\.json\?v=\d+', f'sections-index.json?v={_ver}', _idx)
    if _idx_new != _idx:
        open(_idx_path, 'w', encoding='utf-8').write(_idx_new)

import time as _time
_save_first_seen()   # C1: persist datePosted map for stable rebuilds
_end = _time.time()
VERSION = datetime.now().strftime('%Y%m%d%H%M%S')
PAGES_GENERATED = j_count + sec_count2 + q_count + _du_count
write(str(ROOT/'version.json'), json.dumps({'version':VERSION,'generated':TODAY,'pages':PAGES_GENERATED}, ensure_ascii=False))

print()
print("\u2554" + "\u2550"*54 + "\u2557")
print("\u2551  \u2705 UNIFIED GENERATOR COMPLETE" + " "*23 + "\u2551")
print("\u2560" + "\u2550"*54 + "\u2563")
print(f"\u2551  Jobs (FJA + Sarkari)  : {j_count:<27}\u2551")
print(f"\u2551  State detail          : {s_count:<27}\u2551")
print(f"\u2551  Education detail      : {e_count:<27}\u2551")
print(f"\u2551  Category/study        : {c_count:<27}\u2551")
print(f"\u2551  Section listing       : {sec_count2:<27}\u2551")
print(f"\u2551  Qualification listing : {q_count:<27}\u2551")
print(f"\u2551  TOTAL PAGES           : {PAGES_GENERATED:<27}\u2551")
print("\u255a" + "\u2550"*54 + "\u255d")
print()
