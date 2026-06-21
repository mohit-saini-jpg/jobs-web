"""
generate_all_pages.py
=====================
Generates ALL detail pages with ONE unified 16-section layout:
  /jobs/{slug}/index.html          ← already done by generate_jobs.py
  /state/{state}/{slug}/index.html ← NEW
  /education/{section}/{slug}/index.html ← NEW
  /category/study/{qual}/{slug}/index.html ← NEW

Single layout for every page type. No JS renderer needed.
"""

import json, re, os, html as html_mod, shutil
from datetime import date

SRC      = "Complete_Jobs_Full_Data.json"
BASE_URL = "https://www.topsarkarijobs.com"
TODAY    = date.today().isoformat()

BLOCKED_DOMAINS = {"sarkariresult.com","freejobalert.com","sarkariresultshine.com","sarkarinetwork.com"}

# ── Helpers ────────────────────────────────────────────────────────
def e(s): return html_mod.escape(str(s or ''), quote=True)

def safe(v):
    if v is None: return ''
    if isinstance(v, str): return v.strip()
    if isinstance(v, (int, float, bool)): return str(v).strip()
    if isinstance(v, list): return ', '.join(safe(x) for x in v if x)
    if isinstance(v, dict):
        for k in ['text','value','name','description','details','qualification','eligibility','content']:
            if isinstance(v.get(k), str) and v[k].strip(): return v[k].strip()
        return ' | '.join(safe(val) for val in v.values() if val)
    return str(v).strip()

def slugify(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text[:80].strip('-') or 'page'

def is_blocked(url):
    return any(d in str(url).lower() for d in BLOCKED_DOMAINS)

def normalise_date(raw):
    if not raw: return None
    raw = str(raw).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw): return raw
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    m1 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', raw)
    if m1: return f"{m1.group(3)}-{int(m1.group(2)):02d}-{int(m1.group(1)):02d}"
    m2 = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', raw)
    if m2:
        mo = months.get(m2.group(2)[:3].lower())
        if mo: return f"{m2.group(3)}-{mo:02d}-{int(m2.group(1)):02d}"
    return None

# ── CSS (inline, same as jobs pages) ──────────────────────────────
COMMON_CSS = """
*,*::before,*::after{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f4f8;margin:0;color:#1e293b}
main{min-height:60vh}
a{text-decoration:none}
.pg-wrap{max-width:860px;margin:0 auto;padding:12px 10px 40px}
.bc{font-size:.75rem;color:#64748b;margin-bottom:12px;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.bc a{color:#1d4ed8}
.bc a:hover{text-decoration:underline}
.bc i{font-size:.6rem;color:#d1d5db}
.notice-bar{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;font-size:.8rem;color:#78350f;margin-bottom:12px;display:flex;gap:8px;align-items:flex-start}
.notice-bar i{flex-shrink:0;margin-top:2px}
/* ── Header card ── */
.jd-header{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px 0;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.jd-title{font-size:1.15rem;font-weight:800;color:#0f172a;line-height:1.4;margin:0 0 8px}
.jd-badge-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.jd-badge{display:inline-flex;align-items:center;gap:4px;background:#dbeafe;color:#1e40af;font-size:.71rem;font-weight:700;text-transform:uppercase;padding:3px 8px;border-radius:12px}
.jd-stats{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #e2e8f0;width:100%}
.jd-stat{padding:11px 6px;text-align:center;border-right:1px solid #e2e8f0}
.jd-stat:last-child{border-right:none}
.jd-stat-val{font-size:.95rem;font-weight:800;color:#0f172a}
.jd-stat-lbl{font-size:.67rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
@media(max-width:600px){.jd-stats{grid-template-columns:repeat(2,1fr)}.jd-stat:nth-child(2){border-right:none}.jd-stat:nth-child(3){border-top:1px solid #e2e8f0}.jd-stat:nth-child(4){border-top:1px solid #e2e8f0;border-right:none}}
/* ── Section cards ── */
.job-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.job-card-head{display:flex;align-items:center;gap:8px;padding:9px 14px;color:#fff;font-size:.86rem;font-weight:700}
.job-card-head h2{margin:0;font-size:.86rem;font-weight:700}
/* ── KV Table ── */
.jd-table{width:100%;border-collapse:collapse;font-size:.82rem}
.jd-table th{width:38%;background:#f8fafc;color:#374151;font-weight:700;padding:8px 12px;text-align:left;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word}
.jd-table td{padding:8px 12px;color:#1e293b;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word;overflow-wrap:break-word}
.jd-table tr:last-child th,.jd-table tr:last-child td{border-bottom:none}
.jd-table a{color:#1d4ed8;word-break:break-all}
/* ── Vacancy table ── */
.tbl-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%}
.vac-table{width:100%;border-collapse:collapse;font-size:.82rem;min-width:380px}
.vac-table th{background:#1d4ed8;color:#fff;padding:8px 12px;font-weight:700;white-space:nowrap;text-align:left}
.vac-table td{padding:8px 12px;border-bottom:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top}
.vac-table .vac-tot td{border-bottom:none;font-weight:700;background:#f0f9ff}
/* ── Fee grid ── */
.fee-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}
.fee-item{padding:10px 14px;border-right:1px solid #e9eef4;border-bottom:1px solid #e9eef4}
.fee-label{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:3px}
.fee-val{font-size:.9rem;font-weight:700;color:#1e293b}
.fee-val.free{color:#16a34a}
.fee-val.paid{color:#dc2626}
.fee-note{padding:9px 14px;font-size:.81rem;color:#78350f;background:#fffbeb;border-top:1px solid #fde68a}
/* ── Selection steps ── */
.sel-steps{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
.sel-step{display:inline-flex;align-items:center;gap:6px;background:#f0f7ff;border:1px solid #bfdbfe;border-radius:8px;padding:6px 12px;font-size:.8rem;font-weight:600;color:#1e40af}
.sel-num{background:#1e40af;color:#fff;border-radius:50%;width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;font-size:.65rem;font-weight:800;flex-shrink:0}
/* ── How to apply ── */
.hta-list{list-style:none;margin:0;padding:0}
.hta-item{display:flex;align-items:flex-start;gap:12px;padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:.83rem;color:#1e293b;line-height:1.65}
.hta-item:last-child{border-bottom:none}
.hta-num{flex-shrink:0;min-width:24px;height:24px;background:#0f766e;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:800}
/* ── Instructions ── */
.inst-list{list-style:none;margin:0;padding:0}
.inst-item{display:flex;align-items:flex-start;gap:10px;padding:9px 14px;border-bottom:1px solid #f1f5f9;font-size:.82rem;color:#78350f;line-height:1.6}
.inst-item:last-child{border-bottom:none}
.inst-item i{color:#ca8a04;flex-shrink:0;margin-top:2px}
/* ── Link buttons ── */
.links-grid{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
.link-btn{display:inline-flex;align-items:center;gap:5px;padding:7px 14px;border-radius:8px;font-size:.8rem;font-weight:700;text-decoration:none;white-space:nowrap;transition:all .15s;border:1px solid transparent}
.btn-blue{background:#dbeafe;color:#1e40af;border-color:#93c5fd}.btn-blue:hover{background:#1e40af;color:#fff}
.btn-green{background:#d1fae5;color:#065f46;border-color:#6ee7b7}.btn-green:hover{background:#059669;color:#fff}
.btn-red{background:#fee2e2;color:#991b1b;border-color:#fca5a5}.btn-red:hover{background:#dc2626;color:#fff}
.btn-orange{background:#fef3c7;color:#92400e;border-color:#fcd34d}.btn-orange:hover{background:#d97706;color:#fff}
.btn-purple{background:#ede9fe;color:#5b21b6;border-color:#c4b5fd}.btn-purple:hover{background:#6d28d9;color:#fff}
.btn-teal{background:#ccfbf1;color:#0f766e;border-color:#5eead4}.btn-teal:hover{background:#0f766e;color:#fff}
.btn-indigo{background:#e0e7ff;color:#3730a3;border-color:#a5b4fc}.btn-indigo:hover{background:#3730a3;color:#fff}
.btn-gray{background:#f1f5f9;color:#475569;border-color:#cbd5e1}.btn-gray:hover{background:#475569;color:#fff}
/* ── Short info ── */
.short-info-card{background:#eff6ff;border-left:4px solid #1d4ed8;padding:12px 14px;font-size:.84rem;color:#1e293b;line-height:1.7;margin-bottom:12px;border-radius:0 8px 8px 0}
/* ── FAQ ── */
.faq-item{border-bottom:1px solid #f1f5f9;font-size:.83rem}
.faq-item:last-child{border-bottom:none}
.faq-q{padding:10px 14px;font-weight:700;color:#1e293b;cursor:pointer;display:flex;justify-content:space-between;align-items:center;user-select:none}
.faq-a{padding:0 14px 10px;color:#475569;line-height:1.65;display:none}
.faq-q.open+.faq-a{display:block}
/* ── Education section content ── */
.edu-para{font-size:.82rem;color:#374151;line-height:1.7;padding:10px 14px;border-bottom:1px solid #f1f5f9}
.edu-para:last-child{border-bottom:none}
.edu-ul,.edu-ol{padding:10px 14px 10px 30px;margin:0}
.edu-ul li,.edu-ol li{font-size:.8rem;color:#374151;padding:4px 0;line-height:1.55}
.edu-mi-item{padding:10px 14px;border-bottom:1px solid #f1f5f9}
.edu-mi-item:last-child{border-bottom:none}
.edu-mi-label{font-size:.72rem;font-weight:700;color:#1a56db;text-transform:uppercase;letter-spacing:.03em;margin-bottom:4px}
.edu-mi-text{font-size:.8rem;color:#374151;line-height:1.6}
"""

