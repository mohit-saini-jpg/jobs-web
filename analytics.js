/**
 * analytics.js — Centralized GA4 Tracking System
 * Site: topsarkarijobs.com
 * Measurement ID: G-C4VRD1C9QS
 *
 * Features:
 *  - Single source of truth: include once, never duplicated
 *  - Deduplication guard (blocks if already loaded)
 *  - SPA / dynamic-page support (history.pushState / replaceState hooks)
 *  - Dynamic page-title normalization for accurate GA reports
 *  - Fallback loader if primary CDN fails
 *  - Engagement events (scroll depth, outbound clicks, search queries)
 *  - Real-time active-user accuracy (session_start, page_view)
 *  - Mobile + desktop compatible
 *  - Auto-inherited by all future pages that include this script
 */
(function () {
  'use strict';

  /* ─── Config ─────────────────────────────────────────────── */
  var GA_ID  = 'G-C4VRD1C9QS';
  var GA_SRC = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  var GA_FB  = 'https://www.google-analytics.com/g/collect'; // fallback check endpoint

  /* ─── Deduplication guard ─────────────────────────────────── */
  if (window.__ga4Loaded) return;
  window.__ga4Loaded = true;

  /* Remove any previously injected duplicate GA scripts before we start */
  var existing = document.querySelectorAll('script[src*="googletagmanager.com/gtag"]');
  existing.forEach(function (s, i) { if (i > 0) s.parentNode && s.parentNode.removeChild(s); });

  /* ─── dataLayer bootstrap (idempotent) ───────────────────── */
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = window.gtag || gtag;

  /* ─── Helper: normalize page title ───────────────────────── */
  function getTitle() {
    var raw = document.title || '';
    // Strip leading pipe/dash noise, collapse whitespace
    raw = raw.replace(/^\s*[|\-–]\s*/, '').trim();
    // Ensure "| Top Sarkari Jobs" suffix for uniformity
    if (raw && !raw.includes('Top Sarkari Jobs')) {
      raw = raw + ' | Top Sarkari Jobs';
    }
    return raw || 'Top Sarkari Jobs';
  }

  /* ─── Helper: normalize page path ────────────────────────── */
  function getPath() {
    return location.pathname + location.search;
  }

  /* ─── Load the GA4 script ────────────────────────────────── */
  function loadGAScript(callback) {
    if (document.querySelector('script[src*="googletagmanager.com/gtag/js?id=' + GA_ID + '"]')) {
      if (callback) callback();
      return;
    }
    var s = document.createElement('script');
    s.async = true;
    s.src = GA_SRC;
    s.onload = function () { if (callback) callback(); };
    s.onerror = function () {
      // Fallback: try loading from alternate CDN
      var fb = document.createElement('script');
      fb.async = true;
      fb.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID + '&l=dataLayer';
      document.head.appendChild(fb);
      if (callback) setTimeout(callback, 500);
    };
    document.head.appendChild(s);
  }

  /* ─── Initialize GA4 config ──────────────────────────────── */
  function initGA() {
    gtag('js', new Date());
    gtag('config', GA_ID, {
      send_page_view: false,          // We fire page_view manually for SPA accuracy
      page_title: getTitle(),
      page_location: location.href,
      page_path: getPath(),
      cookie_flags: 'SameSite=None;Secure',
      allow_google_signals: true,
      allow_ad_personalization_signals: false,
      transport_type: 'beacon'
    });

    // Fire the first page_view
    firePageView();
  }

  /* ─── Fire page_view event ───────────────────────────────── */
  var _lastPath = '';
  function firePageView() {
    var path  = getPath();
    var title = getTitle();

    // Deduplicate: don't fire twice for the same path
    if (path === _lastPath) return;
    _lastPath = path;

    gtag('event', 'page_view', {
      page_title:    title,
      page_location: location.href,
      page_path:     path,
      send_to:       GA_ID
    });
  }

  /* ─── SPA Navigation hooks ───────────────────────────────── */
  function patchHistory(method) {
    var original = history[method];
    history[method] = function () {
      original.apply(history, arguments);
      // Wait a tick for the page to update title/content
      setTimeout(firePageView, 100);
    };
  }
  patchHistory('pushState');
  patchHistory('replaceState');

  window.addEventListener('popstate', function () {
    setTimeout(firePageView, 100);
  });

  /* ─── Dynamic title observer (for SPA pages that set title late) ─ */
  if (typeof MutationObserver !== 'undefined') {
    var titleEl = document.querySelector('title');
    if (titleEl) {
      var _titleObs = new MutationObserver(function () {
        // Only re-fire if path didn't change (title-only update)
        firePageView();
      });
      _titleObs.observe(titleEl, { childList: true });
    }
  }

  /* ─── Scroll Depth Tracking ──────────────────────────────── */
  var _scrollFired = { 25: false, 50: false, 75: false, 90: false };
  function onScroll() {
    var scrolled = (window.scrollY + window.innerHeight) / document.body.scrollHeight * 100;
    [25, 50, 75, 90].forEach(function (depth) {
      if (!_scrollFired[depth] && scrolled >= depth) {
        _scrollFired[depth] = true;
        gtag('event', 'scroll_depth', {
          depth_percent: depth,
          page_path: getPath(),
          non_interaction: true,
          send_to: GA_ID
        });
      }
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });

  /* ─── Outbound Link Tracking ─────────────────────────────── */
  document.addEventListener('click', function (e) {
    var el = e.target.closest('a[href]');
    if (!el) return;
    var href = el.getAttribute('href') || '';
    if (href.startsWith('http') && !href.includes('topsarkarijobs.com')) {
      gtag('event', 'outbound_click', {
        link_url:   href,
        link_text:  (el.textContent || '').trim().slice(0, 100),
        page_path:  getPath(),
        send_to:    GA_ID
      });
    }
  });

  /* ─── Search Query Tracking ──────────────────────────────── */
  var _searchTracked = false;
  function trackSearch(query) {
    if (!query || _searchTracked) return;
    _searchTracked = true;
    setTimeout(function () { _searchTracked = false; }, 2000);
    gtag('event', 'search', {
      search_term: query.slice(0, 100),
      page_path:   getPath(),
      send_to:     GA_ID
    });
  }

  // Track URL ?q= or ?query= params (search result pages)
  (function () {
    var params = new URLSearchParams(location.search);
    var q = params.get('q') || params.get('query') || params.get('search');
    if (q) trackSearch(q);
  })();

  // Track in-page search form submissions
  document.addEventListener('submit', function (e) {
    var form = e.target;
    var input = form.querySelector('input[type="search"], input[name="q"], #q');
    if (input && input.value) trackSearch(input.value);
  });

  /* ─── Job Detail View Tracking ───────────────────────────── */
  // Exposed globally so SPA job pages can call it after render
  window.ga4TrackJobView = function (jobTitle, jobCategory) {
    gtag('event', 'view_item', {
      items: [{
        item_name:     (jobTitle     || document.title || '').slice(0, 200),
        item_category: (jobCategory  || 'Government Job')
      }],
      page_path: getPath(),
      send_to:   GA_ID
    });
  };

  /* ─── Expose manual page_view for SPA renderers ──────────── */
  window.ga4PageView = function (title, path) {
    if (title) document.title = title;
    if (path)  history.replaceState(null, '', path);
    setTimeout(firePageView, 50);
  };

  /* ─── Boot sequence ──────────────────────────────────────── */
  function boot() {
    loadGAScript(initGA);
  }

  // Load immediately on DOMContentLoaded (or now if already ready)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
