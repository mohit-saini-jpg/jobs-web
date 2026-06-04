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
CJ_FILE  = ROOT / 'data' / 'Complete_Jobs_Full_Data.json'
if not CJ_FILE.exists(): CJ_FILE = ROOT / 'Complete_Jobs_Full_Data.json'
DU_FILE  = ROOT / 'dailyupdates.json'
BASE_URL = 'https://www.topsarkarijobs.com'
TODAY    = date.today().isoformat()
YEAR     = date.today().year
BLOCKED  = {'sarkariresult.com','freejobalert.com','sarkarinetwork.com','sarkariresultshine.com'}

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
    head = ''.join(f'<th>{extract_cell(h)[0]}</th>' for h in head_row)
    body = ''.join(
        f'<tr>' + ''.join(f'<td>{extract_cell(c)[0]}</td>' for c in r) + '</tr>'
        for r in data_rows if r
    )
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

def render_list_items(items, ordered=False):
    filtered = [safe(s) for s in (items if isinstance(items, list) else [str(items)]) if safe(s)]
    if not filtered: return ''
    tag = 'ol' if ordered else 'ul'
    return f'<{tag} class="val-list">' + ''.join(f'<li>{e(s)}</li>' for s in filtered) + f'</{tag}>'

def render_selection(sp):
    if not sp: return ''
    if isinstance(sp, str): sp = [s.strip() for s in re.split(r'[,\n;/→]', sp) if s.strip()]
    steps = [safe(s) for s in sp if safe(s)]
    if not steps: return ''
    return '<div class="sel-steps">' + ''.join(
        f'<div class="sel-step"><span class="sel-num">{i+1}</span>{e(s[:100])}</div>'
        for i, s in enumerate(steps)
    ) + '</div>'

def render_hta(steps):
    if not steps: return ''
    if isinstance(steps, str): steps = [s.strip() for s in steps.split('\n') if s.strip()]
    filtered = [safe(s) for s in steps if safe(s)]
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
    for i, f in enumerate(faq_list):
        if not isinstance(f, dict): continue
        q = safe(f.get('question','')); a = safe(f.get('answer',''))
        if not q or not a: continue
        items += (f'<div class="faq-item" id="faq-{i+1}">'
                  f'<div class="faq-q"><span class="faq-icon">Q{i+1}</span><span>{e(q)}</span></div>'
                  f'<div class="faq-a"><span class="faq-icon" style="background:#15803d">A</span><div>{e(a)}</div></div></div>')
    return items

def render_vacancy_table(vac_list):
    if not vac_list or not isinstance(vac_list, list): return ''
    ALL_COLS = [
        ('post_name',['post_name','post','name','Post Name','Name Of Post','Post']),
        ('total',['total','total_vacancies','total_posts','vacancies','Total Posts','Total','Vacancy']),
        ('ur',['ur','general','UR','General (UR)','General']),
        ('obc',['obc','OBC']),('sc',['sc','SC']),('st',['st','ST']),('ews',['ews','EWS']),
        ('women',['women','Women','female','Female']),
        ('salary',['salary','pay_scale','Scale of Pay','Salary']),
        ('qualification',['eligibility','qualification','Educational Qualification']),
        ('department',['department','Department']),
    ]
    LABELS = {'post_name':'Post Name','total':'Total','ur':'UR/General','obc':'OBC',
              'sc':'SC','st':'ST','ews':'EWS','women':'Women','salary':'Salary',
              'qualification':'Qualification','department':'Department'}
    norm = []; avail = set()
    for row in vac_list:
        if not isinstance(row, dict): continue
        n = {}
        for col, aliases in ALL_COLS:
            for a in aliases:
                if a in row and row[a] not in (None,'',{},[]):
                    n[col] = safe(row[a]); avail.add(col); break
        if n: norm.append(n)
    if not norm: return ''
    cols = [c for c,_ in ALL_COLS if c in avail]
    if not cols: return ''
    head = '<th>Sr.</th>' + ''.join(f'<th>{LABELS[c]}</th>' for c in cols)
    rows = ''.join(f'<tr><td>{i+1}</td>' + ''.join(f'<td>{e(r.get(c,""))}</td>' for c in cols) + '</tr>'
                   for i, r in enumerate(norm))
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
    'how to apply':'how_to_apply', 'gender wise vacancies':'category_wise_vacancy',
    'category wise vacancy':'category_wise_vacancy', 'exam pattern':'exam_pattern',
    'syllabus':'syllabus', 'physical eligibility':'physical_eligibility',
    'physical standards':'physical_eligibility',
    'also read :':'important_links_extra', 'also read':'important_links_extra',
    'important related links':'important_links_extra',
    'important instructions':'important_instructions',
}
SKIP_TITLES = {'set as preferred source on google','set as preferred source','about',''}

