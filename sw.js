/**
 * TOP SARKARI JOBS — Zero-Stale Service Worker v6.0
 * ✅ Auto cache cleanup  ✅ Skip waiting  ✅ Force update detection
 * ✅ 2.8GB cache fix     ✅ Smart strategies per resource type
 */
'use strict';

// ── VERSION — change this on every deploy to force cache bust ─────────
const SW_VERSION = '202605260153';

// ── Cache names — version-based, old ones auto-deleted on activate ────
const CACHE = {
  static : `tsj-static-${SW_VERSION}`,
  pages  : `tsj-pages-${SW_VERSION}`,
  data   : `tsj-data-${SW_VERSION}`,
  offline: `tsj-offline-${SW_VERSION}`,
  // NO image cache — images caused 2.8GB bloat!
};
const ALL_CACHES = Object.values(CACHE);

const SITE        = 'https://www.topsarkarijobs.com';
const NOTIF_ICON  = '/icons/icon-192x192.png';
const NOTIF_BADGE = '/icons/icon-96x96.png';

// Only precache tiny critical files — NOT images, NOT large JSON!
const PRECACHE_STATIC = [
  '/styles.css',
  '/script.min.js',
  '/manifest.json',
];

// Max data cache size to prevent 2.8GB bloat
const DATA_CACHE_MAX_ENTRIES = 20;
const DATA_CACHE_MAX_AGE_MS  = 60 * 60 * 1000; // 1 hour

const OFFLINE_HTML = `<!DOCTYPE html><html lang="en-IN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline – Top Sarkari Jobs</title>
<style>*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0d2257;color:#fff;
min-height:100vh;display:flex;align-items:center;justify-content:center;
text-align:center;padding:24px}
.w{max-width:360px}.ic{font-size:72px;margin-bottom:24px}
h1{font-size:24px;font-weight:700;margin-bottom:12px}
p{font-size:15px;opacity:.8;line-height:1.6;margin-bottom:24px}
.btn{display:inline-block;padding:12px 28px;background:#f5a623;
color:#0d2257;border-radius:8px;font-weight:700;font-size:15px;
cursor:pointer;border:none}</style></head>
<body><div class="w"><div class="ic">📡</div><h1>You're Offline</h1>
<p>Internet nahi hai. Enable karein aur retry karein.</p>
<button class="btn" onclick="location.reload()">Try Again</button>
</div></body></html>`;

// ══════════════════════════════════════════════════════════════
// INSTALL — cache minimal critical assets only
// ══════════════════════════════════════════════════════════════
self.addEventListener('install', e => {
  e.waitUntil(
    Promise.allSettled([
      caches.open(CACHE.static).then(c =>
        Promise.allSettled(PRECACHE_STATIC.map(url =>
          c.add(url).catch(() => {}) // ignore individual failures
        ))
      ),
      caches.open(CACHE.offline).then(c =>
        c.put('offline', new Response(OFFLINE_HTML, {
          headers: { 'Content-Type': 'text/html' }
        }))
      ),
    ]).then(() => {
      // ✅ CRITICAL: Skip waiting immediately — users get new SW right away
      return self.skipWaiting();
    })
  );
});

// ══════════════════════════════════════════════════════════════
// ACTIVATE — delete ALL old caches + claim clients
// ══════════════════════════════════════════════════════════════
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => {
        const toDelete = keys.filter(k => !ALL_CACHES.includes(k));
        console.log(`[SW v6] Deleting ${toDelete.length} old caches:`, toDelete);
        return Promise.all(toDelete.map(k => caches.delete(k)));
      })
      .then(() => {
        // ✅ CRITICAL: Take control of ALL open pages immediately
        return self.clients.claim();
      })
      .then(() => {
        // Notify all clients that SW updated — they'll show update toast
        return self.clients.matchAll({ type: 'window' }).then(clients => {
          clients.forEach(c => c.postMessage({
            type: 'SW_UPDATED',
            version: SW_VERSION
          }));
        });
      })
  );
});

