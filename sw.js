/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║   ZERO-STALE CACHE ENGINE v8.0 — GitHub Optimized              ║
 * ║   Top Sarkari Jobs | topsarkarijobs.com                        ║
 * ║                                                                  ║
 * ║   ✅ SW_VERSION replaced by generate_version.js on every deploy ║
 * ║   ✅ skipWaiting + clients.claim — instant takeover             ║
 * ║   ✅ Auto delete ALL old caches on activate                     ║
 * ║   ✅ Smart per-resource strategy (HTML/JSON/JS/CSS)             ║
 * ║   ✅ dailyupdates.json → Network First (always fresh)           ║
 * ║   ✅ sections-index.json → SWR 10-min TTL (small/critical)      ║
 * ║   ✅ /data/*.json → SWR 30-min TTL                              ║
 * ║   ✅ version.json (any ?nc=* variant) → Always network          ║
 * ║   ✅ 500ms delay before SW_UPDATED message (race condition fix)  ║
 * ║   ✅ Push notifications fully preserved                         ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */
'use strict';

// ══════════════════════════════════════════════════════════════
// VERSION — Replaced by generate_version.js on every deploy
// Do NOT manually edit — CI/CD replaces this line
// ══════════════════════════════════════════════════════════════
const SW_VERSION = '20260706140649'; // auto-updated by generate_version.js

// ══════════════════════════════════════════════════════════════
// CACHE NAMES — version-stamped, old ones auto-deleted
// ══════════════════════════════════════════════════════════════
const CACHE = {
  static : `tsj-static-${SW_VERSION}`,
  pages  : `tsj-pages-${SW_VERSION}`,
  data   : `tsj-data-${SW_VERSION}`,
  offline: `tsj-offline-${SW_VERSION}`,
};
const ALL_CACHES = Object.values(CACHE);

// ══════════════════════════════════════════════════════════════
// CONSTANTS
// ══════════════════════════════════════════════════════════════
const SITE               = 'https://www.topsarkarijobs.com';
const NOTIF_ICON         = '/icons/icon-192x192.png';
const NOTIF_BADGE        = '/icons/icon-96x96.png';
const DATA_CACHE_MAX     = 50;                    // max JSON entries cached (was 25)
const DATA_MAX_AGE_MS    = 30 * 60 * 1000;        // 30 min for /data/*.json (was 1hr)
const JSON_MAX_AGE_MS    = 15 * 60 * 1000;        // 15 min for other JSON
const SECTIONS_MAX_AGE_MS = 10 * 60 * 1000;       // 10 min for sections-index.json

// Critical files to precache on install
const PRECACHE_STATIC = [
  // Core styles — always cached
  '/styles.css',
  '/styles-detail.css',  // R11: New detail page CSS
  '/critical.css',
  // Core scripts
  '/script.min.js',
  '/tsj-menu.js',
  '/tsj-config.js',     // R6/R11: Config flags
  '/tsj-init.js',       // R6/R11: Header init
  '/tsj-footer-init.js',// R6/R11: Footer init
  // Header/footer — fetched on EVERY page
  '/header.html',       // R11: Critical - pre-cache to prevent CLS
  '/footer.html',       // R11: Critical
  // Data files
  '/manifest.json',
  '/sections-index.json',
  '/dailyupdates.json',
  // Assets
  '/image.png',
  '/image-40x40.webp',
  '/offline.html',
  '/og-jobs.svg',       // R4/R11: OG images
  // FIX-006: FontAwesome + search/seo engines
  '/fonts/fa/all.min.css?v=20260705fix',
  '/smart-search.min.js',
  '/seo-engine.min.js',
];

// ══════════════════════════════════════════════════════════════
// OFFLINE FALLBACK HTML
// ══════════════════════════════════════════════════════════════
const OFFLINE_HTML = `<!DOCTYPE html><html lang="en-IN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline – Top Sarkari Jobs</title>
<style>*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0d2257;color:#fff;
min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:24px}
.w{max-width:360px}.ic{font-size:72px;margin-bottom:24px}
h1{font-size:24px;font-weight:700;margin-bottom:12px}
p{font-size:15px;opacity:.8;line-height:1.6;margin-bottom:24px}
.btn{display:inline-block;padding:12px 28px;background:#f5a623;color:#0d2257;
border-radius:8px;font-weight:700;font-size:15px;cursor:pointer;border:none}
</style></head>
<body><div class="w"><div class="ic">📡</div><h1>You're Offline</h1>
<p>Internet nahi hai. Enable karein aur retry karein.</p>
<button class="btn" onclick="location.reload()">Retry</button>
</div></body></html>`;

