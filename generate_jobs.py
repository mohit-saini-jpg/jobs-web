"""
generate_jobs.py — Complete_Jobs_Full_Data.json se job pages generate karta hai
=================================================================================
Source: Complete_Jobs_Full_Data.json  (master data, freejobalert_categories + state_jobs + education_jobs)

Output per job:
  - jobs/data/<slug>.json          — job data file
  - jobs/<slug>/index.html         — COMPLETE static HTML (no JS redirect, fully pre-rendered)
  - jobs-index.json                — fast lookup index
"""

import json, re, os, html as html_mod
from datetime import date

SRC      = "Complete_Jobs_Full_Data.json"
DEST     = "jobs/data"
JOBS_DIR = "jobs"
INDEX    = "jobs-index.json"
BASE_URL = "https://www.topsarkarijobs.com"
TODAY    = date.today().isoformat()

BLOCKED_DOMAINS = {"sarkariresult.com","freejobalert.com","sarkariresultshine.com","sarkarinetwork.com"}

VALID_CATS = {
    "10TH_Pass","8TH_Pass","12TH_Pass","Diploma","ITI","B_Tech_BE","B_Com",
    "Any_Graduate","Any_Post_Graduate","Railway_Jobs","Police_Defence",
    "Teaching_Faculty","Bank_Jobs","Medical_Hospital","Latest_Notifications",
}

