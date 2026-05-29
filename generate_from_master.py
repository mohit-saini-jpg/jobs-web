#!/usr/bin/env python3
"""
SINGLE SOURCE MIGRATION SCRIPT
================================
Generates all derived JSON files from Complete_Jobs_Full_Data.json
Run this script whenever Complete_Jobs_Full_Data.json is updated.

Usage: python3 generate_from_master.py
"""

import json, re, os, sys

MASTER_FILE = 'Complete_Jobs_Full_Data.json'
DATA_DIR = 'data'

print(f"Loading {MASTER_FILE}...")
with open(MASTER_FILE, encoding='utf-8') as f:
    data = json.load(f)

print(f"  Total records: {data.get('total_records', 'N/A')}")
print(f"  Generated at: {data.get('generated_at', 'N/A')}")

def slugify(t):
    return re.sub(r'^-+|-+$', '', re.sub(r'[^a-z0-9]+', '-', (t or '').lower()))[:120]

def save_json(path, obj):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    size = os.path.getsize(path)
    print(f"  Saved {path} ({size//1024}KB)")

# ── 1. merged_sarkari_data.json ─────────────────────────────────────────────
print("\n[1] Generating merged_sarkari_data.json...")
sk = data['sarkari_data']
sr_cats = {}
for j in sk.get('jobs', []):
    cat = j.get('category', '')
    if cat.startswith('SR_'):
        if cat not in sr_cats:
            sr_cats[cat] = []
        title = (j.get('title') or '').strip()
        slug = j.get('slug') or slugify(title)
        dates = j.get('important_dates') or {}
        last_date = dates.get('last_date') or dates.get('last_date_to_apply') or ''
        sr_cats[cat].append({
            'title': title, 'url': '/data/jobs/' + slug + '/' if slug else '',
            'last_date': last_date, 'apply_mode': j.get('apply_mode', ''),
            'category': cat, 'sequence': j.get('sequence', 0)
        })

merged = {
    'scraped_at': sk.get('scraped_at', ''),
    'total': sk.get('total', 0),
    'jobs': sk.get('jobs', []),
    'summary': {'sarkariresult_categories': sr_cats, 'upcoming_jobs': sk.get('summary', {}).get('upcoming_jobs', 0)}
}
save_json('merged_sarkari_data.json', merged)

# ── 2. state-jobs-data.json ──────────────────────────────────────────────────
print("\n[2] Generating state-jobs-data.json...")
save_json('state-jobs-data.json', data['state_jobs'])

# ── 3. Education_Jobs.json ───────────────────────────────────────────────────
print("\n[3] Generating Education_Jobs.json...")
save_json('Education_Jobs.json', data['education_jobs'])