// ══════════════════════════════════════════════════════════════
// FETCH — Smart strategies per resource type
// ══════════════════════════════════════════════════════════════
self.addEventListener('fetch', e => {
  const { request: req } = e;
  const url = new URL(req.url);

  // Skip non-GET
  if (req.method !== 'GET') return;
  // Skip extensions
  if (url.protocol === 'chrome-extension:') return;
  // Skip analytics/firebase/external
  if (
    url.hostname.includes('google-analytics') ||
    url.hostname.includes('googletagmanager') ||
    url.hostname.includes('gstatic.com') ||
    url.hostname.includes('firebase') ||
    url.hostname.includes('supabase') ||
    url.hostname !== self.location.hostname
  ) return;

  const path = url.pathname;

  // ── version.json: ALWAYS network, never cache ─────────────────────
  if (path === '/version.json') {
    e.respondWith(
      fetch(req, { cache: 'no-store' }).catch(() =>
        new Response('{}', { headers: { 'Content-Type': 'application/json' } })
      )
    );
    return;
  }

  // ── sw.js: NEVER cache the service worker itself ──────────────────
  if (path === '/sw.js') {
    e.respondWith(fetch(req, { cache: 'no-store' }));
    return;
  }

  // ── HTML pages: Network First (always fresh) ──────────────────────
  if (req.headers.get('accept')?.includes('text/html') || path.endsWith('.html')) {
    e.respondWith(networkFirstPage(req));
    return;
  }

  // ── JSON data: Stale-While-Revalidate (fast + fresh) ─────────────
  if (path.endsWith('.json')) {
    e.respondWith(staleWhileRevalidateData(req));
    return;
  }

  // ── Images: NO caching (was causing 2.8GB bloat!) ─────────────────
  if (path.match(/\.(png|jpg|jpeg|gif|webp|svg|ico)$/i)) {
    e.respondWith(fetch(req).catch(() => new Response('', { status: 408 })));
    return;
  }

  // ── CSS/JS with version param: Cache First (immutable) ───────────
  if (url.searchParams.has('v') &&
      (path.endsWith('.js') || path.endsWith('.css'))) {
    e.respondWith(cacheFirstStatic(req));
    return;
  }

  // ── Everything else: Network first ───────────────────────────────
  e.respondWith(networkFirstPage(req));
});

// ── Strategy: Network First (HTML pages) ────────────────────────────
async function networkFirstPage(req) {
  try {
    const r = await fetch(req, { cache: 'no-cache' });
    if (r.ok) {
      const c = await caches.open(CACHE.pages);
      c.put(req, r.clone());
    }
    return r;
  } catch {
    const cached = await caches.match(req);
    if (cached) return cached;
    return (await caches.match('offline', { cacheName: CACHE.offline })) ||
           new Response(OFFLINE_HTML, { headers: { 'Content-Type': 'text/html' } });
  }
}

// ── Strategy: Stale-While-Revalidate (JSON data) ────────────────────
async function staleWhileRevalidateData(req) {
  const cache  = await caches.open(CACHE.data);
  const cached = await cache.match(req);

  // Always fetch fresh in background
  const fetchPromise = fetch(req, { cache: 'no-cache' })
    .then(async r => {
      if (r.ok) {
        await cache.put(req, r.clone());
        await trimDataCache(cache); // prevent bloat
      }
      return r;
    })
    .catch(() => null);

  // Return cached immediately if available, else wait for network
  return cached || await fetchPromise ||
         new Response('{}', { headers: { 'Content-Type': 'application/json' } });
}

// ── Strategy: Cache First (versioned JS/CSS) ─────────────────────────
async function cacheFirstStatic(req) {
  const cached = await caches.match(req);
  if (cached) return cached;
  try {
    const r = await fetch(req);
    if (r.ok) (await caches.open(CACHE.static)).put(req, r.clone());
    return r;
  } catch {
    return new Response('', { status: 408 });
  }
}

