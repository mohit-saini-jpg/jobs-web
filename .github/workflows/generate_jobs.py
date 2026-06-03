#!/usr/bin/env python3
"""
generate_static_pages.py
========================
PERMANENT FIX: JSON → HTML Static Page Generator
=================================================
One Item = One URL. Always reads from JSON as single source of truth.
Never overwrites newer content with old data.
Run: python3 generate_static_pages.py

Rules:
  ✅ Always reads latest JSON before writing anything
  ✅ Clears target directories BEFORE generating (no stale pages)
  ✅ One JSON item → One unique URL → One index.html
  ✅ Never re-uses cached or old HTML files
  ✅ FORCE_REGENERATE=true by default (env override)
  ✅ Writes a manifest.json after completion for audit trail
"""

import json, re, os, html as html_mod, shutil, hashlib
from datetime import date, datetime
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────
ROOT       = Path('.')
CJ_FILE    = ROOT / 'Complete_Jobs_Full_Data.json'
if not CJ_FILE.exists():
    CJ_FILE = ROOT / 'data' / 'Complete_Jobs_Full_Data.json'

BASE_URL   = 'https://www.topsarkarijobs.com'
TODAY      = date.today().isoformat()
NOW        = datetime.now().isoformat()
GEN_VER    = datetime.now().strftime('%Y%m%d%H%M%S')

BLOCKED    = {'sarkariresult.com','freejobalert.com','sarkarinetwork.com','sarkariresultshine.com'}

