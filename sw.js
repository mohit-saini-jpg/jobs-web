/**
 * Service Worker — Top Sarkari Jobs
 * ✅ Auto cache version using BUILD_DATE — jab bhi code update ho, cache khud clear hoga
 * ✅ Push Notifications, Cache-First, Network-First, Offline fallback
 */

// 🔑 IMPORTANT: Yahan date/time change karo jab bhi koi file update karo
// Format: YYYYMMDD-HHMM
const BUILD_VERSION = '20260516-1200';

const CACHE_NAME = `tsj-static-${BUILD_VERSION}`;
const DATA_CACHE = `tsj-data-${BUILD_VERSION}`;

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
  /merged_sarkari_data\.json$/,
  /dynamic-sections\.json$/,
  /jobs\.json$/,
  /jobs-index\.json/,
  /Complete_Jobs_Full_Data\.json/,
  /state-jobs-data\.json$/,
  /dailyupdates\.json$/
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME && k !== DATA_CACHE).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
  if (event.data?.type === 'CLEAR_CACHE') {
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))));
  }
  if (event.data?.type === 'GET_VERSION') {
    event.ports[0]?.postMessage({ version: BUILD_VERSION });
  }
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = req.url;
  if (!url.startsWith('http')) return;
  if (url.includes('google-analytics') || url.includes('googletagmanager')) return;

  if (NETWORK_FIRST_PATTERNS.some(p => p.test(url))) {
    event.respondWith(networkFirst(req)); return;
  }
  if (CACHEABLE_PATTERNS.some(p => p.test(url))) {
    event.respondWith(cacheFirst(req)); return;
  }
  if (req.destination === 'document') {
    event.respondWith(staleWhileRevalidate(req)); return;
  }
});

async function cacheFirst(req) {
  const cached = await caches.match(req);
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res.ok) (await caches.open(CACHE_NAME)).put(req, res.clone());
    return res;
  } catch { return new Response('', { status: 503 }); }
}

async function networkFirst(req) {
  try {
    const res = await fetch(req, { signal: AbortSignal.timeout?.(8000) });
    if (res.ok) (await caches.open(DATA_CACHE)).put(req, res.clone());
    return res;
  } catch {
    return await caches.match(req) || new Response('[]', { status: 200, headers: { 'Content-Type': 'application/json' } });
  }
}

async function staleWhileRevalidate(req) {
  const cached = await caches.match(req);
  const fetchPromise = fetch(req).then(res => {
    if (res.ok) caches.open(CACHE_NAME).then(c => c.put(req, res.clone()));
    return res;
  }).catch(() => cached || new Response('Offline', { status: 503 }));
  return cached || fetchPromise;
}

self.addEventListener('push', event => {
  const data = event.data?.json() || {};
  event.waitUntil(self.registration.showNotification(
    data.title || '🔔 Top Sarkari Jobs',
    {
      body: data.body || 'New government job notification!',
      icon: '/image.ico', badge: '/image.ico',
      tag: data.tag || 'tsj-update', renotify: true,
      actions: [{ action: 'view', title: '👀 View Jobs' }, { action: 'dismiss', title: '✕ Dismiss' }],
      data: { url: data.url || '/' }
    }
  ));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) {
        if (c.url.includes(self.location.origin) && 'focus' in c) { c.navigate(url); return c.focus(); }
      }
      return clients.openWindow(url);
    })
  );
});