# ── 4. Qualification_Wise_Jobs.json ─────────────────────────────────────────
print("\n[4] Generating Qualification_Wise_Jobs.json...")
CAT_IDS = {
    '10TH_Pass': '10th-pass', '8TH_Pass': '8th-pass', '12TH_Pass': '12th-pass',
    'Diploma': 'diploma', 'ITI': 'iti', 'B_Tech_BE': 'b-tech-be', 'B_Com': 'b-com',
    'Any_Graduate': 'any-graduate', 'Any_Post_Graduate': 'any-post-graduate',
    'Railway_Jobs': 'railway-jobs', 'Police_Defence': 'police-defence',
    'Teaching_Faculty': 'teaching-faculty', 'Bank_Jobs': 'bank-jobs',
    'Medical_Hospital': 'medical-hospital', 'Last_Date_Reminder': 'last-date-reminder',
    'Latest_Notifications': 'latest-notifications', '4th_Pass': '4th-pass',
    '5th_Pass': '5th-pass', '6th_Pass': '6th-pass', '7th_Pass': '7th-pass',
    '9th_Pass': '9th-pass', 'Intermediate': 'intermediate', 'GNM': 'gnm',
    'ANM': 'anm', 'D_Pharm': 'dpharm', 'DMLT': 'dmlt', 'D_El_Ed': 'deled',
    'D_P_Ed': 'd-p-ed', 'DLT': 'dlt', 'VHSE': 'vhse', 'B_Sc': 'bsc', 'BCA': 'bca',
    'MA': 'ma', 'BBA': 'bba', 'LLB': 'llb', 'B_Ed': 'bed', 'MBBS': 'mbbs',
    'B_Pharma': 'bpharma', 'BAMS': 'bams', 'BDS': 'bds', 'MBA_PGDM': 'mba--pgdm',
    'M_A': 'ma', 'M_Com': 'mcom', 'M_Sc': 'msc', 'M_E_MTech': 'me--mtech',
    'MCA': 'mca', 'M_Ed': 'med', 'MS_MD': 'ms--md', 'M_Pharma': 'mpharma',
    'CA': 'ca', 'CS': 'cs', 'ICWA': 'icwa', 'MPhil_PhD': 'mphil--phd',
}
CAT_NAMES = {k: k.replace('_', ' ').replace('TH ', 'th ').replace(' Pass', 'th Pass') for k in CAT_IDS}
# Override with better names
CAT_NAMES.update({
    '10TH_Pass': '10th Pass', '8TH_Pass': '8th Pass', '12TH_Pass': '12th Pass',
    'B_Tech_BE': 'B.Tech / B.E', 'B_Com': 'B.Com', 'Any_Graduate': 'Any Graduate',
    'Any_Post_Graduate': 'Any Post Graduate', 'Railway_Jobs': 'Railway Jobs',
    'Police_Defence': 'Police / Defence', 'Teaching_Faculty': 'Teaching / Faculty',
    'Bank_Jobs': 'Bank Jobs', 'Medical_Hospital': 'Medical / Hospital',
    'Last_Date_Reminder': 'Last Date Reminder', 'Latest_Notifications': 'Latest Notifications',
    'MBA_PGDM': 'MBA / PGDM', 'M_E_MTech': 'M.E / M.Tech', 'MS_MD': 'MS / MD',
    'MPhil_PhD': 'M.Phil / PhD', 'D_El_Ed': 'D.El.Ed', 'D_Pharm': 'D.Pharm',
    'B_Sc': 'B.Sc', 'B_Ed': 'B.Ed', 'B_Pharma': 'B.Pharma', 'M_Sc': 'M.Sc',
    'M_Ed': 'M.Ed', 'M_Pharma': 'M.Pharma', 'M_A': 'M.A', 'M_Com': 'M.Com',
})

fj = data['freejobalert_categories']
qual_sections = []
for cat_key, jobs in fj.items():
    if not isinstance(jobs, list): continue
    cat_id = CAT_IDS.get(cat_key, cat_key.lower().replace('_', '-'))
    cat_title = CAT_NAMES.get(cat_key, cat_key.replace('_', ' '))
    items = []
    for job in jobs:
        bd = job.get('basic_details', {})
        title = (bd.get('job_title') or bd.get('post_name') or '').strip()
        if not title: continue
        slug = slugify(title)
        dates = job.get('important_dates', {})
        last_date = dates.get('last_date_to_apply') or dates.get('last_date') or ''
        links = job.get('important_links', {})
        apply_url = ''
        if isinstance(links, dict):
            apply_url = links.get('apply_online') or links.get('official_website') or ''
            if isinstance(apply_url, list) and apply_url: apply_url = apply_url[0]
        items.append({
            'name': title, 'url': apply_url or '',
            'date': 'Last Date: ' + last_date if last_date else '',
            'lastDate': last_date,
            'qualification': (job.get('qualification', {}).get('education_qualification', '')
                              if isinstance(job.get('qualification'), dict) else ''),
            'postDate': bd.get('post_date', ''), 'board': bd.get('organization_name', ''),
            'detail': {k: v for k, v in job.items() if k != 'basic_details'}
        })
    if items:
        qual_sections.append({
            'id': cat_id, 'title': cat_title + ' Jobs 2026',
            'category': cat_key, 'type': 'qualification', 'items': items
        })
save_json('Qualification_Wise_Jobs.json', {'sections': qual_sections})

# ── 5. dailyupdates.json ─────────────────────────────────────────────────────
print("\n[5] Generating dailyupdates.json...")
from collections import defaultdict
sk_jobs = data['sarkari_data']['jobs']
cat_buckets = defaultdict(list)
for j in sk_jobs:
    cat = j.get('category', '')
    cat_buckets[cat].append(j)

