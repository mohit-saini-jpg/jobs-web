// Vercel Edge Middleware — historical 301 redirects at the edge.
//
// WHY: Vercel ignores the Netlify-style `_redirects` file, and vercel.json caps
// redirects at 1024. This site has thousands of historical /jobs/ slug-rename 301s
// (from renamed recruitment pages). This middleware issues them with no limit,
// reading `redirect-map.js` which is regenerated from `_redirects` on every build
// by build_redirect_map.py — so it never drifts out of sync.
//
// vercel.json redirects run BEFORE middleware, so the ~96 structural redirects
// there take precedence; this handles everything else.

import REDIRECTS from './redirect-map.js';

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

export default function middleware(request) {
  const url = new URL(request.url);
  const p = url.pathname;

  // 0) legacy /jobs/{slug}/{utility}.html leak from the disabled nav-grid widget
  const leak = p.match(JOBS_SLUG_HTML_LEAK);
  if (leak) {
    const dest = LEAK_TARGET[leak[1]];
    if (dest) return redirect(url.origin, dest, url.search);
  }

  // 1) exact map lookup — try as-is, then toggle the trailing slash
  const candidates = p.endsWith('/') ? [p, p.slice(0, -1)] : [p, p + '/'];
  for (const c of candidates) {
    const dest = REDIRECTS[c];
    if (dest && dest !== p) return redirect(url.origin, dest, url.search);
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
