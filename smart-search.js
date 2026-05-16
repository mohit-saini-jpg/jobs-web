/**
 * TOP SARKARI JOBS — HERO SEARCH v3.0
 * ─────────────────────────────────────
 * Data sources (ONLY these 4 files):
 *   1. merged_sarkari_data.json
 *   2. Complete_Jobs_Full_Data.json
 *   3. state-jobs-data.json
 *   4. dailyupdates.json  (only "TOP Headlines Today" section)
 *
 * Every item in index must have url starting with "job.html"
 * External URLs are NEVER added to index.
 * tsjSearchIndex from script.js is BLOCKED.
 */
(function () {
  'use strict';

  const MAX_SUGGEST = 8;
  const DEBOUNCE_MS = 180;
  const SEARCH_PAGE = 'search.html';

  /* ── INDEX ── */
  let INDEX = [];
  let indexReady = false;

  /* ── BLOCK tsjSearchIndex — script.js ka koi bhi data nahi aayega ── */
  function blockTsjSearchIndex() {
    try {
      const sink = [];
      Object.defineProperty(window, 'tsjSearchIndex', {
        get: () => sink,
        set: () => {},
        configurable: false,
      });
    } catch(e) {
      // Already defined — overwrite with no-op proxy
      window.tsjSearchIndex = new Proxy([], {
        set: () => true,
        get: (t, p) => t[p],
      });
    }
    console.log('[search] tsjSearchIndex BLOCKED');
  }

  /* ── SLUGIFY ── */
  function slugify(raw) {
    return String(raw || '')
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/[\s-]+/g, '-')
      .slice(0, 120)
      .replace(/^-+|-+$/g, '') || '';
  }

  /* ── BUILD INTERNAL URL ── */
  function buildUrl(slug, section) {
    if (!slug) return '';
    let u = 'job.html?slug=' + encodeURIComponent(slug);
    if (section) u += '&section=' + encodeURIComponent(section);
    return u;
  }

  /* ── VALIDATE: must be internal job.html link ── */
  function isValid(item) {
    if (!item.title || item.title.length < 4) return false;
    if (!item.url || !item.url.startsWith('job.html')) return false;
    return true;
  }

  /* ── FETCH JSON ── */
  function fetchJson(file) {
    return fetch(file)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .catch(e => { console.warn('[search] Failed:', file, e.message); return null; });
  }

  /* ── PROCESS: merged_sarkari_data.json ── */
  function processMerged(data) {
    const out = [];
    const jobs = Array.isArray(data.jobs) ? data.jobs : [];
    jobs.forEach(job => {
      const bd    = job.basic_details || {};
      const title = String(job.title || bd.job_title || job.post_name || '').trim();
      if (!title) return;
      const rawSlug = job.slug || slugify(title);
      if (!rawSlug) return;
      const mode   = (job.apply_mode || bd.application_mode || '').toLowerCase();
      const prefix = mode === 'offline' ? 'offline-' : '';
      const url    = buildUrl(prefix + rawSlug, 'Sarkari Jobs');
      const org    = String(job.organization || bd.organization_name || job.board_name || '').trim();
      const qual   = String(job.qualification || bd.qualification || '').trim();
      const state  = String(job.state || 'All India').trim();
      const dates  = job.important_dates || {};
      out.push({ title, url, dept: org, qual, state, cat: 'Sarkari Jobs',
        lastDate: String(dates.last_date || dates.last_date_to_apply || '').trim(),
        tags: [title, org, qual, state, 'sarkari naukri government job 2026'].join(' ') });
    });
    return out;
  }

  /* ── PROCESS: Complete_Jobs_Full_Data.json ── */
  const CAT_META = {
    Latest_Notifications:'Latest', '10TH_Pass':'10th Pass', '8TH_Pass':'8th Pass',
    '12TH_Pass':'12th Pass', Diploma:'Diploma', ITI:'ITI', B_Tech_BE:'B.Tech',
    B_Com:'B.Com', Any_Graduate:'Graduate', Any_Post_Graduate:'Post Graduate',
    Railway_Jobs:'Railway', Police_Defence:'Police', Teaching_Faculty:'Teaching',
    Bank_Jobs:'Bank', Medical_Hospital:'Medical', Last_Date_Reminder:'Latest',
    SSC_Jobs:'SSC', UPSC_Jobs:'UPSC', Haryana_Jobs:'Haryana', Defence_Jobs:'Defence',
  };

  function processComplete(data) {
    const out = [];
    if (!data || typeof data !== 'object' || Array.isArray(data)) return out;
    Object.entries(data).forEach(([catKey, arr]) => {
      if (!Array.isArray(arr)) return;
      const cat = CAT_META[catKey] || catKey;
      arr.forEach(job => {
        const bd    = job.basic_details || {};
        const title = String(job.title || bd.job_title || job.post_name || '').trim();
        if (!title) return;
        const rawSlug = job.slug || slugify(title);
        if (!rawSlug) return;
        const mode   = (job.apply_mode || bd.application_mode || '').toLowerCase();
        const prefix = mode === 'offline' ? 'offline-' : '';
        const url    = buildUrl(prefix + rawSlug, cat + ' Jobs');
        const org    = String(job.organization || bd.organization_name || '').trim();
        const qual   = cat;
        const dates  = job.important_dates || {};
        out.push({ title, url, dept: org, qual, state: String(job.state || 'All India').trim(),
          cat, lastDate: String(dates.last_date || dates.last_date_to_apply || '').trim(),
          tags: [title, org, cat, 'sarkari naukri 2026', 'government job'].join(' ') });
      });
    });
    return out;
  }

  /* ── PROCESS: state-jobs-data.json ── */
  function processStateJobs(data) {
    const out = [];
    const secs = Array.isArray(data.sections) ? data.sections : Array.isArray(data) ? data : [];
    secs.forEach(sec => {
      const secTitle = String(sec.title || sec.id || '').trim();
      const secState = String(sec.state || '').trim();
      (sec.items || []).forEach(item => {
        const title = String(item.name || item.title || '').trim();
        if (!title) return;
        const detail = item.detail || {};
        const bd     = detail.basic_details || {};
        const rawSlug = slugify(bd.job_title || title);
        if (!rawSlug) return;
        const mode   = (bd.application_mode || '').toLowerCase();
        const prefix = mode.includes('offline') ? 'offline-' : '';
        const url    = buildUrl(prefix + rawSlug, secTitle);
        const org    = String(item.board || bd.organization_name || secTitle).trim();
        const qual   = String(item.qualification || bd.qualification || '').trim();
        const dates  = detail.important_dates || {};
        out.push({ title, url, dept: org, qual, state: secState || 'All India', cat: 'State Jobs',
          lastDate: String(item.lastDate || item.date || dates.last_date_to_apply || '').trim(),
          tags: [title, org, qual, secTitle, secState, 'state jobs sarkari 2026'].filter(Boolean).join(' ') });
      });
    });
    return out;
  }

  /* ── PROCESS: dailyupdates.json — ONLY whitelisted sections, ONLY slug-based items ── */
  const DAILY_WHITELIST = new Set(['top headlines today','top headlines','today headlines','today jobs','latest jobs today']);

  function processDailyUpdates(data) {
    const out = [];
    const secs = Array.isArray(data.sections) ? data.sections : Array.isArray(data) ? data : [];
    secs.forEach(sec => {
      const secTitle = String(sec.title || sec.id || '').trim();
      if (!DAILY_WHITELIST.has(secTitle.toLowerCase())) {
        console.log('[search] dailyupdates skip section:', secTitle);
        return;
      }
      (sec.items || []).forEach(item => {
        const title = String(item.name || item.title || '').trim();
        if (!title || !item.slug) return; // MUST have slug
        const url = buildUrl(item.slug, secTitle);
        out.push({ title, url, dept: secTitle, qual: '', state: 'All India', cat: 'Latest Job',
          lastDate: String(item.date || item.last_date || '').trim(),
          tags: [title, secTitle, 'sarkari naukri 2026 latest'].join(' ') });
      });
    });
    return out;
  }

  /* ── ADD TO INDEX (with dedup + validation) ── */
  function addToIndex(items) {
    const seen  = new Set(INDEX.map(i => i.url));
    let added = 0, blocked = 0;
    items.forEach(item => {
      if (!isValid(item))            { blocked++; return; }
      if (seen.has(item.url))        { return; }
      seen.add(item.url);
      INDEX.push(item);
      added++;
    });
    if (blocked) console.log('[search] Blocked', blocked, 'invalid/external items');
    console.log('[search] +' + added + ' items | Total:', INDEX.length);
  }

  /* ── LOAD ALL DATA ── */
  function loadAllData() {
    // Phase 1: fast
    Promise.all([
      fetchJson('merged_sarkari_data.json').then(d => d && addToIndex(processMerged(d))),
      fetchJson('dailyupdates.json').then(d => d && addToIndex(processDailyUpdates(d))),
    ]).then(() => {
      indexReady = true;
      refreshActive();
      console.log('[search] Phase 1 done. Index:', INDEX.length);
    });

    // Phase 2: state jobs
    fetchJson('state-jobs-data.json').then(d => {
      if (d) { addToIndex(processStateJobs(d)); refreshActive(); }
    });

    // Phase 3: heavy, delayed
    setTimeout(() => {
      fetchJson('Complete_Jobs_Full_Data.json').then(d => {
        if (d) { addToIndex(processComplete(d)); refreshActive(); }
        console.log('[search] Phase 3 done. Index:', INDEX.length);
      });
    }, 2000);
  }

  /* ── SEARCH ── */
  const STOP = new Set(['recruitment','2026','2025','apply','online','offline','notification',
    'for','and','the','of','to','in','a','an','is','are','with','posts','post','form','exam',
    'board','india','all','bharti','vacancy','job','latest','new','official','government','govt']);

  function doSearch(query) {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const words = q.split(/\s+/).filter(w => w.length >= 1);
    const mw    = words.filter(w => w.length >= 2 && !STOP.has(w));

    return INDEX.map(item => {
      const t  = (item.title || '').toLowerCase();
      const d  = (item.dept  || '').toLowerCase();
      const tg = (item.tags  || '').toLowerCase();
      const s  = (item.state || '').toLowerCase();
      const c  = (item.cat   || '').toLowerCase();
      const ql = (item.qual  || '').toLowerCase();
      let sc = 0;

      if (t.includes(q))          sc += 300;
      else if (t.startsWith(words[0])) sc += 100;

      mw.forEach(w => {
        if (t.includes(w))  sc += w.length >= 5 ? 60 : 30;
        if (d.includes(w))  sc += 15;
        if (tg.includes(w)) sc += 10;
        if (s.includes(w))  sc += 12;
        if (c.includes(w))  sc += 8;
        if (ql.includes(w)) sc += 8;
      });

      if (words.length >= 2 && words.every(w => t.includes(w))) sc += 80;

      return sc >= 8 ? { ...item, _sc: sc } : null;
    }).filter(Boolean).sort((a, b) => b._sc - a._sc);
  }

  /* ── HELPERS ── */
  function esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function highlight(text, q) {
    const t = String(text||'');
    if (!q) return esc(t);
    try {
      const rx = new RegExp('(' + q.trim().replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + ')', 'gi');
      return esc(t).replace(rx, '<mark>$1</mark>');
    } catch { return esc(t); }
  }

  /* ── DROPDOWN ── */
  let dropEl = null, activeIdx = -1, curResults = [];

  function getDropEl(anchor) {
    if (!dropEl) {
      dropEl = document.createElement('div');
      dropEl.id = 'tsj-drop';
      dropEl.setAttribute('role','listbox');
      document.body.appendChild(dropEl);
    }
    const r = anchor.getBoundingClientRect();
    Object.assign(dropEl.style, {
      position:'fixed', top:(r.bottom+4)+'px', left:r.left+'px',
      width:r.width+'px', maxHeight:'430px', overflowY:'auto',
      background:'#fff', border:'1px solid #cbd5e1', borderRadius:'10px',
      boxShadow:'0 8px 32px rgba(13,34,87,.18)', zIndex:'99999', display:'block',
    });
    return dropEl;
  }

  function closeDrop() {
    if (dropEl) dropEl.style.display = 'none';
    activeIdx = -1; curResults = [];
  }

  function showDrop(anchor, q, results) {
    const drop = getDropEl(anchor);
    curResults = results; activeIdx = -1;
    if (!results.length) {
      drop.innerHTML = `<div style="padding:16px 18px;color:#64748b;font-size:.94rem;">
        "<strong>${esc(q)}</strong>" ke liye koi job nahi mili</div>`;
      return;
    }
    const shown = results.slice(0, MAX_SUGGEST);
    drop.innerHTML = shown.map((item, i) => `
      <a class="tsj-si" href="${esc(item.url)}" data-idx="${i}">
        <span class="tsj-si-ic"><i class="fa-solid fa-briefcase"></i></span>
        <span class="tsj-si-body">
          <span class="tsj-si-title">${highlight(item.title, q)}</span>
          <span class="tsj-si-meta">${esc(item.dept||item.cat||'Sarkari Job')}${item.state&&item.state!=='All India'?' · '+esc(item.state):''}${item.lastDate?' | '+esc(item.lastDate):''}</span>
        </span>
        <i class="fa-solid fa-arrow-right tsj-arr"></i>
      </a>`).join('') +
      (results.length > MAX_SUGGEST ? `<a class="tsj-more" href="${SEARCH_PAGE}?q=${encodeURIComponent(q)}">
        <i class="fa-solid fa-magnifying-glass"></i> "${esc(q)}" ke sabhi ${results.length} results dekhein</a>` : '');

    drop.querySelectorAll('.tsj-si').forEach(el => {
      el.addEventListener('mousedown', e => e.preventDefault());
      el.addEventListener('click', e => { e.preventDefault(); window.location.href = el.href; });
    });
  }

  function setActive(idx) {
    if (!dropEl) return;
    dropEl.querySelectorAll('.tsj-si').forEach((el,i) => el.classList.toggle('tsj-active', i===idx));
  }

  /* ── HERO SEARCH ── */
  function refreshActive() {
    const inp = document.getElementById('heroSearch');
    if (inp && inp.value.trim()) inp.dispatchEvent(new Event('input'));
  }

  let _t = null;
  function debouncedSearch(inp) {
    clearTimeout(_t);
    _t = setTimeout(() => {
      const q = inp.value.trim();
      if (!q) { closeDrop(); return; }
      showDrop(inp, q, doSearch(q));
    }, DEBOUNCE_MS);
  }

  function setupHeroSearch() {
    const inp = document.getElementById('heroSearch');
    if (!inp) return;

    inp.addEventListener('input', () => debouncedSearch(inp));
    inp.addEventListener('focus', () => { if (inp.value.trim()) debouncedSearch(inp); });

    inp.addEventListener('keydown', e => {
      if (!dropEl || dropEl.style.display === 'none') return;
      const its = dropEl.querySelectorAll('.tsj-si');
      if (e.key === 'ArrowDown')  { e.preventDefault(); activeIdx = Math.min(activeIdx+1, its.length-1); setActive(activeIdx); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); activeIdx = Math.max(activeIdx-1, -1); setActive(activeIdx); }
      else if (e.key === 'Enter') {
        e.preventDefault();
        if (activeIdx >= 0 && curResults[activeIdx]) window.location.href = curResults[activeIdx].url;
        else { const q = inp.value.trim(); if (q) window.location.href = SEARCH_PAGE+'?q='+encodeURIComponent(q); }
      } else if (e.key === 'Escape') closeDrop();
    });

    // Search button
    ['heroSearchBtn'].concat([...document.querySelectorAll('[data-search-trigger]')].map(el=>el.id)).forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.addEventListener('click', e => {
        e.preventDefault();
        const q = inp.value.trim();
        if (q) window.location.href = SEARCH_PAGE+'?q='+encodeURIComponent(q);
      });
    });

    // Try form submit
    const form = inp.closest('form');
    if (form) form.addEventListener('submit', e => {
      e.preventDefault();
      const q = inp.value.trim();
      if (q) window.location.href = SEARCH_PAGE+'?q='+encodeURIComponent(q);
    });

    document.addEventListener('click', e => {
      if (!inp.contains(e.target) && (!dropEl || !dropEl.contains(e.target))) closeDrop();
    });
  }

  /* ── SEARCH PAGE ── */
  function setupSearchPage() {
    const container = document.getElementById('searchResultsContainer');
    if (!container) return;
    const q = (new URLSearchParams(location.search).get('q') || '').trim();
    if (!q) { container.innerHTML = '<p>Koi search query nahi mili.</p>'; return; }

    const inp = document.getElementById('heroSearch') || document.getElementById('siteSearchInput');
    if (inp) inp.value = q;

    function render() {
      const res = doSearch(q);
      if (!res.length) {
        container.innerHTML = `<p style="color:#64748b;padding:24px 0;">"<strong>${esc(q)}</strong>" ke liye koi job nahi mili.</p>`;
        return;
      }
      container.innerHTML = `
        <p style="color:#475569;font-weight:700;margin-bottom:12px;">${res.length} jobs mili — "<strong>${esc(q)}</strong>"</p>
        <div style="display:flex;flex-direction:column;gap:10px;">
          ${res.map(item => `<div class="tsj-result-card">
            <div class="tsj-rc-head">
              <span class="tsj-rc-icon"><i class="fa-solid fa-briefcase"></i></span>
              <div class="tsj-rc-info">
                <a class="tsj-rc-title" href="${esc(item.url)}">${highlight(item.title, q)}</a>
                ${item.dept?`<div class="tsj-rc-dept">${esc(item.dept)}</div>`:''}
              </div>
            </div>
            <div class="tsj-rc-meta-row">
              <span class="tsj-section-badge"><i class="fa-solid fa-layer-group"></i> ${esc(item.cat)}</span>
              ${item.state&&item.state!=='All India'?`<span><i class="fa-solid fa-location-dot"></i> ${esc(item.state)}</span>`:''}
              ${item.qual?`<span><i class="fa-solid fa-graduation-cap"></i> ${esc(item.qual)}</span>`:''}
              ${item.lastDate?`<span><i class="fa-regular fa-clock"></i> ${esc(item.lastDate)}</span>`:''}
            </div>
            <a class="tsj-rc-apply" href="${esc(item.url)}"><i class="fa-solid fa-arrow-right"></i> View Job</a>
          </div>`).join('')}
        </div>`;
    }

    if (indexReady) render();
    else {
      container.innerHTML = '<p style="color:#64748b;">Loading jobs...</p>';
      const t = setInterval(() => { if (indexReady) { clearInterval(t); render(); } }, 200);
    }
  }

  /* ── STYLES ── */
  function injectStyles() {
    if (document.getElementById('tsj-ss')) return;
    const s = document.createElement('style');
    s.id = 'tsj-ss';
    s.textContent = `
      #tsj-drop{font-family:inherit}
      .tsj-si{display:flex;align-items:center;gap:10px;padding:11px 16px;text-decoration:none;
        color:#1e293b;border-bottom:1px solid #f1f5f9;cursor:pointer;transition:background .12s}
      .tsj-si:last-of-type{border-bottom:none}
      .tsj-si:hover,.tsj-si.tsj-active{background:#eff6ff}
      .tsj-si-ic{width:32px;height:32px;border-radius:8px;background:#1a56db;color:#fff;
        display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.85rem}
      .tsj-si-body{flex:1;min-width:0}
      .tsj-si-title{display:block;font-size:.95rem;font-weight:600;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .tsj-si-title mark{background:#fef08a;color:#1e293b;border-radius:2px;padding:0 1px}
      .tsj-si-meta{display:block;font-size:.78rem;color:#64748b;margin-top:1px}
      .tsj-arr{color:#94a3b8;font-size:.8rem;flex-shrink:0}
      .tsj-more{display:flex;align-items:center;gap:8px;padding:11px 16px;font-size:.88rem;
        color:#1a56db;font-weight:600;text-decoration:none;background:#f8fafc;border-top:1px solid #e2e8f0}
      .tsj-more:hover{background:#eff6ff}
      .tsj-result-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;
        padding:14px 16px;transition:box-shadow .15s}
      .tsj-result-card:hover{box-shadow:0 4px 16px rgba(13,34,87,.1)}
      .tsj-rc-head{display:flex;align-items:flex-start;gap:10px;margin-bottom:8px}
      .tsj-rc-icon{width:36px;height:36px;border-radius:8px;background:#1a56db;color:#fff;
        display:flex;align-items:center;justify-content:center;flex-shrink:0}
      .tsj-rc-title{font-size:1rem;font-weight:700;color:#1a56db;text-decoration:none;line-height:1.3}
      .tsj-rc-title:hover{text-decoration:underline}
      .tsj-rc-title mark{background:#fef08a;color:#1e293b}
      .tsj-rc-dept{font-size:.82rem;color:#64748b;margin-top:2px}
      .tsj-rc-meta-row{display:flex;flex-wrap:wrap;gap:8px;font-size:.78rem;color:#64748b;margin-bottom:8px}
      .tsj-section-badge{background:#eff6ff;color:#1d4ed8;padding:2px 8px;border-radius:20px;font-weight:600}
      .tsj-rc-apply{display:inline-flex;align-items:center;gap:6px;background:#1a56db;color:#fff;
        padding:6px 14px;border-radius:6px;font-size:.82rem;font-weight:600;text-decoration:none}
      .tsj-rc-apply:hover{background:#1e40af}
    `;
    document.head.appendChild(s);
  }

  /* ── INIT ── */
  function init() {
    blockTsjSearchIndex(); // FIRST — before script.js can push anything
    injectStyles();
    loadAllData();
    setupHeroSearch();
    setupSearchPage();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

})();
