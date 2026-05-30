#!/usr/bin/env python3
"""
Complete SEO URL fix for topsarkarijobs.com
Fixes: canonicals, titles, OG tags, hreflang, section page static canonicals,
       sitemap-jobs.xml update
"""
import json, re, os
from pathlib import Path
from datetime import date

BASE = "https://www.topsarkarijobs.com"
TODAY = date.today().strftime('%Y-%m-%d')
site = Path('/home/claude/site/jobs-web-main')
os.chdir(site)

def fix_canonical(content, canonical_url):
    """Replace any canonical (relative or absolute) with correct absolute URL"""
    # Remove existing canonical
    content = re.sub(r'\s*<link[^>]*rel="canonical"[^>]*/>', '', content)
    # Add correct one after <title> or first <meta>
    insert = f'\n  <link rel="canonical" href="{canonical_url}"/>'
    content = re.sub(r'(</title>)', r'\1' + insert, content, count=1)
    return content

def fix_og_url(content, url):
    content = re.sub(
        r'<meta\s+(?:id="[^"]*"\s+)?property="og:url"[^>]*/?>',
        f'<meta property="og:url" content="{url}"/>',
        content
    )
    return content

def fix_hreflang(content, url):
    """Fix all hreflang links to use absolute URL"""
    content = re.sub(
        r'<link[^>]*id="hreflangEn"[^>]*/>',
        f'<link rel="alternate" hreflang="en" href="{url}"/>',
        content
    )
    content = re.sub(
        r'<link[^>]*id="hreflangEnIN"[^>]*/>',
        f'<link rel="alternate" hreflang="en-IN" href="{url}"/>',
        content
    )
    content = re.sub(
        r'<link[^>]*id="hreflangDef"[^>]*/>',
        f'<link rel="alternate" hreflang="x-default" href="{url}"/>',
        content
    )
    return content

# ─── 1. Fix static pages with relative/wrong canonicals ───────────────────────
static_fixes = {
    'about.html': {
        'url': f'{BASE}/about/',
        'title': 'About Us – Top Sarkari Jobs | India No.1 Govt Jobs Portal',
        'desc': 'Top Sarkari Jobs is India\'s trusted platform for latest government job notifications, results, admit cards and online forms. Updated daily.'
    },
    'privacy.html': {
        'url': f'{BASE}/privacy/',
        'title': 'Privacy Policy – Top Sarkari Jobs',
        'desc': 'Privacy Policy of Top Sarkari Jobs. Read how we collect, use and protect your personal information.'
    },
    'terms.html': {
        'url': f'{BASE}/terms/',
        'title': 'Terms and Conditions – Top Sarkari Jobs',
        'desc': 'Terms and Conditions for using Top Sarkari Jobs website. Read our usage policy and disclaimer.'
    },
    'sitemap.html': {
        'url': f'{BASE}/sitemap/',
        'title': 'HTML Sitemap – All Government Jobs, Sections & Pages | Top Sarkari Jobs',
        'desc': 'Complete sitemap of Top Sarkari Jobs – browse all sections, state jobs, qualification-wise jobs, tools and static pages.'
    },
    'tools.html': {
        'url': f'{BASE}/tools/',
        'title': 'Free Online Tools – PDF, Image, Audio/Video Converter | Top Sarkari Jobs',
        'desc': 'Free online tools for govt job forms: JPG to PDF, image resize, compress PDF, passport photo maker, MP4 to MP3. No signup needed.'
    },
    'result.html': {
        'url': f'{BASE}/section/results/',
        'title': 'Government Exam Results 2026 – Sarkari Result | Top Sarkari Jobs',
        'desc': 'Latest government exam results 2026 – SSC, Railway, Banking, Police, UPSC, State PSC results updated daily on Top Sarkari Jobs.'
    },
    'resume-maker.html': {
        'url': f'{BASE}/resume-maker/',
        'title': 'Free Resume / CV Maker 2026 – ATS Friendly | Top Sarkari Jobs',
        'desc': 'Create a free professional resume online. ATS-friendly templates for government job applications. Download as PDF instantly.'
    },
    'helpdesk.html': {
        'url': f'{BASE}/helpdesk/',
        'title': 'Helpdesk & Support – Top Sarkari Jobs',
        'desc': 'Get help and support for Top Sarkari Jobs. Find answers to common questions about government jobs, results and admit cards.'
    },
    'contact.html': {
        'url': f'{BASE}/contact/',
        'title': 'Contact Us – Top Sarkari Jobs',
        'desc': 'Contact the Top Sarkari Jobs team. Reach out for queries about government jobs, partnerships or website feedback.'
    },
    'search.html': {
        'url': f'{BASE}/search/',
        'title': 'Search Government Jobs 2026 – SSC, Railway, Bank, UPSC | Top Sarkari Jobs',
        'desc': 'Search thousands of government jobs 2026. Find latest sarkari naukri by qualification, department, state or keyword.'
    },
    'govt-services.html': {
        'url': f'{BASE}/govt-services/',
        'title': 'Government Services & Schemes 2026 | Top Sarkari Jobs',
        'desc': 'Latest government services, schemes and CSC digital services for Indian citizens. Find Aadhaar, PAN, passport and other govt services.'
    },
    'admit-card.html': {
        'url': f'{BASE}/section/admit-card/',
        'title': 'Government Admit Cards 2026 – Download Exam Hall Tickets | Top Sarkari Jobs',
        'desc': 'Download latest government exam admit cards 2026 – SSC, Railway, IBPS Banking, Police, UPSC, State PSC hall tickets updated daily.'
    },
}

