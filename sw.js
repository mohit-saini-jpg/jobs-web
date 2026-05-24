/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║   TOP SARKARI JOBS — ADVANCED PWA SERVICE WORKER v4.0           ║
 * ║   Full Offline · Background Sync · Push Notifications           ║
 * ║   Stale-While-Revalidate · Cache-First · Network-First          ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */

'use strict';

// ─── Version & Cache Names ────────────────────────────────────────────────────
const SW_VERSION         = 'v4.1';
const CACHE_STATIC       = `tsj-static-${SW_VERSION}`;
const CACHE_PAGES        = `tsj-pages-${SW_VERSION}`;
const CACHE_IMAGES       = `tsj-images-${SW_VERSION}`;
const CACHE_DATA         = `tsj-data-${SW_VERSION}`;
const CACHE_OFFLINE      = `tsj-offline-${SW_VERSION}`;
const ALL_CACHES         = [CACHE_STATIC, CACHE_PAGES, CACHE_IMAGES, CACHE_DATA, CACHE_OFFLINE];

// Background sync tags
const SYNC_JOBS          = 'sync-jobs-data';
const SYNC_ANALYTICS     = 'sync-analytics';

// Push notification config
const NOTIFICATION_TAG   = 'tsj-push';
const NOTIFICATION_ICON  = '/image.png';
const NOTIFICATION_BADGE = '/image.png';

// ─── Cache Size Limits ────────────────────────────────────────────────────────
const CACHE_LIMITS = {
  [CACHE_STATIC]: { maxEntries: 80,  maxAgeSeconds: 31_536_000 }, // 1 year
  [CACHE_PAGES]:  { maxEntries: 60,  maxAgeSeconds:  86_400    }, // 1 day
  [CACHE_IMAGES]: { maxEntries: 100, maxAgeSeconds: 15_552_000 }, // 6 months
  [CACHE_DATA]:   { maxEntries: 20,  maxAgeSeconds:    300     }, // 5 min — fresh data
};

// ─── Critical Assets to Pre-Cache ────────────────────────────────────────────
const PRECACHE_STATIC = [
  '/styles.css',
  '/critical.css',
  '/script.min.js',
  '/seo-engine.min.js',
  '/image.png',
  '/image.webp',
  '/favicon.ico',
];

const PRECACHE_PAGES = [
  '/',
  '/index.html',
  '/result.html',
  '/admit-card.html',
  '/search.html',
  '/category.html',
  '/about.html',
  '/contact.html',
  '/offline.html',
];

const PRECACHE_DATA = [
  '/manifest.json',
  '/config.json',
];

