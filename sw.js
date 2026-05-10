/**
 * Service Worker — Top Sarkari Jobs
 * Features: Push Notifications, Cache-First for static assets,
 *           Network-First for dynamic data, Offline fallback
 */

const CACHE_NAME = 'tsj-v4';
const STATIC_CACHE = 'tsj-static-v4';
const DATA_CACHE = 'tsj-data-v4';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/styles.css',
  '/script.js',
  '/seo-engine.js',
  '/fonts/fa/all.min.css',
  '/image.ico',
  '/image.webp',
  '/offline.html'
];

const CACHEABLE_PATTERNS = [
  /\.(css|js|woff2?|ico|webp|png|jpg|jpeg|svg)$/,
  /fonts\.googleapis\.com/,
  /fonts\.gstatic\.com/
];

const NETWORK_FIRST_PATTERNS = [
  /dynamic-sections\.json$/,
  /jobs\.json$/,
  /jobs-index\.json/,
  /Complete_Jobs_Full_Data\.json/,
  /state-jobs-data\.json$/
];

/* ── Install: pre-cache static assets ── */
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(STATIC_ASSETS.filter(url => !url.includes('offline.html') || true));
    }).then(() => self.skipWaiting())
  );
});

/* ── Activate: clean old caches ── */
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== STATIC_CACHE && k !== DATA_CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

/* ── Fetch: smart caching strategy ── */
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = req.url;

  // Skip non-http(s)
  if (!url.startsWith('http')) return;

  // Google Analytics — don't cache
  if (url.includes('google-analytics') || url.includes('googletagmanager')) return;

  // Network-first for JSON data files
  if (NETWORK_FIRST_PATTERNS.some(p => p.test(url))) {
    event.respondWith(networkFirst(req));
    return;
  }

  // Cache-first for static assets
  if (CACHEABLE_PATTERNS.some(p => p.test(url))) {
    event.respondWith(cacheFirst(req));
    return;
  }

  // Stale-while-revalidate for HTML pages
  if (req.destination === 'document') {
    event.respondWith(staleWhileRevalidate(req));
    return;
  }
});

async function cacheFirst(req) {
  const cached = await caches.match(req);
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(req, res.clone());
    }
    return res;
  } catch (e) {
    return new Response('', { status: 503 });
  }
}

async function networkFirst(req) {
  try {
    const res = await fetch(req, { signal: AbortSignal.timeout?.(5000) });
    if (res.ok) {
      const cache = await caches.open(DATA_CACHE);
      cache.put(req, res.clone());
    }
    return res;
  } catch (e) {
    const cached = await caches.match(req);
    return cached || new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } });
  }
}

async function staleWhileRevalidate(req) {
  const cached = await caches.match(req);
  const fetchPromise = fetch(req).then(res => {
    if (res.ok) {
      caches.open(STATIC_CACHE).then(c => c.put(req, res.clone()));
    }
    return res;
  }).catch(() => cached || new Response('Offline', { status: 503 }));
  return cached || fetchPromise;
}

/* ── Push Notification Handler ── */
self.addEventListener('push', event => {
  const data = event.data?.json() || {};
  const title = data.title || '🔔 Top Sarkari Jobs';
  const options = {
    body: data.body || 'New government job notification! Tap to see latest updates.',
    icon: '/image.ico',
    badge: '/image.ico',
    tag: data.tag || 'tsj-update',
    renotify: true,
    requireInteraction: false,
    actions: [
      { action: 'view', title: '👀 View Jobs', icon: '/image.ico' },
      { action: 'dismiss', title: '✕ Dismiss' }
    ],
    data: { url: data.url || '/' }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

/* ── Notification Click ── */
self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const client of list) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});
