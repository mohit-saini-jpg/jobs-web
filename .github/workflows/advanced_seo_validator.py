#!/usr/bin/env python3
"""
TSJ ADVANCED SEO & 404 VALIDATOR
Pre-deploy validation system for topsarkarijobs.com
Checks: 17 | Mode: disk-only (no HTTP requests)
"""

import os
import re
import sys
import json
import random
import datetime
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Ensure utils module is importable when run from project root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from seo_validator_utils import (
    normalize_slug, slugify, read_file, parse_redirects,
    extract_links, find_index_files, is_page_not_available,
    get_canonical_url, get_page_title, get_meta_description,
)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
ROOT_DIR = os.path.join(os.path.dirname(__file__), '../..')
GITHUB_STEP_SUMMARY = os.environ.get('GITHUB_STEP_SUMMARY', '/tmp/summary.md')
AUTO_FIX = os.environ.get('AUTO_FIX', 'true').lower() == 'true'
BASE_URL = 'https://www.topsarkarijobs.com'

SITEMAP_FILES = [
    'sitemap.xml', 'sitemap-index.xml', 'sitemap-pages.xml',
    'sitemap-sections.xml', 'sitemap-jobs.xml', 'sitemap-categories.xml',
    'sitemap-states.xml', 'sitemap-districts.xml', 'sitemap-education.xml',
    'sitemap-admitcards.xml', 'sitemap-results.xml',
]

CONTENT_FOLDERS = ['jobs', 'state', 'district', 'education', 'category', 'section', 'state-jobs']

LEGACY_PATTERNS = [
    r'view\.html', r'job\.html', r'index\.html',
    r'result\.html', r'search\.html', r'category\.html',
    r'state-job-detail\.html', r'education-detail\.html'
]

PAGE_NOT_AVAILABLE_PATTERNS = [
    r'Page\s+Not\s+Available', r'Job\s+Not\s+Available',
    r'Content\s+Not\s+Found', r'does\s+not\s+exist',
]

validation_results = {
    'critical_errors': [],
    'warnings': [],
    'auto_fixes': [],
    'checks': []
}

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def url_to_filepath(url):
    """Convert sitemap URL to file system path"""
    path = url.replace('https://www.topsarkarijobs.com', '') \
               .replace('https://topsarkarijobs.com', '') \
               .lstrip('/')
    if path.endswith('/') or not path:
        path = os.path.join(path, 'index.html')
    return os.path.join(ROOT_DIR, path)


def url_to_slug(url):
    """Extract last path segment as slug"""
    path = url.replace('https://www.topsarkarijobs.com', '').strip('/')
    parts = path.split('/')
    return parts[-1] if parts else ''


def _parse_sitemap_urls(sitemap_path):
    """Parse a sitemap XML file and return list of <loc> URLs."""
    urls = []
    if not os.path.exists(sitemap_path):
        return urls
    try:
        tree = ET.parse(sitemap_path)
        root = tree.getroot()
        ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        # Try with namespace first
        locs = root.findall(f'.//{ns}loc')
        if not locs:
            locs = root.findall('.//loc')
        for loc in locs:
            if loc.text:
                urls.append(loc.text.strip())
    except Exception as e:
        validation_results['warnings'].append(f"Could not parse {sitemap_path}: {e}")
    return urls


def _add_check(name, critical, failed, details='', count=None):
    """Record a check result."""
    validation_results['checks'].append({
        'name': name,
        'critical': critical,
        'failed': failed,
        'details': details,
        'count': count,
    })


# ---------------------------------------------------------------------------
# CHECK 1: Sitemap URL → file existence
# ---------------------------------------------------------------------------
def check_1_sitemap_url_validation():
    """Parse all sitemaps; verify each URL has a file on disk."""
    all_urls = []
    missing_files = []

    for sitemap_name in SITEMAP_FILES:
        sitemap_path = os.path.join(ROOT_DIR, sitemap_name)
        urls = _parse_sitemap_urls(sitemap_path)
        for url in urls:
            all_urls.append(url)
            # Skip sitemap-index entries that just reference other sitemaps
            if 'sitemap' in url.split('/')[-1] and url.endswith('.xml'):
                continue
            filepath = url_to_filepath(url)
            if not os.path.exists(filepath):
                missing_files.append({
                    'url': url,
                    'expected_file': filepath,
                    'sitemap': sitemap_name,
                })

    if missing_files:
        sample = missing_files[:10]
        detail_lines = [f"  - {m['url']} (expected: {m['expected_file']})" for m in sample]
        if len(missing_files) > 10:
            detail_lines.append(f"  ... and {len(missing_files) - 10} more")
        validation_results['warnings'].append(
            f"CHECK 1: {len(missing_files)} sitemap URLs have no file on disk:\n" +
            "\n".join(detail_lines)
        )
        _add_check('Sitemap URL Validation', critical=False, failed=True,
                   details=f"{len(missing_files)} missing files", count=len(all_urls))
    else:
        _add_check('Sitemap URL Validation', critical=True, failed=False,
                   details='All sitemap URLs have corresponding files', count=len(all_urls))

    return all_urls


