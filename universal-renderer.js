/**
 * ══════════════════════════════════════════════════════════════════════════
 *  TOP SARKARI JOBS — Universal Dynamic JSON-to-Page Rendering System
 *  File:    universal-renderer.js
 *  Version: 2026-05-18
 * ══════════════════════════════════════════════════════════════════════════
 *
 *  WHAT THIS SYSTEM DOES
 *  ─────────────────────
 *  • Automatically understands and renders ANY job-related JSON data on the
 *    job detail page without any manual template updates.
 *
 *  • Detects ALL field types from ALL 4 JSON sources:
 *    ▸ Complete_Jobs_Full_Data.json   (primary, 1300+ structured jobs)
 *    ▸ merged_sarkari_data.json       (offline form jobs, flat fields)
 *    ▸ dailyupdates.json              (section cards, minimal fields)
 *    ▸ state-jobs-data.json           (state govt jobs, nested detail)
 *
 *  • Section rendering order (always sequential):
 *    1.  Short Info / Overview Notice
 *    2.  Overview Table
 *    3.  Important Dates (with ALL date subfields, including raw text)
 *    4.  Application Fee (all category breakdowns)
 *    5.  Age Limit
 *    6.  Educational Qualification
 *    7.  Vacancy Details (dynamic columns, auto-detected)
 *    8.  Category-Wise Vacancy
 *    9.  Physical Eligibility / Standards
 *    10. Exam Pattern
 *    11. Syllabus
 *    12. Salary & Pay Details
 *    13. Selection Process
 *    14. How To Apply (numbered steps, HTML-aware)
 *    15. Important Instructions
 *    16. FAQ (accordion, deduplicated)
 *    17. Left-Nav TOC (dynamically updated to match sections present)
 *    18. [AUTO] Any unknown future JSON field → generic renderer
 *    19. Important Links (always last)
 *
 *  • Gracefully handles:
 *    ▸ String / Array / Object / Nested Object / Array-of-Objects values
 *    ▸ HTML string content (from jobs_info, how_to_apply)
 *    ▸ Keys added, renamed, removed, or reordered in JSON
 *    ▸ Multiple JSON structural formats (flat, nested, array, categories)
 *    ▸ Race conditions (deferred load vs. inline-script render timing)
 *    ▸ Duplicate section prevention (safe to call multiple times)
 *
 *  ⚠  Does NOT change any existing layout, styling, structure or design.
 *     All new cards use the site's existing .jp-card / .jp-sec-head classes.
 *
 * ══════════════════════════════════════════════════════════════════════════
 */

