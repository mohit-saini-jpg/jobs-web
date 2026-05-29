/**
 * ══════════════════════════════════════════════════════════════════════
 *  TOP SARKARI JOBS — "Set as Preferred Source on Google"
 *  Universal Full-Data Renderer  v4.0  (2026-05-28)
 * ══════════════════════════════════════════════════════════════════════
 *
 *  Supports ALL page types:
 *    • job.html          (Complete_Jobs_Full_Data / merged_sarkari_data)
 *    • state-job-detail  (data/state-jobs.json  — sections[] format)
 *    • education-detail  (Education_Jobs.json   — sections[] format)
 *    • view.html / non-job pages
 *
 *  Renders EVERY JSON key — paragraphs, tables, lists, FAQ, links,
 *  instructions, dates, vacancy, category-wise, salary, selection,
 *  how-to-apply, exam-pattern, syllabus, seo_tags, related jobs.
 *
 *  ZERO data loss. ZERO duplicate sections.
 * ══════════════════════════════════════════════════════════════════════
 */
(function () {
  'use strict';

  /* ── Guard: disabled flag ──────────────────────────────────────── */
  if (window.__TSJ_PSR_V4_DONE) return;

  /* ══════════════════════════════════════════════════════════════════
     § 1 — CSS
  ══════════════════════════════════════════════════════════════════ */
  const CSS_ID = 'tsj-psr-v4-css';
  if (!document.getElementById(CSS_ID)) {
    const s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent = `
    /* ── Outer wrapper ── */
    #psr-v4-card{background:#fff;border:1.5px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:16px;box-shadow:0 2px 10px rgba(0,0,0,.07);font-family:inherit;}
    /* ── Section block ── */
    .psr4-sec{border-top:1px solid #e9eef4;}
    .psr4-sec:first-child{border-top:none;}
    .psr4-head{display:flex;align-items:center;gap:7px;padding:7px 14px;font-size:.75rem;font-weight:800;letter-spacing:.04em;color:#fff;}
    .psr4-head i{font-size:.8rem;opacity:.9;}
    .psr4-body{padding:0;}
    /* ── Two-col layout ── */
    .psr4-dual{display:grid;grid-template-columns:1fr 1fr;gap:0;}
    @media(max-width:640px){.psr4-dual{grid-template-columns:1fr;}}
    .psr4-col{padding:0;}
    .psr4-col:first-child{border-right:1px solid #e9eef4;}
    @media(max-width:640px){.psr4-col:first-child{border-right:none;border-bottom:1px solid #e9eef4;}}
    .psr4-col-head{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.05em;padding:5px 12px;display:flex;align-items:center;gap:5px;color:#fff;}
    /* ── Three-col layout ── */
    .psr4-tri{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;}
    @media(max-width:700px){.psr4-tri{grid-template-columns:1fr;}}
    .psr4-tri-col{padding:0;}
    .psr4-tri-col:not(:last-child){border-right:1px solid #e9eef4;}
    @media(max-width:700px){.psr4-tri-col:not(:last-child){border-right:none;border-bottom:1px solid #e9eef4;}}
    .psr4-tri-head{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em;padding:5px 12px;color:#fff;display:flex;align-items:center;gap:5px;}
    .psr4-tri-body{padding:8px 12px;font-size:.78rem;color:#1e293b;line-height:1.7;}
    /* ── KV table (2 col: label | value) ── */
    .psr4-kv{width:100%;border-collapse:collapse;}
    .psr4-kv th{background:#f8fafc;color:#374151;font-weight:700;font-size:.74rem;padding:6px 11px;text-align:left;border-bottom:1px solid #e9eef4;white-space:nowrap;width:42%;vertical-align:top;}
    .psr4-kv td{padding:6px 11px;color:#1e293b;font-size:.76rem;border-bottom:1px solid #e9eef4;line-height:1.55;word-break:break-word;vertical-align:top;}
    .psr4-kv tr:last-child th,.psr4-kv tr:last-child td{border-bottom:none;}
    .psr4-kv td a{color:#1d4ed8;font-weight:600;text-decoration:none;}
    /* ── Multi-col table ── */
    .psr4-tbl-wrap{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;}
    .psr4-tbl{width:100%;border-collapse:collapse;font-size:.74rem;min-width:280px;}
    .psr4-tbl th{background:#1d4ed8;color:#fff;padding:6px 10px;font-weight:700;text-align:left;white-space:nowrap;}
    .psr4-tbl td{padding:6px 10px;border-bottom:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top;}
    .psr4-tbl tbody tr:last-child td{border-bottom:none;background:#f0f9ff;font-weight:700;}
    /* ── Raw content table (from sections[].rows) ── */
    .psr4-raw-tbl{width:100%;border-collapse:collapse;font-size:.74rem;min-width:260px;}
    .psr4-raw-tbl td{padding:5px 10px;border:1px solid #e9eef4;color:#1e293b;word-break:break-word;vertical-align:top;}
    .psr4-raw-tbl tr:first-child td{background:#f0f7ff;font-weight:700;color:#1d4ed8;}
    .psr4-raw-tbl td a{color:#1d4ed8;font-weight:600;text-decoration:none;}
    /* ── Lists ── */
    .psr4-list{list-style:none;margin:0;padding:0;}
    .psr4-li{display:flex;align-items:flex-start;gap:8px;padding:5px 12px;border-bottom:1px solid #f1f5f9;font-size:.77rem;color:#374151;line-height:1.55;}
    .psr4-li:last-child{border-bottom:none;}
    .psr4-li-dot{flex-shrink:0;margin-top:4px;font-size:.55rem;color:#1d4ed8;}
    /* ── Step list ── */
    .psr4-step-list{list-style:none;margin:0;padding:0;}
    .psr4-step{display:flex;align-items:flex-start;gap:8px;padding:6px 12px;border-bottom:1px solid #f1f5f9;font-size:.77rem;color:#1e293b;line-height:1.55;}
    .psr4-step:last-child{border-bottom:none;}
    .psr4-step-num{flex-shrink:0;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.62rem;font-weight:800;color:#fff;margin-top:1px;}
    /* ── FAQ ── */
    .psr4-faq{border-bottom:1px solid #f1f5f9;}
    .psr4-faq:last-child{border-bottom:none;}
    .psr4-faq-q{width:100%;text-align:left;background:#f8fafc;border:none;padding:7px 12px;font-size:.76rem;font-weight:700;color:#0f172a;cursor:pointer;line-height:1.45;display:flex;justify-content:space-between;gap:8px;}
    .psr4-faq-q:hover{background:#eff6ff;color:#1d4ed8;}
    .psr4-faq-a{display:none;padding:5px 12px 8px;font-size:.74rem;color:#374151;line-height:1.65;}
    .psr4-faq-a.open{display:block;}
    /* ── Links ── */
    .psr4-links-wrap{padding:9px 12px;display:flex;flex-wrap:wrap;gap:6px;}
    .psr4-link{display:inline-flex;align-items:center;gap:5px;padding:5px 11px;border-radius:6px;font-size:.73rem;font-weight:700;text-decoration:none;white-space:nowrap;transition:opacity .15s;}
    .psr4-link:hover{opacity:.85;}
    .psr4-link-green{background:#d1fae5;color:#065f46;border:1px solid #6ee7b7;}
    .psr4-link-blue{background:#dbeafe;color:#1e40af;border:1px solid #93c5fd;}
    .psr4-link-red{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;}
    .psr4-link-orange{background:#fef3c7;color:#92400e;border:1px solid #fcd34d;}
    .psr4-link-purple{background:#ede9fe;color:#5b21b6;border:1px solid #c4b5fd;}
    .psr4-link-gray{background:#f1f5f9;color:#475569;border:1px solid #cbd5e1;}
    /* ── Tags ── */
    .psr4-tags{padding:8px 12px;display:flex;flex-wrap:wrap;gap:5px;}
    .psr4-tag{background:#f0f7ff;border:1px solid #bfdbfe;color:#1e40af;padding:3px 9px;border-radius:20px;font-size:.7rem;font-weight:600;}
    /* ── Paragraph ── */
    .psr4-para{padding:8px 12px;font-size:.77rem;color:#374151;line-height:1.7;}
    .psr4-para p{margin:0 0 5px;}
    .psr4-para:last-child p:last-child{margin:0;}
    /* ── Notice/highlight ── */
    .psr4-notice{padding:7px 14px;font-size:.75rem;color:#374151;line-height:1.7;background:#f8fafc;border-left:3px solid #1d4ed8;}
    /* ── Badge ── */
    .psr4-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.69rem;font-weight:700;}
    .psr4-badge-online{background:#d1fae5;color:#065f46;}
    .psr4-badge-offline{background:#fef3c7;color:#92400e;}
    .psr4-date-red{color:#dc2626;font-weight:700;}
    /* ── Responsive ── */
    @media(max-width:480px){
      .psr4-kv th,.psr4-kv td{padding:5px 8px;font-size:.71rem;}
      .psr4-tbl th,.psr4-tbl td{padding:5px 7px;font-size:.7rem;}
      .psr4-raw-tbl td{padding:4px 7px;font-size:.7rem;}
      .psr4-head{padding:6px 10px;}
      .psr4-li,.psr4-step{padding:5px 10px;font-size:.73rem;}
      .psr4-links-wrap{padding:7px 8px;}
    }
    `;
    document.head.appendChild(s);
  }

  /* ══════════════════════════════════════════════════════════════════
     § 2 — UTILITIES
  ══════════════════════════════════════════════════════════════════ */
  const safe = v => {
    if (v == null) return '';
    if (typeof v === 'string') return v.trim();
    if (typeof v === 'number' || typeof v === 'boolean') return String(v);
    if (Array.isArray(v)) return v.map(x => safe(x)).filter(Boolean).join(', ');
    if (typeof v === 'object') {
      for (const k of ['text','value','name','description','details','content','title']) {
        if (typeof v[k] === 'string' && v[k].trim()) return v[k].trim();
      }
      return Object.values(v).map(x => safe(x)).filter(Boolean).join(' | ');
    }
    return '';
  };

  const esc = s => safe(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  const isUrl = s => /^https?:\/\//i.test(safe(s));
  const isPdf = s => /\.pdf(\?|$)/i.test(safe(s));
  const hasVal = v => { const s = safe(v); return s && s !== '—' && s !== '-' && s !== 'N/A' && s !== 'null'; };

  function keyLabel(k) {
    return safe(k).replace(/_+/g,' ').replace(/\b[a-z]/g,c=>c.toUpperCase())
      .replace(/\bObc\b/g,'OBC').replace(/\bEws\b/g,'EWS').replace(/\bSc\b/g,'SC')
      .replace(/\bSt\b/g,'ST').replace(/\bPh\b/g,'PH/PwD').replace(/\bPdf\b/g,'PDF')
      .replace(/\bUrl\b/g,'URL').replace(/\bId\b/g,'ID');
  }

  function fmtDate(raw) {
    if (!raw) return '';
    const s = safe(raw);
    let m = s.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})/);
    if (m) return `${m[3].padStart(2,'0')}/${m[2].padStart(2,'0')}/${m[1]}`;
    m = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
    if (m) return `${m[1].padStart(2,'0')}/${m[2].padStart(2,'0')}/${m[3]}`;
    return s.slice(0,25);
  }

  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  function mkHead(icon, text, color) {
    const d = el('div', 'psr4-head');
    d.style.background = color || '#1d4ed8';
    d.innerHTML = `<i class="fa-solid ${icon}"></i> ${esc(text)}`;
    return d;
  }

  function mkSection(icon, label, color, bodyEl) {
    const wrap = el('div', 'psr4-sec');
    wrap.appendChild(mkHead(icon, label, color));
    const body = el('div', 'psr4-body');
    body.appendChild(bodyEl);
    wrap.appendChild(body);
    return wrap;
  }

  /* Classify link type */
  function linkType(key, url) {
    const k = (key||'').toLowerCase(); const u = (url||'').toLowerCase();
    if (/apply|register|application|form/i.test(k)) return 'apply';
    if (/notification|advt|advertisement/i.test(k)) return 'notif';
    if (/official.web|website|portal/i.test(k)) return 'web';
    if (/admit|hall.ticket/i.test(k)) return 'admit';
    if (/result|merit/i.test(k)) return 'result';
    if (/answer.key/i.test(k)) return 'answer';
    if (/syllabus/i.test(k)) return 'syl';
    if (/login|candidate/i.test(k)) return 'login';
    if (isPdf(u)) return 'notif';
    if (/apply|register/i.test(u)) return 'apply';
    return 'link';
  }
  const LINK_CLS = {apply:'psr4-link-green',notif:'psr4-link-blue',web:'psr4-link-red',admit:'psr4-link-orange',result:'psr4-link-orange',answer:'psr4-link-blue',syl:'psr4-link-purple',login:'psr4-link-purple',link:'psr4-link-gray'};
  const LINK_ICO = {apply:'fa-pen-to-square',notif:'fa-file-pdf',web:'fa-globe',admit:'fa-id-card',result:'fa-trophy',answer:'fa-key',syl:'fa-book-open',login:'fa-user-lock',link:'fa-arrow-up-right-from-square'};

  function smartLabel(key, url) {
    const k = (key||'').toLowerCase();
    if (/apply_online|apply.link|click_here_to_apply/i.test(k)) return 'Apply Online';
    if (/official_notification|notification_pdf/i.test(k)) return 'Official Notification PDF';
    if (/official_website/i.test(k)) return 'Official Website';
    if (/admit_card|hall.ticket/i.test(k)) return 'Admit Card';
    if (/result/i.test(k)) return 'Result';
    if (/answer.key/i.test(k)) return 'Answer Key';
    if (/syllabus/i.test(k)) return 'Syllabus';
    if (/form.pdf|application.form/i.test(k)) return 'Download Form PDF';
    if (/login/i.test(k)) return 'Candidate Login';
    if (/click_here/i.test(k)) {
      if (/login|candidate/i.test(url)) return 'Candidate Login / Apply';
      if (isPdf(url)) return 'Download PDF';
      if (/apply|register/i.test(url)) return 'Apply Online';
      return 'Click Here';
    }
    return keyLabel(key);
  }

  /* ══════════════════════════════════════════════════════════════════
     § 3 — LINK COLLECTOR
     Extracts ALL URLs from any JSON structure into a flat array
     [{label, url, type}], deduped.
  ══════════════════════════════════════════════════════════════════ */
  function collectLinks(raw) {
    const store = []; const seen = new Set();

    function add(label, url, key) {
      const u = safe(url);
      if (!isUrl(u) || seen.has(u)) return;
      // Skip YouTube embeds from link buttons
      if (/youtu\.?be|youtube\.com/i.test(u)) return;
      seen.add(u);
      const t = linkType(key||label||'', u);
      store.push({ label: smartLabel(key||label||'', u) || label || 'Link', url: u, type: t });
    }

    function crawl(obj, parentKey) {
      if (!obj || typeof obj !== 'object') {
        if (typeof obj === 'string' && isUrl(obj)) add(smartLabel(parentKey,obj), obj, parentKey);
        return;
      }
      if (Array.isArray(obj)) {
        obj.forEach((item,i) => {
          if (typeof item === 'string' && isUrl(item)) {
            add(smartLabel(parentKey,item)+' ('+(i+1)+')', item, parentKey);
          } else crawl(item, parentKey);
        });
        return;
      }
      // Object with url/link/href
      const u = safe(obj.url||obj.link||obj.href||'');
      if (isUrl(u)) {
        const lbl = safe(obj.label||obj.text||obj.name||obj.title||parentKey||'');
        add(lbl||smartLabel(parentKey,u), u, parentKey);
        return; // don't double-crawl
      }
      for (const [k,v] of Object.entries(obj)) {
        if (['seo_tags','tags','keywords','faq','faqs','how_to_apply',
             'selection_process','important_instructions','syllabus','exam_pattern',
             'vacancy_details','category_wise_vacancy'].includes(k)) continue;
        crawl(v, k);
      }
    }

    // Priority: flat link fields first (better labels)
    const FLAT = {
      apply_online_link: 'Apply Online',
      apply_online: 'Apply Online',
      official_notification_pdf_link: 'Official Notification PDF',
      official_website_link: 'Official Website',
      official_website: 'Official Website',
      form_pdf_link: 'Download Form PDF',
      form_pdf_free_link: 'Download Form (Free)',
      application_form_pdf_link: 'Application Form PDF',
      admit_card: 'Admit Card',
      result: 'Result',
      answer_key: 'Answer Key',
      syllabus: 'Syllabus PDF',
    };
    for (const [k,lbl] of Object.entries(FLAT)) {
      const v = raw[k] || (raw.important_links && raw.important_links[k]);
      if (typeof v === 'string' && isUrl(v)) add(lbl, v, k);
    }

    // Then crawl important_links
    if (raw.important_links) crawl(raw.important_links, 'important_links');

    // _udyn_links from universal-renderer (already normalized)
    if (Array.isArray(raw._udyn_links)) {
      raw._udyn_links.forEach(l => add(l.label||'Link', l.url, l.type||'link'));
    }

    // useful_links
    if (Array.isArray(raw.useful_links)) {
      raw.useful_links.forEach(ul => {
        const lbl = safe(ul.title||ul.name||ul.label||'');
        const raw_links = ul.links||ul.url||ul.href||'';
        const urls = Array.isArray(raw_links) ? raw_links : [raw_links];
        urls.forEach(u => add(lbl||smartLabel('',u), u, lbl||'link'));
      });
    }

    // state-jobs important_links object
    if (raw.important_links && typeof raw.important_links === 'object') {
      Object.entries(raw.important_links).forEach(([k,v]) => {
        if (typeof v === 'string' && isUrl(v)) add(smartLabel(k,v), v, k);
      });
    }

    return store;
  }

  /* ══════════════════════════════════════════════════════════════════
     § 4 — SECTION CONTENT RENDERER
     Turns ANY content block type into HTML string.
     Handles: paragraph, table (rows with cell objects), list,
              links (structured), ordered arrays, plain strings.
  ══════════════════════════════════════════════════════════════════ */
  function renderContentBlock(block, links, seenLinks) {
    if (!block) return '';
    const type = (block.type||'').toLowerCase();

    /* ── paragraph ── */
    if (type === 'paragraph' || type === 'para') {
      const txt = safe(block.text || block.content || block.value || '');
      if (!txt) return '';
      const html = txt.replace(/\n/g,'<br>');
      return `<div class="psr4-para"><p>${html}</p></div>`;
    }

    /* ── table (state-jobs format: rows[][] of {text, links[]}) ── */
    if (type === 'table') {
      const rows = block.rows;
      if (!Array.isArray(rows) || !rows.length) return '';
      let html = '<div class="psr4-tbl-wrap"><table class="psr4-raw-tbl"><tbody>';
      rows.forEach(row => {
        if (!Array.isArray(row)) {
          // might be a flat string row
          html += `<tr><td colspan="4">${esc(safe(row))}</td></tr>`;
          return;
        }
        // colspan for single-cell rows
        if (row.length === 1) {
          const cell = row[0];
          const cellTxt = safe(cell && cell.text !== undefined ? cell.text : cell);
          const cellLinks = (cell && Array.isArray(cell.links)) ? cell.links : [];
          let cellHtml = esc(cellTxt);
          cellLinks.forEach(lk => {
            const lu = safe(lk.url||lk.href||lk.link||lk||'');
            if (!isUrl(lu)) return;
            const ll = safe(lk.text||lk.label||lk.name||'Open');
            if (!seenLinks.has(lu)) {
              seenLinks.add(lu);
              links.push({ label: ll||'Open', url: lu, type: linkType('',lu) });
            }
          });
          html += `<tr><td colspan="6" style="font-weight:700;background:#f0f7ff;color:#1d4ed8;">${cellHtml}</td></tr>`;
          return;
        }
        html += '<tr>';
        row.forEach(cell => {
          const cellTxt = safe(cell && cell.text !== undefined ? cell.text : cell);
          const cellLinks = (cell && Array.isArray(cell.links)) ? cell.links : [];
          let inner = esc(cellTxt);
          cellLinks.forEach(lk => {
            const lu = safe(lk.url||lk.href||lk.link||lk||'');
            const ll = safe(lk.text||lk.label||lk.name||'Open');
            if (!isUrl(lu)) return;
            if (!seenLinks.has(lu)) {
              seenLinks.add(lu);
              links.push({ label: ll||'Open', url: lu, type: linkType(ll,lu) });
            }
            inner += ` <a href="${esc(lu)}" target="_blank" rel="noopener" class="psr4-link psr4-link-blue" style="font-size:.68rem;padding:2px 7px;">${esc(ll||'Open')}</a>`;
          });
          html += `<td>${inner}</td>`;
        });
        html += '</tr>';
      });
      html += '</tbody></table></div>';
      return html;
    }

    /* ── list ── */
    if (type === 'list' || type === 'ul' || type === 'ol') {
      const items = block.items || block.content || [];
      if (!Array.isArray(items) || !items.length) return '';
      let html = '<ul class="psr4-list">';
      items.forEach(item => {
        const txt = safe(item);
        if (txt) html += `<li class="psr4-li"><i class="fa-solid fa-circle-dot psr4-li-dot"></i><span>${esc(txt)}</span></li>`;
      });
      html += '</ul>';
      return html;
    }

    /* ── links block ── */
    if (type === 'links') {
      const items = block.items || block.links || [];
      const arr = Array.isArray(items) ? items : [items];
      arr.forEach(item => {
        const u = safe(item.url||item.link||item.href||item||'');
        const l = safe(item.text||item.label||item.name||'Link');
        if (isUrl(u) && !seenLinks.has(u)) {
          seenLinks.add(u);
          links.push({ label: l, url: u, type: linkType(l,u) });
        }
      });
      return ''; // will render in links section
    }

    /* ── heading / notice ── */
    if (type === 'heading' || type === 'notice' || type === 'highlight') {
      const txt = safe(block.text||block.content||block.value||'');
      if (!txt) return '';
      return `<div class="psr4-notice">${esc(txt)}</div>`;
    }

    /* ── fallback: render as paragraph ── */
    const txt = safe(block.text||block.content||block.value||block.description||'');
    if (txt) return `<div class="psr4-para"><p>${esc(txt)}</p></div>`;
    return '';
  }

  /* ══════════════════════════════════════════════════════════════════
     § 5 — KV TABLE BUILDER
     Turns {key: value, ...} into a 2-col table DOM element.
     Skips nulls, empty strings, arrays/objects (those go elsewhere).
  ══════════════════════════════════════════════════════════════════ */
  function buildKVTable(pairs) {
    // pairs = [[label, valueHtml], ...]
    if (!pairs || !pairs.length) return null;
    const t = el('table', 'psr4-kv');
    t.innerHTML = pairs.map(([k,v]) => `<tr><th>${esc(k)}</th><td>${v}</td></tr>`).join('');
    return t;
  }

  /* Render a value as safe HTML (url → link, html → raw, text → esc) */
  function renderVal(v) {
    if (v == null) return '';
    const s = safe(v);
    if (!s || s === '—' || s === 'N/A') return '';
    if (isUrl(s)) return `<a href="${esc(s)}" target="_blank" rel="noopener">${esc(s.replace(/^https?:\/\/(www\.)?/,'').slice(0,60))}</a>`;
    if (/<[a-z]/i.test(s)) return s; // raw HTML
    return esc(s);
  }

  /* ══════════════════════════════════════════════════════════════════
     § 6 — VACANCY TABLE BUILDER
  ══════════════════════════════════════════════════════════════════ */
  function buildVacancyTable(vacRows) {
    if (!Array.isArray(vacRows) || !vacRows.length) return null;
    // Detect columns
    const sample = vacRows[0];
    const colMap = {
      post_name: 'Post Name', 'Post Name': 'Post Name',
      total: 'Total', 'Total Posts': 'Total',
      eligibility: 'Qualification', 'Qualification': 'Qualification',
      'Post Name': 'Post Name'
    };
    const knownCols = ['post_name','Post Name','total','Total Posts','eligibility','Qualification'];
    const cols = knownCols.filter(k => vacRows.some(r => hasVal(r[k])));
    if (!cols.length) {
      // Generic: use all keys from first row
      const allCols = Object.keys(sample).filter(k => k !== 'sl');
      if (!allCols.length) return null;
      const wrap = el('div','psr4-tbl-wrap');
      const t = el('table','psr4-tbl');
      t.innerHTML = `<thead><tr>${allCols.map(c=>`<th>${esc(keyLabel(c))}</th>`).join('')}</tr></thead><tbody>`+
        vacRows.map(r=>`<tr>${allCols.map(c=>`<td>${esc(safe(r[c]))}</td>`).join('')}</tr>`).join('')+`</tbody>`;
      wrap.appendChild(t); return wrap;
    }
    const wrap = el('div','psr4-tbl-wrap');
    const t = el('table','psr4-tbl');
    const hdrs = cols.map(c => colMap[c]||keyLabel(c));
    t.innerHTML = `<thead><tr>${hdrs.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>`+
      vacRows.map(r=>`<tr>${cols.map(c=>`<td>${esc(safe(r[c]))}</td>`).join('')}</tr>`).join('')+`</tbody>`;
    wrap.appendChild(t); return wrap;
  }

  /* ══════════════════════════════════════════════════════════════════
     § 7 — SECTIONS FORMAT RENDERER
     Handles Education_Jobs / state-jobs sections[] array
  ══════════════════════════════════════════════════════════════════ */
  function renderSectionsArray(sections, links, seenLinks, card, skipFirst) {
    if (!Array.isArray(sections) || !sections.length) return;
    const COLORS = ['#1d4ed8','#b91c1c','#be185d','#15803d','#5b21b6','#0369a1','#b45309','#0f766e','#475569','#0f172a'];
    const ICONS  = ['fa-circle-info','fa-calendar-days','fa-indian-rupee-sign','fa-users','fa-graduation-cap','fa-list-check','fa-clipboard-list','fa-link','fa-circle-question','fa-tags'];
    sections.forEach((sec, si) => {
      // Skip "Set as Preferred Source on Google" section title — we handle its content inline
      const secTitle = safe(sec.title || sec.heading || sec.id || `Section ${si+1}`);
      const isPreferred = /preferred.source|set.as.preferred/i.test(secTitle);
      const content = sec.content || sec.items || [];
      if (!Array.isArray(content) || !content.length) {
        // Might be a string section
        if (typeof sec.text === 'string' && sec.text.trim()) {
          const wrap = el('div','psr4-sec');
          if (!isPreferred) wrap.appendChild(mkHead(ICONS[si%ICONS.length], secTitle, COLORS[si%COLORS.length]));
          const body = el('div','psr4-body');
          body.innerHTML = `<div class="psr4-para"><p>${esc(sec.text)}</p></div>`;
          wrap.appendChild(body);
          card.appendChild(wrap);
        }
        return;
      }
      const wrap = el('div','psr4-sec');
      if (!isPreferred) wrap.appendChild(mkHead(ICONS[si%ICONS.length], secTitle, COLORS[si%COLORS.length]));
      const body = el('div','psr4-body');
      content.forEach(block => {
        const html = renderContentBlock(block, links, seenLinks);
        if (html) body.innerHTML += html;
      });
      if (body.innerHTML.trim()) { wrap.appendChild(body); card.appendChild(wrap); }
    });
  }

  /* ══════════════════════════════════════════════════════════════════
     § 8 — MAIN CARD BUILDER
     Accepts normalized raw JSON (any source format).
  ══════════════════════════════════════════════════════════════════ */
  function buildCard(raw, titleText) {
    raw = raw || {};
    const card = el('div');
    const seenLinks = new Set();
    const links = []; // collected from all sources
    const renderedKeys = new Set(); // to avoid duplicate sections

    /* ─── Normalize nested sources ─── */
    const bd  = raw.basic_details || {};
    const det = (raw.detail && typeof raw.detail === 'object') ? raw.detail : raw;
    const iDates = det.important_dates  || raw.important_dates || {};
    const fee    = det.application_fee  || det.application_fees || raw.application_fee || raw.application_fees || {};
    const age    = det.age_limit        || raw.age_limit        || {};
    const qual   = det.qualification    || raw.qualification    || {};
    const vd     = det.vacancy_details  || raw.vacancy_details  || [];
    const cwv    = det.category_wise_vacancy || raw.category_wise_vacancy || {};
    const sal    = det.salary_details   || raw.salary_details   || {};
    const selProc= det.selection_process || raw.selection_process || bd.selection_process || '';
    const hta    = det.how_to_apply     || raw.how_to_apply     || bd.how_to_apply     || null;
    const faq    = det.faq              || raw.faq              || raw.faqs            || null;
    const pe     = det.physical_eligibility || raw.physical_eligibility || null;
    const ep     = det.exam_pattern     || raw.exam_pattern     || null;
    const syl    = det.syllabus         || raw.syllabus         || null;
    const insts  = det.important_instructions || raw.important_instructions || null;
    const reqDoc = det.required_documents || raw.required_documents || null;
    const seoTags= raw.seo_tags || raw.tags || raw.keywords || null;
    const shortInfo = safe(bd.short_information || raw.short_information || raw.jobs_info || det.short_info || '');

    /* ─── Helpers ─── */
    function fv(...keys) {
      for (const k of keys) {
        const v = safe(bd[k] || raw[k] || det[k] || '');
        if (v) return v;
      }
      return '';
    }
    const title    = fv('job_title','title','post_name','name') || titleText || '';
    const org      = fv('organization_name','organization','board_name','department','board','org');
    const postName = fv('post_name','post_names','post');
    const totalVac = fv('total_vacancies','total_vacancy','total_posts','total_post','totalPost');
    const salary   = fv('salary','salary_pay_scale','pay_scale') || safe(sal.pay_scale||sal.details||'');
    const applyMode= fv('application_mode','apply_mode','application_mode') || safe(raw.apply_mode||'');
    const jobLoc   = fv('job_location','location') || safe(raw.job_location||'');
    const category = fv('category','job_type') || safe(raw.category||'');
    const minAge   = fv('minimum_age','min_age');
    const maxAge   = fv('maximum_age','max_age');
    const ageRelax = fv('age_relaxation') || safe(age.details||age.age_relaxation||'');
    const ageDetails = safe(age.age_details||age.details||'');
    const eduQual  = fv('education_qualification','eligibility','qualification') || safe(qual.education_qualification||qual.details||'');
    const notifNo  = fv('notification_number','notification_no','advt_no');
    const jobType  = fv('job_type','type');
    const state    = fv('state','job_location');

    /* ─── Important Dates ─── */
    function getDate(...keys) {
      for (const k of keys) {
        const v = safe(iDates[k] || raw[k] || '');
        if (v) return fmtDate(v);
      }
      return '';
    }
    const appBegin  = getDate('application_begin','application_start','start_date','starting_date','application_start_date');
    const lastDate  = getDate('last_date','last_date_to_apply','application_last_date','closing_date','last_apply_date');
    const feeDate   = getDate('last_date_fee_pay','fee_last_date');
    const examDate  = getDate('exam_date','examination_date');
    const admitDate = getDate('admit_card_date','admit_card');
    const resultDate= getDate('result_date','result');
    const corrDate  = getDate('correction_date','correction_last_date');
    const notifDate = getDate('notification_date','date_of_advertisement','notification date');

    /* ─── Fee items ─── */
    const feeItems = [];
    if (fee && typeof fee === 'object' && !Array.isArray(fee)) {
      const MAP = {
        general:'General', obc:'OBC', ews:'EWS', sc:'SC', st:'ST',
        general_obc_ews:'General/OBC/EWS', sc_st:'SC/ST', sc_fee:'SC',
        general_fee:'General', female:'Female/Women', ph:'PH/PwD',
        all:'For All', others:'Others', pw_d:'PwD'
      };
      for (const [k,lbl] of Object.entries(MAP)) {
        const v = safe(fee[k]||'');
        if (v && v !== '0') feeItems.push([lbl,v]);
      }
      // Any remaining fee keys
      for (const [k,v] of Object.entries(fee)) {
        if (['payment_mode','mode','pay_mode'].includes(k)) continue;
        if (!Object.keys(MAP).includes(k) && hasVal(v) && typeof v !== 'object') {
          feeItems.push([keyLabel(k), safe(v)]);
        }
      }
    }
    const payMode = safe(fee.payment_mode||fee.mode||fee.pay_mode||'Online Net Banking / UPI');

    /* ─── SECTION A: Basic Info + Important Info (dual) ─── */
    const basicPairs = [];
    if (hasVal(org))      basicPairs.push(['Organisation', renderVal(org)]);
    if (hasVal(postName)) basicPairs.push(['Post Name', renderVal(postName)]);
    if (hasVal(totalVac)) basicPairs.push(['Total Posts', renderVal(totalVac)]);
    if (hasVal(jobType))  basicPairs.push(['Job Type', renderVal(jobType)]);
    if (hasVal(applyMode)) {
      const m = applyMode.toLowerCase();
      const cls = m.includes('offline') ? 'psr4-badge-offline' : 'psr4-badge-online';
      basicPairs.push(['Application Mode', `<span class="psr4-badge ${cls}">${esc(applyMode)}</span>`]);
    }
    if (hasVal(salary))   basicPairs.push(['Salary / Pay Scale', `<strong style="color:#16a34a">${renderVal(salary)}</strong>`]);
    if (hasVal(jobLoc))   basicPairs.push(['Job Location', renderVal(jobLoc)]);
    if (hasVal(state) && state !== jobLoc) basicPairs.push(['State', renderVal(state)]);
    if (hasVal(category)) basicPairs.push(['Category', renderVal(category.includes('Jobs')?category:'Central / State Govt Jobs')]);
    if (hasVal(notifNo))  basicPairs.push(['Notification No.', renderVal(notifNo)]);
    if (shortInfo && shortInfo.length > 10) {
      const si = shortInfo.length > 250 ? shortInfo.slice(0,250)+'…' : shortInfo;
      basicPairs.push(['Short Information', esc(si)]);
    }

    const importantPairs = [];
    if (hasVal(appBegin))   importantPairs.push(['Application Start', appBegin]);
    if (hasVal(lastDate))   importantPairs.push([`<span class="psr4-date-red">Last Date to Apply</span>`, `<span class="psr4-date-red">${lastDate}</span>`]);
    if (hasVal(feeDate))    importantPairs.push(['Last Date Fee Pay', feeDate]);
    if (hasVal(notifDate))  importantPairs.push(['Notification Date', notifDate]);
    if (hasVal(examDate))   importantPairs.push(['Exam Date', `<strong>${examDate}</strong>`]);
    if (hasVal(admitDate))  importantPairs.push(['Admit Card', admitDate]);
    if (hasVal(resultDate)) importantPairs.push(['Result Date', resultDate]);
    if (hasVal(corrDate))   importantPairs.push(['Correction Date', corrDate]);
    // Extra date fields
    for (const [k,v] of Object.entries(iDates)) {
      if (!['application_begin','application_start','start_date','starting_date','last_date',
            'last_date_to_apply','application_last_date','closing_date','last_apply_date',
            'last_date_fee_pay','fee_last_date','exam_date','examination_date',
            'admit_card_date','admit_card','result_date','result','correction_date',
            'correction_last_date','notification_date','date_of_advertisement',
            'notification date','event','application_start_date'].includes(k)) {
        if (hasVal(v) && typeof v !== 'object') importantPairs.push([keyLabel(k), fmtDate(v)||esc(safe(v))]);
      }
    }
    renderedKeys.add('important_dates');
    renderedKeys.add('basic_details');

    if (basicPairs.length || importantPairs.length) {
      const dual = el('div', 'psr4-sec');
      const dualInner = el('div', 'psr4-dual');

      if (basicPairs.length) {
        const col = el('div','psr4-col');
        const ch = el('div','psr4-col-head');
        ch.style.background='#1d4ed8';
        ch.innerHTML='<i class="fa-solid fa-circle-info"></i> Basic Information';
        col.appendChild(ch);
        const t = buildKVTable(basicPairs);
        if (t) col.appendChild(t);
        dualInner.appendChild(col);
      }
      if (importantPairs.length) {
        const col = el('div','psr4-col');
        const ch = el('div','psr4-col-head');
        ch.style.background='#b91c1c';
        ch.innerHTML='<i class="fa-solid fa-calendar-check"></i> Important Information';
        col.appendChild(ch);
        const t = buildKVTable(importantPairs);
        if (t) col.appendChild(t);
        dualInner.appendChild(col);
      }
      dual.appendChild(dualInner);
      card.appendChild(dual);
    }

    /* ─── SECTION B: Eligibility + Fee + Links (tri) ─── */
    const hasElig = hasVal(eduQual) || hasVal(minAge) || hasVal(maxAge) || hasVal(ageDetails);
    const hasFee  = feeItems.length > 0 || hasVal(safe(fee));
    const allLinks = collectLinks(raw); // gather all URLs
    allLinks.forEach(l => { if (!seenLinks.has(l.url)) { seenLinks.add(l.url); links.push(l); } });
    const hasLinks = links.length > 0;

    if (hasElig || hasFee || hasLinks) {
      const tri = el('div', 'psr4-sec');
      const triInner = el('div', 'psr4-tri');

      // Eligibility col
      const ec = el('div','psr4-tri-col');
      const eh = el('div','psr4-tri-head'); eh.style.background='#4338ca';
      eh.innerHTML='<i class="fa-solid fa-graduation-cap"></i> Eligibility Details';
      ec.appendChild(eh);
      const eb = el('div','psr4-tri-body');
      if (hasVal(eduQual)) eb.innerHTML += `<div style="margin-bottom:5px"><strong>Education:</strong> ${esc(eduQual).slice(0,200)}</div>`;
      if (hasVal(ageDetails)) eb.innerHTML += `<div style="margin-bottom:4px"><strong>Age Limit:</strong> ${esc(ageDetails).slice(0,120)}</div>`;
      else if (hasVal(minAge)||hasVal(maxAge)) {
        eb.innerHTML += `<div style="margin-bottom:4px"><strong>Age Limit:</strong> ${[hasVal(minAge)?'Min: '+minAge:'',hasVal(maxAge)?'Max: '+maxAge:''].filter(Boolean).join(', ')}</div>`;
      }
      if (hasVal(ageRelax)) eb.innerHTML += `<div><strong>Age Relaxation:</strong> ${esc(ageRelax).slice(0,100)}</div>`;
      if (!eb.textContent.trim()) eb.innerHTML = '<span style="color:#64748b;font-size:.74rem">Check notification for eligibility</span>';
      ec.appendChild(eb); triInner.appendChild(ec);

      // Fee col
      const fc = el('div','psr4-tri-col');
      const fh = el('div','psr4-tri-head'); fh.style.background='#be185d';
      fh.innerHTML='<i class="fa-solid fa-indian-rupee-sign"></i> Application Fee';
      fc.appendChild(fh);
      const fb = el('div','psr4-tri-body');
      if (feeItems.length) {
        fb.innerHTML = feeItems.map(([c,a])=>`<div style="margin-bottom:3px"><strong>${esc(c)}:</strong> ${esc(a)}</div>`).join('');
        fb.innerHTML += `<div style="margin-top:5px;color:#64748b;font-size:.71rem"><strong>Mode:</strong> ${esc(payMode.slice(0,60))}</div>`;
      } else if (hasVal(safe(fee))) {
        fb.innerHTML = `<div>${esc(safe(fee)).slice(0,150)}</div>`;
      } else {
        fb.innerHTML = '<span style="color:#059669;font-weight:700">No Fee / Free</span>';
      }
      fc.appendChild(fb); triInner.appendChild(fc);

      // Links col
      const lc = el('div','psr4-tri-col');
      const lh = el('div','psr4-tri-head'); lh.style.background='#0f766e';
      lh.innerHTML='<i class="fa-solid fa-link"></i> Important Links';
      lc.appendChild(lh);
      const lb = el('div','psr4-links-wrap');
      links.slice(0,10).forEach(lk => {
        const cls = LINK_CLS[lk.type]||'psr4-link-gray';
        const ico = LINK_ICO[lk.type]||'fa-arrow-up-right-from-square';
        lb.innerHTML += `<a href="${esc(lk.url)}" target="_blank" rel="noopener" class="psr4-link ${cls}"><i class="fa-solid ${ico}"></i> ${esc(lk.label).slice(0,35)}</a>`;
      });
      if (!lb.innerHTML) lb.innerHTML = '<span style="color:#64748b;font-size:.74rem">See official website</span>';
      lc.appendChild(lb); triInner.appendChild(lc);

      tri.appendChild(triInner);
      card.appendChild(tri);
    }
    renderedKeys.add('application_fee'); renderedKeys.add('application_fees');
    renderedKeys.add('age_limit'); renderedKeys.add('qualification');
    renderedKeys.add('important_links'); renderedKeys.add('useful_links');
    renderedKeys.add('_udyn_links');

    /* ─── SECTION C: Vacancy + Category-Wise (side by side) ─── */
    const vacRows = Array.isArray(vd) ? vd : (hasVal(vd) ? [{post_name:'Post',total:safe(vd)}] : []);
    const cwRows = [];
    const CW_KEYS = {general:'General/UR', ur:'General/UR', obc:'OBC', ews:'EWS', sc:'SC', st:'ST', ph:'PH/PwD', 'Post Name':'Post Name', 'Total Posts':'Total', 'Total':'Total'};
    for (const [k,lbl] of Object.entries(CW_KEYS)) {
      if (hasVal(cwv[k])) cwRows.push([lbl, safe(cwv[k])]);
    }
    // If cwv has other keys
    for (const [k,v] of Object.entries(cwv)) {
      if (!Object.keys(CW_KEYS).includes(k) && hasVal(v) && typeof v !== 'object') {
        cwRows.push([keyLabel(k), safe(v)]);
      }
    }

    if (vacRows.length || cwRows.length) {
      const sec = el('div','psr4-sec');
      const inner = el('div','psr4-dual');

      if (vacRows.length) {
        const col = el('div','psr4-col');
        const ch = el('div','psr4-col-head'); ch.style.background='#15803d';
        ch.innerHTML='<i class="fa-solid fa-users"></i> Vacancy Details (Post Wise)';
        col.appendChild(ch);
        const t = buildVacancyTable(vacRows);
        if (t) col.appendChild(t);
        inner.appendChild(col);
      }
      if (cwRows.length) {
        const col = el('div','psr4-col');
        const ch = el('div','psr4-col-head'); ch.style.background='#0369a1';
        ch.innerHTML='<i class="fa-solid fa-chart-pie"></i> Category Wise Vacancy';
        col.appendChild(ch);
        const t = el('table','psr4-kv');
        const total = cwRows.reduce((s,[,v])=>s+(parseInt(v)||0),0);
        t.innerHTML = cwRows.map(([k,v])=>`<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('') +
          (total ? `<tr><th><strong>Total</strong></th><td><strong>${total}</strong></td></tr>` : '');
        col.appendChild(t);
        inner.appendChild(col);
      }
      sec.appendChild(inner);
      card.appendChild(sec);
    }
    renderedKeys.add('vacancy_details'); renderedKeys.add('category_wise_vacancy');

    /* ─── SECTION D: Selection Process + Required Documents ─── */
    const selSteps = (() => {
      if (Array.isArray(selProc)) return selProc.flatMap(s=>typeof s==='string'?s.split(/[;,\n]/):[safe(s)]).map(s=>s.trim()).filter(Boolean);
      if (typeof selProc === 'string' && selProc.length > 2) return selProc.split(/[,;\n\/]/).map(s=>s.trim()).filter(Boolean);
      return [];
    })();
    const docList = (() => {
      if (!reqDoc) return [];
      if (Array.isArray(reqDoc)) return reqDoc.map(d=>safe(d)).filter(Boolean);
      if (typeof reqDoc === 'string') return reqDoc.split(/[,;\n]/).map(s=>s.trim()).filter(Boolean);
      return [];
    })();
    renderedKeys.add('selection_process'); renderedKeys.add('required_documents');

    if (selSteps.length || docList.length) {
      const sec = el('div','psr4-sec');
      const inner = el('div','psr4-dual');
      if (selSteps.length) {
        const col = el('div','psr4-col');
        const ch = el('div','psr4-col-head'); ch.style.background='#5b21b6';
        ch.innerHTML='<i class="fa-solid fa-list-check"></i> Selection Process';
        col.appendChild(ch);
        const ul = el('ul','psr4-step-list');
        selSteps.slice(0,8).forEach((step,i)=>{
          const li = el('li','psr4-step');
          li.innerHTML=`<span class="psr4-step-num" style="background:#5b21b6">${i+1}</span><span>${esc(step).slice(0,100)}</span>`;
          ul.appendChild(li);
        });
        col.appendChild(ul); inner.appendChild(col);
      }
      if (docList.length) {
        const col = el('div','psr4-col');
        const ch = el('div','psr4-col-head'); ch.style.background='#b45309';
        ch.innerHTML='<i class="fa-solid fa-file-lines"></i> Required Documents';
        col.appendChild(ch);
        const ul = el('ul','psr4-step-list');
        docList.slice(0,10).forEach((doc,i)=>{
          const li = el('li','psr4-step');
          li.innerHTML=`<span class="psr4-step-num" style="background:#b45309">${i+1}</span><span>${esc(doc).slice(0,100)}</span>`;
          ul.appendChild(li);
        });
        col.appendChild(ul); inner.appendChild(col);
      }
      sec.appendChild(inner); card.appendChild(sec);
    }

    /* ─── SECTION E: How To Apply + Exam Pattern + Syllabus ─── */
    const htaSteps = (() => {
      if (Array.isArray(hta)) return hta.flatMap(h=>typeof h==='string'?h.split(/\n/):[safe(h)]).map(s=>s.trim()).filter(s=>s.length>5);
      if (typeof hta === 'string' && hta.length > 5) return hta.split(/\n/).map(s=>s.trim()).filter(s=>s.length>5);
      return [];
    })();
    renderedKeys.add('how_to_apply');

    const hasEP = ep && typeof ep === 'object' && Object.keys(ep).length > 0;
    const hasSyl = syl && (Array.isArray(syl) ? syl.length : Object.keys(syl).length) > 0;
    renderedKeys.add('exam_pattern'); renderedKeys.add('syllabus');

    if (htaSteps.length || hasEP || hasSyl) {
      const sec = el('div','psr4-sec');
      const inner = el('div','psr4-tri');

      if (htaSteps.length) {
        const col = el('div','psr4-tri-col');
        const ch = el('div','psr4-tri-head'); ch.style.background='#0f766e';
        ch.innerHTML='<i class="fa-solid fa-list-ol"></i> How To Apply';
        col.appendChild(ch);
        const ul = el('ul','psr4-step-list');
        htaSteps.slice(0,8).forEach((step,i)=>{
          const li=el('li','psr4-step');
          li.innerHTML=`<span class="psr4-step-num" style="background:#0f766e">${i+1}</span><span>${esc(step.replace(/^\d+[\.\)]\s*/,'')).slice(0,120)}</span>`;
          ul.appendChild(li);
        });
        col.appendChild(ul); inner.appendChild(col);
      }

      if (hasEP) {
        const col = el('div','psr4-tri-col');
        const ch = el('div','psr4-tri-head'); ch.style.background='#b45309';
        ch.innerHTML='<i class="fa-solid fa-table-list"></i> Exam Pattern';
        col.appendChild(ch);
        const body = el('div','psr4-tri-body');
        if (Array.isArray(ep) && ep.length && typeof ep[0]==='object') {
          const cols = Object.keys(ep[0]);
          const wrap = el('div','psr4-tbl-wrap');
          const t = el('table','psr4-tbl');
          t.innerHTML=`<thead><tr>${cols.map(c=>`<th>${esc(keyLabel(c))}</th>`).join('')}</tr></thead><tbody>`+
            ep.map(r=>`<tr>${cols.map(c=>`<td>${esc(safe(r[c]))}</td>`).join('')}</tr>`).join('')+`</tbody>`;
          wrap.appendChild(t); body.appendChild(wrap);
        } else {
          body.textContent = safe(ep).slice(0,300)||'See official notification';
        }
        col.appendChild(body); inner.appendChild(col);
      }

      if (hasSyl) {
        const col = el('div','psr4-tri-col');
        const ch = el('div','psr4-tri-head'); ch.style.background='#0891b2';
        ch.innerHTML='<i class="fa-solid fa-book-open"></i> Syllabus';
        col.appendChild(ch);
        const ul = el('ul','psr4-list');
        const items = Array.isArray(syl) ? syl : Object.keys(syl);
        items.slice(0,10).forEach(item=>{
          const li=el('li','psr4-li');
          li.innerHTML=`<i class="fa-solid fa-circle-dot psr4-li-dot"></i><span>${esc(safe(item)).slice(0,80)}</span>`;
          ul.appendChild(li);
        });
        col.appendChild(ul); inner.appendChild(col);
      }

      if (inner.children.length) { sec.appendChild(inner); card.appendChild(sec); }
    }

    /* ─── SECTION F: Physical Eligibility ─── */
    if (pe && hasVal(safe(pe))) {
      renderedKeys.add('physical_eligibility');
      const body = el('div','psr4-body');
      if (typeof pe === 'object' && !Array.isArray(pe)) {
        const pairs = Object.entries(pe).filter(([,v])=>hasVal(v)&&typeof v!=='object').map(([k,v])=>[keyLabel(k),renderVal(v)]);
        const t = buildKVTable(pairs);
        if (t) body.appendChild(t);
      } else {
        body.innerHTML=`<div class="psr4-para"><p>${esc(safe(pe)).slice(0,400)}</p></div>`;
      }
      if (body.innerHTML) card.appendChild(mkSection('fa-dumbbell','Physical Eligibility / Standards','#b91c1c',body));
    }

    /* ─── SECTION G: Important Instructions ─── */
    if (insts) {
      renderedKeys.add('important_instructions');
      const instList = Array.isArray(insts) ? insts : (typeof insts==='string' ? insts.split(/\n/).map(s=>s.trim()).filter(Boolean) : []);
      if (instList.length) {
        const ul = el('ul','psr4-list');
        instList.slice(0,10).forEach(inst=>{
          const li=el('li','psr4-li');
          li.innerHTML=`<i class="fa-solid fa-circle-exclamation" style="color:#ea580c;flex-shrink:0;margin-top:3px;"></i><span>${esc(safe(inst)).slice(0,150)}</span>`;
          ul.appendChild(li);
        });
        card.appendChild(mkSection('fa-circle-exclamation','Important Instructions','#b45309',ul));
      }
    }

    /* ─── SECTION H: FAQ ─── */
    if (faq) {
      renderedKeys.add('faq'); renderedKeys.add('faqs');
      const faqArr = Array.isArray(faq) ? faq : Object.entries(faq).map(([q,a])=>({question:q,answer:a}));
      const valid = faqArr.filter(f=>f&&(f.question||f.q)&&(f.answer||f.a));
      // Deduplicate
      const seen = new Set();
      const deduped = valid.filter(f => { const k=(f.question||f.q||'').slice(0,50); if(seen.has(k))return false; seen.add(k); return true; });
      if (deduped.length) {
        const wrap = el('div');
        deduped.slice(0,10).forEach(item => {
          const q = safe(item.question||item.q);
          const a = safe(item.answer||item.a);
          const div = el('div','psr4-faq');
          const qBtn = el('button','psr4-faq-q');
          qBtn.innerHTML = esc(q.slice(0,100))+' <i class="fa-solid fa-chevron-down" style="font-size:.6rem;flex-shrink:0;"></i>';
          const aDiv = el('div','psr4-faq-a',esc(a.slice(0,300)));
          qBtn.addEventListener('click',()=>aDiv.classList.toggle('open'));
          div.appendChild(qBtn); div.appendChild(aDiv);
          wrap.appendChild(div);
        });
        card.appendChild(mkSection('fa-circle-question','Frequently Asked Questions (FAQ)','#0f172a',wrap));
      }
    }

    /* ─── SECTION I: SEO Tags / Keywords ─── */
    if (seoTags) {
      renderedKeys.add('seo_tags'); renderedKeys.add('tags'); renderedKeys.add('keywords');
      const tagArr = Array.isArray(seoTags) ? seoTags : (typeof seoTags==='string' ? seoTags.split(/[,;#]/).map(t=>t.trim()).filter(Boolean) : []);
      if (tagArr.length) {
        const wrap = el('div','psr4-tags');
        tagArr.slice(0,15).forEach(tag => wrap.appendChild(el('span','psr4-tag', esc(tag))));
        card.appendChild(mkSection('fa-tags','SEO Tags / Keywords','#475569',wrap));
      }
    }

    /* ─── SECTION J: sections[] array (state-jobs / education format) ─── */
    if (Array.isArray(raw.sections) && raw.sections.length) {
      renderedKeys.add('sections');
      const extraLinks = [];
      renderSectionsArray(raw.sections, extraLinks, seenLinks, card, true);
      // Add any new links found in sections
      extraLinks.forEach(l => { if (!seenLinks.has(l.url)) { seenLinks.add(l.url); links.push(l); } });
    }
    // Also handle Education_Jobs detail.sections
    if (det && Array.isArray(det.sections) && det.sections.length) {
      const extraLinks = [];
      det.sections.forEach(sec => {
        const content = sec.content || [];
        if (!Array.isArray(content)) return;
        const secTitle = safe(sec.heading||sec.title||'');
        const wrap = el('div','psr4-sec');
        if (secTitle) wrap.appendChild(mkHead('fa-circle-info', secTitle, '#1d4ed8'));
        const body = el('div','psr4-body');
        content.forEach(block => {
          const html = renderContentBlock(block, extraLinks, seenLinks);
          if (html) body.innerHTML += html;
        });
        if (body.innerHTML.trim()) { wrap.appendChild(body); card.appendChild(wrap); }
      });
    }

    /* ─── SECTION K: Full Important Links table (all collected) ─── */
    if (links.length > 0) {
      const ul = el('ul', 'psr4-list');
      links.forEach(lk => {
        const cls = LINK_CLS[lk.type]||'psr4-link-gray';
        const ico = LINK_ICO[lk.type]||'fa-arrow-up-right-from-square';
        const li = el('li','psr4-li');
        li.style.justifyContent='space-between';
        li.innerHTML=`<span style="flex:1;font-weight:600;color:#374151">${esc(lk.label)}</span><a href="${esc(lk.url)}" target="_blank" rel="noopener" class="psr4-link ${cls}"><i class="fa-solid ${ico}"></i> Open</a>`;
        ul.appendChild(li);
      });
      card.appendChild(mkSection('fa-link','All Important Links','#0f766e',ul));
    }

    /* ─── SECTION L: Remaining/unknown JSON keys (zero data loss) ─── */
    const SKIP = new Set([...renderedKeys,
      'basic_details','category','slug','url','link','date','postDate','listing_date',
      'last_updated','sequence','status','name','title','examName','short_info',
      'jobs_info','salary_pay_scale','minimum_age','maximum_age','apply_mode',
      'job_location','organization','organization_name','total_vacancy','total_vacancies',
      'post_name','salary','detail','board','job_type','_udyn_links','apply_online_link',
      'apply_online','official_notification_pdf_link','official_website_link','official_website',
      'form_pdf_link','form_pdf_free_link','application_form_pdf_link',
      'short_information','education_qualification','eligibility','qualification',
      'pay_scale','salary_details','exam_date','admit_card','result','answer_key',
      'notification_number','source_url','apply_link','notify_date'
    ]);

    for (const [k, v] of Object.entries(raw)) {
      if (SKIP.has(k)) continue;
      if (!hasVal(v)) continue;
      if (typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === 0) continue;

      const label = keyLabel(k);

      // Array of strings → list
      if (Array.isArray(v) && v.length && typeof v[0]==='string') {
        const ul=el('ul','psr4-list');
        v.slice(0,15).forEach(item=>{
          const li=el('li','psr4-li');
          li.innerHTML=`<i class="fa-solid fa-circle-dot psr4-li-dot"></i><span>${esc(safe(item)).slice(0,200)}</span>`;
          ul.appendChild(li);
        });
        card.appendChild(mkSection('fa-circle-info',label,'#475569',ul));
        continue;
      }

      // Array of objects → table
      if (Array.isArray(v) && v.length && typeof v[0]==='object') {
        const cols = Object.keys(v[0]).slice(0,6);
        if (cols.length) {
          const wrap=el('div','psr4-tbl-wrap');
          const t=el('table','psr4-tbl');
          t.innerHTML=`<thead><tr>${cols.map(c=>`<th>${esc(keyLabel(c))}</th>`).join('')}</tr></thead><tbody>`+
            v.map(r=>`<tr>${cols.map(c=>`<td>${esc(safe(r[c])).slice(0,100)}</td>`).join('')}</tr>`).join('')+`</tbody>`;
          wrap.appendChild(t);
          card.appendChild(mkSection('fa-table',label,'#1d4ed8',wrap));
        }
        continue;
      }

      // Object → KV table
      if (typeof v === 'object' && !Array.isArray(v)) {
        const pairs = Object.entries(v).filter(([,val])=>hasVal(val)&&typeof val!=='object').map(([k2,v2])=>[keyLabel(k2),renderVal(v2)]);
        if (pairs.length) {
          const t=buildKVTable(pairs);
          if (t) card.appendChild(mkSection('fa-circle-info',label,'#475569',t));
        }
        continue;
      }

      // String/number → single row KV
      const s = safe(v);
      if (s && s.length > 2) {
        const t=buildKVTable([[label, renderVal(s)]]);
        if (t) card.appendChild(mkSection('fa-circle-info',label,'#475569',t));
      }
    }

    return card;
  }

  /* ══════════════════════════════════════════════════════════════════
     § 9 — PAGE INJECTOR
  ══════════════════════════════════════════════════════════════════ */
  function injectCard(inner, titleText) {
    if (document.getElementById('psr-v4-card')) return;
    // Build wrapper
    const wrapper = el('div');
    wrapper.id = 'psr-v4-card';

    // Header bar
    const hbar = el('div','psr4-head');
    hbar.style.cssText='background:linear-gradient(135deg,#1a56db,#1d4ed8);padding:10px 16px;font-size:.83rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;';
    hbar.innerHTML=`<span style="display:flex;align-items:center;gap:7px;"><i class="fa-brands fa-google" style="font-size:1rem;"></i> Set as Preferred Source on Google</span><span style="font-size:.65rem;background:rgba(255,255,255,.2);padding:3px 9px;border-radius:20px;font-weight:700;">${esc(titleText).slice(0,60)}</span>`;
    wrapper.appendChild(hbar);
    wrapper.appendChild(inner);

    // Inject position
    const existing = document.getElementById('preferredSourceCard') || document.getElementById('preferredSourceCardNJ');
    if (existing) {
      existing.style.display = 'none';
      existing.parentNode.insertBefore(wrapper, existing.nextSibling);
      return;
    }
    // After Main CTA / before shortInfoCard
    const shortInfo = document.getElementById('shortInfoCard');
    const mainCta = document.getElementById('btnMainCta');
    if (shortInfo && shortInfo.parentNode) {
      shortInfo.parentNode.insertBefore(wrapper, shortInfo);
      return;
    }
    if (mainCta && mainCta.parentNode) {
      mainCta.parentNode.insertBefore(wrapper, mainCta.nextSibling);
      return;
    }
    // Fallback
    const layout = document.getElementById('layoutJob') || document.getElementById('layoutNonJob') || document.getElementById('jbContent') || document.getElementById('sjdCenter');
    if (layout) { layout.insertBefore(wrapper, layout.firstChild); return; }
    // Education detail: prepend to edContent
    const edContent = document.getElementById('edContent');
    if (edContent) { edContent.insertBefore(wrapper, edContent.firstChild); return; }
    document.body.insertBefore(wrapper, document.body.firstChild);
  }

  /* ══════════════════════════════════════════════════════════════════
     § 10 — TRIGGER LOGIC
  ══════════════════════════════════════════════════════════════════ */
  function tryRender() {
    if (document.getElementById('psr-v4-card')) return;
    if (window.__TSJ_PSR_V4_DONE) return;

    const raw  = window.__TSJ_RAW_JOB || null;
    const layoutJob    = document.getElementById('layoutJob');
    const layoutNonJob = document.getElementById('layoutNonJob');
    const isSJD  = !!document.getElementById('sjdTitle');
    const isEdu  = !!(document.getElementById('edContent') && document.getElementById('edContent').style.display !== 'none');

    const isJob    = isSJD || (layoutJob    && layoutJob.style.display    !== 'none');
    const isNonJob = !isSJD && (layoutNonJob && layoutNonJob.style.display !== 'none');

    if (!isJob && !isNonJob && !isSJD && !isEdu) return;

    // Get title
    const titleEl = document.getElementById('sjdTitle') || document.getElementById('jbTitle') ||
                    document.getElementById('nonJobTitle') ||
                    document.querySelector('#edContent h1') ||
                    document.querySelector('#edContent h2') ||
                    document.querySelector('h1.jp-title') || document.querySelector('h1');
    const name = titleEl ? titleEl.textContent.trim() : '';
    if (!name || name === 'Loading...' || name === 'Job Title') return;

    window.__TSJ_PSR_V4_DONE = true;
    const inner = buildCard(raw || {}, name);
    injectCard(inner, name);
  }

  /* ── Hook into render callbacks ── */
  // Chain onto existing __TSJ_ON_RENDER_DONE
  const _prev = window.__TSJ_ON_RENDER_DONE;
  window.__TSJ_ON_RENDER_DONE = function(rawJob) {
    if (typeof _prev === 'function') _prev(rawJob);
    setTimeout(tryRender, 150);
  };

  // Already rendered?
  if (window.__TSJ_RENDER_DONE) setTimeout(tryRender, 0);

  // DOMContentLoaded fallback
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(tryRender, 900));
  } else {
    setTimeout(tryRender, 900);
  }

  // MutationObserver for dynamic pages
  const obs = new MutationObserver(() => {
    if (!document.getElementById('psr-v4-card') && !window.__TSJ_PSR_V4_DONE) {
      setTimeout(tryRender, 200);
    }
  });
  const obsTarget = document.getElementById('jbContent') ||
                    document.querySelector('.sjd-center-col') ||
                    document.body;
  if (obsTarget) obs.observe(obsTarget, { childList: true, subtree: true, attributes: true });

})();
/* ══ END preferred-source-renderer v4.0 ══ */