// ══════════════════════════════════════════════════════════════
// INSTALL — precache critical assets, skip waiting IMMEDIATELY
// ══════════════════════════════════════════════════════════════
self.addEventListener('install', e => {
  e.waitUntil(
    Promise.allSettled([
      caches.open(CACHE.static).then(c =>
        Promise.allSettled(PRECACHE_STATIC.map(url =>
          c.add(url).catch(() => {})
        ))
      ),
      caches.open(CACHE.offline).then(c =>
        c.put('offline', new Response(OFFLINE_HTML, {
          headers: { 'Content-Type': 'text/html; charset=utf-8' }
        }))
      ),
    ])
    .then(() => self.skipWaiting())
  );
});

// ══════════════════════════════════════════════════════════════
// ACTIVATE — delete ALL stale caches, claim all clients
// RC-7 FIX: 500ms delay before SW_UPDATED message
// ══════════════════════════════════════════════════════════════
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => {
        const stale = keys.filter(k => !ALL_CACHES.includes(k));
        if (stale.length) {
          console.log(`[SW v8] Deleting ${stale.length} old caches:`, stale);
        }
        return Promise.all(stale.map(k => caches.delete(k)));
      })
      .then(() => self.clients.claim())  // claim FIRST
      .then(() => {
        // RC-7 FIX: Wait 500ms after clients.claim() before sending SW_UPDATED
        // This ensures the new SW has fully claimed all clients before reload
        return new Promise(resolve => setTimeout(resolve, 500));
      })
      .then(() => {
        return self.clients.matchAll({ type: 'window' }).then(clients => {
          clients.forEach(c => c.postMessage({
            type   : 'SW_UPDATED',
            version: SW_VERSION,
          }));
        });
      })
  );
});

// ══════════════════════════════════════════════════════════════
// FETCH — Smart routing by resource type
// ══════════════════════════════════════════════════════════════
self.addEventListener('fetch', e => {
  const { request: req } = e;
  const url = new URL(req.url);

  if (req.method !== 'GET') return;
  if (url.protocol === 'chrome-extension:' || url.protocol === 'moz-extension:') return;
  if (url.hostname !== self.location.hostname) return;

  const path = url.pathname;

  // ── 1. version.json — network, CDN-cacheable (edge-request optimized)
  //    Lets Vercel CDN absorb checks (s-maxage) instead of hitting origin each time
  if (url.pathname === '/version.json') {
    e.respondWith(
      fetch(req)
        .catch(() => new Response('{}', {
          headers: { 'Content-Type': 'application/json' }
        }))
    );
    return;
  }

  // ── 2. sw.js — NEVER intercept
  if (path === '/sw.js') {
    e.respondWith(fetch(req, { cache: 'no-store' }));
    return;
  }

  // ── 3. dailyupdates.json — RC-6 FIX: Network First (always fresh!)
  if (path === '/dailyupdates.json' || path.endsWith('/dailyupdates.json')) {
    e.respondWith(networkFirstJSON(req));
    return;
  }

  // ── 4. sections-index.json — SWR with 10-min TTL (small/critical)
  if (path === '/sections-index.json' || path.endsWith('/sections-index.json')) {
    e.respondWith(staleWhileRevalidate(req, CACHE.data, SECTIONS_MAX_AGE_MS));
    return;
  }

  // ── 5. HTML pages — Network First
  if (
    req.headers.get('accept')?.includes('text/html') ||
    path.endsWith('.html') ||
    path === '/' ||
    path.endsWith('/')
  ) {
    e.respondWith(networkFirstHTML(req));
    return;
  }

  // ── 6a. Complete_Jobs_Full_Data.json (HEAVY ~9MB gzip) — long TTL.
  //    This big master file only changes when you update jobs (version.json
  //    bumps + SW cache name changes force-refresh it on deploy). Revalidating
  //    it every 30 min wasted huge bandwidth on Vercel. Cache it for 12h; the
  //    daily deploy/version bump already busts it when data actually changes.
  if (path.startsWith('/data/') && path.indexOf('Complete_Jobs_Full_Data') !== -1) {
    e.respondWith(staleWhileRevalidate(req, CACHE.data, 12 * 60 * 60 * 1000));
    return;
  }

  // ── 6b. Other /data/*.json (small: sarkari-mini, sr-*, etc.) — SWR 30-min
  if (path.startsWith('/data/') && path.endsWith('.json')) {
    e.respondWith(staleWhileRevalidate(req, CACHE.data, DATA_MAX_AGE_MS));
    return;
  }

  // ── 7. All other JSON files — SWR with 15-min TTL
  if (path.endsWith('.json')) {
    e.respondWith(staleWhileRevalidate(req, CACHE.data, JSON_MAX_AGE_MS));
    return;
  }

  // ── 8. Versioned JS/CSS (has ?v= param) — Cache First (immutable)
  if (url.searchParams.has('v') && (path.endsWith('.js') || path.endsWith('.css'))) {
    e.respondWith(cacheFirstStatic(req));
    return;
  }

  // ── 9. Unversioned JS/CSS — Network First
  if (path.endsWith('.js') || path.endsWith('.css')) {
    e.respondWith(networkFirstStatic(req));
    return;
  }

  // ── 10. Images — CacheFirst (W07 audit fix)
  if (path.match(/\.(png|jpg|jpeg|gif|webp|svg|ico|avif)$/i)) {
    e.respondWith(cacheFirstStatic(req));
    return;
  }

  // ── 11. Fonts — Cache First
  if (path.match(/\.(woff2?|ttf|eot)$/i)) {
    e.respondWith(cacheFirstStatic(req));
    return;
  }

  // ── 12. Everything else — Network First
  e.respondWith(networkFirstHTML(req));
});