def render_sarkari_sections(sections_list, existing_il=None):
    """Map titled sections to proper renderers"""
    if not sections_list: return ''
    data = {
        'dates':[],'fee':[],'age':[],'sel':[],'vac_tables':[],'cat_vac':[],
        'salary':[],'hta':[],'inst':[],'exam':[],'syllabus':[],'physical':[],
        'also_read':None,'raw':[]
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
        elif mapped == 'salary_details': data['salary'].extend(get_list(content))
        elif mapped == 'how_to_apply': data['hta'].extend(get_list(content))
        elif mapped == 'important_instructions': data['inst'].extend(get_list(content))
        elif mapped == 'exam_pattern':
            data['exam'].extend(get_list(content)); data['exam'].extend(get_tables(content))
        elif mapped == 'syllabus': data['syllabus'].extend(get_list(content))
        elif mapped == 'physical_eligibility': data['physical'].extend(get_list(content))
        elif mapped == 'important_links_extra':
            for b in content:
                if b.get('type')=='table' and b.get('rows'):
                    data['also_read'] = b['rows']; break
        else:
            if content: data['raw'].append({'title':title,'content':content})

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
        elif isinstance(tbl, dict) and tbl.get('_list'):
            lis = render_list_items(tbl['_list'])
            if lis: html += sec_card('qualification','fa-graduation-cap','4338ca,#6366f1', lis)
    for tbl in data['cat_vac']:
        if isinstance(tbl, list):
            rendered = render_smart_table(tbl)
            if rendered: html += sec_card('category_wise_vacancy','fa-chart-bar','15803d,#16a34a', rendered)
        elif isinstance(tbl, dict) and tbl.get('_list'):
            lis = render_list_items(tbl['_list'])
            if lis: html += sec_card('vacancy_details','fa-chart-pie','15803d,#16a34a', lis)
    if data['salary']:
        lis = render_list_items(data['salary'])
        if lis: html += sec_card('salary_details','fa-indian-rupee-sign','15803d,#16a34a', lis)
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
    html += render_edu_sections(data['raw'])
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
                    body_rows = ''.join(f'<tr>' + ''.join(f'<td>{extract_cell(c)[0]}</td>' for c in r) + '</tr>'
                                        for r in data_rows if isinstance(r,(list,tuple)))
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
             'all_links','jobs_info','details_page_content','status','last_date',
             'total_post','text_sections','tables','useful_links','application_fees',
             'minimum_age','maximum_age','salary_pay_scale','homepage_serial',
             'organization','post_name','total_vacancy','apply_mode','job_location',
             'short_information','board_name','listing_date','title'}

SECTION_ORDER = ['basic_details','important_dates','application_fee','age_limit',
                 'qualification','vacancy_details','category_wise_vacancy','salary_details',
                 'selection_process','exam_pattern','syllabus','physical_eligibility',
                 'how_to_apply','important_instructions','important_links','faq']

def build_all_sections(job_obj):
    html = ''
    rendered = set()
    # Check for sarkari titled sections
    sections = job_obj.get('sections') or []
    has_sarkari = bool(sections and any(sec.get('title') for sec in sections if isinstance(sec,dict)))
    il = job_obj.get('important_links') or {}

    if has_sarkari:
        html += render_sarkari_sections(sections, il)
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

