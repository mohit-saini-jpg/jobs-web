/**
 * ╔══════════════════════════════════════════════════════════════╗
 * ║        HYBRID DYNAMIC CACHE MANAGER — sw.js                 ║
 * ║        Top Sarkari Jobs | topsarkarijobs.com                 ║
 * ║                                                              ║
 * ║  Strategy Matrix:                                            ║
 * ║  • API / JSON job data  → Network-only (no-store)            ║
 * ║  • HTML pages           → Stale-While-Revalidate             ║
 * ║  • JS / CSS / Fonts     → Cache-First (immutable, 1 year)    ║
 * ║  • Images / WebP        → Cache-First (6 months)             ║
 * ║  • Offline fallback     → Cached shell page                  ║
 * ╚══════════════════════════════════════════════════════════════╝
 */

'use strict';

// ─── Version & Cache Names ────────────────────────────────────────────────────
const CACHE_VERSION      = 'v3';
const CACHE_STATIC       = `static-assets-${CACHE_VERSION}`;
const CACHE_PAGES        = `html-pages-${CACHE_VERSION}`;
const CACHE_IMAGES       = `images-${CACHE_VERSION}`;
const CACHE_OFFLINE      = `offline-shell-${CACHE_VERSION}`;

// All known cache names for this version (used to purge old ones)
const ALL_CACHES = [CACHE_STATIC, CACHE_PAGES, CACHE_IMAGES, CACHE_OFFLINE];

// ─── Size Limits (prevent storage bloat) ─────────────────────────────────────
const LIMITS = {
  [CACHE_STATIC]: { maxEntries: 60,  maxAgeSeconds: 31_536_000 }, // 1 year
  [CACHE_PAGES]:  { maxEntries: 30,  maxAgeSeconds:  86_400    }, // 1 day
  [CACHE_IMAGES]: { maxEntries: 80,  maxAgeSeconds: 15_552_000 }, // 6 months
};

// ─── Offline Shell Page ───────────────────────────────────────────────────────
const OFFLINE_PAGE = '/offline.html';

// ─── Pre-cache on Install ─────────────────────────────────────────────────────
// Only critical shell assets — keep small for fast SW activation
const PRECACHE_STATIC = [
  '/all.min.css',
];

const PRECACHE_PAGES = [
  '/',
  '/index.html',
];

// ─────────────────────────────────────────────────────────────────────────────
// INSTALL: pre-cache shell assets, claim clients immediately
// ─────────────────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  console.log(`[SW ${CACHE_VERSION}] Installing…`);

  event.waitUntil(
    (async () => {
      // Pre-cache static assets
      const staticCache = await caches.open(CACHE_STATIC);
      await staticCache.addAll(PRECACHE_STATIC).catch(e =>
        console.warn('[SW] Static pre-cache partial fail:', e.message)
      );

      // Pre-cache core pages
      const pageCache = await caches.open(CACHE_PAGES);
      await pageCache.addAll(PRECACHE_PAGES).catch(e =>
        console.warn('[SW] Page pre-cache partial fail:', e.message)
      );

      // Build offline fallback shell
      await buildOfflineFallback();

      // Skip waiting so new SW activates immediately
      await self.skipWaiting();
      console.log(`[SW ${CACHE_VERSION}] Installed ✓`);
    })()
  );
});

// ─────────────────────────────────────────────────────────────────────────────
// ACTIVATE: purge OLD cache versions, take control of all tabs
// ─────────────────────────────────────────────────────────────────────────────
self.addEventListener('activate', event => {
  console.log(`[SW ${CACHE_VERSION}] Activating…`);

  event.waitUntil(
    (async () => {
      // Delete ALL caches not in this version's list
      const allKeys = await caches.keys();
      const stale   = allKeys.filter(k => !ALL_CACHES.includes(k));

      if (stale.length) {
        console.log(`[SW] Purging ${stale.length} old cache(s):`, stale);
        await Promise.all(stale.map(k => caches.delete(k)));
      }

      // Immediately control open tabs without reload
      await self.clients.claim();
      console.log(`[SW ${CACHE_VERSION}] Active ✓ — controlling all clients`);
    })()
  );
});

// ─────────────────────────────────────────────────────────────────────────────
// FETCH: smart routing by request type
// ─────────────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin + whitelisted CDNs
  if (!shouldHandle(request)) return;

  // ── 1. Job API / JSON data  →  Network-Only (always fresh) ──────────────────
  if (isJobData(url, request)) {
    event.respondWith(networkOnly(request));
    return;
  }

  // ── 2. Static assets (JS/CSS/fonts/icons)  →  Cache-First ───────────────────
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(request, CACHE_STATIC, LIMITS[CACHE_STATIC]));
    return;
  }

  // ── 3. Images / WebP  →  Cache-First (long TTL) ──────────────────────────────
  if (isImage(url)) {
    event.respondWith(cacheFirst(request, CACHE_IMAGES, LIMITS[CACHE_IMAGES]));
    return;
  }

  // ── 4. HTML pages  →  Stale-While-Revalidate ─────────────────────────────────
  if (isHTMLPage(request)) {
    event.respondWith(staleWhileRevalidate(request, CACHE_PAGES, LIMITS[CACHE_PAGES]));
    return;
  }

  // ── 5. Everything else  →  Network with offline fallback ─────────────────────
  event.respondWith(networkWithFallback(request));
});

