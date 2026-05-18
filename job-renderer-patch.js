/**
 * ══════════════════════════════════════════════════════════════════════
 *  TOP SARKARI JOBS — JSON-Driven Dynamic Job Rendering System
 *  File: job-renderer-patch.js   Version: 2026-05-16
 * ══════════════════════════════════════════════════════════════════════
 *
 *  WHAT THIS PATCH FIXES / ADDS:
 *  ─────────────────────────────
 *  1. parseFullJob() — extracts ALL JSON fields that were previously ignored:
 *       how_to_apply, faq, physical_eligibility, exam_pattern,
 *       syllabus, salary_details, important_instructions
 *
 *  2. renderJobPage() — injects NEW HTML cards into the page DYNAMICALLY
 *       in correct sequence order (same as JSON field order):
 *       shortInfo → overview → dates → fee → age → qualification →
 *       vacancy → physicalEligibility → examPattern → syllabus →
 *       salaryDetails → selectionProcess → howToApply →
 *       importantInstructions → faq → importantLinks
 *
 *  3. AUTO-RENDER SYSTEM — any new JSON field added in future will
 *       auto-render via the universal `renderGenericSection()` fallback.
 *
 *  4. Non-Job pages also get full detail rendering (scheme/result/admit).
 *
 *  HOW TO USE:
 *  ───────────
 *  Add this ONE line at the end of <body> in job.html (before </body>):
 *
 *      <script src="/job-renderer-patch.js?v=20260516"></script>
 *
 *  This patches the existing renderJobPage and parseFullJob on the
 *  window object so no other changes are needed.
 *
 * ══════════════════════════════════════════════════════════════════════
 */

