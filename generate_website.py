#!/usr/bin/env python3
"""
FULL-STACK JSON-DRIVEN WEBSITE GENERATOR
=========================================
Zero hardcoded content. 100% data from JSON.
Generates: Homepage, 31 Category pages, 34 State pages,
           53 Qualification pages, 38 Education pages,
           All Job Detail pages
"""

import json, re, os, html as html_mod, shutil
from datetime import date, datetime
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
ROOT     = Path('.')
CJ_FILE  = ROOT / 'Complete_Jobs_Full_Data.json'
DU_FILE  = ROOT / 'dailyupdates.json'
BASE_URL = 'https://www.topsarkarijobs.com'
TODAY    = date.today().isoformat()
YEAR     = date.today().year

# ── Helpers ─────────────────────────────────────────────────────────
def e(s): return html_mod.escape(str(s or ''), quote=True)

def safe(v):
    if v is None: return ''
    if isinstance(v, str): return v.strip()
    if isinstance(v, (int, float, bool)): return str(v).strip()
    if isinstance(v, list):
        parts = [safe(x) for x in v if x is not None]
        return ', '.join(p for p in parts if p)
    if isinstance(v, dict):
        for k in ['text','value','name','description','details','qualification',
                  'eligibility','content','pay_scale','salary','title']:
            if isinstance(v.get(k), str) and v[k].strip(): return v[k].strip()
        return ' | '.join(safe(val) for val in v.values() if val)
    return str(v).strip()

