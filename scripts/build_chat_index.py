#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_chat_index.py — universal search index for the TSJ AI chat widget.

Complete_Jobs_Full_Data.json is ~40MB — far too big to fetch/parse in a
browser (especially on mobile). This produces chat-search-index.json: a
compact per-item record across EVERYTHING queryable on the site — job/exam
postings (sarkari_data, FJA, education_jobs), non-job posts from
dailyupdates.json (Govt Scheme & Yojna, ImportantCSC PDF/link, Today
Updates), the site's tools, and section hub pages — a few MB at most —
which the widget loads once, caches, and fuzzy/profile-searches locally
(Fuse.js) before ever calling the AI backend, so most "does this exist on
the site" questions never need a network round-trip to answer.

Each job entry also carries:
  - 'age': [minAge, maxAge] when confidently parseable (sarkari_data only —
    FJA's age text is too free-form/position-specific to parse reliably)
  - 'ql': qualification-category tags (e.g. 'B_A', 'Any_Graduate', '10TH_Pass')
    reused directly from sections-index.json's own per-job classification
    (already computed correctly elsewhere in the pipeline) so the widget can
    answer "B.A pass, age 21 — which jobs am I eligible for?" with a real
    filtered list instead of relying on fuzzy title search alone.

Run from repo root:  python3 scripts/build_chat_index.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = 'https://www.topsarkarijobs.com'

# sections-index.json keys that are job-type/admin buckets, not qualification
# levels — everything else in that file is a genuine qualification tag.
_NON_QUAL_KEYS = {
    'Railway_Jobs', 'Police_Defence', 'Teaching_Faculty', 'Bank_Jobs', 'Medical_Hospital',
    'Last_Date_Reminder', 'Latest_Notifications', 'SR_Latest_Jobs', 'SR_Result',
    'SR_Admit_Card', 'SR_Answer_Key', 'OFFLINE_FORM', 'LATEST_JOBS NEW', 'UPCOMING_JOBS',
    'ADMISSIONS', 'Govt Scheme & Yojna', 'ImportantCSC PDF', 'ImportantCSC link',
    'Today Updates', 'Retired_Staff',
}

# Hardcoded site tools — not present in Complete_Jobs_Full_Data.json at all.
TOOLS = [
    ('AI Photo Enhancer', 'Improve blurry/low-quality photo with real AI super-resolution and face enhancement', '/tools/image/photo-enhancer.html'),
    ('Photo Resize Tool', 'Resize photo to exact pixel size / KB for government form uploads', '/tools/image/image-resizer.html'),
    ('Bulk Image Resize', 'Resize many photos at once to a fixed size', '/tools/image/bulk-image-resize.html'),
    ('Compress Image', 'Reduce photo file size (KB) without losing quality, for form uploads', '/tools/image/compress-image.html'),
    ('Passport Size Photo Maker', 'Create passport / govt form size photo online', '/tools/image/passport-photo.html'),
    ('Background Remover', 'Remove background from a photo online', '/tools/image/background-remove.html'),
    ('Photo Editor', 'Crop, rotate and edit photos online', '/tools/image/photo-editor.html'),
    ('Signature Resize Tool', 'Resize scanned signature to the exact KB/size required for online forms', '/tools/image/signature-resizer.html'),
    ('Document Scanner', 'Scan a document with your phone camera and save as PDF', '/tools/image/document-scanner.html'),
    ('Image to PDF Converter', 'Convert one or more images into a single PDF', '/tools/image/image-to-pdf.html'),
    ('Image Format Converter', 'Convert between JPG, PNG, WEBP, HEIC formats', '/tools/image/convert-any-format.html'),
    ('JPG to PNG Converter', 'Convert JPG image to PNG', '/tools/image/jpg-to-png.html'),
    ('PNG to JPG Converter', 'Convert PNG image to JPG', '/tools/image/png-to-jpg.html'),
    ('WEBP to JPG Converter', 'Convert WEBP image to JPG', '/tools/image/webp-to-jpg.html'),
    ('HEIC to JPG Converter', 'Convert iPhone HEIC photo to JPG', '/tools/image/heic-to-jpg.html'),
    ('Merge Images', 'Combine multiple images into one', '/tools/image/image-merge.html'),
    ('Compress PDF', 'Reduce PDF file size for online form upload', '/tools/pdf/compress-pdf.html'),
    ('Merge PDF', 'Combine multiple PDF files into one', '/tools/pdf/merge-pdf.html'),
    ('Split PDF', 'Split a PDF into separate pages/files', '/tools/pdf/split-pdf.html'),
    ('PDF to Word Converter', 'Convert PDF to an editable Word document', '/tools/pdf/pdf-to-word.html'),
    ('Lock PDF (Password Protect)', 'Add a password to protect a PDF file', '/tools/pdf/pdf-lock.html'),
    ('Unlock PDF', 'Remove password protection from a PDF file', '/tools/pdf/pdf-unlock.html'),
    ('Sign PDF', 'Add an e-signature to a PDF document', '/tools/pdf/sign-pdf.html'),
    ('Add Watermark to PDF', 'Add a text/image watermark to a PDF', '/tools/pdf/add-watermark.html'),
    ('Rotate PDF', 'Rotate pages inside a PDF file', '/tools/pdf/rotate-pdf.html'),
    ('Reorder PDF Pages', 'Rearrange the page order inside a PDF', '/tools/pdf/reorder-pdf.html'),
    ('Any File to PDF', 'Convert almost any file type into a PDF', '/tools/pdf/any-file-to-pdf.html'),
    ('PDF to Any Format', 'Convert a PDF into another file format', '/tools/pdf/pdf-to-any-format.html'),
    ('Compress Video', 'Reduce video file size online', '/tools/av/video-compress.html'),
    ('Convert Video Format', 'Convert video between formats (MP4, MOV, etc.)', '/tools/av/video-convert.html'),
    ('Trim Video', 'Cut/trim a video online', '/tools/av/video-trim.html'),
    ('Video Editor', 'Edit video online — trim, merge, add text', '/tools/av/video-editor.html'),
    ('Video to MP3', 'Extract audio (MP3) from a video file', '/tools/av/video-to-mp3.html'),
    ('Audio Format Converter', 'Convert audio between formats', '/tools/av/audio-convert.html'),
    ('Merge Audio', 'Combine multiple audio files into one', '/tools/av/audio-merge.html'),
    ('Trim Audio', 'Cut/trim an audio file online', '/tools/av/audio-trim.html'),
    ('Screen Recorder', 'Record your screen online, no install needed', '/tools/av/screen-recorder.html'),
    ('Resume / CV Maker', 'Build a professional resume/CV online for free', '/resume-maker/'),
]

# Section hub pages (title, url slug, short description) — curated from the
# canonical FJA_CAT_MAP / SARK_CAT_MAP / dailyupdates section slugs used by
# generate_all.py, so every URL here is guaranteed to be a real live page.
SECTIONS = [
    ('Latest Government Jobs', 'latest-jobs', 'Newest Sarkari Naukri notifications'),
    ('Results 2026', 'results', 'Latest Sarkari Result declarations'),
    ('Admit Card', 'admit-card', 'Latest exam admit card / hall ticket downloads'),
    ('Answer Key', 'answer-key', 'Latest exam answer keys'),
    ('Offline Application Forms', 'offline-form', 'Government jobs accepting offline/postal applications'),
    ('Upcoming Jobs', 'upcoming-jobs', 'Government jobs expected to open soon'),
    ('Admissions', 'admissions', 'Latest college/university admission notifications'),
    ('10th Pass Government Jobs', '10th-pass-jobs', 'Sarkari jobs for 10th/Matric pass candidates'),
    ('8th Pass Government Jobs', '8th-pass', 'Sarkari jobs for 8th pass candidates'),
    ('12th Pass Government Jobs', '12th-pass-jobs', 'Sarkari jobs for 12th/Intermediate pass candidates'),
    ('Diploma Jobs', 'diploma-jobs', 'Sarkari jobs for Diploma holders'),
    ('ITI Jobs', 'iti-jobs', 'Sarkari jobs for ITI pass candidates'),
    ('B.Tech / B.E. Jobs', 'btech-jobs', 'Engineering graduate government jobs'),
    ('BA Pass / B.Com Jobs', 'ba-pass', 'Sarkari jobs for BA/B.Com/graduate candidates'),
    ('Any Graduate Jobs', 'graduation-jobs', 'Sarkari jobs open to any graduate'),
    ('Post Graduate Jobs', 'post-graduation-jobs', 'Sarkari jobs for post-graduate candidates'),
    ('Railway Jobs', 'railway-jobs', 'Indian Railways recruitment notifications'),
    ('Police & Defence Jobs', 'police-jobs', 'Police, Army and defence recruitment'),
    ('Army & Defence Jobs', 'army-jobs', 'Indian Army and defence recruitment'),
    ('Teaching Jobs', 'teaching-jobs', 'Teacher and faculty recruitment'),
    ('Bank Jobs', 'bank-jobs', 'Bank recruitment (PO, Clerk, SO)'),
    ('Medical / Healthcare Jobs', 'healthcare-jobs', 'Nursing, doctor and healthcare department jobs'),
    ('Jobs with Last Date Reminder', 'last-date-reminder', 'Government jobs closing soon'),
    ('Syllabus & Study Material', 'syllabus', 'Exam syllabus and study material'),
    ('Government Scheme & Yojana', 'govt-scheme-yojna', 'Latest central/state government schemes'),
    ('Important CSC Links', 'important-csc-link', 'Useful official links (Aadhaar, PAN, Passport, etc.)'),
    ('Important CSC PDF Downloads', 'important-csc-pdf', 'Useful downloadable government PDFs/certificates'),
    ('Today Updates', 'today-updates', 'Today\'s Sarkari Naukri updates'),
    ('Top 20 Jobs', 'top-20-jobs', 'Most important current government job openings'),
]

_DU_SECTIONS = [
    ('Govt Scheme & Yojna', 'scheme'),
    ('ImportantCSC PDF', 'pdf'),
    ('ImportantCSC link', 'link'),
    ('Today Updates', 'update'),
]

# State slug -> display name, for /state/{slug}/ and district-suffix stripping.
STATE_NAMES = {
    'andaman-nicobar': 'Andaman & Nicobar', 'andhra-pradesh': 'Andhra Pradesh',
    'arunachal-pradesh': 'Arunachal Pradesh', 'assam': 'Assam', 'bihar': 'Bihar',
    'chandigarh': 'Chandigarh', 'chhattisgarh': 'Chhattisgarh', 'dadra-nh': 'Dadra & Nagar Haveli',
    'daman-diu': 'Daman & Diu', 'delhi': 'Delhi', 'goa': 'Goa', 'gujarat': 'Gujarat',
    'haryana': 'Haryana', 'himachal-pradesh': 'Himachal Pradesh', 'jharkhand': 'Jharkhand',
    'jk': 'Jammu & Kashmir', 'karnataka': 'Karnataka', 'kerala': 'Kerala',
    'lakshadweep': 'Lakshadweep', 'madhya-pradesh': 'Madhya Pradesh', 'maharashtra': 'Maharashtra',
    'manipur': 'Manipur', 'meghalaya': 'Meghalaya', 'mizoram': 'Mizoram', 'nagaland': 'Nagaland',
    'odisha': 'Odisha', 'puducherry': 'Puducherry', 'punjab': 'Punjab', 'rajasthan': 'Rajasthan',
    'sikkim': 'Sikkim', 'tamil-nadu': 'Tamil Nadu', 'telangana': 'Telangana', 'tripura': 'Tripura',
    'uttar-pradesh': 'Uttar Pradesh', 'uttarakhand': 'Uttarakhand', 'west-bengal': 'West Bengal',
}
_STATE_SLUGS_BY_LEN = sorted(STATE_NAMES, key=len, reverse=True)


def _norm_slug(s):
    s = str(s or '').strip().lower()
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')[:80].strip('-')


def slugify(text):
    text = str(text or '').lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:80] or 'job'