# ---------------------------------------------------------------------------
# CHECK 2: Page content validation
# ---------------------------------------------------------------------------
def check_2_page_content_validation(all_urls):
    """Check title, meta description, canonical for sampled URLs."""
    # Skip XML/sitemap URLs — they don't have HTML meta tags
    html_urls = [u for u in all_urls if not re.search(r'sitemap[^/]*\.xml', u)]
    sample_urls = html_urls[:200]
    errors = []

    for url in sample_urls:
        filepath = url_to_filepath(url)
        if not os.path.exists(filepath):
            continue
        content = read_file(filepath)
        page_errors = []

        title = get_page_title(content)
        if not title or len(title.strip()) < 5:
            page_errors.append('missing/short title')

        if '<meta name="description" content="' not in content:
            page_errors.append('missing meta description')

        if '<link rel="canonical"' not in content:
            page_errors.append('missing canonical')

        if page_errors:
            errors.append(f"  - {url}: {', '.join(page_errors)}")

    if errors:
        sample = errors[:10]
        if len(errors) > 10:
            sample.append(f"  ... and {len(errors) - 10} more")
        validation_results['critical_errors'].append(
            f"CHECK 2: {len(errors)} pages have content issues:\n" + "\n".join(sample)
        )
        _add_check('Page Content Validation', critical=True, failed=True,
                   details=f"{len(errors)} pages with content issues", count=len(sample_urls))
    else:
        _add_check('Page Content Validation', critical=True, failed=False,
                   details=f'All {len(sample_urls)} sampled pages OK', count=len(sample_urls))


# ---------------------------------------------------------------------------
# CHECK 3: Canonical validation
# ---------------------------------------------------------------------------
def check_3_canonical_validation(all_urls):
    """Verify canonical URLs are clean (no .html, no legacy patterns, https://)."""
    # Skip XML/sitemap URLs — they don't have canonical tags
    html_urls = [u for u in all_urls if not re.search(r'sitemap[^/]*\.xml', u)]
    sample_urls = html_urls[:200]
    invalid = []

    for url in sample_urls:
        filepath = url_to_filepath(url)
        if not os.path.exists(filepath):
            continue
        content = read_file(filepath)
        canonical = get_canonical_url(content)
        if not canonical:
            invalid.append(f"  - {url}: no canonical tag")
            continue

        issues = []
        for pattern in LEGACY_PATTERNS:
            if re.search(pattern, canonical):
                issues.append(f"legacy pattern '{pattern}'")
        if not canonical.startswith('https://'):
            issues.append('does not start with https://')
        if canonical.endswith('.html'):
            issues.append('ends with .html')

        if issues:
            invalid.append(f"  - {url}: canonical='{canonical}' [{'; '.join(issues)}]")

    if invalid:
        sample = invalid[:10]
        if len(invalid) > 10:
            sample.append(f"  ... and {len(invalid) - 10} more")
        validation_results['critical_errors'].append(
            f"CHECK 3: {len(invalid)} pages have invalid canonicals:\n" + "\n".join(sample)
        )
        _add_check('Canonical Validation', critical=True, failed=True,
                   details=f"{len(invalid)} invalid canonicals", count=len(sample_urls))
    else:
        _add_check('Canonical Validation', critical=True, failed=False,
                   details=f'All {len(sample_urls)} canonicals OK', count=len(sample_urls))