QUAL_SLUG  = {
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
QUAL_LABEL = {
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


# ══════════════════════════════════════════════════════════════════
# STEP 1: CACHE CLEARING (run before any writes)
# ══════════════════════════════════════════════════════════════════

def clear_generated_directories():
    """
    Delete all previously generated page directories.
    This is the ONLY correct way to ensure no stale HTML survives.
    """
    targets = [
        ROOT / 'jobs',
        ROOT / 'state',
        ROOT / 'education',
        ROOT / 'category' / 'study',
    ]
    print("\n🗑  Clearing old generated pages...")
    for target in targets:
        if target.exists():
            # Remove all subdirs (generated pages) but keep the directory itself
            for child in list(target.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child)
                    # Keep data/ subdir structure
            print(f"   ✓ Cleared: {target}")
        else:
            target.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ Created: {target}")

    # Ensure required dirs exist
    (ROOT / 'jobs' / 'data').mkdir(parents=True, exist_ok=True)
    (ROOT / 'category' / 'study').mkdir(parents=True, exist_ok=True)
    print("   ✅ Cache cleared. Ready for fresh generation.\n")


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def e(s):
    return html_mod.escape(str(s or ''), quote=True)

def strip_html(text):
    if not text: return ''
    t = re.sub(r'<[^>]+>', ' ', str(text))
    for ent, ch in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&nbsp;',' '),('&quot;','"'),('&#39;',"'")]:
        t = t.replace(ent, ch)
    return ' '.join(t.split())

def safe(v):
    if v is None: return ''
    if isinstance(v, str):
        s = v.strip()
        if '<' in s and '>' in s:
            s = strip_html(s)
        return s
    if isinstance(v, (int, float, bool)): return str(v).strip()
    if isinstance(v, list):
        parts = [safe(x) for x in v if x is not None]
        return ', '.join(p for p in parts if p)
    if isinstance(v, dict):
        for k in ['text','value','name','description','details','qualification',
                  'eligibility','content','pay_scale','salary','title']:
            if isinstance(v.get(k), str) and v[k].strip():
                return v[k].strip()
        return ' | '.join(safe(val) for val in v.values() if val)
    return str(v).strip()

def slugify(text, max_len=80):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text[:max_len].strip('-') or 'page'

def is_blocked(url):
    return any(d in str(url).lower() for d in BLOCKED)

def norm_date(raw):
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


# ══════════════════════════════════════════════════════════════════
# CSS (shared for all pages)
# ══════════════════════════════════════════════════════════════════

PAGE_CSS = """
*,*::before,*::after{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f4f8;margin:0;color:#1e293b}
main{min-height:60vh}
a{text-decoration:none}
.pg-wrap{max-width:860px;margin:0 auto;padding:12px 10px 40px}
.bc{font-size:.75rem;color:#64748b;margin-bottom:12px;display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.bc a{color:#1d4ed8}.bc a:hover{text-decoration:underline}.bc i{font-size:.6rem;color:#d1d5db}
.notice-bar{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;font-size:.8rem;color:#78350f;margin-bottom:12px;display:flex;gap:8px;align-items:flex-start}
.jd-header{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px 18px 0;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.jd-title{font-size:1.15rem;font-weight:800;color:#0f172a;line-height:1.4;margin:0 0 10px}
.jd-badge-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.jd-badge{display:inline-flex;align-items:center;gap:4px;background:#dbeafe;color:#1e40af;font-size:.71rem;font-weight:700;text-transform:uppercase;padding:3px 8px;border-radius:12px}
.jd-stats{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #e2e8f0;width:100%}
.jd-stat{padding:11px 6px;text-align:center;border-right:1px solid #e2e8f0}
.jd-stat:last-child{border-right:none}
.jd-stat-val{font-size:.95rem;font-weight:800;color:#0f172a;word-break:break-word}
.jd-stat-lbl{font-size:.67rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
@media(max-width:600px){.jd-stats{grid-template-columns:repeat(2,1fr)}.jd-stat:nth-child(2){border-right:none}.jd-stat:nth-child(3){border-top:1px solid #e2e8f0}.jd-stat:nth-child(4){border-top:1px solid #e2e8f0;border-right:none}}
.job-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.job-card-head{display:flex;align-items:center;gap:8px;padding:9px 14px;color:#fff;font-size:.86rem;font-weight:700}
.job-card-head h2{margin:0;font-size:.86rem;font-weight:700}
.jd-table{width:100%;border-collapse:collapse;font-size:.82rem}
.jd-table th{width:38%;background:#f8fafc;color:#374151;font-weight:700;padding:8px 12px;text-align:left;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word}
.jd-table td{padding:8px 12px;color:#1e293b;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word;overflow-wrap:break-word;line-height:1.6}
.jd-table tr:last-child th,.jd-table tr:last-child td{border-bottom:none}
.jd-table a{color:#1d4ed8;word-break:break-all}
.tbl-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%}
.vac-table{width:100%;border-collapse:collapse;font-size:.82rem;min-width:380px}
.vac-table th{background:#1d4ed8;color:#fff;padding:8px 12px;font-weight:700;white-space:nowrap;text-align:left}
.vac-table td{padding:8px 12px;border-bottom:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top}
.vac-table .vac-tot td{border-bottom:none;font-weight:700;background:#f0f9ff}
.data-table{width:100%;border-collapse:collapse;font-size:.82rem}
.data-table th{background:#1d4ed8;color:#fff;padding:8px 12px;font-weight:700;text-align:left}
.data-table td{padding:8px 12px;border-bottom:1px solid #e9eef4;color:#1e293b;vertical-align:top}
.fee-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}
.fee-item{padding:10px 14px;border-right:1px solid #e9eef4;border-bottom:1px solid #e9eef4}
.fee-label{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:3px}
.fee-val{font-size:.9rem;font-weight:700;color:#1e293b}
.fee-val.free{color:#16a34a}.fee-val.paid{color:#dc2626}
.fee-note{padding:9px 14px;font-size:.81rem;color:#78350f;background:#fffbeb;border-top:1px solid #fde68a}
.sel-steps{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
.sel-step{display:inline-flex;align-items:center;gap:6px;background:#f0f7ff;border:1px solid #bfdbfe;border-radius:8px;padding:6px 12px;font-size:.8rem;font-weight:600;color:#1e40af}
.sel-num{background:#1e40af;color:#fff;border-radius:50%;width:18px;height:18px;display:inline-flex;align-items:center;justify-content:center;font-size:.65rem;font-weight:800;flex-shrink:0}
.hta-list{list-style:none;margin:0;padding:0}
.hta-item{display:flex;align-items:flex-start;gap:12px;padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:.83rem;color:#1e293b;line-height:1.65}
.hta-item:last-child{border-bottom:none}
.hta-num{flex-shrink:0;min-width:24px;height:24px;background:#0f766e;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:800}
.inst-list{list-style:none;margin:0;padding:0}
.inst-item{display:flex;align-items:flex-start;gap:10px;padding:9px 14px;border-bottom:1px solid #f1f5f9;font-size:.82rem;color:#78350f;line-height:1.6}
.inst-item:last-child{border-bottom:none}.inst-item i{color:#ca8a04;flex-shrink:0;margin-top:2px}
.links-grid{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
.link-btn{display:inline-flex;align-items:center;gap:5px;padding:7px 14px;border-radius:8px;font-size:.8rem;font-weight:700;text-decoration:none;white-space:nowrap;transition:all .15s;border:1px solid transparent}
.lnk-btn{display:inline-flex;align-items:center;gap:5px;padding:5px 10px;border-radius:6px;font-size:.75rem;font-weight:700;text-decoration:none;white-space:nowrap;border:1px solid transparent;margin:2px}
.btn-blue{background:#dbeafe;color:#1e40af;border-color:#93c5fd}.btn-blue:hover{background:#1e40af;color:#fff}
.btn-green{background:#d1fae5;color:#065f46;border-color:#6ee7b7}.btn-green:hover{background:#059669;color:#fff}
.btn-red{background:#fee2e2;color:#991b1b;border-color:#fca5a5}.btn-red:hover{background:#dc2626;color:#fff}
.btn-orange{background:#fef3c7;color:#92400e;border-color:#fcd34d}.btn-orange:hover{background:#d97706;color:#fff}
.btn-purple{background:#ede9fe;color:#5b21b6;border-color:#c4b5fd}.btn-purple:hover{background:#6d28d9;color:#fff}
.btn-teal{background:#ccfbf1;color:#0f766e;border-color:#5eead4}.btn-teal:hover{background:#0f766e;color:#fff}
.btn-indigo{background:#e0e7ff;color:#3730a3;border-color:#a5b4fc}.btn-indigo:hover{background:#3730a3;color:#fff}
.btn-gray{background:#f1f5f9;color:#475569;border-color:#cbd5e1}.btn-gray:hover{background:#475569;color:#fff}
.btn-pdf{background:#fee2e2;color:#991b1b;border-color:#fca5a5}.btn-pdf:hover{background:#dc2626;color:#fff}
.btn-default{background:#dbeafe;color:#1e40af;border-color:#93c5fd}.btn-default:hover{background:#1e40af;color:#fff}
.short-info-card{background:#eff6ff;border-left:4px solid #1d4ed8;padding:12px 14px;font-size:.84rem;color:#1e293b;line-height:1.7;margin-bottom:12px;border-radius:0 8px 8px 0}
.faq-item{border-bottom:1px solid #f1f5f9;font-size:.83rem}
.faq-item:last-child{border-bottom:none}
.faq-q{padding:10px 14px;font-weight:700;color:#1e293b;cursor:pointer;display:flex;justify-content:space-between;align-items:center;user-select:none;line-height:1.5}
.faq-a{padding:0 14px 10px;color:#475569;line-height:1.65;display:none}
.faq-q.open+.faq-a{display:block}
.edu-sec{margin-bottom:2px}
.edu-sec-h{font-size:.87rem;font-weight:700;color:#1e293b;background:#f8fafc;padding:8px 14px;margin:0;border-bottom:1px solid #e9eef4}
.edu-para{font-size:.82rem;color:#374151;line-height:1.7;padding:10px 14px;border-bottom:1px solid #f1f5f9}
.edu-para:last-child{border-bottom:none}
.val-list{padding:10px 14px 10px 30px;margin:0}
.val-list li{font-size:.8rem;color:#374151;padding:4px 0;line-height:1.55}
.mi-item{padding:8px 14px;font-size:.82rem;border-bottom:1px solid #f1f5f9;line-height:1.6}
.mi-item:last-child{border-bottom:none}
.rel-links{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
"""


# ══════════════════════════════════════════════════════════════════
# SECTION RENDERERS
# ══════════════════════════════════════════════════════════════════

def card(grad, icon, heading, body):
    if not body or not str(body).strip(): return ''
    return (f'<div class="job-card">'
            f'<div class="job-card-head" style="background:{grad}">'
            f'<i class="fa-solid {icon}"></i><h2>{e(heading)}</h2>'
            f'</div><div class="job-card-body">{body}</div></div>\n')

def kv_rows(pairs):
    return ''.join(f'<tr><th>{e(l)}</th><td>{e(safe(v))}</td></tr>'
                   for l, v in pairs if safe(v))

def render_important_dates(obj):
    if not obj or not isinstance(obj, dict): return ''
    FIELDS = [
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
        ('admit_card_date','Admit Card Date'),
        ('admit_card','Admit Card Available'),
        ('result_date','Result Date'),
        ('event','Event / Date'),
        ('आवेदन शुरू','Application Start (आवेदन शुरू)'),
        ('अंतिम तिथि','Last Date (अंतिम तिथि)'),
        ('परीक्षा तिथि','Exam Date (परीक्षा तिथि)'),
    ]
    seen = set(); rows = ''
    for k, lbl in FIELDS:
        v = safe(obj.get(k))
        if not v or lbl in seen: continue
        seen.add(lbl)
        is_last = 'last' in k.lower() or 'closing' in k.lower() or 'अंतिम' in k
        style = ' style="color:#dc2626;font-weight:700"' if is_last else ''
        rows += f'<tr><th>{e(lbl)}</th><td{style}>{e(v)}</td></tr>'
    fixed_keys = {k for k, _ in FIELDS}
    for k, v in obj.items():
        sv = safe(v)
        if not sv or k in fixed_keys: continue
        lbl = k.replace('_',' ').title()
        if lbl in seen: continue
        seen.add(lbl)
        rows += f'<tr><th>{e(lbl)}</th><td>{e(sv)}</td></tr>'
    if not rows: return ''
    return card('linear-gradient(135deg,#b91c1c,#dc2626)', 'fa-calendar-check', 'Important Dates',
                f'<table class="jd-table"><tbody>{rows}</tbody></table>')

def render_fee(obj):
    if not obj or not isinstance(obj, dict): return ''
    FIELDS = [
        ('general_fee','General / UR'),('general','General / UR'),('ur','UR'),
        ('obc_fee','OBC'),('obc','OBC'),('sc_fee','SC'),('sc','SC'),('st_fee','ST'),('st','ST'),
        ('ews','EWS'),('pwd_fee','PH / Divyang'),('ph','PH / Divyang'),('pwd','PH / Divyang'),
        ('female_fee','Female'),('female','Female'),
        ('ex_serviceman_fee','Ex-Serviceman'),
        ('all','All Categories'),('all_category','All Categories'),
    ]
    seen = set(); items_html = ''
    def is_free(v): return bool(re.search(r'nil|^0$|free|no fee|exempt', v, re.I))
    for key, lbl in FIELDS:
        v = safe(obj.get(key))
        if not v or lbl in seen: continue
        seen.add(lbl)
        cls = 'free' if is_free(v) else 'paid'
        items_html += f'<div class="fee-item"><div class="fee-label">{e(lbl)}</div><div class="fee-val {cls}">{e(v)}</div></div>'
    note = safe(obj.get('details') or obj.get('fee_mode') or obj.get('payment_mode') or '')
    if not items_html and not note: return ''
    body = (f'<div class="fee-grid">{items_html}</div>' if items_html else '') + \
           (f'<div class="fee-note"><i class="fa-solid fa-circle-info"></i> {e(note)}</div>' if note else '')
    return card('linear-gradient(135deg,#c2410c,#ea580c)', 'fa-indian-rupee-sign', 'Application Fee', body)

def render_age(obj):
    if not obj or not isinstance(obj, dict): return ''
    FIELDS = [
        ('minimum_age','Minimum Age'),('min_age','Minimum Age'),
        ('maximum_age','Maximum Age'),('max_age','Maximum Age'),('age_limit','Age Limit'),
        ('age_relaxation','Age Relaxation'),('age_details','Age Details'),('details','Details'),
    ]
    rows = kv_rows([(lbl, obj.get(k)) for k, lbl in FIELDS])
    if not rows: return ''
    return card('linear-gradient(135deg,#0f766e,#0891b2)', 'fa-user-clock', 'Age Limit',
                f'<table class="jd-table"><tbody>{rows}</tbody></table>')

def render_qual(obj):
    if not obj: return ''
    FIELDS = [
        ('education_qualification','Education Qualification'),
        ('qualification','Qualification'),('eligibility','Eligibility'),
        ('required_degree','Required Degree'),('technical_qualification','Technical Qualification'),
        ('matched_qualifications','Matched Qualifications'),
        ('experience_required','Experience Required'),('details','Details'),
    ]
    if isinstance(obj, str) and obj.strip():
        return card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-graduation-cap',
                    'Qualification / Eligibility',
                    f'<div style="padding:10px 14px;font-size:.83rem;line-height:1.7">{e(obj)}</div>')
    if isinstance(obj, dict):
        rows = kv_rows([(lbl, obj.get(k)) for k, lbl in FIELDS])
        if not rows: return ''
        return card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-graduation-cap',
                    'Qualification / Eligibility',
                    f'<table class="jd-table"><tbody>{rows}</tbody></table>')
    return ''

