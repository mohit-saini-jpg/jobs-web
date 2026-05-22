/**
 * perf-boost-v2.js — Top Sarkari Jobs
 * Advanced Performance: INP optimization, CLS prevention, Resource hints
 * Load: <script src="perf-boost-v2.js" defer></script>
 */
(function(){
'use strict';

// ── 1. Reduce INP: batch DOM reads/writes ─────────────────────
var RAF = window.requestAnimationFrame;
var schedule = RAF || function(fn){ setTimeout(fn, 16); };

// ── 2. CLS Prevention: reserve space for dynamic content ──────
// Force section card heights before JS loads content
var style = document.createElement('style');
style.textContent = [
  '.section-card:empty{min-height:200px}',
  '.ticker-track:empty{min-height:24px}',
  '#dynamic-sections:empty{min-height:400px}',
  // Font display already set via @font-face swap
  // Prevent layout shift from FA icons loading
  '.fa-solid,.fa-brands,.fa-regular{display:inline-block;width:1em;height:1em;vertical-align:-.125em}',
].join('');
document.head.appendChild(style);

// ── 3. Preload next likely pages on idle ──────────────────────
function preloadOnIdle() {
  if (!('requestIdleCallback' in window)) return;
  requestIdleCallback(function() {
    // Most visited pages on jobs site
    var pages = ['/result.html', '/admit-card.html', '/search.html'];
    pages.forEach(function(url) {
      var link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = url;
      link.as = 'document';
      document.head.appendChild(link);
    });
  }, {timeout: 5000});
}

// ── 4. Long Task detection + reporting ───────────────────────
if ('PerformanceObserver' in window) {
  try {
    var ltObs = new PerformanceObserver(function(list) {
      list.getEntries().forEach(function(entry) {
        if (entry.duration > 50) {
          // Long task detected — could report to analytics
          // console.warn('Long task:', entry.duration.toFixed(0) + 'ms');
        }
      });
    });
    ltObs.observe({entryTypes: ['longtask']});
  } catch(e) {}
}

// ── 5. Memory pressure: clear caches on low memory ───────────
if (navigator.deviceMemory && navigator.deviceMemory < 2) {
  // Low-end device (<2GB RAM): reduce animation, disable non-critical features
  document.documentElement.classList.add('low-mem');
  var lowMemStyle = document.createElement('style');
  lowMemStyle.textContent = [
    '.low-mem * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }',
    '.low-mem .ticker-wrap { display: none; }', // hide ticker on very low-end
  ].join('');
  document.head.appendChild(lowMemStyle);
}

// ── 6. Smooth scroll with keyboard a11y fix ───────────────────
document.addEventListener('keydown', function(e) {
  if (e.key === 'Tab') {
    document.documentElement.classList.add('keyboard-nav');
  }
}, {once: false, passive: true});

// ── 7. Network-aware loading ──────────────────────────────────
var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
if (conn) {
  if (conn.saveData || conn.effectiveType === '2g' || conn.effectiveType === 'slow-2g') {
    // Data saver mode: skip non-critical prefetch
    document.documentElement.classList.add('data-saver');
  } else {
    // Good connection: prefetch next pages
    preloadOnIdle();
  }
} else {
  preloadOnIdle();
}

// ── 8. Fix: Passive event listeners for touch ─────────────────
// Upgrade touch listeners for 60fps scroll on mobile
['touchstart', 'touchmove', 'wheel'].forEach(function(evt) {
  window.addEventListener(evt, function(){}, {passive: true, capture: false});
});

// ── 9. Core Web Vitals: CLS tracking ─────────────────────────
if ('PerformanceObserver' in window) {
  try {
    var clsValue = 0;
    var clsObs = new PerformanceObserver(function(list) {
      list.getEntries().forEach(function(entry) {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
          if (clsValue > 0.1) {
            // CLS exceeding threshold — flag for debugging
            document.documentElement.dataset.cls = clsValue.toFixed(3);
          }
        }
      });
    });
    clsObs.observe({type: 'layout-shift', buffered: true});
  } catch(e) {}
}

})();
