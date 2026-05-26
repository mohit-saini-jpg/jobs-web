/**
 * TSJ Version & Auto-Update System v1.0
 * - Fetches version.json every 5 minutes
 * - Auto-reloads when new version detected
 * - Clears stale localStorage/sessionStorage
 * - Shows "Update available" toast (no forced reload without user awareness)
 */
(function TSJVersionSystem() {
  'use strict';

  var VERSION_URL      = '/version.json';
  var CHECK_INTERVAL   = 5 * 60 * 1000; // 5 min
  var LS_VERSION_KEY   = 'tsj_site_version';
  var LS_DATA_VER_KEY  = 'tsj_data_version';
  var CURRENT_VERSION  = null;

  // ── LocalStorage version control ───────────────────────────
  // If data schema version changes, clear old stale data
  var DATA_SCHEMA_VER = '6'; // bump this when JSON structure changes

  (function cleanStaleStorage() {
    try {
      var savedDataVer = localStorage.getItem(LS_DATA_VER_KEY);
      if (savedDataVer !== DATA_SCHEMA_VER) {
        // Clear ALL tsj_ prefixed keys
        var toRemove = [];
        for (var i = 0; i < localStorage.length; i++) {
          var k = localStorage.key(i);
          if (k && (k.startsWith('tsj_') || k.startsWith('__sr_') || k.startsWith('__ticker'))) {
            toRemove.push(k);
          }
        }
        toRemove.forEach(function(k) { localStorage.removeItem(k); });
        // Clear ALL sessionStorage (JSON caches)
        sessionStorage.clear();
        localStorage.setItem(LS_DATA_VER_KEY, DATA_SCHEMA_VER);
        console.log('[TSJ] Cleared stale storage, schema bumped to v' + DATA_SCHEMA_VER);
      }
    } catch(e) {}
  })();

  // ── Fetch current version ───────────────────────────────────
  function fetchVersion() {
    return fetch(VERSION_URL + '?_=' + Date.now(), {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' }
    })
    .then(function(r) { return r.ok ? r.json() : null; })
    .catch(function() { return null; });
  }

  // ── Show update toast ───────────────────────────────────────
  function showUpdateToast(newVer) {
    if (document.getElementById('tsj-update-toast')) return;
    var t = document.createElement('div');
    t.id = 'tsj-update-toast';
    t.style.cssText = [
      'position:fixed;top:70px;left:50%;transform:translateX(-50%);',
      'background:#0d2257;color:#fff;border-radius:10px;',
      'box-shadow:0 4px 20px rgba(0,0,0,.3);',
      'padding:12px 16px;z-index:2147483647;',
      'display:flex;align-items:center;gap:10px;',
      'font-size:.82rem;font-weight:600;',
      'max-width:340px;width:calc(100% - 24px);',
      'animation:tsjSlideIn .3s ease;',
    ].join('');

    var style = document.createElement('style');
    style.textContent = '@keyframes tsjSlideIn{from{opacity:0;transform:translateX(-50%) translateY(-20px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}';
    document.head.appendChild(style);

    t.innerHTML =
      '<span style="font-size:18px">🔄</span>' +
      '<span style="flex:1">New version available!</span>' +
      '<button onclick="location.reload()" style="background:#f5a623;color:#0d2257;border:none;border-radius:6px;padding:5px 12px;font-size:.78rem;font-weight:700;cursor:pointer;white-space:nowrap;">Update Now</button>' +
      '<button onclick="this.parentNode.remove()" style="background:none;border:none;color:rgba(255,255,255,.6);cursor:pointer;font-size:16px;padding:0 4px;">✕</button>';

    document.body.appendChild(t);

    // Auto-reload after 10 seconds (silently)
    setTimeout(function() {
      if (document.getElementById('tsj-update-toast')) {
        location.reload();
      }
    }, 10000);
  }

  // ── Check for updates ───────────────────────────────────────
  function checkVersion() {
    if (document.hidden) return; // skip if tab not visible

    fetchVersion().then(function(data) {
      if (!data || !data.version) return;

      var newVer = data.version;

      if (!CURRENT_VERSION) {
        // First check — store version
        CURRENT_VERSION = newVer;
        try { localStorage.setItem(LS_VERSION_KEY, newVer); } catch(e) {}
        return;
      }

      if (newVer !== CURRENT_VERSION) {
        console.log('[TSJ] New version detected:', newVer, '(was:', CURRENT_VERSION + ')');
        CURRENT_VERSION = newVer;
        try { localStorage.setItem(LS_VERSION_KEY, newVer); } catch(e) {}

        // Clear all caches via SW
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_ALL_CACHES' });
        }

        // Clear sessionStorage JSON caches
        try { sessionStorage.clear(); } catch(e) {}

        // Show update toast
        showUpdateToast(newVer);
      }
    });
  }

  // ── Listen for SW update notifications ─────────────────────
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', function(e) {
      if (e.data && e.data.type === 'SW_UPDATED') {
        console.log('[TSJ] SW updated to v' + e.data.version);
        // Small delay then reload — SW has taken control
        setTimeout(function() {
          try { sessionStorage.clear(); } catch(e2) {}
          location.reload();
        }, 500);
      }
    });

    // Check if there's a waiting SW and activate it
    navigator.serviceWorker.ready.then(function(reg) {
      if (reg.waiting) {
        reg.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
      reg.addEventListener('updatefound', function() {
        var nw = reg.installing;
        if (!nw) return;
        nw.addEventListener('statechange', function() {
          if (nw.state === 'installed') {
            nw.postMessage({ type: 'SKIP_WAITING' });
          }
        });
      });
    });
  }

  // ── Start version checking ──────────────────────────────────
  // First check after 3 seconds (don't block page load)
  setTimeout(checkVersion, 3000);
  // Then every 5 minutes
  setInterval(checkVersion, CHECK_INTERVAL);

  // ── Export for manual use ───────────────────────────────────
  window.TSJVersion = {
    check: checkVersion,
    clearCache: function() {
      try { sessionStorage.clear(); localStorage.clear(); } catch(e) {}
      if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_ALL_CACHES' });
      }
      setTimeout(function() { location.reload(); }, 500);
    }
  };

})();