// ── Trim data cache to prevent bloat ─────────────────────────────────
async function trimDataCache(cache) {
  const keys = await cache.keys();
  if (keys.length > DATA_CACHE_MAX_ENTRIES) {
    // Delete oldest entries
    const toDelete = keys.slice(0, keys.length - DATA_CACHE_MAX_ENTRIES);
    await Promise.all(toDelete.map(k => cache.delete(k)));
  }
}

// ══════════════════════════════════════════════════════════════
// PUSH NOTIFICATIONS — FCM V1
// ══════════════════════════════════════════════════════════════
const CAT_URLS = {
  'latest-jobs': SITE + '/section/latest-jobs/',
  'result'     : SITE + '/section/results/',
  'results'    : SITE + '/section/results/',
  'admit-card' : SITE + '/section/admit-card/',
  'admission'  : SITE + '/section/admissions/',
  'answer-key' : SITE + '/section/answer-key/',
};

self.addEventListener('push', e => {
  let d = {
    title: '🔔 Top Sarkari Jobs', body: 'Nayi Sarkari Naukri aa gayi!',
    url: SITE + '/', category: 'default',
    icon: NOTIF_ICON, badge: NOTIF_BADGE, tag: 'tsj-push',
  };
  if (e.data) {
    try {
      const p = e.data.json();
      const src = p.data || p.notification || p;
      if (src.title)    d.title    = src.title;
      if (src.body)     d.body     = src.body;
      if (src.url)      d.url      = src.url;
      if (src.category) d.category = src.category;
      if (!src.url && src.category) d.url = CAT_URLS[src.category] || (SITE + '/');
    } catch { try { d.body = e.data.text(); } catch {} }
  }

  const CAT_ACTIONS = {
    'latest-jobs': [{action:'view',title:'💼 Jobs Dekho'},{action:'dismiss',title:'✕'}],
    'result'     : [{action:'view',title:'🏆 Result Dekho'},{action:'dismiss',title:'✕'}],
    'admit-card' : [{action:'view',title:'🎫 Download Karo'},{action:'dismiss',title:'✕'}],
    'admission'  : [{action:'view',title:'🎓 Dekho'},{action:'dismiss',title:'✕'}],
    'answer-key' : [{action:'view',title:'🔑 Dekho'},{action:'dismiss',title:'✕'}],
  };

  e.waitUntil(self.registration.showNotification(d.title, {
    body: d.body, icon: d.icon, badge: d.badge, tag: d.tag,
    data: { url: d.url, category: d.category },
    renotify: true, requireInteraction: false, silent: false,
    vibrate: [150, 80, 150],
    actions: CAT_ACTIONS[d.category] || [{action:'view',title:'👁 Dekho'},{action:'dismiss',title:'✕'}],
    timestamp: Date.now(),
  }));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  if (e.action === 'dismiss') return;
  const url = e.notification.data?.url || SITE + '/';
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clients => {
        const ex = clients.find(c => c.url.includes('topsarkarijobs.com'));
        if (ex) { ex.focus(); return ex.navigate(url); }
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
  }

  if (type === 'GET_VERSION') {
    e.source?.postMessage({ type: 'SW_VERSION', version: SW_VERSION });
  }

  if (type === 'CLEAR_ALL_CACHES') {
    // Manual cache clear trigger from page
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))));
  }

  if (type === 'SHOW_JOB_NOTIFICATION' || type === 'SHOW_TEST_NOTIFICATION') {
    const d = e.data.payload || {};
    e.waitUntil(
      self.registration.showNotification(d.title || '🔔 Test Alert', {
        body   : d.body || 'Push working!',
        icon   : NOTIF_ICON, badge: NOTIF_BADGE,
        tag    : 'tsj-test', vibrate: [150, 80, 150],
        data   : { url: d.url || SITE + '/', category: d.category || 'default' },
      })
    );
  }
});
