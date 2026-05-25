/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║  TOP SARKARI JOBS — PWA SERVICE WORKER v5.0                     ║
 * ║  FCM Push · Offline · Stale-While-Revalidate · Background Sync  ║
 * ║  Project: job-portal-750e0 | Sender: 230495552068               ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */
'use strict';

const SW_VERSION   = 'v5.0';
const CACHE_STATIC = `tsj-static-${SW_VERSION}`;
const CACHE_PAGES  = `tsj-pages-${SW_VERSION}`;
const CACHE_IMAGES = `tsj-images-${SW_VERSION}`;
const CACHE_DATA   = `tsj-data-${SW_VERSION}`;
const CACHE_OFFLN  = `tsj-offline-${SW_VERSION}`;
const ALL_CACHES   = [CACHE_STATIC,CACHE_PAGES,CACHE_IMAGES,CACHE_DATA,CACHE_OFFLN];

const NOTIF_ICON   = '/icons/icon-192x192.png';
const NOTIF_BADGE  = '/icons/icon-96x96.png';
const SITE         = 'https://www.topsarkarijobs.com';

const CAT_URLS = {
  'latest-jobs': SITE + '/section/latest-jobs/',
  'result':      SITE + '/section/results/',
  'results':     SITE + '/section/results/',
  'admit-card':  SITE + '/section/admit-card/',
  'admission':   SITE + '/section/admission/',
  'answer-key':  SITE + '/section/answer-key/',
};

const PRECACHE_STATIC = [
  '/styles.css','/critical.css','/script.min.js','/seo-engine.min.js',
  '/image.png','/image.webp','/favicon.ico',
];
const PRECACHE_PAGES = [
  '/','/index.html','/result.html','/admit-card.html',
  '/search.html','/category.html','/about.html','/offline.html',
];
const PRECACHE_DATA = ['/manifest.json','/config.json'];

const OFFLINE_HTML = `<!DOCTYPE html><html lang="en-IN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline – Top Sarkari Jobs</title>
<style>*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0d2257;color:#fff;
min-height:100vh;display:flex;align-items:center;justify-content:center;
text-align:center;padding:24px}
.w{max-width:360px}.ic{font-size:72px;margin-bottom:24px;
animation:p 2s infinite}@keyframes p{0%,100%{opacity:1}50%{opacity:.5}}
h1{font-size:24px;font-weight:700;margin-bottom:12px}
p{font-size:15px;opacity:.8;line-height:1.6;margin-bottom:24px}
.btn{display:inline-block;padding:12px 28px;background:#f5a623;
color:#0d2257;border-radius:8px;font-weight:700;font-size:15px;
cursor:pointer;border:none}</style></head>
<body><div class="w"><div class="ic">📡</div><h1>You're Offline</h1>
<p>Internet nahi hai. Enable karein aur retry karein.</p>
<button class="btn" onclick="location.reload()">Try Again</button>
</div></body></html>`;

// ── INSTALL ───────────────────────────────────────────────────────────────────
self.addEventListener('install', e => {
  e.waitUntil(
    Promise.allSettled([
      caches.open(CACHE_STATIC).then(c => c.addAll(PRECACHE_STATIC)).catch(()=>{}),
      caches.open(CACHE_PAGES).then(c  => c.addAll(PRECACHE_PAGES)).catch(()=>{}),
      caches.open(CACHE_DATA).then(c   => c.addAll(PRECACHE_DATA)).catch(()=>{}),
      caches.open(CACHE_OFFLN).then(c  =>
        c.put('offline', new Response(OFFLINE_HTML, {headers:{'Content-Type':'text/html'}}))
      ),
    ])
    // FIXED: Removed auto-skipWaiting → prevents forced page reload
  );
});

// ── ACTIVATE ──────────────────────────────────────────────────────────────────
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => !ALL_CACHES.includes(k)).map(k => caches.delete(k))))
      // FIXED: Removed clients.claim() - caused page reload on SW activate
      // Pages get new SW on next natural navigation instead
  );
});

// ── FETCH ─────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', e => {
  const { request: req } = e;
  const url = new URL(req.url);
  if (req.method !== 'GET') return;
  if (url.protocol === 'chrome-extension:') return;
  if (url.hostname.includes('google-analytics') || url.hostname.includes('googletagmanager') ||
      url.hostname.includes('gstatic.com') || url.hostname.includes('firebase')) return;
  if (url.pathname.endsWith('.json') && url.origin === self.location.origin) {
    e.respondWith(swrData(req)); return;
  }
  if (req.headers.get('accept')?.includes('text/html')) {
    e.respondWith(netFirstPage(req)); return;
  }
  e.respondWith(cacheFirst(req));
});

async function cacheFirst(req) {
  const c = await caches.match(req);
  if (c) return c;
  try {
    const r = await fetch(req);
    if (r.ok) (await caches.open(CACHE_STATIC)).put(req, r.clone());
    return r;
  } catch { return new Response('', {status:408}); }
}

