/**
 * ╔═══════════════════════════════════════════════════════════════════════════╗
 * ║     UNIVERSAL SCHEMA-FREE DYNAMIC JSON RENDERING ENGINE v2.0             ║
 * ║     Top Sarkari Jobs — Works for ALL page types, ALL JSON structures      ║
 * ╚═══════════════════════════════════════════════════════════════════════════╝
 *
 * HOW IT WORKS:
 *  1. Reads ANY JSON file — no hardcoded fields, no assumptions
 *  2. Auto-detects field types: URL, Array, Object, HTML, FAQ, Table, Date, etc.
 *  3. Maps each type to the correct UI component automatically
 *  4. Renders ALL keys — nothing is ever skipped
 *  5. Generates SEO meta, breadcrumbs, JSON-LD schema from any structure
 *  6. Future-proof: new JSON keys auto-render without code changes
 *
 * SUPPORTED JSON SOURCES:
 *  - Complete_Jobs_Full_Data.json  (jobs by category)
 *  - merged_sarkari_data.json      (sarkari result style jobs)
 *  - dailyupdates.json             (sections with items)
 *  - state-jobs-data.json          (state-wise jobs with detail objects)
 *  - jobs/data/*.json              (individual job JSON files)
 *  - Any future JSON structure     (auto-detected)
 */