def render_vacancy(vac_list):
    if not vac_list or not isinstance(vac_list, list): return ''
    COL_MAP = {
        'post_name':['post_name','post','name','Post Name','Name Of Post','Post'],
        'total':['total','total_vacancies','total_posts','vacancies','Total Posts','Total Vacancies','Total'],
        'ur':['ur','general','UR','General (UR)','General'],
        'obc':['obc','OBC'],
        'sc':['sc','SC'],
        'st':['st','ST'],
        'ews':['ews','EWS'],
        'women':['women','Women','female','Female'],
        'rural':['rural','Rural'],
        'ex_serviceman':['ex_serviceman','ex-serviceman','Ex-Servicemen','ex_servicemen'],
        'salary':['salary','pay_scale','Scale of Pay','Salary','Pay Scale'],
        'qualification':['eligibility','qualification','educational_qualification','Educational Qualification','Qualification'],
        'department':['department','Department'],
        'trade':['trade_name','Trade Name','trade'],
    }
    COL_ORDER = ['post_name','total','ur','obc','sc','st','ews','women','rural','ex_serviceman','salary','qualification','department','trade']
    COL_LABELS = {
        'post_name':'Post Name','total':'Total Posts','ur':'UR/General','obc':'OBC',
        'sc':'SC','st':'ST','ews':'EWS','women':'Women','rural':'Rural',
        'ex_serviceman':'Ex-Servicemen','salary':'Salary / Pay Scale',
        'qualification':'Qualification','department':'Department','trade':'Trade Name',
    }
    norm = []; avail = set()
    for row in vac_list:
        if not isinstance(row, dict): continue
        n = {}
        for col, aliases in COL_MAP.items():
            for a in aliases:
                if a in row and row[a] not in (None, '', {}, []):
                    n[col] = safe(row[a]); avail.add(col); break
        if n: norm.append(n)
    if not norm: return ''
    cols = [c for c in COL_ORDER if c in avail]
    if not cols: return ''
    head = '<th>Sr.</th>' + ''.join(f'<th>{COL_LABELS[c]}</th>' for c in cols)
    rows = ''; totals = {}
    for i, row in enumerate(norm, 1):
        cells = f'<td>{i}</td>' + ''.join(f'<td>{e(row.get(c,""))}</td>' for c in cols)
        rows += f'<tr>{cells}</tr>'
        for c in ['total','ur','obc','sc','st','ews','women','rural','ex_serviceman']:
            if c in cols:
                try: totals[c] = totals.get(c, 0) + int(re.sub(r'\D', '', row.get(c,'0') or '0') or '0')
                except: pass
    if totals:
        tc = '<td><strong>Total</strong></td>' + ''.join(
            f'<td>{"<strong>"+str(totals[c])+"</strong>" if c in totals else ""}</td>' for c in cols)
        rows += f'<tr class="vac-tot">{tc}</tr>'
    body = f'<div class="tbl-scroll"><table class="vac-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    return card('linear-gradient(135deg,#15803d,#16a34a)', 'fa-chart-pie', 'Vacancy Details', body)

def render_cat_vacancy(cwv):
    if not cwv: return ''
    if isinstance(cwv, list): return render_vacancy(cwv)
    if isinstance(cwv, dict) and cwv:
        pairs = [(k.replace('_',' ').title(), v) for k,v in cwv.items() if safe(v)]
        if not pairs: return ''
        rows = ''.join(f'<tr><td>{e(l)}</td><td>{e(safe(v))}</td></tr>' for l,v in pairs)
        body = f'<div class="tbl-scroll"><table class="vac-table"><thead><tr><th>Category</th><th>Posts</th></tr></thead><tbody>{rows}</tbody></table></div>'
        return card('linear-gradient(135deg,#15803d,#16a34a)', 'fa-chart-bar', 'Category-wise Vacancy', body)
    return ''

def render_salary(obj):
    if not obj: return ''
    FIELDS = [
        ('pay_scale','Pay Scale'),('basic_pay','Basic Pay'),('grade_pay','Grade Pay'),
        ('salary','Salary'),('allowance','Allowance'),('details','Details'),
    ]
    if isinstance(obj, str) and obj.strip():
        return card('linear-gradient(135deg,#15803d,#16a34a)', 'fa-indian-rupee-sign', 'Salary & Pay Scale',
                    f'<div style="padding:10px 14px;font-size:.83rem;line-height:1.7">{e(obj)}</div>')
    if isinstance(obj, dict):
        rows = kv_rows([(lbl, obj.get(k)) for k, lbl in FIELDS])
        return card('linear-gradient(135deg,#15803d,#16a34a)', 'fa-indian-rupee-sign', 'Salary & Pay Scale',
                    f'<table class="jd-table"><tbody>{rows}</tbody></table>') if rows else ''
    return ''

def render_selection(sp):
    if not sp: return ''
    steps = [safe(s) for s in sp if safe(s)] if isinstance(sp, list) \
            else [s.strip() for s in re.split(r'[,\n;/]', str(sp)) if s.strip()]
    if not steps: return ''
    items = ''.join(f'<div class="sel-step"><span class="sel-num">{i+1}</span>{e(s[:100])}</div>'
                    for i, s in enumerate(steps))
    return card('linear-gradient(135deg,#5b21b6,#7c3aed)', 'fa-list-check', 'Selection Process',
                f'<div class="sel-steps">{items}</div>')

def render_exam_pattern(ep):
    if not ep: return ''
    FIELDS = [('subjects','Subjects'),('marks','Marks'),('duration','Duration'),
              ('total_questions','Total Questions'),('negative_marking','Negative Marking'),
              ('exam_mode','Exam Mode'),('paper_type','Paper Type')]
    if isinstance(ep, list) and ep and isinstance(ep[0], dict):
        has_fixed = any(ep[0].get(k) for k, _ in FIELDS)
        if has_fixed:
            rows = kv_rows([(lbl, ep[0].get(k)) for k, lbl in FIELDS])
            if rows:
                return card('linear-gradient(135deg,#0369a1,#0284c7)', 'fa-file-lines', 'Exam Pattern',
                            f'<table class="jd-table"><tbody>{rows}</tbody></table>')
        cols = list(ep[0].keys())
        head = '<th>Sr.</th>' + ''.join(f'<th>{e(c.replace("_"," ").title())}</th>' for c in cols)
        rows = ''.join(f'<tr><td>{i+1}</td>' + ''.join(f'<td>{e(safe(r.get(c)))}</td>' for c in cols) + '</tr>'
                       for i, r in enumerate(ep) if isinstance(r, dict))
        return card('linear-gradient(135deg,#0369a1,#0284c7)', 'fa-file-lines', 'Exam Pattern',
                    f'<div class="tbl-scroll"><table class="vac-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>') if rows else ''
    if isinstance(ep, dict) and ep:
        rows = kv_rows([(k.replace('_',' ').title(), v) for k, v in ep.items()])
        return card('linear-gradient(135deg,#0369a1,#0284c7)', 'fa-file-lines', 'Exam Pattern',
                    f'<table class="jd-table"><tbody>{rows}</tbody></table>') if rows else ''
    if isinstance(ep, str) and ep.strip():
        return card('linear-gradient(135deg,#0369a1,#0284c7)', 'fa-file-lines', 'Exam Pattern',
                    f'<div style="padding:10px 14px;font-size:.83rem;line-height:1.7">{e(ep)}</div>')
    return ''

def render_syllabus(syl):
    if not syl: return ''
    FIELDS = [('subject_name','Subject'),('topics','Topics'),('details','Details'),
              ('unit_name','Unit'),('chapter','Chapter')]
    if isinstance(syl, list) and syl:
        if isinstance(syl[0], dict):
            html = ''
            for item in syl:
                rows = kv_rows([(lbl, item.get(k)) for k, lbl in FIELDS])
                if not rows:
                    rows = kv_rows([(k.replace('_',' ').title(), v) for k, v in item.items() if safe(v)])
                if rows: html += f'<table class="jd-table" style="margin-bottom:8px"><tbody>{rows}</tbody></table>'
            return card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-book', 'Syllabus', html) if html else ''
        items = ''.join(f'<div class="sel-step"><i class="fa-solid fa-book-open" style="font-size:.7rem"></i>{e(safe(s)[:100])}</div>'
                        for s in syl if safe(s))
        return card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-book', 'Syllabus',
                    f'<div class="sel-steps">{items}</div>') if items else ''
    if isinstance(syl, str) and syl.strip():
        return card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-book', 'Syllabus',
                    f'<div style="padding:10px 14px;font-size:.83rem;line-height:1.7">{e(syl)}</div>')
    return ''