def slugify(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text[:80].strip('-') or 'page'

def is_blocked(url):
    BLOCKED = {'sarkariresult.com','freejobalert.com','sarkarinetwork.com','sarkariresultshine.com'}
    return any(d in str(url).lower() for d in BLOCKED)

def key_label(key):
    """Convert JSON key to human-readable label"""
    # Hindi keys pass-through
    if any('\u0900' <= c <= '\u097f' for c in str(key)):
        return str(key)
    label = str(key).replace('_', ' ').replace('-', ' ')
    label = re.sub(r'\b([a-z])', lambda m: m.group(1).upper(), label)
    ALIASES = {
        'Url':'URL','Pdf':'PDF','Obc':'OBC','Sc':'SC','St':'ST','Ur':'UR',
        'Ews':'EWS','Pwd':'PwD','Cbt':'CBT','Id':'ID',
    }
    for k,v in ALIASES.items():
        label = re.sub(r'\b'+k+r'\b', v, label)
    return label

SECTION_META = {
    'basic_details':       ('Job Overview',              'fa-circle-info',       'linear-gradient(135deg,#1e40af,#3b82f6)'),
    'important_dates':     ('Important Dates',           'fa-calendar-check',    'linear-gradient(135deg,#b91c1c,#dc2626)'),
    'application_fee':     ('Application Fee',           'fa-indian-rupee-sign', 'linear-gradient(135deg,#c2410c,#ea580c)'),
    'age_limit':           ('Age Limit',                 'fa-user-clock',        'linear-gradient(135deg,#0f766e,#0891b2)'),
    'qualification':       ('Qualification / Eligibility','fa-graduation-cap',   'linear-gradient(135deg,#4338ca,#6366f1)'),
    'vacancy_details':     ('Vacancy Details',           'fa-chart-pie',         'linear-gradient(135deg,#15803d,#16a34a)'),
    'category_wise_vacancy':('Category-wise Vacancy',   'fa-chart-bar',         'linear-gradient(135deg,#15803d,#16a34a)'),
    'salary_details':      ('Salary & Pay Scale',        'fa-indian-rupee-sign', 'linear-gradient(135deg,#15803d,#16a34a)'),
    'selection_process':   ('Selection Process',         'fa-list-check',        'linear-gradient(135deg,#5b21b6,#7c3aed)'),
    'exam_pattern':        ('Exam Pattern',              'fa-file-lines',        'linear-gradient(135deg,#0369a1,#0284c7)'),
    'syllabus':            ('Syllabus',                  'fa-book',              'linear-gradient(135deg,#4338ca,#6366f1)'),
    'physical_eligibility':('Physical Eligibility',      'fa-dumbbell',          'linear-gradient(135deg,#be123c,#e11d48)'),
    'how_to_apply':        ('How to Apply',              'fa-clipboard-list',    'linear-gradient(135deg,#0f766e,#0891b2)'),
    'important_instructions':('Important Instructions',  'fa-circle-exclamation','linear-gradient(135deg,#b45309,#ca8a04)'),
    'important_links':     ('Important Links',           'fa-link',              'linear-gradient(135deg,#1e40af,#1e3a8a)'),
    'faq':                 ('Frequently Asked Questions','fa-circle-question',   'linear-gradient(135deg,#4338ca,#6366f1)'),
}

# ── Universal Recursive JSON Renderer ───────────────────────────────

def render_value(val, depth=0):
    """Recursively render any JSON value"""
    if val is None or val == '' or val == [] or val == {}: return ''
    if isinstance(val, bool):
        cls = 'badge-yes' if val else 'badge-no'
        return f'<span class="badge {cls}">{"✓ Yes" if val else "✗ No"}</span>'
    if isinstance(val, (int, float)):
        return f'<span class="val-num">{e(str(val))}</span>'
    if isinstance(val, str):
        sv = val.strip()
        if not sv: return ''
        # Auto-detect URL
        if sv.startswith('http'):
            icon = 'fa-file-pdf' if sv.lower().endswith('.pdf') else 'fa-external-link-alt'
            if not is_blocked(sv):
                return f'<a href="{e(sv)}" target="_blank" rel="noopener noreferrer" class="auto-link"><i class="fa-solid {icon}"></i> {e(sv[:60])}{"…" if len(sv)>60 else ""}</a>'
        return f'<span class="val-text">{e(sv)}</span>'
    if isinstance(val, list):
        if not val: return ''
        # All strings → bullet list
        if all(isinstance(x, str) for x in val):
            items = ''.join(f'<li>{e(str(x))}</li>' for x in val if x)
            return f'<ul class="val-list">{items}</ul>' if items else ''
        # All dicts → table
        if all(isinstance(x, dict) for x in val if x is not None):
            return render_obj_array_as_table(val, depth)
        # Mixed
        parts = []
        for item in val:
            if item is None: continue
            r = render_value(item, depth+1)
            if r: parts.append(f'<li>{r}</li>')
        return f'<ul class="val-list">{"".join(parts)}</ul>' if parts else ''
    if isinstance(val, dict):
        if not val: return ''
        rows = []
        for k, v in val.items():
            rv = render_value(v, depth+1)
            if rv:
                rows.append(f'<tr><th class="kv-key">{e(key_label(k))}</th><td class="kv-val">{rv}</td></tr>')
        if not rows: return ''
        if depth == 0:
            return f'<table class="kv-table"><tbody>{"".join(rows)}</tbody></table>'
        return f'<div class="nested-obj"><table class="kv-table kv-nested"><tbody>{"".join(rows)}</tbody></table></div>'
    return e(str(val))

def render_obj_array_as_table(arr, depth=0):
    """Render list of dicts as responsive table — auto-detect all columns"""
    if not arr: return ''
    # Collect all unique keys preserving order
    all_keys = []
    seen = set()
    for row in arr:
        if not isinstance(row, dict): continue
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                all_keys.append(k)
    if not all_keys: return ''
    # Filter keys with at least one non-empty value
    useful_keys = [k for k in all_keys if any(safe(row.get(k)) for row in arr if isinstance(row, dict))]
    if not useful_keys: return ''
    head = '<th>Sr.</th>' + ''.join(f'<th>{e(key_label(k))}</th>' for k in useful_keys)
    rows_html = ''
    for i, row in enumerate(arr, 1):
        if not isinstance(row, dict): continue
        cells = f'<td>{i}</td>' + ''.join(f'<td>{render_value(row.get(k), depth+1)}</td>' for k in useful_keys)
        rows_html += f'<tr>{cells}</tr>'
    if not rows_html: return ''
    return f'<div class="tbl-scroll"><table class="data-table"><thead><tr>{head}</tr></thead><tbody>{rows_html}</tbody></table></div>'

# ── Specialised Section Renderers ────────────────────────────────────

def render_basic_details(bd):
    if not bd or not isinstance(bd, dict): return ''
    rows = ''
    PRIORITY = ['job_title','organization_name','post_name','total_vacancies',
                'application_mode','job_location','job_type','notification_number',
                'official_website','last_updated','department']
    rendered = set()
    for k in PRIORITY:
        if k == 'job_title': rendered.add(k); continue  # shown in H1
        v = bd.get(k)
        rv = render_value(v)
        if rv:
            rendered.add(k)
            rows += f'<tr><th><i class="fa-solid fa-angle-right"></i> {e(key_label(k))}</th><td>{rv}</td></tr>'
    # Render remaining keys not in priority list
    for k, v in bd.items():
        if k in rendered: continue
        rv = render_value(v)
        if rv:
            rows += f'<tr><th><i class="fa-solid fa-angle-right"></i> {e(key_label(k))}</th><td>{rv}</td></tr>'
    # short_information as card
    si = safe(bd.get('short_information',''))
    si_html = f'<div class="short-info"><i class="fa-solid fa-circle-info"></i> {e(si)}</div>' if si else ''
    return si_html + (f'<table class="kv-table detail-kv"><tbody>{rows}</tbody></table>' if rows else '')

def render_important_dates(obj):
    if not obj or not isinstance(obj, dict): return ''
    PRIORITY = ['application_start_date','application_begin','start_date',
                'date_of_notification','notification_date',
                'last_date_to_apply','last_date','application_last_date',
                'fee_payment_last_date','fee_last_date','correction_last_date',
                'exam_date','written_exam_date','online_exam_date','omr_exam_date',
                'interview_date','admit_card_date','admit_card','result_date','event',
                'आवेदन शुरू','अंतिम तिथि','परीक्षा तिथि','महत्वपूर्ण तिथि','अधिसूचना']
    rows = ''; seen = set()
    for k in PRIORITY:
        v = safe(obj.get(k))
        lbl = key_label(k)
        if not v or lbl in seen: continue
        seen.add(lbl)
        is_last = bool(re.search(r'last|closing|अंतिम', k, re.I))
        cls = ' class="date-last"' if is_last else ''
        rows += f'<tr><th><i class="fa-regular fa-calendar"></i> {e(lbl)}</th><td{cls}>{e(v)}</td></tr>'
    # Remaining keys
    for k, v in obj.items():
        lbl = key_label(k)
        sv = safe(v)
        if not sv or lbl in seen: continue
        seen.add(lbl)
        rows += f'<tr><th><i class="fa-regular fa-calendar"></i> {e(lbl)}</th><td>{e(sv)}</td></tr>'
    return f'<table class="kv-table"><tbody>{rows}</tbody></table>' if rows else ''

def render_fee(obj):
    if not obj or not isinstance(obj, dict): return ''
    FEE_KEYS = [('general_fee','General / UR'),('general','General / UR'),('ur','UR'),
                ('obc_fee','OBC'),('obc','OBC'),('sc_fee','SC'),('sc','SC'),
                ('st_fee','ST'),('st','ST'),('ews','EWS'),('pwd_fee','PH / PwD'),
                ('ph','PH / PwD'),('pwd','PH / PwD'),('female_fee','Female'),
                ('female','Female'),('ex_serviceman_fee','Ex-Serviceman'),
                ('all','All Categories'),('all_category','All Categories')]
    def is_free(v): return bool(re.search(r'nil|^0$|free|no fee|exempt|शून्य', str(v), re.I))
    seen = set(); items = ''
    for key, lbl in FEE_KEYS:
        v = safe(obj.get(key))
        if not v or lbl in seen: continue
        seen.add(lbl)
        cls = 'fee-free' if is_free(v) else 'fee-paid'
        items += f'<div class="fee-cell"><span class="fee-cat">{e(lbl)}</span><span class="fee-amt {cls}">{e(v)}</span></div>'
    # Remaining keys
    SKIP = {k for k,_ in FEE_KEYS} | {'details','fee_mode','payment_mode'}
    for k, v in obj.items():
        lbl = key_label(k)
        sv = safe(v)
        if not sv or k in SKIP or lbl in seen: continue
        seen.add(lbl)
        items += f'<div class="fee-cell"><span class="fee-cat">{e(lbl)}</span><span class="fee-amt">{e(sv)}</span></div>'
    note_parts = []
    for k in ['details','fee_mode','payment_mode']:
        nv = safe(obj.get(k,''))
        if nv: note_parts.append(nv)
    note = ' | '.join(note_parts)
    result = f'<div class="fee-grid">{items}</div>' if items else ''
    if note: result += f'<div class="fee-note"><i class="fa-solid fa-circle-info"></i> {e(note)}</div>'
    return result

def render_age(obj):
    if not obj or not isinstance(obj, dict): return ''
    return render_value(obj)

def render_qualification(obj):
    if not obj: return ''
    if isinstance(obj, str) and obj.strip():
        return f'<div class="qual-text">{e(obj)}</div>'
    if isinstance(obj, list):
        return render_value(obj)
    if isinstance(obj, dict):
        return render_value(obj)
    return ''

def render_vacancy(vac_list):
    if not vac_list or not isinstance(vac_list, list): return ''
    return render_obj_array_as_table(vac_list)

def render_cat_vacancy(cwv):
    if not cwv: return ''
    if isinstance(cwv, list): return render_vacancy(cwv)
    if isinstance(cwv, dict):
        rows = ''.join(f'<tr><td>{e(key_label(k))}</td><td>{e(safe(v))}</td></tr>'
                       for k,v in cwv.items() if safe(v))
        return (f'<div class="tbl-scroll"><table class="data-table">'
                f'<thead><tr><th>Category</th><th>Posts</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>') if rows else ''
    return ''

def render_selection(sp):
    if not sp: return ''
    steps = []
    if isinstance(sp, list): steps = [safe(s) for s in sp if safe(s)]
    elif isinstance(sp, str): steps = [s.strip() for s in re.split(r'[,\n;/→]', sp) if s.strip()]
    if not steps: return ''
    items = ''.join(f'<div class="step-card"><span class="step-num">{i+1}</span>'
                    f'<span class="step-text">{e(s)}</span></div>' for i,s in enumerate(steps))
    return f'<div class="steps-wrap">{items}</div>'

def render_how_to_apply(steps):
    if not steps: return ''
    if isinstance(steps, list):
        filtered = [safe(s) for s in steps if safe(s)]
    elif isinstance(steps, str):
        filtered = [s.strip() for s in re.split(r'[\n;]', steps) if s.strip()]
    else: return ''
    if not filtered: return ''
    items = ''.join(f'<li class="hta-item"><span class="hta-num">{i+1}</span>'
                    f'<span>{e(s)}</span></li>' for i,s in enumerate(filtered))
    return f'<ol class="hta-list">{items}</ol>'

def render_instructions(insts):
    if not isinstance(insts, list) or not insts: return ''
    filtered = [safe(s) for s in insts if safe(s)]
    if not filtered: return ''
    return ''.join(f'<div class="inst-box"><i class="fa-solid fa-triangle-exclamation"></i> {e(s)}</div>'
                   for s in filtered)

LINK_CFG = {
    'apply_online':          ('Apply Online',          'btn-apply',   'fa-paper-plane'),
    'official_website':      ('Official Website',      'btn-official','fa-globe'),
    'notification_pdf':      ('Download Notification', 'btn-pdf',     'fa-file-pdf'),
    'download_notification': ('Download Notification', 'btn-pdf',     'fa-file-pdf'),
    'official_notification': ('Official Notification', 'btn-pdf',     'fa-file-pdf'),
    'registration_link':     ('Register Now',          'btn-register','fa-user-plus'),
    'login_link':            ('Login',                 'btn-login',   'fa-right-to-bracket'),
    'admit_card':            ('Admit Card',            'btn-admit',   'fa-id-card'),
    'answer_key':            ('Answer Key',            'btn-answer',  'fa-key'),
    'syllabus_pdf':          ('Syllabus PDF',          'btn-syllabus','fa-book'),
    'result_link':           ('Result',                'btn-result',  'fa-trophy'),
    'click_here':            ('Click Here',            'btn-default', 'fa-link'),
    'merit_list':            ('Merit List',            'btn-merit',   'fa-list'),
    'score_card':            ('Score Card',            'btn-score',   'fa-file'),
    'महत्वपूर्ण लिंक':        ('Important Link',        'btn-default', 'fa-link'),
}

def render_links(il_obj):
    if not il_obj or not isinstance(il_obj, dict): return ''
    buttons = ''; seen = set()
    for key, val in il_obj.items():
        if key in ('structured_links','seo_tags'): continue
        urls = val if isinstance(val, list) else [val]
        label, css, icon = LINK_CFG.get(key, (key_label(key), 'btn-default', 'fa-link'))
        for url in urls:
            u = str(url or '').strip()
            if not u.startswith('http') or is_blocked(u) or u in seen: continue
            seen.add(u)
            # Auto-detect
            ul = u.lower()
            if ul.endswith('.pdf'): icon = 'fa-file-pdf'; css = 'btn-pdf'
            elif 'apply' in key.lower(): icon = 'fa-paper-plane'; css = 'btn-apply'
            elif 'result' in key.lower(): icon = 'fa-trophy'; css = 'btn-result'
            elif 'admit' in key.lower(): icon = 'fa-id-card'; css = 'btn-admit'
            elif 'answer' in key.lower(): icon = 'fa-key'; css = 'btn-answer'
            download = ' download' if ul.endswith('.pdf') else ''
            buttons += (f'<a href="{e(u)}" class="lnk-btn {css}" target="_blank" '
                       f'rel="noopener noreferrer"{download}>'
                       f'<i class="fa-solid {icon}"></i> {e(label)}</a>\n')
    # structured_links
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
                ('fa-globe','btn-official') if 'official' in ll else \
                ('fa-link','btn-default')
        download = ' download' if u.lower().endswith('.pdf') else ''
        buttons += (f'<a href="{e(u)}" class="lnk-btn {cl}" target="_blank" '
                   f'rel="noopener noreferrer"{download}>'
                   f'<i class="fa-solid {ic}"></i> {e(lbl[:60])}</a>\n')
    return f'<div class="links-grid">{buttons}</div>' if buttons else ''

def render_faq(faq_list):
    if not isinstance(faq_list, list) or not faq_list: return ''
    items = ''
    for i, f in enumerate(faq_list):
        if not isinstance(f, dict): continue
        q = safe(f.get('question','')); a = safe(f.get('answer',''))
        if not q or not a: continue
        items += f'''<div class="faq-item" id="faq-{i+1}">
  <div class="faq-q"><span class="faq-icon">Q{i+1}</span><span>{e(q)}</span></div>
  <div class="faq-a"><span class="faq-a-icon">A</span><div>{e(a)}</div></div>
</div>'''
    return items

def render_edu_sections(sections_list):
    """Render education raw scraper sections"""
    if not sections_list: return ''
    html = ''
    for sec in sections_list:
        heading = safe(sec.get('heading',''))
        contents = sec.get('content', [])
        if not contents: continue
        body = ''
        for block in contents:
            btype = (block.get('type','') or '').lower()
            if btype == 'paragraph':
                text = safe(block.get('text',''))
                if text: body += f'<p class="edu-para">{e(text)}</p>'
            elif btype == 'table':
                rows = block.get('rows', [])
                headers = block.get('headers', [])
                if not rows: continue
                if not headers and rows: headers = rows[0]; rows = rows[1:]
                head = ''.join(f'<th>{e(h)}</th>' for h in headers)
                body_rows = ''.join(f'<tr>' + ''.join(f'<td>{e(str(c))}</td>' for c in r) + '</tr>' for r in rows)
                body += f'<div class="tbl-scroll"><table class="data-table"><thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table></div>'
            elif btype == 'list':
                items = block.get('items', [])
                body += '<ul class="val-list">' + ''.join(f'<li>{e(li)}</li>' for li in items) + '</ul>'
            elif btype == 'merged_info':
                for mi in block.get('items', []):
                    lbl = safe(mi.get('label','')); txt = safe(mi.get('text',''))
                    if lbl or txt:
                        body += f'<div class="mi-item">{f"<b>{e(lbl)}</b>: " if lbl else ""}{e(txt) if txt else ""}</div>'
        if body.strip():
            if heading:
                html += f'<div class="edu-sec"><h3 class="edu-sec-h">{e(heading)}</h3>{body}</div>'
            else:
                html += f'<div class="edu-sec">{body}</div>'
    return html

def render_unknown_section(key, val):
    """Future-proof: render any unknown JSON key"""
    rv = render_value(val)
    return rv

# ── Section Renderer Dispatcher ─────────────────────────────────────

SECTION_ORDER = [
    'basic_details','important_dates','application_fee','age_limit',
    'qualification','vacancy_details','category_wise_vacancy','salary_details',
    'selection_process','exam_pattern','syllabus','physical_eligibility',
    'how_to_apply','important_instructions','important_links','faq'
]

SKIP_KEYS = {'seo_tags','category','slug','source_url','url','_useful_links'}

def render_section_body(key, val):
    """Dispatch to specialised renderer or universal fallback"""
    if key == 'basic_details':       return render_basic_details(val)
    if key == 'important_dates':     return render_important_dates(val)
    if key == 'application_fee':     return render_fee(val)
    if key == 'age_limit':           return render_age(val)
    if key == 'qualification':       return render_qualification(val)
    if key == 'vacancy_details':     return render_vacancy(val)
    if key == 'category_wise_vacancy': return render_cat_vacancy(val)
    if key == 'salary_details':      return render_value(val)
    if key == 'selection_process':   return render_selection(val)
    if key == 'exam_pattern':        return render_value(val)
    if key == 'syllabus':            return render_value(val)
    if key == 'physical_eligibility': return render_value(val)
    if key == 'how_to_apply':        return render_how_to_apply(val)
    if key == 'important_instructions': return render_instructions(val)
    if key == 'important_links':     return render_links(val)
    if key == 'faq':                 return render_faq(val)
    if key == 'sections':            return render_edu_sections(val) if isinstance(val,list) else render_value(val)
    return render_unknown_section(key, val)

def build_all_sections(job_obj):
    """Build HTML for all 16+ sections in fixed order, then unknown keys"""
    html = ''
    rendered_keys = set()
    # Fixed order first
    for key in SECTION_ORDER:
        if key not in job_obj: continue
        rendered_keys.add(key)
        val = job_obj[key]
        if val is None or val == '' or val == [] or val == {}: continue
        body = render_section_body(key, val)
        if not body or not body.strip(): continue
        meta = SECTION_META.get(key, (key_label(key), 'fa-circle', 'linear-gradient(135deg,#475569,#334155)'))
        title, icon, grad = meta
        html += section_card(title, icon, grad, body)
    # Unknown/future keys auto-rendered
    for key, val in job_obj.items():
        if key in rendered_keys or key in SKIP_KEYS: continue
        if val is None or val == '' or val == [] or val == {}: continue
        body = render_unknown_section(key, val)
        if not body or not body.strip(): continue
        title = key_label(key)
        html += section_card(title, 'fa-circle-dot', 'linear-gradient(135deg,#475569,#334155)', body)
    return html

def section_card(title, icon, grad, body):
    return f'''<section class="sec-card" aria-labelledby="sec-{slugify(title)}">
  <div class="sec-head" style="background:{grad}">
    <i class="fa-solid {icon}" aria-hidden="true"></i>
    <h2 id="sec-{e(slugify(title))}">{e(title)}</h2>
  </div>
  <div class="sec-body">{body}</div>
</section>\n'''

# ── SEO Schemas ──────────────────────────────────────────────────────

def build_schemas(job_obj, canon_url, breadcrumbs):
    bd     = job_obj.get('basic_details', {}) or {}
    dates  = job_obj.get('important_dates', {}) or {}
    sal    = job_obj.get('salary_details', {}) or {}
    faq    = job_obj.get('faq', []) or []
    seo    = job_obj.get('seo_tags', []) or []

    title  = safe(bd.get('job_title',''))
    org    = safe(bd.get('organization_name',''))
    loc    = safe(bd.get('job_location','') or 'India')
    desc   = safe(bd.get('short_information',''))[:500] or title
    posted = TODAY
    last_apply = safe(dates.get('last_date_to_apply') or dates.get('last_date',''))

    schemas = []

    # JobPosting
    jp = {
        '@context':'https://schema.org','@type':'JobPosting',
        'title':title,'description':desc,'datePosted':posted,
        'url':canon_url,'employmentType':'FULL_TIME',
        'hiringOrganization':{'@type':'Organization','name':org or 'Government of India'},
        'jobLocation':{'@type':'Place','address':{'@type':'PostalAddress',
            'addressCountry':'IN','addressLocality':loc}},
        'baseSalary':{'@type':'MonetaryAmount','currency':'INR',
            'value':{'@type':'QuantitativeValue','minValue':15000,'maxValue':100000,'unitText':'MONTH'}},
    }
    if last_apply:
        from datetime import datetime
        for fmt in ['%d %b %Y','%d/%m/%Y','%Y-%m-%d','%d-%m-%Y']:
            try:
                dt = datetime.strptime(last_apply, fmt)
                jp['validThrough'] = dt.strftime('%Y-%m-%dT00:00:00')
                break
            except: pass
    schemas.append(jp)

    # WebPage
    schemas.append({'@context':'https://schema.org','@type':'WebPage',
        'name':title,'description':desc,'url':canon_url,
        'publisher':{'@type':'Organization','name':'Top Sarkari Jobs','url':BASE_URL}})

    # Organization
    if org:
        schemas.append({'@context':'https://schema.org','@type':'Organization',
            'name':org,'url':safe(bd.get('official_website','') or '')})

    # BreadcrumbList
    bc_items = [{'@type':'ListItem','position':1,'name':'Home','item':BASE_URL+'/'}]
    for i,(lbl,url) in enumerate(breadcrumbs, 2):
        bc_items.append({'@type':'ListItem','position':i,'name':lbl,'item':url})
    bc_items.append({'@type':'ListItem','position':len(bc_items)+1,'name':title,'item':canon_url})
    schemas.append({'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':bc_items})

    # FAQPage
    valid_faqs = [f for f in faq if isinstance(f,dict) and f.get('question') and f.get('answer')]
    if valid_faqs:
        schemas.append({'@context':'https://schema.org','@type':'FAQPage',
            'mainEntity':[{'@type':'Question','name':f['question'],
                'acceptedAnswer':{'@type':'Answer','text':f['answer']}} for f in valid_faqs[:10]]})

    tags = ''
    for schema in schemas:
        tags += f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>\n'
    return tags

# ── Page Shell ───────────────────────────────────────────────────────

def page_shell(title_tag, meta_desc, canon_url, keywords, schemas_html,
               bc_html, body_html, extra_head=''):
    title_tag = title_tag[:60]
    meta_desc = meta_desc[:155]
    return f'''<!DOCTYPE html>
<html lang="hi-IN" dir="ltr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{e(title_tag)}</title>
  <meta name="description" content="{e(meta_desc)}"/>
  <meta name="keywords" content="{e(keywords)}"/>
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large"/>
  <link rel="canonical" href="{e(canon_url)}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:site_name" content="Top Sarkari Jobs"/>
  <meta property="og:title" content="{e(title_tag)}"/>
  <meta property="og:description" content="{e(meta_desc)}"/>
  <meta property="og:url" content="{e(canon_url)}"/>
  <meta property="og:image" content="{BASE_URL}/image.png"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{e(title_tag)}"/>
  <meta name="twitter:description" content="{e(meta_desc)}"/>
  {schemas_html}
  <link rel="icon" href="/image.ico"/>
  <link rel="stylesheet" href="/styles.css"/>
  <link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/>
  <noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>
  <link rel="manifest" href="/manifest.json"/>
  <meta name="theme-color" content="#0d2257"/>
  <script>window.__TSJ_STATIC_PAGE=true;window.__TSJ_PSR_DISABLED=true;window.__TSJ_RENDERER_DISABLED=true;</script>
  {extra_head}
  <style>{INLINE_CSS}</style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <div id="headerPlaceholder"></div>
  <script>fetch('/header.html',{{cache:'no-store'}}).then(r=>r.ok?r.text():null).catch(()=>null).then(h=>{{if(h){{var d=document.getElementById('headerPlaceholder');if(d)d.outerHTML=h;}}}})</script>
  <main id="main-content">
    <nav class="breadcrumb" aria-label="Breadcrumb">{bc_html}</nav>
    {body_html}
  </main>
  <div id="footerPlaceholder"></div>
  <script>fetch('/footer.html',{{cache:'no-store'}}).then(r=>r.ok?r.text():null).catch(()=>null).then(h=>{{if(h){{var d=document.getElementById('footerPlaceholder');if(d)d.outerHTML=h;}}}})</script>
  <script src="/tsj-menu.js" defer></script>
  <script src="/analytics.js" defer></script>
</body>
</html>'''

INLINE_CSS = """
/* ── Detail Page Core CSS ── */
.breadcrumb{background:#fff;border-bottom:1px solid #e2e8f0;padding:8px 12px;font-size:.74rem;color:#64748b;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.breadcrumb a{color:#1d4ed8;text-decoration:none}.breadcrumb a:hover{text-decoration:underline}
.breadcrumb .bc-sep{color:#d1d5db;font-size:.6rem}
.detail-wrap{max-width:900px;margin:0 auto;padding:12px 10px 50px}
.detail-header{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 20px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.detail-h1{font-size:1.2rem;font-weight:900;color:#0f172a;line-height:1.4;margin:0 0 8px}
.detail-badges{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.badge{display:inline-flex;align-items:center;gap:4px;font-size:.7rem;font-weight:700;text-transform:uppercase;padding:3px 10px;border-radius:20px;letter-spacing:.04em}
.badge-cat{background:#dbeafe;color:#1e40af}
.badge-loc{background:#dcfce7;color:#15803d}
.badge-mode{background:#ede9fe;color:#5b21b6}
.badge-yes{background:#dcfce7;color:#15803d}.badge-no{background:#fee2e2;color:#991b1b}
.stats-bar{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #e2e8f0;margin-top:10px}
.stat{text-align:center;padding:10px 4px;border-right:1px solid #e2e8f0}
.stat:last-child{border-right:none}
.stat-val{font-size:1rem;font-weight:800;color:#0f172a;word-break:break-word}
.stat-lbl{font-size:.65rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
@media(max-width:600px){.stats-bar{grid-template-columns:repeat(2,1fr)}.stat:nth-child(2){border-right:none}.stat:nth-child(3){border-top:1px solid #e2e8f0}.stat:nth-child(4){border-top:1px solid #e2e8f0;border-right:none}}
.notice{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;font-size:.8rem;color:#78350f;margin-bottom:14px;display:flex;gap:8px;align-items:flex-start}
.short-info{background:#eff6ff;border-left:4px solid #1d4ed8;padding:11px 14px;font-size:.84rem;color:#1e293b;line-height:1.7;margin-bottom:12px;border-radius:0 8px 8px 0;display:flex;gap:8px;align-items:flex-start}
/* Section cards */
.sec-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.04)}
.sec-head{display:flex;align-items:center;gap:8px;padding:10px 14px;color:#fff;font-size:.86rem;font-weight:700}
.sec-head h2{margin:0;font-size:.86rem;font-weight:700;color:#fff}
.sec-body{padding:0}
/* KV Table */
.kv-table{width:100%;border-collapse:collapse;font-size:.82rem}
.kv-table th,.kv-key{background:#f8fafc;color:#374151;font-weight:700;padding:9px 13px;text-align:left;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word;width:38%}
.kv-table td,.kv-val{padding:9px 13px;color:#1e293b;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word;overflow-wrap:break-word;line-height:1.6}
.kv-table tr:last-child th,.kv-table tr:last-child td{border-bottom:none}
.detail-kv th{width:35%}
.auto-link{color:#1d4ed8;word-break:break-all;font-size:.82rem}
.auto-link:hover{text-decoration:underline}
.date-last{color:#dc2626;font-weight:700}
/* Fee */
.fee-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:0;border-bottom:1px solid #f1f5f9}
.fee-cell{padding:10px 14px;border-right:1px solid #f1f5f9;border-bottom:1px solid #f1f5f9}
.fee-cat{display:block;font-size:.68rem;font-weight:700;text-transform:uppercase;color:#64748b;margin-bottom:4px;letter-spacing:.04em}
.fee-amt{font-size:.95rem;font-weight:800;color:#1e293b}
.fee-free{color:#16a34a}.fee-paid{color:#dc2626}
.fee-note{padding:9px 14px;font-size:.8rem;color:#78350f;background:#fffbeb;border-top:1px solid #fde68a;display:flex;gap:6px;align-items:flex-start}
/* Data table */
.tbl-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%}
.data-table{width:100%;border-collapse:collapse;font-size:.81rem;min-width:360px}
.data-table th{background:#1d4ed8;color:#fff;padding:9px 12px;font-weight:700;text-align:left;white-space:nowrap}
.data-table td{padding:9px 12px;border-bottom:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top;line-height:1.5}
.data-table tr:last-child td{border-bottom:none}
.data-table tr:nth-child(even) td{background:#f8fafc}
/* Steps */
.steps-wrap{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
.step-card{display:inline-flex;align-items:center;gap:7px;background:#f0f7ff;border:1px solid #bfdbfe;border-radius:8px;padding:7px 13px;font-size:.81rem;font-weight:600;color:#1e40af}
.step-num{background:#1e40af;color:#fff;border-radius:50%;width:20px;height:20px;display:inline-flex;align-items:center;justify-content:center;font-size:.66rem;font-weight:800;flex-shrink:0}
/* HTA */
.hta-list{list-style:none;margin:0;padding:0}
.hta-item{display:flex;align-items:flex-start;gap:12px;padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:.83rem;line-height:1.65}
.hta-item:last-child{border-bottom:none}
.hta-num{flex-shrink:0;width:26px;height:26px;background:#0f766e;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:800}
/* Instructions */
.inst-box{display:flex;align-items:flex-start;gap:10px;padding:9px 14px;border-bottom:1px solid #f1f5f9;font-size:.82rem;color:#78350f;line-height:1.6}
.inst-box:last-child{border-bottom:none}
.inst-box i{color:#ca8a04;flex-shrink:0;margin-top:2px}
/* Links */
.links-grid{display:flex;flex-wrap:wrap;gap:9px;padding:14px}
.lnk-btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:8px;font-size:.81rem;font-weight:700;text-decoration:none;white-space:nowrap;transition:all .15s;border:1px solid transparent;min-height:40px}
.btn-apply{background:#dcfce7;color:#15803d;border-color:#86efac}.btn-apply:hover{background:#15803d;color:#fff}
.btn-official{background:#d1fae5;color:#065f46;border-color:#6ee7b7}.btn-official:hover{background:#059669;color:#fff}
.btn-pdf{background:#fee2e2;color:#991b1b;border-color:#fca5a5}.btn-pdf:hover{background:#dc2626;color:#fff}
.btn-register{background:#fef3c7;color:#92400e;border-color:#fcd34d}.btn-register:hover{background:#d97706;color:#fff}
.btn-login{background:#ede9fe;color:#5b21b6;border-color:#c4b5fd}.btn-login:hover{background:#6d28d9;color:#fff}
.btn-admit{background:#ccfbf1;color:#0f766e;border-color:#5eead4}.btn-admit:hover{background:#0f766e;color:#fff}
.btn-answer{background:#e0e7ff;color:#3730a3;border-color:#a5b4fc}.btn-answer:hover{background:#3730a3;color:#fff}
.btn-syllabus{background:#f0fdf4;color:#15803d;border-color:#86efac}.btn-syllabus:hover{background:#15803d;color:#fff}
.btn-result{background:#fefce8;color:#713f12;border-color:#fde047}.btn-result:hover{background:#a16207;color:#fff}
.btn-merit{background:#f0f9ff;color:#0369a1;border-color:#7dd3fc}.btn-merit:hover{background:#0369a1;color:#fff}
.btn-score{background:#fdf4ff;color:#7e22ce;border-color:#e879f9}.btn-score:hover{background:#7e22ce;color:#fff}
.btn-default{background:#dbeafe;color:#1e40af;border-color:#93c5fd}.btn-default:hover{background:#1e40af;color:#fff}
/* FAQ */
.faq-item{border-bottom:1px solid #f1f5f9;padding:12px 14px}
.faq-item:last-child{border-bottom:none}
.faq-q{display:flex;gap:10px;align-items:flex-start;font-weight:700;color:#0f172a;font-size:.84rem;line-height:1.5;margin-bottom:8px}
.faq-icon{background:#1d4ed8;color:#fff;border-radius:6px;padding:2px 7px;font-size:.72rem;font-weight:800;flex-shrink:0;margin-top:1px}
.faq-a{display:flex;gap:10px;align-items:flex-start;font-size:.82rem;color:#475569;line-height:1.7}
.faq-a-icon{background:#15803d;color:#fff;border-radius:6px;padding:2px 7px;font-size:.72rem;font-weight:800;flex-shrink:0;margin-top:1px}
/* Nested */
.kv-nested th,.kv-nested td{font-size:.79rem;padding:6px 10px}
.nested-obj{border-left:3px solid #e2e8f0;margin:4px 0;padding-left:8px}
.val-list{margin:6px 0;padding-left:20px;font-size:.82rem;color:#374151;line-height:1.7}
.val-num{font-weight:700;color:#1e40af}
.val-text{color:#1e293b}
/* Edu sections */
.edu-sec{padding:12px 14px;border-bottom:1px solid #f1f5f9}
.edu-sec:last-child{border-bottom:none}
.edu-sec-h{font-size:.85rem;font-weight:700;color:#1e293b;margin:0 0 8px}
.edu-para{font-size:.82rem;color:#374151;line-height:1.7;margin:0 0 8px}
.mi-item{font-size:.82rem;color:#374151;line-height:1.6;padding:4px 0}
/* Internal links */
.rel-section{background:#fff;border:1px solid #e2e8f0;border-radius:12px;margin-top:16px;overflow:hidden}
.rel-head{padding:10px 14px;background:#f8fafc;border-bottom:1px solid #e2e8f0;font-size:.82rem;font-weight:700;color:#374151}
.rel-grid{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
.rel-btn{display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:8px;font-size:.78rem;font-weight:600;text-decoration:none;background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;transition:all .15s}
.rel-btn:hover{background:#1d4ed8;color:#fff;border-color:#1d4ed8;text-decoration:none}
/* Category listing */
.cat-wrap{max-width:900px;margin:0 auto;padding:12px 10px 50px}
.cat-header{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.cat-title{font-size:1.1rem;font-weight:900;color:#0f172a;margin:0 0 4px}
.cat-count{font-size:.78rem;color:#64748b}
.search-bar{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.search-bar input{flex:1;min-width:200px;padding:9px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:.84rem;outline:none}
.search-bar input:focus{border-color:#1d4ed8;box-shadow:0 0 0 2px #dbeafe}
.job-card-item{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.04);transition:box-shadow .15s}
.job-card-item:hover{box-shadow:0 4px 12px rgba(0,0,0,.1)}
.jci-title{font-size:.92rem;font-weight:800;color:#0f172a;line-height:1.4;margin-bottom:6px}
.jci-title a{color:inherit;text-decoration:none}.jci-title a:hover{color:#1d4ed8;text-decoration:underline}
.jci-meta{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.jci-badge{font-size:.68rem;font-weight:700;padding:2px 8px;border-radius:12px}
.jci-org{color:#64748b;font-size:.8rem;margin-bottom:6px;display:flex;gap:5px;align-items:center}
.jci-date{font-size:.77rem;font-weight:700}
.jci-date.urgent{color:#dc2626}
.jci-links{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.jci-link{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:6px;font-size:.73rem;font-weight:700;text-decoration:none;transition:all .12s;border:1px solid transparent;min-height:30px}
/* Pagination */
.pagination{display:flex;justify-content:center;gap:6px;margin-top:20px;flex-wrap:wrap}
.page-btn{padding:7px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:.8rem;font-weight:600;cursor:pointer;background:#fff;color:#374151;transition:all .12s;min-height:36px}
.page-btn:hover,.page-btn.active{background:#1d4ed8;color:#fff;border-color:#1d4ed8}
"""

# ── Breadcrumb HTML ──────────────────────────────────────────────────

def bc_html(crumbs):
    """crumbs: list of (label, url) or (label, None) for last"""
    parts = [f'<a href="/"  class="bc-home">Home</a>']
    for lbl, url in crumbs:
        if url:
            parts.append(f'<span class="bc-sep">›</span><a href="{e(url)}">{e(lbl)}</a>')
        else:
            parts.append(f'<span class="bc-sep">›</span><span aria-current="page">{e(lbl)}</span>')
    return ''.join(parts)

# ── Job Detail Page Builder ──────────────────────────────────────────

def build_job_detail_page(job_obj, slug, canon_url, breadcrumbs):
    bd     = job_obj.get('basic_details', {}) or {}
    dates  = job_obj.get('important_dates', {}) or {}
    il     = job_obj.get('important_links', {}) or {}
    faq_d  = job_obj.get('faq', []) or []
    seo    = job_obj.get('seo_tags', []) or []

    title     = safe(bd.get('job_title','') or 'Government Job ' + str(YEAR))
    org       = safe(bd.get('organization_name','') or 'Government of India')
    vacancies = safe(bd.get('total_vacancies','') or '')
    last_d    = safe(dates.get('last_date_to_apply','') or dates.get('last_date','') or '')
    apply_m   = safe(bd.get('application_mode','') or 'Online')
    location  = safe(bd.get('job_location','') or 'India')
    short_i   = safe(bd.get('short_information','') or '')
    kw_list   = (seo if isinstance(seo, list) else []) + [org, location, 'sarkari job', str(YEAR)]
    keywords  = ', '.join(str(k) for k in kw_list if k)[:200]

    title_tag  = f"{title[:40]} {YEAR} | Top Sarkari Jobs"
    meta_desc  = (short_i[:130] or f"{title}: Apply online, check vacancies, dates.") + f" | {YEAR}"

    schemas_html = build_schemas(job_obj, canon_url, breadcrumbs)
    crumb_html   = bc_html(breadcrumbs + [(title, None)])

    # Quick apply banner from important_links
    apply_url = (safe(il.get('apply_online','')) or
                 safe(il.get('registration_link','')) or
                 safe(bd.get('official_website','')))
    apply_banner = ''
    if apply_url and not is_blocked(apply_url):
        apply_banner = f'''<div class="apply-banner">
  <a href="{e(apply_url)}" target="_blank" rel="noopener noreferrer" class="apply-cta">
    <i class="fa-solid fa-paper-plane"></i> Apply Online / Official Website
  </a>
</div>'''

    header_html = f'''<div class="detail-wrap">
  <div class="notice"><i class="fa-solid fa-triangle-exclamation"></i>
    <span><strong>Important:</strong> Always verify details on the official website before applying. Dates &amp; eligibility may change.</span>
  </div>
  <div class="detail-header">
    <div class="detail-badges">
      <span class="badge badge-cat"><i class="fa-solid fa-briefcase"></i> {e(safe(job_obj.get("category","Govt Job")).replace("_"," "))}</span>
      <span class="badge badge-loc"><i class="fa-solid fa-map-pin"></i> {e(location[:25])}</span>
      <span class="badge badge-mode"><i class="fa-solid fa-laptop"></i> {e(apply_m)}</span>
    </div>
    <h1 class="detail-h1">{e(title)}</h1>
    <div class="stats-bar">
      <div class="stat"><div class="stat-val">{e(vacancies or "—")}</div><div class="stat-lbl">Vacancies</div></div>
      <div class="stat"><div class="stat-val" style="color:#dc2626">{e(last_d or "—")}</div><div class="stat-lbl">Last Date</div></div>
      <div class="stat"><div class="stat-val">{e(apply_m or "—")}</div><div class="stat-lbl">Apply Mode</div></div>
      <div class="stat"><div class="stat-val">{e(location[:15] or "India")}</div><div class="stat-lbl">Location</div></div>
    </div>
  </div>
  {apply_banner}
  {build_all_sections(job_obj)}
  {build_internal_links(job_obj, slug)}
</div>'''

    extra_css = '''<style>
.apply-banner{margin-bottom:14px}
.apply-cta{display:flex;align-items:center;justify-content:center;gap:8px;background:linear-gradient(135deg,#059669,#047857);color:#fff;padding:13px 20px;border-radius:10px;font-size:.92rem;font-weight:800;text-decoration:none;text-align:center}
.apply-cta:hover{background:linear-gradient(135deg,#047857,#065f46);text-decoration:none}
</style>'''

    return page_shell(title_tag, meta_desc, canon_url, keywords,
                      schemas_html, crumb_html, header_html, extra_css)

def build_internal_links(job_obj, slug):
    cat = safe(job_obj.get('category',''))
    bd  = job_obj.get('basic_details', {}) or {}
    loc = safe(bd.get('job_location',''))
    links = [
        ('/section/latest-jobs/', 'Latest Jobs', 'fa-briefcase'),
        ('/section/admit-card/', 'Admit Cards', 'fa-id-card'),
        ('/section/results/', 'Results', 'fa-trophy'),
        ('/section/answer-key/', 'Answer Keys', 'fa-key'),
        ('/state/', 'State Jobs', 'fa-map-location-dot'),
        ('/education/', 'Education Updates', 'fa-graduation-cap'),
    ]
    btns = ''.join(f'<a href="{e(url)}" class="rel-btn"><i class="fa-solid {icon}"></i> {e(label)}</a>'
                   for url,label,icon in links)
    return f'<div class="rel-section"><div class="rel-head">More Links</div><div class="rel-grid">{btns}</div></div>'

# ── Category/Listing Page Builder ────────────────────────────────────

def build_job_card_html(job_obj, page_type='job'):
    bd    = job_obj.get('basic_details', {}) or {}
    dates = job_obj.get('important_dates', {}) or {}
    il    = job_obj.get('important_links', {}) or {}
    title = safe(bd.get('job_title','') or job_obj.get('title','') or job_obj.get('name',''))
    if not title: return ''
    slug  = slugify(title)
    org   = safe(bd.get('organization_name','') or 'Government')
    vac   = safe(bd.get('total_vacancies',''))
    ld    = safe(dates.get('last_date_to_apply','') or dates.get('last_date',''))
    mode  = safe(bd.get('application_mode','') or 'Online')
    notif = safe(bd.get('notification_number',''))
    cat   = safe(job_obj.get('category',''))

    # Quick action links
    ql = ''
    for key, lbl, css in [
        ('apply_online','Apply','jci-link btn-apply'),
        ('notification_pdf','Notification','jci-link btn-pdf'),
        ('result_link','Result','jci-link btn-result'),
        ('admit_card','Admit Card','jci-link btn-admit'),
        ('answer_key','Answer Key','jci-link btn-answer'),
    ]:
        url = safe(il.get(key,''))
        if url and not is_blocked(url):
            icon = {'apply_online':'fa-paper-plane','notification_pdf':'fa-file-pdf',
                    'result_link':'fa-trophy','admit_card':'fa-id-card','answer_key':'fa-key'}.get(key,'fa-link')
            dl = ' download' if 'pdf' in key and url.lower().endswith('.pdf') else ''
            ql += f'<a href="{e(url)}" class="{css}" target="_blank" rel="noopener noreferrer"{dl}><i class="fa-solid {icon}"></i> {e(lbl)}</a>'

    urgent = ''
    if ld:
        try:
            from datetime import datetime
            for fmt in ['%d %b %Y','%d/%m/%Y','%d-%m-%Y']:
                try:
                    dt = datetime.strptime(ld, fmt)
                    if (dt.date() - date.today()).days <= 7:
                        urgent = ' urgent'
                    break
                except: pass
        except: pass

    vac_badge = f'<span class="jci-badge" style="background:#dcfce7;color:#15803d">{e(vac)} Posts</span>' if vac else ''
    mode_badge = f'<span class="jci-badge" style="background:#ede9fe;color:#5b21b6">{e(mode)}</span>'
    notif_badge = f'<span class="jci-badge" style="background:#f1f5f9;color:#475569">{e(notif)}</span>' if notif else ''

    return f'''<article class="job-card-item" data-title="{e(title.lower())}" data-org="{e(org.lower())}">
  <div class="jci-title"><a href="/jobs/{e(slug)}/">{e(title)}</a></div>
  <div class="jci-org"><i class="fa-regular fa-building"></i> {e(org[:60])}</div>
  <div class="jci-meta">{vac_badge}{mode_badge}{notif_badge}</div>
  {f'<div class="jci-date{urgent}"><i class="fa-regular fa-clock"></i> Last Date: {e(ld)}</div>' if ld else ''}
  {f'<div class="jci-links">{ql}</div>' if ql else ''}
</article>'''

def build_listing_page(title, jobs, canon_url, breadcrumbs, description=''):
    title_tag = f"{title} {YEAR} — Notification, Apply Online | Top Sarkari Jobs"
    meta_desc = description[:155] if description else f"{title}: View all latest job notifications, apply online, check dates. {YEAR}"
    collection_schema = {'@context':'https://schema.org','@type':'CollectionPage',
        'name':title,'description':meta_desc,'url':canon_url}
    bc_list = [{'@type':'ListItem','position':1,'name':'Home','item':BASE_URL+'/'}]
    for i,(lbl,url) in enumerate(breadcrumbs, 2):
        bc_list.append({'@type':'ListItem','position':i,'name':lbl,'item':BASE_URL+url if url.startswith('/') else url})
    bc_list.append({'@type':'ListItem','position':len(bc_list)+1,'name':title,'item':canon_url})
    bc_schema_obj = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':bc_list}
    schemas_tag = (f'<script type="application/ld+json">{json.dumps(collection_schema,ensure_ascii=False)}</script>'
                  +f'<script type="application/ld+json">{json.dumps(bc_schema_obj,ensure_ascii=False)}</script>')
    
    bc_items = [('Home', '/')]
    bc_items += breadcrumbs
    bc_items += [(title, None)]
    crumb_html = bc_html(bc_items)

    cards_html = ''.join(build_job_card_html(j) for j in jobs if j)
    if not cards_html:
        cards_html = '<div style="padding:30px;text-align:center;color:#94a3b8"><i class="fa-solid fa-inbox" style="font-size:2rem;display:block;margin-bottom:8px"></i>No records found.</div>'

    desc_p = f'<p style="font-size:.82rem;color:#64748b;margin-top:6px">{e(description[:200])}</p>' if description else ''
    filter_js = ('<script>function filterJobs(q){'
                 'q=q.toLowerCase().trim();'
                 'var cards=document.querySelectorAll(".job-card-item");'
                 'for(var i=0;i<cards.length;i++){'
                 'var t=cards[i].dataset.title||"",o=cards[i].dataset.org||"";'
                 'cards[i].style.display=(!q||t.includes(q)||o.includes(q))?"":"none";}}'
                 '</script>')
    body = (f'<div class="cat-wrap">'
            f'<div class="cat-header">'
            f'<h1 class="cat-title">{e(title)}</h1>'
            f'<p class="cat-count">{len(jobs)} records</p>'
            f'{desc_p}</div>'
            f'<div class="search-bar">'
            f'<input type="search" id="jobSearch" placeholder="Search by keyword, organization..." '
            f'aria-label="Search jobs" onkeyup="filterJobs(this.value)" autocomplete="off"/>'
            f'</div>'
            f'<div id="jobList">{cards_html}</div>'
            f'</div>'
            f'{filter_js}')

    return page_shell(title_tag[:60], meta_desc, canon_url, f"{title}, sarkari jobs {YEAR}",
                      schemas_tag, crumb_html, body)

# ── Load JSON Data ───────────────────────────────────────────────────

print("Loading JSON data...")
with open(CJ_FILE, encoding='utf-8') as f:
    CJ = json.load(f)
with open(DU_FILE, encoding='utf-8') as f:
    DU = json.load(f)

FJA   = CJ.get('freejobalert_categories', {})
SARK  = (CJ.get('sarkari_data',{}) or {}).get('jobs', [])
EDU   = (CJ.get('education_jobs',{}) or {}).get('sections', [])
STATE = (CJ.get('state_jobs',{}) or {}).get('sections', [])
DU_SECS = DU.get('sections', [])

# ── GENERATE ALL PAGES ───────────────────────────────────────────────

written = 0

def write(path, html_content):
    global written
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    written += 1

# ────────────────────────────────────────────────────────────────────
# 1. JOB DETAIL PAGES — /jobs/{slug}/
# ────────────────────────────────────────────────────────────────────
print("Generating job detail pages...")
seen_job_slugs = {}

for cat, jobs_list in FJA.items():
    if not isinstance(jobs_list, list): continue
    for job in jobs_list:
        bd = job.get('basic_details', {}) or {}
        title = safe(bd.get('job_title',''))
        if not title: continue
        slug = slugify(title)
        if slug in seen_job_slugs:
            slug = f"{slug}-{cat.lower().replace('_','-')}"[:80]
        seen_job_slugs[slug] = cat
        job['category'] = cat
        canon = f"{BASE_URL}/jobs/{slug}/"
        bc = [('Latest Jobs', '/section/latest-jobs/')]
        path = str(ROOT / 'jobs' / slug / 'index.html')
        write(path, build_job_detail_page(job, slug, canon, bc))

# Sarkari data jobs
for job in SARK:
    title = safe(job.get('title',''))
    if not title: continue
    slug = slugify(title)
    if slug in seen_job_slugs: continue
    seen_job_slugs[slug] = job.get('category','')
    canon = f"{BASE_URL}/jobs/{slug}/"
    # Normalise structure
    bd = {'job_title':title,'organization_name':safe(job.get('organization','')),
          'total_vacancies':safe(job.get('total_post','')),
          'application_mode':safe(job.get('apply_mode','Online')),
          'job_location':safe(job.get('job_location','India')),
          'short_information':safe(job.get('short_information','')),
          'last_updated':safe(job.get('post_date','')),}
    imp_dates = job.get('important_dates') or {}
    useful = job.get('useful_links') or []
    il = job.get('important_links') or {}
    if isinstance(useful, list) and useful and not il:
        il_built = {}
        for lnk in useful:
            if not isinstance(lnk, dict): continue
            href = lnk.get('links') or lnk.get('url') or ''
            if isinstance(href, list): href = href[0] if href else ''
            href = str(href or '').strip()
            t = (lnk.get('title') or '').lower()
            if not href.startswith('http'): continue
            key = ('apply_online' if 'apply' in t else 'notification_pdf' if any(x in t for x in ['notif','pdf']) else
                   'result_link' if 'result' in t else 'admit_card' if 'admit' in t else
                   'answer_key' if 'answer' in t else 'official_website' if 'official' in t else 'click_here')
            if key in il_built:
                ex = il_built[key]; il_built[key] = (ex if isinstance(ex,list) else [ex]) + [href]
            else: il_built[key] = href
        il = il_built
    full = dict(job); full['basic_details']=bd; full['important_dates']=imp_dates; full['important_links']=il
    bc = [('Latest Jobs', '/section/latest-jobs/')]
    path = str(ROOT / 'jobs' / slug / 'index.html')
    write(path, build_job_detail_page(full, slug, canon, bc))

print(f"  Job detail pages: {written}")

# ────────────────────────────────────────────────────────────────────
# 2. CATEGORY LISTING PAGES
# ────────────────────────────────────────────────────────────────────
print("Generating category listing pages...")

# Map sarkari categories to URL slugs
SARK_CAT_MAP = {
    'OFFLINE_FORM':    ('offline-form',        'Offline Form'),
    'LATEST_JOBS NEW': ('latest-jobs-new',      'Latest Jobs New'),
    'SR_Latest_Jobs':  ('latest-jobs',          'Latest Jobs'),
    'SR_Result':       ('result',               'Results'),
    'SR_Admit_Card':   ('admit-card',           'Admit Cards'),
    'SR_Admission':    ('admission',            'Admissions'),
    'SR_Answer_Key':   ('answer-key',           'Answer Keys'),
    'UPCOMING_JOBS':   ('upcoming-jobs',        'Upcoming Jobs'),
    'STATE_JOBS':      ('state-jobs-central',   'State Jobs'),
    'CENTRAL_JOBS':    ('central-jobs',         'Central Jobs'),
    'ADMISSIONS':      ('admissions',           'Admissions'),
}

# FJA category listing pages
FJA_CAT_MAP = {
    '10TH_Pass':         ('10th-pass-jobs',          '10th Pass Jobs'),
    '8TH_Pass':          ('8th-pass-jobs',           '8th Pass Jobs'),
    '12TH_Pass':         ('12th-pass-jobs',          '12th Pass Jobs'),
    'Diploma':           ('diploma-jobs',            'Diploma Jobs'),
    'ITI':               ('iti-jobs',                'ITI Jobs'),
    'B_Tech_BE':         ('btech-be-jobs',           'B.Tech / BE Jobs'),
    'B_Com':             ('bcom-jobs',               'B.Com Jobs'),
    'Any_Graduate':      ('any-graduate-jobs',       'Any Graduate Jobs'),
    'Any_Post_Graduate': ('post-graduate-jobs',      'Post Graduate Jobs'),
    'Railway_Jobs':      ('railway-jobs',            'Railway Jobs'),
    'Police_Defence':    ('police-defence-jobs',     'Police / Defence Jobs'),
    'Teaching_Faculty':  ('teaching-faculty-jobs',   'Teaching / Faculty Jobs'),
    'Bank_Jobs':         ('bank-jobs',               'Bank Jobs'),
    'Medical_Hospital':  ('medical-hospital-jobs',   'Medical / Hospital Jobs'),
    'Last_Date_Reminder':('last-date-reminder',      'Last Date Reminder'),
    'Latest_Notifications':('latest-notifications',  'Latest Notifications'),
}

for cat_key, (url_slug, label) in FJA_CAT_MAP.items():
    jobs = FJA.get(cat_key, [])
    if not isinstance(jobs, list): continue
    canon = f"{BASE_URL}/section/{url_slug}/"
    bc    = [('Section', '/section/')]
    path  = str(ROOT / 'section' / url_slug / 'index.html')
    page  = build_listing_page(label, jobs, canon, bc)
    write(path, page)

for cat_key, (url_slug, label) in SARK_CAT_MAP.items():
    jobs = [j for j in SARK if j.get('category') == cat_key]
    if not jobs: continue
    # Normalise
    norm_jobs = []
    for j in jobs:
        bd2 = {'job_title':safe(j.get('title','')),
               'organization_name':safe(j.get('organization','')),
               'total_vacancies':safe(j.get('total_post','')),
               'application_mode':safe(j.get('apply_mode','Online')),
               'job_location':'India',
               'short_information':safe(j.get('short_information','')),
               'last_updated':safe(j.get('post_date',''))}
        imp = j.get('important_dates') or {}
        il2 = j.get('important_links') or {}
        norm_jobs.append({'basic_details':bd2,'important_dates':imp,'important_links':il2,'category':cat_key})
    canon = f"{BASE_URL}/section/{url_slug}/"
    bc    = [('Section', '/section/')]
    path  = str(ROOT / 'section' / url_slug / 'index.html')
    write(path, build_listing_page(label, norm_jobs, canon, bc))

print(f"  Category pages written (total so far): {written}")

# ────────────────────────────────────────────────────────────────────
# 3. DAILY UPDATES CATEGORY PAGES (from dailyupdates.json)
# ────────────────────────────────────────────────────────────────────
print("Generating daily update pages...")

DU_SLUG_MAP = {
    'Govt Scheme Yojna':  'govt-scheme-yojna',
    'ImportantCSC PDF':   'important-csc-pdf',
    'ImportantCSC link':  'important-csc-link',
    'Today Updates':      'today-updates',
}

for sec in DU_SECS:
    sec_title = sec.get('title','') or sec.get('id','')
    slug_key  = DU_SLUG_MAP.get(sec_title, slugify(sec_title))
    items     = sec.get('items', [])
    # Build cards from simple name/url items
    cards = ''.join(
        f'<article class="job-card-item">'
        f'<div class="jci-title"><a href="{e(str(item.get("url","#")))}" target="_blank" rel="noopener noreferrer">{e(safe(item.get("name","")))}</a></div>'
        f'</article>'
        for item in items if item.get('name')
    )
    canon = f"{BASE_URL}/section/{slug_key}/"
    bc    = [('Today Updates', '/section/today-updates/')]
    col_s = {'@context':'https://schema.org','@type':'CollectionPage','name':sec_title,'url':canon}
    bc_s  = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[
        {'@type':'ListItem','position':1,'name':'Home','item':BASE_URL+'/'},
        {'@type':'ListItem','position':2,'name':'Today Updates','item':BASE_URL+'/section/today-updates/'},
        {'@type':'ListItem','position':3,'name':sec_title,'item':canon},
    ]}
    schemas_tag = (f'<script type="application/ld+json">{json.dumps(col_s,ensure_ascii=False)}</script>'
                  +f'<script type="application/ld+json">{json.dumps(bc_s,ensure_ascii=False)}</script>')
    crumb = bc_html([('Home','/'),('Today Updates','/section/today-updates/'),(sec_title, None)])
    body  = f'<div class="cat-wrap"><div class="cat-header"><h1 class="cat-title">{e(sec_title)}</h1><p class="cat-count">{len(items)} items</p></div><div id="jobList">{cards}</div></div>'
    title_tag = f"{sec_title} {YEAR} | Top Sarkari Jobs"
    meta_desc = f"Latest {sec_title} updates {YEAR}. All important links, PDFs and notifications."
    page = page_shell(title_tag[:60], meta_desc, canon, sec_title, schemas_tag, crumb, body)
    path = str(ROOT / 'section' / slug_key / 'index.html')
    write(path, page)

