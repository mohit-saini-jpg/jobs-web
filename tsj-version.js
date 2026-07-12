/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║   ZERO-STALE CACHE ENGINE — Version & Update System v8.0       ║
 * ║   Top Sarkari Jobs | topsarkarijobs.com                        ║
 * ║                                                                  ║
 * ║   ✅ Boot-time version check BEFORE any data fetch              ║
 * ║   ✅ sessionStorage cleared instantly on version mismatch       ║
 * ║   ✅ DATA_SCHEMA_VER='8' — one-time wipe of all v7 stale data  ║
 * ║   ✅ Fetches version.json every 5 min (no-store)               ║
 * ║   ✅ Auto-detects new deploy → shows toast → auto-reloads      ║
 * ║   ✅ Clears ALL stale localStorage/sessionStorage               ║
 * ║   ✅ SW registration with updateViaCache:'none'                 ║
 * ║   ✅ Reload loop guard: 10s minimum between reloads             ║
 * ║   ✅ iOS Safari safe: updateViaCache in try/catch               ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */
(function ZeroStaleEngine() {
  'use strict';

  // ── Config ──────────────────────────────────────────────────────────
  var VERSION_URL      = '/version.json';
  var CHECK_INTERVAL   = 6 * 60 * 60 * 1000;  // 6 hours (reduced edge requests)
  var LS_VER_KEY       = 'tsj_site_version';
  var LS_DATA_VER_KEY  = 'tsj_data_version';
  var DATA_SCHEMA_VER  = '8';             // RC-4 FIX: bumped from 7 → clears all v7 stale data
  var SW_URL           = '/sw.js';
  var KNOWN_VERSION    = null;
  var _checkTimer      = null;
  var _toastShown      = false;
  var _lastReload      = 0;               // RC-7 FIX: reload loop guard

  // ── STEP 0: RC-4 FIX — Boot-time version check ─────────────────────
  // This script loads with `defer`, so by the time it runs, index.html's
  // own inline fetches (sections-index.json etc.) have already started —
  // a synchronous XHR here can no longer actually block them, it just
  // blocks the main thread for no benefit (and sync XHR is deprecated by
  // browsers). Fetch async instead; on a version mismatch, sessionStorage
  // is cleared a beat later than before, which is an acceptable tradeoff.
  (function bootVersionCheck() {
    try {
      var savedVer = localStorage.getItem(LS_VER_KEY);
      if (savedVer) {
        fetch(VERSION_URL + '?_t=' + Date.now(), {
          cache: 'no-store',
          headers: { 'Pragma': 'no-cache' }
        }).then(function(r) { return r.ok ? r.json() : null; })
          .then(function(data) {
            if (data && data.version && String(data.version) !== savedVer) {
              sessionStorage.clear();
              localStorage.setItem(LS_VER_KEY, String(data.version));
              KNOWN_VERSION = String(data.version);
              console.log('[TSJ-ZSCE v8] Boot check: version changed, sessionStorage cleared');
            } else if (data && data.version) {
              KNOWN_VERSION = String(data.version);
            }
          }).catch(function() {
            // fetch failed (CORS, offline, etc.) — async check will catch it
          });
      }
    } catch (e) {}
  })();

  // ── Step 1: Storage Cleanup — clear stale data on schema change ────
  (function cleanStaleStorage() {
    try {
      var savedVer = localStorage.getItem(LS_DATA_VER_KEY);
      if (savedVer !== DATA_SCHEMA_VER) {
        // Wipe all tsj_ / __sr_ / __tsj_ / __ticker / __cjfd / __sections / __daily keys
        var toRemove = [];
        for (var i = 0; i < localStorage.length; i++) {
          var k = localStorage.key(i);
          if (k && (
            k.startsWith('tsj_') ||
            k.startsWith('__sr_') ||
            k.startsWith('__tsj_') ||
            k.startsWith('__ticker') ||
            k.startsWith('__cjfd') ||
            k.startsWith('__sections') ||
            k.startsWith('__daily')
          )) {
            toRemove.push(k);
          }
        }
        toRemove.forEach(function(k) { localStorage.removeItem(k); });
        sessionStorage.clear();
        localStorage.setItem(LS_DATA_VER_KEY, DATA_SCHEMA_VER);
        console.log('[TSJ-ZSCE v8] Storage reset — schema bumped to v' + DATA_SCHEMA_VER);
      }
    } catch (e) {}
  })();

  // ── Step 2: Safe sessionStorage setter ─────────────────────────────
  window.__tsjSSSet = function(key, value, maxKB) {
    maxKB = maxKB || 300;
    try {
      var str = JSON.stringify(value);
      if (str.length > maxKB * 1024) {
        console.warn('[TSJ-ZSCE v8] ' + key + ' too large (' + Math.round(str.length / 1024) + 'KB), skipping');
        return false;
      }
      sessionStorage.setItem(key, str);
      return true;
    } catch (e) {
      try {
        var oldKeys = Object.keys(sessionStorage).filter(function(k) {
          return k.startsWith('__sr_') || k.startsWith('__tsj_') || k.startsWith('__cjfd') ||
                 k.startsWith('__sections') || k.startsWith('__daily');
        });
        oldKeys.forEach(function(k) { sessionStorage.removeItem(k); });
        sessionStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (e2) { return false; }
    }
  };

  // ── Step 3: Fetch version.json (always fresh, RC-3 safe) ───────────
  // Uses ?_t= cache buster + no-store header
  // SW matches by pathname '/version.json' so ?_t= variant is also caught
  function fetchVersion() {
    return fetch(VERSION_URL, {
      cache  : 'no-cache'
    })
    .then(function(r) { return r.ok ? r.json() : null; })
    .catch(function() { return null; });
  }

  // ── Step 4: Clear all caches (SW + browser) ────────────────────────
  function clearAllCaches(callback) {
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_ALL_CACHES' });
    }
    try { sessionStorage.clear(); } catch (e) {}
    try {
      var toRemove = [];
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && (
          k.startsWith('tsj_') || k.startsWith('__sr_') ||
          k.startsWith('__tsj_') || k.startsWith('__cjfd') ||
          k.startsWith('__sections') || k.startsWith('__daily')
        )) {
          toRemove.push(k);
        }
      }
      toRemove.forEach(function(k) { localStorage.removeItem(k); });
    } catch (e) {}
    if (typeof callback === 'function') callback();
  }

  // ── Step 5: Show update toast with countdown ───────────────────────
  function showUpdateToast(newVer) {
    if (_toastShown || document.getElementById('tsj-update-toast')) return;
    _toastShown = true;

    if (!document.getElementById('tsj-toast-style')) {
      var style = document.createElement('style');
      style.id = 'tsj-toast-style';
      style.textContent = [
        '@keyframes tsjSlideIn{from{opacity:0;transform:translateX(-50%) translateY(-20px)}',
        'to{opacity:1;transform:translateX(-50%) translateY(0)}}',
        '@keyframes tsjCountdown{from{width:100%}to{width:0%}}'
      ].join('');
      document.head.appendChild(style);
    }

    var toast = document.createElement('div');
    toast.id = 'tsj-update-toast';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');
    toast.style.cssText = [
      'position:fixed;top:72px;left:50%;transform:translateX(-50%);',
      'background:#0d2257;color:#fff;border-radius:12px;',
      'box-shadow:0 6px 24px rgba(0,0,0,.4);',
      'padding:12px 14px 0;z-index:2147483647;',
      'display:flex;flex-direction:column;gap:0;',
      'max-width:340px;width:calc(100% - 24px);',
      'animation:tsjSlideIn .3s ease;',
      'font-family:-apple-system,BlinkMacSystemFont,sans-serif;',
    ].join('');

    toast.innerHTML = [
      '<div style="display:flex;align-items:center;gap:10px;padding-bottom:10px;">',
        '<span style="font-size:20px;flex-shrink:0;">🔄</span>',
        '<span style="flex:1;font-size:.82rem;font-weight:600;line-height:1.3;">',
          'New version available!<br>',
          '<span style="font-weight:400;opacity:.75;font-size:.74rem;">Auto-updating in 8 seconds…</span>',
        '</span>',
        '<button id="tsj-toast-update" style="background:#f5a623;color:#0d2257;border:none;border-radius:7px;padding:6px 12px;font-size:.78rem;font-weight:700;cursor:pointer;white-space:nowrap;flex-shrink:0;">',
          'Update Now',
        '</button>',
        '<button id="tsj-toast-close" style="background:none;border:none;color:rgba(255,255,255,.5);cursor:pointer;font-size:18px;padding:0 2px;margin-left:4px;line-height:1;flex-shrink:0;">✕</button>',
      '</div>',
      '<div style="height:3px;background:rgba(255,255,255,.15);border-radius:0 0 12px 12px;overflow:hidden;margin:0 -14px;">',
        '<div id="tsj-toast-bar" style="height:100%;background:#f5a623;width:100%;animation:tsjCountdown 8s linear forwards;"></div>',
      '</div>',
    ].join('');

    document.body.appendChild(toast);

    document.getElementById('tsj-toast-update').addEventListener('click', function() {
      clearAllCaches(function() { location.reload(true); });
    });

    var autoReload = setTimeout(function() {
      if (document.getElementById('tsj-update-toast')) {
        clearAllCaches(function() { location.reload(true); });
      }
    }, 8000);

    document.getElementById('tsj-toast-close').addEventListener('click', function() {
      toast.remove();
      _toastShown = false;
      clearTimeout(autoReload);
    });
  }

  // ── Step 6: Version check logic (mid-session polling) ──────────────
  function checkVersion() {
    if (typeof document.hidden !== 'undefined' && document.hidden) return;

    fetchVersion().then(function(data) {
      if (!data || !data.version) return;
      var newVer = String(data.version);

      if (!KNOWN_VERSION) {
        KNOWN_VERSION = newVer;
        try { localStorage.setItem(LS_VER_KEY, newVer); } catch (e) {}
        return;
      }

      if (newVer !== KNOWN_VERSION) {
        console.log('[TSJ-ZSCE v8] New deploy: ' + KNOWN_VERSION + ' → ' + newVer);
        KNOWN_VERSION = newVer;
        try { localStorage.setItem(LS_VER_KEY, newVer); } catch (e) {}

        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_ALL_CACHES' });
        }
        try { sessionStorage.clear(); } catch (e) {}

        showUpdateToast(newVer);
      }
    });
  }

  // ── Step 7: Service Worker registration ────────────────────────────
  if ('serviceWorker' in navigator) {
    // PERF FIX (regressed once already — see PERMANENT NOTE at bottom of
    // this file before touching this block again): a first-time visitor
    // has no controller yet — registering the SW for the first time
    // (skipWaiting + clients.claim in sw.js) makes the browser fire
    // 'controllerchange' / our own 'SW_UPDATED' message exactly once, which
    // this code used to treat as "new deploy, reload now". That forced a
    // full page reload on every single first visit — measured by real PSI
    // as a ~3.5-4.7s "redirect"/render-delay eating the whole LCP budget.
    // Only reload for a REAL update: page already had an active controller
    // before this registration.
    var hadControllerAtBoot = !!navigator.serviceWorker.controller;

    navigator.serviceWorker.addEventListener('message', function(e) {
      var type = (e.data || {}).type;

      if (type === 'SW_UPDATED') {
        console.log('[TSJ-ZSCE v8] SW activated v' + e.data.version);
        if (!hadControllerAtBoot) {
          console.log('[TSJ-ZSCE v8] First-time SW install — no reload needed');
          return;
        }
        // RC-7 FIX: only reload if enough time has passed (prevent reload loops)
        var now = Date.now();
        if (now - _lastReload > 10000) {
          _lastReload = now;
          try { sessionStorage.clear(); } catch (err) {}
          // 800ms delay — enough for SW to fully settle after clients.claim()
          setTimeout(function() {
            location.reload(true);
          }, 800);
        } else {
          console.log('[TSJ-ZSCE v8] Reload suppressed (too recent)');
        }
      }

      if (type === 'CACHES_CLEARED') {
        console.log('[TSJ-ZSCE v8] SW caches cleared');
      }
    });

    // RC-8 FIX: iOS Safari safe registration (updateViaCache in try/catch)
    var swOpts = { scope: '/' };
    try { swOpts.updateViaCache = 'none'; } catch (e) {}

    navigator.serviceWorker.register(SW_URL, swOpts)
    .then(function(reg) {
      console.log('[TSJ-ZSCE v8] SW registered, scope:', reg.scope);
      reg.update().catch(function() {});

      if (reg.waiting) {
        console.log('[TSJ-ZSCE v8] Waiting SW found → forcing activation');
        reg.waiting.postMessage({ type: 'SKIP_WAITING' });
      }

      reg.addEventListener('updatefound', function() {
        var installing = reg.installing;
        if (!installing) return;
        installing.addEventListener('statechange', function() {
          if (installing.state === 'installed' && reg.active) {
            console.log('[TSJ-ZSCE v8] New SW installed → forcing skipWaiting');
            installing.postMessage({ type: 'SKIP_WAITING' });
          }
        });
      });
    })
    .catch(function(err) {
      console.warn('[TSJ-ZSCE v8] SW registration failed:', err);
    });

    // Detect SW controller change (new SW took over)
    navigator.serviceWorker.addEventListener('controllerchange', function() {
      // BUG FIX: this used to set hadControllerAtBoot = true here, which
      // broke the very thing it was meant to fix — controllerchange and the
      // SW_UPDATED message BOTH fire once during the SAME initial activation
      // (controllerchange first, then SW_UPDATED ~500ms later per sw.js).
      // Flipping the flag after the first one made the SECOND one think it
      // was a genuine later update and reload anyway — confirmed via a
      // console-log trace: "First-time SW claim" at 224ms, then an actual
      // reload-triggered navigation at 1533ms. hadControllerAtBoot must stay
      // a fixed boot-time snapshot for the whole page session; a long-lived
      // tab still gets real update prompts via the 6-hourly checkVersion()
      // poll and its own toast/reload path, independent of this listener.
      if (!hadControllerAtBoot) {
        console.log('[TSJ-ZSCE v8] First-time SW claim — no reload needed');
        return;
      }
      console.log('[TSJ-ZSCE v8] SW controller changed → reloading');
      // RC-7 FIX: only reload if toast not shown AND enough time has passed
      var now = Date.now();
      if (!_toastShown && (now - _lastReload > 10000)) {
        _lastReload = now;
        try { sessionStorage.clear(); } catch (e) {}
        location.reload(true);
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════════
  // PERMANENT NOTE — DO NOT REMOVE hadControllerAtBoot WITHOUT RE-READING
  // ═══════════════════════════════════════════════════════════════════
  // This exact fix was implemented, reverted (as part of an unrelated bulk
  // revert), and had to be re-diagnosed from a real PSI report + re-applied
  // TWICE in one day (2026-07-12) before this comment was added. Real cost
  // measured both times: LCP balloons to 4-34s and Performance score drops
  // to the 40s-70s range because every first-time visitor gets an
  // unexpected full page reload mid-load. If you are about to revert a
  // commit that touches this file, check whether it also removes
  // `hadControllerAtBoot` — if so, that specific change should survive the
  // revert. The automated Lighthouse Performance Monitor (see
  // .github/workflows/lighthouse.yml) will reopen the tracking GitHub issue
  // (label: perf-regression) within one push if this regresses again.

  // ── Step 7b: Trigger SW precache only AFTER the page has fully loaded —
  // see the matching PERF FIX comment in sw.js's install handler for why
  // (was racing the page's own first-load fetches for the same assets).
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
      setTimeout(function() {
        if (navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({ type: 'PRECACHE_NOW' });
        }
      }, 5000);
    });
  }

  // ── Step 8: Start version polling ──────────────────────────────────
  setTimeout(checkVersion, 3000);
  _checkTimer = setInterval(checkVersion, CHECK_INTERVAL);

  document.addEventListener('visibilitychange', function() {
    if (!document.hidden) checkVersion();
  });

  // ── Step 9: Public API ──────────────────────────────────────────────
  window.TSJVersion = {
    check      : checkVersion,
    getVersion : function() { return KNOWN_VERSION; },
    forceUpdate: function() { clearAllCaches(function() { location.reload(true); }); },
    clearCache : function() { clearAllCaches(function() { console.log('[TSJ-ZSCE v8] Cache cleared'); }); },
  };

  console.log('[TSJ-ZSCE] Zero-Stale Cache Engine v8.0 initialized');

})();