fixed_pages = 0
for fname, fixes in static_fixes.items():
    fpath = site / fname
    if not fpath.exists():
        print(f"  SKIP (not found): {fname}")
        continue
    
    content = fpath.read_text(encoding='utf-8', errors='ignore')
    original = content
    
    # Fix title
    new_title = fixes['title']
    content = re.sub(r'<title[^>]*>.*?</title>', f'<title>{new_title}</title>', content, flags=re.S)
    
    # Fix canonical - remove all existing canonicals first
    content = re.sub(r'[ \t]*<link[^>]*rel=["\']canonical["\'][^>]*/>\n?', '', content)
    # Insert canonical after first <meta charset> or <meta name="viewport">
    content = re.sub(
        r'(<meta[^>]*(?:charset|viewport)[^>]*/>)',
        r'\1\n  <link rel="canonical" href="' + fixes['url'] + '"/>',
        content, count=1
    )
    
    # Fix meta description
    content = re.sub(
        r'<meta[^>]*name=["\']description["\'][^>]*/>',
        f'<meta name="description" content="{fixes["desc"]}"/>',
        content, count=1
    )
    
    # Fix OG url
    url = fixes['url']
    content = re.sub(
        r'<meta[^>]*(?:id="ogUrl"\s+)?property=["\']og:url["\'][^>]*/>',
        f'<meta property="og:url" content="{url}"/>',
        content
    )
    # Fix OG title
    content = re.sub(
        r'<meta[^>]*(?:id="ogTitle"\s+)?property=["\']og:title["\'][^>]*/>',
        f'<meta property="og:title" content="{new_title}"/>',
        content
    )
    # Fix Twitter title
    content = re.sub(
        r'<meta[^>]*(?:id="twTitle"\s+)?name=["\']twitter:title["\'][^>]*/>',
        f'<meta name="twitter:title" content="{new_title}"/>',
        content
    )
    # Fix hreflang absolute
    for lang, val in [('en', url), ('en-IN', url), ('x-default', url)]:
        content = re.sub(
            rf'<link[^>]*hreflang=["\'][lang}["\'][^>]*/>'.replace('{lang}', lang),
            f'<link rel="alternate" hreflang="{lang}" href="{url}"/>',
            content
        )
    
    if content != original:
        fpath.write_text(content, encoding='utf-8')
        fixed_pages += 1
        print(f"  ✅ Fixed: {fname} → {url}")
    else:
        print(f"  — No change: {fname}")

print(f"\nFixed {fixed_pages} static pages")
