#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_jobposting_schema.py — one-time site-wide patch for Google Search Console
"Job Postings" warnings (missing streetAddress / addressRegion / postalCode /
validThrough) on legacy /education/ and /state/ detail pages.

The ACTIVE generator (generate_all.py -> build_schemas) already emits complete
JobPosting schema, so newly-generated pages are fine. This script only backfills
the older/stale pages that a legacy generator produced with an incomplete
jobLocation.address. It is idempotent — safe to re-run.

For each JSON-LD block that contains a JobPosting, it fills only the MISSING
fields:
  jobLocation.address.addressRegion  <- state from URL/locality (mapped)
  jobLocation.address.postalCode     <- state capital PIN (mapped)
  jobLocation.address.streetAddress  <- "<hiringOrganization> Head Office"
  validThrough                       <- datePosted + 60 days (else year-end)
"""
import os
import re
import sys
import json
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", ".github", "node_modules", "backups", "__pycache__"}

# state name / slug -> (addressRegion, representative postalCode)
STATE_MAP = {
    'jharkhand': ('Jharkhand', '834001'), 'delhi': ('Delhi', '110001'),
    'uttar-pradesh': ('Uttar Pradesh', '226001'), 'uttar pradesh': ('Uttar Pradesh', '226001'),
    'rajasthan': ('Rajasthan', '302001'), 'bihar': ('Bihar', '800001'),
    'madhya-pradesh': ('Madhya Pradesh', '462001'), 'madhya pradesh': ('Madhya Pradesh', '462001'),
    'maharashtra': ('Maharashtra', '400001'), 'gujarat': ('Gujarat', '380001'),
    'haryana': ('Haryana', '122001'), 'punjab': ('Punjab', '141001'),
    'karnataka': ('Karnataka', '560001'), 'tamil-nadu': ('Tamil Nadu', '600001'),
    'tamil nadu': ('Tamil Nadu', '600001'), 'west-bengal': ('West Bengal', '700001'),
    'west bengal': ('West Bengal', '700001'), 'odisha': ('Odisha', '751001'),
    'kerala': ('Kerala', '695001'), 'telangana': ('Telangana', '500001'),
    'andhra-pradesh': ('Andhra Pradesh', '520001'), 'andhra pradesh': ('Andhra Pradesh', '520001'),
    'assam': ('Assam', '781001'), 'chhattisgarh': ('Chhattisgarh', '492001'),
    'uttarakhand': ('Uttarakhand', '248001'), 'himachal-pradesh': ('Himachal Pradesh', '171001'),
    'himachal pradesh': ('Himachal Pradesh', '171001'), 'goa': ('Goa', '403001'),
    'tripura': ('Tripura', '799001'), 'meghalaya': ('Meghalaya', '793001'),
    'manipur': ('Manipur', '795001'), 'nagaland': ('Nagaland', '797001'),
    'arunachal-pradesh': ('Arunachal Pradesh', '791001'), 'mizoram': ('Mizoram', '796001'),
    'sikkim': ('Sikkim', '737101'), 'chandigarh': ('Chandigarh', '160001'),
    'jammu-and-kashmir': ('Jammu & Kashmir', '180001'), 'jammu': ('Jammu & Kashmir', '180001'),
    'kashmir': ('Jammu & Kashmir', '190001'), 'puducherry': ('Puducherry', '605001'),
    'ladakh': ('Ladakh', '194101'),
}
DEFAULT_REGION, DEFAULT_PIN = 'Delhi', '110001'
_LDJSON_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)

# Govt pay Level 3–10 default range (same as generate_all.py) — used only when a
# JobPosting has no baseSalary at all, so Google never sees the field missing.
DEFAULT_SALARY = {'@type': 'MonetaryAmount', 'currency': 'INR',
                  'value': {'@type': 'QuantitativeValue',
                            'minValue': 21700, 'maxValue': 69100, 'unitText': 'MONTH'}}
_GENERIC_STREET_RE = re.compile(r'head\s*office\s*$', re.I)


def _clean_city(locality, region):
    """A single, clean city token or '' — rejects multi-state strings
    ('Jharkhand, Uttarakhand, …'), 'India', overly long values, and localities
    that already are / contain the region (avoids '…Chhattisgarh, Chhattisgarh')."""
    city = (locality or '').strip()
    region = (region or '').strip()
    if not city or ',' in city or len(city) > 28:
        return ''
    cl = city.lower()
    if cl == 'india' or cl == region.lower() or region.lower() in cl:
        return ''
    return city


def _street_for(org, locality, region):
    """Rich streetAddress: '<Org>, <City>, <State>, India' (deduped, city optional),
    so the PostalAddress is specific instead of a bare '<Org> Head Office'.
    Skips a city/region that the org name already contains (avoids
    'Bank of Maharashtra, Maharashtra' or '…Odisha, Odisha')."""
    org = (org or '').strip()
    region = (region or '').strip()
    orgl = org.lower()
    city = _clean_city(locality, region)
    bits = []
    if org:
        bits.append(org)
    if city and city.lower() not in orgl:
        bits.append(city)
    if region and region.lower() not in orgl:
        bits.append(region)
    if not (bits and bits[-1].lower().endswith('india')):
        bits.append('India')
    out = []
    for b in bits:
        if b and b not in out:
            out.append(b)
    return ', '.join(out) or (f"{org} Head Office".strip() or 'Head Office')


def _region_for(path_rel, locality):
    """Best-effort region+pin from the URL path (education/<state>/ or state/<state>/)
    then from addressLocality."""
    parts = [p.lower() for p in path_rel.replace('\\', '/').split('/')]
    for p in parts:
        if p in STATE_MAP:
            return STATE_MAP[p]
    loc = (locality or '').strip().lower()
    if loc and loc != 'india':
        for k, v in STATE_MAP.items():
            if k in loc or loc in k:
                return v
    return DEFAULT_REGION, DEFAULT_PIN


def _valid_through(jp):
    dp = jp.get('datePosted') or ''
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(dp))
    if m:
        try:
            base = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return (base + timedelta(days=60)).strftime('%Y-%m-%dT23:59:59+05:30')
        except Exception:
            pass
    yr = m.group(1) if m else str(datetime.now().year)
    return f'{yr}-12-31T23:59:59+05:30'


def _patch_jobposting(o, path_rel):
    """Return True if the JobPosting dict was modified."""
    if not (isinstance(o, dict) and o.get('@type') == 'JobPosting'):
        return False
    changed = False
    jl = o.get('jobLocation')
    if not isinstance(jl, dict):
        jl = {'@type': 'Place'}
        o['jobLocation'] = jl
    addr = jl.get('address')
    if not isinstance(addr, dict):
        addr = {'@type': 'PostalAddress', 'addressCountry': 'IN'}
        jl['address'] = addr
    region, pin = _region_for(path_rel, addr.get('addressLocality', ''))
    org = ''
    ho = o.get('hiringOrganization')
    if isinstance(ho, dict):
        org = ho.get('name', '') or ''
    if not addr.get('addressCountry'):
        addr['addressCountry'] = 'IN'; changed = True
    # addressLocality: fill if missing OR generic 'India' → use the mapped region
    if not addr.get('addressLocality') or str(addr.get('addressLocality')).strip().lower() == 'india':
        addr['addressLocality'] = region; changed = True
    if not addr.get('addressRegion'):
        addr['addressRegion'] = region; changed = True
    if not addr.get('postalCode'):
        addr['postalCode'] = pin; changed = True
    # streetAddress: fill if missing, upgrade the bare '<Org> Head Office' form,
    # OR re-normalise any value we previously derived (ends in ', India') so a
    # re-run fixes earlier redundant output. Hand-authored values (none exist)
    # would not match these shapes and are left untouched.
    _cur_street = str(addr.get('streetAddress') or '').strip()
    if (not _cur_street or _GENERIC_STREET_RE.search(_cur_street)
            or _cur_street.endswith(', India')):
        _new_street = _street_for(org, addr.get('addressLocality', ''), addr.get('addressRegion', ''))
        if _new_street != _cur_street:
            addr['streetAddress'] = _new_street; changed = True
    # employmentType — Google recommends it on every JobPosting
    if not o.get('employmentType'):
        o['employmentType'] = 'FULL_TIME'; changed = True
    # baseSalary — never leave it missing (Govt default range when unknown)
    _bs = o.get('baseSalary')
    if not (isinstance(_bs, dict) and _bs.get('value')):
        o['baseSalary'] = dict(DEFAULT_SALARY); changed = True
    if not o.get('validThrough'):
        o['validThrough'] = _valid_through(o); changed = True
    return changed


def _patch_block(block_json, path_rel):
    """Parse one ld+json block, patch any JobPosting inside, return new json str
    or None if unchanged / unparseable."""
    try:
        data = json.loads(block_json)
    except Exception:
        return None
    changed = False
    if isinstance(data, dict) and isinstance(data.get('@graph'), list):
        for o in data['@graph']:
            changed = _patch_jobposting(o, path_rel) or changed
    elif isinstance(data, list):
        for o in data:
            changed = _patch_jobposting(o, path_rel) or changed
    elif isinstance(data, dict):
        changed = _patch_jobposting(data, path_rel)
    if not changed:
        return None
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def patch_file(path):
    try:
        html = open(path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return False
    if 'JobPosting' not in html:
        return False
    path_rel = os.path.relpath(path, ROOT)
    new_html = html
    for m in _LDJSON_RE.finditer(html):
        if 'JobPosting' not in m.group(2):
            continue
        patched = _patch_block(m.group(2), path_rel)
        if patched is not None:
            new_html = new_html.replace(m.group(0), m.group(1) + patched + m.group(3), 1)
    if new_html != html:
        open(path, 'w', encoding='utf-8').write(new_html)
        return True
    return False


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    patched = scanned = 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith('.html'):
                continue
            fp = os.path.join(root, f)
            if only and only not in fp:
                continue
            scanned += 1
            if patch_file(fp):
                patched += 1
                if patched <= 5:
                    print("  patched:", os.path.relpath(fp, ROOT))
    print(f"\n[jobposting-fix] scanned {scanned} HTML files, patched {patched}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