# ────────────────────────────────────────────────────────────────────
# 4. STATE DETAIL PAGES — /state/{state-slug}/{job-slug}/
# ────────────────────────────────────────────────────────────────────
print("Generating state job pages...")

STATE_URL_MAP = {
    'andaman-and-nicobar':'andaman-nicobar','dadra-and-nagar-haveli':'dadra-nh',
    'daman-and-diu':'daman-diu','jammu-and-kashmir':'jk',
}

for sec in STATE:
    state_name = safe(sec.get('state') or sec.get('title',''))
    state_slug = STATE_URL_MAP.get(slugify(state_name), slugify(state_name))
    state_url  = f"/state-jobs/{state_slug}/"

    for item in sec.get('items', []):
        name = safe(item.get('name','') or item.get('title',''))
        if not name: continue
        job_slug = slugify(name)[:80]
        item_url = safe(item.get('url',''))

        detail = item.get('detail') or {}
        if isinstance(detail, str):
            try: detail = json.loads(detail)
            except: detail = {}

        bd3 = detail.get('basic_details', {}) or {}
        if not bd3.get('job_title'): bd3['job_title'] = name
        if not bd3.get('job_location'): bd3['job_location'] = f"{state_name}, India"
        detail['basic_details'] = bd3
        if not detail.get('important_dates'): detail['important_dates'] = {}
        if item.get('lastDate') and not detail['important_dates'].get('last_date_to_apply'):
            detail['important_dates']['last_date_to_apply'] = item['lastDate']
        detail['source_url'] = item_url
        detail['category'] = state_name

        canon = f"{BASE_URL}/state-jobs/{state_slug}/{job_slug}/"
        bc    = [('State Jobs', '/state-jobs/'), (state_name, state_url)]
        path  = str(ROOT / 'state' / state_slug / job_slug / 'index.html')
        write(path, build_job_detail_page(detail, job_slug, canon, bc))

    # State listing page
    all_state_jobs = [{'basic_details':{'job_title':safe(it.get('name','')),
        'organization_name':state_name,'application_mode':'Online',
        'job_location':f"{state_name}, India"},
        'important_dates':{'last_date_to_apply':safe(it.get('lastDate',''))},
        'important_links':((it.get('detail') or {}).get('important_links') or {}),
        'category':state_name}
        for it in sec.get('items',[]) if it.get('name')]
    if all_state_jobs:
        canon2 = f"{BASE_URL}/state-jobs/{state_slug}/"
        bc2    = [('State Jobs', '/state-jobs/')]
        path2  = str(ROOT / 'state' / state_slug / 'index.html')
        write(path2, build_listing_page(f"{state_name} Government Jobs", all_state_jobs, canon2, bc2,
                                        f"All government job notifications from {state_name}."))