CAT_LABELS = {
    "10TH_Pass":"10th Pass Jobs","8TH_Pass":"8th Pass Jobs","12TH_Pass":"12th Pass Jobs",
    "Diploma":"Diploma Jobs","ITI":"ITI Jobs","B_Tech_BE":"B.Tech / BE Jobs",
    "B_Com":"B.Com Jobs","Any_Graduate":"Graduation Jobs","Any_Post_Graduate":"Post Graduation Jobs",
    "Railway_Jobs":"Railway Jobs","Police_Defence":"Defence Jobs","Teaching_Faculty":"Teaching Jobs",
    "Bank_Jobs":"Bank Jobs","Medical_Hospital":"Medical Jobs","Latest_Notifications":"Latest Jobs",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def slugify(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text[:60].strip('-') or 'job'  # ISSUE-003 FIX: Hard 60-char slug limit (was 80)

# ── ISSUE-004 FIX: Junk/non-job URL filter ──────────────────────────────────
import re as _re
_JUNK_PATTERNS = [
    r'\baadhaar\b', r'\baadhar\b', r'\babha\b', r'\bayushman\b',
    r'\bpm yojana\b', r'\bpension yojana\b', r'\bration card\b',
    r'\be-?shram\b', r'\bpm kisan\b', r'\bkisan credit\b',
    r'\bloan apply\b', r'\bscholarship apply\b', r'\bpregnancy\b',
    r'\bhealth checkup\b', r'\bbijli\b', r'\bpaani bill\b', r'\bpani bill\b',
    r'^\d{3,6}[\s-]*form$', r'^\d{3,6}[\s-]*pension',
]
_RECRUITMENT_KW = [
    'recruitment', 'vacancy', 'vacancies', 'apply online', 'notification',
    'admit card', 'result', 'answer key', 'syllabus', 'bharti',
    'selection', 'posts', 'sarkari', 'naukri', 'job', 'jobs',
    # extended — covers exam/test/form/admission/officer/instructor/helper entries
    'online form', 'exam', 'test', 'admission', 'officer', 'instructor',
    'technician', 'assistant', 'havaldar', 'helper', 'mts', 'constable',
    'conductor', 'apprentice', 'trainee', 'counselling', 'merit list',
    'exam city', 'certificate', 'eligibility test', 're-open',
    'teacher', 'pgt', 'tgt', 'jbt', 'ntt', 'paramedical', 'nursing',
]

def is_real_job(title):
    """Return False if title matches yojana/scheme/non-recruitment patterns."""
    t = str(title or '').lower().strip()
    if not t: return False
    for pat in _JUNK_PATTERNS:
        if _re.search(pat, t):
            return False
    return any(kw in t for kw in _RECRUITMENT_KW)

# ── ISSUE-006 FIX: Optimized title + meta description formula ───────────────
def build_seo_title(title, org, vacancies, year='2026'):
    """Build SEO title ≤ 60 chars following: [Job Title] [Year] – Apply Online | [Org]"""
    # Strip site branding noise
    clean = re.sub(r'\s*[-–|]\s*(FreeJobAlert|SarkariResult|Sarkari Result|Top Sarkari Jobs).*$', '', title, flags=re.I).strip()
    if len(clean) <= 40:
        candidate = f"{clean} {year} – Apply Online"
        if len(candidate) + len(f" | {org[:15]}") <= 60:
            return f"{candidate} | {org[:15]}"
        return candidate[:60]
    elif len(clean) <= 50:
        return f"{clean} {year} – Apply Online"[:60]
    else:
        return f"{clean[:50].rstrip()}… {year}"[:60]

def build_seo_meta_desc(title, org, vacancies, last_date, qual=''):
    """Build meta description ≤ 155 chars targeting search intent keywords."""
    vac_p  = f"{vacancies} vacancies. " if vacancies else ''
    ld_p   = f"Last date: {last_date}. " if last_date else ''
    qual_p = f"Eligibility: {qual[:60]}. " if qual else ''
    desc = f"{org} released {title}. {vac_p}{ld_p}{qual_p}Check eligibility, apply online & notification."
    return desc[:155]

# ── ISSUE-009 FIX: FAQ auto-generation when no faq data exists ──────────────
def build_auto_faq(title, org, last_date, vacancies, qual, fee):
    """Generate 4 high-value FAQ entries for job pages when no native FAQ data."""
    faqs = []
    if last_date:
        faqs.append({
            '@type': 'Question',
            'name': f'What is the last date to apply for {title}?',
            'acceptedAnswer': {'@type': 'Answer', 'text': f'The last date to apply for {title} is {last_date}. Apply before the deadline at the official {org} website.'}
        })
    if vacancies:
        faqs.append({
            '@type': 'Question',
            'name': f'How many vacancies are available in {title}?',
            'acceptedAnswer': {'@type': 'Answer', 'text': f'Total {vacancies} vacancies are available under {title} by {org}.'}
        })
    if qual:
        faqs.append({
            '@type': 'Question',
            'name': f'What is the educational qualification for {title}?',
            'acceptedAnswer': {'@type': 'Answer', 'text': qual[:300] or 'Please refer to the official notification for qualification details.'}
        })
    fee_text = fee if fee else 'Please refer to the official notification for fee details.'
    faqs.append({
        '@type': 'Question',
        'name': f'How to apply online for {title}?',
        'acceptedAnswer': {'@type': 'Answer', 'text': f'Visit the official {org} website, find the {title} notification, register, fill the application form, upload documents, pay fee ({fee_text}), and submit.'}
    })
    return faqs

def clean_slug(s):
    """Strip sr_ prefixes and trailing hex hashes from slugs"""
    s = str(s or '').strip()
    s = re.sub(r'^sr_[a-z_]+-', '', s)
    s = re.sub(r'-[0-9a-f]{6,8}$', '', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:80] or ''

def e(s):
    """HTML escape"""
    return html_mod.escape(str(s or ''), quote=True)

def safe(v):
    """Convert any value to a clean string"""
    if v is None: return ''
    if isinstance(v, str): return v.strip()
    if isinstance(v, (int, float, bool)): return str(v).strip()
    if isinstance(v, list): return ', '.join(safe(x) for x in v if x is not None)
    if isinstance(v, dict):
        for k in ['text','value','name','description','details','qualification','eligibility','content']:
            if isinstance(v.get(k), str) and v[k].strip(): return v[k].strip()
        return ' | '.join(safe(val) for val in v.values() if val)
    return str(v).strip()

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

def is_blocked(url):
    return any(d in str(url).lower() for d in BLOCKED_DOMAINS)

# ── Section Renderers ──────────────────────────────────────────────────────────

CARD_STYLE = """
  .job-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
  .job-card-head{display:flex;align-items:center;gap:8px;padding:9px 14px;color:#fff;font-size:.86rem;font-weight:700}
  .job-card-head i{opacity:.85}
  .job-card-body{}
  .jd-table{width:100%;border-collapse:collapse;font-size:.82rem}
  .jd-table th{width:38%;background:#f8fafc;color:#374151;font-weight:700;padding:8px 12px;text-align:left;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word}
  .jd-table td{padding:8px 12px;color:#1e293b;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word;overflow-wrap:break-word}
  .jd-table tr:last-child th,.jd-table tr:last-child td{border-bottom:none}
  .jd-table a{color:#1d4ed8;word-break:break-all}
  .table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%}
  .vacancy-table{width:100%;border-collapse:collapse;font-size:.82rem;min-width:400px}
  .vacancy-table th{background:#1d4ed8;color:#fff;padding:8px 12px;font-weight:700;white-space:nowrap;text-align:left}
  .vacancy-table td{padding:8px 12px;border-bottom:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top}
  .vacancy-table .vac-total td{border-bottom:none;font-weight:700;background:#f0f9ff}
  .links-grid{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
  .link-btn{display:inline-flex;align-items:center;gap:5px;padding:7px 14px;border-radius:8px;font-size:.8rem;font-weight:700;text-decoration:none;white-space:nowrap;transition:all .15s}
  .btn-blue{background:#dbeafe;color:#1e40af;border:1px solid #93c5fd}
  .btn-blue:hover{background:#1e40af;color:#fff}
  .btn-green{background:#d1fae5;color:#065f46;border:1px solid #6ee7b7}
  .btn-green:hover{background:#059669;color:#fff}
  .btn-red{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5}
  .btn-red:hover{background:#dc2626;color:#fff}
  .btn-orange{background:#fef3c7;color:#92400e;border:1px solid #fcd34d}
  .btn-orange:hover{background:#d97706;color:#fff}
  .btn-purple{background:#ede9fe;color:#5b21b6;border:1px solid #c4b5fd}
  .btn-purple:hover{background:#6d28d9;color:#fff}
  .btn-teal{background:#ccfbf1;color:#0f766e;border:1px solid #5eead4}
  .btn-teal:hover{background:#0f766e;color:#fff}
  .btn-indigo{background:#e0e7ff;color:#3730a3;border:1px solid #a5b4fc}
  .btn-indigo:hover{background:#3730a3;color:#fff}
  .btn-gray{background:#f1f5f9;color:#475569;border:1px solid #cbd5e1}
  .btn-gray:hover{background:#475569;color:#fff}
  .sel-steps{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
  .sel-step{display:inline-flex;align-items:center;gap:6px;background:#f0f7ff;border:1px solid #bfdbfe;border-radius:8px;padding:6px 12px;font-size:.8rem;font-weight:600;color:#1e40af}
  .sel-num{background:#1e40af;color:#fff;border-radius:50%;width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;font-size:.65rem;font-weight:800;flex-shrink:0}
  .hta-list{list-style:none;margin:0;padding:0}
  .hta-item{display:flex;align-items:flex-start;gap:12px;padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:.83rem;color:#1e293b;line-height:1.65}
  .hta-item:last-child{border-bottom:none}
  .hta-num{flex-shrink:0;min-width:24px;height:24px;background:#0f766e;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:800}
  .inst-list{list-style:none;margin:0;padding:0}
  .inst-item{display:flex;align-items:flex-start;gap:10px;padding:9px 14px;border-bottom:1px solid #f1f5f9;font-size:.82rem;color:#78350f;line-height:1.6}
  .inst-item:last-child{border-bottom:none}
  .inst-item i{color:#ca8a04;flex-shrink:0;margin-top:2px}
  .fee-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}
  .fee-item{padding:10px 14px;border-right:1px solid #e9eef4;border-bottom:1px solid #e9eef4}
  .fee-label{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:3px}
  .fee-val{font-size:.9rem;font-weight:700;color:#1e293b}
  .fee-val.free{color:#16a34a}
  .fee-val.paid{color:#dc2626}
  .fee-note{padding:9px 14px;font-size:.81rem;color:#78350f;background:#fffbeb;border-top:1px solid #fde68a}
  .faq-item{border-bottom:1px solid #f1f5f9;font-size:.83rem}
  .faq-item:last-child{border-bottom:none}
  .faq-q{padding:10px 14px;font-weight:600;color:#1e293b;cursor:pointer;display:flex;align-items:center;gap:10px;user-select:none;text-align:left}
  .faq-q:hover{background:#f8fafc}
  .faq-icon{flex-shrink:0;min-width:26px;height:26px;background:#4f46e5;color:#fff;border-radius:6px;padding:0;font-size:.72rem;font-weight:800;display:flex;align-items:center;justify-content:center}
  .faq-q span[style]{flex:1;text-align:left}
  .faq-a{padding:0 14px 12px 50px;color:#475569;line-height:1.7;display:none}
  .faq-q.open+.faq-a{display:block}
  .short-info-card{background:#eff6ff;border-left:4px solid #1d4ed8;padding:12px 14px;font-size:.84rem;color:#1e293b;line-height:1.7;margin-bottom:12px;border-radius:0 8px 8px 0}
  .jd-header{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px 0;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
  .jd-title{font-size:1.15rem;font-weight:800;color:#0f172a;line-height:1.4;margin:0 0 8px}
  .jd-badge-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
  .jd-badge{display:inline-flex;align-items:center;gap:4px;background:#dbeafe;color:#1e40af;font-size:.71rem;font-weight:700;text-transform:uppercase;padding:3px 8px;border-radius:12px}
  .jd-stats{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #e2e8f0}
  @media(max-width:600px){.jd-stats{grid-template-columns:repeat(2,1fr)}}
  .jd-stat{padding:11px 6px;text-align:center;border-right:1px solid #e2e8f0}
  .jd-stat:last-child{border-right:none}
  .jd-stat-val{font-size:.95rem;font-weight:800;color:#0f172a}
  .jd-stat-lbl{font-size:.67rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
  .jd-wrap{max-width:860px;margin:0 auto;padding:12px 10px 40px}
  .jd-bc{font-size:.75rem;color:#64748b;margin-bottom:12px;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
  .jd-bc a{color:#1d4ed8;text-decoration:none}
  .jd-bc a:hover{text-decoration:underline}
  .notice-bar{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;font-size:.8rem;color:#78350f;margin-bottom:12px;display:flex;gap:8px;align-items:flex-start}
  .notice-bar i{flex-shrink:0;margin-top:2px}
  @media(max-width:600px){.jd-stats{grid-template-columns:repeat(2,1fr)}.jd-stat:nth-child(2){border-right:none}.jd-stat:nth-child(3){border-top:1px solid #e2e8f0}.jd-stat:nth-child(4){border-top:1px solid #e2e8f0;border-right:none}}
"""

def render_card(grad, icon, heading, body_html):
    if not body_html or not body_html.strip():
        return ''
    return f'''<div class="job-card">
  <div class="job-card-head" style="background:{grad}">
    <i class="fa-solid {icon}"></i><h2 style="margin:0;font-size:.86rem">{e(heading)}</h2>
  </div>
  <div class="job-card-body">{body_html}</div>
</div>'''

def render_table_rows(pairs):
    """Render key-value pairs as table rows (skip empty values)"""
    rows = ''
    for label, val in pairs:
        sv = safe(val)
        if not sv: continue
        rows += f'<tr><th>{e(label)}</th><td>{e(sv)}</td></tr>'
    return rows

def render_important_dates(dates_obj):
    if not dates_obj or not isinstance(dates_obj, dict): return ''
    DATE_FIELDS = [
        ('application_start_date','Application Start Date'),
        ('application_begin','Application Begin'),
        ('start_date','Start Date'),
        ('date_of_notification','Notification Date'),
        ('notification_date','Notification Date'),
        ('last_date_to_apply','Last Date to Apply'),
        ('last_date','Last Date'),
        ('application_last_date','Application Last Date'),
        ('fee_payment_last_date','Fee Payment Last Date'),
        ('fee_last_date','Fee Last Date'),
        ('correction_last_date','Correction Last Date'),
        ('exam_date','Exam Date'),
        ('written_exam_date','Written Exam Date'),
        ('online_exam_date','Online Exam Date'),
        ('omr_exam_date','OMR Exam Date'),
        ('interview_date','Interview Date'),
        ('admit_card_date','Admit Card Date'),
        ('admit_card','Admit Card Available'),
        ('result_date','Result Date'),
        ('event','Event'),
    ]
    rows = ''
    seen = set()
    for key, label in DATE_FIELDS:
        val = safe(dates_obj.get(key))
        if val and label not in seen:
            seen.add(label)
            is_last = 'last' in key or 'closing' in key
            style = ' style="color:#dc2626;font-weight:700"' if is_last else ''
            rows += f'<tr><th>{e(label)}</th><td{style}>{e(val)}</td></tr>'
    # Render remaining keys not in the fixed list
    fixed_keys = {k for k, _ in DATE_FIELDS}
    for key, val in dates_obj.items():
        if key in fixed_keys: continue
        sv = safe(val)
        if not sv: continue
        label = key.replace('_',' ').title()
        if label in seen: continue
        seen.add(label)
        rows += f'<tr><th>{e(label)}</th><td>{e(sv)}</td></tr>'
    if not rows: return ''
    return render_card('linear-gradient(135deg,#b91c1c,#dc2626)', 'fa-calendar-check', 'Important Dates',
                       f'<table class="jd-table"><tbody>{rows}</tbody></table>')

def render_application_fee(fee_obj):
    if not fee_obj or not isinstance(fee_obj, dict): return ''
    FIELDS = [
        ('general','General / UR'),('general_fee','General / UR'),('ur','UR'),
        ('obc','OBC'),('obc_fee','OBC'),('sc','SC'),('sc_fee','SC'),('st','ST'),
        ('ews','EWS'),('female','Female'),('pwd','PH / Divyang'),('ph','PH / Divyang'),
        ('ex_serviceman_fee','Ex-Serviceman'),('all','All Categories'),
        ('all_category','All Categories'),
    ]
    def is_free(v): return bool(re.search(r'nil|0|free|no fee|exempt', v, re.I))
    items_html = ''; seen = set()
    for key, label in FIELDS:
        val = safe(fee_obj.get(key))
        if not val or label in seen: continue
        seen.add(label)
        cls = 'free' if is_free(val) else 'paid'
        items_html += f'<div class="fee-item"><div class="fee-label">{e(label)}</div><div class="fee-val {cls}">{e(val)}</div></div>'
    note = safe(fee_obj.get('details') or fee_obj.get('fee_mode') or fee_obj.get('payment_mode') or '')
    if not items_html and not note: return ''
    body = f'<div class="fee-grid">{items_html}</div>' if items_html else ''
    if note: body += f'<div class="fee-note"><i class="fa-solid fa-circle-info"></i> {e(note)}</div>'
    return render_card('linear-gradient(135deg,#c2410c,#ea580c)', 'fa-indian-rupee-sign', 'Application Fee', body)

def render_age_limit(age_obj):
    if not age_obj or not isinstance(age_obj, dict): return ''
    FIELDS = [
        ('minimum_age','Minimum Age'),('min_age','Minimum Age'),
        ('maximum_age','Maximum Age'),('max_age','Maximum Age'),('age_limit','Age Limit'),
        ('age_relaxation','Age Relaxation'),('details','Details'),('age_details','Age Details'),
    ]
    rows = render_table_rows([(lbl, age_obj.get(k)) for k, lbl in FIELDS])
    if not rows: return ''
    return render_card('linear-gradient(135deg,#0f766e,#0891b2)', 'fa-user-clock', 'Age Limit',
                       f'<table class="jd-table"><tbody>{rows}</tbody></table>')

def render_qualification(qual_obj):
    if not qual_obj: return ''
    FIELDS = [
        ('education_qualification','Education Qualification'),
        ('qualification','Qualification'),('eligibility','Eligibility'),
        ('required_degree','Required Degree'),('technical_qualification','Technical Qualification'),
        ('experience_required','Experience Required'),('details','Details'),
        ('matched_qualifications','Matched Qualifications'),
    ]
    if isinstance(qual_obj, str):
        if not qual_obj.strip(): return ''
        return render_card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-graduation-cap', 'Qualification / Eligibility',
                           f'<div style="padding:10px 14px;font-size:.83rem;color:#1e293b;">{e(qual_obj)}</div>')
    if isinstance(qual_obj, dict):
        rows = render_table_rows([(lbl, qual_obj.get(k)) for k, lbl in FIELDS])
        if not rows: return ''
        return render_card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-graduation-cap', 'Qualification / Eligibility',
                           f'<table class="jd-table"><tbody>{rows}</tbody></table>')
    return ''