# ---------------------------------------------------------------------------
# CHECK 4: Legacy URL detection
# ---------------------------------------------------------------------------
def check_4_legacy_url_detection():
    """Scan JS files, root HTML files, sitemaps for legacy URL patterns."""
    found = []

    # Root-level .html files
    for fname in os.listdir(ROOT_DIR):
        if fname.endswith('.html') or fname.endswith('.js'):
            fpath = os.path.join(ROOT_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            content = read_file(fpath)
            for pattern in LEGACY_PATTERNS:
                if re.search(pattern, content):
                    found.append(f"  - {fname}: pattern '{pattern}'")
                    break  # one report per file

    # Sitemaps
    for sitemap_name in SITEMAP_FILES:
        fpath = os.path.join(ROOT_DIR, sitemap_name)
        if not os.path.exists(fpath):
            continue
        content = read_file(fpath)
        for pattern in LEGACY_PATTERNS:
            if re.search(pattern, content):
                found.append(f"  - {sitemap_name}: pattern '{pattern}'")
                break

    if found:
        validation_results['warnings'].append(
            f"CHECK 4: Legacy URL patterns found in {len(found)} files:\n" + "\n".join(found[:20])
        )
        _add_check('Legacy URL Detection', critical=False, failed=True,
                   details=f"{len(found)} files contain legacy patterns", count=len(found))
    else:
        _add_check('Legacy URL Detection', critical=False, failed=False,
                   details='No legacy URL patterns found')


# ---------------------------------------------------------------------------
# CHECK 5: Orphan page detection
# ---------------------------------------------------------------------------
def check_5_orphan_page_detection():
    """Find pages on disk with no corresponding sitemap/index entry."""
    known_slugs = set()

    # From sitemaps
    for sitemap_name in SITEMAP_FILES:
        sitemap_path = os.path.join(ROOT_DIR, sitemap_name)
        for url in _parse_sitemap_urls(sitemap_path):
            slug = url_to_slug(url)
            if slug:
                known_slugs.add(slug)

    # From sections-index.json
    sections_path = os.path.join(ROOT_DIR, 'sections-index.json')
    if os.path.exists(sections_path):
        try:
            with open(sections_path, encoding='utf-8') as f:
                sections = json.load(f)
            for category, items in sections.items():
                for item in items:
                    slug = item.get('slug', '')
                    if slug:
                        known_slugs.add(slug)
        except Exception as e:
            validation_results['warnings'].append(f"CHECK 5: Could not read sections-index.json: {e}")

    # From data/jobs-index.json
    jobs_index_path = os.path.join(ROOT_DIR, 'data', 'jobs-index.json')
    if os.path.exists(jobs_index_path):
        try:
            with open(jobs_index_path, encoding='utf-8') as f:
                jobs_index = json.load(f)
            items = jobs_index if isinstance(jobs_index, list) else jobs_index.values() if isinstance(jobs_index, dict) else []
            for item in items:
                if isinstance(item, dict):
                    slug = item.get('slug') or item.get('job_slug', '')
                    if slug:
                        known_slugs.add(slug)
        except Exception:
            pass

    # Scan disk
    orphans = []
    for folder in CONTENT_FOLDERS:
        folder_path = os.path.join(ROOT_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        for entry in os.scandir(folder_path):
            if entry.is_dir():
                disk_slug = entry.name
                if disk_slug not in known_slugs:
                    orphans.append(f"  - {folder}/{disk_slug}")

    if orphans:
        validation_results['warnings'].append(
            f"CHECK 5: {len(orphans)} orphan pages found (on disk, not in sitemap/index):\n" +
            "\n".join(orphans[:20]) +
            (f"\n  ... and {len(orphans) - 20} more" if len(orphans) > 20 else "")
        )
        _add_check('Orphan Page Detection', critical=False, failed=True,
                   details=f"{len(orphans)} orphan pages", count=len(orphans))
    else:
        _add_check('Orphan Page Detection', critical=False, failed=False,
                   details='No orphan pages found')


# ---------------------------------------------------------------------------
# CHECK 6: Index file existence (ALL files, no sampling)
# ---------------------------------------------------------------------------
def check_6_index_file_existence():
    """Verify every content subfolder has a non-empty index.html."""
    missing_indexes = []

    for folder in CONTENT_FOLDERS:
        folder_path = os.path.join(ROOT_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        for entry in os.scandir(folder_path):
            if entry.is_dir():
                index_path = os.path.join(entry.path, 'index.html')
                if not os.path.exists(index_path):
                    missing_indexes.append(f"  - {folder}/{entry.name}/index.html (missing)")
                elif os.path.getsize(index_path) < 100:
                    missing_indexes.append(f"  - {folder}/{entry.name}/index.html (too small: {os.path.getsize(index_path)} bytes)")

    if missing_indexes:
        sample = missing_indexes[:20]
        if len(missing_indexes) > 20:
            sample.append(f"  ... and {len(missing_indexes) - 20} more")
        validation_results['critical_errors'].append(
            f"CHECK 6: {len(missing_indexes)} content folders missing/empty index.html:\n" + "\n".join(sample)
        )
        _add_check('Index File Existence', critical=True, failed=True,
                   details=f"{len(missing_indexes)} missing/empty index files", count=len(missing_indexes))
    else:
        _add_check('Index File Existence', critical=True, failed=False,
                   details='All content folders have valid index.html')


# ---------------------------------------------------------------------------
# CHECK 7: Page Not Available detection
# ---------------------------------------------------------------------------
def check_7_page_not_available(all_urls):
    """Detect pages that render 'Page Not Available' or similar error messages."""
    sample_urls = all_urls[:200]
    bad_pages = []

    for url in sample_urls:
        filepath = url_to_filepath(url)
        if not os.path.exists(filepath):
            continue
        content = read_file(filepath)
        content_no_script = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL)

        found_issue = False
        for pattern in PAGE_NOT_AVAILABLE_PATTERNS:
            if re.search(pattern, content_no_script, re.IGNORECASE):
                bad_pages.append(f"  - {url}: matched '{pattern}'")
                found_issue = True
                break

        if not found_issue:
            title = get_page_title(content)
            if title and re.search(r'\b404\b|Not Found', title, re.IGNORECASE):
                bad_pages.append(f"  - {url}: title contains 404/Not Found")

    if bad_pages:
        sample = bad_pages[:10]
        if len(bad_pages) > 10:
            sample.append(f"  ... and {len(bad_pages) - 10} more")
        validation_results['critical_errors'].append(
            f"CHECK 7: {len(bad_pages)} pages show 'Page Not Available':\n" + "\n".join(sample)
        )
        _add_check('Page Not Available', critical=True, failed=True,
                   details=f"{len(bad_pages)} pages with error content", count=len(sample_urls))
    else:
        _add_check('Page Not Available', critical=True, failed=False,
                   details=f'No error pages in {len(sample_urls)} sampled URLs', count=len(sample_urls))


# ---------------------------------------------------------------------------
# CHECK 8: Redirect loop detection
# ---------------------------------------------------------------------------
def check_8_redirect_loop_detection():
    """Detect circular redirect chains in _redirects file."""
    redirects_path = os.path.join(ROOT_DIR, '_redirects')
    redirects = parse_redirects(redirects_path)

    if not redirects:
        _add_check('Redirect Loop Detection', critical=True, failed=False,
                   details='No _redirects file or empty')
        return

    # Sample first 500 redirects
    sources = list(redirects.keys())[:500]
    loops = []

    for source in sources:
        visited = set()
        current = source
        chain = [current]

        while current in redirects:
            if current in visited:
                loops.append(f"  - Loop detected: {' → '.join(chain)}")
                break
            visited.add(current)
            current = redirects[current]
            chain.append(current)

    if loops:
        sample = loops[:10]
        if len(loops) > 10:
            sample.append(f"  ... and {len(loops) - 10} more")
        validation_results['critical_errors'].append(
            f"CHECK 8: {len(loops)} redirect loops found:\n" + "\n".join(sample)
        )
        _add_check('Redirect Loop Detection', critical=True, failed=True,
                   details=f"{len(loops)} redirect loops", count=len(sources))
    else:
        _add_check('Redirect Loop Detection', critical=True, failed=False,
                   details=f'No loops in {len(sources)} redirects checked', count=len(sources))


# ---------------------------------------------------------------------------
# CHECK 9: Internal link validation
# ---------------------------------------------------------------------------
def check_9_internal_link_validation():
    """Check internal links in sampled jobs pages."""
    jobs_folder = os.path.join(ROOT_DIR, 'jobs')
    if not os.path.isdir(jobs_folder):
        _add_check('Internal Link Validation', critical=False, failed=False,
                   details='jobs/ folder not found')
        return

    all_job_indexes = find_index_files(jobs_folder)
    sample_files = random.sample(all_job_indexes, min(50, len(all_job_indexes)))
    broken_links = []

    for filepath in sample_files:
        content = read_file(filepath)
        links = extract_links(content)
        base_dir = os.path.dirname(filepath)

        for link in links:
            # Skip external, anchors, javascript
            if link.startswith('http') or link.startswith('#') or link.startswith('javascript:'):
                continue
            if link.startswith('/'):
                target = os.path.join(ROOT_DIR, link.lstrip('/'))
            else:
                target = os.path.join(base_dir, link)

            # Normalize: if it ends in / or no extension, check for index.html
            target = os.path.normpath(target)
            if not os.path.exists(target):
                # Try as directory/index.html
                if not os.path.exists(os.path.join(target, 'index.html')):
                    rel = os.path.relpath(filepath, ROOT_DIR)
                    broken_links.append(f"  - [{rel}] → {link}")

    if broken_links:
        sample = broken_links[:15]
        if len(broken_links) > 15:
            sample.append(f"  ... and {len(broken_links) - 15} more")
        validation_results['warnings'].append(
            f"CHECK 9: {len(broken_links)} broken internal links found:\n" + "\n".join(sample)
        )
        _add_check('Internal Link Validation', critical=False, failed=True,
                   details=f"{len(broken_links)} broken links in {len(sample_files)} files sampled", count=len(sample_files))
    else:
        _add_check('Internal Link Validation', critical=False, failed=False,
                   details=f'No broken links in {len(sample_files)} files sampled', count=len(sample_files))


# ---------------------------------------------------------------------------
# CHECK 10: Duplicate URL detection
# ---------------------------------------------------------------------------
def check_10_duplicate_url_detection():
    """Find duplicate URLs across all sitemaps after normalization."""
    all_urls = []
    for sitemap_name in SITEMAP_FILES:
        sitemap_path = os.path.join(ROOT_DIR, sitemap_name)
        all_urls.extend(_parse_sitemap_urls(sitemap_path))

    normalized = {}
    for url in all_urls:
        norm = url.rstrip('/').replace('/index.html', '')
        normalized.setdefault(norm, []).append(url)

    duplicates = {k: v for k, v in normalized.items() if len(v) > 1}

    if duplicates:
        lines = [f"  - {k}: {v}" for k, v in list(duplicates.items())[:10]]
        if len(duplicates) > 10:
            lines.append(f"  ... and {len(duplicates) - 10} more")
        validation_results['warnings'].append(
            f"CHECK 10: {len(duplicates)} duplicate URLs in sitemaps:\n" + "\n".join(lines)
        )
        _add_check('Duplicate URL Detection', critical=False, failed=True,
                   details=f"{len(duplicates)} duplicate normalized URLs", count=len(all_urls))
    else:
        _add_check('Duplicate URL Detection', critical=False, failed=False,
                   details=f'No duplicates in {len(all_urls)} sitemap URLs', count=len(all_urls))


# ---------------------------------------------------------------------------
# CHECK 11: robots.txt validation
# ---------------------------------------------------------------------------
def check_11_robots_validation():
    """Validate robots.txt for correct sitemap directive and disallow rules."""
    robots_path = os.path.join(ROOT_DIR, 'robots.txt')
    important_folders = ['/jobs/', '/state/', '/education/', '/category/', '/section/', '/district/']

    if not os.path.exists(robots_path):
        validation_results['warnings'].append("CHECK 11: robots.txt not found")
        _add_check('Robots.txt Validation', critical=False, failed=True,
                   details='robots.txt not found')
        return

    content = read_file(robots_path)
    issues = []
    critical_issues = []

    if 'Sitemap:' not in content:
        issues.append('Missing Sitemap: directive')

    # Check for wrongly disallowed important folders
    disallowed = re.findall(r'Disallow:\s*(/[^\s]*)', content)
    for folder in important_folders:
        for rule in disallowed:
            if rule.rstrip('/') == folder.rstrip('/') or rule == folder:
                critical_issues.append(f"Important folder disallowed: {folder}")

    # Check legacy pages should be disallowed
    legacy_pages = ['/view.html', '/job.html', '/search.html']
    for page in legacy_pages:
        if page not in content:
            issues.append(f"Should Disallow: {page} (recommended)")

    if critical_issues:
        validation_results['critical_errors'].append(
            "CHECK 11 (CRITICAL): robots.txt blocks important folders:\n" +
            "\n".join(f"  - {i}" for i in critical_issues)
        )
        _add_check('Robots.txt Validation', critical=True, failed=True,
                   details='; '.join(critical_issues))
    elif issues:
        validation_results['warnings'].append(
            "CHECK 11: robots.txt issues:\n" + "\n".join(f"  - {i}" for i in issues)
        )
        _add_check('Robots.txt Validation', critical=False, failed=True,
                   details='; '.join(issues))
    else:
        _add_check('Robots.txt Validation', critical=False, failed=False,
                   details='robots.txt looks good')


# ---------------------------------------------------------------------------
# CHECK 12: Sitemap cleanliness
# ---------------------------------------------------------------------------
def check_12_sitemap_cleanliness():
    """Ensure no .html URLs or ?id= params in content sitemaps."""
    bad_urls = []

    for sitemap_name in SITEMAP_FILES:
        # sitemap-index.xml references other sitemaps — skip .xml check there
        is_index = sitemap_name == 'sitemap-index.xml'
        sitemap_path = os.path.join(ROOT_DIR, sitemap_name)
        urls = _parse_sitemap_urls(sitemap_path)

        for url in urls:
            # Allow sitemap*.xml references in sitemap-index
            if is_index and 'sitemap' in url.split('/')[-1]:
                continue
            issues = []
            if '.html' in url:
                issues.append('.html in URL')
            if '?id=' in url or '?slug=' in url or '?job=' in url:
                issues.append('query parameter in URL')
            if issues:
                bad_urls.append(f"  - [{sitemap_name}] {url}: {', '.join(issues)}")

    if bad_urls:
        sample = bad_urls[:15]
        if len(bad_urls) > 15:
            sample.append(f"  ... and {len(bad_urls) - 15} more")
        validation_results['critical_errors'].append(
            f"CHECK 12: {len(bad_urls)} legacy/dirty URLs in sitemaps:\n" + "\n".join(sample)
        )
        _add_check('Sitemap Cleanliness', critical=True, failed=True,
                   details=f"{len(bad_urls)} dirty sitemap URLs", count=len(bad_urls))
    else:
        _add_check('Sitemap Cleanliness', critical=True, failed=False,
                   details='All sitemap URLs are clean')


# ---------------------------------------------------------------------------
# CHECK 13: Data index validation (ALL, no sampling)
# ---------------------------------------------------------------------------
def check_13_data_index_validation():
    """Verify every slug in sections-index.json has a jobs/{slug}/index.html."""
    missing_pages = []

    # sections-index.json
    sections_path = os.path.join(ROOT_DIR, 'sections-index.json')
    if os.path.exists(sections_path):
        try:
            with open(sections_path, encoding='utf-8') as f:
                sections = json.load(f)
            for category, items in sections.items():
                for item in items:
                    slug = item.get('slug', '')
                    if not slug:
                        continue
                    page_path = f"jobs/{slug}/index.html"
                    if not os.path.exists(os.path.join(ROOT_DIR, page_path)):
                        missing_pages.append((slug, category))
        except Exception as e:
            validation_results['warnings'].append(f"CHECK 13: Could not parse sections-index.json: {e}")

    # data/jobs-index.json (if exists)
    jobs_index_path = os.path.join(ROOT_DIR, 'data', 'jobs-index.json')
    if os.path.exists(jobs_index_path):
        try:
            with open(jobs_index_path, encoding='utf-8') as f:
                jobs_index = json.load(f)
            items = jobs_index if isinstance(jobs_index, list) else list(jobs_index.values()) if isinstance(jobs_index, dict) else []
            for item in items:
                if not isinstance(item, dict):
                    continue
                slug = item.get('slug') or item.get('job_slug', '')
                if not slug:
                    continue
                page_path = f"jobs/{slug}/index.html"
                if not os.path.exists(os.path.join(ROOT_DIR, page_path)):
                    # Avoid duplicating what sections-index already caught
                    if (slug, 'data/jobs-index') not in missing_pages:
                        missing_pages.append((slug, 'data/jobs-index'))
        except Exception as e:
            validation_results['warnings'].append(f"CHECK 13: Could not parse data/jobs-index.json: {e}")

    if missing_pages:
        report_sample = missing_pages[:30]
        lines = [f"  - jobs/{slug}/index.html [category: {cat}]" for slug, cat in report_sample]
        if len(missing_pages) > 30:
            lines.append(f"  ... and {len(missing_pages) - 30} more")
        validation_results['warnings'].append(
            f"CHECK 13: {len(missing_pages)} slugs in index have no HTML page:\n" + "\n".join(lines)
        )
        _add_check('Data Index Validation', critical=False, failed=True,
                   details=f"{len(missing_pages)} missing job pages", count=len(missing_pages))
    else:
        _add_check('Data Index Validation', critical=False, failed=False,
                   details='All index slugs have corresponding HTML pages')

    return missing_pages


# ---------------------------------------------------------------------------
# CHECK 14: Category page validation
# ---------------------------------------------------------------------------
def check_14_category_page_validation():
    """Validate category/education/district/state/section pages for basic SEO."""
    folders = ['category', 'education', 'district', 'state', 'section']
    issues = []
    checked = 0

    for folder in folders:
        folder_path = os.path.join(ROOT_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        for entry in os.scandir(folder_path):
            if not entry.is_dir():
                continue
            index_path = os.path.join(entry.path, 'index.html')
            if not os.path.exists(index_path):
                continue
            checked += 1
            content = read_file(index_path)
            page_issues = []

            if not get_page_title(content):
                page_issues.append('no title')
            if not get_meta_description(content):
                page_issues.append('no meta description')
            if not get_canonical_url(content):
                page_issues.append('no canonical')
            if is_page_not_available(index_path):
                page_issues.append('Page Not Available')
            if os.path.getsize(index_path) < 500:
                page_issues.append(f'too small ({os.path.getsize(index_path)} bytes)')

            if page_issues:
                issues.append(f"  - {folder}/{entry.name}: {', '.join(page_issues)}")

    if issues:
        sample = issues[:20]
        if len(issues) > 20:
            sample.append(f"  ... and {len(issues) - 20} more")
        validation_results['warnings'].append(
            f"CHECK 14: {len(issues)} category/section pages have issues:\n" + "\n".join(sample)
        )
        _add_check('Category Page Validation', critical=False, failed=True,
                   details=f"{len(issues)} pages with issues out of {checked} checked", count=checked)
    else:
        _add_check('Category Page Validation', critical=False, failed=False,
                   details=f'All {checked} category/section pages OK', count=checked)


# ---------------------------------------------------------------------------
# CHECK 15: Schema markup validation
# ---------------------------------------------------------------------------
def check_15_schema_validation():
    """Verify JobPosting JSON-LD schema in sampled job pages."""
    jobs_folder = os.path.join(ROOT_DIR, 'jobs')
    if not os.path.isdir(jobs_folder):
        _add_check('Schema Markup Validation', critical=False, failed=False,
                   details='jobs/ folder not found')
        return

    all_job_indexes = find_index_files(jobs_folder)
    sample_files = random.sample(all_job_indexes, min(20, len(all_job_indexes)))
    schema_issues = []

    for filepath in sample_files:
        content = read_file(filepath)
        ld_blocks = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            content, re.DOTALL | re.IGNORECASE
        )
        rel = os.path.relpath(filepath, ROOT_DIR)

        if not ld_blocks:
            schema_issues.append(f"  - {rel}: no JSON-LD schema found")
            continue

        found_job_posting = False
        for block in ld_blocks:
            try:
                schema = json.loads(block.strip())
                schemas = schema if isinstance(schema, list) else [schema]
                for s in schemas:
                    if s.get('@type') == 'JobPosting':
                        found_job_posting = True
                        missing_fields = []
                        for field in ['title', 'description', 'datePosted']:
                            if not s.get(field):
                                missing_fields.append(field)
                        if missing_fields:
                            schema_issues.append(f"  - {rel}: JobPosting missing fields: {missing_fields}")
            except json.JSONDecodeError as e:
                schema_issues.append(f"  - {rel}: invalid JSON-LD: {e}")

        if not found_job_posting:
            schema_issues.append(f"  - {rel}: no JobPosting schema found")

    if schema_issues:
        validation_results['warnings'].append(
            f"CHECK 15: {len(schema_issues)} schema issues in {len(sample_files)} sampled pages:\n" +
            "\n".join(schema_issues[:15])
        )
        _add_check('Schema Markup Validation', critical=False, failed=True,
                   details=f"{len(schema_issues)} schema issues", count=len(sample_files))
    else:
        _add_check('Schema Markup Validation', critical=False, failed=False,
                   details=f'All {len(sample_files)} sampled pages have valid JobPosting schema', count=len(sample_files))


# ---------------------------------------------------------------------------
# CHECK 16: Auto-fix issues
# ---------------------------------------------------------------------------
def auto_fix_issues():
    """Fuzzy-match missing slugs to existing disk slugs and append 301 redirects."""
    jobs_folder = os.path.join(ROOT_DIR, 'jobs')
    redirects_path = os.path.join(ROOT_DIR, '_redirects')

    if not os.path.isdir(jobs_folder):
        return

    # Build set of existing slugs on disk
    existing_slugs = [entry.name for entry in os.scandir(jobs_folder) if entry.is_dir()]
    existing_norm_map = {normalize_slug(s): s for s in existing_slugs}

    # Gather missing slugs from critical_errors (from check 13)
    missing_slugs = []
    for err in validation_results['critical_errors']:
        if 'CHECK 13' in err:
            for line in err.split('\n'):
                m = re.match(r'\s+-\s+jobs/([^/]+)/index\.html', line)
                if m:
                    missing_slugs.append(m.group(1))

    if not missing_slugs:
        return

    fix_lines = []
    date_comment = f"\n# Auto-fix: SEO slug mismatches — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    fix_lines.append(date_comment)

    for missing_slug in missing_slugs:
        norm = normalize_slug(missing_slug)
        if norm in existing_norm_map:
            found_slug = existing_norm_map[norm]
            redirect_rule = f"/jobs/{missing_slug}/  /jobs/{found_slug}/  301"
            fix_lines.append(redirect_rule)
            validation_results['auto_fixes'].append({
                'missing': missing_slug,
                'found': found_slug,
                'rule': redirect_rule,
            })

    if fix_lines:
        try:
            with open(redirects_path, 'a', encoding='utf-8') as f:
                f.write('\n'.join(fix_lines) + '\n')
            print(f"  → Auto-fixed {len(validation_results['auto_fixes'])} slug mismatches in _redirects")
        except Exception as e:
            validation_results['warnings'].append(f"Auto-fix failed to write _redirects: {e}")


# ---------------------------------------------------------------------------
# CHECK 17: Generate SEO report
# ---------------------------------------------------------------------------
def generate_seo_report():
    """Write markdown report to GITHUB_STEP_SUMMARY and seo-validation-report.txt."""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    critical_failed = [c for c in validation_results['checks'] if c.get('critical') and c.get('failed')]
    has_critical = len(critical_failed) > 0 or len(validation_results['critical_errors']) > 0
    status = '❌ FAIL' if has_critical else '✅ PASS'

    lines = []
    lines.append(f"# 🔍 Pre-Deploy SEO & 404 Validation Report — topsarkarijobs.com\n")
    lines.append(f"## Overall Status: {status}\n")
    lines.append(f"Generated: {now}\n")

    # Summary table
    lines.append("## Summary Table\n")
    lines.append("| Check | Status | Details | Count |")
    lines.append("|-------|--------|---------|-------|")
    for check in validation_results['checks']:
        icon = '❌' if check['failed'] else '✅'
        badge = '🔴 CRITICAL' if (check.get('critical') and check['failed']) else ('⚠️ WARNING' if check['failed'] else '✅ OK')
        count_str = str(check.get('count', '—'))
        lines.append(f"| {icon} {check['name']} | {badge} | {check.get('details', '')} | {count_str} |")
    lines.append("")

    # Critical errors
    lines.append("## Critical Errors\n")
    if validation_results['critical_errors']:
        for err in validation_results['critical_errors']:
            lines.append(f"### ❌ {err[:60]}...\n" if len(err) > 60 else f"### ❌ {err}\n")
            # Print first 3 lines of details
            err_lines = err.split('\n')[1:4]
            for el in err_lines:
                lines.append(f"{el}")
            lines.append("")
    else:
        lines.append("✅ No critical errors found.\n")

    # Warnings
    lines.append("## Warnings (Non-Critical)\n")
    if validation_results['warnings']:
        for w in validation_results['warnings']:
            lines.append(f"- ⚠️ {w[:120]}")
        lines.append("")
    else:
        lines.append("✅ No warnings.\n")

    # Auto-fixes
    lines.append(f"## Auto-Fixed Issues: {len(validation_results['auto_fixes'])}\n")
    if validation_results['auto_fixes']:
        for fix in validation_results['auto_fixes'][:10]:
            lines.append(f"- `{fix['rule']}`")
        if len(validation_results['auto_fixes']) > 10:
            lines.append(f"- ... and {len(validation_results['auto_fixes']) - 10} more")
        lines.append("")

    # Deployment decision
    lines.append("## Deployment Decision\n")
    if has_critical:
        lines.append("❌ **BLOCKED** — Fix critical errors before deploying.\n")
    else:
        lines.append("✅ **SAFE TO DEPLOY** — All critical checks passed.\n")

    report_content = '\n'.join(lines)

    # Write to GitHub Step Summary
    try:
        with open(GITHUB_STEP_SUMMARY, 'a', encoding='utf-8') as f:
            f.write(report_content)
    except Exception:
        pass

    # Write to seo-validation-report.txt
    report_path = os.path.join(ROOT_DIR, 'seo-validation-report.txt')
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
    except Exception as e:
        print(f"Warning: Could not write seo-validation-report.txt: {e}")

    return not has_critical


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("🔍 TSJ ADVANCED SEO & 404 VALIDATION")
    print("=" * 60)

    all_urls = check_1_sitemap_url_validation()
    print(f"✓ CHECK 1: {len(all_urls)} sitemap URLs found")

    check_2_page_content_validation(all_urls)
    print("✓ CHECK 2: Page content validated")

    check_3_canonical_validation(all_urls)
    print("✓ CHECK 3: Canonicals validated")

    check_4_legacy_url_detection()
    print("✓ CHECK 4: Legacy URLs scanned")

    check_5_orphan_page_detection()
    print("✓ CHECK 5: Orphan pages detected")

    check_6_index_file_existence()
    print("✓ CHECK 6: Index files verified")

    check_7_page_not_available(all_urls)
    print("✓ CHECK 7: Page Not Available scanned")

    check_8_redirect_loop_detection()
    print("✓ CHECK 8: Redirect loops checked")

    check_9_internal_link_validation()
    print("✓ CHECK 9: Internal links validated")

    check_10_duplicate_url_detection()
    print("✓ CHECK 10: Duplicate URLs detected")

    check_11_robots_validation()
    print("✓ CHECK 11: robots.txt validated")

    check_12_sitemap_cleanliness()
    print("✓ CHECK 12: Sitemap cleanliness checked")

    check_13_data_index_validation()
    print("✓ CHECK 13: Data indexes validated")

    check_14_category_page_validation()
    print("✓ CHECK 14: Category pages validated")

    check_15_schema_validation()
    print("✓ CHECK 15: Schema markup validated")

    if AUTO_FIX and validation_results['critical_errors']:
        auto_fix_issues()
        print("✓ CHECK 16: Auto-fix applied")

    deployment_safe = generate_seo_report()
    print("✓ CHECK 17: Report generated")

    if not deployment_safe:
        with open(os.environ.get('GITHUB_ENV', '/tmp/github_env'), 'a') as f:
            f.write('CRITICAL_ERRORS=true\n')
        print("\n❌ CRITICAL ERRORS FOUND — DEPLOYMENT BLOCKED")
        print(f"   Critical errors: {len(validation_results['critical_errors'])}")
        print(f"   Warnings: {len(validation_results['warnings'])}")
        sys.exit(1)
    else:
        print("\n✅ ALL CHECKS PASSED — SAFE TO DEPLOY")
        print(f"   Warnings: {len(validation_results['warnings'])}")
        print(f"   Auto-fixes: {len(validation_results['auto_fixes'])}")
        sys.exit(0)


if __name__ == '__main__':
    main()