(function () {
  'use strict';

  /* ══════════════════════════════════════════════════════════════════
     SECTION 1 — CSS INJECTION
     Styles for all new dynamic sections
  ══════════════════════════════════════════════════════════════════ */
  const css = `
    /* ── Dynamic Section Cards ── */
    .dyn-card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      overflow: hidden;
      margin-bottom: 14px;
      box-shadow: 0 1px 3px rgba(0,0,0,.04);
    }
    .dyn-head {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 9px 14px;
      color: #fff;
      font-size: .86rem;
      font-weight: 700;
    }
    .dyn-head i { opacity: .85; }

    /* How To Apply — Numbered Steps */
    .hta-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .hta-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 10px 14px;
      border-bottom: 1px solid #f1f5f9;
      font-size: .83rem;
      color: #1e293b;
      line-height: 1.65;
    }
    .hta-item:last-child { border-bottom: none; }
    .hta-num {
      flex-shrink: 0;
      width: 24px;
      height: 24px;
      background: #1d4ed8;
      color: #fff;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: .72rem;
      font-weight: 800;
      margin-top: 1px;
    }

    /* FAQ */
    .faq-item {
      border-bottom: 1px solid #f1f5f9;
    }
    .faq-item:last-child { border-bottom: none; }
    .faq-q {
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
    }
    .faq-q:hover { background: #f0f7ff; }
    .faq-q .faq-icon {
      color: #1d4ed8;
      font-size: .8rem;
      margin-top: 3px;
      flex-shrink: 0;
      transition: transform .2s;
    }
    .faq-q.open .faq-icon { transform: rotate(90deg); }
    .faq-a {
      display: none;
      padding: 0 14px 12px 40px;
      font-size: .82rem;
      color: #374151;
      line-height: 1.7;
    }
    .faq-a.open { display: block; }

    /* Physical Eligibility */
    .phy-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    }
    .phy-item {
      padding: 10px 14px;
      border-right: 1px solid #e9eef4;
      border-bottom: 1px solid #e9eef4;
    }
    .phy-label {
      font-size: .68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .05em;
      color: #64748b;
      margin-bottom: 3px;
    }
    .phy-val {
      font-size: .88rem;
      font-weight: 700;
      color: #0f172a;
    }

    /* Exam Pattern / Syllabus */
    .ep-table {
      width: 100%;
      border-collapse: collapse;
      font-size: .82rem;
    }
    .ep-table th {
      background: #1d4ed8;
      color: #fff;
      padding: 8px 12px;
      text-align: left;
      font-weight: 700;
    }
    .ep-table td {
      padding: 8px 12px;
      border-bottom: 1px solid #e9eef4;
      color: #1e293b;
      vertical-align: top;
      line-height: 1.6;
    }
    .ep-table tr:last-child td { border-bottom: none; }

    /* Salary Details */
    .sal-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    }
    .sal-item {
      padding: 10px 14px;
      border-right: 1px solid #e9eef4;
      border-bottom: 1px solid #e9eef4;
    }
    .sal-label {
      font-size: .68rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .05em;
      color: #64748b;
      margin-bottom: 3px;
    }
    .sal-val {
      font-size: .9rem;
      font-weight: 800;
      color: #16a34a;
    }

    /* Important Instructions */
    .inst-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .inst-item {
      display: flex;
      align-items: flex-start;
      gap: 9px;
      padding: 8px 14px;
      border-bottom: 1px solid #f1f5f9;
      font-size: .82rem;
      color: #374151;
      line-height: 1.65;
    }
    .inst-item:last-child { border-bottom: none; }
    .inst-item i { color: #ea580c; flex-shrink: 0; margin-top: 3px; }

    /* Generic auto-render table */
    .gen-table {
      width: 100%;
      border-collapse: collapse;
      font-size: .82rem;
    }
    .gen-table th {
      width: 35%;
      background: #f8fafc;
      color: #374151;
      font-size: .82rem;
      font-weight: 700;
      padding: 9px 14px;
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid #e9eef4;
    }
    .gen-table td {
      padding: 9px 14px;
      color: #1e293b;
      font-size: .83rem;
      line-height: 1.65;
      border-bottom: 1px solid #e9eef4;
      vertical-align: top;
    }
    .gen-table tr:last-child th,
    .gen-table tr:last-child td { border-bottom: none; }

    /* Tag chips for list items */
    .dyn-tag-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 12px 14px;
    }
    .dyn-tag {
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
    .dyn-tag i { color: #1d4ed8; }

    /* Detail text block */
    .dyn-detail {
      padding: 10px 14px;
      font-size: .83rem;
      color: #1e293b;
      line-height: 1.7;
      border-bottom: 1px solid #f1f5f9;
    }
    .dyn-detail:last-child { border-bottom: none; }
  `;

  const styleEl = document.createElement('style');
  styleEl.id = 'tsj-dyn-styles';
  styleEl.textContent = css;
  document.head.appendChild(styleEl);


  /* ══════════════════════════════════════════════════════════════════
     SECTION 2 — UTILITY HELPERS (shared with job.html inline script)
  ══════════════════════════════════════════════════════════════════ */

  const safe = v => (v ?? '').toString().trim();

  /** Escape HTML special chars to prevent XSS */
  function esc(str) {
    return safe(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /** Convert a plain-text value with line-breaks to safe HTML paragraphs */
  function textToHtml(str) {
    return safe(str)
      .split(/\n+/)
      .map(l => l.trim())
      .filter(Boolean)
      .map(l => `<p style="margin:0 0 6px;">${esc(l)}</p>`)
      .join('');
  }

  /** Human-readable key formatter: "how_to_apply" → "How To Apply" */
  function keyToLabel(k) {
    return k.replace(/_/g, ' ').replace(/\b[a-z]/g, c => c.toUpperCase());
  }

  /** Create a section card element */
  function makeCard(id, headBg, iconCls, headText, bodyHtml) {
    const d = document.createElement('div');
    d.className = 'dyn-card';
    if (id) d.id = id;
    d.innerHTML = `
      <div class="dyn-head" style="background:${headBg};">
        <i class="${iconCls}"></i> ${esc(headText)}
      </div>
      <div class="dyn-body">${bodyHtml}</div>
    `;
    return d;
  }

  /** Insert a card BEFORE the Important Links card or at end of #jbContent */
  function insertBeforeLinks(card) {
    const layout = document.getElementById('layoutJob');
    if (!layout) return;
    // Find existing Important Links card (last .jp-card in layoutJob)
    const allCards = layout.querySelectorAll('.jp-card');
    let linksCard = null;
    for (const c of allCards) {
      const head = c.querySelector('.jp-sec-head');
      if (head && /important links/i.test(head.textContent)) { linksCard = c; break; }
    }
    if (linksCard) {
      layout.insertBefore(card, linksCard);
    } else {
      // Before the tips card
      const tipsCard = layout.querySelector('.jp-tips-card');
      if (tipsCard) layout.insertBefore(card, tipsCard);
      else layout.appendChild(card);
    }
  }

  /** Remove all previously injected dynamic cards (avoid duplicates on re-render) */
  function clearDynCards() {
    document.querySelectorAll('.dyn-card').forEach(el => el.remove());
  }


  /* ══════════════════════════════════════════════════════════════════
     SECTION 3 — CARD BUILDERS (one per JSON section)
  ══════════════════════════════════════════════════════════════════ */

  /* ── 3a. How To Apply ── */
  function buildHowToApplyCard(steps) {
    /* Support both array of strings AND a single plain string */
    let stepsArr = [];
    if (Array.isArray(steps) && steps.length) {
      stepsArr = steps;
    } else if (typeof steps === 'string' && steps.trim()) {
      /* Split by newlines or sentence-ending periods to create numbered steps */
      const sentences = steps
        .split(/\n+/)
        .map(l => l.trim())
        .filter(Boolean);
      stepsArr = sentences.length > 1 ? sentences : [steps.trim()];
    }
    if (!stepsArr.length) return null;

    const items = stepsArr
      .map((s, i) => `
        <li class="hta-item">
          <span class="hta-num">${i + 1}</span>
          <span>${esc(s)}</span>
        </li>`)
      .join('');
    return makeCard(
      'dynHowToApply',
      'linear-gradient(135deg,#0f766e,#0891b2)',
      'fa-solid fa-clipboard-list',
      'How To Apply',
      `<ul class="hta-list">${items}</ul>`
    );
  }

  /* ── 3b. FAQ ── */
  function buildFaqCard(faqs) {
    if (!Array.isArray(faqs) || !faqs.length) return null;
    // Deduplicate by question text
    const seen = new Set();
    const unique = faqs.filter(f => {
      const q = safe(f.question || f.q || '');
      if (!q || seen.has(q)) return false;
      seen.add(q);
      return true;
    });
    if (!unique.length) return null;

    const items = unique.map((f, i) => {
      const q = esc(f.question || f.q || '');
      const a = esc(f.answer   || f.a || '');
      return `
        <div class="faq-item">
          <div class="faq-q" data-faq="${i}" onclick="(function(el){
            el.classList.toggle('open');
            el.nextElementSibling.classList.toggle('open');
          })(this)">
            <i class="fa-solid fa-chevron-right faq-icon"></i>
            <span>${q}</span>
          </div>
          <div class="faq-a">${a}</div>
        </div>`;
    }).join('');

    return makeCard(
      'dynFaq',
      'linear-gradient(135deg,#b45309,#d97706)',
      'fa-solid fa-circle-question',
      'Frequently Asked Questions (FAQ)',
      items
    );
  }

  /* ── 3c. Physical Eligibility ── */
  function buildPhysicalCard(pe) {
    if (!pe || typeof pe !== 'object') return null;
    const pairs = Object.entries(pe).filter(([, v]) => v);
    if (!pairs.length) return null;

    const items = pairs.map(([k, v]) => `
      <div class="phy-item">
        <div class="phy-label">${esc(keyToLabel(k))}</div>
        <div class="phy-val">${esc(v)}</div>
      </div>`).join('');

    return makeCard(
      'dynPhysical',
      'linear-gradient(135deg,#be123c,#e11d48)',
      'fa-solid fa-dumbbell',
      'Physical Eligibility / Standards',
      `<div class="phy-grid">${items}</div>`
    );
  }

  /* ── 3d. Exam Pattern ── */
  function buildExamPatternCard(ep) {
    if (!ep) return null;

    let bodyHtml = '';

    // Array of objects (sections)
    if (Array.isArray(ep) && ep.length) {
      const cols = Object.keys(ep[0]).filter(k => k !== 'sr_no' && k !== 'sno');
      const thead = ['Sr.No', ...cols.map(keyToLabel)].map(c => `<th>${esc(c)}</th>`).join('');
      const rows = ep.map((row, i) =>
        `<tr><td>${i + 1}</td>${cols.map(c => `<td>${esc(row[c] ?? '')}</td>`).join('')}</tr>`
      ).join('');
      bodyHtml = `<div style="overflow-x:auto;"><table class="ep-table"><thead><tr>${thead}</tr></thead><tbody>${rows}</tbody></table></div>`;
    }
    // Plain object
    else if (typeof ep === 'object' && Object.keys(ep).length) {
      const rows = Object.entries(ep).filter(([, v]) => v).map(([k, v]) =>
        `<tr><th>${esc(keyToLabel(k))}</th><td>${esc(v)}</td></tr>`
      ).join('');
      if (!rows) return null;
      bodyHtml = `<table class="gen-table"><tbody>${rows}</tbody></table>`;
    }
    // String
    else if (typeof ep === 'string' && ep.trim()) {
      bodyHtml = `<div class="dyn-detail">${textToHtml(ep)}</div>`;
    }

    if (!bodyHtml) return null;
    return makeCard(
      'dynExamPattern',
      'linear-gradient(135deg,#0369a1,#0284c7)',
      'fa-solid fa-file-lines',
      'Exam Pattern',
      bodyHtml
    );
  }

  /* ── 3e. Syllabus ── */
  function buildSyllabusCard(syl) {
    if (!syl) return null;
    let bodyHtml = '';

    if (Array.isArray(syl) && syl.length) {
      const items = syl.map(s => `<div class="dyn-tag"><i class="fa-solid fa-book-open"></i>${esc(s)}</div>`).join('');
      bodyHtml = `<div class="dyn-tag-list">${items}</div>`;
    } else if (typeof syl === 'object' && Object.keys(syl).length) {
      const rows = Object.entries(syl).filter(([, v]) => v).map(([k, v]) =>
        `<tr><th>${esc(keyToLabel(k))}</th><td>${esc(v)}</td></tr>`
      ).join('');
      if (!rows) return null;
      bodyHtml = `<table class="gen-table"><tbody>${rows}</tbody></table>`;
    } else if (typeof syl === 'string' && syl.trim()) {
      bodyHtml = `<div class="dyn-detail">${textToHtml(syl)}</div>`;
    }

    if (!bodyHtml) return null;
    return makeCard(
      'dynSyllabus',
      'linear-gradient(135deg,#4338ca,#6366f1)',
      'fa-solid fa-book',
      'Syllabus / Exam Topics',
      bodyHtml
    );
  }

  /* ── 3f. Salary Details ── */
  function buildSalaryDetailsCard(sd) {
    if (!sd || typeof sd !== 'object') return null;
    const pairs = Object.entries(sd).filter(([, v]) => v);
    if (!pairs.length) return null;

    const items = pairs.map(([k, v]) => `
      <div class="sal-item">
        <div class="sal-label">${esc(keyToLabel(k))}</div>
        <div class="sal-val">${esc(v)}</div>
      </div>`).join('');

    return makeCard(
      'dynSalaryDetails',
      'linear-gradient(135deg,#15803d,#16a34a)',
      'fa-solid fa-indian-rupee-sign',
      'Salary & Pay Scale Details',
      `<div class="sal-grid">${items}</div>`
    );
  }

  /* ── 3g. Important Instructions ── */
  function buildInstructionsCard(insts) {
    let instArr = [];
    if (Array.isArray(insts) && insts.length) {
      instArr = insts.filter(s => safe(s));
    } else if (typeof insts === 'string' && insts.trim()) {
      /* Split by newlines or sentence boundaries */
      const lines = insts.split(/\n+/).map(l => l.trim()).filter(Boolean);
      instArr = lines.length > 1 ? lines : [insts.trim()];
    }
    if (!instArr.length) return null;

    const items = instArr.map(s => `
      <li class="inst-item">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span>${esc(s)}</span>
      </li>`).join('');

    return makeCard(
      'dynInstructions',
      'linear-gradient(135deg,#b45309,#ca8a04)',
      'fa-solid fa-circle-exclamation',
      'Important Instructions',
      `<ul class="inst-list">${items}</ul>`
    );
  }

  /* ── 3h. Generic Section (AUTO-RENDER fallback for unknown future fields) ── */
  function buildGenericCard(fieldKey, value) {
    if (!value) return null;
    const label = keyToLabel(fieldKey);
    let bodyHtml = '';

    if (Array.isArray(value)) {
      if (!value.length) return null;
      // Array of objects → table
      if (typeof value[0] === 'object' && value[0] !== null) {
        const cols = Object.keys(value[0]);
        const thead = cols.map(c => `<th>${esc(keyToLabel(c))}</th>`).join('');
        const rows = value.map(r =>
          `<tr>${cols.map(c => `<td>${esc(r[c] ?? '')}</td>`).join('')}</tr>`
        ).join('');
        bodyHtml = `<div style="overflow-x:auto;"><table class="ep-table"><thead><tr>${thead}</tr></thead><tbody>${rows}</tbody></table></div>`;
      } else {
        // Array of strings
        const items = value.map(s => `<div class="dyn-tag"><i class="fa-solid fa-circle-check"></i>${esc(s)}</div>`).join('');
        bodyHtml = `<div class="dyn-tag-list">${items}</div>`;
      }
    } else if (typeof value === 'object') {
      const rows = Object.entries(value).filter(([, v]) => v).map(([k, v]) =>
        `<tr><th>${esc(keyToLabel(k))}</th><td>${esc(v)}</td></tr>`
      ).join('');
      if (!rows) return null;
      bodyHtml = `<table class="gen-table"><tbody>${rows}</tbody></table>`;
    } else if (typeof value === 'string' && value.trim()) {
      bodyHtml = `<div class="dyn-detail">${textToHtml(value)}</div>`;
    }

    if (!bodyHtml) return null;
    return makeCard(null, 'linear-gradient(135deg,#475569,#64748b)', 'fa-solid fa-info-circle', label, bodyHtml);
  }


  /* ══════════════════════════════════════════════════════════════════
     SECTION 4 — EXTENDED parseFullJob (PATCH)
     Adds extraction of all missing JSON fields.
     Call this from job.html's run() AFTER your existing parseFullJob().
  ══════════════════════════════════════════════════════════════════ */

  /**
   * Extracts ALL additional fields from raw job JSON that the base
   * parseFullJob() doesn't handle. Returns a plain object with the extra fields.
   *
   * @param {object} job — Raw job JSON object
   * @returns {object}
   */
  function extractExtraFields(job) {
    if (!job || typeof job !== 'object') return {};

    const bd  = job.basic_details  || {};
    const sal = job.salary_details || {};

    /* Normalise salary_details: prefer nested object, fallback to bd or flat fields */
    const salaryDetails = (() => {
      const s = {};
      const src = (Object.keys(sal).length > 0) ? sal : {};
      /* Known keys */
      const salKeys = ['pay_scale','details','pay_band','grade_pay','level','stipend',
                       'basic_pay','allowances','gross_salary','net_salary','ctc',
                       'salary_per_month','salary_per_year'];
      salKeys.forEach(k => {
        const v = safe(src[k] || job[k] || bd[k] || '');
        if (v) s[k] = v;
      });
      /* Fallback: if salary_details is just {pay_scale, details} try flattening */
      if (!Object.keys(s).length) {
        Object.entries(sal).forEach(([k, v]) => { if (v) s[k] = v; });
      }
      return Object.keys(s).length ? s : null;
    })();

    return {
      howToApply:            job.how_to_apply            || bd.how_to_apply            || null,
      faq:                   job.faq                     || bd.faq                     || null,
      physicalEligibility:   job.physical_eligibility    || bd.physical_eligibility    || null,
      examPattern:           job.exam_pattern            || bd.exam_pattern            || null,
      syllabusData:          job.syllabus                || bd.syllabus                || null,
      salaryDetails:         salaryDetails,
      importantInstructions: job.important_instructions  || bd.important_instructions  || null,

      /* Capture any UNKNOWN top-level keys for auto-rendering */
      _unknownFields: (() => {
        const known = new Set([
          'basic_details','important_dates','application_fee','age_limit',
          'qualification','vacancy_details','category_wise_vacancy','important_links',
          'important_links_obj','useful_links','salary_details','selection_process',
          'short_information','jobs_info','exam_pattern','syllabus','how_to_apply',
          'faq','physical_eligibility','important_instructions','seo_tags',
          'title','post_name','organization','board_name','department','category',
          'total_vacancy','total_vacancies','apply_mode','source_url','slug',
          'last_date','application_begin','salary','salary_pay_scale',
          'education_qualification','eligibility','experience_required',
          'official_website_link','form_pdf_free_link','official_notification_pdf_link',
          'minimum_age','maximum_age','age_relaxation',
        ]);
        const extras = {};
        for (const [k, v] of Object.entries(job)) {
          if (!known.has(k) && v && typeof v !== 'function') {
            /* Only include non-empty non-trivial values */
            if (typeof v === 'string' && v.trim()) extras[k] = v;
            else if (Array.isArray(v) && v.length) extras[k] = v;
            else if (typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length) extras[k] = v;
          }
        }
        return extras;
      })(),
    };
  }


  /* ══════════════════════════════════════════════════════════════════
     SECTION 5 — DYNAMIC RENDER ENGINE
     Called after the base renderJobPage() runs.
     Injects all missing sections into the DOM in correct order.
  ══════════════════════════════════════════════════════════════════ */

  /**
   * Injects all dynamic JSON-driven cards into the job page.
   *
   * @param {object} rawJobJson   — The raw JSON object fetched from /jobs/data/<slug>.json
   * @param {object} parsedRow    — Result of parseFullJob() (base extracted row)
   */
  function injectDynamicSections(rawJobJson, parsedRow) {
    /* Clear any previously injected dyn-cards (prevents duplicates on SPA re-renders) */
    clearDynCards();

    const extras = extractExtraFields(rawJobJson);

    /* ── RENDER SEQUENCE (matches logical reading order) ──
       Each card is inserted before the Important Links card,
       in reverse order (because each insertBeforeLinks puts the
       card just before Links, so the LAST inserted appears first
       before links). We build an ordered array then reverse-insert. */

    const cards = [];

    /* 1. Physical Eligibility */
    const phyCard = buildPhysicalCard(extras.physicalEligibility);
    if (phyCard) cards.push(phyCard);

    /* 2. Exam Pattern */
    const epCard = buildExamPatternCard(extras.examPattern);
    if (epCard) cards.push(epCard);

    /* 3. Syllabus */
    const sylCard = buildSyllabusCard(extras.syllabusData);
    if (sylCard) cards.push(sylCard);

    /* 4. Salary Details (extended — base renderJobPage only shows a single string) */
    if (extras.salaryDetails) {
      /* Only render if salaryDetails has >1 field OR has 'details' with real content */
      const sdEntries = Object.entries(extras.salaryDetails).filter(([, v]) => v);
      if (sdEntries.length > 0) {
        const sdCard = buildSalaryDetailsCard(extras.salaryDetails);
        if (sdCard) cards.push(sdCard);
      }
    }

    /* 5. Important Instructions */
    const instCard = buildInstructionsCard(extras.importantInstructions);
    if (instCard) cards.push(instCard);

    /* 6. How To Apply */
    const htaCard = buildHowToApplyCard(extras.howToApply);
    if (htaCard) cards.push(htaCard);

    /* 7. AUTO-RENDER: any unknown future fields */
    for (const [k, v] of Object.entries(extras._unknownFields || {})) {
      const gc = buildGenericCard(k, v);
      if (gc) cards.push(gc);
    }

    /* 8. FAQ (always last before Important Links) */
    const faqCard = buildFaqCard(extras.faq);
    if (faqCard) cards.push(faqCard);

    /* Insert in correct order: we reverse then insert so they end up in right order */
    /* Since each insertBeforeLinks puts card RIGHT before links,
       inserting in order means each card goes after the previous.
       So we insert in FORWARD order to get correct sequence. */
    cards.forEach(card => insertBeforeLinks(card));
  }


  /* ══════════════════════════════════════════════════════════════════
     SECTION 6 — INTEGRATION HOOK
     Patches the window.__TSJ_RENDER_EXTRA hook that job.html should call.
     If job.html hasn't been updated to call it, we use MutationObserver
     as a fallback to detect when the job page finishes rendering.
  ══════════════════════════════════════════════════════════════════ */

  /**
   * PUBLIC API — job.html calls this after parseFullJob() and renderJobPage().
   * Pass both the raw JSON and the parsed row.
   *
   * Usage in job.html run() function (add these 2 lines):
   *
   *   // After: renderJobPage(name, destUrl, parsed, row);
   *   if (window.__TSJ_RENDER_EXTRA) {
   *     window.__TSJ_RENDER_EXTRA(rawJobData, row);
   *   }
   */
  window.__TSJ_RENDER_EXTRA = function (rawJobJson, parsedRow) {
    if (!rawJobJson) return;
    try {
      injectDynamicSections(rawJobJson, parsedRow);
    } catch (err) {
      console.warn('[TSJ Patch] Dynamic render error:', err);
    }
  };

  /**
   * FALLBACK: If job.html is NOT updated to call __TSJ_RENDER_EXTRA,
   * we intercept the fetch of /jobs/data/<slug>.json by patching fetch.
   * When that JSON is fetched successfully, we cache it and then wait
   * for the spinner to hide (page rendered), then inject our sections.
   */
  (function patchFetch() {
    const _origFetch = window.fetch;
    let _cachedJobJson = null;

    window.fetch = async function (...args) {
      const result = await _origFetch.apply(this, args);
      /* Check if this is a job data fetch */
      const url = (typeof args[0] === 'string') ? args[0] : (args[0] && args[0].url) || '';
      if (url && url.includes('/jobs/data/') && url.endsWith('.json')) {
        /* Clone to not consume the body */
        const clone = result.clone();
        clone.json().then(data => {
          if (data && (data.basic_details || data.title)) {
            _cachedJobJson = data;
            /* Wait for renderJobPage to complete (spinner hides, layout shows) */
            waitForRender(() => {
              if (_cachedJobJson) {
                injectDynamicSections(_cachedJobJson, null);
                _cachedJobJson = null;
              }
            });
          }
        }).catch(() => {});
      }
      return result;
    };

    /** Poll until the three-col layout is visible (render complete) */
    function waitForRender(cb) {
      let tries = 0;
      const id = setInterval(() => {
        const layout = document.getElementById('jbThreeCol');
        const loading = document.getElementById('jbLoading');
        if ((layout && layout.style.display !== 'none') ||
            (loading && loading.style.display === 'none') ||
            tries > 60) {
          clearInterval(id);
          /* Small delay to ensure DOM is fully populated by base renderer */
          setTimeout(cb, 100);
        }
        tries++;
      }, 100);
    }
  })();


  /* ══════════════════════════════════════════════════════════════════
     SECTION 7 — DYNAMIC-SECTIONS-ROW CARD FIX
     The dynamic-sections-row in index.html / view.html shows cards.
     When a card job link is clicked it goes to /jobs/<slug>/ via
     buildRedirectUrl(). The slug is generated from the job title.
     The issue: dailyupdates.json items have no individual JSON files
     at /jobs/data/<slug>.json, so the job page shows minimal data.

     FIX: If we detect we're on a job page that loaded from dailyupdates
     (no /jobs/data/ JSON found), scan the full aggregated JSON in memory
     and try to enrich the page with any matching structured data.

     This runs AFTER the base page renderer completes.
  ══════════════════════════════════════════════════════════════════ */

  /**
   * Enriches a job page that was loaded from a minimal dailyupdates.json
   * item by scanning Complete_Jobs_Full_Data.json for a matching entry.
   * Also scans merged_sarkari_data.json for offline-form jobs that have
   * how_to_apply as a plain string.
   *
   * IMPORTANT GUARDS:
   * - Only runs when NO /jobs/data/<slug>.json was found (patchFetch would
   *   have set _cachedJobJson and already called injectDynamicSections).
   * - Only runs when no dyn-card has been injected yet.
   * - Uses a HIGH similarity threshold (0.82) to prevent wrong-job matches.
   */
  async function tryEnrichFromFullData() {
    const slug = window.__TSJ_SLUG || '';
    if (!slug) return;

    /* Only run if layoutJob is visible */
    const layoutJob = document.getElementById('layoutJob');
    if (!layoutJob || layoutJob.style.display === 'none') return;

    /* GUARD: If any dyn-card already exists, enrichment already happened */
    if (document.querySelector('.dyn-card')) return;

    /* Token matching helpers */
    const STOP_WORDS = new Set([
      'the','and','for','are','was','were','has','have','had','will','can','may',
      '2024','2025','2026','2027','apply','online','offline','form','now','out',
      'notification','vacancy','vacancies','recruitment','post','posts','latest',
      'result','admit','card','answer','key','exam','date','last',
      'syllabus','merit','list','score','hall','ticket','call','letter','job','jobs',
    ]);

    function normStr(s) {
      return safe(s).toLowerCase()
        .replace(/[^\x00-\x7e]/g, ' ')
        .replace(/&/g, ' and ')
        .replace(/[^a-z0-9]+/g, ' ')
        .trim();
    }

    const slugNorm = normStr(slug.replace(/-/g, ' '));
    const tokens = slugNorm.split(/\s+/).filter(t => t.length > 3 && !STOP_WORDS.has(t));
    if (tokens.length < 2) return; /* Not enough specific tokens to match safely */

    function scoreJob(job) {
      const t = normStr(safe(
        job.title || (job.basic_details && job.basic_details.job_title) || job.post_name || ''
      ));
      if (!t) return 0;
      return tokens.filter(tk => t.includes(tk)).length / tokens.length;
    }

    let best = null, bestScore = 0;

    /* ── STEP 1: Search merged_sarkari_data.json first (offline form jobs) ── */
    /* These jobs have how_to_apply as plain strings and no /jobs/data/ files */
    try {
      const rm = await fetch('/merged_sarkari_data.json');
      if (rm.ok) {
        const mergedData = await rm.json();
        const mergedJobs = (mergedData && mergedData.jobs) ? mergedData.jobs : [];
        for (const job of mergedJobs) {
          const sc = scoreJob(job);
          if (sc > bestScore) { bestScore = sc; best = job; }
        }
      }
    } catch (_) {}

    /* ── STEP 2: If not found in merged, try Complete_Jobs_Full_Data.json ── */
    /* HIGH threshold (0.82) — requires >82% of meaningful tokens to match */
    if (!best || bestScore < 0.82) {
      try {
        const r = await fetch('/Complete_Jobs_Full_Data.json');
        if (r.ok) {
          const fullData = await r.json();
          const allJobs = [];
          if (Array.isArray(fullData)) {
            allJobs.push(...fullData);
          } else if (typeof fullData === 'object') {
            for (const val of Object.values(fullData)) {
              if (Array.isArray(val)) allJobs.push(...val);
            }
          }
          for (const job of allJobs) {
            const sc = scoreJob(job);
            if (sc > bestScore) { bestScore = sc; best = job; }
          }
        }
      } catch (_) {}
    }

    /* Inject only if score meets threshold */
    if (best && bestScore >= 0.82) {
      injectDynamicSections(best, null);
    }
  }

  /* Run enrichment after page renders */
  (function scheduleEnrichment() {
    let tries = 0;
    const id = setInterval(() => {
      const layout   = document.getElementById('jbThreeCol');
      const loading  = document.getElementById('jbLoading');
      const rendered = layout && layout.style.display !== 'none';
      const done     = loading && loading.style.display === 'none';
      if (rendered || done || tries > 80) {
        clearInterval(id);
        setTimeout(tryEnrichFromFullData, 200);
      }
      tries++;
    }, 100);
  })();

})();