def render_vacancy_details(vac_list):
    if not vac_list or not isinstance(vac_list, list): return ''
    COLUMN_MAP = {
        'post_name': ['post_name','post','name','Post Name','Name Of Post','Post'],
        'total':     ['total','total_vacancies','total_posts','vacancies','posts','Total Posts','Vacancy','Total Vacancies','Total'],
        'ur':        ['ur','general','UR','General (UR)','General'],
        'obc':       ['obc','OBC'],
        'sc':        ['sc','SC'],
        'st':        ['st','ST'],
        'ews':       ['ews','EWS'],
        'women':     ['women','Women','female','Female'],
        'salary':    ['salary','pay_scale','Scale of Pay','Salary','Pay Scale'],
        'qualification': ['eligibility','qualification','educational_qualification','Educational Qualification','Qualification'],
        'department': ['department','Department'],
    }
    COL_ORDER  = ['post_name','total','ur','obc','sc','st','ews','women','salary','qualification','department']
    COL_LABELS = {'post_name':'Post Name','total':'Total Posts','ur':'UR/General','obc':'OBC','sc':'SC',
                  'st':'ST','ews':'EWS','women':'Women','salary':'Salary / Pay Scale',
                  'qualification':'Qualification','department':'Department'}
    normalized = []; available = set()
    for row in vac_list:
        if not isinstance(row, dict): continue
        norm = {}
        for col, aliases in COLUMN_MAP.items():
            for alias in aliases:
                if alias in row and row[alias] not in (None,'',{},[]):
                    norm[col] = safe(row[alias])
                    available.add(col)
                    break
        if norm: normalized.append(norm)
    if not normalized: return ''
    cols = [c for c in COL_ORDER if c in available]
    if not cols: return ''
    head = '<th>Sr. No.</th>' + ''.join(f'<th>{COL_LABELS[c]}</th>' for c in cols)
    rows_html = ''; totals = {}
    for i, row in enumerate(normalized, 1):
        cells = f'<td>{i}</td>' + ''.join(f'<td>{e(row.get(c,""))}</td>' for c in cols)
        rows_html += f'<tr>{cells}</tr>'
        for c in ['total','ur','obc','sc','st','ews','women']:
            if c in cols:
                try: totals[c] = totals.get(c,0) + int(re.sub(r'\D','', row.get(c,'0') or '0') or '0')
                except: pass
    if totals:
        tcells = '<td><strong>Total</strong></td>'
        for c in cols:
            tcells += f'<td>{"<strong>"+str(totals[c])+"</strong>" if c in totals else ""}</td>'
        rows_html += f'<tr class="vac-total">{tcells}</tr>'
    body = f'<div class="table-scroll"><table class="vacancy-table"><thead><tr>{head}</tr></thead><tbody>{rows_html}</tbody></table></div>'
    return render_card('linear-gradient(135deg,#15803d,#16a34a)', 'fa-chart-pie', 'Vacancy Details', body)

def render_category_vacancy(cwv):
    if not cwv: return ''
    if isinstance(cwv, list):
        return render_vacancy_details(cwv)
    if isinstance(cwv, dict) and cwv:
        pairs = [(k.replace('_',' ').title(), v) for k, v in cwv.items() if safe(v)]
        if not pairs: return ''
        rows = ''.join(f'<tr><td>{e(l)}</td><td>{e(safe(v))}</td></tr>' for l, v in pairs)
        body = f'<div class="table-scroll"><table class="vacancy-table"><thead><tr><th>Category</th><th>Posts</th></tr></thead><tbody>{rows}</tbody></table></div>'
        return render_card('linear-gradient(135deg,#15803d,#16a34a)', 'fa-chart-bar', 'Category-wise Vacancy', body)
    return ''

def render_salary(sal_obj):
    if not sal_obj: return ''
    FIELDS = [
        ('pay_scale','Pay Scale'),('basic_pay','Basic Pay'),('grade_pay','Grade Pay'),
        ('salary','Salary'),('allowance','Allowance'),('details','Details'),
    ]
    if isinstance(sal_obj, str):
        if not sal_obj.strip(): return ''
        return render_card('linear-gradient(135deg,#15803d,#16a34a)', 'fa-indian-rupee-sign', 'Salary & Pay Scale',
                           f'<div style="padding:10px 14px;font-size:.83rem;color:#1e293b;">{e(sal_obj)}</div>')
    if isinstance(sal_obj, dict):
        rows = render_table_rows([(lbl, sal_obj.get(k)) for k, lbl in FIELDS])
        if not rows: return ''
        return render_card('linear-gradient(135deg,#15803d,#16a34a)', 'fa-indian-rupee-sign', 'Salary & Pay Scale',
                           f'<table class="jd-table"><tbody>{rows}</tbody></table>')
    return ''

def render_selection_process(sp):
    if not sp: return ''
    steps = []
    if isinstance(sp, list): steps = [safe(s) for s in sp if safe(s)]
    elif isinstance(sp, str): steps = [s.strip() for s in re.split(r'[,\n;/]', sp) if s.strip()]
    if not steps: return ''
    items = ''.join(f'<div class="sel-step"><span class="sel-num">{i+1}</span>{e(s[:80])}</div>' for i, s in enumerate(steps))
    return render_card('linear-gradient(135deg,#5b21b6,#7c3aed)', 'fa-list-check', 'Selection Process',
                       f'<div class="sel-steps">{items}</div>')

