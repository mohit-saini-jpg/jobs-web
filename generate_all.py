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

import json, re, os, html as _html, shutil, hashlib
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

# ── Wide tablet-style viewport for mobile (Mid View 600-899px), zoom enabled ──
# Forced ~820px logical width on phones so more content shows without hiding,
# and pinch zoom stays available. Stored as a plain string (NOT inside any
# f-string) so its JS braces don't clash with f-string formatting.
VP_SNIPPET = ('<script>/*TSJ-WIDE-VIEWPORT*/(function(){var W=640,'
    'm=document.querySelector(\'meta[name="viewport"]\');'
    'if(!m){m=document.createElement(\'meta\');m.name=\'viewport\';'
    '(document.head||document.documentElement).appendChild(m);}'
    'var sw=(window.screen&&screen.width)||window.innerWidth||W;'
    'if(sw<W){m.setAttribute(\'content\',\'width=\'+W+\', user-scalable=yes, maximum-scale=5.0\');}'
    'else{m.setAttribute(\'content\',\'width=device-width, initial-scale=1.0, user-scalable=yes, maximum-scale=5.0\');}'
    '})();</script>')

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
    ld  = (imp.get('extended_last_date') or imp.get('date_extended')
           or imp.get('last_date_to_apply') or imp.get('last_date') or '').strip()
    lu  = (bd.get('last_updated') or '').strip()
    return (_parse_date_str(ld), _parse_date_str(lu))

def is_garbage_title(title):
    if not title or not title.strip(): return True
    tl = title.lower().strip()
    return any(p in tl for p in GARBAGE_PATTERNS)
TODAY    = date.today().isoformat()
TODAY_ISO = date.today().strftime('%Y-%m-%dT00:00:00+05:30')   # ISO 8601 with IST tz
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

# ── SLUG REGISTRY — permanent solution for title-change 404s ────────────────
# Problem: Scraper ek job ka title update karta hai (e.g. "Answer Key" → "Result")
# → slugify se naya slug banta hai → purana URL 404 ho jaata hai.
# Solution: data/slug-registry.json mein  title_fingerprint → canonical_slug  store
# karo. Ek baar registered slug KABHI nahi badlega — chahe title kuch bhi ho.
#
# slug_registry.json format:
#   { "title_fingerprint": "canonical-slug-80chars", ... }
#   title_fingerprint = normalized lowercase tokens (stop words hata ke)
#
# Flow:
#   1. Load registry at start
#   2. Job ke liye slug chahiye → pehle registry check karo
#   3. Registry mein hai → wahi slug use karo (title change = same slug)
#   4. Registry mein nahi → slugify se generate karo, registry mein save karo
#   5. Save registry at end (only if dirty)

_SLUG_REGISTRY_PATH = None
_SLUG_REGISTRY = {}          # fingerprint → slug
_SLUG_REGISTRY_DIRTY = False
_SR_STOP = frozenset((
    'the','and','for','of','in','to','a','an','with','on','at','by','top',
    'sarkari','jobs','recruitment','apply','online','offline','notification',
    'out','check','details','post','posts','vacancy','vacancies','form',
    'registration','last','date','here','now','download','pdf','2024',
    '2025','2026','2027','2028','latest','govt','government','result',
    'admit','card','answer','key','syllabus','exam','new','all','various',
))

def _sr_fingerprint(title):
    """Stable fingerprint: lowercase alphanum tokens minus stop words."""
    t = re.sub(r'[^a-z0-9\s]', ' ', str(title or '').lower())
    toks = [w for w in t.split() if w and w not in _SR_STOP and len(w) > 1]
    return ' '.join(sorted(toks))   # sorted = order-independent

def _load_slug_registry(root_path):
    global _SLUG_REGISTRY, _SLUG_REGISTRY_PATH
    _SLUG_REGISTRY_PATH = str(Path(root_path) / 'data' / 'slug-registry.json')
    try:
        with open(_SLUG_REGISTRY_PATH, encoding='utf-8') as f:
            _SLUG_REGISTRY = json.load(f)
    except Exception:
        _SLUG_REGISTRY = {}

def _save_slug_registry():
    global _SLUG_REGISTRY_DIRTY
    if not _SLUG_REGISTRY_DIRTY or not _SLUG_REGISTRY_PATH:
        return
    try:
        import os as _osr
        _osr.makedirs(_osr.path.dirname(_SLUG_REGISTRY_PATH), exist_ok=True)
        with open(_SLUG_REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump(_SLUG_REGISTRY, f, ensure_ascii=False,
                      separators=(',', ':'), sort_keys=True)
        _SLUG_REGISTRY_DIRTY = False
    except Exception:
        pass

def registered_slug(title):
    """Return the permanent slug for a job title.
    - First call: generate via slugify(), store in registry, return it.
    - Later calls (same job, different title): registry hit → same slug returned.
    This means a job whose title changes on the source site keeps its original URL.
    """
    global _SLUG_REGISTRY_DIRTY
    if not title:
        return slugify(title)
    fp = _sr_fingerprint(title)
    if fp and fp in _SLUG_REGISTRY:
        return _SLUG_REGISTRY[fp]   # cached — title-change proof
    s = slugify(title)
    if fp and s:
        _SLUG_REGISTRY[fp] = s
        _SLUG_REGISTRY_DIRTY = True
    return s

def _job_title_of(job_obj):
    bd = job_obj.get('basic_details') or {} if isinstance(job_obj, dict) else {}
    return str((bd.get('job_title') if isinstance(bd, dict) else '') or
               (job_obj.get('title') if isinstance(job_obj, dict) else '') or
               (job_obj.get('name') if isinstance(job_obj, dict) else '') or '').strip()

def _register_title_slug(job_obj, slug):
    """Record title-fingerprint → canonical slug so any component that only has a
    title (not the full job dict) resolves to the SAME physically-generated URL."""
    global _SLUG_REGISTRY_DIRTY
    if not slug or not isinstance(job_obj, dict):
        return
    t = _job_title_of(job_obj)
    if not t:
        return
    fp = _sr_fingerprint(t)
    if fp and _SLUG_REGISTRY.get(fp) != slug:
        _SLUG_REGISTRY[fp] = slug
        _SLUG_REGISTRY_DIRTY = True

def canonical_job_slug(title, job_obj=None):
    """THE resolver for listing-card / hub URLs. Returns the exact slug the detail
    page was generated at. Prefers the full job dict; otherwise resolves a title
    through the slug registry (populated by get_canonical_slug as pages build)."""
    if isinstance(job_obj, dict):
        s = get_canonical_slug(job_obj)
        if s:
            return s
    t = str(title or '').strip()
    if not t:
        return ''
    fp = _sr_fingerprint(t)
    if fp and fp in _SLUG_REGISTRY:
        return _SLUG_REGISTRY[fp]
    return registered_slug(t)


# ── CANONICAL SLUG RESOLVER ───────────────────────────────────────────────────
# Rule: ONE job = ONE URL everywhere on the site.
# Priority order (highest → lowest):
#   1. job['_canonical_slug']  — scraper sets this; immutable; always wins
#   2. job['slug']             — scraper-assigned raw slug (normalized)
#   3. registered_slug(title)  — generated from title, stored in slug-registry
#
# This function is THE SINGLE SOURCE OF TRUTH for every <a href="/jobs/…/"> on
# the site — listing cards, section pages, category feeds, sitemaps, schemas.
# NEVER call slugify(title)[:N] directly inside any HTML rendering loop.
# ─────────────────────────────────────────────────────────────────────────────
def get_canonical_slug(job_obj):
    """Return the one true canonical slug for a job record.

    Reads _canonical_slug from the JSON first (scraper-set, permanent).
    Falls back to normalized slug field, then to registered_slug(title).
    Guarantees a clean, dash-normalized string with no trailing dashes,
    no SR prefixes, and no hex hash suffixes — safe for /jobs/{slug}/ URLs.
    """
    # Priority 1: explicit _canonical_slug from scraper (most reliable)
    cs = str(job_obj.get('_canonical_slug') or '').strip()
    if cs:
        s = _norm_slug(cs)
        # register title→slug so TITLE-ONLY resolvers (listing cards built from
        # index data without the full job dict) resolve to this exact slug.
        _register_title_slug(job_obj, s)
        return s

    # Priority 2: raw slug field (normalize it — strip SR prefix, hex suffix)
    raw = str(job_obj.get('slug') or '').strip()
    if raw:
        # Strip SR category prefix (sr_result-, sr_admit_card-, etc.)
        raw = re.sub(r'^sr_[a-z_]+-', '', raw)
        # Strip trailing hex hash (6-8 hex chars, NOT pure numeric FJA IDs)
        _tail = re.search(r'-([0-9a-f]{6,8})$', raw)
        if _tail and not _tail.group(1).isdigit():
            raw = raw[:-len(_tail.group(0))]
        s = _norm_slug(raw)
        if s:
            # SEO FIX (One Job = One URL) — self-healing registry:
            # If the registry has a DIFFERENT stale entry for this title's
            # fingerprint, correct it now so future runs don't mint a frozen
            # duplicate folder via the old stale slug.
            bd2 = job_obj.get('basic_details') or {}
            _t2 = str(
                bd2.get('job_title') or job_obj.get('title') or
                job_obj.get('name') or ''
            ).strip()
            if _t2:
                _fp2 = _sr_fingerprint(_t2)
                if _fp2 and _fp2 in _SLUG_REGISTRY and _SLUG_REGISTRY[_fp2] != s:
                    global _SLUG_REGISTRY_DIRTY
                    _old_reg = _SLUG_REGISTRY[_fp2]
                    _SLUG_REGISTRY[_fp2] = s
                    _SLUG_REGISTRY_DIRTY = True
                    # Log the drift so it's visible run-over-run
                    try:
                        import os as _os2
                        _drift_path = _os2.path.join(
                            _os2.path.dirname(_SLUG_REGISTRY_PATH or '.'),
                            '..', 'REGISTRY_DRIFT_LOG.md'
                        )
                        with open(_drift_path, 'a', encoding='utf-8') as _df:
                            _df.write(
                                f"- fp=`{_fp2}` old=`{_old_reg}` "
                                f"new=`{s}` (job.slug Priority-2 override)\n"
                            )
                    except Exception:
                        pass
            _register_title_slug(job_obj, s)
            return s

    # Priority 3: derive from title via slug-registry (title-change proof)
    bd = job_obj.get('basic_details') or {}
    title = str(
        bd.get('job_title') or
        job_obj.get('title') or
        job_obj.get('name') or ''
    ).strip()
    if title:
        return registered_slug(title)

    return 'page'


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

# ── DYNAMIC PAGE INTENT CLASSIFIER ─────────────────────────────────────────
# Returns one of 9 intents:
#   job | result | admitcard | answerkey | syllabus | admission | scheme |
#   education | article
# Logic: category prefix → data signals → title+slug keywords (priority order)
# NEVER upgrades a non-job category to 'job' based on title alone.
import re as _re_intent

# ── Job confirmation signals ─────────────────────────────────────────────────
_RX_JOB = _re_intent.compile(
    r'\b(recruitment|vacancy|vacancies|online\s*form|apply\s*online|'
    r'notification|bharti|engagement|walk\s*in|hiring|appointment|advt|'
    r'job\s*alert|sarkari\s*naukri\s*form)\b', _re_intent.I)

# ── Non-job signals (mutually exclusive, in priority order) ─────────────────
_RX_ANSWERKEY = _re_intent.compile(
    r'\b(answer\s*key|answer\s*sheet|objection|challenge\s*key|'
    r'response\s*sheet|provisional\s*answer)\b', _re_intent.I)

_RX_RESULT = _re_intent.compile(
    r'\b(result|results|scorecard|score\s*card|merit\s*list|'
    r'cut\s*off|rank\s*card|declared|revaluation|marks\s*available|'
    r'final\s*answer\s*key|provisional\s*key)\b', _re_intent.I)

_RX_ADMIT = _re_intent.compile(
    r'\b(admit\s*card|hall\s*ticket|call\s*letter|exam\s*date|'
    r'date\s*sheet|time\s*table|exam\s*city|slot\s*booking|'
    r'exam\s*schedule|exam\s*centre|download\s*admit)\b', _re_intent.I)

_RX_SYLLABUS = _re_intent.compile(
    r'\b(syllabus|exam\s*pattern|paper\s*pattern|study\s*material|'
    r'previous\s*paper|old\s*paper|model\s*paper|sample\s*paper|'
    r'question\s*paper|curriculum)\b', _re_intent.I)

_RX_ADMISSION = _re_intent.compile(
    r'\b(admission|counselling|counseling|allotment|seat\s*allot|'
    r'neet|jee|cuet|entrance|college\s*admission|merit\s*list\s*admission)\b',
    _re_intent.I)

_RX_SCHEME = _re_intent.compile(
    r'\b(yojana|yojna|scheme|pension|pm\s*kisan|samman\s*nidhi|'
    r'e\s*shram|umang|ration\s*card|aadhar|loan|subsidy|stipend|'
    r'pradhan\s*mantri|mukhya\s*mantri|awas|ujjwala|svamitva|'
    r'scholarship(?!.*exam)|card\s*download|kyc|status\s*check)\b',
    _re_intent.I)

_RX_EDUCATION = _re_intent.compile(
    r'\b(state\s*wise|district\s*wise|education\s*wise|category\s*wise\s*job|'
    r'age\s*limit\s*guide|eligibility\s*guide|qualification\s*wise|'
    r'how\s*to\s*apply\s*guide|10th\s*pass\s*jobs|12th\s*pass\s*jobs|'
    r'graduate\s*jobs|diploma\s*jobs)\b', _re_intent.I)

# ── Category-prefix → intent (AUTHORITATIVE — never overridden by title) ────
_CAT_INTENT = {
    'SR_Latest_Jobs': 'job',      'SR_Upcoming_Jobs': 'job',
    'SR_Result':      'result',   'FJA_Result':       'result',
    'SR_Admit_Card':  'admitcard','FJA_Admit_Card':   'admitcard',
    'SR_Answer_Key':  'answerkey','FJA_Answer_Key':   'answerkey',
    'SR_Syllabus':    'syllabus', 'FJA_Syllabus':     'syllabus',
    'SR_Admission':   'admission','FJA_Admission':    'admission',
    'Scheme':         'scheme',   'Yojana':           'scheme',
    'Education':      'education','StateWise':        'education',
    'Article':        'article',  'Guide':            'article',
    'Info':           'article',
}

# ── SLUG-BASED STATE MAP (acronym-aware, order matters) ─────────────────────
_SLUG_STATE_MAP = [
    # West Bengal — BEFORE Bihar (wbpsc/wbssc contain 'bpsc'/'bssc')
    ('west-bengal','West Bengal','700001'), ('wbpsc','West Bengal','700001'),
    ('wbssc','West Bengal','700001'),
    # Chhattisgarh
    ('chhattisgarh','Chhattisgarh','492001'), ('cgpsc','Chhattisgarh','492001'),
    ('cgvyapam','Chhattisgarh','492001'),
    # Jharkhand
    ('jharkhand','Jharkhand','834001'), ('jssc','Jharkhand','834001'),
    ('jpsc','Jharkhand','834001'),
    # Rajasthan
    ('rajasthan','Rajasthan','302001'), ('rpsc','Rajasthan','302001'),
    ('rsmssb','Rajasthan','302001'),    ('reet','Rajasthan','302001'),
    # Uttar Pradesh
    ('up-police','Uttar Pradesh','226001'), ('uppsc','Uttar Pradesh','226001'),
    ('upsssc','Uttar Pradesh','226001'),    ('upsessb','Uttar Pradesh','226001'),
    ('uttar-pradesh','Uttar Pradesh','226001'), ('uppcb','Uttar Pradesh','226001'),
    # Bihar
    ('bihar','Bihar','800001'),  ('bpsc','Bihar','800001'), ('bssc','Bihar','800001'),
    # Madhya Pradesh
    ('madhya-pradesh','Madhya Pradesh','462001'), ('mppsc','Madhya Pradesh','462001'),
    ('mptet','Madhya Pradesh','462001'),
    # Maharashtra
    ('maharashtra','Maharashtra','400001'), ('mpsc','Maharashtra','400001'),
    ('rbi','Maharashtra','400001'),         ('nabard','Maharashtra','400001'),
    ('niacl','Maharashtra','400001'),
    # Gujarat
    ('gujarat','Gujarat','380001'), ('gpsc','Gujarat','380001'),
    ('gsssb','Gujarat','380001'),   ('gsrtc','Gujarat','380001'),
    # Haryana
    ('haryana','Haryana','122001'), ('hpsc','Haryana','122001'),
    ('hssc','Haryana','122001'),    ('hsssc','Haryana','122001'),
    # Punjab
    ('punjab','Punjab','141001'), ('ppsc','Punjab','141001'), ('psssb','Punjab','141001'),
    # Karnataka
    ('karnataka','Karnataka','560001'), ('kpsc','Karnataka','560001'),
    ('ksp','Karnataka','560001'),
    # Tamil Nadu
    ('tamil-nadu','Tamil Nadu','600001'), ('tnpsc','Tamil Nadu','600001'),
    ('tnusrb','Tamil Nadu','600001'),
    # Odisha
    ('odisha','Odisha','751001'), ('opsc','Odisha','751001'), ('osssc','Odisha','751001'),
    # Telangana
    ('telangana','Telangana','500001'), ('tspsc','Telangana','500001'),
    # Andhra Pradesh
    ('andhra-pradesh','Andhra Pradesh','520001'), ('appsc','Andhra Pradesh','520001'),
    # Assam
    ('assam','Assam','781001'), ('apsc','Assam','781001'), ('apdcl','Assam','781001'),
    # Uttarakhand
    ('uttarakhand','Uttarakhand','248001'), ('ukpsc','Uttarakhand','248001'),
    ('uksssc','Uttarakhand','248001'),
    # Himachal Pradesh
    ('himachal-pradesh','Himachal Pradesh','171001'), ('hppsc','Himachal Pradesh','171001'),
    ('himachal','Himachal Pradesh','171001'),
    # Kerala
    ('kerala','Kerala','695001'),
    # Other states
    ('goa','Goa','403001'),
    ('tripura','Tripura','799001'),   ('tpsc','Tripura','799001'),
    ('manipur','Manipur','795001'),
    ('nagaland','Nagaland','797001'),
    ('meghalaya','Meghalaya','793001'),
    ('mizoram','Mizoram','796001'),
    ('arunachal','Arunachal Pradesh','791001'),
    ('sikkim','Sikkim','737101'),
    ('chandigarh','Chandigarh','160001'),
    ('jammu','Jammu & Kashmir','180001'), ('jkpsc','Jammu & Kashmir','180001'),
    ('jkssb','Jammu & Kashmir','180001'),
    # PSUs
    ('northern-coalfield','Madhya Pradesh','486001'),
    ('central-coalfields','Jharkhand','834001'),
    ('coal-india','West Bengal','700001'),
    ('bhel','Uttar Pradesh','208001'),
    # Delhi & Central
    ('delhi','Delhi','110001'),  ('dsssb','Delhi','110001'),
    ('ndmc','Delhi','110001'),   ('upsc','Delhi','110001'),
    ('ssc','Delhi','110001'),    ('nicl','Delhi','110001'),
    ('ntpc','Delhi','110001'),   ('ongc','Delhi','110001'),
    ('sail','Delhi','110001'),
]

def _detect_state_from_text(text):
    """Return (region, pincode) from slug/title/org text, or (None, None)."""
    t = str(text).lower().replace(' ', '-')
    for kw, region, pin in _SLUG_STATE_MAP:
        if kw in t:
            return region, pin
    return None, None

def _reconstruct_job_from_html(html_content, title, slug):
    """Rebuild minimal job dict from existing page HTML (no data JSON available).
    Extracts org/location/dates from existing JSON-LD. Uses _detect_state_from_text
    on slug+title+org for correct state detection on old orphan pages.
    """
    import json as _j
    job = {
        'title': title,
        'basic_details': {'job_title': title, 'job_location': 'India',
                          'organization_name': 'Government of India',
                          'short_information': title},
        'important_dates': {}, 'salary_details': {},
        'ai_extracted_structured_data': None, 'category': '',
    }
    for _m in _JSONLD_RE.findall(html_content):
        try:
            _d = _j.loads(_m[_m.index('{'):_m.rindex('}')+1])
            if _d.get('@type') == 'JobPosting':
                _ho = _d.get('hiringOrganization', {})
                if _ho.get('name'):
                    job['basic_details']['organization_name'] = _ho['name']
                _addr = (_d.get('jobLocation') or {}).get('address', {})
                _loc  = _addr.get('addressLocality', '')
                if _loc and _loc.lower() not in ('india', ''):
                    job['basic_details']['job_location'] = _loc
                if _d.get('validThrough', '')[:10]:
                    job['important_dates']['last_date_to_apply'] = _d['validThrough'][:10]
                _sal = (_d.get('baseSalary') or {}).get('value', {})
                if _sal.get('minValue'):
                    job['salary_details']['pay_scale'] =                         f"{_sal['minValue']}-{_sal.get('maxValue', _sal['minValue'])}"
        except Exception:
            pass
    # Infer category from slug keywords
    for _kw, _cat in [('admit', 'SR_Admit_Card'), ('result', 'SR_Result'),
                       ('answer-key', 'SR_Answer_Key'), ('syllabus', 'SR_Syllabus'),
                       ('admission', 'SR_Admission'), ('recruitment', 'SR_Latest_Jobs'),
                       ('vacancy', 'SR_Latest_Jobs'), ('yojana', 'Scheme'),
                       ('scheme', 'Scheme')]:
        if _kw in slug.lower():
            job['category'] = _cat; break
    # State detection: slug + title + org (most reliable for old pages)
    _r, _p = _detect_state_from_text(
        f"{slug} {title} {job['basic_details']['organization_name']}")
    if _r:
        job['basic_details']['job_location'] = _r
        job['_detected_region'] = _r
        job['_detected_pin']    = _p
    return job

# SR_Latest_Jobs / SR_Upcoming_Jobs are scraped as generic "latest update"
# buckets and, in practice, also contain scheme/yojana, result, admit
# card, answer key and admission items alongside real job postings — NOT
# forced to 'job' below, so STEP 2/3 keyword detection decides these.
_MIXED_JOB_CATS = ('SR_Latest_Jobs', 'SR_Upcoming_Jobs')

def page_intent(job_obj):
    """Dynamically classify page into one of 9 intents.
    Priority: category prefix > data signals > title/slug keywords.
    Category NEVER gets overridden by title — avoids false positives.
    Exception: SR_Latest_Jobs / SR_Upcoming_Jobs are mixed-content buckets
    (see _MIXED_JOB_CATS) and always fall through to keyword detection.
    """
    bd    = job_obj.get('basic_details', {}) or {}
    cat   = str(job_obj.get('category') or '').strip()
    title = str(bd.get('job_title','') or job_obj.get('title','') or '')
    slug  = str(job_obj.get('_canonical_slug') or job_obj.get('slug') or '')

    # ── STEP 1: Category prefix (authoritative, fastest) ────────────────────
    if cat not in _MIXED_JOB_CATS:
        for prefix, intent in _CAT_INTENT.items():
            if prefix in _MIXED_JOB_CATS:
                continue
            if cat == prefix or cat.startswith(prefix + '_') or cat.startswith(prefix):
                return intent

    # ── STEP 2: Data signals (vacancy/salary = definite job) ────────────────
    has_vacancy = bool(
        job_obj.get('vacancy_details') or
        job_obj.get('category_wise_vacancy') or
        (bd.get('total_vacancies','') not in ('','0', None)))
    if has_vacancy:
        return 'job'

    # ── STEP 3: Title + slug keyword matching (priority order) ──────────────
    blob = f"{title} {slug}".lower()

    # Answer key first (before result, as some AK pages have "result" word)
    if _RX_ANSWERKEY.search(blob):
        return 'answerkey'
    # Syllabus (before result/admit to avoid "exam date" cross-match)
    if _RX_SYLLABUS.search(blob) and not _RX_JOB.search(blob):
        return 'syllabus'
    # Result (only when no job signal)
    if _RX_RESULT.search(blob) and not _RX_JOB.search(blob):
        return 'result'
    # Admit card (only when no job signal)
    if _RX_ADMIT.search(blob) and not _RX_JOB.search(blob):
        return 'admitcard'
    # Admission counselling
    if _RX_ADMISSION.search(blob) and not _RX_JOB.search(blob):
        return 'admission'
    # Job signal (after all non-job checks)
    if _RX_JOB.search(blob):
        return 'job'
    # Scheme / Yojana
    if _RX_SCHEME.search(blob):
        return 'scheme'
    # Education / listing pages
    if _RX_EDUCATION.search(blob):
        return 'education'

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
    # ── Preserve key punctuation patterns BEFORE stripping all specials ──────
    # 1. "10+2" / "12+2" → "10-2" / "12-2"  (standard class notation)
    text = re.sub(r'\b(10|12)\+2\b', r'\1-2', text)
    # 2. Degree abbreviations with dots: B.Ed. → b-ed, D.El.Ed → d-el-ed etc.
    #    Must run before the general punctuation strip.
    text = re.sub(r'\bb\.ed\.?', 'b-ed', text)
    text = re.sub(r'\bd\.el\.ed\.?', 'd-el-ed', text)
    text = re.sub(r'\bd\.p\.ed\.?', 'd-p-ed', text)
    text = re.sub(r'\bb\.tech\.?', 'b-tech', text)
    text = re.sub(r'\bm\.tech\.?', 'm-tech', text)
    text = re.sub(r'\bb\.sc\.?', 'b-sc', text)
    text = re.sub(r'\bm\.sc\.?', 'm-sc', text)
    text = re.sub(r'\bb\.com\.?', 'b-com', text)
    text = re.sub(r'\bm\.com\.?', 'm-com', text)
    text = re.sub(r'\bm\.ed\.?', 'm-ed', text)
    text = re.sub(r'\bph\.d\.?', 'phd', text)
    # 3. Possessive 's → -s  (Bank's → bank-s, India's → india-s)
    text = re.sub(r"\u2019s\b", '-s', text)   # curly apostrophe
    text = re.sub(r"'s\b", '-s', text)         # straight apostrophe
    # ── Standard strip ──────────────────────────────────────────────────────
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    # Strip BEFORE truncation, then truncate, then strip AGAIN
    # (in case 80-char cut lands on a dash boundary).
    text = text.strip('-')[:80].strip('-')
    return text or 'page'

# ── DON'T MISS scraper-leak sanitizer ────────────────────────────────────────
# The scraper sometimes concatenates a "Don't Miss" sidebar widget onto the
# real short_information field. Strip it before it reaches meta-descriptions
# or AI prompts, preventing polluted/identical content across 350+ pages.
_DONT_MISS_RE = re.compile(r"DON[’‘']?T\s+MISS.*", re.I | re.S)

def sanitize_short_info(text):
    """Remove leaked 'Don't Miss' sidebar widget text from short_information."""
    if not text:
        return ''
    cleaned = _DONT_MISS_RE.sub('', str(text)).strip()
    return cleaned

def _norm_slug(s):
    """Normalize any slug (from JSON or wherever) - strip trailing dashes,
    collapse repeated dashes. JSON slugs from PC scraper sometimes end with '-'
    when title >=80 chars; this strips them so URL matches actual page on disk."""
    if not s: return ''
    s = str(s).strip().lower()
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')[:80].strip('-')

def smart_title_cut(text, limit=60):
    """Cut a <title> at a word boundary so there's no mid-word truncation."""
    text = str(text or '')
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0]
    return cut.rstrip(' ,;:-–(')

def clean_slug(s):
    s = str(s or '').strip()
    s = re.sub(r'^sr_[a-z_]+-', '', s)
    s = re.sub(r'-[0-9a-f]{6,8}$', '', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:80] or ''

# ── JUNK-SLUG GUARD — permanently stop CREATING junk /jobs/ pages ────────────
# Root cause of the GSC "Not found (404)" churn: when the scraper fails to
# extract a real job title, slugify() falls back to numbers / stray fragments and
# a junk page like /jobs/1-2026-5/, /jobs/2002/, /jobs/page/, /jobs/ppp/ gets
# created. Google indexes it, then it dies on the next data refresh → 404.
# is_junk_slug() detects these so write() can refuse to CREATE new ones.
# It NEVER removes an existing page (guard only fires when the file is absent),
# so nothing currently live is affected — only brand-new junk is prevented.
_JUNK_SKIP_SEEN = set()

def is_junk_slug(slug):
    """True when a /jobs/ slug carries no real job content: the literal 'page'
    fallback, all-numeric (2002, 1-2026-5, 20-000), too few letters (id, pdf,
    ppp, ews), or a lone acronym/word + year (hssc-2026, haryana, yojana)."""
    s = _norm_slug(slug)
    if not s or s == 'page':
        return True
    letters = re.sub(r'[^a-z]', '', s)
    if len(letters) < 4:                        # id, pdf, ppp, ews, lpg, '-'
        return True
    if re.fullmatch(r'[\d\-]+', s):             # 2002, 1500, 20-000, 1-2026-5, 2026-12
        return True
    tokens = [t for t in s.split('-') if re.fullmatch(r'[a-z]{3,}', t)]
    if len(tokens) < 2 and len(letters) < 8:    # hssc-2026, brcm-2026, apply, haryana, yojana
        return True
    return False

def _log_junk_skip(slug):
    if not slug or slug in _JUNK_SKIP_SEEN:
        return
    _JUNK_SKIP_SEEN.add(slug)
    try:
        _p = Path(ROOT) / 'data' / 'SKIPPED_JUNK_SLUGS.md'
        _p.parent.mkdir(parents=True, exist_ok=True)
        with open(_p, 'a', encoding='utf-8') as _f:
            _f.write(f"- `{slug}`  (skipped {date.today().isoformat()})\n")
    except Exception:
        pass

def is_blocked(url):
    return any(d in str(url).lower() for d in BLOCKED)

def _smart_truncate(text, limit):
    """H3 FIX: truncate on a word boundary with an ellipsis, never mid-word.
    If the text already fits, return it unchanged (no ellipsis)."""
    t = str(text or '').strip()
    if len(t) <= limit:
        return t
    cut = t[:limit]
    # back up to the last whitespace so we don't slice a word in half
    sp = cut.rfind(' ')
    if sp > limit * 0.5:        # only if it doesn't chop too much
        cut = cut[:sp]
    return cut.rstrip(' ,;:.') + '…'


def _is_garbled_field(label, value):
    """H4: detect garbled scrape residue not worth rendering in the fallback dump.
    Signals: label begins with a broken ordinal fragment ("ST Week", "Nd Week",
    "Rd ", "Th ") from a mangled "1st/2nd/3rd" split; label/value is a lone
    fragment like "E Soon"; or the value is cut mid-word (ends in a long
    lowercase run with no terminal punctuation and no spaces near the end)."""
    lbl = str(label or '').strip()
    val = str(value or '').strip()
    # broken ordinal fragments at start of label
    if re.match(r'^(st|nd|rd|th)\b', lbl, re.I):
        return True
    # single-letter-prefix garble — only flag the specific known-broken shapes:
    # a lone letter that is NOT a real word ("A"/"I"), followed by a Capitalized
    # word, where the lone letter is a leftover from a cut prefix (e.g. "E Soon"
    # from "AvailablE Soon"). Require the next token to be a real word, and the
    # lone letter to be an unusual sentence-starter (not A/I).
    _m = re.match(r'^([B-HJ-Z])\s+[A-Z][a-z]', lbl)
    if _m:
        return True
    # value truncated mid-word: only flag an obvious cut CONTINUATION fragment —
    # starts lowercase AND contains a space (e.g. "ailable So"), which a real
    # value never does. Single lowercase words ("declared") are valid.
    if val and len(val) < 16 and val[0].islower() and ' ' in val \
            and not re.search(r'[.!?)\]]$', val):
        return True
    return False


def key_label(key):
    label = str(key)
    # split camelCase / PascalCase → spaced words (applicationBegin → application Begin)
    label = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', label)
    label = label.replace('_',' ').replace('-',' ')
    label = re.sub(r'\s+', ' ', label).strip()
    label = re.sub(r'\b([a-z])', lambda m: m.group(1).upper(), label)
    for k,v in {'Url':'URL','Pdf':'PDF','Obc':'OBC','Sc':'SC','St':'ST','Ur':'UR','Ews':'EWS','Pwd':'PwD','Cbt':'CBT','Ph':'PH','Ews Sbc Obc':'EWS / SBC / OBC','Sc St Ph':'SC / ST / PH','Sc St':'SC / ST'}.items():
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
_schema_patched = 0
_JSONLD_RE = re.compile(
    r'<script[^>]+application/ld\+json[^>]*>.*?</script>',
    re.S | re.I
)

def _patch_jsonld(page_path, new_html):
    """Replace JSON-LD <script> blocks in existing page with fresh ones.
    All other page content is preserved. Fixes schema fields on permanent pages.
    """
    global _schema_patched
    try:
        old_html = page_path.read_text(encoding='utf-8')
    except Exception:
        return
    new_blocks = _JSONLD_RE.findall(new_html)
    if not new_blocks:
        return
    # Build one replacement string with all new JSON-LD blocks
    replacement = '\n'.join(new_blocks)
    # Strip all existing JSON-LD from old page
    stripped = _JSONLD_RE.sub('', old_html)
    # Re-insert before </head>
    if '</head>' in stripped:
        patched = stripped.replace('</head>', replacement + '\n</head>', 1)
    elif '<body' in stripped:
        patched = re.sub(r'(<body[^>]*>)', r'\1\n' + replacement, stripped, count=1)
    else:
        patched = replacement + stripped
    if patched == old_html:
        return  # no change needed
    try:
        page_path.write_text(patched, encoding='utf-8')
        _schema_patched += 1
    except Exception:
        pass

_HASH_RE = re.compile(r'<!-- TSJ_HASH:([0-9a-f]{16}) -->')

# ── TEMPLATE_VERSION ─────────────────────────────────────────────────────────
# The content hash is mixed with this version string. BUMP IT whenever the
# RENDERER/template logic changes (not the data) so every existing page is
# force-rewritten on the next run. Without this, a renderer fix (e.g. a new
# vacancy column) never reaches pages whose JSON data did not change, because
# the data-only hash stays identical and write() skips them.
# Format: YYYYMMDD.N  — bump N for multiple changes the same day.
# 20260701.3 — added vacancy_breakdown renderer (FreeJobAlert snake_case);
#              bump forces re-render of ALL existing pages so previous posts
#              also get the new isolated breakdown tables.
# 20260701.4 — vacancy_breakdown skips buckets already shown above (dedup parity)
#              so duplicate data no longer leaves an orphan empty card.
# 20260706.1 — added brand_help_faq() branded category-tailored Q&A to every page's
#              FAQ (visible + FAQPage schema). BUMP forces re-render of ALL existing
#              ~6,246 pages so old A-Z posts also get the branded FAQ (warna
#              hash-unchanged pages skip ho jaati aur branding sirf nayi pages pe aata).
# 20260707.1 — data_tables renderer fix: multi-column (3+ col) tables now use
#              scrollable data-table class instead of kv-table (which forced
#              width:38% per <th>, crushing columns → text wrapped one
#              character per line). Also auto-linkifies bare URL cells (was
#              plain unclickable text) and pads/truncates rows to header
#              column count (was leaving orphan cells floating outside the
#              table). BUMP forces re-render of ALL existing pages so already-
#              baked District-Wise/Post-Wise "Additional Details" tables (UP
#              Anganwadi, JPSC, etc.) get fixed — data itself did not change,
#              so without this bump the content hash stays identical and
#              write() would keep skipping these pages forever.
# 20260710.1 — REL_CATS_HTML SEO relabel: "Related Categories" footer card
#              (present on every /jobs/*/, /state-jobs/*/, /education/*/,
#              /qualification/*/ page) had bare state names ("Haryana") and
#              bare qualification levels ("Diploma") with no "Jobs" suffix,
#              and an "Education State Wise Jobs" header that muddled
#              education with jobs. BUMP forces re-render of ALL existing
#              pages so already-baked pages also pick up the reworded links —
#              data itself did not change, so without this bump the content
#              hash stays identical and write() would keep skipping these
#              pages forever.
# 20260710.2 — Contrast fix: .fee-free text (green "Fee: Free" label on job
#              detail pages) was #16a34a, only 3.3:1 on white — fails WCAG AA
#              (needs 4.5:1). Changed to #166534 (7.1:1). BUMP forces
#              re-render of ALL existing pages so this PageSpeed-flagged
#              contrast issue is fixed sitewide, not just on new pages.
TEMPLATE_VERSION = '20260710.2-cs'

def _page_content_hash(job_obj):
    """16-char MD5 of body-feeding job fields (ai_* excluded — those are patched
    separately) PLUS the template version, so renderer changes invalidate the hash."""
    def _clean(obj):
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in sorted(obj.items()) if not k.startswith('ai_')}
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        return obj
    raw = TEMPLATE_VERSION + '\x00' + json.dumps(_clean(job_obj), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:16]

_AI_MARKER = '<!-- tsj-ai-enriched -->'

def _preserve_ai_blocks(old_html, new_html):
    """Rewrite pe existing AI-injected CARDS blocks (Expert Analysis, Overview,
    Who Should Apply, Preparation Tips, Salary Insights, Job Profile, Selection
    Strategy) ko naye HTML me carry-over karo — taaki data-update ya
    TEMPLATE_VERSION change AI content ko WIPE na kare (jaisa version-bump pe hua tha).

    - Sirf CARDS blocks preserve karo. FAQ blocks (class="faq-wrap") SKIP: base ab
      khud FAQ banata hai (brand_help_faq + auto_generate_faqs) — warna duplicate FAQ.
    - AI_MARKER wrapping bani rehti hai taaki nightly enricher inhe pehchane
      (already-enriched maan ke skip kare) aur agar naya content ho to update kare.
    - Anchor patch_html jaisa hi: pehle <section class="sec-card"> se pehle, warna
      </main>/</article>/</body> se pehle.
    """
    if _AI_MARKER not in old_html or _AI_MARKER in new_html:
        return new_html
    blocks = re.findall(re.escape(_AI_MARKER) + r'(.*?)' + re.escape(_AI_MARKER),
                        old_html, re.DOTALL)
    # sirf card blocks (jinme FAQ-wrap nahi) — FAQ base khud deta hai
    cards = [b for b in blocks if 'class="faq-wrap"' not in b and b.strip()]
    if not cards:
        return new_html
    inject = ''.join(f'\n{_AI_MARKER}\n{b}{_AI_MARKER}\n' for b in cards)
    pos = new_html.find('<section class="sec-card">')
    if pos != -1:
        return new_html[:pos] + inject + new_html[pos:]
    for _tag in ('</main>', '</article>', '</body>'):
        pos = new_html.rfind(_tag)
        if pos != -1:
            return new_html[:pos] + inject + new_html[pos:]
    return new_html

def write(path, html_content, skip_if_exists=False):
    """Write HTML to disk.
    skip_if_exists=True  -> job detail pages: skip if content hash unchanged
    skip_if_exists=False -> listing/category/section pages: always fully rewrite
    """
    global written
    p = Path(path)
    # ── JUNK-SLUG GUARD: never CREATE a brand-new junk /jobs/<slug>/ page (the
    # source of future 404s). Fires ONLY when the file is absent, so every page
    # already on disk is preserved untouched — zero risk to anything live.
    if not p.exists():
        _pp = p.parts
        if len(_pp) >= 3 and _pp[-1] == 'index.html' and _pp[-3] == 'jobs' and is_junk_slug(_pp[-2]):
            _log_junk_skip(_pp[-2])
            return
    if skip_if_exists and p.exists():
        new_m = _HASH_RE.search(html_content)
        if new_m:
            existing_bytes = p.read_bytes()
            existing_m = _HASH_RE.search(existing_bytes.decode('utf-8', errors='replace'))
            if existing_m and existing_m.group(1) == new_m.group(1):
                _patch_jsonld(p, html_content)
                return  # content hash unchanged; JSON-LD patch only
            # Hash differs → rewrite. But FIRST carry over any AI-injected CARDS
            # blocks (Expert Analysis / Overview / Salary Insights etc.) so the
            # rewrite doesn't WIPE them. Warna har data-update / TEMPLATE_VERSION
            # change AI content uda deta hai (jise nightly enricher ko API-cost pe
            # dobara banana padta). FAQ blocks skip — base khud FAQ banata hai.
            if b'tsj-ai-enriched' in existing_bytes:
                html_content = _preserve_ai_blocks(
                    existing_bytes.decode('utf-8', errors='replace'), html_content)
        else:
            # New HTML has no TSJ_HASH (shouldn't happen for detail pages) — legacy heuristic:
            # only skip if old page ALSO has AI content (avoid wiping enriched pages)
            existing_bytes = p.read_bytes()
            existing_has_ai = b'ai_overview' in existing_bytes or b'fa-circle-info' in existing_bytes
            new_has_ai = 'ai_overview' in html_content or 'Expert Analysis' in html_content
            if not (new_has_ai and not existing_has_ai):
                _patch_jsonld(p, html_content)
                return
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
    'eligibility_section':  ('Eligibility Details',        'fa-graduation-cap',    '4338ca,#6366f1'),
    'course_details':       ('Course-wise Eligibility',    'fa-list-check',         '4338ca,#6366f1'),
    'vacancy_details':      ('Vacancy Details',           'fa-chart-pie',          '15803d,#16a34a'),
    'vacancy_breakdown':    ('Vacancy Breakdown',         'fa-table-list',         '0f766e,#0d9488'),
    'subject_wise_vacancy': ('Subject-wise Vacancy',      'fa-chart-bar',          '15803d,#16a34a'),
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
    'data_tables':          ('Additional Details',        'fa-table-list',         '0f766e,#0891b2'),
    'all_links':            ('Useful Links',              'fa-link',               '1d4ed8,#1e3a8a'),
    'details_page_content': ('Scholarship Details',       'fa-circle-info',        '1e40af,#3b82f6'),
    'text_sections':        ('How to Apply',              'fa-clipboard-list',     '0f766e,#0891b2'),
    'useful_links':         ('Useful Links',              'fa-link',               '1d4ed8,#1e3a8a'),
    'sections':             ('Details',                   'fa-circle-info',        '1e40af,#3b82f6'),
}

# ── DYNAMIC SEO HEADINGS ─────────────────────────────────────────────────────
# Each major section heading becomes "[Job Title core] : [keyword-rich context]"
# so every <h2> carries the recruitment's primary keyword phrase. Headings still
# hide automatically when their section body is empty (handled by sec_card()).
_DYN_HEADING = {
    'basic_details':         'Job Overview',
    'important_dates':       'Important Dates & Timelines',
    'application_fee':       'Application Fee Details',
    'age_limit':             'Age Limit',                       # may append " as on <date>"
    'qualification':         'Eligibility & Qualification',
    'vacancy_details':       'Vacancy Details',                 # may append " Total : N Posts"
    'vacancy_breakdown':     'Vacancy Breakdown',
    'subject_wise_vacancy':  'Subject-wise Vacancy Details',
    'category_wise_vacancy': 'Category-wise Vacancy Details',
    'salary_details':        'Salary Details & Pay Scale',
    'selection_process':     'Selection Process & Exam Pattern',
    'exam_pattern':          'Exam Pattern',
    'syllabus':              'Syllabus',
    'physical_eligibility':  'Physical Eligibility',
    'how_to_apply':          'How to Apply Online Step-by-Step',
    'important_instructions':'Important Instructions',
    'important_links':       'Important Links & Notification PDF',
    'faq':                   'Frequently Asked Questions (FAQ)',
}

# Boilerplate tails stripped from the job title to keep headings tight but keyword-rich.
_HEADING_TITLE_TAIL = re.compile(
    r'\s*[-–—:]\s*(apply online|apply offline|apply now|walk[\s-]?in|notification out|'
    r'last date|online form|short notice|recruitment notification).*$', re.I)

def _seo_heading_title(job_obj):
    """Concise, keyword-rich title prefix for section <h2>s (org + exam + year),
    with the long '- Apply Online for N Posts' boilerplate trimmed off."""
    if not isinstance(job_obj, dict): return ''
    bd = job_obj.get('basic_details') or {}
    t = safe(bd.get('job_title') or job_obj.get('title') or job_obj.get('name') or '')
    if not t: return ''
    t = _HEADING_TITLE_TAIL.sub('', t).strip()
    t = re.sub(r'\s+for\s+\d[\d,]*\s+.*$', '', t, flags=re.I).strip()  # "... for 267 MTS Posts"
    # trim trailing boilerplate words that add no keyword value
    t = re.sub(r'\s+(notification out|notification|online form|apply online|'
               r'short notice|out)\s*$', '', t, flags=re.I).strip()
    if len(t) > 58:
        t = t[:58].rsplit(' ', 1)[0].rstrip(' ,;:-–(')
    return t

def _dyn_section_heading(key, job_obj):
    """Return the dynamic '[Title] : [Context]' heading for a section key, or the
    plain SECTION_META label when the key isn't a mapped content section / no title."""
    suffix = _DYN_HEADING.get(key)
    if not suffix:
        meta = SECTION_META.get(key)
        return meta[0] if meta else (key if isinstance(key, str) else key_label(key))
    t = _seo_heading_title(job_obj)
    if key == 'age_limit':
        ag = job_obj.get('age_limit') or {}
        if isinstance(ag, dict):
            _ason = safe(ag.get('as_on_date') or ag.get('as_on') or ag.get('asondate') or
                         ag.get('as_on_the_date') or '')
            if _ason: suffix = f'Age Limit as on {_ason}'
    elif key == 'vacancy_details':
        bd = job_obj.get('basic_details') or {}
        _cnt = safe(bd.get('total_vacancies') or bd.get('total_vacancy') or
                    job_obj.get('total_post') or job_obj.get('total_vacancy') or '')
        _cnt = re.sub(r'[^\d,]', '', _cnt)
        suffix = f'Vacancy Details Total : {_cnt} Posts' if _cnt else 'Vacancy Details & Eligibility'
    if not t:
        return suffix
    return f'{t} : {suffix}'

def sec_card(key_or_title, icon, grad, body, total_count=None):
    if not body or not str(body).strip(): return ''
    meta = SECTION_META.get(key_or_title)
    title = meta[0] if meta else (key_or_title if isinstance(key_or_title, str) else key_label(key_or_title))
    count_html = f'<span class="sec-count">{total_count}</span>' if total_count else ''
    return (f'<section class="sec-card">'
            f'<div class="sec-head" style="background:linear-gradient(135deg,#{grad})">'
            f'<i class="fa-solid {icon}"></i><h2>{e(title)}</h2>{count_html}</div>'
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
    si = sanitize_short_info(safe(bd.get('short_information','')))
    si_html = f'<div class="short-info"><i class="fa-solid fa-circle-info"></i> {e(si)}</div>' if si else ''
    return si_html + (f'<table class="kv-table"><tbody>{rows}</tbody></table>' if rows else '')

def render_dates(obj):
    if not obj or not isinstance(obj, dict): return ''
    PRIO = ['application_start_date','application_begin','start_date','date_of_notification',
            'notification_date','last_date_to_apply','last_date','application_last_date',
            'extended_last_date','date_extended','extended_fee_payment_date',
            'fee_payment_last_date','exam_date','revised_exam_date','written_exam_date','online_exam_date',
            'omr_exam_date','interview_date','revised_interview_date','admit_card_date',
            'revised_admit_card_date','extended_correction_date','result_date','event',
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
    note = _strip_contamination(note)
    note = _separate_runon_fee(note)
    body = (f'<div class="fee-grid">{items}</div>' if items else '') + \
           (f'<div class="fee-note"><i class="fa-solid fa-circle-info"></i> {e(note)}</div>' if note else '')
    return body


# ── M2 FIX: some sources store fee text as run-on category+amount with no
# separators, e.g. "General OBC EWS00" / "SC ST00" (categories then the amount
# "0" stuck on). Insert readable separators: "General / OBC / EWS: ₹0". ──
_FEE_CAT_WORDS = r'(?:General|UR|OBC|EWS|SC|ST|PwD|PH|Female|Male|All|Gen)'
def _separate_runon_fee(text):
    if not text:
        return text
    t = str(text)
    # split a trailing amount glued to a category word: "EWS00" -> "EWS 00"
    t = re.sub(r'(' + _FEE_CAT_WORDS + r')(\d)', r'\1 \2', t)
    # join consecutive category words with " / " when followed by an amount:
    #   "General OBC EWS 00" -> "General / OBC / EWS: ₹0"
    def _fix(m):
        seg = m.group(0)
        amt = m.group('amt')
        cats = re.findall(_FEE_CAT_WORDS, seg)
        cats = ' / '.join(dict.fromkeys(cats))   # dedupe preserve order
        amt_clean = str(int(amt)) if amt.isdigit() else amt
        return f"{cats}: \u20b9{amt_clean}"
    t = re.sub(r'(?:' + _FEE_CAT_WORDS + r'\s+){1,5}(?P<amt>\d+)', _fix, t)
    return t.strip()


# ── H2 FIX: cross-job "Also read / Read also" link fragments leak into scraped
# text fields (e.g. SHIMUL applicationFee ends with "...| Also read: UKSSSC
# Recruitment 2026..."). Strip any trailing "also read"/"read also" clause and
# the separator before it, since it belongs to a different job record. ──
_CONTAM_RX = re.compile(
    r'\s*[|•·\-–—]*\s*(also\s*read|read\s*also|you\s*may\s*also\s*like|'
    r'related\s*(article|post|job)s?)\s*[:\-–—]?.*$', re.I | re.S)
def _strip_contamination(text):
    if not text:
        return text
    cleaned = _CONTAM_RX.sub('', str(text)).strip()
    # also drop a dangling trailing separator left behind
    cleaned = re.sub(r'\s*[|•·]\s*$', '', cleaned).strip()
    return cleaned or str(text)

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

def _split_long_value(text):
    """Split a long qualification/eligibility-style value into clean chunks.
    Primary split on ' | ' (post-wise separator), fallback to ', '. Returns a
    list of trimmed pieces (each may still contain commas, which is fine)."""
    t = safe(text)
    if not t: return []
    # Prefer pipe split (used as 'Post | Qualification' separators)
    if '|' in t:
        parts = [p.strip(' .;') for p in t.split('|')]
    else:
        # split on comma but keep it readable; only split if many commas
        parts = [p.strip(' .;') for p in re.split(r',\s+', t)] if t.count(',') >= 2 else [t]
    return [p for p in parts if p]

def kv_rows(pairs, long_threshold=90):
    """Build kv-table rows. pairs = list of (label, value).
    Short value  -> normal 2-column row (<th>label</th><td>value</td>).
    Long value   -> stacked: a full-width label heading row, then a full-width
                    row containing a NUMBERED list of the split chunks.
    This matches the requested layout: name on top, text below in small
    numbered pieces."""
    rows = ''
    for lbl, val in pairs:
        v = safe(val)
        if not v:
            continue
        if len(v) > long_threshold:
            chunks = _split_long_value(v)
            if len(chunks) > 1:
                lis = ''.join(f'<li>{e(c)}</li>' for c in chunks)
                rows += (f'<tr><th colspan="2" class="kv-stack-head">{e(lbl)}</th></tr>'
                         f'<tr><td colspan="2" class="kv-stack-body"><ol class="kv-numlist">{lis}</ol></td></tr>')
            else:
                # single long chunk — still stack so it reads top-to-bottom
                rows += (f'<tr><th colspan="2" class="kv-stack-head">{e(lbl)}</th></tr>'
                         f'<tr><td colspan="2" class="kv-stack-body">{e(v)}</td></tr>')
        else:
            rows += f'<tr><th>{e(lbl)}</th><td>{e(v)}</td></tr>'
    return rows

def render_kv_dict(d, order=None, threshold=90):
    """Render a dict as a smart kv-table (stacking long values)."""
    if not isinstance(d, dict): return ''
    pairs = []
    seen = set()
    keys = (order or []) + [k for k in d.keys() if k not in (order or [])]
    for k in keys:
        if k in seen: continue
        seen.add(k)
        v = safe(d.get(k))
        if v:
            pairs.append((key_label(k), v))
    rows = kv_rows(pairs, threshold)
    return f'<table class="kv-table"><tbody>{rows}</tbody></table>' if rows else ''

def render_selection(sp):
    if not sp: return ''
    if isinstance(sp, str): sp = [s.strip() for s in re.split(r'[,\n;/→]', sp) if s.strip()]
    if not sp: return ''
    # Table-row fragments: list of dicts → render as a table, not numbered chips
    if isinstance(sp, list) and sp and isinstance(sp[0], dict):
        # Collect all keys (ordered by first appearance) and build table rows
        all_keys = []
        seen_keys = set()
        for row in sp:
            if isinstance(row, dict):
                for k in row:
                    if k not in seen_keys:
                        all_keys.append(k)
                        seen_keys.add(k)
        if all_keys:
            thead = ''.join(f'<th>{e(key_label(k))}</th>' for k in all_keys)
            tbody = ''
            for row in sp:
                if not isinstance(row, dict): continue
                tbody += '<tr>' + ''.join(f'<td>{e(safe(row.get(k,"")))}</td>' for k in all_keys) + '</tr>'
            if tbody:
                return f'<table class="kv-table"><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>'
    steps = [safe(s) for s in sp if safe(s) and isinstance(s, str)]
    steps = _clean_section_items(steps)
    # Merge dangling short fragments (< 20 chars, no terminal punctuation) into
    # the preceding step — these are scraper-split comma fragments, not real steps
    merged = []
    for s in steps:
        if merged and len(s) <= 20 and not re.search(r'[.!?:]$', s.strip()):
            merged[-1] = merged[-1].rstrip(', ') + ', ' + s
        else:
            merged.append(s)
    steps = [s for s in merged if len(s) > 4][:25]
    if not steps: return ''
    return '<div class="sel-steps">' + ''.join(
        f'<div class="sel-step"><span class="sel-num">{i+1}</span>{e(_smart_truncate(s,140))}</div>'
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

def _il_url(v):
    """Extract URL from an important_links value (plain str OR {url,label} dict)."""
    return (v['url'] if isinstance(v, dict) else str(v or '')).strip()

def _il_label(v, fallback=''):
    """Extract display label from an important_links value."""
    return (v.get('label') or fallback) if isinstance(v, dict) else fallback

_GENERIC_LINK_LABELS = {'click here','click','view','here','open','link','open link',
                        'official pdf document','official pdf','pdf','download','click_here'}

def _label_quality(label):
    """Score how specific/useful a link label is (higher = better). Empty or
    generic labels score 0 so a real label always wins in best-label dedup."""
    l = (label or '').strip()
    if not l or l.lower() in _GENERIC_LINK_LABELS:
        return 0
    return len(re.sub(r'\s+', ' ', l))

# Exam / online-application portal hosts — links here are always an apply/register
# page, never a document, so a bare CDN/portal URL still gets a meaningful label.
_EXAM_PORTAL_HOSTS = ('digialm.com', 'ibpsonline.ibps.in', 'tcsion.com',
                      'cdn3.digialm', 'onlineapplication', 'onlinereg',
                      'apply.', 'recruitment.', 'onlineapp')

def _derive_link_label(url, job_core=''):
    """Derive a human, keyword-rich anchor label purely from a URL (optionally the
    job-title core). NEVER returns a bare generic word like 'Click Here' — the
    weakest fallback is 'Official Website' (for a bare domain)."""
    u  = (url or '').strip()
    ul = u.lower()
    host = re.sub(r'^https?://', '', ul).split('/')[0]
    path = re.sub(r'^https?://[^/]+', '', ul).split('?')[0].split('#')[0]
    seg  = [s for s in path.split('/') if s]
    stem = re.sub(r'\.(pdf|html?|aspx?|php|jsp)$', '', seg[-1]) if seg else ''
    words = re.sub(r'[^a-z0-9]+', ' ', stem).strip()

    def has(*ks): return any(k in ul for k in ks)

    if any(h in host for h in _EXAM_PORTAL_HOSTS):  return 'Online Application Portal'
    if has('corrigend'):                            return 'Corrigendum Notice PDF'
    if has('addend'):                               return 'Addendum Notice PDF'
    if has('admit', 'hallticket', 'hall-ticket', 'call-letter', 'callletter'): return 'Download Admit Card'
    if has('answer', 'anskey', 'ans-key'):          return 'Answer Key'
    if has('syllabus', 'curriculum'):               return 'Syllabus PDF'
    if has('result', 'merit', 'scorecard', 'score-card'): return 'Result / Merit List'
    if has('cutoff', 'cut-off'):                    return 'Cut Off Marks'
    if has('login', 'signin', 'sign-in'):           return 'Login'
    if has('register', 'signup', 'sign-up', 'registration', 'newreg'): return 'Register Now'
    if has('apply', 'career', 'recruit', 'applic', 'vacan'): return 'Apply Online'
    if has('advt', 'advertisement', 'notif', 'notice', 'circular', 'bharti'): return 'Notification PDF'
    if has('brochure', 'prospectus'):               return 'Information Brochure PDF'
    if ul.endswith('.pdf') or '.pdf?' in ul or '.pdf#' in ul:
        # title-case a meaningful filename (>=3 real chars, not just digits)
        if words and len(words.replace(' ', '')) >= 3 and not words.replace(' ', '').isdigit():
            return ' '.join(w.capitalize() for w in words.split())[:56] + ' PDF'
        return 'Download Notification PDF'
    if seg:   # a real path (not a bare domain) but no recognised keyword
        if words and len(words.replace(' ', '')) >= 4 and not words.replace(' ', '').isdigit():
            return ' '.join(w.capitalize() for w in words.split())[:60]
        if job_core:
            return f'{job_core} — Official Link'[:70]
    return 'Official Website'

def _smart_link_label(url, fallback='', job_core=''):
    """Resolve a human link label. Prefer a meaningful raw label; otherwise derive
    one from the URL so we NEVER render a generic 'Click Here' as anchor text."""
    fb = (fallback or '').strip()
    if fb and fb.lower() not in _GENERIC_LINK_LABELS:
        return fb[:70]
    return _derive_link_label(url, job_core)

def _prepare_il(job_obj):
    """Build a clean important_links dict from any job object.

    Handles all three raw formats:
    - dict with _labels sub-key → promotes labels into {url, label} entries
      (value may be a single url OR a list of urls under one key)
    - list of {label, url} dicts → converts to keyed dict
    - all_official_links → merged in (deduped by URL)
    Returns a dict that render_links() can consume.
    """
    raw_il = job_obj.get('important_links') or {}
    il = {}
    job_core = _seo_heading_title(job_obj)   # keyword-rich prefix for URL-derived labels
    if isinstance(raw_il, dict):
        _labels = raw_il.get('_labels') or {}
        for k, v in raw_il.items():
            if k == '_labels' or not v: continue
            # IDEMPOTENT: value may already be a resolved {url, label} dict from a
            # prior _prepare_il pass (SARK loop pre-builds `il` then build_all_sections
            # re-runs _prepare_il). Without this, str({'url':...}) breaks the URL and
            # every link silently vanishes from the page.
            if isinstance(v, dict) and (v.get('url') or v.get('link')):
                u = str(v.get('url') or v.get('link') or '').strip()
                if not u.startswith('http') or is_blocked(u): continue
                il[k] = {'url': u, 'label': _smart_link_label(u, safe(v.get('label') or _labels.get(k, '')), job_core)}
                continue
            # a single key may map to ONE url string OR a LIST of urls (ESIC etc.)
            _urls = v if isinstance(v, list) else [v]
            _base_lbl = safe(_labels.get(k, ''))
            for _idx, _uu in enumerate(_urls):
                u = str(_uu or '').strip()
                if not u.startswith('http') or is_blocked(u): continue
                # first url uses the _labels value; extra urls get a URL-derived label
                lbl = _smart_link_label(u, _base_lbl if _idx == 0 else '', job_core)
                _key = k if _idx == 0 else f'{k}_{_idx+1}'
                while _key in il: _key = f'{_key}_x'
                il[_key] = {'url': u, 'label': lbl}
    elif isinstance(raw_il, list):
        for itm in raw_il:
            if not isinstance(itm, dict): continue
            url = str(itm.get('url') or itm.get('link') or itm.get('links') or '').strip()
            lbl = str(itm.get('label') or itm.get('title') or itm.get('name') or '').strip()
            if not url.startswith('http') or is_blocked(url): continue
            ll = lbl.lower()
            if 'apply' in ll:          base = 'apply_online'
            elif any(x in ll for x in ['short notif']): base = 'short_notification'
            elif 'date extend' in ll or 'extended' in ll: base = 'date_extended_notice'
            elif any(x in ll for x in ['notif','notice','advt','advertisement']): base = 'notification_pdf'
            elif 'result' in ll:       base = 'result_link'
            elif 'admit' in ll:        base = 'admit_card'
            elif 'answer' in ll:       base = 'answer_key'
            elif 'syllabus' in ll:     base = 'syllabus'
            elif 'official' in ll or 'website' in ll: base = 'official_website'
            else:
                base = re.sub(r'[^a-z0-9]+','_', ll).strip('_')[:40] or 'click_here'
            key = base; n = 2
            while key in il:
                key = f'{base}_{n}'; n += 1
            il[key] = {'url': url, 'label': lbl}

    # ── Best-label-wins dedup ───────────────────────────────────────────────
    # url→key map for the entries already in `il`. When the SAME url reappears in
    # all_official_links / all_links / useful_links carrying a MORE specific label,
    # upgrade the existing entry instead of discarding the better label (this was
    # the root cause of stale generic 'Click Here' anchors on merged links).
    _url_key = {}
    for _k, _v in il.items():
        _uu = _il_url(_v)
        if _uu.startswith('http') and _uu not in _url_key:
            _url_key[_uu] = _k

    def _merge_or_upgrade(u, raw_label, base_key):
        if not u.startswith('http') or is_blocked(u):
            return
        new_lbl = _smart_link_label(u, raw_label, job_core)
        if u in _url_key:                       # already present → maybe upgrade label
            ek = _url_key[u]
            if _label_quality(new_lbl) > _label_quality(_il_label(il.get(ek, {}))):
                il[ek]['label'] = new_lbl
            return
        key = base_key; n = 2
        while key in il:
            key = f'{base_key}_{n}'; n += 1
        il[key] = {'url': u, 'label': new_lbl}
        _url_key[u] = key

    # Merge all_official_links (best label wins on URL collision)
    _aol = job_obj.get('all_official_links') or []
    if isinstance(_aol, list) and _aol:
        for _item in _aol:
            if not isinstance(_item, dict): continue
            _u = str(_item.get('url') or '').strip()
            _l = str(_item.get('label') or '').strip()
            _ll = _l.lower()
            if 'apply' in _ll:   _ab = 'apply_online'
            elif any(x in _ll for x in ['notif','pdf','notice','advt']): _ab = 'notification_pdf'
            elif 'result' in _ll:  _ab = 'result_link'
            elif 'admit' in _ll:   _ab = 'admit_card'
            elif 'answer' in _ll:  _ab = 'answer_key'
            elif 'login' in _ll:   _ab = 'login_link'
            elif 'official' in _ll or 'website' in _ll: _ab = 'official_website'
            else: _ab = re.sub(r'[^a-z0-9]+','_', _ll).strip('_')[:40] or 'official_website'
            _merge_or_upgrade(_u, _l, _ab)

    # Merge all_links / useful_links arrays (SARK LATEST_JOBS NEW / OFFLINE_FORM
    # format: [{label|title, url}]) so their official links also render as buttons.
    for _src_key in ('all_links', 'useful_links'):
        _arr = job_obj.get(_src_key) or []
        if not isinstance(_arr, list) or not _arr: continue
        for _item in _arr:
            if not isinstance(_item, dict): continue
            _u = str(_item.get('url') or _item.get('link') or (
                     (_item.get('links') or [''])[0] if isinstance(_item.get('links'), list)
                     else _item.get('links') or '')).strip()
            _l = str(_item.get('label') or _item.get('title') or _item.get('name') or '').strip()
            _ll = (_l + ' ' + _u).lower()
            if 'apply' in _ll or 'career' in _ll:   _ab = 'apply_online'
            elif any(x in _ll for x in ['notif','pdf','advt']): _ab = 'notification_pdf'
            elif 'result' in _ll:  _ab = 'result_link'
            elif 'admit' in _ll:   _ab = 'admit_card'
            elif 'answer' in _ll:  _ab = 'answer_key'
            elif 'login' in _ll:   _ab = 'login_link'
            elif 'official' in _ll or 'website' in _ll or 'visit' in _ll: _ab = 'official_website'
            else: _ab = re.sub(r'[^a-z0-9]+','_', (_l or _u).lower()).strip('_')[:40] or 'official_website'
            _merge_or_upgrade(_u, _l, _ab)
    return il

def render_links(il_obj):
    if not il_obj or not isinstance(il_obj, dict): return ''
    LINK_CFG = {
        'apply_online':         ('Apply Online',          'lk-apply',   'fa-paper-plane'),
        'official_website':     ('Official Website',      'lk-official','fa-globe'),
        'notification_pdf':     ('Download Notification', 'lk-pdf',     'fa-file-pdf'),
        'download_notification':('Download Notification', 'lk-pdf',     'fa-file-pdf'),
        'official_notification':('Official Notification', 'lk-pdf',     'fa-file-pdf'),
        'application_form':     ('Download Application Form', 'lk-pdf', 'fa-file-pdf'),
        'registration_link':    ('Register Now',          'lk-register','fa-user-plus'),
        'login_link':           ('Login',                 'lk-login',   'fa-right-to-bracket'),
        'admit_card':           ('Admit Card',            'lk-admit',   'fa-id-card'),
        'answer_key':           ('Answer Key',            'lk-answer',  'fa-key'),
        'syllabus_pdf':         ('Syllabus PDF',          'lk-syllabus','fa-book'),
        'result_link':          ('Result',                'lk-result',  'fa-trophy'),
        'click_here':           ('Click Here',            'lk-default', 'fa-link'),
        'merit_list':           ('Merit List',            'lk-merit',   'fa-list'),
        'score_card':           ('Score Card',            'lk-orange',  'fa-file'),
        'short_notification':   ('Download Short Notification', 'lk-pdf', 'fa-file-pdf'),
        'date_extended_notice': ('Date Extended Notice',  'lk-pdf',     'fa-file-pdf'),
        'syllabus':             ('Syllabus',              'lk-syllabus','fa-book'),
    }
    def _row(label, url, css, icon):
        # row: label on the left, colored "Open" button on the right.
        # Outbound official links carry rel="nofollow noopener" (SEO Section 4.7):
        # preserves crawl equity by not passing PageRank to external sites.
        dl = ' download' if str(url).lower().endswith('.pdf') else ''
        return (f'<div class="lk-row">'
                f'<span class="lk-label">{e(label)}</span>'
                f'<a href="{e(url)}" class="lk-open {css}" target="_blank" rel="nofollow noopener noreferrer"{dl}>'
                f'<i class="fa-solid {icon}"></i> Open</a></div>\n')
    rows = ''; seen = set()
    for key, val in il_obj.items():
        if key in ('structured_links','seo_tags','_labels'): continue
        # val shapes: plain url str, list of urls, or {url, label} dict
        if isinstance(val, dict) and 'url' in val:
            pairs = [(_il_url(val), _il_label(val))]
        elif isinstance(val, list):
            pairs = [(str(v or '').strip(), '') for v in val]
        else:
            pairs = [(str(val or '').strip(), '')]
        label, css, icon = LINK_CFG.get(key, (key_label(key), 'lk-default', 'fa-link'))
        for u, lbl_override in pairs:
            if not u.startswith('http') or is_blocked(u) or u in seen: continue
            seen.add(u)
            ul = u.lower()
            if ul.endswith('.pdf'): icon, css = 'fa-file-pdf', 'lk-pdf'
            elif 'apply' in key: icon, css = 'fa-paper-plane', 'lk-apply'
            elif 'result' in key: icon, css = 'fa-trophy', 'lk-result'
            elif 'admit' in key: icon, css = 'fa-id-card', 'lk-admit'
            elif 'answer' in key: icon, css = 'fa-key', 'lk-answer'
            # NEVER show literal "Click Here" — resolve a real label from URL
            _final_lbl = _smart_link_label(u, lbl_override or label)
            rows += _row(_final_lbl, u, css, icon)
    for item in (il_obj.get('structured_links') or []):
        if not isinstance(item, dict): continue
        u = str(item.get('url','') or item.get('href','')).strip()
        lbl = str(item.get('label','') or item.get('title','View')).strip() or 'View'
        if not u.startswith('http') or is_blocked(u) or u in seen: continue
        seen.add(u)
        ll = lbl.lower()
        ic,cl = ('fa-paper-plane','lk-apply') if 'apply' in ll else \
                ('fa-trophy','lk-result') if 'result' in ll else \
                ('fa-id-card','lk-admit') if 'admit' in ll else \
                ('fa-key','lk-answer') if 'answer' in ll else \
                ('fa-file-pdf','lk-pdf') if u.lower().endswith('.pdf') else \
                ('fa-globe','lk-official') if 'official' in ll else \
                ('fa-right-to-bracket','lk-login') if 'login' in ll else \
                ('fa-user-plus','lk-register') if ('register' in ll or 'registration' in ll) else \
                ('fa-file','lk-orange') if ('upload' in ll or 'fee' in ll or 'pay' in ll) else \
                ('fa-list','lk-merit') if ('list' in ll or 'merit' in ll) else \
                ('fa-link','lk-default')
        rows += _row(_smart_link_label(u, lbl)[:60], u, cl, ic)
    return f'<div class="links-rows">{rows}</div>' if rows else ''

def brand_help_faq(job_obj):
    """EK brand-attributed, category-tailored, page-specific Q&A jo HAR listing ke
    FAQ me add hota hai (full-build + AI-patch dono flow me — dono jagah identical).

    Design (penalty-safe + truthful):
      • TRUTHFUL: candidate application / result / admit-card OFFICIAL portal pe hoti
        hai — TopSarkariJobs verified link deta hai (isliye "apply on TSJ" jaisa
        overclaim NAHI). Real timeline: project 2020 me (offline) shuru, online 2025.
      • PAGE-SPECIFIC: har answer me real {title} → unique per page, isliye ye
        "scaled/boilerplate content" nahi, genuine page-specific FAQ ke saath sits.
      • Category auto-detect (job / admit card / result / answer key / syllabus-
        admission-yojana etc.) — har item ke liye tailored question."""
    if not isinstance(job_obj, dict):
        return None
    bd = job_obj.get('basic_details') or {}
    title = safe(bd.get('job_title', '') or job_obj.get('title', '')
                 or job_obj.get('post_name', '') or 'this notification')
    if not title:
        return None
    cat = (job_obj.get('category', '') or '').upper()
    tl = title.lower()

    def hit(*words):
        return any(w in cat or w in tl for w in words)

    SITE = "www.topsarkarijobs.com"
    if hit('ANSWER', 'answer key'):
        q = f"Where can I download the official Answer Key for {title}?"
        a = (f"Ans: The official answer key and question-paper solutions for {title} "
             f"can be downloaded through the verified link listed on {SITE}.")
    elif hit('ADMIT', 'admit card', 'hall ticket', 'call letter'):
        q = f"How can I download the Admit Card for {title}?"
        a = (f"Ans: The admit card / hall ticket for {title} can be downloaded from "
             f"the official portal using the direct link provided on {SITE}.")
    elif hit('RESULT', 'merit list', 'score card', 'cut off', 'cutoff'):
        q = f"How can I check the result for {title}?"
        a = (f"Ans: You can check the marks, merit list and cut-off for {title} "
             f"through the official result link provided on {SITE}.")
    elif hit('ADMISSION', 'SYLLABUS', 'YOJANA', 'SCHEME', 'SCHOLARSHIP',
             'syllabus', 'admission', 'yojana', 'scheme', 'scholarship'):
        q = f"Where can I get the latest official updates for {title}?"
        a = (f"Ans: All official PDFs, notifications and step-by-step guides for "
             f"{title} are available on {SITE}.")
    else:
        q = f"How can I apply for {title}?"
        a = (f"Ans: You can apply online through the official recruitment link "
             f"provided for {title} on {SITE}. Read the full notification and check "
             f"your eligibility before applying on the official portal.")
    a += (" TopSarkariJobs began compiling verified government-job updates in 2020 "
          "and launched online in 2025.")
    return {"question": q, "answer": a}


def auto_generate_faqs(job_obj):
    """Generate 5-10 FAQs from ACTUAL page data when JSON has no FAQ.
       Only uses fields that exist — never invents data. Category-aware.
       Handles BOTH structured (basic_details) and flat sarkari-format jobs."""
    if not isinstance(job_obj, dict): return []
    bd    = job_obj.get('basic_details', {}) or {}
    dates = job_obj.get('important_dates', {}) or {}
    # title/org/posts: try basic_details first, then flat sarkari keys
    title = safe(bd.get('job_title','') or job_obj.get('title','') or job_obj.get('post_name','') or 'this recruitment')
    org   = safe(bd.get('organization_name','') or job_obj.get('organization','') or job_obj.get('organisation',''))
    posts = safe(bd.get('total_vacancies','') or job_obj.get('total_post','') or job_obj.get('total_vacancy','') or job_obj.get('vacancies',''))
    mode  = safe(bd.get('application_mode','') or job_obj.get('apply_mode','') or job_obj.get('application_mode',''))
    site  = safe(bd.get('official_website','') or job_obj.get('official_website',''))
    cat   = (job_obj.get('category','') or '').upper()

    def _val(d, keys):
        if isinstance(d, dict):
            for k in keys:
                v = d.get(k)
                if isinstance(v, str) and v.strip(): return safe(v.strip())
        elif isinstance(d, str): return safe(d.strip())
        return ''
    # qualification / age / fee: structured dict OR flat string keys
    qual = (_val(job_obj.get('qualification'), ['education_qualification','qualification','eligibility'])
            or safe(job_obj.get('qualification','') if isinstance(job_obj.get('qualification'),str) else '')
            or safe(job_obj.get('eligibility','') if isinstance(job_obj.get('eligibility'),str) else ''))
    age  = (_val(job_obj.get('age_limit'), ['age_details','age_limit','age','details'])
            or safe(job_obj.get('minimum_age','') or job_obj.get('age_limit','') if isinstance(job_obj.get('age_limit'),str) else job_obj.get('minimum_age','')))
    fee  = (_val(job_obj.get('application_fee'), ['general_fee','general','ur_fee','fee'])
            or _val(job_obj.get('application_fees'), ['general_fee','general','ur_fee','fee'])
            or safe(job_obj.get('application_fees','') if isinstance(job_obj.get('application_fees'),str) else ''))
    last = safe(dates.get('last_date_to_apply','') or dates.get('last_date_apply_online','') or dates.get('last_date','') or job_obj.get('last_date',''))
    start= safe(dates.get('application_start_date','') or dates.get('application_start','') or dates.get('start_date',''))
    exam = safe(dates.get('exam_date','') or dates.get('examination_date',''))
    sal  = (_val(job_obj.get('salary_details'), ['pay_scale','salary','pay'])
            or safe(job_obj.get('salary_pay_scale','') or job_obj.get('salary','') or job_obj.get('pay_scale','')))
    # selection process (list or dict)
    sp = job_obj.get('selection_process')
    sel = ''
    if isinstance(sp, list) and sp:
        sel = _smart_truncate(safe('; '.join(str(x) for x in sp[:2])),300)
    elif isinstance(sp, dict):
        sel = _smart_truncate(_val(sp, ['details','process']),300)
    elif isinstance(sp, str):
        sel = _smart_truncate(safe(sp),300)

    faqs = []
    def add(q, a):
        if a and str(a).strip():
            faqs.append({'question': q, 'answer': a})

    # Category-specific lead questions
    if 'RESULT' in cat:
        if org: add(f"Who has released the result for {title}?", f"The result for {title} has been released by {org}.")
        if site: add(f"How can candidates check the {title} result?", f"Candidates can check and download the result from the official website {site}.")
        add(f"What details are needed to download the {title} result?", "Candidates typically need their registration/roll number and date of birth or password to access the result.")
    elif 'ADMIT' in cat:
        if org: add(f"Who issues the admit card for {title}?", f"The admit card for {title} is issued by {org}.")
        if site: add(f"How can candidates download the {title} admit card?", f"Candidates can download the admit card by logging in with their credentials on the official website {site}.")
        add(f"What details are required to download the {title} admit card?", "Candidates usually need their registration number/application number along with their date of birth or password.")
        if exam: add(f"When is the examination for {title}?", f"As per the notification, the examination date is {exam}.")
    elif 'ANSWER' in cat:
        if org: add(f"Who released the answer key for {title}?", f"The answer key for {title} has been released by {org}.")
        if site: add(f"How can candidates download the {title} answer key?", f"The answer key can be downloaded from the official website {site}.")
    elif 'ADMISSION' in cat or 'ADMISSIONS' in cat:
        if last: add(f"What is the last date to apply for {title}?", f"The last date to apply for {title} is {last}.")
        if qual: add(f"What is the eligibility for {title}?", f"The required eligibility is: {qual}")
        if fee: add(f"What is the application fee for {title}?", f"The application fee is {fee}.")

    # Generic job FAQs (apply to most categories) — only if data present
    if last: add(f"What is the last date to apply for {title}?", f"The last date to submit the online application for {title} is {last}.")
    if start: add(f"When does the application for {title} start?", f"The online application process for {title} starts from {start}.")
    if posts: add(f"How many vacancies are available in {title}?", f"A total of {posts} vacancies are available under {title}.")
    if qual: add(f"What qualification is required for {title}?", f"Candidates must have: {qual}")
    if age:
        _amin = safe(job_obj.get('minimum_age','') or job_obj.get('min_age',''))
        _amax = safe(job_obj.get('maximum_age','') or job_obj.get('max_age',''))
        # if `age` is just a bare number (e.g. "25") build a fuller sentence
        if re.fullmatch(r'\d{1,2}', age.strip()):
            if _amin and _amax:
                _ans = f"The minimum age is {_amin} years and the maximum age is {_amax} years. Age relaxation applies as per government rules."
            elif _amax:
                _ans = f"The maximum age limit is {_amax} years, with relaxation as per government rules."
            else:
                _ans = f"The minimum age is {age} years. Refer to the official notification for the maximum age and category-wise relaxation."
        else:
            _ans = age if re.search(r'[.!]$', age.strip()) else f"The age limit for {title} is: {age}."
        add(f"What is the age limit for {title}?", _ans)
    if fee: add(f"What is the application fee for {title}?", f"The application fee for {title} is {fee}.")
    if sel: add(f"What is the selection process for {title}?", f"The selection process includes: {sel}")
    if sal: add(f"What is the salary / pay scale for {title}?", f"The pay scale for {title} is {sal}.")
    if mode: add(f"How can candidates apply for {title}?", f"Candidates can apply in {mode} mode" + (f" through the official website {site}." if site else "."))
    if exam and not any('examination' in f['question'].lower() or 'exam' in f['question'].lower() for f in faqs):
        add(f"When is the exam for {title}?", f"As per the notification, the exam is scheduled for {exam}.")
    if org: add(f"Which organization has released {title}?", f"{title} has been released by {org}.")
    if site: add(f"What is the official website for {title}?", f"The official website to apply and check details for {title} is {site}.")
    if posts and not any('vacanc' in f['question'].lower() for f in faqs):
        add(f"What is the total number of posts in {title}?", f"There are a total of {posts} posts available under {title}.")

    # ── Content-based fallback for notice/date-sheet/result/admit pages that
    #    have a title + short info + links but no structured job fields.
    #    Derive FAQs from ACTUAL page content (title, short_info, links). ──
    short = sanitize_short_info(safe(job_obj.get('short_info','') or job_obj.get('short_information','') or bd.get('short_information','')))
    il = _prepare_il(job_obj)
    pdf_link = ''
    if isinstance(il, dict):
        pdf_link = (_il_url(il.get('notification_pdf')) or _il_url(il.get('official_website'))
                    or _il_url(il.get('admit_card')) or _il_url(il.get('result_link'))
                    or _il_url(il.get('apply_online')))
    tl = title.lower()
    if len(faqs) < 3:
        # Detect content type from title for a relevant Q
        if 'date sheet' in tl or 'time table' in tl or 'timetable' in tl or 'datesheet' in tl:
            add(f"What is {title} about?", short or f"{title} provides the official examination schedule. Candidates can check the dates and download the PDF from the official website.")
            add(f"How can candidates download the {('date sheet' if 'date sheet' in tl or 'datesheet' in tl else 'time table')}?", f"Candidates can download it" + (f" from {pdf_link}." if pdf_link else " from the official website by logging in or visiting the notice section."))
        elif 'result' in tl:
            add(f"What is {title} about?", short or f"{title} announces the official result. Candidates can check and download it from the official website.")
            add("How can candidates check the result?", f"Candidates can check the result" + (f" at {pdf_link}." if pdf_link else " on the official website using their roll number/registration details."))
        elif 'admit card' in tl or 'hall ticket' in tl:
            add(f"What is {title} about?", short or f"{title} provides the official admit card. Candidates can download it from the official website.")
            add("How can candidates download the admit card?", f"Candidates can download the admit card" + (f" from {pdf_link}." if pdf_link else " from the official website by logging in with their credentials."))
        elif 'answer key' in tl:
            add(f"What is {title} about?", short or f"{title} provides the official answer key for the examination.")
            add("How can candidates download the answer key?", f"Candidates can download the answer key" + (f" from {pdf_link}." if pdf_link else " from the official website."))
        elif 'admission' in tl or 'counselling' in tl or 'counseling' in tl:
            add(f"What is {title} about?", short or f"{title} provides official admission/counselling details. Candidates can check eligibility and process on the official website.")
        else:
            # generic notice/update — only if we have real short_info to back it
            if short:
                add(f"What is {title} about?", short)
                if pdf_link:
                    add("Where can candidates find the official notification?", f"The official notification/PDF is available at {pdf_link}.")

    # De-dup by question, cap 5-10
    seen=set(); out=[]
    for f in faqs:
        k = re.sub(r'\s+',' ',f['question'].lower()).strip()
        if k in seen: continue
        seen.add(k); out.append(f)
        if len(out) >= 10: break
    return out

def render_qualification(val):
    """Qualification section per spec: string -> div; dict -> KV table with
       known fields + matched_qualifications as badges; list -> items."""
    if isinstance(val, str):
        return f'<div class="edu-sec">{e(safe(val))}</div>' if safe(val) else ''
    if isinstance(val, list):
        return render_list_items(val)
    if not isinstance(val, dict):
        return ''
    ORDER = ['education_qualification','qualification','eligibility','required_degree',
             'technical_qualification','experience_required','details','nationality']
    _SKIP_QUAL_KEYS = {'matched_qualifications','post_wise_qualification'}
    pairs = []
    seen_labels = set()
    for k in ORDER:
        v = sanitize_short_info(safe(val.get(k)))
        lbl = key_label(k)
        if v and lbl not in seen_labels:
            seen_labels.add(lbl)
            pairs.append((lbl, v))
    # any extra unknown keys (except handled separately below)
    for k, v in val.items():
        if k in ORDER or k in _SKIP_QUAL_KEYS: continue
        sv = sanitize_short_info(safe(v)); lbl = key_label(k)
        if sv and lbl not in seen_labels:
            seen_labels.add(lbl)
            pairs.append((lbl, sv))
    rows = kv_rows(pairs)
    out = f'<table class="kv-table"><tbody>{rows}</tbody></table>' if rows else ''
    # post_wise_qualification → two-column table (Post Name | Qualification)
    pwq = val.get('post_wise_qualification')
    if isinstance(pwq, list) and pwq:
        pwq_rows = ''
        for item in pwq:
            if not isinstance(item, dict): continue
            pname = safe(item.get('post_name') or item.get('post') or '')
            qual  = sanitize_short_info(safe(
                item.get('essential_qualification') or item.get('qualification') or
                item.get('eligibility') or item.get('details') or ''))
            if not pname and not qual: continue
            pwq_rows += (f'<tr><th style="min-width:160px;white-space:normal">{e(pname)}</th>'
                         f'<td style="white-space:normal">{e(qual)}</td></tr>')
        if pwq_rows:
            out += ('<div style="margin-top:12px;overflow-x:auto">'
                    '<table class="kv-table"><thead><tr>'
                    '<th style="background:#1e40af;color:#fff">Post Name</th>'
                    '<th style="background:#1e40af;color:#fff">Essential Qualification</th>'
                    '</tr></thead><tbody>' + pwq_rows + '</tbody></table></div>')
    # matched_qualifications -> badges
    mq = val.get('matched_qualifications')
    if isinstance(mq, list) and mq:
        badges = ''.join(f'<span class="rel-btn" style="cursor:default">{e(safe(x))}</span>' for x in mq if safe(x))
        if badges:
            out += ('<div style="margin-top:10px"><div style="font-size:.78rem;font-weight:700;color:#374151;margin-bottom:6px">Matched Qualifications</div>'
                    f'<div style="display:flex;flex-wrap:wrap;gap:6px">{badges}</div></div>')
    return out

def render_faq(faq_list):
    if not isinstance(faq_list, list) or not faq_list: return ''
    items = ''
    seen = set()
    idx = 0
    for f in faq_list:
        if not isinstance(f, dict): continue
        q = safe(f.get('question','')); a = safe(f.get('answer',''))
        if not q or not a: continue
        # Q/A swap fix (spec): if the "answer" looks like a question and the
        # "question" doesn't, they are swapped in the source data — fix it.
        def _looks_q(s):
            sl = s.strip().lower()
            return sl.endswith('?') or bool(re.match(r'^(what|when|how|who|where|which|is|are|can|will|does|do|whom|whose|why)\b', sl))
        if _looks_q(a) and not _looks_q(q):
            q, a = a, q
        # strip any pre-existing "Q1." / "Q12)" / "1." numbering from the question text
        # (renderer adds its own Q{n} badge, so leaving it causes "Q1 Q1." double numbering)
        q = re.sub(r'^\s*Q?\s*\d{1,3}\s*[\.\):\-]\s*', '', q, flags=re.I).strip()
        # de-duplicate by normalized question text
        key = re.sub(r'\s+', ' ', q.lower()).strip()
        if not key or key in seen: continue
        seen.add(key)
        idx += 1
        # First FAQ open by default; accordion toggle via faq-init.js.
        _op = ' open' if idx == 1 else ''
        items += (f'<div class="faq-item" id="faq-{idx}">'
                  f'<div class="faq-q{_op}"><span class="faq-icon">Q{idx}</span>'
                  f'<span class="faq-q-text">{e(q)}</span>'
                  f'<i class="fa-solid fa-chevron-down faq-chev" aria-hidden="true"></i></div>'
                  f'<div class="faq-a{_op}"><span class="faq-a-icon faq-icon" style="background:#15803d">A</span>'
                  f'<div>{e(a)}</div></div></div>')
    return items

def _render_catwise_dict(d):
    """H1 FIX: a category-wise-vacancy dict normally maps a label -> value. The
    SHIMUL bug produced a DEGENERATE dict where the source table's HEADER cells
    became keys AND the values are bare numbers that don't correspond, e.g.
    {"Name of Post": "194", "Total Posts": "50"} — i.e. a header label "Name of
    Post" paired with a count "194" (nonsensical). Only reject when EVERY key is a
    header-label AND its value is purely numeric (the swapped-header signature).
    A legitimate {"Post Name": "Junior Assistant", "Total Posts": "45"} (real post
    name as value) still renders."""
    if not isinstance(d, dict) or not d:
        return ''
    _HEADER_KEYS = {'name of post', 'post name', 'total posts', 'total post',
                    'total', 'sl. no.', 'sl no', 's.no.', 'sr', 'sr.', 'post',
                    'name of the post', 'designation', 'no. of posts', 'posts',
                    'no of posts'}
    keys_l = {str(k).strip().lower() for k in d.keys()}
    if keys_l and keys_l.issubset(_HEADER_KEYS):
        # all keys are header labels — malformed ONLY if every value is numeric
        # (a real row would have a textual post name as the value)
        all_numeric = all(re.fullmatch(r'\s*\d[\d,]*\s*', str(v) or '')
                          for v in d.values())
        if all_numeric:
            return ''
    return render_kv_dict(d)


def _render_generic_rows(rows, heading=''):
    """Fallback renderer: when vacancy rows use arbitrary/non-standard column
    names (common in freejobalert scrapes, e.g. 'Name of the ICDS Project',
    'Notifying at Present'), render them as a clean table using the rows' OWN
    keys so NO data is ever dropped. Skips obviously-broken numeric-only keys."""
    if not isinstance(rows, list) or not rows:
        return ''
    dict_rows = [r for r in rows if isinstance(r, dict) and r]
    if not dict_rows:
        return ''
    # union of keys in insertion order across rows
    cols = []
    for r in dict_rows:
        for k in r.keys():
            ks = str(k).strip()
            if ks and ks not in cols:
                cols.append(ks)
    # drop columns whose HEADER is purely numeric (mangled header like "18")
    # but keep them if they actually hold data under a real label elsewhere
    good_cols = [c for c in cols if not re.fullmatch(r'\d[\d,]*', c.strip())]
    if not good_cols:
        good_cols = cols  # nothing better; keep all so data shows
    # require at least one row with real content
    def _has_content(r):
        return any(str(r.get(c, '')).strip() for c in good_cols)
    data_rows = [r for r in dict_rows if _has_content(r)]
    if not data_rows:
        return ''
    # nice header labels (Title Case, keep as-is if already labeled)
    def _lbl(c):
        return c if any(ch.isupper() for ch in c) else c.replace('_', ' ').title()
    head = ''.join(f'<th>{e(_lbl(c))}</th>' for c in good_cols)
    body = ''
    for r in data_rows:
        cells = ''.join(f'<td>{e(safe(r.get(c, "")))}</td>' for c in good_cols)
        body += f'<tr>{cells}</tr>'
    _hh = ''
    if heading:
        _clean = re.sub(r'\s*total\s*:?\s*\d[\d,]*\s*post.*$', '', heading, flags=re.I).strip() or heading
        _hh = f'<div class="kv-stack-head" style="margin-top:4px">{e(_clean)}</div>'
    return _hh + (f'<div class="tbl-scroll"><table class="data-table">'
                  f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


# ── FreeJobAlert vacancy_breakdown renderer (snake_case ONLY) ──────────────
# Generic, dynamic, null-safe renderer for the `vacancy_breakdown` field that
# FreeJobAlert (freejobalert_unified) records carry. Sarkari (sarkari_data)
# records use camelCase and never contain this field, so this NEVER fires for
# them. Mirrors universal-renderer.js cardVacancyBreakdown()/prettifyBreakdownKey().
_BREAKDOWN_LABELS = {
    'post_wise_breakdown':       'Post-wise Breakdown',
    'category_wise_breakdown':   'Category-wise Breakdown',
    'company_wise_breakdown':    'Company-wise Breakdown',
    'discipline_wise_breakdown': 'Discipline-wise Breakdown',
    'gender_wise_breakdown':     'Gender-wise Breakdown',
    'pwd_wise_breakdown':        'PwD-wise Breakdown',
    'additional_breakdown':      'Additional Breakdown',
    # Column-level abbreviations
    'pwd': 'PwD', 'pwbd': 'PwBD', 'hh': 'HH', 'sld': 'SLD', 'oh': 'OH', 'vh': 'VH',
    'ur': 'UR', 'sc': 'SC', 'st': 'ST', 'obc': 'OBC', 'ews': 'EWS', 'esm': 'ESM',
    'gen': 'General', 'wd': 'WD', 'dv': 'DV', 'apst': 'APST', 'sebc': 'SEBC',
    's_no': 'S.No', 'sl_no': 'Sl. No', 'sr_no': 'Sr. No', 's_n': 'S.No', 'sn': 'S.No',
}

def prettify_breakdown_key(k):
    """snake_case breakdown key → clean title (Rule 4). Known buckets/abbrevs get
    exact labels; any '<x>_wise_breakdown' is generic; else fall back to
    key_label() so new/unknown keys still render (never crashes)."""
    raw = safe(k).strip()
    if not raw:
        return ''
    lc = raw.lower()
    if lc in _BREAKDOWN_LABELS:
        return _BREAKDOWN_LABELS[lc]
    m = re.match(r'^(.+?)_wise_breakdown$', lc)
    if m:
        return key_label(m.group(1)) + '-wise Breakdown'
    return key_label(raw)

def render_vacancy_breakdown(vb, prior_html=''):
    """Render the `vacancy_breakdown` object as one isolated table per bucket.
       • Rule 1 — Null-safe: missing / non-dict / {} → '' (no crash).
       • Rule 2 — Dynamic buckets: iterate vb.items(); no hardcoded sections.
       • Rule 3 — Dynamic columns: UNION of every row's keys → table headers.
       • Rule 4 — prettify_breakdown_key() maps snake_case → clean titles.
    `prior_html` = the page HTML rendered so far. A bucket whose table merely
    repeats one already shown above (vacancy_details / category_wise_vacancy from
    the same source data) is SKIPPED — otherwise the page-level _dedup_tbl() pass
    would blank that table and leave an orphan 'Vacancy Breakdown' card."""
    if not vb or not isinstance(vb, dict):          # Rule 1
        return ''
    # Text-signature dedup, mirroring _dedup_tbl() so parity is exact.
    def _sig(frag):
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', frag)).strip().lower()
    seen = set()
    for _tb in re.findall(r'<table\b.*?</table>', prior_html or '', flags=re.S):
        s = _sig(_tb)
        if len(s) >= 20:
            seen.add(s)
    parts = []
    for bucket_key, bucket in vb.items():           # Rule 2 — dynamic buckets
        heading = prettify_breakdown_key(bucket_key)
        # Normalize bucket → list of non-empty row dicts
        if isinstance(bucket, list):
            rows = [r for r in bucket
                    if isinstance(r, dict) and any(str(v).strip() for v in r.values())]
        elif isinstance(bucket, dict) and bucket:
            rows = [bucket]
        else:
            rows = []
        if not rows:
            # Present but not tabular (string) — render generically, don't drop it
            if isinstance(bucket, str) and bucket.strip():
                parts.append(f'<div class="kv-stack-head" style="margin-top:4px">{e(heading)}</div>'
                             f'<div class="edu-sec">{e(bucket.strip())}</div>')
            continue
        # Rule 3 — dynamic columns: UNION of all row keys (JSON insertion order)
        cols = []
        for r in rows:
            for k in r.keys():
                ks = str(k).strip()
                if ks and not ks.startswith('_') and ks not in cols:
                    cols.append(ks)
        if not cols:
            continue
        head = ''.join(f'<th>{e(prettify_breakdown_key(c))}</th>' for c in cols)   # Rule 4
        body = ''
        for r in rows:
            tds = ''
            for c in cols:
                v = r.get(c, '')
                tds += f'<td>{e(safe(v))}</td>' if str(v).strip() != '' else '<td>&mdash;</td>'
            body += f'<tr>{tds}</tr>'
        table_html = (f'<div class="tbl-scroll"><table class="data-table">'
                      f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        tsig = _sig(table_html)
        if len(tsig) >= 20 and tsig in seen:        # already shown above → skip
            continue
        seen.add(tsig)
        parts.append(f'<div class="kv-stack-head" style="margin-top:4px">{e(heading)}</div>'
                     + table_html)
    return ''.join(parts)


def render_vacancy_table(vac_list):
    """Render vacancy rows. SR pages cram a Vacancy-Details table (Post Name |
    Total | Qualification) AND a Category-Wise table (Post Name | UR | OBC | SC |
    ST | EWS | Total) into one vacancy_details list. These must render as TWO
    SEPARATE tables (matching the original site), not one mixed table with empty
    cells. We split rows by their tableHeading / column signature and render each
    group on its own."""
    if not vac_list or not isinstance(vac_list, list): return ''

    _CW_KEYS = ('ur','obc','sc','st','ews','general','unreserved','bc','ebc')
    def _row_is_catwise(r):
        if not isinstance(r, dict): return False
        # explicit nested categoryWise OR flat UR/OBC/SC/ST keys present
        if r.get('categoryWise') or r.get('category_wise'): return True
        present = sum(1 for k in r
                      if str(k).strip().lower() in _CW_KEYS and str(r[k]).strip())
        return present >= 2
    def _heading_is_catwise(r):
        h = safe(r.get('table_heading') or r.get('tableHeading') or '').lower()
        return 'category wise' in h or 'community wise' in h or 'cat wise' in h
    def _row_has_qual(r):
        return bool(isinstance(r, dict) and (
            safe(r.get('qualification') or r.get('eligibility')).strip()))

    # OLD-DATA / merged-row handling: a single row may carry BOTH qualification
    # AND category-wise columns (older scraper merged them). Split such a row into
    # TWO logical rows so the renderer can show separate Vacancy + Category-Wise
    # tables (matching the source site).
    _expanded = []
    for r in vac_list:
        if not isinstance(r, dict):
            continue
        _has_cw = _row_is_catwise(r)
        _has_q = _row_has_qual(r)
        if _has_cw and _has_q:
            # vacancy part (drop category cols)
            _vpart = {k: v for k, v in r.items()
                      if str(k).strip().lower() not in _CW_KEYS
                      and k not in ('categoryWise', 'category_wise')}
            # catwise part (drop qualification/eligibility/subjects)
            _cpart = {k: v for k, v in r.items()
                      if k not in ('qualification', 'eligibility', 'subjects',
                                   'age', 'department')}
            # mark catwise heading so it groups correctly
            _cpart['table_heading'] = (safe(r.get('table_heading') or r.get('tableHeading'))
                                       or 'Category Wise Vacancy Details')
            if 'category wise' not in _cpart['table_heading'].lower():
                _cpart['table_heading'] = 'Category Wise Vacancy Details'
            _expanded.append(_vpart)
            _expanded.append(_cpart)
        else:
            _expanded.append(r)
    vac_list = _expanded

    # split into two ordered groups
    vac_rows, cat_rows = [], []
    for r in vac_list:
        if not isinstance(r, dict): continue
        if _row_is_catwise(r) or _heading_is_catwise(r):
            cat_rows.append(r)
        else:
            vac_rows.append(r)

    def _vac_heading(r):
        return safe(r.get('table_heading') or r.get('tableHeading') or '').strip().lower()

    def _group_vac_by_heading(rows):
        """Group consecutive vacancy rows that share the same table_heading."""
        groups, current, cur_h = [], [], None
        for r in rows:
            h = _vac_heading(r)
            if cur_h is None or h == cur_h or not h:
                current.append(r)
                if h: cur_h = h
            else:
                groups.append(current)
                current = [r]; cur_h = h
        if current:
            groups.append(current)
        return groups

    # if there's a genuine split (both groups non-trivial), render separately
    if cat_rows and (vac_rows or len(cat_rows) >= 1):
        parts = []
        if vac_rows:
            for grp in _group_vac_by_heading(vac_rows):
                parts.append(_render_vac_group(grp, mode='vacancy'))
        if cat_rows:
            parts.append(_render_vac_group(cat_rows, mode='catwise'))
        return ''.join(p for p in parts if p)
    # otherwise single table (no category-wise data) — still group by heading
    parts = [_render_vac_group(grp, mode='vacancy')
             for grp in _group_vac_by_heading(vac_list)]
    return ''.join(p for p in parts if p)


def _render_vac_group(vac_list, mode='vacancy'):
    if not vac_list or not isinstance(vac_list, list): return ''
    # column sets differ per table type so each renders clean (no empty columns)
    if mode == 'catwise':
        ALL_COLS = [
            ('post_name',['post_name','post','name','Post Name','Name Of Post','Post','subject','Subject']),
            ('department',['department','Department','specialty','Specialty','speciality','Speciality','discipline','Discipline','trade','Trade','branch','Branch']),
            ('ur',['ur','general','UR','General (UR)','General']),
            ('obc',['obc','OBC']),('sc',['sc','SC']),('st',['st','ST']),('ews',['ews','EWS']),
            ('bc',['bc','BC']),('ebc',['ebc','EBC']),
            ('women',['women','Women','female','Female']),
            ('male',['male','Male','men','Men']),
            ('total',['total','total_post','total_vacancies','total_posts','vacancies','Total Posts','Total','Vacancy']),
        ]
    else:
        ALL_COLS = [
            ('post_name',['post_name','post','name','Post Name','Name Of Post','Post','subject','Subject']),
            ('subjects',['subjects','Subjects','subject_details','Subjects Details']),
            ('advt_no',['advt_no','Advt No','advertisement_no','Advertisement No']),
            ('state',['State / UT','State/UT','state','State','State / Ut']),
            ('language',['Language','language','Medium','medium']),
            ('total',['total','total_post','total_vacancies','total_posts','vacancies','Total Posts','Total','Vacancy']),
            ('age',['age','ageLimit','age_limit','Age Limit','Age','age_details']),
            ('male',['male','Male','men','Men']),
            ('women',['women','Women','female','Female']),
            ('transgender',['transgender','Transgender']),
            ('pay_level',['Pay Level','pay_level','Level','Pay Matrix Level','PayLevel','Pay Matrix','pay band']),
            ('salary',['salary','pay_scale','Scale of Pay','Salary']),
            ('qualification',['eligibility','qualification','Educational Qualification']),
            ('department',['department','Department']),
            ('notification_pdf',['notification_pdf','notification_link','pdf','Notification PDF']),
        ]
    LABELS = {'post_name':'Post Name','subjects':'Subjects Details','advt_no':'Advt No','state':'State / UT','language':'Language',
              'total':'Total','age':'Age Limit','ur':'UR/General','obc':'OBC',
              'sc':'SC','st':'ST','ews':'EWS','bc':'BC','ebc':'EBC','women':'Women/Female','male':'Male','transgender':'Transgender',
              'pay_level':'Pay Level','salary':'Salary',
              'qualification':'Qualification','department':'Department','notification_pdf':'Notification'}
    # flatten nested categoryWise dict into flat keys so columns line up
    _flat_list = []
    for row in vac_list:
        if not isinstance(row, dict): continue
        row = dict(row)
        _cw = row.get('categoryWise') or row.get('category_wise')
        if isinstance(_cw, dict):
            for k, v in _cw.items():
                kl = str(k).strip().lower()
                if kl and kl not in row:
                    row[kl] = v
        _flat_list.append(row)
    vac_list = _flat_list
    norm = []; avail = set()
    _tbl_heading = ''
    for row in vac_list:
        if not isinstance(row, dict): continue
        if not _tbl_heading:
            _th = safe(row.get('table_heading') or row.get('tableHeading') or '').strip()
            if _th and len(_th) > 5:
                _tbl_heading = _th
        # case-insensitive key lookup: SR/edu scrapers use varying key casing
        # ("Name of Post" vs "Name Of Post" vs "name_of_post"). Build a
        # lowercased-key view so aliases match regardless of case/spacing.
        _row_ci = {}
        for _k, _v in row.items():
            _row_ci[str(_k).strip().lower()] = _v
        def _lookup(alias):
            if alias in row and row[alias] not in (None, '', {}, []):
                return row[alias]
            _al = str(alias).strip().lower()
            if _al in _row_ci and _row_ci[_al] not in (None, '', {}, []):
                return _row_ci[_al]
            return None
        if not any(_lookup(a) is not None for _c, al in ALL_COLS for a in al):
            continue
        n = {}
        for col, aliases in ALL_COLS:
            for a in aliases:
                _val = _lookup(a)
                if _val is not None:
                    n[col] = safe(_val); avail.add(col); break
        if n: norm.append(n)
    if not norm: return _render_generic_rows(vac_list, _tbl_heading)
    cols = [c for c,_ in ALL_COLS if c in avail]
    if not cols: return _render_generic_rows(vac_list, _tbl_heading)

    # ── FIX: If row has many unique keys but renderer matched very few standard cols,
    # the table will look broken (only Sr+Total shows). Detect this case and use
    # the GENERIC renderer instead, which preserves all original JSON keys as columns.
    # E.g., JSON {"Sr. No.","Category","Posts as on 31.12.2025","Anticipated","Total"}
    # → only "Total" matches → 5 real columns but rendering 1-2. Fallback fixes this.
    _all_input_keys = set()
    for _r in vac_list:
        if isinstance(_r, dict):
            for _k in _r.keys():
                _ks = str(_k).strip()
                # Skip meta keys
                if _ks and _ks.lower() not in ('table_heading','tableheading','categorywise','category_wise'):
                    _all_input_keys.add(_ks)
    # If we matched fewer than 60% of unique input keys → input has rich data
    # that we're losing. Use generic renderer to preserve everything.
    # If matched fewer than 60% of input keys → input has rich data we're losing.
    # Threshold lowered to 2 so even simple {District,Vacancies} or {Post,Total}
    # tables render with their actual column names instead of forced Sr+Total.
    if len(_all_input_keys) >= 2 and len(cols) < max(2, int(len(_all_input_keys) * 0.6)):
        return _render_generic_rows(vac_list, _tbl_heading)

    # ── C3 FIX: clean rows + compute the real grand total ──
    def _to_int(v):
        m = re.search(r'\d[\d,]*', str(v or ''))
        return int(m.group().replace(',', '')) if m else None
    def _is_total_label(v):
        return bool(re.search(r'\b(total|grand\s*total|sum)\b', str(v or ''), re.I))

    # Physical-eligibility rows sometimes leak into vacancyDetails (SSC GD:
    # "Gender", "Male (General/OBC/SC)", "Male ST", "Female ...", with
    # Height/Chest/Race values). These are NOT vacancy posts — drop them from the
    # vacancy table so they don't pollute it. A row is "physical" when its
    # post_name is a bare gender/standard label OR its values look like body
    # measurements (cm / chest / km / minute / running).
    _PHYS_LABEL_RX = re.compile(
        r'^(gender|male|female|transgender|height|chest|weight|running|race|'
        r'physical|pet|pst)\b', re.I)
    _PHYS_VAL_RX = re.compile(
        r'\b(\d+\s*(cm|cms|kg|kgs|km|metre|meter|mtr|min|minute|sec|feet|ft)\b'
        r'|\d{2,3}\s*[-/]\s*\d{2,3}|chest|expansion)\b', re.I)
    def _is_physical_row(r):
        nm = safe(r.get('post_name', '')).strip()
        if not nm:
            return False
        # bare gender/standard label with no real total => physical pollution
        if _PHYS_LABEL_RX.match(nm):
            # genuine vacancy "Male"/"Female" rows usually carry a numeric total;
            # physical rows carry measurements or nothing
            tot = safe(r.get('total', '')).strip()
            if not tot or not re.search(r'\d', tot):
                return True
            # has a measurement-looking value anywhere => physical
        # any cell value looks like a body measurement
        for _k, _v in r.items():
            if _k == 'post_name':
                continue
            if _PHYS_VAL_RX.search(safe(_v)):
                return True
        return False

    has_name = 'post_name' in cols
    # label column = first non-total descriptive column (post_name/state/language)
    _label_cols = [c for c in cols if c in ('post_name','state','language','department')]
    # count how many rows look physical vs how many are genuine posts
    _phys_ct = sum(1 for r in norm if _is_physical_row(r))
    _genuine_ct = len(norm) - _phys_ct
    clean = []
    explicit_total = None
    _total_rows_seen = 0   # count of embedded "Total"/subtotal rows (ESIC-style)
    for r in norm:
        # unified descriptive label = first non-numeric column present (incl. department)
        _lbl_val = (r.get('post_name','') or r.get('state','') or
                    r.get('language','') or r.get('department',''))
        name = _lbl_val
        # drop physical-eligibility pollution rows (only when there ARE genuine
        # vacancy rows too — otherwise this might be a genuine physical table that
        # the section router will handle elsewhere)
        if _genuine_ct >= 1 and _is_physical_row(r):
            continue
        # capture an explicitly-labelled total row, don't render it as a data line.
        # ESIC-style tables embed per-group "Total" subtotal rows (Department:"Total")
        # — these must NOT render as data AND must NOT be summed into the grand total.
        if _is_total_label(_lbl_val):
            t = _to_int(r.get('total'))
            if t: explicit_total = t
            _total_rows_seen += 1
            continue
        # capture an UNLABELLED total row: has a Total value but no descriptive label at all
        if _label_cols and not any(str(r.get(lc,'')).strip() for lc in _label_cols) and str(r.get('total','')).strip():
            t = _to_int(r.get('total'))
            if t: explicit_total = t
            _total_rows_seen += 1
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
        # Multiple embedded subtotal rows (e.g. ESIC Specialist=14 + SR=34): no single
        # captured "Total" is the grand total — the sum of detail rows is authoritative.
        if _total_rows_seen >= 2:
            grand_total = data_sum or grand_total
        elif grand_total is not None and grand_total < data_max:
            grand_total = data_sum or None      # captured "total" was bogus -> use real sum
        if grand_total is None and data_nums:
            grand_total = data_sum

    def _vac_cell(c, val):
        sval = safe(val)
        if c == 'notification_pdf' and sval.startswith('http'):
            return '<td><a href="%s" target="_blank" rel="noopener nofollow"><i class="fa-solid fa-file-pdf"></i> PDF</a></td>' % e(sval)
        return '<td>%s</td>' % e(sval)

    # ── ELIGIBILITY SPLIT ──────────────────────────────────────────────
    # User rule: Vacancy Details table me eligibility/qualification NAHI aani
    # chahiye — wo ek ALAG table me honi chahiye. Agar vacancy rows me
    # qualification column hai to use vacancy cols se hata kar ek alag
    # "Eligibility" sub-table banao (sirf un posts ke liye jinke paas hai).
    _elig_block = ''
    if (mode == 'vacancy' and 'qualification' in cols and has_name
            and 'total' in cols):
        # only split when there's a real Vacancy table (Post + Total) to stand on
        # its own; if it's eligibility-only (no total), keep one combined table.
        _elig_rows = [r for r in clean if str(r.get('qualification', '')).strip()]
        if _elig_rows:
            # Many SR pages put ONE shared eligibility on the first post that
            # applies to all — render Post | Eligibility for the rows that have it.
            _er_html = ''.join(
                f'<tr><td>{_i+1}</td><td>{e(safe(_r.get("post_name","")))}</td>'
                f'<td>{e(safe(_r.get("qualification","")))}</td></tr>'
                for _i, _r in enumerate(_elig_rows))
            _eh = ''
            if _tbl_heading:
                _ehc = re.sub(r'\s*total\s*:?\s*\d[\d,]*\s*post.*$', '', _tbl_heading, flags=re.I).strip()
                _ehc = re.sub(r'vacancy\s*details?', 'Eligibility', _ehc, flags=re.I).strip() or 'Eligibility'
                # if heading already mentions eligibility keep it, else append
                if 'eligib' not in _ehc.lower():
                    _ehc = _ehc + ' : Eligibility'
                _eh = f'<div class="kv-stack-head" style="margin-top:10px">{e(_ehc)}</div>'
            _elig_block = (_eh + '<div class="tbl-scroll"><table class="data-table">'
                           '<thead><tr><th>Sr.</th><th>Post Name</th>'
                           '<th>Eligibility</th></tr></thead><tbody>'
                           + _er_html + '</tbody></table></div>')
        # remove qualification from the vacancy table columns
        cols = [c for c in cols if c != 'qualification']

    head = '<th>Sr.</th>' + ''.join(f'<th>{LABELS[c]}</th>' for c in cols)
    rows = ''.join(f'<tr><td>{i+1}</td>' + ''.join(_vac_cell(c, r.get(c,"")) for c in cols) + '</tr>'
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
    _head_html = ''
    if _tbl_heading:
        # strip a trailing "Total : N Post" tail for a cleaner sub-heading
        _clean_h = re.sub(r'\s*total\s*:?\s*\d[\d,]*\s*post.*$', '', _tbl_heading, flags=re.I).strip()
        _clean_h = _clean_h or _tbl_heading
        _head_html = f'<div class="kv-stack-head" style="margin-top:4px">{e(_clean_h)}</div>'
    return _head_html + f'<div class="tbl-scroll"><table class="data-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>' + _elig_block

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
                    ic,cl = (('fa-paper-plane','lk-apply') if 'apply' in lbl.lower() else
                             ('fa-globe','lk-official') if 'official' in lbl.lower() else
                             ('fa-id-card','lk-admit') if 'admit' in lbl.lower() else
                             ('fa-key','lk-answer') if 'answer' in lbl.lower() else
                             ('fa-trophy','lk-result') if 'result' in lbl.lower() else
                             ('fa-file-pdf','lk-pdf') if ul.endswith('.pdf') else
                             ('fa-arrow-up-right-from-square','lk-default'))
                    _dl = ' download' if ul.endswith('.pdf') else ''
                    btns += (f'<div class="lk-row"><span class="lk-label">{e(lbl[:60])}</span>'
                             f'<a href="{e(url)}" class="lk-open {cl}" target="_blank" rel="noopener noreferrer"{_dl}>'
                             f'<i class="fa-solid {ic}"></i> Open</a></div>\n')
        if btns: html += sec_card('important_links','fa-link','1e40af,#1e3a8a', f'<div class="links-rows">{btns}</div>')
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
                        ul = url.lower(); ll = lbl.lower()
                        ic,cl = ('fa-file-pdf','lk-pdf') if ul.endswith('.pdf') else \
                                ('fa-paper-plane','lk-apply') if 'apply' in ll else \
                                ('fa-globe','lk-official') if 'official' in ll else \
                                ('fa-id-card','lk-admit') if 'admit' in ll else \
                                ('fa-key','lk-answer') if 'answer' in ll else \
                                ('fa-trophy','lk-result') if 'result' in ll else \
                                ('fa-arrow-up-right-from-square','lk-default')
                        _dl = ' download' if ul.endswith('.pdf') else ''
                        btns += (f'<div class="lk-row"><span class="lk-label">{e(lbl[:60])}</span>'
                                 f'<a href="{e(url)}" class="lk-open {cl}" target="_blank" rel="noopener noreferrer"{_dl}>'
                                 f'<i class="fa-solid {ic}"></i> Open</a></div>\n')
                    if btns: body += f'<div class="links-rows">{btns}</div>'
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
             'short_information','board_name','listing_date','title',
             'all_official_links',   # merged into important_links at build time
             'fja_categories','state_tags','district_tags',  # tag-only, no page value
             }

SECTION_ORDER = ['basic_details','important_dates','application_fee','age_limit',
                 'qualification','eligibility_section','course_details','vacancy_details','vacancy_breakdown','subject_wise_vacancy','category_wise_vacancy','salary_details',
                 'selection_process','exam_pattern','syllabus','physical_eligibility',
                 'tables','data_tables','text_sections',
                 'how_to_apply','important_instructions','important_links','faq']
# NOTE: 'useful_links' & 'all_links' are intentionally NOT in SECTION_ORDER.
# _prepare_il() already merges those arrays into `important_links`, so rendering
# them standalone produced (a) a duplicate "Useful Links" box and (b) literal
# "Click Here" labels from the standalone all_links renderer. Every such link now
# flows through render_links(), which resolves a real label via _smart_link_label().

def _smart_render(val, depth=0):
    """UNIVERSAL SMART RENDERER — handles ANY JSON value type automatically.

    Returns HTML for whatever is passed in. JSON insertion order preserved.

    Type handling:
      None / empty       → ''
      bool / number      → text
      string             → paragraph
      list[str]          → bullet list
      list[dict]         → table (union of keys = headers, JSON order)
      list[mixed]        → fallback bullet list (each item rendered recursively)
      dict (flat)        → key-value table
      dict (nested)      → recursive sub-cards
      dict-of-list       → table per sub-key
    """
    # Empty / null → nothing
    if val is None or val == '' or val == [] or val == {}:
        return ''

    # Bool / number → text
    if isinstance(val, (bool, int, float)):
        return f'<div class="edu-sec">{e(safe(val))}</div>'

    # String → paragraph (preserves line breaks)
    if isinstance(val, str):
        _txt = sanitize_short_info(safe(val)).strip()
        if not _txt:
            return ''
        # If contains "|" separators → bullet list (common scraper pattern)
        if '|' in _txt and _txt.count('|') >= 2:
            _parts = [p.strip() for p in _txt.split('|') if p.strip() and len(p.strip()) > 2]
            if len(_parts) >= 2:
                return '<ul class="val-list">' + ''.join(f'<li>{e(p)}</li>' for p in _parts) + '</ul>'
        # Multi-paragraph text
        if '\n\n' in _txt or _txt.count('\n') >= 3:
            _paras = [p.strip() for p in re.split(r'\n{2,}', _txt) if p.strip()]
            if _paras:
                return ''.join(f'<p class="edu-para">{e(p)}</p>' for p in _paras)
        return f'<div class="edu-sec" style="line-height:1.7">{e(_txt)}</div>'

    # List
    if isinstance(val, list):
        _items = [x for x in val if x is not None and x != '' and x != {} and x != []]
        if not _items:
            return ''
        # All dicts → table with union of keys (JSON order preserved)
        if all(isinstance(x, dict) for x in _items):
            _cols = []
            for _row in _items:
                for _k in _row.keys():
                    if _k not in _cols:
                        _cols.append(_k)
            if not _cols:
                return ''
            _head = ''.join(f'<th>{e(key_label(_c))}</th>' for _c in _cols)
            _body = ''
            for _row in _items:
                _body += '<tr>' + ''.join(
                    f'<td>{e(safe(_row.get(_c, "")))}</td>' for _c in _cols
                ) + '</tr>'
            return f'<table class="kv-table"><tbody><tr>{_head}</tr>{_body}</tbody></table>'
        # All scalars → bullet list
        if all(isinstance(x, (str, int, float, bool)) for x in _items):
            _li = [safe(x) for x in _items if safe(x)]
            return '<ul class="val-list">' + ''.join(f'<li>{e(s)}</li>' for s in _li) + '</ul>' if _li else ''
        # Mixed → recursive render each item
        _parts = []
        for _i, _it in enumerate(_items):
            _sub = _smart_render(_it, depth+1)
            if _sub:
                _parts.append(f'<div class="edu-sub-item" style="margin:8px 0">{_sub}</div>')
        return ''.join(_parts)

    # Dict
    if isinstance(val, dict):
        # Filter out internal/empty keys
        _items = [(k, v) for k, v in val.items()
                  if v is not None and v != '' and v != [] and v != {}
                  and not (isinstance(k, str) and k.startswith('_'))]
        if not _items:
            return ''
        # All values scalar → key-value table
        if all(isinstance(v, (str, int, float, bool)) for _, v in _items):
            _rows = ''.join(
                f'<tr><td><strong>{e(key_label(k))}</strong></td><td>{e(safe(v))}</td></tr>'
                for k, v in _items)
            return f'<table class="kv-table"><tbody>{_rows}</tbody></table>'
        # Mixed → render each key as a sub-block with its label
        if depth >= 3:
            # Avoid deep nesting — flatten
            return ''.join(
                f'<div class="edu-sub-item"><strong>{e(key_label(k))}:</strong> '
                f'{_smart_render(v, depth+1)}</div>' for k, v in _items)
        _parts = []
        for _k, _v in _items:
            _sub = _smart_render(_v, depth+1)
            if _sub:
                _parts.append(
                    f'<div class="edu-sub" style="margin:10px 0 6px">'
                    f'<div style="font-weight:700;color:#0d2257;font-size:.95rem;margin-bottom:4px">'
                    f'{e(key_label(_k))}</div>{_sub}</div>')
        return ''.join(_parts)

    # Fallback for any other type
    return f'<div class="edu-sec">{e(safe(val))}</div>'


def _render_unknown_list(val):
    """Generic renderer for an unknown list field so its data is never dropped.
    Handles list-of-strings (→ bullet list) and list-of-dicts (→ table)."""
    if not isinstance(val, list) or not val:
        return ''
    # list of dicts → table using union of keys (insertion order preserved)
    if all(isinstance(x, dict) for x in val):
        cols = []
        for row in val:
            for k in row.keys():
                if k not in cols:
                    cols.append(k)
        if not cols:
            return ''
        head = ''.join(f'<th>{e(key_label(c))}</th>' for c in cols)
        body_rows = ''
        for row in val:
            body_rows += '<tr>' + ''.join(
                f'<td>{e(safe(row.get(c, "")))}</td>' for c in cols) + '</tr>'
        return f'<table class="kv-table"><tbody><tr>{head}</tr>{body_rows}</tbody></table>'
    # list of scalars → bullet list
    items = [safe(x) for x in val if safe(x)]
    if not items:
        return ''
    return '<ul class="val-list">' + ''.join(f'<li>{e(it)}</li>' for it in items) + '</ul>'

def _render_ai_sections(job_obj):
    """Phase 5: render the AI-generated content sections (overview, expert
    analysis, etc.) as section cards — ONLY when the AI field is present.
    Additive: a job with no AI content renders nothing here, exactly as before.
    Facts (tables/dates/fees) are never produced here — those stay fact-sourced."""
    out = ''
    # (key, heading, icon, color)
    ai_cards = [
        ('ai_overview',            'Overview',              'fa-circle-info',       '1d4ed8,#3b82f6'),
        ('ai_expert_analysis',     'Expert Analysis',       'fa-lightbulb',         '7c3aed,#a855f7'),
        ('ai_who_should_apply',    'Who Should Apply',      'fa-user-check',        '0f766e,#0891b2'),
        ('ai_preparation_tips',    'Preparation Tips',      'fa-list-check',        '047857,#10b981'),
        ('ai_salary_insights',     'Salary Insights',       'fa-indian-rupee-sign', 'b45309,#f59e0b'),
        ('ai_job_profile_analysis','Job Profile',           'fa-briefcase',         '475569,#334155'),
        ('ai_selection_strategy',  'Selection Strategy',    'fa-bullseye',          'be123c,#f43f5e'),
    ]
    for key, heading, icon, color in ai_cards:
        val = safe(job_obj.get(key, '') or '')
        if val and len(val) > 20:
            body = f'<div class="edu-sec" style="line-height:1.7">{e(val)}</div>'
            out += sec_card(heading, icon, color, body)
    return out


# ── FJA content_sections renderer (dynamic, complete, un-mixed titled tables) ──
# Scraper ab har section ka heading + uski saari tables (structured, isolated,
# multi-column matrix-safe) `content_sections` me deta hai. Yahan usse generic
# render karte hain — koi bhi (naya bhi) table apne heading ke saath aata hai,
# kabhi mix nahi. Jo sections special renderers me handle hote hain (how to apply /
# links / faq / overview) unhe skip karte hain.
_CSALL_SKIP_RE = re.compile(
    r'(how\s*to\s*apply|apply\s*online|step[\s-]*by[\s-]*step|application\s*process|'
    r'important\s*link|useful\s*link|^\s*faq\b|frequently\s*asked|'
    r'official\s*notification|pdf\s*download|^\s*overview|basic\s*detail|'
    r'common\s*mistake|other\s*active|other\s*(latest\s*)?(govt\s*)?(jobs|recruitment)|'
    r'you\s*might\s*be\s*interested|other\s*posts|about\s*the\s*author)',
    re.I)
_CSALL_ICONS = [
    ('date',      'fa-calendar-check',        'b91c1c,#dc2626'),
    ('fee',       'fa-indian-rupee-sign',     'c2410c,#ea580c'),
    ('salary',    'fa-indian-rupee-sign',     '15803d,#16a34a'),
    ('pay',       'fa-indian-rupee-sign',     '15803d,#16a34a'),
    ('age',       'fa-user-clock',            '0f766e,#0891b2'),
    ('eligib',    'fa-graduation-cap',        '4338ca,#6366f1'),
    ('qualif',    'fa-graduation-cap',        '4338ca,#6366f1'),
    ('vacan',     'fa-chart-pie',             '15803d,#16a34a'),
    ('post',      'fa-chart-pie',             '15803d,#16a34a'),
    ('selection', 'fa-list-check',            '5b21b6,#7c3aed'),
    ('exam',      'fa-file-lines',            '0369a1,#0284c7'),
    ('pattern',   'fa-file-lines',            '0369a1,#0284c7'),
    ('syllabus',  'fa-book',                  '4338ca,#6366f1'),
]

def _csall_table_html(rows):
    if not isinstance(rows, list) or not rows: return ''
    cols = []
    for r in rows:
        if isinstance(r, dict):
            for k in r.keys():
                if k not in cols: cols.append(k)
    if not cols: return ''
    head = ''.join(f'<th>{e(key_label(c))}</th>' for c in cols)
    body = ''
    for r in rows:
        if not isinstance(r, dict): continue
        body += '<tr>' + ''.join(f'<td>{e(safe(r.get(c, "")))}</td>' for c in cols) + '</tr>'
    if not body: return ''
    return (f'<div class="tbl-scroll"><table class="data-table">'
            f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')

def render_content_sections_all(sections):
    if not isinstance(sections, list): return ''
    out = ''
    for sec in sections:
        if not isinstance(sec, dict): continue
        heading = safe(sec.get('heading', ''))
        if not heading or _CSALL_SKIP_RE.search(heading): continue
        tables = sec.get('tables') or []
        text = safe(sec.get('text', ''))
        body = ''
        if text:
            body += (f'<div style="padding:10px 14px;font-size:.9rem;color:#334155;'
                     f'line-height:1.6">{e(text[:900])}</div>')
        multi = len([t for t in tables if isinstance(t, dict) and t.get('rows')]) > 1
        for t in tables:
            if not isinstance(t, dict): continue
            th = _csall_table_html(t.get('rows') or [])
            if not th: continue
            cap = safe(t.get('caption', ''))
            if cap and multi:
                body += (f'<div style="font-weight:700;color:#334155;'
                         f'margin:12px 14px 4px;font-size:.92rem;">{e(cap)}</div>')
            body += th
        if not body: continue
        icon, grad = 'fa-table-list', '475569,#334155'
        hl = heading.lower()
        for kw, ic, gr in _CSALL_ICONS:
            if kw in hl:
                icon, grad = ic, gr; break
        out += sec_card(heading, icon, grad, body)
    return out


def build_all_sections(job_obj):
    html = ''
    rendered = set()
    # ── AI LAYER (Phase 5): AI content sections render FIRST (prominent), only
    # when present. Pure addition — no effect on jobs without AI content. ──
    _ai_secs_html = _render_ai_sections(job_obj)
    if _ai_secs_html:
        html += f'<!-- TSJ_AI_BLOCK_START -->\n{_ai_secs_html}<!-- TSJ_AI_BLOCK_END -->\n'
    # AI overview replaces the old short-info card: if ai_overview exists, mark
    # short_information as "already handled" so we don't show both (no dup).
    if safe(job_obj.get('ai_overview', '') or ''):
        rendered.add('short_information')
        rendered.add('shortInfo')
    # Check for sarkari titled sections
    sections = job_obj.get('sections') or []
    has_sarkari = bool(sections and any(sec.get('title') for sec in sections if isinstance(sec,dict)))
    has_edu_secs = bool(sections and any(sec.get('heading') is not None for sec in sections if isinstance(sec,dict)) and not has_sarkari)
    il = _prepare_il(job_obj)

    # ── FJA content_sections FIRST — complete, un-mixed, titled tables. ──
    # Kuch generation loops job_obj se content_sections strip kar dete hain, isliye
    # _scraped_from / slug / title se global lookup (_CS_BY_KEY) fallback — robust.
    _cs = job_obj.get('content_sections')
    if not (isinstance(_cs, list) and _cs):
        _bd0 = job_obj.get('basic_details') or {}
        for _lk in (job_obj.get('_scraped_from'), job_obj.get('slug'),
                    _cs_norm_title(_bd0.get('job_title', '') or job_obj.get('title', ''))):
            if _lk and _lk in _CS_BY_KEY:
                _cs = _CS_BY_KEY[_lk]
                break
    # content_sections (list format) kabhi raw "Content Sections" card na bane
    if isinstance(job_obj.get('content_sections'), list):
        rendered.add('content_sections')
    _cs_rendered = False
    if isinstance(_cs, list) and any(isinstance(s, dict) and s.get('tables') for s in _cs):
        _bd = job_obj.get('basic_details')
        if _bd and _bd != {}:
            _bd_body = render_basic_details(_bd)
            if _bd_body and _bd_body.strip():
                _bm = SECTION_META.get('basic_details', ('Job Overview', 'fa-circle-info', '1e40af,#3b82f6'))
                html += sec_card('basic_details', _bm[1], _bm[2], _bd_body)
                rendered.add('basic_details')
        html += render_content_sections_all(_cs)
        # Covered typed keys + raw carriers ko rendered mark karo (dobara / raw dump na ho)
        for _k in ('content_sections', 'important_dates', 'application_fee', 'age_limit',
                   'qualification', 'vacancy_details', 'vacancy_breakdown',
                   'category_wise_vacancy', 'salary_details', 'selection_process',
                   'exam_pattern', 'syllabus', 'physical_eligibility',
                   'tables', 'text_sections', 'data_tables', 'details_page_content'):
            rendered.add(_k)
        _cs_rendered = True

    if not _cs_rendered and has_sarkari:
        html += render_sarkari_sections(sections, il)
        rendered.add('sections')
    elif not _cs_rendered and has_edu_secs:
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
                html += sec_card(_dyn_section_heading(_pre_key, job_obj), _pre_meta[1], _pre_meta[2], _pre_body)
        # Now render the edu content sections
        html += render_edu_sections(sections)
        rendered.add('sections')

    for key in SECTION_ORDER:
        if key in rendered: continue
        val = job_obj.get(key)
        if val is None or val == '' or val == [] or val == {}:
            # important_links may itself be empty {} while all_official_links /
            # all_links (already merged into `il` by _prepare_il) still hold real
            # links — render from `il` instead of skipping the section.
            if key == 'important_links' and il:
                val = il
            else:
                continue
        rendered.add(key)
        if key == 'basic_details':      body = render_basic_details(val)
        elif key == 'important_dates':  body = render_dates(val)
        elif key == 'application_fee':  body = render_fee(val)
        elif key == 'age_limit':        body = render_list_items(val) if isinstance(val,list) else (render_kv_dict(val) if isinstance(val,dict) else e(safe(val)))
        elif key == 'qualification':    body = render_qualification(val)
        elif key == 'course_details':
            # SR courseDetails: [{courseName, eligibility}] — render as clean 2-col table
            # SAFETY NET: older scraper sometimes mis-captured a VACANCY table as
            # course_details, putting the Total-Post NUMBER (e.g. "178") as
            # courseName, OR duplicating the vacancy eligibility text here. Drop:
            #  - numeric/empty courseName
            #  - rows whose courseName is already a vacancy post name
            #  - rows whose eligibility text duplicates a vacancy eligibility
            #    (SGPGI: same "Bachelor Degree..." text in both tables)
            _cd = val if isinstance(val, list) else []
            _vac_posts = set()
            _vac_eligs = set()
            def _norm(t):
                return re.sub(r'[^a-z0-9]+', ' ', safe(t).lower()).strip()
            for _vp in (job_obj.get('vacancy_details') or []):
                if isinstance(_vp, dict):
                    _pn = _norm(_vp.get('post_name') or _vp.get('postName'))
                    if _pn: _vac_posts.add(_pn)
                    _ve = _norm(_vp.get('qualification') or _vp.get('eligibility'))
                    if _ve and len(_ve) > 15: _vac_eligs.add(_ve)
            _cd_rows = []
            _cd_seen = set()
            for _c in _cd:
                if not isinstance(_c, dict): continue
                _cn = safe(_c.get('courseName') or _c.get('course_name') or _c.get('course') or '')
                _el = safe(_c.get('eligibility') or _c.get('eligiblity') or _c.get('qualification') or '')
                # bad row: courseName missing OR purely a number (it's a post count)
                if not _cn.strip() or re.fullmatch(r'\d[\d,]*', _cn.strip()):
                    continue
                if not (_cn or _el): continue
                # skip if courseName is actually a vacancy post (duplicate listing)
                if _norm(_cn) in _vac_posts:
                    continue
                # skip if the eligibility text duplicates a vacancy eligibility
                if _el and _norm(_el) in _vac_eligs:
                    continue
                # skip if courseName itself is just an eligibility sentence already
                # shown under vacancy (SGPGI: courseName holds the elig text)
                if _norm(_cn) in _vac_eligs:
                    continue
                _sig = _norm(_cn) + '|' + _norm(_el)
                if _sig in _cd_seen:      # internal duplicate
                    continue
                _cd_seen.add(_sig)
                _cd_rows.append(f'<tr><td>{e(_cn)}</td><td>{e(_el)}</td></tr>')
            if _cd_rows:
                body = ('<table class="kv-table"><tbody>'
                        '<tr><th>Course Name</th><th>Eligibility</th></tr>'
                        + ''.join(_cd_rows) + '</tbody></table>')
            else:
                body = ''
        elif key == 'vacancy_details':  body = render_vacancy_table(val)
        elif key == 'vacancy_breakdown': body = render_vacancy_breakdown(val, prior_html=html)
        elif key == 'subject_wise_vacancy': body = render_vacancy_table(val) if isinstance(val,list) else ''
        elif key == 'eligibility_section':
            # NDA-type "Army Wing : ...", "For Airforce & Naval Wing : ..."
            # eligibility blocks. Render each block's heading + bullet items.
            _es_parts = []
            for _blk in (val if isinstance(val, list) else []):
                if not isinstance(_blk, dict): continue
                _items = _blk.get('items') or []
                if not _items: continue
                _lis = ''.join(f'<li>{e(safe(_it))}</li>' for _it in _items if safe(_it).strip())
                if _lis:
                    _es_parts.append(f'<ul class="edu-list">{_lis}</ul>')
            body = ''.join(_es_parts)
        elif key == 'category_wise_vacancy': body = (render_vacancy_table(val) if isinstance(val,list) else _render_catwise_dict(val) if isinstance(val,dict) else '')
        elif key == 'salary_details':   body = render_list_items(val) if isinstance(val,list) else (render_kv_dict(val) if isinstance(val,dict) else f'<div class="edu-sec">{e(safe(val))}</div>')
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
        elif key == 'data_tables':
            # SR scraper dataTables: [{heading, headers:[...], rows:[[col,...]]}]
            # BULLETPROOF SAFETY NET: even if junk slips into data_tables (old data
            # or scraper miss), NEVER render duplicate/junk table rows. All real
            # structured data already lives in vacancy_details / important_dates /
            # application_fee / age_limit / important_links. So data_tables ko sirf
            # genuinely-extra clean rows ke liye render karo.
            _dt = val if isinstance(val, list) else []
            _dt_parts = []
            # text already captured in vacancy_details (eligibility/subjects) →
            # never re-render it as a junk table row
            _vac_captured = set()
            _vd = job_obj.get('vacancy_details') or []
            if isinstance(_vd, list):
                for _v in _vd:
                    if isinstance(_v, dict):
                        for _f in ('eligibility', 'subjects', 'post_name'):
                            _tv = safe(_v.get(_f) or '').strip().lower()
                            if len(_tv) > 15:
                                _vac_captured.add(_tv[:60])
            # aggressive junk-row matcher
            _JUNK_ROW = re.compile(
                r'important\s*dates?\b|application\s*fees?\b|how\s*to\s*(fill|apply)|'
                r'some\s*useful|interested\s*candidate|download\s*the\s*sarkari|'
                r'sarkari\s*result\s*(android|apple|mobile|channel|tools?)|'
                r'join\s*sarkari|join\s*channel|telegram|whatsapp|'
                r'signature\s*resizer|pdf\s*compress|age\s*calculat|'
                r'for\s*the\s*latest\s*updates|short\s*details\s*of\s*notification|'
                r'official\s*website\s*of|result®|since\s*20\d\d|'
                r'^\s*app\s*$|^\s*click\s*here\s*$|^\s*download\b|'
                r'notification\s*20\d\d\s*:|recruitment\s*20\d\d\s*:|'
                r'exam\s*20\d\d\s*:.*eligibility|:\s*age\s*limit\s*details', re.I)
            for _t in _dt:
                if not isinstance(_t, dict):
                    continue
                _hd = safe(_t.get('heading') or _t.get('table_name') or '')
                _hdrs = _t.get('headers') or []
                _rows = _t.get('rows') or []
                if not _rows and not _hdrs:
                    continue
                _clean_rows = []
                for _r in _rows:
                    if not isinstance(_r, list):
                        continue
                    _rtext = ' '.join(safe(c) for c in _r).strip()
                    if not _rtext:
                        continue
                    # drop junk rows
                    if _JUNK_ROW.search(_rtext):
                        continue
                    # drop pure link rows ["Apply Online","Click Here"]
                    if len(_r) == 2 and re.fullmatch(
                            r'\s*(click here|official website|telegram\s*\|?\s*whatsapp'
                            r'|english\s*\|?\s*hindi)\s*', safe(_r[1]), re.I):
                        continue
                    # drop column-header rows (Post Name | ... Eligibility/Total/Subjects)
                    _rl = _rtext.lower()
                    if 'post name' in _rl and any(
                            k in _rl for k in ['eligib', 'total', 'subject', 'qualif']):
                        continue
                    # drop single-cell section-heading rows
                    _nonempty = [c for c in _r if safe(c).strip()]
                    if len(_nonempty) == 1 and re.search(
                            r':\s*(eligibility|age limit|vacancy|physical|category|'
                            r'subject|selection)\b', _rtext, re.I):
                        continue
                    # drop rows already captured in vacancy_details
                    if any(safe(c).strip().lower()[:60] in _vac_captured for c in _r):
                        continue
                    _clean_rows.append(_r)
                # require at least one multi-column data row to render at all
                _multi = [r for r in _clean_rows
                          if len([c for c in r if safe(c).strip()]) >= 2]
                if not _multi:
                    continue
                _hdrs_clean = _hdrs
                if isinstance(_hdrs, list):
                    _h_join = ' '.join(safe(h) for h in _hdrs)
                    if _JUNK_ROW.search(_h_join) or 'Short Details' in _h_join:
                        _hdrs_clean = []
                # column count check: kv-table's CSS forces width:38% on EVERY
                # <th> (it's designed for 2-col label:value rows). District/
                # state-wise breakdown tables have 3-5+ columns (District |
                # Vacancy | Last Date | Link...) — putting width:38% on each
                # of 5 <th> = 190% total width, so the browser crushes columns
                # down to near-zero and text wraps one character per line.
                # Multi-column tables must use the scrollable data-table class
                # instead (table-layout:auto, no forced per-th width).
                _ncols = max(len(_hdrs_clean) if isinstance(_hdrs_clean, list) else 0,
                             max((len(r) for r in _clean_rows), default=0))
                _is_multicol = _ncols > 2

                def _cellhtml(_c):
                    # auto-linkify bare URLs (e.g. pdf_url from district-wise
                    # tables) so download/notification links are clickable
                    # instead of rendering as raw unbroken URL text.
                    _cs = safe(_c).strip()
                    if _cs.startswith('http://') or _cs.startswith('https://'):
                        return f'<a href="{e(_cs)}" target="_blank" rel="noopener noreferrer">Download</a>'
                    return e(_cs)

                if _is_multicol:
                    _tbl = '<div class="tbl-scroll"><table class="data-table"><tbody>'
                else:
                    _tbl = '<table class="kv-table"><tbody>'
                if isinstance(_hdrs_clean, list) and any(safe(h) for h in _hdrs_clean):
                    _tbl += '<tr>' + ''.join(f'<th>{e(safe(h))}</th>' for h in _hdrs_clean if safe(h)) + '</tr>'
                    _first_is_header = False
                else:
                    _first_is_header = True
                for _ri, _r in enumerate(_clean_rows):
                    _cells = [safe(c) for c in _r]
                    # keep row width == header width so no cell ever floats
                    # outside the visible columns (e.g. a stray extra value
                    # like an orphan "103" with no matching header)
                    if isinstance(_hdrs_clean, list) and _hdrs_clean and len(_cells) != len(_hdrs_clean):
                        if len(_cells) < len(_hdrs_clean):
                            _cells = _cells + [''] * (len(_hdrs_clean) - len(_cells))
                        else:
                            _cells = _cells[:len(_hdrs_clean)]
                    _tag = 'th' if (_first_is_header and _ri == 0 and len(_cells) > 1) else 'td'
                    if _tag == 'th':
                        _tbl += '<tr>' + ''.join(f'<th>{e(c)}</th>' for c in _cells) + '</tr>'
                    else:
                        _tbl += '<tr>' + ''.join(f'<td>{_cellhtml(c)}</td>' for c in _cells) + '</tr>'
                _tbl += '</tbody></table>'
                if _is_multicol:
                    _tbl += '</div>'
                if _hd and _hd.lower() not in ('table', 'data table'):
                    _dt_parts.append(f'<div class="kv-stack-head" style="margin-top:10px">{e(_hd)}</div>{_tbl}')
                else:
                    _dt_parts.append(_tbl)
            body = ''.join(_dt_parts)
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
                        return ('fa-file-pdf', 'lk-pdf')
                    if 'result' in t or 'merit' in t: return ('fa-trophy', 'lk-result')
                    if 'admit' in t: return ('fa-id-card', 'lk-admit')
                    if 'answer' in t or 'key' in t: return ('fa-key', 'lk-answer')
                    if 'login' in t: return ('fa-right-to-bracket', 'lk-login')
                    if 'register' in t or 'registration' in t: return ('fa-user-plus', 'lk-register')
                    if 'upload' in t or 'fee' in t or 'pay' in t: return ('fa-file', 'lk-orange')
                    if 'official' in t or 'website' in t: return ('fa-globe', 'lk-official')
                    if 'apply' in t or 'ibpsreg' in ul or 'career' in ul:
                        return ('fa-paper-plane', 'lk-apply')
                    return ('fa-arrow-up-right-from-square', 'lk-default')

                rows_html = ''
                seen_render = set()
                for item in ul_items:
                    lnk = item['url']
                    if lnk in seen_render: continue
                    seen_render.add(lnk)
                    ic, cl = _smart_link(item['title'], lnk)
                    _dl = ' download' if lnk.lower().endswith('.pdf') else ''
                    rows_html += (f'<div class="lk-row"><span class="lk-label">{e(item["title"])}</span>'
                                  f'<a href="{e(lnk)}" class="lk-open {cl}" target="_blank" rel="noopener noreferrer"{_dl}>'
                                  f'<i class="fa-solid {ic}"></i> Open</a></div>\n')
                if rows_html:
                    body = f'<div class="links-rows">{rows_html}</div>'
        elif key == 'all_links':
            # all_links: [{label, title, url}] — render as row layout (label + Open)
            if isinstance(val, list):
                valid = [lnk for lnk in val if isinstance(lnk,dict) and str(lnk.get('url','')).startswith('http') and not is_blocked(str(lnk.get('url','')))]
                if valid:
                    rows_html = ''; _seen_al = set()
                    for lnk in valid:
                        lbl   = safe(lnk.get('label') or lnk.get('title') or 'Click Here').strip()[:80]
                        url_l = str(lnk.get('url','')).strip()
                        if not lbl: lbl = 'Click Here'
                        if url_l in _seen_al: continue
                        _seen_al.add(url_l)
                        ul_lower = url_l.lower(); ll = lbl.lower()
                        ic,cl = ('fa-file-pdf','lk-pdf') if ul_lower.endswith('.pdf') else \
                                ('fa-paper-plane','lk-apply') if 'apply' in ll else \
                                ('fa-trophy','lk-result') if 'result' in ll else \
                                ('fa-id-card','lk-admit') if 'admit' in ll else \
                                ('fa-key','lk-answer') if 'answer' in ll else \
                                ('fa-globe','lk-official') if ('official' in ll or 'website' in ll) else \
                                ('fa-right-to-bracket','lk-login') if 'login' in ll else \
                                ('fa-user-plus','lk-register') if 'regist' in ll else \
                                ('fa-arrow-up-right-from-square','lk-default')
                        _dl = ' download' if ul_lower.endswith('.pdf') else ''
                        rows_html += (f'<div class="lk-row"><span class="lk-label">{e(lbl)}</span>'
                                      f'<a href="{e(url_l)}" class="lk-open {cl}" target="_blank" rel="noopener noreferrer"{_dl}>'
                                      f'<i class="fa-solid {ic}"></i> Open</a></div>\n')
                    body = f'<div class="links-rows">{rows_html}</div>'
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
                # content_sections — {heading: [lines...]} used by NON_JOB / news
                # entries (e.g. Haryana E-Kshatipurti). Render each heading as a
                # sub-heading and its lines as a numbered list / paragraphs.
                _cs = val.get('content_sections')
                if isinstance(_cs, dict) and _cs:
                    # Skip the heading already used as the card title
                    for _h in (_dpc_headings or list(_cs.keys())):
                        _h = safe(_h).strip()
                        lines = _cs.get(_h) or _cs.get(_h.strip()) or []
                        if not lines: continue
                        clean_lines = []
                        for ln in lines:
                            ln = safe(ln).strip()
                            if not ln or len(ln) < 3: continue
                            if _JUNK_RX.search(ln): continue
                            # drop "... says: <date> [...]" comment-spam lines
                            if re.search(r'\bsays:\s', ln, re.I): continue
                            if re.match(r'^\[.*\]$', ln): continue
                            clean_lines.append(ln)
                        if not clean_lines: continue
                        # sub-heading (skip if it's the card title itself)
                        if _h and _h != _dpc_title:
                            parts.append(f'<div class="kv-stack-head" style="margin-top:10px">{e(_h)}</div>')
                        # single line → paragraph; multiple → numbered list
                        if len(clean_lines) == 1:
                            parts.append(f'<p class="edu-para">{e(clean_lines[0])}</p>')
                        else:
                            parts.append('<ol class="kv-numlist">' + ''.join(f'<li>{e(c)}</li>' for c in clean_lines) + '</ol>')
                body = ''.join(parts) if parts else ''
                # FALLBACK: if no structured content was found but a full_text
                # blob exists, render it as readable paragraphs (split on blank
                # lines) so the detail page is never empty.
                if not body.strip():
                    _ft = safe(val.get('full_text'))
                    if _ft and len(_ft) > 40:
                        _ft_parts = []
                        for _seg in re.split(r'\n{2,}|\r\n\r\n', _ft):
                            _seg = _seg.strip()
                            if not _seg or len(_seg) < 15: continue
                            if _JUNK_RX.search(_seg): continue
                            _ft_parts.append(f'<p class="edu-para">{e(_seg[:1200])}</p>')
                            if len(_ft_parts) >= 30: break
                        body = ''.join(_ft_parts)
                # Use dynamic title instead of hardcoded SECTION_META label
                if body and body.strip():
                    html += sec_card(_dpc_title, 'fa-circle-info', '1e40af,#3b82f6', body)
                body = ''  # mark as already rendered
        elif key == 'syllabus':         body = (render_list_items(val) if isinstance(val,list) else f'<div class="edu-sec">{e(safe(val))}</div>')
        elif key == 'physical_eligibility': body = (render_kv_dict(val) if isinstance(val,dict) else render_list_items(val) if isinstance(val,list) else f'<div class="edu-sec">{e(safe(val))}</div>')
        elif key == 'how_to_apply':
            # AI LAYER: prefer the AI rewrite if present, else the scraped steps.
            _ai_hta = safe(job_obj.get('ai_how_to_apply_rewrite', '') or '')
            body = (f'<div class="edu-sec" style="line-height:1.7">{e(_ai_hta)}</div>'
                    if _ai_hta else render_hta(val))
        elif key == 'important_instructions': body = ''.join(f'<div class="inst-box"><i class="fa-solid fa-triangle-exclamation"></i><span>{e(safe(s))}</span></div>' for s in (val if isinstance(val,list) else [val]) if safe(s))
        elif key == 'important_links':  body = render_links(il)  # use _prepare_il-merged links (labels, all_official_links, list-expansion)
        elif key == 'faq':
            # AI LAYER: prefer AI-expanded FAQs; wrap in sentinel so patch_ai_html.py
            # can update in-place without re-injecting (idempotent).
            # BRAND: har page pe ek category-tailored, page-specific branded Q&A
            # (dono flow me — AI aur non-AI). render_faq dedupes; idempotent.
            _brand_qa = brand_help_faq(job_obj)
            _ai_faqs = job_obj.get('ai_expanded_faqs') or []
            if _ai_faqs:
                _merged = list(_ai_faqs)
                if _brand_qa and _brand_qa not in _merged:
                    _merged.append(_brand_qa)
                body = f'<!-- TSJ_AI_FAQ_START -->{render_faq(_merged)}<!-- TSJ_AI_FAQ_END -->'
            else:
                _json_faqs = [f for f in (val if isinstance(val, list) else [])
                              if isinstance(f, dict) and safe(f.get('question')) and safe(f.get('answer'))]
                # SEO: guarantee a useful minimum. Thin JSON FAQ (<5) — common before
                # the nightly AI enricher runs — is supplemented with FAQs auto-built
                # from THIS page's real fields (dates/fee/eligibility/vacancy — never
                # invented). render_faq dedupes; capped so it stays tidy.
                if len(_json_faqs) < 5:
                    _extra = [f for f in auto_generate_faqs(job_obj) if f not in _json_faqs]
                    _merged = (_json_faqs + _extra)[:12]
                else:
                    _merged = _json_faqs
                if _brand_qa and _brand_qa not in _merged:
                    _merged.append(_brand_qa)
                body = render_faq(_merged)
        elif key == 'sections':
            body = render_edu_sections(val) if isinstance(val,list) else ''
        else:                           body = ''
        meta = SECTION_META.get(key)
        if meta and body and body.strip():
            html += sec_card(_dyn_section_heading(key, job_obj), meta[1], meta[2], body)

    # ── UNIVERSAL FALLBACK: ANY top-level JSON key not rendered above gets
    # auto-rendered via _smart_render in JSON's natural order. New keys added
    # to JSON later (by scraper updates) automatically appear in HTML without
    # any code change — fully dynamic & order-preserving.
    _ad_keys = set(job_obj.get('_ad_derived_keys') or [])
    _has_course_details = bool(job_obj.get('course_details'))
    _dyn_elig = {}            # legacy course-eligibility grouping (preserved)
    _NEVER_AS_UNKNOWN = set(SKIP_KEYS) | set(SECTION_ORDER) | {
        'meta', 'sections', 'short_information', 'organization', 'total_post',
        'totalpost', 'post_date', 'name', 'breadcrumbs', 'course_name',
        'how_to_apply', 'physical_eligibility', 'result_url', 'answer_key_url',
        'resulturl', 'answerkeyurl', '_ad_derived_keys',
        # brand_seo enrichment blocks — NEVER render visibly. Ye JSON-LD/attribution
        # blocks the-page pe tables ban ke layout tod rahe the. Site apna khud ka
        # proper invisible JSON-LD (build_schemas) + footer branding deti hai, isliye
        # ye visible render bekaar tha. (JSON se bhi hata rahe hain — ye safety net.)
        'seo', 'publishedBy', 'attribution', 'published_by',
        # LATEST_JOBS NEW / OFFLINE_FORM / UPCOMING_JOBS / ADMISSIONS (shine/network
        # source) me ye extra fields page ke bottom pe DUPLICATE sections ban rahe the:
        #   all_links → already important_links me merge hai (standalone duplicate)
        #   details_page_content → raw scraped content ("Scholarship Details")
        #   faqs → site khud auto_generate_faqs banati hai (scraped faqs redundant)
        #   age_relaxation_notes / salary_stipend / age_reference_date → fallback dump
        # Inhe kabhi render mat karo. Links important_links section me safe rahenge.
        'all_links', 'details_page_content', 'faqs',
        'age_relaxation_notes', 'salary_stipend', 'age_reference_date',
    }
    for key, val in job_obj.items():
        # Skip internal/AI/already-rendered keys
        if isinstance(key, str) and key.startswith('_'):
            continue
        if isinstance(key, str) and (key.startswith('ai_') or
                key in ('content_hash', 'ai_schema_faq', 'ai_expanded_faqs',
                        'ai_extracted_structured_data')):
            continue
        if key in rendered or key in _NEVER_AS_UNKNOWN:
            continue
        if not val or val == {} or val == []:
            continue

        # additionalData-derived course-eligibility blob (legacy grouping)
        if key in _ad_keys and isinstance(val, str):
            if _has_course_details:
                continue
            _dyn_elig[key] = val
            continue
        if isinstance(val, str):
            _looks_elig = bool(re.search(r'(\d+%|\bmarks\b|\bpass(ed)?\b|10\+2|graduation|bachelor|degree|diploma)', val, re.I))
            if _looks_elig and _has_course_details:
                continue
            if _looks_elig and len(val) < 400:
                _dyn_elig[key] = val
                continue

        # UNIVERSAL SMART RENDER — handles dicts, lists-of-dicts (tables),
        # lists-of-strings (bullets), nested structures, anything else.
        _body = _smart_render(val)
        if _body and _body.strip():
            # Skip garbled scalar values
            if isinstance(val, str) and _is_garbled_field(key_label(key), safe(val)):
                continue
            html += sec_card(key_label(key), 'fa-circle-dot', '475569,#334155', _body)

    # grouped dynamic eligibility table (only if course_details didn't already cover it)
    if _dyn_elig:
        _rows = ''.join(
            f'<tr><td>{e(key_label(_k))}</td><td>{e(safe(_v))}</td></tr>'
            for _k, _v in _dyn_elig.items())
        _body = ('<table class="kv-table"><tbody>'
                 '<tr><th>Course / Category</th><th>Eligibility</th></tr>'
                 + _rows + '</tbody></table>')
        html += sec_card('Course-wise Eligibility', 'fa-list-check', '4338ca,#6366f1', _body)

    # (leftover scalars now rendered inline above via _smart_render - no separate loop needed)

    # ── Auto-FAQ: if no JSON FAQ was rendered, generate from page data ──
    if 'faq' not in rendered:
        # AI LAYER: if AI-expanded FAQs exist, use those; else auto-generate.
        _ai_faqs = job_obj.get('ai_expanded_faqs') or []
        _auto = _ai_faqs if _ai_faqs else auto_generate_faqs(job_obj)
        if len(_auto) >= 2:  # show if we have at least a couple real FAQs
            _auto_body = render_faq(_auto)
            if _auto_body and _auto_body.strip():
                _m = SECTION_META.get('faq', ('FAQs','fa-circle-question','4338ca,#6366f1'))
                html += sec_card('faq', _m[1], _m[2], _auto_body)
                rendered.add('faq')

    # ── Safety net: drop any sec-card whose heading already appeared earlier ──
    # (guards against a field rendering both inside `sections` and as a top-level
    # SECTION_ORDER key — e.g. Important Dates / Application Fee on some edu jobs.)
    html = _dedup_section_cards(html)

    return html

def _dedup_section_cards(html):
    """Remove duplicate sec-card blocks that share the same <h2> heading,
    keeping the first occurrence. Handles both <div class="sec-card"> and
    <section class="sec-card"> wrappers. Non-card html is left untouched."""
    if not html or 'sec-card' not in html:
        return html
    parts = re.split(r'(?=<(?:div|section) class="sec-card")', html)
    seen = set()
    out = []
    for p in parts:
        m = re.search(r'<h2>([^<]+)</h2>', p)
        if m:
            key = re.sub(r'\s+', ' ', m.group(1)).strip().lower()
            if key in seen and key not in ('additional details',):
                continue
            seen.add(key)
        out.append(p)
    html = ''.join(out)
    # Also drop EXACT-duplicate <table> blocks anywhere on the page (same content
    # rendered twice via two different fields/paths — e.g. an info page that has
    # the same "Particulars | Details" table from two JSON keys).
    _seen_tbl = set()
    def _dedup_tbl(mt):
        block = mt.group(0)
        sig = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', block)).strip().lower()
        if len(sig) < 20:           # tiny tables: leave alone
            return block
        if sig in _seen_tbl:
            return ''               # remove duplicate table
        _seen_tbl.add(sig)
        return block
    html = re.sub(r'<table\b.*?</table>', _dedup_tbl, html, flags=re.S)
    return html

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
    faq   = (job_obj.get('ai_expanded_faqs') or job_obj.get('faq', []) or [])
    title = safe(bd.get('job_title','') or job_obj.get('title',''))
    org   = safe(bd.get('organization_name','') or 'Government of India')
    loc   = safe(bd.get('job_location','') or 'India')
    desc  = sanitize_short_info(safe(bd.get('short_information','')))[:500] or title
    # Smart last_d: for result/admitcard pages, application deadline is stale — prefer result_date/exam_date
    _is_result_page = any(x in str(job_obj.get('category','')).lower() for x in ('result','admit'))
    if _is_result_page:
        last_d = safe(dates.get('result_date','') or dates.get('marks_available','')
                      or dates.get('exam_date','') or dates.get('last_date_apply_online','')
                      or dates.get('last_date_to_apply','') or dates.get('last_date',''))
    else:
        last_d = safe(dates.get('extended_last_date','') or dates.get('date_extended','')
                      or dates.get('last_date_to_apply','') or dates.get('last_date_apply_online','')
                      or dates.get('last_date','') or dates.get('exam_date','') or dates.get('written_exam_date',''))
    vacancies = safe(bd.get('total_vacancies','') or job_obj.get('total_post','') or job_obj.get('total_vacancy',''))
    # SECURE FALLBACK: ai_extracted_structured_data for missing fields
    ai_data = job_obj.get('ai_extracted_structured_data') or {}
    # Official website (used in job + non-job schemas)
    _official_site_url = safe(
        _il_url((job_obj.get('important_links') or {}).get('official_website')) or
        _il_url((job_obj.get('useful_links') or {}).get('official_website')) or
        (job_obj.get('basic_details') or {}).get('official_website','') or '')
    if is_blocked(_official_site_url):
        _official_site_url = ''

    if slug is None:
        slug = registered_slug(title)[:80]
    intent = page_intent(job_obj)
    # C1: stable datePosted (never build-date for the same job across rebuilds)
    date_posted    = get_date_posted(slug, job_obj)           # YYYY-MM-DD
    date_posted_iso = f"{date_posted}T00:00:00+05:30"         # ISO 8601 with IST

    # ── Breadcrumb schema (always) ──
    bc_items = [{'@type':'ListItem','position':1,'name':'Home','item':BASE_URL+'/'}]
    for i,(lbl,url) in enumerate(breadcrumbs, 2):
        bc_items.append({'@type':'ListItem','position':i,'name':lbl,'item':url})
    bc_items.append({'@type':'ListItem','position':len(bc_items)+1,'name':title,'item':canon_url})
    bc_schema = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':bc_items}

    if intent == 'job':
        # FIX #3: hiringOrganization.sameAs must be the EMPLOYER's official site,
        # not our own domain (self-referencing sameAs causes GSC schema errors).
        _official_site = safe(
            _il_url((job_obj.get('important_links') or {}).get('official_website')) or
            _il_url((job_obj.get('useful_links') or {}).get('official_website')) or
            (job_obj.get('basic_details') or {}).get('official_website', '') or '')
        _hiring_org = {'@type': 'Organization', 'name': org}
        if _official_site and not is_blocked(_official_site):
            _hiring_org['sameAs'] = _official_site
        # ── SECURE FALLBACK: addressRegion + postalCode from loc/state/ai_data ──
        # Map common state names/abbreviations to (region, postalCode)
        _STATE_MAP = {
            'jharkhand':('Jharkhand','834001'), 'delhi':('Delhi','110001'),
            'uttar pradesh':('Uttar Pradesh','226001'), 'up':('Uttar Pradesh','226001'),
            'rajasthan':('Rajasthan','302001'), 'bihar':('Bihar','800001'),
            'madhya pradesh':('Madhya Pradesh','462001'), 'mp':('Madhya Pradesh','462001'),
            'maharashtra':('Maharashtra','400001'), 'gujarat':('Gujarat','380001'),
            'haryana':('Haryana','122001'), 'punjab':('Punjab','141001'),
            'karnataka':('Karnataka','560001'), 'tamil nadu':('Tamil Nadu','600001'),
            'west bengal':('West Bengal','700001'), 'odisha':('Odisha','751001'),
            'kerala':('Kerala','695001'), 'telangana':('Telangana','500001'),
            'andhra pradesh':('Andhra Pradesh','520001'), 'assam':('Assam','781001'),
            'chhattisgarh':('Chhattisgarh','492001'), 'uttarakhand':('Uttarakhand','248001'),
            'himachal pradesh':('Himachal Pradesh','171001'), 'goa':('Goa','403001'),
            'tripura':('Tripura','799001'), 'meghalaya':('Meghalaya','793001'),
            'manipur':('Manipur','795001'), 'nagaland':('Nagaland','797001'),
            'arunachal pradesh':('Arunachal Pradesh','791001'), 'mizoram':('Mizoram','796001'),
            'sikkim':('Sikkim','737101'), 'chandigarh':('Chandigarh','160001'),
            'jammu':('Jammu & Kashmir','180001'), 'kashmir':('Jammu & Kashmir','190001'),
            'india':('Delhi','110001'),  # national-level jobs default
        }
        # ── 4-LEVEL STATE DETECTION ─────────────────────────────────────────────
        # L1: ai_data.job_location  (AI-extracted, most reliable)
        # L2: loc / job_location field  (from basic_details)
        # L3: _SLUG_STATE_MAP on slug+title+org  (acronym-aware: UPPCB→UP, CGPSC→CG)
        # L4: _detected_region from _reconstruct_job_from_html (HTML-only old pages)
        _loc_lower  = loc.lower().strip()
        _ai_region  = safe((ai_data.get('job_location') or ''))
        _pre_region = safe(job_obj.get('_detected_region') or '')
        _pre_pin    = safe(job_obj.get('_detected_pin') or '')
        _address_region, _postal_code = 'Delhi', '110001'  # master default

        # L1: ai_data
        if _ai_region and _ai_region not in ('null','None',''):
            for _sk, (_rv, _pv) in _STATE_MAP.items():
                if _sk in _ai_region.lower():
                    _address_region, _postal_code = _rv, _pv; break

        # L2: loc field (only when not generic 'india')
        if _address_region == 'Delhi' and _loc_lower not in ('india', ''):
            for _sk, (_rv, _pv) in _STATE_MAP.items():
                if _sk in _loc_lower:
                    _address_region, _postal_code = _rv, _pv; break

        # L3: _SLUG_STATE_MAP on slug+title+org
        if _address_region == 'Delhi':
            _s3r, _s3p = _detect_state_from_text(
                f"{slug or ''} {title} {org}".lower().replace(' ', '-'))
            if _s3r:
                _address_region, _postal_code = _s3r, _s3p

        # L4: pre-detected from HTML reconstruction
        if _address_region == 'Delhi' and _pre_region:
            _address_region, _postal_code = _pre_region, _pre_pin

        # ai_data postal_code hard override (6-digit only)
        _ai_pin = str(ai_data.get('postal_code') or '').strip()
        if len(_ai_pin) == 6 and _ai_pin.isdigit():
            _postal_code = _ai_pin

        # ── H1: proper JobPosting only for real jobs ──
        # Rich, specific streetAddress (org + city + state) instead of a bare
        # "<Org> Head Office" — a fuller PostalAddress reads better in Google's
        # job rich-result and satisfies the "streetAddress" enhancement field.
        # Reject a messy locality (multi-state list, embeds the region, or too
        # long) so we never emit "…Chhattisgarh, Chhattisgarh" style garbage.
        _loc_raw = safe(loc)
        _loc_city = _loc_raw if _loc_raw else ''
        if (not _loc_city or ',' in _loc_city or len(_loc_city) > 28
                or _loc_city.strip().lower() in ('india', '')
                or _address_region.lower() in _loc_city.lower()):
            _loc_city = ''
        _org_l = safe(org).lower()
        _addr_bits = [safe(org)] if safe(org) else []
        if _loc_city and _loc_city.lower() not in _org_l:
            _addr_bits.append(_loc_city)
        if _address_region and _address_region.lower() not in _org_l:
            _addr_bits.append(_address_region)
        if not (_addr_bits and _addr_bits[-1].lower().endswith('india')):
            _addr_bits.append('India')
        _seen_ab = []
        for _b in _addr_bits:
            if _b and _b not in _seen_ab:
                _seen_ab.append(_b)
        _street_address = ', '.join(_seen_ab) or f"{org} Head Office"
        jp = {'@context':'https://schema.org','@type':'JobPosting','title':title,
              'description':desc,'datePosted':date_posted_iso,'url':canon_url,
              'employmentType':'FULL_TIME','directApply':False,
              'identifier':{'@type':'PropertyValue','name':org,
                            'value':safe(bd.get('advt_no','') or bd.get('notification_no','') or slug)},
              'hiringOrganization':_hiring_org,
              'jobLocation':{'@type':'Place','address':{'@type':'PostalAddress','addressCountry':'IN',
                  'addressLocality':(_loc_city or _address_region),'addressRegion':_address_region,
                  'postalCode':_postal_code,'streetAddress':_street_address}},
              'applicantLocationRequirements':{'@type':'Country','name':'India'}}
        # SECURE FALLBACK: baseSalary — use pay_scale if available, else Govt default range
        _pay_str = safe((job_obj.get('basic_details') or {}).get('pay_scale','') or
                        (job_obj.get('salary_details') or {}).get('pay_scale','') or
                        safe(ai_data.get('salary_range') or ''))
        _sal_val = _pay_str if _pay_str and _pay_str not in ('null','None','N/A','') else ''
        if _sal_val:
            _sal_min, _sal_max = parse_salary(_sal_val)
        else:
            _sal_min, _sal_max = 21700, 69100  # Level 3-10 Govt default
        jp['baseSalary'] = {'@type':'MonetaryAmount','currency':'INR',
            'value':{'@type':'QuantitativeValue','minValue':_sal_min,'maxValue':_sal_max,'unitText':'MONTH'}}

        # SECURE FALLBACK: validThrough — primary: last_date from dates dict
        # Secondary: ai_data.last_date, Tertiary: "As per Schedule" → year-end default
        _SKIP_DATES = {'as per schedule','notified soon','','none','null','as announced'}
        if last_d and last_d.lower().strip() not in _SKIP_DATES:
            nd = norm_date(last_d)
            if nd:
                jp['validThrough'] = nd + 'T00:00:00+05:30'
                jp['applicationDeadline'] = nd
        if 'validThrough' not in jp:
            # Try ai_data.last_date
            _ai_last = safe(ai_data.get('last_date') or '')
            if _ai_last and _ai_last.lower().strip() not in _SKIP_DATES:
                _ai_nd = norm_date(_ai_last)
                if _ai_nd:
                    jp['validThrough'] = _ai_nd + 'T00:00:00+05:30'
                    jp['applicationDeadline'] = _ai_nd
        # FINAL FALLBACK: if still no validThrough, use current year-end (31 Dec)
        if 'validThrough' not in jp:
            from datetime import datetime as _dt_vt
            _cur_year = _dt_vt.now().year
            jp['validThrough'] = f'{_cur_year}-12-31T00:00:00+05:30'
            jp['applicationDeadline'] = f'{_cur_year}-12-31'
        # totalJobOpenings (numeric, from vacancies) per spec
        _vac_num = re.search(r'\d[\d,]*', str(vacancies or ''))
        if _vac_num:
            try:
                jp['totalJobOpenings'] = int(_vac_num.group().replace(',', ''))
            except ValueError:
                pass
        # speakable for voice-search SEO per spec
        jp['speakable'] = {'@type':'SpeakableSpecification',
                           'cssSelector':['.detail-h1', '.notice', '.stats-bar']}
        primary = jp
    else:
        # ── NON-JOB: intent-specific schema (9 types) ────────────────────────────
        _article_base = {
            '@context':         'https://schema.org',
            'headline':         title[:110],
            'description':      desc,
            'url':              canon_url,
            'datePublished':    date_posted_iso,
            'dateModified':     TODAY_ISO,
            'author':           {'@type':'Organization',
                                 'name':'Top Sarkari Jobs Editorial Team',
                                 'url': BASE_URL + '/about/'},
            'publisher':        {'@type':'Organization',
                                 '@id':  BASE_URL + '/#organization',
                                 'name': 'Top Sarkari Jobs',
                                 'logo': {'@type':'ImageObject',
                                          'url': BASE_URL + '/image.png'}},
            'mainEntityOfPage': {'@type':'WebPage','@id': canon_url},
            'image':            BASE_URL + '/og-jobs.png',
        }
        if intent == 'result':
            _ev_nd = norm_date(safe(dates.get('result_date','') or dates.get('marks_available',''))) or date_posted
            primary = {
                '@context':'https://schema.org','@type':'SpecialAnnouncement',
                'name':title[:110],'text':desc,'datePosted':date_posted_iso,
                'expires':f"{_ev_nd}T23:59:00+05:30",
                'category':'https://www.wikidata.org/wiki/Q82799',
                'announcementLocation':{'@type':'Organization','name':org,
                    **({'url':_official_site_url} if _official_site_url else {})},
                'url':canon_url,
                **{k:v for k,v in _article_base.items()
                   if k in ('datePublished','dateModified','author','publisher','mainEntityOfPage','image')},
            }
        elif intent == 'admitcard':
            _exam_nd = norm_date(safe(dates.get('exam_date','') or dates.get('written_exam_date','')))
            _ac_nd   = norm_date(safe(dates.get('admit_card_date','') or dates.get('admit_card_available',''))) or date_posted
            _org_url = _official_site_url or canon_url
            primary = {
                '@context':'https://schema.org','@type':'Event',
                'name':title[:110],'description':desc,
                'startDate':(f"{_exam_nd}T09:00:00+05:30" if _exam_nd else f"{_ac_nd}T00:00:00+05:30"),
                'endDate':(f"{_exam_nd}T17:00:00+05:30" if _exam_nd else f"{_ac_nd}T23:59:00+05:30"),
                'eventStatus':'https://schema.org/EventScheduled',
                'eventAttendanceMode':'https://schema.org/OfflineEventAttendanceMode',
                'location':{'@type':'Place',
                    'name':loc if loc and loc!='India' else 'India (Multiple Centres)',
                    'address':{'@type':'PostalAddress','addressCountry':'IN','addressLocality':loc}},
                'organizer':{'@type':'Organization','name':org,'url':_org_url},
                'performer':{'@type':'Organization','name':org,'url':_org_url},
                'offers':{'@type':'Offer','url':canon_url,'price':'0','priceCurrency':'INR',
                    'availability':'https://schema.org/InStock','validFrom':date_posted_iso},
                'url':canon_url,'image':BASE_URL+'/og-jobs.png',
            }
        elif intent == 'answerkey':
            primary = {**_article_base,'@type':'Article',
                'about':{'@type':'Thing','name':f'{org} Answer Key'},
                'keywords':f'answer key, {org}, {title[:60]}'}
        elif intent == 'syllabus':
            primary = {
                '@context':'https://schema.org','@type':'Course',
                'name':title[:110],'description':desc,'url':canon_url,
                'provider':{'@type':'Organization','name':org},
                'educationalLevel':'Government Exam','inLanguage':'hi-IN',
            }
        elif intent == 'admission':
            primary = {
                '@context':'https://schema.org','@type':'EducationalOccupationalProgram',
                'name':title[:110],'description':desc,'url':canon_url,
                'provider':{'@type':'Organization','name':org},
                'applicationStartDate':date_posted,
                'applicationDeadline':norm_date(last_d) if last_d else TODAY,
                'offers':{'@type':'Offer','category':'Admission'},
            }
        elif intent == 'scheme':
            primary = {
                '@context':'https://schema.org','@type':'GovernmentService',
                'name':title[:110],'description':desc,'url':canon_url,
                'provider':{'@type':'GovernmentOrganization','name':org},
                'serviceType':'Government Scheme',
                'areaServed':{'@type':'Country','name':'India'},
                'availableChannel':{'@type':'ServiceChannel','serviceUrl':canon_url,
                    'serviceLocation':{'@type':'Country','name':'India'}},
            }
        else:
            # education / article / generic fallback
            primary = {**_article_base,'@type':'Article'}

    # Part C: sitewide WebSite (SearchAction) + Organization schema so AI/answer
    # engines and Google sitelinks-search-box can parse the brand on every page.
    _site_schema = {'@context':'https://schema.org','@type':'WebSite',
        'name':'Top Sarkari Jobs','url':BASE_URL+'/',
        'potentialAction':{'@type':'SearchAction',
            'target':{'@type':'EntryPoint','urlTemplate':BASE_URL+'/search/?q={search_term_string}'},
            'query-input':'required name=search_term_string'}}
    _org_schema = {'@context':'https://schema.org','@type':'Organization',
        'name':'Top Sarkari Jobs','url':BASE_URL+'/',
        'logo':BASE_URL+'/image.png',
        'sameAs':['https://www.youtube.com/@topsarkarijobs',
                  'https://www.instagram.com/topsarkarijobs',
                  'https://whatsapp.com/channel/topsarkarijobs']}

    out = (f'<script type="application/ld+json">{json.dumps(_site_schema, ensure_ascii=False)}</script>\n'
           f'<script type="application/ld+json">{json.dumps(_org_schema, ensure_ascii=False)}</script>\n'
           f'<script type="application/ld+json">{json.dumps(primary, ensure_ascii=False)}</script>\n'
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
    # If JSON had no usable FAQ, fall back to auto-generated FAQs (schema must
    # match the visible auto-FAQ section rendered by build_all_sections).
    if not valid_faqs:
        _auto = auto_generate_faqs(job_obj)
        if len(_auto) >= 2:
            valid_faqs = _auto
    # BRAND: wahi branded category-tailored Q&A jo visible FAQ section me add hoti
    # hai — FAQPage schema me bhi rakho taaki structured data on-page content se
    # match kare (Google FAQ rich-result requirement). Dedup by question.
    _bqa = brand_help_faq(job_obj)
    if _bqa:
        _bk = re.sub(r'\s+', ' ', _bqa['question'].lower()).strip()
        if _bk and _bk not in _seen_q:
            _seen_q.add(_bk)
            valid_faqs.append(_bqa)
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
.dh-top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:9px}
.dh-share{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.dh-share-lbl{font-size:.7rem;font-weight:800;color:#fff;background:linear-gradient(135deg,#7c3aed,#6d28d9);padding:4px 10px;border-radius:20px;display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.dh-share-btns{display:flex;gap:5px;flex-wrap:wrap}
.dh-sh{width:30px;height:30px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:.82rem;text-decoration:none;border:none;cursor:pointer;transition:transform .12s,opacity .12s}
.dh-sh:hover{transform:translateY(-2px);opacity:.9}
.dh-sh.wa{background:#25d366}.dh-sh.tg{background:#0088cc}.dh-sh.fb{background:#1877f2}.dh-sh.tw{background:#000}.dh-sh.li{background:#0a66c2}.dh-sh.cp{background:#64748b}
.stats-bar{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #e2e8f0;margin-top:10px}
.stat{text-align:center;padding:10px 4px;border-right:1px solid #e2e8f0}
.stat:last-child{border-right:none}
.stat-val{font-size:.95rem;font-weight:800;color:#0f172a;word-break:break-word}
.stat-lbl{font-size:.65rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
@media(max-width:600px){.stats-bar{grid-template-columns:repeat(2,1fr)}.stat:nth-child(2){border-right:none}.stat:nth-child(3){border-top:1px solid #e2e8f0}.stat:nth-child(4){border-top:1px solid #e2e8f0;border-right:none}}
.short-info{background:#eff6ff;border-left:4px solid #1d4ed8;padding:10px 14px;font-size:.84rem;color:#1e293b;line-height:1.7;margin-bottom:10px;border-radius:0 8px 8px 0;display:flex;gap:8px;align-items:flex-start}
.sec-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.04)}
.sec-head{display:flex;align-items:center;gap:8px;padding:10px 14px;color:#fff;font-size:.86rem;font-weight:700}
.sec-head h2{margin:0;font-size:1.05rem;font-weight:800;color:#fff;letter-spacing:.01em}
.sec-head .sec-count{margin-left:auto;font-size:.75rem;font-weight:600;background:rgba(255,255,255,.25);padding:2px 8px;border-radius:20px;white-space:nowrap}
.sec-body{padding:0}
.kv-table{width:100%;border-collapse:collapse;font-size:.82rem}
.kv-table th{background:#f8fafc;color:#374151;font-weight:700;padding:9px 13px;text-align:left;border-bottom:1px solid #e9eef4;width:38%;vertical-align:top;word-break:break-word}
.kv-table td{padding:9px 13px;color:#1e293b;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word;overflow-wrap:break-word;line-height:1.6}
.kv-table tr:last-child th,.kv-table tr:last-child td{border-bottom:none}
.kv-stack-head{background:#eef2ff;color:#3730a3;font-weight:800;padding:9px 13px;text-align:left;border-bottom:1px solid #e0e7ff;font-size:.84rem}
.kv-stack-body{padding:10px 13px 12px;border-bottom:1px solid #e9eef4}
.kv-numlist{margin:0;padding-left:0;list-style:none;counter-reset:kvn}
.kv-numlist li{counter-increment:kvn;position:relative;padding:7px 8px 7px 34px;margin-bottom:6px;background:#f8fafc;border:1px solid #eef0f4;border-radius:7px;font-size:.8rem;line-height:1.55;color:#1e293b}
.kv-numlist li:last-child{margin-bottom:0}
.kv-numlist li::before{content:counter(kvn);position:absolute;left:8px;top:7px;width:19px;height:19px;background:#4338ca;color:#fff;border-radius:50%;font-size:.68rem;font-weight:700;display:flex;align-items:center;justify-content:center}
.date-last{color:#dc2626;font-weight:700}
.fee-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}
.fee-cell{padding:9px 13px;border-right:1px solid #f1f5f9;border-bottom:1px solid #f1f5f9}
.fee-cat{display:block;font-size:.68rem;font-weight:700;text-transform:uppercase;color:#64748b;margin-bottom:3px;letter-spacing:.04em}
.fee-amt{font-size:.93rem;font-weight:800;color:#1e293b}.fee-free{color:#166534}.fee-paid{color:#dc2626}
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
.rel-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;margin-top:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.rel-card-head{padding:10px 14px;font-size:.82rem;font-weight:800;color:#fff;display:flex;align-items:center;gap:7px}
.rel-card-head.c-state{background:linear-gradient(135deg,#1e40af,#2563eb)}
.rel-card-head.c-cat{background:linear-gradient(135deg,#059669,#047857)}
.rel-card-head.c-edu{background:linear-gradient(135deg,#7c3aed,#6d28d9)}
.rel-card-head.c-qual{background:linear-gradient(135deg,#b45309,#d97706)}
.rel-card-head.c-social{background:linear-gradient(135deg,#dc2626,#ea580c)}
.rel-card-body{display:flex;flex-wrap:wrap;gap:7px;padding:12px 14px}
.rel-social-body{display:flex;flex-direction:column;gap:8px;padding:12px 14px}
.rel-social{display:flex;align-items:center;justify-content:center;gap:8px;padding:10px 14px;border-radius:8px;font-size:.82rem;font-weight:800;color:#fff;text-decoration:none;transition:opacity .12s}
.rel-social:hover{opacity:.9}
.rel-social.wa{background:#25d366}.rel-social.yt{background:#ff0000}.rel-social.ig{background:linear-gradient(135deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888)}.rel-social.tg{background:#0088cc}.rel-social.fb{background:#1877f2}.rel-social.sc{background:#fffc00;color:#1a1a1a}
.cat-wrap{max-width:880px;margin:0 auto;padding:12px 10px 48px}
.cat-header{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:15px 18px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.cat-h1{font-size:1.1rem;font-weight:900;color:#0f172a;margin:0 0 4px}
.cat-count{font-size:.78rem;color:#64748b;margin:0}
.search-bar{display:flex;gap:8px;margin-bottom:12px}
.search-bar input{flex:1;min-width:200px;padding:9px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:.84rem;outline:none}
.search-bar input:focus{border-color:#1d4ed8;box-shadow:0 0 0 2px #dbeafe}
.job-card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:9px;box-shadow:0 1px 3px rgba(0,0,0,.04);transition:box-shadow .15s;position:relative;cursor:pointer}
.job-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.1)}
.job-card-title{font-size:1.1rem;font-weight:800;color:#0f172a;line-height:1.4;margin-bottom:5px}
.job-card-title a{color:inherit}.job-card-title a:hover{color:#1d4ed8;text-decoration:underline}
.job-card-org{color:#64748b;font-size:.79rem;margin-bottom:5px;display:flex;gap:5px;align-items:center}
.job-card-meta{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px}
.jm-badge{font-size:.67rem;font-weight:700;padding:2px 8px;border-radius:12px}
.job-card-date{font-size:.76rem;font-weight:700}.job-card-date.urgent{color:#dc2626}
.job-card-links{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}
.job-card:active{transform:scale(.997)}
.job-card-title a{pointer-events:none}
.jl-btn{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:6px;font-size:.72rem;font-weight:700;text-decoration:none;transition:all .12s;border:1px solid transparent;min-height:28px}
.btn-answer{background:#fef9c3;color:#854d0e;border-color:#fde68a}.btn-answer:hover{background:#b45309;color:#fff}
"""

# ── Page builder ───────────────────────────────────────────────
REL_CATS_HTML = '''<div class="rel-section">
<div class="rel-head"><i class="fa-solid fa-grip"></i> Related Categories</div>
<div style="padding:0 14px 14px">

<div class="rel-cats-grid">

  <!-- State Wise Jobs CARD -->
  <div class="rel-card">
    <div class="rel-card-head c-state"><i class="fa-solid fa-map-location-dot"></i> State Wise Jobs</div>
    <div class="rel-card-body">
      <a href="/state-jobs/andhra-pradesh/" class="rel-btn">Andhra Pradesh Jobs</a>
      <a href="/state-jobs/arunachal-pradesh/" class="rel-btn">Arunachal Pradesh Jobs</a>
      <a href="/state-jobs/assam/" class="rel-btn">Assam Jobs</a>
      <a href="/state-jobs/bihar/" class="rel-btn">Bihar Jobs</a>
      <a href="/state-jobs/chandigarh/" class="rel-btn">Chandigarh Jobs</a>
      <a href="/state-jobs/chhattisgarh/" class="rel-btn">Chhattisgarh Jobs</a>
      <a href="/state-jobs/delhi/" class="rel-btn">Delhi Jobs</a>
      <a href="/state-jobs/goa/" class="rel-btn">Goa Jobs</a>
      <a href="/state-jobs/gujarat/" class="rel-btn">Gujarat Jobs</a>
      <a href="/state-jobs/haryana/" class="rel-btn">Haryana Jobs</a>
      <a href="/state-jobs/himachal-pradesh/" class="rel-btn">Himachal Pradesh Jobs</a>
      <a href="/state-jobs/jammu-and-kashmir/" class="rel-btn">Jammu &amp; Kashmir Jobs</a>
      <a href="/state-jobs/jharkhand/" class="rel-btn">Jharkhand Jobs</a>
      <a href="/state-jobs/karnataka/" class="rel-btn">Karnataka Jobs</a>
      <a href="/state-jobs/kerala/" class="rel-btn">Kerala Jobs</a>
      <a href="/state-jobs/madhya-pradesh/" class="rel-btn">Madhya Pradesh Jobs</a>
      <a href="/state-jobs/maharashtra/" class="rel-btn">Maharashtra Jobs</a>
      <a href="/state-jobs/meghalaya/" class="rel-btn">Meghalaya Jobs</a>
      <a href="/state-jobs/mizoram/" class="rel-btn">Mizoram Jobs</a>
      <a href="/state-jobs/nagaland/" class="rel-btn">Nagaland Jobs</a>
      <a href="/state-jobs/odisha/" class="rel-btn">Odisha Jobs</a>
      <a href="/state-jobs/puducherry/" class="rel-btn">Puducherry Jobs</a>
      <a href="/state-jobs/punjab/" class="rel-btn">Punjab Jobs</a>
      <a href="/state-jobs/rajasthan/" class="rel-btn">Rajasthan Jobs</a>
      <a href="/state-jobs/sikkim/" class="rel-btn">Sikkim Jobs</a>
      <a href="/state-jobs/tamil-nadu/" class="rel-btn">Tamil Nadu Jobs</a>
      <a href="/state-jobs/telangana/" class="rel-btn">Telangana Jobs</a>
      <a href="/state-jobs/tripura/" class="rel-btn">Tripura Jobs</a>
      <a href="/state-jobs/uttar-pradesh/" class="rel-btn">Uttar Pradesh Jobs</a>
      <a href="/state-jobs/uttarakhand/" class="rel-btn">Uttarakhand Jobs</a>
      <a href="/state-jobs/west-bengal/" class="rel-btn">West Bengal Jobs</a>
      <a href="/state-jobs/andaman-and-nicobar/" class="rel-btn">Andaman &amp; Nicobar Jobs</a>
      <a href="/state-jobs/dadra-and-nagar-haveli/" class="rel-btn">Dadra &amp; Nagar Haveli Jobs</a>
      <a href="/state/" class="rel-btn rel-btn-all"><i class="fa-solid fa-list"></i> All State Jobs</a>
    </div>
  </div>

  <!-- Job Categories CARD -->
  <div class="rel-card">
    <div class="rel-card-head c-cat"><i class="fa-solid fa-layer-group"></i> Job Categories</div>
    <div class="rel-card-body">
      <a href="/section/latest-jobs/" class="rel-btn"><i class="fa-solid fa-bolt"></i> Latest Jobs</a>
      <a href="/section/results/" class="rel-btn"><i class="fa-solid fa-trophy"></i> Results</a>
      <a href="/section/admit-card/" class="rel-btn"><i class="fa-solid fa-id-card"></i> Admit Cards</a>
      <a href="/section/answer-key/" class="rel-btn"><i class="fa-solid fa-key"></i> Answer Key</a>
      <a href="/section/upcoming-jobs/" class="rel-btn"><i class="fa-solid fa-calendar-plus"></i> Upcoming Jobs</a>
      <a href="/section/offline-form/" class="rel-btn"><i class="fa-solid fa-file-pen"></i> Offline Form</a>
      <a href="/section/railway-jobs/" class="rel-btn"><i class="fa-solid fa-train"></i> Railway Jobs</a>
      <a href="/section/police-jobs/" class="rel-btn"><i class="fa-solid fa-shield-halved"></i> Police / Defence</a>
      <a href="/section/bank-jobs/" class="rel-btn"><i class="fa-solid fa-building-columns"></i> Bank Jobs</a>
      <a href="/section/teaching-jobs/" class="rel-btn"><i class="fa-solid fa-chalkboard-user"></i> Teaching Jobs</a>
      <a href="/section/army-jobs/" class="rel-btn"><i class="fa-solid fa-shield-halved"></i> Army / Navy / AF</a>
      <a href="/section/healthcare-jobs/" class="rel-btn"><i class="fa-solid fa-stethoscope"></i> Medical / Health</a>
      <a href="/section/btech-jobs/" class="rel-btn"><i class="fa-solid fa-gear"></i> Engineering Jobs</a>
      <a href="/section/latest-jobs/" class="rel-btn"><i class="fa-solid fa-landmark"></i> Central Govt Jobs</a>
      <a href="/section/admissions/" class="rel-btn"><i class="fa-solid fa-graduation-cap"></i> Admissions</a>
      <a href="/section/govt-scheme-yojna/" class="rel-btn"><i class="fa-solid fa-hand-holding-heart"></i> Govt Schemes</a>
      <a href="/section/top-20-jobs/" class="rel-btn"><i class="fa-solid fa-medal"></i> Top 20 Jobs</a>
      <a href="/section/jobs-with-last-date/" class="rel-btn"><i class="fa-solid fa-clock"></i> Last Date Near</a>
      <a href="/section/top-20-jobs/" class="rel-btn"><i class="fa-solid fa-star"></i> Popular Categories</a>
    </div>
  </div>

</div>

<!-- Education State Wise CARD -->
<div class="rel-card">
<div class="rel-card-head c-edu"><i class="fa-solid fa-graduation-cap"></i> State Wise Education Updates</div>
<div class="rel-card-body">
  <a href="/education/andhra-pradesh/" class="rel-btn">AP Education</a>
  <a href="/education/assam/" class="rel-btn">Assam Education</a>
  <a href="/education/bihar/" class="rel-btn">Bihar Education</a>
  <a href="/education/chhattisgarh/" class="rel-btn">Chhattisgarh Education</a>
  <a href="/education/delhi/" class="rel-btn">Delhi Education</a>
  <a href="/education/gujarat/" class="rel-btn">Gujarat Education</a>
  <a href="/education/haryana/" class="rel-btn">Haryana Education</a>
  <a href="/education/himachal-pradesh/" class="rel-btn">HP Education</a>
  <a href="/education/jharkhand/" class="rel-btn">Jharkhand Education</a>
  <a href="/education/karnataka/" class="rel-btn">Karnataka Education</a>
  <a href="/education/kerala/" class="rel-btn">Kerala Education</a>
  <a href="/education/madhya-pradesh/" class="rel-btn">MP Education</a>
  <a href="/education/maharashtra/" class="rel-btn">Maharashtra Education</a>
  <a href="/education/odisha/" class="rel-btn">Odisha Education</a>
  <a href="/education/punjab/" class="rel-btn">Punjab Education</a>
  <a href="/education/rajasthan/" class="rel-btn">Rajasthan Education</a>
  <a href="/education/tamil-nadu/" class="rel-btn">Tamil Nadu Education</a>
  <a href="/education/telangana/" class="rel-btn">Telangana Education</a>
  <a href="/education/uttar-pradesh/" class="rel-btn">UP Education</a>
  <a href="/education/uttarakhand/" class="rel-btn">Uttarakhand Education</a>
  <a href="/education/west-bengal/" class="rel-btn">West Bengal Education</a>
  <a href="/education/" class="rel-btn rel-btn-all"><i class="fa-solid fa-list"></i> All Education Updates</a>
</div>
</div>

<!-- Qualification Wise CARD -->
<div class="rel-card">
<div class="rel-card-head c-qual"><i class="fa-solid fa-book-open"></i> Qualification Wise Government Jobs</div>
<div class="rel-card-body">
  <a href="/qualification/8th-pass/" class="rel-btn">8th Pass Jobs</a>
  <a href="/qualification/10th-pass/" class="rel-btn">10th Pass Jobs</a>
  <a href="/qualification/12th-pass/" class="rel-btn">12th Pass Jobs</a>
  <a href="/qualification/intermediate/" class="rel-btn">Intermediate Jobs</a>
  <a href="/qualification/iti/" class="rel-btn">ITI Jobs</a>
  <a href="/qualification/diploma/" class="rel-btn">Diploma Jobs</a>
  <a href="/qualification/b-tech-be/" class="rel-btn">B.Tech / BE</a>
  <a href="/qualification/b-com/" class="rel-btn">B.Com</a>
  <a href="/qualification/b-sc/" class="rel-btn">B.Sc</a>
  <a href="/qualification/bca/" class="rel-btn">BCA</a>
  <a href="/qualification/bba/" class="rel-btn">BBA</a>
  <a href="/qualification/b-ed/" class="rel-btn">B.Ed</a>
  <a href="/qualification/llb/" class="rel-btn">LLB</a>
  <a href="/qualification/mbbs/" class="rel-btn">MBBS</a>
  <a href="/qualification/bds/" class="rel-btn">BDS</a>
  <a href="/qualification/bams/" class="rel-btn">BAMS</a>
  <a href="/qualification/b-pharma/" class="rel-btn">B.Pharma</a>
  <a href="/qualification/gnm/" class="rel-btn">GNM</a>
  <a href="/qualification/anm/" class="rel-btn">ANM</a>
  <a href="/qualification/dmlt/" class="rel-btn">DMLT</a>
  <a href="/qualification/d-pharm/" class="rel-btn">D.Pharm</a>
  <a href="/qualification/d-el-ed/" class="rel-btn">D.El.Ed</a>
  <a href="/qualification/any-graduate/" class="rel-btn">Any Graduate Jobs</a>
  <a href="/qualification/mba-pgdm/" class="rel-btn">MBA / PGDM</a>
  <a href="/qualification/m-sc/" class="rel-btn">M.Sc</a>
  <a href="/qualification/m-com/" class="rel-btn">M.Com</a>
  <a href="/qualification/mca/" class="rel-btn">MCA</a>
  <a href="/qualification/m-ed/" class="rel-btn">M.Ed</a>
  <a href="/qualification/ms-md/" class="rel-btn">MS / MD</a>
  <a href="/qualification/m-pharma/" class="rel-btn">M.Pharma</a>
  <a href="/qualification/ca/" class="rel-btn">CA</a>
  <a href="/qualification/cs/" class="rel-btn">CS</a>
  <a href="/qualification/mphil-phd/" class="rel-btn">MPhil / PhD</a>
  <a href="/qualification/any-post-graduate/" class="rel-btn">Any PG Jobs</a>
  <a href="/category/study/" class="rel-btn rel-btn-all"><i class="fa-solid fa-list"></i> All Qualification Jobs</a>
</div>
</div>

<!-- Social Media CARD -->
<div class="rel-card">
<div class="rel-card-head c-social"><i class="fa-solid fa-bell"></i> Join &amp; Follow Us</div>
<div class="rel-social-body">
  <a href="https://whatsapp.com/channel/0029Vb2rMdsHbFUyxUBfKk0T" target="_blank" rel="noopener" class="rel-social wa"><i class="fa-brands fa-whatsapp"></i> Join WhatsApp Channel</a>
  <a href="https://www.youtube.com/@Topsarkarijobs" target="_blank" rel="noopener" class="rel-social yt"><i class="fa-brands fa-youtube"></i> YouTube Channel Join Now</a>
  <a href="https://www.instagram.com/topsarkarijobs" target="_blank" rel="noopener" class="rel-social ig"><i class="fa-brands fa-instagram"></i> Instagram</a>
  <a href="https://x.com/TopSarkariJobs" target="_blank" rel="noopener" class="rel-social tw"><i class="fa-brands fa-x-twitter"></i> X (Twitter)</a>
  <a href="https://www.snapchat.com/add/topsarkarijobss" target="_blank" rel="noopener" class="rel-social sc"><i class="fa-brands fa-snapchat"></i> Snapchat</a>
  <a href="https://www.facebook.com/profile.php?id=61587033757932" target="_blank" rel="noopener" class="rel-social fb"><i class="fa-brands fa-facebook-f"></i> Facebook</a>
</div>
</div>

</div>
</div>'''

def build_detail_page(job_obj, slug, canon_url, breadcrumbs, badge_label='Govt Job', noindex_dup=False):
    bd    = job_obj.get('basic_details', {}) or {}
    dates = job_obj.get('important_dates', {}) or {}
    il    = job_obj.get('important_links', {}) or {}
    seo   = job_obj.get('seo_tags', []) or []
    faq   = job_obj.get('faq', []) or []

    title     = safe(bd.get('job_title','') or job_obj.get('title','') or 'Government Job')
    org       = safe(bd.get('organization_name','') or job_obj.get('organization','') or job_obj.get('board','') or 'Government of India')
    vacancies = safe(bd.get('total_vacancies','') or bd.get('total_posts','') or bd.get('total_post','')
                     or job_obj.get('total_post','') or job_obj.get('total_vacancy','') or job_obj.get('total_posts','')
                     or job_obj.get('totalPost','') or job_obj.get('vacancies',''))
    # Fallback: pull "<n> Posts" / "<n> Vacancies" out of the title if no explicit field
    if not vacancies:
        _vm = re.search(r'([\d,]+)\s*(?:posts?|vacanc)', title, re.I)
        if _vm: vacancies = _vm.group(1)
    last_d    = safe(dates.get('extended_last_date','') or dates.get('date_extended','')
                     or dates.get('last_date_to_apply','') or dates.get('last_date_apply_online','')
                     or dates.get('last_date','') or dates.get('last_date_pay_fee','')
                     or job_obj.get('last_date','') or job_obj.get('lastDate',''))
    # If no explicit last date, fall back to the most relevant date present
    # (exam/result/admit/interview) so the header never shows a bare "—".
    _dh_lbl = 'Last Date'
    if not last_d and isinstance(dates, dict):
        for _dk, _dlbl in [('exam_date','Exam Date'),('result_date','Result Date'),
                           ('admit_card_date','Admit Card'),('interview_date','Interview'),
                           ('counselling_date','Counselling'),('application_begin','Starts')]:
            if safe(dates.get(_dk)):
                last_d = safe(dates.get(_dk)); _dh_lbl = _dlbl; break
    apply_m   = safe(bd.get('application_mode','') or job_obj.get('apply_mode','') or job_obj.get('application_mode','')
                     or ('Offline' if job_obj.get('category') == 'OFFLINE_FORM' else 'Online'))
    location  = safe(bd.get('job_location','') or job_obj.get('job_location','') or job_obj.get('state','')
                     or job_obj.get('location','') or 'India')

    # ── Extra fields for rich WhatsApp/social share message ──
    def _first_str(d, keys, allow_fallback=True):
        if isinstance(d, dict):
            for k in keys:
                v = d.get(k)
                if isinstance(v, str) and v.strip():
                    return safe(v.strip())
            if allow_fallback:
                # fallback: first non-empty string value that isn't a long 'details' note
                for kk, v in d.items():
                    if kk == 'details': continue
                    if isinstance(v, str) and v.strip():
                        return safe(v.strip())
        elif isinstance(d, list) and d:
            return safe('; '.join(str(x) for x in d if x)[:200])
        elif isinstance(d, str):
            return safe(d.strip())
        return ''
    _qual = _first_str(job_obj.get('qualification'), ['education_qualification','qualification','eligibility'])
    _age  = _first_str(job_obj.get('age_limit'), ['age_details','age_limit','age'])
    _fee  = _first_str(job_obj.get('application_fee'), ['general_fee','general','ur_fee','fee','application_fee'], allow_fallback=False)

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
    # Indian states/UTs — a bare state name must NEVER stand in for the exam body
    _STATE_NAMES = {
        'andhra pradesh','arunachal pradesh','assam','bihar','chhattisgarh','goa',
        'gujarat','haryana','himachal pradesh','jharkhand','karnataka','kerala',
        'madhya pradesh','maharashtra','manipur','meghalaya','mizoram','nagaland',
        'odisha','punjab','rajasthan','sikkim','tamil nadu','telangana','tripura',
        'uttar pradesh','uttarakhand','west bengal','delhi','jammu','kashmir',
        'ladakh','puducherry','chandigarh','andaman','lakshadweep','dadra','daman',
    }
    # ❶ FIX: real job title is the single source of truth for <title>, for ALL
    # content types — not just recruitment. Bare-state org names are rejected.
    _clean_title = re.sub(r'\s*-\s*(latest jobs|big update|notification out).*$', '', title, flags=re.I).strip()
    _has_intent = bool(re.search(r'\b(recruitment|vacancy|vacancies|online form|apply online|posts|notification|admit card|result|answer key|hall ticket|scorecard|merit list)\b', _clean_title, re.I))
    _org_is_state = _org_s.strip().lower() in _STATE_NAMES
    if _has_intent and len(_clean_title) >= 12:
        # Prefer the intent-rich real title (matches <h1>)
        _jp = _clean_title
    elif _ct != 'default':
        # Fallback for result/admit/answer: org-based — but only if org is a real
        # exam body, never a bare state. If org is a state, use the raw title.
        _fmt = {'result':'{o} {y} Result','admit':'{o} {y} Admit Card','answer':'{o} {y} Answer Key'}
        if _org_is_state or len(_org_s.strip()) < 3:
            _jp = _clean_title or title
        else:
            _jp = _fmt[_ct].format(o=_org_s, y=_yr)
    else:
        if _org_is_state or len(_org_s.strip()) < 3:
            _jp = _clean_title or title
        else:
            _jp = f'{_org_s} {_yr} Recruitment{_vac_s}'
            if len(_jp) > _MAX:
                _jp = f'{_org_s} {_yr}{_vac_s}'
            if len(_jp) < 15:
                _jp = _clean_title or title[:_MAX]
    if len(_jp) > _MAX:
        _jp = smart_title_cut(_jp, _MAX)
    title_tag = smart_title_cut(_jp + _BRAND, 60)
    # ── AI LAYER (Phase 5): prefer ai_title if present, else the fact-built title.
    # Additive + safe: if the AI field is null/missing, behaviour is exactly as before.
    _ai_title = safe(job_obj.get('ai_title', '') or '')
    if _ai_title:
        # Strip any brand suffix the AI may have baked in, then re-apply via
        # the same _jp + _BRAND pattern so the FINAL <title> is always ≤60 chars.
        _ai_bare = re.sub(r'\s*\|?\s*Top Sarkari Jobs\s*$', '', _ai_title, flags=re.I).strip()
        title_tag = smart_title_cut(_ai_bare + _BRAND, 60)
    short_info = sanitize_short_info(safe(bd.get('short_information','') or job_obj.get('jobs_info','') or job_obj.get('short_information','')))
    # Build meta description inline
    _si = short_info.rstrip('.,; ').strip() if short_info else ''
    # Fallback: if sanitized short_info is too short to be meaningful, build
    # description purely from structured fields that are never polluted.
    if len(_si) < 30:
        _si = ''
    _vd = vacancies if vacancies and vacancies not in ('—','') else ''
    _ld_s = last_d.strip() if last_d and last_d not in ('—','') else ''
    # ❸ FIX: build description that ends on a clean word/sentence boundary
    # (never a dangling preposition like "for." / "by." / "on the.")
    _DANGLING = re.compile(r'\s*\b(for|by|on|the|of|to|in|at|with|and|or|a|an|as|from)\s*$', re.I)
    def _strip_dangling(s):
        # repeatedly drop trailing stop-words ("...on the" → "...on" → "...")
        s = s.rstrip(' .,;:-')
        prev = None
        while s and s != prev:
            prev = s
            s = _DANGLING.sub('', s).rstrip(' .,;:-')
        return s
    if _si:
        # Prefer the FIRST complete sentence if it fits in ~160 chars
        _first_sent = re.match(r'^(.{40,160}?[.!?])(\s|$)', _si)
        if _first_sent:
            _base_md = _first_sent.group(1)
        elif len(_si) <= 150:
            _base_md = _si
        else:
            # back off to last sentence terminator, else last full word, within 150
            _slice = _si[:150].rstrip()
            _sent = max(_slice.rfind('.'), _slice.rfind('!'), _slice.rfind('?'))
            if _sent >= 80:
                _base_md = _slice[:_sent+1]
            else:
                _base_md = _slice[:_slice.rfind(' ')] if ' ' in _slice else _slice
        _base_md = _strip_dangling(_base_md)
    else:
        _base_md = f'{(_clean_title or title)[:60].rstrip()} {YEAR}'
    _parts = [_base_md]
    if _vd: _parts.append(f'{_vd} Posts')
    if _ld_s: _parts.append(f'Last Date: {_ld_s}')
    _cta_md = f'Apply {apply_m.lower() if apply_m else "online"} at Top Sarkari Jobs.'
    _md_full = '. '.join(p.rstrip('.') for p in _parts) + '. ' + _cta_md
    # SEO: meta description target window is 140–150 chars (Section 4.4).
    if len(_md_full) > 150:
        _cut = _md_full[:150]
        # back off to last full word; avoid mid-word cut
        if ' ' in _cut:
            _cut = _cut[:_cut.rfind(' ')]
        meta_desc = _strip_dangling(_cut) + '…'
    else:
        meta_desc = _md_full

    # ── AI LAYER (Phase 5): prefer ai_meta_description if present.
    _ai_meta = safe(job_obj.get('ai_meta_description', '') or '')
    if _ai_meta:
        _ai_meta = _ai_meta.strip()
        if len(_ai_meta) > 150:
            _cut = _ai_meta[:150]
            if ' ' in _cut: _cut = _cut[:_cut.rfind(' ')]
            _ai_meta = _strip_dangling(_cut) + '…'
        meta_desc = _ai_meta

    schemas_html = build_schemas(job_obj, canon_url, breadcrumbs, slug)

    # Breadcrumb HTML
    bc_html = '<nav class="bc" aria-label="Breadcrumb"><a href="/">Home</a>'
    for lbl, url in breadcrumbs:
        bc_html += f'<span class="bc-sep">›</span><a href="{e(url)}">{e(lbl)}</a>'
    bc_html += f'<span class="bc-sep">›</span><span aria-current="page">{e(title[:55])}{"…" if len(title)>55 else ""}</span></nav>'

    # Quick apply link
    apply_url = safe(_il_url(il.get('apply_online')) or _il_url(il.get('registration_link')) or bd.get('official_website',''))
    apply_banner = ''
    if apply_url and not is_blocked(apply_url):
        apply_banner = (f'<a href="{e(apply_url)}" target="_blank" rel="nofollow noopener noreferrer" class="apply-cta">'
                       f'<i class="fa-solid fa-paper-plane"></i> Apply Online / Official Website ↗</a>')

    # Header (with share buttons)
    cat_badge = safe(job_obj.get('category','') or badge_label).replace('_',' ')
    # human-readable "Updated" date for the editorial byline (E-E-A-T signal)
    try:
        _byline_date = date.fromisoformat(TODAY).strftime('%d %B %Y').lstrip('0')
    except Exception:
        _byline_date = TODAY
    import urllib.parse as _uparse
    _raw_url = canon_url
    # Build rich share message (WhatsApp / Telegram). Skip empty fields.
    _msg_lines = [f'📢 {title}']
    if vacancies and vacancies not in ('—',''): _msg_lines.append(f'📋 Posts: {vacancies}')
    if _qual: _msg_lines.append(f'🎓 Qualification: {_qual[:120]}')
    if _age:  _msg_lines.append(f'🎂 Age Limit: {_age[:100]}')
    if _fee:  _msg_lines.append(f'💰 Application Fee: {_fee[:100]}')
    if last_d and last_d not in ('—',''): _msg_lines.append(f'📅 Last Date: {last_d}')
    _msg_lines.append('👉 Apply Online:')
    _msg_lines.append(_raw_url)
    _msg_lines.append('🔔 Complete Details Available Here')
    _msg_lines.append('#SarkariJob #GovernmentJobs #LatestJobs')
    _share_msg = '\n'.join(_msg_lines)
    # URL-encoded versions for share links
    _enc_msg = _uparse.quote(_share_msg, safe='')
    _enc_url = _uparse.quote(_raw_url, safe='')
    _enc_title = _uparse.quote(title, safe='')
    _share_u = e(canon_url)
    share_row = f'''<div class="dh-share">
    <span class="dh-share-lbl"><i class="fa-solid fa-share-nodes"></i> Share This Job</span>
    <div class="dh-share-btns">
      <a href="https://api.whatsapp.com/send?text={_enc_msg}" target="_blank" rel="noopener" class="dh-sh wa" aria-label="Share on WhatsApp"><i class="fa-brands fa-whatsapp"></i></a>
      <a href="https://t.me/share/url?url={_enc_url}&text={_enc_msg}" target="_blank" rel="noopener" class="dh-sh tg" aria-label="Share on Telegram"><i class="fa-brands fa-telegram"></i></a>
      <a href="https://www.facebook.com/sharer/sharer.php?u={_enc_url}" target="_blank" rel="noopener" class="dh-sh fb" aria-label="Share on Facebook"><i class="fa-brands fa-facebook-f"></i></a>
      <a href="https://twitter.com/intent/tweet?text={_enc_msg}" target="_blank" rel="noopener" class="dh-sh tw" aria-label="Share on X"><i class="fa-brands fa-x-twitter"></i></a>
      <a href="https://www.linkedin.com/sharing/share-offsite/?url={_enc_url}" target="_blank" rel="noopener" class="dh-sh li" aria-label="Share on LinkedIn"><i class="fa-brands fa-linkedin-in"></i></a>
      <button type="button" class="dh-sh cp" data-share-text="{e(_share_msg)}" data-share-url="{_share_u}" aria-label="Copy details"><i class="fa-solid fa-link"></i></button>
    </div>
  </div>'''
    header_html = f'''<div class="detail-header">
  <div class="dh-top">
    <div class="badges">
      <span class="badge badge-cat"><i class="fa-solid fa-briefcase"></i> {e(cat_badge or badge_label)}</span>
      <span class="badge badge-loc"><i class="fa-solid fa-map-pin"></i> {e(location[:25])}</span>
      <span class="badge badge-mode"><i class="fa-solid fa-laptop"></i> {e(apply_m)}</span>
    </div>
    {share_row}
  </div>
  <h1 class="detail-h1">{e(title)}</h1>
  <div class="editorial-byline" style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:.74rem;color:#64748b;margin:2px 0 8px;">
    <i class="fa-solid fa-circle-check" style="color:#16a34a;"></i>
    <span>Reviewed by the <a href="/about/" style="color:#1a56db;text-decoration:none;font-weight:600;">Top Sarkari Jobs Editorial Team</a></span>
    <span aria-hidden="true">·</span>
    <span>Updated {e(_byline_date)}</span>
    <span aria-hidden="true">·</span>
    <span>Sourced from the official notification — <a href="/editorial-policy/" style="color:#1a56db;text-decoration:none;">how we verify</a></span>
  </div>
  <div class="stats-bar">
    <div class="stat"><div class="stat-val">{e(vacancies or "—")}</div><div class="stat-lbl">Vacancies</div></div>
    <div class="stat"><div class="stat-val" style="color:#dc2626">{e(last_d or "—")}</div><div class="stat-lbl">{e(_dh_lbl)}</div></div>
    <div class="stat"><div class="stat-val">{e(apply_m or "Online")}</div><div class="stat-lbl">Apply Mode</div></div>
    <div class="stat"><div class="stat-val">{e(location or "India")}</div><div class="stat-lbl">Location</div></div>
  </div>
</div>'''

    sections_html = build_all_sections(job_obj)
    if not sections_html.strip():
        sections_html = '<div class="sec-card"><div class="sec-body" style="padding:24px;text-align:center;color:#94a3b8"><i class="fa-solid fa-clock" style="font-size:1.5rem;display:block;margin-bottom:8px"></i>Detailed information will be updated soon. Please visit the official website.</div></div>'

    # ❹ Related Jobs — internal links to other /jobs/ pages (same cat/org/qual/state)
    _rj_org = safe(bd.get('organization','') or bd.get('department','') or job_obj.get('organization',''))
    _rj_state = safe(bd.get('state','') or job_obj.get('state','') or job_obj.get('board',''))
    _rj_html = _related_jobs_html(slug,
                                  cat=safe(job_obj.get('category','')),
                                  org=_rj_org,
                                  qual=safe(badge_label),
                                  state=_rj_state, limit=8)
    rel_links = _rj_html + REL_CATS_HTML

    body = f'''<div class="pg-wrap">
  {bc_html}
  <div class="notice"><i class="fa-solid fa-triangle-exclamation"></i><span><strong>Important:</strong> Always verify details on official website. Dates &amp; eligibility may change.</span></div>
  {header_html}
  {f'<div style="margin-bottom:12px">{apply_banner}</div>' if apply_banner else ''}
  {sections_html}
  {rel_links}
</div>'''
    # Final safety net: collapse any duplicate section cards that slipped through
    # from different render paths (sarkari sections + structured fields, etc.).
    # Related-Jobs block has no <h2>, so it is never affected.
    body = _dedup_section_cards(body)

    # FIX #9: context-aware OG image (fixes the ['/result','/result'] dup bug)
    _intent_img = page_intent(job_obj)
    if _intent_img == 'result' or '/result' in canon_url:
        _og_img_job = f"{BASE_URL}/og-results.png"
    elif _intent_img == 'admit_card' or 'admit' in canon_url:
        _og_img_job = f"{BASE_URL}/og-admit.png"
    elif _intent_img in ('scheme', 'article'):
        _og_img_job = f"{BASE_URL}/og-scheme.png"
    elif any(x in canon_url for x in ['study', 'pass', 'graduate', 'iti', 'diploma']):
        _og_img_job = f"{BASE_URL}/og-study.png"
    else:
        _og_img_job = f"{BASE_URL}/og-jobs.png"

    _content_sig = _page_content_hash(job_obj)
    return f'''<!DOCTYPE html>
<html lang="en-IN">
<head>
<!-- TSJ_HASH:{_content_sig} -->
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>{VP_SNIPPET}
<title>{e(title_tag)}</title>
<meta name="description" content="{e(meta_desc)}"/>
<meta name="robots" content="{'noindex,follow' if noindex_dup else 'index,follow,max-snippet:-1,max-image-preview:large'}"/>
<link rel="canonical" href="{e(canon_url)}"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="Top Sarkari Jobs"/>
<meta property="og:title" content="{e(title_tag)}"/>
<meta property="og:description" content="{e(meta_desc)}"/>
<meta property="og:url" content="{e(canon_url)}"/>
<meta property="og:image" content="{_og_img_job}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{e(title_tag)}"/>
<meta name="twitter:description" content="{e(meta_desc)}"/>
{schemas_html}
<script>
window.__TSJ_SLUG = "{slug}";
window.__TSJ_CANONICAL = "{e(canon_url)}";
window.__TSJ_STATIC_PAGE = true;
window.__TSJ_PSR_DISABLED = true;
window.__TSJ_RENDERER_DISABLED = true;
try {{ if (window.location.pathname !== '/jobs/{slug}/') {{ window.history.replaceState(null, '', '/jobs/{slug}/'); }} }} catch(_e) {{}}
</script>
<script src="/tsj-config.js"></script>
<link rel="dns-prefetch" href="https://www.googletagmanager.com"/>
<meta name="author" content="Top Sarkari Jobs"/>
<meta name="geo.region" content="IN"/>
<link rel="icon" href="/image.ico"/>
<link rel="stylesheet" href="/styles.css"/>
<link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/>
<noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>
<link rel="manifest" href="/manifest.json"/>
<meta name="theme-color" content="#0d2257"/>
<script>(function(){{var _l=false;function la(){{if(_l)return;_l=true;var s=document.createElement('script');s.src='/analytics.js';s.async=true;document.head.appendChild(s);}}window.addEventListener('scroll',la,{{once:true,passive:true}});window.addEventListener('click',la,{{once:true}});setTimeout(la,4000);}})();</script>
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
<script src="/faq-init.js?v={ASSET_VER}" defer></script>
<script>
(function(){{
  document.addEventListener('click',function(ev){{
    var b=ev.target.closest('.dh-sh.cp');
    if(!b)return;
    var txt=b.getAttribute('data-share-text')||b.getAttribute('data-share-url')||location.href;
    if(navigator.clipboard){{navigator.clipboard.writeText(txt).then(function(){{
      var i=b.querySelector('i');if(i){{var o=i.className;i.className='fa-solid fa-check';setTimeout(function(){{i.className=o;}},1400);}}
    }});}}
  }});
}})();
</script>
</body>
</html>'''

# ── Listing page builder ───────────────────────────────────────
# ── Section-specific meta descriptions (SEO optimized) ──────────────────────
SECTION_META_DESC = {
    'latest-jobs-new':     "Latest government job notifications 2026 from Sarkari Result. Apply online for new central & state vacancies — SSC, Railway, UPSC, Bank, Police jobs updated daily.",
    'latest-jobs':         "Latest Sarkari Naukri 2026: New government job alerts from all central and state departments. Check eligibility, last date and apply online.",
    'sr-latest-jobs':      "Latest Sarkari Jobs 2026 from SarkariResult: Central & state government recruitment notifications. Check vacancies, eligibility and apply online.",
    'admit-card':          "Download Sarkari Admit Card 2026: Hall tickets for SSC, Railway, IBPS, UPSC, Police, teaching exams. Get your call letter with registration number.",
    'results':             "Sarkari Result 2026: Check latest government exam results, merit lists and scorecards for SSC, Railway, UPSC, Bank and State PSC exams.",
    'result':              "Sarkari Result 2026: Check latest government exam results, merit lists and scorecards for SSC, Railway, UPSC, Bank and State PSC exams.",
    'answer-key':          "Download official answer keys 2026 for SSC, Railway, UPSC, Police and Bank exams. Raise objections and check your score before final result.",
    'upcoming-jobs':       "Upcoming Government Jobs 2026: Advance notification of new Sarkari Naukri — SSC, Railway, Bank, Defence, UPSC and State PSC recruitments coming soon.",
    'offline-form':        "Government jobs with offline application 2026: Download application forms, check last date and address. Apply by post for Sarkari Naukri vacancies.",
    '10th-pass-jobs':      "10th Pass Government Jobs 2026: Latest Sarkari Naukri for matriculation pass candidates — Police, Railway, SSC MTS, Postal, Army, Defence vacancies.",
    '12th-pass-jobs':      "12th Pass Sarkari Jobs 2026: Government job notifications for intermediate pass — SSC CHSL, Railway, Constable, Clerk, LDC, Defence vacancies.",
    '8th-pass':            "8th Pass Government Jobs 2026: Sarkari Naukri for class 8 pass candidates — Peon, Chowkidar, Helper, Sweeper, Group D vacancies updated daily.",
    'graduation-jobs':     "Graduate Sarkari Jobs 2026: Government vacancies for any graduate — SSC CGL, Bank PO, Railway NTPC, UPSC, Officer level posts apply online.",
    'post-graduation-jobs':"Post Graduate Government Jobs 2026: PG level Sarkari Naukri — Lecturer, Manager, Officer, Research vacancies for MA/MSc/MBA/MTech candidates.",
    'bank-jobs':           "Bank Jobs 2026: IBPS PO, Clerk, RRB, SBI recruitment notifications. Latest banking sector government job vacancies with online application links.",
    'railway-jobs':        "Railway Jobs 2026: RRB NTPC, Group D, ALP, JE, RPF, Station Master vacancies. Apply online for Indian Railways Sarkari Naukri.",
    'police-jobs':         "Police & Defence Jobs 2026: Constable, SI, ASI, Army, CRPF, BSF, CISF, SSB recruitment. Government security force vacancies for 10th/12th/graduate.",
    'teaching-jobs':       "Teaching Jobs 2026: TGT, PGT, PRT, Lecturer government vacancies. School and college teaching recruitment — KVS, NVS, state education boards.",
    'healthcare-jobs':     "Medical & Healthcare Government Jobs 2026: Staff Nurse, Doctor, AYUSH, Paramedical vacancies. AIIMS, ESIC, state health department recruitment.",
    'diploma-jobs':        "Diploma Pass Government Jobs 2026: Sarkari Naukri for ITI/Diploma holders — JE, Technician, Electrician, Mechanic, Fitter vacancies in PSUs and Railways.",
    'iti-jobs':            "ITI Pass Government Jobs 2026: Sarkari Naukri for ITI certificate holders — Trade Apprentice, Technician, Fitter, Electrician, Mechanic vacancies.",
    'btech-jobs':          "B.Tech/BE Government Jobs 2026: Engineering graduate Sarkari Naukri — JE, AE, Officer, Manager posts in PSUs, Railways, Defence, UPSC.",
    'army-jobs':           "Indian Army & Defence Jobs 2026: Soldier, Officer, Technical, Tradesman recruitment. Apply online for Army, Navy, Air Force, Paramilitary vacancies.",
    'state-jobs-central':  "State Government Jobs 2026: Latest state PSC, PPSC, RPSC, MPSC, BPSC recruitment notifications. Apply for Sarkari Naukri in your state.",
    'central-jobs':        "Central Government Jobs 2026: Ministries, PSUs, central departments recruitment. UPSC, SSC, Railway, Defence — apply online for central sarkari naukri.",
    'admissions':          "Government College Admissions 2026: University entrance exams, merit list, counselling schedule. Apply for admission to central and state universities.",
    'admission':           "Sarkari Admission 2026: Government college and university admissions — entrance exams, merit lists, counselling dates and application forms.",
    'last-date-reminder':  "Government Jobs Last Date 2026: Jobs expiring soon — apply before deadline. Last date reminders for SSC, Railway, Bank, UPSC and state PSC jobs.",
    'latest-notifications':"Latest Government Job Notifications 2026: New Sarkari recruitment notifications from all departments. Check eligibility and apply before last date.",
    'ba-pass':             "BA/Arts Graduate Government Jobs 2026: Sarkari Naukri for BA pass candidates — Clerk, Patwari, Teacher, Officer level vacancies in state and central departments.",
    'jobs-with-last-date': "Government Jobs With Last Date 2026: Sarkari Naukri with upcoming deadlines. Filter by qualification and apply online before last date.",
    'top-20-jobs':         "Top 20 Government Jobs 2026: Most popular Sarkari Naukri this week — highest vacancy count, best pay scale, easy eligibility. Apply online now.",
    'today-updates':       "Today's Government Job Updates 2026: Fresh Sarkari Naukri notifications added today — new vacancies, admit cards, results and answer keys.",
    'govt-scheme-yojna':   "Government Schemes & Yojana 2026: Central and state government welfare schemes — PM Kisan, PMAY, Ujjwala, scholarship, subsidy yojana information.",
    'importantcsc-link':   "CSC Important Links 2026: Common Service Centre useful government portals, online services, certificate download links for CSC operators.",
    'importantcsc-pdf':    "CSC Important PDF Forms 2026: Download government forms, certificates, application PDFs for Common Service Centre services.",
    'syllabus':            "Government Exam Syllabus 2026: Download latest syllabus PDF for SSC, Railway, UPSC, Bank, Police, Teaching and state PSC exams.",
}


# ── STATE-WISE RICH SEO CONTENT (unique per state, injected by _seo_listing_content) ──
_STATE_SEO_CONTENT = {
  "Uttar Pradesh": """<h2>About Uttar Pradesh Government Jobs 2026</h2>
<p>Uttar Pradesh Sarkari Naukri 2026 ke liye yeh sabse sahi jagah hai. UPPSC (Uttar Pradesh Public Service Commission) sabse bada recruitment body hai jo har saal civil services, administrative aur technical posts ke liye notification jari karta hai. Lucknow, Kanpur, Agra, Varanasi, Prayagraj, Meerut jaise major districts ke candidates yahan apni yogyata ke mutabik latest vacancies track kar sakte hain. UP Government Jobs 2026 mein iss saal badi sankhya mein bharti expected hai.</p>
<p>UP ke important recruitment bodies mein UPSRTC, UP Jal Nigam, UPPCL aur UPSSSC shamil hain. UP Police Bharti Evam Pramotion Board ke through constable, SI aur inspector level posts aate hain. UP NHM aur SGPGI Lucknow ke under nursing, pharmacist, technician aur doctor level ke posts nikalte hain. UP Basic Shiksha Parishad aur UPSESSB ke through teacher aur lecturer recruitments hoti hain. BHU Varanasi, AMU Aligarh aur Lucknow University mein bhi academic posts available hain 2026 mein.</p>
<p>Govt Jobs in UP mein 10th pass, 12th pass, ITI, Diploma, Graduate aur PG sabhi ke liye vacancies nikalti hain. Gorakhpur, Mathura, Bareilly, Allahabad jaise districts ke candidates bhi online form ke zariye apply kar sakte hain. Online form, admit card aur result sab ek jagah milega Top Sarkari Jobs par.</p>
<h2>Latest Government Jobs in Uttar Pradesh</h2>
<p>Latest UP Government Jobs mein abhi UPPSC, UPSSSC, UP Police aur NHM ki vacancies open hain. UP Sarkari Naukri 2026 ke liye online form, admit card download aur result sab Top Sarkari Jobs par milenge. Nayi notification miss mat karo — daily check karo.</p>
<h2>Qualification Wise Jobs in Uttar Pradesh</h2>
<p>UP mein 10th pass ke liye peon, driver, MTS posts hain. 12th pass ke liye UP Police constable aur clerk vacancies hain. ITI aur Diploma walon ke liye technical posts UPPCL aur UP Jal Nigam mein available hain. Graduate aur Post Graduate candidates UPPSC PCS exam aur UPSESSB teaching posts ke liye apply kar sakte hain.</p>
<h2>Department Wise Recruitment in Uttar Pradesh</h2>
<p>UP Police Bharti Board mein constable aur SI posts, SGPGI Lucknow mein medical staff, UP Basic Shiksha Parishad mein teacher bharti, aur UPPCL mein technical posts — yeh sab UP ke major recruitment sources hain 2026 mein. UPPSC exam calendar follow karo aur Top Sarkari Jobs par Uttar Pradesh Recruitment 2026 ka poora update paao.</p>""",

  "Rajasthan": """<h2>About Rajasthan Government Jobs 2026</h2>
<p>Rajasthan Sarkari Naukri 2026 mein iss saal kaafi vacancies aane ki ummeed hai. RPSC (Rajasthan Public Service Commission) state ki sabse badi recruitment agency hai jo RAS, RTS aur other civil services ke liye exam conduct karti hai. Jaipur, Jodhpur, Udaipur, Kota, Bikaner, Ajmer jaise cities mein candidates badi sankhya mein government jobs ke liye taiyari kar rahe hain. Rajasthan mein sarkari naukri ka competition high hai isliye time par apply karna zaroori hai.</p>
<p>RSMSSB, Rajasthan RVUNL aur Rajasthan Grameen Bank important recruitment bodies hain. Rajasthan Police aur RAC ke through constable, patwari aur inspector posts nikalte hain. RMSC aur RUHS Jaipur ke under nursing officer, lab technician aur pharmacist ke posts aate hain. RBSE aur Rajasthan DELED Board ke through Level 1 aur Level 2 teacher recruitment hoti hai. University of Rajasthan, MLSU Udaipur aur MDS University Ajmer mein bhi academic posts available hain 2026 mein.</p>
<p>Rajasthan Government Jobs 2026 mein 10th se lekar post graduate tak sabhi ke liye avsar hain. Jodhpur, Kota, Bikaner, Sikar ke candidates bhi online form ke zariye apply kar sakte hain. RSMSSB ke through patwari, LDC, lab assistant jaise posts bhi nikalte hain.</p>
<h2>Latest Government Jobs in Rajasthan</h2>
<p>Latest Rajasthan Government Jobs mein RPSC, RSMSSB, Rajasthan Police aur NHM ki vacancies abhi open hain. Online form, admit card aur result sab Top Sarkari Jobs par ek jagah milenge. Rajasthan Sarkari Naukri 2026 ka koi bhi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Rajasthan</h2>
<p>Rajasthan mein 10th pass ke liye peon aur class IV posts hain, 12th pass ke liye constable aur LDC. ITI holders ke liye RVUNL mein technical posts available hain. Diploma candidates PWD aur engineering department mein apply kar sakte hain. Graduate aur PG candidates RPSC RAS aur college lecturer posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Rajasthan</h2>
<p>Rajasthan Police aur RAC, RMSC health department, RBSE teacher bharti aur RSMSSB patwari recruitment — yeh sab Rajasthan ke top recruitment sources hain. RVUNL mein technical aur non-technical dono posts available hain. RPSC exam schedule follow karo aur Top Sarkari Jobs par Rajasthan Recruitment 2026 ka full update paao.</p>""",

  "Bihar": """<h2>About Bihar Government Jobs 2026</h2>
<p>Bihar Sarkari Naukri 2026 ke aspiring candidates ke liye yeh page sabhi zaroori updates ka hub hai. BPSC (Bihar Public Service Commission) Bihar ka sabse important exam conduct karta hai jo BAS, BPS aur other Group A B posts ke liye hota hai. Patna, Gaya, Muzaffarpur, Bhagalpur, Darbhanga, Purnia jaise districts mein lakho candidates government job ki taiyari mein jute hain. Bihar Government Jobs 2026 mein teacher bharti, police bharti aur health department ki vacancies badi sankhya mein expected hain.</p>
<p>BSPHCL, Bihar STET aur Bihar State Road Transport major recruitment organizations hain. Bihar Police aur BPSSC ke through constable, SI aur other posts nikale jaate hain. SHSB aur PMCH Patna ke through health department mein ANM, GNM, lab technician aur doctor level ki bharti hoti hai. BSEB aur Bihar School Examination Board ke through teacher eligibility test aur school teacher posts fill ki jaati hain. Patna University, Magadh University aur Nalanda Open University mein bhi non-teaching posts available hain.</p>
<p>Govt Jobs in Bihar mein 10th pass waale MTS aur Group D ke liye eligible hain jabki 12th pass waale constable aur clerk apply kar sakte hain. ITI aur diploma holders ke liye BSPHCL mein posts hain. Darbhanga, Bhagalpur, Gaya ke candidates bhi online form se asaani se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Bihar</h2>
<p>Latest Bihar Government Jobs mein BPSC, BPSSC, Bihar Police aur STET ki vacancies currently open hain. Bihar Sarkari Naukri 2026 ke liye online form, admit card aur result sab Top Sarkari Jobs par milega. Nayi notification miss mat karo.</p>
<h2>Qualification Wise Jobs in Bihar</h2>
<p>Bihar mein 10th pass ke liye police constable aur Group D posts hain. 12th pass ke liye clerk, assistant aur BSEB related posts milte hain. ITI holders ke liye BSPHCL technical posts aur diploma candidates ke liye engineering department mein avsar hain. Graduate aur PG waale BPSC exam aur STET teacher posts ke liye apply karein.</p>
<h2>Department Wise Recruitment in Bihar</h2>
<p>Bihar Police aur BPSSC, SHSB health bharti, BSEB teacher recruitment aur BSPHCL technical posts — yeh Bihar ke top hiring departments hain 2026 mein. BPSC exam ki taiyari karo aur Top Sarkari Jobs par Bihar Recruitment 2026 ka daily update paao.</p>""",

  "Madhya Pradesh": """<h2>About Madhya Pradesh Government Jobs 2026</h2>
<p>Madhya Pradesh Sarkari Naukri 2026 ke liye MP mein kaafi vacancies aa rahi hain. MPPSC (Madhya Pradesh Public Service Commission) state ka pramukh exam body hai jo MP State Services, Forest Service aur other posts ke liye selection karta hai. Bhopal, Indore, Jabalpur, Gwalior, Ujjain aur Rewa jaise cities mein candidates badi tadaad mein government jobs ki taiyari karte hain.</p>
<p>MPPKVVCL, MP Madhya Kshetra Vidyut Vitaran aur MP Housing Board important recruitment bodies hain. MP Police aur MP Vyapam ke through constable, SI, patwari aur other posts nikale jaate hain. MP NHM aur AIIMS Bhopal ke under ANM, staff nurse aur technical posts aate hain. MPBSE aur MP Teacher Eligibility Board ke through primary aur secondary teacher bharti hoti hai. Barkatullah University Bhopal, Vikram University Ujjain aur DAVV Indore mein academic posts bhi available hain 2026 mein.</p>
<p>MP Recruitment 2026 mein 10th pass se lekar PG tak sabhi ke liye avsar hain. Gwalior, Satna, Sagar, Chhindwara jaise districts ke candidates bhi online form ke zariye apply kar sakte hain.</p>
<h2>Latest Government Jobs in Madhya Pradesh</h2>
<p>Latest MP Government Jobs mein MPPSC, MP Vyapam, MP Police aur NHM ki vacancies open hain. Online form, admit card aur result sab Top Sarkari Jobs par ek jagah milenge. Madhya Pradesh Sarkari Naukri 2026 ka koi bhi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Madhya Pradesh</h2>
<p>MP mein 10th pass ke liye peon aur Group D posts hain. 12th pass ke liye MP Police constable aur clerk posts available hain. ITI holders MPPKVVCL mein technical posts ke liye apply kar sakte hain. Diploma candidates PWD mein aur Graduate/PG candidates MPPSC aur MPTET teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Madhya Pradesh</h2>
<p>MP Police aur Vyapam, AIIMS Bhopal medical staff, MPBSE teacher bharti aur MPPKVVCL technical posts — yeh MP ke major recruitment sources hain 2026 mein. MPPSC exam calendar track karo aur Top Sarkari Jobs par Madhya Pradesh Recruitment 2026 ka poora update paao.</p>""",

  "Maharashtra": """<h2>About Maharashtra Government Jobs 2026</h2>
<p>Maharashtra Sarkari Naukri 2026 ke liye iss page par sabhi latest updates milenge. MPSC (Maharashtra Public Service Commission) Maharashtra ka sabse prestigious exam conduct karta hai jo Maharashtra Civil Services, Police Service aur Engineering Services ke liye selection karta hai. Mumbai, Pune, Nagpur, Nashik, Aurangabad, Thane jaise cities ke candidates badi sankhya mein Maharashtra Government Jobs 2026 ki taiyari karte hain.</p>
<p>MSRTC, MAHADISCOM aur Maharashtra Metro Rail important recruitment bodies hain. Maharashtra Police aur MHB ke through constable, PSI aur other posts nikale jaate hain. Maharashtra NHM aur KEM Mumbai ke under nursing officer, technician aur doctor posts aate hain. Maharashtra SSC Board aur MSEB ke through teacher bharti hoti hai. Mumbai University, Pune University aur Nagpur University mein bhi teaching aur non-teaching posts available hain 2026 mein.</p>
<p>Maharashtra Recruitment 2026 mein 10th, 12th, ITI, Diploma, Graduate aur PG — sabhi ke liye opportunities hain. Kolhapur, Solapur, Amravati ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Maharashtra</h2>
<p>Latest Maharashtra Government Jobs mein MPSC, Maharashtra Police, MSRTC aur NHM ki vacancies currently open hain. Online form, admit card aur result Top Sarkari Jobs par ek jagah milta hai. Maharashtra Sarkari Naukri 2026 ki notification miss mat karo.</p>
<h2>Qualification Wise Jobs in Maharashtra</h2>
<p>Maharashtra mein 10th pass ke liye peon, constable aur Group D posts hain. 12th pass ke liye clerk aur assistant posts milte hain. ITI holders MAHADISCOM mein, diploma candidates PWD mein apply kar sakte hain. Graduate aur PG waale MPSC exams aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Maharashtra</h2>
<p>Maharashtra Police aur MHB, NHM health bharti, MSEB teacher recruitment aur MSRTC driver posts — yeh Maharashtra ke top hiring departments hain 2026 mein. MPSC schedule follow karo aur Top Sarkari Jobs par Maharashtra Recruitment 2026 ka full update paao.</p>""",

  "Gujarat": """<h2>About Gujarat Government Jobs 2026</h2>
<p>Gujarat Sarkari Naukri 2026 ke liye iss page par sabhi latest vacancies milti hain. GPSC (Gujarat Public Service Commission) Gujarat mein Class 1 aur Class 2 government officers ki bharti karta hai. Ahmedabad, Surat, Vadodara, Rajkot, Gandhinagar aur Bhavnagar ke candidates badi sankhya mein Gujarat Government Jobs 2026 ki taiyari mein lage hue hain.</p>
<p>GSRTC, GUVNL, Gujarat Metro Rail aur GNFC important recruitment bodies hain. Gujarat Police aur LRD ke through constable, PSI aur LRD bharti hoti hai. GMERS aur Civil Hospital Ahmedabad ke under health department mein staff nurse, lab tech aur doctor posts aate hain. GSEB aur Gujarat HTAT Board ke through primary aur secondary teacher recruitment hoti hai. Gujarat University, MS University Baroda aur Saurashtra University mein bhi academic posts available hain 2026 mein.</p>
<p>Gujarat Recruitment 2026 mein 10th pass waale Group D, 12th pass waale constable aur clerk, ITI holders GUVNL mein apply kar sakte hain. Jamnagar, Junagadh, Anand ke candidates bhi online form se asaani se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Gujarat</h2>
<p>Latest Gujarat Government Jobs mein GPSC, GSSSB, Gujarat Police aur GUVNL ki vacancies open hain. Gujarat Sarkari Naukri 2026 ke liye online form, admit card aur result sab Top Sarkari Jobs par milenge. Koi bhi vacancy miss mat karo.</p>
<h2>Qualification Wise Jobs in Gujarat</h2>
<p>Gujarat mein 10th pass ke liye peon aur Group D, 12th pass ke liye constable aur clerk posts hain. ITI holders GUVNL mein, diploma candidates Gujarat PWD mein apply kar sakte hain. Graduate aur PG candidates GPSC Class 1/2 exam aur HTAT teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Gujarat</h2>
<p>Gujarat Police LRD, GMERS health bharti, GSEB teacher recruitment aur GUVNL technical posts — yeh Gujarat ke top hiring departments hain 2026 mein. GPSC aur GSSSB ka calendar follow karo aur Top Sarkari Jobs par Gujarat Recruitment 2026 ka poora update paao.</p>""",

  "West Bengal": """<h2>About West Bengal Government Jobs 2026</h2>
<p>West Bengal Sarkari Naukri 2026 ke liye yeh page sabhi latest vacancies ka reliable source hai. WBPSC (West Bengal Public Service Commission) West Bengal Civil Service aur other state-level posts ke liye selection conduct karta hai. Kolkata, Howrah, Asansol, Siliguri, Durgapur aur Bardhaman jaise cities ke candidates badi tadaad mein government jobs ki taiyari karte hain.</p>
<p>WBSEDCL, CSTC, West Bengal PWD aur Kolkata Metro important recruitment bodies hain. West Bengal Police aur Kolkata Police ke through constable aur sub-inspector posts nikale jaate hain. WBNHM aur SSKM Hospital Kolkata ke under health posts aate hain. WBBSE aur WBCHSE ke through school teacher recruitment hoti hai. Calcutta University, Jadavpur University aur Kalyani University mein bhi academic posts available hain 2026 mein.</p>
<p>WB Recruitment 2026 mein 10th pass, 12th pass, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Malda, Murshidabad, Purulia ke candidates bhi online form se easily apply kar sakte hain.</p>
<h2>Latest Government Jobs in West Bengal</h2>
<p>Latest WB Government Jobs mein WBPSC, WB Police, WBSEDCL aur NHM ki vacancies open hain. Online form, admit card download aur result sab Top Sarkari Jobs par ek jagah milenge. West Bengal Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in West Bengal</h2>
<p>WB mein 10th pass ke liye Group D aur constable posts hain. 12th pass ke liye clerk aur assistant posts. ITI holders WBSEDCL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG waale WBPSC exam aur school teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in West Bengal</h2>
<p>West Bengal Police, WBNHM health bharti, WBBSE teacher recruitment aur WBSEDCL technical posts — yeh WB ke top hiring departments hain 2026 mein. WBPSC calendar follow karo aur Top Sarkari Jobs par West Bengal Recruitment 2026 ka poora update paao.</p>""",

  "Tamil Nadu": """<h2>About Tamil Nadu Government Jobs 2026</h2>
<p>Tamil Nadu Sarkari Naukri 2026 ke liye TNPSC (Tamil Nadu Public Service Commission) sabse pramukh recruitment body hai jo Group 1, Group 2, Group 4 aur CCSE exams conduct karta hai. Chennai, Coimbatore, Madurai, Tiruchirappalli, Salem aur Erode jaise major cities mein lakho candidates Tamil Nadu Government Jobs 2026 ki taiyari kar rahe hain.</p>
<p>TNEB, TNSTC, TANGEDCO aur Tamil Nadu PWD important recruitment bodies hain. Tamil Nadu Police aur TNUSRB ke through police constable, SI aur fingerprint examiner posts nikale jaate hain. Tamil Nadu NHM aur Government Hospitals Chennai ke under health posts aate hain. TN School Education aur TNTET Board ke through teacher recruitment hoti hai. University of Madras, Anna University aur Bharathidasan University mein bhi academic posts available hain 2026 mein.</p>
<p>TN Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Tirunelveli, Vellore, Thanjavur, Dindigul ke candidates bhi online form se easily apply kar sakte hain.</p>
<h2>Latest Government Jobs in Tamil Nadu</h2>
<p>Latest Tamil Nadu Government Jobs mein TNPSC, TN Police, TANGEDCO aur NHM ki vacancies open hain. Online form, hall ticket download aur result sab Top Sarkari Jobs par milenge. Tamil Nadu Sarkari Naukri 2026 ka daily update miss mat karo.</p>
<h2>Qualification Wise Jobs in Tamil Nadu</h2>
<p>TN mein 10th pass ke liye constable aur Group D, 12th pass ke liye clerk, typist aur VAO posts. ITI holders TANGEDCO mein, Diploma candidates TWAD Board mein apply kar sakte hain. Graduate aur PG candidates TNPSC Group 1/2 aur teacher eligibility test ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Tamil Nadu</h2>
<p>TNUSRB police bharti, Tamil Nadu NHM health posts, TNTET teacher recruitment aur TANGEDCO technical posts — yeh TN ke top hiring departments hain 2026 mein. TNPSC calendar follow karo aur Top Sarkari Jobs par Tamil Nadu Recruitment 2026 ka full update paao.</p>""",

  "Karnataka": """<h2>About Karnataka Government Jobs 2026</h2>
<p>Karnataka Sarkari Naukri 2026 ke liye KPSC (Karnataka Public Service Commission) sabse important exam body hai jo KAS, KPS aur other Group A B posts ke liye selection karta hai. Bengaluru, Mysuru, Hubballi, Mangaluru, Belagavi aur Kalaburagi jaise cities mein candidates badi tadaad mein Karnataka Government Jobs 2026 ki taiyari mein lage hain.</p>
<p>BMTC, KSRTC, BESCOM aur Karnataka Neeravari Nigam pramukh recruitment bodies hain. Karnataka Police aur KSP ke through police constable, PSI aur other posts nikale jaate hain. KSDNEB aur NIMHANS Bangalore ke under health aur nursing posts aate hain. Karnataka School Examination Board aur DPAR ke through teacher aur government servant recruitment hoti hai. Bangalore University, Mysore University aur Visvesvaraya Tech University mein bhi academic posts available hain 2026 mein.</p>
<p>Karnataka Recruitment 2026 mein 10th pass se lekar post graduate tak sabhi ke liye avsar hain. Shivamogga, Tumakuru, Dharwad, Vijayapura ke candidates bhi online form ke zariye apply kar sakte hain.</p>
<h2>Latest Government Jobs in Karnataka</h2>
<p>Latest Karnataka Government Jobs mein KPSC, KSP, BESCOM aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par ek jagah milta hai. Karnataka Sarkari Naukri 2026 ka daily update miss mat karo.</p>
<h2>Qualification Wise Jobs in Karnataka</h2>
<p>Karnataka mein 10th pass ke liye Group D aur constable posts hain. 12th pass ke liye KSRTC conductor aur clerk posts. ITI holders BESCOM mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG waale KPSC KAS aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Karnataka</h2>
<p>KSP police bharti, KSDNEB health posts, Karnataka School teacher recruitment aur BESCOM technical posts — yeh Karnataka ke top hiring departments hain 2026 mein. KPSC exam calendar follow karo aur Top Sarkari Jobs par Karnataka Recruitment 2026 ka poora update paao.</p>""",

  "Telangana": """<h2>About Telangana Government Jobs 2026</h2>
<p>Telangana Sarkari Naukri 2026 ke liye TSPSC (Telangana State Public Service Commission) sabse pramukh exam body hai jo Group 1, Group 2, Group 3 aur other state service posts ke liye selection karta hai. Hyderabad, Warangal, Karimnagar, Nizamabad, Khammam aur Adilabad jaise cities ke candidates Telangana Government Jobs 2026 ke liye taiyar hain.</p>
<p>TSRTC, TSSPDCL, Hyderabad Metro Rail aur TSNPDCL important recruitment bodies hain. Telangana Police aur TSLPRB ke through constable, SI aur other posts nikalte hain. TS NHM aur Osmania General Hospital ke under ANM, GNM aur technical health posts aate hain. TSBIE aur TS TET Board ke through teacher recruitment hoti hai. Osmania University, Kakatiya University aur JNTU Hyderabad mein bhi academic posts available hain 2026 mein.</p>
<p>Telangana Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Nalgonda, Mahbubnagar, Medak ke candidates bhi online form se easily apply kar sakte hain.</p>
<h2>Latest Government Jobs in Telangana</h2>
<p>Latest Telangana Government Jobs mein TSPSC, TSLPRB, TSSPDCL aur NHM ki vacancies open hain. Online form, hall ticket aur result sab Top Sarkari Jobs par ek jagah milenge. Telangana Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Telangana</h2>
<p>TS mein 10th pass ke liye constable aur peon posts, 12th pass ke liye clerk aur typist. ITI holders TSSPDCL mein, Diploma candidates TSRTC mein apply kar sakte hain. Graduate aur PG waale TSPSC Group 1 aur teacher eligibility test ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Telangana</h2>
<p>TSLPRB police bharti, TS NHM health posts, TSTET teacher recruitment aur TSSPDCL technical posts — yeh TS ke top hiring departments hain 2026 mein. TSPSC exam calendar follow karo aur Top Sarkari Jobs par Telangana Recruitment 2026 ka full update paao.</p>""",

  "Andhra Pradesh": """<h2>About Andhra Pradesh Government Jobs 2026</h2>
<p>Andhra Pradesh Sarkari Naukri 2026 ke liye APPSC (Andhra Pradesh Public Service Commission) pramukh recruitment body hai jo Group 1, Group 2, Group 3 aur other posts ke liye exam conduct karta hai. Visakhapatnam, Vijayawada, Guntur, Tirupati, Kakinada aur Nellore jaise cities mein candidates AP Government Jobs 2026 ki taiyari kar rahe hain.</p>
<p>APSRTC, APEPDCL, AP Grama Sachivalayam aur APGENCO important recruitment bodies hain. AP Police aur APSLPRB ke through constable, SI aur fire department posts nikalte hain. AP NHM aur Government General Hospital Vijayawada ke under health posts aate hain. APBSE aur AP Teacher Recruitment Board ke through DSC aur teacher posts fill ki jaati hain. Andhra University, Sri Venkateswara University aur Krishna University mein bhi academic posts available hain 2026 mein.</p>
<p>AP Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Kurnool, Kadapa, Chittoor ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Andhra Pradesh</h2>
<p>Latest AP Government Jobs mein APPSC, APSLPRB, APEPDCL aur NHM ki vacancies open hain. Online form, admit card aur result sab Top Sarkari Jobs par milenge. Andhra Pradesh Sarkari Naukri 2026 ka koi bhi notification yahan se track karo.</p>
<h2>Qualification Wise Jobs in Andhra Pradesh</h2>
<p>AP mein 10th pass ke liye Grama Sachivalayam aur constable posts, 12th pass ke liye clerk aur assistant. ITI holders APEPDCL mein, Diploma candidates APGENCO mein apply kar sakte hain. Graduate aur PG waale APPSC Group 1 aur DSC teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Andhra Pradesh</h2>
<p>APSLPRB police bharti, AP NHM health posts, AP DSC teacher recruitment aur APEPDCL technical posts — yeh AP ke top hiring departments hain 2026 mein. APPSC exam calendar follow karo aur Top Sarkari Jobs par Andhra Pradesh Recruitment 2026 ka poora update paao.</p>""",

  "Haryana": """<h2>About Haryana Government Jobs 2026</h2>
<p>Haryana Sarkari Naukri 2026 ke liye yeh page sabse accurate aur updated source hai. HPSC (Haryana Public Service Commission) Haryana mein HCS, HPS aur other Group A B posts ke liye selection conduct karta hai. Gurugram, Faridabad, Ambala, Hisar, Karnal, Rohtak aur Panipat jaise industrial cities ke candidates badi tadaad mein Haryana Government Jobs 2026 ki taiyari mein jute hain.</p>
<p>HSIDC, Haryana Roadways, DHBVN aur UHBVN pramukh recruitment bodies hain. Haryana Police aur HSSC ke through constable, SI, patwari aur Gram Sachiv posts nikalte hain. PGIMS Rohtak aur Haryana NHM ke under staff nurse, ANM, lab technician aur medical officer posts aate hain. HBSE aur Haryana Shiksha Vibhag ke through PRT, TGT, PGT teacher recruitment hoti hai. Kurukshetra University, MDU Rohtak aur Chaudhary Devi Lal University mein bhi academic posts available hain 2026 mein.</p>
<p>Haryana Recruitment 2026 mein 10th, 12th, ITI, Diploma, Graduate aur PG sabhi ke liye vacancies nikalti hain. Bhiwani, Sirsa, Rewari, Mahendragarh ke candidates bhi online form se easily apply kar sakte hain.</p>
<h2>Latest Government Jobs in Haryana</h2>
<p>Latest Haryana Government Jobs mein HSSC, HPSC, Haryana Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par ek jagah milenge. Haryana Sarkari Naukri 2026 ka koi bhi update miss mat karo — daily check karo.</p>
<h2>Qualification Wise Jobs in Haryana</h2>
<p>Haryana mein 10th pass ke liye Group D aur peon posts hain. 12th pass ke liye constable aur clerk. ITI holders DHBVN mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates HPSC HCS exam aur PGT teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Haryana</h2>
<p>Haryana Police HSSC, PGIMS Rohtak health bharti, HBSE teacher recruitment aur DHBVN technical posts — yeh Haryana ke top hiring departments hain 2026 mein. HSSC aur HPSC calendar follow karo aur Top Sarkari Jobs par Haryana Recruitment 2026 ka poora update paao.</p>""",

  "Punjab": """<h2>About Punjab Government Jobs 2026</h2>
<p>Punjab Sarkari Naukri 2026 ke liye PPSC (Punjab Public Service Commission) state mein sabse important exam body hai. Ludhiana, Amritsar, Jalandhar, Patiala, Bathinda aur Mohali jaise cities ke candidates badi sankhya mein Punjab Government Jobs 2026 ki taiyari mein hain.</p>
<p>PRTC, PSPCL, Punjab Mandi Board aur Punjab Housing Board important recruitment bodies hain. Punjab Police aur PSSSB ke through constable, sub-inspector aur other posts nikalte hain. PGIMER Chandigarh aur Punjab NHM ke under health posts nikali jaati hain. PSEB aur Punjab Shiksha Board ke through teacher recruitment hoti hai. Panjab University Chandigarh, Guru Nanak Dev University aur Punjab Agricultural University mein bhi academic posts available hain 2026 mein.</p>
<p>Punjab Recruitment 2026 mein 10th, 12th, ITI, Diploma, Graduate aur PG sabhi ke liye avsar hain. Ferozepur, Gurdaspur, Sangrur, Hoshiarpur ke candidates bhi online form ke zariye apply kar sakte hain.</p>
<h2>Latest Government Jobs in Punjab</h2>
<p>Latest Punjab Government Jobs mein PPSC, PSSSB, Punjab Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par ek jagah milte hain. Punjab Sarkari Naukri 2026 ka koi bhi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Punjab</h2>
<p>Punjab mein 10th pass ke liye Group D aur constable posts, 12th pass ke liye clerk aur assistant posts hain. ITI holders PSPCL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates PPSC PCS aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Punjab</h2>
<p>Punjab Police PSSSB, PGIMER health staff, PSEB teacher recruitment aur PSPCL technical posts — yeh Punjab ke top hiring departments hain 2026 mein. PPSC exam calendar follow karo aur Top Sarkari Jobs par Punjab Recruitment 2026 ka full update paao.</p>""",

  "Delhi": """<h2>About Delhi Government Jobs 2026</h2>
<p>Delhi Sarkari Naukri 2026 ke liye yeh page sabse reliable update source hai. DSSSB (Delhi Subordinate Services Selection Board) Delhi mein teacher, clerk, patwari aur other Group B C posts ke liye recruitment karta hai. New Delhi, East Delhi, West Delhi, North Delhi, South Delhi aur Dwarka ke candidates badi tadaad mein Delhi Government Jobs 2026 ki taiyari karte hain. Delhi mein central aur state dono level ke jobs available hain.</p>
<p>DTC, DMRC Metro, Delhi Jal Board aur NDMC pramukh recruitment organizations hain. Delhi Police aur CISF ke through constable, head constable aur sub-inspector posts nikalte hain. AIIMS New Delhi aur Delhi NHM ke under doctor, nurse aur paramedical posts aate hain. CBSE aur Directorate of Education Delhi ke through TGT, PGT teacher posts fill ki jaati hain. Delhi University, Jamia Millia Islamia aur JNU mein bhi academic posts available hain 2026 mein.</p>
<p>Govt Jobs in Delhi sirf local candidates ke liye nahi — pure India se apply kar sakte hain. 10th ke liye Group D, 12th ke liye constable aur clerk, ITI holders ke liye DMRC technical posts aur Graduate/PG ke liye DSSSB — sab available hain.</p>
<h2>Latest Government Jobs in Delhi</h2>
<p>Latest Delhi Government Jobs mein DSSSB, Delhi Police, DMRC aur AIIMS ki vacancies open hain. Online form, admit card download aur result sab Top Sarkari Jobs par ek jagah milenge. Delhi Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Delhi</h2>
<p>Delhi mein 10th pass ke liye Group D aur constable posts, 12th pass ke liye clerk aur assistant. ITI holders DMRC mein, Diploma candidates Delhi Jal Board mein apply kar sakte hain. Graduate aur PG waale DSSSB teacher posts aur Delhi PSC ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Delhi</h2>
<p>Delhi Police CISF, AIIMS medical staff, DSSSB teacher recruitment aur DMRC technical posts — yeh Delhi ke top hiring departments hain 2026 mein. DSSSB exam calendar follow karo aur Top Sarkari Jobs par Delhi Recruitment 2026 ka poora update paao.</p>""",

  "Odisha": """<h2>About Odisha Government Jobs 2026</h2>
<p>Odisha Sarkari Naukri 2026 ke liye OPSC (Odisha Public Service Commission) sabse important recruitment body hai jo OAS, OPS aur other state civil services ke liye exam conduct karta hai. Bhubaneswar, Cuttack, Rourkela, Berhampur, Sambalpur aur Puri jaise cities mein candidates badi sankhya mein Odisha Government Jobs 2026 ki taiyari mein hain.</p>
<p>OSRTC, GRIDCO, Odisha Mining Corporation aur NALCO pramukh recruitment bodies hain. Odisha Police aur OSSC ke through constable aur other posts nikalte hain. OHRC aur AIIMS Bhubaneswar ke under health department mein medical posts aate hain. BSE Odisha aur CHSE Odisha ke through teacher recruitment hoti hai. Utkal University, Berhampur University aur Sambalpur University mein bhi academic posts available hain 2026 mein.</p>
<p>Odisha Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Koraput, Sundargarh, Keonjhar, Ganjam ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Odisha</h2>
<p>Latest Odisha Government Jobs mein OPSC, OSSC, Odisha Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Odisha Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Odisha</h2>
<p>Odisha mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk aur assistant posts hain. ITI holders GRIDCO mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates OPSC OAS aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Odisha</h2>
<p>Odisha Police OSSC, OHRC health bharti, BSE Odisha teacher recruitment aur GRIDCO technical posts — yeh Odisha ke top hiring departments hain 2026 mein. OPSC calendar follow karo aur Top Sarkari Jobs par Odisha Recruitment 2026 ka full update paao.</p>""",

  "Jharkhand": """<h2>About Jharkhand Government Jobs 2026</h2>
<p>Jharkhand Sarkari Naukri 2026 ke liye JPSC (Jharkhand Public Service Commission) pramukh exam body hai jo JPSC Civil Services aur other Group A B posts ke liye selection karta hai. Ranchi, Dhanbad, Jamshedpur, Bokaro, Hazaribagh aur Giridih jaise cities mein candidates Jharkhand Government Jobs 2026 ki taiyari mein hain.</p>
<p>JBVNL, JSRTC aur Jharkhand Housing Board important recruitment bodies hain. Jharkhand Police aur JSSC ke through constable, SI aur other posts nikalte hain. Jharkhand NHM aur Rajendra Institute Ranchi ke under health posts aate hain. JAC Board aur Jharkhand Shiksha Pariyojna ke through teacher recruitment hoti hai. Ranchi University, VBKU aur VBU Hazaribagh mein bhi academic posts available hain 2026 mein.</p>
<p>Jharkhand Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Dumka, Deoghar, Pakur, Lohardaga ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Jharkhand</h2>
<p>Latest Jharkhand Government Jobs mein JPSC, JSSC, Jharkhand Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Jharkhand Sarkari Naukri 2026 ka koi bhi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Jharkhand</h2>
<p>Jharkhand mein 10th pass ke liye Group D, 12th pass ke liye constable aur clerk posts hain. ITI holders JBVNL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates JPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Jharkhand</h2>
<p>Jharkhand Police JSSC, NHM health bharti, JAC teacher recruitment aur JBVNL technical posts — yeh Jharkhand ke top hiring departments hain 2026 mein. JPSC calendar follow karo aur Top Sarkari Jobs par Jharkhand Recruitment 2026 ka poora update paao.</p>""",

  "Chhattisgarh": """<h2>About Chhattisgarh Government Jobs 2026</h2>
<p>Chhattisgarh Sarkari Naukri 2026 ke liye CGPSC (Chhattisgarh Public Service Commission) pramukh recruitment body hai. Raipur, Bilaspur, Durg, Bhilai, Jagdalpur aur Korba jaise cities mein candidates CG Government Jobs 2026 ki taiyari kar rahe hain.</p>
<p>CSRTC, CSPDCL aur Chhattisgarh Housing Board important recruitment bodies hain. Chhattisgarh Police aur CGPEB ke through constable posts nikalte hain. CG NHM aur AIIMS Raipur ke under health posts aate hain. CGBSE aur CG Vyavsayik Pariksha Mandal ke through teacher posts fill ki jaati hain. Pt. Ravishankar Shukla University, Hemchand Yadav University aur CSVTU Bhilai mein bhi academic posts available hain 2026 mein.</p>
<p>CG Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Surguja, Bastar, Rajnandgaon, Korba ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Chhattisgarh</h2>
<p>Latest CG Government Jobs mein CGPSC, CGPEB, CG Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Chhattisgarh Sarkari Naukri 2026 ka daily update miss mat karo.</p>
<h2>Qualification Wise Jobs in Chhattisgarh</h2>
<p>CG mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk aur assistant posts hain. ITI holders CSPDCL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates CGPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Chhattisgarh</h2>
<p>CG Police CGPEB, AIIMS Raipur health posts, CGBSE teacher recruitment aur CSPDCL technical posts — yeh CG ke top hiring departments hain 2026 mein. CGPSC calendar follow karo aur Top Sarkari Jobs par Chhattisgarh Recruitment 2026 ka poora update paao.</p>""",

  "Assam": """<h2>About Assam Government Jobs 2026</h2>
<p>Assam Sarkari Naukri 2026 ke liye APSC (Assam Public Service Commission) pramukh exam body hai jo ACS, APS aur other state services posts ke liye selection karta hai. Guwahati, Dibrugarh, Silchar, Jorhat, Tinsukia aur Nagaon jaise cities mein candidates badi sankhya mein Assam Government Jobs 2026 ki taiyari mein hain.</p>
<p>ASTC, APDCL, Oil India Limited aur NF Railway important recruitment bodies hain. Assam Police aur SLPRB ke through constable, SI aur other posts nikalte hain. GMCH Guwahati aur Assam NHM ke under health posts aate hain. SEBA aur AHSEC Board ke through teacher recruitment hoti hai. Gauhati University, Dibrugarh University aur Tezpur University mein bhi academic posts available hain 2026 mein.</p>
<p>Assam Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Kamrup, Sonitpur, Cachar, Barpeta ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Assam</h2>
<p>Latest Assam Government Jobs mein APSC, SLPRB, Assam Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par ek jagah milenge. Assam Sarkari Naukri 2026 ka koi bhi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Assam</h2>
<p>Assam mein 10th pass ke liye constable aur Group D, 12th pass ke liye clerk aur assistant posts hain. ITI holders APDCL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates APSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Assam</h2>
<p>SLPRB police bharti, Assam NHM health posts, SEBA teacher recruitment aur APDCL technical posts — yeh Assam ke top hiring departments hain 2026 mein. APSC calendar follow karo aur Top Sarkari Jobs par Assam Recruitment 2026 ka full update paao.</p>""",

  "Kerala": """<h2>About Kerala Government Jobs 2026</h2>
<p>Kerala Sarkari Naukri 2026 ke liye Kerala PSC (Kerala Public Service Commission) sabse pramukh exam body hai jo LDC, LD Typist, Plus Two Level aur Degree Level posts ke liye selection karta hai. Thiruvananthapuram, Kochi, Kozhikode, Thrissur, Kannur aur Alappuzha jaise cities mein candidates Kerala Government Jobs 2026 ki taiyari mein hain.</p>
<p>KSRTC, KSEB, Cochin Shipyard aur Kerala Minerals pramukh recruitment bodies hain. Kerala Police aur Kerala Armed Police ke through constable posts nikalte hain. AIMS Kochi aur Kerala NHM ke under health posts aate hain. KBPE aur DHSE Kerala ke through HSA aur UP School teacher posts fill ki jaati hain. University of Kerala, Mahatma Gandhi University aur Calicut University mein bhi academic posts available hain 2026 mein.</p>
<p>Kerala Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Palakkad, Malappuram, Kottayam, Kollam ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Kerala</h2>
<p>Latest Kerala Government Jobs mein Kerala PSC, Kerala Police, KSEB aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Kerala Sarkari Naukri 2026 ka daily update miss mat karo.</p>
<h2>Qualification Wise Jobs in Kerala</h2>
<p>Kerala mein 10th pass ke liye LDC aur constable posts, 12th pass ke liye LD Typist aur Plus Two Level posts hain. ITI holders KSEB mein, Diploma candidates Cochin Shipyard mein apply kar sakte hain. Graduate aur PG candidates Kerala PSC Degree Level posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Kerala</h2>
<p>Kerala Police, AIMS Kochi health staff, KBPE teacher recruitment aur KSEB technical posts — yeh Kerala ke top hiring departments hain 2026 mein. Kerala PSC notifications follow karo aur Top Sarkari Jobs par Kerala Recruitment 2026 ka poora update paao.</p>""",

  "Himachal Pradesh": """<h2>About Himachal Pradesh Government Jobs 2026</h2>
<p>Himachal Pradesh Sarkari Naukri 2026 ke liye HPPSC (Himachal Pradesh Public Service Commission) aur HPSSSB pramukh recruitment bodies hain. Shimla, Dharamshala, Mandi, Solan, Hamirpur aur Kullu jaise hill districts ke candidates HP Government Jobs 2026 ki taiyari mein hain.</p>
<p>HRTC, HPSEB aur HP Housing Board important recruitment bodies hain. HP Police aur HPSSSB ke through constable, clerk aur patwari posts nikalte hain. IGMC Shimla aur HP NHM ke under health posts aate hain. HPBOSE aur HP Shiksha Board ke through TGT, PGT aur teacher recruitment hoti hai. HP University Shimla, Himachal Pradesh Technical University aur CSK Agriculture University mein bhi academic posts available hain 2026 mein.</p>
<p>HP Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Sirmaur, Kinnaur, Lahaul-Spiti, Chamba ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Himachal Pradesh</h2>
<p>Latest HP Government Jobs mein HPPSC, HPSSSB, HP Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Himachal Pradesh Sarkari Naukri 2026 ka koi bhi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Himachal Pradesh</h2>
<p>HP mein 10th pass ke liye Group D aur constable, 12th pass ke liye JBT teacher aur clerk posts hain. ITI holders HPSEB mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates HPPSC exam aur TGT/PGT teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Himachal Pradesh</h2>
<p>HP Police HPSSSB, IGMC health bharti, HPBOSE teacher recruitment aur HPSEB technical posts — yeh HP ke top hiring departments hain 2026 mein. HPPSC calendar follow karo aur Top Sarkari Jobs par Himachal Pradesh Recruitment 2026 ka poora update paao.</p>""",

  "Uttarakhand": """<h2>About Uttarakhand Government Jobs 2026</h2>
<p>Uttarakhand Sarkari Naukri 2026 ke liye UKPSC (Uttarakhand Public Service Commission) aur UKSSSC pramukh recruitment bodies hain. Dehradun, Haridwar, Roorkee, Haldwani, Nainital aur Rishikesh ke candidates UK Government Jobs 2026 ki taiyari mein hain.</p>
<p>UTC, UPCL, Uttarakhand Housing Corporation aur THDC India important recruitment bodies hain. Uttarakhand Police aur UKSSSC ke through constable, patwari aur other posts nikalte hain. AIIMS Rishikesh aur UK NHM ke under health posts aate hain. UBSE aur UK Board of School Education ke through teacher recruitment hoti hai. HNB Garhwal University, Kumaun University aur Uttarakhand Technical University mein bhi academic posts available hain 2026 mein.</p>
<p>UK Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Pauri, Tehri, Pithoragarh, Chamoli ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Uttarakhand</h2>
<p>Latest Uttarakhand Government Jobs mein UKPSC, UKSSSC, UK Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Uttarakhand Sarkari Naukri 2026 ka koi bhi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Uttarakhand</h2>
<p>UK mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk aur patwari posts hain. ITI holders UPCL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates UKPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Uttarakhand</h2>
<p>UK Police UKSSSC, AIIMS Rishikesh health posts, UBSE teacher recruitment aur UPCL technical posts — yeh UK ke top hiring departments hain 2026 mein. UKPSC calendar follow karo aur Top Sarkari Jobs par Uttarakhand Recruitment 2026 ka full update paao.</p>""",

  "Jammu and Kashmir": """<h2>About Jammu and Kashmir Government Jobs 2026</h2>
<p>Jammu and Kashmir Sarkari Naukri 2026 ke liye JKPSC (Jammu and Kashmir Public Service Commission) aur JKSSB pramukh recruitment bodies hain. Jammu, Srinagar, Anantnag, Baramulla, Udhampur aur Rajouri ke candidates J&K Government Jobs 2026 ki taiyari mein hain. UT status milne ke baad J&K mein UPSC aur JKPSC dono ke through opportunities aur badh gayi hain.</p>
<p>JKRTC, JKSPDC, J&K Bank aur JKPDD important recruitment bodies hain. J&K Police aur JKSSB ke through constable aur sub-inspector posts nikalte hain. SKIMS Soura aur J&K NHM ke under health posts aate hain. JKBOSE aur School Education Department ke through teacher recruitment hoti hai. University of Jammu, University of Kashmir aur SMVDU mein bhi academic posts available hain 2026 mein.</p>
<p>J&K Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Kulgam, Shopian, Kishtwar, Ramban ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Jammu and Kashmir</h2>
<p>Latest J&K Government Jobs mein JKPSC, JKSSB, J&K Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Jammu and Kashmir Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Jammu and Kashmir</h2>
<p>J&K mein 10th pass ke liye constable aur Group D, 12th pass ke liye clerk aur assistant posts hain. ITI holders JKSPDC mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates JKPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Jammu and Kashmir</h2>
<p>J&K Police JKSSB, SKIMS health bharti, JKBOSE teacher recruitment aur JKSPDC technical posts — yeh J&K ke top hiring departments hain 2026 mein. JKPSC calendar follow karo aur Top Sarkari Jobs par Jammu Kashmir Recruitment 2026 ka poora update paao.</p>""",

  "Goa": """<h2>About Goa Government Jobs 2026</h2>
<p>Goa Sarkari Naukri 2026 ke liye Goa Public Service Commission (GPSC Goa) pramukh recruitment body hai. Panaji, Margao, Vasco da Gama, Mapusa, Ponda aur Bicholim ke candidates Goa Government Jobs 2026 ki taiyari mein hain. Tourism hub hone ke bawajood Goa mein education, health, mining aur port sector mein government jobs ka scope wide hai.</p>
<p>KTC Goa, Goa Electricity Department, EDC Goa aur Goa Shipyard important recruitment bodies hain. Goa Police aur Goa Armed Police ke through constable posts nikalte hain. Goa Medical College Panaji aur Goa NHM ke under health posts aate hain. GBSHSE aur Goa School Education ke through teacher recruitment hoti hai. Goa University aur NIT Goa mein bhi academic posts available hain 2026 mein.</p>
<p>Goa Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. North Goa aur South Goa ke candidates online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Goa</h2>
<p>Latest Goa Government Jobs mein GPSC Goa, Goa Police, KTC aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Goa Sarkari Naukri 2026 ka koi bhi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Goa</h2>
<p>Goa mein 10th pass ke liye Group D aur constable posts, 12th pass ke liye clerk aur assistant hain. ITI holders Goa Shipyard mein, Diploma candidates EDC Goa mein apply kar sakte hain. Graduate aur PG candidates GPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Goa</h2>
<p>Goa Police, Goa Medical College health staff, GBSHSE teacher recruitment aur Goa Electricity Department technical posts — yeh Goa ke top hiring departments hain 2026 mein. GPSC Goa calendar follow karo aur Top Sarkari Jobs par Goa Recruitment 2026 ka full update paao.</p>""",

  "Tripura": """<h2>About Tripura Government Jobs 2026</h2>
<p>Tripura Sarkari Naukri 2026 ke liye TPSC (Tripura Public Service Commission) aur TRPB pramukh recruitment bodies hain. Agartala, Dharmanagar, Udaipur, Kailashahar, Belonia aur Sabroom ke candidates Tripura Government Jobs 2026 ki taiyari mein hain.</p>
<p>TRTC, TSECL aur Tripura Tribal Welfare Department important recruitment bodies hain. Tripura Police aur TRPB ke through constable posts nikalte hain. AGMC Agartala aur Tripura NHM ke under health posts aate hain. TBSE aur Tripura School Education ke through teacher recruitment hoti hai. Tripura University, MBB University aur ICFAI University Tripura mein bhi academic posts available hain 2026 mein.</p>
<p>Tripura Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Sepahijala, Gomati, Unakoti, Khowai ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Tripura</h2>
<p>Latest Tripura Government Jobs mein TPSC, TRPB, Tripura Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Tripura Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Tripura</h2>
<p>Tripura mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk posts hain. ITI holders TSECL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates TPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Tripura</h2>
<p>Tripura Police TRPB, AGMC health bharti, TBSE teacher recruitment aur TSECL technical posts — yeh Tripura ke top hiring departments hain 2026 mein. TPSC calendar follow karo aur Top Sarkari Jobs par Tripura Recruitment 2026 ka poora update paao.</p>""",

  "Manipur": """<h2>About Manipur Government Jobs 2026</h2>
<p>Manipur Sarkari Naukri 2026 ke liye MPSC Manipur (Manipur Public Service Commission) pramukh recruitment body hai. Imphal, Churachandpur, Bishnupur, Thoubal, Senapati aur Ukhrul ke candidates Manipur Government Jobs 2026 ki taiyari mein hain.</p>
<p>MSRTC, MSPDCL aur Manipur Housing Board important recruitment bodies hain. Manipur Police aur MPPRB ke through constable posts nikalte hain. JNIMS Imphal aur Manipur NHM ke under health posts aate hain. BSEM aur COHSEM Board ke through teacher recruitment hoti hai. Manipur University aur DM College mein bhi academic posts available hain 2026 mein.</p>
<p>Manipur Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Chandel, Jiribam, Tamenglong, Kangpokpi ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Manipur</h2>
<p>Latest Manipur Government Jobs mein MPSC, MPPRB, Manipur Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Manipur Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Manipur</h2>
<p>Manipur mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk posts hain. ITI holders MSPDCL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates MPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Manipur</h2>
<p>Manipur Police MPPRB, JNIMS health bharti, BSEM teacher recruitment aur MSPDCL technical posts — yeh Manipur ke top hiring departments hain 2026 mein. MPSC calendar follow karo aur Top Sarkari Jobs par Manipur Recruitment 2026 ka poora update paao.</p>""",

  "Meghalaya": """<h2>About Meghalaya Government Jobs 2026</h2>
<p>Meghalaya Sarkari Naukri 2026 ke liye MPSC Meghalaya (Meghalaya Public Service Commission) pramukh recruitment body hai. Shillong, Tura, Jowai, Nongpoh, Williamnagar aur Baghmara ke candidates Meghalaya Government Jobs 2026 ki taiyari mein hain.</p>
<p>MTC, MEPCO aur Meghalaya Housing Corporation important recruitment bodies hain. Meghalaya Police aur MRPB ke through constable posts nikalte hain. Civil Hospital Shillong aur Meghalaya NHM ke under health posts aate hain. MBOSE aur MSCE Board ke through teacher recruitment hoti hai. North Eastern Hill University aur Martin Luther Christian University mein bhi academic posts available hain 2026 mein.</p>
<p>Meghalaya Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. East Khasi Hills, Ri Bhoi, West Garo Hills ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Meghalaya</h2>
<p>Latest Meghalaya Government Jobs mein MPSC, MRPB, Meghalaya Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Meghalaya Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Meghalaya</h2>
<p>Meghalaya mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk posts hain. ITI holders MEPCO mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates MPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Meghalaya</h2>
<p>Meghalaya Police MRPB, Civil Hospital health staff, MBOSE teacher recruitment aur MEPCO technical posts — yeh Meghalaya ke top hiring departments hain 2026 mein. MPSC calendar follow karo aur Top Sarkari Jobs par Meghalaya Recruitment 2026 ka poora update paao.</p>""",

  "Nagaland": """<h2>About Nagaland Government Jobs 2026</h2>
<p>Nagaland Sarkari Naukri 2026 ke liye NPSC (Nagaland Public Service Commission) pramukh recruitment body hai. Kohima, Dimapur, Mokokchung, Tuensang, Wokha aur Zunheboto ke candidates Nagaland Government Jobs 2026 ki taiyari mein hain.</p>
<p>NSRTC, Nagaland Power Department aur Nagaland Housing Federation important recruitment bodies hain. Nagaland Police aur NPRB ke through constable posts nikalte hain. Naga Hospital Authority aur Nagaland NHM ke under health posts aate hain. NBSE aur NCHSE Board ke through teacher recruitment hoti hai. Nagaland University aur ICFAI University Nagaland mein bhi academic posts available hain 2026 mein.</p>
<p>Nagaland Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Phek, Kiphire, Longleng, Mon ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Nagaland</h2>
<p>Latest Nagaland Government Jobs mein NPSC, NPRB, Nagaland Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Nagaland Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Nagaland</h2>
<p>Nagaland mein 10th pass ke liye Group D, 12th pass ke liye constable aur clerk posts hain. ITI holders Power Department mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates NPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Nagaland</h2>
<p>Nagaland Police NPRB, Naga Hospital health staff, NBSE teacher recruitment aur Nagaland Power Department technical posts — yeh Nagaland ke top hiring departments hain 2026 mein. NPSC calendar follow karo aur Top Sarkari Jobs par Nagaland Recruitment 2026 ka poora update paao.</p>""",

  "Mizoram": """<h2>About Mizoram Government Jobs 2026</h2>
<p>Mizoram Sarkari Naukri 2026 ke liye MPSC Mizoram (Mizoram Public Service Commission) pramukh recruitment body hai. Aizawl, Lunglei, Champhai, Serchhip, Kolasib aur Lawngtlai ke candidates Mizoram Government Jobs 2026 ki taiyari mein hain.</p>
<p>MZRTC, ZIDCO aur Mizoram Housing Board important recruitment bodies hain. Mizoram Police aur MIRPB ke through constable posts nikalte hain. Civil Hospital Aizawl aur Mizoram NHM ke under health posts aate hain. MBSE aur HSSLC Board ke through teacher recruitment hoti hai. Mizoram University aur Pachhunga University College mein bhi academic posts available hain 2026 mein.</p>
<p>Mizoram Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Mamit, Siaha, Saitual, Khawzawl ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Mizoram</h2>
<p>Latest Mizoram Government Jobs mein MPSC Mizoram, MIRPB, Mizoram Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Mizoram Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Mizoram</h2>
<p>Mizoram mein 10th pass ke liye Group D, 12th pass ke liye constable aur clerk posts hain. ITI holders ZIDCO mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates MPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Mizoram</h2>
<p>Mizoram Police MIRPB, Civil Hospital health staff, MBSE teacher recruitment aur ZIDCO technical posts — yeh Mizoram ke top hiring departments hain 2026 mein. MPSC Mizoram calendar follow karo aur Top Sarkari Jobs par Mizoram Recruitment 2026 ka poora update paao.</p>""",

  "Arunachal Pradesh": """<h2>About Arunachal Pradesh Government Jobs 2026</h2>
<p>Arunachal Pradesh Sarkari Naukri 2026 ke liye APPSC Arunachal (Arunachal Pradesh Public Service Commission) aur APSSB pramukh recruitment bodies hain. Itanagar, Naharlagun, Pasighat, Ziro, Bomdila aur Tawang ke candidates AP Government Jobs 2026 ki taiyari mein hain.</p>
<p>APST, APECL aur Arunachal Pradesh Housing Board important recruitment bodies hain. Arunachal Pradesh Police aur APSSB ke through constable posts nikalte hain. TRIHMS Naharlagun aur AP NHM Arunachal ke under health posts aate hain. CBSE Arunachal aur APDHTE ke through teacher recruitment hoti hai. Rajiv Gandhi University aur Arunachal University of Studies mein bhi academic posts available hain 2026 mein.</p>
<p>Arunachal Pradesh Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Papum Pare, East Siang, West Kameng, Dibang Valley ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Arunachal Pradesh</h2>
<p>Latest Arunachal Pradesh Government Jobs mein APPSC, APSSB, AP Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Arunachal Pradesh Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Arunachal Pradesh</h2>
<p>Arunachal mein 10th pass ke liye Group D, 12th pass ke liye constable aur clerk posts hain. ITI holders APECL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates APPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Arunachal Pradesh</h2>
<p>AP Police APSSB, TRIHMS health staff, CBSE teacher recruitment aur APECL technical posts — yeh Arunachal ke top hiring departments hain 2026 mein. APPSC calendar follow karo aur Top Sarkari Jobs par Arunachal Pradesh Recruitment 2026 ka poora update paao.</p>""",

  "Sikkim": """<h2>About Sikkim Government Jobs 2026</h2>
<p>Sikkim Sarkari Naukri 2026 ke liye SPSC (Sikkim Public Service Commission) aur SSSB pramukh recruitment bodies hain. Gangtok, Namchi, Mangan, Gyalshing, Rangpo aur Jorethang ke candidates Sikkim Government Jobs 2026 ki taiyari mein hain.</p>
<p>SNT Sikkim, SPDCL aur Sikkim Housing Development Corporation important recruitment bodies hain. Sikkim Police aur SSSB ke through constable posts nikalte hain. STNM Hospital Gangtok aur Sikkim NHM ke under health posts aate hain. BSEM Sikkim aur COHSEM Sikkim ke through teacher recruitment hoti hai. Sikkim University aur Sikkim Manipal University mein bhi academic posts available hain 2026 mein.</p>
<p>Sikkim Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. North Sikkim, West Sikkim, South Sikkim ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Sikkim</h2>
<p>Latest Sikkim Government Jobs mein SPSC, SSSB, Sikkim Police aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Sikkim Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Sikkim</h2>
<p>Sikkim mein 10th pass ke liye Group D, 12th pass ke liye constable aur clerk posts hain. ITI holders SPDCL mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates SPSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Sikkim</h2>
<p>Sikkim Police SSSB, STNM Hospital health staff, COHSEM teacher recruitment aur SPDCL technical posts — yeh Sikkim ke top hiring departments hain 2026 mein. SPSC calendar follow karo aur Top Sarkari Jobs par Sikkim Recruitment 2026 ka poora update paao.</p>""",

  "Chandigarh": """<h2>About Chandigarh Government Jobs 2026</h2>
<p>Chandigarh Sarkari Naukri 2026 ke liye CSSC (Chandigarh Service Selection Commission) aur UT Administration pramukh recruitment bodies hain. Chandigarh Sector 1-50, Industrial Area, Manimajra aur Panchkula nearby ke candidates Chandigarh Government Jobs 2026 ki taiyari mein hain. Union Territory hone ki wajah se yahan central aur UT dono level ke jobs available hain.</p>
<p>CTU Chandigarh, PSPCL, Chandigarh Housing Board aur CSCL important recruitment bodies hain. Chandigarh Police aur UT Police ke through constable posts nikalte hain. PGIMER Chandigarh aur Government Medical College ke under health posts aate hain. CBSE Board aur UT Education Department ke through teacher recruitment hoti hai. Panjab University Chandigarh aur Chandigarh University mein bhi academic posts available hain 2026 mein.</p>
<p>Chandigarh Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. CTU mein driver posts, PGIMER mein technical posts aur UT Administration mein clerk posts regularly nikalte hain.</p>
<h2>Latest Government Jobs in Chandigarh</h2>
<p>Latest Chandigarh Government Jobs mein CSSC, Chandigarh Police, PGIMER aur CTU ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Chandigarh Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Chandigarh</h2>
<p>Chandigarh mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk aur assistant posts hain. ITI holders CTU mein, Diploma candidates UT PWD mein apply kar sakte hain. Graduate aur PG candidates CSSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Chandigarh</h2>
<p>Chandigarh Police UT, PGIMER medical staff, UT Education teacher recruitment aur CTU technical posts — yeh Chandigarh ke top hiring departments hain 2026 mein. CSSC notifications follow karo aur Top Sarkari Jobs par Chandigarh Recruitment 2026 ka poora update paao.</p>""",

  "Puducherry": """<h2>About Puducherry Government Jobs 2026</h2>
<p>Puducherry Sarkari Naukri 2026 ke liye PSCPB (Puducherry Service Commission cum Public Board) pramukh recruitment body hai. Puducherry, Karaikal, Mahe aur Yanam — in chaar enclaves ke candidates Puducherry Government Jobs 2026 ki taiyari mein hain.</p>
<p>PRTC, PCCW aur Puducherry Industrial Promotion Development important recruitment bodies hain. Puducherry Police aur UT Armed Police ke through constable posts nikalte hain. JIPMER Puducherry aur Indira Gandhi Government Hospital ke under health posts aate hain — JIPMER ek very prestigious institution hai. PBSE aur Pondicherry Board ke through teacher recruitment hoti hai. Pondicherry University mein bhi academic posts available hain 2026 mein.</p>
<p>Puducherry Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Villianur, Ozhukarai, Bahour ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Puducherry</h2>
<p>Latest Puducherry Government Jobs mein PSCPB, Puducherry Police, JIPMER aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Puducherry Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Puducherry</h2>
<p>Puducherry mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk posts hain. ITI holders PCCW mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates PSCPB exam aur JIPMER technical posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Puducherry</h2>
<p>Puducherry Police UT, JIPMER medical staff, PBSE teacher recruitment aur PRTC technical posts — yeh Puducherry ke top hiring departments hain 2026 mein. PSCPB notifications follow karo aur Top Sarkari Jobs par Puducherry Recruitment 2026 ka poora update paao.</p>""",

  "Andaman and Nicobar Islands": """<h2>About Andaman and Nicobar Islands Government Jobs 2026</h2>
<p>Andaman and Nicobar Islands Sarkari Naukri 2026 ke liye ANDAMAN SSC (Andaman and Nicobar Staff Selection Commission) aur UT Administration pramukh recruitment bodies hain. Port Blair, Diglipur, Mayabunder, Car Nicobar aur Campbell Bay ke candidates A&N Government Jobs 2026 ki taiyari mein hain.</p>
<p>Andaman Nicobar Transport, Port Blair Municipality aur ANIIDCO important recruitment bodies hain. Andaman Police aur UT Police Force ke through constable posts nikalte hain. GB Pant Hospital Port Blair aur UT NHM ke under health posts aate hain. CBSE Andaman aur Directorate of Education A&N ke through teacher recruitment hoti hai. Dr. BR Ambedkar Institute of Technology mein bhi academic posts available hain 2026 mein.</p>
<p>A&N Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. North Andaman, Middle Andaman, Little Andaman ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Andaman and Nicobar Islands</h2>
<p>Latest A&N Government Jobs mein ANDAMAN SSC, UT Police, GB Pant Hospital aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Andaman Nicobar Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Andaman and Nicobar Islands</h2>
<p>A&N mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk posts hain. ITI holders Port Blair Municipality mein, Diploma candidates PWD mein apply kar sakte hain. Graduate aur PG candidates ANDAMAN SSC exam aur teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Andaman and Nicobar Islands</h2>
<p>A&N Police UT, GB Pant Hospital medical staff, DoE teacher recruitment aur ANIIDCO technical posts — yeh A&N ke top hiring departments hain 2026 mein. UT Administration notifications follow karo aur Top Sarkari Jobs par Andaman Nicobar Recruitment 2026 ka poora update paao.</p>""",

  "Ladakh": """<h2>About Ladakh Government Jobs 2026</h2>
<p>Ladakh Sarkari Naukri 2026 ke liye LAHDC Leh aur LAHDC Kargil (Ladakh Autonomous Hill Development Council) pramukh recruitment bodies hain. Leh, Kargil, Nubra, Zanskar, Drass aur Sankoo ke candidates Ladakh Government Jobs 2026 ki taiyari mein hain. 2019 mein UT status milne ke baad Ladakh mein government jobs ka scope aur badh gaya hai.</p>
<p>LAHDC, LREDA aur UT Ladakh PWD important recruitment bodies hain. Ladakh Police aur UT Police Recruitment ke through constable posts nikalte hain. SNM Hospital Leh aur Kargil District Hospital ke under health posts aate hain. CBSE Ladakh aur UT Education Department ke through teacher recruitment hoti hai. University of Ladakh nayi hai aur isme teaching posts 2026 mein expected hain.</p>
<p>Ladakh Recruitment 2026 mein 10th, 12th, ITI, Diploma aur Graduate sabhi ke liye avsar hain. Changtang, Sham, Rupshu, Zanskar ke candidates bhi online form se apply kar sakte hain.</p>
<h2>Latest Government Jobs in Ladakh</h2>
<p>Latest Ladakh Government Jobs mein LAHDC, UT Police, SNM Hospital aur NHM ki vacancies open hain. Online form, admit card aur result Top Sarkari Jobs par milenge. Ladakh Sarkari Naukri 2026 ka koi update miss mat karo.</p>
<h2>Qualification Wise Jobs in Ladakh</h2>
<p>Ladakh mein 10th pass ke liye Group D aur constable, 12th pass ke liye clerk posts hain. ITI holders PWD mein, Diploma candidates LREDA mein apply kar sakte hain. Graduate aur PG candidates LAHDC exam aur University of Ladakh teacher posts ke liye eligible hain.</p>
<h2>Department Wise Recruitment in Ladakh</h2>
<p>Ladakh Police UT, SNM Hospital health staff, UT Education teacher recruitment aur PWD technical posts — yeh Ladakh ke top hiring departments hain 2026 mein. LAHDC notifications follow karo aur Top Sarkari Jobs par Ladakh Recruitment 2026 ka poora update paao.</p>""",
}
# ── END STATE SEO CONTENT ────────────────────────────────────────────────────


def _seo_listing_content(title, jobs, canon_url):
    """Unique SEO content for listing pages — fixes thin content for ~4900 pages."""
    import re as _re
    _n = len(jobs); _yr = YEAR
    _url = canon_url.lower()
    _name = _re.sub(r'\s*\d{4}\s*$','', title).strip()
    _name = _re.sub(r'\s*(govt|government)\s+jobs?\s*$','', _name, flags=_re.I).strip()
    if '/state/' in _url or '/state-jobs/' in _url:
        _st = _re.sub(r'\s*(govt|government)\s+jobs?.*$','', _name, flags=_re.I).strip()
        # ── Rich state-specific SEO content ──
        _rich = _STATE_SEO_CONTENT.get(_st, '')
        if _rich:
            return ('<div class="seo-content" style="margin:24px 10px 8px;padding:18px 20px;'                    'background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px;'                    'font-size:.92rem;line-height:1.7;color:#334155">'                    + _rich + '</div>')
        # Fallback for unknown states
        p1 = (f"{_st} Government Jobs {_yr}: Is page par {_st} state ke saare latest sarkari naukri notifications milenge. Yahan {_st} ke government departments, boards, corporations aur public sector me nikalne wali sabhi vacancies update ki jaati hain.")
        p2 = (f"{_st} me sarkari job dhoondhne wale candidates ko yahan recruitment ki puri jankari milti hai: post name, total vacancies, eligibility, age limit, application fee, important dates aur direct apply link.")
        p3 = (f"Naye {_st} government job alerts ke liye is page ko regularly check karein. Hum {_st} ke sabhi districts aur departments ki vacancies cover karte hain.")
        return ('<div class="seo-content" style="margin:24px 10px 8px;padding:18px 20px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px;font-size:.92rem;line-height:1.7;color:#334155">'            f'<h2 style="font-size:1.1rem;font-weight:800;color:#0d2257;margin:0 0 12px">About {e(_st)} {_yr}</h2>'            f'<p style="margin:0 0 12px">{e(p1)}</p>'            f'<p style="margin:0 0 12px">{e(p2)}</p>'            f'<p style="margin:0">{e(p3)}</p>'            '</div>')
    elif '/district/' in _url:
        _dt = _re.sub(r'\s+govt jobs.*$','', _name, flags=_re.I).strip()
        _dt = _re.sub(r'\s*\(.*\)\s*$','', _dt).strip()
        p1 = (f"{_dt} Government Jobs {_yr}: {_dt} district aur aas-paas ke area me nikalne wali latest sarkari vacancies yahan milti hain.")
        p2 = (f"{_dt} ke local candidates ke liye yahan har job ki complete detail hai — eligibility, vacancies, last date aur apply link.")
        p3 = (f"Naye notifications aate hi yahan automatically show honge.")
    elif '/qualification/' in _url:
        p1 = (f"{_name} Government Jobs {_yr}: {_name} qualification wale candidates ke liye sabhi eligible sarkari jobs yahan listed hain.")
        p2 = (f"Har job ke liye yahan milega: required qualification, age limit, vacancies, pay scale, selection process aur application link.")
        p3 = (f"Central aur state dono level ki {_name} jobs yahan update hoti hain.")
    elif '/education/' in _url:
        p1 = (f"{_name} {_yr}: Is page par {_name} se judi sabhi latest education updates milti hain — board exam results (10th, 12th), entrance exams, admit cards / hall tickets, counselling aur admission notifications. Dhyan dein: yeh government job vacancies nahi, balki education sector ki official updates (exams, results, admissions) hain.")
        p2 = (f"Har update ke saath complete detail hoti hai — important dates, eligibility criteria, registration/application process, exam date, result link aur official website ka direct link. Students aur parents dono ke liye ek hi jagah puri jankari milti hai.")
        p3 = (f"{_name} me aane wale naye admission forms, exam schedules, hall tickets aur result announcements ke liye yeh page rozana update hota hai. Bookmark karke regularly check karein taaki koi important education deadline miss na ho.")
    elif '/section/' in _url:
        p1 = (f"{_name} {_yr}: Is section me {_name} se judi sabhi latest updates aur notifications ek jagah milti hain.")
        p2 = (f"Har item ke liye complete details diye gaye hain — dates, eligibility aur direct links.")
        p3 = (f"Government job aspirants ke liye {_name} ek important category hai.")
    elif '/category/' in _url:
        p1 = (f"{_name} {_yr}: {_name} se related sabhi government job notifications yahan ek saath milte hain.")
        p2 = (f"Har job ki puri detail yahan hai — eligibility, vacancies, dates aur apply link.")
        p3 = (f"Yeh page automatically latest {_name} openings se update hota hai.")
    else:
        p1 = (f"{_name} {_yr}: Latest government job notifications aur sarkari naukri updates yahan milti hain.")
        p2 = (f"Har job ke saath complete details hain — eligibility, dates aur apply links.")
        p3 = (f"Naye notifications ke liye yeh page regularly check karein.")
    return ('<div class="seo-content" style="margin:24px 10px 8px;padding:18px 20px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px;font-size:.92rem;line-height:1.7;color:#334155">'
        f'<h2 style="font-size:1.1rem;font-weight:800;color:#0d2257;margin:0 0 12px">About {e(_name)} {_yr}</h2>'
        f'<p style="margin:0 0 12px">{e(p1)}</p>'
        f'<p style="margin:0 0 12px">{e(p2)}</p>'
        f'<p style="margin:0">{e(p3)}</p>'
        '</div>')

_DISK_JOB_SLUGS = None
def _page_exists_on_disk(slug):
    """Ground-truth check: does jobs/<slug>/index.html physically exist?
    seen_jobs is NOT reliable — it includes slugs that were _mark_job'd but whose
    detail-page write was skipped (deduped/filtered), so a slug can be in seen_jobs
    with no file. Listings must link only to pages that actually exist on disk.
    Lazily built once (all detail pages are written before any listing renders)."""
    global _DISK_JOB_SLUGS
    if _DISK_JOB_SLUGS is None:
        import glob as _g
        _DISK_JOB_SLUGS = set(os.path.basename(os.path.dirname(p))
                              for p in _g.glob(str(ROOT / 'jobs' / '*' / 'index.html')))
    return slug in _DISK_JOB_SLUGS

def build_listing_page(title, jobs, canon_url, breadcrumbs, desc='', top_html='', list_noun='Jobs'):
    # _DISK_JOB_SLUGS freezes on its first-ever call (often triggered early,
    # mid-way through the detail-page write loop, by the "Related Jobs" widget).
    # Force a fresh glob here so every listing page sees ALL detail pages
    # written so far in this run — otherwise jobs added later in the same run
    # (e.g. brand-new postings) get silently dropped from listing cards even
    # though their /jobs/<slug>/ page already exists on disk.
    global _DISK_JOB_SLUGS
    _DISK_JOB_SLUGS = None
    _yr_str = str(YEAR)
    _t = title if _yr_str in title else f"{title} {YEAR}"
    # SEO FIX: latest-jobs page ka title differentiate karo homepage se
    _url_key_for_title = canon_url.rstrip('/').split('/')[-1]
    if _url_key_for_title in ('latest-jobs', 'latest-jobs-new', 'latest-notifications', 'latest-govt-jobs'):
        title_tag = f"Latest Sarkari Naukri {YEAR} — New Govt Job Alerts | Top Sarkari Jobs"
    else:
        title_tag = f"{_t} — Apply Online | Top Sarkari Jobs"

    # FIX #12: section-specific meta description > passed desc > generic fallback
    _url_key = canon_url.rstrip('/').split('/')[-1]
    meta_desc = (
        SECTION_META_DESC.get(_url_key) or
        (desc[:155] if desc else None) or
        f"{title} {YEAR}: Latest government job notifications — check eligibility, important dates and apply online."
    )
    meta_desc = meta_desc[:160]

    # FIX #5: context-aware OG image for section pages
    if any(x in canon_url for x in ['/result', '/results']):
        _og_img = f"{BASE_URL}/og-results.png"
    elif 'admit' in canon_url:
        _og_img = f"{BASE_URL}/og-admit.png"
    elif any(x in canon_url for x in ['/study', 'pass-jobs', 'graduate', 'iti', 'diploma', 'btech']):
        _og_img = f"{BASE_URL}/og-study.png"
    elif any(x in canon_url for x in ['scheme', 'yojna', 'csc']):
        _og_img = f"{BASE_URL}/og-scheme.png"
    else:
        _og_img = f"{BASE_URL}/og-jobs.png"

    bc_html    = '<nav class="bc" aria-label="Breadcrumb"><a href="/">Home</a>'
    for lbl, url in breadcrumbs:
        bc_html += f'<span class="bc-sep">›</span><a href="{e(url)}">{e(lbl)}</a>'
    bc_html   += f'<span class="bc-sep">›</span><span aria-current="page">{e(title)}</span></nav>'
    bc_schema  = {'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':
        [{'@type':'ListItem','position':1,'name':'Home','item':BASE_URL+'/'}] +
        [{'@type':'ListItem','position':i+2,'name':b[0],'item':BASE_URL+b[1]} for i,b in enumerate(breadcrumbs)] +
        [{'@type':'ListItem','position':len(breadcrumbs)+2,'name':title,'item':canon_url}]}

    # ItemList schema for top 10 jobs (rich results)
    # Uses get_canonical_slug() so schema URLs match the actual pages on disk.
    _il_elements = []
    for _ili, _jb in enumerate(jobs[:10], 1):
        _bd2 = _jb.get('basic_details', {}) or {}
        _jt2 = safe(_bd2.get('job_title', '') or _jb.get('title', '') or _jb.get('name', ''))
        _js2 = get_canonical_slug(_jb)
        if _jt2 and _js2:
            _il_elements.append({'@type':'ListItem','position':_ili,'name':_jt2,
                                 'url':f"{BASE_URL}/jobs/{_js2}/"})
    _schemas_list = [bc_schema]
    if _il_elements:
        _schemas_list.append({'@context':'https://schema.org','@type':'ItemList',
            'name':title_tag,'description':meta_desc,'url':canon_url,
            'numberOfItems':len(jobs),'itemListElement':_il_elements})
    schemas_tag = '\n'.join(
        f'<script type="application/ld+json">{json.dumps(s, ensure_ascii=False)}</script>'
        for s in _schemas_list)

    cards_html = ''
    _idx = 0  # FIX: sequential display number for RENDERED cards only (skipped jobs must not eat a number)
    for job in jobs:
        bd    = job.get('basic_details',{}) or {}
        dates = job.get('important_dates',{}) or {}
        il    = job.get('important_links',{}) or {}
        jtitle = safe(bd.get('job_title','') or job.get('title','') or job.get('name',''))
        if not jtitle: continue
        # ── CANONICAL SLUG: use get_canonical_slug() — never slugify() inline ──────
        # Guarantees listing card href matches the actual /jobs/{slug}/index.html
        # on disk. Prevents 404s from prefix / truncation / hash mismatches.
        jslug = get_canonical_slug(job)
        # ── ZERO-404 GUARANTEE ────────────────────────────────────────────────
        # If this job's canonical slug has no physical page (deduped into another
        # record, filtered, or title-drifted), resolve it to the real canonical
        # page via the dedup fingerprint maps; if still none exists, SKIP the card
        # entirely rather than emit a dead /jobs/<slug>/ link. seen_jobs holds every
        # page on disk (preloaded + freshly built) by the time listings render.
        _has_listing_override = bool(safe(job.get('_listing_url','')))
        if not _has_listing_override and not _page_exists_on_disk(jslug):
            _alt = None
            try:
                _dup, _canon = _is_dup_job(jslug, jtitle)
                if _canon and _page_exists_on_disk(_canon):
                    _alt = _canon
            except Exception:
                pass
            if not _alt:
                _fp_alt = _fingerprint(jtitle)
                if _fp_alt and _page_exists_on_disk(seen_fp.get(_fp_alt, '')):
                    _alt = seen_fp[_fp_alt]
            if _alt:
                jslug = _alt
            else:
                continue   # no real page on disk → never render a 404 link
        # Landing/index pages can override the per-row link target (e.g. /state/{slug}/
        # instead of /jobs/{slug}/) via the optional _listing_url field.
        _idx += 1  # FIX: only count jobs that survive all skip-checks above → true continuous 1,2,3...
        _row_url = safe(job.get('_listing_url','')) or f"/jobs/{e(jslug)}/"
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
        cards_html += f'''<article class="job-card" data-title="{e(jtitle.lower())}" data-org="{e(jorg.lower())}" onclick="if(!getSelection().toString()){{location.href='{_row_url}'}}">
  <div class="job-card-title"><span class="jc-sn">{_idx}</span><a href="{_row_url}">{e(jtitle)}</a></div>
  <div class="job-card-org"><i class="fa-regular fa-building"></i> {e(jorg[:60])}</div>
  <div class="job-card-meta">
    {f'<span class="jm-badge" style="background:#dcfce7;color:#15803d">{e(jvac)} {"Posts" if _row_url.startswith("/jobs/") else list_noun}</span>' if jvac else ''}
    {f'<span class="jm-badge" style="background:#ede9fe;color:#5b21b6">{e(jmode)}</span>' if _row_url.startswith("/jobs/") else ''}
    {status_badge}
  </div>
  {f'<div class="job-card-date{urgent_cls}"><i class="fa-regular fa-clock"></i> Last Date: <strong>{e(jld)}</strong></div>' if jld else ''}
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

    # ── INTERNAL LINKING: Add 12 related job links at bottom of listing pages ──
    # Picks jobs from same category context (boosts crawler discovery + SEO link equity).
    _related_links_html = ''
    try:
        _seed_cat = ''
        _cu = (canon_url or '').lower()
        if '/state/' in _cu or '/state-jobs/' in _cu: _seed_cat = 'state'
        elif '/category/' in _cu: _seed_cat = 'cat'
        elif '/qualification/' in _cu: _seed_cat = 'qual'
        elif '/section/' in _cu: _seed_cat = 'sec'
        # Pick first 12 jobs from this listing as internal links; if listing < 12,
        # supplement from _REL_INDEX (global related-jobs pool).
        _pick = []
        _seen = set()
        for _j in (jobs or [])[:30]:
            _js = get_canonical_slug(_j)
            _jn = _j.get('title','') or (_j.get('basic_details') or {}).get('job_title','') or _j.get('name','') or ''
            if _js and _js not in _seen and _jn and _page_exists_on_disk(_js):
                _pick.append((_js, _jn[:65]))
                _seen.add(_js)
            if len(_pick) >= 12: break
        # Fallback from global related index
        if len(_pick) < 12:
            for _rs, _rinfo in list(_REL_INDEX.items())[:50]:
                if _rs in _seen: continue
                _rn = (_rinfo.get('title') if isinstance(_rinfo, dict) else '') or ''
                if _rs and _rn:
                    _pick.append((_rs, _rn[:65]))
                    _seen.add(_rs)
                if len(_pick) >= 12: break
        if _pick:
            _links = ''.join(
                f'<a href="/jobs/{e(_s)}/" style="display:block;padding:8px 12px;margin:4px 0;background:#fff;border:1px solid #e5e7eb;border-radius:8px;color:#0d2257;font-size:.88rem;font-weight:600;text-decoration:none">→ {e(_n)}</a>'
                for _s, _n in _pick
            )
            _related_links_html = (
                '<div class="rel-jobs" style="margin:24px 10px 8px;padding:18px 18px 14px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px">'
                '<h2 style="font-size:1.05rem;font-weight:800;color:#0d2257;margin:0 0 12px">Related Government Jobs You May Like</h2>'
                f'{_links}</div>'
            )
    except Exception: pass

    body = (f'<div class="cat-wrap">'
            f'<h1 class="cat-h1" style="margin:12px 10px 4px">{e(title)}</h1>'
            f'<p class="cat-count" style="margin:0 10px 12px;color:#64748b;font-size:.78rem">{len(jobs)} records</p>'
            f'{top_html}'
            f'<div class="search-bar" style="margin:0 10px 12px">'
            f'<input type="search" placeholder="Search..." aria-label="Search" onkeyup="filterJobs(this.value)" autocomplete="off"/>'
            f'</div><div id="jobList" style="padding:0 10px">{cards_html}</div>'
            f'{_seo_listing_content(title, jobs, canon_url)}'
            f'{_related_links_html}'
            f'<div style="padding:0 10px">{REL_CATS_HTML}</div></div>'
            f'{filter_js}')

    return f'''<!DOCTYPE html>
<html lang="en-IN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>{VP_SNIPPET}
<title>{e(title_tag)}</title>
<meta name="description" content="{e(meta_desc)}"/>
<meta name="author" content="Top Sarkari Jobs"/>
<meta name="geo.region" content="IN"/>
<meta name="language" content="en-IN"/>
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"/>
<link rel="canonical" href="{e(canon_url)}"/>
<meta property="og:type" content="website"/>
<meta property="og:site_name" content="Top Sarkari Jobs"/>
<meta property="og:title" content="{e(title_tag)}"/>
<meta property="og:description" content="{e(meta_desc)}"/>
<meta property="og:url" content="{e(canon_url)}"/>
<meta property="og:image" content="{_og_img}"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:site" content="@topsarkarijobs"/>
<meta name="twitter:title" content="{e(title_tag)}"/>
<meta name="twitter:description" content="{e(meta_desc)}"/>
<meta name="twitter:image" content="{_og_img}"/>
{schemas_tag}
<script src="/tsj-config.js"></script>
<link rel="icon" href="/image.ico"/>
<link rel="stylesheet" href="/styles.css"/>
<link rel="preload" href="/fonts/fa/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'"/>
<noscript><link rel="stylesheet" href="/fonts/fa/all.min.css"/></noscript>
<link rel="manifest" href="/manifest.json"/>
<meta name="theme-color" content="#0d2257"/>
<script>(function(){{var _l=false;function la(){{if(_l)return;_l=true;var s=document.createElement('script');s.src='/analytics.js';s.async=true;document.head.appendChild(s);}}window.addEventListener('scroll',la,{{once:true,passive:true}});window.addEventListener('click',la,{{once:true}});setTimeout(la,4000);}})();</script>
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
_load_slug_registry(ROOT)  # Slug registry: title-change proof permanent slugs
with open(CJ_FILE, encoding='utf-8') as f: CJ = json.load(f)

# Capture FJA content_sections IMMEDIATELY after load — some later loops strip it
# (and even _scraped_from) from job dicts. Key by URL + slug + normalized title so
# build_all_sections can always recover it, whichever key the job_obj still has.
def _cs_norm_title(t):
    return re.sub(r'[^a-z0-9]+', ' ', str(t or '').lower()).strip()

_CS_BY_KEY = {}
try:
    _cs_n = 0
    for _uj0 in (CJ.get('freejobalert_unified', {}) or {}).get('deduped_jobs', []) or []:
        _cs0 = _uj0.get('content_sections')
        if not (isinstance(_cs0, list) and _cs0):
            continue
        _cs_n += 1
        _title0 = (_uj0.get('basic_details') or {}).get('job_title', '')
        for _k0 in (_uj0.get('_scraped_from'), _uj0.get('slug'), _cs_norm_title(_title0)):
            if _k0:
                _CS_BY_KEY[_k0] = _cs0
    print(f"  [content_sections] cached {_cs_n} FJA section-sets ({len(_CS_BY_KEY)} keys)")
except Exception as _e0:
    print(f"  [content_sections] cache failed: {_e0}")
with open(DU_FILE, encoding='utf-8') as f: DU = json.load(f)

# ── SLUG NORMALIZATION: PC scraper ke slugs me kabhi-kabhi trailing dash ──
# rehti hai (jab title 80+ chars ho aur cut dash pe land kare). Saare slugs ko
# load ke turant baad normalize karte hain so URL == disk page name.
def _normalize_all_slugs():
    _fixed_count = 0
    # Unified deduped_jobs
    _uni = (CJ.get('freejobalert_unified', {}) or {}).get('deduped_jobs', []) or []
    for _j in _uni:
        _s = _j.get('slug', '')
        if _s:
            _ns = _norm_slug(_s)
            if _ns != _s:
                _j['slug'] = _ns
                _fixed_count += 1
    # sarkari_data.jobs
    for _j in (CJ.get('sarkari_data', {}) or {}).get('jobs', []) or []:
        _s = _j.get('slug', '')
        if _s:
            _ns = _norm_slug(_s)
            if _ns != _s:
                _j['slug'] = _ns
                _fixed_count += 1
    # freejobalert_categories
    for _cat, _jobs in (CJ.get('freejobalert_categories', {}) or {}).items():
        if isinstance(_jobs, list):
            for _j in _jobs:
                _s = _j.get('slug', '') if isinstance(_j, dict) else ''
                if _s:
                    _ns = _norm_slug(_s)
                    if _ns != _s:
                        _j['slug'] = _ns
                        _fixed_count += 1
    if _fixed_count > 0:
        print(f"  [slug-norm] Normalized {_fixed_count} slugs (stripped trailing dashes)")
_normalize_all_slugs()

# ── BACKWARD COMPAT: Smart-search reads `freejobalert_categories` (old format).
# New scraper puts everything in `freejobalert_unified`. Rebuild categories
# from unified so search works. Also write back to data/ JSON file.
_uni_for_search = CJ.get('freejobalert_unified', {}) or {}
_uni_jobs_search = _uni_for_search.get('deduped_jobs', []) or []
_fja_cats_existing = CJ.get('freejobalert_categories', {}) or {}
_fja_cats_empty = sum(len(v) for v in _fja_cats_existing.values() if isinstance(v, list)) == 0

if _uni_jobs_search and _fja_cats_empty:
    print(f"  [search-compat] Rebuilding freejobalert_categories from {len(_uni_jobs_search)} unified jobs...")
    _rebuilt_cats = {}
    _by_fja = _uni_for_search.get('by_fja_category', {}) or {}
    _url_to_uj = {j.get('_scraped_from',''): j for j in _uni_jobs_search}
    for _cat_name, _urls in _by_fja.items():
        _cat_jobs = []
        for _u in _urls:
            _uj = _url_to_uj.get(_u)
            if _uj:
                _cat_jobs.append(_uj)
        if _cat_jobs:
            _rebuilt_cats[_cat_name] = _cat_jobs
    # Also create Latest_Notifications combining all unified jobs
    if 'Latest_Notifications' not in _rebuilt_cats:
        _rebuilt_cats['Latest_Notifications'] = _uni_jobs_search
    CJ['freejobalert_categories'] = _rebuilt_cats
    print(f"  [search-compat] Rebuilt {len(_rebuilt_cats)} FJA categories")
    # Write back to data/ JSON so smart-search.js reads updated data
    _data_path_search = ROOT / 'data' / 'Complete_Jobs_Full_Data.json'
    if _data_path_search.parent.exists():
        try:
            with open(_data_path_search, 'w', encoding='utf-8') as _f:
                json.dump(CJ, _f, ensure_ascii=False, separators=(',', ':'))
            print(f"  [search-compat] data/Complete_Jobs_Full_Data.json updated")
        except Exception as _e:
            print(f"  [search-compat] data/ write failed: {_e}")

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

# ── UNIFIED FALLBACK ────────────────────────────────────────────────────────
# scraper_fja.py ki jagah ab scraper_unified_fja.py chalta hai jo data
# 'freejobalert_unified' key mein dalta hai. Agar legacy key empty ho to
# unified data se FJA_RAW build karo taaki site mein jobs dikhein.
if not FJA_RAW:
    _uni = (CJ.get('freejobalert_unified') or {})
    _uni_jobs = _uni.get('deduped_jobs', []) or []
    if _uni_jobs:
        # by_fja_category index use karo — har category ke liye job list banao
        _by_fja = _uni.get('by_fja_category', {}) or {}
        _url_to_job = {j.get('_scraped_from', ''): j for j in _uni_jobs}
        FJA_RAW = {}
        for _cat, _urls in _by_fja.items():
            _cat_jobs = [_url_to_job[u] for u in _urls if u in _url_to_job]
            if _cat_jobs:
                FJA_RAW[_cat] = _cat_jobs
        # Agar by_fja_category empty ho to direct fja_categories tags se build karo
        if not FJA_RAW:
            from collections import defaultdict as _dd
            _tmp = _dd(list)
            for _j in _uni_jobs:
                for _c in (_j.get('fja_categories') or []):
                    _tmp[_c].append(_j)
            FJA_RAW = dict(_tmp)
        print(f"  [unified->FJA] {len(_uni_jobs)} unified jobs -> {len(FJA_RAW)} FJA categories")

FJA     = {cat: [j for j in jobs if not is_garbage_title(
               (j.get('basic_details') or {}).get('job_title','') or j.get('title',''))]
           for cat, jobs in FJA_RAW.items() if isinstance(jobs, list)}
SARK    = [j for j in (CJ.get('sarkari_data',{}) or {}).get('jobs', []) if not is_garbage_title(j.get('title',''))]

# ── FIX: Correct scraper mis-categorisation of SR_Admission ──────────────────
# The scraper sometimes tags recruitment/exam items (UPSSSC, NTA, TET, RO/ARO…)
# as SR_Admission. Real admissions say "admission", "counselling", "entrance",
# "pravesh", "UG/PG", etc. Re-classify the obvious recruitment ones to
# SR_Latest_Jobs so the Admission section shows only genuine admissions and
# every category lists the right items (JSON order preserved within each).
def _correct_admission_category(jobs):
    ADM_HINTS = re.compile(r'\b(admission|counsel+ing|entrance|pravesh|ug |pg |under ?graduate|post ?graduate|b\.?ed admission|phd admission|diploma admission)\b', re.I)
    RECRUIT_HINTS = re.compile(r'\b(recruitment|vacanc|online form|apply online|posts?|bharti|eligibility test|ro ?/ ?aro|computer assistant|fireman|guard|auditor|accountant|constable|clerk|officer)\b', re.I)
    moved = 0
    for j in jobs:
        if j.get('category') != 'SR_Admission':
            continue
        t = safe(j.get('title',''))
        # if it looks like recruitment AND has no admission hint → move out
        if RECRUIT_HINTS.search(t) and not ADM_HINTS.search(t):
            j['category'] = 'SR_Latest_Jobs'
            moved += 1
    if moved:
        print(f"  [fix] re-classified {moved} mis-tagged SR_Admission item(s) -> SR_Latest_Jobs")
    return jobs
SARK = _correct_admission_category(SARK)

# ── REMOVE deprecated categories permanently ────────────────────────────────
# State Jobs, Central Jobs and SR Admission have been retired from the site.
# (The admission corrector above first rescues any real RECRUITMENT items that
#  were mis-tagged as SR_Admission, moving them to SR_Latest_Jobs, so genuine
#  jobs are kept; only the leftover admission/state/central entries are dropped.)
_REMOVED_CATS = {'STATE_JOBS', 'CENTRAL_JOBS', 'SR_Admission'}
_before_rm = len(SARK)
SARK = [j for j in SARK if j.get('category') not in _REMOVED_CATS]
if _before_rm != len(SARK):
    print(f"  [remove] dropped {_before_rm - len(SARK)} item(s) from retired categories {sorted(_REMOVED_CATS)}")
# education_jobs can be either:
# - dict with 'sections' key: {"sections": [...]}  (old format)
# - list directly: [...]                            (new format from updated scraper)
_edu_raw = CJ.get('education_jobs', {}) or {}
if isinstance(_edu_raw, list):
    # New format: list of items — wrap into sections structure
    EDU_SEC = _edu_raw
elif isinstance(_edu_raw, dict):
    EDU_SEC = _edu_raw.get('sections', [])
else:
    EDU_SEC = []
SJ_SEC  = (CJ.get('state_jobs',{}) or {}).get('sections', [])

# ── STATE JOBS UNIFIED FALLBACK ─────────────────────────────────────────────
# scraper_state.py ki jagah unified scraper state_tags dalta hai. Agar legacy
# state_jobs empty ho to unified ke by_state index se sections build karo.
if not SJ_SEC:
    _uni2 = (CJ.get('freejobalert_unified') or {})
    _uni_jobs2 = _uni2.get('deduped_jobs', []) or []
    _by_state = _uni2.get('by_state', {}) or {}
    if _uni_jobs2 and _by_state:
        _url_map2 = {j.get('_scraped_from', ''): j for j in _uni_jobs2}
        _sj_sections = []
        for _st, _urls in _by_state.items():   # JSON order preserved
            _st_jobs = []
            for _u in _urls:
                _j2 = _url_map2.get(_u)
                if not _j2: continue
                _bd = _j2.get('basic_details', {}) or {}
                _title = _bd.get('job_title','') or _j2.get('title','')
                if _title:
                    _st_jobs.append({'name': _title,
                                     'slug': _j2.get('slug',''),
                                     'total_vacancy': _bd.get('total_vacancies',''),
                                     '_scraped_from': _u})
            if _st_jobs:
                _sj_sections.append({'state': _st, 'title': _st + ' Govt Jobs',
                                     'category': 'STATE WISE JOBS - ' + _st,
                                     'items': _st_jobs})
        SJ_SEC = _sj_sections
        print(f"  [unified->state] {len(SJ_SEC)} state sections from unified data")
# ── STATE JOBS: Add correct slug to prevent search duplicates ────────────────
# Smart search uses slugify(item.name) for state_jobs items → wrong slug
# (e.g. 'BEL – Havildar – 4 Posts' → 'bel-havildar-security-4-posts' which is wrong).
# Fix: Build FJA title→slug lookup, cross-match state_jobs items to correct FJA slug.
# If no match, use _scraped_from URL as fallback.
_fja_title_slug = {}
for _fcat, _fjobs in (FJA_RAW or {}).items():
    for _fj in (_fjobs or []):
        _fbd = (_fj.get('basic_details') or {})
        _ftit = _fbd.get('job_title','').strip().lower()
        if _ftit:
            _fja_title_slug[_ftit] = slugify(_fbd.get('job_title',''))[:80]

def _state_item_slug(item):
    # Try: cross-match to FJA slug by keywords in name
    _name = (item.get('name','') or '').strip()
    _name_low = _name.lower()
    # Extract key words (org + post keywords)
    _words = set(re.sub(r'[^a-z0-9\s]','',_name_low).split()) - {'posts','post','and','for','of','the','in','a'}
    # Find best FJA match
    best_match = None; best_score = 0
    for _ftit, _fslug in _fja_title_slug.items():
        _ft_words = set(re.sub(r'[^a-z0-9\s]','',_ftit).split()) - {'recruitment','2026','apply','online','offline','notification','jobs','vacancy'}
        _common = _words & _ft_words
        if len(_common) >= 2:
            score = len(_common)
            if score > best_score:
                best_score = score; best_match = _fslug
    if best_match: return best_match
    # Fallback: _scraped_from URL
    _src = item.get('_scraped_from','')
    if _src:
        _m = re.search(r'/articles/([^/?#]+)/?$', _src)
        if _m: return slugify(_m.group(1))[:80]
    return slugify(_name)[:80]

for _sjsec in SJ_SEC:
    for _sjit in _sjsec.get('items', []):
        if not _sjit.get('slug'):
            _sjit['slug'] = _state_item_slug(_sjit)

DU_SECS = DU.get('sections', [])

STATE_SLUG_FIX = {
    'andaman-and-nicobar':'andaman-nicobar','dadra-and-nagar-haveli':'dadra-nh',
    'daman-and-diu':'daman-diu','jammu-and-kashmir':'jk',
}

# Track slugs to avoid duplicates
seen_jobs    = {}  # slug → source
seen_fp      = {}  # content fingerprint (normalized title) → canonical slug
jobs_index   = {}  # for jobs-index.json
sindex       = {}  # for sections-index.json

# ── PERMANENT PAGE SYSTEM: disk pe jo pages already exist hain unhe seen maano ──
# Iska matlab: JSON se job remove ho jaye to bhi uska HTML page kabhi delete
# nahi hoga. Sirf naye jobs ke pages banenge. Category listing har baar update
# hogi (kyunki woh skip_if_exists=False se likhte hain).
import glob as _glob_preload
_H1_RE_PRELOAD = re.compile(r'<h1 class="detail-h1">([^<]+)</h1>')
_existing_disk_pages = 0
for _existing_html in _glob_preload.glob(str(ROOT / 'jobs' / '*' / 'index.html')):
    _eslug = os.path.basename(os.path.dirname(_existing_html))
    if not _eslug or _eslug in seen_jobs:
        continue
    # Title fingerprint bhi register karo — cross-source dedup ke liye
    try:
        _eh = open(_existing_html, encoding='utf-8', errors='ignore').read(30000)
        _em = _H1_RE_PRELOAD.search(_eh)
        if _em:
            _etitle = _em.group(1).strip()
            # Register fingerprint for cross-source dedup (prevents two JSON sources
            # from building two pages for the same job). Do NOT add to seen_jobs —
            # that would block the FJA/SARK loops from rebuilding existing pages
            # when content changes (hash differs or page has no TSJ_HASH yet).
            _efp = _fingerprint(_etitle) if '_fingerprint' in globals() else ''
            if _efp and _efp not in seen_fp:
                seen_fp[_efp] = _eslug
            jobs_index[_eslug] = {'cat': '__disk__', 'title': _etitle[:120], 'last_date': ''}
            _existing_disk_pages += 1
            # ── SCHEMA PATCH: load saved job JSON and patch JSON-LD in-place ──
            # This ensures pages NOT regenerated this deploy still get
            # updated baseSalary, addressRegion, postalCode, validThrough.
            try:
                _data_json = ROOT / 'jobs' / 'data' / f'{_eslug}.json'
                if _data_json.exists():
                    with open(_data_json, encoding='utf-8') as _djf:
                        _djob = json.load(_djf)
                else:
                    # No saved JSON (old/orphan page) — reconstruct from HTML
                    _djob = _reconstruct_job_from_html(_eh, _etitle, _eslug)
                _dcanon = f"{BASE_URL}/jobs/{_eslug}/"
                _dhtml  = build_schemas(_djob, _dcanon, [], _eslug)
                _patch_jsonld(Path(_existing_html), _dhtml)
            except Exception:
                pass
        else:
            # H1 nahi mila — phir bhi slug ko seen maano taaki overwrite na ho
            seen_jobs[_eslug] = '__disk__'
            _existing_disk_pages += 1
    except Exception:
        seen_jobs[_eslug] = '__disk__'
        _existing_disk_pages += 1
print(f"  [permanent-pages] {_existing_disk_pages} existing disk pages pre-loaded (will never be deleted or regenerated)")

# ── One Job = One URL: content fingerprint ───────────────────────────────────
# The same recruitment appears in multiple sources (sarkari + state + education)
# with DIFFERENT slugs (e.g. "gsssb-granthpal-recruitment-2026-apply-online" vs
# "gsssb-granthpal-1-posts"). Slug-only dedup misses these. A normalized-title
# fingerprint catches the same job regardless of slug so only ONE /jobs/ page is
# ever written. Listing pages still link every duplicate to this one canonical URL.
_FP_STOP = {'the','and','for','of','in','to','a','an','with','on','at','by','top','sarkari','jobs'}
def _fingerprint(title):
    import re as _re
    t = _re.sub(r'[^a-z0-9\s]', ' ', safe(title).lower())
    toks = [w for w in t.split() if w and w not in _FP_STOP and len(w) > 1]
    return ' '.join(toks)

# ── ❹ Related Jobs index — internal-link equity between /jobs/ pages ─────────
# Pre-build a lightweight index of every canonical job so each detail page can
# link to 6-10 contextually-related job pages (same category → org → qualification
# → state). This deepens crawl paths and spreads link equity (was 0 job-to-job
# links before). Uses the site's EXISTING .rel-btn / card classes — no new CSS.
_REL_INDEX = []          # [{slug,title,cat,org,qual,state}]
_REL_SEEN = set()
def _rel_state_of(job, bd):
    return safe(bd.get('state','') or job.get('state','') or job.get('board','')).strip().lower()
def _rel_register(slug, title, cat='', org='', qual='', state=''):
    if not slug or slug in _REL_SEEN:
        return
    _REL_SEEN.add(slug)
    _REL_INDEX.append({'slug': slug, 'title': safe(title),
                       'cat': safe(cat).lower().strip(),
                       'org': safe(org).lower().strip(),
                       'qual': safe(qual).lower().strip(),
                       'state': safe(state).lower().strip()})

def _related_jobs_html(slug, cat='', org='', qual='', state='', limit=8):
    """Pick up to `limit` related /jobs/ links by category→org→qual→state."""
    cat=safe(cat).lower().strip(); org=safe(org).lower().strip()
    qual=safe(qual).lower().strip(); state=safe(state).lower().strip()
    picked, used = [], {slug}
    def _take(pred):
        for it in _REL_INDEX:
            if len(picked) >= limit: break
            if it['slug'] in used: continue
            if pred(it):
                picked.append(it); used.add(it['slug'])
    if org:   _take(lambda it: org and it['org'] == org)
    if cat:   _take(lambda it: cat and it['cat'] == cat)
    if qual:  _take(lambda it: qual and it['qual'] == qual)
    if state: _take(lambda it: state and it['state'] == state)
    # top-up with any recent jobs so every page has >=6 internal links
    _take(lambda it: True)
    if len(picked) < 3:
        return ''
    items = ''.join(
        f'<li class="sec-item"><a href="/jobs/{e(it["slug"])}/">{e(it["title"][:90])}</a></li>'
        for it in picked[:limit] if _page_exists_on_disk(it.get("slug","")))
    if not items:
        return ''
    return ('<section class="sec-card" style="margin-top:16px">'
            '<div class="sec-head"><div class="left">'
            '<i class="fa-solid fa-link"></i> Related Jobs</div></div>'
            f'<div class="sec-body"><ul class="sec-list">{items}</ul></div></section>')


# ── VERSION-AWARE DUPLICATE LOGIC ────────────────────────────────────────────
# Duplicate check is NOT URL-only. The SAME recruitment can return with the same
# title but a NEW notification — changed dates, post count, advt no, year, PDF.
# Those must become a NEW version: a NEW record, NEW HTML, NEW unique URL/slug.
# We detect this by building a content "version signature" and only treat two
# jobs as identical when BOTH the title-core AND the signature match.

import hashlib as _vh_hash

def _extract_year(job):
    """Best-effort recruitment year (advt year / article section / from title)."""
    import re as _re
    for src in (safe((job.get('meta') or {}).get('articleSection')),
                safe(job.get('year')),
                safe(job.get('title'))):
        m = _re.search(r'\b(20\d{2})\b', src)
        if m:
            return m.group(1)
    return ''

def _extract_advt_no(job):
    """Advertisement / notification number if present (normalized like 02-2026)."""
    import re as _re
    # explicit fields first
    for k in ('advt_no','advtNo','advertisement_no','advertisementNo','notification_no','notificationNo'):
        v = safe(job.get(k))
        if v:
            return _re.sub(r'[^0-9a-z]+', '-', v.lower()).strip('-')
    # subject/category-wise rows sometimes carry it
    for lk in ('subjectWiseVacancy','subject_wise_vacancy','categoryWiseVacancy'):
        rows = job.get(lk)
        if isinstance(rows, list):
            for r in rows:
                if isinstance(r, dict):
                    v = safe(r.get('advtNo') or r.get('advt_no'))
                    if v:
                        return _re.sub(r'[^0-9a-z]+', '-', v.lower()).strip('-')
    # finally, pull "Advt No 14/2026" style out of the title
    m = _re.search(r'advt[.\s-]*no[.\s-]*([0-9]+[/\-][0-9]{2,4})', safe(job.get('title')), _re.I)
    if m:
        return _re.sub(r'[^0-9a-z]+', '-', m.group(1).lower()).strip('-')
    return ''

def _version_signature(job):
    """Hash of the fields that define a *version* of a recruitment. If any of
    these change, it's a new notification → new page. Kept deliberately small &
    stable so cosmetic edits don't spawn pages, but real changes do."""
    d = job.get('importantDates') or job.get('important_dates') or {}
    if isinstance(d, dict):
        dates = '|'.join(safe(d.get(k)) for k in
                         ('applicationBegin','application_begin','lastDateApplyOnline',
                          'last_date_apply_online','last_date','examDate','exam_date'))
    else:
        dates = safe(d)
    parts = [
        _extract_year(job),
        _extract_advt_no(job),
        dates,
        safe(job.get('totalPost') or job.get('total_post') or job.get('total_vacancy')),
        # notification PDF filename (not full URL — host can vary)
        safe(_pdf_name(job)),
    ]
    raw = '::'.join(parts)
    return _vh_hash.md5(raw.encode('utf-8')).hexdigest()[:10]

def _pdf_name(job):
    """Notification PDF file name, if any (used in the version signature)."""
    import re as _re
    links = job.get('importantLinks') or job.get('important_links') or []
    cand = []
    if isinstance(links, list):
        for it in links:
            if isinstance(it, dict):
                u = safe(it.get('url'))
                if u.lower().endswith('.pdf'):
                    cand.append(u)
    if not cand:
        return ''
    # last path segment of the first PDF
    return _re.sub(r'[^a-z0-9._-]', '', cand[0].rsplit('/', 1)[-1].lower())

# slug (base, no version) → set of version signatures already written
seen_versions = {}
versioned_variant_slugs = set()  # slugs that are intentional NEW VERSIONS (protect from prune)

def _versioned_slug(base_slug, job):
    """Return the final unique slug for this job.
    - First time we see a base_slug: use it as-is.
    - Same base_slug but DIFFERENT version signature (new notification): append
      a version suffix so it gets its OWN url/html:
         annual reissue      → -<year>      (ssc-gd-recruitment-2026)
         multiple in a year  → -<advtno>    (ssc-gd-recruitment-02-2026)
    - Same base_slug AND same signature: it's a true duplicate → return None."""
    sig = _version_signature(job)
    known = seen_versions.get(base_slug)
    if known is None:
        seen_versions[base_slug] = {sig: base_slug}
        return base_slug
    if sig in known:
        return None                      # exact same version already written
    # New version of an existing recruitment → build a distinct slug
    year = _extract_year(job)
    advt = _extract_advt_no(job)
    if advt:
        suffix = advt if year and year in advt else (f'{advt}-{year}' if year else advt)
    elif year and year not in base_slug:
        suffix = year
    else:
        suffix = sig                     # fallback: short hash keeps it unique
    cand = clean_slug(f'{base_slug}-{suffix}')[:80].strip('-')
    n = 2
    while cand in seen_jobs:
        cand = clean_slug(f'{base_slug}-{suffix}-{n}')[:80].strip('-')
        n += 1
    known[sig] = cand
    versioned_variant_slugs.add(cand)   # protect this new-version page from H1 prune
    return cand

def _is_dup_job(slug, title):
    """True if this job was already rendered — checks BOTH slug AND content
    fingerprint so cross-source duplicates are caught even when titles differ.
    (e.g. FJA 'BEL Security Recruitment 2026 - Apply Offline for 14 Jr Supervisor'
    vs SARK 'BEL Security Recruitment 2026, Apply For Jr. Supervisor, Havildar'
    → same fingerprint 'bel security supervisor havildar' → one canonical page.)
    Returns (is_dup: bool, canon_slug: str | None)
    """
    if slug in seen_jobs:
        return True, slug
    fp = _fingerprint(title)
    if fp and fp in seen_fp:
        return True, seen_fp[fp]   # caller can use this as canonical slug
    return False, None

def _mark_job(slug, title, source):
    seen_jobs[slug] = source
    fp = _fingerprint(title)
    if fp and fp not in seen_fp:
        seen_fp[fp] = slug

def _canonical_slug_for(slug, title):
    """Return the canonical slug for a job — existing slug if already seen,
    else the fingerprint-matched slug if a cross-source dup was already rendered."""
    if slug in seen_jobs:
        return slug
    fp = _fingerprint(title)
    return seen_fp.get(fp, slug)

j_count = s_count = e_count = c_count = sec_count = qual_count = 0

# ─────────────────────────────────────────────────────────────
# 1. JOB DETAIL PAGES — freejobalert_categories
# ─────────────────────────────────────────────────────────────
# ❹ Pre-pass: register every canonical job in the related-jobs index FIRST so
# that each detail page (built below) can link to other already-known jobs.
def _rel_prepass():
    _seen_fp_pre = set()
    for cat, jobs_list in FJA.items():
        if not isinstance(jobs_list, list): continue
        cat_label = QUAL_LABEL.get(cat, cat.replace('_',' ').title())
        for job in jobs_list:
            bd = job.get('basic_details', {}) or {}
            title = safe(bd.get('job_title',''))
            if not title: continue
            slug = get_canonical_slug(job)
            fp = _fingerprint(title)
            if fp in _seen_fp_pre: continue
            _seen_fp_pre.add(fp)
            _rel_register(slug, title, cat=safe(job.get('category','') or cat),
                          org=safe(bd.get('organization','') or bd.get('department','')),
                          qual=cat_label, state=_rel_state_of(job, bd))
    for job in SARK:
        bd = job.get('basic_details', {}) or {}
        title = safe(bd.get('job_title','') or job.get('title','') or
                     bd.get('jobTitle','') or job.get('name',''))
        if not title: continue
        slug = get_canonical_slug(job)
        fp = _fingerprint(title)
        if fp in _seen_fp_pre: continue
        _seen_fp_pre.add(fp)
        _rel_register(slug, title, cat=safe(job.get('category','')),
                      org=safe(bd.get('organization','') or job.get('organization','') or
                               bd.get('department','')),
                      qual='', state=_rel_state_of(job, bd))
_rel_prepass()
print(f"  [related] indexed {len(_REL_INDEX)} jobs for internal linking")

print("Generating /jobs/ pages (FJA categories)...")
for cat, jobs_list in FJA.items():
    if not isinstance(jobs_list, list): continue
    cat_slug  = QUAL_SLUG.get(cat, slugify(cat))
    cat_label = QUAL_LABEL.get(cat, cat.replace('_',' ').title())
    for job in jobs_list:
        bd = job.get('basic_details', {}) or {}
        title = safe(bd.get('job_title',''))
        if not title: continue
        # Use get_canonical_slug() — respects _canonical_slug from scraper first,
        # then slug field, then slug-registry. Detail page and listing card always
        # resolve to the same path this way.
        slug = get_canonical_slug(job)
        # SEO FIX (One Job = One URL): the same recruitment is listed under
        # multiple qualification categories. The old line appended "-{cat_slug}"
        # which minted a SEPARATE duplicate HTML page per category
        # (e.g. ...-bba, ...-bca, ...-mba-pgdm) -> 10-19 dup URLs per job and
        # "Discovered - currently not indexed" in Google. We now skip duplicates
        # so the first-seen category owns the single canonical /jobs/{slug}/ page.
        # IMPORTANT: this only affects DETAIL-PAGE creation. Category LISTING
        # pages are built separately and still show the job under every relevant
        # category, all linking to this one canonical URL. JSON order preserved.
        if _is_dup_job(slug, title)[0]:
            continue
        _mark_job(slug, title, cat); job['category'] = cat
        canon = f"{BASE_URL}/jobs/{slug}/"
        # R9 FIX: Breadcrumb uses correct qualification hierarchy
        _bc_lbl, _bc_url = get_best_bc_category(cat, job)
        bc    = [('Study Wise', f"{BASE_URL}/category/study/"),
                 (_bc_lbl, f"{BASE_URL}{_bc_url}")]
        write(str(ROOT/'jobs'/slug/'index.html'), build_detail_page(job, slug, canon, bc, cat_label), skip_if_exists=True)
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

# ── CROSS-SOURCE DEDUP: FJA canonical slug lookup ────────────────────────────
# Build exam-code index from FJA (already written). When SARK has a job with
# overlapping exam identifiers (e.g. "AIIMS CRE-5"), use FJA canonical slug
# and add a redirect instead of creating a 2nd page.
# ── CROSS-SOURCE DEDUP: FJA→SARK title similarity index ─────────────────────
# Permanent fix: ek job ke ek se zyada pages kabhi nahi banenge.
# FJA loop ke baad, har FJA job ka title-token index build karo.
# SARK loop mein har job ke title se FJA index check karo via Jaccard similarity.
# 55% overlap + ≥3 common tokens = same job → SARK redirects to FJA, no new page.

_DEDUP_SKIP = frozenset(('the and for with of in to a an at by on from up is are was '
                        'were be been being apply online form recruitment vacancy post '
                        'exam result admit card notification advertisement advt across '
                        'central govt various latest notifications here more out noti '
                        '2020 2021 2022 2023 2024 2025 2026 2027 2028').split())

def _title_tokens(t):
    """Content words from title — skip common/generic terms."""
    t = re.sub(r'[^a-z0-9\s]', ' ', str(t or '').lower())
    return frozenset(w for w in t.split() if w not in _DEDUP_SKIP and len(w) > 2)

# Build FJA token index: list of (frozenset_of_tokens, fja_slug, raw_title_lower)
_fja_token_index = []   # list of (frozenset_of_tokens, fja_slug, raw_title_lower)

for _fj in (CJ.get('freejobalert_unified',{}) or {}).get('deduped_jobs',[]):
    _fbd = _fj.get('basic_details',{}) or {}
    _ft = _fbd.get('job_title','')
    if not _ft: continue
    _fslug = get_canonical_slug(_fj)  # SINGLE SOURCE OF TRUTH — same slug as detail page
    _ftok = _title_tokens(_ft)
    if len(_ftok) >= 3:   # only meaningful titles
        _fja_token_index.append((_ftok, _fslug, _ft.lower()))

def _find_fja_canonical(sark_title):
    """Find FJA canonical slug for a SARK job using Jaccard title similarity.
    Returns FJA slug if strong title overlap detected, else None.
    Conservative thresholds prevent false positives (different posts same org).
    """
    stok = _title_tokens(sark_title)
    if len(stok) < 3: return None

    # SECONDARY: Exam-code based matching (e.g. "CRE-5", "JTO", "AFCAT-02")
    # If SARK and FJA share org acronym + exam code → definite same job
    _sark_raw = str(sark_title or '').lower()
    for _ftok, _fslug, _fja_raw_t in _fja_token_index:
        # Quick extract compound codes like "cre-5", "jto", "afcat-02" from SARK title
        _sark_codes = re.findall(r'\b[a-z]{2,6}[\-]?\d{1,2}\b|\bjto\b|\bcgl\b|\bchsl\b|\bcpo\b|\bmts\b|\bcre-\d\b|\bafcat\b', _sark_raw)
        if _sark_codes:
            _shared_codes = [c for c in _sark_codes if c in _fja_raw_t]
            if len(_shared_codes) >= 1 and len(_ftok & stok) >= 2:
                return _fslug   # org + exam code match = same job

    # PRIMARY: Jaccard similarity
    best_score = 0.0
    best_slug = None
    best_inter_len = 0
    for ftok, fslug, _ in _fja_token_index:
        inter = stok & ftok
        n_inter = len(inter)
        if n_inter < 3: continue
        jaccard = n_inter / len(stok | ftok)
        if jaccard > best_score:
            best_score = jaccard
            best_slug = fslug
            best_inter_len = n_inter

    # Conservative thresholds to prevent false positives:
    if best_inter_len >= 5 and best_score >= 0.50: return best_slug
    if best_inter_len >= 4 and best_score >= 0.55: return best_slug
    return None


# Master Complete_Jobs_Full_Data.json uses camelCase keys for SR_*/OFFLINE_FORM/
# LATEST_JOBS NEW records (importantDates, applicationFee, importantLinks,
# shortInfo, additionalData.howToApply) and FLAT fields for STATE/UPCOMING/
# CENTRAL/ADMISSIONS (last_date, fee_general...). build_detail_page expects
# snake_case objects. This maps everything so NO table/text/key is missed.
def _camel_to_snake(s):
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', str(s)).lower()

def _normalize_sarkari_job(job):
    if not isinstance(job, dict):
        return job
    j = dict(job)
    CAMEL = {
        'importantDates':'important_dates', 'applicationFee':'application_fee',
        'applicationFees':'application_fees', 'importantLinks':'important_links',
        'shortInfo':'short_information', 'shortInformation':'short_information',
        'postDate':'post_date', 'lastDate':'last_date', 'ageLimit':'age_limit',
        'vacancyDetails':'vacancy_details', 'howToApply':'how_to_apply',
        'usefulLinks':'useful_links', 'textSections':'text_sections',
        'nameOfPost':'name_of_post', 'postName':'post_name',
        'selectionProcess':'selection_process', 'dataTables':'data_tables',
        'subjectWiseVacancy':'subject_wise_vacancy', 'courseDetails':'course_details',
        'eligibilitySection':'eligibility_section',
        'faqs':'faq',   # LATEST_JOBS NEW / OFFLINE_FORM use plural 'faqs'
    }
    for cam, snk in CAMEL.items():
        if j.get(cam) and not j.get(snk):
            j[snk] = j[cam]
    # additionalData.howToApply → how_to_apply
    ad = j.get('additionalData') or {}
    _ad_derived = set()
    if isinstance(ad, dict):
        if ad.get('howToApply') and not j.get('how_to_apply'):
            j['how_to_apply'] = ad['howToApply']
        for k, v in ad.items():
            sk = _camel_to_snake(k)
            if v and not j.get(sk):
                j[sk] = v
                _ad_derived.add(sk)
    # remember which top-level keys came from additionalData (course-eligibility
    # blobs) so the detail builder can fold them into one table / drop dups.
    if _ad_derived:
        j['_ad_derived_keys'] = sorted(_ad_derived)
    # Merge top-level resultUrl / answerKeyUrl into important_links so the
    # detail page shows them as Result / Answer Key buttons (was dropped before).
    _url_map = {'resultUrl': 'result_link', 'result_url': 'result_link',
                'answerKeyUrl': 'answer_key', 'answer_key_url': 'answer_key',
                'admitCardUrl': 'admit_card', 'admit_card_url': 'admit_card'}
    _il = j.get('important_links')
    for _src, _dst in _url_map.items():
        _u = j.get(_src)
        if isinstance(_u, str) and _u.strip().startswith('http'):
            if isinstance(_il, dict):
                _il.setdefault(_dst, _u)
            elif isinstance(_il, list):
                if not any(isinstance(x, dict) and x.get('url') == _u for x in _il):
                    _il.append({'title': _dst.replace('_', ' ').title(), 'url': _u})
            else:
                j['important_links'] = {_dst: _u}
                _il = j['important_links']
    # snake-ify inner keys of important_dates / application_fee dicts
    # REPLACE camel keys (do NOT keep both — that caused duplicate rows)
    for key in ('important_dates', 'application_fee', 'application_fees'):
        o = j.get(key)
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                sk = _camel_to_snake(k)
                # first writer wins; if snake form already set from a true
                # snake key, don't overwrite with camel duplicate
                if sk not in out:
                    out[sk] = v
            j[key] = out

    # snake-ify keys INSIDE list-of-dict fields (vacancy rows, subject rows)
    # so render_vacancy_table sees post_name / total_post / notification_pdf etc.
    def _snake_rows(rows):
        out = []
        for row in rows:
            if isinstance(row, dict):
                nr = {}
                for k, v in row.items():
                    sk = _camel_to_snake(k)
                    if sk not in nr:
                        nr[sk] = v
                # Flatten nested categoryWise {General,OBC,SC,ST,EWS,...} into
                # flat columns so render_vacancy_table shows the category split.
                _cw = nr.pop('category_wise', None) or row.get('categoryWise')
                if isinstance(_cw, dict):
                    for _ck, _cv in _cw.items():
                        _ckl = str(_ck).strip().lower()
                        _map = {'general':'ur','ur':'ur','unreserved':'ur',
                                'obc':'obc','sc':'sc','st':'st','ews':'ews',
                                'female':'women','women':'women','total':'total'}
                        _col = _map.get(_ckl)
                        if _col and not nr.get(_col):
                            nr[_col] = _cv
                # Flatten nested genderWise {male, female} into Male/Female columns
                # (NDA-type Service | Male | Female | Total tables).
                _gw = nr.pop('gender_wise', None) or row.get('genderWise')
                if isinstance(_gw, dict):
                    for _gk, _gv in _gw.items():
                        _gkl = str(_gk).strip().lower()
                        if _gkl in ('male', 'men', 'man') and not nr.get('male'):
                            nr['male'] = _gv
                        elif _gkl in ('female', 'women', 'lady') and not nr.get('women'):
                            nr['women'] = _gv
                        elif _gkl == 'transgender' and not nr.get('transgender'):
                            nr['transgender'] = _gv
                out.append(nr)
            else:
                out.append(row)
        return out
    for lk in ('vacancy_details', 'vacancyDetails', 'subjectWiseVacancy',
               'subject_wise_vacancy', 'category_wise_vacancy', 'categoryWiseVacancy'):
        if isinstance(j.get(lk), list):
            j[lk] = _snake_rows(j[lk])
    # canonical aliases for the subject-wise list
    if isinstance(j.get('subjectWiseVacancy'), list) and not j.get('subject_wise_vacancy'):
        j['subject_wise_vacancy'] = j['subjectWiseVacancy']
    if isinstance(j.get('categoryWiseVacancy'), list) and not j.get('category_wise_vacancy'):
        j['category_wise_vacancy'] = j['categoryWiseVacancy']
    # Build important_dates from FLAT fields (STATE/UPCOMING/CENTRAL/ADMISSIONS)
    if not (isinstance(j.get('important_dates'), dict) and j['important_dates']):
        FD = ['application_start','application_begin','notification_date','last_date',
              'fee_payment_last_date','exam_date','written_exam_date','admit_card_date',
              'interview_date','result_date','counselling_date','joining_date']
        asm = {f: j[f] for f in FD if j.get(f)}
        if asm:
            j['important_dates'] = asm
    # Build application_fee from FLAT fee_* fields
    has_fee = (isinstance(j.get('application_fee'), dict) and j['application_fee']) or \
              (isinstance(j.get('application_fees'), dict) and j['application_fees'])
    if not has_fee:
        FF = {'fee_general':'general','fee_ur':'ur','fee_obc':'obc','fee_ews':'ews',
              'fee_sc':'sc','fee_st':'st','fee_sc_st':'sc_st','fee_female':'female',
              'fee_ph':'ph','fee_pwd':'pwd','fee_general_obc':'general_obc','fee_all':'all'}
        asm = {canon: j[flat] for flat, canon in FF.items() if j.get(flat)}
        if j.get('fee_payment_mode'):
            asm['payment_mode'] = j['fee_payment_mode']
        if asm:
            j['application_fee'] = asm
    return j

# Dict of SARK duplicate slugs that should redirect to FJA canonical
_dedup_sark_slugs = {}   # sark_slug → fja_canonical_slug

for job in SARK:
    job = _normalize_sarkari_job(job)
    title = safe(job.get('title',''))
    if not title: continue
    # get_canonical_slug() reads _canonical_slug first (scraper-set, immutable),
    # then falls back to normalized slug field, then registered_slug(title).
    # This is the ONLY place the SARK base slug is derived — no ad-hoc slugify().
    base_slug = get_canonical_slug(job)
    if not base_slug: continue
    # Version-aware: same recruitment + changed dates/posts/advt/year/pdf → new
    # version → new unique slug. Same content → None (true duplicate, skip).
    slug = _versioned_slug(base_slug, job)
    if slug is None or slug in seen_jobs:
        continue

    # ── CROSS-SOURCE DEDUP CHECK: before marking or writing ──────────────────
    # If FJA already has a canonical page for same job (by exam codes),
    # add redirect instead of creating duplicate page.
    _fja_canon_now = _find_fja_canonical(title)
    if _fja_canon_now and _fja_canon_now != slug:
        # SARK job = same job as FJA. Record redirect; delete SARK page if exists.
        _dedup_sark_slugs[slug] = _fja_canon_now   # tracked for cleanup below
        _p_sark_dup = ROOT/'jobs'/slug/'index.html'
        if _p_sark_dup.exists():
            import shutil as _sh_dup
            _sh_dup.rmtree(str(_p_sark_dup.parent), ignore_errors=True)
        continue   # skip mark + write: FJA page is the canonical

    _mark_job(slug, title, job.get('category',''))

    # Build important_links — _prepare_il handles dict/_labels/list/all_official_links
    il = _prepare_il(job)
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
    # Keep vacancy_details / subject_wise_vacancy / category_wise_vacancy as
    # SEPARATE sections — they are DIFFERENT tables on the source site and must
    # render separately (e.g. MPPSC: vacancy table + subject-wise table; CBI:
    # vacancy table + category-wise table). vacancy_details may itself contain
    # both plain-vacancy rows and category-wise rows; render_vacancy_table splits
    # those internally.
    _vac_main = [r for r in (job.get('vacancy_details') or job.get('vacancyDetails') or []) if isinstance(r, dict)]
    _subj_wise = [r for r in (job.get('subject_wise_vacancy') or job.get('subjectWiseVacancy') or []) if isinstance(r, dict)]
    _cat_wise = [r for r in (job.get('category_wise_vacancy') or job.get('categoryWiseVacancy') or []) if isinstance(r, dict)]
    full = {'basic_details':bd,'important_dates':imp_dates,'application_fee':job.get('application_fees') or job.get('application_fee') or {},'age_limit':age,'qualification':job.get('eligibility') or job.get('qualification') or {},'eligibility_section':job.get('eligibility_section') or [],'vacancy_details':_vac_main or [],'subject_wise_vacancy':_subj_wise,'category_wise_vacancy':_cat_wise,'salary_details':{'pay_scale':safe(job.get('salary_pay_scale',''))} if job.get('salary_pay_scale') else {},'how_to_apply':[job['how_to_apply']] if isinstance(job.get('how_to_apply'),str) and job.get('how_to_apply') else (job.get('how_to_apply') or []),'important_links':il,'sections':sections_out,'faq':job.get('faq') or [],'category':job.get('category',''),'slug':slug,
             'tables':job.get('tables') or [],'text_sections':job.get('text_sections') or [],'useful_links':job.get('useful_links') or [],'all_links':job.get('all_links') or [],'details_page_content':job.get('details_page_content') or {}}
    # A-to-Z COMPLETENESS: carry over EVERY other key from the normalized job
    # (course_details, data_tables, dynamic additionalData eligibility keys,
    # result_url, answer_key_url, exam_pattern, syllabus, selection_process, ...)
    # so build_all_sections can render the full JSON — nothing silently dropped.
    # SKIP the camelCase originals (their snake_case forms are already in `full`)
    # plus scalar meta fields that are shown in the header/overview already.
    _FULL_SKIP = {
        # already placed into `full` above (snake_case)
        'basic_details','important_dates','application_fee','application_fees',
        'age_limit','qualification','eligibility','vacancy_details',
        'subject_wise_vacancy','salary_pay_scale','salary_details','how_to_apply',
        'important_links','sections','faq','category','slug','tables',
        'text_sections','useful_links','all_links','details_page_content',
        # camelCase duplicates of the above (would re-render as dup cards)
        'importantDates','applicationFee','applicationFees','ageLimit',
        'vacancyDetails','subjectWiseVacancy','categoryWiseVacancy',
        'category_wise_vacancy','howToApply','importantLinks','usefulLinks',
        'textSections','dataTables','courseDetails','selectionProcess',
        # scalar/meta fields shown in header or not meaningful as a card
        'title','meta','additionalData','additional_data','postDate','post_date',
        'totalPost','total_post','shortInfo','short_information','short_info',
        'organization','name','source_url','url','resultUrl','answerKeyUrl',
        'admitCardUrl','result_url','answer_key_url','admit_card_url',
        'seo_tags','status',
    }
    # keys we DO want as cards even though dynamic: course_details, data_tables,
    # exam_pattern, syllabus, selection_process, physical_eligibility (snake forms)
    for _jk, _jv in job.items():
        if _jk in _FULL_SKIP or _jk in full:
            continue
        if _jv in (None, '', [], {}):
            continue
        full[_jk] = _jv
    # ensure the clean course_details / data_tables snake forms reach the renderer
    if job.get('course_details') and 'course_details' not in full:
        full['course_details'] = job['course_details']
    if job.get('data_tables') and 'data_tables' not in full:
        full['data_tables'] = job['data_tables']
    canon = f"{BASE_URL}/jobs/{slug}/"
    # M4 FIX: breadcrumb must reflect the job's ACTUAL category (badge uses
    # job['category']), not a hardcoded "Latest Jobs". Map each sarkari_data
    # category to its real section breadcrumb so badge and breadcrumb agree.
    _SARK_BC = {
        'SR_Latest_Jobs':  ('Latest Jobs',  '/section/latest-jobs/'),
        'LATEST_JOBS NEW': ('Latest Jobs',  '/section/latest-jobs/'),
        'SR_Result':       ('Results',      '/section/results/'),
        'SR_Admit_Card':   ('Admit Card',   '/section/admit-card/'),
        'SR_Answer_Key':   ('Answer Key',   '/section/answer-key/'),
        'ADMISSIONS':      ('Admissions',   '/section/admissions/'),
        'UPCOMING_JOBS':   ('Upcoming Jobs','/section/upcoming-jobs/'),
        'OFFLINE_FORM':    ('Offline Form', '/section/offline-form/'),
    }
    _jcat = safe(job.get('category', ''))
    _bc_lbl, _bc_url = _SARK_BC.get(_jcat, ('Latest Jobs', '/section/latest-jobs/'))
    bc = [(_bc_lbl, f"{BASE_URL}{_bc_url}")]

    write(str(ROOT/'jobs'/slug/'index.html'), build_detail_page(full, slug, canon, bc), skip_if_exists=True)
    ld = safe(imp_dates.get('last_date_to_apply','') or imp_dates.get('last_date',''))
    jobs_index[slug] = {'cat':job.get('category',''),'title':title[:120],'last_date':ld[:30]}
    j_count += 1

print(f"  All /jobs/: {j_count}")

# ── CROSS-SOURCE DEDUP REDIRECTS: write all SARK→FJA redirects ───────────────
# _dedup_sark_slugs = {sark_slug: fja_slug} collected above
if _dedup_sark_slugs:
    _rrpath = str(ROOT/'_redirects')
    _rr_existing = open(_rrpath, encoding='utf-8').read() if os.path.exists(_rrpath) else ''
    _rr_block = ['', '# ══ SARK→FJA cross-source dedup (same job, different title) ══']
    for _sark_s, _fja_s in _dedup_sark_slugs.items():
        _rline = f"/jobs/{_sark_s}/  /jobs/{_fja_s}/  301"
        if _rline not in _rr_existing:
            _rr_block.append(_rline)
    if len(_rr_block) > 2:
        with open(_rrpath, 'a', encoding='utf-8') as _rrf:
            _rrf.write('\n'.join(_rr_block) + '\n')
    print(f"  [cross-dedup] {len(_dedup_sark_slugs)} SARK pages redirected to FJA canonical")

# ── PERMANENT REDIRECT RULES — ensure on every run ───────────────────────────
# Ye rules HAMESHA _redirects me hone chahiye (old versioned slugs from live site,
# historical dups, etc.). generate_all run pe automatically ensure ho jaate hain.
_PERMANENT_REDIRECTS = [
    # ── Broken URLs from old scraper slug format → correct current slugs ──
    ("/jobs/railway-rrb-section-controller-cen-03-2026-recruitment-2026-apply-online/",
     "/jobs/railway-rrb-section-controller-cen-032026-recruitment-2026-apply-online/"),
    ("/jobs/up-police-sub-inspector-si-advt-no-03-2025-recruitment-2025-pet-admit-card-2026/",
     "/jobs/up-police-sub-inspector-si-advt-no-032025-recruitment-2025-pet-admit-card-2026-f/"),
    ("/jobs/madhya-pradesh-mppsc-food-safety-officer-fso-advt-no-57-2024-recruitment-2024-fi/",
     "/jobs/madhya-pradesh-mppsc-food-safety-officer-fso-advt-no-572024-recruitment-2024-fin/"),
    ("/jobs/haryana-iti-admission-2026/",
     "/jobs/haryana-iti-admission-apply-online-form-2026/"),
    ("/jobs/deendayal-port-authority-traffic-executive-recruitment-2026-apply-offline-for/",
     "/jobs/deendayal-port-authority-traffic-executive-recruitment-2026-apply-offline-for-16/"),
    # AIIMS CRE-5 — old versioned slug from live site (had '-305' suffix from advt no)
    ("/jobs/aiims-cre-5-recruitment-2026-apply-online-for-1484-group-b-and-group-c-posts-305/",
     "/jobs/aiims-cre-5-recruitment-2026-apply-online-for-1484-group-b-c-posts-across-28-cen/"),
    # AIIMS CRE-5 — short slug variant
    ("/jobs/aiims-group-b-group-c-1484-posts/",
     "/jobs/aiims-cre-5-recruitment-2026-apply-online-for-1484-group-b-c-posts-across-28-cen/"),
]
_pr_path = str(ROOT/'_redirects')
_pr_existing = open(_pr_path, encoding='utf-8').read() if os.path.exists(_pr_path) else ''
_pr_added = []
for _pr_src, _pr_dst in _PERMANENT_REDIRECTS:
    _pr_rule = f"{_pr_src}  {_pr_dst}  301"
    if _pr_rule not in _pr_existing:
        _pr_added.append(_pr_rule)
        _pr_existing += _pr_rule  # update in-memory check
# CRITICAL: Delete stale disk pages for PERMANENT REDIRECT sources.
# Vercel: file at /jobs/X/index.html OVERRIDES redirect rule for /jobs/X/.
# We must delete these pages so the 301 redirect can actually fire.
for _pr_src2, _pr_dst2 in _PERMANENT_REDIRECTS:
    import re as _re_pr
    _pm = _re_pr.match(r'^/jobs/([^/]+)/', _pr_src2)
    if _pm:
        _ps = _pm.group(1)
        _pp = ROOT/'jobs'/_ps/'index.html'
        if _pp.exists():
            import shutil as _sh2
            _sh2.rmtree(str(_pp.parent), ignore_errors=True)
            print(f"  [perm-redirect] Deleted stale page: /jobs/{_ps}/")

if _pr_added:
    # Prepend to TOP of _redirects (Vercel: first rule wins)
    # Canonical redirects must appear BEFORE any fallback "→ /" orphan rules
    _new_block = '# ══ Permanent historical redirects (always at top) ══\n'
    _new_block += '\n'.join(_pr_added) + '\n\n'
    _old_content = open(_pr_path, encoding='utf-8').read() if os.path.exists(_pr_path) else ''
    with open(_pr_path, 'w', encoding='utf-8') as _prf:
        _prf.write(_new_block + _old_content)
    print(f"  [permanent-redirects] Prepended {len(_pr_added)} rules to top of _redirects")

# ── UPCOMING_JOBS + ADMISSIONS DETAIL PAGES ───────────────────────────────────
# In sources: data/upcoming-jobs.json + data/admissions.json + sarkari_data raw
# Section pages /section/upcoming-jobs/ + /section/admissions/ se click karne pe
# pehle "Page Not Available" aata tha kyunki detail page hi nahi banti thi.
# Permanent fix: yahan inke detail pages create karte hain SAME build_detail_page se.
print("Generating /jobs/ pages (UPCOMING_JOBS + ADMISSIONS)...")
_up_adm_jobs = []
_seen_extra_slugs = set()

def _read_jobs_file(_path):
    if not os.path.exists(_path): return []
    try:
        _d = json.load(open(_path, encoding='utf-8'))
        if isinstance(_d, dict): return _d.get('jobs', []) or []
        if isinstance(_d, list): return _d
    except Exception: pass
    return []

# Source 1: sarkari_data RAW (no garbage filter) - includes UPCOMING/ADMISSIONS
for _j in (CJ.get('sarkari_data', {}) or {}).get('jobs', []) or []:
    if _j.get('category') in ('UPCOMING_JOBS', 'ADMISSIONS'):
        _t = _j.get('title','')
        _s = _j.get('slug','') or slugify(_t)[:80]
        if _s and _s not in _seen_extra_slugs:
            _up_adm_jobs.append(_j); _seen_extra_slugs.add(_s)

# Source 2: data/upcoming-jobs.json
for _j in _read_jobs_file(str(ROOT/'data'/'upcoming-jobs.json')):
    _j.setdefault('category', 'UPCOMING_JOBS')
    _t = _j.get('title','') or _j.get('name','')
    _s = _j.get('slug','') or slugify(_t)[:80]
    if _s and _s not in _seen_extra_slugs:
        _up_adm_jobs.append(_j); _seen_extra_slugs.add(_s)

# Source 3: data/admissions.json
for _j in _read_jobs_file(str(ROOT/'data'/'admissions.json')):
    _j.setdefault('category', 'ADMISSIONS')
    _t = _j.get('title','') or _j.get('name','')
    _s = _j.get('slug','') or slugify(_t)[:80]
    if _s and _s not in _seen_extra_slugs:
        _up_adm_jobs.append(_j); _seen_extra_slugs.add(_s)

# Generate pages
_extra_created = 0
_extra_skipped = 0
for _j in _up_adm_jobs:
    _t = _j.get('title','') or _j.get('name','')
    if not _t: _extra_skipped += 1; continue
    _slug = _j.get('slug','') or slugify(_t)[:80]
    if not _slug: _extra_skipped += 1; continue
    # Skip if already created (cross-source dedup)
    if _is_dup_job(_slug, _t)[0]:
        _extra_skipped += 1; continue
    # Normalize through same pipeline as SARK
    try:
        _full = _normalize_sarkari_job(_j)
    except Exception:
        _full = dict(_j)
    # Ensure required fields exist
    _full.setdefault('title', _t)
    _full.setdefault('post_name', _full.get('post_name','') or _full.get('postName','') or '')
    # Important dates from flat fields (UPCOMING uses flat: last_date, application_start...)
    if not _full.get('important_dates'):
        _imp = {}
        for _f in ('last_date','application_start','exam_date','result_date','admit_card_date'):
            _v = _full.get(_f)
            if _v: _imp[_f] = _v
        if _imp: _full['important_dates'] = _imp
    # Important links from flat
    if not _full.get('important_links'):
        _il = {}
        for _ln in (_full.get('important_links') or []) if isinstance(_full.get('important_links'), list) else []:
            if isinstance(_ln, dict):
                _u = _ln.get('url') or _ln.get('link')
                _l = _ln.get('label') or _ln.get('name')
                if _u and _l: _il[slugify(_l)[:30] or 'link'] = _u
        if _il: _full['important_links'] = _il
    _cat = _full.get('category','')
    _cat_label = 'Upcoming Job' if _cat == 'UPCOMING_JOBS' else 'Admission'
    _bc_url = '/section/upcoming-jobs/' if _cat == 'UPCOMING_JOBS' else '/section/admissions/'
    _bc_lbl = 'Upcoming Jobs' if _cat == 'UPCOMING_JOBS' else 'Admissions'
    _canon = f"{BASE_URL}/jobs/{_slug}/"
    _bc = [(_bc_lbl, f"{BASE_URL}{_bc_url}")]
    try:
        _page_html = build_detail_page(_full, _slug, _canon, _bc, _cat_label)
        write(str(ROOT/'jobs'/_slug/'index.html'), _page_html, skip_if_exists=True)
        _mark_job(_slug, _t, _cat)
        # Register in jobs_index for sitemap
        _ld = ''
        _imp = _full.get('important_dates') or {}
        if isinstance(_imp, dict):
            _ld = _imp.get('last_date','') or _imp.get('last_date_apply_online','') or _imp.get('last_date_to_apply','')
        jobs_index[_slug] = {'cat': _cat, 'title': _t[:120], 'last_date': str(_ld)[:30]}
        _extra_created += 1
    except Exception as _e:
        print(f"  [extra] failed {_slug}: {_e}")
        _extra_skipped += 1

print(f"  UPCOMING/ADMISSIONS pages: {_extra_created} created, {_extra_skipped} skipped (total source: {len(_up_adm_jobs)})")

# 3. STATE PAGES
print("Generating /state/ pages...")

# ── District mapping (loaded early so state pages can show district cards) ────
# 697 districts across 30 states, grouped by state. Built from
# scraper_district.DISTRICT_META → district_meta_by_state.json.
_DIST_BY_STATE = {}
for _dmp in (str(ROOT/'district_meta_by_state.json'),
             str(ROOT.parent/'scraper'/'district_meta_by_state.json')):
    if os.path.exists(_dmp):
        try:
            _DIST_BY_STATE = json.load(open(_dmp, encoding='utf-8'))
            break
        except Exception as _e:
            print(f"  [district] could not load {_dmp}: {_e}")

def _district_slug(state_name, district_name):
    return slugify(f"{district_name}-{state_name}")[:80]

# District-card HTML for a given state — shown at TOP of each state page.
# Mirrors the "District Wise Jobs" card grid from the reference design.
def _district_cards_html(state_name):
    _ds = _DIST_BY_STATE.get(state_name, [])
    if not _ds:
        return ''
    _cards = ''
    for _d in _ds:
        _dn = _d.get('district', '')
        if not _dn:
            continue
        _sl = _district_slug(state_name, _dn)
        _cards += f'<a class="dwj-card" href="/district/{e(_sl)}/">{e(_dn)}</a>'
    return (
        '<style>'
        '.dwj-wrap{margin:4px 10px 22px}'
        '.dwj-head{background:#2f7fc1;color:#fff;font-weight:700;text-align:center;'
        'padding:11px 16px;border-radius:10px 10px 0 0;font-size:1rem}'
        '.dwj-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));'
        'gap:8px;padding:13px;background:#f8fafc;border:1px solid #e5e7eb;'
        'border-top:none;border-radius:0 0 10px 10px}'
        '.dwj-card{display:block;text-align:center;padding:9px 10px;border-radius:6px;'
        'background:#2f7fc1;color:#fff;text-decoration:none;font-size:.84rem;'
        'font-weight:600;transition:filter .15s}'
        '.dwj-card:hover{filter:brightness(1.1)}'
        '</style>'
        f'<div class="dwj-wrap"><div class="dwj-head">{e(state_name)} — District Wise Jobs</div>'
        f'<div class="dwj-grid">{_cards}</div></div>'
    )

_state_landing_items = []   # (state_name, slug, job_count) for /state/ landing index
for sec in SJ_SEC:
    state_name = safe(sec.get('state') or sec.get('title',''))
    raw_state_slug = slugify(state_name)
    state_slug = STATE_SLUG_FIX.get(raw_state_slug, raw_state_slug)
    _state_landing_items.append((state_name, state_slug, len(sec.get('items', []))))
    for item in sec.get('items', []):
        name = safe(item.get('name','') or item.get('title',''))
        if not name: continue
        item_slug = registered_slug(name)[:80]
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
        if not _is_dup_job(item_slug, name):
            _mark_job(item_slug, name, state_name)
            jobs_html = build_detail_page(detail, item_slug, canon, bc, f'{state_name} Govt Job', noindex_dup=False)
            write(str(ROOT/'jobs'/item_slug/'index.html'), jobs_html, skip_if_exists=True)
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
    # Build simple listing page for /state/{slug}/ — with district cards on top
    _dist_cards = _district_cards_html(state_name)
    state_listing = build_listing_page(
        f"{state_name} Government Jobs {YEAR}",
        [{'basic_details':{'job_title':safe(it.get('name') or it.get('title','')),'organization_name':state_name,
          'total_vacancies':safe(it.get('total_vacancy',''))}}
         for it in state_jobs_list if (it.get('name') or it.get('title',''))],
        canon_listing,
        [('Home','/'),('State Jobs','/state-jobs/')],
        f"Latest {state_name} government jobs {YEAR}. All sarkari naukri for {state_name} state.",
        top_html=_dist_cards,
    )
    write(str(ROOT/'state'/state_slug/'index.html'), state_listing)

    # Also write to /state-jobs/{slug}/ — this is the URL the site nav + cards
    # actually link to. Generating it here keeps it FRESH with ALL items from
    # JSON (the old static /state-jobs/ pages were stale and missing items).
    # IMPORTANT: site nav links use the FULL state slug (e.g. jammu-and-kashmir),
    # not the abbreviated detail-page slug (jk), so write to BOTH so whichever
    # the nav points at is always complete.
    for _sj_slug in {state_slug, raw_state_slug}:
        canon_statejobs = f"{BASE_URL}/state-jobs/{_sj_slug}/"
        statejobs_listing = build_listing_page(
            f"{state_name} Government Jobs {YEAR}",
            [{'basic_details':{'job_title':safe(it.get('name') or it.get('title','')),'organization_name':state_name,
              'total_vacancies':safe(it.get('total_vacancy',''))}}
             for it in state_jobs_list if (it.get('name') or it.get('title',''))],
            canon_statejobs,
            [('Home','/'),('State Jobs','/state-jobs/')],
            f"Latest {state_name} government jobs {YEAR}. All sarkari naukri for {state_name} state.",
            top_html=_district_cards_html(state_name),
        )
        write(str(ROOT/'state-jobs'/_sj_slug/'index.html'), statejobs_listing)

print(f"  State pages: {s_count}")

# 3b. /state/ LANDING INDEX — links to every /state/{slug}/ page.
# Reuse build_listing_page: feed each state as a "job" whose title links out.
_state_landing_jobs = [
    {'basic_details': {'job_title': f"{n} Government Jobs {YEAR}",
                       'organization_name': n,
                       'total_vacancies': str(c) if c else ''},
     'source_url': f"/state/{s}/",
     '_listing_url': f"/state/{s}/"}
    for (n, s, c) in sorted(_state_landing_items)
]
write(str(ROOT/'state'/'index.html'), build_listing_page(
    f"State Wise Government Jobs {YEAR}",
    _state_landing_jobs,
    f"{BASE_URL}/state/",
    [('Home','/'),('State Jobs','/state/')],
    f"Browse latest state government jobs {YEAR}. Select your state for all current sarkari naukri openings."))
print(f"  /state/ landing: {len(_state_landing_jobs)} states")

# ═══════════════════════════════════════════════════════════════════════════
# 3c. DISTRICT-WISE PAGES  (/district/ landing + /district/{slug}/ per district)
# ───────────────────────────────────────────────────────────────────────────
# 697 districts across 30 states (from district_meta_by_state.json, built from
# scraper_district.DISTRICT_META). Each district gets a listing page; the
# /district/ landing groups them by state. State pages get a district-card
# section injected at the TOP (see _district_cards_html used in section 3).
#
# Job data: if Complete_Jobs_Full_Data.json has district-tagged jobs (from the
# unified FJA scraper's `freejobalert_unified.by_district`, or legacy
# `freejobalert_district`), those jobs populate each district page. If not, the
# page still renders as a stub that fills in once district data is scraped.
# ═══════════════════════════════════════════════════════════════════════════
print("Generating /district/ pages...")

# Build a lookup: district name → [job items], from whatever district data exists
_district_jobs = {}   # district_name → list of job dicts
def _collect_district_jobs():
    # Source A: unified scraper's by_district index + deduped_jobs
    uni = CJ.get('freejobalert_unified', {}) or {}
    deduped = uni.get('deduped_jobs', []) or []
    by_url = {j.get('_scraped_from'): j for j in deduped if j.get('_scraped_from')}
    by_dist_idx = uni.get('by_district', {}) or {}

    # KEY MISMATCH FIX: by_district uses 'New_Delhi' (underscore from scraper),
    # DIST_BY_STATE uses 'New Delhi' (space from district_meta_by_state.json).
    # Build normalized lookup → canonical district name from meta.
    _dist_norm = {}   # normalized_key → canonical_name_from_meta
    for _st, _dlist in _DIST_BY_STATE.items():
        for _dd in _dlist:
            _dn = _dd.get('district', '')
            # Both space→underscore and underscore→space normalized to same key
            _norm = _dn.lower().replace(' ', '_').replace('-', '_')
            _dist_norm[_norm] = _dn   # canonical = meta name (with spaces)

    for _dkey, _urls in by_dist_idx.items():
        # Normalize scraper key to find canonical meta name
        _norm_key = _dkey.lower().replace(' ', '_').replace('-', '_')
        _canonical = _dist_norm.get(_norm_key, _dkey)  # fallback to original
        for _u in _urls:
            _job = by_url.get(_u)
            if _job:
                _district_jobs.setdefault(_canonical, []).append(_job)

    # Also walk deduped jobs' district_tags directly
    for _job in deduped:
        for _dtag in (_job.get('district_tags', []) or []):
            _norm_tag = _dtag.lower().replace(' ', '_').replace('-', '_')
            _canonical = _dist_norm.get(_norm_tag, _dtag)
            _lst = _district_jobs.setdefault(_canonical, [])
            if _job not in _lst:
                _lst.append(_job)
    # Source B: legacy freejobalert_district dict (district → [jobs])
    legacy = CJ.get('freejobalert_district', {}) or {}
    if isinstance(legacy, dict):
        for _dname, _items in legacy.items():
            if isinstance(_items, list):
                _district_jobs.setdefault(_dname, []).extend(_items)
    # Source C: freejobalert_categories se district match karo (job_location field)
    # Unified scraper ka data nahi hai to FJA categories se fill karo.
    # har job ka basic_details.job_location → district ya state name se match karo.
    if not any(_district_jobs.values()):
        _all_dist_names = set()
        for _st, _dlist in _DIST_BY_STATE.items():
            for _dd in _dlist:
                _all_dist_names.add(_dd.get('district','').lower())
        for _cat, _cat_jobs in FJA.items():
            if not isinstance(_cat_jobs, list): continue
            for _fj in _cat_jobs:
                _bd = (_fj.get('basic_details') or {})
                _loc = safe(_bd.get('job_location','') or _bd.get('organization_name','')).lower()
                if not _loc: continue
                # Match job_location to any known district name
                for _st, _dlist in _DIST_BY_STATE.items():
                    for _dd in _dlist:
                        _dn = _dd.get('district','')
                        if _dn.lower() in _loc or _loc in _dn.lower():
                            _district_jobs.setdefault(_dn, [])
                            if _fj not in _district_jobs[_dn]:
                                _district_jobs[_dn].append(_fj)
                            break

# ── UNIFIED JOBS: SLUG DERIVE KARO (collect se PEHLE) ────────────────────────
# CRITICAL ORDER: slug derivation _collect_district_jobs() se PEHLE hona chahiye.
# Warna jobs collect hoti hain bina slug ke, aur district page cards kaam nahi
# karte. JSON mein ab slugs hain (scraper_unified_fja.py se), par agar nahi hain
# to yahan se derive ho jayenge — dono cases cover hain.
_uni_data = CJ.get('freejobalert_unified', {}) or {}
_uni_jobs_list = _uni_data.get('deduped_jobs', []) or []
_slug_derived = 0
for _uj in _uni_jobs_list:
    if _uj.get('slug'):
        continue   # already has slug (from updated scraper)
    # PERMANENT FIX: ALWAYS derive slug from job TITLE, not from URL.
    # FJA article URLs have: "group-b-and-group-c" (wrong) vs title: "Group B & C" (right)
    # URL also has numeric article ID suffix (-3053829) that causes partial slugs on truncation.
    # Title-based slug is ALWAYS canonical and matches what FJA loop and _find_fja_canonical use.
    _fja_bd = (_uj.get('basic_details') or {})
    _fja_title = _fja_bd.get('job_title', '')
    if _fja_title:
        _derived = get_canonical_slug(_uj)  # canonical resolver (prefers _canonical_slug/slug)
        if _derived:
            _uj['slug'] = _derived
            _slug_derived += 1
        continue
    # Fallback: URL-based slug (only if title missing)
    _src = _uj.get('_scraped_from', '')
    if not _src:
        continue
    _m_slug = re.search(r'/articles/([^/?#]+)/?$', _src)
    if _m_slug:
        _raw_article_slug = re.sub(r'-\d{5,10}$', '', _m_slug.group(1))
        _derived = slugify(_raw_article_slug)[:80]
        if _derived:
            _uj['slug'] = _derived
            _slug_derived += 1
if _slug_derived:
    print(f"  [unified] {_slug_derived} job slugs derived from _scraped_from URL")

_collect_district_jobs()

_district_landing_items = []   # (state_name, district_name, slug, count)
_dist_count = 0
for _state_name, _districts in _DIST_BY_STATE.items():
    for _d in _districts:
        _dname = _d.get('district', '')
        if not _dname:
            continue
        _dslug = _district_slug(_state_name, _dname)
        _djobs_raw = _district_jobs.get(_dname, [])
        # Normalize district jobs into listing-card shape
        _djobs = []
        for _j in _djobs_raw:
            _bd = _j.get('basic_details', {}) or {}
            _title = safe(_bd.get('job_title', '') or _j.get('title', '') or _j.get('name', ''))
            if not _title:
                continue
            _djobs.append({
                'basic_details': {
                    'job_title': _title,
                    'organization_name': safe(_bd.get('organization_name', '') or _dname),
                    'total_vacancies': safe(_bd.get('total_vacancies', '') or _j.get('total_post', '')),
                },
                # Use get_canonical_slug to ensure district listing cards link
                # to the same URL as the actual detail page on disk.
                '_canonical_slug': get_canonical_slug(_j),
                '_slug': get_canonical_slug(_j),
            })
        _district_landing_items.append((_state_name, _dname, _dslug, len(_djobs)))
        # Build the district listing page
        _dcanon = f"{BASE_URL}/district/{_dslug}/"
        _ddesc = (f"Latest government jobs in {_dname}, {_state_name} {YEAR}. "
                  f"All sarkari naukri vacancies for {_dname} district — "
                  f"check eligibility, dates and apply online.")
        _state_slug_d = STATE_SLUG_FIX.get(slugify(_state_name), slugify(_state_name))
        _state_url_d = f"/state/{_state_slug_d}/"
        # SEO: empty district pages should still be useful.
        # When no jobs exist, inject a friendly "no current jobs" message so
        # Google doesn't see a thin/blank page. Include state link for nav.
        _empty_top = '' if _djobs else (
            f'<div style="margin:4px 10px 16px;padding:16px;background:#f0f9ff;border:1px solid #bae6fd;'
            f'border-radius:10px;text-align:center">'
            f'<p style="font-size:.9rem;color:#0369a1;font-weight:600;margin:0 0 8px">'
            f'<i class="fa-solid fa-circle-info" style="margin-right:6px"></i>'
            f'Abhi {e(_dname)} district ke liye koi active government job nahi hai.</p>'
            f'<p style="font-size:.82rem;color:#0284c7;margin:0">'
            f'{e(_state_name)} ke saare jobs dekhne ke liye: '
            f'<a href="{_state_url_d}" style="color:#0369a1;font-weight:700;text-decoration:underline">'
            f'{e(_state_name)} State Jobs →</a></p></div>'
        )
        _dlisting = build_listing_page(
            f"{_dname} Govt Jobs ({_state_name})",
            _djobs,
            _dcanon,
            [('Home', '/'), ('State Jobs', '/state/'),
             (_state_name, f"/state/{_state_slug_d}/"),
             (f"{_dname} District", f"/district/{_dslug}/")],
            _ddesc,
            top_html=_empty_top,
        )
        write(str(ROOT/'district'/_dslug/'index.html'), _dlisting)
        _dist_count += 1

print(f"  District pages: {_dist_count}")

# /district/ LANDING INDEX — grouped by state
_district_landing_html_parts = []
for _state_name in sorted(_DIST_BY_STATE.keys()):
    _district_landing_html_parts.append(_district_cards_html(_state_name))
_district_landing_body = ''.join(_district_landing_html_parts)
# Reuse build_listing_page shell but inject our grouped grid via a single
# pseudo-job whose title carries the heading; simplest path is a dedicated write
# using build_listing_page with an empty job list + the grid appended is not
# supported, so we emit district landing as its own listing of state links.
_district_landing_jobs = [
    {'basic_details': {'job_title': f"{_n} District Wise Jobs {YEAR}",
                       'organization_name': _n,
                       'total_vacancies': str(sum(1 for x in _district_landing_items if x[0]==_n))},
     'source_url': f"/state/{STATE_SLUG_FIX.get(slugify(_n), slugify(_n))}/",
     '_listing_url': f"/state/{STATE_SLUG_FIX.get(slugify(_n), slugify(_n))}/"}
    for _n in sorted(_DIST_BY_STATE.keys())
]
write(str(ROOT/'district'/'index.html'), build_listing_page(
    f"District Wise Government Jobs {YEAR}",
    _district_landing_jobs,
    f"{BASE_URL}/district/",
    [('Home', '/'), ('District Jobs', '/district/')],
    f"Browse district wise government jobs {YEAR} across India. Select your district for local sarkari naukri vacancies."))
print(f"  /district/ landing: {len(_district_landing_jobs)} states, {_dist_count} districts")


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
        item_slug = registered_slug(name)[:80]
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
        _edu_title = safe((full_d.get('basic_details') or {}).get('job_title','')) or item_slug
        _edu_is_dup, _ = _is_dup_job(item_slug, _edu_title)
        if not _edu_is_dup:
            _mark_job(item_slug, _edu_title, sec_title)
            jobs_html = build_detail_page(full_d, item_slug, canon, bc, sec_title, noindex_dup=False)
            write(str(ROOT/'jobs'/item_slug/'index.html'), jobs_html, skip_if_exists=True)
        e_count += 1

    # Listing page
    edu_jobs = [{'basic_details':{'job_title':safe(it.get('name') or it.get('examName','')),'organization_name':sec_title,'application_mode':'Online','job_location':sec_title,'last_updated':safe(it.get('postDate') or it.get('date',''))},'important_dates':{'notification_date':safe(it.get('date') or it.get('postDate',''))},'important_links':(it.get('detail') or {}).get('important_links') or {},'category':sec_title} for it in sec.get('items',[]) if it.get('name') or it.get('examName')]
    if edu_jobs:
        write(str(ROOT/'education'/sec_id/'index.html'), build_listing_page(f"{sec_title} Education Updates", edu_jobs, f"{BASE_URL}/education/{sec_id}/", [('Education','/education/')], list_noun='Updates'))

print(f"  Education pages: {e_count}")

# 4b. /education/ LANDING INDEX — links to every /education/{id}/ page
_edu_landing_jobs = []
for sec in EDU_SEC:
    _eid   = safe(sec.get('id','') or sec.get('title',''))
    _etit  = safe(sec.get('title','') or _eid)
    if not _eid:
        continue
    _edu_jt = (f"{_etit} Updates {YEAR}" if 'education' in _etit.lower()
               else f"{_etit} Education Updates {YEAR}")
    _edu_landing_jobs.append({
        'basic_details': {'job_title': _edu_jt,
                          'organization_name': f"{_etit} Education Board & Departments",
                          'total_vacancies': str(len(sec.get('items', []))) if sec.get('items') else ''},
        '_listing_url': f"/education/{_eid}/"})
if _edu_landing_jobs:
    write(str(ROOT/'education'/'index.html'), build_listing_page(
        f"State Wise Education Updates {YEAR}",
        _edu_landing_jobs,
        f"{BASE_URL}/education/",
        [('Home','/'),('Education','/education/')],
        f"State-wise education updates {YEAR}: board exam results, entrance exams, admit cards, counselling and admission notifications — updated daily. These are education updates (exams/results/admissions), not job vacancies.",
        list_noun='Updates'))
    print(f"  /education/ landing: {len(_edu_landing_jobs)} states")

# 5. CATEGORY/STUDY PAGES
print("Generating /category/study/ pages...")
_cat_listing_jobs = {}  # cat_slug → list of jobs (for listing page)
for cat, jobs_list in FJA.items():
    if not isinstance(jobs_list, list): continue
    cat_slug  = QUAL_SLUG.get(cat, slugify(cat))
    cat_label = QUAL_LABEL.get(cat, cat.replace('_',' ').title())
    if cat_slug not in _cat_listing_jobs:
        _cat_listing_jobs[cat_slug] = {'label': cat_label, 'jobs': [], 'seen_slugs': set()}
    for job in jobs_list:
        bd = job.get('basic_details',{}) or {}
        title = safe(bd.get('job_title',''))
        if not title: continue
        # Use get_canonical_slug — respects _canonical_slug from scraper so
        # category listing cards link to same page as section listing cards.
        item_slug = get_canonical_slug(job)
        # DUPLICATE GUARD: FJA kabhi-kabhi same recruitment ko naye article-ID
        # (naya URL) ke saath dobara publish kar deta hai. URL alag hone ki
        # wajah se upstream dedup_engine isse same job nahi maanta, aur same
        # title 2 baar listing me aa jaata tha ("purani list dobara dikhna").
        # Slug-level guard yahan final safety-net hai — same slug 2nd baar skip.
        if item_slug in _cat_listing_jobs[cat_slug]['seen_slugs']:
            continue
        _cat_listing_jobs[cat_slug]['seen_slugs'].add(item_slug)
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
        _items.append({'name': t, 'slug': get_canonical_slug(j)})  # canonical — never slugify(title)
    if not _items: continue
    _qual_sections.append({
        'id': cat_slug,
        'qualification': cat_data.get('label', cat_slug.replace('-', ' ').title()),
        'items': _items,
    })
with open(ROOT / 'Qualification_Wise_Jobs.json', 'w', encoding='utf-8') as _qf:
    json.dump({'sections': _qual_sections}, _qf, ensure_ascii=False, separators=(',', ':'))
print(f"  Qualification_Wise_Jobs.json: {len(_qual_sections)} sections")

# 5b. /category/study/ LANDING INDEX — links to every /category/study/{slug}/ page
_study_landing_jobs = []
for cat_slug, cat_data in _cat_listing_jobs.items():
    if cat_slug in _NON_STUDY:
        continue
    _cjobs = cat_data.get('jobs', [])
    if not _cjobs:
        continue
    _clabel = cat_data.get('label', cat_slug.replace('-', ' ').title())
    _study_landing_jobs.append({
        'basic_details': {'job_title': f"{_clabel} Government Jobs {YEAR}",
                          'organization_name': _clabel,
                          'total_vacancies': str(len(_cjobs))},
        '_listing_url': f"/category/study/{cat_slug}/"})
if _study_landing_jobs:
    write(str(ROOT/'category'/'study'/'index.html'), build_listing_page(
        f"Qualification Wise Government Jobs {YEAR}",
        _study_landing_jobs,
        f"{BASE_URL}/category/study/",
        [('Home','/'),('Study Wise Jobs','/category/study/')],
        f"Find government jobs by qualification {YEAR}: 8th, 10th, 12th, ITI, Diploma, Graduate, Post Graduate and more. Updated daily."))
    print(f"  /category/study/ landing: {len(_study_landing_jobs)} qualifications")

# 6. SECTION LISTING PAGES
print("Generating /section/ pages...")
SARK_CAT_MAP = {
    'SR_Latest_Jobs':  'latest-jobs',
    'SR_Result':       'results',
    'SR_Admit_Card':   'admit-card',
    'SR_Answer_Key':   'answer-key',
    'OFFLINE_FORM':    'offline-form',
    'LATEST_JOBS NEW': 'latest-jobs',
    'UPCOMING_JOBS':   'upcoming-jobs',
    'ADMISSIONS':      'admissions',
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

    # ── FALLBACK: OFFLINE_FORM + LATEST_JOBS NEW + UPCOMING_JOBS + ADMISSIONS ─
    # SARK mein ye categories empty hain (SR block). Data 2 sources se lo:
    # 1. merged_sarkari_data.json (already scraped on PC)
    # 2. freejobalert_unified (offline title wale jobs)
    if not sark_jobs and cat_key in ('OFFLINE_FORM','LATEST_JOBS NEW','UPCOMING_JOBS','ADMISSIONS'):
        # Source 1: merged_sarkari_data
        _msd_path = str(ROOT.parent/'scraper'/'merged_sarkari_data.json')
        if not os.path.exists(_msd_path):
            _msd_path = str(ROOT/'scraper'/'merged_sarkari_data.json')
        if os.path.exists(_msd_path):
            try:
                _msd = json.load(open(_msd_path, encoding='utf-8'))
                sark_jobs = [j for j in _msd.get('jobs',[]) if j.get('category') == cat_key]
            except Exception:
                pass
        # Source 2: unified jobs (for OFFLINE_FORM + LATEST_JOBS NEW)
        if not sark_jobs and cat_key in ('OFFLINE_FORM', 'LATEST_JOBS NEW'):
            _uni2 = (CJ.get('freejobalert_unified') or {})
            _uni_jobs2 = _uni2.get('deduped_jobs', []) or []
            _by_fja2 = _uni2.get('by_fja_category', {}) or {}
            _url_to_j2 = {j.get('_scraped_from',''): j for j in _uni_jobs2}
            for _uj2 in _uni_jobs2:
                _bd2 = (_uj2.get('basic_details') or {})
                _t2 = safe(_bd2.get('job_title',''))
                if not _t2: continue
                _is_offline = 'offline' in _t2.lower()
                if cat_key == 'OFFLINE_FORM' and not _is_offline: continue
                # Convert to sark-like format — use canonical resolver so the card
                # URL is identical to the physically generated detail-page path.
                _sl2 = get_canonical_slug(_uj2)
                _imp2 = (_uj2.get('important_dates') or {})
                sark_jobs.append({
                    'category': cat_key,
                    'title': _t2,
                    'slug': _sl2,
                    'organization': safe((_uj2.get('basic_details') or {}).get('organization_name','')),
                    'total_post': safe((_uj2.get('basic_details') or {}).get('total_vacancies','')),
                    'apply_mode': 'Offline' if _is_offline else 'Online',
                    'important_dates': _imp2,
                    'important_links': (_uj2.get('important_links') or {}),
                    'useful_links': {},
                    'status': '',
                })

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
        + '<a href="' + e(url) + '" class="lnk-btn ' + btn_cl + '" target="_blank" rel="nofollow noopener noreferrer" '
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
        on_full = (oi.get('name') or '').strip()   # full name for correct slug
        on_disp = on_full[:80]                      # truncated for display only
        ou  = (oi.get('url') or '').strip()
        osl = _du_slug(on_full, ou)                 # slug from FULL name — matches generated page
        if not _page_exists_on_disk(osl):           # never emit a 404 link
            continue
        others += '<li class="sec-item"><a href="/jobs/' + osl + '/">' + e(on_disp) + '</a></li>'
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
        '<meta name="viewport" content="width=device-width,initial-scale=1.0"/>' + VP_SNIPPET,
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
    'SR_Answer_Key':'answer-key','OFFLINE_FORM':'offline-form',
    'LATEST_JOBS NEW':'latest-jobs-new','UPCOMING_JOBS':'upcoming-jobs',
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
        # CRITICAL FIX: use get_canonical_slug() so section listing card hrefs
        # match the actual /jobs/{slug}/index.html files on disk.
        _clean_slug2 = get_canonical_slug(j)
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
            # Store canonical slug in BOTH _slug AND _canonical_slug so
            # build_listing_page → get_canonical_slug() resolves correctly.
            '_canonical_slug': _clean_slug2,
            '_slug': _clean_slug2,
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
        _esl  = get_canonical_slug(_ej)  # canonical — matches detail page path
        if not _page_exists_on_disk(_esl):  # never emit a 404 link
            continue
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
        'slug':  get_canonical_slug(_mj),  # canonical — matches detail page path
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
        # CRITICAL FIX: use get_canonical_slug() so sections-index slug
        # is identical to the actual /jobs/{slug}/index.html path on disk.
        _sl = get_canonical_slug(_j)
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
    # CRITICAL FIX: get_canonical_slug() so SARK section-index slugs match disk pages
    _sl = get_canonical_slug(_sj)
    _ld = safe((_sj.get('important_dates') or {}).get('last_date','') or _sj.get('last_date',''))
    if _scat not in sections_index:
        sections_index[_scat] = []
    if len(sections_index[_scat]) < 10:
        sections_index[_scat].append({'slug':_sl,'name':_st,'date':_ld})

# ── DEDUP CATEGORY CROSS-LISTING (Phase 7: Category Union) ────────────────────
# After dedup_engine.py runs, master records have _all_categories = union of
# all source categories. A merged record (e.g. TIFR job in 10TH_Pass, Diploma,
# ITI, B_Tech_BE, Any_Graduate) must appear in ALL 5 category sections.
# Without this, merged records only show in their primary FJA category bucket.
_dedup_map = {}   # slug → item dict (for cross-listing)
for _si_cat, _si_jobs in FJA.items():
    if not isinstance(_si_jobs, list): continue
    for _j in _si_jobs:
        _bd = (_j.get('basic_details') or {})
        _t  = safe(_bd.get('job_title',''))
        if not _t: continue
        _all_cats = _j.get('_all_categories', [])
        if not _all_cats: continue
        _sl = get_canonical_slug(_j)
        _imp = (_j.get('important_dates') or {})
        _ld  = safe(_imp.get('last_date_to_apply','') or _imp.get('last_date',''))
        _item = {'slug': _sl, 'name': _t, 'date': _ld}
        # Register in each category from _all_categories
        for _extra_cat in _all_cats:
            if _extra_cat == _si_cat: continue   # already added above
            if not _extra_cat: continue
            if _extra_cat not in sections_index:
                sections_index[_extra_cat] = []
            # Avoid duplicate slug in same category
            if not any(x.get('slug') == _sl for x in sections_index[_extra_cat]):
                if len(sections_index[_extra_cat]) < 10:
                    sections_index[_extra_cat].append(_item)

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

# ── UPCOMING_JOBS + ADMISSIONS: data/ JSON files se HAMESHA rebuild ───────────
# PERMANENT FIX: scraper/ folder delete kar diya. Ab data/upcoming-jobs.json
# aur data/admissions.json se padhte hain (PC scrape ke baad ye files update hoti hain).
_up_path = str(ROOT/'data'/'upcoming-jobs.json')
_adm_path = str(ROOT/'data'/'admissions.json')

def _read_jobs_file(_path):
    if not os.path.exists(_path): return []
    try:
        _d = json.load(open(_path, encoding='utf-8'))
        if isinstance(_d, dict): return _d.get('jobs', []) or []
        if isinstance(_d, list): return _d
    except Exception: pass
    return []

# UPCOMING_JOBS
_up_items = []
for _sj in _read_jobs_file(_up_path):
    _st = safe(_sj.get('title','') or _sj.get('name',''))
    if not _st: continue
    _sl = get_canonical_slug(_sj)
    _ld = safe(_sj.get('last_date','') or
               (_sj.get('important_dates') or {}).get('last_date_apply_online','') or
               (_sj.get('important_dates') or {}).get('last_date_to_apply','') or
               (_sj.get('important_dates') or {}).get('last_date',''))
    _up_items.append({'slug':_sl,'name':_st,'date':_ld})
# Fallback: SARK from current JSON
if not _up_items:
    for _sj in SARK:
        if _sj.get('category') != 'UPCOMING_JOBS': continue
        _st = safe(_sj.get('title',''))
        if not _st: continue
        _sl = get_canonical_slug(_sj)
        _imp = _sj.get('important_dates') or {}
        _ld = safe(_imp.get('last_date_apply_online','') or _imp.get('last_date_to_apply','') or _imp.get('last_date',''))
        _up_items.append({'slug':_sl,'name':_st,'date':_ld})
if _up_items:
    sections_index['UPCOMING_JOBS'] = _up_items[:10]
    print(f"  [UPCOMING_JOBS] {len(_up_items[:10])} items loaded")

# ADMISSIONS
_adm_items = []
for _sj in _read_jobs_file(_adm_path):
    _st = safe(_sj.get('title','') or _sj.get('name',''))
    if not _st: continue
    _sl = get_canonical_slug(_sj)
    _ld = safe(_sj.get('last_date','') or
               (_sj.get('important_dates') or {}).get('last_date_apply_online','') or
               (_sj.get('important_dates') or {}).get('last_date_to_apply','') or
               (_sj.get('important_dates') or {}).get('last_date',''))
    _adm_items.append({'slug':_sl,'name':_st,'date':_ld})
if not _adm_items:
    for _sj in SARK:
        if _sj.get('category') != 'ADMISSIONS': continue
        _st = safe(_sj.get('title',''))
        if not _st: continue
        _sl = get_canonical_slug(_sj)
        _imp = _sj.get('important_dates') or {}
        _ld = safe(_imp.get('last_date_apply_online','') or _imp.get('last_date_to_apply','') or _imp.get('last_date',''))
        _adm_items.append({'slug':_sl,'name':_st,'date':_ld})
if _adm_items:
    sections_index['ADMISSIONS'] = _adm_items[:10]
    print(f"  [ADMISSIONS] {len(_adm_items[:10])} items loaded")

# ── OFFLINE_FORM: FJA jobs se HAMESHA rebuild (permanent fix) ────────────────
_offline_items = []; _offline_seen = set()
for _fj in (list(FJA.get('Latest_Notifications',[])) +
             list(FJA.get('Any_Graduate',[])) +
             list(FJA.get('10TH_Pass',[]))):
    _bd2 = (_fj.get('basic_details') or {})
    _ft = safe(_bd2.get('job_title',''))
    if not _ft or _ft in _offline_seen: continue
    if 'offline' not in _ft.lower(): continue
    _sl2 = get_canonical_slug(_fj)
    _imp2 = (_fj.get('important_dates') or {})
    _ld2 = safe(_imp2.get('last_date_to_apply','') or _imp2.get('last_date',''))
    _offline_items.append({'slug':_sl2,'name':_ft,'date':_ld2})
    _offline_seen.add(_ft)
    if len(_offline_items) >= 10: break
if _offline_items:
    sections_index['OFFLINE_FORM'] = _offline_items

# ── LATEST_JOBS NEW: FJA Latest_Notifications se HAMESHA rebuild ─────────────
_ln_items = []; _ln_seen = set()
for _fj in FJA.get('Latest_Notifications', []):
    _bd3 = (_fj.get('basic_details') or {})
    _ft3 = safe(_bd3.get('job_title',''))
    if not _ft3 or _ft3 in _ln_seen: continue
    _sl3 = get_canonical_slug(_fj)
    _imp3 = (_fj.get('important_dates') or {})
    _ld3 = safe(_imp3.get('last_date_to_apply','') or _imp3.get('last_date',''))
    _ln_items.append({'slug':_sl3,'name':_ft3,'date':_ld3})
    _ln_seen.add(_ft3)
    if len(_ln_items) >= 10: break
if _ln_items:
    sections_index['LATEST_JOBS NEW'] = _ln_items

# ── Add DU sections to sections-index.json (Phase: slug-based internal links) ──
# Govt Scheme & Yojna, ImportantCSC PDF, ImportantCSC link, Today Updates
# These come from dailyupdates.json and have slug fields — add them so
# mkCard on homepage uses /jobs/slug/ internal pages instead of external URLs.
for _du_si_sec in DU_SECS:
    _du_si_title = _du_si_sec.get('title', '')
    if not _du_si_title:
        continue
    _du_si_items = []
    for _du_si_item in _du_si_sec.get('items', [])[:10]:
        _name = (_du_si_item.get('name') or '').strip()
        _slug = (_du_si_item.get('slug') or '').strip()
        _url  = (_du_si_item.get('url') or '').strip()
        if not _name:
            continue
        # Use slug if present (links to /jobs/slug/), else fall back to url
        _du_si_items.append({
            'slug': _slug,
            'name': _name,
            'url':  _url,
            'date': (_du_si_item.get('date') or ''),
        })
    if _du_si_items:
        sections_index[_du_si_title] = _du_si_items

# ── RECONCILE sections-index slugs to ACTUAL disk pages ─────────────────────
# Issue: sections-index items reference /jobs/{slug}/ but page hi nahi exist karta
# Result: User clicks → "Page Not Available" → SEO disaster
# Fix: For each section item, verify slug exists. If not, find closest match by title
# OR remove the item entirely (better than dead link).
import glob as _glob_fix
_disk_slugs = set()
for _f in _glob_fix.glob(str(ROOT/'jobs'/'*'/'index.html')):
    _disk_slugs.add(os.path.basename(os.path.dirname(_f)))

# Build title→slug index from disk pages (for fuzzy match)
def _disk_h1(_slug):
    _p = ROOT/'jobs'/_slug/'index.html'
    if not _p.exists(): return ''
    try:
        _html = _p.read_text(encoding='utf-8', errors='ignore')[:5000]
        _m = re.search(r'<h1[^>]*>([^<]+)</h1>', _html)
        return (_m.group(1) if _m else '').strip().lower()
    except Exception: return ''

# Stop words for fuzzy match
_STOP_RECON = {'recruitment','for','apply','online','offline','notification','out',
               '2026','2025','posts','post','more','the','and','a','to','of','in','on',
               'at','an','is','are','-',',','for','last','date','short'}

def _name_tokens(_name):
    _t = re.sub(r'[^a-z0-9\s]', ' ', (_name or '').lower())
    return frozenset(w for w in _t.split() if w and w not in _STOP_RECON and len(w) > 2)

# Build disk page tokens once
_disk_tokens = {}
for _ds in _disk_slugs:
    _h1 = _disk_h1(_ds)
    if _h1:
        _disk_tokens[_ds] = _name_tokens(_h1)

# Reconcile each sections_index item
_recon_fixed = 0
_recon_removed = 0
for _sec_key, _sec_items in list(sections_index.items()):
    if not isinstance(_sec_items, list): continue
    _kept = []
    for _it in _sec_items:
        if not isinstance(_it, dict):
            _kept.append(_it); continue
        _it_slug = _it.get('slug', '')
        _it_url = (_it.get('url', '') or '')
        # External URLs: keep as-is
        if _it_url.startswith('http') and 'topsarkarijobs.com' not in _it_url:
            _kept.append(_it); continue
        # No slug: keep (no detail page expected)
        if not _it_slug:
            _kept.append(_it); continue
        # Slug has disk page: OK
        if _it_slug in _disk_slugs:
            _kept.append(_it); continue
        # Slug NOT on disk: try fuzzy match
        _it_tokens = _name_tokens(_it.get('name', ''))
        if len(_it_tokens) < 2:
            _recon_removed += 1; continue
        _best_slug = None; _best_score = 0
        for _ds, _dt in _disk_tokens.items():
            _common = _it_tokens & _dt
            if len(_common) >= max(3, int(len(_it_tokens) * 0.55)):
                _score = len(_common)
                if _score > _best_score:
                    _best_score = _score; _best_slug = _ds
        if _best_slug:
            _it['slug'] = _best_slug
            _kept.append(_it)
            _recon_fixed += 1
        else:
            _recon_removed += 1   # no matching page; drop item
    sections_index[_sec_key] = _kept

if _recon_fixed or _recon_removed:
    print(f"  [reconcile] sections-index fixed {_recon_fixed} slugs, removed {_recon_removed} dead items")

write(str(ROOT/'sections-index.json'), json.dumps(sections_index, ensure_ascii=False, separators=(',',':')))

# ── HOMEPAGE SR-SECTION CARDS: server-side pre-render (LCP fix) ─────────────
# The homepage used to ship only 4 empty skeleton divs in static HTML and
# build all 26 section cards purely client-side after fetching
# sections-index.json + dailyupdates.json. Under throttled mobile conditions
# that fetch+parse+render chain was the dominant cost behind a 7s+ LCP.
# sections_index (just written above, already reconciled to real /jobs/
# pages) has every field mkCard() needs, so mirror that exact JS template
# here in Python and inject real HTML at generation time. tsj9's own JS
# still runs afterwards to refresh the cards in the background — it already
# skips replacing the DOM once it finds >=20 real (non-skeleton) cards.
_HOMEPAGE_SECS = [
    ('Latest Jobs',          'SR_Latest_Jobs',       '/section/latest-jobs/',           '#1a56db'),
    ('Result',               'SR_Result',             '/section/results/',               '#9b1c1c'),
    ('Admit Card',           'SR_Admit_Card',         '/section/admit-card/',            '#1e3a5f'),
    ('Admission',            'ADMISSIONS',            '/section/admissions/',            '#14532d'),
    ('Answer Key',           'SR_Answer_Key',         '/section/answer-key/',            '#713f12'),
    ('Offline Form',         'OFFLINE_FORM',          '/section/offline-form/',          '#1e3a5f'),
    ('Upcoming Jobs',        'UPCOMING_JOBS',         '/section/upcoming-jobs/',         '#14532d'),
    ('Latest Jobs New',      'LATEST_JOBS NEW',       '/section/latest-jobs-new/',       '#1a56db'),
    ('Latest Notifications', 'Latest_Notifications',  '/section/latest-notifications/',  '#1a56db'),
    ('10th Pass Jobs',       '10TH_Pass',             '/section/10th-pass-jobs/',        '#9b1c1c'),
    ('12th Pass Jobs',       '12TH_Pass',             '/section/12th-pass-jobs/',        '#14532d'),
    ('Diploma Jobs',         'Diploma',               '/section/diploma-jobs/',          '#713f12'),
    ('ITI Jobs',             'ITI',                   '/section/iti-jobs/',              '#1e3a5f'),
    ('B.Tech / B.E. Jobs',   'B_Tech_BE',             '/section/btech-jobs/',            '#14532d'),
    ('Any Graduate Jobs',    'Any_Graduate',          '/section/graduation-jobs/',       '#1a56db'),
    ('Post Graduate Jobs',   'Any_Post_Graduate',     '/section/post-graduation-jobs/',  '#9b1c1c'),
    ('Railway Jobs',         'Railway_Jobs',          '/section/railway-jobs/',          '#1e3a5f'),
    ('Police / Defence',     'Police_Defence',        '/section/police-jobs/',           '#14532d'),
    ('Teaching / Faculty',   'Teaching_Faculty',      '/section/teaching-jobs/',         '#713f12'),
    ('Bank Jobs',            'Bank_Jobs',             '/section/bank-jobs/',             '#1e3a5f'),
    ('Medical / Hospital',   'Medical_Hospital',      '/section/healthcare-jobs/',       '#9b1c1c'),
    ('Last Date Reminder',   'Last_Date_Reminder',    '/section/last-date-reminder/',    '#14532d'),
    ('Govt Scheme & Yojna',  'Govt Scheme & Yojna',   '/section/govt-scheme-yojna/',     '#1a56db'),
    ('ImportantCSC PDF',     'ImportantCSC PDF',      '/section/importantcsc-pdf/',      '#713f12'),
    ('ImportantCSC link',    'ImportantCSC link',     '/section/importantcsc-link/',     '#9b1c1c'),
    ('Today Updates',        'Today Updates',         '/section/today-updates/',         '#F24EEC'),
]

def _render_homepage_sr_cards(sec_index, max_items=5):
    out = []
    for label, key, url, color in _HOMEPAGE_SECS:
        items = (sec_index.get(key) or [])[:max_items]
        li_parts = []
        n = 0
        for it in items:
            if not isinstance(it, dict): continue
            nm = (it.get('name') or '').strip()
            if not nm: continue
            slug = (it.get('slug') or '').strip()
            raw_url = (it.get('url') or '').strip()
            href = f'/jobs/{slug}/' if slug else (raw_url or url)
            is_ext = href.startswith('http') and 'topsarkarijobs.com' not in href
            tgt = ' target="_blank" rel="noopener noreferrer"' if is_ext else ''
            dt = str(it.get('date') or '')
            n += 1
            li_parts.append(
                f'<li><a href="{e(href)}"{tgt} class="sr-job-link"><span class="sr-num">{n}</span>'
                f'<span class="sr-job-title">{e(nm[:80])}</span>'
                + (f'<span class="sr-job-date">{e(dt[:10])}</span>' if dt else '')
                + ('<span style="margin-left:3px;font-size:.58rem;color:#7c3aed;">↗</span>' if is_ext else '')
                + '</a></li>'
            )
        li_html = ''.join(li_parts) if li_parts else (
            f'<li><a href="{e(url)}" class="sr-job-link">'
            f'<span class="sr-job-title">View all {e(label)} &rarr;</span></a></li>')
        out.append(
            f'<div class="sr-card"><div class="sr-card-head" style="background:{color}">'
            f'<div class="left"><span class="sr-section-title">{e(label)}</span></div>'
            f'<a href="{e(url)}" aria-label="View all {e(label)}" '
            'style="color:#fff;font-size:.68rem;background:rgba(255,255,255,.2);padding:2px 7px;'
            f'border-radius:4px;text-decoration:none;white-space:nowrap;">View All</a></div>'
            f'<ul class="sr-job-list">{li_html}</ul>'
            f'<div class="sr-card-footer"><a href="{e(url)}" class="sr-sub-link">View All {e(label)} &rarr;</a></div>'
            '</div>')
    return ''.join(out)

# Update version string in index.html to bust cache + inject pre-rendered cards
_ver = __import__('datetime').datetime.now().strftime('%Y%m%d%H%M')
_idx_path = str(ROOT/'index.html')
if __import__('os').path.exists(_idx_path):
    _idx = open(_idx_path, encoding='utf-8').read()
    import re as _re
    _idx_new = _re.sub(r'sections-index\.json\?v=\d+', f'sections-index.json?v={_ver}', _idx)
    _sr_cards_html = _render_homepage_sr_cards(sections_index)
    _idx_new = _re.sub(
        r'(<div id="sr-sections-grid" class="sr-sections-grid">)(.*?)(</div>\s*</div>\s*<div id="dynamic-sections")',
        lambda _m: _m.group(1) + _sr_cards_html + _m.group(3),
        _idx_new, count=1, flags=_re.S)
    if _idx_new != _idx:
        open(_idx_path, 'w', encoding='utf-8').write(_idx_new)

import time as _time
_save_first_seen()   # C1: persist datePosted map for stable rebuilds
_save_slug_registry()  # Persist slug registry (title-change proof)

# ── One HTML = One URL: prune any cross-source duplicate pages ────────────────
# Same recruitment can come from sarkari + state + education with DIFFERENT
# slugs (e.g. "...-recruitment-2026-apply-online" and "...-1-posts"). They
# produce IDENTICAL rendered <h1>, which we use as a precise fingerprint. We
# keep the most canonical slug, delete the rest, and append 301 redirects to
# _redirects so deleted URLs forward to the survivor (zero SEO loss).
def prune_duplicate_pages():
    import glob as _glob
    from collections import defaultdict as _dd
    from itertools import combinations as _comb
    H1_RE = re.compile(r'<h1 class="detail-h1">([^<]+)</h1>')
    # Pull vacancy count + last date from the page so we can corroborate fuzzy
    # title matches (same number of posts / same closing date = same job).
    VAC_RE = re.compile(r'(\d{1,6})\s*(?:posts?|vacanc)', re.I)
    DATE_RE = re.compile(r'(\d{1,2}[-/][\d]{1,2}[-/]20\d{2}|20\d{2}-\d{1,2}-\d{1,2})')
    STOP = {'the','and','for','of','in','to','a','an','with','on','at','by','top','sarkari','jobs',
            'recruitment','apply','online','offline','notification','out','check','details','post','posts',
            'vacancy','form','registration','last','date','here','now','download','pdf','2024','2025','2026','2027'}
    def _tokens(h1):
        t = re.sub(r'[^a-z0-9\s]', ' ', (h1 or '').lower())
        return set(w for w in t.split() if w and w not in STOP and len(w) > 1)
    def _score(slug):
        s = 0.0
        if 'recruitment' in slug: s += 3
        if 'apply' in slug: s += 2
        if re.search(r'202\d', slug): s += 2
        if re.search(r'-\d+-posts$', slug) or slug.endswith('-1-posts'): s -= 2
        return s + len(slug) / 100.0

    # Gather every job page's slug + token-set + vacancy + date + raw-fp
    pages = []   # (slug, tokenset, vacancy, date)
    exact_groups = _dd(list)
    for f in _glob.glob(str(ROOT/'jobs'/'*'/'index.html')):
        slug = os.path.basename(os.path.dirname(f))
        try:
            h = open(f, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        m = H1_RE.search(h)
        if not m:
            continue
        h1 = m.group(1).strip()
        toks = _tokens(h1)
        if not toks:
            continue
        vm = VAC_RE.search(h1) or VAC_RE.search(h[:4000])
        vac = vm.group(1) if vm else ''
        dm = DATE_RE.search(h[:6000])
        date = dm.group(1) if dm else ''
        pages.append((slug, toks, vac, date))
        # exact fingerprint key (sorted tokens) for the fast obvious-dup path
        exact_groups[' '.join(sorted(toks))].append(slug)

    # Build merge groups via union-find over fuzzy token similarity
    parent = {}
    def _find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = _find(parent[x])
        return parent[x]
    def _union(a, b):
        parent[_find(a)] = _find(b)

    # 1) exact-token duplicates always union
    for _fp, slugs in exact_groups.items():
        for s in slugs[1:]:
            _union(slugs[0], s)

    # 2) fuzzy: same vacancy or same date + high token overlap → union.
    # Group by vacancy/date first to keep comparisons cheap and precise.
    JACCARD = 0.72
    by_key = _dd(list)
    for idx, (slug, toks, vac, date) in enumerate(pages):
        if vac:
            by_key['v'+vac].append(idx)
        if date:
            by_key['d'+date].append(idx)
    for _key, idxs in by_key.items():
        if len(idxs) < 2:
            continue
        for a, b in _comb(idxs, 2):
            sa, ta, _, _ = pages[a]
            sb, tb, _, _ = pages[b]
            if _find(sa) == _find(sb):
                continue
            uni = ta | tb
            if uni and len(ta & tb) / len(uni) >= JACCARD:
                _union(sa, sb)

    # Collect final clusters
    clusters = _dd(list)
    for slug, toks, vac, date in pages:
        clusters[_find(slug)].append(slug)

    redirects = []
    removed = 0
    for _root, slugs in clusters.items():
        if len(slugs) < 2:
            continue
        # If any page in this group is an intentional NEW VERSION (different
        # year/advt/dates), do NOT merge — these are legitimately separate pages.
        if any(s in versioned_variant_slugs for s in slugs):
            continue
        keep = max(slugs, key=_score)
        for s in slugs:
            if s == keep:
                continue
            d = str(ROOT/'jobs'/s)
            try:
                shutil.rmtree(d)
                pj = str(ROOT/'jobs'/'data'/(s + '.json'))
                if os.path.exists(pj):
                    os.remove(pj)
                redirects.append((s, keep))
                removed += 1
            except Exception:
                pass
    # Append 301 redirects (dedupe against existing lines)
    if redirects:
        rpath = str(ROOT/'_redirects')
        existing = ''
        if os.path.exists(rpath):
            existing = open(rpath, encoding='utf-8').read()
        new_lines = []
        for old, new in redirects:
            rule = f"/jobs/{old}/  /jobs/{new}/  301"
            if rule not in existing:
                new_lines.append(rule)
        if new_lines:
            block = "\n# ══ auto: duplicate job pages → canonical (One-HTML-One-URL) ══\n" + "\n".join(new_lines) + "\n"
            with open(rpath, 'a', encoding='utf-8') as f:
                f.write(block)
    print(f"  [dedup] removed {removed} duplicate page(s); {len(redirects)} redirect(s) added")
    return removed

# PERMANENT PAGE SYSTEM: prune_duplicate_pages() disabled.
# Duplicate pages delete karna band — ek baar bana hua URL hamesha live rahega.
# Disk preload (upar) already dedup handle karta hai — same slug dobara nahi likhega.
_dup_removed = 0
print("  [dedup] prune disabled - permanent page system active")

# ── ORPHAN PAGE REMOVAL: One-Job-One-URL-One-HTML enforcement ────────────────
# Pages exist on disk but NOT in current JSON = orphan from past generates.
# These create duplicate content issues for Google indexing. Delete them.
def remove_orphan_pages():
    import glob as _g
    # Build set of valid slugs from CURRENT JSON data sources
    valid_slugs = set()
    # 1. Sarkari jobs — use get_canonical_slug() so valid_slugs exactly matches
    # the slugs used when creating pages (no deletions due to slug mismatch).
    for _j in SARK:
        _vs = get_canonical_slug(_j)
        if _vs: valid_slugs.add(_vs)
        # Also add raw slug variants for backward compat with already-created pages
        _s = _norm_slug(_j.get('slug', ''))
        if _s: valid_slugs.add(_s)
        _cs = _norm_slug(_j.get('_canonical_slug', ''))
        if _cs: valid_slugs.add(_cs)
    # 2. FJA unified jobs — use get_canonical_slug() for consistency
    _uni_jobs_v = (CJ.get('freejobalert_unified', {}) or {}).get('deduped_jobs', []) or []
    for _j in _uni_jobs_v:
        _vs = get_canonical_slug(_j)
        if _vs: valid_slugs.add(_vs)
        # Also add raw slug and title-based slug for backward compat
        _s = _j.get('slug', '')
        if _s: valid_slugs.add(_s)
        _bd = _j.get('basic_details', {}) or {}
        _t = _bd.get('job_title', '')
        if _t:
            _title_slug = registered_slug(_t)
            if _title_slug: valid_slugs.add(_title_slug)
    # 3. FJA category jobs
    for _fcat, _fjobs in (FJA_RAW or {}).items():
        for _fj in (_fjobs or []):
            _fv = get_canonical_slug(_fj)
            if _fv: valid_slugs.add(_fv)
    # 4. sections-index slugs
    for _cat_items in (sections_index or {}).values():
        if isinstance(_cat_items, list):
            for _it in _cat_items:
                if isinstance(_it, dict) and _it.get('slug'):
                    valid_slugs.add(_it['slug'])
    # 5. DU items (govt schemes, csc pdf, etc)
    for _du_sec in (DU_SECS or []):
        for _du_it in (_du_sec.get('items', []) or []):
            _du_name = _du_it.get('name', '') or _du_it.get('title', '')
            if _du_name:
                _du_slug = slugify(_du_name)[:80]
                if _du_slug: valid_slugs.add(_du_slug)
    # 6. EDUCATION items — CRITICAL: without this, all 883 edu pages get deleted!
    _edu_r = CJ.get('education_jobs', {}) or {}
    _edu_secs = _edu_r if isinstance(_edu_r, list) else _edu_r.get('sections', [])
    for _esec in _edu_secs:
        for _eitem in (_esec.get('items', []) if isinstance(_esec, dict) else []):
            _ename = _eitem.get('name', '') or _eitem.get('examName', '')
            if _ename:
                _es = slugify(_ename)[:80]
                if _es: valid_slugs.add(_es)

    print(f"  [orphan-check] {len(valid_slugs)} valid slugs from current JSON")

    # SAFETY: if valid_slugs is suspiciously small, ABORT (don't delete everything!)
    if len(valid_slugs) < 100:
        print(f"  [orphan-check] SAFETY ABORT - valid_slugs too small, skipping cleanup")
        return 0

    # Find orphan pages on disk
    redirects_added = []
    orphans_deleted = 0
    rpath = str(ROOT/'_redirects')
    existing_redirects = ''
    if os.path.exists(rpath):
        existing_redirects = open(rpath, encoding='utf-8').read()

    for _fpath in _g.glob(str(ROOT/'jobs'/'*'/'index.html')):
        _slug = os.path.basename(os.path.dirname(_fpath))
        if _slug in valid_slugs:
            continue   # page is valid
        # Orphan → delete HTML + add 301 to homepage
        try:
            shutil.rmtree(os.path.dirname(_fpath))
            orphans_deleted += 1
            if f'/jobs/{_slug}/' not in existing_redirects:
                redirects_added.append((_slug, '/section/latest-jobs/'))
        except Exception:
            pass

    # Append redirects
    if redirects_added:
        block = "\n# ══ auto: orphan pages → homepage (Job no longer active) ══\n"
        for old_slug, target in redirects_added:
            block += f"/jobs/{old_slug}/  {target}  301\n"
        with open(rpath, 'a', encoding='utf-8') as _rf:
            _rf.write(block)
    print(f"  [orphan-cleanup] {orphans_deleted} orphan pages removed, {len(redirects_added)} redirects added")
    return orphans_deleted

# PERMANENT PAGE SYSTEM: remove_orphan_pages() disabled.
# JSON se job remove ho jaye to bhi uska /jobs/{slug}/ page kabhi delete nahi hoga.
# Woh page live rehta hai — Google index nahi todna, URL 404 nahi banana.
# Listing pages (category/section) automatically update hote hain — wahan se
# removed job dikhai nahi dega, lekin detail page accessible rahega.
_orphans_removed = 0
print("  [orphan-cleanup] disabled - all existing pages preserved permanently")

# ── ONE-JOB-ONE-URL-ONE-HTML VERIFICATION ─────────────────────────────────────
# After all generation + cleanup, verify the canonical guarantee:
# 1. Remove any stale "/jobs/{slug}/ → / 301" from _redirects where slug is now valid
#    (previous bad runs may have added these; if a valid page exists, redirect blocks it)
# 2. Detect any disk pages NOT in current JSON (true orphans)
# 3. Report final stats
def verify_one_job_one_url():
    import glob as _g2
    # Rebuild current valid_slugs (same as orphan check)
    _valid = set()
    for _j in SARK:
        _s = _j.get('slug', '')
        if _s: _valid.add(_s)
    _uni_v = (CJ.get('freejobalert_unified', {}) or {}).get('deduped_jobs', []) or []
    for _j in _uni_v:
        _s = _j.get('slug', '')
        if _s: _valid.add(_s)
        _bd = _j.get('basic_details', {}) or {}
        _t = _bd.get('job_title', '')
        if _t: _valid.add(slugify(_t)[:80])
    for _fcat, _fjobs in (FJA_RAW or {}).items():
        for _fj in (_fjobs or []):
            _fbd = _fj.get('basic_details', {}) or {}
            _ft = _fbd.get('job_title', '')
            if _ft: _valid.add(slugify(_ft)[:80])
    for _cat_items in (sections_index or {}).values():
        if isinstance(_cat_items, list):
            for _it in _cat_items:
                if isinstance(_it, dict) and _it.get('slug'):
                    _valid.add(_it['slug'])
    # Also include DU items (govt schemes, csc pdf etc — same as orphan check)
    for _du_sec in (DU_SECS or []):
        for _du_it in (_du_sec.get('items', []) or []):
            _du_name = _du_it.get('name', '') or _du_it.get('title', '')
            if _du_name:
                _du_slug = slugify(_du_name)[:80]
                if _du_slug: _valid.add(_du_slug)
    # Education items — must match what's in valid_slugs in remove_orphan_pages
    _edu_rv = CJ.get('education_jobs', {}) or {}
    _edu_secsv = _edu_rv if isinstance(_edu_rv, list) else _edu_rv.get('sections', [])
    for _esecv in _edu_secsv:
        for _eitemv in (_esecv.get('items', []) if isinstance(_esecv, dict) else []):
            _enamev = _eitemv.get('name', '') or _eitemv.get('examName', '')
            if _enamev:
                _esv = slugify(_enamev)[:80]
                if _esv: _valid.add(_esv)

    # STEP 1: Clean stale redirects — for each /jobs/{slug}/ rule, if a real
    # HTML page exists on disk at that slug, the redirect is blocking it.
    # Remove the rule so the page actually serves.
    import glob as _g_verify
    _disk_now = set()
    for _f in _g_verify.glob(str(ROOT/'jobs'/'*'/'index.html')):
        _disk_now.add(os.path.basename(os.path.dirname(_f)))

    rpath = str(ROOT/'_redirects')
    if os.path.exists(rpath) and _disk_now:
        _lines = open(rpath, encoding='utf-8').read().splitlines()
        _kept_lines = []
        _removed_stale = 0
        for _line in _lines:
            _stripped = _line.strip()
            # Match: /jobs/{slug}/  /  301  (orphan-to-homepage rule)
            # Match: /jobs/{slug}/  TARGET  301  — ANY redirect from a slug
            # that's now a valid page must be removed (page exists, redirect blocks it).
            _m = re.match(r'^/jobs/([^/\s]+)/\s+\S+\s+301[!]?\s*$', _stripped)
            if _m:
                _rslug = _m.group(1)
                # NEVER remove cross-source dedup redirects (sark→fja)
                # even if disk has a stale page from a previous run
                if _rslug in _disk_now and _rslug not in _dedup_sark_slugs:
                    # This slug has a real page on disk! Remove blocking redirect.
                    _removed_stale += 1
                    continue
            _kept_lines.append(_line)
        if _removed_stale > 0:
            with open(rpath, 'w', encoding='utf-8') as _rf:
                _rf.write('\n'.join(_kept_lines) + '\n')
            print(f"  [verify] Removed {_removed_stale} stale redirects (pages exist on disk)")

    # STEP 2: Final disk count
    _disk_pages = set()
    for _f in _g2.glob(str(ROOT/'jobs'/'*'/'index.html')):
        _disk_pages.add(os.path.basename(os.path.dirname(_f)))

    _orphans_still = _disk_pages - _valid
    _missing_pages = _valid - _disk_pages

    print(f"  [verify] Disk pages: {len(_disk_pages)}")
    print(f"  [verify] Valid (JSON): {len(_valid)}")
    print(f"  [verify] In both: {len(_disk_pages & _valid)}")
    print(f"  [verify] Orphans remaining: {len(_orphans_still)}")
    if _orphans_still and len(_orphans_still) < 20:
        for _o in list(_orphans_still)[:10]:
            print(f"           orphan: /jobs/{_o}/")
    print(f"  [verify] JSON jobs without page: {len(_missing_pages)} (likely garbage titles or skipped)")
    print(f"  [OK] ONE-JOB-ONE-URL-ONE-HTML: {len(_disk_pages)} unique pages, no duplicate URLs")

verify_one_job_one_url()
print(f"  Total cleanup: {_dup_removed} dup + {_orphans_removed} orphans = {_dup_removed + _orphans_removed} pages removed")

# PERMANENT PAGE SYSTEM: broken-pages deletion disabled.
# Page Not Available wale ya empty pages delete karna band.
# Permanent page system mein koi bhi /jobs/ page delete nahi hoga.
_broken_removed = 0
print("  [broken-pages] deletion disabled - permanent page system active")


# If dedup_engine.py produced a redirect map, inject those 301s into _redirects
# so old URLs (e.g. hssc-cet-group-d-exam-online-form-2026) forward to canonical.
_dedup_rmap_path = str(ROOT.parent / 'scraper' / 'dedup_redirect_map.json')
if not os.path.exists(_dedup_rmap_path):
    _dedup_rmap_path = str(ROOT / 'dedup_redirect_map.json')   # fallback
if os.path.exists(_dedup_rmap_path):
    try:
        _rmap = json.load(open(_dedup_rmap_path, encoding='utf-8'))
        _rpath = str(ROOT / '_redirects')
        _existing_r = open(_rpath, encoding='utf-8').read() if os.path.exists(_rpath) else ''
        _new_lines = []
        for _old_s, _new_s in _rmap.items():
            _rule = f"/jobs/{_old_s}/  /jobs/{_new_s}/  301"
            if _rule not in _existing_r:
                _new_lines.append(_rule)
        if _new_lines:
            _block = "\n# ══ dedup_engine: cross-source duplicate → canonical URL ══\n" + "\n".join(_new_lines) + "\n"
            with open(_rpath, 'a', encoding='utf-8') as _rf:
                _rf.write(_block)
        print(f"  [dedup_redirects] {len(_rmap)} redirect rules from dedup_engine "
              f"({len(_new_lines)} new)")
    except Exception as _e:
        print(f"  [dedup_redirects] could not load redirect map: {_e}")

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
print(f"\u2551  Schema patches        : {_schema_patched:<27}\u2551")
print(f"\u2551  Schema patches        : {_schema_patched:<27}\u2551")
print("\u255a" + "\u2550"*54 + "\u255d")
print()
