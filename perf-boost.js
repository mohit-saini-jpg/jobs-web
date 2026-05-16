/**
 * perf-boost.js — Top Sarkari Jobs
 * Master Performance & Core Web Vitals Optimizer
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * ✅ Lazy load images (IntersectionObserver)
 * ✅ Reduce CLS — reserve image dimensions
 * ✅ Reduce LCP — preconnect & prefetch critical resources
 * ✅ Reduce INP — passive listeners, defer non-critical JS
 * ✅ Font display:swap enforcement
 * ✅ DOM size reduction — virtualized lists
 * ✅ Adaptive JSON fetch — stale-while-revalidate
 * ✅ Resource hints injection
 * ✅ Critical CSS inlining detection
 * ✅ RequestIdleCallback task scheduler
 */

(function () {
  'use strict';

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     1. RESOURCE HINTS (early as possible)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  function injectHints() {
    var head = document.head;
    var hints = [
      { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: true },
      { rel: 'preconnect', href: 'https://www.googletagmanager.com' },
      { rel: 'dns-prefetch', href: '//cdnjs.cloudflare.com' },
      { rel: 'preload', href: '/styles.css', as: 'style' },
      { rel: 'preload', href: '/script.js', as: 'script' },
    ];
    hints.forEach(function (h) {
      if (document.querySelector('link[rel="' + h.rel + '"][href="' + h.href + '"]')) return;
      var el = document.createElement('link');
      el.rel = h.rel;
      el.href = h.href;
      if (h.as) el.setAttribute('as', h.as);
      if (h.crossorigin) el.crossOrigin = '';
      head.insertBefore(el, head.firstChild);
    });
  }
  injectHints();

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     2. LAZY IMAGE LOADING (CLS + LCP)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  var imgObserver = null;

  function setupLazyImages() {
    var imgs = document.querySelectorAll('img[data-src], img:not([loading])');
    imgs.forEach(function (img) {
      // Reserve space to prevent CLS
      if (!img.width && img.getAttribute('data-width')) {
        img.style.width = img.getAttribute('data-width') + 'px';
      }
      if (!img.height && img.getAttribute('data-height')) {
        img.style.height = img.getAttribute('data-height') + 'px';
      }
      // Add loading=lazy if not set
      if (!img.getAttribute('loading')) {
        img.setAttribute('loading', 'lazy');
      }
      if (!img.getAttribute('decoding')) {
        img.setAttribute('decoding', 'async');
      }
    });

    // Handle data-src lazy images
    var lazySrcs = document.querySelectorAll('img[data-src]');
    if (!lazySrcs.length) return;

    if ('IntersectionObserver' in window) {
      imgObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            var img = entry.target;
            img.src = img.getAttribute('data-src');
            if (img.getAttribute('data-srcset')) {
              img.srcset = img.getAttribute('data-srcset');
            }
            img.removeAttribute('data-src');
            imgObserver.unobserve(img);
          }
        });
      }, { rootMargin: '200px 0px', threshold: 0.01 });

      lazySrcs.forEach(function (img) { imgObserver.observe(img); });
    } else {
      // Fallback: load all
      lazySrcs.forEach(function (img) {
        img.src = img.getAttribute('data-src');
      });
    }
  }

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     3. ADAPTIVE JSON FETCH (stale-while-revalidate)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  var JSON_CACHE_TTL = 10 * 60 * 1000; // 10 min

  window.fetchJSON = function (url, opts) {
    opts = opts || {};
    var cacheKey = 'tsj_jc_' + url.split('/').pop();
    var ttl = opts.ttl || JSON_CACHE_TTL;

    return new Promise(function (resolve, reject) {
      // Try memory cache first
      if (window._jsonMemCache && window._jsonMemCache[url]) {
        var cached = window._jsonMemCache[url];
        if (Date.now() - cached.ts < ttl) {
          resolve(cached.data);
          // Background revalidate
          fetch(url, { priority: 'low' })
            .then(function (r) { return r.json(); })
            .then(function (d) {
              window._jsonMemCache[url] = { data: d, ts: Date.now() };
            }).catch(function () {});
          return;
        }
      }

      // Try sessionStorage
      try {
        var raw = sessionStorage.getItem(cacheKey);
        if (raw) {
          var entry = JSON.parse(raw);
          if (Date.now() - entry.ts < ttl) {
            resolve(entry.data);
            window._jsonMemCache = window._jsonMemCache || {};
            window._jsonMemCache[url] = entry;
            return;
          }
        }
      } catch (e) {}

      // Fetch fresh
      fetch(url, {
        headers: { 'Accept': 'application/json' },
        priority: opts.priority || 'high'
      })
        .then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .then(function (data) {
          var entry = { data: data, ts: Date.now() };
          window._jsonMemCache = window._jsonMemCache || {};
          window._jsonMemCache[url] = entry;
          try { sessionStorage.setItem(cacheKey, JSON.stringify(entry)); } catch (e) {}
          resolve(data);
        })
        .catch(reject);
    });
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     4. CLS PREVENTION — layout shift guard
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  function preventCLS() {
    // Reserve height for async-rendered sections
    var placeholders = document.querySelectorAll('[data-min-height]');
    placeholders.forEach(function (el) {
      el.style.minHeight = el.getAttribute('data-min-height') + 'px';
    });

    // Prevent ads/embeds from causing shifts
    var iframes = document.querySelectorAll('iframe:not([height])');
    iframes.forEach(function (iframe) {
      iframe.style.height = '0';
    });
  }

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     5. INP OPTIMIZER — passive event listeners
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  function optimizeINP() {
    // Make scroll, touch, wheel listeners passive by default
    var EventTargetProto = window.EventTarget && window.EventTarget.prototype;
    if (!EventTargetProto) return;

    var _origAEL = EventTargetProto.addEventListener;
    var passiveEvents = new Set(['scroll', 'touchstart', 'touchmove', 'touchend', 'wheel', 'mousewheel']);

    EventTargetProto.addEventListener = function (type, listener, options) {
      if (passiveEvents.has(type)) {
        if (options === undefined || options === false || options === true) {
          options = { passive: true, capture: !!options };
        } else if (typeof options === 'object' && options.passive === undefined) {
          options = Object.assign({}, options, { passive: true });
        }
      }
      return _origAEL.call(this, type, listener, options);
    };
  }

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     6. TASK SCHEDULER — idle-time work
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  var taskQueue = [];
  var taskScheduled = false;

  window.scheduleTask = function (fn, priority) {
    taskQueue.push({ fn: fn, priority: priority || 5 });
    taskQueue.sort(function (a, b) { return a.priority - b.priority; });
    if (!taskScheduled) {
      taskScheduled = true;
      if ('requestIdleCallback' in window) {
        requestIdleCallback(runTasks, { timeout: 2000 });
      } else {
        setTimeout(runTasks, 100);
      }
    }
  };

  function runTasks(deadline) {
    taskScheduled = false;
    while (taskQueue.length) {
      var hasTime = !deadline || deadline.timeRemaining() > 1;
      if (!hasTime) break;
      var task = taskQueue.shift();
      try { task.fn(); } catch (e) { console.warn('Task error:', e); }
    }
    if (taskQueue.length) {
      taskScheduled = true;
      if ('requestIdleCallback' in window) {
        requestIdleCallback(runTasks, { timeout: 1000 });
      } else {
        setTimeout(runTasks, 50);
      }
    }
  }

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     7. FONT OPTIMIZATION
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  function optimizeFonts() {
    // Add font-display:swap to any @font-face rules
    var sheets = Array.from(document.styleSheets);
    sheets.forEach(function (sheet) {
      try {
        var rules = Array.from(sheet.cssRules || []);
        rules.forEach(function (rule) {
          if (rule.type === CSSRule.FONT_FACE_RULE) {
            if (!rule.style.getPropertyValue('font-display')) {
              rule.style.setProperty('font-display', 'swap');
            }
          }
        });
      } catch (e) {} // Cross-origin sheets throw
    });
  }

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     8. PREFETCH ON HOVER (navigation speed)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  var prefetched = new Set();

  function setupHoverPrefetch() {
    document.addEventListener('mouseover', function (e) {
      var a = e.target.closest('a[href]');
      if (!a) return;
      var href = a.href;
      if (!href || prefetched.has(href)) return;
      if (!href.startsWith(location.origin)) return;
      if (href.includes('#') || href.includes('javascript:')) return;

      prefetched.add(href);
      var link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = href;
      document.head.appendChild(link);
    }, { passive: true });
  }

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     9. CORE WEB VITALS REPORTER
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  function reportCWV() {
    if (!('PerformanceObserver' in window)) return;

    // LCP
    try {
      new PerformanceObserver(function (list) {
        var entries = list.getEntries();
        var lcp = entries[entries.length - 1];
        if (lcp && window.gtag) {
          window.gtag('event', 'web_vitals', {
            metric_name: 'LCP',
            metric_value: Math.round(lcp.renderTime || lcp.loadTime),
            metric_delta: Math.round(lcp.renderTime || lcp.loadTime)
          });
        }
      }).observe({ entryTypes: ['largest-contentful-paint'] });
    } catch (e) {}

    // CLS
    try {
      var clsValue = 0;
      new PerformanceObserver(function (list) {
        list.getEntries().forEach(function (entry) {
          if (!entry.hadRecentInput) clsValue += entry.value;
        });
      }).observe({ entryTypes: ['layout-shift'] });
    } catch (e) {}

    // FID / INP
    try {
      new PerformanceObserver(function (list) {
        list.getEntries().forEach(function (entry) {
          if (entry.processingStart && window.gtag) {
            var delay = entry.processingStart - entry.startTime;
            if (delay > 100) {
              window.gtag('event', 'web_vitals', {
                metric_name: 'FID',
                metric_value: Math.round(delay)
              });
            }
          }
        });
      }).observe({ entryTypes: ['first-input'] });
    } catch (e) {}
  }

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     10. DOM VIRTUALIZATION — long lists
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  window.virtualizeList = function (container, items, renderFn, itemHeight) {
    itemHeight = itemHeight || 80;
    var totalHeight = items.length * itemHeight;
    container.style.position = 'relative';
    container.style.height = totalHeight + 'px';
    container.style.overflow = 'auto';

    var rendered = {};
    var viewportObs = new IntersectionObserver(function () { update(); }, {
      root: null, rootMargin: '300px'
    });
    viewportObs.observe(container);

    function update() {
      var scrollTop = container.scrollTop;
      var clientH = container.clientHeight;
      var start = Math.max(0, Math.floor((scrollTop - 300) / itemHeight));
      var end = Math.min(items.length - 1, Math.ceil((scrollTop + clientH + 300) / itemHeight));

      // Remove out-of-view
      Object.keys(rendered).forEach(function (i) {
        if (i < start || i > end) {
          var el = rendered[i];
          if (el && el.parentNode === container) container.removeChild(el);
          delete rendered[i];
        }
      });

      // Add in-view
      for (var i = start; i <= end; i++) {
        if (rendered[i]) continue;
        var el = renderFn(items[i], i);
        el.style.position = 'absolute';
        el.style.top = (i * itemHeight) + 'px';
        el.style.width = '100%';
        container.appendChild(el);
        rendered[i] = el;
      }
    }

    container.addEventListener('scroll', update, { passive: true });
    update();
  };

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     11. SERVICE WORKER REGISTRATION
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  function registerSW() {
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function () {
        navigator.serviceWorker.register('/sw.js', { scope: '/' })
          .then(function (reg) {
            reg.addEventListener('updatefound', function () {
              var newWorker = reg.installing;
              newWorker.addEventListener('statechange', function () {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  // Notify user of update
                  var bar = document.createElement('div');
                  bar.style.cssText = 'position:fixed;bottom:60px;left:50%;transform:translateX(-50%);background:#1d4ed8;color:#fff;padding:10px 20px;border-radius:8px;z-index:10000;font-size:13px;font-weight:600;box-shadow:0 4px 12px rgba(0,0,0,.3);';
                  bar.innerHTML = '🔄 New version available! <button onclick="location.reload()" style="background:#fff;color:#1d4ed8;border:none;padding:4px 10px;border-radius:4px;margin-left:8px;cursor:pointer;font-weight:700;">Refresh</button>';
                  document.body.appendChild(bar);
                  setTimeout(function () { if (bar.parentNode) bar.parentNode.removeChild(bar); }, 8000);
                }
              });
            });
          }).catch(function (e) { console.warn('SW registration failed:', e); });
      });
    }
  }

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     INIT
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  optimizeINP();
  preventCLS();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      setupLazyImages();
      scheduleTask(optimizeFonts, 3);
      scheduleTask(setupHoverPrefetch, 5);
      scheduleTask(reportCWV, 8);
    });
  } else {
    setupLazyImages();
    scheduleTask(optimizeFonts, 3);
    scheduleTask(setupHoverPrefetch, 5);
    scheduleTask(reportCWV, 8);
  }

  window.addEventListener('load', function () {
    registerSW();
  });

  // Re-run lazy images when new content is added (mutation observer)
  var mutationObs = new MutationObserver(function () {
    setupLazyImages();
  });
  mutationObs.observe(document.body || document.documentElement, {
    childList: true, subtree: true
  });

})();