print(f"  State pages (total so far): {written}")

# ────────────────────────────────────────────────────────────────────
# 5. QUALIFICATION PAGES — /qualification/{slug}/
# ────────────────────────────────────────────────────────────────────
print("Generating qualification pages...")

for cat_key, jobs_list in FJA.items():
    if not isinstance(jobs_list, list) or not jobs_list: continue
    q_label = cat_key.replace('_',' ').title()
    q_slug  = cat_key.lower().replace('_','-')
    canon   = f"{BASE_URL}/qualification/{q_slug}/"
    bc      = [('Qualification Wise Jobs', '/qualification/')]
    path    = str(ROOT / 'qualification' / q_slug / 'index.html')
    write(path, build_listing_page(f"{q_label} Jobs", jobs_list, canon, bc,
                                   f"Government job notifications for {q_label} candidates."))

# ────────────────────────────────────────────────────────────────────
# 6. EDUCATION STATE PAGES — /education/{state-slug}/
# ────────────────────────────────────────────────────────────────────
print("Generating education pages...")

for sec in EDU:
    sec_id    = safe(sec.get('id','') or sec.get('title',''))
    sec_title = safe(sec.get('title','') or sec_id)
    if not sec_id: continue
    # Detail pages
    for item in sec.get('items', []):
        name = safe(item.get('name','') or item.get('examName',''))
        if not name: continue
        item_slug = slugify(name)[:80]
        detail    = item.get('detail') or {}
        full_d = {
            'basic_details': {
                'job_title': detail.get('title') or name,
                'organization_name': sec_title,
                'job_location': sec_title,
                'short_information': detail.get('short_info',''),
                'last_updated': safe(item.get('postDate') or item.get('date','')),
            },
            'important_dates': {'notification_date': safe(item.get('date') or item.get('postDate',''))},
            'important_links': detail.get('important_links') or {},
            'sections': detail.get('sections') or [],
            'faq': detail.get('faq') or [],
            'source_url': safe(item.get('url','')),
            'category': sec_title,
        }
        canon = f"{BASE_URL}/education/{sec_id}/{item_slug}/"
        bc    = [('Education', '/education/'), (sec_title, f"/education/{sec_id}/")]
        path  = str(ROOT / 'education' / sec_id / item_slug / 'index.html')
        write(path, build_job_detail_page(full_d, item_slug, canon, bc))

    # Section listing page
    edu_jobs = [{'basic_details':{'job_title':safe(it.get('name') or it.get('examName','')),
        'organization_name':sec_title,'application_mode':'Online','job_location':sec_title,
        'last_updated':safe(it.get('postDate') or it.get('date',''))},
        'important_dates':{'notification_date':safe(it.get('date') or it.get('postDate',''))},
        'important_links':(it.get('detail') or {}).get('important_links') or {},
        'category':sec_title}
        for it in sec.get('items',[]) if it.get('name') or it.get('examName')]
    if edu_jobs:
        canon2 = f"{BASE_URL}/education/{sec_id}/"
        bc2    = [('Education', '/education/')]
        path2  = str(ROOT / 'education' / sec_id / 'index.html')
        write(path2, build_listing_page(f"{sec_title} Education Updates", edu_jobs, canon2, bc2))

print(f"  Total pages written: {written}")
print("\n✅ WEBSITE GENERATION COMPLETE!")
print(f"   Job detail pages + all categories + states + qualifications + education")
print(f"   Total pages: {written}")