# Mirrors generate_all.py's _sr_fingerprint()/registered_slug(): when a job
# has neither _canonical_slug nor slug set (~26% of sarkari_data jobs,
# confirmed by audit), a plain slugify(title) frequently doesn't match the
# real page directory — the page's slug was minted from an EARLIER version
# of the title (e.g. "...Download Answer Key 2026") that has since drifted
# to a new one ("...Download Result 2026"), and without this lookup those
# jobs were silently dropped from the whole index (never findable by the
# chat at all). data/slug-registry.json is the same file generate_all.py
# itself maintains for exactly this reason — read-only here, never written.
_SR_STOP = frozenset((
    'the', 'and', 'for', 'of', 'in', 'to', 'a', 'an', 'with', 'on', 'at', 'by', 'top',
    'sarkari', 'jobs', 'recruitment', 'apply', 'online', 'offline', 'notification',
    'out', 'check', 'details', 'post', 'posts', 'vacancy', 'vacancies', 'form',
    'registration', 'last', 'date', 'here', 'now', 'download', 'pdf', '2024',
    '2025', '2026', '2027', '2028', 'latest', 'govt', 'government', 'result',
    'admit', 'card', 'answer', 'key', 'syllabus', 'exam', 'new', 'all', 'various',
))


def _sr_fingerprint(title):
    t = re.sub(r'[^a-z0-9\s]', ' ', str(title or '').lower())
    toks = [w for w in t.split() if w and w not in _SR_STOP and len(w) > 1]
    return ' '.join(sorted(toks))