CAT_TITLES = {
    'LATEST_JOBS NEW': 'Latest Jobs', 'STATE_JOBS': 'State Jobs',
    'CENTRAL_JOBS': 'Central Jobs', 'UPCOMING_JOBS': 'Upcoming Jobs',
    'OFFLINE_FORM': 'Offline Form', 'ADMISSIONS': 'Admissions',
    'SR_Latest_Jobs': 'Latest Jobs', 'SR_Result': 'Result',
    'SR_Admit_Card': 'Admit Card', 'SR_Admission': 'Admission',
    'SR_Answer_Key': 'Answer Key',
}
daily_sections = []
for cat, jobs in cat_buckets.items():
    title = CAT_TITLES.get(cat, cat.replace('_', ' '))
    items = []
    for j in jobs:
        name = (j.get('title') or '').strip()
        if not name: continue
        slug = j.get('slug') or slugify(name)
        items.append({'name': name, 'url': '/data/jobs/' + slug + '/' if slug else '#',
                      'date': (j.get('important_dates') or {}).get('last_date', '')})
    if items:
        daily_sections.append({'id': cat.lower().replace('_', '-'), 'title': title, 'items': items})
save_json('dailyupdates.json', {'sections': daily_sections})

# ── 6. /data/*.json files ────────────────────────────────────────────────────
print(f"\n[6] Generating /data/*.json files...")
CAT_FILE_MAP = {
    'SR_Latest_Jobs': 'sr-latest-jobs', 'SR_Result': 'sr-result',
    'SR_Admit_Card': 'sr-admit-card', 'SR_Admission': 'sr-admission',
    'SR_Answer_Key': 'sr-answer-key', 'OFFLINE_FORM': 'offline-form',
    'UPCOMING_JOBS': 'upcoming-jobs', 'LATEST_JOBS NEW': 'latest-jobs-new',
    'STATE_JOBS': 'state-jobs', 'CENTRAL_JOBS': 'central-jobs', 'ADMISSIONS': 'admissions',
}
data_cat_buckets = defaultdict(list)
for j in sk_jobs:
    cat = j.get('category', '')
    if cat in CAT_FILE_MAP:
        slug = j.get('slug') or slugify(j.get('title', ''))
        data_cat_buckets[cat].append({
            'title': (j.get('title') or '').strip(),
            'url': '/data/jobs/' + slug + '/' if slug else '#',
            'last_date': (j.get('important_dates') or {}).get('last_date', ''),
            'apply_mode': j.get('apply_mode', ''), 'category': cat, 'slug': slug,
        })

for cat, fname in CAT_FILE_MAP.items():
    jobs = data_cat_buckets.get(cat, [])
    save_json(f'{DATA_DIR}/{fname}.json', {'category': cat, 'jobs': jobs, 'total': len(jobs)})

# merged-summary.json
all_sr = []
for cat in CAT_FILE_MAP:
    all_sr.extend(data_cat_buckets.get(cat, []))
save_json(f'{DATA_DIR}/merged-summary.json', {'jobs': all_sr, 'total': len(all_sr)})

QUAL_FILE_MAP = {
    '10TH_Pass': '10th-pass-jobs', '12TH_Pass': '12th-pass-jobs',
    'B_Tech_BE': 'btech-jobs', 'Any_Graduate': 'graduate-jobs',
    'Any_Post_Graduate': 'post-graduate-jobs', 'Bank_Jobs': 'bank-jobs',
    'Medical_Hospital': 'medical-jobs', 'Police_Defence': 'defence-jobs',
    'Railway_Jobs': 'railway-jobs', 'Teaching_Faculty': 'teaching-jobs',
}
for cat_key, fname in QUAL_FILE_MAP.items():
    jobs_raw = fj.get(cat_key, [])
    jobs_out = []
    for job in jobs_raw:
        bd = job.get('basic_details', {})
        title = (bd.get('job_title') or bd.get('post_name') or '').strip()
        if not title: continue
        slug = slugify(title)
        dates = job.get('important_dates', {})
        jobs_out.append({
            'title': title, 'url': '/data/jobs/' + slug + '/' if slug else '#',
            'last_date': dates.get('last_date_to_apply') or dates.get('last_date') or '',
            'category': cat_key, 'slug': slug, 'organization': bd.get('organization_name', ''),
        })
    save_json(f'{DATA_DIR}/{fname}.json', {'category': cat_key, 'jobs': jobs_out, 'total': len(jobs_out)})

print("\n✅ All derived JSON files generated from Complete_Jobs_Full_Data.json!")
print("   No other JSON file needs to be manually maintained.")
