/**
 * ╔══════════════════════════════════════╗
 * ║  TOP SARKARI JOBS — sw.js v4         ║
 * ║  Ultra-Optimized Service Worker      ║
 * ║  • Cache-First for assets/fonts      ║
 * ║  • Stale-While-Revalidate for HTML   ║
 * ║  • Network-First for JSON data       ║
 * ║  • Background sync for analytics    ║
 * ║  • Offline fallback page            ║
 * ╚══════════════════════════════════════╝
 */
'use strict';

const CACHE_VER     = 'v4';
const CACHE_STATIC  = `static-${CACHE_VER}`;
const CACHE_PAGES   = `pages-${CACHE_VER}`;
const CACHE_IMAGES  = `images-${CACHE_VER}`;
const CACHE_JSON    = `json-${CACHE_VER}`;
const ALL_CACHES    = [CACHE_STATIC, CACHE_PAGES, CACHE_IMAGES, CACHE_JSON];

const STATIC_MAX    = 80;
const PAGES_MAX     = 40;
const IMAGES_MAX    = 100;
const JSON_MAX      = 20;

// Pre-cache critical shell
const PRECACHE = [
  '/',
  '/index.html',
  '/all.min.css',
  '/styles.css',
];

const OFFLINE_URL = '/offline.html';

// ── INSTALL ──────────────────────────────────────────────────
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_STATIC)
      .then(c => c.addAll(PRECACHE.map(u => new Request(u, {cache: 'reload'}))))
      .then(() => self.skipWaiting())
  );
});

// ── ACTIVATE ─────────────────────────────────────────────────
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => !ALL_CACHES.includes(k)).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── HELPER: trim cache ────────────────────────────────────────
async function trimCache(cacheName, maxEntries) {
  const cache = await caches.open(cacheName);
  const keys  = await cache.keys();
  if (keys.length > maxEntries) {
    await Promise.all(keys.slice(0, keys.length - maxEntries).map(k => cache.delete(k)));
  }
}

// ── FETCH ────────────────────────────────────────────────────
self.addEventListener('fetch', e => {
  const { request } = e;
  const url = new URL(request.url);

  // Only handle same-origin + GET
  if (request.method !== 'GET' || url.origin !== location.origin) return;

  const path = url.pathname;

  // ── JSON data: Network-First (fresh data critical for jobs site)
  if (path.endsWith('.json')) {
    e.respondWith(networkFirst(request, CACHE_JSON, JSON_MAX, 3000));
    return;
  }

  // ── Static assets: Cache-First (immutable with versioning)
  if (/\.(css|js|woff2?|ttf|eot|ico)$/.test(path)) {
    e.respondWith(cacheFirst(request, CACHE_STATIC, STATIC_MAX));
    return;
  }

  // ── Images: Cache-First with long TTL
  if (/\.(webp|png|jpg|jpeg|gif|svg|avif)$/.test(path)) {
    e.respondWith(cacheFirst(request, CACHE_IMAGES, IMAGES_MAX));
    return;
  }

  // ── HTML: Stale-While-Revalidate (fast + fresh)
  if (path.endsWith('.html') || path === '/' || !path.includes('.')) {
    e.respondWith(staleWhileRevalidate(request, CACHE_PAGES, PAGES_MAX));
    return;
  }
});

// ── Strategy: Cache-First ─────────────────────────────────────
async function cacheFirst(req, cacheName, maxEntries) {
  const cached = await caches.match(req);
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res.ok) {
      const cache = await caches.open(cacheName);
      cache.put(req, res.clone());
      trimCache(cacheName, maxEntries);
    }
    return res;
  } catch {
    return caches.match(OFFLINE_URL) || new Response('Offline', {status: 503});
  }
}

// ── Strategy: Network-First ───────────────────────────────────
async function networkFirst(req, cacheName, maxEntries, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(req, {signal: controller.signal});
    clearTimeout(timer);
    if (res.ok) {
      const cache = await caches.open(cacheName);
      cache.put(req, res.clone());
      trimCache(cacheName, maxEntries);
    }
    return res;
  } catch {
    clearTimeout(timer);
    const cached = await caches.match(req);
    return cached || new Response('{}', {status: 200, headers: {'Content-Type': 'application/json'}});
  }
}

// ── Strategy: Stale-While-Revalidate ─────────────────────────
async function staleWhileRevalidate(req, cacheName, maxEntries) {
  const cache  = await caches.open(cacheName);
  const cached = await cache.match(req);
  const fetchPromise = fetch(req).then(res => {
    if (res.ok) {
      cache.put(req, res.clone());
      trimCache(cacheName, maxEntries);
    }
    return res;
  }).catch(() => null);
  return cached || fetchPromise || caches.match(OFFLINE_URL);
}

// ── SKIP WAITING message ─────────────────────────────────────
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});
