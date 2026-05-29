/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║   ZERO-STALE CACHE ENGINE v7.0 — GitHub Optimized              ║
 * ║   Top Sarkari Jobs | topsarkarijobs.com                        ║
 * ║                                                                  ║
 * ║   ✅ Auto version bump on every GitHub deploy                   ║
 * ║   ✅ skipWaiting + clients.claim — instant takeover             ║
 * ║   ✅ Auto delete ALL old caches on activate                     ║
 * ║   ✅ Smart per-resource strategy (HTML/JSON/JS/CSS)             ║
 * ║   ✅ Stale-While-Revalidate for JSON data                       ║
 * ║   ✅ Cache-First for versioned JS/CSS (immutable)               ║
 * ║   ✅ Network-First for HTML pages                               ║
 * ║   ✅ Data cache size limit (no 2.8GB bloat)                     ║
 * ║   ✅ Age-based cache eviction for JSON                          ║
 * ║   ✅ Auto-notifies all open tabs on SW update                   ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */
'use strict';

// ══════════════════════════════════════════════════════════════
// VERSION — Auto-updated by GitHub Actions on every deploy
// Do NOT manually edit this line — it is replaced by CI/CD
// ══════════════════════════════════════════════════════════════
const SW_VERSION = '20260529215122'; // auto-updated by generate_version.js

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
const DATA_CACHE_MAX     = 25;              // max JSON entries cached
const DATA_MAX_AGE_MS    = 60 * 60 * 1000; // 1 hour max age for JSON

// Critical files to precache on install (keep tiny — only essentials)
const PRECACHE_STATIC = [
  '/styles.css',
  '/script.min.js',
  '/manifest.json',
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
          c.add(url).catch(() => {}) // fail silently per file
        ))
      ),
      caches.open(CACHE.offline).then(c =>
        c.put('offline', new Response(OFFLINE_HTML, {
          headers: { 'Content-Type': 'text/html; charset=utf-8' }
        }))
      ),
    ])
    .then(() => {
      // ✅ CRITICAL: Skip waiting → new SW activates WITHOUT waiting for old tabs to close
      return self.skipWaiting();
    })
  );
});

// ══════════════════════════════════════════════════════════════
// ACTIVATE — delete ALL stale caches, claim all clients
// ══════════════════════════════════════════════════════════════
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => {
        const stale = keys.filter(k => !ALL_CACHES.includes(k));
        if (stale.length) {
          console.log(`[SW v7] Deleting ${stale.length} old caches:`, stale);
        }
        return Promise.all(stale.map(k => caches.delete(k)));
      })
      .then(() => {
        // ✅ CRITICAL: Take control of ALL open pages immediately
        return self.clients.claim();
      })
      .then(() => {
        // Notify all open tabs → they will reload automatically
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

  // Skip non-GET requests
  if (req.method !== 'GET') return;

  // Skip browser extensions
  if (url.protocol === 'chrome-extension:' || url.protocol === 'moz-extension:') return;

  // Skip all external origins (analytics, firebase, supabase, fonts, CDN)
  if (url.hostname !== self.location.hostname) return;

  const path = url.pathname;

  // ── 1. version.json — ALWAYS fresh from network (never cache)
  if (path === '/version.json') {
    e.respondWith(
      fetch(req, { cache: 'no-store' })
        .catch(() => new Response('{}', {
          headers: { 'Content-Type': 'application/json' }
        }))
    );
    return;
  }

  // ── 2. sw.js — NEVER intercept the service worker itself
  if (path === '/sw.js') {
    e.respondWith(fetch(req, { cache: 'no-store' }));
    return;
  }

  // ── 3. HTML pages — Network First (always try fresh, fallback to cache)
  if (
    req.headers.get('accept')?.includes('text/html') ||
    path.endsWith('.html') ||
    path === '/' ||
    path.endsWith('/')
  ) {
    e.respondWith(networkFirstHTML(req));
    return;
  }

  // ── 4. /data/*.json — Stale-While-Revalidate (instant + background refresh)
  if (path.startsWith('/data/') && path.endsWith('.json')) {
    e.respondWith(staleWhileRevalidate(req, CACHE.data));
    return;
  }

  // ── 5. All other JSON files — Stale-While-Revalidate with age limit
  if (path.endsWith('.json')) {
    e.respondWith(staleWhileRevalidate(req, CACHE.data));
    return;
  }

  // ── 6. Versioned JS/CSS (has ?v= param) — Cache First (immutable)
  if (url.searchParams.has('v') && (path.endsWith('.js') || path.endsWith('.css'))) {
    e.respondWith(cacheFirstStatic(req));
    return;
  }

  // ── 7. Unversioned JS/CSS — Network First (may change on redeploy)
  if (path.endsWith('.js') || path.endsWith('.css')) {
    e.respondWith(networkFirstStatic(req));
    return;
  }

  // ── 8. Images — Fetch only, NO caching (prevents storage bloat)
  if (path.match(/\.(png|jpg|jpeg|gif|webp|svg|ico|avif)$/i)) {
    e.respondWith(
      fetch(req).catch(() => new Response('', { status: 408, statusText: 'Offline' }))
    );
    return;
  }

  // ── 9. Fonts — Cache First (fonts rarely change)
  if (path.match(/\.(woff2?|ttf|eot)$/i)) {
    e.respondWith(cacheFirstStatic(req));
    return;
  }

  // ── 10. Everything else — Network First
  e.respondWith(networkFirstHTML(req));
});

