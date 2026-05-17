/**
 * poster-engine.js
 * TopSarkariJobs — Dynamic Job Poster Engine
 * Auto-detects current job page, matches JSON data, generates & injects poster
 *
 * Usage: Include after <div id="dynamic-job-poster"></div> in job.html
 */

(function (window, document) {
  'use strict';

  /* ══════════════════════════════════════
     CONFIG
  ══════════════════════════════════════ */
  const CONFIG = {
    posterContainerId: 'dynamic-job-poster',
    dataFiles: [
      '/Complete_Jobs_Full_Data.json',
      '/merged_sarkari_data.json',
    ],
    skeletonDelay: 0,        // Show skeleton immediately
    maxSearchDepth: 3,       // How many JSON nesting levels to search
    siteUrl: 'https://www.topsarkarijobs.com',
    siteName: 'TopSarkariJobs.com',
  };

  /* ══════════════════════════════════════
     1. SLUG RESOLUTION
  ══════════════════════════════════════ */
  function getCurrentSlug() {
    let slug = '';

    // From sessionStorage (set by 404.html redirect)
    try { slug = sessionStorage.getItem('__tsj_slug') || ''; } catch (_) {}

    // From URL path /jobs/<slug>/
    if (!slug) {
      const m = window.location.pathname.match(/\/jobs\/([^\/]+)\/?$/);
      if (m) slug = decodeURIComponent(m[1]);
    }

    // From ?slug= query param
    if (!slug) {
      const qp = new URLSearchParams(window.location.search);
      slug = qp.get('slug') || qp.get('id') || '';
    }

    return slug.trim();
  }

  /* ══════════════════════════════════════
     2. JOB DATA MATCHING
  ══════════════════════════════════════ */
  function slugToId(slug) {
    // Normalise: lowercase, strip trailing date patterns
    return slug.toLowerCase()
      .replace(/[-_]+/g, '-')
      .replace(/\/$/, '');
  }

  function titleToSlug(title) {
    return title.toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .trim();
  }

  function scoreMatch(slug, title, keys) {
    const s = slugToId(slug);
    let score = 0;

    // Exact file slug match
    for (const k of (keys || [])) {
      const fileSlug = slugToId(k.replace(/\.json$/, ''));
      if (fileSlug === s || fileSlug.startsWith(s) || s.startsWith(fileSlug.substring(0, 30))) score += 100;
    }

    // Title similarity
    if (title) {
      const tSlug = titleToSlug(title);
      const sWords = s.split('-').filter(w => w.length > 3);
      const tWords = tSlug.split('-').filter(w => w.length > 3);
      const common = sWords.filter(w => tWords.includes(w)).length;
      score += common * 10;
    }
    return score;
  }

  function findJobInData(data, slug) {
    // data can be: array of jobs, object with category keys -> arrays, or flat object
    let bestJob = null, bestScore = 0;

    const tryJob = (job, keys) => {
      const title = job?.basic_details?.job_title || job?.title || '';
      const sc = scoreMatch(slug, title, keys);
      if (sc > bestScore) { bestScore = sc; bestJob = job; }
    };

    if (Array.isArray(data)) {
      data.forEach(j => tryJob(j, [j?.slug || '']));
    } else if (typeof data === 'object') {
      // Might be { category: [jobs] } or { slug: job }
      for (const [key, val] of Object.entries(data)) {
        if (Array.isArray(val)) {
          val.forEach(j => tryJob(j, [key, j?.slug || '']));
        } else if (val && typeof val === 'object' && val.basic_details) {
          tryJob(val, [key]);
        }
      }
    }

    return bestScore > 0 ? bestJob : null;
  }

  /* ══════════════════════════════════════
     3. INDIVIDUAL JOB FILE LOADER
     (fastest: load jobs/data/<slug>.json directly)
  ══════════════════════════════════════ */
  async function tryLoadJobFile(slug) {
    const candidates = [
      `/jobs/data/${slug}.json`,
      `/jobs/data/${slug}-latest-notifications.json`,
    ];

    for (const url of candidates) {
      try {
        const res = await fetch(url, { cache: 'no-store' });
        if (res.ok) {
          const data = await res.json();
          if (data && data.basic_details) return data;
        }
      } catch (_) {}
    }
    return null;
  }

  /* ══════════════════════════════════════
     4. FALLBACK: SEARCH IN FULL JSON FILES
  ══════════════════════════════════════ */
  async function searchInFullData(slug) {
    for (const file of CONFIG.dataFiles) {
      try {
        const res = await fetch(file, { cache: 'default' });
        if (!res.ok) continue;
        const data = await res.json();
        const job = findJobInData(data, slug);
        if (job) return job;
      } catch (_) {}
    }
    return null;
  }

  /* ══════════════════════════════════════
     5. SKELETON LOADER
  ══════════════════════════════════════ */
  function showSkeleton(container) {
    container.innerHTML = '<div class="poster-skeleton" aria-label="Loading job poster…"></div>';
  }

  function hideSkeleton(container) {
    const sk = container.querySelector('.poster-skeleton');
    if (sk) sk.remove();
  }

  /* ══════════════════════════════════════
     6. OG IMAGE & SEO INJECTION
  ══════════════════════════════════════ */
  function injectOGMeta(jobData, pageUrl) {
    const title = jobData?.basic_details?.job_title || '';
    const desc  = jobData?.basic_details?.short_information || title;
    const imgUrl = `${CONFIG.siteUrl}/image.png`; // TODO: dynamic poster screenshot if html2canvas available

    const setMeta = (id, attr, val) => {
      let el = document.getElementById(id);
      if (!el) { el = document.createElement('meta'); el.id = id; document.head.appendChild(el); }
      el.setAttribute(attr, val);
    };
    const setMetaName = (name, val) => {
      let el = document.querySelector(`meta[name="${name}"]`);
      if (!el) { el = document.createElement('meta'); el.setAttribute('name', name); document.head.appendChild(el); }
      el.setAttribute('content', val);
    };

    setMeta('ogTitle', 'content', title + ' | ' + CONFIG.siteName);
    setMeta('ogDesc',  'content', desc.substring(0, 160));
    setMeta('ogUrl',   'content', pageUrl);
    setMetaName('twitter:title', title);
    setMetaName('twitter:description', desc.substring(0, 160));
    // og:image — set to static for now
    let ogImg = document.querySelector('meta[property="og:image"]');
    if (!ogImg) { ogImg = document.createElement('meta'); ogImg.setAttribute('property','og:image'); document.head.appendChild(ogImg); }
    ogImg.setAttribute('content', imgUrl);
  }

  /* ══════════════════════════════════════
     7. MAIN ENGINE
  ══════════════════════════════════════ */
  async function run() {
    const container = document.getElementById(CONFIG.posterContainerId);
    if (!container) return; // Not on a job page

    const slug = getCurrentSlug();
    if (!slug) return; // No slug detected

    const pageUrl = window.location.href.split('?')[0].split('#')[0];

    // Show skeleton immediately
    showSkeleton(container);

    let jobData = null;

    // Strategy 1: Fast — try loading individual job file
    jobData = await tryLoadJobFile(slug);

    // Strategy 2: Search full JSON files
    if (!jobData) {
      jobData = await searchInFullData(slug);
    }

    hideSkeleton(container);

    if (!jobData) {
      // No job found - clean exit (don't show error to user)
      container.innerHTML = '';
      return;
    }

    // Build the poster
    if (!window.TSJPosterTemplate) {
      console.error('[PosterEngine] dynamic-template.js not loaded');
      return;
    }

    const html = window.TSJPosterTemplate.build(jobData, slug, pageUrl);
    container.innerHTML = html;

    // Init QR code
    window.TSJPosterTemplate.initQR(pageUrl);

    // Inject OG meta
    injectOGMeta(jobData, pageUrl);

    // Expose for download button
    window.TSJPoster = window.TSJPosterTemplate;
    window.TSJPoster._currentData = jobData;
  }

  /* ══════════════════════════════════════
     8. BOOTSTRAP
  ══════════════════════════════════════ */
  function init() {
    // Lazy: wait for the container to be available
    if (document.getElementById(CONFIG.posterContainerId)) {
      run();
    } else if (document.readyState !== 'complete') {
      document.addEventListener('DOMContentLoaded', run, { once: true });
    } else {
      // Observe for container insertion (in case of dynamic rendering)
      const obs = new MutationObserver(() => {
        if (document.getElementById(CONFIG.posterContainerId)) {
          obs.disconnect();
          run();
        }
      });
      obs.observe(document.body || document.documentElement, { childList: true, subtree: true });
    }
  }

  // Expose public API
  window.TSJPosterEngine = { run, init, getSlug: getCurrentSlug };

  init();

})(window, document);
