
(function () {
  'use strict';

  
  const SITE = 'https://www.topsarkarijobs.com';
  const SITE_NAME = 'Top Sarkari Jobs';
  const MAX_RECENTLY_VIEWED = 10;
  const POPULAR_SEARCHES = [
    'SSC CGL 2026', 'Railway RPF 2026', 'IBPS PO 2026', 'UP Police 2026',
    'Bihar Police 2026', 'Army GD 2026', 'UPSC 2026', 'Bank PO 2026',
    '10th Pass Jobs', '12th Pass Jobs', 'ITI Jobs 2026', 'Police Jobs 2026',
    'Teaching Jobs 2026', 'CRPF 2026', 'NDA 2026', 'DRDO 2026'
  ];

  
  const Store = {
    get(key, fallback = null) {
      try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; }
      catch (e) { return fallback; }
    },
    set(key, val) {
      try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) {}
    }
  };

  
  const RecentlyViewed = {
    key: 'tsj_rv',
    add(item) {
      let list = Store.get(this.key, []);
      list = list.filter(x => x.url !== item.url);
      list.unshift({ ...item, time: Date.now() });
      if (list.length > MAX_RECENTLY_VIEWED) list = list.slice(0, MAX_RECENTLY_VIEWED);
      Store.set(this.key, list);
    },
    get() { return Store.get(this.key, []); },
    render() {
      const el = document.getElementById('recently-viewed-list');
      if (!el) return;
      const items = this.get();
      if (!items.length) { el.closest('.sec-card') && (el.closest('.sec-card').style.display = 'none'); return; }
      el.innerHTML = items.slice(0, 5).map(item => `
        <a href="${item.url}" class="rv-item">
          <i class="fa-solid fa-clock-rotate-left" style="color:var(--muted);font-size:.7rem;"></i>
          <span>${escHtml(item.title)}</span>
          <i class="fa-solid fa-chevron-right arrow"></i>
        </a>`).join('');
    }
  };

  
  function buildStickyNotifBar() {
    if (document.getElementById('sticky-notif-bar')) return;
    const dismissed = Store.get('tsj_notif_dismissed', 0);
    if (Date.now() - dismissed < 86400000) return; 

    const bar = document.createElement('div');
    bar.id = 'sticky-notif-bar';
    bar.innerHTML = `
      <style>
        #sticky-notif-bar {
          position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;
          background: linear-gradient(90deg, #0d2257, #1a56db);
          color: #fff; font-size: .78rem; font-weight: 600;
          padding: 9px 16px; display: flex; align-items: center;
          justify-content: space-between; gap: 10px;
          box-shadow: 0 -3px 16px rgba(0,0,0,.18);
          transform: translateY(100%); transition: transform .4s ease;
        }
        #sticky-notif-bar.show { transform: translateY(0); }
        #sticky-notif-bar .snb-text { display: flex; align-items: center; gap: 8px; }
        #sticky-notif-bar .snb-blink { animation: snbBlink 1.2s infinite; color: #fbbf24; }
        @keyframes snbBlink { 0%,100%{opacity:1} 50%{opacity:.4} }
        #sticky-notif-bar .snb-actions { display: flex; align-items: center; gap: 8px; }
        #sticky-notif-bar .snb-btn {
          background: #25d366; color: #fff; border: none; border-radius: 5px;
          padding: 5px 12px; font-size: .73rem; font-weight: 700; cursor: pointer;
          white-space: nowrap;
        }
        #sticky-notif-bar .snb-close {
          background: rgba(255,255,255,.15); border: none; color: #fff;
          border-radius: 50%; width: 22px; height: 22px; font-size: .7rem;
          cursor: pointer; display: flex; align-items: center; justify-content: center;
        }
        @media(max-width:480px){ #sticky-notif-bar { font-size:.7rem; } }
      </style>
      <div class="snb-text">
        <i class="fa-solid fa-bell snb-blink"></i>
        <span>🔥 नई भर्ती आई! Latest Govt Jobs 2026 — अभी देखें</span>
      </div>
      <div class="snb-actions">
        <a href="https://www.whatsapp.com/channel/0029Vb2rMdsHbFUyxUBfKk0T" target="_blank" rel="noopener" class="snb-btn">
          <i class="fa-brands fa-whatsapp"></i> Join WhatsApp
        </a>
        <button class="snb-close" id="snbClose" aria-label="Close notification"><i class="fa-solid fa-xmark"></i></button>
      </div>`;
    document.body.appendChild(bar);
    setTimeout(() => bar.classList.add('show'), 2000);
    document.getElementById('snbClose').addEventListener('click', () => {
      bar.classList.remove('show');
      Store.set('tsj_notif_dismissed', Date.now());
      setTimeout(() => bar.remove(), 400);
    });
  }

  
  function initPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    const asked = Store.get('tsj_push_asked', 0);
    if (Date.now() - asked < 604800000) return; 
    Store.set('tsj_push_asked', Date.now());

    setTimeout(() => {
      if (Notification.permission === 'default') {
        Notification.requestPermission().then(perm => {
          if (perm === 'granted') {
            navigator.serviceWorker.register('/sw.js').catch(() => {});
          }
        });
      }
    }, 15000); 
  }

  
  function buildPopularSearches() {
    const el = document.getElementById('popular-searches-widget');
    if (!el) return;
    const searches = Store.get('tsj_searches', []);
    
    const all = [...new Set([...searches, ...POPULAR_SEARCHES])].slice(0, 16);
    el.innerHTML = all.map(q =>
      `<a href="search.html?q=${encodeURIComponent(q)}" class="ps-tag">${escHtml(q)}</a>`
    ).join('');
  }

  
  function trackSearch(query) {
    if (!query || query.length < 2) return;
    let searches = Store.get('tsj_searches', []);
    searches = [query, ...searches.filter(s => s.toLowerCase() !== query.toLowerCase())].slice(0, 8);
    Store.set('tsj_searches', searches);
  }

  
  function buildShareButtons(container) {
    if (!container) return;
    const url = encodeURIComponent(location.href);
    const title = encodeURIComponent(document.title);
    container.innerHTML = `
      <style>
        .share-bar { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
        .share-btn {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 6px 12px; border-radius: 6px; font-size: .73rem; font-weight: 700;
          text-decoration: none; border: none; cursor: pointer; transition: opacity .2s;
        }
        .share-btn:hover { opacity: .85; }
        .share-wa { background: #25d366; color: #fff; }
        .share-tg { background: #0088cc; color: #fff; }
        .share-tw { background: #000; color: #fff; }
        .share-fb { background: #1877f2; color: #fff; }
        .share-copy { background: #f1f5f9; color: #374151; border: 1px solid #e2e8f0; }
      </style>
      <div class="share-bar" role="group" aria-label="Share this page">
        <span style="font-size:.73rem;font-weight:700;color:#64748b;align-self:center;">Share:</span>
        <a class="share-btn share-wa" href="https://wa.me/?text=${title}%20${url}" target="_blank" rel="noopener" aria-label="Share on WhatsApp">
          <i class="fa-brands fa-whatsapp"></i> WhatsApp
        </a>
        <a class="share-btn share-tg" href="https://t.me/share/url?url=${url}&text=${title}" target="_blank" rel="noopener" aria-label="Share on Telegram">
          <i class="fa-brands fa-telegram"></i> Telegram
        </a>
        <a class="share-btn share-tw" href="https://twitter.com/intent/tweet?url=${url}&text=${title}" target="_blank" rel="noopener" aria-label="Share on Twitter">
          <i class="fa-brands fa-x-twitter"></i> X
        </a>
        <button class="share-btn share-copy" id="shareCopyBtn" aria-label="Copy link">
          <i class="fa-solid fa-copy"></i> Copy Link
        </button>
      </div>`;
    const copyBtn = container.querySelector('#shareCopyBtn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(location.href).then(() => {
          copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
          copyBtn.style.background = '#d1fae5';
          setTimeout(() => { copyBtn.innerHTML = '<i class="fa-solid fa-copy"></i> Copy Link'; copyBtn.style.background = ''; }, 2000);
        }).catch(() => {});
      });
    }
  }

  
  function injectJobSchema(jobData) {
    const existing = document.getElementById('jobSchema');
    if (!existing || !jobData) return;
    const schema = {
      '@context': 'https://schema.org',
      '@type': 'JobPosting',
      title: jobData.title || document.title,
      description: jobData.description || document.querySelector('meta[name="description"]')?.content || '',
      datePosted: jobData.datePosted || new Date().toISOString().split('T')[0],
      validThrough: jobData.lastDate || '',
      employmentType: 'FULL_TIME',
      hiringOrganization: {
        '@type': 'Organization',
        name: jobData.org || 'Government of India',
        sameAs: SITE
      },
      jobLocation: {
        '@type': 'Place',
        address: { '@type': 'PostalAddress', addressCountry: 'IN', addressRegion: jobData.state || 'India' }
      },
      baseSalary: jobData.salary ? {
        '@type': 'MonetaryAmount',
        currency: 'INR',
        value: { '@type': 'QuantitativeValue', value: jobData.salary, unitText: 'MONTH' }
      } : undefined
    };
    
    Object.keys(schema).forEach(k => schema[k] === undefined && delete schema[k]);
    existing.textContent = JSON.stringify(schema);
  }

  function injectBreadcrumbSchema(crumbs) {
    const el = document.createElement('script');
    el.type = 'application/ld+json';
    el.id = 'breadcrumbSchema';
    el.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: crumbs.map((c, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: c.name,
        item: c.url
      }))
    });
    const existing = document.getElementById('breadcrumbSchema');
    if (existing) existing.remove();
    document.head.appendChild(el);
  }

  
  function buildBreadcrumb(crumbs) {
    const el = document.getElementById('dynamic-breadcrumb');
    if (!el) return;
    el.innerHTML = crumbs.map((c, i) => {
      if (i === crumbs.length - 1) return `<span aria-current="page">${escHtml(c.name)}</span>`;
      return `<a href="${c.url}">${escHtml(c.name)}</a><span class="sep" aria-hidden="true">›</span>`;
    }).join('');
    injectBreadcrumbSchema(crumbs);
  }

  
  function applyLazyLoading() {
    document.querySelectorAll('img:not([loading])').forEach(img => {
      img.setAttribute('loading', 'lazy');
      img.setAttribute('decoding', 'async');
      if (!img.alt) img.alt = img.title || SITE_NAME;
    });
  }

  
  function prefetchOnHover() {
    const prefetched = new Set();
    document.addEventListener('mouseover', e => {
      const a = e.target.closest('a[href]');
      if (!a) return;
      const href = a.getAttribute('href');
      if (!href || href.startsWith('http') || href.startsWith('#') || prefetched.has(href)) return;
      prefetched.add(href);
      const link = document.createElement('link');
      link.rel = 'prefetch'; link.href = href;
      document.head.appendChild(link);
    }, { passive: true });
  }

  
  function setupAutoRefreshBadge() {
    const el = document.getElementById('live-update-badge');
    if (!el) return;
    let count = 0;
    setInterval(() => {
      count++;
      el.textContent = `${count} new update${count > 1 ? 's' : ''}`;
      el.style.display = 'inline-block';
    }, 120000); 
  }

  
  function initPage() {
    const page = (location.pathname.split('/').pop() || 'index.html').toLowerCase();

    
    if (page === 'view.html' || page === 'job.html') {
      const params = new URLSearchParams(location.search);
      const title = params.get('name') || params.get('section') || document.title;
      if (title) RecentlyViewed.add({ title, url: location.href });
    }

    
    if (page === '' || page === 'index.html') {
      buildBreadcrumb([{ name: 'Home', url: SITE + '/' }]);
      buildPopularSearches();
      setupAutoRefreshBadge();

      
      const heroSearchBtn = document.getElementById('heroSearchBtn');
      const heroSearchInput = document.getElementById('heroSearch');
      if (heroSearchBtn && heroSearchInput) {
        heroSearchBtn.addEventListener('click', () => trackSearch(heroSearchInput.value.trim()));
        heroSearchInput.addEventListener('keydown', e => { if (e.key === 'Enter') trackSearch(heroSearchInput.value.trim()); });
      }
    }

    
    if (page === 'result.html') {
      buildBreadcrumb([
        { name: 'Home', url: SITE + '/' },
        { name: 'Results', url: SITE + '/result.html' }
      ]);
    }

    
    if (page === 'admit-card.html') {
      buildBreadcrumb([
        { name: 'Home', url: SITE + '/' },
        { name: 'Admit Cards', url: SITE + '/admit-card.html' }
      ]);
    }

    
    if (page === 'job.html') {
      const shareContainer = document.getElementById('job-share-buttons');
      if (shareContainer) buildShareButtons(shareContainer);
    }

    
    if (page === 'view.html') {
      const params = new URLSearchParams(location.search);
      const section = params.get('section') || '';
      if (section) {
        buildBreadcrumb([
          { name: 'Home', url: SITE + '/' },
          { name: section, url: location.href }
        ]);
      }
      const shareContainer = document.getElementById('view-share-buttons');
      if (shareContainer) buildShareButtons(shareContainer);
    }

    
    if (page === 'search.html') {
      const params = new URLSearchParams(location.search);
      const q = params.get('q') || '';
      if (q) trackSearch(q);
    }

    
    RecentlyViewed.render();

    
    const shareEl = document.querySelector('.page-share-container');
    if (shareEl) buildShareButtons(shareEl);
  }

  
  function fixCLS() {
    
    document.querySelectorAll('img:not([width]):not([height])').forEach(img => {
      if (!img.style.aspectRatio) img.style.aspectRatio = '16/9';
    });
  }

  
  function escHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

  function run() {
    initPage();
    buildStickyNotifBar();
    applyLazyLoading();
    prefetchOnHover();
    fixCLS();
    
    if ('requestIdleCallback' in window) {
      requestIdleCallback(initPushNotifications, { timeout: 10000 });
    } else {
      setTimeout(initPushNotifications, 5000);
    }
  }

  
  window.TSJSeo = { RecentlyViewed, buildShareButtons, buildBreadcrumb, injectJobSchema, trackSearch };

})();