// ─────────────────────────────────────────────────────────────────────────────
// MESSAGE: allow page to trigger cache control actions
// ─────────────────────────────────────────────────────────────────────────────
self.addEventListener('message', event => {
  const { type, payload } = event.data || {};

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'CLEAR_JOB_CACHE':
      // Pages can tell SW to drop HTML cache (e.g. after data refresh)
      caches.delete(CACHE_PAGES).then(() => {
        event.ports[0]?.postMessage({ ok: true });
        console.log('[SW] HTML page cache cleared on demand');
      });
      break;

    case 'GET_CACHE_STATS':
      getCacheStats().then(stats => {
        event.ports[0]?.postMessage(stats);
      });
      break;

    case 'TRIM_CACHES':
      Promise.all(
        Object.entries(LIMITS).map(([name, limit]) => trimCache(name, limit))
      ).then(() => event.ports[0]?.postMessage({ ok: true }));
      break;
  }
});

// ═════════════════════════════════════════════════════════════════════════════
// STRATEGY IMPLEMENTATIONS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Network-Only — for job API/JSON data.
 * Adds cache-busting headers to guarantee fresh responses.
 */
async function networkOnly(request) {
  const freshReq = new Request(request.url, {
    method:  request.method,
    headers: new Headers({
      ...Object.fromEntries(request.headers.entries()),
      'Cache-Control': 'no-store, no-cache',
      'Pragma':        'no-cache',
    }),
    mode:        request.mode,
    credentials: request.credentials,
  });

  try {
    const response = await fetch(freshReq);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response;
  } catch (err) {
    console.warn('[SW] Network-Only failed for:', request.url, err.message);
    return new Response(
      JSON.stringify({ error: 'offline', message: 'No network — job data unavailable' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Cache-First — for static assets (JS/CSS/fonts/images).
 * Serve from cache instantly; fetch & store if not cached.
 * Enforces per-cache size + age limits.
 */
async function cacheFirst(request, cacheName, limits) {
  const cache  = await caches.open(cacheName);
  const cached = await cache.match(request);

  if (cached && !isCacheEntryStale(cached, limits.maxAgeSeconds)) {
    return cached; // ⚡ instant
  }

  // Not cached or stale — fetch fresh
  try {
    const response = await fetch(request.clone());
    if (response.ok) {
      const toStore = response.clone();
      // Async store + trim — don't block the response
      (async () => {
        await cache.put(request, toStore);
        await trimCache(cacheName, limits);
      })();
    }
    return response;
  } catch (err) {
    // Return stale copy if we have one, even if expired
    if (cached) return cached;
    throw err;
  }
}

/**
 * Stale-While-Revalidate — for HTML pages.
 * Return cached version immediately (fast), then update cache in background.
 * If no cache exists, wait for network.
 */
async function staleWhileRevalidate(request, cacheName, limits) {
  const cache  = await caches.open(cacheName);
  const cached = await cache.match(request);

  // Background revalidation (fire-and-forget)
  const networkFetch = fetch(request.clone())
    .then(async response => {
      if (response.ok) {
        await cache.put(request, response.clone());
        await trimCache(cacheName, limits);
      }
      return response;
    })
    .catch(err => {
      console.warn('[SW] SWR revalidation failed:', err.message);
      return null;
    });

  if (cached) {
    // Serve stale immediately, update in background
    return cached;
  }

  // No cache — wait for network
  const networkResponse = await networkFetch;
  if (networkResponse) return networkResponse;

  // Total offline: return offline shell
  return getOfflinePage();
}

/**
 * Network with Offline Fallback — for misc requests.
 */
async function networkWithFallback(request) {
  try {
    return await fetch(request);
  } catch {
    if (isHTMLPage(request)) return getOfflinePage();
    return new Response('', { status: 503 });
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// CACHE MANAGEMENT UTILITIES
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Trim cache: evict oldest entries beyond maxEntries, and entries older than maxAgeSeconds.
 */
async function trimCache(cacheName, { maxEntries, maxAgeSeconds }) {
  const cache = await caches.open(cacheName);
  const keys  = await cache.keys();

  const now = Date.now();
  let deleted = 0;

  // Age-based eviction — check Date header
  for (const request of keys) {
    const response = await cache.match(request);
    if (response && isCacheEntryStale(response, maxAgeSeconds)) {
      await cache.delete(request);
      deleted++;
    }
  }

  // Count-based eviction — delete oldest if over limit
  const remaining = (await cache.keys()).length;
  if (remaining > maxEntries) {
    const overflow = remaining - maxEntries;
    const allKeys  = await cache.keys();
    // Evict from the start (oldest added first)
    for (let i = 0; i < overflow; i++) {
      await cache.delete(allKeys[i]);
      deleted++;
    }
  }

  if (deleted > 0) {
    console.log(`[SW] Trimmed ${deleted} entries from "${cacheName}"`);
  }
}

/**
 * Check if a cached response is older than maxAgeSeconds.
 */
function isCacheEntryStale(response, maxAgeSeconds) {
  const dateHeader = response.headers.get('date');
  if (!dateHeader) return false;
  const age = (Date.now() - new Date(dateHeader).getTime()) / 1000;
  return age > maxAgeSeconds;
}

/**
 * Return cached stats for all caches (for the DevTools panel).
 */
async function getCacheStats() {
  const stats = {};
  for (const name of ALL_CACHES) {
    const cache = await caches.open(name);
    const keys  = await cache.keys();

    let totalBytes = 0;
    for (const req of keys) {
      const res = await cache.match(req);
      if (res) {
        const buf = await res.clone().arrayBuffer().catch(() => null);
        if (buf) totalBytes += buf.byteLength;
      }
    }

    stats[name] = {
      entries:  keys.length,
      sizeMB:   +(totalBytes / 1_048_576).toFixed(2),
      urls:     keys.map(r => r.url),
    };
  }
  return stats;
}

// ─────────────────────────────────────────────────────────────────────────────
// OFFLINE PAGE
// ─────────────────────────────────────────────────────────────────────────────

async function buildOfflineFallback() {
  const cache = await caches.open(CACHE_OFFLINE);
  const html  = generateOfflineHTML();
  await cache.put(
    new Request(OFFLINE_PAGE),
    new Response(html, {
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    })
  );
}

async function getOfflinePage() {
  const cache    = await caches.open(CACHE_OFFLINE);
  const fallback = await cache.match(OFFLINE_PAGE);
  return fallback || new Response('<h1>Offline</h1>', {
    status:  503,
    headers: { 'Content-Type': 'text/html' }
  });
}

function generateOfflineHTML() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline — Top Sarkari Jobs</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    background:#0f172a;color:#e2e8f0;
    display:flex;align-items:center;justify-content:center;
    min-height:100vh;padding:24px;text-align:center;
  }
  .card{
    background:#1e293b;border-radius:16px;padding:40px 32px;
    max-width:380px;width:100%;
    border:1px solid #334155;
  }
  .icon{font-size:56px;margin-bottom:20px}
  h1{font-size:22px;font-weight:700;color:#f1f5f9;margin-bottom:10px}
  p{color:#94a3b8;line-height:1.6;font-size:14px;margin-bottom:24px}
  button{
    background:#f97316;color:#fff;border:none;
    padding:12px 28px;border-radius:8px;font-size:15px;
    font-weight:600;cursor:pointer;width:100%;
  }
  button:active{opacity:.85}
</style>
</head>
<body>
<div class="card">
  <div class="icon">📡</div>
  <h1>You're Offline</h1>
  <p>No internet connection detected. Please check your data or Wi-Fi and try again to see the latest Sarkari Jobs.</p>
  <button onclick="location.reload()">Retry Connection</button>
</div>
</body>
</html>`;
}

// ═════════════════════════════════════════════════════════════════════════════
// REQUEST CLASSIFICATION HELPERS
// ═════════════════════════════════════════════════════════════════════════════

function shouldHandle(request) {
  const url = new URL(request.url);
  // Only handle GET requests
  if (request.method !== 'GET') return false;
  // Same-origin
  if (url.origin === self.location.origin) return true;
  // Whitelisted CDNs (fonts, analytics)
  const cdnWhitelist = [
    'fonts.googleapis.com',
    'fonts.gstatic.com',
    'cdnjs.cloudflare.com',
  ];
  return cdnWhitelist.some(h => url.hostname.endsWith(h));
}

function isJobData(url, request) {
  // JSON job data files — always network-only
  if (url.pathname.endsWith('.json') && !url.pathname.includes('manifest')) return true;
  // API endpoints
  if (url.pathname.startsWith('/api/')) return true;
  // Any request with no-store hint
  const cc = request.headers.get('cache-control') || '';
  if (cc.includes('no-store') || cc.includes('no-cache')) return true;
  return false;
}

function isStaticAsset(url) {
  return /\.(js|css|woff2?|ttf|eot|otf|ico)(\?.*)?$/.test(url.pathname);
}

function isImage(url) {
  return /\.(png|jpg|jpeg|gif|svg|webp|avif)(\?.*)?$/.test(url.pathname);
}

function isHTMLPage(request) {
  const accept = request.headers.get('accept') || '';
  return (
    accept.includes('text/html') ||
    request.destination === 'document' ||
    request.url.endsWith('.html') ||
    request.url.endsWith('/')
  );
}