def load_slug_registry(root):
    path = os.path.join(root, 'data', 'slug-registry.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def canonical_slug(job, title, slug_registry=None):
    """Mirrors get_canonical_slug()'s Priority 1/2/3 (direct fields, then the
    title-fingerprint slug registry) — only the true last-resort slugify(title)
    guess (which the site itself never actually uses to mint a URL) is not
    replicated further than that."""
    cs = str(job.get('_canonical_slug') or '').strip()
    if cs:
        return _norm_slug(cs)
    raw = str(job.get('slug') or '').strip()
    if raw:
        raw = re.sub(r'^sr_[a-z_]+-', '', raw)
        m = re.search(r'-([0-9a-f]{6,8})$', raw)
        if m and not m.group(1).isdigit():
            raw = raw[:-len(m.group(0))]
        s = _norm_slug(raw)
        if s:
            return s
    if slug_registry:
        fp = _sr_fingerprint(title)
        if fp and fp in slug_registry:
            s = _norm_slug(slug_registry[fp])
            if s:
                return s
    return slugify(title)


def norm_date(d):
    d = str(d or '').strip()
    if not d:
        return ''
    m = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})', d)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', d)
    return d[:10] if m else d[:20]


def parse_age_range(job):
    al = job.get('ageLimit')
    if not isinstance(al, dict):
        return None
    mn = re.match(r'^\d+', str(al.get('minAge', '')).strip())
    mx = re.match(r'^\d+', str(al.get('maxAge', '')).strip())
    if not mn or not mx:
        return None
    mn_i, mx_i = int(mn.group()), int(mx.group())
    if 0 < mn_i <= mx_i <= 75:
        return [mn_i, mx_i]
    return None


