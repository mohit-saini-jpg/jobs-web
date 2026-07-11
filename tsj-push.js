/**
 * TOP SARKARI JOBS — Push Notification System v4.0
 * Firebase Cloud Messaging V1 | job-portal-750e0
 * FIXED: Prompt always shows | Auto rotate job notifications | Bell button
 */
(function () {
  'use strict';

  // ── Firebase Config ───────────────────────────────────────────────
  var FCM = {
    apiKey:            "AIzaSyBb4R2TlJgowhHAsROO9Lue5ztI_BtF1xY",
    authDomain:        "job-portal-750e0.firebaseapp.com",
    projectId:         "job-portal-750e0",
    storageBucket:     "job-portal-750e0.firebasestorage.app",
    messagingSenderId: "230495552068",
    appId:             "1:230495552068:web:9b3980e4bf831b7366f211",
    measurementId:     "G-GBET4E4DF3",
    vapidKey:          "BHHqgCttMPzjG0B-KnYUgVu3nrleMV8FUHYQyIQpqC2xtPozCW_s2ZURExUHsvBE05jk4SzxeFEymTwbUqNua58",
    tokenEndpoint:     "https://cykkclkfimmqbahanidg.supabase.co/functions/v1/save-push-token",
  };

  var SITE = 'https://www.topsarkarijobs.com';

  var CATS = {
    'latest-jobs': { label:'Latest Jobs',  url: SITE+'/section/latest-jobs/',  emoji:'💼', color:'#1a56db', dataKey:'SR_Latest_Jobs'  },
    'result':      { label:'Results',      url: SITE+'/section/results/',      emoji:'🏆', color:'#166534', dataKey:'SR_Result'       },
    'admit-card':  { label:'Admit Card',   url: SITE+'/section/admit-card/',   emoji:'🎫', color:'#b45309', dataKey:'SR_Admit_Card'   },
    'admission':   { label:'Admission',    url: SITE+'/section/admissions/',   emoji:'🎓', color:'#7c3aed', dataKey:'SR_Admission'    },
    'answer-key':  { label:'Answer Key',   url: SITE+'/section/answer-key/',   emoji:'🔑', color:'#be185d', dataKey:'SR_Answer_Key'   },
  };

  // ── Storage — v4 keys (clears all old keys on load) ───────────────
  var V = 'tsj_v4_';
  var SK = { TOKEN:'tsj_v4_token', SUB:'tsj_v4_sub', ASKED:'tsj_v4_asked', DIS:'tsj_v4_dis', JOBS:'tsj_v4_jobs', IDX:'tsj_v4_idx' };

  // Clear ALL old version keys on first run
  (function clearOldKeys() {
    var oldPrefixes = ['tsj_push_', 'tsj_fcm_token', 'tsj_fcm_token_v', 'tsj_push_sub_v', 'tsj_push_asked_v', 'tsj_push_dis_v', 'tsj_unblock_shown', 'tsj_v3_'];
    try {
      var toRemove = [];
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && oldPrefixes.some(function(p){ return k.indexOf(p) === 0; })) {
          toRemove.push(k);
        }
      }
      toRemove.forEach(function(k){ localStorage.removeItem(k); });
      if (toRemove.length) console.log('[TSJPush] Cleared', toRemove.length, 'old keys');
    } catch(e) {}
  })();

  function sg(k)   { try { return JSON.parse(localStorage.getItem(k)); } catch(e) { return null; } }
  function ss(k,v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch(e) {} }

  // ── Device Detection ──────────────────────────────────────────────
  var ua       = navigator.userAgent || '';
  var isIOS    = /iPad|iPhone|iPod/i.test(ua) && !window.MSStream;
  var isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(ua);
  var canPush  = 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window;

  // ── State ─────────────────────────────────────────────────────────
  var _msg = null, _ready = false, _swReg = null;
  var _jobCache = null;   // cached merged_sarkari_data jobs
  var _jobIdx   = 0;      // current rotation index

  // ══════════════════════════════════════════════════════════════════
  // FIREBASE INIT
  // ══════════════════════════════════════════════════════════════════
  function loadFirebase() {
    return new Promise(function(res, rej) {
      if (window.firebase && window.firebase.messaging) return res(window.firebase);
      var s1 = document.createElement('script');
      s1.src = 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js';
      s1.async = true;   // non-blocking (this whole loader runs lazily via tsj-push)
      s1.onload = function() {
        var s2 = document.createElement('script');
        s2.src = 'https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js';
        s2.async = true;  // order guaranteed: s2 loaded inside s1.onload
        s2.onload  = function() { res(window.firebase); };
        s2.onerror = function() { rej(new Error('FCM load failed')); };
        document.head.appendChild(s2);
      };
      s1.onerror = function() { rej(new Error('Firebase load failed')); };
      document.head.appendChild(s1);
    });
  }

  function initFCM() {
    if (_ready) return Promise.resolve(_msg);
    return loadFirebase().then(function(fb) {
      if (!fb.apps.length) fb.initializeApp(FCM);
      _msg   = fb.messaging();
      _ready = true;
      _msg.onMessage(function(p) { showFgToast(p); });
      return _msg;
    });
  }

  function regSW() {
    if (_swReg) return Promise.resolve(_swReg);
    if (!('serviceWorker' in navigator)) return Promise.reject('no SW');
    // FIXED: Use existing SW registration — do NOT register again
    // pwa-install.js already registers /sw.js
    // Multiple registrations caused page refresh loop
    return navigator.serviceWorker.ready.then(function(r) {
      _swReg = r;
      return r;
    });
  }

  function getToken(m) {
    return navigator.serviceWorker.ready.then(function(sw) {
      return m.getToken({ vapidKey: FCM.vapidKey, serviceWorkerRegistration: sw });
    }).then(function(t) {
      if (!t) return null;
      if (sg(SK.TOKEN) !== t) {
        ss(SK.TOKEN, t);
        fetch(FCM.tokenEndpoint, {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ token:t, categories:Object.keys(CATS), ua:ua.slice(0,100), url:location.href, ts:Date.now() })
        }).catch(function(){});
      }
      return t;
    }).catch(function(e){ console.warn('[TSJPush]', e.message); return null; });
  }

  // ══════════════════════════════════════════════════════════════════
  // SUBSCRIBE
  // ══════════════════════════════════════════════════════════════════
  function subscribe() {
    if (!canPush) { if (isIOS) showIOSGuide(); return Promise.resolve(null); }
    return Notification.requestPermission().then(function(p) {
      if (p !== 'granted') { ss(SK.DIS, Date.now()); showBlockedBanner(); return null; }
      return regSW()
        .then(function() { return initFCM(); })
        .then(function(m)  { return getToken(m); })
        .then(function(t)  {
          ss(SK.SUB, !!t);
          if (t) { showSuccessToast(); startLocalRotation(); }
          return t;
        });
    });
  }

  function unsubscribe() {
    ss(SK.SUB, false); ss(SK.TOKEN, null);
    stopLocalRotation();
    return (_msg ? _msg.deleteToken().catch(function(){}) : Promise.resolve());
  }

  // ══════════════════════════════════════════════════════════════════
  // LOCAL JOB ROTATION — auto notification every 10 min
  // Rotates through real job pages from merged_sarkari_data.json
  // Works on: PC browser, Mobile browser, PWA installed app
  // ══════════════════════════════════════════════════════════════════
  var _rotateTimer = null;
  var ROTATE_MS    = 10 * 60 * 1000; // 10 minutes

  function startLocalRotation() {
    if (!sg(SK.SUB)) return;
    stopLocalRotation();
    // Ensure SW registration is ready, then load jobs and start timer
    var swPromise = _swReg
      ? Promise.resolve(_swReg)
      : navigator.serviceWorker.ready.then(function(r){ _swReg = r; return r; }).catch(function(){ return null; });

    swPromise.then(function() {
      return loadJobData();
    }).then(function() {
      // First notification after 30 seconds
      setTimeout(function() {
        if (sg(SK.SUB)) sendNextJobNotif();
      }, 30000);
      // Then every 10 minutes
      _rotateTimer = setInterval(function() {
        if (sg(SK.SUB)) sendNextJobNotif();
      }, ROTATE_MS);
    });
  }

  function stopLocalRotation() {
    if (_rotateTimer) { clearInterval(_rotateTimer); _rotateTimer = null; }
  }

  function loadJobData() {
    if (_jobCache && _jobCache.length) return Promise.resolve(_jobCache);

    // Use sections-index.json — small, always deployed, has slug+name for all categories
    return fetch('/sections-index.json', { cache: 'no-cache' })
      .then(function(r) { return r.json(); })
      .then(function(si) {
        var validCats = ['SR_Latest_Jobs','SR_Result','SR_Admit_Card','SR_Answer_Key'];
        var jobs = [];

        validCats.forEach(function(cat) {
          var items = si[cat] || [];
          items.forEach(function(item) {
            var slug  = item.slug || '';
            var title = item.name || item.title || '';
            if (slug && title) {
              jobs.push({ title: title, slug: slug, category: cat });
            }
          });
        });

        // Interleave: latest-job, result, admit-card, latest-job, result...
        var buckets = {};
        validCats.forEach(function(c) {
          buckets[c] = jobs.filter(function(j){ return j.category === c; });
        });
        var interleaved = [];
        var maxLen = Math.max.apply(null, validCats.map(function(c){ return (buckets[c]||[]).length; }).concat([0]));
        for (var i = 0; i < maxLen; i++) {
          validCats.forEach(function(cat) {
            if (buckets[cat] && buckets[cat][i]) interleaved.push(buckets[cat][i]);
          });
        }

        _jobCache = interleaved.length ? interleaved : jobs;
        var saved = sg(SK.IDX) || 0;
        _jobIdx   = (saved < _jobCache.length) ? saved : 0;
        console.log('[TSJPush] Loaded', _jobCache.length, 'jobs from sections-index');
        return _jobCache;
      })
      .catch(function() { _jobCache = []; return []; });
  }

  function sendNextJobNotif() {
    loadJobData().then(function(jobs) {
      if (!jobs.length) return;

      // Get current job — skip if no slug
      var job   = jobs[_jobIdx % jobs.length];
      var slug  = job.slug;
      if (!slug) { _jobIdx = (_jobIdx + 1) % jobs.length; return; }
      var title = (job.title || '').trim();
      var catKey= getCatKey(job.category);
      var cat   = CATS[catKey] || CATS['latest-jobs'];
      // Always use individual job detail page URL
      var url   = SITE + '/jobs/' + slug + '/';

      // Short title for notification
      var short = title.length > 62 ? title.slice(0,59)+'...' : title;
      var notifTitle = cat.emoji + ' ' + short;
      var notifBody  = getBody(catKey, title);

      // Advance index for next time
      _jobIdx = (_jobIdx + 1) % jobs.length;
      ss(SK.IDX, _jobIdx);

      // Show via SW registration.showNotification — works in background too
      var notifOptions = {
        body   : notifBody,
        icon   : '/icons/icon-192x192.png',
        badge  : '/icons/icon-96x96.png',
        tag    : 'tsj-job-' + catKey,
        renotify: true,
        vibrate: [150, 80, 150],
        data   : { url: url, category: catKey },
        actions: [
          { action: 'view', title: '🔔 अभी साइट विजिट करें मौका ना खोयें' }
        ]
      };
      // Use SW registration.showNotification (works when tab not focused)
      if (_swReg) {
        _swReg.showNotification(notifTitle, notifOptions).catch(function(){
          // Fallback: postMessage to SW
          if (navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
              type: 'SHOW_JOB_NOTIFICATION',
              payload: { title: notifTitle, body: notifBody, url: url, category: catKey }
            });
          }
        });
      } else if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({
          type: 'SHOW_JOB_NOTIFICATION',
          payload: { title: notifTitle, body: notifBody, url: url, category: catKey }
        });
      }
    });
  }

  function getCatKey(dataCategory) {
    var map = { 'SR_Latest_Jobs':'latest-jobs','SR_Result':'result','SR_Admit_Card':'admit-card','SR_Answer_Key':'answer-key','SR_Admission':'admission' };
    return map[dataCategory] || 'latest-jobs';
  }

  function getBody(catKey, title) {
    var t = title.slice(0, 80);
    if (catKey === 'result')     return t + ' — Result aa gaya! Abhi check karo.';
    if (catKey === 'admit-card') return t + ' — Admit Card jari! Download karo.';
    if (catKey === 'answer-key') return t + ' — Answer Key out!';
    if (catKey === 'admission')  return t + ' — Admission open!';
    return t + ' — Abhi apply karein! Last date miss mat karo.';
  }

  // ══════════════════════════════════════════════════════════════════
  // FOREGROUND TOAST (user is on site)
  // ══════════════════════════════════════════════════════════════════
  function showFgToast(payload) {
    var d   = payload.data || payload.notification || {};
    var url = d.url || (CATS[d.category]||{}).url || '/';
    var cat = CATS[d.category] || { emoji:'🔔', color:'#1a56db', label:'Update' };
    _toast(d.title||'🔔 Top Sarkari Jobs', d.body||'Nayi update!', cat, url, 7000);
  }

  function showSuccessToast() {
    _toast('Notifications ON! 🎉', 'Latest Jobs, Results, Admit Card ki instant alert milegi!',
           { emoji:'✅', color:'#16a34a', label:'' }, null, 5000);
  }

  function _toast(title, body, cat, url, dur) {
    injectCSS('tsj-tc', toastCSS());
    var old = document.getElementById('tsj-t');
    if (old) old.remove();
    var t = document.createElement('div');
    t.id  = 'tsj-t';
    t.setAttribute('role', 'alert');
    t.innerHTML =
      '<div class="ti" style="background:'+cat.color+'">'+cat.emoji+'</div>'+
      '<div class="tb"><div class="tt">'+esc(title)+'</div><div class="tx">'+esc(body)+'</div></div>'+
      '<button class="tc" aria-label="Close">✕</button>';
    if (url) t.addEventListener('click', function(e){ if(!e.target.classList.contains('tc')) location.href=url; });
    t.querySelector('.tc').addEventListener('click', function(e){ e.stopPropagation(); rmEl(t); });
    document.body.appendChild(t);
    raf2(function(){ t.classList.add('ts'); });
    setTimeout(function(){ rmEl(t); }, dur||6000);
  }

  // ══════════════════════════════════════════════════════════════════
  // PROMPT — Shows 3s on mobile, 6s on desktop. Always fresh check.
  // ══════════════════════════════════════════════════════════════════
  function canPrompt() {
    if (sg(SK.SUB)) return false;
    if (!canPush && !(isIOS)) return false;
    if (typeof Notification !== 'undefined' && Notification.permission === 'denied') return false;
    // Allow if never asked OR asked more than 1 day ago
    var asked = sg(SK.ASKED);
    if (asked && Date.now() - asked < 86400000) return false;
    // Allow if not dismissed OR dismissed more than 3 days ago
    var dis = sg(SK.DIS);
    if (dis && Date.now() - dis < 3 * 86400000) return false;
    return true;
  }

  function showPrompt() {
    if (!canPrompt()) {
      // Show unblock banner if blocked
      if (typeof Notification !== 'undefined' && Notification.permission === 'denied') {
        showBlockedBanner();
      }
      return;
    }
    ss(SK.ASKED, Date.now());
    injectCSS('tsj-pc', promptCSS());

    var el = document.createElement('div');
    el.id  = 'tsj-pp';
    el.setAttribute('role','dialog');
    el.setAttribute('aria-label','Instant Sarkari Job Alerts subscription prompt');
    el.innerHTML =
      '<button class="ppc" id="ppc">✕</button>'+
      '<div class="pph">'+
        '<div style="font-size:36px;margin-bottom:6px">🔔</div>'+
        '<div class="ppt">Instant Sarkari Job Alerts!</div>'+
        '<div class="pps">Latest Jobs · Results · Admit Card · Answer Key — seedha notification mein!</div>'+
      '</div>'+
      '<div class="ppcs">'+
        Object.entries(CATS).map(function(e){
          return '<span class="ppc2" style="border-color:'+e[1].color+';color:'+e[1].color+'">'+e[1].emoji+' '+e[1].label+'</span>';
        }).join('')+
      '</div>'+
      '<button class="ppa" id="ppa">🔔 Allow Notifications</button>'+
      '<button class="ppl" id="ppl">Abhi Nahi</button>';

    document.body.appendChild(el);
    raf2(function(){ el.classList.add('pps2'); });

    function close(dis) {
      if (dis) ss(SK.DIS, Date.now());
      el.classList.remove('pps2');
      setTimeout(function(){ rmEl(el); }, 400);
    }

    document.getElementById('ppc').addEventListener('click', function(){ close(true); });
    document.getElementById('ppl').addEventListener('click', function(){ close(false); });
    document.getElementById('ppa').addEventListener('click', function(){ close(false); subscribe(); });
  }

  // ── Persistent Bell Button (always visible, tap to subscribe) ─────
  function addBellButton() {
    if (sg(SK.SUB)) return; // Already subscribed
    if (document.getElementById('tsj-bell')) return;
    injectCSS('tsj-bc', bellCSS());
    var b = document.createElement('button');
    b.id  = 'tsj-bell';
    b.setAttribute('aria-label', 'Enable job notifications');
    b.title = 'Job Alerts Enable Karo';
    b.innerHTML = '🔔';
    b.addEventListener('click', function() {
      rmEl(b);
      if (canPrompt()) showPrompt();
      else subscribe();
    });
    document.body.appendChild(b);
  }

  // ── Blocked Banner ────────────────────────────────────────────────
  function showBlockedBanner() {
    if (document.getElementById('tsj-bl')) return;
    injectCSS('tsj-blc', blockedCSS());
    var el = document.createElement('div');
    el.id  = 'tsj-bl';
    var isChrome = /Chrome/i.test(ua) && !/Edg/i.test(ua);
    var step = isChrome
      ? 'Chrome: Address bar 🔒 → Permissions → Notifications → <b>Allow</b> → Reload'
      : 'Browser Settings → Notifications → topsarkarijobs.com → <b>Allow</b>';
    el.innerHTML =
      '<span style="font-size:22px">🔔</span>'+
      '<div class="blt"><div class="bln">Job Alerts Block Hain</div>'+
      '<div class="bls">'+step+'</div></div>'+
      '<button class="blc" id="blc">✕</button>';
    document.body.appendChild(el);
    raf2(function(){ el.classList.add('bls2'); });
    document.getElementById('blc').addEventListener('click', function(){ rmEl(el); });
    setTimeout(function(){ rmEl(el); }, 12000);
  }

  // ── iOS Guide ─────────────────────────────────────────────────────
  function showIOSGuide() {
    injectCSS('tsj-ic', iosCSS());
    var el = document.createElement('div');
    el.id  = 'tsj-ios';
    el.innerHTML =
      '<button style="position:absolute;top:10px;right:14px;background:#f1f5f9;border:none;border-radius:50%;width:30px;height:30px;cursor:pointer;font-size:14px" id="iosc">✕</button>'+
      '<div style="font-size:36px;text-align:center;margin-bottom:8px">📲</div>'+
      '<div style="font-size:.95rem;font-weight:800;color:#0f172a;text-align:center;margin-bottom:12px">iOS pe Notifications Enable Karo</div>'+
      '<div style="font-size:.78rem;color:#475569;line-height:1.7">'+
        '1️⃣ Safari neeche <b>Share ⬆️</b> tap karo<br>'+
        '2️⃣ <b>"Add to Home Screen"</b> select karo<br>'+
        '3️⃣ Home Screen se app open karo → Notifications milenge'+
      '</div>'+
      '<button style="display:block;width:100%;margin-top:16px;padding:12px;background:#1a56db;color:#fff;border:none;border-radius:10px;font-size:.88rem;font-weight:700;cursor:pointer" id="iook">Samajh Gaya!</button>';
    document.body.appendChild(el);
    raf2(function(){ el.classList.add('iosh'); });
    function closeIOS(){ el.classList.remove('iosh'); setTimeout(function(){ rmEl(el); },400); ss(SK.DIS,Date.now()); }
    document.getElementById('iosc').addEventListener('click', closeIOS);
    document.getElementById('iook').addEventListener('click', closeIOS);
  }

  // ══════════════════════════════════════════════════════════════════
  // CSS
  // ══════════════════════════════════════════════════════════════════
  function toastCSS() { return '#tsj-t{position:fixed;top:70px;right:10px;left:10px;z-index:2147483647;background:#fff;border-radius:14px;box-shadow:0 8px 32px rgba(0,0,0,.2);display:flex;align-items:center;gap:10px;padding:13px 11px;cursor:pointer;transform:translateY(-160%);opacity:0;transition:transform .35s cubic-bezier(.34,1.2,.64,1),opacity .3s;max-width:420px;margin:0 auto;-webkit-tap-highlight-color:transparent}@media(min-width:600px){#tsj-t{left:auto;width:350px}}#tsj-t.ts{transform:translateY(0);opacity:1}.ti{width:42px;height:42px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:21px;flex-shrink:0;color:#fff}.tb{flex:1;overflow:hidden;min-width:0}.tt{font-size:.83rem;font-weight:800;color:#0f172a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px}.tx{font-size:.74rem;color:#475569;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.tc{background:none;border:none;cursor:pointer;color:#475569;font-size:17px;padding:5px;min-width:30px;min-height:30px;display:flex;align-items:center;justify-content:center;border-radius:50%}.tc:hover{background:#f1f5f9}'; }

  function promptCSS() { return '#tsj-pp{position:fixed;bottom:calc(68px + env(safe-area-inset-bottom,0px));left:50%;width:calc(100% - 20px);max-width:380px;transform:translateX(-50%) translateY(130%);opacity:0;z-index:2147483645;background:#fff;border-radius:20px;box-shadow:0 -4px 40px rgba(0,0,0,.18),0 8px 40px rgba(0,0,0,.12);padding:20px 16px 16px;transition:transform .4s cubic-bezier(.34,1.2,.64,1),opacity .3s}#tsj-pp.pps2{transform:translateX(-50%) translateY(0);opacity:1}.ppc{position:absolute;top:10px;right:12px;background:none;border:none;cursor:pointer;color:#475569;font-size:17px;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:50%}.pph{text-align:center;margin-bottom:12px}.ppt{font-size:.95rem;font-weight:800;color:#0f172a;margin-bottom:5px;line-height:1.3}.pps{font-size:.74rem;color:#64748b;line-height:1.5}.ppcs{display:flex;flex-wrap:wrap;gap:5px;justify-content:center;margin-bottom:14px}.ppc2{font-size:.66rem;font-weight:700;padding:3px 9px;border-radius:20px;border:1.5px solid;background:#fff;white-space:nowrap}.ppa{display:block;width:100%;padding:13px;background:linear-gradient(135deg,#1a56db,#0d2257);color:#fff;border:none;border-radius:11px;font-size:.88rem;font-weight:700;cursor:pointer;margin-bottom:9px;min-height:48px;-webkit-tap-highlight-color:transparent}.ppa:active{opacity:.9}.ppl{display:block;width:100%;background:none;border:none;cursor:pointer;color:#475569;font-size:.78rem;padding:8px;min-height:40px}'; }

  function bellCSS() { return '#tsj-bell{position:fixed;bottom:calc(126px + env(safe-area-inset-bottom,0px));right:14px;z-index:149;width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#1a56db,#0d2257);color:#fff;font-size:22px;border:none;cursor:pointer;box-shadow:0 4px 16px rgba(26,86,219,.45);display:flex;align-items:center;justify-content:center;-webkit-tap-highlight-color:transparent;animation:bellring 3s ease-in-out infinite}@media(min-width:901px){#tsj-bell{bottom:76px}}@keyframes bellring{0%,90%,100%{transform:rotate(0)}93%{transform:rotate(-15deg)}96%{transform:rotate(15deg)}99%{transform:rotate(-8deg)}}'; }

  function blockedCSS() { return '#tsj-bl{position:fixed;bottom:calc(68px + env(safe-area-inset-bottom,0px));left:10px;right:10px;max-width:420px;margin:0 auto;z-index:2147483644;background:#1e3a5f;color:#fff;border-radius:14px;box-shadow:0 4px 24px rgba(0,0,0,.25);display:flex;align-items:center;gap:10px;padding:12px 13px;transform:translateY(140%);opacity:0;transition:transform .4s cubic-bezier(.34,1.2,.64,1),opacity .3s}@media(min-width:600px){#tsj-bl{left:50%;transform:translateX(-50%) translateY(140%);width:400px}}#tsj-bl.bls2{transform:translateY(0);opacity:1}@media(min-width:600px){#tsj-bl.bls2{transform:translateX(-50%) translateY(0)}}.blt{flex:1;min-width:0}.bln{font-size:.82rem;font-weight:800;margin-bottom:3px}.bls{font-size:.72rem;opacity:.85;line-height:1.4}.bls b{color:#fbbf24}.blc{background:rgba(255,255,255,.15);border:none;color:#fff;border-radius:50%;min-width:28px;min-height:28px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}'; }

  function iosCSS() { return '#tsj-ios{position:fixed;bottom:0;left:0;right:0;z-index:2147483647;background:#fff;border-radius:20px 20px 0 0;box-shadow:0 -4px 40px rgba(0,0,0,.2);padding:24px 20px calc(20px + env(safe-area-inset-bottom,0px));transform:translateY(100%);opacity:0;transition:transform .4s cubic-bezier(.34,1.2,.64,1),opacity .3s}#tsj-ios.iosh{transform:translateY(0);opacity:1}'; }

  // ══════════════════════════════════════════════════════════════════
  // HELPERS
  // ══════════════════════════════════════════════════════════════════
  function injectCSS(id, css) { if (!document.getElementById(id)) { var s=document.createElement('style'); s.id=id; s.textContent=css; document.head.appendChild(s); } }
  function rmEl(el)  { if (el && el.parentNode) { el.classList.remove('ts','pps2','bls2','iosh'); setTimeout(function(){ if(el.parentNode) el.remove(); }, 400); } }
  function raf2(fn)  { requestAnimationFrame(function(){ requestAnimationFrame(fn); }); }
  function esc(s)    { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  // ══════════════════════════════════════════════════════════════════
  // PUBLIC API
  // ══════════════════════════════════════════════════════════════════
  window.TSJPush = {
    subscribe:    subscribe,
    unsubscribe:  unsubscribe,
    isSubscribed: function() { return !!sg(SK.SUB); },
    showPrompt:   showPrompt,
    getToken:     function() { return sg(SK.TOKEN); },

    // Test: sends notification for latest real job page
    testNotification: function(category) {
      var catKey = category || 'latest-jobs';
      var cat    = CATS[catKey] || CATS['latest-jobs'];
      // Load from sections-index.json → pick real job → show detail page URL
      loadJobData().then(function(jobs) {
        var catJobs = jobs.filter(function(j){ return j.category === (cat.dataKey || 'SR_Latest_Jobs'); });
        if (!catJobs.length) catJobs = jobs; // fallback: any job
        var job  = catJobs[Math.floor(Math.random() * Math.min(catJobs.length, catJobs.length))];
        var url  = job ? (SITE + '/jobs/' + job.slug + '/') : cat.url;
        var titl = job ? (job.title || '').slice(0, 62) : cat.label + ' Alert';
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({
            type: 'SHOW_JOB_NOTIFICATION',
            payload: { title: cat.emoji + ' ' + titl, body: getBody(catKey, titl), url: url, category: catKey }
          });
        }
      }).catch(function() {
        if (navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({
            type: 'SHOW_JOB_NOTIFICATION',
            payload: { title: cat.emoji + ' Test: ' + cat.label, body: 'Push working!', url: cat.url, category: catKey }
          });
        }
      });
    },

    init: function() {
      if (!sg(SK.SUB)) return;
      // Get SW registration first, then init FCM + start rotation
      regSW().then(function(r) {
        _swReg = r;
        return initFCM();
      }).catch(function(){});
      startLocalRotation();
    },
  };

  // ══════════════════════════════════════════════════════════════════
  // AUTO INIT
  // ══════════════════════════════════════════════════════════════════
  function boot() {
    // If already subscribed — init FCM + start rotation
    if (sg(SK.SUB)) {
      setTimeout(function() { window.TSJPush.init(); }, 1000);
    }

    // Show bell button after 2 seconds (always visible if not subscribed)
    setTimeout(addBellButton, 2000);

    // Show prompt:
    // Mobile: 4 seconds | Desktop: 8 seconds
    var delay = isMobile ? 4000 : 8000;
    setTimeout(function() {
      if (!sg(SK.SUB)) showPrompt();
    }, delay);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function(){ setTimeout(boot, 300); });
  } else {
    setTimeout(boot, 300);
  }

})();