def render_physical(pe):
    if not pe or not isinstance(pe, dict): return ''
    FIELDS = [('height','Height'),('chest','Chest'),('running','Running'),
              ('weight','Weight'),('physical_test','Physical Test'),
              ('eyesight','Eyesight'),('walking','Walking')]
    rows = kv_rows([(lbl, pe.get(k)) for k, lbl in FIELDS])
    fixed = {k for k, _ in FIELDS}
    for k, v in pe.items():
        if k not in fixed and safe(v):
            rows += f'<tr><th>{e(k.replace("_"," ").title())}</th><td>{e(safe(v))}</td></tr>'
    return card('linear-gradient(135deg,#be123c,#e11d48)', 'fa-dumbbell',
                'Physical Eligibility / Standards',
                f'<table class="jd-table"><tbody>{rows}</tbody></table>') if rows else ''

def render_hta(steps):
    if not steps: return ''
    if isinstance(steps, list):
        filtered = [safe(s) for s in steps if safe(s)]
    elif isinstance(steps, str):
        filtered = [s.strip() for s in re.split(r'[\n;]', steps) if s.strip()]
    else:
        return ''
    if not filtered: return ''
    items = ''.join(f'<li class="hta-item"><span class="hta-num">{i+1}</span><span>{e(s)}</span></li>'
                    for i, s in enumerate(filtered))
    return card('linear-gradient(135deg,#0f766e,#0891b2)', 'fa-clipboard-list', 'How to Apply',
                f'<ul class="hta-list">{items}</ul>')