# ── Section renderers (same as generate_jobs.py) ─────────────────

def render_card(grad, icon, heading, body_html):
    if not body_html or not body_html.strip(): return ''
    return f'''<div class="job-card">
  <div class="job-card-head" style="background:{grad}">
    <i class="fa-solid {icon}"></i><h2>{e(heading)}</h2>
  </div>
  <div class="job-card-body">{body_html}</div>
</div>'''

def render_table_rows(pairs):
    rows = ''
    for label, val in pairs:
        sv = safe(val)
        if not sv: continue
        rows += f'<tr><th>{e(label)}</th><td>{e(sv)}</td></tr>'
    return rows

def render_important_dates(obj):
    if not obj or not isinstance(obj, dict): return ''
    DATE_FIELDS = [
        ('application_start_date','Application Start'),('application_begin','Application Begin'),
        ('start_date','Start Date'),('date_of_notification','Notification Date'),
        ('notification_date','Notification Date'),('last_date_to_apply','Last Date to Apply'),
        ('last_date','Last Date'),('application_last_date','Application Last Date'),
        ('fee_payment_last_date','Fee Payment Last Date'),('exam_date','Exam Date'),
        ('written_exam_date','Written Exam Date'),('online_exam_date','Online Exam Date'),
        ('interview_date','Interview Date'),('admit_card_date','Admit Card Date'),
        ('admit_card','Admit Card'),('result_date','Result Date'),('event','Event'),
    ]
    seen = set(); rows = ''
    for k, lbl in DATE_FIELDS:
        v = safe(obj.get(k))
        if not v or lbl in seen: continue
        seen.add(lbl)
        is_last = 'last' in k or 'closing' in k
        style = ' style="color:#dc2626;font-weight:700"' if is_last else ''
        rows += f'<tr><th>{e(lbl)}</th><td{style}>{e(v)}</td></tr>'
    for k, v in obj.items():
        sv = safe(v)
        if not sv: continue
        lbl = k.replace('_',' ').replace('  ',' ').title()
        if lbl in seen: continue
        seen.add(lbl)
        rows += f'<tr><th>{e(lbl)}</th><td>{e(sv)}</td></tr>'
    if not rows: return ''
    return render_card('linear-gradient(135deg,#b91c1c,#dc2626)','fa-calendar-check','Important Dates',
                       f'<table class="jd-table"><tbody>{rows}</tbody></table>')

