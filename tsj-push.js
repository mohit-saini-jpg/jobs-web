/**
 * ╔══════════════════════════════════════════════════════════════════════╗
 * ║  TOP SARKARI JOBS — FCM Push Notification System v2.0               ║
 * ║  Firebase Cloud Messaging V1 API + Web Push                        ║
 * ║  Project: job-portal-750e0                                         ║
 * ║  Sender ID: 230495552068                                           ║
 * ╚══════════════════════════════════════════════════════════════════════╝
 */
(function () {
  'use strict';

  // ══════════════════════════════════════════════════════════════════
  // FIREBASE CONFIG — job-portal-750e0
  // ══════════════════════════════════════════════════════════════════
  var FCM_CONFIG = {
    apiKey:            "AIzaSyBb4R2TlJgowhHAsROO9Lue5ztI_BtF1xY",
    authDomain:        "job-portal-750e0.firebaseapp.com",
    projectId:         "job-portal-750e0",
    storageBucket:     "job-portal-750e0.firebasestorage.app",
    messagingSenderId: "230495552068",
    appId:             "1:230495552068:web:9b3980e4bf831b7366f211",
    measurementId:     "G-GBET4E4DF3",
    // VAPID Public Key — Web Push Certificate (job-portal-750e0)
    vapidKey: "BHHqgCttMPzjG0B-KnYUgVu3nrleMV8FUHYQyIQpqC2xtPozCW_s2ZURExUHsvBE05jk4SzxeFEymTwbUqNua58",
    // Token save endpoint — update if using different backend
    tokenEndpoint: "https://cykkclkfimmqbahanidg.supabase.co/functions/v1/save-push-token",
  };

  // ══════════════════════════════════════════════════════════════════
  // CATEGORY CONFIG
  // ══════════════════════════════════════════════════════════════════
  var CATEGORIES = {
    'latest-jobs': { label:'Latest Jobs',  url:'https://www.topsarkarijobs.com/section/latest-jobs/', emoji:'💼', color:'#1a56db' },
    'result':      { label:'Results',      url:'https://www.topsarkarijobs.com/section/results/',     emoji:'🏆', color:'#16a34a' },
    'admit-card':  { label:'Admit Card',   url:'https://www.topsarkarijobs.com/section/admit-card/',  emoji:'🎫', color:'#d97706' },
    'admission':   { label:'Admission',    url:'https://www.topsarkarijobs.com/section/admission/',   emoji:'🎓', color:'#7c3aed' },
    'answer-key':  { label:'Answer Key',   url:'https://www.topsarkarijobs.com/section/answer-key/',  emoji:'🔑', color:'#be185d' },
  };

  // ══════════════════════════════════════════════════════════════════
  // STORAGE
  // ══════════════════════════════════════════════════════════════════
  var SK = { TOKEN:'tsj_fcm_token', SUBSCRIBED:'tsj_push_subscribed', ASKED:'tsj_push_asked_at', DISMISSED:'tsj_push_dismissed_at' };
  function sg(k)   { try { return JSON.parse(localStorage.getItem(k)); } catch(e) { return null; } }
  function ss(k,v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch(e) {} }

  // ══════════════════════════════════════════════════════════════════
  // FIREBASE SDK — Load lazily from CDN
  // ══════════════════════════════════════════════════════════════════
  var _messaging = null, _initialized = false;

  function loadFirebase() {
    return new Promise(function(resolve, reject) {
      if (window.firebase && window.firebase.messaging) return resolve(window.firebase);
      var srcs = [
        'https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js',
        'https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js',
      ];
      var loaded = 0;
      srcs.forEach(function(src) {
        var s = document.createElement('script');
        s.src = src; s.async = false;
        s.onload  = function() { if (++loaded === srcs.length) resolve(window.firebase); };
        s.onerror = function() { reject(new Error('Firebase load failed')); };
        document.head.appendChild(s);
      });
    });
  }

  function initFCM() {
    if (_initialized) return Promise.resolve(_messaging);
    return loadFirebase().then(function(fb) {
      if (!fb.apps.length) fb.initializeApp(FCM_CONFIG);
      _messaging   = fb.messaging();
      _initialized = true;
      // Foreground messages → show in-page toast
      _messaging.onMessage(function(payload) { showToast(payload); });
      return _messaging;
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // SERVICE WORKER REGISTRATION
  // ══════════════════════════════════════════════════════════════════
  function registerSW() {
    if (!('serviceWorker' in navigator)) return Promise.reject('SW not supported');
    return navigator.serviceWorker.register('/sw.js', { scope: '/' })
      .then(function(reg) { reg.update(); return reg; });
  }

  // ══════════════════════════════════════════════════════════════════
  // GET FCM TOKEN + SAVE
  // ══════════════════════════════════════════════════════════════════
  function getToken(messaging) {
    return navigator.serviceWorker.ready.then(function(swReg) {
      return messaging.getToken({
        vapidKey: FCM_CONFIG.vapidKey,
        serviceWorkerRegistration: swReg,
      });
    }).then(function(token) {
      if (!token) return null;
      var stored = sg(SK.TOKEN);
      if (stored !== token) {
        ss(SK.TOKEN, token);
        ss(SK.SUBSCRIBED, true);
        // Save to backend (best effort)
        fetch(FCM_CONFIG.tokenEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            token: token,
            categories: Object.keys(CATEGORIES),
            ua:  navigator.userAgent.slice(0, 100),
            url: location.href, ts: Date.now(),
          }),
        }).catch(function() {});
      }
      return token;
    }).catch(function(err) {
      console.warn('[TSJPush] getToken:', err.message);
      return null;
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // SUBSCRIBE
  // ══════════════════════════════════════════════════════════════════
  function subscribe() {
    if (!('Notification' in window)) return Promise.reject('Not supported');
    return Notification.requestPermission().then(function(perm) {
      if (perm !== 'granted') { ss(SK.DISMISSED, Date.now()); return null; }
      return registerSW()
        .then(function() { return initFCM(); })
        .then(function(msg) { return getToken(msg); })
        .then(function(token) {
          ss(SK.SUBSCRIBED, !!token);
          if (token) showSuccessToast();
          return token;
        });
    });
  }

  function unsubscribe() {
    ss(SK.SUBSCRIBED, false); ss(SK.TOKEN, null);
    if (!_messaging) return Promise.resolve();
    return _messaging.deleteToken().catch(function() {});
  }

  // ══════════════════════════════════════════════════════════════════
  // FOREGROUND TOAST
  // ══════════════════════════════════════════════════════════════════
  function showToast(payload) {
    var d = payload.data || payload.notification || {};
    var title    = d.title    || '🔔 Top Sarkari Jobs';
    var body     = d.body     || 'Nayi update aa gayi!';
    var url      = d.url      || (CATEGORIES[d.category] || {}).url || '/';
    var cat      = CATEGORIES[d.category] || { emoji:'🔔', color:'#1a56db', label:'Update' };
    injectToastCSS();
    var t = document.createElement('div');
    t.id = 'tsj-fg-toast';
    t.setAttribute('role','alert');
    t.innerHTML =
      '<div class="tt-icon" style="background:' + cat.color + '">' + cat.emoji + '</div>' +
      '<div class="tt-body">' +
        '<div class="tt-title">' + esc(title) + '</div>' +
        '<div class="tt-text">'  + esc(body)  + '</div>' +
        '<div class="tt-cat">'   + esc(cat.label) + '</div>' +
      '</div>' +
      '<button class="tt-x" aria-label="Close">✕</button>';
    t.addEventListener('click', function(e) {
      if (!e.target.classList.contains('tt-x')) location.href = url;
    });
    t.querySelector('.tt-x').addEventListener('click', function(e) {
      e.stopPropagation(); rmToast(t);
    });
    var old = document.getElementById('tsj-fg-toast');
    if (old) old.remove();
    document.body.appendChild(t);
    requestAnimationFrame(function() {
      requestAnimationFrame(function() { t.classList.add('tt-show'); });
    });
    setTimeout(function() { rmToast(t); }, 7000);
  }

  function showSuccessToast() {
    injectToastCSS();
    var t = document.createElement('div');
    t.id = 'tsj-fg-toast';
    t.innerHTML =
      '<div class="tt-icon" style="background:#16a34a">✅</div>' +
      '<div class="tt-body"><div class="tt-title">Notifications ON! 🎉</div>' +
      '<div class="tt-text">Ab aapko Latest Jobs, Results, Admit Card ki instant alert milegi.</div></div>' +
      '<button class="tt-x" aria-label="Close">✕</button>';
    t.querySelector('.tt-x').addEventListener('click', function() { rmToast(t); });
    var old = document.getElementById('tsj-fg-toast');
    if (old) old.remove();
    document.body.appendChild(t);
    requestAnimationFrame(function() {
      requestAnimationFrame(function() { t.classList.add('tt-show'); });
    });
    setTimeout(function() { rmToast(t); }, 6000);
  }

  function rmToast(el) {
    if (!el) return;
    el.classList.remove('tt-show');
    setTimeout(function() { if (el.parentNode) el.remove(); }, 400);
  }

  function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function injectToastCSS() {
    if (document.getElementById('tsj-toast-css')) return;
    var s = document.createElement('style');
    s.id = 'tsj-toast-css';
    s.textContent =
      '#tsj-fg-toast{position:fixed;top:16px;right:16px;z-index:2147483647;background:#fff;border-radius:14px;' +
      'box-shadow:0 8px 32px rgba(0,0,0,.18);display:flex;align-items:center;gap:12px;' +
      'padding:14px 16px;max-width:340px;width:calc(100vw - 32px);cursor:pointer;' +
      'transform:translateY(-140%);opacity:0;' +
      'transition:transform .35s cubic-bezier(.34,1.2,.64,1),opacity .3s;' +
      '-webkit-tap-highlight-color:transparent;}' +
      '#tsj-fg-toast.tt-show{transform:translateY(0);opacity:1}' +
      '.tt-icon{width:42px;height:42px;border-radius:12px;display:flex;align-items:center;' +
      'justify-content:center;font-size:20px;flex-shrink:0;color:#fff;}' +
      '.tt-body{flex:1;overflow:hidden}' +
      '.tt-title{font-size:.82rem;font-weight:800;color:#0f172a;white-space:nowrap;' +
      'overflow:hidden;text-overflow:ellipsis;margin-bottom:2px;}' +
      '.tt-text{font-size:.74rem;color:#475569;line-height:1.4;' +
      'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}' +
      '.tt-cat{font-size:.65rem;font-weight:700;color:#94a3b8;text-transform:uppercase;' +
      'letter-spacing:.04em;margin-top:3px;}' +
      '.tt-x{background:none;border:none;cursor:pointer;color:#94a3b8;font-size:14px;' +
      'padding:4px;flex-shrink:0;line-height:1;border-radius:50%;' +
      'width:24px;height:24px;display:flex;align-items:center;justify-content:center;}' +
      '.tt-x:hover{background:#f1f5f9;color:#475569}' +
      '@media(max-width:480px){#tsj-fg-toast{top:8px;right:8px;left:8px;width:auto;max-width:none}}';
    document.head.appendChild(s);
  }

  // ══════════════════════════════════════════════════════════════════
  // SOFT PROMPT UI
  // ══════════════════════════════════════════════════════════════════
  function canPrompt() {
    if (sg(SK.SUBSCRIBED)) return false;
    if (!('Notification' in window) || !('serviceWorker' in navigator)) return false;
    if (Notification.permission === 'denied') return false;
    var dis = sg(SK.DISMISSED); if (dis && Date.now() - dis < 3 * 86400000) return false;
    var ask = sg(SK.ASKED);     if (ask && Date.now() - ask < 86400000) return false;
    return true;
  }

  function showPrompt() {
    if (!canPrompt()) return;
    ss(SK.ASKED, Date.now());
    injectPromptCSS();
    var el = document.createElement('div');
    el.id = 'tsj-push-prompt';
    el.setAttribute('role','dialog');
    el.setAttribute('aria-label','Enable job alerts');
    el.innerHTML =
      '<button class="pp-close" id="ppClose" aria-label="Close">✕</button>' +
      '<div class="pp-icon">🔔</div>' +
      '<div class="pp-title">Instant Sarkari Job Alerts!</div>' +
      '<div class="pp-sub">Latest Jobs · Results · Admit Card · Answer Key — seedha notification mein paayein!</div>' +
      '<div class="pp-cats">' +
        Object.entries(CATEGORIES).map(function(e) {
          return '<span class="pp-cat" style="border-color:' + e[1].color + ';color:' + e[1].color + '">' +
            e[1].emoji + ' ' + e[1].label + '</span>';
        }).join('') +
      '</div>' +
      '<button class="pp-allow" id="ppAllow">🔔 Allow Notifications</button>' +
      '<button class="pp-later" id="ppLater">Baad Mein</button>';
    document.body.appendChild(el);
    requestAnimationFrame(function() {
      requestAnimationFrame(function() { el.classList.add('pp-show'); });
    });
    function close() {
      el.classList.remove('pp-show');
      setTimeout(function() { if (el.parentNode) el.remove(); }, 400);
    }
    document.getElementById('ppClose').onclick = function() { ss(SK.DISMISSED, Date.now()); close(); };
    document.getElementById('ppLater').onclick = close;
    document.getElementById('ppAllow').onclick = function() { close(); subscribe(); };
  }

  function injectPromptCSS() {
    if (document.getElementById('tsj-pp-css')) return;
    var s = document.createElement('style');
    s.id = 'tsj-pp-css';
    s.textContent =
      '#tsj-push-prompt{position:fixed;bottom:80px;left:50%;' +
      'transform:translateX(-50%) translateY(140px);z-index:2147483646;' +
      'background:#fff;border-radius:20px;box-shadow:0 16px 48px rgba(0,0,0,.22);' +
      'padding:24px 20px 20px;max-width:320px;width:calc(100vw - 32px);' +
      'text-align:center;opacity:0;' +
      'transition:transform .4s cubic-bezier(.34,1.2,.64,1),opacity .3s;}' +
      '#tsj-push-prompt.pp-show{transform:translateX(-50%) translateY(0);opacity:1}' +
      '.pp-close{position:absolute;top:10px;right:12px;background:none;border:none;' +
      'cursor:pointer;color:#94a3b8;font-size:16px;width:28px;height:28px;' +
      'display:flex;align-items:center;justify-content:center;border-radius:50%;}' +
      '.pp-close:hover{background:#f1f5f9}' +
      '.pp-icon{font-size:40px;margin-bottom:8px}' +
      '.pp-title{font-size:.95rem;font-weight:800;color:#0f172a;margin-bottom:6px}' +
      '.pp-sub{font-size:.75rem;color:#64748b;line-height:1.5;margin-bottom:14px}' +
      '.pp-cats{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin-bottom:16px}' +
      '.pp-cat{font-size:.66rem;font-weight:700;padding:3px 9px;border-radius:20px;' +
      'border:1.5px solid;background:#fff;}' +
      '.pp-allow{display:block;width:100%;padding:12px;' +
      'background:linear-gradient(135deg,#1a56db,#0d2257);color:#fff;' +
      'border:none;border-radius:10px;font-size:.85rem;font-weight:700;' +
      'cursor:pointer;margin-bottom:8px;transition:opacity .2s;}' +
      '.pp-allow:hover{opacity:.9}' +
      '.pp-later{background:none;border:none;cursor:pointer;color:#94a3b8;font-size:.75rem;}';
    document.head.appendChild(s);
  }

  // ══════════════════════════════════════════════════════════════════
  // PUBLIC API
  // ══════════════════════════════════════════════════════════════════
  window.TSJPush = {
    subscribe:    subscribe,
    unsubscribe:  unsubscribe,
    isSubscribed: function() { return !!sg(SK.SUBSCRIBED); },
    showPrompt:   showPrompt,
    getToken:     function() { return sg(SK.TOKEN); },

    // Test notification via SW message
    testNotification: function(category) {
      var cat = CATEGORIES[category || 'latest-jobs'] || CATEGORIES['latest-jobs'];
      if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({
          type: 'SHOW_TEST_NOTIFICATION',
          payload: {
            title: cat.emoji + ' Test: ' + cat.label,
            body:  'Push notification working on topsarkarijobs.com!',
            url:   cat.url, category: category || 'latest-jobs',
          }
        });
      }
    },

    // Init FCM for already-subscribed users (receive foreground messages)
    init: function() {
      if (!sg(SK.SUBSCRIBED)) return;
      registerSW().then(function() { return initFCM(); }).catch(function() {});
    },
  };

  // ══════════════════════════════════════════════════════════════════
  // AUTO INIT
  // ══════════════════════════════════════════════════════════════════
  function autoInit() {
    if (sg(SK.SUBSCRIBED)) {
      var idle = 'requestIdleCallback' in window;
      if (idle) requestIdleCallback(function() { window.TSJPush.init(); }, { timeout: 5000 });
      else setTimeout(function() { window.TSJPush.init(); }, 3000);
    }
    // Show prompt after 30 sec
    setTimeout(function() { if (canPrompt()) showPrompt(); }, 30000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    if ('requestIdleCallback' in window) requestIdleCallback(autoInit, { timeout: 8000 });
    else setTimeout(autoInit, 2000);
  }

})();