;(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.UniversalRenderer = factory();
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════
     § 1  UTILITY HELPERS
  ═══════════════════════════════════════════════════════ */

  const safe = v => (v == null ? '' : String(v).trim());

  /** Convert any key/slug to a human-readable heading */
  function humanKey(key) {
    return safe(key)
      .replace(/_+/g, ' ')
      .replace(/-+/g, ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .replace(/\b\w/g, c => c.toUpperCase())
      .trim();
  }

  /** Is the value a valid URL? */
  function isUrl(v) {
    const s = safe(v);
    return /^(https?:\/\/|\/\/|www\.)/i.test(s) || /\.(gov\.in|nic\.in|edu\.in|com|org|net|in|io)(\/|$)/i.test(s);
  }

  /** Is the value HTML? */
  function isHtml(v) {
    return typeof v === 'string' && /<[a-z][\s\S]*>/i.test(v);
  }

  /** Is the value a date string? */
  function isDate(v) {
    if (typeof v !== 'string') return false;
    return /\d{1,2}[\-\/]\d{1,2}[\-\/]\d{2,4}/.test(v) ||
      /\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)/i.test(v) ||
      /\b20\d{2}\b/.test(v) && /date|deadline|start|end/i.test(v);
  }

  /** Is the value a salary? */
  function isSalary(v) {
    const s = safe(v);
    return /₹|rs\.?|inr|per\s*month|pay\s*scale|pay\s*band|grade\s*pay|level/i.test(s);
  }

  /** Format a date string to DD/MM/YYYY */
  function fmtDate(v) {
    const s = safe(v);
    let m = s.match(/^(\d{4})[\-\/](\d{1,2})[\-\/](\d{1,2})$/);
    if (m) return `${m[3].padStart(2,'0')}/${m[2].padStart(2,'0')}/${m[1]}`;
    m = s.match(/^(\d{1,2})[\-\/](\d{1,2})[\-\/](\d{4})$/);
    if (m) return `${m[1].padStart(2,'0')}/${m[2].padStart(2,'0')}/${m[3]}`;
    return s;
  }

  /** Normalize URL — add protocol if missing */
  function normalizeUrl(v) {
    const s = safe(v);
    if (!s) return '';
    if (/^(https?:\/\/|mailto:|tel:)/i.test(s)) return s;
    if (s.startsWith('#') || s.startsWith('/') || s.startsWith('?')) return s;
    if (/\.(gov\.in|nic\.in|com|org|net|in|io)(\/|$)/i.test(s)) return 'https://' + s.replace(/^\/+/, '');
    return s;
  }

  /** Categorize a link by its title for button styling */
  function categorizeLinkTitle(title) {
    const t = safe(title).toLowerCase();
    if (/apply\s*online|apply\s*link|apply\s*form|registration|apply\s*now/i.test(t))
      return { icon: 'fa-paper-plane', cls: 'ure-btn-green', sub: 'Apply Now' };
    if (/admit\s*card|hall\s*ticket|call\s*letter|e-admit/i.test(t))
      return { icon: 'fa-id-card', cls: 'ure-btn-orange', sub: 'Download Now' };
    if (/result|merit\s*list|score\s*card|cut.?off/i.test(t))
      return { icon: 'fa-trophy', cls: 'ure-btn-orange', sub: 'View Result' };
    if (/answer\s*key|response\s*sheet/i.test(t))
      return { icon: 'fa-key', cls: 'ure-btn-blue', sub: 'Download Now' };
    if (/notification|official\s*notif|advert|news/i.test(t))
      return { icon: 'fa-file-pdf', cls: 'ure-btn-blue', sub: 'View PDF' };
    if (/syllabus|exam\s*pattern|curriculum/i.test(t))
      return { icon: 'fa-book-open', cls: 'ure-btn-blue', sub: 'Download Now' };
    if (/official\s*website|official\s*portal|website/i.test(t))
      return { icon: 'fa-globe', cls: 'ure-btn-red', sub: 'Visit Now' };
    if (/download|pdf|form/i.test(t))
      return { icon: 'fa-file-arrow-down', cls: 'ure-btn-blue', sub: 'Download' };
    if (/login|candidate\s*login|dashboard/i.test(t))
      return { icon: 'fa-right-to-bracket', cls: 'ure-btn-green', sub: 'Login' };
    return { icon: 'fa-link', cls: 'ure-btn-blue', sub: 'Click Here' };
  }

  /** Detect if array of objects looks like table data */
  function isTableArray(arr) {
    if (!Array.isArray(arr) || arr.length === 0) return false;
    return arr.every(item => typeof item === 'object' && item !== null && !Array.isArray(item));
  }

  /** Detect if array looks like FAQ */
  function isFaqArray(arr) {
    if (!Array.isArray(arr) || arr.length === 0) return false;
    return arr.some(item =>
      item && typeof item === 'object' &&
      (('question' in item && 'answer' in item) ||
       ('q' in item && 'a' in item) ||
       ('faq' in item))
    );
  }

  /** Check if a key should be treated as important links section */
  function isLinksKey(key) {
    return /links?|url|href|apply|download|website|portal|pdf|notification/i.test(key);
  }

  /** Check if key is SEO metadata (skip rendering) */
  function isSeoKey(key) {
    return /^(seo|meta|canonical|og_|twitter_|schema|structured)/i.test(key);
  }

  /** Get icon for a section based on its key */
  function sectionIcon(key) {
    const k = key.toLowerCase();
    if (/date|timeline|schedule|deadline/i.test(k)) return 'fa-calendar-days';
    if (/fee|payment|cost|charge/i.test(k)) return 'fa-indian-rupee-sign';
    if (/age|limit|eligib/i.test(k)) return 'fa-user-clock';
    if (/qualif|education|degree/i.test(k)) return 'fa-graduation-cap';
    if (/vacancy|post|position/i.test(k)) return 'fa-users';
    if (/salary|pay|wage|stipend/i.test(k)) return 'fa-money-bill-wave';
    if (/selection|process|stage/i.test(k)) return 'fa-list-check';
    if (/exam|test|paper|syllabus/i.test(k)) return 'fa-file-pen';
    if (/physical|fitness|medical/i.test(k)) return 'fa-heart-pulse';
    if (/how.*apply|application|procedure|steps/i.test(k)) return 'fa-circle-info';
    if (/link|url|apply|download|website/i.test(k)) return 'fa-link';
    if (/faq|question/i.test(k)) return 'fa-circle-question';
    if (/instruction|note|important/i.test(k)) return 'fa-triangle-exclamation';
    if (/detail|info|about|overview/i.test(k)) return 'fa-circle-info';
    if (/category|section/i.test(k)) return 'fa-tag';
    if (/result|merit|score/i.test(k)) return 'fa-trophy';
    if (/admit|card|ticket/i.test(k)) return 'fa-id-card';
    if (/scheme|yojana|govt/i.test(k)) return 'fa-landmark';
    return 'fa-chevron-right';
  }

  /** Get accent color for a section */
  function sectionColor(key) {
    const k = key.toLowerCase();
    if (/date|timeline|deadline/i.test(k)) return '#0ea5e9';
    if (/fee|payment/i.test(k)) return '#f59e0b';
    if (/age/i.test(k)) return '#8b5cf6';
    if (/qualif|education/i.test(k)) return '#10b981';
    if (/vacancy|post/i.test(k)) return '#3b82f6';
    if (/salary|pay/i.test(k)) return '#22c55e';
    if (/selection/i.test(k)) return '#6366f1';
    if (/exam|syllabus/i.test(k)) return '#0891b2';
    if (/link|apply/i.test(k)) return '#4f46e5';
    if (/faq/i.test(k)) return '#7c3aed';
    if (/instruction|important/i.test(k)) return '#ef4444';
    return '#0ea5e9';
  }

  /* ═══════════════════════════════════════════════════════
     § 2  COMPONENT RENDERERS
     Each returns an HTML string. Type is auto-detected.
  ═══════════════════════════════════════════════════════ */

  const components = {

    /** Render a single primitive value */
    primitive(key, value) {
      const s = safe(value);
      if (!s) return '';
      if (isUrl(s)) {
        const cat = categorizeLinkTitle(key);
        const href = normalizeUrl(s);
        return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="ure-btn ${cat.cls}">
          <i class="fa-solid ${cat.icon}"></i>
          <span class="ure-btn-label">${humanKey(key)}</span>
          <span class="ure-btn-sub">${cat.sub}</span>
        </a>`;
      }
      if (isSalary(s)) {
        return `<div class="ure-kv-item ure-salary">
          <div class="ure-kv-label"><i class="fa-solid fa-indian-rupee-sign"></i> ${humanKey(key)}</div>
          <div class="ure-kv-val ure-salary-val">${s}</div>
        </div>`;
      }
      const dateVal = isDate(s) ? fmtDate(s) : null;
      if (dateVal) {
        return `<div class="ure-kv-item ure-date-item">
          <div class="ure-kv-label"><i class="fa-solid fa-calendar-day"></i> ${humanKey(key)}</div>
          <div class="ure-kv-val ure-date-val">${dateVal}</div>
        </div>`;
      }
      return `<div class="ure-kv-item">
        <div class="ure-kv-label">${humanKey(key)}</div>
        <div class="ure-kv-val">${s}</div>
      </div>`;
    },

    /** Render HTML string safely */
    html(key, value) {
      return `<div class="ure-html-content">${value}</div>`;
    },

    /** Render a flat array of strings or URLs */
    list(key, arr) {
      if (!arr.length) return '';
      // Check if items are URLs → button list
      if (arr.every(item => typeof item === 'string' && isUrl(item))) {
        return arr.map((url, i) => {
          const href = normalizeUrl(url);
          const cat = categorizeLinkTitle(key + ' ' + (i + 1));
          return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="ure-btn ${cat.cls}">
            <i class="fa-solid ${cat.icon}"></i>
            <span class="ure-btn-label">${humanKey(key)} ${arr.length > 1 ? i+1 : ''}</span>
            <span class="ure-btn-sub">${cat.sub}</span>
          </a>`;
        }).join('');
      }
      // Steps/process — numbered if looks like steps
      const isSteps = /process|step|how|procedure|instruction|apply/i.test(key);
      if (isSteps) {
        return `<ol class="ure-steps-list">${arr.map(item =>
          `<li class="ure-step-item"><span class="ure-step-text">${safe(item)}</span></li>`
        ).join('')}</ol>`;
      }
      // Default bullet list
      return `<ul class="ure-list">${arr.map(item =>
        `<li class="ure-list-item"><i class="fa-solid fa-circle-check ure-list-icon"></i><span>${safe(item)}</span></li>`
      ).join('')}</ul>`;
    },

    /** Render array of objects as responsive table */
    table(key, arr) {
      if (!arr.length) return '';
      // Collect all unique column keys across all rows
      const colSet = new Set();
      arr.forEach(row => { if (row && typeof row === 'object') Object.keys(row).forEach(k => colSet.add(k)); });
      const cols = [...colSet];
      if (!cols.length) return '';
      return `<div class="ure-table-wrap">
        <table class="ure-table">
          <thead><tr>${cols.map(c => `<th>${humanKey(c)}</th>`).join('')}</tr></thead>
          <tbody>${arr.map(row => `<tr>${cols.map(c => {
            const v = row && row[c];
            const s = safe(v);
            const isRed = /total|grand\s*total/i.test(s) && /total/i.test(String(c));
            return `<td${isRed ? ' class="ure-td-total"' : ''}>${s || '—'}</td>`;
          }).join('')}</tr>`).join('')}</tbody>
        </table>
      </div>`;
    },

    /** Render FAQ accordion */
    faq(key, arr) {
      return `<div class="ure-faq-list">${arr.map((item, i) => {
        const q = safe(item.question || item.q || item.Q || '');
        const a = safe(item.answer || item.a || item.A || '');
        if (!q && !a) return '';
        return `<div class="ure-faq-item" id="faq-${i}">
          <button class="ure-faq-q" onclick="URE.toggleFaq(this)" aria-expanded="false">
            <span class="ure-faq-icon"><i class="fa-solid fa-circle-question"></i></span>
            <span class="ure-faq-text">${q}</span>
            <i class="fa-solid fa-chevron-down ure-faq-arrow"></i>
          </button>
          <div class="ure-faq-a" hidden>${isHtml(a) ? a : `<p>${a}</p>`}</div>
        </div>`;
      }).join('')}</div>`;
    },

    /** Render important links section (mixed object with URLs) */
    links(key, obj) {
      const buttons = [];
      function collectLinks(data, parentKey) {
        if (!data) return;
        if (typeof data === 'string' && isUrl(data)) {
          const href = normalizeUrl(data);
          const cat = categorizeLinkTitle(parentKey);
          buttons.push({ href, label: humanKey(parentKey), icon: cat.icon, cls: cat.cls, sub: cat.sub });
        } else if (Array.isArray(data)) {
          data.forEach((item, i) => {
            if (typeof item === 'string' && isUrl(item)) {
              const href = normalizeUrl(item);
              const cat = categorizeLinkTitle(parentKey);
              const label = data.length > 1 ? `${humanKey(parentKey)} (${i+1})` : humanKey(parentKey);
              buttons.push({ href, label, icon: cat.icon, cls: cat.cls, sub: cat.sub });
            } else if (item && typeof item === 'object') {
              const url = item.url || item.href || item.link || '';
              const title = item.title || item.name || item.label || parentKey;
              if (url && isUrl(url)) {
                const href = normalizeUrl(url);
                const cat = categorizeLinkTitle(title);
                buttons.push({ href, label: humanKey(title), icon: cat.icon, cls: cat.cls, sub: cat.sub });
              }
            }
          });
        } else if (data && typeof data === 'object') {
          Object.entries(data).forEach(([k, v]) => collectLinks(v, k));
        }
      }
      collectLinks(obj, key);
      if (!buttons.length) return '';
      const seen = new Set();
      return `<div class="ure-links-grid">${buttons.filter(b => {
        if (seen.has(b.href)) return false;
        seen.add(b.href);
        return true;
      }).map(b => `<a href="${b.href}" target="_blank" rel="noopener noreferrer" class="ure-btn ${b.cls}">
        <i class="fa-solid ${b.icon}"></i>
        <span class="ure-btn-label">${b.label}</span>
        <span class="ure-btn-sub">${b.sub}</span>
      </a>`).join('')}</div>`;
    },

    /** Render selection process as badge steps */
    selectionProcess(arr) {
      const steps = Array.isArray(arr) ? arr : [arr];
      return `<div class="ure-sel-steps">${steps.map(s =>
        `<div class="ure-sel-badge"><i class="fa-solid fa-check-circle"></i><span>${safe(s)}</span></div>`
      ).join('<div class="ure-sel-arrow"><i class="fa-solid fa-arrow-right"></i></div>')}</div>`;
    },

    /** Render a nested object as key-value grid */
    object(key, obj) {
      const entries = Object.entries(obj).filter(([, v]) => v != null && v !== '' && !(Array.isArray(v) && v.length === 0) && !(typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === 0));
      if (!entries.length) return '';
      return `<div class="ure-kv-grid">${entries.map(([k, v]) => {
        const s = safe(v);
        if (isUrl(s)) {
          const href = normalizeUrl(s);
          const cat = categorizeLinkTitle(k);
          return `<div class="ure-kv-item ure-kv-full"><a href="${href}" target="_blank" rel="noopener noreferrer" class="ure-btn ${cat.cls} ure-btn-inline"><i class="fa-solid ${cat.icon}"></i>${humanKey(k)}</a></div>`;
        }
        if (isSalary(s)) return `<div class="ure-kv-item ure-salary"><div class="ure-kv-label">${humanKey(k)}</div><div class="ure-kv-val ure-salary-val">${s}</div></div>`;
        const dateVal = isDate(s) ? fmtDate(s) : null;
        if (dateVal) return `<div class="ure-kv-item ure-date-item"><div class="ure-kv-label"><i class="fa-solid fa-calendar-day"></i> ${humanKey(k)}</div><div class="ure-kv-val ure-date-val">${dateVal}</div></div>`;
        if (isHtml(s)) return `<div class="ure-kv-item ure-kv-full"><div class="ure-kv-label">${humanKey(k)}</div><div class="ure-html-content">${s}</div></div>`;
        return `<div class="ure-kv-item"><div class="ure-kv-label">${humanKey(k)}</div><div class="ure-kv-val">${s || '—'}</div></div>`;
      }).join('')}</div>`;
    },

  };

  /* ═══════════════════════════════════════════════════════
     § 3  SMART DISPATCHER
     Auto-detects value type and dispatches to correct component
  ═══════════════════════════════════════════════════════ */

  function renderValue(key, value) {
    // Skip null/empty
    if (value == null || value === '') return '';
    if (Array.isArray(value) && value.length === 0) return '';
    if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) return '';

    // Skip SEO-only keys from display
    if (isSeoKey(key)) return '';

    // Links / URL objects
    if (isLinksKey(key) && typeof value === 'object') return components.links(key, value);

    // FAQ arrays
    if (isFaqArray(Array.isArray(value) ? value : [])) return components.faq(key, value);

    // Selection process
    if (/selection.*process|process.*selection/i.test(key) && Array.isArray(value))
      return components.selectionProcess(value);

    // Arrays
    if (Array.isArray(value)) {
      if (isTableArray(value)) return components.table(key, value);
      // Array of strings/primitives
      const flatArr = value.map(safe).filter(Boolean);
      if (flatArr.length) return components.list(key, flatArr.length === value.length ? flatArr : value);
      return '';
    }

    // Objects (nested)
    if (typeof value === 'object') return components.object(key, value);

    // HTML string
    if (isHtml(value)) return components.html(key, value);

    // Primitive
    return components.primitive(key, value);
  }

  /* ═══════════════════════════════════════════════════════
     § 4  SECTION WRAPPER
     Wraps rendered content in a styled card section
  ═══════════════════════════════════════════════════════ */

  function renderSection(key, value) {
    const content = renderValue(key, value);
    if (!content || !content.trim()) return '';

    const icon = sectionIcon(key);
    const color = sectionColor(key);
    const title = humanKey(key);
    const isLinkSec = isLinksKey(key) && typeof value === 'object';
    const isFaqSec = isFaqArray(Array.isArray(value) ? value : []);

    return `
    <div class="ure-section" data-key="${key}">
      <div class="ure-section-head" style="--sec-color:${color}">
        <span class="ure-section-icon"><i class="fa-solid ${icon}"></i></span>
        <h2 class="ure-section-title">${title}</h2>
      </div>
      <div class="ure-section-body ${isFaqSec ? 'ure-body-faq' : ''} ${isLinkSec ? 'ure-body-links' : ''}">
        ${content}
      </div>
    </div>`;
  }

  /* ═══════════════════════════════════════════════════════
     § 5  HERO / QUICK STATS GENERATOR
     Extracts key highlight data from any JSON structure
  ═══════════════════════════════════════════════════════ */

  function extractHeroData(data) {
    const hero = {
      title: '', org: '', posts: '', lastDate: '', applyMode: '',
      salary: '', shortInfo: '', category: '', postDate: ''
    };

    function deepSearch(obj, depth) {
      if (depth > 4 || !obj || typeof obj !== 'object') return;
      for (const [k, v] of Object.entries(obj)) {
        const kl = k.toLowerCase();
        const vs = safe(v);
        if (!hero.title && /job_title|title|name/i.test(kl) && typeof v === 'string' && v.length > 10) hero.title = vs;
        if (!hero.org && /org|organization|board|department|institute|company/i.test(kl) && typeof v === 'string') hero.org = vs;
        if (!hero.posts && /total_vac|vacancy|vacancies|total_post|posts?$/i.test(kl) && typeof v !== 'object') hero.posts = vs;
        if (!hero.lastDate && /last_date|closing|deadline/i.test(kl) && typeof v === 'string') hero.lastDate = fmtDate(vs);
        if (!hero.applyMode && /apply_mode|application_mode|mode/i.test(kl) && typeof v === 'string') hero.applyMode = vs;
        if (!hero.salary && isSalary(vs)) hero.salary = vs;
        if (!hero.shortInfo && /short_info|description|summary|snippet/i.test(kl) && typeof v === 'string' && v.length > 30) hero.shortInfo = vs;
        if (!hero.category && /category|type|job_type/i.test(kl) && typeof v === 'string') hero.category = vs;
        if (!hero.postDate && /post_date|posted_date|date/i.test(kl) && typeof v === 'string') hero.postDate = fmtDate(vs);
        if (v && typeof v === 'object') deepSearch(v, depth + 1);
      }
    }

    deepSearch(data, 0);
    return hero;
  }

  /** Build hero HTML from extracted data */
  function renderHero(hero, slug) {
    if (!hero.title) return '';
    const stats = [
      hero.org && { icon: 'fa-building', label: 'Organisation', val: hero.org },
      hero.posts && { icon: 'fa-users', label: 'Total Posts', val: hero.posts },
      hero.lastDate && { icon: 'fa-calendar-xmark', label: 'Last Date', val: hero.lastDate, red: true },
      hero.applyMode && { icon: 'fa-paper-plane', label: 'Apply Mode', val: hero.applyMode },
      hero.salary && { icon: 'fa-money-bill-wave', label: 'Salary', val: hero.salary },
    ].filter(Boolean);

    return `
    <div class="ure-hero">
      <div class="ure-hero-badges">
        ${hero.category ? `<span class="ure-badge ure-badge-cat">${hero.category}</span>` : ''}
        <span class="ure-badge ure-badge-new">🆕 New</span>
        ${hero.lastDate ? `<span class="ure-badge ure-badge-date">📅 Last Date: ${hero.lastDate}</span>` : ''}
      </div>
      <h1 class="ure-hero-title">${hero.title}</h1>
      ${hero.org ? `<p class="ure-hero-org"><i class="fa-solid fa-building"></i> ${hero.org}</p>` : ''}
      ${stats.length ? `
      <div class="ure-stats-grid">
        ${stats.map(s => `
        <div class="ure-stat-card ${s.red ? 'ure-stat-red' : ''}">
          <div class="ure-stat-icon"><i class="fa-solid ${s.icon}"></i></div>
          <div class="ure-stat-info">
            <div class="ure-stat-label">${s.label}</div>
            <div class="ure-stat-val">${s.val}</div>
          </div>
        </div>`).join('')}
      </div>` : ''}
      ${hero.shortInfo ? `<div class="ure-short-info"><i class="fa-solid fa-circle-info"></i> ${hero.shortInfo}</div>` : ''}
    </div>`;
  }

  /* ═══════════════════════════════════════════════════════
     § 6  SEO ENGINE
     Auto-generates all meta tags, schema, breadcrumbs
  ═══════════════════════════════════════════════════════ */

  function injectSEO(hero, slug, dataType) {
    const title = hero.title || humanKey(slug) || 'Sarkari Job Details';
    const desc = hero.shortInfo ||
      `${title} — Check eligibility, vacancies, last date, salary and how to apply on Top Sarkari Jobs.`;
    const canonUrl = `https://www.topsarkarijobs.com/${dataType}/${slug}/`;
    const fullTitle = `${title} | Top Sarkari Jobs`;

    // Title & meta
    document.title = fullTitle;
    const setMeta = (sel, attr, val) => { const el = document.querySelector(sel); if (el) el.setAttribute(attr, val); };
    setMeta('#metaDesc, meta[name="description"]', 'content', desc.slice(0, 160));
    setMeta('#canonicalTag, link[rel="canonical"]', 'href', canonUrl);
    setMeta('#ogTitle, meta[property="og:title"]', 'content', fullTitle);
    setMeta('#ogDesc, meta[property="og:description"]', 'content', desc.slice(0, 300));
    setMeta('#ogUrl, meta[property="og:url"]', 'content', canonUrl);
    setMeta('#twTitle, meta[name="twitter:title"]', 'content', fullTitle);
    setMeta('#twDesc, meta[name="twitter:description"]', 'content', desc.slice(0, 200));

    // JSON-LD JobPosting
    const isJob = /job|recruit|vacancy/i.test(dataType + ' ' + title);
    if (isJob) {
      const schema = {
        '@context': 'https://schema.org', '@type': 'JobPosting',
        title, description: desc,
        identifier: { '@type': 'PropertyValue', name: 'Top Sarkari Jobs', value: slug },
        datePosted: new Date().toISOString().split('T')[0],
        hiringOrganization: { '@type': 'Organization', name: hero.org || 'Government of India', sameAs: 'https://www.topsarkarijobs.com' },
        jobLocation: { '@type': 'Place', address: { '@type': 'PostalAddress', addressCountry: 'IN', addressRegion: 'India' } },
        employmentType: 'FULL_TIME', url: canonUrl
      };
      if (hero.lastDate) schema.validThrough = hero.lastDate;
      if (hero.posts && !isNaN(hero.posts)) schema.totalJobOpenings = parseInt(hero.posts);
      const el = document.getElementById('jobSchema') || document.createElement('script');
      el.type = 'application/ld+json'; el.id = 'jobSchema';
      el.textContent = JSON.stringify(schema);
      if (!document.getElementById('jobSchema')) document.head.appendChild(el);
    }

    // Breadcrumb schema
    const bcList = [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://www.topsarkarijobs.com/' },
      { '@type': 'ListItem', position: 2, name: humanKey(dataType), item: `https://www.topsarkarijobs.com/${dataType}/` },
      { '@type': 'ListItem', position: 3, name: title, item: canonUrl }
    ];
    const bcEl = document.getElementById('breadcrumbSchema') || document.createElement('script');
    bcEl.type = 'application/ld+json'; bcEl.id = 'breadcrumbSchema';
    bcEl.textContent = JSON.stringify({ '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: bcList });
    if (!document.getElementById('breadcrumbSchema')) document.head.appendChild(bcEl);

    return { title, desc, canonUrl };
  }

  /* ═══════════════════════════════════════════════════════
     § 7  BREADCRUMBS HTML
  ═══════════════════════════════════════════════════════ */

  function renderBreadcrumbs(hero, slug, dataType) {
    const title = hero.title || humanKey(slug);
    const shortTitle = title.length > 60 ? title.slice(0, 57) + '…' : title;
    return `
    <nav class="ure-breadcrumb" aria-label="Breadcrumb">
      <ol class="ure-bc-list">
        <li><a href="/"><i class="fa-solid fa-house"></i> Home</a></li>
        <li><i class="fa-solid fa-chevron-right"></i></li>
        <li><a href="/view.html?section=latest%20jobs">${humanKey(dataType)}</a></li>
        <li><i class="fa-solid fa-chevron-right"></i></li>
        <li aria-current="page">${shortTitle}</li>
      </ol>
    </nav>`;
  }

  /* ═══════════════════════════════════════════════════════
     § 8  MAIN PAGE RENDERER
     Renders ALL keys from ANY JSON structure
  ═══════════════════════════════════════════════════════ */

  /**
   * Renders a complete page from any JSON data object.
   * @param {Object|Array} data - The JSON data
   * @param {string} slug - URL slug
   * @param {string} dataType - 'jobs', 'results', 'admit-cards', etc.
   * @param {HTMLElement} container - DOM element to render into
   */
  function renderPage(data, slug, dataType, container) {
    if (!container) return;

    // Flatten if top-level is array with one item
    let pageData = data;
    if (Array.isArray(data) && data.length === 1) pageData = data[0];

    // Extract hero data
    const hero = extractHeroData(pageData);

    // Inject SEO
    const seoInfo = injectSEO(hero, slug, dataType);

    // Build sections from ALL keys
    const sections = [];

    // Determine the keys to render — handle flat vs nested structures
    let renderKeys = [];
    if (Array.isArray(pageData)) {
      // Data is array — render as table if uniform objects, else as list
      sections.push(renderSection('items', pageData));
    } else if (typeof pageData === 'object' && pageData !== null) {
      renderKeys = Object.keys(pageData);
    }

    // Render each key in order
    for (const key of renderKeys) {
      const value = pageData[key];
      // Skip empty
      if (value == null || value === '') continue;
      if (Array.isArray(value) && value.length === 0) continue;
      if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) continue;
      // Skip meta/seo keys from sections
      if (isSeoKey(key)) continue;
      // Skip the title/org if already in hero
      if (/^(job_title|title|name)$/i.test(key) && hero.title) continue;

      sections.push(renderSection(key, value));
    }

    const validSections = sections.filter(Boolean).join('');

    container.innerHTML = `
      ${renderBreadcrumbs(hero, slug, dataType)}
      ${renderHero(hero, slug)}
      <div class="ure-content">
        <div class="ure-main">
          ${validSections || '<div class="ure-empty">Content loading…</div>'}
        </div>
        <aside class="ure-sidebar">
          <div class="ure-sidebar-widget">
            <div class="ure-widget-head"><i class="fa-solid fa-fire"></i> Latest Jobs</div>
            <div id="ureSidebarLatest" class="ure-widget-body">
              <div class="ure-loading-pulse"></div>
            </div>
          </div>
        </aside>
      </div>`;

    // Load sidebar latest jobs async
    loadSidebarJobs(document.getElementById('ureSidebarLatest'));
  }

  /* ═══════════════════════════════════════════════════════
     § 9  SIDEBAR LOADER
  ═══════════════════════════════════════════════════════ */

  function loadSidebarJobs(el) {
    if (!el) return;
    fetch('/jobs-index.json').then(r => r.json()).then(data => {
      const items = Array.isArray(data) ? data.slice(0, 8) : [];
      if (!items.length) { el.innerHTML = '<p class="ure-muted">No jobs found.</p>'; return; }
      el.innerHTML = items.map(job => {
        const name = safe(job.name || job.title || job.job_title || '');
        const slug = safe(job.slug || job.id || '');
        const date = safe(job.lastDate || job.last_date || '');
        if (!name) return '';
        return `<a href="/jobs/${slug}/" class="ure-sidebar-item">
          <div class="ure-sidebar-title">${name.length > 70 ? name.slice(0,67)+'…' : name}</div>
          ${date ? `<div class="ure-sidebar-date"><i class="fa-solid fa-calendar-day"></i> ${fmtDate(date)}</div>` : ''}
        </a>`;
      }).filter(Boolean).join('');
    }).catch(() => {
      el.innerHTML = '<p class="ure-muted">Could not load jobs.</p>';
    });
  }

  /* ═══════════════════════════════════════════════════════
     § 10  JSON SOURCE READERS
     Auto-reads all 4 JSON sources and finds items by slug
  ═══════════════════════════════════════════════════════ */

  /**
   * Find a job/item by slug across all JSON data sources.
   * Returns { data, dataType, found }
   */
  async function findBySlug(slug) {
    const sources = [
      { file: '/Complete_Jobs_Full_Data.json', type: 'jobs',         reader: readCompleteJobsJson },
      { file: '/merged_sarkari_data.json',     type: 'jobs',         reader: readMergedSarkariJson },
      { file: '/state-jobs-data.json',          type: 'state-jobs',  reader: readStateJobsJson },
      { file: '/dailyupdates.json',             type: 'updates',     reader: readDailyUpdatesJson },
    ];

    // Also try direct slug JSON file
    try {
      const r = await fetch(`/jobs/data/${slug}.json`);
      if (r.ok) {
        const data = await r.json();
        return { data, dataType: 'jobs', found: true };
      }
    } catch (_) {}

    for (const src of sources) {
      try {
        const r = await fetch(src.file);
        if (!r.ok) continue;
        const raw = await r.json();
        const found = src.reader(raw, slug);
        if (found) return { data: found, dataType: src.type, found: true };
      } catch (_) {}
    }
    return { data: null, dataType: 'jobs', found: false };
  }

  function slugMatch(candidate, slug) {
    const normalize = s => safe(s).toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
    return normalize(candidate) === normalize(slug);
  }

  function readCompleteJobsJson(raw, slug) {
    if (typeof raw !== 'object' || Array.isArray(raw)) return null;
    for (const catArr of Object.values(raw)) {
      if (!Array.isArray(catArr)) continue;
      for (const job of catArr) {
        const title = safe(job.basic_details?.job_title || job.title || '');
        if (slugMatch(title, slug)) return job;
        // Also check slug field
        if (job.slug && slugMatch(job.slug, slug)) return job;
      }
    }
    return null;
  }

  function readMergedSarkariJson(raw, slug) {
    const jobs = raw.jobs || (Array.isArray(raw) ? raw : []);
    for (const job of jobs) {
      const title = safe(job.title || job.name || '');
      if (slugMatch(title, slug)) return job;
      if (job.slug && slugMatch(job.slug, slug)) return job;
    }
    return null;
  }

  function readStateJobsJson(raw, slug) {
    const sections = raw.sections || (Array.isArray(raw) ? raw : []);
    for (const section of sections) {
      const items = section.items || [];
      for (const item of items) {
        const name = safe(item.name || '');
        if (slugMatch(name, slug)) return item.detail || item;
        if (item.slug && slugMatch(item.slug, slug)) return item.detail || item;
      }
    }
    return null;
  }

  function readDailyUpdatesJson(raw, slug) {
    const sections = raw.sections || [];
    for (const section of sections) {
      const items = section.items || [];
      for (const item of items) {
        const name = safe(item.name || '');
        if (slugMatch(name, slug)) return item;
      }
    }
    return null;
  }

  /* ═══════════════════════════════════════════════════════
     § 11  MAIN INIT — Entry Point
  ═══════════════════════════════════════════════════════ */

  async function init(slug, container) {
    if (!container) container = document.getElementById('ureRoot');
    if (!container) { console.error('URE: No container found'); return; }

    // Show loading state
    container.innerHTML = `<div class="ure-loading"><div class="ure-spinner"></div><p>Loading content…</p></div>`;

    const { data, dataType, found } = await findBySlug(slug);

    if (!found || !data) {
      container.innerHTML = `<div class="ure-error">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <h2>Content Not Found</h2>
        <p>The page "<strong>${humanKey(slug)}</strong>" could not be found.</p>
        <a href="/" class="ure-btn ure-btn-blue">← Back to Home</a>
      </div>`;
      return;
    }

    renderPage(data, slug, dataType, container);
  }

  /* ═══════════════════════════════════════════════════════
     § 12  INTERACTIVE: FAQ TOGGLE
  ═══════════════════════════════════════════════════════ */

  function toggleFaq(btn) {
    const answer = btn.nextElementSibling;
    const isOpen = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', !isOpen);
    if (isOpen) { answer.hidden = true; } else { answer.hidden = false; }
  }

  /* Public API */
  return { init, findBySlug, renderPage, renderSection, renderValue, extractHeroData, injectSEO, toggleFaq, humanKey, fmtDate, isUrl, isSalary };
});

/* Make toggle available globally for inline onclick handlers */
window.URE = window.UniversalRenderer;
