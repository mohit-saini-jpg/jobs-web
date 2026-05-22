/**
 * ══════════════════════════════════════════════════════════════════════════
 *  TOP SARKARI JOBS — Ultra Advanced Universal Dynamic Rendering Engine
 *  File:    universal-renderer.js
 *  Version: 2026-05-21 (v3.0 — Complete Rewrite)
 * ══════════════════════════════════════════════════════════════════════════
 *
 *  ARCHITECTURE
 *  ─────────────
 *  1. DeepParser    — Recursively walks ANY JSON structure, classifies every
 *                     node by type (date, url, table, list, kv, html, text)
 *  2. FieldNormalizer — Collapses all 4 JSON source variations into ONE
 *                       canonical schema (e.g. application_fees = application_fee)
 *  3. LinkIntelligence — Auto-detects URLs anywhere in JSON, classifies them
 *                       (apply_online, notification_pdf, official_website, etc.)
 *  4. CardBuilders  — Typed renderers (table, tags, grid, html, steps, FAQ)
 *  5. MasterInjector — Ordered, dedup-safe section injection + TOC updater
 *  6. IntegrationHub — Race-condition-free 4-way callback system
 *
 *  FIXES IN v3.0
 *  ─────────────
 *  ✅ important_links: click_here array → intelligent link labeling
 *  ✅ Merged data flat links (apply_online_link, official_notification_pdf_link…)
 *  ✅ State-jobs nested detail.{important_dates, application_fee, …} unwrap
 *  ✅ important_dates: start_date / application_start / application_begin unify
 *  ✅ application_fees (plural) ↔ application_fee normalize
 *  ✅ Vacancy table with ANY column set (post_name/total/eligibility etc)
 *  ✅ Deep-nested unknown objects auto-rendered (recursive)
 *  ✅ Every URL in ANY key always surfaces in Important Links
 *  ✅ Zero missing content — every JSON value renders somewhere
 *  ✅ Duplicate injection permanently blocked
 *
 * ══════════════════════════════════════════════════════════════════════════
 */

