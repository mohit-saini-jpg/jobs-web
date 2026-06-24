"""
TSJ SEO Validator Utilities
Shared helper functions for advanced_seo_validator.py
"""

import os
import re


def normalize_slug(slug: str) -> str:
    """Remove all non-alphanumeric chars, lowercase — for fuzzy matching"""
    return re.sub(r'[^a-z0-9]', '', str(slug).lower())


def slugify(text: str) -> str:
    """Convert text to URL-safe slug"""
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')[:80]


def read_file(filepath: str, encoding: str = 'utf-8') -> str:
    """Read file safely with latin-1 fallback"""
    try:
        with open(filepath, encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, encoding='latin-1') as f:
                return f.read()
        except Exception:
            return ''
    except Exception:
        return ''


def parse_redirects(filepath: str) -> dict:
    """Parse Netlify _redirects format → {source: target}"""
    redirects = {}
    if not os.path.exists(filepath):
        return redirects
    try:
        with open(filepath, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    redirects[parts[0]] = parts[1]
    except Exception:
        pass
    return redirects


def extract_links(html_content: str) -> list:
    """Extract all href values from <a> tags"""
    return re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html_content)


def find_index_files(base_path: str) -> list:
    """Recursively find all index.html files"""
    indexes = []
    for root, dirs, files in os.walk(base_path):
        if 'index.html' in files:
            indexes.append(os.path.join(root, 'index.html'))
    return indexes


def is_page_not_available(filepath: str) -> bool:
    """Check if file contains Page Not Available patterns"""
    patterns = [
        r'Page\s+Not\s+Available',
        r'Job\s+Not\s+Available',
        r'Content\s+Not\s+Found',
    ]
    content = read_file(filepath)
    content_no_script = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL)
    for pattern in patterns:
        if re.search(pattern, content_no_script, re.IGNORECASE):
            return True
    return False


def get_canonical_url(html_content: str) -> str | None:
    """Extract canonical URL from HTML"""
    match = re.search(r'<link rel="canonical" href="([^"]+)"', html_content)
    return match.group(1) if match else None


def get_page_title(html_content: str) -> str | None:
    """Extract page title from HTML"""
    match = re.search(r'<title>(.+?)</title>', html_content)
    return match.group(1) if match else None


def get_meta_description(html_content: str) -> str | None:
    """Extract meta description from HTML"""
    match = re.search(r'<meta name="description" content="([^"]+)"', html_content)
    return match.group(1) if match else None
