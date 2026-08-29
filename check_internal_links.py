#!/usr/bin/env python3
"""
check_internal_links.py -- genuine site-wide internal link resolver.

Unlike .github/workflows/check_broken_links.py (jobs/-only, cross-references
sections-index.json slugs against disk -- never parses a real <a href>),
this walks every rendered page across every tree, extracts every <a href>
pointing at the site's own domain, and resolves it against:
  - the real on-disk page set (every dir with an index.html, plus flat
    /a/b/name.html files like the /tools/ single-page tools)
  - the _redirects -> redirect-map.js 301 map (exact literal rules only,
    matching what build_redirect_map.py actually emits)
  - vercel.json's own redirects array
  - _gone_urls.txt (intentionally-410'd pages)
Anything left over is a genuinely broken internal link: not live, not
redirected, not intentionally gone.

Also reports the inbound-link distribution across /jobs/ pages (a page with
0 distinct inbound internal links is an orphan, reachable only via
sitemap.xml/search) -- this is what surfaced the Related Jobs widget's
uneven-fallback bug (see _related_jobs_html in generate_all.py).

Read-only. Pure stdlib. Run from repo root:
    python3 check_internal_links.py
"""
import glob
import json
import os
import re
from collections import defaultdict

ROOT = '.'
BASE_HOST = 'www.topsarkarijobs.com'

TREES = ('jobs', 'state', 'state-jobs', 'education', 'category', 'qualification',
         'district', 'section', 'about', 'contact', 'privacy', 'terms',
         'disclaimer', 'helpdesk', 'editorial-policy', 'fact-check-policy',
         'correction-policy', 'tools', 'govt-services', 'resume-maker',
         'apply-request', 'app', 'sitemap', 'search')

# Skip entirely: binary downloads and other non-page assets that are never
# rendered pages and never live in a TREES dir with an index.html.
_SKIP_DIRS = ('/downloads/',)

_HREF_RE = re.compile(r'<a\b[^>]*\bhref="([^"]+)"', re.I)
_STATIC_EXT_RE = re.compile(
    r'\.(css|js|mjs|json|xml|txt|pdf|png|jpe?g|gif|svg|ico|webp|woff2?|ttf|apk|zip)(\?|#|$)', re.I)


def build_live_paths():
    """Every /a/b/.../  path with a real index.html on disk, plus every
    literal /a/b/name.html flat file (e.g. the /tools/ single-page tools,
    which are served as real files, not directory+index.html)."""
    live = set()
    live.add('/')
    for t in TREES:
        base = os.path.join(ROOT, t)
        if not os.path.isdir(base):
            continue
        for dp, dns, fns in os.walk(base):
            rel_dir = os.path.relpath(dp, ROOT).replace(os.sep, '/')
            if 'index.html' in fns:
                live.add('/' + rel_dir + '/')
            for fn in fns:
                if fn.endswith('.html') and fn != 'index.html':
                    live.add('/' + rel_dir + '/' + fn)
    return live


def build_redirect_map():
    """Mirrors build_redirect_map.py's own filter exactly (exact literal
    301s only) plus vercel.json's native redirects array."""
    mapping = {}
    red_path = os.path.join(ROOT, '_redirects')
    if os.path.isfile(red_path):
        with open(red_path, encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) < 3:
                    continue
                src, dst, code = parts[0], parts[1], parts[2].rstrip('!')
                if code != '301':
                    continue
                if any(c in src for c in (':', '*', '?')) or any(c in dst for c in (':', '*', '?')):
                    continue
                if src == dst or not src.startswith('/'):
                    continue
                mapping[src] = dst
    vj_path = os.path.join(ROOT, 'vercel.json')
    if os.path.isfile(vj_path):
        try:
            vj = json.load(open(vj_path, encoding='utf-8'))
            for r in vj.get('redirects', []):
                src, dst = r.get('source'), r.get('destination')
                if src and dst and not any(c in src for c in (':', '*')):
                    mapping.setdefault(src, dst)
        except Exception:
            pass
    return mapping