/* ─────────────────────────────────────────────────────────────────────────
   IIFE WRAPPER — no global leakage
───────────────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  /* ══════════════════════════════════════════════════════════════════════
     § 1 — ADDITIONAL CSS
     Only styles NOT already in job.html or the original patch file.
  ══════════════════════════════════════════════════════════════════════ */
  const _CSS_ID = 'tsj-universal-styles';
  if (!document.getElementById(_CSS_ID)) {
    const css = `
    /* ── Prevent double-injection by marking wrapper ── */
    #tsj-universal-styles { display:none; }

    /* ── Dynamic Section Cards (mirror .jp-card exactly) ── */
    .udyn-card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      overflow: hidden;
      margin-bottom: 14px;
      box-shadow: 0 1px 3px rgba(0,0,0,.04);
    }
    .udyn-head {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 9px 14px;
      color: #fff;
      font-size: .86rem;
      font-weight: 700;
    }
    .udyn-head i { opacity: .85; }

    /* ── How To Apply — numbered steps ── */
    .udyn-hta-list { list-style:none; margin:0; padding:0; }
    .udyn-hta-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 10px 14px;
      border-bottom: 1px solid #f1f5f9;
      font-size: .83rem;
      color: #1e293b;
      line-height: 1.65;
    }
    .udyn-hta-item:last-child { border-bottom: none; }
    .udyn-hta-num {
      flex-shrink: 0;
      min-width: 24px;
      height: 24px;
      background: #0f766e;
      color: #fff;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: .72rem;
      font-weight: 800;
      margin-top: 1px;
    }
    /* HTML content wrapper (for jobs_info / how_to_apply HTML strings) */
    .udyn-html-body {
      padding: 10px 14px;
      font-size: .83rem;
      color: #1e293b;
      line-height: 1.75;
    }
    .udyn-html-body p { margin: 0 0 8px; }
    .udyn-html-body ul, .udyn-html-body ol { margin: 0 0 8px; padding-left: 20px; }
    .udyn-html-body li { margin-bottom: 3px; }
    .udyn-html-body a { color: #1d4ed8; }

    /* ── FAQ — accordion ── */
    .udyn-faq-item { border-bottom: 1px solid #f1f5f9; }
    .udyn-faq-item:last-child { border-bottom: none; }
    .udyn-faq-q {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 11px 14px;
      font-size: .84rem;
      font-weight: 700;
      color: #0f172a;
      cursor: pointer;
      background: #f8fafc;
      transition: background .12s;
      line-height: 1.5;
      user-select: none;
    }
    .udyn-faq-q:hover { background: #f0f7ff; }
    .udyn-faq-icon {
      color: #1d4ed8;
      font-size: .8rem;
      margin-top: 3px;
      flex-shrink: 0;
      transition: transform .2s;
    }
    .udyn-faq-q.open .udyn-faq-icon { transform: rotate(90deg); }
    .udyn-faq-a {
      display: none;
      padding: 0 14px 12px 40px;
      font-size: .82rem;
      color: #374151;
      line-height: 1.7;
    }
    .udyn-faq-a.open { display: block; }

    /* ── Physical Eligibility grid ── */
    .udyn-phy-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    }
    .udyn-phy-item {
      padding: 10px 14px;
      border-right: 1px solid #e9eef4;
      border-bottom: 1px solid #e9eef4;
    }
    .udyn-phy-label {
      font-size: .68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .05em;
      color: #64748b;
      margin-bottom: 3px;
    }
    .udyn-phy-val { font-size: .88rem; font-weight: 700; color: #0f172a; }

    /* ── Salary grid ── */
    .udyn-sal-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    }
    .udyn-sal-item {
      padding: 10px 14px;
      border-right: 1px solid #e9eef4;
      border-bottom: 1px solid #e9eef4;
    }
    .udyn-sal-label { font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:3px; }
    .udyn-sal-val { font-size:.9rem;font-weight:800;color:#16a34a; }
    .udyn-sal-detail {
      padding: 10px 14px;
      font-size: .82rem;
      color: #374151;
      line-height: 1.7;
      border-top: 1px solid #f1f5f9;
    }

    /* ── Important Instructions ── */
    .udyn-inst-list { list-style:none;margin:0;padding:0; }
    .udyn-inst-item {
      display: flex;
      align-items: flex-start;
      gap: 9px;
      padding: 8px 14px;
      border-bottom: 1px solid #f1f5f9;
      font-size: .82rem;
      color: #374151;
      line-height: 1.65;
    }
    .udyn-inst-item:last-child { border-bottom: none; }
    .udyn-inst-item i { color: #ea580c; flex-shrink: 0; margin-top: 3px; }

    /* ── Generic table (auto-detected) ── */
    .udyn-gen-table {
      width: 100%;
      border-collapse: collapse;
      font-size: .82rem;
      min-width: 280px;
    }
    .udyn-gen-table th {
      width: 35%;
      background: #f8fafc;
      color: #374151;
      font-size: .82rem;
      font-weight: 700;
      padding: 9px 14px;
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid #e9eef4;
      word-break: break-word;
    }
    .udyn-gen-table td {
      padding: 9px 14px;
      color: #1e293b;
      font-size: .83rem;
      line-height: 1.65;
      border-bottom: 1px solid #e9eef4;
      vertical-align: top;
      word-break: break-word;
    }
    .udyn-gen-table tr:last-child th,
    .udyn-gen-table tr:last-child td { border-bottom: none; }

    /* ── Scrollable table wrapper ── */
    .udyn-table-scroll {
      width: 100%;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }

    /* ── Dynamic vacancy table (auto columns) ── */
    .udyn-vac-table {
      width: 100%;
      border-collapse: collapse;
      font-size: .82rem;
      min-width: 360px;
    }
    .udyn-vac-table th {
      background: #1d4ed8;
      color: #fff;
      padding: 8px 12px;
      text-align: center;
      font-weight: 700;
      white-space: nowrap;
    }
    .udyn-vac-table td {
      padding: 8px 12px;
      text-align: center;
      border-bottom: 1px solid #e9eef4;
      color: #1e293b;
      word-break: break-word;
    }
    .udyn-vac-table tr:last-child td { border-bottom: none; font-weight: 700; background: #f0f9ff; }

    /* ── Tag chips ── */
    .udyn-tag-list { display:flex;flex-wrap:wrap;gap:8px;padding:12px 14px; }
    .udyn-tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #f0f7ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 6px 12px;
      font-size: .8rem;
      font-weight: 600;
      color: #1e40af;
    }
    .udyn-tag i { color: #1d4ed8; }

    /* ── Detail text block ── */
    .udyn-detail {
      padding: 10px 14px;
      font-size: .83rem;
      color: #1e293b;
      line-height: 1.7;
      border-bottom: 1px solid #f1f5f9;
    }
    .udyn-detail:last-child { border-bottom: none; }

    /* ── Raw text / notice block ── */
    .udyn-raw-notice {
      padding: 10px 14px;
      font-size: .81rem;
      color: #374151;
      line-height: 1.7;
      background: #f8fafc;
      border-top: 1px solid #f1f5f9;
      white-space: pre-line;
    }

    /* ── Left-nav TOC link (dynamically added) ── */
    .jp-left-nav-item.udyn-toc-link { color: #374151; }
    .jp-left-nav-item.udyn-toc-link:hover { color: #1d4ed8; }

    /* ── Section anchor offset fix ── */
    .udyn-anchor { scroll-margin-top: var(--header-height, 140px); }

    @media (max-width: 600px) {
      .udyn-vac-table { font-size: .76rem; }
      .udyn-vac-table th, .udyn-vac-table td { padding: 7px 9px; }
      .udyn-gen-table { font-size: .78rem; }
      .udyn-gen-table th, .udyn-gen-table td { padding: 8px 10px; }
    }
    `;
    const st = document.createElement('style');
    st.id = _CSS_ID;
    st.textContent = css;
    document.head.appendChild(st);
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 2 — UTILITY HELPERS
  ══════════════════════════════════════════════════════════════════════ */

  const safe = v => (v == null ? '' : String(v)).trim();

  /** Escape HTML to prevent XSS */
  function esc(str) {
    return safe(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /** Convert snake_case / underscore key → Title Case label */
  function keyToLabel(k) {
    return safe(k)
      .replace(/_+/g, ' ')
      .replace(/\b[a-z]/g, c => c.toUpperCase())
      .replace(/\bObc\b/g, 'OBC')
      .replace(/\bEws\b/g, 'EWS')
      .replace(/\bSc\b/g, 'SC')
      .replace(/\bSt\b/g, 'ST')
      .replace(/\bPh\b/g, 'PH/PwD')
      .replace(/\bUrl\b/g, 'URL')
      .replace(/\bPdf\b/g, 'PDF')
      .replace(/\bUr\b/g, 'UR')
      .replace(/\bCpc\b/g, 'CPC')
      .trim();
  }

  /** Convert plain text with newlines → safe HTML paragraphs */
  function textToHtml(str) {
    const lines = safe(str).split(/\n+/).map(l => l.trim()).filter(Boolean);
    if (!lines.length) return '';
    return lines.map(l => `<p style="margin:0 0 6px;">${esc(l)}</p>`).join('');
  }

  /** Strip HTML tags from a string (for plain-text fallback) */
  function stripHtml(str) {
    return safe(str).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  }

  /** Check if a string contains HTML tags */
  function isHtml(str) {
    return /<[a-z][\s\S]*>/i.test(safe(str));
  }

  /** Safe render of a value that might be HTML or plain text */
  function renderValue(val) {
    if (typeof val !== 'string') return esc(String(val ?? ''));
    if (isHtml(val)) return val; // trusted internal HTML from JSON
    return esc(val);
  }

  /**
   * Checks if an object is non-empty (has at least one truthy value).
   * Works for objects, arrays, and strings.
   */
  function hasContent(v) {
    if (!v) return false;
    if (typeof v === 'string') return v.trim().length > 0;
    if (Array.isArray(v)) return v.length > 0;
    if (typeof v === 'object') return Object.values(v).some(x => hasContent(x));
    return true;
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 3 — DOM HELPERS
  ══════════════════════════════════════════════════════════════════════ */

  /** Create a section card with header and body HTML */
  function makeCard(id, headBg, iconCls, headText, bodyHtml) {
    const d = document.createElement('div');
    d.className = 'udyn-card';
    if (id) { d.id = id; d.className += ' udyn-anchor'; }
    d.innerHTML =
      `<div class="udyn-head" style="background:${headBg};">` +
        `<i class="${iconCls}"></i> ${esc(headText)}` +
      `</div>` +
      `<div class="udyn-body">${bodyHtml}</div>`;
    return d;
  }

  /** Insert a card BEFORE the "Important Links" card in #layoutJob */
  function insertBeforeLinks(card) {
    const layout = document.getElementById('layoutJob');
    if (!layout) return;
    const allCards = layout.querySelectorAll('.jp-card, .udyn-card');
    let linksCard = null;
    for (const c of allCards) {
      const head = c.querySelector('.jp-sec-head, .udyn-head');
      if (head && /important links/i.test(head.textContent)) { linksCard = c; break; }
    }
    if (linksCard) {
      layout.insertBefore(card, linksCard);
    } else {
      const tipsCard = layout.querySelector('.jp-tips-card');
      if (tipsCard) layout.insertBefore(card, tipsCard);
      else layout.appendChild(card);
    }
  }

  /**
   * Remove previously injected universal-renderer cards only.
   * Leaves existing base .jp-card elements untouched.
   */
  function clearUniversalCards() {
    document.querySelectorAll('.udyn-card').forEach(el => el.remove());
    // Also remove old .dyn-card from the original patch (avoid duplication)
    document.querySelectorAll('.dyn-card').forEach(el => el.remove());
    // Remove TOC links added by universal renderer
    document.querySelectorAll('.udyn-toc-link').forEach(el => el.remove());
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 3b — UPCOMING_JOBS SECTIONS NORMALIZER
     Converts the sections[] array format (used by merged_sarkari_data UPCOMING_JOBS)
     into structured fields that the extract functions understand.
     Called at the top of onJobRendered() before runBasePatches / injectAllSections.
  ══════════════════════════════════════════════════════════════════════ */

  /**
   * Parse a date string like "22/05/2026" or "22/05/2026 11:59 PM" → "22/05/2026"
   */
  function parseDateStr(str) {
    if (!str) return '';
    const m = str.match(/(\d{2}\/\d{2}\/\d{4})/);
    return m ? m[1] : str.trim();
  }

  /**
   * Extract starting date from Important Dates list items.
   * Looks for items like "Starting Date : 22/05/2026"
   */
  function extractStartingDateFromItems(items) {
    if (!Array.isArray(items)) return '';
    for (const item of items) {
      if (/starting\s*date/i.test(item)) {
        const m = item.match(/:\s*(.+)$/);
        return m ? parseDateStr(m[1].trim()) : '';
      }
    }
    return '';
  }

  /**
   * Normalize UPCOMING_JOBS sections[] array into structured fields.
   * Mutates the rawJob object in-place to add important_dates, application_fee,
   * age_limit, salary_details, vacancy_details, category_wise_vacancy, etc.
   * so that all existing extract functions work without modification.
   */
  function normalizeUpcomingJobsSections(rawJob) {
    if (!rawJob || !Array.isArray(rawJob.sections) || rawJob.sections.length === 0) return rawJob;
    // Only run for UPCOMING_JOBS category
    if (rawJob.category !== 'UPCOMING_JOBS') return rawJob;

    const sections = rawJob.sections;

    // Helper: get all text from a section's content
    function getSectionItems(sectionTitle) {
      const sec = sections.find(s => s.title && s.title.toLowerCase() === sectionTitle.toLowerCase());
      if (!sec || !Array.isArray(sec.content)) return [];
      const items = [];
      for (const blk of sec.content) {
        if (blk.type === 'list' && Array.isArray(blk.items)) items.push(...blk.items);
        else if (blk.type === 'paragraph' && blk.text) items.push(blk.text);
      }
      return items;
    }

    function getSectionRows(sectionTitle) {
      const sec = sections.find(s => s.title && s.title.toLowerCase() === sectionTitle.toLowerCase());
      if (!sec || !Array.isArray(sec.content)) return [];
      for (const blk of sec.content) {
        if (blk.type === 'table' && Array.isArray(blk.rows)) return blk.rows;
      }
      return [];
    }

    // Helper: parse key: value style items
    function parseKV(items) {
      const map = {};
      for (const item of items) {
        const colon = item.indexOf(':');
        if (colon > 0) {
          const key = item.slice(0, colon).trim().toLowerCase().replace(/\s+/g, '_');
          const val = item.slice(colon + 1).trim();
          map[key] = val;
        }
      }
      return map;
    }

    // ── Important Dates ──
    if (!rawJob.important_dates || Object.keys(rawJob.important_dates).length === 0) {
      const dateItems = getSectionItems('Important Dates');
      const kv = parseKV(dateItems);
      const id = {};
      if (kv['starting_date'] || kv['application_begin_date'] || kv['starting_date_(online)']) {
        id.application_begin = kv['starting_date'] || kv['application_begin_date'] || kv['starting_date_(online)'] || '';
      }
      if (kv['last_date']) {
        id.last_date = parseDateStr(kv['last_date']);
      }
      if (kv['correction_date']) id.correction_last_date = parseDateStr(kv['correction_date']);
      if (kv['notification_out'] || kv['notification_date']) {
        id.notification_date = parseDateStr(kv['notification_out'] || kv['notification_date']);
      }
      if (kv['exam_date']) id.exam_date = parseDateStr(kv['exam_date']);
      // Also store raw text so existing rawText fallback works
      if (dateItems.length > 0) id.raw = dateItems.join(' | ');
      rawJob.important_dates = id;
    }

    // ── Application Fee ──
    if (!rawJob.application_fee || Object.keys(rawJob.application_fee).length === 0) {
      const feeItems = getSectionItems('Application Fees');
      const kv = parseKV(feeItems);
      const fee = {};
      if (kv['for_all_candidates']) fee.all = kv['for_all_candidates'];
      if (kv['general']) fee.general = kv['general'];
      if (kv['obc']) fee.obc = kv['obc'];
      if (kv['sc/st'] || kv['sc_/_st']) fee.sc_st = kv['sc/st'] || kv['sc_/_st'];
      if (kv['payment_mode']) fee.note = 'Payment Mode: ' + kv['payment_mode'];
      if (feeItems.length > 0 && Object.keys(fee).length === 0) {
        fee.note = feeItems.join(' | ');
      }
      rawJob.application_fee = fee;
    }

    // ── Age Limit ──
    if (!rawJob.age_limit || Object.keys(rawJob.age_limit).length === 0) {
      const ageItems = getSectionItems('Age Limit Details');
      const kv = parseKV(ageItems);
      const age = {};
      if (kv['age_limit']) age.age_limit = kv['age_limit'];
      if (kv['minimum_age']) age.minimum_age = kv['minimum_age'];
      if (kv['maximum_age']) age.maximum_age = kv['maximum_age'];
      if (kv['age_relaxation']) age.age_relaxation = kv['age_relaxation'];
      if (ageItems.length > 0 && Object.keys(age).length === 0) age.age_limit = ageItems.join(', ');
      rawJob.age_limit = age;
    }

    // ── Pay Scale / Salary ──
    if (!rawJob.salary_details || Object.keys(rawJob.salary_details).length === 0) {
      const payItems = getSectionItems('Pay Scale Details');
      if (payItems.length > 0 && !rawJob.salary) {
        rawJob.salary = payItems.join(' | ');
      }
    }

    // ── Selection Process ──
    if (!rawJob.selection_process || (Array.isArray(rawJob.selection_process) && rawJob.selection_process.length === 0)) {
      const selItems = getSectionItems('Selection Process');
      if (selItems.length > 0) rawJob.selection_process = selItems;
    }

    // ── Category Wise Vacancy from table ──
    if (!rawJob.category_wise_vacancy || Object.keys(rawJob.category_wise_vacancy).length === 0) {
      const rows = getSectionRows('Category Wise Vacancies') || getSectionRows('Qualification Details');
      // Find the header row and data row
      for (const row of rows) {
        const texts = row.map(c => (c.text || '').trim().toLowerCase());
        if (texts.includes('gen') || texts.includes('general')) {
          // This is header row - next row should have values
          const idx = rows.indexOf(row);
          const valRow = rows[idx + 1];
          if (valRow && valRow.length >= 2) {
            const cw = {};
            for (let i = 0; i < row.length; i++) {
              const hdr = (row[i].text || '').trim().toLowerCase();
              const val = valRow[i] ? (valRow[i].text || '').trim() : '';
              if (hdr === 'gen' || hdr === 'general' || hdr === 'ur') cw.general = val;
              else if (hdr === 'obc') cw.obc = val;
              else if (hdr === 'ews') cw.ews = val;
              else if (hdr === 'sc') cw.sc = val;
              else if (hdr === 'st') cw.st = val;
              else if (hdr === 'total') cw.total = val;
            }
            if (Object.keys(cw).length > 0) rawJob.category_wise_vacancy = cw;
          }
          break;
        }
      }
    }

    // ── Total vacancies ──
    if (!rawJob.total_vacancy && !rawJob.total_vacancies) {
      // Try Overview table for "Total Posts"
      const overviewSec = sections.find(s => s.title === 'Overview');
      if (overviewSec && Array.isArray(overviewSec.content)) {
        for (const blk of overviewSec.content) {
          if (blk.type === 'table' && Array.isArray(blk.rows)) {
            for (let ri = 0; ri < blk.rows.length; ri++) {
              const row = blk.rows[ri];
              for (let ci = 0; ci < row.length; ci++) {
                if (/total\s*posts?/i.test(row[ci].text || '')) {
                  // value in next row same column
                  const nextRow = blk.rows[ri + 1];
                  if (nextRow && nextRow[ci]) rawJob.total_vacancy = (nextRow[ci].text || '').trim();
                }
              }
            }
          }
        }
      }
      // Also check category_wise_vacancy total
      if (!rawJob.total_vacancy && rawJob.category_wise_vacancy && rawJob.category_wise_vacancy.total) {
        rawJob.total_vacancy = rawJob.category_wise_vacancy.total;
      }
    }

    // ── Exam Pattern / Written Exam ──
    if (!rawJob.exam_pattern || Object.keys(rawJob.exam_pattern).length === 0) {
      const epSec = sections.find(s => /written\s*exam\s*pattern|exam\s*pattern/i.test(s.title || ''));
      if (epSec && Array.isArray(epSec.content)) {
        const rows = [];
        for (const blk of epSec.content) {
          if (blk.type === 'table' && Array.isArray(blk.rows)) rows.push(...blk.rows);
        }
        if (rows.length > 0) {
          // Convert table rows to array of objects
          const subjects = [];
          let headerRow = null;
          for (const row of rows) {
            const texts = row.map(c => (c.text || '').trim());
            const isHeader = texts.some(t => /subject|questions|marks/i.test(t));
            if (isHeader) { headerRow = texts; continue; }
            if (headerRow && row.length >= 2 && !/^(negative|time|grand)/i.test(texts[0])) {
              const obj = {};
              for (let i = 0; i < headerRow.length; i++) {
                obj[headerRow[i].toLowerCase()] = texts[i] || '';
              }
              subjects.push(obj);
            }
          }
          const notes = [];
          for (const blk of epSec.content) {
            if (blk.type === 'paragraph' && blk.text) notes.push(blk.text);
          }
          rawJob.exam_pattern = { subjects, notes: notes.join(' | ') };
        }
      }
    }

    // ── Qualification ──
    if (!rawJob.qualification || Object.keys(rawJob.qualification).length === 0) {
      const qualItems = getSectionItems('Qualification Details');
      if (qualItems.length > 0) {
        rawJob.qualification = { education_qualification: qualItems.join(' ') };
        rawJob.education_qualification = qualItems.join(' ');
      }
    }

    return rawJob;
  }

  /* ══════════════════════════════════════════════════════════════════════
     § 4 — FIELD EXTRACTORS
     Each function normalizes a specific JSON section across ALL formats.
  ══════════════════════════════════════════════════════════════════════ */

  /**
   * Extract ALL important dates from raw job JSON.
   * Handles both structured objects and raw text strings.
   */
  function extractDates(job) {
    const id = job.important_dates || {};
    const knownFields = {
      application_begin:      id.application_begin || id.application_start || id.start_date || job.application_begin || '',
      last_date:              id.last_date || id.application_last_date || id.last_date_for_apply ||
                              id.closing_date || id.last_apply_date || job.last_date || job.last_date_to_apply || '',
      fee_payment_last_date:  id.fee_payment_last_date || id.fee_last_date || '',
      correction_last_date:   id.correction_last_date || '',
      exam_date:              id.exam_date || job.exam_date || '',
      admit_card_date:        id.admit_card_date || id.admit_card || '',
      result_date:            id.result_date || '',
      interview_date:         id.interview_date || '',
      document_verification:  id.document_verification || id.dv_date || '',
      counselling_date:       id.counselling_date || '',
      joining_date:           id.joining_date || '',
    };
    // Collect any extra date-looking fields in important_dates not in our map
    const handled = new Set(Object.keys(knownFields).concat(['raw', 'rawDate']));
    const extra = {};
    for (const [k, v] of Object.entries(id)) {
      if (!handled.has(k) && v && !/^(start|end)$/i.test(k)) extra[k] = v;
    }
    // Raw text block (keep for supplemental display)
    const rawText = safe(id.raw || id.rawDate || '');
    return { knownFields, extra, rawText };
  }

  /**
   * Extract fee data — handles multiple field naming conventions.
   * Normalizes: general, obc, ews, sc, st, female, ph, general_obc_ews combined, etc.
   */
  function extractFees(job) {
    const fee = job.application_fee || job.application_fees || {};
    const feeIsStr = typeof fee === 'string' || (typeof job.application_fee === 'string');
    const feeObj = (typeof fee === 'object' && !Array.isArray(fee)) ? fee : {};
    return {
      general:         safe(feeObj.general || feeObj.ur || feeObj.unreserved || ''),
      obc:             safe(feeObj.obc || ''),
      ews:             safe(feeObj.ews || ''),
      sc:              safe(feeObj.sc || ''),
      st:              safe(feeObj.st || ''),
      sc_st:           safe(feeObj.sc_st || feeObj['sc/st'] || ''),
      female:          safe(feeObj.female || feeObj.women || ''),
      ph:              safe(feeObj.ph || feeObj.pwd || feeObj.divyang || ''),
      general_obc:     safe(feeObj.general_obc || feeObj.gen_obc || ''),
      general_obc_ews: safe(feeObj.general_obc_ews || feeObj.gen_obc_ews || feeObj.ur_obc_ews || ''),
      all:             safe(feeObj.all || feeObj.all_candidates || ''),
      flat:            feeIsStr ? safe(typeof fee === 'string' ? fee : job.application_fee) : '',
      note:            safe(feeObj.note || feeObj.payment_note || feeObj.payment_mode || ''),
    };
  }

  /**
   * Extract vacancy details — handles both array-of-objects and flat category-wise objects.
   */
  function extractVacancy(job) {
    const vd = job.vacancy_details || [];
    const cw = job.category_wise_vacancy || {};
    return { vd, cw };
  }

  /**
   * Extract physical eligibility — handles nested objects and plain strings.
   */
  function extractPhysical(job) {
    const pe = job.physical_eligibility || {};
    if (!pe || (typeof pe === 'object' && !Array.isArray(pe) && Object.keys(pe).length === 0)) return null;
    return pe;
  }

  /**
   * Extract exam pattern — handles array, object, and string.
   */
  function extractExamPattern(job) {
    const ep = job.exam_pattern || {};
    if (!hasContent(ep)) return null;
    return ep;
  }

  /**
   * Extract syllabus — handles array, object (by subject), and string.
   */
  function extractSyllabus(job) {
    const syl = job.syllabus || {};
    if (!hasContent(syl)) return null;
    return syl;
  }

  /**
   * Extract salary details — handles nested object and plain string.
   */
  function extractSalary(job) {
    const sd = job.salary_details || {};
    const flat = safe(job.salary || job.salary_pay_scale || (job.basic_details && job.basic_details.salary) || '');
    return { structured: sd, flat };
  }

  /**
   * Extract selection process — handles array and string.
   */
  function extractSelection(job) {
    const sp = job.selection_process || (job.basic_details && job.basic_details.selection_process) || [];
    return sp;
  }

  /**
   * Extract how-to-apply — handles array of strings, plain string, and HTML string.
   */
  function extractHowToApply(job) {
    return job.how_to_apply || job.apply_process || '';
  }

  /**
   * Extract important instructions.
   */
  function extractInstructions(job) {
    return job.important_instructions || job.instructions || [];
  }

  /**
   * Extract FAQ array.
   */
  function extractFaq(job) {
    return job.faq || job.faqs || [];
  }

  /**
   * Extract additional info text (jobs_info, short_information HTML).
   */
  function extractJobsInfo(job) {
    const bd = job.basic_details || {};
    return safe(job.jobs_info || bd.jobs_info || '');
  }

  /**
   * Detect ALL remaining fields NOT handled by any specific extractor above.
   * Used for auto-rendering unknown future JSON fields.
   */
  function extractUnknownFields(job) {
    const KNOWN_TOP_KEYS = new Set([
      'basic_details', 'important_dates', 'application_fee', 'application_fees',
      'age_limit', 'qualification', 'vacancy_details', 'category_wise_vacancy',
      'salary_details', 'selection_process', 'exam_pattern', 'syllabus',
      'physical_eligibility', 'how_to_apply', 'important_instructions',
      'important_links', 'important_links_obj', 'faq', 'faqs',
      'seo_tags', 'category', 'slug', 'title', 'post_name', 'organization',
      'board_name', 'department', 'total_vacancy', 'total_vacancies',
      'apply_mode', 'application_mode', 'mode', 'last_date', 'last_date_to_apply',
      'application_begin', 'exam_date', 'salary', 'salary_pay_scale',
      'minimum_age', 'maximum_age', 'age_relaxation', 'education_qualification',
      'eligibility', 'experience_required', 'short_information', 'jobs_info',
      'source_url', 'apply_online', 'official_website', 'official_website_link',
      'form_pdf_free_link', 'official_notification_pdf_link',
      'apply_online_link', 'application_form_pdf_link', 'form_pdf_link',
      'listing_date', 'last_updated', 'apply_process', 'post_date', 'status',
      'useful_links', 'sequence', 'job_location', 'job_type', 'homepage_serial',
      'apply_mode', 'application_fees', 'minimum_age', 'maximum_age',
      'salary_pay_scale', 'total_post', 'closing_date', 'application_last_date',
      'instructions', 'tables', // tables handled separately via extractTables()
    ]);
    const unknown = {};
    for (const [k, v] of Object.entries(job)) {
      if (KNOWN_TOP_KEYS.has(k)) continue;
      if (!hasContent(v)) continue;
      unknown[k] = v;
    }
    return unknown;
  }

  /** Extract SR-style 'tables' field (array of array-of-arrays or array-of-objects) */
  function extractTables(job) {
    return job.tables || null;
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 5 — CARD BUILDERS (one per section type)
  ══════════════════════════════════════════════════════════════════════ */

  /* ── 5a. How To Apply ── */
  function buildHowToApply(value) {
    if (!hasContent(value)) return null;

    let bodyHtml = '';

    // Array of steps (most common)
    if (Array.isArray(value) && value.length) {
      const items = value
        .map(s => safe(s))
        .filter(Boolean)
        .map((s, i) =>
          `<li class="udyn-hta-item">` +
            `<span class="udyn-hta-num">${i + 1}</span>` +
            `<span>${isHtml(s) ? s : esc(s)}</span>` +
          `</li>`
        ).join('');
      bodyHtml = `<ul class="udyn-hta-list">${items}</ul>`;
    }
    // HTML string
    else if (typeof value === 'string' && isHtml(value)) {
      bodyHtml = `<div class="udyn-html-body">${value}</div>`;
    }
    // Plain text string
    else if (typeof value === 'string' && value.trim()) {
      const lines = value.trim().split(/\n+/).map(l => l.trim()).filter(Boolean);
      if (lines.length > 2) {
        // Multiple lines → numbered steps
        const items = lines.map((s, i) =>
          `<li class="udyn-hta-item">` +
            `<span class="udyn-hta-num">${i + 1}</span>` +
            `<span>${esc(s)}</span>` +
          `</li>`
        ).join('');
        bodyHtml = `<ul class="udyn-hta-list">${items}</ul>`;
      } else {
        bodyHtml = `<div class="udyn-detail">${textToHtml(value)}</div>`;
      }
    }

    if (!bodyHtml) return null;
    return makeCard(
      'udyn-how-to-apply',
      'linear-gradient(135deg,#0f766e,#0891b2)',
      'fa-solid fa-clipboard-list',
      'How To Apply',
      bodyHtml
    );
  }

  /* ── 5b. FAQ — Accordion ── */
  function buildFaq(faqs) {
    if (!Array.isArray(faqs) || !faqs.length) return null;
    const seen = new Set();
    const unique = faqs.filter(f => {
      const q = safe(f.question || f.q || f.ques || '');
      if (!q || seen.has(q)) return false;
      seen.add(q);
      return true;
    });
    if (!unique.length) return null;

    const items = unique.map((f, i) => {
      const q = esc(f.question || f.q || f.ques || '');
      const a = esc(f.answer || f.a || f.ans || '');
      return `
        <div class="udyn-faq-item">
          <div class="udyn-faq-q" onclick="(function(el){
            el.classList.toggle('open');
            var next = el.nextElementSibling;
            if(next) next.classList.toggle('open');
          })(this)">
            <i class="fa-solid fa-chevron-right udyn-faq-icon"></i>
            <span>${q}</span>
          </div>
          <div class="udyn-faq-a">${a}</div>
        </div>`;
    }).join('');

    return makeCard(
      'udyn-faq',
      'linear-gradient(135deg,#b45309,#d97706)',
      'fa-solid fa-circle-question',
      'Frequently Asked Questions (FAQ)',
      items
    );
  }

  /* ── 5c. Physical Eligibility ── */
  function buildPhysical(pe) {
    if (!pe || !hasContent(pe)) return null;
    let bodyHtml = '';

    if (typeof pe === 'object' && !Array.isArray(pe)) {
      const pairs = Object.entries(pe).filter(([, v]) => hasContent(v));
      if (!pairs.length) return null;
      bodyHtml = `<div class="udyn-phy-grid">${
        pairs.map(([k, v]) =>
          `<div class="udyn-phy-item">` +
            `<div class="udyn-phy-label">${esc(keyToLabel(k))}</div>` +
            `<div class="udyn-phy-val">${esc(typeof v === 'object' ? JSON.stringify(v) : String(v))}</div>` +
          `</div>`
        ).join('')
      }</div>`;
    } else if (typeof pe === 'string' && pe.trim()) {
      bodyHtml = `<div class="udyn-detail">${textToHtml(pe)}</div>`;
    }

    if (!bodyHtml) return null;
    return makeCard(
      'udyn-physical',
      'linear-gradient(135deg,#be123c,#e11d48)',
      'fa-solid fa-dumbbell',
      'Physical Eligibility / Standards',
      bodyHtml
    );
  }

  /* ── 5d. Exam Pattern ── */
  function buildExamPattern(ep) {
    if (!hasContent(ep)) return null;
    let bodyHtml = '';

    if (Array.isArray(ep) && ep.length) {
      if (typeof ep[0] === 'object' && ep[0] !== null) {
        const cols = [...new Set(ep.flatMap(r => Object.keys(r)))];
        const thead = cols.map(c => `<th>${esc(keyToLabel(c))}</th>`).join('');
        const tbody = ep.map(r =>
          `<tr>${cols.map(c => `<td>${esc(safe(r[c]))}</td>`).join('')}</tr>`
        ).join('');
        bodyHtml = `<div class="udyn-table-scroll"><table class="udyn-vac-table" style="min-width:420px;"><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table></div>`;
      } else {
        bodyHtml = `<div class="udyn-tag-list">${ep.map(s => `<div class="udyn-tag"><i class="fa-solid fa-file-lines"></i>${esc(s)}</div>`).join('')}</div>`;
      }
    } else if (typeof ep === 'object') {
      const pairs = Object.entries(ep).filter(([, v]) => hasContent(v));
      if (!pairs.length) return null;
      bodyHtml = `<table class="udyn-gen-table"><tbody>${
        pairs.map(([k, v]) =>
          `<tr><th>${esc(keyToLabel(k))}</th><td>${esc(typeof v === 'object' ? JSON.stringify(v) : String(v))}</td></tr>`
        ).join('')
      }</tbody></table>`;
    } else if (typeof ep === 'string' && ep.trim()) {
      bodyHtml = `<div class="udyn-detail">${textToHtml(ep)}</div>`;
    }

    if (!bodyHtml) return null;
    return makeCard(
      'udyn-exam-pattern',
      'linear-gradient(135deg,#0369a1,#0284c7)',
      'fa-solid fa-file-lines',
      'Exam Pattern',
      bodyHtml
    );
  }

  /* ── 5e. Syllabus ── */
  function buildSyllabus(syl) {
    if (!hasContent(syl)) return null;
    let bodyHtml = '';

    if (Array.isArray(syl) && syl.length) {
      if (typeof syl[0] === 'string') {
        bodyHtml = `<div class="udyn-tag-list">${
          syl.map(s => `<div class="udyn-tag"><i class="fa-solid fa-book-open"></i>${esc(s)}</div>`).join('')
        }</div>`;
      } else {
        // Array of objects
        const cols = [...new Set(syl.flatMap(r => Object.keys(r)))];
        const thead = cols.map(c => `<th>${esc(keyToLabel(c))}</th>`).join('');
        const tbody = syl.map(r =>
          `<tr>${cols.map(c => `<td>${esc(safe(r[c]))}</td>`).join('')}</tr>`
        ).join('');
        bodyHtml = `<div class="udyn-table-scroll"><table class="udyn-vac-table" style="min-width:360px;"><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table></div>`;
      }
    } else if (typeof syl === 'object' && !Array.isArray(syl)) {
      const pairs = Object.entries(syl).filter(([, v]) => hasContent(v));
      if (!pairs.length) return null;
      const rows = pairs.map(([k, v]) => {
        const valStr = Array.isArray(v) ? v.join(', ') : (typeof v === 'object' ? JSON.stringify(v) : String(v));
        return `<tr><th>${esc(keyToLabel(k))}</th><td>${esc(valStr)}</td></tr>`;
      }).join('');
      bodyHtml = `<table class="udyn-gen-table"><tbody>${rows}</tbody></table>`;
    } else if (typeof syl === 'string' && syl.trim()) {
      bodyHtml = `<div class="udyn-detail">${textToHtml(syl)}</div>`;
    }

    if (!bodyHtml) return null;
    return makeCard(
      'udyn-syllabus',
      'linear-gradient(135deg,#4338ca,#6366f1)',
      'fa-solid fa-book',
      'Syllabus / Exam Topics',
      bodyHtml
    );
  }

  /* ── 5f. Salary Details (extended) ── */
  function buildSalaryDetails(structured, flat) {
    if (!hasContent(structured) && !flat) return null;

    let bodyHtml = '';

    if (hasContent(structured)) {
      const pairs = Object.entries(structured).filter(([k, v]) => hasContent(v) && k !== 'details');
      if (pairs.length) {
        bodyHtml += `<div class="udyn-sal-grid">${
          pairs.map(([k, v]) =>
            `<div class="udyn-sal-item">` +
              `<div class="udyn-sal-label">${esc(keyToLabel(k))}</div>` +
              `<div class="udyn-sal-val">${esc(String(v))}</div>` +
            `</div>`
          ).join('')
        }</div>`;
      }
      // Long 'details' string goes in a separate readable block
      const details = safe(structured.details || '');
      if (details) {
        bodyHtml += `<div class="udyn-sal-detail">${textToHtml(details)}</div>`;
      }
    }

    if (!bodyHtml && flat) {
      bodyHtml = `<div class="udyn-detail">${esc(flat)}</div>`;
    }

    if (!bodyHtml) return null;
    return makeCard(
      'udyn-salary',
      'linear-gradient(135deg,#15803d,#16a34a)',
      'fa-solid fa-indian-rupee-sign',
      'Salary & Pay Scale Details',
      bodyHtml
    );
  }

  /* ── 5g. Important Instructions ── */
  function buildInstructions(insts) {
    let arr = [];
    if (Array.isArray(insts)) arr = insts.map(s => safe(s)).filter(Boolean);
    else if (typeof insts === 'string' && insts.trim()) {
      const lines = insts.split(/\n+/).map(l => l.trim()).filter(Boolean);
      arr = lines.length > 1 ? lines : [insts.trim()];
    }
    if (!arr.length) return null;

    const items = arr.map(s =>
      `<li class="udyn-inst-item">` +
        `<i class="fa-solid fa-triangle-exclamation"></i>` +
        `<span>${esc(s)}</span>` +
      `</li>`
    ).join('');

    return makeCard(
      'udyn-instructions',
      'linear-gradient(135deg,#b45309,#ca8a04)',
      'fa-solid fa-circle-exclamation',
      'Important Instructions / Notice',
      `<ul class="udyn-inst-list">${items}</ul>`
    );
  }

  /* ── 5h. Jobs Info HTML notice ── */
  function buildJobsInfo(htmlStr) {
    if (!htmlStr) return null;
    const text = stripHtml(htmlStr).trim();
    if (!text || text.length < 20) return null;
    // Show as a collapsible notice block
    return makeCard(
      'udyn-jobs-info',
      'linear-gradient(135deg,#0f766e,#0891b2)',
      'fa-solid fa-circle-info',
      'About This Recruitment',
      `<div class="udyn-html-body">${htmlStr}</div>`
    );
  }

  /* ── 5i. Important Dates (extended — all date subfields) ── */
  function buildDatesExtended(dates) {
    const { knownFields, extra, rawText } = dates;
    const DATE_LABELS = {
      application_begin:     'Application Start Date',
      last_date:             'Last Date to Apply',
      fee_payment_last_date: 'Fee Payment Last Date',
      correction_last_date:  'Correction Last Date',
      exam_date:             'Exam Date',
      admit_card_date:       'Admit Card Available',
      result_date:           'Result Date',
      interview_date:        'Interview / DV Date',
      document_verification: 'Document Verification',
      counselling_date:      'Counselling Date',
      joining_date:          'Joining Date',
    };
    const rows = [];
    for (const [k, label] of Object.entries(DATE_LABELS)) {
      const v = safe(knownFields[k]);
      if (v) rows.push({ label, val: v, red: /last date/i.test(label) });
    }
    for (const [k, v] of Object.entries(extra)) {
      if (v) rows.push({ label: keyToLabel(k), val: safe(v), red: false });
    }
    if (!rows.length && !rawText) return null;

    let bodyHtml = rows.map(r =>
      `<tr>` +
        `<th>${esc(r.label)}</th>` +
        `<td style="${r.red ? 'color:#dc2626;font-weight:800;' : ''}">${esc(r.val)}</td>` +
      `</tr>`
    ).join('');

    if (rawText && rows.length === 0) {
      bodyHtml = `<tr><th>Date Information</th><td class="udyn-raw-notice" style="white-space:pre-line;">${esc(rawText)}</td></tr>`;
    } else if (rawText) {
      bodyHtml += `<tr><th>Additional Date Info</th><td style="font-size:.79rem;color:#64748b;white-space:pre-line;">${esc(rawText)}</td></tr>`;
    }

    if (!bodyHtml) return null;
    return makeCard(
      'udyn-dates-extended',
      'linear-gradient(135deg,#b91c1c,#dc2626)',
      'fa-regular fa-calendar-check',
      'Important Dates',
      `<div class="udyn-table-scroll" style="overflow-x:auto;"><table class="udyn-gen-table">${bodyHtml}</table></div>`
    );
  }

  /* ── 5j. Application Fee (all categories) ── */
  function buildFeeExtended(fees) {
    const ALL_FEE_KEYS = [
      { key: 'general',         label: 'General / UR'        },
      { key: 'obc',             label: 'OBC'                 },
      { key: 'ews',             label: 'EWS'                 },
      { key: 'sc',              label: 'SC'                  },
      { key: 'st',              label: 'ST'                  },
      { key: 'sc_st',           label: 'SC / ST'             },
      { key: 'female',          label: 'Female'              },
      { key: 'ph',              label: 'PH / Divyang'        },
      { key: 'general_obc',     label: 'General / OBC'       },
      { key: 'general_obc_ews', label: 'General / OBC / EWS' },
      { key: 'all',             label: 'All Candidates'      },
      { key: 'flat',            label: 'Application Fee'     },
    ];
    const isFree = v => /nil|^0$|free|no fee|exempt/i.test(v.trim());

    let hasAny = false;
    let gridHtml = '';
    for (const { key, label } of ALL_FEE_KEYS) {
      const v = fees[key];
      if (!v) continue;
      hasAny = true;
      const colorClass = isFree(v) ? 'color:#16a34a;' : 'color:#1d4ed8;';
      gridHtml +=
        `<div style="padding:10px 14px;border-right:1px solid #e9eef4;border-bottom:1px solid #e9eef4;">` +
          `<div style="font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#64748b;margin-bottom:3px;">${esc(label)}</div>` +
          `<div style="font-size:.9rem;font-weight:700;${colorClass}">${esc(v)}</div>` +
        `</div>`;
    }

    let noticeHtml = '';
    if (fees.note) {
      noticeHtml = `<div style="padding:9px 14px;font-size:.81rem;color:#78350f;background:#fffbeb;border-top:1px solid #fde68a;">${esc(fees.note)}</div>`;
    }

    if (!hasAny) return null;
    return makeCard(
      'udyn-fee',
      'linear-gradient(135deg,#c2410c,#ea580c)',
      'fa-solid fa-indian-rupee-sign',
      'Application Fee',
      `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));">${gridHtml}</div>${noticeHtml}`
    );
  }

  /* ── 5k. Vacancy Details (dynamic auto-detected columns) ── */
  function buildVacancyExtended(vd, cw) {
    let bodyHtml = '';

    if (Array.isArray(vd) && vd.length) {
      // Detect all columns present
      const allCols = [...new Set(vd.flatMap(r => Object.keys(r)))];
      if (allCols.length) {
        const thead = allCols.map(c => `<th>${esc(keyToLabel(c))}</th>`).join('');
        const tbody = vd.map(r =>
          `<tr>${allCols.map(c => `<td>${esc(safe(r[c]))}</td>`).join('')}</tr>`
        ).join('');
        bodyHtml = `<div class="udyn-table-scroll"><table class="udyn-vac-table" style="min-width:360px;"><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table></div>`;
      }
    } else if (cw && typeof cw === 'object' && Object.keys(cw).length) {
      // Category-wise object
      const pairs = Object.entries(cw).filter(([, v]) => hasContent(v));
      if (pairs.length) {
        const tbody = pairs.map(([k, v]) =>
          `<tr><td>${esc(keyToLabel(k))}</td><td>${esc(String(v))}</td></tr>`
        ).join('');
        bodyHtml = `<div class="udyn-table-scroll"><table class="udyn-vac-table" style="min-width:260px;"><thead><tr><th>Category</th><th>Vacancies</th></tr></thead><tbody>${tbody}</tbody></table></div>`;
      }
    }

    if (!bodyHtml) return null;
    return makeCard(
      'udyn-vacancy-extended',
      'linear-gradient(135deg,#15803d,#16a34a)',
      'fa-solid fa-chart-pie',
      'Vacancy Details',
      bodyHtml
    );
  }

  /* ── 5l. Generic Card (AUTO-RENDER for unknown fields) ── */
  function buildGeneric(fieldKey, value) {
    if (!hasContent(value)) return null;
    const label = keyToLabel(fieldKey);
    let bodyHtml = '';
    const headBg = 'linear-gradient(135deg,#475569,#64748b)';

    if (Array.isArray(value) && value.length) {
      if (typeof value[0] === 'object' && value[0] !== null) {
        // Array of objects → table
        const cols = [...new Set(value.flatMap(r => Object.keys(r)))];
        const thead = cols.map(c => `<th>${esc(keyToLabel(c))}</th>`).join('');
        const tbody = value.map(r =>
          `<tr>${cols.map(c => `<td>${esc(safe(r[c]))}</td>`).join('')}</tr>`
        ).join('');
        bodyHtml = `<div class="udyn-table-scroll"><table class="udyn-vac-table" style="min-width:360px;"><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table></div>`;
      } else {
        // Array of strings → tags
        bodyHtml = `<div class="udyn-tag-list">${
          value.map(s => `<div class="udyn-tag"><i class="fa-solid fa-circle-check"></i>${esc(String(s))}</div>`).join('')
        }</div>`;
      }
    } else if (typeof value === 'object' && !Array.isArray(value)) {
      const pairs = Object.entries(value).filter(([, v]) => hasContent(v));
      if (!pairs.length) return null;
      const rows = pairs.map(([k, v]) => {
        const valStr = typeof v === 'object' ? JSON.stringify(v) : String(v);
        return `<tr><th>${esc(keyToLabel(k))}</th><td>${esc(valStr)}</td></tr>`;
      }).join('');
      bodyHtml = `<table class="udyn-gen-table"><tbody>${rows}</tbody></table>`;
    } else if (typeof value === 'string' && value.trim()) {
      bodyHtml = isHtml(value)
        ? `<div class="udyn-html-body">${value}</div>`
        : `<div class="udyn-detail">${textToHtml(value)}</div>`;
    }

    if (!bodyHtml) return null;
    return makeCard(null, headBg, 'fa-solid fa-info-circle', label, bodyHtml);
  }

  /* ── 5m. SR Tables Card (merged_sarkari 'tables' field — array-of-array-of-arrays) ── */
  function buildTablesCard(tables) {
    if (!Array.isArray(tables) || !tables.length) return null;
    let allHtml = '';

    for (const tableGroup of tables) {
      if (!Array.isArray(tableGroup) || !tableGroup.length) continue;

      // Each tableGroup is an array of rows; each row is an array of cells
      const firstRow = tableGroup[0];

      if (Array.isArray(firstRow)) {
        // Array-of-arrays: [[cell1, cell2], [cell1, cell2], ...]
        // Detect if first row looks like a header (short text, no URL)
        const isHeader = firstRow.length === 2 && firstRow.every(c =>
          typeof c === 'string' && c.length < 80 && !/^https?:\/\//i.test(c)
        );

        let tbody = '';
        const dataRows = isHeader ? tableGroup.slice(1) : tableGroup;

        for (const row of dataRows) {
          if (!Array.isArray(row)) continue;
          const cells = row.map(cell => {
            const s = safe(String(cell ?? ''));
            // If cell looks like a URL, make it a link button
            if (/^https?:\/\//i.test(s)) {
              return `<td><a href="${esc(s)}" target="_blank" rel="noopener" style="color:#1d4ed8;font-weight:600;">Visit Link</a></td>`;
            }
            return `<td>${esc(s)}</td>`;
          }).join('');
          tbody += `<tr>${cells}</tr>`;
        }

        if (!tbody) continue;

        let thead = '';
        if (isHeader) {
          thead = `<thead><tr>${firstRow.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>`;
        }

        allHtml += `<div class="udyn-table-scroll" style="margin-bottom:8px;">` +
          `<table class="udyn-vac-table" style="min-width:300px;">` +
          thead + `<tbody>${tbody}</tbody>` +
          `</table></div>`;
      }
    }

    if (!allHtml) return null;
    return makeCard(
      'udyn-sr-tables',
      'linear-gradient(135deg,#1d4ed8,#1d6dbc)',
      'fa-solid fa-table',
      'Important Details',
      allHtml
    );
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 6 — SECTION-ALREADY-EXISTS GUARDS
     Prevent re-rendering sections already shown by base job.html renderer.
  ══════════════════════════════════════════════════════════════════════ */

  function sectionExists(id) {
    return !!document.getElementById(id);
  }

  function baseSectionVisible(id) {
    const el = document.getElementById(id);
    return el && el.style.display !== 'none';
  }

  function datesBaseVisible() {
    return baseSectionVisible('datesDetailCard');
  }

  function feeBaseVisible() {
    return baseSectionVisible('feeCard');
  }

  function vacancyBaseVisible() {
    // The base vacancy card is shown if it has visible rows
    const vc = document.getElementById('vacCard');
    if (!vc || vc.style.display === 'none') return false;
    const rows = vc.querySelectorAll('#vacBody tr');
    return rows.length > 0;
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 7 — LEFT-NAV TABLE OF CONTENTS UPDATER
     Dynamically adds TOC links matching the sections actually rendered.
  ══════════════════════════════════════════════════════════════════════ */

  function updateTOC(sectionsRendered) {
    const navList = document.querySelector('.jp-left-nav-list');
    if (!navList) return;

    // Remove previous dynamic TOC entries
    navList.querySelectorAll('.udyn-toc-link').forEach(el => el.remove());

    if (!sectionsRendered.length) return;

    // Add a divider
    const div = document.createElement('div');
    div.className = 'jp-left-nav-divider';
    div.textContent = 'Job Details';
    navList.appendChild(div);

    for (const { id, icon, label } of sectionsRendered) {
      const a = document.createElement('a');
      a.className = 'jp-left-nav-item udyn-toc-link';
      a.href = `#${id}`;
      a.innerHTML = `<i class="fa-solid ${icon}"></i>${label}`;
      navList.appendChild(a);
    }
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 8 — MASTER INJECTOR
     Orchestrates detection, building, and sequential insertion of all cards.
  ══════════════════════════════════════════════════════════════════════ */

  const SECTION_DEFS = [
    // [id, icon, label] — used for TOC and section anchors
    { id: 'udyn-jobs-info',         icon: 'fa-circle-info',         label: 'About This Recruitment' },
    { id: 'udyn-dates-extended',    icon: 'fa-calendar-check',      label: 'Important Dates'        },
    { id: 'udyn-fee',               icon: 'fa-indian-rupee-sign',   label: 'Application Fee'        },
    { id: 'udyn-vacancy-extended',  icon: 'fa-chart-pie',           label: 'Vacancy Details'        },
    { id: 'udyn-physical',          icon: 'fa-dumbbell',            label: 'Physical Eligibility'   },
    { id: 'udyn-exam-pattern',      icon: 'fa-file-lines',          label: 'Exam Pattern'           },
    { id: 'udyn-syllabus',          icon: 'fa-book',                label: 'Syllabus'               },
    { id: 'udyn-salary',            icon: 'fa-indian-rupee-sign',   label: 'Salary Details'         },
    { id: 'udyn-how-to-apply',      icon: 'fa-clipboard-list',      label: 'How To Apply'           },
    { id: 'udyn-instructions',      icon: 'fa-circle-exclamation',  label: 'Important Instructions' },
    { id: 'udyn-faq',               icon: 'fa-circle-question',     label: 'FAQ'                    },
  ];

  function injectAllSections(rawJob) {
    if (!rawJob || typeof rawJob !== 'object') return;

    // Guard: only run on job layout
    const layoutJob = document.getElementById('layoutJob');
    if (!layoutJob || layoutJob.style.display === 'none') return;

    // Clear any previously injected universal cards
    clearUniversalCards();

    const tocRendered = [];
    const CARDS_IN_ORDER = [];

    // ─── 1. About This Recruitment (jobs_info HTML) ────────────────────
    const jobsInfo = extractJobsInfo(rawJob);
    // Only show if base shortInfoCard is hidden or jobsInfo is different
    if (jobsInfo && !baseSectionVisible('shortInfoCard')) {
      const c = buildJobsInfo(jobsInfo);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-jobs-info') });
    }

    // ─── 2. Important Dates (extended) ────────────────────────────────
    // Only inject extended version if base datesDetailCard is NOT showing all fields
    const datesData = extractDates(rawJob);
    const allDateValues = Object.values(datesData.knownFields).concat(Object.values(datesData.extra)).filter(Boolean);
    const baseShownDates = datesBaseVisible();
    // Count how many dates the base card shows (it only renders specific fields)
    const baseDateRows = document.querySelectorAll('#datesDetailBody tr').length;
    const hasMissingDates = (allDateValues.length > baseDateRows) || (!baseShownDates && allDateValues.length > 0) || datesData.rawText;

    if (hasMissingDates) {
      const c = buildDatesExtended(datesData);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-dates-extended') });
    }

    // ─── 3. Application Fee (extended) ────────────────────────────────
    const feeData = extractFees(rawJob);
    const feeHasExtra = feeData.general_obc_ews || feeData.general_obc || feeData.all || feeData.flat || feeData.note;
    if (feeHasExtra && !feeBaseVisible()) {
      const c = buildFeeExtended(feeData);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-fee') });
    } else if (!feeBaseVisible()) {
      // Try to show any fee info we can find
      const hasSomeFee = Object.values(feeData).some(v => v);
      if (hasSomeFee) {
        const c = buildFeeExtended(feeData);
        if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-fee') });
      }
    }

    // ─── 4. Vacancy Details (dynamic columns) ─────────────────────────
    const { vd, cw } = extractVacancy(rawJob);
    if (!vacancyBaseVisible() && (vd.length > 0 || hasContent(cw))) {
      const c = buildVacancyExtended(vd, cw);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-vacancy-extended') });
    }

    // ─── 5. Physical Eligibility ───────────────────────────────────────
    const pe = extractPhysical(rawJob);
    if (pe) {
      const c = buildPhysical(pe);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-physical') });
    }

    // ─── 6. Exam Pattern ──────────────────────────────────────────────
    const ep = extractExamPattern(rawJob);
    if (ep) {
      const c = buildExamPattern(ep);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-exam-pattern') });
    }

    // ─── 7. Syllabus ──────────────────────────────────────────────────
    const syl = extractSyllabus(rawJob);
    if (syl) {
      const c = buildSyllabus(syl);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-syllabus') });
    }

    // ─── 8. Salary Details ────────────────────────────────────────────
    const { structured: sd, flat: salFlat } = extractSalary(rawJob);
    const hasSalaryData = hasContent(sd) || salFlat;
    if (hasSalaryData && !sectionExists('dynSalaryDetails')) {
      const c = buildSalaryDetails(sd, salFlat);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-salary') });
    }

    // ─── 9. How To Apply ──────────────────────────────────────────────
    const hta = extractHowToApply(rawJob);
    if (hasContent(hta) && !sectionExists('dynHowToApply')) {
      const c = buildHowToApply(hta);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-how-to-apply') });
    }

    // ─── 10. Important Instructions ───────────────────────────────────
    const insts = extractInstructions(rawJob);
    if (hasContent(insts) && !sectionExists('dynInstructions')) {
      const c = buildInstructions(insts);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-instructions') });
    }

    // ─── 11. FAQ ──────────────────────────────────────────────────────
    const faqs = extractFaq(rawJob);
    if (hasContent(faqs) && !sectionExists('dynFaq')) {
      const c = buildFaq(faqs);
      if (c) CARDS_IN_ORDER.push({ card: c, def: SECTION_DEFS.find(d => d.id === 'udyn-faq') });
    }

    // ─── 11b. SR Tables (merged_sarkari 'tables' field) ───────────────
    const tablesData = extractTables(rawJob);
    if (tablesData && !sectionExists('dynSRTable') && !sectionExists('udyn-sr-tables')) {
      const c = buildTablesCard(tablesData);
      if (c) CARDS_IN_ORDER.push({ card: c, def: { id: 'udyn-sr-tables', icon: 'fa-table', label: 'Important Details' } });
    }

    // ─── 12. AUTO-RENDER: Unknown future fields ────────────────────────
    const unknownFields = extractUnknownFields(rawJob);
    for (const [k, v] of Object.entries(unknownFields)) {
      const c = buildGeneric(k, v);
      if (c) CARDS_IN_ORDER.push({ card: c, def: { id: `udyn-generic-${k}`, icon: 'fa-info-circle', label: keyToLabel(k) } });
    }

    // ─── Insert all cards in ORDER before Important Links ─────────────
    for (const { card, def } of CARDS_IN_ORDER) {
      insertBeforeLinks(card);
      if (def) tocRendered.push(def);
    }

    // ─── Update Left-Nav TOC ──────────────────────────────────────────
    updateTOC(tocRendered);
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 9 — FIELD PATCHING (update existing base-renderer elements)
     These patches apply real data from JSON to fields already rendered
     by job.html's base renderer when those fields have richer data.
  ══════════════════════════════════════════════════════════════════════ */

  function patchField(id, value) {
    if (!value) return;
    const el = document.getElementById(id);
    if (el && (el.textContent === '—' || el.textContent === '' || el.textContent === 'See Notification')) {
      el.textContent = value;
    }
  }

  function patchTableRow(tbodyId, labelPattern, value) {
    if (!value) return;
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    for (const tr of tbody.querySelectorAll('tr')) {
      const th = tr.querySelector('th');
      if (th && labelPattern.test(th.textContent)) {
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

    // Organisation
    const org = safe(rawJob.organization || rawJob.board_name || rawJob.department || bd.organization_name || bd.department || '');
    patchField('statOrg', org);
    patchTableRow('jbTable', /organisation/i, org);

    // Total vacancies
    const tv = safe(rawJob.total_vacancy || rawJob.total_vacancies || bd.total_vacancies || rawJob.total_post || '');
    if (tv) {
      patchField('statPosts', tv);
      patchTableRow('jbTable', /total vacancies/i, tv);
    }

    // Apply mode
    const mode = safe(rawJob.apply_mode || rawJob.application_mode || bd.apply_mode || '');
    if (mode) {
      const el = document.getElementById('statApplyMode');
      if (el) {
        el.textContent = mode;
        el.style.color = /offline/i.test(mode) ? '#ea580c' : '#16a34a';
      }
      patchTableRow('jbTable', /application mode/i, mode);
    }

    // Last date — patch both stat box and sidebar
    const lastDate = safe(
      id.last_date || id.application_last_date || id.last_date_for_apply ||
      rawJob.last_date || rawJob.last_date_to_apply || ''
    );
    if (lastDate && !/^see notification$/i.test(lastDate)) {
      const fmt = fmtDatePatch(lastDate);
      patchField('statLastDate', fmt);
      patchField('dateLastVal', fmt);
      const sideRow = document.getElementById('dateLastRow');
      if (sideRow) sideRow.style.display = '';
      const metaWrap = document.getElementById('metaLastDateWrap');
      const metaEl = document.getElementById('metaLastDate');
      if (metaWrap && metaEl) {
        metaEl.textContent = 'Last Date: ' + fmt;
        metaWrap.style.display = '';
      }
    }

    // Salary — add row in overview table if missing
    const salary = safe(rawJob.salary || rawJob.salary_pay_scale || bd.salary || bd.salary_pay_scale || '');
    if (salary) {
      const rows = document.querySelectorAll('#jbTable tbody tr');
      let hasSalRow = false;
      for (const tr of rows) {
        const th = tr.querySelector('th');
        if (th && /salary/i.test(th.textContent)) { hasSalRow = true; break; }
      }
      if (!hasSalRow) {
        const tbody = document.querySelector('#jbTable tbody');
        if (tbody) {
          const tr = document.createElement('tr');
          tr.innerHTML = `<th>Salary / Pay Scale</th><td>${esc(salary)}</td>`;
          const lastTr = tbody.lastElementChild;
          if (lastTr) tbody.insertBefore(tr, lastTr);
          else tbody.appendChild(tr);
        }
      }
    }

    // Age limit — populate base ageCard if not already shown
    const minAge = safe(rawJob.minimum_age || age.minimum_age || '');
    const maxAge = safe(rawJob.maximum_age || age.maximum_age || age.age_limit || age.age_details || '');
    const ageRelax = safe(rawJob.age_relaxation || age.age_relaxation || age.details || '');
    const ageCard = document.getElementById('ageCard');
    if ((minAge || maxAge || ageRelax) && ageCard && ageCard.style.display === 'none') {
      ageCard.style.display = '';
      const ageRows = [];
      if (minAge)   ageRows.push(['Minimum Age', minAge]);
      if (maxAge)   ageRows.push(['Maximum Age', maxAge]);
      if (ageRelax) ageRows.push(['Age Relaxation', ageRelax]);
      const ageBody = document.getElementById('ageTableBody');
      if (ageBody) {
        ageBody.innerHTML = ageRows.map(([k,v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('');
      }
    }

    // Qualification / Eligibility — populate base qualCard if missing
    const eduQual = safe(rawJob.education_qualification || rawJob.eligibility ||
      (rawJob.qualification && rawJob.qualification.education_qualification) ||
      (rawJob.qualification && rawJob.qualification.eligibility) || '');
    const qualCard = document.getElementById('qualCard');
    if (eduQual && qualCard && qualCard.style.display === 'none') {
      qualCard.style.display = '';
      const qualContent = document.getElementById('qualContent');
      if (qualContent) {
        qualContent.innerHTML = `<div class="jp-detail-text"><strong>Education Qualification:</strong> ${esc(eduQual)}</div>`;
      }
    }

    // Short information — show shortInfoCard if missing
    const shortInfo = safe(rawJob.short_information || rawJob.jobs_info || bd.short_information || '');
    const siCard = document.getElementById('shortInfoCard');
    const siText = document.getElementById('shortInfoText');
    if (shortInfo && siCard && siCard.style.display === 'none' && siText) {
      siCard.style.display = '';
      if (isHtml(shortInfo)) {
        siText.innerHTML = shortInfo;
      } else {
        siText.textContent = shortInfo;
      }
    }
  }

  /** Minimal date formatter (standalone, no dep on job.html scope) */
  function fmtDatePatch(val) {
    const s = safe(val);
    let m = s.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})$/);
    if (m) return ('0'+m[3]).slice(-2)+'/'+('0'+m[2]).slice(-2)+'/'+m[1];
    m = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
    if (m) return ('0'+m[1]).slice(-2)+'/'+('0'+m[2]).slice(-2)+'/'+m[3];
    return s;
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 10 — FALLBACK: SCAN FULL JSON FOR MATCHING JOB
     When the job page was loaded from dailyupdates.json (no individual
     /jobs/data/<slug>.json found) and window.__TSJ_RAW_JOB is null,
     this function searches all 4 JSON sources for a matching job to
     enrich the page with full structured data.
  ══════════════════════════════════════════════════════════════════════ */

  const STOP_WORDS = new Set([
    'the','and','for','are','was','were','has','have','had','will','can','may',
    '2024','2025','2026','2027','apply','online','offline','form','now','out',
    'notification','vacancy','vacancies','recruitment','post','posts','latest',
    'result','admit','card','answer','key','exam','date','last','jobs','job',
    'syllabus','merit','list','score','hall','ticket','call','letter',
  ]);

  function normStr(s) {
    return safe(s).toLowerCase()
      .replace(/[^\x00-\x7e]/g, ' ')
      .replace(/&/g, ' and ')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  }

  function scoreMatch(title, tokens) {
    const t = normStr(title);
    if (!t) return 0;
    const matches = tokens.filter(tk => t.includes(tk)).length;
    return matches / tokens.length;
  }

  async function findAndEnrichFromFullData() {
    const slug = window.__TSJ_SLUG || '';
    if (!slug) return;

    // Only run on job layout that isn't already enriched
    const layoutJob = document.getElementById('layoutJob');
    if (!layoutJob || layoutJob.style.display === 'none') return;
    if (document.querySelector('.udyn-card')) return; // already enriched

    const slugNorm = normStr(slug.replace(/-/g, ' '));
    const tokens = slugNorm.split(/\s+/).filter(t => t.length > 3 && !STOP_WORDS.has(t));
    if (tokens.length < 2) return;

    let best = null, bestScore = 0;

    // Search merged_sarkari_data.json (offline form jobs)
    try {
      const r = await fetch('/merged_sarkari_data.json');
      if (r.ok) {
        const d = await r.json();
        const jobs = (d && d.jobs) ? d.jobs : [];
        for (const job of jobs) {
          const title = safe(job.title || job.post_name || '');
          const sc = scoreMatch(title, tokens);
          if (sc > bestScore) { bestScore = sc; best = job; }
        }
      }
    } catch (_) {}

    // Search Complete_Jobs_Full_Data.json (1300+ structured jobs)
    if (!best || bestScore < 0.82) {
      try {
        const r = await fetch('/Complete_Jobs_Full_Data.json');
        if (r.ok) {
          const d = await r.json();
          const jobs = [];
          if (Array.isArray(d)) {
            jobs.push(...d);
          } else if (typeof d === 'object') {
            for (const val of Object.values(d)) {
              if (Array.isArray(val)) jobs.push(...val);
            }
          }
          for (const job of jobs) {
            const title = safe(
              job.title || (job.basic_details && job.basic_details.job_title) || job.post_name || ''
            );
            const sc = scoreMatch(title, tokens);
            if (sc > bestScore) { bestScore = sc; best = job; }
          }
        }
      } catch (_) {}
    }

    // Use HIGH threshold (0.82) to prevent wrong-job enrichment
    if (best && bestScore >= 0.82) {
      runBasePatches(best);
      injectAllSections(best);
    }
  }


  /* ══════════════════════════════════════════════════════════════════════
     § 11 — INTEGRATION
     Race-condition-free callback system that works whether this deferred
     script loads before or after job.html's inline render completes.
  ══════════════════════════════════════════════════════════════════════ */

  function onJobRendered(rawJob) {
    if (rawJob && typeof rawJob === 'object') {
      // Normalize UPCOMING_JOBS sections[] format → structured fields
      try { rawJob = normalizeUpcomingJobsSections(rawJob); } catch (e) { console.warn('[Universal Renderer] Normalize error:', e); }
      // We have the raw JSON — run patches + inject sections
      try { runBasePatches(rawJob); } catch (e) { console.warn('[Universal Renderer] Patch error:', e); }
      try { injectAllSections(rawJob); } catch (e) { console.warn('[Universal Renderer] Inject error:', e); }
    } else {
      // No raw JSON (dailyupdates item) — try enrichment from full data
      setTimeout(findAndEnrichFromFullData, 200);
    }
  }

  (function integrate() {
    // Case 1: job.html already done rendering (fast cache / pre-rendered)
    if (window.__TSJ_RENDER_DONE) {
      setTimeout(() => onJobRendered(window.__TSJ_RAW_JOB), 0);
      return;
    }

    // Case 2: Not done yet — register as the __TSJ_ON_RENDER_DONE callback
    // job.html calls this in its finally{} block
    window.__TSJ_ON_RENDER_DONE = function (rawJob) {
      setTimeout(() => onJobRendered(rawJob), 0);
    };

    // Case 3: Fallback — fetch-intercept (for legacy compatibility if
    // __TSJ_ON_RENDER_DONE is not called by job.html)
    const _origFetch = window.fetch;
    window.fetch = async function (...args) {
      const res = await _origFetch.apply(this, args);
      const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
      if (url && url.includes('/jobs/data/') && url.endsWith('.json')) {
        const clone = res.clone();
        clone.json().then(data => {
          if (data && (data.basic_details || data.title)) {
            window.__TSJ_RAW_JOB = data;
            // Wait for render complete
            let tries = 0;
            const id = setInterval(() => {
              const layout = document.getElementById('jbThreeCol');
              const loading = document.getElementById('jbLoading');
              if ((layout && layout.style.display !== 'none') ||
                  (loading && loading.style.display === 'none') ||
                  tries > 80) {
                clearInterval(id);
                setTimeout(() => {
                  // Only if __TSJ_ON_RENDER_DONE wasn't already called
                  if (!document.querySelector('.udyn-card') && !document.querySelector('.dyn-card')) {
                    onJobRendered(data);
                  }
                }, 150);
              }
              tries++;
            }, 100);
          }
        }).catch(() => {});
      }
      return res;
    };

    // Case 4: Last-resort polling (handles all edge cases)
    let _pollCount = 0;
    const _pollId = setInterval(() => {
      _pollCount++;
      const layout = document.getElementById('jbThreeCol');
      const loading = document.getElementById('jbLoading');
      const done = (layout && layout.style.display !== 'none') ||
                   (loading && loading.style.display === 'none') ||
                   window.__TSJ_RENDER_DONE;

      if (done || _pollCount > 100) {
        clearInterval(_pollId);
        // Only inject if not already done
        if (!document.querySelector('.udyn-card') && !document.querySelector('.dyn-card')) {
          setTimeout(() => onJobRendered(window.__TSJ_RAW_JOB || null), 100);
        }
      }
    }, 100);
  })();


})();
/* ── END Universal Dynamic JSON-to-Page Rendering System ── */
