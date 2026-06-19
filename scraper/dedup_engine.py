"""
DEDUP ENGINE — One Recruitment = One URL = One HTML Page
=========================================================
Reads Complete_Jobs_Full_Data.json, detects cross-source duplicates using
multi-signal fingerprinting, merges them into master records, and writes:
  1. Complete_Jobs_Full_Data.json  (in-place, same file, deduped)
  2. dedup_redirect_map.json       (old_slug → canonical_slug for 301s)

HOW IT WORKS
------------
Phase 1 — Extract all records from all sources into a flat list.
Phase 2 — Fingerprint each record using stable fields (not just title).
Phase 3 — Cluster duplicates (union-find).
Phase 4 — Merge each cluster into one master record.
Phase 5 — Write back deduplicated JSON + redirect map.

RUN: python dedup_engine.py [--input FILE] [--dry-run]
"""

import json, re, sys, os, hashlib, argparse
from collections import defaultdict

# ── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_FILE  = os.environ.get("AI_DATA_FILE", "Complete_Jobs_Full_Data.json")
REDIRECT_FILE = "dedup_redirect_map.json"

# Stop words stripped from title fingerprints
STOP = {
    'the','and','for','of','in','to','a','an','with','on','at','by',
    'sarkari','jobs','job','recruitment','apply','online','form','notification',
    'out','check','download','here','link','registration','exam','2024','2025','2026',
    'vacancy','vacancies','post','posts','class','grade','level','advt','no','ntc',
}