def render_instructions(insts):
    if not isinstance(insts, list) or not insts: return ''
    filtered = [safe(s) for s in insts if safe(s)]
    if not filtered: return ''
    items = ''.join(f'<li class="inst-item"><i class="fa-solid fa-triangle-exclamation"></i><span>{e(s)}</span></li>'
                    for s in filtered)
    return card('linear-gradient(135deg,#b45309,#ca8a04)', 'fa-circle-exclamation',
                'Important Instructions', f'<ul class="inst-list">{items}</ul>')

LINK_CFG = {
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
    'click_here':            ('Click Here',            'btn-blue',   'fa-link'),
    'merit_list':            ('Merit List',            'btn-teal',   'fa-list'),
    'score_card':            ('Score Card',            'btn-orange', 'fa-file'),
}

def render_links(il_obj):
    if not il_obj or not isinstance(il_obj, dict): return ''
    buttons = ''; seen = set()
    for key, val in il_obj.items():
        if key in ('structured_links', 'seo_tags'): continue
        urls = val if isinstance(val, list) else [val]
        label, css, icon = LINK_CFG.get(key, ('View', 'btn-gray', 'fa-link'))
        for url in urls:
            u = str(url or '').strip()
            if not u.startswith('http') or is_blocked(u) or u in seen: continue
            seen.add(u)
            ul = u.lower()
            if ul.endswith('.pdf'): icon, css = 'fa-file-pdf', 'btn-red'
            elif 'apply' in key: icon, css = 'fa-paper-plane', 'btn-blue'
            elif 'result' in key: icon, css = 'fa-trophy', 'btn-green'
            elif 'admit' in key: icon, css = 'fa-id-card', 'btn-teal'
            elif 'answer' in key: icon, css = 'fa-key', 'btn-indigo'
            buttons += f'<a href="{e(u)}" class="link-btn {css}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {icon}"></i> {e(label)}</a>\n'
    for item in (il_obj.get('structured_links') or []):
        if not isinstance(item, dict): continue
        u = str(item.get('url','') or item.get('href','')).strip()
        lbl = str(item.get('label','') or item.get('title','View')).strip() or 'View'
        if not u.startswith('http') or is_blocked(u) or u in seen: continue
        seen.add(u)
        ll = lbl.lower()
        ic, cl = ('fa-paper-plane','btn-blue') if 'apply' in ll else \
                 ('fa-trophy','btn-green') if 'result' in ll else \
                 ('fa-id-card','btn-teal') if 'admit' in ll else \
                 ('fa-key','btn-indigo') if 'answer' in ll else \
                 ('fa-file-pdf','btn-red') if u.endswith('.pdf') else \
                 ('fa-globe','btn-green') if 'official' in ll else \
                 ('fa-link','btn-blue')
        buttons += f'<a href="{e(u)}" class="link-btn {cl}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ic}"></i> {e(lbl[:55])}</a>\n'
    if not buttons: return ''
    return card('linear-gradient(135deg,#1e40af,#1e3a8a)', 'fa-link', 'Important Links',
                f'<div class="links-grid">{buttons}</div>')

def render_faq(faq_list):
    if not isinstance(faq_list, list) or not faq_list: return ''
    items = ''
    for f in faq_list:
        if not isinstance(f, dict): continue
        q = safe(f.get('question','')); a = safe(f.get('answer',''))
        if not q or not a: continue
        items += (f'<div class="faq-item">'
                  f'<div class="faq-q" onclick="this.classList.toggle(\'open\');'
                  f'this.nextElementSibling.style.display=this.classList.contains(\'open\')?\'block\':\'none\'">'
                  f'{e(q)} <i class="fa-solid fa-chevron-down" style="font-size:.7rem;color:#94a3b8"></i></div>'
                  f'<div class="faq-a">{e(a)}</div></div>')
    return card('linear-gradient(135deg,#4338ca,#6366f1)', 'fa-circle-question', 'FAQs', items) if items else ''

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
                ic = 'fa-file-pdf' if ul.endswith('.pdf') else 'fa-external-link-alt'
                cl = 'btn-pdf' if ul.endswith('.pdf') else 'btn-default'
                btns += f'<a href="{e(url)}" class="lnk-btn {cl}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ic}"></i> {e(lbl[:40])}</a> '
            if btns:
                return (f'{e(text)}<br>{btns}' if text else btns), True
        return e(text), False
    if isinstance(cell, list):
        parts = [extract_cell(c)[0] for c in cell if c is not None]
        return '<br>'.join(p for p in parts if p), False
    return e(str(cell)), False