def render_exam_pattern(ep):
    if not ep: return ''
    if isinstance(ep, list) and ep:
        cols = list(ep[0].keys()) if isinstance(ep[0], dict) else []
        if not cols: return ''
        head = '<th>Sr.No</th>' + ''.join(f'<th>{e(c.replace("_"," ").title())}</th>' for c in cols)
        rows = ''.join(f'<tr><td>{i+1}</td>' + ''.join(f'<td>{e(safe(r.get(c)))}</td>' for c in cols) + '</tr>'
                       for i, r in enumerate(ep) if isinstance(r, dict))
        body = f'<div class="table-scroll"><table class="vacancy-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
        return render_card('linear-gradient(135deg,#0369a1,#0284c7)', 'fa-file-lines', 'Exam Pattern', body)
    if isinstance(ep, dict) and ep:
        rows = render_table_rows([(k.replace('_',' ').title(), v) for k, v in ep.items()])
        if not rows: return ''
        return render_card('linear-gradient(135deg,#0369a1,#0284c7)', 'fa-file-lines', 'Exam Pattern',
                           f'<table class="jd-table"><tbody>{rows}</tbody></table>')
    if isinstance(ep, str) and ep.strip():
        return render_card('linear-gradient(135deg,#0369a1,#0284c7)', 'fa-file-lines', 'Exam Pattern',
                           f'<div style="padding:10px 14px;font-size:.83rem;color:#1e293b;">{e(ep)}</div>')
    return ''

def render_syllabus(syl):
    if not syl: return ''
    if isinstance(syl, list):
        items = ''.join(f'<div class="sel-step"><i class="fa-solid fa-book-open"></i>{e(safe(s)[:100])}</div>' for s in syl if safe(s))
        if not items: return ''
        return render_card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-book', 'Syllabus',
                           f'<div class="sel-steps">{items}</div>')
    if isinstance(syl, dict):
        rows = render_table_rows([(k.replace('_',' ').title(), v) for k, v in syl.items()])
        if not rows: return ''
        return render_card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-book', 'Syllabus',
                           f'<table class="jd-table"><tbody>{rows}</tbody></table>')
    if isinstance(syl, str) and syl.strip():
        return render_card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-book', 'Syllabus',
                           f'<div style="padding:10px 14px;font-size:.83rem;">{e(syl)}</div>')
    return ''

def render_physical_eligibility(pe):
    if not pe or not isinstance(pe, dict): return ''
    pairs = [(k.replace('_',' ').title(), v) for k, v in pe.items() if safe(v)]
    if not pairs: return ''
    rows = render_table_rows(pairs)
    return render_card('linear-gradient(135deg,#be123c,#e11d48)', 'fa-dumbbell', 'Physical Eligibility / Standards',
                       f'<table class="jd-table"><tbody>{rows}</tbody></table>')

def render_how_to_apply(steps):
    if not isinstance(steps, list) or not steps: return ''
    filtered = [safe(s) for s in steps if safe(s)]
    if not filtered: return ''
    items = ''.join(f'<li class="hta-item"><span class="hta-num">{i+1}</span><span>{e(s)}</span></li>' for i, s in enumerate(filtered))
    return render_card('linear-gradient(135deg,#0f766e,#0891b2)', 'fa-clipboard-list', 'How to Apply',
                       f'<ul class="hta-list">{items}</ul>')

def render_instructions(insts):
    if not isinstance(insts, list) or not insts: return ''
    filtered = [safe(s) for s in insts if safe(s)]
    if not filtered: return ''
    items = ''.join(f'<li class="inst-item"><i class="fa-solid fa-triangle-exclamation"></i><span>{e(s)}</span></li>' for s in filtered)
    return render_card('linear-gradient(135deg,#b45309,#ca8a04)', 'fa-circle-exclamation', 'Important Instructions',
                       f'<ul class="inst-list">{items}</ul>')

LINK_CONFIG = {
    'apply_online':          ('Apply Online',          'btn-blue',   'fa-paper-plane'),
    'official_website':      ('Official Website',      'btn-green',  'fa-globe'),
    'notification_pdf':      ('Download Notification', 'btn-red',    'fa-file-pdf'),
    'download_notification': ('Download Notification', 'btn-red',    'fa-file-pdf'),
    'official_notification': ('Official Notification', 'btn-red',    'fa-file-pdf'),
    'registration_link':     ('Register Now',          'btn-orange', 'fa-user-plus'),
    'login_link':            ('Login',                 'btn-purple', 'fa-right-to-bracket'),
    'admit_card':            ('Admit Card',            'btn-teal',   'fa-id-card'),
    'answer_key':            ('Answer Key',            'btn-indigo', 'fa-key'),
    'syllabus_pdf':          ('Syllabus PDF',          'btn-gray',   'fa-book'),
    'result_link':           ('Result',                'btn-green',  'fa-trophy'),
    'click_here':            ('Open Link',             'btn-blue',   'fa-link'),
    'merit_list':            ('Merit List',            'btn-teal',   'fa-list'),
    'score_card':            ('Score Card',            'btn-orange', 'fa-file'),
}

def smart_label_from_url(url, fallback, job_title='', org=''):
    """Infer SEO-friendly label from URL patterns + job context if fallback is generic."""
    u = url.lower()
    ctx = (job_title or org or '').strip()
    if re.match(r'^(click here|view|link|here|open link|open)$', fallback.strip(), re.I):
        if 'admit' in u or 'hallticket' in u or 'hall-ticket' in u:
            return f'Download {ctx} Admit Card' if ctx else 'Download Admit Card'
        if 'answer' in u or 'anskey' in u:
            return f'{ctx} Answer Key' if ctx else 'Download Answer Key'
        if 'syllabus' in u:
            return f'Download {ctx} Syllabus' if ctx else 'Download Syllabus'
        if 'result' in u or 'merit' in u or 'scorecard' in u:
            return f'Check {ctx} Result' if ctx else 'Check Result'
        if '.pdf' in u or 'notification' in u or 'advt' in u or 'advertisement' in u:
            return f'Download {ctx} Notification PDF' if ctx else 'Download Notification PDF'
        if 'login' in u or 'signin' in u:
            return f'{ctx} Candidate Login' if ctx else 'Candidate Login'
        if 'register' in u or 'signup' in u:
            return f'Register for {ctx}' if ctx else 'Register Now'
        if 'apply' in u or 'application' in u or 'career' in u or 'recruit' in u:
            return f'Apply Online for {ctx}' if ctx else 'Apply Online'
    return fallback

def smart_icon(label_lower, url):
    u = url.lower()
    if '.pdf' in u or 'notification' in label_lower or 'pdf' in label_lower or 'advt' in label_lower:
        return 'fa-file-pdf'
    if 'admit' in label_lower or 'hallticket' in u: return 'fa-id-card'
    if 'result' in label_lower or 'merit' in label_lower: return 'fa-trophy'
    if 'answer' in label_lower: return 'fa-key'
    if 'syllabus' in label_lower: return 'fa-book'
    if 'login' in label_lower or 'candidate' in label_lower: return 'fa-right-to-bracket'
    if 'register' in label_lower: return 'fa-user-plus'
    if 'apply' in label_lower or 'application' in label_lower: return 'fa-paper-plane'
    if 'website' in label_lower or ('official' in label_lower and '.pdf' not in u): return 'fa-globe'
    return 'fa-link'

def smart_css(label_lower, url):
    u = url.lower()
    if '.pdf' in u or 'notification' in label_lower or 'pdf' in label_lower: return 'btn-red'
    if 'admit' in label_lower: return 'btn-teal'
    if 'result' in label_lower or 'merit' in label_lower: return 'btn-green'
    if 'answer' in label_lower: return 'btn-indigo'
    if 'syllabus' in label_lower: return 'btn-gray'
    if 'login' in label_lower: return 'btn-purple'
    if 'register' in label_lower: return 'btn-orange'
    if 'apply' in label_lower: return 'btn-blue'
    if 'website' in label_lower or ('official' in label_lower and '.pdf' not in u): return 'btn-green'
    return 'btn-blue'

