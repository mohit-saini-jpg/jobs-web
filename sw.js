/**
 * TOP SARKARI JOBS — sw.js v5
 * Ultra-optimized: JSON cached aggressively, HTML SWR, assets immutable
 */
'use strict';
const V='v5',CS=`static-${V}`,CP=`pages-${V}`,CI=`images-${V}`,CJ=`json-${V}`;
const ALL=[CS,CP,CI,CJ];

// Pre-cache critical shell (only small essentials)
const SHELL=['/','index.html','/styles.css','/all.min.css','/critical.css'];

self.addEventListener('install',e=>{
  e.waitUntil(
    caches.open(CS).then(c=>c.addAll(SHELL.map(u=>new Request(u,{cache:'reload'}))))
    .then(()=>self.skipWaiting())
  );
});

self.addEventListener('activate',e=>{
  e.waitUntil(
    caches.keys().then(keys=>Promise.all(keys.filter(k=>!ALL.includes(k)).map(k=>caches.delete(k))))
    .then(()=>self.clients.claim())
  );
});

async function trim(name,max){
  const c=await caches.open(name),k=await c.keys();
  if(k.length>max)await Promise.all(k.slice(0,k.length-max).map(r=>c.delete(r)));
}

// Cache-first with background refresh
async function cacheFirst(req,cache,max){
  const hit=await caches.match(req);
  if(hit){
    // Background refresh for JSON
    fetch(req).then(r=>{if(r.ok){caches.open(cache).then(c=>{c.put(req,r);trim(cache,max)})}}).catch(()=>{});
    return hit;
  }
  try{
    const res=await fetch(req);
    if(res.ok){const c=await caches.open(cache);c.put(req,res.clone());trim(cache,max);}
    return res;
  }catch{return new Response('{}',{status:200,headers:{'Content-Type':'application/json'}});}
}

// Stale-while-revalidate
async function swr(req,cache,max){
  const c=await caches.open(cache),hit=await c.match(req);
  const fresh=fetch(req).then(r=>{if(r.ok){c.put(req,r.clone());trim(cache,max);}return r;}).catch(()=>null);
  return hit||fresh;
}

self.addEventListener('fetch',e=>{
  const{request:req}=e;
  if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin!==location.origin)return;
  const p=url.pathname;

  // JSON: cache-first (fresh from server if cached, else fetch)
  if(p.endsWith('.json'))return e.respondWith(cacheFirst(req,CJ,30));
  // Images
  if(/\.(webp|png|jpg|jpeg|gif|svg|avif|ico)$/.test(p))return e.respondWith(cacheFirst(req,CI,100));
  // Static assets (immutable)
  if(/\.(css|js|woff2?)$/.test(p))return e.respondWith(cacheFirst(req,CS,80));
  // HTML pages
  if(p.endsWith('.html')||p==='/'||!p.includes('.'))return e.respondWith(swr(req,CP,50));
});

self.addEventListener('message',e=>{if(e.data?.type==='SKIP_WAITING')self.skipWaiting();});