async function netFirstPage(req) {
  try {
    const r = await fetch(req);
    if (r.ok) (await caches.open(CACHE_PAGES)).put(req, r.clone());
    return r;
  } catch {
    const c = await caches.match(req);
    if (c) return c;
    return (await caches.match('offline',{cacheName:CACHE_OFFLN})) ||
           new Response(OFFLINE_HTML, {headers:{'Content-Type':'text/html'}});
  }
}

async function swrData(req) {
  const cache  = await caches.open(CACHE_DATA);
  const cached = await cache.match(req);
  const fetchP = fetch(req, {cache:'default'})
    .then(r => { if (r.ok) cache.put(req, r.clone()); return r; })
    .catch(() => null);
  return cached || await fetchP || new Response('{}',{headers:{'Content-Type':'application/json'}});
}

// ══════════════════════════════════════════════════════════════════════════════
// PUSH NOTIFICATIONS — FCM V1
// ══════════════════════════════════════════════════════════════════════════════
self.addEventListener('push', e => {
  let d = { title:'🔔 Top Sarkari Jobs', body:'Nayi Sarkari Naukri aa gayi!',
            url: SITE + '/', category:'default', icon:NOTIF_ICON, badge:NOTIF_BADGE,
            tag:'tsj-push', image:'' };

  if (e.data) {
    try {
      const p = e.data.json();
      // Support FCM data payload, notification payload, and nested formats
      const src = p.data || p.notification || p;
      if (src.title)    d.title    = src.title;
      if (src.body)     d.body     = src.body;
      if (src.url)      d.url      = src.url;
      if (src.category) d.category = src.category;
      if (src.icon)     d.icon     = src.icon;
      if (src.image)    d.image    = src.image;
      if (src.tag)      d.tag      = src.tag;
      // Route by category if no specific URL
      if (!src.url && src.category) d.url = CAT_URLS[src.category] || (SITE + '/');
    } catch { try { d.body = e.data.text(); } catch {} }
  }

  const CAT_ACTIONS = {
    'latest-jobs': [{action:'view',title:'💼 Jobs Dekho'},{action:'dismiss',title:'✕'}],
    'result':      [{action:'view',title:'🏆 Result Dekho'},{action:'dismiss',title:'✕'}],
    'admit-card':  [{action:'view',title:'🎫 Download Karo'},{action:'dismiss',title:'✕'}],
    'admission':   [{action:'view',title:'🎓 Dekho'},{action:'dismiss',title:'✕'}],
    'answer-key':  [{action:'view',title:'🔑 Dekho'},{action:'dismiss',title:'✕'}],
  };

  const opts = {
    body:   d.body, icon: d.icon, badge: d.badge, tag: d.tag,
    data:   { url: d.url, category: d.category },
    renotify: true, requireInteraction: false, silent: false,
    vibrate: [150, 80, 150, 80, 300],
    actions: CAT_ACTIONS[d.category] || [{action:'view',title:'👁 Dekho'},{action:'dismiss',title:'✕'}],
    timestamp: Date.now(),
  };
  if (d.image) opts.image = d.image;

  e.waitUntil(self.registration.showNotification(d.title, opts));
});

// ── NOTIFICATION CLICK ────────────────────────────────────────────────────────
self.addEventListener('notificationclick', e => {
  e.notification.close();
  if (e.action === 'dismiss') return;
  const url = e.notification.data?.url || SITE + '/';
  e.waitUntil(
    self.clients.matchAll({type:'window', includeUncontrolled:true}).then(clients => {
      const ex = clients.find(c => c.url.includes('topsarkarijobs.com'));
      if (ex) { ex.focus(); return ex.navigate(url); }
      return self.clients.openWindow(url);
    })
  );
});

// ── BACKGROUND SYNC ───────────────────────────────────────────────────────────
self.addEventListener('sync', e => {
  if (e.tag === 'sync-jobs-data') {
    e.waitUntil(
      fetch('/dailyupdates.json',{cache:'no-cache'})
        .then(r => r.ok ? caches.open(CACHE_DATA).then(c => c.put('/dailyupdates.json',r)) : null)
        .catch(()=>{})
    );
  }
});

// ── MESSAGES FROM MAIN THREAD ─────────────────────────────────────────────────
self.addEventListener('message', e => {
  const { type } = e.data || {};
  if (type === 'SKIP_WAITING') self.skipWaiting();
  if (type === 'CACHE_URLS') {
    const { urls } = e.data;
    if (Array.isArray(urls)) {
      e.waitUntil(
        caches.open(CACHE_PAGES).then(c => Promise.allSettled(urls.map(u => c.add(u))))
      );
    }
  }
  if (type === 'SHOW_JOB_NOTIFICATION' || type === 'SHOW_TEST_NOTIFICATION') {
    const d = e.data.payload || {};
    e.waitUntil(
      self.registration.showNotification(d.title || '🔔 Test Alert', {
        body:    d.body || 'Push working!',
        icon:    NOTIF_ICON, badge: NOTIF_BADGE,
        tag:     'tsj-test', vibrate: [150, 80, 150],
        data:    { url: d.url || SITE + '/', category: d.category || 'default' },
      })
    );
  }
});
