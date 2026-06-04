#!/usr/bin/env python3
"""
patch_generator.py — Auto-fix generate_all.py NameError
Runs automatically from GitHub Actions if build_seo_title is undefined.
"""
import re, sys, os

src_path = 'generate_all.py'
if not os.path.exists(src_path):
    print("generate_all.py not found")
    sys.exit(1)

with open(src_path, 'r', encoding='utf-8') as f:
    src = f.read()

if 'build_seo_title' not in src and 'build_meta_desc' not in src:
    print("No patch needed")
    sys.exit(0)

print("Patching generate_all.py...")

# Fix 1: broken double title_tag lines
old_title = (
    "    title_tag = (build_seo_title(title, vacancies, org) + ' | Top Sarkari Jobs')[:60]\n"
    "    title_tag = (_job_part + _BRAND)[:60]"
)
new_title = r"""    _BRAND = ' | Top Sarkari Jobs'
    _vt = vacancies if vacancies and vacancies not in ('\u2014','') else ''
    _vs = ', ' + _vt + ' Posts' if _vt else ''
    _OM = {
        'Delhi Subordinate Services Selection Board':'DSSSB',
        'Staff Selection Commission':'SSC',
        'Union Public Service Commission':'UPSC',
        'Railway Recruitment Board':'RRB',
        'State Bank of India':'SBI',
        'Reserve Bank of India':'RBI',
        'Employees Provident Fund Organisation':'EPFO',
        'Institute of Banking Personnel Selection':'IBPS',
        'All India Institute of Medical Sciences':'AIIMS',
        'National Testing Agency':'NTA',
        'Bharat Sanchar Nigam Limited':'BSNL',
    }
    _os = next((s for f, s in _OM.items() if f.lower() in org.lower()), None)
    if not _os:
        _w = org.split()
        _os = org if len(_w) <= 3 else ' '.join(_w[:3])
    _MAX = 60 - len(_BRAND)
    import re as _re2
    _yr_m = _re2.search(r'20\d\d', title)
    _yr = _yr_m.group() if _yr_m else str(2026)
    _tl = title.lower()
    if _re2.search(r'\b(result|declared|merit list)\b', _tl):
        _jp = _os + ' ' + _yr + ' Result'
    elif _re2.search(r'\b(admit card|hall ticket|call letter)\b', _tl):
        _jp = _os + ' ' + _yr + ' Admit Card'
    elif _re2.search(r'\b(answer key)\b', _tl):
        _jp = _os + ' ' + _yr + ' Answer Key'
    else:
        _jp = _os + ' ' + _yr + ' Recruitment' + _vs
    if len(_jp) > _MAX:
        _jp = _jp[:_MAX - 1].rsplit(' ', 1)[0].rstrip(',-') + '\u2026'
    title_tag = (_jp + _BRAND)[:60]"""

if old_title in src:
    src = src.replace(old_title, new_title, 1)
    print("  Fixed: title_tag double lines")
else:
    # Try regex for slight variations
    src = re.sub(
        r"    title_tag = \(build_seo_title\([^)]+\) \+ '[^']+'\)\[:[0-9]+\]\n    title_tag = \([^)]+\)\[:[0-9]+\]",
        new_title, src, count=1
    )
    print("  Fixed: title_tag (regex)")

# Fix 2: broken meta_desc call
old_meta = "    meta_desc = build_meta_desc(title, org, vacancies, last_d, apply_m, short_info)[:155]"
new_meta = r"""    _si2 = short_info.rstrip('., ').strip()[:100] if short_info else ''
    _base2 = _si2 if _si2 else title[:60].rstrip() + ' Recruitment'
    _parts2 = [_base2]
    if vacancies and vacancies not in ('\u2014', ''):
        _parts2.append(vacancies + ' Posts')
    if last_d and last_d not in ('\u2014', ''):
        _parts2.append('Last Date: ' + last_d)
    meta_desc = ('. '.join(p.rstrip('.') for p in _parts2) + '. Apply at Top Sarkari Jobs.')[:155]"""

if old_meta in src:
    src = src.replace(old_meta, new_meta, 1)
    print("  Fixed: meta_desc call")
else:
    src = re.sub(
        r"    meta_desc = build_meta_desc\([^)]+\)\[:[0-9]+\]",
        new_meta, src, count=1
    )
    print("  Fixed: meta_desc (regex)")

# Verify syntax
import ast
try:
    ast.parse(src)
    with open(src_path, 'w', encoding='utf-8') as f:
        f.write(src)
    print("Patch complete - generate_all.py syntax OK")
except SyntaxError as e:
    print(f"SYNTAX ERROR after patch: {e}")
    sys.exit(1)
