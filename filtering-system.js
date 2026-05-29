/**
 * ══════════════════════════════════════════════════════════════════════
 *  TOP SARKARI JOBS — Filtering System v5.0
 *  Category / State / Education / Tag based job filtering
 * ══════════════════════════════════════════════════════════════════════
 *
 *  STEP 8 IMPLEMENTATION:
 *    jobs.filter(job => job.tags.includes("10th"))
 *    jobs.filter(job => job.category.includes("railway"))
 *    jobs.filter(job => job.state.includes("haryana"))
 *    jobs.filter(job => job.type.includes("admit-card"))
 *
 *  Shows: title, short info, link → main job page (/data/jobs/{slug}/)
 *  Does NOT generate duplicate HTML pages.
 *
 *  USAGE:
 *    <!-- Category listing page -->
 *    <div id="job-filter-root"
 *         data-mode="category"
 *         data-value="Railway_Jobs"
 *         data-max="100">
 *    </div>
 *    <script src="/filtering-system.js?v=5.0" defer></script>
 *
 *  data-mode values: "category" | "state" | "tag" | "education" | "search"
 *  data-value: the filter value
 *  data-max: max items to show (default 50)
 *
 * ══════════════════════════════════════════════════════════════════════
 */
(function () {
  'use strict';

  const INDEX_URL = '/data-jobs-index.json';

  /* ── Styles ── */
  if (!document.getElementById('tsj-filter-css')) {
    const s = document.createElement('style');
    s.id = 'tsj-filter-css';
    s.textContent = `
    .tjf-wrap{font-family:inherit;}
    .tjf-header{display:flex;align-items:center;justify-content:space-between;padding:10px 0;margin-bottom:12px;border-bottom:2px solid #e2e8f0;}
    .tjf-count{font-size:.8rem;color:#64748b;background:#f1f5f9;border-radius:20px;padding:3px 10px;}
    .tjf-search{width:100%;padding:8px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:.85rem;margin-bottom:12px;outline:none;}
    .tjf-search:focus{border-color:#1d4ed8;box-shadow:0 0 0 2px #dbeafe;}
    .tjf-sort{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;}
    .tjf-sort-btn{padding:4px 10px;border:1px solid #e2e8f0;border-radius:6px;font-size:.73rem;cursor:pointer;background:#fff;color:#374151;}
    .tjf-sort-btn.active{background:#1d4ed8;color:#fff;border-color:#1d4ed8;}
    .tjf-grid{display:grid;grid-template-columns:1fr;gap:8px;}
    .tjf-card{border:1px solid #e2e8f0;border-radius:8px;padding:11px 14px;background:#fff;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;transition:box-shadow .15s;}
    .tjf-card:hover{box-shadow:0 2px 8px rgba(0,0,0,.1);}
    .tjf-card-left{flex:1;min-width:0;}
    .tjf-card-title{font-size:.86rem;font-weight:700;color:#0f172a;text-decoration:none;line-height:1.4;display:block;}
    .tjf-card-title:hover{color:#1d4ed8;}
    .tjf-card-meta{font-size:.73rem;color:#64748b;margin-top:4px;display:flex;flex-wrap:wrap;gap:6px;}
    .tjf-badge{display:inline-flex;align-items:center;gap:3px;background:#f1f5f9;border-radius:4px;padding:2px 7px;font-size:.7rem;}
    .tjf-badge.last-date{background:#fef3c7;color:#92400e;}
    .tjf-badge.vacancies{background:#d1fae5;color:#065f46;}
    .tjf-badge.location{background:#ede9fe;color:#5b21b6;}
    .tjf-view-btn{background:#1d4ed8;color:#fff;padding:6px 14px;border-radius:6px;font-size:.73rem;font-weight:700;text-decoration:none;flex-shrink:0;white-space:nowrap;}
    .tjf-view-btn:hover{background:#1e40af;}
    .tjf-empty{text-align:center;padding:32px;color:#64748b;font-size:.85rem;}
    .tjf-load-more{display:block;width:100%;padding:10px;border:2px solid #1d4ed8;border-radius:8px;background:#fff;color:#1d4ed8;font-size:.82rem;font-weight:700;cursor:pointer;margin-top:12px;text-align:center;}
    .tjf-load-more:hover{background:#dbeafe;}
    .tjf-spinner{text-align:center;padding:24px;color:#64748b;font-size:.8rem;}
    `;
    document.head.appendChild(s);
  }

  /* ── Utilities ── */
  function esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function jobUrl(slug) { return '/data/jobs/' + slug + '/'; }

  /* ── Render a single job card ── */
  function renderCard(job) {
    const lastDateBadge = job.lastDate
      ? `<span class="tjf-badge last-date">📅 ${esc(job.lastDate)}</span>` : '';
    const vacBadge = job.vacancies
      ? `<span class="tjf-badge vacancies">👥 ${esc(job.vacancies)}</span>` : '';
    const locBadge = job.location && job.location !== 'India'
      ? `<span class="tjf-badge location">📍 ${esc(job.location.slice(0,30))}</span>` : '';
    return `
    <div class="tjf-card">
      <div class="tjf-card-left">
        <a href="${jobUrl(job.url ? job.url.match(/\/data\/jobs\/([^\/]+)/)?.[1] || '' : (job.slug || ''))}"
           class="tjf-card-title">${esc(job.title)}</a>
        <div class="tjf-card-meta">
          ${lastDateBadge}${vacBadge}${locBadge}
        </div>
      </div>
      <a href="${jobUrl(job.url ? job.url.match(/\/data\/jobs\/([^\/]+)/)?.[1] || '' : (job.slug || ''))}"
         class="tjf-view-btn">View →</a>
    </div>`;
  }

  /* ── Main filter engine ── */
  class JobFilterEngine {
    constructor(container) {
      this.container = container;
      this.mode      = container.dataset.mode  || 'category';
      this.value     = container.dataset.value || '';
      this.max       = parseInt(container.dataset.max || '50');
      this.title     = container.dataset.title || '';
      this.allJobs   = [];
      this.filtered  = [];
      this.displayed = 20;
      this.sortBy    = 'default';
      this.query     = '';
    }

    async load() {
      this.container.innerHTML = '<div class="tjf-spinner">Loading jobs…</div>';
      try {
        const r   = await fetch(INDEX_URL);
        const idx = await r.json();
        this.allJobs = this._extract(idx);
        this._applyFilter();
        this._render();
      } catch (e) {
        this.container.innerHTML = '<div class="tjf-empty">Could not load jobs. Please refresh.</div>';
      }
    }

    _extract(idx) {
      // idx format: {slug: {title, cat, lastDate, location, tags, url}, ...}
      const jobs = [];
      for (const [slug, meta] of Object.entries(idx)) {
        jobs.push({
          slug    : slug,
          title   : meta.title || '',
          cat     : meta.cat   || '',
          lastDate: meta.lastDate || '',
          location: meta.location || '',
          tags    : meta.tags   || [],
          url     : meta.url    || jobUrl(slug),
          vacancies: meta.vacancies || '',
        });
      }
      return jobs;
    }

    _applyFilter() {
      let jobs = this.allJobs;
      const v  = this.value.toLowerCase();

      switch (this.mode) {
        case 'category':
          jobs = jobs.filter(j => j.cat.toLowerCase() === v || j.cat.toLowerCase().replace(/_/g,'-') === v);
          break;
        case 'state':
          jobs = jobs.filter(j => j.location.toLowerCase().includes(v));
          break;
        case 'tag':
          jobs = jobs.filter(j => j.tags.some(t => t.toLowerCase() === v));
          break;
        case 'education':
          jobs = jobs.filter(j => j.tags.some(t => t.toLowerCase().includes(v)) || j.cat.toLowerCase().includes(v));
          break;
        case 'search':
          jobs = this._search(jobs, v);
          break;
        default:
          break;
      }

      // Apply text search if query set
      if (this.query) {
        jobs = this._search(jobs, this.query);
      }

      // Sort
      if (this.sortBy === 'date') {
        jobs = jobs.slice().sort((a,b) => (b.lastDate||'').localeCompare(a.lastDate||''));
      } else if (this.sortBy === 'title') {
        jobs = jobs.slice().sort((a,b) => a.title.localeCompare(b.title));
      }

      this.filtered = jobs.slice(0, this.max);
    }

    _search(jobs, q) {
      if (!q) return jobs;
      const words = q.toLowerCase().split(/\s+/).filter(Boolean);
      return jobs.filter(j => {
        const text = (j.title + ' ' + j.location + ' ' + j.tags.join(' ')).toLowerCase();
        return words.every(w => text.includes(w));
      });
    }

    _render() {
      const show = this.filtered.slice(0, this.displayed);
      const total = this.filtered.length;

      const html = `
      <div class="tjf-wrap">
        <div class="tjf-header">
          <strong>${esc(this.title || this.value)}</strong>
          <span class="tjf-count">${total} jobs</span>
        </div>
        <input type="text" class="tjf-search" placeholder="Search within these jobs…"
               id="tjf-search-${Date.now()}" value="${esc(this.query)}"/>
        <div class="tjf-sort">
          <button class="tjf-sort-btn ${this.sortBy==='default'?'active':''}" data-sort="default">Latest</button>
          <button class="tjf-sort-btn ${this.sortBy==='date'?'active':''}"    data-sort="date">By Last Date</button>
          <button class="tjf-sort-btn ${this.sortBy==='title'?'active':''}"   data-sort="title">A–Z</button>
        </div>
        <div class="tjf-grid">
          ${show.map(renderCard).join('') || '<div class="tjf-empty">No jobs found for this filter.</div>'}
        </div>
        ${this.displayed < total ? `<button class="tjf-load-more">Load More (${total - this.displayed} remaining)</button>` : ''}
      </div>`;

      this.container.innerHTML = html;
      this._bindEvents();
    }

    _bindEvents() {
      // Search input
      const inp = this.container.querySelector('.tjf-search');
      if (inp) {
        inp.addEventListener('input', () => {
          this.query    = inp.value;
          this.displayed = 20;
          this._applyFilter();
          this._render();
        });
      }

      // Sort buttons
      this.container.querySelectorAll('.tjf-sort-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          this.sortBy   = btn.dataset.sort;
          this.displayed = 20;
          this._applyFilter();
          this._render();
        });
      });

      // Load more
      const lm = this.container.querySelector('.tjf-load-more');
      if (lm) {
        lm.addEventListener('click', () => {
          this.displayed += 20;
          this._render();
        });
      }
    }
  }

  /* ── Auto-init all filter containers ── */
  function initAll() {
    document.querySelectorAll('[id="job-filter-root"], .job-filter-root, [data-mode]').forEach(el => {
      if (el.__tjfInit) return;
      el.__tjfInit = true;
      new JobFilterEngine(el).load();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  /* Expose */
  window.TSJ = window.TSJ || {};
  window.TSJ.JobFilterEngine = JobFilterEngine;

})();