# Org name normalization map (abbreviation → canonical)
ORG_NORM = {
    'haryana staff selection commission': 'hssc',
    'haryana staff selection commission (hssc)': 'hssc',
    'staff selection commission': 'ssc',
    'staff selection commission (ssc)': 'ssc',
    'railway recruitment board': 'rrb',
    'union public service commission': 'upsc',
    'institute of banking personnel selection': 'ibps',
    'state bank of india': 'sbi',
    'reserve bank of india': 'rbi',
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def slugify(text):
    t = re.sub(r'[^a-z0-9]+', '-', str(text or '').lower().strip())
    return re.sub(r'-+', '-', t).strip('-')

def norm_text(text):
    """Normalize text for comparison."""
    t = re.sub(r'[^a-z0-9\s]', ' ', str(text or '').lower())
    return ' '.join(w for w in t.split() if w and w not in STOP)

def norm_org(org):
    """Normalize organization name."""
    o = str(org or '').lower().strip()
    # Try full match
    for k, v in ORG_NORM.items():
        if k in o:
            return v
    # Extract abbreviation in parens
    m = re.search(r'\(([A-Z]{2,8})\)', str(org or ''))
    if m:
        return m.group(1).lower()
    # Just first 20 chars normalized
    return re.sub(r'\s+', '', norm_text(o)[:20])

def norm_date(d):
    """Normalize date to YYYY-MM-DD for comparison."""
    if not d:
        return ''
    d = str(d).strip()
    # Try DD/MM/YYYY
    m = re.match(r'(\d{2})[/.-](\d{2})[/.-](\d{4})', d)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # Try DD-Mon-YYYY
    months = {'jan':'01','feb':'02','mar':'03','apr':'04','may':'05','jun':'06',
               'jul':'07','aug':'08','sep':'09','oct':'10','nov':'11','dec':'12'}
    m2 = re.match(r'(\d{1,2})[- ]([a-zA-Z]{3})[- ](\d{4})', d)
    if m2:
        mon = months.get(m2.group(2).lower(), '00')
        return f"{m2.group(3)}-{mon}-{m2.group(1).zfill(2)}"
    return d[:10]

def norm_fee(fee_dict):
    """Normalize fee to a string."""
    if isinstance(fee_dict, dict):
        gen = fee_dict.get('general', fee_dict.get('general_fee', fee_dict.get('General', '')))
        return re.sub(r'[^\d]', '', str(gen or ''))
    return re.sub(r'[^\d]', '', str(fee_dict or ''))

def norm_vacancies(v):
    """Normalize vacancy count."""
    if isinstance(v, (int, float)):
        return str(int(v))
    return re.sub(r'[^\d]', '', str(v or ''))[:6]

def extract_apply_domain(job_rec):
    """Extract apply-online domain for matching."""
    # Try different field paths
    links = (job_rec.get('important_links') or
             job_rec.get('importantLinks') or
             job_rec.get('all_official_links') or {})
    if isinstance(links, dict):
        url = (links.get('apply_online') or links.get('Apply Online') or
               links.get('click_here', [''])[0] if isinstance(links.get('click_here'), list) else links.get('click_here', ''))
    elif isinstance(links, list):
        url = ''
        for lk in links:
            if isinstance(lk, dict):
                lbl = str(lk.get('label','') or lk.get('title','')).lower()
                if 'apply' in lbl:
                    url = lk.get('url', lk.get('link', ''))
                    break
    else:
        url = ''
    m = re.search(r'https?://(?:www\.)?([^/]+)', str(url or ''))
    return m.group(1).lower() if m else ''

def extract_last_date(job_rec):
    """Extract last date from any source format."""
    # FJA
    imp = job_rec.get('important_dates') or job_rec.get('importantDates') or {}
    if isinstance(imp, dict):
        d = (imp.get('last_date_to_apply') or
             imp.get('lastDateApplyOnline') or
             imp.get('Last Date') or
             imp.get('last_date') or '')
        return norm_date(d)
    return ''

def extract_org(job_rec):
    bd = job_rec.get('basic_details') or {}
    org = (bd.get('organization_name') or bd.get('organization') or
           job_rec.get('organization') or bd.get('department') or '')
    return norm_org(org)

def extract_title(job_rec):
    bd = job_rec.get('basic_details') or {}
    return (bd.get('job_title') or bd.get('title') or
            job_rec.get('title') or job_rec.get('name') or
            job_rec.get('post_name') or '')

def extract_vacancy_count(job_rec):
    v = (job_rec.get('totalPost') or
         job_rec.get('total_vacancy') or
         job_rec.get('vacancies') or '')
    if not v:
        bd = job_rec.get('basic_details') or {}
        v = bd.get('total_posts') or bd.get('vacancies') or ''
    return norm_vacancies(v)

def extract_fee(job_rec):
    return norm_fee(
        job_rec.get('applicationFee') or
        job_rec.get('application_fee') or
        (job_rec.get('basic_details') or {}).get('application_fee') or {}
    )

def extract_categories(job_rec, source_key):
    """Get all categories a record belongs to."""
    cats = set()
    c = job_rec.get('category') or job_rec.get('categories') or ''
    if c:
        if isinstance(c, list):
            cats.update(c)
        else:
            cats.add(str(c))
    cats.add(source_key)   # always include its source category
    return cats

def extract_slug(job_rec):
    """Get existing slug or derive from title."""
    bd = job_rec.get('basic_details') or {}
    s = bd.get('slug') or job_rec.get('slug') or job_rec.get('post_slug') or ''
    if not s:
        t = extract_title(job_rec)
        if t:
            s = slugify(t)[:80].rstrip('-')
    return s

# ── FINGERPRINT ───────────────────────────────────────────────────────────────

def fingerprint(job_rec):
    """
    Multi-signal fingerprint for duplicate detection.
    Uses: org + normalized_title_tokens + year + last_date + fee + vacancy.
    Returns a short hash string.
    """
    org = extract_org(job_rec)
    title = extract_title(job_rec)
    year = (re.search(r'20\d{2}', title) or re.search(r'20\d{2}', str(job_rec)))
    year = year.group() if year else ''
    last_date = extract_last_date(job_rec)
    fee = extract_fee(job_rec)
    vacancy = extract_vacancy_count(job_rec)
    apply_domain = extract_apply_domain(job_rec)
    title_norm = norm_text(title)

    # Primary key: org + normalized title tokens
    primary = f"{org}|{title_norm}"
    primary_hash = hashlib.md5(primary.encode()).hexdigest()[:8]

    # Secondary key: org + last_date + fee (catches same exam with different titles)
    if org and last_date and fee:
        secondary = f"{org}|{last_date}|{fee}"
        secondary_hash = hashlib.md5(secondary.encode()).hexdigest()[:8]
    else:
        secondary_hash = None

    # Tertiary: same apply domain + org (very strong signal)
    if org and apply_domain and apply_domain not in ('', 'www', 'sarkariresult.com', 'freejobalert.com'):
        tertiary = f"{org}|{apply_domain}"
        tertiary_hash = hashlib.md5(tertiary.encode()).hexdigest()[:8]
    else:
        tertiary_hash = None

    # NOTE: tertiary (apply domain) removed — too broad, causes false merges
    # (e.g. all BEL jobs sharing same domain would incorrectly merge)
    return primary_hash, secondary_hash, None

# ── UNION-FIND ────────────────────────────────────────────────────────────────

class UnionFind:
    def __init__(self):
        self.parent = {}
    def find(self, x):
        self.parent.setdefault(x, x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, x, y):
        self.parent[self.find(x)] = self.find(y)

# ── FLAT RECORD EXTRACTOR ─────────────────────────────────────────────────────

def extract_all_records(data):
    """
    Flatten all sources into list of (source_key, record).
    Returns: [(source_key, record), ...]
    """
    records = []

    # FJA: dict of category → [records]
    fja = data.get('freejobalert_categories', {})
    if isinstance(fja, dict):
        for cat, items in fja.items():
            if isinstance(items, list):
                for rec in items:
                    rec.setdefault('_source_key', cat)
                    records.append((cat, rec))

    # Sarkari: {jobs: [...]}
    sr = data.get('sarkari_data', {})
    sr_jobs = sr.get('jobs', []) if isinstance(sr, dict) else (sr if isinstance(sr, list) else [])
    for rec in sr_jobs:
        cat = rec.get('category', 'SR_Latest_Jobs')
        rec.setdefault('_source_key', cat)
        records.append((cat, rec))

    # Education: flat list or {jobs: [...]}
    edu = data.get('education_jobs', [])
    if isinstance(edu, dict):
        edu = edu.get('jobs', list(edu.values())[0] if edu else [])
    for rec in edu:
        cat = rec.get('category', 'EDUCATION')
        rec.setdefault('_source_key', cat)
        records.append((cat, rec))

    # State: dict of state → [records] or list
    state = data.get('state_jobs', {})
    if isinstance(state, dict):
        for st, items in state.items():
            if isinstance(items, list):
                for rec in items:
                    rec.setdefault('_source_key', f'STATE_{st.upper()}')
                    records.append((f'STATE_{st.upper()}', rec))
            elif isinstance(items, dict) and 'items' in items:
                for rec in items['items']:
                    rec.setdefault('_source_key', f'STATE_{st.upper()}')
                    records.append((f'STATE_{st.upper()}', rec))
    elif isinstance(state, list):
        for rec in state:
            cat = rec.get('category', 'STATE_JOBS')
            rec.setdefault('_source_key', cat)
            records.append((cat, rec))

    return records

# ── CANONICAL SLUG GENERATOR ──────────────────────────────────────────────────

def make_canonical_slug(records_in_cluster):
    """
    Generate ONE clean slug from the cluster's records.
    Priority: advt_no > most complete title > longest title.
    """
    # Collect all titles
    titles = [extract_title(r) for _, r in records_in_cluster if extract_title(r)]
    if not titles:
        return None

    org = extract_org(records_in_cluster[0][1])
    year = ''
    for t in titles:
        m = re.search(r'20\d{2}', t)
        if m:
            year = m.group()
            break

    # Clean up title: remove source site noise
    NOISE = re.compile(
        r'\s*-?\s*(apply\s+online|apply\s+offline|notification\s+out|'
        r'check\s+details?|online\s+form|registration\s+form|'
        r'notification\s+pdf|apply\s+now|apply\s+here|'
        r'for\s+\d+\s+posts?|last\s+date\s+extended|'
        r'download\s+now|download\s+pdf|walkin|walk.in)\s*', re.I
    )
    # Pick longest title as most informative, then clean it
    best_title = max(titles, key=len)
    clean = NOISE.sub(' ', best_title)
    clean = re.sub(r'\s{2,}', ' ', clean).strip()

    # Ensure year is in slug
    slug = slugify(clean)[:80].rstrip('-')
    if year and year not in slug:
        slug = f"{slug}-{year}"
    slug = slug[:80].rstrip('-')

    return slug

# ── CONTENT MERGER ────────────────────────────────────────────────────────────

def merge_dates(records):
    """Union of all important dates."""
    merged = {}
    for _, rec in records:
        d = rec.get('important_dates') or rec.get('importantDates') or {}
        if isinstance(d, dict):
            for k, v in d.items():
                if v and k not in merged:
                    merged[k] = v
    return merged

def merge_fee(records):
    """Best application fee (most complete)."""
    for _, rec in records:
        f = rec.get('application_fee') or rec.get('applicationFee') or {}
        if f and isinstance(f, dict) and len(f) > 1:
            return f
    # Return any non-empty
    for _, rec in records:
        f = rec.get('application_fee') or rec.get('applicationFee') or {}
        if f:
            return f
    return {}

def merge_links(records):
    """Union of important links."""
    merged = {'apply_online': '', 'official_website': '', 'notification_pdf': ''}
    for _, rec in records:
        links = rec.get('important_links') or rec.get('importantLinks') or {}
        if isinstance(links, dict):
            for k, v in links.items():
                if v and not merged.get(k):
                    merged[k] = v if not isinstance(v, list) else (v[0] if v else '')
        elif isinstance(links, list):
            for lk in links:
                if isinstance(lk, dict):
                    lbl = str(lk.get('label','') or lk.get('title','')).lower()
                    url = lk.get('url', lk.get('link', ''))
                    if 'apply' in lbl and not merged['apply_online']:
                        merged['apply_online'] = url
                    elif 'official' in lbl and 'website' in lbl and not merged['official_website']:
                        merged['official_website'] = url
                    elif ('notification' in lbl or 'pdf' in lbl) and not merged['notification_pdf']:
                        merged['notification_pdf'] = url
    return merged

def best_field(records, *keys):
    """Return the best (longest non-empty) value across records for given keys."""
    best = ''
    for _, rec in records:
        for k in keys:
            v = rec.get(k) or (rec.get('basic_details') or {}).get(k) or ''
            if isinstance(v, (dict, list)):
                v = str(v)
            if len(str(v)) > len(str(best)):
                best = v
    return best

def merge_faqs(records):
    """Union of FAQs, deduped by question."""
    seen_q = set()
    merged = []
    for _, rec in records:
        faqs = rec.get('faq') or []
        for faq in faqs:
            if isinstance(faq, dict):
                q = str(faq.get('question', faq.get('q', ''))).strip()
                qnorm = norm_text(q)[:60]
                if qnorm and qnorm not in seen_q:
                    seen_q.add(qnorm)
                    merged.append(faq)
    return merged

def union_categories(records, source_keys):
    """Union of ALL categories from all source records."""
    cats = set(source_keys)
    for _, rec in records:
        c = rec.get('category') or rec.get('categories') or ''
        if isinstance(c, list):
            cats.update(c)
        elif c:
            cats.add(str(c))
        sk = rec.get('_source_key', '')
        if sk:
            cats.add(sk)
    return list(cats)

def pick_base_record(records):
    """Pick the most complete record as base."""
    def score(rec):
        s = 0
        for k in ['title', 'organization', 'importantDates', 'applicationFee',
                   'vacancyDetails', 'importantLinks', 'faq', 'shortInfo']:
            v = rec.get(k)
            if v:
                s += len(str(v))
        bd = rec.get('basic_details') or {}
        for k in ['job_title', 'organization_name', 'total_posts']:
            v = bd.get(k)
            if v:
                s += len(str(v))
        return s
    return max(records, key=lambda x: score(x[1]))

def create_master_record(cluster_records, canonical_slug, all_categories):
    """
    Merge all records in cluster into ONE master record.
    Preserves original source data but merges:
    - Categories (union of all)
    - Important dates (union)
    - Best title / org / vacancy info
    - All FAQs (deduped)
    - All important links
    - AI content from best record
    """
    base_src, base_rec = pick_base_record(cluster_records)

    import copy
    master = copy.deepcopy(base_rec)

    # Set canonical info
    master['_canonical_slug'] = canonical_slug
    master['_is_master'] = True
    master['_merged_from'] = [extract_slug(r) for _, r in cluster_records]
    master['_source_count'] = len(cluster_records)

    # Union categories
    master['_all_categories'] = all_categories
    master['category'] = all_categories[0] if all_categories else base_rec.get('category', '')

    # Merge dates
    merged_dates = merge_dates(cluster_records)
    if merged_dates:
        if 'important_dates' in master or 'importantDates' in master:
            master['important_dates'] = merged_dates
            master['importantDates'] = merged_dates
        else:
            master['important_dates'] = merged_dates

    # Merge fee
    master_fee = merge_fee(cluster_records)
    if master_fee:
        master['application_fee'] = master_fee
        master['applicationFee'] = master_fee

    # Merge links
    merged_links = merge_links(cluster_records)
    if 'important_links' in master:
        master['important_links'].update(merged_links)
    else:
        master['important_links'] = merged_links

    # Merge FAQs
    merged_faqs = merge_faqs(cluster_records)
    if merged_faqs:
        master['faq'] = merged_faqs

    # Best title
    best_title = best_field(cluster_records, 'title', 'job_title')
    if best_title:
        master['title'] = best_title
        if 'basic_details' in master and isinstance(master['basic_details'], dict):
            master['basic_details']['job_title'] = best_title

    # Best org
    best_org = best_field(cluster_records, 'organization', 'organization_name')
    if best_org:
        master['organization'] = best_org

    # Best vacancy info
    best_vacancy = best_field(cluster_records, 'totalPost', 'total_vacancy', 'vacancies')
    if best_vacancy:
        master['totalPost'] = best_vacancy

    return master

# ── MAIN DEDUP PIPELINE ───────────────────────────────────────────────────────

def run_dedup(data, dry_run=False):
    print("\n[DEDUP] Starting deduplication pipeline...")

    all_records = extract_all_records(data)
    print(f"[DEDUP] Total records extracted: {len(all_records)}")

    # Phase 1: Fingerprint all records
    fp_map = {}   # fp_hash → list of record indices
    uf = UnionFind()

    for i, (src, rec) in enumerate(all_records):
        p_hash, s_hash, t_hash = fingerprint(rec)

        # Register primary hash
        if p_hash not in fp_map:
            fp_map[p_hash] = i
        else:
            uf.union(i, fp_map[p_hash])

        # Register secondary hash (same org + last_date + fee)
        # Guard: require 3+ common title tokens before merging via secondary
        # This prevents "PAU Data Collection" and "PAU Research Assistant" 
        # from merging just because same org + same date
        if s_hash:
            if s_hash not in fp_map:
                fp_map[s_hash] = i
            else:
                other_i = fp_map[s_hash]
                _, other_rec = all_records[other_i]
                ti = set(norm_text(extract_title(rec)).split()[:8])
                to = set(norm_text(extract_title(other_rec)).split()[:8])
                if len(ti & to) >= 3:   # 3+ common tokens = same recruitment
                    uf.union(i, fp_map[s_hash])
                # else: same org+date but different job posts - keep separate

        # Tertiary hash (apply domain) DISABLED - too broad
        # (e.g. all BEL jobs share bel-india.com but are different recruitments)

    # Phase 2: Group clusters
    clusters = defaultdict(list)
    for i, (src, rec) in enumerate(all_records):
        root = uf.find(i)
        clusters[root].append((src, rec))

    dup_clusters = {k: v for k, v in clusters.items() if len(v) > 1}
    single_records = {k: v for k, v in clusters.items() if len(v) == 1}

    print(f"[DEDUP] Clusters: {len(clusters)} total")
    print(f"[DEDUP] Duplicate clusters: {len(dup_clusters)} (will merge)")
    print(f"[DEDUP] Single records: {len(single_records)} (pass-through)")
    total_merged = sum(len(v) for v in dup_clusters.values())
    print(f"[DEDUP] Records that will be merged: {total_merged} → {len(dup_clusters)} master records")
    print(f"[DEDUP] URL reduction: {len(all_records)} → {len(clusters)} unique pages")

    if dry_run:
        # Show sample duplicate clusters
        print("\n[DRY RUN] Sample duplicate clusters:")
        for i, (root, recs) in enumerate(list(dup_clusters.items())[:5]):
            print(f"\n  Cluster {i+1} ({len(recs)} records):")
            for src, rec in recs:
                print(f"    [{src}] {extract_title(rec)[:70]}")
        return None, None

    # Phase 3: Build redirect map and master records
    redirect_map = {}   # old_slug → canonical_slug
    master_records = []

    for root, recs in clusters.items():
        canonical_slug = make_canonical_slug(recs)
        if not canonical_slug:
            continue

        all_cats = union_categories(recs, [s for s, _ in recs])

        if len(recs) == 1:
            # Single record — add canonical slug + categories
            _, rec = recs[0]
            old_slug = extract_slug(rec)
            rec['_canonical_slug'] = canonical_slug
            rec['_all_categories'] = all_cats
            if old_slug and old_slug != canonical_slug:
                redirect_map[old_slug] = canonical_slug
            master_records.append(rec)
        else:
            # Merge cluster
            master = create_master_record(recs, canonical_slug, all_cats)
            for _, rec in recs:
                old_slug = extract_slug(rec)
                if old_slug and old_slug != canonical_slug:
                    redirect_map[old_slug] = canonical_slug
            master_records.append(master)

    print(f"\n[DEDUP] Master records created: {len(master_records)}")
    print(f"[DEDUP] Redirect entries: {len(redirect_map)}")

    return master_records, redirect_map

# ── WRITE BACK ────────────────────────────────────────────────────────────────

def write_deduped(data, master_records, redirect_map, input_file, redirect_file):
    """
    Write deduped records back into the same JSON structure.
    FJA records go back to freejobalert_categories,
    SR records go back to sarkari_data.jobs, etc.
    """
    import copy
    out = copy.deepcopy(data)

    # Separate masters by source origin
    fja_out = defaultdict(list)
    sr_out = []
    edu_out = []
    state_out = defaultdict(list)

    for rec in master_records:
        all_cats = rec.get('_all_categories', [rec.get('_source_key', '')])
        src_key = rec.get('_source_key', '')

        # Determine primary source
        is_fja = any(c in (data.get('freejobalert_categories') or {}) for c in all_cats)
        is_sr = any(c.startswith('SR_') for c in all_cats)
        is_edu = 'EDUCATION' in all_cats or src_key == 'EDUCATION'
        is_state = any(c.startswith('STATE_') for c in all_cats)

        if is_fja:
            # Find the FJA category key
            for c in all_cats:
                if c in (data.get('freejobalert_categories') or {}):
                    fja_out[c].append(rec)
                    break
            else:
                # Use original source key
                fja_out[src_key].append(rec)
        elif is_sr:
            sr_out.append(rec)
        elif is_edu:
            edu_out.append(rec)
        elif is_state:
            for c in all_cats:
                if c.startswith('STATE_'):
                    state_key = c[6:].lower()
                    state_out[state_key].append(rec)
                    break

    # Write back
    if fja_out:
        out['freejobalert_categories'] = dict(fja_out)
    if sr_out:
        if isinstance(out.get('sarkari_data'), dict):
            out['sarkari_data']['jobs'] = sr_out
        else:
            out['sarkari_data'] = {'jobs': sr_out}
    if edu_out:
        out['education_jobs'] = edu_out
    if state_out:
        out['state_jobs'] = dict(state_out)

    # Update counts
    total = len(master_records)
    out['total_records'] = total
    out['dedup_applied'] = True
    out['dedup_redirects'] = len(redirect_map)

    # Write JSON
    tmp = input_file + '.dedup_tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=None)
    os.replace(tmp, input_file)
    print(f"[DEDUP] Wrote deduped JSON → {input_file}")

    # Write redirect map
    with open(redirect_file, 'w', encoding='utf-8') as f:
        json.dump(redirect_map, f, ensure_ascii=False, indent=2)
    print(f"[DEDUP] Wrote redirect map → {redirect_file} ({len(redirect_map)} entries)")


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Dedup engine for topsarkarijobs')
    ap.add_argument('--input',    default=INPUT_FILE,    help='Input JSON file')
    ap.add_argument('--redirects', default=REDIRECT_FILE, help='Output redirect map file')
    ap.add_argument('--dry-run',  action='store_true',   help='Show clusters, do not write')
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: {args.input} not found")
        sys.exit(1)

    print(f"[DEDUP] Loading {args.input}...")
    with open(args.input, encoding='utf-8') as f:
        data = json.load(f)

    master_records, redirect_map = run_dedup(data, dry_run=args.dry_run)

    if not args.dry_run and master_records is not None:
        write_deduped(data, master_records, redirect_map, args.input, args.redirects)
        print(f"\n[DEDUP] Done. Deduplication complete.")

if __name__ == '__main__':
    main()
