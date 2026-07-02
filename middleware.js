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
export const config = {
  matcher: ['/((?!_next/|_vercel/|assets/|images/|fonts/|api/|.*\\.[a-zA-Z0-9]+$).*)'],
};

function redirect(origin, dest, search) {
  const to = dest.endsWith('/') || dest.includes('#') ? dest : dest;
  return Response.redirect(origin + to + (search || ''), 301);
}

export default function middleware(request) {
  const url = new URL(request.url);
  const p = url.pathname;

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