def render_important_links(il_obj, job_title='', org=''):
    if not il_obj: return ''
    buttons = ''; seen = set()

    # FORMAT A: list of {label, url} objects (SR/Sarkari format)
    if isinstance(il_obj, list):
        for item in il_obj:
            if not isinstance(item, dict): continue
            url = str(item.get('url') or item.get('href') or '').strip()
            lbl = str(item.get('label') or item.get('title') or '').strip()
            if not url.startswith('http') or is_blocked(url) or url in seen: continue
            seen.add(url)
            lbl = smart_label_from_url(url, lbl or 'Open Link', job_title, org)
            lbl_lower = lbl.lower()
            icon_k = smart_icon(lbl_lower, url)
            css_k  = smart_css(lbl_lower, url)
            buttons += f'<a href="{e(url)}" class="link-btn {css_k}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {icon_k}"></i> {e(lbl[:60])}</a>\n'
        if buttons:
            return render_card('linear-gradient(135deg,#1e40af,#1e3a8a)', 'fa-link', 'Important Links',
                               f'<div class="links-grid">{buttons}</div>')
        return ''

    # FORMAT B/C/D: dict format
    if not isinstance(il_obj, dict): return ''

    # Extract _labels for click_here / generic key disambiguation
    _labels = il_obj.get('_labels', {})
    if not isinstance(_labels, dict): _labels = {}

    for key, val in il_obj.items():
        if key in ('structured_links', '_labels', 'seo_tags', '_useful_links'): continue
        urls = val if isinstance(val, list) else [val]
        raw_label, css, icon = LINK_CONFIG.get(key, ('Open Link', 'btn-blue', 'fa-link'))
        label_override = str(_labels.get(key, '') or '').strip()
        label = label_override if label_override and not re.match(r'^(click here|view|link|here|open)$', label_override, re.I) else raw_label
        url_count = sum(1 for u in urls if str(u or '').startswith('http'))
        for idx, url in enumerate(urls):
            url = str(url or '').strip()
            if not url.startswith('http') or is_blocked(url) or url in seen: continue
            seen.add(url)
            final_label = label if url_count <= 1 else f'{label} ({idx+1})'
            final_label = smart_label_from_url(url, final_label, job_title, org)
            lbl_lower = final_label.lower()
            _icon = smart_icon(lbl_lower, url)
            _css  = smart_css(lbl_lower, url)
            buttons += f'<a href="{e(url)}" class="link-btn {_css}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {_icon}"></i> {e(final_label[:60])}</a>\n'

    structured = il_obj.get('structured_links', [])
    if isinstance(structured, list):
        for item in structured:
            if not isinstance(item, dict): continue
            url = str(item.get('url','') or item.get('href','')).strip()
            lbl = str(item.get('label','') or item.get('title','') or 'Open Link').strip() or 'Open Link'
            if not url.startswith('http') or is_blocked(url) or url in seen: continue
            seen.add(url)
            lbl = smart_label_from_url(url, lbl, job_title, org)
            lbl_lower = lbl.lower()
            icon_k = smart_icon(lbl_lower, url)
            css_k  = smart_css(lbl_lower, url)
            buttons += f'<a href="{e(url)}" class="link-btn {css_k}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {icon_k}"></i> {e(lbl[:60])}</a>\n'

    if not buttons: return ''
    return render_card('linear-gradient(135deg,#1e40af,#1e3a8a)', 'fa-link', 'Important Links',
                       f'<div class="links-grid">{buttons}</div>')

def render_faq(faq_list):
    if not isinstance(faq_list, list) or not faq_list: return ''
    import re as _re

    def is_label(s):
        s = s.strip()
        return bool(_re.search(r':\s*$', s)) or bool(_re.match(
            r'^(application|last date|exam date|admit card|fee|age|minimum|maximum|eligibility|vacancy|result|notification|start|end|begin|close)', s, _re.I))

    def is_value(s):
        s = s.strip()
        return bool(_re.match(r'^\d{1,2}/\d{1,2}/\d{4}|^\d{2,4}$|^\d+\s*(years?|posts?|vacancies|rs\.?|rupees?|/-)', s, _re.I))

    # Dedup by normalized question (strip Q1. prefix)
    seen = {}
    deduped = []
    for item in faq_list:
        if not isinstance(item, dict): continue
        q = safe(item.get('question',''))
        a = safe(item.get('answer',''))
        if not q or not a: continue
        # Q/A swap fix
        if is_label(a) and is_value(q):
            q, a = _re.sub(r':\s*$', '', a).strip(), q
        # Normalize key: strip "Q1. " prefix
        key = _re.sub(r'^q\d+[\.\)]\s*', '', q.lower().strip())
        if key in seen: continue
        seen[key] = True
        deduped.append((q, a))

    items = ''
    for idx, (q, a) in enumerate(deduped, 1):
        items += f'''<div class="faq-item">
  <div class="faq-q" onclick="this.classList.toggle('open');this.nextElementSibling.style.display=this.classList.contains('open')?'block':'none'">
    <span class="faq-icon">{idx}</span>
    <span style="flex:1;text-align:left;line-height:1.5">{e(q)}</span>
    <i class="fa-solid fa-chevron-down" style="font-size:.72rem;color:#94a3b8;margin-left:auto;flex-shrink:0;transition:transform .22s"></i>
  </div>
  <div class="faq-a">{e(a)}</div>
</div>'''
    if not items: return ''
    return render_card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-circle-question', 'FAQs', items)

# ── Main static HTML builder ──────────────────────────────────────────────────

# ISSUE-021 FIX: Related jobs for internal linking — built at runtime from seen_slugs index
# _ALL_JOBS_FOR_RELATED is populated during the main loop before we generate pages
_ALL_JOBS_FOR_RELATED = []  # list of (slug, title, state, qual_text)

def generate_related_jobs_html(current_slug, current_state, current_qual, max_items=6):
    """Find related jobs by same state or qualification — internal linking (ISSUE-021)."""
    if not _ALL_JOBS_FOR_RELATED:
        return ''
    related = []
    # Same state first, then same qual
    for slug, title, state, qual in _ALL_JOBS_FOR_RELATED:
        if slug == current_slug: continue
        if state and state == current_state:
            related.append((slug, title))
        if len(related) >= max_items: break
    if len(related) < max_items:
        for slug, title, state, qual in _ALL_JOBS_FOR_RELATED:
            if slug == current_slug: continue
            if (slug, title) in related: continue
            if qual and qual == current_qual:
                related.append((slug, title))
            if len(related) >= max_items: break
    if not related:
        return ''
    items = ''.join(
        f'<li style="border-bottom:1px solid #f1f5f9;padding:8px 14px">'
        f'<a href="/jobs/{s}/" style="color:#1d4ed8;font-size:.82rem;text-decoration:none;display:block;line-height:1.4">'
        f'{e(t[:80])}</a></li>'
        for s, t in related
    )
    return (f'<div class="job-card" style="margin-top:8px">'
            f'<div class="job-card-head" style="background:#1e40af"><i class="fa-solid fa-briefcase"></i> Related Government Jobs</div>'
            f'<ul style="list-style:none;margin:0;padding:0">{items}</ul>'
            f'</div>')