def build_gone_set():
    gone = set()
    gp = os.path.join(ROOT, '_gone_urls.txt')
    if os.path.isfile(gp):
        with open(gp, encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    gone.add(line)
    return gone


def normalize_href(href, live_paths):
    """Return an absolute site path ('/a/b/') for an internal href, or None
    if it's external/non-navigational (mailto, tel, javascript, anchor-only,
    a static asset, or an off-site absolute URL)."""
    h = href.strip()
    if not h or h.startswith(('#', 'mailto:', 'tel:', 'javascript:', 'data:')):
        return None
    if h.startswith('http://') or h.startswith('https://'):
        m = re.match(r'https?://([^/]+)(/.*)?$', h)
        if not m or m.group(1).lower() not in (BASE_HOST, BASE_HOST[4:]):
            return None  # external domain
        path = m.group(2) or '/'
    elif h.startswith('/'):
        path = h
    else:
        return None  # relative (../, foo.html) -- not used site-wide here
    path = path.split('?')[0].split('#')[0]
    if any(d in path for d in _SKIP_DIRS):
        return None
    if _STATIC_EXT_RE.search(path):
        return None
    if not path.endswith('/') and not path.endswith('.html'):
        path += '/'
    return path


def resolve(path, live_paths, redirects, gone):
    if path in live_paths:
        return 'ok', path
    if path in gone:
        return 'gone', path
    if path in redirects:
        dst = redirects[path]
        dst_norm = dst if (dst.endswith('/') or dst.endswith('.html')) else dst + '/'
        if dst_norm in live_paths:
            return 'redirect_ok', dst_norm
        return 'redirect_broken', dst_norm
    return 'broken', None


def main():
    print('Building live-page set...')
    live = build_live_paths()
    print(f'  {len(live)} live pages')
    redirects = build_redirect_map()
    print(f'  {len(redirects)} exact 301 rules (from _redirects + vercel.json)')
    gone = build_gone_set()
    print(f'  {len(gone)} intentionally-gone (410) urls')

    counts = defaultdict(int)
    broken_samples = defaultdict(list)  # target_path -> [source_files]
    inbound = defaultdict(set)  # live target_path -> set of distinct source files linking to it
    files_scanned = 0

    all_files = []
    for t in TREES:
        all_files += glob.glob(os.path.join(ROOT, t, '**', 'index.html'), recursive=True)
    all_files = sorted(set(all_files))

    for fp in all_files:
        files_scanned += 1
        try:
            with open(fp, encoding='utf-8', errors='ignore') as f:
                html = f.read()
        except Exception:
            continue
        for href in _HREF_RE.findall(html):
            path = normalize_href(href, live)
            if path is None:
                continue
            status, target = resolve(path, live, redirects, gone)
            counts[status] += 1
            if status == 'broken' and len(broken_samples[path]) < 3:
                broken_samples[path].append(fp)
            if status in ('ok', 'redirect_ok'):
                self_path = '/' + os.path.relpath(os.path.dirname(fp), ROOT).replace(os.sep, '/') + '/'
                if target != self_path:
                    inbound[target].add(fp)

    print()
    print(f'Files scanned: {files_scanned}')
    print(f'Total internal <a href> checked: {sum(counts.values())}')
    for k in ('ok', 'redirect_ok', 'gone', 'redirect_broken', 'broken'):
        print(f'  {k:16s} {counts.get(k, 0)}')

    print()
    print(f'Distinct BROKEN target paths: {len(broken_samples)}')
    ranked = sorted(broken_samples.items(), key=lambda kv: -len(kv[1]))
    for target, sources in ranked[:60]:
        print(f'  {target}  (from {sources[0]})')

    # Orphan-page signal: /jobs/ pages with 0 or 1 distinct internal inbound
    # content links (only reachable via sitemap.xml/search otherwise).
    job_live = [p for p in live if p.startswith('/jobs/')]
    inbound_counts = {p: len(inbound.get(p, ())) for p in job_live}
    zero_inbound = sum(1 for c in inbound_counts.values() if c == 0)
    one_inbound = sum(1 for c in inbound_counts.values() if c == 1)
    print()
    print(f'/jobs/ pages with 0 distinct inbound internal links: {zero_inbound}')
    print(f'/jobs/ pages with exactly 1 distinct inbound internal link: {one_inbound}')
    worst = sorted(inbound_counts.items(), key=lambda kv: kv[1])[:20]
    for p, c in worst:
        print(f'  {c:3d}  {p}')

    with open('link_check_report.json', 'w', encoding='utf-8') as f:
        json.dump({
            'files_scanned': files_scanned,
            'counts': dict(counts),
            'broken_targets': {k: v for k, v in broken_samples.items()},
            'jobs_inbound_histogram': {
                str(n): sum(1 for c in inbound_counts.values() if c == n)
                for n in range(0, 11)
            },
        }, f, indent=2)
    print('\nFull report: link_check_report.json')


if __name__ == '__main__':
    main()
