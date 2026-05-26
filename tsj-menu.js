/**
 * TSJ Universal Menu System — works on ALL pages
 * Handles: mobile offcanvas menu, accordion, desktop dropdowns
 * Called automatically OR via window.__TSJ_INIT_HEADER()
 */
(function () {
  'use strict';

  function initMenu() {
    var menuBtn    = document.getElementById('menuBtn');
    var closeBtn   = document.getElementById('closeMenuBtn');
    var mobileMenu = document.getElementById('mobileMenu');
    var overlay    = document.getElementById('menuOverlay');

    if (!menuBtn || menuBtn.dataset.tsjMenuInit || menuBtn.dataset.offcanvasInit) return; // already initialized
    menuBtn.dataset.tsjMenuInit = '1';

    // Make sure menu starts hidden
    if (mobileMenu) mobileMenu.hidden = true;
    if (overlay)    overlay.hidden    = true;

    function openMenu() {
      if (!mobileMenu || !overlay) return;
      mobileMenu.hidden            = false;
      overlay.hidden               = false;
      mobileMenu.classList.add('open');
      overlay.classList.add('show');
      menuBtn.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    }

    function closeMenu() {
      if (!mobileMenu || !overlay) return;
      mobileMenu.hidden            = true;
      overlay.hidden               = true;
      mobileMenu.classList.remove('open');
      overlay.classList.remove('show');
      menuBtn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    }

    menuBtn.addEventListener('click', openMenu);
    if (closeBtn) closeBtn.addEventListener('click', closeMenu);
    if (overlay)  overlay.addEventListener('click', closeMenu);

    // Accordion + link handling inside offcanvas
    if (mobileMenu) {
      mobileMenu.addEventListener('click', function (e) {
        var accBtn = e.target.closest('.mob-acc-head');
        if (accBtn) {
          e.stopPropagation();
          var id   = accBtn.getAttribute('data-acc');
          var body = id ? document.getElementById(id) : null;
          if (!body) return;
          var isOpen = accBtn.classList.contains('open');
          // Close all other accordions
          mobileMenu.querySelectorAll('.mob-acc-head.open').forEach(function (b) {
            if (b !== accBtn) {
              b.classList.remove('open');
              var ob = document.getElementById(b.getAttribute('data-acc'));
              if (ob) ob.classList.remove('open');
            }
          });
          accBtn.classList.toggle('open', !isOpen);
          body.classList.toggle('open', !isOpen);
          return;
        }
        // Close menu when a link is tapped
        if (e.target.closest('a[href]')) closeMenu();
      });
    }

    // Desktop nav dropdowns
    document.querySelectorAll('[data-dd]').forEach(function (dd) {
      var btn  = dd.querySelector('.nav-dd-btn');
      var menu = dd.querySelector('.nav-dd-menu');
      if (!btn || !menu) return;
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        var isOpen = menu.style.display === 'block';
        document.querySelectorAll('.nav-dd-menu').forEach(function (m) { m.style.display = ''; });
        if (!isOpen) menu.style.display = 'block';
      });
    });
    document.addEventListener('click', function () {
      document.querySelectorAll('.nav-dd-menu').forEach(function (m) { m.style.display = ''; });
    });

    // Mobile search button → scroll to search
    var mobileSearchBtn = document.getElementById('mobileSearchBtn');
    if (mobileSearchBtn && window.innerWidth < 768) {
      mobileSearchBtn.style.display = 'flex';
      mobileSearchBtn.addEventListener('click', function () {
        var hero = document.getElementById('hero-search-section');
        var inp  = document.getElementById('heroSearch');
        if (hero) hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
        if (inp)  setTimeout(function () { inp.focus(); }, 400);
      });
    }

    // Menu search input — filter/suggest (handled by smart-search.js if loaded)
    var menuSearchInp = document.getElementById('menuSearchInput');
    if (menuSearchInp && !menuSearchInp._tsjInit) {
      menuSearchInp._tsjInit = true;
      // Basic fallback filter when smart-search is not loaded
      menuSearchInp.addEventListener('input', function () {
        if (window.TSJSmartSearchMenuReady) return; // smart-search handles it
        var q   = this.value.trim().toLowerCase();
        var nav = document.querySelector('.offcanvas-nav');
        if (!nav) return;
        nav.querySelectorAll('a').forEach(function (a) {
          a.style.display = (!q || a.textContent.toLowerCase().includes(q)) ? '' : 'none';
        });
        nav.querySelectorAll('.mob-acc-body').forEach(function (b) {
          b.classList.toggle('open', !!q);
        });
        nav.querySelectorAll('.mob-acc-head').forEach(function (b) {
          b.classList.toggle('open', !!q);
        });
      });
    }
  }

  // ── Define __TSJ_INIT_HEADER globally ────────────────────────────
  // Called by all pages after header.html is injected into DOM
  window.__TSJ_INIT_HEADER = function () {
    // Small delay to ensure DOM is fully updated
    setTimeout(initMenu, 50);
  };

  // ── Also try to init on DOMContentLoaded (for pages with static header) ──
  function tryInit() {
    if (document.getElementById('menuBtn')) {
      initMenu();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryInit);
  } else {
    tryInit();
  }

  // ── MutationObserver as final fallback (for dynamic header injection) ──
  var headerEl = document.getElementById('site-header');
  if (headerEl && !document.getElementById('menuBtn')) {
    var obs = new MutationObserver(function () {
      if (document.getElementById('menuBtn')) {
        obs.disconnect();
        setTimeout(initMenu, 30);
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

})();