def render_fee(obj):
    if not obj or not isinstance(obj, dict): return ''
    FIELDS = [('General / UR','general'),('General / UR','general_fee'),('OBC','obc'),('OBC','obc_fee'),
              ('SC','sc'),('SC','sc_fee'),('ST','st'),('EWS','ews'),('Female','female'),
              ('PH / Divyang','ph'),('PH / Divyang','pwd'),('Ex-Serviceman','ex_serviceman_fee'),
              ('All Categories','all'),('All Categories','all_category')]
    def is_free(v): return bool(re.search(r'nil|^0$|free|no fee|exempt',v,re.I))
    items = ''; seen = set()
    for lbl, key in FIELDS:
        val = safe(obj.get(key))
        if not val or lbl in seen: continue
        seen.add(lbl)
        cls = 'free' if is_free(val) else 'paid'
        items += f'<div class="fee-item"><div class="fee-label">{e(lbl)}</div><div class="fee-val {cls}">{e(val)}</div></div>'
    note = safe(obj.get('details') or obj.get('fee_mode') or obj.get('payment_mode') or '')
    if not items and not note: return ''
    body = (f'<div class="fee-grid">{items}</div>' if items else '') + \
           (f'<div class="fee-note"><i class="fa-solid fa-circle-info"></i> {e(note)}</div>' if note else '')
    return render_card('linear-gradient(135deg,#c2410c,#ea580c)','fa-indian-rupee-sign','Application Fee',body)

def render_age(obj):
    if not obj or not isinstance(obj, dict): return ''
    pairs = [('Minimum Age',obj.get('minimum_age') or obj.get('min_age')),
             ('Maximum Age',obj.get('maximum_age') or obj.get('max_age') or obj.get('age_limit')),
             ('Age Relaxation',obj.get('age_relaxation') or obj.get('details')),
             ('Age Details',obj.get('age_details'))]
    rows = render_table_rows(pairs)
    if not rows: return ''
    return render_card('linear-gradient(135deg,#0f766e,#0891b2)','fa-user-clock','Age Limit',
                       f'<table class="jd-table"><tbody>{rows}</tbody></table>')

def render_qual(obj):
    if not obj: return ''
    if isinstance(obj, str):
        return render_card('linear-gradient(135deg,#4338ca,#6366f1)','fa-graduation-cap','Qualification / Eligibility',
                           f'<div style="padding:10px 14px;font-size:.83rem">{e(obj)}</div>') if obj.strip() else ''
    if isinstance(obj, dict):
        pairs = [('Education Qualification',obj.get('education_qualification') or obj.get('qualification') or obj.get('eligibility')),
                 ('Required Degree',obj.get('required_degree')),('Experience',obj.get('experience_required')),('Details',obj.get('details'))]
        rows = render_table_rows(pairs)
        return render_card('linear-gradient(135deg,#4338ca,#6366f1)','fa-graduation-cap','Qualification / Eligibility',
                           f'<table class="jd-table"><tbody>{rows}</tbody></table>') if rows else ''
    return ''