def build_schemas(job_obj, canon_url, breadcrumbs):
    bd    = job_obj.get('basic_details', {}) or {}
    dates = job_obj.get('important_dates', {}) or {}
    faq   = job_obj.get('faq', []) or []
    title = safe(bd.get('job_title','') or job_obj.get('title',''))
    org   = safe(bd.get('organization_name','') or 'Government of India')
    loc   = safe(bd.get('job_location','') or 'India')
    desc  = safe(bd.get('short_information',''))[:500] or title
    last_d = safe(dates.get('last_date_to_apply','') or dates.get('last_date',''))

    _pay_str = safe((job_obj.get('basic_details') or {}).get('pay_scale','') or
                    (job_obj.get('salary_details') or {}).get('pay_scale','') or '')
    _sal_min, _sal_max = parse_salary(_pay_str)
    jp = {'@context':'https://schema.org','@type':'JobPosting','title':title,
          'description':desc,'datePosted':TODAY,'url':canon_url,
          'employmentType':'FULL_TIME',
          'hiringOrganization':{'@type':'Organization','name':org},
          'jobLocation':{'@type':'Place','address':{'@type':'PostalAddress','addressCountry':'IN','addressLocality':loc}},
          'baseSalary':{'@type':'MonetaryAmount','currency':'INR','value':{'@type':'QuantitativeValue','minValue':_sal_min,'maxValue':_sal_max,'unitText':'MONTH'}}}
    if last_d:
        nd = norm_date(last_d)
        if nd: jp['validThrough'] = nd + 'T00:00:00'

    bc_items = [{'@type':'ListItem','position':1,'name':'Home','item':BASE_URL+'/'}]
    for i,(lbl,url) in enumerate(breadcrumbs, 2):
        bc_items.append({'@type':'ListItem','position':i,'name':lbl,'item':url})
    bc_items.append({'@type':'ListItem','position':len(bc_items)+1,'name':title,'item':canon_url})
    bc_schema = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':bc_items}

    out = (f'<script type="application/ld+json">{json.dumps(jp, ensure_ascii=False)}</script>\n'
           f'<script type="application/ld+json">{json.dumps(bc_schema, ensure_ascii=False)}</script>\n')

    valid_faqs = [f for f in faq if isinstance(f,dict) and f.get('question') and f.get('answer')][:10]
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
.data-table{width:100%;border-collapse:collapse;font-size:.81rem;min-width:320px}
.data-table th{background:#1d4ed8;color:#fff;padding:8px 12px;font-weight:700;text-align:left;white-space:nowrap}
.data-table td{padding:8px 12px;border-bottom:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top;line-height:1.5}
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
.rel-btn{display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:8px;font-size:.77rem;font-weight:600;text-decoration:none;background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;transition:all .15s}
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
    last_d    = safe(dates.get('last_date_to_apply','') or dates.get('last_date','') or job_obj.get('last_date',''))
    apply_m   = safe(bd.get('application_mode','') or job_obj.get('apply_mode','') or 'Online')
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
    meta_desc = ('. '.join(p.rstrip('.') for p in _parts) + '. ' + _cta_md)[:155]

    schemas_html = build_schemas(job_obj, canon_url, breadcrumbs)

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
<script src="/tsj-init.js" defer></script>
<main id="main">{body}</main>
<div id="footerPlaceholder"></div>
<script src="/tsj-footer-init.js" defer></script>
<script src="/tsj-menu.js" defer></script>
</body>
</html>'''

# ── Listing page builder ───────────────────────────────────────
def build_listing_page(title, jobs, canon_url, breadcrumbs, desc=''):
    title_tag  = f"{title} {YEAR} — Apply Online | Top Sarkari Jobs"
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
        jslug  = slugify(jtitle)
        jorg   = safe(bd.get('organization_name','') or 'Government')
        jvac   = safe(bd.get('total_vacancies','') or job.get('total_post',''))
        jld    = safe(dates.get('last_date_to_apply','') or dates.get('last_date','') or job.get('last_date',''))
        jmode  = safe(bd.get('application_mode','') or job.get('apply_mode','') or 'Online')
        # Quick links
        ql = ''
        for key, lbl, css in [('apply_online','Apply','btn-apply jl-btn'),('notification_pdf','Notification','btn-pdf jl-btn'),('result_link','Result','btn-result jl-btn'),('admit_card','Admit Card','btn-admit jl-btn')]:
            url = safe(il.get(key,''))
            if url and not is_blocked(url):
                ic = {'apply_online':'fa-paper-plane','notification_pdf':'fa-file-pdf','result_link':'fa-trophy','admit_card':'fa-id-card'}.get(key,'fa-link')
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
        cards_html += f'''<article class="job-card" data-title="{e(jtitle.lower())}" data-org="{e(jorg.lower())}">
  <div class="job-card-title"><a href="/jobs/{e(jslug)}/">{e(jtitle)}</a></div>
  <div class="job-card-org"><i class="fa-regular fa-building"></i> {e(jorg[:60])}</div>
  <div class="job-card-meta">
    {f'<span class="jm-badge" style="background:#dcfce7;color:#15803d">{e(jvac)} Posts</span>' if jvac else ''}
    <span class="jm-badge" style="background:#ede9fe;color:#5b21b6">{e(jmode)}</span>
  </div>
  {f'<div class="job-card-date{urgent_cls}"><i class="fa-regular fa-clock"></i> Last Date: {e(jld)}</div>' if jld else ''}
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
<script src="/tsj-init.js" defer></script>
<main id="main">{bc_html}{body}</main>
<div id="footerPlaceholder"></div>
<script src="/tsj-footer-init.js" defer></script>
<script src="/tsj-menu.js" defer></script>
</body>
</html>'''

# ═══════════════════════════════════════════════════════════════
# LOAD JSON DATA
# ═══════════════════════════════════════════════════════════════
print("Loading JSON data...")
with open(CJ_FILE, encoding='utf-8') as f: CJ = json.load(f)
with open(DU_FILE, encoding='utf-8') as f: DU = json.load(f)

FJA     = CJ.get('freejobalert_categories', {})
SARK    = (CJ.get('sarkari_data',{}) or {}).get('jobs', [])
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
    for field, key in [('apply_online_link','apply_online'),('official_notification_pdf_link','notification_pdf'),('official_website_link','official_website'),('form_pdf_link','notification_pdf')]:
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
    raw_tables = job.get('tables') or []
    if raw_tables and not sections_out:
        for tbl in raw_tables:
            name = tbl.get('table_name','') or ''
            if 'gb headline' in name.lower(): continue
            rows = tbl.get('rows',[]) or []
            if rows: sections_out.append({'title':name,'content':[{'type':'table','rows':rows}]})

    bd = {'job_title':title,'organization_name':safe(job.get('organization','') or job.get('board_name','')),'post_name':safe(job.get('post_name','')),'total_vacancies':safe(job.get('total_vacancy','') or job.get('total_post','')),'application_mode':safe(job.get('apply_mode','') or 'Online'),'job_location':safe(job.get('job_location','') or job.get('state','') or 'India'),'short_information':strip_html(safe(job.get('short_information','') or job.get('jobs_info',''))),'last_updated':safe(job.get('post_date','') or job.get('listing_date','')),'job_type':safe(job.get('entry_type',''))}
    imp_dates = {}
    raw_d = job.get('important_dates') or {}
    if isinstance(raw_d, dict): imp_dates.update({k:v for k,v in raw_d.items() if v})
    age = {}
    if job.get('minimum_age'): age['minimum_age'] = safe(job['minimum_age'])
    if job.get('maximum_age'): age['maximum_age'] = safe(job['maximum_age'])
    full = {'basic_details':bd,'important_dates':imp_dates,'application_fee':job.get('application_fees') or {},'age_limit':age or (job.get('age_limit') or {}),'qualification':job.get('eligibility') or job.get('qualification') or {},'vacancy_details':job.get('vacancy_details') or [],'salary_details':{'pay_scale':safe(job.get('salary_pay_scale',''))} if job.get('salary_pay_scale') else {},'how_to_apply':[job['how_to_apply']] if isinstance(job.get('how_to_apply'),str) and job.get('how_to_apply') else (job.get('how_to_apply') or []),'important_links':il,'sections':sections_out,'faq':job.get('faq') or [],'category':job.get('category',''),'slug':slug}
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
        state_html = build_detail_page(detail, item_slug, canon, bc, f'{state_name} Govt Job', noindex_dup=True)
        write(str(ROOT/'state'/state_slug/item_slug/'index.html'), state_html)
        if item_slug not in seen_jobs:
            seen_jobs[item_slug] = state_name
            # /jobs/ page: index,follow (primary canonical)
            jobs_html = build_detail_page(detail, item_slug, canon, bc, f'{state_name} Govt Job', noindex_dup=False)
            write(str(ROOT/'jobs'/item_slug/'index.html'), jobs_html)
        s_count += 1

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
        edu_html = build_detail_page(full_d, item_slug, canon, bc, sec_title, noindex_dup=True)
        write(str(ROOT/'education'/sec_id/item_slug/'index.html'), edu_html)
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
for cat, jobs_list in FJA.items():
    if not isinstance(jobs_list, list): continue
    cat_slug  = QUAL_SLUG.get(cat, slugify(cat))
    cat_label = QUAL_LABEL.get(cat, cat.replace('_',' ').title())
    for job in jobs_list:
        bd = job.get('basic_details',{}) or {}
        title = safe(bd.get('job_title',''))
        if not title: continue
        item_slug = slugify(title)[:80]
        canon = f"{BASE_URL}/category/study/{cat_slug}/{item_slug}/"
        bc    = [('Study Wise Jobs', f"{BASE_URL}/category/study/"), (f'{cat_label} Jobs', f"{BASE_URL}/category/study/{cat_slug}/")]
        _canon_j = f"{BASE_URL}/jobs/{item_slug}/"  # canonical always points to /jobs/
        write(str(ROOT/'category'/'study'/cat_slug/item_slug/'index.html'), build_detail_page(job, item_slug, _canon_j, bc, f'{cat_label} Jobs', noindex_dup=True))
        c_count += 1

print(f"  Category/study pages: {c_count}")

# 6. SECTION LISTING PAGES
print("Generating /section/ pages...")
SARK_CAT_MAP = {
    'SR_Latest_Jobs':'latest-jobs','SR_Result':'result','SR_Admit_Card':'admit-card',
    'SR_Admission':'admission','SR_Answer_Key':'answer-key','OFFLINE_FORM':'offline-form',
    'LATEST_JOBS NEW':'latest-jobs-new','UPCOMING_JOBS':'upcoming-jobs',
    'STATE_JOBS':'state-jobs-central','CENTRAL_JOBS':'central-jobs',
    'ADMISSIONS':'admissions',
}
FJA_CAT_MAP = {
    '10TH_Pass':'10th-pass-jobs','8TH_Pass':'8th-pass-jobs','12TH_Pass':'12th-pass-jobs',
    'Diploma':'diploma-jobs','ITI':'iti-jobs','B_Tech_BE':'btech-be-jobs','B_Com':'bcom-jobs',
    'Any_Graduate':'any-graduate-jobs','Any_Post_Graduate':'post-graduate-jobs',
    'Railway_Jobs':'railway-jobs','Police_Defence':'police-defence-jobs',
    'Teaching_Faculty':'teaching-faculty-jobs','Bank_Jobs':'bank-jobs',
    'Medical_Hospital':'medical-hospital-jobs','Last_Date_Reminder':'last-date-reminder',
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
    norm = [{'basic_details':{'job_title':safe(j.get('title','')),'organization_name':safe(j.get('organization','')),'total_vacancies':safe(j.get('total_post','') or j.get('total_vacancy','')),'application_mode':safe(j.get('apply_mode','') or 'Online'),'job_location':'India'},'important_dates':j.get('important_dates') or {},'important_links':j.get('important_links') or {},'category':cat_key} for j in sark_jobs if j.get('title')]
    lbl = cat_key.replace('_',' ').replace('SR ','').title()
    write(str(ROOT/'section'/url_slug/'index.html'), build_listing_page(lbl, norm, f"{BASE_URL}/section/{url_slug}/", []))
    sec_count += 1

# dailyupdates sections
DU_SLUG_MAP = {'Govt Scheme Yojna':'govt-scheme-yojna','ImportantCSC PDF':'important-csc-pdf','ImportantCSC link':'important-csc-link','Today Updates':'today-updates'}
for sec in DU_SECS:
    sec_title = sec.get('title','') or sec.get('id','')
    slug_key  = DU_SLUG_MAP.get(sec_title, slugify(sec_title))
    items     = sec.get('items', [])
    cards_html = ''.join(f'<article class="job-card"><div class="job-card-title"><a href="{e(str(item.get("url","#")))}" target="_blank" rel="noopener noreferrer">{e(safe(item.get("name","")))}</a></div></article>' for item in items if item.get('name'))
    body_html = f'<div class="cat-wrap"><h1 class="cat-h1" style="margin:12px 10px 4px">{e(sec_title)}</h1><p class="cat-count" style="margin:0 10px 12px;color:#64748b;font-size:.78rem">{len(items)} items</p><div id="jobList" style="padding:0 10px">{cards_html}</div></div>'
    bc_s = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':BASE_URL+'/'},{'@type':'ListItem','position':2,'name':sec_title,'item':f"{BASE_URL}/section/{slug_key}/"}]}
    schema_tag = f'<script type="application/ld+json">{json.dumps(bc_s,ensure_ascii=False)}</script>'
    bc_html = f'<nav class="bc"><a href="/">Home</a><span class="bc-sep">›</span><span>{e(sec_title)}</span></nav>'
    page = f'''<!DOCTYPE html><html lang="en-IN"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>{e(sec_title)} {YEAR} | Top Sarkari Jobs</title><meta name="description" content="Latest {e(sec_title)} updates {YEAR}."/><meta name="robots" content="index,follow"/><link rel="canonical" href="{BASE_URL}/section/{slug_key}/"/>{schema_tag}<script src="/tsj-config.js"></script><link rel="icon" href="/image.ico"/><link rel="stylesheet" href="/styles.css"/><link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/><noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript><link rel="stylesheet" href="/styles-detail.css" media="print" onload="this.media='all'"/><noscript><link rel="stylesheet" href="/styles-detail.css"/></noscript></head><body><div id="headerPlaceholder"></div><script src="/tsj-init.js" defer></script><main>{bc_html}{body_html}</main><div id="footerPlaceholder"></div><script src="/tsj-footer-init.js" defer></script></body></html>'''
    write(str(ROOT/'section'/slug_key/'index.html'), page)
    sec_count += 1

print(f"  Section pages: {sec_count}")

# 7. QUALIFICATION LISTING PAGES
print("Generating /qualification/ pages...")
for cat_key, jobs_list in FJA.items():
    if not isinstance(jobs_list, list) or not jobs_list: continue
    q_slug  = QUAL_SLUG.get(cat_key, cat_key.lower().replace('_','-'))
    q_label = QUAL_LABEL.get(cat_key, cat_key.replace('_',' ').title())
    write(str(ROOT/'qualification'/q_slug/'index.html'), build_listing_page(f"{q_label} Jobs", jobs_list, f"{BASE_URL}/qualification/{q_slug}/", [], f"Government job notifications for {q_label} candidates."))
    qual_count += 1

print(f"  Qualification pages: {qual_count}")

# ─────────────────────────────────────────────────────────────
# WRITE INDEXES (sections-index.json + jobs-index.json)
# ─────────────────────────────────────────────────────────────
INDEX  = ROOT / 'jobs-index.json'
SINDEX = ROOT / 'sections-index.json'

with open(INDEX, 'w', encoding='utf-8') as f:
    json.dump(jobs_index, f, ensure_ascii=False, separators=(',',':'))

# Sections index — FJA + Sarkari SR_* categories
for cat, jobs_list in FJA.items():
    if not isinstance(jobs_list, list): continue
    items = []
    for job in jobs_list:
        bd4 = job.get('basic_details',{}) or {}
        t = safe(bd4.get('job_title',''))
        if not t: continue
        sl = slugify(t)
        dt = job.get('important_dates',{}) or {}
        ld = safe(dt.get('last_date_to_apply',''))
        items.append({'slug':sl,'name':t,'date':norm_date(ld) or ''})
    if items: sindex[cat] = items

sark_by_cat = {}
for sj in SARK:
    cat = sj.get('category','')
    if not cat: continue
    t = safe(sj.get('title',''))
    if not t: continue
    sl = clean_slug(sj.get('slug','')) or slugify(t)
    ld = safe((sj.get('important_dates') or {}).get('last_date_to_apply','') or sj.get('last_date',''))
    sark_by_cat.setdefault(cat,[]).append({'slug':sl,'name':t,'date':ld[:20]})
for cat, items in sark_by_cat.items():
    if items: sindex[cat] = items

with open(SINDEX, 'w', encoding='utf-8') as f:
    json.dump(sindex, f, ensure_ascii=False, separators=(',',':'))

total = j_count + s_count + e_count + c_count + sec_count + qual_count
print(f"""
╔══════════════════════════════════════════════════════╗
║  ✅ UNIFIED GENERATOR COMPLETE                       ║
╠══════════════════════════════════════════════════════╣
║  Jobs (FJA + Sarkari)  : {j_count:<8}                    ║
║  State detail          : {s_count:<8}                    ║
║  Education detail      : {e_count:<8}                    ║
║  Category/study        : {c_count:<8}                    ║
║  Section listing       : {sec_count:<8}                    ║
║  Qualification listing : {qual_count:<8}                    ║
║  TOTAL PAGES           : {total:<8}                    ║
╚══════════════════════════════════════════════════════╝
""")
