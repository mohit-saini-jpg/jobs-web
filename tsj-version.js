/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║   ZERO-STALE CACHE ENGINE — Version & Update System v7.0       ║
 * ║   Top Sarkari Jobs | topsarkarijobs.com                        ║
 * ║                                                                  ║
 * ║   ✅ Fetches version.json every 5 min (no-store)               ║
 * ║   ✅ Auto-detects new deploy → shows toast → auto-reloads      ║
 * ║   ✅ Clears ALL stale localStorage/sessionStorage               ║
 * ║   ✅ Handles SW registration, update detection & takeover       ║
 * ║   ✅ Handles waiting SW → forces skipWaiting immediately        ║
 * ║   ✅ Fires on tab visibility change (catches bg tab updates)    ║
 * ║   ✅ Safe storage cleanup (no QuotaExceededError)               ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */
(function ZeroStaleEngine() {
  'use strict';

  // ── Config ─────────────────────────────────────────────────────────
  var VERSION_URL      = '/version.json';
  var CHECK_INTERVAL   = 5 * 60 * 1000; // 5 minutes
  var LS_VER_KEY       = 'tsj_site_version';
  var LS_DATA_VER_KEY  = 'tsj_data_version';
  var DATA_SCHEMA_VER  = '7'; // Bump when JSON structure changes
  var SW_URL           = '/sw.js';
  var KNOWN_VERSION    = null;
  var _checkTimer      = null;
  var _toastShown      = false;

  // ── Step 1: Storage Cleanup — clear stale cache on schema change ───
  (function cleanStaleStorage() {
    try {
      var savedVer = localStorage.getItem(LS_DATA_VER_KEY);
      if (savedVer !== DATA_SCHEMA_VER) {
        // Collect all tsj_/sr_/ticker keys
        var toRemove = [];
        for (var i = 0; i < localStorage.length; i++) {
          var k = localStorage.key(i);
          if (k && (
            k.startsWith('tsj_') ||
            k.startsWith('__sr_') ||
            k.startsWith('__tsj_') ||
            k.startsWith('__ticker') ||
            k.startsWith('__cjfd')
          )) {
            toRemove.push(k);
          }
        }
        toRemove.forEach(function(k) { localStorage.removeItem(k); });
        // Clear ALL sessionStorage (JSON caches live here)
        sessionStorage.clear();
        localStorage.setItem(LS_DATA_VER_KEY, DATA_SCHEMA_VER);
        console.log('[TSJ-ZSCE] Storage reset — schema bumped to v' + DATA_SCHEMA_VER);
      }
    } catch (e) {}
  })();

  // ── Step 2: Safe sessionStorage setter ────────────────────────────
  // Prevents QuotaExceededError on mobile devices
  window.__tsjSSSet = function(key, value, maxKB) {
    maxKB = maxKB || 300;
    try {
      var str = JSON.stringify(value);
      if (str.length > maxKB * 1024) {
        console.warn('[TSJ-ZSCE] ' + key + ' too large (' + Math.round(str.length / 1024) + 'KB), skipping');
        return false;
      }
      sessionStorage.setItem(key, str);
      return true;
    } catch (e) {
      // QuotaExceededError — clear old keys and retry
      try {
        var oldKeys = Object.keys(sessionStorage).filter(function(k) {
          return k.startsWith('__sr_') || k.startsWith('__tsj_') || k.startsWith('__cjfd');
        });
        oldKeys.forEach(function(k) { sessionStorage.removeItem(k); });
        sessionStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (e2) { return false; }
    }
  };

  // ── Step 3: Fetch version.json (always fresh, never cached) ───────
  function fetchVersion() {
    return fetch(VERSION_URL + '?_t=' + Date.now(), {
      cache  : 'no-store',
      headers: { 'Cache-Control': 'no-cache, no-store', 'Pragma': 'no-cache' }
    })
    .then(function(r) { return r.ok ? r.json() : null; })
    .catch(function() { return null; });
  }

  // ── Step 4: Clear all caches (SW + browser) ───────────────────────
  function clearAllCaches(callback) {
    // Tell SW to nuke its caches
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_ALL_CACHES' });
    }
    // Clear JS-side caches
    try { sessionStorage.clear(); } catch (e) {}
    // Clear tsj_ localStorage keys
    try {
      var toRemove = [];
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && (k.startsWith('tsj_') || k.startsWith('__sr_') || k.startsWith('__tsj_') || k.startsWith('__cjfd'))) {
          toRemove.push(k);
        }
      }
      toRemove.forEach(function(k) { localStorage.removeItem(k); });
    } catch (e) {}

    if (typeof callback === 'function') callback();
  }

  // ── Step 5: Show update toast with auto-reload countdown ──────────
  function showUpdateToast(newVer) {
    if (_toastShown || document.getElementById('tsj-update-toast')) return;
    _toastShown = true;

    // Inject animation styles
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
      // Countdown bar
      '<div style="height:3px;background:rgba(255,255,255,.15);border-radius:0 0 12px 12px;overflow:hidden;margin:0 -14px;">',
        '<div id="tsj-toast-bar" style="height:100%;background:#f5a623;width:100%;animation:tsjCountdown 8s linear forwards;"></div>',
      '</div>',
    ].join('');

    document.body.appendChild(toast);

    // Update Now button
    document.getElementById('tsj-toast-update').addEventListener('click', function() {
      clearAllCaches(function() { location.reload(true); });
    });

    // Close button
    document.getElementById('tsj-toast-close').addEventListener('click', function() {
      toast.remove();
      _toastShown = false;
    });

    // Auto-reload after 8 seconds
    var autoReload = setTimeout(function() {
      if (document.getElementById('tsj-update-toast')) {
        clearAllCaches(function() { location.reload(true); });
      }
    }, 8000);

    // Cancel auto-reload if user closes toast
    document.getElementById('tsj-toast-close').addEventListener('click', function() {
      clearTimeout(autoReload);
    });
  }

  // ── Step 6: Version check logic ────────────────────────────────────
  function checkVersion() {
    // Skip check if tab not visible (save bandwidth on bg tabs)
    if (typeof document.hidden !== 'undefined' && document.hidden) return;

    fetchVersion().then(function(data) {
      if (!data || !data.version) return;
      var newVer = String(data.version);

      if (!KNOWN_VERSION) {
        // First check — record current version
        KNOWN_VERSION = newVer;
        try { localStorage.setItem(LS_VER_KEY, newVer); } catch (e) {}
        return;
      }

      if (newVer !== KNOWN_VERSION) {
        console.log('[TSJ-ZSCE] New deploy detected: ' + KNOWN_VERSION + ' → ' + newVer);
        KNOWN_VERSION = newVer;
        try { localStorage.setItem(LS_VER_KEY, newVer); } catch (e) {}

        // Tell SW to clear its caches too
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_ALL_CACHES' });
        }
        // Clear JS-side sessionStorage caches
        try { sessionStorage.clear(); } catch (e) {}

        // Show toast (auto-reloads in 8s)
        showUpdateToast(newVer);
      }
    });
  }

  // ── Step 7: Service Worker registration & lifecycle handling ───────
  if ('serviceWorker' in navigator) {
    // Listen for SW messages
    navigator.serviceWorker.addEventListener('message', function(e) {
      var type = (e.data || {}).type;

      // SW_UPDATED = new SW just took control
      if (type === 'SW_UPDATED') {
        console.log('[TSJ-ZSCE] SW activated v' + e.data.version);
        // Clear JS caches and reload
        try { sessionStorage.clear(); } catch (err) {}
        // Small delay to let SW settle before reload
        setTimeout(function() {
          location.reload(true);
        }, 400);
      }

      // Caches were cleared by SW
      if (type === 'CACHES_CLEARED') {
        console.log('[TSJ-ZSCE] SW caches cleared');
      }
    });

    // Register or update SW
    navigator.serviceWorker.register(SW_URL, {
      scope     : '/',
      updateViaCache: 'none', // CRITICAL: browser must always re-fetch sw.js
    })
    .then(function(reg) {
      console.log('[TSJ-ZSCE] SW registered, scope:', reg.scope);

      // Force immediate SW update check
      reg.update().catch(function() {});

      // If there's already a waiting SW → force it to activate NOW
      if (reg.waiting) {
        console.log('[TSJ-ZSCE] Waiting SW found → forcing activation');
        reg.waiting.postMessage({ type: 'SKIP_WAITING' });
      }

      // Watch for new SW installation
      reg.addEventListener('updatefound', function() {
        var installing = reg.installing;
        if (!installing) return;

        installing.addEventListener('statechange', function() {
          if (installing.state === 'installed') {
            if (reg.active) {
              // New SW installed but waiting → force it
              console.log('[TSJ-ZSCE] New SW installed → forcing skipWaiting');
              installing.postMessage({ type: 'SKIP_WAITING' });
            }
          }
        });
      });
    })
    .catch(function(err) {
      console.warn('[TSJ-ZSCE] SW registration failed:', err);
    });

    // Detect when SW controller changes (= new SW took over)
    navigator.serviceWorker.addEventListener('controllerchange', function() {
      console.log('[TSJ-ZSCE] SW controller changed → reloading');
      // Don't reload if user triggered it manually
      if (!_toastShown) {
        try { sessionStorage.clear(); } catch (e) {}
        location.reload(true);
      }
    });
  }

  // ── Step 8: Start version polling ──────────────────────────────────
  // First check after 3 seconds (don't block page load)
  setTimeout(checkVersion, 3000);
  // Then every 5 minutes
  _checkTimer = setInterval(checkVersion, CHECK_INTERVAL);

  // Also check when tab becomes visible again (catches updates while bg)
  document.addEventListener('visibilitychange', function() {
    if (!document.hidden) checkVersion();
  });

  // ── Step 9: Public API ──────────────────────────────────────────────
  window.TSJVersion = {
    check      : checkVersion,
    getVersion : function() { return KNOWN_VERSION; },
    forceUpdate: function() {
      clearAllCaches(function() { location.reload(true); });
    },
    clearCache : function() {
      clearAllCaches(function() {
        console.log('[TSJ-ZSCE] Cache cleared');
      });
    },
  };

  console.log('[TSJ-ZSCE] Zero-Stale Cache Engine v7.0 initialized');

})();