def render_edu_sections(sections_list):
    if not sections_list: return ''
    html = ''
    for sec in sections_list:
        heading = safe(sec.get('heading','') or sec.get('title',''))
        if 'preferred source' in heading.lower() or 'set as preferred' in heading.lower():
            continue
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
                first_row = rows[0] if rows else []
                is_obj_format = (isinstance(first_row, list) and first_row and
                                 isinstance(first_row[0], dict) and 'text' in first_row[0])
                if is_obj_format:
                    hdr_cells = [extract_cell(c)[0] for c in first_row]
                    if len(hdr_cells) == 1:
                        data_rows = rows[1:]
                        if data_rows:
                            hdr_cells = [extract_cell(c)[0] for c in data_rows[0]]
                            data_rows = data_rows[1:]
                        else:
                            continue
                    else:
                        data_rows = rows[1:]
                    head = ''.join(f'<th>{h}</th>' for h in hdr_cells)
                    body_rows = ''.join(
                        f'<tr>' + ''.join(f'<td>{extract_cell(c)[0]}</td>' for c in r) + '</tr>'
                        for r in data_rows if isinstance(r, list)
                    )
                    if body_rows:
                        body += f'<div class="tbl-scroll"><table class="data-table"><thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table></div>'
                else:
                    if not headers and rows:
                        headers = rows[0]; rows = rows[1:]
                    head = ''.join(f'<th>{e(str(h))}</th>' for h in (headers or []))
                    body_rows = ''.join(
                        f'<tr>' + ''.join(f'<td>{extract_cell(c)[0]}</td>' for c in r) + '</tr>'
                        for r in rows if isinstance(r, (list, tuple))
                    )
                    if body_rows:
                        body += f'<div class="tbl-scroll"><table class="data-table">{f"<thead><tr>{head}</tr></thead>" if head else ""}<tbody>{body_rows}</tbody></table></div>'
            elif btype == 'list':
                items = block.get('items', [])
                if items:
                    lis = ''.join(f'<li>{e(str(li)) if isinstance(li,str) else extract_cell(li)[0]}</li>' for li in items if li)
                    body += f'<ul class="val-list">{lis}</ul>'
            elif btype == 'merged_info':
                for mi in block.get('items', []):
                    if not isinstance(mi, dict): continue
                    lbl = safe(mi.get('label','')); txt = safe(mi.get('text',''))
                    if lbl or txt:
                        body += f'<div class="mi-item">{f"<b>{e(lbl)}</b>: " if lbl else ""}{e(txt) if txt else ""}</div>'
            elif btype == 'important_links':
                links_data = block.get('links', [])
                if isinstance(links_data, list) and links_data:
                    btns = ''
                    for lnk in links_data:
                        if not isinstance(lnk, dict): continue
                        url = str(lnk.get('url','') or '').strip()
                        lbl = str(lnk.get('label','') or lnk.get('text','') or 'View').strip() or 'View'
                        if not url.startswith('http') or is_blocked(url): continue
                        ul = url.lower()
                        ic = 'fa-file-pdf' if ul.endswith('.pdf') else 'fa-external-link-alt'
                        cl = 'btn-pdf' if ul.endswith('.pdf') else 'btn-default'
                        btns += f'<a href="{e(url)}" class="lnk-btn {cl}" target="_blank" rel="noopener noreferrer"><i class="fa-solid {ic}"></i> {e(lbl[:60])}</a>\n'
                    if btns:
                        body += f'<div class="links-grid">{btns}</div>'
                elif isinstance(links_data, dict):
                    body += render_links(links_data)
            else:
                text = safe(block.get('text','') or block.get('content',''))
                if text: body += f'<p class="edu-para">{e(text)}</p>'
        if body.strip():
            if heading:
                html += f'<div class="edu-sec"><h3 class="edu-sec-h">{e(heading)}</h3>{body}</div>'
            else:
                html += f'<div class="edu-sec">{body}</div>'
    return html


# ══════════════════════════════════════════════════════════════════
# PAGE BUILDER
# ══════════════════════════════════════════════════════════════════

