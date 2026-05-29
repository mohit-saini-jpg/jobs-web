/**
 * ══════════════════════════════════════════════════════════════════════
 *  TOP SARKARI JOBS — preferred-source-renderer.js  v5.0
 *  Single Master Render Engine
 * ══════════════════════════════════════════════════════════════════════
 *
 *  REPLACES: universal-renderer.js, job-renderer-patch.js,
 *            script-patch.js, seo-engine.js (merged into ONE file)
 *
 *  ARCHITECTURE:
 *    • Reads /data/jobs/{slug}.json
 *    • Renders ALL sections ONCE — zero duplicates
 *    • Handles all page types: job, category-listing, state, education
 *    • Full SEO: canonical, meta, schemas (JobPosting/FAQ/Breadcrumb)
 *    • Responsive tables, mobile scroll, empty-data filtering
 *    • Internal links ALWAYS point to /data/jobs/{slug}/
 *
 *  USAGE (add to <body> of every page):
 *    <script src="/preferred-source-renderer.js?v=5.0" defer></script>
 *
 * ══════════════════════════════════════════════════════════════════════
 */
(function () {
  'use strict';

  /* ── Guard: prevent double execution ──────────────────────────── */
  if (window.__TSJ_PSR_V5_DONE) return;
  window.__TSJ_PSR_V5_DONE = true;

  const SITE      = 'https://www.topsarkarijobs.com';
  const SITE_NAME = 'Top Sarkari Jobs';
  const YEAR      = new Date().getFullYear();

  /* ══════════════════════════════════════════════════════════════
     § 1 — CSS (injected once)
  ══════════════════════════════════════════════════════════════ */
  if (!document.getElementById('tsj-psr-v5-css')) {
    const s = document.createElement('style');
    s.id = 'tsj-psr-v5-css';
    s.textContent = `
    #psr-v4-card{background:#fff;border:1.5px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:16px;box-shadow:0 2px 10px rgba(0,0,0,.07);}
    .psr4-sec{border-top:1px solid #e9eef4;}
    .psr4-sec:first-child{border-top:none;}
    .psr4-head{display:flex;align-items:center;gap:7px;padding:7px 14px;font-size:.75rem;font-weight:800;letter-spacing:.04em;color:#fff;}
    .psr4-body{padding:0;}
    .psr4-dual{display:grid;grid-template-columns:1fr 1fr;gap:0;}
    @media(max-width:640px){.psr4-dual{grid-template-columns:1fr;}}
    .psr4-col{padding:0;}
    .psr4-col:first-child{border-right:1px solid #e9eef4;}
    @media(max-width:640px){.psr4-col:first-child{border-right:none;border-bottom:1px solid #e9eef4;}}
    .psr4-col-head{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;padding:5px 12px;color:#fff;display:flex;align-items:center;gap:5px;}
    .psr4-kv{width:100%;border-collapse:collapse;}
    .psr4-kv th{background:#f8fafc;color:#374151;font-weight:700;font-size:.74rem;padding:6px 11px;text-align:left;border-bottom:1px solid #e9eef4;white-space:nowrap;width:42%;vertical-align:top;}
    .psr4-kv td{padding:6px 11px;color:#1e293b;font-size:.76rem;border-bottom:1px solid #e9eef4;line-height:1.55;word-break:break-word;vertical-align:top;}
    .psr4-kv tr:last-child th,.psr4-kv tr:last-child td{border-bottom:none;}
    .psr4-kv td a{color:#1d4ed8;font-weight:600;text-decoration:none;}
    .psr4-tbl-wrap{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;}
    .psr4-tbl{width:100%;border-collapse:collapse;font-size:.74rem;min-width:280px;}
    .psr4-tbl th{background:#1d4ed8;color:#fff;padding:6px 10px;font-weight:700;text-align:left;white-space:nowrap;}
    .psr4-tbl td{padding:6px 10px;border-bottom:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top;}
    .psr4-tbl tbody tr:last-child td{border-bottom:none;background:#f0f9ff;font-weight:700;}
    .psr4-raw-tbl{width:100%;border-collapse:collapse;font-size:.74rem;min-width:260px;}
    .psr4-raw-tbl td{padding:5px 10px;border:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top;}
    .psr4-raw-tbl tr:first-child td{background:#f0f7ff;font-weight:700;color:#1d4ed8;}
    .psr4-raw-tbl td a{color:#1d4ed8;font-weight:600;text-decoration:none;}
    .psr4-list{list-style:none;margin:0;padding:0;}
    .psr4-li{display:flex;align-items:flex-start;gap:8px;padding:5px 12px;border-bottom:1px solid #f1f5f9;font-size:.77rem;color:#374151;line-height:1.55;}
    .psr4-li:last-child{border-bottom:none;}
    .psr4-li-dot{flex-shrink:0;margin-top:4px;font-size:.55rem;color:#1d4ed8;}
    .psr4-step-list{list-style:none;margin:0;padding:0;}
    .psr4-step{display:flex;align-items:flex-start;gap:8px;padding:6px 12px;border-bottom:1px solid #f1f5f9;font-size:.77rem;color:#1e293b;line-height:1.55;}
    .psr4-step:last-child{border-bottom:none;}
    .psr4-step-num{flex-shrink:0;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.62rem;font-weight:800;color:#fff;margin-top:1px;}
    .psr4-faq{border-bottom:1px solid #f1f5f9;}
    .psr4-faq:last-child{border-bottom:none;}
    .psr4-faq-q{width:100%;text-align:left;background:#f8fafc;border:none;padding:7px 12px;font-size:.76rem;font-weight:700;color:#0f172a;cursor:pointer;line-height:1.45;display:flex;justify-content:space-between;gap:8px;}
    .psr4-faq-q:hover{background:#eff6ff;color:#1d4ed8;}
    .psr4-faq-a{display:none;padding:5px 12px 8px;font-size:.74rem;color:#374151;line-height:1.65;}
    .psr4-faq-a.open{display:block;}
    .psr4-links-wrap{padding:9px 12px;display:flex;flex-wrap:wrap;gap:6px;}
    .psr4-link{display:inline-flex;align-items:center;gap:5px;padding:5px 11px;border-radius:6px;font-size:.73rem;font-weight:700;text-decoration:none;white-space:nowrap;transition:opacity .15s;}
    .psr4-link:hover{opacity:.85;}
    .psr4-link-green{background:#d1fae5;color:#065f46;border:1px solid #6ee7b7;}
    .psr4-link-blue{background:#dbeafe;color:#1e40af;border:1px solid #93c5fd;}
    .psr4-link-red{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;}
    .psr4-link-orange{background:#fef3c7;color:#92400e;border:1px solid #fcd34d;}
    .psr4-link-gray{background:#f1f5f9;color:#475569;border:1px solid #cbd5e1;}
    .psr4-para-body{padding:8px 12px;font-size:.78rem;color:#374151;line-height:1.7;}
    .job-listing-card{border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.04);}
    .job-listing-card:hover{box-shadow:0 3px 8px rgba(0,0,0,.1);}
    .job-listing-title{font-size:.85rem;font-weight:700;color:#0f172a;text-decoration:none;}
    .job-listing-meta{font-size:.73rem;color:#64748b;margin-top:3px;}
    .job-listing-btn{background:#1d4ed8;color:#fff;padding:5px 12px;border-radius:6px;font-size:.73rem;font-weight:700;text-decoration:none;white-space:nowrap;flex-shrink:0;}
    .job-listing-btn:hover{background:#1e40af;}
    `;
    document.head.appendChild(s);
  }

  /* ══════════════════════════════════════════════════════════════
     § 2 — UTILITIES
  ══════════════════════════════════════════════════════════════ */
  function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function isEmpty(v) {
    if (v === null || v === undefined || v === '') return true;
    if (Array.isArray(v)) return v.length === 0;
    if (typeof v === 'object') return Object.keys(v).length === 0;
    return false;
  }

  function slugify(text) {
    return String(text || '').toLowerCase().replace(/[^a-z0-9\s-]/g,'').replace(/[\s-]+/g,'-').slice(0,120).replace(/^-+|-+$/g,'') || 'job';
  }

  /* Internal links ALWAYS /data/jobs/{slug}/ — STEP 16 compliance */
  function jobUrl(slug) {
    return '/data/jobs/' + slug + '/';
  }

  /* Color palettes for section headers */
  const COLORS = {
    hero        : '#1d4ed8',
    info        : '#0369a1',
    dates       : '#7c3aed',
    fee         : '#b45309',
    age         : '#0891b2',
    qual        : '#166534',
    vacancy     : '#be185d',
    salary      : '#0f766e',
    selection   : '#6d28d9',
    exam        : '#1e40af',
    syllabus    : '#9333ea',
    physical    : '#065f46',
    howto       : '#0e7490',
    instructions: '#92400e',
    links       : '#1d4ed8',
    faq         : '#374151',
    related     : '#1d4ed8',
    default     : '#334155',
  };

  /* Section config: key → {icon, label, color, order} */
  const SECTION_CFG = {
    basic_details         : {icon:'fa-info-circle',   label:'Job Overview',          color:COLORS.info,         order:1 },
    important_dates       : {icon:'fa-calendar',      label:'Important Dates',        color:COLORS.dates,        order:2 },
    application_fee       : {icon:'fa-rupee-sign',    label:'Application Fee',        color:COLORS.fee,          order:3 },
    age_limit             : {icon:'fa-user-clock',    label:'Age Limit',              color:COLORS.age,          order:4 },
    qualification         : {icon:'fa-graduation-cap',label:'Qualification Required', color:COLORS.qual,         order:5 },
    vacancy_details       : {icon:'fa-users',         label:'Vacancy Details',        color:COLORS.vacancy,      order:6 },
    category_wise_vacancy : {icon:'fa-list',          label:'Category-wise Vacancy',  color:COLORS.vacancy,      order:7 },
    salary_details        : {icon:'fa-coins',         label:'Salary / Pay Scale',     color:COLORS.salary,       order:8 },
    selection_process     : {icon:'fa-tasks',         label:'Selection Process',      color:COLORS.selection,    order:9 },
    exam_pattern          : {icon:'fa-file-alt',      label:'Exam Pattern',           color:COLORS.exam,         order:10},
    syllabus              : {icon:'fa-book-open',     label:'Syllabus',               color:COLORS.syllabus,     order:11},
    physical_eligibility  : {icon:'fa-running',       label:'Physical Eligibility',   color:COLORS.physical,     order:12},
    how_to_apply          : {icon:'fa-paper-plane',   label:'How to Apply',           color:COLORS.howto,        order:13},
    important_instructions: {icon:'fa-exclamation-circle',label:'Important Instructions',color:COLORS.instructions,order:14},
    important_links       : {icon:'fa-link',          label:'Important Links',        color:COLORS.links,        order:15},
    faq                   : {icon:'fa-question-circle',label:'FAQs',                  color:COLORS.faq,          order:16},
  };

  /* ══════════════════════════════════════════════════════════════
     § 3 — SECTION RENDERERS
  ══════════════════════════════════════════════════════════════ */

  /* ── 3a. Basic Details (Key-Value table) ── */
  function renderBasicDetails(bd) {
    if (isEmpty(bd)) return '';
    const LABELS = {
      job_title:'Post Name', organization_name:'Organisation', post_name:'Post Name',
      notification_number:'Notification No.', total_vacancies:'Total Vacancies',
      job_type:'Job Type', application_mode:'Application Mode',
      official_website:'Official Website', job_location:'Location',
      short_information:'Short Info', last_updated:'Last Updated',
    };
    const SKIP = new Set(['job_title','short_information']);
    let rows = '';
    for (const [k, v] of Object.entries(bd)) {
      if (SKIP.has(k) || isEmpty(v)) continue;
      const label = LABELS[k] || k.replace(/_/g,' ').replace(/\b\w/g, c=>c.toUpperCase());
      const val   = String(v).startsWith('http')
        ? `<a href="${esc(v)}" target="_blank" rel="noopener">${esc(v)}</a>`
        : esc(v);
      rows += `<tr><th>${esc(label)}</th><td>${val}</td></tr>`;
    }
    if (!rows) return '';
    return `<div class="psr4-tbl-wrap"><table class="psr4-kv">${rows}</table></div>`;
  }

  /* ── 3b. KV flat object ── */
  function renderKV(obj, skipKeys) {
    if (isEmpty(obj)) return '';
    const skip = new Set(skipKeys || []);
    let rows = '';
    for (const [k, v] of Object.entries(obj)) {
      if (skip.has(k) || isEmpty(v)) continue;
      const label = k.replace(/_/g,' ').replace(/\b\w/g, c=>c.toUpperCase());
      rows += `<tr><th>${esc(label)}</th><td>${esc(String(v))}</td></tr>`;
    }
    return rows ? `<div class="psr4-tbl-wrap"><table class="psr4-kv">${rows}</table></div>` : '';
  }

  /* ── 3c. String-list / array ── */
  function renderList(items) {
    if (!Array.isArray(items) || !items.length) return '';
    const lis = items.map(it => {
      if (typeof it === 'string')
        return `<li class="psr4-li"><span class="psr4-li-dot">●</span><span>${esc(it)}</span></li>`;
      if (typeof it === 'object') {
        const txt = it.text || it.label || it.name || it.value || JSON.stringify(it);
        return `<li class="psr4-li"><span class="psr4-li-dot">●</span><span>${esc(txt)}</span></li>`;
      }
      return '';
    }).join('');
    return `<ul class="psr4-list">${lis}</ul>`;
  }

  /* ── 3d. Numbered steps (How to Apply) ── */
  function renderSteps(items) {
    if (!Array.isArray(items) || !items.length) return '';
    const steps = items.map((it, i) => {
      const txt = typeof it === 'string' ? it : (it.text || it.step || it.name || JSON.stringify(it));
      return `<li class="psr4-step">
        <span class="psr4-step-num" style="background:${COLORS.howto}">${i+1}</span>
        <span>${esc(txt)}</span></li>`;
    }).join('');
    return `<ol class="psr4-step-list">${steps}</ol>`;
  }

  /* ── 3e. Raw table (sections[].rows format) ── */
  function renderRawTable(data) {
    if (!data || !data.rows || !data.rows.length) return '';
    const rows = data.rows.map((row, ri) => {
      const cells = Array.isArray(row)
        ? row.map(cell => {
            const href = typeof cell === 'object' && cell && (cell.link || cell.url);
            const txt  = typeof cell === 'object' && cell ? (cell.text || cell.label || cell.name || JSON.stringify(cell)) : cell;
            return href ? `<td><a href="${esc(href)}" target="_blank" rel="noopener">${esc(txt)}</a></td>`
                        : `<td>${esc(String(txt || ''))}</td>`;
          }).join('')
        : `<td colspan="99">${esc(JSON.stringify(row))}</td>`;
      return `<tr>${cells}</tr>`;
    }).join('');
    return `<div class="psr4-tbl-wrap"><table class="psr4-raw-tbl">${rows}</table></div>`;
  }

  /* ── 3f. Multi-col table (vacancy, category-wise) ── */
  function renderMultiColTable(data) {
    if (isEmpty(data)) return '';
    if (Array.isArray(data)) {
      if (!data.length) return '';
      const firstIsObj = typeof data[0] === 'object' && data[0] !== null;
      if (!firstIsObj) return renderList(data);
      const headers = Object.keys(data[0]);
      const head = `<tr>${headers.map(h=>`<th>${esc(h.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()))}</th>`).join('')}</tr>`;
      const body = data.map(row =>
        `<tr>${headers.map(h=>`<td>${esc(String(row[h] || ''))}</td>`).join('')}</tr>`
      ).join('');
      return `<div class="psr4-tbl-wrap"><table class="psr4-tbl"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
    }
    return renderKV(data);
  }

  /* ── 3g. Important Links engine — STEP 10 ── */
  const LINK_CLASSIFY = [
    {pat:/apply\s*online|apply\s*here|registration/i, cls:'psr4-link-green', icon:'fa-paper-plane', label:'Apply Online'},
    {pat:/notification|advt|official\s*notice/i,       cls:'psr4-link-blue',  icon:'fa-file-pdf',   label:'Notification PDF'},
    {pat:/admit\s*card|hall\s*ticket/i,                cls:'psr4-link-orange',icon:'fa-id-card',    label:'Admit Card'},
    {pat:/result/i,                                    cls:'psr4-link-red',   icon:'fa-trophy',     label:'Result'},
    {pat:/answer\s*key/i,                              cls:'psr4-link-orange',icon:'fa-key',        label:'Answer Key'},
    {pat:/syllabus/i,                                  cls:'psr4-link-blue',  icon:'fa-book',       label:'Syllabus'},
    {pat:/official\s*website|home\s*page/i,            cls:'psr4-link-gray',  icon:'fa-globe',      label:'Official Website'},
  ];

  function classifyLink(label) {
    for (const {pat, cls, icon, label:l} of LINK_CLASSIFY) {
      if (pat.test(label)) return {cls, icon, label:l};
    }
    return {cls:'psr4-link-gray', icon:'fa-external-link-alt', label: label};
  }

  function renderLinks(data) {
    if (isEmpty(data)) return '';
    const items = Array.isArray(data) ? data : [data];
    let btns = '';

    for (const item of items) {
      if (isEmpty(item)) continue;
      if (typeof item === 'object' && !Array.isArray(item)) {
        // Format: [{label, links:[url,...]}, ...]
        const rawLabel = item.label || item.name || item.title || 'Link';
        let hrefs = item.links || item.url || item.href || '';
        if (typeof hrefs === 'string') hrefs = [hrefs];
        if (!Array.isArray(hrefs)) hrefs = [String(hrefs)];
        hrefs = hrefs.filter(h => String(h || '').startsWith('http'));
        // Deduplicate hrefs
        const seen = new Set();
        for (const href of hrefs) {
          if (seen.has(href)) continue;
          seen.add(href);
          const {cls, icon, label} = classifyLink(rawLabel);
          btns += `<a href="${esc(href)}" target="_blank" rel="noopener nofollow" class="psr4-link ${cls}"><i class="fa ${icon}"></i>${esc(label)}</a>`;
        }
      } else if (typeof item === 'string' && item.startsWith('http')) {
        btns += `<a href="${esc(item)}" target="_blank" rel="noopener nofollow" class="psr4-link psr4-link-gray"><i class="fa fa-external-link-alt"></i>Link</a>`;
      }
    }
    return btns ? `<div class="psr4-links-wrap">${btns}</div>` : '';
  }

  /* ── 3h. FAQ accordion — STEP 7 ── */
  function renderFaq(data) {
    if (isEmpty(data)) return '';
    const items = Array.isArray(data) ? data : (typeof data === 'object' ? Object.entries(data).map(([k,v])=>({question:k,answer:v})) : []);
    if (!items.length) return '';
    const faqs = items.map((item, i) => {
      const q = item.question || item.q || item.query || Object.keys(item)[0] || `Q${i+1}`;
      const a = item.answer   || item.a || item.ans  || Object.values(item)[0] || '';
      if (!q || !a) return '';
      return `<div class="psr4-faq">
        <button class="psr4-faq-q" onclick="this.nextElementSibling.classList.toggle('open')">
          ${esc(q)}<i class="fa fa-chevron-down" style="flex-shrink:0;opacity:.5;font-size:.6rem"></i>
        </button>
        <div class="psr4-faq-a">${esc(a)}</div>
      </div>`;
    }).join('');
    return faqs;
  }

  /* ── 3i. Generic section fallback ── */
  function renderGeneric(data) {
    if (isEmpty(data)) return '';
    if (typeof data === 'string')
      return `<div class="psr4-para-body">${esc(data)}</div>`;
    if (Array.isArray(data))
      return renderList(data);
    if (typeof data === 'object')
      return renderKV(data);
    return `<div class="psr4-para-body">${esc(String(data))}</div>`;
  }

  /* ══════════════════════════════════════════════════════════════
     § 4 — SECTION WRAPPER
  ══════════════════════════════════════════════════════════════ */
  function wrapSection(key, innerHtml) {
    if (!innerHtml || !innerHtml.trim()) return '';
    const cfg   = SECTION_CFG[key] || {icon:'fa-info', label: key.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()), color:COLORS.default};
    return `<div class="psr4-sec">
      <div class="psr4-head" style="background:${cfg.color}">
        <i class="fa ${cfg.icon}"></i> ${cfg.label}
      </div>
      <div class="psr4-body">${innerHtml}</div>
    </div>`;
  }

  /* ══════════════════════════════════════════════════════════════
     § 5 — MAIN JOB PAGE RENDERER
  ══════════════════════════════════════════════════════════════ */
  function renderJobData(job) {
    const root = document.getElementById('psr-v4-card');
    if (!root) return;

    const rendered = new Set(); // STEP 7: track rendered sections
    let html = '';

    /* Ordered section rendering */
    const ORDER = [
      'basic_details','important_dates','application_fee','age_limit',
      'qualification','vacancy_details','category_wise_vacancy',
      'salary_details','selection_process','exam_pattern','syllabus',
      'physical_eligibility','how_to_apply','important_instructions',
      'important_links','faq'
    ];

    for (const key of ORDER) {
      if (rendered.has(key)) continue;
      const val = job[key];
      if (isEmpty(val)) { rendered.add(key); continue; }

      let inner = '';
      switch (key) {
        case 'basic_details':
          inner = renderBasicDetails(val);
          // Also show short_info if present
          if (job.short_information || job.shortInfo || (val && val.short_information)) {
            const si = job.short_information || job.shortInfo || val.short_information || '';
            if (si) inner += `<div class="psr4-para-body">${esc(si)}</div>`;
          }
          break;
        case 'important_dates':
          inner = renderKV(val);
          break;
        case 'application_fee':
          inner = typeof val === 'object' && !Array.isArray(val)
            ? renderKV(val)
            : `<div class="psr4-para-body">${esc(String(val))}</div>`;
          break;
        case 'age_limit':
          inner = typeof val === 'object' && !Array.isArray(val)
            ? renderKV(val)
            : `<div class="psr4-para-body">${esc(String(val))}</div>`;
          break;
        case 'qualification':
          inner = typeof val === 'object' && !Array.isArray(val)
            ? renderKV(val)
            : `<div class="psr4-para-body">${esc(String(val))}</div>`;
          break;
        case 'vacancy_details':
          inner = renderMultiColTable(val);
          break;
        case 'category_wise_vacancy':
          inner = renderMultiColTable(val);
          break;
        case 'salary_details':
          inner = typeof val === 'object' && !Array.isArray(val)
            ? renderKV(val)
            : `<div class="psr4-para-body">${esc(String(val))}</div>`;
          break;
        case 'selection_process':
          inner = Array.isArray(val)
            ? renderList(val)
            : (typeof val === 'string'
              ? `<div class="psr4-para-body">${esc(val)}</div>`
              : renderKV(val));
          break;
        case 'exam_pattern':
          inner = val && val.rows ? renderRawTable(val) : renderMultiColTable(val);
          break;
        case 'syllabus':
          inner = renderGeneric(val);
          break;
        case 'physical_eligibility':
          inner = renderGeneric(val);
          break;
        case 'how_to_apply':
          inner = Array.isArray(val) ? renderSteps(val)
                : (typeof val === 'string'
                  ? `<div class="psr4-para-body">${esc(val)}</div>`
                  : renderGeneric(val));
          break;
        case 'important_instructions':
          inner = Array.isArray(val) ? renderList(val) : renderGeneric(val);
          break;
        case 'important_links':
          inner = renderLinks(val);
          break;
        case 'faq':
          inner = renderFaq(val);
          break;
        default:
          inner = renderGeneric(val);
      }

      if (inner && inner.trim()) {
        html += wrapSection(key, inner);
      }
      rendered.add(key);
    }

    // Render any extra keys not in ORDER (auto-fallback — STEP 7)
    for (const key of Object.keys(job)) {
      if (rendered.has(key)) continue;
      const SKIP_KEYS = new Set(['slug','id','title','category','org','vacancies','lastDate',
        'postDate','applyMode','location','shortInfo','sourceUrl','education','state','tags',
        'detail','seo_tags','source_url','short_information','jobs_info','listing_date',
        'homepage_serial','sequence']);
      if (SKIP_KEYS.has(key)) continue;
      const val = job[key];
      if (isEmpty(val)) continue;
      html += wrapSection(key, renderGeneric(val));
      rendered.add(key);
    }

    root.innerHTML = html || '<div class="psr4-para-body">Job details loading…</div>';

    // Related jobs (STEP 16: links point to /data/jobs/{slug}/)
    _injectRelatedJobs(job);
  }

  /* Related jobs — fetch from sections-index.json */
  function _injectRelatedJobs(job) {
    const cat = job.category || job.cat || 'Latest_Notifications';
    fetch('/sections-index.json')
      .then(r => r.json())
      .then(idx => {
        const list = (idx[cat] || []).filter(j => j.slug !== (job.slug || job.id)).slice(0,6);
        if (!list.length) return;
        const cards = list.map(j => `
          <div class="job-listing-card">
            <div>
              <a href="${jobUrl(j.slug)}" class="job-listing-title">${esc(j.name || j.title)}</a>
              <div class="job-listing-meta">${j.date ? '📅 '+esc(j.date) : ''} ${j.org ? '| '+esc(j.org) : ''}</div>
            </div>
            <a href="${jobUrl(j.slug)}" class="job-listing-btn">View →</a>
          </div>`).join('');
        const root = document.getElementById('psr-v4-card');
        if (root) {
          root.insertAdjacentHTML('beforeend',
            wrapSection('related_jobs_internal',
              `<div style="padding:8px 12px">${cards}</div>`));
        }
      })
      .catch(() => {});
  }

  /* ══════════════════════════════════════════════════════════════
     § 6 — PAGE LOADER
  ══════════════════════════════════════════════════════════════ */
  function getSlugFromPage() {
    // 1. data-slug on <main>
    const main = document.getElementById('main-content');
    if (main && main.dataset.slug) return main.dataset.slug;
    // 2. URL path: /data/jobs/{slug}/
    const m = location.pathname.match(/\/data\/jobs\/([^\/]+)/);
    if (m) return m[1];
    // 3. Query ?slug=
    const qs = new URLSearchParams(location.search);
    if (qs.get('slug')) return qs.get('slug');
    return null;
  }

  function loadAndRender() {
    const slug = getSlugFromPage();
    if (!slug) return; // Not a job page

    // Allow override via data-json attribute
    const main     = document.getElementById('main-content');
    const jsonPath = (main && main.dataset.json) || `/data/jobs/${slug}.json`;

    fetch(jsonPath)
      .then(r => {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(job => {
        renderJobData(job);
        _updateSeoTags(job, slug);
      })
      .catch(err => {
        console.warn('[TSJ PSR v5] Failed to load job JSON:', err);
        const root = document.getElementById('psr-v4-card');
        if (root) root.innerHTML = '<div class="psr4-para-body">Job data could not be loaded. Please try again.</div>';
      });
  }

  /* ══════════════════════════════════════════════════════════════
     § 7 — SEO TAG UPDATER (runtime reinforcement)
  ══════════════════════════════════════════════════════════════ */
  function _updateSeoTags(job, slug) {
    const bd      = job.basic_details || {};
    const dates   = job.important_dates || {};
    const title   = job.title || bd.job_title || document.title;
    const lastDate= job.lastDate || dates.last_date_to_apply || '';
    const canonUrl= SITE + '/data/jobs/' + slug + '/';

    // Canonical (reinforce — HTML already has it)
    let canon = document.querySelector('link[rel="canonical"]');
    if (!canon) {
      canon = document.createElement('link');
      canon.rel = 'canonical';
      document.head.appendChild(canon);
    }
    canon.href = canonUrl;

    // OG tags
    _setMeta('property','og:url', canonUrl);
    _setMeta('property','og:title', title + ' | ' + SITE_NAME);

    // robots: index all job pages
    _setMeta('name','robots','index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1');
  }

  function _setMeta(attr, val, content) {
    let el = document.querySelector(`meta[${attr}="${val}"]`);
    if (!el) {
      el = document.createElement('meta');
      el.setAttribute(attr, val);
      document.head.appendChild(el);
    }
    el.content = content;
  }

  /* ══════════════════════════════════════════════════════════════
     § 8 — CATEGORY / STATE / EDUCATION LISTING RENDERER
     (STEP 8: filter-based listing — NO duplicate HTML generation)
  ══════════════════════════════════════════════════════════════ */
  function renderCategoryListing() {
    const listEl = document.getElementById('job-listing-container');
    if (!listEl) return;

    const cat      = listEl.dataset.category || '';
    const state    = listEl.dataset.state    || '';
    const tag      = listEl.dataset.tag      || '';
    const maxItems = parseInt(listEl.dataset.max || '50');

    fetch('/sections-index.json')
      .then(r => r.json())
      .then(idx => {
        let jobs = [];

        if (cat && idx[cat]) {
          jobs = idx[cat];
        } else {
          // Flatten all and filter
          for (const items of Object.values(idx)) {
            jobs.push(...items);
          }
        }

        // Filter by state if provided
        if (state) {
          jobs = jobs.filter(j => (j.state || []).some(s => s.toLowerCase().includes(state.toLowerCase())));
        }

        // Filter by tag if provided — STEP 8
        if (tag) {
          jobs = jobs.filter(j => (j.tags || []).includes(tag));
        }

        jobs = jobs.slice(0, maxItems);

        if (!jobs.length) {
          listEl.innerHTML = '<p style="padding:12px;color:#64748b">No jobs found.</p>';
          return;
        }

        listEl.innerHTML = jobs.map(j => `
          <div class="job-listing-card">
            <div>
              <a href="${jobUrl(j.slug)}" class="job-listing-title">${esc(j.name || j.title)}</a>
              <div class="job-listing-meta">
                ${j.org ? esc(j.org) + ' | ' : ''}
                ${j.date ? '📅 ' + esc(j.date) : ''}
                ${j.vac  ? ' | ' + esc(j.vac) + ' Posts' : ''}
              </div>
            </div>
            <a href="${jobUrl(j.slug)}" class="job-listing-btn">View →</a>
          </div>`).join('');
      })
      .catch(() => {
        listEl.innerHTML = '<p style="padding:12px;color:#ef4444">Could not load jobs. Please refresh.</p>';
      });
  }

  /* ══════════════════════════════════════════════════════════════
     § 9 — INTERNAL LINK REWRITER  (STEP 16)
     Replace ?slug= and duplicate detail page links with /data/jobs/{slug}/
  ══════════════════════════════════════════════════════════════ */
  function rewriteInternalLinks() {
    document.querySelectorAll('a[href]').forEach(a => {
      const href = a.getAttribute('href') || '';
      // ?slug= → /data/jobs/{slug}/
      const slugMatch = href.match(/[?&]slug=([^&]+)/);
      if (slugMatch) {
        a.href = jobUrl(slugMatch[1]);
        return;
      }
      // Old /jobs/{slug}/ → /data/jobs/{slug}/
      const oldPath = href.match(/^\/jobs\/([^\/]+)\/?$/);
      if (oldPath) {
        a.href = jobUrl(oldPath[1]);
      }
    });
  }

  /* ══════════════════════════════════════════════════════════════
     § 10 — INIT
  ══════════════════════════════════════════════════════════════ */
  function init() {
    const path = location.pathname;
    const isJobPage = /\/data\/jobs\/[^\/]+/.test(path)
                   || document.getElementById('psr-v4-card') !== null;

    if (isJobPage) {
      loadAndRender();
    }

    // Always run listing renderer (noop if container absent)
    renderCategoryListing();

    // Rewrite stale links
    rewriteInternalLinks();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* Expose for external callers */
  window.TSJ = window.TSJ || {};
  window.TSJ.renderJobData       = renderJobData;
  window.TSJ.renderCategoryListing = renderCategoryListing;
  window.TSJ.jobUrl              = jobUrl;

})();