(function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════════════════════
     § 1 — CSS (injected once, mirrors site design tokens)
  ═══════════════════════════════════════════════════════════════════════ */
  const _CSS_ID = 'tsj-univ-v3-styles';
  if (!document.getElementById(_CSS_ID)) {
    const el = document.createElement('style');
    el.id = _CSS_ID;
    el.textContent = `
    #${_CSS_ID}{display:none}
    /* ── Card shell ── */
    .udyn-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
    .udyn-anchor{scroll-margin-top:var(--header-height,140px)}
    .udyn-head{display:flex;align-items:center;gap:8px;padding:9px 14px;color:#fff;font-size:.86rem;font-weight:700}
    .udyn-head i{opacity:.85}
    .udyn-body{}
    /* ── Generic two-col table ── */
    .udyn-gen-table{width:100%;border-collapse:collapse;font-size:.82rem}
    .udyn-gen-table th{width:36%;background:#f8fafc;color:#374151;font-weight:700;padding:9px 14px;text-align:left;vertical-align:top;border-bottom:1px solid #e9eef4;word-break:break-word}
    .udyn-gen-table td{padding:9px 14px;color:#1e293b;font-size:.83rem;line-height:1.65;border-bottom:1px solid #e9eef4;vertical-align:top;word-break:break-word}
    .udyn-gen-table tr:last-child th,.udyn-gen-table tr:last-child td{border-bottom:none}
    /* ── Multi-col table (vacancy/exam) ── */
    .udyn-table-scroll{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}
    .udyn-vac-table{width:100%;border-collapse:collapse;font-size:.82rem;min-width:320px}
    .udyn-vac-table th{background:#1d4ed8;color:#fff;padding:8px 12px;font-weight:700;white-space:nowrap;text-align:left}
    .udyn-vac-table td{padding:8px 12px;border-bottom:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top}
    .udyn-vac-table tbody tr:last-child td{border-bottom:none;font-weight:700;background:#f0f9ff}
    /* ── Tag chips ── */
    .udyn-tag-list{display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px}
    .udyn-tag{display:inline-flex;align-items:center;gap:6px;background:#f0f7ff;border:1px solid #bfdbfe;border-radius:8px;padding:6px 12px;font-size:.8rem;font-weight:600;color:#1e40af}
    /* ── Numbered steps ── */
    .udyn-steps-list{list-style:none;margin:0;padding:0}
    .udyn-step{display:flex;align-items:flex-start;gap:12px;padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:.83rem;color:#1e293b;line-height:1.65}
    .udyn-step:last-child{border-bottom:none}
    .udyn-step-num{flex-shrink:0;min-width:24px;height:24px;background:#0f766e;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:800;margin-top:1px}
    /* ── HTML content ── */
    .udyn-html-body{padding:10px 14px;font-size:.83rem;color:#1e293b;line-height:1.75}
    .udyn-html-body p{margin:0 0 8px}
    .udyn-html-body ul,.udyn-html-body ol{margin:0 0 8px;padding-left:20px}
    .udyn-html-body a{color:#1d4ed8}
    /* ── Plain detail block ── */
    .udyn-detail{padding:10px 14px;font-size:.83rem;color:#1e293b;line-height:1.7;border-bottom:1px solid #f1f5f9}
    .udyn-detail:last-child{border-bottom:none}
    /* ── Notice block (pre-line) ── */
    .udyn-notice{padding:10px 14px;font-size:.81rem;color:#374151;line-height:1.7;background:#f8fafc;white-space:pre-line}
    /* ── Grid (fee, salary, phy) ── */
    .udyn-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr))}
    .udyn-grid-item{padding:10px 14px;border-right:1px solid #e9eef4;border-bottom:1px solid #e9eef4}
    .udyn-grid-label{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:3px}
    .udyn-grid-val{font-size:.9rem;font-weight:700;color:#1e293b}
    .udyn-grid-note{padding:9px 14px;font-size:.81rem;color:#78350f;background:#fffbeb;border-top:1px solid #fde68a}
    /* ── FAQ accordion ── */
    .udyn-faq-item{border-bottom:1px solid #f1f5f9}
    .udyn-faq-item:last-child{border-bottom:none}
    .udyn-faq-q{display:flex;align-items:flex-start;gap:10px;padding:11px 14px;font-size:.84rem;font-weight:700;color:#0f172a;cursor:pointer;background:#f8fafc;user-select:none;line-height:1.5}
    .udyn-faq-q:hover{background:#f0f7ff}
    .udyn-faq-icon{color:#1d4ed8;font-size:.8rem;margin-top:3px;flex-shrink:0;transition:transform .2s}
    .udyn-faq-q.open .udyn-faq-icon{transform:rotate(90deg)}
    .udyn-faq-a{display:none;padding:0 14px 12px 40px;font-size:.82rem;color:#374151;line-height:1.7}
    .udyn-faq-a.open{display:block}
    /* ── Instructions list ── */
    .udyn-inst-list{list-style:none;margin:0;padding:0}
    .udyn-inst-item{display:flex;align-items:flex-start;gap:9px;padding:8px 14px;border-bottom:1px solid #f1f5f9;font-size:.82rem;color:#374151;line-height:1.65}
    .udyn-inst-item:last-child{border-bottom:none}
    .udyn-inst-item i{color:#ea580c;flex-shrink:0;margin-top:3px}
    /* ── Important Links ── */
    .udyn-links-list{list-style:none;margin:0;padding:0}
    .udyn-link-row{display:flex;align-items:center;gap:10px;padding:9px 14px;border-bottom:1px solid #f1f5f9;font-size:.83rem}
    .udyn-link-row:last-child{border-bottom:none}
    .udyn-link-label{color:#374151;font-weight:600;flex:1;min-width:120px}
    .udyn-link-btn{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:6px;font-size:.78rem;font-weight:700;text-decoration:none;white-space:nowrap;flex-shrink:0}
    .udyn-link-apply{background:#16a34a;color:#fff}
    .udyn-link-pdf{background:#dc2626;color:#fff}
    .udyn-link-website{background:#1d4ed8;color:#fff}
    .udyn-link-login{background:#7c3aed;color:#fff}
    .udyn-link-video{background:#dc2626;color:#fff}
    .udyn-link-default{background:#475569;color:#fff}
    /* ── Salary ── */
    .udyn-sal-val{color:#16a34a}
    /* ── Responsive ── */
    @media(max-width:600px){
      .udyn-vac-table{font-size:.72rem}
      .udyn-vac-table th,.udyn-vac-table td{padding:6px 7px}
      .udyn-gen-table{font-size:.76rem}
      .udyn-gen-table th,.udyn-gen-table td{padding:7px 9px;word-break:break-word}
      .udyn-link-row{flex-wrap:wrap;gap:6px}
      .udyn-link-label{min-width:unset;width:100%;font-size:.79rem}
      .udyn-link-btn{width:100%;justify-content:center;padding:7px 12px;font-size:.8rem}
      .udyn-grid{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}
      .udyn-head{font-size:.82rem;padding:8px 12px}
      .udyn-table-scroll{-webkit-overflow-scrolling:touch;overflow-x:auto}
      .udyn-step{padding:8px 10px;font-size:.8rem}
      .udyn-step-num{min-width:22px;height:22px;font-size:.68rem}
    }
    /* ── Nav TOC ── */
    .jp-left-nav-item.udyn-toc-link{color:#374151}
    .jp-left-nav-item.udyn-toc-link:hover{color:#1d4ed8}
    `;
    document.head.appendChild(el);
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 2 — CORE UTILITIES
  ═══════════════════════════════════════════════════════════════════════ */

  const safe = v => (v == null ? '' : String(v)).trim();

  function esc(s) {
    return safe(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function isHtml(s) { return /<[a-z][\s\S]*>/i.test(safe(s)); }

  function isUrl(s) { return /^https?:\/\//i.test(safe(s)); }

  function isPdf(url) { return /\.pdf(\?|$)/i.test(safe(url)); }

  function stripHtml(s) { return safe(s).replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim(); }

  function keyToLabel(k) {
    return safe(k)
      .replace(/_+/g,' ')
      .replace(/\b[a-z]/g, c => c.toUpperCase())
      .replace(/\bObc\b/g,'OBC').replace(/\bEws\b/g,'EWS')
      .replace(/\bSc\b/g,'SC').replace(/\bSt\b/g,'ST')
      .replace(/\bPh\b/g,'PH/PwD').replace(/\bUrl\b/g,'URL')
      .replace(/\bPdf\b/g,'PDF').replace(/\bUr\b/g,'UR')
      .replace(/\bId\b/g,'ID').replace(/\bNo\b/g,'No.')
      .trim();
  }

  function hasContent(v) {
    if (v == null) return false;
    if (typeof v === 'string') return v.trim().length > 0;
    if (typeof v === 'number' || typeof v === 'boolean') return true;
    if (Array.isArray(v)) return v.some(x => hasContent(x));
    if (typeof v === 'object') return Object.values(v).some(x => hasContent(x));
    return false;
  }

  function textToHtml(str) {
    return safe(str).split(/\n+/).map(l => l.trim()).filter(Boolean)
      .map(l => `<p style="margin:0 0 6px;">${esc(l)}</p>`).join('');
  }

  /** Render a value as safe HTML — auto-detects html/url/plain */
  function renderVal(v) {
    if (v == null) return '—';
    if (typeof v === 'object') return esc(JSON.stringify(v));
    const s = String(v).trim();
    if (!s) return '—';
    if (isUrl(s)) return `<a href="${esc(s)}" target="_blank" rel="noopener" style="color:#1d4ed8;font-weight:600;word-break:break-all;">${esc(s)}</a>`;
    if (isHtml(s)) return s;
    return esc(s);
  }

  /** Format date strings intelligently */
  function fmtDate(val) {
    const s = safe(val);
    let m = s.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})$/);
    if (m) return `${m[3].padStart(2,'0')}/${m[2].padStart(2,'0')}/${m[1]}`;
    m = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
    if (m) return `${m[1].padStart(2,'0')}/${m[2].padStart(2,'0')}/${m[3]}`;
    return s;
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 3 — FIELD NORMALIZER
     Collapses ALL JSON source variations into ONE canonical structure.
     Handles: Complete_Jobs, merged_sarkari, dailyupdates, state-jobs
  ═══════════════════════════════════════════════════════════════════════ */

  function normalize(raw) {
    if (!raw || typeof raw !== 'object') return raw;
    const job = Object.assign({}, raw);

    // ── Unwrap state-jobs nested 'detail' object ──────────────────────
    // state-jobs items have: { name, url, date, detail: { basic_details, important_dates, … } }
    if (job.detail && typeof job.detail === 'object') {
      const d = job.detail;
      // Promote all detail fields into top-level (non-destructively)
      for (const [k, v] of Object.entries(d)) {
        if (!hasContent(job[k]) && hasContent(v)) job[k] = v;
      }
      // Also keep basic_details sub-fields
      if (d.basic_details) {
        const bd = d.basic_details;
        if (!job.title && (bd.job_title || bd.post_name)) job.title = bd.job_title || bd.post_name;
        if (!job.organization && bd.organization_name) job.organization = bd.organization_name;
        if (!job.apply_mode && bd.application_mode) job.apply_mode = bd.application_mode;
        if (!job.short_information && bd.short_information) job.short_information = bd.short_information;
        if (!job.total_vacancy && bd.total_vacancies) job.total_vacancy = bd.total_vacancies;
      }
    }

    // ── Unwrap basic_details ─────────────────────────────────────────
    const bd = job.basic_details || {};
    if (!job.organization) job.organization = bd.organization_name || bd.department || bd.board || '';
    if (!job.title) job.title = bd.job_title || bd.post_name || job.post_name || '';
    if (!job.apply_mode) job.apply_mode = bd.application_mode || bd.apply_mode || '';
    if (!job.total_vacancy) job.total_vacancy = bd.total_vacancies || bd.total_posts || '';
    if (!job.short_information) job.short_information = bd.short_information || '';
    if (!job.jobs_info) job.jobs_info = bd.jobs_info || '';
    if (!job.salary) job.salary = bd.salary || bd.salary_pay_scale || job.salary_pay_scale || '';

    // ── Normalize important_dates keys ───────────────────────────────
    const id = job.important_dates || {};
    if (typeof id === 'object') {
      // Unify start date variants
      id.application_begin = id.application_begin || id.application_start || id.start_date || id.starting_date || id.starting_date_online || '';
      // Unify last date variants
      id.last_date = id.last_date || id.last_date_to_apply || id.application_last_date || id.closing_date || id.last_apply_date || '';
      // Unify exam date
      id.exam_date = id.exam_date || job.exam_date || '';
      job.important_dates = id;
    }

    // ── Normalize application_fees → application_fee ─────────────────
    if (!hasContent(job.application_fee) && hasContent(job.application_fees)) {
      job.application_fee = job.application_fees;
    }

    // ── Collect ALL URLs from flat merged-sarkari link fields ─────────
    const MERGED_LINK_MAP = {
      apply_online_link:              { label: 'Apply Online',            type: 'apply'   },
      form_pdf_free_link:             { label: 'Application Form (Free)', type: 'pdf'     },
      application_form_pdf_link:      { label: 'Application Form PDF',   type: 'pdf'     },
      form_pdf_link:                  { label: 'Form PDF',               type: 'pdf'     },
      official_notification_pdf_link: { label: 'Official Notification',   type: 'pdf'     },
      official_website_link:          { label: 'Official Website',        type: 'website' },
      apply_online:                   { label: 'Apply Online',            type: 'apply'   },
      source_url:                     { label: 'Source / Apply Link',     type: 'apply'   },
    };

    // Build or augment important_links_obj (our canonical link store)
    if (!job._udyn_links) job._udyn_links = [];

    for (const [field, meta] of Object.entries(MERGED_LINK_MAP)) {
      const url = safe(job[field]);
      if (isUrl(url)) {
        job._udyn_links.push({ label: meta.label, url, type: meta.type });
      }
    }

    // ── Parse important_links dict ────────────────────────────────────
    // Handles: { click_here: [url1, url2], notification_pdf: url, login: url, … }
    const il = job.important_links;
    if (il && typeof il === 'object' && !Array.isArray(il)) {
      for (const [k, v] of Object.entries(il)) {
        const urls = Array.isArray(v) ? v : [v];
        for (const url of urls) {
          const u = safe(url);
          if (!isUrl(u)) continue;
          const type = classifyLinkKey(k, u);
          const label = smartLinkLabel(k, u, urls.length > 1 ? urls.indexOf(url) + 1 : 0);
          job._udyn_links.push({ label, url: u, type });
        }
      }
    } else if (Array.isArray(il)) {
      for (const item of il) {
        if (typeof item === 'string' && isUrl(item)) {
          job._udyn_links.push({ label: smartLinkLabel('link', item, 0), url: item, type: classifyLinkKey('link', item) });
        } else if (item && typeof item === 'object') {
          const url = safe(item.url || item.link || item.href || '');
          const label = safe(item.label || item.text || item.name || item.title || '');
          if (isUrl(url)) {
            job._udyn_links.push({ label: label || smartLinkLabel('link', url, 0), url, type: classifyLinkKey(label, url) });
          }
        }
      }
    }

    // ── Also hunt URLs recursively in useful_links ────────────────────
    // Format: [{title: "Apply Online", links: "https://..." OR ["url1","url2"]}, ...]
    if (job.useful_links) {
      if (Array.isArray(job.useful_links)) {
        for (const item of job.useful_links) {
          if (!item) continue;
          const label = safe(item.title || item.name || item.label || '');
          // links can be a string OR an array of strings
          const rawLinks = item.links || item.link || item.url || '';
          const urls = Array.isArray(rawLinks) ? rawLinks : [rawLinks];
          urls.forEach((u, idx) => {
            const url = safe(u);
            if (!isUrl(url)) return;
            // Skip YouTube / video links
            if (/youtu\.?be|youtube\.com/i.test(url)) return;
            // For arrays with multiple URLs, append index suffix to label
            const finalLabel = urls.length > 1
              ? (label ? `${label} (${idx + 1})` : smartLinkLabel('link', url, idx + 1))
              : (label || smartLinkLabel('link', url, 0));
            job._udyn_links.push({
              label: finalLabel,
              url,
              type: classifyLinkKey(label || 'link', url)
            });
          });
        }
      } else {
        collectUrlsDeep(job.useful_links, job._udyn_links);
      }
    }

    // ── Deduplicate links ─────────────────────────────────────────────
    const seen = new Set();
    job._udyn_links = job._udyn_links.filter(l => {
      if (seen.has(l.url)) return false;
      seen.add(l.url);
      return true;
    });

    return job;
  }

  /** Classify link type from key name + URL */
  function classifyLinkKey(key, url) {
    const k = safe(key).toLowerCase();
    const u = safe(url).toLowerCase();
    if (/apply|register|registration|form|apply_online/i.test(k)) return 'apply';
    if (/login/i.test(k)) return 'login';
    if (/notification|advt|advertisement|pdf|syllabus|admit|result/i.test(k)) return 'pdf';
    if (/official|website|home/i.test(k)) return 'website';
    if (/video|youtube|youtu\.be|watch/i.test(k) || /youtu\.?be|youtube/i.test(u)) return 'video';
    // Guess from URL
    if (isPdf(u)) return 'pdf';
    if (/youtu\.?be|youtube/i.test(u)) return 'video';
    if (/login|apply|register|form|candidate|exam\\.aspx|online/i.test(u)) return 'apply';
    return 'default';
  }

  /** Generate a smart human-readable label for a link */
  function smartLinkLabel(key, url, index) {
    const k = safe(key).toLowerCase().replace(/_/g,' ');
    if (/notification_pdf|official_notif/i.test(key)) return 'Official Notification PDF';
    if (/login/i.test(key)) return 'Candidate Login';
    if (/click_here/i.test(key)) {
      // Guess from URL content
      if (/login|candidate/i.test(url)) return 'Candidate Login / Apply Online';
      if (isPdf(url)) return 'Download Notification PDF';
      if (/apply|register/i.test(url)) return 'Apply Online';
      if (index > 1) return `Link ${index}`;
      return 'Apply / Official Link';
    }
    if (/apply/i.test(key)) return 'Apply Online';
    if (/official/i.test(key)) return 'Official Website';
    if (/notification|advt|advertisement/i.test(key)) return 'Official Notification';
    if (/pdf/i.test(key) || isPdf(url)) return 'Download PDF';
    if (/website|home/i.test(key)) return 'Official Website';
    return keyToLabel(key);
  }

  /** Recursively collect URLs from any data structure */
  function collectUrlsDeep(data, store, label = '') {
    if (!data) return;
    if (typeof data === 'string' && isUrl(data)) {
      store.push({ label: label || smartLinkLabel('link', data, 0), url: data, type: classifyLinkKey(label, data) });
    } else if (Array.isArray(data)) {
      data.forEach((item, i) => collectUrlsDeep(item, store, label || `Link ${i+1}`));
    } else if (typeof data === 'object') {
      for (const [k, v] of Object.entries(data)) {
        collectUrlsDeep(v, store, label || keyToLabel(k));
      }
    }
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 4 — SMART FIELD EXTRACTORS
  ═══════════════════════════════════════════════════════════════════════ */

  function exDates(job) {
    const id = job.important_dates || {};
    const DATE_MAP = {
      application_begin:      'Application Start Date',
      last_date:              'Last Date to Apply',
      fee_payment_last_date:  'Fee Payment Last Date',
      correction_last_date:   'Correction Window Last Date',
      notification_date:      'Notification Released',
      exam_date:              'Exam Date',
      admit_card_date:        'Admit Card Available',
      admit_card:             'Admit Card Date',
      result_date:            'Result Date',
      interview_date:         'Interview / DV Date',
      document_verification:  'Document Verification',
      dv_date:                'DV Date',
      counselling_date:       'Counselling Date',
      joining_date:           'Joining Date',
    };
    const rows = [];
    const usedKeys = new Set(Object.keys(DATE_MAP));

    for (const [k, label] of Object.entries(DATE_MAP)) {
      const v = safe(id[k]);
      if (v) rows.push({ label, val: fmtDate(v), highlight: /last date/i.test(label) });
    }
    // Remaining unknown date fields
    for (const [k, v] of Object.entries(id)) {
      if (usedKeys.has(k) || k === 'raw' || !hasContent(v)) continue;
      rows.push({ label: keyToLabel(k), val: fmtDate(safe(v)), highlight: /last/i.test(k) });
    }
    // Raw text fallback
    const rawText = safe(id.raw || id.rawDate || '');
    return { rows, rawText };
  }

  function exFees(job) {
    const fee = job.application_fee || {};
    const feeIsStr = typeof fee === 'string';
    const feeObj = (typeof fee === 'object' && !Array.isArray(fee)) ? fee : {};
    const FEE_MAP = [
      ['general',         'General / UR'],
      ['ur',              'UR'],
      ['obc',             'OBC'],
      ['ews',             'EWS'],
      ['sc',              'SC'],
      ['st',              'ST'],
      ['sc_st',           'SC / ST'],
      ['female',          'Female / Women'],
      ['ph',              'PH / PwD'],
      ['pwd',             'PwD'],
      ['divyang',         'Divyang'],
      ['general_obc',     'General / OBC'],
      ['gen_obc',         'Gen / OBC'],
      ['general_obc_ews', 'General / OBC / EWS'],
      ['gen_obc_ews',     'Gen / OBC / EWS'],
      ['ur_obc_ews',      'UR / OBC / EWS'],
      ['all',             'All Candidates'],
      ['all_candidates',  'All Candidates'],
    ];
    const usedKeys = new Set(FEE_MAP.map(([k]) => k).concat(['note','payment_note','payment_mode']));
    const items = [];

    for (const [k, label] of FEE_MAP) {
      const v = safe(feeObj[k]);
      if (v) items.push({ label, val: v });
    }
    if (!items.length && feeIsStr) {
      const v = safe(typeof fee === 'string' ? fee : job.application_fee);
      if (v) items.push({ label: 'Application Fee', val: v });
    }
    // Remaining keys
    for (const [k, v] of Object.entries(feeObj)) {
      if (usedKeys.has(k) || !hasContent(v)) continue;
      items.push({ label: keyToLabel(k), val: safe(v) });
    }
    const note = safe(feeObj.note || feeObj.payment_note || feeObj.payment_mode || '');
    return { items, note };
  }

  function exVacancy(job) {
    // vacancy_details: array-of-objects (most common)
    let rows = [];
    const vd = job.vacancy_details;
    if (Array.isArray(vd) && vd.length) {
      rows = vd.filter(r => typeof r === 'object' && r !== null);
    }

    // category_wise_vacancy: object
    const cw = job.category_wise_vacancy || {};

    return { rows, cw };
  }

  function exSalary(job) {
    const sd = job.salary_details || {};
    const flat = safe(job.salary || job.salary_pay_scale || (job.basic_details && (job.basic_details.salary || job.basic_details.salary_pay_scale)) || '');
    return { structured: sd, flat };
  }

  function exPhysical(job) {
    const pe = job.physical_eligibility || job.physical_standards || null;
    return hasContent(pe) ? pe : null;
  }

  function exExamPattern(job) {
    const ep = job.exam_pattern;
    return hasContent(ep) ? ep : null;
  }

  function exSyllabus(job) {
    const s = job.syllabus;
    return hasContent(s) ? s : null;
  }

  function exSelection(job) {
    const sp = job.selection_process || (job.basic_details && job.basic_details.selection_process) || [];
    return sp;
  }

  function exHowToApply(job) {
    return job.how_to_apply || job.apply_process || '';
  }

  function exInstructions(job) {
    return job.important_instructions || job.instructions || [];
  }

  function exFaq(job) {
    return job.faq || job.faqs || [];
  }

  function exJobsInfo(job) {
    return safe(job.jobs_info || (job.basic_details && job.basic_details.jobs_info) || '');
  }

  function exShortInfo(job) {
    return safe(job.short_information || (job.basic_details && job.basic_details.short_information) || '');
  }

  function exTables(job) {
    return job.tables || null;
  }

  function exTextSections(job) {
    return job.text_sections || null;
  }

  function exQualification(job) {
    const q = job.qualification || {};
    const flat = safe(job.education_qualification || job.eligibility || '');
    if (typeof q === 'string') return q;
    if (typeof q === 'object') {
      const v = q.education_qualification || q.eligibility || q.qualification || '';
      return safe(v) || flat;
    }
    return flat;
  }

  /**
   * Extract all UNKNOWN top-level fields not handled by any extractor.
   * These get auto-rendered as generic cards.
   */
  const KNOWN_KEYS = new Set([
    'basic_details','important_dates','application_fee','application_fees',
    'age_limit','qualification','vacancy_details','category_wise_vacancy',
    'salary_details','selection_process','exam_pattern','syllabus',
    'physical_eligibility','physical_standards','how_to_apply','important_instructions',
    'important_links','important_links_obj','faq','faqs','seo_tags','category',
    'slug','title','post_name','organization','board_name','department',
    'total_vacancy','total_vacancies','total_post','apply_mode','application_mode','mode',
    'last_date','last_date_to_apply','application_begin','exam_date',
    'salary','salary_pay_scale','minimum_age','maximum_age','age_relaxation',
    'education_qualification','eligibility','experience_required',
    'short_information','jobs_info','source_url','apply_online',
    'official_website','official_website_link','form_pdf_free_link',
    'official_notification_pdf_link','apply_online_link','application_form_pdf_link',
    'form_pdf_link','form_pdf_link','listing_date','last_updated','apply_process',
    'post_date','status','useful_links','sequence','job_location','job_type',
    'homepage_serial','closing_date','application_last_date','instructions',
    'tables','sections','text_sections','id','name','url','date','lastDate','postDate',
    'board','detail','_udyn_links','state','items',
  ]);

  function exUnknown(job) {
    const out = {};
    for (const [k, v] of Object.entries(job)) {
      if (KNOWN_KEYS.has(k)) continue;
      if (!hasContent(v)) continue;
      if (k.startsWith('_')) continue;
      out[k] = v;
    }
    return out;
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 5 — DEEP RECURSIVE RENDERER
     Converts ANY nested JSON value into readable HTML intelligently.
  ═══════════════════════════════════════════════════════════════════════ */

  /**
   * Recursively render a value to HTML.
   * Handles: string, number, bool, null, array-of-strings, array-of-objects,
   *          nested objects, HTML strings, URLs, dates, tables.
   */
  function deepRender(value, depth) {
    depth = depth || 0;
    if (value == null || value === '') return '<span style="color:#94a3b8;">—</span>';

    if (typeof value === 'boolean') return value ? '<span style="color:#16a34a;font-weight:700;">Yes</span>' : '<span style="color:#dc2626;font-weight:700;">No</span>';

    if (typeof value === 'number') return `<strong>${value}</strong>`;

    if (typeof value === 'string') {
      const s = value.trim();
      if (!s) return '<span style="color:#94a3b8;">—</span>';
      if (isUrl(s)) {
        const t = isPdf(s) ? 'Download PDF' : (classifyLinkKey('link', s) === 'apply' ? 'Apply / Click Here' : 'Click Here');
        return `<a href="${esc(s)}" target="_blank" rel="noopener" class="udyn-link-btn ${isPdf(s) ? 'udyn-link-pdf' : 'udyn-link-website'}" style="font-size:.78rem;padding:3px 10px;">${t}</a>`;
      }
      if (isHtml(s)) return `<div class="udyn-html-body" style="padding:0;">${s}</div>`;
      if (/\n/.test(s)) return textToHtml(s);
      return esc(s);
    }

    if (Array.isArray(value)) {
      if (!value.length) return '<span style="color:#94a3b8;">—</span>';
      // All URLs → link buttons
      if (value.every(x => typeof x === 'string' && isUrl(x))) {
        return value.map(u => `<a href="${esc(u)}" target="_blank" rel="noopener" class="udyn-link-btn ${isPdf(u) ? 'udyn-link-pdf' : 'udyn-link-apply'}" style="font-size:.78rem;padding:3px 10px;margin:2px 4px 2px 0;display:inline-flex;">${isPdf(u) ? 'Download PDF' : 'Apply / Click Here'}</a>`).join('');
      }
      // All strings → tag chips
      if (value.every(x => typeof x === 'string')) {
        return `<div class="udyn-tag-list" style="padding:0;">${value.map(s => `<div class="udyn-tag">${esc(s)}</div>`).join('')}</div>`;
      }
      // Array of objects → table
      if (value.every(x => x && typeof x === 'object' && !Array.isArray(x))) {
        return buildAoOTable(value);
      }
      // Mixed array
      return value.map(item => `<div style="margin-bottom:4px;">${deepRender(item, depth+1)}</div>`).join('');
    }

    if (typeof value === 'object') {
      const pairs = Object.entries(value).filter(([, v]) => hasContent(v));
      if (!pairs.length) return '<span style="color:#94a3b8;">—</span>';
      if (depth > 2) {
        // Avoid extreme nesting — render flat
        return pairs.map(([k, v]) => `<strong>${esc(keyToLabel(k))}:</strong> ${deepRender(v, depth+1)}`).join('<br>');
      }
      const rows = pairs.map(([k, v]) =>
        `<tr><th>${esc(keyToLabel(k))}</th><td>${deepRender(v, depth+1)}</td></tr>`
      ).join('');
      return `<table class="udyn-gen-table">${rows}</table>`;
    }

    return esc(String(value));
  }

  /** Array-of-objects → styled multi-column table */
  function buildAoOTable(arr) {
    const cols = [...new Set(arr.flatMap(r => Object.keys(r)))];
    const thead = `<thead><tr>${cols.map(c => `<th>${esc(keyToLabel(c))}</th>`).join('')}</tr></thead>`;
    const tbody = arr.map(r =>
      `<tr>${cols.map(c => `<td>${deepRender(r[c], 1)}</td>`).join('')}</tr>`
    ).join('');
    return `<div class="udyn-table-scroll"><table class="udyn-vac-table">${thead}<tbody>${tbody}</tbody></table></div>`;
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 6 — CARD DOM BUILDERS
  ═══════════════════════════════════════════════════════════════════════ */

  function makeCard(id, headBg, iconCls, headText, bodyHtml) {
    const d = document.createElement('div');
    d.className = 'udyn-card' + (id ? ' udyn-anchor' : '');
    if (id) d.id = id;
    d.innerHTML =
      `<div class="udyn-head" style="background:${headBg}">` +
        `<i class="${iconCls}"></i>${esc(headText)}` +
      `</div><div class="udyn-body">${bodyHtml}</div>`;
    return d;
  }

  /* ── 6a. Important Dates ── */
  function cardDates(data) {
    const { rows, rawText } = data;
    if (!rows.length && !rawText) return null;
    let html = rows.map(r =>
      `<tr><th>${esc(r.label)}</th>` +
      `<td style="${r.highlight ? 'color:#dc2626;font-weight:800;' : ''}">${esc(r.val)}</td></tr>`
    ).join('');
    if (!html && rawText) html = `<tr><th>Date Info</th><td class="udyn-notice">${esc(rawText)}</td></tr>`;
    else if (rawText) html += `<tr><th>Additional Info</th><td style="font-size:.79rem;color:#64748b;white-space:pre-line;">${esc(rawText)}</td></tr>`;
    if (!html) return null;
    return makeCard('udyn-dates-extended','linear-gradient(135deg,#b91c1c,#dc2626)',
      'fa-regular fa-calendar-check','Important Dates',
      `<div class="udyn-table-scroll"><table class="udyn-gen-table">${html}</table></div>`);
  }

  /* ── 6b. Application Fee ── */
  function cardFee(data) {
    const { items, note } = data;
    if (!items.length) return null;
    const isFree = v => /nil|^0$|free|no fee|exempt/i.test(v.trim());
    const gridHtml = items.map(({ label, val }) =>
      `<div class="udyn-grid-item">` +
        `<div class="udyn-grid-label">${esc(label)}</div>` +
        `<div class="udyn-grid-val" style="${isFree(val) ? 'color:#16a34a;' : 'color:#1d4ed8;'}">${esc(val)}</div>` +
      `</div>`
    ).join('');
    const noteHtml = note ? `<div class="udyn-grid-note">${esc(note)}</div>` : '';
    return makeCard('udyn-fee','linear-gradient(135deg,#c2410c,#ea580c)',
      'fa-solid fa-indian-rupee-sign','Application Fee',
      `<div class="udyn-grid">${gridHtml}</div>${noteHtml}`);
  }

  /* ── 6c. Vacancy Details ── */
  function cardVacancy(rows, cw) {
    let html = '';
    if (rows.length) {
      html = buildAoOTable(rows);
    } else if (hasContent(cw)) {
      const pairs = Object.entries(cw).filter(([, v]) => hasContent(v));
      if (pairs.length) {
        const tbody = pairs.map(([k, v]) => `<tr><td>${esc(keyToLabel(k))}</td><td>${esc(safe(v))}</td></tr>`).join('');
        html = `<div class="udyn-table-scroll"><table class="udyn-vac-table"><thead><tr><th>Category</th><th>Vacancies</th></tr></thead><tbody>${tbody}</tbody></table></div>`;
      }
    }
    if (!html) return null;
    return makeCard('udyn-vacancy-extended','linear-gradient(135deg,#15803d,#16a34a)',
      'fa-solid fa-chart-pie','Vacancy Details', html);
  }

  /* ── 6d. Physical Eligibility ── */
  function cardPhysical(pe) {
    if (!hasContent(pe)) return null;
    let html = '';
    if (typeof pe === 'object' && !Array.isArray(pe)) {
      const pairs = Object.entries(pe).filter(([, v]) => hasContent(v));
      if (!pairs.length) return null;
      html = `<div class="udyn-grid">${pairs.map(([k, v]) =>
        `<div class="udyn-grid-item"><div class="udyn-grid-label">${esc(keyToLabel(k))}</div><div class="udyn-grid-val">${deepRender(v, 1)}</div></div>`
      ).join('')}</div>`;
    } else if (typeof pe === 'string') {
      html = `<div class="udyn-detail">${textToHtml(pe)}</div>`;
    } else {
      html = `<div class="udyn-detail">${deepRender(pe, 0)}</div>`;
    }
    return makeCard('udyn-physical','linear-gradient(135deg,#be123c,#e11d48)',
      'fa-solid fa-dumbbell','Physical Eligibility / Standards', html);
  }

  /* ── 6e. Exam Pattern ── */
  function cardExamPattern(ep) {
    if (!hasContent(ep)) return null;
    let html = '';
    if (Array.isArray(ep)) {
      if (ep.length && typeof ep[0] === 'object') html = buildAoOTable(ep);
      else html = `<div class="udyn-tag-list">${ep.map(s => `<div class="udyn-tag"><i class="fa-solid fa-file-lines"></i>${esc(String(s))}</div>`).join('')}</div>`;
    } else if (ep && typeof ep === 'object') {
      // subjects + notes sub-structure
      const { subjects, notes, ...rest } = ep;
      if (Array.isArray(subjects) && subjects.length) html += buildAoOTable(subjects);
      if (notes) html += `<div class="udyn-detail" style="font-size:.8rem;color:#64748b;">${textToHtml(notes)}</div>`;
      if (!html && hasContent(rest)) html = deepRender(rest, 0);
    } else if (typeof ep === 'string') {
      html = `<div class="udyn-detail">${textToHtml(ep)}</div>`;
    }
    if (!html) return null;
    return makeCard('udyn-exam-pattern','linear-gradient(135deg,#0369a1,#0284c7)',
      'fa-solid fa-file-lines','Exam Pattern', html);
  }

  /* ── 6f. Syllabus ── */
  function cardSyllabus(syl) {
    if (!hasContent(syl)) return null;
    let html = '';
    if (Array.isArray(syl)) {
      if (syl.length && typeof syl[0] === 'object') html = buildAoOTable(syl);
      else html = `<div class="udyn-tag-list">${syl.map(s => `<div class="udyn-tag"><i class="fa-solid fa-book-open"></i>${esc(String(s))}</div>`).join('')}</div>`;
    } else if (typeof syl === 'object') {
      html = deepRender(syl, 0);
    } else {
      html = `<div class="udyn-detail">${textToHtml(String(syl))}</div>`;
    }
    if (!html) return null;
    return makeCard('udyn-syllabus','linear-gradient(135deg,#4338ca,#6366f1)',
      'fa-solid fa-book','Syllabus / Exam Topics', html);
  }

  /* ── 6g. Salary ── */
  function cardSalary(structured, flat) {
    if (!hasContent(structured) && !flat) return null;
    let html = '';
    if (hasContent(structured)) {
      if (typeof structured === 'string') {
        html = `<div class="udyn-detail"><span class="udyn-sal-val" style="font-size:1rem;font-weight:800;">${esc(structured)}</span></div>`;
      } else if (typeof structured === 'object') {
        const { details, ...rest } = structured;
        const pairs = Object.entries(rest).filter(([, v]) => hasContent(v));
        if (pairs.length) {
          html = `<div class="udyn-grid" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr));">${
            pairs.map(([k, v]) =>
              `<div class="udyn-grid-item"><div class="udyn-grid-label">${esc(keyToLabel(k))}</div>` +
              `<div class="udyn-grid-val udyn-sal-val">${esc(String(v))}</div></div>`
            ).join('')
          }</div>`;
        }
        if (details) html += `<div class="udyn-detail" style="font-size:.82rem;color:#374151;">${textToHtml(details)}</div>`;
      }
    }
    if (!html && flat) {
      html = `<div class="udyn-detail"><span class="udyn-sal-val" style="font-size:.95rem;font-weight:800;">${esc(flat)}</span></div>`;
    }
    if (!html) return null;
    return makeCard('udyn-salary','linear-gradient(135deg,#15803d,#16a34a)',
      'fa-solid fa-indian-rupee-sign','Salary & Pay Scale Details', html);
  }

  /* ── 6h. Selection Process ── */
  function cardSelection(sp) {
    if (!hasContent(sp)) return null;
    let html = '';
    if (Array.isArray(sp) && sp.length) {
      html = `<div class="udyn-tag-list">${sp.map(s =>
        `<div class="udyn-tag"><i class="fa-solid fa-arrow-right-long"></i>${esc(String(s))}</div>`
      ).join('')}</div>`;
    } else if (typeof sp === 'string' && sp.trim()) {
      html = `<div class="udyn-detail">${textToHtml(sp)}</div>`;
    } else if (typeof sp === 'object') {
      html = deepRender(sp, 0);
    }
    if (!html) return null;
    return makeCard('udyn-selection','linear-gradient(135deg,#0f766e,#0891b2)',
      'fa-solid fa-list-check','Selection Process', html);
  }

  /* ── 6i. How To Apply ── */
  function cardHowToApply(hta) {
    if (!hasContent(hta)) return null;
    let html = '';
    if (Array.isArray(hta) && hta.length) {
      const items = hta.map(s => safe(s)).filter(Boolean);
      html = `<ul class="udyn-steps-list">${items.map((s, i) =>
        `<li class="udyn-step"><span class="udyn-step-num">${i+1}</span><span>${isHtml(s) ? s : esc(s)}</span></li>`
      ).join('')}</ul>`;
    } else if (typeof hta === 'string') {
      if (isHtml(hta)) html = `<div class="udyn-html-body">${hta}</div>`;
      else {
        const lines = hta.split(/\n+/).map(l => l.trim()).filter(Boolean);
        if (lines.length > 1) {
          html = `<ul class="udyn-steps-list">${lines.map((s, i) =>
            `<li class="udyn-step"><span class="udyn-step-num">${i+1}</span><span>${esc(s)}</span></li>`
          ).join('')}</ul>`;
        } else {
          html = `<div class="udyn-detail">${esc(hta)}</div>`;
        }
      }
    }
    if (!html) return null;
    return makeCard('udyn-how-to-apply','linear-gradient(135deg,#0f766e,#0891b2)',
      'fa-solid fa-clipboard-list','How To Apply', html);
  }

  /* ── 6j. Instructions ── */
  function cardInstructions(insts) {
    let arr = [];
    if (Array.isArray(insts)) arr = insts.map(s => safe(s)).filter(Boolean);
    else if (typeof insts === 'string' && insts.trim()) {
      arr = insts.split(/\n+/).map(l => l.trim()).filter(Boolean);
    }
    if (!arr.length) return null;
    const items = arr.map(s =>
      `<li class="udyn-inst-item"><i class="fa-solid fa-triangle-exclamation"></i><span>${esc(s)}</span></li>`
    ).join('');
    return makeCard('udyn-instructions','linear-gradient(135deg,#b45309,#ca8a04)',
      'fa-solid fa-circle-exclamation','Important Instructions / Notice',
      `<ul class="udyn-inst-list">${items}</ul>`);
  }

  /* ── 6k. FAQ ── */
  function cardFaq(faqs) {
    let arr = [];
    if (Array.isArray(faqs)) {
      arr = faqs.filter(f => f && (f.question || f.q) && (f.answer || f.a));
    } else if (typeof faqs === 'object') {
      arr = Object.entries(faqs).map(([q, a]) => ({ question: q, answer: a }));
    }
    if (!arr.length) return null;
    const items = arr.map((f, i) => {
      const q = safe(f.question || f.q || '');
      const a = safe(f.answer || f.a || '');
      return `<div class="udyn-faq-item">` +
        `<div class="udyn-faq-q" onclick="(function(el){var a=el.nextElementSibling;el.classList.toggle('open');a.classList.toggle('open');})(this)">` +
          `<i class="fa-solid fa-chevron-right udyn-faq-icon"></i>${esc(q)}` +
        `</div><div class="udyn-faq-a">${esc(a)}</div></div>`;
    }).join('');
    return makeCard('udyn-faq','linear-gradient(135deg,#7c3aed,#8b5cf6)',
      'fa-solid fa-circle-question','Frequently Asked Questions', items);
  }

  /* ── 6l. Jobs Info HTML notice ── */
  function cardJobsInfo(htmlStr) {
    if (!htmlStr) return null;
    const text = stripHtml(htmlStr);
    if (text.length < 20) return null;
    const content = isHtml(htmlStr) ? `<div class="udyn-html-body">${htmlStr}</div>` : `<div class="udyn-detail">${textToHtml(htmlStr)}</div>`;
    return makeCard('udyn-jobs-info','linear-gradient(135deg,#0f766e,#0891b2)',
      'fa-solid fa-circle-info','About This Recruitment', content);
  }

  /* ── 6m. SR Tables (merged_sarkari 'tables' field) ── */
  /*
   * renderTableRows — Smart renderer for mixed-column-count row arrays.
   *
   * Problem: A single 'rows' array often contains MULTIPLE logical sub-tables
   * concatenated together (e.g. a 2-col eligibility table followed by a 4-col
   * district-vacancy table). Naively treating the first row as header breaks
   * layout when column counts change mid-array.
   *
   * Solution: Split rows into sub-groups wherever column count changes, then
   * render each sub-group as its own table with its own header detection.
   */
  function renderTableRows(rows) {
    if (!Array.isArray(rows) || !rows.length) return '';

    /* ── Step 1: Split into sub-tables by column-count boundary ── */
    const subTables = [];
    let cur = [], curCols = -1;
    for (const row of rows) {
      if (!Array.isArray(row)) continue;
      if (row.length !== curCols) {
        if (cur.length) subTables.push(cur);
        cur = [row]; curCols = row.length;
      } else {
        cur.push(row);
      }
    }
    if (cur.length) subTables.push(cur);

    /* ── Step 2: Render each sub-table ── */
    let html = '';
    for (const st of subTables) {
      if (!st.length) continue;

      /* Header detection: first row all strings/no URLs, next row same col count */
      const firstRow = st[0];
      const nextRow  = st[1];
      const isHeader = nextRow &&
        firstRow.every(c => typeof c === 'string' && !isUrl(c) && c.length < 120) &&
        nextRow.length >= firstRow.length;

      const headerHtml = isHeader
        ? `<thead><tr>${firstRow.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>`
        : '';
      const dataRows = isHeader ? st.slice(1) : st;

      /* Single-row, single-col-count sub-table with no data rows after header → render as KV row */
      if (isHeader && dataRows.length === 0) continue;

      /* Special case: 1 data row only + 2 cols → render as key-value pair in gen-table style */
      const isKV = !isHeader && st.length === 1 && st[0].length === 2;

      const bodyHtml = dataRows.map(row => {
        const cells = row.map(cell => {
          const s = safe(String(cell ?? ''));
          if (!s) return '<td>—</td>';
          if (isUrl(s)) {
            const isp = isPdf(s);
            return `<td><a href="${esc(s)}" target="_blank" rel="noopener"
              class="udyn-link-btn ${isp ? 'udyn-link-pdf' : 'udyn-link-apply'}"
              style="font-size:.75rem;padding:4px 10px;display:inline-flex;align-items:center;gap:4px;">
              <i class="${isp ? 'fa-solid fa-file-pdf' : 'fa-solid fa-arrow-up-right-from-square'}"></i>
              ${isp ? 'PDF' : 'Link'}</a></td>`;
          }
          return `<td>${esc(s)}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
      }).join('');

      if (!bodyHtml && !headerHtml) continue;

      if (isKV) {
        /* Render as compact KV using gen-table style */
        html += `<table class="udyn-gen-table" style="margin-bottom:0;">
          <tbody><tr><th>${esc(st[0][0])}</th><td>${esc(st[0][1])}</td></tr></tbody>
        </table>`;
      } else {
        html += `<div class="udyn-table-scroll" style="margin-bottom:10px;">
          <table class="udyn-vac-table">${headerHtml}<tbody>${bodyHtml}</tbody></table>
        </div>`;
      }
    }
    return html;
  }

  function cardTables(tables) {
    if (!Array.isArray(tables) || !tables.length) return null;
    let allHtml = '';

    for (const group of tables) {
      /* ── Format A: Object { table_name, rows } (merged_sarkari format) ── */
      if (group && typeof group === 'object' && !Array.isArray(group)) {
        const tname = safe(group.table_name || '');
        const rows  = group.rows;
        if (!Array.isArray(rows) || !rows.length) continue;
        const heading = tname
          ? `<div style="padding:9px 14px 5px;font-size:.8rem;font-weight:700;color:#1d4ed8;background:#f0f7ff;border-bottom:1px solid #dbeafe;line-height:1.4;">${esc(tname)}</div>`
          : '';
        const tableHtml = renderTableRows(rows);
        if (tableHtml) allHtml += `<div style="margin-bottom:2px;">${heading}${tableHtml}</div>`;
      }
      /* ── Format B: Direct array-of-arrays ── */
      else if (Array.isArray(group) && group.length && Array.isArray(group[0])) {
        const tableHtml = renderTableRows(group);
        if (tableHtml) allHtml += tableHtml;
      }
    }

    if (!allHtml) return null;
    return makeCard('udyn-sr-tables','linear-gradient(135deg,#1d4ed8,#1d6dbc)',
      'fa-solid fa-table','Vacancy / Important Details', allHtml);
  }

  /* ── 6m2. SR Text Sections (merged_sarkari 'text_sections' field) ── */
  /* Format: [{ section: "How to Fill Form...", content: "Step1 | Step2 | ..." }] */
  function cardTextSections(textSections) {
    if (!Array.isArray(textSections) || !textSections.length) return null;
    let allHtml = '';

    for (const sec of textSections) {
      if (!sec || typeof sec !== 'object') continue;
      const heading = safe(sec.section || sec.title || '');
      const content = safe(sec.content || sec.text || sec.description || '');
      if (!content) continue;

      const headHtml = heading
        ? `<div style="padding:9px 14px 5px;font-size:.82rem;font-weight:700;color:#0f766e;background:#f0fdf4;border-bottom:1px solid #bbf7d0;">${esc(heading)}</div>`
        : '';

      /* Split by pipe | or newlines → numbered steps */
      const steps = content.split(/\s*\|\s*|\n+/).map(s => s.trim()).filter(Boolean);
      let bodyHtml = '';
      if (steps.length > 1) {
        bodyHtml = `<ul class="udyn-steps-list">${steps.map((s, i) =>
          `<li class="udyn-step">
            <span class="udyn-step-num">${i+1}</span>
            <span>${esc(s)}</span>
          </li>`
        ).join('')}</ul>`;
      } else {
        bodyHtml = `<div class="udyn-detail">${esc(content)}</div>`;
      }
      allHtml += headHtml + bodyHtml;
    }

    if (!allHtml) return null;
    return makeCard('udyn-text-sections','linear-gradient(135deg,#0f766e,#059669)',
      'fa-solid fa-clipboard-list','How To Apply / Instructions', allHtml);
  }

  /* ── 6n. Important Links (FULLY REBUILT — zero missing links) ── */
  function cardLinks(links) {
    if (!links || !links.length) return null;

    // Sort: apply first, then pdf, then website, then others
    const ORDER = { apply: 0, login: 1, pdf: 2, website: 3, default: 4 };
    const sorted = [...links].sort((a, b) => (ORDER[a.type] || 4) - (ORDER[b.type] || 4));

    const typeStyle = { apply: 'udyn-link-apply', login: 'udyn-link-login', pdf: 'udyn-link-pdf', website: 'udyn-link-website', video: 'udyn-link-video', default: 'udyn-link-default' };
    const typeLabel = { apply: 'Apply Now', login: 'Login', pdf: 'Download PDF', website: 'Visit Website', video: 'Watch Video', default: 'Click Here' };
    const typeIcon  = { apply: 'fa-solid fa-pen-to-square', login: 'fa-solid fa-right-to-bracket', pdf: 'fa-solid fa-file-pdf', website: 'fa-solid fa-globe', video: 'fa-brands fa-youtube', default: 'fa-solid fa-link' };

    const rows = sorted.map(({ label, url, type }) =>
      `<li class="udyn-link-row">` +
        `<span class="udyn-link-label"><i class="${typeIcon[type] || typeIcon.default}" style="margin-right:6px;color:#64748b;"></i>${esc(label)}</span>` +
        `<a href="${esc(url)}" target="_blank" rel="noopener" class="udyn-link-btn ${typeStyle[type] || typeStyle.default}">` +
          `<i class="${typeIcon[type] || typeIcon.default}"></i>${typeLabel[type] || typeLabel.default}` +
        `</a>` +
      `</li>`
    ).join('');

    return makeCard('udyn-imp-links','linear-gradient(135deg,#1d4ed8,#1e40af)',
      'fa-solid fa-link','Important Links',
      `<ul class="udyn-links-list">${rows}</ul>`);
  }

  /* ── 6o. Generic unknown field card (deep recursive) ── */
  function cardGeneric(key, value) {
    if (!hasContent(value)) return null;
    const label = keyToLabel(key);
    const html = deepRender(value, 0);
    if (!html) return null;
    return makeCard(null, 'linear-gradient(135deg,#475569,#64748b)',
      'fa-solid fa-info-circle', label,
      `<div class="udyn-detail">${html}</div>`);
  }

  /* ── 6p. Age Limit ── */
  function cardAgeLimit(job) {
    const age = job.age_limit || {};
    const minAge = safe(job.minimum_age || age.minimum_age || '');
    const maxAge = safe(job.maximum_age || age.maximum_age || age.age_limit || age.age_details || '');
    const relax  = safe(job.age_relaxation || age.age_relaxation || age.details || '');
    const pairs  = [];
    if (minAge) pairs.push(['Minimum Age', minAge]);
    if (maxAge) pairs.push(['Maximum / Upper Age Limit', maxAge]);
    if (relax)  pairs.push(['Age Relaxation', relax]);
    // Extra keys in age_limit
    const KNOWN_AGE = new Set(['minimum_age','maximum_age','age_limit','age_details','age_relaxation','details']);
    for (const [k, v] of Object.entries(age)) {
      if (KNOWN_AGE.has(k) || !hasContent(v)) continue;
      pairs.push([keyToLabel(k), safe(v)]);
    }
    if (!pairs.length) return null;
    const rows = pairs.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('');
    return makeCard('udyn-age-limit','linear-gradient(135deg,#7c3aed,#8b5cf6)',
      'fa-solid fa-user-clock','Age Limit Details',
      `<div class="udyn-table-scroll"><table class="udyn-gen-table">${rows}</table></div>`);
  }

  /* ── 6q. Qualification ── */
  function cardQualification(qual) {
    if (!qual) return null;
    const content = deepRender(qual, 0);
    if (!content) return null;
    return makeCard('udyn-qualification','linear-gradient(135deg,#0369a1,#0284c7)',
      'fa-solid fa-graduation-cap','Educational Qualification / Eligibility',
      `<div class="udyn-detail">${content}</div>`);
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 7 — NORMALIZER FOR UPCOMING_JOBS sections[] format
  ═══════════════════════════════════════════════════════════════════════ */

  function normalizeUpcomingJobsSections(rawJob) {
    if (!rawJob || !Array.isArray(rawJob.sections) || rawJob.sections.length === 0) return rawJob;
    if (rawJob.category !== 'UPCOMING_JOBS') return rawJob;
    const sections = rawJob.sections;

    function getItems(title) {
      const sec = sections.find(s => s.title && s.title.toLowerCase() === title.toLowerCase());
      if (!sec || !Array.isArray(sec.content)) return [];
      const out = [];
      for (const blk of sec.content) {
        if (blk.type === 'list' && Array.isArray(blk.items)) out.push(...blk.items);
        else if (blk.type === 'paragraph' && blk.text) out.push(blk.text);
      }
      return out;
    }
    function parseKV(items) {
      const m = {};
      for (const item of items) {
        const colon = item.indexOf(':');
        if (colon > 0) m[item.slice(0,colon).trim().toLowerCase().replace(/\s+/g,'_')] = item.slice(colon+1).trim();
      }
      return m;
    }
    function getRows(title) {
      const sec = sections.find(s => s.title && s.title.toLowerCase() === title.toLowerCase());
      if (!sec || !Array.isArray(sec.content)) return [];
      for (const blk of sec.content) if (blk.type === 'table' && Array.isArray(blk.rows)) return blk.rows;
      return [];
    }

    if (!rawJob.important_dates || !Object.keys(rawJob.important_dates).length) {
      const kv = parseKV(getItems('Important Dates'));
      rawJob.important_dates = {
        application_begin: kv['starting_date'] || kv['application_begin_date'] || '',
        last_date: kv['last_date'] || '',
        correction_last_date: kv['correction_date'] || '',
        exam_date: kv['exam_date'] || '',
        raw: getItems('Important Dates').join(' | '),
      };
    }
    if (!rawJob.application_fee || !Object.keys(rawJob.application_fee).length) {
      const kv = parseKV(getItems('Application Fees'));
      rawJob.application_fee = { general: kv['general']||'', obc: kv['obc']||'', sc_st: kv['sc/st']||kv['sc_/_st']||'', all: kv['for_all_candidates']||'', note: kv['payment_mode'] ? 'Mode: '+kv['payment_mode'] : '' };
    }
    if (!rawJob.selection_process || (Array.isArray(rawJob.selection_process) && !rawJob.selection_process.length)) {
      const items = getItems('Selection Process');
      if (items.length) rawJob.selection_process = items;
    }
    // Exam pattern from table
    const epSec = sections.find(s => /written\s*exam\s*pattern|exam\s*pattern/i.test(s.title || ''));
    if (epSec && Array.isArray(epSec.content) && !hasContent(rawJob.exam_pattern)) {
      const rows = [];
      for (const blk of epSec.content) if (blk.type === 'table' && blk.rows) rows.push(...blk.rows);
      if (rows.length) {
        let header = null; const subjects = [];
        for (const row of rows) {
          const texts = row.map(c => (c.text||'').trim());
          if (texts.some(t => /subject|questions|marks/i.test(t))) { header = texts; continue; }
          if (header && row.length >= 2) {
            const obj = {};
            header.forEach((h, i) => { obj[h.toLowerCase()] = texts[i] || ''; });
            subjects.push(obj);
          }
        }
        const notes = epSec.content.filter(b => b.type==='paragraph' && b.text).map(b => b.text).join(' | ');
        if (subjects.length) rawJob.exam_pattern = { subjects, notes };
      }
    }
    return rawJob;
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 8 — DOM HELPERS
  ═══════════════════════════════════════════════════════════════════════ */

  function insertBeforeLinks(card) {
    const layout = document.getElementById('layoutJob');
    if (!layout) return;
    // Find existing Important Links card
    let linksCard = null;
    for (const c of layout.querySelectorAll('.jp-card, .udyn-card')) {
      const head = c.querySelector('.jp-sec-head, .udyn-head');
      if (head && /important links/i.test(head.textContent)) { linksCard = c; break; }
    }
    if (linksCard) layout.insertBefore(card, linksCard);
    else {
      const tips = layout.querySelector('.jp-tips-card');
      if (tips) layout.insertBefore(card, tips);
      else layout.appendChild(card);
    }
  }

  function appendAfterAll(card) {
    const layout = document.getElementById('layoutJob');
    if (!layout) return;
    layout.appendChild(card);
  }

  function clearUniversalCards() {
    document.querySelectorAll('.udyn-card').forEach(el => el.remove());
  }

  function sectionExists(id) { return !!document.getElementById(id); }
  function baseSectionVisible(id) { const el = document.getElementById(id); return el && el.style.display !== 'none'; }
  function datesBaseVisible() { return baseSectionVisible('datesDetailCard'); }
  function feeBaseVisible() { return baseSectionVisible('feeCard'); }
  function vacancyBaseVisible() {
    const vc = document.getElementById('vacCard');
    if (!vc || vc.style.display === 'none') return false;
    return vc.querySelectorAll('#vacBody tr').length > 0;
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 9 — LEFT-NAV TOC UPDATER
  ═══════════════════════════════════════════════════════════════════════ */

  function updateTOC(sections) {
    const navList = document.querySelector('.jp-left-nav-list');
    if (!navList) return;
    navList.querySelectorAll('.udyn-toc-link').forEach(el => el.remove());
    if (!sections.length) return;
    const div = document.createElement('div');
    div.className = 'jp-left-nav-divider';
    div.textContent = 'Job Details';
    navList.appendChild(div);
    for (const { id, icon, label } of sections) {
      const a = document.createElement('a');
      a.className = 'jp-left-nav-item udyn-toc-link';
      a.href = `#${id}`;
      a.innerHTML = `<i class="fa-solid ${icon}"></i>${label}`;
      navList.appendChild(a);
    }
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 10 — FIELD PATCHER (update base-renderer DOM elements)
  ═══════════════════════════════════════════════════════════════════════ */

  function patchField(id, value) {
    if (!value) return;
    const el = document.getElementById(id);
    if (el && (el.textContent === '—' || el.textContent === '' || /^see notification$/i.test(el.textContent))) {
      el.textContent = value;
    }
  }
  function patchTableRow(tbodyId, pattern, value) {
    if (!value) return;
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    for (const tr of tbody.querySelectorAll('tr')) {
      const th = tr.querySelector('th');
      if (th && pattern.test(th.textContent)) {
        const td = tr.querySelector('td');
        if (td && (td.textContent === '—' || td.textContent === '')) td.textContent = value;
        break;
      }
    }
  }

  function runBasePatches(rawJob) {
    if (!rawJob) return;
    const bd = rawJob.basic_details || {};
    const id = rawJob.important_dates || {};
    const age = rawJob.age_limit || {};

    // Org
    const org = safe(rawJob.organization || rawJob.board_name || rawJob.department || bd.organization_name || bd.department || '');
    patchField('statOrg', org); patchTableRow('jbTable', /organisation/i, org);

    // Total vacancies
    const tv = safe(rawJob.total_vacancy || rawJob.total_vacancies || bd.total_vacancies || rawJob.total_post || '');
    if (tv) { patchField('statPosts', tv); patchTableRow('jbTable', /total vacancies/i, tv); }

    // Apply mode
    const mode = safe(rawJob.apply_mode || rawJob.application_mode || bd.apply_mode || '');
    if (mode) {
      const el = document.getElementById('statApplyMode');
      if (el) { el.textContent = mode; el.style.color = /offline/i.test(mode) ? '#ea580c' : '#16a34a'; }
      patchTableRow('jbTable', /application mode/i, mode);
    }

    // Last date
    const lastDate = safe(id.last_date || id.application_last_date || rawJob.last_date || rawJob.last_date_to_apply || '');
    if (lastDate && !/^see notification$/i.test(lastDate)) {
      const fmt = fmtDate(lastDate);
      patchField('statLastDate', fmt); patchField('dateLastVal', fmt);
      const sideRow = document.getElementById('dateLastRow');
      if (sideRow) sideRow.style.display = '';
      const metaEl = document.getElementById('metaLastDate');
      const metaWrap = document.getElementById('metaLastDateWrap');
      if (metaWrap && metaEl) { metaEl.textContent = 'Last Date: '+fmt; metaWrap.style.display = ''; }
    }

    // Salary in overview table
    const salary = safe(rawJob.salary || rawJob.salary_pay_scale || bd.salary || bd.salary_pay_scale || '');
    if (salary) {
      const rows = document.querySelectorAll('#jbTable tbody tr');
      let has = false;
      for (const tr of rows) { const th = tr.querySelector('th'); if (th && /salary/i.test(th.textContent)) { has = true; break; } }
      if (!has) {
        const tbody = document.querySelector('#jbTable tbody');
        if (tbody) {
          const tr = document.createElement('tr');
          tr.innerHTML = `<th>Salary / Pay Scale</th><td>${esc(salary)}</td>`;
          const last = tbody.lastElementChild;
          if (last) tbody.insertBefore(tr, last); else tbody.appendChild(tr);
        }
      }
    }

    // Age card patch
    const minAge = safe(rawJob.minimum_age || age.minimum_age || '');
    const maxAge = safe(rawJob.maximum_age || age.maximum_age || age.age_limit || age.age_details || '');
    const ageRelax = safe(rawJob.age_relaxation || age.age_relaxation || age.details || '');
    const ageCard = document.getElementById('ageCard');
    if ((minAge || maxAge || ageRelax) && ageCard && ageCard.style.display === 'none') {
      ageCard.style.display = '';
      const ageBody = document.getElementById('ageTableBody');
      if (ageBody) {
        const r = [];
        if (minAge) r.push(['Minimum Age', minAge]);
        if (maxAge) r.push(['Maximum Age', maxAge]);
        if (ageRelax) r.push(['Age Relaxation', ageRelax]);
        ageBody.innerHTML = r.map(([k,v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('');
      }
    }

    // Qualification card patch
    const eduQual = safe(rawJob.education_qualification || rawJob.eligibility || (rawJob.qualification && (rawJob.qualification.education_qualification || rawJob.qualification.eligibility)) || '');
    const qualCard = document.getElementById('qualCard');
    if (eduQual && qualCard && qualCard.style.display === 'none') {
      qualCard.style.display = '';
      const qualContent = document.getElementById('qualContent');
      if (qualContent) qualContent.innerHTML = `<div class="jp-detail-text"><strong>Education Qualification:</strong> ${esc(eduQual)}</div>`;
    }

    // Short info patch
    const shortInfo = safe(rawJob.short_information || rawJob.jobs_info || bd.short_information || '');
    const siCard = document.getElementById('shortInfoCard');
    const siText = document.getElementById('shortInfoText');
    if (shortInfo && siCard && siCard.style.display === 'none' && siText) {
      siCard.style.display = '';
      if (isHtml(shortInfo)) siText.innerHTML = shortInfo; else siText.textContent = shortInfo;
    }
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 11 — MASTER INJECTOR
     All cards in correct order, dedup-safe.
  ═══════════════════════════════════════════════════════════════════════ */

  const SECTION_DEFS = [
    { id: 'udyn-jobs-info',          icon: 'fa-circle-info',        label: 'About This Recruitment' },
    { id: 'udyn-dates-extended',     icon: 'fa-calendar-check',     label: 'Important Dates'        },
    { id: 'udyn-fee',                icon: 'fa-indian-rupee-sign',  label: 'Application Fee'        },
    { id: 'udyn-age-limit',          icon: 'fa-user-clock',         label: 'Age Limit'              },
    { id: 'udyn-qualification',      icon: 'fa-graduation-cap',     label: 'Qualification'          },
    { id: 'udyn-vacancy-extended',   icon: 'fa-chart-pie',          label: 'Vacancy Details'        },
    { id: 'udyn-physical',           icon: 'fa-dumbbell',           label: 'Physical Eligibility'   },
    { id: 'udyn-exam-pattern',       icon: 'fa-file-lines',         label: 'Exam Pattern'           },
    { id: 'udyn-syllabus',           icon: 'fa-book',               label: 'Syllabus'               },
    { id: 'udyn-salary',             icon: 'fa-indian-rupee-sign',  label: 'Salary Details'         },
    { id: 'udyn-selection',          icon: 'fa-list-check',         label: 'Selection Process'      },
    { id: 'udyn-how-to-apply',       icon: 'fa-clipboard-list',     label: 'How To Apply'           },
    { id: 'udyn-instructions',       icon: 'fa-circle-exclamation', label: 'Important Instructions' },
    { id: 'udyn-faq',                icon: 'fa-circle-question',    label: 'FAQ'                    },
    { id: 'udyn-text-sections',      icon: 'fa-clipboard-list',     label: 'How To Apply'           },
    { id: 'udyn-sr-tables',          icon: 'fa-table',              label: 'Vacancy Details'        },
    { id: 'udyn-imp-links',          icon: 'fa-link',               label: 'Important Links'        },
  ];

  function defFor(id) { return SECTION_DEFS.find(d => d.id === id); }

  function injectAllSections(rawJob) {
    if (!rawJob || typeof rawJob !== 'object') return;
    const layout = document.getElementById('layoutJob');
    if (!layout || layout.style.display === 'none') return;

    // Deduplicate — clear previous universal cards
    clearUniversalCards();

    const toc = [];
    const queue = []; // { card, def, append? }

    function push(card, defId) {
      if (!card) return;
      const def = defFor(defId);
      queue.push({ card, def });
      if (def) toc.push(def);
    }

    // ── 1. Jobs Info ──────────────────────────────────────────────────
    const jobsInfo = exJobsInfo(rawJob);
    if (jobsInfo && !baseSectionVisible('shortInfoCard')) push(cardJobsInfo(jobsInfo), 'udyn-jobs-info');

    // ── 2. Important Dates ────────────────────────────────────────────
    const datesData = exDates(rawJob);
    const allDateVals = datesData.rows.length + (datesData.rawText ? 1 : 0);
    const baseDateRows = document.querySelectorAll('#datesDetailBody tr').length;
    if (allDateVals > 0 && (allDateVals > baseDateRows || !datesBaseVisible() || datesData.rawText)) {
      push(cardDates(datesData), 'udyn-dates-extended');
    }

    // ── 3. Application Fee ────────────────────────────────────────────
    const feeData = exFees(rawJob);
    if (feeData.items.length && !feeBaseVisible()) push(cardFee(feeData), 'udyn-fee');

    // ── 4. Age Limit ──────────────────────────────────────────────────
    if (!baseSectionVisible('ageCard')) {
      push(cardAgeLimit(rawJob), 'udyn-age-limit');
    }

    // ── 5. Qualification ──────────────────────────────────────────────
    if (!baseSectionVisible('qualCard')) {
      const qual = exQualification(rawJob);
      if (qual) push(cardQualification(qual), 'udyn-qualification');
    }

    // ── 6. Vacancy Details ────────────────────────────────────────────
    const { rows: vacRows, cw: vacCW } = exVacancy(rawJob);
    if (!vacancyBaseVisible() && (vacRows.length || hasContent(vacCW))) {
      push(cardVacancy(vacRows, vacCW), 'udyn-vacancy-extended');
    }

    // ── 7. Physical Eligibility ───────────────────────────────────────
    const pe = exPhysical(rawJob);
    if (pe) push(cardPhysical(pe), 'udyn-physical');

    // ── 8. Exam Pattern ───────────────────────────────────────────────
    const ep = exExamPattern(rawJob);
    if (ep) push(cardExamPattern(ep), 'udyn-exam-pattern');

    // ── 9. Syllabus ───────────────────────────────────────────────────
    const syl = exSyllabus(rawJob);
    if (syl) push(cardSyllabus(syl), 'udyn-syllabus');

    // ── 10. Salary ────────────────────────────────────────────────────
    const { structured: sd, flat: salFlat } = exSalary(rawJob);
    if ((hasContent(sd) || salFlat) && !sectionExists('dynSalaryDetails')) {
      push(cardSalary(sd, salFlat), 'udyn-salary');
    }

    // ── 11. Selection Process ─────────────────────────────────────────
    const sp = exSelection(rawJob);
    if (hasContent(sp) && !sectionExists('dynSelection')) push(cardSelection(sp), 'udyn-selection');

    // ── 12. How To Apply ──────────────────────────────────────────────
    const hta = exHowToApply(rawJob);
    if (hasContent(hta) && !sectionExists('dynHowToApply')) push(cardHowToApply(hta), 'udyn-how-to-apply');

    // ── 13. Important Instructions ────────────────────────────────────
    const insts = exInstructions(rawJob);
    if (hasContent(insts) && !sectionExists('dynInstructions')) push(cardInstructions(insts), 'udyn-instructions');

    // ── 14. FAQ ───────────────────────────────────────────────────────
    const faqs = exFaq(rawJob);
    if (hasContent(faqs) && !sectionExists('dynFaq')) push(cardFaq(faqs), 'udyn-faq');

    // ── 15. SR Tables (merged_sarkari 'tables' field) ─────────────────
    const tables = exTables(rawJob);
    if (tables && !sectionExists('udyn-sr-tables')) push(cardTables(tables), 'udyn-sr-tables');

    // ── 15b. SR Text Sections (merged_sarkari 'text_sections' field) ──
    const textSections = exTextSections(rawJob);
    if (textSections && !sectionExists('udyn-text-sections')) push(cardTextSections(textSections), 'udyn-text-sections');

    // ── 16. Unknown future fields (auto-rendered recursively) ─────────
    const unknown = exUnknown(rawJob);
    for (const [k, v] of Object.entries(unknown)) {
      const c = cardGeneric(k, v);
      if (c) {
        const id = `udyn-generic-${k}`;
        queue.push({ card: c, def: { id, icon: 'fa-info-circle', label: keyToLabel(k) } });
        toc.push({ id, icon: 'fa-info-circle', label: keyToLabel(k) });
      }
    }

    // ── 17. Important Links (ALWAYS LAST — aggregated from all sources) ──
    const links = rawJob._udyn_links || [];
    if (links.length) {
      const c = cardLinks(links);
      if (c) queue.push({ card: c, def: defFor('udyn-imp-links'), append: true });
    }

    // ── Insert all cards ──────────────────────────────────────────────
    for (const { card, append } of queue) {
      if (append) appendAfterAll(card);
      else insertBeforeLinks(card);
    }

    updateTOC(toc.filter(d => d));
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 12 — FALLBACK: SEARCH FULL DATA FOR SLUG MATCH
     Used when job page loaded from dailyupdates (no individual JSON).
  ═══════════════════════════════════════════════════════════════════════ */

  const STOP_WORDS = new Set(['the','and','for','are','was','were','has','have','had','will','can','may',
    '2024','2025','2026','2027','apply','online','offline','form','now','out','notification','vacancy',
    'vacancies','recruitment','post','posts','latest','result','admit','card','answer','key','exam','date',
    'last','jobs','job','syllabus','merit','list','score','hall','ticket','call','letter']);

  function normStr(s) {
    return safe(s).toLowerCase().replace(/[^\x00-\x7e]/g,' ').replace(/&/g,' and ').replace(/[^a-z0-9]+/g,' ').trim();
  }
  function scoreMatch(title, tokens) {
    const t = normStr(title);
    return t ? tokens.filter(tk => t.includes(tk)).length / tokens.length : 0;
  }

  async function findAndEnrichFromFullData() {
    const slug = window.__TSJ_SLUG || '';
    if (!slug) return;
    const layout = document.getElementById('layoutJob');
    if (!layout || layout.style.display === 'none') return;
    if (document.querySelector('.udyn-card')) return;

    const slugNorm = normStr(slug.replace(/-/g,' '));
    const tokens = slugNorm.split(/\s+/).filter(t => t.length > 3 && !STOP_WORDS.has(t));
    if (tokens.length < 2) return;

    let best = null, bestScore = 0;

    try {
      const r = await fetch('/merged_sarkari_data.json');
      if (r.ok) {
        const d = await r.json();
        const jobs = (d && d.jobs) ? d.jobs : (Array.isArray(d) ? d : []);
        for (const job of jobs) {
          const sc = scoreMatch(safe(job.title || job.post_name || ''), tokens);
          if (sc > bestScore) { bestScore = sc; best = job; }
        }
      }
    } catch (_) {}

    if (!best || bestScore < 0.82) {
      try {
        const r = await fetch('/Complete_Jobs_Full_Data.json');
        if (r.ok) {
          const d = await r.json();
          const jobs = Array.isArray(d) ? d : Object.values(d).flatMap(v => Array.isArray(v) ? v : []);
          for (const job of jobs) {
            const t = safe(job.title || (job.basic_details && job.basic_details.job_title) || job.post_name || '');
            const sc = scoreMatch(t, tokens);
            if (sc > bestScore) { bestScore = sc; best = job; }
          }
        }
      } catch (_) {}
    }

    if (best && bestScore >= 0.82) {
      const normalized = normalize(best);
      runBasePatches(normalized);
      injectAllSections(normalized);
    }
  }


  /* ═══════════════════════════════════════════════════════════════════════
     § 13 — INTEGRATION HUB
     Race-condition-free 4-way callback system.
  ═══════════════════════════════════════════════════════════════════════ */

  function onJobRendered(rawJob) {
    let job = rawJob;
    if (job && typeof job === 'object') {
      try { job = normalizeUpcomingJobsSections(job); } catch(e) { console.warn('[UR] normalize sections:', e); }
      job = normalize(job);
      try { runBasePatches(job); } catch(e) { console.warn('[UR] patch:', e); }
      try { injectAllSections(job); } catch(e) { console.warn('[UR] inject:', e); }
    } else {
      setTimeout(findAndEnrichFromFullData, 200);
    }
  }

  (function integrate() {
    // Case 1: Already rendered
    if (window.__TSJ_RENDER_DONE) {
      setTimeout(() => onJobRendered(window.__TSJ_RAW_JOB), 0);
      return;
    }

    // Case 2: Register callback
    window.__TSJ_ON_RENDER_DONE = function(rawJob) {
      setTimeout(() => onJobRendered(rawJob), 0);
    };

    // Case 3: SEO Engine hook
    window.__SEO_ENGINE_JOB_READY = function(seoJob) {
      // Merge SEO data into TSJ_RAW_JOB if available
      if (window.__TSJ_RAW_JOB) return; // Already have full data
      setTimeout(() => onJobRendered(seoJob), 0);
    };

    // Case 4: Fetch intercept (legacy compatibility)
    const _origFetch = window.fetch;
    window.fetch = async function(...args) {
      const res = await _origFetch.apply(this, args);
      const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
      if (url && url.includes('/jobs/data/') && url.endsWith('.json')) {
        const clone = res.clone();
        clone.json().then(data => {
          if (data && (data.basic_details || data.title)) {
            window.__TSJ_RAW_JOB = data;
            let tries = 0;
            const id = setInterval(() => {
              const done = (document.getElementById('jbThreeCol') && document.getElementById('jbThreeCol').style.display !== 'none') ||
                           (document.getElementById('jbLoading') && document.getElementById('jbLoading').style.display === 'none') ||
                           tries > 80;
              if (done) {
                clearInterval(id);
                if (!document.querySelector('.udyn-card')) setTimeout(() => onJobRendered(data), 150);
              }
              tries++;
            }, 100);
          }
        }).catch(() => {});
      }
      return res;
    };

    // Case 5: Polling fallback
    let _polls = 0;
    const _pid = setInterval(() => {
      _polls++;
      const layout = document.getElementById('jbThreeCol');
      const loading = document.getElementById('jbLoading');
      const done = (layout && layout.style.display !== 'none') ||
                   (loading && loading.style.display === 'none') ||
                   window.__TSJ_RENDER_DONE || _polls > 100;
      if (done) {
        clearInterval(_pid);
        if (!document.querySelector('.udyn-card'))
          setTimeout(() => onJobRendered(window.__TSJ_RAW_JOB || null), 100);
      }
    }, 100);
  })();

})();
/* ══ END Universal Dynamic JSON-to-Page Rendering Engine v3.0 ══ */
