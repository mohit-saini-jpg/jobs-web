/**
 * ╔══════════════════════════════════════════════════════════════════════╗
 * ║  TOP SARKARI JOBS — FCM Push Notification System v3.0               ║
 * ║  Firebase Cloud Messaging V1 | Project: job-portal-750e0           ║
 * ║  FIXED: Mobile prompt · Android Chrome · SW conflict · Timing      ║
 * ╚══════════════════════════════════════════════════════════════════════╝
 */
(function () {
  'use strict';

  // ── Config ────────────────────────────────────────────────────────
  var FCM_CONFIG = {
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

  var CATEGORIES = {
    'latest-jobs': { label:'Latest Jobs',  url:'https://www.topsarkarijobs.com/section/latest-jobs/', emoji:'💼', color:'#1a56db' },
    'result':      { label:'Results',      url:'https://www.topsarkarijobs.com/section/results/',     emoji:'🏆', color:'#16a34a' },
    'admit-card':  { label:'Admit Card',   url:'https://www.topsarkarijobs.com/section/admit-card/',  emoji:'🎫', color:'#d97706' },
    'admission':   { label:'Admission',    url:'https://www.topsarkarijobs.com/section/admission/',   emoji:'🎓', color:'#7c3aed' },
    'answer-key':  { label:'Answer Key',   url:'https://www.topsarkarijobs.com/section/answer-key/',  emoji:'🔑', color:'#be185d' },
  };

  var SK = {
    TOKEN:      'tsj_fcm_token_v3',
    SUBSCRIBED: 'tsj_push_sub_v3',
    ASKED:      'tsj_push_asked_v3',
    DISMISSED:  'tsj_push_dis_v3',
  };

  // ── Storage ───────────────────────────────────────────────────────
  function sg(k)   { try { return JSON.parse(localStorage.getItem(k)); } catch(e) { return null; } }
  function ss(k,v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch(e) {} }

  // ── Device detection ──────────────────────────────────────────────
  var ua         = navigator.userAgent || '';
  var isIOS      = /iPad|iPhone|iPod/i.test(ua) && !window.MSStream;
  var isAndroid  = /Android/i.test(ua);
  var isMobile   = isIOS || isAndroid || /Mobile/i.test(ua);
  var isSafari   = /^((?!chrome|android).)*safari/i.test(ua);
  // iOS Safari does NOT support Web Push (except iOS 16.4+ PWA mode)
  var canPush    = 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window;

  // ── State ─────────────────────────────────────────────────────────
  var _messaging = null, _initialized = false, _swReg = null;

  // ══════════════════════════════════════════════════════════════════
  // SERVICE WORKER — register once, reuse
  // ══════════════════════════════════════════════════════════════════
  function registerSW() {
    if (_swReg) return Promise.resolve(_swReg);
    if (!('serviceWorker' in navigator)) return Promise.reject('SW not supported');
    // Use exact path, no version query string (pwa-install.js also registers same)
    return navigator.serviceWorker.register('/sw.js', { scope: '/' })
      .then(function(reg) {
        _swReg = reg;
        reg.update();
        return reg;
      });
  }

  // ══════════════════════════════════════════════════════════════════
  // FIREBASE SDK — lazy load
  // ══════════════════════════════════════════════════════════════════
  function loadFirebase() {
    return new Promise(function(resolve, reject) {
      if (window.firebase && window.firebase.messaging) return resolve(window.firebase);
      // Load both scripts sequentially
      var s1 = document.createElement('script');
      s1.src = 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js';
      s1.onload = function() {
        var s2 = document.createElement('script');
        s2.src = 'https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js';
        s2.onload  = function() { resolve(window.firebase); };
        s2.onerror = function() { reject(new Error('FCM SDK load failed')); };
        document.head.appendChild(s2);
      };
      s1.onerror = function() { reject(new Error('Firebase SDK load failed')); };
      document.head.appendChild(s1);
    });
  }

  function initFCM() {
    if (_initialized) return Promise.resolve(_messaging);
    return loadFirebase().then(function(fb) {
      if (!fb.apps.length) fb.initializeApp(FCM_CONFIG);
      _messaging   = fb.messaging();
      _initialized = true;
      _messaging.onMessage(function(payload) { showForegroundToast(payload); });
      return _messaging;
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // GET FCM TOKEN
  // ══════════════════════════════════════════════════════════════════
  function getFCMToken(messaging) {
    return navigator.serviceWorker.ready.then(function(swReg) {
      return messaging.getToken({
        vapidKey: FCM_CONFIG.vapidKey,
        serviceWorkerRegistration: swReg,
      });
    }).then(function(token) {
      if (!token) { console.warn('[TSJPush] No token — check VAPID key'); return null; }
      var stored = sg(SK.TOKEN);
      if (stored !== token) {
        ss(SK.TOKEN, token);
        // Save token to backend (best effort)
        fetch(FCM_CONFIG.tokenEndpoint, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            token:      token,
            categories: Object.keys(CATEGORIES),
            ua:         ua.slice(0, 120),
            url:        location.href,
            ts:         Date.now(),
          }),
        }).catch(function() {});
      }
      return token;
    }).catch(function(err) {
      console.warn('[TSJPush] getToken error:', err.message);
      return null;
    });
  }

  // ══════════════════════════════════════════════════════════════════
  // SUBSCRIBE — request permission + get token
  // ══════════════════════════════════════════════════════════════════
  function subscribe() {
    if (!canPush) {
      // iOS Safari — show instructions
      if (isIOS && isSafari) { showIOSInstructions(); return Promise.resolve(null); }
      return Promise.reject('Push not supported');
    }

    return Notification.requestPermission().then(function(perm) {
      if (perm !== 'granted') {
        ss(SK.DISMISSED, Date.now());
        showDeniedHelp();
        return null;
      }
      return registerSW()
        .then(function() { return initFCM(); })
        .then(function(msg)   { return getFCMToken(msg); })
        .then(function(token) {
          ss(SK.SUBSCRIBED, !!token);
          if (token) showSuccessToast();
          return token;
        });
    });
  }

  function unsubscribe() {
    ss(SK.SUBSCRIBED, false);
    ss(SK.TOKEN, null);
    if (!_messaging) return Promise.resolve();
    return _messaging.deleteToken().catch(function() {});
  }

  // ══════════════════════════════════════════════════════════════════
  // PROMPT UI — Fixed for mobile
  // FIXES: bottom position above bottom nav, larger touch targets,
  //        shows sooner (5s not 30s on mobile), z-index above all
  // ══════════════════════════════════════════════════════════════════
  function canShowPrompt() {
    if (sg(SK.SUBSCRIBED)) return false;
    if (!canPush && !(isIOS && isSafari)) return false;
    // If denied — show unblock instructions banner instead
    if (Notification.permission === 'denied') {
      var lastUnblock = sg('tsj_unblock_shown');
      if (!lastUnblock || Date.now() - lastUnblock > 7 * 86400000) {
        setTimeout(function() { showUnblockBanner(); }, 5000);
      }
      return false;
    }
    var dis = sg(SK.DISMISSED);
    if (dis && Date.now() - dis < 3 * 86400000) return false;
    var ask = sg(SK.ASKED);
    if (ask && Date.now() - ask < 86400000) return false;
    return true;
  }

  function showPrompt() {
    if (!canShowPrompt()) return;
    ss(SK.ASKED, Date.now());

    injectCSS('tsj-pp-css', getPromptCSS());

    var el = document.createElement('div');
    el.id  = 'tsj-push-prompt';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    el.setAttribute('aria-label', 'Enable job alerts');

    el.innerHTML =
      '<button class="pp-close" id="tsjPpClose" aria-label="Close">✕</button>' +
      '<div class="pp-head">' +
        '<div class="pp-bell">🔔</div>' +
        '<div class="pp-title">Instant Sarkari Job Alerts!</div>' +
        '<div class="pp-sub">Latest Jobs · Results · Admit Card · Answer Key — seedha mobile notification mein!</div>' +
      '</div>' +
      '<div class="pp-cats">' +
        Object.entries(CATEGORIES).map(function(e) {
          return '<span class="pp-cat" style="border-color:' + e[1].color + ';color:' + e[1].color + '">' +
            e[1].emoji + ' ' + e[1].label + '</span>';
        }).join('') +
      '</div>' +
      '<button class="pp-allow" id="tsjPpAllow">🔔 Allow Notifications</button>' +
      '<button class="pp-later" id="tsjPpLater">Abhi Nahi</button>';

    document.body.appendChild(el);

    // Animate in
    requestAnimationFrame(function() {
      requestAnimationFrame(function() { el.classList.add('pp-show'); });
    });

    function closePrompt(dismissed) {
      if (dismissed) ss(SK.DISMISSED, Date.now());
      el.classList.remove('pp-show');
      setTimeout(function() { if (el.parentNode) el.remove(); }, 400);
    }

    document.getElementById('tsjPpClose').addEventListener('click', function() { closePrompt(true); });
    document.getElementById('tsjPpLater').addEventListener('click', function() { closePrompt(false); });
    document.getElementById('tsjPpAllow').addEventListener('click', function() {
      closePrompt(false);
      subscribe();
    });

    // Touch outside to close
    el.addEventListener('click', function(e) {
      if (e.target === el) closePrompt(false);
    });
  }

  // iOS Safari — show "Add to Home Screen" instructions
  function showIOSInstructions() {
    injectCSS('tsj-ios-css', getIOSCSS());
    var el = document.createElement('div');
    el.id  = 'tsj-ios-prompt';
    el.innerHTML =
      '<button class="ios-close" id="tsjIosClose">✕</button>' +
      '<div class="ios-icon">📲</div>' +
      '<div class="ios-title">iOS pe Notifications Kaise Enable Karein</div>' +
      '<div class="ios-steps">' +
        '<div class="ios-step"><span class="ios-num">1</span>Safari mein neeche <strong>Share button</strong> tap karein <span class="ios-icon2">⬆️</span></div>' +
        '<div class="ios-step"><span class="ios-num">2</span><strong>"Add to Home Screen"</strong> select karein</div>' +
        '<div class="ios-step"><span class="ios-num">3</span>Home Screen se app open karein → notifications milenge</div>' +
      '</div>' +
      '<button class="ios-ok" id="tsjIosOk">Samajh Gaya!</button>';
    document.body.appendChild(el);
    requestAnimationFrame(function() {
      requestAnimationFrame(function() { el.classList.add('ios-show'); });
    });
    function closeIOS() {
      el.classList.remove('ios-show');
      setTimeout(function() { if (el.parentNode) el.remove(); }, 400);
      ss(SK.DISMISSED, Date.now());
    }
    document.getElementById('tsjIosClose').addEventListener('click', closeIOS);
    document.getElementById('tsjIosOk').addEventListener('click', closeIOS);
  }

  // Show help when permission is denied
  function showDeniedHelp() {
    injectCSS('tsj-toast-css', getToastCSS());
    var t = document.createElement('div');
    t.id  = 'tsj-fg-toast';
    t.innerHTML =
      '<div class="tt-icon" style="background:#dc2626">⚠️</div>' +
      '<div class="tt-body">' +
        '<div class="tt-title">Notification Block Hai</div>' +
        '<div class="tt-text">Browser Settings → Notifications → topsarkarijobs.com → Allow karein</div>' +
      '</div>' +
      '<button class="tt-x" aria-label="Close">✕</button>';
    t.querySelector('.tt-x').addEventListener('click', function() { rmToast(t); });
    appendToast(t);
    setTimeout(function() { rmToast(t); }, 8000);
  }

  // ══════════════════════════════════════════════════════════════════
  // FOREGROUND TOAST — shows when user is on site
  // ══════════════════════════════════════════════════════════════════
  function showForegroundToast(payload) {
    var d    = payload.data || payload.notification || {};
    var title = d.title || '🔔 Top Sarkari Jobs';
    var body  = d.body  || 'Nayi update aa gayi!';
    var url   = d.url   || (CATEGORIES[d.category] || {}).url || '/';
    var cat   = CATEGORIES[d.category] || { emoji:'🔔', color:'#1a56db', label:'Update' };

    injectCSS('tsj-toast-css', getToastCSS());
    var t = document.createElement('div');
    t.id  = 'tsj-fg-toast';
    t.setAttribute('role', 'alert');
    t.setAttribute('aria-live', 'polite');
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
    appendToast(t);
    setTimeout(function() { rmToast(t); }, 7000);
  }

  function showSuccessToast() {
    injectCSS('tsj-toast-css', getToastCSS());
    var t = document.createElement('div');
    t.id  = 'tsj-fg-toast';
    t.setAttribute('role', 'status');
    t.innerHTML =
      '<div class="tt-icon" style="background:#16a34a">✅</div>' +
      '<div class="tt-body">' +
        '<div class="tt-title">Notifications ON! 🎉</div>' +
        '<div class="tt-text">Latest Jobs, Results, Admit Card ki instant alert milegi!</div>' +
      '</div>' +
      '<button class="tt-x" aria-label="Close">✕</button>';
    t.querySelector('.tt-x').addEventListener('click', function() { rmToast(t); });
    appendToast(t);
    setTimeout(function() { rmToast(t); }, 6000);
  }

  function appendToast(t) {
    var old = document.getElementById('tsj-fg-toast');
    if (old) old.remove();
    document.body.appendChild(t);
    requestAnimationFrame(function() {
      requestAnimationFrame(function() { t.classList.add('tt-show'); });
    });
  }

  function rmToast(el) {
    if (!el || !el.parentNode) return;
    el.classList.remove('tt-show');
    setTimeout(function() { if (el.parentNode) el.remove(); }, 400);
  }

  function esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ══════════════════════════════════════════════════════════════════
  // CSS INJECTION
  // ══════════════════════════════════════════════════════════════════
  function injectCSS(id, css) {
    if (document.getElementById(id)) return;
    var s = document.createElement('style');
    s.id  = id;
    s.textContent = css;
    document.head.appendChild(s);
  }

  function getToastCSS() {
    return [
      '#tsj-fg-toast{',
        'position:fixed;top:72px;right:12px;left:12px;',  /* Mobile: full width near top */
        'z-index:2147483647;background:#fff;border-radius:14px;',
        'box-shadow:0 8px 32px rgba(0,0,0,.22);',
        'display:flex;align-items:center;gap:12px;',
        'padding:14px 12px;cursor:pointer;',
        'transform:translateY(-150%);opacity:0;',
        'transition:transform .35s cubic-bezier(.34,1.2,.64,1),opacity .3s;',
        '-webkit-tap-highlight-color:transparent;',
        'max-width:400px;margin:0 auto;',
      '}',
      '@media(min-width:600px){#tsj-fg-toast{left:auto;width:360px;}}',
      '#tsj-fg-toast.tt-show{transform:translateY(0);opacity:1}',
      '.tt-icon{width:44px;height:44px;border-radius:12px;display:flex;',
        'align-items:center;justify-content:center;font-size:22px;',
        'flex-shrink:0;color:#fff;}',
      '.tt-body{flex:1;overflow:hidden;min-width:0}',
      '.tt-title{font-size:.85rem;font-weight:800;color:#0f172a;',
        'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px;}',
      '.tt-text{font-size:.76rem;color:#475569;line-height:1.4;',
        'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}',
      '.tt-cat{font-size:.66rem;font-weight:700;color:#94a3b8;',
        'text-transform:uppercase;letter-spacing:.04em;margin-top:3px;}',
      '.tt-x{background:none;border:none;cursor:pointer;color:#94a3b8;',
        'font-size:18px;padding:6px;flex-shrink:0;line-height:1;',
        'min-width:32px;min-height:32px;display:flex;align-items:center;justify-content:center;',
        'border-radius:50%;}',
      '.tt-x:hover,.tt-x:active{background:#f1f5f9;color:#475569}',
    ].join('');
  }

  function getPromptCSS() {
    // bottom: calc(70px + safe-area) — above mobile bottom nav bar
    return [
      '#tsj-push-prompt{',
        'position:fixed;',
        'bottom:calc(68px + env(safe-area-inset-bottom,0px));',
        'left:12px;right:12px;',
        'z-index:2147483645;',
        'background:#fff;border-radius:20px;',
        'box-shadow:0 -4px 40px rgba(0,0,0,.18),0 8px 40px rgba(0,0,0,.15);',
        'padding:20px 16px 16px;',
        'transform:translateY(120%);opacity:0;',
        'transition:transform .4s cubic-bezier(.34,1.2,.64,1),opacity .3s;',
        'max-width:420px;margin:0 auto;',
        'left:50%;transform:translateX(-50%) translateY(120%);width:calc(100% - 24px);',
      '}',
      '@media(min-width:600px){',
        '#tsj-push-prompt{width:380px;left:50%;transform:translateX(-50%) translateY(120%);}',
        '#tsj-push-prompt.pp-show{transform:translateX(-50%) translateY(0)!important;}',
      '}',
      '#tsj-push-prompt.pp-show{transform:translateX(-50%) translateY(0);opacity:1}',
      '.pp-close{position:absolute;top:10px;right:12px;background:none;border:none;',
        'cursor:pointer;color:#94a3b8;font-size:18px;',
        'min-width:36px;min-height:36px;display:flex;align-items:center;',
        'justify-content:center;border-radius:50%;',
        '-webkit-tap-highlight-color:transparent;}',
      '.pp-close:hover,.pp-close:active{background:#f1f5f9;color:#475569}',
      '.pp-head{text-align:center;margin-bottom:14px}',
      '.pp-bell{font-size:36px;margin-bottom:6px}',
      '.pp-title{font-size:1rem;font-weight:800;color:#0f172a;margin-bottom:5px;line-height:1.3}',
      '.pp-sub{font-size:.76rem;color:#64748b;line-height:1.5}',
      '.pp-cats{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin-bottom:14px}',
      '.pp-cat{font-size:.68rem;font-weight:700;padding:4px 10px;border-radius:20px;',
        'border:1.5px solid;background:#fff;white-space:nowrap;}',
      '.pp-allow{display:block;width:100%;padding:14px;',
        'background:linear-gradient(135deg,#1a56db,#0d2257);color:#fff;',
        'border:none;border-radius:12px;font-size:.9rem;font-weight:700;',
        'cursor:pointer;margin-bottom:10px;',
        'min-height:48px;', /* Touch target */
        '-webkit-tap-highlight-color:transparent;}',
      '.pp-allow:active{opacity:.9}',
      '.pp-later{display:block;width:100%;background:none;border:none;',
        'cursor:pointer;color:#94a3b8;font-size:.8rem;',
        'padding:8px;min-height:40px;', /* Touch target */
        '-webkit-tap-highlight-color:transparent;}',
    ].join('');
  }

  function getIOSCSS() {
    return [
      '#tsj-ios-prompt{',
        'position:fixed;bottom:0;left:0;right:0;',
        'z-index:2147483647;background:#fff;',
        'border-radius:20px 20px 0 0;',
        'box-shadow:0 -4px 40px rgba(0,0,0,.2);',
        'padding:24px 20px calc(20px + env(safe-area-inset-bottom,0px));',
        'transform:translateY(100%);opacity:0;',
        'transition:transform .4s cubic-bezier(.34,1.2,.64,1),opacity .3s;',
      '}',
      '#tsj-ios-prompt.ios-show{transform:translateY(0);opacity:1}',
      '.ios-close{position:absolute;top:12px;right:16px;background:#f1f5f9;',
        'border:none;border-radius:50%;width:32px;height:32px;',
        'cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;}',
      '.ios-icon{font-size:40px;text-align:center;margin-bottom:8px}',
      '.ios-title{font-size:.95rem;font-weight:800;color:#0f172a;text-align:center;margin-bottom:14px}',
      '.ios-steps{display:flex;flex-direction:column;gap:10px;margin-bottom:16px}',
      '.ios-step{display:flex;align-items:flex-start;gap:10px;font-size:.8rem;color:#475569;line-height:1.5}',
      '.ios-num{background:#1a56db;color:#fff;border-radius:50%;',
        'min-width:22px;height:22px;display:flex;align-items:center;',
        'justify-content:center;font-size:.72rem;font-weight:700;flex-shrink:0;}',
      '.ios-icon2{font-size:1.1em}',
      '.ios-ok{display:block;width:100%;padding:14px;',
        'background:#1a56db;color:#fff;border:none;border-radius:12px;',
        'font-size:.9rem;font-weight:700;cursor:pointer;}',
    ].join('');
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

    testNotification: function(category) {
      var cat = CATEGORIES[category || 'latest-jobs'] || CATEGORIES['latest-jobs'];
      if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({
          type: 'SHOW_TEST_NOTIFICATION',
          payload: { title: cat.emoji + ' Test: ' + cat.label,
                     body: 'Push notification working!', url: cat.url, category: category || 'latest-jobs' }
        });
      }
    },

    // For already-subscribed users — init FCM to receive foreground messages
    init: function() {
      if (!sg(SK.SUBSCRIBED)) return;
      registerSW().then(function() { return initFCM(); }).catch(function() {});
    },
  };

  // ══════════════════════════════════════════════════════════════════
  // AUTO INIT — Mobile optimized timing
  // ══════════════════════════════════════════════════════════════════
  function autoInit() {
    // Already subscribed → init FCM for foreground messages
    if (sg(SK.SUBSCRIBED)) {
      setTimeout(function() { window.TSJPush.init(); }, 2000);
    }

    // Show prompt timing:
    // Mobile: 8 seconds (user still on page)
    // Desktop: 15 seconds
    var delay = isMobile ? 8000 : 15000;
    setTimeout(function() {
      if (canShowPrompt()) showPrompt();
    }, delay);
  }

  // Start after DOM ready + small delay to not block page render
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      setTimeout(autoInit, 500);
    });
  } else {
    setTimeout(autoInit, 500);
  }

})();
