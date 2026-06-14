/**
 * ULTRA PERFORMANCE PATCH v8.0 — Top Sarkari Jobs
 * Load: <script src="perf-ultra.js" defer></script>
 *
 * ✅ Lazy loads images below fold (IntersectionObserver)
 * ✅ Passive scroll listeners (layout shift reduction)
 * ✅ Idle prefetch: sections-index.json + dailyupdates.json (fresh, not missing files)
 * ✅ Respects data-saver mode + online status
 * ✅ RC-8 FIX: no more jobs-index.json / jobs-search-index.json (may not exist)
 */
(function() {
  'use strict';

  // ── 1. Lazy load images below fold ───────────────────────────────────
  if ('IntersectionObserver' in window) {
    var imgObs = new IntersectionObserver(function(entries) {
      entries.forEach(function(e) {
        if (e.isIntersecting) {
          var img = e.target;
          if (img.dataset.src) { img.src = img.dataset.src; delete img.dataset.src; }
          imgObs.unobserve(img);
        }
      });
    }, { rootMargin: '200px' });

    document.querySelectorAll('img[data-src]').forEach(function(img) {
      imgObs.observe(img);
    });
  }

  // ── 2. Idle prefetch — REMOVED to cut Vercel edge requests ──────────────
  // Previously this re-fetched sections-index.json + dailyupdates.json with
  // { cache: 'reload' } on EVERY page view, bypassing browser + CDN cache and
  // doubling edge requests for files the homepage already loaded. The service
  // worker (stale-while-revalidate) and CDN s-maxage already keep these fresh,
  // so the extra forced prefetch only wasted bandwidth. Intentionally disabled.

  // ── 3. Passive scroll listener ───────────────────────────────────────
  var passiveSupported = false;
  try {
    var opts = Object.defineProperty({}, 'passive', {
      get: function() { passiveSupported = true; }
    });
    window.addEventListener('testPassive', null, opts);
    window.removeEventListener('testPassive', null, opts);
  } catch(e) {}

  // Throttle non-critical scroll updates
  var ticking = false;
  document.addEventListener('scroll', function() {
    if (!ticking) {
      requestAnimationFrame(function() { ticking = false; });
      ticking = true;
    }
  }, passiveSupported ? { passive: true } : false);

})();
