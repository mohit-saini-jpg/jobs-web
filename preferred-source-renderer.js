/**
 * ══════════════════════════════════════════════════════════════════════
 *  TOP SARKARI JOBS — Set as Preferred Source on Google
 *  Full Rich Details Block Renderer
 *  Version: 2026-05-27
 * ══════════════════════════════════════════════════════════════════════
 */
(function () {
  'use strict';

  /* ── CSS ─────────────────────────────────────────────────────────── */
  const CSS_ID = 'tsj-psr-styles';
  if (!document.getElementById(CSS_ID)) {
    const s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent = `
    /* ── PSR Card Shell ── */
    .psr-card{background:#fff;border:1.5px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.06);}
    .psr-head{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;background:linear-gradient(135deg,#7c3aed,#4f46e5);color:#fff;font-size:.9rem;font-weight:800;gap:8px;}
    .psr-head-left{display:flex;align-items:center;gap:8px;font-size:.9rem;}
    .psr-head-right{font-size:.7rem;font-weight:600;background:rgba(255,255,255,.18);padding:3px 10px;border-radius:20px;white-space:nowrap;}
    .psr-subhead{background:linear-gradient(90deg,#fbbf24,#f59e0b);color:#1c1917;font-size:.72rem;font-weight:800;text-align:center;padding:5px 12px;letter-spacing:.06em;text-transform:uppercase;}
    .psr-section-label{font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#fff;padding:5px 14px;display:flex;align-items:center;gap:6px;}
    /* ── Dual-column tables (Basic Info + Important Info) ── */
    .psr-dual{display:grid;grid-template-columns:1fr 1fr;gap:0;}
    @media(max-width:640px){.psr-dual{grid-template-columns:1fr;}}
    .psr-dual-col{}
    .psr-dual-col:first-child{border-right:1px solid #e2e8f0;}
    .psr-dual-label{font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;padding:6px 12px;display:flex;align-items:center;gap:5px;}
    .psr-table{width:100%;border-collapse:collapse;}
    .psr-table th{background:#f8fafc;color:#374151;font-weight:700;font-size:.76rem;padding:7px 12px;text-align:left;border-bottom:1px solid #e9eef4;white-space:nowrap;width:42%;}
    .psr-table td{padding:7px 12px;color:#1e293b;font-size:.79rem;border-bottom:1px solid #e9eef4;line-height:1.5;word-break:break-word;}
    .psr-table tr:last-child th,.psr-table tr:last-child td{border-bottom:none;}
    .psr-table td a{color:#1d4ed8;text-decoration:none;font-weight:600;}
    .psr-table td a:hover{text-decoration:underline;}
    /* ── Tri-col sections (Eligibility/Fee/Links) ── */
    .psr-tri{display:grid;grid-template-columns:1fr 1fr 1fr;border-top:1px solid #e2e8f0;}
    @media(max-width:700px){.psr-tri{grid-template-columns:1fr;}}
    .psr-tri-col{padding:0;}
    .psr-tri-col:not(:last-child){border-right:1px solid #e2e8f0;}
    @media(max-width:700px){.psr-tri-col:not(:last-child){border-right:none;border-bottom:1px solid #e2e8f0;}}
    .psr-tri-head{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;padding:6px 12px;display:flex;align-items:center;gap:5px;}
    .psr-tri-body{padding:8px 12px;font-size:.78rem;color:#1e293b;line-height:1.7;}
    /* ── Link buttons inside psr ── */
    .psr-link-btn{display:inline-flex;align-items:center;gap:5px;font-size:.73rem;font-weight:700;padding:4px 10px;border-radius:6px;text-decoration:none;white-space:nowrap;margin:2px 3px 2px 0;transition:all .15s;}
    .psr-link-green{background:#d1fae5;color:#065f46;border:1px solid #6ee7b7;}
    .psr-link-green:hover{background:#059669;color:#fff;}
    .psr-link-blue{background:#dbeafe;color:#1e40af;border:1px solid #93c5fd;}
    .psr-link-blue:hover{background:#1e40af;color:#fff;}
    .psr-link-red{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;}
    .psr-link-red:hover{background:#dc2626;color:#fff;}
    .psr-link-orange{background:#fef3c7;color:#92400e;border:1px solid #fcd34d;}
    .psr-link-orange:hover{background:#d97706;color:#fff;}
    .psr-link-purple{background:#ede9fe;color:#5b21b6;border:1px solid #c4b5fd;}
    .psr-link-purple:hover{background:#6d28d9;color:#fff;}
    /* ── 3-table row: dates / vacancy / category-wise ── */
    .psr-triple{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;border-top:1px solid #e2e8f0;}
    @media(max-width:700px){.psr-triple{grid-template-columns:1fr;}}
    .psr-triple-col{padding:0;}
    .psr-triple-col:not(:last-child){border-right:1px solid #e2e8f0;}
    @media(max-width:700px){.psr-triple-col:not(:last-child){border-right:none;border-bottom:1px solid #e2e8f0;}}
    .psr-mini-table{width:100%;border-collapse:collapse;font-size:.76rem;}
    .psr-mini-table th{background:#f0f9ff;color:#1d4ed8;padding:5px 10px;text-align:left;border-bottom:1px solid #e2e8f0;font-weight:700;white-space:nowrap;}
    .psr-mini-table td{padding:5px 10px;border-bottom:1px solid #f1f5f9;color:#1e293b;}
    .psr-mini-table td:last-child,.psr-mini-table th:last-child{text-align:right;}
    .psr-mini-table tr:last-child td{border-bottom:none;font-weight:700;background:#f8fafc;}
    .psr-date-red{color:#dc2626;font-weight:700;}
    /* ── Selection + Docs 2-col ── */
    .psr-two{display:grid;grid-template-columns:1fr 1fr;gap:0;border-top:1px solid #e2e8f0;}
    @media(max-width:640px){.psr-two{grid-template-columns:1fr;}}
    .psr-two-col:first-child{border-right:1px solid #e2e8f0;}
    @media(max-width:640px){.psr-two-col:first-child{border-right:none;border-bottom:1px solid #e2e8f0;}}
    .psr-step-list{list-style:none;margin:0;padding:0;}
    .psr-step{display:flex;align-items:flex-start;gap:8px;padding:6px 12px;border-bottom:1px solid #f1f5f9;font-size:.78rem;color:#1e293b;line-height:1.55;}
    .psr-step:last-child{border-bottom:none;}
    .psr-step-num{flex-shrink:0;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.65rem;font-weight:800;color:#fff;margin-top:1px;}
    .psr-step-num-blue{background:#1d4ed8;}
    .psr-step-num-green{background:#059669;}
    .psr-doc-item{display:flex;align-items:flex-start;gap:7px;padding:5px 12px;border-bottom:1px solid #f1f5f9;font-size:.78rem;color:#374151;line-height:1.5;}
    .psr-doc-item:last-child{border-bottom:none;}
    /* ── How To Apply + Exam Pattern + Syllabus triple ── */
    .psr-hte{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;border-top:1px solid #e2e8f0;}
    @media(max-width:700px){.psr-hte{grid-template-columns:1fr;}}
    .psr-hte-col:not(:last-child){border-right:1px solid #e2e8f0;}
    @media(max-width:700px){.psr-hte-col:not(:last-child){border-right:none;border-bottom:1px solid #e2e8f0;}}
    .psr-hte-body{padding:8px 12px;font-size:.76rem;color:#1e293b;line-height:1.65;}
    .psr-ep-table{width:100%;border-collapse:collapse;font-size:.74rem;}
    .psr-ep-table th{background:#fef3c7;color:#92400e;padding:5px 8px;text-align:left;border-bottom:1px solid #fde68a;font-weight:700;}
    .psr-ep-table td{padding:5px 8px;border-bottom:1px solid #f1f5f9;color:#1e293b;}
    .psr-syl-list{list-style:none;padding:0;margin:0;}
    .psr-syl-item{padding:4px 12px;border-bottom:1px solid #f1f5f9;font-size:.77rem;color:#374151;}
    .psr-syl-item:last-child{border-bottom:none;}
    .psr-syl-item::before{content:"• ";color:#7c3aed;font-weight:700;}
    /* ── FAQ + Related + Tags 3-col ── */
    .psr-frt{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;border-top:1px solid #e2e8f0;}
    @media(max-width:700px){.psr-frt{grid-template-columns:1fr;}}
    .psr-frt-col:not(:last-child){border-right:1px solid #e2e8f0;}
    @media(max-width:700px){.psr-frt-col:not(:last-child){border-right:none;border-bottom:1px solid #e2e8f0;}}
    .psr-faq-item{border-bottom:1px solid #f1f5f9;}
    .psr-faq-item:last-child{border-bottom:none;}
    .psr-faq-q{padding:7px 12px;font-size:.75rem;font-weight:700;color:#1e293b;cursor:pointer;background:#f8fafc;border:none;width:100%;text-align:left;line-height:1.45;}
    .psr-faq-q:hover{background:#eff6ff;color:#1d4ed8;}
    .psr-faq-a{display:none;padding:5px 12px 8px;font-size:.74rem;color:#374151;line-height:1.65;background:#fff;}
    .psr-faq-a.open{display:block;}
    .psr-related-list{list-style:none;margin:0;padding:0;}
    .psr-related-item{border-bottom:1px solid #f1f5f9;}
    .psr-related-item:last-child{border-bottom:none;}
    .psr-related-item a{display:block;padding:6px 12px;font-size:.77rem;color:#1d4ed8;text-decoration:none;line-height:1.45;}
    .psr-related-item a:hover{background:#eff6ff;}
    .psr-related-item a i{font-size:.6rem;margin-right:4px;color:#6b7280;}
    .psr-tag-wrap{padding:10px 12px;display:flex;flex-wrap:wrap;gap:5px;}
    .psr-tag{background:#f0f7ff;border:1px solid #bfdbfe;color:#1e40af;padding:3px 10px;border-radius:20px;font-size:.72rem;font-weight:600;}
    /* ── Non-job specific ── */
    .psr-nj-info-table .psr-table th{background:#fdf4ff;}
    /* ── Badge ── */
    .psr-mode-badge{display:inline-block;padding:2px 9px;border-radius:10px;font-size:.72rem;font-weight:700;}
    .psr-badge-online{background:#d1fae5;color:#065f46;}
    .psr-badge-offline{background:#fef3c7;color:#92400e;}
    .psr-badge-walkin{background:#e0e7ff;color:#3730a3;}
    .psr-badge-download{background:#e0f2fe;color:#0369a1;}
    /* ── Responsive tweaks ── */
    @media(max-width:480px){
      .psr-table th,.psr-table td,.psr-mini-table th,.psr-mini-table td{padding:5px 8px;font-size:.72rem;}
      .psr-tri-body,.psr-hte-body{padding:6px 8px;}
      .psr-step,.psr-doc-item{padding:5px 8px;}
      .psr-tag-wrap{padding:7px 8px;}
    }
    `;
    document.head.appendChild(s);
  }

  /* ── Helpers ─────────────────────────────────────────────────────── */
  function safe(v) { return (v == null ? '' : String(v)).trim(); }
  function hasVal(v) { const s = safe(v); return s && s !== '—' && s !== '-' && s !== 'N/A'; }
  function arr(v) { return Array.isArray(v) ? v : (v ? [v] : []); }
  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }
  function fmtDate(raw) {
    if (!raw) return '';
    const s = safe(raw);
    // ISO: 2026-06-10 → 10/06/2026
    let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return m[3]+'/'+m[2]+'/'+m[1];
    // DD-MM-YYYY
    m = s.match(/^(\d{2})[\/\-](\d{2})[\/\-](\d{4})/);
    if (m) return m[1]+'/'+m[2]+'/'+m[3];
    return s.slice(0, 20);
  }
  function sectionHead(icon, label, color, rightText) {
    const d = el('div', 'psr-section-label');
    d.style.background = color || '#1d4ed8';
    d.innerHTML = `<i class="fa-solid ${icon}"></i> ${label}`;
    return d;
  }

  /* ── Extract row data intelligently ─────────────────────────────── */
  function extractJobData(raw, row) {
    const j = raw || {};
    const dates = j.important_dates || j.dates || {};
    const fee   = j.application_fees || j.application_fee || {};
    const bd    = j.basic_details || {};
    const il    = j.important_links || {};
    const vd    = j.vacancy_details || [];
    const cwv   = j.category_wise_vacancy || {};

    function fv(/* fields */) {
      for (let i = 0; i < arguments.length; i++) {
        const v = safe(j[arguments[i]] || bd[arguments[i]] || row?.[arguments[i]] || '');
        if (v) return v;
      }
      return '';
    }

    // Basic
    const title    = fv('title','post_name','job_title','name') || safe(row?.title || '');
    const org      = fv('organization','board_name','department','org') || safe(row?.org || '');
    const dept     = fv('department','board_name');
    const postName = fv('post_name','post_names');
    const totalVac = fv('total_vacancy','total_vacancies','total_post') || safe(row?.totalVac || '');
    const salary   = fv('salary','salary_pay_scale','pay_scale') || safe(row?.salary || '');
    const applyMode= fv('apply_mode','application_mode') || safe(row?.applyMode || 'Online');
    const jobLoc   = fv('job_location','location') || safe(row?.jobLocation || 'All India');
    const category = fv('category','job_type') || safe(row?.category || '');
    const minAge   = fv('minimum_age') || safe(row?.minAge || '');
    const maxAge   = fv('maximum_age') || safe(row?.maxAge || '');
    const ageRelax = fv('age_relaxation') || safe(row?.ageRelax || '');
    const eduQual  = fv('education_qualification','eligibility','qualification') || safe(row?.eduQual || '');
    const shortInfo= fv('short_information','jobs_info') || safe(row?.shortInfo || '');
    const howToApply= fv('how_to_apply') || '';
    const selProc  = j.selection_process || bd.selection_process || row?.selProc || '';
    const examPat  = j.exam_pattern || j.examination_pattern || null;
    const syllabus = j.syllabus || j.syllabus_details || null;
    const faq      = j.faq || j.faqs || null;
    const reqDocs  = j.required_documents || j.documents_required || null;
    const tags     = j.tags || j.keywords || null;

    // Dates
    const appBegin = fmtDate(dates.application_begin || dates.application_start || dates.start_date || row?.appBegin || '');
    const lastDate = fmtDate(dates.last_date || dates.last_date_to_apply || row?.lastDate || j.last_date || '');
    const feeDate  = fmtDate(dates.last_date_fee_pay || dates.fee_last_date || row?.feeLastDate || '');
    const examDate = fmtDate(dates.exam_date || dates.examination_date || row?.examDate || '');
    const admitDate= fmtDate(dates.admit_card_date || dates.admit_card || row?.admitDate || '');
    const resultDate=fmtDate(dates.result_date || row?.resultDate || '');
    const corrDate = fmtDate(dates.correction_date || dates.correction_last_date || row?.corrDate || '');

    // Fee
    const feeItems = [];
    if (fee && typeof fee === 'object') {
      const feeMap = {
        general_obc_ews: 'General / OBC / EWS', sc_st: 'SC / ST',
        general: 'General', obc: 'OBC', ews: 'EWS', sc: 'SC', st: 'ST',
        female: 'Female / Women', ph: 'PH / PwD', others: 'Others',
        all: 'For All', payment_mode: null, mode: null, pay_mode: null
      };
      for (const [k, label] of Object.entries(feeMap)) {
        if (!label) continue;
        const v = safe(fee[k] || '');
        if (v) feeItems.push([label, v]);
      }
    } else if (row?.feeItems) {
      feeItems.push(...row.feeItems);
    }
    const payMode = safe(fee.payment_mode || fee.mode || row?.payMode || 'Online');

    // Links
    function bestUrl(/* keys */) {
      for (let i = 0; i < arguments.length; i++) {
        const v = safe(j[arguments[i]] || il[arguments[i]] || '');
        if (v && v.startsWith('http')) return v;
      }
      return '';
    }
    const applyUrl   = bestUrl('apply_online_link','apply_online','apply_link') || safe(row?.applyOnline || '');
    const notifUrl   = bestUrl('official_notification_pdf_link','official_notification','notification_pdf') || safe(row?.notifPdf || '');
    const websiteUrl = bestUrl('official_website_link','official_website') || safe(row?.officialWebsite || row?.officialWebsiteLink || '');
    const admitUrl   = bestUrl('admit_card') || safe(row?.admitCard || '');
    const resultUrl  = bestUrl('result') || safe(row?.result || '');
    const answerUrl  = bestUrl('answer_key') || safe(row?.answerKey || '');
    const syllUrl    = bestUrl('syllabus','syllabus_pdf') || safe(row?.syllabus || '');
    const formPdf    = bestUrl('form_pdf_free_link','application_form_pdf_link') || safe(row?.formPdfFreeLink || '');

    // Vacancy details
    const vacRows = Array.isArray(vd) ? vd : [];
    const cwRows = [];
    if (hasVal(cwv.general || cwv.ur)) cwRows.push(['General/UR', cwv.general || cwv.ur]);
    if (hasVal(cwv.obc))  cwRows.push(['OBC', cwv.obc]);
    if (hasVal(cwv.ews))  cwRows.push(['EWS', cwv.ews]);
    if (hasVal(cwv.sc))   cwRows.push(['SC',  cwv.sc]);
    if (hasVal(cwv.st))   cwRows.push(['ST',  cwv.st]);
    if (hasVal(cwv.ph))   cwRows.push(['PH/PwD', cwv.ph]);
    // Also check row cw
    if (!cwRows.length && row) {
      if (hasVal(row.cwVacGen)) cwRows.push(['General/UR', row.cwVacGen]);
      if (hasVal(row.cwVacObc)) cwRows.push(['OBC', row.cwVacObc]);
      if (hasVal(row.cwVacEws)) cwRows.push(['EWS', row.cwVacEws]);
      if (hasVal(row.cwVacSc))  cwRows.push(['SC',  row.cwVacSc]);
      if (hasVal(row.cwVacSt))  cwRows.push(['ST',  row.cwVacSt]);
      if (hasVal(row.cwVacPh))  cwRows.push(['PH/PwD', row.cwVacPh]);
    }

    // Useful links from row
    const usefulLinks = (row && row.usefulLinks) || [];

    return {
      title, org, dept, postName, totalVac, salary, applyMode, jobLoc, category,
      minAge, maxAge, ageRelax, eduQual, shortInfo, howToApply, selProc,
      examPat, syllabus, faq, reqDocs, tags,
      appBegin, lastDate, feeDate, examDate, admitDate, resultDate, corrDate,
      feeItems, payMode,
      applyUrl, notifUrl, websiteUrl, admitUrl, resultUrl, answerUrl, syllUrl, formPdf,
      vacRows, cwRows, usefulLinks
    };
  }

  /* ── Build Job Preferred Source Card ──────────────────────────── */
  function buildJobCard(raw, row, name) {
    const d = extractJobData(raw, row);
    const titleText = name || d.title;
    if (!titleText) return null;

    const card = el('div', 'psr-card');

    /* ── Header ── */
    const head = el('div', 'psr-head');
    head.innerHTML = `
      <div class="psr-head-left"><i class="fa-brands fa-google" style="font-size:1rem;"></i> Set as Preferred Source on Google</div>
      <div class="psr-head-right">⭐ YAHAN PAR FULL DETAILS SHOW HOGI</div>`;
    card.appendChild(head);

    /* ── Subhead ── */
    card.appendChild(el('div', 'psr-subhead', '⭐ YAHAN PAR FULL DETAILS SHOW HOGI'));

    /* ── SECTION 1: Dual table — Basic Info + Important Info ── */
    const basicRows = [];
    if (hasVal(d.org)) basicRows.push(['Job Name', titleText.replace(/\s*[-–]\s*$/, '')]);
    if (hasVal(d.org)) basicRows.push(['Department', d.org]);
    if (hasVal(d.postName)) basicRows.push(['Post Name', d.postName]);
    if (hasVal(d.totalVac)) basicRows.push(['Total Posts', d.totalVac]);
    if (hasVal(d.category)) basicRows.push(['Category', d.category.includes('Jobs') ? d.category : 'Central Government Jobs']);
    if (hasVal(d.jobLoc)) basicRows.push(['State', d.jobLoc]);
    const modeVal = (() => {
      const m = safe(d.applyMode).toLowerCase();
      const cls = m.includes('offline') ? 'psr-badge-offline' : m.includes('walk') ? 'psr-badge-walkin' : 'psr-badge-online';
      return `<span class="psr-mode-badge ${cls}">${safe(d.applyMode) || 'Online'}</span>`;
    })();
    basicRows.push(['Application Mode', modeVal]);
    if (d.shortInfo && d.shortInfo.length > 10) {
      basicRows.push(['Short Information', d.shortInfo.slice(0, 200) + (d.shortInfo.length > 200 ? '...' : '')]);
    }

    const importantRows = [];
    if (hasVal(d.appBegin)) importantRows.push(['Application Start', d.appBegin]);
    if (hasVal(d.lastDate)) importantRows.push([`<span style="color:#dc2626;font-weight:800;">Last Date to Apply</span>`, `<span class="psr-date-red">${d.lastDate}</span>`]);
    if (hasVal(d.feeDate))  importantRows.push(['Last Date Fee Pay', d.feeDate]);
    if (hasVal(d.examDate)) importantRows.push(['Exam Date', d.examDate]);
    if (hasVal(d.admitDate))importantRows.push(['Admit Card', d.admitDate]);
    if (hasVal(d.resultDate))importantRows.push(['Result Date', d.resultDate]);
    if (hasVal(d.jobLoc))  importantRows.push(['Job Location', d.jobLoc]);

    if (basicRows.length || importantRows.length) {
      const dual = el('div', 'psr-dual');

      if (basicRows.length) {
        const col = el('div', 'psr-dual-col');
        const lbl = el('div', 'psr-dual-label');
        lbl.style.background = '#1d4ed8'; lbl.style.color = '#fff';
        lbl.innerHTML = '<i class="fa-solid fa-circle-info"></i> Basic Information';
        col.appendChild(lbl);
        const t = el('table', 'psr-table');
        t.innerHTML = basicRows.map(([k,v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('');
        col.appendChild(t);
        dual.appendChild(col);
      }

      if (importantRows.length) {
        const col = el('div', 'psr-dual-col');
        const lbl = el('div', 'psr-dual-label');
        lbl.style.background = '#dc2626'; lbl.style.color = '#fff';
        lbl.innerHTML = '<i class="fa-solid fa-calendar-check"></i> Important Information';
        col.appendChild(lbl);
        const t = el('table', 'psr-table');
        t.innerHTML = importantRows.map(([k,v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('');
        col.appendChild(t);
        dual.appendChild(col);
      }
      card.appendChild(dual);
    }

    /* ── SECTION 2: Tri-col — Eligibility + Fee + Important Links ── */
    const hasElig = hasVal(d.eduQual) || hasVal(d.minAge) || hasVal(d.maxAge);
    const hasFee  = d.feeItems.length > 0;
    const hasLinks= hasVal(d.applyUrl) || hasVal(d.notifUrl) || hasVal(d.websiteUrl) || hasVal(d.admitUrl) || hasVal(d.resultUrl) || hasVal(d.answerUrl) || hasVal(d.syllUrl) || hasVal(d.formPdf) || d.usefulLinks.length;

    if (hasElig || hasFee || hasLinks) {
      const tri = el('div', 'psr-tri');

      // Eligibility col
      const ec = el('div', 'psr-tri-col');
      const eh = el('div', 'psr-tri-head');
      eh.style.background = '#4338ca'; eh.style.color = '#fff';
      eh.innerHTML = '<i class="fa-solid fa-graduation-cap"></i> Eligibility Details';
      ec.appendChild(eh);
      const eb = el('div', 'psr-tri-body');
      if (hasVal(d.eduQual)) eb.innerHTML += `<div style="margin-bottom:5px;"><strong>Education:</strong> ${safe(d.eduQual).slice(0,160)}</div>`;
      if (hasVal(d.minAge) || hasVal(d.maxAge)) {
        eb.innerHTML += `<div><strong>Age Limit:</strong> ${[hasVal(d.minAge) ? 'Min: '+d.minAge : '', hasVal(d.maxAge) ? 'Max: '+d.maxAge : ''].filter(Boolean).join(', ')}</div>`;
        if (hasVal(d.ageRelax)) eb.innerHTML += `<div style="margin-top:3px;"><strong>Age Relaxation:</strong> ${d.ageRelax.slice(0,80)}</div>`;
      }
      if (!ec.textContent.trim()) eb.innerHTML = '<span style="color:#64748b;font-size:.75rem;">Check Notification</span>';
      ec.appendChild(eb);
      tri.appendChild(ec);

      // Fee col
      const fc = el('div', 'psr-tri-col');
      const fh = el('div', 'psr-tri-head');
      fh.style.background = '#be185d'; fh.style.color = '#fff';
      fh.innerHTML = '<i class="fa-solid fa-indian-rupee-sign"></i> Application Fee';
      fc.appendChild(fh);
      const fb = el('div', 'psr-tri-body');
      if (hasFee) {
        fb.innerHTML = d.feeItems.map(([cat, amt]) => `<div style="margin-bottom:3px;"><strong>${cat}:</strong> ${amt}</div>`).join('');
        if (hasVal(d.payMode)) fb.innerHTML += `<div style="margin-top:5px;color:#64748b;font-size:.72rem;"><strong>Payment:</strong> ${d.payMode.slice(0,50)}</div>`;
      } else {
        fb.innerHTML = '<span style="color:#059669;font-weight:700;">No Fee / Free</span>';
      }
      fc.appendChild(fb);
      tri.appendChild(fc);

      // Links col
      const lc = el('div', 'psr-tri-col');
      const lh = el('div', 'psr-tri-head');
      lh.style.background = '#0f766e'; lh.style.color = '#fff';
      lh.innerHTML = '<i class="fa-solid fa-link"></i> Important Links';
      lc.appendChild(lh);
      const lb = el('div', 'psr-tri-body');
      const linkDefs = [
        { url: d.notifUrl,  label: 'Notification PDF', cls: 'psr-link-blue',   icon: 'fa-file-pdf' },
        { url: d.applyUrl,  label: 'Apply Online',     cls: 'psr-link-green',  icon: 'fa-pen-to-square' },
        { url: d.websiteUrl,label: 'Official Website', cls: 'psr-link-red',    icon: 'fa-globe' },
        { url: d.admitUrl,  label: 'Admit Card',       cls: 'psr-link-orange', icon: 'fa-id-card' },
        { url: d.resultUrl, label: 'Result',           cls: 'psr-link-orange', icon: 'fa-trophy' },
        { url: d.answerUrl, label: 'Answer Key',       cls: 'psr-link-blue',   icon: 'fa-key' },
        { url: d.syllUrl,   label: 'Syllabus',         cls: 'psr-link-purple', icon: 'fa-book-open' },
        { url: d.formPdf,   label: 'Download Form',    cls: 'psr-link-blue',   icon: 'fa-file-arrow-down' },
      ];
      let linkHtml = '';
      const seenUrls = new Set();
      for (const lk of linkDefs) {
        if (!hasVal(lk.url) || seenUrls.has(lk.url)) continue;
        seenUrls.add(lk.url);
        linkHtml += `<a href="${lk.url}" target="_blank" rel="noopener" class="psr-link-btn ${lk.cls}"><i class="fa-solid ${lk.icon}"></i> ${lk.label}</a>`;
      }
      // useful_links
      for (const ul of d.usefulLinks.slice(0, 6)) {
        const rawLinks = ul.links || ul.url || ul.href || '';
        const urls = Array.isArray(rawLinks) ? rawLinks : [rawLinks];
        for (const u of urls) {
          const hu = safe(u);
          if (!hu || !hu.startsWith('http') || seenUrls.has(hu)) continue;
          seenUrls.add(hu);
          const t = safe(ul.title || ul.name || 'Link').slice(0,35);
          linkHtml += `<a href="${hu}" target="_blank" rel="noopener" class="psr-link-btn psr-link-blue"><i class="fa-solid fa-arrow-up-right-from-square"></i> ${t}</a>`;
        }
      }
      if (!linkHtml) linkHtml = '<span style="color:#64748b;font-size:.75rem;">Check official website</span>';
      lb.innerHTML = linkHtml;
      lc.appendChild(lb);
      tri.appendChild(lc);

      card.appendChild(tri);
    }

    /* ── SECTION 3: Triple tables — Dates + Vacancy + Category-wise ── */
    const hasMoreDates = hasVal(d.appBegin) || hasVal(d.lastDate) || hasVal(d.examDate);
    const hasVac = d.vacRows.length > 0;
    const hasCw  = d.cwRows.length > 0;

    if (hasMoreDates || hasVac || hasCw) {
      const triple = el('div', 'psr-triple');

      // Dates col
      if (hasMoreDates) {
        const dc = el('div', 'psr-triple-col');
        const dh = el('div', 'psr-tri-head');
        dh.style.background = '#b91c1c'; dh.style.color = '#fff';
        dh.innerHTML = '<i class="fa-solid fa-calendar-days"></i> Important Dates';
        dc.appendChild(dh);
        const dateRowsArr = [
          ['Start Date',       d.appBegin],
          ['Last Date',        d.lastDate,  true],
          ['Fee Last Date',    d.feeDate],
          ['Admit Card',       d.admitDate],
          ['Exam Date',        d.examDate],
          ['Result Date',      d.resultDate],
          ['Correction',       d.corrDate],
        ].filter(([,v]) => hasVal(v));
        const dt = el('table', 'psr-mini-table');
        dt.innerHTML = `<thead><tr><th>Event</th><th>Date</th></tr></thead><tbody>${
          dateRowsArr.map(([k,v,red]) => `<tr><td>${k}</td><td ${red?'class="psr-date-red"':''}>${v}</td></tr>`).join('')
        }</tbody>`;
        dc.appendChild(dt);
        triple.appendChild(dc);
      }

      // Vacancy Details col
      if (hasVac) {
        const vc = el('div', 'psr-triple-col');
        const vh = el('div', 'psr-tri-head');
        vh.style.background = '#15803d'; vh.style.color = '#fff';
        vh.innerHTML = '<i class="fa-solid fa-users"></i> Vacancy Details (Post Wise)';
        vc.appendChild(vh);
        const colKeys = ['post_name','total','eligibility'];
        const colLabels = {post_name:'Post Name',total:'Total',eligibility:'Qualification'};
        const usedCols = colKeys.filter(k => d.vacRows.some(r => hasVal(r[k])));
        if (!usedCols.length) usedCols.push('post_name','total');
        const vt = el('table', 'psr-mini-table');
        vt.innerHTML = `<thead><tr>${usedCols.map(k=>`<th>${colLabels[k]||k}</th>`).join('')}</tr></thead><tbody>${
          d.vacRows.map(r => `<tr>${usedCols.map(k=>`<td>${safe(r[k])}</td>`).join('')}</tr>`).join('')
        }</tbody>`;
        vc.appendChild(vt);
        triple.appendChild(vc);
      } else if (hasCw) {
        const vc = el('div', 'psr-triple-col');
        const vh = el('div', 'psr-tri-head');
        vh.style.background = '#15803d'; vh.style.color = '#fff';
        vh.innerHTML = '<i class="fa-solid fa-users"></i> Vacancy Details';
        vc.appendChild(vh);
        const vt = el('table', 'psr-mini-table');
        vt.innerHTML = `<thead><tr><th>Post Name</th><th>Total Posts</th></tr></thead><tbody>${
          [['Total', d.totalVac || 'Various']].map(([k,v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('')
        }</tbody>`;
        vc.appendChild(vt);
        triple.appendChild(vc);
      }

      // Category-wise col
      if (hasCw) {
        const cc = el('div', 'psr-triple-col');
        const ch = el('div', 'psr-tri-head');
        ch.style.background = '#0369a1'; ch.style.color = '#fff';
        ch.innerHTML = '<i class="fa-solid fa-chart-pie"></i> Category Wise Details';
        cc.appendChild(ch);
        const ct = el('table', 'psr-mini-table');
        const totalCw = d.cwRows.reduce((s,[,v]) => s + (parseInt(v)||0), 0);
        ct.innerHTML = `<thead><tr><th>Category</th><th>Total Posts</th></tr></thead><tbody>${
          d.cwRows.map(([k,v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('')
        }${totalCw ? `<tr><td><strong>Total</strong></td><td><strong>${totalCw}</strong></td></tr>` : ''}</tbody>`;
        cc.appendChild(ct);
        triple.appendChild(cc);
      }

      if (triple.children.length) card.appendChild(triple);
    }

    /* ── SECTION 4: Selection Process + Required Documents ── */
    const selSteps = (() => {
      const sp = d.selProc;
      if (Array.isArray(sp)) return sp;
      if (typeof sp === 'string' && sp.length > 2) return sp.split(/[,;\n\/]/).map(s=>s.trim()).filter(Boolean);
      return [];
    })();
    const docList = (() => {
      if (!d.reqDocs) return [];
      if (Array.isArray(d.reqDocs)) return d.reqDocs;
      if (typeof d.reqDocs === 'string') return d.reqDocs.split(/[,;\n]/).map(s=>s.trim()).filter(Boolean);
      return [];
    })();

    if (selSteps.length || docList.length) {
      const two = el('div', 'psr-two');

      if (selSteps.length) {
        const sc = el('div', 'psr-two-col');
        const sh = el('div', 'psr-tri-head');
        sh.style.background = '#5b21b6'; sh.style.color = '#fff';
        sh.innerHTML = '<i class="fa-solid fa-list-check"></i> Selection Process';
        sc.appendChild(sh);
        // Also try to extract stages
        const sb = el('div');
        const ul = el('ul', 'psr-step-list');
        selSteps.slice(0,6).forEach((step, i) => {
          const li = el('li', 'psr-step');
          const num = el('span', 'psr-step-num psr-step-num-blue', `${i+1}`);
          const txt = el('span', '', safe(step).slice(0,80));
          li.appendChild(num); li.appendChild(txt);
          ul.appendChild(li);
        });
        sb.appendChild(ul);
        // Try 4-stage process
        const stageKeys = ['Stage 1', 'Stage 2', 'Stage 3', 'Stage 4'];
        if (selSteps.length >= 4 && selSteps.some(s => /stage|written|trade|document|medical/i.test(s))) {
          const sb2 = el('div');
          const ul2 = el('ul', 'psr-step-list');
          selSteps.slice(0,4).forEach((step, i) => {
            const li = el('li', 'psr-step');
            li.innerHTML = `<span class="psr-step-num psr-step-num-blue">${i+1}</span><span>Stage ${i+1}: ${safe(step).slice(0,60)}</span>`;
            ul2.appendChild(li);
          });
          sb.innerHTML = ''; sb.appendChild(ul2);
        }
        sc.appendChild(sb);
        two.appendChild(sc);
      }

      if (docList.length) {
        const dc = el('div', 'psr-two-col');
        const dh = el('div', 'psr-tri-head');
        dh.style.background = '#b45309'; dh.style.color = '#fff';
        dh.innerHTML = '<i class="fa-solid fa-file-lines"></i> Required Documents';
        dc.appendChild(dh);
        const db = el('div');
        docList.slice(0,8).forEach((doc, i) => {
          const item = el('div', 'psr-doc-item');
          item.innerHTML = `<span class="psr-step-num psr-step-num-green" style="font-size:.6rem;">${i+1}</span><span>${safe(doc).slice(0,80)}</span>`;
          db.appendChild(item);
        });
        dc.appendChild(db);
        two.appendChild(dc);
      }

      if (two.children.length) card.appendChild(two);
    }

    /* ── SECTION 5: How To Apply + Exam Pattern + Syllabus ── */
    const htaText = safe(d.howToApply).slice(0, 600);
    const hasHta  = htaText.length > 10;
    const hasEp   = !!d.examPat;
    const hasSyl  = !!d.syllabus;

    if (hasHta || hasEp || hasSyl) {
      const hte = el('div', 'psr-hte');

      if (hasHta) {
        const hc = el('div', 'psr-hte-col');
        const hh = el('div', 'psr-tri-head');
        hh.style.background = '#0f766e'; hh.style.color = '#fff';
        hh.innerHTML = '<i class="fa-solid fa-list-ol"></i> How To Apply';
        hc.appendChild(hh);
        const hb = el('div', 'psr-hte-body');
        // Try to split into numbered steps
        const steps = htaText.split(/\n/).filter(s => s.trim().length > 5).slice(0, 6);
        if (steps.length > 1) {
          const ul = el('ul', 'psr-step-list');
          steps.forEach((step, i) => {
            const li = el('li', 'psr-step');
            li.innerHTML = `<span class="psr-step-num psr-step-num-green">${i+1}</span><span>${step.replace(/^\d+[\.\)]\s*/,'').slice(0,100)}</span>`;
            ul.appendChild(li);
          });
          hb.appendChild(ul);
        } else {
          hb.textContent = htaText.slice(0, 400);
        }
        hc.appendChild(hb);
        hte.appendChild(hc);
      }

      if (hasEp) {
        const ec = el('div', 'psr-hte-col');
        const eh = el('div', 'psr-tri-head');
        eh.style.background = '#b45309'; eh.style.color = '#fff';
        eh.innerHTML = '<i class="fa-solid fa-table-list"></i> Exam Pattern';
        ec.appendChild(eh);
        const eb = el('div', 'psr-hte-body');
        if (Array.isArray(d.examPat) && d.examPat.length > 0 && typeof d.examPat[0] === 'object') {
          const t = el('table', 'psr-ep-table');
          const cols = Object.keys(d.examPat[0]);
          t.innerHTML = `<thead><tr>${cols.map(c=>`<th>${c}</th>`).join('')}</tr></thead><tbody>${
            d.examPat.map(r=>`<tr>${cols.map(c=>`<td>${safe(r[c])}</td>`).join('')}</tr>`).join('')
          }</tbody>`;
          eb.appendChild(t);
        } else if (typeof d.examPat === 'string') {
          eb.textContent = d.examPat.slice(0, 300);
        } else {
          eb.textContent = 'See official notification';
        }
        ec.appendChild(eb);
        hte.appendChild(ec);
      }

      if (hasSyl) {
        const sc = el('div', 'psr-hte-col');
        const sh = el('div', 'psr-tri-head');
        sh.style.background = '#0891b2'; sh.style.color = '#fff';
        sh.innerHTML = '<i class="fa-solid fa-book-open"></i> Syllabus';
        sc.appendChild(sh);
        const sb = el('div', 'psr-hte-body');
        if (Array.isArray(d.syllabus)) {
          const ul = el('ul', 'psr-syl-list');
          d.syllabus.slice(0,8).forEach(item => {
            const li = el('li', 'psr-syl-item', safe(item).slice(0,60));
            ul.appendChild(li);
          });
          sb.appendChild(ul);
        } else if (typeof d.syllabus === 'object') {
          const subjects = Object.keys(d.syllabus).slice(0,5);
          const ul = el('ul', 'psr-syl-list');
          subjects.forEach(sub => {
            const li = el('li', 'psr-syl-item', sub.replace(/_/g,' '));
            ul.appendChild(li);
          });
          sb.appendChild(ul);
        } else {
          sb.textContent = safe(d.syllabus).slice(0,200);
        }
        sc.appendChild(sb);
        hte.appendChild(sc);
      }

      if (hte.children.length) card.appendChild(hte);
    }

    /* ── SECTION 6: FAQ + Related Jobs + Tags ── */
    const faqList = (() => {
      if (!d.faq) return [];
      const src = Array.isArray(d.faq) ? d.faq : Object.entries(d.faq||{}).map(([q,a])=>({question:q,answer:a}));
      return src.filter(f => f && (f.question||f.q) && (f.answer||f.a));
    })();
    const tagList = (() => {
      if (!d.tags) return [];
      if (Array.isArray(d.tags)) return d.tags;
      if (typeof d.tags === 'string') return d.tags.split(/[,;#]/).map(t=>t.trim()).filter(Boolean);
      return [];
    })();

    // Generate auto FAQ from data if none in JSON
    const autoFaq = [];
    if (!faqList.length) {
      if (hasVal(d.lastDate)) autoFaq.push({ q: 'What is the last date to apply?', a: `Ans. ${d.lastDate}` });
      if (hasVal(d.applyMode)) autoFaq.push({ q: 'What is the application mode?', a: `Ans. ${d.applyMode}` });
      if (hasVal(d.examDate)) autoFaq.push({ q: 'What is the exam date?', a: `Ans. ${d.examDate}` });
      if (d.feeItems.length) autoFaq.push({ q: 'Is there any application fee for SC/ST?', a: `Ans. ${d.feeItems.find(([k])=>/sc|st/i.test(k))?.[1] || 'See notification'}` });
    }
    const finalFaq = faqList.length ? faqList.slice(0,5) : autoFaq.slice(0,4);

    // Related jobs — category based
    const relatedLinks = (() => {
      const slug = safe(window.__TSJ_SLUG || '');
      const catLabel = safe(d.category || '');
      const combo = (slug + ' ' + catLabel).toLowerCase();
      if (/railway|rrb/.test(combo)) return [
        ['Latest Sarkari Jobs 2026', '/section/latest-jobs/'],
        ['Railway Jobs 2026', '/section/railway-jobs/'],
        ['Upcoming Govt Jobs 2026', '/section/upcoming-jobs/'],
        ['Sarkari Result 2026', '/section/results/'],
      ];
      if (/bank|sbi|rbi|ibps/.test(combo)) return [
        ['Bank Jobs 2026', '/section/bank-jobs/'],
        ['Latest Sarkari Jobs 2026', '/section/latest-jobs/'],
        ['Admit Card 2026', '/section/admit-card/'],
        ['Bank Result 2026', '/section/results/'],
      ];
      if (/police|army|defence|crpf|cisf/.test(combo)) return [
        ['Police & Defence Jobs 2026', '/section/police-jobs/'],
        ['Latest Sarkari Jobs 2026', '/section/latest-jobs/'],
        ['Admit Card 2026', '/section/admit-card/'],
        ['Police Result 2026', '/section/results/'],
      ];
      return [
        ['Latest Sarkari Jobs 2026', '/section/latest-jobs/'],
        ['Upcoming Govt Jobs 2026', '/section/upcoming-jobs/'],
        ['Central Govt Jobs 2026', '/section/central-jobs/'],
        ['Sarkari Result 2026', '/section/results/'],
      ];
    })();

    // Auto tags from title+category
    const autoTags = [];
    if (!tagList.length) {
      const words = titleText.split(/\s+/).filter(w => w.length > 4 && !/^(online|apply|form|2026|2025|posts?)$/i.test(w));
      words.slice(0,5).forEach(w => autoTags.push('#'+w.replace(/[^a-zA-Z0-9]/g,'')));
      if (hasVal(d.category)) autoTags.push('#'+d.category.replace(/\s+/g,''));
      autoTags.push('#LatestJobs2026', '#SarkariNaukri');
    }
    const finalTags = tagList.length ? tagList.slice(0,10) : autoTags.slice(0,8);

    if (finalFaq.length || relatedLinks.length || finalTags.length) {
      const frt = el('div', 'psr-frt');

      // FAQ col
      if (finalFaq.length) {
        const fc = el('div', 'psr-frt-col');
        const fh = el('div', 'psr-tri-head');
        fh.style.background = '#0f172a'; fh.style.color = '#fff';
        fh.innerHTML = '<i class="fa-solid fa-circle-question"></i> FAQ';
        fc.appendChild(fh);
        finalFaq.forEach(item => {
          const q = safe(item.question || item.q);
          const a = safe(item.answer || item.a);
          if (!q) return;
          const wrap = el('div', 'psr-faq-item');
          const qEl = el('button', 'psr-faq-q', `Q. ${q.slice(0,80)}`);
          const aEl = el('div', 'psr-faq-a', `${a.slice(0,200)}`);
          qEl.addEventListener('click', () => {
            const isOpen = aEl.classList.contains('open');
            aEl.classList.toggle('open', !isOpen);
          });
          wrap.appendChild(qEl); wrap.appendChild(aEl);
          fc.appendChild(wrap);
        });
        frt.appendChild(fc);
      }

      // Related col
      if (relatedLinks.length) {
        const rc = el('div', 'psr-frt-col');
        const rh = el('div', 'psr-tri-head');
        rh.style.background = '#0f766e'; rh.style.color = '#fff';
        rh.innerHTML = '<i class="fa-solid fa-briefcase"></i> Related Jobs';
        rc.appendChild(rh);
        const rl = el('ul', 'psr-related-list');
        relatedLinks.forEach(([label, href]) => {
          const li = el('li', 'psr-related-item');
          li.innerHTML = `<a href="${href}"><i class="fa-solid fa-angle-right"></i>${label}</a>`;
          rl.appendChild(li);
        });
        rc.appendChild(rl);
        frt.appendChild(rc);
      }

      // Tags col
      if (finalTags.length) {
        const tc = el('div', 'psr-frt-col');
        const th = el('div', 'psr-tri-head');
        th.style.background = '#475569'; th.style.color = '#fff';
        th.innerHTML = '<i class="fa-solid fa-tags"></i> Tags';
        tc.appendChild(th);
        const tw = el('div', 'psr-tag-wrap');
        finalTags.forEach(tag => {
          const span = el('span', 'psr-tag', safe(tag).replace(/^#?/,'#'));
          tw.appendChild(span);
        });
        tc.appendChild(tw);
        frt.appendChild(tc);
      }

      if (frt.children.length) card.appendChild(frt);
    }

    return card;
  }

  /* ── Build Non-Job Preferred Source Card ──────────────────────── */
  function buildNonJobCard(raw, row, name) {
    const j = raw || {};
    const titleText = name || safe(j.title || j.name || '');
    if (!titleText) return null;

    const card = el('div', 'psr-card');

    /* Header */
    const head = el('div', 'psr-head');
    head.innerHTML = `
      <div class="psr-head-left"><i class="fa-brands fa-google" style="font-size:1rem;"></i> Set as Preferred Source on Google</div>
      <div class="psr-head-right">⭐ YAHAN PAR FULL DETAILS SHOW HOGI</div>`;
    card.appendChild(head);
    card.appendChild(el('div', 'psr-subhead', '⭐ YAHAN PAR FULL DETAILS SHOW HOGI'));

    /* Detect type */
    const nlc = titleText.toLowerCase();
    const isScheme  = /scheme|yojna|yojana|pradhan\s*mantri/i.test(nlc);
    const isBalance = /balance\s*check|check\s*balance|status\s*check/i.test(nlc);
    const isAdmit   = /admit\s*card|hall\s*ticket/i.test(nlc);
    const isResult  = /result|merit\s*list|score\s*card/i.test(nlc);
    const isAnswer  = /answer\s*key/i.test(nlc);

    /* Service info table */
    const d = extractJobData(raw, row);
    const serviceRows = [];

    serviceRows.push(['Service Name', titleText.replace(/\s*[-–]\s*$/, '')]);

    const dept = safe(j.department || j.organization || j.board_name || j.org || row?.org || '');
    if (hasVal(dept)) serviceRows.push(['Department', dept]);

    const purpose = safe(j.purpose || j.description || j.short_information || '');
    if (hasVal(purpose)) serviceRows.push(['Purpose', purpose.slice(0,120)]);

    const beneficiaries = safe(j.beneficiaries || j.eligible_for || j.target || '');
    if (hasVal(beneficiaries)) serviceRows.push(['Beneficiaries', beneficiaries.slice(0,80)]);

    const websiteUrl = d.websiteUrl || safe(j.official_website || j.official_website_link || row?.officialWebsite || '');
    if (hasVal(websiteUrl)) serviceRows.push(['Official Website', `<a href="${websiteUrl}" target="_blank" rel="noopener">${websiteUrl.replace(/^https?:\/\/(www\.)?/,'').slice(0,50)}</a>`]);

    const serviceType = safe(j.service_type || (isBalance ? 'Online Service' : isScheme ? 'Govt Scheme' : isAdmit ? 'Admit Card' : isResult ? 'Result' : 'Online'));
    serviceRows.push(['Service Type', serviceType]);

    const state = safe(j.state || j.applicable_state || row?.jobLocation || '');
    if (hasVal(state)) serviceRows.push(['State', state]);

    const shortInfo = safe(j.short_information || j.jobs_info || j.description || row?.shortInfo || '');
    if (hasVal(shortInfo)) serviceRows.push(['Short Information', shortInfo.slice(0,200)]);

    const dual = el('div', 'psr-dual');

    // Left: Service info
    const lc = el('div', 'psr-dual-col');
    const lh = el('div', 'psr-dual-label');
    lh.style.background = '#7c3aed'; lh.style.color = '#fff';
    lh.innerHTML = '<i class="fa-solid fa-circle-info"></i> Service Information';
    lc.appendChild(lh);
    const lt = el('table', 'psr-table psr-nj-info-table');
    lt.innerHTML = serviceRows.map(([k,v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('');
    lc.appendChild(lt);
    dual.appendChild(lc);

    // Right: Important details
    const importantNJRows = [];
    const appStart = safe(j.service_start || j.available_from || '');
    importantNJRows.push(['Service Start', hasVal(appStart) ? appStart : 'Available Now']);
    const lastDate = safe(j.last_date || (j.important_dates && j.important_dates.last_date) || '');
    importantNJRows.push(['Last Date', hasVal(lastDate) ? fmtDate(lastDate) : 'No Last Date']);
    const updateDate = safe(j.last_updated || j.update_date || '');
    importantNJRows.push(['Update', hasVal(updateDate) ? updateDate : 'As Per Department']);
    const charges = safe(j.charges || j.fee || '');
    importantNJRows.push(['Charges', hasVal(charges) ? charges : (isBalance ? 'Free' : 'Free')]);

    const rc = el('div', 'psr-dual-col');
    const rh = el('div', 'psr-dual-label');
    rh.style.background = '#b91c1c'; rh.style.color = '#fff';
    rh.innerHTML = '<i class="fa-solid fa-calendar-check"></i> Important Details';
    rc.appendChild(rh);
    const rt = el('table', 'psr-table');
    rt.innerHTML = importantNJRows.map(([k,v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('');
    rc.appendChild(rt);
    dual.appendChild(rc);

    card.appendChild(dual);

    /* Important Links + How To Use */
    const linkDefs = [];
    if (hasVal(d.websiteUrl)) linkDefs.push({ url: d.websiteUrl, label: 'Official Website', cls: 'psr-link-red', icon: 'fa-globe' });
    if (hasVal(d.applyUrl))  linkDefs.push({ url: d.applyUrl,  label: 'Apply / Check',   cls: 'psr-link-green', icon: 'fa-arrow-up-right-from-square' });
    if (hasVal(d.notifUrl))  linkDefs.push({ url: d.notifUrl,  label: 'Notification PDF', cls: 'psr-link-blue',  icon: 'fa-file-pdf' });
    if (hasVal(d.resultUrl)) linkDefs.push({ url: d.resultUrl, label: 'Check Result',     cls: 'psr-link-orange',icon: 'fa-trophy' });
    if (hasVal(d.admitUrl))  linkDefs.push({ url: d.admitUrl,  label: 'Admit Card',       cls: 'psr-link-orange',icon: 'fa-id-card' });
    if (hasVal(d.answerUrl)) linkDefs.push({ url: d.answerUrl, label: 'Answer Key',       cls: 'psr-link-blue',  icon: 'fa-key' });
    for (const ul of d.usefulLinks.slice(0,3)) {
      const rawLinks = ul.links || ul.url || '';
      const urls = Array.isArray(rawLinks) ? rawLinks : [rawLinks];
      urls.forEach(u => {
        const hu = safe(u);
        if (hu && hu.startsWith('http') && !linkDefs.some(l=>l.url===hu))
          linkDefs.push({ url: hu, label: safe(ul.title||'Link').slice(0,30), cls: 'psr-link-blue', icon: 'fa-link' });
      });
    }
    // Fallback: row destUrl
    const destUrl = safe(row?.destUrl || row?.officialWebsite || '');
    if (!linkDefs.length && hasVal(destUrl))
      linkDefs.push({ url: destUrl, label: 'Click Here', cls: 'psr-link-red', icon: 'fa-globe' });

    // How to use steps
    const howToUse = (() => {
      const hta = safe(j.how_to_apply || j.steps || j.how_to_use || row?.howToApply || '');
      if (hta.length > 10) {
        return hta.split(/\n/).filter(s=>s.trim().length>4).slice(0,5);
      }
      // Auto-generate
      if (isBalance) return [
        `${websiteUrl || 'Official website'} पर जाएं`,
        `'Happy Card Balance Check' पर क्लिक करें`,
        `अपना Registration Number भरें`,
        `Captcha भरें और 'Submit' करें`,
        `Balance Screen पर दिखेगा`
      ];
      if (isScheme) return [
        'Official website पर जाएं',
        'Scheme / Yojana section खोलें',
        'Eligibility criteria check करें',
        'Application form भरें',
        'Documents upload करें और submit करें'
      ];
      return [
        'Official website पर जाएं',
        'Required section खोलें',
        'Necessary details भरें',
        'Submit करें'
      ];
    })();

    // Required Documents
    const reqDocs = (() => {
      if (!j.required_documents && !j.documents) return [];
      const src = j.required_documents || j.documents || '';
      if (Array.isArray(src)) return src;
      if (typeof src === 'string') return src.split(/[,;\n]/).map(s=>s.trim()).filter(Boolean);
      return [];
    })();
    const autoReqDocs = reqDocs.length ? reqDocs : (() => {
      if (isBalance) return ['Happy Card Number / Registration Number','Mobile Number','Captcha Code','Basic Detail'];
      if (isScheme)  return ['Aadhaar Card','Income Certificate','Residence Proof','Bank Passbook','Photo'];
      return [];
    })();

    const tri = el('div', 'psr-tri');

    // Links col
    const lkc = el('div', 'psr-tri-col');
    const lkh = el('div', 'psr-tri-head');
    lkh.style.background = '#0f766e'; lkh.style.color = '#fff';
    lkh.innerHTML = '<i class="fa-solid fa-link"></i> Important Links';
    lkc.appendChild(lkh);
    const lkb = el('div', 'psr-tri-body');
    lkb.innerHTML = linkDefs.map(lk => `<a href="${lk.url}" target="_blank" rel="noopener" class="psr-link-btn ${lk.cls}"><i class="fa-solid ${lk.icon}"></i> ${lk.label}</a>`).join('') || '<span style="color:#64748b;font-size:.75rem;">Check official website</span>';
    lkc.appendChild(lkb);
    tri.appendChild(lkc);

    // How to use col
    const htc = el('div', 'psr-tri-col');
    const hth = el('div', 'psr-tri-head');
    hth.style.background = '#0369a1'; hth.style.color = '#fff';
    hth.innerHTML = '<i class="fa-solid fa-list-ol"></i> How To ' + (isBalance ? 'Check Balance' : isScheme ? 'Apply' : 'Use');
    htc.appendChild(hth);
    const htb = el('div', 'psr-tri-body');
    const hul = el('ul', 'psr-step-list');
    howToUse.slice(0,5).forEach((step, i) => {
      const li = el('li', 'psr-step');
      li.innerHTML = `<span class="psr-step-num psr-step-num-green">${i+1}</span><span>${safe(step).slice(0,80)}</span>`;
      hul.appendChild(li);
    });
    htb.appendChild(hul);
    htc.appendChild(htb);
    tri.appendChild(htc);

    // Required Docs col
    const rdc = el('div', 'psr-tri-col');
    const rdh = el('div', 'psr-tri-head');
    rdh.style.background = '#b45309'; rdh.style.color = '#fff';
    rdh.innerHTML = '<i class="fa-solid fa-file-lines"></i> Required Documents';
    rdc.appendChild(rdh);
    if (autoReqDocs.length) {
      const rdb = el('div');
      autoReqDocs.slice(0,5).forEach((doc,i) => {
        const item = el('div', 'psr-doc-item');
        item.innerHTML = `<span class="psr-step-num psr-step-num-blue" style="font-size:.6rem;">${i+1}</span><span>${safe(doc).slice(0,70)}</span>`;
        rdb.appendChild(item);
      });
      rdc.appendChild(rdb);
    } else {
      const rdb = el('div', 'psr-tri-body', '<span style="color:#64748b;">See official notification</span>');
      rdc.appendChild(rdb);
    }
    tri.appendChild(rdc);

    card.appendChild(tri);

    /* Instructions + FAQ + Related */
    const instructions = (() => {
      if (!j.instructions && !j.important_instructions) return [];
      const src = j.instructions || j.important_instructions || '';
      if (Array.isArray(src)) return src;
      if (typeof src === 'string') return src.split(/[;\n]/).map(s=>s.trim()).filter(Boolean);
      return [];
    })();
    const autoInstructions = instructions.length ? instructions : (() => {
      if (isBalance) return [
        'Correct Registration Number दर्ज करें।',
        'Internet Connection होना आवश्यक है।',
        'यदि captcha नहीं दिखे तो page refresh करें।',
        'सदा याद रखें की balance online ही check होगा।'
      ];
      return [];
    })();

    const faqItems = (() => {
      if (!j.faq) {
        if (isBalance) return [
          { q: `${titleText.replace(/\s*[-–].*/,'').slice(0,50)} कैसे चेक करें?`, a: `Official website पर जाकर check करें।` },
          { q: 'क्या कोई charge लगता है?', a: 'Ans. नहीं, यह सेवा बिल्कुल free है।' },
          { q: 'किसके लिए यह सेवा उपलब्ध है?', a: 'Ans. Registered Labour / Workers के लिए।' },
        ];
        if (isScheme) return [
          { q: 'इस scheme का लाभ कौन ले सकता है?', a: 'Ans. Eligible beneficiaries — official notification देखें।' },
          { q: 'Apply कैसे करें?', a: 'Ans. Official website पर जाकर form fill करें।' },
        ];
        return [];
      }
      const src = Array.isArray(j.faq) ? j.faq : Object.entries(j.faq||{}).map(([q,a])=>({question:q,answer:a}));
      return src.filter(f => f && (f.question||f.q) && (f.answer||f.a)).slice(0,4);
    })();

    // Related services
    const relatedServices = (() => {
      if (isBalance) return [
        ['Labour Department Haryana', '#'],
        ['E-Shram Card Balance Check', '#'],
        ['PF Balance Check', '#'],
        ['Labour Registration Check', '#'],
      ];
      if (isScheme) return [
        ['Latest Govt Schemes', '/section/latest-jobs/'],
        ['State Jobs', '/section/state-jobs/'],
        ['Central Schemes', '/section/central-jobs/'],
      ];
      return [
        ['Latest Sarkari Jobs 2026', '/section/latest-jobs/'],
        ['Sarkari Result 2026', '/section/results/'],
        ['Upcoming Jobs', '/section/upcoming-jobs/'],
      ];
    })();

    const hasInst = autoInstructions.length > 0;
    const hasFaqNJ = faqItems.length > 0;
    const tagsNJ   = safe(j.tags || titleText).split(/[\s,#]+/).filter(w=>w.length>3).slice(0,6).map(w=>'#'+w.replace(/[^a-zA-Z0-9]/g,''));

    if (hasInst || hasFaqNJ || relatedServices.length) {
      const frt = el('div', 'psr-frt');

      if (hasInst) {
        const ic = el('div', 'psr-frt-col');
        const ih = el('div', 'psr-tri-head');
        ih.style.background = '#6d28d9'; ih.style.color = '#fff';
        ih.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Important Instructions';
        ic.appendChild(ih);
        autoInstructions.slice(0,5).forEach(inst => {
          const d = el('div', 'psr-doc-item');
          d.innerHTML = `<i class="fa-solid fa-circle-dot" style="color:#7c3aed;font-size:.6rem;margin-top:4px;flex-shrink:0;"></i><span>${safe(inst).slice(0,100)}</span>`;
          ic.appendChild(d);
        });
        frt.appendChild(ic);
      }

      if (hasFaqNJ) {
        const fc = el('div', 'psr-frt-col');
        const fh = el('div', 'psr-tri-head');
        fh.style.background = '#0f172a'; fh.style.color = '#fff';
        fh.innerHTML = '<i class="fa-solid fa-circle-question"></i> FAQ';
        fc.appendChild(fh);
        faqItems.forEach(item => {
          const q = safe(item.question || item.q);
          const a = safe(item.answer || item.a);
          if (!q) return;
          const wrap = el('div', 'psr-faq-item');
          const qEl  = el('button', 'psr-faq-q', `Q. ${q.slice(0,80)}`);
          const aEl  = el('div', 'psr-faq-a', a.slice(0,200));
          qEl.addEventListener('click', () => aEl.classList.toggle('open'));
          wrap.appendChild(qEl); wrap.appendChild(aEl);
          fc.appendChild(wrap);
        });
        frt.appendChild(fc);
      }

      if (relatedServices.length) {
        const rc = el('div', 'psr-frt-col');
        const rh = el('div', 'psr-tri-head');
        rh.style.background = '#0f766e'; rh.style.color = '#fff';
        rh.innerHTML = '<i class="fa-solid fa-link"></i> Related Services';
        rc.appendChild(rh);
        const rl = el('ul', 'psr-related-list');
        relatedServices.forEach(([label, href]) => {
          const li = el('li', 'psr-related-item');
          li.innerHTML = `<a href="${href}"><i class="fa-solid fa-angle-right"></i>${label}</a>`;
          rl.appendChild(li);
        });
        rc.appendChild(rl);
        // Tags
        if (tagsNJ.length) {
          const tw = el('div', 'psr-tag-wrap');
          tagsNJ.forEach(tag => tw.appendChild(el('span','psr-tag', tag)));
          rc.appendChild(el('div','psr-tri-head','').cloneNode());
          rc.appendChild(tw);
        }
        frt.appendChild(rc);
      }

      if (frt.children.length) card.appendChild(frt);
    }

    return card;
  }

  /* ── Inject card into page ───────────────────────────────────── */
  function injectCard(card, isJob) {
    if (!card) return;
    // Check for already injected
    if (document.getElementById('psr-rich-card')) return;
    card.id = 'psr-rich-card';

    const cardId = isJob ? 'preferredSourceCard' : 'preferredSourceCardNJ';
    const existing = document.getElementById(cardId);
    if (existing) {
      existing.style.display = 'none';
      existing.parentNode.insertBefore(card, existing.nextSibling);
      return;
    }
    // State job detail: inject after main CTA or after header card
    const sjdCta = document.getElementById('btnMainCta');
    const sjdShort = document.getElementById('shortInfoCard');
    if (sjdShort && sjdShort.parentNode) {
      sjdShort.parentNode.insertBefore(card, sjdShort);
      return;
    }
    if (sjdCta && sjdCta.parentNode) {
      sjdCta.parentNode.insertBefore(card, sjdCta.nextSibling);
      return;
    }
    // Generic fallback: prepend to layoutJob or main content
    const layout = document.getElementById('layoutJob') || document.getElementById('layoutNonJob') || document.getElementById('jbContent');
    if (layout) layout.insertBefore(card, layout.firstChild);
  }

  /* ── Integration hook ───────────────────────────────────────── */
  function tryRender() {
    if (document.getElementById('psr-rich-card')) return; // already rendered
    const raw   = window.__TSJ_RAW_JOB;
    const row   = window.__TSJ_ROW || null;

    const layoutJob    = document.getElementById('layoutJob');
    const layoutNonJob = document.getElementById('layoutNonJob');
    // Detect state-job-detail.html by presence of sjdTitle
    const isSJD = !!document.getElementById('sjdTitle');

    const isJob    = isSJD || (layoutJob && layoutJob.style.display !== 'none');
    const isNonJob = !isSJD && layoutNonJob && layoutNonJob.style.display !== 'none';

    if (!isJob && !isNonJob && !isSJD) return;

    const name = (document.getElementById('sjdTitle') || document.getElementById('jbTitle'))?.textContent ||
                 document.getElementById('nonJobTitle')?.textContent || '';
    if (!name || name === 'Loading...' || name === 'Job Title') return;

    if (isJob || isSJD) {
      const card = buildJobCard(raw || {}, row, name);
      if (card) injectCard(card, true);
    } else if (isNonJob) {
      const card = buildNonJobCard(raw || {}, row, name);
      if (card) injectCard(card, false);
    }
  }

  /* ── Wait for render completion ──────────────────────────────── */
  const _origOnRenderDone = window.__TSJ_ON_RENDER_DONE;
  window.__TSJ_ON_RENDER_DONE = function(rawJob) {
    if (typeof _origOnRenderDone === 'function') _origOnRenderDone(rawJob);
    setTimeout(tryRender, 120);
  };

  // Also try after page load as fallback
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(tryRender, 800));
  } else {
    setTimeout(tryRender, 800);
  }

  // Watch for layout changes (dynamic render)
  const _obs = new MutationObserver(() => {
    if (!document.getElementById('psr-rich-card')) {
      setTimeout(tryRender, 200);
    }
  });
  const target = document.getElementById('jbContent') || document.getElementById('sjdTitle')?.closest('.sjd-center-col') || document.body;
  _obs.observe(target, { childList: true, subtree: true, attributes: true });

})();
