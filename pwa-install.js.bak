/**
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║   TOP SARKARI JOBS — PWA INSTALL SYSTEM v4.0                    ║
 * ║   Android · iOS · Desktop · Windows PWA                         ║
 * ║   beforeinstallprompt · iOS Smart Banner · TWA Detection        ║
 * ╚══════════════════════════════════════════════════════════════════╝
 */

(function TSJ_PWA() {
  'use strict';

  // ─── Config ────────────────────────────────────────────────────────────────
  const CONFIG = {
    appName:        'Top Sarkari Jobs',
    appShortName:   'TopSarkariJobs',
    themeColor:     '#0d2257',
    accentColor:    '#f5a623',
    whiteColor:     '#ffffff',
    installDelay:   4000,     // ms before showing install banner
    iosBannerDelay: 3000,
    dismissDays:    7,        // days to hide after dismiss
    storageKey:     'tsj_pwa_',
    vapidKey:       'YOUR_VAPID_PUBLIC_KEY_HERE', // Replace with actual VAPID key
  };

  // ─── State ─────────────────────────────────────────────────────────────────
  let deferredPrompt = null;
  const ua = navigator.userAgent;
  const isAndroid    = /Android/i.test(ua);
  const isIOS        = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
  const isIPad       = /iPad/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const isWindows    = /Windows/.test(ua);
  const isMac        = /Macintosh/.test(ua) && !isIPad;
  const isSafari     = /Safari/.test(ua) && !/Chrome/.test(ua);
  const isChrome     = /Chrome/.test(ua) && !/Edge/.test(ua);
  const isEdge       = /Edg\//.test(ua);
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches
                    || window.navigator.standalone === true
                    || document.referrer.includes('android-app://');
  const isTWA        = document.referrer.startsWith('android-app://') || 
                       (new URLSearchParams(location.search)).get('twa') === '1';

  // ─── Storage Helpers ────────────────────────────────────────────────────────
  function store(key, val) {
    try { localStorage.setItem(CONFIG.storageKey + key, JSON.stringify(val)); } catch {}
  }
  function retrieve(key) {
    try { return JSON.parse(localStorage.getItem(CONFIG.storageKey + key)); } catch { return null; }
  }
  function isDismissed(key) {
    const t = retrieve(key + '_dismissed');
    if (!t) return false;
    return (Date.now() - t) < CONFIG.dismissDays * 86400000;
  }
  function dismiss(key) {
    store(key + '_dismissed', Date.now());
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SERVICE WORKER REGISTRATION
  // ══════════════════════════════════════════════════════════════════════════
  function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;

    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js?v=4.0').then(function (reg) {
        console.log('[PWA] SW registered, scope:', reg.scope);

        // Auto-update: when new SW found, activate immediately
        reg.addEventListener('updatefound', function () {
          const newWorker = reg.installing;
          newWorker.addEventListener('statechange', function () {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              newWorker.postMessage({ type: 'SKIP_WAITING' });
              showUpdateToast();
            }
          });
        });

        // Schedule background sync for job data
        if ('SyncManager' in window) {
          reg.sync.register('sync-jobs-data').catch(() => {});
        }

        // Periodic background sync (Chrome 80+)
        if ('periodicSync' in reg) {
          reg.periodicSync.register('tsj-daily-sync', {
            minInterval: 24 * 60 * 60 * 1000
          }).catch(() => {});
        }

        // Store reg globally for push notifications
        window._tsjSWReg = reg;

      }).catch(function (err) {
        console.warn('[PWA] SW registration failed:', err);
      });

      // Reload on controller change
      let refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', function () {
        if (!refreshing) { refreshing = true; window.location.reload(); }
      });

      // Listen for messages from SW
      navigator.serviceWorker.addEventListener('message', function (event) {
        const { type } = event.data || {};
        if (type === 'JOBS_SYNCED') {
          showToast('✅ Jobs data updated in background!', 3000);
        }
      });
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // CSS INJECTION
  // ══════════════════════════════════════════════════════════════════════════
  function injectStyles() {
    const css = `
/* ── TSJ PWA Install UI ─────────────────────────────────────── */
#tsj-pwa-overlay {
  position: fixed; inset: 0; z-index: 999990;
  background: rgba(0,0,0,0.55); backdrop-filter: blur(4px);
  display: flex; align-items: flex-end; justify-content: center;
  padding: 0 0 env(safe-area-inset-bottom, 0);
  opacity: 0; transition: opacity 0.3s ease;
  pointer-events: none;
}
#tsj-pwa-overlay.visible { opacity: 1; pointer-events: all; }

#tsj-install-sheet {
  background: #fff; border-radius: 24px 24px 0 0;
  padding: 0 0 env(safe-area-inset-bottom, 16px);
  width: 100%; max-width: 540px;
  transform: translateY(100%);
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 -8px 40px rgba(13,34,87,0.25);
  overflow: hidden;
}
#tsj-pwa-overlay.visible #tsj-install-sheet {
  transform: translateY(0);
}

.tsj-sheet-handle {
  width: 40px; height: 4px; border-radius: 2px;
  background: #dde; margin: 12px auto 0;
}

.tsj-sheet-header {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 20px 12px;
}
.tsj-sheet-icon {
  width: 60px; height: 60px; border-radius: 14px;
  background: linear-gradient(135deg, #0d2257 0%, #1a3a8f 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 30px; flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(13,34,87,0.3);
}
.tsj-sheet-info h3 {
  font-size: 17px; font-weight: 700; color: #0d2257; margin: 0 0 3px;
}
.tsj-sheet-info p {
  font-size: 13px; color: #666; margin: 0; line-height: 1.4;
}
.tsj-ratings {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; color: #f5a623; margin-top: 4px;
}

.tsj-features {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 8px; padding: 4px 20px 14px;
}
.tsj-feature {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-radius: 10px;
  background: #f0f4fb; font-size: 12px; color: #333; font-weight: 500;
}
.tsj-feature-icon { font-size: 18px; flex-shrink: 0; }

.tsj-sheet-actions {
  padding: 0 20px 20px;
  display: flex; flex-direction: column; gap: 10px;
}
.tsj-btn-install {
  display: block; width: 100%; padding: 15px;
  background: linear-gradient(135deg, #0d2257 0%, #1a3a8f 100%);
  color: #fff; border: none; border-radius: 14px;
  font-size: 16px; font-weight: 700; letter-spacing: 0.3px;
  cursor: pointer; text-align: center;
  box-shadow: 0 4px 16px rgba(13,34,87,0.35);
  transition: transform 0.15s, box-shadow 0.15s;
}
.tsj-btn-install:active {
  transform: scale(0.98); box-shadow: 0 2px 8px rgba(13,34,87,0.25);
}
.tsj-btn-later {
  display: block; width: 100%; padding: 12px;
  background: transparent; color: #888;
  border: none; border-radius: 14px;
  font-size: 14px; cursor: pointer; text-align: center;
}

/* ── iOS Guide ────────────────────────────────────────────────── */
#tsj-ios-guide {
  position: fixed; bottom: 0; left: 0; right: 0;
  z-index: 999991; padding: 0 16px env(safe-area-inset-bottom, 16px);
  transform: translateY(110%);
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
#tsj-ios-guide.visible { transform: translateY(0); }
#tsj-ios-inner {
  background: #fff; border-radius: 20px;
  padding: 20px; box-shadow: 0 -4px 30px rgba(0,0,0,0.2);
}
.tsj-ios-close {
  position: absolute; top: 14px; right: 18px;
  background: #eee; border: none; border-radius: 50%;
  width: 28px; height: 28px; cursor: pointer;
  font-size: 14px; display: flex; align-items: center; justify-content: center;
}
.tsj-ios-step {
  display: flex; align-items: flex-start; gap: 12px; margin: 10px 0;
}
.tsj-ios-num {
  width: 26px; height: 26px; border-radius: 50%;
  background: #0d2257; color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; flex-shrink: 0;
}
.tsj-ios-arrow {
  text-align: center; margin-top: 12px;
  animation: tsj-bounce 1s infinite;
}
@keyframes tsj-bounce {
  0%,100% { transform: translateY(0); }
  50% { transform: translateY(6px); }
}

/* ── Floating Install Button ──────────────────────────────────── */
#tsj-fab {
  position: fixed; bottom: calc(80px + env(safe-area-inset-bottom, 0px));
  right: 16px; z-index: 999980;
  background: linear-gradient(135deg, #f5a623 0%, #e8920f 100%);
  color: #fff; border: none; border-radius: 50px;
  padding: 12px 18px; font-size: 13px; font-weight: 700;
  display: flex; align-items: center; gap: 8px;
  box-shadow: 0 4px 20px rgba(245,166,35,0.5);
  cursor: pointer; transition: all 0.3s;
  transform: translateY(20px); opacity: 0;
  animation: tsj-fab-in 0.5s 5s forwards;
}
@keyframes tsj-fab-in {
  to { transform: translateY(0); opacity: 1; }
}
#tsj-fab:hover { transform: translateY(-2px) scale(1.03); }
#tsj-fab svg { width: 16px; height: 16px; fill: currentColor; }

/* ── Toast ────────────────────────────────────────────────────── */
#tsj-toast {
  position: fixed; bottom: calc(90px + env(safe-area-inset-bottom, 0px));
  left: 50%; transform: translateX(-50%) translateY(20px);
  background: rgba(13,34,87,0.95); color: #fff;
  padding: 10px 20px; border-radius: 50px;
  font-size: 13px; font-weight: 500;
  z-index: 999995; opacity: 0;
  transition: all 0.3s; pointer-events: none;
  white-space: nowrap; max-width: 90vw;
}
#tsj-toast.show {
  opacity: 1; transform: translateX(-50%) translateY(0);
}

/* ── Update Banner ────────────────────────────────────────────── */
#tsj-update-banner {
  position: fixed; top: 0; left: 0; right: 0; z-index: 999992;
  background: #0d2257; color: #fff;
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; font-size: 13px;
  transform: translateY(-100%); transition: transform 0.3s;
}
#tsj-update-banner.visible { transform: translateY(0); }
#tsj-update-reload {
  background: #f5a623; color: #0d2257;
  border: none; border-radius: 6px;
  padding: 6px 12px; font-weight: 700; font-size: 12px; cursor: pointer;
}

/* ── Splash Screen ────────────────────────────────────────────── */
#tsj-splash {
  position: fixed; inset: 0; z-index: 999999;
  background: linear-gradient(160deg, #0a1a4a 0%, #0d2257 50%, #1a3a8f 100%);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  transition: opacity 0.5s 0.3s, transform 0.5s 0.3s;
}
#tsj-splash.hide {
  opacity: 0; transform: scale(1.05); pointer-events: none;
}
#tsj-splash.gone { display: none; }
.tsj-splash-logo {
  width: 96px; height: 96px; border-radius: 22px;
  background: #fff; display: flex; align-items: center;
  justify-content: center; font-size: 48px;
  margin-bottom: 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  animation: tsj-logo-pulse 1.5s ease-in-out infinite alternate;
}
@keyframes tsj-logo-pulse {
  from { box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
  to   { box-shadow: 0 12px 48px rgba(245,166,35,0.4); }
}
.tsj-splash-name {
  color: #fff; font-size: 22px; font-weight: 800; letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.tsj-splash-tagline {
  color: rgba(255,255,255,0.65); font-size: 13px; letter-spacing: 0.3px;
}
.tsj-splash-loader {
  margin-top: 40px; width: 120px; height: 3px;
  background: rgba(255,255,255,0.15); border-radius: 2px; overflow: hidden;
}
.tsj-splash-bar {
  height: 100%; border-radius: 2px;
  background: linear-gradient(90deg, #f5a623, #ffcc70);
  animation: tsj-load 1.8s ease-in-out forwards;
}
@keyframes tsj-load {
  from { width: 0%; }
  to   { width: 100%; }
}

@media (prefers-color-scheme: dark) {
  #tsj-install-sheet, #tsj-ios-inner {
    background: #1a1a2e; color: #eee;
  }
  .tsj-feature { background: #252545; color: #ddd; }
  .tsj-sheet-info h3 { color: #eee; }
  .tsj-sheet-info p, .tsj-ratings { color: #aaa; }
}
    `;
    const style = document.createElement('style');
    style.id = 'tsj-pwa-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SPLASH SCREEN (standalone/TWA only or first launch)
  // ══════════════════════════════════════════════════════════════════════════
  function showSplash() {
    if (!isStandalone && !isTWA) return;
    const el = document.createElement('div');
    el.id = 'tsj-splash';
    el.innerHTML = `
      <div class="tsj-splash-logo">🏛️</div>
      <div class="tsj-splash-name">Top Sarkari Jobs</div>
      <div class="tsj-splash-tagline">India's No.1 Govt Jobs Platform</div>
      <div class="tsj-splash-loader"><div class="tsj-splash-bar"></div></div>
    `;
    document.body.insertBefore(el, document.body.firstChild);

    // Hide after 2s
    setTimeout(() => {
      el.classList.add('hide');
      setTimeout(() => {
        el.classList.add('gone');
      }, 600);
    }, 1800);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // INSTALL SHEET (Android / Desktop)
  // ══════════════════════════════════════════════════════════════════════════
  function buildInstallSheet() {
    const overlay = document.createElement('div');
    overlay.id = 'tsj-pwa-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Install Top Sarkari Jobs App');

    const platformLabel = isAndroid ? 'Android App' : isWindows ? 'Windows App' : isMac ? 'Mac App' : 'Desktop App';
    const platformHint  = isAndroid ? 'Works offline · No Play Store needed' : 'Install as desktop app · Works offline';

    overlay.innerHTML = `
      <div id="tsj-install-sheet">
        <div class="tsj-sheet-handle"></div>
        <div class="tsj-sheet-header">
          <div class="tsj-sheet-icon">🏛️</div>
          <div class="tsj-sheet-info">
            <h3>${CONFIG.appName}</h3>
            <p>${platformHint}</p>
            <div class="tsj-ratings">★★★★★ <span style="color:#888;font-size:11px">4.8 • Free • ${platformLabel}</span></div>
          </div>
        </div>
        <div class="tsj-features">
          <div class="tsj-feature"><span class="tsj-feature-icon">⚡</span>Instant Loading</div>
          <div class="tsj-feature"><span class="tsj-feature-icon">📡</span>Works Offline</div>
          <div class="tsj-feature"><span class="tsj-feature-icon">🔔</span>Job Alerts</div>
          <div class="tsj-feature"><span class="tsj-feature-icon">🏠</span>Home Screen</div>
        </div>
        <div class="tsj-sheet-actions">
          <button class="tsj-btn-install" id="tsj-install-btn">
            📲 Install Free App
          </button>
          <button class="tsj-btn-later" id="tsj-later-btn">Maybe later</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    // Close on overlay click
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) hideInstallSheet();
    });

    document.getElementById('tsj-later-btn').addEventListener('click', function () {
      dismiss('install_sheet');
      hideInstallSheet();
      showFAB(); // Show FAB as fallback
    });

    document.getElementById('tsj-install-btn').addEventListener('click', triggerInstall);

    return overlay;
  }

  function showInstallSheet() {
    if (isDismissed('install_sheet')) { showFAB(); return; }
    const overlay = document.getElementById('tsj-pwa-overlay') || buildInstallSheet();
    requestAnimationFrame(() => {
      overlay.classList.add('visible');
    });
  }

  function hideInstallSheet() {
    const overlay = document.getElementById('tsj-pwa-overlay');
    if (overlay) overlay.classList.remove('visible');
  }

  async function triggerInstall() {
    if (!deferredPrompt) {
      showToast('Use browser menu → "Add to Home Screen"', 4000);
      hideInstallSheet();
      return;
    }
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    deferredPrompt = null;
    hideInstallSheet();
    if (outcome === 'accepted') {
      store('installed', true);
      showToast('🎉 App installed successfully!', 3000);
      trackEvent('pwa_installed');
    } else {
      dismiss('install_sheet');
      showFAB();
      trackEvent('pwa_dismissed');
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // iOS INSTALL GUIDE
  // ══════════════════════════════════════════════════════════════════════════
  function buildIOSGuide() {
    const el = document.createElement('div');
    el.id = 'tsj-ios-guide';

    const shareIcon = isIPad
      ? '⬆️ Share (top right)'
      : '⬆️ Share button (bottom center)';

    el.innerHTML = `
      <div id="tsj-ios-inner" style="position:relative">
        <button class="tsj-ios-close" id="tsj-ios-close">✕</button>
        <div style="font-weight:700;font-size:16px;color:#0d2257;margin-bottom:12px">
          📲 Add to Home Screen
        </div>
        <div style="font-size:13px;color:#555;margin-bottom:14px">
          Install Top Sarkari Jobs as an iPhone app — no App Store needed!
        </div>
        <div class="tsj-ios-step">
          <div class="tsj-ios-num">1</div>
          <div style="font-size:13px;color:#333">Tap the <strong>${shareIcon}</strong> in Safari</div>
        </div>
        <div class="tsj-ios-step">
          <div class="tsj-ios-num">2</div>
          <div style="font-size:13px;color:#333">Scroll down and tap <strong>"Add to Home Screen"</strong></div>
        </div>
        <div class="tsj-ios-step">
          <div class="tsj-ios-num">3</div>
          <div style="font-size:13px;color:#333">Tap <strong>"Add"</strong> in the top right corner</div>
        </div>
        <div class="tsj-ios-arrow">☝️ Done! App added to your iPhone home screen</div>
      </div>
    `;

    document.body.appendChild(el);

    document.getElementById('tsj-ios-close').addEventListener('click', function () {
      dismiss('ios_guide');
      el.classList.remove('visible');
    });

    return el;
  }

  function showIOSGuide() {
    if (isDismissed('ios_guide')) return;
    const el = document.getElementById('tsj-ios-guide') || buildIOSGuide();
    requestAnimationFrame(() => el.classList.add('visible'));
    trackEvent('ios_guide_shown');
  }

  // ══════════════════════════════════════════════════════════════════════════
  // FLOATING ACTION BUTTON
  // ══════════════════════════════════════════════════════════════════════════
  function buildFAB() {
    if (document.getElementById('tsj-fab')) return;
    const fab = document.createElement('button');
    fab.id = 'tsj-fab';
    fab.setAttribute('aria-label', 'Install App');
    fab.innerHTML = `
      <svg viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
      Install App
    `;
    fab.addEventListener('click', function () {
      if (isIOS || isIPad) { showIOSGuide(); }
      else { showInstallSheet(); }
    });
    document.body.appendChild(fab);
  }

  function showFAB() {
    buildFAB();
    // Already shown via CSS animation
  }

  // ══════════════════════════════════════════════════════════════════════════
  // TOAST
  // ══════════════════════════════════════════════════════════════════════════
  function showToast(msg, duration = 3000) {
    let toast = document.getElementById('tsj-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'tsj-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove('show'), duration);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // UPDATE TOAST
  // ══════════════════════════════════════════════════════════════════════════
  function showUpdateToast() {
    let banner = document.getElementById('tsj-update-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'tsj-update-banner';
      banner.innerHTML = `
        <span>🔄 New version available!</span>
        <button id="tsj-update-reload">Update Now</button>
      `;
      document.body.appendChild(banner);
      document.getElementById('tsj-update-reload').addEventListener('click', () => {
        window.location.reload();
      });
    }
    requestAnimationFrame(() => banner.classList.add('visible'));
  }

  // ══════════════════════════════════════════════════════════════════════════
  // PUSH NOTIFICATIONS
  // ══════════════════════════════════════════════════════════════════════════
  async function requestPushPermission() {
    if (!('Notification' in window) || !('PushManager' in window)) return;
    if (Notification.permission === 'granted') return;
    if (Notification.permission === 'denied') return;

    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      subscribeToPush();
    }
  }

  async function subscribeToPush() {
    try {
      const reg = window._tsjSWReg || await navigator.serviceWorker.ready;
      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(CONFIG.vapidKey)
      });
      // Send subscription to your backend
      // await sendSubscriptionToServer(subscription);
      console.log('[PWA] Push subscription:', JSON.stringify(subscription));
    } catch (e) {
      console.warn('[PWA] Push subscription failed:', e.message);
    }
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ANALYTICS HELPER
  // ══════════════════════════════════════════════════════════════════════════
  function trackEvent(name, params = {}) {
    try {
      if (typeof gtag === 'function') {
        gtag('event', name, { event_category: 'PWA', ...params });
      }
    } catch {}
  }

  // ══════════════════════════════════════════════════════════════════════════
  // META TAGS FOR iOS
  // ══════════════════════════════════════════════════════════════════════════
  function injectIOSMeta() {
    const metas = [
      ['apple-mobile-web-app-capable',          'yes'],
      ['apple-mobile-web-app-status-bar-style', 'black-translucent'],
      ['apple-mobile-web-app-title',            CONFIG.appShortName],
      ['mobile-web-app-capable',                'yes'],
      ['application-name',                      CONFIG.appName],
      ['msapplication-TileColor',               CONFIG.themeColor],
      ['msapplication-TileImage',               '/icons/icon-144x144.png'],
      ['msapplication-tap-highlight',           'no'],
      ['format-detection',                      'telephone=no'],
    ];

    metas.forEach(([name, content]) => {
      if (!document.querySelector(`meta[name="${name}"]`)) {
        const m = document.createElement('meta');
        m.name = name;
        m.content = content;
        document.head.appendChild(m);
      }
    });

    // Apple touch icons
    const iconSizes = [57, 60, 72, 76, 114, 120, 144, 152, 180];
    iconSizes.forEach(size => {
      if (!document.querySelector(`link[rel="apple-touch-icon"][sizes="${size}x${size}"]`)) {
        const link = document.createElement('link');
        link.rel = 'apple-touch-icon';
        link.sizes = `${size}x${size}`;
        link.href = `/icons/apple-touch-icon-${size}x${size}.png`;
        document.head.appendChild(link);
      }
    });

    // Default apple-touch-icon
    if (!document.querySelector('link[rel="apple-touch-icon"]:not([sizes])')) {
      const link = document.createElement('link');
      link.rel = 'apple-touch-icon';
      link.href = '/icons/icon-180x180.png';
      document.head.appendChild(link);
    }

    // iOS Splash screens
    const splashScreens = [
      { media: '(device-width: 430px) and (device-height: 932px) and (-webkit-device-pixel-ratio: 3)', href: '/splash/splash-1290x2796.png' },
      { media: '(device-width: 393px) and (device-height: 852px) and (-webkit-device-pixel-ratio: 3)', href: '/splash/splash-1179x2556.png' },
      { media: '(device-width: 390px) and (device-height: 844px) and (-webkit-device-pixel-ratio: 3)', href: '/splash/splash-1170x2532.png' },
      { media: '(device-width: 375px) and (device-height: 812px) and (-webkit-device-pixel-ratio: 3)', href: '/splash/splash-1125x2436.png' },
      { media: '(device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 2)', href: '/splash/splash-828x1792.png' },
      { media: '(device-width: 375px) and (device-height: 667px) and (-webkit-device-pixel-ratio: 2)', href: '/splash/splash-750x1334.png' },
      { media: '(device-width: 768px) and (device-height: 1024px) and (-webkit-device-pixel-ratio: 2)', href: '/splash/splash-1536x2048.png' },
    ];

    splashScreens.forEach(({ media, href }) => {
      if (!document.querySelector(`link[rel="apple-touch-startup-image"][media="${media}"]`)) {
        const link = document.createElement('link');
        link.rel = 'apple-touch-startup-image';
        link.media = media;
        link.href = href;
        document.head.appendChild(link);
      }
    });

    // Theme color meta
    if (!document.querySelector('meta[name="theme-color"]')) {
      const m = document.createElement('meta');
      m.name = 'theme-color';
      m.content = CONFIG.themeColor;
      document.head.appendChild(m);
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ANDROID TWA DETECTION
  // ══════════════════════════════════════════════════════════════════════════
  function handleTWA() {
    if (isTWA) {
      document.documentElement.classList.add('tsj-twa');
      // In TWA mode, hide browser-specific UI
      store('is_twa', true);
      trackEvent('twa_launch');
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // MAIN INIT
  // ══════════════════════════════════════════════════════════════════════════
  function init() {
    // Already installed as app — don't show prompts
    if (isStandalone) {
      showSplash();
      handleTWA();
      // Request push permissions after brief delay in standalone
      setTimeout(requestPushPermission, 5000);
      return;
    }

    injectStyles();
    injectIOSMeta();

    // Capture beforeinstallprompt (Android/Desktop Chrome/Edge)
    window.addEventListener('beforeinstallprompt', function (e) {
      e.preventDefault();
      deferredPrompt = e;
      trackEvent('pwa_prompt_available', { platform: isAndroid ? 'android' : 'desktop' });

      setTimeout(function () {
        if (!isDismissed('install_sheet') && !retrieve('installed')) {
          showInstallSheet();
          trackEvent('pwa_sheet_shown');
        } else {
          showFAB();
        }
      }, CONFIG.installDelay);
    });

    // iOS: show guide in Safari (not Chrome/Firefox on iOS)
    if ((isIOS || isIPad) && isSafari) {
      setTimeout(function () {
        if (!isDismissed('ios_guide') && !retrieve('installed')) {
          showIOSGuide();
          trackEvent('ios_guide_triggered');
        } else {
          showFAB();
        }
      }, CONFIG.iosBannerDelay);
    }

    // Track install
    window.addEventListener('appinstalled', function () {
      store('installed', true);
      deferredPrompt = null;
      hideInstallSheet();
      showToast('🎉 App installed! Open from your home screen.', 4000);
      trackEvent('pwa_app_installed');
    });

    // Always show FAB after delay if no prompt appeared (fallback)
    setTimeout(function () {
      if (!deferredPrompt && !(isIOS || isIPad)) {
        // Desktop: show FAB as info/guide
        buildFAB();
      }
    }, 8000);
  }

  // ── Public API ─────────────────────────────────────────────────────────────
  window.TSJ_PWA = {
    showInstall:     showInstallSheet,
    showIOSGuide:    showIOSGuide,
    requestPush:     requestPushPermission,
    showToast:       showToast,
    isStandalone:    isStandalone,
    isAndroid:       isAndroid,
    isIOS:           isIOS,
    isTWA:           isTWA,
  };

  // ── Boot ───────────────────────────────────────────────────────────────────
  registerServiceWorker();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
