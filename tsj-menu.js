/**
 * TSJ Universal Menu System — works on ALL pages
 * Handles: mobile offcanvas menu, accordion, desktop dropdowns
 * Called automatically OR via window.__TSJ_INIT_HEADER()
 */
(function () {
  'use strict';

  // ── Desktop nav dropdowns via DOCUMENT DELEGATION ────────────────
  // Bound once on document, so it works on every page regardless of
  // whether the header is static or injected later via fetch.
  if (!document.body || !document.body._tsjDDDelegated) {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest ? e.target.closest('.nav-dd-btn') : null;
      if (btn) {
        // a dropdown toggle button was clicked
        e.preventDefault();
        e.stopPropagation();
        var dd   = btn.closest('[data-dd]') || btn.parentNode;
        var menu = dd ? dd.querySelector('.nav-dd-menu') : null;
        if (!menu) return;
        var isOpen = menu.style.display === 'block';
        // close all menus + reset all buttons
        document.querySelectorAll('.nav-dd-menu').forEach(function (m) { m.style.display = ''; });
        document.querySelectorAll('.nav-dd-btn').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
        if (!isOpen) {
          menu.style.display = 'block';
          btn.setAttribute('aria-expanded', 'true');
        }
        return;
      }
      // click outside any open dropdown → close all
      if (!(e.target.closest && e.target.closest('.nav-dd-menu'))) {
        document.querySelectorAll('.nav-dd-menu').forEach(function (m) { m.style.display = ''; });
        document.querySelectorAll('.nav-dd-btn').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
      }
    });
    if (document.body) document.body._tsjDDDelegated = true;
  }

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

    // Desktop nav dropdowns — handled by a single delegated listener below
    // (see initDropdownDelegation). Nothing to bind per-element here, so the
    // dropdowns work even when the header is injected dynamically after load.

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

  // ── MutationObserver fallback (for dynamic header injection) ──
  // Watch the body for the menuBtn appearing, regardless of current header state.
  if (!document.getElementById('menuBtn')) {
    var obs = new MutationObserver(function () {
      if (document.getElementById('menuBtn')) {
        obs.disconnect();
        setTimeout(initMenu, 30);
      }
    });
    if (document.body) {
      obs.observe(document.body, { childList: true, subtree: true });
    } else {
      document.addEventListener('DOMContentLoaded', function () {
        obs.observe(document.body, { childList: true, subtree: true });
      });
    }
  }

})();

// R3 FIX: ESC key closes dropdowns
document.addEventListener('keydown', function(e){
  if(e.key==='Escape'){
    document.querySelectorAll('.nav-dd-menu').forEach(function(m){m.style.display='';});
    document.querySelectorAll('.nav-dd-btn').forEach(function(b){b.setAttribute('aria-expanded','false');});
  }
});

// ── Google Translate widget — lazy-loaded, NO cloaking ───────────────────────
// Loads the Google Translate script ONLY after the first user interaction (or a
// short idle fallback), so it adds nothing to initial page load / LCP / CLS.
// Googlebot sees the exact same markup + script — no user-agent detection.
(function(){
  var loaded=false;
  function loadGT(){
    if(loaded)return; loaded=true;
    var s=document.createElement('script');
    s.src='https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
    s.async=true;
    (document.body||document.documentElement).appendChild(s);
  }
  window.addEventListener('scroll',loadGT,{once:true,passive:true});
  window.addEventListener('touchstart',loadGT,{once:true,passive:true});
  window.addEventListener('keydown',loadGT,{once:true});
  window.addEventListener('click',loadGT,{once:true});
  // Passive-user fallback during idle time, so it never blocks page load.
  if('requestIdleCallback' in window){ requestIdleCallback(function(){ setTimeout(loadGT,3000); }); }
  else { setTimeout(loadGT,4000); }
})();

window.googleTranslateElementInit=function(){
  var el=document.getElementById('google_translate_element');
  if(!el){ setTimeout(window.googleTranslateElementInit,200); return; }   // header may still be injecting
  if(el.getAttribute('data-gt-done')) return;
  try{
    new google.translate.TranslateElement(
      { pageLanguage:'en', autoDisplay:false,
        includedLanguages:'en,hi,bn,ta,te,mr,gu,kn,ml,pa,or,as,ur' },
      'google_translate_element'
    );
    el.setAttribute('data-gt-done','1');
  }catch(e){}
};