def render_vacancy(vac_list):
    if not vac_list or not isinstance(vac_list, list): return ''
    COL_MAP = {
        'post_name':['post_name','post','name','Post Name','Name Of Post'],
        'total':['total','total_vacancies','total_posts','vacancies','Total Posts','Total Vacancies'],
        'ur':['ur','general','UR','General (UR)'],'obc':['obc','OBC'],
        'sc':['sc','SC'],'st':['st','ST'],'ews':['ews','EWS'],
        'women':['women','Women','female'],
        'salary':['salary','pay_scale','Scale of Pay','Salary'],
        'qualification':['eligibility','qualification','Educational Qualification'],
    }
    ORDER = ['post_name','total','ur','obc','sc','st','ews','women','salary','qualification']
    LABELS = {'post_name':'Post Name','total':'Total Posts','ur':'UR/General','obc':'OBC',
               'sc':'SC','st':'ST','ews':'EWS','women':'Women','salary':'Salary','qualification':'Qualification'}
    norm = []; avail = set()
    for row in vac_list:
        if not isinstance(row, dict): continue
        n = {}
        for col, aliases in COL_MAP.items():
            for a in aliases:
                if a in row and row[a] not in (None,'',{},[]):
                    n[col] = safe(row[a]); avail.add(col); break
        if n: norm.append(n)
    if not norm: return ''
    cols = [c for c in ORDER if c in avail]
    if not cols: return ''
    head = '<th>Sr.</th>' + ''.join(f'<th>{LABELS[c]}</th>' for c in cols)
    rows = ''; totals = {}
    for i, row in enumerate(norm, 1):
        cells = f'<td>{i}</td>' + ''.join(f'<td>{e(row.get(c,""))}</td>' for c in cols)
        rows += f'<tr>{cells}</tr>'
        for c in ['total','ur','obc','sc','st','ews','women']:
            if c in cols:
                try: totals[c] = totals.get(c,0) + int(re.sub(r'\D','',row.get(c,'0') or '0') or '0')
                except: pass
    if totals:
        tc = '<td><strong>Total</strong></td>' + ''.join(
            f'<td>{"<strong>"+str(totals[c])+"</strong>" if c in totals else ""}</td>' for c in cols)
        rows += f'<tr class="vac-tot">{tc}</tr>'
    body = f'<div class="tbl-scroll"><table class="vac-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    return render_card('linear-gradient(135deg,#15803d,#16a34a)','fa-chart-pie','Vacancy Details',body)

def render_category_vacancy(cwv):
    if not cwv: return ''
    if isinstance(cwv, list): return render_vacancy(cwv)
    if isinstance(cwv, dict) and cwv:
        pairs = [(k.replace('_',' ').title(), v) for k,v in cwv.items() if safe(v)]
        if not pairs: return ''
        rows = ''.join(f'<tr><td>{e(l)}</td><td>{e(safe(v))}</td></tr>' for l,v in pairs)
        body = f'<div class="tbl-scroll"><table class="vac-table"><thead><tr><th>Category</th><th>Posts</th></tr></thead><tbody>{rows}</tbody></table></div>'
        return render_card('linear-gradient(135deg,#15803d,#16a34a)','fa-chart-bar','Category-wise Vacancy',body)
    return ''

def render_salary(obj):
    if not obj: return ''
    if isinstance(obj, str):
        return render_card('linear-gradient(135deg,#15803d,#16a34a)','fa-indian-rupee-sign','Salary & Pay Scale',
                           f'<div style="padding:10px 14px;font-size:.83rem">{e(obj)}</div>') if obj.strip() else ''
    if isinstance(obj, dict):
        pairs = [('Pay Scale',obj.get('pay_scale')),('Basic Pay',obj.get('basic_pay')),
                 ('Grade Pay',obj.get('grade_pay')),('Salary',obj.get('salary')),('Details',obj.get('details'))]
        rows = render_table_rows(pairs)
        return render_card('linear-gradient(135deg,#15803d,#16a34a)','fa-indian-rupee-sign','Salary & Pay Scale',
                           f'<table class="jd-table"><tbody>{rows}</tbody></table>') if rows else ''
    return ''

def render_selection(sp):
    if not sp: return ''
    steps = [safe(s) for s in sp if safe(s)] if isinstance(sp, list) \
            else [s.strip() for s in re.split(r'[,\n;/]', str(sp)) if s.strip()]
    if not steps: return ''
    items = ''.join(f'<div class="sel-step"><span class="sel-num">{i+1}</span>{e(s[:80])}</div>' for i,s in enumerate(steps))
    return render_card('linear-gradient(135deg,#5b21b6,#7c3aed)','fa-list-check','Selection Process',
                       f'<div class="sel-steps">{items}</div>')

def render_exam_pattern(ep):
    if not ep: return ''
    if isinstance(ep, list) and ep and isinstance(ep[0], dict):
        cols = list(ep[0].keys())
        head = '<th>Sr.</th>' + ''.join(f'<th>{e(c.replace("_"," ").title())}</th>' for c in cols)
        rows = ''.join(f'<tr><td>{i+1}</td>' + ''.join(f'<td>{e(safe(r.get(c)))}</td>' for c in cols) + '</tr>'
                       for i,r in enumerate(ep))
        body = f'<div class="tbl-scroll"><table class="vac-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
        return render_card('linear-gradient(135deg,#0369a1,#0284c7)','fa-file-lines','Exam Pattern',body)
    if isinstance(ep, dict) and ep:
        rows = render_table_rows([(k.replace('_',' ').title(), v) for k,v in ep.items()])
        return render_card('linear-gradient(135deg,#0369a1,#0284c7)','fa-file-lines','Exam Pattern',
                           f'<table class="jd-table"><tbody>{rows}</tbody></table>') if rows else ''
    if isinstance(ep, str) and ep.strip():
        return render_card('linear-gradient(135deg,#0369a1,#0284c7)','fa-file-lines','Exam Pattern',
                           f'<div style="padding:10px 14px;font-size:.83rem">{e(ep)}</div>')
    return ''

def render_syllabus(syl):
    if not syl: return ''
    if isinstance(syl, list) and syl:
        items = ''.join(f'<div class="sel-step"><i class="fa-solid fa-book-open" style="font-size:.7rem"></i>{e(safe(s)[:100])}</div>' for s in syl if safe(s))
        return render_card('linear-gradient(135deg,#4338ca,#6366f1)','fa-book','Syllabus',
                           f'<div class="sel-steps">{items}</div>') if items else ''
    if isinstance(syl, str) and syl.strip():
        return render_card('linear-gradient(135deg,#4338ca,#6366f1)','fa-book','Syllabus',
                           f'<div style="padding:10px 14px;font-size:.83rem">{e(syl)}</div>')
    return ''

def render_physical(pe):
    if not pe or not isinstance(pe, dict): return ''
    pairs = [(k.replace('_',' ').title(), v) for k,v in pe.items() if safe(v)]
    rows = render_table_rows(pairs)
    return render_card('linear-gradient(135deg,#be123c,#e11d48)','fa-dumbbell','Physical Eligibility',
                       f'<table class="jd-table"><tbody>{rows}</tbody></table>') if rows else ''

def render_hta(steps):
    if not isinstance(steps, list) or not steps: return ''
    filtered = [safe(s) for s in steps if safe(s)]
    if not filtered: return ''
    items = ''.join(f'<li class="hta-item"><span class="hta-num">{i+1}</span><span>{e(s)}</span></li>' for i,s in enumerate(filtered))
    return render_card('linear-gradient(135deg,#0f766e,#0891b2)','fa-clipboard-list','How to Apply',
                       f'<ul class="hta-list">{items}</ul>')

def render_instructions(insts):
    if not isinstance(insts, list) or not insts: return ''
    filtered = [safe(s) for s in insts if safe(s)]
    if not filtered: return ''
    items = ''.join(f'<li class="inst-item"><i class="fa-solid fa-triangle-exclamation"></i><span>{e(s)}</span></li>' for s in filtered)
    return render_card('linear-gradient(135deg,#b45309,#ca8a04)','fa-circle-exclamation','Important Instructions',
                       f'<ul class="inst-list">{items}</ul>')

LINK_CFG = {
    'apply_online':('Apply Online','btn-blue','fa-paper-plane'),
    'official_website':('Official Website','btn-green','fa-globe'),
    'notification_pdf':('Download Notification','btn-red','fa-file-pdf'),
    'download_notification':('Download Notification','btn-red','fa-file-pdf'),
    'official_notification':('Official Notification','btn-red','fa-file-pdf'),
    'registration_link':('Register Now','btn-orange','fa-user-plus'),
    'login_link':('Login','btn-purple','fa-right-to-bracket'),
    'admit_card':('Admit Card','btn-teal','fa-id-card'),
    'answer_key':('Answer Key','btn-indigo','fa-key'),
    'syllabus_pdf':('Syllabus PDF','btn-gray','fa-book'),
    'result_link':('Result','btn-green','fa-trophy'),
    'click_here':('Click Here','btn-blue','fa-link'),
    'merit_list':('Merit List','btn-teal','fa-list'),
}

def render_links(il_obj):
    if not il_obj or not isinstance(il_obj, dict): return ''
    buttons = ''; seen = set()
    for key, val in il_obj.items():
        if key in ('structured_links','seo_tags'): continue
        urls = val if isinstance(val, list) else [val]
        label, css, icon = LINK_CFG.get(key, ('View','btn-gray','fa-link'))
        for url in urls:
            u = str(url or '').strip()
            if not u.startswith('http') or is_blocked(u) or u in seen: continue
            seen.add(u)
            ic = 'fa-file-pdf' if u.lower().endswith('.pdf') else icon
            cl = 'btn-red' if u.lower().endswith('.pdf') else css
            buttons += f'<a href="{e(u)}" class="link-btn {cl}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ic}"></i> {e(label)}</a>\n'
    for item in (il_obj.get('structured_links') or []):
        if not isinstance(item, dict): continue
        u = str(item.get('url','') or item.get('href','')).strip()
        lbl = str(item.get('label','') or item.get('title','View')).strip() or 'View'
        if not u.startswith('http') or is_blocked(u) or u in seen: continue
        seen.add(u)
        ll = lbl.lower()
        ic,cl = ('fa-paper-plane','btn-blue') if 'apply' in ll else \
                ('fa-trophy','btn-green') if 'result' in ll else \
                ('fa-id-card','btn-teal') if 'admit' in ll else \
                ('fa-file-pdf','btn-red') if u.endswith('.pdf') else \
                ('fa-globe','btn-green') if 'official' in ll else \
                ('fa-link','btn-blue')
        buttons += f'<a href="{e(u)}" class="link-btn {cl}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ic}"></i> {e(lbl[:50])}</a>\n'
    if not buttons: return ''
    return render_card('linear-gradient(135deg,#1e40af,#1e3a8a)','fa-link','Important Links',
                       f'<div class="links-grid">{buttons}</div>')

def render_faq(faq_list):
    if not isinstance(faq_list, list) or not faq_list: return ''
    items = ''
    for f in faq_list:
        if not isinstance(f, dict): continue
        q = safe(f.get('question','')); a = safe(f.get('answer',''))
        if not q or not a: continue
        items += f'''<div class="faq-item">
  <div class="faq-q" onclick="this.classList.toggle('open');this.nextElementSibling.style.display=this.classList.contains('open')?'block':'none'">
    {e(q)} <i class="fa-solid fa-chevron-down" style="font-size:.7rem;color:#94a3b8"></i>
  </div>
  <div class="faq-a">{e(a)}</div>
</div>'''
    return render_card('linear-gradient(135deg,#4338ca,#6366f1)','fa-circle-question','FAQs', items) if items else ''

def render_edu_sections(sections_list):
    """Render raw education scraper sections (paragraph/table/list/merged_info format)"""
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
                if text: body += f'<div class="edu-para">{e(text)}</div>'
            elif btype == 'table':
                rows = block.get('rows', [])
                if not rows: continue
                headers = block.get('headers', [])
                data_rows = rows
                if not headers and rows and rows[0]:
                    headers = rows[0]; data_rows = rows[1:]
                if headers and (len(headers) == 2 or (data_rows and len(data_rows[0]) == 2)):
                    body += f'<div class="tbl-scroll"><table class="jd-table"><tbody>'
                    for row in data_rows:
                        if len(row) >= 2:
                            body += f'<tr><th>{e(row[0])}</th><td>{e(row[1])}</td></tr>'
                    body += '</tbody></table></div>'
                else:
                    head = ''.join(f'<th>{e(h)}</th>' for h in headers)
                    rows_html = ''.join(f'<tr>' + ''.join(f'<td>{e(c)}</td>' for c in r) + '</tr>' for r in data_rows)
                    body += f'<div class="tbl-scroll"><table class="vac-table"><thead><tr>{head}</tr></thead><tbody>{rows_html}</tbody></table></div>'
            elif btype == 'list':
                items_list = block.get('items', [])
                tag = 'ol' if block.get('style') == 'ordered' else 'ul'
                body += f'<{tag} class="edu-{"ol" if tag=="ol" else "ul"}">' + \
                        ''.join(f'<li>{e(li)}</li>' for li in items_list) + f'</{tag}>'
            elif btype == 'merged_info':
                for mi in block.get('items',[]):
                    lbl = safe(mi.get('label','')); txt = safe(mi.get('text',''))
                    if not lbl and not txt: continue
                    body += f'<div class="edu-mi-item">'
                    if lbl: body += f'<div class="edu-mi-label">{e(lbl)}</div>'
                    if txt: body += f'<div class="edu-mi-text">{e(txt)}</div>'
                    body += '</div>'
        if not body.strip(): continue
        if heading:
            html += f'<div class="job-card"><div class="job-card-head" style="background:#475569"><i class="fa-solid fa-circle-dot"></i><h2>{e(heading)}</h2></div><div class="job-card-body">{body}</div></div>'
        else:
            html += f'<div class="job-card"><div class="job-card-body">{body}</div></div>'
    return html

# ── Build full 16-section HTML ──────────────────────────────────────

def build_page_html(title, detail, canon_url, breadcrumbs, page_type='job', source_type_label=''):
    """
    detail = full job object with all keys
    breadcrumbs = list of (label, url) tuples
    """
    bd    = detail.get('basic_details', {}) or {}
    dates = detail.get('important_dates', {}) or {}
    fee   = detail.get('application_fee', {}) or {}
    age   = detail.get('age_limit', {}) or {}
    qual  = detail.get('qualification') or {}
    vac   = detail.get('vacancy_details') or []
    cwv   = detail.get('category_wise_vacancy') or {}
    sal   = detail.get('salary_details') or {}
    sel   = detail.get('selection_process') or []
    ep    = detail.get('exam_pattern')
    syl   = detail.get('syllabus')
    pe    = detail.get('physical_eligibility') or {}
    hta   = detail.get('how_to_apply') or []
    insts = detail.get('important_instructions') or []
    il    = detail.get('important_links') or {}
    faq   = detail.get('faq') or []
    edu_sections = detail.get('sections') or []  # education raw sections

    org        = safe(bd.get('organization_name') or bd.get('post_name') or bd.get('board') or '')
    vacancies  = safe(bd.get('total_vacancies') or bd.get('total_post') or detail.get('total_post') or '')
    last_date  = safe(dates.get('last_date_to_apply') or dates.get('last_date') or detail.get('lastDate') or detail.get('last_date') or '')
    apply_mode = safe(bd.get('application_mode') or detail.get('apply_mode') or 'Online')
    location   = safe(bd.get('job_location') or detail.get('state') or 'India')
    short_info = safe(bd.get('short_information') or detail.get('short_info') or detail.get('short_information') or '')
    source_url = safe(detail.get('source_url') or detail.get('url') or '')

    # Meta
    meta_desc = f"{title}: {vacancies+' vacancies, ' if vacancies else ''}{('last date '+last_date+'. ') if last_date else ''}Apply online – Top Sarkari Jobs."
    if len(meta_desc) > 155: meta_desc = meta_desc[:152].rsplit(' ',1)[0].rstrip('.,–') + '…'

    posted_date = normalise_date(safe(bd.get('last_updated') or dates.get('date_of_notification') or '')) or TODAY

    # Schema
    job_schema = {
        '@context':'https://schema.org','@type':'JobPosting',
        'title':title,'description':short_info or meta_desc,
        'datePosted':posted_date,'url':canon_url,
        'hiringOrganization':{'@type':'Organization','name':org or 'Government of India'},
        'jobLocation':{'@type':'Place','address':{'@type':'PostalAddress','addressCountry':'IN','addressLocality':location}},
    }
    if last_date:
        iso = normalise_date(last_date)
        if iso: job_schema['validThrough'] = iso

    bc_items = [{'@type':'ListItem','position':1,'name':'Home','item':f'{BASE_URL}/'}]
    for i,(lbl,url) in enumerate(breadcrumbs, 2):
        bc_items.append({'@type':'ListItem','position':i,'name':lbl,'item':url})
    bc_items.append({'@type':'ListItem','position':len(bc_items)+1,'name':title,'item':canon_url})
    bc_schema = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':bc_items}

    # Breadcrumb HTML
    bc_html = '<nav class="bc" aria-label="Breadcrumb"><a href="/">Home</a>'
    for lbl, url in breadcrumbs:
        bc_html += f'<i class="fa-solid fa-chevron-right"></i><a href="{e(url)}">{e(lbl)}</a>'
    bc_html += f'<i class="fa-solid fa-chevron-right"></i><span>{e(title[:60])}{"…" if len(title)>60 else ""}</span></nav>'

    # Header card
    BD_FIELDS = [('Organization',bd.get('organization_name')),('Post Name',bd.get('post_name')),
                 ('Total Vacancies',bd.get('total_vacancies') or vacancies),
                 ('Application Mode',bd.get('application_mode') or apply_mode),
                 ('Job Location',bd.get('job_location') or location),
                 ('Job Type',bd.get('job_type')),('Notification No.',bd.get('notification_number')),
                 ('Advertisement No.',bd.get('advt_no')),('Last Updated',bd.get('last_updated'))]
    hdr_rows = ''.join(f'<tr><th>{e(l)}</th><td>{e(safe(v))}</td></tr>' for l,v in BD_FIELDS if safe(v))
    if source_url and not is_blocked(source_url):
        hdr_rows += f'<tr><th>Official Website</th><td><a href="{e(source_url)}" target="_blank" rel="noopener noreferrer">{e(source_url[:80])}</a></td></tr>'

    badge2_color = '#dcfce7' if page_type=='job' else '#fef9c3' if page_type=='education' else '#f3e8ff'
    badge2_text  = '#166534' if page_type=='job' else '#713f12' if page_type=='education' else '#581c87'
    badge_label  = source_type_label or ('Govt Job' if page_type=='job' else 'Education' if page_type=='education' else 'State Job')

    header_html = f'''<div class="jd-header">
  <div class="jd-badge-row">
    <span class="jd-badge"><i class="fa-solid fa-briefcase"></i> {e(badge_label)}</span>
    <span class="jd-badge" style="background:{badge2_color};color:{badge2_text}"><i class="fa-solid fa-map-pin"></i> {e(location[:30])}</span>
  </div>
  <h1 class="jd-title">{e(title)}</h1>
  {f'<table class="jd-table" style="margin-bottom:0"><tbody>{hdr_rows}</tbody></table>' if hdr_rows else ''}
  <div class="jd-stats">
    <div class="jd-stat"><div class="jd-stat-val">{e(vacancies or "—")}</div><div class="jd-stat-lbl">Vacancies</div></div>
    <div class="jd-stat"><div class="jd-stat-val" style="color:#dc2626">{e(last_date or "—")}</div><div class="jd-stat-lbl">Last Date</div></div>
    <div class="jd-stat"><div class="jd-stat-val">{e(apply_mode or "—")}</div><div class="jd-stat-lbl">Apply Mode</div></div>
    <div class="jd-stat"><div class="jd-stat-val">{e((location[:18] if location else "India"))}</div><div class="jd-stat-lbl">Location</div></div>
  </div>
</div>'''

    # Build sections
    sections = ''
    if short_info:
        sections += f'<div class="short-info-card"><i class="fa-solid fa-circle-info" style="color:#1d4ed8;margin-right:6px"></i>{e(short_info)}</div>'

    sections += render_important_dates(dates)
    sections += render_fee(fee)
    sections += render_age(age)
    sections += render_qual(qual)
    sections += render_vacancy(vac)
    sections += render_category_vacancy(cwv)
    sections += render_salary(sal)
    sections += render_selection(sel)
    sections += render_exam_pattern(ep)
    sections += render_syllabus(syl)
    sections += render_physical(pe)
    sections += render_hta(hta)
    sections += render_instructions(insts)
    # Education raw scraper sections
    sections += render_edu_sections(edu_sections)
    sections += render_links(il)
    sections += render_faq(faq)

    if not sections.strip():
        if source_url and not is_blocked(source_url):
            sections = render_card('linear-gradient(135deg,#1e40af,#1e3a8a)','fa-link','Important Links',
                f'<div class="links-grid"><a href="{e(source_url)}" class="link-btn btn-green" target="_blank" rel="noopener noreferrer"><i class="fa-solid fa-globe"></i> Official Website</a></div>')
        else:
            sections = '<div class="job-card"><div class="job-card-body" style="padding:20px;text-align:center;color:#94a3b8"><i class="fa-solid fa-clock" style="font-size:1.5rem;display:block;margin-bottom:8px"></i>Details coming soon. Check official website.</div></div>'

    faq_schema_tag = ''
    valid_faqs = [f for f in faq if isinstance(f,dict) and f.get('question') and f.get('answer')][:5]
    if valid_faqs:
        faq_schema = {'@context':'https://schema.org','@type':'FAQPage',
            'mainEntity':[{'@type':'Question','name':f['question'],'acceptedAnswer':{'@type':'Answer','text':f['answer']}} for f in valid_faqs]}
        faq_schema_tag = f'<script type="application/ld+json">{json.dumps(faq_schema,ensure_ascii=False)}</script>'

    title_tag = title if len(title)+19 <= 60 else title[:40].rstrip()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{e(title_tag)} | Top Sarkari Jobs</title>
  <meta name="description" content="{e(meta_desc)}"/>
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large"/>
  <link rel="canonical" href="{e(canon_url)}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:site_name" content="Top Sarkari Jobs"/>
  <meta property="og:title" content="{e(title_tag)} | Top Sarkari Jobs"/>
  <meta property="og:description" content="{e(meta_desc)}"/>
  <meta property="og:url" content="{e(canon_url)}"/>
  <meta property="og:image" content="{BASE_URL}/image.png"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{e(title_tag)} | Top Sarkari Jobs"/>
  <meta name="twitter:description" content="{e(meta_desc)}"/>
  <script type="application/ld+json">{json.dumps(job_schema,ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(bc_schema,ensure_ascii=False)}</script>
  {faq_schema_tag}
  <script>
    window.__TSJ_STATIC_PAGE = true;
    window.__TSJ_PSR_DISABLED = true;
    window.__TSJ_RENDERER_DISABLED = true;
  </script>
  <link rel="icon" type="image/x-icon" href="/image.ico"/>
  <link rel="stylesheet" href="/styles.css"/>
  <link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/>
  <noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>
  <link rel="manifest" href="/manifest.json"/>
  <meta name="theme-color" content="#0d2257"/>
  <script src="/analytics.js" defer></script>
  <style>{COMMON_CSS}</style>
</head>
<body>
  <div id="headerPlaceholder"></div>
  <script>fetch('/header.html',{{cache:'no-store'}}).then(r=>r.ok?r.text():null).catch(()=>null).then(h=>{{if(h){{var d=document.getElementById('headerPlaceholder');if(d)d.outerHTML=h;}}}})</script>
  <main>
    <div class="pg-wrap">
      {bc_html}
      <div class="notice-bar">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span><strong>Important:</strong> Always verify details on the official website before applying. Dates &amp; eligibility may change.</span>
      </div>
      {header_html}
      {sections}
    </div>
  </main>
  <div id="footerPlaceholder"></div>
  <script>fetch('/footer.html',{{cache:'no-store'}}).then(r=>r.ok?r.text():null).catch(()=>null).then(h=>{{if(h){{var d=document.getElementById('footerPlaceholder');if(d)d.outerHTML=h;}}}})</script>
  <script src="/tsj-menu.js" defer></script>
</body>
</html>"""

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

print(f"Loading {SRC}...")
with open(SRC, encoding='utf-8') as f:
    data = json.load(f)

state_count = edu_count = cat_count = 0

# ── 1. STATE JOBS ──────────────────────────────────────────────────
print("\nGenerating state job pages...")
sj = data.get('state_jobs', {})
for sec in sj.get('sections', []):
    state_name = safe(sec.get('state') or sec.get('title') or '')
    state_slug = slugify(state_name)
    state_dir  = os.path.join('state', state_slug)

    for item in sec.get('items', []):
        name = safe(item.get('name') or item.get('title') or '')
        if not name: continue

        # Derive slug from URL or name
        item_url = safe(item.get('url',''))
        # Only use URL slug if it looks like a clean page slug
        raw_slug = ''
        if item_url:
            parts = item_url.rstrip('/').split('/')
            candidate = parts[-1] if parts else ''
            # Valid slug: only hyphens/alphanumeric, no dots/query/encoding, reasonable length
            if (candidate and 
                re.match(r'^[a-z0-9][a-z0-9-]{2,80}$', candidate.lower()) and
                '.' not in candidate and '?' not in candidate and
                '%' not in candidate and '=' not in candidate and
                len(candidate) <= 80):
                raw_slug = candidate
        item_slug = slugify(name)[:80]  # always use name-based slug, capped at 80 chars
        if raw_slug and len(raw_slug) <= 80:
            item_slug = raw_slug
        if not item_slug: continue

        detail = item.get('detail') or {}
        if isinstance(detail, str):
            try: detail = json.loads(detail)
            except: detail = {}

        # Enrich detail with item-level data
        if not detail.get('basic_details'):
            detail['basic_details'] = {}
        bd = detail['basic_details']
        if not bd.get('job_title'): bd['job_title'] = name
        if not bd.get('job_location'): bd['job_location'] = f"{state_name}, India"
        if not detail.get('important_dates'):
            detail['important_dates'] = {}
        if item.get('lastDate') and not detail['important_dates'].get('last_date_to_apply'):
            detail['important_dates']['last_date_to_apply'] = item['lastDate']
        detail['source_url'] = item_url

        canon_url = f"{BASE_URL}/state/{state_slug}/{item_slug}/"
        breadcrumbs = [('State Jobs',f'{BASE_URL}/state/'), (f'{state_name} Jobs',f'{BASE_URL}/state/{state_slug}/')]

        out_dir = os.path.join(state_dir, item_slug)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f2:
            f2.write(build_page_html(name, detail, canon_url, breadcrumbs, 'state', f'{state_name} Govt Job'))
        state_count += 1

print(f"  State pages: {state_count}")

# ── 2. EDUCATION PAGES ─────────────────────────────────────────────
print("\nGenerating education pages...")
ej = data.get('education_jobs', {})
for sec in ej.get('sections', []):
    sec_id    = safe(sec.get('id') or sec.get('title') or '')
    sec_title = safe(sec.get('title') or sec_id)
    sec_slug  = sec_id  # use id as-is (already slugified in JSON)
    sec_dir   = os.path.join('education', sec_slug)

    for item in sec.get('items', []):
        name = safe(item.get('name') or item.get('examName') or '')
        if not name: continue
        item_slug = slugify(name)[:80]
        if not item_slug: continue

        detail = item.get('detail') or {}
        # Build a proper detail dict from education item
        full_detail = {
            'basic_details': {
                'job_title': detail.get('title') or name,
                'organization_name': safe(sec_title),
                'job_location': safe(sec_title),
                'short_information': detail.get('short_info',''),
                'last_updated': safe(item.get('postDate') or item.get('date') or ''),
            },
            'important_dates': {},
            'important_links': detail.get('important_links') or {},
            'sections': detail.get('sections') or [],
            'faq': detail.get('faq') or [],
            'source_url': safe(item.get('url',''))
        }
        if item.get('date') or item.get('postDate'):
            full_detail['important_dates']['notification_date'] = safe(item.get('date') or item.get('postDate'))

        canon_url = f"{BASE_URL}/education/{sec_slug}/{item_slug}/"
        breadcrumbs = [('Education',f'{BASE_URL}/education/'), (sec_title,f'{BASE_URL}/education/{sec_slug}/')]

        out_dir = os.path.join(sec_dir, item_slug)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f2:
            f2.write(build_page_html(name, full_detail, canon_url, breadcrumbs, 'education', sec_title))
        edu_count += 1

print(f"  Education pages: {edu_count}")

# ── 3. CATEGORY/STUDY PAGES ────────────────────────────────────────
print("\nGenerating category/study pages...")
fja = data.get('freejobalert_categories', {})

QUAL_SLUG_MAP = {
    '10TH_Pass':'10th-pass','8TH_Pass':'8th-pass','12TH_Pass':'12th-pass',
    '4th_Pass':'4th-pass','5th_Pass':'5th-pass','6th_Pass':'6th-pass',
    '7th_Pass':'7th-pass','9th_Pass':'9th-pass',
    'Diploma':'diploma','ITI':'iti','B_Tech_BE':'b-tech-be','B_Com':'b-com',
    'Any_Graduate':'any-graduate','Any_Post_Graduate':'any-post-graduate',
    'Railway_Jobs':'railway-jobs','Police_Defence':'police-defence',
    'Teaching_Faculty':'teaching-faculty','Bank_Jobs':'bank-jobs',
    'Medical_Hospital':'medical-hospital','Latest_Notifications':'latest-jobs',
    'Last_Date_Reminder':'last-date-reminder','Intermediate':'intermediate',
    'GNM':'gnm','ANM':'anm','D_Pharm':'d-pharm','DMLT':'dmlt',
    'D_El_Ed':'d-el-ed','D_P_Ed':'d-p-ed','B_Sc':'b-sc','BCA':'bca',
    'MA':'ma','BBA':'bba','LLB':'llb','B_Ed':'b-ed','MBBS':'mbbs',
    'B_Pharma':'b-pharma','BAMS':'bams','BDS':'bds','M_Sc':'m-sc',
    'M_Com':'m-com','M_Ed':'m-ed','M_A':'m-a','M_E_MTech':'me-mtech',
    'MCA':'mca','MBA_PGDM':'mba-pgdm','MS_MD':'ms-md','M_Pharma':'m-pharma',
    'CA':'ca','CS':'cs','ICWA':'icwa','MPhil_PhD':'mphil-phd',
    'VHSE':'vhse','DLT':'dlt',
}
QUAL_LABEL_MAP = {
    '10TH_Pass':'10th Pass','8TH_Pass':'8th Pass','12TH_Pass':'12th Pass',
    '4th_Pass':'4th Pass','5th_Pass':'5th Pass','6th_Pass':'6th Pass',
    '7th_Pass':'7th Pass','9th_Pass':'9th Pass',
    'Diploma':'Diploma','ITI':'ITI','B_Tech_BE':'B.Tech / BE','B_Com':'B.Com',
    'Any_Graduate':'Any Graduate','Any_Post_Graduate':'Any PG',
    'Railway_Jobs':'Railway Jobs','Police_Defence':'Police / Defence',
    'Teaching_Faculty':'Teaching / Faculty','Bank_Jobs':'Bank Jobs',
    'Medical_Hospital':'Medical / Hospital','Latest_Notifications':'Latest Jobs',
    'Last_Date_Reminder':'Last Date Reminder','Intermediate':'Intermediate',
    'GNM':'GNM','ANM':'ANM','D_Pharm':'D.Pharm','DMLT':'DMLT',
    'D_El_Ed':'D.El.Ed','D_P_Ed':'D.P.Ed','B_Sc':'B.Sc','BCA':'BCA',
    'MA':'MA','BBA':'BBA','LLB':'LLB','B_Ed':'B.Ed','MBBS':'MBBS',
    'B_Pharma':'B.Pharma','BAMS':'BAMS','BDS':'BDS','M_Sc':'M.Sc',
    'M_Com':'M.Com','M_Ed':'M.Ed','M_A':'M.A','M_E_MTech':'M.E / M.Tech',
    'MCA':'MCA','MBA_PGDM':'MBA / PGDM','MS_MD':'MS / MD','M_Pharma':'M.Pharma',
    'CA':'CA','CS':'CS','ICWA':'ICWA','MPhil_PhD':'M.Phil / Ph.D',
    'VHSE':'VHSE','DLT':'DLT',
}

for cat, jobs in fja.items():
    if not isinstance(jobs, list): continue
    cat_slug  = QUAL_SLUG_MAP.get(cat, slugify(cat))
    cat_label = QUAL_LABEL_MAP.get(cat, cat.replace('_',' '))
    cat_dir   = os.path.join('category','study', cat_slug)

    for job in jobs:
        bd    = job.get('basic_details', {}) or {}
        title = safe(bd.get('job_title',''))
        if not title: continue
        item_slug = slugify(title)[:80]
        if not item_slug: continue

        canon_url = f"{BASE_URL}/category/study/{cat_slug}/{item_slug}/"
        breadcrumbs = [('Study Wise Jobs',f'{BASE_URL}/category/study/'),
                       (f'{cat_label} Jobs',f'{BASE_URL}/category/study/{cat_slug}/')]

        out_dir = os.path.join(cat_dir, item_slug)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f2:
            f2.write(build_page_html(title, job, canon_url, breadcrumbs, 'job', f'{cat_label} Jobs'))
        cat_count += 1

print(f"  Category/study pages: {cat_count}")

print(f"\n✅ ALL DONE!")
print(f"  State pages    : {state_count}")
print(f"  Education pages: {edu_count}")
print(f"  Category pages : {cat_count}")
print(f"  TOTAL          : {state_count + edu_count + cat_count}")
