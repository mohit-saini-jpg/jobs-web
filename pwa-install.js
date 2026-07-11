/**
 * TOP SARKARI JOBS — PWA Install System v6.0
 * iOS Fix: touchstart + pointer-events + no overlay black bug
 * FAB: auto-fold to left after 8s
 */
(function () {
  'use strict';

  var ua          = navigator.userAgent;
  var isIOS       = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
  var isIPad      = /iPad/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var isSafari    = /Safari/.test(ua) && !/Chrome/.test(ua) && !/CriOS/.test(ua);
  var isAndroid   = /Android/i.test(ua);
  var isStandalone = window.navigator.standalone === true ||
                     window.matchMedia('(display-mode: standalone)').matches;

  var SK = 'tsj6_'; // storage key prefix — v6 resets old dismissals
  var deferredPrompt = null;
  var fabEl = null;
  var isFolded = false;
  var foldTimer = null;

  /* ── Storage ── */
  function save(k, v)  { try { localStorage.setItem(SK+k, JSON.stringify(v)); } catch(e){} }
  function load(k)     { try { return JSON.parse(localStorage.getItem(SK+k)); } catch(e){ return null; } }
  function wasDismissed(k) {
    var t = load(k+'_at');
    return t && (Date.now() - t) < 86400000; // 1 day
  }
  function setDismissed(k) { save(k+'_at', Date.now()); }

  /* ── iOS tap fix: use touchend for reliable iOS clicks ── */
  function onTap(el, fn) {
    var moved = false;
    el.addEventListener('touchstart', function(e){ moved = false; }, {passive:true});
    el.addEventListener('touchmove',  function(e){ moved = true;  }, {passive:true});
    el.addEventListener('touchend',   function(e){
      if (!moved) { e.preventDefault(); fn(e); }
    });
    el.addEventListener('click', fn); // desktop fallback
  }

  /* ══════════════════════════════════════════
     STYLES
  ══════════════════════════════════════════ */
  function injectStyles() {
    var css = [
      /* FAB */
      '#tsj-fab{position:fixed;bottom:calc(70px + env(safe-area-inset-bottom,0px));left:50%;',
      'transform:translateX(-50%) translateY(120px);z-index:2147483647;',
      'background:#f5c800;color:#111;border:none;border-radius:50px;padding:0;',
      'display:flex;align-items:center;overflow:hidden;white-space:nowrap;',
      'box-shadow:0 4px 20px rgba(0,0,0,0.3);cursor:pointer;',
      'opacity:0;max-width:92vw;',
      'transition:transform .5s cubic-bezier(.34,1.2,.64,1),left .5s,opacity .5s,border-radius .4s;',
      '-webkit-tap-highlight-color:transparent;}',

      '#tsj-fab.show{transform:translateX(-50%) translateY(0);opacity:1;}',

      '#tsj-fab.folded{left:0!important;transform:translateX(0) translateY(0)!important;',
      'border-radius:0 50px 50px 0!important;}',
      '#tsj-fab.folded .tsj-fab-txt{display:none;}',
      '#tsj-fab.folded .tsj-fab-ico{width:46px;height:46px;}',

      '.tsj-fab-txt{display:flex;flex-direction:column;padding:8px 14px 8px 16px;line-height:1.3;}',
      '.tsj-fab-top{font-size:9px;font-weight:700;color:#111;}',
      '.tsj-fab-main{font-size:13px;font-weight:900;color:#111;}',
      '.tsj-fab-ico{background:#111;color:#f5c800;width:46px;min-height:46px;',
      'display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;}',

      /* iOS Guide */
      '#tsj-ios{position:fixed;bottom:0;left:0;right:0;z-index:2147483647;',
      'background:#fff;border-radius:24px 24px 0 0;',
      'padding:0 0 env(safe-area-inset-bottom,12px);',
      'box-shadow:0 -6px 32px rgba(13,34,87,0.25);',
      'transform:translateY(110%);transition:transform .4s cubic-bezier(.34,1.1,.64,1);',
      'pointer-events:all;-webkit-overflow-scrolling:touch;}',
      '#tsj-ios.show{transform:translateY(0);}',

      /* Android sheet */
      '#tsj-ov{position:fixed;inset:0;z-index:2147483640;',
      'background:rgba(0,0,0,.55);opacity:0;pointer-events:none;transition:opacity .3s;}',
      '#tsj-ov.show{opacity:1;pointer-events:all;}',
      '#tsj-sheet{position:fixed;bottom:0;left:0;right:0;z-index:2147483641;',
      'background:#fff;border-radius:24px 24px 0 0;',
      'padding:0 0 env(safe-area-inset-bottom,16px);',
      'transform:translateY(100%);transition:transform .4s cubic-bezier(.34,1.56,.64,1);',
      'box-shadow:0 -8px 40px rgba(13,34,87,0.25);}',
      '#tsj-sheet.show{transform:translateY(0);}',

      /* Shared */
      '.tsj-handle{width:40px;height:4px;border-radius:2px;background:#dde;margin:12px auto 0;}',
      '.tsj-hdr{display:flex;align-items:center;gap:14px;padding:14px 20px 10px;',
      'border-bottom:1px solid #f0f4f8;}',
      '.tsj-app-ico{width:58px;height:58px;border-radius:14px;',
      'background:linear-gradient(135deg,#0d2257,#1a3a8f);',
      'display:flex;align-items:center;justify-content:center;font-size:28px;flex-shrink:0;}',
      '.tsj-app-name{font-size:16px;font-weight:700;color:#0d2257;}',
      '.tsj-app-sub{font-size:12px;color:#595959;margin-top:2px;}',
      '.tsj-stars{font-size:11px;color:#b45309;margin-top:2px;}',
      '.tsj-close{width:30px;height:30px;border-radius:50%;background:#f0f0f0;',
      'border:none;font-size:14px;color:#555;cursor:pointer;margin-left:auto;flex-shrink:0;',
      'display:flex;align-items:center;justify-content:center;',
      '-webkit-tap-highlight-color:transparent;}',
      '.tsj-feats{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px 20px;}',
      '.tsj-feat{display:flex;align-items:center;gap:8px;padding:10px 12px;',
      'border-radius:10px;background:#f0f4fb;font-size:12px;font-weight:500;color:#333;}',
      '.tsj-steps{padding:0 20px 12px;}',
      '.tsj-step-lbl{font-size:11px;font-weight:700;color:#0d2257;',
      'text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px;}',
      '.tsj-step{display:flex;align-items:center;gap:12px;padding:10px 14px;',
      'background:#f7f9ff;border-radius:12px;border:1px solid #e8eef8;margin-bottom:8px;}',
      '.tsj-step-n{width:26px;height:26px;border-radius:50%;background:#0d2257;color:#fff;',
      'display:flex;align-items:center;justify-content:center;font-size:12px;',
      'font-weight:800;flex-shrink:0;}',
      '.tsj-step-t{font-size:13px;color:#333;line-height:1.4;}',
      '.tsj-step-t b{color:#0d2257;}',
      '.tsj-actions{padding:4px 20px 16px;display:flex;flex-direction:column;gap:8px;}',
      '.tsj-btn-primary{display:block;width:100%;padding:15px;',
      'background:linear-gradient(135deg,#0d2257,#1a3a8f);color:#fff;',
      'border:none;border-radius:14px;font-size:15px;font-weight:700;cursor:pointer;',
      'box-shadow:0 4px 14px rgba(13,34,87,0.3);',
      '-webkit-tap-highlight-color:transparent;text-align:center;}',
      '.tsj-btn-later{display:block;width:100%;padding:11px;background:transparent;',
      'color:#666;border:none;font-size:13px;cursor:pointer;',
      '-webkit-tap-highlight-color:transparent;}',
    ].join('');

    var s = document.createElement('style');
    s.id = 'tsj-pwa-css';
    s.textContent = css;
    document.head.appendChild(s);
  }

  /* ══════════════════════════════════════════
     iOS GUIDE (no overlay — prevents black fade)
  ══════════════════════════════════════════ */
  function buildIOSGuide() {
    var el = document.createElement('div');
    el.id = 'tsj-ios';
    el.innerHTML = [
      '<div class="tsj-handle"></div>',
      '<div class="tsj-hdr">',
        '<div class="tsj-app-ico">🏛️</div>',
        '<div>',
          '<div class="tsj-app-name">Top Sarkari Jobs</div>',
          '<div class="tsj-app-sub">Free App • No App Store needed!</div>',
          '<div class="tsj-stars">★★★★★ 4.8 Free</div>',
        '</div>',
        '<button class="tsj-close" id="tsj-ios-x">✕</button>',
      '</div>',
      '<div class="tsj-steps">',
        '<div class="tsj-step-lbl">📲 3 Steps mein install karo:</div>',
        '<div class="tsj-step"><div class="tsj-step-n">1</div>',
          '<div class="tsj-step-t">Safari mein neeche <b>Share ⬆️</b> tap karo</div></div>',
        '<div class="tsj-step"><div class="tsj-step-n">2</div>',
          '<div class="tsj-step-t"><b>"Add to Home Screen"</b> tap karo</div></div>',
        '<div class="tsj-step"><div class="tsj-step-n">3</div>',
          '<div class="tsj-step-t">Upar right mein <b>"Add"</b> tap karo ✅</div></div>',
      '</div>',
      '<div class="tsj-actions">',
        '<button class="tsj-btn-primary" id="tsj-ios-ok">⬆️ Samajh gaya, Install karta hun</button>',
        '<button class="tsj-btn-later" id="tsj-ios-later">Baad mein</button>',
      '</div>',
    ].join('');

    document.body.appendChild(el);

    function closeIOS() {
      el.classList.remove('show');
      setDismissed('ios');
    }

    onTap(document.getElementById('tsj-ios-x'),     closeIOS);
    onTap(document.getElementById('tsj-ios-later'), closeIOS);
    onTap(document.getElementById('tsj-ios-ok'), function() {
      var btn = document.getElementById('tsj-ios-ok');
      btn.textContent = '⬆️ Ab neeche Share button tap karo';
      btn.style.background = 'linear-gradient(135deg,#1b5e20,#388e3c)';
      setTimeout(closeIOS, 2500);
    });

    return el;
  }

  function showIOSGuide() {
    if (wasDismissed('ios') || isStandalone) return;
    var el = document.getElementById('tsj-ios') || buildIOSGuide();
    el.style.display = '';
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        el.classList.add('show');
      });
    });
  }

  /* ══════════════════════════════════════════
     ANDROID / DESKTOP SHEET
  ══════════════════════════════════════════ */
  function buildSheet() {
    var ov = document.createElement('div');
    ov.id = 'tsj-ov';
    document.body.appendChild(ov);

    var sh = document.createElement('div');
    sh.id = 'tsj-sheet';
    sh.innerHTML = [
      '<div class="tsj-handle"></div>',
      '<div class="tsj-hdr">',
        '<div class="tsj-app-ico">🏛️</div>',
        '<div>',
          '<div class="tsj-app-name">Top Sarkari Jobs</div>',
          '<div class="tsj-app-sub">Works offline • No Play Store needed</div>',
          '<div class="tsj-stars">★★★★★ 4.8 • Free • '+(isAndroid?'Android':'Desktop')+' App</div>',
        '</div>',
        '<button class="tsj-close" id="tsj-sh-x">✕</button>',
      '</div>',
      '<div class="tsj-feats">',
        '<div class="tsj-feat">⚡ Instant Loading</div>',
        '<div class="tsj-feat">📡 Works Offline</div>',
        '<div class="tsj-feat">🔔 Job Alerts</div>',
        '<div class="tsj-feat">🏠 Home Screen</div>',
      '</div>',
      '<div class="tsj-actions">',
        '<button class="tsj-btn-primary" id="tsj-sh-install">📲 Install Free App</button>',
        '<button class="tsj-btn-later" id="tsj-sh-later">Maybe later</button>',
      '</div>',
    ].join('');
    document.body.appendChild(sh);

    function closeSheet() {
      sh.classList.remove('show');
      ov.classList.remove('show');
      setDismissed('sheet');
    }

    onTap(ov, closeSheet);
    onTap(document.getElementById('tsj-sh-x'),     closeSheet);
    onTap(document.getElementById('tsj-sh-later'), function(){ closeSheet(); showFAB(); });
    onTap(document.getElementById('tsj-sh-install'), function() {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function(r) {
          deferredPrompt = null;
          closeSheet();
          if (r.outcome === 'accepted') {
            save('installed', 1);
            removeFAB();
          } else {
            showFAB();
          }
        });
      } else {
        closeSheet();
        showFAB();
      }
    });
  }

  function showSheet() {
    if (wasDismissed('sheet') || load('installed') || isStandalone) { showFAB(); return; }
    if (!document.getElementById('tsj-sh-install')) buildSheet();
    requestAnimationFrame(function() {
      document.getElementById('tsj-ov').classList.add('show');
      document.getElementById('tsj-sheet').classList.add('show');
    });
  }

  /* ══════════════════════════════════════════
     FAB — Floating Button with auto-fold
  ══════════════════════════════════════════ */
  function buildFAB() {
    if (document.getElementById('tsj-fab')) return;
    fabEl = document.createElement('button');
    fabEl.id = 'tsj-fab';
    fabEl.setAttribute('aria-label', 'Install App');
    fabEl.innerHTML = [
      '<div class="tsj-fab-txt">',
        '<span class="tsj-fab-top">Govt: \u0928\u094c\u0915\u0930\u0940 \u0938\u093f\u0930\u094d\u092b \u090f\u0915 \u0915\u094d\u0932\u093f\u0915 \u0926\u0942\u0930</span>',
        '<span class="tsj-fab-main">\u2b07 INSTALL App</span>',
      '</div>',
      '<div class="tsj-fab-ico">\u2b07</div>',
    ].join('');

    onTap(fabEl, function() {
      if (isFolded) {
        // Expand
        isFolded = false;
        fabEl.classList.remove('folded');
        fabEl.style.left = '50%';
        clearTimeout(foldTimer);
        foldTimer = setTimeout(foldFAB, 8000);
      } else {
        // Open install
        clearTimeout(foldTimer);
        if (isIOS || isIPad) { showIOSGuide(); }
        else { showSheet(); }
      }
    });

    document.body.appendChild(fabEl);

    // Show after 5s, fold after 8s
    setTimeout(function() {
      fabEl.classList.add('show');
      foldTimer = setTimeout(foldFAB, 8000);
    }, 5000);
  }

  function foldFAB() {
    if (!fabEl) return;
    isFolded = true;
    fabEl.style.left = '0';
    fabEl.classList.add('folded');
  }

  function showFAB() { buildFAB(); }

  function removeFAB() {
    if (fabEl) { fabEl.remove(); fabEl = null; }
  }

  /* ══════════════════════════════════════════
     SERVICE WORKER
  ══════════════════════════════════════════ */
  function registerSW() {
    if (!('serviceWorker' in navigator)) return;
    window.addEventListener('load', function() {
      navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' }).then(function(reg) {
        reg.addEventListener('updatefound', function() {
          // FIXED: Removed SKIP_WAITING postMessage.
          // Auto-activating new SW caused page reload/refresh loop.
          // New SW activates naturally when all tabs are closed/reopened.
        });
        setInterval(function(){ reg.update(); }, 30*60*1000);
        window._tsjSWReg = reg;
      }).catch(function(){});

      // AUDIT FIX: Removed auto-reload on controllerchange.
      // Old code caused page to refresh every time SW updated — bad UX.
      // SW update happens silently; user gets new version on next natural navigation.
    });
  }

  /* ══════════════════════════════════════════
     iOS META TAGS
  ══════════════════════════════════════════ */
  function injectIOSMeta() {
    var metas = [
      ['apple-mobile-web-app-capable','yes'],
      ['apple-mobile-web-app-status-bar-style','black-translucent'],
      ['apple-mobile-web-app-title','TopSarkariJobs'],
      ['mobile-web-app-capable','yes'],
    ];
    metas.forEach(function(m) {
      if (!document.querySelector('meta[name="'+m[0]+'"]')) {
        var el = document.createElement('meta');
        el.name = m[0]; el.content = m[1];
        document.head.appendChild(el);
      }
    });
  }

  /* ══════════════════════════════════════════
     INIT
  ══════════════════════════════════════════ */
  function init() {
    if (isStandalone) return; // already installed, do nothing

    injectStyles();
    injectIOSMeta();
    registerSW();

    // Android / Desktop: capture install prompt
    window.addEventListener('beforeinstallprompt', function(e) {
      e.preventDefault();
      deferredPrompt = e;
      setTimeout(function() {
        if (!wasDismissed('sheet') && !load('installed')) {
          showSheet();
        } else {
          showFAB();
        }
      }, 5000);
    });

    // iOS
    if (isIOS || isIPad) {
      buildFAB(); // FAB shows itself after 5s
      setTimeout(function() {
        if (!wasDismissed('ios') && !load('installed')) {
          showIOSGuide();
        }
      }, 5000);
    }

    // Desktop fallback (no beforeinstallprompt)
    setTimeout(function() {
      if (!deferredPrompt && !isIOS && !isIPad) {
        buildFAB();
      }
    }, 9000);

    window.addEventListener('appinstalled', function() {
      save('installed', 1);
      removeFAB();
      deferredPrompt = null;
    });
  }

  // Public API
  window.TSJ_PWA = { showIOSGuide: showIOSGuide, showSheet: showSheet };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