// ══════════════════════════════════════════════════════════════
// STRATEGY: Network First → JSON (for dailyupdates.json)
// Always network, fallback to cache only if offline
// ══════════════════════════════════════════════════════════════
async function networkFirstJSON(req) {
  try {
    const res = await fetch(req, { cache: 'no-cache' });
    if (res.ok) {
      const cache = await caches.open(CACHE.data);
      const headers = new Headers(res.headers);
      headers.set('sw-cached-at', Date.now().toString());
      const stamped = new Response(await res.clone().blob(), {
        status: res.status, statusText: res.statusText, headers,
      });
      cache.put(req, stamped);
    }
    return res;
  } catch (_) {
    const cached = await caches.match(req);
    return cached || new Response('{}', { headers: { 'Content-Type': 'application/json' } });
  }
}

// ══════════════════════════════════════════════════════════════
// STRATEGY: Network First → HTML pages
// ══════════════════════════════════════════════════════════════
async function networkFirstHTML(req) {
  try {
    const res = await fetch(req, { cache: 'no-cache' });
    if (res.ok || res.status === 304) {
      const cache = await caches.open(CACHE.pages);
      cache.put(req, res.clone());
    }
    return res;
  } catch (_) {
    const cached = await caches.match(req);
    if (cached) return cached;
    if (req.url !== `${self.location.origin}/`) {
      const rootCached = await caches.match('/');
      if (rootCached) return rootCached;
    }
    const offline = await caches.match('offline', { cacheName: CACHE.offline });
    return offline || new Response(OFFLINE_HTML, {
      headers: { 'Content-Type': 'text/html; charset=utf-8' }
    });
  }
}

// ══════════════════════════════════════════════════════════════
// STRATEGY: Network First → Unversioned static assets
// ══════════════════════════════════════════════════════════════
async function networkFirstStatic(req) {
  try {
    const res = await fetch(req, { cache: 'no-cache' });
    if (res.ok) {
      const cache = await caches.open(CACHE.static);
      cache.put(req, res.clone());
    }
    return res;
  } catch (_) {
    const cached = await caches.match(req);
    return cached || new Response('', { status: 408 });
  }
}

// ══════════════════════════════════════════════════════════════
// STRATEGY: Stale-While-Revalidate — JSON data files
// maxAgeMs parameter allows per-resource TTL
// ══════════════════════════════════════════════════════════════
async function staleWhileRevalidate(req, cacheName, maxAgeMs) {
  const cache  = await caches.open(cacheName);
  const cached = await cache.match(req);

  const fetchPromise = fetch(req, { cache: 'no-cache' })
    .then(async res => {
      if (res.ok) {
        const headers = new Headers(res.headers);
        headers.set('sw-cached-at', Date.now().toString());
        const stamped = new Response(await res.clone().blob(), {
          status: res.status, statusText: res.statusText, headers,
        });
        await cache.put(req, stamped);
        await trimCache(cache, DATA_CACHE_MAX, maxAgeMs);
      }
      return res;
    })
    .catch(() => null);

  if (cached) {
    const cachedAt = parseInt(cached.headers.get('sw-cached-at') || '0', 10);
    const age = Date.now() - cachedAt;

    if (age < maxAgeMs) {
      fetchPromise; // fire & forget background update
      return cached;
    }
    // Stale — wait for network, fallback to cache
    const fresh = await fetchPromise;
    return fresh || cached;
  }

  return (await fetchPromise) ||
    new Response('{}', { headers: { 'Content-Type': 'application/json' } });
}