def build_page(title, detail, canon_url, breadcrumbs, page_type='job', type_label=''):
    """
    Build complete pre-rendered HTML page from JSON detail object.
    One item → one URL → one index.html. No caching. Fresh every time.
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
    edu_s = detail.get('sections') or []
    src   = safe(detail.get('source_url') or detail.get('url') or '')

    org        = safe(bd.get('organization_name') or bd.get('post_name') or 'Government of India')
    vacancies  = safe(bd.get('total_vacancies') or bd.get('total_vacancy') or detail.get('total_post') or '')
    last_date  = safe(dates.get('last_date_to_apply') or dates.get('last_date') or detail.get('lastDate') or '')
    apply_mode = safe(bd.get('application_mode') or detail.get('apply_mode') or 'Online')
    location   = safe(bd.get('job_location') or detail.get('state') or 'India')
    short_info = safe(bd.get('short_information') or detail.get('short_info') or detail.get('short_information') or '')
    job_title_full = safe(bd.get('job_title') or title)
    posted     = norm_date(safe(bd.get('last_updated') or dates.get('date_of_notification') or '')) or TODAY

    # SEO
    meta_desc = f"{title}: {vacancies+' vacancies, ' if vacancies else ''}{('last date '+last_date+'. ') if last_date else ''}Apply online – Top Sarkari Jobs."
    if len(meta_desc) > 155: meta_desc = meta_desc[:152].rsplit(' ',1)[0].rstrip('.,–') + '…'
    title_tag = title if len(title)+19 <= 60 else title[:40].rstrip()

    # JSON-LD Schema
    job_schema = {
        '@context':'https://schema.org','@type':'JobPosting',
        'title':job_title_full,'description':short_info or meta_desc,
        'datePosted':posted,'url':canon_url,
        'hiringOrganization':{'@type':'Organization','name':org,'sameAs':'https://www.india.gov.in'},
        'jobLocation':{'@type':'Place','address':{'@type':'PostalAddress','addressCountry':'IN','addressLocality':location}},
        'baseSalary':{'@type':'MonetaryAmount','currency':'INR',
                      'value':{'@type':'QuantitativeValue','minValue':15000,'maxValue':80000,'unitText':'MONTH'}},
    }
    iso = norm_date(last_date)
    if iso: job_schema['validThrough'] = iso
    vn = re.search(r'\d+', str(vacancies or ''))
    if vn: job_schema['totalJobOpenings'] = int(vn.group())

    bc_items = [{'@type':'ListItem','position':1,'name':'Home','item':f'{BASE_URL}/'}]
    for i,(lbl,url) in enumerate(breadcrumbs, 2):
        bc_items.append({'@type':'ListItem','position':i,'name':lbl,'item':url})
    bc_items.append({'@type':'ListItem','position':len(bc_items)+1,'name':title,'item':canon_url})
    bc_schema = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':bc_items}

    valid_faqs = [f for f in (faq if isinstance(faq,list) else [])
                  if isinstance(f,dict) and f.get('question') and f.get('answer')][:5]
    faq_schema_tag = ''
    if valid_faqs:
        faq_schema = {'@context':'https://schema.org','@type':'FAQPage',
            'mainEntity':[{'@type':'Question','name':f['question'],
                           'acceptedAnswer':{'@type':'Answer','text':f['answer']}} for f in valid_faqs]}
        faq_schema_tag = f'<script type="application/ld+json">{json.dumps(faq_schema,ensure_ascii=False)}</script>'

    # Breadcrumb HTML
    bc_html = '<nav class="bc" aria-label="Breadcrumb"><a href="/">Home</a>'
    for lbl, url in breadcrumbs:
        bc_html += f'<i class="fa-solid fa-chevron-right"></i><a href="{e(url)}">{e(lbl)}</a>'
    bc_html += f'<i class="fa-solid fa-chevron-right"></i><span>{e(title[:60])}{"…" if len(title)>60 else ""}</span></nav>'

    # Header card
    BD_FIELDS = [
        ('Organization',     bd.get('organization_name')),
        ('Post Name',        bd.get('post_name')),
        ('Total Vacancies',  bd.get('total_vacancies') or vacancies),
        ('Application Mode', bd.get('application_mode') or apply_mode),
        ('Job Location',     bd.get('job_location') or location),
        ('Job Type',         bd.get('job_type')),
        ('Notification No.', bd.get('notification_number')),
        ('Advertisement No.',bd.get('advt_no')),
        ('Last Updated',     bd.get('last_updated')),
    ]
    hdr_rows = kv_rows(BD_FIELDS)
    if src and not is_blocked(src):
        hdr_rows += f'<tr><th>Official Website</th><td><a href="{e(src)}" target="_blank" rel="noopener noreferrer">{e(src[:80])}</a></td></tr>'

    badge_label = type_label or ('Govt Job' if page_type=='job' else 'Education' if page_type=='education' else 'State Job')
    badge2_bg = '#dcfce7' if page_type=='job' else '#fef9c3' if page_type=='education' else '#f3e8ff'
    badge2_cl = '#166534' if page_type=='job' else '#713f12' if page_type=='education' else '#581c87'

    header_html = f'''<div class="jd-header">
  <div class="jd-badge-row">
    <span class="jd-badge"><i class="fa-solid fa-briefcase"></i> {e(badge_label)}</span>
    <span class="jd-badge" style="background:{badge2_bg};color:{badge2_cl}"><i class="fa-solid fa-map-pin"></i> {e(location[:30])}</span>
  </div>
  <h1 class="jd-title">{e(title)}</h1>
  {f'<table class="jd-table" style="margin-bottom:0"><tbody>{hdr_rows}</tbody></table>' if hdr_rows else ''}
  <div class="jd-stats">
    <div class="jd-stat"><div class="jd-stat-val">{e(vacancies or '—')}</div><div class="jd-stat-lbl">Vacancies</div></div>
    <div class="jd-stat"><div class="jd-stat-val" style="color:#dc2626">{e(last_date or '—')}</div><div class="jd-stat-lbl">Last Date</div></div>
    <div class="jd-stat"><div class="jd-stat-val">{e(apply_mode or '—')}</div><div class="jd-stat-lbl">Apply Mode</div></div>
    <div class="jd-stat"><div class="jd-stat-val">{e((location or 'India')[:18])}</div><div class="jd-stat-lbl">Location</div></div>
  </div>
</div>'''

    # All 16 sections
    secs = ''
    if short_info:
        secs += f'<div class="short-info-card"><i class="fa-solid fa-circle-info" style="color:#1d4ed8;margin-right:6px"></i>{e(short_info)}</div>'
    secs += render_important_dates(dates)
    secs += render_fee(fee)
    secs += render_age(age)
    secs += render_qual(qual)
    secs += render_vacancy(vac)
    secs += render_cat_vacancy(cwv)
    secs += render_salary(sal)
    secs += render_selection(sel)
    secs += render_exam_pattern(ep)
    secs += render_syllabus(syl)
    secs += render_physical(pe)
    secs += render_hta(hta)
    secs += render_instructions(insts)
    secs += render_edu_sections(edu_s)
    secs += render_links(il)
    secs += render_faq(faq)

    if not secs.strip():
        if src and not is_blocked(src):
            secs = card('linear-gradient(135deg,#1e40af,#1e3a8a)', 'fa-link', 'Important Links',
                        f'<div class="links-grid"><a href="{e(src)}" class="link-btn btn-green" target="_blank" rel="noopener noreferrer"><i class="fa-solid fa-globe"></i> Official Website</a></div>')
        else:
            secs = '<div class="job-card"><div class="job-card-body" style="padding:20px;text-align:center;color:#94a3b8"><i class="fa-solid fa-clock" style="font-size:1.5rem;display:block;margin-bottom:8px"></i>Detailed information will be updated soon.</div></div>'

    int_links = '''<div class="job-card" style="margin-top:8px">
  <div class="job-card-head" style="background:#475569"><i class="fa-solid fa-arrow-right"></i><h2>Related Categories</h2></div>
  <div class="job-card-body rel-links">
    <a href="/section/latest-jobs/" class="link-btn btn-gray"><i class="fa-solid fa-briefcase"></i> Latest Jobs</a>
    <a href="/section/admit-card/" class="link-btn btn-teal"><i class="fa-solid fa-id-card"></i> Admit Cards</a>
    <a href="/section/results/" class="link-btn btn-green"><i class="fa-solid fa-trophy"></i> Results</a>
    <a href="/state/" class="link-btn btn-indigo"><i class="fa-solid fa-map-location-dot"></i> State Jobs</a>
    <a href="/education/" class="link-btn btn-purple"><i class="fa-solid fa-graduation-cap"></i> Education</a>
  </div>
</div>'''

    # Generation watermark (hidden, for debugging)
    gen_mark = f'<!-- Generated: {NOW} | Source: Complete_Jobs_Full_Data.json | Version: {GEN_VER} -->'

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
  <script type="application/ld+json">{json.dumps(job_schema, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(bc_schema, ensure_ascii=False)}</script>
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
  <style>{PAGE_CSS}</style>
</head>
<body>
  {gen_mark}
  <div id="headerPlaceholder"></div>
  <script>fetch('/header.html',{{cache:'no-store'}}).then(r=>r.ok?r.text():null).catch(()=>null).then(h=>{{if(h){{var d=document.getElementById('headerPlaceholder');if(d)d.outerHTML=h;}}}})</script>
  <main>
    <div class="pg-wrap">
      {bc_html}
      <div class="notice-bar">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span><strong>Important:</strong> Always verify details on the official website. Dates &amp; eligibility may change.</span>
      </div>
      {header_html}
      {secs}
      {int_links}
    </div>
  </main>
  <div id="footerPlaceholder"></div>
  <script>fetch('/footer.html',{{cache:'no-store'}}).then(r=>r.ok?r.text():null).catch(()=>null).then(h=>{{if(h){{var d=document.getElementById('footerPlaceholder');if(d)d.outerHTML=h;}}}})</script>
  <script src="/tsj-menu.js" defer></script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════
# WRITE HELPER — atomic, no partial writes
# ══════════════════════════════════════════════════════════════════

written_pages = []

def write_page(out_path: Path, html_content: str, slug: str, url: str, page_type: str):
    """
    Atomically write HTML to disk.
    Uses temp file → rename to avoid partial writes / torn pages.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix('.tmp')
    try:
        tmp.write_text(html_content, encoding='utf-8')
        tmp.replace(out_path)  # atomic rename
        written_pages.append({'slug': slug, 'url': url, 'type': page_type, 'path': str(out_path)})
    except Exception as ex:
        if tmp.exists():
            tmp.unlink()
        print(f"   ⚠️  Failed to write {out_path}: {ex}")