def eligibility_text(job):
    parts = []
    for vd in job.get('vacancyDetails', []) or []:
        elig = str(vd.get('eligibility', '') or '').strip()
        if elig and elig not in parts:
            parts.append(elig)
        if len(parts) >= 2:
            break
    return ' | '.join(parts)[:200]


def build_qual_map(root):
    """Reverse-maps job slug -> list of qualification-category tags, reusing
    sections-index.json's own per-job classification instead of re-deriving
    it (that classification already runs daily and is proven correct)."""
    path = os.path.join(root, 'sections-index.json')
    qmap = {}
    if not os.path.exists(path):
        return qmap
    with open(path, encoding='utf-8') as f:
        secs = json.load(f)
    for key, items in (secs or {}).items():
        if key in _NON_QUAL_KEYS or not isinstance(items, list):
            continue
        for it in items:
            slug = str(it.get('slug', '')).strip()
            if not slug:
                continue
            qmap.setdefault(slug, [])
            if key not in qmap[slug]:
                qmap[slug].append(key)
    return qmap


def main():
    cj_path = os.path.join(ROOT, 'Complete_Jobs_Full_Data.json')
    if not os.path.exists(cj_path):
        cj_path = os.path.join(ROOT, 'data', 'Complete_Jobs_Full_Data.json')
    if not os.path.exists(cj_path):
        print('Complete_Jobs_Full_Data.json not found — skipping chat index build')
        return

    with open(cj_path, encoding='utf-8') as f:
        cj = json.load(f)

    _disk_slugs = set()
    jobs_dir = os.path.join(ROOT, 'jobs')
    if os.path.isdir(jobs_dir):
        _disk_slugs = set(os.listdir(jobs_dir))

    slug_registry = load_slug_registry(ROOT)
    qual_map = build_qual_map(ROOT)

    seen_slugs = set()
    out = []

    def add(title, org, category, date, slug, ty='job', age=None, ql=None, q=''):
        if not title or not slug:
            return
        if _disk_slugs and slug not in _disk_slugs:
            return  # never index a link that 404s
        if slug in seen_slugs:
            return
        seen_slugs.add(slug)
        rec = {
            't': title[:160],
            'o': (org or '')[:100],
            'c': (category or '')[:60],
            'd': norm_date(date),
            'u': f'/jobs/{slug}/',
            'ty': ty,
        }
        if age:
            rec['age'] = age
        if ql:
            rec['ql'] = ql
        if q:
            rec['q'] = q[:200]
        out.append(rec)

    # sarkari_data.jobs
    for j in (cj.get('sarkari_data', {}) or {}).get('jobs', []) or []:
        title = str(j.get('title', '')).strip()
        if not title:
            continue
        slug = canonical_slug(j, title, slug_registry)
        date = j.get('important_dates', {}).get('last_date', '') if isinstance(j.get('important_dates'), dict) else ''
        add(title, j.get('organization', ''), j.get('category', ''), date or j.get('postDate', ''), slug,
            ty='job', age=parse_age_range(j), ql=qual_map.get(slug), q=eligibility_text(j))

    # freejobalert_unified.deduped_jobs
    for j in (cj.get('freejobalert_unified', {}) or {}).get('deduped_jobs', []) or []:
        bd = j.get('basic_details', {}) or {}
        title = str(bd.get('job_title', '')).strip()
        if not title:
            continue
        slug = canonical_slug(j, title, slug_registry)
        imp = j.get('important_dates', {}) or {}
        date = imp.get('last_date_to_apply', '') or imp.get('last_date', '')
        qual = j.get('qualification', {}) or {}
        add(title, bd.get('organization_name', ''), j.get('category', ''), date, slug,
            ty='job', ql=qual_map.get(slug), q=str(qual.get('details', ''))[:200])

    # education_jobs.sections[].items[]
    for sec in (cj.get('education_jobs', {}) or {}).get('sections', []) or []:
        cat = sec.get('category', '') or sec.get('title', '')
        for it in sec.get('items', []) or []:
            title = str(it.get('name', '') or it.get('title', '')).strip()
            if not title:
                continue
            slug = canonical_slug(it, title, slug_registry)
            add(title, it.get('organization', ''), cat, it.get('postDate', '') or it.get('date', ''), slug, ty='education')

    job_count = len(out)

    # dailyupdates.json — non-job posts (schemes, official links, PDFs, updates)
    du_path = os.path.join(ROOT, 'dailyupdates.json')
    du_count = 0
    if os.path.exists(du_path):
        with open(du_path, encoding='utf-8') as f:
            du = json.load(f)
        du_secs = du.get('sections', du) if isinstance(du, dict) else du
        du_ty_map = dict(_DU_SECTIONS)
        for sec in du_secs or []:
            sec_title = sec.get('title', '')
            ty = du_ty_map.get(sec_title, 'update')
            for it in sec.get('items', []) or []:
                name = str(it.get('name', '') or '').strip()
                slug = str(it.get('slug', '')).strip()
                if not name or not slug:
                    continue
                before = len(out)
                add(name, '', sec_title, '', slug, ty=ty)
                if len(out) > before:
                    du_count += 1

    # Tools — hardcoded, not in Complete_Jobs_Full_Data.json
    for title, desc, url in TOOLS:
        out.append({'t': title, 'o': '', 'c': 'Tool', 'd': '', 'u': url, 'ty': 'tool', 'q': desc})

    # Section hub pages
    for title, slug, desc in SECTIONS:
        out.append({'t': title, 'o': '', 'c': 'Section', 'd': '', 'u': f'/section/{slug}/', 'ty': 'section', 'q': desc})

    # State-wise job hub pages
    state_count = 0
    state_dir = os.path.join(ROOT, 'state')
    if os.path.isdir(state_dir):
        for slug in sorted(os.listdir(state_dir)):
            name = STATE_NAMES.get(slug)
            if not name or not os.path.isfile(os.path.join(state_dir, slug, 'index.html')):
                continue
            out.append({'t': f'{name} Government Jobs', 'o': '', 'c': 'State', 'd': '',
                        'u': f'/state/{slug}/', 'ty': 'state'})
            state_count += 1

    # District-wise job hub pages
    dist_count = 0
    dist_dir = os.path.join(ROOT, 'district')
    if os.path.isdir(dist_dir):
        for slug in sorted(os.listdir(dist_dir)):
            if not os.path.isfile(os.path.join(dist_dir, slug, 'index.html')):
                continue
            state_slug = next((s for s in _STATE_SLUGS_BY_LEN if slug.endswith('-' + s)), None)
            if not state_slug:
                continue
            dist_name = slug[:-(len(state_slug) + 1)].replace('-', ' ').title()
            state_name = STATE_NAMES[state_slug]
            out.append({'t': f'{dist_name} Govt Jobs ({state_name})', 'o': '', 'c': 'District', 'd': '',
                        'u': f'/district/{slug}/', 'ty': 'district'})
            dist_count += 1

    out_path = os.path.join(ROOT, 'chat-search-index.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'chat-search-index.json: {len(out)} items ({job_count} jobs, {du_count} scheme/link/pdf posts, '
          f'{len(TOOLS)} tools, {len(SECTIONS)} sections, {state_count} states, {dist_count} districts) '
          f'— {os.path.getsize(out_path)/1024:.0f} KB')


if __name__ == '__main__':
    main()
