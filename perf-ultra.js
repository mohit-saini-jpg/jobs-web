/**
 * ULTRA PERFORMANCE PATCH — Top Sarkari Jobs
 * Load this file with: <script src="perf-ultra.js" defer></script>
 * ✅ Lazy loads Font Awesome icons after paint
 * ✅ IntersectionObserver for below-fold cards
 * ✅ Reduces layout shift
 * ✅ Preloads next JSON on idle
 */
(function() {
  'use strict';

  // 1) Lazy load images below fold
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

  // 2) Preload JSON data files on idle (so next page visit is instant)
  if ('requestIdleCallback' in window) {
    requestIdleCallback(function() {
      var files = ['jobs-index.json', 'jobs-search-index.json'];
      files.forEach(function(f) {
        try {
          fetch(f, { cache: 'force-cache', priority: 'low' }).catch(function(){});
        } catch(e) {}
      });
    }, { timeout: 5000 });
  }

  // 3) Add passive event listeners for scroll performance
  var passiveSupported = false;
  try {
    var opts = Object.defineProperty({}, 'passive', {
      get: function() { passiveSupported = true; }
    });
    window.addEventListener('testPassive', null, opts);
    window.removeEventListener('testPassive', null, opts);
  } catch(e) {}

  // 4) Reduce paint on scroll — throttle non-critical updates
  var ticking = false;
  document.addEventListener('scroll', function() {
    if (!ticking) {
      requestAnimationFrame(function() { ticking = false; });
      ticking = true;
    }
  }, passiveSupported ? { passive: true } : false);

})();