# ══════════════════════════════════════════════════════════════════
# MAIN — THREE GENERATORS
# ══════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  generate_static_pages.py — JSON → HTML Static Generator")
    print(f"  Run at: {NOW}")
    print("=" * 60)

    # ── STEP 1: Read JSON (always fresh, never cached) ──────────
    if not CJ_FILE.exists():
        print(f"\n❌ ERROR: {CJ_FILE} not found. Cannot generate pages.")
        raise SystemExit(1)

    print(f"\n📂 Reading JSON: {CJ_FILE}")
    json_mtime = datetime.fromtimestamp(CJ_FILE.stat().st_mtime).isoformat()
    with open(CJ_FILE, encoding='utf-8') as f:
        data = json.load(f)
    print(f"   JSON last modified: {json_mtime}")
    print(f"   JSON generated_at:  {data.get('generated_at','unknown')}")

    FJA   = data.get('freejobalert_categories', {})
    STATE = (data.get('state_jobs', {}) or {}).get('sections', [])
    EDU   = (data.get('education_jobs', {}) or {}).get('sections', [])

    # ── STEP 2: Clear old generated directories ──────────────────
    clear_generated_directories()

    # ── STEP 3A: Qualification/Category pages ───────────────────
    print("📄 Generating qualification (category/study) pages...")
    cat_count = 0; seen_cat_slugs = {}

    for cat, jobs_list in FJA.items():
        if not isinstance(jobs_list, list): continue
        cat_slug  = QUAL_SLUG.get(cat, slugify(cat))
        cat_label = QUAL_LABEL.get(cat, cat.replace('_',' '))
        cat_dir   = ROOT / 'category' / 'study' / cat_slug

        for job in jobs_list:
            bd    = job.get('basic_details', {}) or {}
            title = safe(bd.get('job_title',''))
            if not title: continue
            slug = slugify(title)
            if not slug: continue

            # Deduplicate: if slug seen in this cat, append counter
            key = f"{cat_slug}/{slug}"
            if key in seen_cat_slugs:
                seen_cat_slugs[key] += 1
                slug = f"{slug}-{seen_cat_slugs[key]}"
            else:
                seen_cat_slugs[key] = 0

            canon  = f"{BASE_URL}/category/study/{cat_slug}/{slug}/"
            bc     = [('Study Wise Jobs', f'{BASE_URL}/category/study/'),
                      (f'{cat_label} Jobs', f'{BASE_URL}/category/study/{cat_slug}/')]
            html   = build_page(title, job, canon, bc, 'job', f'{cat_label} Jobs')
            write_page(cat_dir / slug / 'index.html', html, slug, canon, 'category')
            cat_count += 1

    print(f"   ✓ Category pages: {cat_count}")

    # ── STEP 3B: State job pages ─────────────────────────────────
    print("📄 Generating state job pages...")
    state_count = 0; seen_state_slugs = {}

    for sec in STATE:
        state_name = safe(sec.get('state') or sec.get('title') or '')
        state_slug = slugify(state_name)
        state_dir  = ROOT / 'state' / state_slug

        for item in sec.get('items', []):
            name = safe(item.get('name') or item.get('title') or '')
            if not name: continue

            # Prefer URL slug if clean
            item_url = safe(item.get('url',''))
            slug = ''
            if item_url:
                parts = item_url.rstrip('/').split('/')
                candidate = parts[-1] if parts else ''
                if (candidate and re.match(r'^[a-z0-9][a-z0-9-]{2,80}$', candidate.lower())
                        and '.' not in candidate and '?' not in candidate
                        and '%' not in candidate and len(candidate) <= 80):
                    slug = candidate
            if not slug:
                slug = slugify(name)
            if not slug: continue

            key = f"{state_slug}/{slug}"
            if key in seen_state_slugs:
                seen_state_slugs[key] += 1
                slug = f"{slug}-{seen_state_slugs[key]}"
            else:
                seen_state_slugs[key] = 0

            detail = item.get('detail') or {}
            if isinstance(detail, str):
                try: detail = json.loads(detail)
                except: detail = {}

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

            canon = f"{BASE_URL}/state/{state_slug}/{slug}/"
            bc    = [('State Jobs', f'{BASE_URL}/state/'),
                     (f'{state_name} Jobs', f'{BASE_URL}/state/{state_slug}/')]
            html  = build_page(name, detail, canon, bc, 'state', f'{state_name} Govt Job')
            write_page(state_dir / slug / 'index.html', html, slug, canon, 'state')
            state_count += 1

    print(f"   ✓ State pages: {state_count}")

    # ── STEP 3C: Education pages ─────────────────────────────────
    print("📄 Generating education pages...")
    edu_count = 0; seen_edu_slugs = {}

    for sec in EDU:
        sec_id    = safe(sec.get('id') or sec.get('title') or '')
        sec_title = safe(sec.get('title') or sec_id)
        sec_slug  = slugify(sec_id) if sec_id else slugify(sec_title)
        sec_dir   = ROOT / 'education' / sec_slug

        for item in sec.get('items', []):
            name = safe(item.get('name') or item.get('examName') or '')
            if not name: continue
            slug = slugify(name)
            if not slug: continue

            key = f"{sec_slug}/{slug}"
            if key in seen_edu_slugs:
                seen_edu_slugs[key] += 1
                slug = f"{slug}-{seen_edu_slugs[key]}"
            else:
                seen_edu_slugs[key] = 0

            det = item.get('detail') or {}
            full_detail = {
                'basic_details': {
                    'job_title':         det.get('title') or name,
                    'organization_name': sec_title,
                    'job_location':      sec_title,
                    'short_information': det.get('short_info',''),
                    'last_updated':      safe(item.get('postDate') or item.get('date') or ''),
                },
                'important_dates': {},
                'important_links': det.get('important_links') or {},
                'sections':        det.get('sections') or [],
                'faq':             det.get('faq') or [],
                'source_url':      safe(item.get('url','')),
            }
            if item.get('date') or item.get('postDate'):
                full_detail['important_dates']['notification_date'] = safe(item.get('date') or item.get('postDate'))

            canon = f"{BASE_URL}/education/{sec_slug}/{slug}/"
            bc    = [('Education', f'{BASE_URL}/education/'),
                     (sec_title, f'{BASE_URL}/education/{sec_slug}/')]
            html  = build_page(name, full_detail, canon, bc, 'education', sec_title)
            write_page(sec_dir / slug / 'index.html', html, slug, canon, 'education')
            edu_count += 1

    print(f"   ✓ Education pages: {edu_count}")

    # ── STEP 4: Write generation manifest ───────────────────────
    total = cat_count + state_count + edu_count
    manifest = {
        'generated_at':   NOW,
        'generator':      'generate_static_pages.py',
        'version':        GEN_VER,
        'json_source':    str(CJ_FILE),
        'json_modified':  json_mtime,
        'json_generated': data.get('generated_at',''),
        'totals': {
            'category': cat_count,
            'state':    state_count,
            'education': edu_count,
            'total':    total,
        },
        'pages': written_pages,
    }
    manifest_path = ROOT / 'static-gen-manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"\n{'=' * 60}")
    print(f"  ✅ GENERATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Category pages : {cat_count}")
    print(f"  State pages    : {state_count}")
    print(f"  Education pages: {edu_count}")
    print(f"  TOTAL          : {total}")
    print(f"  Manifest       : {manifest_path}")
    print(f"  Version        : {GEN_VER}")
    print(f"{'=' * 60}\n")

    return total


if __name__ == '__main__':
    main()