// ══════════════════════════════════════════════════════════════
// STRATEGY: Cache First → Versioned JS/CSS
// ══════════════════════════════════════════════════════════════
async function cacheFirstStatic(req) {
  const cached = await caches.match(req);
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res.ok) {
      (await caches.open(CACHE.static)).put(req, res.clone());
    }
    return res;
  } catch (_) {
    return new Response('', { status: 408, statusText: 'Offline' });
  }
}

// ══════════════════════════════════════════════════════════════
// CACHE TRIM — Prevent storage bloat
// ══════════════════════════════════════════════════════════════
async function trimCache(cache, maxEntries, maxAgeMs) {
  try {
    const keys = await cache.keys();
    for (const key of keys) {
      const resp = await cache.match(key);
      if (resp) {
        const cachedAt = parseInt(resp.headers.get('sw-cached-at') || '0', 10);
        if (cachedAt && Date.now() - cachedAt > maxAgeMs) {
          await cache.delete(key);
        }
      }
    }
    const remaining = await cache.keys();
    if (remaining.length > maxEntries) {
      const toDelete = remaining.slice(0, remaining.length - maxEntries);
      await Promise.all(toDelete.map(k => cache.delete(k)));
    }
  } catch (_) {}
}

// ══════════════════════════════════════════════════════════════
// PUSH NOTIFICATIONS — preserved exactly
// ══════════════════════════════════════════════════════════════
const CAT_ACTIONS = {
  'latest-jobs' : [{ action: 'view', title: '💼 अभी साईट विजिट करे मुका ना खोये' }],
  'result'      : [{ action: 'view', title: '🏆 अभी साईट विजिट करे मुका ना खोये' }],
  'admit-card'  : [{ action: 'view', title: '🎫 अभी साईट विजिट करे मुका ना खोये' }],
  'answer-key'  : [{ action: 'view', title: '🔑 अभी साईट विजिट करे मुका ना खोये' }],
  'admission'   : [{ action: 'view', title: '🎓 अभी साईट विजिट करे मुका ना खोये' }],
};

self.addEventListener('push', e => {
  let d = {};
  try { d = e.data?.json() || {}; } catch (_) { d = { title: '🔔 New Update', body: 'Dekho!', url: SITE + '/' }; }

  const title    = d.title || '🔔 Top Sarkari Jobs — New Update';
  const body     = d.body  || 'Nayi sarkari vacancy aa gayi. Abhi check karo!';
  const url      = d.url   || SITE + '/';
  const category = d.category || 'latest-jobs';

  e.waitUntil(
    self.registration.showNotification(title, {
      body, icon: NOTIF_ICON, badge: NOTIF_BADGE,
      tag       : `tsj-${category}`,
      data      : { url, category },
      renotify  : true,
      requireInteraction: false,
      silent    : false,
      vibrate   : [150, 80, 150],
      actions   : CAT_ACTIONS[category] || [
        { action: 'view', title: '🔔 अभी साइट विजिट करें मौका ना खोयें' },
      ],
      timestamp : Date.now(),
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  if (e.action === 'dismiss') return;
  const url = e.notification.data?.url || SITE + '/';
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clients => {
        const existing = clients.find(c => c.url.includes('topsarkarijobs.com'));
        if (existing) { existing.focus(); return existing.navigate(url); }
        return self.clients.openWindow(url);
      })
  );
});

// ══════════════════════════════════════════════════════════════
// MESSAGES FROM MAIN THREAD
// ══════════════════════════════════════════════════════════════
self.addEventListener('message', e => {
  const { type } = e.data || {};

  if (type === 'SKIP_WAITING') {
    self.skipWaiting();
    return;
  }

  if (type === 'GET_VERSION') {
    e.source?.postMessage({ type: 'SW_VERSION', version: SW_VERSION });
    return;
  }

  if (type === 'CLEAR_ALL_CACHES') {
    e.waitUntil(
      caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
        .then(() => {
          e.source?.postMessage({ type: 'CACHES_CLEARED' });
        })
    );
    return;
  }

  if (type === 'SHOW_JOB_NOTIFICATION' || type === 'SHOW_TEST_NOTIFICATION') {
    const d = e.data.payload || {};
    e.waitUntil(
      self.registration.showNotification(d.title || '🔔 Test Alert', {
        body   : d.body    || 'Push working!',
        icon   : NOTIF_ICON, badge: NOTIF_BADGE,
        tag    : 'tsj-test', vibrate: [150, 80, 150],
        data   : { url: d.url || SITE + '/', category: d.category || 'default' },
      })
    );
    return;
  }
});