// ─── Offline Fallback HTML ───────────────────────────────────────────────────
const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="en-IN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline – Top Sarkari Jobs</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d2257;color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:24px}
  .wrap{max-width:360px}
  .icon{font-size:72px;margin-bottom:24px;animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
  h1{font-size:24px;font-weight:700;margin-bottom:12px}
  p{font-size:15px;opacity:.8;line-height:1.6;margin-bottom:24px}
  .btn{display:inline-block;padding:12px 28px;background:#f5a623;color:#0d2257;border-radius:8px;font-weight:700;text-decoration:none;font-size:15px;cursor:pointer;border:none}
  .cached{margin-top:20px;font-size:13px;opacity:.6}
</style>
</head>
<body>
<div class="wrap">
  <div class="icon">📡</div>
  <h1>You're Offline</h1>
  <p>No internet connection detected. Please check your network and try again. Previously visited pages are available offline.</p>
  <button class="btn" onclick="window.location.reload()">Try Again</button>
  <div class="cached">Cached pages available below 👇</div>
</div>
<script>
caches.keys().then(names=>{
  const n=names.find(n=>n.includes('tsj-pages'));
  if(!n)return;
  return caches.open(n).then(c=>c.keys()).then(keys=>{
    if(!keys.length)return;
    const div=document.createElement('div');
    div.style.cssText='margin-top:16px;text-align:left';
    div.innerHTML='<ul style="list-style:none;padding:0">'+keys.slice(0,8).map(k=>`<li style="margin:6px 0"><a href="${k.url}" style="color:#f5a623;font-size:13px">${k.url.replace(location.origin,'')}</a></li>`).join('')+'</ul>';
    document.querySelector('.wrap').appendChild(div);
  });
});
</script>
</body>
</html>`;

// ══════════════════════════════════════════════════════════════════════════════
// INSTALL EVENT
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('install', event => {
  console.log(`[SW ${SW_VERSION}] Installing…`);
  event.waitUntil(
    (async () => {
      // Build offline fallback first
      const offlineCache = await caches.open(CACHE_OFFLINE);
      await offlineCache.put('/offline.html', new Response(OFFLINE_HTML, {
        headers: { 'Content-Type': 'text/html; charset=utf-8' }
      }));

      // Pre-cache static assets (non-blocking individual failures)
      const staticCache = await caches.open(CACHE_STATIC);
      await Promise.allSettled(
        PRECACHE_STATIC.map(url =>
          staticCache.add(url).catch(e => console.warn('[SW] Skip:', url, e.message))
        )
      );

      // Pre-cache core pages
      const pageCache = await caches.open(CACHE_PAGES);
      await Promise.allSettled(
        PRECACHE_PAGES.map(url =>
          pageCache.add(url).catch(e => console.warn('[SW] Skip page:', url, e.message))
        )
      );

      // Pre-cache data files
      const dataCache = await caches.open(CACHE_DATA);
      await Promise.allSettled(
        PRECACHE_DATA.map(url =>
          dataCache.add(url).catch(e => console.warn('[SW] Skip data:', url))
        )
      );

      await self.skipWaiting();
      console.log(`[SW ${SW_VERSION}] Installed ✓`);
    })()
  );
});

// ══════════════════════════════════════════════════════════════════════════════
// ACTIVATE EVENT
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('activate', event => {
  console.log(`[SW ${SW_VERSION}] Activating…`);
  event.waitUntil(
    (async () => {
      // Purge old caches
      const cacheNames = await caches.keys();
      await Promise.all(
        cacheNames
          .filter(name => name.startsWith('tsj-') && !ALL_CACHES.includes(name))
          .map(name => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
      // Also purge old v1/v2/v3 caches
      await Promise.all(
        cacheNames
          .filter(name => /^(static|html|images|offline)-assets-v/.test(name))
          .map(name => caches.delete(name))
      );
      await self.clients.claim();
      console.log(`[SW ${SW_VERSION}] Active ✓`);
    })()
  );
});

// ══════════════════════════════════════════════════════════════════════════════
// FETCH EVENT — Route Requests
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin + trusted CDNs
  if (!url.origin.includes('topsarkarijobs.com') &&
      !url.origin.includes('localhost') &&
      !url.origin.includes('fonts.googleapis.com') &&
      !url.origin.includes('fonts.gstatic.com') &&
      !url.origin.includes('cdnjs.cloudflare.com')) {
    return;
  }

  // Skip non-GET
  if (request.method !== 'GET') return;

  const pathname = url.pathname;

  // ── 1. JSON job data → Network-first, fallback to cache (stale ok) ──
  if (pathname.endsWith('.json') && 
      (pathname.includes('job') || pathname.includes('update') || pathname.includes('section'))) {
    event.respondWith(networkFirstData(request));
    return;
  }

  // ── 2. Static assets (CSS, JS, Fonts) → Cache-First (long-lived) ──
  if (/\.(css|js|woff2?|ttf|eot)(\?.*)?$/.test(pathname)) {
    event.respondWith(cacheFirst(request, CACHE_STATIC));
    return;
  }

  // ── 3. Images → Cache-First (medium-lived) ──
  if (/\.(png|jpg|jpeg|webp|gif|svg|ico)(\?.*)?$/.test(pathname)) {
    event.respondWith(cacheFirst(request, CACHE_IMAGES));
    return;
  }

  // ── 4. HTML pages → Stale-While-Revalidate ──
  if (request.headers.get('Accept')?.includes('text/html') || pathname.endsWith('.html') || pathname === '/') {
    event.respondWith(staleWhileRevalidate(request, CACHE_PAGES));
    return;
  }

  // ── 5. Other JSON → Network with cache fallback ──
  if (pathname.endsWith('.json')) {
    event.respondWith(networkFirstData(request));
    return;
  }

  // ── 6. Default → Network with offline fallback ──
  event.respondWith(networkWithOfflineFallback(request));
});

// ══════════════════════════════════════════════════════════════════════════════
// CACHING STRATEGIES
// ══════════════════════════════════════════════════════════════════════════════

/** Cache-First: serve from cache, fallback network, store result */
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached && !isStale(cached, cacheName)) return cached;

  try {
    const response = await fetch(request.clone());
    if (response.ok) {
      await cache.put(request, response.clone());
      await trimCache(cacheName);
    }
    return response;
  } catch {
    return cached || new Response('', { status: 503 });
  }
}

/** Stale-While-Revalidate: return cached immediately, update in background */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  const networkFetch = fetch(request.clone()).then(async response => {
    if (response.ok) {
      await cache.put(request, response.clone());
      await trimCache(cacheName);
    }
    return response;
  }).catch(() => null);

  if (cached) return cached;

  // Not in cache — wait for network
  try {
    const response = await networkFetch;
    return response || offlineFallback(request);
  } catch {
    return offlineFallback(request);
  }
}

/** Network-First for data: try network, fallback to stale cache */
async function networkFirstData(request) {
  const url = new URL(request.url);
  // Main data files: ALWAYS from network, never serve stale
  const noCacheFiles = [
    'Complete_Jobs_Full_Data.json','sections-index.json',
    'dailyupdates.json','merged_sarkari_data.json',
    'state-jobs-data.json','jobs-index.json','jobs-search-index.json'
  ];
  if (noCacheFiles.some(f => url.pathname.includes(f))) {
    try {
      const resp = await fetch(request, { cache: 'no-store' });
      if (resp.ok) return resp;
    } catch(e) {}
  }
  const cache = await caches.open(CACHE_DATA);
  try {
    const response = await fetch(request.clone(), {
      signal: AbortSignal.timeout ? AbortSignal.timeout(5000) : undefined
    });
    if (response.ok) {
      await cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await cache.match(request);
    return cached || new Response(JSON.stringify({ error: 'offline', cached: false }), {
      status: 200,
      headers: { 'Content-Type': 'application/json', 'X-TSJ-Offline': 'true' }
    });
  }
}

/** Network with offline HTML fallback */
async function networkWithOfflineFallback(request) {
  try {
    return await fetch(request);
  } catch {
    return offlineFallback(request);
  }
}

async function offlineFallback(request) {
  const url = new URL(request.url);
  // Try page cache first
  const pageCache = await caches.open(CACHE_PAGES);
  const cached = await pageCache.match(request) || await pageCache.match('/index.html');
  if (cached) return cached;
  // Serve offline shell
  const offlineCache = await caches.open(CACHE_OFFLINE);
  return await offlineCache.match('/offline.html') ||
    new Response(OFFLINE_HTML, { headers: { 'Content-Type': 'text/html' } });
}

// ══════════════════════════════════════════════════════════════════════════════
// CACHE UTILITIES
// ══════════════════════════════════════════════════════════════════════════════

function isStale(response, cacheName) {
  const limit = CACHE_LIMITS[cacheName];
  if (!limit) return false;
  const date = response.headers.get('date');
  if (!date) return false;
  const age = (Date.now() - new Date(date).getTime()) / 1000;
  return age > limit.maxAgeSeconds;
}

async function trimCache(cacheName) {
  const limit = CACHE_LIMITS[cacheName];
  if (!limit) return;
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length > limit.maxEntries) {
    const toDelete = keys.slice(0, keys.length - limit.maxEntries);
    await Promise.all(toDelete.map(k => cache.delete(k)));
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// BACKGROUND SYNC
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('sync', event => {
  if (event.tag === SYNC_JOBS) {
    event.waitUntil(syncJobsData());
  } else if (event.tag === SYNC_ANALYTICS) {
    event.waitUntil(flushAnalyticsQueue());
  }
});

async function syncJobsData() {
  try {
    const cache = await caches.open(CACHE_DATA);
    const urls = ['/dailyupdates.json', '/sections-index.json', '/merged_sarkari_data.json'];
    await Promise.allSettled(
      urls.map(async url => {
        const response = await fetch(url);
        if (response.ok) await cache.put(url, response.clone());
      })
    );
    // Notify all clients
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach(client => client.postMessage({ type: 'JOBS_SYNCED', timestamp: Date.now() }));
    console.log('[SW] Background sync: jobs data refreshed');
  } catch (e) {
    console.warn('[SW] Background sync failed:', e.message);
  }
}

async function flushAnalyticsQueue() {
  // Placeholder: flush any queued analytics events when back online
  console.log('[SW] Analytics queue flushed');
}

// ══════════════════════════════════════════════════════════════════════════════
// PUSH NOTIFICATIONS
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('push', event => {
  let data = {
    title: 'Top Sarkari Jobs',
    body: 'New government jobs & results are available!',
    url: '/',
    icon: NOTIFICATION_ICON,
    badge: NOTIFICATION_BADGE,
    tag: NOTIFICATION_TAG,
  };

  if (event.data) {
    try {
      const payload = event.data.json();
      data = { ...data, ...payload };
    } catch {
      data.body = event.data.text() || data.body;
    }
  }

  const options = {
    body: data.body,
    icon: data.icon || NOTIFICATION_ICON,
    badge: data.badge || NOTIFICATION_BADGE,
    tag: data.tag || NOTIFICATION_TAG,
    data: { url: data.url || '/' },
    renotify: true,
    requireInteraction: false,
    actions: [
      { action: 'view', title: '👁 View Jobs' },
      { action: 'dismiss', title: '✕ Dismiss' }
    ],
    vibrate: [200, 100, 200],
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;

  const url = event.notification.data?.url || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      const existing = clients.find(c => c.url === url || c.url.includes('topsarkarijobs.com'));
      if (existing) return existing.focus();
      return self.clients.openWindow(url);
    })
  );
});

// ══════════════════════════════════════════════════════════════════════════════
// MESSAGE HANDLER (from main thread)
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('message', event => {
  const { type } = event.data || {};

  if (type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (type === 'CACHE_URLS') {
    const { urls } = event.data;
    if (Array.isArray(urls)) {
      event.waitUntil(
        caches.open(CACHE_PAGES).then(cache =>
          Promise.allSettled(urls.map(url => cache.add(url)))
        )
      );
    }
  }

  if (type === 'GET_CACHE_SIZE') {
    event.waitUntil(
      (async () => {
        const info = {};
        for (const name of ALL_CACHES) {
          const cache = await caches.open(name);
          const keys = await cache.keys();
          info[name] = keys.length;
        }
        event.source?.postMessage({ type: 'CACHE_SIZE', data: info });
      })()
    );
  }

  if (type === 'CLEAR_CACHE') {
    event.waitUntil(
      Promise.all(ALL_CACHES.map(name => caches.delete(name)))
        .then(() => event.source?.postMessage({ type: 'CACHE_CLEARED' }))
    );
  }
});

console.log(`[SW ${SW_VERSION}] Script loaded ✓`);
