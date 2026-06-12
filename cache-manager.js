/**
 * ╔══════════════════════════════════════════════════════════════╗
 * ║      HYBRID DYNAMIC CACHE MANAGER — cache-manager.js        ║
 * ║      Client-side controller for sw.js                       ║
 * ║                                                              ║
 * ║  Handles:                                                    ║
 * ║  • Service Worker registration + update lifecycle            ║
 * ║  • Background job data refresh (API fetch, no-cache)         ║
 * ║  • Cache stats reporting to DevTools / admin panel           ║
 * ║  • Periodic cache trimming                                   ║
 * ║  • "New version available" toast notification                ║
 * ╚══════════════════════════════════════════════════════════════╝
 */

'use strict';

const CacheManager = (() => {

  // ─── Config ────────────────────────────────────────────────────────────────
  const CONFIG = {
    swPath:               '/sw.js',
    swScope:              '/',
    // How often to attempt a background data refresh (ms)
    dataRefreshInterval:  10 * 60 * 1000,   // 10 min idle-on-return threshold
    // Show "update ready" toast after SW update found
    showUpdateToast:      true,
    // Auto-trim caches every N minutes
    trimInterval:         30 * 60 * 1000,  // 30 minutes
    // Log level: 'silent' | 'info' | 'verbose'
    logLevel:             'info',
  };

  // ─── Internal state ────────────────────────────────────────────────────────
  let registration   = null;
  let refreshTimer   = null;
  let trimTimer      = null;
  let _newWorker     = null;

  // ─────────────────────────────────────────────────────────────────────────
  // PUBLIC API
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * init() — call once after DOMContentLoaded.
   * Registers SW, schedules refresh + trim timers.
   */
  async function init() {
    if (!('serviceWorker' in navigator)) {
      log('warn', 'Service Workers not supported in this browser');
      return;
    }

    try {
      registration = await navigator.serviceWorker.register(CONFIG.swPath, {
        scope:       CONFIG.swScope,
        updateViaCache: 'none',    // Always check for SW updates via network
      });

      log('info', `SW registered (scope: ${registration.scope})`);

      // ── Update lifecycle handling ─────────────────────────────────────────
      registration.addEventListener('updatefound', onUpdateFound);
      navigator.serviceWorker.addEventListener('controllerchange', onControllerChange);

      // Check for updates on page visibility change
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
          registration?.update().catch(() => {});
        }
      });

      // ── Periodic SW update check ──────────────────────────────────────────
      setInterval(() => registration?.update().catch(() => {}), 60 * 60 * 1000);

      // ── Background data refresh ───────────────────────────────────────────
      scheduleDataRefresh();

      // ── Auto-trim ─────────────────────────────────────────────────────────
      scheduleTrim();

      // ── Report initial stats (verbose mode) ──────────────────────────────
      if (CONFIG.logLevel === 'verbose') {
        getCacheStats().then(stats => log('verbose', 'Cache stats:', stats));
      }

    } catch (err) {
      log('warn', 'SW registration failed:', err.message);
    }
  }

  /**
   * fetchJobData(url) — always-fresh job API fetch.
   * Bypasses SW cache entirely using cache: 'no-store'.
   */
  async function fetchJobData(url) {
    log('verbose', `[no-cache] Fetching job data: ${url}`);

    const response = await fetch(url, {
      method:  'GET',
      cache:   'no-store',
      headers: {
        'Cache-Control': 'no-store, no-cache',
        'Pragma':        'no-cache',
      },
    });

    if (!response.ok) {
      throw new Error(`Job data fetch failed: HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * clearPageCache() — drop the HTML pages cache.
   * Useful after a major content update.
   */
  async function clearPageCache() {
    if (!registration?.active) return false;

    return new Promise(resolve => {
      const channel = new MessageChannel();
      channel.port1.onmessage = e => resolve(e.data?.ok === true);
      registration.active.postMessage({ type: 'CLEAR_JOB_CACHE' }, [channel.port2]);
    });
  }

  /**
   * getCacheStats() — returns per-cache size + entry counts.
   */
  async function getCacheStats() {
    if (!registration?.active) return null;

    return new Promise(resolve => {
      const channel = new MessageChannel();
      channel.port1.onmessage = e => resolve(e.data);
      registration.active.postMessage({ type: 'GET_CACHE_STATS' }, [channel.port2]);
    });
  }

  /**
   * trimCaches() — manually trigger cache eviction.
   */
  async function trimCaches() {
    if (!registration?.active) return;

    return new Promise(resolve => {
      const channel = new MessageChannel();
      channel.port1.onmessage = e => resolve(e.data?.ok);
      registration.active.postMessage({ type: 'TRIM_CACHES' }, [channel.port2]);
    });
  }

  /**
   * applyUpdate() — activates waiting SW immediately (triggers reload).
   */
  function applyUpdate() {
    if (_newWorker) {
      _newWorker.postMessage({ type: 'SKIP_WAITING' });
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // INTERNALS
  // ─────────────────────────────────────────────────────────────────────────

  function onUpdateFound() {
    const newWorker = registration.installing;
    if (!newWorker) return;

    log('info', 'SW update found — installing…');

    newWorker.addEventListener('statechange', () => {
      if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
        log('info', 'New SW installed and waiting — showing update toast');
        _newWorker = newWorker;
        if (CONFIG.showUpdateToast) showUpdateToast();
      }
    });
  }

  function onControllerChange() {
    log('info', 'SW controller changed — reloading page for fresh assets');
    window.location.reload();
  }

  // ── Background Data Refresh ───────────────────────────────────────────────

  function scheduleDataRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);

    // Data is re-fetched automatically when version.json changes (handled by
    // tsj-version.js, polled every 90s). No blind interval polling needed —
    // that was re-downloading the 62MB master JSON unnecessarily.
    // Still refresh when user returns to a tab that's been idle a while.
    var _lastRefresh = Date.now();
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' &&
          (Date.now() - _lastRefresh) > CONFIG.dataRefreshInterval) {
        _lastRefresh = Date.now();
        document.dispatchEvent(new CustomEvent('cache:refresh'));
      }
    });
  }

  function scheduleTrim() {
    if (trimTimer) clearInterval(trimTimer);
    trimTimer = setInterval(() => {
      trimCaches().then(() => log('verbose', 'Cache trim complete'));
    }, CONFIG.trimInterval);
  }

  // ── Update Toast ──────────────────────────────────────────────────────────

  function showUpdateToast() {
    // Avoid creating duplicate toasts
    if (document.getElementById('sw-update-toast')) return;

    const toast = document.createElement('div');
    toast.id    = 'sw-update-toast';
    toast.innerHTML = `
      <span>🚀 New version available</span>
      <button id="sw-update-btn">Update Now</button>
      <button id="sw-toast-close" aria-label="Dismiss">✕</button>
    `;

    Object.assign(toast.style, {
      position:        'fixed',
      bottom:          '20px',
      left:            '50%',
      transform:       'translateX(-50%)',
      background:      '#1e293b',
      color:           '#f1f5f9',
      padding:         '12px 16px',
      borderRadius:    '10px',
      display:         'flex',
      alignItems:      'center',
      gap:             '12px',
      fontSize:        '14px',
      fontWeight:      '500',
      zIndex:          '99999',
      boxShadow:       '0 8px 32px rgba(0,0,0,0.4)',
      border:          '1px solid #334155',
      maxWidth:        'calc(100vw - 40px)',
      animation:       'swToastIn 0.3s ease',
    });

    // Inject keyframes once
    if (!document.getElementById('sw-toast-styles')) {
      const style = document.createElement('style');
      style.id    = 'sw-toast-styles';
      style.textContent = `
        @keyframes swToastIn {
          from { opacity:0; transform:translateX(-50%) translateY(12px) }
          to   { opacity:1; transform:translateX(-50%) translateY(0) }
        }
        #sw-update-btn {
          background:#f97316; color:#fff; border:none;
          padding:6px 14px; border-radius:6px; font-size:13px;
          font-weight:600; cursor:pointer; white-space:nowrap;
        }
        #sw-toast-close {
          background:none; border:none; color:#94a3b8;
          font-size:16px; cursor:pointer; padding:2px 4px;
          line-height:1;
        }
      `;
      document.head.appendChild(style);
    }

    document.body.appendChild(toast);

    document.getElementById('sw-update-btn').addEventListener('click', () => {
      toast.remove();
      applyUpdate();
    });

    document.getElementById('sw-toast-close').addEventListener('click', () => {
      toast.remove();
    });

    // Auto-dismiss after 15s
    setTimeout(() => toast?.remove(), 15_000);
  }

  // ── Logger ────────────────────────────────────────────────────────────────

  function log(level, ...args) {
    const levels = { silent: 0, warn: 1, info: 2, verbose: 3 };
    const current = levels[CONFIG.logLevel] ?? 2;
    if (levels[level] <= current) {
      const prefix = `[CacheManager]`;
      if (level === 'warn') console.warn(prefix, ...args);
      else                  console.log(prefix, ...args);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  return { init, fetchJobData, clearPageCache, getCacheStats, trimCaches, applyUpdate };

})();

// ─── Auto-init on DOMContentLoaded ───────────────────────────────────────────
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => CacheManager.init());
} else {
  CacheManager.init();
}

// ─── Export for module environments ──────────────────────────────────────────
if (typeof module !== 'undefined') module.exports = CacheManager;