def build_static_html(slug, title, full_job_obj, cat):
    """Build COMPLETE pre-rendered HTML — no JS redirect, fully self-contained"""
    bd     = full_job_obj.get('basic_details', {}) or {}
    dates  = full_job_obj.get('important_dates', {}) or {}
    fee    = full_job_obj.get('application_fee', {}) or {}
    age    = full_job_obj.get('age_limit', {}) or {}
    qual   = full_job_obj.get('qualification') or {}
    vac    = full_job_obj.get('vacancy_details') or []
    cwv    = full_job_obj.get('category_wise_vacancy') or {}
    sal    = full_job_obj.get('salary_details') or {}
    sel    = full_job_obj.get('selection_process') or []
    ep     = full_job_obj.get('exam_pattern')
    syl    = full_job_obj.get('syllabus')
    pe     = full_job_obj.get('physical_eligibility') or {}
    hta    = full_job_obj.get('how_to_apply') or []
    insts  = full_job_obj.get('important_instructions') or []
    il     = full_job_obj.get('important_links') or full_job_obj.get('importantLinks') or {}
    faq    = full_job_obj.get('faq') or []

    canon_url  = f"{BASE_URL}/jobs/{slug}/"
    cat_label  = CAT_LABELS.get(cat, 'Government Jobs')
    org        = safe(bd.get('organization_name') or bd.get('post_name') or bd.get('job_title') or 'Government of India')
    vacancies  = safe(bd.get('total_vacancies') or bd.get('total_vacancy') or '')
    last_date_r= safe(dates.get('last_date_to_apply') or dates.get('last_date') or '')
    apply_mode = safe(bd.get('application_mode') or 'Online')
    location   = safe(bd.get('job_location') or 'India')
    short_info = safe(bd.get('short_information') or '')
    posted_date= normalise_date(safe(bd.get('last_updated') or dates.get('date_of_notification') or dates.get('date of notification') or '')) or TODAY
    source_url = safe(full_job_obj.get('source_url') or '')
    qual_text  = safe(qual.get('education_qualification') if isinstance(qual, dict) else '')
    fee_text   = safe(fee.get('general_fee') if isinstance(fee, dict) else '')

    # ISSUE-006 FIX: Optimized SEO title using helper
    title_tag = build_seo_title(title, org, vacancies)

    # ISSUE-006 FIX: Optimized meta description using helper
    meta_desc = build_seo_meta_desc(title, org, vacancies, last_date_r, qual_text)

    # ISSUE-032 FIX: news_keywords meta for Google News eligibility
    state_kw = safe(full_job_obj.get('state', ''))
    news_keywords = f"{org}, sarkari naukri, government job 2026{', ' + state_kw + ' recruitment' if state_kw else ''}"

    # Schema — ISSUE-024 FIX: BreadcrumbList merged into @graph with Organization entity
    org_schema = bd.get('organization_name') or 'Government of India'
    job_schema = {
        '@context':'https://schema.org',
        '@graph': [
            {
                '@type': 'Organization',
                '@id': 'https://www.topsarkarijobs.com/#org',
                'name': 'Top Sarkari Jobs',
                'url': 'https://www.topsarkarijobs.com/'
            },
            {
                '@type':'JobPosting',
                'title':title,'description':short_info or meta_desc,
                'datePosted':posted_date,'employmentType':'FULL_TIME','url':canon_url,
                'identifier':{'@type':'PropertyValue','name':org_schema,'value':slug},
                'applicantLocationRequirements':{'@type':'Country','name':'India'},
                'hiringOrganization':{'@type':'Organization','name':org_schema,'sameAs':'https://www.india.gov.in'},
                'jobLocation':{'@type':'Place','address':{'@type':'PostalAddress','addressCountry':'IN','addressLocality':location}},
                'directApply': False,
                # ISSUE-027 FIX: speakable schema for Google Assistant / AI Search
                'speakable': {'@type':'SpeakableSpecification','cssSelector':['.jd-title','.notice-bar','.jd-stats']},
            },
            # ISSUE-026 FIX: Article schema for E-E-A-T signals
            {
                '@type': 'Article',
                'headline': title,
                'url': canon_url,
                'datePublished': posted_date,
                'dateModified': TODAY,
                'author': {
                    '@type': 'Organization',
                    'name': 'Top Sarkari Jobs Editorial Team',
                    'url': 'https://www.topsarkarijobs.com/about/'
                },
                'publisher': {
                    '@type': 'Organization',
                    '@id': 'https://www.topsarkarijobs.com/#org'
                },
                'inLanguage': 'en-IN'
            },
            {
                '@type':'BreadcrumbList',
                'itemListElement':[
                    {'@type':'ListItem','position':1,'name':'Home','item':f'{BASE_URL}/'},
                    {'@type':'ListItem','position':2,'name':'Latest Jobs','item':f'{BASE_URL}/section/latest-jobs/'},
                    {'@type':'ListItem','position':3,'name':title,'item':canon_url}
                ]
            }
        ]
    }
    jp = job_schema['@graph'][1]
    if last_date_r:
        iso = normalise_date(last_date_r)
        if iso: jp['validThrough'] = iso; jp['applicationDeadline'] = iso
    if vacancies:
        vn = re.search(r'\d+', str(vacancies))
        if vn: jp['totalJobOpenings'] = int(vn.group())

    # ISSUE-009 FIX: FAQ schema — use native FAQ data OR auto-generate
    faq_main_entity = []
    for f in (faq if isinstance(faq, list) else [])[:5]:
        if isinstance(f, dict) and f.get('question') and f.get('answer'):
            faq_main_entity.append({'@type':'Question','name':f['question'],'acceptedAnswer':{'@type':'Answer','text':f['answer']}})
    if not faq_main_entity:
        # Auto-generate FAQ if no native FAQ data (ISSUE-009)
        faq_main_entity = build_auto_faq(title, org, last_date_r, vacancies, qual_text, fee_text)
    if faq_main_entity:
        faq_schema = {'@context':'https://schema.org','@type':'FAQPage','mainEntity':faq_main_entity}
        faq_schema_tag = f'<script type="application/ld+json">{json.dumps(faq_schema, ensure_ascii=False)}</script>'
    else:
        faq_schema_tag = ''

    # ── Build the 16-section body ──
    sections_html = ''

    # 1. Header Card
    BD_FIELDS = [
        ('organization_name','Organization'),('post_name','Post Name'),
        ('total_vacancies','Total Vacancies'),('application_mode','Application Mode'),
        ('job_location','Job Location'),('job_type','Job Type'),
        ('notification_number','Notification No.'),('advt_no','Advertisement No.'),
        ('last_updated','Last Updated'),('post_date','Post Date'),
    ]
    hdr_rows = ''
    for key, label in BD_FIELDS:
        val = safe(bd.get(key))
        if not val: continue
        hdr_rows += f'<tr><th>{e(label)}</th><td>{e(val)}</td></tr>'
    if source_url and not is_blocked(source_url):
        hdr_rows += f'<tr><th>Official Website</th><td><a href="{e(source_url)}" target="_blank" rel="noopener noreferrer">{e(source_url[:80])}</a></td></tr>'

    # Stats bar
    stat_vac = e(vacancies or '—')
    stat_ld  = e(last_date_r or '—')
    stat_mode = e(apply_mode or '—')
    stat_loc = e(location[:20] if location else '—')

    header_html = f'''<div class="jd-header">
  <div class="jd-badge-row">
    <span class="jd-badge"><i class="fa-solid fa-briefcase"></i> {e(cat_label)}</span>
    <span class="jd-badge" style="background:#dcfce7;color:#166534"><i class="fa-solid fa-map-pin"></i> {e(location[:30])}</span>
  </div>
  <h1 class="jd-title">{e(title)}</h1>
  {f'<table class="jd-table" style="margin-bottom:0"><tbody>{hdr_rows}</tbody></table>' if hdr_rows else ''}
  <div class="jd-stats">
    <div class="jd-stat"><div class="jd-stat-val">{stat_vac}</div><div class="jd-stat-lbl">Vacancies</div></div>
    <div class="jd-stat"><div class="jd-stat-val" style="color:#dc2626">{stat_ld}</div><div class="jd-stat-lbl">Last Date</div></div>
    <div class="jd-stat"><div class="jd-stat-val">{stat_mode}</div><div class="jd-stat-lbl">Apply Mode</div></div>
    <div class="jd-stat"><div class="jd-stat-val">{stat_loc}</div><div class="jd-stat-lbl">Location</div></div>
  </div>
</div>'''

    if short_info:
        sections_html += f'<div class="short-info-card"><i class="fa-solid fa-circle-info" style="color:#1d4ed8;margin-right:6px"></i>{e(short_info)}</div>'

    sections_html += render_important_dates(dates)
    sections_html += render_application_fee(fee)
    sections_html += render_age_limit(age)
    sections_html += render_qualification(qual)
    sections_html += render_vacancy_details(vac)
    sections_html += render_category_vacancy(cwv)
    sections_html += render_salary(sal)
    sections_html += render_selection_process(sel)
    sections_html += render_exam_pattern(ep)
    sections_html += render_syllabus(syl)
    sections_html += render_physical_eligibility(pe)
    sections_html += render_how_to_apply(hta)
    sections_html += render_instructions(insts)
    sections_html += render_important_links(il, job_title=title, org=org)
    sections_html += render_faq(faq)
    # ISSUE-021 FIX: Related jobs for internal linking (PageRank flow to job pages)
    sections_html += generate_related_jobs_html(
        slug,
        safe(full_job_obj.get('state', '')),
        qual_text[:30]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{e(title_tag)} | Top Sarkari Jobs</title>
  <meta name="description" content="{e(meta_desc)}"/>
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"/>
  <link rel="canonical" href="{canon_url}"/>
  <link rel="alternate" hreflang="en-IN" href="{canon_url}"/>
  <link rel="alternate" hreflang="x-default" href="{canon_url}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:site_name" content="Top Sarkari Jobs"/>
  <meta property="og:title" content="{e(title_tag)} | Top Sarkari Jobs"/>
  <meta property="og:description" content="{e(meta_desc)}"/>
  <meta property="og:url" content="{canon_url}"/>
  <meta property="og:image" content="{BASE_URL}/image.png"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{e(title_tag)} | Top Sarkari Jobs"/>
  <meta name="twitter:description" content="{e(meta_desc)}"/>
  <!-- ISSUE-032 FIX: news_keywords for Google News eligibility -->
  <meta name="news_keywords" content="{e(news_keywords)}"/>
  <!-- ISSUE-002/009/024/027 FIX: Pre-rendered @graph schema (JobPosting + BreadcrumbList + Organization + speakable) -->
  <script type="application/ld+json">{json.dumps(job_schema, ensure_ascii=False)}</script>
  {faq_schema_tag}
  <script>
    window.__TSJ_SLUG = {json.dumps(slug)};
    window.__TSJ_CANONICAL = {json.dumps(canon_url)};
    window.__TSJ_STATIC_PAGE = true;
    window.__TSJ_PSR_DISABLED = true;
    window.__TSJ_RENDERER_DISABLED = true;
    try {{
      if (window.location.pathname !== '/jobs/{slug}/') {{
        window.history.replaceState(null, '', '/jobs/{slug}/');
      }}
    }} catch(_) {{}}
  </script>
  <link rel="icon" type="image/x-icon" href="/image.ico"/>
  <link rel="stylesheet" href="/styles.css"/>
  <link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/>
  <noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>
  <link rel="manifest" href="/manifest.json"/>
  <meta name="theme-color" content="#0d2257"/>
  <script src="/analytics.js" defer></script>
  <style>{CARD_STYLE}</style>
</head>
<body>
  <div id="headerPlaceholder"></div>
  <script>
    fetch('/header.html',{{cache:'no-store'}}).then(function(r){{return r.ok?r.text():null;}}).catch(function(){{return null;}})
      .then(function(h){{if(h){{var d=document.getElementById('headerPlaceholder');if(d)d.outerHTML=h;}}}});
  </script>
  <main>
    <div class="jd-wrap">
      <nav class="jd-bc" aria-label="Breadcrumb">
        <a href="/">Home</a>
        <i class="fa-solid fa-chevron-right" style="font-size:.6rem;color:#d1d5db"></i>
        <a href="/section/latest-jobs/">{e(cat_label)}</a>
        <i class="fa-solid fa-chevron-right" style="font-size:.6rem;color:#d1d5db"></i>
        <span>{e(title[:60])}{'…' if len(title)>60 else ''}</span>
      </nav>
      <div class="notice-bar">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span><strong>Important:</strong> Apply only through official links. Always verify details on the official website before submitting your application.</span>
      </div>
      {header_html}
      {sections_html}
      <!-- ISSUE-026 FIX: E-E-A-T editorial block — Google E-E-A-T signal for government job portal -->
      <div class="job-card" style="margin-top:8px">
        <div style="font-size:.75rem;color:#64748b;padding:12px 14px;border-top:1px solid #e2e8f0;line-height:1.6">
          <strong>Editorial Note:</strong> This recruitment notification was verified and published by the
          <a href="/about/" rel="author" style="color:#1d4ed8">Top Sarkari Jobs Editorial Team</a>
          on <time datetime="{posted_date}">{posted_date}</time>.
          Always verify details from the official notification before applying.
          {f'<a href="{e(source_url)}" rel="nofollow noopener" target="_blank" style="color:#1d4ed8;margin-left:4px">View Official Notification ↗</a>' if source_url and not is_blocked(source_url) else ''}
        </div>
      </div>
    </div>
  </main>
  <div id="footerPlaceholder"></div>
  <script>
    fetch('/footer.html',{{cache:'no-store'}}).then(function(r){{return r.ok?r.text():null;}}).catch(function(){{return null;}})
      .then(function(h){{if(h){{var d=document.getElementById('footerPlaceholder');if(d)d.outerHTML=h;}}}});
  </script>
  <script src="/tsj-menu.js" defer></script>
  <!-- FAQ accordion init -->
  <script src="/faq-init.js" defer></script>
  <noscript>
    <div style="font-family:sans-serif;max-width:800px;margin:40px auto;padding:20px">
      <h1>{e(title)}</h1>
      <p>Organization: {e(org)}</p>
      <p>Vacancies: {e(vacancies)}</p>
      <p>Last Date: {e(last_date_r)}</p>
      <p>Apply Mode: {e(apply_mode)}</p>
      {f'<p>{e(short_info[:500])}</p>' if short_info else ''}
    </div>
  </noscript>
</body>
</html>"""

# ═══════════════════════════════════════
# MAIN PROCESSING
# ═══════════════════════════════════════
os.makedirs(DEST, exist_ok=True)

existing_json = set(os.listdir(DEST))
existing_dirs = set(d for d in os.listdir(JOBS_DIR)
                    if os.path.isdir(os.path.join(JOBS_DIR, d)) and d != 'data')

# Load existing index so it's cumulative — never lose old entries
if os.path.exists(INDEX):
    try:
        with open(INDEX, encoding='utf-8') as _f:
            index = json.load(_f)
        if not isinstance(index, dict):
            index = {}
    except Exception:
        index = {}
else:
    index = {}

new_files  = set()
new_dirs   = set()
written    = 0
skipped    = 0
seen_slugs = {}
# Pre-populate seen_slugs from existing index to prevent cross-run duplicates
for _existing_slug in index:
    seen_slugs[_existing_slug] = index[_existing_slug].get('cat', 'existing') \
        if isinstance(index[_existing_slug], dict) else 'existing'
redirects_new = []  # (from_path, to_path) for sr_ variants

if not os.path.exists(SRC):
    print(f"ERROR: {SRC} not found!")
    exit(1)

print(f"Loading {SRC}...")
with open(SRC, encoding='utf-8') as f:
    data = json.load(f)

# ISSUE-021 FIX: Pre-build related jobs index for internal linking
print("Building related jobs index...")
_fja_all = data.get('freejobalert_categories', {})
for _cat, _jobs in _fja_all.items():
    if not isinstance(_jobs, list): continue
    for _j in _jobs:
        _bd = _j.get('basic_details', {}) or {}
        _t = safe(_bd.get('job_title', ''))
        if not _t or not is_real_job(_t): continue
        _sl = slugify(_t)
        _st = safe(_j.get('state', ''))
        _q  = safe((_j.get('qualification') or {}).get('education_qualification', ''))[:30]
        _ALL_JOBS_FOR_RELATED.append((_sl, _t, _st, _q))
_sd_all = (data.get('sarkari_data', {}) or {}).get('jobs', [])
for _j in _sd_all:
    _t = safe(_j.get('title', ''))
    if not _t or not is_real_job(_t): continue
    _sl = clean_slug(safe(_j.get('slug', ''))) or slugify(_t)
    _st = safe(_j.get('state', ''))
    _q  = safe((_j.get('qualification') or {}).get('education_qualification', ''))[:30]
    _ALL_JOBS_FOR_RELATED.append((_sl, _t, _st, _q))
print(f"  Related jobs index: {len(_ALL_JOBS_FOR_RELATED)} entries")

# ── SOURCE 1: freejobalert_categories ──
fja = data.get('freejobalert_categories', {})
fja_count = 0
for cat, jobs in fja.items():
    if not isinstance(jobs, list): continue
    if cat not in VALID_CATS:
        continue
    for job in jobs:
        bd    = job.get('basic_details', {}) or {}
        title = safe(bd.get('job_title') or '')
        if not title: skipped += 1; continue
        # ISSUE-004 FIX: Skip yojana/scheme/non-recruitment entries
        if not is_real_job(title): skipped += 1; continue

        slug = slugify(title)
        if slug in seen_slugs:
            # dedup
            slug = f"{slug}-{cat.lower().replace('_','-')}"
        seen_slugs[slug] = cat
        job['category'] = cat

        fname = f"{slug}.json"
        with open(os.path.join(DEST, fname), 'w', encoding='utf-8') as f2:
            json.dump(job, f2, ensure_ascii=False, separators=(',',':'))
        new_files.add(fname)

        slug_dir = os.path.join(JOBS_DIR, slug)
        os.makedirs(slug_dir, exist_ok=True)
        html_path = os.path.join(slug_dir, 'index.html')
        if not os.path.exists(html_path):
            with open(html_path, 'w', encoding='utf-8') as f2:
                f2.write(build_static_html(slug, title, job, cat))
        new_dirs.add(slug)

        dates = job.get('important_dates', {}) or {}
        last_date = safe(dates.get('last_date_to_apply') or '')
        index[slug] = {'cat':cat,'title':title[:120],'last_date':last_date[:30]}
        written += 1; fja_count += 1

print(f"  freejobalert_categories: {fja_count} jobs")

# ── SOURCE 2: sarkari_data ──
sd = data.get('sarkari_data', {})
sd_jobs = sd.get('jobs', []) if isinstance(sd, dict) else []
sd_count = 0
for job in sd_jobs:
    raw_slug = safe(job.get('slug',''))
    title    = safe(job.get('title',''))
    if not title: continue
    # ISSUE-004 FIX: Skip yojana/scheme/non-recruitment entries
    if not is_real_job(title): continue

    slug = clean_slug(raw_slug) if raw_slug else slugify(title)
    if not slug: continue

    # Track sr_ redirect if original slug had prefix
    if raw_slug and raw_slug != slug:
        redirects_new.append((f'/jobs/{raw_slug}/', f'/jobs/{slug}/'))

    if slug in seen_slugs or slug in new_dirs:
        # Write redirect, skip page gen
        if raw_slug and raw_slug not in (slug, ''):
            redirects_new.append((f'/jobs/{raw_slug}/', f'/jobs/{slug}/'))
        continue

    seen_slugs[slug] = 'Latest_Notifications'

    imp_dates = job.get('important_dates') or {}
    if isinstance(imp_dates, str): imp_dates = {}
    raw_il = job.get('important_links') or {}
    useful = job.get('useful_links') or []
    if isinstance(useful, list) and useful and not raw_il:
        il_built = {}
        for lnk in useful:
            if not isinstance(lnk, dict): continue
            href = lnk.get('links') or lnk.get('url') or ''
            if isinstance(href, list): href = href[0] if href else ''
            href = str(href).strip()
            title_lnk = (lnk.get('title') or lnk.get('name') or '').lower()
            if not href.startswith('http'): continue
            if 'apply' in title_lnk: key = 'apply_online'
            elif 'notification' in title_lnk or 'pdf' in title_lnk: key = 'notification_pdf'
            elif 'result' in title_lnk: key = 'result_link'
            elif 'admit' in title_lnk: key = 'admit_card'
            elif 'answer' in title_lnk: key = 'answer_key'
            elif 'syllabus' in title_lnk: key = 'syllabus_pdf'
            elif 'official' in title_lnk or 'website' in title_lnk: key = 'official_website'
            else: key = 'click_here'
            if key in il_built:
                existing = il_built[key]
                il_built[key] = (existing if isinstance(existing, list) else [existing]) + [href]
            else:
                il_built[key] = href
        raw_il = il_built
    # Handle SR-format importantLinks (camelCase, array of {label, url})
    if isinstance(raw_il, list):
        il = raw_il  # pass list directly — render_important_links handles Format A
    elif isinstance(raw_il, dict):
        il = raw_il
        # Merge importantLinks array if present and dict is empty/minimal
        il_arr = job.get('importantLinks')
        if isinstance(il_arr, list) and il_arr:
            if not il:
                il = il_arr  # use array directly
            else:
                # Collect existing URLs to avoid duplicates
                existing_urls = set()
                for v in il.values():
                    for u in (v if isinstance(v, list) else [v]):
                        if str(u or '').startswith('http'): existing_urls.add(str(u).strip())
                extra = [item for item in il_arr
                         if isinstance(item, dict) and str(item.get('url','') or '').strip() not in existing_urls]
                if extra:
                    il.setdefault('structured_links', []).extend(
                        {'url': item['url'], 'label': item.get('label','Open Link')} for item in extra
                    )
    else:
        il = {}

    bd = {
        'job_title':        title,
        'organization_name': safe(job.get('organization') or job.get('board_name') or ''),
        'post_name':        safe(job.get('post_name') or ''),
        'total_vacancies':  safe(job.get('total_post') or job.get('total_vacancy') or ''),
        'application_mode': safe(job.get('apply_mode') or 'Online'),
        'job_location':     safe(job.get('job_location') or 'India'),
        'short_information':safe(job.get('short_information') or job.get('jobs_info') or ''),
        'last_updated':     safe(job.get('post_date') or job.get('listing_date') or ''),
    }
    full = dict(job)
    full['basic_details'] = bd
    full['important_dates'] = imp_dates
    full['important_links'] = il
    full['category'] = 'Latest_Notifications'
    full['slug'] = slug

    fname = f"{slug}.json"
    with open(os.path.join(DEST, fname), 'w', encoding='utf-8') as f2:
        json.dump(full, f2, ensure_ascii=False, separators=(',',':'))
    new_files.add(fname)

    slug_dir = os.path.join(JOBS_DIR, slug)
    os.makedirs(slug_dir, exist_ok=True)
    html_path = os.path.join(slug_dir, 'index.html')
    if not os.path.exists(html_path):
        with open(html_path, 'w', encoding='utf-8') as f2:
            f2.write(build_static_html(slug, title, full, 'Latest_Notifications'))
    new_dirs.add(slug)

    last_date = safe(imp_dates.get('last_date_to_apply') or imp_dates.get('last_date') or '')
    index[slug] = {'cat':'Latest_Notifications','title':title[:120],'last_date':last_date[:30]}
    written += 1; sd_count += 1

print(f"  sarkari_data: {sd_count} jobs")

# ── SOURCE 3: state_jobs ──
sj = data.get('state_jobs', {})
sj_sections = sj.get('sections', []) if isinstance(sj, dict) else []
sj_count = 0
for sec in sj_sections:
    state_name = safe(sec.get('state') or sec.get('title') or 'India')
    for item in sec.get('items', []):
        name = safe(item.get('name') or item.get('title') or '')
        if not name: continue
        raw_slug = safe(item.get('url','').rstrip('/').split('/')[-1] if '/' in item.get('url','') else '')
        slug = clean_slug(raw_slug) if raw_slug else slugify(name)
        if not slug or slug in seen_slugs or slug in new_dirs: continue

        detail = item.get('detail') or {}
        if isinstance(detail, str):
            try: detail = json.loads(detail)
            except: detail = {}

        bd_raw = detail.get('basic_details', {}) or {}
        dates_raw = detail.get('important_dates', {}) or {}
        if isinstance(bd_raw, str): bd_raw = {}
        if isinstance(dates_raw, str): dates_raw = {}

        bd = {
            'job_title':        name,
            'organization_name': safe(bd_raw.get('organization_name') or bd_raw.get('post_name') or ''),
            'post_name':        safe(bd_raw.get('post_name') or name),
            'total_vacancies':  safe(bd_raw.get('total_vacancies') or ''),
            'application_mode': safe(bd_raw.get('application_mode') or 'Online'),
            'job_location':     f"{state_name}, India",
            'short_information':safe(bd_raw.get('short_information') or ''),
            'last_updated':     safe(item.get('postDate') or item.get('date') or ''),
        }
        if not dates_raw:
            dates_raw = {
                'last_date_to_apply': safe(item.get('lastDate') or ''),
                'date_of_notification': safe(item.get('postDate') or ''),
            }

        full = dict(detail) if detail else {}
        full['basic_details'] = bd
        full['important_dates'] = dates_raw
        full['category'] = 'Latest_Notifications'
        full['slug'] = slug
        full['state'] = state_name
        full['source_url'] = safe(item.get('url') or '')

        seen_slugs[slug] = 'Latest_Notifications'
        fname = f"{slug}.json"
        with open(os.path.join(DEST, fname), 'w', encoding='utf-8') as f2:
            json.dump(full, f2, ensure_ascii=False, separators=(',',':'))
        new_files.add(fname)

        slug_dir = os.path.join(JOBS_DIR, slug)
        os.makedirs(slug_dir, exist_ok=True)
        html_path = os.path.join(slug_dir, 'index.html')
        if not os.path.exists(html_path):
            with open(html_path, 'w', encoding='utf-8') as f2:
                f2.write(build_static_html(slug, name, full, 'Latest_Notifications'))
        new_dirs.add(slug)

        last_date = safe(dates_raw.get('last_date_to_apply') or '')
        index[slug] = {'cat':'Latest_Notifications','title':name[:120],'last_date':last_date[:30]}
        written += 1; sj_count += 1

print(f"  state_jobs: {sj_count} jobs")

# ── Cleanup stale files — DISABLED ──
# JSON data files are NEVER auto-deleted — they back the permanent HTML pages.
preserved_json = existing_json - new_files

# HTML dirs are NEVER auto-deleted — pages accumulate permanently for SEO.
# Use the manual "delete-old-pages.yml" workflow if cleanup is ever needed.
preserved_dirs = existing_dirs - new_dirs

# ── Write jobs-index.json ──
with open(INDEX, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, separators=(',',':'))

# ── Append new sr_ redirects to _redirects ──
if redirects_new:
    existing_redir = open('_redirects', encoding='utf-8').read()
    new_rules = '\n'.join(f'{from_p}  {to_p}  301' for from_p, to_p in redirects_new
                          if from_p not in existing_redir)
    if new_rules:
        with open('_redirects', 'a', encoding='utf-8') as rf:
            rf.write(f'\n\n# Auto-generated sr_ slug redirects ({TODAY})\n')
            rf.write(new_rules + '\n')
        print(f"  _redirects: {len(redirects_new)} new sr_ redirect rules appended")

print(f"\n✅ DONE!")
print(f"  Total jobs written : {written}")
print(f"  JSON files preserved (not deleted) : {len(preserved_json)}")
print(f"  HTML dirs preserved (not deleted)  : {len(preserved_dirs)}")
print(f"  Index entries      : {len(index)}")
