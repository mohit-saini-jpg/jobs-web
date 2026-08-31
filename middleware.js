// Vercel Edge Middleware — historical 301 redirects + 410 Gone at the edge.
//
// WHY: Vercel ignores the Netlify-style `_redirects` file, and vercel.json caps
// redirects at 1024. This site has thousands of historical /jobs/ slug-rename 301s
// (from renamed recruitment pages). This middleware issues them with no limit,
// reading `redirect-map.js` which is regenerated from `_redirects` on every build
// by build_redirect_map.py — so it never drifts out of sync.
//
// vercel.json redirects run BEFORE middleware, so the ~96 structural redirects
// there take precedence; this handles everything else.
//
// It also answers known-permanently-removed paths (old expired job postings
// with no successor page) with a real HTTP 410 Gone instead of letting them
// fall through to the platform's default 404 — Search Console deindexes 410s
// much faster than 404s, which it keeps re-crawling indefinitely. That list
// (gone-map.js) is compiled from `_gone_urls.txt` by build_gone_map.py.

import REDIRECTS from './redirect-map.js';
import QUERY_REDIRECTS from './redirect-map-query.js';
import GONE from './gone-map.js';

// Legacy bare-state URL scheme: /{state}/{job}/ -> /state/{state}/{job}/
const STATES = new Set([
  'andhra-pradesh', 'arunachal-pradesh', 'assam', 'bihar', 'chhattisgarh', 'goa',
  'gujarat', 'haryana', 'himachal-pradesh', 'jharkhand', 'karnataka', 'kerala',
  'madhya-pradesh', 'maharashtra', 'manipur', 'meghalaya', 'mizoram', 'nagaland',
  'odisha', 'punjab', 'rajasthan', 'sikkim', 'tamil-nadu', 'telangana', 'tripura',
  'uttar-pradesh', 'uttarakhand', 'west-bengal', 'delhi', 'jammu-and-kashmir',
  'ladakh', 'chandigarh', 'puducherry', 'andaman-and-nicobar',
  'dadra-and-nagar-haveli', 'daman-and-diu', 'lakshadweep',
]);

// Run on clean-URL page paths only; skip static assets and platform internals.
// NOTE: .html is deliberately NOT in the excluded-extensions list below — this
// site never serves real .html files under /jobs/, so any request for one is
// a legacy broken relative link (see JOBS_SLUG_HTML_LEAK below) that needs to
// reach the middleware to be redirected, not fall through as a 404.
export const config = {
  matcher: ['/((?!_next/|_vercel/|assets/|images/|fonts/|api/|.*\\.(?:css|js|mjs|json|xml|txt|pdf|png|jpe?g|gif|svg|ico|webp|woff2?|ttf)$).*)'],
};

// PERMANENT FIX (2026-07-13): a since-disabled JS widget (script.js
// renderHomeQuickLinks, dead since ~May 2026) once injected relative links
// like href="category.html?group=study" into job detail pages. The browser
// resolved those relative to the current page, producing URLs like
// /jobs/{slug}/category.html?group=study — which never existed. Google
// crawled and indexed thousands of these before the widget was disabled, and
// they still show up in Search Console as "Not found (404)". The widget is
// gone, but the URLs Google already knows about still need a real redirect
// to actually resolve — this catches ANY job slug + any of these filenames.
const JOBS_SLUG_HTML_LEAK = /^\/jobs\/[^/]+\/(index|category|helpdesk|tools|view|govt-services|resume-maker)\.html$/;
const LEAK_TARGET = {
  index: '/',
  category: '/category.html',
  helpdesk: '/helpdesk/',
  tools: '/tools/',
  view: '/',
  'govt-services': '/govt-services/',
  'resume-maker': '/resume-maker/',
};

function redirect(origin, dest, search) {
  const to = dest.endsWith('/') || dest.includes('#') ? dest : dest;
  return Response.redirect(origin + to + (search || ''), 301);
}

// Mirrors build_redirect_map.py's query_key(): pathname + sorted 'k=v' pairs
// joined by ';', order-independent so a Googlebot re-request with params in a
// different order than they were originally crawled in still matches.
function queryKey(pathname, searchParams) {
  const pairs = [];
  for (const [k, v] of searchParams) pairs.push(`${k}=${v}`);
  pairs.sort();
  return `${pathname}?${pairs.join(';')}`;
}

// job.html?slug=X has NO per-value _redirects rule (there are too many to
// enumerate one by one, unlike view.html/category.html/state-jobs.html's
// small enumerable value sets) -- mirrors job.html's own client-side
// window.location.replace() cleanup exactly, just as a real, instant 301
// instead of a redirect that depends on Googlebot successfully executing JS.
function jobHtmlSlugTarget(searchParams) {
  const raw = searchParams.get('slug') || searchParams.get('_slug') || '';
  if (!raw) return null;
  const cleaned = raw.replace(/^sr_[a-z_]+-/, '').replace(/-[0-9a-f]{6,8}$/, '');
  return cleaned ? `/jobs/${encodeURIComponent(cleaned)}/` : null;
}

function gone() {
  return new Response('410 Gone — this page has been permanently removed.', {
    status: 410,
    headers: { 'content-type': 'text/plain; charset=utf-8' },
  });
}

export default function middleware(request) {
  const url = new URL(request.url);
  const p = url.pathname;

  // 0) legacy /jobs/{slug}/{utility}.html leak from the disabled nav-grid widget
  const leak = p.match(JOBS_SLUG_HTML_LEAK);
  if (leak) {
    const dest = LEAK_TARGET[leak[1]];
    if (dest) return redirect(url.origin, dest, url.search);
  }

  // 0b) legacy query-string URLs (job.html?slug=, view.html?section=,
  // category.html?group=, state-jobs.html?state=, state-job-detail.html?
  // state=&slug=, education-detail.html?section=, education/<state>/?slug=)
  // -- these .html files still exist on disk but only redirect client-side
  // via window.location.replace(), which depends on Googlebot successfully
  // rendering the page. A real GSC "Page indexing" export showed these
  // patterns are a large share of the "Not found (404)" bucket. Query-string
  // rules are never in REDIRECTS (build_redirect_map.py keeps them in a
  // separate map since the lookup key must include the search string).
  if (url.search) {
    const qDest = QUERY_REDIRECTS[queryKey(p, url.searchParams)];
    if (qDest && qDest !== p) return redirect(url.origin, qDest, '');
    if (p === '/job.html') {
      const jobDest = jobHtmlSlugTarget(url.searchParams);
      if (jobDest) return redirect(url.origin, jobDest, '');
    }
  }

  // 1) exact map lookup — try as-is, then toggle the trailing slash
  const candidates = p.endsWith('/') ? [p, p.slice(0, -1)] : [p, p + '/'];
  for (const c of candidates) {
    const dest = REDIRECTS[c];
    if (dest && dest !== p) return redirect(url.origin, dest, url.search);
  }

  // 1b) known-permanently-removed pages (expired postings, no successor) —
  // 410 Gone instead of falling through to the platform default 404, so
  // Search Console deindexes them instead of re-crawling forever.
  for (const c of candidates) {
    if (GONE.has(c)) return gone();
  }

  // 2) legacy bare-state scheme: /{state}/{rest} -> /state/{state}/{rest}
  const m = p.match(/^\/([a-z][a-z-]*)\/(.+)$/);
  if (m && STATES.has(m[1])) {
    let dest = `/state/${m[1]}/${m[2]}`;
    if (!dest.endsWith('/')) dest += '/';
    if (dest !== p) return redirect(url.origin, dest, url.search);
  }

  return undefined; // no match — continue to the static file
}
