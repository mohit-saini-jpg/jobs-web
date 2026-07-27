/* Forces a wider CSS layout viewport (650-800px, scaled by device width)
   on phones for every tools/*.html page, so the tool's normal desktop/
   tablet layout renders instead of its narrow-phone fallback -- plus a
   floating +/- zoom control so users can compensate, since forcing a
   wider viewport shrinks the rendered text/tap-target size by default
   (the browser scales the whole page down to fit the real screen).
   Desktop/tablet (real width >= 560px -- the smallest tablets start at
   768px, so this comfortably covers every phone, including large ones
   like Pro Max, without ever catching a tablet) is left completely alone. */
(function () {
  var MIN_W = 650, MAX_W = 800;
  var STEP = 60;
  var meta = null;

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

  function defaultWidth() {
    // Proportional within [MIN_W, MAX_W] by real screen width, so small
    // phones don't get shrunk as aggressively as large ones.
    var real = window.screen.width || window.innerWidth;
    var w = Math.round(MIN_W + (real - 360) * 1.6);
    return Math.max(MIN_W, Math.min(MAX_W, w));
  }

  var currentWidth = defaultWidth();
  // Zoom "in" goes toward the real device width (100% native size, no
  // forced shrink); zoom "out" goes wider than the default max (see more
  // at once, smaller text).
  var zoomMinWidth = window.screen.width || window.innerWidth;
  var zoomMaxWidth = MAX_W + STEP * 3;

  function applyWidth() {
    // No initial-scale here -- it directly conflicts with width=NNN (tells
    // the browser to both "stay at 100% zoom" AND "layout viewport is
    // NNN px", which Chromium resolves by ignoring the zoom-out entirely,
    // just overflowing instead of shrinking to fit). Omitting it lets the
    // browser auto-compute the correct fit-to-screen scale.
    getMeta().setAttribute(
      'content',
      'width=' + Math.round(currentWidth) + ',user-scalable=yes,maximum-scale=5'
    );
  }

  function pct() {
    // 100% = real device width (no shrink), lower % = more zoomed out.
    return Math.round((zoomMinWidth / currentWidth) * 100);
  }

  function updateLabel() {
    var lbl = document.getElementById('tsj-zoom-val');
    if (lbl) lbl.textContent = pct() + '%';
  }

  function buildUI() {
    if (document.getElementById('tsj-zoom-ctrl')) return;
    var style = document.createElement('style');
    style.textContent =
      '#tsj-zoom-ctrl{position:fixed;right:20px;bottom:20px;z-index:99998;' +
      'display:flex;align-items:center;gap:2px;background:#111827;' +
      'border-radius:999px;padding:6px;box-shadow:0 4px 16px rgba(0,0,0,.28);' +
      'font-family:inherit}' +
      '#tsj-zoom-ctrl button{width:34px;height:34px;border:none;border-radius:50%;' +
      'background:#1f2937;color:#fff;font-size:1.15rem;font-weight:700;' +
      'line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center}' +
      '#tsj-zoom-ctrl button:active{background:#345de6}' +
      '#tsj-zoom-val{color:#fff;font-size:.72rem;font-weight:700;min-width:38px;text-align:center}';
    document.head.appendChild(style);

    var wrap = document.createElement('div');
    wrap.id = 'tsj-zoom-ctrl';
    wrap.innerHTML =
      '<button type="button" data-d="1" aria-label="Zoom out (dekhein zyada content)">−</button>' +
      '<span id="tsj-zoom-val"></span>' +
      '<button type="button" data-d="-1" aria-label="Zoom in (bada text)">+</button>';
    document.body.appendChild(wrap);

    wrap.addEventListener('click', function (e) {
      var btn = e.target.closest('button');
      if (!btn) return;
      var dir = parseInt(btn.getAttribute('data-d'), 10);
      currentWidth = Math.max(zoomMinWidth, Math.min(zoomMaxWidth, currentWidth + dir * STEP));
      applyWidth();
      updateLabel();
    });

    updateLabel();
  }

  function init() {
    if (!isPhone()) return;
    applyWidth();
    if (document.body) buildUI();
    else document.addEventListener('DOMContentLoaded', buildUI);
  }

  init();
})();
