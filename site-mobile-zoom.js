/* Site-wide mobile zoom control -- a small floating +/- control on phones
   so users can widen/narrow the CSS layout viewport to their own liking,
   the same underlying mechanism tools-mobile-zoom.js already gives tool
   pages. Unlike that script, this one does NOT force a wider viewport on
   load -- the site's normal default (width=device-width from the page's
   own <meta viewport> tag) stays exactly as-is until the user actually
   taps a button. Desktop/tablet (>=560px real width) is left alone.

   Skips itself entirely on tool pages, which already load
   tools-mobile-zoom.js -- having both would fight over the same
   <meta name="viewport"> tag and show two conflicting zoom controls. */
(function () {
  if (document.querySelector('script[src^="/tools-mobile-zoom.js"]')) return;

  var STEP = 60;
  var ZOOM_IN_MAX = 150;   // how far below native width layout can shrink (bigger text/content)
  var ZOOM_OUT_MAX = 240;  // how far above native width layout can grow (smaller text, more on screen)
  var meta = null;
  var active = false;
  var currentWidth = null;

  function isPhone() {
    return window.innerWidth < 560;
  }

  function getMeta() {
    if (meta) return meta;
    meta = document.querySelector('meta[name="viewport"]');
    if (!meta) {
      meta = document.createElement('meta');
      meta.setAttribute('name', 'viewport');
      document.head.appendChild(meta);
    }
    return meta;
  }

  function nativeWidth() {
    return window.screen.width || window.innerWidth;
  }

  function applyWidth() {
    getMeta().setAttribute(
      'content',
      'width=' + Math.round(currentWidth) + ',user-scalable=yes,maximum-scale=5'
    );
  }

  function pct() {
    return Math.round((nativeWidth() / currentWidth) * 100);
  }

  function updateLabel() {
    var lbl = document.getElementById('tsj-szoom-val');
    if (lbl) lbl.textContent = active ? pct() + '%' : '100%';
  }

  function buildUI() {
    if (document.getElementById('tsj-szoom-ctrl')) return;
    var style = document.createElement('style');
    style.textContent =
      /* Right side, stacked ABOVE the whole existing right-edge column
         (WhatsApp .wa-float at bottom:~70-116px, then #tsj-bell at
         bottom:~126-174px) with a safe gap. Also clears the install-app
         FAB on the left, which folds to bottom:var(--tsj-nav-h)+82+38px
         tall -- so this is pinned to the same --tsj-nav-h var plus a
         16px buffer past that, staying correctly clear of it even if
         the real nav-bar height ever changes. Both formulas include
         env(safe-area-inset-bottom) so the gap holds on notched devices
         too (it cancels out either way). */
      '#tsj-szoom-ctrl{position:fixed;right:14px;' +
      'bottom:calc(var(--tsj-nav-h,59px) + 136px + env(safe-area-inset-bottom,0px));z-index:9997;' +
      'display:flex;align-items:center;gap:1px;background:#111827;' +
      'border-radius:999px;padding:4px;box-shadow:0 4px 14px rgba(0,0,0,.25);' +
      'font-family:inherit}' +
      '#tsj-szoom-ctrl button{width:26px;height:26px;border:none;border-radius:50%;' +
      'background:#1f2937;color:#fff;font-size:.9rem;font-weight:700;' +
      'line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;' +
      '-webkit-tap-highlight-color:transparent}' +
      '#tsj-szoom-ctrl button:active{background:#345de6}' +
      '#tsj-szoom-val{color:#fff;font-size:.58rem;font-weight:700;min-width:28px;text-align:center}';
    document.head.appendChild(style);

    var wrap = document.createElement('div');
    wrap.id = 'tsj-szoom-ctrl';
    wrap.innerHTML =
      '<button type="button" data-d="1" aria-label="Zoom out (dekhein zyada content)">−</button>' +
      '<span id="tsj-szoom-val">100%</span>' +
      '<button type="button" data-d="-1" aria-label="Zoom in (bada text)">+</button>';
    document.body.appendChild(wrap);

    wrap.addEventListener('click', function (e) {
      var btn = e.target.closest('button');
      if (!btn) return;
      if (!active) {
        active = true;
        currentWidth = nativeWidth();
      }
      var dir = parseInt(btn.getAttribute('data-d'), 10);
      var minW = Math.max(240, nativeWidth() - ZOOM_IN_MAX);
      var maxW = nativeWidth() + ZOOM_OUT_MAX;
      currentWidth = Math.max(minW, Math.min(maxW, currentWidth + dir * STEP));
      applyWidth();
      updateLabel();
    });
  }

  function init() {
    if (!isPhone()) return;
    if (document.body) buildUI();
    else document.addEventListener('DOMContentLoaded', buildUI);
  }

  init();
})();