// ══════════════════════════════════════════════════════════════
// STRATEGY: Network First → HTML pages
// Always tries network, falls back to cache, then offline page
// ══════════════════════════════════════════════════════════════
async function networkFirstHTML(req) {
  try {
    const res = await fetch(req, { cache: 'no-cache' });
    if (res.ok || res.status === 304) {
      const cache = await caches.open(CACHE.pages);
      cache.put(req, res.clone()); // background update
    }
    return res;
  } catch (_) {
    // Network failed → try cache
    const cached = await caches.match(req);
    if (cached) return cached;

    // Try root page as fallback for sub-paths
    if (req.url !== `${self.location.origin}/`) {
      const rootCached = await caches.match('/');
      if (rootCached) return rootCached;
    }

    // Last resort: offline page
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
// STRATEGY: Stale-While-Revalidate → JSON data files
// Returns cached immediately, updates cache in background
// Evicts entries older than DATA_MAX_AGE_MS
// ══════════════════════════════════════════════════════════════
async function staleWhileRevalidate(req, cacheName) {
  const cache  = await caches.open(cacheName);
  const cached = await cache.match(req);

  // Always fetch fresh in background
  const fetchPromise = fetch(req, { cache: 'no-cache' })
    .then(async res => {
      if (res.ok) {
        // Clone with timestamp header for age tracking
        const headers = new Headers(res.headers);
        headers.set('sw-cached-at', Date.now().toString());
        const stamped = new Response(await res.clone().blob(), {
          status : res.status,
          statusText: res.statusText,
          headers,
        });
        await cache.put(req, stamped);
        await trimCache(cache, DATA_CACHE_MAX, DATA_MAX_AGE_MS);
      }
      return res;
    })
    .catch(() => null);

  // Check cache age
  if (cached) {
    const cachedAt = parseInt(cached.headers.get('sw-cached-at') || '0', 10);
    const age = Date.now() - cachedAt;

    if (age < DATA_MAX_AGE_MS) {
      // Fresh enough — return cached, update silently in bg
      fetchPromise; // fire & forget
      return cached;
    }
    // Stale — wait for network but return cache if network fails
    const fresh = await fetchPromise;
    return fresh || cached;
  }

  // No cache — must wait for network
  return (await fetchPromise) ||
    new Response('{}', { headers: { 'Content-Type': 'application/json' } });
}

// ══════════════════════════════════════════════════════════════
// STRATEGY: Cache First → Versioned JS/CSS (immutable)
// These files have ?v=XXX so a new version = new URL = cache miss
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
// Removes entries over limit + entries older than maxAge
// ══════════════════════════════════════════════════════════════
async function trimCache(cache, maxEntries, maxAgeMs) {
  try {
    const keys = await cache.keys();

    // Delete expired entries first
    for (const key of keys) {
      const resp = await cache.match(key);
      if (resp) {
        const cachedAt = parseInt(resp.headers.get('sw-cached-at') || '0', 10);
        if (cachedAt && Date.now() - cachedAt > maxAgeMs) {
          await cache.delete(key);
        }
      }
    }

    // Then trim by count
    const remaining = await cache.keys();
    if (remaining.length > maxEntries) {
      const toDelete = remaining.slice(0, remaining.length - maxEntries);
      await Promise.all(toDelete.map(k => cache.delete(k)));
    }
  } catch (_) {}
}

// ══════════════════════════════════════════════════════════════
// PUSH NOTIFICATIONS
// ══════════════════════════════════════════════════════════════
const CAT_ACTIONS = {
  'latest-jobs' : [{ action: 'view', title: '💼 Apply Now'    }, { action: 'dismiss', title: '✕' }],
  'result'      : [{ action: 'view', title: '🏆 Result Dekho' }, { action: 'dismiss', title: '✕' }],
  'admit-card'  : [{ action: 'view', title: '🎫 Download'     }, { action: 'dismiss', title: '✕' }],
  'answer-key'  : [{ action: 'view', title: '🔑 Dekho'        }, { action: 'dismiss', title: '✕' }],
  'admission'   : [{ action: 'view', title: '🎓 Apply'        }, { action: 'dismiss', title: '✕' }],
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
        { action: 'view',    title: '👁 Dekho' },
        { action: 'dismiss', title: '✕' },
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

  // Manual skip waiting (from update detection)
  if (type === 'SKIP_WAITING') {
    self.skipWaiting();
    return;
  }

  // Version query
  if (type === 'GET_VERSION') {
    e.source?.postMessage({ type: 'SW_VERSION', version: SW_VERSION });
    return;
  }

  // Manual full cache clear
  if (type === 'CLEAR_ALL_CACHES') {
    e.waitUntil(
      caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
        .then(() => {
          e.source?.postMessage({ type: 'CACHES_CLEARED' });
        })
    );
    return;
  }

  // Push notification tests
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
